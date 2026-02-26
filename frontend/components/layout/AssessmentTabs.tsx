'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  Home,
  Building2,
  FileText,
  Link2,
  MessageSquare,
  BarChart3,
  AlertTriangle,
  FileDown,
  Layers,
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface AssessmentTabsProps {
  assessmentId: string;
}

const tabs = [
  { name: 'Overview', path: '', icon: Home },
  { name: 'Company Profile', path: '/company-profile', icon: Building2 },
  { name: 'Scope', path: '/scope', icon: Layers },
  { name: 'Policies', path: '/policies', icon: FileText },
  { name: 'Mappings', path: '/mappings', icon: Link2 },
  { name: 'Interviews', path: '/interviews', icon: MessageSquare },
  { name: 'Scores', path: '/scores', icon: BarChart3 },
  { name: 'Deviations', path: '/deviations', icon: AlertTriangle },
  { name: 'Reports', path: '/reports', icon: FileDown },
];

export function AssessmentTabs({ assessmentId }: AssessmentTabsProps) {
  const pathname = usePathname();
  const basePath = `/assessments/${assessmentId}`;

  return (
    <div className="border-b border-neutral-200 bg-white">
      <nav className="-mb-px flex space-x-1 overflow-x-auto px-1 py-2" aria-label="Tabs">
        {tabs.map((tab) => {
          const href = `${basePath}${tab.path}`;
          const isActive = tab.path === ''
            ? pathname === basePath
            : pathname.startsWith(href);
          const Icon = tab.icon;

          return (
            <Link
              key={tab.name}
              href={href}
              className={cn(
                'relative inline-flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium',
                'transition-all duration-200 whitespace-nowrap group',
                isActive
                  ? 'bg-gradient-to-r from-primary-500 to-primary-600 text-white shadow-md'
                  : 'text-neutral-600 hover:bg-gradient-to-r hover:from-slate-50 hover:to-slate-100 hover:text-neutral-900'
              )}
            >
              <Icon className={cn(
                'h-4 w-4 transition-transform duration-200',
                !isActive && 'group-hover:scale-110'
              )} />
              {tab.name}
              {isActive && (
                <span className="absolute -bottom-2.5 left-1/2 -translate-x-1/2 w-8 h-0.5 bg-gradient-to-r from-primary-400 to-accent-400 rounded-full" />
              )}
            </Link>
          );
        })}
      </nav>
    </div>
  );
}
