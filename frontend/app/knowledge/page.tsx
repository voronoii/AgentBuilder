import Link from 'next/link';
import { Plus } from 'lucide-react';
import { KbList } from '@/components/knowledge/KbList';
import { listKnowledgeBases, type KnowledgeBase } from '@/lib/knowledge';

export const dynamic = 'force-dynamic';

export default async function KnowledgePage() {
  let kbs: KnowledgeBase[] = [];
  try {
    kbs = await listKnowledgeBases();
  } catch {
    kbs = [];
  }
  return (
    <section className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">지식베이스</h1>
        <Link
          href="/knowledge/new"
          className="inline-flex items-center gap-1.5 rounded-lg bg-clay-accent px-4 py-2 text-sm font-medium text-white hover:opacity-90 transition-opacity"
        >
          <Plus className="h-4 w-4" />
          새 지식베이스
        </Link>
      </div>
      <KbList items={kbs} />
    </section>
  );
}
