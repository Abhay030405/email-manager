"""Data models package."""

from app.models.customer import Customer, Gender, ActivityStatus, CUSTOMER_INDEXES
from app.models.campaign import Campaign, CampaignStatus, ParsedData, CAMPAIGN_INDEXES
from app.models.variant import CampaignVariant, VariantStatus, VARIANT_INDEXES
from app.models.metrics import Metrics, METRICS_INDEXES
from app.models.segment import Segment, SegmentCriteria, SEGMENT_INDEXES

__all__ = [
    "Customer",
    "Gender",
    "ActivityStatus",
    "CUSTOMER_INDEXES",
    "Campaign",
    "CampaignStatus",
    "ParsedData",
    "CAMPAIGN_INDEXES",
    "CampaignVariant",
    "VariantStatus",
    "VARIANT_INDEXES",
    "Metrics",
    "METRICS_INDEXES",
    "Segment",
    "SegmentCriteria",
    "SEGMENT_INDEXES",
]
