#!/usr/bin/env python3
"""
Simple environment / connectivity checker for the ai-travel-planner app.
Run: python scripts/check_env.py
"""
import os
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

REQUIRED = [
    "DATABASE_URL",
    "GROQ_API_KEY",
    "TAVILY_API_KEY",
]

OPTIONAL = [
    "MAPBOX_API_KEY",
]

print("Checking environment variables:\n")
missing = []
for k in REQUIRED:
    v = os.getenv(k)
    print(f"- {k}: {'SET' if v else 'MISSING'}")
    if not v:
        missing.append(k)

for k in OPTIONAL:
    v = os.getenv(k)
    print(f"- {k}: {'SET' if v else 'not set (optional)'}")

if missing:
    print("\nERROR: Missing required environment variables:")
    for k in missing:
        print(f"  - {k}")
    print("\nPlease add them to your .env or export them in your shell. Exiting.")
    sys.exit(2)

# Test DB connection
print("\nTesting database connection...")
try:
    import psycopg
except Exception as e:
    print(f"Cannot import psycopg: {e}")
    print("Install dependencies: pip install -r requirements.txt")
    sys.exit(3)

db_url = os.getenv("DATABASE_URL")
try:
    conn = psycopg.connect(db_url, sslmode='require')
    cur = conn.cursor()
    cur.execute("SELECT version(), now();")
    r = cur.fetchone()
    print("- Connected successfully:", r)
    cur.close()
    conn.close()
except Exception as e:
    print("- Failed to connect to database:", e)
    print("Check DATABASE_URL, network access and credentials.")
    sys.exit(4)

print("\nAll checks passed.")
