// ─── tools/maestro_bridge/rhythm.ts ──────────────────────────────────────────
// Rhythm / beat-mapping validation for ReEngrave OMR output.
//
// Lives in ReEngrave (not in maestroAnalyst) per the personal-use deviation
// in docs/maestro-integration-plan.md → "M1 Decision deviation". If this
// stabilizes and Sean wants it permanent in gradus, promoting is a small
// move: copy this file into gradus/lib/maestroAnalyst/rhythmValidation.ts,
// add an export line in maestroAnalyst/index.ts, update the submodule
// pointer.
//
// What it does:
//   For each measure × voice, sum the note durations (in quarter-beats)
//   and compare to the expected beats from the active time signature.
//   When the time signature is missing — common for ReEngrave OMR output
//   because DSv2-trained YOLO often misses time-sig digits — infer one
//   from the modal beat-sum across measures. Emit warnings for measures
//   that don't match.

import type { Note, Score } from './gradus/lib/maestroAnalyst/types';
import type { ScoreAnalysis } from './gradus/lib/maestroAnalyst/types';

export interface BeatMapWarning {
  measure: number;
  voice: number;
  part_id: string;
  part_name: string;
  expected_beats: number;
  summed_beats: number;
  delta: number;                    // summed - expected; negative = short
  diagnosis: string;
  cadence_evidence?: string;        // nearby cadence from analyzeScore (M2 enrichment)
}

export interface PerMeasureSummary {
  measure: number;
  time_signature: string | null;
  expected_beats: number | null;
  voices: Record<number, number>;   // voice → summed quarter-beats
  max_voice_beats: number;
}

export interface RhythmOutput {
  schema_version: 1;
  capability: 'rhythm';
  source_path: string;
  time_signature_source: 'explicit' | 'inferred' | 'unknown';
  effective_time_signature: string | null;
  expected_beats_per_measure: number | null;
  divisions_per_quarter: number;
  warnings: BeatMapWarning[];
  per_measure: PerMeasureSummary[];
  meta: {
    measure_count: number;
    warnings_count: number;
    measures_with_warnings: number;
    /** Set when no consistent time signature could be inferred — usually
     *  means the OMR is severely broken or the source is genuinely
     *  through-composed without bar lines. */
    no_consistent_meter?: true;
  };
}

// Tolerance for "matches the time signature" — a thirty-second note in
// 4/4 = 0.125 quarters. Tighter than this and we'd flag noise; looser
// and we'd miss real fragments.
const BEAT_TOLERANCE = 0.125;

// Standard time signatures we'll consider when inferring from the data.
// Listed as (label, beats-per-measure-in-quarters). Compound meters are
// expressed in their quarter-note equivalent (6/8 = 3 quarter-beats).
const STANDARD_TIME_SIGS: Array<{ label: string; quarters: number }> = [
  { label: '2/4',  quarters: 2 },
  { label: '3/4',  quarters: 3 },
  { label: '4/4',  quarters: 4 },
  { label: '5/4',  quarters: 5 },
  { label: '6/4',  quarters: 6 },
  { label: '7/4',  quarters: 7 },
  { label: '3/8',  quarters: 1.5 },
  { label: '6/8',  quarters: 3 },
  { label: '9/8',  quarters: 4.5 },
  { label: '12/8', quarters: 6 },
  { label: '2/2',  quarters: 4 },
  { label: '3/2',  quarters: 6 },
];

function sumNotesByMeasureVoice(
  score: Score,
): Map<number, Map<number, { sum: number; partId: string; partName: string }>> {
  const out = new Map<number, Map<number, { sum: number; partId: string; partName: string }>>();
  for (const n of score.notes) {
    // Chord members share an onset with the chord's primary note. The
    // primary note's duration already reflects the chord's duration —
    // counting members again would double-count.
    if (n.isChordMember) continue;

    let byVoice = out.get(n.measure);
    if (!byVoice) {
      byVoice = new Map();
      out.set(n.measure, byVoice);
    }
    let entry = byVoice.get(n.voice);
    if (!entry) {
      entry = { sum: 0, partId: n.partId, partName: n.partName };
      byVoice.set(n.voice, entry);
    }
    entry.sum += n.duration;
  }
  return out;
}

function inferTimeSignature(
  perMeasure: PerMeasureSummary[],
): { label: string; quarters: number } | null {
  // Take the modal max-voice-beats across measures, then snap to the
  // nearest standard signature within tolerance.
  if (perMeasure.length === 0) return null;

  const counts = new Map<number, number>();
  for (const m of perMeasure) {
    const rounded = Math.round(m.max_voice_beats * 4) / 4;  // snap to 16th-note grid
    counts.set(rounded, (counts.get(rounded) ?? 0) + 1);
  }

  // Find the modal beat-count value.
  let modeBeats = 0;
  let modeCount = 0;
  for (const [beats, count] of counts) {
    if (count > modeCount) {
      modeBeats = beats;
      modeCount = count;
    }
  }

  // The mode must cover at least half the measures to count as a real
  // signature; otherwise meter is too unstable to infer.
  if (modeCount * 2 < perMeasure.length) return null;

  // Snap to the closest standard time signature within tolerance.
  let best: { label: string; quarters: number } | null = null;
  let bestDiff = Infinity;
  for (const sig of STANDARD_TIME_SIGS) {
    const diff = Math.abs(sig.quarters - modeBeats);
    if (diff < bestDiff && diff <= BEAT_TOLERANCE) {
      best = sig;
      bestDiff = diff;
    }
  }
  return best;
}

function diagnose(summed: number, expected: number, voice: number): string {
  const delta = summed - expected;
  const absDelta = Math.abs(delta);
  // Express in note-value terms when possible.
  let noteValueHint = '';
  if (absDelta >= 1.99 && absDelta <= 2.01) noteValueHint = ' (~half note)';
  else if (absDelta >= 0.99 && absDelta <= 1.01) noteValueHint = ' (~quarter note)';
  else if (absDelta >= 0.49 && absDelta <= 0.51) noteValueHint = ' (~eighth note)';
  else if (absDelta >= 0.24 && absDelta <= 0.26) noteValueHint = ' (~sixteenth note)';
  else if (absDelta >= 0.124 && absDelta <= 0.126) noteValueHint = ' (~thirty-second note)';

  if (delta > 0) {
    return `voice ${voice} sums to ${summed.toFixed(3)} quarter-beats, exceeds expected ${expected} by ${absDelta.toFixed(3)}${noteValueHint} — likely OMR stacked notes from multiple voices into voice ${voice}, or chord-member detection missed an isChordMember flag`;
  } else {
    return `voice ${voice} sums to ${summed.toFixed(3)} quarter-beats, short of expected ${expected} by ${absDelta.toFixed(3)}${noteValueHint} — likely OMR missed a note or rest, or a tied-over note was double-stopped at the bar line`;
  }
}

export function analyzeRhythm(
  analysis: ScoreAnalysis,
  sourcePath: string,
): RhythmOutput {
  const score = analysis.score;
  const byMeasureVoice = sumNotesByMeasureVoice(score);

  // Build per-measure summaries before deciding on time signature.
  const perMeasure: PerMeasureSummary[] = [];
  for (let m = 1; m <= score.measureCount; m++) {
    const byVoice = byMeasureVoice.get(m) ?? new Map();
    const voices: Record<number, number> = {};
    let maxBeats = 0;
    for (const [voice, entry] of byVoice) {
      voices[voice] = entry.sum;
      if (entry.sum > maxBeats) maxBeats = entry.sum;
    }
    perMeasure.push({
      measure: m,
      time_signature: null,
      expected_beats: null,
      voices,
      max_voice_beats: maxBeats,
    });
  }

  // Decide effective time signature: explicit > inferred > unknown.
  let sigSource: 'explicit' | 'inferred' | 'unknown' = 'unknown';
  let effectiveSig: string | null = null;
  let expectedBeats: number | null = null;

  if (score.timeSignatures.length > 0) {
    // M1: use the first time signature globally. Mid-piece changes are
    // handled in M2 when we have richer per-measure context.
    const ts = score.timeSignatures[0];
    effectiveSig = `${ts.beats}/${ts.beatType}`;
    expectedBeats = (ts.beats / ts.beatType) * 4;
    sigSource = 'explicit';
  } else {
    const inferred = inferTimeSignature(perMeasure);
    if (inferred) {
      effectiveSig = inferred.label;
      expectedBeats = inferred.quarters;
      sigSource = 'inferred';
    }
  }

  // Annotate per-measure summaries now that we know the signature.
  if (expectedBeats !== null) {
    for (const m of perMeasure) {
      m.time_signature = effectiveSig;
      m.expected_beats = expectedBeats;
    }
  }

  // Generate warnings.
  const warnings: BeatMapWarning[] = [];
  if (expectedBeats !== null) {
    for (const m of perMeasure) {
      for (const [voiceStr, beats] of Object.entries(m.voices)) {
        const voice = Number(voiceStr);
        if (Math.abs(beats - expectedBeats) <= BEAT_TOLERANCE) continue;

        const byVoice = byMeasureVoice.get(m.measure)!;
        const entry = byVoice.get(voice)!;

        // Cadence cross-reference: any cadence within one measure of this one.
        const adjCadence = analysis.cadences.find(
          c => Math.abs(c.measure - m.measure) <= 1,
        );
        const cadenceEvidence = adjCadence
          ? `${adjCadence.type} at m${adjCadence.measure} b${adjCadence.beat.toFixed(2)}`
          : undefined;

        warnings.push({
          measure: m.measure,
          voice,
          part_id: entry.partId,
          part_name: entry.partName,
          expected_beats: expectedBeats,
          summed_beats: beats,
          delta: beats - expectedBeats,
          diagnosis: diagnose(beats, expectedBeats, voice),
          cadence_evidence: cadenceEvidence,
        });
      }
    }
  }

  const measuresWithWarnings = new Set(warnings.map(w => w.measure)).size;

  return {
    schema_version: 1,
    capability: 'rhythm',
    source_path: sourcePath,
    time_signature_source: sigSource,
    effective_time_signature: effectiveSig,
    expected_beats_per_measure: expectedBeats,
    divisions_per_quarter: score.divisions,
    warnings,
    per_measure: perMeasure,
    meta: {
      measure_count: score.measureCount,
      warnings_count: warnings.length,
      measures_with_warnings: measuresWithWarnings,
      ...(sigSource === 'unknown' ? { no_consistent_meter: true as const } : {}),
    },
  };
}
