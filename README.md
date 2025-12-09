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
 # 🌍 AI Travel Planner

An interactive pre-trip intelligence generator: enter a destination and month, the app queries live sources, summarizes useful local advice, extracts key locations (with coordinates) and renders them on an attractive dark basemap. Export PDF briefings and persist guides to a Postgres database.

**Highlights**
- **Streamlit UI:** modularized into maintainable components (`app.py`, `ui.py`, `ai.py`, `maps.py`, `db.py`).
- **LLM-powered briefs:** Groq (Llama 3) via LangChain for concise local intelligence and extraction.
- **Map visualization:** PyDeck (Mapbox Dark when `MAPBOX_API_KEY` is provided) with labeled pins and offset labels to avoid overlap.
- **Persistence & export:** save guides to Postgres and download as PDF.

**Status:** Demo-ready. Includes a `Dockerfile` for containerized deployment.

## Table of contents

- Project overview
- Quick start (local)
- Docker usage
- Architecture & modules
- Configuration (env vars)
- Database schema
- Limitations & known issues
- Security, privacy & cost considerations
- Testing, debugging & troubleshooting
- Next steps / optional changes

## Project overview

This tool is meant for building short, practical pre-trip briefings. It:

- Queries live web sources (via a small search tool) to gather context.
- Prompts an LLM to synthesize advice and a short coordinate list in a predictable format.
- Extracts coordinates and renders them on a PyDeck map with readable labels.
- Lets you save the generated text to Postgres and download a printable PDF.

## Project modules

- `app.py`: small delegator that loads `.env` (if present) and starts the UI.
- `ui.py`: Streamlit UI — sidebar, pages, widget wiring and user interactions.
- `ai.py`: AI interactions and prompt/LLM wiring (generate_intel, chat helpers).
- `maps.py`: map rendering, coordinate extraction, PDF creation and helper URLs.
- `db.py`: database connection and persistence helpers (save/load itineraries and chats).
- `scripts/check_env.py`: helper script to verify required env vars and test DB connectivity.
- `tests/`: comprehensive test suite with unit and integration tests.
- `run_tests.sh`: convenient test runner script with multiple testing options.

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
TAVILY_API_KEY=your_tavily_key
MAPBOX_API_KEY=your_mapbox_key  # optional but recommended for Mapbox Dark
DATABASE_URL=postgres://user:pass@host/db  # optional for persistence
```

3. (Optional) Validate environment and DB connectivity:

```bash
python scripts/check_env.py
```

4. Run the app:

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
  -e TAVILY_API_KEY="${TAVILY_API_KEY}" \
  -e MAPBOX_API_KEY="${MAPBOX_API_KEY}" \
  -e DATABASE_URL="${DATABASE_URL}" \
  ai-travel-planner:latest
```

For production, prefer a managed Postgres (Supabase/Neon) and inject secrets via the hosting platform.

## Architecture & modules

- User enters destination + month in `ui.py`.
- `ai.py` assembles search context and prompts the LLM for a structured briefing and small coordinate block (`Name | lat | lon`).
- `maps.py` extracts coordinates, builds a Pandas DataFrame and renders a PyDeck map with labeled pins.
- `db.py` persists guides and chat messages when `DATABASE_URL` is provided.

This flow is synchronous and optimized for prototyping; there is no background worker or job queue.

## Configuration (environment variables)

- `GROQ_API_KEY` (required for LLM features) — Groq API key.
- `TAVILY_API_KEY` (required) — API key used by the small search tool.
- `MAPBOX_API_KEY` (optional) — Mapbox token. When provided Mapbox Dark is used; otherwise a public Carto dark basemap is used.
- `DATABASE_URL` (optional) — Postgres connection string for `save`, `list`, and `chat` persistence.

The app will load `.env` automatically (via `python-dotenv`) when `app.py` starts. If a variable is missing, features that depend on it will be disabled or will display an error.

## Database schema

The app expects two simple tables. Example SQL to create them:

```sql
CREATE TABLE saved_itineraries (
  id SERIAL PRIMARY KEY,
  destination TEXT NOT NULL,
  trip_days INTEGER DEFAULT 0,
  itinerary_text TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE trip_chats (
  id SERIAL PRIMARY KEY,
  trip_id INTEGER REFERENCES saved_itineraries(id) ON DELETE CASCADE,
  role TEXT,
  content TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);
```

You can run these statements with `psql` or any Postgres client. I can add a `migrations/` file and an init script if you'd like automated setup.

## Limitations & known issues

- **LLM hallucinations / factuality:** The LLM can produce incorrect or outdated advice. The app minimizes risk by feeding web search context, but ALWAYS verify important facts (visa rules, opening hours, entry requirements).
- **Coordinate accuracy:** Coordinates are extracted from LLM output using a regex; malformed coordinates may be ignored.
- **Rate limits & cost:** Groq API usage may incur cost and rate limits. Consider caching results to reduce calls.
- **Privacy:** Any user-generated content sent to the LLM provider is subject to the provider's policies. Do not send sensitive personal data.
- **No background processing:** Long-running calls are synchronous in the Streamlit session.

## Security, privacy & cost considerations

- Do not commit `.env` or secrets to Git. Use platform secret stores in production.
- Limit API keys to specific services (where supported) and rotate keys regularly.
- Use managed DBs with network restrictions and SSL (Neon/Supabase recommended).

## Testing, debugging & troubleshooting

### Comprehensive Test Suite

This project includes a professional testing suite with unit tests, integration tests, and CI/CD automation.

**Test Coverage:**
- ✅ Unit tests for all core modules (ai.py, db.py, maps.py)
- ✅ Integration tests for end-to-end workflows
- ✅ Performance and security tests
- ✅ Automated CI/CD pipeline with GitHub Actions
- ✅ Code coverage reporting

**Running Tests:**

```bash
# Quick test run
./run_tests.sh all

# Run with coverage report
./run_tests.sh coverage

# Run specific test categories
./run_tests.sh unit           # Unit tests only
./run_tests.sh integration    # Integration tests only
./run_tests.sh quick          # Skip slow tests

# Code quality checks
./run_tests.sh lint           # Linting and formatting
./run_tests.sh security       # Security scans

# View coverage report
./run_tests.sh show-coverage
```

**Manual pytest commands:**

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html --cov-report=term-missing

# Run specific test file
pytest tests/test_ai.py -v

# Run specific test class
pytest tests/test_ai.py::TestGenerateIntel -v

# Run with detailed output
pytest -v -s
```

**CI/CD Pipeline:**

Every push and pull request triggers:
- Test suite on Python 3.9, 3.10, 3.11
- Code quality checks (flake8, black, isort)
- Security scans (safety, bandit)
- Coverage reporting to Codecov
- Docker image build validation

See `.github/workflows/ci-cd.yml` for full pipeline configuration.

**Test Documentation:**

For detailed testing documentation, see [docs/TESTING.md](docs/TESTING.md)

### Environment Validation

Validate environment and DB: `python scripts/check_env.py`.

### Debugging

- Run a local syntax check:

```bash
python -m py_compile app.py ui.py ai.py db.py maps.py
```

- If the app fails to start, check `requirements.txt` for missing deps and confirm `MAPBOX_API_KEY`/`GROQ_API_KEY`/`TAVILY_API_KEY` env vars are set.
- To debug map issues, inspect the `temp_generated_full` value in the Streamlit interface (there is an expander showing raw output).

### Common Issues

**Import Errors:** Ensure all dependencies are installed: `pip install -r requirements.txt`

**Test Failures:** Tests use mocked dependencies. If tests fail:
1. Check pytest is installed: `pip install pytest pytest-cov pytest-mock`
2. Verify you're in the project root
3. Check test logs for specific errors

**Coverage Not Generated:** Run `./run_tests.sh coverage` or `pytest --cov=.`

## Next steps / optional changes

- Add automated DB migration (`migrations/` and an init script).
- Add caching for generated guides to reduce API calls and speed up repeat views.
- ~Add a GitHub Actions workflow to build and publish the Docker image on push.~ ✅ **Done - CI/CD pipeline implemented**
- Expand test coverage to include UI component testing
- Add performance benchmarking suite
- Implement load testing for production readiness

## Testing & Code Quality

This project demonstrates professional software engineering practices:

- **80%+ test coverage** across all modules
- **Automated CI/CD** with GitHub Actions
- **Type hints and documentation** for maintainability
- **Security scanning** (bandit, safety)
- **Code quality checks** (flake8, black, isort)
- **Mocked external dependencies** for reliable testing
- **Integration tests** for end-to-end workflows

Run `./run_tests.sh` to see all testing options.
