"""Customer Segmentation Agent — filter-first, then segment.

Phase 1: LLM extracts AudienceCriteria from audience_who / audience_location / audience_filters.
Phase 2: Python hard-filters the full customer pool (AND logic — every active criterion must pass).
Phase 3: LLM segments the qualified pool into 3-7 prioritised, named groups.
"""

import json
import logging
from collections import defaultdict
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from app.agents.base_agent import BaseAgent
from app.models.customer import ActivityStatus, Customer, Gender

logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────

_MIN_SEGMENT_PCT = 0.05
_MAX_SEGMENTS = 7
_MIN_SEGMENTS = 3
_MIN_QUALIFIED = 10          # fall back to general_audience below this

_ALLOWED_GOALS = {"awareness", "conversion", "retention", "engagement"}

_GOAL_ACTIVITY_PRIORITY: dict[str, list[str]] = {
    "awareness":  ["inactive", "dormant", "active"],
    "conversion": ["active", "inactive", "dormant"],
    "retention":  ["active", "inactive", "dormant"],
    "engagement": ["active", "inactive", "dormant"],
}

_AGE_BRACKETS: list[tuple[int, int, str]] = [
    (0,  17,  "minors"),
    (18, 24,  "gen_z"),
    (25, 34,  "millennials"),
    (35, 44,  "gen_x_young"),
    (45, 54,  "gen_x_senior"),
    (55, 120, "seniors"),
]

_METRO_CITIES = [
    "Mumbai", "Delhi", "Bangalore", "Chennai",
    "Hyderabad", "Kolkata", "Pune", "Ahmedabad",
]

_NOT_SPECIFIED = "Not specified"


# ── Schemas ───────────────────────────────────────────────────────────────────

class AudienceCriteria(BaseModel):
    """Structured filter criteria mapped to Customer DB fields.

    Any field left None / [] means 'no filter — accept all values'.
    """
    age_min: Optional[int] = None
    age_max: Optional[int] = None
    gender: list[str] = Field(default_factory=list)
    occupation_types: list[str] = Field(default_factory=list)
    marital_status: list[str] = Field(default_factory=list)
    cities: list[str] = Field(default_factory=list)
    min_income: Optional[int] = None
    max_income: Optional[int] = None
    min_credit_score: Optional[int] = None
    max_credit_score: Optional[int] = None
    app_installed: Optional[str] = None        # "Y" | "N"
    existing_customer: Optional[str] = None    # "Y" | "N"
    kyc_status: Optional[str] = None           # "Y" | "N"
    social_media_active: Optional[str] = None  # "Y" | "N"
    min_kids: Optional[int] = None
    min_family_size: Optional[int] = None
    max_family_size: Optional[int] = None


class SegmentationInput(BaseModel):
    """Input schema for the segmentation agent."""

    customers: list[Customer]
    target_audience: str = Field(default="General audience")
    audience_who: str = ""
    audience_location: str = ""
    audience_filters: str = ""
    campaign_goal: str = "awareness"

    @field_validator("campaign_goal")
    @classmethod
    def validate_goal(cls, v: str) -> str:
        normalised = v.lower().strip()
        return normalised if normalised in _ALLOWED_GOALS else "awareness"

    @field_validator("customers")
    @classmethod
    def require_customers(cls, v: list[Customer]) -> list[Customer]:
        if not v:
            raise ValueError("customers list must not be empty")
        return v


class SegmentOut(BaseModel):
    """A single named customer segment."""

    segment_name: str
    description: str
    customer_ids: list[str]
    size: int = 0
    targeting_priority: int = Field(..., ge=1, le=5)
    recommended_approach: str

    @model_validator(mode="after")
    def sync_size(self) -> "SegmentOut":
        self.size = len(self.customer_ids)
        return self


class SegmentationResult(BaseModel):
    """Full output of the segmentation agent."""

    segments: list[SegmentOut]
    total_customers: int
    qualified_count: int
    filter_applied: AudienceCriteria
    coverage_pct: float
    distribution: dict[str, int] = Field(default_factory=dict)

    @model_validator(mode="after")
    def sort_and_distribute(self) -> "SegmentationResult":
        self.segments = sorted(self.segments, key=lambda s: s.targeting_priority, reverse=True)
        self.distribution = {s.segment_name: s.size for s in self.segments}
        return self


# ── Prompts ───────────────────────────────────────────────────────────────────

_CRITERIA_EXTRACTION_TEMPLATE = """\
You are a data analyst. Parse the audience description below and map each piece of \
information to the exact Customer database field it corresponds to.
Return ONLY a valid JSON object — no markdown, no extra text.

## Audience description
audience_who      : {audience_who}
audience_location : {audience_location}
audience_filters  : {audience_filters}

## Customer DB field reference (map to these exact field names and value formats)
- age_min / age_max         : int — age range (e.g. "aged 25-45" → age_min=25, age_max=45)
- gender                    : list[str] — "Male" | "Female" | "Other"
- occupation_types          : list[str] — "Full-time" | "Part-time" | "Self-employed" | "Retired" | "Student"
  (map "salaried"→Full-time, "self-employed"→Self-employed, "retired"→Retired, "student"→Student)
- marital_status            : list[str] — "Married" | "Single" | "Divorced" | "Widowed"
- cities                    : list[str] — exact city names
  (expand "Metro cities" → ["Mumbai","Delhi","Bangalore","Chennai","Hyderabad","Kolkata","Pune","Ahmedabad"])
  (expand "Tier-1" → same as Metro; "Tier-2" → ["Jaipur","Lucknow","Surat","Kanpur","Nagpur","Indore"])
- min_income / max_income   : int — Monthly_Income in ₹ (strip ₹ symbol and "k" multiplier)
- min_credit_score / max_credit_score : int — Credit_score range 300–850
- app_installed             : "Y" | "N" | null
- existing_customer         : "Y" | "N" | null
- kyc_status                : "Y" | "N" | null  (map "KYC verified"→"Y")
- social_media_active       : "Y" | "N" | null
- min_kids                  : int | null — minimum Kids_in_Household
- min_family_size / max_family_size : int | null — Family_Size range

## IMPORTANT: Multiple audience groups
If the audience is described as multiple separate groups (e.g. "Group 1: ..., Group 2: ..."),
you MUST produce a SINGLE merged criteria object that covers ALL groups together, using the most
permissive (inclusive) values so that every group's members can qualify:
- age_min: minimum of all groups' age_min values
- age_max: maximum of all groups' age_max values (omit if any group has no upper bound)
- gender, occupation_types, marital_status, cities: UNION of all values across all groups
- min_income: lowest threshold mentioned across all groups (most permissive)
- max_income: highest upper-bound mentioned, or null if any group has no upper bound
- Boolean flags (app_installed, kyc_status, existing_customer, social_media_active):
    • Set to "Y" / "N" only when EVERY group specifies the SAME value for that flag.
    • If groups disagree or any group omits the flag, set it to null (no restriction).

## Rules
- Set ONLY fields that are explicitly mentioned in the audience description.
- Leave all other fields as null or [].
- Do NOT invent criteria not stated in the input.
- Always return a SINGLE flat JSON object, never an array.

## Required JSON schema
{{
  "age_min": <int|null>,
  "age_max": <int|null>,
  "gender": [],
  "occupation_types": [],
  "marital_status": [],
  "cities": [],
  "min_income": <int|null>,
  "max_income": <int|null>,
  "min_credit_score": <int|null>,
  "max_credit_score": <int|null>,
  "app_installed": <"Y"|"N"|null>,
  "existing_customer": <"Y"|"N"|null>,
  "kyc_status": <"Y"|"N"|null>,
  "social_media_active": <"Y"|"N"|null>,
  "min_kids": <int|null>,
  "min_family_size": <int|null>,
  "max_family_size": <int|null>
}}
"""

_SEGMENTATION_TEMPLATE = """\
You are an expert marketing analyst. A filter has already been applied: only the \
{qualified_count} customers below qualified against all audience criteria. Your task \
is to divide this qualified pool into {min_seg}–{max_seg} meaningful sub-segments.

## Campaign context
- Target audience : {target_audience}
- Campaign goal   : {campaign_goal}
- Filters applied : {filter_summary}

## Qualified pool summary  ({qualified_count} of {total_count} total customers)

Age distribution :
{age_distribution}

Gender distribution :
{gender_distribution}

Activity status (Existing_Customer + App_Installed) :
{activity_distribution}

Location top-5 :
{location_distribution}

## Pre-computed sub-groups (within the qualified pool)
Each line is a named group you may reference. Group names are exact — copy them precisely.
{candidate_groups}

## Instructions
1. Choose {min_seg}–{max_seg} sub-groups from the list above that best serve the campaign goal.
2. You may combine multiple groups into one segment by listing all relevant group names.
3. Merge similar groups if needed; every segment must cover ≥ {min_pct_int}% of the qualified pool.
4. Together your segments must cover ALL pre-computed groups so that every qualified customer
   belongs to at least one segment.
5. Assign targeting_priority (1–5, 5=highest) based on fit with the goal.
6. Respond with ONLY a valid JSON array — no markdown, no extra text.

## IMPORTANT
- The "candidate_groups" field must contain group names copied EXACTLY from the
  "Pre-computed sub-groups" section above.
- Do NOT invent customer IDs or group names — reference only the names listed above.

## Required JSON schema for each element
{{
  "segment_name"       : "<snake_case label for this segment>",
  "description"        : "<why this sub-segment matters for the campaign>",
  "candidate_groups"   : ["<exact_group_name_from_list>", ...],
  "targeting_priority" : <1-5>,
  "recommended_approach": "<1-2 sentence tactical guidance>"
}}
"""


# ── Agent ─────────────────────────────────────────────────────────────────────

class CustomerSegmentationAgent(BaseAgent):
    """Three-phase segmentation: extract criteria → hard-filter → LLM-segment."""

    def __init__(self, **kwargs: Any) -> None:
        kwargs.setdefault("temperature", 0.1)
        kwargs.setdefault("max_tokens", 2048)
        super().__init__(**kwargs)

    # ── Public interface ──────────────────────────────────────────────────────

    async def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        seg_input: SegmentationInput = self._validate_input(input_data, SegmentationInput)
        total = len(seg_input.customers)

        self._log_action("execute_start", {
            "total_customers": total,
            "campaign_goal": seg_input.campaign_goal,
            "audience_who": seg_input.audience_who,
            "audience_location": seg_input.audience_location,
            "audience_filters": seg_input.audience_filters,
        })

        # ── Phase 1: Extract criteria via LLM ────────────────────────────────
        criteria = await self._extract_criteria(seg_input)
        self._log_action("criteria_extracted", criteria.model_dump())

        # ── Phase 2: Hard-filter (Python, AND logic) ──────────────────────────
        qualified = self._apply_criteria(seg_input.customers, criteria)
        qualified_count = len(qualified)

        self._log_action("candidates_filtered", {
            "total": total,
            "qualified": qualified_count,
            "filter_rate_pct": round(qualified_count / total * 100, 1) if total else 0,
        })

        # Fallback: too few qualified → use everyone with a warning
        if qualified_count < _MIN_QUALIFIED:
            logger.warning(
                "segmentation: only %d customers qualified — "
                "falling back to full pool", qualified_count
            )
            qualified = seg_input.customers
            qualified_count = total

        # ── Phase 3: Segment the qualified pool via LLM ───────────────────────
        segments_list = await self._segment_pool(seg_input, qualified, total, criteria)

        # Strip any hallucinated/invalid IDs the LLM may have produced.
        # Only customer_ids that exist in the qualified pool are kept;
        # _ensure_coverage below will then fill gaps with the real unassigned IDs.
        valid_cid_set = {c.customer_id for c in qualified}
        for seg in segments_list:
            seg["customer_ids"] = [
                cid for cid in seg.get("customer_ids", []) if cid in valid_cid_set
            ]

        # Ensure full coverage of qualified pool
        segments_list = self._ensure_coverage(segments_list, qualified)

        # Validate through Pydantic
        validated: list[SegmentOut] = []
        for seg_dict in segments_list:
            try:
                validated.append(SegmentOut(**seg_dict))
            except Exception as exc:
                self._log_action("segment_validation_warning", {
                    "error": str(exc), "segment": seg_dict,
                })

        assigned_ids: set[str] = set()
        for seg in validated:
            assigned_ids.update(seg.customer_ids)
        coverage_pct = round(len(assigned_ids) / qualified_count * 100, 1) if qualified_count else 0.0

        result = SegmentationResult(
            segments=validated,
            total_customers=total,
            qualified_count=qualified_count,
            filter_applied=criteria,
            coverage_pct=coverage_pct,
        )

        self._log_action("execute_complete", {
            "segments_created": len(result.segments),
            "qualified_count": qualified_count,
            "coverage_pct": result.coverage_pct,
            "distribution": result.distribution,
        })

        return result.model_dump()

    # ── Phase 1: Criteria extraction ──────────────────────────────────────────

    async def _extract_criteria(self, seg_input: SegmentationInput) -> AudienceCriteria:
        """Call LLM to parse audience strings → AudienceCriteria."""
        has_audience_info = any([
            seg_input.audience_who,
            seg_input.audience_location,
            seg_input.audience_filters,
        ])
        if not has_audience_info:
            return AudienceCriteria()

        prompt = _CRITERIA_EXTRACTION_TEMPLATE.format(
            audience_who=seg_input.audience_who or _NOT_SPECIFIED,
            audience_location=seg_input.audience_location or _NOT_SPECIFIED,
            audience_filters=seg_input.audience_filters or _NOT_SPECIFIED,
        )
        raw = await self._retry_with_backoff(self._call_llm, prompt)
        parsed = self._parse_llm_output(raw)

        # LLM returned an array of per-group criteria — merge into one
        if isinstance(parsed, list):
            parsed = self._merge_criteria_list(parsed)

        if not isinstance(parsed, dict):
            logger.warning("Criteria extraction returned non-dict; using empty criteria")
            return AudienceCriteria()
        try:
            return AudienceCriteria(**parsed)
        except Exception as exc:
            logger.warning("AudienceCriteria validation failed (%s); using empty criteria", exc)
            return AudienceCriteria()

    @staticmethod
    def _merge_criteria_list(criteria_list: list) -> dict:
        """Merge a list of per-group criteria dicts into one permissive union criteria."""
        dicts = [c for c in criteria_list if isinstance(c, dict)]
        if not dicts:
            return {}
        merged: dict = {}
        CustomerSegmentationAgent._merge_age(dicts, merged)
        CustomerSegmentationAgent._merge_list_fields(dicts, merged)
        CustomerSegmentationAgent._merge_income(dicts, merged)
        CustomerSegmentationAgent._merge_flags(dicts, merged)
        return merged

    @staticmethod
    def _merge_age(dicts: list[dict], merged: dict) -> None:
        age_mins = [c["age_min"] for c in dicts if c.get("age_min") is not None]
        age_maxs = [c["age_max"] for c in dicts if c.get("age_max") is not None]
        if age_mins:
            merged["age_min"] = min(age_mins)
        if age_maxs and len(age_maxs) == len(dicts):
            merged["age_max"] = max(age_maxs)

    @staticmethod
    def _merge_list_fields(dicts: list[dict], merged: dict) -> None:
        for field in ("gender", "occupation_types", "marital_status", "cities"):
            vals: set = set()
            for c in dicts:
                vals.update(c.get(field) or [])
            if vals:
                merged[field] = list(vals)

    @staticmethod
    def _merge_income(dicts: list[dict], merged: dict) -> None:
        min_incomes = [c["min_income"] for c in dicts if c.get("min_income") is not None]
        if min_incomes:
            merged["min_income"] = min(min_incomes)
        max_incomes = [c["max_income"] for c in dicts if c.get("max_income") is not None]
        if max_incomes and len(max_incomes) == len(dicts):
            merged["max_income"] = max(max_incomes)

    @staticmethod
    def _merge_flags(dicts: list[dict], merged: dict) -> None:
        n = len(dicts)
        for flag in ("app_installed", "kyc_status", "existing_customer", "social_media_active"):
            flag_vals = [c[flag] for c in dicts if c.get(flag) is not None]
            unanimous = len(flag_vals) == n and len(set(flag_vals)) == 1
            if unanimous:
                merged[flag] = flag_vals[0]

    # ── Phase 2: Hard filter (AND logic) ─────────────────────────────────────

    @staticmethod
    def _check_demographic(cust: Customer, c: AudienceCriteria) -> bool:
        return all([
            c.age_min is None or cust.Age >= c.age_min,
            c.age_max is None or cust.Age <= c.age_max,
            not c.gender or cust.Gender in c.gender,
            not c.occupation_types or cust.Occupation_type in c.occupation_types,
            not c.marital_status or cust.Marital_Status in c.marital_status,
        ])

    @staticmethod
    def _check_financial(cust: Customer, c: AudienceCriteria) -> bool:
        return all([
            c.min_income is None or cust.Monthly_Income >= c.min_income,
            c.max_income is None or cust.Monthly_Income <= c.max_income,
            c.min_credit_score is None or cust.Credit_score >= c.min_credit_score,
            c.max_credit_score is None or cust.Credit_score <= c.max_credit_score,
        ])

    @staticmethod
    def _check_flags(cust: Customer, c: AudienceCriteria) -> bool:
        return all([
            c.app_installed is None or cust.App_Installed == c.app_installed,
            c.existing_customer is None or cust.Existing_Customer == c.existing_customer,
            c.kyc_status is None or cust.KYC_status == c.kyc_status,
            c.social_media_active is None or cust.Social_Media_Active == c.social_media_active,
        ])

    @staticmethod
    def _check_household(cust: Customer, c: AudienceCriteria) -> bool:
        return all([
            c.min_kids is None or cust.Kids_in_Household >= c.min_kids,
            c.min_family_size is None or cust.Family_Size >= c.min_family_size,
            c.max_family_size is None or cust.Family_Size <= c.max_family_size,
        ])

    @staticmethod
    def _customer_qualifies(cust: Customer, c: AudienceCriteria) -> bool:
        """Return True if the customer satisfies ALL non-null criteria (AND logic)."""
        return (
            (not c.cities or cust.City in c.cities)
            and CustomerSegmentationAgent._check_demographic(cust, c)
            and CustomerSegmentationAgent._check_financial(cust, c)
            and CustomerSegmentationAgent._check_flags(cust, c)
            and CustomerSegmentationAgent._check_household(cust, c)
        )

    @staticmethod
    def _apply_criteria(customers: list[Customer], c: AudienceCriteria) -> list[Customer]:
        """Return customers that satisfy ALL non-null criteria (AND logic)."""
        return [
            cust for cust in customers
            if CustomerSegmentationAgent._customer_qualifies(cust, c)
        ]

    # ── Phase 3: Segment the qualified pool ───────────────────────────────────

    async def _segment_pool(
        self,
        seg_input: SegmentationInput,
        qualified: list[Customer],
        total_count: int,
        criteria: AudienceCriteria,
    ) -> list[dict]:
        qualified_count = len(qualified)
        summaries = self._build_summaries(qualified)
        candidate_groups = self._build_candidate_groups(qualified, seg_input.campaign_goal)
        candidate_text = self._format_candidates(candidate_groups, qualified_count)
        filter_summary = self._summarise_criteria(criteria)

        prompt = _SEGMENTATION_TEMPLATE.format(
            qualified_count=qualified_count,
            total_count=total_count,
            min_seg=_MIN_SEGMENTS,
            max_seg=_MAX_SEGMENTS,
            target_audience=seg_input.target_audience,
            campaign_goal=seg_input.campaign_goal,
            filter_summary=filter_summary,
            age_distribution=summaries["age"],
            gender_distribution=summaries["gender"],
            activity_distribution=summaries["activity"],
            location_distribution=summaries["location"],
            candidate_groups=candidate_text,
            min_pct_int=int(_MIN_SEGMENT_PCT * 100),
        )

        raw = await self._retry_with_backoff(self._call_llm, prompt)
        parsed = self._parse_llm_output(raw)
        segments = self._extract_segment_list(parsed, raw)
        return self._resolve_customer_ids(segments, candidate_groups)

    @staticmethod
    def _extract_segment_list(parsed: Any, raw: str) -> list[dict]:
        """Coerce the LLM output into a flat list of segment dicts."""
        if isinstance(parsed, list):
            return parsed
        if isinstance(parsed, dict):
            for key in ("segments", "data"):
                if isinstance(parsed.get(key), list):
                    return parsed[key]
            first_val = next(iter(parsed.values()), None)
            if isinstance(first_val, list):
                return first_val
        try:
            result = json.loads(raw) if isinstance(raw, str) else []
            return result if isinstance(result, list) else []
        except Exception:
            return []

    @staticmethod
    def _resolve_customer_ids(
        segments: list[dict], candidate_groups: dict[str, list[str]]
    ) -> list[dict]:
        """Replace each segment's 'candidate_groups' names with actual customer_ids.

        The LLM returns group names (e.g. "gen_x_senior_active"); this method
        looks up those names in the pre-computed candidate_groups map and unions
        the real customer IDs into each segment's customer_ids list.
        """
        for seg in segments:
            group_names = seg.pop("candidate_groups", None)
            if group_names and isinstance(group_names, list):
                ids: set[str] = set()
                for gname in group_names:
                    ids.update(candidate_groups.get(gname, []))
                seg["customer_ids"] = list(ids)
            elif not seg.get("customer_ids"):
                seg["customer_ids"] = []
        return segments

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _build_candidate_groups(
        self, customers: list[Customer], goal: str
    ) -> dict[str, list[str]]:
        """Sub-group the qualified pool by activity, age bracket, and combined dims."""
        groups: dict[str, list[str]] = defaultdict(list)
        priority_statuses = _GOAL_ACTIVITY_PRIORITY.get(goal, ["active"])

        for c in customers:
            cid = c.customer_id
            bracket = self._age_bracket(c.Age)
            status = c.activity_status.value

            groups[bracket].append(cid)
            groups[f"status_{status}"].append(cid)
            if status == priority_statuses[0]:
                groups[f"high_priority_{priority_statuses[0]}"].append(cid)
            if c.Gender in (Gender.MALE, Gender.FEMALE):
                groups[f"gender_{c.Gender}"].append(cid)
            groups[f"{bracket}_{status}"].append(cid)

        return dict(groups)

    @staticmethod
    def _age_bracket(age: int) -> str:
        for low, high, label in _AGE_BRACKETS:
            if low <= age <= high:
                return label
        return "other_age"

    def _build_summaries(self, customers: list[Customer]) -> dict[str, str]:
        total = len(customers)
        age_c: dict[str, int] = defaultdict(int)
        gender_c: dict[str, int] = defaultdict(int)
        loc_c: dict[str, int] = defaultdict(int)
        activity_c: dict[str, int] = defaultdict(int)

        for c in customers:
            age_c[self._age_bracket(c.Age)] += 1
            gender_c[c.Gender] += 1
            loc_c[c.City] += 1
            activity_c[c.activity_status.value] += 1

        def _fmt(counts: dict[str, int]) -> str:
            return "\n".join(
                f"  {k}: {v} ({v / total * 100:.1f}%)"
                for k, v in sorted(counts.items(), key=lambda x: -x[1])
            )

        top5_locs = dict(sorted(loc_c.items(), key=lambda x: -x[1])[:5])
        return {
            "age": _fmt(age_c),
            "gender": _fmt(gender_c),
            "location": _fmt(top5_locs),
            "activity": _fmt(activity_c),
        }

    @staticmethod
    def _format_candidates(groups: dict[str, list[str]], total: int) -> str:
        lines: list[str] = []
        for name, ids in sorted(groups.items(), key=lambda x: -len(x[1])):
            pct = len(ids) / total * 100 if total else 0
            if pct < _MIN_SEGMENT_PCT * 100:
                continue
            lines.append(f"  {name} ({len(ids)} customers, {pct:.1f}%)")
        return "\n".join(lines) if lines else "  (no sub-groups met minimum size)"

    @staticmethod
    def _membership_parts(criteria: AudienceCriteria) -> list[str]:
        """Return label strings for list-membership and city criteria."""
        parts: list[str] = []
        for attr, label in [
            ("gender", "Gender"),
            ("occupation_types", "Occupation_type"),
            ("marital_status", "Marital_Status"),
        ]:
            vals = getattr(criteria, attr)
            if vals:
                parts.append(f"{label} ∈ {vals}")
        cities = criteria.cities
        if cities:
            parts.append(f"City ∈ {cities[:4]}{'…' if len(cities) > 4 else ''}")
        return parts

    @staticmethod
    def _flag_parts(criteria: AudienceCriteria) -> list[str]:
        """Return label strings for Y/N flag and household criteria."""
        parts: list[str] = []
        for attr, label in [
            ("app_installed", "App_Installed"),
            ("existing_customer", "Existing_Customer"),
            ("kyc_status", "KYC_status"),
            ("social_media_active", "Social_Media_Active"),
        ]:
            flag = getattr(criteria, attr)
            if flag is not None:
                parts.append(f"{label} = {flag}")
        if criteria.min_kids is not None:
            parts.append(f"Kids_in_Household ≥ {criteria.min_kids}")
        if criteria.min_family_size is not None:
            parts.append(f"Family_Size ≥ {criteria.min_family_size}")
        return parts

    @staticmethod
    def _summarise_criteria(criteria: AudienceCriteria) -> str:
        parts: list[str] = []

        lo, hi = criteria.age_min, criteria.age_max
        if lo is not None or hi is not None:
            parts.append(f"Age {lo or ''}–{hi or ''}")

        parts.extend(CustomerSegmentationAgent._membership_parts(criteria))

        if criteria.min_income is not None:
            parts.append(f"Monthly_Income ≥ ₹{criteria.min_income:,}")
        if criteria.max_income is not None:
            parts.append(f"Monthly_Income ≤ ₹{criteria.max_income:,}")
        if criteria.min_credit_score is not None:
            parts.append(f"Credit_score ≥ {criteria.min_credit_score}")

        parts.extend(CustomerSegmentationAgent._flag_parts(criteria))

        return "; ".join(parts) if parts else "None (all customers eligible)"

    def _ensure_coverage(
        self, segments_list: list[dict], qualified: list[Customer]
    ) -> list[dict]:
        assigned: set[str] = set()
        for seg in segments_list:
            assigned.update(seg.get("customer_ids", []))

        unassigned = [c.customer_id for c in qualified if c.customer_id not in assigned]
        if not unassigned:
            return segments_list

        self._log_action("coverage_gap", {"unassigned_count": len(unassigned)})
        if segments_list:
            lowest = min(segments_list, key=lambda s: s.get("targeting_priority", 1))
            lowest["customer_ids"] = list(set(lowest.get("customer_ids", [])) | set(unassigned))
        else:
            segments_list.append({
                "segment_name": "general_audience",
                "description": "All qualified customers — no finer segmentation was possible.",
                "customer_ids": [c.customer_id for c in qualified],
                "targeting_priority": 1,
                "recommended_approach": "Use broad, general messaging.",
            })
        return segments_list

    async def _call_llm(self, prompt: str) -> str:
        response = await self.llm.ainvoke(prompt)
        return response.content if hasattr(response, "content") else str(response)
