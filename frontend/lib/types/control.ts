import { UUID } from './common';

export interface Control {
  id: UUID;
  assessment_id: UUID;
  identifier: string;
  name: string;
  description: string | null;
  owner: string | null;
  control_type: string | null;
  implementation_status: string | null;
  created_at: string;
  updated_at: string;
}

export interface ControlUploadError {
  row: number;
  field: string | null;
  message: string;
}

export interface ControlUploadResponse {
  total_rows: number;
  successful: number;
  failed: number;
  errors: ControlUploadError[] | null;
  controls: Control[];
}

export interface ControlMapping {
  id: UUID;
  control_id: UUID;
  subcategory_id: UUID | null;
  requirement_id: UUID | null;
  confidence_score: number | null;
  is_approved: boolean;
  approved_by_id: UUID | null;
  approved_at: string | null;
  created_at: string;
  subcategory_code: string | null;
  requirement_code: string | null;
  requirement_name: string | null;
  requirement_description: string | null;
  requirement_framework_name: string | null;
  requirement_parent_code: string | null;
  reasoning: string | null;
  control_name: string | null;
  control_description: string | null;
}
