'use client';

import { Handle, Position, type NodeProps } from '@xyflow/react';
import { X } from 'lucide-react';

import type { NodeData, NodeType } from '@/lib/workflow';
import { useWorkflowStore } from '@/stores/workflowStore';
import { cn } from '@/lib/utils';

import { NODE_STYLES } from './nodeStyles';

interface BaseNodeProps {
  id: string;
  data: NodeData;
  selected?: boolean;
  showSourceHandle?: boolean;
  showTargetHandle?: boolean;
}

/** Render key settings as preview fields inside the node body. */
function FieldPreview({ data }: { data: NodeData }) {
  const fields: Array<{ label: string; value: string }> = [];
  const type = data.type as NodeType;

  if (type === 'llm' || type === 'agent') {
    if (data.provider) fields.push({ label: 'Provider', value: String(data.provider) });
    if (data.model) fields.push({ label: 'Model', value: String(data.model) });
  }
  if (type === 'agent' && data.maxIterations) {
    fields.push({ label: 'Max Iterations', value: String(data.maxIterations) });
  }
  if (type === 'knowledge_base') {
    if (data.topK) fields.push({ label: 'Top K', value: String(data.topK) });
  }
  if (type === 'prompt_template' && data.template) {
    const vars = String(data.template).match(/\{(\w+)\}/g);
    if (vars) {
      fields.push({ label: 'Variables', value: vars.join(', ') });
    }
  }
  if (type === 'input_guardrail') {
    if (data.checks && data.checks.length > 0) {
      fields.push({ label: 'Checks', value: data.checks.join(', ') });
    }
    if (data.provider) fields.push({ label: 'Judge LLM', value: `${data.provider}/${data.model || '?'}` });
  }

  if (fields.length === 0) return null;

  return (
    <div className="border-t border-oat-light px-3 py-2 space-y-1">
      {fields.map((f) => (
        <div key={f.label}>
          <div className="text-[10px] font-medium uppercase tracking-wide text-warmSilver">
            {f.label}
          </div>
          <div className="text-[11px] text-clay-text truncate">{f.value}</div>
        </div>
      ))}
    </div>
  );
}

export function BaseNode({
  id,
  data,
  selected,
  showSourceHandle = true,
  showTargetHandle = true,
}: BaseNodeProps) {
  const setSelectedNodeId = useWorkflowStore((s) => s.setSelectedNodeId);
  const removeNode = useWorkflowStore((s) => s.removeNode);
  const nodeType = data.type as NodeType;
  const style = NODE_STYLES[nodeType];
  const Icon = style.icon;

  return (
    <div
      className={cn(
        'relative min-w-[200px] rounded-card border bg-white shadow-clay-1 transition-all',
        selected
          ? 'border-clay-accent shadow-clay-focus'
          : 'border-clay-border',
      )}
      onClick={() => setSelectedNodeId(id)}
    >
      {showTargetHandle && (
        <Handle
          type="target"
          position={Position.Left}
          className="!w-3 !h-3 !bg-oat !border-2 !border-white !shadow-[0_0_0_1px_#dad4c8]"
        />
      )}

      {/* Header */}
      <div className="flex items-center gap-2 px-3 py-2.5">
        <div className={cn('h-2 w-2 rounded-full flex-shrink-0', style.dotColor)} />
        <Icon className="h-4 w-4 text-warmSilver flex-shrink-0" />
        <span className="text-xs font-semibold text-clayBlack flex-1 truncate">
          {data.label}
        </span>
        <button
          className="text-warmSilver hover:text-red-500 transition-colors"
          onClick={(e) => {
            e.stopPropagation();
            removeNode(id);
          }}
          aria-label="삭제"
        >
          <X className="h-3.5 w-3.5" />
        </button>
      </div>

      {/* Field preview */}
      <FieldPreview data={data} />

      {showSourceHandle && (
        <Handle
          type="source"
          position={Position.Right}
          className="!w-3 !h-3 !bg-oat !border-2 !border-white !shadow-[0_0_0_1px_#dad4c8]"
        />
      )}
    </div>
  );
}

// ---------- Typed wrappers ----------

export function ChatInputNode(props: NodeProps) {
  return (
    <BaseNode
      id={props.id}
      data={props.data as unknown as NodeData}
      selected={props.selected}
      showTargetHandle={false}
      showSourceHandle={true}
    />
  );
}

export function ChatOutputNode(props: NodeProps) {
  return (
    <BaseNode
      id={props.id}
      data={props.data as unknown as NodeData}
      selected={props.selected}
      showTargetHandle={true}
      showSourceHandle={false}
    />
  );
}

export function LLMNode(props: NodeProps) {
  return (
    <BaseNode
      id={props.id}
      data={props.data as unknown as NodeData}
      selected={props.selected}
    />
  );
}

export function AgentNode(props: NodeProps) {
  return (
    <BaseNode
      id={props.id}
      data={props.data as unknown as NodeData}
      selected={props.selected}
    />
  );
}

export function KnowledgeBaseNode(props: NodeProps) {
  return (
    <BaseNode
      id={props.id}
      data={props.data as unknown as NodeData}
      selected={props.selected}
    />
  );
}

export function PromptTemplateNode(props: NodeProps) {
  return (
    <BaseNode
      id={props.id}
      data={props.data as unknown as NodeData}
      selected={props.selected}
    />
  );
}

export function InputGuardrailNode(props: NodeProps) {
  return (
    <BaseNode
      id={props.id}
      data={props.data as unknown as NodeData}
      selected={props.selected}
    />
  );
}
