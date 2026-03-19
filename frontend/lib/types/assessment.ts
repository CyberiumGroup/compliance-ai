import { UUID } from './common';

export type AssessmentStatus = 'DRAFT' | 'IN_PROGRESS' | 'COMPLETED' | 'ARCHIVED';
export type AssessmentDepth = 'design' | 'implementation' | 'operating_effectiveness';

export interface Assessment {
  id: UUID;
  name: string;
  description: string | null;
  organization_name: string;
  status: AssessmentStatus;
  depth_level: AssessmentDepth;
  policy_mapping_threshold: number | null;
  industry: string | null;
  business_description: string | null;
  product_service_description: string | null;
  information_types: string | null;
  created_by_id: UUID;
  created_at: string;
  updated_at: string;
}

export interface AssessmentCreate {
  name: string;
  description?: string;
  organization_name: string;
  depth_level?: AssessmentDepth;
}

export interface AssessmentUpdate {
  name?: string;
  description?: string;
  organization_name?: string;
  status?: AssessmentStatus;
  depth_level?: AssessmentDepth;
  policy_mapping_threshold?: number | null;
  industry?: string | null;
  business_description?: string | null;
  product_service_description?: string | null;
  information_types?: string | null;
}

export interface AssessmentListResponse {
  items: Assessment[];
  total: number;
}

export interface AssessmentTransitions {
  current_status: string;
  available_transitions: string[];
}
