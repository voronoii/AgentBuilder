import { ChatApp } from '@/components/chat/ChatApp';

interface ChatPageProps {
  params: Promise<{ appId: string }>;
}

export default async function ChatPage({ params }: ChatPageProps) {
  const { appId } = await params;
  return <ChatApp appId={appId} />;
}
