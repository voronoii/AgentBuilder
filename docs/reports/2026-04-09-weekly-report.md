# AgentBuilder 프로젝트 진행 현황 (2026-04-08 ~ 04-10)

## 프로젝트 개요
Dify/Langflow/Sim Studio를 벤치마킹한 **노드 기반 에이전트 빌더 플랫폼** 자체 개발. 지식베이스(RAG), 워크플로우 캔버스, 외부 MCP 도구를 조합해 LLM 에이전트를 시각적으로 구성할 수 있는 로컬 우선 플랫폼.

## 완료한 작업

### 1. 설계 및 기획
- **MVP 범위 확정**: 단일 사용자, 탭 3개(지식/워크플로우/도구), 핵심 노드 6종(Chat I/O, LLM, Agent, Knowledge Base, Prompt Template)
- **기술 스택 선정**:
  - 백엔드: FastAPI + SQLAlchemy(async) + LangGraph
  - 프론트엔드: Next.js 15 + React Flow + Tailwind + Zustand
  - 인프라: PostgreSQL + Qdrant(벡터 DB) + Docker Compose
- **한국어 임베딩 모델 기본값** 적용: Snowflake Arctic Embed L v2.0 Korean (로컬 HF, API 키 없이 즉시 사용)
- **설계 문서 작성**: `docs/specs/2026-04-08-agentbuilder-design.md` — 17개 섹션, 아키텍처/노드 카탈로그/RAG 파이프라인/MCP 통합/실행 엔진/결정 로그

### 2. Milestone 0 (Foundation) 구현 완료
- **Docker Compose 4-서비스 스택 구축 및 검증**: postgres, qdrant, api, web 컨테이너가 서로 연결되어 정상 동작 확인
- **백엔드 기반**: FastAPI 앱 팩토리, `/health` 엔드포인트, 환경변수 기반 Settings, 비동기 DB 엔진, Alembic 마이그레이션 기반 구축
- **프론트엔드 기반**: Next.js 15 스켈레톤, Clay 디자인 시스템 토큰(Tailwind), API 연동 페이지
- **테스트**: 백엔드 단위 테스트 8건 모두 통과 (TDD 방식)
- **커밋 이력**: 17개 커밋으로 단계별 추적 가능

### 3. 사후 리뷰 및 개선
- **재검토 수행**: 오버 엔지니어링 요소 제거, 누락된 설계 항목 식별
- **즉시 해결**: 버전 문자열 단일 소스화, 불필요한 API 버저닝 제거, HF 모델 경로 환경변수화
- **스펙 보강**: 장기 실행 작업 패턴, 에러 응답 표준, CORS/URL 정책 섹션 추가
- **후속 이슈 트래킹 문서 작성**: `docs/tracking/m0-followups.md` (12개 항목)

### 4. Milestone 1 (Knowledge Base / RAG 파이프라인) 구현 완료

**백엔드 — RAG 파이프라인 전체 구축**:
- 파일 파서 모듈: 15개 확장자 지원 (txt/md/mdx/html/htm/xml/vtt/properties/pdf/docx/pptx/xlsx/csv/epub/eml)
- 임베딩 Provider 추상화: 로컬 HF 기본값(Snowflake Arctic Embed L v2.0 Korean, 1024차원) + fastembed fallback
- 청킹 파이프라인: RecursiveCharacterTextSplitter 기반, 백그라운드 asyncio 작업 + SSE 진행률 스트리밍
- Qdrant 벡터 DB 연동: 컬렉션 자동 생성(ensure_collection), upsert, 문서별 삭제, 시맨틱 검색(query_points)
- 지식베이스 CRUD API, 문서 업로드/목록/검색 엔드포인트

**프론트엔드 — 지식 탭 UI**:
- 지식베이스 생성/목록 페이지 + 상세 페이지(Clay 디자인 토큰 적용)
- 드래그앤드롭 파일 업로드 + SSE 실시간 진행률 바 + 2초 폴링 fallback
- 시맨틱 검색 테스트 UI (쿼리 입력 → 유사 청크 결과 표시)

**인프라 — Docker 환경 안정화**:
- Next.js rewrites 프록시(`/api/*` → `http://api:8000`) 적용으로 원격 접속 시 CORS/네트워크 문제 해결
- Dockerfile `ARG`/`ENV` 패턴 정립 (`NEXT_PUBLIC_*` 빌드 타임 변수)

### 5. 실사용 테스트 및 버그 수정 (04-10)

**E2E 테스트를 통한 9건 이슈 발견 및 수정**:
- Next.js 빌드 타입 에러 수정, Tailwind 시맨틱 토큰 누락 추가
- Dockerfile `NEXT_PUBLIC_API_URL` ARG 누락 → 빌드 타임 주입 패턴 정립
- 원격 브라우저 → localhost 연결 불가 → Next.js rewrite 프록시 도입
- 중복 KB 이름 생성 시 500 → IntegrityError 캐치하여 409 응답 처리
- Qdrant 컬렉션 미존재 시 404 → ensure_collection 자동 생성 로직 추가
- SSE 스트림 원격 동작 불가 → 프록시 경유 + 폴링 fallback 구현
- qdrant-client 1.17 API 변경 대응 (search() → query_points() 마이그레이션)
- 한국어 임베딩 시맨틱 검색 정상 동작 확인 (score 0.62)

### 6. UX 개선 (04-10)

- 업로드 영역에 **지원 파일 형식**(15종)과 **최대 업로드 크기**(50MB) 안내 표시
- 업로드 시 **클라이언트 사이드 파일 크기 사전 검증** + 서버 413 응답 처리
- RAG 처리 완료 문서의 **청크 미리보기 기능** 추가 (Qdrant scroll API로 상위 3개 청크 텍스트 표시)
- `GET /knowledge/config` 엔드포인트 추가 (프론트에서 동적으로 설정 로드)
- `GET /knowledge/{kb_id}/documents/{doc_id}/chunks` 엔드포인트 추가

## 다음 예정 작업

### Milestone 2 — 외부 MCP 도구 등록 시스템 (STDIO / HTTP-SSE)
### 이후 Milestone
- **M3**: 워크플로우 캔버스 (React Flow 기반 노드 에디터)
- **M4**: 워크플로우 실행 엔진 (LangGraph 컴파일러 + 실시간 로깅)
- **M5**: 통합 테스트 및 다듬기
