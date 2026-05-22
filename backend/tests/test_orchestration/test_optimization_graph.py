"""Tests for optimization orchestration graph."""

from __future__ import annotations

from datetime import datetime

import pytest

from app.models.metrics import Metrics
from app.models.variant import CampaignVariant
from app.orchestration import optimization_graph as og
from app.orchestration.state import create_initial_optimization_state


@pytest.fixture
def patch_db(mock_db, monkeypatch):
    monkeypatch.setattr(og.MongoDB, "get_db", classmethod(lambda cls: mock_db))
    return mock_db


@pytest.fixture
def patch_content_agent(monkeypatch):
    class FakeContent:
        async def execute(self, payload):
            return {
                "variant_id": payload["variant_id"],
                "segment_name": "optimized_segment",
                "subject_lines": ["Improved variant subject"],
                "email_body": "<html><body><p>Improved variant body for optimization.</p></body></html>",
                "personalization_tags": ["[FIRST_NAME]"],
            }

    monkeypatch.setattr(og, "ContentGenerationAgent", FakeContent)


@pytest.mark.asyncio
async def test_metrics_collection_node(patch_db, monkeypatch):
    class FakeMonitoring:
        async def collect_metrics(self, campaign_id, mock_api_campaign_ids=None):
            return {
                "variant_metrics": [
                    {"variant_id": "v1", "open_rate": 20.0, "click_rate": 5.0},
                    {"variant_id": "v2", "open_rate": 10.0, "click_rate": 1.0},
                ]
            }

    monkeypatch.setattr(og, "_load_optional_agent", lambda *_args: FakeMonitoring)
    state = create_initial_optimization_state("camp-opt-001")

    result = await og.collect_metrics_node(state)
    assert "variant_metrics" in result["current_metrics"]


@pytest.mark.asyncio
async def test_poor_performer_identification(patch_db):
    state = create_initial_optimization_state("camp-opt-001")
    state["current_metrics"] = {
        "variant_metrics": [
            {"variant_id": "v1", "open_rate": 30.0, "click_rate": 7.0},
            {"variant_id": "v2", "open_rate": 10.0, "click_rate": 1.0},
            {"variant_id": "v3", "open_rate": 25.0, "click_rate": 5.0},
            {"variant_id": "v4", "open_rate": 15.0, "click_rate": 2.0},
        ]
    }

    result = await og.identify_poor_performers_node(state)
    assert result["poor_performers"] == ["v2"]


@pytest.mark.asyncio
async def test_optimization_node(patch_db, monkeypatch):
    class FakeOptimization:
        async def optimize_campaign(self, campaign_id, metrics):
            return [
                {"variant_id": "v2", "changes": ["Use stronger CTA"]},
            ]

    monkeypatch.setattr(og, "_load_optional_agent", lambda *_args: FakeOptimization)

    state = create_initial_optimization_state("camp-opt-001")
    state["current_metrics"] = {
        "variant_metrics": [{"variant_id": "v2", "open_rate": 10.0, "click_rate": 1.0}]
    }
    state["poor_performers"] = ["v2"]

    result = await og.optimization_node(state)
    assert len(result["optimization_recommendations"]) == 1


@pytest.mark.asyncio
async def test_variant_regeneration(patch_db, patch_content_agent, monkeypatch):
    monkeypatch.setattr(og, "_load_optional_agent", lambda *_args: None)

    await patch_db["campaign_variants"].insert_one(
        CampaignVariant(
            variant_id="v-poor-1",
            campaign_id="camp-opt-001",
            segment_name="segment_a",
            subject_line="Old subject",
            email_body="A" * 60,
        ).model_dump()
    )

    state = create_initial_optimization_state("camp-opt-001")
    state["poor_performers"] = ["v-poor-1"]
    state["optimization_recommendations"] = [{"variant_id": "v-poor-1", "changes": ["Improve CTA"]}]

    result = await og.regenerate_variants_node(state)
    assert len(result["new_variants"]) == 1


@pytest.mark.asyncio
async def test_convergence_check():
    state = create_initial_optimization_state("camp-opt-001")
    state["iteration_count"] = 3
    assert og.check_convergence(state) == "end"

    state = create_initial_optimization_state("camp-opt-001")
    state["current_metrics"] = {
        "variant_metrics": [
            {"variant_id": "v1", "open_rate": 40.0, "click_rate": 20.0},
            {"variant_id": "v2", "open_rate": 35.0, "click_rate": 18.0},
        ]
    }
    assert og.check_convergence(state) == "end"


@pytest.mark.asyncio
async def test_feedback_loop(patch_db, patch_content_agent, monkeypatch):
    monkeypatch.setattr(og, "_load_optional_agent", lambda *_args: None)

    await patch_db["campaigns"].insert_one(
        {
            "campaign_id": "camp-loop-001",
            "campaign_brief": "Loop test",
            "status": "optimizing",
            "parsed_data": {},
            "segments": [],
            "created_by": "tester",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
    )

    metrics = [
        Metrics(variant_id="v1", campaign_id="camp-loop-001", mock_campaign_id="mock-v1", open_rate=0.08, click_rate=0.010),
        Metrics(variant_id="v2", campaign_id="camp-loop-001", mock_campaign_id="mock-v2", open_rate=0.09, click_rate=0.011),
        Metrics(variant_id="v3", campaign_id="camp-loop-001", mock_campaign_id="mock-v3", open_rate=0.10, click_rate=0.012),
        Metrics(variant_id="v4", campaign_id="camp-loop-001", mock_campaign_id="mock-v4", open_rate=0.11, click_rate=0.010),
    ]
    for metric in metrics:
        await patch_db["metrics"].insert_one(metric.model_dump())

    for variant_id in ["v1", "v2", "v3", "v4"]:
        await patch_db["campaign_variants"].insert_one(
            CampaignVariant(
                variant_id=variant_id,
                campaign_id="camp-loop-001",
                segment_name="segment_a",
                subject_line="Subject",
                email_body="A" * 60,
            ).model_dump()
        )

    result = await og.run_optimization_workflow("camp-loop-001")
    assert result["iteration_count"] >= 1
    assert result["convergence_achieved"] is True


@pytest.mark.asyncio
async def test_optimization_workflow_end_to_end(patch_db, patch_content_agent, monkeypatch):
    monkeypatch.setattr(og, "_load_optional_agent", lambda *_args: None)

    await patch_db["campaigns"].insert_one(
        {
            "campaign_id": "camp-opt-e2e-001",
            "campaign_brief": "Optimization E2E",
            "status": "optimizing",
            "parsed_data": {},
            "segments": [],
            "created_by": "tester",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
    )

    for idx in range(1, 5):
        await patch_db["metrics"].insert_one(
            Metrics(
                variant_id=f"ve2e-{idx}",
                campaign_id="camp-opt-e2e-001",
                mock_campaign_id=f"mock-ve2e-{idx}",
                open_rate=(10.0 + idx) / 100,
                click_rate=(1.0 + idx * 0.3) / 100,
            ).model_dump()
        )
        await patch_db["campaign_variants"].insert_one(
            CampaignVariant(
                variant_id=f"ve2e-{idx}",
                campaign_id="camp-opt-e2e-001",
                segment_name="segment_a",
                subject_line="Subject",
                email_body="A" * 60,
            ).model_dump()
        )

    result = await og.run_optimization_workflow("camp-opt-e2e-001")
    assert result["campaign_id"] == "camp-opt-e2e-001"
    assert "optimization_recommendations" in result


@pytest.mark.asyncio
async def test_metrics_collection_from_mock_api(patch_db, monkeypatch):
    """collect_metrics_node should use mock_api_campaign_ids when available."""
    mock_metrics = {
        "variant_metrics": [
            {"variant_id": "v1", "open_rate": 60.0, "click_rate": 20.0, "mock_campaign_id": "mock-001"},
        ],
        "aggregates": {"avg_open_rate": 60.0},
        "customer_results": [{"customer_id": "CUST0001", "opened": True, "clicked": False}],
    }

    class FakeMonitoring:
        async def collect_metrics(self, campaign_id, mock_api_campaign_ids=None):
            return mock_metrics

    monkeypatch.setattr(og, "_load_optional_agent", lambda *_: FakeMonitoring)

    state = create_initial_optimization_state("camp-mock-metrics-001")
    state["mock_api_campaign_ids"] = {"v1": "mock-001"}

    result = await og.collect_metrics_node(state)
    assert result["current_metrics"]["variant_metrics"][0]["open_rate"] == 60.0
    assert result["customer_results"][0]["customer_id"] == "CUST0001"


@pytest.mark.asyncio
async def test_poor_performer_identification_with_performance_scores(patch_db):
    """identify_poor_performers_node should populate performance_scores."""
    state = create_initial_optimization_state("camp-perf-scores-001")
    state["current_metrics"] = {
        "variant_metrics": [
            {"variant_id": "v1", "open_rate": 50.0, "click_rate": 15.0},
            {"variant_id": "v2", "open_rate": 10.0, "click_rate": 2.0},
        ]
    }

    result = await og.identify_poor_performers_node(state)
    assert "performance_scores" in result
    assert "v1" in result["performance_scores"]
    assert "v2" in result["performance_scores"]
    # v1 score = 0.7*15 + 0.3*50 = 10.5 + 15 = 25.5
    # v2 score = 0.7*2 + 0.3*10 = 1.4 + 3 = 4.4
    assert result["performance_scores"]["v1"] > result["performance_scores"]["v2"]
    assert "v2" in result["poor_performers"]


@pytest.mark.asyncio
async def test_optimization_workflow_with_mock_api_ids(patch_db, patch_content_agent, monkeypatch):
    """run_optimization_workflow should accept and pass mock_api_campaign_ids."""
    monkeypatch.setattr(og, "_load_optional_agent", lambda *_args: None)

    await patch_db["campaigns"].insert_one({
        "campaign_id": "camp-with-ids-001",
        "campaign_brief": "Test with Mock API IDs",
        "status": "optimizing",
        "parsed_data": {},
        "segments": [],
        "created_by": "tester",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    })

    for idx in range(1, 3):
        await patch_db["campaign_variants"].insert_one(
            CampaignVariant(
                variant_id=f"v-ids-{idx}",
                campaign_id="camp-with-ids-001",
                segment_name="seg",
                subject_line="Subject",
                email_body="A" * 60,
            ).model_dump()
        )

    result = await og.run_optimization_workflow(
        "camp-with-ids-001",
        mock_api_campaign_ids={"v-ids-1": "mock-uuid-001", "v-ids-2": "mock-uuid-002"},
    )
    assert result["campaign_id"] == "camp-with-ids-001"
    assert result["convergence_achieved"] is True


@pytest.mark.asyncio
async def test_customer_results_in_optimization_state(patch_db, monkeypatch):
    """customer_results should be surfaced in OptimizationState after collect_metrics."""
    customer_results = [
        {"customer_id": "CUST0001", "opened": True, "clicked": False, "variant_id": "v1"},
        {"customer_id": "CUST0002", "opened": False, "clicked": False, "variant_id": "v1"},
    ]

    class FakeMonitoring:
        async def collect_metrics(self, campaign_id, mock_api_campaign_ids=None):
            return {
                "variant_metrics": [{"variant_id": "v1", "open_rate": 50.0, "click_rate": 10.0}],
                "aggregates": {},
                "customer_results": customer_results,
            }

    monkeypatch.setattr(og, "_load_optional_agent", lambda *_: FakeMonitoring)

    state = create_initial_optimization_state("camp-cust-results-001")
    result = await og.collect_metrics_node(state)

    assert len(result["customer_results"]) == 2
    assert result["customer_results"][0]["opened"] is True
