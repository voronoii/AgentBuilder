'use client';

import { useEffect, useRef } from 'react';
import { Bug, Trash2 } from 'lucide-react';

import { useWorkflowStore } from '@/stores/workflowStore';

interface DebugEventPanelProps {
  onClose: () => void;
}

const TYPE_COLORS: Record<string, string> = {
  node_start: 'text-blue-600',
  node_end: 'text-blue-400',
  llm_start: 'text-emerald-600',
  llm_end: 'text-emerald-400',
  llm_token: 'text-amber-600',
  tool_call: 'text-purple-600',
  tool_result: 'text-purple-400',
  workflow_end: 'text-green-600',
  workflow_error: 'text-red-600',
  hook_start: 'text-orange-600',
  hook_result: 'text-orange-400',
};

function formatTime(ms: number): string {
  const d = new Date(ms);
  const hh = d.getHours().toString().padStart(2, '0');
  const mm = d.getMinutes().toString().padStart(2, '0');
  const ss = d.getSeconds().toString().padStart(2, '0');
  const msPart = d.getMilliseconds().toString().padStart(3, '0');
  return `${hh}:${mm}:${ss}.${msPart}`;
}

function previewPayload(payload: Record<string, unknown> | null | undefined): string {
  if (!payload) return '';
  // llm_token은 토큰만 압축 표시
  if (typeof payload.token === 'string') {
    const t = payload.token;
    return t.length > 30 ? `"${t.slice(0, 30)}…"` : `"${t}"`;
  }
  // 일반 payload는 JSON 직렬화 후 자르기
  try {
    const raw = JSON.stringify(payload);
    return raw.length > 120 ? raw.slice(0, 120) + '…' : raw;
  } catch {
    return String(payload);
  }
}

export function DebugEventPanel({ onClose }: DebugEventPanelProps) {
  const debugEvents = useWorkflowStore((s) => s.debugEvents);
  const executingNodeIds = useWorkflowStore((s) => s.executingNodeIds);
  const nodes = useWorkflowStore((s) => s.nodes);
  const clearDebugEvents = useWorkflowStore((s) => s.clearDebugEvents);

  const listRef = useRef<HTMLDivElement>(null);

  // 새 이벤트 도착 시 자동 스크롤(맨 아래)
  useEffect(() => {
    if (listRef.current) {
      listRef.current.scrollTop = listRef.current.scrollHeight;
    }
  }, [debugEvents.length]);

  const graphIds = nodes.map((n) => ({
    id: n.id,
    label: (n.data as { label?: string }).label ?? n.id,
    type: (n.data as { type?: string }).type ?? '?',
  }));

  return (
    <aside className="flex w-[28rem] flex-col border-l border-clay-border bg-white">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-clay-border bg-clay-surface px-4 py-2">
        <div className="flex items-center gap-2">
          <Bug className="h-4 w-4 text-clay-accent" />
          <span className="text-sm font-semibold text-clayBlack">디버그</span>
          <span className="text-[11px] text-warmSilver">
            {debugEvents.length}개 이벤트
          </span>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={() => clearDebugEvents()}
            aria-label="비우기"
            className="rounded p-1 text-warmSilver hover:bg-oat-light hover:text-clayBlack"
            title="이벤트 로그 비우기"
          >
            <Trash2 className="h-3.5 w-3.5" />
          </button>
          <button
            onClick={onClose}
            aria-label="닫기"
            className="text-xs text-warmSilver hover:text-clayBlack"
          >
            ✕
          </button>
        </div>
      </div>

      {/* Status — 활성 노드 + 그래프 노드 매핑 */}
      <div className="border-b border-clay-border bg-cream px-3 py-2 text-[11px]">
        <div className="mb-1.5">
          <span className="font-semibold text-clayBlack">활성 노드: </span>
          {executingNodeIds.size === 0 ? (
            <span className="text-warmSilver">(없음)</span>
          ) : (
            [...executingNodeIds].map((id) => {
              const meta = graphIds.find((n) => n.id === id);
              return (
                <span
                  key={id}
                  className="ml-1 inline-flex items-center gap-1 rounded bg-clay-accent/10 px-1.5 py-0.5 text-clay-accent"
                >
                  {meta ? `${meta.label} (${meta.type})` : id}
                </span>
              );
            })
          )}
        </div>
        <details className="text-warmSilver">
          <summary className="cursor-pointer font-semibold text-clayBlack">
            그래프 노드 ID ({graphIds.length})
          </summary>
          <div className="mt-1 space-y-0.5 font-mono text-[10px]">
            {graphIds.map((n) => (
              <div key={n.id}>
                <span className="text-clay-text">{n.label}</span>
                <span className="ml-1 text-warmSilver">[{n.type}]</span>
                <span className="ml-1 text-purple-500">{n.id}</span>
              </div>
            ))}
          </div>
        </details>
      </div>

      {/* Events list */}
      <div ref={listRef} className="flex-1 overflow-y-auto bg-white p-2 font-mono text-[10px]">
        {debugEvents.length === 0 && (
          <p className="mt-4 text-center text-xs text-warmSilver">
            워크플로우를 실행하면 이벤트가 여기에 실시간으로 표시됩니다.
          </p>
        )}
        {debugEvents.map((ev) => {
          const colorCls = TYPE_COLORS[ev.event_type] ?? 'text-clay-text';
          const matched = ev.node_id
            ? graphIds.find((n) => n.id === ev.node_id)
            : null;
          return (
            <div
              key={ev.seq}
              className="border-b border-oat-light px-1 py-1 leading-snug"
            >
              <div className="flex items-baseline gap-2">
                <span className="text-warmSilver tabular-nums">#{ev.seq}</span>
                <span className="text-warmSilver tabular-nums">
                  {formatTime(ev.receivedAt)}
                </span>
                <span className={`font-semibold ${colorCls}`}>{ev.event_type}</span>
              </div>
              {ev.node_id && (
                <div className="mt-0.5 ml-6">
                  <span className="text-warmSilver">node:</span>{' '}
                  <span className={matched ? 'text-emerald-600' : 'text-amber-600'}>
                    {ev.node_id}
                  </span>
                  {matched ? (
                    <span className="ml-1 text-emerald-600">✓ {matched.label}</span>
                  ) : (
                    <span className="ml-1 text-amber-600">✗ 그래프 매칭 없음</span>
                  )}
                </div>
              )}
              {ev.payload && Object.keys(ev.payload).length > 0 && (
                <div className="mt-0.5 ml-6 break-all text-warmCharcoal">
                  {previewPayload(ev.payload)}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </aside>
  );
}
