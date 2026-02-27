'use client';

import { useState, useMemo, useEffect, useRef } from 'react';
import { ChevronDown, ChevronRight, AlertTriangle, CheckCircle2, Info, Save } from 'lucide-react';
import { PolicyMapping } from '@/lib/types';
import { RequirementMappingGroup } from './RequirementMappingGroup';
import { cn } from '@/lib/utils';
import { apiRequest } from '@/lib/api/client';

const DEFAULT_GLOBAL_THRESHOLD = 80;

// ─── Types ────────────────────────────────────────────────────────────────────

type Ancestor = { code: string; name: string | null };

interface ReqGroupData {
  requirementCode: string;
  requirementName: string | null;
  requirementDescription: string | null;
  requirementGuidance: string | null;
  requirementParentCode: string | null;
  mappings: PolicyMapping[];
  hasDocs: boolean;
  ancestors: Ancestor[];
}

interface HierarchyNode {
  code: string;
  name: string | null;
  children: HierarchyNode[];
  directRequirements: ReqGroupData[];
  docCount: number;
  missingCount: number;
}

interface FrameworkData {
  frameworkName: string;
  children: HierarchyNode[];         // requirements grouped by ancestor tree
  directRequirements: ReqGroupData[]; // requirements with no ancestors
  docCount: number;
  missingCount: number;
}

// ─── Data helpers ─────────────────────────────────────────────────────────────

function computeScore(m: PolicyMapping): number {
  return m.relevance_percentage ?? (m.confidence_score != null ? (m.confidence_score + 1) / 2 * 100 : 0);
}

function checkHasDocs(mappings: PolicyMapping[], threshold: number): boolean {
  return mappings.filter(m => !m.is_rejected).some(m => computeScore(m) >= threshold);
}

function flattenNodeReqs(nodes: HierarchyNode[]): ReqGroupData[] {
  return nodes.flatMap(n => [...n.directRequirements, ...flattenNodeReqs(n.children)]);
}

/** Recursively group requirements by ancestor at the given depth. */
function groupByAncestor(requirements: ReqGroupData[], depth: number): HierarchyNode[] {
  const toGroup = requirements.filter(r => r.ancestors.length > depth);
  if (toGroup.length === 0) return [];

  const nodeMap = new Map<string, { ancestor: Ancestor; reqs: ReqGroupData[] }>();
  for (const req of toGroup) {
    const ancestor = req.ancestors[depth];
    if (!nodeMap.has(ancestor.code)) nodeMap.set(ancestor.code, { ancestor, reqs: [] });
    nodeMap.get(ancestor.code)!.reqs.push(req);
  }

  return [...nodeMap.entries()]
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([, { ancestor, reqs }]) => {
      const directRequirements = reqs.filter(r => r.ancestors.length === depth + 1);
      const deeperReqs = reqs.filter(r => r.ancestors.length > depth + 1);
      const children = groupByAncestor(deeperReqs, depth + 1);

      const allInNode = [...directRequirements, ...flattenNodeReqs(children)];
      return {
        code: ancestor.code,
        name: ancestor.name,
        children,
        directRequirements,
        docCount: allInNode.filter(r => r.hasDocs).length,
        missingCount: allInNode.filter(r => !r.hasDocs).length,
      };
    });
}

function buildGroups(mappings: PolicyMapping[], threshold: number): FrameworkData[] {
  type ReqEntry = {
    name: string | null;
    description: string | null;
    guidance: string | null;
    parentCode: string | null;
    ancestors: Ancestor[];
    mappings: PolicyMapping[];
  };

  const fwMap = new Map<string, Map<string, ReqEntry>>();

  for (const m of mappings) {
    const fw = m.requirement_framework_name ?? 'Unknown Framework';
    const code = m.requirement_code ?? 'Unknown';

    if (!fwMap.has(fw)) fwMap.set(fw, new Map());
    const reqMap = fwMap.get(fw)!;

    if (!reqMap.has(code)) {
      reqMap.set(code, {
        name: m.requirement_name ?? null,
        description: m.requirement_description ?? null,
        guidance: m.requirement_guidance ?? null,
        parentCode: m.requirement_parent_code ?? null,
        ancestors: m.requirement_ancestors ?? [],
        mappings: [],
      });
    }
    reqMap.get(code)!.mappings.push(m);
  }

  const result: FrameworkData[] = [];

  for (const [fw, reqMap] of [...fwMap.entries()].sort(([a], [b]) => a.localeCompare(b))) {
    const requirements: ReqGroupData[] = [...reqMap.entries()]
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([code, entry]) => ({
        requirementCode: code,
        requirementName: entry.name,
        requirementDescription: entry.description,
        requirementGuidance: entry.guidance,
        requirementParentCode: entry.parentCode,
        mappings: entry.mappings,
        hasDocs: checkHasDocs(entry.mappings, threshold),
        ancestors: entry.ancestors,
      }));

    const directRequirements = requirements.filter(r => r.ancestors.length === 0);
    const children = groupByAncestor(requirements.filter(r => r.ancestors.length > 0), 0);
    const allReqs = [...directRequirements, ...flattenNodeReqs(children)];

    result.push({
      frameworkName: fw,
      children,
      directRequirements,
      docCount: allReqs.filter(r => r.hasDocs).length,
      missingCount: allReqs.filter(r => !r.hasDocs).length,
    });
  }

  return result;
}

// ─── DocBadges ────────────────────────────────────────────────────────────────

function DocBadges({ docCount, missingCount }: { docCount: number; missingCount: number }) {
  return (
    <div className="flex items-center gap-1.5 flex-shrink-0">
      {docCount > 0 && (
        <span className="flex items-center gap-1 text-xs font-medium text-green-700 bg-green-100 px-2 py-0.5 rounded-full">
          <CheckCircle2 className="h-3 w-3" />
          {docCount} documented
        </span>
      )}
      {missingCount > 0 && (
        <span className="flex items-center gap-1 text-xs font-semibold text-red-600 bg-red-50 ring-1 ring-red-300 px-2 py-0.5 rounded-full">
          <AlertTriangle className="h-3 w-3" />
          {missingCount} missing
        </span>
      )}
    </div>
  );
}

// ─── NodeSection (recursive) ──────────────────────────────────────────────────

interface NodeSectionProps {
  node: HierarchyNode;
  depth: number; // 0 = direct child of framework
  collapseKey: string;
  showMissingOnly: boolean;
  collapsedNodes: Set<string>;
  onToggleNode: (key: string) => void;
  defaultThreshold: number;
  onThresholdChange: (code: string, threshold: number) => void;
  onReject: (mappingId: string) => Promise<void>;
  onUnreject: (mappingId: string) => Promise<void>;
}

function NodeSection({
  node,
  depth,
  collapseKey,
  showMissingOnly,
  collapsedNodes,
  onToggleNode,
  defaultThreshold,
  onThresholdChange,
  onReject,
  onUnreject,
}: NodeSectionProps) {
  const isCollapsed = collapsedNodes.has(collapseKey);

  const visibleDirectReqs = showMissingOnly
    ? node.directRequirements.filter(r => !r.hasDocs)
    : node.directRequirements;
  const visibleChildren = showMissingOnly
    ? node.children.filter(c => c.missingCount > 0)
    : node.children;

  if (showMissingOnly && visibleDirectReqs.length === 0 && visibleChildren.length === 0) return null;

  // Indentation: 24px base + 20px per depth level
  const indentLeft = 24 + depth * 20;
  const contentIndentLeft = indentLeft + 20;

  // Style varies by depth
  const codeStyle = cn(
    'font-mono font-semibold px-2 py-0.5 rounded border flex-shrink-0',
    depth === 0 ? 'text-sm' : 'text-xs',
    node.missingCount > 0
      ? 'text-red-700 bg-red-50 border-red-200'
      : 'text-neutral-600 bg-neutral-100 border-neutral-200'
  );

  return (
    <div>
      {/* Node header */}
      <button
        onClick={() => onToggleNode(collapseKey)}
        style={{ paddingLeft: `${indentLeft}px` }}
        className={cn(
          'w-full flex items-center gap-2.5 py-2 pr-4 text-left transition-colors',
          node.missingCount > 0 ? 'hover:bg-red-50/40' : 'hover:bg-neutral-50'
        )}
      >
        {isCollapsed
          ? <ChevronRight className="h-3.5 w-3.5 text-neutral-400 flex-shrink-0" />
          : <ChevronDown className="h-3.5 w-3.5 text-neutral-400 flex-shrink-0" />}
        <span className={codeStyle}>{node.code}</span>
        {node.name && (
          <span className={cn(
            'truncate text-neutral-600',
            depth === 0 ? 'text-sm' : 'text-xs'
          )}>
            {node.name}
          </span>
        )}
        <div className="flex-1" />
        <DocBadges docCount={node.docCount} missingCount={node.missingCount} />
      </button>

      {/* Node body */}
      {!isCollapsed && (
        <div>
          {/* Child nodes */}
          {visibleChildren.map(child => (
            <NodeSection
              key={child.code}
              node={child}
              depth={depth + 1}
              collapseKey={`${collapseKey}||${child.code}`}
              showMissingOnly={showMissingOnly}
              collapsedNodes={collapsedNodes}
              onToggleNode={onToggleNode}
              defaultThreshold={defaultThreshold}
              onThresholdChange={onThresholdChange}
              onReject={onReject}
              onUnreject={onUnreject}
            />
          ))}

          {/* Direct requirements at this node */}
          {visibleDirectReqs.length > 0 && (
            <div
              style={{ paddingLeft: `${contentIndentLeft}px`, paddingRight: '16px' }}
              className="pb-3 pt-1 space-y-2"
            >
              {visibleDirectReqs.map(req => (
                <RequirementMappingGroup
                  key={req.requirementCode}
                  requirementCode={req.requirementCode}
                  requirementName={req.requirementName}
                  requirementDescription={req.requirementDescription}
                  requirementGuidance={req.requirementGuidance}
                  requirementParentCode={req.requirementParentCode}
                  mappings={req.mappings}
                  defaultThreshold={defaultThreshold}
                  onThresholdChange={(t) => onThresholdChange(req.requirementCode, t)}
                  onReject={onReject}
                  onUnreject={onUnreject}
                />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ─── MappingsList ─────────────────────────────────────────────────────────────

interface MappingsListProps {
  policyMappings: PolicyMapping[];
  assessmentId: string;
  initialThreshold?: number;
  onSaveThreshold: (threshold: number) => Promise<void>;
  onRejectPolicy: (mappingId: string) => Promise<void>;
  onUnrejectPolicy: (mappingId: string) => Promise<void>;
}

export function MappingsList({
  policyMappings,
  assessmentId,
  initialThreshold,
  onSaveThreshold,
  onRejectPolicy,
  onUnrejectPolicy,
}: MappingsListProps) {
  const [showMissingOnly, setShowMissingOnly] = useState(false);
  const [collapsedFw, setCollapsedFw] = useState<Set<string>>(new Set());
  const [collapsedNodes, setCollapsedNodes] = useState<Set<string>>(new Set());
  const [globalThreshold, setGlobalThreshold] = useState(initialThreshold ?? DEFAULT_GLOBAL_THRESHOLD);
  const [reqThresholds, setReqThresholds] = useState<Map<string, number>>(new Map());
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const savedTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const reqDebounceRef = useRef<Map<string, ReturnType<typeof setTimeout>>>(new Map());

  // Build code -> requirement_id lookup from policyMappings
  const codeToRequirementId = useMemo(() => {
    const m = new Map<string, string>();
    for (const pm of policyMappings) {
      if (pm.requirement_code && pm.requirement_id) {
        m.set(pm.requirement_code, pm.requirement_id);
      }
    }
    return m;
  }, [policyMappings]);

  // On mount: fetch persisted per-requirement thresholds and convert to code-keyed map
  useEffect(() => {
    if (!assessmentId) return;
    apiRequest<Record<string, number>>(`/assessments/${assessmentId}/requirement-thresholds`)
      .then(data => {
        const idToCode = new Map<string, string>();
        for (const pm of policyMappings) {
          if (pm.requirement_id && pm.requirement_code) {
            idToCode.set(pm.requirement_id, pm.requirement_code);
          }
        }
        const codeKeyed = new Map<string, number>();
        for (const [reqId, threshold] of Object.entries(data)) {
          const code = idToCode.get(reqId);
          if (code) codeKeyed.set(code, threshold);
        }
        if (codeKeyed.size > 0) setReqThresholds(codeKeyed);
      })
      .catch(() => {/* ignore — thresholds not persisted yet */});
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [assessmentId]);

  // Sync if the saved threshold loads after initial render
  useEffect(() => {
    if (initialThreshold != null) {
      setGlobalThreshold(initialThreshold);
    }
  }, [initialThreshold]);

  const frameworks = useMemo(
    () => buildGroups(policyMappings, globalThreshold),
    [policyMappings, globalThreshold]
  );
  const totalMissing = frameworks.reduce((s, fw) => s + fw.missingCount, 0);

  const handleReqThresholdChange = (code: string, t: number) => {
    setReqThresholds(prev => new Map(prev).set(code, t));

    // Debounce-save to backend (300ms)
    const existing = reqDebounceRef.current.get(code);
    if (existing) clearTimeout(existing);
    const timer = setTimeout(() => {
      const requirementId = codeToRequirementId.get(code);
      if (!requirementId) return;
      apiRequest(`/assessments/${assessmentId}/requirement-thresholds/${requirementId}`, {
        method: 'PUT',
        body: { threshold: t },
      }).catch(() => {/* ignore save errors silently */});
      reqDebounceRef.current.delete(code);
    }, 300);
    reqDebounceRef.current.set(code, timer);
  };

  const traversalStats = useMemo(() => {
    const uniqueReqs = new Set(policyMappings.map(m => m.requirement_code).filter(Boolean)).size;
    const uniqueDocs = new Set(policyMappings.map(m => m.policy_id)).size;
    const baseline = uniqueReqs * uniqueDocs;
    const relevant = policyMappings.filter(m => {
      if (m.is_rejected) return false;
      const t = reqThresholds.get(m.requirement_code ?? '') ?? globalThreshold;
      return computeScore(m) >= t;
    }).length;
    const reduction = baseline > 0 ? Math.round((1 - relevant / baseline) * 100) : 0;
    return { uniqueReqs, uniqueDocs, baseline, relevant, reduction };
  }, [policyMappings, globalThreshold, reqThresholds]);

  const handleSave = async () => {
    setSaving(true);
    setSaved(false);
    try {
      await onSaveThreshold(globalThreshold);
      setSaved(true);
      if (savedTimerRef.current) clearTimeout(savedTimerRef.current);
      savedTimerRef.current = setTimeout(() => setSaved(false), 2500);
    } finally {
      setSaving(false);
    }
  };

  if (policyMappings.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        No mappings generated yet. Click &quot;Suggest Mappings&quot; to score your policies against requirements.
      </div>
    );
  }

  const toggleFw = (name: string) =>
    setCollapsedFw(prev => { const s = new Set(prev); s.has(name) ? s.delete(name) : s.add(name); return s; });

  const toggleNode = (key: string) =>
    setCollapsedNodes(prev => { const s = new Set(prev); s.has(key) ? s.delete(key) : s.add(key); return s; });

  const collectNodeKeys = (nodes: HierarchyNode[], prefix: string): string[] =>
    nodes.flatMap(n => {
      const key = `${prefix}||${n.code}`;
      return [key, ...collectNodeKeys(n.children, key)];
    });

  const handleCollapseAll = () => {
    setCollapsedFw(new Set(frameworks.map(fw => fw.frameworkName)));
    setCollapsedNodes(new Set(
      frameworks.flatMap(fw => collectNodeKeys(fw.children, fw.frameworkName))
    ));
  };

  const handleExpandAll = () => {
    setCollapsedFw(new Set());
    setCollapsedNodes(new Set());
  };

  return (
    <div className="space-y-4">
      {/* Controls: row 1 — legend + filter */}
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div className="flex items-center gap-3 text-xs text-neutral-500 flex-wrap">
          <span className="font-medium text-neutral-600">Relevance score:</span>
          <span className="flex items-center gap-1"><span className="inline-block w-2 h-2 rounded-full bg-green-500" /> ≥80% high</span>
          <span className="flex items-center gap-1"><span className="inline-block w-2 h-2 rounded-full bg-amber-500" /> 60–79% moderate</span>
          <span className="flex items-center gap-1"><span className="inline-block w-2 h-2 rounded-full bg-red-400" /> &lt;60% low</span>
          <div className="relative group">
            <Info className="h-3.5 w-3.5 text-neutral-400 cursor-help" />
            <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 hidden group-hover:block z-20 w-72 px-3 py-2 bg-neutral-800 text-white text-xs rounded-lg shadow-xl leading-relaxed pointer-events-none">
              <p className="font-medium mb-1">How the relevance score is calculated</p>
              <p>Each policy document is split into ~300-token chunks. The score is the highest cosine similarity between any chunk and the requirement text, normalized from 0–100%.</p>
              <p className="mt-1 text-neutral-300">A high score means at least one section of the policy closely matches the language and intent of the requirement. It does not guarantee coverage, only suggests how relevant the document might be to an assessment.</p>
              <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-neutral-800" />
            </div>
          </div>
        </div>

        <button
          onClick={() => setShowMissingOnly(v => !v)}
          className={cn(
            'flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-all border',
            showMissingOnly
              ? 'bg-red-50 text-red-700 border-red-300 ring-1 ring-red-200'
              : 'text-neutral-600 border-neutral-200 hover:bg-neutral-50'
          )}
        >
          <AlertTriangle className="h-3.5 w-3.5" />
          Missing documentation only
          {totalMissing > 0 && (
            <span className={cn(
              'px-1.5 py-0.5 text-xs font-semibold rounded-full',
              showMissingOnly ? 'bg-red-200 text-red-800' : 'bg-neutral-100 text-neutral-600'
            )}>
              {totalMissing}
            </span>
          )}
        </button>
      </div>

      {/* Controls: row 2 — default threshold (own row so the slider never shifts) */}
      <div className="flex items-center gap-2 text-xs text-neutral-600">
        <span className="whitespace-nowrap font-medium">Default threshold</span>
        <input
          type="range"
          min={0}
          max={100}
          step={1}
          value={globalThreshold}
          onChange={e => { setGlobalThreshold(Number(e.target.value)); setSaved(false); setReqThresholds(new Map()); }}
          className="w-32 accent-primary-500 cursor-pointer"
        />
        <span className="w-8 text-right tabular-nums font-semibold">{globalThreshold}%</span>
        <button
          onClick={handleSave}
          disabled={saving || saved}
          className={cn(
            'flex items-center gap-1 px-2.5 py-1 rounded-md border text-xs font-medium transition-all',
            saved
              ? 'border-green-300 bg-green-50 text-green-700'
              : 'border-neutral-200 text-neutral-600 hover:bg-neutral-50 hover:border-neutral-300',
            (saving || saved) && 'cursor-default'
          )}
        >
          {saved ? (
            <><CheckCircle2 className="h-3 w-3" />Saved</>
          ) : (
            <><Save className="h-3 w-3" />{saving ? 'Saving…' : 'Save default threshold'}</>
          )}
        </button>
        {globalThreshold !== (initialThreshold ?? DEFAULT_GLOBAL_THRESHOLD) && (
          <button
            onClick={() => { setGlobalThreshold(initialThreshold ?? DEFAULT_GLOBAL_THRESHOLD); setSaved(false); setReqThresholds(new Map()); }}
            className="text-neutral-400 hover:text-neutral-600 transition-colors"
          >
            Reset
          </button>
        )}
      </div>

      {/* Traversal reduction stats */}
      <div className="flex items-center gap-6 px-4 py-3 rounded-lg bg-primary-50/60 border border-primary-100">
        <div className="flex items-baseline gap-1.5">
          <span className="text-3xl font-bold text-primary-700 tabular-nums">{traversalStats.reduction}%</span>
          <span className="text-sm font-medium text-primary-600">reduction in document review</span>
        </div>
        <div className="h-8 w-px bg-primary-200" />
        <div className="text-xs text-neutral-600 space-y-0.5">
          <p>
            <span className="font-semibold text-neutral-800">{traversalStats.relevant}</span> relevant pairs at current thresholds
            {' '}vs <span className="font-semibold text-neutral-800">{traversalStats.baseline}</span> baseline
          </p>
          <p className="text-neutral-400">
            {traversalStats.uniqueReqs} requirements × {traversalStats.uniqueDocs} documents
          </p>
        </div>
      </div>

      {/* Collapse / expand all */}
      <div className="flex justify-end gap-3 text-xs text-neutral-400">
        <button onClick={handleExpandAll} className="hover:text-neutral-600 transition-colors">Expand all</button>
        <span>·</span>
        <button onClick={handleCollapseAll} className="hover:text-neutral-600 transition-colors">Collapse all</button>
      </div>

      {/* Framework sections */}
      <div className="space-y-3">
        {frameworks.map(fw => {
          const isFwCollapsed = collapsedFw.has(fw.frameworkName);

          // For missing-only filter: determine visible content
          const visibleDirectReqs = showMissingOnly
            ? fw.directRequirements.filter(r => !r.hasDocs)
            : fw.directRequirements;
          const visibleChildren = showMissingOnly
            ? fw.children.filter(c => c.missingCount > 0)
            : fw.children;

          if (showMissingOnly && visibleDirectReqs.length === 0 && visibleChildren.length === 0) return null;

          return (
            <div
              key={fw.frameworkName}
              className={cn(
                'rounded-xl border overflow-hidden shadow-sm',
                fw.missingCount > 0 && fw.docCount === 0 ? 'border-red-200' : 'border-neutral-200'
              )}
            >
              {/* Framework header */}
              <button
                onClick={() => toggleFw(fw.frameworkName)}
                className={cn(
                  'w-full flex items-center gap-3 px-4 py-3 text-left transition-colors',
                  fw.missingCount > 0 && fw.docCount === 0
                    ? 'bg-red-50/60 hover:bg-red-50'
                    : 'bg-neutral-50 hover:bg-neutral-100'
                )}
              >
                {isFwCollapsed
                  ? <ChevronRight className="h-4 w-4 text-neutral-400 flex-shrink-0" />
                  : <ChevronDown className="h-4 w-4 text-neutral-400 flex-shrink-0" />}
                <span className="text-sm font-semibold text-neutral-800 flex-1 text-left">
                  {fw.frameworkName}
                </span>
                <DocBadges docCount={fw.docCount} missingCount={fw.missingCount} />
              </button>

              {/* Framework body */}
              {!isFwCollapsed && (
                <div className="bg-white divide-y divide-neutral-100">
                  {/* Hierarchy nodes */}
                  {visibleChildren.map(child => (
                    <NodeSection
                      key={child.code}
                      node={child}
                      depth={0}
                      collapseKey={`${fw.frameworkName}||${child.code}`}
                      showMissingOnly={showMissingOnly}
                      collapsedNodes={collapsedNodes}
                      onToggleNode={toggleNode}
                      defaultThreshold={globalThreshold}
                      onThresholdChange={handleReqThresholdChange}
                      onReject={onRejectPolicy}
                      onUnreject={onUnrejectPolicy}
                    />
                  ))}

                  {/* Requirements with no ancestors (flat structure) */}
                  {visibleDirectReqs.length > 0 && (
                    <div className="px-4 pb-4 pt-2 space-y-2">
                      {visibleDirectReqs.map(req => (
                        <RequirementMappingGroup
                          key={req.requirementCode}
                          requirementCode={req.requirementCode}
                          requirementName={req.requirementName}
                          requirementDescription={req.requirementDescription}
                          requirementGuidance={req.requirementGuidance}
                          requirementParentCode={req.requirementParentCode}
                          mappings={req.mappings}
                          defaultThreshold={globalThreshold}
                          onThresholdChange={(t) => handleReqThresholdChange(req.requirementCode, t)}
                          onReject={onRejectPolicy}
                          onUnreject={onUnrejectPolicy}
                        />
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
