'use client';

import { useState } from 'react';
import { ChevronDown, ChevronRight, Layers } from 'lucide-react';
import { getPolicyChunks, PolicyChunk } from '@/lib/api/policies';
import { cn } from '@/lib/utils';

interface PolicyChunkViewerProps {
  assessmentId: string;
  policyId: string;
  chunkStrategy: string | null;
}

export function PolicyChunkViewer({ assessmentId, policyId, chunkStrategy }: PolicyChunkViewerProps) {
  const [open, setOpen] = useState(false);
  const [chunks, setChunks] = useState<PolicyChunk[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedChunks, setExpandedChunks] = useState<Set<number>>(new Set());

  const handleToggle = async () => {
    if (!open && chunks === null) {
      setLoading(true);
      try {
        const data = await getPolicyChunks(assessmentId, policyId);
        setChunks(data);
      } catch {
        setError('Failed to load chunks');
      } finally {
        setLoading(false);
      }
    }
    setOpen(prev => !prev);
  };

  const toggleChunk = (index: number) => {
    setExpandedChunks(prev => {
      const next = new Set(prev);
      if (next.has(index)) next.delete(index);
      else next.add(index);
      return next;
    });
  };

  const embeddedCount = chunks ? chunks.filter(c => c.has_embedding).length : 0;

  return (
    <div className="mt-3 border-t border-neutral-100 pt-3">
      <button
        onClick={handleToggle}
        className="flex items-center gap-1.5 text-xs text-neutral-500 hover:text-neutral-700 transition-colors"
      >
        {open ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}
        <Layers className="h-3.5 w-3.5" />
        {loading ? 'Loading chunks…' : 'View chunks'}
      </button>

      {open && !loading && (
        <div className="mt-2 space-y-1">
          {error ? (
            <p className="text-xs text-red-500">{error}</p>
          ) : chunks && chunks.length > 0 ? (
            <>
              <p className="text-xs text-neutral-400 mb-2">
                {chunks.length} chunk{chunks.length !== 1 ? 's' : ''}
                {chunkStrategy ? ` · ${chunkStrategy}` : ''}
                {' · '}
                <span className={embeddedCount === chunks.length ? 'text-accent-600' : 'text-neutral-400'}>
                  {embeddedCount}/{chunks.length} embedded
                </span>
              </p>
              {chunks.map((chunk) => {
                const isExpanded = expandedChunks.has(chunk.chunk_index);
                const preview = chunk.chunk_text.slice(0, 150);
                const hasMore = chunk.chunk_text.length > 150;
                return (
                  <div
                    key={chunk.chunk_index}
                    className="rounded-lg border border-neutral-100 bg-neutral-50 px-3 py-2 text-xs"
                  >
                    <button
                      onClick={() => toggleChunk(chunk.chunk_index)}
                      className="flex w-full items-start gap-2 text-left"
                    >
                      <span className="shrink-0 mt-0.5">
                        <span
                          className={cn(
                            'inline-block h-2 w-2 rounded-full',
                            chunk.has_embedding ? 'bg-accent-500' : 'bg-neutral-300'
                          )}
                          title={chunk.has_embedding ? 'Embedded' : 'Not yet embedded'}
                        />
                      </span>
                      <span className="font-mono text-neutral-400 shrink-0">
                        #{chunk.chunk_index + 1}
                      </span>
                      <span className="text-neutral-700 break-words min-w-0">
                        {isExpanded ? chunk.chunk_text : preview}
                        {!isExpanded && hasMore && (
                          <span className="text-neutral-400"> …</span>
                        )}
                      </span>
                      {hasMore && (
                        <span className="shrink-0 text-neutral-400 ml-auto">
                          {isExpanded ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
                        </span>
                      )}
                    </button>
                    <div className="mt-1 flex items-center gap-3 text-neutral-400 pl-8">
                      <span>~{chunk.token_count} tokens</span>
                    </div>
                  </div>
                );
              })}
            </>
          ) : (
            <p className="text-xs text-neutral-400">No chunks stored yet.</p>
          )}
        </div>
      )}
    </div>
  );
}
