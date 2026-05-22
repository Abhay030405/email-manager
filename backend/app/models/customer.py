"""Customer data model aligned with Mock Campaign API schema.

The Mock API returns customer data with 18 fields including Indian
demographics.  Field aliases handle CSV variations like "Dependent count"
and "KYC status".
"""

from datetime import datetime
from typing import Any, ClassVar, Literal, Optional
import re

from pydantic import BaseModel, Field, field_validator, model_validator


class Customer(BaseModel):
    """Customer document model matching the Mock Campaign API 18-field schema."""

    # ── Mock API core fields (18) ─────────────────────────────────
    customer_id: str = Field(
        ..., description="Primary key, format CUST0001"
    )
    Full_name: str = Field(..., description="Customer full name")
    email: str = Field(..., description="Email address")
    Age: int = Field(..., ge=0, le=120)
    Gender: Literal["Male", "Female", "Other"]
    Marital_Status: Literal["Married", "Single", "Divorced", "Widowed"] = "Single"
    Family_Size: int = Field(1, ge=1, le=10)
    Dependent_count: int = Field(
        0, ge=0, alias="Dependent count"
    )
    Occupation: str = Field("", description="e.g. Engineer, Doctor, Teacher")
    Occupation_type: Literal[
        "Full-time", "Part-time", "Self-employed", "Retired", "Student"
    ] = Field("Full-time", alias="Occupation type")
    Monthly_Income: int = Field(0, ge=0)
    KYC_status: Literal["Y", "N"] = Field("N", alias="KYC status")
    City: str = Field(..., description="Indian city name")
    Kids_in_Household: int = Field(0, ge=0)
    App_Installed: Literal["Y", "N"] = "N"
    Existing_Customer: Literal["Y", "N"] = Field(
        "N", alias="Existing Customer"
    )
    Credit_score: int = Field(300, ge=300, le=850)
    Social_Media_Active: Literal["Y", "N"] = "N"

    # ── Internal tracking fields ──────────────────────────────────
    synced_from_mock_api: bool = False
    last_synced_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # ── Validators ────────────────────────────────────────────────

    @field_validator("customer_id")
    @classmethod
    def validate_customer_id(cls, v: str) -> str:
        """Ensure customer_id matches CUST#### format."""
        if not re.match(r"^CUST\d{4}$", v):
            raise ValueError(
                "customer_id must match pattern CUST followed by 4 digits"
            )
        return v

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Basic email format check."""
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", v):
            raise ValueError("Invalid email format")
        return v.strip().lower()

    @field_validator("Full_name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Full_name must not be empty")
        return v.strip()

    @field_validator("City")
    @classmethod
    def validate_city(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("City must not be empty")
        return v.strip()

    # ── Serialization ─────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict for MongoDB insertion (uses field names, not aliases)."""
        return self.model_dump(by_alias=False)

    @classmethod
    def from_mock_api(cls, data: dict[str, Any]) -> "Customer":
        """Parse a customer record from Mock API response.

        Handles CSV field-name variations (spaces in names).
        """
        mapped = {**data}
        # Mark as synced from API
        mapped.setdefault("synced_from_mock_api", True)
        mapped.setdefault("last_synced_at", datetime.utcnow())
        return cls.model_validate(mapped)

    model_config = {
        "populate_by_name": True,
        "collection": "customers",
    }


# Index definitions for the customers collection
CUSTOMER_INDEXES = [
    {"keys": [("customer_id", 1)], "unique": True},
    {"keys": [("Age", 1)]},
    {"keys": [("Gender", 1)]},
    {"keys": [("City", 1)]},
    {"keys": [("Credit_score", 1)]},
    {"keys": [("Occupation", 1)]},
    {"keys": [("App_Installed", 1)]},
    {"keys": [("Existing_Customer", 1)]},
    # Compound index for segmentation queries
    {"keys": [("Gender", 1), ("Age", 1), ("City", 1)]},
]
