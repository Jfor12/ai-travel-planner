import os
import sys

import psycopg
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# A throwaway local database. Never point this at production.
TEST_DB = os.environ.get("TEST_DATABASE_URL", "postgresql://postgres@localhost:5433/postgres?sslmode=require")
ADMIN_TOKEN = "test-admin-token"

os.environ["DATABASE_URL"] = TEST_DB
os.environ["GROQ_API_KEY"] = "test-groq"
os.environ["TAVILY_API_KEY"] = "test-tavily"
os.environ["ADMIN_TOKEN"] = ADMIN_TOKEN

import api  # noqa: E402

SCHEMA = [
    "DROP TABLE IF EXISTS trip_chats, saved_itineraries, guide_cache CASCADE",
    """CREATE TABLE saved_itineraries (
        id SERIAL PRIMARY KEY,
        destination VARCHAR(255) NOT NULL,
        trip_days INTEGER DEFAULT 0,
        itinerary_text TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""",
]


def sql(query, params=None):
    with psycopg.connect(TEST_DB) as conn, conn.cursor() as cur:
        cur.execute(query, params)
        return cur.fetchall() if cur.description else None


@pytest.fixture(autouse=True)
def fresh_state(monkeypatch):
    for statement in SCHEMA:
        sql(statement)
    if hasattr(api, "ensure_schema"):
        api.ensure_schema()
    for store in ("rate_limit_storage", "chat_rate_limit_storage"):
        if hasattr(api, store):
            getattr(api, store).clear()
    yield


@pytest.fixture
def fake_ai(monkeypatch):
    calls = {"generate": [], "chat": []}

    def fake_generate(destination, month, *args, **kwargs):
        calls["generate"].append({"destination": destination, "month": month, "args": args, "kwargs": kwargs})
        text = (f"## Neighborhoods\n* **Old Town:** Generated guide for {destination} in {month}.\n\n"
                "(---PAGE BREAK---)\n\n### COORDINATES\nOld Town | 41.9 | 12.5\n")
        return text, ["https://www.example.com/guide", "https://blog.example.org/food"]

    def fake_chat(guide_context, user_query, *args, **kwargs):
        calls["chat"].append({"guide": guide_context, "query": user_query, "args": args, "kwargs": kwargs})
        return "Answer from the guide."

    monkeypatch.setattr(api, "generate_guide", fake_generate)
    monkeypatch.setattr(api, "verify_locations", lambda destination, locations: locations)  # no network in tests
    monkeypatch.setattr(api, "run_chat_response", fake_chat)
    return calls


@pytest.fixture
def client():
    from fastapi.testclient import TestClient
    return TestClient(api.app)
