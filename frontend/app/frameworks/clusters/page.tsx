'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import {
  Boxes,
  ChevronLeft,
  ChevronDown,
  RefreshCw,
  Trash2,
  BarChart2,
  MessageSquare,
} from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent, PageHeader } from '@/components/ui';
import { LoadingPage, ErrorMessage } from '@/components/ui';
import { Button } from '@/components/ui/Button';
import {
  listClusters,
  getClusterMembers,
  generateClusters,
  deleteClusters,
  estimateInterviewReduction,
  generateEmbeddings,
  getEmbeddingStats,
  listFrameworks,
} from '@/lib/api';
import {
  RequirementCluster,
  ClusterMember,
  ClusterType,
  InterviewReduction,
  EmbeddingStats,
  Framework,
} from '@/lib/types';
import { cn } from '@/lib/utils';

const clusterTypeColors: Record<ClusterType, string> = {
  semantic: 'bg-blue-100 text-blue-700',
  topic: 'bg-purple-100 text-purple-700',
  interview: 'bg-green-100 text-green-700',
};

export default function ClustersPage() {
  const [clusters, setClusters] = useState<RequirementCluster[]>([]);
  const [frameworks, setFrameworks] = useState<Framework[]>([]);
  const [expandedCluster, setExpandedCluster] = useState<string | null>(null);
  const [clusterMembers, setClusterMembers] = useState<Record<string, ClusterMember[]>>({});
  const [interviewReduction, setInterviewReduction] = useState<InterviewReduction | null>(null);
  const [embeddingStats, setEmbeddingStats] = useState<EmbeddingStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [generating, setGenerating] = useState(false);
  const [generatingEmbeddings, setGeneratingEmbeddings] = useState(false);
  const [deleting, setDeleting] = useState(false);

  // Generate form
  const [selectedFrameworks, setSelectedFrameworks] = useState<string[]>([]);
  const [threshold, setThreshold] = useState(0.85);
  const [clusterType, setClusterType] = useState<ClusterType>('semantic');

  const fetchData = async () => {
    try {
      setLoading(true);
      const [clustersData, frameworksData, reductionData, embeddingsData] = await Promise.all([
        listClusters(),
        listFrameworks(),
        estimateInterviewReduction(),
        getEmbeddingStats(),
      ]);
      setClusters(clustersData);
      setFrameworks(frameworksData);
      setInterviewReduction(reductionData);
      setEmbeddingStats(embeddingsData);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load clusters');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleExpandCluster = async (clusterId: string) => {
    if (expandedCluster === clusterId) {
      setExpandedCluster(null);
      return;
    }

    setExpandedCluster(clusterId);

    if (!clusterMembers[clusterId]) {
      try {
        const members = await getClusterMembers(clusterId);
        setClusterMembers((prev) => ({ ...prev, [clusterId]: members }));
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load cluster members');
      }
    }
  };

  const handleGenerateClusters = async () => {
    try {
      setGenerating(true);
      await generateClusters({
        framework_ids: selectedFrameworks.length > 0 ? selectedFrameworks : undefined,
        threshold,
        cluster_type: clusterType,
      });
      await fetchData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to generate clusters');
    } finally {
      setGenerating(false);
    }
  };

  const handleGenerateEmbeddings = async () => {
    try {
      setGeneratingEmbeddings(true);
      await generateEmbeddings();
      await fetchData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to generate embeddings');
    } finally {
      setGeneratingEmbeddings(false);
    }
  };

  const handleDeleteClusters = async () => {
    if (!confirm('Are you sure you want to delete all clusters? This action cannot be undone.')) {
      return;
    }

    try {
      setDeleting(true);
      await deleteClusters();
      await fetchData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete clusters');
    } finally {
      setDeleting(false);
    }
  };

  if (loading) {
    return <LoadingPage message="Loading requirement clusters..." />;
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-6">
        <Link
          href="/frameworks"
          className="text-sm text-neutral-500 hover:text-neutral-700 flex items-center gap-1"
        >
          <ChevronLeft className="w-4 h-4" />
          Back to Frameworks
        </Link>
      </div>

      <PageHeader
        title="Requirement Clusters"
        description="AI-powered clustering to reduce interview burden across frameworks"
        icon={Boxes}
      />

      {error && (
        <div className="mb-6">
          <ErrorMessage message={error} />
        </div>
      )}

      {/* Interview Reduction Stats */}
      {interviewReduction && (
        <Card className="mb-6 animate-fadeIn">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <BarChart2 className="w-5 h-5" />
              Interview Optimization
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
              <div className="text-center">
                <p className="text-3xl font-bold text-neutral-900">
                  {interviewReduction.questions_without_clustering}
                </p>
                <p className="text-sm text-neutral-500">Questions Without Clustering</p>
              </div>
              <div className="text-center">
                <p className="text-3xl font-bold text-primary-600">
                  {interviewReduction.questions_with_clustering}
                </p>
                <p className="text-sm text-neutral-500">Questions With Clustering</p>
              </div>
              <div className="text-center">
                <p className="text-3xl font-bold text-green-600">
                  {Math.round(interviewReduction.reduction_percentage)}%
                </p>
                <p className="text-sm text-neutral-500">Reduction</p>
              </div>
              <div className="text-center">
                <p className="text-3xl font-bold text-accent-600">
                  {interviewReduction.total_clusters}
                </p>
                <p className="text-sm text-neutral-500">Active Clusters</p>
              </div>
            </div>
            <div className="mt-4 p-4 bg-green-50 rounded-lg border border-green-200">
              <p className="text-sm text-green-700">
                <strong>Clustering Impact:</strong> By grouping similar requirements across{' '}
                {frameworks.length} frameworks, interview time is reduced from{' '}
                {interviewReduction.questions_without_clustering} questions to{' '}
                {interviewReduction.questions_with_clustering} questions - a{' '}
                {Math.round(interviewReduction.reduction_percentage)}% reduction in interview burden.
              </p>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Embedding Stats */}
      {embeddingStats && (
        <Card className="mb-6">
          <CardHeader>
            <CardTitle>Embedding Coverage</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-6">
              <div className="flex-1">
                <div className="h-4 bg-neutral-200 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-primary-500 to-accent-500 transition-all"
                    style={{ width: `${embeddingStats.coverage_percentage}%` }}
                  />
                </div>
              </div>
              <div className="text-right">
                <p className="text-2xl font-bold text-neutral-900">
                  {Math.round(embeddingStats.coverage_percentage)}%
                </p>
                <p className="text-sm text-neutral-500">
                  {embeddingStats.with_embeddings} / {embeddingStats.total_requirements} requirements
                </p>
              </div>
              <Button
                variant="outline"
                onClick={handleGenerateEmbeddings}
                disabled={generatingEmbeddings}
              >
                <RefreshCw className={cn('w-4 h-4 mr-2', generatingEmbeddings && 'animate-spin')} />
                {generatingEmbeddings ? 'Generating...' : 'Generate Embeddings'}
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Generate Clusters */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Generate Clusters</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-4">
            <div>
              <label className="block text-sm font-medium text-neutral-700 mb-1">
                Cluster Type
              </label>
              <select
                value={clusterType}
                onChange={(e) => setClusterType(e.target.value as ClusterType)}
                className="w-full px-3 py-2 border border-neutral-300 rounded-lg"
              >
                <option value="semantic">Semantic</option>
                <option value="topic">Topic</option>
                <option value="interview">Interview</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-neutral-700 mb-1">
                Similarity Threshold
              </label>
              <input
                type="number"
                min="0"
                max="1"
                step="0.05"
                value={threshold}
                onChange={(e) => setThreshold(parseFloat(e.target.value))}
                className="w-full px-3 py-2 border border-neutral-300 rounded-lg"
              />
            </div>
            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-neutral-700 mb-1">
                Frameworks (select multiple for cross-framework clustering, or none for all)
              </label>
              <div className="flex flex-wrap gap-2 mt-1">
                {frameworks.map((f) => (
                  <label
                    key={f.id}
                    className={cn(
                      'inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border cursor-pointer transition-colors text-sm',
                      selectedFrameworks.includes(f.id)
                        ? 'bg-primary-50 border-primary-300 text-primary-800'
                        : 'bg-white border-neutral-300 text-neutral-700 hover:border-neutral-400'
                    )}
                  >
                    <input
                      type="checkbox"
                      checked={selectedFrameworks.includes(f.id)}
                      onChange={(e) => {
                        if (e.target.checked) {
                          setSelectedFrameworks((prev) => [...prev, f.id]);
                        } else {
                          setSelectedFrameworks((prev) => prev.filter((id) => id !== f.id));
                        }
                      }}
                      className="sr-only"
                    />
                    <span className={cn(
                      'w-4 h-4 rounded border flex items-center justify-center flex-shrink-0',
                      selectedFrameworks.includes(f.id)
                        ? 'bg-primary-500 border-primary-500'
                        : 'border-neutral-400'
                    )}>
                      {selectedFrameworks.includes(f.id) && (
                        <svg className="w-3 h-3 text-white" viewBox="0 0 12 12" fill="none">
                          <path d="M2 6l3 3 5-5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                        </svg>
                      )}
                    </span>
                    {f.name}
                  </label>
                ))}
              </div>
            </div>
          </div>
          <div className="flex gap-3">
            <Button onClick={handleGenerateClusters} disabled={generating}>
              <RefreshCw className={cn('w-4 h-4 mr-2', generating && 'animate-spin')} />
              {generating ? 'Generating...' : 'Generate Clusters'}
            </Button>
            {clusters.length > 0 && (
              <Button variant="destructive" onClick={handleDeleteClusters} disabled={deleting}>
                <Trash2 className="w-4 h-4 mr-2" />
                {deleting ? 'Deleting...' : 'Delete All Clusters'}
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Clusters List */}
      <Card>
        <CardHeader>
          <CardTitle>Clusters ({clusters.length})</CardTitle>
        </CardHeader>
        <CardContent>
          {clusters.length === 0 ? (
            <p className="text-center text-neutral-500 py-8">
              No clusters found. Generate embeddings first, then create clusters.
            </p>
          ) : (
            <div className="space-y-3">
              {clusters.map((cluster, index) => (
                <div
                  key={cluster.id}
                  className="bg-white rounded-lg border border-neutral-200 overflow-hidden animate-slideInUp opacity-0"
                  style={{
                    animationDelay: `${index * 50}ms`,
                    animationFillMode: 'forwards',
                  }}
                >
                  <div
                    className="p-4 cursor-pointer hover:bg-neutral-50 transition-colors"
                    onClick={() => handleExpandCluster(cluster.id)}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <ChevronDown
                          className={cn(
                            'w-4 h-4 text-neutral-400 transition-transform',
                            expandedCluster === cluster.id && 'rotate-180'
                          )}
                        />
                        <span
                          className={cn(
                            'px-2 py-1 text-xs font-medium rounded',
                            clusterTypeColors[cluster.cluster_type as ClusterType]
                          )}
                        >
                          {cluster.cluster_type}
                        </span>
                        <span className="font-medium text-neutral-900">{cluster.name}</span>
                        <span className="text-sm text-neutral-500">
                          ({cluster.member_count} requirements)
                        </span>
                      </div>
                      {cluster.interview_question && (
                        <MessageSquare className="w-4 h-4 text-green-500" />
                      )}
                    </div>
                    {cluster.description && (
                      <p className="text-sm text-neutral-500 mt-2 ml-7">{cluster.description}</p>
                    )}
                  </div>

                  {expandedCluster === cluster.id && (
                    <div className="border-t border-neutral-200 bg-neutral-50 p-4">
                      {cluster.interview_question && (
                        <div className="mb-4 p-3 bg-green-50 rounded-lg border border-green-200">
                          <p className="text-xs font-medium text-green-700 mb-1">
                            Unified Interview Question
                          </p>
                          <p className="text-sm text-green-900">{cluster.interview_question}</p>
                        </div>
                      )}

                      <p className="text-xs font-medium text-neutral-500 mb-2">Cluster Members</p>
                      {clusterMembers[cluster.id] ? (
                        <div className="space-y-2">
                          {clusterMembers[cluster.id].map((member) => (
                            <div
                              key={member.requirement_id}
                              className="p-2 bg-white rounded border border-neutral-200 text-sm"
                            >
                              <div className="flex items-center justify-between">
                                <span className="font-mono text-primary-600">
                                  {member.requirement_code}
                                </span>
                                <span className="text-neutral-400">
                                  {Math.round(member.similarity_score * 100)}% similarity
                                </span>
                              </div>
                              <p className="text-neutral-600 mt-1">{member.requirement_name}</p>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <p className="text-sm text-neutral-400">Loading members...</p>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
