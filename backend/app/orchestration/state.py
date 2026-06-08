"""Workflow state definitions and persistence helpers for LangGraph orchestration."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Literal, TypedDict

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field, ValidationError

from app.db.mongodb import MongoDB

logger = logging.getLogger(__name__)


class CampaignState(TypedDict):
	"""Typed state for the campaign creation workflow."""

	campaign_id: str
	campaign_brief: str
	parsed_data: dict[str, Any]
	segments: dict[str, list[str]]
	strategy: dict[str, Any]
	variants: list[dict[str, Any]]
	approval_status: str
	execution_status: str
	mock_api_campaign_ids: dict[str, str]
	metrics: dict[str, Any]
	customer_results: list[dict[str, Any]]
	optimization_suggestions: list[dict[str, Any]]
	error_messages: list[str]
	checkpoint_data: dict[str, Any]
	mock_api_errors: list[dict[str, Any]]


class OptimizationState(TypedDict):
	"""Typed state for the optimization feedback-loop workflow."""

	campaign_id: str
	current_metrics: dict[str, Any]
	mock_api_campaign_ids: dict[str, str]
	customer_results: list[dict[str, Any]]
	poor_performers: list[str]
	optimization_recommendations: list[dict[str, Any]]
	new_variants: list[dict[str, Any]]
	iteration_count: int
	convergence_achieved: bool
	performance_scores: dict[str, float]
	error_messages: list[str]


class CampaignStateModel(BaseModel):
	"""Pydantic validation model for campaign workflow state."""

	campaign_id: str = Field(..., min_length=1)
	campaign_brief: str = Field(..., min_length=1)
	parsed_data: dict[str, Any] = Field(default_factory=dict)
	segments: dict[str, list[str]] = Field(default_factory=dict)
	strategy: dict[str, Any] = Field(default_factory=dict)
	variants: list[dict[str, Any]] = Field(default_factory=list)
	approval_status: Literal["pending", "approved", "rejected"] = "pending"
	execution_status: Literal[
		"not_started", "in_progress", "completed", "failed"
	] = "not_started"
	mock_api_campaign_ids: dict[str, str] = Field(default_factory=dict)
	metrics: dict[str, Any] = Field(default_factory=dict)
	customer_results: list[dict[str, Any]] = Field(default_factory=list)
	optimization_suggestions: list[dict[str, Any]] = Field(default_factory=list)
	error_messages: list[str] = Field(default_factory=list)
	checkpoint_data: dict[str, Any] = Field(default_factory=dict)
	mock_api_errors: list[dict[str, Any]] = Field(default_factory=list)


class OptimizationStateModel(BaseModel):
	"""Pydantic validation model for optimization workflow state."""

	campaign_id: str = Field(..., min_length=1)
	current_metrics: dict[str, Any] = Field(default_factory=dict)
	mock_api_campaign_ids: dict[str, str] = Field(default_factory=dict)
	customer_results: list[dict[str, Any]] = Field(default_factory=list)
	poor_performers: list[str] = Field(default_factory=list)
	optimization_recommendations: list[dict[str, Any]] = Field(default_factory=list)
	new_variants: list[dict[str, Any]] = Field(default_factory=list)
	iteration_count: int = Field(default=0, ge=0)
	convergence_achieved: bool = False
	performance_scores: dict[str, float] = Field(default_factory=dict)
	error_messages: list[str] = Field(default_factory=list)


def create_initial_campaign_state(campaign_id: str, campaign_brief: str) -> CampaignState:
	"""Create a fully shaped campaign state with default values."""
	return CampaignState(
		campaign_id=campaign_id,
		campaign_brief=campaign_brief,
		parsed_data={},
		segments={},
		strategy={},
		variants=[],
		approval_status="pending",
		execution_status="not_started",
		mock_api_campaign_ids={},
		metrics={},
		customer_results=[],
		optimization_suggestions=[],
		error_messages=[],
		checkpoint_data={},
		mock_api_errors=[],
	)


def create_initial_optimization_state(campaign_id: str) -> OptimizationState:
	"""Create a fully shaped optimization state with default values."""
	return OptimizationState(
		campaign_id=campaign_id,
		current_metrics={},
		mock_api_campaign_ids={},
		customer_results=[],
		poor_performers=[],
		optimization_recommendations=[],
		new_variants=[],
		iteration_count=0,
		convergence_achieved=False,
		performance_scores={},
		error_messages=[],
	)


class StateManager:
	"""Persist and restore workflow state/checkpoints in MongoDB."""

	def __init__(self, db: AsyncIOMotorDatabase | None = None) -> None:
		self.db = db if db is not None else MongoDB.get_db()
		self.state_collection = self.db["workflow_states"]
		self.checkpoint_collection = self.db["workflow_checkpoints"]
		self.api_mapping_collection = self.db["api_mappings"]

	async def ensure_indexes(self) -> None:
		"""Create indexes for workflow collections."""
		await self.state_collection.create_index("campaign_id", unique=True)
		await self.state_collection.create_index("updated_at")
		await self.checkpoint_collection.create_index("campaign_id")
		await self.checkpoint_collection.create_index("timestamp")
		await self.checkpoint_collection.create_index("checkpoint_id", unique=True)
		await self.api_mapping_collection.create_index("campaign_id")
		await self.api_mapping_collection.create_index("variant_id")

	async def save_state(self, state: CampaignState, campaign_id: str) -> dict[str, Any]:
		"""Validate and persist campaign workflow state for a campaign."""
		self._validate_or_raise(state)

		payload = {
			"campaign_id": campaign_id,
			"state": dict(state),
			"updated_at": datetime.now(tz=timezone.utc),
		}
		await self.state_collection.update_one(
			{"campaign_id": campaign_id},
			{"$set": payload},
			upsert=True,
		)
		logger.info("Saved workflow state", extra={"campaign_id": campaign_id})
		return payload

	async def load_state(self, campaign_id: str) -> CampaignState:
		"""Load campaign workflow state from MongoDB."""
		document = await self.state_collection.find_one({"campaign_id": campaign_id})
		if not document:
			raise ValueError(f"No workflow state found for campaign_id={campaign_id}")

		state_data = document.get("state", {})
		validated = CampaignStateModel.model_validate(state_data)
		return CampaignState(**validated.model_dump())

	def validate_state(self, state: CampaignState) -> bool:
		"""Return True when campaign state passes Pydantic validation."""
		try:
			self._validate_or_raise(state)
			return True
		except ValidationError:
			return False

	async def create_checkpoint(
		self,
		state: CampaignState,
		current_node: str = "unknown",
	) -> dict[str, Any]:
		"""Create and persist a workflow checkpoint snapshot."""
		validated = CampaignStateModel.model_validate(state)
		checkpoint = {
			"checkpoint_id": str(ObjectId()),
			"campaign_id": validated.campaign_id,
			"current_node": current_node,
			"timestamp": datetime.now(tz=timezone.utc),
			"state_snapshot": validated.model_dump(),
		}
		await self.checkpoint_collection.insert_one(checkpoint)
		logger.info(
			"Created workflow checkpoint",
			extra={
				"campaign_id": validated.campaign_id,
				"checkpoint_id": checkpoint["checkpoint_id"],
				"current_node": current_node,
			},
		)
		return checkpoint

	async def restore_from_checkpoint(self, checkpoint_id: str) -> CampaignState:
		"""Restore campaign state from a checkpoint identifier."""
		checkpoint = await self.checkpoint_collection.find_one(
			{"checkpoint_id": checkpoint_id}
		)
		if checkpoint is None:
			raise ValueError(f"Checkpoint not found: checkpoint_id={checkpoint_id}")

		snapshot = checkpoint.get("state_snapshot", {})
		validated = CampaignStateModel.model_validate(snapshot)
		return CampaignState(**validated.model_dump())

	async def get_latest_checkpoint(self, campaign_id: str) -> dict[str, Any] | None:
		"""Return most recent checkpoint for a campaign, if any."""
		return await self.checkpoint_collection.find_one(
			{"campaign_id": campaign_id},
			sort=[("timestamp", -1)],
		)

	async def save_mock_api_mapping(
		self, campaign_id: str, variant_id: str, mock_campaign_id: str
	) -> None:
		"""Persist a variant_id → Mock API campaign_id mapping to MongoDB."""
		await self.api_mapping_collection.update_one(
			{"campaign_id": campaign_id, "variant_id": variant_id},
			{
				"$set": {
					"campaign_id": campaign_id,
					"variant_id": variant_id,
					"mock_campaign_id": mock_campaign_id,
					"recorded_at": datetime.now(tz=timezone.utc),
				}
			},
			upsert=True,
		)
		logger.info(
			"Saved Mock API mapping",
			extra={
				"campaign_id": campaign_id,
				"variant_id": variant_id,
				"mock_campaign_id": mock_campaign_id,
			},
		)

	def _validate_or_raise(self, state: CampaignState) -> None:
		"""Validate campaign state and raise Pydantic validation errors."""
		CampaignStateModel.model_validate(state)

