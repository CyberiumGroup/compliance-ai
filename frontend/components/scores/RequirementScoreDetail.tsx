'use client';

import { useState } from 'react';
import { RefreshCw } from 'lucide-react';
import { RequirementScore } from '@/lib/types';
import { ScorePanel } from './ScorePanel';
import { PhaseOutputDrawer } from './PhaseOutputDrawer';
import { cn } from '@/lib/utils';

interface RequirementScoreDetailProps {
  score: RequirementScore;
  onRerun: (requirementId: string) => Promise<void>;
}

export function RequirementScoreDetail({ score, onRerun }: RequirementScoreDetailProps) {
  const [rerunning, setRerunning] = useState(false);

  const handleRerun = async () => {
    setRerunning(true);
    try {
      await onRerun(score.requirement_id);
    } finally {
      setRerunning(false);
    }
  };

  const isNotScored = score.status === 'not_scored';
  const isSkipped = score.status === 'skipped';
  const isCompleted = score.status === 'completed';
  const isFailed = score.status === 'failed';

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          <span className="font-mono text-xs font-semibold text-primary-700 bg-primary-50 border border-primary-200 px-2 py-0.5 rounded">
            {score.requirement_code ?? '—'}
          </span>
          <h2 className="text-base font-semibold text-neutral-900 mt-2 leading-snug">
            {score.requirement_name}
          </h2>
          {score.requirement_description && (
            <p className="text-sm text-neutral-500 mt-1.5 leading-relaxed">
              {score.requirement_description}
            </p>
          )}
        </div>

        <button
          onClick={handleRerun}
          disabled={rerunning}
          className="flex items-center gap-1.5 text-xs text-neutral-500 hover:text-neutral-800 transition-colors flex-shrink-0 px-3 py-1.5 rounded-lg border border-neutral-200 hover:border-neutral-300 bg-white disabled:opacity-50"
        >
          <RefreshCw className={cn('h-3.5 w-3.5', rerunning && 'animate-spin')} />
          Re-run
        </button>
      </div>

      {/* Status banners */}
      {isNotScored && (
        <div className="rounded-lg bg-neutral-50 border border-neutral-200 px-4 py-3">
          <p className="text-sm font-medium text-neutral-600">Not yet scored</p>
          <p className="text-xs text-neutral-400 mt-0.5">
            Select this requirement and click Re-run, or include it in a full scoring run.
          </p>
        </div>
      )}

      {isSkipped && (
        <div className="rounded-lg bg-red-50 border border-red-200 px-4 py-3">
          <p className="text-sm font-medium text-red-700">Missing documentation</p>
          <p className="text-xs text-red-500 mt-0.5">
            No qualifying policy mappings found for this requirement. Upload and map relevant
            policies to enable scoring.
          </p>
        </div>
      )}

      {isFailed && (
        <div className="rounded-lg bg-red-50 border border-red-200 px-4 py-3">
          <p className="text-sm font-medium text-red-700">Scoring failed</p>
          {score.error_message && (
            <p className="text-xs text-red-500 mt-0.5">{score.error_message}</p>
          )}
        </div>
      )}

      {/* Score panels */}
      {isCompleted && (
        <div className="space-y-3">
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

          <PhaseOutputDrawer
            phase1Output={score.phase1_output}
            phase2Output={score.phase2_output}
            phase4Output={score.phase4_output}
            phase5Output={score.phase5_output}
          />
        </div>
      )}
    </div>
  );
}
