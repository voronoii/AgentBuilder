# M3 워크플로우 캔버스 — 세션 시작 가이드

> 이 문서를 새 세션 시작 시 첫 메시지로 붙여넣거나 참조하세요.
> 최종 수정: 2026-04-10 (스펙 리뷰 반영)

---

## 1. 프로젝트 컨텍스트

```
프로젝트: /DATA3/users/mj/AgentBuilder
브랜치: feat/m1-knowledge-rag (M2까지 작업 포함, 아직 미커밋 파일 30+개 있음)
Docker: api(28000), web(23000), postgres(5432), qdrant(6333)
Python: 3.13 (Dockerfile python:3.13-slim + Node.js 22)
Alembic 헤드: m2_003
```

### 완료된 마일스톤
- **M0**: Docker Compose 4-service, FastAPI skeleton, Next.js skeleton, Clay 토큰
- **M1**: 지식베이스 RAG (CRUD, 파일파서 11종, 임베딩, Qdrant, 검색, SSE 진행률, UI)
- **M2**: MCP 도구 시스템 (CRUD, STDIO/HTTP-SSE/Streamable HTTP 3종 어댑터, 디스커버리, UI)

### 반드시 읽어야 할 파일
```
docs/specs/2026-04-08-agentbuilder-design.md    # 전체 스펙 (§4 노드 6종, §4.4 Zustand, §5 Provider, §8 실행엔진, §10 UX, §11.3 CORS, §14 M3)
docs/tracking/m1-status.md                       # M1 교훈 (프록시, Dockerfile ARG, SSE 폴링)
docs/tracking/m2-status.md                       # M2 교훈 (session.refresh, state lift-up, transport 3종)
DESIGN.md                                        # Clay 디자인 시스템 (노드 색상, 섀도우, 폰트)
```

---

## 2. M3 범위 (스펙 §14 기준)

### 백엔드 (7태스크)

| # | 태스크 | 비고 |
|---|--------|------|
| B1 | CORS 설정 (`CORSMiddleware` + `Settings.cors_origins`) | M3 첫 태스크. 이것 없으면 클라이언트 fetch 전부 차단 |
| B2 | 브라우저/서버 URL 이원화 (`lib/api.ts` `typeof window` 분기) | §11.3 참조. `NEXT_PUBLIC_API_URL` 빌드타임 주입 확인 |
| B3 | `Workflow` 모델 + Alembic 마이그레이션 (`m3_001`) | id, name, description, nodes(JSON), edges(JSON), created_at, updated_at |
| B4 | Pydantic 스키마 — `WorkflowCreate`, `WorkflowUpdate`, `WorkflowRead` | nodes/edges는 `list[dict]`로 받아 JSON blob 저장 |
| B5 | `WorkflowRepository` + CRUD API (POST/GET/GET/{id}/PUT/DELETE) | |
| B6 | ChatProvider 정적 모델 목록 API (`GET /providers`) | 환경변수 기반. `make_chat_model()` 실행 로직은 **M4** |
| B7 | 저장 시 기본 유효성 검사 (경고 수준) | ChatInput 1개 + ChatOutput 1개 존재 확인. 엄격 검증은 M4 |

### 프론트엔드 (8태스크)

| # | 태스크 | 비고 |
|---|--------|------|
| F1 | Zustand 설치 + 스토어 2개 구현 | `useWorkflowStore` (nodes/edges/CRUD), `useSidebarStore` (패널 상태) — §4.4 |
| F2 | React Flow 설치 + 기본 캔버스 (`/workflows/{id}/edit`) | `@xyflow/react`, `'use client'` 필수 |
| F3 | 워크플로우 목록/생성 페이지 (`/workflows`) | |
| F4 | 6종 노드 UI 컴포넌트 (Clay swatch 색상) | ChatInput/ChatOutput(Pomegranate), LLM(Slushie), Agent(Ube), KB(Matcha), PromptTemplate(Lemon) |
| F5 | 좌측 사이드바 — 📦 컴포넌트(검색 인라인) + 🔌 MCP 2탭만 | 📊 실행로그는 M4에서 추가 |
| F6 | 노드 설정 패널 | LLM/Agent: Provider+Model 드롭다운, Agent: MCP Tool 체크박스, KB: 지식베이스 드롭다운, PromptTemplate: 변수 자동 추출 |
| F7 | 엣지 연결 + 핸들 (in/out) | |
| F8 | 그래프 저장/로드 (PUT /workflows/{id}) | React Flow Node[]/Edge[] → 그대로 JSON 저장, 복원 시 `setNodes()` |

---

## 3. 핵심 데이터 모델

### 백엔드 (§4.3)

```python
class Workflow:
    id: UUID
    name: str
    description: str
    nodes: list[Node]    # JSON blob
    edges: list[Edge]    # JSON blob
    created_at, updated_at

class Node:
    id: str
    type: NodeType  # chat_input | chat_output | llm | agent | knowledge_base | prompt_template
    position: {x, y}
    data: dict  # 타입별 설정

class Edge:
    id: str
    source: str
    source_handle: str
    target: str
    target_handle: str
```

### 프론트엔드 Zustand (§4.4)

```typescript
// useWorkflowStore
interface WorkflowStore {
  workflowId: string | null;
  workflowName: string;
  nodes: Node[];          // React Flow Node[]
  edges: Edge[];          // React Flow Edge[]
  selectedNodeId: string | null;
  onNodesChange: OnNodesChange;
  onEdgesChange: OnEdgesChange;
  onConnect: OnConnect;
  addNode: (type: NodeType, position: XYPosition) => void;
  removeNode: (id: string) => void;
  updateNodeData: (id: string, data: Partial<NodeData>) => void;
  loadWorkflow: (id: string) => Promise<void>;
  saveWorkflow: () => Promise<void>;
}

// useSidebarStore
interface SidebarStore {
  isOpen: boolean;
  activePanel: 'components' | 'mcp' | null;
  toggle: (panel: string) => void;
}
```

### React Flow ↔ 백엔드 직렬화 규약

- React Flow `Node[]`/`Edge[]` 형태를 **그대로** `Workflow.nodes`/`Workflow.edges` JSON에 저장
- 프론트에서 추가 변환 없이 `setNodes(workflow.nodes)`로 복원
- 백엔드는 JSON blob으로만 취급, M4 컴파일러가 해석

---

## 4. M1/M2에서 배운 교훈 (반드시 적용)

| # | 교훈 | 적용 |
|---|------|------|
| 1 | `NEXT_PUBLIC_*` 환경변수 → `frontend/Dockerfile` ARG+ENV 필수 | 새 env var 추가 시 확인 |
| 2 | 프론트엔드는 `/api` 프록시 경유 (직접 localhost 호출 금지) | `next.config.ts` rewrites 사용 |
| 3 | `onupdate=func.now()` 사용 시 `session.refresh()` 필요 | Workflow 모델에도 동일 적용 |
| 4 | 자식 컴포넌트에 prop을 자체 useState로 복사하지 말 것 | 부모가 state 소유, 자식은 props만 렌더링 |
| 5 | SSE 불안정 → 폴링 fallback 패턴 | 실시간 기능 구현 시 참고 |
| 6 | ruff format + lint 매 태스크 후 실행 | B904, SIM105, N811 등 자주 발생 |
| 7 | host venv에 일부 패키지 미설치 → API 테스트는 Docker E2E | conftest isolation 또는 Docker 내부 실행 |
| 8 | React Flow는 `'use client'` 필수 | Next.js App Router에서 Client Component |

### M3 신규 주의사항

| # | 항목 | 설명 |
|---|------|------|
| 9 | CORS 먼저 | M3 첫 태스크. 클라이언트 fetch 전제조건 |
| 10 | 브라우저/서버 URL 이원화 | `typeof window === 'undefined'` → 컨테이너 URL, 아니면 호스트 URL |
| 11 | 노드 간 데이터 타입은 string-only | MVP 결정. 강타입 검증은 Phase 2 |
| 12 | ChatProvider는 목록 API만 | `GET /providers` 정적 목록. `make_chat_model()`은 M4 |

---

## 5. 태스크 실행 순서 (의존성 기반)

```
Phase 1 — 인프라 (B1 → B2)
  B1: CORS 설정
  B2: URL 이원화 (lib/api.ts 분기)

Phase 2 — 백엔드 CRUD (B3 → B4 → B5, B6 병렬)
  B3: Workflow 모델 + 마이그레이션
  B4: Pydantic 스키마
  B5: Repository + API 라우터
  B6: ChatProvider 정적 목록 API (B3~B5와 독립, 병렬 가능)

Phase 3 — 프론트 기반 (F1 → F2 → F3)
  F1: Zustand 스토어 2개
  F2: React Flow 캔버스 페이지
  F3: 워크플로우 목록 페이지

Phase 4 — 노드 & UI (F4 → F5 → F6 → F7)
  F4: 6종 노드 컴포넌트
  F5: 좌측 사이드바 (drag & drop)
  F6: 노드 설정 패널
  F7: 엣지 연결 + 핸들

Phase 5 — 저장 & 검증 (F8 + B7)
  F8: 그래프 저장/로드
  B7: 저장 시 유효성 검사

Phase 6 — 마무리
  Docker E2E 테스트 + m3-status.md
```

---

## 6. 추천 스킬 & 에이전트

### 반드시 사용할 스킬
```
ecc:frontend-design          — Clay 디자인 시스템 구현, 노드 UI
ecc:frontend-patterns        — React / Next.js 패턴
langgraph-fundamentals       — M4 컴파일러가 생성할 LangGraph 구조 이해 (노드 데이터 모델 설계에 필수)
langgraph-docs               — LangGraph 최신 API 레퍼런스
```

### 상황별 사용
```
ecc:documentation-lookup     — React Flow, Zustand, Tailwind 등 라이브러리 최신 API 확인
ecc:nextjs-turbopack         — Next.js 15 App Router 관련 이슈
ecc:vercel-react-best-practices — React 19 패턴
ecc:vercel-composition-patterns — 컴포넌트 구조 설계
ecc:typescript-reviewer      — TypeScript 코드 리뷰
ecc:python-patterns          — 백엔드 코드
ecc:database-migrations      — Alembic 마이그레이션
```

### 워크플로우 스킬
```
autopilot                    — "M3 진행해줘" 같은 큰 요청 시 자동 실행
ultrawork / ulw              — 병렬 에이전트로 백엔드+프론트엔드 동시 작업
```

---

## 7. 새 세션 첫 메시지 예시

```
AgentBuilder 프로젝트의 Milestone 3 (워크플로우 캔버스)를 진행해줘.

프로젝트 경로: /DATA3/users/mj/AgentBuilder
스펙: docs/specs/2026-04-08-agentbuilder-design.md (§4 노드, §4.4 Zustand, §5 Provider, §11.3 CORS, §14 M3)
M3 시작 가이드: docs/plans/m3-session-guide.md

실행 순서 (가이드 §5 참조):
1. Phase 1: CORS 설정 + URL 이원화 (M3 전제조건)
2. Phase 2: 백엔드 (모델 → 마이그레이션 → 스키마 → 리포 → API + ChatProvider 목록 API)
3. Phase 3-4: 프론트엔드 (Zustand → React Flow 캔버스 → 목록 페이지 → 노드 6종 → 사이드바 → 설정 폼 → 엣지)
4. Phase 5: 저장/로드 + 유효성 검사
5. Phase 6: docker compose up --build E2E 테스트 + m3-status.md

M1/M2 교훈 반드시 적용 (Dockerfile ARG, /api 프록시, session.refresh, state lift-up)
React Flow 문서는 Context7 MCP로 조회해서 최신 API 확인할 것.
```

---

## 8. 주의사항

- **M2 미커밋**: 현재 30+개 파일이 unstaged. M3 시작 전에 커밋 여부 결정 필요
- **Git remote 없음**: push할 곳이 없음. 로컬 커밋만 가능
- **React Flow 의존성**: `frontend/package.json`에 `@xyflow/react` 추가 필요
- **Zustand**: 캔버스 상태 관리에 필요. `frontend/package.json`에 `zustand` 추가 필요
- **ChatProvider는 M3에서 목록 API만**: `GET /providers` 정적 목록 반환. `make_chat_model()` 등 실행 로직은 M4
- **좌측 사이드바 M3 범위**: 📦 컴포넌트 + 🔌 MCP 2탭만. 📊 실행로그는 M4
- **노드 간 데이터 타입**: MVP는 string-only. 강타입 검증은 Phase 2
- **저장 시 유효성 검사**: M3에서는 경고 수준 (ChatInput/ChatOutput 존재 확인). 엄격 검증(사이클, 고립 노드)은 M4 실행 전
- **Clay 테마 전면 적용은 M5로 유보** — M3에서는 노드 카드에 swatch 색상만 적용

---

## 9. M3 완료 후 M4로 넘어가는 항목

M3에서 **의도적으로 제외**한 항목 (M4에서 구현):

| 항목 | M3 상태 | M4에서 |
|------|---------|--------|
| `WorkflowRun` + `RunEvent` 모델 | 없음 | 모델 + 마이그레이션 |
| `make_chat_model()` 실행 로직 | 목록 API만 | Provider별 LLM 인스턴스 생성 |
| WorkflowCompiler | 없음 | UI graph → LangGraph 변환 |
| 엄격 유효성 검사 | 경고 수준만 | 사이클/고립 노드/타입 불일치 |
| 📊 실행로그 사이드바 탭 | 없음 | 실행 이벤트 표시 |
| 플레이그라운드 패널 | 없음 | 우측 채팅 UI |
