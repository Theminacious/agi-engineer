#!/bin/bash
# Start Celery worker for background task processing

cd "$(dirname "$0")/backend"

# Activate virtual environment if exists
if [ -d "../venv" ]; then
    source ../venv/bin/activate
fi

echo "🚀 Starting Celery worker..."
celery -A app.tasks.celery_app worker --loglevel=info --concurrency=2
