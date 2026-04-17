'use client';

import { useState } from 'react';
import { X } from 'lucide-react';

import { type PublishedApp, publishApp } from '@/lib/apps';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

interface PublishModalProps {
  workflowId: string;
  workflowName: string;
  onClose: () => void;
  onPublished: (appId: string) => void;
}

export function PublishModal({ workflowId, workflowName, onClose, onPublished }: PublishModalProps) {
  const [name, setName] = useState(workflowName);
  const [description, setDescription] = useState('');
  const [welcomeMessage, setWelcomeMessage] = useState('안녕하세요! 무엇을 도와드릴까요?');
  const [placeholderText, setPlaceholderText] = useState('메시지를 입력하세요...');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;

    setSubmitting(true);
    setError('');

    try {
      const app: PublishedApp = await publishApp({
        workflow_id: workflowId,
        name: name.trim(),
        description: description.trim() || undefined,
        welcome_message: welcomeMessage.trim() || undefined,
        placeholder_text: placeholderText.trim() || undefined,
      });
      onPublished(app.id);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : '앱 게시에 실패했습니다.');
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="w-full max-w-md rounded-card border border-clay-border bg-white shadow-clay-2 mx-4">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-clay-border px-5 py-4">
          <h2 className="text-base font-semibold text-clayBlack">앱으로 게시</h2>
          <button
            onClick={onClose}
            className="rounded-md p-1 text-warmSilver hover:bg-oat-light hover:text-clayBlack transition-colors"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="px-5 py-4 space-y-4">
          {error && (
            <p className="rounded-card border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-600">
              {error}
            </p>
          )}

          <div className="space-y-1.5">
            <label className="block text-sm font-medium text-clayBlack">
              앱 이름 <span className="text-red-500">*</span>
            </label>
            <Input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="앱 이름을 입력하세요"
              required
            />
          </div>

          <div className="space-y-1.5">
            <label className="block text-sm font-medium text-clayBlack">설명</label>
            <Input
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="앱에 대한 설명을 입력하세요"
            />
          </div>

          <div className="space-y-1.5">
            <label className="block text-sm font-medium text-clayBlack">환영 메시지</label>
            <Input
              value={welcomeMessage}
              onChange={(e) => setWelcomeMessage(e.target.value)}
              placeholder="안녕하세요! 무엇을 도와드릴까요?"
            />
          </div>

          <div className="space-y-1.5">
            <label className="block text-sm font-medium text-clayBlack">입력창 플레이스홀더</label>
            <Input
              value={placeholderText}
              onChange={(e) => setPlaceholderText(e.target.value)}
              placeholder="메시지를 입력하세요..."
            />
          </div>

          {/* Footer */}
          <div className="flex items-center justify-end gap-2 border-t border-clay-border pt-4">
            <Button type="button" variant="outline" onClick={onClose} disabled={submitting}>
              취소
            </Button>
            <Button type="submit" disabled={submitting || !name.trim()}>
              {submitting ? '게시 중...' : '게시'}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
