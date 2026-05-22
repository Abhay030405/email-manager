"""Tests for orchestration state management."""

from __future__ import annotations

import pytest

from app.orchestration.state import StateManager, create_initial_campaign_state, create_initial_optimization_state


@pytest.mark.asyncio
async def test_state_validation(mock_db):
    manager = StateManager(mock_db)
    valid_state = create_initial_campaign_state("camp-state-100", "A valid brief")
    assert manager.validate_state(valid_state) is True

    invalid_state = dict(valid_state)
    invalid_state["campaign_id"] = ""
    assert manager.validate_state(invalid_state) is False


@pytest.mark.asyncio
async def test_state_save_load(mock_db):
    manager = StateManager(mock_db)
    state = create_initial_campaign_state("camp-state-101", "Save and load this state")
    state["parsed_data"] = {"campaign_goal": "awareness"}

    await manager.save_state(state, state["campaign_id"])
    loaded = await manager.load_state(state["campaign_id"])

    assert loaded["campaign_id"] == "camp-state-101"
    assert loaded["parsed_data"]["campaign_goal"] == "awareness"


@pytest.mark.asyncio
async def test_checkpoint_creation(mock_db):
    manager = StateManager(mock_db)
    state = create_initial_campaign_state("camp-state-102", "Checkpoint test")

    checkpoint = await manager.create_checkpoint(state, current_node="segmentation")

    assert checkpoint["campaign_id"] == "camp-state-102"
    assert checkpoint["current_node"] == "segmentation"
    assert "checkpoint_id" in checkpoint


@pytest.mark.asyncio
async def test_checkpoint_recovery(mock_db):
    manager = StateManager(mock_db)
    state = create_initial_campaign_state("camp-state-103", "Recovery test")
    state["strategy"] = {"selected_segments": ["segment_a"]}

    checkpoint = await manager.create_checkpoint(state, current_node="strategy")
    restored = await manager.restore_from_checkpoint(checkpoint["checkpoint_id"])

    assert restored["campaign_id"] == "camp-state-103"
    assert restored["strategy"]["selected_segments"] == ["segment_a"]


@pytest.mark.asyncio
async def test_state_includes_mock_api_fields(mock_db):
    """New Mock API fields should be present in initial campaign state."""
    state = create_initial_campaign_state("camp-state-104", "Mock API fields test")
    assert "mock_api_campaign_ids" in state
    assert "customer_count" in state
    assert "customer_results" in state
    assert "mock_api_errors" in state
    assert state["mock_api_campaign_ids"] == {}
    assert state["customer_count"] == 0


@pytest.mark.asyncio
async def test_mock_api_mapping_persistence(mock_db):
    """save_mock_api_mapping should upsert to api_mappings collection."""
    manager = StateManager(mock_db)
    await manager.save_mock_api_mapping("camp-state-105", "var-001", "mock-uuid-001")

    doc = await mock_db["api_mappings"].find_one({
        "campaign_id": "camp-state-105",
        "variant_id": "var-001",
    })
    assert doc is not None
    assert doc["mock_campaign_id"] == "mock-uuid-001"

    # Upsert — second call should update, not duplicate
    await manager.save_mock_api_mapping("camp-state-105", "var-001", "mock-uuid-002")
    count = await mock_db["api_mappings"].count_documents({
        "campaign_id": "camp-state-105",
        "variant_id": "var-001",
    })
    assert count == 1
    updated = await mock_db["api_mappings"].find_one({"campaign_id": "camp-state-105", "variant_id": "var-001"})
    assert updated["mock_campaign_id"] == "mock-uuid-002"


@pytest.mark.asyncio
async def test_state_save_load_with_mock_api_fields(mock_db):
    """State with mock_api_campaign_ids should round-trip correctly."""
    manager = StateManager(mock_db)
    state = create_initial_campaign_state("camp-state-106", "Mock API mapping test")
    state["mock_api_campaign_ids"] = {"var-001": "mock-uuid-001", "var-002": "mock-uuid-002"}
    state["customer_count"] = 100

    await manager.save_state(state, state["campaign_id"])
    loaded = await manager.load_state(state["campaign_id"])

    assert loaded["mock_api_campaign_ids"]["var-001"] == "mock-uuid-001"
    assert loaded["customer_count"] == 100


@pytest.mark.asyncio
async def test_optimization_state_includes_mock_api_fields():
    """OptimizationState should have performance_scores and mock_api_campaign_ids."""
    state = create_initial_optimization_state("camp-opt-state-001")
    assert "performance_scores" in state
    assert "mock_api_campaign_ids" in state
    assert "customer_results" in state
    assert state["performance_scores"] == {}
    assert state["mock_api_campaign_ids"] == {}
