"""Factory Boy factories for Campaign test data."""

import uuid
from datetime import datetime

import factory
from faker import Faker

fake = Faker()


class ParsedDataFactory(factory.Factory):
    class Meta:
        model = dict

    product_name = factory.LazyFunction(lambda: fake.company())
    product_description = factory.LazyFunction(lambda: fake.sentence())
    target_audience = factory.LazyChoice(
        ["young professionals", "seniors", "students", "homemakers", "entrepreneurs"]
    )
    campaign_goal = factory.LazyChoice(["awareness", "conversion", "retention", "engagement"])
    cta_link = factory.LazyFunction(lambda: fake.url())
    budget = factory.LazyFunction(lambda: float(fake.random_int(10000, 500000)))
    preferred_tone = factory.LazyChoice(["professional", "casual", "friendly", "urgent"])
    key_messages = factory.LazyFunction(
        lambda: [fake.sentence() for _ in range(3)]
    )
    constraints = None


class CampaignFactory(factory.Factory):
    class Meta:
        model = dict

    campaign_id = factory.LazyFunction(lambda: str(uuid.uuid4()))
    campaign_brief = factory.LazyFunction(lambda: fake.text(max_nb_chars=200))
    parsed_data = factory.LazyFunction(ParsedDataFactory.create)
    status = factory.LazyChoice(["draft", "pending_approval", "approved", "executing", "completed"])
    created_by = factory.LazyChoice(["admin", "test_user", "marketing_manager"])
    segments = factory.LazyFunction(list)
    created_at = factory.LazyFunction(datetime.utcnow)
    updated_at = factory.LazyFunction(datetime.utcnow)
    mock_campaign_id = None
    approved_at = None
    scheduled_time = None
