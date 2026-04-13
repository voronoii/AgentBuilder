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
- 탭 4개: **지식 / 워크플로우 / 도구 / 환경변수**
- 노드 6개: Chat Input / Chat Output / Language Model / Agent / Knowledge Base / Prompt Template
- 외부 MCP 연결 (STDIO + HTTP/SSE + Streamable HTTP)
- 워크플로우 실행 + 실시간 로깅 + 에러 표시

### 1.4 MVP에서 의도적으로 제외


| 기능                                            | 이유              | 후속 Phase |
| --------------------------------------------- | --------------- | -------- |
| 멀티 유저 / 인증                                    | 단일 사용자 MVP      | Phase 2  |
| 분기/루프 노드 (If-Else, Loop)                      | 조건 엣지 UX 복잡도    | Phase 2  |
| Code / Python Interpreter 노드                  | 샌드박싱 보안 이슈      | Phase 3  |
| HTTP Request 노드                               | MCP로 대체 가능      | Phase 2  |
| Structured Output / Guardrails / Smart Router | 편의 기능           | Phase 2+ |
| 워크플로우 생성 Assistant Chat (우측 패널)               | MVP 이후          | Phase 2  |
| 워크플로우 버전 관리 / 협업                              | 단일 사용자          | Phase 3  |
| 워크플로우 템플릿 갤러리                                 | MVP 이후          | Phase 2  |
| 커스텀 MCP 작성 도우미                                | "외부 MCP 가져오기"부터 | Phase 2  |


---

## 2. 기술 스택

### 2.1 백엔드


| 항목       | 선택                                                                 | 근거                                             |
| -------- | ------------------------------------------------------------------ | ---------------------------------------------- |
| 언어       | **Python 3.13**                                                    | LLM/임베딩/파일파싱 생태계, 프로젝트 기존 스택                   |
| 웹 프레임워크  | **FastAPI**                                                        | Async, OpenAPI 자동 생성, SSE/WebSocket 친화         |
| 워크플로우 엔진 | **LangGraph**                                                      | StateGraph, 조건 엣지, `astream_events()` 실시간 스트리밍 |
| ORM      | **SQLAlchemy 2.0 (async)** + Alembic                               | FastAPI 표준, async 지원                           |
| 메타데이터 DB | **PostgreSQL 16**                                                  | 처음부터 운영 DB로 (마이그레이션 비용 절감)                     |
| 벡터 DB    | **Qdrant**                                                         | 가벼움, Docker 친화, 메타데이터 필터링                      |
| 파일 파싱    | **unstructured / pypdf / python-docx / openpyxl** 등 (Phase 0에서 확정) | 무변환 처리 가능한 포맷 우선                               |
| MCP 어댑터  | **langchain-mcp-adapters**                                         | MCP → LangChain Tool 자동 변환                     |


### 2.2 프론트엔드


| 항목     | 선택                                 | 근거                             |
| ------ | ---------------------------------- | ------------------------------ |
| 프레임워크  | **Next.js 15+ (App Router)**       | Dify/Sim Studio 패턴, SSR 옵션     |
| 캔버스 엔진 | **React Flow (xyflow)**            | 모든 벤치마크 플랫폼이 채택한 표준            |
| 스타일링   | **Tailwind CSS** + **Clay 디자인 토큰** | DESIGN.md의 Clay 스타일 구현         |
| 상태 관리  | **Zustand**                        | Dify/Langflow/Sim Studio 모두 사용 |
| 데이터 페칭 | **TanStack Query (React Query)**   | 서버 상태 관리                       |
| 폼      | **React Hook Form** + **zod**      | 노드 설정 폼                        |


### 2.3 인프라


| 항목    | 선택                                                         |
| ----- | ---------------------------------------------------------- |
| 컨테이너  | **Docker Compose** (4-service: postgres, qdrant, api, web) |
| 로컬 개발 | `docker compose up` 한 줄                                    |
| 환경 변수 | `.env` + `pydantic-settings`                               |


---

## 3. 정보 구조 (IA)

### 3.1 Top-Level Navigation

```
┌──────────────────────────────────────────────────────────┐
│  [Logo]  지식    워크플로우    도구    설정        [User] │
└──────────────────────────────────────────────────────────┘
```

- **지식**: 지식베이스 자산 관리 (업로드, 임베딩, 검색 테스트)
- **워크플로우**: 워크플로우 자산 관리 + 캔버스 에디터 (스튜디오)
- **도구**: MCP 서버 자산 관리 (등록, credential, 툴 디스커버리)
- **설정**: API 키 및 엔드포인트 관리 (M3에서 추가, Post-MVP에서 "환경변수"→"설정"으로 리네임)

> **명명 원칙**: 네 탭 모두 "그 안에 들어있는 자산/설정"의 이름을 사용 → 멘탈 모델 일관성

### 3.2 워크플로우 에디터 내부 (Langflow 패턴)

```
┌──┬──────────────────────────────────────────────┐
│📦│                                               │
│🔌│         React Flow Canvas                     │
│📊│         (노드 + 엣지)                          │
│  │                                               │
│  │                                               │
└──┴──────────────────────────────────────────────┘
   ↑
   └─ 좌측 수직 사이드바 (에디터 전용)
      📦 컴포넌트 (검색 인라인) / 🔌 MCP / 📊 실행로그
```

> **마일스톤별 범위**: M3에서는 📦 컴포넌트(검색 인라인 포함) + 🔌 MCP 2개 탭만 구현. 📊 실행로그는 M4 실행 엔진 완성 후 추가.

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
  - **Knowledge Base**: 지식 탭에서 구축된 KB 중 선택 (체크박스, 다중 선택 가능). Agent가 필요할 때 자율적으로 KB 검색 도구를 호출
  - **TOOLS**: 등록된 MCP 툴 중 선택 (체크박스, Dify 패턴)
- **입력**: `input: str`
- **출력**: `response: str`
- **LangGraph 매핑**: `create_react_agent(model, tools=[...])` 서브그래프
- **Tool 연결 방식**: **Dify 방식** — Tool과 KB 모두 노드 내부 속성 (별도 노드 ❌)
- **KB-as-Tool**: 선택된 각 KB는 `StructuredTool(name="search_kb_{name}", args={query: str})`로 변환되어 MCP 도구와 함께 Agent에 전달. Agent가 ReAct 루프 안에서 필요할 때만 자율적으로 KB 검색을 호출. KB 메타데이터(컬렉션명, 임베딩 모델)는 컴파일 시점에 DB에서 조회하고 클로저에 캡처 → 런타임에서는 DB 세션 없이 Qdrant 검색만 수행 (세션 충돌 방지)

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


| 패턴         | 그래프                                                                            |
| ---------- | ------------------------------------------------------------------------------ |
| 단순 챗봇      | `Chat Input → Language Model → Chat Output`                                    |
| RAG 챗봇     | `Chat Input → Knowledge Base → Prompt Template → Language Model → Chat Output` |
| 툴 에이전트     | `Chat Input → Agent(+MCP tools) → Chat Output`                                 |
| RAG + 에이전트 | `Chat Input → Agent(+KB도구 +MCP tools) → Chat Output`                           |

> **RAG + 에이전트 패턴 변경 (2026-04-12)**: 기존에는 KB 노드를 Agent 앞에 엣지로 연결했으나, KB를 Agent의 내부 도구로 통합. Agent가 필요할 때만 자율적으로 KB 검색을 호출하므로 불필요한 검색을 피하고 캔버스도 단순해짐. 기존 KB 독립 노드 방식(RAG 챗봇 패턴)도 여전히 사용 가능.


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

### 4.4 프론트엔드 상태 관리 (Zustand)

```typescript
// useWorkflowStore — 캔버스 핵심 상태
interface WorkflowStore {
  workflowId: string | null;
  workflowName: string;
  nodes: Node[];          // React Flow Node[]
  edges: Edge[];          // React Flow Edge[]
  selectedNodeId: string | null;

  // React Flow 이벤트 핸들러
  onNodesChange: OnNodesChange;
  onEdgesChange: OnEdgesChange;
  onConnect: OnConnect;

  // CRUD 동작
  addNode: (type: NodeType, position: XYPosition) => void;
  removeNode: (id: string) => void;
  updateNodeData: (id: string, data: Partial<NodeData>) => void;

  // 서버 동기화
  loadWorkflow: (id: string) => Promise<void>;
  saveWorkflow: () => Promise<void>;
}

// useSidebarStore — UI 패널 상태
interface SidebarStore {
  isOpen: boolean;             // 디폴트 true (에디터 진입 시 자동 오픈)
  activePanel: 'components' | 'mcp' | null;  // 디폴트 'components'
  toggle: (panel: string) => void;
  close: () => void;
}
```

> **Auto-save**: 모든 상태 변경 액션(`onNodesChange`, `onEdgesChange`, `onConnect`, `addNode`, `removeNode`, `updateNodeData`) 후 1.5초 디바운스로 `saveWorkflow()` 자동 호출. 수동 저장 버튼도 유지.

> **노드 추가**: 사이드바에서 클릭하면 캔버스에 즉시 노드 추가 (연속 추가 시 위치 자동 오프셋).

> **엣지 삭제**: 커스텀 `DeletableEdge` 컴포넌트 — 연결선 가운데에 ✕ 버튼 표시, 클릭 시 엣지 삭제.

> **React Flow ↔ 백엔드 직렬화**: React Flow의 `Node[]`/`Edge[]` 형태를 그대로 `Workflow.nodes`/`Workflow.edges` JSON에 저장. 프론트에서 추가 변환 없이 `setNodes(workflow.nodes)`로 복원. 백엔드는 JSON blob으로만 취급하고, M4 컴파일러가 해석.

---

## 5. Model Provider 추상화

### 5.1 지원 Provider (MVP)

#### Chat (LLM 노드 / Agent 노드)


| Provider               | 라이브러리                                | 비고             |
| ---------------------- | ------------------------------------ | -------------- |
| **OpenAI**             | `langchain-openai`                   | API key        |
| **Claude (Anthropic)** | `langchain-anthropic`                | API key        |
| **vLLM**               | `langchain-openai` (OpenAI 호환 엔드포인트) | base_url + 모델명. `.env`에 `VLLM_BASE_URL` 환경변수 지원. `GET /providers` 시 vLLM `/v1/models` 엔드포인트에서 동적 모델 목록 조회. 모델명 `"default"` 시 자동 감지 |


#### Embedding (Knowledge Base)


| Provider                            | 라이브러리                                           | 비고                                                                                                                     |
| ----------------------------------- | ----------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| **local_hf (HuggingFace 로컬)** ★ 디폴트 | `langchain-huggingface` (sentence-transformers) | API key 불필요. 디폴트 모델: **Snowflake Arctic Embed L v2.0 Korean** (XLM-RoBERTa Large, 1024 dim, 8194 context). 한국어 RAG 특화. |
| **fastembed (fallback)**            | `fastembed`                                     | 로컬 HF 모델 경로 없을 때 fallback. `intfloat/multilingual-e5-small`                                                            |
| **OpenAI**                          | `langchain-openai`                              | `text-embedding-3-small` / `text-embedding-3-large`                                                                    |
| **vLLM**                            | `langchain-openai` (OpenAI 호환)                  | 사용자가 임베딩 모델 서빙한 경우                                                                                                     |
| ~~Anthropic~~                       | —                                               | Anthropic은 first-party 임베딩 API 없음 (chat-only)                                                                          |


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

- **DB 우선** (M3~): `app_settings` 테이블에 key-value로 저장. 사용자가 **환경변수** 탭에서 API 키를 직접 입력/수정. Secret 값은 API 응답에서 마스킹 처리 (뒤 4자만 노출).
- **환경변수 폴백**: DB에 값이 없으면 `.env` + `pydantic-settings`의 환경변수 참조. 양쪽 모두 없으면 해당 provider disabled. vLLM은 `VLLM_BASE_URL` 환경변수 → `docker-compose.yml`에서 `AGENTBUILDER_VLLM_BASE_URL`로 매핑 → `Settings.vllm_base_url` pydantic-settings 필드로 바인딩.
- **시드 데이터**: 마이그레이션 시 `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `VLLM_BASE_URL` 3개 키 자동 생성.
- **향후**: DB에 암호화 저장 (Phase 2)
- fastembed는 키 불필요 → **첫 사용 friction zero**

---

## 6. 지식베이스 (RAG) 파이프라인

> **MVP의 핵심 차별점.** "Smooth"가 가장 중요한 영역.

### 6.1 사용자 흐름 (UX)

```
1. 지식 탭 → "+ 새 지식베이스"
2. 이름 입력 (임베딩 모델은 디폴트로 자동 채워짐 — local_hf/Snowflake Arctic Embed L v2.0 Korean, 로컬 모델 없으면 fastembed fallback)
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


| 포맷                                            | 라이브러리                        | 비고                    |
| --------------------------------------------- | ---------------------------- | --------------------- |
| TXT, MD, MDX, HTML, HTM, XML, VTT, PROPERTIES | 표준 텍스트 처리                    | 인코딩 자동 감지             |
| PDF                                           | `pypdf` 또는 `pdfplumber`      | 텍스트 PDF 우선 (스캔 OCR ❌) |
| DOCX                                          | `python-docx`                | 구버전 DOC ❌             |
| PPTX                                          | `python-pptx`                | 구버전 PPT ❌             |
| XLSX                                          | `openpyxl`                   | 구버전 XLS는 `xlrd` 추가 검토 |
| CSV                                           | 표준 라이브러리 / `pandas`          |                       |
| EPUB                                          | `ebooklib` + BeautifulSoup   |                       |
| EML, MSG                                      | `eml-parser` / `extract-msg` |                       |


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
- **재시작 복구**: 서버 재시작 시 `processing` 상태였던 문서는 `**failed`로 변경**하고 UI에 "다시 시도" 버튼 표시 (재시도는 idempotent — 해당 문서의 기존 청크를 지우고 재임베딩)
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


| 방식                   | MVP       | 설명                                                                                   |
| -------------------- | --------- | ------------------------------------------------------------------------------------ |
| **STDIO**            | ✅         | 로컬 바이너리/스크립트 (`npx @modelcontextprotocol/server-filesystem` 등). 컨테이너에 Node.js 22 설치됨 |
| **HTTP/SSE**         | ✅         | 원격 MCP 서버 — Legacy SSE transport (MCP spec ≤ 2024-11-05)                             |
| **Streamable HTTP**  | ✅         | 원격 MCP 서버 — MCP spec 2025-03-26+ 권장 transport                                        |
| **JSON Bulk Import** | ❌ Phase 2 | 여러 서버를 한 번에 등록                                                                       |


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

- 탭: **STDIO** | **HTTP/SSE** | **Streamable HTTP** (기본)
- STDIO: command, args, env vars
- HTTP/SSE & Streamable HTTP: URL, headers, env vars
- 등록 시점에 `list_tools` 호출 → 툴 목록 자동 디스커버리 (BackgroundTask, 실패해도 등록 유지) → DB 캐싱

### 7.4 워크플로우와의 연결

- Agent 노드의 `[+ Tool]` 클릭
- 등록된 MCP 서버의 툴 카탈로그 모달
- 체크박스로 다중 선택
- 실행 시점에 `langchain-mcp-adapters`로 LangChain Tool로 변환 후 `create_react_agent`에 전달

### 7.5 데이터 모델

```python
class MCPTransport(StrEnum):
    STDIO = "stdio"
    HTTP_SSE = "http_sse"
    STREAMABLE_HTTP = "streamable_http"

class MCPServer:
    id: UUID
    name: str  # unique
    description: str
    transport: MCPTransport
    config: dict  # transport별 설정 (command/args 또는 url/headers)
    env_vars: dict
    enabled: bool
    discovered_tools: list[ToolMetadata]  # JSON 캐시
    last_discovered_at: datetime | None
    created_at: datetime
    updated_at: datetime
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


| 이벤트            | 의미                                   |
| -------------- | ------------------------------------ |
| `node_start`   | 노드 실행 시작                             |
| `node_end`     | 노드 실행 종료 + output                    |
| `node_error`   | 노드 실행 실패 + traceback                 |
| `llm_token`    | LLM 토큰 스트리밍 (Language Model / Agent) |
| `tool_call`    | MCP 툴 호출 (Agent 내부)                  |
| `tool_result`  | MCP 툴 결과 (Agent 내부)                  |
| `workflow_end` | 전체 종료                                |


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
- **재시작 복구**: 서버 재시작 시 `running` 상태 run은 모두 `**failed`로 마크**하고 에러에 "server restart" 기록. 자동 재시도 ❌
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
- **shadcn/ui** (Radix 기반) 컴포넌트 라이브러리 — Button, Input, Textarea, Select, Dialog, Tabs, Badge, Collapsible
- **Lucide React** 아이콘 시스템 — 전체 이모지를 SVG 아이콘으로 교체
- Clay Elevation 4단계 (`shadow-clay-0` ~ `shadow-clay-2` + `shadow-clay-focus`)
- `cn()` 유틸리티 (`clsx` + `tailwind-merge`)

### 10.2 캔버스 노드 시각 디자인 (Approach B: Thin Border + Color Dot)

- 노드 카드: 흰 배경 + **1px oat 테두리** + `shadow-clay-1` (기존 `border-2` 컬러 테두리 제거)
- 타입 표시: 헤더 왼쪽 **8px 컬러 도트** + Lucide 아이콘 (warmSilver)
- 도트 컬러: Chat IO=rose(`#f43f5e`), LLM=cyan(`#06b6d4`), Agent=purple(`#8b5cf6`), KB=emerald(`#078a52`), Prompt=amber(`#d97706`)
- 헤더/바디 구분: 1px `#eee9df` 구분선, 바디에 주요 설정값 미리보기 (Provider, Model, Top K 등)
- 선택 시: `border-clay-accent` + `shadow-clay-focus` (기존 `ring-2 ring-blue-400` 제거)
- 핸들(input/output): oat 배경 + 흰색 테두리 + oat 외곽선
- 삭제 버튼: Lucide `X` 아이콘 (기존 ✕ 텍스트 대체)

### 10.3 좌측 사이드바

- 에디터 진입 시 컴포넌트 패널 자동 오픈 (디폴트)
- 컴포넌트 패널: 노드 목록 + 검색 인라인 + **클릭으로 캔버스에 즉시 추가** (연속 추가 시 위치 자동 오프셋)
  - 각 노드 버튼: 컬러 도트 + Lucide 아이콘 + 라벨 (기존 이모지+컬러 테두리 → 통일된 흰색 카드)
- MCP 패널: 등록된 서버 + 툴 목록
- 실행로그 패널: Lucide 아이콘 + shadcn Badge 상태 표시
- 패널 헤더: Lucide 아이콘 + 텍스트 (기존 이모지 제거)

### 10.4 TopNav

- 로고: matcha 컬러 사각 아이콘(`A`) + "AgentBuilder" 텍스트
- 탭: Lucide 아이콘 + 텍스트 라벨 (BookOpen/Workflow/Wrench/Settings)
- Active 탭: matcha 하단 바 인디케이터 + font-semibold
- "환경변수" → "설정"으로 리네임

### 10.5 툴바 (워크플로우 에디터)

- Lucide 아이콘 + 텍스트 라벨 (기존 이모지 제거)
- 수직 divider로 기능 그룹 분리 (뒤로가기 | 이름 | 사이드바 토글 | 실행 | 저장)
- "실행" 버튼: matcha outline 스타일 (기존 "▶ 플레이그라운드" 대체)
- "저장" 버튼: shadcn Button + Lucide Save 아이콘

### 10.6 플레이그라운드

- 사용자 메시지: `bg-clayBlack` (기존 `bg-blue-600`)
- 전송 버튼: matcha 배경 + Lucide Send 아이콘 (기존 녹색 "전송" 텍스트)
- 노드 이벤트 로그: Lucide 아이콘 (Play/Check/Wrench/AlertCircle)

### 10.7 공통 컴포넌트 패턴

- **페이지 헤더**: 제목 + subtitle + 액션 버튼 (모든 목록 페이지 통일)
- **카드**: 흰 배경 + 1px oat 테두리 + `rounded-card` + hover 시 `border-clay-accent` + `shadow-clay-2`
- **빈 상태**: dashed border + Lucide 아이콘(40px) + 제목 + 설명
- **폼**: shadcn Input/Textarea/Select (기존 `.input-field` 클래스 제거)
- **모달**: shadcn Dialog (기존 커스텀 fixed overlay 대체)
- **상태 표시**: shadcn Badge (success/destructive/info/warning/secret variants)

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

- **MVP**: **루트 라우트**만 사용 (`/health`, `/workflows`, `/knowledge`, `/mcp`, `/providers`, `/settings`, `/runs` 등)
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

- `KNOWLEDGE_`* — 지식베이스 관련
- `WORKFLOW_*` — 워크플로우/실행 관련
- `MCP_*` — 도구 관련
- `SETTING_*` — 환경변수/설정 관련
- `VALIDATION_*` — 입력 검증 실패
- `INTERNAL_*` — 서버 내부 에러

### 11.3 CORS & 브라우저/서버 URL 이원화

> ⚠️ **M3 필수**: 캔버스 프론트에서 클라이언트 사이드 fetch 등장. M0/M1/M2는 Server Component만 사용하므로 없어도 동작했음.

- **CORS**: `FastAPI CORSMiddleware` + `Settings.cors_origins: list[str]`. `.env`에서 JSON 리스트로 관리.
- **URL 이원화**: 브라우저는 호스트 매핑된 `http://localhost:${API_PORT}`, 서버 컴포넌트는 컨테이너 네트워크 `http://api:8000`. `lib/api.ts`에서 `typeof window === 'undefined'`로 분기.
- **Next.js env 주의**: `NEXT_PUBLIC_`*은 **빌드 타임**에 번들에 박힘 → `web` Dockerfile의 build stage에 `ARG`로 주입하거나 docker-compose `build.args`로 전달.

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
    ports: ["28000:8000"]   # 호스트 28000 → 컨테이너 8000
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
    ports: ["23000:3000"]   # 호스트 23000 → 컨테이너 3000

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

- Docker Compose 4-service 구성 (postgres, qdrant, api, web)
- 백엔드 FastAPI skeleton + health endpoint
- 프론트 Next.js skeleton + Clay 디자인 토큰 세팅
- SQLAlchemy + Alembic 초기 마이그레이션
- 환경 변수 / 설정 관리
  > 상세: `[docs/plans/2026-04-08-milestone-0-foundation.md](plans/2026-04-08-milestone-0-foundation.md)` | 후속: `[docs/tracking/m0-followups.md](tracking/m0-followups.md)`

### Milestone 1 — 지식베이스 (RAG) ✅ 완료 (2026-04-09)

- 지식베이스 CRUD API
- 파일 업로드 + 진행률 SSE
- 파일 파서 모듈 (11 포맷: txt/md/html/xml/pdf/docx/pptx/xlsx/csv/epub/eml)
- EmbeddingProvider Registry (local_hf 디폴트 / fastembed fallback)
- ChatProvider Registry → **M3: 정적 모델 목록 API만** (`GET /providers`), **M4: `make_chat_model()` 실행 로직 — OpenAI / Anthropic / vLLM / OpenRouter 4종 구현 완료**
- 로컬 HF 모델 로딩 (`langchain-huggingface`, GPU auto-detect)
- Docker volume 마운트로 호스트 모델 접근 검증
- 청킹 + 임베딩 파이프라인
- Qdrant 컬렉션 관리 (차원 고정)
- 검색 테스트 UI
- 지식 탭 UI 구현 — 목록/생성/상세/파일업로드/SSE진행률/검색 패널
  > 상세: `[docs/plans/2026-04-09-milestone-1-knowledge-rag.md](plans/2026-04-09-milestone-1-knowledge-rag.md)` | 상태: `[docs/tracking/m1-status.md](tracking/m1-status.md)`

### Milestone 2 — 도구 (MCP) ✅ 완료 (2026-04-10)

- MCP 서버 CRUD API (POST/GET/GET/{id}/PUT/DELETE + POST/{id}/discover)
- 3종 어댑터: STDIO (subprocess) + HTTP/SSE (sse_client) + Streamable HTTP (streamablehttp_client)
- 툴 디스커버리 + DB JSON 캐싱 (등록 시 BackgroundTask 자동 + 수동 재발견)
- 도구 탭 UI (서버 목록 카드, 3탭 등록 모달, 툴 카탈로그, 활성/비활성 토글)
- Dockerfile에 Node.js 22 추가 (npx STDIO MCP 지원)
- Alembic 마이그레이션 m2_001 ~ m2_003
  > 상세: `[docs/plans/2026-04-10-milestone-2-mcp-tools.md](plans/2026-04-10-milestone-2-mcp-tools.md)` | 상태: `[docs/tracking/m2-status.md](tracking/m2-status.md)`

### Milestone 3 — 워크플로우 캔버스 ✅ 완료 (2026-04-10)

**백엔드**

- CORS 설정 (`CORSMiddleware` + `Settings.cors_origins`) — M0에서 이미 구현
- 브라우저/서버 URL 이원화 (`lib/api.ts`에서 `typeof window` 분기) — M0에서 이미 구현
- `Workflow` 모델 + Alembic 마이그레이션 (`m3_001`)
- Pydantic 스키마 (`WorkflowCreate`, `WorkflowUpdate`, `WorkflowRead`, `WorkflowValidationResult`)
- `WorkflowRepository` + 워크플로우 CRUD API (POST/GET/GET/{id}/PUT/DELETE)
- ChatProvider 정적 모델 목록 API (`GET /providers`) — DB 설정(§5.4) 우선 + 환경변수 폴백으로 provider/model 목록 반환. `make_chat_model()` 실행 로직은 M4
- React Flow ↔ 백엔드 직렬화 규약 — React Flow `Node[]`/`Edge[]` 그대로 JSON blob 저장
- 워크플로우 저장 시 기본 유효성 검사 (경고 수준) — `POST /workflows/{id}/validate` ChatInput/ChatOutput 존재 확인
- `AppSetting` 모델 + Alembic 마이그레이션 (`m3_002`) — API 키/엔드포인트 key-value 저장 (시크릿 마스킹)
- Settings CRUD API (GET/PUT `/settings`, PUT `/settings/{key}`) — 환경변수 탭 백엔드. **M4에서 POST/DELETE 추가 (사용자 자유 추가/삭제)**

**프론트엔드**

- Zustand 스토어 설계 및 구현
  - `useWorkflowStore` — nodes, edges, 선택 상태, addNode/removeNode/updateNode, onNodesChange/onEdgesChange, **auto-save (1.5초 디바운스)**
  - `useSidebarStore` — 사이드바 열림/닫힘, 활성 패널 (**에디터 진입 시 컴포넌트 패널 자동 오픈**)
- React Flow 기본 캔버스 (`/workflows/{id}/edit`)
- 워크플로우 목록/생성 페이지 (`/workflows`)
- 6개 노드 UI 컴포넌트 (Clay 스타일 swatch 색상 — Pomegranate/Slushie/Ube/Matcha/Lemon)
- 좌측 사이드바 — 📦 컴포넌트(검색 인라인 + **클릭 추가**) + 🔌 MCP 2탭. 📊 실행로그는 M4
- 노드 설정 폼 (Provider/Model 드롭다운, Tool 체크박스, KB 드롭다운, 프롬프트 변수 자동 추출)
- 커스텀 `DeletableEdge` — 엣지 가운데 ✕ 버튼으로 연결선 삭제
- 그래프 저장/로드 (auto-save + 수동 💾 저장)
- 환경변수 관리 페이지 (`/settings`) — API 키 입력/수정 UI, 카테고리 그룹, 시크릿 마스킹
- TopNav에 환경변수 탭 추가
  > 상태: `[docs/tracking/m3-status.md](tracking/m3-status.md)`

### Milestone 4 — 워크플로우 실행 엔진 ✅ 완료 (2026-04-11)

**백엔드 — 모델/스키마/마이그레이션**
- [x] `WorkflowRun` + `RunEvent` 모델 (`app/models/run.py`) + Alembic 마이그레이션 `m4_001`
  - `RunStatus` StrEnum (running/success/failed/cancelled)
  - `WorkflowRun`: FK→workflows, indexes on workflow_id/status
  - `RunEvent`: FK→workflow_runs (CASCADE), composite index on run_id+timestamp
- [x] Pydantic 스키마 (`RunCreate`, `RunRead`, `RunEventRead`, `RunSummary`)
- [x] `RunRepository` (`app/repositories/run.py`) — CRUD + `mark_stale_runs_failed()` 스타트업 복구
- [x] 에러 코드 추가: `RUN_NOT_FOUND`, `RUN_ALREADY_FINISHED`, `RUN_CANCEL_FAILED`, `COMPILATION_FAILED`

**백엔드 — ChatProvider 실행 로직**
- [x] `make_chat_model()` (`app/services/providers/chat/registry.py`)
  - OpenAI: `ChatOpenAI` + DB/env 키 resolve
  - Anthropic: `ChatAnthropic` + DB/env 키 resolve
  - vLLM: `ChatOpenAI(base_url=...)` OpenAI-compatible API
  - **OpenRouter**: `ChatOpenAI(base_url="https://openrouter.ai/api/v1")` + `default_headers` (HTTP-Referer, X-OpenRouter-Title)
- [x] **컴파일/런타임 분리 (2026-04-12 코드리뷰 C2 수정)**
  - `resolve_provider_credentials()` — 컴파일 시점에 DB에서 API 키 조회
  - `make_chat_model_sync()` — 런타임에 pre-resolved credentials로 모델 생성 (DB 접근 없음)
  - 기존 `make_chat_model()`은 편의 래퍼로 유지 (내부에서 둘을 순차 호출)
- [x] pyproject.toml 의존성 추가: `langchain-openai`, `langchain-anthropic`, `langgraph`, `langgraph-checkpoint-postgres`
- [x] Provider 모델 목록에 OpenRouter 추가 (유료 + 무료 모델 포함)
  - 유료: `openai/gpt-5.2`, `openai/gpt-4.1-mini`, `anthropic/claude-sonnet-4-20250514`, `google/gemini-2.5-flash` 등
  - 무료: `nvidia/nemotron-3-super-120b-a12b:free`, `arcee-ai/trinity-large-preview:free`, `z-ai/glm-4.5-air:free`

**백엔드 — WorkflowCompiler**
- [x] `WorkflowValidator` (`app/services/workflow/validator.py`) — 5가지 검증
  - ChatInput/ChatOutput 정확히 1개씩
  - 고립 노드 검출
  - 사이클 감지 (Kahn's algorithm)
  - 필수 필드 검증 (LLM/Agent→provider+model, KB→knowledgeBaseId, Prompt→template)
  - 엣지 참조 유효성
- [x] `WorkflowCompiler` (`app/services/workflow/compiler.py`) — UI graph → LangGraph StateGraph
  - 검증 → 위상 정렬 → 노드 함수 생성 → 엣지 배선 → compile()
  - `WorkflowState` TypedDict (`app/services/workflow/state.py`) — 순환 import 방지를 위해 별도 파일
  - **(2026-04-12 코드리뷰 C4 수정)** 엣지 분석으로 `predecessor_map` 구성 → 각 노드 팩토리에 `predecessor_ids` 전달 (토폴로지 인식 입력 라우팅)
  - **(2026-04-12 코드리뷰 C5 수정)** `_find_sink_nodes()` — 모든 sink 노드를 END에 연결 (기존: 마지막 1개만 연결 → 다중 분기 그래프 오류)
- [x] `WorkflowState` — **(2026-04-12 코드리뷰 C3 수정)** `node_outputs: Annotated[dict, _merge_dicts]` reducer 추가. 병렬 노드 출력 안전 병합. 각 노드는 `{node_id: output}`만 반환 (reducer가 자동 병합)
- [x] 노드 레지스트리 (`app/nodes/registry.py`) — 타입별 팩토리 디스패치, `predecessor_ids` 전달

**백엔드 — 6개 노드 LangGraph 구현** (`app/nodes/`)
- [x] `chat_input.py` — user_input → node_outputs + messages 시딩
- [x] `chat_output.py` — predecessor 출력 수집 → final_output
- [x] `llm.py` — `async make_llm_node` (C2 수정으로 async 변경), `resolve_provider_credentials` + `make_chat_model_sync` 사용
- [x] `agent.py` — `create_react_agent` + MCP 도구 로딩 (`_load_mcp_tools`) + KB 도구 (`_build_kb_tools`)
  - **(2026-04-12 코드리뷰 C1 수정)** `_load_mcp_tools` → `tuple[tools, adapters]` 반환, `try/finally`로 어댑터 정리 보장 (`_close_adapters`)
  - **(C2 수정)** `resolve_provider_credentials` 컴파일 시점 호출, `make_chat_model_sync` 런타임 사용
- [x] `knowledge_base.py` — 컴파일 시 KB 검증, 런타임 시 Qdrant 검색 + 컨텍스트 포맷
- [x] `prompt_template.py` — `{variable}` 치환, 알 수 없는 플레이스홀더 유지

**백엔드 — 실행 런타임 + SSE + API**
- [x] `WorkflowRuntime` (`app/services/workflow/runtime.py`)
  - `asyncio.create_task()` 기반 백그라운드 실행
  - 글로벌 `asyncio.Semaphore(3)` 동시성 제한
  - `asyncio.Queue` 기반 SSE 이벤트 릴레이
  - `astream_events(version="v2")` → LangGraph 이벤트 매핑 (`_map_event`)
  - LLM 토큰 수집으로 final_output 재구성 (Agent 노드 호환)
  - 빈 토큰 필터링 (`if not token: continue`) — GLM 등 일부 모델이 실제 응답 전에 100+개의 빈 토큰을 보내는 문제 대응. DB 저장 + SSE 전송 모두에서 skip
  - 실행 완료 시 수집된 토큰 기반 `workflow_end` 이벤트에 최종 응답 포함 — 프론트엔드에서 토큰 스트리밍/비스트리밍 모델 모두 동일하게 응답 표시 가능
  - 스타트업 복구: `running` → `failed` 마크
  - **(2026-04-12 코드리뷰 H1)** `asyncio.wait_for(timeout=300)` — 5분 실행 타임아웃. 무한 루프/stuck 방지, 세마포어 슬롯 영구 점유 차단
  - **(H2)** 이벤트 DB commit 배치화 (`_EVENT_BATCH_SIZE=20`) — 토큰마다 commit → 20개 단위 flush. SSE 전송은 즉시 유지
- [x] Runs API (`app/api/runs.py`)
  - `POST /workflows/{id}/runs` — 실행 생성 + 백그라운드 시작
  - `GET /runs/{id}` — 실행 상태 조회
  - `GET /runs/{id}/events` — SSE 실시간 스트림 (60초 keep-alive ping)
  - `GET /runs/{id}/events/history` — DB 저장된 이벤트 조회
  - `POST /runs/{id}/cancel` — 실행 취소
  - `GET /workflows/{id}/runs` — 실행 이력 목록

**백엔드 — Settings 확장**
- [x] Settings에 POST(생성) / DELETE(삭제) API 추가 — 사용자가 키를 자유롭게 추가/삭제 가능
- [x] `SettingCreate` 스키마: key, value, description, category, is_secret
- [x] **(H3)** `GET /settings/{key}/value` raw-secret 엔드포인트 삭제 — 비인증 환경에서 원문 시크릿 노출 방지. 백엔드 서비스는 `SettingsRepository.get_value()` 직접 사용

**백엔드 — 설정/인프라 개선 (2026-04-12 코드리뷰)**
- [x] **(H4)** `get_settings()` 싱글턴 캐싱 (`core/config.py`) — 매 호출마다 `.env` 파싱 반복 → 모듈 레벨 `_settings_cache`로 첫 호출에만 파싱
- [x] **(H5)** MCP discovery 세션 분리 (`api/mcp.py`) — `_try_discover(server_id, timeout)` 방식으로 변경, `get_sessionmaker()`로 별도 세션 생성. 요청 스코프 세션 닫힘 후 사용 방지

**백엔드 — KB-as-Tool (Agent 노드에 지식베이스 도구 통합)**
- [x] `search_knowledge_base()` 공통 함수 추출 (`app/nodes/knowledge_base.py`) — KB 노드와 Agent 내 KB 도구 양쪽에서 재사용
- [x] `_resolve_kb_metadata()` (`app/nodes/agent.py`) — 컴파일 시점에 DB에서 KB 메타데이터(컬렉션명, 임베딩 프로바이더/모델) 조회. 런타임 DB 세션 충돌 방지
- [x] `_build_kb_tools()` (`app/nodes/agent.py`) — pre-resolved 메타데이터로 `StructuredTool` 생성 (DB 접근 없음)
  - 도구명: `search_kb_{sanitized_name}`, 입력 스키마: `{query: str}`
  - MCP 도구 리스트와 합쳐서 `create_react_agent(tools=[...mcp, ...kb])`에 전달
- [x] `make_agent_node`를 `async`로 변경 — KB 메타데이터 조회를 위해 `await _resolve_kb_metadata()` 호출
- [x] `registry.py` — `make_agent_node` 호출에 `await` 추가
- [x] `node_data.knowledgeBases` 필드 파싱: `[{knowledgeBaseId, topK, scoreThreshold}]`

**프론트엔드**
- [x] 플레이그라운드 패널 (`PlaygroundPanel.tsx`)
  - 우측 슬라이드인 채팅 UI (w-96)
  - 사용자 입력 → POST /runs → SSE 구독 → LLM 토큰 스트리밍
  - SSE Named Event 수신: `addEventListener`로 `llm_token`/`node_start`/`node_end`/`workflow_end`/`workflow_error`/`done` 등 전체 이벤트 타입 수신 (`onmessage`는 unnamed event만 수신하므로 불충분)
  - 정상 종료(`done`/`workflow_end`) vs 에러(`onerror`) 구분: `closedRef`로 정상 종료 신호 수신 여부를 추적하여, SSE 연결 종료 시 오탐 방지
  - 토큰 스트리밍 모델 / 비스트리밍 모델 모두 지원: `hasTokensRef`로 토큰 수신 여부 추적, `workflow_end.payload.output`에서 최종 응답 fallback (중복 방지)
  - 노드 실행 로그 (subtle) + 에러 표시
- [x] 실행로그 패널 (`RunLogPanel.tsx`)
  - 좌측 사이드바 📊 실행로그 탭
  - 실행 이력 목록 (상태 배지 색상, 상대 시간)
  - 클릭 확장: 시간 정보 + 이벤트 상세
  - 이벤트별 아이콘/색상: ▶node_start, ✓node_end, 💬llm_token, 🔧tool_call, ❌workflow_error
  - `payload` 내용 렌더링: 에러 메시지, 출력 미리보기, 도구 호출 정보
  - 실패 시 에러 요약 미리보기 (접지 않아도 표시)
  - 🔄 새로고침 버튼 + running 상태 시 3초 자동 폴링
- [x] Agent 설정 패널에 Knowledge Base 선택 UI 추가 (`NodeConfigPanel.tsx`)
  - `AgentConfig`에 KB 체크박스 목록 (MCP Tools와 동일 패턴)
  - 다중 선택 → `node_data.knowledgeBases[]`에 `{knowledgeBaseId, topK: 5, scoreThreshold: 0.0}` 저장
  - 기존 `useKnowledgeBases()` 훅 재사용 (`GET /api/knowledge`)
- [x] `NodeData` 인터페이스에 `knowledgeBases` 필드 추가 (`lib/workflow.ts`)
- [x] Settings 페이지 확장
  - "+ 새 설정 추가" 폼 (키/값/카테고리/시크릿 여부)
  - 각 설정 옆 삭제 버튼 (확인 단계 포함)
- [x] `useSidebarStore` 확장: `PanelType`에 `'runlog'` 추가
- [x] `WorkflowEditor.tsx` 툴바: ▶ 플레이그라운드 + 📊 실행로그 버튼
- [x] **(H8)** Auto-save 실패 UI 표시 (`workflowStore.ts`) — `saveError: string | null` 상태 추가, `_scheduleAutoSave`에 `onError` 콜백 전달, 성공 시 초기화
- [x] **(H9)** 숫자 입력 NaN 가드 (`NodeConfigPanel.tsx`) — 모든 `parseFloat`/`parseInt` 호출에 `Number.isNaN()` 가드. NaN이면 `onChange` 미호출 (6곳)

**버그 수정 기록**
- [x] `datetime.UTC` → `UTC` import 수정 (`app/repositories/run.py`) — Python 3.13에서 `datetime.datetime.UTC`는 존재하지 않음, `datetime.UTC` (모듈 상수) 사용해야 함
- [x] FastAPI DELETE 204 응답 body 에러 수정 — `status_code=204`와 `-> None` 조합이 FastAPI에서 assertion 실패. 200 + `{"ok": True}` 반환으로 변경
- [x] OpenRouter Gemini 모델 ID 수정 — `google/gemini-2.5-flash-preview` (존재하지 않음) → `google/gemini-2.5-flash` (실제 ID)
- [x] Agent 노드 final_output 빈 문자열 버그 — `astream_events`의 `on_chain_end`가 Agent 내부 상태를 반환하지 않는 문제. LLM 토큰 수집 방식으로 final_output 재구성
- [x] RunSummary에 `error` 필드 누락 — 실행 목록에서 실패 원인을 즉시 확인 불가. 스키마에 `error: str | None` 추가
- [x] RunLogPanel 이벤트 payload 미표시 — 프론트 `RunEvent` 인터페이스에 `payload` 필드 누락 (`data`로 잘못 정의). 이벤트별 payload 포맷팅 함수 추가
- [x] **플레이그라운드 SSE Named Event 수신 실패** — `EventSource.onmessage`는 unnamed event만 수신. 백엔드는 `event: llm_token` 등 named event를 보내므로 `addEventListener`로 교체. 이 버그로 인해 **전 모델에서** 플레이그라운드 응답이 표시되지 않았음
- [x] **SSE 연결 종료 시 오탐 에러 처리** — 서버가 `event: done`으로 정상 종료 신호를 보낸 뒤 연결을 닫으면 `EventSource.onerror`가 발생. `closedRef` 플래그로 이미 정상 종료 신호를 받았는지 추적하여 오탐 방지
- [x] **빈 토큰 대량 발생 (GLM 등)** — 일부 모델이 실제 응답 전에 빈 문자열 토큰을 100+개 보냄. 런타임에서 `if not token: continue`로 빈 토큰 DB 저장 + SSE 전송 모두 skip. 모델별 분기 없는 범용 처리
- [x] **비스트리밍 모델 응답 미표시** — 토큰을 개별 전송하지 않는 모델에서 플레이그라운드 응답이 빈 채로 종료. 런타임이 수집된 토큰으로 `workflow_end` 이벤트에 최종 응답을 포함시키고, 프론트에서 `hasTokensRef`로 토큰 수신 이력이 없을 때만 `workflow_end.payload.output` fallback 사용. 중복 방지
- [x] **Agent 노드 런타임 DB 세션 충돌** — `_load_kb_tools()`가 런타임에 DB 세션으로 KB 조회 시 `another operation is in progress` 에러 발생. 해결: KB 메타데이터를 컴파일 시점에 조회(`_resolve_kb_metadata`)하고 클로저에 캡처, 런타임에서는 DB 접근 없이 Qdrant 검색만 수행

**코드 리뷰 수정 (2026-04-12) — CRITICAL 5건 완료**
- [x] **(C1) MCP 어댑터 연결 누수** — `_load_mcp_tools` → `tuple[tools, adapters]` 반환, `agent_node` 내 `try/finally`로 실행 후 `_close_adapters()` 보장
- [x] **(C2) 컴파일/런타임 DB 세션 분리** — `resolve_provider_credentials()` (컴파일 시점 DB 조회) + `make_chat_model_sync()` (런타임, DB 불필요) 분리. LLM/Agent 양쪽 적용. `make_llm_node`도 `async`로 변경
- [x] **(C3) node_outputs LangGraph reducer 누락** — `_merge_dicts` reducer 추가 (`Annotated[dict, _merge_dicts]`), 6개 노드 모두 `{node_id: output}`만 반환하도록 단순화
- [x] **(C4) get_input_text 토폴로지 무시** — `predecessor_ids` 파라미터 추가, 컴파일러에서 엣지 기반 `predecessor_map` 구성 → 각 노드 팩토리에 전달. 분기 그래프에서 올바른 선행 노드 출력을 읽음
- [x] **(C5) 다중 sink 노드 END 미연결** — `_find_last_processing_node` → `_find_sink_nodes` (모든 sink를 `list[str]`로 반환), 각각 `graph.add_edge(sink, END)` 연결
> 상세: `[docs/plans/2026-04-12-m3m4-review-fixes.md](plans/2026-04-12-m3m4-review-fixes.md)`

**코드 리뷰 수정 (2026-04-12) — HIGH 8건 완료 (1건 보류)**
- [x] **(H1)** 워크플로우 실행 타임아웃 — `asyncio.wait_for(timeout=300)` (5분). 타임아웃 시 `failed` 상태 기록
- [x] **(H2)** 토큰 DB commit 배치화 — `_EVENT_BATCH_SIZE=20` 단위 flush. SSE 전송은 즉시 유지
- [x] **(H3)** raw-secret 엔드포인트 삭제 — `GET /settings/{key}/value` 제거. 내부 서비스는 리포지토리 직접 사용
- [x] **(H4)** `get_settings()` 싱글턴 캐싱 — 모듈 레벨 `_settings_cache`. 첫 호출에만 `.env` 파싱
- [x] **(H5)** MCP discovery 세션 분리 — `_try_discover(server_id)` + `get_sessionmaker()`로 별도 세션 생성
- [x] **(H6)** `create_react_agent` prompt 호환성 — LangGraph 0.6.11에서 `prompt` 파라미터 정식 지원 확인. 이슈 아님
- [ ] **(H7)** `as unknown as` 캐스트 — React Flow `Node.data`가 `Record<string, unknown>` 타입이므로 현 버전에서 제거 불가. **보류**
- [x] **(H8)** Auto-save 실패 UI 표시 — `saveError` 상태 추가, `onError` 콜백으로 에러 캡처
- [x] **(H9)** 숫자 입력 NaN 가드 — `Number.isNaN()` 가드 6곳 적용

**검증 결과 (2026-04-12)**
- 무료 모델 3종 (Nemotron/Trinity/GLM) 실제 LLM 응답 확인 ✅
- 플레이그라운드 SSE 토큰 스트리밍 정상 (Named Event 수신 확인) ✅
- WorkflowRun 생성/조회/목록/취소 API 정상 ✅
- RunEvent DB 저장 + SSE 스트리밍 정상 ✅
- Validator 검증 (model 누락 감지, 사이클, 고립 노드) 정상 ✅
- 스타트업 복구 (running→failed 마크) 정상 ✅
- **Agent+KB 도구 통합 정상** — Agent가 `search_kb_TEST34` 도구를 자율 호출, tool_call/tool_result 이벤트 로그 기록, 워크플로우 success 확인 ✅

### Milestone 5 — 통합 & 다듬기 ✅

- End-to-end 시나리오 테스트 (RAG + Agent + MCP)
- 빌드/실행 에러 메시지 다듬기
- README + 사용 가이드
- 데모 워크플로우 1~2개 시드 데이터

**구현 내용 (2026-04-12)**

**Phase 1: M3/M4 MEDIUM 이슈 10건 전체 수정**
- M1: `ReactFlowNode`/`ReactFlowEdge` Pydantic 모델 추가 (`schemas/workflow.py`). `extra="allow"`로 하위 호환
- M2: `ProviderModelInfo`/`ProviderInfo` 스키마 + `response_model` 데코레이터 (`api/providers.py`)
- M3: 파일 업로드 64KB 청크 스트리밍 방식으로 교체. 초과 시 부분 파일 삭제 (`api/knowledge.py`)
- M4: `_check_input_output_path()` BFS 검증 추가 (`validator.py`). ChatInput→ChatOutput 경로 없으면 경고
- M5: 실행 전 `validateWorkflow()` 호출 추가 (`PlaygroundPanel.tsx`). 검증 실패 시 에러 표시 후 중단
- M6: 하드코딩 `/api/...` fetch → `apiBase()` 패턴으로 교체 (5개 컴포넌트). SSR 호환
- M7: 아이콘 전용 버튼에 `aria-label` 추가 (닫기/삭제 버튼 4곳)
- M8: `NODE_LABELS` 상수 중복 제거 — `workflowStore.ts`에서 삭제, `nodeStyles.ts`에서 import
- M9: `@app.on_event("startup")` → `lifespan` async context manager 마이그레이션 (`main.py`)
- M10: 메시지 목록 `key={i}` → 안정적 복합 key (`PlaygroundPanel.tsx`)

**Phase 2: 백엔드 테스트 45개 신규 작성 (전체 통과)**
- `test_validator.py` (15개): I/O 노드 검증, 사이클, 고립 노드, 필수 필드, 엣지 유효성, I/O 경로 검증
- `test_runtime.py` (16개): `_map_event()` 순수 함수 테스트 — 6종 이벤트 매핑 + 엣지 케이스
- `test_node_registry.py` (8개): 노드 팩토리 디스패치, chat_input/chat_output callable 동작
- `test_compiler.py` (6개): 컴파일 성공/실패, sink 감지, 패스스루 거부

**Phase 3: 에러 메시지 한국어 통일**
- 백엔드 6개 파일 `detail` 문자열 한국어화 (`workflow.py`, `runs.py`, `knowledge.py`, `errors.py` 등)
- `code`(기계 판독용)는 영문 유지, 로그 메시지 변경 없음
- 프론트엔드: fetch 에러 시 `res.json()` 파싱 → `err.detail` 표시, 파싱 실패 시 기본 메시지 폴백

**Phase 4: 데모 시드 데이터**
- `backend/app/seed/demo_workflows.py`: 2개 데모 워크플로우 정의
  - "간단한 Q&A 챗봇" — ChatInput → LLM → ChatOutput (3노드, 2엣지)
  - "RAG 지식 챗봇" — ChatInput → KnowledgeBase → PromptTemplate → LLM → ChatOutput (5노드, 4엣지)
- `POST /workflows/seed` 엔드포인트: 이름 기준 멱등 생성, `{"created": [...], "skipped": [...]}`

**Phase 5: 문서화**
- `README.md` 전면 재작성 (233줄): 아키텍처 다이어그램, Quick Start, 환경변수, 프로젝트 구조, 노드 타입, 개발 셋업, 제약사항. 포트 28000/23000, Python 3.13 반영
- `docs/usage-guide.md` 신규 (317줄): 7개 섹션 — 시작하기, LLM 설정, 지식베이스, MCP 도구, 워크플로우 빌드, 실행, 데모

### Post-MVP 개선 (2026-04-13)

**vLLM 통합 강화**
- [x] `.env`에 `VLLM_BASE_URL` 환경변수 추가, `docker-compose.yml`에서 `AGENTBUILDER_VLLM_BASE_URL`로 매핑
- [x] `Settings.vllm_base_url` pydantic-settings 필드 추가 (`core/config.py`)
- [x] `resolve_provider_credentials()` vLLM 폴백 체인 개선: DB → `Settings.vllm_base_url` → raw env var
- [x] `GET /providers` — vLLM `/v1/models` 엔드포인트에서 동적 모델 목록 조회 (5초 타임아웃, 실패 시 `"default"` 폴백)
- [x] `make_chat_model_sync()` — `"default"` 모델명 시 `/v1/models`에서 첫 번째 모델 자동 감지

**지식베이스 문서 삭제 기능**
- [x] `KnowledgeRepository.delete_document()` — DB에서 문서 행 삭제 후 반환 (파일/벡터 정리용)
- [x] `DELETE /knowledge/{kb_id}/documents/{doc_id}` API 엔드포인트 — Qdrant `delete_by_document()`로 해당 문서 청크만 선택 삭제 + 업로드 파일 `unlink`
- [x] `DELETE /knowledge/{kb_id}` 개선 — 기존 DB만 삭제 → Qdrant 컬렉션 삭제(`delete_collection`) + 업로드 디렉토리 삭제(`shutil.rmtree`) 추가
- [x] `lib/knowledge.ts` — `deleteDocument()` API 클라이언트 함수 추가
- [x] `IngestionProgress.tsx` — 각 문서 행에 삭제 버튼 추가 (confirm 대화상자 포함)

**플레이그라운드 UX 개선**
- [x] 플레이그라운드 채팅 버블에 마크다운 렌더링 적용 (`react-markdown` + `remark-gfm`) — 볼드, 리스트, 코드블록, 테이블, 링크 지원
- [x] 실행로그 `RunLogPanel` — 연속 `llm_token` 이벤트를 하나의 `llm_output` 항목으로 병합 표시 (`mergeTokenEvents`). 토큰 개수 + 시간 범위 표시

**UI 전체 리디자인 — 상업용 에이전트 빌더 품질 (2026-04-13)**
> 상세 스펙: `docs/superpowers/specs/2026-04-13-ui-redesign-design.md`
> 구현 플랜: `docs/superpowers/plans/2026-04-13-ui-redesign.md`

- [x] **의존성 추가**: `lucide-react`, `@radix-ui/*` (dialog/select/tabs/tooltip/collapsible/slot), `class-variance-authority`, `clsx`, `tailwind-merge`
- [x] **디자인 토큰 보강**: Clay Elevation 4단계 (`shadow-clay-0/1/2/focus`), 누락 토큰 수정 (`clay-bg`, `clay-muted`)
- [x] **shadcn/ui 컴포넌트 생성** (`components/ui/`): Button(5 variants), Input, Textarea, Select, Badge(7 variants), Dialog, Tabs, Collapsible — 전체 Clay 토큰 적용
- [x] **TopNav 리디자인**: matcha 로고 뱃지 + Lucide 아이콘(BookOpen/Workflow/Wrench/Settings) + active 하단 바 인디케이터 + "환경변수"→"설정" 리네임
- [x] **노드 스타일 시스템 교체**: 이모지+컬러 테두리 → Lucide 아이콘 + 8px 컬러 도트. `NODE_STYLES` 레코드로 통합 (`dotColor`, `icon: LucideIcon`, `label`). 역호환 `NODE_COLORS`/`NODE_LABELS` 유지
- [x] **BaseNode 리디자인**: `border-2` 컬러 → `border` 1px oat 통일, 컬러 도트 + Lucide 아이콘, 헤더/바디 구분선, 설정값 미리보기(`FieldPreview`), 선택 시 matcha ring, Lucide `X` 삭제 버튼
- [x] **워크플로우 툴바**: Lucide 아이콘 + 텍스트 라벨, 수직 divider 그룹 분리, matcha "실행" 버튼, shadcn Button 저장
- [x] **사이드바**: 노드 버튼에 도트+아이콘, 패널 헤더에 Lucide 아이콘, 검색 focus ring matcha
- [x] **NodeConfigPanel**: shadcn Input/Textarea/Select 폼, 도트 헤더, uppercase 라벨, 패널 너비 288→320px
- [x] **PlaygroundPanel**: 사용자 메시지 `bg-blue-600`→`bg-clayBlack`, 전송 버튼 matcha+Send 아이콘, 노드 이벤트 Lucide 아이콘
- [x] **RunLogPanel**: 이모지 → Lucide SVG, shadcn Badge 상태 표시, RefreshCw 새로고침
- [x] **지식 페이지**: 아이콘 뱃지 카드, 메타 정보, 빈 상태 개선, shadcn 폼/버튼, `rounded-full`→`rounded-lg`
- [x] **도구 페이지**: Transport 이모지→Lucide, shadcn Badge/Dialog/Tabs, 등록 모달 Radix Dialog+Tabs
- [x] **설정 페이지**: 이모지→Lucide 그룹 아이콘, uppercase 라벨, shadcn Badge/Button/Input
- [x] **워크플로우 목록**: shadcn Button/Input, Lucide 아이콘, 카드 hover 개선
- [x] **`.input-field` 클래스 제거** (`globals.css`) — shadcn Input으로 대체
- [x] **이모지 0건** — 전체 프론트엔드 소스에서 이모지 완전 제거 확인
- [x] **빌드 성공** — `npm run build` zero errors

---

## 15. 미해결 / TBD

> 다음 브레인스토밍 세션에서 결정 필요. 구현 진입 전 정리.


| #     | 항목                                       | 비고                                                                                                                                                         |
| ----- | ---------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1     | Phase 0 파일 포맷 라이브러리 최종 확정                | `unstructured` 통합 vs 개별 파서 비교 검증 필요                                                                                                                        |
| 2     | 청킹 기본값 튜닝 (chunk_size/overlap)           | 영문 vs 한국어 차이                                                                                                                                               |
| ~~3~~ | ~~Model Provider별 모델 목록 가져오는 방식~~        | **결정: 정적 + 동적 혼합.** OpenAI/Anthropic/OpenRouter는 정적 목록. vLLM은 `/v1/models` 엔드포인트에서 동적 조회 (5초 타임아웃, 실패 시 `"default"` 폴백). DB 설정 기반 enabled 플래그 (§5.4)     |
| 4     | Qdrant 컬렉션 명명 규칙                         | UUID vs 사용자 슬러그                                                                                                                                            |
| ~~5~~ | ~~워크플로우 실행 동시성 제한~~                      | **결정: `asyncio.Semaphore(3)`** — 최대 3개 동시 실행. GPU/API rate limit 보호                                                                                         |
| 6     | ~~노드 간 데이터 타입 검증~~                       | **결정: MVP는 string-only.** 강타입 검증은 Phase 2                                                                                                                  |
| 7     | Prompt Template 변수 추출 정규식 사양             | 중첩, 이스케이프 처리                                                                                                                                               |
| ~~8~~ | ~~MCP credential 저장 (env 변수 vs DB 암호화)~~ | **결정: DB `app_settings` 테이블.** 환경변수 탭에서 UI 입력. Secret 마스킹. 암호화는 Phase 2                                                                                    |
| 9     | 파일 업로드 크기 제한 / 보관 정책                     | 디스크 사용량 가드                                                                                                                                                 |
| 10    | deepagents 패키지 활용 가능성                    | Phase 2 "Deep Agent" 노드로 검토                                                                                                                                |
| 11    | 워크플로우 export/import 포맷                   | JSON 표준화                                                                                                                                                   |
| 12    | i18n 정책                                  | UI 한국어 우선? 영어 동시?                                                                                                                                          |
| 13    | **API 버저닝 복원 시점**                        | 현재 루트 라우트만. 외부 사용자·breaking change·멀티 클라이언트 등장 시 `/api/v1` 도입 (§11.1 복원 절차)                                                                                |
| ~~14~~| ~~**로깅 전략**~~                              | **결정: stdlib `logging`.** M4에서 `_log = logging.getLogger(__name__)` 패턴으로 구현. 별도 라이브러리 불필요                                                                    |
| 15    | **CORS origins 관리 방식**                   | env var JSON 리스트 → Settings. Prod에서 와일드카드 금지 (§11.3)                                                                                                       |
| 16    | **에러 코드 enum 구체화**                       | `app/core/errors.py`에 도메인별 코드 정의. M1 첫 엔드포인트 작성 시 착수                                                                                                       |
| 17    | **Dockerfile `ARG` 규칙**                  | `NEXT_PUBLIC_`* 변수는 Next.js 빌드 타임에 번들에 박힘. `frontend/Dockerfile` build 스테이지에 `ARG <VAR>` + `ENV <VAR>=${<VAR>}` 선언 필수. 새 환경변수 추가 시 마다 체크 (M1 실사용 테스트에서 발견) |


---

## 16. 결정 로그 (Decision Log)


| 날짜         | 결정                                                         | 근거                                                                             |
| ---------- | ---------------------------------------------------------- | ------------------------------------------------------------------------------ |
| 2026-04-08 | Python 풀스택 (FastAPI + Next.js)                             | Python 생태계 우위, 프로젝트 기존 스택                                                      |
| 2026-04-08 | LangGraph를 워크플로우 엔진으로                                      | StateGraph + `astream_events` 가 요구사항과 일치                                       |
| 2026-04-08 | deepagents는 MVP에서 사용 안 함                                   | 사용자 그래프 자유도와 충돌, Phase 2 후보                                                    |
| 2026-04-08 | Qdrant 벡터 DB 고정                                            | 사용자 지정                                                                         |
| 2026-04-08 | Postgres를 처음부터 사용                                          | SQLite → PG 마이그레이션 비용 회피                                                       |
| 2026-04-08 | MCP를 top-level "도구" 탭으로 승격                                 | 지식과 동일한 "재사용 가능 자산" 원칙                                                         |
| 2026-04-08 | Tool 연결은 Dify 패턴 (노드 속성)                                   | UX 단순함, LangGraph 매핑 자연스러움                                                     |
| 2026-04-08 | 워크플로우 탭 명명 "워크플로우" (스튜디오 ❌)                                | 세 탭 명칭 대칭성 ("자산" 모델)                                                           |
| 2026-04-08 | MVP 노드 6종 확정                                               | Chat I/O + LLM + Agent + KB + Prompt                                           |
| 2026-04-08 | 단일 사용자 MVP, 인증 없음                                          | 사용자 지정                                                                         |
| 2026-04-08 | UI 네비: top nav (Dify) + editor 좌측 사이드바 (Langflow)          | 두 패턴 직교, 함께 채택                                                                 |
| 2026-04-08 | 임베딩 디폴트는 **로컬 Snowflake Arctic Embed L Korean** (1024 dim) | 한국어 RAG 특화, 사용자 서버에 이미 다운로드됨, smooth RAG의 핵심                                   |
| 2026-04-08 | 디폴트 모델 경로 → env var + Docker read-only volume              | 컨테이너 portability, 호스트 경로 분리                                                    |
| 2026-04-08 | 로컬 모델 없으면 fastembed로 fallback                              | graceful degradation                                                           |
| 2026-04-08 | Anthropic은 embedding 미지원 (chat-only)                       | first-party 임베딩 API 없음 — Provider 추상화에서 제외                                     |
| 2026-04-08 | ChatProvider / EmbeddingProvider 별도 Protocol               | Anthropic 부재를 타입으로 표현                                                          |
| 2026-04-09 | API 루트 라우트만 사용 (버저닝 없음)                                    | 단일 사용자 MVP, 외부 사용자 없음. 복원 절차는 §11.1에 기록                                        |
| 2026-04-09 | 에러 응답 표준 envelope (`detail`, `code`, `request_id`)         | 프론트 분기 로직 일관성, 디버깅 편의                                                          |
| 2026-04-09 | 장기 작업 패턴: `asyncio.create_task` + 프로세스 메모리 상태 + DB 영속화     | 단일 사용자 MVP. Celery/Redis/Temporal 오버킬. 재시작 시 `running`→`failed` 마크             |
| 2026-04-09 | HF_MODELS_PATH 환경변수화                                       | 호스트 경로 하드코딩 제거, 포터빌리티                                                          |
| 2026-04-09 | 버전 문자열 단일 소스 (`pyproject.toml` → `importlib.metadata`)     | drift 제거                                                                       |
| 2026-04-09 | CORS / 브라우저·서버 URL 이원화 정책 명시                               | M3에서 발견하면 반나절 까먹는 함정. 지금 기록                                                    |
| 2026-04-10 | MCP transport 3종 (STDIO + HTTP/SSE + Streamable HTTP)      | 생태계 현실: 대부분 STDIO, 신규는 Streamable HTTP 전환 중. 모두 지원                             |
| 2026-04-10 | 환경변수 탭 신설 (top-level 4번째 탭)                                | API 키를 사용자가 UI에서 직접 관리. `.env` 편집 없이 모델/MCP에서 활용                               |
| 2026-04-10 | API 키 저장은 DB 우선 + env var 폴백                               | `app_settings` 테이블 key-value. Provider API가 DB→env 순서로 조회                      |
| 2026-04-10 | Secret 마스킹 (뒤 4자만 노출)                                      | API 응답에서 `********7890` 형태. 프론트에서 원문 노출 방지                                     |
| 2026-04-10 | Auto-save 디폴트 (1.5초 디바운스)                                  | 워크플로우 캔버스에서 모든 변경 후 자동 저장. 사용자 수동 저장도 가능                                       |
| 2026-04-10 | 사이드바 클릭으로 노드 추가 (drag-and-drop 대신)                         | 직관적 UX. 연속 추가 시 위치 자동 오프셋으로 겹침 방지                                              |
| 2026-04-10 | 커스텀 DeletableEdge (엣지 가운데 ✕ 버튼)                            | 연결선 삭제를 시각적으로 명확하게. React Flow edgeTypes 커스텀                                   |
| 2026-04-10 | 에디터 진입 시 컴포넌트 사이드바 자동 오픈                                   | 빈 캔버스에서 즉시 노드 추가 가능하도록                                                         |
| 2026-04-10 | API 컨테이너에 Node.js 22 설치                                    | STDIO MCP 서버 대부분 `npx` 기반, 컨테이너 내 실행 필수                                        |
| 2026-04-10 | 등록 시 auto-discovery는 BackgroundTask (non-fatal)            | 등록 API는 항상 201 반환, discovery 실패해도 서버 등록 유지                                     |
| 2026-04-10 | 프론트 state lift-up 패턴                                       | 자식 컴포넌트가 prop을 자체 state로 복사하면 부모 업데이트 미반영. 부모가 state 소유                        |
| 2026-04-10 | ChatProvider M3/M4 경계 분리                                   | M3: 정적 모델 목록 API (`GET /providers`), M4: `make_chat_model()` 실행 로직. 오버엔지니어링 방지 |
| 2026-04-10 | M3 좌측 사이드바 2탭만 (📦+🔌)                                     | 📊 실행로그는 M4 엔진 완성 후. 📄 파일 탭은 용도 불명, Phase 2로 유보                               |
| 2026-04-10 | MVP 노드 간 데이터 타입은 string-only                               | 강타입 검증은 Phase 2. MVP 복잡도 감소                                                    |
| 2026-04-10 | Zustand store 2개 (`useWorkflowStore`, `useSidebarStore`)   | 캔버스 상태와 UI 상태 분리. React Flow 상태는 Zustand에 동기화                                  |
| 2026-04-10 | M3에서 저장 시 기본 유효성 검사 (경고 수준)                                | ChatInput/ChatOutput 존재 확인. 엄격 검증(사이클, 고립 노드)은 M4 실행 전                         |
| 2026-04-10 | CORS는 M3 첫 태스크로 설정                                         | 클라이언트 사이드 fetch 시작점. 누락 시 전체 프론트 개발 차단됨                                        |
| 2026-04-11 | OpenRouter를 4번째 ChatProvider로 추가                            | OpenAI-compatible API (`ChatOpenAI` + `base_url` 교체). 무료 모델 제공으로 API 키 비용 없이 테스트 가능 |
| 2026-04-11 | WorkflowState를 별도 파일(`state.py`)로 분리                       | compiler ↔ nodes 간 순환 import 방지. 공유 TypedDict 위치 통일                              |
| 2026-04-11 | Agent 노드 final_output은 LLM 토큰 수집 방식                        | `astream_events`의 `on_chain_end`가 Agent 내부 상태를 노출하지 않아 토큰 수집이 유일한 방법              |
| 2026-04-11 | 실행로그 폴링 주기 3초 + 수동 새로고침 버튼 병행                              | SSE 실시간 연동보다 단순하고 안정적. running 상태에서만 자동 폴링, 완료 시 중지                              |
| 2026-04-11 | Settings를 동적 CRUD로 확장 (POST/DELETE 추가)                     | 사전 정의 키만 사용하는 구조에서 사용자가 자유롭게 키 추가/삭제 가능. OpenRouter 등 새 프로바이더 키 즉시 등록 가능        |
| 2026-04-11 | 동시성 제한 `asyncio.Semaphore(3)`                                | 단일 사용자 MVP에서도 동시 실행 제한 필요 (LLM API rate limit, GPU 보호)                           |
| 2026-04-11 | 실행 이벤트 매핑: LangGraph v2 이벤트 → 6종 커스텀 이벤트                    | node_start/node_end/llm_token/tool_call/tool_result/workflow_end+error          |
| 2026-04-12 | SSE Named Event 사용 (event 필드 활용)                             | 백엔드가 `event: llm_token` 형태로 보냄. 프론트는 `addEventListener` 필수 (`onmessage`는 unnamed만 수신) |
| 2026-04-12 | 빈 토큰 범용 필터링 (모델별 분기 없음)                                     | GLM 등 일부 모델이 빈 토큰을 대량 발생. `if not token: continue` 1줄로 범용 처리. 모델 추가 시 별도 대응 불필요 |
| 2026-04-12 | workflow_end에 수집 토큰 기반 최종 응답 포함                              | `astream_events`의 `on_chain_end`는 Agent 내부 상태를 노출하지 않음. 토큰 수집이 유일한 범용 방법. 프론트에서 `hasTokensRef`로 중복 방지 |
| 2026-04-12 | KB를 Agent 노드의 내부 도구로 통합 (KB-as-Tool)                          | 기존 엣지 방식(`KB→Agent`)은 UX 혼란 유발 + 매번 불필요한 검색 실행. Dify 패턴과 일치시켜 KB를 Agent 속성(체크박스)으로 선택. Agent가 ReAct 루프에서 필요할 때만 자율적으로 KB 검색 호출 |
| 2026-04-12 | KB 메타데이터 컴파일/런타임 분리                                           | `make_agent_node`를 `async`로 변경하여 컴파일 시점에 DB 조회(`_resolve_kb_metadata`). 런타임 DB 세션 충돌(`another operation in progress`) 방지. 클로저에 캡처된 메타데이터로 Qdrant 검색만 수행 |
| 2026-04-12 | KB 검색 로직을 `search_knowledge_base()` 공통 함수로 추출                   | KB 독립 노드 + Agent 내 KB 도구 양쪽에서 재사용. 중복 코드 제거                                         |
| 2026-04-12 | 기존 KB 독립 노드 유지 (하위 호환)                                        | RAG 챗봇 패턴(`ChatInput→KB→PromptTemplate→LLM→ChatOutput`)도 여전히 동작. Agent가 없는 워크플로우에서 KB 사용 가능 |
| 2026-04-12 | **M3~M4 코드 리뷰 CRITICAL 5건 수정**                                  | 4개 전문 에이전트 병렬 리뷰 (TypeScript, Python, LangGraph, API). CRITICAL 5 / HIGH 9 / MEDIUM 10건 발견. CRITICAL 전체 수정 완료 |
| 2026-04-12 | node_outputs에 `_merge_dicts` reducer 추가                           | 병렬 노드가 동시에 state를 반환해도 결과 소실 없이 안전 병합. 각 노드는 `{node_id: output}`만 반환 |
| 2026-04-12 | get_input_text에 `predecessor_ids` 토폴로지 인식 추가                    | 컴파일러가 엣지 분석으로 선행 노드 목록을 구성하여 노드에 전달. 분기/합류 그래프에서 올바른 입력 라우팅 보장 |
| 2026-04-12 | ChatProvider를 `resolve_provider_credentials` + `make_chat_model_sync`로 분리 | 컴파일 시점에 DB에서 API 키 조회, 런타임에서는 DB 세션 없이 모델 생성. `another operation in progress` 세션 충돌 근본 해결 |
| 2026-04-12 | MCP 어댑터 `try/finally` 정리 패턴                                      | `_load_mcp_tools` → `tuple[tools, adapters]` 반환. Agent 실행 후 `_close_adapters()`로 모든 연결 정리. 리소스 누수 방지 |
| 2026-04-12 | 다중 sink 노드 전체 END 연결                                            | `_find_sink_nodes()` → 모든 sink를 `list[str]`로 반환, 각각 END 연결. 병렬 분기 그래프 정상 종료 보장 |
| 2026-04-12 | 워크플로우 실행 타임아웃 300초 (H1)                                          | `asyncio.wait_for` 래핑. stuck LLM/무한 tool 루프 시 세마포어 슬롯 영구 점유 방지 |
| 2026-04-12 | 이벤트 DB commit 배치화 20개 단위 (H2)                                     | 토큰마다 commit → 20개 flush. 500토큰 응답 시 500회 → 25회 commit으로 I/O 대폭 감소. SSE는 즉시 전송 유지 |
| 2026-04-12 | raw-secret 엔드포인트 삭제 (H3)                                          | `GET /settings/{key}/value` 제거. 인증 없는 MVP에서 원문 시크릿 HTTP 노출 차단. 내부 서비스는 리포지토리 직접 사용 |
| 2026-04-12 | `get_settings()` 싱글턴 캐싱 (H4)                                       | 매 요청마다 `.env` 파싱 반복 → 모듈 레벨 캐시 1회 파싱. 핫패스 성능 개선 |
| 2026-04-12 | MCP discovery 세션 분리 (H5)                                            | `_try_discover`가 별도 세션 생성. 요청 스코프 세션 닫힘 후 백그라운드 태스크에서 `Session is closed` 에러 방지 |
| 2026-04-12 | Auto-save 실패 `saveError` 상태 추가 (H8)                                 | 저장 실패 시 `saveError` 설정, 성공 시 초기화. 사용자에게 저장 실패 피드백 제공 가능 |
| 2026-04-12 | 숫자 입력 NaN 가드 (H9)                                                  | `parseFloat('')` → NaN이 서버에 전송되던 문제. `Number.isNaN()` 가드로 NaN 시 `onChange` 미호출 |
| 2026-04-12 | MEDIUM 이슈 10건 M5에서 전체 수정                                              | Pydantic 스키마(M1), response_model(M2), 스트리밍 업로드(M3), I/O 경로 검증(M4), validateWorkflow 호출(M5), apiBase 통일(M6), aria-label(M7), NODE_LABELS 중복 제거(M8), lifespan 마이그레이션(M9), key 안정화(M10) |
| 2026-04-12 | 에러 메시지 한국어 통일                                                          | user-facing `detail` 한국어화, `code` 영문 유지. 프론트엔드에서 구조화 에러 body 파싱 추가 |
| 2026-04-12 | 데모 시드 데이터 2종 + `POST /workflows/seed` 엔드포인트                            | "간단한 Q&A 챗봇"(3노드) + "RAG 지식 챗봇"(5노드). 멱등 생성 |
| 2026-04-12 | M3/M4 백엔드 테스트 45개 신규                                                   | validator(15) + runtime(16) + node_registry(8) + compiler(6). M1/M2 27개와 합산 72개 |
| 2026-04-12 | README 재작성 + Usage Guide 신규                                             | 포트 28000/23000, Python 3.13 반영. usage-guide.md 7개 섹션 |
| 2026-04-13 | vLLM 모델 목록 동적 조회                                                          | 정적 하드코딩(`"default"`) → vLLM `/v1/models` 실시간 조회. OpenAI/Anthropic/OpenRouter는 정적 유지 |
| 2026-04-13 | vLLM base_url 환경변수 체인 추가                                                   | `.env` → docker-compose → pydantic-settings → DB 폴백. 기존 DB-only에서 env var 경로 추가 |
| 2026-04-13 | 개별 문서 삭제 + KB 삭제 시 전체 정리                                                  | `delete_by_document()`로 Qdrant 청크 선택 삭제. KB 삭제 시 컬렉션+파일시스템 정리 추가 (기존 DB만 삭제 → 3중 정리) |
| 2026-04-13 | 플레이그라운드 마크다운 렌더링                                                          | `react-markdown` + `remark-gfm`. assistant 메시지만 적용, user 메시지는 plain text 유지 |
| 2026-04-13 | 실행로그 llm_token 병합 표시                                                       | 연속 토큰 이벤트를 `llm_output` 1개로 합침. 토큰 수 + 시간 범위 표시. 가독성 대폭 개선 |
| 2026-04-13 | **전체 UI 리디자인 — 상업용 품질로 업그레이드**                                                | Dify 벤치마크. Clay 톤 유지. 이모지 → Lucide Icons, shadcn/ui 도입, Approach B(Thin Border + Color Dot) 노드 디자인 |
| 2026-04-13 | shadcn/ui (Radix 기반) 컴포넌트 도입                                                    | Button/Input/Textarea/Select/Dialog/Tabs/Badge/Collapsible. 순수 Tailwind에서 컴포넌트 라이브러리로 전환. 폼/모달/상태표시 품질 향상 |
| 2026-04-13 | Lucide React 아이콘 시스템 채택                                                           | 전체 이모지를 SVG 아이콘으로 교체. 15+ 위치에서 이모지 제거. 노드/툴바/사이드바/페이지 전체 적용 |
| 2026-04-13 | 노드 디자인 Approach B (Thin Border + Color Dot)                                       | 3가지 후보(A: Clay Elevation, B: Thin Border+Dot, C: Left Accent) 중 B 선택. 노드 경계 명확 + 기존 코드 최소 변경 |
| 2026-04-13 | 사용자 메시지 색상 `bg-blue-600` → `bg-clayBlack`                                        | Clay 디자인 시스템과 일관된 색상. 상업 플랫폼 톤 |
| 2026-04-13 | "환경변수" 탭 → "설정"으로 리네임                                                            | 간결한 라벨. 기능 확장 가능성 (향후 일반 설정 추가 시) |
| 2026-04-13 | Clay Elevation 토큰 4단계 추가                                                            | `shadow-clay-0`(Flat) ~ `shadow-clay-2`(Hover) + `shadow-clay-focus`. PDF 디자인 시스템 기반 |


---

## 17. 참조

- **DESIGN.md** — Clay 디자인 시스템
- **워크플로우.png** — Dify 캔버스 참조
- **docs/langflow_workflow.png** — Langflow 캔버스 참조
- **docs/langflow nodes.png** — Langflow 노드 카탈로그 참조
- LangGraph: [https://langchain-ai.github.io/langgraph/](https://langchain-ai.github.io/langgraph/)
- React Flow (xyflow): [https://reactflow.dev/](https://reactflow.dev/)
- Qdrant: [https://qdrant.tech/](https://qdrant.tech/)
- MCP Spec: [https://modelcontextprotocol.io/](https://modelcontextprotocol.io/)
- langchain-mcp-adapters: [https://github.com/langchain-ai/langchain-mcp-adapters](https://github.com/langchain-ai/langchain-mcp-adapters)

---

**상태**: MVP 전체 마일스톤 (M0~M5) 완료. Post-MVP 개선 진행 중 (2026-04-13~): vLLM 동적 모델 감지, 문서 삭제 기능, 마크다운 렌더링, 실행로그 토큰 병합. Phase 2 확장 후보: 멀티유저/인증, 분기/루프 노드, 워크플로우 import/export, 시크릿 암호화, i18n, Deep Agent 노드.