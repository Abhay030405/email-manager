"""Optimization Agent — generates data-driven recommendations to improve campaign performance."""

from __future__ import annotations

import logging
from typing import Any

from app.agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)

# Performance score: 0.7 * click_rate + 0.3 * open_rate (rates as percentages 0-100)
SCORE_THRESHOLD = 12.0


class OptimizationAgent(BaseAgent):
    """Analyzes Mock API metrics and generates actionable optimization recommendations.

    Uses GPT-4 to interpret performance patterns and suggest improvements for:
    - Subject line length and personalization (40-60 chars for best Mock API score)
    - Email body quality (100-200 words HTML with CTAs)
    - Send timing (Tue/Wed 8-10 AM for ~18% open-rate boost)
    - Demographic re-targeting based on per-customer results
    """

    def __init__(self) -> None:
        super().__init__(model_name="gpt-4", temperature=0.3, max_tokens=2000)

    async def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Delegate to optimize_campaign using fields from input_data."""
        campaign_id = input_data.get("campaign_id", "")
        metrics = input_data.get("metrics", {})
        return await self.optimize_campaign(campaign_id, metrics)

    async def optimize_campaign(
        self, campaign_id: str, metrics: dict[str, Any]
    ) -> dict[str, Any]:
        """Analyze metrics and generate optimization recommendations.

        Args:
            campaign_id: Internal campaign identifier.
            metrics:     Dict with ``variant_metrics``, ``aggregates``,
                         and optionally ``customer_results``.

        Returns:
            Dict with ``optimization_recommendations`` list.
        """
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

    async def _call_llm(self, prompt: str) -> str:
        from langchain.schema import HumanMessage
        response = await self.llm.agenerate([[HumanMessage(content=prompt)]])
        return response.generations[0][0].text


def _analyze_customer_results(results: list[dict[str, Any]]) -> dict[str, Any]:
    if not results:
        return {}
    non_openers = [r for r in results if not r.get("opened")]
    low_clickers = [r for r in results if r.get("opened") and not r.get("clicked")]
    avg_open_prob = (
        sum(r.get("open_probability", 0.0) for r in results) / len(results)
        if results else 0.0
    )
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
        "You are a marketing optimization expert. Based on the following email campaign "
        "performance data, generate specific optimization recommendations.",
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
            f"CUSTOMER BEHAVIOR: {demographic_insights.get('non_opener_count', 0)} non-openers, "
            f"avg open probability={demographic_insights.get('avg_open_probability', 0):.2f}",
        ])
    lines.extend([
        "",
        "Provide recommendations as a JSON array. Each element should have:",
        '{"variant_id": "...", "changes": ["improvement 1", ...], "priority": "high|medium|low"}',
        "",
        "Focus on: subject line (40-60 chars, urgency/personalization/emoji), "
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
                "Improve subject line specificity and personalization",
                "Increase CTA clarity and placement",
                "Adjust send time to peak engagement hours",
            ]
        recommendations.append({
            "variant_id": vid,
            "changes": changes,
            "priority": "high" if score < 6.0 else "medium",
        })
    return recommendations
