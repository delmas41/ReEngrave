# Noteheads — the anchor family

One section per symbol, five questions each, in Sean's numbering. Written
2026-09-20 off `origin/claude/integration-2026-09-18` (`4215c810`). Q4 is read
out of `tools/omr/staged/` and the committed funnel records, never out of prose.

**Two records supply almost every figure here**, and they disagree about
everything, so they are never pooled:

| | Litolff Beethoven 5, pp.1-4 | Breitkopf Brahms 1, pp.0-3 |
|---|--:|--:|
| notehead boxes | 2,347 | 3,337 |
| `<note>` written | 965 (41%) | 2,513 (75%) |
| dominant loss | identity (988) | `duration_narrowed` (537) |
| raster | bitonal, 600 dpi is native | 531 dpi native |
| boxes the print says are NOT noteheads | 15.6% of a 90-tile sample | **35.6%** |

Source: `benchmarks/omr-stage-trace-2026-09/out/funnel-note-litolff.txt` and
`funnel-note-breitkopf.txt`; `benchmarks/omr-stem-crop-pass-2026-09/FINDINGS.md` §2, §7.

**A probe was used**, once, and it is named where it appears: a count of
hand-labelled boxes per class across the 14 catalog versions
`data/user-labeled/catalog-versions.txt` admits (591 label files, 3,871 boxes).
Nothing was transcribed, exported or scored.

---

## Prior work this starts from, and where it is cited

Four documents already answer part of these questions for this family. They are
cited in place rather than re-derived; **§"Where this disagrees" at the end
lists the four places this dossier does not agree with them.**

| document | what it already settles | where it appears below |
|---|---|---|
| `docs/position-grammar-confusables-2026-09-04.md` §2 | Sean's Q1 alphabet, by MARK: **BOWL/BLOB** covers the hollow heads, **DOT** the augmentation dot, **HORIZONTAL STROKE** the ledger line, **VERTICAL STROKE** the barline. Its principle — *identity is assigned by a grammar that knows the lattice and the anchors, never by staring harder at the ink* — governs every Q1 here | each §1 opens from its entry |
| `benchmarks/omr-family-positions-2026-09/FINDINGS.md` + `staged/positions.py` + `staged/capture.py` | the per-family POSITION fact. **Eleven families got one on 2026-09-17; `note` is NOT one of them, because it already had the exemplar.** Ten producers, no consumers, `OMR_FAMILY_POSITIONS` default OFF | each §3 |
| `tools/omr/staged/ASSUMPTIONS.md` | `A-OWN-1` (tier order; confidence declared and unweighted), `A-OWN-2` (the range veto reads position + clef, never a resolved pitch), `A-DUR-1` (duration is a VERDICT composed of measurements), `A-EVAL-2` (an abstained clef produces NO pitches), `A-INK-3/4` (GATHER is lossless; a factor contributes, it does not decide) | §4 and §5 |
| `docs/exploration-what-is-on-the-page-2026-09-09.md` | **B.5** *no stem means a whole note* — absence-of-stem as positive duration evidence, *"only worth it if `adjudicate_duration` declares it"*; **B.7** proportional spacing, the one raster measurement nobody takes and the only duration signal independent of stem, beam and class; **C1** cross-staff simultaneity | Whole §1, §5 |

⚠️ **Sean's own standing caution on position, 2026-09-17, applies to everything
in each §3**: *"position is an option for helping us determine something but
will rarely be a clear rule that determines by itself… Quick rules will give us
quick results that could be poor."*
(`benchmarks/omr-family-positions-2026-09/FINDINGS.md` §preamble.)

⚠️ **`capture.py --check` grades `note` `shape: yes / position: MEASURED /
location: composes`, and `Q.NOTEHEAD_STAFF_POSITION` is labelled THE EXEMPLAR
— one of only THREE staff-grid position quantities, and the only one of the
three whose consumer is a decision that changes a value** (`restate_pitch`).
The other two are the clef's and the key signature's. Every other family's
position row is `position_declared_but_unread`.
(MEASURED HERE, run this session: `python3 -m tools.omr.staged.capture --check`.)

---

## The three facts that govern the whole family

**(a) The subject is the detector's box, not the ink.** `gather.py:330` files
one row per detection and `gather.py:373` files the detector's class name with
`log.observe` — as a fact about the page. Routing downstream is BY CLASS. So a
barline called `noteheadBlackInSpace` enters the notehead family and cannot
leave it; ink the detector missed has no address at all and is outside the
domain of every decision in the system. Of 28 adjudicators exactly one ever
questions the class, and it asks only *is this a whole rest*.
(MEASURED HERE + ASSERTED: `docs/breakthrough-2026-09-18-the-unit-of-enquiry.md`
§1-§3; the 28/1 count is `python3 -m tools.omr.staged.inventory`.)

**(b) The three legacy hygiene filters do not run on the staged path.**
`_drop_clipped_notehead_fragments`, `_drop_unladdered_noteheads` and
`_dedupe_cross_staff_detections` all live in `tools/omr/transcribe.py` and are
called from nowhere else (`grep -rn` over `tools/`). `staged/gather.py:323`
calls `detector.detect(...)` fresh. So the edge-fragment rule, the
no-ledger-rung rule and the cross-staff delete are LEGACY ONLY; the staged path
re-answers the third as `Q.GLYPH_OWNER` and does not answer the other two at all.
(MEASURED HERE, by grep, n = whole tree.)

**(c) The staged path asks the detector a different question.**
`gather.py:323` passes neither `iou_threshold` nor `agnostic_nms`, so it takes
`0.7` / `False` where `transcribe()` passes `0.5` / `True`. Class-wise NMS never
compares `noteheadHalfInSpace` with `noteheadBlackInSpace`, so one notehead can
survive as three rows at IoU 0.91-0.96 with three different duration verdicts.
**284 same-cell notehead pairs** on Litolff pp.1-4. Recorded at the site and
deliberately not changed — it is a GATHER change and needs two re-gathers to
price. (MEASURED HERE: `gather.py:305-322`;
`benchmarks/omr-staged-dedupe-2026-09/FINDINGS.md` §6.1, table at §2(ii).)

---

## `noteheadBlackOnLine` / `noteheadBlackInSpace`

A small solid oval, about one staff space tall and a little wider. The two
classes are one shape; the suffix is a claim about where it stands. Produced by
the YOLO detector only — there is no CV notehead reader anywhere in the tree.

### 1. What sets it apart — and what it is confused with

**The alphabet's entry is BOWL / BLOB** (`docs/position-grammar-confusables-2026-09-04.md`
§2): *the bowl of a* legato *"g", the lower bowl of a 6/8's "8", and a clipped
neighbour-staff head are all notehead-shaped*, with two shipped discriminators —
the one-staff-space height and the missing ledger rung. **This section AGREES
with both, ADDS two confusables that entry does not name, and DISAGREES about
the word "shipped".** See §"Where this disagrees" at the end.

The distinguishing facts, in the order the repo has evidence for them:

| fact | number | grade |
|---|---|---|
| **HEIGHT ≈ one staff space** | Bravura 1.000 sp; interior heads measure 0.61-1.12 sp, only 3 of 594 under 0.80 | `[C1 + L3]` MEASURED HERE |
| **WIDTH > height** | p5-p95 **1.26-1.78 sp** on Litolff `decided`, 1.26-1.58 on Breitkopf; a barline is 0.40-0.45 sp | MEASURED HERE, n = 3,234 |
| **it is SOLID** | ink fill ≥0.9 on 129 of 159 boxes on a Litolff page | MEASURED HERE, and this is the fact that fails on scans — see the Half section |
| **it stands on the half-space lattice** | ON-line ink overlap median 0.022 of head height (n=430), IN-space 0.374 (n=406), empty interval 0.15-0.29 | `[C2]` MEASURED HERE |

**Confused with, concretely, each one adjudicated against the print:**

* **A BARLINE.** The largest single confusion. On Breitkopf, `too TALL` is 476
  of 3,337 notehead boxes (14.3%) and the crop pass read **12 of 12 sampled as
  not a notehead**, every one a box 0.40-0.45 spaces wide on a vertical rule.
  459 of those 476 are under 1.0 staff spaces wide.
  (`benchmarks/omr-stem-crop-pass-2026-09/FINDINGS.md` §2;
  `benchmarks/omr-notehead-width-2026-09/FINDINGS.md` §2, §5.)
* **THE NEIGHBOURING STAFF'S INK through the 4-6 space cell padding.** A measure
  cell is the staff plus 4 or 6 staff spaces of air, so the same ink is detected
  in two staves' cells. 636 overlapping cross-staff contest groups on Litolff
  pp.1-4. Separately, 14 of 25 print-adjudicated phantom notes stand OUTSIDE the
  staff (steps 10-17) in bars whose print holds one whole rest and nothing else.
  (`benchmarks/omr-staged-dedupe-2026-09/FINDINGS.md` §3;
  `benchmarks/omr-phantom-notes-2026-09/FINDINGS.md` §4.)
* **A printed LETTER.** A capital **B** (2.18 sp wide), the `e` of *cresc*
  (1.10), three script `ff` letterforms, the bowl of a *legato* `g`.
  (MEASURED HERE, 22 print-confirmed misses in
  `benchmarks/omr-notehead-width-2026-09/FINDINGS.md` §6.)
* **THE CELL'S OWN CROP EDGE.** A sliver of the staff above is exactly the shape
  of a flat oval. Crop fragments measure 0.29-0.56 spaces tall; genuine heads
  touching an edge measure 0.77-0.99. (`[C1 + L3]`, MEASURED HERE, n = 594.)
* **Itself, three times over** — the same-cell NMS triple at (c) above.

⚠️ **The reverse confusion is the one that costs most: `arpeggiato` fires 98 and
86 times on two pages** at median 56×388 px and confidence 0.39, against
noteheads' 146×131 at 0.67. A 1:7 tall thin box at half a notehead's confidence
is a stem or a barline. Neither work prints ninety arpeggios a page.
(MEASURED HERE: `benchmarks/omr-staged-gather-2026-09/FINDINGS.md` §"derived
check"; 377 on the four-page Litolff record,
`benchmarks/omr-cleanup-count-2026-09/FINDINGS.md` §3d.)

**The on-line / in-space suffix is a POSITION claim inside a SHAPE class, and
nothing in either pipeline reads it as position.** `gather_notehead_positions`
measures the staff position geometrically from the cell's own line grid and
ignores the suffix entirely (`gather.py:444-450`). The suffix is read in exactly
two places: as a prefix that gets stripped in `_HEAD_BEATS`, and as the
same-class gate on the cross-staff contest. That second one has a measured cost:
**37 cross-staff notehead pairs at IoU ≥ 0.5 (47 at IoU 0.3) differ ONLY in the
`InSpace`/`OnLine` suffix and are therefore refused a contest** — which is the
one thing two staves' grids MUST disagree about for ink in the gap between them.
(MEASURED HERE:
`benchmarks/omr-phantom-notes-2026-09/FINDINGS_2026-09-15_STALENESS.md` §"three
candidate repairs", item 1.)

### 2. Best method: YOLO / CV / other

**YOLO, and it is the best-read thing in the project on clean ink.** Reading F1
**0.999** over 856 truth noteheads on eleven engraved works, precision 0.998,
recall 1.000, and the score does not move at all when the centre tolerance is
widened from 0.5 to 2.0 staff spaces — so they are found AND precisely placed.
(MEASURED HERE: `benchmarks/omr-reading-vs-reproduction-2026-09/FINDINGS.md` §2.)

On a scan the recall is still good (Brahms p2 frame control 0.980) and the fault
is **precision**. That is the whole of Sean's question and §5 answers it.

**What CV adds, and what it cannot.** A width floor at <1.0 staff spaces is the
cheapest mechanical *that is not a notehead*: over 255 blind-adjudicated boxes it
costs **ZERO of 103 print-confirmed noteheads on both plates** and catches
**41 of 63** print-confirmed non-noteheads (Litolff 9/19, Breitkopf 32/44). It
was measured and **deliberately not proposed** — it is a GATHER change. The 22 it
misses are the RIGHT width and the wrong height, and a height floor is refused
for a measured reason: the shortest print-CONFIRMED noteheads are **0.340 and
0.345 spaces tall**, so an unrestricted `h < 0.6` floor would delete real heads
on both plates. (MEASURED HERE:
`benchmarks/omr-notehead-width-2026-09/FINDINGS.md` §3, §6, §7.)

⚠️ **A width read off the detector's own box is not a second witness.** The box
and the class are one assertion by one reader on one crop, so the width can catch
the detector contradicting itself and can never corroborate it. The measurement
that would be independent is of the **INK**, and that is `Q.INK` — default-ON,
one row per connected piece of a cell's ink, in both frames, **read by nothing**
in any adjudicator, consequence, inference or the exporter (verified by grep).
(MEASURED HERE + ASSERTED:
`benchmarks/omr-notehead-width-2026-09/FINDINGS.md` §0, §8.)

**Training evidence** (probe, this session, over the 14 admitted catalog
versions — 591 label files, 3,871 boxes): `noteheadBlackOnLine` **700**,
`noteheadBlackInSpace` **609**. The two best-covered classes in the whole corpus.

### 3. Where on the page the deciding information lives

**The position fact already exists and is already consumed**, which is unique in
this pipeline: `capture.py` grades `note` `position: MEASURED` and calls
`Q.NOTEHEAD_STAFF_POSITION` *THE EXEMPLAR*, consumed by `consequences.restate_pitch`
together with the clef. The notehead family is therefore **absent from the eleven
that `positions.py` had to be written for** — it is the model those ten were
built against, in the same STEP frame (top line 0.0, bottom line 8.0).
(`benchmarks/omr-family-positions-2026-09/FINDINGS.md` §1, §1a.)

⚠️ And Sean's caution cuts here too: the position tells us WHERE, never WHAT.
Nothing in the pipeline uses a notehead's position to test whether it is a
notehead — the one rule that could (`notehead_is_a_whole_rest`) uses it only to
ask a different question.

* **Inside the box** — fill, aspect, height in staff spaces. This is where the
  answer to *is it an oval* lives, and it is the only place the detector looks.
* **The staff's own five lines**, for the position. `Q.NOTEHEAD_STAFF_POSITION`
  is `(y_center − top_y) / half_step` off the CELL's own measured lines. The
  cell grid is slid onto the ink beneath it (`OMR_CELL_LINE_TRACE`, default ON)
  because a scanned staff tilts and bows **8-17 page px** across its width.
* **The surrounding ink, outside the box** — and this is where the repo has
  repeatedly found the answer it could not get from inside. The eight boxes that
  are the two round counters of a printed time-signature **8** have nothing
  inside them that disagrees; only the digit around them does. *A crop centred
  on a head cannot tell you the head is a NUMERAL — use a full-width strip.*
  (MEASURED HERE: `benchmarks/omr-stem-crop-pass-2026-09/FINDINGS.md` §5.)
* **The cell's crop boundary** — a detection flush against it is the neighbour's.
* **The other staves of the system**, for ownership: the ledger ladder, the
  instrument's written range, and last, distance.

### 4. Stage by stage

**GATHER** (`gather.py`) writes, per notehead detection:
`Q.GLYPH_BOX` (class + canonical box + `bbox_page_px`), `Q.GLYPH_CONF`,
`Q.NOTEHEAD_CLASS`, `Q.NOTEHEAD_STAFF_POSITION` (scoreless — a ruler reading is
not a guess), and per cell `Q.CELL_STAFF_SPACE` and `Q.CELL_BOX`. For a
CONTESTED glyph only, `Q.GLYPH_BAND_DISTANCE` per candidate staff (carrying
`position_in_candidate`) and, where the head is outside a candidate's band,
`Q.GLYPH_LADDER`.

**ADJUDICATE** — four decisions take a notehead as their subject:

| decision | Litolff, 2,347 heads | Breitkopf, 3,337 heads |
|---|---|---|
| `duration` | 1,990 decided / **357 narrowed** | 2,795 / **542 narrowed** |
| `stem_direction` | 1,443 decided / **904 abstained** (793 `no_stem`, 111 `stems_disagree`) | 1,791 / **1,546 abstained** |
| `notehead_is_a_whole_rest` | 2,347 decided; **True on 25** | 3,337 decided; **True on 12** |
| `glyph_owner` (contested only) | 464 rows: distance 331, ladder 107, range_veto 20, **6 abstain `tied`** | 617 rows: distance 338, ladder 244, range_veto 35, 0 abstain |

(All from the two committed funnel files.)

The assumptions those four decisions run under are declared, not implicit:
**`A-DUR-1`** — a duration is a VERDICT composed from measurements, so the
notehead CLASS is an input to it and never the answer itself;
**`A-OWN-1`** — ladder, then the range veto, then distance, with
`Q.GLYPH_CONF` *declared in `wants` and must not be weighted* (P(winner conf >
loser conf) = **0.545** against a 0.500 null over 4,521 contested pairs, and a
`|Δconf| > 0` tie-break would overturn distance on **45.5%** of contests);
**`A-OWN-2`** — the range veto reads POSITION + CLEF and never a resolved
pitch, so the basis records the loop if anyone ever closes it.
(`tools/omr/staged/ASSUMPTIONS.md` A-DUR-1, A-OWN-1, A-OWN-2.)

**EVALUATE** — `restate_pitch` (`clef` → `pitch`): 2,113 first answers on
Litolff; `move_glyph` (`glyph_owner` → `pitch`) restates **214** as `reowned`,
and supersedes rather than deletes. `reconcile_duration` changes **50** duration
values and collapses 5 narrowings. This is the stage correcting ADJUDICATE.

**INFER** — two rules, both targeting `Q.DURATION`, both `sideways=True`,
reading `Q.ONSET_COLUMN` / `Q.EVENT` / `Q.DURATION` / `Q.GLYPH_BOX`. They may
only collapse a NARROWING to one of that reader's own candidates.
**`OMR_INFER` is default OFF**, and its exact population is Breitkopf's dominant
loss (537). (MEASURED HERE: `inferences.py:287, :375`; `infer.py:125`.)

**EXPORT** — `_place_notes` walks `Q.GLYPH_BOX` and refuses, counted by reason:

```
Litolff:   written 965 | staff_not_identified 783 · duration_narrowed 335 ·
           no_pitch 205 · owned_by_another_staff 173 · ink_is_a_whole_rest 25
Breitkopf: written 2,513 | duration_narrowed 537 · owned_by_another_staff 293 ·
           written_value_fits_no_note 30 · ink_is_a_whole_rest 12
```

The balance is an EQUALITY the exporter raises on, and it holds on both.
⚠️ Three of those reasons pool noteheads with rests, so no notes-only partition
closes. ⚠️ `staff_not_identified` is `OMR_HOLD_OUT_UNIDENTIFIED` working as
designed, so **41% is not a measure of how well that page was read**.

⚠️ **Nothing questions `Q.NOTEHEAD_CLASS` itself.** `_head_class` takes the
argmax by score over `ev.rows(Q.NOTEHEAD_CLASS)` at glyph scope — one reader
files it, so the argmax has one candidate and is inert. `Q.GLYPH_CONF` is
declared by `glyph_owner` and **read by nothing anywhere** (grep over
`tools/omr/staged/`): a notehead at 0.26 and one at 0.98 are equally true.

### 5. Abstain or best-guess — and what leans on this mark's certainty

**(a) Can it abstain, and does it?**

*Yes* for everything a notehead is used FOR, and *no* for whether it is one.

* `duration` **narrows** rather than deciding on 357 / 542 heads, and the
  exporter refuses to argmax the candidates even though they carry `support`.
* `stem_direction` abstains 904 / 1,546.
* `glyph_owner` abstains `tied` when two candidates score equal — *two equal-cost
  mappings that disagree carry literally zero information.*
* `restate_pitch` produces **no pitch at all** for a staff whose clef abstained,
  and the exporter refuses to write treble as a default — **`A-EVAL-2`**, and it
  is the assumption that turns 205 Litolff heads into a counted `no_pitch`
  rather than into 205 wrong pitches.
* **But `is this ink a notehead` has no decision, no abstention, and no place to
  put one.** The answer is the subject's name. `notehead_is_a_whole_rest` is the
  single narrow exception, and it can only ever say *whole rest*, never *barline*
  or *letter*. (MEASURED HERE by inventory + grep; ASSERTED as a framing in
  `docs/breakthrough-2026-09-18-the-unit-of-enquiry.md` §5.)

**(b) What leans on this, and Sean's question: is a confidently WRONG anchor a
different risk from one that MISSES?**

**Yes, and the repo has both measured. They fail in opposite directions and only
one of them is visible.**

A **MISSING** notehead removes a subject. Everything anchored on it goes silent
and is COUNTED:

* **550 of 721 merged arcs (76.3%) bind fewer than two noteheads and are
  refused**, and **108 of those sit in bars where the detector produced NO
  notehead at all** — one bar's print shows a slur over six legible heads and the
  record's whole content is a tie, a spurious `restWhole`, a flat, a staff and a
  ledger line. (MEASURED HERE: `benchmarks/omr-arc-recovery-2026-09/FINDINGS.md`.)
* A dot with no head to its left is left unattached rather than given away.
* A stem with no head at either end is, on the stem thread's own rule, *not a
  stem* — and that half of the rule is EVALUATE-shaped because it is forced.

A **WRONG** notehead creates a subject, and everything anchored on it attaches
confidently to nothing:

* The beam-mate tier **gave a stem direction to a DOT** — 2 of 26 standoff heads.
* `no stem means a whole note` was tested on 31 heads the record calls WHOLE and
  still gives a direction: of 17 adjudicated, **16 are CLASS-false** — eight are
  the two round counters of a printed `8`, five are the white gap between two
  thick staff lines. The convention was neither confirmed nor contradicted,
  because the population was not whole notes.
* The width floor leaves **22 of 63** print-confirmed non-noteheads standing, and
  **13 of the 22 are `noteheadWhole*`** — right width, wrong height, invisible to
  the one cheap test.
(MEASURED HERE: `benchmarks/omr-stem-crop-pass-2026-09/FINDINGS.md` §1, §5;
`benchmarks/omr-notehead-width-2026-09/FINDINGS.md` §3, §6.)

**So the asymmetry is: a missing anchor produces a GAP that every consumer
already counts; a wrong anchor produces a CONSEQUENCE that no consumer can
refuse, because nothing downstream is permitted to doubt the class.** A wrong
notehead does not merely fail — it recruits a stem, an arc end, a dot and a
voice.

**The independence check, which is the part that decides whether noteheads
should anchor the sweep.** Ask of the anchor: *does it fail on the same pages as
the thing I am anchoring?*

* **For the heads we read correctly, the answer is favourable and measured.** On
  Brahms p2 notehead recall is **0.980** while **half the stems are missing**, so
  on that page the two demonstrably do not fail together.
  (`docs/plan-2026-09-18-what-distinguishes-each-mark.md` §9.5.)
* **For the heads we get wrong, they fail on exactly the same subjects, and that
  is the qualifier.** On Breitkopf `no_stem` is 1,529 of 3,337 heads; **576 of
  those boxes are under one staff space wide, and 459 of the 576 (79.7%) are in
  the `too TALL` bucket** — which the print reads 12 of 12 as *not a notehead*.
  The population with no stem and the population that is not a notehead are the
  same population. So *notehead certainty is independent of stem certainty* holds
  where the anchor is right and **fails precisely on the subjects an anchor would
  be spent on**. (MEASURED HERE:
  `benchmarks/omr-notehead-width-2026-09/FINDINGS.md` §2, §5;
  `benchmarks/omr-stem-crop-pass-2026-09/FINDINGS.md` §2.)

⚠️ And the adjudicating eye is not independent of the attachment reader: both
measure ink beside the head. Every print figure above is properly *the ink beside
the head behaves as the convention says.* One adjudicator, no inter-rater figure.

---

## `noteheadHalfOnLine` / `noteheadHalfInSpace`

The same oval with a white counter. Detector only.

### 1. What sets it apart — and what it is confused with

**The alphabet's BOWL/BLOB entry is about this symbol above all** — it is the
"bowl" in the name. It lists what a hollow head is confused WITH. It does not
cover the direction that actually costs most here, which is a hollow head
confused with a SOLID one because the plate closed its counter; that is below,
and it is an ADDITION to the entry rather than a disagreement with it.

**From a black head: the counter, and nothing else** — same height, and
measured on both plates the WIDTH does not separate them either (Litolff Half
1.61 sp median against Black 1.46; Breitkopf 1.56 against 1.40 — Half is
slightly wider, but the bands overlap completely). So the half note is
distinguished by an INTERIOR feature, which is the one thing a bitonal scan
destroys. (MEASURED HERE:
`benchmarks/omr-notehead-width-2026-09/FINDINGS.md` §6.)

⚠️⚠️ **THE COUNTER CLOSES ON A SCAN, AND THIS IS THE SINGLE LARGEST MEASURED
READING FAULT IN THE FAMILY.** On Beethoven 5 p.1 the page prints **68 half
notes** and the detector reported **9**. Not misclassified — not detected. At
600 dpi bitonal (which is that plate's native resolution) the counter has closed
to a thin diagonal sliver inside an otherwise solid head, and a detector trained
on clean engraving has no reason to call it hollow. **Twenty of twenty-six
duration errors on that page are a half note read as something shorter.**
The control is decisive: the same music engraved by LilyPond gives 31 hollow
detections against 30 real half notes, and pitch recall and pitch+duration
recall come out **identical to three decimals (0.926)**.
(MEASURED HERE: `benchmarks/omr-first-run-2026-08/DURATIONS.md`.)

**Confused with:** a black notehead (the dominant direction, above); the bowl of
a printed letter; on the other plates, the same barline/edge/neighbour set as the
black head — though note that **the under-1.0-space count is ZERO for every Half
and Whole class on both plates**, so the barline contamination is entirely in
`noteheadBlack*`. The Half classes are the cleanest notehead classes on both
records by share-decided (0.70-0.76).

### 2. Best method: YOLO / CV / other

**YOLO, and the lever is labelled data, not a rule.** Four CV routes were
measured on the closed-counter population and all four failed:

| route | result |
|---|---|
| reclassify by ink fill | nothing to reclassify — the heads are not detected |
| counters as enclosed white holes | **662 candidates for 68 half notes** |
| Bravura `noteheadHalf` template match | 15 of 68 at threshold 0.50, **none above** |
| dilate the paper to reopen the counter, re-detect | 4 → 9 hollow, and inflates `noteheadWhole` 1 → 5 |

(MEASURED HERE: `benchmarks/omr-first-run-2026-08/DURATIONS.md`.)

**The labelling route was taken and it worked, partially.** A five-publisher
hollow-notehead campaign fed a fine-tune; the shipped weights are a head GRAFT
(`merge_class_head.py`, the seven notehead class rows kept, 201 restored) plus a
per-class bias floor. On Beethoven 5 p.1 half-note detections go **8 → 27 → 31**
against a truth of 68, dense notehead recall 0.941 → 1.000, pitch+duration recall
0.435 → 0.510. **So roughly 46% of that plate's half notes are now read, from
12%.** (MEASURED HERE:
`benchmarks/omr-labeling-survey-2026-09/ROUND5_METHOD_2026-09-04.md` §3a-§3b.)

⚠️ That gain is **recall bought with precision**, stated in its own source: the
graft's arm scores *worse* on OMR-NED on the very page the campaign is about
(`wrong note head` 30 → 72), because the metric charges the new heads that are
wrong. Axis 1 rewards it, axis 2 charges it, on the same change.

**Training evidence** (probe, this session): `noteheadHalfOnLine` **159**,
`noteheadHalfInSpace` **145** boxes — about a fifth of the black heads'.

### 3. Where on the page the deciding information lives

⚠️⚠️ **THIS IS THE ONE SYMBOL IN THE FAMILY WHERE POSITION CANNOT HELP AT ALL,
AND IT IS THE CLEAREST INSTANCE OF SEAN'S OWN WARNING.** Black, half and whole
heads stand on the same lattice, in the same places, with the same anchors. The
position fact `capture.py` grades MEASURED for this family answers *which
pitch*, never *which value*. A grammar layer that knows the lattice and the
anchors — the confusables doc's whole principle — has nothing to say here.

**Inside the box, and only inside it** — the counter is the whole discriminator.
That is why this symbol is the one where the print quality is the ceiling, and
why *"there is nothing better available for Litolff"*: its raster is `bpc: 1`,
genuinely bitonal, and 600 dpi is exactly its native resolution, so a fused blob
is fused ON THE PLATE. (MEASURED HERE:
`benchmarks/omr-stem-crop-pass-2026-09/FINDINGS.md` §7.)

The one outside-the-box fact that bears on it is `[C15]` *no stem means a whole
note* — its contrapositive, *a stem means this is not a whole note*, would
separate half from whole. It is filed **ASSERTED, with no figure**, and the one
population anyone tried to score it on was 16-of-17 class-false.

### 4. Stage by stage

Identical to the black head at every stage — the class is filed by
`gather.py:373` and read by `_HEAD_BEATS["noteheadHalf"] = 2.0`
(`adjudicators/rhythm.py:44`). No decision anywhere weighs *black vs half*.

⚠️ **The same-cell NMS triple is specifically a black/half confusion**, and its
worked instance is one notehead surviving as `noteheadHalfInSpace` (0.371),
`noteheadBlackInSpace` (0.288) and `noteheadHalfOnLine` (0.252) with duration
verdicts 1.0, 0.5 and 1.0. The record already knows — all three sit in one
`Verdict.correlated` group — and **`Verdict.correlated` is consumed by nothing.**
(MEASURED HERE: `benchmarks/omr-staged-dedupe-2026-09/FINDINGS.md` §2(ii), §6.4.)

### 5. Abstain or best-guess — and what leans on this mark's certainty

**(a)** No. There is no *hollow or solid, I cannot tell* state. The class is
observed as a fact and the duration follows from it by table lookup. The nearest
thing to an abstention is `Ruling.abstain("unknown_head")`, which fires only for
a class name outside the four-entry table — i.e. never for a real notehead class.

**(b)** Everything that reads a DURATION leans on this: the bar sum, the meter
decision's bar terms, `reconcile_duration`, `size_measure_rest`, and both INFER
rules. A half read as a quarter shortens its bar by a beat, and the bar-sum
warning that would catch it fires **111 of 193 scan staves and is UNCONSUMED**
(`adjudicators/rhythm.py`, `checked_by`).

⚠️ **And the independence fails here in the classic shape.** A plate whose
counters have closed is a plate whose bars do not sum, so the bar-sum arbiter is
silent exactly where the reading is worst — *the bars are not an independent
umpire over a bad reading*, which this repo has now recorded four times.
(MEASURED HERE + ASSERTED: CLAUDE.md's own section of that name;
`docs/stage-charter-2026-09-18-what-each-stage-does.md` §4.1.)

---

## `noteheadWholeOnLine` / `noteheadWholeInSpace`

A wider oval with a larger counter and no stem.

### 1. What sets it apart — and what it is confused with

**The alphabet's BOWL/BLOB entry covers this symbol implicitly** and names the
*lower bowl of a 6/8's "8"* — which the crop pass then found to be, literally,
the dominant contaminant of this class. The entry got that right before anyone
counted. What it does not do is separate whole from half, which is the question
this symbol actually fails at.

**The literature gives two discriminators and this repo has measured neither.**
`[L4]` says a whole head is **1.688 sp** wide against a half's **1.180** — a 43%
gap with Whole wider — and that height cannot separate them at all. `[C15]` says
the absence of a stem is positive evidence. Both are filed **LITERATURE ONLY /
ASSERTED**, and the second has *no figure* in the registry.

⚠️⚠️ **MEASURED ON BOTH PLATES, THE WIDTH GAP IS ABSENT AND THE SIGN IS
REVERSED**: `noteheadWhole` sits between Black and Half and is NARROWER than
Half (Litolff 1.59 vs Half 1.61; Breitkopf 1.44 vs 1.56). **And that does not
refute `[L4]`, because the class is not whole notes.** The crop pass adjudicated
17 whole-class heads against the plate and found **16 of 17 CLASS-FALSE** —
eight are the two round counters of a printed time-signature **8** (three of them
on a cautionary `9/8` after a final double barline), five are the white GAP
between two thick staff lines, two are a dotted HALF note with a printed up-stem,
one is a hairpin wedge. (MEASURED HERE:
`benchmarks/omr-notehead-width-2026-09/FINDINGS.md` §6;
`benchmarks/omr-stem-crop-pass-2026-09/FINDINGS.md` §5.)

⚠️⚠️ **THE WIDTH SAYS THE SAME THING WITHOUT THE PRINT, WHICH IS THE
CROSS-CHECK.** Share of each class whose stem the pipeline reads (`decided`):

| class | Litolff | Breitkopf |
|---|--:|--:|
| `noteheadBlack*` | 0.59 / 0.59 | 0.46 / 0.63 |
| `noteheadHalf*` | 0.71 / 0.70 | 0.73 / 0.76 |
| **`noteheadWholeInSpace`** | 0.67 (n=12) | **0.107** (n=75) |
| **`noteheadWholeOnLine`** | **0.000** (n=5) | 0.310 (n=29) |

`noteheadWholeInSpace` on Breitkopf decides on one box in ten, by a wide margin
the lowest of any class on either plate. **Two instruments, one conclusion: the
Whole classes are a dustbin.** (MEASURED HERE, same file §6.)

**Confused with, named from the print:** a time-signature digit's counters, the
white gap between thick staff lines, a whole REST (two of them, 1.12 and 1.27
spaces wide but **0.34 and 0.64 TALL**), a bass clef (2.49 sp), a hairpin, a
dotted half note.

**The on-line/in-space suffix is worth nothing here:** with n = 5 and n = 12 on
Litolff and both classes contaminated on Breitkopf, no statement about it is
supportable.

### 2. Best method: YOLO / CV / other

**Neither, as things stand — the population is too small and too polluted to
call.** 17 boxes on Litolff and 104 on Breitkopf over 8 pages. A width floor
does not reach the contamination (the under-1.0 count is **ZERO for every Whole
class on both plates**); a height floor would reach it and is REFUSED, because
the shortest print-confirmed noteheads measure 0.340 and 0.345 spaces.

**What would reach it is the SURROUNDING ink** — a counter of an `8` has a digit
around it, a staff-line gap has two lines around it, a whole rest has a bar of
silence around it. That is `Q.INK`'s question, and `Q.INK` is read by nothing.
(ASSERTED, with the shape distributions committed at
`benchmarks/omr-notehead-width-2026-09/out/contamination.json → shape_vs_print`
so a session holding print can adjudicate it.)

**Training evidence** (probe, this session): `noteheadWholeOnLine` **82**,
`noteheadWholeInSpace` **61** boxes.

### 3. Where on the page the deciding information lives

⚠️ Position says nothing here either — see the Half section's §3. The
discriminators are all about the ink BESIDE the head, which is the one place
neither `Q.NOTEHEAD_STAFF_POSITION` nor the eleven new position quantities look.

* **Width relative to its own staff space** — 1.688 sp by the font, untested on a
  plate.
* **The absence of a stem**, which is a fact about the ink BESIDE the head and is
  the only structural discriminator. Unmeasured here.
* **Whether a time signature or a staff-line gap is around it** — outside the box,
  and nothing looks.
* **Whether the bar holds anything else.** A whole note fills its bar; the
  surviving print-confirmed instances all do.

### 4. Stage by stage

Identical to the other two. `_HEAD_BEATS["noteheadWhole"] = 4.0`; a
`noteheadWholeOnLine` read in a 2/4 bar contributes 4.0 quarters to a 2.0-quarter
bar, which is precisely the population `size_measure_rest` and `bar_fill` argue
about for rests — but for a NOTE there is no equivalent consequence, and nothing
in EVALUATE questions a 4.0 in a 2.0 bar.
(MEASURED HERE by reading `consequences.py`: the only rules touching duration are
`size_measure_rest`, which requires the bar's only standing duration to be one
dotless `restWhole`, and `reconcile_duration`, which re-reads a BEAM LEVEL ±1 and
so cannot move 4.0 to 2.0 for an unbeamed head.)

### 5. Abstain or best-guess — and what leans on this mark's certainty

**(a)** No abstention exists, and this is the class where one would be worth
most: it is the class the print says is 16-of-17 wrong.

**(b)** A false whole note is the most expensive single wrong anchor in the
family, because it asserts a bar-length duration. It will (i) overfill its bar,
(ii) make that bar's sum useless as an arbiter, (iii) suppress
`size_measure_rest` on that cell (the rule requires the bar's ONLY standing
duration to be one whole rest), and (iv) stand as a chord member or an arc
endpoint. It cannot abstain and no consequence can question it.

⚠️ `docs/exploration-what-is-on-the-page-2026-09-09.md` **B.5** states the
condition for the one repair that would help — *"Absence-of-stem is positive
evidence for duration… Cheap to add as corroboration; only worth it if
`adjudicate_duration` declares it."* It does not declare it: `Q.STEM` is in
`wants` and is read only to attach beams and flags, never to ask whether a stem
exists at all. ⚠️ And **B.7** names the only duration signal that is genuinely
independent of stem, beam and class — proportional horizontal spacing, *"the one
entry here that is a genuine measurement of the raster nobody takes"*. For a
whole note, which fills its bar, that would be the strongest available witness
and it has never been computed.

⚠️ The one existing check that WOULD reach it — `[C15]`, *no stem means a whole
note*, run backwards — is the check whose own test population turned out to be
16-of-17 not-whole-notes. So the discriminator and the contamination are
entangled: **you cannot price `[C15]` on this class until the class is cleaned,
and cleaning the class is what `[C15]` was for.**

---

## `noteheadDoubleWhole*` (OnLine / InSpace, and their `*Small` variants)

The breve: an oval with flanking vertical strokes. Four classes in the space.

### 1-5, briefly, because there is nothing to report and that is the finding

⚠️ **The breve appears in NONE of the alphabet's seven mark entries** — it is
neither a bowl nor a blob, because it carries flanking vertical strokes, and the
VERTICAL STROKE entry is about stems and barlines. So this symbol has no Q1 in
the repo at all, and this is the first place one is asked for.

**ZERO detections on both committed records** — the per-class tables over 2,347
and 3,337 notehead boxes list only the six Black/Half/Whole classes.
**ZERO hand-labelled boxes** across all 14 admitted catalog versions (probe, this
session), and the labelling inventory annotates the family *"R1 family; rare on
orchestral pages"*.

The class HAS a route: `_HEAD_BEATS["noteheadDoubleWhole"] = 8.0` and the legacy
`_NOTEHEAD_INTRINSIC["noteheaddoublewhole"] = (8.0, "double_whole")`, and the
prefix ordering is safe (`noteheadDoubleWhole…` does not start with
`noteheadWhole`, checked). So if one is ever detected it would be read; nothing
would question it; and at 8.0 quarters it would be the most destructive single
wrong duration available.

⚠️ `[C1 + L3]` records the breve as **2.396 × 1.240 staff spaces** — the only
notehead in the family that is NOT one space tall, because of the flanking
strokes. Any height-based notehead rule that ships must exempt it, and none
currently does (they are all legacy and edge-restricted).

**Grade:** MEASURED HERE for the two zeros (n = 5,684 boxes, 591 label files);
LITERATURE for the Bravura dimensions; ASSERTED for everything about how it would
behave, because it has never happened.

---

## The `*Small` variants, and `graceNoteAcciaccatura*` / `graceNoteAppoggiatura*`

Two different things that both mean *grace note*: eight `notehead…Small` classes
(a small head), and four `graceNote…` classes (the slashed/unslashed grace
figure). Plus `noteheadFullSmall` and `noteheadHalfSmall` in the coarse half of
the 208-class space.

### 1. What sets it apart — and what it is confused with

**The alphabet's BOWL/BLOB entry names this exactly, as its one open lead**:
*"Recorded lead, untried: a grace head is smaller than its neighbors (41×38 px
against 51-83 in the same cell) — the one route left after two label-side fixes
were refuted."* This section AGREES and UPDATES it: *untried* was true in
2026-09-04 and is no longer — it was tried twice at the LABEL end and never at
the reader end. See below.

**SIZE, relative to its neighbours in the same cell.** Measured: grace heads at
**41×38 px against 51-83 px** for full heads in the same cell; the DSv2 classes
render at roughly 0.6× (`grace_score.py`), and the labelling batch places a
0.62-space click box. **Absolute size cannot say it** — that is a fact about the
plate's staff space — so the discriminator is comparative and needs the cell's
own head population.
(MEASURED HERE, n small:
`docs/position-grammar-confusables-2026-09-04.md` §2 BOWL/BLOB;
`benchmarks/omr-labeling-grace1-2026-09/batch_config.json`.)

**Confused with:** an ordinary notehead (the dominant direction, below); an
edge-clipped fragment (0.29-0.56 spaces, overlapping the grace band); a
staccato dot or augmentation dot at the small end.

⚠️ `[C1 + L3]`'s height rule is explicitly restricted to edge-touching
detections **because of grace notes** — *"A short notehead in the middle of a
cell is some other problem and this must not have an opinion about it."*

### 2. Best method: YOLO / CV / other

**Undetermined, because the detector has never been taught it.**

* **ZERO hand-labelled `graceNote*` boxes** in all 14 admitted catalog versions
  (probe, this session). `*Small` noteheads: **8 boxes total** —
  `noteheadBlackInSpaceSmall` 5, `noteheadHalfOnLineSmall` 2,
  `noteheadBlackOnLineSmall` 1 — against 1,756 full-size notehead boxes.
* Anything not boxed on a training image is taught as background, so this corpus
  actively teaches that grace heads are nothing.
* **Two labelling batches were run and the ground truth is 30 boxes.**
  `omr-labeling-grace1-2026-09`: 103 cells swept blind, **zero graces found** —
  sampling 8 cells of a ~150-cell page against ornaments concentrated in a few
  staves. `omr-labeling-grace2-2026-09`: 152 cells, eye-verified page regions
  (the Peters print marks every grace run with a ★), **30 boxes over 15 cells**,
  15 `noteheadBlackOnLineSmall` and 15 `noteheadBlackInSpaceSmall`. Those
  verdicts were never converted into a catalog version.
  (MEASURED HERE, probe this session over the committed verdict JSON.)
* The pre-fill path cannot supply truth either: the transcription holds **0
  `Small` detections on any page** and the reference encoding holds **0 grace
  notes in 28,579**, so grace notes are a ceiling for the MXL pre-fill and the
  two errors they cause there are unfixable from either source.
  (MEASURED HERE: `docs/handoff-2026-09-03-prefill-measured.md`, quoted in
  CLAUDE.md's pre-fill section.)

⚠️ `truth_tokens`' docstring justifies skipping grace notes *"because the
detector labels them `*Small`"* — **false on a scan**, and it makes the skip
actively harmful the moment a reference does carry `<grace/>`.

### 3. Where on the page the deciding information lives

⚠️ **No position quantity reaches this symbol.** `capture.py` has no grace
family row; `positions.py` gave one to eleven families and grace was not among
them, because grace ink is either filed under `note` (the `*Small` classes,
where it silently inherits a full notehead's treatment) or under nothing at all
(the `graceNote*` classes). The discriminator is a SIZE RATIO, which is not a
position fact and has no home in either scheme.

* **The other heads in the same cell** — the only ruler that works.
* **The slash** across the stem (acciaccatura), which is what the `graceNote*`
  classes are actually drawn around.
* **The beat note immediately to its right**, which is what it belongs to.
* **The printed footnote / ★**, in the Peters case — which is how the labelling
  batch found them at all, and is not a signal any reader has.

### 4. Stage by stage — ⚠️ this is the finding

**A `*Small` notehead is read as a FULL-VALUE note, on both paths.**
`_NOTEHEAD_PREFIX = "notehead"` (`gather.py:257`), so
`noteheadBlackInSpaceSmall` gets `Q.NOTEHEAD_CLASS`, a
`Q.NOTEHEAD_STAFF_POSITION`, a pitch, and `_HEAD_BEATS` matches it by
`startswith("noteheadBlack")` → **1.0 quarter**. The legacy
`_NOTEHEAD_INTRINSIC` does the same. **Neither path contains the string `grace`
or `Small` anywhere in `export.py`, `rhythm.py`, `voicing.py` or
`pitch_resolver.py`** (grep), so no `<grace/>` is ever written and a grace note
steals a real beat from its bar.

**A `graceNote*` detection has no quantity at all.** It does not start with
`notehead`, so GATHER files only an anonymous `Q.GLYPH_BOX`.
`gather_coverage.FAMILY_TO_Q` maps `"grace": None` — one of the families whose
ink *"no consumer can ask for and no abstention can be recorded about"*.
(MEASURED HERE: `gather_coverage.py:590`; `python3 -m tools.omr.staged.gather_coverage`.)

**EVALUATE / INFER / EXPORT**: nothing. There is no grace consequence, no grace
inference, and no `<grace/>` emission.

### 5. Abstain or best-guess — and what leans on this mark's certainty

**(a)** No, in the strongest form in this dossier: one variant cannot abstain
because it is silently promoted to a full note, and the other cannot abstain
because it has no subject to abstain about.

**(b)** A grace note read as a full note is a **bar-arithmetic** fault: it adds
a beat that is not there, which corrupts the bar sum, and the bar sum is the
arbiter for the meter, for `reconcile_duration` and for both INFER rules. It
also becomes an arc endpoint and a chord member. Because the reach is currently
zero detections on the two committed records, **the cost is not measured and
this is a latent rather than an observed fault** — but it is latent only as long
as the detector keeps missing them, which is the opposite of the direction the
project is going.

---

## `ledgerLine`

A short horizontal stroke carrying a note above or below its staff. Class 1 in
the space; also measured directly off the raster by
`tools/omr/annotate/ledger_grid.py`.

### 1. What sets it apart — and what it is confused with

**The alphabet's entry is HORIZONTAL STROKE — tenuto vs ledger line, Sean's own
example** (`docs/position-grammar-confusables-2026-09-04.md` §2): *a ledger line
lies ON the extended half-space lattice, continues a ladder run toward a head or
has a head centred through it, and matches the staff's own measured line
thickness… a tenuto sits OFF the lattice about a space beyond its head, with
nothing centred through it.* It also names the consequence: **the confusion is
live in the EVIDENCE CHAIN, not just the export — a tenuto misread as a ledger
feeds false rungs into attribution, and the reverse starves it.**

This section AGREES with the lattice and ladder clauses (both are shipped as
`Q.GLYPH_LADDER`), and **DISAGREES with the thickness clause on two counts** —
see §"Where this disagrees". It also ADDS the largest measured confusion, which
that entry does not name: the class fires on ORDINARY STAFF LINES.

* **It is a SHORT horizontal run centred on a notehead's x.** *A run much longer
  than a head's width plus twice the extension is not a ledger line.* Bravura's
  `legerLineExtension` is 0.4 sp each side; LilyPond expresses it as 0.25 of head
  width ≈ 0.30 sp. (`[C3 + L5]`, LITERATURE.)
* **It is THICKER than a staff line** — Bravura 0.16 vs 0.13, about 23% heavier.
  Filed **LITERATURE ONLY, untested here**, and the repo's adjacent measurement
  runs the other way: `remove_staff_lines` clears only a median **55%** of a
  Litolff cell's line ink. (`[L6]`.)
* **It comes in an unbroken LADDER.** An engraver prints every rung between the
  staff and the note. (`[C4]`, MEASURED HERE as a consequence — the ladder tier
  took pooled OMR-NED 0.1506 → 0.1431 and Beethoven notes to 81/81.)

**Confused with, measured:**

* ⚠️⚠️ **AN ORDINARY STAFF LINE. 1,107 of 1,878 `ledgerLine` detections on the
  Litolff record land INSIDE the staff**, every one of them at steps 0/2/4/6/8 —
  the five printed lines. *"Whether that path filters them is unchecked."* This
  is 59% of the class's output on that record. (MEASURED HERE:
  `benchmarks/omr-ledger-extrapolation-2026-09/FINDINGS.md` §3.)
* **A TENUTO**, which is the same shape. (Recorded as a live confusable in
  `[C4]`'s known exceptions; no figure.)
* **Its own splitting**: a rung printed THROUGH a hollow head is interrupted by
  the counter and comes out as two short spans, so a contiguous-run detector is
  blind to exactly the rung that matters most. (`[C6]`, MEASURED HERE; the
  bridging constant is 0.55 spaces, a half's counter.)

⚠️ **And the detector's box is systematically wrong about a rung's position.**
Asked of the model's boxes, the Litolff rung gaps read 1.130 / 1.090 / 1.080;
asked of the raster, 1.032 / 1.079 / 1.048. **The first gap is 10% too wide**,
because a rung print-merges into the same connected component as its notehead
and a box drawn round merged ink sits further out than the line it names. *The
raster is the better instrument and no headline figure comes from the detector.*
(MEASURED HERE: same file §5.)

### 2. Best method: YOLO / CV / other

**Classical CV off the raster, decisively.**

* The raster reader finds rungs as rows of ink in a strip at the head's own
  x-range, and finds the staff's own five lines in the same strip as its ruler.
  Control: those five lines sit **+1.06 px** (Litolff, sd 2.38, n=5,201) and
  **−0.33 px** (Breitkopf, sd 3.03, n=6,712) from the record, against a half-step
  of 7.75 px. A strip that cannot recover four of five staff lines is REFUSED.
* Scored on the 1,107 in-staff detections, whose true positions are known
  exactly, the detector's box carries a bias of **+0.011 spaces at sd 0.048** —
  it locates a printed horizontal line to a twentieth of a space. So the box is
  precise; it is the merge that moves it.
* ⚠️ **YOLO is structurally poor at thin lines** — the stated Phase-4f reason
  stems and beams moved to classical CV — and **the training corpus contains 5
  `ledgerLine` boxes across 591 labelled cells** (probe, this session), so a
  fine-tune on this corpus teaches that ledger lines are background. Measured:
  under fine-tuning `ledgerLine` goes **288 → 5 → 0 → 0** across arms, and the
  shipped weights restore it by head surgery rather than by training.
  (MEASURED HERE:
  `benchmarks/omr-labeling-survey-2026-09/ROUND5_METHOD_2026-09-04.md` table §2.)

### 3. Where on the page the deciding information lives

⚠️ **This symbol has NO position quantity and NO family row.** `capture.py`'s
table has fourteen families and `ledgerLine` is not one of them;
`export.NOT_NOTATION` files it as *"consumed by `glyph_owner`'s ladder
arbitration"*, and `gather_coverage.FAMILY_TO_Q` maps the family to
`GLYPH_LADDER` — **a boolean verdict about a NOTE, not a reading of the rung.**
So the one fact this symbol is actually for — WHERE the rung sits — reaches the
record only inside another mark's ownership evidence, and the pitch reader never
sees it. (MEASURED HERE by reading `capture.py:239-256`, `export.py:2967-2985`,
`gather_coverage.py:590`.)

* **Between the staff and the notehead** — the ladder occupies exactly that gap,
  and its completeness is the fact.
* **At the head's own x**, and no wider than the head plus two extensions.
* ⚠️ **Its PITCH is a property of the PLATE, not of the staff.** Measured over
  nine publishers the rung gap is **Litolff 1.102-1.135, Eulenburg 1.050,
  Jurgenson 1.055, Universal 1.030** against **Breitkopf 0.975, Peters 0.977,
  Simrock 0.975, Novello 0.975** — the literature's "same spacing" is wrong in
  both directions. A corrected CONSTANT was swept and refused: no single factor
  serves 1.03-1.11 and 0.97-1.00 at once. (`[C3 + L5]`, MEASURED HERE, three
  independent populations, two detector-free.)

### 4. Stage by stage — ⚠️ the second finding

**GATHER.** A `ledgerLine` detection gets a `Q.GLYPH_BOX` like everything else.
It is then read in exactly ONE place: `_ledger_index` (`gather.py:637`) collects
them per system, and `_observe_ladder` (`:649`) writes `Q.GLYPH_LADDER` — a
BOOLEAN, `found == expected` — **only for a CONTESTED notehead, and only where
that head is outside the candidate staff's band.** Everything else the class
detects is filed and never read.

**ADJUDICATE.** `Q.GLYPH_LADDER` is read by `adjudicate_glyph_owner` alone, as
tier 1. It is the deciding tier on **107 of 464** contests on Litolff and
**244 of 617** on Breitkopf. A BROKEN ladder contributes nothing — not a
negative — because *two broken ladders are not evidence either way: a found rung
can belong to the other staff's note exactly as a gap can.*

**⚠️ There is NO ledger-line consumer on the PITCH path.** `pitch_resolver` and
the staged `_cell_grid` extrapolate the in-staff grid outward at exactly
**1.000×** — half the mean of this staff's own four printed line gaps. On Litolff
the grid has fallen **half a step behind by the fourth ledger rung** (+0.065 /
+0.223 / +0.319 / **+0.541, which FLIPS**) and **66 of 2,347 heads (2.81%) are
read a diatonic step wrong, against 0 of Breitkopf's 3,337**. 66 is explicitly a
FLOOR — 44 further heads stand beyond the fourth rung where the drift is larger
and only 10 strips reach. `measure_ledger_rungs` exists and does this correctly;
its only callers are the labelling UI and its own test. *The value existed and
nothing read it.*
(MEASURED HERE: `benchmarks/omr-ledger-extrapolation-2026-09/FINDINGS.md` §0, §4.)

**EVALUATE / INFER / EXPORT.** Nothing. No `Q.LEDGER_LINE` quantity exists;
`gather_coverage` maps the family to `GLYPH_LADDER`, which is a verdict-shaped
fact about a NOTE rather than a reading of the rung.

**Legacy only:** `_drop_unladdered_noteheads` (an outside-staff head with no rung
at all, at confidence 0.45-0.53 against 0.76+ for every real one) and the
ladder tier of `_dedupe_cross_staff_detections`. Neither runs on the staged path.

### 5. Abstain or best-guess — and what leans on this mark's certainty

**(a)** `Q.GLYPH_LADDER` is a boolean and cannot express *three of four*, which
is deliberate — counting was measured WORSE (a ghost's single rung WAS the real
note's own ledger). But `found` IS on the record and is read by nothing, and
`wiring.KNOWN_GAPS` carries that as a standing gap with the note *"recorded so
that refusal stays checkable, not so it is reversed."*

**(b) Two things lean on it, and they fail together.**

* **Cross-staff ownership.** 107 and 244 contests decide on it. A rung missed is
  a contest that falls back to distance, *which is measured to be nearly a coin
  flip* (contested hairpin copies sat 5-62 px nearer one staff against 25 px the
  other way).
* **Pitch, outside the staff.** And here the dependency is not on the detector at
  all — the reader ignores the printed rungs entirely and extrapolates.

⚠️ **The independence answer is the one good one in this dossier.** The raster
rung reader does NOT come off the detector and does not fail when the detector
does: it was measured against the printed staff lines in the same strip and it
beat the detector's boxes on the plate that drifts. So *if you want a second
witness for a ledger note's pitch, it exists, it is detector-free, and it is
already written* — it is simply not wired to the reader. This is the cleanest
available instance of *a second witness must not come off the same raster* being
satisfiable.

⚠️ **And a warning for anyone wiring it**: 44% of ledger-country heads are
off-grid against 11% inside the staff, and correcting the 32 own-staff heads with
ink truth to their TRUE position changed the stem convention's agreement by
**exactly nothing — 17 of 32 either way**. Fixing the ledger grid is a PITCH
repair and demonstrably not a stem-direction one.

---

## `augmentationDot`

A small filled dot to the right of a note or rest, lengthening it by half.

### 1. What sets it apart — and what it is confused with

**The alphabet's DOT entry is the authoritative Q1 for this symbol and this
section does not improve on it** — *one mark, four roles, plus noise*, with the
augmentation dot named by *right of a head, at the head's space, or half a space
above for a head on a line; the window asymmetric 0.75 / 0.25 because a dot
never sits under its note*. The four roles and their discriminators are
reproduced in the table below **verbatim from that document**; everything after
the table is what this dossier ADDS, which is the per-symbol reach and the
staged wiring. Nothing here disagrees with it.

**Position, and the position is asymmetric.** A note in a space takes its dot in
the same space; a note ON A LINE takes it in the space **above** — half a staff
space up — and a dot is **never below** its note. Measured over 116 dots the
signed offsets are **bimodal and nothing else: 52 at 0.00 spaces, 52 at +0.50,
nothing between +0.57 and +3.75.** The sources agree to the half-space.
(`[C50 + L31]`, MEASURED HERE + LITERATURE.)

⚠️ **The unit matters more than the window.** The old gate was
`max(dot.height, 12) * 1.2` — a length derived from the dot's own small, noisy
box — so the on-a-line case landed within a few pixels of it and went either way:
**C Horn 1's dotted half read as a half in bars 1 and 5 and as a dotted half in
bars 2, 3, 4 and 6.** The box-derived gate cost **193 edits**. Shipped:
`DOT_ABOVE_NOTE_MAX_SPACES = 0.75`, `DOT_BELOW_NOTE_MAX_SPACES = 0.25`, in STAFF
SPACES.

⚠️ **The asymmetry is forced by double stops** — Brahms's Viola plays two heads a
space apart each with its own dot, so the lower dot is equidistant from both, a
symmetric window TIES, and the upper note comes out double-dotted while the lower
loses its dot. That is the literature's own chord exception arriving as a
measurement.

**Confused with, concretely** (`docs/position-grammar-confusables-2026-09-04.md`
§2 DOT — one mark, four roles):

| role | what names it |
|---|---|
| **staccato** | stacked VERTICALLY with one head, opposite the stem, **never to the head's right** |
| **F-clef dots** | header window only, straddling line 4, past the clef body's right edge (0.94-1.79 notehead widths) |
| **repeat dots** | a vertical pair in spaces 2+3, adjacent to a barline |
| **ink noise** | none of the above |

Also confused with a real dot in the wrong ROLE: on Breitkopf the single
`aug_dot` that attaches to a rest across 691 rows is **FALSE** — width 0.180
staff spaces against a median of 0.490, rank 1 of 656, and the crop shows a
clean undotted whole rest.

### 2. Best method: YOLO / CV / other

**YOLO for the ink, geometry for the role, and the split is already right.**
Reading F1 **0.962** on the engraved family (102 truth, 108 predicted, precision
0.935, recall 0.990); at a 2.0-space tolerance 0.971, so it is found and well
placed. Export: 158 detected, **149 exported, truth 149 — matches the truth.**
(MEASURED HERE:
`benchmarks/omr-reading-vs-reproduction-2026-09/FINDINGS.md` §2, §3.)

**Training evidence** (probe, this session): **167 boxes** — the third-largest
class in the corpus after the two black noteheads.

⚠️ **On a scan the limit is DETECTION and it is publisher-shaped.** Litolff
pp.1-3 fires **20 `aug_dot` rows in total, of which exactly ONE reaches a
notehead**; Breitkopf fires **656** (and 371 flags against Litolff's 49). Over
848 rows across three documents, **752 attach to a notehead and exactly one to a
rest.** So a dot rule measured on Litolff is measuring nothing.
(MEASURED HERE: `benchmarks/omr-staged-dotted-rest-2026-09/FINDINGS.md` §reach.)

### 3. Where on the page the deciding information lives

⚠️ **This symbol has no position quantity and no family row either** —
`capture.py` has no `augmentation` family, `positions.py` gave it none, and
`export.NOT_NOTATION` files it as *"consumed by `duration` as a dot"*. Unlike
the ledger line that is arguably right: the dot's position is only ever
meaningful RELATIVE to a particular head, which is what `_attached_dots`
computes and which no absolute staff-grid row could carry. **This is the
family-positions work's own design claim** — *the musically meaningful
measurement differs by symbol and a schema wide enough for all of them would
hold none of them well* — arriving as a reason NOT to add a row.
(`benchmarks/omr-family-positions-2026-09/FINDINGS.md` §1.)

* **To the RIGHT of a notehead or rest**, within about five dot-widths in x.
* **At the note's own space, or half a space above it** — never below.
* **In STAFF SPACES**, never in the dot's own bounding box. This is the single
  most important sentence about this symbol.
* **Which head is the dot's BEST target** — the claim is reciprocal, so a dot is
  taken only where THIS head is the best target the dot has in the cell.

### 4. Stage by stage

**GATHER.** `gather_rhythm_marks` (`gather.py:722`) files `Q.AUG_DOT` with the
dot's `(x_center, y_center)` **on the DOT'S OWN glyph subject**, plus its
`Q.GLYPH_BOX`. `Q.CELL_STAFF_SPACE` is gathered per cell because the window is
in staff spaces and the canonical frame's half-step is **not** a constant — on
one engraved fixture **184 of 368 cells read 100 px and the other 184 read
38.5-56**.

**ADJUDICATE.** `_attached_dots` (`adjudicators/rhythm.py:284`), inside
`adjudicate_duration`. It reads `Q.AUG_DOT` at `SELF_AND_DESCENDANTS` scope on
the CELL — and that scope is the whole story: for a while it read the NOTEHEAD's
own subject, so **157 dot rows on a three-page record produced ZERO durations
carrying a dot**, and the two constants written for this decision sat in the
module used by nothing in it. The pool is `Q.NOTEHEAD_CLASS` **and** `Q.REST`,
because `_pair_dots_to_targets` builds exactly that pool and reading noteheads
alone was a divergence from the paid-for rule.

**EVALUATE.** Nothing dot-specific. `reconcile_duration` re-reads a BEAM LEVEL
±1 and leaves the dot count alone.

**INFER.** Untouched — the two rules collapse narrowings, and a narrowing carries
its `dots` through unchanged.

**EXPORT.** `_place_notes` writes the dot count into `<type>` + `<dot/>` via
`_dotted_duration_for_beats`. ⚠️ *The dots are ONE fact, not two* — summing the
type's prefix and the dot count wrote a double-dotted quarter for every
single-dotted one, 82 edits on one fixture.

⚠️ **`DOT_ABOVE_NOTE_MAX_SPACES` / `DOT_BELOW_NOTE_MAX_SPACES` are DUPLICATED
LITERALS**, held in both `tools/omr/rhythm.py:1118/:1133` and
`tools/omr/staged/adjudicators/rhythm.py:63-64`, not a shared import — and every
other measured constant in this area is imported specifically to prevent drift.
This pair is the odd one out. (MEASURED HERE by reading both files;
`[C50 + L31]` code row says the same.)

### 5. Abstain or best-guess — and what leans on this mark's certainty

**(a) Yes, and it does — by leaving the dot unattached.** A dot with no head to
its LEFT inside the window is simply not claimed; nothing is given to the nearest
thing available. The reciprocity is what makes that safe per-glyph. And a dot
that would go to a rest is scored in the same pool, so widening the pool can TAKE
a dot from a notehead — which is the rule working, not a regression.

**(b) The bar sum leans on it, and the rest of the family barely notices it.**
A missed dot shortens its note by a third of its value and the bar no longer
sums; a false dot lengthens it. Nothing else reads the dot.

**Independence: this one is genuinely separable, with a caveat.** The dot is a
different piece of ink from the head, read by the same detector on the same crop
— so it is NOT an independent witness about the head, and the repo's
`correlated_groups` rule would absorb it. But the reverse direction is the useful
one and it is sound: the dot's ROLE is decided by GEOMETRY against the staff grid,
which is a ruler and not the detector. ⚠️ **What fails together is reach**: the
same plate that hides a half note's counter also loses its dots (Litolff 35 dots
and 49 flags over 2,347 noteheads, against 656 and 371 over 3,337 on Breitkopf).
So on the plate where durations are worst, both duration witnesses are absent at
once.

---

## Where this disagrees with existing documents

Four places, each named because the disagreement is itself the finding.

**1. `position-grammar-confusables` §2 BOWL/BLOB calls two discriminators
"shipped". They are shipped on the LEGACY path only, and do not run on the
staged one.** *"a notehead is a staff space tall (…`_drop_clipped_notehead_fragments`)"*
and *"an outside-staff head with no ledger rung at all is not a note"* both live
in `tools/omr/transcribe.py` (`:544` and `:3739`) and are called from nowhere
else; `staged/gather.py:323` calls the detector fresh and neither filter is in
its path. The same is true of `_dedupe_cross_staff_detections`, which the staged
path re-answers as `Q.GLYPH_OWNER` — that one IS carried across, the other two
are not. **Anyone reading that document as a description of the current staged
reader will over-estimate it by two filters.**
(MEASURED HERE, by grep over `tools/`.)

**2. The same entry does not name the largest measured notehead confusion,
and the alphabet files it under an entry that calls it solved.** On Breitkopf
**476 of 3,337 notehead boxes are `too TALL`**, 459 of them under one staff
space wide, and the print reads **12 of 12 sampled as a barline**. The alphabet's
VERTICAL STROKE entry is headed *"stem vs barline (already solved; the
precedent)"* — which is true of the classical-CV readers that find stems and
barlines, and is not true of the DETECTOR calling a barline a notehead. **The
solved case and the unsolved case share a name.** Nor does BOWL/BLOB name the
second decisive contaminant, **a time-signature digit's two round counters**,
which is a sub-part carved out of a larger glyph and cannot be refuted by
anything inside the box.
(MEASURED HERE: `benchmarks/omr-stem-crop-pass-2026-09/FINDINGS.md` §2, §5.)

**3. HORIZONTAL STROKE says a ledger line "matches the staff's own measured line
thickness". The literature registry says it is 23% THICKER, and the measurement
is read by nothing either way.** `[L6]` *A ledger line is thicker than a staff
line* gives Bravura `legerLineThickness` **0.16** against `staffLineThickness`
**0.13**, and warns *"23% is not a large margin and may not survive a
low-resolution bitonal scan."* So *matches* and *is 23% heavier* are two
different predictions and the tenuto/ledger rule would be built differently
under each. Separately, the thickness the entry says is *"recorded per staff
since the frame-retention work"* is `Q.STAFF_SKEW.thickness_px`, which
`wiring.KNOWN_GAPS` lists as **read by nothing** — so the discriminator is
unavailable today whichever prediction is right.
(`docs/engraving-conventions.md` `[L6]`; `tools/omr/staged/wiring.py`
`"DETAIL Q.STAFF_SKEW.thickness_px"`.)

**4. "Recorded lead, UNTRIED: a grace head is smaller than its neighbours" is no
longer untried — it was tried twice at the LABEL end and never at the reader
end.** `omr-labeling-grace1-2026-09` swept 103 cells blind and found **zero**;
`omr-labeling-grace2-2026-09` swept 152 eye-verified cells and produced **30
boxes over 15 cells** — the project's first grace ground truth. Neither batch
was converted into a catalog version, so the admitted training corpus still
holds **8 `*Small` boxes and 0 `graceNote*` boxes** against 1,756 full-size
notehead boxes. The lead is not untried; it is unharvested.
(MEASURED HERE, probe this session over the committed verdict JSON and
`data/user-labeled/catalog-versions.txt`.)

⚠️ **One thing that is NOT a disagreement and is worth saying so.** The
family-positions work gave eleven families a position quantity and gave the
notehead family none. That is correct: `note` already had the exemplar, and it
is the only family in the tree whose position row is read by a decision that
changes a value. The gap in this family is not a missing position — it is that
**no position, existing or proposed, answers *is this a notehead*.**

---

## What we do not know

1. **Whether the class is right.** There is no measurement of notehead
   CLASSIFICATION accuracy on a scan — black vs half vs whole — anywhere in the
   repo. The 0.999 F1 is a DETECTION figure on engraved pages, matched on centres.
   Everything we know about the class comes from 255 blind-adjudicated boxes, one
   adjudicator, no inter-rater figure, two publishers, 8 pages.
2. **What the 5.55% / 37.67% contamination rate is typical of.** The two plates
   differ **7×** and nothing says which is normal. A third publisher is what the
   denominator needs.
3. **`[L4]` (whole wider than half) and `[C15]` (no stem means whole).** Both
   remain untested, and both are untestable on the current records for the same
   reason: the `noteheadWhole*` population is 16-of-17 class-false.
4. **Whether a grace note would be read.** Zero detections on both records, zero
   labelled boxes in the catalog, and a code path that would silently promote one
   to a full quarter. The cost is latent and unmeasured.
5. **What the ledger-grid repair is worth end to end.** The 66-head figure is a
   count of misread positions on one plate, not a scored file; nothing was
   re-gathered or re-exported.
6. **Whether the 1,107 in-staff `ledgerLine` detections are filtered anywhere.**
   Explicitly recorded as unchecked.
7. **The whole-rest-ink rule's accuracy on a second document.** 25 catches on
   Litolff, 12 on Breitkopf, all 25 hand-adjudicated on one plate; two of its six
   cuts have no plateau, which is why it is the one staged repair behind a flag.
8. **Whether a ledger rung is thicker than a staff line ON A PLATE.** The two
   repo documents predict different things (see disagreement 3), the measurement
   that would settle it is recorded per staff and read by nothing, and it is the
   discriminator the tenuto/ledger rule would be built on.
9. **Nothing here was re-gathered.** Everything is read off two committed records
   and the committed benchmark outputs.

---

## Questions for Sean

1. **The anchor question, answered and handed back.** A wrong notehead is a
   different and worse risk than a missing one: a gap is counted, a false anchor
   recruits a stem, an arc end and a dot, and nothing downstream may doubt it.
   And the independence check splits — noteheads and stems do NOT fail together
   on the heads we read (recall 0.980 against half the stems missing), but they
   DO fail together on the heads we get wrong (459 of 576 under-width boxes on
   Breitkopf are in the same `too TALL` bucket the print reads 12-of-12 as not a
   notehead). **So: should the sweep anchor on noteheads as a whole, or only on
   the heads that have a read stem — an anchor with a declared domain?** The
   second is measurable today and the first is not.
2. **The `Whole` classes are a dustbin on both plates, and the two discriminators
   the literature gives for them are both unmeasured here.** Is it worth a small
   print pass on the 104 Breitkopf `noteheadWhole*` boxes to settle `[L4]` and
   `[C15]` at once? They are the same 17 boxes the crop pass already opened and
   it named the 11 it did not reach, cheapest first.
3. **The ledger grid.** `measure_ledger_rungs` measures the printed rungs
   correctly, is detector-free, and its only consumers are the labelling UI and
   its own test, while the READER extrapolates at 1.000× and misreads 66 Litolff
   heads by a diatonic step. Is wiring it to `pitch_resolver` a job you want, and
   do you want it as a REPLACEMENT for the extrapolation or as a second witness
   that records a disagreement?
4. **Grace notes.** A small notehead is currently promoted to a full quarter and
   steals a beat from its bar; a `graceNote*` glyph has no quantity at all. Two
   labelling sittings produced 30 boxes and were never admitted to the catalog.
   Is this worth opening now, or is it correctly parked until the detector fires
   on one?
5. **The on-line / in-space suffix is a POSITION claim living inside a SHAPE
   class**, and the geometry already measures the position independently. Its
   only live effect is that the same-class contest gate refuses 37 cross-staff
   pairs that differ ONLY in that suffix — which is the one thing two staves'
   grids must disagree about for ink in the gap between them. **Should the
   contest be suffix-blind?** (It is a GATHER change and would need
   `is_relocated_copy`'s domain guarantee re-established in the same change.)
6. **The tenuto/ledger discriminator disagrees with itself across two of our own
   documents** — the confusables alphabet says a ledger line *matches* the
   staff's line thickness, the literature registry says it is 23% heavier, and
   the per-staff thickness measurement that would decide it is on the record and
   read by nothing. Which reading do you want built, and is it worth measuring
   the ratio on a plate first? (It is one raster pass, no re-gather.)
7. **Still open from 2026-09-18 and touching this family**: should an
   accidental's vertical stroke be in the stem veto's domain at all?
