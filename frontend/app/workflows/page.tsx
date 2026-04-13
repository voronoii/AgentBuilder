import { WorkflowListClient } from '@/components/workflow/WorkflowList';

export default function WorkflowsPage() {
  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-semibold tracking-tight text-clayBlack">
          워크플로우
        </h1>
      </div>
      <WorkflowListClient />
    </div>
  );
}
