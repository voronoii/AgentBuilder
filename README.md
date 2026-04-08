# AgentBuilder

Node-based agent builder platform. Build LLM workflows by composing nodes on a visual canvas, with knowledge bases (RAG) and external MCP tools.

See [docs/specs/2026-04-08-agentbuilder-design.md](docs/specs/2026-04-08-agentbuilder-design.md) for the full design.

## Quick start

```bash
cp .env.example .env
docker compose up -d
```

- API: http://localhost:8000
- Web: http://localhost:3000

## Project layout

- `backend/` — FastAPI service (Python 3.11, SQLAlchemy async, LangGraph)
- `frontend/` — Next.js 15 app (React Flow canvas, Tailwind + Clay design tokens)
- `docs/` — design specs, plans, references
