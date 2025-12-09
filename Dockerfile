# Dockerfile for AI Travel Planner (Streamlit app)
# Uses a slim Python base, installs system deps for Postgres bindings, installs Python deps,
# copies the app, and runs Streamlit in headless mode.

FROM python:3.12-slim

# Install minimal system deps required for some Python packages (psycopg, build tools)
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       build-essential \
       libpq-dev \
       gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy dependency manifest first so layer caches can be reused
COPY requirements.txt /app/

# Install Python deps
RUN pip install --no-cache-dir -r requirements.txt

# Copy app sources
COPY . /app

# Create a non-root user and switch to them
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# Streamlit environment defaults for container usage
ENV PYTHONUNBUFFERED=1 \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_SERVER_ENABLECORS=false

# Cloud Run supplies a runtime PORT environment variable. Use 8080 by default
EXPOSE 8080

# Use shell form so the runtime $PORT (set by Cloud Run) is honored. Falls back to 8080.
CMD ["sh", "-c", "streamlit run app.py --server.port=${PORT:-8080} --server.address=0.0.0.0"]
