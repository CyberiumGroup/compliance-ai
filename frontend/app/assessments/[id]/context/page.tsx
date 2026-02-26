'use client';

import { useState, useEffect, use } from 'react';
import { Building2, ShieldCheck, Save, CheckCircle2, ChevronDown, ChevronRight, ShieldAlert } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent, Button } from '@/components/ui';
import { LoadingSpinner, ErrorMessage } from '@/components/ui';
import { getAssessment, updateAssessment } from '@/lib/api';
import { useUserId } from '@/lib/hooks/useUserId';
import { cn } from '@/lib/utils';

interface ContextPageProps {
  params: Promise<{ id: string }>;
}

// ─── NIST SP 800-60 Information Types ─────────────────────────────────────────

interface InfoType {
  id: string;
  label: string;
}

interface InfoTypeGroup {
  id: string;
  label: string;
  description: string;
  types: InfoType[];
}

const INFORMATION_TYPE_GROUPS: InfoTypeGroup[] = [
  {
    id: 'business',
    label: 'Business Operations',
    description: 'Management and support information types applicable to most organizations (NIST SP 800-60, C.2–C.3)',
    types: [
      // Identity & access
      { id: 'identity_auth',        label: 'Personal identity and authentication information' },      // C.2.8.9
      // Financial
      { id: 'accounting',           label: 'Accounting records' },                                   // C.3.2.4
      { id: 'payments',             label: 'Payments and transactions' },                             // C.3.2.5
      { id: 'collections',          label: 'Collections and receivables' },                           // C.3.2.6
      { id: 'assets_liabilities',   label: 'Asset and liability management' },                        // C.3.2.1
      // HR & personnel
      { id: 'staff_acquisition',    label: 'Staff acquisition and onboarding' },                     // C.3.3.2
      { id: 'compensation',         label: 'Compensation management' },                               // C.3.3.4
      { id: 'benefits',             label: 'Benefits management' },                                   // C.3.3.5
      { id: 'employee_performance', label: 'Employee performance management' },                       // C.3.3.6
      // IT & security
      { id: 'info_security',        label: 'Information security operations' },                       // C.3.5.5
      { id: 'system_monitoring',    label: 'System and network monitoring' },                         // C.3.5.8
      { id: 'records_retention',    label: 'Records retention and management' },                      // C.3.5.6
      { id: 'info_sharing',         label: 'Information sharing' },                                   // C.3.5.9
      // Procurement & supply chain
      { id: 'goods_acquisition',    label: 'Goods acquisition / procurement' },                       // C.3.4.1
      { id: 'services_acquisition', label: 'Services acquisition and contracting' },                  // C.3.4.4
      { id: 'inventory_logistics',  label: 'Inventory control and logistics' },                       // C.3.4.2–3
      // Continuity & customer
      { id: 'continuity',           label: 'Contingency planning and continuity of operations' },     // C.2.4.1–2
      { id: 'customer_services',    label: 'Customer services and support' },                         // C.2.6.1
    ],
  },
  {
    id: 'government',
    label: 'Government / Mission Services',
    description: 'Mission-based information types for government and public sector organizations (NIST SP 800-60, D.x)',
    types: [
      { id: 'border_security',      label: 'Border and transportation security' },                    // D.2.1
      { id: 'military_ops',         label: 'Military operations' },                                   // D.26.1
      { id: 'intelligence',         label: 'Intelligence collection and analysis' },                  // D.3.2–3
      { id: 'emergency_response',   label: 'Emergency and disaster response' },                       // D.4.4
      { id: 'disaster_planning',    label: 'Disaster preparedness and planning' },                    // D.4.2
      { id: 'foreign_affairs',      label: 'Foreign affairs and diplomatic operations' },             // D.5.1
      { id: 'financial_oversight',  label: 'Financial sector oversight and regulation' },             // D.9.3
      { id: 'health_delivery',      label: 'Health care delivery services' },                         // D.14.4
      { id: 'health_admin',         label: 'Health care administration' },                            // D.14.3
      { id: 'public_health',        label: 'Population health management and consumer safety' },      // D.14.2
      { id: 'retirement_disability',label: 'Retirement and disability programs' },                    // D.15.1
      { id: 'social_assistance',    label: 'Unemployment, housing, and food assistance' },            // D.15.2–4
      { id: 'law_enforcement',      label: 'Criminal investigation and apprehension' },               // D.16.1–2
      { id: 'prosecution',          label: 'Legal prosecution, litigation, and judicial hearings' },  // D.17.1–4
      { id: 'corrections',          label: 'Corrections and criminal rehabilitation' },               // D.18.1–2
      { id: 'science_research',     label: 'Scientific and technological research and innovation' },  // D.19.1
    ],
  },
];

// ─── Form state ────────────────────────────────────────────────────────────────

interface ProfileForm {
  organization_name: string;
  industry: string;
  business_description: string;
  product_service_description: string;
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function ContextPage({ params }: ContextPageProps) {
  const { id } = use(params);
  const userId = useUserId();

  const [profile, setProfile] = useState<ProfileForm>({
    organization_name: '',
    industry: '',
    business_description: '',
    product_service_description: '',
  });
  const [selectedTypes, setSelectedTypes] = useState<Set<string>>(new Set());
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(new Set(['business']));

  const [loading, setLoading] = useState(true);
  const [savingProfile, setSavingProfile] = useState(false);
  const [savedProfile, setSavedProfile] = useState(false);
  const [savingRisk, setSavingRisk] = useState(false);
  const [savedRisk, setSavedRisk] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!userId) return;
    const fetchData = async () => {
      try {
        const assessment = await getAssessment(id, userId);
        setProfile({
          organization_name: assessment.organization_name ?? '',
          industry: assessment.industry ?? '',
          business_description: assessment.business_description ?? '',
          product_service_description: assessment.product_service_description ?? '',
        });
        if (assessment.information_types) {
          try {
            const parsed = JSON.parse(assessment.information_types);
            if (Array.isArray(parsed)) setSelectedTypes(new Set(parsed));
          } catch { /* ignore malformed */ }
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load context');
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [id, userId]);

  const handleProfileChange = (field: keyof ProfileForm) =>
    (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
      setProfile(prev => ({ ...prev, [field]: e.target.value }));
      setSavedProfile(false);
    };

  const toggleType = (typeId: string) => {
    setSelectedTypes(prev => {
      const next = new Set(prev);
      next.has(typeId) ? next.delete(typeId) : next.add(typeId);
      return next;
    });
    setSavedRisk(false);
  };

  const toggleGroup = (groupId: string) => {
    setExpandedGroups(prev => {
      const next = new Set(prev);
      next.has(groupId) ? next.delete(groupId) : next.add(groupId);
      return next;
    });
  };

  const handleSaveProfile = async () => {
    if (!userId) return;
    setSavingProfile(true);
    setError(null);
    try {
      await updateAssessment(id, {
        organization_name: profile.organization_name || undefined,
        industry: profile.industry || null,
        business_description: profile.business_description || null,
        product_service_description: profile.product_service_description || null,
      }, userId);
      setSavedProfile(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save company profile');
    } finally {
      setSavingProfile(false);
    }
  };

  const handleSaveRisk = async () => {
    if (!userId) return;
    setSavingRisk(true);
    setError(null);
    try {
      await updateAssessment(id, {
        information_types: JSON.stringify([...selectedTypes]),
      }, userId);
      setSavedRisk(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save risk profile');
    } finally {
      setSavingRisk(false);
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
      {error && <ErrorMessage message={error} />}

      {/* ── Company Profile ── */}
      <Card animated>
        <CardHeader variant="gradient">
          <CardTitle icon={<Building2 className="h-5 w-5" />}>Company Profile</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-neutral-500 mb-6">
            This information gives the AI assessment tool additional context about the client
            organization during scoring and report generation.
          </p>

          <div className="space-y-5">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
              <div>
                <label className={labelClass}>Company name</label>
                <input
                  type="text"
                  value={profile.organization_name}
                  onChange={handleProfileChange('organization_name')}
                  placeholder="Acme Corp"
                  className={inputClass}
                />
                <div className="flex items-center gap-1.5 mt-1.5 text-xs text-neutral-400">
                  <ShieldCheck className="h-3 w-3 flex-shrink-0" />
                  <span>Company name will never be disclosed to external AI services.</span>
                </div>
              </div>
              <div>
                <label className={labelClass}>Industry</label>
                <input
                  type="text"
                  value={profile.industry}
                  onChange={handleProfileChange('industry')}
                  placeholder="e.g. Financial services, Healthcare, SaaS"
                  className={inputClass}
                />
              </div>
            </div>

            <div>
              <label className={labelClass}>Business description</label>
              <textarea
                rows={4}
                value={profile.business_description}
                onChange={handleProfileChange('business_description')}
                placeholder="Describe what the company does, its size, key markets, and any relevant operational context…"
                className={textareaClass}
              />
            </div>

            <div>
              <label className={labelClass}>Product / service description</label>
              <textarea
                rows={4}
                value={profile.product_service_description}
                onChange={handleProfileChange('product_service_description')}
                placeholder="Describe the products or services being assessed, including how data is stored, processed, or transmitted…"
                className={textareaClass}
              />
            </div>
          </div>

          <div className="mt-6 flex items-center gap-3">
            <Button
              variant="gradient"
              onClick={handleSaveProfile}
              loading={savingProfile}
              leftIcon={savedProfile ? <CheckCircle2 className="h-4 w-4" /> : <Save className="h-4 w-4" />}
            >
              {savedProfile ? 'Saved' : 'Save'}
            </Button>
            {savedProfile && <span className="text-sm text-green-600">Profile saved successfully.</span>}
          </div>
        </CardContent>
      </Card>

      {/* ── Risk Profile ── */}
      <Card animated>
        <CardHeader variant="gradient">
          <CardTitle icon={<ShieldAlert className="h-5 w-5" />}>Risk Profile</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-neutral-500 mb-1">
            Select all information types that this organization handles, holds, or processes.
          </p>
          <p className="text-xs text-neutral-400 mb-6">
            Categories are derived from NIST SP 800-60. Selections help tailor the scoring context.
          </p>

          <div className="space-y-3">
            {INFORMATION_TYPE_GROUPS.map(group => {
              const isExpanded = expandedGroups.has(group.id);
              const selectedInGroup = group.types.filter(t => selectedTypes.has(t.id)).length;

              return (
                <div key={group.id} className="rounded-lg border border-neutral-200 overflow-hidden">
                  {/* Group header */}
                  <button
                    onClick={() => toggleGroup(group.id)}
                    className="w-full flex items-center gap-3 px-4 py-3 bg-neutral-50 hover:bg-neutral-100 transition-colors text-left"
                  >
                    {isExpanded
                      ? <ChevronDown className="h-4 w-4 text-neutral-400 flex-shrink-0" />
                      : <ChevronRight className="h-4 w-4 text-neutral-400 flex-shrink-0" />}
                    <span className="text-sm font-semibold text-neutral-800 flex-1">{group.label}</span>
                    {selectedInGroup > 0 && (
                      <span className="text-xs font-medium text-primary-700 bg-primary-50 border border-primary-200 px-2 py-0.5 rounded-full">
                        {selectedInGroup} selected
                      </span>
                    )}
                  </button>

                  {/* Group body */}
                  {isExpanded && (
                    <div className="px-4 py-4 bg-white">
                      <p className="text-xs text-neutral-400 mb-3">{group.description}</p>
                      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
                        {group.types.map(type => {
                          const checked = selectedTypes.has(type.id);
                          return (
                            <label
                              key={type.id}
                              className={cn(
                                'flex items-center gap-2.5 px-3 py-2 rounded-lg border cursor-pointer transition-all text-sm',
                                checked
                                  ? 'border-primary-300 bg-primary-50 text-primary-800'
                                  : 'border-neutral-200 hover:border-neutral-300 hover:bg-neutral-50 text-neutral-700'
                              )}
                            >
                              <input
                                type="checkbox"
                                checked={checked}
                                onChange={() => toggleType(type.id)}
                                className="accent-primary-500 h-3.5 w-3.5 flex-shrink-0"
                              />
                              {type.label}
                            </label>
                          );
                        })}
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          <div className="mt-6 flex items-center gap-3">
            <Button
              variant="gradient"
              onClick={handleSaveRisk}
              loading={savingRisk}
              leftIcon={savedRisk ? <CheckCircle2 className="h-4 w-4" /> : <Save className="h-4 w-4" />}
            >
              {savedRisk ? 'Saved' : 'Save'}
            </Button>
            {savedRisk && <span className="text-sm text-green-600">Risk profile saved successfully.</span>}
            {selectedTypes.size > 0 && (
              <span className="text-xs text-neutral-400 ml-auto">{selectedTypes.size} type{selectedTypes.size !== 1 ? 's' : ''} selected</span>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
