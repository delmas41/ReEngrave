// TypeScript interfaces matching backend SQLAlchemy models and API responses

export type ExportFormat = 'pdf' | 'musicxml' | 'lilypond';

export type ProcessingStatus =
  | 'pending'
  | 'processing'
  | 'review'
  | 'complete'
  | 'error';

export type HumanDecision = 'accept' | 'reject' | 'edit';

export type DifferenceType =
  | 'note'
  | 'rhythm'
  | 'articulation'
  | 'dynamic'
  | 'beam'
  | 'slur'
  | 'accidental'
  | 'clef'
  | 'other';

export type Era = 'baroque' | 'classical' | 'romantic' | 'modern';

export type ScoreSource = 'imslp' | 'upload';

// ---------------------------------------------------------------------------
// Core domain interfaces
// ---------------------------------------------------------------------------

export interface Score {
  id: string;
  title: string;
  composer: string;
  era: Era;
  source: ScoreSource;
  source_url: string | null;
  original_pdf_path: string;
  musicxml_path: string | null;
  status: ProcessingStatus;
  created_at: string; // ISO datetime string
  updated_at: string;
  metadata_json: Record<string, unknown> | null;
}

export interface FlaggedDifference {
  id: string;
  score_id: string;
  measure_number: number;
  instrument: string;
  time_signature: string;
  key_signature: string;
  difference_type: DifferenceType;
  description: string;
  pdf_snippet_path: string;
  musicxml_snippet_path: string;
  audiveris_confidence: number; // 0-1
  claude_vision_confidence: number; // 0-1
  human_decision: HumanDecision | null;
  human_edit_value: string | null;
  human_reviewed_at: string | null;
  auto_accepted: boolean;
  auto_accept_rule_id: string | null;
  created_at: string;
}

export interface KnowledgePattern {
  id: string;
  pattern_type: 'audiveris_failure' | 'claude_vision_prompt' | 'instrument_quirk';
  instrument: string | null;
  difference_type: DifferenceType;
  era: Era | null;
  pattern_description: string;
  occurrence_count: number;
  accept_count: number;
  reject_count: number;
  edit_count: number;
  confidence_threshold: number;
  example_ids: string[] | null;
  created_at: string;
  updated_at: string;
}

export interface AutoAcceptRule {
  id: string;
  pattern_id: string;
  rule_description: string;
  instrument: string | null;
  difference_type: DifferenceType;
  min_audiveris_confidence: number;
  min_claude_confidence: number;
  min_confirmations: number;
  current_confirmations: number;
  is_active: boolean;
  created_at: string;
}

export interface IMSLPSearchResult {
  title: string;
  composer: string;
  era: Era;
  url: string;
  pdf_urls: string[];
  description: string;
}

// ---------------------------------------------------------------------------
// Analytics / reporting interfaces
// ---------------------------------------------------------------------------

export interface PatternSummary {
  instrument: string | null;
  difference_type: DifferenceType;
  occurrences: number;
  accept_rate: number;
}

export interface AutoRuleDetail {
  id: string;
  instrument: string | null;
  difference_type: DifferenceType;
  confirmations: number;
  description: string;
}

export interface LearningReport {
  total_scores: number;
  total_corrections: number;
  accept_rate: number;
  total_accepts: number;
  total_rejects: number;
  active_auto_rules: number;
  top_patterns: PatternSummary[];
  active_auto_rules_detail: AutoRuleDetail[];
  prompt_performance: Record<string, unknown>;
  suggested_improvements: string[];
}

// ---------------------------------------------------------------------------
// Frontend state interfaces
// ---------------------------------------------------------------------------

/** Local UI state for reviewing a single diff card */
export interface DiffReviewState {
  diffId: string;
  decision: HumanDecision | null;
  editValue: string;
  isSubmitting: boolean;
  isEditMode: boolean;
}

/** Crop region for PDF.js renderer */
export interface CropRegion {
  x: number;
  y: number;
  w: number;
  h: number;
}
