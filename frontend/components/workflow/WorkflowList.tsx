'use client';

import { useRouter } from 'next/navigation';
import { useCallback, useEffect, useState } from 'react';
import { Plus, Pencil, Trash2, Workflow } from 'lucide-react';

import {
  type WorkflowRead,
  createWorkflow,
  deleteWorkflow,
  fetchWorkflows,
} from '@/lib/workflow';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

export function WorkflowListClient() {
  const router = useRouter();
  const [workflows, setWorkflows] = useState<WorkflowRead[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [newName, setNewName] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    try {
      const data = await fetchWorkflows();
      setWorkflows(data);
    } catch {
      setError('워크플로우 목록을 불러올 수 없습니다.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleCreate = async () => {
    if (!newName.trim()) return;
    setCreating(true);
    setError('');
    try {
      const wf = await createWorkflow({ name: newName.trim() });
      router.push(`/workflows/${wf.id}/edit`);
    } catch {
      setError('워크플로우 생성에 실패했습니다.');
      setCreating(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm('이 워크플로우를 삭제하시겠습니까?')) return;
    try {
      await deleteWorkflow(id);
      setWorkflows((prev) => prev.filter((w) => w.id !== id));
    } catch {
      setError('삭제에 실패했습니다.');
    }
  };

  if (loading) {
    return <p className="text-warmSilver">로딩 중...</p>;
  }

  return (
    <div>
      {error && (
        <p className="mb-4 rounded-card border border-red-200 bg-red-50 px-4 py-2 text-sm text-red-600">
          {error}
        </p>
      )}

      {/* Create button / form */}
      {showForm ? (
        <div className="mb-6 flex items-center gap-3">
          <Input
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            placeholder="워크플로우 이름"
            autoFocus
            onKeyDown={(e) => e.key === 'Enter' && handleCreate()}
          />
          <Button
            onClick={handleCreate}
            disabled={creating || !newName.trim()}
          >
            {creating ? '생성 중...' : '생성'}
          </Button>
          <button
            onClick={() => { setShowForm(false); setNewName(''); }}
            className="text-sm text-warmSilver hover:text-clayBlack"
          >
            취소
          </button>
        </div>
      ) : (
        <Button
          onClick={() => setShowForm(true)}
          className="mb-6"
        >
          <Plus className="h-4 w-4" />
          새 워크플로우
        </Button>
      )}

      {/* Workflow grid */}
      {workflows.length === 0 ? (
        <p className="text-warmSilver text-sm">워크플로우가 없습니다. 새로 만들어보세요!</p>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {workflows.map((wf) => (
            <div
              key={wf.id}
              className="rounded-card border border-clay-border bg-white p-4 shadow-clay transition-all hover:border-clay-accent hover:shadow-clay-2"
            >
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-2 min-w-0">
                  <Workflow className="h-4 w-4 shrink-0 text-warmSilver" />
                  <h3 className="font-semibold text-clayBlack truncate">{wf.name}</h3>
                </div>
                <button
                  onClick={() => handleDelete(wf.id)}
                  className="ml-2 shrink-0 text-warmSilver hover:text-red-500 transition-colors"
                  title="삭제"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
              {wf.description && (
                <p className="mt-1 text-sm text-warmSilver line-clamp-2">
                  {wf.description}
                </p>
              )}
              <div className="mt-3 flex items-center justify-between">
                <span className="text-xs text-warmSilver">
                  노드 {wf.nodes.length}개
                </span>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => router.push(`/workflows/${wf.id}/edit`)}
                >
                  <Pencil className="h-3 w-3" />
                  편집
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
