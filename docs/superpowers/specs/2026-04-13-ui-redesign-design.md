# AgentBuilder UI Redesign — Design Spec

**작성일**: 2026-04-13
**상태**: Approved (브레인스토밍 완료)
**목적**: AgentBuilder 프론트엔드 UI를 상업용 에이전트 빌더 플랫폼 수준으로 리디자인

---

## 1. 목표 & 원칙

### 1.1 목표

현재 "AI가 만들어준 프로토타입" 수준의 UI를 Dify 수준의 **상업용 에이전트 빌더 플랫폼** 품질로 올린다.

### 1.2 벤치마크

- **Dify** — 주요 벤치마크. 깔끔한 미니멀 디자인, 노드 에디터 완성도
- Clay 디자인 시스템(getdesign.md) — 디자인 토큰 레퍼런스

### 1.3 핵심 원칙

1. **Clay 톤 유지** — cream/matcha/oat 팔레트를 유지하되 품질만 올림
2. **이모지 제거** — 전체 이모지를 Lucide SVG 아이콘으로 교체
3. **shadcn/ui 도입** — 폼, 모달, 드롭다운 등 기반 컴포넌트 품질 향상
4. **전체 리디자인** — TopNav, 워크플로우 에디터, 지식, 도구, 설정 모든 페이지

---

## 2. 신규 의존성

| 패키지 | 용도 | 상태 |
|--------|------|------|
| `shadcn/ui` | Button, Input, Select, Dialog, Dropdown, Tabs, Tooltip 등 | 추가 |
| `lucide-react` | 전체 아이콘 시스템 (이모지 대체) | 추가 |
| `class-variance-authority` | shadcn 컴포넌트 variant 관리 | 추가 |
| `clsx` + `tailwind-merge` | 조건부 클래스 유틸리티 | 추가 |

### 2.1 기존 의존성

- Tailwind CSS, ReactFlow, Zustand, react-markdown — 모두 유지
- Clay 디자인 토큰 (tailwind.config.ts) — 유지 + elevation/radius 보강

---

## 3. 디자인 토큰 보강

현재 tailwind.config.ts의 Clay 토큰을 유지하면서 다음을 추가:

### 3.1 Elevation (Clay 디자인 시스템 PDF 기반)

```
shadow-clay-0: none                          // Level 0: Flat
shadow-clay-1: 0 1px 3px rgba(0,0,0,0.06)    // Level 1: Clay (기본)
shadow-clay-2: 0 4px 12px rgba(0,0,0,0.08)   // Level 2: Hover/Hard
shadow-clay-focus: 0 0 0 2px rgba(7,138,82,0.15) // Focus ring
```

### 3.2 Border Radius (Clay PDF 기반)

기존 `rounded-card`(12px), `rounded-feature`(24px), `rounded-section`(40px) 유지.

---

## 4. TopNav 리디자인

### 4.1 변경 사항

| 요소 | 현재 | 변경 |
|------|------|------|
| 로고 | "AgentBuilder" 텍스트만 | matcha 컬러 사각 아이콘 + 텍스트 |
| 탭 | 텍스트 링크만 | Lucide 아이콘 + 텍스트 라벨 |
| Active 표시 | hover 색상 변경만 | matcha 하단 바 인디케이터 + font-weight 600 |
| "환경변수" 탭 | "환경변수" | "설정"으로 간소화 |

### 4.2 탭별 아이콘

| 탭 | Lucide 아이콘 |
|-----|-------------|
| 지식 | `BookOpen` |
| 워크플로우 | `Workflow` |
| 도구 | `Wrench` |
| 설정 | `Settings` |

---

## 5. 아이콘 매핑 (이모지 → Lucide)

전체 프로젝트에서 이모지를 Lucide 아이콘으로 교체한다.

### 5.1 노드 아이콘

| 노드 타입 | 현재 | Lucide |
|-----------|------|--------|
| Chat Input | 💬 | `MessageSquare` |
| Chat Output | 📤 | `MessageSquareShare` |
| Language Model | 🧠 | `Cpu` |
| Agent | 🤖 | `Bot` |
| Knowledge Base | 📚 | `BookOpen` |
| Prompt Template | 📝 | `FileText` |

### 5.2 UI 아이콘

| 위치 | 현재 | Lucide |
|------|------|--------|
| 저장 버튼 | 💾 | `Save` |
| 새로고침 | 🔄 | `RefreshCw` |
| 컴포넌트 패널 | 📦 | `LayoutGrid` |
| MCP 패널 | 🔌 | `Plug` |
| 실행로그 | 📊 | `Activity` |
| 플레이그라운드 | ▶ | `Play` |
| MCP STDIO | 📦 | `Terminal` |
| MCP HTTP | 🌐 | `Globe` |
| MCP SSE | ⚡ | `Zap` |
| 노드 시작 이벤트 | ▶ | `Play` |
| 노드 완료 이벤트 | ✓ | `Check` |
| 에러 이벤트 | ❌ | `AlertCircle` |
| 도구 호출 이벤트 | 🔧 | `Wrench` |

---

## 6. 워크플로우 에디터

### 6.1 툴바 리디자인

| 요소 | 현재 | 변경 |
|------|------|------|
| 버튼 스타일 | 이모지 + 텍스트 | Lucide 아이콘 + 텍스트 라벨 |
| 플레이그라운드 버튼 | 항상 녹색, 이모지 | "실행" 버튼, matcha outline 스타일 |
| 그룹 구분 | 없음 | 수직 divider (1px oat) |
| Active 상태 | clayBlack 배경 + white 텍스트 | 동일 유지 |

### 6.2 노드 디자인 (Approach B: Thin Border + Color Dot)

**핵심 변경:** 두꺼운 컬러 테두리를 제거하고, 1px oat 테두리 + 8px 컬러 도트로 교체.

| 요소 | 현재 | 변경 |
|------|------|------|
| 테두리 | `border-2` (2px, 노드별 컬러) | `border` (1px, `#dad4c8` oat 통일) |
| 타입 표시 | 컬러 배경 + 컬러 테두리 | 헤더 왼쪽 8px 컬러 도트 |
| 아이콘 | 이모지 | Lucide SVG (warmSilver `#9f9b93`) |
| 헤더/바디 구분 | 없음 (단일 영역) | 1px `#eee9df` 구분선 |
| 필드 프리뷰 | 없음 | 주요 설정값 미리보기 (label + value) |
| 선택 상태 | `ring-2 ring-blue-400` | `border-color: #078a52` + matcha shadow ring |
| 그림자 | shadow-clay | shadow-clay-1 (`0 1px 3px rgba(0,0,0,0.04)`) |
| Handle (포트) | oat 배경 + oat 테두리 | 동일 유지 |
| 배경 | 노드별 컬러 배경 (bg-cyan-50 등) | `#fff` 흰색 통일 |

### 6.3 노드 타입별 컬러 도트

| 노드 타입 | 도트 색상 | Hex |
|-----------|----------|-----|
| Chat Input / Output | rose | `#f43f5e` |
| Language Model | cyan | `#06b6d4` |
| Agent | purple | `#8b5cf6` |
| Knowledge Base | green (matcha) | `#078a52` |
| Prompt Template | amber | `#d97706` |

### 6.4 노드 설정 패널 (NodeConfigPanel)

| 요소 | 현재 | 변경 |
|------|------|------|
| 헤더 | 컬러 아이콘 + 컬러 라벨 | 컬러 도트 + 흰색 제목 (노드와 일관) |
| 폼 컴포넌트 | 순수 Tailwind input | shadcn/ui Input, Select, Textarea |
| Label 스타일 | text-xs | uppercase + letter-spacing |
| 패널 너비 | 288px | 320px |
| 패널 배경 | clay-surface | 유지 |

### 6.5 플레이그라운드 패널 (PlaygroundPanel)

| 요소 | 현재 | 변경 |
|------|------|------|
| 사용자 메시지 배경 | `bg-blue-600` | `bg-clayBlack (#000)` |
| 어시스턴트 메시지 | cream 배경 + oat 테두리 | 유지 |
| 전송 버튼 | `bg-green-600` 텍스트 "전송" | matcha 배경 + Lucide `Send` 아이콘 |
| 헤더 | "▶ 플레이그라운드" | Lucide `Play` 아이콘 + "플레이그라운드" |
| 노드 이벤트 로그 | 이모지 (▶/✓/💬/🔧) | Lucide (Play/Check/MessageSquare/Wrench) |
| 패널 너비 | 384px | 유지 |

### 6.6 사이드바 (Sidebar)

| 요소 | 변경 |
|------|------|
| 컴포넌트 패널 | 노드 타입별 클릭 버튼에 Lucide 아이콘 + 컬러 도트 적용 |
| MCP 패널 | 도구 이름/설명/서버 레이아웃 유지, 이모지만 교체 |
| 실행로그 패널 | 이모지 → Lucide 아이콘, 상태 badge 스타일 통일 |

### 6.7 실행로그 패널 (RunLogPanel)

| 요소 | 현재 | 변경 |
|------|------|------|
| 이벤트 아이콘 | 이모지 (▶/✓/💬/🔧/📋/✅/❌) | Lucide SVG |
| 상태 badge | 컬러 텍스트 | shadcn Badge 컴포넌트 |
| 새로고침 아이콘 | 🔄 | Lucide `RefreshCw` |

---

## 7. 지식 페이지

### 7.1 목록 (KbList)

| 요소 | 현재 | 변경 |
|------|------|------|
| 카드 상단 | 이름만 | 아이콘 뱃지 (matcha 배경 BookOpen) + 이름 |
| 카드 메타 | embedding provider + dimension | 파일 수 + 청크 수 (Lucide 아이콘 포함) |
| 카드 액션 | 없음 (카드 클릭으로 이동) | 편집/삭제 버튼 하단 분리 |
| 빈 상태 | dashed border + 텍스트 | Lucide Plus 아이콘 + 설명 + CTA |
| 버튼 스타일 | `rounded-full bg-clay-accent` pill | `rounded-lg` 사각 버튼 (Clay 체계) |

### 7.2 KB 상세 (IngestionProgress + SearchPanel)

| 요소 | 변경 |
|------|------|
| 업로드 드롭존 | Lucide `Upload` 아이콘으로 교체, "파일 선택" 버튼 shadcn Button |
| 진행률 바 | 유지 (matcha 컬러 이미 적용됨) |
| 검색 패널 | 입력 + 버튼을 shadcn Input + Button으로 교체 |
| 결과 카드 | 유지 (구조 양호), 유사도 점수 badge 스타일만 개선 |

### 7.3 생성 폼 (CreateKbForm)

| 요소 | 변경 |
|------|------|
| 입력 필드 | shadcn Input, Textarea로 교체 |
| 고급 설정 토글 | shadcn Collapsible 또는 Accordion |
| 제출 버튼 | `rounded-full` → `rounded-lg` 사각 |

---

## 8. 도구 페이지

### 8.1 서버 목록 (McpServerList)

| 요소 | 현재 | 변경 |
|------|------|------|
| 제목 | "도구 (MCP 서버)" | "도구", 설명은 subtitle로 분리 |
| Transport 아이콘 | 이모지 (📦/🌐/⚡) | Lucide (Terminal/Globe/Zap) |
| 상태 표시 | green/gray pill 텍스트 | shadcn Badge (Active: matcha, Inactive: warmSilver) |
| 도구 카드 | 단순 테두리 카드 | oat 배경 태그 칩으로 변경 |
| 버튼 | 한글 텍스트 버튼 | shadcn Button (outline variant) |

### 8.2 등록 모달 (RegisterMcpModal)

| 요소 | 현재 | 변경 |
|------|------|------|
| 모달 | 커스텀 fixed overlay | shadcn Dialog |
| Transport 탭 | 커스텀 segmented control | shadcn Tabs |
| 입력 필드 | 커스텀 input | shadcn Input, Textarea |
| 버튼 | 커스텀 스타일 | shadcn Button (ghost + primary) |

---

## 9. 설정 페이지

| 요소 | 현재 | 변경 |
|------|------|------|
| 탭 이름 | "환경변수" | "설정" |
| 그룹 아이콘 | 이모지 (🔑/🌐/⚙️) | Lucide (Lock/Globe/Settings) |
| 그룹 라벨 | 일반 텍스트 | uppercase + letter-spacing |
| 설정 행 | 2-line 레이아웃 | compact 1-line, 키+값+액션 일렬 |
| 추가 폼 | dashed border 인라인 확장 | shadcn Dialog 모달 |
| SECRET badge | pomegranate 텍스트 | 소형 pill badge (`bg-red-50 text-red-500`) |
| 편집/삭제 | 커스텀 버튼 | shadcn Button (outline + destructive) |

---

## 10. 공통 컴포넌트 패턴

### 10.1 페이지 헤더

모든 목록 페이지(지식, 워크플로우, 도구, 설정)에 통일된 헤더:

```
[제목]
[설명 subtitle]                              [+ 액션 버튼]
```

- 제목: text-lg font-bold
- 설명: text-sm text-warmSilver
- 액션 버튼: shadcn Button (matcha primary)

### 10.2 카드

모든 카드에 통일된 패턴:

- 배경: `#fff`
- 테두리: 1px `#dad4c8`
- 둥글기: `rounded-card` (12px)
- Hover: `border-color: #078a52`, `shadow-clay-2`
- 구조: 아이콘 뱃지 + 제목 / 설명 / 메타 / 액션 (구분선)

### 10.3 빈 상태

모든 빈 목록에 통일된 패턴:

- dashed border 컨테이너
- Lucide 아이콘 (40px, `#dad4c8`)
- 제목 (font-semibold)
- 설명 (text-sm text-warmSilver)

---

## 11. 범위 외 (변경하지 않는 것)

| 항목 | 이유 |
|------|------|
| ReactFlow 캔버스 기본 동작 | 라이브러리 기본값 유지 |
| 캔버스 배경 (dot grid) | 현재 스타일 양호 |
| Zustand 상태 관리 구조 | 기능 변경 아님, UI만 리디자인 |
| API 통신 레이어 (lib/) | 변경 불필요 |
| 라우팅 구조 | 유지 ("환경변수" → "설정" URL만 변경) |
| 반응형 breakpoint | 현재 sm/lg 구조 유지 |

---

## 12. 구현 전략

### 12.1 순서

1. **기반 셋업** — shadcn/ui 초기화, Lucide 설치, 디자인 토큰 보강
2. **공통 컴포넌트** — 페이지 헤더, 카드, 빈 상태 패턴
3. **TopNav** — 아이콘 + active 인디케이터
4. **워크플로우 에디터** — 노드(BaseNode + nodeStyles), 툴바, 사이드바, 설정 패널, 플레이그라운드
5. **지식 페이지** — 목록, 생성 폼, 상세
6. **도구 페이지** — 서버 목록, 등록 모달, 도구 카탈로그
7. **설정 페이지** — 그룹 레이아웃, 행 스타일, 추가/편집 모달

### 12.2 영향 파일 목록

| 파일 | 변경 유형 |
|------|----------|
| `tailwind.config.ts` | 토큰 보강 (elevation, radius) |
| `components/ui/*` | 신규 (shadcn 컴포넌트) |
| `components/nav/TopNav.tsx` | 리디자인 |
| `components/workflow/WorkflowEditor.tsx` | 툴바 리디자인 |
| `components/workflow/Sidebar.tsx` | 아이콘 교체, 스타일 개선 |
| `components/workflow/nodes/BaseNode.tsx` | 노드 디자인 변경 |
| `components/workflow/nodes/nodeStyles.ts` | 컬러 도트 체계로 변경 |
| `components/workflow/NodeConfigPanel.tsx` | shadcn 폼 + 도트 헤더 |
| `components/workflow/PlaygroundPanel.tsx` | 메시지 색상, 아이콘 교체 |
| `components/workflow/RunLogPanel.tsx` | 이모지 → Lucide, badge |
| `components/knowledge/KbList.tsx` | 카드 리디자인 |
| `components/knowledge/CreateKbForm.tsx` | shadcn 폼 |
| `components/knowledge/IngestionProgress.tsx` | 아이콘 교체 |
| `components/knowledge/FileUpload.tsx` | 아이콘 교체 |
| `components/knowledge/SearchPanel.tsx` | shadcn 입력 |
| `components/mcp/McpServerList.tsx` | 카드 리디자인 |
| `components/mcp/RegisterMcpModal.tsx` | shadcn Dialog + Tabs |
| `components/mcp/ToolCatalog.tsx` | 태그 칩 스타일 |
| `components/settings/SettingsPage.tsx` | 전체 리디자인 |
| `app/layout.tsx` | 미세 조정 |
| `app/tools/page.tsx` | 제목 변경 |
| `app/settings/page.tsx` | URL/제목 변경 |
| `components/workflow/WorkflowList.tsx` | 카드 + 버튼 스타일 |
