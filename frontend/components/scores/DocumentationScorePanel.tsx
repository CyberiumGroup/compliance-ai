'use client';

import { useState } from 'react';
import { ChevronDown, ChevronUp, CheckCircle2, FileText, AlertCircle } from 'lucide-react';
import { DocumentationScoreExplanation } from '@/lib/types';
import { cn } from '@/lib/utils';

// ─── Coverage ring (no percentage text — shows label inside) ──────────────────

function CoverageRing({ label }: { label: 'Covered' | 'Partial' | 'Gap' | null }) {
  const score = label === 'Covered' ? 100 : label === 'Partial' ? 50 : label === 'Gap' ? 0 : null;
  const radius = 28;
  const circumference = 2 * Math.PI * radius;

  if (score === null) {
    return (
      <div className="w-[72px] h-[72px] flex-shrink-0 flex items-center justify-center rounded-full bg-neutral-50 border-2 border-dashed border-neutral-200">
        <span className="text-xs text-neutral-400 text-center leading-tight px-1">N/A</span>
      </div>
    );
  }

  const filled = (score / 100) * circumference;
  const color = score === 100 ? '#22c55e' : score === 50 ? '#f59e0b' : '#ef4444';
  const trackColor = score === 0 ? '#fecaca' : '#e5e7eb';
  const labelColor = score === 100 ? '#16a34a' : score === 50 ? '#d97706' : '#dc2626';

  return (
    <div className="relative w-[72px] h-[72px] flex-shrink-0">
      <svg width="72" height="72" className="absolute inset-0">
        <circle cx="36" cy="36" r={radius} fill="none" stroke={trackColor} strokeWidth="6" />
        {score > 0 && (
          <circle
            cx="36"
            cy="36"
            r={radius}
            fill="none"
            stroke={color}
            strokeWidth="6"
            strokeDasharray={`${filled} ${circumference - filled}`}
            strokeLinecap="round"
            transform="rotate(-90 36 36)"
          />
        )}
      </svg>
      <div className="absolute inset-0 flex items-center justify-center">
        <span className="text-[10px] font-bold leading-tight text-center px-0.5" style={{ color: labelColor }}>
          {label}
        </span>
      </div>
    </div>
  );
}

// ─── DocumentationScorePanel ──────────────────────────────────────────────────

interface DocumentationScorePanelProps {
  score: number | null;
  explanation: DocumentationScoreExplanation | null;
  depthLevel?: string;
}

export function DocumentationScorePanel({ score, explanation, depthLevel = 'design' }: DocumentationScorePanelProps) {
  const [expanded, setExpanded] = useState(false);

  const label = explanation?.coverage_label ?? null;
  const explanationText = explanation?.explanation;
  const recommendations = explanation?.recommendations ?? [];
  const statementEvals = explanation?.policy_statement_evaluations ?? [];

  const hasDetails = statementEvals.length > 0 || recommendations.length > 0;

  return (
    <div className="rounded-xl border border-neutral-200 bg-white overflow-hidden">
      {/* Header row */}
      <div className="flex items-center gap-4 p-4">
        <CoverageRing label={label} />

        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold text-neutral-900">Score 1 — Met by Documentation</p>
          <p className="text-xs text-neutral-500 mt-0.5">
            {depthLevel === 'implementation'
              ? 'Policy coverage and evidence support for each policy statement'
              : 'Policy coverage of this requirement'}
          </p>
          {explanationText && (
            <p className="text-xs text-neutral-600 mt-2 leading-relaxed">{explanationText}</p>
          )}
        </div>

        {hasDetails && (
          <button
            onClick={() => setExpanded(v => !v)}
            className="flex-shrink-0 text-neutral-400 hover:text-neutral-600 transition-colors"
          >
            {expanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
          </button>
        )}
      </div>

      {/* Expanded detail */}
      {expanded && (
        <div className="border-t border-neutral-100 px-4 pb-4 pt-3 space-y-4">
          {/* Recommendations */}
          {recommendations.length > 0 && (
            <div>
              <p className="text-xs font-semibold text-neutral-700 mb-2">Recommendations</p>
              <ul className="space-y-1.5">
                {recommendations.map((rec, i) => (
                  <li key={i} className="flex gap-2 text-xs text-neutral-600">
                    <span className={cn(
                      'flex-shrink-0 px-1.5 py-0.5 rounded text-[10px] font-semibold uppercase tracking-wide',
                      rec.type?.toLowerCase() === 'policy'
                        ? 'bg-blue-100 text-blue-700'
                        : rec.type?.toLowerCase() === 'evidence'
                        ? 'bg-purple-100 text-purple-700'
                        : 'bg-neutral-100 text-neutral-600'
                    )}>
                      {rec.type || 'Action'}
                    </span>
                    <span>{rec.action}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Per-statement evaluations */}
          {statementEvals.length > 0 && (
            <div>
              <p className="text-xs font-semibold text-neutral-700 mb-2">Policy Statements</p>
              <ul className="space-y-2">
                {statementEvals.map((eval_, i) => (
                  <li key={i} className="rounded-lg border border-neutral-200 bg-neutral-50 p-3">
                    {/* Statement text */}
                    <p className="text-xs text-neutral-800 leading-relaxed">{eval_.statement}</p>

                    {/* Source document */}
                    <p className="mt-1.5 text-xs text-neutral-400">
                      <span className="font-medium text-neutral-500">{eval_.document_title}</span>
                      {eval_.document_section && <> &middot; {eval_.document_section}</>}
                    </p>

                    {/* Evidence (implementation depth) */}
                    {depthLevel === 'implementation' && (
                      <div className="mt-2 pt-2 border-t border-neutral-200">
                        {eval_.has_evidence && eval_.supporting_evidence.length > 0 ? (
                          <ul className="space-y-1.5">
                            {eval_.supporting_evidence.map((ev, j) => (
                              <li key={j} className="flex items-start gap-1.5">
                                <CheckCircle2 className="h-3.5 w-3.5 text-green-500 flex-shrink-0 mt-0.5" />
                                <div className="min-w-0">
                                  <p className="text-xs font-medium text-neutral-600 flex items-center gap-1">
                                    <FileText className="h-3 w-3 flex-shrink-0" />
                                    {ev.document_title}
                                  </p>
                                  <p className="text-xs text-green-700 mt-0.5 leading-relaxed">{ev.explanation}</p>
                                </div>
                              </li>
                            ))}
                          </ul>
                        ) : (
                          <div className="flex items-center gap-1.5">
                            <AlertCircle className="h-3.5 w-3.5 text-red-400 flex-shrink-0" />
                            <p className="text-xs text-red-600">No supporting evidence found</p>
                          </div>
                        )}
                      </div>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
