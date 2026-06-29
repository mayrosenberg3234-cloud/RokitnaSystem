"""Role based permission model.

Every sensitive action is represented by a :class:`Permission`.  A static map
ties each :class:`RoleEnum` to the set of permissions it is granted.  The
:func:`has_permission` / :func:`require_permission` helpers are the single point
through which authorization is enforced across the application.
"""

from __future__ import annotations

from enum import Enum

from models.user import RoleEnum


class Permission(str, Enum):
    """Discrete, checkable capabilities within the system."""

    LOGIN = "Login"
    MANAGE_CLIENTS = "ManageClients"
    RECORD_DECISIONS = "RecordDecisions"
    VIEW_PROJECTS = "ViewProjects"
    GENERATE_REPORTS = "GenerateReports"
    VIEW_REPORTS = "ViewReports"
    VIEW_OWN_PROJECT = "ViewOwnProject"
    SUBMIT_INQUIRY = "SubmitInquiry"
    SCHEDULE_MEETINGS = "ScheduleMeetings"
    MANAGE_PROJECT_CONTENT = "ManageProjectContent"
    APPROVE_CHANGES = "ApproveChanges"
    SEND_REMINDERS = "SendReminders"
    VIEW_OVERSIGHT = "ViewOversight"


class PermissionError(Exception):
    """Raised when a user attempts an action they are not allowed to perform."""


# Mapping of every role to the permissions it holds.
PERMISSIONS: dict[RoleEnum, frozenset[Permission]] = {
    RoleEnum.OFFICE_MANAGER: frozenset(
        {
            Permission.LOGIN,
            Permission.MANAGE_CLIENTS,
            Permission.GENERATE_REPORTS,
            Permission.VIEW_REPORTS,
            Permission.VIEW_PROJECTS,
            Permission.SCHEDULE_MEETINGS,
            Permission.SEND_REMINDERS,
            Permission.VIEW_OVERSIGHT,
        }
    ),
    RoleEnum.ARCHITECT: frozenset(
        {
            Permission.LOGIN,
            Permission.RECORD_DECISIONS,
            Permission.VIEW_PROJECTS,
            Permission.MANAGE_PROJECT_CONTENT,
        }
    ),
    RoleEnum.CLIENT: frozenset(
        {
            Permission.LOGIN,
            Permission.VIEW_OWN_PROJECT,
            Permission.SUBMIT_INQUIRY,
            Permission.APPROVE_CHANGES,
        }
    ),
}


def has_permission(role: RoleEnum, permission: Permission) -> bool:
    """Return ``True`` when ``role`` is granted ``permission``."""
    return permission in PERMISSIONS.get(role, frozenset())


def require_permission(role: RoleEnum, permission: Permission) -> None:
    """Raise :class:`PermissionError` when ``role`` lacks ``permission``."""
    if not has_permission(role, permission):
        raise PermissionError(
            f"Role '{role.value}' is not allowed to perform '{permission.value}'"
        )
