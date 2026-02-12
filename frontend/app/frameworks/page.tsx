'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { Layers, Plus, RefreshCw, Settings, ChevronRight, AlertTriangle } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent, PageHeader } from '@/components/ui';
import { LoadingPage, ErrorMessage } from '@/components/ui';
import { Button } from '@/components/ui/Button';
import { listFrameworks, loadBuiltinFrameworks } from '@/lib/api';
import { Framework } from '@/lib/types';
import { cn } from '@/lib/utils';

const frameworkTypeColors: Record<string, string> = {
  nist_csf: 'from-blue-500 to-blue-600',
  iso_27001: 'from-green-500 to-green-600',
  soc2_tsc: 'from-purple-500 to-purple-600',
  custom: 'from-orange-500 to-orange-600',
};

const frameworkTypeLabels: Record<string, string> = {
  nist_csf: 'NIST CSF',
  iso_27001: 'ISO 27001',
  soc2_tsc: 'SOC 2',
  custom: 'Custom',
};

export default function FrameworksPage() {
  const [frameworks, setFrameworks] = useState<Framework[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [loadingBuiltin, setLoadingBuiltin] = useState(false);

  const fetchFrameworks = async () => {
    try {
      setLoading(true);
      const data = await listFrameworks();
      setFrameworks(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load frameworks');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchFrameworks();
  }, []);

  const handleLoadBuiltin = async () => {
    const confirmed = window.confirm(
      'This will reload all built-in frameworks from their source definitions. '
      + 'Existing requirements will be deleted and recreated, which will clear any '
      + 'crosswalks, clusters, and requirement mappings linked to them.\n\n'
      + 'Continue?'
    );
    if (!confirmed) return;

    try {
      setLoadingBuiltin(true);
      await loadBuiltinFrameworks(undefined, true);
      await fetchFrameworks();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load built-in frameworks');
    } finally {
      setLoadingBuiltin(false);
    }
  };

  const handleInitialLoad = async () => {
    try {
      setLoadingBuiltin(true);
      await loadBuiltinFrameworks();
      await fetchFrameworks();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load built-in frameworks');
    } finally {
      setLoadingBuiltin(false);
    }
  };

  if (loading) {
    return <LoadingPage message="Loading compliance frameworks..." />;
  }

  if (error) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <ErrorMessage message={error} />
      </div>
    );
  }

  const activeFrameworks = frameworks.filter(f => f.is_active);
  const inactiveFrameworks = frameworks.filter(f => !f.is_active);

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <PageHeader
        title="Compliance Frameworks"
        description="Manage and explore compliance frameworks for your assessments"
        icon={Layers}
        actions={
          <Link href="/frameworks/new">
            <Button>
              <Plus className="w-4 h-4 mr-2" />
              Custom Framework
            </Button>
          </Link>
        }
      />

      {/* Summary Stats */}
      <Card className="mb-8 animate-fadeIn">
        <CardContent>
          <div className="grid grid-cols-4 gap-6 text-center">
            <div className="p-4 rounded-xl bg-gradient-to-br from-primary-50 to-primary-100 border border-primary-200">
              <p className="text-4xl font-bold gradient-text">{frameworks.length}</p>
              <p className="text-sm text-neutral-600 mt-1">Total Frameworks</p>
            </div>
            <div className="p-4 rounded-xl bg-gradient-to-br from-blue-50 to-blue-100 border border-blue-200">
              <p className="text-4xl font-bold text-blue-600">
                {frameworks.filter(f => f.framework_type === 'nist_csf').length}
              </p>
              <p className="text-sm text-neutral-600 mt-1">NIST CSF</p>
            </div>
            <div className="p-4 rounded-xl bg-gradient-to-br from-green-50 to-green-100 border border-green-200">
              <p className="text-4xl font-bold text-green-600">
                {frameworks.filter(f => f.framework_type === 'iso_27001').length}
              </p>
              <p className="text-sm text-neutral-600 mt-1">ISO 27001</p>
            </div>
            <div className="p-4 rounded-xl bg-gradient-to-br from-purple-50 to-purple-100 border border-purple-200">
              <p className="text-4xl font-bold text-purple-600">
                {frameworks.filter(f => f.framework_type === 'soc2_tsc').length}
              </p>
              <p className="text-sm text-neutral-600 mt-1">SOC 2</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Active Frameworks */}
      <div className="mb-8">
        <h2 className="text-lg font-semibold text-neutral-900 mb-4">Active Frameworks</h2>
        {activeFrameworks.length === 0 ? (
          <Card>
            <CardContent className="text-center py-12">
              <Layers className="w-12 h-12 text-neutral-300 mx-auto mb-4" />
              <p className="text-neutral-500 mb-4">No frameworks loaded yet</p>
              <Button onClick={handleInitialLoad} disabled={loadingBuiltin}>
                <RefreshCw className={cn('w-4 h-4 mr-2', loadingBuiltin && 'animate-spin')} />
                Load Built-in Frameworks
              </Button>
            </CardContent>
          </Card>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {activeFrameworks.map((framework, index) => (
              <Link key={framework.id} href={`/frameworks/${framework.id}`}>
                <Card
                  className="h-full hover:shadow-lg transition-all cursor-pointer animate-slideInUp opacity-0"
                  style={{
                    animationDelay: `${index * 100}ms`,
                    animationFillMode: 'forwards',
                  }}
                >
                  <CardHeader>
                    <div className="flex items-center justify-between">
                      <span
                        className={cn(
                          'px-3 py-1 text-white text-xs font-semibold rounded-full bg-gradient-to-r',
                          frameworkTypeColors[framework.framework_type] || frameworkTypeColors.custom
                        )}
                      >
                        {frameworkTypeLabels[framework.framework_type] || 'Custom'}
                      </span>
                      {framework.is_builtin && (
                        <span className="px-2 py-0.5 text-xs text-neutral-500 bg-neutral-100 rounded">
                          Built-in
                        </span>
                      )}
                    </div>
                    <CardTitle className="mt-3">{framework.name}</CardTitle>
                    <p className="text-sm text-neutral-500">Version {framework.version}</p>
                  </CardHeader>
                  <CardContent>
                    {framework.description && (
                      <p className="text-sm text-neutral-600 line-clamp-2 mb-4">
                        {framework.description}
                      </p>
                    )}
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-neutral-500">
                        {framework.hierarchy_levels} level{framework.hierarchy_levels !== 1 ? 's' : ''}
                      </span>
                      <span className="text-primary-600 flex items-center">
                        View details <ChevronRight className="w-4 h-4 ml-1" />
                      </span>
                    </div>
                  </CardContent>
                </Card>
              </Link>
            ))}
          </div>
        )}
      </div>

      {/* Inactive Frameworks */}
      {inactiveFrameworks.length > 0 && (
        <div>
          <h2 className="text-lg font-semibold text-neutral-900 mb-4">Inactive Frameworks</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {inactiveFrameworks.map((framework) => (
              <Link key={framework.id} href={`/frameworks/${framework.id}`}>
                <Card className="h-full hover:shadow-lg transition-all cursor-pointer opacity-60">
                  <CardHeader>
                    <div className="flex items-center justify-between">
                      <span className="px-3 py-1 text-neutral-500 text-xs font-semibold rounded-full bg-neutral-200">
                        {frameworkTypeLabels[framework.framework_type] || 'Custom'}
                      </span>
                      <span className="px-2 py-0.5 text-xs text-neutral-500 bg-neutral-100 rounded">
                        Inactive
                      </span>
                    </div>
                    <CardTitle className="mt-3 text-neutral-500">{framework.name}</CardTitle>
                  </CardHeader>
                </Card>
              </Link>
            ))}
          </div>
        </div>
      )}

      {/* Quick Links */}
      <Card className="mt-8">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Settings className="w-5 h-5" />
            Framework Tools
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Link href="/frameworks/crosswalks">
              <div className="p-4 rounded-xl border border-neutral-200 hover:border-primary-300 hover:bg-primary-50 transition-all cursor-pointer">
                <h3 className="font-medium text-neutral-900">Cross-Framework Mappings</h3>
                <p className="text-sm text-neutral-500 mt-1">
                  View and manage requirement mappings between frameworks
                </p>
              </div>
            </Link>
            <Link href="/frameworks/clusters">
              <div className="p-4 rounded-xl border border-neutral-200 hover:border-accent-300 hover:bg-accent-50 transition-all cursor-pointer">
                <h3 className="font-medium text-neutral-900">Requirement Clusters</h3>
                <p className="text-sm text-neutral-500 mt-1">
                  AI-powered clustering to reduce interview burden
                </p>
              </div>
            </Link>
            <Link href="/frameworks/settings">
              <div className="p-4 rounded-xl border border-neutral-200 hover:border-purple-300 hover:bg-purple-50 transition-all cursor-pointer">
                <h3 className="font-medium text-neutral-900">Company Frameworks</h3>
                <p className="text-sm text-neutral-500 mt-1">
                  Configure which frameworks your organization uses
                </p>
              </div>
            </Link>
          </div>
        </CardContent>
      </Card>

      {/* Danger Zone */}
      <Card className="mt-8 border-red-200">
        <CardContent>
          <div className="flex items-center justify-between gap-4">
            <div className="flex items-start gap-3">
              <AlertTriangle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
              <div>
                <h3 className="font-medium text-neutral-900">Reload Built-in Frameworks</h3>
                <p className="text-sm text-neutral-500 mt-1">
                  Deletes and reloads all built-in framework requirements from source files.
                  This will clear any crosswalks, clusters, and requirement mappings linked to them.
                </p>
              </div>
            </div>
            <Button
              variant="ghost"
              className="border border-red-300 text-red-600 hover:bg-red-50 hover:text-red-700 flex-shrink-0"
              onClick={handleLoadBuiltin}
              disabled={loadingBuiltin}
            >
              <RefreshCw className={cn('w-4 h-4 mr-2', loadingBuiltin && 'animate-spin')} />
              {loadingBuiltin ? 'Reloading...' : 'Reload'}
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
