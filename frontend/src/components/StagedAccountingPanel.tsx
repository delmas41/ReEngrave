/**
 * ROADMAP 3.3c: a compact accounting panel for a STAGED job.
 *
 * Shows the exporter's own coverage figures — straight off
 * `Score.metadata_json` (`staged_unread_bars` / `staged_held_out_bars` /
 * `staged_bars_total` / `staged_held_out_staves`, written by
 * `backend/modules/staged_omr.py` off `staged.export.to_musicxml`'s own
 * report, CLAUDE.md §4d) — never recomputed here. Renders nothing for a
 * `local`/`claude_vision` job, and nothing until those fields exist (a job
 * that is still processing, or one that errored before EXPORT ran).
 *
 * "Open marked PDF" reuses the existing `exportScore(id, 'pdf')` download
 * flow (same one `Export.tsx`'s format cards use) — for a staged score,
 * `export_module.export_as_pdf` already prefers the native staged
 * exporter, which since ROADMAP 3.5 marks unread and held-out bars in red
 * with a reason word. No new backend download route: this is the SAME
 * link, generated on first request if it does not exist yet.
 */

import { useState } from 'react';
import { exportScore } from '../api/client';
import type { Score } from '../types';

const styles: Record<string, React.CSSProperties> = {
  panel: {
    border: '1px solid #dee2e6',
    borderRadius: 8,
    backgroundColor: '#f8f9fa',
    padding: '10px 14px',
    marginBottom: 16,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    flexWrap: 'wrap' as const,
    gap: 8,
  },
  text: { fontSize: 13, color: '#444', fontWeight: 600 },
  actions: { display: 'flex', alignItems: 'center', gap: 10 },
  link: {
    fontSize: 12,
    fontWeight: 700,
    color: '#2980b9',
    textDecoration: 'none',
    cursor: 'pointer',
    background: 'none',
    border: 'none',
    padding: 0,
  },
  error: { fontSize: 12, color: '#c0392b' },
};

export default function StagedAccountingPanel({ score }: { score: Score }) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const meta: Record<string, unknown> = score.metadata_json ?? {};

  if (meta.omr_engine !== 'staged') {
    return null;
  }

  const unread = meta.staged_unread_bars;
  const heldOut = meta.staged_held_out_bars;
  const barsTotal = meta.staged_bars_total;
  const heldOutStaves = meta.staged_held_out_staves;

  // Nothing written yet (still processing, or errored before EXPORT ran) —
  // show nothing rather than a panel full of zeroes that would look like a
  // clean run.
  if (
    typeof unread !== 'number' ||
    typeof heldOut !== 'number' ||
    typeof barsTotal !== 'number' ||
    typeof heldOutStaves !== 'number'
  ) {
    return null;
  }

  async function handleOpenPdf() {
    setLoading(true);
    setError(null);
    try {
      const url = await exportScore(score.id, 'pdf');
      window.open(url, '_blank', 'noopener,noreferrer');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not open the marked PDF.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={styles.panel}>
      <span style={styles.text}>
        {unread} of {barsTotal} bars unread · {heldOut} held (do not add up) ·{' '}
        {heldOutStaves} {heldOutStaves === 1 ? 'staff' : 'staves'} held out
      </span>
      <div style={styles.actions}>
        <button style={styles.link} onClick={handleOpenPdf} disabled={loading}>
          {loading ? 'Opening…' : 'Open marked PDF →'}
        </button>
        {error && <span style={styles.error}>{error}</span>}
      </div>
    </div>
  );
}
