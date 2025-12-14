"""
Database initialization script for AI Travel Planner
Creates required tables if they don't exist
"""

import os
import psycopg
from dotenv import load_dotenv

load_dotenv()

def init_database():
    """Initialize database tables"""
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        print("❌ DATABASE_URL not configured")
        return False
    
    try:
        conn = psycopg.connect(db_url, sslmode='require')
        with conn.cursor() as cur:
            # Create saved_itineraries table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS saved_itineraries (
                    id SERIAL PRIMARY KEY,
                    destination VARCHAR(255) NOT NULL,
                    trip_days INTEGER DEFAULT 0,
                    itinerary_text TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create trip_chats table for chat history
            cur.execute("""
                CREATE TABLE IF NOT EXISTS trip_chats (
                    id SERIAL PRIMARY KEY,
                    trip_id INTEGER REFERENCES saved_itineraries(id) ON DELETE CASCADE,
                    role VARCHAR(50) NOT NULL,
                    content TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.commit()
        conn.close()
        print("✅ Database tables initialized successfully")
        return True
    except Exception as e:
        print(f"❌ Error initializing database: {e}")
        return False

if __name__ == "__main__":
    init_database()
