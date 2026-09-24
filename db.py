import os

import psycopg

# guide_cache holds guides the server generated itself. Only /api/generate-intel
# writes to it, so nothing a visitor sends can change what other visitors are served.
SCHEMA = [
    """
    CREATE TABLE IF NOT EXISTS saved_itineraries (
        id SERIAL PRIMARY KEY,
        destination VARCHAR(255) NOT NULL,
        trip_days INTEGER DEFAULT 0,
        itinerary_text TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS trip_chats (
        id SERIAL PRIMARY KEY,
        trip_id INTEGER REFERENCES saved_itineraries(id) ON DELETE CASCADE,
        role VARCHAR(50) NOT NULL,
        content TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS guide_cache (
        destination_key VARCHAR(100) NOT NULL,
        month VARCHAR(9) NOT NULL,
        guide_text TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (destination_key, month)
    )
    """,
]


def _connect():
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        return None
    # Supabase needs TLS; a URL that sets its own sslmode (e.g. local tests) wins.
    options = {} if 'sslmode=' in db_url else {'sslmode': 'require'}
    return psycopg.connect(db_url, connect_timeout=10, **options)


def get_connection():
    """A raw connection or None. Callers must close it."""
    try:
        return _connect()
    except Exception:
        return None


def _run(query, params=None, fetch=None):
    """Run one statement on a fresh connection that is always closed."""
    conn = _connect()
    if conn is None:
        raise RuntimeError('DATABASE_URL not configured')
    with conn:  # commits on success, rolls back on error, then closes
        with conn.cursor() as cur:
            cur.execute(query, params)
            if fetch == 'one':
                return cur.fetchone()
            if fetch == 'all':
                return cur.fetchall()
            return cur.rowcount


def ensure_schema():
    conn = _connect()
    if conn is None:
        raise RuntimeError('DATABASE_URL not configured')
    with conn:
        with conn.cursor() as cur:
            for statement in SCHEMA:
                cur.execute(statement)


def destination_key(destination):
    return ' '.join(destination.split()).lower()


# --- Server-generated guide cache ----------------------------------------------------

def cache_max_age_days():
    try:
        return max(1, int(os.getenv('CACHE_MAX_AGE_DAYS', '90')))
    except ValueError:
        return 90


def get_cached_guide(destination, month):
    """The cached guide, unless it's older than CACHE_MAX_AGE_DAYS (default 90):
    scams, transport and restaurants change, so old guides are regenerated."""
    row = _run(
        """
        SELECT guide_text FROM guide_cache
        WHERE destination_key = %s AND month = %s
          AND created_at > CURRENT_TIMESTAMP - make_interval(days => %s)
        """,
        (destination_key(destination), month, cache_max_age_days()), fetch='one')
    return row[0] if row else None


def cache_guide(destination, month, text):
    _run(
        """
        INSERT INTO guide_cache (destination_key, month, guide_text) VALUES (%s, %s, %s)
        ON CONFLICT (destination_key, month)
        DO UPDATE SET guide_text = EXCLUDED.guide_text, created_at = CURRENT_TIMESTAMP
        """,
        (destination_key(destination), month, text))


# --- Shared saved trips --------------------------------------------------------------------

def save_itinerary(dest, month, text):
    row = _run(
        "INSERT INTO saved_itineraries (destination, trip_days, itinerary_text) VALUES (%s, %s, %s) RETURNING id",
        (f"{dest} [{month}]", 0, text), fetch='one')
    return row[0]


def update_itinerary(trip_id, new_text):
    return _run("UPDATE saved_itineraries SET itinerary_text = %s WHERE id = %s", (new_text, trip_id))


def delete_itinerary(trip_id):
    return _run("DELETE FROM saved_itineraries WHERE id = %s", (trip_id,))


def get_history(limit=200):
    return _run(
        "SELECT id, destination, created_at FROM saved_itineraries ORDER BY created_at DESC LIMIT %s",
        (limit,), fetch='all')


def get_itinerary_details(trip_id):
    return _run("SELECT destination, itinerary_text FROM saved_itineraries WHERE id = %s", (trip_id,), fetch='one')
