import { apiBase } from './api';

// ---------- Types ----------

export type NodeType =
  | 'chat_input'
  | 'chat_output'
  | 'llm'
  | 'agent'
  | 'knowledge_base'
  | 'prompt_template'
  | 'input_guardrail';

export interface NodeData {
  type: NodeType;
  label: string;
  // LLM / Agent
  provider?: string;
  model?: string;
  temperature?: number;
  maxTokens?: number;
  systemMessage?: string;
  // Agent
  strategy?: string;
  instruction?: string;
  maxIterations?: number;
  tools?: string[];
  knowledgeBases?: Array<{
    knowledgeBaseId: string;
    topK?: number;
    scoreThreshold?: number;
  }>;
  // Knowledge Base
  knowledgeBaseId?: string;
  topK?: number;
  scoreThreshold?: number;
  // Prompt Template
  template?: string;
  variables?: string[];
  // Input Guardrail
  checks?: string[];
  custom_rule?: string;
  heuristic_threshold?: number;
  action?: string;
}

export interface WorkflowRead {
  id: string;
  name: string;
  description: string;
  nodes: Array<Record<string, unknown>>;
  edges: Array<Record<string, unknown>>;
  created_at: string;
  updated_at: string;
}

export interface ProviderModel {
  id: string;
  name: string;
}

export interface Provider {
  id: string;
  name: string;
  enabled: boolean;
  models: ProviderModel[];
}

export interface ValidationWarning {
  code: string;
  message: string;
}

export interface ValidationResult {
  valid: boolean;
  warnings: ValidationWarning[];
}

// ---------- API ----------

export async function fetchWorkflows(): Promise<WorkflowRead[]> {
  const res = await fetch(`${apiBase()}/workflows`);
  if (!res.ok) throw new Error(`Failed to fetch workflows: ${res.status}`);
  return res.json();
}

export async function fetchWorkflow(id: string): Promise<WorkflowRead> {
  const res = await fetch(`${apiBase()}/workflows/${id}`);
  if (!res.ok) throw new Error(`Failed to fetch workflow: ${res.status}`);
  return res.json();
}

export async function createWorkflow(data: {
  name: string;
  description?: string;
}): Promise<WorkflowRead> {
  const res = await fetch(`${apiBase()}/workflows`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error(`Failed to create workflow: ${res.status}`);
  return res.json();
}

export async function updateWorkflow(
  id: string,
  data: {
    name?: string;
    description?: string;
    nodes?: Array<Record<string, unknown>>;
    edges?: Array<Record<string, unknown>>;
  },
): Promise<WorkflowRead> {
  const res = await fetch(`${apiBase()}/workflows/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error(`Failed to update workflow: ${res.status}`);
  return res.json();
}

export async function deleteWorkflow(id: string): Promise<void> {
  const res = await fetch(`${apiBase()}/workflows/${id}`, { method: 'DELETE' });
  if (!res.ok) throw new Error(`Failed to delete workflow: ${res.status}`);
}

export async function validateWorkflow(id: string): Promise<ValidationResult> {
  const res = await fetch(`${apiBase()}/workflows/${id}/validate`, {
    method: 'POST',
  });
  if (!res.ok) throw new Error(`Failed to validate workflow: ${res.status}`);
  return res.json();
}

export async function fetchProviders(): Promise<Provider[]> {
  const res = await fetch(`${apiBase()}/providers`);
  if (!res.ok) throw new Error(`Failed to fetch providers: ${res.status}`);
  return res.json();
}
