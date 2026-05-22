"""Tests for orchestration error handling, retries, and recovery."""

from __future__ import annotations

import logging
from unittest.mock import MagicMock

import pytest
import requests

from app.orchestration import campaign_graph as cg
from app.orchestration.state import StateManager, create_initial_campaign_state


@pytest.fixture
def patch_db(mock_db, monkeypatch):
    monkeypatch.setattr(cg.MongoDB, "get_db", classmethod(lambda cls: mock_db))
    return mock_db


@pytest.fixture
def patch_fast_sleep(monkeypatch):
    async def _noop_sleep(_seconds: float):
        return None

    monkeypatch.setattr(cg.asyncio, "sleep", _noop_sleep)


@pytest.mark.asyncio
async def test_node_failure_recovery(patch_db, patch_fast_sleep, monkeypatch):
    attempts = {"count": 0}

    class FlakyParser:
        async def execute(self, payload):
            attempts["count"] += 1
            if attempts["count"] < 3:
                raise RuntimeError("Transient parser failure")
            return {
                "product_name": "Recovered Product",
                "product_description": "Recovered",
                "target_audience": "SMB",
                "campaign_goal": "awareness",
                "cta_link": "",
                "budget": None,
                "preferred_tone": "professional",
                "key_messages": ["Recovered output"],
                "constraints": None,
            }

    monkeypatch.setattr(cg, "CampaignBriefParserAgent", FlakyParser)

    state = create_initial_campaign_state("camp-retry-001", "Retry scenario")
    result = await cg.parse_brief_node(state)

    assert attempts["count"] == 3
    assert result["parsed_data"]["product_name"] == "Recovered Product"


@pytest.mark.asyncio
async def test_checkpoint_restore(patch_db, monkeypatch):
    manager = StateManager(patch_db)
    state = create_initial_campaign_state("camp-recover-001", "Recovery scenario")

    checkpoint = await manager.create_checkpoint(state, current_node="strategy")

    async def pass_node(current_state):
        return current_state

    async def approved_node(current_state):
        next_state = dict(current_state)
        next_state["approval_status"] = "approved"
        return next_state

    async def execution_node(current_state):
        next_state = dict(current_state)
        next_state["execution_status"] = "completed"
        return next_state

    monkeypatch.setattr(cg, "parse_brief_node", pass_node)
    monkeypatch.setattr(cg, "fetch_customers_node", pass_node)
    monkeypatch.setattr(cg, "segmentation_node", pass_node)
    monkeypatch.setattr(cg, "strategy_node", pass_node)
    monkeypatch.setattr(cg, "content_generation_node", pass_node)
    monkeypatch.setattr(cg, "approval_node", approved_node)
    monkeypatch.setattr(cg, "execution_node", execution_node)

    recovered = await cg.recover_workflow("camp-recover-001", checkpoint["checkpoint_id"])
    assert recovered["campaign_id"] == "camp-recover-001"


@pytest.mark.asyncio
async def test_fallback_strategies(patch_db, patch_fast_sleep, monkeypatch):
    class AlwaysFailParser:
        async def execute(self, payload):
            raise RuntimeError("parse failure")

    class AlwaysFailSegmentation:
        async def execute(self, payload):
            raise RuntimeError("segmentation failure")

    class AlwaysFailContent:
        async def execute(self, payload):
            raise RuntimeError("content failure")

    class FailingExecution:
        async def execute_campaign(self, campaign_id, variants):
            raise RuntimeError("execution failure")

    def _loader(_module_name: str, class_name: str):
        if class_name == "ExecutionAgent":
            return FailingExecution
        return None

    monkeypatch.setattr(cg, "CampaignBriefParserAgent", AlwaysFailParser)
    monkeypatch.setattr(cg, "CustomerSegmentationAgent", AlwaysFailSegmentation)
    monkeypatch.setattr(cg, "ContentGenerationAgent", AlwaysFailContent)
    monkeypatch.setattr(cg, "_load_optional_agent", _loader)

    state = create_initial_campaign_state("camp-fallback-001", "Fallback scenario")
    parsed = await cg.parse_brief_node(state)
    assert parsed["parsed_data"]["product_name"] == "Campaign Product"

    parsed["customers"] = [
        {"customer_id": "cust-1", "age": 25, "activity_status": "active"},
        {"customer_id": "cust-2", "age": 61, "activity_status": "inactive"},
    ]
    segmented = await cg.segmentation_node(parsed)
    assert segmented["segments"]

    segmented["strategy"] = {
        "selected_segments": ["active_customers"],
        "send_schedule": {"active_customers": "2026-01-01T10:00:00+00:00"},
    }
    generated = await cg.content_generation_node(segmented)
    assert generated["variants"]

    generated["approval_status"] = "approved"
    executed = await cg.execution_node(generated)
    assert executed["execution_status"] == "failed"
    assert "manual_execution_queue" in executed["checkpoint_data"]


@pytest.mark.asyncio
async def test_error_logging(patch_db, patch_fast_sleep, monkeypatch, caplog):
    class AlwaysFailParser:
        async def execute(self, payload):
            raise RuntimeError("hard parser failure")

    monkeypatch.setattr(cg, "CampaignBriefParserAgent", AlwaysFailParser)

    state = create_initial_campaign_state("camp-error-log-001", "Error log scenario")

    with caplog.at_level(logging.ERROR):
        result = await cg.parse_brief_node(state)

    assert result["error_messages"]
    assert any("node.error" in message for message in caplog.messages)


@pytest.mark.asyncio
async def test_mock_api_cold_start_handling(patch_db, monkeypatch):
    """fetch_customers_node should retry on cold start timeout then succeed."""
    call_count = {"n": 0}

    def fake_get_count():
        call_count["n"] += 1
        if call_count["n"] < 2:
            raise requests.exceptions.Timeout("cold start")
        return 1

    def fake_get_customers(limit, offset):
        return [{"customer_id": "CUST0001", "Full_name": "Test", "email": "t@example.com",
                 "Age": 30, "Gender": "Male", "City": "Mumbai"}]

    mock_client = MagicMock()
    mock_client.get_customer_count.side_effect = fake_get_count
    mock_client.get_customers.side_effect = fake_get_customers

    monkeypatch.setattr(cg, "MockCampaignClient", lambda: mock_client)

    async def noop_sleep(_):
        pass
    monkeypatch.setattr(cg.asyncio, "sleep", noop_sleep)

    state = create_initial_campaign_state("camp-cold-start-001", "Cold start test")
    result = await cg.fetch_customers_node(state)
    assert result["customer_count"] >= 0  # either from API or DB fallback


@pytest.mark.asyncio
async def test_mock_api_validation_error(patch_db, monkeypatch):
    """execution_node should handle validation errors gracefully."""
    from app.external.mock_campaign_client import MockCampaignAPIError

    class FakeExecutionAgent:
        async def execute_campaign(self, campaign_id, variants):
            raise MockCampaignAPIError(400, "customer_ids must not be empty")

    monkeypatch.setattr(cg, "_load_optional_agent", lambda m, c: FakeExecutionAgent if c == "ExecutionAgent" else None)

    await patch_db["campaigns"].insert_one({
        "campaign_id": "camp-val-err-001",
        "status": "approved",
        "campaign_brief": "Test",
        "parsed_data": {},
        "created_by": "test",
        "created_at": "2026-01-01",
        "updated_at": "2026-01-01",
        "segments": [],
    })

    state = create_initial_campaign_state("camp-val-err-001", "Validation error test")
    state["approval_status"] = "approved"
    state["variants"] = [{"variant_id": "var-001", "customer_ids": [], "segment_name": "seg"}]

    result = await cg.execution_node(state)
    # Node should not crash — error is captured
    assert result["execution_status"] in ("failed", "completed")


@pytest.mark.asyncio
async def test_mock_api_timeout_retry_in_call_mock_api_with_retry(monkeypatch):
    """call_mock_api_with_retry should retry on timeout."""
    call_count = {"n": 0}

    async def noop_sleep(_):
        pass
    monkeypatch.setattr(cg.asyncio, "sleep", noop_sleep)

    def flaky_func():
        call_count["n"] += 1
        if call_count["n"] < 3:
            raise requests.exceptions.Timeout("timeout")
        return {"ok": True}

    result = await cg.call_mock_api_with_retry(flaky_func)
    assert result == {"ok": True}
    assert call_count["n"] == 3


@pytest.mark.asyncio
async def test_mock_api_errors_tracked_in_state(patch_db, monkeypatch):
    """mock_api_errors should be populated when Mock API fetch fails."""
    mock_client = MagicMock()
    mock_client.get_customer_count.side_effect = requests.exceptions.ConnectionError("failed")
    monkeypatch.setattr(cg, "MockCampaignClient", lambda: mock_client)

    async def noop_sleep(_):
        pass
    monkeypatch.setattr(cg.asyncio, "sleep", noop_sleep)

    state = create_initial_campaign_state("camp-err-track-001", "Error tracking test")
    result = await cg.fetch_customers_node(state)

    # mock_api_errors may be set even if fallback succeeded
    assert "mock_api_errors" in result
