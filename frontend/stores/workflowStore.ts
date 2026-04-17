'use client';

import {
  type Edge,
  type Node,
  type OnConnect,
  type OnEdgesChange,
  type OnNodesChange,
  type XYPosition,
  addEdge,
  applyEdgeChanges,
  applyNodeChanges,
} from '@xyflow/react';
import { create } from 'zustand';

import type { NodeData, NodeType } from '@/lib/workflow';
import { fetchWorkflow, updateWorkflow } from '@/lib/workflow';
import { NODE_LABELS } from '@/components/workflow/nodes/nodeStyles';

function makeNodeId(): string {
  return `node_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`;
}

// Auto-save debounce
let _autoSaveTimer: ReturnType<typeof setTimeout> | null = null;
function _scheduleAutoSave(saveFn: () => Promise<void>, onError: (err: unknown) => void) {
  if (_autoSaveTimer) clearTimeout(_autoSaveTimer);
  _autoSaveTimer = setTimeout(() => {
    saveFn().catch(onError);
  }, 1500);
}

interface WorkflowStore {
  workflowId: string | null;
  workflowName: string;
  nodes: Node[];
  edges: Edge[];
  selectedNodeId: string | null;
  saveError: string | null;

  setSelectedNodeId: (id: string | null) => void;
  onNodesChange: OnNodesChange;
  onEdgesChange: OnEdgesChange;
  onConnect: OnConnect;
  addNode: (type: NodeType, position: XYPosition) => void;
  removeNode: (id: string) => void;
  updateNodeData: (id: string, data: Partial<NodeData>) => void;
  loadWorkflow: (id: string) => Promise<void>;
  saveWorkflow: () => Promise<void>;
  setWorkflowName: (name: string) => void;
  reset: () => void;
}

export const useWorkflowStore = create<WorkflowStore>((set, get) => ({
  workflowId: null,
  workflowName: '',
  nodes: [],
  edges: [],
  selectedNodeId: null,
  saveError: null,

  setSelectedNodeId: (id) => set({ selectedNodeId: id }),

  onNodesChange: (changes) => {
    set((state) => ({ nodes: applyNodeChanges(changes, state.nodes) }));
    if (get().workflowId) _scheduleAutoSave(get().saveWorkflow, (err) => set({ saveError: err instanceof Error ? err.message : '저장 실패' }));
  },

  onEdgesChange: (changes) => {
    set((state) => ({ edges: applyEdgeChanges(changes, state.edges) }));
    if (get().workflowId) _scheduleAutoSave(get().saveWorkflow, (err) => set({ saveError: err instanceof Error ? err.message : '저장 실패' }));
  },

  onConnect: (connection) => {
    set((state) => ({ edges: addEdge(connection, state.edges) }));
    if (get().workflowId) _scheduleAutoSave(get().saveWorkflow, (err) => set({ saveError: err instanceof Error ? err.message : '저장 실패' }));
  },

  addNode: (type, position) => {
    const id = makeNodeId();
    const newNode: Node = {
      id,
      type,
      position,
      data: {
        type,
        label: NODE_LABELS[type],
      } satisfies NodeData,
    };
    set((state) => ({ nodes: [...state.nodes, newNode] }));
    if (get().workflowId) _scheduleAutoSave(get().saveWorkflow, (err) => set({ saveError: err instanceof Error ? err.message : '저장 실패' }));
  },

  removeNode: (id) => {
    set((state) => ({
      nodes: state.nodes.filter((n) => n.id !== id),
      edges: state.edges.filter((e) => e.source !== id && e.target !== id),
      selectedNodeId: state.selectedNodeId === id ? null : state.selectedNodeId,
    }));
    if (get().workflowId) _scheduleAutoSave(get().saveWorkflow, (err) => set({ saveError: err instanceof Error ? err.message : '저장 실패' }));
  },

  updateNodeData: (id, data) => {
    set((state) => ({
      nodes: state.nodes.map((n) =>
        n.id === id ? { ...n, data: { ...n.data, ...data } } : n,
      ),
    }));
    if (get().workflowId) _scheduleAutoSave(get().saveWorkflow, (err) => set({ saveError: err instanceof Error ? err.message : '저장 실패' }));
  },

  loadWorkflow: async (id) => {
    const wf = await fetchWorkflow(id);
    set({
      workflowId: wf.id,
      workflowName: wf.name,
      nodes: wf.nodes as Node[],
      edges: wf.edges as Edge[],
      selectedNodeId: null,
    });
  },

  saveWorkflow: async () => {
    const { workflowId, workflowName, nodes, edges } = get();
    if (!workflowId) return;
    await updateWorkflow(workflowId, {
      name: workflowName,
      nodes: nodes as Array<Record<string, unknown>>,
      edges: edges as Array<Record<string, unknown>>,
    });
    set({ saveError: null });
  },

  setWorkflowName: (name) => set({ workflowName: name }),

  reset: () =>
    set({
      workflowId: null,
      workflowName: '',
      nodes: [],
      edges: [],
      selectedNodeId: null,
      saveError: null,
    }),
}));
