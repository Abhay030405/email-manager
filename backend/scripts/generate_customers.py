"""Generate 5 000 additional customer records, append to customers.csv,
and upsert them into MongoDB.

Usage (from backend/):
    python scripts/generate_customers.py
"""

import asyncio
import csv
import random
import sys
from pathlib import Path
from datetime import datetime

# Make app importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db.mongodb import MongoDB
from app.db.repositories.customer_repo import CustomerRepository
from app.models.customer import Customer

# ── Seed for reproducibility ─────────────────────────────────────
random.seed(2024)

# ── Value pools drawn from existing data distribution ─────────────

FIRST_NAMES = [
    "Aarav", "Aditya", "Ajay", "Akash", "Amit", "Amita", "Amitabh", "Ananya",
    "Anjali", "Ankit", "Ankita", "Anushka", "Arjun", "Aryan", "Ashish", "Ayesha",
    "Deepak", "Deepika", "Dev", "Disha", "Divya", "Gaurav", "Geeta", "Harshita",
    "Ishaan", "Ishita", "Jyoti", "Kabir", "Karan", "Kartik", "Kavita", "Kavya",
    "Kishan", "Komal", "Krishna", "Kunal", "Lakshmi", "Manish", "Manisha",
    "Meena", "Meera", "Mohit", "Monika", "Neha", "Nikhil", "Nisha", "Pallavi",
    "Pooja", "Pradeep", "Prakash", "Priya", "Rahul", "Raj", "Rajesh", "Rakesh",
    "Ramesh", "Ravi", "Rekha", "Riya", "Rohit", "Ruchi", "Sachin", "Sakshi",
    "Sameer", "Sandeep", "Sanjay", "Sapna", "Sara", "Seema", "Shivam", "Shruti",
    "Sneha", "Sonal", "Subhash", "Sumit", "Sunita", "Suresh", "Swati", "Tanvi",
    "Tarun", "Tina", "Usha", "Varun", "Vibha", "Vikram", "Vinay", "Vinita",
    "Vishal", "Yamini", "Yash", "Zara",
]

LAST_NAMES = [
    "Agarwal", "Agrawal", "Ahuja", "Arora", "Bajaj", "Banerjee", "Bose",
    "Chakraborty", "Chatterjee", "Chopra", "Choudhary", "Das", "Desai",
    "Dubey", "Dutta", "Garg", "Ghosh", "Goswami", "Goyal", "Gupta",
    "Iyer", "Jain", "Jha", "Joshi", "Kaur", "Khanna", "Kapoor", "Kulkarni",
    "Kumar", "Lal", "Malhotra", "Mehta", "Menon", "Mishra", "Mukherjee",
    "Nair", "Nanda", "Pandey", "Patel", "Pillai", "Prasad", "Rao",
    "Reddy", "Roy", "Saxena", "Sen", "Shah", "Sharma", "Singh", "Sinha",
    "Srivastava", "Subramanian", "Tiwari", "Tripathi", "Varma", "Verma", "Yadav",
]

CITIES = [
    "Mumbai", "Delhi", "Bengaluru", "Hyderabad", "Chennai", "Kolkata",
    "Ahmedabad", "Pune", "Jaipur", "Lucknow", "Kochi", "Indore",
    "Bhopal", "Nagpur", "Surat", "Patna", "Vadodara", "Visakhapatnam",
    "Coimbatore", "Chandigarh",
]

OCCUPATIONS = [
    "Engineer", "IT Professional", "Doctor", "Teacher", "Banker",
    "Civil Servant", "Architect", "Pharmacist", "Homemaker", "Accountant",
    "Lawyer", "Business Owner", "Sales Manager", "HR Manager", "Nurse",
]

OCCUPATION_TYPES = ["Full-time", "Part-time", "Self-employed"]
# Weighted probabilities matching observed distribution
OCC_TYPE_WEIGHTS = [0.62, 0.28, 0.10]

GENDERS = ["Male", "Female"]
MARITAL_STATUSES = ["Single", "Married", "Divorced"]
MARITAL_WEIGHTS = [0.50, 0.42, 0.08]


def _income_for_occupation(occupation: str) -> int:
    """Return a plausible monthly income (INR) for the given occupation."""
    ranges = {
        "Doctor": (120_000, 260_000),
        "Banker": (80_000, 220_000),
        "Architect": (60_000, 180_000),
        "IT Professional": (60_000, 200_000),
        "Engineer": (50_000, 180_000),
        "Lawyer": (70_000, 200_000),
        "Business Owner": (50_000, 250_000),
        "Civil Servant": (45_000, 180_000),
        "Accountant": (40_000, 120_000),
        "Sales Manager": (45_000, 130_000),
        "HR Manager": (45_000, 120_000),
        "Teacher": (30_000, 100_000),
        "Pharmacist": (40_000, 110_000),
        "Nurse": (30_000, 80_000),
        "Homemaker": (20_000, 60_000),
    }
    lo, hi = ranges.get(occupation, (25_000, 200_000))
    return random.randint(lo, hi)


def generate_record(seq: int) -> dict:
    """Generate a single synthetic customer record."""
    first = random.choice(FIRST_NAMES)
    last = random.choice(LAST_NAMES)
    full_name = f"{first} {last}"
    customer_id = f"CUST{seq:04d}"
    email = f"{first.lower()}.{last.lower()}{seq}@example.com"

    age = random.randint(18, 60)
    gender = random.choice(GENDERS)
    marital = random.choices(MARITAL_STATUSES, weights=MARITAL_WEIGHTS)[0]
    family_size = random.randint(1, 4)
    dependents = random.randint(0, min(4, family_size))

    occupation = random.choice(OCCUPATIONS)
    occ_type = random.choices(OCCUPATION_TYPES, weights=OCC_TYPE_WEIGHTS)[0]
    income = _income_for_occupation(occupation)

    kyc = random.choices(["Y", "N"], weights=[0.35, 0.65])[0]
    city = random.choice(CITIES)
    kids = random.randint(0, 3) if marital == "Married" else random.choices([0, 1], weights=[0.85, 0.15])[0]
    app_installed = random.choices(["Y", "N"], weights=[0.55, 0.45])[0]
    existing = random.choices(["Y", "N"], weights=[0.40, 0.60])[0]
    credit_score = random.randint(450, 720)
    social = random.choices(["Y", "N"], weights=[0.50, 0.50])[0]

    return {
        "customer_id": customer_id,
        "Full_name": full_name,
        "email": email,
        "Age": age,
        "Gender": gender,
        "Marital_Status": marital,
        "Family_Size": family_size,
        "Dependent count": dependents,
        "Occupation": occupation,
        "Occupation type": occ_type,
        "Monthly_Income": income,
        "KYC status": kyc,
        "City": city,
        "Kids_in_Household": kids,
        "App_Installed": app_installed,
        "Existing Customer": existing,
        "Credit score": credit_score,
        "Social_Media_Active": social,
    }


CSV_PATH = Path(__file__).resolve().parent.parent.parent / "customers.csv"

FIELDNAMES = [
    "customer_id", "Full_name", "email", "Age", "Gender",
    "Marital_Status", "Family_Size", "Dependent count", "Occupation",
    "Occupation type", "Monthly_Income", "KYC status", "City",
    "Kids_in_Household", "App_Installed", "Existing Customer",
    "Credit score", "Social_Media_Active",
]

NEW_COUNT = 5_000
START_SEQ = 5_001  # existing records are CUST0001-CUST5000


def write_to_csv(records: list[dict]) -> None:
    with open(CSV_PATH, "a", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDNAMES)
        writer.writerows(records)
    print(f"  Appended {len(records)} rows to {CSV_PATH.name}")


async def push_to_db(records: list[dict]) -> None:
    print("  Connecting to MongoDB…")
    await MongoDB.connect()
    db = MongoDB.get_db()
    repo = CustomerRepository(db)

    customers: list[Customer] = []
    for r in records:
        # Use model_validate so Pydantic resolves aliased field names correctly
        c = Customer.model_validate({
            "customer_id": r["customer_id"],
            "Full_name": r["Full_name"],
            "email": r["email"],
            "Age": r["Age"],
            "Gender": r["Gender"],
            "Marital_Status": r["Marital_Status"],
            "Family_Size": r["Family_Size"],
            "Dependent count": r["Dependent count"],
            "Occupation": r["Occupation"],
            "Occupation type": r["Occupation type"],
            "Monthly_Income": r["Monthly_Income"],
            "KYC status": r["KYC status"],
            "City": r["City"],
            "Kids_in_Household": r["Kids_in_Household"],
            "App_Installed": r["App_Installed"],
            "Existing Customer": r["Existing Customer"],
            "Credit score": r["Credit score"],
            "Social_Media_Active": r["Social_Media_Active"],
        })
        customers.append(c)

    upserted = await repo.sync_from_mock_api(customers)
    await MongoDB.disconnect()
    print(f"  Upserted {upserted} customer documents into MongoDB")


async def main() -> None:
    print(f"Generating {NEW_COUNT} new customer records (CUST{START_SEQ:04d}–CUST{START_SEQ + NEW_COUNT - 1:04d})…")
    records = [generate_record(i) for i in range(START_SEQ, START_SEQ + NEW_COUNT)]

    print("Writing to CSV…")
    write_to_csv(records)

    print("Pushing to MongoDB…")
    await push_to_db(records)

    print("\nDone!")


if __name__ == "__main__":
    asyncio.run(main())
