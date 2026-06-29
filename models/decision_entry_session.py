"""In-memory state model for the Requirement 15 decision-entry workflow.

``DecisionLog`` represents the persistent business entity.  This class models
the temporary interaction session used while an architect enters a decision.
That separation makes the State Diagram precise: the screen workflow has
states, while a saved decision remains a durable database record.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class DecisionEntryStatus(str, Enum):
    """States from the Requirement 15 State Diagram."""

    DRAFT = "DecisionDraft"
    INVALID = "DecisionInvalid"
    SAVING = "DecisionSaving"
    RECORDED = "DecisionRecorded"
    SAVE_FAILED = "DecisionSaveFailed"
    CLOSED = "DecisionClosed"

    @property
    def hebrew_label(self) -> str:
        """Human-readable label for GUI feedback."""
        labels = {
            DecisionEntryStatus.DRAFT: "טיוטת החלטה",
            DecisionEntryStatus.INVALID: "פרטי החלטה לא תקינים",
            DecisionEntryStatus.SAVING: "שמירת החלטה",
            DecisionEntryStatus.RECORDED: "החלטה תועדה",
            DecisionEntryStatus.SAVE_FAILED: "שמירת החלטה נכשלה",
            DecisionEntryStatus.CLOSED: "תהליך תיעוד נסגר",
        }
        return labels[self]


@dataclass
class DecisionEntrySession:
    """State holder for the decision-entry form lifecycle."""

    status: DecisionEntryStatus = DecisionEntryStatus.DRAFT
    last_error: Optional[str] = None

    def return_to_draft(self) -> None:
        """Start a fresh correction/retry cycle from the draft state."""
        self.status = DecisionEntryStatus.DRAFT
        self.last_error = None

    def mark_invalid(self, message: str) -> None:
        """Move to ``DecisionInvalid`` after a validation/business-rule error."""
        self.status = DecisionEntryStatus.INVALID
        self.last_error = message

    def begin_saving(self) -> None:
        """Move to ``DecisionSaving`` immediately before persistence begins."""
        self.status = DecisionEntryStatus.SAVING
        self.last_error = None

    def mark_recorded(self) -> None:
        """Move to ``DecisionRecorded`` after an atomic database commit."""
        self.status = DecisionEntryStatus.RECORDED
        self.last_error = None

    def mark_save_failed(self, message: str) -> None:
        """Move to ``DecisionSaveFailed`` if persistence fails."""
        self.status = DecisionEntryStatus.SAVE_FAILED
        self.last_error = message

    def close(self) -> None:
        """Move to the final state once the decision-entry interaction ends."""
        self.status = DecisionEntryStatus.CLOSED
        self.last_error = None
