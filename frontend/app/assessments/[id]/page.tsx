'use client';

import { useState, useEffect, use } from 'react';
import Link from 'next/link';
import { Layers, Clock, FileText } from 'lucide-react';
import { LoadingSpinner } from '@/components/ui';
import {
  getAssessment,
  getAssessmentScope,
  listFrameworks,
  listPolicies,
} from '@/lib/api';
import { useUserId } from '@/lib/hooks/useUserId';
import { WorkflowStepper } from '@/components/assessment/WorkflowStepper';
import { cn } from '@/lib/utils';
import { Policy, EvidenceSection, AssessmentDepth } from '@/lib/types';

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

const SECTION_LABELS: Record<EvidenceSection, string> = {
  policy:    'Policy',
  process:   'Process',
  control:   'Control',
  interview: 'Interview',
  proof:     'Proof',
};

const DEPTH_LABELS: Record<AssessmentDepth, string> = {
  design:                 'Design',
  implementation:         'Implementation',
  operating_effectiveness: 'Operating Effectiveness',
};

const SECTION_COLORS: Record<EvidenceSection, string> = {
  policy:    'bg-blue-100 text-blue-700',
  process:   'bg-violet-100 text-violet-700',
  control:   'bg-teal-100 text-teal-700',
  interview: 'bg-amber-100 text-amber-700',
  proof:     'bg-neutral-100 text-neutral-600',
};


function relativeTime(isoString: string): string {
  const now = Date.now();
  const then = new Date(isoString).getTime();
  const diffMs = now - then;
  const diffMins = Math.floor(diffMs / 60_000);
  if (diffMins < 1) return 'just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  const diffHours = Math.floor(diffMins / 60);
  if (diffHours < 24) return `${diffHours}h ago`;
  const diffDays = Math.floor(diffHours / 24);
  if (diffDays < 7) return `${diffDays}d ago`;
  return new Date(isoString).toLocaleDateString('en-GB', { day: 'numeric', month: 'short' });
}

export default function AssessmentOverviewPage({ params }: OverviewPageProps) {
  const { id } = use(params);
  const userId = useUserId();
  const [frameworksInScope, setFrameworksInScope] = useState<FrameworkInfo[]>([]);
  const [policies, setPolicies] = useState<Policy[]>([]);
  const [depthLevel, setDepthLevel] = useState<AssessmentDepth | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!userId) return;
    const fetchData = async () => {
      try {
        const [assessment, scope, allFrameworks, docs] = await Promise.all([
          getAssessment(id, userId).catch(() => null),
          getAssessmentScope(id).catch(() => []),
          listFrameworks().catch(() => []),
          listPolicies(id, userId).catch(() => []),
        ]);
        const ids = new Set(scope.map((s) => s.framework_id));
        setFrameworksInScope(
          allFrameworks
            .filter((f) => ids.has(f.id))
            .map((f) => ({ id: f.id, name: f.name, framework_type: f.framework_type }))
        );
        setPolicies(docs);
        if (assessment) setDepthLevel(assessment.depth_level);
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

  // Recent evidence: last 5 uploads sorted newest first
  const recentDocs = [...policies]
    .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
    .slice(0, 5);


  return (
    <div className="space-y-6 animate-fadeIn">

      {/* Workflow pipeline */}
      {userId && <WorkflowStepper assessmentId={id} userId={userId} />}

      {/* Dashboard grid */}
      <div className="grid grid-cols-3 gap-4">

        {/* Recent Evidence — 2/3 width */}
        <div className="col-span-2 rounded-lg border border-neutral-200 bg-white overflow-hidden">
          <div className="flex items-center justify-between px-5 py-3.5 border-b border-neutral-100">
            <div className="flex items-center gap-2">
              <Clock className="h-3.5 w-3.5 text-neutral-400" />
              <span className="text-sm font-semibold text-neutral-800">Recent Evidence Uploads</span>
            </div>
            <Link
              href={`/assessments/${id}/evidence`}
              className="text-xs text-primary-600 hover:text-primary-700 font-medium"
            >
              View all →
            </Link>
          </div>

          {recentDocs.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-10 text-center">
              <FileText className="h-7 w-7 text-neutral-200 mb-2" />
              <p className="text-sm text-neutral-400">No evidence uploaded yet</p>
              <Link
                href={`/assessments/${id}/evidence`}
                className="mt-2 text-xs text-primary-600 hover:text-primary-700 font-medium"
              >
                Upload evidence →
              </Link>
            </div>
          ) : (
            <ul className="divide-y divide-neutral-50">
              {recentDocs.map((doc) => (
                <li key={doc.id} className="flex items-center gap-3 px-5 py-3">
                  {doc.section ? (
                    <span className={cn(
                      'inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-semibold uppercase tracking-wide flex-shrink-0',
                      SECTION_COLORS[doc.section]
                    )}>
                      {SECTION_LABELS[doc.section]}
                    </span>
                  ) : (
                    <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-semibold uppercase tracking-wide flex-shrink-0 bg-neutral-100 text-neutral-500">
                      —
                    </span>
                  )}
                  <span className="flex-1 min-w-0 text-sm text-neutral-800 truncate">{doc.name}</span>
                  <span className="text-xs text-neutral-400 flex-shrink-0">{relativeTime(doc.created_at)}</span>
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* Right column */}
        <div className="col-span-1 flex flex-col gap-4">

          {/* Assessment Depth */}
          {depthLevel && (
            <div className="rounded-lg border border-neutral-200 bg-white px-4 py-3.5 flex items-center justify-between">
              <span className="text-xs font-medium text-neutral-500">Assessment depth</span>
              <span className="text-xs font-semibold text-neutral-800">{DEPTH_LABELS[depthLevel]}</span>
            </div>
          )}

          {/* Frameworks in Scope */}
          {frameworksInScope.length > 0 && (
            <div className="rounded-lg border border-neutral-200 bg-white overflow-hidden">
              <div className="flex items-center gap-2 px-4 py-3.5 border-b border-neutral-100">
                <Layers className="h-3.5 w-3.5 text-neutral-400" />
                <span className="text-sm font-semibold text-neutral-800">Frameworks in Scope</span>
              </div>
              <div className="px-4 py-3 flex flex-wrap gap-1.5">
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
            </div>
          )}

        </div>
      </div>

    </div>
  );
}
