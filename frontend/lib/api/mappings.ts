import { apiRequest } from './client';
import {
  MappingGenerateRequest,
  MappingGenerateResponse,
  MappingApproveResponse,
  GapListResponse,
  PolicyMapping,
} from '../types';

export async function generateMappings(
  assessmentId: string,
  options: MappingGenerateRequest = {},
  userId?: string
): Promise<MappingGenerateResponse> {
  return apiRequest<MappingGenerateResponse>(
    `/mappings/assessments/${assessmentId}/generate`,
    {
      method: 'POST',
      body: options,
      userId,
    }
  );
}

export async function approveMapping(
  mappingId: string,
  userId?: string
): Promise<MappingApproveResponse> {
  return apiRequest<MappingApproveResponse>(
    `/mappings/${mappingId}/approve`,
    {
      method: 'POST',
      userId,
    }
  );
}

export async function rejectMapping(
  mappingId: string,
  userId?: string
): Promise<MappingApproveResponse> {
  return apiRequest<MappingApproveResponse>(
    `/mappings/${mappingId}/reject`,
    {
      method: 'POST',
      userId,
    }
  );
}

export async function unrejectMapping(
  mappingId: string,
  userId?: string
): Promise<MappingApproveResponse> {
  return apiRequest<MappingApproveResponse>(
    `/mappings/${mappingId}/unreject`,
    {
      method: 'POST',
      userId,
    }
  );
}

export async function clearAllMappings(
  assessmentId: string,
  userId?: string
): Promise<{ policy_mappings_deleted: number; total_deleted: number }> {
  return apiRequest(
    `/mappings/assessments/${assessmentId}/all`,
    {
      method: 'DELETE',
      userId,
    }
  );
}

export async function listPolicyMappings(
  assessmentId: string,
  userId?: string
): Promise<PolicyMapping[]> {
  return apiRequest<PolicyMapping[]>(
    `/mappings/assessments/${assessmentId}/policies`,
    { userId }
  );
}

export async function getGaps(
  assessmentId: string,
  userId?: string
): Promise<GapListResponse> {
  return apiRequest<GapListResponse>(
    `/mappings/assessments/${assessmentId}/gaps`,
    { userId }
  );
}

export interface BulkMappingResult {
  mapping_id: string;
  success: boolean;
  error: string | null;
}

export interface BulkMappingResponse {
  total: number;
  successful: number;
  failed: number;
  results: BulkMappingResult[];
}

export async function bulkApproveMappings(
  mappingIds: string[],
  userId?: string
): Promise<BulkMappingResponse> {
  return apiRequest<BulkMappingResponse>('/mappings/bulk-approve', {
    method: 'POST',
    body: { mapping_ids: mappingIds, mapping_type: 'policy' },
    userId,
  });
}

export async function bulkRejectMappings(
  mappingIds: string[],
  userId?: string
): Promise<BulkMappingResponse> {
  return apiRequest<BulkMappingResponse>('/mappings/bulk-reject', {
    method: 'POST',
    body: { mapping_ids: mappingIds, mapping_type: 'policy' },
    userId,
  });
}
