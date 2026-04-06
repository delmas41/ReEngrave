/**
 * Dashboard — score library and analytics hub.
 * Lists all scores with status and quick-access actions.
 */

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import {
  getLearningReport,
  getPatterns,
  listScores,
  deleteScore,
  triggerAnalyticsUpdate,
  triggerFinetuningExport,
} from '../api/client';
import type { KnowledgePattern, PatternSummary, ProcessingStatus, Score } from '../types';

// ---------------------------------------------------------------------------
// Styles
// ---------------------------------------------------------------------------

const STATUS_COLOR: Record<ProcessingStatus, string> = {
  pending: '#f39c12',
  processing: '#2980b9',
  review: '#8e44ad',
  complete: '#27ae60',
  error: '#e74c3c',
};

const STATUS_STEP: Record<ProcessingStatus, string> = {
  pending: 'Step 1: ReEngrave',
  processing: 'Step 1: Processing…',
  review: 'Step 2: Review',
  complete: 'Complete',
  error: 'Error',
};

const styles: Record<string, React.CSSProperties> = {
  sectionTitle: { fontSize: 16, fontWeight: 700, color: '#2c3e50', marginBottom: 16 },
  pageHeading: { fontSize: 24, fontWeight: 700, color: '#1a1a2e', marginBottom: 4 },
  pageSubtitle: { color: '#666', fontSize: 14, marginBottom: 28 },

  // Score list
  scoreGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))',
    gap: 14,
    marginBottom: 32,
  },
  scoreCard: {
    border: '1px solid #dee2e6',
    borderRadius: 10,
    backgroundColor: '#fff',
    padding: '16px 18px',
    boxShadow: '0 1px 4px rgba(0,0,0,0.05)',
    display: 'flex',
    flexDirection: 'column' as const,
    gap: 10,
  },
  scoreCardTop: {
    display: 'flex',
    alignItems: 'flex-start',
    justifyContent: 'space-between',
    gap: 8,
  },
  scoreTitle: { fontSize: 15, fontWeight: 700, color: '#1a1a2e', lineHeight: 1.3 },
  scoreMeta: { fontSize: 12, color: '#888', marginTop: 2 },
  statusBadge: (status: ProcessingStatus): React.CSSProperties => ({
    flexShrink: 0,
    display: 'inline-block',
    padding: '2px 10px',
    borderRadius: 10,
    backgroundColor: STATUS_COLOR[status] + '22',
    color: STATUS_COLOR[status],
    fontWeight: 600,
    fontSize: 11,
    border: `1px solid ${STATUS_COLOR[status]}44`,
    textTransform: 'capitalize',
    whiteSpace: 'nowrap' as const,
  }),
  stepLabel: (status: ProcessingStatus): React.CSSProperties => ({
    fontSize: 11,
    color: STATUS_COLOR[status],
    fontWeight: 600,
    backgroundColor: STATUS_COLOR[status] + '11',
    border: `1px solid ${STATUS_COLOR[status]}33`,
    borderRadius: 4,
    padding: '2px 8px',
    display: 'inline-block',
  }),
  scoreActions: { display: 'flex', gap: 8, marginTop: 4 },
  continueBtn: {
    flex: 1,
    padding: '7px 12px',
    borderRadius: 6,
    border: 'none',
    backgroundColor: '#1a1a2e',
    color: '#fff',
    fontWeight: 600,
    fontSize: 12,
    cursor: 'pointer',
    textAlign: 'center' as const,
  },
  exportBtn: {
    padding: '7px 14px',
    borderRadius: 6,
    border: '1px solid #27ae60',
    backgroundColor: '#fff',
    color: '#27ae60',
    fontWeight: 600,
    fontSize: 12,
    cursor: 'pointer',
  },
  deleteBtn: {
    padding: '7px 10px',
    borderRadius: 6,
    border: '1px solid #eee',
    backgroundColor: '#fff',
    color: '#ccc',
    fontWeight: 600,
    fontSize: 12,
    cursor: 'pointer',
  },
  newScoreRow: {
    display: 'flex',
    gap: 10,
    marginBottom: 24,
    flexWrap: 'wrap' as const,
  },
  newBtn: (variant: 'primary' | 'secondary'): React.CSSProperties => ({
    padding: '9px 18px',
    borderRadius: 7,
    border: variant === 'primary' ? 'none' : '1px solid #dee2e6',
    backgroundColor: variant === 'primary' ? '#1a1a2e' : '#fff',
    color: variant === 'primary' ? '#fff' : '#444',
    fontWeight: 600,
    fontSize: 13,
    cursor: 'pointer',
  }),
  emptyState: {
    border: '2px dashed #dee2e6',
    borderRadius: 10,
    padding: '40px 24px',
    textAlign: 'center' as const,
    color: '#aaa',
    fontSize: 14,
    marginBottom: 32,
  },
  emptyIcon: { fontSize: 36, marginBottom: 12 },
  divider: { borderTop: '1px solid #f0f0f0', margin: '8px 0 28px' },

  // Analytics section (collapsed by default)
  analyticsToggle: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    fontSize: 16,
    fontWeight: 700,
    color: '#2c3e50',
    cursor: 'pointer',
    background: 'none',
    border: 'none',
    padding: 0,
    marginBottom: 20,
  },
  statsGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))',
    gap: 14,
    marginBottom: 28,
  },
  statCard: {
    border: '1px solid #dee2e6',
    borderRadius: 8,
    padding: '16px 18px',
    backgroundColor: '#fff',
    boxShadow: '0 1px 3px rgba(0,0,0,0.04)',
  },
  statValue: { fontSize: 28, fontWeight: 800, color: '#1a1a2e', lineHeight: 1 },
  statLabel: { fontSize: 12, color: '#888', marginTop: 4, fontWeight: 500 },
  section: {
    border: '1px solid #dee2e6',
    borderRadius: 8,
    padding: 20,
    backgroundColor: '#fff',
    marginBottom: 20,
  },
  table: { width: '100%', borderCollapse: 'collapse' as const, fontSize: 13 },
  th: {
    textAlign: 'left' as const,
    padding: '7px 10px',
    borderBottom: '2px solid #eee',
    color: '#888',
    fontWeight: 600,
    fontSize: 11,
    textTransform: 'uppercase' as const,
    letterSpacing: '0.5px',
  },
  td: { padding: '8px 10px', borderBottom: '1px solid #f5f5f5', color: '#444' },
  pill: (pct: number): React.CSSProperties => {
    const color = pct >= 0.8 ? '#27ae60' : pct >= 0.5 ? '#f39c12' : '#e74c3c';
    return {
      display: 'inline-block',
      padding: '1px 8px',
      borderRadius: 10,
      backgroundColor: color + '20',
      color,
      fontWeight: 600,
      fontSize: 12,
      border: `1px solid ${color}40`,
    };
  },
  suggestion: {
    padding: '8px 12px',
    borderRadius: 6,
    backgroundColor: '#f0f8ff',
    border: '1px solid #bee3f8',
    fontSize: 13,
    color: '#2980b9',
    marginBottom: 8,
  },
  actionRow: { display: 'flex', gap: 10, marginBottom: 20, flexWrap: 'wrap' as const },
  btn: (variant: 'primary' | 'secondary'): React.CSSProperties => ({
    padding: '8px 18px',
    borderRadius: 6,
    border: variant === 'primary' ? 'none' : '1px solid #dee2e6',
    backgroundColor: variant === 'primary' ? '#1a1a2e' : '#fff',
    color: variant === 'primary' ? '#fff' : '#444',
    fontWeight: 600,
    fontSize: 13,
    cursor: 'pointer',
  }),
};

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function StatCard({ value, label }: { value: number | string; label: string }) {
  return (
    <div style={styles.statCard}>
      <div style={styles.statValue}>{value}</div>
      <div style={styles.statLabel}>{label}</div>
    </div>
  );
}

function toChartData(patterns: PatternSummary[]) {
  return patterns.map((p) => ({
    name: `${p.difference_type}${p.instrument ? ` (${p.instrument})` : ''}`,
    accept: Math.round(p.accept_rate * 100),
    reject: Math.round((1 - p.accept_rate) * 100),
    count: p.occurrences,
  }));
}

function continueRoute(score: Score): string {
  if (score.status === 'pending' || score.status === 'processing' || score.status === 'error') {
    return `/scores/${score.id}/process`;
  }
  return `/scores/${score.id}/review`;
}

function continueBtnLabel(score: Score): string {
  if (score.status === 'pending') return 'ReEngrave →';
  if (score.status === 'processing') return 'View Progress →';
  if (score.status === 'error') return 'Retry →';
  if (score.status === 'complete') return 'Review Again →';
  return 'Continue Review →';
}

function ScoreCard({ score, onDelete }: { score: Score; onDelete: (id: string) => void }) {
  const navigate = useNavigate();
  const canExport = score.status === 'review' || score.status === 'complete';
  const dateStr = new Date(score.created_at).toLocaleDateString(undefined, {
    month: 'short', day: 'numeric', year: 'numeric',
  });

  return (
    <div style={styles.scoreCard}>
      <div style={styles.scoreCardTop}>
        <div>
          <div style={styles.scoreTitle}>{score.title}</div>
          <div style={styles.scoreMeta}>{score.composer} · {score.era} · {dateStr}</div>
        </div>
        <span style={styles.statusBadge(score.status)}>{score.status}</span>
      </div>

      <span style={styles.stepLabel(score.status)}>{STATUS_STEP[score.status]}</span>

      <div style={styles.scoreActions}>
        <button
          style={styles.continueBtn}
          onClick={() => navigate(continueRoute(score))}
        >
          {continueBtnLabel(score)}
        </button>
        {canExport && (
          <button
            style={styles.exportBtn}
            onClick={() => navigate(`/scores/${score.id}/export`)}
          >
            Export
          </button>
        )}
        <button
          style={styles.deleteBtn}
          onClick={() => {
            if (window.confirm(`Delete "${score.title}"?`)) onDelete(score.id);
          }}
          title="Delete score"
        >
          ✕
        </button>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export default function Dashboard() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [showAnalytics, setShowAnalytics] = useState(false);

  const { data: scores = [], isLoading: scoresLoading } = useQuery({
    queryKey: ['scores'],
    queryFn: listScores,
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => deleteScore(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['scores'] }),
  });

  const { data: report, isLoading: reportLoading } = useQuery({
    queryKey: ['learning-report'],
    queryFn: getLearningReport,
    enabled: showAnalytics,
  });

  const { data: patterns = [], isLoading: patternsLoading } = useQuery({
    queryKey: ['patterns'],
    queryFn: getPatterns,
    enabled: showAnalytics,
  });

  const updateMutation = useMutation({
    mutationFn: triggerAnalyticsUpdate,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['learning-report'] });
      qc.invalidateQueries({ queryKey: ['patterns'] });
    },
  });

  const exportMutation = useMutation({
    mutationFn: triggerFinetuningExport,
  });

  const chartData = report ? toChartData(report.top_patterns) : [];

  return (
    <div>
      <h1 style={styles.pageHeading}>My Scores</h1>
      <p style={styles.pageSubtitle}>
        Import a new score or continue where you left off.
      </p>

      {/* New score actions */}
      <div style={styles.newScoreRow}>
        <button style={styles.newBtn('primary')} onClick={() => navigate('/search')}>
          + Search IMSLP
        </button>
        <button style={styles.newBtn('secondary')} onClick={() => navigate('/upload')}>
          + Upload File
        </button>
      </div>

      {/* Score list */}
      {scoresLoading && (
        <p style={{ color: '#888', fontSize: 14, marginBottom: 24 }}>Loading scores…</p>
      )}
      {!scoresLoading && scores.length === 0 && (
        <div style={styles.emptyState}>
          <div style={styles.emptyIcon}>🎼</div>
          <div style={{ fontWeight: 600, color: '#666', marginBottom: 8 }}>No scores yet</div>
          <div>Search IMSLP or upload a PDF to get started.</div>
        </div>
      )}
      {scores.length > 0 && (
        <div style={styles.scoreGrid}>
          {scores.map((score: Score) => (
            <ScoreCard
              key={score.id}
              score={score}
              onDelete={(id) => deleteMutation.mutate(id)}
            />
          ))}
        </div>
      )}

      <div style={styles.divider} />

      {/* Analytics — collapsible */}
      <button
        style={styles.analyticsToggle}
        onClick={() => setShowAnalytics((v) => !v)}
      >
        <span>{showAnalytics ? '▾' : '▸'}</span>
        Analytics &amp; Learning Insights
      </button>

      {showAnalytics && (
        <>
          <div style={styles.actionRow}>
            <button
              style={styles.btn('primary')}
              onClick={() => updateMutation.mutate()}
              disabled={updateMutation.isPending}
            >
              {updateMutation.isPending ? 'Updating…' : 'Update Analysis'}
            </button>
            <button
              style={styles.btn('secondary')}
              onClick={() => exportMutation.mutate()}
              disabled={exportMutation.isPending}
            >
              {exportMutation.isPending ? 'Exporting…' : 'Export Fine-tuning Dataset'}
            </button>
            {exportMutation.isSuccess && (
              <span style={{ fontSize: 13, color: '#27ae60', alignSelf: 'center' }}>
                Exported to {exportMutation.data?.path}
              </span>
            )}
          </div>

          {reportLoading ? (
            <p style={{ color: '#888', fontSize: 14 }}>Loading report…</p>
          ) : report ? (
            <>
              <div style={styles.statsGrid}>
                <StatCard value={report.total_scores} label="Total Scores" />
                <StatCard value={report.total_corrections} label="Diffs Reviewed" />
                <StatCard
                  value={`${(report.accept_rate * 100).toFixed(1)}%`}
                  label="Overall Accept Rate"
                />
                <StatCard value={report.active_auto_rules} label="Active Auto-Rules" />
              </div>

              {chartData.length > 0 && (
                <div style={styles.section}>
                  <div style={styles.sectionTitle}>Diff Types — Accept vs Reject Rate</div>
                  <ResponsiveContainer width="100%" height={240}>
                    <BarChart data={chartData} margin={{ top: 4, right: 8, left: 0, bottom: 4 }}>
                      <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                      <YAxis unit="%" tick={{ fontSize: 11 }} />
                      <Tooltip formatter={(v: number) => `${v}%`} />
                      <Legend />
                      <Bar dataKey="accept" name="Accept %" fill="#27ae60" />
                      <Bar dataKey="reject" name="Reject %" fill="#e74c3c" />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              )}

              {report.suggested_improvements.length > 0 && (
                <div style={styles.section}>
                  <div style={styles.sectionTitle}>Learning Insights</div>
                  {report.suggested_improvements.map((s, i) => (
                    <div key={i} style={styles.suggestion}>{s}</div>
                  ))}
                </div>
              )}

              {report.active_auto_rules_detail.length > 0 && (
                <div style={styles.section}>
                  <div style={styles.sectionTitle}>Active Auto-Accept Rules</div>
                  <table style={styles.table}>
                    <thead>
                      <tr>
                        <th style={styles.th}>Instrument</th>
                        <th style={styles.th}>Diff Type</th>
                        <th style={styles.th}>Confirmations</th>
                        <th style={styles.th}>Description</th>
                      </tr>
                    </thead>
                    <tbody>
                      {report.active_auto_rules_detail.map((r) => (
                        <tr key={r.id}>
                          <td style={styles.td}>{r.instrument ?? 'All'}</td>
                          <td style={styles.td}>{r.difference_type}</td>
                          <td style={styles.td}>{r.confirmations}</td>
                          <td style={styles.td}>{r.description}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </>
          ) : null}

          <div style={styles.section}>
            <div style={styles.sectionTitle}>Knowledge Patterns</div>
            {patternsLoading && <p style={{ color: '#aaa', fontSize: 13, textAlign: 'center', padding: 16 }}>Loading patterns…</p>}
            {!patternsLoading && patterns.length === 0 && (
              <p style={{ color: '#aaa', fontSize: 13, textAlign: 'center', padding: 16 }}>
                No patterns yet. Review some diffs to build the knowledge base.
              </p>
            )}
            {patterns.length > 0 && (
              <table style={styles.table}>
                <thead>
                  <tr>
                    <th style={styles.th}>Instrument</th>
                    <th style={styles.th}>Diff Type</th>
                    <th style={styles.th}>Era</th>
                    <th style={styles.th}>Occurrences</th>
                    <th style={styles.th}>Accept Rate</th>
                    <th style={styles.th}>Pattern</th>
                  </tr>
                </thead>
                <tbody>
                  {patterns.map((p: KnowledgePattern) => {
                    const acceptRate = p.occurrence_count > 0 ? p.accept_count / p.occurrence_count : 0;
                    return (
                      <tr key={p.id}>
                        <td style={styles.td}>{p.instrument ?? '—'}</td>
                        <td style={styles.td}>{p.difference_type}</td>
                        <td style={styles.td}>{p.era ?? '—'}</td>
                        <td style={styles.td}>{p.occurrence_count}</td>
                        <td style={styles.td}>
                          <span style={styles.pill(acceptRate)}>
                            {(acceptRate * 100).toFixed(0)}%
                          </span>
                        </td>
                        <td style={styles.td}>{p.pattern_description}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
          </div>
        </>
      )}
    </div>
  );
}
