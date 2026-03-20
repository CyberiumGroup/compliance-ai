'use client';

import { useState, useEffect, use } from 'react';
import { useRouter } from 'next/navigation';
import { Button, Input, Textarea } from '@/components/ui';
import { LoadingSpinner, ErrorMessage } from '@/components/ui';
import { getAssessment, updateAssessment } from '@/lib/api';
import { useUserId } from '@/lib/hooks/useUserId';

interface EditPageProps {
  params: Promise<{ id: string }>;
}

export default function AssessmentEditPage({ params }: EditPageProps) {
  const { id } = use(params);
  const userId = useUserId();
  const router = useRouter();

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [formData, setFormData] = useState({
    name: '',
    organization_name: '',
    description: '',
  });

  useEffect(() => {
    if (!userId) return;
    getAssessment(id, userId)
      .then((a) =>
        setFormData({
          name: a.name,
          organization_name: a.organization_name,
          description: a.description ?? '',
        })
      )
      .catch((err) => setError(err instanceof Error ? err.message : 'Failed to load assessment'))
      .finally(() => setLoading(false));
  }, [id, userId]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!userId) return;
    setSaving(true);
    setError(null);
    try {
      await updateAssessment(
        id,
        {
          name: formData.name.trim(),
          organization_name: formData.organization_name.trim(),
          description: formData.description.trim() || undefined,
        },
        userId
      );
      router.push(`/assessments/${id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save changes');
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center py-16">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  if (error && !formData.name) {
    return <ErrorMessage message={error} />;
  }

  return (
    <div className="max-w-xl">
      <div className="mb-6">
        <h2 className="text-lg font-semibold text-neutral-900">Edit assessment details</h2>
        <p className="text-sm text-neutral-500 mt-1">Update the name, organisation, and description for this assessment.</p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-5">
        {error && (
          <div className="rounded-md bg-red-50 border border-red-200 px-4 py-3">
            <p className="text-sm text-red-700">{error}</p>
          </div>
        )}

        <Input
          label="Assessment name"
          required
          value={formData.name}
          onChange={(e) => setFormData({ ...formData, name: e.target.value })}
          placeholder="Q1 2025 Security Assessment"
        />

        <Input
          label="Organisation name"
          required
          value={formData.organization_name}
          onChange={(e) => setFormData({ ...formData, organization_name: e.target.value })}
          placeholder="Acme Corporation"
        />

        <Textarea
          label="Description"
          value={formData.description}
          onChange={(e) => setFormData({ ...formData, description: e.target.value })}
          placeholder="Brief description of the assessment scope and objectives…"
          rows={4}
        />

        <div className="flex items-center gap-3 pt-2 border-t border-neutral-200">
          <Button type="submit" loading={saving} disabled={!formData.name.trim()}>
            Save changes
          </Button>
          <Button
            type="button"
            variant="ghost"
            onClick={() => router.push(`/assessments/${id}`)}
            disabled={saving}
          >
            Cancel
          </Button>
        </div>
      </form>
    </div>
  );
}
