// ─── tools/maestro_bridge/analyze.ts ─────────────────────────────────────────
// ReEngrave ↔ maestroAnalyst bridge. CLI entry.
//
// Usage:
//   npx tsx analyze.ts harmony <musicxml-path>
//   npx tsx analyze.ts harmony <musicxml-path> --pretty
//
// Reads a MusicXML file, runs maestroAnalyst's analyzeScore() over it, and
// prints a structured JSON report to stdout. Exit 0 on success; non-zero
// with a one-line error on stderr otherwise.
//
// M0 scope: harmony subcommand only. rhythm + cross-check come in M1+M2.

import * as fs from 'node:fs';
import * as path from 'node:path';
import { parseXmlString, parseMxlBuffer } from './gradus/lib/maestroAnalyst/xmlParser';
import { analyzeScore } from './gradus/lib/maestroAnalyst';
import type { ScoreAnalysis } from './gradus/lib/maestroAnalyst/types';
import { analyzeRhythm } from './rhythm';

interface HarmonyOutput {
  schema_version: 1;
  capability: 'harmony';
  source_path: string;
  overall_key: {
    key: string;
    confidence: number;
  };
  local_keys: Array<{ measure: number; key: string; confidence: number }>;
  chord_analyses: Array<{
    measure: number;
    beat: number;
    rn: string;                 // top reading, curriculum form
    rn_ascii: string;           // top reading, ASCII form
    rn_confidence: number;
    pitches: string[];
    pcs: number[];
    local_key: string;
    inversion: string;
    basis: string;
  }>;
  cadences: Array<{
    type: string;
    measure: number;
    beat: number;
    soprano_final_degree: number | null;
    penultimate: string;
    final: string;
    basis: string;
  }>;
  phrases: Array<{ index: number; measure_start: number; measure_end: number }>;
  meta: {
    parts: string[];
    measure_count: number;
    chord_count: number;
  };
}

function usage(): never {
  process.stderr.write(
    'usage: analyze.ts harmony     <musicxml-path> [--pretty]\n' +
    '       analyze.ts rhythm      <musicxml-path> [--pretty]\n' +
    '       analyze.ts cross-check <musicxml-path> --work <id> (not yet — M2)\n',
  );
  process.exit(2);
}

function fail(msg: string): never {
  process.stderr.write(`error: ${msg}\n`);
  process.exit(1);
}

async function readMusicXml(filePath: string): Promise<ReturnType<typeof parseXmlString>> {
  if (!fs.existsSync(filePath)) fail(`file not found: ${filePath}`);
  const ext = path.extname(filePath).toLowerCase();
  if (ext === '.mxl') {
    const buf = fs.readFileSync(filePath);
    return parseMxlBuffer(buf);
  }
  // .musicxml, .xml, anything else — treat as plain XML
  const xml = fs.readFileSync(filePath, 'utf8');
  return parseXmlString(xml);
}

function shapeHarmony(analysis: ScoreAnalysis, sourcePath: string): HarmonyOutput {
  return {
    schema_version: 1,
    capability: 'harmony',
    source_path: sourcePath,
    overall_key: {
      key: analysis.overallKey.key,
      confidence: analysis.overallKeyConfidence,
    },
    local_keys: analysis.localKeys.map(lk => ({
      measure: lk.measure,
      key: lk.key,
      confidence: lk.confidence,
    })),
    chord_analyses: analysis.chordAnalyses.map(c => {
      const top = c.readings[0];
      return {
        measure: c.measure,
        beat: c.beat,
        rn: top?.rn ?? c.primary ?? '?',
        rn_ascii: top?.rnAscii ?? c.primary ?? '?',
        rn_confidence: top?.confidence ?? 0,
        pitches: c.pitches,
        pcs: Array.from(c.pcSet ?? []),
        local_key: top?.localKey ?? analysis.overallKey.key,
        inversion: top?.inversion ?? 'root',
        basis: top?.basis ?? c.primaryBasis ?? '',
      };
    }),
    cadences: analysis.cadences.map(c => ({
      type: c.type,
      measure: c.measure,
      beat: c.beat,
      soprano_final_degree: c.sopranoFinalDegree,
      penultimate: c.penultimate,
      final: c.final,
      basis: c.basis,
    })),
    phrases: analysis.phrases.map(p => ({
      index: p.index,
      measure_start: p.measureStart,
      measure_end: p.measureEnd,
    })),
    meta: {
      parts: analysis.score.parts.map(p => p.name),
      measure_count: analysis.score.measureCount,
      chord_count: analysis.chordStream.chords.length,
    },
  };
}

async function main() {
  const argv = process.argv.slice(2);
  if (argv.length < 2) usage();
  const subcommand = argv[0];
  const xmlPath = argv[1];
  const pretty = argv.includes('--pretty');

  if (subcommand !== 'harmony' && subcommand !== 'rhythm') {
    if (subcommand === 'cross-check') {
      fail(`subcommand "cross-check" not implemented yet — see docs/maestro-integration-plan.md (M2)`);
    }
    usage();
  }

  const score = await readMusicXml(xmlPath);
  const analysis = analyzeScore(score);

  let out: unknown;
  if (subcommand === 'harmony') {
    out = shapeHarmony(analysis, xmlPath);
  } else {
    out = analyzeRhythm(analysis, xmlPath);
  }

  process.stdout.write(JSON.stringify(out, null, pretty ? 2 : 0));
  process.stdout.write('\n');
}

main().catch(err => {
  process.stderr.write(`error: ${err instanceof Error ? err.message : String(err)}\n`);
  if (err instanceof Error && err.stack) {
    process.stderr.write(err.stack + '\n');
  }
  process.exit(1);
});
