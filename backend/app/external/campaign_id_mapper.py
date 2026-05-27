"""In-process mapper between internal variant IDs and Mock API campaign IDs."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class CampaignIDMapper:
    """Maintains a bidirectional mapping of variant_id ↔ mock_campaign_id.

    Persisting to MongoDB is the authority; this class provides a fast in-memory
    lookup during a single workflow execution run.
    """

    def __init__(self) -> None:
        self._variant_to_mock: dict[str, str] = {}
        self._mock_to_variant: dict[str, str] = {}

    def register(self, variant_id: str, mock_campaign_id: str) -> None:
        """Record a new variant_id → mock_campaign_id mapping."""
        self._variant_to_mock[variant_id] = mock_campaign_id
        self._mock_to_variant[mock_campaign_id] = variant_id
        logger.debug("Registered mapping: %s → %s", variant_id, mock_campaign_id)

    def get_mock_id(self, variant_id: str) -> str | None:
        return self._variant_to_mock.get(variant_id)

    def get_variant_id(self, mock_campaign_id: str) -> str | None:
        return self._mock_to_variant.get(mock_campaign_id)

    def all_mock_ids(self) -> list[str]:
        return list(self._variant_to_mock.values())

    def as_dict(self) -> dict[str, str]:
        """Return the full variant_id → mock_campaign_id mapping."""
        return dict(self._variant_to_mock)

    def load(self, mapping: dict[str, Any]) -> None:
        """Populate from an existing mapping dict (e.g., from campaign state)."""
        for variant_id, mock_campaign_id in mapping.items():
            if variant_id and mock_campaign_id:
                self.register(str(variant_id), str(mock_campaign_id))

    def __len__(self) -> int:
        return len(self._variant_to_mock)

    def __repr__(self) -> str:
        return f"CampaignIDMapper({self._variant_to_mock!r})"
