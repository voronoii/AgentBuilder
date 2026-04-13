import { apiBase } from './api';

export interface AppSetting {
  key: string;
  value: string;
  description: string;
  category: string;
  is_secret: boolean;
  updated_at: string;
}

export async function fetchSettings(): Promise<AppSetting[]> {
  const res = await fetch(`${apiBase()}/settings`);
  if (!res.ok) throw new Error(`Failed to fetch settings: ${res.status}`);
  return res.json();
}

export async function updateSetting(
  key: string,
  value: string,
): Promise<AppSetting> {
  const res = await fetch(`${apiBase()}/settings/${encodeURIComponent(key)}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ value }),
  });
  if (!res.ok) throw new Error(`Failed to update setting: ${res.status}`);
  return res.json();
}

export interface SettingCreatePayload {
  key: string;
  value?: string;
  description?: string;
  category?: string;
  is_secret?: boolean;
}

export async function createSetting(
  payload: SettingCreatePayload,
): Promise<AppSetting> {
  const res = await fetch(`${apiBase()}/settings`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to create setting: ${res.status}`);
  }
  return res.json();
}

export async function deleteSetting(key: string): Promise<void> {
  const res = await fetch(`${apiBase()}/settings/${encodeURIComponent(key)}`, {
    method: 'DELETE',
  });
  if (!res.ok && res.status !== 204) {
    throw new Error(`Failed to delete setting: ${res.status}`);
  }
}

export async function bulkUpdateSettings(
  settings: Record<string, string>,
): Promise<AppSetting[]> {
  const res = await fetch(`${apiBase()}/settings`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ settings }),
  });
  if (!res.ok) throw new Error(`Failed to update settings: ${res.status}`);
  return res.json();
}
