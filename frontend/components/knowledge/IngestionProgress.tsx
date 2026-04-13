'use client';

import { useEffect, useRef, useState } from 'react';
import { Upload, Check, AlertCircle, FileText } from 'lucide-react';
import type { ChunkPreview, DocumentRead, KnowledgeConfig } from '@/lib/knowledge';
import {
  deleteDocument,
  getKnowledgeConfig,
  listDocumentChunks,
  listDocuments,
  uploadDocument,
} from '@/lib/knowledge';

type ProgressEvent = {
  document_id: string;
  status: 'processing' | 'done' | 'failed';
  chunks_done: number;
  chunks_total: number;
  error: string | null;
};

// SSE는 Next.js rewrite (/api/*) 를 통해 프록시. 원격 서버에서도 동작.
const SSE_BASE = '/api';

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
  const [config, setConfig] = useState<KnowledgeConfig | null>(null);
  const [chunks, setChunks] = useState<Record<string, ChunkPreview[]>>({});
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});
  const [deleting, setDeleting] = useState<Record<string, boolean>>({});
  const esRef = useRef<EventSource | null>(null);

  // config 로드 (지원 확장자, 최대 업로드 크기)
  useEffect(() => {
    getKnowledgeConfig()
      .then(setConfig)
      .catch(() => setConfig(null));
  }, []);

  // SSE 연결 — Next.js rewrite 경유
  useEffect(() => {
    const es = new EventSource(`${SSE_BASE}/knowledge/${kbId}/ingestion/stream`);
    esRef.current = es;
    es.addEventListener('progress', async (ev) => {
      const evt = JSON.parse((ev as MessageEvent).data) as ProgressEvent;
      setProgress((prev) => ({ ...prev, [evt.document_id]: evt }));
      if (evt.status === 'done' || evt.status === 'failed') {
        setDocs(await listDocuments(kbId));
      }
    });
    es.onerror = () => {};
    return () => es.close();
  }, [kbId]);

  // Fallback 폴링
  useEffect(() => {
    const hasInflight = docs.some((d) => d.status === 'pending' || d.status === 'processing');
    if (!hasInflight) return;
    const timer = setInterval(async () => {
      try {
        setDocs(await listDocuments(kbId));
      } catch {
        /* ignore */
      }
    }, 2000);
    return () => clearInterval(timer);
  }, [kbId, docs]);

  async function toggleChunks(docId: string) {
    const isOpen = !expanded[docId];
    setExpanded((prev) => ({ ...prev, [docId]: isOpen }));
    if (isOpen && !chunks[docId]) {
      try {
        const preview = await listDocumentChunks(kbId, docId, 3);
        setChunks((prev) => ({ ...prev, [docId]: preview }));
      } catch {
        setChunks((prev) => ({ ...prev, [docId]: [] }));
      }
    }
  }

  async function handleDelete(docId: string) {
    if (!confirm('이 문서와 관련된 모든 청크가 삭제됩니다. 계속할까요?')) return;
    setDeleting((prev) => ({ ...prev, [docId]: true }));
    try {
      await deleteDocument(kbId, docId);
      setDocs((prev) => prev.filter((d) => d.id !== docId));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setDeleting((prev) => ({ ...prev, [docId]: false }));
    }
  }

  async function handleFiles(files: FileList | File[]) {
    setError(null);
    setUploading(true);
    const maxBytes = config ? config.max_upload_mb * 1024 * 1024 : Infinity;
    for (const file of Array.from(files)) {
      if (file.size > maxBytes) {
        setError(`"${file.name}" 파일이 최대 ${config?.max_upload_mb}MB를 초과합니다.`);
        setUploading(false);
        return;
      }
      try {
        const doc = await uploadDocument(kbId, file);
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

  const acceptAttr = config ? config.supported_extensions.map((e) => `.${e}`).join(',') : undefined;

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
        <Upload className="mx-auto h-8 w-8 text-warmSilver mb-2" />
        <p className="text-sm text-clay-muted">
          {uploading ? '업로드 중...' : '파일을 여기로 끌어다 놓거나'}
        </p>
        <label className="mt-2 inline-flex cursor-pointer items-center gap-1.5 rounded-lg border border-clay-border bg-white px-3 py-1.5 text-sm text-clay-text hover:bg-oat-light transition-colors">
          파일 선택
          <input
            type="file"
            multiple
            accept={acceptAttr}
            className="hidden"
            disabled={uploading}
            onChange={(e) => e.target.files && void handleFiles(e.target.files)}
          />
        </label>
        {config && (
          <div className="mt-3 space-y-1 text-xs text-clay-muted">
            <p>
              <span className="font-medium">지원 형식:</span>{' '}
              {config.supported_extensions.map((e) => `.${e}`).join(', ')}
            </p>
            <p>
              <span className="font-medium">최대 크기:</span> {config.max_upload_mb}MB
            </p>
          </div>
        )}
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
            const isDone = status === 'done';
            const isFailed = status === 'failed';
            const isOpen = !!expanded[d.id];
            const docChunks = chunks[d.id];
            return (
              <li key={d.id} className="rounded-xl border border-clay-border bg-clay-surface p-3">
                <div className="flex items-center justify-between text-sm">
                  <div className="flex items-center gap-2 min-w-0">
                    <FileText className="h-4 w-4 shrink-0 text-warmSilver" />
                    <span className="truncate">{d.filename}</span>
                  </div>
                  <div className="ml-2 flex shrink-0 items-center gap-2">
                    {isDone && <Check className="h-3.5 w-3.5 text-emerald-500" />}
                    {isFailed && <AlertCircle className="h-3.5 w-3.5 text-red-400" />}
                    <span className="text-clay-muted">{status}</span>
                    <button
                      type="button"
                      onClick={() => void handleDelete(d.id)}
                      disabled={!!deleting[d.id]}
                      className="rounded px-1.5 py-0.5 text-xs text-red-400 hover:bg-red-50 hover:text-red-600 disabled:opacity-50"
                      title="문서 삭제"
                    >
                      {deleting[d.id] ? '삭제 중...' : '삭제'}
                    </button>
                  </div>
                </div>
                <div className="mt-2 h-2 overflow-hidden rounded-full bg-clay-border">
                  <div
                    className="h-full bg-clay-accent transition-all duration-300"
                    style={{ width: `${pct}%` }}
                  />
                </div>
                {p?.error && <p className="mt-1 text-xs text-red-600">{p.error}</p>}
                {isDone && (
                  <div className="mt-2">
                    <button
                      type="button"
                      onClick={() => void toggleChunks(d.id)}
                      className="text-xs text-clay-accent hover:underline"
                    >
                      {isOpen ? '청크 미리보기 숨기기' : '청크 미리보기'}
                    </button>
                    {isOpen && docChunks && (
                      <div className="mt-2 space-y-2">
                        {docChunks.length === 0 ? (
                          <p className="text-xs text-clay-muted">청크를 찾지 못했어요.</p>
                        ) : (
                          docChunks.map((c) => (
                            <div
                              key={c.chunk_index}
                              className="rounded-lg border border-clay-border bg-white p-2 text-xs text-clay-text"
                            >
                              <div className="mb-1 text-clay-muted">#{c.chunk_index}</div>
                              <div className="whitespace-pre-wrap break-words">
                                {c.text.length > 300 ? `${c.text.slice(0, 300)}…` : c.text}
                              </div>
                            </div>
                          ))
                        )}
                      </div>
                    )}
                  </div>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
