"""Campaign test data factories (Faker-based, no factory-boy required)."""

from __future__ import annotations

import random
import uuid
from datetime import datetime, timezone

from faker import Faker

fake = Faker()

_STATUSES = ["draft", "pending_approval", "approved", "executing", "completed", "optimizing"]
_GOALS = ["awareness", "conversion", "retention", "engagement"]
_TONES = ["Formal", "Friendly", "Urgent"]


class ParsedDataFactory:
    @classmethod
    def create(cls, **kwargs) -> dict:
        data = {
            "product_details": {
                "product_name": fake.company(),
                "product_description": fake.sentence(),
                "cta_link": fake.url(),
            },
            "target_audience": {
                "Group 1": {
                    "min_age": random.randint(18, 35),
                    "max_age": random.randint(36, 60),
                    "Occupation_type": "Full-time",
                    "App_Installed": "Y",
                }
            },
            "campaign_goal": {"objective": random.choice(_GOALS)},
            "campaign_preferences": {
                "email_tone": random.choice(_TONES),
                "campaign_name": fake.bs().title(),
                "content_hints": "",
            },
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
            "segments": [],
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
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
        return cls.create(status="approved", approved_at=datetime.now(timezone.utc), **kwargs)

    @classmethod
    def create_executing(cls, **kwargs) -> dict:
        return cls.create(status="executing", **kwargs)

    @classmethod
    def create_completed(cls, **kwargs) -> dict:
        return cls.create(status="completed", **kwargs)
