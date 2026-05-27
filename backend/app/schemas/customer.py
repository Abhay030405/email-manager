"""Customer request / response schemas."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, Field

# Re-export existing CRUD schemas
from app.models.schemas import CustomerCreate, CustomerResponse, CustomerUpdate

__all__ = [
    # Existing CRUD schemas (thin re-exports)
    "CustomerCreate",
    "CustomerResponse",
    "CustomerUpdate",
    # Richer / validated schemas
    "CustomerSchema",
    "CustomerListResponse",
]


# ── Full validated customer schema (Mock API format) ──────────────────────────

class CustomerSchema(BaseModel):
    """Customer record matching the 18-field Mock Campaign API schema.

    Used for responses and for validating data ingested from the Mock API.
    """

    customer_id: str = Field(..., pattern=r"^CUST\d{4}$")
    Full_name: str = Field(..., min_length=1)
    email: EmailStr
    Age: int = Field(..., ge=18, le=100)
    Gender: Literal["Male", "Female", "Other"]
    Marital_Status: Literal["Married", "Single", "Divorced", "Widowed"]
    Family_Size: int = Field(..., ge=1)
    Dependent_count: int = Field(..., ge=0)
    Occupation: str
    Occupation_type: Literal["Full-time", "Part-time", "Self-employed", "Retired", "Student"]
    Monthly_Income: int = Field(..., ge=0)
    KYC_status: Literal["Y", "N"]
    City: str
    Kids_in_Household: int = Field(..., ge=0)
    App_Installed: Literal["Y", "N"]
    Existing_Customer: Literal["Y", "N"]
    Credit_score: int = Field(..., ge=300, le=850)
    Social_Media_Active: Literal["Y", "N"]

    model_config = {
        "populate_by_name": True,
        "json_schema_extra": {
            "examples": [
                {
                    "customer_id": "CUST0001",
                    "Full_name": "Ravi Sharma",
                    "email": "ravi.sharma@example.com",
                    "Age": 32,
                    "Gender": "Male",
                    "Marital_Status": "Married",
                    "Family_Size": 4,
                    "Dependent_count": 2,
                    "Occupation": "Software Engineer",
                    "Occupation_type": "Full-time",
                    "Monthly_Income": 75000,
                    "KYC_status": "Y",
                    "City": "Mumbai",
                    "Kids_in_Household": 1,
                    "App_Installed": "Y",
                    "Existing_Customer": "Y",
                    "Credit_score": 720,
                    "Social_Media_Active": "Y",
                }
            ]
        },
    }


class CustomerListResponse(BaseModel):
    """Paginated customer list with origin metadata."""

    customers: list[CustomerSchema]
    total: int
    fetched_from: str = Field(
        ...,
        description="Source of the data: 'database' or 'mock_api'",
    )
