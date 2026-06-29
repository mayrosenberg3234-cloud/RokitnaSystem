"""Professional decision-management GUI — Requirement 15.

``DecisionManagementForm`` is the User Class for recording a professional
architectural decision.  It deliberately contains presentation/input work only;
permission checks, validation, domain-object creation and SQL are delegated to
``DecisionController`` and ``DBRepository``.
"""

from __future__ import annotations

import streamlit as st

from controllers.decision_controller import DecisionController
from models.decision_entry_session import (
    DecisionEntrySession,
    DecisionEntryStatus,
)
from models.project import Project
from models.user import User

DECISION_ENTRY_SESSION_KEY = "decision_entry_session"
DECISION_FEEDBACK_KEY = "decision_management_feedback"


class DecisionManagementForm:
    """Render the Requirement 15 professional-decision workflow."""

    def __init__(self, controller: DecisionController | None = None) -> None:
        self._controller = controller or DecisionController()

    # ------------------------------------------------------------------ #
    # DecisionEntrySession / State Diagram support
    # ------------------------------------------------------------------ #
    def _entry_session(self) -> DecisionEntrySession:
        """Return the temporary state object for the current GUI workflow."""
        session = st.session_state.get(DECISION_ENTRY_SESSION_KEY)
        if not isinstance(session, DecisionEntrySession):
            session = DecisionEntrySession()
            st.session_state[DECISION_ENTRY_SESSION_KEY] = session
        return session

    def _reset_entry_session(self) -> None:
        """Start a new decision-entry lifecycle in ``DecisionDraft``."""
        st.session_state[DECISION_ENTRY_SESSION_KEY] = DecisionEntrySession()

    def _set_feedback(self, message: str, feedback_type: str = "success") -> None:
        """Preserve a user-facing message across Streamlit's rerun."""
        st.session_state[DECISION_FEEDBACK_KEY] = {
            "message": message,
            "type": feedback_type,
        }

    def _display_pending_feedback(self) -> None:
        """Display the latest recorded/invalid/save-failure feedback."""
        feedback = st.session_state.pop(DECISION_FEEDBACK_KEY, None)
        if feedback is None:
            return

        feedback_type = feedback["type"]
        if feedback_type == "success":
            self.display_save_confirmation(feedback["message"])
        elif feedback_type == "error":
            self.display_save_error(feedback["message"])
        else:
            self.display_validation_error(feedback["message"])

    def _display_state_caption(self) -> None:
        """Show the current decision-entry state without exposing technical data."""
        entry = self._entry_session()
        st.caption(f"מצב תהליך תיעוד ההחלטה: {entry.status.hebrew_label}")

    # ------------------------------------------------------------------ #
    # Public GUI messages named in the Sequence Diagram
    # ------------------------------------------------------------------ #
    def display_save_confirmation(self, message: str) -> None:
        """Show the successful end-of-process feedback to the architect."""
        st.success(message)

    def display_validation_error(self, message: str) -> None:
        """Show a friendly validation/business-rule message."""
        st.error(message)

    def display_save_error(self, message: str) -> None:
        """Show a friendly persistence failure message without a traceback."""
        st.error(message)

    # ------------------------------------------------------------------ #
    # Form / display methods
    # ------------------------------------------------------------------ #
    def display_decision_form(self, user: User, project: Project) -> None:
        """Render and submit the decision form for the selected project."""
        entry = self._entry_session()

        if entry.status == DecisionEntryStatus.CLOSED:
            st.info("תהליך התיעוד נסגר. ניתן להתחיל תיעוד החלטה חדש.")
            if st.button("התחל תיעוד החלטה חדש", key="new_decision_entry"):
                self._reset_entry_session()
                st.rerun()
            return

        st.markdown("#### תיעוד החלטה חדשה")
        st.caption(
            f"ההחלטה תישמר בפרויקט: **{project.project_name}** "
            "ותתווסף אוטומטית להיסטוריית השינויים שלו."
        )

        with st.form("decision_form", clear_on_submit=True):
            decision_text = st.text_area(
                "תוכן ההחלטה המקצועית",
                height=140,
                placeholder="לדוגמה: הוחלט להשתמש בתאורה חמה באזור הציבורי.",
            )
            submitted = st.form_submit_button("שמור החלטה", use_container_width=True)

        if not submitted:
            return

        # State Diagram: DecisionInvalid / DecisionSaveFailed -> DecisionDraft.
        if entry.status in {
            DecisionEntryStatus.INVALID,
            DecisionEntryStatus.SAVE_FAILED,
            DecisionEntryStatus.RECORDED,
        }:
            entry.return_to_draft()

        # State Diagram: DecisionDraft -> DecisionSaving.
        entry.begin_saving()

        # SD-R15: DecisionManagementForm -> DecisionController.save_decision()
        result = self._controller.save_decision(
            user.role,
            user.user_id,
            project.project_id,
            decision_text,
        )

        if result.success:
            # State Diagram: DecisionSaving -> DecisionRecorded.
            entry.mark_recorded()
            timestamps = result.data or {}
            decision_time = timestamps.get("decision_created_at", "")
            message = result.message
            if decision_time:
                message = f"{message} | חותמת זמן: {decision_time}"
            self._set_feedback(message, "success")
            st.rerun()

        failure = result.data or {}
        if failure.get("state") == "save_failed":
            # State Diagram: DecisionSaving -> DecisionSaveFailed.
            entry.mark_save_failed(result.message)
            self._set_feedback(result.message, "error")
        else:
            # State Diagram: DecisionDraft -> DecisionInvalid.
            entry.mark_invalid(result.message)
            self._set_feedback(result.message, "validation")
        st.rerun()

    def display_decisions(self, user: User, project_id: int) -> None:
        """Display recorded decisions for the selected project."""
        st.markdown("#### החלטות קודמות בפרויקט")
        result = self._controller.list_decisions(user.role, project_id)

        if not result.success:
            self.display_validation_error(result.message)
            return

        decisions = result.data
        if not decisions:
            st.caption("עדיין לא תועדו החלטות בפרויקט זה.")
            return

        table = [
            {
                "מזהה החלטה": decision.decision_id,
                "תוכן החלטה": decision.decision_text,
                "מזהה מתעד": decision.created_by_user_id,
                "נוצר בתאריך": decision.created_at or "—",
            }
            for decision in decisions
        ]
        st.dataframe(table, use_container_width=True, hide_index=True)

    def display_change_history(self, user: User, project_id: int) -> None:
        """Display the ChangeHistory records created for the selected project."""
        st.markdown("#### היסטוריית שינויים בפרויקט")
        result = self._controller.list_changes(user.role, project_id)

        if not result.success:
            self.display_validation_error(result.message)
            return

        changes = result.data
        if not changes:
            st.caption("עדיין לא תועדו שינויים בפרויקט זה.")
            return

        table = [
            {
                "מזהה שינוי": change.change_id,
                "מזהה החלטה": change.decision_id,
                "תיאור": change.description,
                "מזהה מתעד": change.created_by_user_id,
                "נוצר בתאריך": change.created_at or "—",
            }
            for change in changes
        ]
        st.dataframe(table, use_container_width=True, hide_index=True)

    def _display_close_action(self) -> None:
        """Expose the final transition DecisionRecorded -> DecisionClosed."""
        entry = self._entry_session()
        if entry.status != DecisionEntryStatus.RECORDED:
            return

        if st.button("סיום תיעוד החלטה", key="close_decision_entry"):
            entry.close()
            st.info("תהליך תיעוד ההחלטה נסגר.")
            st.rerun()

    def render(self, user: User) -> None:
        """Render the end-to-end Requirement 15 screen."""
        st.header("תיעוד החלטות מקצועיות בפרויקט")
        st.caption(
            "האדריכלית מתעדת החלטה מקצועית, מקשרת אותה לפרויקט ושומרת "
            "בו-זמנית גם את היסטוריית השינויים של הפרויקט."
        )
        st.divider()

        self._display_pending_feedback()
        self._display_state_caption()

        projects_result = self._controller.list_projects(user.role)
        if not projects_result.success:
            self.display_validation_error(projects_result.message)
            return

        projects: list[Project] = projects_result.data
        if not projects:
            st.info("אין פרויקטים זמינים לתיעוד החלטות.")
            return

        options = {
            f"{project.project_id} — {project.project_name}": project
            for project in projects
        }
        selected_label = st.selectbox("בחר פרויקט", list(options.keys()))
        project = options[selected_label]

        self.display_decision_form(user, project)
        st.divider()
        self.display_decisions(user, project.project_id)
        self.display_change_history(user, project.project_id)
        self._display_close_action()


# Compatibility wrapper keeps ``app.py`` unchanged while the UML User Class is
# now represented by a real Python class.
_decision_management_form = DecisionManagementForm()


def render(user: User) -> None:
    """Render Requirement 15 using the shared form object."""
    _decision_management_form.render(user)
