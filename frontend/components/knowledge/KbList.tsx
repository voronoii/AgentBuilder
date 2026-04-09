import Link from 'next/link';
import type { KnowledgeBase } from '@/lib/knowledge';

export function KbList({ items }: { items: KnowledgeBase[] }) {
  if (items.length === 0) {
    return (
      <div className="rounded-2xl border border-dashed border-clay-border p-10 text-center text-clay-muted">
        아직 지식베이스가 없어요. 오른쪽 위에서 하나 만들어 보세요.
      </div>
    );
  }
  return (
    <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {items.map((kb) => (
        <li key={kb.id}>
          <Link
            href={`/knowledge/${kb.id}`}
            className="block rounded-2xl border border-clay-border bg-clay-surface p-5 transition hover:border-clay-accent"
          >
            <h2 className="text-lg font-medium">{kb.name}</h2>
            <p className="mt-1 line-clamp-2 text-sm text-clay-muted">{kb.description || '—'}</p>
            <div className="mt-3 flex gap-3 text-xs text-clay-muted">
              <span>{kb.embedding_provider}</span>
              <span>dim {kb.embedding_dim}</span>
            </div>
          </Link>
        </li>
      ))}
    </ul>
  );
}
