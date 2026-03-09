import { apiRequest, ApiError } from './client';
import { ScoringJob, RequirementScore, PolicyExtractionResult } from '../types';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

// ─── LLM Scoring API ─────────────────────────────────────────────────────────

export async function runScoring(
  assessmentId: string,
  userId?: string
): Promise<{ job_id: string; status: string }> {
  return apiRequest(`/assessments/${assessmentId}/scoring/run`, {
    method: 'POST',
    userId,
  });
}

export async function getScoringJob(
  assessmentId: string,
  userId?: string
): Promise<ScoringJob | null> {
  return apiRequest<ScoringJob | null>(`/assessments/${assessmentId}/scoring/job`, {
    userId,
  });
}

export async function getRequirementScores(
  assessmentId: string,
  userId?: string
): Promise<RequirementScore[]> {
  return apiRequest<RequirementScore[]>(`/assessments/${assessmentId}/scoring/requirements`, {
    userId,
  });
}

export async function rerunRequirementScore(
  assessmentId: string,
  requirementId: string,
  userId?: string
): Promise<RequirementScore> {
  return apiRequest<RequirementScore>(
    `/assessments/${assessmentId}/scoring/requirements/${requirementId}/rerun`,
    { method: 'POST', userId }
  );
}

export async function clearRequirementScores(
  assessmentId: string,
  requirementIds: string[],
  userId?: string
): Promise<{ deleted: number }> {
  return apiRequest<{ deleted: number }>(
    `/assessments/${assessmentId}/scoring/requirements`,
    { method: 'DELETE', userId, body: requirementIds }
  );
}

// ─── Excel export ─────────────────────────────────────────────────────────────

/**
 * Download scoring results as an Excel file.
 * Uses raw fetch (not apiRequest) since we need binary blob handling.
 */
export async function downloadScoringExcel(assessmentId: string): Promise<void> {
  const token = typeof window !== 'undefined' ? localStorage.getItem('compliance-ai-access-token') : null;
  const headers: HeadersInit = {};
  if (token) headers['Authorization'] = `Bearer ${token}`;

  const res = await fetch(`${API_BASE}/assessments/${assessmentId}/scoring/export`, { headers });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new ApiError(res.status, err.detail || `Export failed: ${res.status}`);
  }

  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = `compliance-scores-${assessmentId}.xlsx`;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

// ─── Policy Statement Extraction ──────────────────────────────────────────────

export async function runPolicyExtraction(
  assessmentId: string,
  requirementId: string,
  userId?: string
): Promise<PolicyExtractionResult> {
  return apiRequest<PolicyExtractionResult>(
    `/assessments/${assessmentId}/scoring/requirements/${requirementId}/policy-extraction`,
    { method: 'POST', userId }
  );
}

export async function getPolicyStatements(
  assessmentId: string,
  requirementId: string,
  userId?: string
): Promise<PolicyExtractionResult> {
  return apiRequest<PolicyExtractionResult>(
    `/assessments/${assessmentId}/scoring/requirements/${requirementId}/policy-statements`,
    { userId }
  );
}

export async function deletePolicyStatement(
  assessmentId: string,
  requirementId: string,
  statementId: string,
  userId?: string
): Promise<{ deleted: boolean }> {
  return apiRequest<{ deleted: boolean }>(
    `/assessments/${assessmentId}/scoring/requirements/${requirementId}/policy-statements/${statementId}`,
    { method: 'DELETE', userId }
  );
}

// ─── Compatibility shim — used by WorkflowStepper / assessment overview ───────

/**
 * Returns a minimal summary object when scoring is complete, null otherwise.
 * Used by WorkflowStepper (hasScores check) and assessment overview (overall_maturity display).
 * overall_maturity is returned as null since the new system uses per-requirement scores.
 */
export async function getScoreSummary(
  assessmentId: string,
  userId?: string
): Promise<{ overall_maturity: null } | null> {
  const job = await getScoringJob(assessmentId, userId);
  return job?.status === 'completed' ? { overall_maturity: null } : null;
}
