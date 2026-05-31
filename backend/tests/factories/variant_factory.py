"""CampaignVariant test data factories (Faker-based, no factory-boy required)."""

from __future__ import annotations

import random
import uuid
from datetime import datetime, timedelta

from faker import Faker

fake = Faker()

_SEGMENTS = ["young_professionals", "seniors", "students", "high_spenders", "dormant_users"]
_VARIANT_TYPES = ["var_1", "var_2", "variant_A", "variant_B"]
_STATUSES = ["draft", "scheduled", "sent", "cancelled"]


class VariantFactory:
    @classmethod
    def create(cls, **kwargs) -> dict:
        data = {
            "variant_id": str(uuid.uuid4()),
            "campaign_id": str(uuid.uuid4()),
            "mock_campaign_id": None,
            "segment_name": random.choice(_SEGMENTS),
            "subject_line": fake.sentence(nb_words=8).rstrip("."),
            "email_body": fake.paragraph(nb_sentences=5),
            "send_time": datetime.utcnow() + timedelta(hours=1),
            "variant_type": random.choice(_VARIANT_TYPES),
            "personalization_tags": ["Full_name", "City"],
            "status": random.choice(_STATUSES),
            "customer_ids": [f"CUST{random.randint(1, 5000):04d}" for _ in range(5)],
            "campaign_metadata": None,
            "created_at": datetime.utcnow(),
        }
        data.update(kwargs)
        return data

    @classmethod
    def create_batch(cls, n: int, **kwargs) -> list[dict]:
        return [cls.create(**kwargs) for _ in range(n)]

    @classmethod
    def create_draft(cls, **kwargs) -> dict:
        return cls.create(status="draft", **kwargs)

    @classmethod
    def create_scheduled(cls, **kwargs) -> dict:
        return cls.create(status="scheduled", send_time=datetime.utcnow() + timedelta(hours=2), **kwargs)

    @classmethod
    def create_sent(cls, **kwargs) -> dict:
        return cls.create(status="sent", mock_campaign_id=str(uuid.uuid4()), **kwargs)
