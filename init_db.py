"""
Database initialization script for AI Travel Planner
Creates required tables if they don't exist. The API also does this on startup.
"""

from dotenv import load_dotenv

from db import ensure_schema

load_dotenv()


def init_database():
    """Initialize database tables"""
    try:
        ensure_schema()
        print("Database tables initialized successfully")
        return True
    except Exception as e:
        print(f"Error initializing database: {e}")
        return False


if __name__ == "__main__":
    init_database()
