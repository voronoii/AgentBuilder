'use client';

import type { MCPServer, ToolMetadata } from '@/lib/mcp';

interface Props {
  server: MCPServer;
}

function ToolCard({ tool }: { tool: ToolMetadata }) {
  return (
    <div className="rounded-lg border border-clay-border bg-white px-2.5 py-2">
      <p className="text-xs font-semibold text-clay-text">{tool.name}</p>
      {tool.description && (
        <p className="mt-0.5 text-[11px] leading-snug text-clay-text opacity-60 line-clamp-2">
          {tool.description}
        </p>
      )}
    </div>
  );
}

export function ToolCatalog({ server }: Props) {
  const tools = server.discovered_tools;

  if (tools.length === 0) {
    return (
      <p className="text-xs text-clay-text opacity-50">
        {server.last_discovered_at ? '디스커버된 도구 없음' : '아직 디스커버리 미완료'}
      </p>
    );
  }

  return (
    <div className="mt-3 grid grid-cols-2 gap-1.5 sm:grid-cols-3">
      {tools.map((t) => (
        <ToolCard key={t.name} tool={t} />
      ))}
    </div>
  );
}
