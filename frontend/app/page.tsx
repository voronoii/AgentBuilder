import { fetchHealth } from '@/lib/api';

export const dynamic = 'force-dynamic';

export default async function HomePage() {
  let status: 'ok' | 'error' = 'error';
  let detail = 'unreachable';
  let version = '?';
  let appName = '?';

  try {
    const health = await fetchHealth();
    status = health.status === 'ok' ? 'ok' : 'error';
    detail = health.status;
    version = health.version;
    appName = health.app;
  } catch (err) {
    detail = err instanceof Error ? err.message : 'unknown error';
  }

  return (
    <main className="min-h-screen flex items-center justify-center p-8">
      <section className="bg-white border border-oat rounded-feature shadow-clay p-10 max-w-lg w-full">
        <h1 className="text-3xl font-semibold mb-6">AgentBuilder</h1>
        <dl className="space-y-2 text-sm">
          <div className="flex justify-between">
            <dt className="text-warmSilver">App</dt>
            <dd>{appName}</dd>
          </div>
          <div className="flex justify-between">
            <dt className="text-warmSilver">Version</dt>
            <dd>{version}</dd>
          </div>
          <div className="flex justify-between">
            <dt className="text-warmSilver">API</dt>
            <dd className={status === 'ok' ? 'text-matcha-600' : 'text-pomegranate-400'}>
              {detail}
            </dd>
          </div>
        </dl>
      </section>
    </main>
  );
}
