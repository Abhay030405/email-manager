"""Customer data model for MongoDB customers collection."""

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator


class Gender(str, Enum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"


class ActivityStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    DORMANT = "dormant"


class PurchaseRecord(BaseModel):
    """Individual purchase history entry."""

    product: str
    amount: float = Field(..., gt=0)
    date: datetime


class Preferences(BaseModel):
    """Customer preference data."""

    tags: list[str] = Field(default_factory=list)
    categories: list[str] = Field(default_factory=list)


class Customer(BaseModel):
    """Customer document model for MongoDB."""

    customer_id: str = Field(..., description="Primary key for customer")
    age: int = Field(..., ge=0, le=120)
    gender: Gender
    location: str
    activity_status: ActivityStatus = ActivityStatus.ACTIVE
    purchase_history: list[PurchaseRecord] = Field(default_factory=list)
    preferences: Preferences = Field(default_factory=Preferences)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("customer_id")
    @classmethod
    def validate_customer_id(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("customer_id must not be empty")
        return v.strip()

    @field_validator("location")
    @classmethod
    def validate_location(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("location must not be empty")
        if len(v.strip()) < 2:
            raise ValueError("location must be at least 2 characters")
        return v.strip()

    def to_dict(self) -> dict[str, Any]:
        """Serialize the model to a dictionary for MongoDB insertion."""
        return self.model_dump()

    model_config = {"collection": "customers"}


# Index definitions for the customers collection
CUSTOMER_INDEXES = [
    {"keys": [("customer_id", 1)], "unique": True},
    {"keys": [("age", 1)]},
    {"keys": [("gender", 1)]},
    {"keys": [("location", 1)]},
    {"keys": [("activity_status", 1)]},
]
