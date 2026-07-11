"""
Render shared Plotly chart figures to PNG for PDF and Word export.
"""

from __future__ import annotations

import logging
import os
import shutil
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import plotly.graph_objects as go

from services.report_chart_figures import (
    build_report_chart_figures,
    has_chart_visuals,
)

logger = logging.getLogger(__name__)

DEFAULT_EXPORT_WIDTH = 1200
DEFAULT_EXPORT_HEIGHT = 480
CHART_EXPORT_UNAVAILABLE_NOTE = (
    "Chart images could not be rendered in this environment."
)

CHROME_EXECUTABLE_NAMES = (
    "google-chrome",
    "chromium",
    "chromium-browser",
    "chrome",
)

COMMON_CHROME_PATHS = (
    "/usr/bin/google-chrome",
    "/usr/bin/chromium",
    "/usr/bin/chromium-browser",
    "/usr/bin/chrome",
    "/snap/bin/chromium",
)


@dataclass(frozen=True)
class ChartExportResult:
    images: list[tuple[str, bytes]]
    unavailable_note: str | None = None


def _kaleido_available() -> bool:
    try:
        import kaleido  # noqa: F401
    except ImportError:
        return False

    return True


def _windows_chrome_paths() -> list[str]:
    paths: list[str] = []
    for env_name in ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA"):
        base = os.environ.get(env_name, "").strip()
        if not base:
            continue
        paths.append(os.path.join(base, "Google", "Chrome", "Application", "chrome.exe"))

    return paths


def _kaleido_cached_chrome_paths() -> list[str]:
    discovered: list[str] = []
    cache_roots = (
        Path.home() / ".cache" / "choreographer",
        Path.home() / ".cache" / "kaleido",
        Path.home() / ".local" / "share" / "choreographer",
    )
    executable_names = {"chrome", "chrome.exe", "chromium", "chromium.exe", "google-chrome"}

    for root in cache_roots:
        if not root.exists():
            continue

        for path in root.rglob("*"):
            if path.is_file() and path.name.lower() in executable_names:
                discovered.append(str(path))

    return discovered


def _choreographer_browser_path() -> str | None:
    try:
        import choreographer
    except ImportError:
        return None

    for attr in ("get_browser_executable", "get_chrome_path", "browser_executable"):
        getter = getattr(choreographer, attr, None)
        if not callable(getter):
            continue

        try:
            path = getter()
        except Exception:
            logger.debug("Unable to resolve choreographer browser via %s", attr, exc_info=True)
            continue

        if path and os.path.isfile(str(path)):
            return str(path)

    return None


def find_chrome_executable() -> str | None:
    """Return the first discovered Chrome/Chromium executable, if any."""

    for env_name in ("CHROME_PATH", "GOOGLE_CHROME_BIN", "CHROMIUM_PATH"):
        env_path = os.environ.get(env_name, "").strip()
        if env_path and os.path.isfile(env_path):
            return env_path

    choreographer_path = _choreographer_browser_path()
    if choreographer_path:
        return choreographer_path

    for name in CHROME_EXECUTABLE_NAMES:
        found = shutil.which(name)
        if found and os.path.isfile(found):
            return found

    for path in (*COMMON_CHROME_PATHS, *_windows_chrome_paths(), *_kaleido_cached_chrome_paths()):
        if os.path.isfile(path):
            return path

    return None


def _ensure_chrome_path() -> str | None:
    chrome = find_chrome_executable()
    if chrome and not os.environ.get("CHROME_PATH"):
        os.environ["CHROME_PATH"] = chrome
    return chrome


@lru_cache(maxsize=1)
def is_chart_export_available() -> bool:
    """Return True when kaleido and a Chrome/Chromium executable are available."""

    if not _kaleido_available():
        logger.warning("Chart export unavailable: kaleido is not installed")
        return False

    chrome = find_chrome_executable()
    if not chrome:
        logger.warning(
            "Chart export unavailable: Chrome/Chromium executable not found "
            "(checked PATH and common install locations)"
        )
        return False

    return True


def plotly_figure_to_png(
    figure: go.Figure,
    *,
    width: int = DEFAULT_EXPORT_WIDTH,
    height: int = DEFAULT_EXPORT_HEIGHT,
) -> bytes:
    """Rasterize a Plotly figure for embedding in exported documents."""

    _ensure_chrome_path()
    return figure.to_image(format="png", width=width, height=height, scale=2)


def render_chart_pngs(chart_data: dict[str, Any]) -> ChartExportResult:
    """Build Plotly figures and render them to PNG bytes when export is available."""

    if not has_chart_visuals(chart_data):
        return ChartExportResult(images=[])

    if not is_chart_export_available():
        return ChartExportResult(
            images=[],
            unavailable_note=CHART_EXPORT_UNAVAILABLE_NOTE,
        )

    images: list[tuple[str, bytes]] = []

    try:
        for title, figure in build_report_chart_figures(chart_data):
            try:
                images.append((title, plotly_figure_to_png(figure)))
            except Exception:
                logger.exception("Chart export failed while rendering %r", title)
                return ChartExportResult(
                    images=[],
                    unavailable_note=CHART_EXPORT_UNAVAILABLE_NOTE,
                )
    except Exception:
        logger.exception("Chart export failed while building Plotly figures")
        return ChartExportResult(
            images=[],
            unavailable_note=CHART_EXPORT_UNAVAILABLE_NOTE,
        )

    return ChartExportResult(images=images)
