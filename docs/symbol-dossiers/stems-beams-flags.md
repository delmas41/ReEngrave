# Symbol dossier — stems, beams, flags, tremolos, tuplets

**2026-09-20.** One `##` section per symbol, five `###` subsections each, in
Sean's numbering. Research only: nothing under `tools/` changes in this branch.
`git diff` against the branch point touches `docs/symbol-dossiers/` alone.

This family is the one carried furthest, so the sections below say as much
about what was **refuted** as about what is known. Four things were tried and
did not survive contact with the print, and each is named at its symbol:
the stem's *length*, the stem's *direction-from-position*, the pair rule's
*accidental* premise, and the attribution lane's *two-stems-as-one* headline.

| symbol | reader today | has a `Q.` | a decision reads it | reaches the file |
|---|---|---|---|---|
| **stem** | classical CV (`detect_stems`) | `Q.STEM` | yes — 4 decisions | **never** (`<stem>` is a KNOWN GAP) |
| **beam** | classical CV (`detect_beams`) + YOLO `beam` | `Q.BEAM_STROKE` | yes — duration, stem direction | legacy `<beam>` yes; **staged: no** |
| **flag8th…128th Up/Down** | YOLO | `Q.FLAG` | yes — duration only | as the ABSENCE of `<beam>` |
| **flag…Small** (grace) | YOLO | `Q.FLAG` (gathered) | reaches the table and **gets 0 levels** | — |
| **tremolo1–5** | YOLO | **none of its own** (`Q.ORNAMENT_MARK`) | `ornament_owner` | `<tremolo>` |
| **tuplet3 / tupletBracket** | YOLO | `Q.TUPLET_MARKER` | `tuplet_ratio` | `<time-modification>` |
| **tuplet1,2,4,5,6,7,8,9** | YOLO fires them | **NO quantity** | **none** | **no** |
| **fingering3** | YOLO | read **as** `Q.TUPLET_MARKER` | `tuplet_ratio` | as a tuplet |

### What this dossier builds on, and the one place it disagrees

Four documents already answer part of these five questions and are cited
rather than re-derived:

| document | what it already settles | this dossier |
|---|---|---|
| [`docs/position-grammar-confusables-2026-09-04.md`](../position-grammar-confusables-2026-09-04.md) §2 | Sean's Q1 table **by MARK** — dot, arc, wedge, horizontal stroke, **vertical stroke**, digit, bowl | **agrees on DIGIT, adds BEAM / FLAG / TREMOLO to the alphabet, and DISAGREES with "vertical stroke — already solved" (below)** |
| [`benchmarks/omr-family-positions-2026-09/FINDINGS.md`](../../benchmarks/omr-family-positions-2026-09/FINDINGS.md) + `staged/positions.py` + `staged/capture.py` | the per-family POSITION fact — ten producers, **no consumers**, `OMR_FAMILY_POSITIONS` default OFF | **stem, beam and flag are not among the ten**; tuplet and ornament are |
| `tools/omr/staged/ASSUMPTIONS.md` **A-DUR-1, A-DUR-6, A-DUR-8** | duration is a VERDICT composed from beam / flag / dot / head-class / stem; the two 2026-09-09 attachment faults and their closure | cited at each symbol's Q4 rather than restated |
| [`docs/exploration-what-is-on-the-page-2026-09-09.md`](../exploration-what-is-on-the-page-2026-09-09.md) §5, §6 | *no stem means a whole note* and *no beam between two eighths is metre evidence* — both **absences**, neither consumed | cited at stem Q5 and beam Q3 |

⚠️⚠️ **THE DISAGREEMENT, stated plainly.** The confusables doc heads its
vertical-stroke entry *"stem vs barline (already solved; the precedent)"*, and
on the evidence of the six weeks since it is **not solved on a conductor's
scan**:

* the mechanism it cites — `_spans_system`, *"nothing but a barline runs from
  the top of the upper staff to the bottom of the lower"* — lives in
  `measure_extractor.py:362` and belongs to **barline FINDING**. `detect_stems`
  never consults it. What separates a barline from a stem *inside the stem
  reader* is an 8.0-space height cap and a 0.8-space cell-edge margin, on a
  population that decays smoothly with **no empty interval**.
* **Breitkopf's single largest stem-census bucket IS barlines**: `too TALL` is
  476 heads (31.1%) and the print sample reads it **12 of 12 not a notehead**,
  every one a box 0.40-0.45 sp wide on a vertical rule. MEASURED HERE,
  `omr-stem-crop-pass-2026-09/FINDINGS.md` §2.
* Sean's own endpoint test read **0 of 19** print-settled barlines in the cell
  frame — *"the test is faintly BACKWARDS"* — and only reached 11-13 of 19 once
  a **page-frame** reader was built on 2026-09-20. MEASURED HERE,
  `omr-vertical-runs-page-2026-09/FINDINGS.md` §1.

**The precedent is real and the claim is too strong.** *Classical CV owns both
marks and the model never had to* is correct. *Already solved* describes
**braced keyboard systems**, where a stem crossing the brace gap was the
failure `_spans_system` fixed; it does not describe a 12-staff orchestral page
where a barline enters the stem reader as a candidate and leaves it as a
notehead.

**A probe was used** and it is small: `python3` over the **2,244 committed JSON
artifacts under `benchmarks/`** (hand-labelling and verdict directories
excluded), counting detector rows by class name. It reads committed files only,
runs in a few seconds, and is quoted once per symbol as *"the committed-artefact
scan"*. ⚠️ It is a shape, never a rate — those artefacts are many vintages and
configurations, and the engraved orchestral fixtures are gitignored build
products, so the largest flag and tuplet populations measured elsewhere are
**not** in it.

---

## stem

A near-vertical hairline leaving a notehead at its left or right edge. Read by
the **classical-CV rung** (`tools/omr/line_detection.py:586 detect_stems`),
filed as `Q.STEM` by `gather_cv_lines` (`tools/omr/staged/gather.py:1383`).
The 208-class space **does contain a `stem` class** and the detector's boxes for
it are deliberately unused — Phase 4f moved stems to CV on the ground that YOLO
bounding boxes are structurally bad at thin lines.

### 1. What sets it apart — and what it is confused with

**Start from the mark alphabet.** `docs/position-grammar-confusables-2026-09-04.md`
§2 files this under **VERTICAL STROKE — stem vs barline**, and its
discriminator is *extent*: nothing but a barline runs from the top of the upper
staff to the bottom of the lower. **This dossier agrees with the discriminator
and disagrees with the heading** — see the disagreement block at the top of
this file. What follows is the per-SYMBOL reading that entry does not carry.

**The distinguishing fact is ATTACHMENT, and it is not length.**

- A stem meets a notehead **at one END**, offset about half a notehead width
  from that head's centre — `stemUpSE` at `[1.18, 0.168]`, `stemDownNW` at
  `[0.0, −0.168]` staff spaces. LITERATURE (Bravura `glyphsWithAnchors`;
  Wikipedia *Stem (music)*; registry `[C9 + L10]`).
- **Right-and-up or left-and-down; right-and-down does not exist.**
  **96 of 96 against the print** across two publishers — 67 down-and-left,
  29 up-and-right, **zero** right-and-down. MEASURED HERE
  (`benchmarks/omr-stem-crop-pass-2026-09/FINDINGS.md` §4, n = 96).
  ⚠️ Three tiles appeared to refute it and all three dissolved at 1.8× zoom.
- **Length is refuted as a discriminator.** `Q.STEM` heights run
  **2.16 → 6.78 staff spaces, median 3.93, n = 1,919** — and a barline at 4.00
  sits at the *median*. MEASURED HERE (`tools/omr/staged/record.py:381` comment,
  re-derived; `docs/plan-2026-09-18-what-distinguishes-each-mark.md` §1).
  Gould's 3½ spaces is a DEFAULT the music overrides in both directions.

**What it is confused with, concretely:**

| confused with | where measured |
|---|---|
| **a BARLINE** — thickness cannot separate them (0.12 vs 0.16 sp) | LITERATURE `[L14]`, Bravura `engravingDefaults`. On Breitkopf pp.0-3 `too TALL` is the **largest** census bucket, 476 heads / 31.1%, and it is **12 of 12 not a notehead** in the print sample, every one a box 0.40-0.45 sp wide on a vertical rule. MEASURED HERE, `omr-stem-crop-pass-2026-09/FINDINGS.md` §2 |
| **an ACCIDENTAL's two vertical strokes** — a sharp or a natural is two parallel verticals ~0.5-0.7 sp apart, ~2 sp tall | the premise of `_drop_paired_strokes`. **Measured FALSE as the dominant case** — see Q1's answer to Sean below |
| **a NEIGHBOURING STAFF's ink** through the 4+4-space cell padding | the `at a CELL EDGE` bucket, 70 Litolff / 22 Breitkopf heads; and the page-frame reader shows the cell-frame candidate count (6,128 / 6,816) is ~1.8× the true mark count (3,465 / 4,536) purely by duplication. MEASURED HERE, `omr-vertical-runs-page-2026-09/FINDINGS.md` §3 |
| **a BRACKET or a systemic rule** crossing the crop | the second population "from 10 spaces up to the height of the cell itself". MEASURED HERE, `[C13]` |
| **the two round COUNTERS of a printed time-signature 8**, the `e` of *cresc*, a capital **B**, a whole rest, a bass clef, a trill's wavy line, the white GAP between two thick staff lines | all read off the plate. **46 of 180 boxes the record calls a notehead are not noteheads** — 15.6% Litolff, 35.6% Breitkopf. MEASURED HERE, `omr-stem-crop-pass-2026-09/FINDINGS.md` §2, §5 |
| **ANOTHER STEM** — two fused into one component | 17 of 4,225 runs overshoot at both ends; ceiling **13 noteheads of 5,684 (0.23%)**; of 13 crops opened, **one** is the fault, and the Litolff rate **inverts** (6 of 6 opened are not fused). MEASURED HERE, `omr-stem-run-split-2026-09/FINDINGS.md` |

**The one asymmetry a single stem cannot produce:** a stem STARTS at its
notehead, so it can overshoot the outer heads at **one** end only. Overshoot at
**both** ends is two fused stems. MEASURED HERE
(`docs/conventions/stem-exception-space-2026-09.md` §2.1a; 50% of flagged runs
Breitkopf, 18% Litolff).

#### Sean's open question: should an accidental's vertical stroke be in the stem veto's domain at all?

**There are two different "stem vetoes" and the answer differs.**

**(a) `_drop_paired_strokes`, the shipped pair rule** — drops BOTH members of
any pair of verticals whose centres are within 0.9 sp and which overlap
vertically by ≥0.6 of the shorter. An accidental is in its domain *by design*.
The gate lane's answer is that **the domain is right and the ACTION is wrong**:

- of the 244 strokes the rule deletes on Litolff pp.1-4, **80 carry a detected
  notehead, and 62 of those 80 (77.5%) were paired with ANOTHER stroke that
  also carries one** — two genuine stems eating each other. **73 of the 793
  stemless heads (9.2%)** would stop abstaining without the rule. MEASURED
  HERE, `omr-stem-pair-rule-2026-09/FINDINGS.md` §2/§2a, reproduced to the unit
  in `omr-stem-notehead-gate-2026-09/FINDINGS.md` §0.
- **Geometry cannot narrow it.** Over 36 stem pairs against 94 accidental
  pairs, the best single feature separates at **0.823** against a **0.723**
  majority baseline, with **no empty interval anywhere** — centre-dx clusters at
  0.56-0.70 sp for all three shapes. A cut read off that table is a constant
  fitted to one plate. MEASURED HERE, same file §3b.
- ⚠️⚠️ **And the fixture that justified the rule PRINTS NO ACCIDENTAL AT ALL.**
  `benchmarks/omr-phase4-lines/reference-lines.ly` is plain C and G major —
  zero sharps, flats or naturals in 48 stems — so the cited win
  (*"+7/+8/+5/+2 to −1/0/+1/0"*) was never a measurement of accidental
  rejection. All 28 of its deletions fall in **one bar** and **28 of 28 stand
  on a notehead**; read at its own per-bar resolution the shipped rule
  **EMPTIES a bar of four chords** (truth 4, rule ON 0). MEASURED HERE,
  `omr-stem-notehead-gate-2026-09/FINDINGS.md` §5, §5a-§5d, crop cut.

  **So: yes, an accidental belongs in that rule's domain — but the rule has
  never been scored on a page that prints one.** `OMR_STEM_NOTEHEAD_GATE`
  (default OFF) keeps the domain and narrows the action to *a stroke that meets
  a notehead is a stem and is kept*, which is exactly the property an
  accidental's stroke does not have. Its cost is +80 / +152 strokes, all on a
  head, **0 lost**, 73 and 178 heads stop abstaining — and +5 on the rule's own
  hand cells.

**(b) The EVALUATE veto the forward plan proposes** — *no head at either end ⇒
NOT a stem*. There the answer is **no, and the surprise is diagnostic**: it
fired on **24 accidentals, clefs and rests of 33** while the whole thread had
framed it against barlines, *because the pipeline has no category for "a
vertical line that is not a stem."* MEASURED HERE, plan §7.
An accidental's stroke belongs in the domain of the question **"what kind of
vertical mark is this?"** and does not belong in the domain of a rule whose only
two outcomes are *stem* and *deleted*. **Today only the second exists.**
`Q.VERTICAL_RUN` is exactly the first and is **producer-only, read by nothing**
(`tools/omr/staged/reach.py:88`).

### 2. Best method: YOLO / CV / other

**Classical CV, and the decision is Phase 4f's and stands** — a YOLO box cannot
bound a hairline. But the CV rung is a **connected-component** reader, and that
is where it breaks:

| | Litolff Beethoven 5 pp.1-4 | Breitkopf Brahms 1 pp.0-3 |
|---|--:|--:|
| noteheads | 2,347 | 3,337 |
| `Q.STEM` strokes | 1,920 | 2,305 |
| **heads with NO stem** | **793 (33.8%)** | **1,529 (45.8%)** |
| vertical marks on the page (page frame) | 3,465 | 4,536 |

MEASURED HERE (`omr-stem-notehead-gate-2026-09/out/*.json`;
`omr-vertical-runs-page-2026-09/FINDINGS.md` §3).

**What it reads badly, and on which plate.** The whole 793 attributes exactly,
with no residue bucket:

| why the head has no stem | Litolff | Breitkopf |
|---|--:|--:|
| **too WIDE** (w > 0.6 sp) — the notehead is still joined to its stem | **237** | 358 |
| **too SHORT** (h < 2.0 sp) | 199 | 298 |
| **no component overlaps it at all** | 167 | 197 |
| dropped by the pair rule | 73 | 178 |
| at a CELL EDGE (0.8 sp) | 70 | 22 |
| **too TALL** (h > 8.0 sp) | 47 | **476** |

MEASURED HERE (`omr-stem-ink-2026-09/FINDINGS.md` §G1, sums to 793 exactly;
Breitkopf column from `omr-stem-crop-pass-2026-09/FINDINGS.md`'s census).

**The two plates fail for opposite reasons and must never be pooled.**
**Litolff MERGES**: one spot-checked cell's opening yields 3 components of
median height 811 px in a cell whose staff spacing is 100 px — **8.1 staff
spaces, one blob holding stems, beams and noteheads together** — which is why
its largest bucket is `too WIDE`. **Breitkopf's largest bucket is BARLINES.**
MEASURED HERE (`omr-stem-ink-2026-09/FINDINGS.md` §G4; crop pass §2).

⚠️ **Three repairs were tried on the CV rung and all three are dead**: reading
the ORIGINAL image instead of the erased one recovers **fewer** (268 vs 287 of
793); horizontal pre-dilation at 1/2/3/5 px buys **four heads**; and two of the
six filters (**ASPECT** and **AREA**) **cannot fire at the shipped defaults** —
zero over 12,944 real candidates, by arithmetic, though every document
describing the chain calls it six filters. MEASURED HERE
(`omr-stem-ink-2026-09/FINDINGS.md` §G2/§G3;
`omr-vertical-runs-2026-09/FINDINGS.md` §5).

**What works is a reader that finds the stroke INSIDE the blob.**
`OMR_STEM_STROKE` (default OFF) reads a column profile rather than a component
and recovers **92.1% / 73.6%** of the strokes; its recovered strokes agree with
right-up/left-down at **82.6% / 96.3%** against a 0.506 baseline. MEASURED HERE
(`omr-stem-stroke-2026-09/FINDINGS.md`).

**And the width cap's discards are real ink, not junk: 33 of 33** against the
print (Litolff 9/9, Breitkopf 24/24, one-sided 95% lower bound 0.913). It
recovers **217 heads on Litolff and 345 on Breitkopf**. ⚠️ That removes the
junk worry; it does **not** price the cap, because the print settles only 33 of
55 and that subset is by construction the legible one. MEASURED HERE (crop pass
§3).

### 3. Where on the page the deciding information lives

Four places, in descending order of how decisive they are:

1. **At the notehead's left or right EDGE**, half a head width off its centre,
   at the stroke's own END. This is the fact; everything else is corroboration.
2. **At the stroke's FAR end** — a flag hangs there, a beam joins there.
3. **At the stroke's TWO ends against the staff's outer lines.** Sean's barline
   test. ⚠️⚠️ **It was unavailable for the wrong reason and is now available.**
   `Q.STEM` is CELL-canonical with **no page coordinates at all** while
   `Q.STAFF_LINES` is page pixels, so the two could not be compared. Read in the
   PAGE frame the test fires on **11-13 of 19** print-settled barlines at
   0.25-0.60 staff spaces and on **0 of 63** print-settled stems — where in the
   cell frame it read **0 and 0**. **The measure cell was clipping the ends.**
   MEASURED HERE, `omr-vertical-runs-page-2026-09/FINDINGS.md` §1. ⚠️ The
   barline half is circular (its sample was drawn from the `too TALL` bucket);
   **the stem column is not**, and it is the decisive one.
4. **How many staves the run spans** — a quantity a cell frame cannot express at
   all. Litolff 2,773 runs span one staff, 274 span 2-4, 16 span 11-12;
   Breitkopf 3,931 / 10 / 7 at 13-14. The long ones land on exactly the staff
   counts those pages' systems have. MEASURED HERE, same file §3.
   ⚠️ **Not proposed as a rule** — nothing there says a run spanning a system is
   a barline rather than a bracket.

⚠️⚠️ **THE STEM HAS NO FAMILY-POSITION QUANTITY, AND THE GRADING TOOL SAYS SO
IN ITS OWN WORDS.** `positions.py`'s ten position facts are rest, time, tuplet,
articulation, fermata, ornament, arc, dynamic, wedge and direction — **stem,
beam and flag are not among them** — and `capture.py` grades `STEM` under
`RAW_INK` rather than in the notation-family table, with the entry:
*"its endpoints ARE a staff-grid measurement waiting to be made: a stem runs
from its notehead to a beam, so `y0`/`y1` against the grid would say which.
**Nothing converts them.**"* (`capture.py:350`). Its sibling `VERTICAL_RUN`
entry answers exactly that half — those rows carry the endpoints **in page
pixels**, the frame `Q.STAFF_LINES` is in — and then declines to put a
staff-grid position on the gather row, *"because putting it on the gather row
would put the decision in GATHER"* (`capture.py:360`).

⚠️ **A DISAGREEMENT INSIDE THE TREE, found here.** That `capture.py:352` entry
spells a stem's value **`x`, `y0`, `y1`**. `record.py:381-395` records that
spelling as **WRONG** — the value is `[x, y, w, h]`, verified against the
record on **400 of 400 rows** (`detail.x0 == value[0]`,
`detail.x1 - detail.x0 == value[2]`) — and names it the **third
mutually-disagreeing box convention in one record**, the one that *"gives a
NEGATIVE width and a clean believable zero"* and cost
`omr-ink-extent-2026-09` an entire run. The prose in the grading tool still
carries the convention the vocabulary records as refuted. **Derived from the
tree, 2026-09-20.**

⚠️ And Sean's own caution about this class of fact, from the family-positions
brief: *"position is an option for helping us determine something but will
rarely be a clear rule that determines by itself."*

### 4. Stage by stage

| stage | what happens | where |
|---|---|---|
| **GATHER** | `detect_stems` opens the ERASED cell image with a `(1, 1.6 spaces)` kernel, takes connected components, applies six filters then the pair rule, and `gather_cv_lines` files **only the survivors** as `Q.STEM` `[x, y, w, h]` CANONICAL | `line_detection.py:586`; `gather.py:1465` |
| | ⚠️⚠️ **A cell whose every candidate was REFUSED is recorded `ABSTAIN.NO_INK`** — *"no ink"* for a page that holds ink. The collapse Sean named unprompted | `gather.py:1465-1470` |
| | `Q.VERTICAL_RUN` (`OMR_VERTICAL_RUNS`, default OFF) files every candidate accepted **or refused**, with which filter refused it and its page box | `gather.py:1263`, `record.py:455` |
| **ADJUDICATE** | `Q.STEM_DIRECTION` (ORDER 17) — `adjudicate_stem_direction`, reasons `stem_projection` / `beam_mate` / `no_stem` / `stems_disagree` / `no_evidence` | `adjudicators/rhythm.py:2814` |
| | `Q.DURATION` reads `Q.STEM` to join a head to its beam by its STEM | `rhythm.py:482`, `_stem_joined` at `:164` |
| | `Q.EVENT`'s divisi guard reads `Q.STEM_DIRECTION` | `rhythm.py:846` |
| | `Q.VOICES` reads `Q.STEM_DIRECTION` | `rhythm.py:3198` |
| | `Q.ARC_OWNER` declares and reads `Q.STEM` | `adjudicators/ownership.py:674` |
| **EVALUATE** | nothing reads a stem. `reconcile_duration` re-reads a *beam level*, not a stem | `consequences.py:233` |
| **INFER** | nothing. Its three rules target `Q.DURATION` and `Q.SLOT_INDEX` | `inferences.py` |
| **EXPORT** | `_stem_probes` converts `Q.STEM` to page pixels **through the head as its own ruler**, because the row carries no page box — used for ARC reach, not for a stem element | `staged/export.py:941`, `:960` |
| | ⚠️ **`<stem>up/down</stem>` is never written by either exporter.** `export_coverage.KNOWN_GAPS["stem"]`: *"truth-visible and musicdiff does not score it, so it costs nothing today — which is why it stayed invisible to every forensic hunt"*, and it is named there as the **largest single open item** on that list | `tools/omr/export_coverage.py:442` |

⚠️ `ASSUMPTIONS.md` **A-DUR-1** is the governing statement of why a stem is in
this chain at all: *"a duration is COMPOSED from marks; the marks are
measurements, the value is not"*, and `Q.STEM` is one of the five it names.
**A-DUR-8** records the fault and its closure — `Q.STEM` *"declared in `wants`
and `composed_from`, carried a `KNOWN_GAPS` entry, and read by nothing"*, 916
rows on a three-page record.

⚠️ **No convention in the registry's "Stems & beams" category is declared by any
decision — 18 of 18.** MEASURED HERE, `omr-convention-coverage-2026-09/FINDINGS.md`
§4, re-derived here with `tools/omr/conventions.py`.

### 5. Abstain or best-guess — and what leans on this mark's certainty

**(a) Can it abstain, and does it?** `Q.STEM` itself is **not a decision** — it
is an observation, and a candidate the six filters refuse produces **no row at
all**. So the honest answer is: *the question "is this ink a stem?" is never
asked of a stage, and therefore cannot abstain.* What abstains is the decision
one layer down, `Q.STEM_DIRECTION`, and it abstains well and in two distinct
words: **`no_stem`** (nothing meets this head — ordinary; a whole note has none)
and **`stems_disagree`** (two stems meet it and point opposite ways — a warning).
On Litolff pp.1-4: `stem_projection` 1,443, `no_stem` 793, `stems_disagree` 111.
MEASURED HERE, `omr-stem-direction-2026-09/FINDINGS.md` §1.

⚠️ **THE ABSENCE IS EVIDENCE AND NOTHING READS IT.**
`docs/exploration-what-is-on-the-page-2026-09-09.md` §5: *"No stem means a
whole note. Absence-of-stem is positive evidence for duration, and the duration
decision consumes stems and beams as things that are THERE."* Registry `[C15]`,
status **ASSERTED, no figure**. The obstacle is named in its own *known
exceptions*: **a head whose stem the CV rung simply missed is indistinguishable
from a genuinely stemless one** — which on these two plates is 793 and 1,529
heads.

⚠️ **9 of the 793 are whole notes and those abstentions are the decision being
RIGHT.** Half notes get a stem 309 times against 103 that do not, so those 103
are misses and not convention. Same file.

**(b) What leans on it, and does it fail on the same pages?**

- **Beams lean on stems DIRECTLY, not independently.** `detect_beams` takes the
  stem list as its input and keeps only components that **≥2 stems end at**
  (`min_attached_stems = 2`). Measured consequence: turning the notehead gate on
  moves the stem set and CV beams move with it, **322 → 337 (Litolff), 412 → 444
  (Breitkopf)**, with no beam rule touched. MEASURED HERE, gate FINDINGS §3.
  **So the beam reader is not a second witness over the stem reader; it is
  downstream of it.**
- **Duration leans on beams, therefore on stems.** `adjudicate_duration`'s own
  docstring calls the beam level its fragile input.
- **Chord grouping and voices lean on stem DIRECTION.** The divisi guard is
  live only where a direction was decided, and it reports
  `divisi_guard: no_direction_decided` otherwise rather than reading as a clean
  bill.
- **The beam-mate tier is the second tier of stem direction and it is a BEAM
  fact** — so on a page whose beams fail, both tiers fail together.
  ⚠️⚠️ **And the print scored it: of the 26 Breitkopf heads where the attachment
  convention and the shipped beam-mate tier disagree, the print settles 16 and
  agrees with ATTACHMENT 16-0.** MEASURED HERE, crop pass §1, blind protocol.
  ⚠️ The adjudicating eye is **not** independent of the attachment reader (it
  measures ink beside the head, and so does the convention), so the honest
  reading is *"the ink beside the head behaves as the convention says"*.
- ⚠️ **The genuinely independent anchor is the NOTEHEAD, and it has been
  checked**: on Brahms p2 notehead recall is 0.980 while half the stems are
  missing, so they demonstrably do not fail together. MEASURED HERE,
  plan §9.5. **But the notehead fault is PRECISION** — 46 of 180 boxes are not
  noteheads — and a precision fault in an anchor has not been thought through.
- ⚠️ **`OMR_STEM_NOTEHEAD_GATE`'s standing objection is exactly this**: the gate
  COUPLES `Q.STEM` to the detector, so a rung that is today an independent
  reader of the ink stops being one, and it is weakest precisely where stems are
  most often missed.

**Evidence grade:** attachment convention **MEASURED HERE** (96/96 print, n=96)
and **LITERATURE** (`[C9+L10]`); length **MEASURED HERE** and refuted as a
discriminator (n=1,919); pair-rule premise **MEASURED HERE** and refuted
(n=244/80/62); barline endpoint test **MEASURED HERE** in the page frame
(n=19 barlines / 63 stems, both scans); `[L12]`/`[L13]`/`[L14]`/`[L15]`/`[L17]`
/`[L18]`/`[L19]` **LITERATURE ONLY, untested here**.

---

## beam

A thick horizontal stroke joining the tips of two or more stems. Two readers
produce it and both file **`Q.BEAM_STROKE`**: the classical-CV rung
(`line_detection.py:1043 detect_beams`, reader `CV_LINES`, on the ERASED image)
and the YOLO class **`beam`** (`gather_detector_beams`, `gather.py:1738`,
reader `DETECTOR`, on the ORIGINAL image).

### 1. What sets it apart — and what it is confused with

**The mark alphabet has no BEAM entry, and this is the addition.** The
confusables doc's nearest neighbour is **HORIZONTAL STROKE — tenuto vs ledger
line**, whose roles are a tenuto and a ledger line. A beam is a third role of
the same mark, and a **hairpin limb** is a fourth (measured below). ⚠️ That
matters because the doc's ledger-line discriminator — *lies ON the extended
half-space lattice, matches the staff's own measured line thickness* — is
exactly what separates a ledger line from a beam too, and a beam is **thicker
than a staff line by ~4×** (Bravura `beamThickness` 0.5 against
`staffLineThickness` 0.13). **Nothing in this pipeline uses thickness to
separate them**; `detect_beams` uses *how many stems END at it*.

- **It runs from the FIRST stem it joins to the LAST**, and a note belongs to it
  **via its STEM, not via its notehead centre**. The outer note of every beamed
  group has its head centre roughly half a notehead width past the stroke's end
  — measured overshoot **0.35-0.47 notehead widths**, which is the stem offset
  and nothing else. MEASURED HERE, `[C12]`,
  `omr-staged-duration-beams-2026-09/FINDINGS.md`, n = 114 narrowed durations.
- **Stacked beams sit 0.75 staff spaces centre to centre** (stroke 0.5 + gap
  0.25). The two sources agree to the number, and the measured population is
  bimodal with a genuine **EMPTY INTERVAL**: **0.19-0.26 sp, 460 pairs — one
  physical beam, fragmented**, against **0.65-0.79 sp, 69 pairs — genuinely
  stacked**. LITERATURE (Bravura `beamThickness` 0.5 / `beamSpacing` 0.25;
  LilyPond `beam-thickness 0.48`) **and MEASURED HERE** (`[C79 + L20]`;
  `tools/omr/rhythm.py:131 BEAM_Y_CLUSTER_FACTOR = 0.35`).
  ⚠️ Corollary the stroke lane took as a prohibition: **the gap is NARROWER
  than the stroke, so an erosion tuned to open the gaps eats the strokes first.**
- **A beam joins stem TIPS, so every stem on one stroke points the same way.**
  MEASURED HERE, `[C11]`, beam-mate unanimous 0.984 at reach 152.

**Confused with, concretely** — and the list is why `min_attached_stems = 2`
exists: **slurs, ties, ledger lines and staff-line residue**. Without the
two-stem-ends requirement the reference sheet reported **51 beam bars against a
known 14, and 41 against a known 12 on one staff**; with it, summed error over
four staff-line thicknesses falls **157 → 3**, and it holds down to a 150 dpi
render. MEASURED HERE, `line_detection.py:1056` docstring,
`benchmarks/omr-phase4-lines`.

⚠️ Also confused with: **a HAIRPIN's ink.** Brahms 1 Contrabass m4 — a spurious
685 px "beam" at the real beams' own y spanned the whole bar and swallowed six
notes into one run where the page prints two groups of three. MEASURED HERE,
`omr-beam-gap-2026-09/FINDINGS.md`.

### 2. Best method: YOLO / CV / other

**Both, kept apart, and the arbitration is the ADJUDICATOR's.** This is the one
symbol in the family where the two methods are genuinely combined and the
combination was measured three ways.

⚠️ **A YOLO beam box bounds the STACK, not a stroke.** A box over two strokes
contributes a centre in the GAP between them, the run then has no gap wide
enough to cluster, and **three sixteenths read as three eighths** (Brahms
Violin 2: CV strokes at canonical y 1112 and 1172, 60 px apart against a 35 px
tolerance — two levels — and the YOLO box adds 1142 between them).

| arm | pooled OMR-NED | note |
|---|--:|---|
| union (Phase 4f) | 0.1917 | destroys the bimodality |
| **kept — a YOLO beam only where no CV stroke overlaps in x** | **0.1861** | shipped |
| replace CV outright | 0.1855 | **REFUSED**: the only arm that regresses an authored fixture; notes losing every beam go 4 → 7 |

MEASURED HERE, `_kept_beams` at `adjudicators/rhythm.py:67`; CLAUDE.md
*Durations: two units*.

⚠️ **And erasing the staff lines for YOLO MANUFACTURES beam confusion**: YOLO
beams **46 → 105 at precision 0.783 → 0.343**, firing on staff-line residue.
MEASURED HERE (`gather_cv_lines` docstring; the erasure arm, n = 2 engraved
works). **So the two readers see different images on purpose, and every
`Q.BEAM_STROKE` row records which.**

⚠️⚠️ **The CV rung reads the STACK COUNT from vertical ink runs, not from box
height, and where it can it also returns each bar's BAND.** Over 2,124
components on 31 pages, **51 read more than one bar — every one on a scan,
every one a two-bar stack**; the fabricated evenly-divided band sat a median
0.106 sp from the measured one and **18 of 102 bar placements were displaced
past the 0.35-space clustering tolerance**. Through the pipeline that changes
**55 durations on 9 scan pages** (42 longer, 13 shorter, no pitch moves),
priced at **−37 edits** on the 20-row scan gate, of which −43 is attributable.
MEASURED HERE, `omr-beam-bar-bands-2026-09`, `line_detection.py:_stacked_bar_bands`.
⚠️ Its own two-sided cost: an excursion band is right for the EDGE test and poor
for the CENTRE, flipping **4 of the 51** from two levels to one.

### 3. Where on the page the deciding information lives

- **At the stem TIPS.** The stroke's two x-ends are stems, and that is the whole
  of the grouping question.
- **In the VERTICAL INK RUNS through the stroke's own columns** — how many bars
  are stacked, and where each sits. Not in the box's height.
- **In the 0.75-space pitch** between stacked bars — the one constant in this
  family that sits in a measured empty interval rather than on a plateau.
- ⚠️ **NOT in the beam's slope**, today. `[L21]` — the beam is angled by the
  OUTER interval, horizontal in three named cases — predicts the pitch relation
  of a group's outer notes **with no notehead reading at all**, which is the
  scarce kind of witness. LITERATURE ONLY; **no consumer found.**
- ⚠️ **NOT in where the beam sits relative to the bar**, today. `[L22]`
  (beaming follows the metre) is a metre signal readable from geometry with no
  duration arithmetic — and **Gould explicitly records the rule is NOT
  historical for Classical and Romantic repertoire**, which is this project's
  whole corpus. LITERATURE ONLY; no consumer.
  ⚠️ Two other documents ask for the same thing from the other side and both
  record it unbuilt: `ASSUMPTIONS.md` **A-DUR-6 item 6** — *"beat subdivision
  agrees with the meter: ❌ not built; beams are gathered, grouping is not
  read"* — and the exploration doc §6 — *"No beam between two eighths … Beaming
  is meter evidence the meter vote does not consult."*

⚠️ **THE BEAM HAS NO FAMILY-POSITION QUANTITY EITHER**, and unlike the stem it
has no `RAW_INK` entry of its own in `capture.py` — only the reader mapping
`CV_LINES → line_detection.detect_beams` (`capture.py:518`) and a note that
`Q.BEAM_STROKE` is one of two quantities that *"record a runtime fact"*
(`:1956`). It is absent from `capture --check`'s family table, which lists
articulation, clef, direction, dynamic, fermata, key, note, ornament, rest,
slur, tie, time, tuplet and wedge. **Run here, 2026-09-20.**

### 4. Stage by stage

| stage | what happens | where |
|---|---|---|
| **GATHER** | CV: horizontal opening at 1.5 spaces → components filtered on width/height/aspect → **kept only where ≥2 stems END at them** → bar count and bands from vertical ink runs. Filed `Q.BEAM_STROKE` `[x,y,w,h]` canonical, with `image` and `staff_lines_erased` | `line_detection.py:1043`; `gather.py:1465` |
| | YOLO: every `beam` detection filed as `Q.BEAM_STROKE`, reader `DETECTOR`, `image: original` | `gather.py:1738` |
| | ⚠️ **These are STROKES, not LEVELS** — deliberately. Emitting a level here would put the arbitration in the gathering phase | `gather_cv_lines` docstring |
| **ADJUDICATE** | `_kept_beams` keeps CV strokes plus YOLO boxes no CV stroke explains in x | `rhythm.py:67` |
| | `_stem_joined` joins a head to a stroke **through its own stem**; `_beam_levels` returns **(CERTAIN, POSSIBLE)** — a RANGE, because the reading is a range | `rhythm.py:164`, `:366` |
| | a range becomes `Ruling.narrow(...)`, reason `beams_ambiguous`, candidates ordered by SUPPORT (2.0 for the certain level, 1.0 for the rest) | `rhythm.py:557` |
| | `_direction_from_a_beam_mate` borrows a direction across a shared stroke — reason **`beam_mate`**, unanimity only | `rhythm.py:2765` |
| **EVALUATE** | `reconcile_duration` re-reads **one** note's beam level, only among the levels its own candidates ADMIT, only where the landing is UNIQUE, never a rest, once | `consequences.py:233` |
| **INFER** | `collapse_duration_by_column` and `collapse_duration_to_barline` target the NARROWED population. **`OMR_INFER` is default OFF** | `inferences.py:287`, `:375` |
| **EXPORT** | legacy `annotate_beams` writes `<beam number=N>` — `wrong flag/beam` **449 → 31**, pooled **2,745 → 2,473** | `tools/omr/export.py:1295` |
| | ⚠️⚠️ **the STAGED exporter writes NO `<beam>` element at all** — `grep '<beam' tools/omr/staged/export.py` is **0**, `beam_states` is never passed to `_mxl_note`, and there is no beam counter. In MusicXML the absence of `<beam>` IS a flag, so **on the staged path every beamed note comes out flagged.** It is not on the staged `KNOWN_GAPS`; `NOT_NOTATION["beam"]` reads *"consumed by `duration` as a beam stroke"*, which is true of the LEVEL and not of the ELEMENT | `staged/export.py:2446`, `:2969` |

⚠️ `ASSUMPTIONS.md` **A-DUR-8** is the record of the stem-joining repair and
its two figures (assessable bars 12 → 14 → 16, correct 7 → 10 → 16;
`narrowed` 147 → 29), and it carries the instruction that goes with them:
**do not tune `METER_CARRY_FLOOR` or `METER_FROM_BARS_FLOOR` against this** —
that is fitting a constant to a broken input.

### 5. Abstain or best-guess — and what leans on this mark's certainty

**(a) Yes, and it is the clearest abstention in the family.** `adjudicate_duration`
distinguishes **three** states and the docstring says why they must not
collapse: `reader_declined` (the CV rung abstained), `read` (levels found), and
`none_over_this_note` (the rung ran and no stroke covers this head). Where the
level is a range it **narrows rather than decides**, and `export.py` refuses to
argmax a narrowed duration even though the candidates carry support.

**(b) What leans on it.**

- **Duration**, which is the largest consumer in the project.
- **Stem direction**, through the beam-mate tier.
- **Meter**, at one remove: bar sums are the most-cited constraint in the
  pipeline and are built from durations built from beam levels.
- **Tuplets**, on the legacy path: `_tuplet_groups` takes a group's EXTENT from
  the beam box, padded by a notehead width. ⚠️ **On the staged path it does
  not** — `adjudicate_tuplet` declares `Q.BEAM_STROKE` and never reads it
  (see the tuplet section).

⚠️⚠️ **The independence check FAILS here, structurally.** `detect_beams` takes
the stems as input, so beams and stems are one witness, not two — and the CV
duration and the meter that arbitrates it both come off the same rung. This is
the repo's own *"the bars are not an independent umpire over a bad reading"*
in its sharpest local form: on a page whose beams are mis-read, the bar sums
that would catch it are built from those same beams.

⚠️ **The one genuinely independent cross-check in this family is the
flag/beam contradiction** — see the flag section — because there the two
witnesses are the CV beam rung and the YOLO flag class, different readers on
different images.

**Evidence grade:** stacked-beam pitch **LITERATURE** + **MEASURED HERE**
(empty interval, n = 529 pairs); stem-tip joining **MEASURED HERE** (n = 114,
engraved fixture 12/7 → 16/16); YOLO-kept arbitration **MEASURED HERE**
(pooled 0.1917 / 0.1861 / 0.1855, 11 works); `min_attached_stems` **MEASURED
HERE** (157 → 3, reference sheet); slope and metre rules **LITERATURE ONLY**.

---

## flag8thUp / flag8thDown / flag16th / flag32nd / flag64th / flag128th (+ `…Small`)

The hook or hooks drawn on the far end of an unbeamed note's stem. Twelve
classes in the 208-class space: `flag{8th,16th,32nd,64th,128th}{Up,Down}` plus
**`flag8thUpSmall`** and **`flag8thDownSmall`** (grace sizes; there is no
`flag16thUpSmall`). Gathered by prefix as **`Q.FLAG`**
(`gather.py:718`, `_FLAG_PREFIX = "flag"`).

### 1. What sets it apart — and what it is confused with

**The mark alphabet has no FLAG entry either.** A flag is a hook — closest to
the doc's **ARC** family in shape and to nothing in it in role. Added here, and
the reason it belongs: *a flag is the only mark in this family whose identity is
settled by an ABSENCE elsewhere* (no beam over this head), which is the
"matches no grammatical position" dividend the confusables doc's §1 names, used
in the opposite direction.

- **A flag NAMES A VALUE; it is not a tally.** One `flag16thUp` is ONE glyph
  with TWO hooks. The bug was `levels = len(flags)`, which read a sixteenth as
  an eighth; `_FLAG_LEVELS` is now **derived** from `rhythm._FLAG_DURATIONS`
  rather than restated, and the combination rule is **MAX, not SUM** — two flag
  detections on one stem are two readings of one glyph. MEASURED HERE, `[C80]`,
  `adjudicators/rhythm.py:206-216`, `:275`.
- **It hangs on the STEM, about 3.5 staff spaces from the head** — not on the
  notehead. LITERATURE: Gould p.15, tail **2½-3¼ staff spaces (3-3¼ the norm)**;
  Bravura `flag8thUp` bbox **1.056 × 3.276 sp** with `stemUpNW` at `[0.0, −0.04]`;
  SMuFL registration *"y=0 is the end of a stem of normal length, x=0 the
  left-hand side of the stem"*.
  ⚠️ **But a down-stemmed note's tail may curve as far as to touch the
  notehead**, so a flag's INK can reach the head even though its attachment does
  not. LITERATURE, Gould.
- **The HARD contradiction: a note under a beam carries no flag.** A notehead
  with a beam level AND a flag on its stem is one of the two readings being
  wrong — a **truth-free probe**, which is rare. Rate: **engraved 3 of 112
  flagged notes (2.7%), Litolff scan 7 of 37 (18.9%), Breitkopf 27.5%** —
  ordered engraved < Litolff < Breitkopf, i.e. **the worse the ink, the more
  the flag half picks up.** MEASURED HERE,
  `omr-staged-duration-beams-2026-09/FINDINGS.md`. **No gate was added.**

**Confused with:** a **slur or tie edge**, another staff's ink through the cell
padding, and — the measured case — **a beam**, in the contradiction above.

### 2. Best method: YOLO / CV / other

**YOLO, and it reads the EIGHTH flag and almost nothing else.**
Committed-artefact scan, 2,244 files under `benchmarks/` excluding labelling and
verdict directories:

| class | rows |
|---|--:|
| `flag8thDown` | 470 |
| `flag8thUp` | 200 |
| `flag16thUp` | 16 |
| `flag16thDown` | 3 |
| `flag64thUp` | 1 |
| `flag32ndUp/Down`, `flag128thUp/Down` | **0** |
| `flag8thUpSmall`, `flag8thDownSmall` | **0** (they appear only in HAND-LABELLED verdicts and the training corpus) |

**PROBE, this dossier.** Eighth flags are **96.0%** of every flag row in the
scan. ⚠️ A shape, not a rate — the engraved orchestral fixtures are gitignored.

**Reach per plate, from the committed measurements:**

| | flag boxes | aug. dots | noteheads |
|---|--:|--:|--:|
| engraved `beethoven-sym5-mvt4` m203-218, 23 parts | **134** | 157 | 1,118 |
| Litolff Beethoven 5 pp.1-4 (*low-res bitonal*) | **49** | 35 | 2,347 |
| Breitkopf Brahms 1 pp.0-3 | **371** | 656 | 3,337 |

MEASURED HERE, `omr-staged-duration-beams-2026-09/FINDINGS.md`; CLAUDE.md
*A MARK must be attached to its notehead*.

**What that buys.** On the engraved fixture the marks half is worth the bars
going right. On **Litolff the marks half is worth exactly ZERO** (per-staff
readings 401 → 401) — **not because the rule fails but because 49 boxes over
2,347 heads is a DETECTION limit**. On **Breitkopf the same half is worth +13
alone and the two halves are SUPER-ADDITIVE: +15 and +13 separately, +66
together**, because a bar is right only when every note in it is. MEASURED
HERE, same file. ⚠️ **Read every "on a scan" claim about flags as "on THAT
scan".**

### 3. Where on the page the deciding information lives

- **On the STEM, at its far end.** This is the attachment, and on the staged
  path it beats the legacy rule outright: `rhythm._flag_for_notehead` matches on
  **x-centre proximity** and says in its own docstring that it cannot use the
  stem because *"the notehead's stem direction isn't reliably available from a
  0-stem detector"* — **stale, since `gather_cv_lines` reads 916 stems.**
- **In the CLASS NAME.** The number of hooks is in the name, not in the ink's
  extent, and no reader measures hooks.
- **In the presence of a BEAM over the same head** — the contradiction above.
- ⚠️ **Not in the flag's y-extent**: nothing measures how far down the stem the
  ink reaches, so the 2½-3¼ space tail is LITERATURE with no consumer.
- ⚠️ **And there is no `Q.FLAG_POSITION`.** `positions.py`'s ten do not include
  one, and `capture --check`'s family table has no `flag` row. So the one fact
  that would separate a flag from a slur edge — *it stands at the far end of a
  stem, 3.5 spaces from the head* — is expressible only as the stem-overlap
  test the adjudicator already does, and never as a measurement.

### 4. Stage by stage

| stage | what happens | where |
|---|---|---|
| **GATHER** | any class starting `flag` → `Q.FLAG`, value = the class name, on the **FLAG's own glyph subject**, with `score`, `x_center`, `y_center` | `gather.py:713-721` |
| **ADJUDICATE** | `_attached_flags` claims a flag only where its box overlaps a stem that overlaps THIS head; levels via `_FLAG_LEVELS`, combined with **max** | `rhythm.py:232-282` |
| | `adjudicate_duration` uses a flag **only when no beam level was found** — `beam_evidence = "flag"` | `rhythm.py:522-527` |
| | ⚠️⚠️ **THE HISTORICAL FAULT, `ASSUMPTIONS.md` A-DUR-8's second half**: `Q.FLAG` is gathered on the FLAG's glyph and was read on the NOTEHEAD's, so **not one of 134 rows ever reached a duration** and `beam_evidence == "flag"` fired **ZERO** times. Repaired: **112 flags attached, 109 deciding** | `rhythm.py:237` |
| **EVALUATE / INFER** | nothing reads `Q.FLAG` | — |
| **EXPORT** | there is no `<flag>` element in MusicXML: **the absence of `<beam>` IS the flag.** So the legacy exporter expresses flags correctly by writing beams, and the **staged exporter — which writes no `<beam>` — expresses every note as flagged** | `tools/omr/export.py:1099`; `staged/export.py` |

⚠️ **A GRACE FLAG IS GATHERED AND SILENTLY WORTH NOTHING.** `flag8thUpSmall`
matches the `flag` prefix, so it becomes a `Q.FLAG` row and can be attached —
but `_FLAG_DURATIONS` holds no `*Small` key, so `_flag_levels_for` returns
`None`, the `max()` skips it, and the note keeps its head value. **Derived from
the tree** (`rhythm.py:85-96`, `:174`; `adjudicators/rhythm.py:206`), **reach
unmeasured — 0 rows in the committed-artefact scan.** It is a gap that costs
nothing today and would cost silently the day the detector fires one.

### 5. Abstain or best-guess — and what leans on this mark's certainty

**(a)** There is no `Q.FLAG` decision to abstain. A flag is a measurement
consumed by `Q.DURATION`, and the abstention is duration's. It is honest in the
useful direction: a flag is used **only where the beams said nothing**, so a
flag can never overturn a beam reading — which is the right ordering, since a
beamed note carries no flag.

**(b)** Only **`Q.DURATION`** leans on it, and through duration everything that
leans on duration (the bar sum, the meter, `reconcile_duration`, INFER's two
duration rules).

⚠️⚠️ **The independence here is GOOD and is the exception in this family.** The
flag comes from YOLO on the ORIGINAL image; the beam comes from classical CV on
the ERASED image. They are two readers of two images, so the contradiction
probe (*a beamed note has no flag*) is a genuine two-witness test, which is why
its rate ordering across three plates is informative rather than circular.
⚠️ It is a RATE and never a count of errors: **it does not say which of the two
readings is wrong.**

**Evidence grade:** value-naming and stem attachment **MEASURED HERE** (`[C80]`,
n = 112 attached / 109 deciding) and **LITERATURE** (SMuFL, Gould p.15,
Bravura); the per-class distribution **PROBE, this dossier** (n = 690 flag rows
over 2,244 committed artefacts); the `*Small` gap **derived from the tree,
reach unmeasured**; the contradiction rates **MEASURED HERE** (n = 112 / 37 /
Breitkopf).

---

## tremolo1 / tremolo2 / tremolo3 / tremolo4 / tremolo5

One to five short slanted strokes drawn **across the stem**, naming a
subdivision. Five classes in the 208-class space.

### 1. What sets it apart — and what it is confused with

**No entry in the mark alphabet.** A tremolo stroke is a short slanted bar, so
it belongs beside the doc's **HORIZONTAL STROKE** family (tenuto, ledger line)
with a slope — and its distinguishing position is the one no other member of
that family has: **on the stem**, not on the lattice and not beside a head.
Added here.

- **It rides the STEM, so it has no SIDE at all.** Every other ornament and
  every articulation is printed above or below its note and its class name says
  which; a tremolo's does not. Recorded in the tree: *"a TREMOLO's side is
  `None` because it rides the stem, so for that class the class name carries no
  position of any kind and the ruler is the only thing that does"*
  (`staged/capture.py:665-669`). **ASSERTED** — registry `[C55]`, status
  ASSERTED, and the registry says plainly **no figure is possible today.**
- **The stroke COUNT is the value**, and it is in the class name (`tremolo3`),
  not in any measurement. `Q.ORNAMENT_MARK` records `strokes` and it is *"a
  tremolo's only"*.
- **Confused with:** nothing has been measured, because nothing has been
  detected. The plausible confusions — a beam fragment, a stem's own thickening,
  a short slur edge — are **unmeasured here**.

### 2. Best method: YOLO / CV / other

**Nominally YOLO. In practice neither, because the checkpoint does not produce
the class.**

- **ZERO `tremolo1`-`tremolo5` detections across 34,115 detections**, and
  **not one across 7,090 committed JSON artifacts at any confidence.**
  MEASURED HERE, `export_coverage.KNOWN_GAPS["ornaments"]`,
  `gather_coverage.py:340`.
- **Confirmed independently by the probe**: **0 rows** in the committed-artefact
  scan over 2,244 files. PROBE, this dossier.
- **The label corpus carries 46 hand-labelled tremolo boxes** (e.g.
  `benchmarks/omr-labeling-2026-05-24/verdicts/beet5-p55-sys2-s13-m2.verdict.json`)
  **that the checkpoint does not reproduce.** So it is *a class the labels carry
  and the model does not emit*, not an absent class. MEASURED HERE.
- **The truth wants it.** The eleven-work engraved truth's **only** ornaments
  are **twelve `<tremolo type="single">1</tremolo>`**, all in
  `beethoven-sym3-mvt1`. MEASURED HERE, same source.

**So the method question for tremolo is a TRAINING question, not a reader
question**, and it sits squarely in the hazard CLAUDE.md already records: the
labelling protocol says skip stems and beams, unboxed ink trains as background,
and a fine-tune on this corpus deletes whole classes within one epoch.

### 3. Where on the page the deciding information lives

**On the stem, between the notehead and the beam or flag.** Not above the staff,
not beside the head.

⚠️ **This is the ONE symbol in the family that HAS a family-position quantity.**
`Q.ORNAMENT_POSITION` was built for exactly this case and the family-positions
table gives the tremolo as its stated reason: *"the same again, apart for its
own reason: a tremolo rides the STEM and its class states no side at all, so
position is the only thing that ever says which side it is on."* It is
**producer-only behind `OMR_FAMILY_POSITIONS`, default OFF, and read by
nothing**; `reach.py:178` names `adjudicate_ornament_owner` as its first
consumer. `capture --check` grades the whole `ornament` family
`position: NONE, side: cls` — *"above/below read off the CLASS NAME — not a
ruler, and not independent of the classification it comes from"* — which for a
tremolo means the class name supplies **nothing at all**. MEASURED HERE
(`benchmarks/omr-family-positions-2026-09/FINDINGS.md` §1; `capture --check`
run here).

### 4. Stage by stage

| stage | what happens | where |
|---|---|---|
| **GATHER** | **no quantity of its own.** `_ornament_kind` ASKS `transcribe._ORNAMENT_KINDS` rather than prefix-matching — ⚠️ **precisely because `tremolo1`-`5` are ornaments whose class names do not begin `ornament`** — and files `Q.ORNAMENT_MARK` with `strokes` and **`side = None`** | `gather.py:758`, `:891-899` |
| **ADJUDICATE** | `adjudicate_ornament_owner` — nearest notehead in x on the printed side, `_ORNAMENT_MAX_DX_NOTEHEAD_WIDTHS = 1.0`, **declared UNMEASURED** (no corpus exists to sweep it on). ⚠️ For a tremolo the **side test is SKIPPED**, not defaulted | `adjudicators/ownership.py:1146`, `:1168` |
| **EVALUATE / INFER** | nothing | — |
| **EXPORT** | `<tremolo>` with its stroke count, inside `<ornaments>`; ⚠️ **LilyPond is deliberately NOT given tremolo**, because `c4:32` is a duration SUBDIVISION, so a wrong mapping writes a different RHYTHM rather than a different mark | `staged/export.py:1554`; `[C55]` known exceptions |

**The wiring is complete and the reach is zero.** That is the honest statement:
the family has an adjudicator, an exporter and a recorded stroke count, and has
never had one input.

### 5. Abstain or best-guess — and what leans on this mark's certainty

**(a)** `adjudicate_ornament_owner` abstains where no notehead is within the
window, and for a tremolo it abstains on the ownership question only — it never
guesses a side, because there is no side to guess. **It has never abstained on a
real tremolo, because it has never seen one.**

**(b) Nothing leans on it, and that is the finding.** A tremolo is a
DURATION-bearing mark in every other engraving system and here it is filed as an
ornament with no duration consequence at all: `adjudicate_duration` does not
read `Q.ORNAMENT_MARK`. So a missed tremolo costs a mark, not a rhythm — which
is why the LilyPond refusal above is the right call and why the MusicXML side is
safe.

**Evidence grade:** *rides the stem* **ASSERTED** (`[C55]`, no figure possible);
zero detections **MEASURED HERE** (34,115 detections; 7,090 artifacts) and
**PROBE, this dossier** (2,244 artefacts); twelve `<tremolo>` in the engraved
truth **MEASURED HERE**; 46 hand labels **MEASURED HERE**; every geometric
claim about a tremolo's own ink **unmeasured**.

---

## tuplet1 … tuplet9 and tupletBracket / tupleBracket

The digit printed over a tuplet group, and the square bracket that may enclose
it. Eleven classes: `tuplet1`-`tuplet9`, `tupletBracket` (fine vocabulary) and
`tupleBracket` (coarse).

### 1. What sets it apart — and what it is confused with

**This one the mark alphabet already has, and this dossier agrees with it
entirely.** `docs/position-grammar-confusables-2026-09-04.md` §2 **DIGIT — one
glyph, five roles**: tuplet digit, fingering, time-signature digit, measure
number, and stacked instrument numbers left of the bracket (plus plate numbers
in the margin). It cites the same 33-of-33 figure this dossier does, and it
carries one warning worth repeating at every digit threshold: ⚠️ ***type design
moves under you — a Litolff `3` matches Bravura's `6`. Never tune a digit
threshold on one edition.***

**What this section ADDS** is per-symbol: which of the eleven tuplet classes
has a route (two), what the staged decision actually reads (not the position),
and what the bracket's own span is worth.

- **The DIGIT and the BRACKET sit differently and must be read differently.**
  The digit is printed over the MIDDLE of its group, so **its centre must fall
  inside the group's span**; the bracket ENCLOSES the group, so **the group must
  fall inside the bracket's span**. Detected brackets are far wider than the
  notes they cover — **one measured at 1846 px over a 478 px group** — and
  testing a bracket's centre **rejects every one of them**. MEASURED HERE,
  `[C54]`, `rhythm._tuplet_groups`.
- **A GROUP is a set of NOTES, not a beam STROKE.** A sixteenth carries two
  strokes; applying the ratio per stroke gives `(1/4)×(2/3)×(2/3) = 1/9`, and
  `mozart-sym41-mvt1` prints 40 groups of triplet sixteenths and cost **464
  edits** for it. Identical member sets are now collapsed. MEASURED HERE,
  `[C54]` known exceptions.
- **A tuplet digit stands OUTSIDE the staff over its beam; a time-signature
  digit stands INSIDE it; a fingering sits beside its notehead; a measure number
  sits at a system's upper left.** **One printed digit, four roles, separated by
  POSITION alone.** MEASURED HERE `[C53]` + LITERATURE `[L42]` (a meter digit is
  ~2 staff spaces tall, so a 1-space digit is a fingering, a tuplet number or a
  measure number — never a meter) and `[L68]`.

**Confused with, concretely:** `fingering3` (its own section below); a
**time-signature digit** — and the coarse half of the class space makes this
worse, since one `numeral` class covers meters, tuplet digits, fingerings **and**
measure numbers, and *"a spurious `timeSig4` once shipped a 2/4 page as common
time at 390 bar-check failures"*; a **measure number**; and for the bracket, an
**ottava bracket** (`ottavaBracket` is a separate class) or a hairpin.

### 2. Best method: YOLO / CV / other

**YOLO for the marker, and the marker is not the hard part — the GROUP is.**
Which notes are in the group comes from the **BEAM BOX**, padded by a notehead
width, *"because it bounds beam INK, which starts at the first stem —
unpadded, every stem-up group loses its first note"*. So the tuplet reading is
downstream of the beam reading.

**Reach, committed-artefact scan (2,244 files):**

| class | rows |
|---|--:|
| `tuplet3` | 55 |
| `tupletBracket` | 37 |
| **`tuplet6`** | **11** (median confidence **0.167**, i.e. mostly under `OMR_CONF_THRESHOLD = 0.25`) |
| `tuplet1, 2, 4, 5, 7, 8, 9` | 0 |
| `fingering3` | 0 |

**PROBE, this dossier.** ⚠️ The engraved orchestral fixtures are gitignored
build products, so the figures that matter most — **33 `fingering3` against 16
`tuplet3` over twelve engraved works** — come from
`omr-corpus-widening-2026-09/FINDINGS.md` and are not in this scan.

**What it is worth when it works:** pooled OMR-NED **0.2595 → 0.2489**,
Mahler 5 **0.0826 → 0.0455** with its duration rate **0.318 → 0.864**, Beethoven
and Brahms byte-identical; admitting `fingering3` took Mahler to **0.0331** and
its duration rate to **1.000**, and `tchaikovsky-sym6-mvt2` 0.2321 → 0.1958.
MEASURED HERE, CLAUDE.md *Tuplets*; `[C53]`, `[C54]`.

### 3. Where on the page the deciding information lives

1. **The digit's x-CENTRE against the beamed group's x-span** (padded by a
   notehead width). This is the whole discriminator.
2. **The digit's y — OUTSIDE the staff, over the beam.** ⚠️⚠️ **`Q.TUPLET_MARKER`
   records `x0`, `x1`, `x_center` and NO `y` AT ALL** (`positions.py:84`). So
   the staged record **cannot ask the question the convention names.**
   `Q.TUPLET_MARKER_POSITION` exists to supply it — the family-positions table
   states the fact as *"whether the digit clears the staff, and by how much"* —
   and it is **producer-only behind `OMR_FAMILY_POSITIONS`, default OFF, read
   by nothing**, with `adjudicate_tuplet_ratio` named as its first consumer
   (`reach.py:180`). `capture --check` grades the `tuplet` family
   `position: NONE`. Run here, 2026-09-20.
3. **The digit's HEIGHT in staff spaces** — the literature's separator from a
   meter digit. Unmeasured here.
4. **The bracket's span**, which must CONTAIN the group.

### 4. Stage by stage

| stage | what happens | where |
|---|---|---|
| **GATHER** | ⚠️ **only four class names are routed**: `_TUPLET_CLASSES = ("tuplet3", "fingering3", "tupletBracket", "tupleBracket")`. **`tuplet1`, `2`, `4`-`9` have NO quantity and NO route** — a sextuplet digit the detector fires is gathered by nothing and has no address at any stage | `gather.py:690`, `:726` |
| | filed as `Q.TUPLET_MARKER` with `x0`/`x1`/`x_center`/`is_bracket` — **no y** | `gather.py:726-732` |
| **ADJUDICATE** | `adjudicate_tuplet` (ORDER: **before** `Q.DURATION`, because duration reads the ratio to scale its beats) | `adjudicators/rhythm.py:656` |
| | it abstains four ways: `no_marker`, `wrong_member_count`, `ambiguous_bracket`, and only ever `3:2` | `:696-720` |
| | ⚠️⚠️ **ITS DOCSTRING STATES THE POSITIONAL GATE AND ITS BODY DOES NOT CONTAIN ONE.** The body reads `Q.TUPLET_MARKER` rows, counts the noteheads **in the whole CELL**, requires exactly three, takes `digits[0]`, and returns `3:2`. **No x test. No beam grouping.** The members are *every notehead in the bar*, not a beamed group | `:690-724`, verified by reading |
| | the tree agrees: `python3 -m tools.omr.staged.inventory --check` prints *"tuplet_ratio declares 'beam_stroke' in `wants` and never reads it — the declaration is inert"*, with the known reason *"the staged decision groups by 'exactly as many heads as the digit claims' in the cell instead"* | run here |
| | ⚠️ **`adjudicate_tuplet` fired ZERO times across 286 runs of the plumbing matrix**, on fixtures printing explicit `\tuplet 3/2`. The *exactly three noteheads in the cell* condition is brutal on dense music | `positions.py:410`; `[C53]` |
| **EVALUATE** | `reconcile_duration` **skips a tuplet member** (its `beats` is already scaled, so re-deriving a level would silently drop the ratio) | `consequences.py:315` |
| **EXPORT** | `<time-modification>` carries the ratio; `<tuplet>` in `<notations>` is the drawn bracket. ⚠️ `_compute_divisions` is an **LCM, not a max** — a triplet eighth is 1/3 of a quarter and the old power-of-two ladder would round every tuplet duration | `staged/export.py:2435`; CLAUDE.md *Tuplets* |

**The legacy path does what the staged path does not.** `rhythm._tuplet_groups`
builds groups from **BEAMED** noteheads via `_beamed_groups`, tests the digit's
centre inside the padded group span, tests the group inside the bracket, and
requires the member count to match. `_TUPLET_NORMAL_FOR = {3: 2}` — so
`tuplet6` is READ and then ABANDONED, deliberately, because a 6 is 6-in-4 or
6-in-3 depending on how the engraver counts and *"reading a digit we have not
measured is how a correct bar becomes a wrong one"*. MEASURED HERE,
`rhythm.py:1210`, `:1313`.

### 5. Abstain or best-guess — and what leans on this mark's certainty

**(a) It abstains generously and in four named ways, and that is right** — a
wrong ratio corrupts a whole bar. ⚠️ **But the staged version abstains for the
wrong reason**: `wrong_member_count` counts the noteheads of the CELL, not of a
beamed group, so on a bar holding a triplet and six other notes it abstains
*because the bar is busy*, not because the marker is doubtful. **A conductor's
page is almost always busy**, which is the mechanism behind *zero firings in
286 runs*.

**(b) `Q.DURATION` leans on it directly**, and through duration the bar sum and
the meter. Because the ratio is decided FIRST, a wrong ratio propagates to
every member's `beats` before any bar arithmetic runs.

⚠️ **Independence:** on the legacy path the tuplet's group comes from the BEAM,
so it fails on the same pages as the beam reader and is not an independent
witness over duration. On the staged path it is independent of the beam — and
only because it reads nothing.

**Evidence grade:** digit-vs-bracket geometry **MEASURED HERE** (`[C54]`, n = 1
measured bracket at 1846 px, and the 12-work class counts); per-class reach
**PROBE, this dossier** (n = 2,244 artefacts); the missing positional gate on
the staged path **derived from the tree and corroborated by `inventory --check`**;
the LCM **MEASURED HERE** (byte-identical on Brahms and the authored fixtures);
`tuplet1,2,4,5,7,8,9` having no route **derived from the tree** (`gather.py:690`).

---

## fingering3 — only where it is confused with tuplet3

A printed `3`. DSv2 gives it a class of its own because the distinction from
`tuplet3` is **positional** — a `3` over a beamed group against a `3` beside a
notehead — and the detector reproduces that split badly on orchestral pages.
The rest of the fingering family belongs to the text dossier.

### 1. What sets it apart — and what it is confused with

**Nothing about its SHAPE does.** It is the same printed glyph as `tuplet3`, and
the class name is not evidence about which role it plays:

- over twelve engraved works, **33 `fingering3` against 16 `tuplet3`, and ALL 33
  sit in a cell that holds a real triplet**; the single detection that does not
  is a `tuplet3`. MEASURED HERE, `[C53]`,
  `omr-corpus-widening-2026-09/FINDINGS.md`, n = 49.
- `mozart-sym41-mvt1` prints 40 triplet groups and hands back **30 `fingering3`
  against 13 `tuplet3`** — so 70% of its markers were dropped before anything
  looked at them, with a duration rate of 0.465 against a note recall of 0.991.
  MEASURED HERE, `rhythm.py:1218-1244`.
- ⚠️ **This corrected a claim that stood in CLAUDE.md for a day**: the Mahler
  group said to *"carry no marker at all, at any confidence"* carries a
  `fingering3` at **0.72**, the highest-confidence tuplet marker on that page.

**Confused with:** `tuplet3`, obviously; and in the COARSE half of the class
space with a meter digit and a measure number, since one `numeral` class covers
all four roles.

### 2. Best method: YOLO / CV / other

**YOLO reads the glyph; only POSITION can read the role**, and the literature
supplies a second, independent separator the repo does not use: a meter digit is
about **2 staff spaces tall**, so a digit one staff space tall is a fingering, a
tuplet number or a measure number and never a meter. LITERATURE `[L42]`;
Bravura `timeSig4` 1.720 × **2.004** sp. **Unmeasured here.**

### 3. Where on the page the deciding information lives

- **Beside its notehead** (fingering) versus **over the beam, outside the staff**
  (tuplet) versus **inside the staff** (meter) versus **upper-left of a system**
  (measure number).
- **Its HEIGHT in staff spaces**, which separates the meter role from the other
  three on its own.
- ⚠️ The fact that WOULD decide it, `Q.TUPLET_MARKER_POSITION`'s *does the digit
  clear the staff*, exists and is off by default — the same one-line answer as
  the tuplet section above, because on the staged path a `fingering3` and a
  `tuplet3` are literally the same quantity.

### 4. Stage by stage

- **GATHER**: `fingering3` is in `_TUPLET_CLASSES` and is filed as
  **`Q.TUPLET_MARKER`** — i.e. the staged record does not distinguish it from a
  tuplet digit at all (`gather.py:690`). Fingerings `0,1,2,4,5` are gathered by
  nothing.
- **ADJUDICATE**: it reaches `adjudicate_tuplet` as a digit. ⚠️ **On the staged
  path the positional gate that is supposed to make admitting this class safe
  is not performed** (see the tuplet section). The admission is safe only
  because *"conductor's scores do not carry fingerings, which is why it has not
  appeared"* — **which is an argument about the corpus, not about the rule.**
- **EXPORT**: `export_coverage.KNOWN_GAPS["fingering"]` — *"a performance
  marking, not a notation family we export"*; the staged `FAMILIES` entry for
  `tuplet` explicitly claims the classes `("tuplet", "fingering3")`.

### 5. Abstain or best-guess — and what leans on this mark's certainty

**(a)** There is no fingering decision. The only abstention available is
`adjudicate_tuplet`'s, and on the staged path it abstains on member count
rather than on position.

**(b)** `Q.TUPLET_RATIO` leans on it, and therefore `Q.DURATION` does.
The registry names the falsifier plainly: **a real fingering `3` centred over a
beamed group of exactly three would still be misread**, and *"no conductor's
score in the corpus prints one to price that against"* — so **the risk is
unmeasured rather than absent.**

**Evidence grade:** the 33-vs-16 split **MEASURED HERE** (n = 49 over 12 works);
the benefit **MEASURED HERE** (Mahler 0.0455 → 0.0331, rate 0.864 → 1.000);
the size separator **LITERATURE ONLY**; the residual risk **ASSERTED, and the
registry says so**.

---

## What we do not know

1. **Whether a rescued stem is a REAL stem.** Not one of the 80 / 152 strokes
   the notehead gate rescues has been checked against the print, and neither
   have the 3 hand cells it makes worse. Every accuracy statement in that lane
   is agreement between two of our own readings.
2. **~90% of the missing stems.** The pair rule accounts for 9.2%; shared stems
   for ~0. The remainder is *the ink is FUSED and there is no stem component to
   find*, which explains the direction and is not a measurement of how often —
   the 8.1-space blob is **one spot-checked cell**.
3. **Whether `STEM_MAX_HEIGHT_LINES = 8.0` costs anything.** The print settles
   only 33 of 55 width-cap discards and that subset is by construction the
   legible one. There is a cap and **no floor**, and Gould's 2.5-space floor has
   never been priced.
4. **What a one-staff barline does to Sean's endpoint test.** The print sample
   was drawn from the `too TALL` bucket, so it establishes nothing about the
   commonest kind of barline on the page — roughly **92%** of them.
5. **Whether the staged exporter writing no `<beam>` costs anything.** It is not
   in the staged `KNOWN_GAPS`, no A/B has been run, and OMR-NED would not be a
   fair instrument for it anyway.
6. **Anything at all about a tremolo's ink.** Zero detections means zero
   measurements: no offset, no confusion set, no reach.
7. **Whether `adjudicate_tuplet` would fire if it grouped by beams.** Its zero
   firings are consistent with both *the markers are absent* and *the member
   test is wrong*, and no arm separates them.
8. **Grace-note flags and `tuplet6`.** Both are gathered-or-detectable and worth
   nothing today; neither has been seen often enough to price.
9. **Two plates, both scans, 8 pages, one adjudicator.** ~60% of Litolff's
   noteheads cannot have their stem adjudicated by eye **at all** — controls and
   sample alike — and that plate is bitonal at its native resolution, so nothing
   better exists for it. The ENGRAVED family is untouched by every stem figure
   here except the LilyPond reference sheet, which is a render and not a
   publisher.
10. **No OMR-NED figure is claimed anywhere in this dossier**, deliberately: the
    metric is symmetric and pays for emitting fewer symbols, which is the wrong
    direction for every symbol in this family.
11. **Whether a stem, beam or flag would benefit from a family-position
    quantity.** Three of the six symbols here have none, and Sean's own
    instruction to the family-positions lane was *"or if it should be symbol
    specific then make it so"* — nobody has asked the question for this family.
    ⚠️ And his warning applies with full force: *"position … will rarely be a
    clear rule that determines by itself."*

---

## Questions for Sean

1. **The pair rule.** Its cited justification is a page total on a fixture that
   prints **no accidental at all**, and at that fixture's own per-bar resolution
   the rule **empties a bar of four chords**. Does it get re-justified on a page
   that prints accidentals, or retired? (`OMR_STEM_NOTEHEAD_GATE` is built,
   default OFF, and narrows rather than removes it.)
2. **Your Friday question, answered two ways above — do you agree with the
   split?** An accidental's stroke belongs in the domain of *"what kind of
   vertical mark is this?"* and not in the domain of a rule whose only outcomes
   are *stem* and *deleted*. If you agree, the work is a decision that reads
   `Q.VERTICAL_RUN` — which is gathered, page-framed, and read by nothing.
3. **The staged exporter writes no `<beam>`.** Every beamed note on that path
   comes out flagged. Is closing that ahead of anything else in this family?
4. **`<stem>up/down</stem>` is never written by either exporter**, and
   `export_coverage` calls it the largest single open item on its list. We
   compute the direction and throw it away. Worth writing?
5. **Tremolo is a training problem, not a reader problem** — 46 hand-labelled
   boxes the checkpoint does not reproduce, twelve in the engraved truth. Is it
   worth a labelling pass, given that a missed tremolo costs a mark and not a
   rhythm?
6. **`tuplet6` and its siblings have no route at all.** The legacy path reads a
   6 and then abandons it because a 6 is 6-in-4 or 6-in-3 depending on how the
   engraver counts. **Which convention do your plates use?** One answer from you
   closes a class.
7. **`adjudicate_tuplet` requires exactly three noteheads in the whole BAR.**
   Should it group by the beam the way the legacy reader does — or is the right
   move to give `Q.TUPLET_MARKER` a `y` first, so the digit's *over the beam,
   outside the staff* position can be tested at all?
8. **The mark alphabet is missing three marks and one heading is too strong.**
   `docs/position-grammar-confusables-2026-09-04.md` has no BEAM, FLAG or
   TREMOLO entry, and heads its vertical-stroke entry *"already solved"* — which
   this dossier disagrees with on the evidence of the six weeks since. Should
   the doc be amended, or is the disagreement worth leaving on the record here?
9. **`capture.py:352` still spells a stem's value `x, y0, y1`** where
   `record.py` records that spelling as refuted (400 of 400 rows). It is a
   comment in a grading tool, not code — but it is the exact convention that
   cost one lane a whole run. Fix in place, or leave it to whoever next reads
   it?
10. **Stems and beams are one witness, not two** — `detect_beams` takes the stem
   list as its input. Given your *lean on what we know more* principle, should
   the beam reader keep that dependency, or should a beam be readable without
   stems so the two can disagree?

