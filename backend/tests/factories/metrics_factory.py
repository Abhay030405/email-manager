"""Factory Boy factories for Metrics test data."""

import uuid
from datetime import datetime

import factory
from faker import Faker

fake = Faker()


class MetricsFactory(factory.Factory):
    class Meta:
        model = dict

    metric_id = factory.LazyFunction(lambda: str(uuid.uuid4()))
    variant_id = factory.LazyFunction(lambda: str(uuid.uuid4()))
    campaign_id = factory.LazyFunction(lambda: str(uuid.uuid4()))
    mock_campaign_id = factory.LazyFunction(lambda: str(uuid.uuid4()))

    total_sent = factory.LazyFunction(lambda: fake.random_int(50, 2000))
    open_rate = factory.LazyFunction(lambda: round(fake.pyfloat(min_value=0.05, max_value=0.80), 3))
    click_rate = factory.LazyFunction(lambda: round(fake.pyfloat(min_value=0.01, max_value=0.30), 3))
    click_through_rate = factory.LazyFunction(lambda: round(fake.pyfloat(min_value=0.005, max_value=0.20), 3))

    # Derived counts (approximated)
    unique_opens = factory.LazyAttribute(lambda o: max(1, int(o.total_sent * o.open_rate)))
    unique_clicks = factory.LazyAttribute(lambda o: max(0, int(o.unique_opens * o.click_rate)))

    performance_score = factory.LazyAttribute(
        lambda o: round(0.7 * o.click_rate + 0.3 * o.open_rate, 3)
    )

    calculated_at = factory.LazyFunction(datetime.utcnow)
    collected_at = factory.LazyFunction(datetime.utcnow)
    last_updated = factory.LazyFunction(datetime.utcnow)


class HighPerformingMetricsFactory(MetricsFactory):
    open_rate = factory.LazyFunction(lambda: round(fake.pyfloat(min_value=0.50, max_value=0.80), 3))
    click_rate = factory.LazyFunction(lambda: round(fake.pyfloat(min_value=0.20, max_value=0.40), 3))


class LowPerformingMetricsFactory(MetricsFactory):
    open_rate = factory.LazyFunction(lambda: round(fake.pyfloat(min_value=0.01, max_value=0.15), 3))
    click_rate = factory.LazyFunction(lambda: round(fake.pyfloat(min_value=0.001, max_value=0.05), 3))
