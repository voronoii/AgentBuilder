'use client';

import { Handle, Position, type NodeProps } from '@xyflow/react';
import { Loader2, X } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';

import type { NodeData, NodeType } from '@/lib/workflow';
import { useWorkflowStore } from '@/stores/workflowStore';
import { cn } from '@/lib/utils';

import { NODE_STYLES } from './nodeStyles';

// 노드 활성 상태가 minMs 만큼 보이도록 보장. React 18 자동 배칭 + 60fps paint
// 사이클로 인해 짧은 활성 구간(예: 1.6초 안에 다 끝나는 sub-graph 사이클)이
// 그냥 묻혀버리는 문제를 방지한다.
function useStickyActive(rawActive: boolean, minMs: number = 1000): boolean {
  const [sticky, setSticky] = useState(false);
  const lastActivatedAtRef = useRef<number>(0);

  useEffect(() => {
    if (rawActive) {
      lastActivatedAtRef.current = Date.now();
      setSticky(true);
      return;
    }
    // raw가 false로 떨어진 시점부터 minMs 동안 sticky 유지
    const elapsed = Date.now() - lastActivatedAtRef.current;
    const remaining = minMs - elapsed;
    if (remaining <= 0) {
      setSticky(false);
      return;
    }
    const id = setTimeout(() => setSticky(false), remaining);
    return () => clearTimeout(id);
  }, [rawActive, minMs]);

  return sticky;
}

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
  if (type === 'output_guardrail') {
    if (data.checks && data.checks.length > 0) {
      fields.push({ label: 'Checks', value: data.checks.join(', ') });
    }
    if (data.action) fields.push({ label: 'Action', value: String(data.action) });
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
  const rawIsExecuting = useWorkflowStore((s) => s.executingNodeIds.has(id));
  const nodeType = data.type as NodeType;
  // ChatInput/ChatOutput은 실제 처리 단계가 아니라 입출력 게이트. sticky 1초를
  // 적용하면 백엔드 워밍업 동안 ChatInput만 활성으로 오래 보여 사용자에게
  // 잘못된 인식("ChatInput이 처리 중")을 줌. 처리 노드(Agent 등)에만 sticky.
  const isGateway = nodeType === 'chat_input' || nodeType === 'chat_output';
  const isExecuting = useStickyActive(rawIsExecuting, isGateway ? 0 : 1000);
  const style = NODE_STYLES[nodeType];
  const Icon = style.icon;

  return (
    <div
      className={cn(
        'relative min-w-[200px] rounded-card bg-white transition-shadow duration-200',
        // 활성 상태: 굵은 외곽선 + 보라색 ring(box-shadow) + pulse 애니메이션.
        // Dify 패턴 — 굵은 border + ring 조합으로 빠른 사이클에서도 paint 인지 보장.
        isExecuting
          ? 'border-2 border-clay-accent shadow-[0_0_0_4px_rgba(124,58,237,0.18)] animate-pulse'
          : selected
            ? 'border-2 border-clay-accent shadow-clay-focus'
            : 'border border-clay-border shadow-clay-1',
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
        {isExecuting && (
          <Loader2 className="h-3.5 w-3.5 flex-shrink-0 animate-spin text-clay-accent" />
        )}
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

export function OutputGuardrailNode(props: NodeProps) {
  return (
    <BaseNode
      id={props.id}
      data={props.data as unknown as NodeData}
      selected={props.selected}
    />
  );
}
