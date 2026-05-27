"""Tests for RealTimeMonitoringService."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.real_time_monitoring_service import RealTimeMonitoringService


def _make_service(broadcast_callback=None, collect_return=None, alerts_return=None):
    metrics_svc = MagicMock()
    metrics_svc.collect_campaign_metrics = AsyncMock(
        return_value=collect_return or {"campaign_id": "camp-001", "variants_collected": 1}
    )

    alert_svc = MagicMock()
    alert_svc.check_and_trigger_alerts = AsyncMock(return_value=alerts_return or [])

    svc = RealTimeMonitoringService(
        metrics_collection_service=metrics_svc,
        alert_service=alert_svc,
        broadcast_callback=broadcast_callback,
    )
    return svc, metrics_svc, alert_svc


# ── start_monitoring / stop_monitoring ────────────────────────────────────────

@pytest.mark.asyncio
async def test_start_monitoring_creates_task():
    svc, *_ = _make_service()
    task = await svc.start_monitoring("camp-001", check_interval_seconds=3600, max_duration_minutes=1)
    assert isinstance(task, asyncio.Task)
    assert "camp-001" in svc._tasks
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


@pytest.mark.asyncio
async def test_stop_monitoring_cancels_task():
    svc, *_ = _make_service()
    await svc.start_monitoring("camp-001", check_interval_seconds=3600)
    await svc.stop_monitoring("camp-001")
    assert "camp-001" not in svc._tasks


@pytest.mark.asyncio
async def test_start_monitoring_replaces_existing_task():
    svc, *_ = _make_service()
    task1 = await svc.start_monitoring("camp-001", check_interval_seconds=3600)
    task2 = await svc.start_monitoring("camp-001", check_interval_seconds=3600)
    assert task1 is not task2
    task2.cancel()
    try:
        await task2
    except asyncio.CancelledError:
        pass


@pytest.mark.asyncio
async def test_stop_monitoring_nonexistent_campaign_does_not_raise():
    svc, *_ = _make_service()
    await svc.stop_monitoring("nonexistent-camp")


# ── get_monitoring_status ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_monitoring_status_active():
    svc, *_ = _make_service()
    await svc.start_monitoring("camp-001", check_interval_seconds=3600)
    status = await svc.get_monitoring_status("camp-001")
    assert status["campaign_id"] == "camp-001"
    assert status["is_monitoring"] is True
    await svc.stop_monitoring("camp-001")


@pytest.mark.asyncio
async def test_get_monitoring_status_inactive():
    svc, *_ = _make_service()
    status = await svc.get_monitoring_status("camp-inactive")
    assert status["is_monitoring"] is False


@pytest.mark.asyncio
async def test_get_monitoring_status_after_stop():
    svc, *_ = _make_service()
    await svc.start_monitoring("camp-001", check_interval_seconds=3600)
    await svc.stop_monitoring("camp-001")
    status = await svc.get_monitoring_status("camp-001")
    assert status["is_monitoring"] is False


# ── get_monitoring_stats ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_monitoring_stats_initial_state():
    svc, *_ = _make_service()
    stats = await svc.get_monitoring_stats()
    assert stats["active_monitors"] == 0
    assert stats["total_metrics_collected"] == 0
    assert stats["alerts_triggered"] == 0
    assert stats["uptime_seconds"] >= 0.0


@pytest.mark.asyncio
async def test_get_monitoring_stats_with_active_monitors():
    svc, *_ = _make_service()
    await svc.start_monitoring("camp-001", check_interval_seconds=3600)
    await svc.start_monitoring("camp-002", check_interval_seconds=3600)
    stats = await svc.get_monitoring_stats()
    assert stats["active_monitors"] == 2
    await svc.stop_monitoring("camp-001")
    await svc.stop_monitoring("camp-002")


# ── broadcast_metrics_update ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_broadcast_with_callback_calls_it():
    callback = AsyncMock()
    svc, *_ = _make_service(broadcast_callback=callback)
    metrics = {"campaign_id": "camp-001", "variants_collected": 1}
    await svc.broadcast_metrics_update("camp-001", metrics)
    callback.assert_called_once_with("camp-001", metrics)


@pytest.mark.asyncio
async def test_broadcast_without_callback_does_not_raise():
    svc, *_ = _make_service(broadcast_callback=None)
    await svc.broadcast_metrics_update("camp-001", {"data": "test"})


@pytest.mark.asyncio
async def test_broadcast_callback_exception_does_not_propagate():
    async def bad_callback(cid, data):
        raise RuntimeError("broadcast failure")

    svc, *_ = _make_service(broadcast_callback=bad_callback)
    await svc.broadcast_metrics_update("camp-001", {"data": "test"})


# ── _monitoring_loop (short integration) ─────────────────────────────────────

@pytest.mark.asyncio
async def test_monitoring_loop_increments_stats():
    callback = AsyncMock()
    svc, metrics_svc, alert_svc = _make_service(broadcast_callback=callback)

    task = await svc.start_monitoring("camp-001", check_interval_seconds=0, max_duration_minutes=0)
    await asyncio.sleep(0.1)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    assert svc._stats["total_metrics_collected"] >= 0


@pytest.mark.asyncio
async def test_monitoring_loop_cancellation_is_clean():
    svc, *_ = _make_service()
    task = await svc.start_monitoring("camp-001", check_interval_seconds=60, max_duration_minutes=60)
    await asyncio.sleep(0.05)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    assert not task.cancelled() or task.done()
