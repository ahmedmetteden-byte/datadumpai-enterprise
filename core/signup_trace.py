"""Temporary file-backed evidence for signup debugging."""

from __future__ import annotations

import logging
from pathlib import Path

SIGNUP_TRACE_FILE = Path("/tmp/signup_trace.log")


def append_signup_trace_line(line: str) -> None:
    """Append one evidence line to the container-local trace file."""

    try:
        SIGNUP_TRACE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with SIGNUP_TRACE_FILE.open("a", encoding="utf-8") as handle:
            handle.write(line.rstrip() + "\n")
    except OSError:
        logging.getLogger(__name__).debug(
            "Could not append signup trace line",
            exc_info=True,
        )


def signup_trace_log(logger: logging.Logger, message: str, *args: object) -> None:
    """Mirror SIGNUP_TRACE logger output to /tmp/signup_trace.log."""

    line = message % args if args else message
    logger.info(line)
    append_signup_trace_line(line)
