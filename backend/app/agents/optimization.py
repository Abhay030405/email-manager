"""Optimization Agent — analyzes campaign performance and generates improvement recommendations."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Optional

from app.agents.base_agent import BaseAgent
from app.utils.optimization_utils import (
    generate_optimization_insights,
    identify_optimization_factors,
)

logger = logging.getLogger(__name__)

SCORE_THRESHOLD = 12.0  # legacy constant for LLM prompt context


class OptimizationAgent(BaseAgent):
    """Analyses Mock API metrics and generates data-driven optimisation recommendations.

    Covers:
    - Subject line (40-60 chars, urgency, personalisation)
    - Email body (100-200 words HTML, CTAs, benefit statements)
    - Send timing (Tue/Wed 8-10 AM)
    - Demographic re-targeting based on per-customer results
    """

    def __init__(self) -> None:
        super().__init__(model_name="gpt-4", temperature=0.3, max_tokens=2000)

    # ── BaseAgent protocol ────────────────────────────────────────────────────

    async def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        campaign_id = input_data.get("campaign_id", "")
        metrics = input_data.get("metrics", {})
        return await self.optimize_campaign(campaign_id, metrics)

    # ── Core API ──────────────────────────────────────────────────────────────

    async def analyze_optimization_opportunity(
        self,
        campaign_id: str,
        metrics_list: list[dict[str, Any]],
        customer_results: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Analyse a campaign and return an opportunity assessment."""
        customer_results = customer_results or []
        if not metrics_list:
            return {
                "overall_performance": 0.0,
                "poor_performers": [],
                "segment_analysis": {},
                "optimization_factors": [],
                "improvement_potential": 0.0,
            }

        scores = [
            0.7 * float(m.get("click_rate", 0.0)) + 0.3 * float(m.get("open_rate", 0.0))
            for m in metrics_list
        ]
        avg_score = sum(scores) / len(scores)

        poor = [
            m for m, s in zip(metrics_list, scores)
            if s < avg_score * 0.75
        ]

        all_factors: list[str] = []
        for m in poor:
            all_factors.extend(identify_optimization_factors(m, customer_results))
        unique_factors = list(dict.fromkeys(all_factors))

        # Improvement potential: proportion of variants that are poor performers
        improvement_potential = len(poor) / len(metrics_list) if metrics_list else 0.0

        return {
            "overall_performance": round(avg_score, 4),
            "poor_performers": poor,
            "segment_analysis": _group_by_segment(metrics_list),
            "optimization_factors": unique_factors,
            "improvement_potential": round(improvement_potential, 4),
        }

    async def generate_optimization_insights(
        self,
        campaign_id: str,
        poor_performers: list[dict[str, Any]],
        segment_performance: dict[str, Any],
        customer_results: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Generate actionable insights for the poor-performing variants."""
        return generate_optimization_insights(
            poor_performers, segment_performance, customer_results
        )

    async def recommend_content_improvements(
        self,
        variant: dict[str, Any],
        insights: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Produce improvement recommendations for a single variant."""
        relevant = [i for i in insights if i.get("variant_id") in (variant.get("variant_id"), None)]

        subject_improvements: list[str] = []
        body_improvements: list[str] = []
        timing_improvements: dict[str, Any] = {}
        targeting_improvements: list[str] = []

        for ins in relevant:
            t = ins.get("type", "")
            rec = ins.get("recommendation", "")
            if t == "content":
                issue = ins.get("issue", "").lower()
                if "subject" in issue:
                    subject_improvements.append(rec)
                else:
                    body_improvements.append(rec)
            elif t == "timing":
                timing_improvements["recommendation"] = rec
                timing_improvements["optimal_window"] = "Tue/Wed 8-10 AM"
            elif t == "targeting":
                targeting_improvements.append(rec)

        if not subject_improvements:
            subject_improvements = [
                "Shorten subject to 40-60 characters",
                "Add urgency or personalisation token",
            ]
        if not body_improvements:
            body_improvements = [
                "Add a prominent CTA above the fold",
                "Trim or expand body to 100-200 words",
            ]

        return {
            "subject_improvements": subject_improvements,
            "body_improvements": body_improvements,
            "timing_improvements": timing_improvements,
            "targeting_improvements": targeting_improvements,
        }

    async def check_convergence(
        self,
        iteration_results: list[Any],
        convergence_threshold: float = 0.05,
    ) -> bool:
        """Return True if the last two iterations improved by less than the threshold."""
        if len(iteration_results) < 2:
            return False
        prev = getattr(iteration_results[-2], "new_performance_score", 0.0)
        curr = getattr(iteration_results[-1], "new_performance_score", 0.0)
        if prev == 0:
            return False
        improvement = (curr - prev) / prev
        return improvement < convergence_threshold

    # ── Legacy method (kept for backward compatibility) ───────────────────────

    async def optimize_campaign(
        self, campaign_id: str, metrics: dict[str, Any]
    ) -> dict[str, Any]:
        """Original entry point — analyses metrics and returns recommendations."""
        self._log_action("optimize_campaign", {"campaign_id": campaign_id})

        variant_metrics: list[dict[str, Any]] = metrics.get("variant_metrics", [])
        customer_results: list[dict[str, Any]] = metrics.get("customer_results", [])

        if not variant_metrics:
            return {"optimization_recommendations": []}

        scored = [
            (
                m.get("variant_id", ""),
                0.7 * float(m.get("click_rate", 0.0)) + 0.3 * float(m.get("open_rate", 0.0)),
                m,
            )
            for m in variant_metrics
        ]
        poor_variants = [(vid, score, m) for vid, score, m in scored if score < SCORE_THRESHOLD]

        if not poor_variants:
            return {"optimization_recommendations": []}

        demographic_insights = _analyze_customer_results(customer_results)
        prompt = _build_optimization_prompt(
            poor_variants, demographic_insights, metrics.get("aggregates", {})
        )

        try:
            raw = await self._retry_with_backoff(self._call_llm, prompt)
            parsed = self._parse_llm_output(raw)
            recommendations = parsed if isinstance(parsed, list) else parsed.get("recommendations", [])
        except Exception as exc:
            logger.warning("LLM optimization call failed, using rule-based fallback: %s", exc)
            recommendations = _rule_based_recommendations(poor_variants, demographic_insights)

        return {"optimization_recommendations": recommendations}

    async def run_optimization_loop(
        self,
        campaign_id: str,
        metrics_list: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Thin wrapper for LangGraph integration."""
        opportunity = await self.analyze_optimization_opportunity(
            campaign_id, metrics_list or []
        )
        insights = await self.generate_optimization_insights(
            campaign_id,
            opportunity["poor_performers"],
            opportunity["segment_analysis"],
            [],
        )
        return {
            "campaign_id": campaign_id,
            "opportunity": opportunity,
            "insights": insights,
            "status": "analysed",
        }

    async def _call_llm(self, prompt: str) -> str:
        from langchain.schema import HumanMessage
        response = await self.llm.agenerate([[HumanMessage(content=prompt)]])
        return response.generations[0][0].text


# ── Private helpers ────────────────────────────────────────────────────────────

def _group_by_segment(metrics_list: list[dict[str, Any]]) -> dict[str, Any]:
    segments: dict[str, list[float]] = {}
    for m in metrics_list:
        seg = m.get("segment_name", "unknown")
        score = 0.7 * float(m.get("click_rate", 0.0)) + 0.3 * float(m.get("open_rate", 0.0))
        segments.setdefault(seg, []).append(score)
    result = {
        seg: {"avg_score": round(sum(s) / len(s), 4), "count": len(s)}
        for seg, s in segments.items()
    }
    return result


def _analyze_customer_results(results: list[dict[str, Any]]) -> dict[str, Any]:
    if not results:
        return {}
    non_openers = [r for r in results if not r.get("opened")]
    low_clickers = [r for r in results if r.get("opened") and not r.get("clicked")]
    avg_open_prob = sum(r.get("open_probability", 0.0) for r in results) / len(results)
    return {
        "total_results": len(results),
        "non_opener_count": len(non_openers),
        "low_clicker_count": len(low_clickers),
        "avg_open_probability": round(avg_open_prob, 3),
    }


def _build_optimization_prompt(
    poor_variants: list[tuple[str, float, dict[str, Any]]],
    demographic_insights: dict[str, Any],
    aggregates: dict[str, Any],
) -> str:
    lines = [
        "You are a marketing optimisation expert. Based on the following email campaign "
        "performance data, generate specific optimisation recommendations.",
        "",
        "POOR PERFORMING VARIANTS (score = 0.7*click_rate + 0.3*open_rate, threshold=12.0):",
    ]
    for vid, score, m in poor_variants:
        lines.append(
            f"  - variant_id={vid}: score={score:.2f}, "
            f"open_rate={m.get('open_rate', 0):.1f}%, "
            f"click_rate={m.get('click_rate', 0):.1f}%"
        )
    if aggregates:
        lines.extend([
            "",
            f"CAMPAIGN AVERAGES: open_rate={aggregates.get('avg_open_rate', 0):.1f}%, "
            f"click_rate={aggregates.get('avg_click_rate', 0):.1f}%",
        ])
    if demographic_insights:
        lines.extend([
            "",
            f"CUSTOMER BEHAVIOUR: {demographic_insights.get('non_opener_count', 0)} non-openers, "
            f"avg open probability={demographic_insights.get('avg_open_probability', 0):.2f}",
        ])
    lines.extend([
        "",
        "Provide recommendations as a JSON array. Each element should have:",
        '{"variant_id": "...", "changes": ["improvement 1", ...], "priority": "high|medium|low"}',
        "",
        "Focus on: subject line (40-60 chars, urgency/personalisation/emoji), "
        "body (100-200 words HTML, clear CTAs), timing (Tue/Wed 8-10 AM).",
        "Return ONLY the JSON array.",
    ])
    return "\n".join(lines)


def _rule_based_recommendations(
    poor_variants: list[tuple[str, float, dict[str, Any]]],
    demographic_insights: dict[str, Any],
) -> list[dict[str, Any]]:
    recommendations = []
    for vid, score, m in poor_variants:
        changes = []
        if float(m.get("open_rate", 0)) < 20:
            changes.extend([
                "Shorten subject line to 40-60 characters",
                "Add urgency words: 'Limited', 'Expires', 'Last chance'",
                "Include recipient first name in subject",
                "Reschedule to Tuesday or Wednesday, 8-10 AM",
            ])
        if float(m.get("click_rate", 0)) < 5:
            changes.extend([
                "Add prominent CTA button above the fold",
                "Include 2-3 benefit statements in first 50 words",
                "Limit body to 100-200 words with HTML formatting",
            ])
        if not changes:
            changes = [
                "Improve subject line specificity and personalisation",
                "Increase CTA clarity and placement",
                "Adjust send time to peak engagement hours",
            ]
        recommendations.append({
            "variant_id": vid,
            "changes": changes,
            "priority": "high" if score < 6.0 else "medium",
        })
    return recommendations
