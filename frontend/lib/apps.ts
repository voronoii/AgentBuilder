import { apiBase } from './api';

export interface PublishedApp {
  id: string;
  workflow_id: string;
  name: string;
  description: string;
  icon_url: string | null;
  welcome_message: string;
  placeholder_text: string;
  api_key: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface AppConfig {
  id: string;
  name: string;
  description: string;
  icon_url: string | null;
  welcome_message: string;
  placeholder_text: string;
}

export interface AppCreatePayload {
  workflow_id: string;
  name: string;
  description?: string;
  welcome_message?: string;
  placeholder_text?: string;
  icon_url?: string | null;
}

export interface AppUpdatePayload {
  name?: string;
  description?: string;
  welcome_message?: string;
  placeholder_text?: string;
  icon_url?: string | null;
}

export async function fetchApps(): Promise<PublishedApp[]> {
  const res = await fetch(`${apiBase()}/apps`);
  if (!res.ok) throw new Error(`Failed to fetch apps: ${res.status}`);
  return res.json();
}

export async function fetchApp(id: string): Promise<PublishedApp> {
  const res = await fetch(`${apiBase()}/apps/${id}`);
  if (!res.ok) throw new Error(`Failed to fetch app: ${res.status}`);
  return res.json();
}

export async function publishApp(data: AppCreatePayload): Promise<PublishedApp> {
  const res = await fetch(`${apiBase()}/apps`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => null);
    throw new Error(err?.detail || `Failed to publish app: ${res.status}`);
  }
  return res.json();
}

export async function updateApp(id: string, data: AppUpdatePayload): Promise<PublishedApp> {
  const res = await fetch(`${apiBase()}/apps/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error(`Failed to update app: ${res.status}`);
  return res.json();
}

export async function deleteApp(id: string): Promise<void> {
  const res = await fetch(`${apiBase()}/apps/${id}`, { method: 'DELETE' });
  if (!res.ok) throw new Error(`Failed to delete app: ${res.status}`);
}

export async function toggleApp(id: string): Promise<PublishedApp> {
  const res = await fetch(`${apiBase()}/apps/${id}/toggle`, { method: 'PUT' });
  if (!res.ok) throw new Error(`Failed to toggle app: ${res.status}`);
  return res.json();
}

export async function regenerateKey(id: string): Promise<PublishedApp> {
  const res = await fetch(`${apiBase()}/apps/${id}/regenerate-key`, { method: 'POST' });
  if (!res.ok) throw new Error(`Failed to regenerate key: ${res.status}`);
  return res.json();
}

export async function fetchAppConfig(id: string): Promise<AppConfig> {
  const res = await fetch(`${apiBase()}/apps/${id}/config`);
  if (!res.ok) throw new Error(`Failed to fetch app config: ${res.status}`);
  return res.json();
}

export async function fetchAppByWorkflow(workflowId: string): Promise<PublishedApp | null> {
  const apps = await fetchApps();
  return apps.find((a) => a.workflow_id === workflowId) ?? null;
}
