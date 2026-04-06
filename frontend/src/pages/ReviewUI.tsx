/**
 * ReviewUI page — Step 2: Vision comparison + diff review.
 * Run comparison, then review each flagged difference before exporting.
 */

import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  getScore,
  getDiffs,
  recordDecision,
  runComparison,
} from '../api/client';
import DiffCard from '../components/DiffCard';
import type { FlaggedDifference, HumanDecision } from '../types';

type Filter = 'all' | 'pending' | 'accepted' | 'rejected' | 'edited';

const styles: Record<string, React.CSSProperties> = {
  backLink: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: 6,
    fontSize: 13,
    color: '#666',
    textDecoration: 'none',
    marginBottom: 24,
    cursor: 'pointer',
    background: 'none',
    border: 'none',
    padding: 0,
  },
  heading: { fontSize: 22, fontWeight: 700, color: '#1a1a2e', marginBottom: 2 },
  meta: { fontSize: 13, color: '#666', marginBottom: 24 },
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
  // Comparison CTA card (shown when no diffs yet)
  compareCard: {
    border: '1px solid #dee2e6',
    borderRadius: 12,
    backgroundColor: '#fff',
    padding: '32px',
    textAlign: 'center',
    boxShadow: '0 2px 8px rgba(0,0,0,0.06)',
    marginBottom: 24,
  },
  compareTitle: { fontSize: 18, fontWeight: 700, color: '#1a1a2e', marginBottom: 8 },
  compareDesc: { fontSize: 14, color: '#666', lineHeight: 1.6, marginBottom: 24, maxWidth: 400, margin: '0 auto 24px' },
  primaryBtn: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: 8,
    padding: '10px 24px',
    borderRadius: 8,
    border: 'none',
    backgroundColor: '#1a1a2e',
    color: '#fff',
    fontWeight: 700,
    fontSize: 14,
    cursor: 'pointer',
  },
  secondaryBtn: (disabled?: boolean): React.CSSProperties => ({
    display: 'inline-flex',
    alignItems: 'center',
    gap: 8,
    padding: '8px 18px',
    borderRadius: 6,
    border: '1px solid #dee2e6',
    backgroundColor: '#fff',
    color: disabled ? '#aaa' : '#444',
    fontWeight: 600,
    fontSize: 13,
    cursor: disabled ? 'default' : 'pointer',
  }),
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
  actionRow: { display: 'flex', gap: 10, marginBottom: 20, flexWrap: 'wrap' as const, alignItems: 'center' },
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
  exportBanner: {
    border: '1px solid #a9dfbf',
    borderRadius: 8,
    backgroundColor: '#eafaf1',
    padding: '14px 18px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    flexWrap: 'wrap' as const,
    gap: 12,
    marginBottom: 20,
  },
  exportBannerText: { fontSize: 14, color: '#1e8449', fontWeight: 600 },
  exportBtn: {
    padding: '8px 20px',
    borderRadius: 6,
    border: 'none',
    backgroundColor: '#27ae60',
    color: '#fff',
    fontWeight: 700,
    fontSize: 13,
    cursor: 'pointer',
  },
  processingNote: {
    backgroundColor: '#ebf5fb',
    border: '1px solid #aed6f1',
    borderRadius: 6,
    padding: '10px 14px',
    fontSize: 13,
    color: '#2980b9',
    marginBottom: 16,
  },
  empty: { color: '#888', fontSize: 14, textAlign: 'center' as const, padding: 32 },
  error: { color: '#c0392b', fontSize: 14 },
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
  const [filter, setFilter] = useState<Filter>('pending');
  const [pollingEnabled, setPollingEnabled] = useState(false);

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

  const runCompareMutation = useMutation({
    mutationFn: () => runComparison(scoreId!),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['score', scoreId] });
      qc.invalidateQueries({ queryKey: ['diffs', scoreId] });
      setPollingEnabled(true);
    },
  });

  if (scoreError) {
    return <p style={styles.error}>Failed to load score.</p>;
  }

  const reviewed = diffs.filter((d) => d.human_decision !== null || d.auto_accepted).length;
  const total = diffs.length;
  const pct = total > 0 ? Math.round((reviewed / total) * 100) : 0;
  const allReviewed = total > 0 && reviewed === total;
  const pendingCount = diffs.filter((d) => d.human_decision === null && !d.auto_accepted).length;

  const filteredDiffs = filterDiffs(diffs, filter);

  return (
    <div>
      <button style={styles.backLink} onClick={() => navigate('/')}>
        ← All Scores
      </button>

      <div style={{ marginBottom: 24 }}>
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

      {/* Processing banner */}
      {score?.status === 'processing' && (
        <div style={styles.processingNote}>
          Comparison running… this page will refresh automatically.
        </div>
      )}

      {/* No diffs yet — show comparison CTA */}
      {total === 0 && score?.status !== 'processing' && (
        <div style={styles.compareCard}>
          <div style={{ fontSize: 40, marginBottom: 12 }}>🔍</div>
          <div style={styles.compareTitle}>Run Vision Comparison</div>
          <p style={styles.compareDesc}>
            Claude Vision will compare each measure of your original PDF against the
            re-engraved MusicXML to flag any differences for your review.
          </p>
          <button
            style={styles.primaryBtn}
            onClick={() => runCompareMutation.mutate()}
            disabled={runCompareMutation.isPending || !score?.musicxml_path}
          >
            {runCompareMutation.isPending ? 'Starting…' : '✦ Run Vision Comparison'}
          </button>
        </div>
      )}

      {/* All reviewed — export banner */}
      {allReviewed && (
        <div style={styles.exportBanner}>
          <span style={styles.exportBannerText}>
            ✓ All {total} differences reviewed — ready to export!
          </span>
          <button
            style={styles.exportBtn}
            onClick={() => navigate(`/scores/${scoreId}/export`)}
          >
            Export Score →
          </button>
        </div>
      )}

      {/* Action row (re-run comparison + progress context) */}
      {total > 0 && (
        <div style={styles.actionRow}>
          <button
            style={styles.secondaryBtn(runCompareMutation.isPending)}
            onClick={() => runCompareMutation.mutate()}
            disabled={runCompareMutation.isPending || score?.status === 'processing'}
          >
            {runCompareMutation.isPending ? 'Starting…' : '↻ Re-run Comparison'}
          </button>
          {!allReviewed && (
            <span style={{ fontSize: 13, color: '#888' }}>
              {pendingCount} difference{pendingCount !== 1 ? 's' : ''} pending review
            </span>
          )}
        </div>
      )}

      {/* Progress bar */}
      {total > 0 && (
        <div>
          <div style={styles.progressLabel}>
            {reviewed} of {total} reviewed ({pct}%)
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
              {key === 'pending' && pendingCount > 0 && (
                <span> ({pendingCount})</span>
              )}
            </button>
          ))}
        </div>
      )}

      {/* Diff cards */}
      {filteredDiffs.length === 0 && total === 0 && score?.status !== 'processing' && null}
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
