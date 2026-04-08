import type { Metadata } from 'next';
import type { ReactNode } from 'react';
import './globals.css';

export const metadata: Metadata = {
  title: 'AgentBuilder',
  description: 'Build agent workflows visually',
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="ko">
      <body className="bg-cream text-clayBlack">{children}</body>
    </html>
  );
}
