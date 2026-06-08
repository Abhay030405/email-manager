"""CustomerSegmentationAgent — pure-Python, multi-group parallel segmentation.

Flow per group (runs in parallel across all groups via asyncio.gather):
  Step 2 — Hard filter:
    Apply all group criteria EXCEPT App_Installed / Existing_Customer (AND logic).
    Return eligible customers + pass App_Installed / Existing_Customer through for Step 3.

  Step 3 — Sub-segmentation by App_Installed × Existing_Customer:
    Both null  → 3 segments: active (App=Y + Existing=Y),
                              inactive (Existing=Y, any app),
                              dormant (Existing=N)
    ≥1 specified → 1 segment filtered to only the matching customers.

No LLM calls — all logic is deterministic Python.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from pydantic import BaseModel, Field, model_validator

from app.agents.base_agent import BaseAgent


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

logger = logging.getLogger(__name__)

# ── City normalisation ────────────────────────────────────────────────────────

_CITY_ALIASES: dict[str, str] = {
    "bengaluru": "bangalore",
    "bengalur":  "bangalore",
    "new delhi": "delhi",
    "calcutta":  "kolkata",
    "bombay":    "mumbai",
}


def _normalize_city(city: str) -> str:
    lower = city.lower().strip()
    return _CITY_ALIASES.get(lower, lower)


def _city_matches(customer_city: str, allowed: list[str]) -> bool:
    cc = _normalize_city(customer_city)
    return any(_normalize_city(c) == cc for c in allowed)


def _parse_cities(city_raw: str | None) -> list[str] | None:
    """Parse a city string into a list of city names.

    Returns None (= no filter) when the string is empty or expresses
    'any city' / 'all cities' / tier-based broad catchments.
    """
    if not city_raw:
        return None
    lower = city_raw.lower()
    if "any" in lower or "all " in lower:
        return None

    cleaned = city_raw.replace(" and ", ",").replace(" & ", ",")
    cities = [c.strip() for c in cleaned.split(",") if c.strip()]
    # Drop description fragments (e.g. "Tier-2 cities like")
    cities = [
        c for c in cities
        if len(c) <= 25
        and not any(w in c.lower() for w in ("including", "tier", "cities", "like"))
    ]
    return cities if cities else None


# ── Step 2: field-level hard filter ──────────────────────────────────────────

class _GroupCriteria:
    """Pre-computed, immutable filter criteria for one audience group.

    App_Installed and Existing_Customer are intentionally excluded here —
    they are handled separately in Step 3 (sub-segmentation).
    """

    __slots__ = (
        "min_age", "max_age", "marital_status", "occupation_type",
        "occupation", "min_income", "kyc_status", "cities",
        "min_credit_score", "social_media", "min_kids", "min_family",
    )

    def __init__(self, group: dict) -> None:
        self.min_age         = group.get("min_age")
        self.max_age         = group.get("max_age")
        self.marital_status  = group.get("Marital_Status")
        self.occupation_type = group.get("Occupation_type")
        self.occupation      = group.get("Occupation")
        self.min_income      = group.get("Monthly_Income")
        self.kyc_status      = group.get("KYC_status")
        self.cities          = _parse_cities(group.get("City"))
        self.min_credit_score = group.get("Credit_score")
        self.social_media    = group.get("Social_Media_Active")
        self.min_kids        = group.get("Kids_in_Household")
        self.min_family      = group.get("Family_Size")

    @property
    def filter_applied(self) -> dict:
        result: dict = {}
        if self.min_age is not None:        result["age_min"]            = self.min_age
        if self.max_age is not None:        result["age_max"]            = self.max_age
        if self.marital_status:             result["marital_status"]     = self.marital_status
        if self.occupation_type:            result["occupation_type"]    = self.occupation_type
        if self.occupation:                 result["occupation"]         = self.occupation
        if self.min_income is not None:     result["min_income"]         = self.min_income
        if self.kyc_status:                 result["kyc_status"]         = self.kyc_status
        if self.cities:                     result["cities"]             = self.cities
        if self.min_credit_score is not None: result["min_credit_score"] = self.min_credit_score
        if self.social_media:               result["social_media_active"] = self.social_media
        if self.min_kids is not None:       result["min_kids"]           = self.min_kids
        if self.min_family is not None:     result["min_family_size"]    = self.min_family
        return result


def _check_age(c: dict, cr: _GroupCriteria) -> bool:
    age = c.get("Age") or 0
    if cr.min_age is not None and age < cr.min_age:
        return False
    if cr.max_age is not None and age > cr.max_age:
        return False
    return True


def _check_demographics(c: dict, cr: _GroupCriteria) -> bool:
    if cr.marital_status and c.get("Marital_Status") != cr.marital_status:
        return False
    if cr.occupation_type and c.get("Occupation_type") != cr.occupation_type:
        return False
    if cr.occupation and c.get("Occupation") != cr.occupation:
        return False
    return True


def _check_financials(c: dict, cr: _GroupCriteria) -> bool:
    if cr.min_income is not None and (c.get("Monthly_Income") or 0) < cr.min_income:
        return False
    if cr.min_credit_score is not None and (c.get("Credit_score") or 0) < cr.min_credit_score:
        return False
    return True


def _check_flags_and_location(c: dict, cr: _GroupCriteria) -> bool:
    if cr.kyc_status and c.get("KYC_status") != cr.kyc_status:
        return False
    if cr.social_media and c.get("Social_Media_Active") != cr.social_media:
        return False
    if cr.cities and not _city_matches(str(c.get("City") or ""), cr.cities):
        return False
    return True


def _check_household(c: dict, cr: _GroupCriteria) -> bool:
    if cr.min_kids is not None and (c.get("Kids_in_Household") or 0) < cr.min_kids:
        return False
    if cr.min_family is not None and (c.get("Family_Size") or 0) < cr.min_family:
        return False
    return True


def _customer_passes(c: dict, cr: _GroupCriteria) -> bool:
    return (
        _check_age(c, cr)
        and _check_demographics(c, cr)
        and _check_financials(c, cr)
        and _check_flags_and_location(c, cr)
        and _check_household(c, cr)
    )


def _filter_customers(
    customers: list[dict], group: dict
) -> tuple[list[dict], dict]:
    """Apply all group criteria EXCEPT App_Installed and Existing_Customer.

    Returns (eligible_customers, filter_applied_dict).
    Monthly_Income and Credit_score are treated as minimum thresholds (≥).
    """
    cr = _GroupCriteria(group)
    eligible = [c for c in customers if _customer_passes(c, cr)]
    return eligible, cr.filter_applied


# ── Step 3: App_Installed × Existing_Customer sub-segmentation ────────────────

def _get_customer_id(c: dict) -> str:
    return str(c.get("customer_id") or c.get("_id") or "")


def _segment_suffix(app: str | None, existing: str | None) -> str:
    parts: list[str] = []
    if app == "Y":      parts.append("app")
    elif app == "N":    parts.append("no_app")
    if existing == "Y": parts.append("existing")
    elif existing == "N": parts.append("prospect")
    return "_".join(parts) or "all"


def _segment_description(app: str | None, existing: str | None) -> str:
    descs: list[str] = []
    if app == "Y":        descs.append("app installed")
    elif app == "N":      descs.append("app not installed")
    if existing == "Y":   descs.append("existing customer")
    elif existing == "N": descs.append("non-customer (prospect)")
    return " — ".join(descs) if descs else "all eligible customers"


def _segment_priority(app: str | None, existing: str | None) -> int:
    if app == "Y" and existing == "Y": return 5
    if app == "Y" and existing == "N": return 4
    if app == "Y":    return 4
    if existing == "Y": return 3
    if existing == "N": return 3
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


def _make_segment(
    name: str,
    customers: list[dict],
    description: str,
    priority: int,
    approach: str,
    applied_criteria: dict,
) -> dict:
    return {
        "segment_name": name,
        "description": description,
        "customer_ids": [_get_customer_id(c) for c in customers],
        "size": len(customers),
        "targeting_priority": priority,
        "recommended_approach": approach,
        "applied_criteria": applied_criteria,
    }


def _create_sub_segments(
    group_name: str,
    eligible: list[dict],
    app_filter: str | None,
    existing_filter: str | None,
) -> list[dict]:
    """Step 3: sub-divide eligible pool by App_Installed × Existing_Customer.

    Both null  → 3 segments (active / inactive / dormant).
    ≥1 specified → 1 segment filtered to matching customers only.
    """
    prefix = group_name.lower().replace(" ", "_")  # "group_1", "group_2"

    if app_filter is None and existing_filter is None:
        # ── Both unspecified → 3-way activity split ───────────────────────────
        active   = [c for c in eligible
                    if c.get("App_Installed") == "Y" and c.get("Existing_Customer") == "Y"]
        inactive = [c for c in eligible
                    if c.get("Existing_Customer") == "Y" and c.get("App_Installed") != "Y"]
        dormant  = [c for c in eligible if c.get("Existing_Customer") == "N"]

        segments: list[dict] = []
        if active:
            segments.append(_make_segment(
                f"{prefix}_active", active,
                "Active customers — app installed + existing relationship",
                5, "Lead with loyalty and retention messaging. Upsell focus.",
                {"App_Installed": "Y", "Existing_Customer": "Y"},
            ))
        if inactive:
            segments.append(_make_segment(
                f"{prefix}_inactive", inactive,
                "Existing customers without the app — re-engagement opportunity",
                3, "Drive app install with benefit-led messaging.",
                {"App_Installed": "N", "Existing_Customer": "Y"},
            ))
        if dormant:
            segments.append(_make_segment(
                f"{prefix}_dormant", dormant,
                "Non-customers — acquisition focus",
                4, "Welcome framing. Emphasise simplicity of sign-up.",
                {"Existing_Customer": "N"},
            ))
        return segments

    # ── At least one is specified → single filtered segment ──────────────────
    pool = eligible
    criteria: dict = {}

    if app_filter is not None:
        pool = [c for c in pool if c.get("App_Installed") == app_filter]
        criteria["App_Installed"] = app_filter
    if existing_filter is not None:
        pool = [c for c in pool if c.get("Existing_Customer") == existing_filter]
        criteria["Existing_Customer"] = existing_filter

    if not pool:
        return []

    suffix = _segment_suffix(app_filter, existing_filter)
    return [_make_segment(
        f"{prefix}_{suffix}",
        pool,
        _segment_description(app_filter, existing_filter),
        _segment_priority(app_filter, existing_filter),
        _segment_approach(app_filter, existing_filter),
        criteria,
    )]


# ── Agent ─────────────────────────────────────────────────────────────────────

class CustomerSegmentationAgent(BaseAgent):
    """Pure-Python segmentation agent.

    Processes every audience group in parallel (asyncio.gather).
    No LLM calls — all filtering and sub-segmentation is deterministic.
    """

    def __init__(self, **kwargs: Any) -> None:
        kwargs.setdefault("temperature", 0.0)
        kwargs.setdefault("max_tokens", 256)
        super().__init__(**kwargs)

    async def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        customers: list[dict] = input_data.get("customers") or []
        target_audience: Any = input_data.get("target_audience") or {}
        total_count = len(customers)

        self._log_action("execute_start", {
            "total_customers": total_count,
            "groups": list(target_audience.keys()) if isinstance(target_audience, dict) else [],
        })

        # Handle legacy callers that still pass target_audience as a string
        if not isinstance(target_audience, dict) or not target_audience:
            logger.warning(
                "segmentation: target_audience is not a group dict — "
                "creating single general_audience segment"
            )
            return self._general_fallback(customers, total_count)

        # ── Process all groups in parallel ────────────────────────────────────
        group_tasks = [
            self._process_group(name, group, customers, total_count)
            for name, group in target_audience.items()
        ]
        group_results: list[dict] = await asyncio.gather(*group_tasks)

        # ── Flatten segments from all groups ──────────────────────────────────
        all_segments: list[dict] = []
        all_distribution: dict[str, int] = {}
        for gr in group_results:
            all_segments.extend(gr["segments"])
            all_distribution.update(gr["distribution"])

        # Unique qualified customer IDs across all groups
        unique_qualified = {
            cid
            for seg in all_segments
            for cid in seg.get("customer_ids", [])
        }
        coverage_pct = round(len(unique_qualified) / total_count * 100, 1) if total_count else 0.0

        result = {
            "segments": all_segments,
            "total_customers": total_count,
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

    async def _process_group(
        self,
        group_name: str,
        group_data: dict,
        customers: list[dict],
        total_count: int,
    ) -> dict:
        """Steps 2 + 3 for a single audience group."""

        # Step 2 — hard filter (excludes App_Installed, Existing_Customer)
        eligible, filter_applied = _filter_customers(customers, group_data)
        qualified_count = len(eligible)

        self._log_action("group_filtered", {
            "group": group_name,
            "eligible": qualified_count,
            "total": total_count,
        })

        if qualified_count == 0:
            logger.warning("segmentation: group '%s' matched 0 customers", group_name)
            return {
                "group_name": group_name,
                "qualified_count": 0,
                "total_count": total_count,
                "filter_applied": filter_applied,
                "segments": [],
                "coverage_pct": 0.0,
                "distribution": {},
            }

        # Pass App_Installed + Existing_Customer through to Step 3
        app_filter      = group_data.get("App_Installed")
        existing_filter = group_data.get("Existing_Customer")

        # Step 3 — sub-segment by App_Installed × Existing_Customer
        segments = _create_sub_segments(
            group_name, eligible, app_filter, existing_filter
        )

        distribution = {s["segment_name"]: s["size"] for s in segments}
        covered = sum(s["size"] for s in segments)
        coverage_pct = round(covered / qualified_count * 100, 1) if qualified_count else 0.0

        return {
            "group_name": group_name,
            "qualified_count": qualified_count,
            "total_count": total_count,
            "filter_applied": filter_applied,
            "segments": segments,
            "coverage_pct": coverage_pct,
            "distribution": distribution,
        }

    # ── Fallback ──────────────────────────────────────────────────────────────

    @staticmethod
    def _general_fallback(customers: list[dict], total_count: int) -> dict:
        """Return a single catch-all segment when no group criteria are available."""
        segment = _make_segment(
            "general_audience",
            customers,
            "All customers — no audience group criteria specified",
            1,
            "Use broad, benefit-led messaging.",
            {},
        )
        return {
            "segments": [segment],
            "total_customers": total_count,
            "qualified_count": total_count,
            "coverage_pct": 100.0,
            "distribution": {"general_audience": total_count},
            "groups_detail": [],
        }
