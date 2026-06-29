"""Authentication controller.

Implements the full login flow: field validation, user lookup, password hash
comparison, active-account check and a final ``LOGIN`` permission check.  All
outcomes are returned as :class:`ActionResult` so the GUI only ever shows
friendly messages.
"""

from __future__ import annotations

from controllers import ActionResult
from repositories.db_repository import DBRepository
from services.validation_service import ValidationError, require_non_empty
from utils.hashing import verify_password
from utils.logger import get_logger
from utils.permissions import Permission, has_permission

logger = get_logger()


class AuthController:
    """Coordinates the authentication use case."""

    def __init__(self, repository: DBRepository | None = None) -> None:
        self._repository = repository or DBRepository()

    def login(self, username: str, password: str) -> ActionResult:
        """Authenticate a user and return the :class:`User` on success."""
        try:
            username = require_non_empty(username, "שם משתמש")
            password = require_non_empty(password, "סיסמה")
        except ValidationError as exc:
            return ActionResult.fail(str(exc))

        user = self._repository.find_user_by_username(username)
        if user is None or not verify_password(password, user.password_hash):
            logger.warning("LOGIN FAILED: %s", username)
            return ActionResult.fail("שם משתמש או סיסמה שגויים")

        if not user.is_active:
            logger.warning("LOGIN FAILED (inactive): %s", username)
            return ActionResult.fail("המשתמש אינו פעיל. פנה למנהל המערכת")

        if not has_permission(user.role, Permission.LOGIN):
            logger.warning("PERMISSION DENIED (login): %s", username)
            return ActionResult.fail("אין לך הרשאת כניסה למערכת")

        logger.info("LOGIN SUCCESS: %s (%s)", username, user.role.value)
        return ActionResult.ok("התחברת בהצלחה", data=user)
