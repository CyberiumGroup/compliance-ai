'use client';

import { useState, useRef, useEffect } from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';
import { RequirementScore, ScoreAncestor } from '@/lib/types';
import { RequirementScoreListItem } from './RequirementScoreListItem';
import { cn } from '@/lib/utils';

interface Props {
  scores: RequirementScore[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  checkedReqIds: Set<string>;
  onToggleReq: (reqId: string) => void;
  onToggleGroup: (reqIds: string[]) => void;
}

interface L2Group {
  key: string;
  ancestor: ScoreAncestor | null;
  scores: RequirementScore[];
}

interface L1Group {
  key: string;
  ancestor: ScoreAncestor | null;
  l2Groups: L2Group[];
}

function buildGroups(scores: RequirementScore[]): L1Group[] {
  const l1Groups: L1Group[] = [];
  const l1Map = new Map<string, number>();

  for (const score of scores) {
    const anc = score.ancestors ?? [];
    const l1 = anc[0] ?? null;
    const l2 = anc[1] ?? null;
    const l1Key = l1?.id ?? '__none__';

    let l1Idx = l1Map.get(l1Key);
    if (l1Idx === undefined) {
      l1Idx = l1Groups.length;
      l1Map.set(l1Key, l1Idx);
      l1Groups.push({ key: l1Key, ancestor: l1, l2Groups: [] });
    }

    const l2Key = l2?.id ?? '__none__';
    const l1Group = l1Groups[l1Idx];
    let l2Group = l1Group.l2Groups.find(g => g.key === l2Key);
    if (!l2Group) {
      l2Group = { key: l2Key, ancestor: l2, scores: [] };
      l1Group.l2Groups.push(l2Group);
    }
    l2Group.scores.push(score);
  }

  return l1Groups;
}

/** Checkbox that supports the HTML `indeterminate` state via a ref. */
function GroupCheckbox({
  checked,
  indeterminate,
  onChange,
}: {
  checked: boolean;
  indeterminate: boolean;
  onChange: () => void;
}) {
  const ref = useRef<HTMLInputElement>(null);
  useEffect(() => {
    if (ref.current) ref.current.indeterminate = indeterminate;
  }, [indeterminate]);
  return (
    <input
      ref={ref}
      type="checkbox"
      checked={checked}
      onChange={e => { e.stopPropagation(); onChange(); }}
      onClick={e => e.stopPropagation()}
      className="h-3.5 w-3.5 flex-shrink-0 cursor-pointer rounded"
    />
  );
}

export function RequirementScoreHierarchyList({
  scores,
  selectedId,
  onSelect,
  checkedReqIds,
  onToggleReq,
  onToggleGroup,
}: Props) {
  const groups = buildGroups(scores);
  const [collapsed, setCollapsed] = useState<Set<string>>(new Set());

  const toggle = (key: string) =>
    setCollapsed(prev => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });

  const isOpen = (key: string) => !collapsed.has(key);

  return (
    <div className="flex flex-col">
      {groups.map(l1 => {
        const l1ReqIds = l1.l2Groups.flatMap(g => g.scores.map(s => s.requirement_id));
        const l1CheckedCount = l1ReqIds.filter(id => checkedReqIds.has(id)).length;
        const l1AllChecked = l1ReqIds.length > 0 && l1CheckedCount === l1ReqIds.length;
        const l1Indeterminate = l1CheckedCount > 0 && !l1AllChecked;
        const l1Open = isOpen(l1.key);
        const totalCount = l1ReqIds.length;

        return (
          <div key={l1.key} className="mb-1">
            {/* L1 header — Function level */}
            <div className="flex items-center gap-1.5 px-1 py-1 rounded-md hover:bg-neutral-50 transition-colors">
              <GroupCheckbox
                checked={l1AllChecked}
                indeterminate={l1Indeterminate}
                onChange={() => onToggleGroup(l1ReqIds)}
              />
              <button
                onClick={() => toggle(l1.key)}
                className="flex items-center gap-1 flex-1 min-w-0 text-left"
              >
                {l1Open
                  ? <ChevronDown className="h-3.5 w-3.5 text-neutral-400 flex-shrink-0" />
                  : <ChevronRight className="h-3.5 w-3.5 text-neutral-400 flex-shrink-0" />}
                <span className="text-xs font-semibold text-neutral-700 flex-1 min-w-0 truncate">
                  {l1.ancestor
                    ? `${l1.ancestor.code} — ${l1.ancestor.name}`
                    : 'Requirements'}
                </span>
              </button>
              <span className="text-[10px] text-neutral-400 tabular-nums flex-shrink-0">
                {totalCount}
              </span>
            </div>

            {l1Open && (
              <div className="mt-0.5">
                {l1.l2Groups.map(l2 => {
                  const l2CompositeKey = `${l1.key}::${l2.key}`;
                  const l2ReqIds = l2.scores.map(s => s.requirement_id);
                  const l2CheckedCount = l2ReqIds.filter(id => checkedReqIds.has(id)).length;
                  const l2AllChecked = l2ReqIds.length > 0 && l2CheckedCount === l2ReqIds.length;
                  const l2Indeterminate = l2CheckedCount > 0 && !l2AllChecked;
                  const l2Open = isOpen(l2CompositeKey);

                  // No L2 ancestor — render items directly under L1
                  if (!l2.ancestor) {
                    return (
                      <div key={l2.key} className="pl-4 flex flex-col gap-1 mt-0.5">
                        {l2.scores.map(score => (
                          <RequirementScoreListItem
                            key={score.id}
                            score={score}
                            selected={score.id === selectedId}
                            onSelect={() => onSelect(score.id)}
                            checked={checkedReqIds.has(score.requirement_id)}
                            onToggle={() => onToggleReq(score.requirement_id)}
                          />
                        ))}
                      </div>
                    );
                  }

                  return (
                    <div key={l2.key} className="mb-0.5">
                      {/* L2 header — Category level */}
                      <div className="flex items-center gap-1.5 pl-5 pr-1 py-0.5 rounded-md hover:bg-neutral-50 transition-colors">
                        <GroupCheckbox
                          checked={l2AllChecked}
                          indeterminate={l2Indeterminate}
                          onChange={() => onToggleGroup(l2ReqIds)}
                        />
                        <button
                          onClick={() => toggle(l2CompositeKey)}
                          className="flex items-center gap-1 flex-1 min-w-0 text-left"
                        >
                          {l2Open
                            ? <ChevronDown className="h-3 w-3 text-neutral-300 flex-shrink-0" />
                            : <ChevronRight className="h-3 w-3 text-neutral-300 flex-shrink-0" />}
                          <span className={cn(
                            'text-[11px] font-medium flex-1 min-w-0 truncate',
                            l2Open ? 'text-neutral-600' : 'text-neutral-400',
                          )}>
                            {l2.ancestor.code} — {l2.ancestor.name}
                          </span>
                        </button>
                        <span className="text-[10px] text-neutral-400 tabular-nums flex-shrink-0">
                          {l2ReqIds.length}
                        </span>
                      </div>

                      {l2Open && (
                        <div className="pl-9 flex flex-col gap-1 mt-0.5 mb-1">
                          {l2.scores.map(score => (
                            <RequirementScoreListItem
                              key={score.id}
                              score={score}
                              selected={score.id === selectedId}
                              onSelect={() => onSelect(score.id)}
                              checked={checkedReqIds.has(score.requirement_id)}
                              onToggle={() => onToggleReq(score.requirement_id)}
                            />
                          ))}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
