'use client';

import { useState } from 'react';
import { ChevronDown, ChevronRight, Atom, RefreshCw, AlertTriangle } from 'lucide-react';
import { getPolicyFacts, regeneratePolicyFacts } from '@/lib/api/policies';
import { PolicyFact } from '@/lib/types';
import { cn } from '@/lib/utils';

interface PolicyFactViewerProps {
  assessmentId: string;
  policyId: string;
  factsExtractedAt: string | null;
  userId?: string;
}

// ── Single fact row ────────────────────────────────────────────────────────────

function FactRow({ fact }: { fact: PolicyFact }) {
  const [expanded, setExpanded] = useState(false);
  const attrs = fact.key_attributes;
  const hasAttrs = attrs && Object.values(attrs).some(v => v !== null && v !== '');

  return (
    <div className="rounded-lg border border-neutral-100 bg-neutral-50 text-xs">
      <button
        onClick={() => setExpanded(e => !e)}
        className="flex w-full items-start gap-2 px-3 py-2 text-left"
      >
        <span className={cn(
          'shrink-0 mt-0.5 inline-block h-2 w-2 rounded-full',
          fact.confidence === 'explicit' ? 'bg-accent-500' : 'bg-amber-400'
        )}
          title={fact.confidence === 'explicit' ? 'Explicit' : fact.confidence === 'implied' ? 'Implied' : undefined}
        />
        <span className="flex-1 text-neutral-700 break-words min-w-0 leading-relaxed">
          {fact.statement}
        </span>
        {(hasAttrs || fact.document_reference?.section) && (
          <span className="shrink-0 text-neutral-400 ml-1">
            {expanded ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
          </span>
        )}
      </button>

      {expanded && (
        <div className="px-3 pb-2.5 space-y-1.5 pl-7">
          {fact.document_reference?.section && (
            <p className="text-neutral-400">
              <span className="font-medium text-neutral-500">Section:</span>{' '}
              {fact.document_reference.section}
            </p>
          )}
          {attrs && Object.entries(attrs).map(([key, val]) =>
            val ? (
              <p key={key} className="text-neutral-500">
                <span className="font-medium capitalize">{key.replace(/_/g, ' ')}:</span>{' '}
                {val}
              </p>
            ) : null
          )}
        </div>
      )}
    </div>
  );
}

// ── Main component ─────────────────────────────────────────────────────────────

export function PolicyFactViewer({
  assessmentId,
  policyId,
  factsExtractedAt: initialExtractedAt,
  userId,
}: PolicyFactViewerProps) {
  const [open, setOpen] = useState(false);
  const [facts, setFacts] = useState<PolicyFact[] | null>(null);
  const [extractedAt, setExtractedAt] = useState<string | null>(initialExtractedAt);
  const [loading, setLoading] = useState(false);
  const [regenerating, setRegenerating] = useState(false);
  const [queued, setQueued] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleToggle = async () => {
    if (!open && facts === null) {
      setLoading(true);
      setError(null);
      try {
        const data = await getPolicyFacts(assessmentId, policyId);
        setFacts(data.facts);
        setExtractedAt(data.facts_extracted_at);
      } catch {
        setError('Failed to load facts');
      } finally {
        setLoading(false);
      }
    }
    setOpen(prev => !prev);
  };

  const handleRegenerate = async (e: React.MouseEvent) => {
    e.stopPropagation();
    setRegenerating(true);
    setError(null);
    try {
      await regeneratePolicyFacts(assessmentId, policyId, userId);
      setExtractedAt(null);
      setFacts(null);
      setQueued(true);
      setOpen(false);
    } catch {
      setError('Failed to queue regeneration');
    } finally {
      setRegenerating(false);
    }
  };

  const isPending = extractedAt === null;
  const factCount = facts?.length ?? 0;

  return (
    <div className="mt-2 border-t border-neutral-100 pt-2">
      <div className="flex items-center gap-2">
        <button
          onClick={handleToggle}
          className="flex items-center gap-1.5 text-xs text-neutral-500 hover:text-neutral-700 transition-colors flex-1 min-w-0"
        >
          {open ? <ChevronDown className="h-3.5 w-3.5 shrink-0" /> : <ChevronRight className="h-3.5 w-3.5 shrink-0" />}
          <Atom className="h-3.5 w-3.5 shrink-0" />
          {loading ? 'Loading facts…' : 'View facts'}
        </button>

        <button
          onClick={handleRegenerate}
          disabled={regenerating}
          className="shrink-0 flex items-center gap-1 text-xs text-neutral-400 hover:text-primary-600 transition-colors disabled:opacity-50"
          title="Re-run fact extraction for this document"
        >
          <RefreshCw className={cn('h-3 w-3', regenerating && 'animate-spin')} />
          {regenerating ? 'Queuing…' : 'Regenerate'}
        </button>
      </div>

      {open && !loading && (
        <div className="mt-2 space-y-1">
          {error ? (
            <p className="text-xs text-red-500">{error}</p>
          ) : facts && facts.length > 0 ? (
            <>
              <p className="text-xs text-neutral-400 mb-1.5">
                {facts.length} fact{facts.length !== 1 ? 's' : ''} extracted
                {extractedAt && (
                  <> · {new Date(extractedAt).toLocaleDateString()}</>
                )}
              </p>
              {facts.map(fact => (
                <FactRow key={fact.id} fact={fact} />
              ))}
            </>
          ) : queued ? (
            <p className="text-xs text-neutral-400">
              Extraction is running in the background. Refresh the page or click Regenerate to check again.
            </p>
          ) : isPending ? (
            <p className="text-xs text-neutral-400">
              No facts extracted yet. Click Regenerate to run extraction.
            </p>
          ) : (
            <p className="text-xs text-neutral-400">
              No facts were extracted from this document. Click Regenerate to try again.
            </p>
          )}
        </div>
      )}
    </div>
  );
}
