#!/bin/bash

# AGI Engineer V2 - Development Startup Script
# Starts both frontend and backend servers

set -e

PROJECT_ROOT="/Users/theminacious/Documents/mywork/agi-engineer"
BACKEND_DIR="$PROJECT_ROOT/backend"
FRONTEND_DIR="$PROJECT_ROOT/frontend"
PYTHON_CMD="$PROJECT_ROOT/venv/bin/python"
if [ ! -x "$PYTHON_CMD" ]; then
  # Fallback to system python if venv not present
  PYTHON_CMD="python3"
fi

echo "🚀 AGI Engineer V2 - Starting Development Servers"
echo "=================================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Kill any existing processes on ports 8000 and 3000
echo -e "${YELLOW}Cleaning up existing processes...${NC}"
lsof -ti:8000 2>/dev/null | xargs kill -9 2>/dev/null || true
lsof -ti:3000 2>/dev/null | xargs kill -9 2>/dev/null || true
lsof -ti:6379 2>/dev/null | xargs kill -9 2>/dev/null || true
sleep 1

# Start Redis (for background tasks)
echo -e "${YELLOW}Starting Redis (Port 6379)...${NC}"
if command -v redis-server &> /dev/null; then
  nohup redis-server --port 6379 --daemonize yes > "$PROJECT_ROOT/redis.log" 2>&1
  echo -e "${GREEN}✓ Redis started${NC}"
else
  echo -e "${YELLOW}⚠ Redis not found - install with: brew install redis${NC}"
  echo -e "${YELLOW}  Background tasks will be disabled${NC}"
fi

# Start Backend (Uvicorn)
echo -e "${YELLOW}Starting Backend (Port 8000) with Uvicorn...${NC}"
cd "$BACKEND_DIR"
nohub_out="$PROJECT_ROOT/backend.log"
nohup "$PYTHON_CMD" -m uvicorn app.main:app --reload --port 8000 > "$nohub_out" 2>&1 &
BACKEND_PID=$!
echo -e "${GREEN}✓ Backend started (PID: $BACKEND_PID)${NC}"

# Start Frontend
echo -e "${YELLOW}Starting Frontend (Port 3000)...${NC}"
cd "$FRONTEND_DIR"
export NEXT_PUBLIC_API_URL="http://localhost:8000"
nohup npm run dev > "$PROJECT_ROOT/frontend.log" 2>&1 &
FRONTEND_PID=$!
echo -e "${GREEN}✓ Frontend started (PID: $FRONTEND_PID)${NC}"

# Start Celery Worker (optional, for background tasks)
if command -v redis-server &> /dev/null && pgrep -x redis-server > /dev/null; then
  echo -e "${YELLOW}Starting Celery Worker...${NC}"
  cd "$BACKEND_DIR"
  nohup "$PYTHON_CMD" -m celery -A app.tasks.celery_app worker --loglevel=info --concurrency=2 > "$PROJECT_ROOT/celery.log" 2>&1 &
  CELERY_PID=$!
  echo -e "${GREEN}✓ Celery Worker started (PID: $CELERY_PID)${NC}"
fi

# Wait for servers to start
echo -e "${YELLOW}Waiting for servers to start...${NC}"
sleep 5

# Check if servers are running
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
  echo -e "${GREEN}✓ Backend is responding${NC}"
else
  echo -e "${RED}✗ Backend failed to start - check backend.log${NC}"
  cat "$PROJECT_ROOT/backend.log" | tail -20
fi

if curl -s http://localhost:3000 > /dev/null 2>&1; then
  echo -e "${GREEN}✓ Frontend is responding${NC}"
else
  echo -e "${RED}✗ Frontend failed to start - check frontend.log${NC}"
  cat "$PROJECT_ROOT/frontend.log" | tail -20
fi

echo ""
echo -e "${GREEN}=================================================="
echo -e "✅ AGI Engineer V2 is Running!"
echo -e "=================================================${NC}"
echo ""
echo -e "Frontend: ${GREEN}http://localhost:3000${NC}"
echo -e "Backend:  ${GREEN}http://localhost:8000${NC}"
echo -e "API Docs: ${GREEN}http://localhost:8000/docs${NC}"
echo -e "Redis:    ${GREEN}localhost:6379${NC}"
echo ""
echo -e "Logs:"
echo -e "  Backend:  tail -f $PROJECT_ROOT/backend.log"
echo -e "  Frontend: tail -f $PROJECT_ROOT/frontend.log"
if [ -n "$CELERY_PID" ]; then
  echo -e "  Celery:   tail -f $PROJECT_ROOT/celery.log"
fi
echo ""
if [ -n "$CELERY_PID" ]; then
  echo -e "To stop servers: kill $BACKEND_PID $FRONTEND_PID $CELERY_PID"
else
  echo -e "To stop servers: kill $BACKEND_PID $FRONTEND_PID"
fi
echo ""

# Keep script running
wait
