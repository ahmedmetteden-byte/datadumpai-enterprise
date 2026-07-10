"""
DataDumpAI Enterprise
Theme Engine

This module is the single source of truth for the
application's visual identity.

Every UI component should import colors and spacing
from here instead of hardcoding values.
"""

from dataclasses import dataclass


# ==========================================================
# BRAND COLORS
# ==========================================================

@dataclass(frozen=True)
class Brand:

    PRIMARY = "#2563EB"
    PRIMARY_HOVER = "#1D4ED8"
    ACCENT = "#06B6D4"


# ==========================================================
# APPLICATION COLORS
# ==========================================================

@dataclass(frozen=True)
class Colors:

    # Backgrounds
    CANVAS = "#EDF2F7"
    SURFACE = "#FFFFFF"
    SURFACE_ALT = "#F8FAFC"

    # Sidebar
    SIDEBAR = "#0F172A"
    SIDEBAR_HOVER = "#1E293B"
    SIDEBAR_ACTIVE = "#2563EB"

    # Text
    TEXT = "#0F172A"
    MUTED = "#64748B"
    LIGHT = "#94A3B8"
    WHITE = "#FFFFFF"

    # Borders
    BORDER = "#E2E8F0"
    BORDER_LIGHT = "#F1F5F9"

    # Status
    SUCCESS = "#16A34A"
    WARNING = "#D97706"
    ERROR = "#DC2626"
    INFO = "#2563EB"


# ==========================================================
# TYPOGRAPHY
# ==========================================================

@dataclass(frozen=True)
class Typography:

    FONT = (
        "Inter,"
        "'Segoe UI',"
        "Roboto,"
        "Arial,"
        "sans-serif"
    )

    HERO = 52

    PAGE_TITLE = 36

    SECTION = 26

    CARD = 20

    BODY = 15

    SMALL = 13

    CAPTION = 12


# ==========================================================
# SPACING
# ==========================================================

@dataclass(frozen=True)
class Spacing:

    XS = 4
    SM = 8
    MD = 12
    LG = 16
    XL = 24
    XXL = 32
    XXXL = 48
    PAGE = 56


# ==========================================================
# RADII
# ==========================================================

@dataclass(frozen=True)
class Radius:

    SMALL = 8
    MEDIUM = 12
    LARGE = 18
    XLARGE = 24
    ROUND = 999


# ==========================================================
# SHADOWS
# ==========================================================

@dataclass(frozen=True)
class Shadow:

    CARD = (
        "0 2px 6px rgba(15,23,42,.05), "
        "0 12px 28px rgba(15,23,42,.08)"
    )

    FLOAT = (
        "0 18px 40px rgba(15,23,42,.14)"
    )

    NONE = "none"


# ==========================================================
# CONTROLS
# ==========================================================

@dataclass(frozen=True)
class Controls:

    SIDEBAR_ITEM = 38

    BUTTON = 40

    INPUT = 42

    TAB = 40

    TOOLBAR = 60

    HERO = 135


# ==========================================================
# EXPORTS
# ==========================================================

BRAND = Brand()
COLORS = Colors()
TYPE = Typography()
SPACE = Spacing()
RADIUS = Radius()
SHADOW = Shadow()
CONTROL = Controls()