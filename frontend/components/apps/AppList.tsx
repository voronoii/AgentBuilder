'use client';

import { useCallback, useEffect, useState } from 'react';
import { AppWindow, ExternalLink, ToggleLeft, ToggleRight, Trash2 } from 'lucide-react';

import { type PublishedApp, fetchApps, toggleApp, deleteApp } from '@/lib/apps';
import { Badge } from '@/components/ui/badge';

export function AppListClient() {
  const [apps, setApps] = useState<PublishedApp[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    try {
      const data = await fetchApps();
      setApps(data);
    } catch {
      setError('앱 목록을 불러올 수 없습니다.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleToggle = async (id: string) => {
    try {
      const updated = await toggleApp(id);
      setApps((prev) => prev.map((a) => (a.id === id ? updated : a)));
    } catch {
      setError('앱 상태 변경에 실패했습니다.');
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm('이 앱을 삭제하시겠습니까?')) return;
    try {
      await deleteApp(id);
      setApps((prev) => prev.filter((a) => a.id !== id));
    } catch {
      setError('앱 삭제에 실패했습니다.');
    }
  };

  if (loading) {
    return <p className="text-warmSilver">로딩 중...</p>;
  }

  return (
    <div>
      {error && (
        <p className="mb-4 rounded-card border border-red-200 bg-red-50 px-4 py-2 text-sm text-red-600">
          {error}
        </p>
      )}

      {apps.length === 0 ? (
        <div className="flex flex-col items-center justify-center gap-3 rounded-card border-2 border-dashed border-clay-border py-16 text-center">
          <AppWindow className="h-10 w-10 text-warmSilver" />
          <p className="text-sm text-warmSilver">게시된 앱이 없습니다.</p>
          <p className="text-xs text-warmSilver">워크플로우 편집기에서 앱으로 게시할 수 있습니다.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {apps.map((app) => (
            <AppCard
              key={app.id}
              app={app}
              onToggle={handleToggle}
              onDelete={handleDelete}
            />
          ))}
        </div>
      )}
    </div>
  );
}

interface AppCardProps {
  app: PublishedApp;
  onToggle: (id: string) => void;
  onDelete: (id: string) => void;
}

function AppCard({ app, onToggle, onDelete }: AppCardProps) {
  const initial = app.name.charAt(0).toUpperCase();

  return (
    <div className="rounded-card border border-clay-border bg-white p-4 shadow-clay transition-all hover:border-clay-accent hover:shadow-clay-2">
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-3 min-w-0">
          {app.icon_url ? (
            <img
              src={app.icon_url}
              alt={app.name}
              className="h-9 w-9 shrink-0 rounded-lg object-cover"
            />
          ) : (
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-clay-accent/10 text-clay-accent font-semibold text-sm">
              {initial}
            </div>
          )}
          <div className="min-w-0">
            <h3 className="font-semibold text-clayBlack truncate">{app.name}</h3>
            <Badge variant={app.is_active ? 'success' : 'outline'} className="mt-0.5">
              {app.is_active ? '활성' : '비활성'}
            </Badge>
          </div>
        </div>
      </div>

      {app.description && (
        <p className="mt-2 text-sm text-warmSilver line-clamp-2">{app.description}</p>
      )}

      <div className="mt-3 flex items-center gap-2 border-t border-clay-border pt-3">
        <a
          href={`/chat/${app.id}`}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-xs font-medium text-warmSilver hover:bg-oat-light hover:text-clayBlack transition-colors"
          title="앱 열기"
        >
          <ExternalLink className="h-3.5 w-3.5" />
          열기
        </a>

        <button
          onClick={() => onToggle(app.id)}
          className="inline-flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-xs font-medium text-warmSilver hover:bg-oat-light hover:text-clayBlack transition-colors"
          title={app.is_active ? '비활성화' : '활성화'}
        >
          {app.is_active ? (
            <ToggleRight className="h-3.5 w-3.5 text-green-600" />
          ) : (
            <ToggleLeft className="h-3.5 w-3.5" />
          )}
          {app.is_active ? '비활성화' : '활성화'}
        </button>

        <button
          onClick={() => onDelete(app.id)}
          className="ml-auto inline-flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-xs font-medium text-warmSilver hover:bg-red-50 hover:text-red-500 transition-colors"
          title="삭제"
        >
          <Trash2 className="h-3.5 w-3.5" />
          삭제
        </button>
      </div>
    </div>
  );
}
