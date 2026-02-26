'use client';

import { useState, useEffect, use } from 'react';
import { Building2, Save, CheckCircle2, ShieldCheck } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent, Button } from '@/components/ui';
import { LoadingSpinner, ErrorMessage } from '@/components/ui';
import { getAssessment, updateAssessment } from '@/lib/api';
import { useUserId } from '@/lib/hooks/useUserId';

interface CompanyProfilePageProps {
  params: Promise<{ id: string }>;
}

interface FormState {
  organization_name: string;
  industry: string;
  business_description: string;
  product_service_description: string;
}

export default function CompanyProfilePage({ params }: CompanyProfilePageProps) {
  const { id } = use(params);
  const userId = useUserId();

  const [form, setForm] = useState<FormState>({
    organization_name: '',
    industry: '',
    business_description: '',
    product_service_description: '',
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!userId) return;

    const fetchData = async () => {
      try {
        const assessment = await getAssessment(id, userId);
        setForm({
          organization_name: assessment.organization_name ?? '',
          industry: assessment.industry ?? '',
          business_description: assessment.business_description ?? '',
          product_service_description: assessment.product_service_description ?? '',
        });
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load profile');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [id, userId]);

  const handleChange = (field: keyof FormState) =>
    (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
      setForm(prev => ({ ...prev, [field]: e.target.value }));
      setSaved(false);
    };

  const handleSave = async () => {
    if (!userId) return;
    setSaving(true);
    setError(null);
    try {
      await updateAssessment(id, {
        organization_name: form.organization_name || undefined,
        industry: form.industry || null,
        business_description: form.business_description || null,
        product_service_description: form.product_service_description || null,
      }, userId);
      setSaved(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save profile');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center py-12">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  const inputClass =
    'w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-900 placeholder:text-neutral-400 focus:border-primary-400 focus:outline-none focus:ring-2 focus:ring-primary-100 transition-colors';
  const textareaClass = `${inputClass} resize-none leading-relaxed`;
  const labelClass = 'block text-sm font-medium text-neutral-700 mb-1.5';

  return (
    <div className="space-y-6 animate-fadeIn">
      <Card animated>
        <CardHeader variant="gradient">
          <CardTitle icon={<Building2 className="h-5 w-5" />}>Company Profile</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-neutral-500 mb-6">
            This information gives the AI assessment tool additional context about the client organization during
            scoring and report generation.
          </p>

          <div className="space-y-5">
            {/* Row 1: Company name + Industry */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
              <div>
                <label className={labelClass}>Company name</label>
                <input
                  type="text"
                  value={form.organization_name}
                  onChange={handleChange('organization_name')}
                  placeholder="Acme Corp"
                  className={inputClass}
                />
                <div className="flex items-center gap-1.5 mt-1.5 text-xs text-neutral-400">
                  <ShieldCheck className="h-3 w-3 flex-shrink-0" />
                  <span>Never disclosed to external AI services.</span>
                </div>
              </div>
              <div>
                <label className={labelClass}>Industry</label>
                <input
                  type="text"
                  value={form.industry}
                  onChange={handleChange('industry')}
                  placeholder="e.g. Financial services, Healthcare, SaaS"
                  className={inputClass}
                />
              </div>
            </div>

            {/* Business description */}
            <div>
              <label className={labelClass}>Business description</label>
              <textarea
                rows={4}
                value={form.business_description}
                onChange={handleChange('business_description')}
                placeholder="Describe what the company does, its size, key markets, and any relevant operational context…"
                className={textareaClass}
              />
            </div>

            {/* Product / service description */}
            <div>
              <label className={labelClass}>Product / service description</label>
              <textarea
                rows={4}
                value={form.product_service_description}
                onChange={handleChange('product_service_description')}
                placeholder="Describe the products or services being assessed, including how data is stored, processed, or transmitted…"
                className={textareaClass}
              />
            </div>
          </div>

          {error && <ErrorMessage message={error} className="mt-4" />}

          <div className="mt-6 flex items-center gap-3">
            <Button
              variant="gradient"
              onClick={handleSave}
              loading={saving}
              leftIcon={saved ? <CheckCircle2 className="h-4 w-4" /> : <Save className="h-4 w-4" />}
            >
              {saved ? 'Saved' : 'Save'}
            </Button>
            {saved && (
              <span className="text-sm text-green-600">Profile saved successfully.</span>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
