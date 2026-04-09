import { getKnowledgeBase, listDocuments } from '@/lib/knowledge';
import { IngestionProgress } from '@/components/knowledge/IngestionProgress';
import { SearchPanel } from '@/components/knowledge/SearchPanel';

export const dynamic = 'force-dynamic';

export default async function KbDetailPage({ params }: { params: Promise<{ kbId: string }> }) {
  const { kbId } = await params;
  const kb = await getKnowledgeBase(kbId);
  const documents = await listDocuments(kbId);

  return (
    <section className="space-y-8">
      <header>
        <h1 className="text-2xl font-semibold">{kb.name}</h1>
        <p className="text-sm text-clay-muted">
          {kb.embedding_provider} · {kb.embedding_model} · dim {kb.embedding_dim}
        </p>
      </header>
      <div className="grid gap-8 lg:grid-cols-2">
        <div className="space-y-4">
          <h2 className="text-lg font-medium">파일 업로드</h2>
          <IngestionProgress kbId={kb.id} initialDocuments={documents} />
        </div>
        <div className="space-y-4">
          <h2 className="text-lg font-medium">검색 테스트</h2>
          <SearchPanel kbId={kb.id} />
        </div>
      </div>
    </section>
  );
}
