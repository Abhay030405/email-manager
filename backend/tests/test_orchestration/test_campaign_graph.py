"""Tests for campaign orchestration graph."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.orchestration import campaign_graph as cg
from app.orchestration.state import StateManager, create_initial_campaign_state


@pytest.fixture
def base_state() -> dict:
    return create_initial_campaign_state("camp-orch-001", "Launch a spring campaign")


@pytest.fixture
def patch_db(mock_db, monkeypatch):
    monkeypatch.setattr(cg.MongoDB, "get_db", classmethod(lambda cls: mock_db))
    return mock_db


@pytest.fixture
def patch_campaign_agents(monkeypatch):
    class FakeParser:
        async def execute(self, payload):
            assert "brief_text" in payload
            return {
                "product_name": "CampaignX Pro",
                "product_description": "Automation platform",
                "target_audience": "SMB marketers",
                "campaign_goal": "conversion",
                "cta_link": "https://example.com",
                "budget": 5000.0,
                "preferred_tone": "professional",
                "key_messages": ["Speed", "Personalization", "Scale"],
                "constraints": None,
            }

    class FakeSegmentation:
        async def execute(self, payload):
            customers = payload["customers"]
            first_half = [c["customer_id"] for c in customers[: max(1, len(customers) // 2)]]
            second_half = [c["customer_id"] for c in customers[max(1, len(customers) // 2) :]]
            return {
                "segments": [
                    {
                        "segment_name": "active_segment",
                        "description": "High intent users",
                        "customer_ids": first_half,
                        "size": len(first_half),
                        "targeting_priority": 5,
                        "recommended_approach": "Use direct CTA",
                    },
                    {
                        "segment_name": "nurture_segment",
                        "description": "Needs warmup",
                        "customer_ids": second_half,
                        "size": len(second_half),
                        "targeting_priority": 3,
                        "recommended_approach": "Use educational copy",
                    },
                ]
            }

    class FakeStrategy:
        async def execute(self, payload):
            return {
                "selected_segments": ["active_segment", "nurture_segment"],
                "send_schedule": {
                    "active_segment": datetime.now(tz=timezone.utc).isoformat(),
                    "nurture_segment": datetime.now(tz=timezone.utc).isoformat(),
                },
                "ab_test_plan": {
                    "num_variants": 2,
                    "variant_distribution": {"variant_A": 50.0, "variant_B": 50.0},
                    "test_dimension": "subject_line",
                },
                "budget_allocation": {"active_segment": 70.0, "nurture_segment": 30.0},
                "expected_metrics": {"active_segment": 0.25, "nurture_segment": 0.18},
                "reasoning": {
                    "active_segment": "Closer to purchase",
                    "nurture_segment": "Needs nurturing",
                },
            }

    class FakeContent:
        async def execute(self, payload):
            return {
                "variant_id": payload["variant_id"],
                "segment_name": payload["segment"]["segment_name"],
                "subject_lines": ["Ready to grow your campaigns?"],
                "email_body": "<html><body><p>Hi [FIRST_NAME],</p><p>Campaign update.</p></body></html>",
                "preview_text": "Campaign update for your segment",
                "personalization_tags": ["[FIRST_NAME]"],
                "tone": "professional",
                "estimated_read_time": "1 min",
            }

    class FakeApproval:
        async def check_approval_status(self, campaign_id):
            return {"approval_status": "approved"}

    class FakeExecution:
        async def execute_campaign(self, campaign_id, variants):
            return {
                "execution_status": "completed",
                "metrics": {"emails_scheduled": len(variants)},
            }

    def _loader(_module_name: str, class_name: str):
        mapping = {
            "ApprovalAgent": FakeApproval,
            "ExecutionAgent": FakeExecution,
        }
        return mapping.get(class_name)

    monkeypatch.setattr(cg, "CampaignBriefParserAgent", FakeParser)
    monkeypatch.setattr(cg, "CustomerSegmentationAgent", FakeSegmentation)
    monkeypatch.setattr(cg, "CampaignStrategyAgent", FakeStrategy)
    monkeypatch.setattr(cg, "ContentGenerationAgent", FakeContent)
    monkeypatch.setattr(cg, "_load_optional_agent", _loader)


@pytest.mark.asyncio
async def test_parse_brief_node(base_state, patch_db, patch_campaign_agents):
    result = await cg.parse_brief_node(base_state)
    assert result["parsed_data"]["product_name"] == "CampaignX Pro"


@pytest.mark.asyncio
async def test_segmentation_node(base_state, patch_db, patch_campaign_agents, sample_customers):
    state = dict(base_state)
    state["customers"] = [customer.model_dump() for customer in sample_customers]
    state["parsed_data"] = {
        "target_audience": "SMB marketers",
        "campaign_goal": "conversion",
    }

    result = await cg.segmentation_node(state)
    assert "active_segment" in result["segments"]
    assert "nurture_segment" in result["segments"]


@pytest.mark.asyncio
async def test_strategy_node(base_state, patch_db, patch_campaign_agents):
    state = dict(base_state)
    state["parsed_data"] = {
        "product_name": "CampaignX Pro",
        "product_description": "Automation platform",
        "target_audience": "SMB marketers",
        "campaign_goal": "conversion",
        "cta_link": "https://example.com",
        "budget": 5000.0,
        "preferred_tone": "professional",
        "key_messages": ["Scale"],
        "constraints": None,
    }
    state["segments"] = {"active_segment": ["cust-001"]}
    state["checkpoint_data"] = {
        "segments_detail": [
            {
                "segment_name": "active_segment",
                "description": "High intent users",
                "customer_ids": ["cust-001"],
                "size": 1,
                "targeting_priority": 5,
                "recommended_approach": "Use direct CTA",
            }
        ]
    }

    result = await cg.strategy_node(state)
    assert "selected_segments" in result["strategy"]


@pytest.mark.asyncio
async def test_content_generation_node(base_state, patch_db, patch_campaign_agents):
    state = dict(base_state)
    state["parsed_data"] = {
        "product_name": "CampaignX Pro",
        "product_description": "Automation platform",
        "target_audience": "SMB marketers",
        "campaign_goal": "conversion",
        "cta_link": "https://example.com",
        "budget": 5000.0,
        "preferred_tone": "professional",
        "key_messages": ["Scale"],
        "constraints": None,
    }
    state["segments"] = {"active_segment": ["cust-001"]}
    state["strategy"] = {
        "selected_segments": ["active_segment"],
        "send_schedule": {"active_segment": datetime.now(tz=timezone.utc).isoformat()},
    }
    state["checkpoint_data"] = {
        "segments_detail": [
            {
                "segment_name": "active_segment",
                "description": "High intent users",
                "customer_ids": ["cust-001"],
                "size": 1,
                "targeting_priority": 5,
                "recommended_approach": "Use direct CTA",
            }
        ]
    }

    result = await cg.content_generation_node(state)
    assert len(result["variants"]) == 1


@pytest.mark.asyncio
async def test_approval_routing(base_state):
    approved = dict(base_state)
    approved["approval_status"] = "approved"
    rejected = dict(base_state)
    rejected["approval_status"] = "rejected"
    pending = dict(base_state)
    pending["approval_status"] = "pending"

    assert cg.should_execute(approved) == "execute"
    assert cg.should_execute(rejected) == "end"
    assert cg.should_execute(pending) == "wait"


@pytest.mark.asyncio
async def test_full_workflow_execution(
    patch_db,
    patch_campaign_agents,
    sample_customers,
):
    for customer in sample_customers:
        await patch_db["customers"].insert_one(customer.model_dump())

    result = await cg.run_campaign_workflow("camp-workflow-001", "Launch seasonal promo")
    assert result["approval_status"] == "approved"
    assert result["execution_status"] == "completed"
    assert len(result["variants"]) >= 1


@pytest.mark.asyncio
async def test_workflow_with_rejection(patch_db, patch_campaign_agents, monkeypatch, sample_customers):
    class RejectionApproval:
        async def check_approval_status(self, campaign_id):
            return {"approval_status": "rejected"}

    def _loader(_module_name: str, class_name: str):
        if class_name == "ApprovalAgent":
            return RejectionApproval
        return None

    monkeypatch.setattr(cg, "_load_optional_agent", _loader)

    for customer in sample_customers:
        await patch_db["customers"].insert_one(customer.model_dump())

    result = await cg.run_campaign_workflow("camp-reject-001", "Launch seasonal promo")
    assert result["approval_status"] == "rejected"
    assert result["execution_status"] == "not_started"


@pytest.mark.asyncio
async def test_state_persistence(patch_db, patch_campaign_agents, sample_customers):
    for customer in sample_customers:
        await patch_db["customers"].insert_one(customer.model_dump())

    campaign_id = "camp-state-001"
    await cg.run_campaign_workflow(campaign_id, "Launch retention campaign")

    state_manager = StateManager(patch_db)
    persisted = await state_manager.load_state(campaign_id)
    assert persisted["campaign_id"] == campaign_id
    assert persisted["parsed_data"]
