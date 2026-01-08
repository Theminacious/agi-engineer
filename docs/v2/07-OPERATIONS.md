# V2 Operations & Maintenance Guide

> **Running AGI Engineer V2 in Production**  
> Monitoring, maintenance, incident response, and runbooks

---

## 📑 Table of Contents

1. [Operational Overview](#operational-overview)
2. [Monitoring Dashboard](#monitoring-dashboard)
3. [Daily Operations](#daily-operations)
4. [Maintenance Tasks](#maintenance-tasks)
5. [Incident Response](#incident-response)
6. [Performance Tuning](#performance-tuning)
7. [Capacity Planning](#capacity-planning)

---

## Operational Overview

### Architecture Components

```
┌─────────────────────────────────────────────┐
│           GitHub                            │
│    (Event source, OAuth, verification)      │
└────────────────────┬────────────────────────┘
                     │ Webhooks
        ┌────────────▼────────────┐
        │  Webhook Handler        │
        │  (FastAPI Endpoint)     │
        └────────────┬────────────┘
                     │
    ┌────────────────┴───────────────┐
    │                                │
┌───▼──────┐                  ┌─────▼────┐
│ Analysis │◄─── Queues ────►│  Redis   │
│ Engine   │                  │ (Cache)  │
│ (V1)     │                  └──────────┘
└───┬──────┘
    │
┌───▼──────────────────┐
│  PostgreSQL          │
│  - Installations     │
│  - Runs              │
│  - Results           │
│  - Users             │
└──────────────────────┘

┌──────────────────────┐
│  Next.js Frontend    │
│  - Dashboard         │
│  - Runs              │
│  - Analytics         │
└──────────────────────┘
```

### SLA & Availability

```
Production SLA:
- Availability: 99.9% (< 45 min downtime/month)
- Response time: < 200ms (p95)
- API availability: 99.95%
- Database: 99.99%

Maintenance Windows:
- Weekly: Tuesday 2-3 AM UTC
- Monthly: Last Saturday 2-4 AM UTC
- Notice: 48 hours advance
```

---

## Monitoring Dashboard

### Key Metrics to Track

#### Application Metrics

```
1. Request Metrics
   - Requests/minute
   - Response time (p50, p95, p99)
   - Error rate
   - 4xx/5xx responses

2. Analysis Metrics
   - Analyses/minute
   - Average analysis time
   - Success rate
   - Queue depth

3. Database Metrics
   - Query time (p50, p95, p99)
   - Connection pool usage
   - Slow queries (> 1s)
   - Transactions/minute

4. Infrastructure Metrics
   - CPU usage
   - Memory usage
   - Disk usage
   - Network I/O
```

### Setting Up Prometheus

```yaml
# prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'agi-engineer-backend'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
    
  - job_name: 'postgres'
    static_configs:
      - targets: ['localhost:9187']
    
  - job_name: 'redis'
    static_configs:
      - targets: ['localhost:9121']

alerting:
  alertmanagers:
    - static_configs:
        - targets: ['localhost:9093']
```

### Grafana Dashboard Setup

```bash
# Import dashboard JSON
curl -X POST http://localhost:3000/api/dashboards/db \
  -H "Authorization: Bearer $GRAFANA_TOKEN" \
  -H "Content-Type: application/json" \
  -d @dashboard.json
```

Key panels to create:
- Request latency (line chart)
- Error rate (gauge)
- Analysis success rate (gauge)
- Database connections (line chart)
- Queue depth (bar chart)
- CPU/Memory (area chart)

### Alert Rules

```yaml
# alerts.yml
groups:
  - name: agi_engineer
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
        for: 5m
        annotations:
          summary: "High error rate detected"

      - alert: SlowResponse
        expr: histogram_quantile(0.95, http_request_duration_seconds) > 1
        for: 5m
        annotations:
          summary: "API response time > 1s"

      - alert: DatabaseDown
        expr: pg_up == 0
        for: 1m
        annotations:
          summary: "PostgreSQL is down"

      - alert: HighQueueDepth
        expr: analysis_queue_depth > 100
        for: 10m
        annotations:
          summary: "Analysis queue backing up"

      - alert: DiskSpaceWarning
        expr: node_filesystem_avail_bytes < 5368709120  # 5GB
        annotations:
          summary: "Low disk space"
```

---

## Daily Operations

### Morning Checklist

```bash
#!/bin/bash
# daily_check.sh

echo "🔍 Daily Operations Check"
echo "=========================="

# 1. Check service health
echo "✓ Checking service health..."
curl -s http://localhost:8000/health | jq .
curl -s http://localhost:3000 > /dev/null && echo "Frontend: OK" || echo "Frontend: DOWN"

# 2. Check error logs
echo "\n✓ Checking error logs (last 10 mins)..."
docker logs --since 10m agi-engineer-backend 2>&1 | grep -i error || echo "No errors"

# 3. Check database
echo "\n✓ Checking database..."
psql -U admin -h localhost agi_engineer -c "SELECT count(*) FROM analysis_run" || echo "DB: DOWN"

# 4. Check disk space
echo "\n✓ Checking disk space..."
df -h | grep -E "^/dev" | awk '{if($5 > 80) print "WARNING: " $6 " is " $5 " full"}'

# 5. Check backup status
echo "\n✓ Checking last backup..."
ls -lh /backups/ | tail -1

# 6. Summary
echo "\n✅ Daily check complete"
```

### Monitoring Commands

```bash
# Real-time service status
docker-compose -f docker-compose.prod.yml ps

# View logs
docker-compose -f docker-compose.prod.yml logs -f --tail=100

# Check resource usage
docker stats

# Database connections
psql -c "SELECT datname, count(*) FROM pg_stat_activity GROUP BY datname"

# Queue depth
redis-cli LLEN analysis_queue

# Recent errors
docker logs agi-engineer-backend --since 1h 2>&1 | grep -i error
```

### Hourly Checks

```python
# scripts/hourly_check.py
import requests
import time
from datetime import datetime

def hourly_health_check():
    """Run health checks every hour"""
    
    checks = {
        'API Health': 'http://localhost:8000/health',
        'Frontend': 'http://localhost:3000',
        'Database': 'http://localhost:8000/api/health/db',
    }
    
    results = {}
    for name, url in checks.items():
        try:
            response = requests.get(url, timeout=5)
            results[name] = '✅' if response.status_code == 200 else '❌'
        except Exception as e:
            results[name] = f'❌ {str(e)}'
    
    # Log results
    timestamp = datetime.now().isoformat()
    print(f"[{timestamp}] Health Check:")
    for name, status in results.items():
        print(f"  {status} {name}")
    
    # Alert if any failed
    if any('❌' in str(v) for v in results.values()):
        send_alert(f"Health check failed: {results}")

if __name__ == '__main__':
    while True:
        hourly_health_check()
        time.sleep(3600)  # Wait 1 hour
```

---

## Maintenance Tasks

### Database Maintenance

```sql
-- Daily: Analyze tables (updates statistics)
ANALYZE;

-- Weekly: Reindex (maintains index efficiency)
REINDEX DATABASE agi_engineer;

-- Monthly: Full VACUUM (reclaims space)
VACUUM FULL ANALYZE;

-- Clean old analysis results (older than 90 days)
DELETE FROM analysis_result 
WHERE run_id IN (
  SELECT id FROM analysis_run 
  WHERE created_at < NOW() - INTERVAL '90 days'
);

-- Archive old runs to separate table
INSERT INTO analysis_run_archive 
SELECT * FROM analysis_run 
WHERE created_at < NOW() - INTERVAL '1 year';

DELETE FROM analysis_run 
WHERE created_at < NOW() - INTERVAL '1 year';

-- Check table size
SELECT schemaname, tablename, 
  pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) 
FROM pg_tables 
WHERE schemaname != 'pg_catalog' 
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

### Cache Maintenance

```bash
# Redis maintenance
redis-cli INFO memory              # Check memory usage
redis-cli DBSIZE                   # Check key count
redis-cli FLUSHDB --ASYNC         # Clear cache (non-blocking)

# Clear specific patterns
redis-cli KEYS "analysis:*" | xargs redis-cli DEL

# Monitor Redis
redis-cli MONITOR
```

### Log Rotation

```yaml
# /etc/docker/daemon.json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "100m",
    "max-file": "3"
  }
}
```

### Backup Procedures

```bash
# Daily backup (runs at 2 AM)
0 2 * * * /usr/local/bin/backup.sh

# Backup script
#!/bin/bash
# /usr/local/bin/backup.sh

BACKUP_DIR="/backups"
DB_NAME="agi_engineer"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Database backup
pg_dump $DB_NAME | gzip > $BACKUP_DIR/db_$TIMESTAMP.sql.gz

# Upload to S3
aws s3 cp $BACKUP_DIR/db_$TIMESTAMP.sql.gz \
  s3://agi-engineer-backups/

# Keep only last 30 days locally
find $BACKUP_DIR -name "db_*.sql.gz" -mtime +30 -delete

echo "Backup complete: $TIMESTAMP"
```

### Certificate Renewal

```bash
# Auto-renew Let's Encrypt certificates
# Add to crontab (runs monthly)
0 0 1 * * certbot renew --quiet --post-hook "docker-compose restart nginx"

# Manual renewal
certbot renew
docker-compose restart nginx

# Check certificate expiration
openssl x509 -enddate -noout -in /etc/letsencrypt/live/agi-engineer.com/cert.pem
```

---

## Incident Response

### Incident Severity Levels

```
SEV-1 (Critical):
  - Complete service outage
  - Data loss
  - Security breach
  Response time: < 5 minutes

SEV-2 (High):
  - Partial service degradation
  - High error rate (> 5%)
  - Major feature broken
  Response time: < 30 minutes

SEV-3 (Medium):
  - Minor feature broken
  - Performance degradation
  - Low error rate (< 1%)
  Response time: < 2 hours

SEV-4 (Low):
  - Non-critical feature broken
  - Cosmetic issues
  Response time: < 1 day
```

### Incident Playbook

#### API Errors Spike (SEV-2)

```bash
#!/bin/bash
# Detect and respond to error spike

ERROR_RATE=$(curl -s http://localhost:8000/metrics | grep http_requests_total | grep 5xx | awk '{print $2}')

if (( $(echo "$ERROR_RATE > 0.05" | bc -l) )); then
  echo "🚨 High error rate: $ERROR_RATE"
  
  # 1. Check logs
  docker logs agi-engineer-backend --tail=100
  
  # 2. Check database
  psql -c "SELECT count(*) FROM analysis_run WHERE status='error'"
  
  # 3. Check memory/CPU
  docker stats agi-engineer-backend --no-stream
  
  # 4. Restart if needed
  docker-compose restart agi-engineer-backend
  
  # 5. Alert team
  curl -X POST https://hooks.slack.com/services/... \
    -d "{\"text\": \"🚨 API Error Spike: $ERROR_RATE\"}"
fi
```

#### Database Down (SEV-1)

```bash
#!/bin/bash
# Database recovery playbook

echo "🚨 DATABASE DOWN - Recovery in progress"

# 1. Check if container is running
docker-compose ps postgres

# 2. Check logs
docker logs agi-engineer-postgres

# 3. Try restart
docker-compose restart postgres
sleep 30

# 4. Verify connectivity
psql -U admin -h localhost agi_engineer -c "SELECT 1" && echo "✅ Connected" || echo "❌ Failed"

# 5. If restart fails, restore from backup
if [ $? -ne 0 ]; then
  echo "Attempting restore from backup..."
  
  # Restore from latest backup
  LATEST_BACKUP=$(ls -t /backups/db_*.sql.gz | head -1)
  gunzip -c $LATEST_BACKUP | psql -U admin -h localhost agi_engineer
  
  # Verify
  psql -U admin -h localhost agi_engineer -c "SELECT count(*) FROM analysis_run"
fi

echo "Recovery complete"
```

#### Memory Leak (SEV-2)

```bash
#!/bin/bash
# Monitor and handle memory leak

MEMORY_THRESHOLD=2000  # MB

while true; do
  MEMORY=$(docker stats agi-engineer-backend --no-stream | tail -1 | awk '{print $4}' | sed 's/MiB//')
  
  if (( $(echo "$MEMORY > $MEMORY_THRESHOLD" | bc -l) )); then
    echo "⚠️ High memory usage: ${MEMORY}MB"
    
    # 1. Check for memory leak
    curl http://localhost:8000/debug/memory
    
    # 2. Restart service (graceful)
    docker-compose restart agi-engineer-backend
    
    # 3. Alert
    curl -X POST https://hooks.slack.com/services/... \
      -d "{\"text\": \"⚠️ Memory leak detected: ${MEMORY}MB, restarted\"}"
  fi
  
  sleep 300  # Check every 5 minutes
done
```

### Escalation Path

```
1. Pagerduty Alert (automatic)
   ↓
2. On-call engineer notified
   ↓
3. If not resolved in 15min → Senior engineer
   ↓
4. If not resolved in 30min → Team lead
   ↓
5. If not resolved in 60min → Manager + Team lead
```

### Post-Incident Review

```markdown
# Incident Report Template

## Incident Summary
- **Date**: 2026-01-09
- **Duration**: 45 minutes
- **Severity**: SEV-2
- **Impact**: API response time degraded 10x

## Timeline
- 12:00 - Error spike detected
- 12:05 - Team alerted
- 12:10 - Root cause identified (cache miss)
- 12:15 - Cache restarted
- 12:45 - Service normalized

## Root Cause
Redis connection pool exhausted due to slow queries

## Resolution
1. Restarted Redis
2. Optimized slow query
3. Added connection pooling limits

## Prevention
- [ ] Implement query timeout
- [ ] Add cache monitoring
- [ ] Improve alerting
- [ ] Add load testing to CI

## Action Items
- Owner: John | Due: 2026-01-11 | Query optimization
- Owner: Jane | Due: 2026-01-12 | Enhanced monitoring
```

---

## Performance Tuning

### Database Query Optimization

```sql
-- Find slow queries
SELECT query, calls, total_time, mean_time 
FROM pg_stat_statements 
WHERE mean_time > 100 
ORDER BY mean_time DESC;

-- Add missing indexes
EXPLAIN ANALYZE 
SELECT * FROM analysis_result WHERE severity='error';

-- Create indexes
CREATE INDEX idx_result_severity ON analysis_result(severity);
CREATE INDEX idx_run_status ON analysis_run(status);

-- Update statistics
ANALYZE;
```

### Connection Pooling Tuning

```python
# backend/app/db/__init__.py
engine = create_engine(
    settings.database_url,
    pool_size=20,           # Connections to keep open
    max_overflow=40,        # Additional connections when needed
    pool_recycle=3600,      # Recycle connections every hour
    pool_pre_ping=True,     # Test connection before use
)
```

### Redis Optimization

```bash
# Monitor Redis performance
redis-cli INFO stats
redis-cli --latency-history

# Tune Redis
# /etc/redis/redis.conf
maxmemory 512mb
maxmemory-policy allkeys-lru

# Monitor memory
redis-cli INFO memory
```

### API Response Time

```python
# Add request timing middleware
from fastapi import Request
import time

@app.middleware("http")
async def add_timing_header(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = time.time() - start
    response.headers["X-Process-Time"] = str(duration)
    return response
```

---

## Capacity Planning

### Current Capacity

```
Baseline (current load):
- Requests/sec: 50
- Analysis/hour: 200
- DB connections: 5-10
- Memory usage: 500MB
- Disk usage: 50GB

Headroom:
- API: 100 req/sec (50% of limit)
- Analysis: 500/hour (40% of limit)
- Memory: 2GB (4x current)
- Disk: 100GB (2x current)
```

### Growth Projections

```
Q1 2026:
- 10x user growth expected
- Need to scale database
- Add read replicas

Q2 2026:
- 100x user growth possible
- Multi-region deployment
- Advanced caching layer

Recommended actions:
- Monitor trends monthly
- Load test before scaling
- Plan infrastructure 3 months ahead
```

### Scaling Strategy

```
Phase 1: Vertical Scaling (current)
- Increase server size
- Upgrade database
- Cost: Low, Effort: Low

Phase 2: Horizontal Scaling (Q1)
- Load balancer
- Multiple backends
- Read replicas
- Cost: Medium, Effort: Medium

Phase 3: Global Scaling (Q2)
- CDN for frontend
- Multi-region database
- Edge computing
- Cost: High, Effort: High
```

---

## Contact Information

```
On-Call Schedule:
- Monday-Friday: Engineering team
- Weekends: Senior engineer rotation
- Holidays: Designated rotation

Emergency Contacts:
- Slack: #incident-response
- PagerDuty: agi-engineer-oncall
- Phone: [Emergency number]

Escalation:
- Level 1: On-call engineer
- Level 2: Engineering lead
- Level 3: VP Engineering
```

---

**Version**: 2.0  
**Phase**: Operations & Maintenance  
**Status**: Complete ✅  
**Last Updated**: January 9, 2026
