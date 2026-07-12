"""
Blob storage — local filesystem or Supabase Storage.
"""

from __future__ import annotations

import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

import config
from core.auth import get_current_user_id
from core.user_paths import get_user_projects_root


class FileStore:
    """Read and write project files across storage backends."""

    CATEGORIES = ("documents", "reports", "exports")

    def __init__(self, user_id: str) -> None:
        self._user_id = user_id
        self._backend = self._resolve_backend()

    @classmethod
    def for_current_user(cls) -> FileStore:
        return cls(get_current_user_id())

    @staticmethod
    def _resolve_backend() -> str:
        if config.use_supabase_storage():
            return "supabase"
        return "local"

    def _local_root(self, project_id: str) -> Path:
        return get_user_projects_root(self._user_id) / project_id

    def _storage_key(self, project_id: str, category: str, filename: str) -> str:
        safe_name = Path(filename).name
        return f"{self._user_id}/{project_id}/{category}/{safe_name}"

    def _split_storage_key(self, storage_key: str) -> list[str]:
        return storage_key.replace("\\", "/").strip("/").split("/")

    def _parse_storage_key(self, storage_key: str) -> tuple[str, str, str, str]:
        parts = self._split_storage_key(storage_key)
        if len(parts) != 4:
            raise ValueError(f"Invalid storage key: {storage_key!r}")
        user_id, project_id, category, filename = parts
        return user_id, project_id, category, filename

    def _assert_owned_storage_key(self, storage_key: str) -> None:
        user_root = get_user_projects_root(self._user_id).resolve()
        path = Path(storage_key)

        try:
            path.resolve(strict=False).relative_to(user_root)
            return
        except ValueError:
            pass

        parts = self._split_storage_key(storage_key)
        if len(parts) == 4 and parts[2] in self.CATEGORIES:
            if parts[0] != self._user_id:
                raise PermissionError(f"Access denied to storage key: {storage_key!r}")
            return

        raise PermissionError(f"Access denied to storage key: {storage_key!r}")

    def write(
        self,
        project_id: str,
        category: str,
        filename: str,
        content: bytes,
    ) -> str:
        safe_name = Path(filename).name

        if self._backend == "supabase":
            key = self._storage_key(project_id, category, safe_name)
            client = self._supabase_client()
            client.storage.from_(config.SUPABASE_STORAGE_BUCKET).upload(
                key,
                content,
                file_options={"content-type": "application/octet-stream", "upsert": "true"},
            )
            return key

        folder = self._local_root(project_id) / category
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / safe_name
        path.write_bytes(content)
        return str(path)

    def read_bytes(self, storage_key: str) -> bytes:
        self._assert_owned_storage_key(storage_key)

        path = Path(storage_key)
        if path.is_file():
            return path.read_bytes()

        if self._backend == "supabase" or self._looks_like_storage_key(storage_key):
            key = self._normalize_key(storage_key)
            client = self._supabase_client()
            return client.storage.from_(config.SUPABASE_STORAGE_BUCKET).download(key)

        return Path(storage_key).read_bytes()

    def read_text(self, storage_key: str, *, encoding: str = "utf-8") -> str:
        return self.read_bytes(storage_key).decode(encoding)

    def delete(self, storage_key: str) -> None:
        self._assert_owned_storage_key(storage_key)

        path = Path(storage_key)
        if path.is_file():
            path.unlink()
            return

        if self._backend == "supabase" or self._looks_like_storage_key(storage_key):
            key = self._normalize_key(storage_key)
            client = self._supabase_client()
            client.storage.from_(config.SUPABASE_STORAGE_BUCKET).remove([key])

    def exists(self, storage_key: str) -> bool:
        try:
            self._assert_owned_storage_key(storage_key)
        except PermissionError:
            return False

        path = Path(storage_key)
        if path.is_file():
            return True

        if self._backend == "supabase" or self._looks_like_storage_key(storage_key):
            try:
                self.read_bytes(storage_key)
                return True
            except Exception:
                return False

        return False

    def list_files(self, project_id: str, category: str) -> list[str]:
        if self._backend == "supabase":
            prefix = f"{self._user_id}/{project_id}/{category}/"
            client = self._supabase_client()
            entries = client.storage.from_(config.SUPABASE_STORAGE_BUCKET).list(prefix)
            names: list[str] = []
            for entry in entries or []:
                name = entry.get("name")
                if name and not name.endswith("/"):
                    names.append(name)
            return sorted(names)

        folder = self._local_root(project_id) / category
        if not folder.exists():
            return []
        return sorted(path.name for path in folder.iterdir() if path.is_file())

    @contextmanager
    def readable_path(self, storage_key: str) -> Iterator[Path]:
        """Yield a local path suitable for libraries that need filesystem access."""

        self._assert_owned_storage_key(storage_key)

        if self._backend == "local" and not self._looks_like_storage_key(storage_key):
            path = Path(storage_key)
            if not path.is_file():
                raise FileNotFoundError(storage_key)
            yield path
            return

        suffix = Path(self._normalize_key(storage_key)).suffix or ".bin"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as handle:
            handle.write(self.read_bytes(storage_key))
            temp_path = Path(handle.name)

        try:
            yield temp_path
        finally:
            temp_path.unlink(missing_ok=True)

    def ensure_project_folders(self, project_id: str) -> None:
        if self._backend == "local":
            root = self._local_root(project_id)
            for category in self.CATEGORIES:
                (root / category).mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _looks_like_storage_key(storage_key: str) -> bool:
        parts = storage_key.replace("\\", "/").strip("/").split("/")
        return len(parts) == 4 and parts[2] in FileStore.CATEGORIES

    def _normalize_key(self, storage_key: str) -> str:
        if self._looks_like_storage_key(storage_key):
            return storage_key.replace("\\", "/")
        return storage_key.replace("\\", "/")

    @staticmethod
    def _supabase_client():
        from core.database import get_database_client

        return get_database_client()
