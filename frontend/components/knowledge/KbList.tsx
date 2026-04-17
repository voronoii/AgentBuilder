import Link from 'next/link';
import { BookOpen, File, Layers, Plus } from 'lucide-react';
import type { KnowledgeBase } from '@/lib/knowledge';

export function KbList({ items }: { items: KnowledgeBase[] }) {
  return (
    <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {items.map((kb) => (
        <li key={kb.id}>
          <Link
            href={`/knowledge/${kb.id}`}
            className="block rounded-card border border-clay-border bg-white p-4 transition-all hover:border-clay-accent hover:shadow-clay-2"
          >
            <div className="flex items-center gap-3 mb-3">
              <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-violet-50 text-violet-600">
                <BookOpen className="h-[18px] w-[18px]" />
              </div>
              <span className="text-sm font-semibold text-clayBlack">{kb.name}</span>
            </div>
            <p className="line-clamp-2 text-xs text-warmSilver mb-3">
              {kb.description || '설명 없음'}
            </p>
            <div className="flex gap-3 text-[11px] text-warmSilver">
              <span className="flex items-center gap-1">
                <File className="h-3 w-3" />
                {kb.embedding_provider}
              </span>
              <span className="flex items-center gap-1">
                <Layers className="h-3 w-3" />
                dim {kb.embedding_dim}
              </span>
            </div>
          </Link>
        </li>
      ))}
      {items.length === 0 && (
        <li className="sm:col-span-2 lg:col-span-3">
          <div className="rounded-card border border-dashed border-clay-border p-10 text-center">
            <Plus className="mx-auto h-10 w-10 text-clay-border mb-3" />
            <h4 className="text-sm font-semibold text-clay-text mb-1">지식베이스 추가</h4>
            <p className="text-xs text-warmSilver">
              파일을 업로드하여 에이전트의 지식을 구축하세요
            </p>
          </div>
        </li>
      )}
    </ul>
  );
}
