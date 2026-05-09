'use client';

import { useRef, useState } from 'react';
import { ChevronDown, Loader2, Sparkles } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Select } from '@/components/ui/select';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible';
import { generateAgentInstruction } from '@/lib/prompts';

interface InstructionGeneratorModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** Agent 노드의 provider. 비어있지 않으면 1순위로 사용 */
  provider: string;
  /** Agent 노드의 model. 비어있지 않으면 1순위로 사용 */
  model: string;
  knowledgeBaseNames: string[];
  toolNames: string[];
  hasExistingInstruction: boolean;
  onGenerated: (instruction: string, mode: 'overwrite' | 'append') => void;
}

const TONE_OPTIONS: ReadonlyArray<{ value: string; label: string }> = [
  { value: 'friendly', label: '친절하게' },
  { value: 'professional', label: '전문적으로' },
  { value: 'concise', label: '간결하게' },
  { value: 'detailed', label: '자세하게' },
];

const TOOL_POLICY_OPTIONS: ReadonlyArray<{ value: string; label: string }> = [
  { value: 'when_needed', label: '필요할 때만 사용' },
  { value: 'aggressive', label: '적극적으로 사용' },
  { value: 'never', label: '사용 안 함 (LLM 노드 권장)' },
];

const UNKNOWN_HANDLING_OPTIONS: ReadonlyArray<{ value: string; label: string }> = [
  { value: 'say_dont_know', label: '모른다고 말하기' },
  { value: 'ask', label: '추가 질문하기' },
  { value: 'best_effort', label: '확인된 범위에서 답하기' },
];

const MIN_GOAL_LENGTH = 5;
const MAX_GOAL_LENGTH = 4000;

export function InstructionGeneratorModal({
  open,
  onOpenChange,
  provider,
  model,
  knowledgeBaseNames,
  toolNames,
  hasExistingInstruction,
  onGenerated,
}: InstructionGeneratorModalProps) {
  const useAgentModel = Boolean(provider && model);
  const [goal, setGoal] = useState('');
  const [tone, setTone] = useState('friendly');
  const [toolPolicy, setToolPolicy] = useState('when_needed');
  const [unknownHandling, setUnknownHandling] = useState('say_dont_know');
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<{
    instruction: string;
    usedProvider: string;
    usedModel: string;
  } | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const goalLength = goal.trim().length;
  const canGenerate = goalLength >= MIN_GOAL_LENGTH && !loading;

  const reset = () => {
    setGoal('');
    setTone('friendly');
    setToolPolicy('when_needed');
    setUnknownHandling('say_dont_know');
    setAdvancedOpen(false);
    setLoading(false);
    setError(null);
    setResult(null);
    abortRef.current = null;
  };

  const handleOpenChange = (next: boolean) => {
    if (!next) {
      abortRef.current?.abort();
      reset();
    }
    onOpenChange(next);
  };

  const handleGenerate = async () => {
    if (!canGenerate) return;
    setLoading(true);
    setError(null);
    setResult(null);

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      const res = await generateAgentInstruction(
        {
          goal: goal.trim(),
          tone,
          tool_policy: toolPolicy,
          unknown_handling: unknownHandling,
          knowledge_bases: knowledgeBaseNames,
          tools: toolNames,
          // Agent의 provider/model이 둘 다 있을 때만 1순위로 보냄.
          // 둘 중 하나라도 비어있으면 백엔드의 INSTRUCTION_GENERATOR_* fallback을 사용.
          ...(useAgentModel ? { provider, model } : {}),
        },
        controller.signal,
      );
      setResult({
        instruction: res.instruction,
        usedProvider: res.used_provider,
        usedModel: res.used_model,
      });
    } catch (err) {
      if ((err as Error).name === 'AbortError') return;
      const message =
        err instanceof Error ? err.message : '지시문 생성에 실패했습니다.';
      setError(message);
    } finally {
      setLoading(false);
      abortRef.current = null;
    }
  };

  const handleAbort = () => {
    abortRef.current?.abort();
    abortRef.current = null;
    setLoading(false);
  };

  const apply = (mode: 'overwrite' | 'append') => {
    if (!result) return;
    onGenerated(result.instruction, mode);
    reset();
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-clay-accent" />
            AI로 에이전트 지시문 생성
          </DialogTitle>
          <DialogDescription>
            이 에이전트가 무엇을 해야 하는지 자유롭게 적어주세요.
            {useAgentModel ? (
              <> 지시문 생성에는 이 에이전트가 사용하는 모델을 그대로 사용합니다.</>
            ) : (
              <> 에이전트에 모델이 지정되지 않았습니다. 기본 지시문 생성 모델로 작성합니다.</>
            )}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-3">
          <div>
            <label
              htmlFor="instruction-goal"
              className="mb-1 block text-[11px] font-semibold uppercase tracking-wide text-warmSilver"
            >
              이 에이전트가 무엇을 해야 하나요?
            </label>
            <Textarea
              id="instruction-goal"
              rows={4}
              value={goal}
              onChange={(e) => setGoal(e.target.value)}
              placeholder="예: 사내 문서를 검색해서 신규 입사자의 질문에 답변하는 에이전트"
              disabled={loading}
              maxLength={MAX_GOAL_LENGTH}
            />
            <p className="mt-1 text-[11px] text-warmSilver">
              {goalLength} / {MAX_GOAL_LENGTH}
              {goalLength > 0 && goalLength < MIN_GOAL_LENGTH && (
                <span className="ml-2 text-amber-700">
                  최소 {MIN_GOAL_LENGTH}자 이상 입력해주세요.
                </span>
              )}
            </p>
          </div>

          <Collapsible open={advancedOpen} onOpenChange={setAdvancedOpen}>
            <CollapsibleTrigger className="flex items-center gap-1 text-xs font-medium text-clay-text transition-colors hover:text-clay-accent">
              <ChevronDown
                className={`h-3.5 w-3.5 transition-transform ${
                  advancedOpen ? '' : '-rotate-90'
                }`}
              />
              고급 옵션
            </CollapsibleTrigger>
            <CollapsibleContent className="mt-2 space-y-2 rounded-md border border-clay-border bg-white p-3">
              <div>
                <label className="mb-1 block text-[11px] font-semibold uppercase tracking-wide text-warmSilver">
                  답변 톤
                </label>
                <Select
                  value={tone}
                  onChange={(e) => setTone(e.target.value)}
                  disabled={loading}
                >
                  {TONE_OPTIONS.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </Select>
              </div>
              <div>
                <label className="mb-1 block text-[11px] font-semibold uppercase tracking-wide text-warmSilver">
                  도구 사용 방식
                </label>
                <Select
                  value={toolPolicy}
                  onChange={(e) => setToolPolicy(e.target.value)}
                  disabled={loading}
                >
                  {TOOL_POLICY_OPTIONS.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </Select>
              </div>
              <div>
                <label className="mb-1 block text-[11px] font-semibold uppercase tracking-wide text-warmSilver">
                  모르는 내용 처리
                </label>
                <Select
                  value={unknownHandling}
                  onChange={(e) => setUnknownHandling(e.target.value)}
                  disabled={loading}
                >
                  {UNKNOWN_HANDLING_OPTIONS.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </Select>
              </div>
            </CollapsibleContent>
          </Collapsible>
        </div>

        {error && (
          <div className="rounded-md border border-red-300 bg-red-50 p-3 text-xs text-red-900">
            {error}
          </div>
        )}

        {result && (
          <div className="rounded-md border border-clay-border bg-oat-light p-3">
            <div className="mb-2 flex items-center justify-between gap-2">
              <p className="text-[11px] font-semibold uppercase tracking-wide text-warmSilver">
                생성 결과 미리보기
              </p>
              <p className="text-[10px] text-warmSilver">
                {result.usedProvider} · {result.usedModel}
              </p>
            </div>
            <pre className="max-h-72 overflow-auto whitespace-pre-wrap text-xs text-clay-text">
              {result.instruction}
            </pre>
          </div>
        )}

        <DialogFooter>
          {!result ? (
            <>
              <Button
                variant="outline"
                onClick={() => handleOpenChange(false)}
                disabled={loading}
              >
                닫기
              </Button>
              {loading ? (
                <Button variant="outline" onClick={handleAbort}>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  생성 중... 취소
                </Button>
              ) : (
                <Button onClick={handleGenerate} disabled={!canGenerate}>
                  <Sparkles className="h-4 w-4" />
                  생성하기
                </Button>
              )}
            </>
          ) : (
            <>
              <Button
                variant="outline"
                onClick={handleGenerate}
                disabled={loading}
              >
                다시 생성
              </Button>
              {hasExistingInstruction && (
                <Button variant="outline" onClick={() => apply('append')}>
                  끝에 추가
                </Button>
              )}
              <Button onClick={() => apply('overwrite')}>
                {hasExistingInstruction ? '덮어쓰기' : '적용'}
              </Button>
            </>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
