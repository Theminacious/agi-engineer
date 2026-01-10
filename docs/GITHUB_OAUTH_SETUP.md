# GitHub OAuth Setup Guide

## Step-by-Step Instructions

### 1. Create GitHub OAuth Application

1. Go to: https://github.com/settings/apps/new
2. Fill in the form with these details:

   **Application Name:**
   ```
   AGI Engineer V2
   ```

   **Homepage URL:**
   ```
   http://localhost:3000
   ```

   **Authorization callback URL:**
   ```
   http://localhost:3000/oauth/callback
   ```

   **Description:**
   ```
   Automated code quality analysis with AI
   ```

3. **Permissions (Required for this app):**
   - Repository permissions:
     - Contents: `Read & write` (for accessing code)
     - Pull requests: `Read & write` (for creating PRs)
     - Checks: `Read & write` (for status checks)
   
   - Organization permissions:
     - Members: `Read-only` (optional, for org info)

4. **Subscribe to events:**
   - Check: `Push`
   - Check: `Pull request`
   - Check: `Repository`

5. Click **Create GitHub App**

---

### 2. Generate Client Secret

After creating the app:

1. Scroll down to **Client secrets** section
2. Click **Generate a new client secret**
3. Copy the generated secret (it will only show once)

---

### 3. Generate Private Key

1. Scroll down to **Private keys** section
2. Click **Generate a private key**
3. A PEM file will download automatically
4. Open the downloaded file in a text editor and copy the entire content

---

### 4. Update Your .env File

Edit `/Users/theminacious/Documents/mywork/agi-engineer/backend/.env`:

```bash
# Replace these placeholder values:

# From your GitHub App page:
GITHUB_APP_ID=YOUR_APP_ID_HERE
GITHUB_CLIENT_ID=YOUR_CLIENT_ID_HERE
GITHUB_CLIENT_SECRET=YOUR_CLIENT_SECRET_HERE

# From the downloaded private key file (keep the \n characters):
GITHUB_APP_PRIVATE_KEY=-----BEGIN RSA PRIVATE KEY-----\nMIIE...\n...\n-----END RSA PRIVATE KEY-----

# Keep these as-is (already configured):
DATABASE_URL=postgresql://user:password@localhost/agi_engineer_v2
API_HOST=0.0.0.0
API_PORT=8000
API_ENV=development
JWT_SECRET_KEY=your-secret-key-here
WEBHOOK_SECRET=your-webhook-secret-here
GROQ_API_KEY=your-groq-api-key-here
FRONTEND_URL=http://localhost:3000
```

---

### 5. Restart Backend

After updating the `.env` file, restart the backend:

```bash
# Kill the current process
lsof -ti:8000 | xargs kill -9

# Restart
cd /Users/theminacious/Documents/mywork/agi-engineer/backend
/Users/theminacious/Documents/mywork/agi-engineer/venv/bin/python main.py
```

---

### 6. Test the Login Flow

1. Open frontend: http://localhost:3000
2. Click **Login with GitHub**
3. You'll be redirected to GitHub to authorize
4. After authorization, you'll be redirected back to `/dashboard`

---

## Troubleshooting

### "Invalid Client ID" Error
- Check that `GITHUB_CLIENT_ID` matches exactly (no spaces)
- Verify it's from the OAuth App page, not the App ID

### "Redirect URI mismatch" Error
- Make sure Authorization callback URL in GitHub App settings matches exactly:
  ```
  http://localhost:3000/oauth/callback
  ```
- Must include the `/oauth/callback` path

### "Failed to exchange code" Error
- Check that `GITHUB_CLIENT_SECRET` is correct
- Make sure it was just generated (old secrets expire)
- Verify `FRONTEND_URL=http://localhost:3000` in .env

### Blank Screen After Login
- Open browser console (F12) for error messages
- Check backend logs for API errors
- Verify all credentials are correct in .env

---

## For Production Deployment

When deploying to production:

1. Create a new OAuth App with your production domain:
   - Homepage URL: `https://yourdomain.com`
   - Authorization callback URL: `https://yourdomain.com/oauth/callback`

2. Update `.env` in production:
   - `FRONTEND_URL=https://yourdomain.com`
   - New Client ID and Secret

3. Configure environment variables on your hosting platform

---

## Files Modified by OAuth Setup

- Backend: `/backend/.env` - Contains OAuth credentials
- Frontend: `http://localhost:3000/auth` - Login page
- Backend: `/backend/app/routers/oauth.py` - OAuth endpoints
- Backend: `/backend/app/security.py` - OAuth manager

