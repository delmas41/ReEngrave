/**
 * ReviewUI page.
 * Main interface for reviewing flagged differences between PDF and MusicXML.
 */

import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  getScore,
  getDiffs,
  recordDecision,
  runOMR,
  runComparison,
  getScoreStatus,
  checkVisionAccess,
} from '../api/client';
import DiffCard from '../components/DiffCard';
import VisionComparisonPaywall from '../components/VisionComparisonPaywall';
import type { FlaggedDifference, HumanDecision } from '../types';

type Filter = 'all' | 'pending' | 'accepted' | 'rejected' | 'edited';

const styles: Record<string, React.CSSProperties> = {
  heading: { fontSize: 22, fontWeight: 700, color: '#1a1a2e', marginBottom: 2 },
  meta: { fontSize: 13, color: '#666', marginBottom: 20 },
  statusBadge: (status: string): React.CSSProperties => {
    const colors: Record<string, string> = {
      pending: '#f39c12',
      processing: '#2980b9',
      review: '#8e44ad',
      complete: '#27ae60',
      error: '#e74c3c',
    };
    const c = colors[status] ?? '#7f8c8d';
    return {
      display: 'inline-block',
      padding: '2px 10px',
      borderRadius: 10,
      backgroundColor: c + '22',
      color: c,
      fontWeight: 600,
      fontSize: 12,
      border: `1px solid ${c}44`,
      marginLeft: 8,
      textTransform: 'capitalize',
    };
  },
  progressBar: {
    height: 8,
    borderRadius: 4,
    backgroundColor: '#e9ecef',
    marginBottom: 20,
    overflow: 'hidden',
  },
  progressFill: (pct: number): React.CSSProperties => ({
    height: '100%',
    width: `${pct}%`,
    backgroundColor: '#27ae60',
    borderRadius: 4,
    transition: 'width 0.3s',
  }),
  progressLabel: { fontSize: 12, color: '#666', marginBottom: 6 },
  filterRow: { display: 'flex', gap: 8, marginBottom: 20, flexWrap: 'wrap' as const },
  filterBtn: (active: boolean): React.CSSProperties => ({
    padding: '5px 14px',
    borderRadius: 16,
    border: active ? '1px solid #1a1a2e' : '1px solid #dee2e6',
    backgroundColor: active ? '#1a1a2e' : '#fff',
    color: active ? '#fff' : '#555',
    fontSize: 13,
    cursor: 'pointer',
    fontWeight: active ? 600 : 400,
  }),
  actionRow: { display: 'flex', gap: 10, marginBottom: 20, flexWrap: 'wrap' as const },
  actionBtn: (variant: 'primary' | 'secondary'): React.CSSProperties => ({
    padding: '8px 18px',
    borderRadius: 6,
    border: variant === 'primary' ? 'none' : '1px solid #dee2e6',
    backgroundColor: variant === 'primary' ? '#1a1a2e' : '#fff',
    color: variant === 'primary' ? '#fff' : '#444',
    fontWeight: 600,
    fontSize: 13,
    cursor: 'pointer',
  }),
  empty: { color: '#888', fontSize: 14, textAlign: 'center' as const, padding: 32 },
  error: { color: '#c0392b', fontSize: 14 },
  processingNote: {
    backgroundColor: '#ebf5fb',
    border: '1px solid #aed6f1',
    borderRadius: 6,
    padding: '10px 14px',
    fontSize: 13,
    color: '#2980b9',
    marginBottom: 16,
  },
};

const FILTER_LABELS: { key: Filter; label: string }[] = [
  { key: 'all', label: 'All' },
  { key: 'pending', label: 'Pending' },
  { key: 'accepted', label: 'Accepted' },
  { key: 'rejected', label: 'Rejected' },
  { key: 'edited', label: 'Edited' },
];

function filterDiffs(diffs: FlaggedDifference[], filter: Filter): FlaggedDifference[] {
  switch (filter) {
    case 'pending': return diffs.filter((d) => d.human_decision === null && !d.auto_accepted);
    case 'accepted': return diffs.filter((d) => d.human_decision === 'accept' || d.auto_accepted);
    case 'rejected': return diffs.filter((d) => d.human_decision === 'reject');
    case 'edited': return diffs.filter((d) => d.human_decision === 'edit');
    default: return diffs;
  }
}

export default function ReviewUI() {
  const { id: scoreId } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [filter, setFilter] = useState<Filter>('all');
  const [pollingEnabled, setPollingEnabled] = useState(false);

  const { data: visionAccess, refetch: refetchAccess } = useQuery({
    queryKey: ['vision-access', scoreId],
    queryFn: () => checkVisionAccess(scoreId!),
    enabled: !!scoreId,
  });

  const { data: score, error: scoreError } = useQuery({
    queryKey: ['score', scoreId],
    queryFn: () => getScore(scoreId!),
    refetchInterval: pollingEnabled ? 3000 : false,
  });

  const { data: diffs = [] } = useQuery({
    queryKey: ['diffs', scoreId],
    queryFn: () => getDiffs(scoreId!),
    enabled: !!scoreId,
    refetchInterval: pollingEnabled ? 3000 : false,
  });

  // Start polling when status is 'processing'
  useEffect(() => {
    setPollingEnabled(score?.status === 'processing');
  }, [score?.status]);

  const decideMutation = useMutation({
    mutationFn: ({
      diffId,
      decision,
      editValue,
    }: {
      diffId: string;
      decision: HumanDecision;
      editValue?: string;
    }) => recordDecision(diffId, decision, editValue),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['diffs', scoreId] }),
  });

  const runOMRMutation = useMutation({
    mutationFn: () => runOMR(scoreId!),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['score', scoreId] });
      setPollingEnabled(true);
    },
  });

  const runCompareMutation = useMutation({
    mutationFn: () => runComparison(scoreId!),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['score', scoreId] });
      setPollingEnabled(true);
    },
  });

  if (scoreError) {
    return <p style={styles.error}>Failed to load score.</p>;
  }

  const reviewed = diffs.filter(
    (d) => d.human_decision !== null || d.auto_accepted
  ).length;
  const total = diffs.length;
  const pct = total > 0 ? Math.round((reviewed / total) * 100) : 0;
  const allReviewed = total > 0 && reviewed === total;

  const filteredDiffs = filterDiffs(diffs, filter);

  return (
    <div>
      <div>
        <h1 style={styles.heading}>
          {score?.title ?? 'Loading…'}
          {score && <span style={styles.statusBadge(score.status)}>{score.status}</span>}
        </h1>
        {score && (
          <p style={styles.meta}>
            {score.composer} · {score.era} · source: {score.source}
          </p>
        )}
      </div>

      {score?.status === 'processing' && (
        <div style={styles.processingNote}>
          Processing in progress… this page will refresh automatically.
        </div>
      )}

      {/* Action buttons */}
      <div style={styles.actionRow}>
        {score?.status === 'pending' && (
          <button
            style={styles.actionBtn('primary')}
            onClick={() => runOMRMutation.mutate()}
            disabled={runOMRMutation.isPending}
          >
            {runOMRMutation.isPending ? 'Starting OMR…' : 'Run OMR'}
          </button>
        )}
        {score?.musicxml_path && score.status !== 'processing' && visionAccess?.has_access && (
          <button
            style={styles.actionBtn('secondary')}
            onClick={() => runCompareMutation.mutate()}
            disabled={runCompareMutation.isPending}
          >
            {runCompareMutation.isPending ? 'Starting…' : 'Run Vision Comparison'}
          </button>
        )}
        {allReviewed && (
          <button
            style={styles.actionBtn('primary')}
            onClick={() => navigate(`/scores/${scoreId}/export`)}
          >
            Proceed to Export →
          </button>
        )}
      </div>

      {/* Progress bar */}
      {total > 0 && (
        <div>
          <div style={styles.progressLabel}>
            {reviewed} of {total} differences reviewed ({pct}%)
          </div>
          <div style={styles.progressBar}>
            <div style={styles.progressFill(pct)} />
          </div>
        </div>
      )}

      {/* Filter buttons */}
      {total > 0 && (
        <div style={styles.filterRow}>
          {FILTER_LABELS.map(({ key, label }) => (
            <button
              key={key}
              style={styles.filterBtn(filter === key)}
              onClick={() => setFilter(key)}
            >
              {label}
              {key === 'pending' && (
                <span> ({diffs.filter((d) => d.human_decision === null && !d.auto_accepted).length})</span>
              )}
            </button>
          ))}
        </div>
      )}

      {/* Vision paywall — shown only when score has MusicXML but no access yet */}
      {score?.musicxml_path && visionAccess && !visionAccess.has_access && (
        <VisionComparisonPaywall
          scoreId={scoreId!}
          isAdmin={visionAccess.is_admin}
          onAccessGranted={() => {
            refetchAccess();
            qc.invalidateQueries({ queryKey: ['score', scoreId] });
          }}
        />
      )}

      {/* Diff cards */}
      {filteredDiffs.length === 0 && total === 0 && (
        <div style={styles.empty}>
          No flagged differences yet.
          {score?.status === 'review' && ' Run a comparison to detect differences.'}
        </div>
      )}
      {filteredDiffs.length === 0 && total > 0 && (
        <div style={styles.empty}>No differences match the selected filter.</div>
      )}

      {filteredDiffs.map((diff) => (
        <DiffCard
          key={diff.id}
          diff={diff}
          onDecide={(id, decision, editValue) =>
            decideMutation.mutate({ diffId: id, decision, editValue })
          }
        />
      ))}
    </div>
  );
}
