'use client';

import { SkipForward } from 'lucide-react';
import { RequirementScore } from '@/lib/types';
import { cn } from '@/lib/utils';

interface RequirementScoreListItemProps {
  score: RequirementScore;
  selected: boolean;
  onSelect: () => void;
  checked?: boolean;
  onToggle?: () => void;
}

function ScorePip({ value, label }: { value: number | null; label: string }) {
  if (value === null) {
    return <span className="text-[10px] text-neutral-400">{label}: —</span>;
  }
  const color =
    value >= 75 ? 'text-green-700' :
    value >= 50 ? 'text-amber-600' :
    value >= 25 ? 'text-orange-600' :
    'text-red-600';
  return (
    <span className={cn('text-[10px] font-semibold tabular-nums', color)}>
      {label}: {Math.round(value)}%
    </span>
  );
}

export function RequirementScoreListItem({
  score,
  selected,
  onSelect,
  checked,
  onToggle,
}: RequirementScoreListItemProps) {
  const isSkipped = score.status === 'skipped';
  const isCompleted = score.status === 'completed';
  const isFailed = score.status === 'failed';

  return (
    <div
      className={cn(
        'w-full flex items-start gap-2 px-2 py-2 rounded-lg border transition-colors',
        selected
          ? 'border-primary-300 bg-primary-50'
          : 'border-neutral-200 bg-white hover:bg-neutral-50',
      )}
    >
      {onToggle !== undefined && (
        <input
          type="checkbox"
          checked={checked ?? false}
          onChange={onToggle}
          onClick={e => e.stopPropagation()}
          className="mt-0.5 h-3.5 w-3.5 flex-shrink-0 cursor-pointer rounded"
        />
      )}

      <button onClick={onSelect} className="flex-1 min-w-0 text-left">
        <div className="flex items-start gap-2">
          <span className="font-mono text-[11px] font-semibold text-primary-700 bg-primary-50 border border-primary-200 px-1.5 py-0.5 rounded flex-shrink-0">
            {score.requirement_code ?? '—'}
          </span>
          <span className="text-xs text-neutral-700 leading-snug line-clamp-2 flex-1">
            {score.requirement_name}
          </span>
        </div>

        <div className="mt-1.5 flex items-center gap-3 flex-wrap pl-0.5">
          {isSkipped && (
            <span className="flex items-center gap-1 text-[10px] text-red-600 font-medium">
              <SkipForward className="h-3 w-3" />
              Missing documentation
            </span>
          )}
          {isFailed && (
            <span className="text-[10px] text-red-500 font-medium">Failed</span>
          )}
          {isCompleted && (
            <>
              <ScorePip value={score.score1} label="Design" />
              <ScorePip value={score.score2} label="Risk" />
              <ScorePip value={score.score3} label="Peer" />
            </>
          )}
          {!isSkipped && !isFailed && !isCompleted && (
            <span className="text-[10px] text-neutral-400">Not scored</span>
          )}
        </div>
      </button>
    </div>
  );
}
