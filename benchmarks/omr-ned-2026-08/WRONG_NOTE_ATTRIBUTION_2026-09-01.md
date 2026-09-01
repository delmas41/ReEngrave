# What `wrong note` is — and it is not wrong notes

`wrong note` is 733 of the 1811 pooled edits (40.5%), the largest category in
the benchmark and the one nobody had opened. This attributes it.

Baseline reproduced before anything was touched:

    python3 -m tools.omr.training.orchestral_eval --omr-ned

    pooled OMR-NED 0.2595   1811 edits over 3696 truth + 3283 predicted symbols
    mahler 0.0826 (154)   beethoven 0.1714 (213)   brahms 0.3730 (1444)

(`next-steps-omr-2026-09-01.md` quotes `wrong note` at 808 edits / 44%. That is
the figure from before the dynamics fix landed; at 0.2595 it is 733 / 40.5%.
Still the largest category by a wide margin.)

**The answer is that the residue is systematic.** Every large bucket has a
named mechanism; the part of the budget that disagrees in no pattern at all is
**59 edits, 3.3%**. Nothing found here argues for detector work.

Two tools were written for it, both committed:

    python3 benchmarks/omr-ned-2026-08/attribute_wrong_notes.py
    .venv-omrned/bin/python benchmarks/omr-ned-2026-08/dump_ops.py PRED TRUTH

---

## Finding 0 — the category name is misleading, and the last reading of it was wrong

musicdiff's own op→category map (`Visualization._HEADER_NAME_OF_EDIT_NAME`):

    noteins, notedel  -> wrong note
    pitchnameedit     -> wrong PITCH        <- a different category

`wrong note` counts notes present on one side and absent on the other. A note
read at the wrong pitch is `wrong pitch`, which does not appear anywhere in
this benchmark — its count is zero on all three works.

So `BRAHMS_ATTRIBUTION_2026-09-01.md` was reading it backwards:

> `notedel` and `noteins` are near-balanced (109 / 104), which matters: we emit
> about the RIGHT NUMBER of notes and get their pitch wrong.

Balanced `notedel`/`noteins` means musicdiff **declined to pair** those notes,
not that it paired them and found the pitch wrong. What makes it decline is
usually the DURATION: `_annotated_note_diff` can charge a pitch change or a dot
or a beam, but where the pairing cost exceeds `notation_size` the aligner takes
delete-plus-insert instead, and a note with the wrong duration reliably crosses
that line. One misread rhythm therefore costs about EIGHT edits and files them
under `wrong note`.

Measured: of the 452 pooled edits on measures whose pitches are all correct and
whose rhythm is not, 398 are `noteins` + `notedel`.

## Method — and why the previous method could not have found the biggest fault

The by-hand pass aligned each part's PITCH NAME sequence with
`difflib.SequenceMatcher`. That has a blind spot which happens to sit exactly
on the worst failure mode there is: **a uniformly transposed part contains no
matching block**, so every note becomes an insert plus a delete and the part
reports ZERO wrong pitches. Run that way, Brahms Violin 1 scores 4 replaced
notes, 23 inserted and 25 deleted — while 35 of its 39 notes sit in bars that
are uniformly four staff positions low and the remaining bar is wrong too.

`attribute_wrong_notes.py` therefore aligns **by measure and by index**. The
fixture is engraved from its own truth so the measure counts agree by
construction, and within a bar both sides are in reading order. Each measure is
then classified, and the classes are the causes:

| class | meaning |
|---|---|
| `exact` | identical pitches AND durations |
| `duration` | every pitch right, at least one duration wrong |
| `order` | same pitches, different sequence |
| `shift:k` | every note off by the SAME k staff positions |
| `accid` | right staff positions, wrong accidentals |
| `mixed` | paired, and disagreeing in no one pattern |
| `count` | the two sides disagree how many notes are in the bar |

Notes, pooled over the three works — 610 in the truth, 626 counted here
because a `count` bar is charged the larger of its two sides:

| class | notes | share |
|---|--:|--:|
| exact | 320 | 51.1% |
| duration | 89 | 14.2% |
| count | 82 | 13.1% |
| order | 54 | 8.6% |
| shift | 45 | 7.2% |
| accid | 26 | 4.2% |
| **mixed** | **10** | **1.6%** |

## The edit budget, attributed to those causes

Joining every op in the musicdiff op list to the class of the measure it sits
in (`dump_ops.py` gives each op a part and a measure):

| cause | edits | share |
|---|--:|--:|
| **rhythm** (`duration` bars) | 452 | 25.0% |
| **directions and text** (ops with no part at all) | 319 | 17.6% |
| **one misfitted staff window** (`shift` bars) | 318 | 17.6% |
| **notation on bars that are otherwise perfect** (`exact`) | 317 | 17.5% |
| **note count** (`count` bars) | 261 | 14.4% |
| **scattered** (`mixed`) | **59** | **3.3%** |
| `order` bars (cost is not the ordering — see below) | 53 | 2.9% |
| `accid` bars | 32 | 1.8% |

READ THE CAVEAT. Every op inside a measure is charged to that measure's class,
so each row is an UPPER bound on its cause — an `order` bar still pays for its
beams. That cuts one way only, and it is the direction that matters: `mixed`,
the bucket with no pattern, is at most 3.3%.

`order` costs nothing of its own. musicdiff sorts chord pitches
(`annotation.py:173`, `sortDiatonicAscending`), and Brahms's Viola — the part
that is entirely `order`, all 7 bars — carries 20 edits, none of them
`wrong note`. Writing a double stop high-to-low is free.

---

## Finding 1 — rhythm is the largest single cause, 452 edits, and it is two mistakes

Every wrong duration in the benchmark, as the ratio predicted/true:

| ratio | notes | what it is |
|---|--:|---|
| ×0.5 | 23 | beam level one too many |
| ×2 | 18 | beam level one too few |
| ×1.5 | 15 | a triplet read as three straight notes |
| ×0.667 | 11 | dotted note read undotted |
| other | 10 | |

**Mahler's rhythm error is one thing, and the signal for it is already in the
JSON.** All 15 of its wrong durations are `0.3333 → 0.5`: the Trauermarsch
trumpet fanfare, half note plus eighth-note triplet, five times. Every pitch is
right. And:

    grep -ci tuplet tools/omr/{export,rhythm,transcribe,line_detection}.py
    0 0 0 0

while the page's own detections carry `tuplet3` ×3 and `tupletBracket` ×2, and
DeepScoresV2 has had `tuplet1`–`tuplet9` and `tupletBracket` in the class space
all along. **This is the fifth time the same shape has appeared** — beams
detected and dropped, dots detected and double-counted, dynamics detected and
dropped, and now tuplets detected and ignored. It is worth 87 of Mahler's 154
edits, 57% of that work's entire budget.

**The meter feedback loop exists and cannot reach the rest.** Brahms's page
meter is read correctly as 6/8 with 126 votes and stamped on every measure, and
exactly 2 reconciliations fired on 21 staves. `_reconcile_measure_to_meter`
re-reads a beam level by ±1 and nothing else, and the Violin 2 bars need a dot
as well as a beam — truth `0.75 0.25 0.25 0.25 1 0.5` read as
`1 0.5 0.5 0.5 1 0.5` — so no ±1 beam move lands on 3.0 and it correctly
declines. Its refusal is right; its reach is one edit too short.

## Finding 2 — one staff's five-line window is two spaces high: 263 edits

Brahms part 16, Violin 1, costs 263 edits — more than any other single part in
the benchmark, and more than the whole of Beethoven. Its `shift:-4` is uniform
across six of its seven bars, 35 of its 39 notes: `C6 C6 C#6` read as
`F5 F5 F#5`, four staff positions low, every bar.

Measuring the page's own ink across the staff's x-extent settles what happened.
Rows at coverage ≥ 0.30, and what the detector chose:

    y=7498  0.438  <== detected as a staff line
    y=7539  0.485  <== detected as a staff line
    y=7578  1.000
    y=7580  1.000  <== detected
    y=7620  1.000
    y=7621  1.000  <== detected
    y=7661  1.000
    y=7662  1.000  <== detected
    y=7703  1.000
    y=7744  1.000

The real staff is `[7578, 7620, 7661, 7703, 7744]`. The window took two rows of
partial-width ink above it — ledger lines under a high violin line — and kept
only the top three real lines, landing **two spaces (82 px) high**.

**Three tells were already recorded in `staff_geometry`, and the existing rule
is looking at the weakest of them.** `_refit_misaligned_group` (step 3d, the
fix that recovered the contrabass) gates on `max(thickness) >= 2.5 * median`:

| | staff 16 | every other staff on the page |
|---|--:|--:|
| thickness | `[9, 8, 5, 4, 5]` — ratio **1.8** | 1.0–1.25 |
| wander | **14.0 px** | 1.0–3.0 px |
| coverage of its outer rows | **0.44, 0.49** | 1.00 |

So the thickness ratio is 1.8 against a threshold of 2.5 and the rule declines
— correctly, on the evidence it consults. Coverage is the decisive
discriminator here and the function that measures it, `_longest_row_run`,
is already in the file and already used one line further down as the rule's
*confirmation* gate. The rule also slides by exactly one spacing, and this
window needs two.

**Do not fix this by lowering `MISFIT_THICKNESS_RATIO`.** 1.8 is inside the
normal range for a clean staff on this very page, and the repo has a written
history of clef thresholds tuned on one corpus and refused by the next.

## Finding 3 — the `count` bucket is three mechanisms, not noise

261 edits, and none of it is scattered:

1. **Seven spurious whole noteheads, all in staff-start measures.**
   Contrabassoon `A♭4/4`, Bb Clarinet 2 `F6/4`, Bassoon 1 `A♭4/4`, Eb Horn 3
   `G6/4` three times. The page detects `noteheadWholeInSpace` ×7 and contains
   no whole notes at all; the excerpt's first bar is where the clef and key
   signature sit.
2. **A whole staff lost.** C Horn 2 has one note in each of its 7 bars in the
   truth and emits **zero** in all seven.
3. **Two flute staves trading a note.** Flute 2 drops its highest note in 4 of
   7 bars while Flute 1 gains a spurious `G3` in 3 of them. This page reports
   `n_cross_staff_duplicates_removed` = 174 (Mahler's reports 1029), so the
   deduper is the first thing to look at.

## Finding 4 — what a perfect bar still costs

317 pooled edits fall in measures whose pitches AND durations are both exactly
right: `editbeam` 108, `insbar`/`delbar` 132, `accidentins` 33,
`insexpression` 14. Beethoven is 163 of them — its notes have been perfect
since the staff fix and its whole remaining budget is notation and the
whole-bar amplification that notation triggers. The previous file's warning
holds: the `entire measure` bucket is amplification, and it moves when its
cause moves, not when it is targeted.

---

## What this decides

Ranked by measured size, with the cheap ones first because they are cheap:

1. **Tuplets** — 87 edits on Mahler alone, 57% of that work's budget, and the
   detections are already in the JSON. Same shape as the last four fixes.
2. **The Violin 1 staff window** — 263 edits on one staff, with the
   discriminator (row coverage) already computed in the same file.
3. **Beam level ±1 and lost dots** — the rest of the 452; partly reachable by
   widening `_reconcile_measure_to_meter` to move a dot as well as a beam,
   which is a change to a component that already exists and already abstains
   safely.
4. **The `count` mechanisms** — three small independent ones, above.
5. **Directions and text** — 319 pooled, still the biggest single line, still
   needing detection the pipeline does not have. Unchanged from the last
   handoff, and still not to be started expecting the others' economics.

And the thing that is NOT on the list: nothing here is a case for retraining
the detector. The notes are being found. What happens to them afterwards —
their durations, the window they are measured against, whether they survive
deduplication, whether they reach the exporter — is where the budget goes.

---

## FIXED 2026-09-01 — tuplets, the first of the three

Pooled **0.2595 → 0.2489**, 1811 edits → 1743. Every one of the 68 came from
Mahler, exactly where this file said they were:

| | before | after |
|---|--:|--:|
| pooled OMR-NED | 0.2595 | **0.2489** |
| mahler | 0.0826 (154 edits) | **0.0455 (86)** |
| mahler duration rate | 0.318 | **0.864** |
| mahler `wrong note` | 81 | 16 |
| mahler `wrong tuplet` | 10 | 2 |
| beethoven | 0.1714 (213) | 0.1714 (213) |
| brahms | 0.3730 (1444) | 0.3730 (1444) |

Beethoven and Brahms are unchanged to the edit — neither page carries a tuplet
marker. Phase-1 layout: **no change** on all 12 pages. The authored end-to-end
fixtures: identical to three decimal places on all three (stash-and-rerun, not
a stored snapshot). Tests 1116 → 1152.

**It was an export-and-resolution gap, not a detection one, as predicted.** The
`tuplet3` and `tupletBracket` detections were already sitting in the JSON. What
was missing was anything that read them: the pipeline did not contain the string
"tuplet" outside the detector's class map.

Three things the implementation turned on, all of which would have been easy to
get wrong:

1. **The written note value is already correct.** A triplet eighth is printed as
   an eighth. Only `duration_beats` is scaled, by 2/3; `duration_type` stays
   `eighth`, which is what `<type>` and LilyPond's `8` both want. Nothing is
   re-read.
2. **The beam box says which notes, the marker only says that.** The digit is
   printed over the middle of its group and does not span it; the bracket spans
   far more than it (1846px over a 478px group). Neither box is the group. The
   beam box is, padded by a notehead width — beam ink starts at the first stem,
   and unpadded the test drops the first note of every stem-up group.
3. **`_compute_divisions` had to become an LCM.** It searched a power-of-two
   ladder and took the max, and 16 thirds is not an integer, so a triplet would
   have been written with a rounded `<duration>` and a short bar. The LCM of
   powers of two is their max, so tuplet-free scores are byte-identical — which
   is what Brahms's unchanged 1444 confirms.

Coverage is 4 of the 5 triplet groups on the page; the fifth has no marker
detected at any confidence, and its 2 remaining `instuplet` edits are the whole
residue of the category. Mahler's remaining 86 edits are directions (24), the
whole-bar amplification those cause (18), and 11 accidentals.

**Still open, in the order this file ranked them:** Brahms Violin 1's staff
window (263 edits), beam level ±1 and lost dots, the `count` mechanisms, and
directions and text.

---

## FIXED 2026-09-01 — the Violin 1 staff window, and what it uncovered

Pooled **0.2489 → 0.2449**, 1743 edits → 1715. Brahms 0.3730 → **0.3657**, its
note recall 0.800 → **0.824** and precision 0.797 → **0.819**. Beethoven and
Mahler unchanged to the edit; phase-1 layout unchanged on all 12 pages; the
authored fixtures identical. Tests 1152 → 1166.

**The window is right now.** Violin 1's `shift:-4` is gone — 35 of its 39 notes
were four staff positions low and none is. `[7498, 7539, 7580, 7621, 7662]`
became `[7580, 7621, 7662, 7702, 7743]`, and `m1` reads `C6 C6 C#6` exactly.

Coverage went in as a SECOND signal beside thickness, not a replacement, because
the fault has two shapes: a window that locked onto a BEAM has a fat end line
(the contrabass, 18px against 5px) and one that locked onto LEDGER LINES has end
lines at staff weight that do not run. The rule can now also slide by two, which
the old one could not — and Violin 1 needed two.

Measured over 270 staves and 5 editions before anything changed
(`benchmarks/omr-phase1-baseline/probe_line_coverage.py`), the worse end line's
coverage over the staff's own median:

    0.041  brahms-e2e  staff 16      0.107  bolero-p5 staff 12
    0.055  bolero-p31  staff 11      0.109  bolero-p5 staff 21
    0.076  beet5-p2    staff 18      0.112  bolero-p5 staff  3
    ------------------------------- 6x gap, nothing in between -----------
    0.682  lamer-p25   staff 16      0.784  beet5-p2  staff  2

All six were confirmed misfitted by reading each page's own ink profile — this
found **five more** than the one it was written for. Both of the next two are
correctly placed staves on faint scans and are untouched. After the fix the
worst deficit on the corpus is lamer-p25's 0.237, its last row sitting 2px off
its line, and the staff count is unchanged at 270 — nothing was lost or invented.

### The net is −28, not −86, and the difference is worth more than the fix

| part | before | after | |
|---|--:|--:|---|
| 16 Violin 1 | 263 | **177** | −86 |
| 15 Timpani | 31 | **90** | **+59** |
| every other part | | | 0 |

Violin 1's own cost fell by 86. The Timpani gained 59, and the cause is exact:

    staff 15 Timpani  lines [7093 … 7259]   cell reaches 4 spaces below → 7423
    staff 16 Violin 1 lines [7580 … 7743]   cell reaches 4 spaces above → 7416

Violin 1's m3 and m4 are its highest notes — `G6 A♭6 A♭6 A6`, `A6 B♭6 B♭6 A♭6` —
and they sit at y 7373-7408, ABOVE its own cell and INSIDE the Timpani's. They
now export as `A♭1 B♭1 G1 A1` on a timpani, and Violin 1's m3 and m4 come out
empty. Before the fix the window was two spaces higher, so the same notes fell
inside it by accident.

**So this is not a regression the fix caused; it is a pre-existing mis-assignment
the fix stopped hiding.** LilyPond opened that gap *for* those ledger notes, and
`_dedupe_cross_staff_detections` resolves a contested glyph by distance to the
nearer five-line band — which, for a note in a gap opened on its account, is the
wrong staff. Raising `PAD_ABOVE_STAFF_LINES` alone does not help: the note then
lands in both cells and the same distance rule still awards it to the Timpani.

That makes cross-staff attribution the next item, ahead of the rhythm residue,
and it needs a signal the band distance does not carry — the ledger lines
themselves, which this page detects 299 of, or the stem. It is the same
mechanism as the two flutes trading a note in Finding 3.
