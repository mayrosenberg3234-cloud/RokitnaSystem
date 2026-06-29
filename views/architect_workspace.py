"""Architect workspace view.

Lets the architect document on-site field notes, upload project drawings and
document project changes that are sent to the client for approval.  Decisions
(Requirement 15) keep their own dedicated screen.
"""

from __future__ import annotations

import streamlit as st

from controllers.architect_controller import ArchitectController
from models.project import Project
from models.user import User
from utils.sql_log_widget import render_sql_query_log

ARCH_FEEDBACK_KEY = "architect_workspace_feedback"


class ArchitectWorkspace:
    """Render the architect's field-notes / drawings / changes workspace."""

    def __init__(self, controller: ArchitectController | None = None) -> None:
        self._controller = controller or ArchitectController()

    def _set_feedback(self, message: str) -> None:
        st.session_state[ARCH_FEEDBACK_KEY] = message

    def _display_pending_feedback(self) -> None:
        feedback = st.session_state.pop(ARCH_FEEDBACK_KEY, None)
        if feedback:
            st.success(feedback)

    def _display_reminders(self, user: User) -> None:
        result = self._controller.list_my_reminders(user)
        if not result.success or not result.data:
            return
        st.markdown("#### תזכורות מהמנהל")
        for reminder in result.data:
            st.info(f"{reminder.message}  \n*{reminder.created_at or ''}*")

    def _field_notes_section(self, user: User, project: Project) -> None:
        st.markdown("##### הערות שטח")
        with st.form(f"field_note_form_{project.project_id}", clear_on_submit=True):
            text = st.text_area(
                "תוכן ההערה",
                height=90,
                placeholder="לדוגמה: נמדד הפרש גובה ברצפה, נדרשת התאמה.",
            )
            if st.form_submit_button("הוסף הערה", use_container_width=True):
                res = self._controller.add_field_note(user, project.project_id, text)
                if res.success:
                    self._set_feedback(res.message)
                    st.rerun()
                st.error(res.message)

        notes = self._controller.list_field_notes(user.role, project.project_id).data or []
        if notes:
            st.dataframe(
                [
                    {"מזהה": n.note_id, "הערה": n.description, "נרשמה": n.created_at or "—"}
                    for n in notes
                ],
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.caption("עדיין לא תועדו הערות שטח לפרויקט זה.")

    def _drawings_section(self, user: User, project: Project) -> None:
        st.markdown("##### העלאת סרטוט")
        with st.form(f"drawing_form_{project.project_id}", clear_on_submit=True):
            uploaded = st.file_uploader(
                "בחר קובץ סרטוט", type=None, key=f"upl_{project.project_id}"
            )
            description = st.text_input("תיאור הסרטוט", placeholder="לדוגמה: תוכנית סלון")
            if st.form_submit_button("העלה סרטוט", use_container_width=True):
                if uploaded is None:
                    st.error("לא נבחר קובץ להעלאה")
                else:
                    res = self._controller.upload_drawing(
                        user,
                        project.project_id,
                        uploaded.name,
                        uploaded.getvalue(),
                        description,
                    )
                    if res.success:
                        self._set_feedback(res.message)
                        st.rerun()
                    st.error(res.message)

        drawings = self._controller.list_drawings(user.role, project.project_id).data or []
        if drawings:
            st.dataframe(
                [
                    {"מזהה": d.drawing_id, "קובץ": d.file_name, "תיאור": d.description or "—",
                     "הועלה": d.created_at or "—"}
                    for d in drawings
                ],
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.caption("עדיין לא הועלו סרטוטים לפרויקט זה.")

    def _changes_section(self, user: User, project: Project) -> None:
        st.markdown("##### תיעוד שינוי לאישור הלקוח")
        with st.form(f"change_form_{project.project_id}", clear_on_submit=True):
            description = st.text_area(
                "תיאור השינוי",
                height=90,
                placeholder="לדוגמה: הגדלת חלון הסלון לרוחב 2.4 מ'.",
            )
            cost = st.number_input("עלות השינוי (₪)", min_value=0.0, step=100.0)
            if st.form_submit_button("שלח שינוי לאישור", use_container_width=True):
                res = self._controller.document_change(
                    user, project.project_id, description, cost
                )
                if res.success:
                    self._set_feedback(res.message)
                    st.rerun()
                st.error(res.message)

        changes = self._controller.list_changes(user.role, project.project_id).data or []
        if changes:
            st.dataframe(
                [
                    {
                        "מזהה": c.change_id,
                        "תיאור": c.description,
                        "עלות": f"{c.cost:,.2f}",
                        "סטטוס": c.status.hebrew_label,
                    }
                    for c in changes
                ],
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.caption("עדיין לא תועדו שינויים לפרויקט זה.")

    def render(self, user: User) -> None:
        st.header("סטודיו אדריכלי")
        st.caption(
            "תיעוד הערות שטח, העלאת סרטוטים ותיעוד שינויים לאישור הלקוח."
        )
        self._display_pending_feedback()
        self._display_reminders(user)
        st.divider()

        projects_result = self._controller.list_projects(user.role)
        if not projects_result.success:
            st.error(projects_result.message)
            return
        projects: list[Project] = projects_result.data
        if not projects:
            st.info("אין פרויקטים זמינים.")
            return

        options = {f"{p.project_id} — {p.project_name}": p for p in projects}
        selected = st.selectbox("בחר פרויקט", list(options.keys()))
        project = options[selected]

        st.divider()
        self._field_notes_section(user, project)
        st.divider()
        self._drawings_section(user, project)
        st.divider()
        self._changes_section(user, project)
        st.divider()
        render_sql_query_log(clear_key="sql_clear_architect")


_architect_workspace = ArchitectWorkspace()


def render(user: User) -> None:
    """Render the architect workspace via the shared instance."""
    _architect_workspace.render(user)
