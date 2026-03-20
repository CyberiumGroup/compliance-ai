'use client';

import { useState, useEffect, use } from 'react';
import Link from 'next/link';
import { Layers } from 'lucide-react';
import { LoadingSpinner } from '@/components/ui';
import { getAssessmentScope, listFrameworks } from '@/lib/api';
import { useUserId } from '@/lib/hooks/useUserId';
import { WorkflowStepper } from '@/components/assessment/WorkflowStepper';
import { cn } from '@/lib/utils';

interface OverviewPageProps {
  params: Promise<{ id: string }>;
}

interface FrameworkInfo {
  id: string;
  name: string;
  framework_type: string;
}

const FRAMEWORK_TYPE_COLORS: Record<string, string> = {
  nist_csf:  'bg-blue-50 text-blue-700 border-blue-200 hover:border-blue-300',
  iso_27001: 'bg-emerald-50 text-emerald-700 border-emerald-200 hover:border-emerald-300',
  soc2_tsc:  'bg-violet-50 text-violet-700 border-violet-200 hover:border-violet-300',
  custom:    'bg-amber-50 text-amber-700 border-amber-200 hover:border-amber-300',
};

export default function AssessmentOverviewPage({ params }: OverviewPageProps) {
  const { id } = use(params);
  const userId = useUserId();
  const [frameworksInScope, setFrameworksInScope] = useState<FrameworkInfo[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!userId) return;
    const fetchData = async () => {
      try {
        const [scope, allFrameworks] = await Promise.all([
          getAssessmentScope(id).catch(() => []),
          listFrameworks().catch(() => []),
        ]);
        const ids = new Set(scope.map((s) => s.framework_id));
        setFrameworksInScope(
          allFrameworks
            .filter((f) => ids.has(f.id))
            .map((f) => ({ id: f.id, name: f.name, framework_type: f.framework_type }))
        );
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [id, userId]);

  if (loading) {
    return (
      <div className="flex justify-center py-16">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fadeIn">

      {/* Frameworks in scope */}
      {frameworksInScope.length > 0 && (
        <div className="flex flex-wrap items-center gap-2">
          <span className="flex items-center gap-1.5 text-xs font-medium text-neutral-400">
            <Layers className="h-3.5 w-3.5" />
            In scope:
          </span>
          {frameworksInScope.map((f) => (
            <Link
              key={f.id}
              href={`/frameworks/${f.id}`}
              className={cn(
                'inline-flex items-center px-2.5 py-1 rounded-md border text-xs font-medium transition-all hover:shadow-sm',
                FRAMEWORK_TYPE_COLORS[f.framework_type] ?? FRAMEWORK_TYPE_COLORS.custom
              )}
            >
              {f.name}
            </Link>
          ))}
        </div>
      )}

      {/* Workflow pipeline */}
      {userId && <WorkflowStepper assessmentId={id} userId={userId} />}
    </div>
  );
}
