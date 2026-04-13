import { WorkflowEditor } from '@/components/workflow/WorkflowEditor';

interface EditPageProps {
  params: Promise<{ id: string }>;
}

export default async function WorkflowEditPage({ params }: EditPageProps) {
  const { id } = await params;
  return <WorkflowEditor workflowId={id} />;
}
