'use client';

import { useState, useEffect, use } from 'react';
import Link from 'next/link';
import {
  FileText,
  Link2,
  MessageSquare,
  BarChart3,
  ArrowUpRight,
  TrendingUp,
  Layers,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui';
import { LoadingSpinner } from '@/components/ui';
import { getAssessment, listPolicies, listSessions, getScoreSummary, getAssessmentScope, listFrameworks } from '@/lib/api';
import { useUserId } from '@/lib/hooks/useUserId';
import { Assessment, AssessmentScope, Framework } from '@/lib/types';
import { WorkflowStepper } from '@/components/assessment/WorkflowStepper';
import { cn } from '@/lib/utils';

interface OverviewPageProps {
  params: Promise<{ id: string }>;
}

interface Stats {
  policies: number;
  interviews: number;
  overallScore: number | null;
}

interface FrameworkInfo {
  id: string;
  code: string;
  name: string;
  framework_type: string;
}

const statConfig = [
  {
    name: 'Policies',
    icon: FileText,
    gradient: 'from-accent-500 to-accent-600',
    bgGradient: 'from-accent-50 to-accent-100',
    textColor: 'text-accent-600'
  },
  {
    name: 'Interviews',
    icon: MessageSquare,
    gradient: 'from-purple-500 to-purple-600',
    bgGradient: 'from-purple-50 to-purple-100',
    textColor: 'text-purple-600'
  },
  {
    name: 'Maturity Score',
    icon: BarChart3,
    gradient: 'from-amber-500 to-amber-600',
    bgGradient: 'from-amber-50 to-amber-100',
    textColor: 'text-amber-600'
  },
];

export default function AssessmentOverviewPage({ params }: OverviewPageProps) {
  const { id } = use(params);
  const userId = useUserId();
  const [assessment, setAssessment] = useState<Assessment | null>(null);
  const [stats, setStats] = useState<Stats>({
    policies: 0,
    interviews: 0,
    overallScore: null,
  });
  const [frameworksInScope, setFrameworksInScope] = useState<FrameworkInfo[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!userId) return;

    const fetchData = async () => {
      try {
        const [assessmentData, policies, sessions] = await Promise.all([
          getAssessment(id, userId),
          listPolicies(id, userId).catch(() => []),
          listSessions(id, userId).catch(() => []),
        ]);

        setAssessment(assessmentData);

        let overallScore = null;
        try {
          const scoreSummary = await getScoreSummary(id, userId);
          overallScore = scoreSummary.overall_maturity;
        } catch {
          // Scores may not be calculated yet
        }

        // Fetch framework scope
        try {
          const [scope, allFrameworks] = await Promise.all([
            getAssessmentScope(id),
            listFrameworks(),
          ]);
          const frameworkIds = scope.map((s) => s.framework_id);
          const scopedFrameworks = allFrameworks
            .filter((f) => frameworkIds.includes(f.id))
            .map((f) => ({
              id: f.id,
              code: f.code,
              name: f.name,
              framework_type: f.framework_type,
            }));
          setFrameworksInScope(scopedFrameworks);
        } catch {
          // Scope may not be set
        }

        setStats({
          policies: policies.length,
          interviews: sessions.length,
          overallScore,
        });
      } catch (err) {
        console.error('Failed to load overview data:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [id, userId]);

  if (loading) {
    return (
      <div className="flex justify-center py-12">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  const statCards = [
    { ...statConfig[0], value: stats.policies, href: `/assessments/${id}/policies` },
    { ...statConfig[1], value: stats.interviews, href: `/assessments/${id}/interviews` },
    {
      ...statConfig[2],
      value: stats.overallScore !== null ? stats.overallScore.toFixed(1) : '-',
      href: `/assessments/${id}/scores`,
      suffix: stats.overallScore !== null ? '/4.0' : '',
    },
  ];

  const quickActions = [
    {
      title: 'Upload Policies',
      description: 'PDF, DOCX, TXT, MD',
      href: `/assessments/${id}/policies`,
      icon: FileText,
      gradient: 'from-accent-500 to-accent-600',
      bgGradient: 'from-accent-50 to-accent-100',
    },
    {
      title: 'Generate Mappings',
      description: 'AI-powered analysis',
      href: `/assessments/${id}/mappings`,
      icon: Link2,
      gradient: 'from-purple-500 to-purple-600',
      bgGradient: 'from-purple-50 to-purple-100',
    },
    {
      title: 'Start Interview',
      description: 'Guided questionnaire',
      href: `/assessments/${id}/interviews`,
      icon: MessageSquare,
      gradient: 'from-orange-500 to-orange-600',
      bgGradient: 'from-orange-50 to-orange-100',
    },
  ];

  return (
    <div className="space-y-8 animate-fadeIn">
      {/* Stats Grid */}
      <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
        {statCards.map((stat, index) => {
          const Icon = stat.icon;
          return (
            <Link key={stat.name} href={stat.href}>
              <Card
                hover
                glow
                className="h-full animate-slideInUp opacity-0"
                style={{
                  animationDelay: `${index * 100}ms`,
                  animationFillMode: 'forwards'
                }}
              >
                <CardContent className="pt-5">
                  <div className="flex items-start justify-between">
                    <div className={cn(
                      'p-3 rounded-xl bg-gradient-to-br',
                      stat.bgGradient
                    )}>
                      <Icon className={cn('h-6 w-6', stat.textColor)} />
                    </div>
                    <ArrowUpRight className="h-4 w-4 text-neutral-400" />
                  </div>
                  <div className="mt-4">
                    <p className="text-sm font-medium text-neutral-500">{stat.name}</p>
                    <p className="mt-1 flex items-baseline gap-1">
                      <span className="text-3xl font-bold gradient-text">{stat.value}</span>
                      {'suffix' in stat && stat.suffix && (
                        <span className="text-lg text-neutral-400">{stat.suffix}</span>
                      )}
                    </p>
                  </div>
                </CardContent>
              </Card>
            </Link>
          );
        })}
      </div>

      {/* Workflow Progress */}
      {userId && (
        <Card animated>
          <CardHeader variant="gradient">
            <CardTitle icon={<TrendingUp className="h-5 w-5" />}>
              Assessment Workflow
            </CardTitle>
          </CardHeader>
          <CardContent>
            <WorkflowStepper assessmentId={id} userId={userId} />
          </CardContent>
        </Card>
      )}

      {/* Frameworks in Scope */}
      {frameworksInScope.length > 0 && (
        <Card animated>
          <CardHeader variant="gradient">
            <CardTitle icon={<Layers className="h-5 w-5" />}>
              Frameworks in Scope ({frameworksInScope.length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-3">
              {frameworksInScope.map((framework) => {
                const typeColors: Record<string, string> = {
                  nist_csf: 'bg-blue-100 text-blue-700 border-blue-200',
                  iso_27001: 'bg-green-100 text-green-700 border-green-200',
                  soc2_tsc: 'bg-purple-100 text-purple-700 border-purple-200',
                  custom: 'bg-orange-100 text-orange-700 border-orange-200',
                };
                return (
                  <Link
                    key={framework.id}
                    href={`/frameworks/${framework.id}`}
                    className={cn(
                      'px-4 py-2 rounded-lg border text-sm font-medium transition-all hover:shadow-md',
                      typeColors[framework.framework_type] || typeColors.custom
                    )}
                  >
                    {framework.name}
                  </Link>
                );
              })}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Description */}
      {assessment?.description && (
        <Card animated>
          <CardHeader variant="gradient">
            <CardTitle icon={<TrendingUp className="h-5 w-5" />}>
              Description
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-neutral-700 leading-relaxed">{assessment.description}</p>
          </CardContent>
        </Card>
      )}

      {/* Quick Actions */}
      <Card animated>
        <CardHeader variant="gradient">
          <CardTitle>Quick Actions</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {quickActions.map((action, index) => {
              const Icon = action.icon;
              return (
                <Link
                  key={action.title}
                  href={action.href}
                  className={cn(
                    'flex items-center gap-4 p-4 rounded-xl',
                    'bg-neutral-50 hover:bg-white',
                    'border border-transparent hover:border-neutral-200',
                    'hover:shadow-lg',
                    'transition-all duration-300',
                    'group animate-slideInUp opacity-0'
                  )}
                  style={{
                    animationDelay: `${(index + 4) * 75}ms`,
                    animationFillMode: 'forwards'
                  }}
                >
                  <div className={cn(
                    'flex-shrink-0 w-12 h-12 rounded-xl flex items-center justify-center',
                    'bg-gradient-to-br',
                    action.bgGradient,
                    'group-hover:scale-110 transition-transform duration-300'
                  )}>
                    <Icon className={cn(
                      'w-6 h-6',
                      `bg-gradient-to-r ${action.gradient} bg-clip-text`
                    )} style={{ color: 'var(--primary-600)' }} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-semibold text-neutral-900 group-hover:text-primary-600 transition-colors">
                      {action.title}
                    </p>
                    <p className="text-xs text-neutral-500">{action.description}</p>
                  </div>
                  <ArrowUpRight className="h-4 w-4 text-neutral-300 group-hover:text-primary-500 group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-all" />
                </Link>
              );
            })}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
