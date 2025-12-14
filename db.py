import os
import psycopg
import streamlit as st


def get_connection():
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        return None
    try:
        return psycopg.connect(db_url, sslmode='require')
    except Exception:
        return None


def get_cached_guide(dest, month):
    """Check if a guide already exists for this destination and month"""
    conn = get_connection()
    if not conn:
        return None
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT itinerary_text, created_at 
                FROM saved_itineraries 
                WHERE destination = %s 
                ORDER BY created_at DESC 
                LIMIT 1
            """, (f"{dest} [{month}]",))
            result = cur.fetchone()
            conn.close()
            return result
    except Exception:
        if conn:
            conn.close()
        return None


def save_itinerary(dest, month, text):
    conn = get_connection()
    if conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO saved_itineraries (destination, trip_days, itinerary_text)
                VALUES (%s, %s, %s)
            """, (f"{dest} [{month}]", 0, text))
            conn.commit()
        conn.close()
        try:
            st.toast("✅ Intel Saved!")
        except Exception:
            pass


def update_itinerary(trip_id, new_text):
    conn = get_connection()
    if conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE saved_itineraries SET itinerary_text = %s WHERE id = %s", (new_text, trip_id))
            conn.commit()
        conn.close()
        try:
            st.toast("✅ Updated!")
        except Exception:
            pass


def delete_itinerary(trip_id):
    conn = get_connection()
    if conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM saved_itineraries WHERE id = %s", (trip_id,))
            conn.commit()
        conn.close()
        try:
            st.toast("🗑️ Deleted!")
        except Exception:
            pass


def get_history():
    conn = get_connection()
    if not conn:
        return []
    with conn.cursor() as cur:
        cur.execute("SELECT id, destination, created_at FROM saved_itineraries ORDER BY created_at DESC")
        return cur.fetchall()


def get_itinerary_details(trip_id):
    conn = get_connection()
    if conn:
        with conn.cursor() as cur:
            cur.execute("SELECT destination, itinerary_text FROM saved_itineraries WHERE id = %s", (trip_id,))
            return cur.fetchone()
    return None


def save_chat_message(trip_id, role, content):
    conn = get_connection()
    if conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO trip_chats (trip_id, role, content)
                VALUES (%s, %s, %s)
            """, (trip_id, role, content))
            conn.commit()
        conn.close()


def load_chat_history(trip_id):
    conn = get_connection()
    if not conn:
        return []
    with conn.cursor() as cur:
        cur.execute("""
            SELECT role, content FROM trip_chats 
            WHERE trip_id = %s 
            ORDER BY created_at ASC
        """, (trip_id,))
        rows = cur.fetchall()
    return [{"role": r[0], "content": r[1]} for r in rows]
