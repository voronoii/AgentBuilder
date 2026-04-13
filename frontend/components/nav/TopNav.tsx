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
