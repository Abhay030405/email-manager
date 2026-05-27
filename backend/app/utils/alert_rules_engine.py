"""Alert rules engine — evaluates metrics against configurable thresholds."""

from __future__ import annotations

from typing import Any, Optional

from app.models.metrics import Metrics


RULES: dict[str, dict[str, Any]] = {
    "low_open_rate": {
        "metric": "open_rate",
        "operator": "lt",
        "threshold": 0.30,   # 30% expressed as 0.0-1.0
        "severity": "warning",
    },
    "critical_open_rate": {
        "metric": "open_rate",
        "operator": "lt",
        "threshold": 0.15,
        "severity": "critical",
    },
    "low_click_rate": {
        "metric": "click_rate",
        "operator": "lt",
        "threshold": 0.05,
        "severity": "warning",
    },
    "stalled_clicks": {
        "metric": "click_rate",
        "operator": "lt",
        "threshold": 0.01,
        "severity": "critical",
    },
}

_RECOMMENDATIONS: dict[str, str] = {
    "low_open_rate": "Try improving subject line personalisation and review send time.",
    "critical_open_rate": "Immediately review subject lines, sender reputation, and spam filters.",
    "low_click_rate": "Ensure the CTA link is prominent, functional, and above the fold.",
    "stalled_clicks": "Pause and redesign email layout. Focus on value proposition and clear CTA.",
    "declining_performance": "Investigate audience fatigue. Consider re-segmentation or content refresh.",
}

_MESSAGES: dict[str, str] = {
    "low_open_rate": "Open rate {actual:.1%} is below the {threshold:.0%} warning threshold.",
    "critical_open_rate": "CRITICAL: Open rate {actual:.1%} is below the {threshold:.0%} critical threshold.",
    "low_click_rate": "Click rate {actual:.1%} is below the {threshold:.0%} warning threshold.",
    "stalled_clicks": "CRITICAL: Click rate {actual:.1%} is below the {threshold:.0%} critical threshold.",
    "declining_performance": "Performance trend is declining.",
}


class AlertRulesEngine:
    """Evaluates alert rules against a Metrics document."""

    def __init__(self, custom_rules: dict[str, dict[str, Any]] | None = None) -> None:
        self._rules = dict(RULES)
        if custom_rules:
            self._rules.update(custom_rules)

    def evaluate_rules(
        self,
        metrics: Metrics,
        trend: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """Return a list of violated rule dicts; empty if everything is fine."""
        violations: list[dict[str, Any]] = []

        for rule_name, rule in self._rules.items():
            metric_val = getattr(metrics, rule["metric"], None)
            if metric_val is None:
                continue
            if self.evaluate_custom_rule(metric_val, rule["operator"], rule["threshold"]):
                threshold_display = rule["threshold"]
                actual_display = metric_val
                violations.append({
                    "alert_type": rule_name,
                    "severity": rule["severity"],
                    "threshold": threshold_display,
                    "actual_value": actual_display,
                    "message": _MESSAGES.get(rule_name, rule_name).format(
                        actual=actual_display, threshold=threshold_display
                    ),
                    "recommendation": self.get_recommendation(rule_name),
                })

        if trend == "declining":
            violations.append({
                "alert_type": "declining_performance",
                "severity": "warning",
                "threshold": 0.0,
                "actual_value": 0.0,
                "message": _MESSAGES["declining_performance"],
                "recommendation": self.get_recommendation("declining_performance"),
            })

        return violations

    @staticmethod
    def evaluate_custom_rule(metric_value: float, operator: str, threshold: float) -> bool:
        """Return True if the rule is *violated* (alert should fire)."""
        ops = {
            "lt": lambda v, t: v < t,
            "lte": lambda v, t: v <= t,
            "gt": lambda v, t: v > t,
            "gte": lambda v, t: v >= t,
            "eq": lambda v, t: v == t,
            "ne": lambda v, t: v != t,
        }
        fn = ops.get(operator)
        if fn is None:
            return False
        return fn(metric_value, threshold)

    @staticmethod
    def get_recommendation(alert_type: str) -> str:
        return _RECOMMENDATIONS.get(alert_type, "Review campaign performance and take corrective action.")
