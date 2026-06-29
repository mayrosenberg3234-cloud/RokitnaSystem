"""Payment domain model."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class Payment:
    """A payment made to settle (fully or partially) a payment request."""

    request_id: int
    amount: float
    payment_date: Optional[str] = None
    payment_id: Optional[int] = None
