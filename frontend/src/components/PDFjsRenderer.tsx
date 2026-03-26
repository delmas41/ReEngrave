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
        const pdfjs = await import('pdfjs-dist');

        // Resolve the worker via Vite's asset pipeline — works in dev and production.
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

        if (cropRegion) {
          // Render the full page to an offscreen canvas, then copy the crop
          // region to the visible canvas.
          //
          // cropRegion {x, y, w, h} uses canvas-space coordinates:
          //   - origin at the top-left of the rendered page
          //   - units are PDF user-space units (1 unit = scale pixels on canvas)
          //   - y increases downward

          const offscreen = document.createElement('canvas');
          offscreen.width = viewport.width;
          offscreen.height = viewport.height;
          const offCtx = offscreen.getContext('2d');
          if (!offCtx) throw new Error('Offscreen canvas 2D context not available');

          await page.render({ canvasContext: offCtx, viewport }).promise;

          if (cancelled) return;

          // Convert PDF units → canvas pixels
          const srcX = cropRegion.x * scale;
          const srcY = cropRegion.y * scale;
          const srcW = cropRegion.w * scale;
          const srcH = cropRegion.h * scale;

          canvas.width = srcW;
          canvas.height = srcH;
          context.drawImage(offscreen, srcX, srcY, srcW, srcH, 0, 0, srcW, srcH);
        } else {
          canvas.width = viewport.width;
          canvas.height = viewport.height;
          await page.render({ canvasContext: context, viewport }).promise;
        }

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
