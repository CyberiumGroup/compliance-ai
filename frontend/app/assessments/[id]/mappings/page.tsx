'use client';

import { useState, useEffect, use } from 'react';
import { Link2, Sparkles, AlertTriangle, Search, Trash2 } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent, Button } from '@/components/ui';
import { LoadingSpinner, ErrorMessage } from '@/components/ui';
import { MappingsList, GapsList } from '@/components/mappings';
import {
  generateMappings,
  clearAllMappings,
  listControlMappings,
  listPolicyMappings,
  approveMapping,
  rejectMapping,
  getGaps,
} from '@/lib/api';
import { useUserId } from '@/lib/hooks/useUserId';
import { ControlMapping, PolicyMapping, GapListResponse } from '@/lib/types';
import { cn } from '@/lib/utils';

interface MappingsPageProps {
  params: Promise<{ id: string }>;
}

export default function MappingsPage({ params }: MappingsPageProps) {
  const { id } = use(params);
  const userId = useUserId();
  const [controlMappings, setControlMappings] = useState<ControlMapping[]>([]);
  const [policyMappings, setPolicyMappings] = useState<PolicyMapping[]>([]);
  const [gapData, setGapData] = useState<GapListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [clearing, setClearing] = useState(false);
  const [analyzingGaps, setAnalyzingGaps] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'mappings' | 'gaps'>('mappings');

  const fetchMappings = async () => {
    if (!userId) return;

    try {
      const [controls, policies, gaps] = await Promise.all([
        listControlMappings(id, userId).catch(() => []),
        listPolicyMappings(id, userId).catch(() => []),
        getGaps(id, userId).catch(() => null),
      ]);
      setControlMappings(controls);
      setPolicyMappings(policies);
      setGapData(gaps);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load mappings');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (userId) {
      fetchMappings();
    }
  }, [id, userId]);

  const handleGenerate = async () => {
    if (!userId) return;

    setGenerating(true);
    setError(null);

    try {
      await generateMappings(id, {}, userId);
      await fetchMappings();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to suggest mappings');
    } finally {
      setGenerating(false);
    }
  };

  const handleClearAll = async () => {
    if (!userId) return;

    if (!confirm(
      'Are you sure you want to clear ALL mappings? This will permanently delete all pending and approved mappings for this assessment. This action cannot be undone.'
    )) {
      return;
    }

    setClearing(true);
    setError(null);

    try {
      await clearAllMappings(id, userId);
      setControlMappings([]);
      setPolicyMappings([]);
      setGapData(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to clear mappings');
    } finally {
      setClearing(false);
    }
  };

  const handleAnalyzeGaps = async () => {
    if (!userId) return;

    setAnalyzingGaps(true);
    setError(null);

    try {
      const gaps = await getGaps(id, userId);
      setGapData(gaps);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to analyze coverage');
    } finally {
      setAnalyzingGaps(false);
    }
  };

  const handleApproveControl = async (mappingId: string, approved: boolean) => {
    if (!userId) return;

    if (approved) {
      await approveMapping(mappingId, userId);
      setControlMappings(
        controlMappings.map((m) =>
          m.id === mappingId ? { ...m, is_approved: true } : m
        )
      );
    } else {
      await rejectMapping(mappingId, userId);
      setControlMappings(controlMappings.filter((m) => m.id !== mappingId));
    }
  };

  const handleApprovePolicy = async (mappingId: string, approved: boolean) => {
    if (!userId) return;

    if (approved) {
      await approveMapping(mappingId, userId);
      setPolicyMappings(
        policyMappings.map((m) =>
          m.id === mappingId ? { ...m, is_approved: true } : m
        )
      );
    } else {
      await rejectMapping(mappingId, userId);
      setPolicyMappings(policyMappings.filter((m) => m.id !== mappingId));
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center py-12">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  const tabs = [
    {
      id: 'mappings',
      label: 'Mappings',
      icon: Link2,
      count: controlMappings.length + policyMappings.length,
    },
    {
      id: 'gaps',
      label: 'Coverage Gaps',
      icon: AlertTriangle,
      count: gapData?.total_gaps ?? null,
    },
  ];

  return (
    <div className="space-y-6 animate-fadeIn">
      <Card animated>
        <CardHeader variant="gradient">
          <CardTitle icon={<Sparkles className="h-5 w-5" />}>AI Mapping Suggestions</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="flex items-start gap-4 p-4 rounded-lg bg-primary-50/50 border border-primary-100">
              <div className="flex-1">
                <h4 className="text-sm font-semibold text-neutral-900">Suggest Mappings</h4>
                <p className="text-xs text-neutral-600 mt-1">
                  Use AI to analyze your controls and policies and suggest mappings to framework
                  requirements. Existing mappings (both pending and approved) will be preserved
                  — only new suggestions will be added.
                </p>
              </div>
              <Button
                variant="gradient"
                onClick={handleGenerate}
                loading={generating}
                className="flex-shrink-0"
                leftIcon={<Sparkles className="h-4 w-4" />}
              >
                Suggest Mappings
              </Button>
            </div>

            {(controlMappings.length + policyMappings.length > 0) && (
              <div className="flex items-start gap-4 p-4 rounded-lg bg-red-50/50 border border-red-100">
                <div className="flex-1">
                  <h4 className="text-sm font-semibold text-red-900">Clear All Mappings</h4>
                  <p className="text-xs text-red-700/70 mt-1">
                    Permanently delete all mappings for this assessment, including approved mappings.
                    This cannot be undone.
                  </p>
                </div>
                <Button
                  variant="ghost"
                  onClick={handleClearAll}
                  loading={clearing}
                  className="flex-shrink-0 text-red-600 hover:text-red-700 hover:bg-red-100"
                  leftIcon={<Trash2 className="h-4 w-4" />}
                >
                  Clear All
                </Button>
              </div>
            )}
          </div>
          {error && <ErrorMessage message={error} className="mt-4" />}
        </CardContent>
      </Card>

      {/* Custom Tab Navigation */}
      <div className="border-b border-neutral-200">
        <nav className="-mb-px flex space-x-4">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as 'mappings' | 'gaps')}
                className={cn(
                  'relative flex items-center gap-2 py-3 px-4 text-sm font-medium transition-all duration-200',
                  isActive
                    ? 'text-primary-600'
                    : 'text-neutral-500 hover:text-neutral-700'
                )}
              >
                <Icon className="h-4 w-4" />
                {tab.label}
                {tab.count !== null && (
                  <span className={cn(
                    'px-2 py-0.5 text-xs font-semibold rounded-full',
                    isActive
                      ? 'bg-gradient-to-r from-primary-500 to-primary-600 text-white'
                      : 'bg-neutral-100 text-neutral-600'
                  )}>
                    {tab.count}
                  </span>
                )}
                {isActive && (
                  <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-gradient-to-r from-primary-500 to-accent-500 rounded-full" />
                )}
              </button>
            );
          })}
        </nav>
      </div>

      {activeTab === 'mappings' ? (
        <Card animated>
          <CardContent>
            <MappingsList
              controlMappings={controlMappings}
              policyMappings={policyMappings}
              onApproveControl={handleApproveControl}
              onApprovePolicy={handleApprovePolicy}
            />
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          <Card animated>
            <CardContent>
              <div className="flex items-center justify-between">
                <p className="text-sm text-neutral-600">
                  Analyze which framework requirements are covered by your approved mappings
                  and identify gaps that need attention.
                </p>
                <Button
                  variant="gradient"
                  onClick={handleAnalyzeGaps}
                  loading={analyzingGaps}
                  leftIcon={<Search className="h-4 w-4" />}
                  className="flex-shrink-0 ml-4"
                >
                  {gapData ? 'Re-analyze' : 'Analyze Coverage'}
                </Button>
              </div>
            </CardContent>
          </Card>

          {analyzingGaps ? (
            <div className="flex justify-center py-12">
              <LoadingSpinner size="lg" />
            </div>
          ) : gapData ? (
            <Card animated>
              <CardContent>
                <GapsList gapData={gapData} assessmentId={id} />
              </CardContent>
            </Card>
          ) : (
            <Card>
              <CardContent>
                <div className="text-center py-8">
                  <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-gradient-to-br from-primary-50 to-accent-50 flex items-center justify-center">
                    <Search className="h-8 w-8 text-primary-400" />
                  </div>
                  <p className="text-neutral-500">
                    Click &quot;Analyze Coverage&quot; to check which requirements are covered by your approved mappings.
                  </p>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      )}
    </div>
  );
}
