'use client';

import { useEffect, useRef, useState } from 'react';
import type { DocumentRead } from '@/lib/knowledge';
import { listDocuments, uploadDocument } from '@/lib/knowledge';

type ProgressEvent = {
  document_id: string;
  status: 'processing' | 'done' | 'failed';
  chunks_done: number;
  chunks_total: number;
  error: string | null;
};

// SSE는 Next.js rewrite 버퍼링을 피해 API를 직접 호출
const SSE_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:28000';

export function IngestionProgress({
  kbId,
  initialDocuments,
}: {
  kbId: string;
  initialDocuments: DocumentRead[];
}) {
  const [docs, setDocs] = useState<DocumentRead[]>(initialDocuments);
  const [progress, setProgress] = useState<Record<string, ProgressEvent>>({});
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const esRef = useRef<EventSource | null>(null);

  // SSE 연결 — API 직접 (rewrite 우회)
  useEffect(() => {
    const es = new EventSource(`${SSE_BASE}/knowledge/${kbId}/ingestion/stream`);
    esRef.current = es;
    es.addEventListener('progress', async (ev) => {
      const evt = JSON.parse((ev as MessageEvent).data) as ProgressEvent;
      setProgress((prev) => ({ ...prev, [evt.document_id]: evt }));
      if (evt.status === 'done' || evt.status === 'failed') {
        // 완료 시 목록 새로고침
        setDocs(await listDocuments(kbId));
      }
    });
    es.onerror = () => {};
    return () => es.close();
  }, [kbId]);

  async function handleFiles(files: FileList | File[]) {
    setError(null);
    setUploading(true);
    for (const file of Array.from(files)) {
      try {
        const doc = await uploadDocument(kbId, file);
        // 업로드 즉시 목록에 추가 (pending 상태)
        setDocs((prev) => {
          if (prev.find((d) => d.id === doc.id)) return prev;
          return [...prev, doc];
        });
      } catch (e) {
        setError((e as Error).message);
        setUploading(false);
        return;
      }
    }
    setUploading(false);
  }

  return (
    <div className="space-y-4">
      {/* 업로드 영역 */}
      <div
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          void handleFiles(e.dataTransfer.files);
        }}
        className={`rounded-2xl border-2 border-dashed p-8 text-center transition ${
          dragging ? 'border-clay-accent bg-clay-accent/5' : 'border-clay-border'
        }`}
      >
        <p className="text-sm text-clay-muted">
          {uploading ? '업로드 중...' : '파일을 여기로 끌어다 놓거나'}
        </p>
        <label className="mt-2 inline-block cursor-pointer rounded-full bg-clay-accent px-4 py-2 text-sm text-white">
          파일 선택
          <input
            type="file"
            multiple
            className="hidden"
            disabled={uploading}
            onChange={(e) => e.target.files && void handleFiles(e.target.files)}
          />
        </label>
        {error && <p className="mt-3 text-sm text-red-600">{error}</p>}
      </div>

      {/* 문서 목록 */}
      {docs.length === 0 ? (
        <p className="text-sm text-clay-muted">업로드한 문서가 없어요.</p>
      ) : (
        <ul className="space-y-2">
          {docs.map((d) => {
            const p = progress[d.id];
            const status = p?.status ?? d.status;
            const pct =
              p && p.chunks_total > 0
                ? Math.round((p.chunks_done / p.chunks_total) * 100)
                : status === 'done'
                ? 100
                : 0;
            return (
              <li key={d.id} className="rounded-xl border border-clay-border bg-clay-surface p-3">
                <div className="flex items-center justify-between text-sm">
                  <span className="truncate">{d.filename}</span>
                  <span className="ml-2 shrink-0 text-clay-muted">{status}</span>
                </div>
                <div className="mt-2 h-2 overflow-hidden rounded-full bg-clay-border">
                  <div
                    className="h-full bg-clay-accent transition-all duration-300"
                    style={{ width: `${pct}%` }}
                  />
                </div>
                {p?.error && <p className="mt-1 text-xs text-red-600">{p.error}</p>}
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
