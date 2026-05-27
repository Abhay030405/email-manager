"""API schemas package.

Domain-specific modules re-export from ``app.models.schemas`` so that API
route files always import from ``app.schemas``.
Common infrastructure (pagination, errors, health) lives in ``schemas.common``.
"""

# ── Common infrastructure ─────────────────────────────────────────────────────
from app.schemas.common import (
    APIResponse,
    ErrorDetail,
    ErrorResponse,
    HealthStatus,
    NotFoundResponse,
    PageParams,
    PaginatedResponse,
    ServiceHealth,
    SuccessResponse,
    WorkflowStatusResponse,
)

# ── Approval ──────────────────────────────────────────────────────────────────
from app.schemas.approval import (
    ApprovalActionRequest,
    ApprovalRequest,
    ApprovalResponse,
    ApprovalResultResponse,
)

# ── Campaign ──────────────────────────────────────────────────────────────────
from app.schemas.campaign import (
    CampaignCreate,
    CampaignCreateRequest,
    CampaignDetailResponse,
    CampaignListResponse,
    CampaignResponse,
    CampaignUpdate,
    CampaignUpdateRequest,
    CampaignWorkflowStatus,
)

# ── Customer ──────────────────────────────────────────────────────────────────
from app.schemas.customer import (
    CustomerCreate,
    CustomerListResponse,
    CustomerResponse,
    CustomerSchema,
    CustomerUpdate,
)

# ── Metrics ───────────────────────────────────────────────────────────────────
from app.schemas.metrics import (
    CampaignMetricsResponse,
    CustomerResultSchema,
    MetricsCreate,
    MetricsResponse,
    MetricsUpdate,
)

# ── Segment ───────────────────────────────────────────────────────────────────
from app.schemas.segment import SegmentCreate, SegmentResponse, SegmentUpdate

# ── Variant ───────────────────────────────────────────────────────────────────
from app.schemas.variant import (
    VariantCreate,
    VariantDetailResponse,
    VariantResponse,
    VariantUpdate,
)

__all__ = [
    # Common
    "APIResponse",
    "ErrorDetail",
    "ErrorResponse",
    "HealthStatus",
    "NotFoundResponse",
    "PageParams",
    "PaginatedResponse",
    "ServiceHealth",
    "SuccessResponse",
    "WorkflowStatusResponse",
    # Approval
    "ApprovalActionRequest",
    "ApprovalRequest",
    "ApprovalResponse",
    "ApprovalResultResponse",
    # Campaign
    "CampaignCreate",
    "CampaignCreateRequest",
    "CampaignDetailResponse",
    "CampaignListResponse",
    "CampaignResponse",
    "CampaignUpdate",
    "CampaignUpdateRequest",
    "CampaignWorkflowStatus",
    # Customer
    "CustomerCreate",
    "CustomerListResponse",
    "CustomerResponse",
    "CustomerSchema",
    "CustomerUpdate",
    # Metrics
    "CampaignMetricsResponse",
    "CustomerResultSchema",
    "MetricsCreate",
    "MetricsResponse",
    "MetricsUpdate",
    # Segment
    "SegmentCreate",
    "SegmentResponse",
    "SegmentUpdate",
    # Variant
    "VariantCreate",
    "VariantDetailResponse",
    "VariantResponse",
    "VariantUpdate",
]
