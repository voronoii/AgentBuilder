'use client';

import { useEffect, useRef, useState } from 'react';
import { flushSync } from 'react-dom';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Play, Send, Search, Wrench, Loader2, Check } from 'lucide-react';

import { apiBase } from '@/lib/api';
import { validateWorkflow } from '@/lib/workflow';
import { useWorkflowStore } from '@/stores/workflowStore';

interface RunEvent {
  event_type: string;
  node_id?: string;
  payload?: Record<string, unknown>;
  data?: unknown;
  token?: string;
}

type ToolStepStatus = 'running' | 'done' | 'error';
interface ToolStep {
  name: string;
  status: ToolStepStatus;
  startedAt: number;
  endedAt?: number;
  input?: unknown;       // tool_call.input — ReasoningTrail에서 펼치기 표시용
  output?: string;       // tool_result.output — 펼치기 시 raw text
}

// Agent의 LLM 추론 thought (도구 호출 직전 reasoning 텍스트)
interface AgentThought {
  id: string;
  content: string;
  toolNames: string[];   // 이 thought 직후 호출되는 도구 목록 (UI 미리보기용)
  createdAt: number;
}

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  isStreaming?: boolean;
  steps?: ToolStep[];
  thoughts?: AgentThought[]; // LLM의 도구 호출 직전 reasoning 카드 stack
  postToolPause?: boolean;
  startedAt?: number;       // 어시스턴트 메시지가 시작된 시각 (ms)
  lastErrorAt?: number;     // 직전 tool 에러 발생 시각 — 재시도 인디케이터용
  llmInferring?: boolean;   // LLM 추론 진행 중 (on_chat_model_start ~ on_chat_model_end)
  llmCallCount?: number;    // 지금까지 시작된 LLM 호출 수 (첫 호출 / 후속 호출 구분용)
  lastToolStatus?: 'success' | 'error' | null; // 직전 도구 호출 결과 — 후속 LLM 추론 라벨에 사용
}

// 도구 이름에서 사람이 읽을 수 있는 진행/완료 카피를 만들어내는 엔진.
// raw 입력/출력은 노출하지 않음 — 채팅 UX 용도, 디버깅은 RunLogPanel.

type VerbKind = 'kb' | 'search' | 'fetch' | 'analyze' | 'count' | 'summarize' | 'create' | 'update' | 'delete' | 'send' | 'list' | 'tool';

interface VerbDef {
  tokens: string[];
  running: string; // "{목적어}을(를) {running}"
  done: string;    // "{목적어} {done}"
  kind: VerbKind;
}

// 우선순위가 위에서 아래로 — 더 구체적인 동사를 먼저 두기.
const VERB_DEFS: VerbDef[] = [
  { tokens: ['summarize', 'summary', '요약'], running: '요약하고 있어요', done: '요약 완료', kind: 'summarize' },
  { tokens: ['count', 'aggregate', 'sum', 'tally', '집계', '산출'], running: '산출하고 있어요', done: '산출 완료', kind: 'count' },
  { tokens: ['analyze', 'analysis', 'analytics', 'trend', 'trends', 'transition', 'transitions', 'distribution', 'breakdown', 'stats', 'statistics', 'compare', 'comparison', '분석', '추이'], running: '분석하고 있어요', done: '분석 완료', kind: 'analyze' },
  { tokens: ['search', 'find', 'query', 'lookup', '검색'], running: '검색하고 있어요', done: '검색 완료', kind: 'search' },
  { tokens: ['get', 'fetch', 'read', 'load', 'retrieve', 'collect', '조회', '가져오기'], running: '조회하고 있어요', done: '조회 완료', kind: 'fetch' },
  { tokens: ['list', 'enumerate', '목록'], running: '목록을 가져오고 있어요', done: '목록 조회 완료', kind: 'list' },
  { tokens: ['generate', 'create', 'write', 'draft', 'compose', 'render', 'build', '작성', '생성'], running: '작성하고 있어요', done: '작성 완료', kind: 'create' },
  { tokens: ['update', 'edit', 'modify', 'patch', 'change', '수정'], running: '수정하고 있어요', done: '수정 완료', kind: 'update' },
  { tokens: ['delete', 'remove', 'drop', '삭제'], running: '삭제하고 있어요', done: '삭제 완료', kind: 'delete' },
  { tokens: ['send', 'post', 'publish', 'submit', 'dispatch', '전송', '발송'], running: '전송하고 있어요', done: '전송 완료', kind: 'send' },
];

const VERB_TOKEN_INDEX: Map<string, VerbDef> = (() => {
  const m = new Map<string, VerbDef>();
  for (const def of VERB_DEFS) {
    for (const t of def.tokens) m.set(t.toLowerCase(), def);
  }
  return m;
})();

const TOKEN_KO: Record<string, string> = {
  // 일반
  news: '뉴스', article: '기사', articles: '기사', headline: '헤드라인', headlines: '헤드라인',
  app: '앱', apps: '앱', data: '데이터', dataset: '데이터셋',
  report: '리포트', reports: '리포트',
  log: '로그', logs: '로그', user: '사용자', users: '사용자', file: '파일', files: '파일',
  doc: '문서', docs: '문서', document: '문서', documents: '문서', image: '이미지', images: '이미지',
  calendar: '일정', event: '일정', events: '일정', mail: '메일', email: '메일', emails: '메일',
  message: '메시지', messages: '메시지', chat: '채팅', task: '작업', tasks: '작업',
  ticket: '티켓', issue: '이슈', issues: '이슈', pr: 'PR', commit: '커밋', repo: '저장소',
  product: '상품', order: '주문', orders: '주문', customer: '고객', invoice: '인보이스',
  weather: '날씨', stock: '주식', price: '가격', web: '웹', page: '페이지', url: '링크',
  kb: '지식베이스', knowledge: '지식베이스', database: '데이터베이스', db: '데이터베이스',
  notion: 'Notion', slack: 'Slack', github: 'GitHub', gmail: 'Gmail', drive: '드라이브',
  sheet: '시트', sheets: '시트', table: '테이블',
  // 분석/지표
  keyword: '키워드', keywords: '키워드', topic: '토픽', topics: '토픽',
  buzz: '버즈', volume: '량', count: '건수', counts: '건수', total: '합계',
  trend: '추이', trends: '추이', transition: '추이', transitions: '추이',
  distribution: '분포', stats: '통계', statistics: '통계', summary: '요약',
  period: '기간', date: '날짜', range: '범위', source: '출처',
  sentiment: '감성', score: '점수',
};

const NOISE_TOKENS = new Set(['tool', 'mcp', 'api', 'v1', 'v2', 'fn', 'func', 'mcp_', 'the', 'a', 'an']);

function tokenize(name: string): string[] {
  return name
    .replace(/([a-z])([A-Z])/g, '$1 $2') // camelCase → 분리
    .replace(/([A-Z]+)([A-Z][a-z])/g, '$1 $2') // PASCALCase ABBR boundaries
    .split(/[_\-\s.]+/)
    .map((t) => t.trim())
    .filter(Boolean);
}

function findVerb(tokens: string[]): { def: VerbDef; matchedToken: string } | null {
  // 첫 번째로 매칭되는 동사 토큰을 사용. 정의 순서가 우선순위.
  // 토큰을 순회하며 verb index 조회.
  let best: { def: VerbDef; matchedToken: string; defOrder: number } | null = null;
  const orderOf = new Map<VerbDef, number>(VERB_DEFS.map((d, i) => [d, i] as [VerbDef, number]));
  for (const t of tokens) {
    const def = VERB_TOKEN_INDEX.get(t.toLowerCase());
    if (!def) continue;
    const order = orderOf.get(def) ?? 999;
    if (best === null || order < best.defOrder) {
      best = { def, matchedToken: t, defOrder: order };
    }
  }
  return best ? { def: best.def, matchedToken: best.matchedToken } : null;
}

function describeTool(name: string): { running: string; done: string; kind: VerbKind } {
  if (!name) return { running: '도구를 실행하고 있어요', done: '도구 실행 완료', kind: 'tool' };

  // KB 도구는 백엔드에서 `search_kb_<KB이름>` 형태로 구워서 보냄
  if (name.startsWith('search_kb_')) {
    const kbName = name.slice('search_kb_'.length).replace(/_+/g, ' ').trim();
    if (kbName) {
      return {
        running: `${kbName}에서 검색하고 있어요`,
        done: `${kbName} 검색 완료`,
        kind: 'kb',
      };
    }
    return { running: '지식베이스에서 검색하고 있어요', done: '지식베이스 검색 완료', kind: 'kb' };
  }

  const tokens = tokenize(name);
  const verb = findVerb(tokens);

  // 목적어 후보 = NOISE 제외 + 동사 토큰 처리
  // - 매칭된 동사 토큰: TOKEN_KO에 한국어 명사형이 있으면 목적어로 사용
  //   예: 'Transitions' → analyze 동사로 매칭됐지만 TOKEN_KO['transitions']='추이'라
  //       "키워드 추이를 분석" 형태가 됨
  // - 매칭되지 않은 다른 동사 토큰: 사전에 명사형이 있으면 사용, 없으면 제거
  //   예: 'Get' → fetch 동사이지만 TOKEN_KO['get']이 없어 제거
  const verbTokenLower = verb?.matchedToken.toLowerCase();
  const objectTokens = tokens.filter((t) => {
    const lo = t.toLowerCase();
    if (NOISE_TOKENS.has(lo)) return false;
    if (lo === verbTokenLower) return TOKEN_KO[lo] !== undefined;
    if (VERB_TOKEN_INDEX.has(lo)) return TOKEN_KO[lo] !== undefined;
    return true;
  });
  const objectKo = objectTokens
    .map((t) => TOKEN_KO[t.toLowerCase()] ?? t)
    .join(' ')
    .trim();

  if (verb) {
    const polished = objectKo ? `${objectKo}${hasJongseong(objectKo) ? '을' : '를'} ` : '';
    return {
      running: `${polished}${verb.def.running}`,
      done: objectKo ? `${objectKo} ${verb.def.done}` : verb.def.done,
      kind: verb.def.kind,
    };
  }

  const pretty = objectKo || tokens.join(' ');
  return {
    running: pretty ? `${pretty}${hasJongseong(pretty) ? '을' : '를'} 실행하고 있어요` : '도구를 실행하고 있어요',
    done: pretty ? `${pretty} 실행 완료` : '도구 실행 완료',
    kind: 'tool',
  };
}

function hasJongseong(s: string): boolean {
  if (!s) return false;
  const last = s.trim().slice(-1);
  const code = last.charCodeAt(0);
  if (code < 0xac00 || code > 0xd7a3) return false; // 한글 음절이 아니면 false
  return (code - 0xac00) % 28 !== 0;
}

function kindIcon(kind: string) {
  if (kind === 'kb' || kind === 'search' || kind === 'fetch' || kind === 'list') return Search;
  return Wrench;
}

// 도구가 매우 빠르게 끝날 때 사용자가 진행 라벨을 못 읽고 지나가는 문제를 막기 위해,
// 라벨 변화를 큐에 쌓고 minMs 간격으로 순차 표시. SSE 이벤트가 React 배칭 때문에
// 한 프레임에 압축돼도 중간 단계가 모두 한 번씩은 보임.
function now(): number {
  return typeof performance !== 'undefined' ? performance.now() : Date.now();
}

// 1Hz로 강제 리렌더 — 경과시간 카운터처럼 시간 기반 표시 갱신용.
function useTick(active: boolean, intervalMs: number = 1000): number {
  const [tick, setTick] = useState(0);
  useEffect(() => {
    if (!active) return;
    const id = setInterval(() => setTick((t) => t + 1), intervalMs);
    return () => clearInterval(id);
  }, [active, intervalMs]);
  return tick;
}

// running 단계가 한 번이라도 보였으면 그 라벨을 minMs 동안 유지.
// 큐 기반 안정화는 React 18 자동 배칭으로 인해 짧은 도구 호출에서 commit이
// 사라지는 문제가 있었다. 이 패턴은 단순히 "마지막 running 도구 + 만료시간"을
// state로 들고, 그 시간 안에는 라벨이 보이도록 보장한다.
interface PinnedTool {
  name: string;
  until: number;
  startedAt: number;  // running step의 startedAt — dependency 식별용
}

function usePinnedRunningTool(
  running: ToolStep | undefined,
  minMs: number = 1000,
): PinnedTool | null {
  const [pinned, setPinned] = useState<PinnedTool | null>(null);

  // 새 running 단계가 등장하면 표시 만료시간 갱신
  useEffect(() => {
    if (!running) return;
    setPinned({
      name: running.name,
      startedAt: running.startedAt,
      until: Date.now() + minMs,
    });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [running?.name, running?.startedAt, minMs]);

  // 만료시간이 지나면 자동으로 unpin
  useEffect(() => {
    if (!pinned) return;
    const remaining = pinned.until - Date.now();
    if (remaining <= 0) {
      setPinned(null);
      return;
    }
    const id = setTimeout(() => setPinned(null), remaining);
    return () => clearTimeout(id);
  }, [pinned]);

  return pinned;
}

// 가장 최근 thought를 라이브 라벨로 표시할 때 minMs 보장. thought 도착 직후
// 도구 호출이 시작되어도 그 시간 동안은 thought가 라벨에 머무른다.
interface PinnedThought {
  id: string;
  content: string;
  until: number;
}

function usePinnedThought(
  latest: AgentThought | null,
  minMs: number = 1500,
): PinnedThought | null {
  const [pinned, setPinned] = useState<PinnedThought | null>(null);

  useEffect(() => {
    if (!latest) return;
    setPinned({
      id: latest.id,
      content: latest.content,
      until: Date.now() + minMs,
    });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [latest?.id, minMs]);

  useEffect(() => {
    if (!pinned) return;
    const remaining = pinned.until - Date.now();
    if (remaining <= 0) {
      setPinned(null);
      return;
    }
    const id = setTimeout(() => setPinned(null), remaining);
    return () => clearTimeout(id);
  }, [pinned]);

  return pinned;
}

function formatElapsed(ms: number): string {
  const s = Math.max(0, Math.floor(ms / 1000));
  if (s < 60) return `${s}초`;
  const m = Math.floor(s / 60);
  const rem = s % 60;
  return rem === 0 ? `${m}분` : `${m}분 ${rem}초`;
}

// 도구 카드 한 장 — input/output을 펼쳐서 raw text로 보여줌. Dify 패턴 차용:
// JSON viewer 없이 단순 <pre> wrap, isFinished boolean 하나로 spinner↔check 토글.
function ToolCard({ step }: { step: ToolStep }) {
  const [expanded, setExpanded] = useState(false);
  const { done, kind } = describeTool(step.name);
  const Icon = kindIcon(kind);
  const isFinished = step.status === 'done';
  const isError = step.status === 'error';
  const hasDetail = step.input !== undefined || (step.output && step.output.length > 0);

  const toggle = () => {
    if (hasDetail) setExpanded((v) => !v);
  };

  const elapsed = step.endedAt && step.startedAt ? step.endedAt - step.startedAt : null;

  return (
    <div className={`rounded-md border text-[11px] ${isError ? 'border-amber-200 bg-amber-50' : 'border-clay-border bg-clay-surface'}`}>
      <button
        type="button"
        onClick={toggle}
        disabled={!hasDetail}
        className="flex w-full items-center gap-1.5 px-2 py-1 text-left disabled:cursor-default"
      >
        {isFinished ? (
          <Check className="h-3.5 w-3.5 flex-shrink-0 text-emerald-500" />
        ) : isError ? (
          <span className="text-amber-600">!</span>
        ) : (
          <Loader2 className="h-3.5 w-3.5 flex-shrink-0 animate-spin text-clay-accent" />
        )}
        <Icon className="h-3 w-3 flex-shrink-0 opacity-60" />
        <span className="flex-1 truncate text-clay-text">
          {isError ? `${done.replace(/ 완료$/, '')} 실패` : isFinished ? done : describeTool(step.name).running}
        </span>
        {elapsed !== null && (
          <span className="text-[10px] tabular-nums text-warmSilver">
            {(elapsed / 1000).toFixed(1)}s
          </span>
        )}
        {hasDetail && (
          <span className="text-warmSilver">{expanded ? '▾' : '▸'}</span>
        )}
      </button>
      {expanded && hasDetail && (
        <div className="border-t border-clay-border px-2 py-1.5 font-mono text-[10px] leading-snug">
          {step.input !== undefined && (
            <div className="mb-1.5">
              <div className="mb-0.5 font-semibold text-clay-text/70">Input</div>
              <pre className="whitespace-pre-wrap break-all rounded bg-white px-1.5 py-1 text-clay-text">
                {(() => {
                  try {
                    return JSON.stringify(step.input, null, 2);
                  } catch {
                    return String(step.input);
                  }
                })()}
              </pre>
            </div>
          )}
          {step.output && (
            <div>
              <div className="mb-0.5 font-semibold text-clay-text/70">Output</div>
              <pre className="whitespace-pre-wrap break-all rounded bg-white px-1.5 py-1 text-clay-text">
                {step.output.length > 1000 ? step.output.slice(0, 1000) + '\n…(생략)' : step.output}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function ToolSteps({
  steps,
  thoughts,
  isStreaming,
  hasContent,
  postToolPause,
  startedAt,
  lastErrorAt,
  llmInferring,
  llmCallCount,
  lastToolStatus,
}: {
  steps: ToolStep[];
  thoughts: AgentThought[];
  isStreaming?: boolean;
  hasContent: boolean;
  postToolPause: boolean;
  startedAt?: number;
  lastErrorAt?: number;
  llmInferring?: boolean;
  llmCallCount?: number;
  lastToolStatus?: 'success' | 'error' | null;
}) {
  const hasSteps = steps && steps.length > 0;
  const hasThoughts = thoughts && thoughts.length > 0;
  // 1초마다 리렌더해서 경과시간 갱신
  useTick(!!isStreaming && !hasContent, 1000);

  if (!hasSteps && !hasThoughts && !isStreaming) return null;

  const dim = hasContent;
  // ReasoningTrail 카드 — 도구는 진행중/성공/실패 모두 누적 표시 (사용자가
  // 실제 어떤 도구가 어떤 입력으로 호출됐는지 볼 수 있도록). 같은 도구가
  // 재시도되면 별도 카드로 stack.
  const running = steps.find((s) => s.status === 'running');
  const errorCount = steps.filter((s) => s.status === 'error').length;

  // 최근 30초 안에 에러가 있었으면 "재시도/방법 정리 중" 모드
  const recentError = lastErrorAt !== undefined && now() - lastErrorAt < 30000;

  // ── 라이브 라벨 결정 ──────────────────────────────────────────────────
  // running 단계가 한 번이라도 보였으면 그 라벨을 minMs(1000ms) 보장 표시.
  // 그 후엔 상황별 fallback. hasContent=true면 라벨 자동 소멸.
  const pinnedRunning = usePinnedRunningTool(running, 1000);
  // pinned 만료 후에도 정확히 unpin이 일어나도록 1초마다 강제 리렌더
  useTick(!!pinnedRunning, 250);

  // pinned가 살아있는 동안은 답변 진행 여부와 무관하게 라벨 유지.
  // 도구 호출이 매우 빠르게 끝나(<30ms) 곧장 답변 토큰 + workflow_end가 같은
  // batch로 도착하면, isStreaming/hasContent 조건만으로는 pinned가 즉시 무시되어
  // 라벨이 paint될 시간이 없다. pinned 만료(1초)까지는 무조건 표시.
  const showPinned = pinnedRunning && Date.now() < pinnedRunning.until;

  // ── 라이브 라벨 결정 ──────────────────────────────────────────────────
  // 우선순위:
  //   1) thought minMs(1.5초) 살아있음 → reasoning 텍스트 (도구 라벨보다 우선)
  //   2) 도구 실행 중 (running) → "X를 분석하고 있어요"
  //   3) 도구 직후 pinned 살아있음 → 같은 라벨 유지 (1초 보장)
  //   4) 그 외 → 일반 fallback
  // thought 우선이 핵심 — 그렇지 않으면 thought 도착 직후 tool_call이 같은
  // batch로 도착해 thought가 paint되기 전에 도구 라벨로 덮인다.
  const callCount = llmCallCount ?? 0;
  const lastThought = thoughts.length > 0 ? thoughts[thoughts.length - 1] : null;
  const pinnedThought = usePinnedThought(lastThought, 1500);
  useTick(!!pinnedThought, 250);
  const showThought = pinnedThought && Date.now() < pinnedThought.until && isStreaming && !hasContent;

  let stableLive: string | null = null;
  if (showThought) {
    stableLive = pinnedThought.content;
  } else if (running && isStreaming) {
    stableLive = describeTool(running.name).running;
  } else if (showPinned) {
    stableLive = describeTool(pinnedRunning.name).running;
  } else if (isStreaming && !hasContent) {
    if (llmInferring) {
      // LLM이 추론 중인 시점 — 호출 회차 + 직전 도구 결과를 보고 라벨 결정
      if (callCount <= 1) {
        stableLive = '질의를 분석하고 있어요';
      } else if (lastToolStatus === 'error') {
        if (errorCount >= 2) {
          stableLive = '다른 방법으로 다시 시도하고 있어요';
        } else {
          stableLive = '오류를 보고 호출 방식을 정리하고 있어요';
        }
      } else if (lastToolStatus === 'success') {
        stableLive = '결과를 정리하고 있어요';
      } else {
        stableLive = '다음 단계를 준비하고 있어요';
      }
    } else if (recentError && errorCount >= 2) {
      stableLive = '다른 방법으로 다시 시도하고 있어요';
    } else if (recentError) {
      stableLive = '오류를 보고 호출 방식을 정리하고 있어요';
    } else if (steps.some((s) => s.status === 'done' || s.status === 'error')) {
      stableLive = postToolPause ? '결과를 정리하고 있어요' : '다음 단계를 준비하고 있어요';
    } else if (!hasSteps) {
      stableLive = '요청을 분석하고 있어요';
    }
  }

  // 답변 영역 trail — 도구 카드만 stack (사용자가 호출된 도구 + input/output을
  // 펼쳐서 확인). thought는 라이브 라벨 자리에서만 흘러가게 하여 진행 중에 한
  // 곳에서 reasoning을 볼 수 있도록.
  const toolTrail = [...steps].sort((a, b) => a.startedAt - b.startedAt);

  if (!stableLive && toolTrail.length === 0) return null;

  // 경과시간 — 어시스턴트 메시지가 시작된 시점부터
  const elapsed = startedAt !== undefined ? now() - startedAt : 0;
  const elapsedText = elapsed > 1500 ? formatElapsed(elapsed) : null;

  return (
    <div className={`mb-1.5 flex flex-col gap-1.5 ${dim ? 'opacity-70' : ''}`}>
      {toolTrail.length > 0 && (
        <div className="flex flex-col gap-1">
          {toolTrail.map((step, i) => (
            <ToolCard key={`tool-${i}-${step.name}-${step.startedAt}`} step={step} />
          ))}
        </div>
      )}
      {stableLive && (
        <div className="flex max-w-full items-start gap-2 self-start rounded-lg bg-clay-accent/10 px-3 py-2 text-[11px] leading-relaxed text-clay-accent">
          <Loader2 className="mt-0.5 h-3.5 w-3.5 flex-shrink-0 animate-spin" />
          <span className="flex-1 whitespace-pre-wrap break-words">{stableLive}</span>
          {elapsedText && (
            <span className="mt-0.5 flex-shrink-0 text-clay-text/50 tabular-nums">{elapsedText}</span>
          )}
        </div>
      )}
    </div>
  );
}

interface PlaygroundPanelProps {
  workflowId: string;
  onClose: () => void;
}

function useRunSSE(
  runId: string | null,
  onToken: (token: string) => void,
  onEnd: (eventType: string) => void,
  onToolCall: (name: string, input?: unknown) => void,
  onToolResult: (name: string, output: string) => void,
  onLLMStart: () => void,
  onLLMEnd: () => void,
  onAgentThought: (content: string, toolNames: string[]) => void,
  onAnyEvent: (eventType: string, nodeId: string | null | undefined, payload: Record<string, unknown> | null | undefined) => void,
) {
  const [events, setEvents] = useState<RunEvent[]>([]);
  const [status, setStatus] = useState<'idle' | 'running' | 'done' | 'error'>('idle');
  const closedRef = useRef(false);
  const hasTokensRef = useRef(false);

  useEffect(() => {
    if (!runId) return;
    setStatus('running');
    setEvents([]);
    closedRef.current = false;
    hasTokensRef.current = false;

    // eslint-disable-next-line no-console
    console.debug('[playground] EventSource opening t=', performance.now().toFixed(0), 'ms');
    const es = new EventSource(`${apiBase()}/runs/${runId}/events`);
    es.addEventListener('open', () => {
      // eslint-disable-next-line no-console
      console.debug('[playground] EventSource onopen t=', performance.now().toFixed(0), 'ms');
    });

    // The backend sends named SSE events (event: llm_token, event: node_start, etc.)
    // We need to handle them via a generic listener, not onmessage (which only catches unnamed events).
    const handleEvent = (e: MessageEvent) => {
      let parsed: { event_type?: string; payload?: Record<string, unknown>; node_id?: string };
      try {
        parsed = JSON.parse(e.data);
      } catch {
        return;
      }

      const eventType = parsed.event_type || e.type;

      // 디버그 사이드바용 — 모든 이벤트(ping 제외)를 store에 푸시
      if (eventType !== 'ping') {
        onAnyEvent(eventType, parsed.node_id, parsed.payload ?? null);
      }

      // 첫 의미있는 이벤트(node_start)의 wall-time 측정용 로그
      if (eventType === 'node_start' && !hasTokensRef.current) {
        // eslint-disable-next-line no-console
        console.debug('[playground] first node_start t=', performance.now().toFixed(0), 'ms node_id=', parsed.node_id);
      }

      if (eventType === 'workflow_end') {
        // If no tokens were streamed yet but workflow_end carries final output,
        // push it as a complete message (handles non-streaming models).
        const output = (parsed.payload as Record<string, unknown>)?.output;
        if (typeof output === 'string' && output && !hasTokensRef.current) {
          onToken(output);
        }
        closedRef.current = true;
        setStatus('done');
        onEnd('workflow_end');
        es.close();
        return;
      }

      if (eventType === 'workflow_error') {
        closedRef.current = true;
        setStatus('error');
        onEnd('workflow_error');
        es.close();
        return;
      }

      if (eventType === 'llm_token') {
        const token = (parsed.payload as Record<string, unknown>)?.token;
        if (typeof token === 'string' && token) {
          hasTokensRef.current = true;
          onToken(token);
        }
        return;
      }

      if (eventType === 'tool_call') {
        const payload = (parsed.payload ?? {}) as Record<string, unknown>;
        const toolName = payload.tool_name;
        const input = payload.input;
        if (typeof toolName === 'string' && toolName) onToolCall(toolName, input);
      } else if (eventType === 'tool_result') {
        const payload = (parsed.payload ?? {}) as Record<string, unknown>;
        const toolName = payload.tool_name;
        const rawOutput = payload.output;
        const output = typeof rawOutput === 'string' ? rawOutput : '';
        if (typeof toolName === 'string' && toolName) onToolResult(toolName, output);
      } else if (eventType === 'llm_start') {
        onLLMStart();
      } else if (eventType === 'llm_end') {
        onLLMEnd();
      } else if (eventType === 'agent_thought') {
        const payload = (parsed.payload ?? {}) as Record<string, unknown>;
        const content = typeof payload.content === 'string' ? payload.content : '';
        const toolCallsRaw = payload.tool_calls;
        const toolNames: string[] = [];
        if (Array.isArray(toolCallsRaw)) {
          for (const tc of toolCallsRaw) {
            if (tc && typeof tc === 'object' && typeof (tc as { name?: unknown }).name === 'string') {
              toolNames.push((tc as { name: string }).name);
            }
          }
        }
        if (content) onAgentThought(content, toolNames);
      }

      // Other events (node_start, node_end, tool_call, etc.)
      setEvents((prev) => [
        ...prev,
        { event_type: eventType, node_id: parsed.node_id, payload: parsed.payload },
      ]);
    };

    // Listen for all named event types the backend sends
    const eventTypes = ['llm_token', 'llm_start', 'llm_end', 'agent_thought', 'node_start', 'node_end', 'workflow_end', 'workflow_error', 'tool_call', 'tool_result', 'done', 'ping'];
    for (const t of eventTypes) {
      es.addEventListener(t, handleEvent);
    }
    // Also catch unnamed messages as fallback
    es.onmessage = handleEvent;

    // Handle the "done" event (server signals clean close)
    es.addEventListener('done', () => {
      if (!closedRef.current) {
        closedRef.current = true;
        setStatus((prev) => (prev === 'running' ? 'done' : prev));
        onEnd('workflow_end');
      }
      es.close();
    });

    es.onerror = () => {
      // Only treat as error if we haven't received a clean done/workflow_end signal
      if (!closedRef.current) {
        closedRef.current = true;
        setStatus('error');
        onEnd('workflow_error');
      }
      es.close();
    };

    return () => {
      closedRef.current = true;
      es.close();
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [runId]);

  return { events, status };
}

export function PlaygroundPanel({ workflowId, onClose }: PlaygroundPanelProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [runId, setRunId] = useState<string | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  const nodes = useWorkflowStore((s) => s.nodes);
  const addExecutingNode = useWorkflowStore((s) => s.addExecutingNode);
  const removeExecutingNode = useWorkflowStore((s) => s.removeExecutingNode);
  const clearExecutingNodes = useWorkflowStore((s) => s.clearExecutingNodes);
  const pushDebugEvent = useWorkflowStore((s) => s.pushDebugEvent);
  const clearDebugEvents = useWorkflowStore((s) => s.clearDebugEvents);

  // One conversation per panel lifecycle. Panel re-open ⇒ new thread (no carryover).
  const conversationIdRef = useRef<string>(
    typeof crypto !== 'undefined' && 'randomUUID' in crypto
      ? crypto.randomUUID()
      : `conv_${Date.now()}_${Math.random().toString(36).slice(2, 10)}`,
  );

  // Cached IDs for the chat I/O nodes — backend doesn't emit events for them
  // (they collapse to LangGraph START/END), so we drive their highlight from
  // the frontend timeline instead.
  const chatInputId = nodes.find((n) => (n.data as { type?: string }).type === 'chat_input')?.id;
  const chatOutputId = nodes.find((n) => (n.data as { type?: string }).type === 'chat_output')?.id;
  const clearTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // SSE 콜백에서 setMessages만 호출하면 React 18 자동 배칭이 도구 호출 4단계
  // (call→result→call→result)와 그 후 첫 토큰까지 한 batch로 묶어 commit해서
  // running 상태가 ToolSteps에 한 번도 표시되지 않는다. flushSync로 강제 동기
  // commit해야 사용자가 라이브 라벨을 볼 수 있다.
  const appendToolStep = (toolName: string, input?: unknown) => {
    // eslint-disable-next-line no-console
    console.debug('[playground] appendToolStep', toolName);
    flushSync(() => {
      setMessages((prev) => {
        const last = prev[prev.length - 1];
        if (!last || last.role !== 'assistant' || !last.isStreaming) return prev;
        const steps = [
          ...(last.steps ?? []),
          { name: toolName, status: 'running' as const, startedAt: Date.now(), input },
        ];
        return [...prev.slice(0, -1), { ...last, steps, postToolPause: false }];
      });
    });
  };

  const completeToolStep = (toolName: string, output: string) => {
    // 출력에서 에러 패턴 감지 — MCP 표준 에러 / "error" 키워드 / Tool error
    const isError =
      /MCP error/i.test(output) ||
      /^\[Tool error/i.test(output) ||
      /"code"\s*:\s*"invalid_/i.test(output) ||
      /Input validation error/i.test(output);
    // eslint-disable-next-line no-console
    console.debug('[playground] completeToolStep', toolName, 'isError=', isError);
    flushSync(() => {
      setMessages((prev) => {
        const last = prev[prev.length - 1];
        if (!last || last.role !== 'assistant' || !last.steps) return prev;
        const steps = [...last.steps];
        // LIFO 매칭: 같은 이름의 가장 최근 running 단계를 마감
        for (let i = steps.length - 1; i >= 0; i--) {
          if (steps[i].name === toolName && steps[i].status === 'running') {
            steps[i] = {
              ...steps[i],
              status: isError ? ('error' as const) : ('done' as const),
              endedAt: Date.now(),
              output,
            };
            break;
          }
        }
        return [
          ...prev.slice(0, -1),
          {
            ...last,
            steps,
            postToolPause: !isError,
            lastErrorAt: isError ? Date.now() : last.lastErrorAt,
            lastToolStatus: isError ? 'error' : 'success',
          },
        ];
      });
    });
  };

  // LLM 추론 시작/끝 — A안 fallback 라벨이 풍부하게 전환되도록 추적.
  // tool 핸들러와 동일하게 flushSync로 강제 commit.
  const startLLMInference = () => {
    flushSync(() => {
      setMessages((prev) => {
        const last = prev[prev.length - 1];
        if (!last || last.role !== 'assistant' || !last.isStreaming) return prev;
        return [
          ...prev.slice(0, -1),
          {
            ...last,
            llmInferring: true,
            llmCallCount: (last.llmCallCount ?? 0) + 1,
          },
        ];
      });
    });
  };

  const endLLMInference = () => {
    flushSync(() => {
      setMessages((prev) => {
        const last = prev[prev.length - 1];
        if (!last || last.role !== 'assistant' || !last.isStreaming) return prev;
        return [
          ...prev.slice(0, -1),
          { ...last, llmInferring: false },
        ];
      });
    });
  };

  const appendAgentThought = (content: string, toolNames: string[]) => {
    if (!content.trim()) return;
    flushSync(() => {
      setMessages((prev) => {
        const last = prev[prev.length - 1];
        if (!last || last.role !== 'assistant' || !last.isStreaming) return prev;
        const thoughts = [
          ...(last.thoughts ?? []),
          {
            id: `thought_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`,
            content,
            toolNames,
            createdAt: Date.now(),
          },
        ];
        return [...prev.slice(0, -1), { ...last, thoughts }];
      });
    });
  };

  const appendToken = (token: string) => {
    setMessages((prev) => {
      const last = prev[prev.length - 1];
      if (last && last.role === 'assistant' && last.isStreaming) {
        return [
          ...prev.slice(0, -1),
          { ...last, content: last.content + token, postToolPause: false },
        ];
      }
      return prev;
    });
  };

  const finalizeRun = (eventType: string) => {
    setIsRunning(false);
    setRunId(null);

    // Mark ChatOutput as the final active node briefly, then clear all.
    if (eventType === 'workflow_end' && chatOutputId) {
      // Drop any lingering processing nodes; show only ChatOutput.
      clearExecutingNodes();
      addExecutingNode(chatOutputId);
    }
    if (clearTimerRef.current) clearTimeout(clearTimerRef.current);
    clearTimerRef.current = setTimeout(() => {
      clearExecutingNodes();
      clearTimerRef.current = null;
    }, 1500);

    if (eventType === 'workflow_error') {
      setMessages((prev) => {
        const last = prev[prev.length - 1];
        if (last && last.role === 'assistant' && last.isStreaming) {
          return [
            ...prev.slice(0, -1),
            { ...last, isStreaming: false, content: last.content || '오류가 발생했습니다.' },
          ];
        }
        return prev;
      });
    } else {
      setMessages((prev) => {
        const last = prev[prev.length - 1];
        if (last && last.role === 'assistant' && last.isStreaming) {
          return [...prev.slice(0, -1), { ...last, isStreaming: false }];
        }
        return prev;
      });
    }
  };

  const { events } = useRunSSE(
    runId,
    appendToken,
    finalizeRun,
    appendToolStep,
    completeToolStep,
    startLLMInference,
    endLLMInference,
    appendAgentThought,
    (event_type, node_id, payload) =>
      pushDebugEvent({ event_type, node_id, payload }),
  );

  // Track only newly-arrived events to drive incremental side-effects
  // (highlight set + log). Without this, replaying the cumulative `events`
  // array on every change would double-add entries.
  const lastEventIndexRef = useRef(0);
  useEffect(() => {
    if (events.length <= lastEventIndexRef.current) {
      lastEventIndexRef.current = events.length;
      return;
    }
    const newOnes = events.slice(lastEventIndexRef.current);
    lastEventIndexRef.current = events.length;

    // 노드 하이라이트: node_start 시 그래프 노드와 매칭되는 ID만 활성화하고,
    // 이전에 활성화돼 있던 노드는 모두 정리해서 "한 번에 한 노드만 보이게" 한다.
    // node_end는 무시 — LangGraph가 LLM 호출 단위로 매번 토글해서 paint 안 됨.
    // 대신 다음 node_start가 자연스럽게 갈아끼우고, workflow 끝에 finalizeRun이 정리.
    const graphNodeIds = new Set(nodes.map((n) => n.id));
    for (const ev of newOnes) {
      if (ev.event_type === 'node_start' && ev.node_id && graphNodeIds.has(ev.node_id)) {
        flushSync(() => {
          clearExecutingNodes();
          addExecutingNode(ev.node_id as string);
        });
      }
    }
  }, [events, addExecutingNode, clearExecutingNodes, nodes]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    return () => {
      if (clearTimerRef.current) {
        clearTimeout(clearTimerRef.current);
        clearTimerRef.current = null;
      }
      clearExecutingNodes();
    };
  }, [clearExecutingNodes]);

  const handleSend = async () => {
    const text = input.trim();
    if (!text || isRunning) return;

    try {
      const validation = await validateWorkflow(workflowId);
      if (!validation.valid) {
        const firstWarning = validation.warnings[0]?.message ?? '워크플로우가 유효하지 않습니다.';
        setMessages((prev) => [
          ...prev,
          { role: 'assistant', content: `⚠️ ${firstWarning}`, isStreaming: false },
        ]);
        return;
      }
    } catch {
      // validation endpoint failure — proceed optimistically
    }

    setInput('');
    setMessages((prev) => [
      ...prev,
      { role: 'user', content: text },
      { role: 'assistant', content: '', isStreaming: true, startedAt: Date.now() },
    ]);
    setIsRunning(true);

    // Seed highlight on ChatInput; it'll be cleared as soon as the first
    // backend node_start arrives.
    if (clearTimerRef.current) {
      clearTimeout(clearTimerRef.current);
      clearTimerRef.current = null;
    }
    clearExecutingNodes();
    clearDebugEvents();
    if (chatInputId) addExecutingNode(chatInputId);
    // eslint-disable-next-line no-console
    console.debug('[playground] handleSend t=', performance.now().toFixed(0), 'ms');

    try {
      const res = await fetch(`${apiBase()}/workflows/${workflowId}/runs`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          input: {
            message: text,
            conversation_id: conversationIdRef.current,
          },
        }),
      });

      if (!res.ok) {
        let errorDetail = '실행 요청에 실패했습니다.';
        try {
          const errBody = await res.json() as { detail?: string };
          if (errBody.detail) errorDetail = errBody.detail;
        } catch {
          // ignore JSON parse failure — keep default message
        }
        throw new Error(errorDetail);
      }

      const body = (await res.json()) as { run_id: string } | { id: string };
      const id = 'run_id' in body ? body.run_id : body.id;
      setRunId(id);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : '실행 요청에 실패했습니다.';
      setIsRunning(false);
      setMessages((prev) => {
        const last = prev[prev.length - 1];
        if (last && last.role === 'assistant' && last.isStreaming) {
          return [
            ...prev.slice(0, -1),
            { ...last, isStreaming: false, content: message },
          ];
        }
        return prev;
      });
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      void handleSend();
    }
  };

  return (
    <aside className="flex w-96 flex-col border-l border-clay-border bg-white">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-clay-border bg-clay-surface px-4 py-2">
        <div className="flex items-center gap-2">
          <Play className="h-4 w-4 text-clay-accent" />
          <span className="text-sm font-semibold text-clayBlack">플레이그라운드</span>
          {isRunning && (
            <span className="flex items-center gap-1 text-xs text-clay-accent">
              <span className="inline-block h-2 w-2 animate-pulse rounded-full bg-clay-accent" />
              실행 중...
            </span>
          )}
        </div>
        <button
          onClick={onClose}
          aria-label="닫기"
          className="text-xs text-warmSilver hover:text-clayBlack"
        >
          ✕
        </button>
      </div>

      {/* Message list */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {messages.length === 0 && (
          <p className="text-center text-xs text-warmSilver mt-8">
            메시지를 입력해 워크플로우를 실행하세요.
          </p>
        )}
        {messages.map((msg, i) => (
          <div
            key={`msg-${i}-${msg.role}`}
            className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[80%] rounded-xl px-3 py-2 text-sm leading-relaxed ${
                msg.role === 'user'
                  ? 'bg-violet-950 text-white'
                  : 'bg-cream border border-clay-border text-clayBlack'
              }`}
            >
              {msg.role === 'assistant' &&
                (msg.isStreaming ||
                  (msg.steps && msg.steps.length > 0) ||
                  (msg.thoughts && msg.thoughts.length > 0)) && (
                <ToolSteps
                  steps={msg.steps ?? []}
                  thoughts={msg.thoughts ?? []}
                  isStreaming={msg.isStreaming}
                  hasContent={!!msg.content}
                  postToolPause={!!msg.postToolPause}
                  startedAt={msg.startedAt}
                  lastErrorAt={msg.lastErrorAt}
                  llmInferring={msg.llmInferring}
                  llmCallCount={msg.llmCallCount}
                  lastToolStatus={msg.lastToolStatus}
                />
              )}
              {msg.role === 'assistant' && msg.content ? (
                <ReactMarkdown
                  remarkPlugins={[remarkGfm]}
                  components={{
                    p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
                    ul: ({ children }) => <ul className="mb-2 ml-4 list-disc last:mb-0">{children}</ul>,
                    ol: ({ children }) => <ol className="mb-2 ml-4 list-decimal last:mb-0">{children}</ol>,
                    li: ({ children }) => <li className="mb-0.5">{children}</li>,
                    code: ({ children, className }) => {
                      const isBlock = className?.includes('language-');
                      return isBlock ? (
                        <pre className="my-2 overflow-x-auto rounded bg-gray-900 px-3 py-2 text-xs text-gray-100">
                          <code>{children}</code>
                        </pre>
                      ) : (
                        <code className="rounded bg-gray-200 px-1 py-0.5 text-xs">{children}</code>
                      );
                    },
                    pre: ({ children }) => <>{children}</>,
                    strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
                    a: ({ href, children }) => (
                      <a href={href} target="_blank" rel="noopener noreferrer" className="text-blue-600 underline">
                        {children}
                      </a>
                    ),
                    table: ({ children }) => (
                      <div className="my-2 overflow-x-auto">
                        <table className="min-w-full border-collapse text-xs">{children}</table>
                      </div>
                    ),
                    th: ({ children }) => <th className="border border-clay-border bg-oat-light px-2 py-1 text-left font-medium">{children}</th>,
                    td: ({ children }) => <td className="border border-clay-border px-2 py-1">{children}</td>,
                  }}
                >
                  {msg.content}
                </ReactMarkdown>
              ) : (
                msg.content || ''
              )}
            </div>
          </div>
        ))}

        <div ref={bottomRef} />
      </div>

      {/* Input area */}
      <div className="border-t border-clay-border p-3">
        <div className="flex gap-2">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isRunning}
            placeholder="메시지 입력... (Enter로 전송)"
            rows={2}
            className="flex-1 resize-none rounded border border-clay-border bg-white px-3 py-2 text-xs focus:outline-none focus:ring-2 focus:ring-clay-accent disabled:opacity-50"
          />
          <button
            onClick={() => void handleSend()}
            disabled={isRunning || !input.trim()}
            className="self-end rounded bg-clay-accent px-3 py-2 text-xs text-white hover:opacity-90 disabled:opacity-50"
          >
            <Send className="h-4 w-4" />
          </button>
        </div>
      </div>
    </aside>
  );
}
