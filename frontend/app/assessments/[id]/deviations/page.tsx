'use client';

import { useState, useEffect, use } from 'react';
import { AlertTriangle, Search, AlertCircle } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent, Button } from '@/components/ui';
import { LoadingSpinner, ErrorMessage, EmptyState } from '@/components/ui';
import { DeviationCard, DeviationFilters } from '@/components/deviations';
import { detectDeviations, listDeviations, updateDeviation } from '@/lib/api';
import { useUserId } from '@/lib/hooks/useUserId';
import { DeviationListResponse } from '@/lib/types';
import { cn } from '@/lib/utils';

interface DeviationsPageProps {
  params: Promise<{ id: string }>;
}

export default function DeviationsPage({ params }: DeviationsPageProps) {
  const { id } = use(params);
  const userId = useUserId();
  const [data, setData] = useState<DeviationListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [detecting, setDetecting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [severityFilter, setSeverityFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');

  const fetchDeviations = async () => {
    if (!userId) return;

    try {
      const result = await listDeviations(
        id,
        { severity: severityFilter || undefined, status: statusFilter || undefined },
        userId
      );
      setData(result);
    } catch {
      setData(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (userId) {
      fetchDeviations();
    }
  }, [id, userId, severityFilter, statusFilter]);

  const handleDetect = async () => {
    if (!userId) return;

    setDetecting(true);
    setError(null);

    try {
      const result = await detectDeviations(id, userId);
      setData(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to detect deviations');
    } finally {
      setDetecting(false);
    }
  };

  const handleUpdateStatus = async (deviationId: string, status: string, notes?: string) => {
    if (!userId || !data) return;

    await updateDeviation(deviationId, { status, remediation_notes: notes }, userId);
    setData({
      ...data,
      items: data.items.map((d) =>
        d.id === deviationId ? { ...d, status, remediation_notes: notes || d.remediation_notes } : d
      ),
    });
  };

  if (loading) {
    return (
      <div className="flex justify-center py-12">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  const severityConfig = [
    { key: 'CRITICAL', label: 'Critical', bg: 'from-red-50 to-red-100', border: 'border-red-200', text: 'text-red-700' },
    { key: 'HIGH', label: 'High', bg: 'from-orange-50 to-orange-100', border: 'border-orange-200', text: 'text-orange-700' },
    { key: 'MEDIUM', label: 'Medium', bg: 'from-amber-50 to-amber-100', border: 'border-amber-200', text: 'text-amber-700' },
    { key: 'LOW', label: 'Low', bg: 'from-accent-50 to-accent-100', border: 'border-accent-200', text: 'text-accent-700' },
  ];

  return (
    <div className="space-y-6 animate-fadeIn">
      <Card animated>
        <CardHeader variant="gradient">
          <div className="flex justify-between items-center">
            <CardTitle icon={<AlertTriangle className="h-5 w-5" />}>Deviations & Risk</CardTitle>
            <Button variant="gradient" onClick={handleDetect} loading={detecting} leftIcon={<Search className="h-4 w-4" />}>
              {data && data.total > 0 ? 'Re-detect' : 'Detect Deviations'}
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-neutral-600">
            Deviations identify gaps between your current security posture and framework
            requirements. Each deviation is risk-ranked based on impact and likelihood.
          </p>
          {error && <ErrorMessage message={error} className="mt-4" />}
        </CardContent>
      </Card>

      {data && data.total > 0 && (
        <>
          <Card animated>
            <CardContent>
              <div className="grid grid-cols-5 gap-4">
                <div className="p-4 bg-gradient-to-br from-slate-50 to-slate-100 rounded-xl border border-neutral-200 text-center">
                  <p className="text-3xl font-bold gradient-text">{data.total}</p>
                  <p className="text-sm text-neutral-500 mt-1">Total</p>
                </div>
                {severityConfig.map((config) => (
                  <div
                    key={config.key}
                    className={cn(
                      'p-4 rounded-xl border text-center bg-gradient-to-br',
                      config.bg,
                      config.border
                    )}
                  >
                    <p className={cn('text-3xl font-bold', config.text)}>
                      {data.by_severity[config.key] || 0}
                    </p>
                    <p className="text-sm text-neutral-500 mt-1">{config.label}</p>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          <Card animated>
            <CardContent>
              <DeviationFilters
                severity={severityFilter}
                status={statusFilter}
                onSeverityChange={setSeverityFilter}
                onStatusChange={setStatusFilter}
                counts={{ by_severity: data.by_severity, by_status: data.by_status }}
              />
            </CardContent>
          </Card>

          <div className="space-y-4">
            {data.items.map((deviation, index) => (
              <div
                key={deviation.id}
                className="animate-slideInUp opacity-0"
                style={{
                  animationDelay: `${index * 75}ms`,
                  animationFillMode: 'forwards'
                }}
              >
                <DeviationCard
                  deviation={deviation}
                  onUpdateStatus={handleUpdateStatus}
                />
              </div>
            ))}
          </div>
        </>
      )}

      {(!data || data.total === 0) && (
        <EmptyState
          title="No deviations detected"
          description="Run deviation detection to identify gaps in your security posture"
          action={{
            label: 'Detect Deviations',
            onClick: handleDetect,
          }}
        />
      )}
    </div>
  );
}
