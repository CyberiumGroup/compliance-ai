'use client';

import { useState, useEffect, use } from 'react';
import { FileDown, FileText } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent, Button } from '@/components/ui';
import { LoadingSpinner, ErrorMessage } from '@/components/ui';
import { ReportList, GenerateButton, ReportViewer } from '@/components/reports';
import { listReports, getReport } from '@/lib/api';
import { useUserId } from '@/lib/hooks/useUserId';
import { Report } from '@/lib/types';

interface ReportsPageProps {
  params: Promise<{ id: string }>;
}

export default function ReportsPage({ params }: ReportsPageProps) {
  const { id } = use(params);
  const userId = useUserId();
  const [reports, setReports] = useState<Report[]>([]);
  const [selectedReport, setSelectedReport] = useState<Report | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchReports = async () => {
    if (!userId) return;

    try {
      const data = await listReports(id, userId);
      setReports(data.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load reports');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (userId) {
      fetchReports();
    }
  }, [id, userId]);

  const handleGenerate = (report: Report) => {
    setReports([report, ...reports]);
    setSelectedReport(report);
  };

  const handleView = async (reportId: string) => {
    if (!userId) return;

    try {
      const report = await getReport(reportId, userId);
      setSelectedReport(report);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load report');
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center py-12">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  if (selectedReport) {
    return (
      <ReportViewer report={selectedReport} onClose={() => setSelectedReport(null)} />
    );
  }

  return (
    <div className="space-y-6 animate-fadeIn">
      <Card animated>
        <CardHeader variant="gradient">
          <CardTitle icon={<FileDown className="h-5 w-5" />}>Generate Report</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-neutral-600 mb-4">
            Generate comprehensive reports based on your assessment data. Reports include
            executive summaries, maturity scores, deviations, and recommendations.
          </p>
          <GenerateButton assessmentId={id} onGenerate={handleGenerate} />
        </CardContent>
      </Card>

      {error && <ErrorMessage message={error} onRetry={fetchReports} />}

      <Card animated>
        <CardHeader variant="gradient">
          <CardTitle icon={<FileText className="h-5 w-5" />}>Generated Reports</CardTitle>
        </CardHeader>
        <CardContent>
          <ReportList reports={reports} onView={handleView} />
        </CardContent>
      </Card>
    </div>
  );
}
