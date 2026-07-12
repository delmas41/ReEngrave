# Dossier-Guided Verification — design brief & handoff

**Status:** design brief for the *next* session. Not yet implemented.
**Builds on:** branch `claude/omr-time-signature-inference-e547f1` (6 commits
`cc00305`→`eaf8311`: the deterministic time-sig/clef layer). ⚠️ **All line
numbers below are relative to this branch/worktree — `main` lacks these commits
and diverges by ~100 lines. Work on the branch, not bare `main`.**
**Provenance:** produced 2026-07-11 by a 7-agent workflow (5 parallel subsystem
readers → design synthesis → adversarial critique); every code citation was
verified against the worktree.

---

## 0. Thesis

The July-2026 confidence probe (`benchmarks/omr-detection-probe-2026-07/findings.md`)
proved the orchestral wall is a **synthetic→real domain gap**, not a threshold
problem: at conf 0.10 the detector recovered **zero** real time-sig digits on
Boléro/Mahler first pages and only partial, **mostly-treble** clefs (no
bass/alto); lowering conf floods noteheads with 2.4–3.5× false positives. So the
shipped deterministic layer correctly **abstains** — it cannot see its inputs.

A **dossier of known facts** for these canonical works supplies exactly the
clef/key/meter/measure-count ground truth the detector can't produce, converting
OMR from "detect blindly" into **"detect → verify-against-known → flag
disagreements for a human."** Build it by **reusing** the annotate loop
(model-proposes → human-adjudicates → corrections-become-training-data), the
theory-layer harness, and the review-UI flag convention. **No greenfield
rebuilds.**

---

## 1. The dossier schema (v2)

One pure-Python-loaded JSON file per work (prefer a `tools/omr/dossier.py`
loader over extending the TypeScript `ScholarlyEntry` — the gradus submodule is
empty and Node isn't in the Docker backend, so a Python loader runs in-container).
`ScholarlyEntry` (`tools/maestro_bridge/scholarly/db.ts:34–54`) is the conceptual
precedent: by-`work_id`, hand-authored, already carries `known_overall_key`,
`expected_measure_count`, `expected_time_signature`, `key_plan[]`,
`common_omr_pitfalls[]`.

```jsonc
{
  "schema_version": 2,
  "work_id": "ravel-bolero",
  "composer": "Ravel", "title": "Boléro",

  // — HAND-INPUT (Sean) —
  "instrumentation": [                    // ordered, top→bottom of the LARGEST un-condensed system
    { "slot": 0,  "instrument": "Flute 1",       "expected_clef": "treble", "transposition": 0 },
    { "slot": 1,  "instrument": "Clarinet in Bb", "expected_clef": "treble", "transposition": 2 }, // written key = concert + 2 sharps
    { "slot": 12, "instrument": "Cello",          "expected_clef": "bass",   "transposition": 0 },
    { "slot": 13, "instrument": "Contrabass",     "expected_clef": "bass",   "transposition": 0, "sounds_8vb": true }
  ],
  "starting_key":  "C major",
  "key_changes":   [ { "measure": 5, "key": "C major" } ],   // concert pitch; [] if none
  "starting_meter":"3/4",
  "meter_changes": [ ],                                       // {measure, meter}; [] if constant
  "total_measures": 340,

  // — OPTIONAL per-page (Sean can page-by-page declare) —
  "pages": [ { "page": 0, "systems": 1, "measures_per_system": [4] },
             { "page": 1, "systems": 2, "measures_per_system": [3, 3] } ],

  // — AUTO-GATHERABLE (a few Claude prompts / WebSearch on the canonical work) —
  "expected_measure_count": 340,
  "common_omr_pitfalls": ["divisi strings split one staff into two",
                          "long single-meter piece: any meter_change flag is suspect"],
  "source_citations": ["…"]
}
```

**Three traps (each a verified codebase gap):**
1. **Transposition.** Dossier key/clef facts are **concert-pitch**; the score is
   written **transposed**. Apply `transposition` before comparing to a staff's
   detected `key_signature`, or every transposing staff false-flags.
2. **Measure numbering.** `measure_index` in the transcribe output is renumbered
   **within a system** (`_page_column_lengths` uses it as a column key), NOT
   piece-global. Accumulate a running global count across pages+systems before
   matching `key_changes` / `meter_changes`.
3. **Meter equality = bar LENGTH.** Beat-sum inference collapses 6/8→3/4,
   12/8→6/4 (same bar length; `rhythm.py:258–291`). A dossier 6/8 must **not**
   "disagree" with an inferred 3/4 of equal length. Store the true meter; drive
   `expected_beats = num*4/den` from the dossier and corroborate via length.

---

## 2. Verify-against-dossier checks

Each consumes the **structural transcribe JSON directly** — NOT maestroAnalyst's
harmonic reduction (`cross-check.ts` structurally cannot see
clef/meter/segmentation). Write them as **pure Python/JSON** so they also run in
Docker.

| Dossier field | Transcribe signal (file:line) | Check → flag |
|---|---|---|
| `instrumentation[slot].expected_clef` | `staff_dict['clef']` (`transcribe.py:1247–1253`, from `active_clef_by_staff` ‖ `_ClefContinuity.starting_clef` (475) ‖ `_default_clef_for_position` (432)) | disagree → `clef_disagreement`; if detector abstained, **seed** `active_clef` from the dossier (kills the silent treble-default that transposes a whole bass staff up a 13th). |
| `instrumentation[slot]` register | resolved `pitch` on every notehead (`pitch_resolver`) | aggregate staff register; if shifted a clean clef-interval outside the instrument range → high-confidence `clef_disagreement`. **The only self-diagnosis of a wrong clef:** one staff's geometry is clef-invariant; symmetry is broken only by an external register anchor (the dossier). Score `|register − expected|`, either direction. |
| `starting_key` + `key_changes` (÷transposition) | `staff_dict['key_signature']={sharps,flats}` (`_detect_key_sig_from_cell:525`; `key_signature_final` on change, 1353–1357) | seed `active_key_sig` (1254; today `{}` conflates "no accidentals detected" with "piece is in C"); compare counted sharps/flats → `key_disagreement`. |
| `starting_meter` + `meter_changes` | `staff_dict['time_signature']` + page `inferred_time_signature`; `backfill_page_time_signatures` (`rhythm.py:470`) | make dossier meter the **top-priority `source='dossier'`** in backfill, above `_dominant_detected_meter` (429) / `infer_page_time_signature` (385); authoritatively fills nulls. A *detected* C/cut-C glyph (the only reliably-detected meter) that disagrees → `meter_disagreement`. |
| meter (notation math) | `_measure_rhythm_sum_warning` (def `1078`, called `1390`, **skipped when `time_signature is None`** = most orchestral measures) | dossier meter turns this into an **always-on notation-math verifier** — **but reshape it first (see §6 Phase 1); the naive per-staff path over-fires catastrophically.** |
| `pages[].systems`/`.measures_per_system`, `total_measures` | `page_dict['n_systems']`, `sys_dict['n_staves']`, `staff_dict['n_measures']`, `n_measures_total` (1468) | mismatch → new `structure_warning`; a per-page measure shortfall **+** existing `phase1_warning` (fused >2×-median, 1340) pinpoints the cell for re-selection; can steer `resegment_fused_measures` (`measure_extractor.py:680`) toward the known count. |

Existing abstention flags to reuse verbatim (already measure-dict keys):
`time_signature==null`, `time_signature.source∈{inferred,detected_propagated}`
(+`confidence/votes`), `phase1_warning`, `rhythm_sum_warning`, `pitch==null`,
per-detection `confidence`.

---

## 3. Confidence / flagging model

"Surface for hand-selection" = a check produced a disagreement OR the detector
abstained on a field the dossier declares. Follow the **existing flag convention
verbatim** — write extra keys onto the measure/staff dict
(`clef_disagreement`, `key_disagreement`, `meter_disagreement`,
`structure_warning`), exactly as `phase1_warning`/`rhythm_sum_warning` already
ride along. Then reuse a UI:

**Preferred first UI — the annotate server** (`tools/omr/annotate/server.py:create_app` 544).
Its verdict primitives already map onto dossier adjudication: `t/f/u` →
AGREES/WRONG/unsure; `c` (WRONG_CATEGORY + corrected class) → CORRECT-VALUE
(clef/key/meter picker); `a` (added_detections) → MISSING (human supplies a fact
the detector abstained on). The `/api/cell/<id>/page` endpoint (953,
`_find_cell_bbox_on_page` 841) renders the source PDF page with the cell
highlighted — the single most valuable reuse for "is this really 3/4?" /
"is this measure fused?". Neighbour nav by system/staff = "walk the dossier down
the score." Generalize the verdict schema: mirror `_validate_v2` (398) /
`_load_or_init_verdict` (347) / 1.2s autosave with a per-fact record
`{fact_id, kind(clef|key|meter|measure_count|beat_sum), scope, verdict(AGREES|WRONG|MISSING|unsure|null),
model_value, dossier_value, human_value, confidence, source, notes}`;
`_reconcile_with_detections` (371) handles re-runs after a dossier edit /
re-segmentation, preserving decisions by id.

**Alternate UI — `FlaggedDifference` + ReviewUI.** Rows with
`difference_type∈{clef,key_signature,time_signature,instrumentation,measure_count}`;
DiffCard accept/reject/edit + `PATCH /api/diffs/{id}/decision` unchanged; lives
on the free deterministic side. Caveat: needs a `Score↔dossier` association that
doesn't exist yet (no migrations in this project) — prefer the annotate server
for the first slices.

**Alignment guard (critical).** The dossier↔staff join is
`(page, system, slot)→instrument`. A mis-segmented system shifts every mapping.
Treat an `n_staves`/`n_systems` mismatch vs the dossier as a hard "**do not trust
the role mapping on this page**": emit `structure_warning`, skip clef/key seeding
there, route the human to fix segmentation first. (This also re-enables
`_ClefContinuity`'s same-size-system gate once the count is corrected.)

---

## 4. Where a few Claude prompts add value vs deterministic

**Deterministic suffices (no LLM):** all §2 cross-checks — clef range-fit, key
sharp/flat count, meter backfill priority, rhythm-sum, structure counts. Pure
joins/arithmetic over transcribe JSON.

**A bounded Claude prompt earns its keep** (mirror `maestro_bridge.py`'s
subprocess spawn + `theory_layer.py`'s swallow-failures/env-gate wrapper):
1. **Dossier auto-gather** — from title/composer, draft
   `instrumentation`/`starting_meter`/`total_measures`/`common_omr_pitfalls` for
   Sean to confirm (canonical works are well-documented); WebSearch-assisted.
2. **Margin instrument-label OCR** — crop a system's left margin, read printed
   instrument names → confirm/repair the `slot→instrument` alignment when staff
   counts are ambiguous (divisi). Directly attacks the §3 alignment guard.
3. **Ambiguous clef/key tie-break** — where range-fit is a near-tie, show the
   measure crop + candidate pitches, ask which clef is musically coherent. Rare.

Do **not** route structural checks through maestroAnalyst — harmonic-only, weak
on impressionist/modal orchestral music, and the gradus submodule is currently
empty (`git submodule update --init && (cd tools/maestro_bridge && npm install)`
required before any Node check runs at all).

---

## 5. Correction → training-set loop (two sinks)

- **Glyph corrections** (hand-boxed time-sig digit, corrected clef, barline) feed
  the **existing** `verdicts_to_yolo_labels.py` → `data/user-labeled/vN` →
  `build_catalog_yaml.py` (nc=208 cap intact) pipeline **unchanged** — just more
  boxes, directly attacking the domain gap. Accumulating time-sig-digit boxes is
  the only long-term fix for meter detection.
- **Scalar/structural corrections** (measure count, key/meter-change location)
  feed a **parallel versioned corrections store** reusing the same
  immutable-`vN`-dir + `metadata.json` provenance + union-catalog discipline, to
  tune the deterministic layer / a future structural model. Model the audit
  trail on M4's `corrections_applied` array
  (`theory_layer.apply_pitch_corrections:165`, `_walk_to_detection:326` drift
  guard).

---

## 6. Phases — smallest useful vertical slice FIRST

### Phase 0 — dossier schema + loader (½ day)
Pure-Python `tools/omr/dossier.py` loader. Hand-author ONE dossier: **Boléro**
(constant 3/4, 340 measures, well-known instrumentation, and a probe page).

### Phase 1 — FIRST EXPERIMENT: meter backfill + notation-math on Boléro
Chosen because **meter is piece-global → this slice needs NO
instrumentation/slot/transposition/alignment machinery** (that's the hard part;
build it in later phases). Steps:
1. Add `dossier: Dossier | None = None` to `transcribe()` (1124). **When
   `dossier is None` the backfill path MUST be byte-identical to today** — this,
   not a WTC re-run, is the clean-case regression guard. Thread to **`main()`
   only** via a `--dossier` CLI flag (the `transcribe(` caller at 1546). **Do
   NOT thread to `local_omr.py:232` yet** — the web path has no Score↔dossier
   association or UI to supply one; defer.
2. In `backfill_page_time_signatures` (470) make a dossier meter the
   **top-priority `source='dossier'`**, above detected-propagation / beat-sum
   inference. (Constant-meter Boléro dodges the meter-change→global-measure
   mapping — a real unsolved sub-problem deferred with the non-constant pieces,
   **not** an oversight.)
3. **Reshape the notation-math verifier before trusting it — the naive path
   over-fires catastrophically on this exact page.** `_measure_rhythm_sum_warning`
   runs per-staff-per-measure; `split_events_into_voices([])` returns `[[]]`
   (`voicing.py:229`), so an empty/resting staff-measure flags
   `{expected:3, actual:0}`; and `rhythm.py:274–283` documents that *correctly*
   transcribed Boléro bars sum to ~2.0 (instruments rest a beat; rests are
   under-detected too). Forcing 3/4 would flag nearly every staff-measure as a
   false positive. So:
   - **Aggregate to the measure COLUMN across all staves of the system** (mirror
     the per-column MAX that beat-sum *inference* already uses), not
     per-staff-per-measure.
   - Flag **under-sum only when the fullest voice across the whole column still
     falls short**; never flag a resting/empty staff.
   - Treat **over-sum (`actual > expected`) as the high-confidence signal**
     (extra beats ⇒ likely a fused barline; cross-reference `phase1_warning`);
     **under-sum as low-confidence** (usually a missing rest, given the gap).
4. **Success metric = PRECISION of flags, not coverage.** "Went from ~0 measures
   evaluated to ~all" is trivially true and meaningless. Real proof: after the
   column reshape, flagged columns are dominated by *genuine* rhythm/segmentation
   errors (spot-check 5 over-sum flags against the PDF — confirm they're real
   fused/extra-beat measures), while resting/sparse-but-correct columns do NOT
   flag. Baseline = no dossier → rhythm-sum skipped everywhere. Prove Bach WTC
   (clean, no dossier) byte-identical. Run `tools/omr/tests`.

### Phase 2 — clef seed + range-fit verify
Seed `active_clef` from the dossier at 1247; add
`clef_from_pitch_distribution(staff_cells, expected_range)`. Metric: a known bass
staff the detector defaults to treble → resolved pitches land ~a 13th too high →
range-fit flags it; with the seed, pitches land in range.

### Phase 3 — structure verify + alignment guard
`structure_warning` on `n_systems`/`n_staves`/`n_measures` mismatch; the §3
"don't trust role mapping" gate.

### Phase 4 — human-in-the-loop UI
Generalize the annotate verdict schema (§3) OR wire `FlaggedDifference`. Surface
all `*_disagreement`/`*_warning` flags for hand-selection.

### Phase 5 — correction→training sinks (§5) + optional Claude prompts (§4)

**Verification discipline every phase:** baseline first; prove the metric moved
on the flagged case; **prove the clean case is byte-identical** (dossier=None ⇒
identical output; plus a real clean piece like Bach WTC unchanged); run
`tools/omr/tests`. No merge/deploy without Sean's go-ahead.

---

## Appendix — paste-ready handoff prompt

The self-contained prompt to start the next session lives with this brief; it is
the corrected §6-Phase-1-first version (column-aggregated verifier, precision
metric, byte-identical-when-None guard, CLI-only, no alignment machinery in slice
1). If starting fresh, read in order:
`benchmarks/omr-detection-probe-2026-07/findings.md` →
`tools/omr/transcribe.py:1078–1394` → `tools/omr/rhythm.py:385–498`.
