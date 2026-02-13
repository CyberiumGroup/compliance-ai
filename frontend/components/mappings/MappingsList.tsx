'use client';

import { useState } from 'react';
import { Clock, Check, List } from 'lucide-react';
import { MappingCard } from './MappingCard';
import { ControlMapping, PolicyMapping } from '@/lib/types';
import { cn } from '@/lib/utils';

type StatusFilter = 'all' | 'pending' | 'approved';

interface MappingsListProps {
  controlMappings: ControlMapping[];
  policyMappings: PolicyMapping[];
  onApproveControl: (mappingId: string, approved: boolean) => Promise<void>;
  onApprovePolicy: (mappingId: string, approved: boolean) => Promise<void>;
}

export function MappingsList({
  controlMappings,
  policyMappings,
  onApproveControl,
  onApprovePolicy,
}: MappingsListProps) {
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('pending');

  const allMappings = [
    ...controlMappings.map((m) => ({ ...m, _type: 'control' as const })),
    ...policyMappings.map((m) => ({ ...m, _type: 'policy' as const })),
  ].sort((a, b) => {
    // Sort by approval status (pending first), then by confidence
    if (a.is_approved !== b.is_approved) {
      return a.is_approved ? 1 : -1;
    }
    return (b.confidence_score || 0) - (a.confidence_score || 0);
  });

  if (allMappings.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        No mappings generated yet. Click &quot;Suggest Mappings&quot; to analyze your controls and policies.
      </div>
    );
  }

  const pendingCount = allMappings.filter((m) => !m.is_approved).length;
  const approvedCount = allMappings.filter((m) => m.is_approved).length;

  const filteredMappings = allMappings.filter((m) => {
    if (statusFilter === 'pending') return !m.is_approved;
    if (statusFilter === 'approved') return m.is_approved;
    return true;
  });

  const filters: { id: StatusFilter; label: string; count: number; icon: typeof List }[] = [
    { id: 'pending', label: 'Pending Review', count: pendingCount, icon: Clock },
    { id: 'approved', label: 'Approved', count: approvedCount, icon: Check },
    { id: 'all', label: 'All', count: allMappings.length, icon: List },
  ];

  return (
    <div className="space-y-4">
      <div className="flex gap-2">
        {filters.map((filter) => {
          const Icon = filter.icon;
          const isActive = statusFilter === filter.id;
          return (
            <button
              key={filter.id}
              onClick={() => setStatusFilter(filter.id)}
              className={cn(
                'flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-all',
                isActive
                  ? filter.id === 'pending'
                    ? 'bg-amber-100 text-amber-700 ring-1 ring-amber-200'
                    : filter.id === 'approved'
                      ? 'bg-green-100 text-green-700 ring-1 ring-green-200'
                      : 'bg-neutral-200 text-neutral-700 ring-1 ring-neutral-300'
                  : 'text-neutral-500 hover:bg-neutral-100'
              )}
            >
              <Icon className="h-3.5 w-3.5" />
              {filter.label}
              <span className={cn(
                'px-1.5 py-0.5 text-xs font-semibold rounded-full',
                isActive
                  ? filter.id === 'pending'
                    ? 'bg-amber-200 text-amber-800'
                    : filter.id === 'approved'
                      ? 'bg-green-200 text-green-800'
                      : 'bg-neutral-300 text-neutral-700'
                  : 'bg-neutral-100 text-neutral-500'
              )}>
                {filter.count}
              </span>
            </button>
          );
        })}
      </div>

      {filteredMappings.length === 0 ? (
        <div className="text-center py-8 text-neutral-500">
          {statusFilter === 'pending'
            ? 'No pending mappings. All mappings have been reviewed.'
            : statusFilter === 'approved'
              ? 'No approved mappings yet.'
              : 'No mappings found.'}
        </div>
      ) : (
        <div className="grid gap-3">
          {filteredMappings.map((mapping) => (
            <MappingCard
              key={mapping.id}
              mapping={mapping}
              type={mapping._type}
              onApprove={(approved) =>
                mapping._type === 'control'
                  ? onApproveControl(mapping.id, approved)
                  : onApprovePolicy(mapping.id, approved)
              }
            />
          ))}
        </div>
      )}
    </div>
  );
}
