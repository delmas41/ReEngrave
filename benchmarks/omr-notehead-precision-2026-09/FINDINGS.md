# Litolff p3 dyads: doubled heads, missed heads, and ties (2026-09-30)

DIAGNOSIS ONLY. No file under `tools/` changed by this lane. All numbers
below are read from the whole-movement record
`library/_shared-records/beethoven5-litolff-mvt1-whole-20260930b.record.json`
(page index 3 = pdf idx 3, bars 49-82) via `record_io.load_record`, from the
exported `benchmarks/acceptance/out/beethoven5-litolff/beethoven5-litolff.musicxml`,
and from the source PDF rendered at 600 dpi. Probe scripts:
`probe/dyads-2026-09-30/`. Crops: `out/print/dyads/` (manifests
`manifest-a.json`, `manifest-b.json`, `manifest-d.json`). Record-level
extracts: `out/dyads-*.json`.

WARNING, provenance caveat. The record's `provenance.commit` (`2718c4505`) is
an ancestor of this branch's HEAD and `dirty=False`, so it is a valid
baseline by rule 7/10 -- but it carries `Q.TIE_PAIR` verdicts from
`adjudicate_tie_pair` (ROADMAP 3.2b), which ROADMAP's own row still marks
"not merged". The tree disagrees with that row: `Q.TIE_PAIR` **is** in
`adjudicate.ORDER` (`adjudicate.py:970`) and `export.py` reads it
(`_TIE_PAIR_COUNTED_ELSEWHERE`, `tie_pairing`, `tie_contradictions`). Per
rule 10, the tree wins; ROADMAP's 3.2b/3.2c rows are stale and should be
corrected by whoever owns that lane -- flagged, not fixed here (out of scope
for a diagnosis-only brief).

---

## A. Doubled heads

**Population A** (the brief's own definition): same-class notehead-glyph
pairs in one cell, centres within 1.2 staff spaces vertically, bounding
boxes overlapping horizontally. **53 pairs** on page 3 (474 notehead glyphs
total). All 53 are grouped by `Q.EVENT` as `x_clustered` / `kind=chord` --
EVENT correctly treats every one as simultaneous ink.

2.30 (`notehead_is_a_duplicate_box`) refuses **10 of 53** (8 with reason
`notehead_is_a_duplicate_box` specifically; 2 coincide with an unrelated
refusal on the same box). The other **43 stand** -- both glyphs are
written. Measured why: `NOTEHEAD_DUPLICATE_IOU_MIN` (0.02) is not the
binding constraint (missed pairs' IoU ranges 0.004-0.70, median 0.16, well
above the floor); `NOTEHEAD_DUPLICATE_MAX_DY_STAFF_SPACES` (0.25) is -- the
missed pairs' centre-to-centre `dy` ranges **0.255-1.19 staff spaces**,
always just above or well past the gate, while the 8 the rule catches sit
at `dy` 0.005-0.38 (one outlier attribution artefact excluded, see script
comments).

**A KEY MECHANISM, newly confirmed from `Q.PITCH`:** of the 43 missed
pairs, only **2 round to the SAME written pitch** (Sean's "shows as one" --
two identical noteheads stacked are visually indistinguishable, so the bug
is invisible even though the chord holds a doubled note). The other **41
round to DIFFERENT, adjacent pitches** -- this is Sean's other observation,
"a single note would often print 2 notes... a second apart": the SAME
physical ink, boxed twice, fits two slightly different centroids that
`restate_pitch` (EVALUATE) rounds to two different staff positions, so
EXPORT writes a real but spurious second note next to the true one.

### Judged sample (20 of 53, print-checked at 600 dpi, ink-% measured before judging)

| bucket (n sampled) | judged one-head-boxed-twice | judged real chord (2+ distinct notes) | judged NOT simultaneous (false lead) |
|---|---|---|---|
| overlap+same-side, 2.30-caught (5) | 5/5 | 0 | 0 |
| overlap+same-side, stands (8) | 4/8 (A06,A09,A11,A13) | 4/8 (A07,A08,A10,A12 -- 3rds/4ths, correctly same-side, correctly left alone) | 0 |
| no-overlap, same-side (4, A14-17) | 0 | 0 | 3/3 viewed (A14,A15,A16 -- a beamed run of distinct heads; `Q.EVENT` already says `different_events`) |
| no-overlap, opposite-side (3, A18-20) | 0 | 0 | 3/3 (repeated-note / tremolo figure, each note its own stem; `different_events`) |

So: A01-A13 (13/13 judged) = Population A proper (overlap required, the
brief's own scope). Split **9 confirmed duplicate : 4 confirmed real
chord**. 2.30 is precise on what it catches (5/5 right) but its recall
inside its own target population is ~9/13 by this sample (scaling: ~30 of
the 53 same mechanism likely still stand, extrapolating the 4/8 "stands"
rate to all 43 -- an estimate, not a recount). A14-20 (7/20) fall OUTSIDE
population A's own `Q.EVENT` grouping in the sense that matters: they were
only reached by widening the search to test the manager's stem-side
question (dx up to 1.6 head-widths, overlap not required) and every one
turned out to be `different_events` -- sequential notes, not candidates for
this population at all. Full crosstab and all 113 extended pairs:
`out/dyads-pairs-a-extended.json`.

### The manager's question: same-side vs opposite-side of the stem

Column added to the pair table (`out/dyads-pairs-a.json`,
`out/dyads-pairs-a-extended.json`): each head's canonical-frame centre x
compared to the nearest covering `Q.STEM` box's centre x, in the SAME cell
canonical frame (stems have no page-frame row, so this cannot be done in
page pixels without first fitting a per-cell canonical to page affine from
the cell's own `Q.GLYPH_BOX` rows -- done in `crop_pairs.py` for the drawn
purple stem boxes, not needed for the numeric test itself).

**Result: 100% same-side within Population A proper (53/53: 43 with a
stem read, 10 `no_stem_in_cell`; zero opposite).** This is a clean split
for the FIRST half of Sean's convention -- every pair that is literally one
physical mark boxed twice is on one side of its own stem, because it IS
that stem's own ink read twice. But it is **not evidence for the SECOND
half** (a real second sits opposite sides), because:

- The 4 confirmed real-chord pairs in the SAME judged sample (A07/A08/A10/
  A12, position gap ~2-3 units = a 3rd/4th) are ALSO same-side -- correctly
  so, per standard engraving (only an adjacent 2nd is offset; a 3rd or
  wider stacks in line). So same-side alone cannot separate "duplicate"
  from "real chord" within Population A -- both classes read the same way.
  The discriminator that DOES work within A is the one already used (IoU +
  centre distance), just under-gated on `dy`.
- Broadening the search (`analyze_real_chords.py`, every `Q.EVENT`
  `kind=chord` pair regardless of overlap, 228 chord-member pairs total) to
  hunt for an actual single-stem SECOND: **zero found.** The only
  "opposite side" cases anywhere in this analysis (49 of 113 extended
  pairs, all no-overlap) were confirmed by crop and by `Q.EVENT` to be
  SEQUENTIAL notes (repeated-note/tremolo figures, a beamed run), each
  carrying its OWN stem -- "opposite side" there is an artefact of the
  nearest-stem heuristic picking a different neighbour stem for each note,
  not a real interval signal. The few wide-interval (5-8 position-unit,
  more-than-an-octave) same-event chord members that also read "opposite"
  (6 of 168) show the identical artefact (no `stem_covers=True` match at
  that distance).

**So: NOT CONFIRMED.** The rule is a plausible, standard-notation-consistent
convention, but this page's judged sample contains no positive example of a
genuine same-stem second surviving as two boxes -- real close-interval
dyads on this MERGING plate appear to collapse into the duplicate-box
population (A above) rather than surviving as two offset boxes at all. A
later build lane relying on "opposite side => real second" should know the
rule is untested here, not refuted -- just never observed.

**Failure modes, named as asked:**
- No stem read: 10/53 in Population A proper, 19-22/113 in the extended
  set (page 3 has 128 `Q.STEM` abstentions of 371+128 cell-attempts,
  `reason=no_line_accepted`).
- Stems in both directions (divisi): not observed in the judged sample;
  cannot report on it.
- Whole notes: not observed in the judged sample (this page's candidates
  are all Half/Black classes); cannot report on it.
- Wrong-stem attribution for sequential notes: the dominant failure mode
  actually found (above) -- not one the manager named, but the one that
  would burn a lane that trusted "opposite => real second" without first
  gating on `Q.EVENT` simultaneity.
- `tools/omr/conventions.py` (114 entries) has NO entry for a
  same-side/opposite-side stem rule. Not added here, per instruction.

---

## B. Missed dyads (one box hiding two heads)

Proxy used (the brief's own ask, approximated): single notehead glyphs
whose OWN `Q.GLYPH_BOX` height is an outlier vs same-class boxes on this
page (median 1.19-1.46 staff spaces depending on class; threshold set at
1.65 sp). **32 candidates** (`out/dyads-pop-b.json`).

**Judged sample: 20 of 32, crop + row-by-row ink profile measured
(`out/print/dyads/B*.png`, `manifest-b.json`).** Of the ones actually
opened and read (11 -- B01-B11): **zero confirmed two-merged-heads.** Every
viewed case was one of:
- a single black notehead whose box also captured attached stem ink
  (B01 h=3.18sp, B02 h=2.80sp -- the box is tall because it spans head plus
  stem, not two heads);
- a single, naturally oblique/diagonal half-note head shape at this
  plate's engraving angle (B03, B07, and most of the `noteheadHalf*`
  entries at 1.65-1.85 sp -- this class's own median is already 1.3-1.5 sp,
  so the "outlier" band here is mostly normal variance, not a signal);
- one outright false detection: B11 (`too_narrow`, refused) is a bare stem
  segment between two REAL neighbouring heads, not a head at all.

**Conclusion: this proxy did not find a real missed-dyad on this page.**
That is a negative result about the PROXY, not a claim that no such case
exists -- box height is confounded by stem-inclusion and by a class's own
natural elongation, and the brief's literal ask (connected ink extent along
the stem, measured on `image_no_staff` after erasure) needs the no-staff
raster the gather used internally, which is not persisted in the record and
would need a fresh gather to recover (`Q.INK` per CLAUDE.md's ink finding is
gathered but is a different quantity, read by nothing downstream). Not run,
per "build, don't burn runs" -- flagged as the open next step rather than
guessed at.

---

## C. Stage table (where doubled/missed notes are lost or created)

| mechanism | stage | evidence |
|---|---|---|
| detector fires two overlapping same-class boxes on one physical mark | GATHER / detector | root cause for all of population A; not a STAGED-stage fault, a detector-precision fact (CLAUDE.md section 9's "the one thing no stage can repair") |
| `notehead_is_a_duplicate_box` catches the tight cases, misses the wider-offset ones | ADJUDICATE (2.30, `notehead_precision.py`) | measured above: `dy` gate (0.25 sp) is the binding, too-tight constant; IoU floor is not |
| `restate_pitch` independently rounds each surviving duplicate's centroid | EVALUATE | this is where "shows as one" (same rounded pitch) vs "prints a spurious second" (different rounded pitch) is DECIDED, not a new loss -- it is applying its own rule correctly to bad GATHER/ADJUDICATE input |
| `Q.EVENT`'s `x_clustered` chord grouping | EVALUATE (via adjudicate order) | correctly groups every duplicate pair as one simultaneity; not implicated in the bug, a necessary-but-not-sufficient precondition for 2.30 to even apply |
| EXPORT | EXPORT | writes whatever ADJUDICATE left standing; no additional duplication or loss mechanism found here for population A |
| population B (a possible detector/EXPORT merge of two heads into one written note) | not confirmed | the tried proxy (box height) found no positive case on this page; genuinely open |

---

## D. Ties

Page 3, `arc_kind` verdicts: **135 of 251** arc glyphs classified `tie`
(rest `slur`, 116). Clustering overlapping `Q.ARC_BOX` page boxes (IoU>0.05,
same physical ink read more than once) gives **99 unique tie-classified ink
marks**. `Q.TIE_PAIR` resolves these to **19 unique NAMED pairings**
(`paired`); the rest abstain (`spans_a_whole_bar` 20, `no_start_head` 19,
`no_head_near_the_arc` 17, `no_pair_at_one_position` 16, `no_stop_head` 9,
`enters_from_previous_system` 7, `runs_off_the_system` 2) or narrow
(`more_than_one_pair` 10). All 19 named pairings are confirmed `tie`-kind,
not `slur` -- the kind gate holds.

**Exported MusicXML, bars 49-82 (all 12 parts): 7 `<tie type="start">`, 4
`<tie type="stop">`.** A start-without-stop pair means at least one tie's
stop head or its bar was held out downstream (matches ROADMAP 2.19's own
note that this page has no printed meter and is heavily bar-held-out, and
3.2c's still-open "drop both ends of a tie when either end's bar is held
out"). So of the record's own 19 named ties, only ~7 survive to the file --
a >60% export-side loss, on top of the 99 to 19 ADJUDICATE-side narrowing.

**Print check (10 of 99 clusters sampled, `out/print/dyads/D*.png`,
`manifest-d.json`):** only **1 of 10** (D05) shows the isolated-arc shape of
a genuine tie -- two single, non-beamed noteheads at the same pitch joined
by one short curve, no repeating pattern. The other sampled clusters (D04,
D06, D08, and most of the rest) show a curve repeated under or over EVERY
beamed note-pair across an entire passage -- the shape and repetition rate
of a bowing/phrase slur, not a tie. This is consistent with Sean's "ties
are almost nonexistent" (DECISIONS 2026-09-30): the `arc_kind` classifier's
135/99 tie-shaped detections on this page are very likely dominated by slur
or bowing-articulation ink being read as `tie`, not by real ties.
CONVENTION ASSUMED / NOT CONFIRMED: I did not verify pitch-equality across
each sampled arc's two flanking heads (the print-only read cannot
distinguish a tie from a same-pitch slur without it), so this is a strong
visual impression from a 10-of-99 sample, not a settled count -- a next
lane should cross the arc_kind population against `Q.PITCH` agreement at
both ends before trusting 99, or 19, or 135 as "how many ties print here".

**Printed-tie count on the page itself**: not independently hand-counted
across all 19 staves x 2 systems (out of budget for this lane) -- the
99/19/135 figures above are the record's own candidate counts, offered as
the closest measurement made, not a manual page census. Flagged as NOT DONE
rather than guessed.

---

## Crops and files

- `out/print/dyads/A01..A20-*.png` -- population A judged sample, each
  labelled with class, `dy`, overlap/no-overlap, stem-side, refused/stands,
  and per-box ink-%; red = first glyph in the pair, green = second, blue =
  staff lines, purple = `Q.STEM` box(es) in that cell (page-frame, fit from
  a per-cell canonical to page affine -- see `crop_pairs.py`).
- `out/print/dyads/B01..B20-*.png` -- population B candidates, red = the
  single box, blue = staff lines; label carries box height in staff spaces
  and the measured ink-%.
- `out/print/dyads/D01..D10-tie-cluster.png` -- sampled tie-ink clusters,
  red = each clustered arc box.
- `out/print/dyads/manifest-{a,b,d}.json` -- machine-readable version of
  the same, including every measured ink-% before any verdict was written
  (rule from `feedback_print_check_every_lane`: measure ink numerically
  before judging, viewed at a zoom where one head is >=60px wide -- enforced
  by `crop_pairs.py`/`crop_single.py`'s upscaling to a 70px head-width
  floor).
- `probe/dyads-2026-09-30/*.py` -- every script that produced the numbers
  above, re-runnable against the same record.
- `out/dyads-pairs-a.json`, `out/dyads-pairs-a-extended.json`,
  `out/dyads-chord-pairs.json`, `out/dyads-pop-b.json` -- the full
  record-level extracts behind every count in this section.
