"""Utility functions for the optimization engine."""

from __future__ import annotations

from typing import Any


# ── Optimization factor identification ────────────────────────────────────────

def identify_optimization_factors(
    metrics: dict[str, Any],
    customer_results: list[dict[str, Any]],
) -> list[str]:
    """Identify which dimensions can be improved for a variant.

    Args:
        metrics:          Aggregated metrics dict (open_rate, click_rate as 0-1 or 0-100).
        customer_results: Per-customer result dicts with opened/clicked/probabilities.

    Returns:
        List of factor slugs such as "low_subject_line_opens".
    """
    factors: list[str] = []

    # Normalise rates — handle both 0-1 and 0-100 inputs
    open_rate = float(metrics.get("open_rate", 0.0))
    click_rate = float(metrics.get("click_rate", 0.0))
    if open_rate > 1.0:
        open_rate /= 100.0
    if click_rate > 1.0:
        click_rate /= 100.0

    if open_rate < 0.30:
        factors.append("low_subject_line_opens")
    if open_rate < 0.15:
        factors.append("critical_open_rate")

    if click_rate < 0.05:
        factors.append("weak_call_to_action")
    if click_rate < 0.01:
        factors.append("stalled_clicks")

    if customer_results:
        non_openers = [r for r in customer_results if not r.get("opened", False)]
        avg_open_prob = (
            sum(r.get("open_probability", 0.0) for r in customer_results) / len(customer_results)
        )
        if len(non_openers) / len(customer_results) > 0.6:
            factors.append("poor_demographic_targeting")
        if avg_open_prob < 0.4:
            factors.append("suboptimal_send_timing")

        clickers = [r for r in customer_results if r.get("opened", False) and not r.get("clicked", False)]
        if clickers and len(clickers) / max(1, len(customer_results) - len(non_openers)) > 0.7:
            factors.append("poor_body_engagement")

    return factors


def generate_optimization_insights(
    poor_performers: list[dict[str, Any]],
    segment_performance: dict[str, Any],
    customer_results: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Generate actionable optimization insights from performance data.

    Returns:
        List of insight dicts: {type, issue, evidence, recommendation}
    """
    insights: list[dict[str, Any]] = []

    for pp in poor_performers:
        open_rate = float(pp.get("open_rate", 0.0))
        click_rate = float(pp.get("click_rate", 0.0))
        score = float(pp.get("performance_score", 0.0))
        variant_id = pp.get("variant_id", "unknown")

        if open_rate < 0.20:
            insights.append({
                "type": "content",
                "variant_id": variant_id,
                "issue": "Low open rate — subject line underperforming",
                "evidence": f"Open rate {open_rate:.1%} is below 20% threshold",
                "recommendation": "Shorten subject to 40-60 chars, add urgency/personalization",
            })
        if click_rate < 0.05:
            insights.append({
                "type": "content",
                "variant_id": variant_id,
                "issue": "Low click rate — body/CTA not compelling",
                "evidence": f"Click rate {click_rate:.1%} is below 5% threshold",
                "recommendation": "Add prominent CTA above fold; trim body to 100-200 words",
            })
        if score < 0.10:
            insights.append({
                "type": "targeting",
                "variant_id": variant_id,
                "issue": "Overall poor performance — segment may be misaligned",
                "evidence": f"Performance score {score:.3f} below 0.10",
                "recommendation": "Review demographic targeting; consider re-segmentation",
            })

    # Segment-level insights
    worst_seg = segment_performance.get("worst_segment")
    if worst_seg and worst_seg.get("avg_score", 1.0) < 0.15:
        insights.append({
            "type": "targeting",
            "variant_id": None,
            "issue": f"Segment '{worst_seg.get('segment_name')}' is significantly underperforming",
            "evidence": f"Average score {worst_seg.get('avg_score', 0):.3f}",
            "recommendation": "Redesign messaging for this segment or exclude from campaign",
        })

    # Customer-level insights
    if customer_results:
        non_openers = [r for r in customer_results if not r.get("opened", False)]
        if non_openers:
            low_prob = [r for r in non_openers if r.get("open_probability", 1.0) < 0.3]
            if len(low_prob) / len(customer_results) > 0.4:
                insights.append({
                    "type": "timing",
                    "variant_id": None,
                    "issue": "High proportion of customers with low open probability",
                    "evidence": f"{len(low_prob)} customers with open_probability < 30%",
                    "recommendation": "Switch to Tue/Wed 8-10 AM send window for better deliverability",
                })

    return insights


# ── Content improvement helpers ───────────────────────────────────────────────

def build_improvement_prompt_context(
    variant: dict[str, Any],
    insights: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build context dict passed to the content generation agent."""
    relevant = [i for i in insights if i.get("variant_id") in (variant.get("variant_id"), None)]
    recommendations = [i["recommendation"] for i in relevant]
    return {
        "segment_name": variant.get("segment_name", ""),
        "previous_subject": variant.get("subject_line", ""),
        "previous_body": variant.get("email_body", ""),
        "optimization_requirements": recommendations,
        "must_improve": [i["issue"] for i in relevant],
    }
