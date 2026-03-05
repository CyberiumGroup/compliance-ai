import { uploadFile, apiRequest } from './client';
import { Policy, PolicyUploadResponse, PolicyFactsResponse } from '../types';

export async function uploadPolicy(
  assessmentId: string,
  file: File,
  metadata: {
    name?: string;
    description?: string;
    version?: string;
    owner?: string;
    document_type?: 'policy' | 'evidence';
  } = {},
  userId?: string
): Promise<PolicyUploadResponse> {
  return uploadFile<PolicyUploadResponse>(
    `/assessments/${assessmentId}/policies/upload`,
    file,
    userId,
    metadata as Record<string, string>
  );
}

export async function listPolicies(
  assessmentId: string,
  userId?: string,
  documentType?: 'policy' | 'evidence'
): Promise<Policy[]> {
  const params = documentType ? `?document_type=${documentType}` : '';
  return apiRequest<Policy[]>(`/assessments/${assessmentId}/policies${params}`, { userId });
}

export async function getPolicy(policyId: string, userId?: string): Promise<Policy> {
  return apiRequest<Policy>(`/policies/${policyId}`, { userId });
}

export async function deletePolicy(policyId: string, userId?: string): Promise<void> {
  return apiRequest<void>(`/policies/${policyId}`, {
    method: 'DELETE',
    userId,
  });
}

export interface PolicyChunk {
  chunk_index: number;
  chunk_text: string;
  token_count: number;
  has_embedding: boolean;
}

export async function getPolicyChunks(assessmentId: string, policyId: string): Promise<PolicyChunk[]> {
  return apiRequest<PolicyChunk[]>(`/assessments/${assessmentId}/policies/${policyId}/chunks`);
}

export async function getPolicyFacts(
  assessmentId: string,
  policyId: string,
): Promise<PolicyFactsResponse> {
  return apiRequest<PolicyFactsResponse>(
    `/assessments/${assessmentId}/policies/${policyId}/facts`,
  );
}

export async function regeneratePolicyFacts(
  assessmentId: string,
  policyId: string,
  userId?: string,
): Promise<{ queued: boolean }> {
  return apiRequest<{ queued: boolean }>(
    `/assessments/${assessmentId}/policies/${policyId}/facts/regenerate`,
    { method: 'POST', userId },
  );
}
