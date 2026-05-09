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

// 디버그용 — PlaygroundPanel SSE 이벤트를 실시간으로 푸시받아
// DebugEventPanel이 보여줄 수 있게 한다.
export interface DebugEvent {
  seq: number;            // 도착 순번
  receivedAt: number;     // 클라이언트 수신 ms 타임스탬프
  event_type: string;
  node_id?: string | null;
  payload?: Record<string, unknown> | null;
}

interface WorkflowStore {
  workflowId: string | null;
  workflowName: string;
  nodes: Node[];
  edges: Edge[];
  selectedNodeId: string | null;
  executingNodeIds: Set<string>;
  saveError: string | null;
  debugEvents: DebugEvent[];

  setSelectedNodeId: (id: string | null) => void;
  addExecutingNode: (id: string) => void;
  removeExecutingNode: (id: string) => void;
  clearExecutingNodes: () => void;
  pushDebugEvent: (ev: Omit<DebugEvent, 'seq' | 'receivedAt'>) => void;
  clearDebugEvents: () => void;
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
  executingNodeIds: new Set<string>(),
  saveError: null,
  debugEvents: [],

  setSelectedNodeId: (id) => set({ selectedNodeId: id }),

  addExecutingNode: (id) =>
    set((state) => {
      if (state.executingNodeIds.has(id)) return state;
      const next = new Set(state.executingNodeIds);
      next.add(id);
      return { executingNodeIds: next };
    }),
  removeExecutingNode: (id) =>
    set((state) => {
      if (!state.executingNodeIds.has(id)) return state;
      const next = new Set(state.executingNodeIds);
      next.delete(id);
      return { executingNodeIds: next };
    }),
  clearExecutingNodes: () =>
    set((state) =>
      state.executingNodeIds.size === 0 ? state : { executingNodeIds: new Set<string>() },
    ),

  pushDebugEvent: (ev) =>
    set((state) => {
      const seq = state.debugEvents.length === 0
        ? 1
        : state.debugEvents[state.debugEvents.length - 1].seq + 1;
      const next: DebugEvent = {
        seq,
        receivedAt: Date.now(),
        event_type: ev.event_type,
        node_id: ev.node_id ?? null,
        payload: ev.payload ?? null,
      };
      // 메모리 부담 방지 — 최근 500개만 유지
      const tail = state.debugEvents.length >= 500
        ? state.debugEvents.slice(-499)
        : state.debugEvents;
      return { debugEvents: [...tail, next] };
    }),
  clearDebugEvents: () => set({ debugEvents: [] }),

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
      executingNodeIds: new Set<string>(),
      saveError: null,
    }),
}));
