"""Metrics utility functions — conversion, scoring, and statistical helpers."""

from __future__ import annotations

import math
from datetime import datetime
from typing import Any


# ── Conversion ────────────────────────────────────────────────────────────────

def convert_mock_api_metrics_to_percentages(metrics: dict[str, Any]) -> dict[str, Any]:
    """Convert 0.0-1.0 rate fields from the Mock API to percentages (0.0-100.0)."""
    result = dict(metrics)
    for field in ("open_rate", "click_rate", "click_through_rate"):
        if field in result and result[field] is not None:
            result[field] = round(float(result[field]) * 100, 4)
    return result


def calculate_performance_score(open_rate: float, click_rate: float) -> float:
    """Return performance_score in [0, 1].

    Formula: 0.7 * click_rate_pct/100 + 0.3 * open_rate_pct/100
    Accepts percentages (0-100) and normalises internally.
    """
    click_norm = max(0.0, min(click_rate / 100.0, 1.0))
    open_norm = max(0.0, min(open_rate / 100.0, 1.0))
    return round(0.7 * click_norm + 0.3 * open_norm, 4)


def calculate_engagement_score(
    open_rate: float, click_rate: float, ctr: float
) -> float:
    """Return weighted engagement score in [0, 100].

    Weights: open 40%, click 40%, CTR 20%.
    All inputs expected as percentages (0-100).
    """
    capped = lambda v: max(0.0, min(v, 100.0))
    return round(0.4 * capped(open_rate) + 0.4 * capped(click_rate) + 0.2 * capped(ctr), 4)


# ── Statistical helpers ───────────────────────────────────────────────────────

def calculate_std_dev(values: list[float]) -> float:
    """Population standard deviation of *values*. Returns 0.0 for < 2 points."""
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    variance = sum((v - mean) ** 2 for v in values) / len(values)
    return round(math.sqrt(variance), 6)


def calculate_percentile(value: float, values: list[float]) -> int:
    """Return 0-100 percentile rank of *value* within *values*."""
    if not values:
        return 0
    below = sum(1 for v in values if v < value)
    return round(below / len(values) * 100)


def calculate_trend(
    values: list[float],
    timestamps: list[datetime] | None = None,
) -> tuple[str, float]:
    """Determine trend direction and rate of change.

    Returns:
        (trend, rate_of_change_pct) where trend is "improving", "stable", or "declining".
    """
    if len(values) < 2:
        return "stable", 0.0
    first, last = values[0], values[-1]
    if first == 0:
        return "stable", 0.0
    rate = (last - first) / abs(first) * 100
    if rate > 5:
        trend = "improving"
    elif rate < -5:
        trend = "declining"
    else:
        trend = "stable"
    return trend, round(rate, 4)


# ── Time helpers ──────────────────────────────────────────────────────────────

def calculate_time_to_event(event_timestamp: datetime, campaign_send_time: datetime) -> int:
    """Return minutes elapsed from *campaign_send_time* to *event_timestamp*."""
    delta = event_timestamp - campaign_send_time
    return max(0, int(delta.total_seconds() / 60))


def get_business_hours_elapsed(start_time: datetime, end_time: datetime) -> float:
    """Calculate business hours (09:00–17:00) elapsed between two datetimes."""
    BUSINESS_START = 9
    BUSINESS_END = 17
    total_seconds = 0.0
    current = start_time
    while current < end_time:
        # Advance to start of next business period
        if current.hour < BUSINESS_START:
            current = current.replace(hour=BUSINESS_START, minute=0, second=0)
        if current.hour >= BUSINESS_END:
            # Skip to next day business start
            from datetime import timedelta
            current = (current + timedelta(days=1)).replace(hour=BUSINESS_START, minute=0, second=0)
        if current >= end_time:
            break
        period_end = min(end_time, current.replace(hour=BUSINESS_END, minute=0, second=0))
        if period_end > current:
            total_seconds += (period_end - current).total_seconds()
        current = current.replace(hour=BUSINESS_END, minute=0, second=0)
    return round(total_seconds / 3600, 4)
