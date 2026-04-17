import Link from 'next/link';
import {
  BookOpen,
  Workflow,
  Wrench,
  Settings,
  ArrowRight,
  Cpu,
  Bot,
  Zap,
} from 'lucide-react';
import { fetchHealth } from '@/lib/api';

export const dynamic = 'force-dynamic';

const features = [
  {
    href: '/knowledge',
    icon: BookOpen,
    title: '지식',
    description: '파일을 업로드하고 에이전트가 참조할 지식베이스를 구축합니다.',
    color: 'bg-violet-50 text-violet-600',
  },
  {
    href: '/workflows',
    icon: Workflow,
    title: '워크플로우',
    description: '노드 기반 캔버스에서 LLM, 도구, 지식을 조합하여 에이전트를 만듭니다.',
    color: 'bg-blue-50 text-blue-600',
  },
  {
    href: '/tools',
    icon: Wrench,
    title: '도구',
    description: 'MCP 서버를 연결하여 에이전트에 외부 도구를 제공합니다.',
    color: 'bg-amber-50 text-amber-600',
  },
  {
    href: '/settings',
    icon: Settings,
    title: '설정',
    description: 'API 키, 엔드포인트 등 LLM 프로바이더 설정을 관리합니다.',
    color: 'bg-slate-50 text-slate-600',
  },
];

export default async function HomePage() {
  let apiOk = false;
  let version = '';

  try {
    const health = await fetchHealth();
    apiOk = health.status === 'ok';
    version = health.version;
  } catch {
    apiOk = false;
  }

  return (
    <main className="min-h-[calc(100vh-64px)]">
      {/* Hero */}
      <section className="py-16 text-center">
        <div className="mx-auto max-w-2xl">
          <div className="mb-6 flex justify-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-violet-100 text-violet-600">
              <Bot className="h-5 w-5" />
            </div>
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-100 text-blue-600">
              <Cpu className="h-5 w-5" />
            </div>
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-amber-100 text-amber-600">
              <Zap className="h-5 w-5" />
            </div>
          </div>

          <h1 className="text-3xl font-bold tracking-tight text-clayBlack sm:text-4xl">
            AgentBuilder
          </h1>
          <p className="mt-3 text-base text-warmSilver">
            노드 기반 캔버스에서 LLM, 지식베이스, MCP 도구를 조합하여
            <br className="hidden sm:block" />
            에이전트 워크플로우를 만들고 실행하세요.
          </p>

          <div className="mt-6 flex items-center justify-center gap-4">
            <Link
              href="/workflows"
              className="inline-flex items-center gap-2 rounded-lg bg-clay-accent px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-clay-accent/90"
            >
              시작하기
              <ArrowRight className="h-4 w-4" />
            </Link>
            <div className="flex items-center gap-2 text-xs text-warmSilver">
              <span className={`h-2 w-2 rounded-full ${apiOk ? 'bg-emerald-500' : 'bg-red-400'}`} />
              {apiOk ? 'API 연결됨' : 'API 연결 실패'}
              {version && <span className="text-clay-border">v{version}</span>}
            </div>
          </div>
        </div>
      </section>

      {/* Feature cards */}
      <section className="mx-auto max-w-3xl px-6 pb-16">
        <div className="grid gap-4 sm:grid-cols-2">
          {features.map((f) => {
            const Icon = f.icon;
            return (
              <Link
                key={f.href}
                href={f.href}
                className="group flex items-start gap-4 rounded-card border border-clay-border bg-white p-5 transition-all hover:border-clay-accent hover:shadow-clay-2"
              >
                <div className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-lg ${f.color}`}>
                  <Icon className="h-5 w-5" />
                </div>
                <div className="min-w-0">
                  <h3 className="text-sm font-semibold text-clayBlack group-hover:text-clay-accent transition-colors">
                    {f.title}
                  </h3>
                  <p className="mt-1 text-xs leading-relaxed text-warmSilver">
                    {f.description}
                  </p>
                </div>
                <ArrowRight className="ml-auto mt-1 h-4 w-4 shrink-0 text-clay-border transition-colors group-hover:text-clay-accent" />
              </Link>
            );
          })}
        </div>
      </section>
    </main>
  );
}
