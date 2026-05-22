"""Optimization feedback-loop workflow powered by LangGraph."""

from __future__ import annotations

import asyncio
import importlib
import logging
from datetime import datetime, timezone
from math import ceil
from typing import Any, Awaitable, Callable

from bson import ObjectId
from bson.errors import InvalidId
from app.db.mongodb import MongoDB
from app.db.repositories.campaign_repo import CampaignRepository
from app.db.repositories.metrics_repo import MetricsRepository
from app.db.repositories.variant_repo import VariantRepository
from app.external.mock_campaign_client import MockCampaignClient, MockCampaignAPIError
from app.models.variant import CampaignVariant, VariantStatus
from app.orchestration.state import (
	OptimizationState,
	OptimizationStateModel,
	StateManager,
	create_initial_optimization_state,
)

try:
	from langgraph.graph import END, START, StateGraph
except ImportError:  # pragma: no cover - compatibility fallback
	from langgraph.graph import StateGraph

	START = "__start__"
	END = "__end__"

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
PERFORMANCE_THRESHOLD = 12.0

CampaignStrategyAgent: Any | None = None
ContentGenerationAgent: Any | None = None


def _load_optional_agent(module_name: str, class_name: str) -> Any | None:
	try:
		module = importlib.import_module(module_name)
		return getattr(module, class_name)
	except Exception:
		return None


def _resolve_agent_class(current: Any | None, module_name: str, class_name: str) -> Any:
	if current is not None:
		return current
	module = importlib.import_module(module_name)
	return getattr(module, class_name)


def _append_error(state: OptimizationState, message: str) -> OptimizationState:
	next_state = OptimizationState(**dict(state))
	errors = list(next_state.get("error_messages", []))
	errors.append(message)
	next_state["error_messages"] = errors
	return next_state


async def _save_optimization_state(state: OptimizationState) -> None:
	db = MongoDB.get_db()
	await db["workflow_states"].update_one(
		{"campaign_id": state["campaign_id"], "workflow_type": "optimization"},
		{
			"$set": {
				"campaign_id": state["campaign_id"],
				"workflow_type": "optimization",
				"state": dict(state),
				"updated_at": datetime.now(tz=timezone.utc),
			}
		},
		upsert=True,
	)


async def _create_checkpoint(state: OptimizationState, current_node: str) -> None:
	db = MongoDB.get_db()
	await db["workflow_checkpoints"].insert_one(
		{
			"campaign_id": state["campaign_id"],
			"workflow_type": "optimization",
			"current_node": current_node,
			"timestamp": datetime.now(tz=timezone.utc),
			"state_snapshot": dict(state),
		}
	)


async def _execute_node_with_retries(
	node_name: str,
	state: OptimizationState,
	operation: Callable[[OptimizationState], Awaitable[OptimizationState]],
	fallback: Callable[[OptimizationState], OptimizationState] | None = None,
) -> OptimizationState:
	logger.info("node.enter", extra={"node": node_name, "campaign_id": state.get("campaign_id")})
	last_error: Exception | None = None

	for attempt in range(1, MAX_RETRIES + 1):
		try:
			await _create_checkpoint(state, node_name)
			next_state = await operation(OptimizationState(**dict(state)))
			OptimizationStateModel.model_validate(next_state)
			await _save_optimization_state(next_state)
			logger.info(
				"node.exit",
				extra={
					"node": node_name,
					"campaign_id": next_state.get("campaign_id"),
					"attempt": attempt,
					"timestamp": datetime.now(tz=timezone.utc).isoformat(),
				},
			)
			return next_state
		except Exception as exc:  # pragma: no cover - error-path tested via monkeypatch
			last_error = exc
			logger.exception(
				"node.error",
				extra={
					"node": node_name,
					"campaign_id": state.get("campaign_id"),
					"attempt": attempt,
					"error": str(exc),
				},
			)
			if attempt < MAX_RETRIES:
				await asyncio.sleep(2 ** (attempt - 1))

	failed_state = _append_error(
		state,
		f"{node_name} failed after {MAX_RETRIES} retries: {last_error}",
	)
	if fallback is not None:
		failed_state = fallback(failed_state)
	await _save_optimization_state(failed_state)
	return failed_state


async def collect_metrics_node(state: OptimizationState) -> OptimizationState:
	"""Collect campaign performance metrics from Mock API or MongoDB."""

	async def _op(current_state: OptimizationState) -> OptimizationState:
		campaign_id = current_state["campaign_id"]
		mock_api_campaign_ids: dict[str, str] = dict(current_state.get("mock_api_campaign_ids", {}))
		monitoring_cls = _load_optional_agent("app.agents.monitoring", "MonitoringAgent")

		if monitoring_cls is not None:
			agent = monitoring_cls()
			if hasattr(agent, "collect_metrics"):
				response = agent.collect_metrics(campaign_id, mock_api_campaign_ids or None)
				metrics = await response if asyncio.iscoroutine(response) else response
			elif hasattr(agent, "execute"):
				response = agent.execute({
					"campaign_id": campaign_id,
					"mock_api_campaign_ids": mock_api_campaign_ids,
				})
				metrics = await response if asyncio.iscoroutine(response) else response
			else:
				raise AttributeError("MonitoringAgent missing collect_metrics/execute")
		else:
			repo = MetricsRepository(MongoDB.get_db())
			metric_docs = await repo.find_by_campaign(campaign_id)
			metrics = {
				"variant_metrics": [doc.model_dump() for doc in metric_docs],
				"aggregates": await repo.calculate_campaign_aggregates(campaign_id),
				"customer_results": [],
			}

		if not isinstance(metrics, dict):
			raise ValueError("Collected metrics must be a dictionary")

		next_state = OptimizationState(**dict(current_state))
		next_state["current_metrics"] = metrics
		# Surface per-customer results into top-level state field
		customer_results = metrics.get("customer_results", [])
		next_state["customer_results"] = customer_results
		return next_state

	return await _execute_node_with_retries("collect_metrics", state, _op)


async def identify_poor_performers_node(state: OptimizationState) -> OptimizationState:
	"""Identify bottom 25% performing variants using weighted score."""

	async def _op(current_state: OptimizationState) -> OptimizationState:
		variant_metrics = current_state.get("current_metrics", {}).get("variant_metrics", [])
		scored: list[tuple[str, float]] = []
		for metric in variant_metrics:
			variant_id = metric.get("variant_id")
			if not variant_id:
				continue
			click_rate = float(metric.get("click_rate", 0.0) or 0.0)
			open_rate = float(metric.get("open_rate", 0.0) or 0.0)
			score = 0.7 * click_rate + 0.3 * open_rate
			scored.append((variant_id, score))

		scored.sort(key=lambda item: item[1])
		bottom_n = ceil(len(scored) * 0.25) if scored else 0
		poor_performers = [variant_id for variant_id, _ in scored[:bottom_n]]
		performance_scores = {variant_id: score for variant_id, score in scored}

		next_state = OptimizationState(**dict(current_state))
		next_state["poor_performers"] = poor_performers
		next_state["performance_scores"] = performance_scores
		return next_state

	return await _execute_node_with_retries("identify_poor_performers", state, _op)


async def optimization_node(state: OptimizationState) -> OptimizationState:
	"""Generate optimization recommendations."""

	async def _op(current_state: OptimizationState) -> OptimizationState:
		campaign_id = current_state["campaign_id"]
		optimization_cls = _load_optional_agent("app.agents.optimization", "OptimizationAgent")

		if optimization_cls is not None:
			agent = optimization_cls()
			if hasattr(agent, "optimize_campaign"):
				response = agent.optimize_campaign(campaign_id, current_state["current_metrics"])
				recommendations = await response if asyncio.iscoroutine(response) else response
			elif hasattr(agent, "execute"):
				response = agent.execute(
					{
						"campaign_id": campaign_id,
						"metrics": current_state["current_metrics"],
					}
				)
				recommendations = await response if asyncio.iscoroutine(response) else response
			else:
				raise AttributeError("OptimizationAgent missing optimize_campaign/execute")
		else:
			recommendations = [
				{
					"variant_id": variant_id,
					"changes": [
						"Improve subject-line specificity",
						"Increase CTA clarity",
						"Adjust send time to high-engagement hour",
					],
				}
				for variant_id in current_state.get("poor_performers", [])
			]

		if isinstance(recommendations, dict):
			recommendations = recommendations.get("optimization_recommendations", [])
		if not isinstance(recommendations, list):
			raise ValueError("Optimization recommendations must be a list")

		next_state = OptimizationState(**dict(current_state))
		next_state["optimization_recommendations"] = recommendations
		return next_state

	return await _execute_node_with_retries("optimization", state, _op)


def _fallback_regenerate(state: OptimizationState) -> OptimizationState:
	next_state = OptimizationState(**dict(state))
	next_state["new_variants"] = [
		{
			"variant_id": f"regen_{variant_id}",
			"subject_line": "Improved message for higher CTR",
			"email_body": "<html><body><p>Hi [FIRST_NAME], improved creative.</p></body></html>",
			"segment_name": "optimized_segment",
			"variant_type": "optimized",
			"status": VariantStatus.DRAFT.value,
			"send_time": datetime.now(tz=timezone.utc).isoformat(),
		}
		for variant_id in state.get("poor_performers", [])
	]
	return next_state


async def regenerate_variants_node(state: OptimizationState) -> OptimizationState:
	"""Create improved variants and replace poor performers in DB."""

	async def _op(current_state: OptimizationState) -> OptimizationState:
		content_cls = _resolve_agent_class(
			ContentGenerationAgent,
			"app.agents.content_gen",
			"ContentGenerationAgent",
		)
		content_agent = content_cls()
		campaign_id = current_state["campaign_id"]
		poor_performers = current_state.get("poor_performers", [])
		recommendations = current_state.get("optimization_recommendations", [])

		repo = VariantRepository(MongoDB.get_db())
		await repo.update_status_bulk(poor_performers, VariantStatus.CANCELLED)

		new_variants: list[dict[str, Any]] = []
		for idx, variant_id in enumerate(poor_performers, start=1):
			rec = recommendations[idx - 1] if idx - 1 < len(recommendations) else {}

			if hasattr(content_agent, "generate_content"):
				response = content_agent.generate_content(
					{"optimization": rec},
					{"segment": "optimized_segment", "variant": variant_id},
				)
				generated = await response if asyncio.iscoroutine(response) else response
				if isinstance(generated, list) and generated:
					generated = generated[0]
			else:
				response = content_agent.execute(
					{
						"parsed_brief": {
							"product_name": "Campaign Product",
							"product_description": "Optimized variant generation",
							"target_audience": "General audience",
							"campaign_goal": "conversion",
							"cta_link": "",
							"budget": None,
							"preferred_tone": "professional",
							"key_messages": ["Improved value proposition"],
							"constraints": None,
						},
						"segment": {
							"segment_name": "optimized_segment",
							"description": "Optimization-generated segment",
							"customer_ids": [],
							"size": 0,
							"targeting_priority": 3,
							"recommended_approach": "Emphasize CTR improvements.",
						},
						"variant_id": f"regen_{variant_id}",
						"strategy": {
							"selected_segments": ["optimized_segment"],
							"send_schedule": {
								"optimized_segment": datetime.now(tz=timezone.utc).isoformat()
							},
							"ab_test_plan": {
								"num_variants": 2,
								"variant_distribution": {"variant_A": 50.0, "variant_B": 50.0},
								"test_dimension": "subject_line",
							},
							"budget_allocation": {"optimized_segment": 100.0},
							"expected_metrics": {"optimized_segment": 0.2},
							"reasoning": {"optimized_segment": "Optimization refresh"},
						},
					}
				)
				generated = await response if asyncio.iscoroutine(response) else response

			if not isinstance(generated, dict):
				raise ValueError("Regenerated content must be a dictionary")

			model = CampaignVariant(
				variant_id=generated.get("variant_id", f"regen_{variant_id}"),
				campaign_id=campaign_id,
				segment_name=generated.get("segment_name", "optimized_segment"),
				subject_line=(generated.get("subject_lines") or ["Improved campaign variant"])[0],
				email_body=generated.get("email_body", "A" * 60),
				variant_type="optimized",
				status=VariantStatus.DRAFT,
			)
			await repo.create(model)
			new_variants.append(model.model_dump())

		next_state = OptimizationState(**dict(current_state))
		next_state["new_variants"] = new_variants
		return next_state

	return await _execute_node_with_retries(
		"regenerate_variants",
		state,
		_op,
		fallback=_fallback_regenerate,
	)


async def update_strategy_node(state: OptimizationState) -> OptimizationState:
	"""Update campaign strategy and optionally re-schedule new variants via Mock API."""

	async def _op(current_state: OptimizationState) -> OptimizationState:
		campaign_repo = CampaignRepository(MongoDB.get_db())
		mock_api_campaign_ids: dict[str, str] = dict(current_state.get("mock_api_campaign_ids", {}))

		refinement_notes = {
			"poor_performers": current_state.get("poor_performers", []),
			"recommendations": current_state.get("optimization_recommendations", []),
			"performance_scores": current_state.get("performance_scores", {}),
		}

		try:
			strategy_cls = _resolve_agent_class(
				CampaignStrategyAgent,
				"app.agents.strategy",
				"CampaignStrategyAgent",
			)
			strategy_agent = strategy_cls()
			if hasattr(strategy_agent, "refine_strategy"):
				response = strategy_agent.refine_strategy(refinement_notes)
				refined = await response if asyncio.iscoroutine(response) else response
			else:
				refined = {"optimization_learnings": refinement_notes}
		except Exception:
			refined = {"optimization_learnings": refinement_notes}

		# Attempt to schedule new variants via Mock API and capture their IDs
		new_variants: list[dict[str, Any]] = current_state.get("new_variants", [])
		if new_variants:
			try:
				client = MockCampaignClient()
				db = MongoDB.get_db()
				state_manager = StateManager(db)
				for variant in new_variants:
					variant_id = variant.get("variant_id", "")
					customer_ids: list[str] = variant.get("customer_ids", [])
					if not customer_ids:
						continue
					try:
						scheduled = await asyncio.get_event_loop().run_in_executor(
							None,
							lambda vid=variant_id, v=variant, cids=customer_ids: client.schedule_campaign(
								customer_ids=cids,
								subject=v.get("subject_line", v.get("subject", "")),
								body=v.get("email_body", v.get("body", "")),
								scheduled_time=v.get("send_time", datetime.now(tz=timezone.utc).isoformat()),
								segment_name=v.get("segment_name", "optimized"),
								variant_id=vid,
								campaign_metadata={"internal_campaign_id": current_state["campaign_id"]},
							),
						)
						mock_id = scheduled.get("campaign_id", "")
						if mock_id:
							mock_api_campaign_ids[variant_id] = mock_id
							await state_manager.save_mock_api_mapping(
								current_state["campaign_id"], variant_id, mock_id
							)
					except Exception as sched_exc:
						logger.warning("Failed to schedule optimized variant %s: %s", variant_id, sched_exc)
			except Exception as exc:
				logger.warning("Mock API re-scheduling skipped: %s", exc)

		await campaign_repo.update(
			current_state["campaign_id"],
			{
				"updated_at": datetime.utcnow(),
				"optimization_strategy": refined,
			},
		)

		next_state = OptimizationState(**dict(current_state))
		next_state["iteration_count"] = int(next_state.get("iteration_count", 0)) + 1
		next_state["mock_api_campaign_ids"] = mock_api_campaign_ids
		return next_state

	return await _execute_node_with_retries("update_strategy", state, _op)


def check_convergence(state: OptimizationState) -> str:
	"""Determine if optimization loop should stop."""
	if state.get("error_messages"):
		return "end"
	if int(state.get("iteration_count", 0)) >= 3:
		return "end"

	variant_metrics = state.get("current_metrics", {}).get("variant_metrics", [])
	if variant_metrics:
		scores = [
			0.7 * float(metric.get("click_rate", 0.0) or 0.0)
			+ 0.3 * float(metric.get("open_rate", 0.0) or 0.0)
			for metric in variant_metrics
			if metric.get("variant_id")
		]
		if scores and all(score >= PERFORMANCE_THRESHOLD for score in scores):
			return "end"

	if not state.get("poor_performers"):
		return "end"
	return "continue"


def create_optimization_graph() -> Any:
	"""Build and compile optimization feedback-loop graph."""
	graph = StateGraph(OptimizationState)

	graph.add_node("collect_metrics", collect_metrics_node)
	graph.add_node("identify_poor_performers", identify_poor_performers_node)
	graph.add_node("optimization", optimization_node)
	graph.add_node("regenerate_variants", regenerate_variants_node)
	graph.add_node("update_strategy", update_strategy_node)

	graph.add_edge(START, "collect_metrics")
	graph.add_edge("collect_metrics", "identify_poor_performers")
	graph.add_edge("identify_poor_performers", "optimization")
	graph.add_edge("optimization", "regenerate_variants")
	graph.add_edge("regenerate_variants", "update_strategy")
	graph.add_conditional_edges(
		"update_strategy",
		check_convergence,
		{
			"continue": "collect_metrics",
			"end": END,
		},
	)

	return graph.compile()


async def run_optimization_workflow(
	campaign_id: str,
	mock_api_campaign_ids: dict[str, str] | None = None,
) -> dict[str, Any]:
	"""Execute optimization feedback loop and return final state."""
	initial_state = create_initial_optimization_state(campaign_id)
	if mock_api_campaign_ids:
		initial_state["mock_api_campaign_ids"] = mock_api_campaign_ids
	await _save_optimization_state(initial_state)

	graph = create_optimization_graph()
	final_state = await graph.ainvoke(initial_state, config={"recursion_limit": 30})
	if not isinstance(final_state, dict):
		raise ValueError("Optimization workflow returned non-dict state")

	final_state["convergence_achieved"] = check_convergence(OptimizationState(**final_state)) == "end"
	await _save_optimization_state(OptimizationState(**final_state))
	return final_state


async def recover_workflow(campaign_id: str, checkpoint_id: str) -> dict[str, Any]:
	"""Recover optimization workflow from a checkpoint."""
	db = MongoDB.get_db()
	query = {
		"campaign_id": campaign_id,
		"workflow_type": "optimization",
		"$or": [{"checkpoint_id": checkpoint_id}, {"_id": checkpoint_id}],
	}
	try:
		query["$or"].append({"_id": ObjectId(checkpoint_id)})
	except (InvalidId, TypeError):
		pass

	checkpoint = await db["workflow_checkpoints"].find_one(query)

	if checkpoint is None:
		raise ValueError(
			f"No optimization checkpoint found for campaign_id={campaign_id}, checkpoint_id={checkpoint_id}"
		)

	restored_state = OptimizationStateModel.model_validate(
		checkpoint.get("state_snapshot", {})
	).model_dump()
	state = OptimizationState(**restored_state)

	current_node = checkpoint.get("current_node", "collect_metrics")
	sequence: list[tuple[str, Callable[[OptimizationState], Awaitable[OptimizationState]]]] = [
		("collect_metrics", collect_metrics_node),
		("identify_poor_performers", identify_poor_performers_node),
		("optimization", optimization_node),
		("regenerate_variants", regenerate_variants_node),
		("update_strategy", update_strategy_node),
	]
	names = [name for name, _ in sequence]
	start_idx = names.index(current_node) if current_node in names else 0

	for name, fn in sequence[start_idx:]:
		state = await fn(state)
		if name == "update_strategy" and check_convergence(state) == "end":
			break

	state["convergence_achieved"] = check_convergence(state) == "end"
	await _save_optimization_state(state)
	return dict(state)

