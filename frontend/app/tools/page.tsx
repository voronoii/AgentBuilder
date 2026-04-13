'use client';

import { useEffect, useState } from 'react';
import type { MCPServer } from '@/lib/mcp';
import { listMcpServers } from '@/lib/mcp';
import { McpServerList } from '@/components/mcp/McpServerList';
import { RegisterMcpModal } from '@/components/mcp/RegisterMcpModal';

export default function ToolsPage() {
  const [servers, setServers] = useState<MCPServer[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listMcpServers()
      .then(setServers)
      .catch((e: unknown) =>
        setError(e instanceof Error ? e.message : '서버 목록 로드 실패'),
      )
      .finally(() => setLoading(false));
  }, []);

  function handleCreated(server: MCPServer) {
    setServers((prev) => [server, ...prev]);
    setShowModal(false);
  }

  function handleDeleted(id: string) {
    setServers((prev) => prev.filter((s) => s.id !== id));
  }

  function handleUpdated(updated: MCPServer) {
    setServers((prev) => prev.map((s) => (s.id === updated.id ? updated : s)));
  }

  return (
    <section className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-clay-text">도구 (MCP 서버)</h1>
        <button
          onClick={() => setShowModal(true)}
          className="rounded-full bg-clay-accent px-4 py-2 text-sm font-medium text-white hover:opacity-90"
        >
          + 새 MCP 서버
        </button>
      </div>

      {loading && (
        <p className="text-sm text-clay-text opacity-50">불러오는 중…</p>
      )}
      {error && (
        <p className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-600">{error}</p>
      )}
      {!loading && !error && (
        <McpServerList servers={servers} onDeleted={handleDeleted} onUpdated={handleUpdated} />
      )}

      {showModal && (
        <RegisterMcpModal
          onClose={() => setShowModal(false)}
          onCreated={handleCreated}
        />
      )}
    </section>
  );
}
