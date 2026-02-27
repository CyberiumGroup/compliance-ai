'use client';

import { useState } from 'react';
import { ChevronDown, ChevronUp, RefreshCw, SkipForward } from 'lucide-react';
import { RequirementScore } from '@/lib/types';
import { ScorePanel } from './ScorePanel';
import { PhaseOutputDrawer } from './PhaseOutputDrawer';
import { cn } from '@/lib/utils';

interface RequirementScoreCardProps {
  score: RequirementScore;
  onRerun: (requirementId: string) => Promise<void>;
}

function ScoreBadge({ value, label }: { value: number | null; label: string }) {
  if (value === null) {
    return (
      <span className="px-2 py-0.5 text-xs rounded-full bg-neutral-100 text-neutral-400">
        {label}: N/A
      </span>
    );
  }
  const color =
    value >= 75 ? 'bg-green-100 text-green-700' :
    value >= 50 ? 'bg-amber-100 text-amber-700' :
    value >= 25 ? 'bg-orange-100 text-orange-700' :
    'bg-red-100 text-red-700';

  return (
    <span className={cn('px-2 py-0.5 text-xs rounded-full font-medium', color)}>
      {label}: {Math.round(value)}%
    </span>
  );
}

export function RequirementScoreCard({ score, onRerun }: RequirementScoreCardProps) {
  const [expanded, setExpanded] = useState(false);
  const [rerunning, setRerunning] = useState(false);

  const isSkipped = score.status === 'skipped';
  const isFailed = score.status === 'failed';
  const isCompleted = score.status === 'completed';

  const handleRerun = async (e: React.MouseEvent) => {
    e.stopPropagation();
    setRerunning(true);
    try {
      await onRerun(score.requirement_id);
    } finally {
      setRerunning(false);
    }
  };

  return (
    <div className="rounded-xl border border-neutral-200 bg-white overflow-hidden shadow-sm">
      {/* Header row — div instead of button to avoid nested-button violation */}
      <div
        className={cn(
          'w-full flex items-center gap-3 px-4 py-3 text-left transition-colors',
          isCompleted && 'cursor-pointer hover:bg-neutral-50',
        )}
        onClick={() => isCompleted && setExpanded(v => !v)}
        role={isCompleted ? 'button' : undefined}
        tabIndex={isCompleted ? 0 : undefined}
        onKeyDown={isCompleted ? (e) => e.key === 'Enter' && setExpanded(v => !v) : undefined}
      >
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-mono text-xs font-semibold text-primary-700 bg-primary-50 border border-primary-200 px-2 py-0.5 rounded">
              {score.requirement_code ?? '—'}
            </span>
            {score.requirement_name && (
              <span className="text-sm font-medium text-neutral-900 truncate">
                {score.requirement_name}
              </span>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2 flex-shrink-0">
          {isSkipped && (
            <span className="flex items-center gap-1 text-xs text-neutral-400 bg-neutral-50 px-2 py-0.5 rounded-full border border-neutral-200">
              <SkipForward className="h-3 w-3" />
              Missing documentation
            </span>
          )}
          {isFailed && (
            <span className="text-xs text-red-600 bg-red-50 px-2 py-0.5 rounded-full border border-red-200">
              Failed
            </span>
          )}
          {isCompleted && (
            <>
              <ScoreBadge value={score.score1} label="Design" />
              <ScoreBadge value={score.score2} label="Risk" />
              <ScoreBadge value={score.score3} label="Peer" />
            </>
          )}

          <button
            onClick={handleRerun}
            disabled={rerunning}
            className="p-1 text-neutral-300 hover:text-neutral-500 transition-colors rounded"
            title="Re-run scoring for this requirement"
          >
            <RefreshCw className={cn('h-3.5 w-3.5', rerunning && 'animate-spin')} />
          </button>

          {isCompleted && (
            expanded
              ? <ChevronUp className="h-4 w-4 text-neutral-400" />
              : <ChevronDown className="h-4 w-4 text-neutral-400" />
          )}
        </div>
      </div>

      {/* Expanded score panels */}
      {expanded && isCompleted && (
        <div className="border-t border-neutral-100 px-4 pb-4 pt-3 space-y-3">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <ScorePanel
              title="Score 1 — Met by Design"
              subtitle="Control documentation coverage of requirement elements"
              score={score.score1}
              explanation={score.score1_explanation}
            />
            <ScorePanel
              title="Score 2 — Risk-Based Adequacy"
              subtitle="North American best practices for your risk profile"
              score={score.score2}
              explanation={score.score2_explanation}
              nullReason="No risk profile configured for this assessment"
            />
            <ScorePanel
              title="Score 3 — Peer Alignment"
              subtitle="Alignment with industry peers matching your company profile"
              score={score.score3}
              explanation={score.score3_explanation}
              nullReason="No company profile configured for this assessment"
            />
          </div>

          <PhaseOutputDrawer
            phase1Output={score.phase1_output}
            phase2Output={score.phase2_output}
            phase4Output={score.phase4_output}
            phase5Output={score.phase5_output}
          />
        </div>
      )}

      {isFailed && score.error_message && (
        <div className="border-t border-red-100 px-4 py-2">
          <p className="text-xs text-red-600">{score.error_message}</p>
        </div>
      )}
    </div>
  );
}
