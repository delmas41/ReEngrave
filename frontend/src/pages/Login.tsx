/**
 * Login page.
 */

import { useState, type FormEvent } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

const styles: Record<string, React.CSSProperties> = {
  page: {
    minHeight: '100vh',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#f8f9fa',
  },
  card: {
    background: '#fff',
    borderRadius: 10,
    boxShadow: '0 4px 24px rgba(0,0,0,0.10)',
    padding: '40px 36px',
    width: '100%',
    maxWidth: 400,
  },
  logo: {
    fontSize: 26,
    fontWeight: 700,
    color: '#1a1a2e',
    marginBottom: 6,
    letterSpacing: '-0.5px',
  },
  logoAccent: { color: '#e2b96f' },
  subtitle: { color: '#888', fontSize: 14, marginBottom: 28 },
  label: {
    display: 'block',
    fontSize: 13,
    fontWeight: 600,
    color: '#333',
    marginBottom: 5,
  },
  input: {
    width: '100%',
    padding: '9px 12px',
    border: '1px solid #dee2e6',
    borderRadius: 6,
    fontSize: 14,
    outline: 'none',
    boxSizing: 'border-box',
    marginBottom: 16,
  },
  btn: {
    width: '100%',
    padding: '10px 0',
    backgroundColor: '#1a1a2e',
    color: '#fff',
    border: 'none',
    borderRadius: 6,
    fontSize: 15,
    fontWeight: 600,
    cursor: 'pointer',
    marginTop: 4,
  },
  error: {
    color: '#c0392b',
    fontSize: 13,
    marginBottom: 12,
    padding: '8px 12px',
    backgroundColor: '#fdf3f2',
    borderRadius: 5,
    border: '1px solid #f5c6c0',
  },
  footer: {
    marginTop: 20,
    textAlign: 'center',
    fontSize: 13,
    color: '#666',
  },
  link: { color: '#1a1a2e', fontWeight: 600, textDecoration: 'none' },
};

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await login(email, password);
      navigate('/', { replace: true });
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        'Login failed. Please try again.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={styles.page}>
      <div style={styles.card}>
        <div style={styles.logo}>
          Re<span style={styles.logoAccent}>Engrave</span>
        </div>
        <p style={styles.subtitle}>Sign in to your account</p>

        <form onSubmit={handleSubmit}>
          {error && <div style={styles.error}>{error}</div>}

          <label style={styles.label} htmlFor="email">Email</label>
          <input
            id="email"
            type="email"
            style={styles.input}
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            autoFocus
            autoComplete="email"
          />

          <label style={styles.label} htmlFor="password">Password</label>
          <input
            id="password"
            type="password"
            style={styles.input}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            autoComplete="current-password"
          />

          <button style={styles.btn} type="submit" disabled={loading}>
            {loading ? 'Signing in…' : 'Sign in'}
          </button>
        </form>

        <div style={styles.footer}>
          Don&apos;t have an account?{' '}
          <Link to="/register" style={styles.link}>
            Sign up
          </Link>
        </div>
      </div>
    </div>
  );
}
