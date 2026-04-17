import { AppListClient } from '@/components/apps/AppList';

export default function AppsPage() {
  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-semibold tracking-tight text-clayBlack">앱</h1>
      </div>
      <AppListClient />
    </div>
  );
}
