"""Shared prompt guidance blocks for report generation."""

from __future__ import annotations

from typing import Any


def additional_guidance_section(report_context: dict[str, Any]) -> str:
    text = (report_context.get("additional_guidance") or "").strip()
    if not text:
        return ""
    return f"\nADDITIONAL USER GUIDANCE\n{text}\n"
