"""
Supabase authentication service.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from config import (
    AUTH_DEV_BYPASS,
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
    is_duplicate_email_error,
    normalize_email,
)


class AuthError(Exception):
    """Raised when an authentication action fails."""


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
            from supabase import create_client

            self._client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

    @property
    def is_configured(self) -> bool:
        return self._client is not None or AUTH_DEV_BYPASS

    def _require_client(self):
        if AUTH_DEV_BYPASS:
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
        if not AUTH_DEV_BYPASS:
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
        if not AUTH_DEV_BYPASS:
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

        if EmailUniquenessService().email_exists(normalized_email):
            raise AuthError(DUPLICATE_EMAIL_MESSAGE)

        if AUTH_DEV_BYPASS:
            return self.dev_sign_up(normalized_email, full_name=full_name)

        client = self._require_client()
        assert client is not None

        try:
            response = client.auth.sign_up(
                {
                    "email": normalized_email,
                    "password": password,
                    "options": {
                        "data": {"full_name": full_name.strip()},
                        "email_redirect_to": AUTH_REDIRECT_URL,
                    },
                }
            )
        except Exception as exc:
            if is_duplicate_email_error(exc):
                raise AuthError(DUPLICATE_EMAIL_MESSAGE) from exc
            raise AuthError("Sign up failed. Please try again.") from exc

        if response.user is None:
            raise AuthError("Sign up failed. Please try again.")

        session = response.session
        user = self._user_from_payload(response.user.model_dump())

        if session is None:
            EmailUniquenessService().register_email(normalized_email, user.id)
            return None

        EmailUniquenessService().register_email(normalized_email, user.id)

        return AuthSession(
            access_token=session.access_token,
            refresh_token=session.refresh_token,
            user=user,
        )

    def sign_in(
        self,
        email: str,
        password: str,
    ) -> AuthSession:
        if AUTH_DEV_BYPASS:
            return self.dev_sign_in()

        from services.lockout_service import LockoutService

        normalized_email = normalize_email(email)
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

    def sign_out(
        self,
        access_token: str | None = None,
        refresh_token: str | None = None,
    ) -> None:
        if AUTH_DEV_BYPASS:
            return

        client = self._require_client()
        assert client is not None

        if access_token and refresh_token:
            client.auth.set_session(access_token, refresh_token)

        client.auth.sign_out()

    def restore_session(
        self,
        access_token: str,
        refresh_token: str,
    ) -> AuthSession:
        if AUTH_DEV_BYPASS:
            return self.dev_sign_in()

        client = self._require_client()
        assert client is not None

        response = client.auth.set_session(access_token, refresh_token)

        return self._session_from_response(response)

    def refresh_session(self, refresh_token: str) -> AuthSession:
        if AUTH_DEV_BYPASS:
            return self.dev_sign_in()

        client = self._require_client()
        assert client is not None

        response = client.auth.refresh_session(refresh_token)

        return self._session_from_response(response)

    def send_password_reset(self, email: str) -> None:
        client = self._require_client()
        assert client is not None

        client.auth.reset_password_for_email(
            email.strip(),
            {"redirect_to": AUTH_REDIRECT_URL},
        )

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

        client.auth.resend(
            {
                "type": "signup",
                "email": email.strip(),
                "options": {"email_redirect_to": AUTH_REDIRECT_URL},
            }
        )

    def exchange_auth_code(self, code: str) -> AuthSession:
        """Exchange a Supabase email link code for a session."""

        client = self._require_client()
        assert client is not None

        response = client.auth.exchange_code_for_session({"auth_code": code})

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
