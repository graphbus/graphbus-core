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
