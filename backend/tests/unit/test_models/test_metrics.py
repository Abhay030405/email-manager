"""Unit tests for the Metrics model."""

import pytest
from pydantic import ValidationError

from app.models.metrics import Metrics


@pytest.mark.unit
class TestMetricsModel:

    def test_performance_score_auto_calculated(self):
        m = Metrics(
            variant_id="var-1",
            campaign_id="camp-1",
            mock_campaign_id="mock-1",
            open_rate=0.40,
            click_rate=0.10,
        )
        expected = round(0.7 * 0.10 + 0.3 * 0.40, 2)
        assert m.performance_score == expected

    def test_open_rate_percentage_property(self):
        m = Metrics(
            variant_id="v", campaign_id="c", mock_campaign_id="m",
            open_rate=0.35,
        )
        assert m.open_rate_percentage == 35.0

    def test_click_rate_percentage_property(self):
        m = Metrics(
            variant_id="v", campaign_id="c", mock_campaign_id="m",
            click_rate=0.085,
        )
        assert m.click_rate_percentage == 8.5

    def test_ctr_percentage_property(self):
        m = Metrics(
            variant_id="v", campaign_id="c", mock_campaign_id="m",
            click_through_rate=0.06,
        )
        assert m.ctr_percentage == 6.0

    def test_rates_must_be_between_0_and_1(self):
        with pytest.raises(ValidationError):
            Metrics(
                variant_id="v", campaign_id="c", mock_campaign_id="m",
                open_rate=1.5,
            )
        with pytest.raises(ValidationError):
            Metrics(
                variant_id="v", campaign_id="c", mock_campaign_id="m",
                click_rate=-0.1,
            )

    def test_from_mock_api_classmethod(self):
        data = {
            "open_rate": 0.60,
            "click_rate": 0.20,
            "click_through_rate": 0.33,
            "total_sent": 100,
            "unique_opens": 60,
            "unique_clicks": 20,
        }
        m = Metrics.from_mock_api(
            data,
            variant_id="var-1",
            campaign_id="camp-1",
            mock_campaign_id="mock-abc",
        )
        assert m.open_rate == 0.60
        assert m.click_rate == 0.20
        assert m.total_sent == 100
        assert m.unique_opens == 60
        assert m.collected_at is not None

    def test_metric_id_auto_generated(self):
        m = Metrics(variant_id="v", campaign_id="c", mock_campaign_id="m")
        assert m.metric_id is not None
        assert len(m.metric_id) > 0

    def test_total_sent_non_negative(self):
        with pytest.raises(ValidationError):
            Metrics(
                variant_id="v", campaign_id="c", mock_campaign_id="m",
                total_sent=-1,
            )
