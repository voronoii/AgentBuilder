# M2 MCP 도구 시스템 — 구현 상태

> 완료일: 2026-04-10  
> 브랜치: `feat/m1-knowledge-rag` (M2 작업 포함)  
> 테스트: 15 passed (host unit), API E2E Docker 스택에서 모든 엔드포인트 검증 완료  
> Alembic 헤드: `m2_003`

---

## 커밋 목록

| 커밋 | 내용 |
|------|------|
| *(미커밋)* | M2 의존성 추가 (`mcp>=1.3`, `langchain-mcp-adapters>=0.1`) |
| *(미커밋)* | MCPServer 모델 + Alembic 마이그레이션 (`m2_001`) |
| *(미커밋)* | 에러 코드 4종 + `mcp_discovery_timeout` 설정 추가 |
| *(미커밋)* | MCPServer 스키마 + 리포지터리 |
| *(미커밋)* | StdioAdapter + HttpSseAdapter + discover_tools 서비스 |
| *(미커밋)* | MCP CRUD API + 자동/수동 discovery 엔드포인트 |
| *(미커밋)* | 백엔드 테스트 4개 파일 (모델·리포·어댑터·API) |
| *(미커밋)* | 프론트엔드 타입·API 클라이언트 + 3개 컴포넌트 + /tools 페이지 |
| *(미커밋)* | ruff format·lint 8개 오류 수정 |
| *(미커밋)* | StreamableHttpAdapter 추가, transport 3종 지원 (`m2_002`, `m2_003`) |
| *(미커밋)* | Dockerfile에 Node.js 22 추가 (npx STDIO MCP 지원) |
| *(미커밋)* | 프론트엔드 서버 등록 즉시 반영 버그 수정 (state lift-up) |
| *(미커밋)* | RegisterMcpModal 3탭 UI (STDIO / HTTP/SSE / Streamable HTTP) |

---

## 태스크 체크리스트

### 태스크 1-3: 기반 인프라

- [x] **태스크 1** — M2 의존성 추가 (`mcp`, `langchain-mcp-adapters`)
- [x] **태스크 2** — MCPServer 모델 + `mcp_transport` Enum + JSON 컬럼 설계
- [x] **태스크 3** — Alembic 마이그레이션 `m2_001` (down_revision=m1_001)

### 태스크 4-6: 에러·설정·스키마

- [x] **태스크 4** — 에러 코드 추가 (`MCP_NOT_FOUND`, `MCP_DUPLICATE_NAME`, `MCP_CONNECTION_FAILED`, `MCP_DISCOVERY_FAILED`)
- [x] **태스크 5** — `mcp_discovery_timeout` 설정 (기본값 30초)
- [x] **태스크 6** — Pydantic 스키마 (`ToolMetadata`, `MCPServerCreate`, `MCPServerUpdate`, `MCPServerRead`)

### 태스크 7: 리포지터리

- [x] **태스크 7** — `MCPRepository` (create·list_all·get_by_id·update·delete·update_discovered_tools)

### 태스크 8-10: 어댑터·디스커버리

- [x] **태스크 8** — `StdioAdapter` (subprocess stdio_client, asyncio.wait_for 타임아웃 적용)
- [x] **태스크 9** — `HttpSseAdapter` (sse_client + 헤더 전달)
- [x] **태스크 9b** — `StreamableHttpAdapter` (streamablehttp_client, MCP spec 2025-03-26+)
- [x] **태스크 10** — `discover_tools` 서비스 (connect→list_tools→DB 캐시→close)

### 태스크 11-12: API

- [x] **태스크 11** — MCP CRUD API (POST/GET/GET/{id}/PUT/DELETE)
- [x] **태스크 12** — 자동 discovery (BackgroundTask) + 수동 rediscover (`POST /{id}/discover`)

### 태스크 13: 백엔드 테스트

- [x] **태스크 13** — 유닛 테스트 4파일 작성 및 15개 케이스 통과
  - `test_models_mcp.py` (4개) — 필드 기본값, transport enum, discovered_tools JSON
  - `test_mcp_repository.py` (7개) — CRUD + update_discovered_tools
  - `test_mcp_adapters.py` (4개) — _tool_to_dict, StdioAdapter/HttpSseAdapter init, _build_adapter
  - `test_mcp_api.py` (9개) — Docker E2E 기준 (host venv ebooklib 의존성 충돌로 host 단독 실행 제외)

### 태스크 14: 프론트엔드

- [x] **태스크 14** — `frontend/lib/mcp.ts` (타입·API 클라이언트, `/api` 프록시 경유)
- [x] `ToolCatalog.tsx` — 발견된 도구 그리드 렌더링 (name·description·input_schema)
- [x] `McpServerList.tsx` — 서버 카드 (enabled 토글·삭제·재발견·도구목록 펼침)
- [x] `RegisterMcpModal.tsx` — STDIO / HTTP/SSE / Streamable HTTP 3탭 모달
- [x] `app/tools/page.tsx` — `'use client'`, useEffect mount 시 서버 목록 로드

### 태스크 15: 마감

- [x] **태스크 15** — ruff format·lint 통과, M2 상태 문서 작성

---

## 구현 중 발견 버그 및 개선

### 1차: 초기 구현

| 버그 | 원인 | 수정 |
|------|------|------|
| PUT `/{id}` → HTTP 500 `ResponseValidationError` | `onupdate=func.now()` 로 인해 flush 후 `updated_at` 속성이 expire됨. 비동기 컨텍스트 밖에서 접근 시 `MissingGreenlet` 발생 | `await session.commit()` 후 `await session.refresh(server)` 추가 |
| ruff B904: `raise AppError` without `from exc` | `except IntegrityError as exc` 내부에서 cause 미전달 | `raise AppError(...) from exc` 로 수정 (2곳) |
| ruff UP042: `str, enum.Enum` 패턴 | Python 3.11+ 에서는 `enum.StrEnum` 권장 | `class MCPTransport(enum.StrEnum)` 로 변경 |
| ruff SIM105: `try/except/pass` | bare `try/except` 블록 | `contextlib.suppress(Exception)` 으로 교체 |
| ruff UP017: `datetime.timezone.utc` | Python 3.11+ `UTC` 별칭 권장 | `from datetime import UTC` + `datetime.now(tz=UTC)` |
| ruff N811: `UUID as PgUUID` | 임포트 alias 대문자 규칙 위반 | `# noqa: N811` 추가 (M1 knowledge.py 동일 패턴) |
| `test_mcp_api.py` host 단독 수집 오류 | host venv에 `ebooklib` 미설치 → knowledge 라우터 임포트 실패 | API 테스트는 Docker E2E에서만 실행 |

### 2차: Transport 확장 & UI 버그 수정

| 항목 | 내용 |
|------|------|
| Streamable HTTP transport 추가 | `StreamableHttpAdapter` 구현 (`mcp.client.streamable_http.streamablehttp_client`) |
| Transport ENUM 변경 | `stdio` + `http_sse` → `stdio` + `http_sse` + `streamable_http` (3종 지원) |
| Alembic `m2_002` | `streamable_http` ENUM 값 추가, `stdio` 제거 |
| Alembic `m2_003` | `stdio` ENUM 값 재추가 (3종 모두 지원) |
| Dockerfile Node.js 추가 | `python:3.13-slim`에 Node.js 22 설치 → 컨테이너 내 `npx` 사용 가능 |
| 서버 등록 후 UI 미반영 버그 | `McpServerList`가 `initialServers`를 자체 useState로 복사 → prop 변경 무시 | state를 `ToolsPage`로 lift-up, `McpServerList`는 props만 렌더링 |
| RegisterMcpModal 3탭 UI | STDIO / HTTP/SSE / Streamable HTTP 탭 + 각 transport별 힌트 표시 |
| McpServerList transport 라벨 | `stdio: '📦 STDIO'`, `http_sse: '🌐 HTTP/SSE'`, `streamable_http: '⚡ Streamable HTTP'` |

---

## E2E 검증 결과 (Docker)

```
POST   /api/mcp                → 201 Created  (stdio / http_sse / streamable_http 모두 정상)
GET    /api/mcp                → 200           (목록)
GET    /api/mcp/{id}           → 200           (단건 조회)
PUT    /api/mcp/{id}           → 200           (수정, session.refresh 적용)
POST   /api/mcp/{id}/discover  → 200 / 502     (성공 또는 MCP_DISCOVERY_FAILED)
DELETE /api/mcp/{id}           → 204 No Content
POST   /api/mcp (중복 이름)    → 409 MCP_DUPLICATE_NAME
GET    /api/mcp/{없는 ID}      → 404 MCP_NOT_FOUND
POST   /api/mcp (transport=stdio, 이전에는 거부됨) → 201 (3종 모두 허용)
GET    /tools                  → 200           (프론트엔드 도구 탭 페이지)
```

컨테이너 런타임:
- Node.js: v22.x, npx: v10.x (STDIO MCP 서버 실행 가능)
- MCP SDK: v1.27.0 (stdio_client, sse_client, streamablehttp_client 모두 사용 가능)
- Alembic 헤드: `m2_003`
- DB ENUM `mcp_transport`: `stdio`, `http_sse`, `streamable_http`

---

## 알려진 제한사항 및 M3 고려사항

| 항목 | 상태 | 비고 |
|------|------|------|
| HTTP/SSE·Streamable HTTP env_vars | 미사용 | HTTP 전송에서는 env_vars를 헤더로 전달하지 않음 (정보용) |
| discovery 실패 시 UI 피드백 | 미구현 | 서버 등록은 성공하나 도구 목록이 빈 상태로 표시됨 |
| MCP 서버 연결 풀 (장기 세션) | 미구현 | M4 tool execution에서 long-lived session 관리 필요 |
| `test_mcp_api.py` host 단독 실행 | 미지원 | Docker E2E 또는 pytest conftest isolation 필요 |

> **M3~M5 체크포인트**:
> - MCP 어댑터를 장기 세션으로 재사용할 경우 `connect()`/`close()` 생명주기 관리 필수
> - langchain-mcp-adapters M4 tool execution 시 `discovered_tools` JSON → LangChain Tool 객체 변환 로직 필요
> - 새 NEXT_PUBLIC_* 환경변수 추가 시 `frontend/Dockerfile` build 스테이지에 ARG+ENV 반드시 선언
> - STDIO MCP는 컨테이너 내 Node.js/Python 런타임에 의존 — 새 런타임 필요 시 Dockerfile 수정
