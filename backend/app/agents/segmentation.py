"""CustomerSegmentationAgent — Mock API-backed multi-group parallel segmentation.

Flow per group (runs in parallel across all groups via asyncio.gather):
  Step 1 — API filter:
    Call POST /api/customers/filter with all group criteria EXCEPT
    App_Installed / Existing_Customer. Returns customer_ids directly.

  Step 2 — Sub-segmentation by App_Installed × Existing_Customer:
    Both null  → 3 API calls: active (App=Y + Existing=Y),
                               inactive (Existing=Y, App=N),
                               dormant (Existing=N)
    ≥1 specified → 1 API call with app_installed/existing_customer added.

No LLM calls — all logic is deterministic.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from pydantic import BaseModel, Field, model_validator

from app.agents.base_agent import BaseAgent
from app.external.mock_campaign_client import MockCampaignClient

logger = logging.getLogger(__name__)

# Total customers in the Mock API cohort — used for coverage calculations.
_MOCK_TOTAL_CUSTOMERS = 5000


# ── Shared output schema (imported by strategy.py and content_gen.py) ─────────

class SegmentOut(BaseModel):
    """A single named customer segment returned by the segmentation agent."""

    segment_name: str
    description: str
    customer_ids: list[str]
    size: int = 0
    targeting_priority: int = Field(..., ge=1, le=5)
    recommended_approach: str
    applied_criteria: dict = Field(default_factory=dict)

    @model_validator(mode="after")
    def sync_size(self) -> "SegmentOut":
        self.size = len(self.customer_ids)
        return self


# ── AudienceGroup → filter API field mapping ─────────────────────────────────

def _first_set(group: dict, *keys: str) -> Any:
    """Return the first non-None value found in *group* under any of *keys*."""
    for k in keys:
        v = group.get(k)
        if v is not None:
            return v
    return None


def _build_filter_body(
    group: dict,
    *,
    app_installed: str | None = None,
    existing_customer: str | None = None,
) -> dict[str, Any]:
    """Map AudienceGroup fields to the POST /api/customers/filter request body.

    Accepts both PascalCase keys (AudienceGroup model) and snake_case keys
    (LLM brief-parser output). app_installed / existing_customer are passed
    separately and override any value in the group dict.
    """
    body: dict[str, Any] = {}

    min_age = _first_set(group, "min_age")
    max_age = _first_set(group, "max_age")
    if min_age is not None and max_age is not None and min_age > max_age:
        min_age, max_age = max_age, min_age
    if min_age is not None:
        body["min_age"] = min_age
    if max_age is not None:
        body["max_age"] = max_age

    gender = _first_set(group, "gender")
    if gender:
        body["gender"] = [gender]   # filter API expects array

    min_income = _first_set(group, "min_income", "min_monthly_income")
    if min_income is not None:
        body["min_monthly_income"] = min_income

    max_income = _first_set(group, "max_income", "max_monthly_income")
    if max_income is not None:
        body["max_monthly_income"] = max_income

    kyc = _first_set(group, "KYC_status", "kyc_status")
    if kyc:
        body["kyc_status"] = kyc

    credit = _first_set(group, "Credit_score", "min_credit_score")
    if credit is not None:
        body["min_credit_score"] = credit

    social = _first_set(group, "Social_Media_Active", "social_media_active")
    if social:
        body["social_media_active"] = social

    if app_installed is not None:
        body["app_installed"] = app_installed
    if existing_customer is not None:
        body["existing_customer"] = existing_customer

    return body


# ── Segment metadata helpers ──────────────────────────────────────────────────

def _segment_description(app: str | None, existing: str | None) -> str:
    parts: list[str] = []
    if app == "Y":       parts.append("app installed")
    elif app == "N":     parts.append("app not installed")
    if existing == "Y":  parts.append("existing customer")
    elif existing == "N": parts.append("non-customer (prospect)")
    return " — ".join(parts) if parts else "all eligible customers"


def _segment_priority(app: str | None, existing: str | None) -> int:
    if app == "Y" and existing == "Y": return 5
    if app == "Y" and existing == "N": return 4
    if app == "Y":                     return 4
    if existing == "Y":                return 3
    if existing == "N":                return 3
    return 2


def _segment_approach(app: str | None, existing: str | None) -> str:
    if app == "Y" and existing == "Y":
        return "Loyalty and upsell focus. Lead with the relationship and reward their trust."
    if app == "Y" and existing == "N":
        return "Conversion focus — they're engaged but not yet a customer. Make sign-up feel effortless."
    if app == "Y":
        return "App-native messaging. Highlight in-app convenience and one-tap sign-up."
    if existing == "Y":
        return "Existing relationship: emphasise expanded benefits and new product features."
    if existing == "N":
        return "Welcome framing. Focus on simplicity, safety, and the benefit of starting today."
    return "Broad benefit-led messaging tailored to this group's life stage."


# ── Segment-building helpers ──────────────────────────────────────────────────

def _three_way_segments(
    prefix: str,
    base_criteria: dict,
    active_ids: list[str],
    inactive_ids: list[str],
    dormant_ids: list[str],
) -> list[dict]:
    """Build active / inactive / dormant segment dicts from pre-fetched ID lists."""
    segments: list[dict] = []
    if active_ids:
        segments.append({
            "segment_name": f"{prefix}_active",
            "description": "Active customers — app installed + existing relationship",
            "customer_ids": active_ids,
            "size": len(active_ids),
            "targeting_priority": 5,
            "recommended_approach": "Lead with loyalty and retention messaging. Upsell focus.",
            "applied_criteria": {**base_criteria, "App_Installed": "Y", "Existing_Customer": "Y"},
        })
    if inactive_ids:
        segments.append({
            "segment_name": f"{prefix}_inactive",
            "description": "Existing customers without the app — re-engagement opportunity",
            "customer_ids": inactive_ids,
            "size": len(inactive_ids),
            "targeting_priority": 3,
            "recommended_approach": "Drive app install with benefit-led messaging.",
            "applied_criteria": {**base_criteria, "App_Installed": "N", "Existing_Customer": "Y"},
        })
    if dormant_ids:
        segments.append({
            "segment_name": f"{prefix}_dormant",
            "description": "Non-customers — acquisition focus",
            "customer_ids": dormant_ids,
            "size": len(dormant_ids),
            "targeting_priority": 4,
            "recommended_approach": "Welcome framing. Emphasise simplicity of sign-up.",
            "applied_criteria": {**base_criteria, "Existing_Customer": "N"},
        })
    return segments


def _single_segment(
    prefix: str,
    base_criteria: dict,
    ids: list[str],
    app_filter: str | None,
    existing_filter: str | None,
) -> list[dict]:
    """Build a single segment dict when app/existing filters are explicitly set."""
    suffix_parts: list[str] = []
    criteria: dict = dict(base_criteria)
    if app_filter is not None:
        suffix_parts.append("app" if app_filter == "Y" else "no_app")
        criteria["App_Installed"] = app_filter
    if existing_filter is not None:
        suffix_parts.append("existing" if existing_filter == "Y" else "prospect")
        criteria["Existing_Customer"] = existing_filter
    suffix = "_".join(suffix_parts) or "all"
    return [{
        "segment_name": f"{prefix}_{suffix}",
        "description": _segment_description(app_filter, existing_filter),
        "customer_ids": ids,
        "size": len(ids),
        "targeting_priority": _segment_priority(app_filter, existing_filter),
        "recommended_approach": _segment_approach(app_filter, existing_filter),
        "applied_criteria": criteria,
    }]


# ── Agent ─────────────────────────────────────────────────────────────────────

class CustomerSegmentationAgent(BaseAgent):
    """Mock API-backed segmentation agent.

    Processes every audience group in parallel (asyncio.gather).
    Calls POST /api/customers/filter — no local customer data needed.
    No LLM calls — all logic is deterministic.
    """

    def __init__(self, **kwargs: Any) -> None:
        kwargs.setdefault("temperature", 0.0)
        kwargs.setdefault("max_tokens", 256)
        super().__init__(**kwargs)
        self._client = MockCampaignClient()

    async def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        target_audience: Any = input_data.get("target_audience") or {}

        self._log_action("execute_start", {
            "groups": list(target_audience.keys()) if isinstance(target_audience, dict) else [],
        })

        if not isinstance(target_audience, dict) or not target_audience:
            logger.warning(
                "segmentation: target_audience is not a group dict — "
                "creating single general_audience segment"
            )
            return self._general_fallback()

        group_tasks = [
            self._process_group(name, group)
            for name, group in target_audience.items()
        ]
        group_results: list[dict] = await asyncio.gather(*group_tasks)

        all_segments: list[dict] = []
        all_distribution: dict[str, int] = {}
        for gr in group_results:
            all_segments.extend(gr["segments"])
            all_distribution.update(gr["distribution"])

        unique_qualified = {
            cid
            for seg in all_segments
            for cid in seg.get("customer_ids", [])
        }
        coverage_pct = round(len(unique_qualified) / _MOCK_TOTAL_CUSTOMERS * 100, 1)

        result = {
            "segments": all_segments,
            "total_customers": _MOCK_TOTAL_CUSTOMERS,
            "qualified_count": len(unique_qualified),
            "coverage_pct": coverage_pct,
            "distribution": all_distribution,
            "groups_detail": group_results,
        }

        self._log_action("execute_complete", {
            "groups": len(group_results),
            "total_segments": len(all_segments),
            "qualified_count": len(unique_qualified),
            "coverage_pct": coverage_pct,
        })

        return result

    # ── Per-group pipeline ────────────────────────────────────────────────────

    async def _process_group(self, group_name: str, group_data: dict) -> dict:
        """Call the filter API for a single audience group and build sub-segments."""
        prefix = group_name.lower().replace(" ", "_")
        app_filter = _first_set(group_data, "App_Installed", "app_installed")
        existing_filter = _first_set(group_data, "Existing_Customer", "existing_customer")
        base_criteria = _build_filter_body(group_data)

        if app_filter is None and existing_filter is None:
            active_ids, inactive_ids, dormant_ids = await asyncio.gather(
                self._call_filter(group_data, app_installed="Y", existing_customer="Y"),
                self._call_filter(group_data, app_installed="N", existing_customer="Y"),
                self._call_filter(group_data, existing_customer="N"),
            )
            segments = _three_way_segments(prefix, base_criteria, active_ids, inactive_ids, dormant_ids)
        else:
            ids = await self._call_filter(
                group_data, app_installed=app_filter, existing_customer=existing_filter
            )
            if not ids:
                logger.warning("segmentation: group '%s' matched 0 customers", group_name)
            segments = _single_segment(prefix, base_criteria, ids, app_filter, existing_filter) if ids else []

        qualified_count = sum(s["size"] for s in segments)
        distribution = {s["segment_name"]: s["size"] for s in segments}

        self._log_action("group_filtered", {
            "group": group_name,
            "qualified": qualified_count,
            "segments": len(segments),
        })

        return {
            "group_name": group_name,
            "qualified_count": qualified_count,
            "filter_applied": base_criteria,
            "segments": segments,
            "coverage_pct": round(qualified_count / _MOCK_TOTAL_CUSTOMERS * 100, 1),
            "distribution": distribution,
        }

    # ── Mock API call ─────────────────────────────────────────────────────────

    async def _call_filter(
        self,
        group: dict,
        *,
        app_installed: str | None = None,
        existing_customer: str | None = None,
    ) -> list[str]:
        """POST /api/customers/filter and return the customer_ids list."""
        body = _build_filter_body(group, app_installed=app_installed, existing_customer=existing_customer)
        loop = asyncio.get_event_loop()
        try:
            result = await loop.run_in_executor(
                None, lambda: self._client.filter_customers(body)
            )
            return result.get("customer_ids", [])
        except Exception as exc:
            logger.error("segmentation: filter API call failed — %s", exc)
            return []

    # ── Fallback ──────────────────────────────────────────────────────────────

    @staticmethod
    def _general_fallback() -> dict:
        """Return a single catch-all placeholder when no group criteria are available."""
        return {
            "segments": [{
                "segment_name": "general_audience",
                "description": "All customers — no audience group criteria specified",
                "customer_ids": [],
                "size": 0,
                "targeting_priority": 1,
                "recommended_approach": "Use broad, benefit-led messaging.",
                "applied_criteria": {},
            }],
            "total_customers": _MOCK_TOTAL_CUSTOMERS,
            "qualified_count": 0,
            "coverage_pct": 0.0,
            "distribution": {"general_audience": 0},
            "groups_detail": [],
        }
