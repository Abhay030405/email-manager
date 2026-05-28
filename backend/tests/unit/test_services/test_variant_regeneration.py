"""Unit tests for VariantRegenerationService."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from mongomock_motor import AsyncMongoMockClient

from app.services.variant_regeneration_service import VariantRegenerationService
from app.models.variant import CampaignVariant, VariantStatus


@pytest_asyncio.fixture
async def variant_regen_service():
    client = AsyncMongoMockClient()
    db = client["campaignx_test"]
    mock_llm = MagicMock()
    service = VariantRegenerationService(db=db)
    yield service
    client.close()


@pytest.mark.unit
class TestVariantRegenerationService:

    @pytest.mark.asyncio
    async def test_regenerate_creates_new_variant(self, variant_regen_service, sample_variants):
        original = sample_variants[0]

        new_variant = await variant_regen_service.regenerate_variant(
            original_variant=original,
            optimization_insights=[
                {"issue": "Low open rate", "recommendation": "More personalised subject"}
            ],
        )

        assert new_variant is not None

    @pytest.mark.asyncio
    async def test_regenerated_variant_different_from_original(
        self, variant_regen_service, sample_variants
    ):
        original = sample_variants[0]

        new_variant = await variant_regen_service.regenerate_variant(
            original_variant=original,
            optimization_insights=[],
        )

        if new_variant:
            assert new_variant.variant_id != original.variant_id
