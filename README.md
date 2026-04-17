# AgentBuilder

**노드 기반 AI 에이전트 빌더 플랫폼**

비주얼 캔버스에서 LLM·지식베이스·MCP 도구를 노드로 조립해 에이전트 워크플로우를 만들고 실행합니다. Dify / Langflow / Sim Studio를 벤치마킹한 로컬 우선 플랫폼입니다.

---

## 주요 기능

- **비주얼 워크플로우 캔버스** — React Flow 기반 노드-엣지 편집기, 드래그 앤 드롭으로 워크플로우 조립
- **부드러운 RAG 경험** — 문서 업로드 → 자동 청킹·임베딩 → 실시간 검색 테스트까지 한 화면에서
- **MCP 도구 통합** — STDIO / HTTP-SSE / Streamable HTTP 방식으로 외부 MCP 서버를 등록하고 에이전트에 연결
- **실시간 스트리밍 실행** — LangGraph `astream_events()` 기반 토큰 스트리밍 + 실행 로그
- **모델 프로바이더 추상화** — OpenAI / Anthropic / OpenRouter 를 동등하게 선택 가능

---

## 아키텍처

```
┌─────────────────────────────────────────────────┐
│  Next.js 15 (App Router)  :23000                │
│  React Flow Canvas  ─  Zustand  ─  TanStack Q.  │
└──────────────────────┬──────────────────────────┘
                       │ REST / SSE (HTTP)
┌──────────────────────▼──────────────────────────┐
│  FastAPI  :28000                                 │
│  LangGraph  ─  LangChain MCP Adapters            │
└────────┬───────────────────────┬────────────────┘
         │                       │
┌────────▼────────┐   ┌──────────▼────────────────┐
│  PostgreSQL 16  │   │  Qdrant v1.12              │
│  (메타데이터 DB)  │   │  (벡터 DB / RAG)            │
└─────────────────┘   └───────────────────────────┘
```

**서비스 포트**

| 서비스 | 외부 포트 | 설명 |
|--------|-----------|------|
| Web (Next.js) | 23000 | 브라우저 UI |
| API (FastAPI) | 28000 | REST API / SSE |
| PostgreSQL | 5432 | 메타데이터 DB |
| Qdrant | 6333 | 벡터 DB |

---

## 사전 요구사항

- [Docker](https://docs.docker.com/get-docker/) 24+
- [Docker Compose](https://docs.docker.com/compose/) v2.20+

---

## 빠른 시작

```bash
# 1. 환경 변수 파일 복사
cp .env.example .env

# 2. .env 파일에서 API 키 설정 (선택)
#    LLM/Agent 노드를 사용하려면 필수
#    OPENAI_API_KEY=sk-...
#    ANTHROPIC_API_KEY=sk-ant-...

# 3. 서비스 시작
docker compose up -d

# 4. 브라우저에서 접속
#    UI:     http://localhost:23000
#    API 문서: http://localhost:28000/docs
```

> 첫 실행 시 도커 이미지 빌드와 DB 마이그레이션이 자동으로 진행됩니다. 약 2-3분 소요됩니다.

서비스 상태 확인:

```bash
docker compose ps
docker compose logs -f api   # 백엔드 로그
docker compose logs -f web   # 프론트엔드 로그
```

서비스 중지:

```bash
docker compose down          # 컨테이너만 중지 (데이터 보존)
docker compose down -v       # 컨테이너 + 볼륨 삭제 (데이터 초기화)
```

---

## 환경 변수

`.env.example`을 복사해 `.env`로 사용합니다. 주요 변수:

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `API_PORT` | `8000` | API 컨테이너 내부 포트 |
| `WEB_PORT` | `3000` | Web 컨테이너 내부 포트 |
| `NEXT_PUBLIC_API_URL` | `http://localhost:28000` | 브라우저에서 API를 호출하는 URL |
| `POSTGRES_USER` | `agentbuilder` | PostgreSQL 사용자 |
| `POSTGRES_PASSWORD` | `agentbuilder` | PostgreSQL 비밀번호 |
| `POSTGRES_DB` | `agentbuilder` | PostgreSQL 데이터베이스 이름 |
| `POSTGRES_PORT` | `5432` | PostgreSQL 포트 |
| `QDRANT_PORT` | `6333` | Qdrant HTTP 포트 |
| `HF_MODELS_PATH` | `/DATA3/users/mj/hf_models` | HuggingFace 모델 디렉터리 (호스트 경로) |
| `OPENAI_API_KEY` | *(비어있음)* | OpenAI API 키 |
| `ANTHROPIC_API_KEY` | *(비어있음)* | Anthropic API 키 |

> `NEXT_PUBLIC_API_URL`은 브라우저가 직접 API를 호출하는 주소입니다. 기본값(`http://localhost:28000`)은 호스트 머신에서 접속할 때 사용하는 포트입니다.

---

## 프로젝트 구조

```
AgentBuilder/
├── backend/                  # FastAPI 서비스 (Python 3.13)
│   ├── app/
│   │   ├── api/              # REST 엔드포인트
│   │   │   ├── knowledge.py  # 지식베이스 API
│   │   │   ├── mcp.py        # MCP 서버 API
│   │   │   ├── providers.py  # LLM 프로바이더 API
│   │   │   ├── runs.py       # 워크플로우 실행 API (SSE)
│   │   │   ├── settings.py   # 앱 설정 API
│   │   │   └── workflow.py   # 워크플로우 CRUD API
│   │   ├── core/             # 설정, 데이터베이스
│   │   ├── models/           # SQLAlchemy ORM 모델
│   │   ├── nodes/            # LangGraph 노드 구현
│   │   ├── repositories/     # 데이터 접근 레이어
│   │   ├── schemas/          # Pydantic 스키마
│   │   ├── seed/             # 데모 데이터 시드
│   │   └── services/         # 비즈니스 로직
│   ├── tests/
│   └── pyproject.toml
├── frontend/                 # Next.js 15 앱
│   ├── src/
│   │   ├── app/              # App Router 페이지
│   │   ├── components/       # React 컴포넌트
│   │   └── ...
│   └── package.json
├── docs/
│   └── specs/                # 설계 명세서
├── docker-compose.yml
└── .env.example
```

---

## 노드 타입

| 노드 | 타입 키 | 설명 |
|------|---------|------|
| Chat Input | `chat_input` | 워크플로우 진입점. 사용자 입력을 수신합니다. |
| Chat Output | `chat_output` | 워크플로우 종착점. 최종 응답을 출력합니다. |
| Language Model | `llm` | 단일 LLM 호출. Provider·모델·Temperature 설정 가능. |
| Agent | `agent` | ReAct 에이전트. MCP 도구와 지식베이스를 자율적으로 호출합니다. |
| Knowledge Base | `knowledge_base` | Qdrant 벡터 검색 노드. Top-K 및 스코어 임계값 설정 가능. |
| Prompt Template | `prompt_template` | `{변수명}` 문법으로 프롬프트를 조립합니다. |

### 워크플로우 패턴 예시

| 패턴 | 구성 |
|------|------|
| 단순 챗봇 | Chat Input → LLM → Chat Output |
| RAG 챗봇 | Chat Input → Knowledge Base → Prompt Template → LLM → Chat Output |
| 도구 에이전트 | Chat Input → Agent(+MCP 도구) → Chat Output |
| RAG + 에이전트 | Chat Input → Agent(+KB 도구 +MCP 도구) → Chat Output |

---

## 로컬 개발 환경

Docker 없이 직접 실행할 때는 PostgreSQL과 Qdrant를 별도로 실행한 뒤 아래 절차를 따릅니다.

### 백엔드

```bash
cd backend

# 의존성 설치 (Python 3.13 권장)
pip install -e ".[dev]"

# 환경 변수 설정
export AGENTBUILDER_DATABASE_URL="postgresql+asyncpg://agentbuilder:agentbuilder@localhost:5432/agentbuilder"
export AGENTBUILDER_QDRANT_URL="http://localhost:6333"

# DB 마이그레이션 실행
alembic upgrade head

# 개발 서버 시작 (포트 8000)
uvicorn app.main:app --reload --port 8000
```

### 프론트엔드

```bash
cd frontend

# 의존성 설치
npm install   # 또는 pnpm install

# 환경 변수 설정
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local

# 개발 서버 시작 (포트 3000)
npm run dev
```

### 백엔드 테스트

```bash
cd backend
pytest
```

---

## 알려진 제약사항

- **단일 사용자**: 인증·인가 없음. 신뢰할 수 있는 로컬 네트워크에서만 사용하세요.
- **분기/루프 노드 미지원**: If-Else, Loop 노드는 Phase 2에서 추가 예정입니다.
- **워크플로우 버전 관리 없음**: 변경 이력은 저장되지 않습니다.
- **로컬 임베딩 모델 필요**: 기본 임베딩 모델(`snowflake-arctic-embed-l-v2.0-ko`)이 `HF_MODELS_PATH`에 있어야 합니다.

---

## 관련 문서

- [설계 명세서](docs/specs/2026-04-08-agentbuilder-design.md) — MVP 전체 설계
- [사용 가이드](docs/usage-guide.md) — 단계별 사용 방법
