const RAW_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';
const API_BASE = RAW_BASE.replace(/\/$/, '');

export type HealthResponse = {
  status: string;
  app: string;
  version: string;
};

export async function fetchHealth(): Promise<HealthResponse> {
  const res = await fetch(`${API_BASE}/health`, { cache: 'no-store' });
  if (!res.ok) {
    throw new Error(`Health check failed: HTTP ${res.status}`);
  }
  return (await res.json()) as HealthResponse;
}
