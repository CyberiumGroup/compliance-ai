'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { ChevronLeft, ChevronRight } from 'lucide-react';

interface StepNavProps {
  assessmentId: string;
}

interface StepDef {
  path: string;
  label: string;
  prevPrompt: string;
  nextPrompt: string;
}

const STEPS: StepDef[] = [
  {
    path: '/context',
    label: 'Context',
    prevPrompt: 'Need to update your context?',
    nextPrompt: 'Ready to define your compliance scope?',
  },
  {
    path: '/scope',
    label: 'Scope',
    prevPrompt: 'Need to adjust your scope?',
    nextPrompt: 'Ready to start uploading evidence?',
  },
  {
    path: '/evidence',
    label: 'Evidence',
    prevPrompt: 'Need to add more evidence?',
    nextPrompt: 'Ready to generate your mappings?',
  },
  {
    path: '/verification',
    label: 'Verification',
    prevPrompt: 'Need to review your mappings?',
    nextPrompt: 'Ready to run your evaluation?',
  },
  {
    path: '/evaluation',
    label: 'Evaluation',
    prevPrompt: 'Need to adjust your evaluation?',
    nextPrompt: 'Ready to generate your report?',
  },
  {
    path: '/reports',
    label: 'Reports',
    prevPrompt: '',
    nextPrompt: '',
  },
];

export function StepNav({ assessmentId }: StepNavProps) {
  const pathname = usePathname();
  const basePath = `/assessments/${assessmentId}`;

  const currentIndex = STEPS.findIndex((s) => pathname.startsWith(`${basePath}${s.path}`));
  if (currentIndex === -1) return null;

  const prev = currentIndex > 0 ? STEPS[currentIndex - 1] : null;
  const next = currentIndex < STEPS.length - 1 ? STEPS[currentIndex + 1] : null;

  if (!prev && !next) return null;

  return (
    <div className="fixed bottom-0 left-0 right-0 z-20 border-t border-neutral-200 bg-white/95 backdrop-blur-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3 flex items-stretch gap-3">

        {prev ? (
          <Link
            href={`${basePath}${prev.path}`}
            className="flex items-center gap-3 rounded-lg border border-neutral-200 bg-white px-4 py-2.5 transition-all duration-150 group hover:border-neutral-300 hover:shadow-sm"
          >
            <ChevronLeft className="h-4 w-4 text-neutral-400 flex-shrink-0 group-hover:-translate-x-0.5 transition-transform" />
            <div className="min-w-0">
              <p className="text-[10px] uppercase tracking-wider font-semibold text-neutral-400 leading-none mb-0.5">
                {STEPS[currentIndex - 1].prevPrompt}
              </p>
              <p className="text-sm font-semibold text-neutral-700">{prev.label}</p>
            </div>
          </Link>
        ) : (
          <div />
        )}

        {next && (
          <Link
            href={`${basePath}${next.path}`}
            className="flex items-center gap-3 rounded-lg border border-primary-200 bg-primary-50/60 px-4 py-2.5 transition-all duration-150 group hover:border-primary-300 hover:bg-primary-50 hover:shadow-sm ml-auto"
          >
            <div className="min-w-0 text-right">
              <p className="text-[10px] uppercase tracking-wider font-semibold text-primary-400 leading-none mb-0.5">
                {STEPS[currentIndex].nextPrompt}
              </p>
              <p className="text-sm font-semibold text-primary-700">{next.label}</p>
            </div>
            <ChevronRight className="h-4 w-4 text-primary-400 flex-shrink-0 group-hover:translate-x-0.5 transition-transform" />
          </Link>
        )}

      </div>
    </div>
  );
}
