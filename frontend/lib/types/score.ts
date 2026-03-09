import { UUID } from './common';

// ─── Policy Statement Extraction Types ────────────────────────────────────────

export interface PolicyStatement {
  id: UUID;
  assessment_id: UUID;
  requirement_id: UUID;
  statement: string;
  document_title: string;
  document_section: string | null;
  is_relevant: boolean;
  created_at: string;
}

export interface PolicyExtractionResult {
  statements: PolicyStatement[];
  count: number;
}

// ─── LLM Scoring Types ────────────────────────────────────────────────────────

export interface ScoringJob {
  id: UUID;
  assessment_id: UUID;
  status: 'pending' | 'running' | 'completed' | 'failed';
  total_requirements: number;
  completed_requirements: number;
  failed_requirements: number;
  error_message: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
}

export interface ScoreExplanationItem {
  element_id?: string;
  mechanism_id?: string;
  issue?: string;
  gap?: string;
}

export interface ScoreImprovement {
  level: string;
  action: string;
}

export interface SupportingDocument {
  title: string;
  relevant_details: string;
}

export interface ScoreExplanation {
  executive_summary: string;
  supporting_documents?: SupportingDocument[];
  deficiencies?: ScoreExplanationItem[];
  gap_analysis?: ScoreExplanationItem[];
  peer_analysis?: ScoreExplanationItem[];
  improvements?: ScoreImprovement[];
  recommendations?: ScoreImprovement[];
  guidance?: ScoreImprovement[];
}

// ─── Documentation Score (Score 1) types ──────────────────────────────────────

export interface DocumentationRecommendation {
  type: string;
  action: string;
}

export interface SupportingEvidenceItem {
  document_title: string;
  explanation: string;
}

export interface DocumentationStatementEvaluation {
  statement_id: string;
  statement: string;
  document_title: string;
  document_section?: string;
  has_evidence: boolean;
  supporting_evidence: SupportingEvidenceItem[];
}

export interface DocumentationScoreExplanation {
  coverage_label: 'Covered' | 'Partial' | 'Gap';
  explanation: string;
  recommendations?: DocumentationRecommendation[];
  policy_statement_evaluations?: DocumentationStatementEvaluation[];
}

export interface ScoreAncestor {
  id: string;
  code: string | null;
  name: string | null;
}

export interface RequirementScore {
  id: UUID;
  assessment_id: UUID;
  requirement_id: UUID;
  framework_id: UUID | null;
  requirement_code: string | null;
  requirement_name: string | null;
  requirement_description: string | null;
  ancestors: ScoreAncestor[];
  score1: number | null;
  score2: number | null;
  score3: number | null;
  phase2_output: Record<string, unknown> | null;
  phase4_output: Record<string, unknown> | null;
  phase5_output: Record<string, unknown> | null;
  score1_explanation: DocumentationScoreExplanation | null;
  score2_explanation: ScoreExplanation | null;
  score3_explanation: ScoreExplanation | null;
  model_used: string | null;
  llm_calls_used: number | null;
  status: 'not_scored' | 'pending' | 'running' | 'completed' | 'failed' | 'skipped';
  skip_reason: 'missing_documentation' | 'no_policy_documents' | 'no_documentation' | 'no_policy_statements' | null;
  error_message: string | null;
  scored_at: string | null;
}

// ─── Legacy types (kept for backward compatibility with old score tables) ─────

export interface ExplanationComponent {
  type: string;
  source: string;
  contribution: number;
  details: string;
}

export interface ExplanationPayload {
  components: ExplanationComponent[];
  rationale: string;
  evidence_citations: Array<{ source: string; text: string }> | null;
  confidence_factors: Record<string, number> | null;
}

export interface SubcategoryScore {
  id: UUID;
  assessment_id: UUID;
  subcategory_id: UUID;
  subcategory_code: string | null;
  score: number;
  explanation_payload: ExplanationPayload;
  calculated_at: string;
  calculated_by: string | null;
  version: number;
}

export interface CategoryScore {
  id: UUID;
  assessment_id: UUID;
  category_id: UUID;
  category_code: string | null;
  category_name: string | null;
  score: number;
  explanation_payload: ExplanationPayload;
  calculated_at: string;
  version: number;
}

export interface FunctionScore {
  id: UUID;
  assessment_id: UUID;
  function_id: UUID;
  function_code: string | null;
  function_name: string | null;
  score: number;
  explanation_payload: ExplanationPayload;
  calculated_at: string;
  version: number;
}

export interface ScoreSummary {
  assessment_id: UUID;
  overall_maturity: number;
  function_scores: FunctionScore[];
  category_scores: CategoryScore[] | null;
  calculated_at: string;
}

export interface ScoreExplanationLegacy {
  score_id: UUID;
  level: 'subcategory' | 'category' | 'function';
  code: string;
  score: number;
  explanation: ExplanationPayload;
}
