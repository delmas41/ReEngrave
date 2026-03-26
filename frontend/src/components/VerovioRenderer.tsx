/**
 * Verovio MusicXML renderer component.
 * Dynamically loads the Verovio toolkit and renders MusicXML to SVG.
 */

import { useEffect, useRef, useState } from 'react';

interface Props {
  measureXml: string;
  measureNumber: number;
  highlightDiff?: boolean;
}

const styles: Record<string, React.CSSProperties> = {
  container: (highlight: boolean): React.CSSProperties => ({
    border: highlight ? '2px solid #e74c3c' : '1px solid #dee2e6',
    borderRadius: 6,
    padding: 8,
    backgroundColor: '#fff',
    minHeight: 80,
    position: 'relative',
  }),
  label: {
    fontSize: 11,
    color: '#666',
    marginBottom: 4,
  },
  loading: {
    color: '#888',
    fontSize: 13,
    padding: 12,
  },
  error: {
    color: '#c0392b',
    fontSize: 13,
    padding: 12,
    backgroundColor: '#fdf2f2',
    borderRadius: 4,
  },
};

// Verovio options tuned for compact, readable measure-level rendering.
// pageWidth wide enough for typical measures; adjustPageHeight trims vertical whitespace.
const VEROVIO_OPTIONS = {
  // Rendering scale (percentage of default size). 55 gives readable notation
  // without being too large for side-by-side diff comparison.
  scale: 55,
  // Trim page height to content so the SVG wraps the staves tightly.
  adjustPageHeight: true,
  // Use a fixed page width (in mm × 10) to keep layout stable across measures.
  // 2400 ≈ 240mm, wide enough for 4–6 measures on one line.
  adjustPageWidth: false,
  pageWidth: 2400,
  // Remove notation software header/footer — we show our own labels.
  noHeader: true,
  noFooter: true,
  // Spacing: tight staff and system spacing for compact view.
  spacingStaff: 4,
  spacingSystem: 0,
  // Use Bravura (SMuFL compliant) for standard notation glyphs.
  font: 'Bravura',
} as Record<string, unknown>;

export default function VerovioRenderer({
  measureXml,
  measureNumber,
  highlightDiff = false,
}: Props) {
  const svgRef = useRef<HTMLDivElement>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!measureXml) {
      setLoading(false);
      return;
    }

    let cancelled = false;

    async function render() {
      setLoading(true);
      setError(null);

      try {
        const verovio = await import('verovio');
        const { VerovioToolkit } = verovio;

        if (cancelled) return;

        const toolkit = new VerovioToolkit();
        toolkit.setOptions(VEROVIO_OPTIONS);

        const loaded = toolkit.loadData(measureXml);
        if (!loaded) {
          throw new Error('Verovio could not parse the MusicXML fragment');
        }

        const svg = toolkit.renderToSVG(1);

        if (cancelled) return;

        if (svgRef.current) {
          svgRef.current.innerHTML = svg;
          // Make the SVG responsive within the container
          const svgEl = svgRef.current.querySelector('svg');
          if (svgEl) {
            svgEl.style.maxWidth = '100%';
            svgEl.style.height = 'auto';
          }
        }
        setLoading(false);
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Render failed');
          setLoading(false);
        }
      }
    }

    render();
    return () => {
      cancelled = true;
    };
  }, [measureXml]);

  return (
    <div style={styles.container(highlightDiff)}>
      <div style={styles.label}>Measure {measureNumber} – MusicXML render</div>
      {loading && <div style={styles.loading}>Loading Verovio renderer…</div>}
      {error && <div style={styles.error}>Render error: {error}</div>}
      {!loading && !error && !measureXml && (
        <div style={styles.loading}>No MusicXML data</div>
      )}
      <div ref={svgRef} />
    </div>
  );
}
