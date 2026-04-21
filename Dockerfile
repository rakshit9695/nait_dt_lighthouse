# Backend container for Fly.io
FROM python:3.12-slim

# System libs needed by scipy/numpy/pyarrow wheels
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY backend ./backend
COPY scenarios ./scenarios
COPY assumptions.md ./assumptions.md
COPY README.md ./README.md

ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PORT=8000

EXPOSE 8000

CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT}"]
