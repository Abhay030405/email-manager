"""Response schemas for alert endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


class AlertResponse(BaseModel):
    alert_id: str
    campaign_id: str
    variant_id: Optional[str]
    alert_type: str
    severity: str
    threshold: float
    actual_value: float
    triggered_at: datetime
    acknowledged: bool
    acknowledged_by: Optional[str]
    acknowledged_at: Optional[datetime]
    message: str
    recommendation: str
    metadata: dict[str, Any]


class AcknowledgeRequest(BaseModel):
    user: str
    notes: Optional[str] = None
