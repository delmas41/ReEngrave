/**
 * Export page.
 * Choose export format and download the re-engraved score.
 */

import { useState } from 'react';
import { useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { getScore, exportScore } from '../api/client';
import type { ExportFormat } from '../types';

interface FormatCard {
  format: ExportFormat;
  label: string;
  extension: string;
  description: string;
  icon: string;
}

const FORMAT_CARDS: FormatCard[] = [
  {
    format: 'lilypond',
    label: 'LilyPond',
    extension: '.ly',
    description: 'Source file for further engraving customization. Edit notation parameters, spacing, and style before final rendering.',
    icon: '🎼',
  },
  {
    format: 'musicxml',
    label: 'MusicXML',
    extension: '.xml',
    description: 'Standard interchange format for notation software (Finale, Sibelius, MuseScore). Includes all accepted corrections.',
    icon: '📄',
  },
  {
    format: 'pdf',
    label: 'Engraved PDF',
    extension: '.pdf',
    description: 'Publication-quality typeset score engraved via LilyPond. Includes full score and optionally individual parts.',
    icon: '🖨️',
  },
];

const styles: Record<string, React.CSSProperties> = {
  heading: { fontSize: 22, fontWeight: 700, color: '#1a1a2e', marginBottom: 4 },
  meta: { fontSize: 13, color: '#666', marginBottom: 28 },
  grid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 16 },
  card: {
    border: '1px solid #dee2e6',
    borderRadius: 10,
    padding: 20,
    backgroundColor: '#fff',
    display: 'flex',
    flexDirection: 'column' as const,
    gap: 12,
  },
  icon: { fontSize: 32 },
  cardTitle: { fontWeight: 700, fontSize: 15, color: '#2c3e50' },
  ext: { fontSize: 11, color: '#888', fontFamily: 'monospace', marginLeft: 6 },
  desc: { fontSize: 13, color: '#666', lineHeight: 1.5, flex: 1 },
  checkbox: { display: 'flex', alignItems: 'center', gap: 8, fontSize: 13, color: '#555', cursor: 'pointer' },
  btn: (loading: boolean): React.CSSProperties => ({
    padding: '9px 18px',
    borderRadius: 6,
    border: 'none',
    backgroundColor: loading ? '#ccc' : '#1a1a2e',
    color: '#fff',
    fontWeight: 600,
    fontSize: 13,
    cursor: loading ? 'not-allowed' : 'pointer',
    marginTop: 4,
  }),
  progress: { fontSize: 12, color: '#2980b9', textAlign: 'center' as const },
  link: {
    display: 'block',
    padding: '8px 14px',
    borderRadius: 6,
    border: '1px solid #27ae60',
    backgroundColor: '#eafaf1',
    color: '#27ae60',
    fontWeight: 600,
    fontSize: 13,
    textDecoration: 'none',
    textAlign: 'center' as const,
  },
  error: { color: '#c0392b', fontSize: 12 },
  separator: { borderTop: '1px solid #eee', margin: '8px 0' },
};

function FormatCardUI({ card, scoreId }: { card: FormatCard; scoreId: string }) {
  const [includeParts, setIncludeParts] = useState(false);
  const [loading, setLoading] = useState(false);
  const [downloadUrl, setDownloadUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleExport() {
    setLoading(true);
    setError(null);
    setDownloadUrl(null);
    try {
      const url = await exportScore(scoreId, card.format);
      setDownloadUrl(url);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Export failed');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={styles.card}>
      <div style={styles.icon}>{card.icon}</div>
      <div>
        <span style={styles.cardTitle}>{card.label}</span>
        <span style={styles.ext}>{card.extension}</span>
      </div>
      <p style={styles.desc}>{card.description}</p>

      {card.format === 'pdf' && (
        <label style={styles.checkbox}>
          <input
            type="checkbox"
            checked={includeParts}
            onChange={(e) => setIncludeParts(e.target.checked)}
          />
          Include individual parts
        </label>
      )}

      <div style={styles.separator} />

      {downloadUrl ? (
        <a
          href={downloadUrl}
          download={`export${card.extension}`}
          style={styles.link}
        >
          Download {card.label}
        </a>
      ) : (
        <button style={styles.btn(loading)} onClick={handleExport} disabled={loading}>
          {loading ? 'Generating…' : `Export as ${card.label}`}
        </button>
      )}

      {loading && <p style={styles.progress}>Engraving score, please wait…</p>}
      {error && <p style={styles.error}>{error}</p>}
    </div>
  );
}

export default function Export() {
  const { id: scoreId } = useParams<{ id: string }>();

  const { data: score } = useQuery({
    queryKey: ['score', scoreId],
    queryFn: () => getScore(scoreId!),
    enabled: !!scoreId,
  });

  return (
    <div>
      <h1 style={styles.heading}>Export Score</h1>
      <p style={styles.meta}>
        {score
          ? `${score.title} by ${score.composer} · ${score.era}`
          : 'Loading score details…'}
      </p>

      <div style={styles.grid}>
        {FORMAT_CARDS.map((card) => (
          <FormatCardUI key={card.format} card={card} scoreId={scoreId!} />
        ))}
      </div>
    </div>
  );
}
