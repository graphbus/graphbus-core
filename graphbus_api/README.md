# GraphBus API Server

This directory contains the FastAPI server that powers the GraphBus negotiation backend.

## Two ways to use it

### 1. Hosted (recommended)
Use the GraphBus hosted API at `https://api.graphbus.com`.  
Sign up at [graphbus.com](https://graphbus.com) to get an API key — no infrastructure required.

```bash
export GRAPHBUS_API_KEY=your_key_here
graphbus build agents/ --enable-agents
```

### 2. Self-hosted
Run your own server if you prefer to keep negotiation traffic on-premises or want to use your own LLM API keys.

**Requirements:** Python 3.9+, your own `DEEPSEEK_API_KEY` or `ANTHROPIC_API_KEY`

```bash
# Install dependencies
pip install fastapi uvicorn httpx python-dotenv

# Set your LLM key (server-side — never exposed to clients)
export DEEPSEEK_API_KEY=your_deepseek_key
# or
export ANTHROPIC_API_KEY=your_anthropic_key

# Start the server
uvicorn graphbus_api.main:app --host 0.0.0.0 --port 8080

# Point graphbus-core at your server
export GRAPHBUS_API_URL=http://localhost:8080
export GRAPHBUS_API_KEY=<key shown at server startup>
```

On first start, the server generates a random `GRAPHBUS_API_KEY` and prints it. Pass that key to your clients.

## API Reference

Once running, visit `http://localhost:8080/docs` for the interactive Swagger UI.

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/build` | Start an async build + negotiation job |
| `GET` | `/api/build/{job_id}` | Poll build job status |
| `GET` | `/api/build` | List all build jobs |
| `POST` | `/api/run` | Start a runtime session from artifacts |
| `POST` | `/api/run/{id}/call` | Call a method on a running agent |
| `POST` | `/api/run/{id}/publish` | Publish an event to the message bus |
| `GET` | `/api/run/{id}/stats` | Runtime session statistics |
| `GET` | `/api/negotiations` | Negotiation history |
| `GET` | `/health` | Health check |

All endpoints except `/health` require `X-Api-Key` header.

### Auth endpoints (requires Firebase)

| Method | Path | Auth Header | Description |
|--------|------|-------------|-------------|
| `POST` | `/auth/verify` | — (body: `id_token`) | Verify Firebase token, create user + issue API key |
| `GET` | `/auth/me` | `X-Api-Key` | Get current user profile |
| `GET` | `/auth/keys` | `X-Firebase-Token` | List user's API keys |
| `POST` | `/auth/keys` | `X-Firebase-Token` | Create a new API key |
| `DELETE` | `/auth/keys/{key_id}` | `X-Firebase-Token` | Revoke an API key |

## Firebase setup (multi-tenant mode)

To enable OAuth (Google/GitHub sign-in) and per-user API key management, configure Firebase:

### 1. Create a Firebase project

1. Go to [Firebase Console](https://console.firebase.google.com/) and create a project
2. Enable **Authentication** → Sign-in providers: Google, GitHub
3. Enable **Cloud Firestore** (start in production mode)

### 2. Generate a service account key

1. Firebase Console → Project Settings → Service Accounts
2. Click **Generate New Private Key** → download the JSON file

### 3. Configure the server

Provide the service account credentials via one of:

```bash
# Option A: path to the JSON file (recommended)
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json

# Option B: inline JSON (useful in Docker / CI)
export FIREBASE_SERVICE_ACCOUNT_JSON='{"type":"service_account","project_id":"...",...}'
```

Then start the server as usual:

```bash
uvicorn graphbus_api.main:app --host 0.0.0.0 --port 8080
```

If Firebase credentials are found, the server prints:

```
============================================================
  Firebase Admin SDK initialized
  Firestore connected — multi-tenant auth enabled
============================================================
```

### 4. Auth flow (client-side)

```
1. User signs in via Firebase client SDK (Google / GitHub)
2. Client gets a Firebase ID token
3. POST /auth/verify  { "id_token": "<token>" }
   → Returns { "uid", "email", "api_key": "gb_...", "key_id" }
4. Use the gb_ key in X-Api-Key header for all subsequent API calls
```

### Without Firebase (self-hosted)

If no Firebase credentials are set, the server falls back to env-var API key auth.
The `/auth/*` endpoints return `503 Service Unavailable`. All other endpoints
work as before using the `GRAPHBUS_API_KEY` from the environment.
