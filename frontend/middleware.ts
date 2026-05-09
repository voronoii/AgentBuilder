import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

const API_BACKEND = process.env.API_URL_INTERNAL ?? 'http://api:8000';

export function middleware(request: NextRequest) {
  const { pathname, search } = request.nextUrl;

  // Let Next.js API routes handle /api/chat/*
  if (pathname.startsWith('/api/chat/')) {
    return NextResponse.next();
  }

  // SSE 스트림은 NextResponse.rewrite 가 chunk 를 buffer 하므로 Route
  // Handler (/app/api/runs/[runId]/events/route.ts)가 fetch + new Response 로
  // 직접 pass-through 하도록 middleware 는 통과시킨다.
  if (/^\/api\/runs\/[^/]+\/events\/?$/.test(pathname)) {
    return NextResponse.next();
  }

  // Proxy all other /api/* to the backend
  if (pathname.startsWith('/api/')) {
    const backendPath = pathname.replace(/^\/api/, '');
    const url = new URL(`${API_BACKEND}${backendPath}${search}`);
    return NextResponse.rewrite(url);
  }

  return NextResponse.next();
}

export const config = {
  matcher: '/api/:path*',
};
