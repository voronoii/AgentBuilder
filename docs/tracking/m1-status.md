# M1 Knowledge Base / RAG — 구현 상태

> 완료일: 2026-04-09  
> 브랜치: `feat/m1-knowledge-rag`  
> 테스트: 37 passed, 1 skipped (qdrant — docker 미기동 시 건너뜀)

---

## 커밋 목록

| 커밋 | 내용 |
|------|------|
| `a7526a8` | M1 RAG 의존성 추가 + HF 모델 smoke 테스트 (M0 follow-up E 해소) |
| `50821a9` | 에러 엔벨로프, request-id 미들웨어, CORS, dual-URL (M0 follow-up A/B/F 해소) |
| `912f9de` | KnowledgeBase·Document 모델 + Alembic 마이그레이션 |
| `1d62f0a` | 임베딩 레지스트리, fastembed/local_hf 프로바이더, Qdrant 래퍼, 스키마, 리포지터리 |
| `8d3dd31` | Progress Bus + 수집 파이프라인 |
| `384e33f` | 파일 파서 11종 + 청커 + 레지스트리 |
| `6bf700c` | 오케스트레이터 + Knowledge API (CRUD·업로드·SSE·검색) |
| `7f072ad` | 프론트엔드 지식베이스 UI (목록/생성/상세/업로드/SSE/검색) |
| `c169353` | ruff format·lint 적용 |

---

## 태스크 체크리스트

### 태스크 1-3: 기반 인프라

- [x] **태스크 1** — M1 의존성 추가 (`a7526a8`)
- [x] **태스크 2** — 에러 엔벨로프 + CORS + dual-URL (`50821a9`)
- [x] **태스크 3** — KnowledgeBase·Document 모델 + 마이그레이션 (`912f9de`)

### 태스크 4-7: 임베딩·벡터 스토어

- [x] **태스크 4** — EmbeddingProvider Protocol + fastembed 프로바이더 (`1d62f0a`)
- [x] **태스크 5** — LocalHfProvider (Snowflake Arctic Embed L Ko) (`1d62f0a`)
- [x] **태스크 6** — 임베딩 레지스트리 (register·get·build_default) (`1d62f0a`)
- [x] **태스크 7** — QdrantStore (ping·create_collection·upsert·search·delete) (`1d62f0a`)

### 태스크 8-12: 파서·청커

- [x] **태스크 8** — ParsedDocument·Parser Protocol + 파서 레지스트리 (`384e33f`)
- [x] **태스크 9** — txt/md/html/xml 파서 (`384e33f`)
- [x] **태스크 10** — pdf/docx/pptx/xlsx/csv 파서 (`384e33f`)
- [x] **태스크 11** — epub/eml 파서 (`384e33f`)
- [x] **태스크 12** — RecursiveCharacterTextSplitter 기반 청커 (`384e33f`)

### 태스크 13-14: 수집 파이프라인

- [x] **태스크 13** — ProgressBus (publish·subscribe, 최신 상태 replay) (`8d3dd31`)
- [x] **태스크 14** — run_ingestion (parse→chunk→embed→upsert, 결정적 point ID) (`8d3dd31`)

### 태스크 15-19: 오케스트레이터·API

- [x] **태스크 15** — IngestionOrchestrator (semaphore, 3-phase execute, fail) (`6bf700c`)
- [x] **태스크 16** — Bootstrap (get_store·get_orchestrator·session_factory) (`6bf700c`)
- [x] **태스크 17** — Knowledge CRUD API (POST/GET/GET/{id}/DELETE) (`6bf700c`)
- [x] **태스크 18** — Document 업로드·목록 API + 오케스트레이터 enqueue (`6bf700c`)
- [x] **태스크 19** — SSE 스트리밍 + Search API (`6bf700c`)

### 태스크 20-22: 프론트엔드

- [x] **태스크 20** — KB 목록 페이지 + TopNav 3탭 레이아웃 (`7f072ad`)
- [x] **태스크 21** — KB 생성 폼 (기본/고급 토글) (`7f072ad`)
- [x] **태스크 22** — KB 상세 (파일 업로드·SSE 진행 상황·검색 패널) (`7f072ad`)

### 태스크 23: 마감

- [x] **태스크 23** — ruff format·lint, M0 follow-up 마감, M1 상태 문서 (`c169353` + this)

---

## 실사용 테스트 후 발견 버그

### 1차 (2026-04-09)

| 커밋 | 버그 | 원인 | 수정 |
|------|------|------|------|
| `ecb0495` | TS 빌드 실패 — `kbs` 변수 암시적 `any[]` | `let kbs;` 선언에 타입 누락 | `let kbs: KnowledgeBase[] = []` |
| `3e09d63` | "새 지식베이스" 버튼·테두리·배경 미표시 | `clay-accent` 등 semantic 토큰이 Tailwind config에 미등록 | `tailwind.config.ts`에 `clay-accent/border/surface/text` 추가 |
| `5f5126c` | KB 생성 시 "failed to fetch" | `frontend/Dockerfile` build 스테이지에 `ARG NEXT_PUBLIC_API_URL` 선언 누락 → 번들에 `undefined` 박힘 | `ARG` + `ENV` 추가 |

### 2차 (2026-04-10) — 원격 E2E 테스트

| 커밋 | 버그 | 원인 | 수정 |
|------|------|------|------|
| `54e8bca` | 원격 브라우저에서 "failed to fetch" 지속 | 번들에 `localhost:28000` 하드코딩 → 원격 PC에서 도달 불가 | Next.js `rewrites()` 프록시 도입 (`/api/*` → `http://api:8000`), 브라우저는 same-origin `/api` 호출 |
| `f25b807` | KB 생성 시 500 `INTERNAL_UNEXPECTED` | 동일 이름 KB 재생성 → `IntegrityError` 미캐치 | `IntegrityError` catch → 409 `KNOWLEDGE_DUPLICATE_NAME` 응답 |
| `da3f233` | 파일 업로드 실패 (Qdrant 404) | `delete_by_document` 호출 시 컬렉션 미존재 | `_collection_exists` 체크 추가 + `ensure_collection` 자동 생성 로직 |
| `237c48a` | 파일 업로드 후 UI에 반영 안됨 | SSE가 `localhost:28000` 직접 연결 → 원격에서 수신 불가 | FileUpload → IngestionProgress 통합, SSE를 `/api` 프록시 경유로 변경 |
| `3e126db` | SSE 불안정 + 검색 500 에러 | SSE 원격 연결 불안정 / qdrant-client 1.17에서 `search()` 제거됨 | 2초 폴링 fallback 추가 / `search()` → `query_points()` 마이그레이션 |

### UX 개선 (2026-04-10)

| 변경 | 내용 |
|------|------|
| 업로드 안내 표시 | 지원 확장자 15종 + 최대 업로드 크기(50MB) 표시 |
| 파일 크기 검증 | 클라이언트 사전 검증 + 서버 413 `KNOWLEDGE_FILE_TOO_LARGE` |
| 청크 미리보기 | 완료 문서에서 상위 3개 청크 텍스트 미리보기 (Qdrant scroll API) |
| 신규 엔드포인트 | `GET /knowledge/config`, `GET /knowledge/{kb_id}/documents/{doc_id}/chunks` |

> **M2~M5 체크 포인트**:
> - 새 `NEXT_PUBLIC_*` 환경변수 추가 시 반드시 `frontend/Dockerfile` build 스테이지에도 `ARG` + `ENV` 선언 추가할 것
> - qdrant-client 버전 업그레이드 시 API 호환성 확인 필수 (1.14+ `search()` → `query_points()`)
> - 원격 접속 시 프론트엔드는 반드시 same-origin 프록시 경유 (직접 `localhost` 호출 금지)

---

## 알려진 제한사항 및 M2 고려사항

| 항목 | 상태 | 비고 |
|------|------|------|
| FastAPI `on_event` deprecation 경고 | 미처리 | lifespan handler로 교체 권장 (M2 전) |
| local_hf 프로바이더 오프라인 로드 | 미검증 | 컨테이너 내부 `/models/` 마운트 필요 |
| Qdrant 컬렉션 미존재 시 자동 생성 | 구현됨 | upload 시 `create_collection` 호출 |
| 스타트업 복구 (stale PROCESSING → FAILED) | 구현됨 | `main.py` lifespan 훅 |
| 프론트 SSE EventSource 브라우저 재연결 | 기본 동작 | 추가 구현 없음 |
