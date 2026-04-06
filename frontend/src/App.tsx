import { useEffect } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import Navigation from './components/Navigation';
import Dashboard from './pages/Dashboard';
import IMSLPSearch from './pages/IMSLPSearch';
import FileUpload from './pages/FileUpload';
import Login from './pages/Login';
import Register from './pages/Register';
import PaymentSuccess from './pages/PaymentSuccess';
import ScoreProcess from './pages/ScoreProcess';
import ReviewUI from './pages/ReviewUI';
import Export from './pages/Export';
import { AuthProvider, useAuth } from './context/AuthContext';
import { setAccessToken } from './api/client';

const styles: Record<string, React.CSSProperties> = {
  app: {
    minHeight: '100vh',
    backgroundColor: '#f8f9fa',
    fontFamily: "'Segoe UI', system-ui, -apple-system, sans-serif",
  },
  main: {
    maxWidth: 1200,
    margin: '0 auto',
    padding: '24px 16px',
  },
};

/** Syncs AuthContext token into the axios client and guards protected routes. */
function AppShell() {
  const { user, accessToken, isLoading } = useAuth();

  // Keep API client token in sync with auth context
  useEffect(() => {
    setAccessToken(accessToken);
  }, [accessToken]);

  if (isLoading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100vh' }}>
        <span style={{ color: '#888', fontSize: 14 }}>Loading…</span>
      </div>
    );
  }

  return (
    <div style={styles.app}>
      {user && <Navigation />}
      <main style={user ? styles.main : undefined}>
        <Routes>
          {/* Public routes */}
          <Route path="/login" element={user ? <Navigate to="/" replace /> : <Login />} />
          <Route path="/register" element={user ? <Navigate to="/" replace /> : <Register />} />
          <Route path="/payment/success" element={<PaymentSuccess />} />

          {/* Protected routes — redirect to login if not authenticated */}
          <Route path="/" element={user ? <Dashboard /> : <Navigate to="/login" replace />} />
          <Route path="/search" element={user ? <IMSLPSearch /> : <Navigate to="/login" replace />} />
          <Route path="/upload" element={user ? <FileUpload /> : <Navigate to="/login" replace />} />
          <Route path="/scores/:id/process" element={user ? <ScoreProcess /> : <Navigate to="/login" replace />} />
          <Route path="/scores/:id/review" element={user ? <ReviewUI /> : <Navigate to="/login" replace />} />
          <Route path="/scores/:id/export" element={user ? <Export /> : <Navigate to="/login" replace />} />

          {/* Catch-all */}
          <Route path="*" element={<Navigate to={user ? '/' : '/login'} replace />} />
        </Routes>
      </main>
    </div>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <AppShell />
    </AuthProvider>
  );
}
