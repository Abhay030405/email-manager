"""Tests for CampaignIDMapper."""

from app.external.campaign_id_mapper import CampaignIDMapper


def test_register_and_get_mock_id():
    mapper = CampaignIDMapper()
    mapper.register("variant_001", "mock-uuid-001")
    assert mapper.get_mock_id("variant_001") == "mock-uuid-001"


def test_register_and_get_variant_id():
    mapper = CampaignIDMapper()
    mapper.register("variant_002", "mock-uuid-002")
    assert mapper.get_variant_id("mock-uuid-002") == "variant_002"


def test_get_missing_returns_none():
    mapper = CampaignIDMapper()
    assert mapper.get_mock_id("nonexistent") is None
    assert mapper.get_variant_id("nonexistent") is None


def test_all_mock_ids():
    mapper = CampaignIDMapper()
    mapper.register("v1", "m1")
    mapper.register("v2", "m2")
    ids = mapper.all_mock_ids()
    assert set(ids) == {"m1", "m2"}


def test_as_dict():
    mapper = CampaignIDMapper()
    mapper.register("v1", "m1")
    mapper.register("v2", "m2")
    d = mapper.as_dict()
    assert d == {"v1": "m1", "v2": "m2"}


def test_load_from_mapping():
    mapper = CampaignIDMapper()
    mapper.load({"v1": "m1", "v2": "m2"})
    assert mapper.get_mock_id("v1") == "m1"
    assert mapper.get_mock_id("v2") == "m2"


def test_load_ignores_empty_values():
    mapper = CampaignIDMapper()
    mapper.load({"v1": "m1", "": "m2", "v3": ""})
    assert len(mapper) == 1
    assert mapper.get_mock_id("v1") == "m1"


def test_len():
    mapper = CampaignIDMapper()
    assert len(mapper) == 0
    mapper.register("v1", "m1")
    assert len(mapper) == 1
    mapper.register("v2", "m2")
    assert len(mapper) == 2


def test_repr_contains_mapping():
    mapper = CampaignIDMapper()
    mapper.register("v1", "m1")
    assert "v1" in repr(mapper)
