'use client';

import { useState, useEffect, use } from 'react';
import { Link2, Sparkles, AlertTriangle } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent, Button } from '@/components/ui';
import { LoadingSpinner, ErrorMessage } from '@/components/ui';
import { MappingsList, GapsList } from '@/components/mappings';
import {
  generateMappings,
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
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'mappings' | 'gaps'>('mappings');

  const fetchData = async () => {
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
      fetchData();
    }
  }, [id, userId]);

  const handleGenerate = async () => {
    if (!userId) return;

    setGenerating(true);
    setError(null);

    try {
      await generateMappings(id, {}, userId);
      await fetchData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to generate mappings');
    } finally {
      setGenerating(false);
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
      count: gapData?.total_gaps || 0,
    },
  ];

  return (
    <div className="space-y-6 animate-fadeIn">
      <Card animated>
        <CardHeader variant="gradient">
          <div className="flex justify-between items-center">
            <CardTitle icon={<Sparkles className="h-5 w-5" />}>AI Mapping Generation</CardTitle>
            <Button variant="gradient" onClick={handleGenerate} loading={generating}>
              {controlMappings.length + policyMappings.length > 0
                ? 'Regenerate Mappings'
                : 'Generate Mappings'}
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-neutral-600">
            Generate AI-powered mappings between your controls/policies and framework
            requirements. Review and approve each suggestion to confirm the mappings.
          </p>
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
                <span className={cn(
                  'px-2 py-0.5 text-xs font-semibold rounded-full',
                  isActive
                    ? 'bg-gradient-to-r from-primary-500 to-primary-600 text-white'
                    : 'bg-neutral-100 text-neutral-600'
                )}>
                  {tab.count}
                </span>
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
        <Card animated>
          <CardContent>
            {gapData ? (
              <GapsList gapData={gapData} assessmentId={id} />
            ) : (
              <div className="text-center py-8">
                <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-gradient-to-br from-primary-50 to-accent-50 flex items-center justify-center">
                  <Link2 className="h-8 w-8 text-primary-500" />
                </div>
                <p className="text-neutral-500">
                  Generate mappings first to analyze coverage gaps.
                </p>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
