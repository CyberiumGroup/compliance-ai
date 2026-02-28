'use client';

import { useState, useRef, useEffect } from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';
import { RequirementScore, ScoreAncestor } from '@/lib/types';
import { RequirementScoreListItem } from './RequirementScoreListItem';
import { cn } from '@/lib/utils';

interface FrameworkInfo {
  name: string;
  type: string;
}

interface Props {
  scores: RequirementScore[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  checkedReqIds: Set<string>;
  onToggleReq: (reqId: string) => void;
  onToggleGroup: (reqIds: string[]) => void;
  frameworkMap?: Map<string, FrameworkInfo>;
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

interface L0Group {
  key: string;
  name: string;
  type: string;
  l1Groups: L1Group[];
}

const FRAMEWORK_TYPE_COLORS: Record<string, string> = {
  nist_csf: 'bg-blue-100 text-blue-700',
  iso_27001: 'bg-green-100 text-green-700',
  soc2_tsc: 'bg-purple-100 text-purple-700',
  custom: 'bg-orange-100 text-orange-700',
};

function buildGroups(scores: RequirementScore[], frameworkMap?: Map<string, FrameworkInfo>): L0Group[] {
  const l0Groups: L0Group[] = [];
  const l0Map = new Map<string, number>();

  for (const score of scores) {
    const fwId = score.framework_id ?? '__none__';
    const fwInfo = frameworkMap?.get(fwId);
    const fwName = fwInfo?.name ?? 'Requirements';
    const fwType = fwInfo?.type ?? 'custom';

    let l0Idx = l0Map.get(fwId);
    if (l0Idx === undefined) {
      l0Idx = l0Groups.length;
      l0Map.set(fwId, l0Idx);
      l0Groups.push({ key: fwId, name: fwName, type: fwType, l1Groups: [] });
    }
    const l0Group = l0Groups[l0Idx];

    const anc = score.ancestors ?? [];
    const l1 = anc[0] ?? null;
    const l2 = anc[1] ?? null;
    const l1Key = l1?.id ?? '__none__';

    let l1Group = l0Group.l1Groups.find(g => g.key === l1Key);
    if (!l1Group) {
      l1Group = { key: l1Key, ancestor: l1, l2Groups: [] };
      l0Group.l1Groups.push(l1Group);
    }

    const l2Key = l2?.id ?? '__none__';
    let l2Group = l1Group.l2Groups.find(g => g.key === l2Key);
    if (!l2Group) {
      l2Group = { key: l2Key, ancestor: l2, scores: [] };
      l1Group.l2Groups.push(l2Group);
    }
    l2Group.scores.push(score);
  }

  return l0Groups;
}

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
  frameworkMap,
}: Props) {
  const l0Groups = buildGroups(scores, frameworkMap);
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
    <div className="flex flex-col gap-1">
      {l0Groups.map(l0 => {
        const l0ReqIds = l0.l1Groups.flatMap(l1 => l1.l2Groups.flatMap(g => g.scores.map(s => s.requirement_id)));
        const l0CheckedCount = l0ReqIds.filter(id => checkedReqIds.has(id)).length;
        const l0AllChecked = l0ReqIds.length > 0 && l0CheckedCount === l0ReqIds.length;
        const l0Indeterminate = l0CheckedCount > 0 && !l0AllChecked;
        const l0Open = isOpen(l0.key);
        const colorClass = FRAMEWORK_TYPE_COLORS[l0.type] ?? FRAMEWORK_TYPE_COLORS.custom;

        return (
          <div key={l0.key}>
            {/* L0 — Framework */}
            <div className="flex items-center gap-2 py-1.5">
              <GroupCheckbox checked={l0AllChecked} indeterminate={l0Indeterminate} onChange={() => onToggleGroup(l0ReqIds)} />
              <button onClick={() => toggle(l0.key)} className="flex items-center gap-1.5 flex-1 min-w-0 text-left">
                {l0Open
                  ? <ChevronDown className="h-3.5 w-3.5 text-neutral-400 flex-shrink-0" />
                  : <ChevronRight className="h-3.5 w-3.5 text-neutral-400 flex-shrink-0" />}
                <span className={cn('text-[11px] font-semibold px-2 py-0.5 rounded-full truncate', colorClass)}>
                  {l0.name}
                </span>
                <span className="text-[10px] text-neutral-400 tabular-nums ml-auto flex-shrink-0">
                  {l0ReqIds.length}
                </span>
              </button>
            </div>

            {/* L1 children — indented under framework */}
            {l0Open && (
              <div className="ml-5 pl-3 border-l border-neutral-200 flex flex-col gap-0.5 mb-1">
                {l0.l1Groups.map(l1 => {
                  const l1ReqIds = l1.l2Groups.flatMap(g => g.scores.map(s => s.requirement_id));
                  const l1CheckedCount = l1ReqIds.filter(id => checkedReqIds.has(id)).length;
                  const l1AllChecked = l1ReqIds.length > 0 && l1CheckedCount === l1ReqIds.length;
                  const l1Indeterminate = l1CheckedCount > 0 && !l1AllChecked;
                  const l1Key = `${l0.key}::${l1.key}`;
                  const l1Open = isOpen(l1Key);

                  return (
                    <div key={l1.key}>
                      {/* L1 — Function */}
                      <div className="flex items-center gap-2 py-1 rounded-md hover:bg-neutral-50 transition-colors">
                        <GroupCheckbox checked={l1AllChecked} indeterminate={l1Indeterminate} onChange={() => onToggleGroup(l1ReqIds)} />
                        <button onClick={() => toggle(l1Key)} className="flex items-center gap-1 flex-1 min-w-0 text-left">
                          {l1Open
                            ? <ChevronDown className="h-3.5 w-3.5 text-neutral-400 flex-shrink-0" />
                            : <ChevronRight className="h-3.5 w-3.5 text-neutral-400 flex-shrink-0" />}
                          <span className="text-xs font-semibold text-neutral-700 flex-1 min-w-0 truncate">
                            {l1.ancestor ? `${l1.ancestor.code} — ${l1.ancestor.name}` : 'Requirements'}
                          </span>
                          <span className="text-[10px] text-neutral-400 tabular-nums flex-shrink-0 ml-1">
                            {l1ReqIds.length}
                          </span>
                        </button>
                      </div>

                      {/* L2 children — indented under function */}
                      {l1Open && (
                        <div className="ml-5 pl-3 border-l border-neutral-100 flex flex-col gap-0.5 mt-0.5 mb-1">
                          {l1.l2Groups.map(l2 => {
                            const l2Key = `${l1Key}::${l2.key}`;
                            const l2ReqIds = l2.scores.map(s => s.requirement_id);
                            const l2CheckedCount = l2ReqIds.filter(id => checkedReqIds.has(id)).length;
                            const l2AllChecked = l2ReqIds.length > 0 && l2CheckedCount === l2ReqIds.length;
                            const l2Indeterminate = l2CheckedCount > 0 && !l2AllChecked;
                            const l2Open = isOpen(l2Key);

                            if (!l2.ancestor) {
                              // No L2 grouping — render items directly
                              return (
                                <div key={l2.key} className="flex flex-col gap-1">
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
                              <div key={l2.key}>
                                {/* L2 — Category */}
                                <div className="flex items-center gap-2 py-0.5 rounded-md hover:bg-neutral-50 transition-colors">
                                  <GroupCheckbox checked={l2AllChecked} indeterminate={l2Indeterminate} onChange={() => onToggleGroup(l2ReqIds)} />
                                  <button onClick={() => toggle(l2Key)} className="flex items-center gap-1 flex-1 min-w-0 text-left">
                                    {l2Open
                                      ? <ChevronDown className="h-3 w-3 text-neutral-300 flex-shrink-0" />
                                      : <ChevronRight className="h-3 w-3 text-neutral-300 flex-shrink-0" />}
                                    <span className={cn(
                                      'text-[11px] font-medium flex-1 min-w-0 truncate',
                                      l2Open ? 'text-neutral-600' : 'text-neutral-400',
                                    )}>
                                      {l2.ancestor.code} — {l2.ancestor.name}
                                    </span>
                                    <span className="text-[10px] text-neutral-400 tabular-nums flex-shrink-0 ml-1">
                                      {l2ReqIds.length}
                                    </span>
                                  </button>
                                </div>

                                {/* Requirement items — indented under category */}
                                {l2Open && (
                                  <div className="ml-5 pl-3 border-l border-neutral-100 flex flex-col gap-1 mt-0.5 mb-1">
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
            )}
          </div>
        );
      })}
    </div>
  );
}
