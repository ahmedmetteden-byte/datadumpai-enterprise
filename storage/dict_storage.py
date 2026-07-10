"""
Generic JSON object persistence.
"""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any


class DictStorage:
    """Persist a single JSON object to disk."""

    def __init__(
        self,
        path: str | Path,
        default: dict[str, Any] | None = None,
    ) -> None:
        self.path = Path(path)
        self.default = deepcopy(default or {})
        self.path.parent.mkdir(parents=True, exist_ok=True)

        if not self.path.exists():
            self.save(self.default)

    def load(self) -> dict[str, Any]:
        with self.path.open(encoding="utf-8") as file:
            data = json.load(file)

        if not isinstance(data, dict):
            raise ValueError(f"Expected a JSON object in {self.path}.")

        return data

    def save(self, data: dict[str, Any]) -> None:
        with self.path.open("w", encoding="utf-8") as file:
            json.dump(data, file, indent=2)
            file.write("\n")
