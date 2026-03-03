'use client';

import { ChevronDown, ChevronUp, FileText } from 'lucide-react';
import { useState } from 'react';
import { ScoreExplanation } from '@/lib/types';
import { cn } from '@/lib/utils';

interface ScorePanelProps {
  title: string;
  subtitle: string;
  score: number | null;
  explanation: ScoreExplanation | null;
  nullReason?: string; // shown instead of score if score is null
}

function ScoreRing({ score }: { score: number }) {
  const radius = 28;
  const circumference = 2 * Math.PI * radius;
  const filled = (score / 100) * circumference;
  const color =
    score >= 75 ? '#22c55e' :
    score >= 50 ? '#f59e0b' :
    score >= 25 ? '#f97316' : '#ef4444';

  return (
    <svg width="72" height="72" className="flex-shrink-0">
      <circle cx="36" cy="36" r={radius} fill="none" stroke="#e5e7eb" strokeWidth="6" />
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
      <text
        x="36"
        y="36"
        dominantBaseline="middle"
        textAnchor="middle"
        fontSize="13"
        fontWeight="700"
        fill={color}
      >
        {Math.round(score)}%
      </text>
    </svg>
  );
}

export function ScorePanel({ title, subtitle, score, explanation, nullReason }: ScorePanelProps) {
  const [expanded, setExpanded] = useState(false);

  const supportingDocs = explanation?.supporting_documents ?? [];
  const deficiencies = explanation?.deficiencies ?? explanation?.gap_analysis ?? explanation?.peer_analysis ?? [];
  const improvements = explanation?.improvements ?? explanation?.recommendations ?? explanation?.guidance ?? [];
  const hasDetails = supportingDocs.length > 0 || deficiencies.length > 0 || improvements.length > 0;

  return (
    <div className="rounded-xl border border-neutral-200 bg-white overflow-hidden">
      <div className="flex items-center gap-4 p-4">
        {score !== null ? (
          <ScoreRing score={score} />
        ) : (
          <div className="w-[72px] h-[72px] flex-shrink-0 flex items-center justify-center rounded-full bg-neutral-50 border-2 border-dashed border-neutral-200">
            <span className="text-xs text-neutral-400 text-center leading-tight px-1">N/A</span>
          </div>
        )}

        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold text-neutral-900">{title}</p>
          <p className="text-xs text-neutral-500 mt-0.5">{subtitle}</p>
          {score === null && nullReason && (
            <p className="text-xs text-neutral-400 mt-1 italic">{nullReason}</p>
          )}
          {explanation?.executive_summary && (
            <p className="text-xs text-neutral-600 mt-2 leading-relaxed">
              {explanation.executive_summary}
            </p>
          )}
        </div>

        {hasDetails && explanation && (
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

      {expanded && explanation && (
        <div className="border-t border-neutral-100 px-4 pb-4 pt-3 space-y-3">
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
      )}
    </div>
  );
}
