const SERVER_BASE = (process.env.API_URL_INTERNAL ?? 'http://localhost:28000').replace(/\/$/, '');
// 브라우저에서는 Next.js rewrite (/api/*) 를 통해 프록시
const BROWSER_BASE = '/api';

export function apiBase(): string {
  return typeof window === 'undefined' ? SERVER_BASE : BROWSER_BASE;
}

export type HealthResponse = { status: string; app: string; version: string };

export async function fetchHealth(): Promise<HealthResponse> {
  const res = await fetch(`${apiBase()}/health`, { cache: 'no-store' });
  if (!res.ok) throw new Error(`Health check failed: HTTP ${res.status}`);
  return (await res.json()) as HealthResponse;
}
