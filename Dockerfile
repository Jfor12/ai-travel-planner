# Dockerfile for AI Travel Planner Backend
# Runs FastAPI server

FROM python:3.12-slim

WORKDIR /app

# psycopg[binary] ships prebuilt, so no compiler or system packages are needed
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app

RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

ENV PYTHONUNBUFFERED=1
ENV PORT=8000

EXPOSE 8000

# Render sets PORT; use it or default to 8000 for local runs
CMD python -m uvicorn api:app --host 0.0.0.0 --port ${PORT}
