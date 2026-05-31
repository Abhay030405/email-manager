"""Metrics test data factories (Faker-based, no factory-boy required)."""

from __future__ import annotations

import random
import uuid
from datetime import datetime


class MetricsFactory:
    @classmethod
    def create(cls, **kwargs) -> dict:
        open_rate = kwargs.pop("open_rate", round(random.uniform(0.05, 0.80), 3))
        click_rate = kwargs.pop("click_rate", round(random.uniform(0.01, 0.30), 3))
        total_sent = kwargs.pop("total_sent", random.randint(50, 2000))
        ctr = kwargs.pop("click_through_rate", round(random.uniform(0.005, 0.20), 3))

        unique_opens = max(1, int(total_sent * open_rate))
        unique_clicks = max(0, int(unique_opens * click_rate))
        performance_score = round(0.7 * click_rate + 0.3 * open_rate, 3)

        data = {
            "metric_id": str(uuid.uuid4()),
            "variant_id": str(uuid.uuid4()),
            "campaign_id": str(uuid.uuid4()),
            "mock_campaign_id": str(uuid.uuid4()),
            "total_sent": total_sent,
            "open_rate": open_rate,
            "click_rate": click_rate,
            "click_through_rate": ctr,
            "unique_opens": unique_opens,
            "unique_clicks": unique_clicks,
            "performance_score": performance_score,
            "calculated_at": datetime.utcnow(),
            "collected_at": datetime.utcnow(),
            "last_updated": datetime.utcnow(),
        }
        data.update(kwargs)
        return data

    @classmethod
    def create_batch(cls, n: int, **kwargs) -> list[dict]:
        return [cls.create(**kwargs) for _ in range(n)]

    @classmethod
    def create_high_performing(cls, **kwargs) -> dict:
        return cls.create(
            open_rate=round(random.uniform(0.50, 0.80), 3),
            click_rate=round(random.uniform(0.20, 0.40), 3),
            **kwargs,
        )

    @classmethod
    def create_low_performing(cls, **kwargs) -> dict:
        return cls.create(
            open_rate=round(random.uniform(0.01, 0.15), 3),
            click_rate=round(random.uniform(0.001, 0.05), 3),
            **kwargs,
        )
