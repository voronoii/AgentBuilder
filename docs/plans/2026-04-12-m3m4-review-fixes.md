# M3~M4 코드 리뷰 & 수정 계획

**작성일**: 2026-04-12
**상태**: In Progress
**목적**: M3(워크플로우 캔버스) + M4(실행 엔진) 구현의 코드 리뷰 결과 정리 및 수정 추적

---

## 리뷰 방법

4개 전문 에이전트를 병렬 투입:
1. **프론트엔드 리뷰** (TypeScript/React) — 타입 안전성, React 패턴, 접근성
2. **백엔드 M4 리뷰** (Python) — 비동기 패턴, 에러 처리, 리소스 관리
3. **LangGraph 패턴 리뷰** — StateGraph 설계, 이벤트 매핑, 노드간 데이터 전달
4. **M3 API/스키마 리뷰** (Python) — API 설계 일관성, DB 모델, 보안

---

## CRITICAL (반드시 수정) — Phase 1

| # | 이슈 | 파일 | 영향 | 상태 |
|---|------|------|------|------|
| C1 | **MCP 어댑터 연결 미정리** — happy path에서 `adapter.close()` 없음. Agent 실행마다 연결 누수 | `nodes/agent.py` | 리소스 누수 | ✅ |
| C2 | **컴파일 시점 DB 세션을 런타임에 재사용** — `make_chat_model(session=session)`, `_load_mcp_tools(session)` 모두 닫힌 세션 사용 가능 | `nodes/agent.py`, `nodes/llm.py` | 런타임 크래시 | ✅ |
| C3 | **node_outputs에 LangGraph reducer 없음** — 병렬 노드가 `{**state, node_id: output}` 반환 시 한쪽 결과 소실 | `state.py` | 데이터 손실 | ✅ |
| C4 | **get_input_text가 토폴로지 무시** — `node_id`를 받지만 미사용, 마지막 dict 값만 반환. 분기 그래프에서 잘못된 입력 읽음 | `nodes/utils.py` | 잘못된 결과 | ✅ |
| C5 | **다중 sink 노드 시 마지막 하나만 END 연결** — 나머지 분기는 LangGraph에서 오류 | `compiler.py` | 컴파일 실패 | ✅ |

---

## HIGH (출시 전 수정 필요) — Phase 2

| # | 이슈 | 파일 | 상태 |
|---|------|------|------|
| H1 | **워크플로우 실행 타임아웃 없음** — 무한 루프 시 세마포어 슬롯 영구 점유 | `runtime.py` | ✅ |
| H2 | **토큰마다 DB commit** — 500토큰 = 500회 commit. 성능 저하 | `runtime.py` | ✅ |
| H3 | **시크릿 평문 저장** + 비보호 raw-secret 엔드포인트 (`GET /settings/{key}/value`) | `settings.py` | ✅ |
| H4 | **`get_settings()` 매 호출마다 새 인스턴스** — env 파싱 반복, 핫패스 성능 | `core/config.py` | ✅ |
| H5 | **MCP discovery 백그라운드 태스크가 닫힌 세션 사용** | `api/mcp.py` | ✅ |
| H6 | **`create_react_agent`의 `prompt` 파라미터** — LangGraph 0.6.11에서 정식 지원 확인 | `nodes/agent.py` | ✅ (이슈 아님) |
| H7 | **프론트엔드 `as unknown as` 캐스트** — React Flow 타입 제약으로 현 버전에서 제거 불가 | `NodeConfigPanel.tsx`, `BaseNode.tsx` | ⏸ 보류 |
| H8 | **Auto-save 실패 무시** — `saveFn().catch(() => {})` | `workflowStore.ts` | ✅ |
| H9 | **숫자 입력 NaN 미처리** — `parseFloat('')` → NaN이 서버로 전송 | `NodeConfigPanel.tsx` | ✅ |

---

## MEDIUM (개선 권장) — Phase 3

| # | 이슈 | 상태 |
|---|------|------|
| M1 | nodes/edges 스키마에 구조 검증 없음 (`dict[str, Any]` 수용) | ✅ |
| M2 | providers API에 response_model/Pydantic 스키마 없음 | ✅ |
| M3 | 파일 업로드 시 전체 메모리 로드 후 크기 체크 | ✅ |
| M4 | Validator가 ChatInput→ChatOutput 연결 경로를 검증하지 않음 | ✅ |
| M5 | `validateWorkflow()` 함수가 존재하지만 프론트에서 호출하지 않음 | ✅ |
| M6 | `fetch('/api/...')` 하드코딩 — `apiBase()` 패턴 미사용 (SSR 깨짐) | ✅ |
| M7 | 접근성: 버튼에 `aria-label` 누락 (✕ 버튼들) | ✅ |
| M8 | `NODE_LABELS` 상수 중복 정의 (2곳) | ✅ |
| M9 | deprecated `@app.on_event("startup")` 사용 | ✅ |
| M10 | 실행 이벤트 목록에서 `key={i}` (index as key) | ✅ |

---

## 수정 기록

### CRITICAL Phase 1 — 2026-04-12 완료

**C3: node_outputs reducer 추가**
- `state.py`: `_merge_dicts` reducer 함수 추가, `node_outputs: Annotated[dict, _merge_dicts]`로 변경
- 모든 노드 (6개): `{**state.get("node_outputs", {}), node_id: output}` → `{node_id: output}`로 단순화 (reducer가 자동 병합)

**C4: get_input_text 선행노드 매핑**
- `utils.py`: `predecessor_ids` 파라미터 추가. 있으면 선행 노드 출력을 join, 없으면 기존 fallback 유지
- `compiler.py`: 엣지 분석으로 `predecessor_map` 구성, `create_node_function`에 전달
- `registry.py`: `predecessor_ids` 파라미터 추가, 각 노드 팩토리에 전달
- 4개 노드 (llm, agent, knowledge_base, prompt_template): `predecessor_ids` 수용 및 `get_input_text`에 전달

**C5: 다중 sink → END 연결**
- `compiler.py`: `_find_last_processing_node` → `_find_sink_nodes`로 변경, 모든 sink를 `list[str]`로 반환, 각각 `graph.add_edge(sink, END)` 연결

**C1: MCP 어댑터 연결 정리**
- `agent.py`: `_load_mcp_tools` 반환 타입을 `tuple[list, list]` (tools, adapters)로 변경
- `_close_adapters()` 유틸 함수 추가
- `agent_node` 내 `try/finally`로 실행 후 어댑터 정리 보장

**C2: DB 세션 컴파일/런타임 분리**
- `chat/registry.py`: `resolve_provider_credentials()` (컴파일 시점 DB 조회) + `make_chat_model_sync()` (런타임, DB 불필요) 분리. 기존 `make_chat_model()`은 편의 래퍼로 유지
- `llm.py`: `async make_llm_node`로 변경. 컴파일 시점에 `resolve_provider_credentials()`, 런타임에 `make_chat_model_sync()` 사용
- `agent.py`: 동일 패턴 적용. credentials 컴파일 시점 resolve
- `registry.py`: `make_llm_node` 호출에 `await` 추가

**검증 결과**
- 모든 임포트 정상 ✅
- 워크플로우 실행 `status: success` 확인 (arcee-ai/trinity-large-preview:free 모델) ✅

### HIGH Phase 2 — 2026-04-12 완료

**H1: 워크플로우 실행 타임아웃**
- `runtime.py`: `asyncio.wait_for(_stream(), timeout=MAX_RUN_TIMEOUT_SECONDS)` (300초)
- 타임아웃 시 `failed` 상태 + 에러 메시지 기록

**H2: 토큰별 DB commit 배치화**
- `runtime.py`: `_EVENT_BATCH_SIZE = 20` — 20개 이벤트마다 `session.commit()`. 스트리밍 종료 시 잔여 flush
- SSE 전송은 즉시 유지 (응답성 보장), DB 쓰기만 배치화

**H3: 시크릿 엔드포인트 제거**
- `settings.py`: `GET /settings/{key}/value` 엔드포인트 삭제 — 비인증 환경에서 raw secret 노출 방지
- 백엔드 서비스는 `SettingsRepository.get_value()` 직접 사용

**H4: get_settings() 캐싱**
- `config.py`: 모듈 레벨 `_settings_cache` 싱글턴. 첫 호출에만 `.env` 파싱, 이후 캐시 반환

**H5: MCP discovery 세션 분리**
- `mcp.py`: `_try_discover(server_id, timeout)` — `get_sessionmaker()`로 별도 세션 생성
- 요청 스코프 세션 재사용 방지

**H6: create_react_agent prompt 파라미터**
- LangGraph 0.6.11에서 `prompt` 파라미터 정식 지원 확인 (SystemMessage | str). 이슈 아님

**H7: as unknown as 캐스트**
- React Flow `Node.data`가 `Record<string, unknown>` 타입이므로 `as unknown as NodeData` 캐스트 불가피. 보류

**H8: Auto-save 실패 UI 표시**
- `workflowStore.ts`: `saveError: string | null` 상태 추가
- `_scheduleAutoSave`에 `onError` 콜백 전달 → 실패 시 `saveError` 설정
- `saveWorkflow` 성공 시 `saveError = null`로 초기화

**H9: 숫자 입력 NaN 가드**
- `NodeConfigPanel.tsx`: 모든 `parseFloat`/`parseInt` 호출에 `Number.isNaN()` 가드 추가
- NaN인 경우 `onChange` 미호출 (기존 값 유지)
