"""Unit tests for the Customer model."""

import pytest
from pydantic import ValidationError

from app.models.customer import Customer


def _valid_customer(**overrides) -> dict:
    base = {
        "customer_id": "CUST0001",
        "Full_name": "Rahul Sharma",
        "email": "rahul@example.com",
        "Age": 28,
        "Gender": "Male",
        "Marital_Status": "Single",
        "Family_Size": 1,
        "Dependent_count": 0,
        "Occupation": "Engineer",
        "Occupation_type": "Full-time",
        "Monthly_Income": 75000,
        "KYC_status": "Y",
        "City": "Bangalore",
        "Kids_in_Household": 0,
        "App_Installed": "Y",
        "Existing_Customer": "N",
        "Credit_score": 750,
        "Social_Media_Active": "Y",
    }
    base.update(overrides)
    return base


@pytest.mark.unit
class TestCustomerModel:

    def test_valid_customer_creation(self):
        c = Customer(**_valid_customer())
        assert c.customer_id == "CUST0001"
        assert c.Full_name == "Rahul Sharma"
        assert c.Age == 28

    def test_customer_id_format(self):
        c = Customer(**_valid_customer(customer_id="CUST9999"))
        assert c.customer_id == "CUST9999"

    def test_kyc_status_valid_values(self):
        c_y = Customer(**_valid_customer(KYC_status="Y"))
        c_n = Customer(**_valid_customer(KYC_status="N"))
        assert c_y.KYC_status == "Y"
        assert c_n.KYC_status == "N"

    def test_invalid_kyc_status_rejected(self):
        with pytest.raises(ValidationError):
            Customer(**_valid_customer(KYC_status="X"))

    def test_gender_valid_values(self):
        for g in ("Male", "Female", "Other"):
            c = Customer(**_valid_customer(Gender=g))
            assert c.Gender == g

    def test_invalid_gender_rejected(self):
        with pytest.raises(ValidationError):
            Customer(**_valid_customer(Gender="Unknown"))

    def test_occupation_type_valid_values(self):
        for ot in ("Full-time", "Part-time", "Self-employed", "Retired", "Student"):
            c = Customer(**_valid_customer(Occupation_type=ot))
            assert c.Occupation_type == ot

    def test_synced_from_mock_api_defaults_false(self):
        c = Customer(**_valid_customer())
        assert c.synced_from_mock_api is False

    def test_customer_model_dump_has_all_18_fields(self):
        c = Customer(**_valid_customer())
        d = c.model_dump()
        required = {
            "customer_id", "Full_name", "email", "Age", "Gender",
            "Marital_Status", "Family_Size", "Dependent_count", "Occupation",
            "Occupation_type", "Monthly_Income", "KYC_status", "City",
            "Kids_in_Household", "App_Installed", "Existing_Customer",
            "Credit_score", "Social_Media_Active",
        }
        assert required.issubset(d.keys())

    def test_email_required(self):
        data = _valid_customer()
        data.pop("email")
        with pytest.raises(ValidationError):
            Customer(**data)
