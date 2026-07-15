"""
Supabase authentication service.
"""

from __future__ import annotations

import logging
from contextlib import suppress
from dataclasses import dataclass
from typing import Any, Literal

import config
from config import (
    AUTH_REDIRECT_URL,
    DEV_USER_EMAIL,
    DEV_USER_ID,
    SUPABASE_ANON_KEY,
    SUPABASE_URL,
    is_supabase_configured,
)
from models.user import User
from services.email_uniqueness import (
    DUPLICATE_EMAIL_MESSAGE,
    EmailUniquenessService,
    SIGN_UP_UNVERIFIED_DUPLICATE_MESSAGE,
    SIGN_UP_VERIFIED_DUPLICATE_MESSAGE,
    is_duplicate_email_error,
    normalize_email,
)


class AuthError(Exception):
    """Raised when an authentication action fails."""

    def __init__(self, message: str, *, title: str | None = None) -> None:
        super().__init__(message)
        self.title = title


PASSWORD_RESET_RATE_LIMIT_TITLE = "Too many password reset requests"
PASSWORD_RESET_RATE_LIMIT_MESSAGE = (
    "You've requested too many password reset emails. "
    "Please wait a few minutes before trying again. "
    "If you've already requested one, check your inbox and spam folder "
    "before requesting another."
)
PASSWORD_RESET_GENERIC_MESSAGE = (
    "We couldn't send the password reset email right now. Please try again later."
)

SIGN_UP_EMAIL_RATE_LIMIT_TITLE = "Too many verification emails"
SIGN_UP_EMAIL_RATE_LIMIT_MESSAGE = (
    "Too many verification emails were sent recently. "
    "Please wait a few minutes, then try creating your account again. "
    "If you already signed up, open the verification link in your inbox "
    "or use Resend on the verification screen."
)
SIGN_UP_CREATED_EMAIL_DELAYED_MESSAGE = (
    "Your account was created, but the verification email is temporarily delayed "
    "due to email rate limits. Wait a few minutes, then use "
    "'Resend verification email' on the next screen."
)

logger = logging.getLogger(__name__)


def _is_email_rate_limit_error(exc: Exception) -> bool:
    from supabase_auth.errors import AuthApiError

    if not isinstance(exc, AuthApiError):
        message = str(exc).lower()
        return "rate limit" in message or "too many" in message

    code = getattr(exc, "code", None)
    if code in {"over_email_send_rate_limit", "over_request_rate_limit"}:
        return True

    if getattr(exc, "status", None) == 429:
        return True

    message = str(exc).lower()
    return "rate limit" in message or "too many" in message


def _is_password_reset_rate_limit_error(exc: Exception) -> bool:
    return _is_email_rate_limit_error(exc)

def _is_password_reset_network_error(exc: Exception) -> bool:
    try:
        import httpx

        network_types = (
            httpx.HTTPError,
            httpx.TransportError,
            ConnectionError,
            TimeoutError,
            OSError,
        )
    except ImportError:
        network_types = (ConnectionError, TimeoutError, OSError)

    return isinstance(exc, network_types)


class SignUpDuplicateError(AuthError):
    """Raised when sign-up targets an email that already has an account."""

    def __init__(self, message: str, *, verification_status: str) -> None:
        super().__init__(message)
        self.verification_status = verification_status


class SignUpEmailDelayedError(AuthError):
    """Raised when the account was created but verification email is delayed."""

    def __init__(self, message: str = SIGN_UP_CREATED_EMAIL_DELAYED_MESSAGE) -> None:
        super().__init__(message, title=SIGN_UP_EMAIL_RATE_LIMIT_TITLE)

@dataclass(frozen=True)
class AuthSession:
    """Tokens returned after a successful sign-in or sign-up."""

    access_token: str
    refresh_token: str
    user: User


class AuthService:
    """Wrap Supabase Auth for sign-up, sign-in, and account management."""

    def __init__(self) -> None:
        self._client = None
        if is_supabase_configured():
            from supabase import ClientOptions, create_client

            # PKCE so password-recovery (and other email) links return ?code=...
            # instead of #access_token=... implicit fragments.
            self._client = create_client(
                SUPABASE_URL,
                SUPABASE_ANON_KEY,
                options=ClientOptions(flow_type="pkce"),
            )

    @property
    def is_configured(self) -> bool:
        return self._client is not None or config.auth_dev_bypass_enabled()

    def _require_client(self):
        if config.auth_dev_bypass_enabled():
            return None
        if self._client is None:
            raise AuthError(
                "Authentication is not configured. Set SUPABASE_URL and "
                "SUPABASE_ANON_KEY in your environment."
            )
        return self._client

    @staticmethod
    def _user_from_payload(payload: dict[str, Any]) -> User:
        metadata = payload.get("user_metadata") or {}
        full_name = metadata.get("full_name") or metadata.get("name")

        return User(
            id=str(payload["id"]),
            email=str(payload.get("email") or ""),
            full_name=str(full_name).strip() if full_name else None,
            email_verified=bool(payload.get("email_confirmed_at")),
        )

    @staticmethod
    def _require_verified_email(user: User) -> None:
        if not user.email_verified:
            raise AuthError(
                "Please verify your email before signing in. "
                "Check your inbox for the confirmation link."
            )

    def _session_from_response(self, response) -> AuthSession:
        if response.session is None or response.user is None:
            raise AuthError("Your session has expired. Please sign in again.")

        user = self._user_from_payload(response.user.model_dump())
        self._require_verified_email(user)

        return AuthSession(
            access_token=response.session.access_token,
            refresh_token=response.session.refresh_token,
            user=user,
        )

    def dev_sign_in(self) -> AuthSession:
        """Legacy development-only sign-in. Never used in production paths."""

        if not config.auth_dev_bypass_enabled():
            raise AuthError("Development auth bypass is disabled.")

        user = User(
            id=DEV_USER_ID,
            email=DEV_USER_EMAIL,
            full_name="Local Developer",
            email_verified=True,
        )
        return AuthSession(
            access_token="dev-access-token",
            refresh_token="dev-refresh-token",
            user=user,
        )

    def dev_sign_up(
        self,
        email: str,
        *,
        full_name: str = "",
    ) -> AuthSession:
        """Legacy development-only sign-up. Never used in production paths."""

        if not config.auth_dev_bypass_enabled():
            raise AuthError("Development auth bypass is disabled.")

        normalized_email = normalize_email(email)
        if not normalized_email:
            raise AuthError("Enter a valid email address.")

        if EmailUniquenessService().email_exists(normalized_email):
            raise AuthError(DUPLICATE_EMAIL_MESSAGE)

        resolved_name = full_name.strip() or "Local Developer"
        user = User(
            id=DEV_USER_ID,
            email=normalized_email,
            full_name=resolved_name,
            email_verified=True,
        )

        EmailUniquenessService().register_email(normalized_email, DEV_USER_ID)

        try:
            from core.current_user import current_user_scope
            from services.profile_service import ProfileService

            with current_user_scope(user):
                ProfileService().save(
                    {"full_name": resolved_name, "email": normalized_email}
                )
        except Exception:
            pass

        return AuthSession(
            access_token="dev-access-token",
            refresh_token="dev-refresh-token",
            user=user,
        )

    @staticmethod
    def _is_duplicate_sign_up_user(user: Any) -> bool:
        payload = user.model_dump() if hasattr(user, "model_dump") else user
        identities = payload.get("identities")
        if identities is None:
            return False
        return len(identities) == 0

    def _lookup_auth_user_by_email(self, email: str) -> Any | None:
        if not config.is_supabase_configured():
            return None

        try:
            from core.database import get_service_role_client
            from supabase_auth.helpers import model_validate
            from supabase_auth.types import UserList

            client = get_service_role_client()
            response = client.auth.admin._request(
                "GET",
                "admin/users",
                query={"filter": email, "page": 1, "per_page": 1},
            )
            users = model_validate(UserList, response.content).users
            if not users:
                return None
            return users[0]
        except Exception:
            return None

    def _existing_account_verification_status(
        self,
        client,
        email: str,
        password: str,
    ) -> Literal["verified", "unverified"]:
        existing = self._lookup_auth_user_by_email(email)
        if existing is not None:
            if existing.email_confirmed_at or existing.confirmed_at:
                return "verified"
            return "unverified"

        try:
            response = client.auth.sign_in_with_password(
                {"email": email, "password": password}
            )
        except Exception as exc:
            message = str(exc).lower()
            if "verify" in message or "confirm" in message:
                return "unverified"
            return "verified"

        if response.session is None or response.user is None:
            return "verified"

        user = self._user_from_payload(response.user.model_dump())
        with suppress(*self._benign_logout_errors()):
            client.auth.sign_out()

        return "verified" if user.email_verified else "unverified"

    def _raise_duplicate_sign_up_error(
        self,
        client,
        email: str,
        password: str,
    ) -> None:
        status = self._existing_account_verification_status(client, email, password)
        if status == "unverified":
            raise SignUpDuplicateError(
                SIGN_UP_UNVERIFIED_DUPLICATE_MESSAGE,
                verification_status="unverified",
            )
        raise SignUpDuplicateError(
            SIGN_UP_VERIFIED_DUPLICATE_MESSAGE,
            verification_status="verified",
        )

    def _delete_orphaned_account_rows(self, email: str) -> bool:
        """
        Remove profile/usage rows for an email that has no matching auth user.

        Orphaned profiles block signup: the auth trigger inserts into
        user_profiles and hits the unique email index, which Supabase reports
        only as "Database error saving new user".
        """

        if self._lookup_auth_user_by_email(email) is not None:
            return False

        if not config.use_database() or not config.is_supabase_configured():
            return False

        try:
            from core.database import get_service_role_client, handle_response

            client = get_service_role_client()
            response = handle_response(
                client.table("user_profiles")
                .select("user_id")
                .ilike("email", email)
                .execute(),
                action="lookup orphaned profiles for signup",
            )
            rows = response.data or []
            if not rows:
                return False

            removed = False
            for row in rows:
                user_id = str(row.get("user_id") or "")
                if not user_id:
                    continue

                handle_response(
                    client.table("user_usage").delete().eq("user_id", user_id).execute(),
                    action="delete orphaned usage for signup",
                )
                handle_response(
                    client.table("user_profiles")
                    .delete()
                    .eq("user_id", user_id)
                    .execute(),
                    action="delete orphaned profile for signup",
                )
                removed = True
                logger.warning(
                    "Removed orphaned account rows for email=%s user_id=%s before signup",
                    email,
                    user_id,
                )

            return removed
        except Exception:
            logger.exception("Failed to reclaim orphaned account rows for %s", email)
            return False

    @staticmethod
    def _is_connectivity_error(exc: Exception) -> bool:
        message = str(exc).lower()
        if "certificate" in message or "ssl" in message:
            return True
        return _is_password_reset_network_error(exc)

    @staticmethod
    def _is_database_save_user_error(exc: Exception) -> bool:
        message = str(exc).lower()
        return "database error saving new user" in message

    def sign_up(
        self,
        email: str,
        password: str,
        *,
        full_name: str = "",
    ) -> AuthSession | None:
        normalized_email = normalize_email(email)
        if not normalized_email:
            raise AuthError("Enter a valid email address.")

        if config.auth_dev_bypass_enabled():
            return self.dev_sign_up(normalized_email, full_name=full_name)

        # Prefer service-role signup so we never depend on Supabase's
        # verification-email rate limit (over_email_send_rate_limit).
        if self._admin_sign_up_available():
            return self._sign_up_with_admin(
                normalized_email,
                password,
                full_name=full_name,
            )

        client = self._require_client()
        assert client is not None

        existing_auth_user = self._lookup_auth_user_by_email(normalized_email)
        if existing_auth_user is not None:
            self._raise_duplicate_sign_up_error(client, normalized_email, password)

        self._delete_orphaned_account_rows(normalized_email)

        try:
            response = self._create_supabase_user(
                client,
                normalized_email,
                password,
                full_name=full_name,
            )
        except Exception as exc:
            if _is_email_rate_limit_error(exc) and self._admin_sign_up_available():
                return self._sign_up_with_admin(
                    normalized_email,
                    password,
                    full_name=full_name,
                )
            response = self._recover_sign_up_failure(
                client,
                exc,
                email=normalized_email,
                password=password,
                full_name=full_name,
            )

        if response.user is None:
            raise AuthError("Sign up failed. Please try again.")

        if self._is_duplicate_sign_up_user(response.user):
            self._raise_duplicate_sign_up_error(client, normalized_email, password)

        session = response.session
        user = self._user_from_payload(response.user.model_dump())

        if session is None:
            return None

        return AuthSession(
            access_token=session.access_token,
            refresh_token=session.refresh_token,
            user=user,
        )

    @staticmethod
    def _admin_sign_up_available() -> bool:
        return bool(
            config.use_database()
            and config.is_supabase_configured()
            and config.SUPABASE_SERVICE_ROLE_KEY
        )

    def _sign_up_with_admin(
        self,
        email: str,
        password: str,
        *,
        full_name: str,
    ) -> AuthSession:
        """Create a confirmed user via service role (no verification email sent)."""

        existing = self._lookup_auth_user_by_email(email)
        if existing is not None:
            confirmed = bool(
                getattr(existing, "email_confirmed_at", None)
                or getattr(existing, "confirmed_at", None)
            )
            if confirmed:
                client = self._require_client()
                assert client is not None
                self._raise_duplicate_sign_up_error(client, email, password)

            # Finish an incomplete prior signup without sending email.
            self._complete_unverified_signup(
                str(existing.id),
                password,
                full_name=full_name,
            )
            return self._session_after_password_sign_in(email, password)

        self._delete_orphaned_account_rows(email)

        try:
            from core.database import get_service_role_client

            admin_client = get_service_role_client()
            response = admin_client.auth.admin.create_user(
                {
                    "email": email,
                    "password": password,
                    "email_confirm": True,
                    "user_metadata": {"full_name": full_name.strip()},
                }
            )
        except Exception as exc:
            if is_duplicate_email_error(exc):
                client = self._require_client()
                assert client is not None
                self._raise_duplicate_sign_up_error(client, email, password)
            if self._is_connectivity_error(exc):
                raise AuthError(
                    "Could not reach the authentication service. "
                    "Check your internet connection and try again."
                ) from exc
            raise AuthError("Sign up failed. Please try again.") from exc

        if response.user is None:
            raise AuthError("Sign up failed. Please try again.")

        return self._session_after_password_sign_in(email, password)

    def _complete_unverified_signup(
        self,
        user_id: str,
        password: str,
        *,
        full_name: str,
    ) -> None:
        from core.database import get_service_role_client

        admin_client = get_service_role_client()
        admin_client.auth.admin.update_user_by_id(
            user_id,
            {
                "password": password,
                "email_confirm": True,
                "user_metadata": {"full_name": full_name.strip()},
            },
        )
        logger.info("Completed unverified signup without email for user_id=%s", user_id)

    def _session_after_password_sign_in(self, email: str, password: str) -> AuthSession:
        client = self._require_client()
        assert client is not None

        try:
            response = client.auth.sign_in_with_password(
                {"email": email, "password": password}
            )
        except Exception as exc:
            raise AuthError(
                "Account created, but automatic sign-in failed. Please sign in."
            ) from exc

        if response.session is None or response.user is None:
            raise AuthError(
                "Account created, but automatic sign-in failed. Please sign in."
            )

        user = self._user_from_payload(response.user.model_dump())
        return AuthSession(
            access_token=response.session.access_token,
            refresh_token=response.session.refresh_token,
            user=user,
        )

    def _recover_sign_up_failure(
        self,
        client,
        exc: Exception,
        *,
        email: str,
        password: str,
        full_name: str,
    ):
        if is_duplicate_email_error(exc):
            self._raise_duplicate_sign_up_error(client, email, password)

        if _is_email_rate_limit_error(exc):
            raise AuthError(
                SIGN_UP_EMAIL_RATE_LIMIT_MESSAGE,
                title=SIGN_UP_EMAIL_RATE_LIMIT_TITLE,
            ) from exc

        if self._is_database_save_user_error(exc):
            if self._delete_orphaned_account_rows(email):
                try:
                    return self._create_supabase_user(
                        client,
                        email,
                        password,
                        full_name=full_name,
                    )
                except Exception as retry_exc:
                    return self._recover_sign_up_failure(
                        client,
                        retry_exc,
                        email=email,
                        password=password,
                        full_name=full_name,
                    )
            raise AuthError(
                "Sign up failed because an incomplete account already exists "
                "for this email. Please contact support or try a different email."
            ) from exc

        if self._is_connectivity_error(exc):
            raise AuthError(
                "Could not reach the authentication service. "
                "Check your internet connection and try again."
            ) from exc

        raise AuthError("Sign up failed. Please try again.") from exc

    def _create_supabase_user(
        self,
        client,
        email: str,
        password: str,
        *,
        full_name: str,
    ):
        return client.auth.sign_up(
            {
                "email": email,
                "password": password,
                "options": {
                    "data": {"full_name": full_name.strip()},
                    "email_redirect_to": AUTH_REDIRECT_URL,
                },
            }
        )

    def sign_in(
        self,
        email: str,
        password: str,
    ) -> AuthSession:
        normalized_email = normalize_email(email)

        if config.auth_dev_bypass_enabled():
            return self.dev_sign_in()

        from services.lockout_service import LockoutService

        LockoutService().check_allowed(normalized_email)

        client = self._require_client()
        assert client is not None

        try:
            response = client.auth.sign_in_with_password(
                {
                    "email": normalized_email,
                    "password": password,
                }
            )
        except Exception as exc:
            LockoutService().record_failure(normalized_email)
            message = str(exc).lower()
            if "invalid" in message or "password" in message or "credentials" in message:
                raise AuthError("Invalid email or password.") from exc
            raise AuthError("Sign in failed. Please try again.") from exc

        if response.session is None or response.user is None:
            LockoutService().record_failure(normalized_email)
            raise AuthError("Invalid email or password.")

        user = self._user_from_payload(response.user.model_dump())
        try:
            self._require_verified_email(user)
        except AuthError:
            LockoutService().record_failure(normalized_email)
            raise

        LockoutService().record_success(normalized_email)

        return AuthSession(
            access_token=response.session.access_token,
            refresh_token=response.session.refresh_token,
            user=user,
        )

    @staticmethod
    def _benign_logout_errors():
        from supabase_auth.errors import AuthError as SupabaseAuthError

        return (SupabaseAuthError,)

    def _revoke_remote_session(self, client, access_token: str) -> None:
        """Revoke the Supabase session when the client has no in-memory session."""

        with suppress(*self._benign_logout_errors()):
            client.auth.admin.sign_out(access_token)

    def sign_out(
        self,
        access_token: str | None = None,
        refresh_token: str | None = None,
    ) -> None:
        if config.auth_dev_bypass_enabled():
            return

        client = self._require_client()
        assert client is not None

        existing_session = None
        with suppress(*self._benign_logout_errors()):
            existing_session = client.auth.get_session()

        if existing_session is not None:
            with suppress(*self._benign_logout_errors()):
                client.auth.sign_out()
            return

        if access_token:
            self._revoke_remote_session(client, access_token)

        with suppress(*self._benign_logout_errors()):
            client.auth.sign_out()

    def restore_session(
        self,
        access_token: str,
        refresh_token: str,
    ) -> AuthSession:
        if config.auth_dev_bypass_enabled():
            return self.dev_sign_in()

        client = self._require_client()
        assert client is not None

        response = client.auth.set_session(access_token, refresh_token)

        return self._session_from_response(response)

    def refresh_session(self, refresh_token: str) -> AuthSession:
        if config.auth_dev_bypass_enabled():
            return self.dev_sign_in()

        client = self._require_client()
        assert client is not None

        response = client.auth.refresh_session(refresh_token)

        return self._session_from_response(response)

    def send_password_reset(self, email: str) -> None:
        from supabase_auth.errors import AuthApiError, AuthRetryableError

        client = self._require_client()
        assert client is not None

        try:
            client.auth.reset_password_for_email(
                email.strip(),
                {"redirect_to": AUTH_REDIRECT_URL},
            )
        except Exception as exc:
            if _is_password_reset_rate_limit_error(exc):
                raise AuthError(
                    PASSWORD_RESET_RATE_LIMIT_MESSAGE,
                    title=PASSWORD_RESET_RATE_LIMIT_TITLE,
                ) from exc

            if isinstance(exc, AuthApiError):
                logger.warning(
                    "Password reset Supabase auth error (%s): %s",
                    getattr(exc, "code", None),
                    exc,
                )
                raise AuthError(PASSWORD_RESET_GENERIC_MESSAGE) from exc

            if isinstance(exc, AuthRetryableError):
                logger.warning("Password reset retryable auth error: %s", exc)
                raise AuthError(PASSWORD_RESET_GENERIC_MESSAGE) from exc

            if _is_password_reset_network_error(exc):
                logger.warning("Password reset network error: %s", exc)
                raise AuthError(PASSWORD_RESET_GENERIC_MESSAGE) from exc

            logger.exception("Unexpected password reset error")
            raise AuthError(PASSWORD_RESET_GENERIC_MESSAGE) from exc

    def update_password(
        self,
        new_password: str,
        access_token: str,
        refresh_token: str,
    ) -> None:
        client = self._require_client()
        assert client is not None

        client.auth.set_session(access_token, refresh_token)
        response = client.auth.update_user({"password": new_password})

        if response.user is None:
            raise AuthError("Could not update your password. Please try again.")

    def resend_verification(self, email: str) -> None:
        client = self._require_client()
        assert client is not None

        try:
            client.auth.resend(
                {
                    "type": "signup",
                    "email": email.strip(),
                    "options": {"email_redirect_to": AUTH_REDIRECT_URL},
                }
            )
        except Exception as exc:
            if _is_email_rate_limit_error(exc):
                raise AuthError(
                    SIGN_UP_EMAIL_RATE_LIMIT_MESSAGE,
                    title=SIGN_UP_EMAIL_RATE_LIMIT_TITLE,
                ) from exc
            raise AuthError(
                "Could not resend the verification email. Please try again shortly."
            ) from exc

    def exchange_auth_code(self, code: str) -> AuthSession:
        """Exchange a Supabase email link code for a session."""

        from core.recovery_callback_trace import log_supabase_exchange

        client = self._require_client()
        assert client is not None

        try:
            response = client.auth.exchange_code_for_session({"auth_code": code})
        except AuthError as exc:
            log_supabase_exchange(
                operation="exchange_code_for_session",
                branch="pkce",
                success=False,
                error=str(exc),
                exception_type=type(exc).__name__,
            )
            raise
        except Exception as exc:
            log_supabase_exchange(
                operation="exchange_code_for_session",
                branch="pkce",
                success=False,
                error=str(exc),
                exception_type=type(exc).__name__,
            )
            raise AuthError("This link is invalid or has expired.") from exc

        session_returned = response.session is not None
        user_returned = response.user is not None
        log_supabase_exchange(
            operation="exchange_code_for_session",
            branch="pkce",
            success=session_returned and user_returned,
            session_returned=session_returned,
            user_returned=user_returned,
        )

        if response.session is None or response.user is None:
            raise AuthError("This link is invalid or has expired.")

        user = self._user_from_payload(response.user.model_dump())

        return AuthSession(
            access_token=response.session.access_token,
            refresh_token=response.session.refresh_token,
            user=user,
        )

    def exchange_recovery_code(self, code: str) -> AuthSession:
        return self.exchange_auth_code(code)

    def exchange_recovery_token_hash(self, token_hash: str) -> AuthSession:
        """Establish a recovery session from a Supabase email token hash."""

        from core.recovery_callback_trace import log_supabase_exchange

        client = self._require_client()
        assert client is not None

        try:
            response = client.auth.verify_otp(
                {
                    "type": "recovery",
                    "token_hash": token_hash,
                }
            )
        except AuthError as exc:
            log_supabase_exchange(
                operation="verify_otp",
                branch="otp",
                success=False,
                error=str(exc),
                exception_type=type(exc).__name__,
            )
            raise
        except Exception as exc:
            log_supabase_exchange(
                operation="verify_otp",
                branch="otp",
                success=False,
                error=str(exc),
                exception_type=type(exc).__name__,
            )
            raise AuthError(
                "This password reset link is invalid or has expired."
            ) from exc

        session_returned = response.session is not None
        user_returned = response.user is not None
        log_supabase_exchange(
            operation="verify_otp",
            branch="otp",
            success=session_returned and user_returned,
            session_returned=session_returned,
            user_returned=user_returned,
        )

        if response.session is None or response.user is None:
            raise AuthError("This password reset link is invalid or has expired.")

        user = self._user_from_payload(response.user.model_dump())

        return AuthSession(
            access_token=response.session.access_token,
            refresh_token=response.session.refresh_token,
            user=user,
        )