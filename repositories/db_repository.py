"""Data access layer — the *only* place SQL is executed.

``DBRepository`` exposes typed methods that map SQLite rows to and from the
domain models.  No other layer (and certainly no view) is permitted to run SQL
directly; this keeps persistence concerns isolated and testable.
"""

from __future__ import annotations

import sqlite3
from typing import Optional

from database import connection_scope, get_connection
from models.alert import Alert
from models.change import ChangeStatus, ProjectChange
from models.change_history import ChangeHistory
from models.client import Client, ClientStatus
from models.decision_log import DecisionLog
from models.drawing import Drawing
from models.field_note import FieldNote
from models.inquiry import ClientInquiry, InquiryStatus
from models.meeting import Meeting, MeetingStatus
from models.milestone import Milestone, MilestoneStatus
from models.payment import Payment
from models.payment_request import PaymentRequest, PaymentRequestStatus
from models.project import Project, ProjectStatus
from models.reminder import Reminder
from models.report import Report, ReportStatus, ReportType
from models.user import RoleEnum, User


class DBRepository:
    """Repository providing CRUD access to every table in the database."""

    # ------------------------------------------------------------------ #
    # Row -> model mappers
    # ------------------------------------------------------------------ #
    @staticmethod
    def _row_to_user(row: sqlite3.Row) -> User:
        keys = row.keys()
        return User(
            user_id=row["userId"],
            username=row["username"],
            password_hash=row["passwordHash"],
            role=RoleEnum.from_value(row["role"]),
            is_active=bool(row["isActive"]),
            client_id=row["clientId"] if "clientId" in keys else None,
            created_at=row["createdAt"],
        )

    @staticmethod
    def _row_to_client(row: sqlite3.Row) -> Client:
        return Client(
            client_id=row["clientId"],
            name=row["name"],
            phone=row["phone"],
            email=row["email"],
            status=ClientStatus(row["status"]),
            created_at=row["createdAt"],
            updated_at=row["updatedAt"],
        )

    @staticmethod
    def _row_to_project(row: sqlite3.Row) -> Project:
        return Project(
            project_id=row["projectId"],
            client_id=row["clientId"],
            project_name=row["projectName"],
            status=ProjectStatus(row["status"]),
            created_at=row["createdAt"],
            updated_at=row["updatedAt"],
        )

    @staticmethod
    def _row_to_decision(row: sqlite3.Row) -> DecisionLog:
        """Map a DecisionLog table row to its domain object."""
        return DecisionLog(
            decision_id=row["decisionId"],
            project_id=row["projectId"],
            created_by_user_id=row["createdByUserId"],
            decision_text=row["decisionText"],
            created_at=row["createdAt"],
        )

    @staticmethod
    def _row_to_change(row: sqlite3.Row) -> ChangeHistory:
        """Map a ChangeHistory table row to its domain object."""
        return ChangeHistory(
            change_id=row["changeId"],
            project_id=row["projectId"],
            decision_id=row["decisionId"],
            created_by_user_id=row["createdByUserId"],
            description=row["description"],
            created_at=row["createdAt"],
        )

    @staticmethod
    def _row_to_milestone(row: sqlite3.Row) -> Milestone:
        return Milestone(
            milestone_id=row["milestoneId"],
            project_id=row["projectId"],
            title=row["title"],
            status=MilestoneStatus(row["status"]),
            created_at=row["createdAt"],
        )

    @staticmethod
    def _row_to_payment_request(row: sqlite3.Row) -> PaymentRequest:
        keys = row.keys()
        return PaymentRequest(
            request_id=row["requestId"],
            project_id=row["projectId"],
            amount=row["amount"],
            description=row["description"] if "description" in keys else "",
            status=PaymentRequestStatus(row["status"]),
            created_at=row["createdAt"],
        )

    @staticmethod
    def _row_to_payment(row: sqlite3.Row) -> Payment:
        return Payment(
            payment_id=row["paymentId"],
            request_id=row["requestId"],
            amount=row["amount"],
            payment_date=row["paymentDate"],
        )

    @staticmethod
    def _row_to_alert(row: sqlite3.Row) -> Alert:
        return Alert(
            alert_id=row["alertId"],
            project_id=row["projectId"],
            message=row["message"],
            created_at=row["createdAt"],
        )

    @staticmethod
    def _row_to_meeting(row: sqlite3.Row) -> Meeting:
        keys = row.keys()
        return Meeting(
            meeting_id=row["meetingId"],
            project_id=row["projectId"],
            meeting_date=row["meetingDate"],
            meeting_time=row["meetingTime"],
            location=row["location"],
            summary=row["summary"],
            status=MeetingStatus(row["status"]) if "status" in keys else MeetingStatus.PROPOSED,
            created_at=row["createdAt"],
        )

    @staticmethod
    def _row_to_inquiry(row: sqlite3.Row) -> ClientInquiry:
        keys = row.keys()
        return ClientInquiry(
            inquiry_id=row["inquiryId"],
            client_id=row["clientId"],
            content=row["content"],
            target_role=row["targetRole"] if "targetRole" in keys else "OfficeManager",
            status=InquiryStatus(row["status"]),
            created_at=row["createdAt"],
        )

    @staticmethod
    def _row_to_drawing(row: sqlite3.Row) -> Drawing:
        return Drawing(
            drawing_id=row["drawingId"],
            project_id=row["projectId"],
            file_name=row["fileName"],
            stored_path=row["storedPath"],
            description=row["description"],
            created_by_user_id=row["createdByUserId"],
            created_at=row["createdAt"],
        )

    @staticmethod
    def _row_to_field_note(row: sqlite3.Row) -> FieldNote:
        return FieldNote(
            note_id=row["noteId"],
            project_id=row["projectId"],
            description=row["description"],
            created_by_user_id=row["createdByUserId"],
            created_at=row["createdAt"],
        )

    @staticmethod
    def _row_to_project_change(row: sqlite3.Row) -> ProjectChange:
        return ProjectChange(
            change_id=row["changeId"],
            project_id=row["projectId"],
            description=row["description"],
            cost=row["cost"],
            status=ChangeStatus(row["status"]),
            created_by_user_id=row["createdByUserId"],
            decided_by_user_id=row["decidedByUserId"],
            decided_at=row["decidedAt"],
            created_at=row["createdAt"],
        )

    @staticmethod
    def _row_to_reminder(row: sqlite3.Row) -> Reminder:
        return Reminder(
            reminder_id=row["reminderId"],
            message=row["message"],
            target_role=row["targetRole"],
            target_client_id=row["targetClientId"],
            created_by_user_id=row["createdByUserId"],
            created_at=row["createdAt"],
        )

    def _log_activity(
        self,
        connection: sqlite3.Connection,
        entity_type: str,
        entity_id: int,
        action: str,
        details: Optional[str] = None,
    ) -> None:
        """Persist an automatic activity entry with a timestamp."""
        connection.execute(
            """
            INSERT INTO ActivityLog (entityType, entityId, action, details, createdAt)
            VALUES (?, ?, ?, ?, datetime('now'))
            """,
            (entity_type, entity_id, action, details),
        )

    def list_activity_log(self, limit: int = 50) -> list[dict[str, object]]:
        """Return the most recent activity-log rows for UI display."""
        if limit is None or limit <= 0:
            return []

        connection = get_connection()
        try:
            rows = connection.execute(
                """
                SELECT
                    entityType,
                    entityId,
                    action,
                    details,
                    strftime('%Y-%m-%d %H:%M:%S', createdAt) AS createdAt
                FROM ActivityLog
                ORDER BY activityId DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
            return [
                {
                    "entity_type": row["entityType"],
                    "entity_id": row["entityId"],
                    "action": row["action"],
                    "details": row["details"],
                    "created_at": row["createdAt"],
                }
                for row in rows
            ]
        finally:
            connection.close()

    # ------------------------------------------------------------------ #
    # Users
    # ------------------------------------------------------------------ #
    def find_user_by_username(self, username: str) -> Optional[User]:
        """Return the user with ``username`` or ``None`` when absent."""
        connection = get_connection()
        try:
            row = connection.execute(
                "SELECT * FROM Users WHERE username = ?", (username,)
            ).fetchone()
            return self._row_to_user(row) if row else None
        finally:
            connection.close()

    def get_user(self, user_id: int) -> Optional[User]:
        """Return the user with ``user_id`` or ``None``.

        Requirement 15 records the authenticated architect's id with every
        decision and history entry.  The controller uses this method to make
        sure that a supplied actor id represents an active user with the same
        role used in the permission check.
        """
        connection = get_connection()
        try:
            row = connection.execute(
                "SELECT * FROM Users WHERE userId = ?", (user_id,)
            ).fetchone()
            return self._row_to_user(row) if row else None
        finally:
            connection.close()

    # ------------------------------------------------------------------ #
    # Clients
    # ------------------------------------------------------------------ #
    def list_clients(self) -> list[Client]:
        """Return every client ordered by creation time (newest first)."""
        connection = get_connection()
        try:
            rows = connection.execute(
                "SELECT * FROM Clients ORDER BY clientId DESC"
            ).fetchall()
            return [self._row_to_client(row) for row in rows]
        finally:
            connection.close()

    def get_client(self, client_id: int) -> Optional[Client]:
        """Return the client with ``client_id`` or ``None``."""
        connection = get_connection()
        try:
            row = connection.execute(
                "SELECT * FROM Clients WHERE clientId = ?", (client_id,)
            ).fetchone()
            return self._row_to_client(row) if row else None
        finally:
            connection.close()

    def find_client_by_phone(self, phone: str) -> Optional[Client]:
        """Return the client matching ``phone`` or ``None``."""
        connection = get_connection()
        try:
            row = connection.execute(
                "SELECT * FROM Clients WHERE phone = ?", (phone,)
            ).fetchone()
            return self._row_to_client(row) if row else None
        finally:
            connection.close()

    def find_client_by_email(self, email: str) -> Optional[Client]:
        """Return the client matching ``email`` (case-insensitive) or ``None``."""
        connection = get_connection()
        try:
            row = connection.execute(
                "SELECT * FROM Clients WHERE LOWER(email) = LOWER(?)", (email,)
            ).fetchone()
            return self._row_to_client(row) if row else None
        finally:
            connection.close()

    def create_client(self, client: Client) -> int:
        """Insert ``client`` and return the new client id."""
        with connection_scope() as connection:
            cursor = connection.execute(
                """
                INSERT INTO Clients (name, phone, email, status)
                VALUES (?, ?, ?, ?)
                """,
                (client.name, client.phone, client.email, client.status.value),
            )
            client_id = int(cursor.lastrowid)
            self._log_activity(
                connection,
                "Client",
                client_id,
                "create_client",
                f"נוצר לקוח: {client.name}",
            )
            return client_id

    def update_client(self, client: Client) -> None:
        """Persist changes to an existing ``client``."""
        with connection_scope() as connection:
            connection.execute(
                """
                UPDATE Clients
                SET name = ?, phone = ?, email = ?, status = ?,
                    updatedAt = datetime('now')
                WHERE clientId = ?
                """,
                (
                    client.name,
                    client.phone,
                    client.email,
                    client.status.value,
                    client.client_id,
                ),
            )
            self._log_activity(
                connection,
                "Client",
                client.client_id,
                "update_client",
                f"עודכן לקוח: {client.name}",
            )

    def delete_client(self, client_id: int) -> None:
        """Permanently delete a client and its linked login account.

        A client without projects has no foreign-key references except the
        login account provisioned for it on creation, so both are removed
        together in one transaction to preserve referential integrity.
        """
        connection = get_connection()
        try:
            connection.execute(
                "DELETE FROM Users WHERE clientId = ?", (client_id,)
            )
            connection.execute(
                "DELETE FROM Clients WHERE clientId = ?", (client_id,)
            )
            connection.commit()
        finally:
            connection.close()

    def archive_client(self, client_id: int) -> None:
        """Mark the client as archived instead of deleting it."""
        with connection_scope() as connection:
            connection.execute(
                """
                UPDATE Clients
                SET status = ?, updatedAt = datetime('now')
                WHERE clientId = ?
                """,
                (ClientStatus.ARCHIVED.value, client_id),
            )
            self._log_activity(
                connection,
                "Client",
                client_id,
                "archive_client",
                "הלקוח הועבר לארכיון",
            )

    # ------------------------------------------------------------------ #
    # Projects
    # ------------------------------------------------------------------ #
    def list_projects(self) -> list[Project]:
        """Return every project."""
        connection = get_connection()
        try:
            rows = connection.execute(
                "SELECT * FROM Projects ORDER BY projectId DESC"
            ).fetchall()
            return [self._row_to_project(row) for row in rows]
        finally:
            connection.close()

    def get_project(self, project_id: int) -> Optional[Project]:
        """Return the project with ``project_id`` or ``None``."""
        connection = get_connection()
        try:
            row = connection.execute(
                "SELECT * FROM Projects WHERE projectId = ?", (project_id,)
            ).fetchone()
            return self._row_to_project(row) if row else None
        finally:
            connection.close()

    def find_active_projects(self) -> list[Project]:
        """Return only the projects currently in the ``Active`` status.

        Requirement 20 collects management information from *active* projects.
        This is the ``findActiveProjects()`` database call in the Requirement 20
        Sequence Diagram.
        """
        connection = get_connection()
        try:
            rows = connection.execute(
                "SELECT * FROM Projects WHERE status = ? ORDER BY projectId DESC",
                (ProjectStatus.ACTIVE.value,),
            ).fetchall()
            return [self._row_to_project(row) for row in rows]
        finally:
            connection.close()

    def list_projects_by_client(self, client_id: int) -> list[Project]:
        """Return all projects belonging to ``client_id``."""
        connection = get_connection()
        try:
            rows = connection.execute(
                "SELECT * FROM Projects WHERE clientId = ? ORDER BY projectId DESC",
                (client_id,),
            ).fetchall()
            return [self._row_to_project(row) for row in rows]
        finally:
            connection.close()

    def count_projects_for_client(self, client_id: int) -> int:
        """Return the total number of projects linked to ``client_id``.

        Requirement 1 archives a client whenever *any* project references the
        client.  This protects historical records as well as active work and
        prevents a foreign-key violation during a permanent delete.
        """
        connection = get_connection()
        try:
            row = connection.execute(
                """
                SELECT COUNT(*) AS count
                FROM Projects
                WHERE clientId = ?
                """,
                (client_id,),
            ).fetchone()
            return int(row["count"])
        finally:
            connection.close()

    def create_project(self, project: Project) -> int:
        """Insert ``project`` and return its new id.

        Both timestamps are explicitly populated so a database migrated from an
        earlier project version (where ``updatedAt`` was added later) behaves
        exactly like a freshly created database.
        """
        with connection_scope() as connection:
            cursor = connection.execute(
                """
                INSERT INTO Projects
                (clientId, projectName, status, createdAt, updatedAt)
                VALUES (?, ?, ?, datetime('now'), datetime('now'))
                """,
                (project.client_id, project.project_name, project.status.value),
            )
            project_id = int(cursor.lastrowid)
            self._log_activity(
                connection,
                "Project",
                project_id,
                "create_project",
                f"נוצר פרויקט: {project.project_name}",
            )
            return project_id

    def update_project_status(
        self,
        project_id: int,
        new_status: ProjectStatus,
    ) -> bool:
        """Persist a status change and refresh the project's timestamp.

        The controller validates ownership, permissions and lifecycle rules
        before it reaches this method.  The repository only performs the SQL
        update and returns whether a project row was actually changed.
        """
        with connection_scope() as connection:
            cursor = connection.execute(
                """
                UPDATE Projects
                SET status = ?, updatedAt = datetime('now')
                WHERE projectId = ?
                """,
                (new_status.value, project_id),
            )
            if cursor.rowcount == 1:
                self._log_activity(
                    connection,
                    "Project",
                    project_id,
                    "update_project_status",
                    f"עודכן סטטוס לפרויקט ל-{new_status.value}",
                )
            return cursor.rowcount == 1

    # ------------------------------------------------------------------ #
    # Decision log and change history — Requirement 15
    # ------------------------------------------------------------------ #
    def save_decision_with_history(
        self,
        decision: DecisionLog,
        change: ChangeHistory,
    ) -> tuple[int, int]:
        """Atomically persist a decision and its matching audit entry.

        The two INSERT statements run in the same database transaction.  If
        either one fails, ``connection_scope`` rolls both changes back.  This
        guarantees the core Requirement 15 business rule: a saved decision is
        never left without a corresponding ChangeHistory record.
        """
        with connection_scope() as connection:
            decision_cursor = connection.execute(
                """
                INSERT INTO DecisionLog
                (projectId, createdByUserId, decisionText, createdAt)
                VALUES (?, ?, ?, datetime('now'))
                """,
                (
                    decision.project_id,
                    decision.created_by_user_id,
                    decision.decision_text,
                ),
            )
            decision_id = int(decision_cursor.lastrowid)
            decision.decision_id = decision_id

            change.decision_id = decision_id
            change_cursor = connection.execute(
                """
                INSERT INTO ChangeHistory
                (projectId, decisionId, createdByUserId, description, createdAt)
                VALUES (?, ?, ?, ?, datetime('now'))
                """,
                (
                    change.project_id,
                    change.decision_id,
                    change.created_by_user_id,
                    change.description,
                ),
            )
            change_id = int(change_cursor.lastrowid)
            change.change_id = change_id

            # Reading timestamps back from SQLite ensures that the in-memory
            # objects display exactly the same value shown in the live SELECT.
            decision_row = connection.execute(
                "SELECT createdAt FROM DecisionLog WHERE decisionId = ?",
                (decision_id,),
            ).fetchone()
            change_row = connection.execute(
                "SELECT createdAt FROM ChangeHistory WHERE changeId = ?",
                (change_id,),
            ).fetchone()
            decision.created_at = decision_row["createdAt"]
            change.created_at = change_row["createdAt"]

            self._log_activity(
                connection,
                "Decision",
                decision_id,
                "save_decision",
                f"נרשמה החלטה: {decision.decision_text}",
            )

        return decision_id, change_id

    def create_decision(self, decision: DecisionLog) -> int:
        """Insert one decision entry.

        This low-level method is kept for repository completeness.  The
        Requirement 15 use case itself must call ``save_decision_with_history``
        so that a decision and its audit entry are saved atomically.
        """
        connection = get_connection()
        try:
            cursor = connection.execute(
                """
                INSERT INTO DecisionLog
                (projectId, createdByUserId, decisionText, createdAt)
                VALUES (?, ?, ?, datetime('now'))
                """,
                (
                    decision.project_id,
                    decision.created_by_user_id,
                    decision.decision_text,
                ),
            )
            connection.commit()
            return int(cursor.lastrowid)
        finally:
            connection.close()

    def list_decisions_by_project(self, project_id: int) -> list[DecisionLog]:
        """Return every decision recorded against ``project_id``."""
        connection = get_connection()
        try:
            rows = connection.execute(
                """
                SELECT * FROM DecisionLog
                WHERE projectId = ?
                ORDER BY decisionId DESC
                """,
                (project_id,),
            ).fetchall()
            return [self._row_to_decision(row) for row in rows]
        finally:
            connection.close()

    def create_change(self, change: ChangeHistory) -> int:
        """Insert one audit entry.

        Kept for repository completeness.  Requirement 15 saves changes using
        ``save_decision_with_history`` rather than calling this method alone.
        """
        connection = get_connection()
        try:
            cursor = connection.execute(
                """
                INSERT INTO ChangeHistory
                (projectId, decisionId, createdByUserId, description, createdAt)
                VALUES (?, ?, ?, ?, datetime('now'))
                """,
                (
                    change.project_id,
                    change.decision_id,
                    change.created_by_user_id,
                    change.description,
                ),
            )
            connection.commit()
            return int(cursor.lastrowid)
        finally:
            connection.close()

    def list_changes_by_project(self, project_id: int) -> list[ChangeHistory]:
        """Return the change history for ``project_id``."""
        connection = get_connection()
        try:
            rows = connection.execute(
                """
                SELECT * FROM ChangeHistory
                WHERE projectId = ?
                ORDER BY changeId DESC
                """,
                (project_id,),
            ).fetchall()
            return [self._row_to_change(row) for row in rows]
        finally:
            connection.close()

    @staticmethod
    def _placeholders(count: int) -> str:
        """Return a comma-separated ``?`` list for a SQL ``IN`` clause."""
        return ", ".join("?" * count)

    # ------------------------------------------------------------------ #
    # Milestones
    # ------------------------------------------------------------------ #
    def list_milestones(self) -> list[Milestone]:
        """Return every milestone across all projects."""
        connection = get_connection()
        try:
            rows = connection.execute(
                "SELECT * FROM Milestones ORDER BY milestoneId DESC"
            ).fetchall()
            return [self._row_to_milestone(row) for row in rows]
        finally:
            connection.close()

    def find_milestones_by_projects(
        self, project_ids: list[int]
    ) -> list[Milestone]:
        """Return milestones belonging to the given projects.

        Requirement 20 Sequence Diagram: ``findMilestones(projectsList)``.
        """
        if not project_ids:
            return []
        connection = get_connection()
        try:
            rows = connection.execute(
                f"""
                SELECT * FROM Milestones
                WHERE projectId IN ({self._placeholders(len(project_ids))})
                ORDER BY milestoneId DESC
                """,
                project_ids,
            ).fetchall()
            return [self._row_to_milestone(row) for row in rows]
        finally:
            connection.close()

    # ------------------------------------------------------------------ #
    # Payment requests & payments
    # ------------------------------------------------------------------ #
    def list_payment_requests(self) -> list[PaymentRequest]:
        """Return every payment request."""
        connection = get_connection()
        try:
            rows = connection.execute(
                "SELECT * FROM PaymentRequests ORDER BY requestId DESC"
            ).fetchall()
            return [self._row_to_payment_request(row) for row in rows]
        finally:
            connection.close()

    def find_payment_requests_by_projects(
        self, project_ids: list[int]
    ) -> list[PaymentRequest]:
        """Return payment requests for the given projects.

        Requirement 20 Sequence Diagram: ``findPaymentRequests(projectsList)``.
        """
        if not project_ids:
            return []
        connection = get_connection()
        try:
            rows = connection.execute(
                f"""
                SELECT * FROM PaymentRequests
                WHERE projectId IN ({self._placeholders(len(project_ids))})
                ORDER BY requestId DESC
                """,
                project_ids,
            ).fetchall()
            return [self._row_to_payment_request(row) for row in rows]
        finally:
            connection.close()

    def create_payment_request(self, request: PaymentRequest) -> int:
        """Insert a payment request (a costed part of a project)."""
        connection = get_connection()
        try:
            cursor = connection.execute(
                """
                INSERT INTO PaymentRequests (projectId, amount, description, status)
                VALUES (?, ?, ?, ?)
                """,
                (
                    request.project_id,
                    request.amount,
                    request.description,
                    request.status.value,
                ),
            )
            connection.commit()
            return int(cursor.lastrowid)
        finally:
            connection.close()

    def create_payment(self, payment: Payment) -> int:
        """Record a payment made against a payment request."""
        connection = get_connection()
        try:
            cursor = connection.execute(
                "INSERT INTO Payments (requestId, amount) VALUES (?, ?)",
                (payment.request_id, payment.amount),
            )
            connection.commit()
            return int(cursor.lastrowid)
        finally:
            connection.close()

    def list_payments(self) -> list[Payment]:
        """Return every recorded payment."""
        connection = get_connection()
        try:
            rows = connection.execute(
                "SELECT * FROM Payments ORDER BY paymentId DESC"
            ).fetchall()
            return [self._row_to_payment(row) for row in rows]
        finally:
            connection.close()

    def find_payments_by_requests(
        self, request_ids: list[int]
    ) -> list[Payment]:
        """Return payments recorded against the given payment requests."""
        if not request_ids:
            return []
        connection = get_connection()
        try:
            rows = connection.execute(
                f"""
                SELECT * FROM Payments
                WHERE requestId IN ({self._placeholders(len(request_ids))})
                ORDER BY paymentId DESC
                """,
                request_ids,
            ).fetchall()
            return [self._row_to_payment(row) for row in rows]
        finally:
            connection.close()

    # ------------------------------------------------------------------ #
    # Alerts
    # ------------------------------------------------------------------ #
    def list_alerts(self) -> list[Alert]:
        """Return every alert."""
        connection = get_connection()
        try:
            rows = connection.execute(
                "SELECT * FROM Alerts ORDER BY alertId DESC"
            ).fetchall()
            return [self._row_to_alert(row) for row in rows]
        finally:
            connection.close()

    def find_alerts_by_projects(self, project_ids: list[int]) -> list[Alert]:
        """Return alerts raised for the given projects.

        Requirement 20 Sequence Diagram: ``findAlerts(projectsList)``.
        """
        if not project_ids:
            return []
        connection = get_connection()
        try:
            rows = connection.execute(
                f"""
                SELECT * FROM Alerts
                WHERE projectId IN ({self._placeholders(len(project_ids))})
                ORDER BY alertId DESC
                """,
                project_ids,
            ).fetchall()
            return [self._row_to_alert(row) for row in rows]
        finally:
            connection.close()

    # ------------------------------------------------------------------ #
    # Meetings (client portal)
    # ------------------------------------------------------------------ #
    def create_meeting(self, meeting: Meeting) -> int:
        """Insert a meeting scheduled against a project."""
        connection = get_connection()
        try:
            cursor = connection.execute(
                """
                INSERT INTO Meetings
                (projectId, meetingDate, meetingTime, location, summary, status)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    meeting.project_id,
                    meeting.meeting_date,
                    meeting.meeting_time,
                    meeting.location,
                    meeting.summary,
                    meeting.status.value,
                ),
            )
            connection.commit()
            return int(cursor.lastrowid)
        finally:
            connection.close()

    def confirm_meeting(self, meeting_id: int) -> bool:
        """Mark a meeting as confirmed by the client."""
        connection = get_connection()
        try:
            cursor = connection.execute(
                "UPDATE Meetings SET status = ? WHERE meetingId = ?",
                (MeetingStatus.CONFIRMED.value, meeting_id),
            )
            connection.commit()
            return cursor.rowcount == 1
        finally:
            connection.close()

    def get_meeting(self, meeting_id: int) -> Optional[Meeting]:
        """Return one meeting or ``None``."""
        connection = get_connection()
        try:
            row = connection.execute(
                "SELECT * FROM Meetings WHERE meetingId = ?", (meeting_id,)
            ).fetchone()
            return self._row_to_meeting(row) if row else None
        finally:
            connection.close()

    def list_upcoming_meetings_by_client(self, client_id: int) -> list[Meeting]:
        """Return future meetings (today onward) for a client's projects."""
        connection = get_connection()
        try:
            rows = connection.execute(
                """
                SELECT m.* FROM Meetings m
                JOIN Projects p ON p.projectId = m.projectId
                WHERE p.clientId = ? AND m.meetingDate >= date('now')
                ORDER BY m.meetingDate ASC, m.meetingTime ASC
                """,
                (client_id,),
            ).fetchall()
            return [self._row_to_meeting(row) for row in rows]
        finally:
            connection.close()

    def list_meetings_by_project(self, project_id: int) -> list[Meeting]:
        """Return every meeting scheduled for a project (newest first)."""
        connection = get_connection()
        try:
            rows = connection.execute(
                """
                SELECT * FROM Meetings
                WHERE projectId = ?
                ORDER BY meetingDate DESC, meetingTime DESC
                """,
                (project_id,),
            ).fetchall()
            return [self._row_to_meeting(row) for row in rows]
        finally:
            connection.close()

    # ------------------------------------------------------------------ #
    # Client inquiries (client portal)
    # ------------------------------------------------------------------ #
    def create_inquiry(self, inquiry: ClientInquiry) -> int:
        """Insert a client inquiry and return its new id."""
        connection = get_connection()
        try:
            cursor = connection.execute(
                """
                INSERT INTO Inquiries (clientId, content, targetRole, status)
                VALUES (?, ?, ?, ?)
                """,
                (
                    inquiry.client_id,
                    inquiry.content,
                    inquiry.target_role,
                    inquiry.status.value,
                ),
            )
            connection.commit()
            return int(cursor.lastrowid)
        finally:
            connection.close()

    def list_inquiries_by_client(self, client_id: int) -> list[ClientInquiry]:
        """Return all inquiries submitted by a client (newest first)."""
        connection = get_connection()
        try:
            rows = connection.execute(
                """
                SELECT * FROM Inquiries
                WHERE clientId = ?
                ORDER BY inquiryId DESC
                """,
                (client_id,),
            ).fetchall()
            return [self._row_to_inquiry(row) for row in rows]
        finally:
            connection.close()

    def list_inquiries_by_target_role(self, target_role: str) -> list[ClientInquiry]:
        """Return inquiries addressed to a given office role (newest first)."""
        connection = get_connection()
        try:
            rows = connection.execute(
                """
                SELECT * FROM Inquiries
                WHERE targetRole = ?
                ORDER BY inquiryId DESC
                """,
                (target_role,),
            ).fetchall()
            return [self._row_to_inquiry(row) for row in rows]
        finally:
            connection.close()

    def list_all_inquiries(self) -> list[ClientInquiry]:
        """Return every inquiry (office-manager oversight)."""
        connection = get_connection()
        try:
            rows = connection.execute(
                "SELECT * FROM Inquiries ORDER BY inquiryId DESC"
            ).fetchall()
            return [self._row_to_inquiry(row) for row in rows]
        finally:
            connection.close()

    # ------------------------------------------------------------------ #
    # Drawings (architect uploads; client views)
    # ------------------------------------------------------------------ #
    def create_drawing(self, drawing: Drawing) -> int:
        """Insert a drawing record and return its new id."""
        connection = get_connection()
        try:
            cursor = connection.execute(
                """
                INSERT INTO Drawings
                (projectId, fileName, storedPath, description, createdByUserId)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    drawing.project_id,
                    drawing.file_name,
                    drawing.stored_path,
                    drawing.description,
                    drawing.created_by_user_id,
                ),
            )
            connection.commit()
            return int(cursor.lastrowid)
        finally:
            connection.close()

    def list_drawings_by_project(self, project_id: int) -> list[Drawing]:
        """Return drawings attached to a project (newest first)."""
        connection = get_connection()
        try:
            rows = connection.execute(
                "SELECT * FROM Drawings WHERE projectId = ? ORDER BY drawingId DESC",
                (project_id,),
            ).fetchall()
            return [self._row_to_drawing(row) for row in rows]
        finally:
            connection.close()

    def list_drawings_by_client(self, client_id: int) -> list[Drawing]:
        """Return every drawing across the client's projects."""
        connection = get_connection()
        try:
            rows = connection.execute(
                """
                SELECT d.* FROM Drawings d
                JOIN Projects p ON p.projectId = d.projectId
                WHERE p.clientId = ?
                ORDER BY d.drawingId DESC
                """,
                (client_id,),
            ).fetchall()
            return [self._row_to_drawing(row) for row in rows]
        finally:
            connection.close()

    def list_all_drawings(self) -> list[Drawing]:
        """Return every drawing (office-manager oversight)."""
        connection = get_connection()
        try:
            rows = connection.execute(
                "SELECT * FROM Drawings ORDER BY drawingId DESC"
            ).fetchall()
            return [self._row_to_drawing(row) for row in rows]
        finally:
            connection.close()

    # ------------------------------------------------------------------ #
    # Field notes (architect)
    # ------------------------------------------------------------------ #
    def create_field_note(self, note: FieldNote) -> int:
        """Insert an on-site field note and return its new id."""
        connection = get_connection()
        try:
            cursor = connection.execute(
                """
                INSERT INTO FieldNotes (projectId, description, createdByUserId)
                VALUES (?, ?, ?)
                """,
                (note.project_id, note.description, note.created_by_user_id),
            )
            connection.commit()
            return int(cursor.lastrowid)
        finally:
            connection.close()

    def list_field_notes_by_project(self, project_id: int) -> list[FieldNote]:
        """Return field notes for a project (newest first)."""
        connection = get_connection()
        try:
            rows = connection.execute(
                "SELECT * FROM FieldNotes WHERE projectId = ? ORDER BY noteId DESC",
                (project_id,),
            ).fetchall()
            return [self._row_to_field_note(row) for row in rows]
        finally:
            connection.close()

    def list_all_field_notes(self) -> list[FieldNote]:
        """Return every field note (office-manager oversight)."""
        connection = get_connection()
        try:
            rows = connection.execute(
                "SELECT * FROM FieldNotes ORDER BY noteId DESC"
            ).fetchall()
            return [self._row_to_field_note(row) for row in rows]
        finally:
            connection.close()

    # ------------------------------------------------------------------ #
    # Project changes / approvals
    # ------------------------------------------------------------------ #
    def create_project_change(self, change: ProjectChange) -> int:
        """Insert a documented project change awaiting approval."""
        connection = get_connection()
        try:
            cursor = connection.execute(
                """
                INSERT INTO Changes
                (projectId, description, cost, status, createdByUserId)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    change.project_id,
                    change.description,
                    change.cost,
                    change.status.value,
                    change.created_by_user_id,
                ),
            )
            connection.commit()
            return int(cursor.lastrowid)
        finally:
            connection.close()

    def get_change(self, change_id: int) -> Optional[ProjectChange]:
        """Return one change or ``None``."""
        connection = get_connection()
        try:
            row = connection.execute(
                "SELECT * FROM Changes WHERE changeId = ?", (change_id,)
            ).fetchone()
            return self._row_to_project_change(row) if row else None
        finally:
            connection.close()

    def set_change_decision(
        self, change_id: int, status: ChangeStatus, decided_by_user_id: int
    ) -> bool:
        """Record the client's approval/rejection of a change."""
        connection = get_connection()
        try:
            cursor = connection.execute(
                """
                UPDATE Changes
                SET status = ?, decidedByUserId = ?, decidedAt = datetime('now')
                WHERE changeId = ?
                """,
                (status.value, decided_by_user_id, change_id),
            )
            connection.commit()
            return cursor.rowcount == 1
        finally:
            connection.close()

    def list_project_changes_by_project(self, project_id: int) -> list[ProjectChange]:
        """Return documented changes for a project (newest first)."""
        connection = get_connection()
        try:
            rows = connection.execute(
                "SELECT * FROM Changes WHERE projectId = ? ORDER BY changeId DESC",
                (project_id,),
            ).fetchall()
            return [self._row_to_project_change(row) for row in rows]
        finally:
            connection.close()

    def list_changes_by_client(self, client_id: int) -> list[ProjectChange]:
        """Return every documented change across a client's projects."""
        connection = get_connection()
        try:
            rows = connection.execute(
                """
                SELECT c.* FROM Changes c
                JOIN Projects p ON p.projectId = c.projectId
                WHERE p.clientId = ?
                ORDER BY c.changeId DESC
                """,
                (client_id,),
            ).fetchall()
            return [self._row_to_project_change(row) for row in rows]
        finally:
            connection.close()

    def find_changes_by_projects(self, project_ids: list[int]) -> list[ProjectChange]:
        """Return changes belonging to the given projects (for the report)."""
        if not project_ids:
            return []
        connection = get_connection()
        try:
            rows = connection.execute(
                f"""
                SELECT * FROM Changes
                WHERE projectId IN ({self._placeholders(len(project_ids))})
                ORDER BY changeId DESC
                """,
                project_ids,
            ).fetchall()
            return [self._row_to_project_change(row) for row in rows]
        finally:
            connection.close()

    def list_all_changes(self) -> list[ProjectChange]:
        """Return every documented change (office-manager oversight)."""
        connection = get_connection()
        try:
            rows = connection.execute(
                "SELECT * FROM Changes ORDER BY changeId DESC"
            ).fetchall()
            return [self._row_to_project_change(row) for row in rows]
        finally:
            connection.close()

    # ------------------------------------------------------------------ #
    # Reminders
    # ------------------------------------------------------------------ #
    def create_reminder(self, reminder: Reminder) -> int:
        """Insert a reminder and return its new id."""
        connection = get_connection()
        try:
            cursor = connection.execute(
                """
                INSERT INTO Reminders
                (message, targetRole, targetClientId, createdByUserId)
                VALUES (?, ?, ?, ?)
                """,
                (
                    reminder.message,
                    reminder.target_role,
                    reminder.target_client_id,
                    reminder.created_by_user_id,
                ),
            )
            connection.commit()
            return int(cursor.lastrowid)
        finally:
            connection.close()

    def list_reminders_for_client(self, client_id: int) -> list[Reminder]:
        """Return reminders addressed to a specific client (newest first)."""
        connection = get_connection()
        try:
            rows = connection.execute(
                """
                SELECT * FROM Reminders
                WHERE targetRole = 'Client' AND targetClientId = ?
                ORDER BY reminderId DESC
                """,
                (client_id,),
            ).fetchall()
            return [self._row_to_reminder(row) for row in rows]
        finally:
            connection.close()

    def list_reminders_for_role(self, target_role: str) -> list[Reminder]:
        """Return reminders broadcast to a role (e.g. all architects)."""
        connection = get_connection()
        try:
            rows = connection.execute(
                """
                SELECT * FROM Reminders
                WHERE targetRole = ? AND targetClientId IS NULL
                ORDER BY reminderId DESC
                """,
                (target_role,),
            ).fetchall()
            return [self._row_to_reminder(row) for row in rows]
        finally:
            connection.close()

    def list_all_reminders(self) -> list[Reminder]:
        """Return every reminder (office-manager oversight)."""
        connection = get_connection()
        try:
            rows = connection.execute(
                "SELECT * FROM Reminders ORDER BY reminderId DESC"
            ).fetchall()
            return [self._row_to_reminder(row) for row in rows]
        finally:
            connection.close()

    # ------------------------------------------------------------------ #
    # User account creation (office manager provisions client logins)
    # ------------------------------------------------------------------ #
    def create_user(self, user: User) -> int:
        """Insert a new user account and return its id."""
        connection = get_connection()
        try:
            cursor = connection.execute(
                """
                INSERT INTO Users (username, passwordHash, role, isActive, clientId)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    user.username,
                    user.password_hash,
                    user.role.value,
                    1 if user.is_active else 0,
                    user.client_id,
                ),
            )
            connection.commit()
            return int(cursor.lastrowid)
        finally:
            connection.close()

    # ------------------------------------------------------------------ #
    # Reports — Requirement 20
    # ------------------------------------------------------------------ #
    def save_report(self, report: Report) -> int:
        """Persist a generated report and return its new id.

        Requirement 20 Sequence Diagram: ``saveReport(report)`` -> DB.  The
        report's type, criteria and status are stored so the generation is
        recorded in the organisation's long-term memory, and ``generatedAt``
        provides the exact second-level timestamp shown during the live demo.
        """
        connection = get_connection()
        try:
            cursor = connection.execute(
                """
                INSERT INTO Reports (reportType, criteria, status, generatedAt)
                VALUES (?, ?, ?, datetime('now'))
                """,
                (
                    report.report_type.value,
                    report.criteria,
                    report.status.value,
                ),
            )
            connection.commit()
            report_id = int(cursor.lastrowid)
            row = connection.execute(
                "SELECT generatedAt FROM Reports WHERE reportId = ?",
                (report_id,),
            ).fetchone()
            report.report_id = report_id
            report.generated_at = row["generatedAt"]
            return report_id
        finally:
            connection.close()

    def list_reports(self) -> list[Report]:
        """Return the history of generated reports (newest first)."""
        connection = get_connection()
        try:
            rows = connection.execute(
                "SELECT * FROM Reports ORDER BY reportId DESC"
            ).fetchall()
            return [
                Report(
                    report_id=row["reportId"],
                    report_type=ReportType(row["reportType"]),
                    criteria=row["criteria"] if "criteria" in row.keys() else None,
                    status=ReportStatus(row["status"])
                    if ("status" in row.keys() and row["status"])
                    else ReportStatus.SAVED,
                    generated_at=row["generatedAt"],
                )
                for row in rows
            ]
        finally:
            connection.close()
