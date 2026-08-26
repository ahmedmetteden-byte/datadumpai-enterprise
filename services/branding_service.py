"""
Custom report logo storage — the "Branded reports with your logo" Professional+
feature. Stores one logo per account, keyed by user id, and hands back raw
bytes for the export builders to embed instead of the default DataDumpAI mark.
"""

from __future__ import annotations

from pathlib import Path

import config
from core.current_user import CurrentUser, require_current_user
from core.database import get_database_client
from core.user_paths import get_user_branding_logo_path

_ALLOWED_CONTENT_TYPES = {
    "image/png": "png",
    "image/jpeg": "jpg",
    "image/svg+xml": "svg",
}
_MAX_LOGO_BYTES = 2 * 1024 * 1024  # 2 MB


class BrandingError(Exception):
    """Raised when a logo upload is rejected."""


class BrandingService:
    """Store and retrieve the per-account custom report logo."""

    def __init__(
        self,
        *,
        current_user: CurrentUser | None = None,
        access_token: str | None = None,
    ) -> None:
        self._current_user = current_user or require_current_user()
        self._access_token = access_token

    def _bucket_key(self, extension: str) -> str:
        return f"{self._current_user.id}/branding/logo.{extension}"

    def _local_path(self, extension: str) -> Path:
        return get_user_branding_logo_path(self._current_user.id, extension)

    def save_logo(self, *, content: bytes, content_type: str) -> str:
        """Persist a new logo, replacing any prior one. Returns the storage key."""

        extension = _ALLOWED_CONTENT_TYPES.get((content_type or "").lower())
        if extension is None:
            raise BrandingError("Logo must be a PNG, JPEG, or SVG image.")
        if not content:
            raise BrandingError("Logo file is empty.")
        if len(content) > _MAX_LOGO_BYTES:
            raise BrandingError("Logo must be smaller than 2MB.")

        other_extensions = [ext for ext in _ALLOWED_CONTENT_TYPES.values() if ext != extension]

        if config.use_supabase_storage():
            client = get_database_client(access_token=self._access_token)
            bucket = client.storage.from_(config.SUPABASE_STORAGE_BUCKET)
            key = self._bucket_key(extension)
            for other_ext in other_extensions:
                try:
                    bucket.remove([self._bucket_key(other_ext)])
                except Exception:
                    pass
            bucket.upload(
                key,
                content,
                file_options={"content-type": content_type, "upsert": "true"},
            )
            return key

        path = self._local_path(extension)
        path.parent.mkdir(parents=True, exist_ok=True)
        for other_ext in other_extensions:
            self._local_path(other_ext).unlink(missing_ok=True)
        path.write_bytes(content)
        return str(path)

    def load_logo_bytes(self, storage_key: str) -> bytes | None:
        """Return the stored logo's bytes, or None if it's missing."""

        if not storage_key:
            return None

        path = Path(storage_key)
        if path.is_file():
            return path.read_bytes()

        if config.use_supabase_storage():
            client = get_database_client(access_token=self._access_token)
            try:
                return client.storage.from_(config.SUPABASE_STORAGE_BUCKET).download(storage_key)
            except Exception:
                return None

        return None

    def content_type_for_key(self, storage_key: str) -> str:
        suffix = Path(storage_key).suffix.lower().lstrip(".")
        for content_type, extension in _ALLOWED_CONTENT_TYPES.items():
            if extension == suffix:
                return content_type
        return "application/octet-stream"

    def delete_logo(self, storage_key: str) -> None:
        if not storage_key:
            return

        path = Path(storage_key)
        if path.is_file():
            path.unlink(missing_ok=True)
            return

        if config.use_supabase_storage():
            client = get_database_client(access_token=self._access_token)
            try:
                client.storage.from_(config.SUPABASE_STORAGE_BUCKET).remove([storage_key])
            except Exception:
                pass
