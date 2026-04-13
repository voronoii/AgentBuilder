# AgentBuilder UI Redesign — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign the entire AgentBuilder frontend from prototype quality to commercial agent-builder platform quality, replacing emojis with Lucide icons, introducing shadcn/ui components, and applying the Thin Border + Color Dot node design.

**Architecture:** Pure UI refactor — no backend changes, no state management changes, no routing changes (except renaming "환경변수" to "설정"). All existing Tailwind Clay tokens are preserved. shadcn/ui is added as copy-paste components (not a library dependency). Lucide React replaces all emoji icons.

**Tech Stack:** Next.js 15, React 19, Tailwind CSS 3.4, shadcn/ui (Radix primitives), lucide-react, @xyflow/react 12

**Design Spec:** `docs/superpowers/specs/2026-04-13-ui-redesign-design.md`

---

## File Structure

### New Files
- `components/ui/button.tsx` — shadcn Button (primary/outline/ghost/destructive variants, Clay colors)
- `components/ui/input.tsx` — shadcn Input (replaces `.input-field` class)
- `components/ui/textarea.tsx` — shadcn Textarea
- `components/ui/select.tsx` — shadcn Select (Radix-based)
- `components/ui/dialog.tsx` — shadcn Dialog (Radix-based, replaces custom modals)
- `components/ui/tabs.tsx` — shadcn Tabs (Radix-based)
- `components/ui/badge.tsx` — shadcn Badge (status indicators)
- `components/ui/tooltip.tsx` — shadcn Tooltip
- `components/ui/collapsible.tsx` — shadcn Collapsible
- `lib/utils.ts` — `cn()` helper (clsx + tailwind-merge)

### Modified Files
- `package.json` — add lucide-react, @radix-ui/*, class-variance-authority, clsx, tailwind-merge
- `tailwind.config.ts` — add elevation shadows, fix missing tokens
- `app/globals.css` — update focus ring color, remove `.input-field`
- `app/layout.tsx` — fix `bg-clay-bg` → `bg-cream`
- `app/settings/page.tsx` — rename page title
- `components/nav/TopNav.tsx` — icons, logo, active indicator
- `components/workflow/nodes/nodeStyles.ts` — color dot system, Lucide icon components
- `components/workflow/nodes/BaseNode.tsx` — thin border, dot, icon, field preview, selected state
- `components/workflow/WorkflowEditor.tsx` — toolbar redesign
- `components/workflow/Sidebar.tsx` — icon replacement, dot system in components panel
- `components/workflow/NodeConfigPanel.tsx` — shadcn form components, dot header
- `components/workflow/PlaygroundPanel.tsx` — message colors, icons
- `components/workflow/RunLogPanel.tsx` — Lucide icons, Badge component
- `components/workflow/WorkflowList.tsx` — card + button styling
- `components/knowledge/KbList.tsx` — card redesign, empty state, fix clay-muted
- `components/knowledge/CreateKbForm.tsx` — shadcn form components
- `components/knowledge/IngestionProgress.tsx` — icon replacement
- `components/knowledge/FileUpload.tsx` — icon replacement
- `components/knowledge/SearchPanel.tsx` — shadcn input
- `components/mcp/McpServerList.tsx` — card redesign, Lucide icons, Badge
- `components/mcp/RegisterMcpModal.tsx` — shadcn Dialog + Tabs
- `components/mcp/ToolCatalog.tsx` — tag chip style
- `components/settings/SettingsPage.tsx` — full redesign

---

## Task 1: Install Dependencies

**Files:**
- Modify: `frontend/package.json`

- [ ] **Step 1: Install Lucide, Radix, and utility packages**

```bash
cd /DATA3/users/mj/AgentBuilder/frontend
npm install lucide-react class-variance-authority clsx tailwind-merge
npm install @radix-ui/react-dialog @radix-ui/react-select @radix-ui/react-tabs @radix-ui/react-tooltip @radix-ui/react-collapsible @radix-ui/react-slot
```

- [ ] **Step 2: Verify installation**

```bash
cd /DATA3/users/mj/AgentBuilder/frontend && npm ls lucide-react class-variance-authority
```

Expected: Both packages listed without errors.

- [ ] **Step 3: Commit**

```bash
cd /DATA3/users/mj/AgentBuilder/frontend
git add package.json package-lock.json
git commit -m "chore: add lucide-react, shadcn/radix primitives, and class utilities"
```

---

## Task 2: Design Token Foundation

**Files:**
- Create: `frontend/lib/utils.ts`
- Modify: `frontend/tailwind.config.ts`
- Modify: `frontend/app/globals.css`
- Modify: `frontend/app/layout.tsx`

- [ ] **Step 1: Create cn() utility**

Create `frontend/lib/utils.ts`:

```ts
import { type ClassValue, clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
```

- [ ] **Step 2: Update tailwind.config.ts — add elevation shadows and fix missing tokens**

In `frontend/tailwind.config.ts`, replace the `boxShadow` section and add the `clay-bg` / `clay-muted` tokens that are referenced but missing:

```ts
// Inside theme.extend.colors, add:
'clay-bg': '#faf9f7',      // = cream (alias used in layout.tsx)
'clay-muted': '#9f9b93',   // = warmSilver (alias used in KbList.tsx)

// Inside theme.extend.boxShadow, replace existing:
boxShadow: {
  'clay': '0px 1px 1px rgba(0,0,0,0.1), 0px -1px 1px rgba(0,0,0,0.04) inset, 0px -0.5px 1px rgba(0,0,0,0.05)',
  'clay-0': 'none',
  'clay-1': '0 1px 3px rgba(0,0,0,0.06)',
  'clay-2': '0 4px 12px rgba(0,0,0,0.08)',
  'clay-focus': '0 0 0 2px rgba(7,138,82,0.15)',
},
```

- [ ] **Step 3: Update globals.css — change focus ring to matcha**

In `frontend/app/globals.css`, replace the `.input-field` block:

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

html,
body {
  background-color: #faf9f7;
  color: #000000;
  -webkit-font-smoothing: antialiased;
}
```

Remove the `.input-field` class entirely — it will be replaced by shadcn Input component.

- [ ] **Step 4: Fix layout.tsx body class**

In `frontend/app/layout.tsx`, the body class uses `bg-clay-bg` which now exists as a token (added in step 2). No change needed if step 2 is applied. Verify it renders correctly.

- [ ] **Step 5: Build check**

```bash
cd /DATA3/users/mj/AgentBuilder/frontend && npm run build
```

Expected: Build succeeds.

- [ ] **Step 6: Commit**

```bash
cd /DATA3/users/mj/AgentBuilder/frontend
git add lib/utils.ts tailwind.config.ts app/globals.css app/layout.tsx
git commit -m "feat: add design token foundation — elevation shadows, cn() utility, fix missing tokens"
```

---

## Task 3: shadcn/ui Base Components

**Files:**
- Create: `frontend/components/ui/button.tsx`
- Create: `frontend/components/ui/input.tsx`
- Create: `frontend/components/ui/textarea.tsx`
- Create: `frontend/components/ui/badge.tsx`
- Create: `frontend/components/ui/dialog.tsx`
- Create: `frontend/components/ui/tabs.tsx`
- Create: `frontend/components/ui/select.tsx`
- Create: `frontend/components/ui/tooltip.tsx`
- Create: `frontend/components/ui/collapsible.tsx`

- [ ] **Step 1: Create Button component**

Create `frontend/components/ui/button.tsx`:

```tsx
import * as React from 'react';
import { Slot } from '@radix-ui/react-slot';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/lib/utils';

const buttonVariants = cva(
  'inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-lg text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-clay-accent focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0',
  {
    variants: {
      variant: {
        default: 'bg-clay-accent text-white hover:bg-clay-accent/90',
        destructive: 'bg-red-500 text-white hover:bg-red-600',
        outline: 'border border-clay-border bg-white hover:bg-oat-light text-clay-text',
        ghost: 'hover:bg-oat-light text-clay-text',
        link: 'text-clay-accent underline-offset-4 hover:underline',
      },
      size: {
        default: 'h-9 px-4 py-2',
        sm: 'h-8 rounded-md px-3 text-xs',
        lg: 'h-10 rounded-lg px-8',
        icon: 'h-9 w-9',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'default',
    },
  },
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : 'button';
    return (
      <Comp
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        {...props}
      />
    );
  },
);
Button.displayName = 'Button';

export { Button, buttonVariants };
```

- [ ] **Step 2: Create Input component**

Create `frontend/components/ui/input.tsx`:

```tsx
import * as React from 'react';
import { cn } from '@/lib/utils';

const Input = React.forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement>>(
  ({ className, type, ...props }, ref) => {
    return (
      <input
        type={type}
        className={cn(
          'flex h-9 w-full rounded-lg border border-clay-border bg-white px-3 py-1 text-sm text-clayBlack shadow-clay-0 transition-colors placeholder:text-warmSilver focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-clay-accent focus-visible:ring-offset-1 disabled:cursor-not-allowed disabled:opacity-50',
          className,
        )}
        ref={ref}
        {...props}
      />
    );
  },
);
Input.displayName = 'Input';

export { Input };
```

- [ ] **Step 3: Create Textarea component**

Create `frontend/components/ui/textarea.tsx`:

```tsx
import * as React from 'react';
import { cn } from '@/lib/utils';

const Textarea = React.forwardRef<HTMLTextAreaElement, React.TextareaHTMLAttributes<HTMLTextAreaElement>>(
  ({ className, ...props }, ref) => {
    return (
      <textarea
        className={cn(
          'flex min-h-[60px] w-full rounded-lg border border-clay-border bg-white px-3 py-2 text-sm text-clayBlack shadow-clay-0 placeholder:text-warmSilver focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-clay-accent focus-visible:ring-offset-1 disabled:cursor-not-allowed disabled:opacity-50',
          className,
        )}
        ref={ref}
        {...props}
      />
    );
  },
);
Textarea.displayName = 'Textarea';

export { Textarea };
```

- [ ] **Step 4: Create Badge component**

Create `frontend/components/ui/badge.tsx`:

```tsx
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/lib/utils';

const badgeVariants = cva(
  'inline-flex items-center rounded-md px-2 py-0.5 text-xs font-semibold transition-colors',
  {
    variants: {
      variant: {
        default: 'bg-oat-light text-clay-text',
        success: 'bg-green-50 text-green-700',
        destructive: 'bg-red-50 text-red-600',
        warning: 'bg-yellow-50 text-yellow-700',
        info: 'bg-blue-50 text-blue-700',
        outline: 'border border-clay-border text-clay-text',
        secret: 'bg-red-50 text-red-500',
      },
    },
    defaultVariants: {
      variant: 'default',
    },
  },
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return <div className={cn(badgeVariants({ variant }), className)} {...props} />;
}

export { Badge, badgeVariants };
```

- [ ] **Step 5: Create Dialog component**

Create `frontend/components/ui/dialog.tsx`:

```tsx
'use client';

import * as React from 'react';
import * as DialogPrimitive from '@radix-ui/react-dialog';
import { X } from 'lucide-react';
import { cn } from '@/lib/utils';

const Dialog = DialogPrimitive.Root;
const DialogTrigger = DialogPrimitive.Trigger;
const DialogPortal = DialogPrimitive.Portal;
const DialogClose = DialogPrimitive.Close;

const DialogOverlay = React.forwardRef<
  React.ComponentRef<typeof DialogPrimitive.Overlay>,
  React.ComponentPropsWithoutRef<typeof DialogPrimitive.Overlay>
>(({ className, ...props }, ref) => (
  <DialogPrimitive.Overlay
    ref={ref}
    className={cn(
      'fixed inset-0 z-50 bg-black/40 data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0',
      className,
    )}
    {...props}
  />
));
DialogOverlay.displayName = DialogPrimitive.Overlay.displayName;

const DialogContent = React.forwardRef<
  React.ComponentRef<typeof DialogPrimitive.Content>,
  React.ComponentPropsWithoutRef<typeof DialogPrimitive.Content>
>(({ className, children, ...props }, ref) => (
  <DialogPortal>
    <DialogOverlay />
    <DialogPrimitive.Content
      ref={ref}
      className={cn(
        'fixed left-[50%] top-[50%] z-50 grid w-full max-w-lg translate-x-[-50%] translate-y-[-50%] gap-4 rounded-2xl border border-clay-border bg-clay-surface p-6 shadow-clay-2',
        className,
      )}
      {...props}
    >
      {children}
      <DialogPrimitive.Close className="absolute right-4 top-4 rounded-sm opacity-70 transition-opacity hover:opacity-100 focus:outline-none focus:ring-2 focus:ring-clay-accent focus:ring-offset-2">
        <X className="h-4 w-4 text-warmSilver" />
        <span className="sr-only">Close</span>
      </DialogPrimitive.Close>
    </DialogPrimitive.Content>
  </DialogPortal>
));
DialogContent.displayName = DialogPrimitive.Content.displayName;

function DialogHeader({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn('flex flex-col space-y-1.5', className)} {...props} />;
}

function DialogFooter({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn('flex justify-end gap-2', className)} {...props} />;
}

function DialogTitle({ className, ...props }: React.ComponentPropsWithoutRef<typeof DialogPrimitive.Title>) {
  return <DialogPrimitive.Title className={cn('text-lg font-semibold text-clayBlack', className)} {...props} />;
}

function DialogDescription({ className, ...props }: React.ComponentPropsWithoutRef<typeof DialogPrimitive.Description>) {
  return <DialogPrimitive.Description className={cn('text-sm text-warmSilver', className)} {...props} />;
}

export {
  Dialog,
  DialogPortal,
  DialogOverlay,
  DialogClose,
  DialogTrigger,
  DialogContent,
  DialogHeader,
  DialogFooter,
  DialogTitle,
  DialogDescription,
};
```

- [ ] **Step 6: Create Tabs component**

Create `frontend/components/ui/tabs.tsx`:

```tsx
'use client';

import * as React from 'react';
import * as TabsPrimitive from '@radix-ui/react-tabs';
import { cn } from '@/lib/utils';

const Tabs = TabsPrimitive.Root;

const TabsList = React.forwardRef<
  React.ComponentRef<typeof TabsPrimitive.List>,
  React.ComponentPropsWithoutRef<typeof TabsPrimitive.List>
>(({ className, ...props }, ref) => (
  <TabsPrimitive.List
    ref={ref}
    className={cn(
      'inline-flex h-9 items-center justify-center rounded-lg bg-oat-light p-1 text-clay-text',
      className,
    )}
    {...props}
  />
));
TabsList.displayName = TabsPrimitive.List.displayName;

const TabsTrigger = React.forwardRef<
  React.ComponentRef<typeof TabsPrimitive.Trigger>,
  React.ComponentPropsWithoutRef<typeof TabsPrimitive.Trigger>
>(({ className, ...props }, ref) => (
  <TabsPrimitive.Trigger
    ref={ref}
    className={cn(
      'inline-flex items-center justify-center whitespace-nowrap rounded-md px-3 py-1 text-sm font-medium transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-clay-accent focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 data-[state=active]:bg-clay-accent data-[state=active]:text-white data-[state=active]:shadow-clay-1',
      className,
    )}
    {...props}
  />
));
TabsTrigger.displayName = TabsPrimitive.Trigger.displayName;

const TabsContent = React.forwardRef<
  React.ComponentRef<typeof TabsPrimitive.Content>,
  React.ComponentPropsWithoutRef<typeof TabsPrimitive.Content>
>(({ className, ...props }, ref) => (
  <TabsPrimitive.Content
    ref={ref}
    className={cn(
      'mt-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-clay-accent focus-visible:ring-offset-2',
      className,
    )}
    {...props}
  />
));
TabsContent.displayName = TabsPrimitive.Content.displayName;

export { Tabs, TabsList, TabsTrigger, TabsContent };
```

- [ ] **Step 7: Create Select component (native, not Radix — simpler for forms)**

Create `frontend/components/ui/select.tsx`:

```tsx
import * as React from 'react';
import { cn } from '@/lib/utils';

const Select = React.forwardRef<HTMLSelectElement, React.SelectHTMLAttributes<HTMLSelectElement>>(
  ({ className, ...props }, ref) => {
    return (
      <select
        className={cn(
          'flex h-9 w-full appearance-none rounded-lg border border-clay-border bg-white px-3 py-1 text-sm text-clayBlack shadow-clay-0 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-clay-accent focus-visible:ring-offset-1 disabled:cursor-not-allowed disabled:opacity-50',
          className,
        )}
        ref={ref}
        {...props}
      />
    );
  },
);
Select.displayName = 'Select';

export { Select };
```

- [ ] **Step 8: Create Collapsible component**

Create `frontend/components/ui/collapsible.tsx`:

```tsx
'use client';

import * as CollapsiblePrimitive from '@radix-ui/react-collapsible';

const Collapsible = CollapsiblePrimitive.Root;
const CollapsibleTrigger = CollapsiblePrimitive.CollapsibleTrigger;
const CollapsibleContent = CollapsiblePrimitive.CollapsibleContent;

export { Collapsible, CollapsibleTrigger, CollapsibleContent };
```

- [ ] **Step 9: Build check**

```bash
cd /DATA3/users/mj/AgentBuilder/frontend && npm run build
```

Expected: Build succeeds. The new components aren't imported anywhere yet, so tree-shaking should exclude them.

- [ ] **Step 10: Commit**

```bash
cd /DATA3/users/mj/AgentBuilder/frontend
git add components/ui/
git commit -m "feat: add shadcn/ui base components — Button, Input, Textarea, Badge, Dialog, Tabs, Select, Collapsible"
```

---

## Task 4: TopNav Redesign

**Files:**
- Modify: `frontend/components/nav/TopNav.tsx`

- [ ] **Step 1: Rewrite TopNav with Lucide icons and active indicator**

Replace the entire content of `frontend/components/nav/TopNav.tsx`:

```tsx
'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { BookOpen, Settings, Workflow, Wrench } from 'lucide-react';
import { cn } from '@/lib/utils';

const tabs = [
  { href: '/knowledge', label: '지식', icon: BookOpen },
  { href: '/workflows', label: '워크플로우', icon: Workflow },
  { href: '/tools', label: '도구', icon: Wrench },
  { href: '/settings', label: '설정', icon: Settings },
];

export function TopNav() {
  const pathname = usePathname();

  return (
    <header className="border-b border-clay-border bg-clay-surface">
      <nav
        className="mx-auto flex max-w-6xl items-center gap-6 px-6"
        aria-label="Main navigation"
      >
        {/* Logo */}
        <Link href="/" className="flex items-center gap-2 py-4">
          <div className="flex h-7 w-7 items-center justify-center rounded-md bg-clay-accent text-xs font-extrabold text-white">
            A
          </div>
          <span className="text-lg font-semibold tracking-tight text-clayBlack">
            AgentBuilder
          </span>
        </Link>

        {/* Tabs */}
        <ul className="flex">
          {tabs.map((t) => {
            const isActive = pathname?.startsWith(t.href);
            const Icon = t.icon;
            return (
              <li key={t.href}>
                <Link
                  href={t.href}
                  className={cn(
                    'flex items-center gap-1.5 border-b-2 px-4 py-4 text-sm transition-colors',
                    isActive
                      ? 'border-clay-accent font-semibold text-clayBlack'
                      : 'border-transparent text-warmSilver hover:text-clay-text',
                  )}
                >
                  <Icon className="h-4 w-4" />
                  {t.label}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>
    </header>
  );
}
```

- [ ] **Step 2: Build check**

```bash
cd /DATA3/users/mj/AgentBuilder/frontend && npm run build
```

- [ ] **Step 3: Commit**

```bash
cd /DATA3/users/mj/AgentBuilder/frontend
git add components/nav/TopNav.tsx
git commit -m "feat: redesign TopNav — Lucide icons, logo badge, active tab indicator"
```

---

## Task 5: Node Style System (Color Dots + Lucide Icons)

**Files:**
- Modify: `frontend/components/workflow/nodes/nodeStyles.ts`

- [ ] **Step 1: Rewrite nodeStyles.ts with color dot system and Lucide icon references**

Replace entire content of `frontend/components/workflow/nodes/nodeStyles.ts`:

```ts
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
      icon: '', // no longer emoji — use NODE_STYLES[type].icon component
      dotColor: val.dotColor,
    },
  ]),
) as Record<NodeType, { bg: string; border: string; text: string; icon: string; dotColor: string }>;

export const NODE_LABELS: Record<NodeType, string> = Object.fromEntries(
  Object.entries(NODE_STYLES).map(([key, val]) => [key, val.label]),
) as Record<NodeType, string>;
```

- [ ] **Step 2: Build check**

```bash
cd /DATA3/users/mj/AgentBuilder/frontend && npm run build
```

- [ ] **Step 3: Commit**

```bash
cd /DATA3/users/mj/AgentBuilder/frontend
git add components/workflow/nodes/nodeStyles.ts
git commit -m "feat: replace emoji node styles with color dot + Lucide icon system"
```

---

## Task 6: BaseNode Redesign

**Files:**
- Modify: `frontend/components/workflow/nodes/BaseNode.tsx`

- [ ] **Step 1: Rewrite BaseNode with thin border, color dot, Lucide icon, field preview**

Replace entire content of `frontend/components/workflow/nodes/BaseNode.tsx`:

```tsx
'use client';

import { Handle, Position, type NodeProps } from '@xyflow/react';
import { X } from 'lucide-react';

import type { NodeData, NodeType } from '@/lib/workflow';
import { useWorkflowStore } from '@/stores/workflowStore';
import { cn } from '@/lib/utils';

import { NODE_STYLES } from './nodeStyles';

interface BaseNodeProps {
  id: string;
  data: NodeData;
  selected?: boolean;
  showSourceHandle?: boolean;
  showTargetHandle?: boolean;
}

/** Render key settings as preview fields inside the node body. */
function FieldPreview({ data }: { data: NodeData }) {
  const fields: Array<{ label: string; value: string }> = [];
  const type = data.type as NodeType;

  if (type === 'llm' || type === 'agent') {
    if (data.provider) fields.push({ label: 'Provider', value: String(data.provider) });
    if (data.model) fields.push({ label: 'Model', value: String(data.model) });
  }
  if (type === 'agent' && data.maxIterations) {
    fields.push({ label: 'Max Iterations', value: String(data.maxIterations) });
  }
  if (type === 'knowledge_base') {
    if (data.topK) fields.push({ label: 'Top K', value: String(data.topK) });
  }
  if (type === 'prompt_template' && data.template) {
    const vars = String(data.template).match(/\{(\w+)\}/g);
    if (vars) {
      fields.push({ label: 'Variables', value: vars.join(', ') });
    }
  }

  if (fields.length === 0) return null;

  return (
    <div className="border-t border-oat-light px-3 py-2 space-y-1">
      {fields.map((f) => (
        <div key={f.label}>
          <div className="text-[10px] font-medium uppercase tracking-wide text-warmSilver">
            {f.label}
          </div>
          <div className="text-[11px] text-clay-text truncate">{f.value}</div>
        </div>
      ))}
    </div>
  );
}

export function BaseNode({
  id,
  data,
  selected,
  showSourceHandle = true,
  showTargetHandle = true,
}: BaseNodeProps) {
  const setSelectedNodeId = useWorkflowStore((s) => s.setSelectedNodeId);
  const removeNode = useWorkflowStore((s) => s.removeNode);
  const nodeType = data.type as NodeType;
  const style = NODE_STYLES[nodeType];
  const Icon = style.icon;

  return (
    <div
      className={cn(
        'relative min-w-[200px] rounded-card border bg-white shadow-clay-1 transition-all',
        selected
          ? 'border-clay-accent shadow-clay-focus'
          : 'border-clay-border',
      )}
      onClick={() => setSelectedNodeId(id)}
    >
      {showTargetHandle && (
        <Handle
          type="target"
          position={Position.Left}
          className="!w-3 !h-3 !bg-oat !border-2 !border-white !shadow-[0_0_0_1px_#dad4c8]"
        />
      )}

      {/* Header */}
      <div className="flex items-center gap-2 px-3 py-2.5">
        <div className={cn('h-2 w-2 rounded-full flex-shrink-0', style.dotColor)} />
        <Icon className="h-4 w-4 text-warmSilver flex-shrink-0" />
        <span className="text-xs font-semibold text-clayBlack flex-1 truncate">
          {data.label}
        </span>
        <button
          className="text-warmSilver hover:text-red-500 transition-colors"
          onClick={(e) => {
            e.stopPropagation();
            removeNode(id);
          }}
          aria-label="삭제"
        >
          <X className="h-3.5 w-3.5" />
        </button>
      </div>

      {/* Field preview */}
      <FieldPreview data={data} />

      {showSourceHandle && (
        <Handle
          type="source"
          position={Position.Right}
          className="!w-3 !h-3 !bg-oat !border-2 !border-white !shadow-[0_0_0_1px_#dad4c8]"
        />
      )}
    </div>
  );
}

// ---------- Typed wrappers ----------

export function ChatInputNode(props: NodeProps) {
  return (
    <BaseNode
      id={props.id}
      data={props.data as unknown as NodeData}
      selected={props.selected}
      showTargetHandle={false}
      showSourceHandle={true}
    />
  );
}

export function ChatOutputNode(props: NodeProps) {
  return (
    <BaseNode
      id={props.id}
      data={props.data as unknown as NodeData}
      selected={props.selected}
      showTargetHandle={true}
      showSourceHandle={false}
    />
  );
}

export function LLMNode(props: NodeProps) {
  return (
    <BaseNode
      id={props.id}
      data={props.data as unknown as NodeData}
      selected={props.selected}
    />
  );
}

export function AgentNode(props: NodeProps) {
  return (
    <BaseNode
      id={props.id}
      data={props.data as unknown as NodeData}
      selected={props.selected}
    />
  );
}

export function KnowledgeBaseNode(props: NodeProps) {
  return (
    <BaseNode
      id={props.id}
      data={props.data as unknown as NodeData}
      selected={props.selected}
    />
  );
}

export function PromptTemplateNode(props: NodeProps) {
  return (
    <BaseNode
      id={props.id}
      data={props.data as unknown as NodeData}
      selected={props.selected}
    />
  );
}
```

- [ ] **Step 2: Build check**

```bash
cd /DATA3/users/mj/AgentBuilder/frontend && npm run build
```

- [ ] **Step 3: Commit**

```bash
cd /DATA3/users/mj/AgentBuilder/frontend
git add components/workflow/nodes/BaseNode.tsx
git commit -m "feat: redesign BaseNode — thin border, color dot, Lucide icon, field preview"
```

---

## Task 7: Workflow Editor Toolbar Redesign

**Files:**
- Modify: `frontend/components/workflow/WorkflowEditor.tsx`

- [ ] **Step 1: Update toolbar section in WorkflowEditor.tsx**

In `WorkflowEditor.tsx`, replace the `<header>` toolbar block (lines ~105-141) with:

```tsx
      {/* Toolbar */}
      <header className="flex items-center border-b border-clay-border bg-clay-surface px-4 py-2">
        {/* Back */}
        <Link
          href="/workflows"
          className="flex items-center gap-1 text-sm text-warmSilver hover:text-clayBlack transition-colors"
        >
          <ChevronLeft className="h-4 w-4" />
          목록
        </Link>
        <div className="mx-3 h-5 w-px bg-clay-border" />

        {/* Workflow name */}
        <span className="font-semibold text-clayBlack">{workflowName}</span>

        <div className="ml-auto flex items-center gap-1">
          {/* Sidebar toggles */}
          <button
            onClick={() => toggleSidebar('components')}
            className={cn(
              'flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition-colors',
              sidebarOpen && useSidebarStore.getState().activePanel === 'components'
                ? 'bg-clayBlack text-white'
                : 'text-clay-text hover:bg-oat-light',
            )}
          >
            <LayoutGrid className="h-3.5 w-3.5" />
            컴포넌트
          </button>
          <button
            onClick={() => toggleSidebar('mcp')}
            className={cn(
              'flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition-colors',
              sidebarOpen && useSidebarStore.getState().activePanel === 'mcp'
                ? 'bg-clayBlack text-white'
                : 'text-clay-text hover:bg-oat-light',
            )}
          >
            <Plug className="h-3.5 w-3.5" />
            MCP
          </button>
          <button
            onClick={() => toggleSidebar('runlog')}
            className={cn(
              'flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition-colors',
              sidebarOpen && useSidebarStore.getState().activePanel === 'runlog'
                ? 'bg-clayBlack text-white'
                : 'text-clay-text hover:bg-oat-light',
            )}
          >
            <Activity className="h-3.5 w-3.5" />
            로그
          </button>

          <div className="mx-2 h-5 w-px bg-clay-border" />

          {/* Playground toggle */}
          <button
            onClick={() => setPlaygroundOpen((v) => !v)}
            className={cn(
              'flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs font-medium transition-colors',
              playgroundOpen
                ? 'border-clay-accent bg-clay-accent text-white'
                : 'border-clay-accent text-clay-accent hover:bg-clay-accent/5',
            )}
          >
            <Play className="h-3.5 w-3.5" />
            실행
          </button>

          <div className="mx-2 h-5 w-px bg-clay-border" />

          {/* Save */}
          <span className="flex items-center gap-1 text-[10px] text-warmSilver">
            <span className="h-1.5 w-1.5 rounded-full bg-clay-accent" />
            자동 저장
          </span>
          <Button
            onClick={handleManualSave}
            disabled={saving}
            size="sm"
            className="ml-1"
          >
            <Save className="h-3.5 w-3.5" />
            {saving ? '저장 중...' : '저장'}
          </Button>
        </div>
      </header>
```

- [ ] **Step 2: Add imports at the top of WorkflowEditor.tsx**

Add these imports at the top of the file:

```tsx
import { Activity, ChevronLeft, LayoutGrid, Play, Plug, Save } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
```

- [ ] **Step 3: Build check**

```bash
cd /DATA3/users/mj/AgentBuilder/frontend && npm run build
```

- [ ] **Step 4: Commit**

```bash
cd /DATA3/users/mj/AgentBuilder/frontend
git add components/workflow/WorkflowEditor.tsx
git commit -m "feat: redesign workflow toolbar — Lucide icons, dividers, matcha run button"
```

---

## Task 8: Sidebar Redesign

**Files:**
- Modify: `frontend/components/workflow/Sidebar.tsx`

- [ ] **Step 1: Update Sidebar with Lucide icons and dot system**

In `Sidebar.tsx`, replace the imports and update:

Add imports at top:
```tsx
import { LayoutGrid, Plug, Activity, X } from 'lucide-react';
import { NODE_STYLES } from './nodes/nodeStyles';
```

Replace the `panelTitle` function:
```tsx
function panelTitle(activePanel: string | null): { label: string; icon: React.ReactNode } {
  if (activePanel === 'components') return { label: '컴포넌트', icon: <LayoutGrid className="h-4 w-4" /> };
  if (activePanel === 'mcp') return { label: 'MCP 도구', icon: <Plug className="h-4 w-4" /> };
  if (activePanel === 'runlog') return { label: '실행 로그', icon: <Activity className="h-4 w-4" /> };
  return { label: '', icon: null };
}
```

Replace the `ComponentsPanel` node buttons — change each button from emoji+colored-border to dot+icon:
```tsx
{filtered.map((type) => {
  const style = NODE_STYLES[type];
  const Icon = style.icon;
  return (
    <button
      key={type}
      type="button"
      onClick={() => handleClick(type)}
      className="flex w-full items-center gap-2 rounded-card border border-clay-border bg-white px-3 py-2 text-sm transition-all hover:border-clay-accent hover:shadow-clay-1 active:scale-[0.98]"
    >
      <div className={cn('h-2 w-2 rounded-full flex-shrink-0', style.dotColor)} />
      <Icon className="h-4 w-4 text-warmSilver" />
      <span className="font-medium text-clayBlack">{style.label}</span>
      <span className="ml-auto text-xs text-warmSilver">+</span>
    </button>
  );
})}
```

Replace the sidebar header to use icon + label (not emoji):
```tsx
<div className="flex items-center justify-between border-b border-clay-border px-4 py-2">
  <div className="flex items-center gap-2">
    {panelTitle(activePanel).icon}
    <span className="text-sm font-semibold text-clayBlack">
      {panelTitle(activePanel).label}
    </span>
  </div>
  <button
    onClick={close}
    aria-label="닫기"
    className="text-warmSilver hover:text-clayBlack transition-colors"
  >
    <X className="h-4 w-4" />
  </button>
</div>
```

Also import `cn` from `@/lib/utils` and `import { cn } from '@/lib/utils';`.

- [ ] **Step 2: Build check**

```bash
cd /DATA3/users/mj/AgentBuilder/frontend && npm run build
```

- [ ] **Step 3: Commit**

```bash
cd /DATA3/users/mj/AgentBuilder/frontend
git add components/workflow/Sidebar.tsx
git commit -m "feat: redesign Sidebar — Lucide icons, color dots, clean node buttons"
```

---

## Task 9: NodeConfigPanel — shadcn Forms + Dot Header

**Files:**
- Modify: `frontend/components/workflow/NodeConfigPanel.tsx`

- [ ] **Step 1: Update imports and header**

Add at top of `NodeConfigPanel.tsx`:
```tsx
import { X } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Select } from '@/components/ui/select';
import { cn } from '@/lib/utils';
import { NODE_STYLES } from './nodes/nodeStyles';
```

- [ ] **Step 2: Replace the panel header**

Find the panel header (which currently uses colored icon + colored label) and replace with:
```tsx
<div className="flex items-center gap-2 border-b border-clay-border px-4 py-3">
  <div className={cn('h-2 w-2 rounded-full', NODE_STYLES[nodeType].dotColor)} />
  {React.createElement(NODE_STYLES[nodeType].icon, { className: 'h-4 w-4 text-warmSilver' })}
  <span className="text-sm font-semibold text-clayBlack">{NODE_STYLES[nodeType].label}</span>
  <button onClick={onClose} className="ml-auto text-warmSilver hover:text-clayBlack transition-colors">
    <X className="h-4 w-4" />
  </button>
</div>
```

- [ ] **Step 3: Replace form field elements**

Throughout NodeConfigPanel.tsx:
- Replace all `<select ... className="input-field">` with `<Select ...>`
- Replace all `<input ... className="input-field">` with `<Input ...>`
- Replace all `<textarea ... className="input-field">` with `<Textarea ...>`
- Replace all `className="input-field"` usages

For the `Field` component label, change to uppercase style:
```tsx
function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="mb-1 block text-[11px] font-semibold uppercase tracking-wide text-warmSilver">
        {label}
      </label>
      {children}
    </div>
  );
}
```

- [ ] **Step 4: Update panel width from w-72 (288px) to w-80 (320px)**

Find the panel container `className` and change `w-72` to `w-80`.

- [ ] **Step 5: Build check**

```bash
cd /DATA3/users/mj/AgentBuilder/frontend && npm run build
```

- [ ] **Step 6: Commit**

```bash
cd /DATA3/users/mj/AgentBuilder/frontend
git add components/workflow/NodeConfigPanel.tsx
git commit -m "feat: redesign NodeConfigPanel — shadcn forms, dot header, uppercase labels"
```

---

## Task 10: PlaygroundPanel — Message Colors + Icons

**Files:**
- Modify: `frontend/components/workflow/PlaygroundPanel.tsx`

- [ ] **Step 1: Update imports**

Add at top:
```tsx
import { Play, Send, Check, AlertCircle, Wrench, MessageSquare } from 'lucide-react';
```

- [ ] **Step 2: Replace emoji/colors throughout**

Apply these replacements in PlaygroundPanel.tsx:
- User message class: `bg-blue-600 text-white` → `bg-clayBlack text-white`
- User message border-radius: keep `rounded-xl` but change to `rounded-2xl rounded-br-sm`
- Assistant message: keep `bg-cream border border-clay-border`, change radius to `rounded-2xl rounded-bl-sm`
- Send button: `bg-green-600` → `bg-clay-accent`, replace text "전송" with `<Send className="h-4 w-4" />`
- Header: replace `▶ 플레이그라운드` with `<Play className="h-4 w-4 text-clay-accent" /> 플레이그라운드`
- Pulsing green dot: keep as-is (already matches matcha)

For node event icons in the inline log, replace emoji strings:
```tsx
const EVENT_DISPLAY: Record<string, { icon: React.ReactNode; label: string }> = {
  node_start: { icon: <Play className="h-3 w-3" />, label: '노드 시작' },
  node_end: { icon: <Check className="h-3 w-3" />, label: '노드 완료' },
  tool_call: { icon: <Wrench className="h-3 w-3" />, label: '도구 호출' },
  workflow_end: { icon: <Check className="h-3 w-3 text-green-600" />, label: '완료' },
  workflow_error: { icon: <AlertCircle className="h-3 w-3 text-red-500" />, label: '에러' },
};
```

- [ ] **Step 3: Build check**

```bash
cd /DATA3/users/mj/AgentBuilder/frontend && npm run build
```

- [ ] **Step 4: Commit**

```bash
cd /DATA3/users/mj/AgentBuilder/frontend
git add components/workflow/PlaygroundPanel.tsx
git commit -m "feat: redesign PlaygroundPanel — black user messages, Lucide icons, matcha send button"
```

---

## Task 11: RunLogPanel — Lucide Icons + Badge

**Files:**
- Modify: `frontend/components/workflow/RunLogPanel.tsx`

- [ ] **Step 1: Update imports**

Add at top:
```tsx
import { Play, Check, MessageSquare, Wrench, ClipboardList, CheckCircle, AlertCircle, RefreshCw } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
```

- [ ] **Step 2: Replace EVENT_ICONS emoji map with Lucide components**

Replace the `EVENT_ICONS` constant:
```tsx
const EVENT_ICONS: Record<string, React.ReactNode> = {
  node_start: <Play className="h-3.5 w-3.5" />,
  node_end: <Check className="h-3.5 w-3.5" />,
  llm_token: <MessageSquare className="h-3.5 w-3.5" />,
  tool_call: <Wrench className="h-3.5 w-3.5" />,
  tool_result: <ClipboardList className="h-3.5 w-3.5" />,
  workflow_end: <CheckCircle className="h-3.5 w-3.5" />,
  workflow_error: <AlertCircle className="h-3.5 w-3.5" />,
};
```

- [ ] **Step 3: Replace status badges**

Replace inline status badges (currently `<span className="... STATUS_COLORS[run.status]">`) with:
```tsx
<Badge variant={
  run.status === 'success' ? 'success' :
  run.status === 'failed' ? 'destructive' :
  run.status === 'running' ? 'info' : 'default'
}>
  {STATUS_LABELS[run.status]}
</Badge>
```

- [ ] **Step 4: Replace refresh button emoji**

Replace `🔄` with `<RefreshCw className="h-3.5 w-3.5" />` in the refresh button.

- [ ] **Step 5: Build check**

```bash
cd /DATA3/users/mj/AgentBuilder/frontend && npm run build
```

- [ ] **Step 6: Commit**

```bash
cd /DATA3/users/mj/AgentBuilder/frontend
git add components/workflow/RunLogPanel.tsx
git commit -m "feat: redesign RunLogPanel — Lucide icons, Badge status indicators"
```

---

## Task 12: Knowledge Pages

**Files:**
- Modify: `frontend/components/knowledge/KbList.tsx`
- Modify: `frontend/components/knowledge/CreateKbForm.tsx`
- Modify: `frontend/components/knowledge/IngestionProgress.tsx`
- Modify: `frontend/components/knowledge/FileUpload.tsx`
- Modify: `frontend/components/knowledge/SearchPanel.tsx`
- Modify: `frontend/app/knowledge/page.tsx`

- [ ] **Step 1: Rewrite KbList.tsx with icon badges, meta info, action buttons**

Replace entire content of `frontend/components/knowledge/KbList.tsx`:

```tsx
import Link from 'next/link';
import { BookOpen, File, Layers, Plus } from 'lucide-react';
import type { KnowledgeBase } from '@/lib/knowledge';

export function KbList({ items }: { items: KnowledgeBase[] }) {
  return (
    <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {items.map((kb) => (
        <li key={kb.id}>
          <Link
            href={`/knowledge/${kb.id}`}
            className="block rounded-card border border-clay-border bg-white p-4 transition-all hover:border-clay-accent hover:shadow-clay-2"
          >
            <div className="flex items-center gap-3 mb-3">
              <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-green-50 text-emerald-600">
                <BookOpen className="h-[18px] w-[18px]" />
              </div>
              <span className="text-sm font-semibold text-clayBlack">{kb.name}</span>
            </div>
            <p className="line-clamp-2 text-xs text-warmSilver mb-3">
              {kb.description || '설명 없음'}
            </p>
            <div className="flex gap-3 text-[11px] text-warmSilver">
              <span className="flex items-center gap-1">
                <File className="h-3 w-3" />
                {kb.embedding_provider}
              </span>
              <span className="flex items-center gap-1">
                <Layers className="h-3 w-3" />
                dim {kb.embedding_dim}
              </span>
            </div>
          </Link>
        </li>
      ))}

      {/* Empty state or add-new card */}
      {items.length === 0 && (
        <li className="sm:col-span-2 lg:col-span-3">
          <div className="rounded-card border border-dashed border-clay-border p-10 text-center">
            <Plus className="mx-auto h-10 w-10 text-clay-border mb-3" />
            <h4 className="text-sm font-semibold text-clay-text mb-1">지식베이스 추가</h4>
            <p className="text-xs text-warmSilver">
              파일을 업로드하여 에이전트의 지식을 구축하세요
            </p>
          </div>
        </li>
      )}
    </ul>
  );
}
```

- [ ] **Step 2: Update knowledge page header**

In `frontend/app/knowledge/page.tsx`, update the page header to use the unified pattern:
- Title + subtitle + action button layout
- Replace `rounded-full` button with `rounded-lg`
- Replace `+` text with `<Plus />` icon

- [ ] **Step 3: Update CreateKbForm — shadcn components**

In `frontend/components/knowledge/CreateKbForm.tsx`:
- Import `{ Input }` from `@/components/ui/input`, `{ Textarea }` from `@/components/ui/textarea`, `{ Select }` from `@/components/ui/select`, `{ Button }` from `@/components/ui/button`
- Replace all `<input className="rounded-lg border border-clay-border bg-white...">` with `<Input />`
- Replace `<textarea>` with `<Textarea />`
- Replace `<select>` with `<Select />`
- Replace submit button with `<Button>생성</Button>`
- Replace the "고급 설정 펼치기" toggle with shadcn Collapsible if desired, or just keep the current toggle

- [ ] **Step 4: Update IngestionProgress — replace emojis**

In `frontend/components/knowledge/IngestionProgress.tsx`:
- Import `{ Upload, Check, AlertCircle, ChevronDown, ChevronUp }` from `lucide-react`
- Replace any emoji icons with Lucide equivalents

- [ ] **Step 5: Update FileUpload — replace emojis**

In `frontend/components/knowledge/FileUpload.tsx`:
- Import `{ Upload }` from `lucide-react`
- Replace upload area icon/emoji with `<Upload className="h-8 w-8 text-warmSilver" />`
- Replace "파일 선택" button with `<Button variant="outline" size="sm">`

- [ ] **Step 6: Update SearchPanel — shadcn input**

In `frontend/components/knowledge/SearchPanel.tsx`:
- Import `{ Input }` from `@/components/ui/input`, `{ Button }` from `@/components/ui/button`, `{ Search }` from `lucide-react`
- Replace search input with `<Input />`
- Replace search button with `<Button size="sm"><Search className="h-4 w-4" /> 검색</Button>`

- [ ] **Step 7: Build check**

```bash
cd /DATA3/users/mj/AgentBuilder/frontend && npm run build
```

- [ ] **Step 8: Commit**

```bash
cd /DATA3/users/mj/AgentBuilder/frontend
git add components/knowledge/ app/knowledge/
git commit -m "feat: redesign Knowledge pages — icon badges, shadcn forms, empty state"
```

---

## Task 13: Tools Pages (MCP)

**Files:**
- Modify: `frontend/components/mcp/McpServerList.tsx`
- Modify: `frontend/components/mcp/RegisterMcpModal.tsx`
- Modify: `frontend/components/mcp/ToolCatalog.tsx`
- Modify: `frontend/app/tools/page.tsx`

- [ ] **Step 1: Update McpServerList — Lucide icons + Badge**

In `frontend/components/mcp/McpServerList.tsx`:
- Import `{ Terminal, Globe, Zap, RefreshCw, Trash2, Power } from 'lucide-react'` and `{ Badge } from '@/components/ui/badge'` and `{ Button } from '@/components/ui/button'`
- Replace `TRANSPORT_ICON` map: `{ stdio: '📦', http_sse: '🌐', streamable_http: '⚡' }` → use Lucide components:
```tsx
const TRANSPORT_ICON: Record<string, React.ReactNode> = {
  stdio: <Terminal className="h-[18px] w-[18px]" />,
  http_sse: <Globe className="h-[18px] w-[18px]" />,
  streamable_http: <Zap className="h-[18px] w-[18px]" />,
};
```
- Replace status pill with `<Badge variant={server.enabled ? 'success' : 'default'}>{server.enabled ? 'Active' : 'Inactive'}</Badge>`
- Replace 🔄 with `<RefreshCw />`, 삭제 text with `<Trash2 />`
- Replace inline buttons with `<Button variant="outline" size="sm">` and `<Button variant="ghost" size="sm">`

- [ ] **Step 2: Rewrite RegisterMcpModal with shadcn Dialog + Tabs**

Replace `frontend/components/mcp/RegisterMcpModal.tsx` to use:
- `<Dialog>` + `<DialogContent>` instead of custom `fixed inset-0` overlay
- `<Tabs>` + `<TabsList>` + `<TabsTrigger>` + `<TabsContent>` instead of custom segmented control
- `<Input>` and `<Textarea>` instead of custom inputs
- `<Button>` instead of custom buttons
- Replace emoji in tab labels: `'📦 STDIO'` → `'STDIO'`, `'🌐 HTTP/SSE'` → `'HTTP/SSE'`, `'⚡ Streamable HTTP'` → `'Streamable HTTP'`

The Dialog prop changes: instead of `onClose` being called directly, use `<Dialog open={true} onOpenChange={(open) => { if (!open) onClose(); }}>`.

- [ ] **Step 3: Update ToolCatalog — tag chip style**

In `frontend/components/mcp/ToolCatalog.tsx`:
- Replace card style with tag chip: `rounded-md border border-oat-light bg-clay-surface px-2 py-1 text-[11px]`

- [ ] **Step 4: Update tools page header**

In `frontend/app/tools/page.tsx`:
- Change title from "도구 (MCP 서버)" to "도구"
- Add subtitle "MCP 서버를 연결하여 에이전트에 외부 도구를 제공합니다"
- Replace button with `<Button><Plus /> MCP 서버 추가</Button>`

- [ ] **Step 5: Build check**

```bash
cd /DATA3/users/mj/AgentBuilder/frontend && npm run build
```

- [ ] **Step 6: Commit**

```bash
cd /DATA3/users/mj/AgentBuilder/frontend
git add components/mcp/ app/tools/
git commit -m "feat: redesign Tools pages — shadcn Dialog/Tabs, Lucide icons, Badge status"
```

---

## Task 14: Settings Page Redesign

**Files:**
- Modify: `frontend/components/settings/SettingsPage.tsx`
- Modify: `frontend/app/settings/page.tsx`

- [ ] **Step 1: Update SettingsPage**

In `frontend/components/settings/SettingsPage.tsx`:
- Import `{ Lock, Globe, Settings, Plus, Pencil, Trash2 } from 'lucide-react'` and `{ Badge } from '@/components/ui/badge'` and `{ Button } from '@/components/ui/button'` and `{ Input } from '@/components/ui/input'`
- Replace `CATEGORY_LABELS` emoji map:
```tsx
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
```
- Replace category group headers: use icon + uppercase label
```tsx
<div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-warmSilver mb-2">
  {CATEGORY_ICON[category]}
  {CATEGORY_LABELS[category]}
</div>
```
- Replace SECRET badge: `<Badge variant="secret">SECRET</Badge>`
- Replace edit/delete buttons with `<Button variant="outline" size="sm"><Pencil className="h-3 w-3" /></Button>` and `<Button variant="ghost" size="sm" className="text-red-500"><Trash2 className="h-3 w-3" /></Button>`
- Replace inline add form with `<Dialog>` (or keep inline but use shadcn `<Input>`)
- Replace all `<input>` with `<Input />`

- [ ] **Step 2: Update settings page title**

In `frontend/app/settings/page.tsx`:
- Change the page title from "환경변수" to "설정"
- Add subtitle

- [ ] **Step 3: Build check**

```bash
cd /DATA3/users/mj/AgentBuilder/frontend && npm run build
```

- [ ] **Step 4: Commit**

```bash
cd /DATA3/users/mj/AgentBuilder/frontend
git add components/settings/ app/settings/
git commit -m "feat: redesign Settings page — Lucide icons, Badge, shadcn inputs, rename to 설정"
```

---

## Task 15: Workflow List Redesign

**Files:**
- Modify: `frontend/components/workflow/WorkflowList.tsx`

- [ ] **Step 1: Update WorkflowList**

In `frontend/components/workflow/WorkflowList.tsx`:
- Import `{ Plus, Pencil, Trash2, Workflow } from 'lucide-react'` and `{ Button } from '@/components/ui/button'` and `{ Input } from '@/components/ui/input'`
- Replace `+ 새 워크플로우` button: `<Button><Plus className="h-4 w-4" /> 새 워크플로우</Button>`
- Replace `rounded bg-clayBlack px-4 py-2 text-sm text-white` create button with `<Button />`
- Replace create form input with `<Input />`
- Replace card style: ensure it uses `rounded-card border border-clay-border bg-white p-4 shadow-clay-1 hover:border-clay-accent hover:shadow-clay-2 transition-all`
- Add icon badge to each card: `<Workflow className="h-4 w-4 text-warmSilver" />`
- Replace 편집 button with `<Button variant="outline" size="sm"><Pencil className="h-3 w-3" /> 편집</Button>`
- Replace ✕ delete with `<button className="text-warmSilver hover:text-red-500"><Trash2 className="h-4 w-4" /></button>`

- [ ] **Step 2: Build check**

```bash
cd /DATA3/users/mj/AgentBuilder/frontend && npm run build
```

- [ ] **Step 3: Commit**

```bash
cd /DATA3/users/mj/AgentBuilder/frontend
git add components/workflow/WorkflowList.tsx
git commit -m "feat: redesign Workflow list — Lucide icons, shadcn Button/Input, card hover effects"
```

---

## Task 16: Final Build Verification

- [ ] **Step 1: Full build**

```bash
cd /DATA3/users/mj/AgentBuilder/frontend && npm run build
```

Expected: Build succeeds with zero errors.

- [ ] **Step 2: Visual spot-check**

```bash
cd /DATA3/users/mj/AgentBuilder/frontend && npm run dev
```

Open http://localhost:3000 and verify:
- TopNav shows logo badge + icons + active indicator
- No emoji visible anywhere
- Workflow editor nodes show thin border + color dots
- All pages use consistent card/button styles

- [ ] **Step 3: Grep for remaining emojis**

```bash
cd /DATA3/users/mj/AgentBuilder/frontend
grep -rn '💬\|📤\|🧠\|🤖\|📚\|📝\|💾\|🔄\|📦\|🔌\|📊\|🔧\|📋\|✅\|❌\|⚡\|🌐\|🔑\|⚙️' components/ app/ --include='*.tsx' --include='*.ts'
```

Expected: No matches (all emojis replaced).

- [ ] **Step 4: Final commit if any fixes needed**

```bash
cd /DATA3/users/mj/AgentBuilder/frontend
git add -A
git commit -m "fix: resolve remaining emoji references and build issues"
```
