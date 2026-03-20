'use client';

import { useState, useEffect, use } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import Link from 'next/link';
import { AssessmentTabs } from '@/components/layout';
import { StepNav } from '@/components/assessment/StepNav';
import { LoadingPage, ErrorMessage } from '@/components/ui';
import { getAssessment } from '@/lib/api';
import { useUserId } from '@/lib/hooks/useUserId';
import { Assessment } from '@/lib/types';
import { ChevronLeft, Pencil } from 'lucide-react';

interface AssessmentLayoutProps {
  children: React.ReactNode;
  params: Promise<{ id: string }>;
}

export default function AssessmentLayout({ children, params }: AssessmentLayoutProps) {
  const { id } = use(params);
  const userId = useUserId();
  const router = useRouter();
  const pathname = usePathname();
  const [assessment, setAssessment] = useState<Assessment | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const isOverview = pathname === `/assessments/${id}`;

  useEffect(() => {
    if (!userId) return;
    getAssessment(id, userId)
      .then(setAssessment)
      .catch((err) => setError(err instanceof Error ? err.message : 'Failed to load assessment'))
      .finally(() => setLoading(false));
  }, [id, userId]);

  if (!userId || loading) return <LoadingPage message="Loading assessment…" />;

  if (error) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <ErrorMessage message={error} onRetry={() => router.refresh()} />
      </div>
    );
  }

  if (!assessment) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <ErrorMessage message="Assessment not found" />
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">

      {/* ── Header ───────────────────────────────────────────────── */}
      <div className="mb-6">
        {!isOverview && (
          <Link
            href={`/assessments/${id}`}
            className="inline-flex items-center gap-1 text-xs text-neutral-400 hover:text-neutral-600 transition-colors mb-3"
          >
            <ChevronLeft className="h-3.5 w-3.5" />
            Overview
          </Link>
        )}

        {/* Title row + inline tabs on non-overview pages */}
        <div className="flex flex-wrap items-center gap-x-6 gap-y-3">
          {/* Title block */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold text-neutral-900 leading-tight truncate">
                {assessment.name}
              </h1>
              {isOverview && (
                <Link
                  href={`/assessments/${id}/edit`}
                  className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md border border-neutral-200 text-xs font-medium text-neutral-500 hover:border-neutral-300 hover:bg-neutral-50 transition-all flex-shrink-0"
                >
                  <Pencil className="h-3 w-3" />
                  Edit
                </Link>
              )}
            </div>
            <p className="mt-1 text-sm text-neutral-400">{assessment.organization_name}</p>
            {assessment.description && (
              <p className="mt-1.5 text-sm text-neutral-500 leading-relaxed max-w-2xl">
                {assessment.description}
              </p>
            )}
          </div>

          {/* Tabs — inline on large screens, wraps below on small */}
          {!isOverview && (
            <AssessmentTabs assessmentId={id} className="self-end pb-1" />
          )}
        </div>

        <div className="mt-4 border-b border-neutral-200" />
      </div>

      {isOverview ? (
        <div className="mt-0">{children}</div>
      ) : (
        <div className="mt-6 pb-28">
          {children}
          <StepNav assessmentId={id} />
        </div>
      )}
    </div>
  );
}
