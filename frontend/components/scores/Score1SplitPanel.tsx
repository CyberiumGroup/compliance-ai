'use client';

import { useState } from 'react';
import { ChevronDown, ChevronUp, FileText, AlertTriangle } from 'lucide-react';
import { ScoreExplanation } from '@/lib/types';
import { cn } from '@/lib/utils';

// ─── Shared ScoreRing (small variant) ─────────────────────────────────────────

function ScoreRing({ score, size = 'lg' }: { score: number; size?: 'sm' | 'lg' }) {
  const dim = size === 'sm' ? 48 : 72;
  const cx = dim / 2;
  const radius = size === 'sm' ? 18 : 28;
  const strokeWidth = size === 'sm' ? 4 : 6;
  const fontSize = size === 'sm' ? '10' : '13';
  const circumference = 2 * Math.PI * radius;
  const filled = (score / 100) * circumference;
  const color =
    score >= 75 ? '#22c55e' :
    score >= 50 ? '#f59e0b' :
    score >= 25 ? '#f97316' : '#ef4444';

  return (
    <svg width={dim} height={dim} className="flex-shrink-0">
      <circle cx={cx} cy={cx} r={radius} fill="none" stroke="#e5e7eb" strokeWidth={strokeWidth} />
      <circle
        cx={cx}
        cy={cx}
        r={radius}
        fill="none"
        stroke={color}
        strokeWidth={strokeWidth}
        strokeDasharray={`${filled} ${circumference - filled}`}
        strokeLinecap="round"
        transform={`rotate(-90 ${cx} ${cx})`}
      />
      <text
        x={cx}
        y={cx}
        dominantBaseline="middle"
        textAnchor="middle"
        fontSize={fontSize}
        fontWeight="700"
        fill={color}
      >
        {Math.round(score)}%
      </text>
    </svg>
  );
}

// ─── ExplanationDetails ────────────────────────────────────────────────────────

function ExplanationDetails({ explanation, label }: { explanation: ScoreExplanation; label: string }) {
  const supportingDocs = explanation.supporting_documents ?? [];
  const deficiencies = explanation.deficiencies ?? explanation.gap_analysis ?? explanation.peer_analysis ?? [];
  const improvements = explanation.improvements ?? explanation.recommendations ?? explanation.guidance ?? [];

  const hasContent = supportingDocs.length > 0 || deficiencies.length > 0 || improvements.length > 0;
  if (!hasContent) return null;

  return (
    <div className="space-y-3 pt-3">
      <p className="text-xs font-semibold text-neutral-500 uppercase tracking-wide">{label}</p>

      {supportingDocs.length > 0 && (
        <div>
          <p className="text-xs font-semibold text-neutral-700 mb-1.5">Supporting Documents</p>
          <ul className="space-y-2">
            {supportingDocs.map((doc, i) => (
              <li key={i} className="flex gap-2.5">
                <FileText className="h-3.5 w-3.5 flex-shrink-0 text-neutral-400 mt-0.5" />
                <div className="min-w-0">
                  <p className="text-xs font-medium text-neutral-800 leading-snug">{doc.title}</p>
                  <p className="text-xs text-neutral-500 mt-0.5 leading-relaxed">{doc.relevant_details}</p>
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}

      {deficiencies.length > 0 && (
        <div>
          <p className="text-xs font-semibold text-neutral-700 mb-1.5">Deficiencies / Gaps</p>
          <ul className="space-y-1">
            {deficiencies.map((d, i) => (
              <li key={i} className="flex gap-2 text-xs text-neutral-600">
                <span className="font-mono text-neutral-400 flex-shrink-0">
                  {d.element_id ?? d.mechanism_id ?? `#${i + 1}`}
                </span>
                <span>{d.issue ?? d.gap ?? ''}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {improvements.length > 0 && (
        <div>
          <p className="text-xs font-semibold text-neutral-700 mb-1.5">Recommendations</p>
          <ul className="space-y-1">
            {improvements.map((imp, i) => (
              <li key={i} className="flex gap-2 text-xs text-neutral-600">
                <span className={cn(
                  'flex-shrink-0 px-1.5 py-0.5 rounded text-[10px] font-semibold uppercase tracking-wide',
                  imp.level?.toLowerCase() === 'immediate'
                    ? 'bg-red-100 text-red-700'
                    : imp.level?.toLowerCase() === 'short-term'
                    ? 'bg-amber-100 text-amber-700'
                    : 'bg-neutral-100 text-neutral-600'
                )}>
                  {imp.level || 'Action'}
                </span>
                <span>{imp.action}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

// ─── Sub-panel ─────────────────────────────────────────────────────────────────

interface SubPanelProps {
  label: string;
  score: number | null;
  explanation: ScoreExplanation | null;
  naReason?: string; // shown when score is null (N/A)
}

function SubPanel({ label, score, explanation, naReason }: SubPanelProps) {
  const skipReason = (explanation as any)?.skip_reason as string | undefined;
  const isZeroWithReason = score === 0 && skipReason;
  const summary = explanation?.executive_summary;

  return (
    <div className="flex-1 min-w-0 space-y-2">
      <p className="text-xs font-semibold text-neutral-600">{label}</p>

      {/* Ring + score on its own row */}
      <div className="flex items-center gap-2">
        {score !== null ? (
          <ScoreRing score={score} size="sm" />
        ) : (
          <div className="w-12 h-12 flex-shrink-0 flex items-center justify-center rounded-full bg-neutral-50 border-2 border-dashed border-neutral-200">
            <span className="text-[9px] text-neutral-400 text-center leading-tight px-0.5">N/A</span>
          </div>
        )}
        {score === null && naReason && (
          <p className="text-xs text-neutral-400 italic">{naReason}</p>
        )}
        {isZeroWithReason && (
          <div className="flex items-center gap-1.5">
            <AlertTriangle className="h-3.5 w-3.5 text-amber-500 flex-shrink-0" />
            <p className="text-xs text-amber-600">
              {skipReason === 'no_evidence_documents'
                ? 'No evidence documents mapped'
                : 'No policy documentation mapped'}
            </p>
          </div>
        )}
      </div>

      {/* Summary on its own row so it gets the full width */}
      {summary && !isZeroWithReason && (
        <p className="text-xs text-neutral-600 leading-relaxed">{summary}</p>
      )}
    </div>
  );
}

// ─── Score1SplitPanel ──────────────────────────────────────────────────────────

export interface Score1SplitPanelProps {
  scoreComposite: number | null;
  scoreDesign: number | null;
  scoreImplementation: number | null; // null = N/A (design depth)
  explanationDesign: ScoreExplanation | null;
  explanationImplementation: ScoreExplanation | null;
  depthLevel: 'design' | 'implementation' | string;
}

export function Score1SplitPanel({
  scoreComposite,
  scoreDesign,
  scoreImplementation,
  explanationDesign,
  explanationImplementation,
  depthLevel,
}: Score1SplitPanelProps) {
  const [expanded, setExpanded] = useState(false);

  const isImplementationDepth = depthLevel === 'implementation';

  // Determine whether there is expandable detail in either sub-panel
  const hasDesignDetail = !!(
    explanationDesign?.supporting_documents?.length ||
    explanationDesign?.deficiencies?.length ||
    explanationDesign?.improvements?.length
  );
  const hasImplDetail = !!(
    explanationImplementation?.supporting_documents?.length ||
    explanationImplementation?.deficiencies?.length ||
    explanationImplementation?.improvements?.length
  );
  const hasDetails = hasDesignDetail || hasImplDetail;

  return (
    <div className="rounded-xl border border-neutral-200 bg-white overflow-hidden">
      {/* Composite header row */}
      <div className="flex items-center gap-4 p-4">
        {scoreComposite !== null ? (
          <ScoreRing score={scoreComposite} size="lg" />
        ) : (
          <div className="w-[72px] h-[72px] flex-shrink-0 flex items-center justify-center rounded-full bg-neutral-50 border-2 border-dashed border-neutral-200">
            <span className="text-xs text-neutral-400 text-center leading-tight px-1">N/A</span>
          </div>
        )}

        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold text-neutral-900">Score 1 — Met by Documentation</p>
          <p className="text-xs text-neutral-500 mt-0.5">
            {isImplementationDepth
              ? 'Composite average of design and implementation sub-scores'
              : 'Policy documentation coverage of requirement elements'}
          </p>
        </div>

        {hasDetails && (
          <button
            onClick={() => setExpanded(v => !v)}
            className="flex-shrink-0 text-neutral-400 hover:text-neutral-600 transition-colors"
          >
            {expanded
              ? <ChevronUp className="h-4 w-4" />
              : <ChevronDown className="h-4 w-4" />}
          </button>
        )}
      </div>

      {/* Sub-panels (always visible) */}
      <div className="border-t border-neutral-100 px-4 py-3 flex gap-4">
        <SubPanel
          label="Design"
          score={scoreDesign}
          explanation={explanationDesign}
        />

        {/* Divider */}
        <div className="w-px bg-neutral-100 self-stretch" />

        <SubPanel
          label="Implementation"
          score={scoreImplementation}
          explanation={explanationImplementation}
          naReason={!isImplementationDepth ? 'Design depth only' : undefined}
        />
      </div>

      {/* Expanded detail */}
      {expanded && (hasDesignDetail || hasImplDetail) && (
        <div className="border-t border-neutral-100 px-4 pb-4 space-y-4">
          {hasDesignDetail && explanationDesign && (
            <ExplanationDetails explanation={explanationDesign} label="Design detail" />
          )}
          {hasImplDetail && explanationImplementation && (
            <>
              {hasDesignDetail && <div className="border-t border-dashed border-neutral-200" />}
              <ExplanationDetails explanation={explanationImplementation} label="Implementation detail" />
            </>
          )}
        </div>
      )}
    </div>
  );
}
