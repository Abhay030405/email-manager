"""Data models package."""

from app.models.campaign import Campaign, CampaignStatus, ParsedData, ProductDetails, CampaignGoalData, CampaignPreferences, CAMPAIGN_INDEXES
from app.models.variant import CampaignVariant, VariantStatus, VARIANT_INDEXES
from app.models.metrics import Metrics, METRICS_INDEXES
from app.models.segment import Segment, SegmentCriteria, SEGMENT_INDEXES

__all__ = [
    "Campaign",
    "CampaignStatus",
    "ParsedData",
    "ProductDetails",
    "CampaignGoalData",
    "CampaignPreferences",
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
