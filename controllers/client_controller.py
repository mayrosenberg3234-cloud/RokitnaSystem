"""Client portal controller.

Lets an authenticated client view their own projects and progress, see their
upcoming meetings, submit inquiries to the office and review the inquiries they
have already sent.  Implements the Part B ``Client.viewProjectStatus()`` and
``ClientInquiry.sendInquiry()`` behaviour.

Every action is scoped to the client record linked to the logged-in user
(``User.client_id``); a client can never see another client's data.
"""

from __future__ import annotations

from controllers import ActionResult
from models.change import ChangeStatus
from models.inquiry import ClientInquiry
from models.user import RoleEnum, User
from repositories.db_repository import DBRepository
from services.validation_service import ValidationError, require_non_empty
from utils.logger import get_logger
from utils.permissions import Permission, PermissionError, require_permission

# Roles a client may address an inquiry to.
INQUIRY_TARGETS = (RoleEnum.OFFICE_MANAGER, RoleEnum.ARCHITECT)

logger = get_logger()


class ClientController:
    """Coordinates the read-only client portal and inquiry submission."""

    def __init__(self, repository: DBRepository | None = None) -> None:
        self._repository = repository or DBRepository()

    def _require_linked_client(self, user: User) -> int | None:
        """Return the client id linked to ``user`` or ``None`` when unlinked."""
        return user.client_id

    def view_my_projects(self, user: User) -> ActionResult:
        """Return the projects (and their status) of the client's own file."""
        try:
            require_permission(user.role, Permission.VIEW_OWN_PROJECT)
        except PermissionError:
            logger.warning("PERMISSION DENIED (view own projects): %s", user.role.value)
            return ActionResult.fail("אין לך הרשאה לצפות בפרויקטים")

        client_id = self._require_linked_client(user)
        if client_id is None:
            return ActionResult.fail(
                "חשבונך אינו מקושר לתיק לקוח. פנה למשרד האדריכלות."
            )

        projects = self._repository.list_projects_by_client(client_id)
        return ActionResult.ok(data=projects)

    def view_my_meetings(self, user: User) -> ActionResult:
        """Return the client's upcoming meetings (today onward)."""
        try:
            require_permission(user.role, Permission.VIEW_OWN_PROJECT)
        except PermissionError:
            return ActionResult.fail("אין לך הרשאה לצפות בפגישות")

        client_id = self._require_linked_client(user)
        if client_id is None:
            return ActionResult.fail(
                "חשבונך אינו מקושר לתיק לקוח. פנה למשרד האדריכלות."
            )

        meetings = self._repository.list_upcoming_meetings_by_client(client_id)
        return ActionResult.ok(data=meetings)

    def submit_inquiry(
        self, user: User, content: str, target_role: str = RoleEnum.OFFICE_MANAGER.value
    ) -> ActionResult:
        """Validate and store a new inquiry addressed to a chosen office role."""
        try:
            require_permission(user.role, Permission.SUBMIT_INQUIRY)
        except PermissionError:
            logger.warning("PERMISSION DENIED (submit inquiry): %s", user.role.value)
            return ActionResult.fail("אין לך הרשאה לשלוח פנייה")

        client_id = self._require_linked_client(user)
        if client_id is None:
            return ActionResult.fail(
                "חשבונך אינו מקושר לתיק לקוח. פנה למשרד האדריכלות."
            )

        if target_role not in {r.value for r in INQUIRY_TARGETS}:
            return ActionResult.fail("נמען הפנייה אינו תקין")

        try:
            content = require_non_empty(content, "תוכן הפנייה")
        except ValidationError as exc:
            return ActionResult.fail(str(exc))

        inquiry = ClientInquiry(
            client_id=client_id, content=content, target_role=target_role
        )
        inquiry_id = self._repository.create_inquiry(inquiry)
        logger.info(
            "INQUIRY SUBMITTED: id=%s client=%s to=%s",
            inquiry_id,
            client_id,
            target_role,
        )
        return ActionResult.ok("הפנייה נשלחה בהצלחה", data=inquiry_id)

    # ------------------------------------------------------------------ #
    # Drawings, changes (approval), meetings, reminders
    # ------------------------------------------------------------------ #
    def view_my_drawings(self, user: User) -> ActionResult:
        """Return the drawings across the client's projects."""
        try:
            require_permission(user.role, Permission.VIEW_OWN_PROJECT)
        except PermissionError:
            return ActionResult.fail("אין לך הרשאה לצפות בסרטוטים")
        client_id = self._require_linked_client(user)
        if client_id is None:
            return ActionResult.fail(
                "חשבונך אינו מקושר לתיק לקוח. פנה למשרד האדריכלות."
            )
        return ActionResult.ok(
            data=self._repository.list_drawings_by_client(client_id)
        )

    def view_my_changes(self, user: User) -> ActionResult:
        """Return the documented changes across the client's projects."""
        try:
            require_permission(user.role, Permission.VIEW_OWN_PROJECT)
        except PermissionError:
            return ActionResult.fail("אין לך הרשאה לצפות בשינויים")
        client_id = self._require_linked_client(user)
        if client_id is None:
            return ActionResult.fail(
                "חשבונך אינו מקושר לתיק לקוח. פנה למשרד האדריכלות."
            )
        return ActionResult.ok(
            data=self._repository.list_changes_by_client(client_id)
        )

    def decide_change(
        self, user: User, change_id: int, approved: bool
    ) -> ActionResult:
        """Approve or reject a documented change (must belong to the client)."""
        try:
            require_permission(user.role, Permission.APPROVE_CHANGES)
        except PermissionError:
            logger.warning("PERMISSION DENIED (approve change): %s", user.role.value)
            return ActionResult.fail("אין לך הרשאה לאשר שינויים")

        client_id = self._require_linked_client(user)
        if client_id is None:
            return ActionResult.fail(
                "חשבונך אינו מקושר לתיק לקוח. פנה למשרד האדריכלות."
            )

        change = self._repository.get_change(change_id)
        if change is None:
            return ActionResult.fail("השינוי לא נמצא")

        project = self._repository.get_project(change.project_id)
        if project is None or project.client_id != client_id:
            return ActionResult.fail("השינוי אינו שייך לפרויקטים שלך")

        if change.status != ChangeStatus.PENDING:
            return ActionResult.fail("השינוי כבר טופל ואינו ממתין לאישור")

        new_status = ChangeStatus.APPROVED if approved else ChangeStatus.REJECTED
        self._repository.set_change_decision(change_id, new_status, user.user_id)
        logger.info(
            "CHANGE DECISION: change=%s client=%s status=%s",
            change_id,
            client_id,
            new_status.value,
        )
        message = "השינוי אושר" if approved else "השינוי נדחה"
        return ActionResult.ok(message)

    def confirm_meeting(self, user: User, meeting_id: int) -> ActionResult:
        """Confirm a proposed meeting that belongs to the client."""
        try:
            require_permission(user.role, Permission.APPROVE_CHANGES)
        except PermissionError:
            return ActionResult.fail("אין לך הרשאה לאשר פגישות")

        client_id = self._require_linked_client(user)
        if client_id is None:
            return ActionResult.fail(
                "חשבונך אינו מקושר לתיק לקוח. פנה למשרד האדריכלות."
            )

        meeting = self._repository.get_meeting(meeting_id)
        if meeting is None:
            return ActionResult.fail("הפגישה לא נמצאה")
        project = self._repository.get_project(meeting.project_id)
        if project is None or project.client_id != client_id:
            return ActionResult.fail("הפגישה אינה שייכת לפרויקטים שלך")

        self._repository.confirm_meeting(meeting_id)
        logger.info("MEETING CONFIRMED: id=%s client=%s", meeting_id, client_id)
        return ActionResult.ok("הפגישה אושרה")

    def view_my_reminders(self, user: User) -> ActionResult:
        """Return reminders the office sent to this client."""
        try:
            require_permission(user.role, Permission.VIEW_OWN_PROJECT)
        except PermissionError:
            return ActionResult.fail("אין לך הרשאה לצפות בתזכורות")
        client_id = self._require_linked_client(user)
        if client_id is None:
            return ActionResult.fail(
                "חשבונך אינו מקושר לתיק לקוח. פנה למשרד האדריכלות."
            )
        return ActionResult.ok(
            data=self._repository.list_reminders_for_client(client_id)
        )

    def list_my_inquiries(self, user: User) -> ActionResult:
        """Return the inquiries the client has already submitted."""
        try:
            require_permission(user.role, Permission.SUBMIT_INQUIRY)
        except PermissionError:
            return ActionResult.fail("אין לך הרשאה לצפות בפניות")

        client_id = self._require_linked_client(user)
        if client_id is None:
            return ActionResult.fail(
                "חשבונך אינו מקושר לתיק לקוח. פנה למשרד האדריכלות."
            )

        inquiries = self._repository.list_inquiries_by_client(client_id)
        return ActionResult.ok(data=inquiries)
