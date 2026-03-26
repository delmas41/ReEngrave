/**
 * File Upload page.
 * Supports uploading PDF scans or MusicXML files directly.
 */

import { useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { uploadPDF, uploadMusicXML } from '../api/client';

type Era = 'baroque' | 'classical' | 'romantic' | 'modern';

interface UploadFormState {
  title: string;
  composer: string;
  era: Era;
  file: File | null;
}

const INITIAL_STATE: UploadFormState = {
  title: '',
  composer: '',
  era: 'classical',
  file: null,
};

const styles: Record<string, React.CSSProperties> = {
  heading: { fontSize: 24, fontWeight: 700, marginBottom: 4, color: '#1a1a2e' },
  subtitle: { color: '#666', marginBottom: 32, fontSize: 14 },
  section: {
    border: '1px solid #dee2e6',
    borderRadius: 8,
    padding: 24,
    backgroundColor: '#fff',
    marginBottom: 24,
  },
  sectionTitle: { fontSize: 16, fontWeight: 700, marginBottom: 16, color: '#2c3e50' },
  sectionDesc: { fontSize: 13, color: '#888', marginBottom: 16 },
  field: { marginBottom: 14 },
  label: { display: 'block', fontSize: 13, fontWeight: 600, color: '#444', marginBottom: 4 },
  input: {
    width: '100%',
    padding: '9px 12px',
    borderRadius: 6,
    border: '1px solid #ccc',
    fontSize: 14,
    boxSizing: 'border-box' as const,
    outline: 'none',
  },
  select: {
    width: '100%',
    padding: '9px 12px',
    borderRadius: 6,
    border: '1px solid #ccc',
    fontSize: 14,
    boxSizing: 'border-box' as const,
    backgroundColor: '#fff',
  },
  fileInput: {
    display: 'block',
    width: '100%',
    padding: '9px 0',
    fontSize: 13,
    color: '#555',
  },
  btn: (disabled: boolean): React.CSSProperties => ({
    padding: '10px 22px',
    borderRadius: 6,
    border: 'none',
    backgroundColor: disabled ? '#ccc' : '#1a1a2e',
    color: '#fff',
    fontWeight: 600,
    fontSize: 14,
    cursor: disabled ? 'not-allowed' : 'pointer',
    marginTop: 8,
  }),
  progress: {
    color: '#2980b9',
    fontSize: 13,
    marginTop: 12,
  },
  error: { color: '#c0392b', fontSize: 13, marginTop: 12 },
  success: { color: '#27ae60', fontSize: 13, marginTop: 12 },
};

function UploadForm({
  sectionTitle,
  description,
  accept,
  buttonLabel,
  onSubmit,
}: {
  sectionTitle: string;
  description: string;
  accept: string;
  buttonLabel: string;
  onSubmit: (state: UploadFormState) => Promise<void>;
}) {
  const [form, setForm] = useState<UploadFormState>(INITIAL_STATE);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const valid = form.title.trim() && form.composer.trim() && form.file !== null;

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!valid) return;
    setUploading(true);
    setError(null);
    setSuccess(false);
    try {
      await onSubmit(form);
      setSuccess(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed');
    } finally {
      setUploading(false);
    }
  }

  return (
    <form style={styles.section} onSubmit={handleSubmit} noValidate>
      <div style={styles.sectionTitle}>{sectionTitle}</div>
      <p style={styles.sectionDesc}>{description}</p>

      <div style={styles.field}>
        <label style={styles.label}>Title *</label>
        <input
          style={styles.input}
          required
          placeholder="e.g. Partita No. 2 in D minor"
          value={form.title}
          onChange={(e) => setForm((s) => ({ ...s, title: e.target.value }))}
        />
      </div>
      <div style={styles.field}>
        <label style={styles.label}>Composer *</label>
        <input
          style={styles.input}
          required
          placeholder="e.g. Johann Sebastian Bach"
          value={form.composer}
          onChange={(e) => setForm((s) => ({ ...s, composer: e.target.value }))}
        />
      </div>
      <div style={styles.field}>
        <label style={styles.label}>Era</label>
        <select
          style={styles.select}
          value={form.era}
          onChange={(e) => setForm((s) => ({ ...s, era: e.target.value as Era }))}
        >
          <option value="baroque">Baroque (before 1750)</option>
          <option value="classical">Classical (1750–1820)</option>
          <option value="romantic">Romantic (1820–1910)</option>
          <option value="modern">Modern (1910–present)</option>
        </select>
      </div>
      <div style={styles.field}>
        <label style={styles.label}>File *</label>
        <input
          style={styles.fileInput}
          type="file"
          accept={accept}
          onChange={(e) =>
            setForm((s) => ({ ...s, file: e.target.files?.[0] ?? null }))
          }
        />
      </div>

      <button style={styles.btn(!valid || uploading)} type="submit" disabled={!valid || uploading}>
        {uploading ? 'Uploading…' : buttonLabel}
      </button>

      {uploading && <p style={styles.progress}>Uploading and processing…</p>}
      {error && <p style={styles.error}>{error}</p>}
      {success && <p style={styles.success}>Upload successful! Redirecting…</p>}
    </form>
  );
}

export default function FileUpload() {
  const navigate = useNavigate();

  async function handlePdfUpload(form: UploadFormState) {
    const score = await uploadPDF(form.file!, form.title, form.composer, form.era);
    setTimeout(() => navigate(`/scores/${score.id}/review`), 800);
  }

  async function handleXmlUpload(form: UploadFormState) {
    const score = await uploadMusicXML(form.file!, form.title, form.composer, form.era);
    setTimeout(() => navigate(`/scores/${score.id}/review`), 800);
  }

  return (
    <div>
      <h1 style={styles.heading}>Upload Score</h1>
      <p style={styles.subtitle}>
        Upload a PDF scan for OMR processing, or a MusicXML file to go straight to review.
      </p>

      <UploadForm
        sectionTitle="Upload PDF Scan"
        description="Upload a scanned PDF. Audiveris will run OMR to convert it to MusicXML, then Claude Vision will compare the output against the original."
        accept=".pdf"
        buttonLabel="Upload PDF"
        onSubmit={handlePdfUpload}
      />

      <UploadForm
        sectionTitle="Upload MusicXML"
        description="Upload an existing MusicXML file. Claude Vision will compare it against a blank reference to identify any anomalies."
        accept=".xml,.musicxml,.mxl"
        buttonLabel="Upload MusicXML"
        onSubmit={handleXmlUpload}
      />
    </div>
  );
}
