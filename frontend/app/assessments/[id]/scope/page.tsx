'use client';

import { useState, useEffect, use } from 'react';
import { CheckCircle2, Layers, Plus, RotateCcw, Save, SlidersHorizontal, Trash2, ChevronDown, ChevronUp } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui';
import { LoadingSpinner, ErrorMessage } from '@/components/ui';
import { Button } from '@/components/ui/Button';
import {
  listFrameworks,
  getAssessment,
  updateAssessment,
  getAssessmentScope,
  setAssessmentScope,
  removeAssessmentScope,
} from '@/lib/api';
import { Framework, AssessmentScope, Assessment, AssessmentDepth } from '@/lib/types';
import { RequirementScopeSelector } from '@/components/assessment/RequirementScopeSelector';
import { cn } from '@/lib/utils';

const frameworkTypeColors: Record<string, string> = {
  nist_csf: 'from-blue-500 to-blue-600',
  iso_27001: 'from-green-500 to-green-600',
  soc2_tsc: 'from-purple-500 to-purple-600',
  custom: 'from-orange-500 to-orange-600',
};

const frameworkTypeLabels: Record<string, string> = {
  nist_csf: 'NIST CSF',
  iso_27001: 'ISO 27001',
  soc2_tsc: 'SOC 2',
  custom: 'Custom',
};

const DEPTH_OPTIONS: { value: AssessmentDepth; label: string; description: string }[] = [
  {
    value: 'design',
    label: 'Design',
    description: 'Controls are designed and documented to meet each requirement',
  },
  {
    value: 'implementation',
    label: 'Implementation',
    description: 'Controls are designed and actively deployed in practice',
  },
  {
    value: 'operating_effectiveness',
    label: 'Operating Effectiveness',
    description: 'Implemented controls are consistently operating as intended over time',
  },
];

interface ScopePageProps {
  params: Promise<{ id: string }>;
}

export default function AssessmentScopePage({ params }: ScopePageProps) {
  const { id: assessmentId } = use(params);
  const [assessment, setAssessment] = useState<Assessment | null>(null);
  const [allFrameworks, setAllFrameworks] = useState<Framework[]>([]);
  const [scopes, setScopes] = useState<AssessmentScope[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [adding, setAdding] = useState(false);
  const [selectedFrameworkId, setSelectedFrameworkId] = useState<string>('');
  const [expandedFramework, setExpandedFramework] = useState<string | null>(null);
  const [localDepth, setLocalDepth] = useState<AssessmentDepth>('design');
  const [savingDepth, setSavingDepth] = useState(false);
  const [depthSaved, setDepthSaved] = useState(false);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [assessmentData, frameworksData, scopeData] = await Promise.all([
        getAssessment(assessmentId),
        listFrameworks(),
        getAssessmentScope(assessmentId),
      ]);
      setAssessment(assessmentData);
      setLocalDepth(assessmentData.depth_level ?? 'design');
      setAllFrameworks(frameworksData);
      setScopes(scopeData);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load data');
    } finally {
      setLoading(false);
    }
  };

  const refreshScopes = async () => {
    try {
      const scopeData = await getAssessmentScope(assessmentId);
      setScopes(scopeData);
    } catch {
      // Silent refresh
    }
  };

  useEffect(() => {
    fetchData();
  }, [assessmentId]);

  const handleDepthSelect = (depth: AssessmentDepth) => {
    setLocalDepth(depth);
    setDepthSaved(false);
  };

  const handleSaveDepth = async () => {
    if (!assessment) return;
    setSavingDepth(true);
    setDepthSaved(false);
    try {
      const updated = await updateAssessment(assessmentId, { depth_level: localDepth });
      setAssessment(updated);
      setDepthSaved(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save depth level');
    } finally {
      setSavingDepth(false);
    }
  };

  const handleResetDepth = () => {
    setLocalDepth(assessment?.depth_level ?? 'design');
    setDepthSaved(false);
  };

  const handleAddFramework = async () => {
    if (!selectedFrameworkId) return;
    try {
      setAdding(true);
      await setAssessmentScope(assessmentId, {
        framework_id: selectedFrameworkId,
        include_all: true,
      });
      setSelectedFrameworkId('');
      await fetchData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to add framework');
    } finally {
      setAdding(false);
    }
  };

  const handleRemoveFramework = async (frameworkId: string) => {
    if (!confirm('Are you sure you want to remove this framework from the assessment scope?')) return;
    try {
      await removeAssessmentScope(assessmentId, frameworkId);
      await fetchData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to remove framework');
    }
  };

  const availableFrameworks = allFrameworks.filter(
    (f) => !scopes.some((s) => s.framework_id === f.id)
  );

  const scopedFrameworksWithDetails = scopes.map((s) => ({
    ...s,
    framework: allFrameworks.find((f) => f.id === s.framework_id),
  }));

  if (loading) {
    return (
      <div className="flex justify-center py-12">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  const depthIsDirty = localDepth !== (assessment?.depth_level ?? 'design');

  return (
    <div className="space-y-6 animate-fadeIn">
      {error && <ErrorMessage message={error} />}

      {/* ── Frameworks ── */}
      <Card animated>
        <CardHeader variant="gradient">
          <CardTitle icon={<Layers className="h-5 w-5" />}>Frameworks</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-neutral-500 mb-6">
            Select the compliance frameworks that are in scope for this assessment. You can include
            all requirements or customise the selection per framework.
          </p>

          {/* Add framework row */}
          <div className="flex gap-3 mb-6">
            <select
              value={selectedFrameworkId}
              onChange={(e) => setSelectedFrameworkId(e.target.value)}
              className="flex-1 px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:ring-2 focus:ring-primary-100 focus:border-primary-400 focus:outline-none transition-colors"
              disabled={availableFrameworks.length === 0}
            >
              <option value="">
                {availableFrameworks.length === 0
                  ? 'All frameworks already in scope'
                  : 'Select a framework to add…'}
              </option>
              {availableFrameworks.map((f) => (
                <option key={f.id} value={f.id}>
                  {f.name} ({frameworkTypeLabels[f.framework_type] || 'Custom'})
                </option>
              ))}
            </select>
            <Button onClick={handleAddFramework} disabled={adding || !selectedFrameworkId} variant="gradient">
              <Plus className="w-4 h-4 mr-2" />
              {adding ? 'Adding…' : 'Add to Scope'}
            </Button>
          </div>

          {/* Frameworks in scope list */}
          {scopes.length === 0 ? (
            <p className="text-sm text-neutral-400 text-center py-6">
              No frameworks in scope. Add a framework above to get started.
            </p>
          ) : (
            <div className="space-y-3">
              {scopedFrameworksWithDetails.map((scope, index) => {
                const isExpanded = expandedFramework === scope.framework_id;
                const hierarchyLabel = scope.framework?.hierarchy_labels?.[0]
                  ? `${scope.framework.hierarchy_labels[0]}s`
                  : 'Categories';

                return (
                  <div
                    key={scope.id}
                    className="rounded-lg border border-neutral-200 hover:border-neutral-300 transition-all animate-slideInUp opacity-0"
                    style={{ animationDelay: `${index * 50}ms`, animationFillMode: 'forwards' }}
                  >
                    <div className="flex items-center justify-between p-4">
                      <div className="flex items-center gap-3">
                        {scope.framework && (
                          <span className={cn(
                            'px-3 py-1.5 text-white text-xs font-semibold rounded-full bg-gradient-to-r',
                            frameworkTypeColors[scope.framework.framework_type] || frameworkTypeColors.custom
                          )}>
                            {frameworkTypeLabels[scope.framework.framework_type] || 'Custom'}
                          </span>
                        )}
                        <div>
                          <p className="text-sm font-medium text-neutral-900">
                            {scope.framework_code || scope.framework?.name || 'Unknown Framework'}
                          </p>
                          <p className="text-xs text-neutral-500 mt-0.5">
                            {scope.include_all ? 'All requirements included' : 'Custom requirement selection'}
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className={cn(
                          'px-2 py-0.5 text-xs rounded-full font-medium',
                          scope.include_all ? 'bg-green-100 text-green-700' : 'bg-amber-100 text-amber-700'
                        )}>
                          {scope.include_all ? 'Full Scope' : 'Partial'}
                        </span>
                        <Button variant="ghost" size="sm" onClick={() => setExpandedFramework(isExpanded ? null : scope.framework_id)}>
                          {isExpanded
                            ? <ChevronUp className="w-4 h-4 text-neutral-400" />
                            : <ChevronDown className="w-4 h-4 text-neutral-400" />}
                        </Button>
                        <Button variant="ghost" size="sm" onClick={() => handleRemoveFramework(scope.framework_id)}>
                          <Trash2 className="w-4 h-4 text-neutral-400 hover:text-red-500" />
                        </Button>
                      </div>
                    </div>
                    {isExpanded && scope.framework && (
                      <div className="border-t border-neutral-100 pb-4">
                        <RequirementScopeSelector
                          frameworkId={scope.framework_id}
                          assessmentId={assessmentId}
                          frameworkType={scope.framework.framework_type}
                          hierarchyLabel={hierarchyLabel}
                          currentScope={scope}
                          onScopeChange={refreshScopes}
                        />
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>

      {/* ── Assessment Depth ── */}
      <Card animated>
        <CardHeader variant="gradient">
          <CardTitle icon={<SlidersHorizontal className="h-5 w-5" />}>Assessment Depth</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-neutral-500 mb-6">
            Depth determines what the scoring evaluates — choose the level that reflects your
            assessment goals. This affects the status vocabulary used during requirement scoring.
          </p>
          <div className="grid grid-cols-3 gap-3">
            {DEPTH_OPTIONS.map((opt) => {
              const isSelected = localDepth === opt.value;
              return (
                <button
                  key={opt.value}
                  onClick={() => handleDepthSelect(opt.value)}
                  disabled={savingDepth}
                  className={cn(
                    'text-left p-4 rounded-lg border-2 transition-all',
                    isSelected
                      ? 'border-primary-500 bg-primary-50'
                      : 'border-neutral-200 bg-white hover:border-neutral-300 hover:bg-neutral-50',
                    savingDepth && 'opacity-60 cursor-not-allowed',
                  )}
                >
                  <div className={cn(
                    'text-sm font-semibold mb-1.5',
                    isSelected ? 'text-primary-700' : 'text-neutral-800',
                  )}>
                    {opt.label}
                  </div>
                  <div className="text-xs text-neutral-500 leading-snug">
                    {opt.description}
                  </div>
                </button>
              );
            })}
          </div>

          <div className="mt-6 flex items-center gap-3">
            <Button
              variant="gradient"
              onClick={handleSaveDepth}
              loading={savingDepth}
              disabled={savingDepth || (!depthIsDirty && !depthSaved)}
              leftIcon={depthSaved && !depthIsDirty ? <CheckCircle2 className="h-4 w-4" /> : <Save className="h-4 w-4" />}
            >
              {depthSaved && !depthIsDirty ? 'Saved' : 'Save'}
            </Button>
            {depthIsDirty && (
              <Button variant="ghost" onClick={handleResetDepth} leftIcon={<RotateCcw className="h-4 w-4" />}>
                Reset
              </Button>
            )}
            {depthSaved && !depthIsDirty && (
              <span className="text-sm text-green-600">Depth saved successfully.</span>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
