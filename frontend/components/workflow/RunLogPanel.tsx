'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { Play, Check, MessageSquare, Wrench, ClipboardList, CheckCircle, AlertCircle, RefreshCw } from 'lucide-react';
import React from 'react';
import { Badge } from '@/components/ui/badge';

import { apiBase } from '@/lib/api';

interface RunSummary {
  id: string;
  status: 'running' | 'success' | 'failed' | 'cancelled';
  started_at: string;
  ended_at: string | null;
  error?: string | null;
  output?: Record<string, unknown> | null;
}

interface RunEvent {
  id: string;
  run_id: string;
  event_type: string;
  node_id?: string | null;
  timestamp: string;
  payload: Record<string, unknown>;
}

const STATUS_LABELS: Record<RunSummary['status'], string> = {
  running: '실행 중',
  success: '성공',
  failed: '실패',
  cancelled: '취소됨',
};


function formatRelativeTime(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffSec = Math.floor(diffMs / 1000);

  if (diffSec < 60) return `${diffSec}초 전`;
  const diffMin = Math.floor(diffSec / 60);
  if (diffMin < 60) return `${diffMin}분 전`;
  const diffHr = Math.floor(diffMin / 60);
  if (diffHr < 24) return `${diffHr}시간 전`;
  const diffDay = Math.floor(diffHr / 24);
  return `${diffDay}일 전`;
}

const EVENT_ICONS: Record<string, React.ReactNode> = {
  node_start: <Play className="h-3.5 w-3.5" />,
  node_end: <Check className="h-3.5 w-3.5" />,
  llm_token: <MessageSquare className="h-3.5 w-3.5" />,
  tool_call: <Wrench className="h-3.5 w-3.5" />,
  tool_result: <ClipboardList className="h-3.5 w-3.5" />,
  workflow_end: <CheckCircle className="h-3.5 w-3.5" />,
  workflow_error: <AlertCircle className="h-3.5 w-3.5" />,
};

const EVENT_COLORS: Record<string, string> = {
  node_start: 'text-blue-600',
  node_end: 'text-green-600',
  workflow_error: 'text-red-600',
  workflow_end: 'text-green-700',
  tool_call: 'text-purple-600',
  tool_result: 'text-purple-500',
};

function formatPayload(ev: RunEvent): string | null {
  const p = ev.payload;
  if (!p || Object.keys(p).length === 0) return null;

  if (ev.event_type === 'workflow_error' && p.error) {
    return String(p.error);
  }
  if (ev.event_type === 'node_end' && p.output) {
    const out = String(p.output);
    return out.length > 200 ? out.slice(0, 200) + '…' : out;
  }
  if (ev.event_type === 'tool_call' && p.tool_name) {
    return `${p.tool_name}(${p.args ? JSON.stringify(p.args).slice(0, 100) : ''})`;
  }
  if (ev.event_type === 'tool_result' && p.result) {
    const r = String(p.result);
    return r.length > 200 ? r.slice(0, 200) + '…' : r;
  }
  if (p.node_name) return String(p.node_name);

  // Fallback: show raw JSON for unknown payloads
  const raw = JSON.stringify(p);
  return raw.length > 200 ? raw.slice(0, 200) + '…' : raw;
}

/** Merge consecutive llm_token events into a single display entry. */
function mergeTokenEvents(events: RunEvent[]): RunEvent[] {
  const merged: RunEvent[] = [];
  let tokenBuf = '';
  let tokenNodeId: string | null = null;
  let tokenTimestampStart = '';
  let tokenTimestampEnd = '';
  let tokenCount = 0;

  const flush = () => {
    if (tokenCount > 0) {
      merged.push({
        id: `merged-llm-token-${merged.length}`,
        run_id: '',
        event_type: 'llm_token_merged',
        node_id: tokenNodeId,
        timestamp: tokenTimestampStart,
        payload: {
          text: tokenBuf,
          token_count: tokenCount,
          timestamp_end: tokenTimestampEnd,
        },
      });
      tokenBuf = '';
      tokenNodeId = null;
      tokenTimestampStart = '';
      tokenTimestampEnd = '';
      tokenCount = 0;
    }
  };

  for (const ev of events) {
    if (ev.event_type === 'llm_token') {
      const token = typeof ev.payload?.token === 'string' ? ev.payload.token : '';
      tokenBuf += token;
      tokenCount++;
      if (!tokenTimestampStart) tokenTimestampStart = ev.timestamp;
      tokenTimestampEnd = ev.timestamp;
      tokenNodeId = ev.node_id ?? tokenNodeId;
    } else {
      flush();
      merged.push(ev);
    }
  }
  flush();
  return merged;
}

function RunEventList({ runId }: { runId: string }) {
  const [events, setEvents] = useState<RunEvent[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${apiBase()}/runs/${runId}/events/history`)
      .then((r) => r.json())
      .then((data: RunEvent[]) => setEvents(Array.isArray(data) ? data : []))
      .catch(() => setEvents([]))
      .finally(() => setLoading(false));
  }, [runId]);

  if (loading) {
    return <p className="py-2 text-xs text-warmSilver">로딩 중...</p>;
  }

  if (events.length === 0) {
    return <p className="py-2 text-xs text-warmSilver">이벤트가 없습니다.</p>;
  }

  const displayEvents = mergeTokenEvents(events);

  return (
    <div className="mt-2 space-y-1.5">
      {displayEvents.map((ev, i) => {
        const isMergedToken = ev.event_type === 'llm_token_merged';
        const icon = isMergedToken ? EVENT_ICONS.llm_token : (EVENT_ICONS[ev.event_type] || <span className="text-xs">•</span>);
        const color = EVENT_COLORS[ev.event_type] || 'text-clay-text';
        const isError = ev.event_type === 'workflow_error';

        // For merged tokens, show concatenated text
        const detail = isMergedToken
          ? (() => {
              const text = String(ev.payload.text ?? '');
              const count = Number(ev.payload.token_count ?? 0);
              const preview = text.length > 300 ? text.slice(0, 300) + '…' : text;
              return `[${count} tokens] ${preview}`;
            })()
          : formatPayload(ev);

        // For merged tokens, show time range
        const timeLabel = isMergedToken && ev.payload.timestamp_end
          ? `${new Date(ev.timestamp).toLocaleTimeString('ko-KR')} ~ ${new Date(String(ev.payload.timestamp_end)).toLocaleTimeString('ko-KR')}`
          : ev.timestamp
            ? new Date(ev.timestamp).toLocaleTimeString('ko-KR')
            : '';

        return (
          <div
            key={i}
            className={`rounded px-2 py-1.5 ${isError ? 'bg-red-50 border border-red-200' : 'bg-white'}`}
          >
            <div className="flex items-center gap-1.5">
              <span className={`flex items-center ${isMergedToken ? 'text-amber-600' : color}`}>{icon}</span>
              <span className={`text-[11px] font-medium ${isMergedToken ? 'text-amber-600' : color}`}>
                {isMergedToken ? 'llm_output' : ev.event_type}
              </span>
              {ev.node_id && (
                <span className="text-[10px] font-mono text-warmSilver truncate">
                  {ev.node_id.length > 20
                    ? ev.node_id.slice(0, 10) + '…' + ev.node_id.slice(-6)
                    : ev.node_id}
                </span>
              )}
              {timeLabel && (
                <span className="ml-auto text-[9px] text-warmSilver shrink-0">
                  {timeLabel}
                </span>
              )}
            </div>
            {detail && (
              <p
                className={`mt-1 text-[11px] leading-relaxed break-all ${
                  isError ? 'text-red-600 font-medium' : 'text-warmCharcoal'
                }`}
              >
                {detail}
              </p>
            )}
          </div>
        );
      })}
    </div>
  );
}

interface RunRowProps {
  run: RunSummary;
}

function RunRow({ run }: RunRowProps) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="rounded border border-clay-border bg-white">
      <button
        onClick={() => setExpanded((v) => !v)}
        className="flex w-full items-center gap-2 px-3 py-2 text-left hover:bg-cream transition-colors"
      >
        <Badge variant={
          run.status === 'success' ? 'success' :
          run.status === 'failed' ? 'destructive' :
          run.status === 'running' ? 'info' : 'default'
        }>
          {STATUS_LABELS[run.status]}
        </Badge>
        <span className="flex-1 truncate text-xs font-mono text-warmSilver">
          {run.id.slice(0, 8)}
        </span>
        <span className="shrink-0 text-[10px] text-warmSilver">
          {formatRelativeTime(run.started_at)}
        </span>
        <span className="text-warmSilver">{expanded ? '▲' : '▼'}</span>
      </button>

      {/* Error preview (always visible for failed runs) */}
      {!expanded && run.status === 'failed' && run.error && (
        <div className="border-t border-red-100 px-3 py-1.5">
          <p className="text-[11px] text-red-500 line-clamp-2 break-all">
            {run.error}
          </p>
        </div>
      )}

      {expanded && (
        <div className="border-t border-clay-border px-3 pb-3">
          <div className="mt-2 text-[10px] text-warmSilver space-y-0.5">
            <p>시작: {new Date(run.started_at).toLocaleString('ko-KR')}</p>
            {run.ended_at && (
              <p>종료: {new Date(run.ended_at).toLocaleString('ko-KR')}</p>
            )}
          </div>
          {run.status === 'failed' && run.error && (
            <div className="mt-2 rounded bg-red-50 border border-red-200 px-3 py-2">
              <p className="text-[10px] font-medium text-red-400 mb-1">에러 메시지</p>
              <p className="text-[11px] text-red-600 break-all leading-relaxed">
                {run.error}
              </p>
            </div>
          )}
          <RunEventList runId={run.id} />
        </div>
      )}
    </div>
  );
}

interface RunLogPanelProps {
  workflowId: string;
}

export function RunLogPanel({ workflowId }: RunLogPanelProps) {
  const [runs, setRuns] = useState<RunSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchRuns = useCallback(async (showSpinner = false) => {
    if (showSpinner) setRefreshing(true);
    try {
      const res = await fetch(`${apiBase()}/workflows/${workflowId}/runs`);
      const data: RunSummary[] = await res.json();
      setRuns(Array.isArray(data) ? data : []);
    } catch {
      /* keep existing data */
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [workflowId]);

  // Initial load
  useEffect(() => { fetchRuns(); }, [fetchRuns]);

  // Auto-poll while any run is "running"
  useEffect(() => {
    const hasRunning = runs.some((r) => r.status === 'running');
    if (hasRunning && !pollRef.current) {
      pollRef.current = setInterval(() => fetchRuns(), 3000);
    }
    if (!hasRunning && pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [runs, fetchRuns]);

  if (loading) {
    return <p className="text-xs text-warmSilver">로딩 중...</p>;
  }

  return (
    <div className="space-y-2">
      <button
        onClick={() => fetchRuns(true)}
        disabled={refreshing}
        className="flex w-full items-center justify-center gap-1.5 rounded border border-clay-border px-3 py-1.5 text-xs text-clay-text hover:bg-oat-light transition-colors disabled:opacity-50"
      >
        <RefreshCw className={`h-3.5 w-3.5 ${refreshing ? 'animate-spin' : ''}`} />
        {refreshing ? '갱신 중...' : '새로고침'}
      </button>

      {runs.length === 0 ? (
        <p className="text-xs text-warmSilver">
          실행 내역이 없습니다. 플레이그라운드에서 워크플로우를 실행해 보세요.
        </p>
      ) : (
        runs.map((run) => <RunRow key={run.id} run={run} />)
      )}
    </div>
  );
}
