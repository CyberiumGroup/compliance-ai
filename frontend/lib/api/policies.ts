import { uploadFile, apiRequest } from './client';
import { Policy, PolicyUploadResponse } from '../types';

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
