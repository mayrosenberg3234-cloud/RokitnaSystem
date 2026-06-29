"""Architect workspace controller.

Lets an authenticated architect document on-site field notes, upload project
drawings and document project changes that are then sent to the client for
approval.  Implements the Part B ``FieldNote``, ``Document`` (drawing) and
``Approval`` (change) behaviour.
"""

from __future__ import annotations

import re

from config import DRAWINGS_DIR
from controllers import ActionResult
from models.change import ProjectChange
from models.drawing import Drawing
from models.field_note import FieldNote
from models.user import RoleEnum, User
from repositories.db_repository import DBRepository
from services.validation_service import ValidationError, require_non_empty
from utils.logger import get_logger
from utils.permissions import Permission, PermissionError, require_permission

logger = get_logger()


class ArchitectController:
    """Coordinates the architect's project-content actions."""

    def __init__(self, repository: DBRepository | None = None) -> None:
        self._repository = repository or DBRepository()

    def _require_content_permission(self, role: RoleEnum) -> None:
        require_permission(role, Permission.MANAGE_PROJECT_CONTENT)

    def list_projects(self, role: RoleEnum) -> ActionResult:
        """Return projects available for the architect's content actions."""
        try:
            self._require_content_permission(role)
        except PermissionError:
            return ActionResult.fail("אין לך הרשאה לנהל תכני פרויקט")
        return ActionResult.ok(data=self._repository.list_projects())

    # ------------------------------------------------------------------ #
    # Field notes
    # ------------------------------------------------------------------ #
    def add_field_note(
        self, user: User, project_id: int, description: str
    ) -> ActionResult:
        """Record an on-site field note for a project."""
        try:
            self._require_content_permission(user.role)
            description = require_non_empty(description, "תוכן ההערה")
        except PermissionError:
            logger.warning("PERMISSION DENIED (field note): %s", user.role.value)
            return ActionResult.fail("אין לך הרשאה לתעד הערות")
        except ValidationError as exc:
            return ActionResult.fail(str(exc))

        if self._repository.get_project(project_id) is None:
            return ActionResult.fail("הפרויקט לא נמצא")

        note = FieldNote(
            project_id=project_id,
            description=description,
            created_by_user_id=user.user_id,
        )
        note_id = self._repository.create_field_note(note)
        logger.info("FIELD NOTE ADDED: id=%s project=%s", note_id, project_id)
        return ActionResult.ok("ההערה תועדה בהצלחה", data=note_id)

    def list_field_notes(self, role: RoleEnum, project_id: int) -> ActionResult:
        try:
            self._require_content_permission(role)
        except PermissionError:
            return ActionResult.fail("אין לך הרשאה לצפות בהערות")
        return ActionResult.ok(
            data=self._repository.list_field_notes_by_project(project_id)
        )

    # ------------------------------------------------------------------ #
    # Drawings
    # ------------------------------------------------------------------ #
    @staticmethod
    def _safe_file_name(name: str) -> str:
        """Strip a file name down to a safe, path-free token."""
        name = (name or "drawing").replace("\\", "/").split("/")[-1]
        return re.sub(r"[^A-Za-z0-9._֐-׿-]", "_", name) or "drawing"

    def upload_drawing(
        self,
        user: User,
        project_id: int,
        file_name: str,
        file_bytes: bytes,
        description: str,
    ) -> ActionResult:
        """Store an uploaded drawing file and record it against the project."""
        try:
            self._require_content_permission(user.role)
        except PermissionError:
            logger.warning("PERMISSION DENIED (upload drawing): %s", user.role.value)
            return ActionResult.fail("אין לך הרשאה להעלות סרטוטים")

        if not file_bytes:
            return ActionResult.fail("לא נבחר קובץ להעלאה")
        if self._repository.get_project(project_id) is None:
            return ActionResult.fail("הפרויקט לא נמצא")

        safe_name = self._safe_file_name(file_name)
        DRAWINGS_DIR.mkdir(parents=True, exist_ok=True)
        # Prefix with project id to avoid collisions between projects.
        stored = DRAWINGS_DIR / f"p{project_id}_{safe_name}"
        stored.write_bytes(file_bytes)

        drawing = Drawing(
            project_id=project_id,
            file_name=safe_name,
            stored_path=str(stored),
            description=(description or "").strip(),
            created_by_user_id=user.user_id,
        )
        drawing_id = self._repository.create_drawing(drawing)
        logger.info("DRAWING UPLOADED: id=%s project=%s", drawing_id, project_id)
        return ActionResult.ok("הסרטוט הועלה בהצלחה", data=drawing_id)

    def list_drawings(self, role: RoleEnum, project_id: int) -> ActionResult:
        try:
            self._require_content_permission(role)
        except PermissionError:
            return ActionResult.fail("אין לך הרשאה לצפות בסרטוטים")
        return ActionResult.ok(
            data=self._repository.list_drawings_by_project(project_id)
        )

    # ------------------------------------------------------------------ #
    # Changes for client approval
    # ------------------------------------------------------------------ #
    def document_change(
        self,
        user: User,
        project_id: int,
        description: str,
        cost: float,
    ) -> ActionResult:
        """Document a project change and submit it for the client's approval."""
        try:
            self._require_content_permission(user.role)
            description = require_non_empty(description, "תיאור השינוי")
        except PermissionError:
            logger.warning("PERMISSION DENIED (document change): %s", user.role.value)
            return ActionResult.fail("אין לך הרשאה לתעד שינויים")
        except ValidationError as exc:
            return ActionResult.fail(str(exc))

        if cost is None or cost < 0:
            return ActionResult.fail("עלות השינוי חייבת להיות מספר אי-שלילי")

        if self._repository.get_project(project_id) is None:
            return ActionResult.fail("הפרויקט לא נמצא")

        change = ProjectChange(
            project_id=project_id,
            description=description,
            cost=float(cost),
            created_by_user_id=user.user_id,
        )
        change_id = self._repository.create_project_change(change)
        logger.info("CHANGE DOCUMENTED: id=%s project=%s", change_id, project_id)
        return ActionResult.ok(
            "השינוי תועד ונשלח לאישור הלקוח", data=change_id
        )

    def list_changes(self, role: RoleEnum, project_id: int) -> ActionResult:
        try:
            self._require_content_permission(role)
        except PermissionError:
            return ActionResult.fail("אין לך הרשאה לצפות בשינויים")
        return ActionResult.ok(
            data=self._repository.list_project_changes_by_project(project_id)
        )

    def list_my_reminders(self, user: User) -> ActionResult:
        """Return reminders the office manager sent to the architects."""
        try:
            self._require_content_permission(user.role)
        except PermissionError:
            return ActionResult.fail("אין לך הרשאה לצפות בתזכורות")
        return ActionResult.ok(
            data=self._repository.list_reminders_for_role(RoleEnum.ARCHITECT.value)
        )
