'use client';

import { useEffect, useRef } from 'react';
import { CheckCircle2, XCircle, Loader2, Clock } from 'lucide-react';
import { ScoringJob } from '@/lib/types';
import { getScoringJob } from '@/lib/api/scores';
import { cn } from '@/lib/utils';

interface ScoringProgressProps {
  assessmentId: string;
  job: ScoringJob;
  onJobUpdate: (job: ScoringJob) => void;
}

export function ScoringProgress({ assessmentId, job, onJobUpdate }: ScoringProgressProps) {
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);

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

  const pct = job.total_requirements > 0
    ? Math.round((job.completed_requirements / job.total_requirements) * 100)
    : 0;

  const isRunning = job.status === 'pending' || job.status === 'running';
  const isCompleted = job.status === 'completed';
  const isFailed = job.status === 'failed';

  return (
    <div className="space-y-3">
      {/* Status badge + label */}
      <div className="flex items-center gap-2">
        {isRunning && (
          <Loader2 className="h-4 w-4 animate-spin text-primary-500" />
        )}
        {isCompleted && <CheckCircle2 className="h-4 w-4 text-green-500" />}
        {isFailed && <XCircle className="h-4 w-4 text-red-500" />}
        {job.status === 'pending' && !isRunning && <Clock className="h-4 w-4 text-neutral-400" />}

        <span className={cn(
          'text-sm font-medium',
          isCompleted && 'text-green-700',
          isFailed && 'text-red-700',
          isRunning && 'text-primary-700',
        )}>
          {job.status === 'pending' && 'Queued…'}
          {job.status === 'running' && `Scoring… ${job.completed_requirements} / ${job.total_requirements}`}
          {job.status === 'completed' && `Completed — ${job.completed_requirements} requirements scored`}
          {job.status === 'failed' && `Failed: ${job.error_message || 'unknown error'}`}
        </span>

        {job.failed_requirements > 0 && (
          <span className="text-xs text-red-600 bg-red-50 px-2 py-0.5 rounded-full">
            {job.failed_requirements} failed
          </span>
        )}
      </div>

      {/* Progress bar */}
      {(isRunning || isCompleted) && job.total_requirements > 0 && (
        <div className="space-y-1">
          <div className="h-2 rounded-full bg-neutral-100 overflow-hidden">
            <div
              className={cn(
                'h-full rounded-full transition-all duration-500',
                isCompleted ? 'bg-green-500' : 'bg-primary-500'
              )}
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
