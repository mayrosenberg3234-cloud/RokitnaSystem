"""Report domain model — Requirement 20.

A ``Report`` is the management-control report described in Part B (Diagram 3 and
the Requirement 20 Sequence Diagram).  It aggregates data collected from the
active projects — milestones, payment requests and alerts — into a single
management report that the office manager can view and export.

The class diagram gives the report its own behaviour:
``generate_management_report()`` assembles the collected data into displayable
sections, while the persisted lifecycle status moves Requested -> Generated ->
Saved exactly as in the Requirement 20 State Diagram.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class ReportType(str, Enum):
    """The kind of report the system produces.

    The implemented Requirement 20 use case is the aggregated management report.
    """

    MANAGEMENT = "ManagementReport"
    FINANCIAL = "FinancialReport"

    @property
    def hebrew_label(self) -> str:
        labels = {
            ReportType.MANAGEMENT: "דוח בקרה ניהולי",
            ReportType.FINANCIAL: "דוח פיננסי",
        }
        return labels[self]


class ReportStatus(str, Enum):
    """Persisted lifecycle status of a report (Requirement 20 State Diagram)."""

    REQUESTED = "Requested"
    GENERATED = "Generated"
    SAVED = "Saved"

    @property
    def hebrew_label(self) -> str:
        labels = {
            ReportStatus.REQUESTED: "התבקש",
            ReportStatus.GENERATED: "הופק",
            ReportStatus.SAVED: "נשמר",
        }
        return labels[self]


@dataclass
class ReportSection:
    """One titled table inside the management report."""

    title: str
    headers: list[str]
    rows: list[list[str]]


@dataclass
class Report:
    """A management-control report aggregated from active projects.

    Attributes mirror the Part B class diagram: ``report_type`` (type),
    ``generated_at`` (createDate), ``criteria`` and ``status``.  The body of the
    report is held in ``sections`` and built by ``generate_management_report``.
    """

    report_type: ReportType = ReportType.MANAGEMENT
    criteria: Optional[str] = None
    status: ReportStatus = ReportStatus.REQUESTED
    report_id: Optional[int] = None
    generated_at: Optional[str] = None
    sections: list[ReportSection] = field(default_factory=list)
    summary: str = ""

    def generate_management_report(
        self,
        projects_section: ReportSection,
        milestones_section: ReportSection,
        payments_section: ReportSection,
        alerts_section: ReportSection,
    ) -> None:
        """Assemble the collected data into the management report sections.

        This is the ``generateManagementReport()`` message on the ``Report``
        object in the Requirement 20 Sequence Diagram.  The controller has
        already gathered the active projects and their milestones, payment
        requests and alerts; here the report object turns them into the
        displayable structure and moves itself to the ``Generated`` state.
        """
        self.sections = [
            projects_section,
            milestones_section,
            payments_section,
            alerts_section,
        ]
        self.summary = (
            f"פרויקטים פעילים: {len(projects_section.rows)} | "
            f"אבני דרך: {len(milestones_section.rows)} | "
            f"דרישות תשלום: {len(payments_section.rows)} | "
            f"התראות: {len(alerts_section.rows)}"
        )
        self.status = ReportStatus.GENERATED

    def mark_saved(self) -> None:
        """Move to the persisted ``Saved`` state after the database write."""
        self.status = ReportStatus.SAVED
