import Link from 'next/link';
import { KbList } from '@/components/knowledge/KbList';
import { listKnowledgeBases } from '@/lib/knowledge';

export const dynamic = 'force-dynamic';

export default async function KnowledgePage() {
  let kbs;
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
          className="rounded-full bg-clay-accent px-4 py-2 text-sm font-medium text-white"
        >
          + 새 지식베이스
        </Link>
      </div>
      <KbList items={kbs} />
    </section>
  );
}
