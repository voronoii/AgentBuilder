import { apiBase } from './api';

export type KnowledgeBase = {
  id: string;
  name: string;
  description: string;
  embedding_provider: string;
  embedding_model: string;
  embedding_dim: number;
  qdrant_collection: string;
  chunk_size: number;
  chunk_overlap: number;
  created_at: string;
  updated_at: string;
};

export type DocumentRead = {
  id: string;
  knowledge_base_id: string;
  filename: string;
  file_size: number;
  file_type: string;
  status: 'pending' | 'processing' | 'done' | 'failed';
  error: string | null;
  chunk_count: number;
  created_at: string;
};

export type KnowledgeConfig = {
  supported_extensions: string[];
  max_upload_mb: number;
};

export async function getKnowledgeConfig(): Promise<KnowledgeConfig> {
  const res = await fetch(`${apiBase()}/knowledge/config`, { cache: 'no-store' });
  if (!res.ok) throw new Error(`getKnowledgeConfig failed: HTTP ${res.status}`);
  return (await res.json()) as KnowledgeConfig;
}

export type ChunkPreview = { chunk_index: number; text: string };

export async function listDocumentChunks(
  kbId: string,
  docId: string,
  limit = 3,
): Promise<ChunkPreview[]> {
  const res = await fetch(
    `${apiBase()}/knowledge/${kbId}/documents/${docId}/chunks?limit=${limit}`,
    { cache: 'no-store' },
  );
  if (!res.ok) throw new Error(`listDocumentChunks failed: HTTP ${res.status}`);
  const data = (await res.json()) as { chunks: ChunkPreview[] };
  return data.chunks;
}

export async function listKnowledgeBases(): Promise<KnowledgeBase[]> {
  const res = await fetch(`${apiBase()}/knowledge`, { cache: 'no-store' });
  if (!res.ok) throw new Error(`listKnowledgeBases failed: HTTP ${res.status}`);
  return (await res.json()) as KnowledgeBase[];
}

export async function getKnowledgeBase(id: string): Promise<KnowledgeBase> {
  const res = await fetch(`${apiBase()}/knowledge/${id}`, { cache: 'no-store' });
  if (!res.ok) throw new Error(`getKnowledgeBase failed: HTTP ${res.status}`);
  return (await res.json()) as KnowledgeBase;
}

export async function createKnowledgeBase(body: Partial<KnowledgeBase>): Promise<KnowledgeBase> {
  const res = await fetch(`${apiBase()}/knowledge`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await res.text());
  return (await res.json()) as KnowledgeBase;
}

export async function listDocuments(kbId: string): Promise<DocumentRead[]> {
  const res = await fetch(`${apiBase()}/knowledge/${kbId}/documents`, { cache: 'no-store' });
  if (!res.ok) throw new Error(`listDocuments failed: HTTP ${res.status}`);
  return (await res.json()) as DocumentRead[];
}

export async function uploadDocument(kbId: string, file: File): Promise<DocumentRead> {
  const body = new FormData();
  body.append('file', file);
  const res = await fetch(`${apiBase()}/knowledge/${kbId}/documents`, { method: 'POST', body });
  if (!res.ok) throw new Error(await res.text());
  return (await res.json()) as DocumentRead;
}

export async function deleteDocument(kbId: string, docId: string): Promise<void> {
  const res = await fetch(`${apiBase()}/knowledge/${kbId}/documents/${docId}`, {
    method: 'DELETE',
  });
  if (!res.ok) throw new Error(await res.text());
}

export type SearchHit = { score: number; text: string; filename: string; chunk_index: number };

export async function searchKnowledgeBase(kbId: string, query: string, topK = 5): Promise<SearchHit[]> {
  const res = await fetch(`${apiBase()}/knowledge/${kbId}/search`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ query, top_k: topK }),
  });
  if (!res.ok) throw new Error(await res.text());
  const data = (await res.json()) as { hits: SearchHit[] };
  return data.hits;
}
