'use client';

import { useEffect, useState } from 'react';
import { apiBase } from '@/lib/api';
import type { DocumentRead } from '@/lib/knowledge';
import { listDocuments } from '@/lib/knowledge';

type Event = {
  kb_id: string;
  document_id: string;
  status: 'processing' | 'done' | 'failed';
  chunks_done: number;
  chunks_total: number;
  error: string | null;
};

export function IngestionProgress({ kbId, initialDocuments }: { kbId: string; initialDocuments: DocumentRead[] }) {
  const [docs, setDocs] = useState<DocumentRead[]>(initialDocuments);
  const [progress, setProgress] = useState<Record<string, Event>>({});

  useEffect(() => {
    const es = new EventSource(`${apiBase()}/knowledge/${kbId}/ingestion/stream`);
    es.addEventListener('progress', async (ev) => {
      const evt = JSON.parse((ev as MessageEvent).data) as Event;
      setProgress((prev) => ({ ...prev, [evt.document_id]: evt }));
      if (evt.status === 'done' || evt.status === 'failed') {
        setDocs(await listDocuments(kbId));
      }
    });
    es.onerror = () => es.close();
    return () => es.close();
  }, [kbId]);

  if (docs.length === 0) {
    return <p className="text-sm text-clay-muted">업로드한 문서가 없어요.</p>;
  }

  return (
    <ul className="space-y-2">
      {docs.map((d) => {
        const p = progress[d.id];
        const pct = p && p.chunks_total > 0
          ? Math.round((p.chunks_done / p.chunks_total) * 100)
          : d.status === 'done' ? 100 : 0;
        return (
          <li key={d.id} className="rounded-xl border border-clay-border bg-clay-surface p-3">
            <div className="flex items-center justify-between text-sm">
              <span className="truncate">{d.filename}</span>
              <span className="text-clay-muted">{p?.status ?? d.status}</span>
            </div>
            <div className="mt-2 h-2 overflow-hidden rounded-full bg-clay-border">
              <div className="h-full bg-clay-accent transition-all" style={{ width: `${pct}%` }} />
            </div>
            {p?.error && <p className="mt-1 text-xs text-red-600">{p.error}</p>}
          </li>
        );
      })}
    </ul>
  );
}
