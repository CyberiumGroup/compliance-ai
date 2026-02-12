'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { Plus, Filter, ClipboardList } from 'lucide-react';
import { Button, PageHeader } from '@/components/ui';
import { LoadingPage, ErrorMessage, EmptyState } from '@/components/ui';
import { AssessmentCard } from '@/components/assessments';
import { listAssessments } from '@/lib/api';
import { useUserId } from '@/lib/hooks/useUserId';
import { Assessment } from '@/lib/types';
import { cn } from '@/lib/utils';

const statusFilters: Array<{ value: string; label: string }> = [
  { value: '', label: 'All' },
  { value: 'DRAFT', label: 'Draft' },
  { value: 'IN_PROGRESS', label: 'In Progress' },
  { value: 'COMPLETED', label: 'Completed' },
  { value: 'ARCHIVED', label: 'Archived' },
];

export default function AssessmentsPage() {
  const userId = useUserId();
  const [assessments, setAssessments] = useState<Assessment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState('');

  const fetchAssessments = async () => {
    if (!userId) return;

    setLoading(true);
    setError(null);

    try {
      const response = await listAssessments(
        { status: statusFilter || undefined },
        userId
      );
      setAssessments(response.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load assessments');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (userId) {
      fetchAssessments();
    }
  }, [userId, statusFilter]);

  if (!userId) {
    return <LoadingPage message="Initializing..." />;
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <PageHeader
        title="Assessments"
        description="Manage your compliance assessments"
        icon={ClipboardList}
        actions={
          <Link href="/assessments/new">
            <Button variant="gradient" leftIcon={<Plus className="h-4 w-4" />}>
              New Assessment
            </Button>
          </Link>
        }
      />

      {/* Filters */}
      <div className="mb-8">
        <div className="flex items-center gap-3 flex-wrap">
          <span className="text-sm font-medium text-neutral-500 flex items-center gap-1.5">
            <Filter className="h-4 w-4" />
            Filter:
          </span>
          <div className="flex gap-2 flex-wrap">
            {statusFilters.map((filter) => (
              <button
                key={filter.value}
                onClick={() => setStatusFilter(filter.value)}
                className={cn(
                  'px-4 py-2 rounded-full text-sm font-medium transition-all duration-200',
                  statusFilter === filter.value
                    ? 'bg-gradient-to-r from-primary-500 to-primary-600 text-white shadow-md'
                    : 'bg-neutral-100 text-neutral-600 hover:bg-neutral-200 hover:shadow-sm'
                )}
              >
                {filter.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Content */}
      {loading ? (
        <LoadingPage message="Loading assessments..." />
      ) : error ? (
        <ErrorMessage message={error} onRetry={fetchAssessments} />
      ) : assessments.length === 0 ? (
        <EmptyState
          title="No assessments found"
          description={
            statusFilter
              ? `No assessments with status "${statusFilter.toLowerCase().replace('_', ' ')}"`
              : 'Get started by creating your first assessment'
          }
          action={
            !statusFilter
              ? {
                  label: 'Create Assessment',
                  onClick: () => (window.location.href = '/assessments/new'),
                }
              : undefined
          }
        />
      ) : (
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {assessments.map((assessment, index) => (
            <div
              key={assessment.id}
              className="animate-slideInUp opacity-0"
              style={{
                animationDelay: `${index * 75}ms`,
                animationFillMode: 'forwards'
              }}
            >
              <AssessmentCard assessment={assessment} />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
