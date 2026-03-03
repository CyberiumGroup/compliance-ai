'use client';

import { useState, useEffect, use } from 'react';
import { FileText, Upload, CheckCircle, AlertCircle, Shield } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui';
import { LoadingSpinner, ErrorMessage } from '@/components/ui';
import { PolicyUploader, PolicyList } from '@/components/policies';
import { listPolicies, deletePolicy } from '@/lib/api';
import { useUserId } from '@/lib/hooks/useUserId';
import { Policy, PolicyUploadResponse } from '@/lib/types';
import { cn } from '@/lib/utils';

interface PoliciesPageProps {
  params: Promise<{ id: string }>;
}

type TabType = 'policy' | 'evidence';

const TABS: { id: TabType; label: string; icon: React.ReactNode }[] = [
  { id: 'policy', label: 'Policies', icon: <FileText className="h-4 w-4" /> },
  { id: 'evidence', label: 'Implementation Evidence', icon: <Shield className="h-4 w-4" /> },
];

export default function PoliciesPage({ params }: PoliciesPageProps) {
  const { id } = use(params);
  const userId = useUserId();
  const [activeTab, setActiveTab] = useState<TabType>('policy');
  const [allDocs, setAllDocs] = useState<Policy[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [uploadResult, setUploadResult] = useState<PolicyUploadResponse | null>(null);

  const fetchDocs = async () => {
    if (!userId) return;
    try {
      // Fetch all docs in a single call; split by document_type on the frontend.
      const data = await listPolicies(id, userId);
      setAllDocs(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load documents');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (userId) {
      fetchDocs();
    }
  }, [id, userId]);

  const handleTabChange = (tab: TabType) => {
    setActiveTab(tab);
    setUploadResult(null);
  };

  const handleUploadComplete = (response: PolicyUploadResponse) => {
    setUploadResult(response);
    setAllDocs(prev => [response.policy, ...prev]);
  };

  const handleDelete = async (policyId: string) => {
    if (!userId) return;
    try {
      await deletePolicy(policyId, userId);
      setAllDocs(prev => prev.filter((p) => p.id !== policyId));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete document');
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center py-12">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  // Split by document_type; treat missing/null as 'policy' (pre-migration docs)
  const policies = allDocs.filter(p => !p.document_type || p.document_type === 'policy');
  const evidence = allDocs.filter(p => p.document_type === 'evidence');
  const currentDocs = activeTab === 'policy' ? policies : evidence;

  return (
    <div className="space-y-6 animate-fadeIn">
      {/* Tab navigation */}
      <div className="flex gap-1 p-1 bg-neutral-100 rounded-xl w-fit">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => handleTabChange(tab.id)}
            className={cn(
              'flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all',
              activeTab === tab.id
                ? 'bg-white text-neutral-900 shadow-sm'
                : 'text-neutral-500 hover:text-neutral-700'
            )}
          >
            {tab.icon}
            {tab.label}
            <span className={cn(
              'ml-1 px-1.5 py-0.5 rounded text-[10px] font-semibold',
              activeTab === tab.id
                ? 'bg-primary-100 text-primary-700'
                : 'bg-neutral-200 text-neutral-500'
            )}>
              {tab.id === 'policy' ? policies.length : evidence.length}
            </span>
          </button>
        ))}
      </div>

      {/* Upload card */}
      <Card animated>
        <CardHeader variant="gradient">
          <CardTitle icon={<Upload className="h-5 w-5" />}>
            {activeTab === 'evidence' ? 'Upload Implementation Evidence' : 'Upload Policy Document'}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {activeTab === 'evidence' && (
            <p className="text-sm text-neutral-500 mb-4">
              Upload implementation evidence such as configuration exports, audit logs, test results,
              or screenshots that demonstrate controls are actively deployed.
            </p>
          )}

          <PolicyUploader
            assessmentId={id}
            onUploadComplete={handleUploadComplete}
            documentType={activeTab}
          />

          {uploadResult && (
            <div className="mt-4 p-4 bg-neutral-50 rounded-xl border border-neutral-200">
              <h4 className="font-semibold text-neutral-900 flex items-center gap-2">
                <CheckCircle className="h-5 w-5 text-accent-500" />
                Upload Result
              </h4>
              <div className="mt-3 space-y-2 text-sm">
                <p className="text-neutral-700">
                  <span className="font-medium">
                    {activeTab === 'evidence' ? 'Evidence' : 'Policy'}:
                  </span>{' '}
                  {uploadResult.policy.name}
                </p>
                {uploadResult.text_extracted ? (
                  <p className="text-accent-600 flex items-center gap-2">
                    <CheckCircle className="h-4 w-4" />
                    Text extracted ({uploadResult.text_length?.toLocaleString()} characters)
                  </p>
                ) : (
                  <p className="text-amber-600 flex items-center gap-2">
                    <AlertCircle className="h-4 w-4" />
                    Text extraction failed: {uploadResult.extraction_error}
                  </p>
                )}
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Documents list */}
      <Card animated>
        <CardHeader variant="gradient">
          <CardTitle icon={activeTab === 'evidence' ? <Shield className="h-5 w-5" /> : <FileText className="h-5 w-5" />}>
            {activeTab === 'evidence'
              ? `Implementation Evidence (${evidence.length})`
              : `Policies (${policies.length})`}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {error ? (
            <ErrorMessage message={error} onRetry={fetchDocs} />
          ) : (
            <PolicyList policies={currentDocs} onDelete={handleDelete} />
          )}
        </CardContent>
      </Card>
    </div>
  );
}
