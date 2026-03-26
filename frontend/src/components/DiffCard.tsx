/**
 * Card component for a single flagged difference.
 * Displays measure info, confidence scores, side-by-side snippet images,
 * and accept/reject/edit controls.
 */

import { useState } from 'react';
import type { FlaggedDifference, HumanDecision } from '../types';

interface Props {
  diff: FlaggedDifference;
  onDecide: (id: string, decision: HumanDecision, editValue?: string) => void;
}

function ConfidenceBadge({ value, label }: { value: number; label: string }) {
  const color =
    value >= 0.8 ? '#27ae60' : value >= 0.5 ? '#f39c12' : '#e74c3c';
  return (
    <span
      style={{
        display: 'inline-block',
        padding: '2px 8px',
        borderRadius: 12,
        backgroundColor: color + '22',
        color,
        fontSize: 11,
        fontWeight: 600,
        marginRight: 6,
        border: `1px solid ${color}44`,
      }}
    >
      {label}: {(value * 100).toFixed(0)}%
    </span>
  );
}

const DECISION_COLORS: Record<HumanDecision, string> = {
  accept: '#27ae60',
  reject: '#e74c3c',
  edit: '#8e44ad',
};

const DIFF_TYPE_COLORS: Record<string, string> = {
  note: '#3498db',
  rhythm: '#e67e22',
  articulation: '#9b59b6',
  dynamic: '#1abc9c',
  beam: '#e74c3c',
  slur: '#2980b9',
  accidental: '#f39c12',
  clef: '#16a085',
  other: '#7f8c8d',
};

const styles: Record<string, React.CSSProperties> = {
  card: {
    border: '1px solid #dee2e6',
    borderRadius: 8,
    backgroundColor: '#fff',
    marginBottom: 16,
    overflow: 'hidden',
    boxShadow: '0 1px 4px rgba(0,0,0,0.06)',
  },
  header: {
    padding: '12px 16px',
    borderBottom: '1px solid #f0f0f0',
    display: 'flex',
    alignItems: 'center',
    gap: 10,
    flexWrap: 'wrap' as const,
  },
  measureBadge: {
    fontWeight: 700,
    fontSize: 13,
    color: '#2c3e50',
  },
  diffTypeBadge: (type: string): React.CSSProperties => ({
    padding: '2px 10px',
    borderRadius: 12,
    backgroundColor: (DIFF_TYPE_COLORS[type] ?? '#7f8c8d') + '22',
    color: DIFF_TYPE_COLORS[type] ?? '#7f8c8d',
    fontSize: 11,
    fontWeight: 600,
    border: `1px solid ${(DIFF_TYPE_COLORS[type] ?? '#7f8c8d')}44`,
    textTransform: 'capitalize' as const,
  }),
  instrument: {
    fontSize: 12,
    color: '#666',
  },
  autoBadge: {
    padding: '2px 8px',
    borderRadius: 10,
    backgroundColor: '#e8f8f5',
    color: '#1abc9c',
    fontSize: 11,
    fontWeight: 600,
    border: '1px solid #a9dfcf',
    marginLeft: 'auto',
  },
  body: {
    padding: '12px 16px',
  },
  description: {
    fontSize: 13,
    color: '#444',
    marginBottom: 12,
    lineHeight: 1.5,
  },
  snippets: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: 12,
    marginBottom: 12,
  },
  snippetBox: {
    border: '1px solid #eee',
    borderRadius: 6,
    padding: 8,
    backgroundColor: '#fafafa',
    textAlign: 'center' as const,
    minHeight: 80,
    display: 'flex',
    flexDirection: 'column' as const,
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
  },
  snippetLabel: {
    fontSize: 10,
    color: '#888',
    fontWeight: 600,
    textTransform: 'uppercase' as const,
    letterSpacing: '0.5px',
  },
  snippetImg: {
    maxWidth: '100%',
    maxHeight: 100,
    objectFit: 'contain' as const,
  },
  snippetPlaceholder: {
    color: '#bbb',
    fontSize: 12,
  },
  actions: {
    display: 'flex',
    gap: 8,
    alignItems: 'center',
    flexWrap: 'wrap' as const,
  },
  btn: (variant: 'accept' | 'reject' | 'edit' | 'submit'): React.CSSProperties => {
    const colorMap = {
      accept: '#27ae60',
      reject: '#e74c3c',
      edit: '#8e44ad',
      submit: '#2980b9',
    };
    const c = colorMap[variant];
    return {
      padding: '6px 16px',
      borderRadius: 6,
      border: `1px solid ${c}`,
      backgroundColor: '#fff',
      color: c,
      fontWeight: 600,
      fontSize: 13,
      cursor: 'pointer',
      transition: 'background-color 0.15s',
    };
  },
  decisionBadge: (decision: HumanDecision): React.CSSProperties => ({
    padding: '4px 14px',
    borderRadius: 12,
    backgroundColor: DECISION_COLORS[decision] + '22',
    color: DECISION_COLORS[decision],
    fontSize: 12,
    fontWeight: 700,
    border: `1px solid ${DECISION_COLORS[decision]}44`,
    textTransform: 'capitalize' as const,
  }),
  textarea: {
    width: '100%',
    minHeight: 80,
    fontFamily: 'monospace',
    fontSize: 12,
    padding: 8,
    border: '1px solid #ccc',
    borderRadius: 4,
    marginBottom: 8,
    boxSizing: 'border-box' as const,
    resize: 'vertical' as const,
  },
};

export default function DiffCard({ diff, onDecide }: Props) {
  const [editMode, setEditMode] = useState(false);
  const [editValue, setEditValue] = useState(diff.human_edit_value ?? '');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const decided = diff.human_decision !== null;

  async function handleDecide(decision: HumanDecision, value?: string) {
    setIsSubmitting(true);
    try {
      await onDecide(diff.id, decision, value);
    } finally {
      setIsSubmitting(false);
      setEditMode(false);
    }
  }

  return (
    <div style={styles.card}>
      <div style={styles.header}>
        <span style={styles.measureBadge}>Measure {diff.measure_number}</span>
        <span style={styles.diffTypeBadge(diff.difference_type)}>
          {diff.difference_type}
        </span>
        <span style={styles.instrument}>{diff.instrument}</span>
        <ConfidenceBadge value={diff.audiveris_confidence} label="OMR" />
        <ConfidenceBadge value={diff.claude_vision_confidence} label="Vision" />
        {diff.auto_accepted && <span style={styles.autoBadge}>Auto-accepted</span>}
      </div>

      <div style={styles.body}>
        <p style={styles.description}>{diff.description}</p>

        {/* Side-by-side snippets */}
        <div style={styles.snippets}>
          <div style={styles.snippetBox}>
            <span style={styles.snippetLabel}>PDF original</span>
            {diff.pdf_snippet_path ? (
              <img
                src={`/uploads/${diff.pdf_snippet_path}`}
                alt="PDF snippet"
                style={styles.snippetImg}
              />
            ) : (
              <span style={styles.snippetPlaceholder}>No image available</span>
            )}
          </div>
          <div style={styles.snippetBox}>
            <span style={styles.snippetLabel}>MusicXML render</span>
            {diff.musicxml_snippet_path ? (
              <img
                src={`/uploads/${diff.musicxml_snippet_path}`}
                alt="MusicXML snippet"
                style={styles.snippetImg}
              />
            ) : (
              <span style={styles.snippetPlaceholder}>No image available</span>
            )}
          </div>
        </div>

        {/* Actions or decision display */}
        {decided ? (
          <div style={styles.actions}>
            <span style={styles.decisionBadge(diff.human_decision!)}>
              {diff.human_decision}
            </span>
            {diff.human_edit_value && (
              <code style={{ fontSize: 11, color: '#666' }}>
                {diff.human_edit_value.slice(0, 60)}
                {diff.human_edit_value.length > 60 ? '…' : ''}
              </code>
            )}
          </div>
        ) : (
          <div>
            {editMode ? (
              <div>
                <textarea
                  style={styles.textarea}
                  placeholder="Enter corrected MusicXML fragment…"
                  value={editValue}
                  onChange={(e) => setEditValue(e.target.value)}
                />
                <div style={styles.actions}>
                  <button
                    style={styles.btn('submit')}
                    disabled={isSubmitting || !editValue.trim()}
                    onClick={() => handleDecide('edit', editValue)}
                  >
                    Submit Edit
                  </button>
                  <button
                    style={{ ...styles.btn('reject'), border: '1px solid #ccc', color: '#666' }}
                    onClick={() => setEditMode(false)}
                  >
                    Cancel
                  </button>
                </div>
              </div>
            ) : (
              <div style={styles.actions}>
                <button
                  style={styles.btn('accept')}
                  disabled={isSubmitting}
                  onClick={() => handleDecide('accept')}
                >
                  Accept
                </button>
                <button
                  style={styles.btn('reject')}
                  disabled={isSubmitting}
                  onClick={() => handleDecide('reject')}
                >
                  Reject
                </button>
                <button
                  style={styles.btn('edit')}
                  disabled={isSubmitting}
                  onClick={() => setEditMode(true)}
                >
                  Edit
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
