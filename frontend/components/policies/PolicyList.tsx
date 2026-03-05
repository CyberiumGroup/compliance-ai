'use client';

import { FileText, Trash2, CheckCircle, AlignLeft, Sparkles, Table } from 'lucide-react';
import { Policy } from '@/lib/types';
import { Card, CardContent } from '@/components/ui';
import { PolicyChunkViewer } from './PolicyChunkViewer';
import { PolicyFactViewer } from './PolicyFactViewer';
import { cn } from '@/lib/utils';

interface PolicyListProps {
  policies: Policy[];
  assessmentId: string;
  onDelete?: (policyId: string) => void;
  userId?: string;
}

export function PolicyList({ policies, assessmentId, onDelete, userId }: PolicyListProps) {
  if (policies.length === 0) {
    return (
      <div className="text-center py-12">
        <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-gradient-to-br from-primary-50 to-accent-50 flex items-center justify-center">
          <FileText className="h-8 w-8 text-primary-500" />
        </div>
        <p className="text-neutral-500">No policies uploaded yet</p>
      </div>
    );
  }

  return (
    <div className="grid gap-4 md:grid-cols-2">
      {policies.map((policy, index) => (
        <Card
          key={policy.id}
          hover
          glow
          className="animate-slideInUp opacity-0"
          style={{
            animationDelay: `${index * 75}ms`,
            animationFillMode: 'forwards'
          }}
        >
          <CardContent>
            <div className="flex justify-between items-start">
              <div className="flex-1 min-w-0">
                <h3 className="text-lg font-semibold text-neutral-900 truncate">
                  {policy.name}
                </h3>
                {policy.description && (
                  <p className="mt-1 text-sm text-neutral-500 line-clamp-2">
                    {policy.description}
                  </p>
                )}
                <div className="mt-3 flex flex-wrap gap-2">
                  {policy.version && (
                    <span className="px-2.5 py-1 text-xs font-medium bg-neutral-100 text-neutral-700 rounded-full">
                      v{policy.version}
                    </span>
                  )}
                  {policy.owner && (
                    <span className="px-2.5 py-1 text-xs font-medium bg-primary-50 text-primary-700 rounded-full">
                      {policy.owner}
                    </span>
                  )}
                  {policy.content_text && (
                    <span className="px-2.5 py-1 text-xs font-medium bg-accent-50 text-accent-700 rounded-full flex items-center gap-1">
                      <CheckCircle className="h-3 w-3" />
                      Text extracted
                    </span>
                  )}
                  {policy.chunk_strategy === 'docling' && (
                    <span className="px-2.5 py-1 text-xs font-medium bg-violet-50 text-violet-700 rounded-full flex items-center gap-1">
                      <Sparkles className="h-3 w-3" />
                      Docling chunks
                    </span>
                  )}
                  {policy.chunk_strategy === 'fixed' && (
                    <span className="px-2.5 py-1 text-xs font-medium bg-neutral-100 text-neutral-600 rounded-full flex items-center gap-1">
                      <AlignLeft className="h-3 w-3" />
                      Fixed chunks
                    </span>
                  )}
                  {policy.chunk_strategy === 'tabular' && (
                    <span className="px-2.5 py-1 text-xs font-medium bg-teal-50 text-teal-700 rounded-full flex items-center gap-1">
                      <Table className="h-3 w-3" />
                      Tabular chunks
                    </span>
                  )}
                </div>
                <PolicyChunkViewer
                  assessmentId={assessmentId}
                  policyId={policy.id}
                  chunkStrategy={policy.chunk_strategy}
                />
                <PolicyFactViewer
                  assessmentId={assessmentId}
                  policyId={policy.id}
                  factsExtractedAt={policy.facts_extracted_at ?? null}
                  userId={userId}
                />
              </div>
              {onDelete && (
                <button
                  onClick={() => onDelete(policy.id)}
                  className={cn(
                    'ml-4 p-2 rounded-lg transition-all duration-200',
                    'text-neutral-400 hover:text-red-600',
                    'hover:bg-red-50'
                  )}
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              )}
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
