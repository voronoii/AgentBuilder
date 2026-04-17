import { SettingsClient } from '@/components/settings/SettingsPage';

export default function SettingsPage() {
  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-semibold tracking-tight text-clayBlack">
          설정
        </h1>
        <p className="mt-1 text-sm text-warmSilver">
          API 키와 엔드포인트를 관리합니다. 여기에 등록된 값은 워크플로우의
          모델 노드와 MCP 도구에서 사용됩니다.
        </p>
      </div>
      <SettingsClient />
    </div>
  );
}
