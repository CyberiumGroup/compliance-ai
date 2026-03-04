'use client';

import { useState } from 'react';
import { X, ChevronDown, ChevronUp, Lightbulb, RotateCcw, FileText, Shield } from 'lucide-react';
import { PolicyMapping } from '@/lib/types';
import { cn } from '@/lib/utils';

interface PolicyRelevanceRowProps {
  mapping: PolicyMapping;
  onReject: () => Promise<void>;
  onUnreject: () => Promise<void>;
}

function RelevanceBadge({ score }: { score: number }) {
  const color =
    score >= 80
      ? 'bg-green-100 text-green-800 ring-green-200'
      : score >= 60
        ? 'bg-amber-100 text-amber-800 ring-amber-200'
        : 'bg-red-100 text-red-800 ring-red-200';

  return (
    <span
      className={cn('inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold ring-1', color)}
      title={
        'Semantic relevance score: the maximum cosine similarity between any section of this ' +
        'policy document and the requirement text, normalized to 0–100%. ' +
        'Higher scores indicate greater content overlap.'
      }
    >
      Semantic Relevance: {Math.round(score)}%
    </span>
  );
}

export function PolicyRelevanceRow({ mapping, onReject, onUnreject }: PolicyRelevanceRowProps) {
  const [expanded, setExpanded] = useState(false);
  const [acting, setActing] = useState(false);

  const score = mapping.relevance_percentage ?? (mapping.confidence_score != null ? (mapping.confidence_score + 1) / 2 * 100 : null);
  const isRejected = mapping.is_rejected;

  const handleReject = async () => {
    setActing(true);
    try {
      await onReject();
    } finally {
      setActing(false);
    }
  };

  const handleUnreject = async () => {
    setActing(true);
    try {
      await onUnreject();
    } finally {
      setActing(false);
    }
  };

  return (
    <div className={cn(
      'rounded-lg border px-4 py-3 space-y-2 transition-colors',
      isRejected
        ? 'border-neutral-200 bg-neutral-50/60 opacity-60'
        : 'border-neutral-200 bg-white hover:border-neutral-300'
    )}>
      {/* Main row */}
      <div className="flex items-start gap-3">
        {/* Policy info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <p className={cn('text-sm font-medium truncate', isRejected ? 'text-neutral-500' : 'text-neutral-900')}>
              {mapping.policy_name ?? 'Unnamed document'}
            </p>
            {mapping.policy_document_type === 'evidence' ? (
              <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-xs font-medium bg-amber-100 text-amber-700 flex-shrink-0">
                <Shield className="h-3 w-3" />
                Evidence
              </span>
            ) : (
              <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-xs font-medium bg-purple-100 text-purple-700 flex-shrink-0">
                <FileText className="h-3 w-3" />
                Policy
              </span>
            )}
          </div>
          {mapping.policy_description && (
            <p className="text-xs text-neutral-500 truncate mt-0.5">
              {mapping.policy_description}
            </p>
          )}
        </div>

        {/* Score */}
        <div className="flex-shrink-0">
          {score != null ? (
            <RelevanceBadge score={score} />
          ) : (
            <span className="text-xs text-neutral-400">—</span>
          )}
        </div>

        {/* Actions */}
        <div className="flex-shrink-0 flex items-center gap-1.5">
          {isRejected ? (
            <>
              <span className="text-xs font-medium text-neutral-400 bg-neutral-100 px-2 py-1 rounded-full">
                Rejected
              </span>
              <button
                onClick={handleUnreject}
                disabled={acting}
                className="flex items-center gap-1 text-xs font-medium text-neutral-600 hover:text-primary-600 border border-neutral-200 hover:border-primary-200 hover:bg-primary-50 px-2.5 py-1 rounded-full transition-colors disabled:opacity-50"
              >
                <RotateCcw className="h-3 w-3" /> Unreject
              </button>
            </>
          ) : (
            <button
              onClick={handleReject}
              disabled={acting}
              className="flex items-center gap-1 text-xs font-medium text-neutral-600 hover:text-red-600 border border-neutral-200 hover:border-red-200 hover:bg-red-50 px-2.5 py-1 rounded-full transition-colors disabled:opacity-50"
            >
              <X className="h-3 w-3" /> Mark as Irrelevant
            </button>
          )}
        </div>
      </div>

      {/* Summary + most relevant section */}
      {(mapping.policy_summary || mapping.source_excerpt) && (
        <div>
          <button
            onClick={() => setExpanded(!expanded)}
            className="flex items-center gap-1 text-xs text-neutral-500 hover:text-neutral-700 transition-colors"
          >
            {expanded ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
            {expanded ? 'Hide details' : 'Show details'}
          </button>
          {expanded && (
            <div className="mt-2 space-y-2">
              {mapping.policy_summary && (
                <div>
                  <div className="flex items-center gap-1.5 mb-1">
                    <p className="text-xs font-medium text-neutral-400 uppercase tracking-wide">Document summary</p>
                    <div className="relative group">
                      <Lightbulb className="h-3 w-3 text-neutral-400 cursor-help" />
                      <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-1.5 hidden group-hover:block z-10 w-56 px-2.5 py-1.5 bg-neutral-800 text-white text-xs rounded shadow-lg leading-relaxed pointer-events-none">
                        This summary was AI-generated from the document text. May contain errors or omissions — always verify against the original document when uncertain.
                        <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-neutral-800" />
                      </div>
                    </div>
                  </div>
                  <p className="text-xs text-neutral-600 leading-relaxed">
                    {mapping.policy_summary}
                  </p>
                </div>
              )}
              {mapping.source_excerpt && (
                <div>
                  <p className="text-xs font-medium text-neutral-400 uppercase tracking-wide mb-1">Most relevant section</p>
                  <blockquote className="pl-3 border-l-2 border-primary-300 text-xs text-neutral-500 italic leading-relaxed">
                    {mapping.source_excerpt}
                  </blockquote>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
