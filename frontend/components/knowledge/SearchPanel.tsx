'use client';

import { useState } from 'react';
import { searchKnowledgeBase, type SearchHit } from '@/lib/knowledge';

export function SearchPanel({ kbId }: { kbId: string }) {
  const [query, setQuery] = useState('');
  const [hits, setHits] = useState<SearchHit[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      setHits(await searchKnowledgeBase(kbId, query, 5));
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-4">
      <form onSubmit={onSubmit} className="flex gap-2">
        <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="검색어를 입력하세요"
          className="flex-1 rounded-lg border border-clay-border bg-white px-3 py-2" />
        <button type="submit" disabled={busy || !query.trim()}
          className="rounded-lg bg-clay-accent px-4 py-2 text-sm text-white disabled:opacity-50">
          검색
        </button>
      </form>
      {error && <p className="text-sm text-red-600">{error}</p>}
      <ul className="space-y-2">
        {hits.map((h, i) => (
          <li key={i} className="rounded-xl border border-clay-border bg-clay-surface p-3">
            <div className="flex items-center justify-between text-xs text-clay-muted">
              <span>{h.filename} · #{h.chunk_index}</span>
              <span>score {h.score.toFixed(3)}</span>
            </div>
            <p className="mt-2 line-clamp-4 whitespace-pre-wrap text-sm">{h.text}</p>
          </li>
        ))}
      </ul>
    </div>
  );
}
