# M0 Follow-ups

> M0 완료(2026-04-09) 후 재검토에서 발견된 이슈 트래킹. 해결될 때마다 체크하고 관련 커밋 해시를 기록.

## 범례
- `[ ]` 미해결 / `[x]` 해결됨 / `[~]` 부분 해결
- 🚨 중요 (반드시 해결) / ⭐ 권장 / 💡 개선

---

## A. CORS 미들웨어 🚨

- [x] **상태**: 해결됨 (M1에서 선행 구현)
- **문제**: M0 현재는 Next.js Server Component가 컨테이너 내부 네트워크로 API를 호출하므로 CORS 불필요. M3/M4에서 클라이언트 사이드 fetch (SSE 스트리밍, React Flow 실시간 업데이트) 추가 시 브라우저가 `http://localhost:28000`을 호출하며 CORS 프리플라이트 발생.
- **해결책**:
  ```python
  # backend/app/main.py
  from fastapi.middleware.cors import CORSMiddleware
  app.add_middleware(
      CORSMiddleware,
      allow_origins=settings.cors_origins,
      allow_methods=["*"],
      allow_headers=["*"],
      allow_credentials=True,
  )
  ```
  `Settings`에 `cors_origins: list[str]` 추가. `.env.example`에서 `AGENTBUILDER_CORS_ORIGINS='["http://localhost:23000","http://localhost:3000"]'` 같은 JSON 리스트.
- **언제**: M1 Task 2에서 선행 처리
- **해결 커밋**: `50821a9`

---

## B. 브라우저용 vs 서버용 API URL 이원화 🚨

- [x] **상태**: 해결됨 (M1에서 선행 구현)
- **문제**: 현재 `docker-compose.yml`에서 `NEXT_PUBLIC_API_URL=http://api:8000`로 세팅. `NEXT_PUBLIC_*`은 **빌드 타임**에 클라이언트 번들에 박히므로, M3에서 클라이언트 사이드 fetch 추가 시 브라우저가 `http://api:8000`을 호출 시도 → 실패 (이 호스트는 브라우저 시점에 보이지 않음).
- **해결책**: Server Component와 Client Component용 URL을 분리.
  ```yaml
  # docker-compose.yml
  web:
    environment:
      NEXT_PUBLIC_API_URL: http://localhost:${API_PORT:-8000}   # 브라우저용 (빌드 타임)
      API_URL_INTERNAL: http://api:8000                          # 서버 컴포넌트용 (런타임)
  ```
  `frontend/lib/api.ts`에서 `typeof window === 'undefined' ? API_URL_INTERNAL : NEXT_PUBLIC_API_URL`로 분기.
- **주의**: `NEXT_PUBLIC_API_URL`은 빌드 시점 필요 → `web` Dockerfile의 build stage에 `ARG`로 주입하거나, docker-compose `build.args`로 전달.
- **언제**: M1 Task 2에서 선행 처리
- **해결 커밋**: `50821a9`

---

## C. HF_MODELS_PATH 하드코딩 ⭐

- [x] **상태**: 해결됨
- **문제**: `docker-compose.yml`에 `/DATA3/users/mj/hf_models` 절대 경로가 박혀 있어서 다른 머신·다른 사용자가 clone하면 깨짐.
- **해결책**: 환경변수로 교체 `${HF_MODELS_PATH:-/DATA3/users/mj/hf_models}:/models:ro`, `.env.example`에 기본값 추가.
- **해결 커밋**: `fc0e1c4`

---

## D. 장기 실행 작업 패턴 미정 🚨

- [x] **상태**: 스펙 확정됨, 구현은 M1/M4에서
- **문제**: M1 (파일 임베딩)과 M4 (워크플로우 실행)는 수초~수분짜리 백그라운드 작업 필요. 패턴 미정.
- **결정**: **`asyncio.create_task()` + 프로세스 메모리 상태 + DB에 최종/중간 상태 저장**. 재시작 시 진행 중 작업 손실 수용. Celery/Redis/Temporal 등은 오버킬.
- **이유**: 단일 사용자 MVP, 로컬 실행. 복잡도 대비 이익 없음. 향후 멀티 유저 시 재평가.
- **스펙 반영**: §6.6 (ingestion 실행 모델), §8.7 (워크플로우 실행 모델)에 명시
- **해결 커밋**: `417028c`

---

## E. M1 의존성 사전 점검 ⭐

- [x] **상태**: 해결됨 (M1 Task 1)
- **필요 패키지** (M1 시작 시 `pyproject.toml`에 추가):
  ```
  qdrant-client>=1.12
  langchain-core>=0.3
  langchain-text-splitters>=0.3
  langchain-huggingface>=0.1.2
  sentence-transformers>=3.3
  fastembed>=0.5,<1.0            # fallback (BAAI/bge-small-en-v1.5)
  pypdf>=5.1
  python-docx>=1.1
  python-pptx>=1.0
  openpyxl>=3.1
  ebooklib>=0.18
  beautifulsoup4>=4.12
  sse-starlette>=2.1
  ```
- **주의**: fastembed 0.8+ 에서 `intfloat/multilingual-e5-small` 제거됨 → `BAAI/bge-small-en-v1.5` 사용.
- **언제**: M1 Task 1에서 처리
- **해결 커밋**: `a7526a8`

---

## F. 에러 응답 포맷 표준 부재 ⭐

- [x] **상태**: 해결됨 (스펙 확정 M0, 구현 M1)
- **결정**: **FastAPI 기본 `HTTPException` + 일관된 JSON envelope**
  ```json
  {
    "detail": "human-readable message",
    "code": "KNOWLEDGE_NOT_FOUND",
    "request_id": "uuid"
  }
  ```
- **구현 방식**:
  - `app/core/errors.py`에 `AppError(HTTPException)` 베이스 클래스와 코드 enum
  - Global exception handler가 envelope로 직렬화
  - `request_id`는 middleware가 header에서 읽거나 생성
- **스펙 반영**: §11.2 (에러 응답 표준)으로 추가
- **해결 커밋**: `417028c` (스펙), `50821a9` (구현)

---

## G. 로깅 전략 미정 ⭐

- [ ] **상태**: 미해결 (M4 전 결정 필요)
- **문제**: 기본 uvicorn 로그만 있음. 구조화 로그 부재. 워크플로우 실행 추적 시 필요.
- **옵션**:
  - `loguru` — 설정 거의 필요 없음, 간편, JSON 지원
  - `structlog` — 더 강력, 러닝커브 있음
  - `logging` (stdlib) + dictConfig — 외부 의존성 없음
- **추천**: **`loguru`** (단일 사용자 MVP에 복잡도 vs 이익 비율 최적). JSON sink로 파일/stdout.
- **언제**: M4 Task 1 직전
- **해결 커밋**: —

---

## 즉시 처리한 오버 엔지니어링 항목 (2026-04-09 재검토)

### 1. HF_MODELS_PATH 환경변수화 → 위 **C**
### 2. 버전 문자열 단일 소스

- [x] **상태**: 해결됨
- **문제**: `pyproject.toml`, `app/main.py`, `app/api/health.py` 세 곳에 `0.0.1` 중복.
- **해결책**: `importlib.metadata.version("agentbuilder-backend")`로 `app/core/config.py`의 `APP_VERSION`에 통합. Fallback `"0.0.0"` (uninstalled case).
- **해결 커밋**: `bd3dd1c`

### 3. `/api/v1/health` 이중 마운트 제거

- [x] **상태**: 해결됨
- **문제**: `/health`와 `/api/v1/health` 동시 마운트는 MVP 단계에서 혼란만 줌.
- **결정**: **루트 라우트만 사용** (`/health`, 향후 `/workflows`, `/knowledge`, `/mcp`). API 버저닝은 당분간 없음.
- **해결 커밋**: `bd3dd1c`
- **리그레션 가드**: `test_api_v1_prefix_not_mounted` 테스트가 `/api/v1/health` 404를 assert — 실수로 다시 마운트되면 CI가 잡음

### 📌 API 버저닝 리마인더

**언젠가 필요할 때 복원 절차**:
1. `backend/app/main.py`에 `api_v1 = APIRouter(prefix="/api/v1")` 추가하고 기존 라우터들 이동
2. Breaking change를 포함하는 변경은 `/api/v2` 네임스페이스에서 시작
3. 프론트 `frontend/lib/api.ts`에 버전 상수 추가
4. **마이그레이션 트리거**: (a) 외부 사용자·통합자가 생김, (b) breaking change가 불가피해짐, (c) 멀티 클라이언트(모바일/CLI 등) 출현

이 리마인더는 스펙 §15 TBD에도 기록됨.

---

## 소소한 정리 💡

### H. `web` 컨테이너 healthcheck 추가

- [ ] `docker-compose.yml`에 `wget --spider http://localhost:3000` 기반 healthcheck 추가
- **언제**: 편할 때

### I. `docs/Untitled` 빈 파일 삭제

- [ ] 프로젝트 루트에 섞여 있음, 무해하지만 정리
- **언제**: 편할 때

### J. `backend/alembic/versions/.gitkeep` 제거

- [ ] 실제 migration 파일 존재하므로 더 이상 불필요
- **언제**: 편할 때

### K. `DESIGN.md` git 미추적

- [ ] `git status` 결과에 untracked. 루트에 있으므로 추적해야 할 듯 (확인 필요)
- **언제**: 지금

### L. Postgres/Qdrant 호스트 포트 노출

- [ ] MVP 디버깅 편의상 유지 OK. `.env.example`에 off 옵션 주석만 추가
- **언제**: 편할 때
