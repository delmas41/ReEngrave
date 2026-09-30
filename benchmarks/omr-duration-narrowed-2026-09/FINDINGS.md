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
- neither (a slur/arc crossing the stem's own body mid-length, an
  overshot stem box, or a secondary beam sitting just inside a primary) --
  ⚠️ **CORRECTED IN PLACE, manager review of the first commit (024bdc7c) --
  see "Manager review, 024bdc7c" below.** This was first built as a real
  answer ("NOT joined outright"), which was WRONG: `_beam_levels` drops a
  `found=False` stroke entirely, and this position is exactly the shape a
  real secondary beam or an overshot stem box takes, not only a slur. It
  DECLINES (`None`), never a "not joined" answer -- rule 8, cannot tell is
  never an answer.

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

### Manager review, 024bdc7c: the third case was a false NOT JOINED

The first landing (`024bdc7c`) gave `beam_stem_join_ink` THREE outcomes:
ends-in-the-beam (joined), cleanly-past-the-tip (measured), and "neither"
-- a stroke that neither reaches the tip nor stands cleanly past it --
which read as `found=False`, i.e. NOT JOINED, and `_beam_levels` DROPS a
`found=False` stroke entirely (neither certain nor possible). **That third
case is wrong for real music**, caught in review before this landed
further: a stroke sitting inside the stem's own reported extent, neither
at the tip nor past it, is the exact shape THREE different things take,
and position alone cannot separate them --

1. a SECONDARY beam (16th/32nd) attaching along the stem's body just
   inside the PRIMARY -- on a real `certain=1, possible=2` note (Brahms
   234 was the example given) the possible stroke is usually exactly this
   second level, and the old rule would have dropped its only candidate;
2. a `Q.STEM` box that OVERSHOOTS its own beam (the CV stem read past the
   ink it should have stopped at) puts the PRIMARY itself in this same
   position;
3. a slur/arc crossing the stem is the only one of the three this case
   was originally meant to name, and the ink cannot tell it apart from
   (1)/(2) with this test.

**Fix**: the "neither" case now returns `None` -- DECLINED, rule 8, cannot
tell is never an answer -- so the note stays NARROWED rather than losing
the candidate. `_beam_stem_beyond_tip` is the shared gate (used by both
`beam_stem_join_ink`'s own check and `_observe_beam_stem_join`'s abstain
reason, so the two cannot drift apart); `_observe_beam_stem_join` now
abstains this case under its OWN word, `ABSTAIN.AMBIGUOUS`, rather than
folding it into `NO_STAFF_GEOMETRY`'s "the raster is missing" sense.

**What NOT JOINED (`found=False`) rests on, after the fix**: exactly one
case -- the stroke stands CLEANLY past the tip (the whole stroke is on the
tip's own far side, position unambiguous) AND the longest unbroken blank
run between the tip and the stroke's near edge exceeds the measured
tolerance. Every other outcome is either JOINED (ends in the beam, or a
clean gap within tolerance) or DECLINED (raster/geometry missing, or the
position is ambiguous per the three cases above).

**The optional stacked-level rule (a crossing stroke within one beam-gap
of an already-JOINED/CERTAIN stroke on this stem, ink continuous between
them, promoted to JOINED as a stacked level) was NOT built** -- named as
optional in review, and building it correctly requires deriving the
expected beam-to-beam spacing from this cell's own MEASURED strokes (not
a constant), which is its own small design problem and its own tests; the
required fix above (declining rather than guessing) is sufficient to stop
the drop, and leaves the secondary NARROWED rather than silently right.
Left as a named follow-on, not built here.

4 new tests added for this fix (RED confirmed against the pre-fix
`024bdc7c` gather.py: 5 of 5 tests touching the changed behaviour fail --
3 pure-function shapes matching cases (1)/(2)/(3) above, one GATHER-
integration test confirming `ABSTAIN.AMBIGUOUS` rather than a false
Observation, and one existing test whose fixture happened to exercise a
now-ambiguous BOTTOM end and needed its own assertion corrected, not just
loosened); one further end-to-end test of the realistic `certain=1,
possible=2` shape was added for documentation and does not by itself
regress against the bug (it does not gather, so it exercises the ALREADY-
correct "declined stays possible" ADJUDICATE-side path either way) --
named honestly rather than claimed as a second RED proof. All 28 pass on
the fixed tree.

### Manager print check, 3c748f45: the horizontal-reach bug

Manager print check on a real page (Brahms p1, `--through adjudicate`,
`out/print/beam-stem-ink-2.38/brahms-p1.record.json` + `crops.py`). The
witness settled 583 duration verdicts (359 JOINED->decided, 224 NOT
JOINED->decided); **3 of 4 sampled JOINED crops were WRONG**: the
candidate stroke was a DIFFERENT group's beam, 4-10 staff spaces to the
side of the stem, promoting an 8th to a 16th.

**The bug**: `beam_stem_join_ink`'s continuity scan walks the STEM's OWN
x-range vertically between the tip and the candidate's near edge, and
nowhere checked that the candidate stroke is even horizontally near that
stem. THIS stem's own real beam sits directly above/below its tip, in
its own column; where a far-away, unrelated stroke's y-range happened to
land near that same height, the scan found the STEM's OWN ink and
credited it to the wrong candidate. Measured on the pre-fix Brahms p1
record: of 338 (stem, stroke) pairs a duration verdict actually USED with
`value=True`, the two boxes' horizontal gap ranged 0-1,406 canonical px
(median staff space on this page ~91-100px), and **109 of 338 (32%) had
a gap over 200px** (roughly 2+ staff spaces) -- not a rare edge case.

**Fix**: `beam_stem_join_ink` gained `stroke_x0`/`stroke_x1` parameters and
a new gate, `_beam_stem_horizontally_reaches` (stroke x0 <= stem x1 + tol
and stroke x1 >= stem x0 - tol, tol = the same measured-thickness
tolerance already used vertically), checked FIRST, before any pixel is
read. A stroke that does not cover the stem is NOT JOINED -- a real
answer settled by the two boxes alone, not a decline (rule 6: the
geometry alone decides this, no ink need be read). `_observe_beam_stem_
join` now extracts the beam's own `x_canonical`/`width_canonical` and
passes them through.

**Re-gathered Brahms p1 with the fix** (`--through adjudicate`, ~2 min):
new used-counts, `{(False, 'decided'): 562, (True, 'decided'): 213,
(False, 'narrowed'): 29, (True, 'narrowed'): 1}` -- JOINED 359->214, NOT
JOINED 224->591 (many pairs that were silently ambiguous before now get a
definite NOT JOINED from the horizontal check firing before the vertical
ambiguity check ever runs). Measured on the FIXED record: of the (stem,
stroke) pairs a duration verdict used with `value=True`, the horizontal
gap is now 0-17px, ALL under the tolerance -- **zero** over 50px, against
109 of 338 over 200px before. `out/print/beam-stem-ink-2.38/
brahms_beam_join_used.png` (regenerated): all 4 JOINED crops now show the
green (stem) bracket directly touching the blue-boxed candidate stroke;
all 4 NOT JOINED crops show the red bracket nowhere near the highlighted
stroke (a hairpin, another group's beam) -- both families read correctly
by eye.

**Does `_beam_levels`'s padded-column test admit strokes several staff
spaces off?** Asked, not changed (manager: only change it if trivially
wrong -- it is not). Measured on the pre-fix record's own USED population:
beam-stroke widths ranged 123-1,382 canonical px, median ~345px (~3.5
staff spaces) -- a SINGLE beam stroke commonly spans several notes, so
its box can genuinely overlap (or come within one notehead-width pad of)
a note's centre column while its FAR end sits many staff spaces away
across an adjacent group. That is not the pad being too generous (the pad
itself is one notehead width, ~1.3 staff spaces, per `BEAM_EDGE_TOLERANCE_
WIDTHS`); it is the column test having no way to know a wide stroke
spanning close to this note does not physically belong to it -- exactly
the ambiguity `Q.BEAM_STEM_JOIN` exists to resolve with a second,
independent reading. Not trivially wrong; not changed.

2 new tests (30 total): a far stroke at the stem's own beam's height ->
NOT JOINED (`test_a_FAR_stroke_at_the_SAME_y_as_the_stems_own_beam_is_
NOT_joined`); a stroke covering the stem -> unchanged (`test_a_stroke_
COVERING_the_stem_is_UNCHANGED`), the positive control. RED confirmed
against the pre-fix (3c748f45) `gather.py`: all 13 pure-measurement tests
fail (the two new tests on the actual bug; the other 11 on the now-wider
call signature, `TypeError`), 17 still pass (`_observe_beam_stem_join`
GATHER-integration and end-to-end ADJUDICATE tests, unaffected by this
particular signature change). All 30 pass fixed.

No further crops or gathers run beyond the one page this review asked for.

### Manager re-check, 3a5bbb67: the intervening-stroke bug

Re-check with more samples (`crops.py` re-seeded to 7, 8 NOT JOINED / 4
JOINED). NOT JOINED: 8/8 correct (far groups' beams, hairpins). **JOINED:
2 of 4 still WRONG** -- the candidate is a long THIN line (a slur/hairpin
the detector boxed as a beam stroke) lying just beyond the stem's OWN
real beam. The continuity walk goes from the tip up THROUGH the stem's
own beam ink (ink genuinely in the stem's own column) and reaches the
thin line within tolerance, crediting it as a level.

**The bug**: the blank-run scan asks only whether the column is
UNBROKEN, never WHOSE ink it is reading. The stem's own real beam (thick,
immediate, right at the tip) fills most of the walked window; the small
gap between that beam's own far edge and the thin line's near edge passes
the same tolerance meant for a shattered PLATE seam.

**The principle** (engraving, stated by the manager): a stem is joined to
the FIRST stroke its column meets past the tip, never to one beyond
another stroke.

**Fix**: `_beam_stem_intervening_stroke`, checked during the walk before
the blank-run scan. At each row in the walked window, does ink reach past
the stem's own column by more than one STEM WIDTH on at least one side,
sustained over a contiguous run of rows at least one measured staff-line
thickness long? A beam is drawn far wider than the stem it serves (it
reaches every note it covers); a stem's own ink is not. Where such a band
is found, the candidate is NOT JOINED -- the walk met a different stroke
first.

**The optional thin-candidate-thickness guard was NOT built.** Checked
for cleanliness first: several of this lane's own existing tests draw a
candidate's thickness equal to the tolerance value itself (both derived
from the same synthetic `gap_tolerance_px=4.0`), so a 1.5x-thickness
floor would have failed those pre-existing "real beam" fixtures and
required reworking their geometry to stay above the new floor -- not a
clean addition on top of the required fix, only a parallel one. The
wide-band walk-time check above already resolves the confirmed bug on
its own (a genuine beam's own width is what the check detects, whatever
the candidate's own thickness is), so the second guard was skipped.

**Re-gathered Brahms p1, re-ran `crops.py`** (same seed 7, 8 NOT JOINED /
4 JOINED): new used-counts `{(False, 'decided'): 566, (True, 'decided'):
209, (False, 'narrowed'): 29, (True, 'narrowed'): 1}` -- JOINED 214->210,
NOT JOINED 591->595 (four more false positives caught). Eye-checked all
12 crops on the regenerated `brahms_beam_join_used.png`: all 4 JOINED
crops now show the green (stem) bracket directly touching the
blue-boxed candidate with no visible intervening ink; all 8 NOT JOINED
crops correctly point at unrelated ink (hairpins, other groups' beams,
none touching the stem's own bracket).

3 new tests (33 total): a thin line past the stem's own real beam -> NOT
JOINED (the confirmed bug, RED first); tip directly in the candidate ->
JOINED unchanged (positive control, trivial branch untouched); a
shattered-seam blank gap under tolerance -> JOINED unchanged (positive
control, window too short for the new run-length threshold to fire). RED
confirmed against pre-fix (3a5bbb67) `gather.py`: exactly 1 of 33 fails
(the bug test) -- the two positive controls pass on both trees, as
designed. All 33 pass fixed.

A known limitation is named, not solved, in `_beam_stem_intervening_
stroke`'s own docstring: a genuinely continuous single beam physically
split into two adjacent CV-detected boxes would also trip this guard,
since shape alone cannot tell "another stroke" from "the same stroke,
re-boxed". Not measured against a real instance of that shape.

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

**Post-review update (second commit, the fix above): 28 tests** in this
file (4 net new -- 3 pure-function shapes + 1 GATHER-integration test for
the fix, described in "Manager review, 024bdc7c" above). `pytest -m "not
slow" tools/omr/tests`: **3,963 passed / 3 skipped**, clean (0 failed),
= `origin/main`'s own 3,935 + this file's 28, by the same subtraction
logic as the first commit (this lane's edits still touch no OTHER test
file). `python3 -m tools.omr.staged.check`: **TOTAL 245, unchanged from
base** -- confirmed again after the fix (reusing the already-vocabuled
`ABSTAIN.AMBIGUOUS` rather than adding a new reason word kept `wiring`
untouched).

**Post-print-check update (third commit, the horizontal-reach fix in
"Manager print check, 3c748f45" above): 30 tests** in this file (2 net
new). `pytest -m "not slow" tools/omr/tests`: **3,965 passed / 3
skipped** = `origin/main`'s own 3,935 + 30, same subtraction logic, no
other test file touched. `python3 -m tools.omr.staged.check`: **TOTAL
245, unchanged from base** yet again (no new quantity, reader or
detail-key gap -- `stroke_x0`/`stroke_x1` are ordinary parameters, not
observation kwargs).

**Post-re-check update (fourth commit, the intervening-stroke fix in
"Manager re-check, 3a5bbb67" above): 33 tests** in this file (3 net new).
`pytest -m "not slow" tools/omr/tests`: **3,968 passed / 3 skipped** =
`origin/main`'s own 3,935 + 33, same subtraction logic, no other test
file touched. `python3 -m tools.omr.staged.check`: **TOTAL 245, unchanged
from base** yet again -- no new quantity, reader or detail key.

Original first-commit numbers, for the record: `pytest -m "not slow"
tools/omr/tests`: **3,959 passed / 3 skipped** on this branch, clean (0
failed, a full run confirmed after an EARLIER run raced against this
lane's own RED/GREEN file-swapping and reported 4 spurious failures --
diagnosed as transient, not a code fault, and re-confirmed clean on a
settled tree). This lane's source edits touch no test file, so the whole
delta from `origin/main` is its own 24 new tests: **3,935 passed / 3
skipped is `origin/main`'s own count**, by subtraction (3,959 − 24), not a
separately re-run number -- the sibling files this lane's change reaches
directly (`test_staged_duration.py` + `test_staged_stem_tip_ink.py`, 114
tests) were re-run explicitly and are unchanged. `python3 -m tools.omr.
staged.check`: **TOTAL 245, unchanged
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

### §4 manager print check (2026-09-29) — what the crops showed at each fix

Fresh `--through adjudicate` gathers of the two count pages, crops cut at
600 dpi from the PDF (`out/print/beam-stem-ink-2.38/crops.py`, stem =
corner bracket, candidate stroke = blue box, only rows a duration verdict
USED). `024bdc7c`: a stroke crossing the stem's body read NOT JOINED —
drops a real secondary beam → now declines. `3c748f45`: 3 of 4 JOINED were
another group's beam several spaces to the side (the walk found the stem's
OWN beam at that height) → the stroke must cover the stem's x. `3a5bbb67`:
2 of 4 JOINED were a slur/hairpin just beyond the stem's own beam (the walk
passed THROUGH the own beam) → a stem joins the FIRST stroke it meets.
`1ad1c1ca`: Brahms p1 8/8 JOINED + 8/8 NOT JOINED correct (seed 11);
Litolff p3 8/8 + 8/8 correct. Used counts, Brahms p1: joined→decided 209,
not joined→decided 566; Litolff p3: 42 / 11. Sean confirmed the 32 crops;
merged to main `b2aa2fd1`.

### ROADMAP 2.38b — certain strokes get the join check too

A FOLLOW-UP print check after the 2.38 merge (`levels_check.py`,
`levels_check_12.py`, `out/print/beam-stem-ink-2.38/brahms_levels_check*
.png`) found a consequence 2.38's own print checks never asked about: of
165 `duration` verdicts DECIDED using ONLY NOT-JOINED beam witnesses, the
final `beam_levels` were wrong at almost every count above 1 -- level 1
→106 (≈11/12 right), level 2 →14 (6/6 WRONG, single-beam 8ths read as
16ths), level 3-4 →26 (nearly all WRONG, 8ths/16ths read as 32nds), level
0 →19 (≈half wrong, one a bass clef boxed as a head).

**Cause**: `_beam_levels` never consulted `Q.BEAM_STEM_JOIN` for a
CERTAIN stroke (exact column overlap, or already stem-joined by box) --
by design, so the ink reader could never override box-geometry certainty
(the positive control 2.38's own tests protect). But box-only certainty
can itself be wrong: a stroke whose box happens to overlap this stem's
column or `_stem_joined`'s box test is not proof it is THIS stem's own
mark. Before 2.38, an extra POSSIBLE stroke often kept `possible >
certain`, so the note stayed NARROWED (held) despite the wrong certain
count sitting underneath, unseen; 2.38's own NOT-JOINED fixes correctly
dropped those extra possible strokes, and doing so surfaced the
underlying wrong certain counts as DECIDED, wrong, durations.

**Fix** (`claude/beam-certain-join-2.38b`, off `origin/main`/`b2aa2fd1`,
not merged): `_beam_levels` now returns a third element,
`certain_conflicts` -- the ids of any CERTAIN stroke whose `Q.BEAM_STEM_
JOIN` witness reads NOT JOINED. GATHER already files a row per (stem,
stroke, end) for the WHOLE cross product in a cell (`_observe_beam_stem_
join`, unconditional on whether ADJUDICATE will call a given pair
certain or possible), and `_beam_join_witness` already builds its
witness dict over every stroke in `kept` regardless of branch, so no
GATHER change was needed -- only reading the witness that was already
being computed and thrown away for the certain branch. In
`adjudicate_duration`, any non-empty `certain_conflicts` NARROWS
(`beam_certain_not_joined`, checked first, before `flags_disagree`)
between the level AS BOX GEOMETRY COUNTS IT and the level WITHOUT the
disputed stroke(s), EQUAL support (rule 8: nothing says which witness is
right, only that they disagree) -- never decided either way, and the
certain stroke is NEVER dropped outright (`_beam_levels` still counts it
in `certain`/`possible` exactly as before; only the disagreement is
surfaced).

**Re-gathered Brahms p1** (`--through adjudicate`, same command, ~2 min):
`beam_certain_not_joined` now abstains 102 `duration` verdicts. The
NOT-JOINED-only population's own `beam_levels` distribution: level 1
106→98, level 2 **14→3**, level 3-4 **26→3** (`levels_check.py`:
`{'zero': 19, 'three+': 3}`; `levels_check_12.py`: `{'0': 19, '1': 98,
'2': 3, '3': 2, '4': 1}`) -- total population 165→123. Level 0 is
UNCHANGED (19) -- a different mechanism entirely (a possible-only stroke
dropped by the ORIGINAL 2.38 fix, never a certain-branch conflict), out
of this lane's scope; the one named bad case (a bass clef boxed as a
notehead) is a detector-precision fault, not a beam-count one.

**Eye-checked both regenerated crop sheets.** Level-1 crops (12): the
large majority show a correctly single-beamed 8th, box on a real note
inside that group. Level-2 crops (3, all that remain): still show what
look like single-beam 8th groups by eye -- a SMALL RESIDUAL not caught by
this fix, because these are not witness DISAGREEMENTS: box and ink
apparently AGREE (both certain, both joined or declined) on what still
looks like the wrong count by eye. That is a different, harder fault
(both witnesses reading off the same raster and failing together --
CLAUDE.md's own warning about two witnesses off one plate) and is named,
not chased further here. Level 3-4 crops (3) show the same shape.

**Tests**: 4 new/changed in `test_staged_beam_stem_join.py` (was 33, now
37) -- `_beam_levels` unit tests updated to the 3-tuple and two new ones
added (a certain stroke JOINED/DECLINED carries no conflict); at the full
`adjudicate_duration` level, the EXISTING positive control (`test_
POSITIVE_CONTROL_a_box_CERTAIN_join_is_unmoved_by_the_ink`) was ITSELF
the bug, renamed and its assertion corrected to NARROWED with the new
reason word, and two new positive controls added (certain+JOINED,
certain+no-witness, both still DECIDED unchanged). RED confirmed against
`b2aa2fd1`: 8 of 37 fail (7 on the widened `_beam_levels` return
signature, 1 -- the renamed bug test -- on the actual behaviour, DECIDED
where NARROWED is now required).

`pytest -m "not slow" tools/omr/tests`: **3,972 passed / 3 skipped** on
this branch (`origin/main`'s own 3,968 + this file's 4 net new tests, no
other test file touched). `python3 -m tools.omr.staged.check`: **TOTAL
245, unchanged from base** -- no new quantity, reader or detail key; the
new reason word `beam_certain_not_joined` is declared in `Q.DURATION`'s
own `reasons=(...)` tuple, same convention as every sibling reason.

### ROADMAP 2.38c -- the two residuals named by 2.38b, chased, and one
build tried and WITHDRAWN

2.38b named two populations of residual duration faults and left both
unchased: (A) 165 `duration` verdicts DECIDED using ONLY NOT-JOINED beam
witnesses, of which level-0 (19, "about half wrong") was a SEPARATE
mechanism from the certain/possible join test 2.38b itself fixes; and (B)
the ~6 that remained wrong at level >=2 AFTER 2.38b landed, where box
geometry and the ink-continuity witness (`Q.BEAM_STEM_JOIN`) AGREE on a
stroke the print says is not this stem's. This item re-gathered Brahms p1
fresh on today's tree (`--through adjudicate --weights auto`,
`beam_certain_not_joined` fires 102x, matching 2.38b's own count exactly)
and traced every member of both populations against the print, per
CLAUDE.md rule 1 ("brief from the tree") and rule 7 ("a control must be
able to fail" -- re-derived, not read off the prior FINDINGS text).

**⚠️⚠️ WITHDRAWN, RE-CHECKED, CORRECTED (manager review of `ad5f26af`).**
The first pass of this section called crops 08-13 "detector false-positive
noteheads on blank paper." That claim was WRONG on all six, caught by the
manager reading the crops against the print. Root cause of the misjudgment,
found by cross-checking against actual pixel darkness inside each box
(`% dark(<128)`, all six 75-96%, i.e. SOLID INK): the first pass judged
"is there a notehead here" by EYE off a crop rendered ~260-280px of
surrounding whitespace either side of a ~40x30px box, displayed at the
image viewer's own downscaled resolution -- at that scale a small solid
black square sits close enough to the surrounding staff-line ink that it
reads, at a glance, as part of the background rather than a distinct
filled shape. No numeric check (ink density inside the box) was run before
writing "should not be a note at all" the first time; a tight 4x zoom crop
and a pixel-darkness measurement (`check_pixels.py`, not committed) both
confirm every one of the six is a real, solidly-inked notehead. This
section is corrected below; the wrong claim is left visible here rather
than deleted, per instruction.

**Method (unchanged).** `out/print/2.38c/{01..16}-*.png`: 600 dpi crops,
staff lines drawn in (cut straight from the PDF, no re-render), a green
corner bracket on the exact detected box, one caption line under each
giving OUR decided value and what the print shows it should be. Scripts
(`crop_subjects.py`, `final_crops.py`, `list_subjects.py`,
`dump_verdict.py`, `tip_ink_check.py`, `check_pixels.py`,
`medium_crop.py`, `tight_crop.py`) are throwaway triage, not committed
(CLAUDE.md rule 9).

**Population A (level-0, 19 notes) -- corrected cause table:**

1. **The CV beam-stroke reader stops short of the stem it should reach**
   (8 of 8 re-checked, crops 01-05, 08-10: `glyph/1/0/0/0/10`, `/24`,
   `/28`, `/31`, `/32`, `glyph/1/0/0/3/12`, `glyph/1/1/3/2/1`,
   `glyph/1/1/3/1/11`). Every one of these is a REAL, solidly-inked
   notehead sitting INSIDE a continuous beamed run on the print -- the
   beam bar visibly passes over the notehead's own column -- yet
   `Q.BEAM_STROKE`'s CV rows for that cell cover only PART of the run:
   e.g. `glyph/1/0/0/0/10`'s stem sits at x=1600-1613 (canonical, this
   cell's own units) while the two CV strokes on record end at x1=1013
   and x1=1452 -- a gap of ~150px, 3.2 staff spaces. `yolo_beams` is 0 in
   these cells too -- the DETECTOR never boxed a beam glyph there
   either, so there is no second candidate to fall back on. Crops 08-10
   (formerly called "false notehead") are the SAME cause, re-verified:
   each is a real head inside the same beam run, wrongly decided
   quarter for the identical reason as 01-05. **This is a GATHER gap**
   (the CV line reader's segmentation length), not a connection
   ADJUDICATE can make -- nothing on the record names the right beam
   count for these notes. **Not built, per the brief's own permission
   to stop at diagnosis.**

   2 of 8 originally-eye-checked (crops 06-07, `glyph/1/0/0/0/5`,
   `glyph/1/1/9/7/4`) still look CORRECT on re-check: genuinely isolated
   notes, no beam run nearby.

   9 of 19 remain unverified individually (not cropped this round);
   named, not chased.

**Population B (level >=2 after 2.38b, 6 notes) -- corrected cause table:**

1. **Two overlapping detector boxes for ONE physical flag, each
   independently satisfying `_beam_levels`'s per-box column test** (2 of
   6, crops 12-13: `glyph/1/0/9/3/11`, `glyph/1/1/10/0/8`). Both are
   real, solidly-inked noteheads with a single-flag (eighth-note) stem,
   confirmed by re-crop: `glyph/1/0/9/3/11` -- `flags_attached=0` (the
   detector never boxed a `flag` glyph at all; the flag's own curl was
   boxed 3x as overlapping `beam`-class glyphs, all at x1664-2003, y
   spanning 912-1009 -- one physical mark, three overlapping boxes) --
   decided 32nd (3 beams) where the print shows an eighth (1 beam).
   `glyph/1/1/10/0/8` -- 4 overlapping boxes covering one flag,
   decided 64th (4 beams) where the print shows an eighth.
2. **A real, isolated note wrongly attributed a NEIGHBOURING beamed
   run's strokes** -- now THREE instances, not one (crops 11, 15, 16):
   `glyph/1/0/9/3/3`, `glyph/1/1/3/0/7`, `glyph/1/0/11/3/5`. All three
   are real noteheads with their own up-stem and no flag, standing
   alone with no beam or flag touching them on the print; a separate
   beamed pair starts one or two notes away. Decided 16th/32nd/16th
   respectively; the print says quarter in all three. Manager confirmed
   crop 16 is NOT borderline -- the boxed head's own stem carries
   neither beam nor flag, the beam starts at the NEXT note. **No
   question asked of Sean about crop 16** (per instruction; the wrong
   claim above is corrected, not re-litigated).
3. **Plausibly correct**, ONE remaining (crop 14, `glyph/1/1/3/0/10`):
   see the withdrawn build below -- this one turned out to be the
   control that caught the build's own unsoundness.

**A connection was tried for cause 1 (12, 13) and WITHDRAWN.**
`rhythm._cluster_duplicate_strokes`: group `Q.BEAM_STROKE` rows that
overlap heavily in BOTH x and y into one cluster before `_beam_levels`
counts them, so a physical stroke the detector names twice counts once.
RED-first: 8 new tests in `test_staged_beam_stem_join.py`
(`TestClusterDuplicateStrokes`), 5 of 8 failed against `origin/main`'s
code (`AttributeError`, the function does not exist there), all 8 green
against the fix; the existing 37 tests were unaffected (a stroke with no
y-overlapping sibling is its own singleton cluster, byte-identical to the
un-clustered path). Priced with a SAME-GATHER re-adjudication (`readjudicate.
py`'s own `rebuild()`, not a second full gather -- CLAUDE.md §6b, "base vs
arm on ONE tree"): `glyph/1/0/9/3/11` 3->1, `glyph/1/1/10/0/8` 4->1, both
matching the print (eighth).

**Then it broke a real note, and was withdrawn before commit.**
`glyph/1/1/3/0/10` (crop 14, the ONE population-B member this section
had called "plausibly correct") went from certain=2 (right: a genuine
2-note 16th group, double beam visible on the print) to certain=1 (WRONG)
under the same fix. Its own two counted strokes, `obs:025206`
(x1803-2009, y737-790) and `obs:025211` (x1803-2009, y721-758), overlap
in y by 21px -- the SAME shape (heavy x-overlap, partial y-overlap) the
fix is built to collapse. Measured the actual overlap fraction (of the
smaller box's height) on every pair on hand: the confirmed-BAD duplicate
pairs (12, 13) run 63-100%; this confirmed-GOOD real pair runs 57% --
NO CLEAN GAP, and picking a threshold between 57 and 63 from three data
points would be tuning a rule to the exact cases in hand, not a measured
boundary (rule 7's own warning). **Box overlap in x and y cannot reliably
tell "one stroke boxed twice" from "two real beam levels drawn close
together"** with the evidence this page provides -- a genuine secondary
beam sits close enough to its primary that their detector boxes can
overlap as much as a duplicate detection's do. Reverted before commit
(`rhythm.py` and the test file both restored to `ad5f26af`, `git diff`
clean); nothing shipped. Caught by re-adjudicating the SAME saved gather
(no detector jitter to hide behind) BEFORE trusting the fix -- exactly
the control rule 7 asks for, run in a state where it could fail, and it
did.

**Verdict: nothing built, corrected causes only.** Population A traces
entirely to a GATHER gap (CV beam-stroke reach) -- not this lane's file
to fix. Population B: 2 members (12, 13) have a real, understood
ADJUDICATE-shaped cause (duplicate detector boxes) but no safe connection
could be built from the geometry on hand; 3 members (11, 15, 16) are a
genuine cross-attribution needing a different, unbuilt mechanism (still
short of a verified >=4-note floor with a safe design); 1 member (14) is
real and correct in the CURRENT (unmodified) tree. `staged.check` TOTAL
**245, unchanged** (no code touched, confirmed after revert);
`pytest -m "not slow" tools/omr/tests`: **4030 passed, 3 skipped**,
identical to the pre-session baseline (no code touched).

**Also flagged, not this lane's fix:** the false-notehead claim this
section made and withdrew was never real -- there is currently NO known
`notehead_precision` gap on this page from this lane's own work; that
earlier flag is retracted along with the claim it was based on.

