"""Central configuration for the Rokitna Project Management System.

Holds filesystem paths, application metadata, the color palette and a few
constants that are shared across all layers of the application.  Keeping these
values in a single module avoids magic strings scattered throughout the code.
"""

from __future__ import annotations

from pathlib import Path

# --------------------------------------------------------------------------- #
# Paths
# --------------------------------------------------------------------------- #
BASE_DIR: Path = Path(__file__).resolve().parent
DB_PATH: Path = BASE_DIR / "rokitna.db"
EXPORTS_DIR: Path = BASE_DIR / "exports"
DRAWINGS_DIR: Path = BASE_DIR / "drawings"
LOG_PATH: Path = BASE_DIR / "rokitna.log"

# --------------------------------------------------------------------------- #
# Application metadata
# --------------------------------------------------------------------------- #
APP_TITLE: str = "Rokitna Project Management"
APP_SUBTITLE: str = "מערכת ניהול פרויקטים למשרד אדריכלות ועיצוב פנים"

# Default password used for the seeded demo users (stored hashed, never plain).
DEFAULT_PASSWORD: str = "1234"

# --------------------------------------------------------------------------- #
# Brand palette — "Premium black + gold" (warm-white background).
# The full visual theme lives in app.py (_apply_theme) and .streamlit/config.toml;
# these constants document the canonical brand colours.
# --------------------------------------------------------------------------- #
COLOR_BACKGROUND: str = "#FAFAF9"   # warm white
COLOR_SURFACE: str = "#FFFFFF"
COLOR_INK: str = "#1C1917"          # warm near-black — primary
COLOR_ACCENT: str = "#A16207"       # gold accent
COLOR_SIDEBAR: str = "#1C1917"      # dark charcoal sidebar
