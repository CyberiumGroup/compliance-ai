'use client';

import { useState } from 'react';
import { RefreshCw, Play } from 'lucide-react';
import { RequirementScore } from '@/lib/types';
import { DocumentationScorePanel } from './DocumentationScorePanel';
import { ScorePanel } from './ScorePanel';
import { PhaseOutputDrawer } from './PhaseOutputDrawer';
import { PolicyExtractionPanel, usePolicyExtraction } from './PolicyExtractionPanel';
import { cn } from '@/lib/utils';

interface RequirementScoreDetailProps {
  score: RequirementScore;
  assessmentId: string;
  onRerun: (requirementId: string) => Promise<void>;
  depthLevel?: string;
}

export function RequirementScoreDetail({ score, assessmentId, onRerun, depthLevel = 'design' }: RequirementScoreDetailProps) {
  const [rerunning, setRerunning] = useState(false);

  const {
    statements,
    loading: extractionLoading,
    extracting,
    hasExtracted,
    error: extractionError,
    handleExtract,
    handleDelete,
  } = usePolicyExtraction(assessmentId, score.requirement_id);

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
  const skipReason = score.skip_reason;

  return (
    <div className="space-y-6">
      {/* Requirement header */}
      <div className="min-w-0">
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

      {/* ── Policy Extraction section ────────────────────────────────── */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <p className="text-[11px] font-semibold text-neutral-400 uppercase tracking-wider">
            Policy Extraction
          </p>
          <button
            onClick={handleExtract}
            disabled={extracting || extractionLoading}
            className="flex items-center gap-1.5 text-xs text-neutral-500 hover:text-neutral-800 transition-colors px-3 py-1.5 rounded-lg border border-neutral-200 hover:border-neutral-300 bg-white disabled:opacity-50"
          >
            {extracting ? (
              <RefreshCw className="h-3.5 w-3.5 animate-spin" />
            ) : hasExtracted ? (
              <RefreshCw className="h-3.5 w-3.5" />
            ) : (
              <Play className="h-3.5 w-3.5" />
            )}
            {extracting ? 'Extracting…' : hasExtracted ? 'Re-run extraction' : 'Run extraction'}
          </button>
        </div>
        <PolicyExtractionPanel
          statements={statements}
          loading={extractionLoading}
          extracting={extracting}
          hasExtracted={hasExtracted}
          error={extractionError}
          onDelete={handleDelete}
        />
      </div>

      {/* ── Scoring section ──────────────────────────────────────────── */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <p className="text-[11px] font-semibold text-neutral-400 uppercase tracking-wider">
            Scoring
          </p>
          <button
            onClick={handleRerun}
            disabled={rerunning}
            className="flex items-center gap-1.5 text-xs text-neutral-500 hover:text-neutral-800 transition-colors px-3 py-1.5 rounded-lg border border-neutral-200 hover:border-neutral-300 bg-white disabled:opacity-50"
          >
            <RefreshCw className={cn('h-3.5 w-3.5', rerunning && 'animate-spin')} />
            Re-run scoring
          </button>
        </div>

        {isNotScored && (
          <div className="rounded-lg bg-neutral-50 border border-neutral-200 px-4 py-3">
            <p className="text-sm font-medium text-neutral-600">Not yet scored</p>
            <p className="text-xs text-neutral-400 mt-0.5">
              Click Re-run scoring, or include this requirement in a full scoring run.
            </p>
          </div>
        )}

        {isSkipped && (
          <div className="rounded-lg bg-red-50 border border-red-200 px-4 py-3">
            <p className="text-sm font-medium text-red-700">
              {skipReason === 'no_policy_documents'
                ? 'No policy documentation'
                : skipReason === 'no_documentation'
                ? 'No documentation'
                : skipReason === 'no_policy_statements'
                ? 'No policy statements extracted'
                : 'Missing documentation'}
            </p>
            <p className="text-xs text-red-500 mt-0.5">
              {skipReason === 'no_documentation'
                ? 'No qualifying policy or evidence documents found. Upload and map documents to enable scoring.'
                : skipReason === 'no_policy_statements'
                ? 'No policy statements have been extracted for this requirement. Run extraction above first.'
                : 'No qualifying policy mappings found. Upload and map relevant policies to enable scoring.'}
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

        {isCompleted && (
          <div className="space-y-3">
            <DocumentationScorePanel
              score={score.score1}
              explanation={score.score1_explanation}
              depthLevel={depthLevel}
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
              phase2Output={score.phase2_output}
              phase4Output={score.phase4_output}
              phase5Output={score.phase5_output}
            />
          </div>
        )}
      </div>
    </div>
  );
}
