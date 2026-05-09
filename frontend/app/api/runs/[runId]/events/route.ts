// SSE proxy for run events.
//
// Why this exists: Next.js middleware의 `NextResponse.rewrite()` 는 SSE 같은
// long-lived streaming 응답을 적시에 flush하지 않고 buffer해서 client 가 첫
// chunk 를 수십 초 늦게 받는 문제가 있다. Route Handler 에서 fetch 응답의
// body 를 그대로 `new Response(body)` 로 pass-through 하면 streaming 이
// 정상 동작한다. middleware 는 이 경로를 NextResponse.next() 로 통과시켜야 한다.

import type { NextRequest } from 'next/server';

const API_BACKEND = process.env.API_URL_INTERNAL ?? 'http://api:8000';

export const dynamic = 'force-dynamic';
export const runtime = 'nodejs';

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ runId: string }> },
) {
  const { runId } = await params;
  const upstream = await fetch(`${API_BACKEND}/runs/${runId}/events`, {
    method: 'GET',
    headers: { Accept: 'text/event-stream' },
    cache: 'no-store',
    // @ts-expect-error — Node.js fetch에서 streaming body를 위해 필요
    duplex: 'half',
  });

  return new Response(upstream.body, {
    status: upstream.status,
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache, no-transform',
      Connection: 'keep-alive',
      // 일부 프록시 / Next.js 자체 buffer 회피용
      'X-Accel-Buffering': 'no',
    },
  });
}
