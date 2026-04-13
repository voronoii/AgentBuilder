'use client';

import type { Node } from '@xyflow/react';
import { useEffect, useState } from 'react';
import { X } from 'lucide-react';
import React from 'react';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Select } from '@/components/ui/select';
import { cn } from '@/lib/utils';
import { NODE_STYLES } from './nodes/nodeStyles';

import { apiBase } from '@/lib/api';
import type { NodeData, NodeType, Provider } from '@/lib/workflow';
import { fetchProviders } from '@/lib/workflow';
import { useWorkflowStore } from '@/stores/workflowStore';

interface KbOption {
  id: string;
  name: string;
}

function useProviders() {
  const [providers, setProviders] = useState<Provider[]>([]);
  useEffect(() => {
    fetchProviders().then(setProviders).catch(() => setProviders([]));
  }, []);
  return providers;
}

function useKnowledgeBases() {
  const [kbs, setKbs] = useState<KbOption[]>([]);
  useEffect(() => {
    fetch(`${apiBase()}/knowledge`)
      .then((r) => r.json())
      .then((data: Array<{ id: string; name: string }>) =>
        setKbs(data.map((kb) => ({ id: kb.id, name: kb.name }))),
      )
      .catch(() => setKbs([]));
  }, []);
  return kbs;
}

function LLMConfig({ data, onChange }: { data: NodeData; onChange: (d: Partial<NodeData>) => void }) {
  const providers = useProviders();
  const currentProvider = providers.find((p) => p.id === data.provider);

  return (
    <div className="space-y-3">
      <Field label="Provider">
        <Select
          value={data.provider || ''}
          onChange={(e) => onChange({ provider: e.target.value, model: '' })}
        >
          <option value="">선택...</option>
          {providers.filter((p) => p.enabled).map((p) => (
            <option key={p.id} value={p.id}>{p.name}</option>
          ))}
        </Select>
      </Field>
      <Field label="Model">
        <Select
          value={data.model || ''}
          onChange={(e) => onChange({ model: e.target.value })}
        >
          <option value="">선택...</option>
          {(currentProvider?.models || []).map((m) => (
            <option key={m.id} value={m.id}>{m.name}</option>
          ))}
        </Select>
      </Field>
      <Field label="Temperature">
        <Input
          type="number"
          min={0}
          max={2}
          step={0.1}
          value={data.temperature ?? 0.7}
          onChange={(e) => { const v = parseFloat(e.target.value); if (!Number.isNaN(v)) onChange({ temperature: v }); }}
        />
      </Field>
      <Field label="Max Tokens">
        <Input
          type="number"
          min={1}
          max={128000}
          value={data.maxTokens ?? 4096}
          onChange={(e) => { const v = parseInt(e.target.value); if (!Number.isNaN(v)) onChange({ maxTokens: v }); }}
        />
      </Field>
      <Field label="System Message">
        <Textarea
          value={data.systemMessage || ''}
          onChange={(e) => onChange({ systemMessage: e.target.value })}
          rows={3}
        />
      </Field>
    </div>
  );
}

function AgentConfig({ data, onChange }: { data: NodeData; onChange: (d: Partial<NodeData>) => void }) {
  const providers = useProviders();
  const kbs = useKnowledgeBases();
  const currentProvider = providers.find((p) => p.id === data.provider);
  const [mcpTools, setMcpTools] = useState<Array<{ name: string; server: string }>>([]);

  useEffect(() => {
    fetch(`${apiBase()}/mcp`)
      .then((r) => r.json())
      .then((servers: Array<{ name: string; discovered_tools: Array<{ name: string }> | null }>) => {
        const tools: Array<{ name: string; server: string }> = [];
        for (const srv of servers) {
          if (srv.discovered_tools) {
            for (const t of srv.discovered_tools) {
              tools.push({ name: t.name, server: srv.name });
            }
          }
        }
        setMcpTools(tools);
      })
      .catch(() => setMcpTools([]));
  }, []);

  const selectedTools = data.tools || [];
  const selectedKBs = data.knowledgeBases || [];
  const selectedKBIds = new Set(selectedKBs.map((kb) => kb.knowledgeBaseId));

  return (
    <div className="space-y-3">
      <Field label="Provider">
        <Select
          value={data.provider || ''}
          onChange={(e) => onChange({ provider: e.target.value, model: '' })}
        >
          <option value="">선택...</option>
          {providers.filter((p) => p.enabled).map((p) => (
            <option key={p.id} value={p.id}>{p.name}</option>
          ))}
        </Select>
      </Field>
      <Field label="Model">
        <Select
          value={data.model || ''}
          onChange={(e) => onChange({ model: e.target.value })}
        >
          <option value="">선택...</option>
          {(currentProvider?.models || []).map((m) => (
            <option key={m.id} value={m.id}>{m.name}</option>
          ))}
        </Select>
      </Field>
      <Field label="Instruction">
        <Textarea
          value={data.instruction || ''}
          onChange={(e) => onChange({ instruction: e.target.value })}
          rows={3}
        />
      </Field>
      <Field label="Max Iterations">
        <Input
          type="number"
          min={1}
          max={20}
          value={data.maxIterations ?? 5}
          onChange={(e) => { const v = parseInt(e.target.value); if (!Number.isNaN(v)) onChange({ maxIterations: v }); }}
        />
      </Field>
      <Field label="Knowledge Base">
        <div className="max-h-32 space-y-1 overflow-y-auto">
          {kbs.length === 0 ? (
            <p className="text-xs text-warmSilver">등록된 지식베이스 없음</p>
          ) : (
            kbs.map((kb) => (
              <label key={kb.id} className="flex items-center gap-2 text-xs">
                <input
                  type="checkbox"
                  checked={selectedKBIds.has(kb.id)}
                  onChange={(e) => {
                    const next = e.target.checked
                      ? [...selectedKBs, { knowledgeBaseId: kb.id, topK: 5, scoreThreshold: 0.0 }]
                      : selectedKBs.filter((k) => k.knowledgeBaseId !== kb.id);
                    onChange({ knowledgeBases: next });
                  }}
                />
                <span>{kb.name}</span>
              </label>
            ))
          )}
        </div>
      </Field>
      <Field label="MCP Tools">
        <div className="max-h-32 space-y-1 overflow-y-auto">
          {mcpTools.length === 0 ? (
            <p className="text-xs text-warmSilver">등록된 도구 없음</p>
          ) : (
            mcpTools.map((tool) => (
              <label key={tool.name} className="flex items-center gap-2 text-xs">
                <input
                  type="checkbox"
                  checked={selectedTools.includes(tool.name)}
                  onChange={(e) => {
                    const next = e.target.checked
                      ? [...selectedTools, tool.name]
                      : selectedTools.filter((t) => t !== tool.name);
                    onChange({ tools: next });
                  }}
                />
                <span>{tool.name}</span>
                <span className="text-warmSilver">({tool.server})</span>
              </label>
            ))
          )}
        </div>
      </Field>
    </div>
  );
}

function KnowledgeBaseConfig({ data, onChange }: { data: NodeData; onChange: (d: Partial<NodeData>) => void }) {
  const kbs = useKnowledgeBases();

  return (
    <div className="space-y-3">
      <Field label="Knowledge Base">
        <Select
          value={data.knowledgeBaseId || ''}
          onChange={(e) => onChange({ knowledgeBaseId: e.target.value })}
        >
          <option value="">선택...</option>
          {kbs.map((kb) => (
            <option key={kb.id} value={kb.id}>{kb.name}</option>
          ))}
        </Select>
      </Field>
      <Field label="Top K">
        <Input
          type="number"
          min={1}
          max={20}
          value={data.topK ?? 5}
          onChange={(e) => { const v = parseInt(e.target.value); if (!Number.isNaN(v)) onChange({ topK: v }); }}
        />
      </Field>
      <Field label="Score Threshold">
        <Input
          type="number"
          min={0}
          max={1}
          step={0.05}
          value={data.scoreThreshold ?? 0.0}
          onChange={(e) => { const v = parseFloat(e.target.value); if (!Number.isNaN(v)) onChange({ scoreThreshold: v }); }}
        />
      </Field>
    </div>
  );
}

function PromptTemplateConfig({ data, onChange }: { data: NodeData; onChange: (d: Partial<NodeData>) => void }) {
  const template = data.template || '';
  // Auto-extract {var} variables
  const vars = Array.from(new Set(template.match(/\{(\w+)\}/g)?.map((m) => m.slice(1, -1)) || []));

  return (
    <div className="space-y-3">
      <Field label="Template">
        <Textarea
          value={template}
          onChange={(e) => {
            const val = e.target.value;
            const extracted = Array.from(
              new Set(val.match(/\{(\w+)\}/g)?.map((m) => m.slice(1, -1)) || []),
            );
            onChange({ template: val, variables: extracted });
          }}
          rows={6}
          placeholder="변수는 {variable_name} 형식으로 사용합니다."
          className="font-mono text-xs"
        />
      </Field>
      {vars.length > 0 && (
        <div>
          <span className="text-xs font-medium text-clayBlack">감지된 변수:</span>
          <div className="mt-1 flex flex-wrap gap-1">
            {vars.map((v) => (
              <span
                key={v}
                className="rounded bg-lemon-400/30 px-2 py-0.5 text-xs text-lemon-800"
              >
                {v}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="mb-1 block text-[11px] font-semibold uppercase tracking-wide text-warmSilver">
        {label}
      </label>
      {children}
    </div>
  );
}

export function NodeConfigPanel({ node }: { node: Node }) {
  const updateNodeData = useWorkflowStore((s) => s.updateNodeData);
  const setSelectedNodeId = useWorkflowStore((s) => s.setSelectedNodeId);
  const data = node.data as unknown as NodeData;
  const nodeType = data.type;

  const handleChange = (partial: Partial<NodeData>) => {
    updateNodeData(node.id, partial);
  };

  return (
    <aside className="flex w-80 flex-col border-l border-clay-border bg-clay-surface">
      <div className="flex items-center gap-2 border-b border-clay-border px-4 py-3">
        <div className={cn('h-2 w-2 rounded-full', NODE_STYLES[nodeType].dotColor)} />
        {React.createElement(NODE_STYLES[nodeType].icon, { className: 'h-4 w-4 text-warmSilver' })}
        <span className="text-sm font-semibold text-clayBlack">{NODE_STYLES[nodeType].label}</span>
        <button onClick={() => setSelectedNodeId(null)} className="ml-auto text-warmSilver hover:text-clayBlack transition-colors">
          <X className="h-4 w-4" />
        </button>
      </div>
      <div className="flex-1 overflow-y-auto p-4">
        {/* Label */}
        <Field label="Label">
          <Input
            value={data.label}
            onChange={(e) => handleChange({ label: e.target.value })}
            className="mb-4"
          />
        </Field>

        {/* Type-specific config */}
        {(nodeType === 'llm') && (
          <LLMConfig data={data} onChange={handleChange} />
        )}
        {(nodeType === 'agent') && (
          <AgentConfig data={data} onChange={handleChange} />
        )}
        {(nodeType === 'knowledge_base') && (
          <KnowledgeBaseConfig data={data} onChange={handleChange} />
        )}
        {(nodeType === 'prompt_template') && (
          <PromptTemplateConfig data={data} onChange={handleChange} />
        )}
        {(nodeType === 'chat_input' || nodeType === 'chat_output') && (
          <p className="text-xs text-warmSilver">
            이 노드는 추가 설정이 필요 없습니다.
          </p>
        )}
      </div>
    </aside>
  );
}
