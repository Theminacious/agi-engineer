"""API Documentation for V2.0 Phase 2"""

# V2.0 Phase 2: GitHub OAuth & Webhooks

## Overview

Phase 2 adds GitHub App OAuth authentication and webhook event handling. This allows users to install the app, and enables real-time code analysis triggers.

## New Endpoints

### OAuth Endpoints

#### `GET /oauth/authorize`
Initiate GitHub OAuth flow.

**Response:**
```json
{
  "authorization_url": "https://github.com/login/oauth/authorize?client_id=...",
  "state": "uuid-for-csrf-protection"
}
```

**Usage:**
```bash
curl http://localhost:8000/oauth/authorize
```

---

#### `GET /oauth/callback?code=CODE&state=STATE`
GitHub OAuth callback handler.

**Query Parameters:**
- `code` - GitHub authorization code
- `state` - CSRF state token

**Response:**
```json
{
  "token": "jwt-token",
  "user": "github-username",
  "installation_id": 1,
  "message": "Successfully authenticated with GitHub"
}
```

**Usage:**
```bash
# GitHub redirects here automatically during OAuth flow
# Frontend stores the JWT token for API authentication
```

---

#### `POST /oauth/refresh`
Refresh JWT token.

**Query Parameters:**
- `current_token` - Current JWT token

**Response:**
```json
{
  "token": "new-jwt-token"
}
```

---

### Webhook Endpoint

#### `POST /webhooks/github`
Handle GitHub webhook events.

**Headers (GitHub sends automatically):**
- `X-Hub-Signature-256` - Webhook signature for validation
- `X-GitHub-Event` - Event type (push, pull_request, etc.)

**Supported Events:**

**1. Push Event**
Triggered when code is pushed to a repository.

**Payload:**
```json
{
  "repository": {"id": 123, "full_name": "user/repo"},
  "ref": "refs/heads/main",
  "after": "commit-sha"
}
```

**Response:**
```json
{
  "status": "queued",
  "event": "push",
  "repository": "user/repo",
  "branch": "main",
  "run_id": 1
}
```

---

**2. Pull Request Event**
Triggered when PR is opened, synchronized, or reopened.

**Supported Actions:** `opened`, `synchronize`, `reopened`

**Payload:**
```json
{
  "action": "opened",
  "repository": {"id": 123, "full_name": "user/repo"},
  "pull_request": {
    "number": 42,
    "head": {
      "ref": "feature-branch",
      "sha": "commit-sha"
    }
  }
}
```

**Response:**
```json
{
  "status": "queued",
  "event": "pull_request",
  "action": "opened",
  "repository": "user/repo",
  "pr": 42,
  "run_id": 1
}
```

---

**3. Pull Request Review Event**
Triggered when review is requested or submitted.

**Supported Actions:** `requested_reviewer`, `submitted`

**Response:**
```json
{
  "status": "queued",
  "event": "pull_request_review",
  "action": "submitted",
  "repository": "user/repo",
  "pr": 42,
  "run_id": 1
}
```

---

### Installation Management Endpoints

#### `GET /installations`
List all installations.

**Response:**
```json
[
  {
    "id": 1,
    "installation_id": 12345,
    "github_user": "octocat",
    "github_org": "GitHub",
    "is_active": true,
    "created_at": "2026-01-09T12:00:00"
  }
]
```

---

#### `GET /installations/{installation_id}`
Get installation details.

**Response:** (same as above)

---

#### `DELETE /installations/{installation_id}`
Uninstall the GitHub App.

**Response:**
```json
{
  "status": "uninstalled",
  "installation_id": 1
}
```

---

#### `POST /installations/{installation_id}/repositories/{repo_id}/enable`
Enable analysis for a repository.

**Response:**
```json
{
  "status": "enabled",
  "repository": "user/repo"
}
```

---

#### `POST /installations/{installation_id}/repositories/{repo_id}/disable`
Disable analysis for a repository.

**Response:**
```json
{
  "status": "disabled",
  "repository": "user/repo"
}
```

---

## Security Features

### 1. Webhook Signature Validation
Every GitHub webhook is signed. The handler validates:
- `X-Hub-Signature-256` header matches computed HMAC-SHA256
- Uses `WEBHOOK_SECRET` from environment

### 2. JWT Token Management
- Tokens created on OAuth callback
- 7-day expiration by default
- Can be refreshed before expiration
- Stored securely (only in browser localStorage)

### 3. OAuth CSRF Protection
- `state` parameter prevents CSRF attacks
- Validated on callback

## Database Models

### Installation
Stores GitHub App installation info.

```python
{
  "id": 1,
  "installation_id": 12345,          # GitHub installation ID
  "github_user": "octocat",
  "github_org": "GitHub",
  "access_token": "ghu_xxx",         # GitHub user token
  "token_expires_at": "2026-02-09",
  "is_active": true,
  "created_at": "2026-01-09T12:00:00",
  "updated_at": "2026-01-09T12:00:00"
}
```

### AnalysisRun
Stores triggered analysis runs.

```python
{
  "id": 1,
  "repository_id": 1,
  "github_event": "push",            # push, pull_request, pull_request_review
  "github_branch": "main",
  "github_commit_sha": "abc123def",
  "pull_request_number": null,
  "status": "pending",               # pending, in_progress, completed, failed
  "created_at": "2026-01-09T12:00:00",
  "started_at": null,
  "completed_at": null,
  "error_message": null
}
```

## Frontend Integration

### 1. Start OAuth Flow
```javascript
// Get authorization URL
const response = await fetch('http://localhost:8000/oauth/authorize');
const { authorization_url } = await response.json();

// Redirect user to GitHub
window.location.href = authorization_url;
```

### 2. Handle Callback
```javascript
// GitHub redirects to /oauth/callback
// Extract code and state from URL
const params = new URLSearchParams(window.location.search);
const code = params.get('code');
const state = params.get('state');

// Exchange for JWT
const response = await fetch(
  `http://localhost:8000/oauth/callback?code=${code}&state=${state}`
);
const { token } = await response.json();

// Store token
localStorage.setItem('jwt_token', token);
```

### 3. Use JWT for API Calls
```javascript
const token = localStorage.getItem('jwt_token');

const response = await fetch('http://localhost:8000/installations', {
  headers: {
    'Authorization': `Bearer ${token}`
  }
});
```

## Testing

Run webhook tests:

```bash
cd backend
pytest tests/test_oauth_webhooks.py -v
```

Test OAuth flow locally:

```bash
# Start backend
python main.py

# Visit http://localhost:8000/docs to see interactive API docs
# Or use curl:
curl http://localhost:8000/oauth/authorize
```

## Environment Variables

See `.env.example` for all required variables:

```env
# GitHub App (register at github.com/settings/apps/new)
GITHUB_APP_ID=123456
GITHUB_APP_PRIVATE_KEY=-----BEGIN...
GITHUB_CLIENT_ID=abc123
GITHUB_CLIENT_SECRET=secret

# Security
JWT_SECRET_KEY=super-secret-key
WEBHOOK_SECRET=webhook-secret

# Database
DATABASE_URL=postgresql://...

# Frontend
FRONTEND_URL=http://localhost:3000
```

## What's Next

**Phase 3: V1 Core Integration**
- Integrate V1 analysis engine (Ruff, ESLint)
- Create `/api/analyze` endpoint
- Queue analysis jobs
- Persist results to database

**Phase 4: Dashboard**
- Display analysis results
- Show run history
- Per-repository settings
- Results visualization

## Troubleshooting

### Webhook Signature Invalid
- Ensure `WEBHOOK_SECRET` matches GitHub App webhook secret
- Check webhook payload is raw bytes (not parsed JSON)

### JWT Token Expired
- Call `/oauth/refresh` to get new token
- Tokens expire after 7 days

### OAuth Callback Fails
- Verify `GITHUB_CLIENT_ID` and `GITHUB_CLIENT_SECRET` are correct
- Check `FRONTEND_URL` matches registered redirect URI on GitHub App

### Database Connection Failed
- Ensure PostgreSQL is running
- Check `DATABASE_URL` format: `postgresql://user:pass@host/db`
- For Docker: use `db:5432` as host
