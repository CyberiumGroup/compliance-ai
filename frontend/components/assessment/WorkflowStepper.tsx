'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import {
  Layers,
  Upload,
  Link2,
  BarChart3,
  FileText,
  CheckCircle,
  Circle,
  Loader2,
  ChevronRight,
} from 'lucide-react';
import {
  getAssessmentScope,
  listPolicies,
  listPolicyMappings,
  getScoreSummary,
  listReports,
} from '@/lib/api';
import { cn } from '@/lib/utils';

interface WorkflowStepperProps {
  assessmentId: string;
  userId: string;
}

type StepStatus = 'not_started' | 'in_progress' | 'complete';

interface WorkflowStep {
  id: string;
  label: string;
  description: string;
  icon: typeof Layers;
  href: string;
  status: StepStatus;
}

export function WorkflowStepper({ assessmentId, userId }: WorkflowStepperProps) {
  const [steps, setSteps] = useState<WorkflowStep[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const checkProgress = async () => {
      try {
        const [scope, policies, policyMappings, reports] =
          await Promise.all([
            getAssessmentScope(assessmentId).catch(() => []),
            listPolicies(assessmentId, userId).catch(() => []),
            listPolicyMappings(assessmentId, userId).catch(() => []),
            listReports(assessmentId, userId).catch(() => ({ items: [] })),
          ]);

        let scoreSummary = null;
        try {
          scoreSummary = await getScoreSummary(assessmentId, userId);
        } catch {
          // Scores not calculated yet
        }

        const hasScope = scope.length > 0;
        const hasEvidence = policies.length > 0;
        const hasMappings = policyMappings.length > 0;
        const approvedMappings = policyMappings.filter((m) => m.is_approved);
        const hasApprovedMappings = approvedMappings.length > 0;
        const hasScores = scoreSummary !== null;
        const hasReports = reports.items.length > 0;

        const getStatus = (done: boolean, partial: boolean): StepStatus => {
          if (done) return 'complete';
          if (partial) return 'in_progress';
          return 'not_started';
        };

        setSteps([
          {
            id: 'scope',
            label: 'Scope',
            description: 'Select compliance frameworks',
            icon: Layers,
            href: `/assessments/${assessmentId}/scope`,
            status: getStatus(hasScope, false),
          },
          {
            id: 'evidence',
            label: 'Evidence',
            description: 'Upload policies',
            icon: Upload,
            href: `/assessments/${assessmentId}/documentation`,
            status: getStatus(policies.length > 0, hasEvidence),
          },
          {
            id: 'mappings',
            label: 'Mappings',
            description: 'Map evidence to requirements',
            icon: Link2,
            href: `/assessments/${assessmentId}/mappings`,
            status: getStatus(hasApprovedMappings, hasMappings),
          },
          {
            id: 'scoring',
            label: 'Scoring',
            description: 'Calculate maturity scores',
            icon: BarChart3,
            href: `/assessments/${assessmentId}/scores`,
            status: getStatus(hasScores, false),
          },
          {
            id: 'report',
            label: 'Report',
            description: 'Generate assessment report',
            icon: FileText,
            href: `/assessments/${assessmentId}/reports`,
            status: getStatus(hasReports, false),
          },
        ]);
      } catch {
        // If progress check fails, show empty steps
      } finally {
        setLoading(false);
      }
    };

    checkProgress();
  }, [assessmentId, userId]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="w-6 h-6 text-primary-500 animate-spin" />
      </div>
    );
  }

  // Find next incomplete step
  const nextStep = steps.find((s) => s.status !== 'complete');

  return (
    <div className="space-y-4">
      {/* Step indicators */}
      <div className="flex items-center gap-1 overflow-x-auto pb-2">
        {steps.map((step, index) => {
          const Icon = step.icon;
          const isNext = nextStep?.id === step.id;
          const StatusIcon =
            step.status === 'complete'
              ? CheckCircle
              : step.status === 'in_progress'
                ? Loader2
                : Circle;

          return (
            <div key={step.id} className="flex items-center">
              <Link
                href={step.href}
                className={cn(
                  'flex items-center gap-2 px-3 py-2 rounded-lg transition-all text-sm whitespace-nowrap',
                  isNext
                    ? 'bg-primary-50 border border-primary-200 text-primary-700'
                    : step.status === 'complete'
                      ? 'bg-accent-50 text-accent-700'
                      : 'text-neutral-500 hover:bg-neutral-50'
                )}
              >
                <StatusIcon
                  className={cn(
                    'w-4 h-4 flex-shrink-0',
                    step.status === 'complete' && 'text-accent-500',
                    step.status === 'in_progress' && 'text-primary-500 animate-spin',
                    step.status === 'not_started' && 'text-neutral-300'
                  )}
                />
                <span className="font-medium">{step.label}</span>
              </Link>
              {index < steps.length - 1 && (
                <ChevronRight className="w-4 h-4 text-neutral-300 mx-1 flex-shrink-0" />
              )}
            </div>
          );
        })}
      </div>

      {/* Next step call to action */}
      {nextStep && (
        <Link
          href={nextStep.href}
          className="flex items-center justify-between p-4 rounded-xl bg-gradient-to-r from-primary-50 to-accent-50 border border-primary-100 hover:border-primary-200 transition-all group"
        >
          <div className="flex items-center gap-3">
            <div className="p-2 bg-white rounded-lg shadow-sm">
              <nextStep.icon className="w-5 h-5 text-primary-600" />
            </div>
            <div>
              <p className="text-sm font-semibold text-primary-700">
                Next: {nextStep.label}
              </p>
              <p className="text-xs text-primary-500">{nextStep.description}</p>
            </div>
          </div>
          <ChevronRight className="w-5 h-5 text-primary-400 group-hover:translate-x-1 transition-transform" />
        </Link>
      )}
    </div>
  );
}
