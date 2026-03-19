'use client';

import { useState, useMemo, useEffect, useRef } from 'react';
import { ChevronDown, ChevronRight, Info } from 'lucide-react';
import { PolicyMapping, EvidenceSection } from '@/lib/types';
import { RequirementMappingGroup } from './RequirementMappingGroup';
import { cn } from '@/lib/utils';
import { apiRequest } from '@/lib/api/client';

const DEFAULT_THRESHOLD = 70;

// ─── Section tabs config ───────────────────────────────────────────────────────

const SECTION_TABS: { id: EvidenceSection; label: string }[] = [
  { id: 'policy',    label: 'Policies'   },
  { id: 'process',   label: 'Processes'  },
  { id: 'control',   label: 'Controls'   },
  { id: 'interview', label: 'Interviews' },
  { id: 'proof',     label: 'Proof'      },
];

/** Returns true if a mapping belongs to the given section (with legacy fallback). */
function matchesSection(m: PolicyMapping, section: EvidenceSection): boolean {
  if (m.policy_section) return m.policy_section === section;
  // Legacy docs with no section: 'policy' type → policy tab, 'evidence' type → proof tab
  if (section === 'policy') return m.policy_document_type === 'policy';
  if (section === 'proof')  return m.policy_document_type === 'evidence';
  return false;
}

// ─── Types ────────────────────────────────────────────────────────────────────

type Ancestor = { code: string; name: string | null; display_order?: number };

interface ReqGroupData {
  requirementCode: string;
  requirementName: string | null;
  requirementDescription: string | null;
  requirementGuidance: string | null;
  requirementParentCode: string | null;
  mappings: PolicyMapping[];
  ancestors: Ancestor[];
}

interface HierarchyNode {
  code: string;
  name: string | null;
  children: HierarchyNode[];
  directRequirements: ReqGroupData[];
}

interface FrameworkData {
  frameworkName: string;
  children: HierarchyNode[];
  directRequirements: ReqGroupData[];
}

// ─── Data helpers ─────────────────────────────────────────────────────────────

function computeScore(m: PolicyMapping): number {
  return m.relevance_percentage ?? (m.confidence_score != null ? (m.confidence_score + 1) / 2 * 100 : 0);
}

function flattenNodeReqs(nodes: HierarchyNode[]): ReqGroupData[] {
  return nodes.flatMap(n => [...n.directRequirements, ...flattenNodeReqs(n.children)]);
}

function groupByAncestor(requirements: ReqGroupData[], depth: number): HierarchyNode[] {
  const toGroup = requirements.filter(r => r.ancestors.length > depth);
  if (toGroup.length === 0) return [];

  const nodeMap = new Map<string, { ancestor: Ancestor; reqs: ReqGroupData[] }>();
  for (const req of toGroup) {
    const ancestor = req.ancestors[depth];
    if (!nodeMap.has(ancestor.code)) nodeMap.set(ancestor.code, { ancestor, reqs: [] });
    nodeMap.get(ancestor.code)!.reqs.push(req);
  }

  return [...nodeMap.values()]
    .sort((a, b) => {
      const orderA = a.ancestor.display_order ?? 0;
      const orderB = b.ancestor.display_order ?? 0;
      return orderA !== orderB ? orderA - orderB : a.ancestor.code.localeCompare(b.ancestor.code);
    })
    .map(({ ancestor, reqs }) => {
      const directRequirements = reqs.filter(r => r.ancestors.length === depth + 1);
      const deeperReqs = reqs.filter(r => r.ancestors.length > depth + 1);
      return {
        code: ancestor.code,
        name: ancestor.name,
        children: groupByAncestor(deeperReqs, depth + 1),
        directRequirements,
      };
    });
}

function buildGroups(mappings: PolicyMapping[]): FrameworkData[] {
  type ReqEntry = {
    name: string | null;
    description: string | null;
    guidance: string | null;
    parentCode: string | null;
    ancestors: Ancestor[];
    displayOrder: number;
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
        displayOrder: m.requirement_display_order ?? 0,
        mappings: [],
      });
    }
    reqMap.get(code)!.mappings.push(m);
  }

  const result: FrameworkData[] = [];
  for (const [fw, reqMap] of [...fwMap.entries()].sort(([a], [b]) => a.localeCompare(b))) {
    const requirements: ReqGroupData[] = [...reqMap.entries()]
      .sort(([codeA, a], [codeB, b]) => a.displayOrder - b.displayOrder || codeA.localeCompare(codeB))
      .map(([code, entry]) => ({
        requirementCode: code,
        requirementName: entry.name,
        requirementDescription: entry.description,
        requirementGuidance: entry.guidance,
        requirementParentCode: entry.parentCode,
        mappings: entry.mappings,
        ancestors: entry.ancestors,
      }));

    result.push({
      frameworkName: fw,
      directRequirements: requirements.filter(r => r.ancestors.length === 0),
      children: groupByAncestor(requirements.filter(r => r.ancestors.length > 0), 0),
    });
  }
  return result;
}

// ─── NodeSection (recursive) ──────────────────────────────────────────────────

interface NodeSectionProps {
  node: HierarchyNode;
  depth: number;
  collapseKey: string;
  collapsedNodes: Set<string>;
  onToggleNode: (key: string) => void;
  reqThresholds: Map<string, number>;
  activeSection: EvidenceSection;
  onThresholdChange: (code: string, threshold: number) => void;
  onReject: (mappingId: string) => Promise<void>;
  onUnreject: (mappingId: string) => Promise<void>;
}

function NodeSection({
  node, depth, collapseKey, collapsedNodes, onToggleNode,
  reqThresholds, activeSection, onThresholdChange, onReject, onUnreject,
}: NodeSectionProps) {
  const isCollapsed = collapsedNodes.has(collapseKey);
  const indentLeft = 24 + depth * 20;
  const contentIndentLeft = indentLeft + 20;

  return (
    <div>
      <button
        onClick={() => onToggleNode(collapseKey)}
        style={{ paddingLeft: `${indentLeft}px` }}
        className="w-full flex items-center gap-2.5 py-2 pr-4 text-left hover:bg-neutral-50 transition-colors"
      >
        {isCollapsed
          ? <ChevronRight className="h-3.5 w-3.5 text-neutral-400 flex-shrink-0" />
          : <ChevronDown className="h-3.5 w-3.5 text-neutral-400 flex-shrink-0" />}
        <span className={cn(
          'font-mono font-semibold px-2 py-0.5 rounded border flex-shrink-0 text-neutral-600 bg-neutral-100 border-neutral-200',
          depth === 0 ? 'text-sm' : 'text-xs'
        )}>
          {node.code}
        </span>
        {node.name && (
          <span className={cn('truncate text-neutral-600', depth === 0 ? 'text-sm' : 'text-xs')}>
            {node.name}
          </span>
        )}
      </button>

      {!isCollapsed && (
        <div>
          {node.children.map(child => (
            <NodeSection
              key={child.code}
              node={child}
              depth={depth + 1}
              collapseKey={`${collapseKey}||${child.code}`}
              collapsedNodes={collapsedNodes}
              onToggleNode={onToggleNode}
              reqThresholds={reqThresholds}
              activeSection={activeSection}
              onThresholdChange={onThresholdChange}
              onReject={onReject}
              onUnreject={onUnreject}
            />
          ))}
          {node.directRequirements.length > 0 && (
            <div style={{ paddingLeft: `${contentIndentLeft}px`, paddingRight: '16px' }} className="pb-3 pt-1 space-y-2">
              {node.directRequirements.map(req => (
                <RequirementMappingGroup
                  key={req.requirementCode}
                  requirementCode={req.requirementCode}
                  requirementName={req.requirementName}
                  requirementDescription={req.requirementDescription}
                  requirementGuidance={req.requirementGuidance}
                  requirementParentCode={req.requirementParentCode}
                  mappings={req.mappings}
                  defaultThreshold={reqThresholds.get(`${req.requirementCode}:${activeSection}`) ?? DEFAULT_THRESHOLD}
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
  onRejectPolicy: (mappingId: string) => Promise<void>;
  onUnrejectPolicy: (mappingId: string) => Promise<void>;
}

export function MappingsList({
  policyMappings,
  assessmentId,
  onRejectPolicy,
  onUnrejectPolicy,
}: MappingsListProps) {
  const [activeSection, setActiveSection] = useState<EvidenceSection>('policy');
  const [collapsedFw, setCollapsedFw] = useState<Set<string>>(new Set());
  const [collapsedNodes, setCollapsedNodes] = useState<Set<string>>(new Set());
  // Keys are "requirementCode:section"
  const [reqThresholds, setReqThresholds] = useState<Map<string, number>>(new Map());
  const reqDebounceRef = useRef<Map<string, ReturnType<typeof setTimeout>>>(new Map());

  const codeToRequirementId = useMemo(() => {
    const m = new Map<string, string>();
    for (const pm of policyMappings) {
      if (pm.requirement_code && pm.requirement_id) m.set(pm.requirement_code, pm.requirement_id);
    }
    return m;
  }, [policyMappings]);

  useEffect(() => {
    if (!assessmentId) return;
    apiRequest<Record<string, number>>(`/assessments/${assessmentId}/requirement-thresholds`)
      .then(data => {
        // Keys from API are "requirementId:section"; convert to "requirementCode:section"
        const idToCode = new Map<string, string>();
        for (const pm of policyMappings) {
          if (pm.requirement_id && pm.requirement_code) idToCode.set(pm.requirement_id, pm.requirement_code);
        }
        const codeKeyed = new Map<string, number>();
        for (const [key, threshold] of Object.entries(data)) {
          const colonIdx = key.lastIndexOf(':');
          const reqId = key.slice(0, colonIdx);
          const section = key.slice(colonIdx + 1);
          const code = idToCode.get(reqId);
          if (code) codeKeyed.set(`${code}:${section}`, threshold);
        }
        if (codeKeyed.size > 0) setReqThresholds(codeKeyed);
      })
      .catch(() => {});
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [assessmentId]);

  // Count mappings per section for the tab badges
  const sectionCounts = useMemo(() =>
    Object.fromEntries(SECTION_TABS.map(t => [t.id, policyMappings.filter(m => matchesSection(m, t.id)).length])),
    [policyMappings]
  );

  // Filter to active section, then build hierarchy
  const sectionMappings = useMemo(
    () => policyMappings.filter(m => matchesSection(m, activeSection)),
    [policyMappings, activeSection]
  );

  const frameworks = useMemo(() => buildGroups(sectionMappings), [sectionMappings]);

  const handleReqThresholdChange = (code: string, t: number) => {
    const key = `${code}:${activeSection}`;
    setReqThresholds(prev => new Map(prev).set(key, t));
    const existing = reqDebounceRef.current.get(key);
    if (existing) clearTimeout(existing);
    const timer = setTimeout(() => {
      const requirementId = codeToRequirementId.get(code);
      if (!requirementId) return;
      apiRequest(`/assessments/${assessmentId}/requirement-thresholds/${requirementId}`, {
        method: 'PUT',
        body: { threshold: t, section: activeSection },
      }).catch(() => {});
      reqDebounceRef.current.delete(key);
    }, 300);
    reqDebounceRef.current.set(key, timer);
  };

  const traversalStats = useMemo(() => {
    const uniqueReqs = new Set(sectionMappings.map(m => m.requirement_code).filter(Boolean)).size;
    const uniqueDocs = new Set(sectionMappings.map(m => m.policy_id)).size;
    const baseline = uniqueReqs * uniqueDocs;
    const relevant = sectionMappings.filter(m => {
      if (m.is_rejected) return false;
      const t = reqThresholds.get(`${m.requirement_code}:${activeSection}`) ?? DEFAULT_THRESHOLD;
      return computeScore(m) >= t;
    }).length;
    const reduction = baseline > 0 ? Math.round((1 - relevant / baseline) * 100) : 0;
    return { uniqueReqs, uniqueDocs, baseline, relevant, reduction };
  }, [sectionMappings, activeSection, reqThresholds]);

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
    setCollapsedNodes(new Set(frameworks.flatMap(fw => collectNodeKeys(fw.children, fw.frameworkName))));
  };

  const handleExpandAll = () => {
    setCollapsedFw(new Set());
    setCollapsedNodes(new Set());
  };

  if (policyMappings.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        No mappings generated yet. Click &quot;Suggest Mappings&quot; to score your documents against requirements.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Section tabs */}
      <div className="flex gap-1 p-1 bg-neutral-100 rounded-xl w-fit flex-wrap">
        {SECTION_TABS.map(tab => {
          const count = sectionCounts[tab.id] ?? 0;
          const isActive = activeSection === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => { setActiveSection(tab.id); setCollapsedFw(new Set()); setCollapsedNodes(new Set()); }}
              className={cn(
                'flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all',
                isActive ? 'bg-white text-neutral-900 shadow-sm' : 'text-neutral-500 hover:text-neutral-700'
              )}
            >
              {tab.label}
              <span className={cn(
                'px-1.5 py-0.5 rounded text-[10px] font-semibold',
                isActive ? 'bg-primary-100 text-primary-700' : 'bg-neutral-200 text-neutral-500'
              )}>
                {count}
              </span>
            </button>
          );
        })}
      </div>

      {/* Legend */}
      <div className="flex items-center gap-3 text-xs text-neutral-500 flex-wrap">
        <span className="font-medium text-neutral-600">Relevance score:</span>
        <span className="flex items-center gap-1"><span className="inline-block w-2 h-2 rounded-full bg-green-500" /> ≥80% high</span>
        <span className="flex items-center gap-1"><span className="inline-block w-2 h-2 rounded-full bg-amber-500" /> 60–79% moderate</span>
        <span className="flex items-center gap-1"><span className="inline-block w-2 h-2 rounded-full bg-red-400" /> &lt;60% low</span>
        <div className="relative group">
          <Info className="h-3.5 w-3.5 text-neutral-400 cursor-help" />
          <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 hidden group-hover:block z-20 w-72 px-3 py-2 bg-neutral-800 text-white text-xs rounded-lg shadow-xl leading-relaxed pointer-events-none">
            <p className="font-medium mb-1">How the relevance score is calculated</p>
            <p>Each document is split into ~300-token chunks. The score is the highest cosine similarity between any chunk and the requirement text, normalized to 0–100%.</p>
            <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-neutral-800" />
          </div>
        </div>
      </div>

      {/* Traversal reduction stats */}
      {sectionMappings.length > 0 && (
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
      )}

      {/* Empty state for this section */}
      {sectionMappings.length === 0 && (
        <div className="text-center py-8 text-neutral-400 text-sm">
          No mappings for this section yet.
        </div>
      )}

      {/* Collapse / expand all */}
      {frameworks.length > 0 && (
        <div className="flex justify-end gap-3 text-xs text-neutral-400">
          <button onClick={handleExpandAll} className="hover:text-neutral-600 transition-colors">Expand all</button>
          <span>·</span>
          <button onClick={handleCollapseAll} className="hover:text-neutral-600 transition-colors">Collapse all</button>
        </div>
      )}

      {/* Framework sections */}
      <div className="space-y-3">
        {frameworks.map(fw => {
          const isFwCollapsed = collapsedFw.has(fw.frameworkName);
          return (
            <div key={fw.frameworkName} className="rounded-xl border border-neutral-200 overflow-hidden shadow-sm">
              <button
                onClick={() => toggleFw(fw.frameworkName)}
                className="w-full flex items-center gap-3 px-4 py-3 text-left bg-neutral-50 hover:bg-neutral-100 transition-colors"
              >
                {isFwCollapsed
                  ? <ChevronRight className="h-4 w-4 text-neutral-400 flex-shrink-0" />
                  : <ChevronDown className="h-4 w-4 text-neutral-400 flex-shrink-0" />}
                <span className="text-sm font-semibold text-neutral-800 flex-1 text-left">
                  {fw.frameworkName}
                </span>
              </button>

              {!isFwCollapsed && (
                <div className="bg-white divide-y divide-neutral-100">
                  {fw.children.map(child => (
                    <NodeSection
                      key={child.code}
                      node={child}
                      depth={0}
                      collapseKey={`${fw.frameworkName}||${child.code}`}
                      collapsedNodes={collapsedNodes}
                      onToggleNode={toggleNode}
                      reqThresholds={reqThresholds}
                      activeSection={activeSection}
                      onThresholdChange={handleReqThresholdChange}
                      onReject={onRejectPolicy}
                      onUnreject={onUnrejectPolicy}
                    />
                  ))}
                  {fw.directRequirements.length > 0 && (
                    <div className="px-4 pb-4 pt-2 space-y-2">
                      {fw.directRequirements.map(req => (
                        <RequirementMappingGroup
                          key={req.requirementCode}
                          requirementCode={req.requirementCode}
                          requirementName={req.requirementName}
                          requirementDescription={req.requirementDescription}
                          requirementGuidance={req.requirementGuidance}
                          requirementParentCode={req.requirementParentCode}
                          mappings={req.mappings}
                          defaultThreshold={reqThresholds.get(`${req.requirementCode}:${activeSection}`) ?? DEFAULT_THRESHOLD}
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
