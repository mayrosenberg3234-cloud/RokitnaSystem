"""Reports GUI — Requirement 20.

``ReportDashboardForm`` is the User Class of the management-report workflow.
It contains presentation and input handling only; criteria validation, data
collection, aggregation and persistence are delegated to ``ReportController``.

The public methods map directly to the Requirement 20 Sequence Diagram:
``openReportsDashboard`` (render), ``displayReportOptions``,
``selectReportCriteria``, ``displayValidationError`` and
``displayManagementReport``.
"""

from __future__ import annotations

import streamlit as st

from controllers.report_controller import ReportController
from models.report import Report, ReportType
from models.user import User

LAST_REPORT_KEY = "last_report"


class ReportDashboardForm:
    """Render the Requirement 20 management-report screen for a manager."""

    def __init__(self, controller: ReportController | None = None) -> None:
        self._controller = controller or ReportController()

    # ------------------------------------------------------------------ #
    # Sequence Diagram messages on the form lifeline
    # ------------------------------------------------------------------ #
    def display_report_options(self) -> str:
        """Show the available report criteria and return the manager's choice.

        Implements ``displayReportOptions()`` + ``selectReportCriteria()``.  A
        leading placeholder lets the manager submit without a choice so the
        ``validateReportCriteria`` "missing criteria" branch is reachable.
        """
        st.markdown("#### בחירת קריטריונים לדוח")
        placeholder = "— בחר/י קריטריון —"
        labels = {placeholder: ""}
        labels.update(
            {label: key for key, label in self._controller.CRITERIA.items()}
        )
        selected_label = st.selectbox("קריטריון הדוח", list(labels.keys()))
        return labels[selected_label]

    def display_validation_error(self, message: str) -> None:
        """Show a friendly criteria-validation message (no traceback)."""
        st.error(message)

    def display_management_report(self, report: Report) -> None:
        """Render the generated management report and its CSV export."""
        st.divider()
        st.markdown(f"#### {report.report_type.hebrew_label}")
        st.caption(report.summary)
        if report.generated_at:
            st.caption(f"הופק בתאריך: {report.generated_at}")

        any_rows = False
        for section in report.sections:
            st.markdown(f"##### {section.title}")
            if section.rows:
                any_rows = True
                table = [dict(zip(section.headers, row)) for row in section.rows]
                st.dataframe(table, use_container_width=True, hide_index=True)
            else:
                st.info("אין נתונים להצגה בחלק זה.")

        if not any_rows:
            st.info("אין כרגע פרויקטים פעילים עם נתונים לדוח.")

        csv_path = self._controller.export_to_csv(report)
        with open(csv_path, "rb") as handle:
            st.download_button(
                "📥 הורד את הדוח כקובץ CSV",
                data=handle.read(),
                file_name=f"{report.report_type.value}.csv",
                mime="text/csv",
                use_container_width=True,
            )

    # ------------------------------------------------------------------ #
    # History
    # ------------------------------------------------------------------ #
    def _display_history(self, user: User) -> None:
        st.divider()
        st.markdown("#### היסטוריית דוחות שהופקו")
        result = self._controller.list_reports(user.role)
        if not result.success:
            st.caption(result.message)
            return
        reports = result.data
        if not reports:
            st.caption("עדיין לא הופקו דוחות.")
            return
        table = [
            {
                "מזהה": r.report_id,
                "סוג דוח": r.report_type.hebrew_label,
                "סטטוס": r.status.hebrew_label,
                "הופק בתאריך": r.generated_at,
            }
            for r in reports
        ]
        st.dataframe(table, use_container_width=True, hide_index=True)

    # ------------------------------------------------------------------ #
    # openReportsDashboard()
    # ------------------------------------------------------------------ #
    def render(self, user: User) -> None:
        """Render the end-to-end Requirement 20 screen."""
        st.header("הפקת דוחות בקרה וניהול")
        st.caption(
            "המערכת אוספת מידע מהפרויקטים הפעילים — אבני דרך, דרישות תשלום, "
            "תשלומים והתראות — ומפיקה דוח בקרה ניהולי אחד."
        )

        report_kind = st.radio(
            "סוג הדוח",
            options=[ReportType.MANAGEMENT, ReportType.FINANCIAL],
            format_func=lambda rt: rt.hebrew_label,
            horizontal=True,
        )
        criteria = self.display_report_options()

        if st.button("הפק דוח", use_container_width=True):
            if report_kind == ReportType.FINANCIAL:
                result = self._controller.generate_financial_report(
                    user.role, criteria
                )
            else:
                # SD-R20: ReportDashboardForm -> ReportController.generate_management_report()
                result = self._controller.generate_management_report(
                    user.role, criteria
                )
            if result.success:
                st.session_state[LAST_REPORT_KEY] = result.data
                st.success(result.message)
            else:
                # alt [missing report criteria] -> displayValidationError()
                st.session_state[LAST_REPORT_KEY] = None
                self.display_validation_error(result.message)

        report = st.session_state.get(LAST_REPORT_KEY)
        if isinstance(report, Report):
            self.display_management_report(report)

        self._display_history(user)


# Compatibility wrapper: app.py keeps calling report_dashboard.render(user).
_report_dashboard_form = ReportDashboardForm()


def render(user: User) -> None:
    """Render Requirement 20 via the ReportDashboardForm User Class."""
    _report_dashboard_form.render(user)
