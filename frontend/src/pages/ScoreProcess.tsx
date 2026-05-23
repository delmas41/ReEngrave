/**
 * Score processing page — Step 1: ReEngrave (OMR).
 * After OMR completes, auto-advances to the vision comparison step.
 */

import { useEffect, useRef, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getScore, runOMR } from '../api/client';
import type { OMREngine, OMRProgress, ProcessingStatus } from '../types';

const STATUS_COLOR: Record<ProcessingStatus, string> = {
  pending: '#f39c12',
  processing: '#2980b9',
  review: '#27ae60',
  complete: '#27ae60',
  error: '#e74c3c',
};

const styles: Record<string, React.CSSProperties> = {
  page: { maxWidth: 680, margin: '0 auto' },
  backLink: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: 6,
    fontSize: 13,
    color: '#666',
    textDecoration: 'none',
    marginBottom: 24,
    cursor: 'pointer',
    background: 'none',
    border: 'none',
    padding: 0,
  },
  scoreTitle: { fontSize: 22, fontWeight: 700, color: '#1a1a2e', marginBottom: 2 },
  scoreMeta: { fontSize: 13, color: '#666', marginBottom: 32 },
  statusBadge: (status: ProcessingStatus): React.CSSProperties => ({
    display: 'inline-block',
    padding: '2px 10px',
    borderRadius: 10,
    backgroundColor: STATUS_COLOR[status] + '22',
    color: STATUS_COLOR[status],
    fontWeight: 600,
    fontSize: 12,
    border: `1px solid ${STATUS_COLOR[status]}44`,
    marginLeft: 8,
    textTransform: 'capitalize',
  }),
  // Step indicator
  steps: {
    display: 'flex',
    alignItems: 'center',
    gap: 0,
    marginBottom: 40,
  },
  step: (active: boolean, done: boolean): React.CSSProperties => ({
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: 6,
    flex: 1,
  }),
  stepCircle: (active: boolean, done: boolean): React.CSSProperties => ({
    width: 36,
    height: 36,
    borderRadius: '50%',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontWeight: 700,
    fontSize: 14,
    backgroundColor: done ? '#27ae60' : active ? '#1a1a2e' : '#e9ecef',
    color: done || active ? '#fff' : '#aaa',
    border: active ? '2px solid #1a1a2e' : done ? '2px solid #27ae60' : '2px solid #dee2e6',
  }),
  stepLabel: (active: boolean, done: boolean): React.CSSProperties => ({
    fontSize: 11,
    fontWeight: active || done ? 600 : 400,
    color: active ? '#1a1a2e' : done ? '#27ae60' : '#aaa',
    textAlign: 'center',
    textTransform: 'uppercase',
    letterSpacing: '0.4px',
  }),
  stepConnector: (done: boolean): React.CSSProperties => ({
    height: 2,
    flex: 1,
    backgroundColor: done ? '#27ae60' : '#dee2e6',
    marginTop: -18,
  }),
  // Main CTA card
  ctaCard: {
    border: '1px solid #dee2e6',
    borderRadius: 12,
    backgroundColor: '#fff',
    padding: '40px 32px',
    textAlign: 'center',
    boxShadow: '0 2px 8px rgba(0,0,0,0.06)',
  },
  ctaIcon: { fontSize: 48, marginBottom: 16 },
  ctaTitle: { fontSize: 20, fontWeight: 700, color: '#1a1a2e', marginBottom: 8 },
  ctaDesc: { fontSize: 14, color: '#666', lineHeight: 1.6, marginBottom: 28, maxWidth: 420, margin: '0 auto 28px' },
  primaryBtn: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: 8,
    padding: '12px 32px',
    borderRadius: 8,
    border: 'none',
    backgroundColor: '#1a1a2e',
    color: '#fff',
    fontWeight: 700,
    fontSize: 15,
    cursor: 'pointer',
    letterSpacing: '0.3px',
  },
  secondaryBtn: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: 8,
    padding: '10px 24px',
    borderRadius: 8,
    border: '1px solid #dee2e6',
    backgroundColor: '#fff',
    color: '#444',
    fontWeight: 600,
    fontSize: 14,
    cursor: 'pointer',
    marginLeft: 12,
  },
  spinner: {
    display: 'inline-block',
    width: 48,
    height: 48,
    border: '4px solid #e9ecef',
    borderTop: '4px solid #2980b9',
    borderRadius: '50%',
    animation: 'spin 1s linear infinite',
    marginBottom: 20,
  },
  processingNote: {
    backgroundColor: '#ebf5fb',
    border: '1px solid #aed6f1',
    borderRadius: 8,
    padding: '12px 16px',
    fontSize: 13,
    color: '#2980b9',
    marginTop: 20,
    display: 'inline-block',
  },
  successIcon: { fontSize: 48, color: '#27ae60', marginBottom: 16 },
  errorNote: {
    backgroundColor: '#fdedec',
    border: '1px solid #f1948a',
    borderRadius: 8,
    padding: '12px 16px',
    fontSize: 13,
    color: '#c0392b',
    marginTop: 16,
  },
};

// Inject keyframe animation once
if (typeof document !== 'undefined' && !document.getElementById('spin-style')) {
  const style = document.createElement('style');
  style.id = 'spin-style';
  style.textContent = '@keyframes spin { to { transform: rotate(360deg); } }';
  document.head.appendChild(style);
}

function StepIndicator({ currentStatus }: { currentStatus: ProcessingStatus }) {
  const isOmrDone = currentStatus !== 'pending' && currentStatus !== 'processing' && currentStatus !== 'error';
  const isReviewDone = currentStatus === 'complete';

  return (
    <div style={styles.steps}>
      <div style={styles.step(true, isOmrDone)}>
        <div style={styles.stepCircle(currentStatus === 'pending' || currentStatus === 'processing', isOmrDone)}>
          {isOmrDone ? '✓' : '1'}
        </div>
        <span style={styles.stepLabel(currentStatus === 'pending' || currentStatus === 'processing', isOmrDone)}>
          ReEngrave
        </span>
      </div>
      <div style={styles.stepConnector(isOmrDone)} />
      <div style={styles.step(isOmrDone && !isReviewDone, isReviewDone)}>
        <div style={styles.stepCircle(isOmrDone && !isReviewDone, isReviewDone)}>
          {isReviewDone ? '✓' : '2'}
        </div>
        <span style={styles.stepLabel(isOmrDone && !isReviewDone, isReviewDone)}>
          Compare & Review
        </span>
      </div>
      <div style={styles.stepConnector(isReviewDone)} />
      <div style={styles.step(isReviewDone, false)}>
        <div style={styles.stepCircle(isReviewDone, false)}>3</div>
        <span style={styles.stepLabel(isReviewDone, false)}>Export</span>
      </div>
    </div>
  );
}

export default function ScoreProcess() {
  const { id: scoreId } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [polling, setPolling] = useState(false);
  const wasProcessing = useRef(false);
  const [selectedEngine, setSelectedEngine] = useState<OMREngine>('claude_vision');

  const { data: score, isLoading } = useQuery({
    queryKey: ['score', scoreId],
    queryFn: () => getScore(scoreId!),
    refetchInterval: polling ? 2000 : false,
  });

  useEffect(() => {
    if (!score) return;
    if (score.status === 'processing') {
      wasProcessing.current = true;
      setPolling(true);
    } else {
      setPolling(false);
      // Auto-advance to review step once OMR finishes
      if (wasProcessing.current && score.status === 'review') {
        navigate(`/scores/${scoreId}/review`);
      }
    }
  }, [score?.status, scoreId, navigate]);

  const omrMutation = useMutation({
    mutationFn: () => runOMR(scoreId!, selectedEngine),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['score', scoreId] });
      wasProcessing.current = true;
      setPolling(true);
    },
    onError: (err: any) => {
      alert(err?.response?.data?.detail || err?.message || 'OMR failed to start. Please try again.');
    },
  });

  // Extract progress from metadata
  const omrProgress: OMRProgress | null = score?.metadata_json?.omr_progress as OMRProgress | null;
  const omrEngine: string = (score?.metadata_json?.omr_engine as string) || '';

  if (isLoading) {
    return <div style={styles.page}><p style={{ color: '#888', fontSize: 14 }}>Loading…</p></div>;
  }

  if (!score) {
    return <div style={styles.page}><p style={{ color: '#c0392b', fontSize: 14 }}>Score not found.</p></div>;
  }

  const isProcessing = score.status === 'processing';
  const omrDone = score.musicxml_path && score.status !== 'pending' && score.status !== 'processing';

  return (
    <div style={styles.page}>
      <button style={styles.backLink} onClick={() => navigate('/')}>
        ← All Scores
      </button>

      <h1 style={styles.scoreTitle}>
        {score.title}
        <span style={styles.statusBadge(score.status)}>{score.status}</span>
      </h1>
      <p style={styles.scoreMeta}>
        {score.composer} · {score.era} · {score.source}
      </p>

      <StepIndicator currentStatus={score.status} />

      <div style={styles.ctaCard}>
        {/* Pending — show engine selector + ReEngrave CTA */}
        {score.status === 'pending' && (
          <>
            <div style={styles.ctaIcon}>🎼</div>
            <div style={styles.ctaTitle}>Ready to ReEngrave</div>
            <p style={styles.ctaDesc}>
              Convert your PDF score to MusicXML. Choose an OMR engine below.
            </p>
            <div style={{ display: 'flex', gap: 8, marginBottom: 20, justifyContent: 'center' }}>
              <button
                style={{
                  padding: '8px 16px', borderRadius: 8, fontSize: 13, fontWeight: 600,
                  cursor: 'pointer', transition: 'all 0.15s',
                  border: selectedEngine === 'claude_vision' ? '2px solid #1a1a2e' : '2px solid #ccc',
                  background: selectedEngine === 'claude_vision' ? '#1a1a2e' : '#fff',
                  color: selectedEngine === 'claude_vision' ? '#fff' : '#555',
                }}
                onClick={() => setSelectedEngine('claude_vision')}
              >
                Claude Vision AI
              </button>
              <button
                style={{
                  padding: '8px 16px', borderRadius: 8, fontSize: 13, fontWeight: 600,
                  cursor: 'pointer', transition: 'all 0.15s',
                  border: selectedEngine === 'audiveris' ? '2px solid #1a1a2e' : '2px solid #ccc',
                  background: selectedEngine === 'audiveris' ? '#1a1a2e' : '#fff',
                  color: selectedEngine === 'audiveris' ? '#fff' : '#555',
                }}
                onClick={() => setSelectedEngine('audiveris')}
              >
                Audiveris (Java)
              </button>
            </div>
            <p style={{ color: '#888', fontSize: 12, marginBottom: 16, textAlign: 'center' as const }}>
              {selectedEngine === 'claude_vision'
                ? 'Claude Vision reads the score visually and generates MusicXML. Best quality, uses API credits.'
                : 'Audiveris runs locally via Java. Fast but often inaccurate on complex scores.'}
            </p>
            <button
              style={styles.primaryBtn}
              onClick={() => omrMutation.mutate()}
              disabled={omrMutation.isPending}
            >
              {omrMutation.isPending ? 'Starting…' : '✦ ReEngrave'}
            </button>
          </>
        )}

        {/* Processing — spinner with progress */}
        {isProcessing && (
          <>
            <div style={styles.spinner} />
            <div style={styles.ctaTitle}>
              {omrEngine === 'claude_vision'
                ? 'Claude Vision is reading your score…'
                : 'Audiveris is scanning your score…'}
            </div>
            {omrProgress && omrProgress.total_pages > 0 ? (
              <>
                <p style={{ color: '#555', fontSize: 14, marginBottom: 12, fontWeight: 600 }}>
                  Page {omrProgress.current_page} of {omrProgress.total_pages}
                </p>
                <div style={{
                  width: '100%', maxWidth: 400, height: 8, background: '#e9ecef',
                  borderRadius: 4, overflow: 'hidden', margin: '0 auto 12px',
                }}>
                  <div style={{
                    width: `${(omrProgress.current_page / omrProgress.total_pages) * 100}%`,
                    height: '100%', background: '#2980b9', borderRadius: 4,
                    transition: 'width 0.3s ease',
                  }} />
                </div>
                {omrProgress.failed_pages.length > 0 && (
                  <p style={{ color: '#e67e22', fontSize: 12 }}>
                    {omrProgress.failed_pages.length} page(s) had issues — will retry or skip
                  </p>
                )}
              </>
            ) : (
              <p style={styles.ctaDesc}>
                Preparing score for analysis. This page will automatically advance
                when processing is complete.
              </p>
            )}
            <div style={styles.processingNote}>
              Tip: you can close this tab and come back — the job runs in the background.
            </div>
          </>
        )}

        {/* OMR done — advance to comparison */}
        {omrDone && score.status !== 'error' && (
          <>
            <div style={{ fontSize: 48, marginBottom: 16 }}>✓</div>
            <div style={styles.ctaTitle}>ReEngrave Complete</div>
            <p style={styles.ctaDesc}>
              MusicXML generated successfully. Now run the vision comparison to detect
              differences between the original PDF and the engraved output.
            </p>
            <button
              style={styles.primaryBtn}
              onClick={() => navigate(`/scores/${scoreId}/review`)}
            >
              Compare & Review Differences →
            </button>
            {score.status === 'complete' && (
              <button
                style={styles.secondaryBtn}
                onClick={() => navigate(`/scores/${scoreId}/export`)}
              >
                Export Score
              </button>
            )}
          </>
        )}

        {/* Error state */}
        {score.status === 'error' && (
          <>
            <div style={{ fontSize: 48, marginBottom: 16 }}>⚠️</div>
            <div style={styles.ctaTitle}>Processing Error</div>
            <p style={styles.ctaDesc}>
              Something went wrong during OMR. You can try again or upload a different file.
            </p>
            <button
              style={styles.primaryBtn}
              onClick={() => omrMutation.mutate()}
              disabled={omrMutation.isPending}
            >
              Retry ReEngrave
            </button>
            <div style={styles.errorNote}>
              If the error persists, check that the uploaded PDF is a valid music score.
            </div>
          </>
        )}
      </div>
    </div>
  );
}
