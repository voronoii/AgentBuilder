'use client';

import React from 'react';
import { useState } from 'react';
import { Terminal, Globe, Zap, RefreshCw, Trash2, Power, Link as LinkIcon, Unlink } from 'lucide-react';
import type { MCPServer } from '@/lib/mcp';
import {
  deleteMcpServer,
  disconnectMcpOAuth,
  discoverTools,
  getMcpServer,
  startMcpOAuth,
  updateMcpServer,
} from '@/lib/mcp';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { ToolCatalog } from './ToolCatalog';

interface Props {
  servers: MCPServer[];
  onDeleted: (id: string) => void;
  onUpdated: (s: MCPServer) => void;
}

const TRANSPORT_LABEL: Record<string, string> = {
  stdio: 'STDIO',
  http_sse: 'HTTP/SSE',
  streamable_http: 'Streamable HTTP',
};

const TRANSPORT_ICON: Record<string, React.ReactNode> = {
  stdio: <Terminal className="h-[18px] w-[18px]" />,
  http_sse: <Globe className="h-[18px] w-[18px]" />,
  streamable_http: <Zap className="h-[18px] w-[18px]" />,
};

function ServerCard({
  server,
  onDeleted,
  onUpdated,
}: {
  server: MCPServer;
  onDeleted: (id: string) => void;
  onUpdated: (s: MCPServer) => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleToggle() {
    setBusy(true);
    setError(null);
    try {
      const updated = await updateMcpServer(server.id, { enabled: !server.enabled });
      onUpdated(updated);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : '토글 실패');
    } finally {
      setBusy(false);
    }
  }

  async function handleDelete() {
    if (!confirm(`"${server.name}" 서버를 삭제하시겠습니까?`)) return;
    setBusy(true);
    setError(null);
    try {
      await deleteMcpServer(server.id);
      onDeleted(server.id);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : '삭제 실패');
    } finally {
      setBusy(false);
    }
  }

  async function handleDiscover() {
    setBusy(true);
    setError(null);
    try {
      const updated = await discoverTools(server.id);
      onUpdated(updated);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : '디스커버리 실패');
    } finally {
      setBusy(false);
    }
  }

  async function handleConnectOAuth() {
    setBusy(true);
    setError(null);
    try {
      const { authorize_url } = await startMcpOAuth(server.id);
      const popup = window.open(authorize_url, 'mcp-oauth', 'width=520,height=720');
      if (!popup) {
        setError('팝업이 차단되었습니다. 팝업 허용 후 다시 시도하세요.');
        return;
      }
      // Wait for popup to close or for postMessage from callback page,
      // then refresh server state to pick up oauth_connected + discovered tools.
      await new Promise<void>((resolve) => {
        const onMsg = (ev: MessageEvent) => {
          if (ev.data && ev.data.type === 'mcp-oauth') {
            window.removeEventListener('message', onMsg);
            clearInterval(t);
            resolve();
          }
        };
        window.addEventListener('message', onMsg);
        const t = setInterval(() => {
          if (popup.closed) {
            window.removeEventListener('message', onMsg);
            clearInterval(t);
            resolve();
          }
        }, 500);
      });
      // Poll once or twice — discovery runs as a backend background task.
      for (let i = 0; i < 4; i++) {
        const fresh = await getMcpServer(server.id);
        onUpdated(fresh);
        if (fresh.oauth_connected) break;
        await new Promise((r) => setTimeout(r, 750));
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'OAuth 연결 실패');
    } finally {
      setBusy(false);
    }
  }

  async function handleDisconnectOAuth() {
    if (!confirm('OAuth 연결을 끊으시겠습니까? 이후 도구 호출 전에 다시 연결해야 합니다.')) return;
    setBusy(true);
    setError(null);
    try {
      const updated = await disconnectMcpOAuth(server.id);
      onUpdated(updated);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'OAuth 연결 해제 실패');
    } finally {
      setBusy(false);
    }
  }

  const isOAuth = server.auth_type === 'oauth';

  return (
    <div className="rounded-xl border border-clay-border bg-clay-surface p-4 shadow-sm">
      {/* Header */}
      <div className="flex items-start justify-between gap-3">
        <button
          onClick={() => setExpanded((v) => !v)}
          className="flex min-w-0 flex-1 items-center gap-2 text-left"
        >
          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-clay-bg text-clay-text">
            {TRANSPORT_ICON[server.transport] ?? <Power className="h-[18px] w-[18px]" />}
          </span>
          <div className="min-w-0">
            <p className="truncate font-medium text-clay-text">{server.name}</p>
            <p className="text-xs text-clay-text opacity-50">
              {TRANSPORT_LABEL[server.transport] ?? server.transport} ·{' '}
              {server.discovered_tools.length}개 도구
            </p>
          </div>
        </button>

        {/* Actions */}
        <div className="flex shrink-0 items-center gap-2">
          <Badge variant={server.enabled ? 'success' : 'default'}>
            {server.enabled ? 'Active' : 'Inactive'}
          </Badge>
          {isOAuth && (
            <Badge variant={server.oauth_connected ? 'success' : 'default'}>
              {server.oauth_connected ? 'OAuth 연결됨' : 'OAuth 연결 필요'}
            </Badge>
          )}
          {isOAuth && !server.oauth_connected && (
            <Button variant="outline" size="sm" onClick={handleConnectOAuth} disabled={busy}>
              <LinkIcon className="h-3.5 w-3.5 mr-1" />
              연결
            </Button>
          )}
          {isOAuth && server.oauth_connected && (
            <Button
              variant="outline"
              size="sm"
              onClick={handleDisconnectOAuth}
              disabled={busy}
              title="OAuth 연결 해제"
            >
              <Unlink className="h-3.5 w-3.5" />
            </Button>
          )}
          <Button
            variant="outline"
            size="sm"
            onClick={handleToggle}
            disabled={busy}
          >
            {server.enabled ? '비활성화' : '활성화'}
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={handleDiscover}
            disabled={busy}
            title="도구 재디스커버리"
          >
            <RefreshCw className="h-3.5 w-3.5" />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={handleDelete}
            disabled={busy}
            className="text-red-500 hover:text-red-600 hover:bg-red-50"
          >
            <Trash2 className="h-3.5 w-3.5" />
          </Button>
        </div>
      </div>

      {error && <p className="mt-2 text-xs text-red-500">{error}</p>}

      {/* Tool catalog (expandable) */}
      {expanded && (
        <div className="mt-3 border-t border-clay-border pt-3">
          {server.description && (
            <p className="mb-2 text-xs text-clay-text opacity-60">{server.description}</p>
          )}
          <ToolCatalog server={server} />
          {server.last_discovered_at && (
            <p className="mt-2 text-xs text-clay-text opacity-40">
              마지막 디스커버리: {new Date(server.last_discovered_at).toLocaleString('ko-KR')}
            </p>
          )}
        </div>
      )}
    </div>
  );
}

export function McpServerList({ servers, onDeleted, onUpdated }: Props) {
  if (servers.length === 0) {
    return (
      <div className="rounded-xl border border-dashed border-clay-border bg-clay-bg py-12 text-center">
        <p className="text-sm text-clay-text opacity-50">등록된 MCP 서버가 없습니다.</p>
        <p className="mt-1 text-xs text-clay-text opacity-40">
          + 새 MCP 서버 버튼으로 추가하세요.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {servers.map((s) => (
        <ServerCard key={s.id} server={s} onDeleted={onDeleted} onUpdated={onUpdated} />
      ))}
    </div>
  );
}
