"""Professional decision controller — Requirement 15.

This controller implements the complete use case:
* only an authenticated architect may record a decision;
* the decision text and selected project are validated;
* the decision is linked to the project at creation time through ``projectId``;
* a matching ``ChangeHistory`` record is created in the same database
  transaction; and
* decisions and their history can be shown back to the architect immediately.

The public methods map directly to the updated Requirement 15 Sequence Diagram.
"""

from __future__ import annotations

import sqlite3

from controllers import ActionResult
from models.change_history import ChangeHistory
from models.decision_log import DecisionLog
from models.user import RoleEnum
from repositories.db_repository import DBRepository
from services.validation_service import ValidationError, require_non_empty
from utils.logger import get_logger
from utils.permissions import Permission, PermissionError, require_permission

logger = get_logger()


class DecisionController:
    """Coordinates the professional-decision use case (Requirement 15)."""

    def __init__(self, repository: DBRepository | None = None) -> None:
        self._repository = repository or DBRepository()

    # ------------------------------------------------------------------ #
    # Internal controller self-message in the Sequence Diagram
    # ------------------------------------------------------------------ #
    def _validate_decision_details(self, decision_text: str) -> str:
        """Validate and normalise the mandatory decision text."""
        return require_non_empty(decision_text, "טקסט ההחלטה")

    def _require_decision_permission(self, role: RoleEnum) -> None:
        """Enforce the same role-based rule for all Requirement 15 actions."""
        require_permission(role, Permission.RECORD_DECISIONS)

    def list_projects(self, role: RoleEnum) -> ActionResult:
        """Return projects available for an architect's decision entry."""
        try:
            self._require_decision_permission(role)
        except PermissionError:
            logger.warning("PERMISSION DENIED (list decision projects): %s", role.value)
            return ActionResult.fail("אין לך הרשאה לתעד החלטות בפרויקטים")

        return ActionResult.ok(data=self._repository.list_projects())

    def list_decisions(self, role: RoleEnum, project_id: int) -> ActionResult:
        """Return decisions already recorded for one existing project."""
        try:
            self._require_decision_permission(role)
        except PermissionError:
            return ActionResult.fail("אין לך הרשאה לצפות בהחלטות")

        if self._repository.get_project(project_id) is None:
            return ActionResult.fail("הפרויקט לא נמצא")

        return ActionResult.ok(
            data=self._repository.list_decisions_by_project(project_id)
        )

    def list_changes(self, role: RoleEnum, project_id: int) -> ActionResult:
        """Return the audit history for one existing project."""
        try:
            self._require_decision_permission(role)
        except PermissionError:
            return ActionResult.fail("אין לך הרשאה לצפות בהיסטוריית השינויים")

        if self._repository.get_project(project_id) is None:
            return ActionResult.fail("הפרויקט לא נמצא")

        return ActionResult.ok(
            data=self._repository.list_changes_by_project(project_id)
        )

    def _validate_actor(self, role: RoleEnum, user_id: int | None) -> str | None:
        """Verify that the authenticated actor exists, is active and matches role."""
        if user_id is None:
            return "לא זוהה משתמש מחובר"

        user = self._repository.get_user(user_id)
        if user is None:
            return "המשתמש המחובר לא נמצא"
        if not user.is_active:
            return "המשתמש המחובר אינו פעיל"
        if user.role != role:
            logger.warning(
                "DECISION ACTOR ROLE MISMATCH: user=%s actual=%s supplied=%s",
                user_id,
                user.role.value,
                role.value,
            )
            return "פרטי ההרשאה אינם עקביים"
        return None

    def save_decision(
        self,
        role: RoleEnum,
        user_id: int | None,
        project_id: int | None,
        decision_text: str,
    ) -> ActionResult:
        """Save a professional decision and audit entry as one atomic action.

        The method follows the Requirement 15 Sequence Diagram exactly:
        permission -> validation -> project lookup -> create domain objects ->
        repository transaction -> success/failure result for the GUI.
        """
        try:
            self._require_decision_permission(role)
        except PermissionError:
            logger.warning("PERMISSION DENIED (save decision): %s", role.value)
            return ActionResult.fail(
                "אין לך הרשאה לתעד החלטות",
                data={"state": "permission_denied"},
            )

        actor_error = self._validate_actor(role, user_id)
        if actor_error is not None:
            return ActionResult.fail(actor_error, data={"state": "invalid"})

        try:
            normalized_text = self._validate_decision_details(decision_text)
        except ValidationError as exc:
            return ActionResult.fail(str(exc), data={"state": "invalid"})

        if project_id is None:
            return ActionResult.fail("יש לבחור פרויקט", data={"state": "invalid"})

        project = self._repository.get_project(project_id)
        if project is None:
            return ActionResult.fail("הפרויקט לא נמצא", data={"state": "invalid"})

        # <<create>> DecisionLog — linked to the project at creation time.
        decision = DecisionLog(
            project_id=project_id,
            created_by_user_id=user_id,
            decision_text=normalized_text,
        )

        # <<create>> ChangeHistory — the exact decision id is filled by the
        # repository after the DecisionLog INSERT, before the transaction commits.
        history = ChangeHistory(
            project_id=project_id,
            created_by_user_id=user_id,
            description="תועדה החלטה מקצועית בפרויקט",
        )

        try:
            decision_id, change_id = self._repository.save_decision_with_history(
                decision,
                history,
            )
        except sqlite3.Error:
            logger.exception(
                "DECISION SAVE FAILED: project=%s user=%s",
                project_id,
                user_id,
            )
            return ActionResult.fail(
                "שמירת ההחלטה נכשלה. לא נשמרו נתונים חלקיים במערכת.",
                data={"state": "save_failed"},
            )

        logger.info(
            "DECISION SAVED ATOMICALLY: decision=%s change=%s project=%s user=%s",
            decision_id,
            change_id,
            project_id,
            user_id,
        )
        return ActionResult.ok(
            "ההחלטה נשמרה בהצלחה והתווספה להיסטוריית הפרויקט",
            data={
                "decision_id": decision_id,
                "change_id": change_id,
                "decision_created_at": decision.created_at,
                "change_created_at": history.created_at,
            },
        )
