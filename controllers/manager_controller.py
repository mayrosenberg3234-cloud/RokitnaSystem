"""Office-manager oversight controller.

Lets the office manager send reminders to a client or to the architects, and
review every action performed across the office — the architect's professional
content (decisions, field notes, drawings, changes) and the clients' actions
(inquiries, change approvals).
"""

from __future__ import annotations

from dataclasses import dataclass

from controllers import ActionResult
from models.reminder import Reminder
from models.user import RoleEnum, User
from repositories.db_repository import DBRepository
from services.validation_service import ValidationError, require_non_empty
from utils.logger import get_logger
from utils.permissions import Permission, PermissionError, require_permission

logger = get_logger()


@dataclass
class OversightData:
    """Everything the office manager reviews in one structured payload."""

    decisions: list
    field_notes: list
    drawings: list
    changes: list
    inquiries: list


class ManagerController:
    """Coordinates reminders and cross-role oversight for the office manager."""

    def __init__(self, repository: DBRepository | None = None) -> None:
        self._repository = repository or DBRepository()

    # ------------------------------------------------------------------ #
    # Reminders
    # ------------------------------------------------------------------ #
    def send_reminder_to_client(
        self, user: User, client_id: int, message: str
    ) -> ActionResult:
        """Send a reminder addressed to one specific client."""
        try:
            require_permission(user.role, Permission.SEND_REMINDERS)
            message = require_non_empty(message, "תוכן התזכורת")
        except PermissionError:
            logger.warning("PERMISSION DENIED (reminder->client): %s", user.role.value)
            return ActionResult.fail("אין לך הרשאה לשלוח תזכורות")
        except ValidationError as exc:
            return ActionResult.fail(str(exc))

        if self._repository.get_client(client_id) is None:
            return ActionResult.fail("הלקוח לא נמצא")

        reminder = Reminder(
            message=message,
            created_by_user_id=user.user_id,
            target_role=RoleEnum.CLIENT.value,
            target_client_id=client_id,
        )
        reminder_id = self._repository.create_reminder(reminder)
        logger.info("REMINDER->CLIENT: id=%s client=%s", reminder_id, client_id)
        return ActionResult.ok("התזכורת נשלחה ללקוח", data=reminder_id)

    def send_reminder_to_architects(
        self, user: User, message: str
    ) -> ActionResult:
        """Send a reminder addressed to the architects."""
        try:
            require_permission(user.role, Permission.SEND_REMINDERS)
            message = require_non_empty(message, "תוכן התזכורת")
        except PermissionError:
            logger.warning("PERMISSION DENIED (reminder->architect): %s", user.role.value)
            return ActionResult.fail("אין לך הרשאה לשלוח תזכורות")
        except ValidationError as exc:
            return ActionResult.fail(str(exc))

        reminder = Reminder(
            message=message,
            created_by_user_id=user.user_id,
            target_role=RoleEnum.ARCHITECT.value,
            target_client_id=None,
        )
        reminder_id = self._repository.create_reminder(reminder)
        logger.info("REMINDER->ARCHITECTS: id=%s", reminder_id)
        return ActionResult.ok("התזכורת נשלחה לאדריכלית", data=reminder_id)

    # ------------------------------------------------------------------ #
    # Dashboard KPIs
    # ------------------------------------------------------------------ #
    def dashboard_stats(self, role: RoleEnum) -> ActionResult:
        """Return headline counts for the office-manager dashboard cards."""
        try:
            require_permission(role, Permission.VIEW_OVERSIGHT)
        except PermissionError:
            return ActionResult.fail("אין לך הרשאה לצפות בנתוני הסיכום")

        active_projects = len(self._repository.find_active_projects())
        clients = len(self._repository.list_clients())
        pending_changes = len(
            [c for c in self._repository.list_all_changes() if c.status.value == "Pending"]
        )
        open_inquiries = len(
            [i for i in self._repository.list_all_inquiries() if i.status.value == "Open"]
        )
        return ActionResult.ok(
            data={
                "active_projects": active_projects,
                "clients": clients,
                "pending_changes": pending_changes,
                "open_inquiries": open_inquiries,
            }
        )

    # ------------------------------------------------------------------ #
    # Oversight
    # ------------------------------------------------------------------ #
    def list_architect_activity(self, role: RoleEnum) -> ActionResult:
        """Return all professional content produced by the architect."""
        try:
            require_permission(role, Permission.VIEW_OVERSIGHT)
        except PermissionError:
            logger.warning("PERMISSION DENIED (oversight architect): %s", role.value)
            return ActionResult.fail("אין לך הרשאה לצפות בפעולות האדריכלית")

        data = {
            "field_notes": self._repository.list_all_field_notes(),
            "drawings": self._repository.list_all_drawings(),
            "changes": self._repository.list_all_changes(),
        }
        return ActionResult.ok(data=data)

    def list_client_activity(self, role: RoleEnum) -> ActionResult:
        """Return all client actions (inquiries + change decisions)."""
        try:
            require_permission(role, Permission.VIEW_OVERSIGHT)
        except PermissionError:
            logger.warning("PERMISSION DENIED (oversight client): %s", role.value)
            return ActionResult.fail("אין לך הרשאה לצפות בפעולות הלקוח")

        changes = self._repository.list_all_changes()
        decided = [c for c in changes if c.decided_at is not None]
        data = {
            "inquiries": self._repository.list_all_inquiries(),
            "change_decisions": decided,
            "reminders": self._repository.list_all_reminders(),
        }
        return ActionResult.ok(data=data)

    def list_recent_activity(self, role: RoleEnum, limit: int = 50) -> ActionResult:
        """Return recent system activity rows for UI display."""
        try:
            require_permission(role, Permission.VIEW_OVERSIGHT)
        except PermissionError:
            logger.warning("PERMISSION DENIED (recent activity): %s", role.value)
            return ActionResult.fail("אין לך הרשאה לצפות ביומן הפעילות")

        return ActionResult.ok(data=self._repository.list_activity_log(limit=limit))

    def list_client_credentials(self, role: RoleEnum) -> ActionResult:
        """Return usernames and passwords for all client accounts."""
        try:
            require_permission(role, Permission.VIEW_OVERSIGHT)
        except PermissionError:
            logger.warning("PERMISSION DENIED (client credentials): %s", role.value)
            return ActionResult.fail("אין לך הרשאה לצפות בפרטי הכניסה")

        return ActionResult.ok(data=self._repository.list_client_credentials())
