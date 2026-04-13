'use client';

import { useEffect, useRef, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Play, Send } from 'lucide-react';

import { apiBase } from '@/lib/api';
import { validateWorkflow } from '@/lib/workflow';

interface RunEvent {
  event_type: string;
  node_id?: string;
  data?: unknown;
  token?: string;
}

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  isStreaming?: boolean;
}

interface PlaygroundPanelProps {
  workflowId: string;
  onClose: () => void;
}

function useRunSSE(runId: string | null, onToken: (token: string) => void, onEnd: (eventType: string) => void) {
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

    const es = new EventSource(`${apiBase()}/runs/${runId}/events`);

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

      // Other events (node_start, node_end, tool_call, etc.)
      setEvents((prev) => [...prev, { event_type: eventType, node_id: parsed.node_id }]);
    };

    // Listen for all named event types the backend sends
    const eventTypes = ['llm_token', 'node_start', 'node_end', 'workflow_end', 'workflow_error', 'tool_call', 'tool_result', 'done', 'ping'];
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
  const [nodeLog, setNodeLog] = useState<string[]>([]);
  const bottomRef = useRef<HTMLDivElement>(null);

  const appendToken = (token: string) => {
    setMessages((prev) => {
      const last = prev[prev.length - 1];
      if (last && last.role === 'assistant' && last.isStreaming) {
        return [
          ...prev.slice(0, -1),
          { ...last, content: last.content + token },
        ];
      }
      return prev;
    });
  };

  const finalizeRun = (eventType: string) => {
    setIsRunning(false);
    setRunId(null);
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

  const { events } = useRunSSE(runId, appendToken, finalizeRun);

  useEffect(() => {
    const nodeEvents = events.filter(
      (e) => e.event_type === 'node_start' || e.event_type === 'node_end',
    );
    if (nodeEvents.length > 0) {
      const lastEvent = nodeEvents[nodeEvents.length - 1];
      const label =
        lastEvent.event_type === 'node_start'
          ? `▶ 노드 시작: ${lastEvent.node_id ?? ''}`
          : `✓ 노드 완료: ${lastEvent.node_id ?? ''}`;
      setNodeLog((prev) => [...prev, label]);
    }
  }, [events]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

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
    setNodeLog([]);
    setMessages((prev) => [
      ...prev,
      { role: 'user', content: text },
      { role: 'assistant', content: '', isStreaming: true },
    ]);
    setIsRunning(true);

    try {
      const res = await fetch(`${apiBase()}/workflows/${workflowId}/runs`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ input: { message: text } }),
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
                msg.content || (msg.isStreaming ? <span className="animate-pulse">…</span> : '')
              )}
            </div>
          </div>
        ))}

        {/* Node log */}
        {nodeLog.length > 0 && (
          <div className="rounded border border-clay-border bg-oat-light px-3 py-2 space-y-0.5">
            {nodeLog.map((log, i) => (
              <p key={`log-${i}`} className="text-[10px] text-warmSilver">{log}</p>
            ))}
          </div>
        )}

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
