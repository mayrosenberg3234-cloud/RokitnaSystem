"""Rokitna Project Management System — Streamlit entry point.

Run with::

    streamlit run app.py

This module wires together the views, handles session state, applies the visual
theme and routes the logged-in user between screens based on their role.  It
contains no business logic or SQL — every action is delegated to a controller.
"""

from __future__ import annotations

import streamlit as st

from config import APP_SUBTITLE, APP_TITLE
from init_db import initialize_database
from models.user import User
from utils.logger import get_logger
from utils.permissions import Permission, has_permission
from views import (
    architect_workspace,
    customer_management,
    dashboard,
    decision_management,
    login_form,
    manager_oversight,
    report_dashboard,
)

logger = get_logger()


def _apply_theme() -> None:
    """Inject the refined warm-neutral 'architecture studio' RTL theme."""
    st.markdown(_THEME_CSS, unsafe_allow_html=True)


# A single, self-contained design system (plain string — no f-string, so literal
# CSS braces need no escaping).  Palette: warm paper background, white surfaces,
# olive brand, gold accent; editorial Hebrew serif headings + clean sans body.
_THEME_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Heebo:wght@300;400;500;600;700;800;900&family=Suez+One&display=swap');

:root {
  --bg: #FAFAF9;          /* warm white */
  --surface: #FFFFFF;
  --surface-2: #F5F5F4;   /* stone-100 */
  --ink: #1C1917;         /* stone-900 (near-black) */
  --muted: #78716C;       /* stone-500 */
  --primary: #1C1917;     /* near-black — primary action */
  --primary-700: #292524; /* hover */
  --accent: #A16207;      /* gold (WCAG-safe) */
  --accent-700: #854D0E;
  --accent-050: #FBF3E3;
  --border: #E7E5E4;      /* stone-200 */
  --ring: rgba(161,98,7,.28);
  /* dark sidebar */
  --side-bg: #1C1917;
  --side-bg-2: #292524;
  --side-border: #3A332E;
  --side-text: #E7E5E4;
  --side-muted: #A8A29E;
  --radius: 12px;
  --radius-sm: 9px;
  --shadow-sm: 0 1px 2px rgba(28,25,23,.04);
  --shadow-md: 0 10px 28px rgba(28,25,23,.10);
  --sans: 'Heebo','Assistant','Segoe UI','Arial Hebrew',sans-serif;
  --display: 'Suez One','Frank Ruhl Libre',Georgia,serif;
}

/* ---- Base ------------------------------------------------------------- */
html, body, .stApp { font-family: var(--sans); }
button, input, textarea, select { font-family: var(--sans); }
/* Preserve Streamlit's Material icon ligatures — never override their font,
   or icons render as raw text (e.g. "keyboard_double_arrow_left"). */
[data-testid="stIconMaterial"], .material-symbols-rounded, .material-symbols-outlined,
span[class*="material-symbols"] {
  font-family: 'Material Symbols Rounded','Material Symbols Outlined' !important;
}
.stApp { background-color: var(--bg); color: var(--ink); }

/* Hide Streamlit's top toolbar (Deploy/menu) for a cleaner product feel. */
[data-testid="stToolbar"] { display: none !important; }
header[data-testid="stHeader"] { background: transparent; height: 0; }

/* Main content: comfortable measure, generous (Exaggerated-Minimalism) spacing. */
[data-testid="stMain"] .block-container {
  direction: rtl;
  max-width: 1140px;
  padding-top: 2.6rem;
  padding-bottom: 5rem;
}

/* ---- Typography (oversized, high contrast) ---------------------------- */
h1, h2 { font-family: var(--display); color: var(--ink); letter-spacing: -0.015em; font-weight: 400; line-height: 1.12; }
h1 { font-size: 2.9rem; margin-bottom: .2rem; }
h2 { font-size: 2rem; }
h3 { font-family: var(--sans); font-weight: 800; font-size: 1.32rem; color: var(--ink); letter-spacing: -.01em; }
h4, h5, h6 { font-family: var(--sans); font-weight: 700; color: var(--ink); }
[data-testid="stMarkdownContainer"] p { line-height: 1.7; }
[data-testid="stCaptionContainer"], .stCaption, small { color: var(--muted) !important; }
a, a:visited { color: var(--accent); text-decoration: none; font-weight: 600; }
a:hover { color: var(--accent-700); text-decoration: underline; }

/* ---- Sidebar (dark charcoal + gold) ---------------------------------- */
section[data-testid="stSidebar"] {
  background-color: var(--side-bg);
  border-left: 1px solid var(--side-border);
  direction: rtl;
  min-width: 20.5rem !important;
}
section[data-testid="stSidebar"] .block-container { padding-top: 1.7rem; }
section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"],
section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] * { color: var(--side-text); }
section[data-testid="stSidebar"] hr { margin: 1rem 0; border-color: var(--side-border); }

/* ---- Buttons: primary = near-black, secondary = quiet outline --------- */
.stButton > button, .stDownloadButton > button, .stFormSubmitButton > button {
  font-family: var(--sans);
  font-weight: 700;
  border-radius: var(--radius-sm);
  border: 1px solid var(--primary);
  background: var(--primary);
  color: #FFFFFF;
  padding: 0.5rem 1.1rem;
  min-height: 2.8rem;
  transition: background .18s ease, border-color .18s ease, transform .06s ease, box-shadow .18s ease;
  box-shadow: var(--shadow-sm);
}
.stButton > button:hover, .stDownloadButton > button:hover, .stFormSubmitButton > button:hover {
  background: var(--primary-700); border-color: var(--primary-700); color: #FFFFFF; box-shadow: var(--shadow-md);
}
.stButton > button:active, .stFormSubmitButton > button:active { transform: translateY(1px); }
.stButton > button:focus-visible, .stFormSubmitButton > button:focus-visible {
  outline: none; box-shadow: 0 0 0 3px var(--ring);
}
/* Primary (filled) call-to-actions in the MAIN area use the gold accent so the
   key action pops against near-black secondary actions. */
[data-testid="stMain"] .stButton > button[kind="primary"],
[data-testid="stMain"] .stFormSubmitButton > button {
  background: var(--accent); border-color: var(--accent); color: #FFFFFF;
}
[data-testid="stMain"] .stButton > button[kind="primary"]:hover,
[data-testid="stMain"] .stFormSubmitButton > button:hover {
  background: var(--accent-700); border-color: var(--accent-700);
}
.stDownloadButton > button { background: var(--accent); border-color: var(--accent); }
.stDownloadButton > button:hover { background: var(--accent-700); border-color: var(--accent-700); }
/* Secondary (outline) in the main area. */
[data-testid="stMain"] .stButton > button[kind="secondary"] {
  background: transparent; color: var(--ink); border: 1px solid var(--border); box-shadow: none;
}
[data-testid="stMain"] .stButton > button[kind="secondary"]:hover {
  background: var(--surface-2); border-color: var(--ink); color: var(--ink);
}

/* Sidebar nav buttons: quiet on dark, gold pill when active. */
section[data-testid="stSidebar"] .stButton > button { text-align: right; }
section[data-testid="stSidebar"] .stButton > button[kind="secondary"] {
  background: transparent; color: var(--side-text); border: 1px solid transparent; box-shadow: none; font-weight: 600;
}
section[data-testid="stSidebar"] .stButton > button[kind="secondary"]:hover {
  background: var(--side-bg-2); border-color: var(--side-border); color: #FFFFFF;
}
section[data-testid="stSidebar"] .stButton > button[kind="primary"] {
  background: var(--accent); border-color: var(--accent); color: #FFFFFF;
}
section[data-testid="stSidebar"] .stButton > button[kind="primary"]:hover {
  background: var(--accent-700); border-color: var(--accent-700);
}

/* ---- Inputs ----------------------------------------------------------- */
.stTextInput input, .stTextArea textarea, .stNumberInput input,
div[data-baseweb="select"] > div, div[data-baseweb="base-input"] {
  border-radius: var(--radius-sm) !important;
  border: 1px solid var(--border) !important;
  background: var(--surface) !important;
}
.stTextInput input:focus, .stTextArea textarea:focus, .stNumberInput input:focus {
  border-color: var(--accent) !important; box-shadow: 0 0 0 3px var(--ring) !important;
}
label, .stTextInput label, .stTextArea label, .stSelectbox label, .stRadio label {
  font-weight: 600 !important; color: var(--ink) !important;
}

/* ---- Cards: forms, bordered containers, expanders --------------------- */
[data-testid="stForm"] {
  background: var(--surface); border: 1px solid var(--border);
  border-radius: var(--radius); padding: 1.3rem 1.4rem; box-shadow: var(--shadow-sm);
}
div[data-testid="stExpander"] {
  border: 1px solid var(--border); border-radius: var(--radius);
  background: var(--surface); box-shadow: var(--shadow-sm); overflow: hidden;
}
div[data-testid="stExpander"] summary { font-weight: 700; }

/* ---- Metrics as KPI cards (gold numbers) ----------------------------- */
[data-testid="stMetric"] {
  background: var(--surface); border: 1px solid var(--border);
  border-radius: var(--radius); padding: 1.05rem 1.15rem; box-shadow: var(--shadow-sm);
  border-top: 3px solid var(--accent);
}
[data-testid="stMetricLabel"] { color: var(--muted); font-weight: 600; }
[data-testid="stMetricValue"] { font-family: var(--display); color: var(--ink); }

/* ---- Tables / dataframes --------------------------------------------- */
[data-testid="stDataFrame"], .stDataFrame {
  border: 1px solid var(--border) !important; border-radius: var(--radius) !important;
  overflow: hidden; box-shadow: var(--shadow-sm);
}

/* ---- Alerts ----------------------------------------------------------- */
[data-testid="stAlert"] { border-radius: var(--radius-sm); border: 1px solid var(--border); }

/* ---- Dividers --------------------------------------------------------- */
hr { border-color: var(--border); margin: 1.5rem 0; }

/* ---- RTL correctness (kept from earlier fixes) ----------------------- */
div[data-testid="InputInstructions"], div[data-testid="stTextInputInstructions"] { display: none !important; }
.stTextInput input, .stTextArea textarea { direction: rtl; text-align: right; }
.stTextInput input::placeholder, .stTextArea textarea::placeholder { text-align: right; opacity: .55; }
.stTextInput input[type="email"], .stTextInput input[type="tel"] { direction: ltr; text-align: left; }
div[data-baseweb="select"] { direction: rtl; }
div[data-baseweb="popover"], ul[role="listbox"], li[role="option"], div[data-baseweb="menu"] {
  direction: rtl !important; text-align: right !important;
}
</style>
"""


def _init_session_state() -> None:
    """Ensure the keys the app relies on always exist in the session state."""
    st.session_state.setdefault("user", None)
    st.session_state.setdefault("page", "dashboard")
    st.session_state.setdefault("last_report", None)


# Navigation items: (page key, label, required permission or None).
_NAV_ITEMS = [
    ("dashboard", "לוח בקרה", None),
    ("customers", "ניהול לקוחות", Permission.MANAGE_CLIENTS),
    ("decisions", "תיעוד החלטות", Permission.RECORD_DECISIONS),
    ("studio", "סטודיו אדריכלי", Permission.MANAGE_PROJECT_CONTENT),
    ("reports", "הפקת דוחות", Permission.GENERATE_REPORTS),
    ("oversight", "מעקב וניהול פעולות", Permission.VIEW_OVERSIGHT),
]


def _render_sidebar(user: User) -> None:
    """Render the sidebar: brand, current user and role-aware navigation."""
    current = st.session_state.get("page", "dashboard")
    with st.sidebar:
        st.markdown(
            f"""
            <div style="display:flex;align-items:center;gap:.65rem;margin-bottom:.25rem;">
              <div style="width:42px;height:42px;border-radius:11px;background:var(--accent);
                          color:#fff;display:flex;align-items:center;justify-content:center;
                          font-family:var(--display);font-size:1.35rem;">R</div>
              <div style="font-family:var(--display);font-size:1.3rem;color:#fff;line-height:1.05;">{APP_TITLE}</div>
            </div>
            <div style="color:var(--side-muted);font-size:.82rem;margin-bottom:.3rem;">{APP_SUBTITLE}</div>
            """,
            unsafe_allow_html=True,
        )
        st.divider()
        st.markdown(
            f"""
            <div style="background:var(--side-bg-2);border:1px solid var(--side-border);
                        border-radius:12px;padding:.75rem .9rem;">
              <div style="color:var(--side-muted);font-size:.76rem;">מחובר/ת כ־</div>
              <div style="font-weight:700;color:#fff;font-size:1.02rem;">{user.username}</div>
              <div style="display:inline-block;margin-top:.4rem;padding:.14rem .6rem;
                          background:rgba(161,98,7,.20);color:#E7B765;
                          border:1px solid rgba(161,98,7,.45);
                          border-radius:999px;font-size:.78rem;font-weight:600;">
                {user.role.hebrew_label}
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("")

        for page_key, label, permission in _NAV_ITEMS:
            if permission is not None and not has_permission(user.role, permission):
                continue
            is_active = current == page_key
            if st.button(
                label,
                key=f"nav_{page_key}",
                use_container_width=True,
                type="primary" if is_active else "secondary",
            ):
                st.session_state["page"] = page_key
                st.rerun()

        st.divider()
        if st.button("התנתקות", use_container_width=True, type="secondary"):
            logger.info("LOGOUT: %s", user.username)
            st.session_state["user"] = None
            st.session_state["page"] = "dashboard"
            st.session_state["last_report"] = None
            st.rerun()


# Pages keyed by the permission required to view them (None = always allowed).
_PAGES = {
    "dashboard": (None, dashboard.render),
    "customers": (Permission.MANAGE_CLIENTS, customer_management.render),
    "decisions": (Permission.RECORD_DECISIONS, decision_management.render),
    "studio": (Permission.MANAGE_PROJECT_CONTENT, architect_workspace.render),
    "reports": (Permission.GENERATE_REPORTS, report_dashboard.render),
    "oversight": (Permission.VIEW_OVERSIGHT, manager_oversight.render),
}


def _route(user: User) -> None:
    """Render the page selected in the session state, enforcing permissions."""
    page = st.session_state.get("page", "dashboard")
    required_permission, render_page = _PAGES.get(page, _PAGES["dashboard"])

    if required_permission is not None and not has_permission(
        user.role, required_permission
    ):
        logger.warning("PERMISSION DENIED (page %s): %s", page, user.username)
        st.error("אין לך הרשאה לצפות בעמוד זה.")
        st.session_state["page"] = "dashboard"
        dashboard.render(user)
        return

    # Final safety net: a view must never expose a raw traceback to the user.
    try:
        render_page(user)
    except Exception:  # noqa: BLE001 - intentional top-level guard
        logger.exception("UNEXPECTED ERROR while rendering page '%s'", page)
        st.error("אירעה שגיאה בלתי צפויה. נסה שוב או חזור ללוח הבקרה.")


def main() -> None:
    """Application entry point."""
    st.set_page_config(page_title=APP_TITLE, page_icon="🏛️", layout="wide")
    try:
        initialize_database()
    except Exception:  # noqa: BLE001 - keep startup failures friendly
        logger.exception("DATABASE INITIALIZATION FAILED")
        st.error("שגיאה באתחול מסד הנתונים. ודא הרשאות כתיבה בתיקייה והפעל מחדש.")
        return
    _apply_theme()
    _init_session_state()

    user: User | None = st.session_state.get("user")
    if user is None:
        login_form.render()
        return

    _render_sidebar(user)
    _route(user)


if __name__ == "__main__":
    main()
