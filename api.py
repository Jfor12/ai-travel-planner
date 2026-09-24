"""
FastAPI backend for AI Travel Planner
Serves REST endpoints for AI generation, map data, and persistence
"""

import hmac
import logging
import os
import re
import time
from collections import defaultdict
from contextlib import asynccontextmanager
from typing import Dict, Optional

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel, Field, field_validator, model_validator

# Import core modules
from ai import generate_intel, run_chat_response
from maps import extract_map_data, create_pdf
from db import (
    cache_guide, ensure_schema, get_cached_guide, get_connection, get_history,
    get_itinerary_details, save_itinerary, update_itinerary, delete_itinerary,
)

# Load environment variables
load_dotenv()
log = logging.getLogger("travel-planner")


@asynccontextmanager
async def lifespan(_app):
    # Create the tables (including the new guide_cache) if they are missing.
    if os.getenv("DATABASE_URL"):
        try:
            ensure_schema()
        except Exception:
            log.exception("Could not initialise the database schema")
    yield


app = FastAPI(
    title="AI Travel Planner API",
    description="Generate travel intelligence and get location coordinates",
    version="1.1.0",
    lifespan=lifespan,
)

# The API has no cookies or sessions, so any origin may call it; write access
# to shared data is protected by the admin token instead.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# RATE LIMITING (in memory, per process)
# ============================================================================

# Key -> [timestamp, ...]. Each limit applies per IP and, as a backstop on API
# spend, across all visitors combined.
rate_limit_storage: Dict[str, list] = defaultdict(list)
chat_rate_limit_storage: Dict[str, list] = defaultdict(list)
RATE_LIMIT = 5  # new guide generations per IP per hour
GLOBAL_RATE_LIMIT = 60  # new guide generations per hour, all visitors
CHAT_RATE_LIMIT = 20  # questions per IP per hour
GLOBAL_CHAT_RATE_LIMIT = 300  # questions per hour, all visitors
RATE_WINDOW = 3600  # 1 hour in seconds


def _allow(storage: Dict[str, list], key: str, limit: int, now: float) -> bool:
    storage[key] = [ts for ts in storage[key] if now - ts < RATE_WINDOW]
    return len(storage[key]) < limit


def check_rate_limit(ip: str, storage=rate_limit_storage, limit=RATE_LIMIT, global_limit=GLOBAL_RATE_LIMIT) -> bool:
    """Returns True (and records the request) if both the IP and global limits allow it."""
    now = time.time()
    if not (_allow(storage, ip, limit, now) and _allow(storage, "*", global_limit, now)):
        return False
    storage[ip].append(now)
    storage["*"].append(now)
    return True


def client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


# ============================================================================
# ADMIN
# ============================================================================

def require_admin(x_admin_token: Optional[str] = Header(default=None)):
    """Editing, deleting and schema changes need the ADMIN_TOKEN secret.
    With no ADMIN_TOKEN configured, these endpoints are switched off."""
    expected = os.getenv("ADMIN_TOKEN")
    if not expected or not x_admin_token or not hmac.compare_digest(x_admin_token.encode(), expected.encode()):
        raise HTTPException(status_code=403, detail="Admin token required")


# ============================================================================
# PYDANTIC MODELS
# ============================================================================

MONTHS = ("January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December")
# Letters (any language), spaces and a little punctuation; nothing that can
# smuggle instructions into the prompt or markup into the page.
DESTINATION_RE = re.compile(r"^[^\W\d_](?:[^\W\d_]|[ '’.,-]){0,79}$")
MAX_GUIDE_CHARS = 50_000


def _destination(value: str) -> str:
    if any(ch in value for ch in "\r\n\t") or not value.isprintable():
        raise ValueError("Use a place name of up to 80 letters")
    value = re.sub(" +", " ", value).strip()
    if not DESTINATION_RE.match(value):
        raise ValueError("Use a place name of up to 80 letters")
    return value


def _month(value: str) -> str:
    value = value.strip().capitalize()
    if value not in MONTHS:
        raise ValueError("Use a month name such as March")
    return value


class TravelRequest(BaseModel):
    # Any other fields (such as the old model_name / temperature) are ignored:
    # the server decides which model to use.
    destination: str
    month: str

    _check_destination = field_validator("destination")(_destination)
    _check_month = field_validator("month")(_month)


class ChatRequest(BaseModel):
    """Ask about a saved trip (trip_id) or a generated guide (destination + month).
    The guide text always comes from the database, never from the client."""
    user_query: str = Field(min_length=1, max_length=500)
    trip_id: Optional[int] = None
    destination: Optional[str] = None
    month: Optional[str] = None

    @field_validator("destination")
    @classmethod
    def _check_destination(cls, v):
        return None if v is None else _destination(v)

    @field_validator("month")
    @classmethod
    def _check_month(cls, v):
        return None if v is None else _month(v)

    @model_validator(mode="after")
    def _needs_a_guide(self):
        if self.trip_id is None and not (self.destination and self.month):
            raise ValueError("Say which guide: trip_id, or destination and month")
        return self


class SaveRequest(BaseModel):
    """Saves the guide the server generated for this destination and month.
    Any guide_text sent by older clients is ignored."""
    destination: str
    month: str

    _check_destination = field_validator("destination")(_destination)
    _check_month = field_validator("month")(_month)


class PdfRequest(BaseModel):
    destination: str = Field(min_length=1, max_length=255)
    month: str = Field(default="", max_length=20)
    guide_text: str = Field(min_length=1, max_length=MAX_GUIDE_CHARS)


class UpdateRequest(BaseModel):
    guide_text: str = Field(min_length=1, max_length=MAX_GUIDE_CHARS)


def _server_error(what: str) -> HTTPException:
    # Details go to the server log, never to the browser.
    log.exception("%s failed", what)
    return HTTPException(status_code=500, detail=f"Something went wrong while trying to {what}. Please try again.")


def _locations(text: str):
    df = extract_map_data(text)
    if df.empty:
        return []
    return [{"name": row["name"], "lat": float(row["lat"]), "lon": float(row["lon"])} for _, row in df.iterrows()]


def _require_database():
    if not os.getenv("DATABASE_URL"):
        raise HTTPException(status_code=503, detail="Saved guides are not available right now")


# ============================================================================
# HEALTH CHECK & INITIALIZATION
# ============================================================================

@app.api_route("/health", methods=["GET", "POST", "HEAD"])
def health_check():
    """Check API health and keep Supabase active by pinging the database"""
    from datetime import datetime

    status_info = {"status": "healthy", "timestamp": datetime.now().isoformat()}

    # Ping database to keep Supabase active
    conn = get_connection()
    try:
        if conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
            status_info["database_status"] = "active"
        else:
            status_info["database_status"] = "unavailable"
    except Exception:
        log.exception("Health check database ping failed")
        status_info["database_status"] = "error"
    finally:
        if conn:
            conn.close()

    return status_info


@app.post("/api/init-db", dependencies=[Depends(require_admin)])
def initialize_database():
    """Initialize database tables (admin only)"""
    _require_database()
    try:
        ensure_schema()
    except Exception:
        raise _server_error("initialise the database")
    return {"success": True, "message": "Database tables initialized successfully"}


# ============================================================================
# TRAVEL INTELLIGENCE ENDPOINTS
# ============================================================================

@app.post("/api/generate-intel")
def generate_travel_intel(request: TravelRequest, http_request: Request):
    """
    Generate comprehensive travel intelligence for a destination.

    - **destination**: City or region (e.g., "Paris")
    - **month**: Month of travel (e.g., "March")

    Returns: Markdown-formatted intelligence with embedded coordinates
    Rate limited to 5 new guides per hour per IP
    """
    has_db = bool(os.getenv("DATABASE_URL"))

    # Check cache first to avoid unnecessary API calls
    if has_db:
        try:
            cached = get_cached_guide(request.destination, request.month)
        except Exception:
            log.exception("Cache lookup failed")
            cached = None
        if cached:
            return {"destination": request.destination, "month": request.month,
                    "intel": cached, "locations": _locations(cached), "cached": True}

    # Rate limit check (only for non-cached requests to save API costs)
    if not check_rate_limit(client_ip(http_request)):
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Maximum {RATE_LIMIT} new guide generations per hour. Try again later or search for a previously generated destination."
        )

    if not os.getenv("GROQ_API_KEY") or not os.getenv("TAVILY_API_KEY"):
        raise HTTPException(status_code=503, detail="Guide generation is not available right now")

    try:
        full_intel = "".join(generate_intel(request.destination, request.month))
    except Exception:
        raise _server_error("generate the guide")

    if has_db:
        try:
            cache_guide(request.destination, request.month, full_intel)
        except Exception:
            log.exception("Could not cache the guide")  # Don't fail the request

    return {"destination": request.destination, "month": request.month,
            "intel": full_intel, "locations": _locations(full_intel), "cached": False}


# ============================================================================
# CHAT ENDPOINTS
# ============================================================================

@app.post("/api/chat")
def chat_with_guide(request: ChatRequest, http_request: Request):
    """
    Ask a follow-up question about a saved trip or a generated guide.
    """
    _require_database()
    try:
        if request.trip_id is not None:
            row = get_itinerary_details(request.trip_id)
            guide = row[1] if row else None
        else:
            guide = get_cached_guide(request.destination, request.month)
    except Exception:
        raise _server_error("load the guide")
    if not guide:
        raise HTTPException(status_code=404, detail="Guide not found. Generate it first.")

    if not check_rate_limit(client_ip(http_request), chat_rate_limit_storage, CHAT_RATE_LIMIT, GLOBAL_CHAT_RATE_LIMIT):
        raise HTTPException(status_code=429, detail=f"You can ask up to {CHAT_RATE_LIMIT} questions an hour. Please try again later.")
    if not os.getenv("GROQ_API_KEY"):
        raise HTTPException(status_code=503, detail="Questions are not available right now")

    try:
        response = run_chat_response(guide, request.user_query)
    except Exception:
        raise _server_error("answer the question")
    return {"query": request.user_query, "response": response}


# ============================================================================
# PERSISTENCE ENDPOINTS
# ============================================================================

@app.post("/api/save-itinerary")
def save_guide(request: SaveRequest):
    """
    Save the guide the server generated for this destination and month to the
    shared list of trips.
    """
    _require_database()
    try:
        guide = get_cached_guide(request.destination, request.month)
        if not guide:
            raise HTTPException(status_code=404, detail="Generate this guide before saving it")
        trip_id = save_itinerary(request.destination, request.month, guide)
    except HTTPException:
        raise
    except Exception:
        raise _server_error("save the guide")
    return {"success": True, "message": "Guide saved successfully", "id": trip_id}


@app.post("/api/export-pdf")
def export_pdf(request: PdfRequest):
    """
    Export a travel guide as a PDF document.
    """
    try:
        pdf_bytes = create_pdf(request.destination, request.guide_text)
    except Exception:
        raise _server_error("create the PDF")

    stem = re.sub(r"[^A-Za-z0-9_-]+", "_", f"{request.destination}_{request.month}").strip("_") or "travel_guide"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{stem[:80]}.pdf"'},
    )


@app.get("/api/itineraries")
def get_all_itineraries():
    """
    Get the most recent saved itineraries.
    """
    _require_database()
    try:
        trips = get_history()
    except Exception:
        raise _server_error("load saved trips")
    return {
        "trips": [
            {"id": trip[0], "destination": trip[1], "created_at": trip[2].isoformat() if trip[2] else None}
            for trip in trips
        ]
    }


@app.get("/api/itinerary/{trip_id}")
def get_itinerary(trip_id: int):
    """
    Get details of a specific itinerary.
    """
    _require_database()
    try:
        details = get_itinerary_details(trip_id)
    except Exception:
        raise _server_error("load the trip")
    if not details:
        raise HTTPException(status_code=404, detail="Itinerary not found")
    return {"destination": details[0], "guide_text": details[1], "locations": _locations(details[1])}


@app.put("/api/itinerary/{trip_id}", dependencies=[Depends(require_admin)])
def update_trip(trip_id: int, request: UpdateRequest):
    """
    Update an existing itinerary (admin only).
    """
    _require_database()
    try:
        changed = update_itinerary(trip_id, request.guide_text)
    except Exception:
        raise _server_error("update the trip")
    if not changed:
        raise HTTPException(status_code=404, detail="Itinerary not found")
    return {"success": True, "message": "Itinerary updated successfully"}


@app.delete("/api/itinerary/{trip_id}", dependencies=[Depends(require_admin)])
def delete_trip(trip_id: int):
    """
    Delete an itinerary (admin only).
    """
    _require_database()
    try:
        changed = delete_itinerary(trip_id)
    except Exception:
        raise _server_error("delete the trip")
    if not changed:
        raise HTTPException(status_code=404, detail="Itinerary not found")
    return {"success": True, "message": "Itinerary deleted successfully"}


# ============================================================================
# ROOT ENDPOINT
# ============================================================================

@app.get("/")
def root():
    """API documentation and endpoint overview"""
    return {
        "name": "AI Travel Planner API",
        "version": "1.1.0",
        "docs": "/docs",
        "endpoints": {
            "health": "GET /health",
            "generate_intel": "POST /api/generate-intel",
            "chat": "POST /api/chat",
            "save_itinerary": "POST /api/save-itinerary",
            "export_pdf": "POST /api/export-pdf",
            "get_itineraries": "GET /api/itineraries",
            "get_itinerary": "GET /api/itinerary/{trip_id}",
            "update_itinerary": "PUT /api/itinerary/{trip_id} (admin)",
            "delete_itinerary": "DELETE /api/itinerary/{trip_id} (admin)",
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
