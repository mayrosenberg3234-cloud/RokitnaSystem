"""Manager oversight view.

Lets the office manager broadcast reminders to the architects, and review every
action across the office — the architect's professional content and the
clients' actions.  (Per-client reminders are sent from the client file.)
"""

from __future__ import annotations

import streamlit as st

from controllers.manager_controller import ManagerController
from models.user import RoleEnum, User
from utils.sql_log_widget import render_sql_query_log

OVERSIGHT_FEEDBACK_KEY = "oversight_feedback"


class ManagerOversight:
    """Render reminders broadcasting and cross-role activity review."""

    def __init__(self, controller: ManagerController | None = None) -> None:
        self._controller = controller or ManagerController()

    @staticmethod
    def _safe_value(value: object, default: str = "—") -> str:
        if value is None:
            return default
        if isinstance(value, str):
            return value or default
        return str(value)

    @staticmethod
    def _safe_status_label(status: object) -> str:
        if status is None:
            return "—"
        if hasattr(status, "hebrew_label"):
            return status.hebrew_label
        return str(status)

    @staticmethod
    def _format_cost(cost: object) -> str:
        try:
            return f"{float(cost):,.2f}"
        except Exception:
            return "0.00"

    def _display_pending_feedback(self) -> None:
        feedback = st.session_state.pop(OVERSIGHT_FEEDBACK_KEY, None)
        if feedback:
            st.success(feedback)

    def _reminders_section(self, user: User) -> None:
        st.markdown("#### שליחת תזכורת לאדריכלית")
        with st.form("reminder_architects_form", clear_on_submit=True):
            message = st.text_area(
                "תוכן התזכורת",
                height=90,
                placeholder="לדוגמה: נא להעלות את תוכניות החשמל עד יום חמישי.",
            )
            if st.form_submit_button("שלח תזכורת לאדריכלית", use_container_width=True):
                res = self._controller.send_reminder_to_architects(user, message)
                if res.success:
                    st.session_state[OVERSIGHT_FEEDBACK_KEY] = res.message
                    st.rerun()
                st.error(res.message)
        st.caption("תזכורת ללקוח מסוים נשלחת מתוך תיק הלקוח במסך ניהול הלקוחות.")

    def _architect_activity_section(self, user: User) -> None:
        st.markdown("#### פעולות האדריכלית")
        result = self._controller.list_architect_activity(user.role)
        if not result.success:
            st.caption(result.message)
            return
        data = result.data or {}

        st.markdown("##### הערות שטח")
        notes = data.get("field_notes") or []
        if notes:
            rows = []
            for n in notes:
                rows.append(
                    {
                        "פרויקט": self._safe_value(getattr(n, "project_id", None)),
                        "הערה": self._safe_value(getattr(n, "description", None)),
                        "נרשמה": self._safe_value(getattr(n, "created_at", None)),
                    }
                )
            st.dataframe(rows, use_container_width=True, hide_index=True)
        else:
            st.caption("אין הערות שטח.")

        st.markdown("##### סרטוטים")
        drawings = data.get("drawings") or []
        if drawings:
            rows = []
            for d in drawings:
                rows.append(
                    {
                        "פרויקט": self._safe_value(getattr(d, "project_id", None)),
                        "קובץ": self._safe_value(getattr(d, "file_name", None)),
                        "תיאור": self._safe_value(getattr(d, "description", None)),
                        "הועלה": self._safe_value(getattr(d, "created_at", None)),
                    }
                )
            st.dataframe(rows, use_container_width=True, hide_index=True)
        else:
            st.caption("אין סרטוטים.")

        st.markdown("##### שינויים שתועדו")
        changes = data.get("changes") or []
        if changes:
            rows = []
            for c in changes:
                rows.append(
                    {
                        "פרויקט": self._safe_value(getattr(c, "project_id", None)),
                        "תיאור": self._safe_value(getattr(c, "description", None)),
                        "עלות": self._format_cost(getattr(c, "cost", 0.0)),
                        "סטטוס": self._safe_status_label(getattr(c, "status", None)),
                    }
                )
            st.dataframe(rows, use_container_width=True, hide_index=True)
        else:
            st.caption("אין שינויים מתועדים.")

    def _system_activity_section(self, user: User) -> None:
        st.markdown("#### יומן פעילות המערכת")
        result = self._controller.list_recent_activity(user.role, limit=20)
        if not result.success:
            st.caption(result.message)
            return

        logs = result.data
        if logs:
            rows = []
            for row in logs:
                rows.append(
                    {
                        "תאריך": row.get("created_at") or "—",
                        "ישות": row.get("entity_type") or "—",
                        "מזהה": row.get("entity_id") or "—",
                        "פעולה": row.get("action") or "—",
                        "פרטים": row.get("details") or "—",
                    }
                )
            st.dataframe(rows, use_container_width=True, hide_index=True)
        else:
            st.caption("עדיין לא נרשמו פעולות במערכת.")

    def _client_credentials_section(self, user: User) -> None:
        st.markdown("#### פרטי כניסה של לקוחות")
        result = self._controller.list_client_credentials(user.role)
        if not result.success:
            st.caption(result.message)
            return
        rows_data = result.data or []
        if not rows_data:
            st.caption("אין לקוחות רשומים במערכת.")
            return
        rows = []
        for r in rows_data:
            rows.append({
                "שם לקוח": r.get("clientName") or "—",
                "שם משתמש": r.get("username") or "—",
                "סיסמה": r.get("plainPassword") or "לא זמינה (נוצר לפני עדכון המערכת)",
                "פעיל": "כן" if r.get("isActive") else "לא",
                "נוצר בתאריך": r.get("createdAt") or "—",
            })
        st.dataframe(rows, use_container_width=True, hide_index=True)

    def _sql_query_section(self) -> None:
        render_sql_query_log(clear_key="sql_clear_manager")

    def _client_activity_section(self, user: User) -> None:
        st.markdown("#### פעולות הלקוחות")
        result = self._controller.list_client_activity(user.role)
        if not result.success:
            st.caption(result.message)
            return
        data = result.data

        st.markdown("##### פניות מלקוחות")
        target_label = {
            RoleEnum.OFFICE_MANAGER.value: "מנהל",
            RoleEnum.ARCHITECT.value: "אדריכלית",
        }
        inquiries = data["inquiries"]
        if inquiries:
            rows = []
            for i in inquiries:
                rows.append(
                    {
                        "לקוח": self._safe_value(getattr(i, "client_id", None)),
                        "נמען": target_label.get(getattr(i, "target_role", ""), "—"),
                        "תוכן": self._safe_value(getattr(i, "content", None)),
                        "סטטוס": self._safe_status_label(getattr(i, "status", None)),
                        "נשלחה": self._safe_value(getattr(i, "created_at", None)),
                    }
                )
            st.dataframe(rows, use_container_width=True, hide_index=True)
        else:
            st.caption("אין פניות.")

        st.markdown("##### החלטות הלקוח על שינויים")
        decisions = data["change_decisions"]
        if decisions:
            rows = []
            for c in decisions:
                rows.append(
                    {
                        "פרויקט": self._safe_value(getattr(c, "project_id", None)),
                        "תיאור": self._safe_value(getattr(c, "description", None)),
                        "עלות": self._format_cost(getattr(c, "cost", None)),
                        "החלטה": self._safe_status_label(getattr(c, "status", None)),
                        "בתאריך": self._safe_value(getattr(c, "decided_at", None)),
                    }
                )
            st.dataframe(rows, use_container_width=True, hide_index=True)
        else:
            st.caption("אין החלטות על שינויים עדיין.")

    def render(self, user: User) -> None:
        st.header("מעקב וניהול פעולות")
        st.caption("שליחת תזכורות וצפייה בכל פעולות האדריכלית והלקוחות.")
        self._display_pending_feedback()
        st.divider()
        self._client_credentials_section(user)
        st.divider()
        self._reminders_section(user)
        st.divider()
        self._system_activity_section(user)
        st.divider()
        self._architect_activity_section(user)
        st.divider()
        self._sql_query_section()
        st.divider()
        self._client_activity_section(user)


_manager_oversight = ManagerOversight()


def render(user: User) -> None:
    """Render the manager oversight page via the shared instance."""
    _manager_oversight.render(user)
