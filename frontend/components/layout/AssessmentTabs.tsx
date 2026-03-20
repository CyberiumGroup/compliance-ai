'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  Building2,
  FileText,
  Link2,
  BarChart3,
  FileDown,
  Layers,
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface AssessmentTabsProps {
  assessmentId: string;
  className?: string;
}

const tabs = [
  { name: 'Context',      path: '/context',      icon: Building2 },
  { name: 'Scope',        path: '/scope',         icon: Layers    },
  { name: 'Evidence',     path: '/evidence',      icon: FileText  },
  { name: 'Verification', path: '/verification',  icon: Link2     },
  { name: 'Evaluation',   path: '/evaluation',    icon: BarChart3 },
  { name: 'Reports',      path: '/reports',       icon: FileDown  },
];

export function AssessmentTabs({ assessmentId, className }: AssessmentTabsProps) {
  const pathname = usePathname();
  const basePath = `/assessments/${assessmentId}`;

  return (
    <nav
      className={cn('flex gap-0 overflow-x-auto [&::-webkit-scrollbar]:hidden [-ms-overflow-style:none] [scrollbar-width:none]', className)}
      aria-label="Assessment sections"
    >
      {tabs.map((tab) => {
        const href = `${basePath}${tab.path}`;
        const isActive = pathname.startsWith(href);
        const Icon = tab.icon;

        return (
          <Link
            key={tab.name}
            href={href}
            className={cn(
              'inline-flex items-center gap-2 px-4 py-3 text-sm font-medium whitespace-nowrap',
              'border-b-2 -mb-px transition-colors duration-150',
              isActive
                ? 'border-primary-600 text-primary-700'
                : 'border-transparent text-neutral-500 hover:text-neutral-800 hover:border-neutral-300'
            )}
          >
            <Icon className="h-3.5 w-3.5 flex-shrink-0" />
            {tab.name}
          </Link>
        );
      })}
    </nav>
  );
}
