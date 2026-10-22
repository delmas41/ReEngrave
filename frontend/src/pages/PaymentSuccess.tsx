/**
 * PaymentSuccess page.
 * Shown after Stripe redirects back with ?session_id=&score_id=
 */

import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { checkVisionAccess } from '../api/client';

export default function PaymentSuccess() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const scoreId = params.get('score_id');
  const [status, setStatus] = useState<'verifying' | 'success' | 'error'>('verifying');

  useEffect(() => {
    if (!scoreId) {
      navigate('/', { replace: true });
      return;
    }

    // Poll for access to be granted (webhook might take a moment)
    let attempts = 0;
    const maxAttempts = 10;

    const check = async () => {
      try {
        const data = await checkVisionAccess(scoreId);
        if (data.has_access) {
          setStatus('success');
          setTimeout(() => navigate(`/scores/${scoreId}/review`, { replace: true }), 2000);
        } else if (attempts < maxAttempts) {
          attempts++;
          setTimeout(check, 1500);
        } else {
          setStatus('error');
        }
      } catch {
        setStatus('error');
      }
    };

    check();
  }, [scoreId, navigate]);

  const styles: Record<string, React.CSSProperties> = {
    page: {
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      minHeight: '60vh',
      textAlign: 'center',
    },
    icon: { fontSize: 56, marginBottom: 16 },
    heading: { fontSize: 24, fontWeight: 700, color: '#1a1a2e', marginBottom: 8 },
    sub: { color: '#666', fontSize: 15 },
  };

  return (
    <div style={styles.page}>
      <div>
        {status === 'verifying' && (
          <>
            <div style={styles.icon}>⏳</div>
            <h1 style={styles.heading}>Verifying payment…</h1>
            <p style={styles.sub}>Please wait while we confirm your purchase.</p>
          </>
        )}
        {status === 'success' && (
          <>
            <div style={styles.icon}>✅</div>
            <h1 style={styles.heading}>Payment confirmed!</h1>
            <p style={styles.sub}>
              Vision AI comparison unlocked. Redirecting you back…
            </p>
          </>
        )}
        {status === 'error' && (
          <>
            <div style={styles.icon}>⚠️</div>
            <h1 style={styles.heading}>Verification taking longer than expected</h1>
            <p style={styles.sub}>
              Your payment was received. It may take a moment to process.{' '}
              {scoreId && (
                <a
                  href={`/scores/${scoreId}/review`}
                  style={{ color: '#1a1a2e', fontWeight: 600 }}
                >
                  Return to score
                </a>
              )}
            </p>
          </>
        )}
      </div>
    </div>
  );
}
