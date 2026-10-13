# The staged pipeline: internals

The record model, the adjudicators, EVALUATE/INFER/EXPORT, the derived
checks and their blind spots. Moved out of `CLAUDE.md` §3 and §4 on
2026-10-13 (`docs/claude-md-migration-2026-10-13.md`). The per-stage
sequence docs (`docs/gather-sequence-2026-10-06.md`,
`docs/adjudicate-sequence-2026-10-07.md`, `docs/evaluate-sequence-2026-10-07.md`,
`docs/infer-sequence-2026-10-07.md`, `docs/export-sequence-2026-10-07.md`)
hold the order inside each stage.

## 1. Two readers, one product path

**STAGED** (`tools/omr/staged/`) is the product path (DECISIONS 2026-09-22).
Every decision is filed against a subject on an append-only record, may
abstain, and can be traced. It exports MusicXML and, since ROADMAP 3.1,
LilyPond (`--lilypond`) and a compiled PDF (`--pdf`, ROADMAP 3.3). ROADMAP
3.3 wires `omr_engine=staged` into the web app, but `local` remains the web
app's default engine, and the staged path lacks several legacy filters --
Phase 3 items on the roadmap.

**LEGACY** (`tools/omr/transcribe.py`, `tools/omr/export.py`,
`tools/omr/contextual.py` and their satellites) is FROZEN: bug fixes only, no
new mechanisms, no new flags. It is what the web app and every benchmark run
until Phase 3 replaces them, and it is the reference reader for A/B. Its 39
flags are frozen with it and may not be read from `tools/omr/staged/`.

Shared by both: the detector (`yolo_detector.py`, the weights, weight
routing), staff/system/barline/measure extraction (`staff_detector.py`,
`system_grouping.py`, `measure_extractor.py`, `preprocessing.py`), the header
readers (`staff_header.py`, `clef_*`, `key_signature_*`,
`time_signature_locator.py`), `line_detection.py`, the direction-text and
margin-label readers, the library, the dossiers, the fact sheet.

## 2. The stages

| stage | question | acts when |
|---|---|---|
| **GATHER** | what is on the page? | always -- decides nothing |
| **ADJUDICATE** | what does this ONE thing mean, on what evidence? | it can read it; else abstains |
| **EVALUATE** | what follows NECESSARILY from what we now know? | the answer is forced |
| **INFER** | what is most LIKELY, given everything at once? | the answer is best -- labelled |
| **EXPORT** | write it, and count what did not make it | always |

The stage a change belongs in is decided by one question: does the answer
FOLLOW, or is it merely BEST? EVALUATE goes silent where two answers both
fit; INFER is the only stage allowed to choose between them, it may only
collapse a NARROWED verdict to one of that reader's own candidates, and it
never overturns a DECIDED one. EXPORT refuses to argmax a narrowing.

## 3. The record (`staged/record.py`)

- **Subjects** form a tree: `Kind.DOCUMENT > PAGE > SYSTEM > STAFF > CELL >
  GLYPH`. A glyph's last coordinate is an index into the detector's output
  for that cell, so ink the detector did not fire on has no glyph subject;
  `Q.INK` is the population beneath that (one row per connected ink
  component, filed at an offset ordinal).
- **Rows** are Observations (a reader saw something, with `reader`, `frame`,
  `score` -- a ruler reading has `score=None`) or Abstentions (a reader looked
  and could not say, with a reason word). `State.READ / DECLINED / ABSENT`
  keeps *a reader found nothing* apart from *no reader ran*, and that
  distinction is the reason the record exists.
- **Verdicts** are `Outcome.DECIDED / NARROWED / ABSTAINED` with a `basis`
  (which rows) and a `reason`. `NARROWED` carries candidates and their
  support. `Verdict.correlated` records which witnesses share provenance.
- **Quantities** (`record.Q`) are the vocabulary. Their producers and
  consumers are DERIVED by `gather_coverage`, `wiring` and `reach`; do not
  type the list anywhere.
- **Scope** (`EXACT / SELF_AND_ANCESTORS / SELF_AND_DESCENDANTS`) says where a
  consumer looks. A quantity filed on a STAFF read by a DOCUMENT decision
  returns nothing at `EXACT` and fails silently; `wiring --check` catches
  the declared cases. The same silence governs ORDER inside GATHER: a reader
  placed above the reader whose rows it reads gets an empty answer, not an
  error, so a reader runs after every producer it reads and the forced edges
  are DERIVED from those reads (`gather.gather`'s docstring), never counted
  (A-GATHER-1 said three; the tree held eleven, one backwards -- ROADMAP 2.58).
- **Provenance**: every record is stamped with the commit and `dirty`. A
  record from a dirty tree, or with `dirty is None`, is not a baseline.
- **`Evidence.correlated_groups`**: rows from one reader on one crop are ONE
  signal. A position hung off a glyph row is absorbed by that glyph's own
  term; a second witness needs its own quantity and its own reader.

## 4. The decisions

The adjudicators live in `staged/adjudicators/` (`structure.py`,
`identity.py`, `header.py`, `clef.py`, `ownership.py`, `rhythm.py`, `text.py`,
`notehead_precision.py`, `family_precision.py`, `movement.py`, `position.py`,
`rest_search.py`, `unread_mark.py`, `key_slots.py`, ...), each registered by
`@decision` into `adjudicate.REGISTRY` and run in `adjudicate.ORDER`. The
count and the order are DERIVED, never typed:

```bash
python3 -c "from tools.omr.staged import adjudicate; print(len(adjudicate.ORDER)); print(*adjudicate.ORDER)"
```

Each declares `wants`, `implicates`, `checked_by` and `reasons`; `inventory
--check` reports a declaration the body does not read. Stubs:
`adjudicate.stubs()` is the truth.

**EVALUATE** (`consequences.py`, `evaluate.py`): `restate_pitch` (position +
clef => pitch), `respell_accidental` (key => sounding alteration),
`move_glyph` (ownership => pitch re-derived), `size_measure_rest` (a lone
dotless whole rest takes the BAR's length), `reconcile_duration` (a beam
level re-read by +/-1 only where exactly one re-reading lands the bar),
`pair_word_and_dynamic` (a bar's word + its adjacent dynamic => one
`Q.MARKING`), and the join. Rule order matters and is asserted: `move_glyph`
runs after `respell_accidental`, which is why the sounding pitch is routed at
EXPORT and not revised in EVALUATE.

**INFER** (`infer.py`, `inferences.py`): every rule registers with a
`Switch` that names its gate. `collapse_slot_index_to_family_block`
(print-verified) and `fill_clef_gap` are `ALWAYS_ON` (promoted 2026-10-07,
ROADMAP 0.2c); the duration rules gate on `OMR_INFER` (default ON since
2026-09-23, ROADMAP 2.3), the part-key rule on `OMR_PART_KEY`. The list is
DERIVED: `infer.RULES` and each rule's `switch.env`. The harness enforces:
runs after EVALUATE, refuses an unfrozen log, writes only where the record
has no answer, never invents a value, supersedes visibly. Since 2026-10-13
(ROADMAP 2.103) every INFER collapse and every bar-sum confirmation is
written GUESSED (blue, `export.GUESS_COLOR`, carrying its candidates); the
rules themselves are bound by the eighth-on-evidence and tuplet-only-when-
seen rules in `CLAUDE.md` §4.

**EXPORT** (`staged/export.py`): MusicXML (and LilyPond/PDF through it).
Reuses the legacy pure renderers (`_mxl_*`) over its own positions. The
accounting control is an EQUALITY -- every gathered notehead is written or
counted under a named refusal (`duration_narrowed`, `no_pitch`,
`staff_not_identified`, `owned_by_another_staff`, `owner_not_read`,
`ink_is_a_whole_rest`) -- and `to_musicxml` RAISES `Unbalanced` rather than
returning a flag. A staff the join could not name is held out of the file
and counted (`OMR_HOLD_OUT_UNIDENTIFIED`). A bar we read nothing in exports
as a measure rest with `measure="yes"` withheld, because we read NOTHING
there, not silence. `status_census` is a partition over every family with an
`unaccounted` bucket a test requires empty; prefer it to any headline
coverage number.

## 5. The derived checks

`python3 -m tools.omr.staged.check` runs all of them and writes
`benchmarks/acceptance/open-findings.json`. Exit 2 = a check is broken; exit
1 = N open findings; exit 0 = clean. **N must go down.** A finding leaves the
list when it is wired, not when it is explained; a `KNOWN_GAPS` entry is a
reason a gap EXISTS, never a reason one is acceptable.

The parts: `inventory` (declarations vs bodies), `health` (decides / abstains
/ records), `wiring` (declared input read where it is filed), `reach` (does
every quantity reach a live consumer), `gather_coverage` (declared vs
gathered quantities, detector families with no quantity), `capture` (shape /
position / raster / resolution per family), `brakes` (refusals whose premise
may have expired), `trace` (what each stage did to one symbol; `--subject`,
`--family`, `--empty-claims`), `conventions` (the engraving registry,
`tools/omr/conventions.py`, and what reads it), `no_producer` (a parameter
threaded with no supplier), `export_coverage` (elements the truth has and we
never emit), `accuracy_record` (the recorded engraved figure agrees with the
tree).

Three blind spots, by construction: none of them sees a GATHER change
(`readjudicate` and `reexport_arm` rebuild from a saved record -- pricing a
GATHER change needs two full re-gathers); none of them sees the DETECTOR;
and `wiring` matches a detail key by bare name, so an unrelated module
naming the same string reads as a consumer.

A new staged module must be registered in `reach.NOT_A_STAGE` or `reach`
reads it as a stage.
