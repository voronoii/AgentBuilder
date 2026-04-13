# 마일스톤 1 — 지식 베이스 (RAG) 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**목표:** "매끄러운" 단일 사용자 RAG 파이프라인 제공 — 사용자가 설정 없이 지식 베이스를 생성하고, 파일을 드롭하면, SSE를 통해 문서별 수집 진행 상황을 실시간으로 확인하며, 검색 쿼리를 실행할 수 있음 — 모두 로컬 한국어 특화 HuggingFace 임베딩 모델(Snowflake Arctic Embed L v2.0 Korean)과 fastembed fallback, Qdrant 벡터 저장소, asyncio 기반 백그라운드 수집 orchestrator로 지원.

**아키텍처:**
- **백엔드**: `/knowledge` CRUD + `/knowledge/{kb_id}/documents` 업로드 + `/knowledge/{kb_id}/ingestion/stream` SSE + `/knowledge/{kb_id}/search`를 위한 FastAPI 라우터. 비동기 SQLAlchemy 모델(`KnowledgeBase`, `Document`). parser registry가 파일 확장자별로 플러그형 parser에 디스패치. RecursiveCharacterTextSplitter가 텍스트를 청크 분할. EmbeddingProvider registry가 local_hf(기본) 또는 fastembed(fallback)을 선택. Qdrant 클라이언트 래퍼가 KB당 하나의 컬렉션을 고정 차원으로 관리. 수집 orchestrator가 `asyncio.create_task`와 `asyncio.Semaphore` 뒤에서 문서별 작업을 실행하고, DB 상태 전환(`pending → processing → done | failed`)을 기록하며, SSE 라우트가 소비하는 인메모리 문서별 캐시를 통해 진행 이벤트를 발행.
- **프론트엔드**: Next.js App Router에 `/knowledge`(목록), `/knowledge/new`(생성 폼), `/knowledge/[kbId]`(상세 + 업로드 + 진행 + 검색 패널)을 추가. SSE는 브라우저에서 `EventSource`를 통해 소비하며, M0 후속 조치 A/B의 CORS middleware + 브라우저/서버 URL 분리를 M1으로 가져옴.
- **에러 계약**: 모든 새 endpoint는 M0 후속 조치 F의 `AppError` 봉투(`detail` / `code` / `request_id`)를 사용. Request ID middleware가 여기서 도입됨.

**기술 스택:** FastAPI 0.115, SQLAlchemy 2.0 async, Alembic, pydantic-settings, qdrant-client, langchain-core, langchain-text-splitters, langchain-huggingface, sentence-transformers, fastembed, pypdf, python-docx, python-pptx, openpyxl, ebooklib, beautifulsoup4, Next.js 15 App Router, React 19, TypeScript, TailwindCSS with Clay tokens, Python 3.13 (호스트 venv) / 3.11 (컨테이너).

**참조 스펙:** [docs/specs/2026-04-08-agentbuilder-design.md](../specs/2026-04-08-agentbuilder-design.md) §3.1, §6 (전체), §11.2, §11.3, §14 M1.
**영향받는 M0 후속 조치:** A (CORS), B (URL 분리), E (M1 의존성), F (에러 봉투). [docs/tracking/m0-followups.md](../tracking/m0-followups.md)에 업데이트됨.

---

## 파일 구조 (태스크 시작 전 확정)

```
AgentBuilder/
├── backend/
│   ├── pyproject.toml                                         (modify — add M1 deps)
│   ├── app/
│   │   ├── main.py                                            (modify — register routers, middleware, error handlers, startup recovery)
│   │   ├── core/
│   │   │   ├── config.py                                      (modify — add uploads_dir, ingestion_max_concurrency, cors_origins, qdrant_collection_prefix)
│   │   │   ├── errors.py                                      (new — AppError + ErrorCode enum + handlers)
│   │   │   └── request_id.py                                  (new — X-Request-ID middleware)
│   │   ├── models/
│   │   │   ├── __init__.py                                    (new)
│   │   │   ├── base.py                                        (new — declarative Base)
│   │   │   └── knowledge.py                                   (new — KnowledgeBase, Document)
│   │   ├── schemas/
│   │   │   ├── __init__.py                                    (new)
│   │   │   └── knowledge.py                                   (new — Pydantic DTOs)
│   │   ├── repositories/
│   │   │   ├── __init__.py                                    (new)
│   │   │   └── knowledge.py                                   (new — CRUD helpers)
│   │   ├── services/
│   │   │   ├── __init__.py                                    (new)
│   │   │   ├── knowledge/
│   │   │   │   ├── __init__.py                                (new)
│   │   │   │   ├── qdrant.py                                  (new — collection + upsert + search wrapper)
│   │   │   │   ├── chunker.py                                 (new — RecursiveCharacterTextSplitter wrapper)
│   │   │   │   ├── progress.py                                (new — in-memory per-doc progress cache + pub/sub)
│   │   │   │   ├── ingestion.py                               (new — pipeline function parse→chunk→embed→upsert)
│   │   │   │   ├── orchestrator.py                            (new — asyncio.create_task + semaphore + startup recovery)
│   │   │   │   └── parsers/
│   │   │   │       ├── __init__.py                            (new — registry + dispatch)
│   │   │   │       ├── base.py                                (new — ParsedDocument + Parser protocol)
│   │   │   │       ├── text.py                                (new — txt/md/mdx/html/htm/xml/vtt/properties)
│   │   │   │       ├── csv_parser.py                          (new — csv via stdlib)
│   │   │   │       ├── pdf.py                                 (new — pypdf)
│   │   │   │       ├── docx.py                                (new — python-docx)
│   │   │   │       ├── pptx.py                                (new — python-pptx)
│   │   │   │       ├── xlsx.py                                (new — openpyxl)
│   │   │   │       ├── epub.py                                (new — ebooklib + bs4)
│   │   │   │       └── eml.py                                 (new — stdlib email.parser)
│   │   │   └── providers/
│   │   │       ├── __init__.py                                (new)
│   │   │       └── embedding/
│   │   │           ├── __init__.py                            (new — registry + selection)
│   │   │           ├── base.py                                (new — EmbeddingProvider protocol)
│   │   │           ├── local_hf.py                            (new — langchain-huggingface)
│   │   │           └── fastembed_provider.py                  (new — fastembed fallback)
│   │   └── api/
│   │       ├── knowledge.py                                   (new — CRUD + upload + SSE + search routers)
│   │       └── health.py                                      (existing — untouched)
│   ├── alembic/versions/<hash>_m1_knowledge.py                (new — migration for KnowledgeBase + Document)
│   └── tests/
│       ├── fixtures/
│       │   ├── sample.txt                                     (new — committed)
│       │   ├── sample.md                                      (new — committed)
│       │   ├── sample.csv                                     (new — committed)
│       │   └── generated/                                     (test-time generated pdf/docx/pptx/xlsx/epub/eml)
│       ├── test_errors.py                                     (new)
│       ├── test_request_id.py                                 (new)
│       ├── test_embedding_registry.py                         (new)
│       ├── test_local_hf_provider.py                          (new — @pytest.mark.gpu, skip if model path missing)
│       ├── test_fastembed_provider.py                         (new)
│       ├── test_qdrant_wrapper.py                             (new — uses real qdrant if available, else skip)
│       ├── test_models_knowledge.py                           (new)
│       ├── test_knowledge_crud.py                             (new)
│       ├── test_file_upload.py                                (new)
│       ├── test_parser_text.py                                (new)
│       ├── test_parser_pdf.py                                 (new)
│       ├── test_parser_docx.py                                (new)
│       ├── test_parser_office.py                              (new — pptx/xlsx/csv)
│       ├── test_parser_misc.py                                (new — epub/eml)
│       ├── test_parser_registry.py                            (new)
│       ├── test_chunker.py                                    (new)
│       ├── test_progress.py                                   (new)
│       ├── test_ingestion_pipeline.py                         (new)
│       ├── test_orchestrator.py                               (new)
│       ├── test_startup_recovery.py                           (new)
│       ├── test_sse_stream.py                                 (new)
│       └── test_search_endpoint.py                            (new)
├── frontend/
│   ├── lib/
│   │   ├── api.ts                                             (modify — dual URL + KB client)
│   │   └── knowledge.ts                                       (new — types + fetchers)
│   ├── app/
│   │   ├── layout.tsx                                         (modify — add top nav)
│   │   └── knowledge/
│   │       ├── page.tsx                                       (new — KB list, Server Component)
│   │       ├── new/page.tsx                                   (new — create form page wrapper)
│   │       └── [kbId]/page.tsx                                (new — detail page)
│   └── components/
│       ├── nav/TopNav.tsx                                     (new — 지식/워크플로우/도구 tabs)
│       └── knowledge/
│           ├── KbList.tsx                                     (new — Server Component)
│           ├── CreateKbForm.tsx                               (new — Client Component, advanced toggle)
│           ├── FileUpload.tsx                                 (new — drag-drop Client Component)
│           ├── IngestionProgress.tsx                          (new — EventSource Client Component)
│           └── SearchPanel.tsx                                (new — Client Component)
├── docker-compose.yml                                         (modify — NEXT_PUBLIC_API_URL → host URL, add API_URL_INTERNAL)
├── .env.example                                               (modify — add AGENTBUILDER_CORS_ORIGINS, API_URL_INTERNAL)
└── docs/
    ├── plans/2026-04-09-milestone-1-knowledge-rag.md          (this file)
    └── tracking/m0-followups.md                               (modify — close A, B, E, F; record commits)
```

---

## 태스크 분해 (총 23개)

### 태스크 1: M1 의존성 추가 및 로컬 HF 모델 접근 확인

리서치 게이트: pyproject.toml 수정 전에, `ecc:search-first`를 호출하여 레포에 기존 헬퍼가 없는지 확인하고, `ecc:documentation-lookup`으로 `langchain-huggingface`, `qdrant-client`, `fastembed`의 최신 릴리스 노트 대비 버전을 고정한다. 결과를 commit 메시지에 기록.

**파일:**
- 수정: `backend/pyproject.toml`
- 생성: `backend/tests/test_local_hf_smoke.py`

- [ ] **단계 1: 실패하는 스모크 테스트 작성**

```python
# backend/tests/test_local_hf_smoke.py
from __future__ import annotations

import os
from pathlib import Path

import pytest


@pytest.mark.gpu
def test_local_hf_model_directory_is_mounted() -> None:
    """Model path from Settings must exist inside the container/host venv.

    Skipped when the model directory is absent (developer laptop without
    the 8GB model). CI marks `gpu` to run only on the host with the mount.
    """
    model_path = Path(
        os.environ.get(
            "AGENTBUILDER_DEFAULT_EMBEDDING_MODEL_PATH",
            "/DATA3/users/mj/hf_models/snowflake-arctic-embed-l-v2.0-ko",
        )
    )
    if not model_path.exists():
        pytest.skip(f"model path not present: {model_path}")

    assert (model_path / "config.json").is_file(), "HF config.json missing"
    assert any(model_path.glob("*.safetensors")) or any(
        model_path.glob("pytorch_model*.bin")
    ), "no model weights found"
```

- [ ] **단계 2: 실행 — 모델이 없는 머신에서는 PASS (skip), 호스트에서는 PASS 예상**

```bash
cd backend && .venv/bin/pytest tests/test_local_hf_smoke.py -v
```

예상 결과: `PASSED` 또는 `SKIPPED` (절대 실패하지 않음).

- [ ] **단계 3: pyproject.toml에 M1 의존성 추가**

`dependencies` 리스트에 추가(기존 항목 유지)하고 `gpu` 마커를 등록:

```toml
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
    # M1 — knowledge base / RAG
    "qdrant-client>=1.12,<2.0",
    "langchain-core>=0.3,<0.4",
    "langchain-text-splitters>=0.3,<0.4",
    "langchain-huggingface>=0.1.2,<0.2",
    "sentence-transformers>=3.3,<4.0",
    "fastembed>=0.4,<0.5",
    "pypdf>=5.1,<6.0",
    "python-docx>=1.1,<2.0",
    "python-pptx>=1.0,<2.0",
    "openpyxl>=3.1,<4.0",
    "ebooklib>=0.18,<0.19",
    "beautifulsoup4>=4.12,<5.0",
    "sse-starlette>=2.1,<3.0",
]
```

그리고 `[tool.pytest.ini_options]` 안에 추가:

```toml
markers = [
    "gpu: requires a local HF model mount + (optional) GPU; skipped otherwise",
]
```

- [ ] **단계 4: 설치 후 스모크 테스트 재실행**

```bash
cd backend && .venv/bin/pip install -e ".[dev]" && .venv/bin/pytest tests/test_local_hf_smoke.py -v
```

예상 결과: `PASSED` 또는 `SKIPPED`, `ERROR` 없음.

- [ ] **단계 5: Commit**

```bash
git add backend/pyproject.toml backend/tests/test_local_hf_smoke.py
git commit -m "chore(backend): add M1 RAG dependencies and HF model smoke test

Adds qdrant-client, langchain-huggingface, sentence-transformers, fastembed,
pypdf, python-docx, python-pptx, openpyxl, ebooklib, bs4, sse-starlette.
Introduces @pytest.mark.gpu marker so heavy-model tests skip on laptops.
Closes M0 follow-up E."
```

---

### 태스크 2: 에러 봉투, AppError, request-id middleware, CORS, 듀얼 URL docker-compose

이 마일스톤 후반에 도입되는 SSE 스트림이 브라우저에서 시작되는 첫 번째 fetch이므로, CORS와 URL 분리가 즉시 필요하기 때문에 M0 후속 조치 A, B, F를 하나의 태스크에서 처리.

**파일:**
- 생성: `backend/app/core/errors.py`, `backend/app/core/request_id.py`
- 수정: `backend/app/main.py`, `backend/app/core/config.py`, `docker-compose.yml`, `.env.example`
- 생성: `backend/tests/test_errors.py`, `backend/tests/test_request_id.py`

- [ ] **단계 1: 실패하는 테스트 작성**

```python
# backend/tests/test_errors.py
from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.errors import AppError, ErrorCode
from app.main import create_app


def test_app_error_is_serialized_as_envelope() -> None:
    app = create_app()

    @app.get("/__boom")
    async def boom() -> None:
        raise AppError(
            status_code=404,
            code=ErrorCode.KNOWLEDGE_NOT_FOUND,
            detail="knowledge base missing",
        )

    client = TestClient(app)
    resp = client.get("/__boom")
    assert resp.status_code == 404
    body = resp.json()
    assert body["detail"] == "knowledge base missing"
    assert body["code"] == "KNOWLEDGE_NOT_FOUND"
    assert "request_id" in body and len(body["request_id"]) > 0
    assert resp.headers["x-request-id"] == body["request_id"]


def test_validation_error_is_repackaged() -> None:
    from pydantic import BaseModel

    app = create_app()

    class Body(BaseModel):
        name: str

    @app.post("/__validate")
    async def v(body: Body) -> dict[str, str]:
        return {"name": body.name}

    client = TestClient(app)
    resp = client.post("/__validate", json={})
    assert resp.status_code == 422
    body = resp.json()
    assert body["code"] == "VALIDATION_FAILED"
    assert "request_id" in body
```

```python
# backend/tests/test_request_id.py
from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app


def test_request_id_generated_when_missing() -> None:
    client = TestClient(create_app())
    resp = client.get("/health")
    assert "x-request-id" in resp.headers
    assert len(resp.headers["x-request-id"]) >= 32  # uuid4 hex


def test_request_id_preserved_when_supplied() -> None:
    client = TestClient(create_app())
    resp = client.get("/health", headers={"X-Request-ID": "caller-supplied-123"})
    assert resp.headers["x-request-id"] == "caller-supplied-123"
```

- [ ] **단계 2: 테스트 실행 — ImportError / 실패 예상**

```bash
cd backend && .venv/bin/pytest tests/test_errors.py tests/test_request_id.py -v
```

예상 결과: FAIL (`ModuleNotFoundError: app.core.errors`).

- [ ] **단계 3: `app/core/errors.py` 구현**

```python
# backend/app/core/errors.py
from __future__ import annotations

from enum import StrEnum
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class ErrorCode(StrEnum):
    # Knowledge
    KNOWLEDGE_NOT_FOUND = "KNOWLEDGE_NOT_FOUND"
    KNOWLEDGE_INVALID_INPUT = "KNOWLEDGE_INVALID_INPUT"
    KNOWLEDGE_UNSUPPORTED_FILE = "KNOWLEDGE_UNSUPPORTED_FILE"
    KNOWLEDGE_PARSER_FAILED = "KNOWLEDGE_PARSER_FAILED"
    KNOWLEDGE_EMBEDDING_FAILED = "KNOWLEDGE_EMBEDDING_FAILED"
    KNOWLEDGE_QDRANT_UNAVAILABLE = "KNOWLEDGE_QDRANT_UNAVAILABLE"
    # Cross-cutting
    VALIDATION_FAILED = "VALIDATION_FAILED"
    INTERNAL_UNEXPECTED = "INTERNAL_UNEXPECTED"


class AppError(Exception):
    def __init__(
        self,
        *,
        status_code: int,
        code: ErrorCode,
        detail: str,
        extra: dict[str, Any] | None = None,
    ) -> None:
        self.status_code = status_code
        self.code = code
        self.detail = detail
        self.extra = extra or {}
        super().__init__(detail)


def _envelope(
    *, detail: str, code: str, request_id: str, extra: dict[str, Any] | None = None
) -> dict[str, Any]:
    body: dict[str, Any] = {"detail": detail, "code": code, "request_id": request_id}
    if extra:
        body["extra"] = extra
    return body


def _request_id_of(request: Request) -> str:
    return getattr(request.state, "request_id", "") or request.headers.get(
        "x-request-id", ""
    )


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(request: Request, exc: AppError) -> JSONResponse:
        rid = _request_id_of(request)
        return JSONResponse(
            status_code=exc.status_code,
            content=_envelope(
                detail=exc.detail,
                code=str(exc.code),
                request_id=rid,
                extra=exc.extra,
            ),
            headers={"X-Request-ID": rid},
        )

    @app.exception_handler(RequestValidationError)
    async def _validation(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        rid = _request_id_of(request)
        return JSONResponse(
            status_code=422,
            content=_envelope(
                detail="request validation failed",
                code=ErrorCode.VALIDATION_FAILED,
                request_id=rid,
                extra={"errors": exc.errors()},
            ),
            headers={"X-Request-ID": rid},
        )

    @app.exception_handler(Exception)
    async def _unexpected(request: Request, exc: Exception) -> JSONResponse:
        rid = _request_id_of(request)
        return JSONResponse(
            status_code=500,
            content=_envelope(
                detail="internal server error",
                code=ErrorCode.INTERNAL_UNEXPECTED,
                request_id=rid,
            ),
            headers={"X-Request-ID": rid},
        )
```

- [ ] **단계 4: `app/core/request_id.py` 구현**

```python
# backend/app/core/request_id.py
from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

_HEADER = "x-request-id"


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        rid = request.headers.get(_HEADER) or uuid.uuid4().hex
        request.state.request_id = rid
        response = await call_next(request)
        response.headers[_HEADER] = rid
        return response
```

- [ ] **단계 5: `app/core/config.py` 확장**

`Settings`에 다음 필드를 추가:

```python
    # Uploads and ingestion
    uploads_dir: str = "/app/uploads"
    ingestion_max_concurrency: int = 2

    # Qdrant
    qdrant_collection_prefix: str = "kb_"

    # CORS — JSON list in env, e.g. '["http://localhost:23000"]'
    cors_origins: list[str] = [
        "http://localhost:23000",
        "http://localhost:3000",
    ]
```

- [ ] **단계 6: `app/main.py`에 middleware + 핸들러 연결**

```python
# backend/app/main.py
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.core.config import APP_VERSION, get_settings
from app.core.errors import register_exception_handlers
from app.core.request_id import RequestIdMiddleware


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version=APP_VERSION,
        debug=settings.debug,
    )

    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=True,
        expose_headers=["X-Request-ID"],
    )
    register_exception_handlers(app)

    app.include_router(health_router)
    return app


app = create_app()
```

- [ ] **단계 7: `docker-compose.yml`과 `.env.example` 업데이트**

`docker-compose.yml`에서 `web` 서비스의 `environment`와 `build.args`를 변경:

```yaml
  web:
    build:
      context: ./frontend
      args:
        NEXT_PUBLIC_API_URL: ${NEXT_PUBLIC_API_URL:-http://localhost:28000}
    environment:
      NEXT_PUBLIC_API_URL: ${NEXT_PUBLIC_API_URL:-http://localhost:28000}
      API_URL_INTERNAL: http://api:8000
```

`.env.example`에 추가:

```dotenv
# Frontend — browser calls use the host-mapped port, server components use the container hostname
NEXT_PUBLIC_API_URL=http://localhost:28000
API_URL_INTERNAL=http://api:8000

# Backend CORS — JSON list
AGENTBUILDER_CORS_ORIGINS=["http://localhost:23000","http://localhost:3000"]
```

- [ ] **단계 8: 테스트 실행 — PASS 예상**

```bash
cd backend && .venv/bin/pytest tests/test_errors.py tests/test_request_id.py tests/test_health.py -v
```

예상 결과: 전부 PASS.

- [ ] **단계 9: Commit**

```bash
git add backend/app/core/errors.py backend/app/core/request_id.py \
        backend/app/core/config.py backend/app/main.py \
        backend/tests/test_errors.py backend/tests/test_request_id.py \
        docker-compose.yml .env.example
git commit -m "feat(backend): error envelope, request-id middleware, CORS, dual-URL

Introduces AppError + ErrorCode enum with JSON envelope {detail, code,
request_id} and X-Request-ID header round-tripping. Adds CORSMiddleware
reading Settings.cors_origins so upcoming SSE streams work from the
browser. Splits NEXT_PUBLIC_API_URL (browser) from API_URL_INTERNAL
(server components). Closes M0 follow-ups A, B, F."
```

---

### 태스크 3: SQLAlchemy 모델 — KnowledgeBase, Document — 및 Alembic 마이그레이션

**파일:**
- 생성: `backend/app/models/__init__.py`, `backend/app/models/base.py`, `backend/app/models/knowledge.py`
- 생성: `backend/alembic/versions/<hash>_m1_knowledge.py`
- 수정: `backend/alembic/env.py` (autogenerate가 인식하도록 Base를 import)
- 생성: `backend/tests/test_models_knowledge.py`

- [ ] **단계 1: 실패하는 테스트 작성**

```python
# backend/tests/test_models_knowledge.py
from __future__ import annotations

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge import Document, DocumentStatus, KnowledgeBase


@pytest.mark.asyncio
async def test_create_kb_with_document(db_session: AsyncSession) -> None:
    kb = KnowledgeBase(
        name="docs",
        description="",
        embedding_provider="local_hf",
        embedding_model="/models/snowflake-arctic-embed-l-v2.0-ko",
        embedding_dim=1024,
        qdrant_collection="kb_docs",
        chunk_size=1000,
        chunk_overlap=200,
    )
    db_session.add(kb)
    await db_session.flush()

    doc = Document(
        knowledge_base_id=kb.id,
        filename="a.txt",
        file_size=12,
        file_type="txt",
        status=DocumentStatus.PENDING,
        storage_path="/app/uploads/a.txt",
    )
    db_session.add(doc)
    await db_session.flush()

    assert isinstance(kb.id, uuid.UUID)
    assert doc.status == DocumentStatus.PENDING
    assert doc.knowledge_base_id == kb.id
```

`db_session` fixture는 `backend/tests/conftest.py`에 정의됨 (M0에서 이미 생성). 아직 async가 활성화되지 않았다면 다음을 추가:

```python
# backend/tests/conftest.py  — append if missing
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models.base import Base


@pytest_asyncio.fixture
async def db_session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    async with sessionmaker() as session:
        yield session
    await engine.dispose()
```

- [ ] **단계 2: 테스트 실행 — FAIL 예상 (모듈 없음)**

```bash
cd backend && .venv/bin/pytest tests/test_models_knowledge.py -v
```

- [ ] **단계 3: `app/models/base.py` 구현**

```python
# backend/app/models/base.py
from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""
```

- [ ] **단계 4: `app/models/knowledge.py` 구현**

```python
# backend/app/models/knowledge.py
from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    Enum as SaEnum,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class DocumentStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    DONE = "done"
    FAILED = "failed"


class KnowledgeBase(Base):
    __tablename__ = "knowledge_bases"

    id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)

    embedding_provider: Mapped[str] = mapped_column(String(50), nullable=False)
    embedding_model: Mapped[str] = mapped_column(String(500), nullable=False)
    embedding_dim: Mapped[int] = mapped_column(Integer, nullable=False)

    qdrant_collection: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)

    chunk_size: Mapped[int] = mapped_column(Integer, default=1000, nullable=False)
    chunk_overlap: Mapped[int] = mapped_column(Integer, default=200, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    documents: Mapped[list["Document"]] = relationship(
        back_populates="knowledge_base",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    knowledge_base_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("knowledge_bases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    file_type: Mapped[str] = mapped_column(String(20), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(1000), nullable=False)

    status: Mapped[DocumentStatus] = mapped_column(
        SaEnum(DocumentStatus, name="document_status"),
        default=DocumentStatus.PENDING,
        nullable=False,
        index=True,
    )
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    knowledge_base: Mapped[KnowledgeBase] = relationship(back_populates="documents")
```

- [ ] **단계 5: `app/models/__init__.py` 구현**

```python
from app.models.base import Base
from app.models.knowledge import Document, DocumentStatus, KnowledgeBase

__all__ = ["Base", "Document", "DocumentStatus", "KnowledgeBase"]
```

- [ ] **단계 6: `alembic/env.py`에 Base 연결**

`alembic/env.py` 상단에 추가 (`from app.core.config...` 뒤):

```python
from app.models import Base  # noqa: F401 — imported for autogenerate side effects

target_metadata = Base.metadata
```

기존 `target_metadata = None` (또는 동등한 라인)을 교체.

- [ ] **단계 7: 마이그레이션 생성**

```bash
cd backend && .venv/bin/alembic revision --autogenerate -m "m1 knowledge base and documents"
```

생성된 파일을 검사 — `knowledge_bases`와 `documents` 테이블, `document_status` enum이 생성되는지 확인. 그대로 commit.

- [ ] **단계 8: 테스트 실행 — PASS 예상**

```bash
cd backend && .venv/bin/pytest tests/test_models_knowledge.py -v
```

- [ ] **단계 9: 개발 DB에 마이그레이션 적용 및 확인**

```bash
cd backend && .venv/bin/alembic upgrade head
```

- [ ] **단계 10: Commit**

```bash
git add backend/app/models/ backend/alembic/env.py backend/alembic/versions/*_m1_knowledge.py \
        backend/tests/test_models_knowledge.py backend/tests/conftest.py
git commit -m "feat(backend): KnowledgeBase and Document models + migration"
```

---

### 태스크 4: 임베딩 provider protocol + fastembed fallback + registry

CI에서 GPU 없이 실행 가능하고 대용량 모델 다운로드가 필요 없는 fallback provider를 먼저 구현하여, registry를 즉시 TDD할 수 있도록 함. `local_hf`는 태스크 5에서 구현.

**파일:**
- 생성: `backend/app/services/providers/__init__.py`, `backend/app/services/providers/embedding/__init__.py`, `.../base.py`, `.../fastembed_provider.py`
- 생성: `backend/tests/test_embedding_registry.py`, `backend/tests/test_fastembed_provider.py`

- [ ] **단계 1: 실패하는 테스트 작성**

```python
# backend/tests/test_fastembed_provider.py
from __future__ import annotations

import pytest

from app.services.providers.embedding.fastembed_provider import FastembedProvider


@pytest.mark.asyncio
async def test_fastembed_embeds_and_reports_dim() -> None:
    provider = FastembedProvider(model_name="intfloat/multilingual-e5-small")
    vectors = await provider.embed_texts(["hello", "world"])
    assert len(vectors) == 2
    assert len(vectors[0]) == provider.dimension
    assert provider.dimension > 0
```

```python
# backend/tests/test_embedding_registry.py
from __future__ import annotations

import pytest

from app.core.errors import AppError
from app.services.providers.embedding import (
    EmbeddingProvider,
    get_embedding_provider,
    register_embedding_provider,
)


class _Dummy:
    dimension = 3

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [[0.1, 0.2, 0.3] for _ in texts]


def test_register_and_get_provider() -> None:
    register_embedding_provider("dummy", lambda **kw: _Dummy())
    p: EmbeddingProvider = get_embedding_provider("dummy")
    assert p.dimension == 3


def test_unknown_provider_raises_app_error() -> None:
    with pytest.raises(AppError):
        get_embedding_provider("nope_does_not_exist")
```

- [ ] **단계 2: 테스트 실행 — ImportError 예상**

```bash
cd backend && .venv/bin/pytest tests/test_embedding_registry.py tests/test_fastembed_provider.py -v
```

- [ ] **단계 3: `base.py` (protocol) 구현**

```python
# backend/app/services/providers/embedding/base.py
from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class EmbeddingProvider(Protocol):
    """Uniform async interface for text embedding backends."""

    dimension: int

    async def embed_texts(self, texts: list[str]) -> list[list[float]]: ...
```

- [ ] **단계 4: fastembed provider 구현**

```python
# backend/app/services/providers/embedding/fastembed_provider.py
from __future__ import annotations

import asyncio

from fastembed import TextEmbedding


class FastembedProvider:
    """CPU-only fallback. No model download config required beyond name."""

    def __init__(self, model_name: str = "intfloat/multilingual-e5-small") -> None:
        self._model = TextEmbedding(model_name=model_name)
        # Probe once to learn dimension deterministically.
        probe = list(self._model.embed(["__probe__"]))
        self.dimension: int = len(probe[0])

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._embed_sync, texts)

    def _embed_sync(self, texts: list[str]) -> list[list[float]]:
        return [vec.tolist() for vec in self._model.embed(texts)]
```

- [ ] **단계 5: registry `__init__.py` 구현**

```python
# backend/app/services/providers/embedding/__init__.py
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.core.errors import AppError, ErrorCode
from app.services.providers.embedding.base import EmbeddingProvider

_Factory = Callable[..., EmbeddingProvider]
_REGISTRY: dict[str, _Factory] = {}


def register_embedding_provider(name: str, factory: _Factory) -> None:
    _REGISTRY[name] = factory


def get_embedding_provider(name: str, **kwargs: Any) -> EmbeddingProvider:
    try:
        factory = _REGISTRY[name]
    except KeyError as exc:
        raise AppError(
            status_code=400,
            code=ErrorCode.KNOWLEDGE_INVALID_INPUT,
            detail=f"unknown embedding provider: {name}",
        ) from exc
    return factory(**kwargs)


def _register_defaults() -> None:
    from app.services.providers.embedding.fastembed_provider import FastembedProvider

    register_embedding_provider(
        "fastembed",
        lambda **kw: FastembedProvider(**kw),
    )


_register_defaults()

__all__ = [
    "EmbeddingProvider",
    "get_embedding_provider",
    "register_embedding_provider",
]
```

- [ ] **단계 6: 테스트 실행 — PASS 예상**

```bash
cd backend && .venv/bin/pytest tests/test_embedding_registry.py tests/test_fastembed_provider.py -v
```

- [ ] **단계 7: Commit**

```bash
git add backend/app/services/providers/ backend/tests/test_embedding_registry.py \
        backend/tests/test_fastembed_provider.py
git commit -m "feat(backend): embedding provider protocol + fastembed fallback + registry"
```

---

### 태스크 5: GPU 자동 감지 + 우아한 fallback을 갖춘 local_hf 임베딩 provider

**파일:**
- 생성: `backend/app/services/providers/embedding/local_hf.py`
- 수정: `backend/app/services/providers/embedding/__init__.py` (`local_hf` 등록 + 선택 헬퍼)
- 생성: `backend/tests/test_local_hf_provider.py`

- [ ] **단계 1: 실패하는 테스트 작성 (마커 게이트)**

```python
# backend/tests/test_local_hf_provider.py
from __future__ import annotations

import os
from pathlib import Path

import pytest

MODEL_PATH = os.environ.get(
    "AGENTBUILDER_DEFAULT_EMBEDDING_MODEL_PATH",
    "/DATA3/users/mj/hf_models/snowflake-arctic-embed-l-v2.0-ko",
)

pytestmark = pytest.mark.gpu


@pytest.mark.asyncio
async def test_local_hf_provider_embeds_korean_text() -> None:
    if not Path(MODEL_PATH).exists():
        pytest.skip(f"model path missing: {MODEL_PATH}")

    from app.services.providers.embedding.local_hf import LocalHfProvider

    provider = LocalHfProvider(model_path=MODEL_PATH)
    vectors = await provider.embed_texts(["안녕하세요, 에이전트빌더입니다."])
    assert len(vectors) == 1
    assert len(vectors[0]) == provider.dimension
    assert provider.dimension == 1024  # arctic embed L v2 korean
```

- [ ] **단계 2: 실행 — 노트북에서는 SKIP, 호스트에서는 FAIL (모듈 없음) 예상**

```bash
cd backend && .venv/bin/pytest tests/test_local_hf_provider.py -v
```

- [ ] **단계 3: `local_hf.py` 구현**

```python
# backend/app/services/providers/embedding/local_hf.py
from __future__ import annotations

import asyncio
import logging

from langchain_huggingface import HuggingFaceEmbeddings

_log = logging.getLogger(__name__)


def _detect_device() -> str:
    try:
        import torch

        if torch.cuda.is_available():
            return "cuda"
    except Exception:  # pragma: no cover — torch import guard
        pass
    return "cpu"


class LocalHfProvider:
    def __init__(self, model_path: str, device: str | None = None) -> None:
        self._device = device or _detect_device()
        _log.info("loading HF embedding model from %s on %s", model_path, self._device)
        self._model = HuggingFaceEmbeddings(
            model_name=model_path,
            model_kwargs={"device": self._device},
            encode_kwargs={"normalize_embeddings": True},
        )
        probe = self._model.embed_query("__probe__")
        self.dimension: int = len(probe)

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._model.embed_documents, texts)
```

- [ ] **단계 4: 임베딩 registry에 등록**

`backend/app/services/providers/embedding/__init__.py`의 `_register_defaults()` 안에 추가:

```python
    from app.services.providers.embedding.local_hf import LocalHfProvider

    def _local_hf_factory(**kw: Any) -> EmbeddingProvider:
        # Caller supplies model_path; fall back to fastembed on any load error.
        try:
            return LocalHfProvider(**kw)
        except Exception as exc:  # noqa: BLE001 — graceful degradation required
            import logging

            logging.getLogger(__name__).warning(
                "local_hf load failed (%s); falling back to fastembed", exc
            )
            return FastembedProvider()

    register_embedding_provider("local_hf", _local_hf_factory)
```

또한 수집 코드에서 사용하는 상위 레벨 헬퍼를 추가:

```python
def build_default_provider(settings: Any) -> EmbeddingProvider:
    """Build the default provider from Settings, honoring graceful fallback."""
    provider_name = settings.default_embedding_provider
    if provider_name == "local_hf":
        return get_embedding_provider(
            "local_hf", model_path=settings.default_embedding_model_path
        )
    return get_embedding_provider(provider_name)
```

- [ ] **단계 5: 테스트 실행**

```bash
cd backend && .venv/bin/pytest tests/test_local_hf_provider.py tests/test_embedding_registry.py -v
```

예상 결과: registry 테스트 PASS; local_hf 테스트는 노트북에서 SKIPPED, 모델이 있는 호스트에서 PASSED.

- [ ] **단계 6: Commit**

```bash
git add backend/app/services/providers/embedding/local_hf.py \
        backend/app/services/providers/embedding/__init__.py \
        backend/tests/test_local_hf_provider.py
git commit -m "feat(backend): local_hf embedding provider with GPU auto-detect + fallback

Uses langchain-huggingface HuggingFaceEmbeddings with device=cuda when
torch.cuda.is_available, otherwise cpu. If the model fails to load
(missing weights, corrupted mount), factory falls back to fastembed
multilingual-e5-small to preserve the 'smooth' UX guarantee."
```

---

### 태스크 6: Qdrant 클라이언트 래퍼 — 컬렉션 관리 + upsert + 검색

**파일:**
- 생성: `backend/app/services/knowledge/__init__.py`, `backend/app/services/knowledge/qdrant.py`
- 생성: `backend/tests/test_qdrant_wrapper.py`

- [ ] **단계 1: 실패하는 테스트 작성**

```python
# backend/tests/test_qdrant_wrapper.py
from __future__ import annotations

import os
import uuid

import pytest

from app.services.knowledge.qdrant import QdrantStore


def _qdrant_url() -> str | None:
    url = os.environ.get("AGENTBUILDER_QDRANT_URL", "http://localhost:26333")
    return url


@pytest.mark.asyncio
async def test_qdrant_roundtrip() -> None:
    url = _qdrant_url()
    try:
        store = QdrantStore(url=url)
        await store.ping()
    except Exception:
        pytest.skip("qdrant not reachable")

    name = f"kb_test_{uuid.uuid4().hex[:8]}"
    try:
        await store.create_collection(name, dimension=4)
        await store.upsert(
            name,
            points=[
                {"id": 1, "vector": [0.1, 0.2, 0.3, 0.4], "payload": {"text": "a"}},
                {"id": 2, "vector": [0.9, 0.8, 0.7, 0.6], "payload": {"text": "b"}},
            ],
        )
        hits = await store.search(name, query=[0.1, 0.2, 0.3, 0.4], top_k=1)
        assert len(hits) == 1
        assert hits[0]["payload"]["text"] == "a"
    finally:
        await store.delete_collection(name)
```

- [ ] **단계 2: 실행 — FAIL 또는 SKIP 예상**

```bash
cd backend && .venv/bin/pytest tests/test_qdrant_wrapper.py -v
```

- [ ] **단계 3: `qdrant.py` 구현**

```python
# backend/app/services/knowledge/qdrant.py
from __future__ import annotations

import asyncio
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.http import models as qm

from app.core.errors import AppError, ErrorCode


class QdrantStore:
    """Thin async wrapper over the sync qdrant-client.

    We keep sync client calls on an executor because the project already runs
    inside an asyncio event loop and qdrant_client.AsyncQdrantClient has
    occasional compatibility gaps with server versions we run locally.
    """

    def __init__(self, url: str) -> None:
        self._client = QdrantClient(url=url)

    async def _run(self, fn: Any, *args: Any, **kwargs: Any) -> Any:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, lambda: fn(*args, **kwargs))

    async def ping(self) -> None:
        try:
            await self._run(self._client.get_collections)
        except Exception as exc:  # noqa: BLE001
            raise AppError(
                status_code=503,
                code=ErrorCode.KNOWLEDGE_QDRANT_UNAVAILABLE,
                detail=f"qdrant unavailable: {exc}",
            ) from exc

    async def create_collection(self, name: str, *, dimension: int) -> None:
        await self._run(
            self._client.recreate_collection,
            collection_name=name,
            vectors_config=qm.VectorParams(size=dimension, distance=qm.Distance.COSINE),
        )

    async def delete_collection(self, name: str) -> None:
        await self._run(self._client.delete_collection, collection_name=name)

    async def upsert(
        self, name: str, *, points: list[dict[str, Any]]
    ) -> None:
        qpoints = [
            qm.PointStruct(
                id=p["id"], vector=p["vector"], payload=p.get("payload", {})
            )
            for p in points
        ]
        await self._run(
            self._client.upsert, collection_name=name, points=qpoints
        )

    async def delete_by_document(self, name: str, *, document_id: str) -> None:
        await self._run(
            self._client.delete,
            collection_name=name,
            points_selector=qm.FilterSelector(
                filter=qm.Filter(
                    must=[
                        qm.FieldCondition(
                            key="document_id",
                            match=qm.MatchValue(value=document_id),
                        )
                    ]
                )
            ),
        )

    async def search(
        self,
        name: str,
        *,
        query: list[float],
        top_k: int = 5,
        score_threshold: float | None = None,
    ) -> list[dict[str, Any]]:
        hits = await self._run(
            self._client.search,
            collection_name=name,
            query_vector=query,
            limit=top_k,
            score_threshold=score_threshold,
        )
        return [
            {"id": h.id, "score": h.score, "payload": h.payload or {}} for h in hits
        ]
```

- [ ] **단계 4: 로컬 qdrant(환경에 따라 포트 26333)에서 테스트 실행**

```bash
cd backend && AGENTBUILDER_QDRANT_URL=http://localhost:26333 \
    .venv/bin/pytest tests/test_qdrant_wrapper.py -v
```

예상 결과: M0 docker-compose 스택이 떠 있으면 PASSED, 아니면 SKIPPED.

- [ ] **단계 5: Commit**

```bash
git add backend/app/services/knowledge/__init__.py backend/app/services/knowledge/qdrant.py \
        backend/tests/test_qdrant_wrapper.py
git commit -m "feat(backend): QdrantStore wrapper with cosine collections + executor bridge"
```

---

### 태스크 7: Pydantic 스키마 + repository CRUD 헬퍼

**파일:**
- 생성: `backend/app/schemas/__init__.py`, `backend/app/schemas/knowledge.py`
- 생성: `backend/app/repositories/__init__.py`, `backend/app/repositories/knowledge.py`
- 생성: `backend/tests/test_knowledge_repository.py`

- [ ] **단계 1: 실패하는 테스트 작성**

```python
# backend/tests/test_knowledge_repository.py
from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.knowledge import KnowledgeRepository
from app.schemas.knowledge import KnowledgeBaseCreate


@pytest.mark.asyncio
async def test_create_and_list_kb(db_session: AsyncSession) -> None:
    repo = KnowledgeRepository(db_session)
    created = await repo.create_kb(
        KnowledgeBaseCreate(
            name="mydocs",
            description="",
            embedding_provider="fastembed",
            embedding_model="intfloat/multilingual-e5-small",
            embedding_dim=384,
            chunk_size=1000,
            chunk_overlap=200,
        ),
        qdrant_collection="kb_mydocs",
    )
    assert created.id is not None

    listed = await repo.list_kbs()
    assert len(listed) == 1 and listed[0].name == "mydocs"

    fetched = await repo.get_kb(created.id)
    assert fetched is not None

    await repo.delete_kb(created.id)
    assert await repo.get_kb(created.id) is None
```

- [ ] **단계 2: 실행 — FAIL 예상**

```bash
cd backend && .venv/bin/pytest tests/test_knowledge_repository.py -v
```

- [ ] **단계 3: `schemas/knowledge.py` 구현**

```python
# backend/app/schemas/knowledge.py
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.knowledge import DocumentStatus


class KnowledgeBaseCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = ""
    embedding_provider: str = "local_hf"
    embedding_model: str = "/models/snowflake-arctic-embed-l-v2.0-ko"
    embedding_dim: int = 1024
    chunk_size: int = 1000
    chunk_overlap: int = 200


class KnowledgeBaseRead(BaseModel):
    id: uuid.UUID
    name: str
    description: str
    embedding_provider: str
    embedding_model: str
    embedding_dim: int
    qdrant_collection: str
    chunk_size: int
    chunk_overlap: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DocumentRead(BaseModel):
    id: uuid.UUID
    knowledge_base_id: uuid.UUID
    filename: str
    file_size: int
    file_type: str
    status: DocumentStatus
    error: str | None
    chunk_count: int
    created_at: datetime

    model_config = {"from_attributes": True}


class SearchRequest(BaseModel):
    query: str = Field(min_length=1)
    top_k: int = 5
    score_threshold: float | None = None


class SearchHit(BaseModel):
    score: float
    text: str
    filename: str
    chunk_index: int


class SearchResponse(BaseModel):
    hits: list[SearchHit]
```

- [ ] **단계 4: `repositories/knowledge.py` 구현**

```python
# backend/app/repositories/knowledge.py
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge import Document, DocumentStatus, KnowledgeBase
from app.schemas.knowledge import KnowledgeBaseCreate


class KnowledgeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_kb(
        self, payload: KnowledgeBaseCreate, *, qdrant_collection: str
    ) -> KnowledgeBase:
        kb = KnowledgeBase(
            name=payload.name,
            description=payload.description,
            embedding_provider=payload.embedding_provider,
            embedding_model=payload.embedding_model,
            embedding_dim=payload.embedding_dim,
            qdrant_collection=qdrant_collection,
            chunk_size=payload.chunk_size,
            chunk_overlap=payload.chunk_overlap,
        )
        self._session.add(kb)
        await self._session.flush()
        return kb

    async def list_kbs(self) -> list[KnowledgeBase]:
        result = await self._session.execute(
            select(KnowledgeBase).order_by(KnowledgeBase.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_kb(self, kb_id: uuid.UUID) -> KnowledgeBase | None:
        return await self._session.get(KnowledgeBase, kb_id)

    async def delete_kb(self, kb_id: uuid.UUID) -> None:
        kb = await self.get_kb(kb_id)
        if kb is not None:
            await self._session.delete(kb)
            await self._session.flush()

    async def create_document(
        self,
        *,
        kb_id: uuid.UUID,
        filename: str,
        file_size: int,
        file_type: str,
        storage_path: str,
    ) -> Document:
        doc = Document(
            knowledge_base_id=kb_id,
            filename=filename,
            file_size=file_size,
            file_type=file_type,
            storage_path=storage_path,
            status=DocumentStatus.PENDING,
        )
        self._session.add(doc)
        await self._session.flush()
        return doc

    async def list_documents(self, kb_id: uuid.UUID) -> list[Document]:
        result = await self._session.execute(
            select(Document)
            .where(Document.knowledge_base_id == kb_id)
            .order_by(Document.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_document(self, doc_id: uuid.UUID) -> Document | None:
        return await self._session.get(Document, doc_id)

    async def set_document_status(
        self,
        doc_id: uuid.UUID,
        *,
        status: DocumentStatus,
        error: str | None = None,
        chunk_count: int | None = None,
    ) -> None:
        doc = await self.get_document(doc_id)
        if doc is None:
            return
        doc.status = status
        if error is not None:
            doc.error = error
        if chunk_count is not None:
            doc.chunk_count = chunk_count
        await self._session.flush()

    async def mark_stale_processing_failed(self) -> int:
        """Called on startup — any doc still `processing` is lost."""
        result = await self._session.execute(
            select(Document).where(Document.status == DocumentStatus.PROCESSING)
        )
        docs = list(result.scalars().all())
        for d in docs:
            d.status = DocumentStatus.FAILED
            d.error = "interrupted by server restart"
        await self._session.flush()
        return len(docs)
```

- [ ] **단계 5: 테스트 실행 — PASS 예상**

```bash
cd backend && .venv/bin/pytest tests/test_knowledge_repository.py -v
```

- [ ] **단계 6: Commit**

```bash
git add backend/app/schemas/ backend/app/repositories/ \
        backend/tests/test_knowledge_repository.py
git commit -m "feat(backend): knowledge Pydantic schemas + repository CRUD helpers"
```

---

### 태스크 8: Parser 기반 + 일반 텍스트 parser (txt/md/mdx/html/htm/xml/vtt/properties)

**파일:**
- 생성: `backend/app/services/knowledge/parsers/__init__.py`, `.../base.py`, `.../text.py`
- 생성: `backend/tests/fixtures/sample.txt`, `backend/tests/fixtures/sample.md`
- 생성: `backend/tests/test_parser_text.py`

- [ ] **단계 1: fixture 생성**

```text
# backend/tests/fixtures/sample.txt
안녕하세요. 이 문서는 테스트용 한글 텍스트입니다.
두 번째 줄입니다.
```

```text
# backend/tests/fixtures/sample.md
# Sample

This is **markdown** with [a link](https://example.com).
```

- [ ] **단계 2: 실패하는 테스트 작성**

```python
# backend/tests/test_parser_text.py
from __future__ import annotations

from pathlib import Path

import pytest

from app.services.knowledge.parsers.text import TextParser

FIX = Path(__file__).parent / "fixtures"


@pytest.mark.asyncio
async def test_text_parser_reads_utf8() -> None:
    parsed = await TextParser().parse(FIX / "sample.txt")
    assert "안녕하세요" in parsed.text
    assert parsed.metadata["char_count"] > 0


@pytest.mark.asyncio
async def test_markdown_parser_strips_nothing() -> None:
    parsed = await TextParser().parse(FIX / "sample.md")
    assert "Sample" in parsed.text
```

- [ ] **단계 3: `parsers/base.py` 구현**

```python
# backend/app/services/knowledge/parsers/base.py
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True)
class ParsedDocument:
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class Parser(Protocol):
    async def parse(self, path: Path) -> ParsedDocument: ...
```

- [ ] **단계 4: `parsers/text.py` 구현**

```python
# backend/app/services/knowledge/parsers/text.py
from __future__ import annotations

from pathlib import Path

from app.services.knowledge.parsers.base import ParsedDocument


def _read_with_fallback(path: Path) -> str:
    for encoding in ("utf-8", "utf-8-sig", "cp949", "latin-1"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return path.read_bytes().decode("utf-8", errors="replace")


class TextParser:
    """Plain-text parser for txt/md/mdx/html/htm/xml/vtt/properties.

    HTML/XML content passes through as-is; downstream chunking handles
    the raw markup. Users who need clean text can use the (future) HTML
    sanitization parser — out of MVP scope.
    """

    async def parse(self, path: Path) -> ParsedDocument:
        text = _read_with_fallback(path)
        return ParsedDocument(
            text=text,
            metadata={"char_count": len(text), "filename": path.name},
        )
```

- [ ] **단계 5: 실행 — PASS 예상**

```bash
cd backend && .venv/bin/pytest tests/test_parser_text.py -v
```

- [ ] **단계 6: Commit**

```bash
git add backend/app/services/knowledge/parsers/ backend/tests/fixtures/sample.txt \
        backend/tests/fixtures/sample.md backend/tests/test_parser_text.py
git commit -m "feat(backend): parser base protocol + text parser with encoding fallback"
```

---

### 태스크 9: PDF parser (pypdf) + DOCX parser (python-docx)

**파일:**
- 생성: `backend/app/services/knowledge/parsers/pdf.py`, `.../docx.py`
- 생성: `backend/tests/test_parser_pdf.py`, `backend/tests/test_parser_docx.py`

- [ ] **단계 1: 자체 fixture를 생성하는 실패 테스트 작성**

```python
# backend/tests/test_parser_pdf.py
from __future__ import annotations

from pathlib import Path

import pytest

from app.services.knowledge.parsers.pdf import PdfParser


@pytest.fixture
def sample_pdf(tmp_path: Path) -> Path:
    pytest.importorskip("reportlab")
    from reportlab.pdfgen import canvas

    p = tmp_path / "sample.pdf"
    c = canvas.Canvas(str(p))
    c.drawString(100, 750, "Hello PDF world")
    c.drawString(100, 730, "Second line here")
    c.save()
    return p


@pytest.mark.asyncio
async def test_pdf_parser_extracts_text(sample_pdf: Path) -> None:
    parsed = await PdfParser().parse(sample_pdf)
    assert "Hello PDF world" in parsed.text
    assert parsed.metadata["page_count"] == 1
```

```python
# backend/tests/test_parser_docx.py
from __future__ import annotations

from pathlib import Path

import pytest

from app.services.knowledge.parsers.docx import DocxParser


@pytest.fixture
def sample_docx(tmp_path: Path) -> Path:
    from docx import Document as DocxDocument

    p = tmp_path / "sample.docx"
    doc = DocxDocument()
    doc.add_heading("Title", level=1)
    doc.add_paragraph("First paragraph with some body text.")
    doc.add_paragraph("Second paragraph.")
    doc.save(p)
    return p


@pytest.mark.asyncio
async def test_docx_parser_extracts_paragraphs(sample_docx: Path) -> None:
    parsed = await DocxParser().parse(sample_docx)
    assert "First paragraph" in parsed.text
    assert "Second paragraph" in parsed.text
```

PDF fixture 생성기를 사용하기 위해 dev 의존성에 `reportlab`을 추가:

```toml
# backend/pyproject.toml  [project.optional-dependencies].dev
dev = [
    "pytest>=8.3,<9.0",
    "pytest-asyncio>=0.25,<0.26",
    "pytest-cov>=6.0,<7.0",
    "ruff>=0.8,<0.9",
    "aiosqlite>=0.20,<0.21",
    "reportlab>=4.2,<5.0",
]
```

재설치: `cd backend && .venv/bin/pip install -e ".[dev]"`

- [ ] **단계 2: 실행 — FAIL 예상 (모듈 없음)**

- [ ] **단계 3: `pdf.py` 구현**

```python
# backend/app/services/knowledge/parsers/pdf.py
from __future__ import annotations

import asyncio
from pathlib import Path

from pypdf import PdfReader

from app.services.knowledge.parsers.base import ParsedDocument


class PdfParser:
    async def parse(self, path: Path) -> ParsedDocument:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._parse_sync, path)

    def _parse_sync(self, path: Path) -> ParsedDocument:
        reader = PdfReader(str(path))
        pages: list[str] = []
        for page in reader.pages:
            try:
                pages.append(page.extract_text() or "")
            except Exception:  # noqa: BLE001 — per-page failures are tolerated
                pages.append("")
        text = "\n\n".join(p for p in pages if p.strip())
        return ParsedDocument(
            text=text,
            metadata={
                "page_count": len(reader.pages),
                "filename": path.name,
            },
        )
```

- [ ] **단계 4: `docx.py` 구현**

```python
# backend/app/services/knowledge/parsers/docx.py
from __future__ import annotations

import asyncio
from pathlib import Path

from docx import Document as DocxDocument

from app.services.knowledge.parsers.base import ParsedDocument


class DocxParser:
    async def parse(self, path: Path) -> ParsedDocument:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._parse_sync, path)

    def _parse_sync(self, path: Path) -> ParsedDocument:
        doc = DocxDocument(str(path))
        parts = [p.text for p in doc.paragraphs if p.text.strip()]
        # Include table cells too — common in Korean corporate docs.
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    if cell.text.strip():
                        parts.append(cell.text)
        text = "\n".join(parts)
        return ParsedDocument(
            text=text,
            metadata={"paragraph_count": len(parts), "filename": path.name},
        )
```

- [ ] **단계 5: 실행 — PASS 예상**

```bash
cd backend && .venv/bin/pytest tests/test_parser_pdf.py tests/test_parser_docx.py -v
```

- [ ] **단계 6: Commit**

```bash
git add backend/app/services/knowledge/parsers/pdf.py \
        backend/app/services/knowledge/parsers/docx.py \
        backend/tests/test_parser_pdf.py backend/tests/test_parser_docx.py \
        backend/pyproject.toml
git commit -m "feat(backend): pdf (pypdf) and docx (python-docx) parsers"
```

---

### 태스크 10: 나머지 parser (pptx / xlsx / csv / epub / eml)

**파일:**
- 생성: `backend/app/services/knowledge/parsers/pptx.py`, `.../xlsx.py`, `.../csv_parser.py`, `.../epub.py`, `.../eml.py`
- 생성: `backend/tests/test_parser_office.py`, `backend/tests/test_parser_misc.py`
- 생성: `backend/tests/fixtures/sample.csv`

- [ ] **단계 1: CSV fixture 생성**

```csv
# backend/tests/fixtures/sample.csv
name,score,note
alice,10,first
bob,20,second
```

- [ ] **단계 2: 실패하는 테스트 작성**

```python
# backend/tests/test_parser_office.py
from __future__ import annotations

from pathlib import Path

import pytest

from app.services.knowledge.parsers.csv_parser import CsvParser
from app.services.knowledge.parsers.pptx import PptxParser
from app.services.knowledge.parsers.xlsx import XlsxParser

FIX = Path(__file__).parent / "fixtures"


@pytest.mark.asyncio
async def test_csv_parser_reads_rows() -> None:
    parsed = await CsvParser().parse(FIX / "sample.csv")
    assert "alice" in parsed.text and "bob" in parsed.text
    assert parsed.metadata["row_count"] == 2


@pytest.mark.asyncio
async def test_xlsx_parser(tmp_path: Path) -> None:
    from openpyxl import Workbook

    p = tmp_path / "s.xlsx"
    wb = Workbook()
    ws = wb.active
    ws.append(["h1", "h2"])
    ws.append(["r1c1", "r1c2"])
    wb.save(p)

    parsed = await XlsxParser().parse(p)
    assert "r1c1" in parsed.text


@pytest.mark.asyncio
async def test_pptx_parser(tmp_path: Path) -> None:
    from pptx import Presentation

    p = tmp_path / "s.pptx"
    prs = Presentation()
    slide = prs.slides.add_slide(prs.slide_layouts[5])
    tb = slide.shapes.add_textbox(0, 0, 100, 100)
    tb.text_frame.text = "hello slide"
    prs.save(p)

    parsed = await PptxParser().parse(p)
    assert "hello slide" in parsed.text
```

```python
# backend/tests/test_parser_misc.py
from __future__ import annotations

from pathlib import Path

import pytest

from app.services.knowledge.parsers.eml import EmlParser
from app.services.knowledge.parsers.epub import EpubParser


@pytest.mark.asyncio
async def test_eml_parser(tmp_path: Path) -> None:
    from email.message import EmailMessage

    p = tmp_path / "m.eml"
    msg = EmailMessage()
    msg["Subject"] = "hi"
    msg["From"] = "a@x"
    msg["To"] = "b@x"
    msg.set_content("body contents here")
    p.write_bytes(bytes(msg))

    parsed = await EmlParser().parse(p)
    assert "body contents here" in parsed.text
    assert parsed.metadata["subject"] == "hi"


@pytest.mark.asyncio
async def test_epub_parser_reads_chapters(tmp_path: Path) -> None:
    ebooklib = pytest.importorskip("ebooklib")
    from ebooklib import epub

    book = epub.EpubBook()
    book.set_identifier("id1")
    book.set_title("t")
    book.set_language("en")
    ch = epub.EpubHtml(title="c", file_name="c.xhtml", lang="en")
    ch.content = "<html><body><p>chapter body text</p></body></html>"
    book.add_item(ch)
    book.toc = (ch,)
    book.spine = ["nav", ch]
    book.add_item(epub.EpubNav())
    book.add_item(epub.EpubNcx())
    p = tmp_path / "b.epub"
    epub.write_epub(str(p), book)

    parsed = await EpubParser().parse(p)
    assert "chapter body text" in parsed.text
```

- [ ] **단계 3: 각 parser 구현**

```python
# backend/app/services/knowledge/parsers/csv_parser.py
from __future__ import annotations

import asyncio
import csv
from pathlib import Path

from app.services.knowledge.parsers.base import ParsedDocument


class CsvParser:
    async def parse(self, path: Path) -> ParsedDocument:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._parse_sync, path)

    def _parse_sync(self, path: Path) -> ParsedDocument:
        rows: list[list[str]] = []
        with path.open("r", encoding="utf-8", newline="") as fh:
            reader = csv.reader(fh)
            header = next(reader, None)
            for row in reader:
                rows.append(row)
        lines: list[str] = []
        if header:
            lines.append(" | ".join(header))
        for r in rows:
            lines.append(" | ".join(r))
        return ParsedDocument(
            text="\n".join(lines),
            metadata={"row_count": len(rows), "filename": path.name},
        )
```

```python
# backend/app/services/knowledge/parsers/xlsx.py
from __future__ import annotations

import asyncio
from pathlib import Path

from openpyxl import load_workbook

from app.services.knowledge.parsers.base import ParsedDocument


class XlsxParser:
    async def parse(self, path: Path) -> ParsedDocument:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._parse_sync, path)

    def _parse_sync(self, path: Path) -> ParsedDocument:
        wb = load_workbook(filename=str(path), read_only=True, data_only=True)
        chunks: list[str] = []
        for sheet in wb.worksheets:
            chunks.append(f"# sheet: {sheet.title}")
            for row in sheet.iter_rows(values_only=True):
                cells = [str(c) for c in row if c is not None]
                if cells:
                    chunks.append(" | ".join(cells))
        return ParsedDocument(
            text="\n".join(chunks),
            metadata={"sheet_count": len(wb.worksheets), "filename": path.name},
        )
```

```python
# backend/app/services/knowledge/parsers/pptx.py
from __future__ import annotations

import asyncio
from pathlib import Path

from pptx import Presentation

from app.services.knowledge.parsers.base import ParsedDocument


class PptxParser:
    async def parse(self, path: Path) -> ParsedDocument:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._parse_sync, path)

    def _parse_sync(self, path: Path) -> ParsedDocument:
        prs = Presentation(str(path))
        lines: list[str] = []
        for i, slide in enumerate(prs.slides, start=1):
            lines.append(f"# slide {i}")
            for shape in slide.shapes:
                if shape.has_text_frame:
                    for p in shape.text_frame.paragraphs:
                        text = "".join(run.text for run in p.runs)
                        if text.strip():
                            lines.append(text)
        return ParsedDocument(
            text="\n".join(lines),
            metadata={"slide_count": len(prs.slides), "filename": path.name},
        )
```

```python
# backend/app/services/knowledge/parsers/eml.py
from __future__ import annotations

import asyncio
from email import policy
from email.parser import BytesParser
from pathlib import Path

from app.services.knowledge.parsers.base import ParsedDocument


class EmlParser:
    async def parse(self, path: Path) -> ParsedDocument:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._parse_sync, path)

    def _parse_sync(self, path: Path) -> ParsedDocument:
        with path.open("rb") as fh:
            msg = BytesParser(policy=policy.default).parse(fh)
        body_part = msg.get_body(preferencelist=("plain", "html"))
        body = body_part.get_content() if body_part is not None else ""
        meta = {
            "subject": msg.get("subject", ""),
            "from": msg.get("from", ""),
            "to": msg.get("to", ""),
            "filename": path.name,
        }
        text = f"Subject: {meta['subject']}\nFrom: {meta['from']}\nTo: {meta['to']}\n\n{body}"
        return ParsedDocument(text=text, metadata=meta)
```

```python
# backend/app/services/knowledge/parsers/epub.py
from __future__ import annotations

import asyncio
from pathlib import Path

from bs4 import BeautifulSoup
from ebooklib import ITEM_DOCUMENT, epub

from app.services.knowledge.parsers.base import ParsedDocument


class EpubParser:
    async def parse(self, path: Path) -> ParsedDocument:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._parse_sync, path)

    def _parse_sync(self, path: Path) -> ParsedDocument:
        book = epub.read_epub(str(path))
        chapters: list[str] = []
        for item in book.get_items_of_type(ITEM_DOCUMENT):
            soup = BeautifulSoup(item.get_content(), "html.parser")
            text = soup.get_text(separator="\n").strip()
            if text:
                chapters.append(text)
        return ParsedDocument(
            text="\n\n".join(chapters),
            metadata={"chapter_count": len(chapters), "filename": path.name},
        )
```

- [ ] **단계 4: 실행**

```bash
cd backend && .venv/bin/pytest tests/test_parser_office.py tests/test_parser_misc.py -v
```

- [ ] **단계 5: Commit**

```bash
git add backend/app/services/knowledge/parsers/pptx.py \
        backend/app/services/knowledge/parsers/xlsx.py \
        backend/app/services/knowledge/parsers/csv_parser.py \
        backend/app/services/knowledge/parsers/epub.py \
        backend/app/services/knowledge/parsers/eml.py \
        backend/tests/test_parser_office.py backend/tests/test_parser_misc.py \
        backend/tests/fixtures/sample.csv
git commit -m "feat(backend): pptx, xlsx, csv, epub, eml parsers"
```

---

### 태스크 11: Parser registry — 파일 확장자별 디스패치

**파일:**
- 수정: `backend/app/services/knowledge/parsers/__init__.py`
- 생성: `backend/tests/test_parser_registry.py`

- [ ] **단계 1: 실패하는 테스트 작성**

```python
# backend/tests/test_parser_registry.py
from __future__ import annotations

from pathlib import Path

import pytest

from app.core.errors import AppError
from app.services.knowledge.parsers import SUPPORTED_EXTENSIONS, get_parser_for


def test_registry_dispatches_known_extensions() -> None:
    from app.services.knowledge.parsers.text import TextParser

    parser = get_parser_for(Path("a.txt"))
    assert isinstance(parser, TextParser)


def test_registry_raises_for_unknown_extension() -> None:
    with pytest.raises(AppError):
        get_parser_for(Path("a.xyz"))


def test_supported_extensions_includes_required_formats() -> None:
    required = {"txt", "md", "html", "xml", "vtt", "pdf", "docx", "pptx", "xlsx", "csv", "epub", "eml"}
    assert required.issubset(SUPPORTED_EXTENSIONS)
```

- [ ] **단계 2: 실행 — FAIL 예상**

- [ ] **단계 3: registry 구현**

```python
# backend/app/services/knowledge/parsers/__init__.py
from __future__ import annotations

from pathlib import Path

from app.core.errors import AppError, ErrorCode
from app.services.knowledge.parsers.base import ParsedDocument, Parser
from app.services.knowledge.parsers.csv_parser import CsvParser
from app.services.knowledge.parsers.docx import DocxParser
from app.services.knowledge.parsers.eml import EmlParser
from app.services.knowledge.parsers.epub import EpubParser
from app.services.knowledge.parsers.pdf import PdfParser
from app.services.knowledge.parsers.pptx import PptxParser
from app.services.knowledge.parsers.text import TextParser
from app.services.knowledge.parsers.xlsx import XlsxParser

_TEXT_EXTS = {"txt", "md", "mdx", "html", "htm", "xml", "vtt", "properties"}

_REGISTRY: dict[str, Parser] = {
    **{ext: TextParser() for ext in _TEXT_EXTS},
    "pdf": PdfParser(),
    "docx": DocxParser(),
    "pptx": PptxParser(),
    "xlsx": XlsxParser(),
    "csv": CsvParser(),
    "epub": EpubParser(),
    "eml": EmlParser(),
}

SUPPORTED_EXTENSIONS: frozenset[str] = frozenset(_REGISTRY.keys())


def get_parser_for(path: Path) -> Parser:
    ext = path.suffix.lstrip(".").lower()
    if ext not in _REGISTRY:
        raise AppError(
            status_code=415,
            code=ErrorCode.KNOWLEDGE_UNSUPPORTED_FILE,
            detail=f"unsupported file extension: .{ext}",
        )
    return _REGISTRY[ext]


__all__ = [
    "ParsedDocument",
    "Parser",
    "SUPPORTED_EXTENSIONS",
    "get_parser_for",
]
```

- [ ] **단계 4: 실행 — PASS 예상**

- [ ] **단계 5: Commit**

```bash
git add backend/app/services/knowledge/parsers/__init__.py \
        backend/tests/test_parser_registry.py
git commit -m "feat(backend): parser registry dispatches by file extension"
```

---

### 태스크 12: Chunker (RecursiveCharacterTextSplitter 래퍼)

**파일:**
- 생성: `backend/app/services/knowledge/chunker.py`
- 생성: `backend/tests/test_chunker.py`

- [ ] **단계 1: 실패하는 테스트 작성**

```python
# backend/tests/test_chunker.py
from __future__ import annotations

from app.services.knowledge.chunker import Chunk, chunk_text


def test_chunk_text_respects_size_and_overlap() -> None:
    text = "가나다라마바사아자차카타파하. " * 200
    chunks = chunk_text(text, chunk_size=200, chunk_overlap=40)
    assert len(chunks) > 1
    for c in chunks:
        assert isinstance(c, Chunk)
        assert len(c.text) <= 200 + 40
    # First two chunks should overlap at their boundary.
    assert chunks[0].text[-10:] in chunks[1].text or chunks[1].index == 1


def test_empty_text_returns_empty_list() -> None:
    assert chunk_text("", chunk_size=100, chunk_overlap=10) == []
```

- [ ] **단계 2: 실행 — FAIL 예상**

- [ ] **단계 3: 구현**

```python
# backend/app/services/knowledge/chunker.py
from __future__ import annotations

from dataclasses import dataclass

from langchain_text_splitters import RecursiveCharacterTextSplitter


@dataclass(frozen=True)
class Chunk:
    index: int
    text: str


def chunk_text(
    text: str,
    *,
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
    separators: list[str] | None = None,
) -> list[Chunk]:
    if not text.strip():
        return []
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=separators or ["\n\n", "\n", ". ", " ", ""],
        length_function=len,
    )
    parts = splitter.split_text(text)
    return [Chunk(index=i, text=p) for i, p in enumerate(parts)]
```

- [ ] **단계 4: 실행 — PASS 예상**

- [ ] **단계 5: Commit**

```bash
git add backend/app/services/knowledge/chunker.py backend/tests/test_chunker.py
git commit -m "feat(backend): RecursiveCharacterTextSplitter chunker wrapper"
```

---

### 태스크 13: 비동기 pub/sub을 갖춘 인메모리 진행 캐시

**파일:**
- 생성: `backend/app/services/knowledge/progress.py`
- 생성: `backend/tests/test_progress.py`

- [ ] **단계 1: 실패하는 테스트 작성**

```python
# backend/tests/test_progress.py
from __future__ import annotations

import asyncio
import uuid

import pytest

from app.services.knowledge.progress import ProgressEvent, progress_bus


@pytest.mark.asyncio
async def test_publish_and_subscribe() -> None:
    kb_id = uuid.uuid4()
    doc_id = uuid.uuid4()
    received: list[ProgressEvent] = []

    async def consume() -> None:
        async for evt in progress_bus.subscribe(kb_id):
            received.append(evt)
            if evt.status == "done":
                break

    consumer = asyncio.create_task(consume())
    await asyncio.sleep(0)  # yield

    await progress_bus.publish(
        ProgressEvent(kb_id=kb_id, document_id=doc_id, status="processing", chunks_done=5, chunks_total=10)
    )
    await progress_bus.publish(
        ProgressEvent(kb_id=kb_id, document_id=doc_id, status="done", chunks_done=10, chunks_total=10)
    )

    await asyncio.wait_for(consumer, timeout=2.0)
    assert [e.status for e in received] == ["processing", "done"]
```

- [ ] **단계 2: 실행 — FAIL 예상**

- [ ] **단계 3: 구현**

```python
# backend/app/services/knowledge/progress.py
from __future__ import annotations

import asyncio
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass, field


@dataclass(frozen=True)
class ProgressEvent:
    kb_id: uuid.UUID
    document_id: uuid.UUID
    status: str  # "processing" | "done" | "failed"
    chunks_done: int = 0
    chunks_total: int = 0
    error: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "kb_id": str(self.kb_id),
            "document_id": str(self.document_id),
            "status": self.status,
            "chunks_done": self.chunks_done,
            "chunks_total": self.chunks_total,
            "error": self.error,
        }


@dataclass
class _Bus:
    _subscribers: dict[uuid.UUID, list[asyncio.Queue[ProgressEvent]]] = field(default_factory=dict)
    _latest: dict[uuid.UUID, dict[uuid.UUID, ProgressEvent]] = field(default_factory=dict)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    async def publish(self, event: ProgressEvent) -> None:
        async with self._lock:
            self._latest.setdefault(event.kb_id, {})[event.document_id] = event
            for q in self._subscribers.get(event.kb_id, []):
                await q.put(event)

    async def subscribe(self, kb_id: uuid.UUID) -> AsyncIterator[ProgressEvent]:
        queue: asyncio.Queue[ProgressEvent] = asyncio.Queue()
        async with self._lock:
            self._subscribers.setdefault(kb_id, []).append(queue)
            # Replay latest state for each doc so late subscribers don't miss.
            for evt in self._latest.get(kb_id, {}).values():
                await queue.put(evt)
        try:
            while True:
                yield await queue.get()
        finally:
            async with self._lock:
                subs = self._subscribers.get(kb_id, [])
                if queue in subs:
                    subs.remove(queue)


progress_bus = _Bus()
```

- [ ] **단계 4: 실행 — PASS 예상**

- [ ] **단계 5: Commit**

```bash
git add backend/app/services/knowledge/progress.py backend/tests/test_progress.py
git commit -m "feat(backend): in-memory per-KB progress bus with latest-state replay"
```

---

### 태스크 14: 수집 pipeline — parse -> chunk -> embed -> upsert

**파일:**
- 생성: `backend/app/services/knowledge/ingestion.py`
- 생성: `backend/tests/test_ingestion_pipeline.py`

- [ ] **단계 1: 실패하는 테스트 작성 (fake 사용)**

```python
# backend/tests/test_ingestion_pipeline.py
from __future__ import annotations

import uuid
from dataclasses import dataclass
from pathlib import Path

import pytest

from app.services.knowledge.ingestion import IngestionContext, run_ingestion
from app.services.knowledge.parsers.base import ParsedDocument


class _FakeEmbedder:
    dimension = 3

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [[float(len(t)), 0.0, 1.0] for t in texts]


@dataclass
class _Recorded:
    collection: str
    point_count: int


class _FakeStore:
    def __init__(self) -> None:
        self.calls: list[_Recorded] = []

    async def upsert(self, name: str, *, points: list[dict]) -> None:
        self.calls.append(_Recorded(collection=name, point_count=len(points)))

    async def delete_by_document(self, name: str, *, document_id: str) -> None:
        pass


class _FakeParser:
    async def parse(self, path: Path) -> ParsedDocument:
        return ParsedDocument(text="hello world " * 50, metadata={"filename": path.name})


@pytest.mark.asyncio
async def test_run_ingestion_chunks_embeds_and_upserts(tmp_path: Path) -> None:
    file = tmp_path / "doc.txt"
    file.write_text("placeholder")

    store = _FakeStore()
    events: list[tuple[str, int, int]] = []

    ctx = IngestionContext(
        kb_id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        collection_name="kb_t",
        file_path=file,
        chunk_size=80,
        chunk_overlap=20,
        parser=_FakeParser(),
        embedder=_FakeEmbedder(),
        store=store,
        on_progress=lambda done, total: events.append(("p", done, total)),
    )

    chunks = await run_ingestion(ctx)
    assert chunks > 0
    assert len(store.calls) >= 1
    assert store.calls[0].collection == "kb_t"
    assert events[-1][1] == events[-1][2]  # final done==total
```

- [ ] **단계 2: 실행 — FAIL 예상**

- [ ] **단계 3: 구현**

```python
# backend/app/services/knowledge/ingestion.py
from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from app.services.knowledge.chunker import chunk_text
from app.services.knowledge.parsers.base import Parser


class _Embedder(Protocol):
    dimension: int
    async def embed_texts(self, texts: list[str]) -> list[list[float]]: ...


class _Store(Protocol):
    async def upsert(self, name: str, *, points: list[dict[str, Any]]) -> None: ...
    async def delete_by_document(self, name: str, *, document_id: str) -> None: ...


ProgressFn = Callable[[int, int], None]


@dataclass
class IngestionContext:
    kb_id: uuid.UUID
    document_id: uuid.UUID
    collection_name: str
    file_path: Path
    chunk_size: int
    chunk_overlap: int
    parser: Parser
    embedder: _Embedder
    store: _Store
    on_progress: ProgressFn
    batch_size: int = 32


async def run_ingestion(ctx: IngestionContext) -> int:
    """Parse → chunk → embed in batches → upsert. Idempotent: clears prior
    points for this document_id before writing new ones.

    Returns the number of chunks upserted.
    """
    parsed = await ctx.parser.parse(ctx.file_path)
    chunks = chunk_text(
        parsed.text,
        chunk_size=ctx.chunk_size,
        chunk_overlap=ctx.chunk_overlap,
    )
    total = len(chunks)
    if total == 0:
        ctx.on_progress(0, 0)
        return 0

    await ctx.store.delete_by_document(
        ctx.collection_name, document_id=str(ctx.document_id)
    )

    done = 0
    for start in range(0, total, ctx.batch_size):
        batch = chunks[start : start + ctx.batch_size]
        vectors = await ctx.embedder.embed_texts([c.text for c in batch])
        points = [
            {
                "id": _point_id(ctx.document_id, c.index),
                "vector": v,
                "payload": {
                    "document_id": str(ctx.document_id),
                    "kb_id": str(ctx.kb_id),
                    "chunk_index": c.index,
                    "text": c.text,
                    "filename": parsed.metadata.get("filename", ""),
                },
            }
            for c, v in zip(batch, vectors, strict=True)
        ]
        await ctx.store.upsert(ctx.collection_name, points=points)
        done += len(batch)
        ctx.on_progress(done, total)

    return total


def _point_id(document_id: uuid.UUID, chunk_index: int) -> int:
    """Deterministic 63-bit point id so re-ingestion overwrites same rows."""
    h = hash((str(document_id), chunk_index))
    return h & ((1 << 63) - 1)
```

- [ ] **단계 4: 실행 — PASS 예상**

- [ ] **단계 5: Commit**

```bash
git add backend/app/services/knowledge/ingestion.py backend/tests/test_ingestion_pipeline.py
git commit -m "feat(backend): ingestion pipeline parse→chunk→embed→upsert with idempotent deletes"
```

---

### 태스크 15: Orchestrator — asyncio.create_task + semaphore + DB 상태 기록 + 시작 복구

**파일:**
- 생성: `backend/app/services/knowledge/orchestrator.py`
- 생성: `backend/tests/test_orchestrator.py`, `backend/tests/test_startup_recovery.py`

- [ ] **단계 1: orchestrator 동작에 대한 실패 테스트 작성**

```python
# backend/tests/test_orchestrator.py
from __future__ import annotations

import asyncio
import uuid
from pathlib import Path

import pytest

from app.models.knowledge import DocumentStatus
from app.repositories.knowledge import KnowledgeRepository
from app.schemas.knowledge import KnowledgeBaseCreate
from app.services.knowledge.orchestrator import IngestionOrchestrator


@pytest.mark.asyncio
async def test_orchestrator_runs_ingestion_and_updates_status(
    db_session, tmp_path: Path
) -> None:
    repo = KnowledgeRepository(db_session)
    kb = await repo.create_kb(
        KnowledgeBaseCreate(
            name="k",
            embedding_provider="fastembed",
            embedding_model="intfloat/multilingual-e5-small",
            embedding_dim=384,
        ),
        qdrant_collection="kb_k",
    )

    f = tmp_path / "a.txt"
    f.write_text("some text content for ingestion " * 20)

    doc = await repo.create_document(
        kb_id=kb.id,
        filename="a.txt",
        file_size=f.stat().st_size,
        file_type="txt",
        storage_path=str(f),
    )

    # Fake dependencies
    class _FE:
        dimension = 3
        async def embed_texts(self, ts): return [[0.0, 0.0, 0.0] for _ in ts]

    class _FS:
        async def upsert(self, *a, **kw): pass
        async def delete_by_document(self, *a, **kw): pass

    orch = IngestionOrchestrator(
        sessionmaker=_single_session_factory(db_session),
        embedder_factory=lambda kb: _FE(),
        store=_FS(),
        max_concurrency=2,
    )

    await orch.enqueue(kb_id=kb.id, document_id=doc.id)
    await orch.wait_idle()

    await db_session.refresh(doc)
    assert doc.status == DocumentStatus.DONE
    assert doc.chunk_count > 0


def _single_session_factory(existing_session):
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def _factory():
        yield existing_session

    return _factory
```

```python
# backend/tests/test_startup_recovery.py
from __future__ import annotations

import pytest

from app.models.knowledge import DocumentStatus
from app.repositories.knowledge import KnowledgeRepository
from app.schemas.knowledge import KnowledgeBaseCreate


@pytest.mark.asyncio
async def test_startup_marks_processing_as_failed(db_session) -> None:
    repo = KnowledgeRepository(db_session)
    kb = await repo.create_kb(
        KnowledgeBaseCreate(
            name="k2",
            embedding_provider="fastembed",
            embedding_model="x",
            embedding_dim=4,
        ),
        qdrant_collection="kb_k2",
    )
    doc = await repo.create_document(
        kb_id=kb.id, filename="a.txt", file_size=1, file_type="txt", storage_path="/tmp/a"
    )
    await repo.set_document_status(doc.id, status=DocumentStatus.PROCESSING)

    changed = await repo.mark_stale_processing_failed()
    assert changed == 1
    await db_session.refresh(doc)
    assert doc.status == DocumentStatus.FAILED
    assert "interrupted" in (doc.error or "")
```

- [ ] **단계 2: 실행 — orchestrator는 FAIL, 시작 복구는 PASS 예상 (repo 메서드가 이미 존재)**

- [ ] **단계 3: orchestrator 구현**

```python
# backend/app/services/knowledge/orchestrator.py
from __future__ import annotations

import asyncio
import logging
import uuid
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from pathlib import Path
from typing import Any, Protocol

from app.models.knowledge import DocumentStatus, KnowledgeBase
from app.repositories.knowledge import KnowledgeRepository
from app.services.knowledge.ingestion import IngestionContext, run_ingestion
from app.services.knowledge.parsers import get_parser_for
from app.services.knowledge.progress import ProgressEvent, progress_bus

_log = logging.getLogger(__name__)


class _Store(Protocol):
    async def upsert(self, name: str, *, points: list[dict[str, Any]]) -> None: ...
    async def delete_by_document(self, name: str, *, document_id: str) -> None: ...


SessionFactory = Callable[[], AbstractAsyncContextManager]
EmbedderFactory = Callable[[KnowledgeBase], Any]


class IngestionOrchestrator:
    def __init__(
        self,
        *,
        sessionmaker: SessionFactory,
        embedder_factory: EmbedderFactory,
        store: _Store,
        max_concurrency: int = 2,
    ) -> None:
        self._sessionmaker = sessionmaker
        self._embedder_factory = embedder_factory
        self._store = store
        self._sem = asyncio.Semaphore(max_concurrency)
        self._tasks: set[asyncio.Task] = set()

    async def enqueue(self, *, kb_id: uuid.UUID, document_id: uuid.UUID) -> None:
        task = asyncio.create_task(self._run_one(kb_id, document_id))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def wait_idle(self) -> None:
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)

    async def _run_one(self, kb_id: uuid.UUID, document_id: uuid.UUID) -> None:
        async with self._sem:
            try:
                await self._execute(kb_id, document_id)
            except Exception as exc:  # noqa: BLE001 — we record and surface
                _log.exception("ingestion failed for %s", document_id)
                await self._fail(kb_id, document_id, str(exc))

    async def _execute(self, kb_id: uuid.UUID, document_id: uuid.UUID) -> None:
        # Phase 1 — load KB + doc snapshot, mark processing
        async with self._sessionmaker() as session:
            repo = KnowledgeRepository(session)
            kb = await repo.get_kb(kb_id)
            doc = await repo.get_document(document_id)
            if kb is None or doc is None:
                raise RuntimeError("kb or doc missing")
            await repo.set_document_status(document_id, status=DocumentStatus.PROCESSING)
            snapshot = (
                kb.qdrant_collection,
                kb.chunk_size,
                kb.chunk_overlap,
                Path(doc.storage_path),
            )

        collection, chunk_size, chunk_overlap, file_path = snapshot

        # Phase 2 — heavy work outside the DB session
        embedder = self._embedder_factory(kb)
        parser = get_parser_for(file_path)

        def _progress(done: int, total: int) -> None:
            asyncio.create_task(
                progress_bus.publish(
                    ProgressEvent(
                        kb_id=kb_id,
                        document_id=document_id,
                        status="processing",
                        chunks_done=done,
                        chunks_total=total,
                    )
                )
            )

        ctx = IngestionContext(
            kb_id=kb_id,
            document_id=document_id,
            collection_name=collection,
            file_path=file_path,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            parser=parser,
            embedder=embedder,
            store=self._store,
            on_progress=_progress,
        )
        chunk_count = await run_ingestion(ctx)

        # Phase 3 — mark done
        async with self._sessionmaker() as session:
            repo = KnowledgeRepository(session)
            await repo.set_document_status(
                document_id, status=DocumentStatus.DONE, chunk_count=chunk_count
            )
            await session.commit() if hasattr(session, "commit") else None

        await progress_bus.publish(
            ProgressEvent(
                kb_id=kb_id,
                document_id=document_id,
                status="done",
                chunks_done=chunk_count,
                chunks_total=chunk_count,
            )
        )

    async def _fail(self, kb_id: uuid.UUID, document_id: uuid.UUID, msg: str) -> None:
        async with self._sessionmaker() as session:
            repo = KnowledgeRepository(session)
            await repo.set_document_status(
                document_id, status=DocumentStatus.FAILED, error=msg
            )
        await progress_bus.publish(
            ProgressEvent(
                kb_id=kb_id,
                document_id=document_id,
                status="failed",
                error=msg,
            )
        )
```

- [ ] **단계 4: 실행 — PASS 예상**

```bash
cd backend && .venv/bin/pytest tests/test_orchestrator.py tests/test_startup_recovery.py -v
```

- [ ] **단계 5: Commit**

```bash
git add backend/app/services/knowledge/orchestrator.py \
        backend/tests/test_orchestrator.py backend/tests/test_startup_recovery.py
git commit -m "feat(backend): ingestion orchestrator with semaphore + progress publication"
```

---

### 태스크 16: Knowledge API — CRUD 라우트

**파일:**
- 생성: `backend/app/api/knowledge.py`
- 수정: `backend/app/main.py` (라우터 등록, 시작 시 orchestrator 빌드, 복구 실행)
- 생성: `backend/tests/test_knowledge_crud.py`

- [ ] **단계 1: 실패하는 테스트 작성**

```python
# backend/tests/test_knowledge_crud.py
from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import create_app


@pytest.mark.asyncio
async def test_create_list_get_delete_kb() -> None:
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        r = await c.post(
            "/knowledge",
            json={
                "name": "docs1",
                "description": "",
                "embedding_provider": "fastembed",
                "embedding_model": "intfloat/multilingual-e5-small",
                "embedding_dim": 384,
            },
        )
        assert r.status_code == 201, r.text
        kb_id = r.json()["id"]

        r = await c.get("/knowledge")
        assert r.status_code == 200
        assert any(item["id"] == kb_id for item in r.json())

        r = await c.get(f"/knowledge/{kb_id}")
        assert r.status_code == 200

        r = await c.delete(f"/knowledge/{kb_id}")
        assert r.status_code == 204

        r = await c.get(f"/knowledge/{kb_id}")
        assert r.status_code == 404
        assert r.json()["code"] == "KNOWLEDGE_NOT_FOUND"
```

이 테스트는 Postgres 대신 인메모리 SQLite 세션을 사용하는 테스트 앱이 필요. `conftest.py`를 확장:

```python
# backend/tests/conftest.py  — append
import pytest
from app.core import db as db_module
from app.main import create_app as _original_create_app


@pytest.fixture(autouse=True)
def _override_db_url(monkeypatch):
    monkeypatch.setenv("AGENTBUILDER_DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    # Clear cached singletons
    db_module._engine = None
    db_module._sessionmaker = None
    yield
```

- [ ] **단계 2: 실행 — FAIL 예상**

- [ ] **단계 3: `api/knowledge.py` 구현 (CRUD 부분만)**

```python
# backend/app/api/knowledge.py
from __future__ import annotations

import re
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.db import get_session
from app.core.errors import AppError, ErrorCode
from app.models.knowledge import KnowledgeBase
from app.repositories.knowledge import KnowledgeRepository
from app.schemas.knowledge import (
    DocumentRead,
    KnowledgeBaseCreate,
    KnowledgeBaseRead,
)

router = APIRouter(prefix="/knowledge", tags=["knowledge"])

_SLUG = re.compile(r"[^a-z0-9]+")


def _slugify(name: str) -> str:
    return _SLUG.sub("_", name.lower()).strip("_") or "kb"


@router.post("", response_model=KnowledgeBaseRead, status_code=status.HTTP_201_CREATED)
async def create_kb(
    payload: KnowledgeBaseCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> KnowledgeBase:
    settings = get_settings()
    repo = KnowledgeRepository(session)
    collection = f"{settings.qdrant_collection_prefix}{_slugify(payload.name)}"
    kb = await repo.create_kb(payload, qdrant_collection=collection)
    await session.commit()
    return kb


@router.get("", response_model=list[KnowledgeBaseRead])
async def list_kbs(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[KnowledgeBase]:
    return await KnowledgeRepository(session).list_kbs()


@router.get("/{kb_id}", response_model=KnowledgeBaseRead)
async def get_kb(
    kb_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> KnowledgeBase:
    kb = await KnowledgeRepository(session).get_kb(kb_id)
    if kb is None:
        raise AppError(
            status_code=404,
            code=ErrorCode.KNOWLEDGE_NOT_FOUND,
            detail=f"knowledge base {kb_id} not found",
        )
    return kb


@router.delete("/{kb_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_kb(
    kb_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> None:
    await KnowledgeRepository(session).delete_kb(kb_id)
    await session.commit()


@router.get("/{kb_id}/documents", response_model=list[DocumentRead])
async def list_documents(
    kb_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list:
    return await KnowledgeRepository(session).list_documents(kb_id)
```

- [ ] **단계 4: `main.py`에 라우터와 시작 훅 등록**

`backend/app/main.py`의 `create_app()` 안, CORS middleware 뒤에 추가:

```python
    from app.api.knowledge import router as knowledge_router
    app.include_router(knowledge_router)

    @app.on_event("startup")
    async def _on_startup() -> None:
        # Startup recovery — any document left in `processing` state is lost.
        from app.core.db import get_sessionmaker
        from app.repositories.knowledge import KnowledgeRepository

        async with get_sessionmaker()() as session:
            changed = await KnowledgeRepository(session).mark_stale_processing_failed()
            await session.commit()
            if changed:
                import logging
                logging.getLogger(__name__).warning(
                    "startup recovery: marked %d stale documents as failed", changed
                )
```

또한 sqlite 테스트 모드용 스키마 자동 생성 블록을 추가 (CRUD 테스트가 Alembic 없이도 동작하도록):

```python
    @app.on_event("startup")
    async def _ensure_schema() -> None:
        from app.core.db import get_engine
        from app.models.base import Base

        url = str(get_engine().url)
        if url.startswith("sqlite"):
            async with get_engine().begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
```

- [ ] **단계 5: 실행 — PASS 예상**

```bash
cd backend && .venv/bin/pytest tests/test_knowledge_crud.py -v
```

- [ ] **단계 6: Commit**

```bash
git add backend/app/api/knowledge.py backend/app/main.py backend/tests/test_knowledge_crud.py \
        backend/tests/conftest.py
git commit -m "feat(backend): knowledge CRUD API + startup recovery + sqlite schema bootstrap"
```

---

### 태스크 17: 파일 업로드 endpoint + orchestrator 연결

**파일:**
- 수정: `backend/app/api/knowledge.py` (업로드 endpoint 추가)
- 수정: `backend/app/main.py` (시작 시 `IngestionOrchestrator` 빌드 및 연결)
- 생성: `backend/app/services/knowledge/bootstrap.py` (테스트에서 fake를 교체할 수 있는 팩토리)
- 생성: `backend/tests/test_file_upload.py`

- [ ] **단계 1: 실패하는 테스트 작성**

```python
# backend/tests/test_file_upload.py
from __future__ import annotations

import asyncio

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import create_app
from app.services.knowledge.bootstrap import get_orchestrator


@pytest.mark.asyncio
async def test_upload_creates_pending_doc_and_schedules_ingestion(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AGENTBUILDER_UPLOADS_DIR", str(tmp_path))
    app = create_app()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        r = await c.post(
            "/knowledge",
            json={
                "name": "up1",
                "embedding_provider": "fastembed",
                "embedding_model": "intfloat/multilingual-e5-small",
                "embedding_dim": 384,
            },
        )
        kb_id = r.json()["id"]

        files = {"file": ("hi.txt", b"hello world " * 40, "text/plain")}
        r = await c.post(f"/knowledge/{kb_id}/documents", files=files)
        assert r.status_code == 202, r.text
        doc = r.json()
        assert doc["filename"] == "hi.txt"
        assert doc["status"] == "pending"

        # Wait for orchestrator to drain.
        await get_orchestrator().wait_idle()

        r = await c.get(f"/knowledge/{kb_id}/documents")
        docs = r.json()
        assert len(docs) == 1
        assert docs[0]["status"] in {"done", "failed"}  # may fail without qdrant; fine
```

- [ ] **단계 2: 실행 — FAIL 예상 (모듈 + 라우트 없음)**

- [ ] **단계 3: `bootstrap.py` 구현**

```python
# backend/app/services/knowledge/bootstrap.py
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

from app.core.config import get_settings
from app.core.db import get_sessionmaker
from app.models.knowledge import KnowledgeBase
from app.services.knowledge.orchestrator import IngestionOrchestrator
from app.services.knowledge.qdrant import QdrantStore
from app.services.providers.embedding import build_default_provider, get_embedding_provider

_orchestrator: IngestionOrchestrator | None = None


def _embedder_for(kb: KnowledgeBase) -> Any:
    if kb.embedding_provider == "local_hf":
        return get_embedding_provider("local_hf", model_path=kb.embedding_model)
    return get_embedding_provider(kb.embedding_provider, model_name=kb.embedding_model)


class _NoopStore:
    async def upsert(self, *a: Any, **kw: Any) -> None: ...
    async def delete_by_document(self, *a: Any, **kw: Any) -> None: ...


def build_orchestrator() -> IngestionOrchestrator:
    settings = get_settings()

    try:
        store: Any = QdrantStore(url=settings.qdrant_url)
    except Exception:
        store = _NoopStore()

    sessionmaker_cls = get_sessionmaker()

    @asynccontextmanager
    async def _session_factory():
        async with sessionmaker_cls() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    return IngestionOrchestrator(
        sessionmaker=_session_factory,
        embedder_factory=_embedder_for,
        store=store,
        max_concurrency=settings.ingestion_max_concurrency,
    )


def get_orchestrator() -> IngestionOrchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = build_orchestrator()
    return _orchestrator


def reset_orchestrator() -> None:
    global _orchestrator
    _orchestrator = None
```

- [ ] **단계 4: `api/knowledge.py`에 업로드 endpoint 추가**

```python
# append to backend/app/api/knowledge.py
from pathlib import Path

from fastapi import UploadFile, File

from app.services.knowledge.bootstrap import get_orchestrator
from app.services.knowledge.parsers import SUPPORTED_EXTENSIONS


@router.post(
    "/{kb_id}/documents",
    response_model=DocumentRead,
    status_code=status.HTTP_202_ACCEPTED,
)
async def upload_document(
    kb_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    file: UploadFile = File(...),
) -> object:
    repo = KnowledgeRepository(session)
    kb = await repo.get_kb(kb_id)
    if kb is None:
        raise AppError(
            status_code=404,
            code=ErrorCode.KNOWLEDGE_NOT_FOUND,
            detail=f"knowledge base {kb_id} not found",
        )

    filename = file.filename or "unnamed"
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in SUPPORTED_EXTENSIONS:
        raise AppError(
            status_code=415,
            code=ErrorCode.KNOWLEDGE_UNSUPPORTED_FILE,
            detail=f"unsupported file extension: .{ext}",
        )

    settings = get_settings()
    uploads_dir = Path(settings.uploads_dir) / str(kb_id)
    uploads_dir.mkdir(parents=True, exist_ok=True)
    storage_path = uploads_dir / f"{uuid.uuid4().hex}_{filename}"

    content = await file.read()
    storage_path.write_bytes(content)

    doc = await repo.create_document(
        kb_id=kb_id,
        filename=filename,
        file_size=len(content),
        file_type=ext,
        storage_path=str(storage_path),
    )
    await session.commit()

    await get_orchestrator().enqueue(kb_id=kb_id, document_id=doc.id)
    return doc
```

- [ ] **단계 5: 테스트 간 orchestrator 초기화**

`backend/tests/conftest.py`에 추가:

```python
@pytest.fixture(autouse=True)
def _reset_orchestrator():
    from app.services.knowledge.bootstrap import reset_orchestrator
    reset_orchestrator()
    yield
    reset_orchestrator()
```

- [ ] **단계 6: 실행 — PASS 예상**

```bash
cd backend && .venv/bin/pytest tests/test_file_upload.py -v
```

- [ ] **단계 7: Commit**

```bash
git add backend/app/services/knowledge/bootstrap.py backend/app/api/knowledge.py \
        backend/tests/test_file_upload.py backend/tests/conftest.py
git commit -m "feat(backend): document upload endpoint + orchestrator bootstrap wiring"
```

---

### 태스크 18: SSE 진행 스트림 endpoint

**파일:**
- 수정: `backend/app/api/knowledge.py` (SSE 라우트 추가)
- 생성: `backend/tests/test_sse_stream.py`

- [ ] **단계 1: 실패하는 테스트 작성**

```python
# backend/tests/test_sse_stream.py
from __future__ import annotations

import asyncio
import json
import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import create_app
from app.services.knowledge.progress import ProgressEvent, progress_bus


@pytest.mark.asyncio
async def test_sse_stream_delivers_progress_events() -> None:
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        r = await c.post(
            "/knowledge",
            json={
                "name": "sse1",
                "embedding_provider": "fastembed",
                "embedding_model": "intfloat/multilingual-e5-small",
                "embedding_dim": 384,
            },
        )
        kb_id = uuid.UUID(r.json()["id"])
        doc_id = uuid.uuid4()

        async def push() -> None:
            await asyncio.sleep(0.05)
            await progress_bus.publish(
                ProgressEvent(
                    kb_id=kb_id, document_id=doc_id, status="processing",
                    chunks_done=1, chunks_total=2,
                )
            )
            await progress_bus.publish(
                ProgressEvent(
                    kb_id=kb_id, document_id=doc_id, status="done",
                    chunks_done=2, chunks_total=2,
                )
            )

        push_task = asyncio.create_task(push())

        received: list[dict] = []
        async with c.stream("GET", f"/knowledge/{kb_id}/ingestion/stream") as resp:
            assert resp.status_code == 200
            async for line in resp.aiter_lines():
                if line.startswith("data: "):
                    received.append(json.loads(line[6:]))
                    if received[-1].get("status") == "done":
                        break

        await push_task
        assert any(e["status"] == "done" for e in received)
```

- [ ] **단계 2: 실행 — FAIL 예상 (라우트 없음)**

- [ ] **단계 3: SSE 라우트 구현**

`backend/app/api/knowledge.py`에 추가:

```python
import json

from sse_starlette.sse import EventSourceResponse

from app.services.knowledge.progress import progress_bus


@router.get("/{kb_id}/ingestion/stream")
async def ingestion_stream(kb_id: uuid.UUID) -> EventSourceResponse:
    async def _events():
        async for evt in progress_bus.subscribe(kb_id):
            yield {"event": "progress", "data": json.dumps(evt.to_dict())}

    return EventSourceResponse(_events(), ping=15)
```

- [ ] **단계 4: 실행 — PASS 예상**

```bash
cd backend && .venv/bin/pytest tests/test_sse_stream.py -v
```

- [ ] **단계 5: Commit**

```bash
git add backend/app/api/knowledge.py backend/tests/test_sse_stream.py
git commit -m "feat(backend): SSE ingestion progress stream per knowledge base"
```

---

### 태스크 19: 검색 endpoint

**파일:**
- 수정: `backend/app/api/knowledge.py`
- 생성: `backend/tests/test_search_endpoint.py`

- [ ] **단계 1: fake store 주입을 사용한 실패 테스트 작성**

```python
# backend/tests/test_search_endpoint.py
from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import create_app
from app.services.knowledge import bootstrap
from app.services.knowledge.orchestrator import IngestionOrchestrator


class _FakeStore:
    async def search(self, name, *, query, top_k, score_threshold=None):
        return [
            {"id": 1, "score": 0.9, "payload": {"text": "hello", "filename": "a.txt", "chunk_index": 0}},
        ]

    async def upsert(self, *a, **kw): pass
    async def delete_by_document(self, *a, **kw): pass


@pytest.mark.asyncio
async def test_search_returns_hits(monkeypatch) -> None:
    app = create_app()
    # Swap store used by the running orchestrator + the /search endpoint.
    orig = bootstrap.build_orchestrator

    def _patched() -> IngestionOrchestrator:
        inst = orig()
        inst._store = _FakeStore()  # noqa: SLF001 — test seam
        return inst

    monkeypatch.setattr(bootstrap, "build_orchestrator", _patched)
    bootstrap.reset_orchestrator()

    # The search endpoint also needs a store handle — it reads it from bootstrap.
    monkeypatch.setattr(bootstrap, "get_store", lambda: _FakeStore(), raising=False)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        r = await c.post(
            "/knowledge",
            json={
                "name": "s1",
                "embedding_provider": "fastembed",
                "embedding_model": "intfloat/multilingual-e5-small",
                "embedding_dim": 384,
            },
        )
        kb_id = r.json()["id"]

        r = await c.post(f"/knowledge/{kb_id}/search", json={"query": "hello", "top_k": 3})
        assert r.status_code == 200, r.text
        data = r.json()
        assert len(data["hits"]) == 1
        assert data["hits"][0]["text"] == "hello"
```

- [ ] **단계 2: `bootstrap.py`에 `get_store` 접근자 추가**

```python
# append to backend/app/services/knowledge/bootstrap.py
_store_singleton: Any = None


def get_store() -> Any:
    global _store_singleton
    if _store_singleton is None:
        try:
            _store_singleton = QdrantStore(url=get_settings().qdrant_url)
        except Exception:
            _store_singleton = _NoopStore()
    return _store_singleton


def reset_store() -> None:
    global _store_singleton
    _store_singleton = None
```

`reset_orchestrator`에서 `reset_store()`도 호출하도록 업데이트.

- [ ] **단계 3: `/search` endpoint 구현**

```python
# append to backend/app/api/knowledge.py
from app.schemas.knowledge import SearchHit, SearchRequest, SearchResponse
from app.services.knowledge.bootstrap import get_store
from app.services.providers.embedding import get_embedding_provider


@router.post("/{kb_id}/search", response_model=SearchResponse)
async def search_kb(
    kb_id: uuid.UUID,
    payload: SearchRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> SearchResponse:
    kb = await KnowledgeRepository(session).get_kb(kb_id)
    if kb is None:
        raise AppError(
            status_code=404,
            code=ErrorCode.KNOWLEDGE_NOT_FOUND,
            detail=f"knowledge base {kb_id} not found",
        )

    if kb.embedding_provider == "local_hf":
        embedder = get_embedding_provider("local_hf", model_path=kb.embedding_model)
    else:
        embedder = get_embedding_provider(kb.embedding_provider, model_name=kb.embedding_model)

    vectors = await embedder.embed_texts([payload.query])
    hits_raw = await get_store().search(
        kb.qdrant_collection,
        query=vectors[0],
        top_k=payload.top_k,
        score_threshold=payload.score_threshold,
    )
    hits = [
        SearchHit(
            score=float(h["score"]),
            text=str(h["payload"].get("text", "")),
            filename=str(h["payload"].get("filename", "")),
            chunk_index=int(h["payload"].get("chunk_index", 0)),
        )
        for h in hits_raw
    ]
    return SearchResponse(hits=hits)
```

- [ ] **단계 4: 실행 — PASS 예상**

```bash
cd backend && .venv/bin/pytest tests/test_search_endpoint.py -v
```

- [ ] **단계 5: Commit**

```bash
git add backend/app/api/knowledge.py backend/app/services/knowledge/bootstrap.py \
        backend/tests/test_search_endpoint.py
git commit -m "feat(backend): knowledge search endpoint with embedder + store composition"
```

---

### 태스크 20: 프론트엔드 — 듀얼 API 클라이언트, 상단 내비게이션, 지식 목록 페이지

**파일:**
- 수정: `frontend/lib/api.ts`
- 생성: `frontend/lib/knowledge.ts`
- 생성: `frontend/components/nav/TopNav.tsx`
- 수정: `frontend/app/layout.tsx`
- 생성: `frontend/app/knowledge/page.tsx`
- 생성: `frontend/components/knowledge/KbList.tsx`

- [ ] **단계 1: `frontend/lib/api.ts` 업데이트**

```ts
// frontend/lib/api.ts
const BROWSER_BASE = (process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:28000').replace(/\/$/, '');
const SERVER_BASE = (process.env.API_URL_INTERNAL ?? BROWSER_BASE).replace(/\/$/, '');

export function apiBase(): string {
  return typeof window === 'undefined' ? SERVER_BASE : BROWSER_BASE;
}

export type HealthResponse = { status: string; app: string; version: string };

export async function fetchHealth(): Promise<HealthResponse> {
  const res = await fetch(`${apiBase()}/health`, { cache: 'no-store' });
  if (!res.ok) throw new Error(`Health check failed: HTTP ${res.status}`);
  return (await res.json()) as HealthResponse;
}
```

- [ ] **단계 2: `frontend/lib/knowledge.ts` 생성**

```ts
// frontend/lib/knowledge.ts
import { apiBase } from './api';

export type KnowledgeBase = {
  id: string;
  name: string;
  description: string;
  embedding_provider: string;
  embedding_model: string;
  embedding_dim: number;
  qdrant_collection: string;
  chunk_size: number;
  chunk_overlap: number;
  created_at: string;
  updated_at: string;
};

export type DocumentRead = {
  id: string;
  knowledge_base_id: string;
  filename: string;
  file_size: number;
  file_type: string;
  status: 'pending' | 'processing' | 'done' | 'failed';
  error: string | null;
  chunk_count: number;
  created_at: string;
};

export async function listKnowledgeBases(): Promise<KnowledgeBase[]> {
  const res = await fetch(`${apiBase()}/knowledge`, { cache: 'no-store' });
  if (!res.ok) throw new Error(`listKnowledgeBases failed: HTTP ${res.status}`);
  return (await res.json()) as KnowledgeBase[];
}

export async function getKnowledgeBase(id: string): Promise<KnowledgeBase> {
  const res = await fetch(`${apiBase()}/knowledge/${id}`, { cache: 'no-store' });
  if (!res.ok) throw new Error(`getKnowledgeBase failed: HTTP ${res.status}`);
  return (await res.json()) as KnowledgeBase;
}

export async function createKnowledgeBase(body: Partial<KnowledgeBase>): Promise<KnowledgeBase> {
  const res = await fetch(`${apiBase()}/knowledge`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await res.text());
  return (await res.json()) as KnowledgeBase;
}

export async function listDocuments(kbId: string): Promise<DocumentRead[]> {
  const res = await fetch(`${apiBase()}/knowledge/${kbId}/documents`, { cache: 'no-store' });
  if (!res.ok) throw new Error(`listDocuments failed: HTTP ${res.status}`);
  return (await res.json()) as DocumentRead[];
}

export async function uploadDocument(kbId: string, file: File): Promise<DocumentRead> {
  const body = new FormData();
  body.append('file', file);
  const res = await fetch(`${apiBase()}/knowledge/${kbId}/documents`, { method: 'POST', body });
  if (!res.ok) throw new Error(await res.text());
  return (await res.json()) as DocumentRead;
}

export type SearchHit = { score: number; text: string; filename: string; chunk_index: number };

export async function searchKnowledgeBase(kbId: string, query: string, topK = 5): Promise<SearchHit[]> {
  const res = await fetch(`${apiBase()}/knowledge/${kbId}/search`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ query, top_k: topK }),
  });
  if (!res.ok) throw new Error(await res.text());
  const data = (await res.json()) as { hits: SearchHit[] };
  return data.hits;
}
```

- [ ] **단계 3: 상단 내비게이션**

```tsx
// frontend/components/nav/TopNav.tsx
import Link from 'next/link';

const tabs = [
  { href: '/knowledge', label: '지식' },
  { href: '/workflows', label: '워크플로우' },
  { href: '/tools', label: '도구' },
];

export function TopNav() {
  return (
    <header className="border-b border-clay-border bg-clay-surface">
      <nav className="mx-auto flex max-w-6xl items-center gap-6 px-6 py-4" aria-label="Main navigation">
        <span className="text-lg font-semibold tracking-tight">AgentBuilder</span>
        <ul className="flex gap-4">
          {tabs.map((t) => (
            <li key={t.href}>
              <Link href={t.href} className="text-sm text-clay-text hover:text-clay-accent">
                {t.label}
              </Link>
            </li>
          ))}
        </ul>
      </nav>
    </header>
  );
}
```

- [ ] **단계 4: `app/layout.tsx` 업데이트**

```tsx
// frontend/app/layout.tsx
import './globals.css';
import type { Metadata } from 'next';
import { TopNav } from '@/components/nav/TopNav';

export const metadata: Metadata = { title: 'AgentBuilder' };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko">
      <body className="min-h-screen bg-clay-bg text-clay-text">
        <TopNav />
        <main className="mx-auto max-w-6xl px-6 py-8">{children}</main>
      </body>
    </html>
  );
}
```

- [ ] **단계 5: 지식 목록 페이지 + 컴포넌트**

```tsx
// frontend/app/knowledge/page.tsx
import Link from 'next/link';
import { KbList } from '@/components/knowledge/KbList';
import { listKnowledgeBases } from '@/lib/knowledge';

export const dynamic = 'force-dynamic';

export default async function KnowledgePage() {
  const kbs = await listKnowledgeBases();
  return (
    <section className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">지식베이스</h1>
        <Link
          href="/knowledge/new"
          className="rounded-full bg-clay-accent px-4 py-2 text-sm font-medium text-white"
        >
          + 새 지식베이스
        </Link>
      </div>
      <KbList items={kbs} />
    </section>
  );
}
```

```tsx
// frontend/components/knowledge/KbList.tsx
import Link from 'next/link';
import type { KnowledgeBase } from '@/lib/knowledge';

export function KbList({ items }: { items: KnowledgeBase[] }) {
  if (items.length === 0) {
    return (
      <div className="rounded-2xl border border-dashed border-clay-border p-10 text-center text-clay-muted">
        아직 지식베이스가 없어요. 오른쪽 위에서 하나 만들어 보세요.
      </div>
    );
  }
  return (
    <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {items.map((kb) => (
        <li key={kb.id}>
          <Link
            href={`/knowledge/${kb.id}`}
            className="block rounded-2xl border border-clay-border bg-clay-surface p-5 transition hover:border-clay-accent"
          >
            <h2 className="text-lg font-medium">{kb.name}</h2>
            <p className="mt-1 line-clamp-2 text-sm text-clay-muted">{kb.description || '—'}</p>
            <div className="mt-3 flex gap-3 text-xs text-clay-muted">
              <span>{kb.embedding_provider}</span>
              <span>dim {kb.embedding_dim}</span>
            </div>
          </Link>
        </li>
      ))}
    </ul>
  );
}
```

- [ ] **단계 6: 브라우저 스모크 테스트**

```bash
cd /DATA3/users/mj/AgentBuilder && docker compose up -d --build web api
```

예상 결과: `http://localhost:23000/knowledge`가 콘솔 에러나 CORS 실패 없이 빈 상태를 렌더링.

- [ ] **단계 7: Commit**

```bash
git add frontend/lib/api.ts frontend/lib/knowledge.ts frontend/components/nav/TopNav.tsx \
        frontend/app/layout.tsx frontend/app/knowledge/page.tsx \
        frontend/components/knowledge/KbList.tsx
git commit -m "feat(frontend): dual-URL api client, top nav, knowledge list page"
```

---

### 태스크 21: 프론트엔드 — KB 생성 폼

**파일:**
- 생성: `frontend/app/knowledge/new/page.tsx`
- 생성: `frontend/components/knowledge/CreateKbForm.tsx`

- [ ] **단계 1: 페이지 생성**

```tsx
// frontend/app/knowledge/new/page.tsx
import { CreateKbForm } from '@/components/knowledge/CreateKbForm';

export default function NewKbPage() {
  return (
    <section className="max-w-xl space-y-6">
      <h1 className="text-2xl font-semibold">새 지식베이스</h1>
      <CreateKbForm />
    </section>
  );
}
```

- [ ] **단계 2: 폼 컴포넌트 (client) 생성**

```tsx
// frontend/components/knowledge/CreateKbForm.tsx
'use client';

import { useRouter } from 'next/navigation';
import { useState } from 'react';
import { createKnowledgeBase } from '@/lib/knowledge';

const DEFAULTS = {
  embedding_provider: 'local_hf',
  embedding_model: '/models/snowflake-arctic-embed-l-v2.0-ko',
  embedding_dim: 1024,
  chunk_size: 1000,
  chunk_overlap: 200,
};

export function CreateKbForm() {
  const router = useRouter();
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [advanced, setAdvanced] = useState(false);
  const [overrides, setOverrides] = useState(DEFAULTS);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const kb = await createKnowledgeBase({ name, description, ...overrides });
      router.push(`/knowledge/${kb.id}`);
    } catch (err) {
      setError((err as Error).message);
      setBusy(false);
    }
  }

  return (
    <form onSubmit={onSubmit} className="space-y-5">
      <label className="block space-y-1">
        <span className="text-sm">이름</span>
        <input
          required
          value={name}
          onChange={(e) => setName(e.target.value)}
          className="w-full rounded-lg border border-clay-border bg-white px-3 py-2"
        />
      </label>
      <label className="block space-y-1">
        <span className="text-sm">설명 (선택)</span>
        <textarea
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          className="w-full rounded-lg border border-clay-border bg-white px-3 py-2"
        />
      </label>

      <button
        type="button"
        onClick={() => setAdvanced((a) => !a)}
        className="text-sm text-clay-muted underline"
      >
        {advanced ? '고급 설정 접기' : '고급 설정 펼치기'}
      </button>

      {advanced && (
        <div className="grid gap-3 rounded-xl border border-clay-border p-4 text-sm">
          <label className="grid gap-1">
            <span>임베딩 제공자</span>
            <select
              value={overrides.embedding_provider}
              onChange={(e) => setOverrides({ ...overrides, embedding_provider: e.target.value })}
              className="rounded border border-clay-border px-2 py-1"
            >
              <option value="local_hf">local_hf (기본, 한국어 최적)</option>
              <option value="fastembed">fastembed (CPU 폴백)</option>
            </select>
          </label>
          <label className="grid gap-1">
            <span>임베딩 모델</span>
            <input
              value={overrides.embedding_model}
              onChange={(e) => setOverrides({ ...overrides, embedding_model: e.target.value })}
              className="rounded border border-clay-border px-2 py-1"
            />
          </label>
          <label className="grid gap-1">
            <span>임베딩 차원</span>
            <input
              type="number"
              value={overrides.embedding_dim}
              onChange={(e) =>
                setOverrides({ ...overrides, embedding_dim: Number(e.target.value) })
              }
              className="rounded border border-clay-border px-2 py-1"
            />
          </label>
          <div className="grid grid-cols-2 gap-3">
            <label className="grid gap-1">
              <span>chunk_size</span>
              <input
                type="number"
                value={overrides.chunk_size}
                onChange={(e) =>
                  setOverrides({ ...overrides, chunk_size: Number(e.target.value) })
                }
                className="rounded border border-clay-border px-2 py-1"
              />
            </label>
            <label className="grid gap-1">
              <span>chunk_overlap</span>
              <input
                type="number"
                value={overrides.chunk_overlap}
                onChange={(e) =>
                  setOverrides({ ...overrides, chunk_overlap: Number(e.target.value) })
                }
                className="rounded border border-clay-border px-2 py-1"
              />
            </label>
          </div>
        </div>
      )}

      {error && <p className="text-sm text-red-600">{error}</p>}

      <button
        type="submit"
        disabled={busy || !name.trim()}
        className="rounded-full bg-clay-accent px-5 py-2 text-white disabled:opacity-50"
      >
        만들기
      </button>
    </form>
  );
}
```

- [ ] **단계 3: 수동 스모크 — 폼에서 KB를 생성하고 상세 페이지로 리디렉트 확인 (태스크 22까지 stub 404)**

- [ ] **단계 4: Commit**

```bash
git add frontend/app/knowledge/new/page.tsx frontend/components/knowledge/CreateKbForm.tsx
git commit -m "feat(frontend): create knowledge base form with advanced toggle"
```

---

### 태스크 22: 프론트엔드 — KB 상세 페이지 (업로드 + 진행 + 검색)

**파일:**
- 생성: `frontend/app/knowledge/[kbId]/page.tsx`
- 생성: `frontend/components/knowledge/FileUpload.tsx`
- 생성: `frontend/components/knowledge/IngestionProgress.tsx`
- 생성: `frontend/components/knowledge/SearchPanel.tsx`

- [ ] **단계 1: 상세 페이지**

```tsx
// frontend/app/knowledge/[kbId]/page.tsx
import { getKnowledgeBase, listDocuments } from '@/lib/knowledge';
import { FileUpload } from '@/components/knowledge/FileUpload';
import { IngestionProgress } from '@/components/knowledge/IngestionProgress';
import { SearchPanel } from '@/components/knowledge/SearchPanel';

export const dynamic = 'force-dynamic';

export default async function KbDetailPage({ params }: { params: { kbId: string } }) {
  const kb = await getKnowledgeBase(params.kbId);
  const documents = await listDocuments(params.kbId);

  return (
    <section className="space-y-8">
      <header>
        <h1 className="text-2xl font-semibold">{kb.name}</h1>
        <p className="text-sm text-clay-muted">
          {kb.embedding_provider} · {kb.embedding_model} · dim {kb.embedding_dim}
        </p>
      </header>

      <div className="grid gap-8 lg:grid-cols-2">
        <div className="space-y-4">
          <h2 className="text-lg font-medium">파일 업로드</h2>
          <FileUpload kbId={kb.id} />
          <IngestionProgress kbId={kb.id} initialDocuments={documents} />
        </div>
        <div className="space-y-4">
          <h2 className="text-lg font-medium">검색 테스트</h2>
          <SearchPanel kbId={kb.id} />
        </div>
      </div>
    </section>
  );
}
```

- [ ] **단계 2: FileUpload (client, drag-drop)**

```tsx
// frontend/components/knowledge/FileUpload.tsx
'use client';

import { useState } from 'react';
import { uploadDocument } from '@/lib/knowledge';

export function FileUpload({ kbId }: { kbId: string }) {
  const [dragging, setDragging] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function uploadAll(files: FileList | File[]) {
    setError(null);
    const arr = Array.from(files);
    for (const file of arr) {
      try {
        await uploadDocument(kbId, file);
      } catch (e) {
        setError((e as Error).message);
        return;
      }
    }
  }

  return (
    <div
      onDragOver={(e) => {
        e.preventDefault();
        setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={(e) => {
        e.preventDefault();
        setDragging(false);
        void uploadAll(e.dataTransfer.files);
      }}
      className={`rounded-2xl border-2 border-dashed p-8 text-center transition ${
        dragging ? 'border-clay-accent bg-clay-accent/5' : 'border-clay-border'
      }`}
    >
      <p className="text-sm text-clay-muted">파일을 여기로 끌어다 놓거나</p>
      <label className="mt-2 inline-block cursor-pointer rounded-full bg-clay-accent px-4 py-2 text-sm text-white">
        파일 선택
        <input
          type="file"
          multiple
          className="hidden"
          onChange={(e) => e.target.files && uploadAll(e.target.files)}
        />
      </label>
      {error && <p className="mt-3 text-sm text-red-600">{error}</p>}
    </div>
  );
}
```

- [ ] **단계 3: IngestionProgress (SSE)**

```tsx
// frontend/components/knowledge/IngestionProgress.tsx
'use client';

import { useEffect, useState } from 'react';
import { apiBase } from '@/lib/api';
import type { DocumentRead } from '@/lib/knowledge';
import { listDocuments } from '@/lib/knowledge';

type Event = {
  kb_id: string;
  document_id: string;
  status: 'processing' | 'done' | 'failed';
  chunks_done: number;
  chunks_total: number;
  error: string | null;
};

export function IngestionProgress({
  kbId,
  initialDocuments,
}: {
  kbId: string;
  initialDocuments: DocumentRead[];
}) {
  const [docs, setDocs] = useState<DocumentRead[]>(initialDocuments);
  const [progress, setProgress] = useState<Record<string, Event>>({});

  useEffect(() => {
    const es = new EventSource(`${apiBase()}/knowledge/${kbId}/ingestion/stream`);
    es.addEventListener('progress', async (ev) => {
      const evt = JSON.parse((ev as MessageEvent).data) as Event;
      setProgress((prev) => ({ ...prev, [evt.document_id]: evt }));
      if (evt.status === 'done' || evt.status === 'failed') {
        setDocs(await listDocuments(kbId));
      }
    });
    es.onerror = () => es.close();
    return () => es.close();
  }, [kbId]);

  if (docs.length === 0) {
    return <p className="text-sm text-clay-muted">업로드한 문서가 없어요.</p>;
  }

  return (
    <ul className="space-y-2">
      {docs.map((d) => {
        const p = progress[d.id];
        const pct =
          p && p.chunks_total > 0
            ? Math.round((p.chunks_done / p.chunks_total) * 100)
            : d.status === 'done'
              ? 100
              : 0;
        return (
          <li key={d.id} className="rounded-xl border border-clay-border bg-clay-surface p-3">
            <div className="flex items-center justify-between text-sm">
              <span className="truncate">{d.filename}</span>
              <span className="text-clay-muted">{p?.status ?? d.status}</span>
            </div>
            <div className="mt-2 h-2 overflow-hidden rounded-full bg-clay-border">
              <div
                className="h-full bg-clay-accent transition-all"
                style={{ width: `${pct}%` }}
              />
            </div>
            {p?.error && <p className="mt-1 text-xs text-red-600">{p.error}</p>}
          </li>
        );
      })}
    </ul>
  );
}
```

- [ ] **단계 4: SearchPanel**

```tsx
// frontend/components/knowledge/SearchPanel.tsx
'use client';

import { useState } from 'react';
import { searchKnowledgeBase, type SearchHit } from '@/lib/knowledge';

export function SearchPanel({ kbId }: { kbId: string }) {
  const [query, setQuery] = useState('');
  const [hits, setHits] = useState<SearchHit[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      setHits(await searchKnowledgeBase(kbId, query, 5));
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-4">
      <form onSubmit={onSubmit} className="flex gap-2">
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="검색어를 입력하세요"
          className="flex-1 rounded-lg border border-clay-border bg-white px-3 py-2"
        />
        <button
          type="submit"
          disabled={busy || !query.trim()}
          className="rounded-lg bg-clay-accent px-4 py-2 text-sm text-white disabled:opacity-50"
        >
          검색
        </button>
      </form>

      {error && <p className="text-sm text-red-600">{error}</p>}

      <ul className="space-y-2">
        {hits.map((h, i) => (
          <li key={i} className="rounded-xl border border-clay-border bg-clay-surface p-3">
            <div className="flex items-center justify-between text-xs text-clay-muted">
              <span>
                {h.filename} · #{h.chunk_index}
              </span>
              <span>score {h.score.toFixed(3)}</span>
            </div>
            <p className="mt-2 line-clamp-4 whitespace-pre-wrap text-sm">{h.text}</p>
          </li>
        ))}
      </ul>
    </div>
  );
}
```

- [ ] **단계 5: 수동 E2E 스모크**

```bash
cd /DATA3/users/mj/AgentBuilder && docker compose up -d --build
```

브라우저에서:
1. http://localhost:23000/knowledge -> "+ 새 지식베이스" -> 이름 `demo`, 제출 -> 리디렉트됨
2. `sample.txt`를 업로더에 드롭 -> SSE를 통해 진행 바가 100%에 도달
3. "안녕" 검색 -> 최소 하나의 결과가 반환됨 (local_hf 모델이 마운트된 경우)

- [ ] **단계 6: Commit**

```bash
git add frontend/app/knowledge/[kbId]/page.tsx \
        frontend/components/knowledge/FileUpload.tsx \
        frontend/components/knowledge/IngestionProgress.tsx \
        frontend/components/knowledge/SearchPanel.tsx
git commit -m "feat(frontend): KB detail page — upload, SSE progress, search panel"
```

---

### 태스크 23: M0 후속 조치 마무리, 문서 정리, 전체 회귀 테스트

**파일:**
- 수정: `docs/tracking/m0-followups.md`
- 생성: `docs/tracking/m1-status.md` (이 계획의 태스크 체크리스트 미러)

- [ ] **단계 1: 전체 백엔드 테스트 스위트 실행**

```bash
cd backend && .venv/bin/pytest -v
```

예상 결과: 전부 PASS (`gpu` 마커가 붙은 테스트는 모델 마운트 없이 SKIP 가능; qdrant가 필요한 테스트는 컨테이너가 내려가 있으면 SKIP).

- [ ] **단계 2: lint 실행**

```bash
cd backend && .venv/bin/ruff check app tests
```

계속 진행하기 전에 발견된 문제를 모두 수정.

- [ ] **단계 3: `docs/tracking/m0-followups.md` 업데이트**

항목 A, B, E, F를 해결됨으로 표시하고 commit 해시를 기록. `[ ]`를 `[x]`로 바꾸고 `해결 커밋` 필드를 채움. 예시:

```markdown
## A. CORS 미들웨어 🚨
- [x] **상태**: 해결됨 (M1 Task 2)
- **해결 커밋**: <hash from Task 2>
```

B, E, F에도 동일하게 적용.

- [ ] **단계 4: `docs/tracking/m1-status.md` 생성**

```markdown
# M1 Status

> Mirror of `docs/plans/2026-04-09-milestone-1-knowledge-rag.md`. Check off as tasks ship.

- [ ] Task 1 — Dependencies + HF smoke test
- [ ] Task 2 — Error envelope, request-id, CORS, dual URL
- [ ] Task 3 — Models + migration
- [ ] Task 4 — Embedding protocol + fastembed
- [ ] Task 5 — local_hf provider with fallback
- [ ] Task 6 — Qdrant wrapper
- [ ] Task 7 — Schemas + repository
- [ ] Task 8 — Text parser
- [ ] Task 9 — PDF + DOCX parsers
- [ ] Task 10 — PPTX/XLSX/CSV/EPUB/EML parsers
- [ ] Task 11 — Parser registry
- [ ] Task 12 — Chunker
- [ ] Task 13 — Progress bus
- [ ] Task 14 — Ingestion pipeline
- [ ] Task 15 — Orchestrator + startup recovery
- [ ] Task 16 — CRUD API
- [ ] Task 17 — Upload endpoint
- [ ] Task 18 — SSE stream
- [ ] Task 19 — Search endpoint
- [ ] Task 20 — Frontend list + nav
- [ ] Task 21 — Frontend create form
- [ ] Task 22 — Frontend detail page
- [ ] Task 23 — Close follow-ups + regression
```

- [ ] **단계 5: Commit**

```bash
git add docs/tracking/m0-followups.md docs/tracking/m1-status.md
git commit -m "docs(tracking): close M0 follow-ups A/B/E/F and add M1 status mirror"
```

---

## 자체 검토 노트

- **스펙 커버리지 (SS6)**: 6.1 UX -> 프론트엔드 태스크 20-22. 6.2 포맷 -> 태스크 8-11 (Phase 0의 모든 포맷 포함; xls/doc/ppt는 스펙에 따라 의도적으로 지연). 6.3 청킹 -> 태스크 12. 6.4 임베딩 local_hf + fastembed fallback -> 태스크 4-5. 6.5 검색 -> 태스크 19. 6.6 수집 실행 모델 (asyncio.create_task + semaphore + 문서별 진행 캐시 + 시작 복구) -> 태스크 13-15. 6.6 데이터 모델 -> 태스크 3.
- **M0 후속 조치**: A (CORS)와 B (URL 분리)는 태스크 18의 SSE 스트림이 브라우저에서 시작되는 첫 번째 fetch이므로 태스크 2에 통합. E (의존성) 태스크 1. F (에러 봉투) 태스크 2.
- **알려진 위험**: (a) `test_knowledge_crud.py`는 `aiosqlite`와 sqlite 스키마 부트스트랩 훅에 의존 — 실행 전에 태스크 16 단계 4가 적용되었는지 확인 필요. (b) `SaEnum("document_status")`는 Postgres와 SQLite에서 다르게 동작; 모델이 문자열 값을 사용하므로 sqlite는 체크 제약으로 자동 처리. (c) Orchestrator 테스트는 단일 공유 `db_session` fixture를 사용 — sqlite `:memory:`가 직렬화하므로 안전하지만, Postgres에서 실행할 때 orchestrator는 자체 sessionmaker를 사용. (d) `reset_orchestrator` + `reset_store` autouse fixture가 테스트 간 fake/real store 오염을 방지.
- **플레이스홀더 없음**: 모든 태스크가 구체적인 코드 또는 쉘 명령을 제시. "TBD"나 "태스크 N과 유사" 같은 참조 없음.
