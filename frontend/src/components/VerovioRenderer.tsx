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
        // Dynamic import to avoid blocking initial bundle load
        // TODO: Tune Verovio options for measure-level rendering:
        //   - adjustPageHeight, spacingSystem, scale, pageWidth, pageHeight
        //   - svgViewBox, header, footer
        const verovio = await import('verovio');
        const { VerovioToolkit } = verovio;

        if (cancelled) return;

        const toolkit = new VerovioToolkit();

        // TODO: Configure options for clean single-measure rendering
        toolkit.setOptions({
          scale: 40,
          adjustPageHeight: true,
          adjustPageWidth: true,
          noHeader: true,
          noFooter: true,
        } as Record<string, unknown>);

        const loaded = toolkit.loadData(measureXml);
        if (!loaded) {
          throw new Error('Verovio could not parse the MusicXML fragment');
        }

        const svg = toolkit.renderToSVG(1);

        if (cancelled) return;

        if (svgRef.current) {
          svgRef.current.innerHTML = svg;
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
