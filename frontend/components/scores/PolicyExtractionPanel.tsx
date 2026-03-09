'use client';

import { useState, useEffect, useCallback } from 'react';
import { ChevronDown, ChevronUp, Play, RefreshCw, CheckCircle, XCircle, Trash2 } from 'lucide-react';
import { LoadingSpinner } from '@/components/ui';
import { runPolicyExtraction, getPolicyStatements, deletePolicyStatement } from '@/lib/api';
import { PolicyStatement } from '@/lib/types';
import { useUserId } from '@/lib/hooks/useUserId';

interface PolicyExtractionPanelProps {
  assessmentId: string;
  requirementId: string;
}

function StatusCircle({ state }: { state: 'none' | 'found' | 'empty' | 'loading' }) {
  if (state === 'loading') {
    return (
      <div className="w-[72px] h-[72px] flex-shrink-0 flex items-center justify-center rounded-full bg-neutral-50 border-2 border-neutral-200">
        <LoadingSpinner size="sm" />
      </div>
    );
  }
  if (state === 'found') {
    return (
      <div className="w-[72px] h-[72px] flex-shrink-0 flex items-center justify-center rounded-full bg-green-50 border-2 border-green-200">
        <CheckCircle className="h-8 w-8 text-green-500" />
      </div>
    );
  }
  if (state === 'empty') {
    return (
      <div className="w-[72px] h-[72px] flex-shrink-0 flex items-center justify-center rounded-full bg-red-50 border-2 border-red-200">
        <XCircle className="h-8 w-8 text-red-400" />
      </div>
    );
  }
  // 'none' — not yet run
  return (
    <div className="w-[72px] h-[72px] flex-shrink-0 flex items-center justify-center rounded-full bg-neutral-50 border-2 border-dashed border-neutral-200">
      <span className="text-xs text-neutral-400 text-center leading-tight px-1">Not run</span>
    </div>
  );
}

export function PolicyExtractionPanel({ assessmentId, requirementId }: PolicyExtractionPanelProps) {
  const userId = useUserId();
  const uid = userId ?? undefined;

  const [expanded, setExpanded] = useState(false);
  const [loading, setLoading] = useState(false);
  const [extracting, setExtracting] = useState(false);
  const [statements, setStatements] = useState<PolicyStatement[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [hasExtracted, setHasExtracted] = useState(false);
  const [hasFetched, setHasFetched] = useState(false);

  const loadExisting = useCallback(async () => {
    setLoading(true);
    try {
      const result = await getPolicyStatements(assessmentId, requirementId, uid);
      setStatements(result.statements);
      if (result.count > 0) setHasExtracted(true);
    } catch {
      // fetch failed — don't retry
    } finally {
      setHasFetched(true);
      setLoading(false);
    }
  }, [assessmentId, requirementId, uid]);

  useEffect(() => {
    if (!hasFetched && !loading) {
      loadExisting();
    }
  }, [hasFetched, loading, loadExisting]);

  const handleExtract = async () => {
    setExtracting(true);
    setError(null);
    try {
      const result = await runPolicyExtraction(assessmentId, requirementId, uid);
      setStatements(result.statements);
      setHasExtracted(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Extraction failed');
    } finally {
      setExtracting(false);
    }
  };

  const handleDelete = async (statementId: string) => {
    try {
      await deletePolicyStatement(assessmentId, requirementId, statementId, uid);
      setStatements(prev => prev.filter(s => s.id !== statementId));
    } catch {
      // silently ignore
    }
  };

  const circleState: 'none' | 'found' | 'empty' | 'loading' =
    loading || extracting ? 'loading' :
    statements.length > 0 ? 'found' :
    hasExtracted ? 'empty' :
    'none';

  const summaryText =
    extracting ? 'Extracting policy statements…' :
    loading ? 'Loading…' :
    statements.length > 0 ? `${statements.length} statement${statements.length !== 1 ? 's' : ''} extracted` :
    hasExtracted ? 'No relevant policy statements found in mapped documents.' :
    'Run extraction to identify relevant policy statements from mapped documents.';

  return (
    <div className="rounded-xl border border-neutral-200 bg-white overflow-hidden">
      {/* Header row — always visible */}
      <div className="flex items-center gap-4 p-4">
        <StatusCircle state={circleState} />

        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold text-neutral-900">Policy Extraction</p>
          <p className="text-xs text-neutral-500 mt-0.5">Policy statements from mapped policy documents</p>
          <p className="text-xs text-neutral-600 mt-2 leading-relaxed">{summaryText}</p>
          {error && (
            <p className="text-xs text-red-600 mt-1">{error}</p>
          )}
        </div>

        <div className="flex items-center gap-2 flex-shrink-0">
          <button
            onClick={handleExtract}
            disabled={extracting || loading}
            className="flex items-center gap-1.5 text-xs font-medium text-white bg-primary-600 hover:bg-primary-700 disabled:opacity-50 px-2.5 py-1.5 rounded-md transition-colors"
          >
            {extracting ? (
              <RefreshCw className="h-3 w-3 animate-spin" />
            ) : hasExtracted ? (
              <RefreshCw className="h-3 w-3" />
            ) : (
              <Play className="h-3 w-3" />
            )}
            {hasExtracted ? 'Re-run' : 'Run'}
          </button>

          {statements.length > 0 && (
            <button
              onClick={() => setExpanded(v => !v)}
              className="text-neutral-400 hover:text-neutral-600 transition-colors"
            >
              {expanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
            </button>
          )}
        </div>
      </div>

      {/* Expanded statement list */}
      {expanded && statements.length > 0 && (
        <div className="border-t border-neutral-100 px-4 pb-4 pt-3 space-y-2">
          {statements.map(stmt => (
            <div
              key={stmt.id}
              className="relative bg-white border border-neutral-200 rounded-lg p-4 pr-36"
            >
              <p className="text-xs text-neutral-800 leading-relaxed">{stmt.statement}</p>
              <p className="mt-2 text-xs text-neutral-400">
                <span className="font-medium text-neutral-600">{stmt.document_title}</span>
                {stmt.document_section && <> &middot; {stmt.document_section}</>}
              </p>
              <button
                onClick={() => handleDelete(stmt.id)}
                className="absolute top-3 right-3 flex items-center gap-1 text-[11px] text-neutral-400 hover:text-red-600 border border-neutral-200 hover:border-red-300 bg-white hover:bg-red-50 px-2 py-1 rounded transition-colors"
              >
                <Trash2 className="h-3 w-3" />
                Mark as irrelevant
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
