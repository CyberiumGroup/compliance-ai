'use client';

import { useEffect, useRef } from 'react';
import { Loader2 } from 'lucide-react';
import { ScoringJob } from '@/lib/types';
import { getScoringJob } from '@/lib/api/scores';

interface ScoringProgressProps {
  assessmentId: string;
  job: ScoringJob;
  onJobUpdate: (job: ScoringJob) => void;
  /** Actual count of scored requirements derived from the scores list */
  scoredCount?: number;
  /** Total in-scope requirements derived from the scores list */
  totalCount?: number;
}

export function ScoringProgress({ assessmentId, job, onJobUpdate, scoredCount, totalCount }: ScoringProgressProps) {
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Hooks must be unconditional — polling only fires when active
  useEffect(() => {
    if (job.status === 'running' || job.status === 'pending') {
      pollingRef.current = setInterval(async () => {
        try {
          const updated = await getScoringJob(assessmentId);
          if (updated) {
            onJobUpdate(updated);
            if (updated.status === 'completed' || updated.status === 'failed') {
              if (pollingRef.current) clearInterval(pollingRef.current);
            }
          }
        } catch {
          // ignore poll errors
        }
      }, 3000);
    }

    return () => {
      if (pollingRef.current) clearInterval(pollingRef.current);
    };
  }, [job.status, assessmentId, onJobUpdate]);

  const isRunning = job.status === 'pending' || job.status === 'running';

  // Only visible while a full scoring job is in progress
  if (!isRunning) return null;

  const completed = (scoredCount !== undefined && (totalCount ?? 0) > 0) ? scoredCount : job.completed_requirements;
  const total = (totalCount !== undefined && totalCount > 0) ? totalCount : job.total_requirements;
  const pct = total > 0 ? Math.round((completed / total) * 100) : 0;

  return (
    <div className="space-y-2 mt-3">
      <div className="flex items-center gap-2">
        <Loader2 className="h-4 w-4 animate-spin text-primary-500 flex-shrink-0" />
        <span className="text-sm font-medium text-primary-700">
          {job.status === 'pending' ? 'Queued…' : `Scoring… ${completed} / ${total}`}
        </span>
        {job.failed_requirements > 0 && (
          <span className="text-xs text-red-600 bg-red-50 px-2 py-0.5 rounded-full">
            {job.failed_requirements} failed
          </span>
        )}
      </div>

      {total > 0 && (
        <div className="space-y-1">
          <div className="h-1.5 rounded-full bg-neutral-100 overflow-hidden">
            <div
              className="h-full rounded-full bg-primary-500 transition-all duration-500"
              style={{ width: `${pct}%` }}
            />
          </div>
          <div className="flex justify-between text-xs text-neutral-400">
            <span>{pct}% complete</span>
            {job.started_at && (
              <span>Started {new Date(job.started_at).toLocaleTimeString()}</span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
