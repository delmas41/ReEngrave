/**
 * VisionComparisonPaywall
 * Shown in ReviewUI when the user hasn't paid for Vision AI on this score.
 * Handles checkout redirect and admin bypass display.
 */

import { useState } from 'react';
import { createCheckoutSession } from '../api/client';

interface Props {
  scoreId: string;
  isAdmin: boolean;
  onAccessGranted: () => void;
}

export default function VisionComparisonPaywall({ scoreId, isAdmin, onAccessGranted }: Props) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  async function handlePay() {
    setError('');
    setLoading(true);
    try {
      const data = await createCheckoutSession(scoreId);
      if (data.has_access) {
        // Admin bypass or already paid
        onAccessGranted();
        return;
      }
      if (data.checkout_url) {
        window.location.href = data.checkout_url;
      }
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        'Could not start checkout. Please try again.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  }

  const styles: Record<string, React.CSSProperties> = {
    container: {
      border: '1px solid #e2b96f44',
      borderRadius: 10,
      backgroundColor: '#fffdf5',
      padding: '28px 32px',
      margin: '24px 0',
      maxWidth: 520,
    },
    badge: {
      display: 'inline-block',
      backgroundColor: '#e2b96f22',
      color: '#b8880a',
      fontSize: 11,
      fontWeight: 700,
      letterSpacing: 0.5,
      padding: '3px 10px',
      borderRadius: 20,
      border: '1px solid #e2b96f55',
      textTransform: 'uppercase',
      marginBottom: 12,
    },
    heading: {
      fontSize: 18,
      fontWeight: 700,
      color: '#1a1a2e',
      marginBottom: 8,
    },
    desc: {
      fontSize: 14,
      color: '#555',
      lineHeight: 1.6,
      marginBottom: 20,
    },
    price: {
      fontSize: 28,
      fontWeight: 700,
      color: '#1a1a2e',
      marginBottom: 4,
    },
    priceSub: { fontSize: 13, color: '#888', marginBottom: 20 },
    btn: {
      padding: '11px 28px',
      backgroundColor: '#1a1a2e',
      color: '#fff',
      border: 'none',
      borderRadius: 6,
      fontSize: 15,
      fontWeight: 600,
      cursor: 'pointer',
    },
    adminBtn: {
      padding: '11px 28px',
      backgroundColor: '#27ae60',
      color: '#fff',
      border: 'none',
      borderRadius: 6,
      fontSize: 15,
      fontWeight: 600,
      cursor: 'pointer',
    },
    error: {
      color: '#c0392b',
      fontSize: 13,
      marginTop: 12,
    },
    feature: {
      display: 'flex',
      alignItems: 'center',
      gap: 8,
      fontSize: 13,
      color: '#444',
      marginBottom: 6,
    },
    check: { color: '#27ae60', fontWeight: 700 },
  };

  return (
    <div style={styles.container}>
      <div style={styles.badge}>Paid Feature</div>
      <h2 style={styles.heading}>Claude Vision AI Comparison</h2>
      <p style={styles.desc}>
        Compare your original PDF against the re-engraved MusicXML using Claude&apos;s
        vision capabilities. Claude reviews each measure and flags differences in notes,
        rhythms, articulation, and more.
      </p>

      <div>
        {[
          'Measure-by-measure visual comparison',
          'Confidence scores for each difference',
          'Detailed descriptions with instrument context',
          'One-time payment per score',
        ].map((f) => (
          <div key={f} style={styles.feature}>
            <span style={styles.check}>✓</span> {f}
          </div>
        ))}
      </div>

      <div style={{ marginTop: 20 }}>
        {isAdmin ? (
          <>
            <div style={styles.price}>Free</div>
            <div style={styles.priceSub}>Admin account — full access</div>
            <button style={styles.adminBtn} onClick={handlePay} disabled={loading}>
              {loading ? 'Unlocking…' : 'Unlock Vision Comparison'}
            </button>
          </>
        ) : (
          <>
            <div style={styles.price}>$5</div>
            <div style={styles.priceSub}>One-time payment for this score</div>
            <button style={styles.btn} onClick={handlePay} disabled={loading}>
              {loading ? 'Redirecting…' : 'Pay $5 to unlock →'}
            </button>
          </>
        )}
        {error && <div style={styles.error}>{error}</div>}
      </div>
    </div>
  );
}
