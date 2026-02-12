'use client';

import { useState } from 'react';
import { Link2, FileText, Check, X, Loader2, ArrowRight, Lightbulb } from 'lucide-react';
import { Card, CardContent, Button } from '@/components/ui';
import { ControlMapping, PolicyMapping } from '@/lib/types';
import { cn } from '@/lib/utils';

interface MappingCardProps {
  mapping: ControlMapping | PolicyMapping;
  type: 'control' | 'policy';
  onApprove: (approved: boolean) => Promise<void>;
}

export function MappingCard({ mapping, type, onApprove }: MappingCardProps) {
  const [loading, setLoading] = useState(false);

  const handleAction = async (approved: boolean) => {
    setLoading(true);
    try {
      await onApprove(approved);
    } finally {
      setLoading(false);
    }
  };

  const entityName = type === 'control'
    ? (mapping as ControlMapping).control_name
    : (mapping as PolicyMapping).policy_name;

  const entityDescription = type === 'control'
    ? (mapping as ControlMapping).control_description
    : (mapping as PolicyMapping).policy_description;

  const reasoning = mapping.reasoning;
  const sourceExcerpt = type === 'policy' ? (mapping as PolicyMapping).source_excerpt : null;

  const reqCode = mapping.requirement_code || mapping.subcategory_code;
  const reqName = mapping.requirement_name;
  const reqDescription = mapping.requirement_description;
  const reqFramework = mapping.requirement_framework_name;
  const reqParentCode = mapping.requirement_parent_code;

  const confidencePercent = mapping.confidence_score
    ? Math.round(mapping.confidence_score * 100)
    : 0;

  const getConfidenceColor = (percent: number) => {
    if (percent >= 80) return {
      bar: 'bg-gradient-to-r from-green-400 to-green-600',
      text: 'text-green-700',
    };
    if (percent >= 60) return {
      bar: 'bg-gradient-to-r from-amber-400 to-amber-600',
      text: 'text-amber-700',
    };
    return {
      bar: 'bg-gradient-to-r from-red-400 to-red-600',
      text: 'text-red-700',
    };
  };

  const colors = getConfidenceColor(confidencePercent);
  const Icon = type === 'control' ? Link2 : FileText;

  return (
    <Card className={cn(
      'transition-all duration-200',
      mapping.is_approved && 'border-green-200 bg-green-50/50'
    )}>
      <CardContent>
        {/* Header: type badge, confidence, and actions */}
        <div className="flex items-center justify-between gap-4 mb-4">
          <div className="flex items-center gap-3">
            <span className={cn(
              'inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium rounded-lg',
              type === 'control'
                ? 'bg-blue-100 text-blue-700'
                : 'bg-purple-100 text-purple-700'
            )}>
              <Icon className="h-3.5 w-3.5" />
              {type}
            </span>
            <div className="relative group flex items-center gap-2 cursor-help">
              <div className="w-24 bg-neutral-100 rounded-full h-2 overflow-hidden">
                <div
                  className={cn('h-2 rounded-full transition-all duration-500', colors.bar)}
                  style={{ width: `${confidencePercent}%` }}
                />
              </div>
              <span className={cn('text-sm font-bold', colors.text)}>{confidencePercent}%</span>
              <div className="absolute left-0 top-full mt-2 w-64 p-3 rounded-lg bg-neutral-800 text-white text-xs leading-relaxed shadow-lg opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-150 z-10">
                <p className="font-semibold mb-1">AI Confidence Score</p>
                <p>How confident the AI model is that this {type} maps to the suggested requirement. Higher scores indicate a stronger semantic match between the two. Review the descriptions to verify the mapping is correct.</p>
              </div>
            </div>
          </div>

          {/* Actions */}
          {!mapping.is_approved ? (
            <div className="flex items-center gap-2">
              <Button
                size="sm"
                variant="primary"
                onClick={() => handleAction(true)}
                disabled={loading}
                leftIcon={loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Check className="h-4 w-4" />}
              >
                Approve
              </Button>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => handleAction(false)}
                disabled={loading}
                leftIcon={<X className="h-4 w-4" />}
              >
                Reject
              </Button>
            </div>
          ) : (
            <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-green-100 text-green-700">
              <Check className="h-4 w-4" />
              <span className="text-sm font-medium">Approved</span>
            </div>
          )}
        </div>

        {/* Side-by-side comparison */}
        <div className="grid grid-cols-1 md:grid-cols-[1fr_auto_1fr] gap-3 items-stretch">
          {/* Left: Control/Policy */}
          <div className={cn(
            'rounded-lg border p-4',
            type === 'control'
              ? 'bg-blue-50/50 border-blue-200'
              : 'bg-purple-50/50 border-purple-200'
          )}>
            <p className={cn(
              'text-xs font-semibold uppercase tracking-wide mb-2',
              type === 'control' ? 'text-blue-500' : 'text-purple-500'
            )}>
              {type}
            </p>
            <h4 className="font-semibold text-neutral-900 text-sm">
              {entityName || 'Unknown'}
            </h4>
            {entityDescription && (
              <p className="mt-2 text-xs text-neutral-600 leading-relaxed">
                {entityDescription}
              </p>
            )}
            {sourceExcerpt && (
              <blockquote className="mt-3 text-xs text-neutral-700 italic leading-relaxed border-l-2 border-purple-300 pl-3">
                &ldquo;{sourceExcerpt}&rdquo;
              </blockquote>
            )}
          </div>

          {/* Arrow */}
          <div className="hidden md:flex items-center justify-center">
            <ArrowRight className="h-5 w-5 text-neutral-400" />
          </div>

          {/* Right: Requirement */}
          <div className="rounded-lg border bg-slate-50/50 border-slate-200 p-4">
            <div className="flex items-center gap-2 mb-2">
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                Requirement
              </p>
              {reqFramework && (
                <span className="text-xs px-1.5 py-0.5 rounded bg-slate-200 text-slate-600 font-medium">
                  {reqFramework}
                </span>
              )}
            </div>
            <h4 className="font-semibold text-neutral-900 text-sm">
              {reqParentCode && (
                <span className="text-neutral-400">{reqParentCode} &rsaquo; </span>
              )}
              {reqCode || 'Unknown'}
            </h4>
            {reqName && (
              <p className="mt-1 text-xs font-medium text-neutral-700">{reqName}</p>
            )}
            {reqDescription && (
              <p className="mt-2 text-xs text-neutral-600 leading-relaxed">
                {reqDescription}
              </p>
            )}
          </div>
        </div>

        {/* AI Reasoning */}
        {reasoning && (
          <div className="mt-4 pt-4 border-t border-neutral-100">
            <div className="flex gap-2">
              <Lightbulb className="h-4 w-4 text-amber-400 flex-shrink-0 mt-0.5" />
              <p className="text-xs text-neutral-600 leading-relaxed">
                {reasoning}
              </p>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
