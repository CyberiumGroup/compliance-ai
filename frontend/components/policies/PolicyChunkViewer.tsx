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

// ── Tabular chunk parser ──────────────────────────────────────────────────────

interface ParsedTable {
  sheetName: string;
  headers: string[];
  rows: string[][];
}

function parseTabularChunk(text: string): ParsedTable | null {
  const doubleBreak = text.indexOf('\n\n');
  if (doubleBreak === -1) return null;

  const sheetName = text.slice(0, doubleBreak).trim();
  const tableText = text.slice(doubleBreak + 2);
  const lines = tableText.split('\n').filter(l => l.trim().startsWith('|'));
  if (lines.length < 2) return null;

  const parseRow = (line: string): string[] =>
    line.split('|').slice(1, -1).map(c => c.trim());

  // A GFM separator row has every cell consisting solely of dashes and/or colons.
  // Using cell-level checking avoids false positives on rows with empty cells,
  // numeric-only cells, or any other data that happens to match a loose line regex.
  const isSeparator = (line: string): boolean => {
    const cells = parseRow(line);
    return cells.length > 0 && cells.every(cell => /^[-:]+$/.test(cell));
  };

  const headers = parseRow(lines[0]);
  const dataLines = lines.slice(1).filter(l => !isSeparator(l));
  const rows = dataLines.map(parseRow);

  return { sheetName, headers, rows };
}

// ── Tabular chunk renderer ────────────────────────────────────────────────────

function TabularChunkItem({
  chunk,
  isExpanded,
  onToggle,
}: {
  chunk: PolicyChunk;
  isExpanded: boolean;
  onToggle: () => void;
}) {
  const parsed = parseTabularChunk(chunk.chunk_text);

  return (
    <div className="rounded-lg border border-teal-100 bg-teal-50/40 px-3 py-2 text-xs">
      {/* Header row — always clickable */}
      <button onClick={onToggle} className="flex w-full items-center gap-2 text-left">
        <span className="shrink-0">
          <span
            className={cn(
              'inline-block h-2 w-2 rounded-full',
              chunk.has_embedding ? 'bg-accent-500' : 'bg-neutral-300'
            )}
            title={chunk.has_embedding ? 'Embedded' : 'Not yet embedded'}
          />
        </span>
        <span className="font-mono text-neutral-400 shrink-0">#{chunk.chunk_index + 1}</span>
        {parsed ? (
          <span className="text-teal-700 font-medium truncate">{parsed.sheetName}</span>
        ) : (
          <span className="text-neutral-500 truncate">{chunk.chunk_text.slice(0, 60)}</span>
        )}
        {parsed && (
          <span className="shrink-0 text-neutral-400 ml-1">
            {parsed.rows.length} rows · {parsed.headers.length} cols
          </span>
        )}
        <span className="shrink-0 text-neutral-400 ml-auto">
          {isExpanded ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
        </span>
      </button>

      {/* Expanded: render the table */}
      {isExpanded && parsed && (
        <div className="mt-3 overflow-x-auto rounded border border-teal-100">
          <table className="w-full text-xs border-collapse">
            <thead>
              <tr className="bg-teal-100/60">
                {parsed.headers.map((h, i) => (
                  <th
                    key={i}
                    className="px-3 py-1.5 text-left font-semibold text-teal-800 border-b border-teal-200 whitespace-nowrap"
                  >
                    {h || <span className="text-neutral-400 italic">—</span>}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {parsed.rows.map((row, ri) => (
                <tr key={ri} className={ri % 2 === 0 ? 'bg-white' : 'bg-teal-50/30'}>
                  {parsed.headers.map((_, ci) => (
                    <td
                      key={ci}
                      className="px-3 py-1.5 text-neutral-700 border-b border-neutral-100 whitespace-nowrap max-w-xs truncate"
                      title={row[ci] ?? ''}
                    >
                      {row[ci] ?? ''}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Fallback: raw text if parse failed */}
      {isExpanded && !parsed && (
        <p className="mt-2 font-mono text-neutral-600 whitespace-pre-wrap break-words">
          {chunk.chunk_text}
        </p>
      )}

      <div className="mt-1.5 text-neutral-400 pl-4">~{chunk.token_count} tokens</div>
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

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

                if (chunkStrategy === 'tabular') {
                  return (
                    <TabularChunkItem
                      key={chunk.chunk_index}
                      chunk={chunk}
                      isExpanded={isExpanded}
                      onToggle={() => toggleChunk(chunk.chunk_index)}
                    />
                  );
                }

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
