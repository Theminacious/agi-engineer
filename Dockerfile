FROM python:3.11-slim

RUN apt-get update && apt-get install -y git curl && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    npm install -g eslint@8 @typescript-eslint/parser@6 @typescript-eslint/eslint-plugin@6 && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./backend/
COPY agent/ ./agent/

WORKDIR /app/backend

ENV PYTHONPATH=/app

CMD uvicorn app.main:app --host 0.0.0.0 --port $PORT
