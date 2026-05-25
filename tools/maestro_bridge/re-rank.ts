// ─── tools/maestro_bridge/re-rank.ts ─────────────────────────────────────────
// M4: Pitch re-ranking using harmony analysis.
//
// Takes an OMR JSON (with `pitch_candidates` per notehead, emitted by
// the M4-extended transcribe.py) plus the harmony analysis (from M0)
// and emits proposed pitch corrections. High-confidence corrections
// (>= threshold, default 0.9) are flagged as `auto_apply`; lower-
// confidence ones are `suggestion` only.
//
// Logic per notehead with candidates:
//   1. Look up local key for this measure (from harmony.local_keys).
//   2. If the current pitch is diatonic in the local key → leave alone.
//   3. If the current pitch is part of a chord that maestro reads with
//      high RN confidence anywhere in this measure → leave alone (the
//      chromaticism is real — secondary dominant, mixture, etc).
//   4. Otherwise look at candidates:
//      - exactly one diatonic candidate → high-confidence correction
//      - multiple diatonic candidates → moderate correction (pick the
//        one closest by y-position weight)
//      - no diatonic candidates → no correction
//
// The output is advisory — the orchestrator (Python theory_layer) is
// responsible for actually applying the corrections to omr.json and
// re-exporting the MusicXML.

import * as fs from 'node:fs';
import { getScalePcs } from './gradus/lib/maestroAnalyst/scale';

interface PitchCandidate {
  pitch: string;
  weight: number;
}

interface Detection {
  class: string;
  category: string;
  confidence: number;
  pitch?: string | null;
  pitch_candidates?: PitchCandidate[];
  [k: string]: unknown;
}

interface OmrMeasure {
  measure_index: number;
  detections: Detection[];
  [k: string]: unknown;
}

interface OmrStaff {
  staff_index: number;
  measures: OmrMeasure[];
  [k: string]: unknown;
}

interface OmrSystem {
  system_index: number;
  staves: OmrStaff[];
  [k: string]: unknown;
}

interface OmrPage {
  page_index: number;
  systems: OmrSystem[];
  [k: string]: unknown;
}

interface OmrJson {
  pages: OmrPage[];
  [k: string]: unknown;
}

interface HarmonyAnalysis {
  local_keys: Array<{ measure: number; key: string; confidence: number }>;
  chord_analyses: Array<{
    measure: number;
    beat: number;
    rn: string;
    rn_confidence: number;
    pcs: number[];
    local_key: string;
    [k: string]: unknown;
  }>;
  [k: string]: unknown;
}

export interface PitchCorrection {
  page_index: number;
  system_index: number;
  staff_index: number;
  measure_index: number;
  detection_index: number;
  original_pitch: string;
  corrected_pitch: string;
  candidates: PitchCandidate[];
  local_key: string;
  confidence: number;
  apply: 'auto' | 'suggestion';
  reason: string;
}

export interface ReRankOutput {
  schema_version: 1;
  capability: 're-rank';
  source_omr_json: string;
  source_harmony_json: string;
  threshold: number;
  total_noteheads_pitched: number;
  noteheads_with_candidates: number;
  noteheads_non_diatonic: number;
  corrections: PitchCorrection[];
  meta: {
    auto_apply_count: number;
    suggestion_count: number;
  };
}

const LETTER_PC: Record<string, number> = {
  C: 0, D: 2, E: 4, F: 5, G: 7, A: 9, B: 11,
};

function pitchToPc(pitch: string): number | null {
  const m = pitch.match(/^([A-G])([b#]*)([0-9-]+)$/);
  if (!m) return null;
  const base = LETTER_PC[m[1]];
  let acc = 0;
  for (const c of m[2]) {
    if (c === '#') acc += 1;
    else if (c === 'b') acc -= 1;
  }
  return ((base + acc) % 12 + 12) % 12;
}

function findLocalKey(harmony: HarmonyAnalysis, measure: number): string {
  const lk = harmony.local_keys.find(l => l.measure === measure);
  return lk?.key ?? 'C major';
}

function hasHighConfidenceChordInMeasure(
  harmony: HarmonyAnalysis,
  measure: number,
  pitchPc: number,
  minConfidence: number,
): boolean {
  // If any chord at this measure with high RN confidence contains the
  // suspect pc, the chromaticism is probably real (e.g. V7/V's third).
  return harmony.chord_analyses.some(
    c => c.measure === measure
      && c.rn_confidence >= minConfidence
      && c.pcs.includes(pitchPc),
  );
}

export interface ReRankOpts {
  threshold: number;
  omrPath: string;
  harmonyPath: string;
}

export function reRankPitches(
  omr: OmrJson,
  harmony: HarmonyAnalysis,
  opts: ReRankOpts,
): ReRankOutput {
  const { threshold, omrPath, harmonyPath } = opts;
  let totalPitched = 0;
  let withCandidates = 0;
  let nonDiatonic = 0;
  const corrections: PitchCorrection[] = [];

  for (let pageIdx = 0; pageIdx < (omr.pages?.length ?? 0); pageIdx++) {
    const page = omr.pages[pageIdx];
    for (let sysIdx = 0; sysIdx < (page.systems?.length ?? 0); sysIdx++) {
      const sys = page.systems[sysIdx];
      for (let staffIdx = 0; staffIdx < (sys.staves?.length ?? 0); staffIdx++) {
        const staff = sys.staves[staffIdx];
        for (const measure of staff.measures ?? []) {
          const measureIdx = measure.measure_index;
          const localKey = findLocalKey(harmony, measureIdx);
          const scalePcs = getScalePcs(localKey);

          for (let detIdx = 0; detIdx < (measure.detections?.length ?? 0); detIdx++) {
            const det = measure.detections[detIdx];
            if (det.category !== 'notehead' || !det.pitch) continue;
            totalPitched++;
            if (!det.pitch_candidates || det.pitch_candidates.length === 0) continue;
            withCandidates++;

            const currentPc = pitchToPc(det.pitch);
            if (currentPc === null) continue;

            // Skip diatonic notes — they're plausible as-is.
            if (scalePcs.has(currentPc)) continue;
            nonDiatonic++;

            // Skip notes that are part of a high-confidence chord reading
            // — chromaticism is real (secondary dominant, mixture, etc).
            if (hasHighConfidenceChordInMeasure(harmony, measureIdx, currentPc, 0.7)) {
              continue;
            }

            // Score candidates: keep diatonic ones only.
            const diatonic = (det.pitch_candidates ?? [])
              .map(c => {
                const pc = pitchToPc(c.pitch);
                return pc === null ? null : { ...c, pc, diatonic: scalePcs.has(pc) };
              })
              .filter((c): c is { pitch: string; weight: number; pc: number; diatonic: boolean } =>
                c !== null && c.diatonic && c.pitch !== det.pitch,
              );

            if (diatonic.length === 0) continue;

            // Candidates already arrive sorted descending by weight from
            // transcribe.py — first diatonic = closest by y-position.
            const best = diatonic[0];

            let confidence: number;
            let reason: string;
            if (diatonic.length === 1) {
              // Single diatonic alternate: confidence scales with how close
              // by y-position. weight=1.0 (right on a staff line) → 1.0
              // confidence; weight=0.5 (halfway between positions) → 0.85.
              confidence = Math.min(1.0, 0.85 + 0.15 * best.weight);
              reason = `Original ${det.pitch} (pc ${currentPc}) is non-diatonic in ${localKey} and not explained by any chord reading in m${measureIdx}; the only diatonic alternate from the y-position candidates is ${best.pitch} (pc ${best.pc}, weight ${best.weight.toFixed(2)}).`;
            } else {
              // Multiple diatonic candidates: ambiguous, lower confidence.
              confidence = 0.55 + 0.3 * best.weight;
              reason = `Original ${det.pitch} (pc ${currentPc}) is non-diatonic in ${localKey}; ${diatonic.length} diatonic alternates available — picked closest by y-position: ${best.pitch}.`;
            }

            corrections.push({
              page_index: pageIdx,
              system_index: sysIdx,
              staff_index: staffIdx,
              measure_index: measureIdx,
              detection_index: detIdx,
              original_pitch: det.pitch,
              corrected_pitch: best.pitch,
              candidates: det.pitch_candidates ?? [],
              local_key: localKey,
              confidence: Number(confidence.toFixed(3)),
              apply: confidence >= threshold ? 'auto' : 'suggestion',
              reason,
            });
          }
        }
      }
    }
  }

  const autoApply = corrections.filter(c => c.apply === 'auto').length;
  const suggestion = corrections.length - autoApply;

  return {
    schema_version: 1,
    capability: 're-rank',
    source_omr_json: omrPath,
    source_harmony_json: harmonyPath,
    threshold,
    total_noteheads_pitched: totalPitched,
    noteheads_with_candidates: withCandidates,
    noteheads_non_diatonic: nonDiatonic,
    corrections,
    meta: { auto_apply_count: autoApply, suggestion_count: suggestion },
  };
}

// CLI entry for direct invocation: `tsx re-rank.ts <omr.json> <harmony.json>`
export function reRankFromFiles(
  omrPath: string,
  harmonyPath: string,
  threshold: number = 0.9,
): ReRankOutput {
  const omr = JSON.parse(fs.readFileSync(omrPath, 'utf8')) as OmrJson;
  const harmony = JSON.parse(fs.readFileSync(harmonyPath, 'utf8')) as HarmonyAnalysis;
  return reRankPitches(omr, harmony, { threshold, omrPath, harmonyPath });
}
