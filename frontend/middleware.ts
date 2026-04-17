import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

const API_BACKEND = process.env.API_URL_INTERNAL ?? 'http://api:8000';

export function middleware(request: NextRequest) {
  const { pathname, search } = request.nextUrl;

  // Let Next.js API routes handle /api/chat/*
  if (pathname.startsWith('/api/chat/')) {
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
