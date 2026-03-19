'use client';

import { useState, useEffect, use } from 'react';
import {
  FileText, Shield, Table2, MessageSquare, CheckCircle, AlertCircle, Upload,
} from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui';
import { LoadingSpinner, ErrorMessage } from '@/components/ui';
import { PolicyUploader, PolicyList } from '@/components/policies';
import { listPolicies, deletePolicy } from '@/lib/api';
import { useUserId } from '@/lib/hooks/useUserId';
import { Policy, PolicyUploadResponse, EvidenceSection } from '@/lib/types';
import { cn } from '@/lib/utils';

interface EvidencePageProps {
  params: Promise<{ id: string }>;
}

interface SectionConfig {
  id: EvidenceSection;
  label: string;
  description: string;
  icon: React.ReactNode;
  formats: string;
}

const SECTIONS: SectionConfig[] = [
  {
    id: 'policy',
    label: 'Policies',
    description: 'Formal policy documents that establish rules, standards, and requirements.',
    icon: <FileText className="h-4 w-4" />,
    formats: 'PDF, DOCX, TXT, MD',
  },
  {
    id: 'process',
    label: 'Processes',
    description: 'Documented procedures and process guides describing how activities are carried out.',
    icon: <FileText className="h-4 w-4" />,
    formats: 'PDF, DOCX, TXT, MD',
  },
  {
    id: 'control',
    label: 'Controls',
    description: 'Control registers or matrices, typically in spreadsheet format.',
    icon: <Table2 className="h-4 w-4" />,
    formats: 'CSV, XLSX',
  },
  {
    id: 'interview',
    label: 'Interviews',
    description: 'Interview notes, transcripts, or responses collected during the assessment.',
    icon: <MessageSquare className="h-4 w-4" />,
    formats: 'DOCX, TXT, MD',
  },
  {
    id: 'proof',
    label: 'Proof',
    description: 'Implementation evidence such as screenshots, logs, configuration exports, or audit reports.',
    icon: <Shield className="h-4 w-4" />,
    formats: 'PDF, DOCX, TXT, MD, XLSX, CSV',
  },
];

export default function EvidencePage({ params }: EvidencePageProps) {
  const { id } = use(params);
  const userId = useUserId();
  const [activeSection, setActiveSection] = useState<EvidenceSection>('policy');
  const [allDocs, setAllDocs] = useState<Policy[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [uploadResult, setUploadResult] = useState<PolicyUploadResponse | null>(null);

  const fetchDocs = async () => {
    if (!userId) return;
    try {
      const data = await listPolicies(id, userId);
      setAllDocs(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load documents');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (userId) fetchDocs();
  }, [id, userId]);

  const handleSectionChange = (section: EvidenceSection) => {
    setActiveSection(section);
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
      setAllDocs(prev => prev.filter(p => p.id !== policyId));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete document');
    }
  };

  const docsForSection = (section: EvidenceSection) => {
    const tagged = allDocs.filter(p => p.section === section);
    // Legacy docs with no section: surface under 'policy' or 'proof'
    if (section === 'policy') return [...tagged, ...allDocs.filter(p => !p.section && p.document_type === 'policy')];
    if (section === 'proof')  return [...tagged, ...allDocs.filter(p => !p.section && p.document_type === 'evidence')];
    return tagged;
  };

  const currentSection = SECTIONS.find(s => s.id === activeSection)!;
  const currentDocs = docsForSection(activeSection);

  if (loading) {
    return (
      <div className="flex justify-center py-12">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fadeIn">
      {/* Tab navigation */}
      <div className="flex gap-1 p-1 bg-neutral-100 rounded-xl w-fit flex-wrap">
        {SECTIONS.map((section) => {
          const count = docsForSection(section.id).length;
          const isActive = activeSection === section.id;
          return (
            <button
              key={section.id}
              onClick={() => handleSectionChange(section.id)}
              className={cn(
                'flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all',
                isActive ? 'bg-white text-neutral-900 shadow-sm' : 'text-neutral-500 hover:text-neutral-700'
              )}
            >
              {section.icon}
              {section.label}
              <span className={cn(
                'ml-1 px-1.5 py-0.5 rounded text-[10px] font-semibold',
                isActive ? 'bg-primary-100 text-primary-700' : 'bg-neutral-200 text-neutral-500'
              )}>
                {count}
              </span>
            </button>
          );
        })}
      </div>

      {/* Upload card */}
      <Card animated>
        <CardHeader variant="gradient">
          <CardTitle icon={<Upload className="h-5 w-5" />}>
            Upload — {currentSection.label}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-neutral-500 mb-4">{currentSection.description}</p>

          <PolicyUploader
            assessmentId={id}
            section={activeSection}
            onUploadComplete={handleUploadComplete}
          />

          {uploadResult && (
            <div className="mt-4 p-4 bg-neutral-50 rounded-xl border border-neutral-200">
              <h4 className="font-semibold text-neutral-900 flex items-center gap-2">
                <CheckCircle className="h-5 w-5 text-accent-500" />
                Upload Result
              </h4>
              <div className="mt-3 space-y-2 text-sm">
                <p className="text-neutral-700">
                  <span className="font-medium">{currentSection.label}:</span>{' '}
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
                    Extraction issue: {uploadResult.extraction_error}
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
          <CardTitle icon={currentSection.icon}>
            {currentSection.label} ({currentDocs.length})
          </CardTitle>
        </CardHeader>
        <CardContent>
          {error ? (
            <ErrorMessage message={error} onRetry={fetchDocs} />
          ) : (
            <PolicyList policies={currentDocs} assessmentId={id} onDelete={handleDelete} />
          )}
        </CardContent>
      </Card>
    </div>
  );
}
