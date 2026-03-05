import { UUID } from './common';

export interface Policy {
  id: UUID;
  assessment_id: UUID;
  name: string;
  description: string | null;
  version: string | null;
  owner: string | null;
  document_type: 'policy' | 'evidence';
  chunk_strategy: 'docling' | 'fixed' | 'tabular' | null;
  file_path: string | null;
  content_text: string | null;
  summary: string | null;
  facts_extracted_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface PolicyFact {
  id: UUID;
  fact_index: number;
  fact_type: 'policy_control' | 'evidence_observation';
  statement: string;
  key_attributes: Record<string, string | null> | null;
  confidence: 'explicit' | 'implied' | null;
  document_reference: { document_name: string; section: string | null } | null;
  extraction_model: string | null;
}

export interface PolicyFactsResponse {
  facts_extracted_at: string | null;
  facts: PolicyFact[];
}

export interface PolicyUploadResponse {
  policy: Policy;
  text_extracted: boolean;
  text_length: number | null;
  extraction_error: string | null;
}

export interface PolicyMapping {
  id: UUID;
  policy_id: UUID;
  subcategory_id: UUID | null;
  requirement_id: UUID | null;
  confidence_score: number | null;
  relevance_percentage: number | null;
  is_approved: boolean;
  approved_by_id: UUID | null;
  approved_at: string | null;
  is_rejected: boolean;
  rejected_at: string | null;
  created_at: string;
  subcategory_code: string | null;
  requirement_code: string | null;
  requirement_name: string | null;
  requirement_description: string | null;
  requirement_framework_name: string | null;
  requirement_parent_code: string | null;
  requirement_level: number | null;
  requirement_ancestors: { code: string; name: string | null; display_order?: number }[] | null;
  requirement_display_order: number | null;
  requirement_guidance: string | null;
  reasoning: string | null;
  source_excerpt: string | null;
  policy_name: string | null;
  policy_description: string | null;
  policy_summary: string | null;
  policy_document_type: 'policy' | 'evidence' | null;
}
