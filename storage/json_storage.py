"""
DataDumpAI Enterprise
JSON Storage Engine
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class JSONStorage:
    """
    Generic JSON persistence layer.
    """

    def __init__(self, path: str | Path):

        self.path = Path(path)

        self.path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        if not self.path.exists():

            self.save([])

    def load(self) -> list[dict[str, Any]]:

        with self.path.open(
            encoding="utf-8",
        ) as file:

            return json.load(file)

    def save(
        self,
        data: list[dict[str, Any]],
    ) -> None:

        with self.path.open(
            "w",
            encoding="utf-8",
        ) as file:

            json.dump(
                data,
                file,
                indent=2,
            )

            file.write("\n")