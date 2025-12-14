"""
FastAPI backend for AI Travel Planner
Serves REST endpoints for AI generation, map data, and persistence
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel
from typing import Optional, List, Dict
import os
import time
from collections import defaultdict
from dotenv import load_dotenv

# Import core modules
from ai import generate_intel, run_chat_response, generate_place_summary
from maps import extract_map_data, create_pdf
from db import save_itinerary, get_connection, get_history, get_itinerary_details, update_itinerary, delete_itinerary, get_cached_guide

# Load environment variables
load_dotenv()

app = FastAPI(
    title="AI Travel Planner API",
    description="Generate travel intelligence and get location coordinates",
    version="1.0.0"
)

# Enable CORS - Allow all origins for now (restrict in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for testing
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiting storage (IP -> [timestamp, timestamp, ...])
rate_limit_storage: Dict[str, list] = defaultdict(list)
RATE_LIMIT = 5  # requests per hour
RATE_WINDOW = 3600  # 1 hour in seconds

def check_rate_limit(ip: str) -> bool:
    """Check if IP has exceeded rate limit. Returns True if allowed."""
    now = time.time()
    
    # Clean old timestamps
    rate_limit_storage[ip] = [ts for ts in rate_limit_storage[ip] if now - ts < RATE_WINDOW]
    
    # Check if under limit
    if len(rate_limit_storage[ip]) >= RATE_LIMIT:
        return False
    
    # Add current request
    rate_limit_storage[ip].append(now)
    return True


# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class TravelRequest(BaseModel):
    destination: str
    month: str
    model_name: Optional[str] = None
    temperature: Optional[float] = None


class ChatRequest(BaseModel):
    guide_text: str
    user_query: str
    model_name: Optional[str] = None
    temperature: Optional[float] = None


class SaveRequest(BaseModel):
    destination: str
    month: str
    guide_text: str


class LocationData(BaseModel):
    name: str
    lat: float
    lon: float


# ============================================================================
# HEALTH CHECK & INITIALIZATION
# ============================================================================

@app.get("/health")
def health_check():
    """Check API health and environment configuration"""
    return {
        "status": "healthy",
        "has_groq_key": bool(os.getenv("GROQ_API_KEY")),
        "has_tavily_key": bool(os.getenv("TAVILY_API_KEY")),
        "has_database": bool(os.getenv("DATABASE_URL")),
    }


@app.post("/api/init-db")
def initialize_database():
    """Initialize database tables (admin endpoint)"""
    try:
        if not os.getenv("DATABASE_URL"):
            raise HTTPException(status_code=500, detail="DATABASE_URL not configured")
        
        import psycopg
        conn = psycopg.connect(os.getenv("DATABASE_URL"), sslmode='require')
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
        
        return {
            "success": True,
            "message": "Database tables initialized successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# TRAVEL INTELLIGENCE ENDPOINTS
# ============================================================================

@app.post("/api/generate-intel")
async def generate_travel_intel(request: TravelRequest, http_request: Request):
    """
    Generate comprehensive travel intelligence for a destination.
    
    - **destination**: City or region (e.g., "Paris")
    - **month**: Month of travel (e.g., "March")
    
    Returns: Markdown-formatted intelligence with embedded coordinates
    Rate limited to 5 requests per hour per IP
    """
    try:
        # Get client IP
        client_ip = http_request.client.host if http_request.client else "unknown"
        
        # Check cache first to avoid unnecessary API calls
        if os.getenv("DATABASE_URL"):
            cached = get_cached_guide(request.destination, request.month)
            if cached:
                full_intel = cached[0]
                
                # Extract coordinates from cached intel
                df = extract_map_data(full_intel)
                locations = []
                if not df.empty:
                    for _, row in df.iterrows():
                        locations.append({
                            "name": row["name"],
                            "lat": float(row["lat"]),
                            "lon": float(row["lon"])
                        })
                
                return {
                    "destination": request.destination,
                    "month": request.month,
                    "intel": full_intel,
                    "locations": locations,
                    "cached": True
                }
        
        # Rate limit check (only for non-cached requests to save API costs)
        if not check_rate_limit(client_ip):
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded. Maximum {RATE_LIMIT} new guide generations per hour. Try again later or search for a previously generated destination."
            )
        
        # Validate API keys
        if not os.getenv("GROQ_API_KEY") or not os.getenv("TAVILY_API_KEY"):
            raise HTTPException(
                status_code=500,
                detail="API keys not configured. Set GROQ_API_KEY and TAVILY_API_KEY."
            )
        
        # Generate intelligence stream (only if not cached)
        intel_parts = []
        for chunk in generate_intel(
            request.destination,
            request.month,
            model_name=request.model_name,
            temperature=request.temperature
        ):
            intel_parts.append(chunk)
        
        full_intel = "".join(intel_parts)
        
        # Auto-save to cache for future requests
        if os.getenv("DATABASE_URL"):
            try:
                save_itinerary(request.destination, request.month, full_intel)
            except:
                pass  # Don't fail if save fails
        
        # Extract coordinates from the intel
        df = extract_map_data(full_intel)
        locations = []
        if not df.empty:
            for _, row in df.iterrows():
                locations.append({
                    "name": row["name"],
                    "lat": float(row["lat"]),
                    "lon": float(row["lon"])
                })
        
        return {
            "destination": request.destination,
            "month": request.month,
            "intel": full_intel,
            "locations": locations,
            "cached": False
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# CHAT ENDPOINTS
# ============================================================================

@app.post("/api/chat")
async def chat_with_guide(request: ChatRequest):
    """
    Ask a follow-up question about a travel guide.
    """
    try:
        if not os.getenv("GROQ_API_KEY"):
            raise HTTPException(status_code=500, detail="GROQ_API_KEY not configured")
        
        response = run_chat_response(
            request.guide_text,
            request.user_query,
            model_name=request.model_name,
            temperature=request.temperature
        )
        
        return {
            "query": request.user_query,
            "response": response,
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# PERSISTENCE ENDPOINTS
# ============================================================================

@app.post("/api/save-itinerary")
async def save_guide(request: SaveRequest):
    """
    Save a travel guide to the database.
    """
    try:
        if not os.getenv("DATABASE_URL"):
            raise HTTPException(status_code=500, detail="DATABASE_URL not configured")
        
        save_itinerary(request.destination, request.month, request.guide_text)
        
        return {
            "success": True,
            "message": "Guide saved successfully",
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/export-pdf")
async def export_pdf(request: SaveRequest):
    """
    Export a travel guide as a PDF document.
    """
    try:
        pdf_bytes = create_pdf(request.destination, request.guide_text)
        
        filename = f"{request.destination.replace(' ', '_')}_{request.month}.pdf"
        
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/itineraries")
async def get_all_itineraries():
    """
    Get list of all saved itineraries.
    """
    try:
        if not os.getenv("DATABASE_URL"):
            raise HTTPException(status_code=500, detail="DATABASE_URL not configured")
        
        trips = get_history()
        return {
            "trips": [
                {
                    "id": trip[0],
                    "destination": trip[1],
                    "created_at": trip[2].isoformat() if trip[2] else None
                }
                for trip in trips
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/itinerary/{trip_id}")
async def get_itinerary(trip_id: int):
    """
    Get details of a specific itinerary.
    """
    try:
        if not os.getenv("DATABASE_URL"):
            raise HTTPException(status_code=500, detail="DATABASE_URL not configured")
        
        details = get_itinerary_details(trip_id)
        if not details:
            raise HTTPException(status_code=404, detail="Itinerary not found")
        
        # Extract locations from the guide text
        locations_df = extract_map_data(details[1])
        
        # Convert DataFrame to array of objects
        locations = []
        if not locations_df.empty:
            locations = locations_df.to_dict('records')
        
        return {
            "destination": details[0],
            "guide_text": details[1],
            "locations": locations
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/itinerary/{trip_id}")
async def update_trip(trip_id: int, request: SaveRequest):
    """
    Update an existing itinerary.
    """
    try:
        if not os.getenv("DATABASE_URL"):
            raise HTTPException(status_code=500, detail="DATABASE_URL not configured")
        
        update_itinerary(trip_id, request.guide_text)
        
        return {
            "success": True,
            "message": "Itinerary updated successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/itinerary/{trip_id}")
async def delete_trip(trip_id: int):
    """
    Delete an itinerary.
    """
    try:
        if not os.getenv("DATABASE_URL"):
            raise HTTPException(status_code=500, detail="DATABASE_URL not configured")
        
        delete_itinerary(trip_id)
        
        return {
            "success": True,
            "message": "Itinerary deleted successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ROOT ENDPOINT
# ============================================================================

@app.get("/")
def root():
    """API documentation and endpoint overview"""
    return {
        "name": "AI Travel Planner API",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": {
            "health": "GET /health",
            "generate_intel": "POST /api/generate-intel",
            "chat": "POST /api/chat",
            "save_itinerary": "POST /api/save-itinerary",
            "export_pdf": "POST /api/export-pdf",
            "get_itineraries": "GET /api/itineraries",
            "get_itinerary": "GET /api/itinerary/{trip_id}",
            "update_itinerary": "PUT /api/itinerary/{trip_id}",
            "delete_itinerary": "DELETE /api/itinerary/{trip_id}",
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
