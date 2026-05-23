/**
 * GradusLibrary — master reference score library and multi-source comparison workspace.
 *
 * Tab 1 — Library:  upload/view/delete Gradus master XMLs.
 * Tab 2 — Compare:  upload 2–6 XMLs, optionally pin a Gradus master,
 *                   run comparison and view similarity matrix + measure report.
 */

import { useRef, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  createComparisonSession,
  createGradusScore,
  deleteGradusScore,
  listGradusScores,
} from '../api/client';
import type { ComparisonResult, GradusScore } from '../types';

// ---------------------------------------------------------------------------
// Styles
// ---------------------------------------------------------------------------

const styles: Record<string, React.CSSProperties> = {
  pageHeading: { fontSize: 24, fontWeight: 700, color: '#1a1a2e', marginBottom: 4 },
  pageSubtitle: { color: '#666', fontSize: 14, marginBottom: 24 },

  tabBar: { display: 'flex', gap: 4, marginBottom: 28, borderBottom: '2px solid #e9ecef' },
  tab: (active: boolean): React.CSSProperties => ({
    padding: '8px 20px',
    fontWeight: active ? 700 : 500,
    fontSize: 14,
    cursor: 'pointer',
    border: 'none',
    background: 'none',
    color: active ? '#1a1a2e' : '#666',
    borderBottom: active ? '2px solid #1a1a2e' : '2px solid transparent',
    marginBottom: -2,
  }),

  // Cards
  card: {
    background: '#fff',
    border: '1px solid #e9ecef',
    borderRadius: 10,
    padding: 20,
    marginBottom: 14,
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    gap: 16,
  },
  cardTitle: { fontWeight: 600, color: '#1a1a2e', fontSize: 15, marginBottom: 2 },
  cardMeta: { color: '#888', fontSize: 12 },

  // Form
  formCard: {
    background: '#f8f9fa',
    border: '1px solid #e9ecef',
    borderRadius: 10,
    padding: 24,
    marginBottom: 28,
  },
  formTitle: { fontWeight: 700, fontSize: 16, color: '#1a1a2e', marginBottom: 16 },
  formRow: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 12 },
  label: { display: 'block', fontSize: 12, fontWeight: 600, color: '#555', marginBottom: 4 },
  input: {
    width: '100%',
    padding: '8px 10px',
    border: '1px solid #ccc',
    borderRadius: 6,
    fontSize: 13,
    boxSizing: 'border-box' as const,
  },
  textarea: {
    width: '100%',
    padding: '8px 10px',
    border: '1px solid #ccc',
    borderRadius: 6,
    fontSize: 13,
    minHeight: 60,
    boxSizing: 'border-box' as const,
    resize: 'vertical' as const,
  },
  fileInput: { fontSize: 13, marginTop: 2 },

  // Buttons
  btnPrimary: {
    background: '#1a1a2e',
    color: '#fff',
    border: 'none',
    borderRadius: 6,
    padding: '9px 20px',
    fontWeight: 600,
    fontSize: 13,
    cursor: 'pointer',
  },
  btnDanger: {
    background: 'none',
    color: '#e74c3c',
    border: '1px solid #e74c3c',
    borderRadius: 6,
    padding: '5px 12px',
    fontSize: 12,
    cursor: 'pointer',
  },
  btnSecondary: {
    background: '#6c757d',
    color: '#fff',
    border: 'none',
    borderRadius: 6,
    padding: '9px 20px',
    fontWeight: 600,
    fontSize: 13,
    cursor: 'pointer',
  },

  // Matrix
  matrixWrap: { overflowX: 'auto' as const, marginBottom: 24 },
  table: {
    borderCollapse: 'collapse' as const,
    fontSize: 13,
    minWidth: 300,
  },
  th: {
    padding: '8px 12px',
    background: '#f8f9fa',
    border: '1px solid #dee2e6',
    fontWeight: 600,
    textAlign: 'left' as const,
    whiteSpace: 'nowrap' as const,
  },
  td: {
    padding: '7px 12px',
    border: '1px solid #dee2e6',
    textAlign: 'center' as const,
    fontWeight: 600,
    fontSize: 13,
  },

  // Measure issues
  issueRow: (agreementPct: number): React.CSSProperties => ({
    display: 'flex',
    alignItems: 'center',
    gap: 12,
    padding: '6px 12px',
    borderRadius: 6,
    marginBottom: 4,
    background:
      agreementPct >= 90
        ? '#d4edda'
        : agreementPct >= 70
        ? '#fff3cd'
        : '#f8d7da',
  }),
  issueNum: { fontWeight: 700, minWidth: 80, fontSize: 13 },
  issuePct: (agreementPct: number): React.CSSProperties => ({
    fontWeight: 700,
    fontSize: 13,
    color:
      agreementPct >= 90
        ? '#155724'
        : agreementPct >= 70
        ? '#856404'
        : '#721c24',
  }),

  sectionTitle: { fontWeight: 700, fontSize: 15, color: '#2c3e50', marginBottom: 10 },
  errorBox: {
    background: '#f8d7da',
    border: '1px solid #f5c6cb',
    borderRadius: 6,
    padding: 12,
    color: '#721c24',
    fontSize: 13,
    marginBottom: 16,
  },
  emptyState: { color: '#888', fontSize: 14, fontStyle: 'italic', padding: '16px 0' },
  spinner: { color: '#888', fontSize: 14, padding: '16px 0' },
};

// ---------------------------------------------------------------------------
// Colour helpers for similarity matrix cells
// ---------------------------------------------------------------------------

function cellStyle(pct: number, isSelf: boolean): React.CSSProperties {
  if (isSelf) return { ...styles.td, background: '#e9ecef', color: '#888' };
  const bg =
    pct >= 90 ? '#d4edda' : pct >= 70 ? '#fff3cd' : '#f8d7da';
  const color =
    pct >= 90 ? '#155724' : pct >= 70 ? '#856404' : '#721c24';
  return { ...styles.td, background: bg, color };
}

// ---------------------------------------------------------------------------
// Library tab
// ---------------------------------------------------------------------------

function LibraryTab() {
  const qc = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [formTitle, setFormTitle] = useState('');
  const [formComposer, setFormComposer] = useState('');
  const [formNotes, setFormNotes] = useState('');
  const xmlRef = useRef<HTMLInputElement>(null);
  const pdfRef = useRef<HTMLInputElement>(null);
  const [formError, setFormError] = useState<string | null>(null);

  const { data: scores, isLoading } = useQuery({
    queryKey: ['gradus-scores'],
    queryFn: listGradusScores,
  });

  const createMutation = useMutation({
    mutationFn: () => {
      const xmlFile = xmlRef.current?.files?.[0];
      if (!xmlFile) throw new Error('XML file is required');
      const pdfFile = pdfRef.current?.files?.[0];
      return createGradusScore(xmlFile, formTitle, formComposer, formNotes || undefined, pdfFile);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['gradus-scores'] });
      setShowForm(false);
      setFormTitle('');
      setFormComposer('');
      setFormNotes('');
      setFormError(null);
      if (xmlRef.current) xmlRef.current.value = '';
      if (pdfRef.current) pdfRef.current.value = '';
    },
    onError: (err: unknown) => {
      setFormError(err instanceof Error ? err.message : 'Upload failed');
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => deleteGradusScore(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['gradus-scores'] }),
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    if (!formTitle.trim() || !formComposer.trim()) {
      setFormError('Title and composer are required');
      return;
    }
    createMutation.mutate();
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <h2 style={styles.sectionTitle}>Master Reference Scores</h2>
        <button style={styles.btnPrimary} onClick={() => setShowForm((v) => !v)}>
          {showForm ? 'Cancel' : '+ Add Master Score'}
        </button>
      </div>

      {showForm && (
        <div style={styles.formCard}>
          <div style={styles.formTitle}>Upload Gradus Master Score</div>
          {formError && <div style={styles.errorBox}>{formError}</div>}
          <form onSubmit={handleSubmit}>
            <div style={styles.formRow}>
              <div>
                <label style={styles.label}>Title *</label>
                <input
                  style={styles.input}
                  value={formTitle}
                  onChange={(e) => setFormTitle(e.target.value)}
                  placeholder="e.g. Well-Tempered Clavier Book I"
                  required
                />
              </div>
              <div>
                <label style={styles.label}>Composer *</label>
                <input
                  style={styles.input}
                  value={formComposer}
                  onChange={(e) => setFormComposer(e.target.value)}
                  placeholder="e.g. J.S. Bach"
                  required
                />
              </div>
            </div>
            <div style={{ marginBottom: 12 }}>
              <label style={styles.label}>Curator Notes</label>
              <textarea
                style={styles.textarea}
                value={formNotes}
                onChange={(e) => setFormNotes(e.target.value)}
                placeholder="Optional notes about this edition or source"
              />
            </div>
            <div style={styles.formRow}>
              <div>
                <label style={styles.label}>MusicXML / MXL file *</label>
                <input ref={xmlRef} type="file" accept=".xml,.mxl,.musicxml" style={styles.fileInput} required />
              </div>
              <div>
                <label style={styles.label}>Reference PDF (optional)</label>
                <input ref={pdfRef} type="file" accept=".pdf" style={styles.fileInput} />
              </div>
            </div>
            <button
              type="submit"
              style={styles.btnPrimary}
              disabled={createMutation.isPending}
            >
              {createMutation.isPending ? 'Uploading…' : 'Save to Library'}
            </button>
          </form>
        </div>
      )}

      {isLoading && <div style={styles.spinner}>Loading library…</div>}

      {!isLoading && (!scores || scores.length === 0) && (
        <div style={styles.emptyState}>
          No master scores yet. Upload the first one above.
        </div>
      )}

      {scores?.map((score: GradusScore) => (
        <div key={score.id} style={styles.card}>
          <div style={{ flex: 1 }}>
            <div style={styles.cardTitle}>{score.title}</div>
            <div style={styles.cardMeta}>
              {score.composer} &nbsp;·&nbsp; Added {new Date(score.created_at).toLocaleDateString()}
              {score.pdf_path && ' · PDF attached'}
            </div>
            {score.notes && (
              <div style={{ fontSize: 13, color: '#555', marginTop: 6 }}>{score.notes}</div>
            )}
          </div>
          <button
            style={styles.btnDanger}
            disabled={deleteMutation.isPending}
            onClick={() => {
              if (window.confirm(`Delete "${score.title}"?`)) {
                deleteMutation.mutate(score.id);
              }
            }}
          >
            Delete
          </button>
        </div>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Compare tab
// ---------------------------------------------------------------------------

function CompareTab() {
  const xmlInputRef = useRef<HTMLInputElement>(null);
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [selectedGradusId, setSelectedGradusId] = useState<string>('');
  const [sessionName, setSessionName] = useState('');
  const [result, setResult] = useState<ComparisonResult | null>(null);
  const [resultLabels, setResultLabels] = useState<string[]>([]);
  const [compareError, setCompareError] = useState<string | null>(null);

  const { data: gradusScores } = useQuery({
    queryKey: ['gradus-scores'],
    queryFn: listGradusScores,
  });

  const compareMutation = useMutation({
    mutationFn: () =>
      createComparisonSession(
        selectedFiles,
        selectedGradusId || undefined,
        sessionName || undefined,
      ),
    onSuccess: (session) => {
      if (session.result_json) {
        try {
          const parsed: ComparisonResult = JSON.parse(session.result_json);
          setResult(parsed);
          setResultLabels(parsed.labels);
          setCompareError(parsed.error ?? null);
        } catch {
          setCompareError('Failed to parse comparison result');
        }
      }
    },
    onError: (err: unknown) => {
      setCompareError(err instanceof Error ? err.message : 'Comparison failed');
    },
  });

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files ?? []);
    if (files.length > 6) {
      setCompareError('Maximum 6 files allowed');
      return;
    }
    setSelectedFiles(files);
    setCompareError(null);
  };

  const handleRun = (e: React.FormEvent) => {
    e.preventDefault();
    setCompareError(null);
    setResult(null);
    if (selectedFiles.length < 2) {
      setCompareError('Select at least 2 XML files to compare');
      return;
    }
    compareMutation.mutate();
  };

  const friendlyLabel = (label: string, gradusLabel = 'master') => {
    if (label === 'master') return gradusLabel;
    const idx = parseInt(label.replace('source_', ''), 10);
    return selectedFiles[idx]?.name ?? label;
  };

  return (
    <div>
      <div style={styles.formCard}>
        <div style={styles.formTitle}>Compare MusicXML Sources</div>
        <p style={{ color: '#555', fontSize: 13, marginBottom: 16 }}>
          Upload 2–6 MusicXML files. Optionally include a Gradus master as the reference.
          Comparison may take 10–30 seconds for large scores.
        </p>
        {compareError && <div style={styles.errorBox}>{compareError}</div>}
        <form onSubmit={handleRun}>
          <div style={{ marginBottom: 12 }}>
            <label style={styles.label}>Session name (optional)</label>
            <input
              style={{ ...styles.input, maxWidth: 340 }}
              value={sessionName}
              onChange={(e) => setSessionName(e.target.value)}
              placeholder="e.g. Beethoven Op.18 comparison"
            />
          </div>
          <div style={{ marginBottom: 12 }}>
            <label style={styles.label}>
              MusicXML files * (2–6 files, .xml / .mxl / .musicxml)
            </label>
            <input
              ref={xmlInputRef}
              type="file"
              accept=".xml,.mxl,.musicxml"
              multiple
              style={styles.fileInput}
              onChange={handleFileChange}
              required
            />
            {selectedFiles.length > 0 && (
              <div style={{ marginTop: 6, fontSize: 12, color: '#555' }}>
                {selectedFiles.length} file(s) selected:{' '}
                {selectedFiles.map((f) => f.name).join(', ')}
              </div>
            )}
          </div>
          <div style={{ marginBottom: 16 }}>
            <label style={styles.label}>Gradus master reference (optional)</label>
            <select
              style={{ ...styles.input, maxWidth: 340 }}
              value={selectedGradusId}
              onChange={(e) => setSelectedGradusId(e.target.value)}
            >
              <option value="">— None —</option>
              {gradusScores?.map((g: GradusScore) => (
                <option key={g.id} value={g.id}>
                  {g.title} ({g.composer})
                </option>
              ))}
            </select>
          </div>
          <button
            type="submit"
            style={styles.btnPrimary}
            disabled={compareMutation.isPending}
          >
            {compareMutation.isPending ? 'Comparing… (this may take 10–30s)' : 'Run Comparison'}
          </button>
        </form>
      </div>

      {result && (
        <ComparisonResults
          result={result}
          labels={resultLabels}
          gradusScores={gradusScores ?? []}
          friendlyLabel={friendlyLabel}
        />
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Comparison results component
// ---------------------------------------------------------------------------

interface ComparisonResultsProps {
  result: ComparisonResult;
  labels: string[];
  gradusScores: GradusScore[];
  friendlyLabel: (label: string) => string;
}

function ComparisonResults({ result, labels, friendlyLabel }: ComparisonResultsProps) {
  const n = labels.length;
  const hasMaster = labels.includes('master');

  // Issues: measures where agreement < 100%
  const issues = result.per_measure_agreement.filter((m) => m.agreement_pct < 100);

  return (
    <div>
      {result.error && <div style={styles.errorBox}>Comparison error: {result.error}</div>}

      {/* Similarity matrix */}
      <div style={styles.sectionTitle}>Similarity Matrix</div>
      <p style={{ color: '#555', fontSize: 13, marginBottom: 12 }}>
        Each cell shows the percentage of measures that are identical between two sources.
        Green ≥ 90% · Yellow 70–90% · Red &lt; 70%
        {hasMaster && ' · "master" is the Gradus reference score.'}
      </p>
      <div style={styles.matrixWrap}>
        <table style={styles.table}>
          <thead>
            <tr>
              <th style={styles.th}></th>
              {labels.map((l) => (
                <th key={l} style={styles.th}>
                  {friendlyLabel(l)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {labels.map((rowLabel, i) => (
              <tr key={rowLabel}>
                <td style={{ ...styles.th, fontWeight: 700 }}>{friendlyLabel(rowLabel)}</td>
                {labels.map((colLabel, j) => {
                  const pct = result.matrix[i]?.[j] ?? 0;
                  return (
                    <td key={colLabel} style={cellStyle(pct, i === j)}>
                      {i === j ? '—' : `${pct.toFixed(1)}%`}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Measure-level issues */}
      <div style={styles.sectionTitle}>
        Measure Agreement ({issues.length} measure{issues.length !== 1 ? 's' : ''} with
        differences)
      </div>

      {issues.length === 0 && result.per_measure_agreement.length > 0 && (
        <div style={{ ...styles.emptyState, color: '#155724', fontStyle: 'normal' }}>
          All measures match across all sources.
        </div>
      )}

      {issues.length > 0 && (
        <div style={{ marginBottom: 24 }}>
          <p style={{ color: '#555', fontSize: 13, marginBottom: 10 }}>
            Measures listed below had at least one differing source.
            Agreement % = fraction of sources whose notes match the majority.
          </p>
          {issues.map((m) => (
            <div key={m.measure_num} style={styles.issueRow(m.agreement_pct)}>
              <span style={styles.issueNum}>Measure {m.measure_num}</span>
              <span style={styles.issuePct(m.agreement_pct)}>
                {m.agreement_pct.toFixed(0)}% agreement
              </span>
              <span style={{ fontSize: 12, color: '#555' }}>
                {m.sources_agreeing} of {n} source{n !== 1 ? 's' : ''} agree
              </span>
            </div>
          ))}
        </div>
      )}

      {/* Summary stats */}
      <div style={{ color: '#666', fontSize: 13 }}>
        Total measures checked: {result.per_measure_agreement.length} &nbsp;·&nbsp;
        Consensus issues: {result.consensus_issues.length}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

type Tab = 'library' | 'compare';

export default function GradusLibrary() {
  const [activeTab, setActiveTab] = useState<Tab>('library');

  return (
    <div>
      <div style={styles.pageHeading}>Gradus Library</div>
      <div style={styles.pageSubtitle}>
        Maintain a curated collection of master reference scores and compare multiple
        XML sources measure-by-measure.
      </div>

      <div style={styles.tabBar}>
        {(['library', 'compare'] as Tab[]).map((tab) => (
          <button
            key={tab}
            style={styles.tab(activeTab === tab)}
            onClick={() => setActiveTab(tab)}
          >
            {tab === 'library' ? 'Library' : 'Compare'}
          </button>
        ))}
      </div>

      {activeTab === 'library' ? <LibraryTab /> : <CompareTab />}
    </div>
  );
}
