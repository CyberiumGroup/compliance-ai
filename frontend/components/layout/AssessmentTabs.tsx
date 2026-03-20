'use client';

import { Fragment } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  Building2,
  FileText,
  Link2,
  BarChart3,
  FileDown,
  Layers,
  ChevronRight,
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface AssessmentTabsProps {
  assessmentId: string;
  className?: string;
}

const tabs = [
  { name: 'Context',    path: '/context',    icon: Building2 },
  { name: 'Scope',      path: '/scope',       icon: Layers    },
  { name: 'Evidence',   path: '/evidence',    icon: FileText  },
  { name: 'Evaluation', path: '/evaluation',  icon: BarChart3 },
  { name: 'Reports',    path: '/reports',     icon: FileDown  },
];

export function AssessmentTabs({ assessmentId, className }: AssessmentTabsProps) {
  const pathname = usePathname();
  const basePath = `/assessments/${assessmentId}`;

  return (
    <nav
      className={cn(
        'flex items-center gap-1 overflow-x-auto [&::-webkit-scrollbar]:hidden [-ms-overflow-style:none] [scrollbar-width:none]',
        className
      )}
      aria-label="Assessment sections"
    >
      {tabs.map((tab, index) => {
        const href = `${basePath}${tab.path}`;
        const isActive = pathname.startsWith(href);
        const Icon = tab.icon;

        return (
          <Fragment key={tab.name}>
            <Link
              href={href}
              className={cn(
                'inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-md border text-xs font-medium whitespace-nowrap transition-all duration-150 flex-shrink-0',
                isActive
                  ? 'bg-primary-50 border-primary-300 text-primary-700'
                  : 'bg-white border-neutral-200 text-neutral-500 hover:border-neutral-300 hover:text-neutral-700 hover:bg-neutral-50'
              )}
            >
              <Icon className="h-3 w-3 flex-shrink-0" />
              {tab.name}
            </Link>
            {index < tabs.length - 1 && (
              <ChevronRight className="h-3 w-3 text-neutral-300 flex-shrink-0" />
            )}
          </Fragment>
        );
      })}
    </nav>
  );
}
