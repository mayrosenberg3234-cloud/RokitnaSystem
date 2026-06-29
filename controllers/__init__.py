"""Controller layer.

Controllers orchestrate validation, permission checks and repository calls on
behalf of the views.  They never raise to the GUI; instead every action returns
an :class:`ActionResult` carrying a success flag, a friendly Hebrew message and
optional payload data.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ActionResult:
    """Outcome of a controller action, safe to display directly in the GUI."""

    success: bool
    message: str = ""
    data: Any = field(default=None)

    @classmethod
    def ok(cls, message: str = "", data: Any = None) -> "ActionResult":
        return cls(success=True, message=message, data=data)

    @classmethod
    def fail(cls, message: str, data: Any = None) -> "ActionResult":
        """Create a safe failure result with optional structured context.

        Views receive a friendly Hebrew ``message``.  The optional ``data``
        field is used sparingly for presentation-state routing, for example
        distinguishing validation failures from a rare persistence failure in
        the Requirement 15 State Diagram.
        """
        return cls(success=False, message=message, data=data)
