// ─── tools/maestro_bridge/scholarly/db.ts ────────────────────────────────────
// Scholarly DB loader. Reads JSON entries from ./works/*.json into memory
// on demand. Each entry is one canonical work + the analytically-consensus
// reading for it (overall key, key plan, notable cadences).
//
// Lookup is by `work_id` only — no fingerprint matching. The caller (the
// `cross-check` subcommand) requires --work <id>; if missing, prints the
// available list. This is the personal-use-pragmatic choice: Sean always
// knows what piece he's scanning, so automatic identification adds
// complexity without value.

import * as fs from 'node:fs';
import * as path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const WORKS_DIR = path.join(__dirname, 'works');

export interface KeyPlanSection {
  section: string;             // analyst-named section ID, e.g. "exposition_group_2"
  measure_start: number;
  measure_end: number;
  key: string;                 // expected key in this section, e.g. "Eb major", or "various" for development
  role: string;                // human-readable description
}

export interface NotableCadence {
  measure: number;
  type: string;                // "PAC" / "IAC" / "HC" / "Plagal" / "Phrygian" / "DC"
  key: string;
  basis: string;
}

export interface ScholarlyEntry {
  schema_version: 1;
  work_id: string;
  composer: string;
  title: string;
  catalog?: string;            // e.g. "BWV 846/1", "Op. 67"
  year_composed?: number;
  source_citations: string[];

  known_overall_key: string;
  expected_measure_count: number;
  expected_time_signature: string;

  key_plan: KeyPlanSection[];
  notable_cadences: NotableCadence[];

  characteristic_features?: string[];
  common_omr_pitfalls?: string[];

  _notes?: string;
}

let _cache: Map<string, ScholarlyEntry> | null = null;

function loadAll(): Map<string, ScholarlyEntry> {
  if (_cache !== null) return _cache;

  const cache = new Map<string, ScholarlyEntry>();
  if (!fs.existsSync(WORKS_DIR)) {
    _cache = cache;
    return cache;
  }

  for (const file of fs.readdirSync(WORKS_DIR)) {
    if (!file.endsWith('.json')) continue;
    const fullPath = path.join(WORKS_DIR, file);
    const raw = fs.readFileSync(fullPath, 'utf8');
    let entry: ScholarlyEntry;
    try {
      entry = JSON.parse(raw) as ScholarlyEntry;
    } catch (e) {
      process.stderr.write(`warning: skipping malformed scholarly entry ${file}: ${e}\n`);
      continue;
    }
    if (!entry.work_id) {
      process.stderr.write(`warning: scholarly entry ${file} missing work_id; skipping\n`);
      continue;
    }
    if (entry.schema_version !== 1) {
      process.stderr.write(
        `warning: scholarly entry ${file} has schema_version ${entry.schema_version}; this loader handles v1 only\n`,
      );
      continue;
    }
    cache.set(entry.work_id, entry);
  }

  _cache = cache;
  return cache;
}

export function getEntry(workId: string): ScholarlyEntry | null {
  return loadAll().get(workId) ?? null;
}

export function listWorks(): Array<{
  work_id: string;
  composer: string;
  title: string;
  catalog?: string;
}> {
  return Array.from(loadAll().values()).map(e => ({
    work_id: e.work_id,
    composer: e.composer,
    title: e.title,
    catalog: e.catalog,
  }));
}
