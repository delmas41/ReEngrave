import { Routes, Route, Navigate } from 'react-router-dom';
import Navigation from './components/Navigation';
import Dashboard from './pages/Dashboard';
import IMSLPSearch from './pages/IMSLPSearch';
import FileUpload from './pages/FileUpload';
import ReviewUI from './pages/ReviewUI';
import Export from './pages/Export';

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
    <div style={styles.app}>
      <Navigation />
      <main style={styles.main}>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/search" element={<IMSLPSearch />} />
          <Route path="/upload" element={<FileUpload />} />
          <Route path="/scores/:id/review" element={<ReviewUI />} />
          <Route path="/scores/:id/export" element={<Export />} />
          {/* Catch-all redirect */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  );
}
