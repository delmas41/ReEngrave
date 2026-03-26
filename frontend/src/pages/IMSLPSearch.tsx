/**
 * IMSLP Search page.
 * Search for scores on IMSLP, browse results, and kick off the download pipeline.
 */

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { searchIMSLP, downloadScore } from '../api/client';
import type { IMSLPSearchResult } from '../types';

const styles: Record<string, React.CSSProperties> = {
  heading: { fontSize: 24, fontWeight: 700, marginBottom: 4, color: '#1a1a2e' },
  subtitle: { color: '#666', marginBottom: 24, fontSize: 14 },
  searchRow: { display: 'flex', gap: 10, marginBottom: 24 },
  input: {
    flex: 1,
    padding: '10px 14px',
    borderRadius: 6,
    border: '1px solid #ccc',
    fontSize: 14,
    outline: 'none',
  },
  btn: {
    padding: '10px 20px',
    borderRadius: 6,
    border: 'none',
    backgroundColor: '#1a1a2e',
    color: '#fff',
    fontWeight: 600,
    fontSize: 14,
    cursor: 'pointer',
  },
  card: {
    border: '1px solid #dee2e6',
    borderRadius: 8,
    padding: '14px 16px',
    marginBottom: 12,
    backgroundColor: '#fff',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    gap: 16,
  },
  title: { fontWeight: 600, fontSize: 15, color: '#2c3e50', marginBottom: 2 },
  meta: { fontSize: 12, color: '#666', marginBottom: 6 },
  description: { fontSize: 12, color: '#888', lineHeight: 1.4 },
  eraBadge: (era: string): React.CSSProperties => {
    const colors: Record<string, string> = {
      baroque: '#8e44ad',
      classical: '#2980b9',
      romantic: '#c0392b',
      modern: '#27ae60',
    };
    const c = colors[era] ?? '#7f8c8d';
    return {
      display: 'inline-block',
      padding: '1px 8px',
      borderRadius: 10,
      backgroundColor: c + '20',
      color: c,
      fontSize: 11,
      fontWeight: 600,
      border: `1px solid ${c}40`,
      marginRight: 6,
      textTransform: 'capitalize',
    };
  },
  pdfCount: { fontSize: 11, color: '#999' },
  downloadBtn: {
    padding: '7px 14px',
    borderRadius: 6,
    border: '1px solid #2980b9',
    backgroundColor: '#fff',
    color: '#2980b9',
    fontWeight: 600,
    fontSize: 13,
    cursor: 'pointer',
    whiteSpace: 'nowrap' as const,
    flexShrink: 0,
  },
  status: { fontSize: 13, color: '#888', marginTop: 16, textAlign: 'center' as const },
  error: { color: '#c0392b', fontSize: 14, marginTop: 16 },
};

export default function IMSLPSearch() {
  const navigate = useNavigate();
  const [query, setQuery] = useState('');
  const [submittedQuery, setSubmittedQuery] = useState('');
  const [downloadingId, setDownloadingId] = useState<string | null>(null);

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['imslp-search', submittedQuery],
    queryFn: () => searchIMSLP(submittedQuery, 10),
    enabled: submittedQuery.length > 0,
  });

  function handleSearch() {
    if (query.trim()) setSubmittedQuery(query.trim());
  }

  async function handleDownload(result: IMSLPSearchResult) {
    const firstPdf = result.pdf_urls[0];
    if (!firstPdf) {
      alert('No PDF URL available for this score.');
      return;
    }
    const key = result.url;
    setDownloadingId(key);
    try {
      const res = await downloadScore(firstPdf, result.title, result.composer, result.era);
      navigate(`/scores/${res.score_id}/process`);
    } catch (err) {
      alert('Download failed. See console for details.');
      console.error(err);
    } finally {
      setDownloadingId(null);
    }
  }

  return (
    <div>
      <h1 style={styles.heading}>IMSLP Search</h1>
      <p style={styles.subtitle}>
        Search the International Music Score Library Project for public domain scores.
      </p>

      <div style={styles.searchRow}>
        <input
          style={styles.input}
          placeholder="Search by title or composer (e.g. Bach Partita, Mozart Sonata)"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
        />
        <button style={styles.btn} onClick={handleSearch} disabled={isLoading}>
          {isLoading ? 'Searching…' : 'Search'}
        </button>
      </div>

      {error && (
        <p style={styles.error}>
          Search failed: {error instanceof Error ? error.message : 'Unknown error'}
        </p>
      )}

      {isLoading && <p style={styles.status}>Searching IMSLP…</p>}

      {data && data.length === 0 && (
        <p style={styles.status}>No results found for "{submittedQuery}".</p>
      )}

      {data?.map((result) => (
        <div key={result.url} style={styles.card}>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={styles.title}>{result.title}</div>
            <div style={styles.meta}>
              <span style={styles.eraBadge(result.era)}>{result.era}</span>
              {result.composer || 'Unknown composer'}
              {result.pdf_urls.length > 0 && (
                <span style={styles.pdfCount}> · {result.pdf_urls.length} PDF(s)</span>
              )}
            </div>
            {result.description && (
              <div style={styles.description}>{result.description}</div>
            )}
          </div>
          <button
            style={{
              ...styles.downloadBtn,
              opacity: result.pdf_urls.length === 0 ? 0.4 : 1,
            }}
            disabled={
              result.pdf_urls.length === 0 || downloadingId === result.url
            }
            onClick={() => handleDownload(result)}
          >
            {downloadingId === result.url ? 'Downloading…' : 'Download & Process'}
          </button>
        </div>
      ))}
    </div>
  );
}
