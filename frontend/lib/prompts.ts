import { apiBase } from './api';

export interface AgentInstructionGenerateRequest {
  goal: string;
  /** Optional override. If omitted, the backend uses INSTRUCTION_GENERATOR_PROVIDER. */
  provider?: string;
  /** Optional override. If omitted, the backend uses INSTRUCTION_GENERATOR_MODEL. */
  model?: string;
  tone?: string;
  tool_policy?: string;
  unknown_handling?: string;
  output_language?: string;
  knowledge_bases?: string[];
  tools?: string[];
}

export interface AgentInstructionGenerateResponse {
  instruction: string;
  used_provider: string;
  used_model: string;
}

export async function generateAgentInstruction(
  request: AgentInstructionGenerateRequest,
  signal?: AbortSignal,
): Promise<AgentInstructionGenerateResponse> {
  const res = await fetch(`${apiBase()}/prompts/agent-instruction/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
    signal,
  });
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const body = (await res.json()) as { detail?: string };
      if (body.detail) detail = body.detail;
    } catch {
      // ignore JSON parse errors and fall back to status
    }
    throw new Error(detail);
  }
  return (await res.json()) as AgentInstructionGenerateResponse;
}
