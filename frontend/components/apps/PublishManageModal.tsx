'use client';

import { useState } from 'react';
import { Copy, Eye, EyeOff, RefreshCw, X } from 'lucide-react';

import { type PublishedApp, deleteApp, regenerateKey } from '@/lib/apps';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';

interface PublishManageModalProps {
  app: PublishedApp;
  onClose: () => void;
  onUnpublish: () => void;
  onKeyRegenerated: (app: PublishedApp) => void;
}

export function PublishManageModal({
  app,
  onClose,
  onUnpublish,
  onKeyRegenerated,
}: PublishManageModalProps) {
  const [showKey, setShowKey] = useState(false);
  const [regenerating, setRegenerating] = useState(false);
  const [unpublishing, setUnpublishing] = useState(false);
  const [copied, setCopied] = useState<string | null>(null);

  const webUrl =
    typeof window !== 'undefined'
      ? `${window.location.origin}/chat/${app.id}`
      : `/chat/${app.id}`;

  const hostname =
    typeof window !== 'undefined' ? window.location.hostname : 'localhost';

  const apiEndpoint = `${hostname}:28000/v1/chat/completions`;

  const maskedKey = app.api_key
    ? `${app.api_key.slice(0, 8)}${'•'.repeat(Math.max(0, app.api_key.length - 12))}${app.api_key.slice(-4)}`
    : '';

  const copyToClipboard = async (text: string, label: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(label);
      setTimeout(() => setCopied(null), 2000);
    } catch {
      // clipboard not available
    }
  };

  const handleRegenerate = async () => {
    if (!confirm('API 키를 재발급하면 기존 키는 즉시 무효화됩니다. 계속하시겠습니까?')) return;
    setRegenerating(true);
    try {
      const updated = await regenerateKey(app.id);
      onKeyRegenerated(updated);
    } catch {
      // silent — keep modal open
    } finally {
      setRegenerating(false);
    }
  };

  const handleUnpublish = async () => {
    if (!confirm('앱 발행을 해제하면 채팅 링크가 비활성화됩니다. 계속하시겠습니까?')) return;
    setUnpublishing(true);
    try {
      await deleteApp(app.id);
      onUnpublish();
    } catch {
      setUnpublishing(false);
    }
  };

  const curlExample = `curl -X POST https://${apiEndpoint} \\
  -H "Content-Type: application/json" \\
  -H "Authorization: Bearer ${app.api_key}" \\
  -d '{
    "model": "default",
    "messages": [
      { "role": "user", "content": "안녕하세요!" }
    ]
  }'`;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="w-full max-w-lg rounded-card border border-clay-border bg-white shadow-clay-2 mx-4 max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-clay-border px-5 py-4">
          <div className="flex items-center gap-2 min-w-0">
            <h2 className="text-base font-semibold text-clayBlack truncate">{app.name}</h2>
            <Badge variant={app.is_active ? 'success' : 'outline'}>
              {app.is_active ? '활성' : '비활성'}
            </Badge>
          </div>
          <button
            onClick={onClose}
            className="shrink-0 rounded-md p-1 text-warmSilver hover:bg-oat-light hover:text-clayBlack transition-colors"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="px-5 py-4 space-y-5">
          {/* Web URL */}
          <section className="space-y-2">
            <h3 className="text-sm font-medium text-clayBlack">웹앱 URL</h3>
            <div className="flex items-center gap-2 rounded-card border border-clay-border bg-oat-light px-3 py-2">
              <span className="flex-1 truncate text-sm text-clayBlack font-mono">{webUrl}</span>
              <button
                onClick={() => copyToClipboard(webUrl, 'url')}
                className="shrink-0 rounded p-1 text-warmSilver hover:text-clayBlack transition-colors"
                title="복사"
              >
                <Copy className="h-3.5 w-3.5" />
              </button>
            </div>
            {copied === 'url' && (
              <p className="text-xs text-green-600">복사되었습니다!</p>
            )}
          </section>

          {/* API Endpoint */}
          <section className="space-y-2">
            <h3 className="text-sm font-medium text-clayBlack">API 엔드포인트</h3>
            <div className="flex items-center gap-2 rounded-card border border-clay-border bg-oat-light px-3 py-2">
              <span className="text-xs text-warmSilver shrink-0">POST</span>
              <span className="flex-1 truncate text-sm text-clayBlack font-mono">{apiEndpoint}</span>
            </div>

            <h4 className="text-xs font-medium text-warmSilver mt-3">API 키</h4>
            <div className="flex items-center gap-2 rounded-card border border-clay-border bg-oat-light px-3 py-2">
              <span className="flex-1 truncate text-sm text-clayBlack font-mono">
                {showKey ? app.api_key : maskedKey}
              </span>
              <button
                onClick={() => setShowKey((v) => !v)}
                className="shrink-0 rounded p-1 text-warmSilver hover:text-clayBlack transition-colors"
                title={showKey ? '숨기기' : '표시'}
              >
                {showKey ? <EyeOff className="h-3.5 w-3.5" /> : <Eye className="h-3.5 w-3.5" />}
              </button>
              <button
                onClick={() => copyToClipboard(app.api_key, 'key')}
                className="shrink-0 rounded p-1 text-warmSilver hover:text-clayBlack transition-colors"
                title="복사"
              >
                <Copy className="h-3.5 w-3.5" />
              </button>
            </div>
            {copied === 'key' && (
              <p className="text-xs text-green-600">복사되었습니다!</p>
            )}
          </section>

          {/* cURL Example */}
          <section className="space-y-2">
            <h3 className="text-sm font-medium text-clayBlack">cURL 예시</h3>
            <div className="relative rounded-card bg-[#1a1a2e] p-4">
              <pre className="text-xs text-green-300 overflow-x-auto whitespace-pre-wrap break-all">
                {curlExample}
              </pre>
              <button
                onClick={() => copyToClipboard(curlExample, 'curl')}
                className="absolute right-3 top-3 rounded p-1 text-gray-400 hover:text-white transition-colors"
                title="복사"
              >
                <Copy className="h-3.5 w-3.5" />
              </button>
            </div>
            {copied === 'curl' && (
              <p className="text-xs text-green-600">복사되었습니다!</p>
            )}
          </section>
        </div>

        {/* Footer actions */}
        <div className="flex items-center justify-between gap-2 border-t border-clay-border px-5 py-4">
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handleRegenerate}
              disabled={regenerating || unpublishing}
            >
              <RefreshCw className={`h-3.5 w-3.5 ${regenerating ? 'animate-spin' : ''}`} />
              키 재발급
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={handleUnpublish}
              disabled={unpublishing || regenerating}
              className="text-red-500 border-red-200 hover:bg-red-50 hover:text-red-600"
            >
              {unpublishing ? '해제 중...' : '발행 해제'}
            </Button>
          </div>
          <Button variant="outline" size="sm" onClick={onClose}>
            닫기
          </Button>
        </div>
      </div>
    </div>
  );
}
