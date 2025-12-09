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
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_ENABLECORS=false

EXPOSE 8501

# Run the app
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
