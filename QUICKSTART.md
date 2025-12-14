# 🚀 Quick Start Guide

## What You Have

1. **Backend API** (`api.py`) - FastAPI server with REST endpoints
2. **Standalone App** (`index.html`) - Beautiful HTML/CSS/JS frontend
3. **Docker Setup** - Easy deployment

## Getting Started (5 minutes)

### Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 2: Set Up Environment

Create `.env` file in the project root:

```
GROQ_API_KEY=your_groq_key_here
TAVILY_API_KEY=your_tavily_key_here
MAPBOX_API_KEY=your_mapbox_key_here
DATABASE_URL=postgres://user:pass@localhost/db  # optional
```

### Step 3: Start the Backend

```bash
python -m uvicorn api:app --host 0.0.0.0 --port 8000 --reload
```

You should see:
```
Uvicorn running on http://0.0.0.0:8000
```

### Step 4: Open the Frontend

Option A - Local file:
```bash
# On macOS/Linux
open index.html

# Or open in your browser
http://127.0.0.1:8000
```

Option B - With Python server:
```bash
# In a new terminal
python -m http.server 3000
# Then visit: http://localhost:3000
```

### Step 5: Test It!

1. Enter: `Paris` and `March`
2. Click "Generate Guide"
3. Watch the magic happen! 🎉

## Integration with WordPress/Elementor

### Option 1: Embed as iframe

In your Elementor page, add a Custom HTML widget:

```html
<iframe 
  src="https://your-domain.com/travel-planner/index.html" 
  style="width:100%; height:800px; border:none; border-radius: 8px;"
  allow="accelerometer; autoplay; camera; gyroscope; picture-in-picture"
></iframe>
```

### Option 2: Embed with Custom Code

In WordPress admin → Elementor → Custom Code, add the HTML directly.

### Option 3: Host Separately

1. Deploy API on one server (e.g., DigitalOcean, Railway, Heroku)
2. Host `index.html` on another (e.g., GitHub Pages, your web server)
3. Update `API_URL` in the HTML to point to your backend

## Deployment

### Local Development
```bash
python -m uvicorn api:app --host 0.0.0.0 --port 8000 --reload
```

### Docker

Build:
```bash
docker build -t ai-travel-planner:latest .
```

Run:
```bash
docker run -p 8000:8000 \
  -e GROQ_API_KEY=your_key \
  -e TAVILY_API_KEY=your_key \
  ai-travel-planner:latest
```

### Cloud Deployment

**Google Cloud Run:**
```bash
gcloud run deploy travel-planner \
  --source . \
  --platform managed \
  --set-env-vars GROQ_API_KEY=***,TAVILY_API_KEY=***
```

**Railway or Heroku:** Push to GitHub and connect in their dashboard

## Customization

### Change API URL

Edit `index.html` line with:
```javascript
const API_URL = 'http://localhost:8000';  // Change this
```

To your deployed API:
```javascript
const API_URL = 'https://api.yourdomain.com';
```

### Update CORS Origins

If hosting on a different domain, edit `api.py`:

```python
CORS_ORIGINS = [
    "http://localhost:3000",
    "https://yourdomain.com",  # Add your domain
]
```

### Customize Styling

Edit the `<style>` section in `index.html` to match your brand.

## API Endpoints

All endpoints are `POST` unless otherwise noted.

### `/api/generate-intel`
Generate a travel guide for a destination

**Request:**
```json
{
  "destination": "Paris",
  "month": "March"
}
```

**Response:**
```json
{
  "destination": "Paris",
  "month": "March",
  "intel": "## 🍝 Gastronomy...",
  "locations": [
    {"name": "Eiffel Tower", "lat": 48.8584, "lon": 2.2945}
  ]
}
```

### `/api/chat`
Ask questions about a guide

**Request:**
```json
{
  "guide_text": "...",
  "user_query": "What are the best restaurants?"
}
```

### `/api/save-itinerary`
Save a guide to database (requires DATABASE_URL)

**Request:**
```json
{
  "destination": "Paris",
  "month": "March",
  "guide_text": "..."
}
```

### `GET /health`
Check API status

## Troubleshooting

### "API not reachable"

Make sure the backend is running:
```bash
python -m uvicorn api:app --host 0.0.0.0 --port 8000
```

Check it's working:
```bash
curl http://localhost:8000/health
```

### "Missing API keys"

Ensure `.env` file exists with:
- `GROQ_API_KEY`
- `TAVILY_API_KEY`

### "CORS error"

If hosting on a different domain, update `CORS_ORIGINS` in `api.py`

### Map not showing

Make sure you have valid coordinates in the guide. The app requires:
```
Location Name | latitude | longitude
```

## File Structure

```
ai-travel-planner/
├── api.py              # FastAPI backend
├── index.html          # Standalone frontend
├── ai.py               # AI logic
├── maps.py             # Map utilities
├── db.py               # Database
├── requirements.txt    # Dependencies
├── Dockerfile          # Container config
└── .env               # Your API keys
```

## Next Steps

1. ✅ Get API keys from Groq and Tavily
2. ✅ Create `.env` file with keys
3. ✅ Run backend: `python -m uvicorn api:app --port 8000`
4. ✅ Open `index.html` in browser
5. ✅ Test with "Paris" / "March"
6. 📦 Deploy to production
7. 🌐 Add to WordPress/Elementor

## Support

- API docs: http://localhost:8000/docs
- Alternative docs: http://localhost:8000/redoc

Enjoy! 🌍✈️
