# Phase 5: Advanced Features - Real-time Processing

## Overview
Phase 5 implements real-time webhook processing with background task queues, WebSocket support for live updates, and the foundation for AI-powered features.

## Completed Features

### 1. Background Task Processing ✅
**Implementation:**
- **Celery Integration**: Distributed task queue using Celery + Redis
- **Analysis Tasks**: Asynchronous code analysis processing
- **Worker Management**: Dedicated worker process for background jobs

**Files Created:**
- `backend/app/tasks/__init__.py` - Task module exports
- `backend/app/tasks/celery_app.py` - Celery configuration
- `backend/app/tasks/analysis_tasks.py` - Analysis task definitions
- `start-celery.sh` - Celery worker startup script

**Key Features:**
```python
@celery_app.task
def run_code_analysis(run_id: int) -> dict:
    # 1. Clone repository from GitHub
    # 2. Run AGI Engineer analysis
    # 3. Store results in database
    # 4. Send WebSocket updates in real-time
```

**Benefits:**
- Non-blocking webhook responses (instant 200 OK)
- Parallel analysis processing (configurable concurrency)
- Automatic retry on failures
- Task monitoring and metrics

### 2. Real-time WebSocket Updates ✅
**Implementation:**
- **WebSocket Router**: Live connection management
- **Run Status Updates**: Real-time progress notifications
- **Dashboard Updates**: Live stats and run list updates

**Files Created:**
- `backend/app/routers/websockets.py` - WebSocket endpoints

**Endpoints:**
- `ws://localhost:8000/ws/run/{run_id}` - Run-specific updates
- `ws://localhost:8000/ws/dashboard/{user_id}` - Dashboard live feed

**Usage:**
```typescript
// Frontend WebSocket connection
const ws = new WebSocket('ws://localhost:8000/ws/run/123')
ws.onmessage = (event) => {
  const update = JSON.parse(event.data)
  // { type: "status_change", status: "completed", total_results: 28 }
}
```

### 3. Enhanced Webhook Processing ✅
**Updates:**
- Webhooks now queue background tasks instead of blocking
- Immediate response with `run_id` for tracking
- Support for push, pull_request, and review events

**Modified Files:**
- `backend/app/routers/webhooks.py` - Added Celery task dispatch

**Flow:**
```
GitHub Webhook → FastAPI → Create DB Run → Queue Celery Task → Return 200 OK
                                                ↓
                            Background Worker → Clone Repo → Analyze → Update DB
                                                ↓
                            WebSocket Broadcast → Live Update to Frontend
```

### 4. Infrastructure Updates ✅
**Docker Compose:**
- Added Redis service for Celery broker
- Added Celery worker service
- Updated environment variables

**Dev Script:**
- Auto-start Redis on macOS (if installed)
- Auto-start Celery worker
- Enhanced logging (redis.log, celery.log)

**Dependencies:**
- `celery>=5.3.0` - Task queue
- `redis>=5.0.0` - Message broker
- `websockets>=12.0` - WebSocket support

## Architecture

### Background Task Flow
```
┌─────────────────┐
│  GitHub Webhook │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  FastAPI Router │
└────────┬────────┘
         │ Create Run
         ▼
┌─────────────────┐      ┌─────────────┐
│    Database     │◄─────┤ Celery Task │
└────────┬────────┘      └──────┬──────┘
         │                       │
         │                       │ WebSocket
         ▼                       ▼
┌─────────────────┐      ┌─────────────┐
│  Frontend API   │◄─────┤  WebSocket  │
└─────────────────┘      └─────────────┘
```

### WebSocket Connection Management
```python
class ConnectionManager:
    active_connections: Dict[int, Set[WebSocket]]
    
    async def send_run_update(run_id, message):
        # Broadcast to all clients watching this run
    
    async def send_dashboard_update(user_id, message):
        # Broadcast to user's dashboard clients
```

## Configuration

### Environment Variables
```bash
# Redis Configuration
REDIS_URL=redis://localhost:6379/0

# Celery Configuration (automatic via REDIS_URL)
# - Broker: redis://localhost:6379/0
# - Backend: redis://localhost:6379/0
```

### Celery Settings
```python
celery_app.conf.update(
    task_serializer="json",
    timezone="UTC",
    task_track_started=True,
    task_time_limit=3600,  # 1 hour max
    worker_prefetch_multiplier=1,
)
```

## Development Workflow

### Starting Services
```bash
# Option 1: Use enhanced dev script (auto-starts all services)
./start-dev.sh

# Option 2: Manual startup
redis-server --port 6379 &
cd backend && uvicorn app.main:app --reload &
cd backend && celery -A app.tasks.celery_app worker --loglevel=info &
cd frontend && npm run dev &
```

### Monitoring Tasks
```bash
# View Celery worker logs
tail -f celery.log

# Monitor Redis
redis-cli monitor

# Check task queue length
redis-cli llen celery
```

## Testing

### Manual Webhook Test
```bash
# Trigger webhook (creates run and queues task)
curl -X POST http://localhost:8000/webhooks/github \
  -H "Content-Type: application/json" \
  -H "X-GitHub-Event: push" \
  -d '{
    "repository": {"full_name": "user/repo", "id": 123},
    "ref": "refs/heads/main",
    "after": "abc123"
  }'

# Check run status
curl http://localhost:8000/api/runs
```

### WebSocket Test
```javascript
// Browser console
const ws = new WebSocket('ws://localhost:8000/ws/run/1')
ws.onmessage = (e) => console.log(JSON.parse(e.data))
```

## Next Features (Remaining in Phase 5)

### 2. AI-Powered Auto-Fix Suggestions
- [ ] Integrate Groq/GPT-4 for fix generation
- [ ] Add "Auto-fix" button to analysis results
- [ ] Generate code patches with diffs
- [ ] One-click PR creation with fixes

### 3. Team Collaboration
- [ ] Multi-user workspace support
- [ ] Role-based access control (admin/developer/viewer)
- [ ] Team activity feed
- [ ] Shared repository management

### 4. Usage Analytics Dashboard
- [ ] Issue trends over time (charts with recharts)
- [ ] Most common issue categories
- [ ] Repository health scores
- [ ] Fix rate metrics

### 5. Billing & Subscription Tiers
- [ ] Free/Pro/Enterprise plans
- [ ] Usage limits and tracking
- [ ] Stripe integration
- [ ] Billing portal and invoices

## Troubleshooting

### Redis Not Starting
```bash
# macOS: Install Redis
brew install redis
brew services start redis

# Linux: Install Redis
sudo apt-get install redis-server
sudo systemctl start redis
```

### Celery Worker Not Connecting
```bash
# Check Redis is running
redis-cli ping  # Should return "PONG"

# Check Redis URL in config
echo $REDIS_URL

# Start worker with debug logs
celery -A app.tasks.celery_app worker --loglevel=debug
```

### WebSocket Connection Failed
```bash
# Check WebSocket endpoint in browser DevTools
# Ensure FastAPI server is running
# Verify CORS settings allow WebSocket connections
```

## Performance Considerations

### Scaling
- **Worker Concurrency**: Adjust `--concurrency=2` based on CPU cores
- **Redis Connection Pool**: Configure max connections in production
- **WebSocket Limits**: Monitor active connections, implement reconnection logic

### Optimization
- **Task Routing**: Route different task types to specialized workers
- **Result Expiration**: Configure Celery to expire old task results
- **Database Indexing**: Add indexes on `run_id` and `status` columns

## Security

### Production Checklist
- [ ] Use Redis password authentication
- [ ] Enable TLS for Redis connections
- [ ] Implement WebSocket authentication (JWT validation)
- [ ] Rate limit webhook endpoints
- [ ] Validate WebSocket message payloads

## Metrics & Monitoring

### Key Metrics
- **Task Queue Length**: Number of pending tasks
- **Task Processing Time**: Average duration per analysis
- **WebSocket Connections**: Active real-time clients
- **Task Failure Rate**: Failed vs. successful tasks

### Recommended Tools
- **Flower**: Celery monitoring dashboard
  ```bash
  pip install flower
  celery -A app.tasks.celery_app flower
  # Visit http://localhost:5555
  ```
- **Redis Commander**: Redis GUI
  ```bash
  npm install -g redis-commander
  redis-commander
  ```

## Documentation

### API Documentation
- WebSocket endpoints now available at `/docs` (FastAPI auto-docs)
- Real-time event types documented in code comments

### Integration Guide
See `GITHUB_OAUTH_SETUP.md` for:
- Webhook configuration
- GitHub App permissions
- Callback URL setup

---

**Status**: ✅ Real-time Processing Complete (Feature 1 of 5)
**Next**: AI-Powered Auto-Fix Suggestions
