'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { MessageSquarePlus, Send, Trash2 } from 'lucide-react';

interface AppConfig {
  id: string;
  name: string;
  description?: string;
  welcome_message?: string;
  icon?: string;
}

interface Conversation {
  id: string;
  title?: string;
  created_at?: string;
  updated_at?: string;
}

interface Message {
  role: 'user' | 'assistant';
  content: string;
  isStreaming?: boolean;
}

interface ChatAppProps {
  appId: string;
}

export function ChatApp({ appId }: ChatAppProps) {
  const [config, setConfig] = useState<AppConfig | null>(null);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConvId, setActiveConvId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  const fetchConfig = useCallback(async () => {
    try {
      const res = await fetch(`/api/apps/${appId}/config`);
      if (res.ok) {
        const data = await res.json();
        setConfig(data);
      }
    } catch {
      // ignore
    }
  }, [appId]);

  const fetchConversations = useCallback(async () => {
    try {
      const res = await fetch(`/api/chat/${appId}`);
      if (res.ok) {
        const data = await res.json();
        setConversations(Array.isArray(data) ? data : data.conversations ?? []);
      }
    } catch {
      // ignore
    }
  }, [appId]);

  useEffect(() => {
    fetchConfig();
    fetchConversations();
  }, [fetchConfig, fetchConversations]);

  const loadConversation = useCallback(async (convId: string) => {
    setActiveConvId(convId);
    try {
      const res = await fetch(`/api/chat/${appId}?conversation_id=${convId}`);
      if (res.ok) {
        const data = await res.json();
        const msgs: Message[] = (Array.isArray(data) ? data : data.messages ?? []).map(
          (m: { role: string; content: string }) => ({
            role: m.role as 'user' | 'assistant',
            content: m.content,
          }),
        );
        setMessages(msgs);
      }
    } catch {
      // ignore
    }
  }, [appId]);

  const startNewConversation = useCallback(() => {
    setActiveConvId(null);
    setMessages([]);
    setInput('');
  }, []);

  const deleteConversation = useCallback(async (convId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await fetch(`/api/chat/${appId}?conversation_id=${convId}`, { method: 'DELETE' });
      if (activeConvId === convId) {
        startNewConversation();
      }
      setConversations((prev) => prev.filter((c) => c.id !== convId));
    } catch {
      // ignore
    }
  }, [appId, activeConvId, startNewConversation]);

  const sendMessage = useCallback(async () => {
    const text = input.trim();
    if (!text || sending) return;

    setInput('');
    setSending(true);

    const userMsg: Message = { role: 'user', content: text };
    const assistantMsg: Message = { role: 'assistant', content: '', isStreaming: true };

    setMessages((prev) => [...prev, userMsg, assistantMsg]);

    try {
      const body = {
        messages: [{ role: 'user', content: text }],
        stream: true,
        ...(activeConvId ? { conversation_id: activeConvId } : {}),
      };

      const res = await fetch(`/api/chat/${appId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });

      if (!res.ok || !res.body) {
        setMessages((prev) => {
          const next = [...prev];
          const last = next[next.length - 1];
          if (last?.isStreaming) {
            next[next.length - 1] = { ...last, content: '오류가 발생했습니다.', isStreaming: false };
          }
          return next;
        });
        return;
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let capturedConvId: string | null = null;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() ?? '';

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          const payload = line.slice(6).trim();
          if (payload === '[DONE]') {
            setMessages((prev) => {
              const next = [...prev];
              const last = next[next.length - 1];
              if (last?.isStreaming) {
                next[next.length - 1] = { ...last, isStreaming: false };
              }
              return next;
            });
            if (capturedConvId) {
              setActiveConvId(capturedConvId);
            }
            await fetchConversations();
            continue;
          }

          try {
            const json = JSON.parse(payload);

            // Capture conversation_id from first chunk
            if (!capturedConvId && json.conversation_id) {
              capturedConvId = json.conversation_id;
            }

            const delta = json.choices?.[0]?.delta?.content;
            if (delta) {
              setMessages((prev) => {
                const next = [...prev];
                const last = next[next.length - 1];
                if (last?.isStreaming) {
                  next[next.length - 1] = { ...last, content: last.content + delta };
                }
                return next;
              });
            }
          } catch {
            // skip malformed lines
          }
        }
      }
    } catch {
      setMessages((prev) => {
        const next = [...prev];
        const last = next[next.length - 1];
        if (last?.isStreaming) {
          next[next.length - 1] = { ...last, content: '오류가 발생했습니다.', isStreaming: false };
        }
        return next;
      });
    } finally {
      setSending(false);
    }
  }, [input, sending, activeConvId, appId, fetchConversations]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
      }
    },
    [sendMessage],
  );

  const convLabel = (conv: Conversation) =>
    conv.title ?? `대화 ${conv.id.slice(0, 8)}`;

  return (
    <div className="flex h-screen bg-clay-bg text-clayBlack overflow-hidden">
      {/* Sidebar */}
      <aside className="w-56 flex flex-col bg-clay-surface border-r border-clay-border shrink-0">
        {/* App header */}
        <div className="px-4 py-5 border-b border-clay-border">
          <div className="flex items-center gap-2">
            <span className="text-2xl">{config?.icon ?? '🤖'}</span>
            <span className="font-semibold text-sm leading-tight line-clamp-2">
              {config?.name ?? '...'}
            </span>
          </div>
        </div>

        {/* New conversation */}
        <div className="px-3 pt-3">
          <button
            onClick={startNewConversation}
            className="w-full flex items-center gap-2 px-3 py-2 rounded-xl text-sm font-medium bg-clay-accent text-white hover:opacity-90 transition-opacity"
          >
            <MessageSquarePlus size={15} />
            새 대화
          </button>
        </div>

        {/* Conversation list */}
        <nav className="flex-1 overflow-y-auto px-3 py-2 space-y-0.5">
          {conversations.length === 0 && (
            <p className="text-xs text-warmSilver px-2 py-3">대화 없음</p>
          )}
          {conversations.map((conv) => (
            <button
              key={conv.id}
              onClick={() => loadConversation(conv.id)}
              className={`group w-full flex items-center justify-between gap-1 px-2 py-2 rounded-lg text-xs text-left transition-colors ${
                activeConvId === conv.id
                  ? 'bg-clay-accent/10 text-clay-accent font-medium'
                  : 'hover:bg-clay-muted/10 text-warmSilver'
              }`}
            >
              <span className="truncate">{convLabel(conv)}</span>
              <span
                role="button"
                aria-label="삭제"
                onClick={(e) => deleteConversation(conv.id, e)}
                className="opacity-0 group-hover:opacity-100 text-warmSilver hover:text-pomegranate-400 transition-opacity shrink-0"
              >
                <Trash2 size={13} />
              </span>
            </button>
          ))}
        </nav>

        {/* Footer */}
        <div className="px-4 py-3 border-t border-clay-border">
          <p className="text-[10px] text-warmSilver text-center">Powered by AgentBuilder</p>
        </div>
      </aside>

      {/* Chat area */}
      <main className="flex flex-col flex-1 min-w-0">
        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-6 py-6 space-y-4">
          {messages.length === 0 && (
            <div className="flex flex-col items-center justify-center h-full text-center gap-3 text-warmSilver">
              <span className="text-5xl">🤖</span>
              <p className="text-sm max-w-xs">
                {config?.welcome_message ?? '안녕하세요! 무엇을 도와드릴까요?'}
              </p>
            </div>
          )}

          {messages.map((msg, idx) => (
            <div
              key={idx}
              className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-[72%] px-4 py-3 rounded-2xl text-sm leading-relaxed ${
                  msg.role === 'user'
                    ? 'bg-clay-accent text-white rounded-br-sm'
                    : 'bg-clay-muted/15 text-clayBlack rounded-bl-sm'
                }`}
              >
                {msg.role === 'assistant' ? (
                  <div className="prose prose-sm max-w-none prose-p:my-1 prose-li:my-0.5">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                      {msg.content || (msg.isStreaming ? '▋' : '')}
                    </ReactMarkdown>
                  </div>
                ) : (
                  <span className="whitespace-pre-wrap">{msg.content}</span>
                )}
                {msg.isStreaming && msg.content && (
                  <span className="inline-block w-1 h-3.5 bg-current animate-pulse ml-0.5 align-middle" />
                )}
              </div>
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>

        {/* Input bar */}
        <div className="px-6 py-4 border-t border-clay-border bg-clay-surface">
          <div className="flex items-end gap-3 max-w-3xl mx-auto">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={sending}
              placeholder="메시지를 입력하세요… (Enter 전송, Shift+Enter 줄바꿈)"
              rows={1}
              className="flex-1 resize-none rounded-xl border border-clay-border bg-clay-bg px-4 py-2.5 text-sm placeholder:text-warmSilver focus:outline-none focus:ring-2 focus:ring-clay-accent/30 disabled:opacity-50 min-h-[42px] max-h-36 overflow-y-auto"
              style={{ fieldSizing: 'content' } as React.CSSProperties}
            />
            <button
              onClick={sendMessage}
              disabled={sending || !input.trim()}
              className="shrink-0 flex items-center justify-center w-10 h-10 rounded-xl bg-clay-accent text-white hover:opacity-90 disabled:opacity-40 transition-opacity"
              aria-label="전송"
            >
              <Send size={16} />
            </button>
          </div>
        </div>
      </main>
    </div>
  );
}
