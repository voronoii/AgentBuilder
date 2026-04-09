import Link from 'next/link';

const tabs = [
  { href: '/knowledge', label: '지식' },
  { href: '/workflows', label: '워크플로우' },
  { href: '/tools', label: '도구' },
];

export function TopNav() {
  return (
    <header className="border-b border-clay-border bg-clay-surface">
      <nav className="mx-auto flex max-w-6xl items-center gap-6 px-6 py-4" aria-label="Main navigation">
        <span className="text-lg font-semibold tracking-tight">AgentBuilder</span>
        <ul className="flex gap-4">
          {tabs.map((t) => (
            <li key={t.href}>
              <Link href={t.href} className="text-sm text-clay-text hover:text-clay-accent">
                {t.label}
              </Link>
            </li>
          ))}
        </ul>
      </nav>
    </header>
  );
}
