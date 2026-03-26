/**
 * Dashboard / analytics page.
 * Shows learning stats, correction patterns, and auto-accept rules.
 */

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
  triggerAnalyticsUpdate,
  triggerFinetuningExport,
} from '../api/client';
import type { KnowledgePattern, PatternSummary } from '../types';

const styles: Record<string, React.CSSProperties> = {
  heading: { fontSize: 24, fontWeight: 700, color: '#1a1a2e', marginBottom: 4 },
  subtitle: { color: '#666', fontSize: 14, marginBottom: 28 },
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
  sectionTitle: { fontSize: 16, fontWeight: 700, color: '#2c3e50', marginBottom: 16 },
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
  empty: { color: '#aaa', fontSize: 13, textAlign: 'center' as const, padding: 16 },
};

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

export default function Dashboard() {
  const qc = useQueryClient();

  const { data: report, isLoading: reportLoading } = useQuery({
    queryKey: ['learning-report'],
    queryFn: getLearningReport,
  });

  const { data: patterns = [], isLoading: patternsLoading } = useQuery({
    queryKey: ['patterns'],
    queryFn: getPatterns,
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
      <h1 style={styles.heading}>Dashboard</h1>
      <p style={styles.subtitle}>
        Self-improving agent statistics, correction patterns, and auto-accept rules.
      </p>

      {/* Action buttons */}
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

      {/* Summary stats */}
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

          {/* Bar chart */}
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

          {/* Suggestions */}
          {report.suggested_improvements.length > 0 && (
            <div style={styles.section}>
              <div style={styles.sectionTitle}>Learning Insights</div>
              {report.suggested_improvements.map((s, i) => (
                <div key={i} style={styles.suggestion}>{s}</div>
              ))}
            </div>
          )}

          {/* Active auto-rules */}
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

      {/* Knowledge patterns table */}
      <div style={styles.section}>
        <div style={styles.sectionTitle}>Knowledge Patterns</div>
        {patternsLoading && <p style={styles.empty}>Loading patterns…</p>}
        {!patternsLoading && patterns.length === 0 && (
          <p style={styles.empty}>No patterns yet. Review some diffs to build the knowledge base.</p>
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
                const acceptRate =
                  p.occurrence_count > 0
                    ? p.accept_count / p.occurrence_count
                    : 0;
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
    </div>
  );
}
