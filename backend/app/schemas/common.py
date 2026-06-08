"""Generic API infrastructure schemas: pagination, responses, errors, health."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Generic, Optional, TypeVar

from fastapi import Query
from pydantic import BaseModel, Field, model_validator

T = TypeVar("T")


# ── Pagination ────────────────────────────────────────────────────────────────

class PageParams(BaseModel):
    """Query-parameter bundle for paginated list endpoints."""

    skip: int = Field(0, ge=0, description="Number of records to skip")
    limit: int = Field(50, ge=1, le=500, description="Maximum records to return")

    @classmethod
    def as_query(
        cls,
        skip: int = Query(0, ge=0, description="Records to skip"),
        limit: int = Query(50, ge=1, le=500, description="Max records to return"),
    ) -> "PageParams":
        return cls(skip=skip, limit=limit)


class PaginatedResponse(BaseModel, Generic[T]):
    """Wrapper returned by all list/search endpoints."""

    items: list[T]
    total: int = Field(..., description="Total matching records (before pagination)")
    skip: int
    limit: int
    has_more: bool = Field(..., description="True when more records exist past this page")

    @classmethod
    def build(
        cls,
        items: list[T],
        total: int,
        skip: int,
        limit: int,
    ) -> "PaginatedResponse[T]":
        return cls(
            items=items,
            total=total,
            skip=skip,
            limit=limit,
            has_more=(skip + len(items)) < total,
        )


# ── Standard response envelopes ───────────────────────────────────────────────

class APIResponse(BaseModel, Generic[T]):
    """Generic success envelope used by single-resource endpoints."""

    success: bool = True
    data: Optional[T] = None
    message: str = ""

    @classmethod
    def ok(cls, data: T, message: str = "") -> "APIResponse[T]":
        return cls(success=True, data=data, message=message)


class SuccessResponse(BaseModel):
    """Lightweight success confirmation for operations that return no resource."""

    message: str
    data: dict[str, Any] = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    """Structured error body returned on 4xx / 5xx responses."""

    error: str
    detail: str
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp of when the error occurred",
    )


class ErrorDetail(BaseModel):
    """Alternate error body with optional field attribution (validation errors)."""

    success: bool = False
    error: str
    detail: Optional[str] = None
    field: Optional[str] = None


class NotFoundResponse(ErrorDetail):
    error: str = "not_found"
    detail: str = "The requested resource was not found."


# ── Health ────────────────────────────────────────────────────────────────────

class ServiceHealth(BaseModel):
    status: str = Field(..., description="ok | degraded | error")
    detail: Optional[str] = None
    latency_ms: Optional[float] = None


class HealthStatus(BaseModel):
    """Response body for GET /health and its sub-checks."""

    status: str = Field(..., description="ok | degraded | error")
    version: str = ""
    environment: str = ""
    services: dict[str, ServiceHealth] = Field(default_factory=dict)


# ── Workflow / async operation status ─────────────────────────────────────────

class WorkflowStatusResponse(BaseModel):
    """Returned immediately when a long-running workflow is triggered."""

    job_id: str = Field("", description="Unique job identifier — same as campaign_id")
    campaign_id: str
    status: str = Field(..., description="draft | running | pending_approval | completed | failed")
    message: str = ""
    current_step: Optional[str] = Field(None, description="Active LangGraph node name")
    mock_api_campaign_ids: dict[str, str] = Field(
        default_factory=dict,
        description="variant_id -> Mock API campaign_id mappings",
    )
    error: Optional[str] = None
    details: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _populate_job_id(self) -> "WorkflowStatusResponse":
        if not self.job_id:
            self.job_id = self.campaign_id
        return self
