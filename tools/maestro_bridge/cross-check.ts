// ─── tools/maestro_bridge/cross-check.ts ─────────────────────────────────────
// Cross-check engine: compares maestroAnalyst's analysis of an OMR-produced
// MusicXML against a known scholarly reading.
//
// Lives in ReEngrave (per the M1 deviation note in docs/maestro-integration-
// plan.md): the comparison logic is OMR-specific (it tolerates measure-
// boundary fuzziness from OMR drift) so keeping it next to the bridge makes
// more sense than promoting it into maestroAnalyst proper.

import type { ScoreAnalysis } from './gradus/lib/maestroAnalyst/types';
import { getEntry, listWorks } from './scholarly/db';
import type { ScholarlyEntry, KeyPlanSection, NotableCadence } from './scholarly/db';

export interface OverallKeyCheck {
  expected: string;
  got: string;
  match: boolean;
  confidence: number;
}

export interface KeyPlanSectionResult {
  section: string;
  measure_range: [number, number];
  expected_key: string;
  observed_keys: Record<string, number>;       // key → fraction of measures in that range
  dominant_observed_key: string;
  match_fraction: number;                       // fraction of measures matching expected
  match: 'high' | 'partial' | 'low' | 'none';
}

export interface CadenceResult {
  expected: NotableCadence;
  matched_to?: { measure: number; type: string; basis: string };
  measure_delta?: number;                       // signed: observed - expected
  match: 'exact' | 'tolerant' | 'wrong_type' | 'missing';
}

export interface Discrepancy {
  dimension: 'overall_key' | 'key_plan_section' | 'cadence';
  what: string;
  expected: string;
  got: string;
  diagnosis: string;
}

export interface CrossCheckOutput {
  schema_version: 1;
  capability: 'cross-check';
  source_path: string;
  work_id: string;
  matched: true;                                 // false case returns ListWorksOutput
  work: {
    composer: string;
    title: string;
    catalog?: string;
    source_citations: string[];
  };
  overall_key_check: OverallKeyCheck;
  key_plan_check: {
    sections_total: number;
    sections_high_match: number;
    sections_partial_match: number;
    sections_low_or_none: number;
    sections: KeyPlanSectionResult[];
  };
  cadence_check: {
    expected_total: number;
    matched_exact: number;
    matched_tolerant: number;
    wrong_type: number;
    missing: number;
    results: CadenceResult[];
  };
  characteristic_features?: string[];
  common_omr_pitfalls?: string[];
  summary: {
    overall_match_quality: 'high' | 'partial' | 'low';
    discrepancy_count: number;
    discrepancies: Discrepancy[];
    diagnosis: string;
  };
}

export interface ListWorksOutput {
  schema_version: 1;
  capability: 'cross-check';
  matched: false;
  reason: 'unknown_work_id' | 'no_work_id_given';
  requested_work_id?: string;
  available_works: Array<{
    work_id: string;
    composer: string;
    title: string;
    catalog?: string;
  }>;
}

// How many measures around a section boundary we'll tolerate before
// counting it as a discrepancy. OMR can drop or duplicate measure numbers
// (especially at repeats), so this matters.
const SECTION_BOUNDARY_TOLERANCE = 2;
const CADENCE_MEASURE_TOLERANCE = 2;

// Key-plan match thresholds — what fraction of measures in a section must
// agree with the expected key for the section to count as "matched".
const HIGH_MATCH_THRESHOLD = 0.7;
const PARTIAL_MATCH_THRESHOLD = 0.4;

function normalizeKeyString(k: string): string {
  return k.trim().toLowerCase().replace(/\s+/g, ' ');
}

function keysMatch(expected: string, got: string): boolean {
  if (expected === 'various') return true;       // development sections etc.
  return normalizeKeyString(expected) === normalizeKeyString(got);
}

function checkOverallKey(
  analysis: ScoreAnalysis,
  expected: string,
): OverallKeyCheck {
  return {
    expected,
    got: analysis.overallKey.key,
    match: keysMatch(expected, analysis.overallKey.key),
    confidence: analysis.overallKeyConfidence,
  };
}

function checkKeyPlanSection(
  analysis: ScoreAnalysis,
  section: KeyPlanSection,
): KeyPlanSectionResult {
  // For each measure in the section's range, find maestroAnalyst's local-
  // key reading. Some measures may have no localKey assignment (e.g. if
  // they're empty or the section extends past the score) — those count as
  // "no observation" and don't affect the match fraction one way or other.
  const startM = Math.max(1, section.measure_start - SECTION_BOUNDARY_TOLERANCE);
  const endM = section.measure_end + SECTION_BOUNDARY_TOLERANCE;

  const observed: Record<string, number> = {};
  let totalObserved = 0;
  for (const lk of analysis.localKeys) {
    if (lk.measure < startM || lk.measure > endM) continue;
    observed[lk.key] = (observed[lk.key] ?? 0) + 1;
    totalObserved++;
  }

  // Normalize counts to fractions.
  const observedFrac: Record<string, number> = {};
  for (const [k, c] of Object.entries(observed)) {
    observedFrac[k] = totalObserved > 0 ? c / totalObserved : 0;
  }

  // Dominant observed key (mode).
  let dominantKey = '';
  let dominantFrac = 0;
  for (const [k, frac] of Object.entries(observedFrac)) {
    if (frac > dominantFrac) {
      dominantKey = k;
      dominantFrac = frac;
    }
  }

  // For "various" key sections (development), success is "no single key
  // dominates the section" — the analyzer should see multiple keys.
  let matchFraction: number;
  let matchTier: KeyPlanSectionResult['match'];

  if (section.key === 'various') {
    // Pass if no single key occupies >70% of the section.
    matchFraction = 1 - dominantFrac;
    matchTier = matchFraction >= HIGH_MATCH_THRESHOLD ? 'high'
              : matchFraction >= PARTIAL_MATCH_THRESHOLD ? 'partial'
              : matchFraction > 0 ? 'low'
              : 'none';
  } else {
    matchFraction = observedFrac[section.key] ?? 0;
    matchTier = matchFraction >= HIGH_MATCH_THRESHOLD ? 'high'
              : matchFraction >= PARTIAL_MATCH_THRESHOLD ? 'partial'
              : matchFraction > 0 ? 'low'
              : 'none';
  }

  return {
    section: section.section,
    measure_range: [section.measure_start, section.measure_end],
    expected_key: section.key,
    observed_keys: observedFrac,
    dominant_observed_key: dominantKey || '(none)',
    match_fraction: matchFraction,
    match: matchTier,
  };
}

function checkCadence(
  analysis: ScoreAnalysis,
  expected: NotableCadence,
): CadenceResult {
  // Find the closest cadence within tolerance.
  let bestMatch: typeof analysis.cadences[number] | null = null;
  let bestDelta = Infinity;
  for (const c of analysis.cadences) {
    const delta = Math.abs(c.measure - expected.measure);
    if (delta <= CADENCE_MEASURE_TOLERANCE && delta < bestDelta) {
      bestMatch = c;
      bestDelta = delta;
    }
  }

  if (!bestMatch) {
    return { expected, match: 'missing' };
  }

  const matchedTo = {
    measure: bestMatch.measure,
    type: bestMatch.type,
    basis: bestMatch.basis,
  };
  const measureDelta = bestMatch.measure - expected.measure;

  if (bestMatch.type !== expected.type) {
    return {
      expected,
      matched_to: matchedTo,
      measure_delta: measureDelta,
      match: 'wrong_type',
    };
  }

  return {
    expected,
    matched_to: matchedTo,
    measure_delta: measureDelta,
    match: measureDelta === 0 ? 'exact' : 'tolerant',
  };
}

function summarize(
  overall: OverallKeyCheck,
  sections: KeyPlanSectionResult[],
  cadences: CadenceResult[],
): CrossCheckOutput['summary'] {
  const discrepancies: Discrepancy[] = [];

  if (!overall.match) {
    discrepancies.push({
      dimension: 'overall_key',
      what: 'overall_key',
      expected: overall.expected,
      got: overall.got,
      diagnosis: `Overall key analysis disagrees with scholarly reading. Confidence on observed key: ${overall.confidence.toFixed(2)}. Possible causes: OMR misread accidentals, key signature drift, or the input MusicXML covers only a subset of the work.`,
    });
  }

  for (const s of sections) {
    if (s.match === 'low' || s.match === 'none') {
      const observedSummary = Object.entries(s.observed_keys)
        .sort(([, a], [, b]) => b - a)
        .slice(0, 3)
        .map(([k, f]) => `${k} (${Math.round(f * 100)}%)`)
        .join(', ');
      discrepancies.push({
        dimension: 'key_plan_section',
        what: s.section,
        expected: s.expected_key,
        got: s.dominant_observed_key,
        diagnosis: `Section ${s.section} (mm. ${s.measure_range[0]}-${s.measure_range[1]}) expected key "${s.expected_key}", but only ${Math.round(s.match_fraction * 100)}% of measures in that range match. Observed: ${observedSummary || '(no key data)'}. Likely cause: OMR misreading key signature or accidentals in this passage.`,
      });
    }
  }

  for (const c of cadences) {
    if (c.match === 'missing') {
      discrepancies.push({
        dimension: 'cadence',
        what: `${c.expected.type} at m${c.expected.measure}`,
        expected: `${c.expected.type} in ${c.expected.key} at m${c.expected.measure}`,
        got: 'not detected',
        diagnosis: `Expected ${c.expected.type} at m${c.expected.measure} (${c.expected.basis}) was not found by the analyzer within ±${CADENCE_MEASURE_TOLERANCE} measures. Likely cause: OMR may have lost the cadential dominant or fragmented the phrase boundary.`,
      });
    } else if (c.match === 'wrong_type') {
      discrepancies.push({
        dimension: 'cadence',
        what: `${c.expected.type} at m${c.expected.measure}`,
        expected: `${c.expected.type}`,
        got: c.matched_to?.type ?? 'unknown',
        diagnosis: `Cadence at m${c.expected.measure} expected to be ${c.expected.type} but analyzer classified it as ${c.matched_to?.type}. ${c.matched_to?.basis ?? ''}`.trim(),
      });
    }
  }

  // Overall quality classification — weighted.
  // High = no discrepancies. Partial = some sections didn't match but
  // overall key + most sections did. Low = overall key wrong, or many
  // sections wrong.
  let quality: 'high' | 'partial' | 'low';
  const highSections = sections.filter(s => s.match === 'high').length;
  const totalSections = sections.length;
  const sectionHighRate = totalSections > 0 ? highSections / totalSections : 1;

  if (discrepancies.length === 0) {
    quality = 'high';
  } else if (overall.match && sectionHighRate >= 0.6) {
    quality = 'partial';
  } else {
    quality = 'low';
  }

  const diagnosis = discrepancies.length === 0
    ? `Analysis matches scholarly reading on all dimensions. ${sections.length} sections checked, ${cadences.length} cadences checked.`
    : `${discrepancies.length} discrepancies found across ${totalSections} key-plan sections and ${cadences.length} expected cadences. ${quality === 'low' ? 'Overall structural reading diverges significantly from the scholarly consensus — review OMR carefully.' : 'Most of the analysis matches; discrepancies are localized.'}`;

  return {
    overall_match_quality: quality,
    discrepancy_count: discrepancies.length,
    discrepancies,
    diagnosis,
  };
}

export function crossCheck(
  analysis: ScoreAnalysis,
  workId: string,
  sourcePath: string,
): CrossCheckOutput | ListWorksOutput {
  const entry = getEntry(workId);
  if (!entry) {
    return {
      schema_version: 1,
      capability: 'cross-check',
      matched: false,
      reason: 'unknown_work_id',
      requested_work_id: workId,
      available_works: listWorks(),
    };
  }

  const overall = checkOverallKey(analysis, entry.known_overall_key);
  const sections = entry.key_plan.map(s => checkKeyPlanSection(analysis, s));
  const cadences = entry.notable_cadences.map(c => checkCadence(analysis, c));

  const sectionTallies = {
    sections_total: sections.length,
    sections_high_match: sections.filter(s => s.match === 'high').length,
    sections_partial_match: sections.filter(s => s.match === 'partial').length,
    sections_low_or_none: sections.filter(s => s.match === 'low' || s.match === 'none').length,
  };

  const cadenceTallies = {
    expected_total: cadences.length,
    matched_exact: cadences.filter(c => c.match === 'exact').length,
    matched_tolerant: cadences.filter(c => c.match === 'tolerant').length,
    wrong_type: cadences.filter(c => c.match === 'wrong_type').length,
    missing: cadences.filter(c => c.match === 'missing').length,
  };

  return {
    schema_version: 1,
    capability: 'cross-check',
    source_path: sourcePath,
    work_id: entry.work_id,
    matched: true,
    work: {
      composer: entry.composer,
      title: entry.title,
      catalog: entry.catalog,
      source_citations: entry.source_citations,
    },
    overall_key_check: overall,
    key_plan_check: { ...sectionTallies, sections },
    cadence_check: { ...cadenceTallies, results: cadences },
    characteristic_features: entry.characteristic_features,
    common_omr_pitfalls: entry.common_omr_pitfalls,
    summary: summarize(overall, sections, cadences),
  };
}

export function listAvailableWorks(): ListWorksOutput {
  return {
    schema_version: 1,
    capability: 'cross-check',
    matched: false,
    reason: 'no_work_id_given',
    available_works: listWorks(),
  };
}
