'use client';

import {
  Background,
  Controls,
  type EdgeTypes,
  type NodeTypes,
  ReactFlow,
  ReactFlowProvider,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { Activity, ChevronLeft, LayoutGrid, Play, Plug, Rocket, Save } from 'lucide-react';
import Link from 'next/link';
import { useCallback, useEffect, useState } from 'react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { useSidebarStore } from '@/stores/sidebarStore';
import { useWorkflowStore } from '@/stores/workflowStore';
import { fetchAppByWorkflow, type PublishedApp } from '@/lib/apps';
import { PublishModal } from '@/components/apps/PublishModal';
import { PublishManageModal } from '@/components/apps/PublishManageModal';

import { DeletableEdge } from './DeletableEdge';
import { NodeConfigPanel } from './NodeConfigPanel';
import { PlaygroundPanel } from './PlaygroundPanel';
import { Sidebar } from './Sidebar';
import {
  AgentNode,
  ChatInputNode,
  ChatOutputNode,
  InputGuardrailNode,
  KnowledgeBaseNode,
  LLMNode,
  PromptTemplateNode,
} from './nodes/BaseNode';

const nodeTypes: NodeTypes = {
  chat_input: ChatInputNode,
  chat_output: ChatOutputNode,
  llm: LLMNode,
  agent: AgentNode,
  knowledge_base: KnowledgeBaseNode,
  prompt_template: PromptTemplateNode,
  input_guardrail: InputGuardrailNode,
};

const edgeTypes: EdgeTypes = {
  default: DeletableEdge,
};

function EditorInner({ workflowId }: { workflowId: string }) {
  const {
    nodes,
    edges,
    selectedNodeId,
    workflowName,
    onNodesChange,
    onEdgesChange,
    onConnect,
    loadWorkflow,
    saveWorkflow,
    setSelectedNodeId,
  } = useWorkflowStore();

  const sidebarOpen = useSidebarStore((s) => s.isOpen);
  const toggleSidebar = useSidebarStore((s) => s.toggle);

  const [saving, setSaving] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState('');
  const [playgroundOpen, setPlaygroundOpen] = useState(false);
  const [publishedApp, setPublishedApp] = useState<PublishedApp | null>(null);
  const [showPublishModal, setShowPublishModal] = useState(false);
  const [showManageModal, setShowManageModal] = useState(false);

  useEffect(() => {
    loadWorkflow(workflowId)
      .then(() => setLoaded(true))
      .catch(() => setError('워크플로우를 불러올 수 없습니다.'));
  }, [workflowId, loadWorkflow]);

  useEffect(() => {
    if (workflowId) {
      fetchAppByWorkflow(workflowId).then(setPublishedApp).catch(() => {});
    }
  }, [workflowId]);

  const handleManualSave = useCallback(async () => {
    setSaving(true);
    try {
      await saveWorkflow();
    } catch {
      setError('저장에 실패했습니다.');
    } finally {
      setSaving(false);
    }
  }, [saveWorkflow]);

  const handlePaneClick = useCallback(() => {
    setSelectedNodeId(null);
  }, [setSelectedNodeId]);

  if (error) {
    return (
      <div className="flex h-screen items-center justify-center">
        <p className="text-red-500">{error}</p>
      </div>
    );
  }

  if (!loaded) {
    return (
      <div className="flex h-screen items-center justify-center">
        <p className="text-warmSilver">로딩 중...</p>
      </div>
    );
  }

  const selectedNode = selectedNodeId
    ? nodes.find((n) => n.id === selectedNodeId)
    : null;

  return (
    <div className="fixed inset-0 z-50 flex flex-col bg-cream">
      {/* Toolbar */}
      <header className="flex items-center border-b border-clay-border bg-clay-surface px-4 py-2">
        <Link
          href="/workflows"
          className="flex items-center gap-1 text-sm text-warmSilver hover:text-clayBlack transition-colors"
        >
          <ChevronLeft className="h-4 w-4" />
          목록
        </Link>
        <div className="mx-3 h-5 w-px bg-clay-border" />
        <span className="font-semibold text-clayBlack">{workflowName}</span>

        <div className="ml-auto flex items-center gap-1">
          <button
            onClick={() => toggleSidebar('components')}
            className={cn(
              'flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition-colors',
              sidebarOpen && useSidebarStore.getState().activePanel === 'components'
                ? 'bg-clayBlack text-white'
                : 'text-clay-text hover:bg-oat-light',
            )}
          >
            <LayoutGrid className="h-3.5 w-3.5" />
            컴포넌트
          </button>
          <button
            onClick={() => toggleSidebar('mcp')}
            className={cn(
              'flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition-colors',
              sidebarOpen && useSidebarStore.getState().activePanel === 'mcp'
                ? 'bg-clayBlack text-white'
                : 'text-clay-text hover:bg-oat-light',
            )}
          >
            <Plug className="h-3.5 w-3.5" />
            MCP
          </button>
          <button
            onClick={() => toggleSidebar('runlog')}
            className={cn(
              'flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition-colors',
              sidebarOpen && useSidebarStore.getState().activePanel === 'runlog'
                ? 'bg-clayBlack text-white'
                : 'text-clay-text hover:bg-oat-light',
            )}
          >
            <Activity className="h-3.5 w-3.5" />
            로그
          </button>

          <div className="mx-2 h-5 w-px bg-clay-border" />

          <button
            onClick={() => setPlaygroundOpen((v) => !v)}
            className={cn(
              'flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs font-medium transition-colors',
              playgroundOpen
                ? 'border-clay-accent bg-clay-accent text-white'
                : 'border-clay-accent text-clay-accent hover:bg-clay-accent/5',
            )}
          >
            <Play className="h-3.5 w-3.5" />
            실행
          </button>

          <div className="mx-2 h-5 w-px bg-clay-border" />

          <span className="flex items-center gap-1 text-[10px] text-warmSilver">
            <span className="h-1.5 w-1.5 rounded-full bg-clay-accent" />
            자동 저장
          </span>
          <Button
            onClick={handleManualSave}
            disabled={saving}
            size="sm"
            className="ml-1"
          >
            <Save className="h-3.5 w-3.5" />
            {saving ? '저장 중...' : '저장'}
          </Button>

          <div className="h-5 w-px bg-clay-border" />
          <button
            onClick={() => publishedApp ? setShowManageModal(true) : setShowPublishModal(true)}
            className="flex items-center gap-1.5 rounded-lg border border-clay-accent px-3 py-1.5 text-sm font-medium text-clay-accent hover:bg-clay-accent hover:text-white transition-colors"
          >
            <Rocket className="h-4 w-4" />
            {publishedApp ? '발행 관리' : '발행'}
          </button>
        </div>
      </header>

      {/* Canvas area */}
      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar */}
        {sidebarOpen && <Sidebar workflowId={workflowId} />}

        {/* React Flow canvas */}
        <div className="flex-1">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onPaneClick={handlePaneClick}
            nodeTypes={nodeTypes}
            edgeTypes={edgeTypes}
            defaultEdgeOptions={{ type: 'default' }}
            fitView
            className="bg-[#fafafa]"
          >
            <Background color="#c8c4bc" gap={20} size={1} />
            <Controls />
          </ReactFlow>
        </div>

        {/* Node config panel */}
        {selectedNode && !playgroundOpen && <NodeConfigPanel node={selectedNode} />}

        {/* Playground panel */}
        {playgroundOpen && (
          <PlaygroundPanel
            workflowId={workflowId}
            onClose={() => setPlaygroundOpen(false)}
          />
        )}
      </div>

      {showPublishModal && (
        <PublishModal
          workflowId={workflowId}
          workflowName={workflowName}
          onClose={() => setShowPublishModal(false)}
          onPublished={(appId) => {
            setShowPublishModal(false);
            fetchAppByWorkflow(workflowId).then(setPublishedApp).catch(() => {});
            window.open(`/chat/${appId}`, '_blank');
          }}
        />
      )}
      {showManageModal && publishedApp && (
        <PublishManageModal
          app={publishedApp}
          onClose={() => setShowManageModal(false)}
          onUnpublish={() => {
            setShowManageModal(false);
            setPublishedApp(null);
          }}
          onKeyRegenerated={setPublishedApp}
        />
      )}
    </div>
  );
}

export function WorkflowEditor({ workflowId }: { workflowId: string }) {
  return (
    <ReactFlowProvider>
      <EditorInner workflowId={workflowId} />
    </ReactFlowProvider>
  );
}
