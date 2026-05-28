"""Factory Boy factories for CampaignVariant test data."""

import uuid
from datetime import datetime, timedelta

import factory
from faker import Faker

fake = Faker()


class VariantFactory(factory.Factory):
    class Meta:
        model = dict

    variant_id = factory.LazyFunction(lambda: str(uuid.uuid4()))
    campaign_id = factory.LazyFunction(lambda: str(uuid.uuid4()))
    mock_campaign_id = None
    segment_name = factory.LazyChoice(
        ["young_professionals", "seniors", "students", "high_spenders", "dormant_users"]
    )
    subject_line = factory.LazyFunction(lambda: fake.sentence(nb_words=8).rstrip("."))
    email_body = factory.LazyFunction(lambda: fake.paragraph(nb_sentences=5))
    send_time = factory.LazyFunction(lambda: datetime.utcnow() + timedelta(hours=1))
    variant_type = factory.LazyChoice(["var_1", "var_2", "variant_A", "variant_B"])
    personalization_tags = factory.LazyFunction(lambda: ["Full_name", "City"])
    status = factory.LazyChoice(["draft", "scheduled", "sent", "cancelled"])
    customer_ids = factory.LazyFunction(
        lambda: [f"CUST{fake.random_int(1, 5000):04d}" for _ in range(5)]
    )
    campaign_metadata = None
    created_at = factory.LazyFunction(datetime.utcnow)
