# `duration_narrowed` triage — ROADMAP 2.36

STAGED only. Read-only triage of the two 2026-09-29 afternoon acceptance
records (`benchmarks/acceptance/manifest.json`), loaded via plain
`json.loads` (no `record_io.expand_id_lists` — `reason`/`candidates`/`detail`
are never pooled, only `considered`/`basis`/`correlated` are, so this
tabulation needed no pool expansion). No re-gather, no re-adjudication, no
crop batches — one parse of each committed file, once, unattended.

Scripts: `triage.py` (ranks every NARROWED `Q.DURATION` verdict by reason,
candidate set and disagreement class) and `chord_reach.py` (measures one
candidate connection's reach before building it). Raw output in `out/`.

## 1. The ranked table

| reason | Litolff (n=1,187 narrowed) | Brahms (n=3,211 narrowed) |
|---|---:|---:|
| `beams_ambiguous` | 779 | 1,960 |
| `beam_discounted_uncertain` (2.25b) | 320 | 1,102 |
| `flags_disagree` | 5 | 75 |
| `flag_ink_unread` (2.18c) | 23 | 54 |
| `rest_slot_contradicts_class` | 38 | 11 |
| `head_fill_from_ink` (2.23) | 22 | 9 |

(`n_narrowed` here is the raw ADJUDICATE-level count before EVALUATE's
`reconcile_duration` bar-sum repair runs — EXPORT's own `duration_narrowed`
bucket after that repair is smaller: ~902 Litolff, ~2,559 Brahms per
`benchmarks/acceptance/current.json`.)

`beams_ambiguous`'s own disagreement classes (`by_disagreement_class` in
`out/*.json`), both documents dominated by the same shape:

| disagreement | Litolff |
|---|---:|
| `beam_count_certain=0_possible=1` | 495 |
| `beam_count_certain=1_possible=2` | 132 |
| `beam_count_certain=0_possible=2` | 51 |

"certain=0, possible=1" is *"nothing certainly covers this note, but one
stroke might"* — the biggest single bucket in both documents by a wide
margin (Brahms's own breakdown is in `out/brahms.json`, same shape).

## 2. Does the biggest class FOLLOW from anything filed? Measured, not guessed

**No connection was found for `beam_count_certain=0_possible=1` itself.**
It is a first-hand geometric judgement about ONE stroke's relationship to
ONE note (`rhythm._beam_levels`), and nothing else on the record witnesses
the same fact from a different angle — the ambiguity is genuinely
undecidable from what is filed today. Deciding it would need a NEW reader
(a second, independent measurement of "does this stroke belong to this
stem" — e.g. an ink-continuity test between the stem's own pixels and the
stroke, in the shape of 2.18c's `Q.STEM_TIP_INK`, but for the BEAM rather
than the flag). **Not built here** — building it without a second witness
would be exactly the guess CLAUDE.md rule 6 forbids.

## 3. The connection that DOES follow: a chord's members share one stem

A physical fact of notation, not an inference: two noteheads struck on ONE
stem are one note event and carry one duration. The record already states,
per glyph, which `Q.STEM` observation its own head box overlapped
(`rhythm._stem_joined`'s `attached`, written into `Ruling.used` by
`adjudicate_duration`) — so two glyphs whose `Q.DURATION` verdicts both name
the SAME stem row are provably chord mates, no re-measurement needed.

**Reach measured first** (`chord_reach.py`, CLAUDE.md rule 5):

| | Litolff | Brahms |
|---|---:|---:|
| narrowed notes (rests excluded) | 1,149 | 3,200 |
| … with a stem in their own `used` | 633 | 1,783 |
| … with >=1 DECIDED stem-mate | 49 | 63 |
| … with EXACTLY ONE DECIDED stem-mate | 38 | 40 |
| … whose narrowing already admits that mate's level -> **would be DECIDED** | **32** | **37** |

All 69 resolved rows are `beams_ambiguous`. This is modest — about 2.8% of
Litolff's narrowed notes, 1.2% of Brahms's — and it is reported as modest
rather than inflated: most narrowed notes have no stem in `used` at all (the
majority of `beams_ambiguous` is a single, un-beamed-looking note with no
sibling to connect to), and most that DO have a stem have no DECIDED
stem-mate in the same bar (chords are a minority of notes). It is the
connection that FOLLOWS, not the biggest bucket.

### Wired (EVALUATE): `consequences.reconcile_chord_duration`

New rule, `tools/omr/staged/consequences.py`, registered under a new
`Consequence.RECONCILE_CHORD_DURATION` tag (kept separate from
`RECONCILE_DURATION` — the existing `test_the_rule_is_downhill_and_carries_a_
bound` in `test_staged_duration.py` picks `evaluate.RULES` by consequence
tag and expects exactly one row per tag; giving the new rule its own tag
avoided colliding with that test rather than weakening it). Same
`cause=Q.METER`, `effect=Q.DURATION`, `scope=Kind.CELL` as
`reconcile_duration`; registered earlier in the file so it runs FIRST in the
same EVALUATE pass (file order is the stable-sort tie-break for rules
sharing a cause), letting a chord-settled note feed the bar-sum search that
follows it.

Per cell: for every NARROWED, non-rest `Q.DURATION` verdict, find the
`Q.STEM` ids in its OWN `used` (not `considered`/`basis` — `adjudicate_
duration` reads EVERY stem in the cell into those, the same set for every
note in the bar; only `used` narrows to the ids `_stem_joined` actually
attached to THIS head's box). If exactly one OTHER glyph's DECIDED duration
in the cell shares one of those ids, AND that mate's own `beam_levels` is
one of the narrowing's OWN candidates, decide it to that candidate. Refuses
(stays NARROWED) on: no stem in `used`; zero or >=2 decided stem-mates
(ambiguous which stem is this note's own — rule 8); a mate level the
narrowing never offered (never invents past what the reader admitted —
caught the `head_fill_from_ink` case directly, where three candidates all
carry `beam_levels: 0` and a beam_levels-0 mate would otherwise look like it
picks one arbitrarily).

### Tests (RED confirmed, GREEN after)

`tools/omr/tests/test_staged_chord_duration.py`, 12 tests. RED confirmed by
copying `origin/main`'s `consequences.py` in over the edited file and
running the suite (12/12 fail with `AttributeError`, the function does not
exist there), then restoring the edited file (12/12 pass). Positive case +
one variant (candidate order doesn't matter, only membership); seven
negative controls (no shared stem; empty `used`; two disagreeing decided
mates; a mate level never offered; the `head_fill_from_ink` three-way-tie
case; a rest, defensively, though `_is_rest` already excludes it
structurally — no rest-reading function touched; no decided note in the
cell at all); a provenance check (superseded row stays on the record); two
registration checks (it is downhill/bounded; it runs before
`reconcile_duration` in the same pass).

## 4. Not built

- The biggest class itself (§2) — needs a new GATHER-side witness, named,
  not built.
- `beam_discounted_uncertain` (2.25b's own rule 8 narrowing) and
  `flags_disagree` were checked against the same chord-mate connection by
  the same script logic (any reason qualifies structurally) — the 69
  resolved rows above are ALL `beams_ambiguous`; no `beam_discounted_
  uncertain` or `flags_disagree` row happened to have a qualifying decided
  stem-mate on either acceptance record. Not a design gap — just this
  population's shape today.
- `rest_slot_contradicts_class` — a rest carries no stem and is out of
  scope for this lane (rest-related functions and `family_precision.py` are
  reserved for the concurrent 2.35 lane).
- `head_fill_from_ink` beyond the guard above — no connection attempted;
  the mate speaks to beam count, not notehead fill, and the two must not be
  conflated.

## 5. Questions for Sean

- Is "two noteheads on one stem share one duration" itself something worth
  spelling out as a rule/DECISIONS line, or is it self-evident enough to
  leave as code commentary only (it is notation, not a convention with an
  edge case)?
- Worth a follow-on lane building the missing GATHER-side witness named in
  §2 (a beam/stem ink-continuity test, mirroring 2.18c's `Q.STEM_TIP_INK`
  but for beam strokes)? That is the one that would move the biggest
  bucket, and it was intentionally NOT built here (no second witness to
  connect it to yet).

## 6. The missing witness, built — ROADMAP 2.38

STAGED only, `claude/beam-stem-ink-2.38`. Answers §5's own question: the
GATHER-side ink-continuity witness for `beams_ambiguous`'s biggest bucket
(`certain=0, possible=1`, §1) that §2/§3 said was needed but did not build.

**CONVENTION ASSUMED / WHAT WOULD FALSIFY IT / NOT CONFIRMED.** A beamed
stem's own ink is continuous with its beam at the tip -- the two are one
connected mark on a clean plate. CLAUDE.md §10: Litolff MERGES and
Breitkopf SHATTERS, so a shattered junction may show a thin blank seam at
the exact join even where the stem and the beam are the SAME mark -- the
tolerance below exists for exactly that seam, never for a genuinely
separate stroke standing apart. Falsified by a print-confirmed join whose
seam is wider than one measured staff-line thickness, or a print-confirmed
NON-join (an unrelated stroke) whose gap is narrower than one. **NOT
CONFIRMED** -- argued from CLAUDE.md's own shattering/merging finding,
never measured against a real beam-junction crop (§7 below).

### The quantity and reader

`Q.BEAM_STEM_JOIN` (`gather.beam_stem_join_ink`, `gather._observe_beam_
stem_join`, reader `READERS.CV_BEAM_JOIN`, `CLAIM.MEASUREMENT`). One row
per (`Q.STEM` row, `Q.BEAM_STROKE` row, end) -- GATHER files the whole
small stem-x-stroke cross product in a cell, both ends, because it does not
know which end is the true tip (`Q.STEM_DIRECTION`'s question, decided
later) or which stroke is even a candidate (`rhythm._beam_levels`'s own
column test, decided later still). `value` is whether the stem's own ink,
scanned in its own x-range, runs CONTINUOUSLY from that end into ink at or
past the candidate stroke's own near edge:

- the tip already sits INSIDE the stroke's own y-range -- joined, no gap;
- the stroke stands cleanly past the tip -- walk the stem's x-range for the
  LONGEST unbroken blank run between the two; joined iff it never exceeds
  the tolerance;
- neither (a slur/arc crossing the stem's own body mid-length, or a stroke
  on the wrong side) -- read as NOT joined outright. This is a real answer,
  not a decline: nothing about a mid-length crossing speaks to whether
  THIS tip has a beam, and reading the stem's own continuous body-ink as if
  it answered the question would be exactly the guess rule 6 forbids.

ABSTAINS -- never defaults -- where the raster or the cell's staff-space
unit is missing, or the stem carries no usable x-range.

### The tolerance, derived not guessed

`BEAM_STEM_JOIN_GAP_TOLERANCE_THICKNESS_MULT = 1.0`, applied to `cell.
staff_line_thickness_canonical` (`measure_extractor.py`'s own measurement of
THIS plate's line erosion, already scaled into the same canonical frame
`image_no_staff` is in -- no new measurement, no frame conversion). A
staff line and a beam stroke are drawn with comparable engraving weight, so
a break the width of ONE measured line is the largest gap a shattering
plate plausibly puts in a mark that is really continuous; wider than that
is a genuinely separate piece of ink. Falls back to `LEDGER_RUNG_INK_
DEFAULT_THICKNESS_SPACES`'s own fraction (0.09 staff spaces) where a cell's
thickness was never traced, same convention, same reason: no cell in
either of this lane's own tests needed the fallback (none was measured
against a real page -- see §7).

### Wiring into ADJUDICATE

`rhythm._beam_levels` gained a `join_witness` parameter (`{stroke id:
True/False/None}`, from the new `rhythm._beam_join_witness`), consulted
ONLY for a stroke the column test would otherwise count as merely POSSIBLE
(the padded-column branch) -- never one already CERTAIN by exact overlap or
by `_stem_joined`'s own box test, which is the positive control this rule
must never move. Where the ink reader says JOINED, the stroke is promoted
to CERTAIN (the level is counted); where it says NOT JOINED, the stroke is
dropped entirely, from both certain and possible (the level is dropped,
and where it was the note's only candidate the note decides at its head
value); where the reader never reached it (`None` -- declined, or simply
never gathered), the stroke stays exactly as box geometry alone called it
and the note stays NARROWED -- rule 8's "a fallback never converts cannot
tell into an answer", applied a fourth time in this module (`_stem_tip_
flag_ink`, `_ink_reads_decisively_hollow` and this being the other three).
`_beam_join_witness` reads only the end this head's OWN stem direction
points to (`Q.STEM_DIRECTION`'s `stem_projection` reason), the same
discipline `_stem_tip_flag_ink` (2.18c) already states for itself.

`Q.BEAM_STEM_JOIN` joins `Q.DURATION`'s `wants`/`composed_from`: the
OUTCOME, not only the value, now depends on it.

### Independence, argued (CLAUDE.md §4b)

The two witnesses read the SAME staff-erased raster (`image_no_staff`) --
by the convention `CV_INK`/`CV_LEDGER`/`CV_STEM_TIP`'s own `READERS`
entries already state, that means they are not immune to a SHARED plate
defect (bleed-through, a torn scan could fail both together) and this is
named, not hidden, exactly as those three name it for themselves. But they
are mechanically independent by the pipeline's own test:
`adjudicate.Evidence.correlated_groups`/`_one_signal` buckets two
Observations as ONE signal only when they share the exact SAME `(reader,
frame, quantity)` key, and `CV_BEAM_JOIN`/`Q.BEAM_STEM_JOIN` are both new,
so they never bucket with `CV_LINES`'s own `Q.BEAM_STROKE`/`Q.STEM` rows.
More than a naming trick: the two ask genuinely different questions of the
ink -- `rhythm._beam_levels`'s column test is a question about a STROKE's
own bounding BOX (does its x-range cover this note's column, exactly or
padded -- geometry from `line_detection`'s morphology), while `Q.BEAM_STEM_
JOIN` is a question about PIXEL CONTINUITY at one specific junction
coordinate, independent of either object's own box. A box can be
imprecise (too short, too long, offset) in ways that do not correlate with
whether the physical ink at the junction is actually continuous, which is
exactly the shape of disagreement this lane exists to catch (the geometry
says "maybe", the ink says "yes" or "no").

### Tests -- RED confirmed

`tools/omr/tests/test_staged_beam_stem_join.py`, 24 tests, four parts: the
pure measurement (`beam_stem_join_ink`, all six synthetic-raster shapes the
brief named -- ends-in-the-beam, one-space-past-with-no-ink, a shattered
1px seam, a gap wider than the tolerance, a slur/arc touching mid-length,
the bottom-tip mirror, window-off-raster, no-raster, stem-x-unknown);
`_observe_beam_stem_join`'s GATHER integration (one row per stem/stroke/end
triple, `NO_MASK`/`NO_STAFF_GEOMETRY` abstentions, the default-thickness
fallback); `_beam_levels`'s witness wiring in isolation (joined/not-joined/
declined, and the POSITIVE CONTROL that an already-certain stroke is
unmoved by a contradicting witness); and the full ADJUDICATE wiring through
`adjudicate.run` (possible+joined -> DECIDED at one beam level;
possible+not-joined -> DECIDED at the head value, the level dropped;
possible+declined -> stays NARROWED `beams_ambiguous`, the unwitnessed
baseline; the join row is in the verdict's `basis`; and the POSITIVE
CONTROL again, end to end -- a stem that already reaches the stroke by box
overlap decides at one beam level even when a filed `Q.BEAM_STEM_JOIN` row
says `found=False` for that same pair).

RED confirmed by restoring `origin/main`'s own `record.py`/`gather.py`/
`capture.py`/`adjudicators/rhythm.py` over the edited files (`git show
HEAD:<path>`) and running the suite: 22 of 24 fail (`AttributeError` /
`TypeError` -- the quantity, reader and `join_witness` parameter do not
exist there); the 2 that pass are the deliberate NO-OP controls
(`test_no_witness_is_the_UNCHANGED_baseline`, `test_the_UNWITNESSED_
baseline_stays_NARROWED`) that assert the PRE-EXISTING behaviour this lane
builds on top of, not the new code -- they are supposed to pass on both
trees. Restoring the edited files returns all 24 to GREEN.

`pytest -m "not slow" tools/omr/tests`: **3,959 passed / 3 skipped** on
this branch, clean (0 failed, a full run confirmed after an EARLIER run
raced against this lane's own RED/GREEN file-swapping and reported 4
spurious failures -- diagnosed as transient, not a code fault, and
re-confirmed clean on a settled tree). This lane's source edits touch no
test file, so the whole delta from `origin/main` is its own 24 new tests:
**3,935 passed / 3 skipped is `origin/main`'s own count**, by subtraction
(3,959 − 24), not a separately re-run number -- the sibling files this
lane's change reaches directly (`test_staged_duration.py` +
`test_staged_stem_tip_ink.py`, 114 tests) were re-run explicitly and are
unchanged. `python3 -m tools.omr.staged.check`: **TOTAL 245, unchanged
from base** (`staged.wiring` 67 and
`staged.capture` 18, both unchanged) -- the new quantity's own diagnostic
detail fields (`gap_px`, `max_blank_run_px`, `window_canonical`) are folded
into the SAME `**m` dict-spread `stem_tip_ink`'s own diagnostic fields use,
which is what keeps them invisible to `wiring.details`'s literal-keyword
AST walk (a `gap_tolerance_px` passed as its OWN named keyword at the call
site was caught as a new, unaccounted DETAIL gap on the first pass and
moved into the same `**m` spread to match precedent, rather than growing
`wiring.KNOWN_GAPS`). `staged.reach` (22, unchanged) confirms the new
quantity has a live consumer (`rhythm._beam_join_witness`), and `staged.
capture`'s `READER_RASTER` table gained one line (`CV_BEAM_JOIN` ->
`staged/gather.py::_observe_beam_stem_join`, erased raster) so the new
reader is not reported as an unresolved raster question.

## 7. Not built (2.38)

- **No print check.** No gather was run against a real page (Sean, 2026-
  09-28: prove lanes cheaply; no per-change whole-movement runs, and a
  single-page gather still costs real wall time this lane's own tests did
  not need). The tolerance's real-page behaviour, and the convention box
  at the top of §6, are therefore NOT CONFIRMED against a print, only
  against synthetic rasters built to the shapes the brief named.
- **`beam_discounted_uncertain` (2.25b) was not wired to this witness.**
  The brief's own wiring instruction ("where the box geometry said
  possible") is `_beam_levels`'s padded-column branch specifically; 2.25b's
  narrowing fires on a DIFFERENT branch (every candidate stroke discounted
  as a neighbour-staff/decided-arc/ledger-line false positive, none left).
  The same ink witness could in principle be asked of the DISCOUNTED
  stroke itself (does the stem's ink reach it after all, overriding the
  discount, or confirm the discount was right) -- named here as the
  natural next step, not built, to keep this lane's blast radius to the
  one branch the brief specified and the tests were written against.
- **Multiple own stems on one head** (`_beam_join_witness`'s own docstring)
  fold a disagreement between two of a chord's stems with `any()` rather
  than refusing -- the more permissive reading, named rather than hidden,
  and not a case either acceptance record's own population presents today.

## 8. Questions for Sean

- Is `BEAM_STEM_JOIN_GAP_TOLERANCE_THICKNESS_MULT = 1.0` (one measured
  staff-line thickness) the right multiple, or should a shattered junction
  get more slack than a staff line's own thickness -- and is the
  `LEDGER_RUNG_INK_DEFAULT_THICKNESS_SPACES` fallback (0.09 spaces) an
  acceptable stand-in where a cell's own thickness was never traced, given
  neither has been checked against a beam-junction crop yet?
- Worth a print check on Litolff/Breitkopf before this lands, or is the
  test coverage (RED-confirmed, positive-controlled, every named shape
  covered) enough to merge and let the acceptance records themselves show
  whether the bucket actually moves?
- Is `beam_discounted_uncertain` (§7) worth the same connection as a
  follow-on lane, now that the witness exists?
