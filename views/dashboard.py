"""Dashboard view — the landing screen after login.

Shows a personalised welcome, headline KPIs (for the office manager) and
quick-access cards to the features the current user's role is permitted to use.
Clients land directly in their self-service portal.
"""

from __future__ import annotations

import streamlit as st

from controllers.manager_controller import ManagerController
from models.user import User
from utils.permissions import Permission, has_permission
from views import client_portal

_manager = ManagerController()

# (permission, page key, title, description)
_ACTION_CARDS = [
    (Permission.MANAGE_CLIENTS, "customers", "ניהול לקוחות",
     "יצירת לקוחות והפקת חשבון, קישור פרויקטים, פגישות ותזכורות"),
    (Permission.RECORD_DECISIONS, "decisions", "תיעוד החלטות",
     "רישום החלטות מקצועיות ושמירתן בהיסטוריית הפרויקט"),
    (Permission.MANAGE_PROJECT_CONTENT, "studio", "סטודיו אדריכלי",
     "הערות שטח, העלאת סרטוטים ותיעוד שינויים לאישור הלקוח"),
    (Permission.GENERATE_REPORTS, "reports", "הפקת דוחות",
     "דוח בקרה ניהולי ודוח פיננסי, כולל ייצוא ל-CSV"),
    (Permission.VIEW_OVERSIGHT, "oversight", "מעקב וניהול פעולות",
     "שליחת תזכורות וצפייה בכל פעולות האדריכלית והלקוחות"),
]


def _render_kpis(user: User) -> None:
    """Render headline KPI cards for the office manager."""
    result = _manager.dashboard_stats(user.role)
    if not result.success:
        return
    s = result.data
    st.markdown("##### תמונת מצב")
    cols = st.columns(4)
    cols[0].metric("פרויקטים פעילים", s["active_projects"])
    cols[1].metric("לקוחות", s["clients"])
    cols[2].metric("שינויים לאישור", s["pending_changes"])
    cols[3].metric("פניות פתוחות", s["open_inquiries"])
    st.divider()


def render(user: User) -> None:
    """Render the role-aware dashboard for ``user``."""
    st.title(f"שלום, {user.username}")
    st.caption(f"{user.role.hebrew_label} · מערכת הניהול של משרד רוקיטנה")
    st.divider()

    # A client's landing experience is the full self-service portal.
    if has_permission(user.role, Permission.VIEW_OWN_PROJECT):
        client_portal.render(user)
        return

    if has_permission(user.role, Permission.VIEW_OVERSIGHT):
        _render_kpis(user)

    available = [
        card for card in _ACTION_CARDS if has_permission(user.role, card[0])
    ]
    if not available:
        st.warning("אין פעולות זמינות עבור תפקיד זה.")
        return

    st.markdown("##### פעולות זמינות")
    # Two cards per row for a calm, readable grid.
    for i in range(0, len(available), 2):
        row = available[i : i + 2]
        cols = st.columns(2)
        for col, (_perm, page_key, title, desc) in zip(cols, row):
            with col:
                with st.container(border=True):
                    st.markdown(f"**{title}**")
                    st.caption(desc)
                    if st.button(
                        "מעבר",
                        key=f"go_{page_key}",
                        use_container_width=True,
                    ):
                        st.session_state["page"] = page_key
                        st.rerun()
