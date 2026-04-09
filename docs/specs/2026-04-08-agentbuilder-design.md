# AgentBuilder — MVP Design Spec

**작성일**: 2026-04-08
**상태**: Draft (브레인스토밍 1차 합의)
**목적**: Dify / Langflow / Sim Studio를 벤치마킹한 에이전트 빌더 플랫폼의 MVP 설계와 구현 추적

---

## 1. 비전 & 범위

### 1.1 한 줄 요약
사용자가 **노드 기반 캔버스**에서 LLM·지식베이스·MCP 도구를 조립해 **에이전트 워크플로우**를 만들고 실행할 수 있는, 로컬 우선의 에이전트 빌더 플랫폼.

### 1.2 핵심 가치
1. **부드러운 RAG 경험** — 지식베이스 구축이 매끄럽다 (가장 중요한 차별점)
2. **자유로운 조합** — 사용자가 캔버스에서 자유롭게 노드를 조합
3. **외부 MCP 통합** — 표준 MCP 프로토콜로 외부 도구를 자유롭게 가져옴
4. **모델 프로바이더 추상화** — OpenAI / Claude / vLLM을 동등하게 선택

### 1.3 MVP 범위 (Phase 0)
- **단일 사용자**, 인증 없음
- **로컬 개발 + Docker Compose 배포**
- 탭 3개: **지식 / 워크플로우 / 도구**
- 노드 6개: Chat Input / Chat Output / Language Model / Agent / Knowledge Base / Prompt Template
- 외부 MCP 연결 (STDIO + HTTP/SSE)
- 워크플로우 실행 + 실시간 로깅 + 에러 표시

### 1.4 MVP에서 의도적으로 제외
| 기능 | 이유 | 후속 Phase |
|---|---|---|
| 멀티 유저 / 인증 | 단일 사용자 MVP | Phase 2 |
| 분기/루프 노드 (If-Else, Loop) | 조건 엣지 UX 복잡도 | Phase 2 |
| Code / Python Interpreter 노드 | 샌드박싱 보안 이슈 | Phase 3 |
| HTTP Request 노드 | MCP로 대체 가능 | Phase 2 |
| Structured Output / Guardrails / Smart Router | 편의 기능 | Phase 2+ |
| 워크플로우 생성 Assistant Chat (우측 패널) | MVP 이후 | Phase 2 |
| 워크플로우 버전 관리 / 협업 | 단일 사용자 | Phase 3 |
| 워크플로우 템플릿 갤러리 | MVP 이후 | Phase 2 |
| 커스텀 MCP 작성 도우미 | "외부 MCP 가져오기"부터 | Phase 2 |

---

## 2. 기술 스택

### 2.1 백엔드
| 항목 | 선택 | 근거 |
|---|---|---|
| 언어 | **Python 3.11+** | LLM/임베딩/파일파싱 생태계, 프로젝트 기존 스택 |
| 웹 프레임워크 | **FastAPI** | Async, OpenAPI 자동 생성, SSE/WebSocket 친화 |
| 워크플로우 엔진 | **LangGraph** | StateGraph, 조건 엣지, `astream_events()` 실시간 스트리밍 |
| ORM | **SQLAlchemy 2.0 (async)** + Alembic | FastAPI 표준, async 지원 |
| 메타데이터 DB | **PostgreSQL 16** | 처음부터 운영 DB로 (마이그레이션 비용 절감) |
| 벡터 DB | **Qdrant** | 가벼움, Docker 친화, 메타데이터 필터링 |
| 파일 파싱 | **unstructured / pypdf / python-docx / openpyxl** 등 (Phase 0에서 확정) | 무변환 처리 가능한 포맷 우선 |
| MCP 어댑터 | **langchain-mcp-adapters** | MCP → LangChain Tool 자동 변환 |

### 2.2 프론트엔드
| 항목 | 선택 | 근거 |
|---|---|---|
| 프레임워크 | **Next.js 15+ (App Router)** | Dify/Sim Studio 패턴, SSR 옵션 |
| 캔버스 엔진 | **React Flow (xyflow)** | 모든 벤치마크 플랫폼이 채택한 표준 |
| 스타일링 | **Tailwind CSS** + **Clay 디자인 토큰** | DESIGN.md의 Clay 스타일 구현 |
| 상태 관리 | **Zustand** | Dify/Langflow/Sim Studio 모두 사용 |
| 데이터 페칭 | **TanStack Query (React Query)** | 서버 상태 관리 |
| 폼 | **React Hook Form** + **zod** | 노드 설정 폼 |

### 2.3 인프라
| 항목 | 선택 |
|---|---|
| 컨테이너 | **Docker Compose** (4-service: postgres, qdrant, api, web) |
| 로컬 개발 | `docker compose up` 한 줄 |
| 환경 변수 | `.env` + `pydantic-settings` |

---

## 3. 정보 구조 (IA)

### 3.1 Top-Level Navigation
```
┌─────────────────────────────────────────────────┐
│  [Logo]  지식    워크플로우    도구       [User] │
└─────────────────────────────────────────────────┘
```
- **지식**: 지식베이스 자산 관리 (업로드, 임베딩, 검색 테스트)
- **워크플로우**: 워크플로우 자산 관리 + 캔버스 에디터 (스튜디오)
- **도구**: MCP 서버 자산 관리 (등록, credential, 툴 디스커버리)

> **명명 원칙**: 세 탭 모두 "그 안에 들어있는 자산"의 이름을 사용 → 멘탈 모델 일관성

### 3.2 워크플로우 에디터 내부 (Langflow 패턴)
```
┌──┬──────────────────────────────────────────────┐
│🔍│                                               │
│📦│         React Flow Canvas                     │
│🔌│         (노드 + 엣지)                          │
│📄│                                               │
│📊│                                               │
└──┴──────────────────────────────────────────────┘
   ↑
   └─ 좌측 수직 사이드바 (에디터 전용)
      🔍 검색 / 📦 컴포넌트 / 🔌 MCP / 📄 파일 / 📊 실행로그
```

### 3.3 자산 → 워크플로우 참조 모델
```
[지식 탭]                       [도구 탭]
  지식베이스 A ──┐                 ┌── MCP서버 X (filesystem)
  지식베이스 B ──┤                 ├── MCP서버 Y (web-search)
                 │                 │
                 ▼                 ▼
              [워크플로우 탭의 캔버스]
                 ▲                 ▲
                 │                 │
            Knowledge Base 노드   Agent 노드 (TOOLS 슬롯)
```
- 지식과 도구는 워크플로우 외부에 존재하는 **재사용 가능한 자산**
- 캔버스의 노드는 자산을 **참조**할 뿐 (소유 ❌)

---

## 4. 노드 카탈로그 (MVP)

### 4.1 노드 6종

#### 1. Chat Input (Start)
- **역할**: 사용자 입력 수신 (워크플로우 진입점)
- **설정**: placeholder 텍스트
- **출력**: `chat_message: str`
- **LangGraph 매핑**: Entry node, 사용자 입력을 state에 주입

#### 2. Chat Output (End)
- **역할**: 최종 응답 출력 (워크플로우 종착점)
- **설정**: 없음 (단순 전달)
- **입력**: `text: str | Message`
- **LangGraph 매핑**: Exit node

#### 3. Language Model
- **역할**: 단일 LLM 호출 (도구 없음)
- **설정**:
  - Model Provider (OpenAI / Claude / vLLM)
  - Model name (Provider별 동적 목록)
  - Temperature, max tokens
  - System message
- **입력**: `prompt: str`
- **출력**: `response: str`
- **LangGraph 매핑**: 단일 함수 노드

#### 4. Agent (★ 핵심)
- **역할**: ReAct 에이전트 — LLM이 도구를 자율적으로 호출
- **설정**:
  - **Strategy**: ReAct (MVP는 ReAct만)
  - **Model**: Provider + Model 선택
  - **Instruction**: 시스템 프롬프트 (textarea)
  - **Max iterations**: 기본 10
  - **TOOLS**: 등록된 MCP 툴 중 선택 (체크박스, Dify 패턴)
- **입력**: `input: str`
- **출력**: `response: str`
- **LangGraph 매핑**: `create_react_agent(model, tools=[...])` 서브그래프
- **Tool 연결 방식**: **Dify 방식** — Tool은 노드 내부 속성 (별도 노드 ❌)

#### 5. Knowledge Base
- **역할**: Qdrant에서 벡터 검색
- **설정**:
  - 지식베이스 선택 (드롭다운 — 지식 탭에서 등록한 것)
  - Top K (기본 5)
  - Score threshold
  - Include metadata (on/off)
- **입력**: `query: str`
- **출력**: `documents: list[Document]` 또는 직렬화된 텍스트
- **LangGraph 매핑**: Retriever 노드 (LangChain Retriever wrapping)

#### 6. Prompt Template
- **역할**: 변수 치환 (`{input}`, `{search_results}`, `{custom}`)
- **설정**:
  - Template (textarea, `{변수명}` 문법)
  - 변수 슬롯 (자동 추출, 각각 입력 핸들 생성)
- **입력**: 변수 슬롯별 dynamic input
- **출력**: `prompt: str`
- **LangGraph 매핑**: 단순 함수 노드 (str.format)

### 4.2 사용 예시 (조합 가능한 워크플로우)

| 패턴 | 그래프 |
|---|---|
| 단순 챗봇 | `Chat Input → Language Model → Chat Output` |
| RAG 챗봇 | `Chat Input → Knowledge Base → Prompt Template → Language Model → Chat Output` |
| 툴 에이전트 | `Chat Input → Agent(+MCP tools) → Chat Output` |
| RAG + 에이전트 | `Chat Input → Knowledge Base → Agent(+MCP tools) → Chat Output` |

### 4.3 노드 데이터 모델 (개념)
```python
class Node:
    id: str
    type: NodeType  # ChatInput | ChatOutput | LLM | Agent | KnowledgeBase | PromptTemplate
    position: {x, y}
    data: dict  # 노드 타입별 설정값
    inputs: list[Handle]
    outputs: list[Handle]

class Edge:
    id: str
    source: str  # node_id
    source_handle: str
    target: str
    target_handle: str

class Workflow:
    id: UUID
    name: str
    description: str
    nodes: list[Node]
    edges: list[Edge]
    created_at, updated_at
```

---

## 5. Model Provider 추상화

### 5.1 지원 Provider (MVP)

#### Chat (LLM 노드 / Agent 노드)
| Provider | 라이브러리 | 비고 |
|---|---|---|
| **OpenAI** | `langchain-openai` | API key |
| **Claude (Anthropic)** | `langchain-anthropic` | API key |
| **vLLM** | `langchain-openai` (OpenAI 호환 엔드포인트) | base_url + 모델명 |

#### Embedding (Knowledge Base)
| Provider | 라이브러리 | 비고 |
|---|---|---|
| **local_hf (HuggingFace 로컬)** ★ 디폴트 | `langchain-huggingface` (sentence-transformers) | API key 불필요. 디폴트 모델: **Snowflake Arctic Embed L v2.0 Korean** (XLM-RoBERTa Large, 1024 dim, 8194 context). 한국어 RAG 특화. |
| **fastembed (fallback)** | `fastembed` | 로컬 HF 모델 경로 없을 때 fallback. `intfloat/multilingual-e5-small` |
| **OpenAI** | `langchain-openai` | `text-embedding-3-small` / `text-embedding-3-large` |
| **vLLM** | `langchain-openai` (OpenAI 호환) | 사용자가 임베딩 모델 서빙한 경우 |
| ~~Anthropic~~ | — | Anthropic은 first-party 임베딩 API 없음 (chat-only) |

**디폴트 모델 경로**: `/DATA3/users/mj/hf_models/snowflake-arctic-embed-l-v2.0-ko` (호스트), `/models/snowflake-arctic-embed-l-v2.0-ko` (컨테이너 내부)

### 5.2 추상화 인터페이스 (개념)
```python
class ChatProvider(Protocol):
    name: str  # "openai" | "anthropic" | "vllm"
    def list_chat_models(self) -> list[str]: ...
    def make_chat_model(self, model: str, **kwargs) -> BaseChatModel: ...

class EmbeddingProvider(Protocol):
    name: str  # "fastembed" | "openai" | "vllm"
    def list_embedding_models(self) -> list[str]: ...
    def make_embedding_model(self, model: str, **kwargs) -> Embeddings: ...
```

> Chat과 Embedding을 별도 Protocol로 분리 — Anthropic의 embedding 부재를 타입 시스템으로 표현.

### 5.3 적용 지점
- **LLM 노드 / Agent 노드**: ChatProvider에서 선택
- **Knowledge Base 임베딩**: EmbeddingProvider에서 선택 (디폴트 = fastembed)
- **공통 UI**: Provider 드롭다운 + Model 드롭다운 (Provider 선택 시 모델 목록 동적 로드)

### 5.4 인증 정보 저장
- **환경변수**: `.env` + `pydantic-settings`로 시작
- fastembed는 키 불필요 → **첫 사용 friction zero**
- 향후: DB에 암호화 저장 + UI 입력 (Phase 2)

---

## 6. 지식베이스 (RAG) 파이프라인

> **MVP의 핵심 차별점.** "Smooth"가 가장 중요한 영역.

### 6.1 사용자 흐름 (UX)
```
1. 지식 탭 → "+ 새 지식베이스"
2. 이름 입력 (임베딩 모델은 디폴트로 자동 채워짐 — fastembed/multilingual-e5-small)
   └ "고급 설정"을 펼쳐서 OpenAI / vLLM 등으로 변경 가능
3. 파일 업로드 (drag & drop, 다중 파일)
4. 청킹 옵션 (기본값으로 진행 가능)
   - chunk_size, chunk_overlap, separator
5. "임베딩 시작" → 진행률 실시간 표시 (SSE)
6. 완료 후 "검색 테스트" 패널에서 즉시 쿼리 가능
```

> **Smooth 원칙**: API 키 없이도 1~6단계가 처음부터 끝까지 동작해야 함. 모든 디폴트는 "그대로 다음"을 누르면 작동.

### 6.2 지원 파일 포맷 (Phase 0 — 무변환 처리 가능 우선)

> 사용자가 제시한 전체 후보:
> XLSX, CSV, HTML, PPT, EPUB, XLS, XML, VTT, MD, PDF, MARKDOWN, DOC, MSG, DOCX, MDX, TXT, EML, HTM, PROPERTIES, PPTX

**Phase 0 (MVP) — 우선 적용 후보** (라이브러리만으로 바로 처리):

| 포맷 | 라이브러리 | 비고 |
|---|---|---|
| TXT, MD, MDX, HTML, HTM, XML, VTT, PROPERTIES | 표준 텍스트 처리 | 인코딩 자동 감지 |
| PDF | `pypdf` 또는 `pdfplumber` | 텍스트 PDF 우선 (스캔 OCR ❌) |
| DOCX | `python-docx` | 구버전 DOC ❌ |
| PPTX | `python-pptx` | 구버전 PPT ❌ |
| XLSX | `openpyxl` | 구버전 XLS는 `xlrd` 추가 검토 |
| CSV | 표준 라이브러리 / `pandas` | |
| EPUB | `ebooklib` + BeautifulSoup | |
| EML, MSG | `eml-parser` / `extract-msg` | |

**Phase 0에서 제외 후보** (변환/OCR 필요):
- DOC (구 Word, libreoffice 필요)
- PPT (구 PPT, libreoffice 필요)
- XLS (구 Excel, 라이브러리는 있지만 우선순위 낮음)

> ⚠️ **TODO**: Phase 0 진입 시 각 라이브러리 실제 검증 + 최종 확정 필요. `unstructured` 라이브러리 통합 vs 개별 파서 선택도 결정해야 함.

### 6.3 청킹 전략 (MVP)
- **기본**: `RecursiveCharacterTextSplitter` (LangChain)
- **옵션**: chunk_size (기본 1000), chunk_overlap (기본 200), separators
- 향후: 시맨틱 청킹, 마크다운 헤더 기반 청킹 등 (Phase 2)

### 6.4 임베딩 & 인덱싱
- **임베딩 디폴트**: **Snowflake Arctic Embed L v2.0 Korean** (로컬 HF, 1024 dim, 한국어 특화)
  - 경로: `${DEFAULT_EMBEDDING_MODEL_PATH}` (env var)
  - 라이브러리: `langchain-huggingface` → `HuggingFaceEmbeddings(model_name=path)`
  - GPU 가용 시 자동 사용 (`device='cuda'` auto-detect)
- **Fallback**: 로컬 모델 경로가 없으면 `fastembed` + `multilingual-e5-small`로 폴백 (graceful degradation)
- **선택지**: local_hf / fastembed / OpenAI / vLLM (Anthropic 제외)
- **저장**: Qdrant 컬렉션 (지식베이스 1개 = 컬렉션 1개)
- **차원 처리**: 임베딩 모델이 정해지면 컬렉션 차원 고정 (디폴트: 1024) — 변경 시 재인덱싱 필요 (UI에서 경고)
- **메타데이터**: 원본 파일명, 페이지, 청크 인덱스, 업로드 시각

### 6.5 검색
- Cosine similarity (Qdrant 기본)
- Top K + score threshold
- Phase 2 후보: hybrid search (BM25 + dense), reranker

### 6.6 Ingestion 실행 모델 (장기 작업 패턴)
> 공통 원칙은 §8.7과 동일. 여기서는 지식베이스 한정.

- **패턴**: `asyncio.create_task()` 로 파이프라인 태스크를 백그라운드 실행
- **진행 상태**:
  - DB `Document.status` (`pending → processing → done | failed`) + `error` 필드
  - 프로세스 메모리에 per-document 진행률 캐시 (bytes processed / chunks embedded)
- **프론트엔드 스트리밍**: SSE로 진행률 push (`/knowledge/{kb_id}/ingestion/stream`)
- **재시작 복구**: 서버 재시작 시 `processing` 상태였던 문서는 **`failed`로 변경**하고 UI에 "다시 시도" 버튼 표시 (재시도는 idempotent — 해당 문서의 기존 청크를 지우고 재임베딩)
- **동시성 제한**: 단일 사용자 MVP → 동일 지식베이스 내 최대 N개 문서 동시 임베딩 (기본 2). GPU 메모리 보호용. `asyncio.Semaphore`로 제한
- **비선택**: Celery/Redis/RQ는 오버킬 (복잡도 vs 이익 비율 나쁨). 멀티 유저 시 재평가

### 6.6 Knowledge Base 데이터 모델
```python
class KnowledgeBase:
    id: UUID
    name: str
    description: str
    embedding_provider: str
    embedding_model: str
    qdrant_collection: str
    chunk_size: int
    chunk_overlap: int
    created_at, updated_at

class Document:
    id: UUID
    knowledge_base_id: UUID
    filename: str
    file_size: int
    file_type: str
    status: enum  # pending | processing | done | failed
    error: str | None
    chunk_count: int
    created_at
```

---

## 7. 도구 (MCP) 시스템

### 7.1 MCP 연결 방식
| 방식 | MVP | 설명 |
|---|---|---|
| **STDIO** | ✅ | 로컬 바이너리/스크립트 (`npx @modelcontextprotocol/server-filesystem` 등) |
| **Streamable HTTP/SSE** | ✅ | 원격 MCP 서버 (URL + 헤더) |
| **JSON Bulk Import** | ❌ Phase 2 | 여러 서버를 한 번에 등록 |

### 7.2 도구 탭 UX
```
┌─ 도구 탭 ───────────────────────────────────┐
│ + 새 MCP 서버                                │
├──────────────────────────────────────────────┤
│ 📦 filesystem (STDIO)         [활성] [⚙️ 편집] │
│   Tools: read_file, list_dir, write_file ... │
├──────────────────────────────────────────────┤
│ 🌐 web-search (HTTP/SSE)      [활성] [⚙️ 편집] │
│   Tools: search, fetch ...                    │
└──────────────────────────────────────────────┘
```

### 7.3 등록 모달 (Langflow 패턴)
- 탭: **STDIO** | **HTTP/SSE**
- STDIO: command, args, env vars
- HTTP/SSE: URL, headers, env vars
- 등록 시점에 `list_tools` 호출 → 툴 목록 자동 디스커버리 → DB 캐싱

### 7.4 워크플로우와의 연결
- Agent 노드의 `[+ Tool]` 클릭
- 등록된 MCP 서버의 툴 카탈로그 모달
- 체크박스로 다중 선택
- 실행 시점에 `langchain-mcp-adapters`로 LangChain Tool로 변환 후 `create_react_agent`에 전달

### 7.5 데이터 모델
```python
class MCPServer:
    id: UUID
    name: str
    transport: enum  # stdio | http_sse
    config: dict  # transport별 설정 (command/args/url/headers)
    env: dict
    enabled: bool
    discovered_tools: list[ToolMetadata]  # 캐시
    last_discovered_at: datetime
```

---

## 8. 워크플로우 실행 엔진

### 8.1 컴파일 (UI Graph → LangGraph)
```
사용자 캔버스 (JSON)
   ↓
WorkflowCompiler
   ↓
LangGraph StateGraph
   ↓
compiled.astream_events(...)
   ↓
SSE → 프론트엔드
```

### 8.2 핵심 단계
1. **Validate**: 노드/엣지 정합성 검사 (고립 노드, 사이클 등)
2. **Topological sort**: 노드 순서 결정
3. **Build StateGraph**:
   - State 스키마 자동 생성 (노드 input/output 핸들에서 추론)
   - 각 노드 → LangGraph 함수 노드로 컴파일
   - 엣지 → `add_edge`
4. **Compile**: `graph.compile(checkpointer=...)`
5. **Stream execution**: `astream_events()`로 노드별 이벤트 방출

### 8.3 실행 이벤트 (실시간 로깅)
| 이벤트 | 의미 |
|---|---|
| `node_start` | 노드 실행 시작 |
| `node_end` | 노드 실행 종료 + output |
| `node_error` | 노드 실행 실패 + traceback |
| `llm_token` | LLM 토큰 스트리밍 (Language Model / Agent) |
| `tool_call` | MCP 툴 호출 (Agent 내부) |
| `tool_result` | MCP 툴 결과 (Agent 내부) |
| `workflow_end` | 전체 종료 |

### 8.4 스트리밍 채널
- **SSE** (Server-Sent Events): 단방향, FastAPI `EventSourceResponse`로 단순 구현
- 향후 양방향 필요 시 WebSocket 전환 (Phase 2)

### 8.5 실행 히스토리
- 모든 실행 이벤트는 Postgres에 저장 (`workflow_runs` 테이블)
- 워크플로우 에디터 좌측 사이드바 📊 "실행 로그" 탭에서 조회

### 8.6 데이터 모델
```python
class WorkflowRun:
    id: UUID
    workflow_id: UUID
    status: enum  # running | success | failed | cancelled
    started_at: datetime
    ended_at: datetime | None
    input: dict
    output: dict | None
    error: str | None

class RunEvent:
    id: UUID
    run_id: UUID
    timestamp: datetime
    event_type: str
    node_id: str | None
    payload: dict
```

### 8.7 실행 모델 (장기 작업 패턴)

단일 사용자 MVP — 외부 task queue(Celery/RQ/Redis/Temporal) **사용 안 함**.

- **실행 트리거**: `POST /workflows/{id}/runs`가 `WorkflowRun` 레코드를 `running`으로 생성 후, `asyncio.create_task()`로 LangGraph 실행을 백그라운드 시작하고 즉시 `run_id` 반환
- **이벤트 스트리밍**: `GET /runs/{run_id}/events` SSE 엔드포인트가 프로세스 메모리의 asyncio Queue를 구독. LangGraph `astream_events()` → Queue로 push → SSE로 relay
- **영속화**: 모든 `RunEvent`는 동시에 Postgres에 저장 (과거 실행 조회용)
- **취소**: `POST /runs/{run_id}/cancel` → 저장된 `asyncio.Task.cancel()` 호출, `status=cancelled`
- **동시성**: 글로벌 `asyncio.Semaphore(N)` (기본 N=3) — 동시 실행 워크플로우 수 제한 (GPU/API rate limit 보호)
- **재시작 복구**: 서버 재시작 시 `running` 상태 run은 모두 **`failed`로 마크**하고 에러에 "server restart" 기록. 자동 재시도 ❌
- **프로세스 로컬 상태**: `dict[run_id, (asyncio.Task, asyncio.Queue)]` — 단일 프로세스 가정. 향후 워커 멀티프로세스 시 Redis pub/sub 등으로 교체 (Phase 2+)

---

## 9. 테스트/플레이그라운드

### 9.1 워크플로우 테스트 모드
- 에디터 우측 상단 **"▶ 플레이그라운드"** 버튼
- 클릭 시 우측 패널 슬라이드 인 → 채팅 UI
- 사용자 입력 → 워크플로우 실행 → 응답 + 노드별 trace 표시

### 9.2 노드 단위 디버깅
- 각 노드 카드에 "마지막 실행 결과" 토글
- 노드 클릭 → 우측 패널에서 입력/출력 + 에러 확인
- 워크플로우.png의 우측 패널 패턴 차용

### 9.3 에러 표시
- **빌드 에러** (컴파일 시): 잘못된 노드 빨간 외곽선 + 에러 메시지 툴팁
- **런타임 에러** (실행 중): 실패한 노드 빨간색 + 상세 traceback 패널 (접기/펼치기)

---

## 10. UX & 디자인 시스템

### 10.1 기반
- DESIGN.md (Clay 디자인 시스템) 전면 적용
- 워밍 크림 배경(`#faf9f7`), 오트 보더(`#dad4c8`), Roobert 폰트, swatch 컬러 팔레트
- 워크플로우 캔버스에서 노드 카드의 둥근 모서리(24px), 다층 섀도우, 호버 애니메이션 적용

### 10.2 캔버스 노드 시각 디자인
- 노드 카드: 흰 배경 + 오트 보더 + Clay shadow
- 헤더: 노드 타입별 swatch 컬러 (LLM=Slushie, Agent=Ube, KB=Matcha, Prompt=Lemon, IO=Pomegranate)
- 핸들(input/output): 작은 원, hover 시 강조
- 선택 시: focus ring (`rgb(20, 110, 245) solid 2px`)

### 10.3 좌측 사이드바
- 수직 아이콘 바 + 클릭 시 패널 확장
- 컴포넌트 패널: 카테고리별 노드 목록 + drag & drop
- MCP 패널: 등록된 서버 + 툴 목록

---

## 11. 시스템 아키텍처 (다이어그램)

```
┌──────────────────────────────────────────────────┐
│              Browser (Next.js)                    │
│  ┌────────┐  ┌────────────┐  ┌────────┐          │
│  │ 지식 UI │  │ 워크플로우  │  │ 도구 UI │          │
│  │        │  │ (ReactFlow)│  │        │          │
│  └───┬────┘  └──────┬─────┘  └────┬───┘          │
│      │ REST + SSE  │              │              │
└──────┼─────────────┼──────────────┼──────────────┘
       ▼             ▼              ▼
┌──────────────────────────────────────────────────┐
│            FastAPI (api 컨테이너)                  │
│                                                    │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────┐ │
│  │ Knowledge   │  │ Workflow    │  │ MCP      │ │
│  │ Service     │  │ Service     │  │ Service  │ │
│  └──────┬──────┘  └──────┬──────┘  └────┬─────┘ │
│         │                │                │      │
│         │         ┌──────▼─────────┐     │      │
│         │         │ Workflow       │     │      │
│         │         │ Compiler &     │     │      │
│         │         │ Runtime        │     │      │
│         │         │ (LangGraph)    │     │      │
│         │         └──────┬─────────┘     │      │
│         │                │                │      │
│  ┌──────▼─────┐  ┌──────▼──────┐  ┌────▼─────┐ │
│  │ Ingestion  │  │ Model       │  │ MCP      │ │
│  │ Pipeline   │  │ Provider    │  │ Adapter  │ │
│  │ (parsers)  │  │ Registry    │  │          │ │
│  └──────┬─────┘  └─────────────┘  └────┬─────┘ │
└─────────┼────────────────────────────────┼──────┘
          ▼                                ▼
   ┌──────────┐  ┌──────────┐    ┌──────────────┐
   │  Qdrant  │  │ Postgres │    │ External MCP │
   │ (vectors)│  │ (metadata│    │ Servers      │
   └──────────┘  └──────────┘    └──────────────┘
```

### 11.1 API 네임스페이스
- **MVP**: **루트 라우트**만 사용 (`/health`, `/workflows`, `/knowledge`, `/mcp`, `/runs` 등)
- **버저닝 없음** — 외부 사용자·통합자가 생기기 전까지 단순 유지
- **복원 절차** (언젠가 필요 시):
  1. `app/main.py`에 `api_v1 = APIRouter(prefix="/api/v1")` 추가하고 기존 라우터들 이동
  2. Breaking change는 `/api/v2`에서 시작
  3. 프론트 `lib/api.ts`에 버전 상수 도입
- **마이그레이션 트리거**: (a) 외부 사용자·통합자, (b) breaking change 불가피, (c) 멀티 클라이언트 (모바일/CLI)

### 11.2 에러 응답 표준
모든 API 에러는 일관된 JSON envelope로 응답.

```json
{
  "detail": "human-readable message",
  "code": "KNOWLEDGE_NOT_FOUND",
  "request_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

- `detail`: 사용자/개발자가 읽는 설명 (영어 기본, 추후 i18n 가능)
- `code`: 기계 친화 에러 코드 (`SCREAMING_SNAKE_CASE`). 프론트 분기 로직용
- `request_id`: 미들웨어가 생성·주입. 응답 헤더 `X-Request-ID`에도 동일 값

**구현**:
- `app/core/errors.py`에 `AppError(HTTPException)` 베이스 + 코드 enum (도메인별)
- 글로벌 exception handler가 envelope로 직렬화
- 422 validation 에러(FastAPI 기본)는 handler가 envelope로 재포장
- Request ID 미들웨어: 헤더 `X-Request-ID`가 있으면 사용, 없으면 UUID 생성

**에러 코드 네임스페이스 예시**:
- `KNOWLEDGE_*` — 지식베이스 관련
- `WORKFLOW_*` — 워크플로우/실행 관련
- `MCP_*` — 도구 관련
- `VALIDATION_*` — 입력 검증 실패
- `INTERNAL_*` — 서버 내부 에러

### 11.3 CORS & 브라우저/서버 URL 이원화
> M3 (캔버스 프론트)에서 클라이언트 사이드 fetch 등장 시 필수. M0/M1/M2는 Server Component만 사용하므로 우선순위 낮음.

- **CORS**: `FastAPI CORSMiddleware` + `Settings.cors_origins: list[str]`. `.env`에서 JSON 리스트로 관리.
- **URL 이원화**: 브라우저는 호스트 매핑된 `http://localhost:${API_PORT}`, 서버 컴포넌트는 컨테이너 네트워크 `http://api:8000`. `lib/api.ts`에서 `typeof window === 'undefined'`로 분기.
- **Next.js env 주의**: `NEXT_PUBLIC_*`은 **빌드 타임**에 번들에 박힘 → `web` Dockerfile의 build stage에 `ARG`로 주입하거나 docker-compose `build.args`로 전달.

---

## 12. Docker Compose 구성 (개념)

```yaml
services:
  postgres:
    image: postgres:16-alpine
    volumes: [pgdata:/var/lib/postgresql/data]
    environment: [POSTGRES_*]

  qdrant:
    image: qdrant/qdrant:latest
    volumes: [qdrant_data:/qdrant/storage]
    ports: ["6333:6333"]

  api:
    build: ./backend
    depends_on: [postgres, qdrant]
    environment:
      - DATABASE_URL
      - QDRANT_URL
      - OPENAI_API_KEY
      - ANTHROPIC_API_KEY
      - DEFAULT_EMBEDDING_PROVIDER=local_hf
      - DEFAULT_EMBEDDING_MODEL_PATH=/models/snowflake-arctic-embed-l-v2.0-ko
    ports: ["8000:8000"]
    volumes:
      - ./backend:/app
      - uploads:/app/uploads
      - /DATA3/users/mj/hf_models:/models:ro   # 로컬 HF 모델 read-only 마운트
    # GPU 사용 시:
    # deploy:
    #   resources:
    #     reservations:
    #       devices: [{driver: nvidia, count: all, capabilities: [gpu]}]

  web:
    build: ./frontend
    depends_on: [api]
    environment: [NEXT_PUBLIC_API_URL]
    ports: ["3000:3000"]

volumes:
  pgdata:
  qdrant_data:
  uploads:
```

---

## 13. 디렉토리 구조 (제안)

```
/DATA3/users/mj/AgentBuilder/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── core/              # config, db, security
│   │   ├── models/            # SQLAlchemy models
│   │   ├── schemas/           # Pydantic schemas
│   │   ├── api/               # FastAPI routers
│   │   │   ├── knowledge.py
│   │   │   ├── workflows.py
│   │   │   ├── mcp.py
│   │   │   └── runs.py
│   │   ├── services/
│   │   │   ├── knowledge/     # ingestion, parsers, embedder
│   │   │   ├── workflow/      # compiler, runtime, executor
│   │   │   ├── mcp/           # adapter, discovery
│   │   │   └── providers/     # model provider registry
│   │   └── nodes/             # 6개 노드 구현
│   ├── alembic/
│   ├── tests/
│   ├── pyproject.toml
│   └── Dockerfile
├── frontend/
│   ├── app/                   # Next.js App Router
│   │   ├── (knowledge)/
│   │   ├── (workflows)/
│   │   └── (tools)/
│   ├── components/
│   │   ├── canvas/            # React Flow + 노드 컴포넌트
│   │   ├── nodes/             # 노드별 카드 UI
│   │   ├── knowledge/
│   │   └── mcp/
│   ├── lib/                   # API client, utils
│   ├── stores/                # Zustand stores
│   ├── styles/                # Tailwind + Clay tokens
│   └── package.json
├── docs/
│   ├── specs/
│   │   └── 2026-04-08-agentbuilder-design.md  ← THIS FILE
│   ├── DESIGN.md              # Clay 디자인 시스템 (already exists)
│   ├── 워크플로우.png
│   ├── langflow_workflow.png
│   └── langflow nodes.png
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## 14. 마일스톤 & 진행 추적

> 각 항목은 별도 implementation plan에서 세분화. 여기서는 큰 그림만.

### Milestone 0 — Foundation (인프라) ✅ 완료 (2026-04-09)
- [x] Docker Compose 4-service 구성 (postgres, qdrant, api, web)
- [x] 백엔드 FastAPI skeleton + health endpoint
- [x] 프론트 Next.js skeleton + Clay 디자인 토큰 세팅
- [x] SQLAlchemy + Alembic 초기 마이그레이션
- [x] 환경 변수 / 설정 관리
> 상세: [`docs/plans/2026-04-08-milestone-0-foundation.md`](plans/2026-04-08-milestone-0-foundation.md) | 후속: [`docs/tracking/m0-followups.md`](tracking/m0-followups.md)

### Milestone 1 — 지식베이스 (RAG) ✅ 완료 (2026-04-09)
- [x] 지식베이스 CRUD API
- [x] 파일 업로드 + 진행률 SSE
- [x] 파일 파서 모듈 (11 포맷: txt/md/html/xml/pdf/docx/pptx/xlsx/csv/epub/eml)
- [x] EmbeddingProvider Registry (local_hf 디폴트 / fastembed fallback)
- [ ] ChatProvider Registry (OpenAI / Claude / vLLM) — Milestone 3에서도 사용 → **M3로 이관**
- [x] 로컬 HF 모델 로딩 (`langchain-huggingface`, GPU auto-detect)
- [x] Docker volume 마운트로 호스트 모델 접근 검증
- [x] 청킹 + 임베딩 파이프라인
- [x] Qdrant 컬렉션 관리 (차원 고정)
- [x] 검색 테스트 UI
- [x] 지식 탭 UI 구현 — 목록/생성/상세/파일업로드/SSE진행률/검색 패널
> 상세: [`docs/plans/2026-04-09-milestone-1-knowledge-rag.md`](plans/2026-04-09-milestone-1-knowledge-rag.md) | 상태: [`docs/tracking/m1-status.md`](tracking/m1-status.md)

### Milestone 2 — 도구 (MCP)
- [ ] MCP 서버 CRUD API
- [ ] STDIO / HTTP-SSE 어댑터
- [ ] 툴 디스커버리 + 캐싱
- [ ] 도구 탭 UI (등록 모달, 서버 목록)

### Milestone 3 — 워크플로우 캔버스
- [ ] 워크플로우 CRUD API
- [ ] React Flow 기본 캔버스
- [ ] 6개 노드 UI 컴포넌트 (Clay 스타일)
- [ ] 좌측 사이드바 (검색 / 컴포넌트 / MCP 패널)
- [ ] 노드 설정 폼 (Provider/Model 선택, Tool 체크박스 등)
- [ ] 그래프 저장/로드

### Milestone 4 — 워크플로우 실행 엔진
- [ ] WorkflowCompiler (UI graph → LangGraph)
- [ ] 6개 노드 LangGraph 구현
- [ ] `astream_events` → SSE 라우트
- [ ] 실행 이벤트 저장 (Postgres)
- [ ] 플레이그라운드 패널 UI
- [ ] 실시간 로깅 패널 + 에러 표시

### Milestone 5 — 통합 & 다듬기
- [ ] End-to-end 시나리오 테스트 (RAG + Agent + MCP)
- [ ] 빌드/실행 에러 메시지 다듬기
- [ ] README + 사용 가이드
- [ ] 데모 워크플로우 1~2개 시드 데이터

---

## 15. 미해결 / TBD

> 다음 브레인스토밍 세션에서 결정 필요. 구현 진입 전 정리.

| # | 항목 | 비고 |
|---|---|---|
| 1 | Phase 0 파일 포맷 라이브러리 최종 확정 | `unstructured` 통합 vs 개별 파서 비교 검증 필요 |
| 2 | 청킹 기본값 튜닝 (chunk_size/overlap) | 영문 vs 한국어 차이 |
| 3 | Model Provider별 모델 목록 가져오는 방식 | API 호출 vs 정적 목록 |
| 4 | Qdrant 컬렉션 명명 규칙 | UUID vs 사용자 슬러그 |
| 5 | 워크플로우 실행 동시성 제한 | 단일 사용자라도 동시 실행 정책 |
| 6 | 노드 간 데이터 타입 검증 | 강타입 vs 자유 (string-only MVP?) |
| 7 | Prompt Template 변수 추출 정규식 사양 | 중첩, 이스케이프 처리 |
| 8 | MCP credential 저장 (env 변수 vs DB 암호화) | MVP는 .env? |
| 9 | 파일 업로드 크기 제한 / 보관 정책 | 디스크 사용량 가드 |
| 10 | deepagents 패키지 활용 가능성 | Phase 2 "Deep Agent" 노드로 검토 |
| 11 | 워크플로우 export/import 포맷 | JSON 표준화 |
| 12 | i18n 정책 | UI 한국어 우선? 영어 동시? |
| 13 | **API 버저닝 복원 시점** | 현재 루트 라우트만. 외부 사용자·breaking change·멀티 클라이언트 등장 시 `/api/v1` 도입 (§11.1 복원 절차) |
| 14 | **로깅 전략** | M4 전 결정. 후보: `loguru` (추천) / `structlog` / stdlib `logging`. JSON sink로 파일 + stdout |
| 15 | **CORS origins 관리 방식** | env var JSON 리스트 → Settings. Prod에서 와일드카드 금지 (§11.3) |
| 16 | **에러 코드 enum 구체화** | `app/core/errors.py`에 도메인별 코드 정의. M1 첫 엔드포인트 작성 시 착수 |

---

## 16. 결정 로그 (Decision Log)

| 날짜 | 결정 | 근거 |
|---|---|---|
| 2026-04-08 | Python 풀스택 (FastAPI + Next.js) | Python 생태계 우위, 프로젝트 기존 스택 |
| 2026-04-08 | LangGraph를 워크플로우 엔진으로 | StateGraph + `astream_events` 가 요구사항과 일치 |
| 2026-04-08 | deepagents는 MVP에서 사용 안 함 | 사용자 그래프 자유도와 충돌, Phase 2 후보 |
| 2026-04-08 | Qdrant 벡터 DB 고정 | 사용자 지정 |
| 2026-04-08 | Postgres를 처음부터 사용 | SQLite → PG 마이그레이션 비용 회피 |
| 2026-04-08 | MCP를 top-level "도구" 탭으로 승격 | 지식과 동일한 "재사용 가능 자산" 원칙 |
| 2026-04-08 | Tool 연결은 Dify 패턴 (노드 속성) | UX 단순함, LangGraph 매핑 자연스러움 |
| 2026-04-08 | 워크플로우 탭 명명 "워크플로우" (스튜디오 ❌) | 세 탭 명칭 대칭성 ("자산" 모델) |
| 2026-04-08 | MVP 노드 6종 확정 | Chat I/O + LLM + Agent + KB + Prompt |
| 2026-04-08 | 단일 사용자 MVP, 인증 없음 | 사용자 지정 |
| 2026-04-08 | UI 네비: top nav (Dify) + editor 좌측 사이드바 (Langflow) | 두 패턴 직교, 함께 채택 |
| 2026-04-08 | 임베딩 디폴트는 **로컬 Snowflake Arctic Embed L Korean** (1024 dim) | 한국어 RAG 특화, 사용자 서버에 이미 다운로드됨, smooth RAG의 핵심 |
| 2026-04-08 | 디폴트 모델 경로 → env var + Docker read-only volume | 컨테이너 portability, 호스트 경로 분리 |
| 2026-04-08 | 로컬 모델 없으면 fastembed로 fallback | graceful degradation |
| 2026-04-08 | Anthropic은 embedding 미지원 (chat-only) | first-party 임베딩 API 없음 — Provider 추상화에서 제외 |
| 2026-04-08 | ChatProvider / EmbeddingProvider 별도 Protocol | Anthropic 부재를 타입으로 표현 |
| 2026-04-09 | API 루트 라우트만 사용 (버저닝 없음) | 단일 사용자 MVP, 외부 사용자 없음. 복원 절차는 §11.1에 기록 |
| 2026-04-09 | 에러 응답 표준 envelope (`detail`, `code`, `request_id`) | 프론트 분기 로직 일관성, 디버깅 편의 |
| 2026-04-09 | 장기 작업 패턴: `asyncio.create_task` + 프로세스 메모리 상태 + DB 영속화 | 단일 사용자 MVP. Celery/Redis/Temporal 오버킬. 재시작 시 `running`→`failed` 마크 |
| 2026-04-09 | HF_MODELS_PATH 환경변수화 | 호스트 경로 하드코딩 제거, 포터빌리티 |
| 2026-04-09 | 버전 문자열 단일 소스 (`pyproject.toml` → `importlib.metadata`) | drift 제거 |
| 2026-04-09 | CORS / 브라우저·서버 URL 이원화 정책 명시 | M3에서 발견하면 반나절 까먹는 함정. 지금 기록 |

---

## 17. 참조

- **DESIGN.md** — Clay 디자인 시스템
- **워크플로우.png** — Dify 캔버스 참조
- **docs/langflow_workflow.png** — Langflow 캔버스 참조
- **docs/langflow nodes.png** — Langflow 노드 카탈로그 참조
- LangGraph: https://langchain-ai.github.io/langgraph/
- React Flow (xyflow): https://reactflow.dev/
- Qdrant: https://qdrant.tech/
- MCP Spec: https://modelcontextprotocol.io/
- langchain-mcp-adapters: https://github.com/langchain-ai/langchain-mcp-adapters

---

**다음 단계**: 이 문서 리뷰 → 미해결 항목 좁히기 → 마일스톤별 implementation plan 작성 (`writing-plans` 스킬).
