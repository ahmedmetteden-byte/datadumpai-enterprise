"""
Document Model
"""

from dataclasses import dataclass


@dataclass
class Document:

    filename: str

    size: int

    uploaded_at: str

    path: str