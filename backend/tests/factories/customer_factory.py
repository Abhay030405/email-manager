"""Factory Boy factories for Customer test data (Mock API 18-field schema)."""

import factory
from faker import Faker

fake = Faker("en_IN")

_OCCUPATIONS = ["Engineer", "Manager", "Doctor", "Teacher", "Analyst", "Designer", "Architect"]
_OCC_TYPES = ["Full-time", "Part-time", "Self-employed", "Retired", "Student"]
_CITIES = ["Mumbai", "Delhi", "Bangalore", "Chennai", "Hyderabad", "Pune", "Kolkata", "Jaipur"]


class CustomerFactory(factory.Factory):
    class Meta:
        model = dict

    customer_id = factory.Sequence(lambda n: f"CUST{n + 1:04d}")
    Full_name = factory.LazyFunction(lambda: fake.name())
    email = factory.LazyFunction(lambda: fake.email())
    Age = factory.LazyFunction(lambda: fake.random_int(18, 80))
    Gender = factory.LazyChoice(["Male", "Female"])
    Marital_Status = factory.LazyChoice(["Single", "Married", "Divorced", "Widowed"])
    Family_Size = factory.LazyFunction(lambda: fake.random_int(1, 6))
    Dependent_count = factory.LazyFunction(lambda: fake.random_int(0, 3))
    Occupation = factory.LazyChoice(_OCCUPATIONS)
    Occupation_type = factory.LazyChoice(_OCC_TYPES)
    Monthly_Income = factory.LazyFunction(lambda: fake.random_int(15000, 250000))
    KYC_status = factory.LazyChoice(["Y", "N"])
    City = factory.LazyChoice(_CITIES)
    Kids_in_Household = factory.LazyFunction(lambda: fake.random_int(0, 3))
    App_Installed = factory.LazyChoice(["Y", "N"])
    Existing_Customer = factory.LazyChoice(["Y", "N"])
    Credit_score = factory.LazyFunction(lambda: fake.random_int(300, 850))
    Social_Media_Active = factory.LazyChoice(["Y", "N"])


class YoungProfessionalCustomerFactory(CustomerFactory):
    """Factory preset for young professional segment."""
    Age = factory.LazyFunction(lambda: fake.random_int(25, 35))
    Occupation_type = "Full-time"
    Occupation = factory.LazyChoice(["Engineer", "Manager", "Analyst", "Designer"])
    Monthly_Income = factory.LazyFunction(lambda: fake.random_int(50000, 150000))
    App_Installed = "Y"
    Social_Media_Active = "Y"
    Credit_score = factory.LazyFunction(lambda: fake.random_int(650, 850))


class SeniorCustomerFactory(CustomerFactory):
    """Factory preset for senior segment."""
    Age = factory.LazyFunction(lambda: fake.random_int(55, 75))
    Occupation_type = factory.LazyChoice(["Retired", "Part-time"])
    Monthly_Income = factory.LazyFunction(lambda: fake.random_int(20000, 80000))
    App_Installed = "N"


class StudentCustomerFactory(CustomerFactory):
    """Factory preset for student segment."""
    Age = factory.LazyFunction(lambda: fake.random_int(18, 24))
    Occupation_type = "Student"
    Occupation = "Student"
    Monthly_Income = factory.LazyFunction(lambda: fake.random_int(5000, 25000))
    Existing_Customer = "N"
    Credit_score = factory.LazyFunction(lambda: fake.random_int(300, 600))
