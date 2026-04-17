import { NextRequest, NextResponse } from 'next/server';

const API_URL = (process.env.API_URL_INTERNAL ?? 'http://localhost:28000').replace(/\/$/, '');

async function getApiKey(appId: string): Promise<string | null> {
  try {
    const res = await fetch(`${API_URL}/apps/${appId}/api-key`, { cache: 'no-store' });
    if (!res.ok) return null;
    const data = await res.json();
    return data.api_key;
  } catch {
    return null;
  }
}

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ appId: string }> },
) {
  const { appId } = await params;
  const body = await request.json();

  const apiKey = await getApiKey(appId);
  if (!apiKey) {
    return NextResponse.json({ error: 'App not found' }, { status: 404 });
  }

  const res = await fetch(`${API_URL}/v1/chat/completions`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${apiKey}`,
    },
    body: JSON.stringify(body),
  });

  if (body.stream) {
    return new NextResponse(res.body, {
      headers: {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
      },
    });
  }

  const data = await res.json();
  return NextResponse.json(data, { status: res.status });
}

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ appId: string }> },
) {
  const { appId } = await params;
  const url = new URL(request.url);
  const convId = url.searchParams.get('conversation_id');

  const apiKey = await getApiKey(appId);
  if (!apiKey) {
    return NextResponse.json({ error: 'App not found' }, { status: 404 });
  }

  const endpoint = convId
    ? `${API_URL}/v1/conversations/${convId}/messages`
    : `${API_URL}/v1/conversations`;

  const res = await fetch(endpoint, {
    headers: { 'Authorization': `Bearer ${apiKey}` },
    cache: 'no-store',
  });
  const data = await res.json();
  return NextResponse.json(data, { status: res.status });
}

export async function DELETE(
  request: NextRequest,
  { params }: { params: Promise<{ appId: string }> },
) {
  const { appId } = await params;
  const url = new URL(request.url);
  const convId = url.searchParams.get('conversation_id');
  if (!convId) {
    return NextResponse.json({ error: 'conversation_id required' }, { status: 400 });
  }

  const apiKey = await getApiKey(appId);
  if (!apiKey) {
    return NextResponse.json({ error: 'App not found' }, { status: 404 });
  }

  const res = await fetch(`${API_URL}/v1/conversations/${convId}`, {
    method: 'DELETE',
    headers: { 'Authorization': `Bearer ${apiKey}` },
  });
  return new NextResponse(null, { status: res.status });
}
