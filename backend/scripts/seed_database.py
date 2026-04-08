"""CLI script to seed the MongoDB database with mock data."""

import asyncio
import sys
from pathlib import Path

# Ensure app package is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db.mongodb import MongoDB
from app.db.migrations.seed_data import seed_all


async def main() -> None:
    print("Connecting to MongoDB...")
    await MongoDB.connect()
    db = MongoDB.get_db()

    print("Seeding database...")
    summary = await seed_all(db)

    print("\nSeed complete!")
    for collection, count in summary.items():
        print(f"  {collection}: {count} documents")

    await MongoDB.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
