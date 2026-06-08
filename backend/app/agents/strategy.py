"""Campaign Strategy Agent — generates targeting strategy, send schedule, and A/B test plan."""

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from app.agents.base_agent import BaseAgent
from app.agents.brief_parser import ParsedBrief
from app.agents.segmentation import SegmentOut

logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────

_ALLOWED_GOALS = {"awareness", "conversion", "retention", "engagement"}

# Keyword → goal enum mapping (checked in order; first match wins)
_GOAL_KEYWORDS: list[tuple[list[str], str]] = [
    (["conver", "sign-up", "signup", "sale", "purchase", "apply", "click", "cta", "lead"], "conversion"),
    (["retain", "loyal", "churn", "re-engag", "re-activ", "laps"], "retention"),
    (["engag", "interact", "open rate", "response", "participat"], "engagement"),
    (["aware", "brand", "reach", "visib", "impres", "introduc"], "awareness"),
]


def _normalise_goal(raw: str) -> str:
    """Map any goal string to one of the four allowed enum values."""
    if not raw:
        return "awareness"
    lower = raw.lower().strip()
    if lower in _ALLOWED_GOALS:
        return lower
    for keywords, goal in _GOAL_KEYWORDS:
        if any(kw in lower for kw in keywords):
            return goal
    return "awareness"
_MAX_SELECTED_SEGMENTS = 5
_MIN_SELECTED_SEGMENTS = 2

# Best-practice send-hour windows (24-h UTC) per goal and day type
_SEND_HOURS: dict[str, dict[str, list[int]]] = {
    "awareness":   {"weekday": [9, 12, 17], "weekend": [10, 14]},
    "conversion":  {"weekday": [10, 14, 19], "weekend": [11, 15]},
    "retention":   {"weekday": [8, 13, 18], "weekend": [10, 16]},
    "engagement":  {"weekday": [11, 15, 20], "weekend": [12, 17]},
}

# Stagger offset in hours between segments for awareness campaigns
_AWARENESS_STAGGER_H = 2

# Base open-rate lookups (empirical marketing benchmarks)
_BASE_OPEN_RATE: dict[str, float] = {
    "active":   0.28,
    "inactive": 0.14,
    "dormant":  0.08,
}
_GOAL_OPEN_RATE_BOOST: dict[str, float] = {
    "awareness":   0.02,
    "conversion":  0.04,
    "retention":   0.06,
    "engagement":  0.03,
}


# ── Schemas ───────────────────────────────────────────────────────────────────

class StrategyInput(BaseModel):
    """Input schema for the strategy agent."""

    parsed_brief: ParsedBrief
    segments: list[SegmentOut]
    current_time: datetime

    @model_validator(mode="before")
    @classmethod
    def normalise_parsed_brief(cls, values: dict) -> dict:
        """Flatten the 4-section parsed_data format into a ParsedBrief-compatible dict."""
        brief = values.get("parsed_brief")
        if not isinstance(brief, dict) or "product_details" not in brief:
            return values
        details = brief.get("product_details", {})
        prefs = brief.get("campaign_preferences", {})
        goal_raw = brief.get("campaign_goal", "")
        if isinstance(goal_raw, str):
            goal_str = goal_raw
        elif isinstance(goal_raw, dict):
            goal_str = goal_raw.get("objective", "")
        else:
            goal_str = ""
        hints = prefs.get("content_hints", "") or ""
        key_messages = [p.strip() for p in hints.split(",") if p.strip()]
        values["parsed_brief"] = {
            "product_name": details.get("product_name") or "Unknown",
            "product_description": details.get("product_description", ""),
            "cta_link": details.get("cta_link", ""),
            "campaign_goal": _normalise_goal(goal_str),
            "campaign_objective": goal_str,
            "campaign_name": prefs.get("campaign_name", ""),
            "preferred_tone": (prefs.get("email_tone") or "professional").lower(),
            "key_messages": key_messages[:5],
            "budget": brief.get("budget"),
            "target_audience": brief.get("target_audience", {}),
        }
        return values

    @field_validator("segments")
    @classmethod
    def require_segments(cls, v: list[SegmentOut]) -> list[SegmentOut]:
        if not v:
            raise ValueError("segments list must not be empty")
        return v

    @field_validator("current_time", mode="before")
    @classmethod
    def ensure_tz(cls, v: Any) -> datetime:
        if isinstance(v, str):
            v = datetime.fromisoformat(v)
        if isinstance(v, datetime) and v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v


class ABTestPlan(BaseModel):
    """A/B test configuration for a campaign."""

    num_variants: int = Field(..., ge=2, le=4)
    variant_distribution: dict[str, float]   # variant_id → percentage (must sum to 100)
    test_dimension: str

    @model_validator(mode="after")
    def validate_distribution(self) -> "ABTestPlan":
        total = sum(self.variant_distribution.values())
        if abs(total - 100.0) > 0.5:
            raise ValueError(
                f"variant_distribution must sum to 100, got {total:.2f}"
            )
        if len(self.variant_distribution) != self.num_variants:
            raise ValueError(
                f"num_variants={self.num_variants} but distribution has "
                f"{len(self.variant_distribution)} entries"
            )
        return self


class CampaignStrategy(BaseModel):
    """Full strategic output produced by the strategy agent."""

    selected_segments: list[str]
    send_schedule: dict[str, datetime]        # segment_name → send_time
    ab_test_plan: ABTestPlan
    budget_allocation: dict[str, float]       # segment_name → budget %
    expected_metrics: dict[str, float]        # segment_name → expected_open_rate
    reasoning: dict[str, str] = Field(default_factory=dict)   # segment_name → rationale

    @model_validator(mode="after")
    def validate_budget(self) -> "CampaignStrategy":
        total = sum(self.budget_allocation.values())
        if self.budget_allocation and abs(total - 100.0) > 0.5:
            raise ValueError(
                f"budget_allocation must sum to 100, got {total:.2f}"
            )
        return self


# ── Prompt ────────────────────────────────────────────────────────────────────

_STRATEGY_TEMPLATE = """\
You are a senior digital marketing strategist. Given the campaign brief, available segments, \
and the pre-computed scheduling/budget hints below, produce a complete campaign strategy.

## Campaign brief summary
- Product        : {product_name}
- Goal           : {campaign_goal}
- Budget (USD)   : {budget}
- Tone           : {preferred_tone}
- Key messages   : {key_messages}

## Available segments (sorted by priority desc)
{segments_summary}

## Pre-computed hints (use these as starting points, refine as needed)
Selected segments  : {selected_segments}
Send schedule      : {send_schedule_hint}
Budget allocation  : {budget_hint}
Expected open rates: {open_rate_hint}

## A/B test guidance
Campaign goal is "{campaign_goal}". Suggest the best test dimension \
(subject_line | content | send_time | cta | tone) and propose {num_variants} variants.

## Instructions
Return ONLY a valid JSON object with EXACTLY these keys:

{{
  "selected_segments"  : ["<segment_name>", ...],
  "send_schedule"      : {{"<segment_name>": "<ISO-8601 datetime>", ...}},
  "ab_test_plan"       : {{
      "num_variants"          : <2-4>,
      "variant_distribution"  : {{"variant_A": <pct>, "variant_B": <pct>, ...}},
      "test_dimension"        : "<dimension>"
  }},
  "budget_allocation"  : {{"<segment_name>": <pct>, ...}},
  "expected_metrics"   : {{"<segment_name>": <open_rate_0_to_1>, ...}},
  "reasoning"          : {{"<segment_name>": "<1–2 sentence rationale>", ...}}
}}

Rules:
- selected_segments must have {min_seg}–{max_seg} entries.
- send_schedule keys must exactly match selected_segments.
- variant_distribution values must sum to exactly 100.
- budget_allocation values must sum to exactly 100.
- expected_metrics values are floats in range [0, 1].
- Use ISO-8601 with timezone offset for datetimes (e.g. "2026-04-10T10:00:00+00:00").
- For awareness goal: stagger sends 2 h apart, favour broad reach.
- For conversion goal: concentrate budget on high-priority segments.
- For retention goal: personalise timing, use friendly/empathetic tone guidance.
- No markdown, no extra text — only the JSON object.
"""


# ── Agent ─────────────────────────────────────────────────────────────────────

class CampaignStrategyAgent(BaseAgent):
    """Produces campaign strategy, scheduling, A/B plan, and budget allocation via GPT-4."""

    def __init__(self, **kwargs: Any) -> None:
        kwargs.setdefault("temperature", 0.3)
        kwargs.setdefault("max_tokens", 2048)
        super().__init__(**kwargs)

    # ── Public interface ──────────────────────────────────────────────────────

    async def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Generate campaign strategy and return a ``CampaignStrategy`` dict.

        Args:
            input_data: Must match ``StrategyInput`` schema.

        Returns:
            Dict representation of ``CampaignStrategy``.
        """
        strategy_input: StrategyInput = self._validate_input(input_data, StrategyInput)
        brief = strategy_input.parsed_brief
        segments = strategy_input.segments
        now = strategy_input.current_time

        self._log_action("execute_start", {
            "campaign_goal": brief.campaign_goal,
            "num_segments": len(segments),
            "budget": brief.budget,
        })

        # 1. Pre-compute heuristic values used as prompt hints
        selected = self._select_segments(segments, brief.campaign_goal)
        send_schedule = self._compute_send_schedule(selected, now, brief.campaign_goal)
        budget_alloc = self._compute_budget_allocation(selected, brief.campaign_goal)
        open_rates = self._estimate_open_rates(selected, brief.campaign_goal)
        num_variants = self._decide_num_variants(brief.budget)

        # 2. Build and invoke the LLM prompt
        prompt = self._build_prompt(
            brief=brief,
            segments=segments,
            selected=selected,
            send_schedule=send_schedule,
            budget_alloc=budget_alloc,
            open_rates=open_rates,
            num_variants=num_variants,
        )
        raw = await self._retry_with_backoff(self._call_llm, prompt)
        result_dict = self._parse_llm_output(raw)

        # 3. Post-process and validate
        result_dict = self._post_process(result_dict, selected, send_schedule, budget_alloc, open_rates)
        strategy: CampaignStrategy = self._validate_input(result_dict, CampaignStrategy)

        self._log_action("execute_complete", {
            "selected_segments": strategy.selected_segments,
            "test_dimension": strategy.ab_test_plan.test_dimension,
            "num_variants": strategy.ab_test_plan.num_variants,
            "budget_allocation": strategy.budget_allocation,
        })

        return strategy.model_dump()

    # ── Heuristics ────────────────────────────────────────────────────────────

    def _select_segments(self, segments: list[SegmentOut], goal: str) -> list[SegmentOut]:
        """Pick the top 2–5 segments by targeting_priority; for conversion bias toward high priority."""
        sorted_segs = sorted(segments, key=lambda s: (s.targeting_priority, s.size), reverse=True)

        if goal == "conversion":
            # Prefer only highest-priority segments
            candidates = [s for s in sorted_segs if s.targeting_priority >= 4] or sorted_segs
        else:
            candidates = sorted_segs

        return candidates[:_MAX_SELECTED_SEGMENTS]

    def _compute_send_schedule(
        self,
        selected: list[SegmentOut],
        now: datetime,
        goal: str,
    ) -> dict[str, datetime]:
        """Assign optimal send datetimes, staggering for awareness campaigns."""
        hours = _SEND_HOURS.get(goal, _SEND_HOURS["engagement"])
        is_weekday = now.weekday() < 5
        hour_pool = hours["weekday"] if is_weekday else hours["weekend"]

        # Start from the next calendar day at the first best-practice hour
        base_date = (now + timedelta(days=1)).replace(
            hour=hour_pool[0], minute=0, second=0, microsecond=0
        )

        schedule: dict[str, datetime] = {}
        for idx, seg in enumerate(selected):
            if goal == "awareness":
                send_dt = base_date + timedelta(hours=idx * _AWARENESS_STAGGER_H)
            else:
                # Rotate through the hour pool; advance day if we wrap around
                hour = hour_pool[idx % len(hour_pool)]
                extra_days = idx // len(hour_pool)
                send_dt = base_date.replace(hour=hour) + timedelta(days=extra_days)
            schedule[seg.segment_name] = send_dt
        return schedule

    def _compute_budget_allocation(
        self, selected: list[SegmentOut], goal: str
    ) -> dict[str, float]:
        """Allocate budget proportionally (priority × size), with conversion-goal concentration."""
        if not selected:
            return {}

        if goal == "conversion":
            # Square the priority to concentrate spend on high-value segments
            weights = {s.segment_name: (s.targeting_priority ** 2) * max(s.size, 1)
                       for s in selected}
        else:
            weights = {s.segment_name: s.targeting_priority * max(s.size, 1)
                       for s in selected}

        total_w = sum(weights.values())
        return {
            name: round(w / total_w * 100, 2)
            for name, w in weights.items()
        }

    def _estimate_open_rates(
        self, selected: list[SegmentOut], goal: str
    ) -> dict[str, float]:
        """Estimate open rates using segment name heuristics + goal boost."""
        boost = _GOAL_OPEN_RATE_BOOST.get(goal, 0.02)
        rates: dict[str, float] = {}
        for seg in selected:
            name_lower = seg.segment_name.lower()
            if "active" in name_lower:
                base = _BASE_OPEN_RATE["active"]
            elif "dormant" in name_lower:
                base = _BASE_OPEN_RATE["dormant"]
            elif "inactive" in name_lower:
                base = _BASE_OPEN_RATE["inactive"]
            else:
                # Blend by priority
                base = 0.10 + (seg.targeting_priority - 1) * 0.04
            rates[seg.segment_name] = round(min(base + boost, 0.99), 4)
        return rates

    @staticmethod
    def _decide_num_variants(budget: Optional[float]) -> int:
        """Lower budgets use fewer variants to maintain statistical significance."""
        if budget is None or budget <= 0:
            return 2
        if budget < 2000:
            return 2
        if budget < 10000:
            return 3
        return 4

    # ── Prompt builder ────────────────────────────────────────────────────────

    def _build_prompt(
        self,
        brief: ParsedBrief,
        segments: list[SegmentOut],
        selected: list[SegmentOut],
        send_schedule: dict[str, datetime],
        budget_alloc: dict[str, float],
        open_rates: dict[str, float],
        num_variants: int,
    ) -> str:
        segments_summary = "\n".join(
            f"  [{s.targeting_priority}/5] {s.segment_name} — {s.size} customers — {s.description}"
            for s in segments
        )
        selected_names = [s.segment_name for s in selected]
        schedule_hint = {k: v.isoformat() for k, v in send_schedule.items()}
        return _STRATEGY_TEMPLATE.format(
            product_name=brief.product_name,
            campaign_goal=brief.campaign_goal,
            budget=brief.budget if brief.budget else "Not specified",
            preferred_tone=brief.preferred_tone,
            key_messages="; ".join(brief.key_messages) if brief.key_messages else "Not specified",
            segments_summary=segments_summary,
            selected_segments=selected_names,
            send_schedule_hint=json.dumps(schedule_hint, indent=2),
            budget_hint=json.dumps(budget_alloc, indent=2),
            open_rate_hint=json.dumps(open_rates, indent=2),
            num_variants=num_variants,
            min_seg=_MIN_SELECTED_SEGMENTS,
            max_seg=_MAX_SELECTED_SEGMENTS,
        )

    async def _call_llm(self, prompt: str) -> str:
        response = await self.llm.ainvoke(prompt)
        return response.content if hasattr(response, "content") else str(response)

    # ── Post-processing ───────────────────────────────────────────────────────

    def _post_process(
        self,
        data: dict[str, Any],
        selected: list[SegmentOut],
        fallback_schedule: dict[str, datetime],
        fallback_budget: dict[str, float],
        fallback_rates: dict[str, float],
    ) -> dict[str, Any]:
        """Normalise LLM output and fill missing keys with pre-computed fallbacks."""
        selected_names = [s.segment_name for s in selected]

        # selected_segments
        if not data.get("selected_segments"):
            data["selected_segments"] = selected_names

        # send_schedule — parse ISO strings back to datetime
        raw_schedule = data.get("send_schedule", {})
        parsed_schedule: dict[str, datetime] = {}
        for seg_name in data["selected_segments"]:
            raw_dt = raw_schedule.get(seg_name)
            if raw_dt:
                try:
                    parsed_schedule[seg_name] = datetime.fromisoformat(str(raw_dt))
                except ValueError:
                    parsed_schedule[seg_name] = fallback_schedule.get(
                        seg_name, list(fallback_schedule.values())[0]
                    )
            else:
                parsed_schedule[seg_name] = fallback_schedule.get(
                    seg_name, list(fallback_schedule.values())[0] if fallback_schedule else datetime.now(tz=timezone.utc)
                )
        data["send_schedule"] = parsed_schedule

        # budget_allocation — normalise so it sums to 100
        budget = data.get("budget_allocation", {})
        if not budget:
            data["budget_allocation"] = fallback_budget
        else:
            total = sum(float(v) for v in budget.values())
            if total > 0 and abs(total - 100.0) > 0.5:
                data["budget_allocation"] = {
                    k: round(float(v) / total * 100, 2) for k, v in budget.items()
                }

        # expected_metrics
        if not data.get("expected_metrics"):
            data["expected_metrics"] = fallback_rates

        # ab_test_plan — ensure distribution sums to 100
        ab = data.get("ab_test_plan", {})
        if not ab:
            n = 2
            data["ab_test_plan"] = {
                "num_variants": n,
                "variant_distribution": {f"variant_{chr(65+i)}": 100.0 / n for i in range(n)},
                "test_dimension": "subject_line",
            }
        else:
            dist = ab.get("variant_distribution", {})
            if dist:
                total_d = sum(float(v) for v in dist.values())
                if total_d > 0 and abs(total_d - 100.0) > 0.5:
                    ab["variant_distribution"] = {
                        k: round(float(v) / total_d * 100, 2) for k, v in dist.items()
                    }
            data["ab_test_plan"] = ab

        data.setdefault("reasoning", {})
        return data
