"""Campaign test data factories (Faker-based, no factory-boy required)."""

from __future__ import annotations

import random
import uuid
from datetime import datetime

from faker import Faker

fake = Faker()

_STATUSES = ["draft", "pending_approval", "approved", "executing", "completed", "optimizing"]
_AUDIENCES = ["young professionals", "seniors", "students", "homemakers", "entrepreneurs"]
_GOALS = ["awareness", "conversion", "retention", "engagement"]
_TONES = ["professional", "casual", "friendly", "urgent"]
_CREATORS = ["admin", "test_user", "marketing_manager"]


class ParsedDataFactory:
    @classmethod
    def create(cls, **kwargs) -> dict:
        data = {
            "product_name": fake.company(),
            "product_description": fake.sentence(),
            "target_audience": random.choice(_AUDIENCES),
            "campaign_goal": random.choice(_GOALS),
            "cta_link": fake.url(),
            "budget": float(random.randint(10000, 500000)),
            "preferred_tone": random.choice(_TONES),
            "key_messages": [fake.sentence() for _ in range(3)],
            "constraints": None,
        }
        data.update(kwargs)
        return data


class CampaignFactory:
    @classmethod
    def create(cls, **kwargs) -> dict:
        data = {
            "campaign_id": str(uuid.uuid4()),
            "campaign_brief": fake.text(max_nb_chars=200),
            "parsed_data": ParsedDataFactory.create(),
            "status": random.choice(_STATUSES),
            "created_by": random.choice(_CREATORS),
            "segments": [],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "mock_campaign_id": None,
            "approved_at": None,
            "scheduled_time": None,
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
    def create_pending(cls, **kwargs) -> dict:
        return cls.create(status="pending_approval", **kwargs)

    @classmethod
    def create_approved(cls, **kwargs) -> dict:
        return cls.create(status="approved", approved_at=datetime.utcnow(), **kwargs)

    @classmethod
    def create_executing(cls, **kwargs) -> dict:
        return cls.create(status="executing", **kwargs)

    @classmethod
    def create_completed(cls, **kwargs) -> dict:
        return cls.create(status="completed", **kwargs)
