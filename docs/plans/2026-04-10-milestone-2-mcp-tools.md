# 마일스톤 2 — MCP 도구 시스템 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**목표:** MCP(Model Context Protocol) 서버를 등록·관리하고, 연결된 서버에서 사용 가능한 도구(Tool)를 자동 디스커버리하여 DB에 캐싱. M4 에이전트 노드에서 `langchain-mcp-adapters`로 LangChain Tool 변환 후 사용할 기반을 제공.

**아키텍처:**
- **백엔드**: `/mcp` CRUD API (POST/GET/GET/{id}/PUT/DELETE) + `/mcp/{id}/discover` 엔드포인트. `MCPServer` SQLAlchemy 모델. STDIO 어댑터(subprocess로 로컬 바이너리 실행)와 HTTP/SSE 어댑터(원격 MCP 서버 연결). 디스커버리 서비스가 `list_tools` 호출 → `discovered_tools` JSON 컬럼에 캐싱.
- **프론트엔드**: `/tools` 페이지 — 서버 목록, 등록 모달(STDIO | HTTP/SSE 탭), 서버별 툴 카탈로그 표시, 활성/비활성 토글.
- **범위 제한**: 등록·디스커버리·캐싱까지. 실제 도구 실행(tool_call)은 M4 범위.

**기술 스택 추가:** `mcp` (MCP Python SDK), `langchain-mcp-adapters` (pyproject.toml에 추가)

**참조 스펙:** [docs/specs/2026-04-08-agentbuilder-design.md](../specs/2026-04-08-agentbuilder-design.md) §7 (전체)
**M1 교훈 적용:** Dockerfile ARG/ENV, /api 프록시 경유, qdrant-client 호환성, SSE 폴링 fallback

---

## 파일 구조 (태스크 시작 전 확정)

```
AgentBuilder/
├── backend/
│   ├── pyproject.toml                                         (modify — add M2 deps)
│   ├── app/
│   │   ├── main.py                                            (modify — register mcp router)
│   │   ├── core/
│   │   │   ├── config.py                                      (modify — add MCP settings)
│   │   │   └── errors.py                                      (modify — add MCP error codes)
│   │   ├── models/
│   │   │   ├── __init__.py                                    (modify — export MCPServer)
│   │   │   └── mcp.py                                         (new — MCPServer model)
│   │   ├── schemas/
│   │   │   └── mcp.py                                         (new — Pydantic DTOs)
│   │   ├── repositories/
│   │   │   └── mcp.py                                         (new — CRUD helpers)
│   │   ├── services/
│   │   │   └── mcp/
│   │   │       ├── __init__.py                                (new)
│   │   │       ├── adapters.py                                (new — STDIO + HTTP/SSE 어댑터)
│   │   │       └── discovery.py                               (new — list_tools → DB 캐싱)
│   │   └── api/
│   │       └── mcp.py                                         (new — CRUD + discover 라우터)
│   ├── alembic/versions/
│   │   └── m2_001_mcp_servers.py                              (new — mcp_servers 테이블)
│   └── tests/
│       ├── test_models_mcp.py                                 (new)
│       ├── test_mcp_repository.py                             (new)
│       ├── test_mcp_adapters.py                               (new)
│       └── test_mcp_api.py                                    (new)
├── frontend/
│   ├── lib/
│   │   └── mcp.ts                                             (new — MCP API client)
│   ├── app/tools/
│   │   └── page.tsx                                           (new — 도구 탭 페이지)
│   └── components/mcp/
│       ├── McpServerList.tsx                                   (new — 서버 카드 목록)
│       ├── RegisterMcpModal.tsx                                (new — 등록 모달)
│       └── ToolCatalog.tsx                                     (new — 툴 카탈로그 표시)
```

---

## 태스크 분해

### 태스크 1: M2 의존성 추가

- [ ] `pyproject.toml`에 `mcp>=1.0,<2.0` 및 `langchain-mcp-adapters>=0.1,<1.0` 추가
- [ ] 컨테이너 내 pip install 확인

### 태스크 2: MCPServer 모델 + ErrorCode 추가

- [ ] `backend/app/models/mcp.py` — MCPServer SQLAlchemy 모델
  - `id: UUID` (PK)
  - `name: str` (unique, max 200)
  - `description: str` (Text, default "")
  - `transport: MCPTransport` (enum: stdio | http_sse)
  - `config: dict` (JSON — transport별: command/args 또는 url/headers)
  - `env_vars: dict` (JSON — 환경변수)
  - `enabled: bool` (default True)
  - `discovered_tools: list` (JSON — ToolMetadata 캐시)
  - `last_discovered_at: datetime | None`
  - `created_at, updated_at`
- [ ] `backend/app/models/__init__.py`에 MCPServer import 추가
- [ ] `backend/app/core/errors.py`에 MCP 에러코드 추가:
  - `MCP_NOT_FOUND`, `MCP_DUPLICATE_NAME`, `MCP_CONNECTION_FAILED`, `MCP_DISCOVERY_FAILED`

### 태스크 3: Alembic 마이그레이션

- [ ] `m2_001_mcp_servers.py` — mcp_servers 테이블 + mcp_transport enum
- [ ] M1 패턴 참고 (enum create/drop, UUID PK, JSON columns)

### 태스크 4: MCP 스키마 (Pydantic DTO)

- [ ] `MCPServerCreate`: name, description, transport, config, env_vars
- [ ] `MCPServerUpdate`: name?, description?, config?, env_vars?, enabled?
- [ ] `MCPServerRead`: 전체 필드 + from_attributes
- [ ] `ToolMetadata`: name, description, input_schema (JSON)

### 태스크 5: MCP 리포지터리

- [ ] `MCPRepository` — create, list_all, get_by_id, update, delete, update_discovered_tools

### 태스크 6: STDIO 어댑터

- [ ] `StdioAdapter` — asyncio.subprocess로 MCP 서버 실행
- [ ] `connect()` → MCP 세션 초기화
- [ ] `list_tools()` → Tool 목록 반환
- [ ] `close()` → 프로세스 종료
- [ ] 타임아웃 (30초 기본)

### 태스크 7: HTTP/SSE 어댑터

- [ ] `HttpSseAdapter` — httpx로 원격 MCP 서버 연결
- [ ] `connect()` → SSE 또는 Streamable HTTP 세션
- [ ] `list_tools()` → Tool 목록 반환
- [ ] `close()` → 연결 종료
- [ ] 헤더/인증 지원

### 태스크 8: 툴 디스커버리 서비스

- [ ] `discover_tools(server: MCPServer)` → 어댑터 선택 → list_tools → ToolMetadata 변환
- [ ] DB에 `discovered_tools` + `last_discovered_at` 업데이트
- [ ] 에러 시 `MCP_DISCOVERY_FAILED` AppError

### 태스크 9: MCP API 라우터

- [ ] `POST /mcp` — 서버 등록 (생성 직후 자동 디스커버리 시도, 실패해도 등록 유지)
- [ ] `GET /mcp` — 서버 목록
- [ ] `GET /mcp/{id}` — 서버 상세
- [ ] `PUT /mcp/{id}` — 서버 수정
- [ ] `DELETE /mcp/{id}` — 서버 삭제
- [ ] `POST /mcp/{id}/discover` — 수동 재디스커버리

### 태스크 10: main.py + Settings 업데이트

- [ ] `config.py`에 `mcp_discovery_timeout: int = 30` 추가
- [ ] `main.py`에 mcp 라우터 등록

### 태스크 11: 백엔드 테스트

- [ ] 모델 테스트 (MCPServer CRUD)
- [ ] 리포지터리 테스트
- [ ] 어댑터 mock 테스트 (subprocess mock)
- [ ] API 엔드포인트 테스트 (TestClient)

### 태스크 12: 프론트엔드 lib/mcp.ts

- [ ] `MCPServer`, `ToolMetadata` 타입 정의
- [ ] `listMcpServers()`, `createMcpServer()`, `getMcpServer()`, `updateMcpServer()`, `deleteMcpServer()`, `discoverTools()` 함수

### 태스크 13: 도구 탭 UI

- [ ] `/tools/page.tsx` — 서버 목록 페이지 (SSR)
- [ ] `McpServerList.tsx` — 서버 카드 (이름, transport, 상태, 툴 수, 편집/삭제)
- [ ] `RegisterMcpModal.tsx` — STDIO | HTTP/SSE 탭 전환 등록 폼
- [ ] `ToolCatalog.tsx` — 서버별 디스커버된 툴 목록 (이름, 설명, 스키마)
- [ ] 활성/비활성 토글, 재디스커버리 버튼

### 태스크 14: Docker E2E 테스트

- [ ] `docker compose up --build` 정상 기동
- [ ] MCP CRUD API 호출 테스트
- [ ] 도구 탭 UI 렌더링 확인
- [ ] M1 교훈 체크 (프록시, Dockerfile ARG)

### 태스크 15: M2 상태 문서 작성

- [ ] `docs/tracking/m2-status.md` — 태스크별 체크리스트, 커밋 목록, 알려진 제한사항
