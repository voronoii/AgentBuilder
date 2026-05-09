import { apiBase } from './api';

export type MCPTransport = 'stdio' | 'http_sse' | 'streamable_http';
export type MCPAuthType = 'none' | 'oauth';

export type ToolMetadata = {
  name: string;
  description: string;
  input_schema: Record<string, unknown>;
};

export type MCPServer = {
  id: string;
  name: string;
  description: string;
  transport: MCPTransport;
  config: Record<string, unknown>;
  env_vars: Record<string, string>;
  enabled: boolean;
  discovered_tools: ToolMetadata[];
  last_discovered_at: string | null;
  created_at: string;
  updated_at: string;
  auth_type: MCPAuthType;
  oauth_connected: boolean;
  oauth_token_expires_at: string | null;
};

export type MCPServerCreate = {
  name: string;
  description?: string;
  transport: MCPTransport;
  config: Record<string, unknown>;
  env_vars?: Record<string, string>;
  auth_type?: MCPAuthType;
};

export type MCPServerUpdate = {
  name?: string;
  description?: string;
  config?: Record<string, unknown>;
  env_vars?: Record<string, string>;
  enabled?: boolean;
};

export async function listMcpServers(): Promise<MCPServer[]> {
  const res = await fetch(`${apiBase()}/mcp`, { cache: 'no-store' });
  if (!res.ok) throw new Error(`listMcpServers failed: HTTP ${res.status}`);
  return (await res.json()) as MCPServer[];
}

export async function getMcpServer(id: string): Promise<MCPServer> {
  const res = await fetch(`${apiBase()}/mcp/${id}`, { cache: 'no-store' });
  if (!res.ok) throw new Error(`getMcpServer failed: HTTP ${res.status}`);
  return (await res.json()) as MCPServer;
}

export async function createMcpServer(body: MCPServerCreate): Promise<MCPServer> {
  const res = await fetch(`${apiBase()}/mcp`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await res.text());
  return (await res.json()) as MCPServer;
}

export async function updateMcpServer(id: string, body: MCPServerUpdate): Promise<MCPServer> {
  const res = await fetch(`${apiBase()}/mcp/${id}`, {
    method: 'PUT',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await res.text());
  return (await res.json()) as MCPServer;
}

export async function deleteMcpServer(id: string): Promise<void> {
  const res = await fetch(`${apiBase()}/mcp/${id}`, { method: 'DELETE' });
  if (!res.ok) throw new Error(`deleteMcpServer failed: HTTP ${res.status}`);
}

export async function discoverTools(id: string): Promise<MCPServer> {
  const res = await fetch(`${apiBase()}/mcp/${id}/discover`, { method: 'POST' });
  if (!res.ok) throw new Error(await res.text());
  return (await res.json()) as MCPServer;
}

export type OAuthStartResponse = { authorize_url: string };
export type OAuthStatus = { connected: boolean; expires_at: string | null };

export async function startMcpOAuth(id: string): Promise<OAuthStartResponse> {
  const res = await fetch(`${apiBase()}/mcp/${id}/oauth/start`, { method: 'POST' });
  if (!res.ok) throw new Error(await res.text());
  return (await res.json()) as OAuthStartResponse;
}

export async function getMcpOAuthStatus(id: string): Promise<OAuthStatus> {
  const res = await fetch(`${apiBase()}/mcp/${id}/oauth/status`, { cache: 'no-store' });
  if (!res.ok) throw new Error(`getMcpOAuthStatus failed: HTTP ${res.status}`);
  return (await res.json()) as OAuthStatus;
}

export async function disconnectMcpOAuth(id: string): Promise<MCPServer> {
  const res = await fetch(`${apiBase()}/mcp/${id}/oauth/disconnect`, { method: 'POST' });
  if (!res.ok) throw new Error(await res.text());
  return (await res.json()) as MCPServer;
}
