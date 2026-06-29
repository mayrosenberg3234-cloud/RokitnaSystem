"""Project domain model and project lifecycle rules."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class ProjectStatus(str, Enum):
    """Lifecycle status of an architecture project.

    The values intentionally match the values stored in SQLite.  The project
    lifecycle used in Requirement 1 is:

    ``Active -> OnHold -> Active`` when work is paused and later resumed,
    and ``Active/OnHold -> Completed`` when the project reaches its end.
    ``Completed`` is a final business state and cannot be reopened through the
    standard client-file workflow.
    """

    ACTIVE = "Active"
    COMPLETED = "Completed"
    ON_HOLD = "OnHold"

    @property
    def hebrew_label(self) -> str:
        """Human-readable Hebrew label used consistently in the GUI."""
        labels = {
            ProjectStatus.ACTIVE: "פעיל",
            ProjectStatus.COMPLETED: "הושלם",
            ProjectStatus.ON_HOLD: "בהמתנה",
        }
        return labels[self]

    @property
    def is_final(self) -> bool:
        """Return whether this status is a terminal lifecycle state."""
        return self is ProjectStatus.COMPLETED


@dataclass
class Project:
    """A project belonging to exactly one client.

    ``client_id`` implements the mandatory side of the relationship
    ``Client 1 ---- 0..* Project``.  The object owns the lifecycle-rule
    behaviour while the controller coordinates permissions and persistence.
    """

    client_id: int
    project_name: str
    status: ProjectStatus = ProjectStatus.ACTIVE
    project_id: Optional[int] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def available_next_statuses(self) -> tuple[ProjectStatus, ...]:
        """Return valid next states for the project's current lifecycle state.

        State-machine rules:
        * Active -> OnHold or Completed
        * OnHold -> Active or Completed
        * Completed -> no further state
        """
        transitions: dict[ProjectStatus, tuple[ProjectStatus, ...]] = {
            ProjectStatus.ACTIVE: (
                ProjectStatus.ON_HOLD,
                ProjectStatus.COMPLETED,
            ),
            ProjectStatus.ON_HOLD: (
                ProjectStatus.ACTIVE,
                ProjectStatus.COMPLETED,
            ),
            ProjectStatus.COMPLETED: (),
        }
        return transitions[self.status]

    def can_transition_to(self, new_status: ProjectStatus) -> bool:
        """Return whether ``new_status`` is a valid next lifecycle state."""
        return (
            isinstance(new_status, ProjectStatus)
            and new_status in self.available_next_statuses()
        )

    def update_project_status(self, new_status: ProjectStatus) -> None:
        """Apply a valid lifecycle transition to the project object.

        This method deliberately changes only the in-memory domain object.
        Persisting the change is the responsibility of ``DBRepository`` after
        the controller has completed authorization and ownership checks.
        """
        if not isinstance(new_status, ProjectStatus):
            raise ValueError("סטטוס הפרויקט אינו תקין")

        if new_status is self.status:
            raise ValueError(
                f"הפרויקט כבר נמצא בסטטוס '{self.status.hebrew_label}'"
            )

        if not self.can_transition_to(new_status):
            raise ValueError(
                "לא ניתן לעדכן פרויקט מסטטוס "
                f"'{self.status.hebrew_label}' לסטטוס "
                f"'{new_status.hebrew_label}'"
            )

        self.status = new_status
