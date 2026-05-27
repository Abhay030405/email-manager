"""Tests for ExecutionLog model and ExecutionLogRepository."""

from __future__ import annotations

import asyncio

import pytest
from mongomock_motor import AsyncMongoMockClient

from app.db.repositories.execution_log_repo import ExecutionLogRepository
from app.models.execution_log import ExecutionLog, ExecutionLogStatus


def run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


@pytest.fixture
def db():
    client = AsyncMongoMockClient()
    return client["campaignx_test"]


@pytest.fixture
def log_repo(db):
    return ExecutionLogRepository(db)


def _make_log(campaign_id="camp-1", variant_id="var-1", status=ExecutionLogStatus.SUCCESS) -> ExecutionLog:
    return ExecutionLog(
        campaign_id=campaign_id,
        variant_id=variant_id,
        mock_campaign_id="mock-uuid-001",
        status=status,
        customer_count=100,
    )


# ── ExecutionLog model ────────────────────────────────────────────────────────

def test_execution_log_default_id_generated():
    log = ExecutionLog(campaign_id="c1", variant_id="v1", status=ExecutionLogStatus.SUCCESS)
    assert log.log_id is not None
    assert len(log.log_id) > 0


def test_execution_log_to_dict():
    log = _make_log()
    d = log.to_dict()
    assert d["campaign_id"] == "camp-1"
    assert d["status"] == "success"


def test_execution_log_statuses():
    for s in ExecutionLogStatus:
        log = ExecutionLog(campaign_id="c", variant_id="v", status=s)
        assert log.status == s


# ── ExecutionLogRepository ────────────────────────────────────────────────────

def test_repo_create_and_find_by_id(log_repo):
    log = _make_log()
    run(log_repo.create(log))
    found = run(log_repo.find_by_id(log.log_id))
    assert found is not None
    assert found.log_id == log.log_id


def test_repo_find_by_campaign(log_repo):
    log1 = _make_log(campaign_id="camp-A")
    log2 = _make_log(campaign_id="camp-A")
    log3 = _make_log(campaign_id="camp-B")
    run(log_repo.create(log1))
    run(log_repo.create(log2))
    run(log_repo.create(log3))
    results = run(log_repo.find_by_campaign("camp-A"))
    assert len(results) == 2
    assert all(r.campaign_id == "camp-A" for r in results)


def test_repo_find_by_variant(log_repo):
    log1 = _make_log(variant_id="var-X")
    log2 = _make_log(variant_id="var-Y")
    run(log_repo.create(log1))
    run(log_repo.create(log2))
    results = run(log_repo.find_by_variant("var-X"))
    assert len(results) == 1
    assert results[0].variant_id == "var-X"


def test_repo_find_failed(log_repo):
    success_log = _make_log(status=ExecutionLogStatus.SUCCESS)
    failed_log = _make_log(status=ExecutionLogStatus.FAILED)
    run(log_repo.create(success_log))
    run(log_repo.create(failed_log))
    failures = run(log_repo.find_failed("camp-1"))
    assert len(failures) == 1
    assert failures[0].status == ExecutionLogStatus.FAILED


def test_repo_find_failed_empty(log_repo):
    run(log_repo.create(_make_log(status=ExecutionLogStatus.SUCCESS)))
    failures = run(log_repo.find_failed("camp-1"))
    assert failures == []


def test_repo_count_by_status(log_repo):
    run(log_repo.create(_make_log(status=ExecutionLogStatus.SUCCESS)))
    run(log_repo.create(_make_log(status=ExecutionLogStatus.SUCCESS)))
    run(log_repo.create(_make_log(status=ExecutionLogStatus.FAILED)))
    counts = run(log_repo.count_by_status("camp-1"))
    assert counts.get("success", 0) == 2
    assert counts.get("failed", 0) == 1


def test_repo_find_by_campaign_empty(log_repo):
    results = run(log_repo.find_by_campaign("no-such-campaign"))
    assert results == []
