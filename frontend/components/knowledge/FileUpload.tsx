'use client';

import { useState } from 'react';
import { Upload } from 'lucide-react';
import { uploadDocument } from '@/lib/knowledge';
import { Button } from '@/components/ui/button';

export function FileUpload({ kbId }: { kbId: string }) {
  const [dragging, setDragging] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function uploadAll(files: FileList | File[]) {
    setError(null);
    for (const file of Array.from(files)) {
      try {
        await uploadDocument(kbId, file);
      } catch (e) {
        setError((e as Error).message);
        return;
      }
    }
  }

  return (
    <div
      onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
      onDragLeave={() => setDragging(false)}
      onDrop={(e) => { e.preventDefault(); setDragging(false); void uploadAll(e.dataTransfer.files); }}
      className={`rounded-2xl border-2 border-dashed p-8 text-center transition ${dragging ? 'border-clay-accent bg-clay-accent/5' : 'border-clay-border'}`}
    >
      <Upload className="mx-auto h-8 w-8 text-warmSilver mb-2" />
      <p className="text-sm text-clay-muted">파일을 여기로 끌어다 놓거나</p>
      <label className="mt-2 inline-block cursor-pointer">
        <Button variant="outline" size="sm" asChild={false} type="button">
          파일 선택
        </Button>
        <input type="file" multiple className="hidden" onChange={(e) => e.target.files && uploadAll(e.target.files)} />
      </label>
      {error && <p className="mt-3 text-sm text-red-600">{error}</p>}
    </div>
  );
}
