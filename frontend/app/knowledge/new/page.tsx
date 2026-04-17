import { CreateKbForm } from '@/components/knowledge/CreateKbForm';

export default function NewKbPage() {
  return (
    <section className="max-w-xl space-y-6">
      <h1 className="text-2xl font-semibold">새 지식베이스</h1>
      <CreateKbForm />
    </section>
  );
}
