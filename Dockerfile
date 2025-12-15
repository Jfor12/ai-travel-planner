# Dockerfile for AI Travel Planner Backend
# Runs FastAPI server

FROM python:3.12-slim

# Install minimal system deps
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       build-essential \
       libpq-dev \
       gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app

RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

ENV PYTHONUNBUFFERED=1
ENV PORT=8000

EXPOSE 8000

# Cloud Run sets PORT env variable, use it or default to 8000
CMD python -m uvicorn api:app --host 0.0.0.0 --port ${PORT}
