/**
 * PDF.js renderer component.
 * Renders a specific page of a PDF to a canvas, with optional crop region.
 */

import { useEffect, useRef, useState } from 'react';
import type { CropRegion } from '../types';

interface Props {
  pdfUrl: string;
  pageNumber: number;
  cropRegion?: CropRegion;
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
  canvas: {
    display: 'block',
    maxWidth: '100%',
  },
  spinner: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 24,
    color: '#888',
    fontSize: 13,
  },
  error: {
    color: '#c0392b',
    fontSize: 13,
    padding: 12,
    backgroundColor: '#fdf2f2',
    borderRadius: 4,
  },
};

export default function PDFjsRenderer({
  pdfUrl,
  pageNumber,
  cropRegion,
  highlightDiff = false,
}: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!pdfUrl) {
      setLoading(false);
      return;
    }

    let cancelled = false;

    async function renderPage() {
      setLoading(true);
      setError(null);

      try {
        // Dynamic import to avoid loading PDF.js in the initial bundle
        const pdfjs = await import('pdfjs-dist');

        // Set worker source – required by PDF.js
        // TODO: Host the worker file locally for production builds
        pdfjs.GlobalWorkerOptions.workerSrc = new URL(
          'pdfjs-dist/build/pdf.worker.mjs',
          import.meta.url
        ).toString();

        const loadingTask = pdfjs.getDocument(pdfUrl);
        const pdf = await loadingTask.promise;

        if (cancelled) return;

        const page = await pdf.getPage(pageNumber);
        const scale = 1.5;
        const viewport = page.getViewport({ scale });

        const canvas = canvasRef.current;
        if (!canvas || cancelled) return;

        const context = canvas.getContext('2d');
        if (!context) throw new Error('Canvas 2D context not available');

        // TODO: Implement cropRegion support:
        //   1. Render full page to an offscreen canvas.
        //   2. Use cropRegion {x, y, w, h} (in PDF units) to clip the viewport.
        //   3. Copy the cropped region to the visible canvas.
        //   This requires converting PDF coordinate space to canvas pixels.

        canvas.width = cropRegion ? cropRegion.w * scale : viewport.width;
        canvas.height = cropRegion ? cropRegion.h * scale : viewport.height;

        const renderContext = {
          canvasContext: context,
          viewport: cropRegion
            ? page.getViewport({
                scale,
                offsetX: -(cropRegion.x * scale),
                offsetY: -(cropRegion.y * scale),
              })
            : viewport,
        };

        await page.render(renderContext).promise;

        if (!cancelled) setLoading(false);
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'PDF render failed');
          setLoading(false);
        }
      }
    }

    renderPage();
    return () => {
      cancelled = true;
    };
  }, [pdfUrl, pageNumber, cropRegion]);

  return (
    <div style={styles.container(highlightDiff)}>
      <div style={styles.label}>Page {pageNumber} – Original PDF</div>
      {loading && <div style={styles.spinner}>Loading PDF…</div>}
      {error && <div style={styles.error}>Error: {error}</div>}
      <canvas ref={canvasRef} style={{ ...styles.canvas, display: loading || error ? 'none' : 'block' }} />
    </div>
  );
}
