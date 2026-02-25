'use client';

import { PolicyMapping } from '@/lib/types';
import { RequirementMappingGroup } from './RequirementMappingGroup';

interface MappingsListProps {
  policyMappings: PolicyMapping[];
  onRejectPolicy: (mappingId: string) => Promise<void>;
  onUnrejectPolicy: (mappingId: string) => Promise<void>;
}

interface RequirementGroup {
  requirementCode: string;
  requirementName: string | null;
  requirementDescription: string | null;
  requirementGuidance: string | null;
  requirementParentCode: string | null;
  mappings: PolicyMapping[];
}

interface FrameworkSection {
  frameworkName: string;
  requirements: RequirementGroup[];
}

function groupMappings(mappings: PolicyMapping[]): FrameworkSection[] {
  const frameworkMap = new Map<string, Map<string, RequirementGroup>>();

  for (const mapping of mappings) {
    const fw = mapping.requirement_framework_name ?? 'Unknown Framework';
    const code = mapping.requirement_code ?? 'Unknown Requirement';

    if (!frameworkMap.has(fw)) {
      frameworkMap.set(fw, new Map());
    }
    const reqMap = frameworkMap.get(fw)!;

    if (!reqMap.has(code)) {
      reqMap.set(code, {
        requirementCode: code,
        requirementName: mapping.requirement_name ?? null,
        requirementDescription: mapping.requirement_description ?? null,
        requirementGuidance: mapping.requirement_guidance ?? null,
        requirementParentCode: mapping.requirement_parent_code ?? null,
        mappings: [],
      });
    }
    reqMap.get(code)!.mappings.push(mapping);
  }

  const sections: FrameworkSection[] = [];
  const sortedFrameworks = [...frameworkMap.keys()].sort((a, b) => a.localeCompare(b));

  for (const fw of sortedFrameworks) {
    const reqMap = frameworkMap.get(fw)!;
    const requirements = [...reqMap.values()].sort((a, b) =>
      a.requirementCode.localeCompare(b.requirementCode)
    );
    sections.push({ frameworkName: fw, requirements });
  }

  return sections;
}

export function MappingsList({ policyMappings, onRejectPolicy, onUnrejectPolicy }: MappingsListProps) {
  if (policyMappings.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        No mappings generated yet. Click &quot;Suggest Mappings&quot; to score your policies against requirements.
      </div>
    );
  }

  const sections = groupMappings(policyMappings);

  return (
    <div className="space-y-6">
      {/* Relevance score legend */}
      <div className="flex items-center gap-3 text-xs text-neutral-500 px-1">
        <span className="font-medium text-neutral-600">Relevance score:</span>
        <span className="flex items-center gap-1">
          <span className="inline-block w-2.5 h-2.5 rounded-full bg-green-500" /> ≥80% high
        </span>
        <span className="flex items-center gap-1">
          <span className="inline-block w-2.5 h-2.5 rounded-full bg-amber-500" /> 60–79% moderate
        </span>
        <span className="flex items-center gap-1">
          <span className="inline-block w-2.5 h-2.5 rounded-full bg-red-500" /> &lt;60% low
        </span>
        <span className="text-neutral-400 ml-1">
          — max cosine similarity between policy sections and requirement, normalized 0–100%
        </span>
      </div>

      <div className="space-y-8">
        {sections.map((section) => (
          <div key={section.frameworkName}>
            <h3 className="text-xs font-semibold text-neutral-500 uppercase tracking-wider mb-3 px-1">
              {section.frameworkName}
            </h3>
            <div className="space-y-3">
              {section.requirements.map((req) => (
                <RequirementMappingGroup
                  key={req.requirementCode}
                  requirementCode={req.requirementCode}
                  requirementName={req.requirementName}
                  requirementDescription={req.requirementDescription}
                  requirementGuidance={req.requirementGuidance}
                  requirementParentCode={req.requirementParentCode}
                  mappings={req.mappings}
                  onReject={onRejectPolicy}
                  onUnreject={onUnrejectPolicy}
                />
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
