'use client';

import { Fragment, useState, useEffect } from 'react';
import Link from 'next/link';
import {
  Building2,
  Layers,
  Upload,
  BarChart3,
  FileText,
  ChevronRight,
  ArrowRight,
  Loader2,
} from 'lucide-react';
import {
  getAssessment,
  getAssessmentScope,
  listPolicies,
  getScoreSummary,
  listReports,
} from '@/lib/api';

interface WorkflowStepperProps {
  assessmentId: string;
  userId: string;
}

type StepStatus = 'not_started' | 'in_progress' | 'complete';

interface StepMetric {
  value: string | number;
  label: string;
}

interface WorkflowStep {
  id: string;
  label: string;
  description: string;
  cta: string;
  icon: React.ElementType;
  href: string;
  status: StepStatus;
  optional?: boolean;
  metric?: StepMetric | null;
}

// ─── Pipeline step card ────────────────────────────────────────────────────────

function StepCard({ step, stepNumber }: { step: WorkflowStep; stepNumber: number }) {
  const Icon = step.icon;

  return (
    <Link
      href={step.href}
      className="flex-1 min-w-0 flex flex-col rounded-lg border border-neutral-200 bg-white p-4 transition-all duration-200 group hover:shadow-md hover:-translate-y-0.5 hover:border-primary-300"
    >
      {/* Step number / optional badge */}
      <div className="flex items-center justify-between mb-3">
        <span className="text-[11px] font-mono text-neutral-400">
          {String(stepNumber).padStart(2, '0')}
        </span>
        {step.optional && (
          <span className="text-[10px] font-medium text-neutral-400 bg-neutral-100 px-1.5 py-0.5 rounded">
            optional
          </span>
        )}
      </div>

      {/* Icon */}
      <div className="w-8 h-8 rounded-md border bg-primary-50 border-primary-200 flex items-center justify-center mb-3 flex-shrink-0">
        <Icon className="h-4 w-4 text-primary-600" />
      </div>

      {/* Label + description */}
      <p className="text-sm font-semibold text-neutral-900 mb-1">{step.label}</p>
      <p className="text-xs text-neutral-500 leading-relaxed flex-1">{step.description}</p>

      {/* Metric */}
      {step.metric != null && (
        <div className="mt-3">
          <span className="text-xl font-bold tabular-nums text-neutral-900">{step.metric.value}</span>
          <span className="text-xs text-neutral-400 ml-1.5">{step.metric.label}</span>
        </div>
      )}

      {/* CTA */}
      <div className="mt-3 flex items-center gap-1 text-xs font-semibold text-primary-600 group-hover:text-primary-700 transition-colors">
        {step.cta}
        <ArrowRight className="h-3 w-3 group-hover:translate-x-0.5 transition-transform" />
      </div>
    </Link>
  );
}

// ─── WorkflowStepper ──────────────────────────────────────────────────────────

export function WorkflowStepper({ assessmentId, userId }: WorkflowStepperProps) {
  const [steps, setSteps] = useState<WorkflowStep[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const checkProgress = async () => {
      try {
        const [assessment, scope, policies, reports] = await Promise.all([
          getAssessment(assessmentId, userId).catch(() => null),
          getAssessmentScope(assessmentId).catch(() => []),
          listPolicies(assessmentId, userId).catch(() => []),
          listReports(assessmentId, userId).catch(() => ({ items: [] })),
        ]);

        let scoreSummary: { overall_maturity: number } | null = null;
        try {
          scoreSummary = await getScoreSummary(assessmentId, userId);
        } catch {
          // not yet scored
        }

        const hasContext = !!(assessment?.business_description || assessment?.industry);
        const hasScope = scope.length > 0;
        const hasScores = scoreSummary !== null;
        const hasReports = reports.items.length > 0;

        const s = (done: boolean, partial: boolean): StepStatus =>
          done ? 'complete' : partial ? 'in_progress' : 'not_started';

        setSteps([
          {
            id: 'context',
            label: 'Context',
            description: 'Describe your organisation, industry, and relevant risk factors.',
            cta: hasContext ? 'Edit context' : 'Add context',
            icon: Building2,
            href: `/assessments/${assessmentId}/context`,
            status: s(hasContext, false),
            metric: null,
          },
          {
            id: 'scope',
            label: 'Scope',
            description: 'Select the compliance frameworks and level of depth applicable to this assessment.',
            cta: hasScope ? 'Edit scope' : 'Set scope',
            icon: Layers,
            href: `/assessments/${assessmentId}/scope`,
            status: s(hasScope, false),
            metric: hasScope ? { value: scope.length, label: scope.length === 1 ? 'framework' : 'frameworks' } : null,
          },
          {
            id: 'evidence',
            label: 'Evidence',
            description: 'Upload policies, processes, controls, interviews, and proof documents.',
            cta: policies.length > 0 ? 'Manage evidence' : 'Upload evidence',
            icon: Upload,
            href: `/assessments/${assessmentId}/evidence`,
            status: s(policies.length > 0, false),
            metric: policies.length > 0 ? { value: policies.length, label: policies.length === 1 ? 'document' : 'documents' } : null,
          },
          {
            id: 'evaluation',
            label: 'Evaluation',
            description: 'Run AI scoring to calculate coverage and adequacy scores across all requirements.',
            cta: hasScores ? 'View scores' : 'Run evaluation',
            icon: BarChart3,
            href: `/assessments/${assessmentId}/evaluation`,
            status: s(hasScores, false),
            metric: hasScores ? { value: 'Scored', label: 'view results →' } : null,
          },
          {
            id: 'report',
            label: 'Reports',
            description: 'Generate formatted compliance reports for stakeholders.',
            cta: hasReports ? 'View report' : 'Generate report',
            icon: FileText,
            href: `/assessments/${assessmentId}/reports`,
            status: s(hasReports, false),
            metric: hasReports ? { value: reports.items.length, label: reports.items.length === 1 ? 'report' : 'reports' } : null,
          },
        ]);
      } catch (err) {
        console.error('[WorkflowStepper] Failed to load progress:', err);
      } finally {
        setLoading(false);
      }
    };

    checkProgress();
  }, [assessmentId, userId]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-16">
        <Loader2 className="w-5 h-5 text-primary-500 animate-spin" />
      </div>
    );
  }

  const numberedSteps = steps.map((step, i) => ({ step, stepNumber: i + 1 }));

  return (
    <div className="space-y-8">

      {/* ── Pipeline ─────────────────────────────────────────────── */}
      <div>
        <div className="mb-4">
          <p className="text-xs font-semibold uppercase tracking-wider text-neutral-400">Workflow</p>
          <h2 className="text-lg font-semibold text-neutral-900 mt-0.5">Assessment Pipeline</h2>
        </div>

        {/* Cards — Fragment avoids extra DOM nodes that can break flex layout */}
        <div className="flex items-stretch gap-2">
          {numberedSteps.map(({ step, stepNumber }, index) => (
            <Fragment key={step.id}>
              <StepCard step={step} stepNumber={stepNumber} />
              {index < steps.length - 1 && (
                <div className="flex items-center flex-shrink-0 text-neutral-300">
                  <ChevronRight className="h-4 w-4" />
                </div>
              )}
            </Fragment>
          ))}
        </div>
      </div>

    </div>
  );
}
