"""
Report Model
"""

from dataclasses import dataclass


@dataclass
class Report:

    filename: str

    name: str

    size: int

    path: str

    created_at: str