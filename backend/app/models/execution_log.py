"""Execution log model — records each Mock API scheduling attempt."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional
import uuid

from pydantic import BaseModel, Field


class ExecutionLogStatus(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    RETRIED = "retried"


class ExecutionLog(BaseModel):
    """Audit record for a single variant scheduling attempt."""

    log_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    campaign_id: str
    variant_id: str
    mock_campaign_id: Optional[str] = None
    status: ExecutionLogStatus
    customer_count: int = 0
    error_message: Optional[str] = None
    retry_count: int = 0
    elapsed_ms: Optional[float] = None
    executed_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = Field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump()

    model_config = {"collection": "execution_logs"}


EXECUTION_LOG_INDEXES = [
    {"keys": [("log_id", 1)], "unique": True},
    {"keys": [("campaign_id", 1)]},
    {"keys": [("variant_id", 1)]},
    {"keys": [("status", 1)]},
    {"keys": [("executed_at", -1)]},
]
