'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { Save, Undo2 } from 'lucide-react';
import { getFrameworkHierarchy, setAssessmentScope } from '@/lib/api';
import { FrameworkHierarchyNode, AssessmentScope, FrameworkType } from '@/lib/types';
import { Button } from '@/components/ui/Button';
import { cn } from '@/lib/utils';

interface RequirementScopeSelectorProps {
  frameworkId: string;
  assessmentId: string;
  frameworkType: FrameworkType;
  hierarchyLabel?: string;
  currentScope: AssessmentScope;
  onScopeChange: () => void;
}

const frameworkColors: Record<string, { color: string; bg: string; border: string; checkbox: string }> = {
  nist_csf: { color: 'text-blue-700', bg: 'bg-blue-50', border: 'border-blue-200', checkbox: 'border-blue-500 bg-blue-500' },
  iso_27001: { color: 'text-green-700', bg: 'bg-green-50', border: 'border-green-200', checkbox: 'border-green-500 bg-green-500' },
  soc2_tsc: { color: 'text-purple-700', bg: 'bg-purple-50', border: 'border-purple-200', checkbox: 'border-purple-500 bg-purple-500' },
  custom: { color: 'text-orange-700', bg: 'bg-orange-50', border: 'border-orange-200', checkbox: 'border-orange-500 bg-orange-500' },
};

function setsEqual(a: Set<string>, b: Set<string>): boolean {
  if (a.size !== b.size) return false;
  for (const item of a) {
    if (!b.has(item)) return false;
  }
  return true;
}

export function RequirementScopeSelector({
  frameworkId,
  assessmentId,
  frameworkType,
  hierarchyLabel,
  currentScope,
  onScopeChange,
}: RequirementScopeSelectorProps) {
  const [categories, setCategories] = useState<FrameworkHierarchyNode[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [selectedCategories, setSelectedCategories] = useState<Set<string>>(new Set());
  const savedSelectionRef = useRef<Set<string>>(new Set());

  const colors = frameworkColors[frameworkType] || frameworkColors.custom;

  const initSelection = useCallback((hierarchy: FrameworkHierarchyNode[], scope: AssessmentScope) => {
    let selected: Set<string>;
    if (scope.include_all) {
      selected = new Set(hierarchy.map((c) => c.id));
    } else if (scope.included_requirement_ids && scope.included_requirement_ids.length > 0) {
      selected = new Set(scope.included_requirement_ids);
    } else {
      const excluded = new Set(scope.excluded_requirement_ids || []);
      selected = new Set(hierarchy.filter((c) => !excluded.has(c.id)).map((c) => c.id));
    }
    setSelectedCategories(selected);
    savedSelectionRef.current = new Set(selected);
  }, []);

  useEffect(() => {
    const fetchHierarchy = async () => {
      try {
        const hierarchy = await getFrameworkHierarchy(frameworkId, 0);
        setCategories(hierarchy);
        initSelection(hierarchy, currentScope);
      } catch {
        // Hierarchy unavailable
      } finally {
        setLoading(false);
      }
    };

    fetchHierarchy();
  }, [frameworkId, currentScope, initSelection]);

  const hasChanges = !setsEqual(selectedCategories, savedSelectionRef.current);

  const handleToggle = (categoryId: string, isRequired: boolean) => {
    if (isRequired) return;

    const newSelected = new Set(selectedCategories);
    if (newSelected.has(categoryId)) {
      newSelected.delete(categoryId);
    } else {
      newSelected.add(categoryId);
    }
    setSelectedCategories(newSelected);
  };

  const handleSelectAll = () => {
    setSelectedCategories(new Set(categories.map((c) => c.id)));
  };

  const handleDiscard = () => {
    setSelectedCategories(new Set(savedSelectionRef.current));
  };

  const handleSave = async () => {
    setSaving(true);

    try {
      const allIds = categories.map((c) => c.id);
      const isAll = selectedCategories.size === allIds.length;

      if (isAll) {
        await setAssessmentScope(assessmentId, {
          framework_id: frameworkId,
          include_all: true,
        });
      } else {
        await setAssessmentScope(assessmentId, {
          framework_id: frameworkId,
          include_all: false,
          included_requirement_ids: Array.from(selectedCategories),
        });
      }

      savedSelectionRef.current = new Set(selectedCategories);
      onScopeChange();
    } catch {
      // Revert on error
      setSelectedCategories(new Set(savedSelectionRef.current));
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="mt-3 px-8 space-y-2">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-14 bg-neutral-100 rounded-lg animate-pulse" />
        ))}
      </div>
    );
  }

  if (categories.length === 0) return null;

  const label = hierarchyLabel || 'Categories';
  const allSelected = categories.length > 0 && categories.every((c) => selectedCategories.has(c.id));

  return (
    <div className="mt-3 px-8">
      <div className="flex items-center justify-between mb-3">
        <p className="text-xs text-neutral-500 font-medium">{label}</p>
        {!allSelected && (
          <button
            type="button"
            onClick={handleSelectAll}
            className="text-xs font-medium text-primary-600 hover:text-primary-700 transition-colors"
          >
            Select all
          </button>
        )}
      </div>
      <div className="space-y-1.5">
        {categories.map((category) => {
          const isSelected = selectedCategories.has(category.id);
          const isRequired = !!(category.metadata as Record<string, unknown>)?.is_required;

          return (
            <button
              key={category.id}
              type="button"
              onClick={() => handleToggle(category.id, isRequired)}
              disabled={isRequired || saving}
              className={cn(
                'w-full flex items-center gap-3 px-4 py-3 rounded-lg border text-left transition-all text-sm',
                isSelected
                  ? `${colors.border} ${colors.bg}`
                  : 'border-neutral-200 bg-white hover:border-neutral-300',
                isRequired && 'cursor-default opacity-90',
                saving && 'opacity-60'
              )}
            >
              <div className={cn(
                'w-5 h-5 rounded border-2 flex-shrink-0 flex items-center justify-center transition-colors',
                isSelected
                  ? colors.checkbox
                  : 'border-neutral-300',
              )}>
                {isSelected && (
                  <svg className="w-3 h-3 text-white" viewBox="0 0 12 12" fill="none">
                    <path d="M2 6l3 3 5-5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                )}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className={cn(
                    'text-xs font-mono px-1.5 py-0.5 rounded',
                    isSelected
                      ? `${colors.bg} ${colors.color}`
                      : 'bg-neutral-100 text-neutral-500'
                  )}>
                    {category.code}
                  </span>
                  <span className={cn(
                    'font-medium',
                    isSelected ? 'text-neutral-900' : 'text-neutral-700'
                  )}>
                    {category.name}
                  </span>
                  {isRequired && (
                    <span className="text-xs text-neutral-400 italic">Required</span>
                  )}
                </div>
                {category.description && (
                  <p className="mt-1 text-xs text-neutral-500 line-clamp-2 leading-relaxed">
                    {category.description}
                  </p>
                )}
              </div>
            </button>
          );
        })}
      </div>

      {hasChanges && (
        <div className="mt-4 flex items-center justify-between p-3 rounded-lg bg-amber-50 border border-amber-200">
          <p className="text-xs text-amber-800 font-medium">You have unsaved scope changes</p>
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={handleDiscard}
              disabled={saving}
              leftIcon={<Undo2 className="h-3.5 w-3.5" />}
            >
              Discard
            </Button>
            <Button
              variant="primary"
              size="sm"
              onClick={handleSave}
              loading={saving}
              leftIcon={<Save className="h-3.5 w-3.5" />}
            >
              Save Changes
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
