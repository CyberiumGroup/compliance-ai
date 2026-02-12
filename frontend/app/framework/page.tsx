'use client';

import { useState, useEffect } from 'react';
import { BookOpen, ChevronDown } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent, PageHeader } from '@/components/ui';
import { LoadingPage, ErrorMessage } from '@/components/ui';
import { getCSFFunctions, getFrameworkSummary } from '@/lib/api';
import { useUserId } from '@/lib/hooks/useUserId';
import { CSFFunction, FrameworkSummary } from '@/lib/types';
import { cn } from '@/lib/utils';

export default function FrameworkPage() {
  const userId = useUserId();
  const [functions, setFunctions] = useState<CSFFunction[]>([]);
  const [summary, setSummary] = useState<FrameworkSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedFunction, setExpandedFunction] = useState<string | null>(null);
  const [expandedCategory, setExpandedCategory] = useState<string | null>(null);

  useEffect(() => {
    if (!userId) return;

    const fetchFramework = async () => {
      try {
        const [functionsData, summaryData] = await Promise.all([
          getCSFFunctions(userId),
          getFrameworkSummary(userId),
        ]);
        setFunctions(functionsData);
        setSummary(summaryData);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load framework');
      } finally {
        setLoading(false);
      }
    };

    fetchFramework();
  }, [userId]);

  if (!userId || loading) {
    return <LoadingPage message="Loading framework data..." />;
  }

  if (error) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <ErrorMessage message={error} />
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <PageHeader
        title="NIST CSF 2.0 Reference"
        description="Reference view for NIST CSF 2.0 functions, categories, and subcategories"
        icon={BookOpen}
      />

      {summary && (
        <Card className="mb-8 animate-fadeIn">
          <CardContent>
            <div className="grid grid-cols-3 gap-6 text-center">
              <div className="p-4 rounded-xl bg-gradient-to-br from-primary-50 to-primary-100 border border-primary-200">
                <p className="text-4xl font-bold gradient-text">{summary.functions_count}</p>
                <p className="text-sm text-neutral-600 mt-1">Functions</p>
              </div>
              <div className="p-4 rounded-xl bg-gradient-to-br from-accent-50 to-accent-100 border border-accent-200">
                <p className="text-4xl font-bold text-accent-600">{summary.categories_count}</p>
                <p className="text-sm text-neutral-600 mt-1">Categories</p>
              </div>
              <div className="p-4 rounded-xl bg-gradient-to-br from-purple-50 to-purple-100 border border-purple-200">
                <p className="text-4xl font-bold text-purple-600">{summary.subcategories_count}</p>
                <p className="text-sm text-neutral-600 mt-1">Subcategories</p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      <div className="space-y-4">
        {functions.map((func, index) => (
          <Card
            key={func.id}
            className="animate-slideInUp opacity-0 overflow-hidden"
            style={{
              animationDelay: `${index * 100}ms`,
              animationFillMode: 'forwards'
            }}
          >
            <CardHeader
              className="cursor-pointer hover:bg-neutral-50 transition-colors"
              onClick={() => setExpandedFunction(expandedFunction === func.id ? null : func.id)}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <span className="px-3 py-1.5 bg-gradient-to-r from-primary-500 to-primary-600 text-white font-bold rounded-lg text-sm">
                    {func.code}
                  </span>
                  <CardTitle>{func.name}</CardTitle>
                </div>
                <ChevronDown
                  className={cn(
                    'w-5 h-5 text-neutral-400 transition-transform duration-300',
                    expandedFunction === func.id && 'rotate-180'
                  )}
                />
              </div>
              {func.description && (
                <p className="text-sm text-neutral-500 mt-2 ml-14">{func.description}</p>
              )}
            </CardHeader>

            {expandedFunction === func.id && func.categories && (
              <CardContent className="bg-neutral-50/50 border-t border-neutral-100">
                <div className="space-y-3">
                  {func.categories.map((category) => (
                    <div key={category.id} className="bg-white rounded-xl border border-neutral-200 overflow-hidden">
                      <div
                        className="p-4 cursor-pointer hover:bg-neutral-50 transition-colors"
                        onClick={() =>
                          setExpandedCategory(expandedCategory === category.id ? null : category.id)
                        }
                      >
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-3">
                            <span className="px-2.5 py-1 bg-gradient-to-r from-accent-500 to-accent-600 text-white text-sm font-medium rounded-lg">
                              {category.code}
                            </span>
                            <span className="font-medium text-neutral-900">{category.name}</span>
                          </div>
                          <ChevronDown
                            className={cn(
                              'w-4 h-4 text-neutral-400 transition-transform duration-300',
                              expandedCategory === category.id && 'rotate-180'
                            )}
                          />
                        </div>
                      </div>

                      {expandedCategory === category.id && category.subcategories && (
                        <div className="border-t border-neutral-200 bg-neutral-50 p-4">
                          <div className="space-y-2">
                            {category.subcategories.map((subcategory, subIndex) => (
                              <div
                                key={subcategory.id}
                                className="p-3 bg-white rounded-lg border border-neutral-200 text-sm animate-fadeIn"
                                style={{
                                  animationDelay: `${subIndex * 50}ms`
                                }}
                              >
                                <span className="font-semibold text-purple-600">
                                  {subcategory.code}
                                </span>
                                <p className="text-neutral-600 mt-1">{subcategory.description}</p>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </CardContent>
            )}
          </Card>
        ))}
      </div>
    </div>
  );
}
