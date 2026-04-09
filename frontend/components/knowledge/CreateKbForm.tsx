'use client';

import { useRouter } from 'next/navigation';
import { useState } from 'react';
import { createKnowledgeBase } from '@/lib/knowledge';

const DEFAULTS = {
  embedding_provider: 'local_hf',
  embedding_model: '/models/snowflake-arctic-embed-l-v2.0-ko',
  embedding_dim: 1024,
  chunk_size: 1000,
  chunk_overlap: 200,
};

export function CreateKbForm() {
  const router = useRouter();
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [advanced, setAdvanced] = useState(false);
  const [overrides, setOverrides] = useState(DEFAULTS);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const kb = await createKnowledgeBase({ name, description, ...overrides });
      router.push(`/knowledge/${kb.id}`);
    } catch (err) {
      setError((err as Error).message);
      setBusy(false);
    }
  }

  return (
    <form onSubmit={onSubmit} className="space-y-5">
      <label className="block space-y-1">
        <span className="text-sm">이름</span>
        <input required value={name} onChange={(e) => setName(e.target.value)}
          className="w-full rounded-lg border border-clay-border bg-white px-3 py-2" />
      </label>
      <label className="block space-y-1">
        <span className="text-sm">설명 (선택)</span>
        <textarea value={description} onChange={(e) => setDescription(e.target.value)}
          className="w-full rounded-lg border border-clay-border bg-white px-3 py-2" />
      </label>
      <button type="button" onClick={() => setAdvanced((a) => !a)} className="text-sm text-clay-muted underline">
        {advanced ? '고급 설정 접기' : '고급 설정 펼치기'}
      </button>
      {advanced && (
        <div className="grid gap-3 rounded-xl border border-clay-border p-4 text-sm">
          <label className="grid gap-1">
            <span>임베딩 제공자</span>
            <select value={overrides.embedding_provider}
              onChange={(e) => setOverrides({ ...overrides, embedding_provider: e.target.value })}
              className="rounded border border-clay-border px-2 py-1">
              <option value="local_hf">local_hf (기본, 한국어 최적)</option>
              <option value="fastembed">fastembed (CPU 폴백)</option>
            </select>
          </label>
          <label className="grid gap-1">
            <span>임베딩 모델</span>
            <input value={overrides.embedding_model}
              onChange={(e) => setOverrides({ ...overrides, embedding_model: e.target.value })}
              className="rounded border border-clay-border px-2 py-1" />
          </label>
          <label className="grid gap-1">
            <span>임베딩 차원</span>
            <input type="number" value={overrides.embedding_dim}
              onChange={(e) => setOverrides({ ...overrides, embedding_dim: Number(e.target.value) })}
              className="rounded border border-clay-border px-2 py-1" />
          </label>
          <div className="grid grid-cols-2 gap-3">
            <label className="grid gap-1">
              <span>chunk_size</span>
              <input type="number" value={overrides.chunk_size}
                onChange={(e) => setOverrides({ ...overrides, chunk_size: Number(e.target.value) })}
                className="rounded border border-clay-border px-2 py-1" />
            </label>
            <label className="grid gap-1">
              <span>chunk_overlap</span>
              <input type="number" value={overrides.chunk_overlap}
                onChange={(e) => setOverrides({ ...overrides, chunk_overlap: Number(e.target.value) })}
                className="rounded border border-clay-border px-2 py-1" />
            </label>
          </div>
        </div>
      )}
      {error && <p className="text-sm text-red-600">{error}</p>}
      <button type="submit" disabled={busy || !name.trim()}
        className="rounded-full bg-clay-accent px-5 py-2 text-white disabled:opacity-50">
        만들기
      </button>
    </form>
  );
}
