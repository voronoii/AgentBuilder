# M3 — 워크플로우 캔버스 상태

> 최종 업데이트: 2026-04-10

## 상태: ✅ 완료

## 백엔드

| # | 태스크 | 상태 | 파일 |
|---|--------|------|------|
| B1 | CORS 설정 | ✅ M0에서 완료 | `app/main.py`, `app/core/config.py` |
| B2 | 브라우저/서버 URL 이원화 | ✅ M0에서 완료 | `frontend/lib/api.ts`, `next.config.mjs` |
| B3 | Workflow 모델 + 마이그레이션 | ✅ | `app/models/workflow.py`, `alembic/versions/m3_001_workflows.py` |
| B4 | Pydantic 스키마 | ✅ | `app/schemas/workflow.py` |
| B5 | WorkflowRepository + CRUD API | ✅ | `app/repositories/workflow.py`, `app/api/workflow.py` |
| B6 | ChatProvider 정적 목록 API | ✅ | `app/api/providers.py` |
| B7 | 저장 시 유효성 검사 (경고 수준) | ✅ | `app/api/workflow.py` (`_validate_workflow`) |

### API 엔드포인트

| Method | Path | 설명 |
|--------|------|------|
| POST | `/workflows` | 워크플로우 생성 |
| GET | `/workflows` | 워크플로우 목록 |
| GET | `/workflows/{id}` | 워크플로우 조회 |
| PUT | `/workflows/{id}` | 워크플로우 수정 (노드/엣지 저장) |
| DELETE | `/workflows/{id}` | 워크플로우 삭제 |
| POST | `/workflows/{id}/validate` | 유효성 검사 (경고 수준) |
| GET | `/providers` | ChatProvider 정적 목록 |

### Alembic

- **m3_001**: `workflows` 테이블 생성 (id, name, description, nodes(JSON), edges(JSON), created_at, updated_at)

## 프론트엔드

| # | 태스크 | 상태 | 파일 |
|---|--------|------|------|
| F1 | Zustand 스토어 2개 | ✅ | `stores/workflowStore.ts`, `stores/sidebarStore.ts` |
| F2 | React Flow 캔버스 | ✅ | `components/workflow/WorkflowEditor.tsx` |
| F3 | 워크플로우 목록/생성 | ✅ | `app/workflows/page.tsx`, `components/workflow/WorkflowList.tsx` |
| F4 | 6종 노드 UI | ✅ | `components/workflow/nodes/BaseNode.tsx`, `nodes/nodeStyles.ts` |
| F5 | 좌측 사이드바 | ✅ | `components/workflow/Sidebar.tsx` |
| F6 | 노드 설정 패널 | ✅ | `components/workflow/NodeConfigPanel.tsx` |
| F7 | 엣지 연결 + 핸들 | ✅ | BaseNode의 Handle + workflowStore onConnect |
| F8 | 그래프 저장/로드 | ✅ | workflowStore saveWorkflow/loadWorkflow |

### 추가된 의존성

- `@xyflow/react` ^12.10.2
- `zustand` ^5.0.12

### 노드 타입 ↔ Clay 색상 매핑

| 노드 | 색상 | 아이콘 |
|------|------|--------|
| ChatInput | Pomegranate | 💬 |
| ChatOutput | Pomegranate | 📤 |
| LLM | Slushie | 🧠 |
| Agent | Ube | 🤖 |
| Knowledge Base | Matcha | 📚 |
| Prompt Template | Lemon | 📝 |

## Docker E2E 테스트 결과

- `docker compose build` ✅ (api + web 모두 성공)
- `docker compose up -d` ✅ (4-service 정상 가동)
- API 엔드포인트 테스트:
  - `GET /health` ✅
  - `POST /workflows` ✅ (생성)
  - `GET /workflows` ✅ (목록)
  - `PUT /workflows/{id}` ✅ (노드/엣지 저장)
  - `POST /workflows/{id}/validate` ✅ (ChatOutput 누락 감지)
  - `DELETE /workflows/{id}` ✅ (204)
  - `GET /providers` ✅ (3개 프로바이더 반환)
- 프론트엔드: `http://localhost:23000/workflows` ✅ (200)
- API 프록시: `http://localhost:23000/api/health` ✅

## 교훈 & 주의사항

1. `session.refresh()` 적용 — `onupdate=func.now()` 사용 시 필수 (M2 교훈 #3)
2. React Flow는 `'use client'` 필수 — Next.js App Router Client Component
3. 편집 페이지 `fixed inset-0` — root layout의 TopNav/main wrapper를 오버라이드
4. ruff B904 — `except` 블록에서 `raise ... from exc` 패턴 적용
5. Node/Edge JSON blob — React Flow 형태 그대로 저장, 프론트에서 추가 변환 없이 복원

## M4에서 구현할 항목

- `WorkflowRun` + `RunEvent` 모델
- `make_chat_model()` — Provider별 LLM 인스턴스 생성
- `WorkflowCompiler` — UI graph → LangGraph 변환
- 엄격 유효성 검사 (사이클, 고립 노드, 타입 불일치)
- 📊 실행로그 사이드바 탭
- 플레이그라운드 패널 (우측 채팅 UI)
