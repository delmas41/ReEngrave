# ROADMAP — from here to a finished score

The phases and gates are defined in
[docs/plan-2026-09-22-from-here-to-a-finished-score.md](docs/plan-2026-09-22-from-here-to-a-finished-score.md).
This file is the STATUS of each item and nothing else. A session that takes
an item puts its branch beside it; a session that finishes one changes its
status and names the commit. Nobody writes a handoff — the line here and the
benchmark `FINDINGS.md` are the record.

Status words: `todo` · `in flight (branch)` · `done (sha)` · `blocked (why)`
· `dropped (why, DECISIONS line)`.

**Definition of done for the product** (plan §4): one command, a whole
movement, MusicXML + LilyPond PDF, unread bars marked never invented, every
staff named or held out, and a cleanup count Sean would rather pay than
re-enter.

---

## Phase 0 — Stop and consolidate

| item | what | status |
|---|---|---|
| 0.1 | Staged is the product path; legacy frozen | done (DECISIONS 2026-09-22) |
| 0.2 | Flag triage table, ≤ 15 product flags | done — table with a verdict on all 60 (`docs/flags-2026-09.md`) |
| 0.2b | Enforce the triage: remove the `promote — now` flags, delete `OMR_ADJUDICATE`, add `OMR_RESEARCH`, a derived test that staged reads no frozen flag and every `OMR_*` read has a row | todo |
| 0.3a | Archive CLAUDE.md → `docs/chronicle-2026-09.md` | done (2b441cb3) |
| 0.3b | New CLAUDE.md spec ≤ 6,000 words | done (2b441cb3; 4,700 words) |
| 0.3c | `docs/DECISIONS.md`, `ROADMAP.md` | done |
| 0.4a | Shared staged test fixture module; delete the four `_log` copies | todo |
| 0.4b | One `python3 -m tools.omr.staged.check` with `open-findings.json` | done — **baseline 250 open findings on 2026-09-22** (wiring 66, reach 26, gather_coverage 19, capture 18, inventory 11, brakes 8, trace 3, source-text tests 47 files, live mutation batteries 52) |
| 0.4c | Fast / slow test tiers derived from measured durations | done — full suite 4,806 passed / 20 skipped in 700 s; fast tier 2,695 tests in 75 s wall (`pytest -m "not slow"`); threshold derived from `tools/omr/tests/durations.json` |
| 0.4d | Archive the 52 mutation batteries under `benchmarks/_archive/`; no new ones | todo — `check` counts live ones meanwhile |
| 0.4e | No new source-text tests; `check` counts them | done — 47 files counted, allowlist of 2 |
| 0.5 | Lane discipline: brief from the tree, phase item, gate, print check | done (plan §6, rules 1–10) |

Gate: spec < 6,000 words; `check` writes `open-findings.json`; flag table
has a verdict on every flag; fast tier under two minutes.

## Phase 1 — The acceptance harness

| item | what | status |
|---|---|---|
| 1.1 | Whole-movement staged records for the three acceptance documents, ink SUMMARY persisted not rows (< 20 MB/page) | todo |
| 1.2 | Run-time budget; `OMR_DIRECTION_TEXT_SCAN_GATE` on for acceptance; movement in < 1 h unattended | todo |
| 1.3 | `python3 -m tools.omr.acceptance` → `benchmarks/acceptance/current.json`, side-by-sides, nightly | **done** (`claude/acceptance-1.3`) — `tools/omr/acceptance.py`, `benchmarks/acceptance/manifest.json`, `tools/omr/tests/test_acceptance.py` (28 tests). Runs today's inputs: the two four-page shared scan records + the committed engraved 24-bar fixture (whole-movement records are 1.1, still todo — the manifest and each doc's `caveats` say so explicitly, never silently). Whole run: **9.3s wall**, well under the 15-min per-step cap. Measured: notes-reaching-file Litolff 965/2347 (0.411), Breitkopf 2262/3337 (0.678), engraved 358/371 (0.965); bars-add-up-to-meter-in-force (per-bar, from each measure's own `<time>`, never a constant) Litolff 1116/1332, Breitkopf 258/794, engraved 412/450; parts named 12/12, 14/14, 18/18; held_out (`staff_not_identified`) 783, 238, 0 — **both scan figures are STALE**, from records gathered 09-17/09-22 before the 2.1b INFER merge (`ec7e42f4`, same-day but later) landed, flagged per-document; engraved reading pooled F1 **0.947** (frame-shift control collapses to 0.058 — position, not luck), OMR-NED **0.1519**, LilyPond compiles, PDF produced, 3 barcheck failures. Side-by-sides (print crop + best-effort Verovio render of the count page's own bars) built for all three. Found and fixed one live bug in the process: `benchmarks/omr-staged-engraved-2026-09/staged_reading.py`'s synthetic page never set `page_index`, which `score_reading._page_of`'s same-day rewrite (`dcdff9f2`, 13 min later) now requires — one-line fix, noted at its site. |
| 1.4 | First cleanup count on the three fixed pages (DECISIONS 2026-09-22) — Sean | todo |

Gate: `current.json` for all three; a baseline count committed.

## Phase 2 — Close the foundation, in funnel order

| item | what | status |
|---|---|---|
| 2.1 | Identity is PLACEMENT, never naming; gate `staff_not_identified` 783 → < 100, zero grafts against print | 783 → 141 by `OMR_SLOT_FAMILY_BLOCK` (09-21); constraint channels (`claude/instrument-identification-channels-8dcaa2`: 2acb3fcf, a0a5aeac, 73d7ffbe, f934ae7c) move 13 placements INFER → ADJUDICATE, count unchanged. Residual = five condensed `Violoncello e Basso` staves. **Decided 2026-09-22** (DECISIONS; `benchmarks/omr-cello-bass-convention-2026-09/`) → 2.1b. Identity branch merged to main at 4cc82433 (adds 55d50393, a test narrowed to its meaning, mutation-tested). **Gate met by 2.1b: `staff_not_identified` 141 → 0, zero grafts** — done |
| 2.1b | Place a [Cello, Contrabass]-narrowed staff on BOTH slots: line to Cello, doubled with `<transpose>` −8ve and `condensed_from` to Contrabass; division text as `<words>`; gate 141 → 0 on Litolff with the 5 staves named, Breitkopf unchanged (it never condenses) | **done** (`claude/condensed-cello-bass-2.1b` @ ec7e42f4, merged with main 4cc82433, fast-forwarded to main). `inferences.collapse_slot_index_to_family_block` collapses the last block member onto the Cello slot ONLY where its own two candidates resolve to [Cello, Contrabass] (via the reference's own `Q.INSTRUMENT`), detail `condensed_with_slot`; `staged/export.py`'s slot join doubles via `_condensed_double` (directions/arcs/glyph/marks stripped so post-join wedge/arc passes can't find it twice) and `_insert_transpose` (needs `<diatonic>0</diatonic><chromatic>0</chromatic><octave-change>-1</octave-change>` — music21's own reader needs `<diatonic>`, not just the schema-required `<chromatic>`); new `notes_doubled_to_condensed_slot` balance bucket, equality held. Measured on the merged tree (`origin/main` 4cc82433 + this branch) over the two shared records: Litolff — exactly the 5 named staves collapse, `staff_not_identified` 141→0, parts stay 12, `notes_doubled_to_condensed_slot`==141, balance holds, all 5 confirmed against the print crops as the bottom string staff of their system (p4/s0's separate Vcl./Basso correctly untouched), full file round-trips through music21 (Contrabass 107 notes); Breitkopf — 0 family_block inferences at all, so 0 impact, confirmed byte-identical by construction. Division text: `direction_lexicon` carries none of "senza Bassi"/"col Basso"/"Vc. soli" — recorded as a finding, not widened (out of scope). `pytest tools/omr/tests -m "not slow"`: 2714 passed. `staged.check`: 252 open findings, identical to `origin/main` alone (this branch adds zero). |
| 2.1c | `instruments.lookup` resolves every dual label (`Violoncello e Basso`, `Violoncell u. Contrabass`, …) to Cello alone, discarding the second instrument on 26 held editions; a bare `Basso.` is a singer without the roster | **done** (`claude/dual-label-lexicon-2.1c`). `Match` gains an additive `condensed_with: str \| None` — the second instrument where a label joins two instrument nouns with a conjunction (`e/ed/u/und/and/et/&`) and BOTH halves resolve through the EXISTING lexicon (`instruments._condensed_partner`; an ambiguous other half — `basso` is Bass voice or Contrabass — resolves toward whichever declared alternative shares the PRIMARY's family, so `Violoncello e Basso` names Contrabass, not a singer). `lookup`'s own answer is UNCHANGED: replayed against all 1,422 real margin labels (`benchmarks/omr-lexicon-2026-09/resolve_labels.py`), 0 of 1,422 primary resolutions moved. Reach: 2 of 1,422 reader-emitted labels gain a partner (`Posaune u. Tuba` ×2 — a real condensed brass pair, not cello/bass); over the catalog's edition rosters, 36 hold a candidate dual Vc/Basso label and 29 now name the pair, the 7 holdouts being OCR-truncated (conjunction at the string's edge, one side empty) or bare juxtaposition with no conjunction at all (`Vc. Cb.` — deliberately not treated as evidence: no new alias, no guess). Bare `Basso.`/`Bassi` untouched (23 of 1,422 unmoved); the roster/score-order channel already rescues 3 `Basso.` occurrences to Contrabass where the work is catalogued — measured (`benchmarks/omr-producer-consumer-2026-09/roster-reach.txt`), not touched. Wired into STAGED `adjudicate_instrument`'s verdict `detail` only (`staged/adjudicators/identity.py`), never its value; NOT wired into `collapse_slot_index_to_family_block` / `_condensed_double` — measured reach is ZERO `Q.MARGIN_LABEL` dual labels on both shared records (Litolff prints no continuation-system string labels; Breitkopf never condenses), so the label-derived case is left as the next consumer, unbuilt. `staged.check` TOTAL unchanged at 252/252 (the new detail key is out of `wiring`'s DETAIL scope, which only walks GATHER-stage rows). `pytest tools/omr/tests -m "not slow"`: 2714 passed, 3 skipped, 0 failed. LEGACY path untouched in behaviour — same `Match` object, additive field only. |
| 2.2 | Key-signature precedence, engraved-only one-sided; gate 20/20 engraved, Litolff ≥ 44/75 | **landed** `claude/identity-conditions-key-signature-b510b3` (`beba5c64` is the default flip; `291677b5` the rule). Engraved gate **exceeded**: 47 of 50 right, 3 wrong, and the template is 67/67 wherever it speaks. ⚠️ **The Litolff half of the gate is NOT measured** — the rule is one-sided and proved a no-op on a real scan gather, so it cannot have moved 44/75, but *cannot have moved it* is not *measured at ≥ 44/75*. ⚠️ n = 1 engraved document, 1 renderer, no print consulted; a second engraved document is the ranked next step and the 10 held candidates are named in `benchmarks/omr-document-identity-2026-09/out/library-domains.json` |
| 2.3 | INFER duration rules against the print (17 + 41 crops) → default decision | todo |
| 2.4a | Notehead precision on staged: port the two legacy filters; width floor as an ADJUDICATE refusal | todo |
| 2.4b | Detector recall on hollow noteheads and hairpins: one labeling round + head surgery | todo |
| 2.4c | Unread-mark subject: zero-coverage mark-sized ink at a corroborated column → marked bar, never a note | todo |
| 2.5 | Arcs — re-measure after 2.4 | blocked (2.4) |

Gate: > 80% of gathered noteheads reach the file on both scans; all parts
named; second count lower than the first.

## Phase 3 — The staged pipeline becomes the product

| item | what | status |
|---|---|---|
| 3.1 | LilyPond exporter for staged, reusing the `_lily_*` renderers | todo |
| 3.2 | Port the legacy-only list deliberately (weight routing first) | todo |
| 3.3 | Web app `omr_engine=staged`; page cap → job budget; default flips on acceptance parity | todo |
| 3.4 | Corrections as human evidence in the record; re-export; auto-accept over recorded verdicts | todo |

Gate: a whole movement through the web app on staged to MusicXML + PDF; an
accepted correction changes the re-export and the record names the decider.

## Phase 4 — Import from IMSLP

| item | what | status |
|---|---|---|
| 4.1 | `reengrave import <work>`: rank, one browser click at the gate, ingest, run, export, render | todo |
| 4.2 | `Kind.MOVEMENT`; a whole work exports one file per movement | todo |
| 4.3 | Budget printed before the run; unattended mode owns its processes | todo |

Gate: Beethoven 5, four movements, four MusicXML + four PDFs, page ranges right.

## Phase 5 — Clean (ongoing)

Cleanup count every two weeks on the fixed pages; corrections filed as
evidence; auto-accept rules from recorded verdicts. Done for a publisher when
Sean would rather fix than re-enter.
