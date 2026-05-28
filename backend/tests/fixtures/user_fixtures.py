"""User and authentication test data fixtures."""

import pytest


@pytest.fixture
def sample_user_payload() -> dict:
    return {
        "username": "test_user",
        "email": "test@example.com",
        "created_by": "test_user",
    }


@pytest.fixture
def admin_user_payload() -> dict:
    return {
        "username": "admin",
        "email": "admin@example.com",
        "created_by": "admin",
        "role": "admin",
    }
