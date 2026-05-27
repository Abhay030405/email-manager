"""Tests for statistical_analysis utilities."""

from __future__ import annotations

import math

import pytest

from app.utils.statistical_analysis import (
    calculate_confidence_interval,
    calculate_sample_size,
    calculate_statistical_power,
    perform_statistical_test,
)


# ── calculate_confidence_interval ────────────────────────────────────────────

def test_confidence_interval_50_percent_rate():
    lo, hi = calculate_confidence_interval(1000, 0.50)
    assert lo < 0.50 < hi
    assert 0.0 <= lo <= hi <= 1.0


def test_confidence_interval_zero_sample_size():
    lo, hi = calculate_confidence_interval(0, 0.30)
    assert lo == 0.0
    assert hi == 1.0


def test_confidence_interval_zero_rate():
    lo, hi = calculate_confidence_interval(100, 0.0)
    assert lo == 0.0
    assert hi >= 0.0


def test_confidence_interval_full_rate():
    lo, hi = calculate_confidence_interval(100, 1.0)
    assert hi == 1.0
    assert lo >= 0.0


def test_confidence_interval_width_decreases_with_more_samples():
    lo1, hi1 = calculate_confidence_interval(100, 0.30)
    lo2, hi2 = calculate_confidence_interval(10000, 0.30)
    width_100 = hi1 - lo1
    width_10k = hi2 - lo2
    assert width_10k < width_100


def test_confidence_interval_99_percent_wider_than_95():
    lo95, hi95 = calculate_confidence_interval(500, 0.30, confidence_level=0.95)
    lo99, hi99 = calculate_confidence_interval(500, 0.30, confidence_level=0.99)
    assert (hi99 - lo99) > (hi95 - lo95)


# ── perform_statistical_test ──────────────────────────────────────────────────

def test_statistical_test_significant_difference():
    # A: 60/100 opens vs B: 20/100 opens — clear difference
    result = perform_statistical_test([60, 100], [20, 100])
    assert result["is_significant"] is True
    assert result["p_value"] < 0.05


def test_statistical_test_no_difference():
    # A: 30/100 vs B: 30/100 — identical
    result = perform_statistical_test([30, 100], [30, 100])
    assert result["is_significant"] is False
    assert result["p_value"] == pytest.approx(1.0, abs=0.1)


def test_statistical_test_zero_samples():
    result = perform_statistical_test([0, 0], [30, 100])
    assert result["is_significant"] is False
    assert result["p_value"] == 1.0


def test_statistical_test_returns_required_keys():
    result = perform_statistical_test([40, 100], [25, 100])
    assert "p_value" in result
    assert "is_significant" in result
    assert "confidence_level" in result
    assert "z_score" in result


def test_statistical_test_p_value_in_range():
    result = perform_statistical_test([50, 200], [35, 200])
    assert 0.0 <= result["p_value"] <= 1.0


def test_statistical_test_all_successes():
    # 100/100 vs 50/100
    result = perform_statistical_test([100, 100], [50, 100])
    assert result["is_significant"] is True


def test_statistical_test_custom_confidence():
    result = perform_statistical_test([55, 100], [45, 100], confidence_level=0.99)
    assert result["confidence_level"] == 0.99


# ── calculate_sample_size ─────────────────────────────────────────────────────

def test_sample_size_positive():
    n = calculate_sample_size(baseline_rate=0.25, minimum_lift=0.10)
    assert n > 0


def test_sample_size_minimum_100():
    n = calculate_sample_size(baseline_rate=0.50, minimum_lift=0.50)
    assert n >= 100


def test_sample_size_larger_for_small_lift():
    n_small_lift = calculate_sample_size(0.25, 0.05)
    n_large_lift = calculate_sample_size(0.25, 0.30)
    assert n_small_lift > n_large_lift


def test_sample_size_larger_for_higher_confidence():
    n_95 = calculate_sample_size(0.25, 0.10, confidence_level=0.95)
    n_99 = calculate_sample_size(0.25, 0.10, confidence_level=0.99)
    assert n_99 > n_95


def test_sample_size_zero_lift_returns_max():
    n = calculate_sample_size(0.25, 0.0)
    assert n == 10_000


# ── calculate_statistical_power ───────────────────────────────────────────────

def test_statistical_power_in_range():
    power = calculate_statistical_power(1000, 0.25, 0.30)
    assert 0.0 <= power <= 1.0


def test_statistical_power_zero_samples():
    power = calculate_statistical_power(0, 0.25, 0.30)
    assert power == 0.0


def test_statistical_power_equal_rates():
    power = calculate_statistical_power(1000, 0.30, 0.30)
    assert power == 0.0


def test_statistical_power_increases_with_sample_size():
    p_small = calculate_statistical_power(100, 0.25, 0.30)
    p_large = calculate_statistical_power(10000, 0.25, 0.30)
    assert p_large >= p_small
