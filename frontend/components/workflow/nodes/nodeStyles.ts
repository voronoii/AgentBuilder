import type { NodeType } from '@/lib/workflow';
import {
  BookOpen,
  Bot,
  Cpu,
  FileText,
  MessageSquare,
  MessageSquareShare,
  type LucideIcon,
} from 'lucide-react';

/** Color dot + Lucide icon per node type (Approach B: Thin Border + Color Dot) */
export const NODE_STYLES: Record<
  NodeType,
  { dotColor: string; icon: LucideIcon; label: string }
> = {
  chat_input: {
    dotColor: 'bg-rose-500',
    icon: MessageSquare,
    label: 'Chat Input',
  },
  chat_output: {
    dotColor: 'bg-rose-500',
    icon: MessageSquareShare,
    label: 'Chat Output',
  },
  llm: {
    dotColor: 'bg-cyan-500',
    icon: Cpu,
    label: 'Language Model',
  },
  agent: {
    dotColor: 'bg-purple-500',
    icon: Bot,
    label: 'Agent',
  },
  knowledge_base: {
    dotColor: 'bg-emerald-600',
    icon: BookOpen,
    label: 'Knowledge Base',
  },
  prompt_template: {
    dotColor: 'bg-amber-500',
    icon: FileText,
    label: 'Prompt Template',
  },
};

/** Backwards-compatible exports for components that still use NODE_COLORS / NODE_LABELS */
export const NODE_COLORS: Record<
  NodeType,
  { bg: string; border: string; text: string; icon: string; dotColor: string }
> = Object.fromEntries(
  Object.entries(NODE_STYLES).map(([key, val]) => [
    key,
    {
      bg: 'bg-white',
      border: 'border-clay-border',
      text: 'text-clayBlack',
      icon: '',
      dotColor: val.dotColor,
    },
  ]),
) as Record<NodeType, { bg: string; border: string; text: string; icon: string; dotColor: string }>;

export const NODE_LABELS: Record<NodeType, string> = Object.fromEntries(
  Object.entries(NODE_STYLES).map(([key, val]) => [key, val.label]),
) as Record<NodeType, string>;
