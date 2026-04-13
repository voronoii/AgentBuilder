'use client';

import { useState } from 'react';
import type { MCPServer, MCPServerCreate, MCPTransport } from '@/lib/mcp';
import { createMcpServer } from '@/lib/mcp';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Button } from '@/components/ui/button';

interface Props {
  onClose: () => void;
  onCreated: (server: MCPServer) => void;
}

const TABS: { value: MCPTransport; label: string; hint: string }[] = [
  {
    value: 'stdio',
    label: 'STDIO',
    hint: '로컬 프로세스 (npx, uvx 등)',
  },
  {
    value: 'http_sse',
    label: 'HTTP/SSE',
    hint: 'Legacy SSE transport (MCP spec ≤ 2024-11-05)',
  },
  {
    value: 'streamable_http',
    label: 'Streamable HTTP',
    hint: 'Recommended — MCP spec 2025-03-26+',
  },
];

function parseKVBlock(raw: string): Record<string, string> {
  const result: Record<string, string> = {};
  for (const line of raw.split('\n')) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('#')) continue;
    const eq = trimmed.indexOf('=');
    if (eq < 1) continue;
    result[trimmed.slice(0, eq).trim()] = trimmed.slice(eq + 1).trim();
  }
  return result;
}

function parseArgs(raw: string): string[] {
  return raw
    .split('\n')
    .map((l) => l.trim())
    .filter(Boolean);
}

export function RegisterMcpModal({ onClose, onCreated }: Props) {
  const [tab, setTab] = useState<MCPTransport>('streamable_http');
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [envBlock, setEnvBlock] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  // STDIO fields
  const [command, setCommand] = useState('');
  const [argsBlock, setArgsBlock] = useState('');

  // HTTP fields (shared by http_sse and streamable_http)
  const [url, setUrl] = useState('');
  const [headersBlock, setHeadersBlock] = useState('');

  const isHttp = tab === 'http_sse' || tab === 'streamable_http';
  const currentTab = TABS.find((t) => t.value === tab)!;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);

    try {
      let config: Record<string, unknown>;

      if (tab === 'stdio') {
        if (!command.trim()) {
          setError('command를 입력하세요.');
          return;
        }
        config = { command: command.trim(), args: parseArgs(argsBlock) };
      } else {
        if (!url.trim()) {
          setError('URL을 입력하세요.');
          return;
        }
        config = { url: url.trim(), headers: parseKVBlock(headersBlock) };
      }

      const payload: MCPServerCreate = {
        name: name.trim(),
        description: description.trim(),
        transport: tab,
        config,
        env_vars: parseKVBlock(envBlock),
      };

      const server = await createMcpServer(payload);
      onCreated(server);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : '등록 실패');
    } finally {
      setBusy(false);
    }
  }

  return (
    <Dialog open={true} onOpenChange={(open) => { if (!open) onClose(); }}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>새 MCP 서버 등록</DialogTitle>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Transport tabs */}
          <Tabs value={tab} onValueChange={(v) => setTab(v as MCPTransport)}>
            <TabsList className="w-full">
              {TABS.map((t) => (
                <TabsTrigger key={t.value} value={t.value} className="flex-1">
                  {t.label}
                </TabsTrigger>
              ))}
            </TabsList>
          </Tabs>
          <p className="text-xs text-clay-text opacity-60">{currentTab.hint}</p>

          {/* Common fields */}
          <div>
            <label className="mb-1 block text-xs font-medium text-clay-text">
              서버 이름 <span className="text-red-500">*</span>
            </label>
            <Input
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="my-mcp-server"
            />
          </div>

          <div>
            <label className="mb-1 block text-xs font-medium text-clay-text">설명</label>
            <Input
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="서버 설명"
            />
          </div>

          {/* STDIO fields */}
          {tab === 'stdio' && (
            <>
              <div>
                <label className="mb-1 block text-xs font-medium text-clay-text">
                  Command <span className="text-red-500">*</span>
                </label>
                <Input
                  required
                  value={command}
                  onChange={(e) => setCommand(e.target.value)}
                  placeholder="npx"
                  className="font-mono"
                />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-clay-text">
                  Args (줄 구분)
                </label>
                <Textarea
                  value={argsBlock}
                  onChange={(e) => setArgsBlock(e.target.value)}
                  rows={3}
                  placeholder={"@modelcontextprotocol/server-filesystem\n/tmp"}
                  className="font-mono"
                />
              </div>
            </>
          )}

          {/* HTTP fields (SSE & Streamable HTTP) */}
          {isHttp && (
            <>
              <div>
                <label className="mb-1 block text-xs font-medium text-clay-text">
                  URL <span className="text-red-500">*</span>
                </label>
                <Input
                  required
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  placeholder={
                    tab === 'streamable_http'
                      ? 'https://example.com/mcp'
                      : 'https://example.com/sse'
                  }
                  className="font-mono"
                />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-clay-text">
                  Headers (KEY=VALUE, 줄 구분)
                </label>
                <Textarea
                  value={headersBlock}
                  onChange={(e) => setHeadersBlock(e.target.value)}
                  rows={3}
                  placeholder="Authorization=Bearer your-token"
                  className="font-mono"
                />
              </div>
            </>
          )}

          {/* Env vars */}
          <div>
            <label className="mb-1 block text-xs font-medium text-clay-text">
              환경변수 (KEY=VALUE, 줄 구분)
            </label>
            <Textarea
              value={envBlock}
              onChange={(e) => setEnvBlock(e.target.value)}
              rows={2}
              placeholder="API_KEY=secret"
              className="font-mono"
            />
          </div>

          {error && (
            <p className="rounded-lg bg-red-50 px-3 py-2 text-xs text-red-600">{error}</p>
          )}

          <DialogFooter>
            <Button
              type="button"
              variant="ghost"
              onClick={onClose}
            >
              취소
            </Button>
            <Button
              type="submit"
              disabled={busy}
            >
              {busy ? '등록 중…' : '등록'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
