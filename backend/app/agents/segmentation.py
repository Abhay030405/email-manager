"""Customer Segmentation Agent — groups customers into meaningful campaign segments."""

import logging
from collections import defaultdict
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

from app.agents.base_agent import BaseAgent
from app.models.customer import ActivityStatus, Customer, Gender

logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────

_AGE_BRACKETS: list[tuple[int, int, str]] = [
    (18, 24, "gen_z"),
    (25, 34, "millennials"),
    (35, 44, "gen_x_young"),
    (45, 54, "gen_x_senior"),
    (55, 120, "seniors"),
]

_MIN_SEGMENT_PCT = 0.05   # segments must cover ≥ 5 % of the population
_MAX_SEGMENTS = 7
_MIN_SEGMENTS = 3

_ALLOWED_GOALS = {"awareness", "conversion", "retention", "engagement"}

# Goal → activity statuses that should be prioritised
_GOAL_ACTIVITY_PRIORITY: dict[str, list[str]] = {
    "awareness":   ["inactive", "dormant", "active"],
    "conversion":  ["active", "inactive", "dormant"],
    "retention":   ["active", "inactive", "dormant"],
    "engagement":  ["active", "inactive", "dormant"],
}


# ── Schemas ───────────────────────────────────────────────────────────────────

class SegmentationInput(BaseModel):
    """Input schema for the segmentation agent."""

    customers: list[Customer]
    target_audience: str = Field(..., min_length=1)
    campaign_goal: str

    @field_validator("campaign_goal")
    @classmethod
    def validate_goal(cls, v: str) -> str:
        normalised = v.lower().strip()
        if normalised not in _ALLOWED_GOALS:
            raise ValueError(
                f"campaign_goal must be one of {sorted(_ALLOWED_GOALS)}, got '{v}'"
            )
        return normalised

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
    coverage_pct: float = Field(..., description="% of customers assigned to ≥1 segment")
    distribution: dict[str, int] = Field(
        default_factory=dict,
        description="segment_name → customer count",
    )

    @model_validator(mode="after")
    def sort_and_distribute(self) -> "SegmentationResult":
        self.segments = sorted(self.segments, key=lambda s: s.targeting_priority, reverse=True)
        self.distribution = {s.segment_name: s.size for s in self.segments}
        return self


# ── Prompt ────────────────────────────────────────────────────────────────────

_SEGMENTATION_TEMPLATE = """\
You are an expert marketing analyst. You will receive a demographic summary of customers \
along with context about the campaign target audience and goal. Your task is to propose \
{min_seg}–{max_seg} meaningful customer segments.

## Campaign context
- Target audience : {target_audience}
- Campaign goal   : {campaign_goal}

## Customer population summary
Total customers  : {total_customers}

Age distribution :
{age_distribution}

Gender distribution :
{gender_distribution}

Location top-5 :
{location_distribution}

Activity status :
{activity_distribution}

## Pre-computed candidate segment groups (name → customer-id list)
{candidate_groups}

## Instructions
1. Select {min_seg}–{max_seg} of the candidate groups that are most relevant to the \
target audience and campaign goal. Merge very similar groups if needed.
2. Each segment must contain at least {min_pct_int}% of total customers — skip any that do not.
3. Assign a targeting_priority (1–5, where 5 is highest) based on fit with the campaign goal.
4. Write a clear description explaining why this segment is valuable for the campaign.
5. Write a recommended_approach (1–2 sentences of tactical guidance for this segment).
6. Ensure all {total_customers} customers appear in at least one segment (segments may overlap).
7. Respond with ONLY a valid JSON array of segment objects — no markdown, no extra text.

## Required JSON schema for each segment object
{{
  "segment_name"          : "<snake_case descriptive name>",
  "description"           : "<why this segment matters for the campaign>",
  "customer_ids"          : ["<id>", ...],
  "targeting_priority"    : <1-5>,
  "recommended_approach"  : "<short tactical guidance>"
}}
"""


# ── Agent ─────────────────────────────────────────────────────────────────────

class CustomerSegmentationAgent(BaseAgent):
    """Segments a customer list into prioritised groups using demographic rules + GPT-4."""

    def __init__(self, **kwargs: Any) -> None:
        kwargs.setdefault("temperature", 0.2)
        kwargs.setdefault("max_tokens", 2048)
        super().__init__(**kwargs)

    # ── Public interface ──────────────────────────────────────────────────────

    async def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Segment customers and return a ``SegmentationResult`` dict.

        Args:
            input_data: Must match ``SegmentationInput`` schema.

        Returns:
            Dict representation of ``SegmentationResult``.
        """
        seg_input: SegmentationInput = self._validate_input(input_data, SegmentationInput)
        customers = seg_input.customers
        total = len(customers)

        self._log_action("execute_start", {
            "total_customers": total,
            "campaign_goal": seg_input.campaign_goal,
        })

        # 1. Build candidate groups from pure Python logic
        candidate_groups = self._build_candidate_groups(customers, seg_input.campaign_goal)

        # 2. Build population summaries for the prompt
        summaries = self._build_summaries(customers)

        # 3. Format candidate groups for the prompt
        candidate_text = self._format_candidates(candidate_groups, total)

        # 4. Ask LLM to select / refine / prioritise
        prompt = self._build_prompt(seg_input, total, summaries, candidate_text)
        raw = await self._retry_with_backoff(self._call_llm, prompt)
        segments_raw = self._parse_llm_output(raw)

        # _parse_llm_output returns dict; LLM should return an array so handle both
        if isinstance(segments_raw, dict):
            # Unwrap common wrapper keys
            segments_list = (
                segments_raw.get("segments")
                or segments_raw.get("data")
                or list(segments_raw.values())[0]
                if segments_raw else []
            )
        else:
            # raw JSON was already a list — re-parse as list
            import json
            try:
                segments_list = json.loads(raw) if isinstance(raw, str) else segments_raw
            except Exception:
                segments_list = []

        if not isinstance(segments_list, list):
            segments_list = []

        # 5. Ensure full population coverage (fallback "all_customers" segment)
        segments_list = self._ensure_coverage(segments_list, customers, total)

        # 6. Validate each segment through Pydantic
        validated_segments: list[SegmentOut] = []
        for seg_dict in segments_list:
            try:
                validated_segments.append(SegmentOut(**seg_dict))
            except Exception as exc:
                self._log_action("segment_validation_warning", {"error": str(exc), "segment": seg_dict})

        # 7. Compute coverage
        assigned_ids: set[str] = set()
        for seg in validated_segments:
            assigned_ids.update(seg.customer_ids)
        coverage_pct = round(len(assigned_ids) / total * 100, 1) if total else 0.0

        result = SegmentationResult(
            segments=validated_segments,
            total_customers=total,
            coverage_pct=coverage_pct,
        )

        self._log_action("execute_complete", {
            "segments_created": len(result.segments),
            "coverage_pct": result.coverage_pct,
            "distribution": result.distribution,
        })

        return result.model_dump()

    # ── Internal: candidate builder ───────────────────────────────────────────

    def _build_candidate_groups(
        self, customers: list[Customer], goal: str
    ) -> dict[str, list[str]]:
        """Build rule-based candidate segment groups from customer demographics."""
        groups: dict[str, list[str]] = defaultdict(list)
        priority_statuses = _GOAL_ACTIVITY_PRIORITY.get(goal, ["active"])

        for c in customers:
            cid = c.customer_id
            bracket_label = self._age_bracket(c.age)

            # Age-bracket segments
            groups[bracket_label].append(cid)

            # Activity-status segments
            groups[f"status_{c.activity_status.value}"].append(cid)

            # Top-priority status for this goal
            if c.activity_status.value == priority_statuses[0]:
                groups[f"high_priority_{priority_statuses[0]}"].append(cid)

            # Gender-based segments (only when relevant)
            if c.gender in (Gender.MALE, Gender.FEMALE):
                groups[f"gender_{c.gender.value}"].append(cid)

            # Combined age + activity (multi-dimensional)
            groups[f"{bracket_label}_{c.activity_status.value}"].append(cid)

        return dict(groups)

    @staticmethod
    def _age_bracket(age: int) -> str:
        for low, high, label in _AGE_BRACKETS:
            if low <= age <= high:
                return label
        return "other_age"

    # ── Internal: summary builders ────────────────────────────────────────────

    def _build_summaries(self, customers: list[Customer]) -> dict[str, str]:
        total = len(customers)

        age_counts: dict[str, int] = defaultdict(int)
        gender_counts: dict[str, int] = defaultdict(int)
        location_counts: dict[str, int] = defaultdict(int)
        activity_counts: dict[str, int] = defaultdict(int)

        for c in customers:
            age_counts[self._age_bracket(c.age)] += 1
            gender_counts[c.gender.value] += 1
            location_counts[c.location] += 1
            activity_counts[c.activity_status.value] += 1

        def _fmt(counts: dict[str, int]) -> str:
            return "\n".join(
                f"  {k}: {v} ({v / total * 100:.1f}%)"
                for k, v in sorted(counts.items(), key=lambda x: -x[1])
            )

        top5_locations = dict(
            sorted(location_counts.items(), key=lambda x: -x[1])[:5]
        )

        return {
            "age": _fmt(age_counts),
            "gender": _fmt(gender_counts),
            "location": _fmt(top5_locations),
            "activity": _fmt(activity_counts),
        }

    @staticmethod
    def _format_candidates(
        groups: dict[str, list[str]], total: int
    ) -> str:
        """Serialise candidate groups for the prompt, filtering micro-segments."""
        lines: list[str] = []
        for name, ids in sorted(groups.items(), key=lambda x: -len(x[1])):
            pct = len(ids) / total * 100 if total else 0
            if pct < _MIN_SEGMENT_PCT * 100:
                continue
            preview = ids[:3]
            ellipsis = f" … +{len(ids) - 3} more" if len(ids) > 3 else ""
            lines.append(f"  {name} ({len(ids)} customers, {pct:.1f}%): {preview}{ellipsis}")
        return "\n".join(lines) if lines else "  (no candidate groups met minimum size)"

    # ── Internal: prompt builder ──────────────────────────────────────────────

    def _build_prompt(
        self,
        seg_input: SegmentationInput,
        total: int,
        summaries: dict[str, str],
        candidate_text: str,
    ) -> str:
        return _SEGMENTATION_TEMPLATE.format(
            min_seg=_MIN_SEGMENTS,
            max_seg=_MAX_SEGMENTS,
            target_audience=seg_input.target_audience,
            campaign_goal=seg_input.campaign_goal,
            total_customers=total,
            age_distribution=summaries["age"],
            gender_distribution=summaries["gender"],
            location_distribution=summaries["location"],
            activity_distribution=summaries["activity"],
            candidate_groups=candidate_text,
            min_pct_int=int(_MIN_SEGMENT_PCT * 100),
        )

    async def _call_llm(self, prompt: str) -> str:
        response = await self.llm.ainvoke(prompt)
        return response.content if hasattr(response, "content") else str(response)

    # ── Internal: coverage guarantor ─────────────────────────────────────────

    def _ensure_coverage(
        self,
        segments_list: list[dict],
        customers: list[Customer],
        total: int,
    ) -> list[dict]:
        """Add a fallback 'all_customers' segment for any unassigned customers."""
        assigned: set[str] = set()
        for seg in segments_list:
            assigned.update(seg.get("customer_ids", []))

        unassigned = [c.customer_id for c in customers if c.customer_id not in assigned]
        if not unassigned:
            return segments_list

        pct = len(unassigned) / total * 100 if total else 0
        self._log_action("coverage_gap", {
            "unassigned_count": len(unassigned),
            "pct": round(pct, 1),
        })

        # Find the lowest-priority existing segment and expand it, or create a catch-all
        if segments_list:
            # Append unassigned IDs to the lowest-priority segment
            lowest = min(segments_list, key=lambda s: s.get("targeting_priority", 1))
            lowest["customer_ids"] = list(set(lowest.get("customer_ids", [])) | set(unassigned))
        else:
            segments_list.append({
                "segment_name": "all_customers",
                "description": "All customers — no more specific segmentation was possible.",
                "customer_ids": [c.customer_id for c in customers],
                "targeting_priority": 1,
                "recommended_approach": "Use a broad, general messaging approach.",
            })

        return segments_list
