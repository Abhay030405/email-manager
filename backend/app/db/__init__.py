"""Database package."""

from app.db.mongodb import MongoDB, get_database

__all__ = ["MongoDB", "get_database"]
