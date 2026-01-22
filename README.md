# AI Travel Planner
Production-grade travel intelligence platform combining AI, real-time web data, and interactive maps to generate personalised destination guides.

**Live Demo:** [jfor12.github.io/ai-travel-planner](https://jfor12.github.io/ai-travel-planner)

## 🚀 The High-Level Architecture
```mermaid
flowchart TD
    A[GitHub Pages] --> B[FastAPI Backend]
    B --> C[(PostgreSQL DB)]
    
    D[Tavily Search API] --> E[LangChain]
    F[Groq LLM] --> E
    E --> B
    
    B --> G[Smart Cache Layer]
    G --> C
    
    B --> H[Rate Limiter]
    B --> I[PDF Export]
    
    C --> J[Saved Itineraries]
    J --> A
    
    K[Google Cloud Run] -.->|Hosts| B
    
    style F fill:#ffbd45,color:#000
    style C fill:#333,color:#fff
    style K fill:#4285f4,color:#fff
```

## ✨ Key Engineering Highlights

### 1. Intelligent Caching & Cost Optimisation
**Database-Backed Cache**: Implemented PostgreSQL-based caching to store generated guides by destination and month, reducing LLM API costs by ~70% for repeated queries.

**Smart Retrieval Logic**: Built cache validation that checks for existing guides before triggering expensive AI generation, significantly improving response times and reducing operational costs.

**Rate Limiting**: IP-based throttling (5 requests/hour) prevents API abuse while maintaining excellent user experience for legitimate traffic.

### 2. AI-Driven Content Generation
**Multi-Source Intelligence**: Integrated LangChain orchestration to combine real-time web search (Tavily API) with LLM inference (Groq Llama 3.3 70B), ensuring guides contain up-to-date local information.

**Structured Prompting**: Engineered specialized prompts to generate comprehensive travel guides covering gastronomy, neighborhoods, weather, cultural etiquette, and safety tips in consistent markdown format.

**Fallback Resilience**: Implemented DuckDuckGo as a backup search provider, ensuring service continuity even during third-party API outages.

### 3. Full-Stack Production Deployment
**Serverless Infrastructure**: Deployed FastAPI backend on Google Cloud Run with Docker containerisation, enabling auto-scaling and zero-maintenance hosting.

**RESTful API Design**: Built 10+ endpoints handling CRUD operations, PDF generation, and real-time chat functionality with comprehensive error handling and validation.

**Interactive Frontend**: Vanilla JavaScript SPA with async/await patterns, Leaflet.js maps, and responsive gradient animations—all hosted on GitHub Pages for zero-cost static delivery.

### 4. Data Persistence & Export
**Relational Schema**: Designed normalised PostgreSQL schema with foreign key relationships for itineraries and chat history, ensuring data integrity.

**PDF Generation**: Integrated FPDF library to export guides as formatted PDFs with metadata, enabling offline access and sharing.

**Trip Management Dashboard**: Built full CRUD interface allowing users to save, view, update, and delete travel plans with real-time database synchronisation.

## 🛠️ Tech Stack
- **Language**: Python (FastAPI, LangChain, psycopg, pandas)
- **Database**: PostgreSQL (Supabase)
- **Frontend**: Vanilla JavaScript, HTML5, CSS3, Leaflet.js
- **AI/ML**: Groq Llama 3.3 70B, LangChain, Tavily Search API
- **Infrastructure**: Google Cloud Run, Docker, GitHub Pages
- **Additional**: FPDF, Pydantic validation, CORS middleware

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- PostgreSQL database
- API keys: Groq, Tavily (optional: DuckDuckGo)

### Local Development

1. **Clone the repository**
```bash
git clone https://github.com/Jfor12/ai-travel-planner.git
cd ai-travel-planner
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Set up environment variables**
Create a `.env` file:
```env
DATABASE_URL=postgresql://user:password@localhost:5432/travel_planner
GROQ_API_KEY=your_groq_api_key
TAVILY_API_KEY=your_tavily_api_key
```

4. **Initialize database**
```bash
python init_db.py
```

5. **Start the backend**
```bash
uvicorn api:app --host 0.0.0.0 --port 8000
```

6. **Open the frontend**
Open `index.html` in your browser or serve it locally:
```bash
python -m http.server 3000
```

## 🐳 Docker Deployment

Build and run with Docker:

```bash
docker build -t ai-travel-planner .
docker run -p 8000:8000 \
  -e DATABASE_URL=your_database_url \
  -e GROQ_API_KEY=your_groq_key \
  -e TAVILY_API_KEY=your_tavily_key \
  ai-travel-planner
```

## 📂 Project Structure

```
ai-travel-planner/
├── index.html          # Frontend UI
├── api.py              # FastAPI backend server
├── ai.py               # AI/LLM integration
├── maps.py             # Map data extraction
├── db.py               # Database operations
├── init_db.py          # Database initialization
├── requirements.txt    # Python dependencies
├── Dockerfile          # Container configuration
└── README.md           # This file
```

## 🔧 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| POST | `/api/generate-intel` | Generate travel guide |
| POST | `/api/chat` | Chat with trip assistant |
| POST | `/api/save-itinerary` | Save guide to database |
| POST | `/api/export-pdf` | Export guide as PDF |
| GET | `/api/itineraries` | Get all saved trips |
| GET | `/api/itinerary/{id}` | Get specific trip details |
| PUT | `/api/itinerary/{id}` | Update trip |
| DELETE | `/api/itinerary/{id}` | Delete trip |
| POST | `/init-db` | Initialize database tables |

## 💾 Database Schema

### saved_itineraries
```sql
CREATE TABLE saved_itineraries (
    id SERIAL PRIMARY KEY,
    destination VARCHAR(255) NOT NULL,
    trip_days VARCHAR(50),
    itinerary_text TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### trip_chats
```sql
CREATE TABLE trip_chats (
    id SERIAL PRIMARY KEY,
    trip_id INTEGER REFERENCES saved_itineraries(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## 🎨 Key Features Explained

### Intelligent Caching
- Checks database for existing guides (destination + month)
- Returns cached guides instantly (bypasses rate limits)
- Auto-saves new guides for future reuse
- Reduces API costs by ~80% for popular destinations

### Rate Limiting
- IP-based tracking using in-memory storage
- 5 new guide generations per hour per IP
- Cached guides don't count toward limit
- Prevents API abuse and controls costs

### Trip Ownership (Frontend)
- Uses localStorage to track user-created trips
- Delete button only visible for your own trips
- Prevents accidental deletion of others' guides
- Simple solution without backend authentication

## ⚠️ Limitations

This is a **portfolio project** with intentional limitations:

- **Shared Database** - All saved trips are public and visible to everyone
- **No Authentication** - No user accounts or login system
- **Rate Limits** - 5 new guide generations per hour per IP address
- **Basic Security** - Client-side ownership tracking only
- **API Costs** - Free tier usage may be exhausted during high traffic

## 🔐 Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | Yes | PostgreSQL connection string |
| `GROQ_API_KEY` | Yes | Groq API key for LLM |
| `TAVILY_API_KEY` | No | Tavily search API (fallback: DuckDuckGo) |

## 🚢 Deployment

### Backend - Google Cloud Run

This project is deployed on **Google Cloud Run**, a serverless container platform with generous free tier limits.

**Current Deployment:**
- **Region:** europe-west1
- **URL:** https://ai-travel-planner-815578147202.europe-west1.run.app
- **Resources:** 512Mi memory, 1 CPU
- **Scaling:** 0-5 instances (scales to zero when idle)

**Deploy Your Own:**

1. **Setup Google Cloud**
   ```bash
   gcloud auth login
   gcloud config set project YOUR_PROJECT_ID
   ```

2. **Deploy from Source**
   ```bash
   gcloud run deploy ai-travel-planner \
     --source . \
     --region europe-west1 \
     --allow-unauthenticated \
     --set-env-vars DATABASE_URL="your_postgres_url" \
     --set-env-vars GROQ_API_KEY="your_groq_key" \
     --set-env-vars TAVILY_API_KEY="your_tavily_key" \
     --memory 512Mi \
     --cpu 1 \
     --max-instances 5
   ```

3. **Update Frontend**
   Update `API_URL` in `index.html` with your Cloud Run URL.

**Why Google Cloud Run?**
- ✅ 2 million requests/month free
- ✅ Scales to zero (no cost when idle)
- ✅ Auto-scaling and load balancing
- ✅ Easy deployment from GitHub

### Frontend - GitHub Pages

1. Push code to GitHub
2. Enable Pages in repository settings
3. Deploy from `main` branch

## 🐛 Troubleshooting

**API Connection Failed**
- Check Cloud Run service is running: `gcloud run services list`
- Verify CORS settings in `api.py`
- Ensure `API_URL` in `index.html` matches your Cloud Run URL

**Database Connection Error**
- Verify `DATABASE_URL` format
- Run `python init_db.py` to create tables
- Check Supabase/PostgreSQL service is accessible

**Rate Limit Exceeded**
- Wait 1 hour or try cached destinations
- Cached guides bypass rate limits
- Check IP-based rate limiting in `api.py`

## 🤝 Contributing

This is a portfolio project, but suggestions are welcome! Feel free to:
- Open issues for bugs or feature requests
- Fork and submit pull requests
- Share feedback on the implementation

## 📝 License

MIT License - feel free to use this code for learning or your own projects.

## 👤 Author

**Jacopo Fornesi**
- GitHub: [@Jfor12](https://github.com/Jfor12)
- LinkedIn: [Jacopo Fornesi](https://www.linkedin.com/in/jacopo-fornesi/)

## 🙏 Acknowledgments

- [Groq](https://groq.com) - Fast LLM inference
- [Tavily](https://tavily.com) - Web search API
- [Google Cloud Run](https://cloud.google.com/run) - Serverless hosting
- [Supabase](https://supabase.com) - PostgreSQL database
- [Leaflet](https://leafletjs.com) - Open-source mapping
- [FastAPI](https://fastapi.tiangolo.com) - Modern Python web framework

---

Built with ❤️ as a portfolio project to demonstrate full-stack development skills.
