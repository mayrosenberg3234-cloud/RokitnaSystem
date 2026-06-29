"""Customer (client) management controller — Requirement 1.

Implements the digital client-file use case from end to end:
* an authorised office manager can create, view, update and request deletion;
* client details are validated and duplicate phone/email values are rejected;
* every client is linked to zero or more projects;
* a client with one or more linked projects is archived rather than deleted, so
  the organisational project history remains intact.

The public methods map directly to the Requirement 1 sequence flow.  The
private helper methods represent the controller's internal self-calls:
validation, duplicate detection and project-link checking.
"""

from __future__ import annotations

from controllers import ActionResult
from models.client import Client, ClientStatus
from models.meeting import Meeting
from models.project import Project, ProjectStatus
from models.user import RoleEnum, User
from repositories.db_repository import DBRepository
from services.validation_service import (
    ValidationError,
    require_non_empty,
    validate_email,
    validate_phone,
)
from utils.hashing import generate_password, hash_password
from utils.logger import get_logger
from utils.permissions import (
    Permission,
    PermissionError,
    require_permission,
)

logger = get_logger()


class CustomerController:
    """Coordinates the digital client-management use case (Requirement 1)."""

    def __init__(self, repository: DBRepository | None = None) -> None:
        self._repository = repository or DBRepository()

    # ------------------------------------------------------------------ #
    # Internal controller self-calls (Sequence Diagram self-messages)
    # ------------------------------------------------------------------ #
    def _validate_client_details(
        self,
        name: str,
        phone: str,
        email: str,
    ) -> tuple[str, str, str]:
        """Validate and normalise the mandatory client details."""
        name = require_non_empty(name, "שם")
        phone = validate_phone(phone)
        email = validate_email(email)
        return name, phone, email

    def _check_duplicate_client(
        self,
        phone: str,
        email: str,
        excluded_client_id: int | None = None,
    ) -> str | None:
        """Return a friendly error when phone/email belongs to another client.

        ``excluded_client_id`` is supplied during an update so a client is
        allowed to keep its own existing phone and email values.
        """
        phone_owner = self._repository.find_client_by_phone(phone)
        if (
            phone_owner is not None
            and phone_owner.client_id != excluded_client_id
        ):
            return "קיים כבר לקוח עם מספר טלפון זה"

        email_owner = self._repository.find_client_by_email(email)
        if (
            email_owner is not None
            and email_owner.client_id != excluded_client_id
        ):
            return "קיים כבר לקוח עם כתובת אימייל זו"

        return None

    def _check_client_projects(self, client_id: int) -> int:
        """Return the total number of projects linked to a client.

        The business rule deliberately counts *all* project states.  A
        completed or paused project is still part of the office's history and
        still references its client, so deleting that client would violate
        referential integrity and damage the digital client file.
        """
        return self._repository.count_projects_for_client(client_id)

    def _validate_project_details(self, project_name: str) -> str:
        """Validate and normalize the project name entered by the manager."""
        return require_non_empty(project_name, "שם הפרויקט")

    def _generate_unique_username(self, email: str) -> str:
        """Derive a unique login username for a new client account."""
        base = email.split("@")[0].strip().lower()
        base = "".join(ch for ch in base if ch.isalnum() or ch in "._-")
        if not base:
            base = "client"
        candidate = base
        suffix = 1
        while self._repository.find_user_by_username(candidate) is not None:
            suffix += 1
            candidate = f"{base}{suffix}"
        return candidate

    # ------------------------------------------------------------------ #
    # Read
    # ------------------------------------------------------------------ #
    def list_clients(self, role: RoleEnum) -> ActionResult:
        """Return all clients for an authorised office manager."""
        try:
            require_permission(role, Permission.MANAGE_CLIENTS)
        except PermissionError:
            logger.warning("PERMISSION DENIED (list clients): %s", role.value)
            return ActionResult.fail("אין לך הרשאה לצפות בלקוחות")

        return ActionResult.ok(data=self._repository.list_clients())

    def get_client(self, role: RoleEnum, client_id: int) -> ActionResult:
        """Return one selected client for the digital client-file display."""
        try:
            require_permission(role, Permission.MANAGE_CLIENTS)
        except PermissionError:
            logger.warning("PERMISSION DENIED (view client): %s", role.value)
            return ActionResult.fail("אין לך הרשאה לצפות בפרטי הלקוח")

        client = self._repository.get_client(client_id)
        if client is None:
            return ActionResult.fail("הלקוח לא נמצא")

        return ActionResult.ok(data=client)

    def list_client_projects(
        self,
        role: RoleEnum,
        client_id: int,
    ) -> ActionResult:
        """Return every project linked to the selected client."""
        try:
            require_permission(role, Permission.MANAGE_CLIENTS)
        except PermissionError:
            logger.warning(
                "PERMISSION DENIED (list client projects): %s", role.value
            )
            return ActionResult.fail("אין לך הרשאה לצפות בפרויקטי הלקוח")

        if self._repository.get_client(client_id) is None:
            return ActionResult.fail("הלקוח לא נמצא")

        projects = self._repository.list_projects_by_client(client_id)
        return ActionResult.ok(data=projects)

    # ------------------------------------------------------------------ #
    # Link project to client
    # ------------------------------------------------------------------ #
    def link_project_to_client(
        self,
        role: RoleEnum,
        client_id: int,
        project_name: str,
    ) -> ActionResult:
        """Create a project and persist its mandatory link to a selected client.

        In the data model, ``Project.client_id`` is the implementation of the
        ``Client 1 --- 0..* Project`` relationship.  Therefore linking a new
        project is performed by creating a ``Project`` object with the chosen
        client id and saving it through ``DBRepository.create_project()``.

        Only an office manager may perform this action.  A new project cannot
        be linked to an archived client because that client is no longer active
        in the organisation's operational workflow.
        """
        try:
            require_permission(role, Permission.MANAGE_CLIENTS)
            project_name = self._validate_project_details(project_name)
        except PermissionError:
            logger.warning(
                "PERMISSION DENIED (link project to client): %s", role.value
            )
            return ActionResult.fail("אין לך הרשאה לקשר פרויקט ללקוח")
        except ValidationError as exc:
            return ActionResult.fail(str(exc))

        client = self._repository.get_client(client_id)
        if client is None:
            return ActionResult.fail("הלקוח לא נמצא")

        if client.status == ClientStatus.ARCHIVED:
            return ActionResult.fail(
                "לא ניתן לקשר פרויקט חדש ללקוח בארכיון"
            )

        # <<create>> Project
        # A new project always begins in ProjectActive.  Other states are
        # reached only through update_project_status(), according to the
        # Project State Diagram.
        project = Project(
            client_id=client_id,
            project_name=project_name,
            status=ProjectStatus.ACTIVE,
        )
        project_id = self._repository.create_project(project)
        logger.info(
            "PROJECT LINKED TO CLIENT: project_id=%s client_id=%s",
            project_id,
            client_id,
        )
        return ActionResult.ok(
            "הפרויקט קושר ללקוח בהצלחה",
            data=project_id,
        )

    # ------------------------------------------------------------------ #
    # Project-status update (Requirement 1 project lifecycle)
    # ------------------------------------------------------------------ #
    def _validate_project_status_transition(
        self,
        project: Project,
        new_status: ProjectStatus,
    ) -> str | None:
        """Return a friendly message when a project lifecycle transition fails.

        The state rules are owned by the ``Project`` business object.  This
        controller self-call translates those rules into a message suitable for
        the GUI and keeps the Sequence Diagram explicit.
        """
        if not isinstance(new_status, ProjectStatus):
            return "סטטוס הפרויקט אינו תקין"

        if new_status is project.status:
            return (
                "הפרויקט כבר נמצא בסטטוס "
                f"'{project.status.hebrew_label}'"
            )

        if not project.can_transition_to(new_status):
            return (
                "לא ניתן לעדכן פרויקט מסטטוס "
                f"'{project.status.hebrew_label}' לסטטוס "
                f"'{new_status.hebrew_label}'"
            )

        return None

    def update_project_status(
        self,
        role: RoleEnum,
        client_id: int,
        project_id: int,
        new_status: ProjectStatus,
    ) -> ActionResult:
        """Update a selected linked project's status according to progress.

        The method enforces four business rules before persisting the change:
        1. only the office manager may update a project's progress;
        2. the selected client must exist and be operational (not archived);
        3. the selected project must belong to that exact client;
        4. the requested status must be a legal state-machine transition.
        """
        try:
            require_permission(role, Permission.MANAGE_CLIENTS)
        except PermissionError:
            logger.warning(
                "PERMISSION DENIED (update project status): %s", role.value
            )
            return ActionResult.fail("אין לך הרשאה לעדכן סטטוס פרויקט")

        client = self._repository.get_client(client_id)
        if client is None:
            return ActionResult.fail("הלקוח לא נמצא")

        if client.status == ClientStatus.ARCHIVED:
            return ActionResult.fail(
                "לא ניתן לעדכן סטטוס פרויקט עבור לקוח בארכיון"
            )

        project = self._repository.get_project(project_id)
        if project is None:
            return ActionResult.fail("הפרויקט לא נמצא")

        # The project must be updated from within its own client's digital file.
        if project.client_id != client_id:
            logger.warning(
                "PROJECT OWNERSHIP MISMATCH: project_id=%s expected_client=%s actual_client=%s",
                project_id,
                client_id,
                project.client_id,
            )
            return ActionResult.fail("הפרויקט שנבחר אינו שייך ללקוח זה")

        transition_error = self._validate_project_status_transition(
            project,
            new_status,
        )
        if transition_error is not None:
            return ActionResult.fail(transition_error)

        old_status = project.status

        # SD-R1 self-message: Project.update_project_status(new_status)
        project.update_project_status(new_status)

        # SD-R1: CustomerController -> DBRepository.update_project_status()
        was_updated = self._repository.update_project_status(
            project.project_id,
            project.status,
        )
        if not was_updated:
            return ActionResult.fail("לא ניתן לעדכן את סטטוס הפרויקט")

        updated_project = self._repository.get_project(project.project_id)
        logger.info(
            "PROJECT STATUS UPDATED: project_id=%s client_id=%s from=%s to=%s",
            project.project_id,
            client_id,
            old_status.value,
            project.status.value,
        )
        return ActionResult.ok(
            "סטטוס הפרויקט עודכן מ־"
            f"'{old_status.hebrew_label}' ל־'{project.status.hebrew_label}'",
            data=updated_project,
        )

    # ------------------------------------------------------------------ #
    # Create
    # ------------------------------------------------------------------ #
    def create_client(
        self,
        role: RoleEnum,
        name: str,
        phone: str,
        email: str,
    ) -> ActionResult:
        """Validate, de-duplicate, create and persist a new client."""
        try:
            require_permission(role, Permission.MANAGE_CLIENTS)
            name, phone, email = self._validate_client_details(name, phone, email)
        except PermissionError:
            logger.warning("PERMISSION DENIED (create client): %s", role.value)
            return ActionResult.fail("אין לך הרשאה ליצור לקוח")
        except ValidationError as exc:
            return ActionResult.fail(str(exc))

        duplicate_error = self._check_duplicate_client(phone, email)
        if duplicate_error is not None:
            return ActionResult.fail(duplicate_error)

        # <<create>> Client
        client = Client(name=name, phone=phone, email=email)
        new_id = self._repository.create_client(client)

        # Provision a linked login account for the client with a generated
        # password, so the office manager can hand the credentials over on
        # creation (the password is shown once and stored only as a hash).
        username = self._generate_unique_username(email)
        password = generate_password()
        account = User(
            username=username,
            password_hash=hash_password(password),
            role=RoleEnum.CLIENT,
            is_active=True,
            client_id=new_id,
        )
        user_id = self._repository.create_user(account)

        logger.info(
            "CLIENT CREATED: id=%s name=%s account=%s(user=%s)",
            new_id,
            name,
            username,
            user_id,
        )
        return ActionResult.ok(
            "הלקוח נוצר בהצלחה וחשבון הכניסה שלו הופק",
            data={
                "client_id": new_id,
                "username": username,
                "password": password,
            },
        )

    # ------------------------------------------------------------------ #
    # Update
    # ------------------------------------------------------------------ #
    def update_client(
        self,
        role: RoleEnum,
        client_id: int,
        name: str,
        phone: str,
        email: str,
    ) -> ActionResult:
        """Validate and persist editable details of an active client.

        Lifecycle status is deliberately not an input to this operation.
        ``ClientActive -> ClientArchived`` is governed only by the controlled
        delete/archive flow, so the implementation cannot bypass the Client
        State Diagram through a manual status update.
        """
        try:
            require_permission(role, Permission.MANAGE_CLIENTS)
            name, phone, email = self._validate_client_details(name, phone, email)
        except PermissionError:
            logger.warning("PERMISSION DENIED (update client): %s", role.value)
            return ActionResult.fail("אין לך הרשאה לעדכן לקוח")
        except ValidationError as exc:
            return ActionResult.fail(str(exc))

        existing = self._repository.get_client(client_id)
        if existing is None:
            return ActionResult.fail("הלקוח לא נמצא")

        if existing.status == ClientStatus.ARCHIVED:
            return ActionResult.fail(
                "לא ניתן לעדכן לקוח בארכיון. הלקוח נשמר לצורכי היסטוריית פרויקטים."
            )

        duplicate_error = self._check_duplicate_client(
            phone,
            email,
            excluded_client_id=client_id,
        )
        if duplicate_error is not None:
            return ActionResult.fail(duplicate_error)

        updated = Client(
            client_id=client_id,
            name=name,
            phone=phone,
            email=email,
            status=existing.status,
            created_at=existing.created_at,
            updated_at=existing.updated_at,
        )
        self._repository.update_client(updated)
        logger.info("CLIENT UPDATED: id=%s", client_id)
        return ActionResult.ok("פרטי הלקוח עודכנו בהצלחה")

    # ------------------------------------------------------------------ #
    # Delete / archive
    # ------------------------------------------------------------------ #
    def delete_client(self, role: RoleEnum, client_id: int) -> ActionResult:
        """Delete a client, or archive it when any linked project exists."""
        try:
            require_permission(role, Permission.MANAGE_CLIENTS)
        except PermissionError:
            logger.warning("PERMISSION DENIED (delete client): %s", role.value)
            return ActionResult.fail("אין לך הרשאה למחוק לקוח")

        client = self._repository.get_client(client_id)
        if client is None:
            return ActionResult.fail("הלקוח לא נמצא")

        if client.status == ClientStatus.ARCHIVED:
            return ActionResult.fail("הלקוח כבר נמצא בארכיון")

        project_count = self._check_client_projects(client_id)
        if project_count > 0:
            # SD-R1 self-message: Client.archive()
            client.archive()
            # Persist the business object's state transition.
            self._repository.archive_client(client.client_id)
            logger.info(
                "CLIENT ARCHIVED (linked projects): id=%s project_count=%s",
                client_id,
                project_count,
            )
            return ActionResult.ok(
                "ללקוח קיימים פרויקטים מקושרים, לכן הוא הועבר לארכיון במקום מחיקה"
            )

        self._repository.delete_client(client_id)
        logger.info("CLIENT DELETED: id=%s", client_id)
        return ActionResult.ok("הלקוח נמחק בהצלחה")

    # ------------------------------------------------------------------ #
    # Meetings (office manager schedules; the client sees them in the portal)
    # ------------------------------------------------------------------ #
    def schedule_meeting(
        self,
        role: RoleEnum,
        client_id: int,
        project_id: int,
        meeting_date: str,
        meeting_time: str,
        location: str,
        summary: str,
    ) -> ActionResult:
        """Schedule a meeting for one of the client's projects.

        Implements the ``Meeting.scheduleMeeting()`` behaviour.  The meeting is
        validated, attached to a project that belongs to the selected client and
        persisted; the client then sees it under their upcoming meetings.
        """
        try:
            require_permission(role, Permission.SCHEDULE_MEETINGS)
            location = require_non_empty(location, "מיקום הפגישה")
            summary = require_non_empty(summary, "נושא הפגישה")
            meeting_date = require_non_empty(meeting_date, "תאריך הפגישה")
            meeting_time = require_non_empty(meeting_time, "שעת הפגישה")
        except PermissionError:
            logger.warning("PERMISSION DENIED (schedule meeting): %s", role.value)
            return ActionResult.fail("אין לך הרשאה לקבוע פגישות")
        except ValidationError as exc:
            return ActionResult.fail(str(exc))

        client = self._repository.get_client(client_id)
        if client is None:
            return ActionResult.fail("הלקוח לא נמצא")
        if client.status == ClientStatus.ARCHIVED:
            return ActionResult.fail("לא ניתן לקבוע פגישה ללקוח בארכיון")

        project = self._repository.get_project(project_id)
        if project is None or project.client_id != client_id:
            return ActionResult.fail("הפרויקט שנבחר אינו שייך ללקוח זה")

        meeting = Meeting(
            project_id=project_id,
            meeting_date=meeting_date,
            meeting_time=meeting_time,
            location=location,
            summary=summary,
        )
        meeting_id = self._repository.create_meeting(meeting)
        logger.info(
            "MEETING SCHEDULED: id=%s project=%s client=%s",
            meeting_id,
            project_id,
            client_id,
        )
        return ActionResult.ok("הפגישה נקבעה בהצלחה", data=meeting_id)

    def list_client_inquiries(
        self,
        role: RoleEnum,
        client_id: int,
    ) -> ActionResult:
        """Return the inquiries a client submitted, for the office manager."""
        try:
            require_permission(role, Permission.MANAGE_CLIENTS)
        except PermissionError:
            return ActionResult.fail("אין לך הרשאה לצפות בפניות הלקוח")

        if self._repository.get_client(client_id) is None:
            return ActionResult.fail("הלקוח לא נמצא")

        inquiries = self._repository.list_inquiries_by_client(client_id)
        return ActionResult.ok(data=inquiries)
