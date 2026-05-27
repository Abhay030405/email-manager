"""Statistical analysis utilities — pure-math implementation (no scipy/numpy)."""

from __future__ import annotations

import math
from typing import Any


# ── Normal distribution helpers ───────────────────────────────────────────────

def _normal_cdf(z: float) -> float:
    """Standard normal CDF using math.erfc."""
    return 0.5 * math.erfc(-z / math.sqrt(2))


def _z_critical(confidence_level: float) -> float:
    """Return the z critical value for a two-tailed test."""
    alpha = 1 - confidence_level
    # Common lookup for standard confidence levels
    _table = {0.90: 1.645, 0.95: 1.960, 0.99: 2.576}
    if confidence_level in _table:
        return _table[confidence_level]
    # Binary search on the normal CDF for arbitrary confidence levels
    target = 1 - alpha / 2
    lo, hi = 0.0, 10.0
    for _ in range(60):
        mid = (lo + hi) / 2
        if _normal_cdf(mid) < target:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


# ── Confidence intervals ──────────────────────────────────────────────────────

def calculate_confidence_interval(
    sample_size: int,
    success_rate: float,
    confidence_level: float = 0.95,
) -> tuple[float, float]:
    """Wilson score confidence interval for a proportion.

    Args:
        sample_size:     Number of observations.
        success_rate:    Observed proportion (0.0 – 1.0).
        confidence_level: Desired confidence (default 0.95).

    Returns:
        (lower_bound, upper_bound) as floats in [0, 1].
    """
    if sample_size == 0:
        return (0.0, 1.0)

    p = max(0.0, min(1.0, success_rate))
    z = _z_critical(confidence_level)
    n = sample_size

    denom = 1 + z ** 2 / n
    centre = (p + z ** 2 / (2 * n)) / denom
    margin = (z * math.sqrt(p * (1 - p) / n + z ** 2 / (4 * n ** 2))) / denom

    lower = max(0.0, centre - margin)
    upper = min(1.0, centre + margin)
    return (round(lower, 6), round(upper, 6))


# ── Two-proportion z-test ─────────────────────────────────────────────────────

def perform_statistical_test(
    sample_a: list[int],
    sample_b: list[int],
    confidence_level: float = 0.95,
) -> dict[str, Any]:
    """Two-proportion z-test for significance.

    Args:
        sample_a: [successes, total] for variant A.
        sample_b: [successes, total] for variant B.
        confidence_level: Desired confidence (default 0.95).

    Returns:
        {p_value, is_significant, confidence_level, z_score}
    """
    successes_a, n_a = sample_a[0], sample_a[1]
    successes_b, n_b = sample_b[0], sample_b[1]

    if n_a == 0 or n_b == 0:
        return {
            "p_value": 1.0,
            "is_significant": False,
            "confidence_level": confidence_level,
            "z_score": 0.0,
        }

    p_a = successes_a / n_a
    p_b = successes_b / n_b
    p_pool = (successes_a + successes_b) / (n_a + n_b)

    if p_pool in (0.0, 1.0):
        return {
            "p_value": 1.0,
            "is_significant": False,
            "confidence_level": confidence_level,
            "z_score": 0.0,
        }

    se = math.sqrt(p_pool * (1 - p_pool) * (1 / n_a + 1 / n_b))
    if se == 0:
        return {
            "p_value": 1.0,
            "is_significant": False,
            "confidence_level": confidence_level,
            "z_score": 0.0,
        }

    z = (p_a - p_b) / se
    # Two-tailed p-value
    p_value = 2 * (1 - _normal_cdf(abs(z)))
    alpha = 1 - confidence_level

    return {
        "p_value": round(p_value, 6),
        "is_significant": p_value < alpha,
        "confidence_level": confidence_level,
        "z_score": round(z, 4),
    }


# ── Sample size calculation ───────────────────────────────────────────────────

def calculate_sample_size(
    baseline_rate: float,
    minimum_lift: float,
    confidence_level: float = 0.95,
    power: float = 0.8,
) -> int:
    """Minimum sample size per variant for a two-proportion test.

    Args:
        baseline_rate:  Expected rate for the control (0.0 – 1.0).
        minimum_lift:   Minimum detectable lift as a proportion (e.g., 0.10 for 10%).
        confidence_level: Desired confidence level (default 0.95).
        power:          Desired statistical power (default 0.80).

    Returns:
        Minimum number of subjects per variant.
    """
    baseline_rate = max(1e-6, min(1 - 1e-6, baseline_rate))
    treatment_rate = min(1.0, baseline_rate * (1 + minimum_lift))

    z_alpha = _z_critical(confidence_level)
    # z for power (one-tailed)
    z_beta_table = {0.80: 0.842, 0.85: 1.036, 0.90: 1.282, 0.95: 1.645}
    z_beta = z_beta_table.get(round(power, 2), 0.842)

    p_avg = (baseline_rate + treatment_rate) / 2
    numerator = (
        z_alpha * math.sqrt(2 * p_avg * (1 - p_avg))
        + z_beta * math.sqrt(baseline_rate * (1 - baseline_rate) + treatment_rate * (1 - treatment_rate))
    ) ** 2
    denominator = (treatment_rate - baseline_rate) ** 2

    if denominator == 0:
        return 10_000

    return max(100, math.ceil(numerator / denominator))


# ── Statistical power ─────────────────────────────────────────────────────────

def calculate_statistical_power(
    sample_size: int,
    baseline_rate: float,
    treatment_rate: float,
    confidence_level: float = 0.95,
) -> float:
    """Estimate statistical power for given sample size and effect size."""
    if sample_size == 0 or baseline_rate == treatment_rate:
        return 0.0

    z_alpha = _z_critical(confidence_level)
    p_avg = (baseline_rate + treatment_rate) / 2
    se_null = math.sqrt(2 * p_avg * (1 - p_avg) / sample_size)
    se_alt = math.sqrt(
        baseline_rate * (1 - baseline_rate) / sample_size
        + treatment_rate * (1 - treatment_rate) / sample_size
    )
    if se_alt == 0:
        return 1.0

    z_power = (abs(treatment_rate - baseline_rate) - z_alpha * se_null) / se_alt
    return round(_normal_cdf(z_power), 4)
