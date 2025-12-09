# 🌍 AI Travel Planner

An interactive pre-trip intelligence generator: enter a destination and month, the app queries live sources, summarizes useful local advice, extracts key locations (with coordinates) and renders them on an attractive dark basemap. Export PDF briefings and persist guides to a Postgres database.

**Highlights**
- **Streamlit UI:** fast, single-file app for live demos and prototypes.
- **LLM-powered briefs:** Groq (Llama 3) via LangChain for concise local intelligence and extraction.
- **Map visualization:** PyDeck (Mapbox Dark when `MAPBOX_API_KEY` is provided) with labeled pins and offset labels to avoid overlap.
- **Persistence & export:** save guides to Postgres and download as PDF.

**Status:** Demo-ready. Includes a `Dockerfile` for containerized deployment.

## Table of contents

- Project overview
- Quick start (local)
- Docker usage
- Architecture & data flow
- Configuration (env vars)
- Limitations & known issues
- Security, privacy & cost considerations
- Testing, debugging & troubleshooting
- Next steps / optional changes

## Project overview

This tool is meant for building short, practical pre-trip briefings. It:

- Queries live web sources (via a small search tool) to gather context.
- Prompts an LLM to synthesize advice and a short coordinate list in a predictable format.
- Extracts coordinates and renders them on a PyDeck map with readable labels.
- Lets you save guides to a Postgres DB and download a printable PDF.

The app is intentionally opinionated (single-file Streamlit app) to be easy to read and adapt.

## Quick Start (Local)

1. Clone and install:

```bash
git clone https://github.com/your-username/ai-travel-planner.git
cd ai-travel-planner
pip install -r requirements.txt
```

2. Add secrets in a `.env` (do not commit):

```ini
GROQ_API_KEY=your_groq_key
MAPBOX_API_KEY=your_mapbox_key  # optional but recommended for Mapbox Dark
DATABASE_URL=postgres://user:pass@host/db  # optional for persistence
```

3. Run the app:

```bash
streamlit run app.py
```

Open `http://localhost:8501` in your browser.

## Docker (quick deploy)

Build and run the provided image:

```bash
docker build -t ai-travel-planner:latest .
docker run --rm -p 8501:8501 \
  -e GROQ_API_KEY="${GROQ_API_KEY}" \
  -e MAPBOX_API_KEY="${MAPBOX_API_KEY}" \
  -e DATABASE_URL="${DATABASE_URL}" \
  ai-travel-planner:latest
```

For production, prefer a managed Postgres (Supabase/Neon) and inject secrets via the hosting platform.

## Architecture & data flow

- User enters destination + month in Streamlit UI.
- The app runs a web search to gather short context notes.
- It calls Groq/Llama 3 with a structured prompt that requests: structured briefing + a small coordinate list in `Name | lat | lon` format.
- The app parses that coordinate block, builds a Pandas DataFrame and renders a PyDeck map.
- Optionally saves the generated text to Postgres and allows follow-up chat interactions (chat history persisted).

This flow is synchronous and optimized for prototyping; there is no background worker or job queue.

## Configuration (environment variables)

- `GROQ_API_KEY` (required for LLM features) — Groq API key.
- `MAPBOX_API_KEY` (optional) — Mapbox token. When provided Mapbox Dark is used; otherwise a public Carto dark basemap is used.
- `DATABASE_URL` (optional) — Postgres connection string for `save`, `list`, and `chat` persistence.

If `DATABASE_URL` is not set the app will still run but persistence features are disabled.

## Limitations & known issues

Please include the following caveats when showcasing or using this demo:

- **LLM hallucinations / factuality:** The LLM can produce incorrect or outdated advice. The app minimizes risk by feeding web search context, but ALWAYS verify important facts (visa rules, opening hours, entry requirements).
- **Coordinate accuracy:** Coordinates are extracted from LLM output using a regex; if the model returns malformed coordinates or miss-ordered values, they may be ignored. The map shows only entries validated as lat/lon within expected ranges.
- **Rate limits & cost:** Groq API usage may incur cost and rate limits. Keep an eye on API quotas, and consider caching results to reduce calls.
- **Privacy:** Any user-generated content sent to the LLM provider is subject to the provider's policies. Do not send sensitive personal data.
- **No background processing:** Long-running calls are synchronous in the Streamlit session; a slow LLM or network call will block the UI. Consider moving generation to an asynchronous worker for production.
- **DB schema assumptions:** The app expects simple `saved_itineraries` and `trip_chats` tables. If you reuse the DB, confirm the schema or migrate accordingly.
- **Mapbox dependency:** Without a valid `MAPBOX_API_KEY` some map features (custom styles) won't be available, but a public basemap is used as fallback.

## Security, privacy & cost considerations

- Do not commit `.env` or secrets to Git. Use platform secret stores in production.
- Limit API keys to specific services (where supported) and rotate keys regularly.
- Use managed DBs with network restrictions and SSL (Neon/Supabase recommended).
- Monitor LLM usage and set budgets/alerts with your provider.

## Testing, debugging & troubleshooting

- Run a local syntax check:

```bash
python -m py_compile app.py
```

- If the app fails to start, check `requirements.txt` for missing deps and confirm `MAPBOX_API_KEY`/`GROQ_API_KEY` env vars are set.
- To debug map issues, inspect the `temp_generated_full` value in the Streamlit interface (there is an expander showing raw output).

## Next steps / optional changes

- Create a "slim" branch that removes LLM and DB code for an ultra-light demo (smaller requirements and privacy-friendly).
- Split the monolithic `app.py` into modules (`ui.py`, `ai.py`, `maps.py`, `db.py`) for maintainability.
- Add caching for generated guides to reduce API calls and speed up repeat views.
- Add a simple GitHub Actions workflow to build and publish the Docker image on push.