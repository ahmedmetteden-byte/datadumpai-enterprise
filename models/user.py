"""
Authenticated user model.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class User:
    """Represents a signed-in DataDumpAI account."""

    id: str
    email: str
    full_name: str | None = None
    email_verified: bool = False

    @property
    def display_name(self) -> str:
        if self.full_name and self.full_name.strip():
            return self.full_name.strip()
        if self.email:
            return self.email.split("@")[0]
        return "User"

    @property
    def initials(self) -> str:
        parts = self.display_name.split()
        if len(parts) >= 2:
            return f"{parts[0][0]}{parts[1][0]}".upper()
        if parts:
            return parts[0][:2].upper()
        return "U"
