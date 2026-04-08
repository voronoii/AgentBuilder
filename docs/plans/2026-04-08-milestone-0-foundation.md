# Milestone 0 — Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up a runnable 4-service Docker Compose stack (postgres, qdrant, api, web) with FastAPI health endpoint, Next.js skeleton showing API status, async SQLAlchemy + Alembic ready, and Clay design tokens wired in Tailwind — so every later milestone has a working foundation.

**Architecture:**
- Backend: Python 3.11 + FastAPI + SQLAlchemy 2.0 (async) + Alembic + pydantic-settings, packaged with `pyproject.toml`, served by uvicorn.
- Frontend: Next.js 15 (App Router, TypeScript) + Tailwind CSS 3.4 with Clay color tokens + simple fetch client to backend.
- Infra: docker-compose.yml with 4 services. Postgres 16, Qdrant latest, api/web built from local Dockerfiles. Volumes for pgdata, qdrant_data, uploads, and a read-only mount of `/DATA3/users/mj/hf_models` for future embedding models.

**Tech Stack:** Python 3.11, FastAPI 0.115, SQLAlchemy 2.0 async, asyncpg, Alembic 1.14, pydantic-settings 2.7, pytest 8.3 + pytest-asyncio + httpx, Next.js 15, React 19, TypeScript 5, Tailwind CSS 3.4, Postgres 16, Qdrant, Docker Compose.

**Reference spec:** [docs/specs/2026-04-08-agentbuilder-design.md](../specs/2026-04-08-agentbuilder-design.md) §1, §2, §11, §12, §13.

---

## File Structure (locked in before tasks)

```
AgentBuilder/
├── .gitignore                       (new)
├── README.md                        (new)
├── docker-compose.yml               (new)
├── .env.example                     (new)
├── backend/
│   ├── pyproject.toml               (new)
│   ├── Dockerfile                   (new)
│   ├── .dockerignore                (new)
│   ├── alembic.ini                  (new — alembic init output, edited)
│   ├── alembic/
│   │   ├── env.py                   (new — async-aware)
│   │   ├── script.py.mako           (new — alembic init default)
│   │   └── versions/.gitkeep        (new)
│   ├── app/
│   │   ├── __init__.py              (new, empty)
│   │   ├── main.py                  (new — FastAPI app factory)
│   │   ├── core/
│   │   │   ├── __init__.py          (new, empty)
│   │   │   ├── config.py            (new — Settings via pydantic-settings)
│   │   │   └── db.py                (new — async engine + session factory)
│   │   └── api/
│   │       ├── __init__.py          (new, empty)
│   │       └── health.py            (new — /health router)
│   └── tests/
│       ├── __init__.py              (new, empty)
│       ├── conftest.py              (new — fixtures, env isolation)
│       ├── test_config.py           (new)
│       ├── test_health.py           (new)
│       └── test_db.py               (new)
└── frontend/
    ├── package.json                 (new)
    ├── tsconfig.json                (new)
    ├── next.config.mjs              (new)
    ├── next-env.d.ts                (new — auto, committed once)
    ├── tailwind.config.ts           (new — Clay tokens)
    ├── postcss.config.mjs           (new)
    ├── Dockerfile                   (new)
    ├── .dockerignore                (new)
    ├── app/
    │   ├── layout.tsx               (new — root layout, Clay bg)
    │   ├── page.tsx                 (new — calls /api/health)
    │   └── globals.css              (new — @tailwind directives + tokens)
    └── lib/
        └── api.ts                   (new — fetch wrapper)
```

**Boundaries:**
- `app/core/config.py` owns ALL settings reading. No other module reads `os.environ`.
- `app/core/db.py` owns the engine and session factory. Routers/services receive sessions via FastAPI dependency.
- `app/api/health.py` knows nothing about DB session — it returns process-level liveness only. (DB readiness comes in M1.)
- Frontend `lib/api.ts` is the only place that constructs fetch URLs from `NEXT_PUBLIC_API_URL`.

---

## Conventions

- **Python**: 4-space indent, type hints everywhere, `from __future__ import annotations` at the top of every module.
- **Commits**: Conventional commits — `feat:`, `chore:`, `test:`, `build:`, `docs:`. No co-author lines (per global git workflow rule).
- **Test naming**: `test_<unit>_<behavior>` snake_case.
- **Run commands shown in this plan assume cwd = `/DATA3/users/mj/AgentBuilder/`** unless otherwise stated.

---

## Task 1 — Initialize repository, base directories, gitignore, README

**Files:**
- Create: `.gitignore`
- Create: `README.md`
- Create: `backend/`, `frontend/`, `backend/app/`, `backend/tests/`, `backend/alembic/versions/`, `frontend/app/`, `frontend/lib/`

- [x] **Step 1: Initialize git repo**

```bash
cd /DATA3/users/mj/AgentBuilder
git init
git branch -M main
```

Expected: `Initialized empty Git repository in /DATA3/users/mj/AgentBuilder/.git/`

- [x] **Step 2: Create directory skeleton**

```bash
mkdir -p backend/app/core backend/app/api backend/tests backend/alembic/versions
mkdir -p frontend/app frontend/lib
touch backend/alembic/versions/.gitkeep
```

- [x] **Step 3: Write `.gitignore`**

Create `/DATA3/users/mj/AgentBuilder/.gitignore`:

```gitignore
# Python
__pycache__/
*.py[cod]
*.egg-info/
.venv/
venv/
.pytest_cache/
.mypy_cache/
.ruff_cache/
.coverage
htmlcov/
dist/
build/

# Node
node_modules/
.next/
out/
.turbo/
*.tsbuildinfo
next-env.d.ts

# Env
.env
.env.local
.env.*.local

# OS / IDE
.DS_Store
.vscode/
.idea/

# Project
uploads/
.omc/state/
.claude/state/

# Keep
!.gitkeep
```

- [x] **Step 4: Write `README.md`**

Create `/DATA3/users/mj/AgentBuilder/README.md`:

```markdown
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
```

- [x] **Step 5: First commit**

```bash
git add .gitignore README.md backend/ frontend/ docs/
git commit -m "chore: initialize project structure"
```

Expected: commit succeeds, `git status` clean.

---

## Task 2 — Backend `pyproject.toml` with dependencies

**Files:**
- Create: `backend/pyproject.toml`

- [x] **Step 1: Write `backend/pyproject.toml`**

```toml
[project]
name = "agentbuilder-backend"
version = "0.0.1"
description = "AgentBuilder backend — FastAPI + LangGraph"
requires-python = ">=3.11,<3.13"
dependencies = [
    "fastapi>=0.115,<0.116",
    "uvicorn[standard]>=0.32,<0.33",
    "pydantic>=2.10,<3.0",
    "pydantic-settings>=2.7,<3.0",
    "sqlalchemy[asyncio]>=2.0.36,<2.1",
    "asyncpg>=0.30,<0.31",
    "alembic>=1.14,<1.15",
    "python-multipart>=0.0.18,<0.1",
    "httpx>=0.28,<0.29",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.3,<9.0",
    "pytest-asyncio>=0.25,<0.26",
    "pytest-cov>=6.0,<7.0",
    "ruff>=0.8,<0.9",
]

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
where = ["."]
include = ["app*"]

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
addopts = "-ra --strict-markers"

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "UP", "B", "SIM"]
```

- [x] **Step 2: Verify install works locally**

```bash
cd /DATA3/users/mj/AgentBuilder/backend
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Expected: ends with `Successfully installed ... fastapi-0.115...`. No errors.

- [x] **Step 3: Commit**

```bash
cd /DATA3/users/mj/AgentBuilder
git add backend/pyproject.toml
git commit -m "build(backend): add pyproject.toml with FastAPI and SQLAlchemy deps"
```

---

## Task 3 — Backend Settings module (TDD)

**Files:**
- Create: `backend/app/__init__.py` (empty)
- Create: `backend/app/core/__init__.py` (empty)
- Create: `backend/app/core/config.py`
- Create: `backend/tests/__init__.py` (empty)
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/test_config.py`

- [x] **Step 1: Create empty package files**

```bash
cd /DATA3/users/mj/AgentBuilder
touch backend/app/__init__.py backend/app/core/__init__.py backend/tests/__init__.py
```

- [x] **Step 2: Write `backend/tests/conftest.py`**

```python
from __future__ import annotations

import os
from collections.abc import Iterator

import pytest


@pytest.fixture(autouse=True)
def isolate_env(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Strip AGENTBUILDER_* env vars before each test for deterministic Settings."""
    for key in list(os.environ):
        if key.startswith("AGENTBUILDER_"):
            monkeypatch.delenv(key, raising=False)
    yield
```

- [x] **Step 3: Write the failing test in `backend/tests/test_config.py`**

```python
from __future__ import annotations

import pytest

from app.core.config import Settings


def test_settings_defaults_when_no_env():
    settings = Settings()
    assert settings.app_name == "AgentBuilder"
    assert settings.api_host == "0.0.0.0"
    assert settings.api_port == 8000
    assert settings.database_url.startswith("postgresql+asyncpg://")
    assert settings.qdrant_url == "http://qdrant:6333"


def test_settings_reads_env_vars(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("AGENTBUILDER_API_PORT", "9001")
    monkeypatch.setenv(
        "AGENTBUILDER_DATABASE_URL",
        "postgresql+asyncpg://u:p@db:5432/x",
    )
    settings = Settings()
    assert settings.api_port == 9001
    assert settings.database_url == "postgresql+asyncpg://u:p@db:5432/x"


def test_settings_default_embedding_path():
    settings = Settings()
    assert settings.default_embedding_provider == "local_hf"
    assert settings.default_embedding_model_path == (
        "/models/snowflake-arctic-embed-l-v2.0-ko"
    )
```

- [x] **Step 4: Run the test, verify it fails**

```bash
cd /DATA3/users/mj/AgentBuilder/backend
source .venv/bin/activate
pytest tests/test_config.py -v
```

Expected: collection error or `ModuleNotFoundError: No module named 'app.core.config'`.

- [x] **Step 5: Implement `backend/app/core/config.py`**

```python
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All runtime configuration. Read once at startup; do not mutate."""

    model_config = SettingsConfigDict(
        env_prefix="AGENTBUILDER_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App
    app_name: str = "AgentBuilder"
    debug: bool = False

    # API server
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # Database
    database_url: str = (
        "postgresql+asyncpg://agentbuilder:agentbuilder@postgres:5432/agentbuilder"
    )

    # Vector DB
    qdrant_url: str = "http://qdrant:6333"

    # Embedding defaults (see spec §5, §6.4)
    default_embedding_provider: str = "local_hf"
    default_embedding_model_path: str = "/models/snowflake-arctic-embed-l-v2.0-ko"
    default_embedding_dim: int = 1024

    # Optional API keys for chat providers (loaded if present)
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None


def get_settings() -> Settings:
    """Factory used by FastAPI dependency injection."""
    return Settings()
```

- [x] **Step 6: Run the test, verify it passes**

```bash
pytest tests/test_config.py -v
```

Expected: `3 passed`.

- [x] **Step 7: Commit**

```bash
cd /DATA3/users/mj/AgentBuilder
git add backend/app/__init__.py backend/app/core/ backend/tests/__init__.py backend/tests/conftest.py backend/tests/test_config.py
git commit -m "feat(backend): add Settings module with env-prefixed config"
```

---

## Task 4 — Backend FastAPI app + `/health` endpoint (TDD)

**Files:**
- Create: `backend/app/api/__init__.py` (empty)
- Create: `backend/app/api/health.py`
- Create: `backend/app/main.py`
- Create: `backend/tests/test_health.py`

- [x] **Step 1: Create empty `api/__init__.py`**

```bash
touch backend/app/api/__init__.py
```

- [x] **Step 2: Write the failing test in `backend/tests/test_health.py`**

```python
from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import create_app


@pytest.fixture
async def client():
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


async def test_health_returns_ok(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["app"] == "AgentBuilder"
    assert "version" in body


async def test_health_under_api_v1_prefix(client: AsyncClient):
    resp = await client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
```

- [x] **Step 3: Run the test, verify it fails**

```bash
cd /DATA3/users/mj/AgentBuilder/backend
pytest tests/test_health.py -v
```

Expected: `ModuleNotFoundError: No module named 'app.main'`.

- [x] **Step 4: Implement `backend/app/api/health.py`**

```python
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.config import Settings, get_settings

router = APIRouter(tags=["health"])

APP_VERSION = "0.0.1"


@router.get("/health")
async def health(settings: Settings = Depends(get_settings)) -> dict[str, str]:
    """Process-level liveness. Does NOT touch the database (M1 will add /ready)."""
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": APP_VERSION,
    }
```

- [x] **Step 5: Implement `backend/app/main.py`**

```python
from __future__ import annotations

from fastapi import FastAPI

from app.api.health import router as health_router
from app.core.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version="0.0.1",
        debug=settings.debug,
    )

    # Top-level health (load balancers, docker healthchecks)
    app.include_router(health_router)

    # Versioned API surface — every future router lives under /api/v1
    app.include_router(health_router, prefix="/api/v1")

    return app


app = create_app()
```

- [x] **Step 6: Run the test, verify it passes**

```bash
pytest tests/test_health.py -v
```

Expected: `2 passed`.

- [x] **Step 7: Smoke-run uvicorn locally**

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000 &
sleep 1
curl -sS http://127.0.0.1:8000/health
kill %1
```

Expected output: `{"status":"ok","app":"AgentBuilder","version":"0.0.1"}`

- [x] **Step 8: Commit**

```bash
cd /DATA3/users/mj/AgentBuilder
git add backend/app/api/ backend/app/main.py backend/tests/test_health.py
git commit -m "feat(backend): add FastAPI app factory and /health endpoint"
```

---

## Task 5 — Backend async DB engine module (TDD with SQLite in-memory)

**Files:**
- Create: `backend/app/core/db.py`
- Create: `backend/tests/test_db.py`

> **Why SQLite for the test:** M0 ships only the engine factory and session dependency — there are no models yet. Pinning the unit test to SQLite-in-memory keeps it hermetic. The Postgres URL gets exercised end-to-end in Task 14.

- [x] **Step 1: Add aiosqlite to dev deps for the test**

Edit `backend/pyproject.toml`, change the `dev` extras list to include `aiosqlite`:

```toml
[project.optional-dependencies]
dev = [
    "pytest>=8.3,<9.0",
    "pytest-asyncio>=0.25,<0.26",
    "pytest-cov>=6.0,<7.0",
    "ruff>=0.8,<0.9",
    "aiosqlite>=0.20,<0.21",
]
```

Reinstall dev extras:

```bash
cd /DATA3/users/mj/AgentBuilder/backend
pip install -e ".[dev]"
```

Expected: `aiosqlite-0.20...` installed.

- [x] **Step 2: Write the failing test in `backend/tests/test_db.py`**

```python
from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.core.db import build_engine, build_sessionmaker


@pytest.fixture
def sqlite_url() -> str:
    return "sqlite+aiosqlite:///:memory:"


async def test_build_engine_returns_async_engine(sqlite_url: str):
    engine = build_engine(sqlite_url)
    try:
        assert isinstance(engine, AsyncEngine)
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            assert result.scalar() == 1
    finally:
        await engine.dispose()


async def test_sessionmaker_yields_async_session(sqlite_url: str):
    engine = build_engine(sqlite_url)
    sessionmaker = build_sessionmaker(engine)
    try:
        async with sessionmaker() as session:
            assert isinstance(session, AsyncSession)
            result = await session.execute(text("SELECT 42"))
            assert result.scalar() == 42
    finally:
        await engine.dispose()
```

- [x] **Step 3: Run the test, verify it fails**

```bash
pytest tests/test_db.py -v
```

Expected: `ModuleNotFoundError: No module named 'app.core.db'`.

- [x] **Step 4: Implement `backend/app/core/db.py`**

```python
from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings


def build_engine(database_url: str) -> AsyncEngine:
    """Construct an async engine. Caller owns the lifecycle (must dispose)."""
    return create_async_engine(database_url, echo=False, future=True)


def build_sessionmaker(
    engine: AsyncEngine,
) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


# Application-wide singletons (constructed lazily)
_engine: AsyncEngine | None = None
_sessionmaker: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        _engine = build_engine(get_settings().database_url)
    return _engine


def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    global _sessionmaker
    if _sessionmaker is None:
        _sessionmaker = build_sessionmaker(get_engine())
    return _sessionmaker


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency. Yields one session per request."""
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        yield session
```

- [x] **Step 5: Run the test, verify it passes**

```bash
pytest tests/test_db.py -v
```

Expected: `2 passed`.

- [x] **Step 6: Run the full suite**

```bash
pytest -v
```

Expected: `7 passed` (3 config + 2 health + 2 db).

- [x] **Step 7: Commit**

```bash
cd /DATA3/users/mj/AgentBuilder
git add backend/pyproject.toml backend/app/core/db.py backend/tests/test_db.py
git commit -m "feat(backend): add async SQLAlchemy engine and session factory"
```

---

## Task 6 — Alembic init + async-aware `env.py` + empty baseline migration

**Files:**
- Create: `backend/alembic.ini`
- Create: `backend/alembic/env.py`
- Create: `backend/alembic/script.py.mako`
- Create: `backend/alembic/versions/<rev>_baseline.py`

- [x] **Step 1: Run alembic init**

```bash
cd /DATA3/users/mj/AgentBuilder/backend
alembic init alembic
```

This creates `alembic.ini`, `alembic/env.py`, `alembic/script.py.mako`, `alembic/README`. We will overwrite `env.py` and edit `alembic.ini`.

- [x] **Step 2: Edit `backend/alembic.ini`**

Open `backend/alembic.ini` and change two lines:

1. Find the line `script_location = alembic` — leave as is.
2. Find the line `sqlalchemy.url = driver://user:pass@localhost/dbname` and replace with:

```ini
sqlalchemy.url =
```

(empty — `env.py` will inject it from Settings.)

- [x] **Step 3: Replace `backend/alembic/env.py` with this async-aware version**

```python
from __future__ import annotations

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.core.config import get_settings

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Inject DB URL from Settings (overrides empty alembic.ini value)
config.set_main_option("sqlalchemy.url", get_settings().database_url)

# M0: no models yet → metadata is None.
# M1 will set: target_metadata = Base.metadata
target_metadata = None


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

- [x] **Step 4: Create the empty baseline migration**

```bash
cd /DATA3/users/mj/AgentBuilder/backend
alembic revision -m "baseline (m0 — empty)"
```

This creates `alembic/versions/<hash>_baseline_m0_empty.py`. Open the generated file and confirm `upgrade()` and `downgrade()` are `pass` (alembic does this by default — leave them).

- [x] **Step 5: Verify the baseline can run offline**

```bash
alembic upgrade head --sql
```

Expected: prints SQL header lines and creates `alembic_version` insert. No errors.

- [x] **Step 6: Add `backend/alembic/versions/.gitkeep` removal note**

The `.gitkeep` from Task 1 can stay; the new versions file will live alongside it.

- [x] **Step 7: Commit**

```bash
cd /DATA3/users/mj/AgentBuilder
git add backend/alembic.ini backend/alembic/
git commit -m "build(backend): add alembic with async env.py and empty baseline migration"
```

---

## Task 7 — Backend Dockerfile

**Files:**
- Create: `backend/Dockerfile`
- Create: `backend/.dockerignore`

- [x] **Step 1: Write `backend/.dockerignore`**

```
.venv
__pycache__
*.pyc
*.pyo
.pytest_cache
.mypy_cache
.ruff_cache
.coverage
htmlcov
tests
.git
```

- [x] **Step 2: Write `backend/Dockerfile`**

```dockerfile
FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# System deps for asyncpg + future psycopg/qdrant clients
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first for layer caching
COPY pyproject.toml ./
RUN pip install --upgrade pip && pip install -e .

# Copy source
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./alembic.ini

EXPOSE 8000

# Default: run migrations then start uvicorn
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
```

- [x] **Step 3: Build the image**

```bash
cd /DATA3/users/mj/AgentBuilder
docker build -t agentbuilder-api:dev backend/
```

Expected: ends with `Successfully tagged agentbuilder-api:dev`. May take 1–3 minutes first time.

- [x] **Step 4: Sanity-run the container in isolation**

```bash
docker run --rm -e AGENTBUILDER_DATABASE_URL=sqlite+aiosqlite:///:memory: \
    -p 18000:8000 --name ab-api-test agentbuilder-api:dev &
sleep 4
curl -sS http://127.0.0.1:18000/health
docker stop ab-api-test
```

Expected output: `{"status":"ok","app":"AgentBuilder","version":"0.0.1"}`.

> Note: alembic upgrade with sqlite+aiosqlite for the empty baseline migration is a no-op and should succeed silently.

- [x] **Step 5: Commit**

```bash
git add backend/Dockerfile backend/.dockerignore
git commit -m "build(backend): add multi-stage-friendly Dockerfile"
```

---

## Task 8 — Frontend Next.js skeleton (manual scaffold)

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/tsconfig.json`
- Create: `frontend/next.config.mjs`
- Create: `frontend/app/layout.tsx`
- Create: `frontend/app/page.tsx`

> **Why manual instead of `create-next-app`:** create-next-app makes interactive choices and writes files we don't want (default README, eslint config we'd replace). Manually keeps the diff small and reviewable.

- [x] **Step 1: Write `frontend/package.json`**

```json
{
  "name": "agentbuilder-web",
  "version": "0.0.1",
  "private": true,
  "scripts": {
    "dev": "next dev -p 3000",
    "build": "next build",
    "start": "next start -p 3000",
    "lint": "next lint"
  },
  "dependencies": {
    "next": "15.1.3",
    "react": "19.0.0",
    "react-dom": "19.0.0"
  },
  "devDependencies": {
    "@types/node": "22.10.5",
    "@types/react": "19.0.2",
    "@types/react-dom": "19.0.2",
    "typescript": "5.7.2"
  }
}
```

- [x] **Step 2: Write `frontend/tsconfig.json`**

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["dom", "dom.iterable", "esnext"],
    "allowJs": false,
    "skipLibCheck": true,
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true,
    "plugins": [{ "name": "next" }],
    "paths": {
      "@/*": ["./*"]
    }
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
  "exclude": ["node_modules"]
}
```

- [x] **Step 3: Write `frontend/next.config.mjs`**

```javascript
/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  output: 'standalone',
};

export default nextConfig;
```

- [x] **Step 4: Write `frontend/app/layout.tsx`**

```tsx
import type { Metadata } from 'next';
import type { ReactNode } from 'react';

export const metadata: Metadata = {
  title: 'AgentBuilder',
  description: 'Build agent workflows visually',
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="ko">
      <body>{children}</body>
    </html>
  );
}
```

- [x] **Step 5: Write a placeholder `frontend/app/page.tsx`**

```tsx
export default function HomePage() {
  return (
    <main>
      <h1>AgentBuilder</h1>
      <p>Skeleton page — wired in Task 10.</p>
    </main>
  );
}
```

- [x] **Step 6: Install and verify build**

```bash
cd /DATA3/users/mj/AgentBuilder/frontend
npm install
npm run build
```

Expected: ends with `Compiled successfully` and prints route table including `/`.

- [x] **Step 7: Commit**

```bash
cd /DATA3/users/mj/AgentBuilder
git add frontend/package.json frontend/package-lock.json frontend/tsconfig.json frontend/next.config.mjs frontend/app/layout.tsx frontend/app/page.tsx
git commit -m "feat(frontend): scaffold Next.js 15 app with TypeScript"
```

---

## Task 9 — Frontend Tailwind CSS + Clay design tokens

**Files:**
- Create: `frontend/tailwind.config.ts`
- Create: `frontend/postcss.config.mjs`
- Create: `frontend/app/globals.css`
- Modify: `frontend/app/layout.tsx`
- Modify: `frontend/package.json`

> **Scope note:** This task wires the Clay color palette (from DESIGN.md §2) and warm cream background only. Roobert font, OpenType stylistic sets, custom animations, and the full type scale are deferred to M3 when we build real UI.

- [x] **Step 1: Install Tailwind**

```bash
cd /DATA3/users/mj/AgentBuilder/frontend
npm install -D tailwindcss@3.4.17 postcss@8.4.49 autoprefixer@10.4.20
```

Expected: `tailwindcss@3.4.17` added.

- [x] **Step 2: Write `frontend/postcss.config.mjs`**

```javascript
export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
};
```

- [x] **Step 3: Write `frontend/tailwind.config.ts` with Clay tokens**

```typescript
import type { Config } from 'tailwindcss';

const config: Config = {
  content: ['./app/**/*.{ts,tsx}', './components/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // Clay base — see DESIGN.md §2
        cream: '#faf9f7',
        clayBlack: '#000000',
        oat: {
          DEFAULT: '#dad4c8',
          light: '#eee9df',
        },
        warmSilver: '#9f9b93',
        warmCharcoal: '#55534e',
        // Swatch palette
        matcha: {
          300: '#84e7a5',
          600: '#078a52',
          800: '#02492a',
        },
        slushie: {
          500: '#3bd3fd',
          800: '#0089ad',
        },
        lemon: {
          400: '#f8cc65',
          500: '#fbbd41',
          700: '#d08a11',
          800: '#9d6a09',
        },
        ube: {
          300: '#c1b0ff',
          800: '#43089f',
          900: '#32037d',
        },
        pomegranate: {
          400: '#fc7981',
        },
        blueberry: {
          800: '#01418d',
        },
      },
      borderRadius: {
        card: '12px',
        feature: '24px',
        section: '40px',
      },
      boxShadow: {
        clay:
          '0px 1px 1px rgba(0,0,0,0.1), 0px -1px 1px rgba(0,0,0,0.04) inset, 0px -0.5px 1px rgba(0,0,0,0.05)',
      },
    },
  },
  plugins: [],
};

export default config;
```

- [x] **Step 4: Write `frontend/app/globals.css`**

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

html,
body {
  background-color: #faf9f7; /* cream */
  color: #000000;
  -webkit-font-smoothing: antialiased;
}
```

- [x] **Step 5: Update `frontend/app/layout.tsx` to import globals.css**

Replace the file contents with:

```tsx
import type { Metadata } from 'next';
import type { ReactNode } from 'react';
import './globals.css';

export const metadata: Metadata = {
  title: 'AgentBuilder',
  description: 'Build agent workflows visually',
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="ko">
      <body className="bg-cream text-clayBlack">{children}</body>
    </html>
  );
}
```

- [x] **Step 6: Verify build still works**

```bash
cd /DATA3/users/mj/AgentBuilder/frontend
npm run build
```

Expected: `Compiled successfully`. No Tailwind class warnings.

- [x] **Step 7: Commit**

```bash
cd /DATA3/users/mj/AgentBuilder
git add frontend/package.json frontend/package-lock.json frontend/tailwind.config.ts frontend/postcss.config.mjs frontend/app/globals.css frontend/app/layout.tsx
git commit -m "feat(frontend): add Tailwind CSS with Clay color tokens"
```

---

## Task 10 — Frontend API client + health page wired to backend

**Files:**
- Create: `frontend/lib/api.ts`
- Modify: `frontend/app/page.tsx`

- [x] **Step 1: Write `frontend/lib/api.ts`**

```typescript
const RAW_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';
const API_BASE = RAW_BASE.replace(/\/$/, '');

export type HealthResponse = {
  status: string;
  app: string;
  version: string;
};

export async function fetchHealth(): Promise<HealthResponse> {
  const res = await fetch(`${API_BASE}/health`, { cache: 'no-store' });
  if (!res.ok) {
    throw new Error(`Health check failed: HTTP ${res.status}`);
  }
  return (await res.json()) as HealthResponse;
}
```

- [x] **Step 2: Update `frontend/app/page.tsx` to call the backend**

```tsx
import { fetchHealth } from '@/lib/api';

export const dynamic = 'force-dynamic';

export default async function HomePage() {
  let status: 'ok' | 'error' = 'error';
  let detail = 'unreachable';
  let version = '?';
  let appName = '?';

  try {
    const health = await fetchHealth();
    status = health.status === 'ok' ? 'ok' : 'error';
    detail = health.status;
    version = health.version;
    appName = health.app;
  } catch (err) {
    detail = err instanceof Error ? err.message : 'unknown error';
  }

  return (
    <main className="min-h-screen flex items-center justify-center p-8">
      <section className="bg-white border border-oat rounded-feature shadow-clay p-10 max-w-lg w-full">
        <h1 className="text-3xl font-semibold mb-6">AgentBuilder</h1>
        <dl className="space-y-2 text-sm">
          <div className="flex justify-between">
            <dt className="text-warmSilver">App</dt>
            <dd>{appName}</dd>
          </div>
          <div className="flex justify-between">
            <dt className="text-warmSilver">Version</dt>
            <dd>{version}</dd>
          </div>
          <div className="flex justify-between">
            <dt className="text-warmSilver">API</dt>
            <dd className={status === 'ok' ? 'text-matcha-600' : 'text-pomegranate-400'}>
              {detail}
            </dd>
          </div>
        </dl>
      </section>
    </main>
  );
}
```

- [x] **Step 3: Verify the build picks up the new page**

```bash
cd /DATA3/users/mj/AgentBuilder/frontend
npm run build
```

Expected: `Compiled successfully`. `/` listed as a dynamic route.

- [x] **Step 4: Commit**

```bash
cd /DATA3/users/mj/AgentBuilder
git add frontend/lib/api.ts frontend/app/page.tsx
git commit -m "feat(frontend): add API client and wire home page to /health"
```

---

## Task 11 — Frontend Dockerfile

**Files:**
- Create: `frontend/Dockerfile`
- Create: `frontend/.dockerignore`

- [x] **Step 1: Write `frontend/.dockerignore`**

```
node_modules
.next
out
.turbo
.git
Dockerfile
.dockerignore
```

- [x] **Step 2: Write `frontend/Dockerfile`**

```dockerfile
# ---------- deps ----------
FROM node:20-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

# ---------- build ----------
FROM node:20-alpine AS build
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

# ---------- runtime ----------
FROM node:20-alpine AS runtime
WORKDIR /app
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000

# Standalone output (next.config.mjs sets output: 'standalone')
COPY --from=build /app/.next/standalone ./
COPY --from=build /app/.next/static ./.next/static
COPY --from=build /app/public ./public 2>/dev/null || true

EXPOSE 3000
CMD ["node", "server.js"]
```

> If the `public` copy line above causes a build error because `public/` doesn't exist, remove it. Next 15 standalone build does not require a `public/` directory.

- [x] **Step 3: Build the image**

```bash
cd /DATA3/users/mj/AgentBuilder
docker build -t agentbuilder-web:dev frontend/
```

Expected: ends with `Successfully tagged agentbuilder-web:dev`. If the public copy line errors, edit it out and rebuild.

- [x] **Step 4: Commit**

```bash
git add frontend/Dockerfile frontend/.dockerignore
git commit -m "build(frontend): add multi-stage Dockerfile with standalone output"
```

---

## Task 12 — `docker-compose.yml` (postgres + qdrant + api + web)

**Files:**
- Create: `docker-compose.yml`

- [x] **Step 1: Write `docker-compose.yml`**

```yaml
services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-agentbuilder}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-agentbuilder}
      POSTGRES_DB: ${POSTGRES_DB:-agentbuilder}
    volumes:
      - pgdata:/var/lib/postgresql/data
    ports:
      - "${POSTGRES_PORT:-5432}:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-agentbuilder}"]
      interval: 5s
      timeout: 3s
      retries: 10

  qdrant:
    image: qdrant/qdrant:v1.12.4
    volumes:
      - qdrant_data:/qdrant/storage
    ports:
      - "${QDRANT_PORT:-6333}:6333"
    healthcheck:
      test: ["CMD-SHELL", "curl -fsS http://localhost:6333/readyz || exit 1"]
      interval: 5s
      timeout: 3s
      retries: 10

  api:
    build:
      context: ./backend
    depends_on:
      postgres:
        condition: service_healthy
      qdrant:
        condition: service_healthy
    environment:
      AGENTBUILDER_DATABASE_URL: postgresql+asyncpg://${POSTGRES_USER:-agentbuilder}:${POSTGRES_PASSWORD:-agentbuilder}@postgres:5432/${POSTGRES_DB:-agentbuilder}
      AGENTBUILDER_QDRANT_URL: http://qdrant:6333
      AGENTBUILDER_DEFAULT_EMBEDDING_PROVIDER: local_hf
      AGENTBUILDER_DEFAULT_EMBEDDING_MODEL_PATH: /models/snowflake-arctic-embed-l-v2.0-ko
      AGENTBUILDER_OPENAI_API_KEY: ${OPENAI_API_KEY:-}
      AGENTBUILDER_ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY:-}
    volumes:
      - uploads:/app/uploads
      - /DATA3/users/mj/hf_models:/models:ro
    ports:
      - "${API_PORT:-8000}:8000"
    healthcheck:
      test: ["CMD-SHELL", "curl -fsS http://localhost:8000/health || exit 1"]
      interval: 5s
      timeout: 3s
      retries: 10

  web:
    build:
      context: ./frontend
    depends_on:
      api:
        condition: service_healthy
    environment:
      NEXT_PUBLIC_API_URL: http://api:8000
      NODE_ENV: production
    ports:
      - "${WEB_PORT:-3000}:3000"

volumes:
  pgdata:
  qdrant_data:
  uploads:
```

> **Note on `NEXT_PUBLIC_API_URL=http://api:8000`:** This works because `app/page.tsx` runs on the server (it's a Server Component with `dynamic = 'force-dynamic'`), so it resolves the Docker network hostname `api`. M3 will introduce client-side fetches and we'll add a separate browser-facing URL then.

- [x] **Step 2: Validate the compose file syntax**

```bash
cd /DATA3/users/mj/AgentBuilder
docker compose config > /dev/null
```

Expected: no output and exit code 0. Any output is an error to fix.

- [x] **Step 3: Commit**

```bash
git add docker-compose.yml
git commit -m "build: add 4-service docker-compose (postgres, qdrant, api, web)"
```

---

## Task 13 — `.env.example`

**Files:**
- Create: `.env.example`

- [x] **Step 1: Write `.env.example`**

```env
# ---- Postgres ----
POSTGRES_USER=agentbuilder
POSTGRES_PASSWORD=agentbuilder
POSTGRES_DB=agentbuilder
POSTGRES_PORT=5432

# ---- Qdrant ----
QDRANT_PORT=6333

# ---- API ----
API_PORT=8000

# ---- Web ----
WEB_PORT=3000

# ---- Chat provider keys (optional in M0; required for LLM/Agent nodes in M3) ----
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
```

- [x] **Step 2: Commit**

```bash
git add .env.example
git commit -m "docs: add .env.example with all M0 variables"
```

---

## Task 14 — End-to-end smoke test (compose up → both services healthy)

**Files:** none (operational verification + commit of any fixes if needed)

- [x] **Step 1: Bring the stack up**

```bash
cd /DATA3/users/mj/AgentBuilder
cp .env.example .env
docker compose up -d --build
```

Expected: 4 containers start. May take 2–5 minutes for first build.

- [x] **Step 2: Wait for health and check**

```bash
docker compose ps
```

Expected: postgres and qdrant show `(healthy)`, api shows `(healthy)`, web shows `Up`. If api is `(unhealthy)` after 60s, jump to Step 6.

- [x] **Step 3: Hit the API directly**

```bash
curl -sS http://localhost:8000/health
```

Expected: `{"status":"ok","app":"AgentBuilder","version":"0.0.1"}`.

- [x] **Step 4: Hit the web page**

```bash
curl -sS http://localhost:3000/ | grep -E "AgentBuilder|ok"
```

Expected: HTML containing `AgentBuilder` and `ok` (the API status rendered into the page).

- [x] **Step 5: Check Postgres is reachable inside the api container**

```bash
docker compose exec api python -c "import asyncio; from app.core.db import get_engine; from sqlalchemy import text;
async def main():
    eng = get_engine()
    async with eng.connect() as c:
        r = await c.execute(text('SELECT 1'))
        print('db says', r.scalar())
    await eng.dispose()
asyncio.run(main())"
```

Expected: `db says 1`.

- [x] **Step 6 (only if anything fails): Inspect logs**

```bash
docker compose logs api --tail 100
docker compose logs web --tail 100
docker compose logs postgres --tail 50
docker compose logs qdrant --tail 50
```

Common fixes:
- **api unhealthy with `connection refused` to postgres**: increase `retries` in postgres healthcheck or rerun `docker compose up -d`. The `depends_on: condition: service_healthy` should handle this — if it doesn't, check that `pg_isready` is in the postgres image (it is by default).
- **web build fails on `public/` copy**: edit `frontend/Dockerfile`, remove the `COPY --from=build /app/public` line, rebuild with `docker compose build web`.
- **api fails alembic upgrade**: check that the baseline migration in `backend/alembic/versions/` has empty `upgrade()`/`downgrade()`.

If a fix is needed, apply it, rebuild only the affected service (`docker compose build <service>` then `docker compose up -d <service>`), and re-run Steps 2–5.

- [x] **Step 7: Bring the stack down**

```bash
docker compose down
```

Expected: all 4 containers stopped and removed. Volumes preserved.

- [x] **Step 8: Commit any fixes**

If Step 6 required edits, commit them now:

```bash
git add -A
git commit -m "fix(infra): adjust M0 stack so docker compose up succeeds end-to-end"
```

If no fixes were needed, this step is a no-op.

---

## Done criteria

- `docker compose up -d` brings up postgres, qdrant, api, web with no errors.
- `curl http://localhost:8000/health` returns `{"status":"ok",...}`.
- `curl http://localhost:3000/` returns HTML showing the API status as `ok`.
- `pytest` in `backend/` passes (7 tests: 3 config + 2 health + 2 db).
- `npm run build` in `frontend/` succeeds.
- Git history is a clean sequence of small commits, one per task.

---

## Notes for the next milestone (M1 — Knowledge Base)

These hooks were intentionally left in place by M0:
- `app.core.db.get_session` — FastAPI dependency ready for routers to use.
- `alembic/env.py` `target_metadata = None` — change to `Base.metadata` once `app.models` is created.
- `Settings.default_embedding_*` — already wired, just needs the EmbeddingProvider Registry to consume them.
- The `:ro` mount of `/DATA3/users/mj/hf_models` is already in compose, so M1 can `from langchain_huggingface import HuggingFaceEmbeddings; HuggingFaceEmbeddings(model_name="/models/snowflake-arctic-embed-l-v2.0-ko")` without further infra work.
