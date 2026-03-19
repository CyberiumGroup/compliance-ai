'use client';

import { useState, useEffect, use } from 'react';
import { Link2, Sparkles, Trash2 } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent, Button } from '@/components/ui';
import { LoadingSpinner, ErrorMessage } from '@/components/ui';
import { MappingsList } from '@/components/mappings';
import {
  generateMappings,
  clearAllMappings,
  listPolicyMappings,
  rejectMapping,
  unrejectMapping,
} from '@/lib/api';
import { useUserId } from '@/lib/hooks/useUserId';
import { PolicyMapping } from '@/lib/types';

interface MappingsPageProps {
  params: Promise<{ id: string }>;
}

export default function MappingsPage({ params }: MappingsPageProps) {
  const { id } = use(params);
  const userId = useUserId();
  const [policyMappings, setPolicyMappings] = useState<PolicyMapping[]>([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [clearing, setClearing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchMappings = async () => {
    if (!userId) return;
    try {
      const mappings = await listPolicyMappings(id, userId).catch(() => []);
      setPolicyMappings(mappings);
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
      'Are you sure you want to clear ALL mappings? This will permanently delete all mappings for this assessment. This action cannot be undone.'
    )) {
      return;
    }

    setClearing(true);
    setError(null);

    try {
      await clearAllMappings(id, userId);
      setPolicyMappings([]);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to clear mappings');
    } finally {
      setClearing(false);
    }
  };

  const handleRejectPolicy = async (mappingId: string) => {
    if (!userId) return;
    await rejectMapping(mappingId, userId);
    setPolicyMappings(
      policyMappings.map((m) =>
        m.id === mappingId ? { ...m, is_rejected: true, rejected_at: new Date().toISOString() } : m
      )
    );
  };

  const handleUnrejectPolicy = async (mappingId: string) => {
    if (!userId) return;
    await unrejectMapping(mappingId, userId);
    setPolicyMappings(
      policyMappings.map((m) =>
        m.id === mappingId ? { ...m, is_rejected: false, rejected_at: null } : m
      )
    );
  };

  if (loading) {
    return (
      <div className="flex justify-center py-12">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fadeIn">
      <Card animated>
        <CardHeader variant="gradient">
          <CardTitle icon={<Sparkles className="h-5 w-5" />}>Semantic Mapping</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="flex items-start gap-4 p-4 rounded-lg bg-primary-50/50 border border-primary-100">
              <div className="flex-1">
                <h4 className="text-sm font-semibold text-neutral-900">Suggest Mappings</h4>
                <p className="text-xs text-neutral-600 mt-1">
                  Scores all uploaded policies against each in-scope requirement using semantic
                  similarity. Results are grouped by requirement and ranked by relevance.
                  Existing mappings will be preserved — only new pairs will be added.
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

            {policyMappings.length > 0 && (
              <div className="flex items-start gap-4 p-4 rounded-lg bg-red-50/50 border border-red-100">
                <div className="flex-1">
                  <h4 className="text-sm font-semibold text-red-900">Clear All Mappings</h4>
                  <p className="text-xs text-red-700/70 mt-1">
                    Permanently delete all mappings for this assessment. This cannot be undone.
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

      <Card animated>
        <CardContent>
          <MappingsList
            policyMappings={policyMappings}
            assessmentId={id}
            onRejectPolicy={handleRejectPolicy}
            onUnrejectPolicy={handleUnrejectPolicy}
          />
        </CardContent>
      </Card>
    </div>
  );
}
