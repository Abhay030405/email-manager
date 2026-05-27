"""Variant request / response schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.variant import VariantStatus

# Re-export existing CRUD schemas
from app.models.schemas import VariantCreate, VariantResponse, VariantUpdate

__all__ = [
    # Existing CRUD schemas (thin re-exports)
    "VariantCreate",
    "VariantResponse",
    "VariantUpdate",
    # Richer response schema with spec-aligned field names
    "VariantDetailResponse",
]


# ── Richer variant detail response ────────────────────────────────────────────

class VariantDetailResponse(BaseModel):
    """Full variant detail with spec-aligned field names (subject/body)
    and optional embedded metrics."""

    id: str = Field(..., description="Alias for variant_id")
    campaign_id: str
    variant_id: str
    segment_name: str

    # Spec uses 'subject' and 'body' — map from model's subject_line / email_body
    subject: str = Field(..., min_length=10, max_length=200)
    body: str = Field(..., min_length=50, max_length=5000)

    send_time: datetime
    mock_api_campaign_id: Optional[str] = None
    metrics: Optional[dict] = None
    status: VariantStatus

    model_config = {"from_attributes": True}

    @classmethod
    def from_variant(
        cls,
        variant: "VariantResponse",
        metrics: Optional[dict] = None,
    ) -> "VariantDetailResponse":
        """Build from the existing VariantResponse model."""
        return cls(
            id=variant.variant_id,
            campaign_id=variant.campaign_id,
            variant_id=variant.variant_id,
            segment_name=variant.segment_name,
            subject=variant.subject_line or "No subject",
            body=variant.email_body or "No body",
            send_time=variant.send_time,
            mock_api_campaign_id=variant.mock_campaign_id,
            metrics=metrics,
            status=variant.status,
        )
