"""Customer test data factories (Faker-based, no factory-boy required)."""

from __future__ import annotations

import random
from datetime import datetime

from faker import Faker

fake = Faker("en_IN")

_OCCUPATIONS = ["Engineer", "Manager", "Doctor", "Teacher", "Analyst", "Designer", "Architect"]
_OCC_TYPES = ["Full-time", "Part-time", "Self-employed", "Retired", "Student"]
_CITIES = ["Mumbai", "Delhi", "Bangalore", "Chennai", "Hyderabad", "Pune", "Kolkata", "Jaipur"]
_YN = ["Y", "N"]

_counter = [0]


def _next_customer_id() -> str:
    _counter[0] += 1
    return f"CUST{_counter[0]:04d}"


class CustomerFactory:
    @classmethod
    def create(cls, **kwargs) -> dict:
        data = {
            "customer_id": _next_customer_id(),
            "Full_name": fake.name(),
            "email": fake.email(),
            "Age": random.randint(18, 80),
            "Gender": random.choice(["Male", "Female"]),
            "Marital_Status": random.choice(["Single", "Married", "Divorced", "Widowed"]),
            "Family_Size": random.randint(1, 6),
            "Dependent_count": random.randint(0, 3),
            "Occupation": random.choice(_OCCUPATIONS),
            "Occupation_type": random.choice(_OCC_TYPES),
            "Monthly_Income": random.randint(15000, 250000),
            "KYC_status": random.choice(_YN),
            "City": random.choice(_CITIES),
            "Kids_in_Household": random.randint(0, 3),
            "App_Installed": random.choice(_YN),
            "Existing_Customer": random.choice(_YN),
            "Credit_score": random.randint(300, 850),
            "Social_Media_Active": random.choice(_YN),
        }
        data.update(kwargs)
        return data

    @classmethod
    def create_batch(cls, n: int, **kwargs) -> list[dict]:
        return [cls.create(**kwargs) for _ in range(n)]

    @classmethod
    def create_young_professional(cls, **kwargs) -> dict:
        return cls.create(
            Age=random.randint(25, 35),
            Occupation_type="Full-time",
            Occupation=random.choice(["Engineer", "Manager", "Analyst", "Designer"]),
            Monthly_Income=random.randint(50000, 150000),
            App_Installed="Y",
            Social_Media_Active="Y",
            Credit_score=random.randint(650, 850),
            **kwargs,
        )

    @classmethod
    def create_senior(cls, **kwargs) -> dict:
        return cls.create(
            Age=random.randint(55, 75),
            Occupation_type=random.choice(["Retired", "Part-time"]),
            Monthly_Income=random.randint(20000, 80000),
            App_Installed="N",
            **kwargs,
        )

    @classmethod
    def create_student(cls, **kwargs) -> dict:
        return cls.create(
            Age=random.randint(18, 24),
            Occupation_type="Student",
            Occupation="Student",
            Monthly_Income=random.randint(5000, 25000),
            Existing_Customer="N",
            Credit_score=random.randint(300, 600),
            **kwargs,
        )
