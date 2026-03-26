import { Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import ProtectedRoute from './components/ProtectedRoute';
import Navigation from './components/Navigation';
import Dashboard from './pages/Dashboard';
import IMSLPSearch from './pages/IMSLPSearch';
import FileUpload from './pages/FileUpload';
import ReviewUI from './pages/ReviewUI';
import Export from './pages/Export';
import Login from './pages/Login';
import Register from './pages/Register';
import PaymentSuccess from './pages/PaymentSuccess';

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

export default function App() {
  return (
    <AuthProvider>
      <Routes>
        {/* Public routes — no navigation chrome */}
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />

        {/* Protected routes — wrapped in navigation */}
        <Route
          path="/*"
          element={
            <ProtectedRoute>
              <div style={styles.app}>
                <Navigation />
                <main style={styles.main}>
                  <Routes>
                    <Route path="/" element={<Dashboard />} />
                    <Route path="/search" element={<IMSLPSearch />} />
                    <Route path="/upload" element={<FileUpload />} />
                    <Route path="/scores/:id/review" element={<ReviewUI />} />
                    <Route path="/scores/:id/export" element={<Export />} />
                    <Route path="/payment-success" element={<PaymentSuccess />} />
                    <Route path="*" element={<Navigate to="/" replace />} />
                  </Routes>
                </main>
              </div>
            </ProtectedRoute>
          }
        />
      </Routes>
    </AuthProvider>
  );
}
