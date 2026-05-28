"""Customer test data fixtures (Mock API 18-field schema)."""

import pytest
from faker import Faker

from app.models.customer import Customer

fake = Faker("en_IN")


@pytest.fixture
def sample_customer() -> Customer:
    return Customer(
        customer_id="CUST0001",
        Full_name="Rahul Sharma",
        email="rahul.sharma@example.com",
        Age=28,
        Gender="Male",
        Marital_Status="Single",
        Family_Size=1,
        Dependent_count=0,
        Occupation="Software Engineer",
        Occupation_type="Full-time",
        Monthly_Income=75000,
        KYC_status="Y",
        City="Bangalore",
        Kids_in_Household=0,
        App_Installed="Y",
        Existing_Customer="N",
        Credit_score=750,
        Social_Media_Active="Y",
        synced_from_mock_api=True,
    )


@pytest.fixture
def sample_customers_small() -> list[Customer]:
    """10 customers with diverse demographics for fast unit tests."""
    data = [
        ("CUST0001", "Rahul Sharma", 28, "Male", "Single", "Bangalore", "Full-time", 75000, 750, "Y", "N", "Y"),
        ("CUST0002", "Priya Patel", 32, "Female", "Married", "Mumbai", "Full-time", 90000, 720, "Y", "Y", "Y"),
        ("CUST0003", "Amit Kumar", 45, "Male", "Married", "Delhi", "Self-employed", 150000, 800, "N", "Y", "N"),
        ("CUST0004", "Sunita Devi", 58, "Female", "Widowed", "Chennai", "Retired", 30000, 690, "N", "Y", "N"),
        ("CUST0005", "Rohit Singh", 22, "Male", "Single", "Pune", "Student", 10000, 550, "Y", "N", "Y"),
        ("CUST0006", "Kavya Reddy", 35, "Female", "Single", "Hyderabad", "Full-time", 85000, 760, "Y", "N", "Y"),
        ("CUST0007", "Suresh Nair", 50, "Male", "Married", "Kochi", "Full-time", 120000, 810, "N", "Y", "N"),
        ("CUST0008", "Meena Iyer", 27, "Female", "Single", "Bangalore", "Part-time", 40000, 630, "Y", "N", "Y"),
        ("CUST0009", "Deepak Joshi", 40, "Male", "Married", "Jaipur", "Self-employed", 95000, 740, "Y", "Y", "Y"),
        ("CUST0010", "Ananya Gupta", 25, "Female", "Single", "Mumbai", "Full-time", 65000, 700, "Y", "N", "Y"),
    ]
    customers = []
    for cid, name, age, gender, marital, city, occ_type, income, credit, app, existing, social in data:
        customers.append(
            Customer(
                customer_id=cid,
                Full_name=name,
                email=f"{name.lower().replace(' ', '.')}@example.com",
                Age=age,
                Gender=gender,
                Marital_Status=marital,
                Family_Size=2,
                Dependent_count=0,
                Occupation="Professional",
                Occupation_type=occ_type,
                Monthly_Income=income,
                KYC_status="Y",
                City=city,
                Kids_in_Household=0,
                App_Installed=app,
                Existing_Customer=existing,
                Credit_score=credit,
                Social_Media_Active=social,
                synced_from_mock_api=True,
            )
        )
    return customers


@pytest.fixture
def sample_customers_batch() -> list[Customer]:
    """100 synthetic customers for broader tests."""
    occupations = ["Engineer", "Manager", "Doctor", "Teacher", "Analyst", "Designer"]
    occ_types = ["Full-time", "Part-time", "Self-employed", "Retired", "Student"]
    cities = ["Mumbai", "Delhi", "Bangalore", "Chennai", "Hyderabad", "Pune", "Kolkata"]
    customers = []
    for i in range(1, 101):
        customers.append(
            Customer(
                customer_id=f"CUST{i:04d}",
                Full_name=fake.name(),
                email=fake.email(),
                Age=18 + (i % 62),
                Gender="Male" if i % 2 == 0 else "Female",
                Marital_Status="Single" if i % 3 == 0 else "Married",
                Family_Size=1 + (i % 5),
                Dependent_count=i % 3,
                Occupation=occupations[i % len(occupations)],
                Occupation_type=occ_types[i % len(occ_types)],
                Monthly_Income=20000 + (i * 1500),
                KYC_status="Y" if i % 4 != 0 else "N",
                City=cities[i % len(cities)],
                Kids_in_Household=i % 3,
                App_Installed="Y" if i % 3 != 0 else "N",
                Existing_Customer="Y" if i % 2 == 0 else "N",
                Credit_score=500 + (i % 350),
                Social_Media_Active="Y" if i % 2 == 0 else "N",
                synced_from_mock_api=True,
            )
        )
    return customers


@pytest.fixture
def mock_api_customer_dict() -> dict:
    """Raw Mock API customer payload (18 fields)."""
    return {
        "customer_id": "CUST0001",
        "Full_name": "Rahul Sharma",
        "email": "rahul.sharma@example.com",
        "Age": 28,
        "Gender": "Male",
        "Marital_Status": "Single",
        "Family_Size": 1,
        "Dependent_count": 0,
        "Occupation": "Software Engineer",
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
