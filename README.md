# 🌍 AI Travel Planner

An intelligent travel guide generator powered by AI that creates personalized destination guides with interactive maps, real-time web data, and exportable PDFs. Built as a portfolio project showcasing full-stack development with modern cloud technologies.

**Live Demo:** [https://jfor12.github.io/ai-travel-planner](https://jfor12.github.io/ai-travel-planner)  
**Backend API:** [https://ai-travel-planner-815578147202.europe-west1.run.app](https://ai-travel-planner-815578147202.europe-west1.run.app/health)

## ✨ Features

- **AI-Powered Travel Guides** - Generate comprehensive destination guides using Groq LLM (Llama 3.3)
- **Real-Time Web Search** - Integrates live data using Tavily search API
- **Interactive Maps** - Visualize locations with Leaflet.js mapping
- **Smart Caching** - Database-cached guides to reduce API costs
- **Rate Limiting** - IP-based protection (5 generations/hour)
- **Save & Export** - Store trips in PostgreSQL and export as PDF
- **My Trips Dashboard** - View, manage, and revisit saved itineraries
- **Responsive Design** - Beautiful animated gradient UI that works on all devices

## 🎯 Tech Stack

### Frontend
- **HTML/CSS/JavaScript** - Modern vanilla JS with async/await
- **Leaflet.js** - Interactive map rendering
- **GitHub Pages** - Static hosting

### Backend
- **FastAPI** - High-performance Python web framework
- **PostgreSQL** - Relational database (Supabase)
- **Google Cloud Run** - Serverless container deployment
- **Docker** - Containerization

### AI & APIs
- **Groq API** - Fast LLM inference (Llama 3.3 70B)
- **LangChain** - LLM orchestration framework
- **Tavily API** - Real-time web search
- **DuckDuckGo** - Fallback search provider

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
