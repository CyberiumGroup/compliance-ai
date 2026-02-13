import { UUID } from './common';

export type EntityType = 'policy' | 'control';
export type GapType = 'unmapped_requirement' | 'policy_only' | 'control_only';

export interface MappingGenerateRequest {
  include_policies?: boolean;
  include_controls?: boolean;
  confidence_threshold?: number;
}

export interface MappingSuggestion {
  entity_type: EntityType;
  entity_id: UUID;
  entity_name: string;
  requirement_id: UUID;
  requirement_code: string;
  confidence_score: number;
  reasoning: string | null;
}

export interface MappingGenerateResponse {
  assessment_id: UUID;
  suggestions_count: number;
  policy_mappings: number;
  control_mappings: number;
  suggestions: MappingSuggestion[];
}

export interface MappingApproveRequest {
  is_approved: boolean;
  notes?: string;
}

export interface MappingApproveResponse {
  mapping_id: UUID;
  mapping_type: EntityType;
  is_approved: boolean;
  approved_at: string | null;
}

export interface Gap {
  gap_type: GapType;
  requirement_id: UUID;
  requirement_code: string;
  requirement_name: string | null;
  requirement_description: string | null;
  framework_name: string | null;
  parent_code: string | null;
  has_policy: boolean;
  has_control: boolean;
  policy_names: string[] | null;
  control_names: string[] | null;
}

export interface GapListResponse {
  assessment_id: UUID;
  total_requirements: number;
  total_gaps: number;
  unmapped_requirements: number;
  policy_only_count: number;
  control_only_count: number;
  coverage_percentage: number;
  gaps: Gap[];
}
