'use client';

import React from 'react';
import { useCallback, useEffect, useState } from 'react';
import { Lock, Globe, Settings, Pencil, Trash2 } from 'lucide-react';

import {
  type AppSetting,
  createSetting,
  deleteSetting,
  fetchSettings,
  updateSetting,
} from '@/lib/settings';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

const CATEGORY_ICON: Record<string, React.ReactNode> = {
  api_keys: <Lock className="h-4 w-4" />,
  endpoints: <Globe className="h-4 w-4" />,
  general: <Settings className="h-4 w-4" />,
};

const CATEGORY_LABELS: Record<string, string> = {
  api_keys: 'API Keys',
  endpoints: 'Endpoints',
  general: 'General',
};

const CATEGORY_DESCRIPTIONS: Record<string, string> = {
  api_keys:
    'LLM 프로바이더의 API 키를 입력하세요. 워크플로우의 LLM/Agent 노드에서 사용됩니다.',
  endpoints: '외부 서비스 엔드포인트를 설정합니다.',
  general: '기타 설정값을 관리합니다.',
};

function SettingRow({
  setting,
  onSaved,
  onDeleted,
}: {
  setting: AppSetting;
  onSaved: () => void;
  onDeleted: () => void;
}) {
  const [editing, setEditing] = useState(false);
  const [value, setValue] = useState('');
  const [saving, setSaving] = useState(false);
  const [flash, setFlash] = useState('');
  const [confirmDelete, setConfirmDelete] = useState(false);

  const isMasked = setting.is_secret && setting.value.startsWith('*');
  const displayValue = setting.value || '(미설정)';

  const handleEdit = () => {
    setValue(setting.is_secret ? '' : setting.value);
    setEditing(true);
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await updateSetting(setting.key, value);
      setFlash('저장됨');
      setEditing(false);
      onSaved();
      setTimeout(() => setFlash(''), 2000);
    } catch {
      setFlash('저장 실패');
    } finally {
      setSaving(false);
    }
  };

  const handleCancel = () => {
    setEditing(false);
    setValue('');
  };

  return (
    <div className="flex items-start gap-4 rounded-card border border-clay-border bg-white px-4 py-3">
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <code className="text-sm font-semibold text-clayBlack">
            {setting.key}
          </code>
          {setting.is_secret && (
            <Badge variant="secret">SECRET</Badge>
          )}
          {flash && (
            <span className="text-xs text-matcha-600">{flash}</span>
          )}
        </div>
        <p className="mt-0.5 text-xs text-warmSilver">{setting.description}</p>

        {editing ? (
          <div className="mt-2 flex items-center gap-2">
            <Input
              type={setting.is_secret ? 'password' : 'text'}
              value={value}
              onChange={(e) => setValue(e.target.value)}
              placeholder={
                setting.is_secret ? '새 값을 입력하세요' : '값을 입력하세요'
              }
              className="flex-1"
              autoFocus
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleSave();
                if (e.key === 'Escape') handleCancel();
              }}
            />
            <Button
              onClick={handleSave}
              disabled={saving}
              size="sm"
            >
              {saving ? '저장 중...' : '저장'}
            </Button>
            <button
              onClick={handleCancel}
              className="text-xs text-warmSilver hover:text-clayBlack"
            >
              취소
            </button>
          </div>
        ) : (
          <div className="mt-1">
            <span
              className={`text-sm ${
                setting.value
                  ? isMasked
                    ? 'font-mono text-warmCharcoal'
                    : 'text-clayBlack'
                  : 'italic text-warmSilver'
              }`}
            >
              {displayValue}
            </span>
          </div>
        )}
      </div>

      {!editing && (
        <div className="flex shrink-0 gap-1">
          <Button
            variant="outline"
            size="sm"
            onClick={handleEdit}
          >
            <Pencil className="h-3 w-3" />
            편집
          </Button>
          {confirmDelete ? (
            <div className="flex items-center gap-1">
              <Button
                size="sm"
                onClick={async () => {
                  await deleteSetting(setting.key);
                  onDeleted();
                }}
                className="bg-red-500 hover:bg-red-600"
              >
                확인
              </Button>
              <button
                onClick={() => setConfirmDelete(false)}
                className="text-xs text-warmSilver hover:text-clayBlack"
              >
                취소
              </button>
            </div>
          ) : (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setConfirmDelete(true)}
              className="text-red-500 hover:text-red-600 hover:bg-red-50"
            >
              <Trash2 className="h-3 w-3" />
            </Button>
          )}
        </div>
      )}
    </div>
  );
}

const CATEGORY_OPTIONS = [
  { value: 'api_keys', label: 'API Keys' },
  { value: 'endpoints', label: 'Endpoints' },
  { value: 'general', label: 'General' },
];

function AddSettingForm({ onCreated }: { onCreated: () => void }) {
  const [open, setOpen] = useState(false);
  const [key, setKey] = useState('');
  const [value, setValue] = useState('');
  const [description, setDescription] = useState('');
  const [category, setCategory] = useState('api_keys');
  const [isSecret, setIsSecret] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async () => {
    if (!key.trim()) {
      setError('키를 입력하세요');
      return;
    }
    setSaving(true);
    setError('');
    try {
      await createSetting({
        key: key.trim().toUpperCase(),
        value,
        description,
        category,
        is_secret: isSecret,
      });
      setKey('');
      setValue('');
      setDescription('');
      setOpen(false);
      onCreated();
    } catch (e) {
      setError(e instanceof Error ? e.message : '추가 실패');
    } finally {
      setSaving(false);
    }
  };

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        className="rounded-card border-2 border-dashed border-clay-border px-4 py-3 text-sm text-warmSilver hover:border-clay-accent hover:text-clay-accent transition-colors"
      >
        + 새 설정 추가
      </button>
    );
  }

  return (
    <div className="rounded-card border border-clay-accent bg-white px-4 py-4 space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-clayBlack">새 설정 추가</h3>
        <button onClick={() => setOpen(false)} className="text-xs text-warmSilver hover:text-clayBlack">✕</button>
      </div>
      {error && <p className="text-xs text-red-500">{error}</p>}
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="text-xs text-warmSilver">키 (자동 대문자)</label>
          <Input
            value={key}
            onChange={(e) => setKey(e.target.value)}
            placeholder="OPENROUTER_API_KEY"
            className="mt-1"
            onKeyDown={(e) => e.key === 'Enter' && handleSubmit()}
          />
        </div>
        <div>
          <label className="text-xs text-warmSilver">카테고리</label>
          <select
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            className="mt-1 w-full rounded border border-clay-border bg-cream px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-clay-accent"
          >
            {CATEGORY_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
        </div>
      </div>
      <div>
        <label className="text-xs text-warmSilver">값</label>
        <Input
          type={isSecret ? 'password' : 'text'}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder="값을 입력하세요"
          className="mt-1"
        />
      </div>
      <div>
        <label className="text-xs text-warmSilver">설명 (선택)</label>
        <Input
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="이 설정에 대한 설명"
          className="mt-1"
        />
      </div>
      <div className="flex items-center gap-4">
        <label className="flex items-center gap-2 text-xs text-clay-text">
          <input
            type="checkbox"
            checked={isSecret}
            onChange={(e) => setIsSecret(e.target.checked)}
            className="rounded"
          />
          시크릿 값 (마스킹 처리)
        </label>
        <div className="ml-auto flex gap-2">
          <button onClick={() => setOpen(false)} className="text-xs text-warmSilver hover:text-clayBlack">취소</button>
          <Button
            onClick={handleSubmit}
            disabled={saving}
            size="sm"
          >
            {saving ? '추가 중...' : '추가'}
          </Button>
        </div>
      </div>
    </div>
  );
}

export function SettingsClient() {
  const [settings, setSettings] = useState<AppSetting[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    try {
      const data = await fetchSettings();
      setSettings(data);
    } catch {
      setError('설정을 불러올 수 없습니다.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  if (loading) return <p className="text-warmSilver">로딩 중...</p>;

  if (error) {
    return (
      <p className="rounded-card border border-red-200 bg-red-50 px-4 py-2 text-sm text-red-600">
        {error}
      </p>
    );
  }

  // Group by category
  const grouped: Record<string, AppSetting[]> = {};
  for (const s of settings) {
    const cat = s.category || 'general';
    if (!grouped[cat]) grouped[cat] = [];
    grouped[cat].push(s);
  }

  return (
    <div className="space-y-8">
      <AddSettingForm onCreated={load} />
      {Object.entries(grouped).map(([category, items]) => (
        <section key={category}>
          <h2 className="flex items-center gap-2 text-sm font-semibold uppercase tracking-wider text-warmSilver mb-1">
            {CATEGORY_ICON[category] ?? null}
            {CATEGORY_LABELS[category] || category}
          </h2>
          <p className="mb-3 text-xs text-warmSilver">
            {CATEGORY_DESCRIPTIONS[category] || ''}
          </p>
          <div className="space-y-3">
            {items.map((s) => (
              <SettingRow key={s.key} setting={s} onSaved={load} onDeleted={load} />
            ))}
          </div>
        </section>
      ))}
    </div>
  );
}
