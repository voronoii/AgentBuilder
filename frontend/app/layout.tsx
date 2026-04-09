import './globals.css';
import type { Metadata } from 'next';
import { TopNav } from '@/components/nav/TopNav';

export const metadata: Metadata = { title: 'AgentBuilder' };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko">
      <body className="min-h-screen bg-clay-bg text-clay-text">
        <TopNav />
        <main className="mx-auto max-w-6xl px-6 py-8">{children}</main>
      </body>
    </html>
  );
}
