"""Reporting controller — Requirement 20.

Implements the management-control report exactly as described in the Part B
Requirement 20 Sequence Diagram:

    validate_report_criteria
        -> get_active_projects        (Project / DB.findActiveProjects)
        -> get_milestones_status      (Milestone / DB.findMilestones)
        -> get_payment_requests       (PaymentRequest / DB.findPaymentRequests)
        -> get_project_alerts         (Alert / DB.findAlerts)
        -> <<create>> Report
        -> Report.generate_management_report()
        -> save_report               (DB.saveReport)
        -> displayManagementReport

The office manager requests the report; the system collects information from the
*active* projects, aggregates it into a single management report, records the
generation in the database and returns the report for on-screen display and CSV
export.  Requires ``GENERATE_REPORTS`` / ``VIEW_REPORTS``.
"""

from __future__ import annotations

import csv
from datetime import datetime

from config import EXPORTS_DIR
from controllers import ActionResult
from models.alert import Alert
from models.milestone import Milestone
from models.payment_request import PaymentRequest
from models.project import Project
from models.report import Report, ReportSection, ReportStatus, ReportType
from models.user import RoleEnum
from utils.logger import get_logger
from utils.permissions import (
    Permission,
    PermissionError,
    require_permission,
)
from repositories.db_repository import DBRepository

logger = get_logger()


class ReportCriteriaError(Exception):
    """Raised when the requested report criteria are missing or unknown."""


class ReportController:
    """Coordinates management-report generation and CSV export (Requirement 20)."""

    # Report criteria the manager may choose. Kept as an explicit, validated set
    # so ``validate_report_criteria`` has a real "missing criteria" branch, which
    # maps to the ``alt [missing report criteria]`` fragment of the Sequence
    # Diagram.
    CRITERIA = {
        "active_projects": "דוח בקרה ניהולי — כל הפרויקטים הפעילים",
    }

    def __init__(self, repository: DBRepository | None = None) -> None:
        self._repository = repository or DBRepository()

    # ------------------------------------------------------------------ #
    # Controller self-messages in the Sequence Diagram
    # ------------------------------------------------------------------ #
    def _validate_report_criteria(self, criteria: str | None) -> str:
        """Validate the report criteria; raise on a missing/unknown value.

        Sequence Diagram self-message: ``validateReportCriteria()``.
        """
        if criteria is None or str(criteria).strip() == "":
            raise ReportCriteriaError("יש לבחור קריטריונים להפקת הדוח")
        criteria = str(criteria).strip()
        if criteria not in self.CRITERIA:
            raise ReportCriteriaError("הקריטריונים שנבחרו אינם נתמכים")
        return criteria

    def _get_active_projects(self) -> list[Project]:
        """Collect the active projects. SD: ``getActiveProjects()``."""
        return self._repository.find_active_projects()

    def _get_milestones_status(
        self, project_ids: list[int]
    ) -> list[Milestone]:
        """Collect milestones for the active projects. SD: ``getMilestonesStatus()``."""
        return self._repository.find_milestones_by_projects(project_ids)

    def _get_payment_requests(
        self, project_ids: list[int]
    ) -> list[PaymentRequest]:
        """Collect payment requests for the active projects. SD: ``getPaymentRequests()``."""
        return self._repository.find_payment_requests_by_projects(project_ids)

    def _get_project_alerts(self, project_ids: list[int]) -> list[Alert]:
        """Collect alerts for the active projects. SD: ``getProjectAlerts()``."""
        return self._repository.find_alerts_by_projects(project_ids)

    # ------------------------------------------------------------------ #
    # Section builders
    # ------------------------------------------------------------------ #
    def _client_name_map(self) -> dict[int, str]:
        return {c.client_id: c.name for c in self._repository.list_clients()}

    @staticmethod
    def _elapsed_days(created_at: str | None) -> str:
        """Return the number of days a project has been running, as text."""
        if not created_at:
            return "—"
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                started = datetime.strptime(created_at, fmt)
                break
            except ValueError:
                started = None
        if started is None:
            return "—"
        return str(max((datetime.now() - started).days, 0))

    def _projects_section(
        self, projects: list[Project], client_names: dict[int, str]
    ) -> ReportSection:
        rows = [
            [
                str(p.project_id),
                p.project_name,
                client_names.get(p.client_id, "—"),
                p.status.hebrew_label,
                p.created_at or "",
                self._elapsed_days(p.created_at),
            ]
            for p in projects
        ]
        return ReportSection(
            title="פרויקטים פעילים",
            headers=[
                "מזהה",
                "שם פרויקט",
                "לקוח",
                "סטטוס",
                "נפתח בתאריך",
                "זמן ביצוע (ימים)",
            ],
            rows=rows,
        )

    def _milestones_section(
        self, milestones: list[Milestone], project_names: dict[int, str]
    ) -> ReportSection:
        rows = [
            [
                str(m.milestone_id),
                project_names.get(m.project_id, str(m.project_id)),
                m.title,
                m.status.hebrew_label,
                m.created_at or "",
            ]
            for m in milestones
        ]
        return ReportSection(
            title="אבני דרך",
            headers=["מזהה", "פרויקט", "כותרת", "סטטוס", "נוצר בתאריך"],
            rows=rows,
        )

    def _payments_section(
        self,
        payment_requests: list[PaymentRequest],
        project_names: dict[int, str],
    ) -> ReportSection:
        request_ids = [req.request_id for req in payment_requests]
        paid_by_request: dict[int, float] = {}
        for payment in self._repository.find_payments_by_requests(request_ids):
            paid_by_request[payment.request_id] = (
                paid_by_request.get(payment.request_id, 0.0) + payment.amount
            )
        rows = [
            [
                str(req.request_id),
                project_names.get(req.project_id, str(req.project_id)),
                f"{req.amount:,.2f}",
                f"{paid_by_request.get(req.request_id, 0.0):,.2f}",
                req.status.hebrew_label,
            ]
            for req in payment_requests
        ]
        return ReportSection(
            title="דרישות תשלום ותשלומים",
            headers=["מזהה בקשה", "פרויקט", "סכום נדרש", "שולם", "סטטוס"],
            rows=rows,
        )

    def _alerts_section(
        self, alerts: list[Alert], project_names: dict[int, str]
    ) -> ReportSection:
        rows = [
            [
                str(a.alert_id),
                project_names.get(a.project_id, str(a.project_id)),
                a.message,
                a.created_at or "",
            ]
            for a in alerts
        ]
        return ReportSection(
            title="התראות",
            headers=["מזהה", "פרויקט", "הודעה", "נוצר בתאריך"],
            rows=rows,
        )

    # ------------------------------------------------------------------ #
    # Persistence — Sequence Diagram: saveReport(report) -> DB
    # ------------------------------------------------------------------ #
    def _save_report(self, report: Report) -> int:
        # Move to the persisted state *before* the insert so the stored row
        # reflects the final ReportSaved state (Requirement 20 State Diagram).
        report.mark_saved()
        return self._repository.save_report(report)

    # ------------------------------------------------------------------ #
    # Public use-case entry point
    # ------------------------------------------------------------------ #
    def generate_management_report(
        self, role: RoleEnum, criteria: str | None
    ) -> ActionResult:
        """Generate the management-control report end to end.

        Mirrors the Requirement 20 Sequence Diagram message order:
        permission -> validate criteria -> collect active projects ->
        milestones -> payment requests -> alerts -> create Report ->
        generate_management_report() -> save_report() -> result for the GUI.
        """
        try:
            require_permission(role, Permission.GENERATE_REPORTS)
        except PermissionError:
            logger.warning("PERMISSION DENIED (generate report): %s", role.value)
            return ActionResult.fail("אין לך הרשאה להפיק דוחות")

        # alt [missing report criteria] -> validationFailed
        try:
            criteria = self._validate_report_criteria(criteria)
        except ReportCriteriaError as exc:
            return ActionResult.fail(str(exc))

        # else [criteria valid]: collect data from the active projects.
        active_projects = self._get_active_projects()
        project_ids = [p.project_id for p in active_projects]
        project_names = {p.project_id: p.project_name for p in active_projects}

        milestones = self._get_milestones_status(project_ids)
        payment_requests = self._get_payment_requests(project_ids)
        alerts = self._get_project_alerts(project_ids)

        client_names = self._client_name_map()

        # <<create>> Report, then generateManagementReport().
        report = Report(report_type=ReportType.MANAGEMENT, criteria=criteria)
        report.generate_management_report(
            self._projects_section(active_projects, client_names),
            self._milestones_section(milestones, project_names),
            self._payments_section(payment_requests, project_names),
            self._alerts_section(alerts, project_names),
        )

        # saveReport(report) -> DB
        report_id = self._save_report(report)
        logger.info(
            "MANAGEMENT REPORT GENERATED: id=%s active_projects=%s",
            report_id,
            len(active_projects),
        )
        return ActionResult.ok("דוח הבקרה הניהולי הופק בהצלחה", data=report)

    def generate_financial_report(
        self, role: RoleEnum, criteria: str | None
    ) -> ActionResult:
        """Generate a financial report for the active projects.

        Breaks each active project's cost down by part (payment requests),
        shows what has been paid and what is still outstanding, lists the cost
        of documented project changes, and summarises the totals.
        """
        try:
            require_permission(role, Permission.GENERATE_REPORTS)
        except PermissionError:
            logger.warning("PERMISSION DENIED (financial report): %s", role.value)
            return ActionResult.fail("אין לך הרשאה להפיק דוחות")

        try:
            criteria = self._validate_report_criteria(criteria)
        except ReportCriteriaError as exc:
            return ActionResult.fail(str(exc))

        active_projects = self._get_active_projects()
        project_ids = [p.project_id for p in active_projects]
        project_names = {p.project_id: p.project_name for p in active_projects}

        payment_requests = self._get_payment_requests(project_ids)
        request_ids = [r.request_id for r in payment_requests]
        paid_by_request: dict[int, float] = {}
        for payment in self._repository.find_payments_by_requests(request_ids):
            paid_by_request[payment.request_id] = (
                paid_by_request.get(payment.request_id, 0.0) + payment.amount
            )
        changes = self._repository.find_changes_by_projects(project_ids)

        total_required = sum(r.amount for r in payment_requests)
        total_paid = sum(paid_by_request.values())
        total_outstanding = total_required - total_paid
        approved_change_cost = sum(
            c.cost for c in changes if c.status.value == "Approved"
        )

        parts_section = ReportSection(
            title="עלויות לפי חלקי הפרויקט",
            headers=["פרויקט", "חלק בפרויקט", "סכום נדרש", "שולם", "יתרה", "סטטוס"],
            rows=[
                [
                    project_names.get(r.project_id, str(r.project_id)),
                    r.description or "—",
                    f"{r.amount:,.2f}",
                    f"{paid_by_request.get(r.request_id, 0.0):,.2f}",
                    f"{r.amount - paid_by_request.get(r.request_id, 0.0):,.2f}",
                    r.status.hebrew_label,
                ]
                for r in payment_requests
            ],
        )
        changes_section = ReportSection(
            title="עלויות שינויים בפרויקט",
            headers=["פרויקט", "תיאור השינוי", "עלות", "סטטוס אישור"],
            rows=[
                [
                    project_names.get(c.project_id, str(c.project_id)),
                    c.description,
                    f"{c.cost:,.2f}",
                    c.status.hebrew_label,
                ]
                for c in changes
            ],
        )
        summary_section = ReportSection(
            title="סיכום פיננסי",
            headers=["מדד", "סכום"],
            rows=[
                ["סה\"כ נדרש לתשלום", f"{total_required:,.2f}"],
                ["סה\"כ שולם", f"{total_paid:,.2f}"],
                ["יתרה לתשלום", f"{total_outstanding:,.2f}"],
                ["עלויות שינויים מאושרים", f"{approved_change_cost:,.2f}"],
                [
                    "סה\"כ כולל שינויים מאושרים",
                    f"{total_required + approved_change_cost:,.2f}",
                ],
            ],
        )

        report = Report(report_type=ReportType.FINANCIAL, criteria=criteria)
        report.sections = [parts_section, changes_section, summary_section]
        report.summary = (
            f"נדרש: {total_required:,.2f} | שולם: {total_paid:,.2f} | "
            f"יתרה: {total_outstanding:,.2f} | "
            f"עלויות שינויים מאושרים: {approved_change_cost:,.2f}"
        )
        report.status = ReportStatus.GENERATED

        report_id = self._save_report(report)
        logger.info(
            "FINANCIAL REPORT GENERATED: id=%s active_projects=%s",
            report_id,
            len(active_projects),
        )
        return ActionResult.ok("הדוח הפיננסי הופק בהצלחה", data=report)

    def list_reports(self, role: RoleEnum) -> ActionResult:
        """Return the history of previously generated reports."""
        try:
            require_permission(role, Permission.VIEW_REPORTS)
        except PermissionError:
            return ActionResult.fail("אין לך הרשאה לצפות בדוחות")
        return ActionResult.ok(data=self._repository.list_reports())

    # ------------------------------------------------------------------ #
    # CSV export (bonus tool — produces a timestamped artefact)
    # ------------------------------------------------------------------ #
    def export_to_csv(self, report: Report) -> str:
        """Write the management report (all sections) to a CSV file.

        Returns the path of the written file.  The file is a verifiable,
        timestamped export artefact for the live demonstration.
        """
        EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
        file_path = EXPORTS_DIR / f"{report.report_type.value}.csv"
        # utf-8-sig keeps Hebrew readable when opened in Excel.
        with open(file_path, "w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.writer(handle)
            writer.writerow([report.report_type.hebrew_label])
            if report.criteria:
                writer.writerow([self.CRITERIA.get(report.criteria, report.criteria)])
            if report.generated_at:
                writer.writerow([f"הופק בתאריך: {report.generated_at}"])
            writer.writerow([report.summary])
            for section in report.sections:
                writer.writerow([])
                writer.writerow([section.title])
                writer.writerow(section.headers)
                writer.writerows(section.rows)
        logger.info("REPORT EXPORTED CSV: %s", file_path)
        return str(file_path)
