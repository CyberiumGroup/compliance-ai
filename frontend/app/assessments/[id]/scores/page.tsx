'use client';

import { useState, useEffect, use, useCallback } from 'react';
import { AlertTriangle, BarChart3, FileDown, Play, RefreshCw, Trash2, X } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent, Button } from '@/components/ui';
import { LoadingSpinner, ErrorMessage } from '@/components/ui';
import { ScoringProgress } from '@/components/scores/ScoringProgress';
import { RequirementScoreHierarchyList } from '@/components/scores/RequirementScoreHierarchyList';
import { RequirementScoreDetail } from '@/components/scores/RequirementScoreDetail';
import {
  runScoring,
  getScoringJob,
  getRequirementScores,
  rerunRequirementScore,
  clearRequirementScores,
  downloadScoringExcel,
} from '@/lib/api/scores';
import { useUserId } from '@/lib/hooks/useUserId';
import { ScoringJob, RequirementScore } from '@/lib/types';

interface ScoresPageProps {
  params: Promise<{ id: string }>;
}

export default function ScoresPage({ params }: ScoresPageProps) {
  const { id } = use(params);
  const userId = useUserId();

  const [job, setJob] = useState<ScoringJob | null>(null);
  const [scores, setScores] = useState<RequirementScore[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // ─── Multi-select state ───────────────────────────────────────────────────
  const [checkedReqIds, setCheckedReqIds] = useState<Set<string>>(new Set());
  const [rerunProgress, setRerunProgress] = useState<{ done: number; total: number } | null>(null);
  const [clearConfirming, setClearConfirming] = useState(false);
  const [clearing, setClearing] = useState(false);

  // ─── Export state ─────────────────────────────────────────────────────────
  const [exportingExcel, setExportingExcel] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    if (!userId) return;
    try {
      const [jobData, scoresData] = await Promise.all([
        getScoringJob(id, userId).catch(() => null),
        getRequirementScores(id, userId).catch(() => [] as RequirementScore[]),
      ]);
      setJob(jobData);
      setScores(scoresData);
      if (scoresData.length > 0) {
        setSelectedId(prev => {
          if (prev) return prev;
          // Prefer first scored requirement; fall back to first in list
          const firstScored = scoresData.find(s => s.status !== 'not_scored');
          return (firstScored ?? scoresData[0]).id;
        });
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load scores');
    } finally {
      setLoading(false);
    }
  }, [id, userId]);

  useEffect(() => {
    if (userId) fetchData();
  }, [fetchData, userId]);

  const handleRunScoring = async () => {
    if (!userId) return;
    setRunning(true);
    setError(null);
    try {
      await runScoring(id, userId);
      const newJob = await getScoringJob(id, userId);
      setJob(newJob);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start scoring');
    } finally {
      setRunning(false);
    }
  };

  const handleJobUpdate = useCallback(async (updatedJob: ScoringJob) => {
    setJob(updatedJob);
    if (updatedJob.status === 'completed' || updatedJob.status === 'failed') {
      const freshScores = await getRequirementScores(id, userId).catch(() => [] as RequirementScore[]);
      setScores(freshScores);
      setSelectedId(prev => prev ?? (freshScores[0]?.id ?? null));
    }
  }, [id, userId]);

  const handleRerunRequirement = async (requirementId: string) => {
    if (!userId) return;
    const updated = await rerunRequirementScore(id, requirementId, userId);
    setScores(prev => prev.map(s => s.requirement_id === requirementId ? updated : s));
    // If this was a not_scored item, its id was requirement_id; update to the real score id
    setSelectedId(prev => prev === requirementId ? updated.id : prev);
  };

  // ─── Multi-select handlers ────────────────────────────────────────────────
  const handleToggleReq = (reqId: string) => {
    setCheckedReqIds(prev => {
      const next = new Set(prev);
      if (next.has(reqId)) next.delete(reqId);
      else next.add(reqId);
      return next;
    });
  };

  const handleToggleGroup = (reqIds: string[]) => {
    setCheckedReqIds(prev => {
      const allChecked = reqIds.every(id => prev.has(id));
      const next = new Set(prev);
      if (allChecked) reqIds.forEach(id => next.delete(id));
      else reqIds.forEach(id => next.add(id));
      return next;
    });
  };

  const handleRerunSelected = async () => {
    if (!userId || checkedReqIds.size === 0 || rerunProgress) return;
    const reqIds = Array.from(checkedReqIds);
    setRerunProgress({ done: 0, total: reqIds.length });
    for (const reqId of reqIds) {
      try {
        const updated = await rerunRequirementScore(id, reqId, userId);
        setScores(prev => prev.map(s => s.requirement_id === reqId ? updated : s));
        // If this was a not_scored item, its id was requirement_id; update selectedId to the real score id
        setSelectedId(prev => prev === reqId ? updated.id : prev);
      } catch {
        // continue with remaining requirements on error
      }
      setRerunProgress(prev => prev ? { ...prev, done: prev.done + 1 } : null);
    }
    setRerunProgress(null);
    setCheckedReqIds(new Set());
    setClearConfirming(false);
  };

  // ─── Clear selected handler ───────────────────────────────────────────────
  const handleClearSelected = async () => {
    if (!userId || checkedReqIds.size === 0) return;
    setClearing(true);
    const reqIds = Array.from(checkedReqIds);
    try {
      await clearRequirementScores(id, reqIds, userId);
      // Replace cleared scores with not_scored placeholders (requirements remain in list)
      setScores(prev => prev.map(s => {
        if (!checkedReqIds.has(s.requirement_id)) return s;
        return {
          id: s.requirement_id,
          assessment_id: null,
          requirement_id: s.requirement_id,
          requirement_code: s.requirement_code,
          requirement_name: s.requirement_name,
          requirement_description: s.requirement_description,
          ancestors: s.ancestors,
          score1: null, score2: null, score3: null,
          phase1_output: null, phase2_output: null,
          phase4_output: null, phase5_output: null,
          score1_explanation: null, score2_explanation: null, score3_explanation: null,
          model_used: null, llm_calls_used: null,
          status: 'not_scored' as const,
          skip_reason: null, error_message: null, scored_at: null,
        };
      }));
      // If selected item was cleared, point selectedId to its new not_scored entry (id = requirement_id)
      setSelectedId(prev => {
        if (!prev) return null;
        const sel = scores.find(s => s.id === prev);
        return sel && checkedReqIds.has(sel.requirement_id) ? sel.requirement_id : prev;
      });
      setCheckedReqIds(new Set());
      setClearConfirming(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to clear scores');
      setClearConfirming(false);
    } finally {
      setClearing(false);
    }
  };

  // ─── Export handler ───────────────────────────────────────────────────────
  const handleExportExcel = async () => {
    setExportingExcel(true);
    setExportError(null);
    try {
      await downloadScoringExcel(id);
    } catch (err) {
      setExportError(err instanceof Error ? err.message : 'Export failed');
    } finally {
      setExportingExcel(false);
    }
  };

  // ─── Summary stats ────────────────────────────────────────────────────────
  const completedScores = scores.filter(s => s.status === 'completed');
  const avg = (values: (number | null)[]) => {
    const nums = values.filter((v): v is number => v !== null);
    if (!nums.length) return null;
    return Math.round(nums.reduce((a, b) => a + b, 0) / nums.length);
  };
  const avgScore1 = avg(completedScores.map(s => s.score1));
  const avgScore2 = avg(completedScores.map(s => s.score2));
  const avgScore3 = avg(completedScores.map(s => s.score3));

  const jobIsActive = job?.status === 'pending' || job?.status === 'running';
  const selectedScore = scores.find(s => s.id === selectedId) ?? null;
  // True when at least one checked requirement has existing score data to clear
  const checkedHaveScoredItems = Array.from(checkedReqIds).some(reqId =>
    scores.some(s => s.requirement_id === reqId && s.status !== 'not_scored')
  );
  // Show "Re-run All" only when some requirements have already been scored
  const anyScored = scores.some(s => s.status !== 'not_scored');

  if (loading) {
    return (
      <div className="flex justify-center py-12">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fadeIn">
      {/* Header */}
      <Card animated>
        <CardHeader variant="gradient">
          <div className="flex justify-between items-center">
            <CardTitle icon={<BarChart3 className="h-5 w-5" />}>Compliance Scores</CardTitle>
            <div className="flex items-center gap-2">
              {anyScored && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={handleExportExcel}
                  loading={exportingExcel}
                  leftIcon={<FileDown className="h-4 w-4" />}
                >
                  {exportingExcel ? 'Generating…' : 'Export .xlsx'}
                </Button>
              )}
              <Button
                variant="gradient"
                onClick={handleRunScoring}
                loading={running}
                disabled={jobIsActive}
                leftIcon={jobIsActive ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
              >
                {anyScored ? 'Re-run All' : 'Run Scoring'}
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-neutral-600 mb-4">
            AI-assisted scoring generates three independent scores (0–100%) per requirement:
            design coverage, risk-based best practice adequacy, and peer alignment.
          </p>

          {error && <ErrorMessage message={error} className="mb-4" />}
          {exportError && <ErrorMessage message={exportError} className="mb-4" />}

          {job && (
            <ScoringProgress
              assessmentId={id}
              job={job}
              onJobUpdate={handleJobUpdate}
            />
          )}
        </CardContent>
      </Card>

      {/* Summary stat cards */}
      {completedScores.length > 0 && (
        <div className="grid grid-cols-3 gap-4">
          {[
            { label: 'Score 1 — Met by Design', value: avgScore1, subtitle: 'Control documentation coverage' },
            { label: 'Score 2 — Risk Adequacy', value: avgScore2, subtitle: 'Best practice alignment' },
            { label: 'Score 3 — Peer Alignment', value: avgScore3, subtitle: 'Industry peer comparison' },
          ].map(({ label, value, subtitle }) => (
            <Card key={label} animated className="text-center">
              <CardContent className="pt-6">
                <p className="text-4xl font-bold text-primary-700 tabular-nums">
                  {value !== null ? `${value}%` : '—'}
                </p>
                <p className="text-sm font-semibold text-neutral-800 mt-2">{label}</p>
                <p className="text-xs text-neutral-500 mt-0.5">{subtitle}</p>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Split-panel requirement viewer */}
      {scores.length > 0 && (
        <div className="flex gap-4 items-start">
          {/* Left — requirement list */}
          <div className="w-80 flex-shrink-0">
            <div className="sticky top-4 flex flex-col max-h-[calc(100vh-16rem)] overflow-y-auto pr-1">
              {/* List header + selection toolbar */}
              <div className="flex items-center gap-2 px-1 mb-1.5">
                <p className="text-xs font-semibold text-neutral-500 flex-1">
                  Requirements ({scores.length})
                </p>
              </div>

              {/* Selection / action toolbar */}
              {(checkedReqIds.size > 0 || rerunProgress || clearing) && (
                <div className="mb-2 rounded-lg border overflow-hidden text-xs">
                  {clearConfirming ? (
                    /* ── Confirmation state ── */
                    <div className="bg-red-50 border-red-200 px-3 py-2 space-y-2">
                      <div className="flex items-center gap-1.5 text-red-700 font-medium">
                        <AlertTriangle className="h-3.5 w-3.5 flex-shrink-0" />
                        Clear {checkedReqIds.size} score{checkedReqIds.size !== 1 ? 's' : ''}? This cannot be undone.
                      </div>
                      <p className="text-red-500 leading-snug">
                        All generated score data and explanations for the selected requirements will be permanently deleted.
                      </p>
                      <div className="flex gap-2">
                        <button
                          onClick={() => setClearConfirming(false)}
                          disabled={clearing}
                          className="flex-1 py-1 rounded border border-red-300 text-red-600 hover:bg-red-100 transition-colors disabled:opacity-50"
                        >
                          Cancel
                        </button>
                        <button
                          onClick={handleClearSelected}
                          disabled={clearing}
                          className="flex-1 py-1 rounded bg-red-600 hover:bg-red-700 text-white font-semibold transition-colors disabled:opacity-50 flex items-center justify-center gap-1"
                        >
                          {clearing
                            ? <RefreshCw className="h-3 w-3 animate-spin" />
                            : <Trash2 className="h-3 w-3" />}
                          {clearing ? 'Clearing…' : 'Confirm Delete'}
                        </button>
                      </div>
                    </div>
                  ) : rerunProgress ? (
                    /* ── Re-run progress state ── */
                    <div className="bg-primary-50 border-primary-200 px-3 py-1.5 flex items-center gap-2">
                      <RefreshCw className="h-3.5 w-3.5 text-primary-500 animate-spin flex-shrink-0" />
                      <span className="text-primary-700 font-medium flex-1">
                        Re-running {rerunProgress.done}/{rerunProgress.total}…
                      </span>
                    </div>
                  ) : (
                    /* ── Normal selection state ── */
                    <div className="bg-primary-50 border-primary-200 px-2 py-1.5 flex items-center gap-1.5">
                      <span className="text-primary-700 font-medium flex-1">
                        {checkedReqIds.size} selected
                      </span>
                      <button
                        onClick={() => setCheckedReqIds(new Set())}
                        className="text-primary-400 hover:text-primary-700 transition-colors p-0.5"
                        title="Clear selection"
                      >
                        <X className="h-3.5 w-3.5" />
                      </button>
                      <button
                        onClick={handleRerunSelected}
                        className="flex items-center gap-1 font-semibold text-white bg-primary-600 hover:bg-primary-700 px-2 py-1 rounded transition-colors"
                      >
                        <RefreshCw className="h-3 w-3" />
                        Re-run
                      </button>
                      {checkedHaveScoredItems && (
                        <button
                          onClick={() => setClearConfirming(true)}
                          className="flex items-center gap-1 font-semibold text-red-600 hover:text-red-800 border border-red-200 hover:border-red-400 bg-white hover:bg-red-50 px-2 py-1 rounded transition-colors"
                        >
                          <Trash2 className="h-3 w-3" />
                          Clear
                        </button>
                      )}
                    </div>
                  )}
                </div>
              )}

              <RequirementScoreHierarchyList
                scores={scores}
                selectedId={selectedId}
                onSelect={setSelectedId}
                checkedReqIds={checkedReqIds}
                onToggleReq={handleToggleReq}
                onToggleGroup={handleToggleGroup}
              />
            </div>
          </div>

          {/* Right — detail panel */}
          <div className="flex-1 min-w-0">
            {selectedScore ? (
              <Card animated>
                <CardContent className="pt-6">
                  <RequirementScoreDetail
                    score={selectedScore}
                    onRerun={handleRerunRequirement}
                  />
                </CardContent>
              </Card>
            ) : (
              <Card animated>
                <CardContent className="py-16 text-center">
                  <BarChart3 className="h-10 w-10 text-neutral-200 mx-auto mb-3" />
                  <p className="text-sm text-neutral-400">Select a requirement to view details</p>
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      )}

      {/* Empty state — only when no requirements are in scope at all */}
      {scores.length === 0 && !jobIsActive && (
        <Card animated>
          <CardContent className="py-12 text-center">
            <BarChart3 className="h-12 w-12 text-neutral-200 mx-auto mb-4" />
            <p className="text-sm font-medium text-neutral-600">No requirements in scope</p>
            <p className="text-xs text-neutral-400 mt-1">
              Add a framework to this assessment's scope to begin scoring.
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
