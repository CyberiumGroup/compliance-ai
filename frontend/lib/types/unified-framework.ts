import { UUID } from './common';

// Framework types
export type FrameworkType = 'nist_csf' | 'iso_27001' | 'soc2_tsc' | 'custom';
export type MappingType = 'equivalent' | 'partial' | 'related';
export type MappingSource = 'ai_generated' | 'human_defined' | 'official';
export type ClusterType = 'semantic' | 'topic' | 'interview';

export interface Framework {
  id: UUID;
  code: string;
  name: string;
  version: string;
  description: string | null;
  framework_type: FrameworkType;
  hierarchy_levels: number;
  hierarchy_labels: string[] | null;
  is_active: boolean;
  is_builtin: boolean;
  metadata: Record<string, unknown> | null;
}

export interface FrameworkRequirement {
  id: UUID;
  code: string;
  name: string;
  description: string | null;
  guidance: string | null;
  level: number;
  is_assessable: boolean;
  parent_id: UUID | null;
  display_order: number;
  metadata: Record<string, unknown> | null;
}

export interface FrameworkHierarchyNode extends FrameworkRequirement {
  children: FrameworkHierarchyNode[];
}

export interface FrameworkStats {
  framework_id: UUID;
  framework_code: string;
  framework_name: string;
  total_requirements: number;
  assessable_requirements: number;
  requirements_by_level: Record<string, number>;
}

// Crosswalk types
export interface Crosswalk {
  id: UUID;
  source_requirement_id: UUID;
  source_requirement_code: string | null;
  target_requirement_id: UUID;
  target_requirement_code: string | null;
  mapping_type: MappingType;
  confidence_score: number;
  mapping_source: MappingSource;
  reasoning: string | null;
  is_approved: boolean;
  approved_at: string | null;
}

export interface CrosswalkStats {
  total_crosswalks: number;
  approved: number;
  pending_review: number;
  by_type: Record<string, number>;
  by_source: Record<string, number>;
  average_confidence: number;
}

export interface CrosswalkGenerateRequest {
  source_framework_id: UUID;
  target_framework_id: UUID;
  similarity_threshold?: number;
  top_k_per_requirement?: number;
  validate_with_llm?: boolean;
  auto_approve_threshold?: number;
}

export interface CrosswalkCreateRequest {
  source_requirement_id: UUID;
  target_requirement_id: UUID;
  mapping_type?: MappingType;
  reasoning?: string;
}

// Cluster types
export interface RequirementCluster {
  id: UUID;
  name: string;
  description: string | null;
  cluster_type: ClusterType;
  member_count: number;
  is_active: boolean;
  interview_question: string | null;
}

export interface ClusterMember {
  requirement_id: UUID;
  requirement_code: string;
  requirement_name: string;
  framework_id: UUID;
  similarity_score: number;
}

export interface ClusterGenerateRequest {
  framework_ids?: UUID[];
  threshold?: number;
  min_cluster_size?: number;
  cluster_type?: ClusterType;
}

export interface EmbeddingStats {
  total_requirements: number;
  with_embeddings: number;
  without_embeddings: number;
  coverage_percentage: number;
}

export interface InterviewReduction {
  total_requirements: number;
  clustered_requirements: number;
  unclustered_requirements: number;
  total_clusters: number;
  questions_without_clustering: number;
  questions_with_clustering: number;
  reduction_percentage: number;
}

// Company framework types
export interface CompanyFramework {
  id: UUID;
  framework_id: UUID;
  framework_code: string | null;
  framework_name: string | null;
  is_active: boolean;
  priority: number;
  notes: string | null;
}

export interface CompanyFrameworkCreate {
  framework_id: UUID;
  priority?: number;
  notes?: string;
}

// Assessment scope types
export interface AssessmentScope {
  id: UUID;
  framework_id: UUID;
  framework_code: string | null;
  include_all: boolean;
  excluded_requirement_ids: UUID[] | null;
  included_requirement_ids: UUID[] | null;
}

export interface AssessmentScopeCreate {
  framework_id: UUID;
  include_all?: boolean;
  excluded_requirement_ids?: UUID[];
  included_requirement_ids?: UUID[];
}
