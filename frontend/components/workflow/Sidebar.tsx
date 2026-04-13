'use client';

import { Activity, LayoutGrid, Plug, X } from 'lucide-react';
import React, { useEffect, useState } from 'react';

import type { NodeType } from '@/lib/workflow';
import { apiBase } from '@/lib/api';
import { cn } from '@/lib/utils';
import { useSidebarStore } from '@/stores/sidebarStore';
import { useWorkflowStore } from '@/stores/workflowStore';

import { NODE_STYLES } from './nodes/nodeStyles';
import { RunLogPanel } from './RunLogPanel';

const NODE_TYPES: NodeType[] = [
  'chat_input',
  'chat_output',
  'llm',
  'agent',
  'knowledge_base',
  'prompt_template',
];

interface McpTool {
  name: string;
  description: string;
  server_name: string;
}

/** Stagger new nodes so they don't stack on top of each other. */
let _clickCount = 0;

function ComponentsPanel() {
  const [search, setSearch] = useState('');
  const addNode = useWorkflowStore((s) => s.addNode);

  const filtered = NODE_TYPES.filter((t) =>
    NODE_STYLES[t].label.toLowerCase().includes(search.toLowerCase()),
  );

  const handleClick = (type: NodeType) => {
    const offset = (_clickCount++ % 8) * 40;
    addNode(type, { x: 300 + offset, y: 150 + offset });
  };

  return (
    <div>
      <input
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        placeholder="노드 검색..."
        className="mb-3 w-full rounded border border-clay-border bg-white px-3 py-1.5 text-xs focus:outline-none focus:ring-2 focus:ring-clay-accent"
      />
      <div className="space-y-2">
        {filtered.map((type) => {
          const style = NODE_STYLES[type];
          const Icon = style.icon;
          return (
            <button
              key={type}
              type="button"
              onClick={() => handleClick(type)}
              className="flex w-full items-center gap-2 rounded-card border border-clay-border bg-white px-3 py-2 text-sm transition-all hover:border-clay-accent hover:shadow-clay-1 active:scale-[0.98]"
            >
              <div className={cn('h-2 w-2 rounded-full flex-shrink-0', style.dotColor)} />
              <Icon className="h-4 w-4 text-warmSilver" />
              <span className="font-medium text-clayBlack">{style.label}</span>
              <span className="ml-auto text-xs text-warmSilver">+</span>
            </button>
          );
        })}
        {filtered.length === 0 && (
          <p className="text-xs text-warmSilver">일치하는 노드가 없습니다.</p>
        )}
      </div>
    </div>
  );
}

function McpPanel() {
  const [tools, setTools] = useState<McpTool[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${apiBase()}/mcp`)
      .then((res) => res.json())
      .then((servers: Array<{ name: string; discovered_tools: Array<{ name: string; description: string }> | null }>) => {
        const allTools: McpTool[] = [];
        for (const srv of servers) {
          if (srv.discovered_tools) {
            for (const tool of srv.discovered_tools) {
              allTools.push({
                name: tool.name,
                description: tool.description || '',
                server_name: srv.name,
              });
            }
          }
        }
        setTools(allTools);
      })
      .catch(() => setTools([]))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <p className="text-xs text-warmSilver">로딩 중...</p>;

  if (tools.length === 0) {
    return (
      <p className="text-xs text-warmSilver">
        등록된 MCP 도구가 없습니다. 도구 페이지에서 MCP 서버를 추가하세요.
      </p>
    );
  }

  return (
    <div className="space-y-2">
      {tools.map((tool) => (
        <div
          key={`${tool.server_name}/${tool.name}`}
          className="rounded border border-clay-border bg-white px-3 py-2"
        >
          <p className="text-xs font-medium text-clayBlack">{tool.name}</p>
          <p className="text-xs text-warmSilver line-clamp-2">
            {tool.description}
          </p>
          <p className="mt-1 text-[10px] text-warmSilver">
            서버: {tool.server_name}
          </p>
        </div>
      ))}
    </div>
  );
}

interface SidebarProps {
  workflowId?: string;
}

function panelTitle(activePanel: string | null): { label: string; icon: React.ReactNode } {
  if (activePanel === 'components') return { label: '컴포넌트', icon: <LayoutGrid className="h-4 w-4" /> };
  if (activePanel === 'mcp') return { label: 'MCP 도구', icon: <Plug className="h-4 w-4" /> };
  if (activePanel === 'runlog') return { label: '실행 로그', icon: <Activity className="h-4 w-4" /> };
  return { label: '', icon: null };
}

export function Sidebar({ workflowId }: SidebarProps) {
  const { activePanel, close } = useSidebarStore();

  return (
    <aside className="flex w-64 flex-col border-r border-clay-border bg-clay-surface">
      <div className="flex items-center justify-between border-b border-clay-border px-4 py-2">
        <div className="flex items-center gap-2">
          {panelTitle(activePanel).icon}
          <span className="text-sm font-semibold text-clayBlack">
            {panelTitle(activePanel).label}
          </span>
        </div>
        <button
          onClick={close}
          aria-label="닫기"
          className="text-warmSilver hover:text-clayBlack transition-colors"
        >
          <X className="h-4 w-4" />
        </button>
      </div>
      <div className="flex-1 overflow-y-auto p-3">
        {activePanel === 'components' && <ComponentsPanel />}
        {activePanel === 'mcp' && <McpPanel />}
        {activePanel === 'runlog' && workflowId && <RunLogPanel workflowId={workflowId} />}
        {activePanel === 'runlog' && !workflowId && (
          <p className="text-xs text-warmSilver">워크플로우 ID가 없습니다.</p>
        )}
      </div>
    </aside>
  );
}
