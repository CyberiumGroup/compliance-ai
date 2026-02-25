'use client';

import { useState, useMemo } from 'react';
import Link from 'next/link';
import { CheckCircle, FileText, MessageSquare, Filter } from 'lucide-react';
import { GapListResponse } from '@/lib/types';
import { Card, CardContent } from '@/components/ui';
import { Button } from '@/components/ui/Button';
import { cn } from '@/lib/utils';

interface GapsListProps {
  gapData: GapListResponse;
  assessmentId?: string;
}

export function GapsList({ gapData, assessmentId }: GapsListProps) {
  const [frameworkFilter, setFrameworkFilter] = useState<string>('all');

  // Extract unique framework names for filter options
  const frameworks = useMemo(() => {
    const names = new Set<string>();
    for (const gap of gapData.gaps) {
      if (gap.framework_name) names.add(gap.framework_name);
    }
    return Array.from(names).sort();
  }, [gapData.gaps]);

  // Filter and sort gaps
  const filteredGaps = useMemo(() => {
    let gaps = gapData.gaps;

    if (frameworkFilter !== 'all') {
      gaps = gaps.filter((g) => g.framework_name === frameworkFilter);
    }

    // Sort by framework, then parent code, then requirement code
    return [...gaps].sort((a, b) => {
      const fw = (a.framework_name || '').localeCompare(b.framework_name || '');
      if (fw !== 0) return fw;
      const parent = (a.parent_code || '').localeCompare(b.parent_code || '');
      if (parent !== 0) return parent;
      return (a.requirement_code || '').localeCompare(b.requirement_code || '');
    });
  }, [gapData.gaps, frameworkFilter]);

  if (gapData.gaps.length === 0) {
    return (
      <div className="text-center py-12">
        <div className="w-20 h-20 mx-auto mb-6 rounded-full bg-gradient-to-br from-accent-100 to-accent-200 flex items-center justify-center animate-scaleIn">
          <CheckCircle className="h-10 w-10 text-accent-600" />
        </div>
        <h3 className="text-xl font-semibold gradient-text mb-2">Full Coverage Achieved!</h3>
        <p className="text-sm text-neutral-500 max-w-md mx-auto">
          All requirements have approved policy mappings.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Summary Stats */}
      <div className="grid grid-cols-3 gap-4 p-5 bg-gradient-to-br from-slate-50 to-slate-100 rounded-xl border border-neutral-200">
        <div className="text-center">
          <p className="text-sm text-neutral-500">Total Requirements</p>
          <p className="text-3xl font-bold text-neutral-700">{gapData.total_requirements}</p>
        </div>
        <div className="text-center">
          <p className="text-sm text-neutral-500">Coverage Gaps</p>
          <p className="text-3xl font-bold gradient-text">{gapData.total_gaps}</p>
        </div>
        <div className="text-center">
          <p className="text-sm text-neutral-500">No Coverage</p>
          <p className="text-3xl font-bold text-red-600">
            {gapData.unmapped_requirements}
          </p>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="flex items-center gap-4">
        <div className="flex-1 bg-neutral-200 rounded-full h-3 overflow-hidden">
          <div
            className="h-full rounded-full bg-gradient-to-r from-accent-400 to-accent-600 progress-shimmer transition-all duration-500"
            style={{ width: `${gapData.coverage_percentage}%` }}
          />
        </div>
        <span className="text-sm font-semibold text-neutral-700 min-w-[80px] text-right">
          {gapData.coverage_percentage.toFixed(1)}% coverage
        </span>
      </div>

      {/* Framework Filter */}
      {frameworks.length > 1 && (
        <div className="flex items-center gap-2">
          <Filter className="h-4 w-4 text-neutral-400" />
          <span className="text-sm font-medium text-neutral-500">Framework:</span>
          <div className="flex gap-1.5">
            <button
              onClick={() => setFrameworkFilter('all')}
              className={cn(
                'px-2.5 py-1 rounded-lg text-xs font-medium transition-all',
                frameworkFilter === 'all'
                  ? 'bg-neutral-200 text-neutral-700 ring-1 ring-neutral-300'
                  : 'text-neutral-500 hover:bg-neutral-100'
              )}
            >
              All
            </button>
            {frameworks.map((fw) => (
              <button
                key={fw}
                onClick={() => setFrameworkFilter(fw)}
                className={cn(
                  'px-2.5 py-1 rounded-lg text-xs font-medium transition-all',
                  frameworkFilter === fw
                    ? 'bg-slate-200 text-slate-700 ring-1 ring-slate-300'
                    : 'text-neutral-500 hover:bg-neutral-100'
                )}
              >
                {fw}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Gap Cards */}
      {filteredGaps.length === 0 ? (
        <div className="text-center py-8 text-neutral-500">
          No gaps match the selected filters.
        </div>
      ) : (
        <div className="grid gap-3">
          <p className="text-xs text-neutral-400">
            Showing {filteredGaps.length} of {gapData.total_gaps} gaps
          </p>
          {filteredGaps.map((gap, index) => (
            <Card
              key={gap.requirement_id}
              hover
              className="animate-slideInUp opacity-0"
              style={{
                animationDelay: `${index * 50}ms`,
                animationFillMode: 'forwards'
              }}
            >
              <CardContent>
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-semibold text-neutral-900">
                        {gap.parent_code && (
                          <span className="text-neutral-400">{gap.parent_code} &rsaquo; </span>
                        )}
                        {gap.requirement_code}
                      </span>
                      <span className="px-2.5 py-0.5 text-xs font-semibold rounded-full border bg-gradient-to-r from-red-50 to-red-100 text-red-700 border-red-200">
                        No Coverage
                      </span>
                      {gap.framework_name && (
                        <span className="text-xs px-1.5 py-0.5 rounded bg-slate-200 text-slate-600 font-medium">
                          {gap.framework_name}
                        </span>
                      )}
                    </div>
                    {gap.requirement_name && (
                      <p className="mt-1 text-sm font-medium text-neutral-700">{gap.requirement_name}</p>
                    )}
                    {gap.requirement_description && (
                      <p className="mt-1 text-sm text-neutral-600">{gap.requirement_description}</p>
                    )}
                  </div>
                </div>

                {/* Action Buttons */}
                {assessmentId && (
                  <div className="mt-3 pt-3 border-t border-neutral-100 flex flex-wrap gap-2">
                    <Link href={`/assessments/${assessmentId}/policies`}>
                      <Button variant="ghost" size="sm">
                        <FileText className="w-3.5 h-3.5 mr-1" />
                        Upload Policy
                      </Button>
                    </Link>
                    <Link href={`/assessments/${assessmentId}/interviews`}>
                      <Button variant="ghost" size="sm">
                        <MessageSquare className="w-3.5 h-3.5 mr-1" />
                        Add Interview
                      </Button>
                    </Link>
                  </div>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
