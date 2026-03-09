'use client';

import { useState, useEffect } from 'react';
import { ChevronDown, ChevronUp, FileText, BookOpen, XCircle, AlertTriangle, Shield } from 'lucide-react';
import { PolicyMapping } from '@/lib/types';
import { PolicyRelevanceRow } from './PolicyRelevanceRow';
import { cn } from '@/lib/utils';

interface RequirementMappingGroupProps {
  requirementCode: string;
  requirementName: string | null;
  requirementDescription: string | null;
  requirementGuidance: string | null;
  requirementParentCode: string | null;
  mappings: PolicyMapping[];
  defaultThreshold: number;
  onThresholdChange?: (threshold: number) => void;
  onReject: (mappingId: string) => Promise<void>;
  onUnreject: (mappingId: string) => Promise<void>;
}

export function RequirementMappingGroup({
  requirementCode,
  requirementName,
  requirementDescription,
  requirementGuidance,
  requirementParentCode,
  mappings,
  defaultThreshold,
  onThresholdChange,
  onReject,
  onUnreject,
}: RequirementMappingGroupProps) {
  const [collapsed, setCollapsed] = useState(false);
  const [threshold, setThreshold] = useState(defaultThreshold);

  // Sync when the global default changes
  useEffect(() => {
    setThreshold(defaultThreshold);
  }, [defaultThreshold]);
  const [guidanceExpanded, setGuidanceExpanded] = useState(false);
  const [showRejected, setShowRejected] = useState(false);

  const activeMappings = mappings.filter((m) => !m.is_rejected);
  const rejectedMappings = mappings.filter((m) => m.is_rejected);

  const getScore = (m: PolicyMapping) =>
    m.relevance_percentage ?? (m.confidence_score != null ? (m.confidence_score + 1) / 2 * 100 : 0);

  // Sort active mappings by relevance descending
  const sorted = [...activeMappings].sort((a, b) => getScore(b) - getScore(a));

  // Filter by threshold — these are the "pending" mappings
  const displayed = sorted.filter((m) => getScore(m) >= threshold);

  const policyDisplayed   = displayed.filter(m => m.policy_document_type === 'policy');
  const evidenceDisplayed = displayed.filter(m => m.policy_document_type === 'evidence');

  return (
    <div className="rounded-xl border border-neutral-200 bg-white overflow-hidden shadow-sm">
      {/* Header */}
      <button
        className="w-full flex items-start gap-3 px-4 py-3 text-left hover:bg-neutral-50 transition-colors"
        onClick={() => setCollapsed(!collapsed)}
      >
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            {requirementParentCode && (
              <span className="font-mono text-xs text-neutral-400 bg-neutral-100 border border-neutral-200 px-2 py-0.5 rounded">
                {requirementParentCode}
              </span>
            )}
            {requirementParentCode && (
              <span className="text-neutral-300 text-xs">›</span>
            )}
            <span className="font-mono text-xs font-semibold text-primary-700 bg-primary-50 border border-primary-200 px-2 py-0.5 rounded">
              {requirementCode}
            </span>
            {requirementName && (
              <span className="text-sm font-medium text-neutral-900">
                {requirementName}
              </span>
            )}
          </div>
          {requirementDescription && (
            <p className="text-xs text-neutral-600 mt-1.5 leading-relaxed">
              {requirementDescription}
            </p>
          )}
        </div>

        {/* Stats */}
        <div className="flex-shrink-0 flex items-center gap-2">
          {policyDisplayed.length > 0 ? (
            <span className="flex items-center gap-1 text-xs font-medium text-green-700 bg-green-100 px-2 py-0.5 rounded-full">
              <FileText className="h-3 w-3" />
              {policyDisplayed.length} {policyDisplayed.length === 1 ? 'policy' : 'policies'}
            </span>
          ) : (
            <span
              className="flex items-center gap-1 text-xs font-medium text-red-600 bg-red-50 ring-1 ring-red-200 px-2 py-0.5 rounded-full"
              title="No policy documents meet the threshold — Documentation scoring (Phase 2) will be skipped."
            >
              <AlertTriangle className="h-3 w-3" />
              No policy mapped
            </span>
          )}
          {evidenceDisplayed.length > 0 ? (
            <span className="flex items-center gap-1 text-xs font-medium text-teal-700 bg-teal-50 px-2 py-0.5 rounded-full">
              <Shield className="h-3 w-3" />
              {evidenceDisplayed.length} {evidenceDisplayed.length === 1 ? 'evidence doc' : 'evidence docs'}
            </span>
          ) : (
            <span
              className="flex items-center gap-1 text-xs font-medium text-amber-700 bg-amber-50 ring-1 ring-amber-200 px-2 py-0.5 rounded-full"
              title="No evidence documents meet the threshold — implementation depth evidence evaluation will be skipped."
            >
              <AlertTriangle className="h-3 w-3" />
              No evidence
            </span>
          )}
          {rejectedMappings.length > 0 && (
            <span className="flex items-center gap-1 text-xs font-medium text-neutral-500 bg-neutral-100 px-2 py-0.5 rounded-full">
              <XCircle className="h-3 w-3" />
              {rejectedMappings.length} rejected
            </span>
          )}
          {collapsed ? (
            <ChevronDown className="h-4 w-4 text-neutral-400" />
          ) : (
            <ChevronUp className="h-4 w-4 text-neutral-400" />
          )}
        </div>
      </button>

      {/* Body */}
      {!collapsed && (
        <div className={cn('px-4 pb-4 space-y-2', mappings.length > 0 ? 'pt-1' : 'pt-2')}>
          {/* Guidance */}
          {requirementGuidance && (
            <div className="border border-neutral-100 rounded-lg overflow-hidden">
              <button
                onClick={(e) => { e.stopPropagation(); setGuidanceExpanded(!guidanceExpanded); }}
                className="w-full flex items-center gap-2 px-3 py-2 text-left bg-neutral-50 hover:bg-neutral-100 transition-colors"
              >
                <BookOpen className="h-3.5 w-3.5 text-neutral-400 flex-shrink-0" />
                <span className="text-xs font-medium text-neutral-600 flex-1">Implementation guidance</span>
                {guidanceExpanded
                  ? <ChevronUp className="h-3.5 w-3.5 text-neutral-400" />
                  : <ChevronDown className="h-3.5 w-3.5 text-neutral-400" />}
              </button>
              {guidanceExpanded && (
                <div className="px-3 py-2.5 text-xs text-neutral-600 leading-relaxed whitespace-pre-wrap bg-white">
                  {requirementGuidance}
                </div>
              )}
            </div>
          )}

          {/* Threshold control */}
          <div
            className="flex items-center gap-3 py-2 border-b border-neutral-100"
            onClick={(e) => e.stopPropagation()}
          >
            <span className="text-xs text-neutral-500 whitespace-nowrap">Min. relevance</span>
            <input
              type="range"
              min={0}
              max={100}
              step={1}
              value={threshold}
              onChange={(e) => { const t = Number(e.target.value); setThreshold(t); onThresholdChange?.(t); }}
              className="w-28 accent-primary-500 cursor-pointer"
            />
            <span className="text-xs font-semibold text-neutral-700 w-8 text-right tabular-nums">
              {threshold}%
            </span>
            {threshold !== defaultThreshold && (
              <button
                onClick={() => setThreshold(defaultThreshold)}
                className="text-xs text-neutral-400 hover:text-neutral-600 transition-colors"
              >
                Reset
              </button>
            )}
          </div>

          {/* Active (pending) mappings */}
          {displayed.length === 0 ? (
            <p className="text-xs text-neutral-400 py-2">
              {sorted.length === 0
                ? 'No documents meet the relevance threshold for this requirement.'
                : `No documents meet the ${threshold}% threshold. Lower the slider to see more.`}
            </p>
          ) : (
            displayed.map((mapping) => (
              <PolicyRelevanceRow
                key={mapping.id}
                mapping={mapping}
                onReject={() => onReject(mapping.id)}
                onUnreject={() => onUnreject(mapping.id)}
              />
            ))
          )}

          {/* Rejected section toggle */}
          {rejectedMappings.length > 0 && (
            <div className="pt-1">
              <button
                onClick={(e) => { e.stopPropagation(); setShowRejected(!showRejected); }}
                className="flex items-center gap-1.5 text-xs text-neutral-400 hover:text-neutral-600 transition-colors"
              >
                <XCircle className="h-3.5 w-3.5" />
                {showRejected
                  ? 'Hide rejected'
                  : `Show ${rejectedMappings.length} rejected`}
                {showRejected
                  ? <ChevronUp className="h-3 w-3" />
                  : <ChevronDown className="h-3 w-3" />}
              </button>

              {showRejected && (
                <div className="mt-2 space-y-2">
                  {rejectedMappings.map((mapping) => (
                    <PolicyRelevanceRow
                      key={mapping.id}
                      mapping={mapping}
                      onReject={() => onReject(mapping.id)}
                      onUnreject={() => onUnreject(mapping.id)}
                    />
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
