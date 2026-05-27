"""Tests for AlertService and AlertRulesEngine."""

from __future__ import annotations

import logging
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.performance_alert import PerformanceAlert
from app.services.alert_service import AlertService
from app.utils.alert_rules_engine import AlertRulesEngine, RULES
from tests.test_services.conftest import make_metrics


def _make_service(alert_exists: bool = False, existing_alerts=None):
    alert_repo = MagicMock()
    alert_repo.alert_exists = AsyncMock(return_value=alert_exists)
    alert_repo.create = AsyncMock()

    async def fake_acknowledge(alert_id, user):
        a = PerformanceAlert(
            alert_id=alert_id,
            campaign_id="camp-001",
            alert_type="low_open_rate",
            severity="warning",
            threshold=0.30,
            actual_value=0.20,
            triggered_at=datetime.utcnow(),
            message="low",
            recommendation="fix it",
            acknowledged=True,
            acknowledged_by=user,
            acknowledged_at=datetime.utcnow(),
        )
        return a

    alert_repo.acknowledge_alert = AsyncMock(side_effect=fake_acknowledge)
    alert_repo.update = AsyncMock()
    alert_repo.list_active_alerts = AsyncMock(return_value=existing_alerts or [])

    metrics_repo = MagicMock()
    metrics_repo.find_by_campaign = AsyncMock(return_value=[])
    metrics_repo.calculate_trend = AsyncMock(return_value="stable")

    campaign_repo = MagicMock()
    rules_engine = AlertRulesEngine()

    svc = AlertService(
        alert_repo=alert_repo,
        metrics_repo=metrics_repo,
        campaign_repo=campaign_repo,
        rules_engine=rules_engine,
    )
    return svc, alert_repo, metrics_repo


def _make_alert(
    campaign_id: str = "camp-001",
    alert_type: str = "low_open_rate",
    severity: str = "warning",
) -> PerformanceAlert:
    return PerformanceAlert(
        campaign_id=campaign_id,
        alert_type=alert_type,
        severity=severity,
        threshold=0.30,
        actual_value=0.20,
        triggered_at=datetime.utcnow(),
        message="Open rate below threshold",
        recommendation="Improve subject line",
    )


# ── trigger_alert ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_trigger_alert_creates_new_alert():
    svc, alert_repo, _ = _make_service(alert_exists=False)
    alert = await svc.trigger_alert(
        campaign_id="camp-001",
        alert_type="low_open_rate",
        severity="warning",
        threshold=0.30,
        actual_value=0.20,
    )
    assert alert is not None
    assert alert.campaign_id == "camp-001"
    alert_repo.create.assert_called_once()


@pytest.mark.asyncio
async def test_trigger_alert_deduplication_skips_existing():
    svc, alert_repo, _ = _make_service(alert_exists=True)
    result = await svc.trigger_alert(
        campaign_id="camp-001",
        alert_type="low_open_rate",
        severity="warning",
        threshold=0.30,
        actual_value=0.20,
    )
    assert result is None
    alert_repo.create.assert_not_called()


@pytest.mark.asyncio
async def test_trigger_alert_uses_custom_message():
    svc, alert_repo, _ = _make_service(alert_exists=False)
    alert = await svc.trigger_alert(
        campaign_id="camp-001",
        alert_type="low_open_rate",
        severity="warning",
        threshold=0.30,
        actual_value=0.20,
        message="Custom message",
        recommendation="Do something",
    )
    assert alert.message == "Custom message"
    assert alert.recommendation == "Do something"


@pytest.mark.asyncio
async def test_trigger_alert_with_variant_id():
    svc, alert_repo, _ = _make_service(alert_exists=False)
    alert = await svc.trigger_alert(
        campaign_id="camp-001",
        alert_type="low_click_rate",
        severity="warning",
        threshold=0.05,
        actual_value=0.02,
        variant_id="var-001",
    )
    assert alert is not None
    assert alert.variant_id == "var-001"


# ── check_and_trigger_alerts ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_check_and_trigger_alerts_no_metrics():
    svc, alert_repo, metrics_repo = _make_service()
    metrics_repo.find_by_campaign = AsyncMock(return_value=[])
    result = await svc.check_and_trigger_alerts("camp-001")
    assert result == []
    alert_repo.create.assert_not_called()


@pytest.mark.asyncio
async def test_check_and_trigger_alerts_fires_on_low_open_rate():
    m = make_metrics(open_rate=0.10, click_rate=0.02)
    svc, alert_repo, metrics_repo = _make_service(alert_exists=False)
    metrics_repo.find_by_campaign = AsyncMock(return_value=[m])

    alerts = await svc.check_and_trigger_alerts("camp-001")
    assert len(alerts) > 0
    types = {a.alert_type for a in alerts}
    assert "critical_open_rate" in types or "low_open_rate" in types


@pytest.mark.asyncio
async def test_check_and_trigger_alerts_no_violations_for_good_metrics():
    m = make_metrics(open_rate=0.45, click_rate=0.12)
    svc, alert_repo, metrics_repo = _make_service(alert_exists=False)
    metrics_repo.find_by_campaign = AsyncMock(return_value=[m])

    alerts = await svc.check_and_trigger_alerts("camp-001")
    assert alerts == []


@pytest.mark.asyncio
async def test_check_and_trigger_alerts_dedup_prevents_duplicates():
    m = make_metrics(open_rate=0.10, click_rate=0.02)
    svc, alert_repo, metrics_repo = _make_service(alert_exists=True)
    metrics_repo.find_by_campaign = AsyncMock(return_value=[m])

    alerts = await svc.check_and_trigger_alerts("camp-001")
    assert alerts == []


# ── acknowledge_alert ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_acknowledge_alert_marks_acknowledged():
    svc, alert_repo, _ = _make_service()
    result = await svc.acknowledge_alert("alert-001", "admin-user")
    assert result is not None
    assert result.acknowledged is True
    assert result.acknowledged_by == "admin-user"


@pytest.mark.asyncio
async def test_acknowledge_alert_with_notes_updates_metadata():
    svc, alert_repo, _ = _make_service()
    await svc.acknowledge_alert("alert-001", "admin-user", notes="Investigated and resolved")
    alert_repo.update.assert_called_once()


# ── get_active_alerts ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_active_alerts_returns_all():
    a1 = _make_alert()
    a2 = _make_alert(alert_type="low_click_rate")
    svc, alert_repo, _ = _make_service(existing_alerts=[a1, a2])

    result = await svc.get_active_alerts()
    assert len(result) == 2


@pytest.mark.asyncio
async def test_get_active_alerts_filters_by_severity():
    warning = _make_alert(severity="warning")
    critical = _make_alert(severity="critical", alert_type="critical_open_rate")
    svc, alert_repo, _ = _make_service(existing_alerts=[warning, critical])

    result = await svc.get_active_alerts(severity="critical")
    assert all(a.severity == "critical" for a in result)
    assert len(result) == 1


@pytest.mark.asyncio
async def test_get_active_alerts_filtered_by_campaign_passed_to_repo():
    svc, alert_repo, _ = _make_service(existing_alerts=[])
    await svc.get_active_alerts(campaign_id="camp-abc")
    alert_repo.list_active_alerts.assert_called_with(campaign_id="camp-abc")


# ── notify_about_alert ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_notify_about_alert_logs_critical(caplog):
    svc, *_ = _make_service()
    alert = _make_alert(severity="critical", alert_type="critical_open_rate")
    with caplog.at_level(logging.CRITICAL):
        await svc.notify_about_alert(alert)
    assert alert.alert_type in caplog.text


@pytest.mark.asyncio
async def test_notify_about_alert_logs_warning(caplog):
    svc, *_ = _make_service()
    alert = _make_alert(severity="warning")
    with caplog.at_level(logging.WARNING):
        await svc.notify_about_alert(alert)
    assert alert.alert_type in caplog.text


# ── AlertRulesEngine ──────────────────────────────────────────────────────────

def test_rules_engine_evaluate_rules_all_pass():
    engine = AlertRulesEngine()
    m = make_metrics(open_rate=0.45, click_rate=0.10)
    violations = engine.evaluate_rules(m)
    assert violations == []


def test_rules_engine_evaluate_rules_low_open_rate_violation():
    engine = AlertRulesEngine()
    m = make_metrics(open_rate=0.20, click_rate=0.08)
    violations = engine.evaluate_rules(m)
    types = [v["alert_type"] for v in violations]
    assert "low_open_rate" in types


def test_rules_engine_evaluate_rules_critical_open_rate():
    engine = AlertRulesEngine()
    m = make_metrics(open_rate=0.10, click_rate=0.08)
    violations = engine.evaluate_rules(m)
    types = [v["alert_type"] for v in violations]
    assert "critical_open_rate" in types
    assert "low_open_rate" in types


def test_rules_engine_evaluate_rules_stalled_clicks():
    engine = AlertRulesEngine()
    m = make_metrics(open_rate=0.35, click_rate=0.005)
    violations = engine.evaluate_rules(m)
    types = [v["alert_type"] for v in violations]
    assert "stalled_clicks" in types
    assert "low_click_rate" in types


def test_rules_engine_declining_trend_adds_violation():
    engine = AlertRulesEngine()
    m = make_metrics(open_rate=0.45, click_rate=0.10)
    violations = engine.evaluate_rules(m, trend="declining")
    types = [v["alert_type"] for v in violations]
    assert "declining_performance" in types


def test_rules_engine_custom_rules_override():
    custom = {
        "super_high_open": {
            "metric": "open_rate",
            "operator": "gt",
            "threshold": 0.90,
            "severity": "info",
        }
    }
    engine = AlertRulesEngine(custom_rules=custom)
    m = make_metrics(open_rate=0.95, click_rate=0.10)
    violations = engine.evaluate_rules(m)
    types = [v["alert_type"] for v in violations]
    assert "super_high_open" in types


@pytest.mark.parametrize("operator,value,threshold,expected", [
    ("lt", 0.20, 0.30, True),
    ("lt", 0.35, 0.30, False),
    ("lte", 0.30, 0.30, True),
    ("gt", 0.50, 0.30, True),
    ("gte", 0.30, 0.30, True),
    ("eq", 0.50, 0.50, True),
    ("ne", 0.50, 0.30, True),
    ("ne", 0.30, 0.30, False),
    ("invalid_op", 0.50, 0.30, False),
])
def test_rules_engine_evaluate_custom_rule_operators(operator, value, threshold, expected):
    result = AlertRulesEngine.evaluate_custom_rule(value, operator, threshold)
    assert result == expected


def test_rules_engine_get_recommendation_known_type():
    rec = AlertRulesEngine.get_recommendation("low_open_rate")
    assert len(rec) > 10


def test_rules_engine_get_recommendation_unknown_type():
    rec = AlertRulesEngine.get_recommendation("nonexistent_rule")
    assert "corrective" in rec.lower() or len(rec) > 5
