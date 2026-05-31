"""Unit tests for the CampaignVariant model."""

from datetime import datetime, timedelta

import pytest
from pydantic import ValidationError

from app.models.variant import CampaignVariant, VariantStatus


@pytest.mark.unit
class TestCampaignVariantModel:

    def _valid_variant(self, **overrides) -> dict:
        base = {
            "variant_id": "var-001",
            "campaign_id": "camp-001",
            "segment_name": "young_professionals",
            "subject_line": "Exclusive offer for you",
            "email_body": "<p>Dear Customer, check out our exclusive offer.</p>",
            "status": VariantStatus.DRAFT,
        }
        base.update(overrides)
        return base

    def test_create_variant_with_defaults(self):
        v = CampaignVariant(**self._valid_variant())
        assert v.variant_id == "var-001"
        assert v.status == VariantStatus.DRAFT
        assert v.customer_ids == []
        assert v.personalization_tags == []

    def test_variant_status_enum_values(self):
        assert VariantStatus.DRAFT == "draft"
        assert VariantStatus.SCHEDULED == "scheduled"
        assert VariantStatus.SENT == "sent"
        assert VariantStatus.CANCELLED == "cancelled"

    def test_variant_with_customer_ids(self):
        v = CampaignVariant(**self._valid_variant(
            customer_ids=["CUST0001", "CUST0002", "CUST0003"]
        ))
        assert len(v.customer_ids) == 3
        assert "CUST0001" in v.customer_ids

    def test_variant_with_send_time(self):
        send = datetime.utcnow() + timedelta(hours=2)
        v = CampaignVariant(**self._valid_variant(send_time=send))
        assert v.send_time is not None

    def test_variant_id_auto_generated_when_omitted(self):
        data = self._valid_variant()
        data.pop("variant_id")
        v = CampaignVariant(**data)
        # variant_id has a default_factory — should be auto-generated UUID
        assert v.variant_id is not None
        assert len(v.variant_id) > 0

    def test_campaign_id_required(self):
        data = self._valid_variant()
        data.pop("campaign_id")
        with pytest.raises(ValidationError):
            CampaignVariant(**data)

    def test_model_dump(self):
        v = CampaignVariant(**self._valid_variant())
        d = v.model_dump()
        assert d["variant_id"] == "var-001"
        assert d["campaign_id"] == "camp-001"
        assert d["status"] == "draft"
