'use client';

import { useState } from 'react';
import { ChevronDown, ChevronUp, Code2 } from 'lucide-react';

interface PhaseOutputDrawerProps {
  phase1Output: Record<string, unknown> | null;
  phase2Output: Record<string, unknown> | null;
  phase2bOutput?: Record<string, unknown> | null;
  phase4Output: Record<string, unknown> | null;
  phase5Output: Record<string, unknown> | null;
}

export function PhaseOutputDrawer({
  phase1Output,
  phase2Output,
  phase2bOutput,
  phase4Output,
  phase5Output,
}: PhaseOutputDrawerProps) {
  const [open, setOpen] = useState(false);

  const outputs = [
    { label: 'Phase 1 — Element Decomposition', data: phase1Output },
    { label: 'Phase 2a — Design Evaluation', data: phase2Output },
    { label: 'Phase 2b — Implementation Evaluation', data: phase2bOutput },
    { label: 'Phase 4 — Mechanism Extraction', data: phase4Output },
    { label: 'Phase 5 — Mechanism Evaluations', data: phase5Output },
  ].filter(o => o.data);

  if (outputs.length === 0) return null;

  return (
    <div className="mt-2">
      <button
        onClick={() => setOpen(v => !v)}
        className="flex items-center gap-1.5 text-xs text-neutral-400 hover:text-neutral-600 transition-colors"
      >
        <Code2 className="h-3.5 w-3.5" />
        {open ? 'Hide' : 'Show'} raw phase outputs
        {open ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
      </button>

      {open && (
        <div className="mt-3 space-y-3">
          {outputs.map(({ label, data }) => (
            <div key={label} className="rounded-lg border border-neutral-200 overflow-hidden">
              <div className="px-3 py-2 bg-neutral-50 border-b border-neutral-200">
                <p className="text-xs font-mono font-semibold text-neutral-600">{label}</p>
              </div>
              <pre className="px-3 py-2 text-[10px] leading-relaxed text-neutral-700 overflow-x-auto max-h-48 bg-white">
                {JSON.stringify(data, null, 2)}
              </pre>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
