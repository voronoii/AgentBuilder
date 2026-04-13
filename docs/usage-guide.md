# AgentBuilder 사용 가이드

단계별로 AgentBuilder의 주요 기능을 안내합니다.

---

## 목차

1. [시작하기](#1-시작하기)
2. [LLM 프로바이더 설정](#2-llm-프로바이더-설정)
3. [지식베이스 만들기](#3-지식베이스-만들기)
4. [MCP 도구 등록](#4-mcp-도구-등록)
5. [워크플로우 만들기](#5-워크플로우-만들기)
6. [워크플로우 실행](#6-워크플로우-실행)
7. [데모 워크플로우](#7-데모-워크플로우)

---

## 1. 시작하기

### Docker Compose로 실행

```bash
# 저장소 클론 후 프로젝트 디렉터리로 이동
cd AgentBuilder

# 환경 변수 파일 준비
cp .env.example .env

# 서비스 시작
docker compose up -d
```

첫 실행 시 도커 이미지 빌드와 DB 마이그레이션이 자동으로 진행됩니다. 약 2–3분 후 아래 주소로 접속할 수 있습니다.

| 서비스 | URL |
|--------|-----|
| 웹 UI | http://localhost:23000 |
| API 문서 (Swagger) | http://localhost:28000/docs |

### 서비스 상태 확인

```bash
docker compose ps
```

모든 서비스(`postgres`, `qdrant`, `api`, `web`)가 `running` 상태여야 합니다. API 컨테이너가 `healthy` 상태가 된 뒤 web 컨테이너가 시작됩니다.

### 문제 해결

```bash
# 백엔드 로그 확인
docker compose logs -f api

# 프론트엔드 로그 확인
docker compose logs -f web

# 모든 서비스 재시작
docker compose restart
```

---

## 2. LLM 프로바이더 설정

Language Model 노드와 Agent 노드를 사용하려면 LLM 프로바이더 API 키를 등록해야 합니다.

### 설정 방법

1. 상단 내비게이션에서 **환경변수** 탭을 클릭합니다.
2. **+ 추가** 버튼을 클릭합니다.
3. 아래 표를 참고해 프로바이더별 키 이름과 값을 입력합니다.
4. **저장** 버튼을 클릭합니다.

| 프로바이더 | 설정 키 예시 | 비고 |
|------------|-------------|------|
| OpenAI | `OPENAI_API_KEY` | https://platform.openai.com/api-keys |
| Anthropic | `ANTHROPIC_API_KEY` | https://console.anthropic.com |
| OpenRouter | `OPENROUTER_API_KEY` | https://openrouter.ai/keys — 무료 모델 이용 가능 |

> `.env` 파일에 `OPENAI_API_KEY`나 `ANTHROPIC_API_KEY`를 직접 입력하고 `docker compose up -d`를 다시 실행해도 됩니다.

### OpenRouter 사용 팁

OpenRouter는 OpenAI API 호환 엔드포인트를 제공하며, `meta-llama/llama-4-scout:free` 같은 무료 모델도 제공합니다. API 키 없이도 일부 모델을 테스트할 수 있습니다.

---

## 3. 지식베이스 만들기

지식베이스는 RAG(검색 증강 생성)의 핵심입니다. 문서를 업로드하면 자동으로 청킹·임베딩되어 Qdrant 벡터 DB에 저장됩니다.

### 지식베이스 생성

1. 상단 내비게이션에서 **지식** 탭을 클릭합니다.
2. **+ 새 지식베이스** 버튼을 클릭합니다.
3. 이름과 설명을 입력하고 **생성**을 클릭합니다.

### 문서 업로드

1. 생성된 지식베이스 카드를 클릭해 상세 화면으로 이동합니다.
2. **문서 업로드** 버튼을 클릭하고 파일을 선택합니다.

지원 파일 형식:

| 형식 | 확장자 |
|------|--------|
| PDF | `.pdf` |
| Word | `.docx` |
| PowerPoint | `.pptx` |
| Excel | `.xlsx` |
| EPUB | `.epub` |
| 웹 페이지 | `.html` |
| 텍스트 | `.txt`, `.md` |

3. 업로드 후 **처리 중** 상태가 표시됩니다. 임베딩이 완료되면 **완료** 상태로 바뀝니다.

### 검색 테스트

문서 업로드 후 지식베이스가 제대로 작동하는지 바로 확인할 수 있습니다.

1. 지식베이스 상세 화면에서 **검색 테스트** 패널을 찾습니다.
2. 검색어를 입력하고 **검색** 버튼을 클릭합니다.
3. 유사도 스코어와 함께 관련 문서 청크가 표시됩니다.

---

## 4. MCP 도구 등록

MCP(Model Context Protocol) 서버를 등록하면 에이전트가 외부 도구(파일 시스템, 웹 검색, 데이터베이스 등)를 사용할 수 있습니다.

### MCP 서버 등록

1. 상단 내비게이션에서 **도구** 탭을 클릭합니다.
2. **+ MCP 서버 추가** 버튼을 클릭합니다.
3. 서버 정보를 입력합니다.

### 연결 방식별 설정

#### STDIO

로컬에서 실행 중인 MCP 서버에 표준 입출력으로 연결합니다.

| 항목 | 예시 |
|------|------|
| 이름 | `filesystem` |
| 명령어 | `npx` |
| 인수 | `-y @modelcontextprotocol/server-filesystem /home/user/docs` |

#### HTTP-SSE

원격 또는 로컬 HTTP 서버에 Server-Sent Events 방식으로 연결합니다.

| 항목 | 예시 |
|------|------|
| 이름 | `my-server` |
| URL | `http://localhost:8080/sse` |

#### Streamable HTTP

최신 MCP 스펙의 Streamable HTTP 방식으로 연결합니다.

| 항목 | 예시 |
|------|------|
| 이름 | `my-server` |
| URL | `http://localhost:8080/mcp` |

### 도구 확인

서버 등록 후 **연결 테스트** 버튼을 클릭하면 해당 서버가 노출하는 도구 목록이 표시됩니다. 등록된 도구는 이후 **Agent 노드**의 TOOLS 슬롯에서 선택할 수 있습니다.

---

## 5. 워크플로우 만들기

### 워크플로우 생성

1. 상단 내비게이션에서 **워크플로우** 탭을 클릭합니다.
2. **+ 새 워크플로우** 버튼을 클릭합니다.
3. 이름과 설명을 입력하고 **생성**을 클릭합니다.
4. 워크플로우 카드를 클릭하면 캔버스 에디터가 열립니다.

### 캔버스 에디터 구성

```
┌──┬──────────────────────────────────────────────┐
│📦│                                               │
│🔌│         React Flow Canvas                     │
│  │         (노드 + 엣지)                          │
│  │                                               │
└──┴──────────────────────────────────────────────┘
  ↑
  └─ 좌측 수직 사이드바
     📦 컴포넌트 탭 — 추가 가능한 노드 목록
     🔌 MCP 탭     — 등록된 MCP 서버 목록
```

### 노드 추가

1. 좌측 사이드바에서 **컴포넌트** 탭을 선택합니다.
2. 원하는 노드 타입을 클릭하면 캔버스에 즉시 추가됩니다.
   - 여러 번 클릭하면 자동으로 위치가 조금씩 어긋나 쌓입니다.
3. 노드를 드래그해 원하는 위치로 이동합니다.

### 노드 연결

1. 소스 노드의 오른쪽 **출력 핸들**(원형 점)에서 마우스를 눌러 드래그합니다.
2. 타겟 노드의 왼쪽 **입력 핸들**로 드롭하면 엣지(연결선)가 생성됩니다.
3. 연결선 가운데의 **✕ 버튼**을 클릭하면 엣지를 삭제할 수 있습니다.

### 노드 설정

1. 캔버스에서 노드를 클릭하면 오른쪽에 **설정 패널**이 열립니다.
2. 노드 타입별 설정 항목:

| 노드 | 주요 설정 항목 |
|------|--------------|
| Chat Input | Placeholder 텍스트 |
| Chat Output | (설정 없음) |
| Language Model | Provider, Model, Temperature, Max Tokens, System Message |
| Agent | Strategy, Provider, Model, System Prompt, Max Iterations, Knowledge Base, Tools |
| Knowledge Base | 지식베이스 선택, Top K, Score Threshold |
| Prompt Template | 템플릿 텍스트 (`{변수명}` 문법) |

### 자동 저장

노드·엣지 변경 시 1.5초 디바운스로 자동 저장됩니다. 상단의 **저장** 버튼으로 즉시 저장할 수도 있습니다.

### 노드 삭제

노드를 선택(클릭)한 후 `Delete` 또는 `Backspace` 키를 누르면 삭제됩니다.

---

## 6. 워크플로우 실행

### Playground에서 대화

1. 캔버스 에디터 상단의 **Playground** 버튼을 클릭합니다.
2. 하단의 입력창에 메시지를 입력하고 전송합니다.
3. 워크플로우가 실행되며 응답이 스트리밍으로 표시됩니다.

### 실행 로그 확인

좌측 사이드바에서 **실행 로그** 탭(📊)을 선택하면 현재 실행 중인 워크플로우의 단계별 로그를 실시간으로 확인할 수 있습니다.

| 로그 항목 | 설명 |
|-----------|------|
| 노드 이름 | 현재 실행 중인 노드 |
| 실행 시간 | 각 노드의 소요 시간 |
| 입출력 | 노드별 입력값과 출력값 |
| 에러 | 실패 시 오류 메시지 |

### Agent 노드 실행 중 동작

Agent 노드(ReAct 에이전트)는 LLM이 도구 호출 여부를 스스로 결정합니다.

- **MCP 도구 호출**: Agent가 필요하다고 판단하면 등록된 MCP 서버의 도구를 자동으로 호출합니다.
- **지식베이스 검색**: 설정 패널에서 선택된 지식베이스는 `search_kb_{이름}` 도구로 변환되어 에이전트가 자율적으로 검색합니다.
- **반복 제한**: 무한 루프를 방지하기 위해 Max Iterations(기본값 10) 내에서 실행을 마칩니다.

---

## 7. 데모 워크플로우

AgentBuilder에는 즉시 실행해볼 수 있는 데모 워크플로우가 포함되어 있습니다.

### 시드 데이터 로드

```bash
# API 컨테이너에서 시드 스크립트 실행
docker compose exec api python -m app.seed
```

또는 API 엔드포인트로 직접 실행:

```bash
curl -X POST http://localhost:28000/api/seed
```

### 데모 1: 단순 Q&A 챗봇

**구성**: `Chat Input → LLM → Chat Output`

가장 기본적인 워크플로우입니다. Language Model 노드 하나만으로 사용자 질문에 답변합니다.

- **LLM 설정**: OpenRouter의 `meta-llama/llama-4-scout:free` 모델 (무료)
- **System Message**: "당신은 친절하고 도움이 되는 AI 어시스턴트입니다."

**실행 방법**:
1. **워크플로우** 탭에서 `단순 Q&A 챗봇` 워크플로우를 클릭합니다.
2. **Playground** 버튼을 클릭합니다.
3. 질문을 입력하고 전송합니다.

### 데모 2: RAG 지식베이스 챗봇

**구성**: `Chat Input → Knowledge Base → Prompt Template → LLM → Chat Output`

문서에서 관련 내용을 검색한 뒤 그 내용을 바탕으로 답변하는 워크플로우입니다.

- **Knowledge Base 노드**: 미리 생성된 지식베이스를 참조 (시드 실행 시 자동 생성)
- **Prompt Template**: 검색 결과를 `{search_results}`로 주입
- **LLM**: 검색된 문서를 근거로 답변 생성

**실행 방법**:
1. **워크플로우** 탭에서 `RAG 지식베이스 챗봇` 워크플로우를 클릭합니다.
2. **Playground** 버튼을 클릭합니다.
3. 지식베이스에 포함된 내용과 관련된 질문을 입력합니다.
4. 좌측 **실행 로그** 탭에서 Knowledge Base 노드의 검색 결과도 확인할 수 있습니다.

---

## 추가 참고

- [API 문서](http://localhost:28000/docs) — Swagger UI에서 모든 API 엔드포인트 확인
- [설계 명세서](specs/2026-04-08-agentbuilder-design.md) — MVP 전체 설계 문서
- [README](../README.md) — 설치 및 아키텍처 개요
