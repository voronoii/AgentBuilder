const BROWSER_BASE = (process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:28000').replace(/\/$/, '');
const SERVER_BASE = (process.env.API_URL_INTERNAL ?? BROWSER_BASE).replace(/\/$/, '');

export function apiBase(): string {
  return typeof window === 'undefined' ? SERVER_BASE : BROWSER_BASE;
}

export type HealthResponse = { status: string; app: string; version: string };

export async function fetchHealth(): Promise<HealthResponse> {
  const res = await fetch(`${apiBase()}/health`, { cache: 'no-store' });
  if (!res.ok) throw new Error(`Health check failed: HTTP ${res.status}`);
  return (await res.json()) as HealthResponse;
}
