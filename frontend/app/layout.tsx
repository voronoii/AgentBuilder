import './globals.css';
import type { Metadata } from 'next';
import localFont from 'next/font/local';
import { TopNav } from '@/components/nav/TopNav';

const kopub = localFont({
  src: [
    { path: './fonts/KoPubWorld-Dotum-Light.woff2', weight: '300', style: 'normal' },
    { path: './fonts/KoPubWorld-Dotum-Medium.woff2', weight: '500', style: 'normal' },
    { path: './fonts/KoPubWorld-Dotum-Bold.woff2', weight: '700', style: 'normal' },
  ],
  variable: '--font-kopub',
  display: 'swap',
});

export const metadata: Metadata = { title: 'AgentBuilder' };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko" className={kopub.variable}>
      <body className="min-h-screen bg-clay-bg font-kopub text-clay-text">
        <TopNav />
        <main className="mx-auto max-w-6xl px-6 py-8">{children}</main>
      </body>
    </html>
  );
}
