'use client';

import { useState, useEffect, use } from 'react';
import { Layers, Plus, Trash2, ChevronDown, ChevronUp } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui';
import { LoadingPage, ErrorMessage } from '@/components/ui';
import { Button } from '@/components/ui/Button';
import {
  listFrameworks,
  getAssessmentScope,
  setAssessmentScope,
  removeAssessmentScope,
} from '@/lib/api';
import { Framework, AssessmentScope } from '@/lib/types';
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

interface ScopePageProps {
  params: Promise<{ id: string }>;
}

export default function AssessmentScopePage({ params }: ScopePageProps) {
  const { id: assessmentId } = use(params);
  const [allFrameworks, setAllFrameworks] = useState<Framework[]>([]);
  const [scopes, setScopes] = useState<AssessmentScope[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [adding, setAdding] = useState(false);
  const [selectedFrameworkId, setSelectedFrameworkId] = useState<string>('');
  const [expandedFramework, setExpandedFramework] = useState<string | null>(null);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [frameworksData, scopeData] = await Promise.all([
        listFrameworks(),
        getAssessmentScope(assessmentId),
      ]);
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
      // Silent refresh — don't show error for background updates
    }
  };

  useEffect(() => {
    fetchData();
  }, [assessmentId]);

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
    if (!confirm('Are you sure you want to remove this framework from the assessment scope?')) {
      return;
    }

    try {
      await removeAssessmentScope(assessmentId, frameworkId);
      await fetchData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to remove framework');
    }
  };

  // Get frameworks not yet in scope
  const availableFrameworks = allFrameworks.filter(
    (f) => !scopes.some((s) => s.framework_id === f.id)
  );

  // Get full framework details for scoped frameworks
  const scopedFrameworksWithDetails = scopes.map((s) => ({
    ...s,
    framework: allFrameworks.find((f) => f.id === s.framework_id),
  }));

  if (loading) {
    return <LoadingPage message="Loading assessment scope..." />;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-neutral-900 flex items-center gap-2">
            <Layers className="w-6 h-6 text-primary-500" />
            Framework Scope
          </h1>
          <p className="text-neutral-500 mt-1">
            Configure which compliance frameworks are included in this assessment
          </p>
        </div>
      </div>

      {error && (
        <div className="mb-6">
          <ErrorMessage message={error} />
        </div>
      )}

      {/* Add Framework */}
      <Card>
        <CardHeader>
          <CardTitle>Add Framework to Scope</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex gap-4">
            <div className="flex-1">
              <select
                value={selectedFrameworkId}
                onChange={(e) => setSelectedFrameworkId(e.target.value)}
                className="w-full px-3 py-2 border border-neutral-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                disabled={availableFrameworks.length === 0}
              >
                <option value="">
                  {availableFrameworks.length === 0
                    ? 'All frameworks already in scope'
                    : 'Select a framework to add...'}
                </option>
                {availableFrameworks.map((f) => (
                  <option key={f.id} value={f.id}>
                    {f.name} ({frameworkTypeLabels[f.framework_type] || 'Custom'})
                  </option>
                ))}
              </select>
            </div>
            <Button onClick={handleAddFramework} disabled={adding || !selectedFrameworkId}>
              <Plus className="w-4 h-4 mr-2" />
              {adding ? 'Adding...' : 'Add to Scope'}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Frameworks in Scope */}
      <Card>
        <CardHeader>
          <CardTitle>Frameworks in Scope ({scopes.length})</CardTitle>
        </CardHeader>
        <CardContent>
          {scopes.length === 0 ? (
            <p className="text-center text-neutral-500 py-8">
              No frameworks in scope. Add frameworks above to define the assessment coverage.
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
                    className="bg-white rounded-lg border border-neutral-200 hover:border-neutral-300 transition-all animate-slideInUp opacity-0"
                    style={{
                      animationDelay: `${index * 50}ms`,
                      animationFillMode: 'forwards',
                    }}
                  >
                    <div className="flex items-center justify-between p-4">
                      <div className="flex items-center gap-4">
                        {scope.framework && (
                          <span
                            className={cn(
                              'px-3 py-1.5 text-white text-xs font-semibold rounded-full bg-gradient-to-r',
                              frameworkTypeColors[scope.framework.framework_type] ||
                                frameworkTypeColors.custom
                            )}
                          >
                            {frameworkTypeLabels[scope.framework.framework_type] || 'Custom'}
                          </span>
                        )}
                        <div>
                          <h3 className="font-medium text-neutral-900">
                            {scope.framework_code || scope.framework?.name || 'Unknown Framework'}
                          </h3>
                          <p className="text-sm text-neutral-500">
                            {scope.include_all
                              ? 'All requirements included'
                              : 'Custom requirement selection'}
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <span
                          className={cn(
                            'px-2 py-1 text-xs rounded',
                            scope.include_all
                              ? 'bg-green-100 text-green-700'
                              : 'bg-yellow-100 text-yellow-700'
                          )}
                        >
                          {scope.include_all ? 'Full Scope' : 'Partial'}
                        </span>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => setExpandedFramework(isExpanded ? null : scope.framework_id)}
                        >
                          {isExpanded ? (
                            <ChevronUp className="w-4 h-4 text-neutral-400" />
                          ) : (
                            <ChevronDown className="w-4 h-4 text-neutral-400" />
                          )}
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleRemoveFramework(scope.framework_id)}
                        >
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

      {/* Info */}
      <Card className="bg-blue-50 border-blue-200">
        <CardContent className="pt-6">
          <h3 className="font-medium text-blue-900 mb-2">About Assessment Scope</h3>
          <ul className="text-sm text-blue-700 space-y-1">
            <li>- Frameworks in scope determine which requirements will be assessed</li>
            <li>- AI-powered clustering groups similar requirements to reduce interview burden</li>
            <li>- Scores and deviations are tracked per-framework for detailed reporting</li>
            <li>- You can modify the scope at any time during the assessment</li>
          </ul>
        </CardContent>
      </Card>
    </div>
  );
}
