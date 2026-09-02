# Where the OMR work stands — 2026-09-01

Successor to `next-steps-omr-2026-08-29.md`. The change since then is that
**accuracy is measurable against an outside standard**, and the first four things
that measurement pointed at have been fixed.

## The number, and how to reproduce it

```bash
python3 -m tools.omr.omr_ned --bootstrap                 # once
python3 -m tools.omr.training.orchestral_eval --omr-ned
```

**Pooled OMR-NED 0.1506** on the engraved orchestral benchmark (Mahler 0.0455,
Beethoven 0.1775, Brahms 0.1922), down from **0.3164** at the start of
2026-08-31. Lower is better; it is the metric OMR papers report
(*Sheet Music Benchmark*, ISMIR 2025). Full reading in
`benchmarks/omr-ned-2026-08/FINDINGS.md`.

**Read it next to note recall, not instead of it.** It scores recognition AND
export together, and the engraved benchmark says nothing about scan robustness.

## What the metric found, and the pattern in it

| fix | pooled | commit |
|---|--:|---|
| beams never exported | 0.3164 → 0.3045 | `d272ac3` |
| staff window fitted onto a beam | 0.3045 → 0.2716 | `f2e1991` |
| augmentation dots counted twice | 0.2716 → 0.2624 | `52ba215` |
| dynamics never exported | 0.2624 → 0.2595 | `89277a2` |
| tuplets detected and never consumed | 0.2595 → 0.2489 | `d5079d5` |
| a staff line RUNS (two windows in five did not) | 0.2489 → 0.2449 | `9276122` |
| ledger notes awarded by distance, not evidence | 0.2449 → 0.2263 | `81446a0` |
| slurs cut in two by the barline | 0.2263 → 0.2209 | `bae93b1` |
| the crop's own edge read as noteheads | 0.2209 → 0.2137 | `77f796e` |
| a dot measured against its own bounding box | 0.2137 → 0.1917 | `b445e66` |
| a YOLO beam box bounds the stack, not a stroke | 0.1917 → 0.1861 | `cf559ca` |
| a stem capped at 6 staff spaces | 0.1861 → 0.1601 | `50a3920` |
| a beam bar counted from its neighbour's ink | 0.1601 → 0.1506 | `c62b372` |

**Five of the first eight were EXPORT bugs on data the pipeline had already
computed correctly.** Beams detected and dropped, dots detected and counted twice,
dynamics detected and dropped, tuplet markers sitting unread in the JSON, slur
arcs detected and never rejoined. None was visible to any metric this repo had
before — note recall called the Beethoven page perfect (1.000) throughout.

The lesson worth carrying: when a category is large, check whether the signal
exists upstream before assuming it needs better detection. `grep -c beam
tools/omr/export.py` returned 0 while `beam_levels` sat on 271 noteheads.

## Ranked next steps

### 1. Attribute `wrong note` — DONE 2026-09-01, and the answer is SYSTEMATIC

`benchmarks/omr-ned-2026-08/WRONG_NOTE_ATTRIBUTION_2026-09-01.md`. The part of
the budget that disagrees in no pattern at all is **59 edits, 3.3%**; nothing in
it argues for detector work. Two things this step corrected on its way:
`wrong note` is `noteins`/`notedel` and NOT wrong pitches (`wrong pitch` is a
separate musicdiff category and is zero here), and aligning on pitch names — the
method in `BRAHMS_ATTRIBUTION_2026-09-01.md` — cannot see a uniformly transposed
part at all.

What it found, ranked, replaces the rest of this list at the top:

- ~~**Tuplets detected and never consumed**~~ — **DONE**, pooled
  0.2595 → **0.2489**, Mahler 0.0826 → **0.0455** (154 → 86 edits), Beethoven
  and Brahms unchanged to the edit, phase-1 layout unchanged, authored fixtures
  identical. The fifth instance of the beams/dots/dynamics shape, and it was
  export-and-resolution again: the detections were in the JSON and nothing read
  them. See the FIXED section of the attribution report.
- ~~**Brahms Violin 1's staff window is two spaces high**~~ — **DONE**, pooled
  0.2489 → **0.2449**, Brahms recall 0.800 → 0.824. Coverage went in beside
  thickness as a second signal and found **five more misfitted windows** across
  bolero and beet5-p2 that nobody had seen. Net was −28 rather than −86 because
  it uncovered the next item.
- ~~**Cross-staff attribution of ledger notes**~~ — **DONE**, pooled
  0.2449 → **0.2263**, Brahms recall 0.824 → **0.909**. Distance to the nearer
  band is not how a note is read; the ledger LADDER (evidence about the glyph)
  and the instrument's written RANGE (evidence about the part) now decide, with
  distance as the tie-break. The cell pad also had to grow — but only where
  there is unambiguously room, since cell height moves detections.
- **The bassoon pair Beethoven still gets wrong.** Two adjacent bassoon staves
  contest one notehead; one bar resolves on the range veto and the identical bar
  beside it does not. Worth ~8 edits. The ladder cannot help — the note is near
  both staves — so it is the pair ordering reaching the veto inconsistently.
- **A spurious whole note on Beethoven's Flute 1 m1**, older than any of this
  work and never attributed.
- ~~**Seven spurious whole noteheads**~~ — **DONE**, pooled 0.2209 → **0.2137**,
  Brahms 1256 → **1201 edits**, Beethoven and Mahler unchanged to the edit,
  authored fixtures untouched because the rule never fires on them. (It was
  worth 99 edits when first measured; the ledger fix landed in between and took
  some of the same damage a different way.)
  Not a header misread, which is what the attribution report had guessed from
  three of the seven landing in bar 1: they are ink from the staff next door
  that the cell crop sliced, and a wide flat sliver is the shape of a hollow
  notehead. Two of them are the bowl of the **g** in *legato*. A notehead is a
  staff space tall and these are 0.29-0.56, against 0.77-0.99 for the notes a
  crop merely grazes — `transcribe._drop_clipped_notehead_fragments`, measured
  by `benchmarks/omr-ned-2026-08/probe_edge_fragments.py`.
- **Cross-staff attribution of ledger notes — NEW, and now the top item.** With
  Violin 1 placed correctly its highest notes (`A6`, `B♭6`) sit in the gap
  ABOVE its own cell and INSIDE the Timpani's, and export as `A♭1`/`B♭1` on a
  timpani: +59 edits on that part. `_dedupe_cross_staff_detections` awards a
  contested glyph to the nearer five-line band, and LilyPond opened that gap
  *for* those notes, so nearness is the wrong rule. Raising
  `PAD_ABOVE_STAFF_LINES` does not fix it — the note then lands in both cells
  and the same distance rule still picks the timpani. Needs the ledger lines
  (299 detected on that page) or the stem.
  **Carry this into that work: C Horn 2 needs BOTH halves and neither alone.**
  Its 7 bars (50 edits) are dropped because its `C3` — treble clef, 4.5 spaces
  below the bottom line — begins four pixels past its own cell, so the crop
  holds its ledger lines and not the note. Attribution can only choose between
  cells that hold a glyph, and today no cell holds this one. Growing the crop
  first was measured and REJECTED on its own: at pad 5 Brahms goes 0.3420 →
  **0.3732** (+128 edits), C Horn 2 is still empty, Eb Horn 3 gains the note in
  all seven bars, and page-wide dedupe removals go 135 → 390. Full geometry in
  the attribution report's DIAGNOSED section.
- ~~**Beam level ±1 and lost dots**~~ — **DONE**, pooled 0.2137 → **0.1861**,
  Brahms 1201 → **1008 edits** and its duration rate 0.889 → **0.931**,
  Beethoven and Mahler unchanged to the edit. The biggest single step the metric
  has produced, and **neither half needed the meter.** This entry proposed
  widening `_reconcile_measure_to_meter` to move a dot as well as a beam; that
  turned out to be the wrong lever twice over. Both faults were signals already
  on the page, discarded by a threshold written in the wrong unit:
  - a dot was measured against **its own bounding box** (`max(dot.height,12)*1.2`)
    rather than the staff space, so the on-a-line case — where engraving puts
    the dot half a space up — landed on the threshold and went either way. 30 of
    120 detected dots never reached a note. The window also has to be
    ASYMMETRIC, or a double stop's lower dot ties between the two noteheads and
    double-dots the upper one.
  - a **YOLO beam box bounds the whole stack**, not one stroke, so unioning it
    with the classical-CV beams put a centre in the GAP between two levels and
    welded them into one. The docstring had said "replace" since Phase 4f while
    the code said "union"; the truth is neither — CV wins where it speaks, YOLO
    covers where it is silent.
  Full reading in the FIXED section of the attribution report.
- ~~**The missing stems, and the beam bar beside them**~~ — **DONE**, pooled
  0.1861 → **0.1506**, Brahms 1008 → **761 edits**, duration rate 0.931 →
  **0.968**, `exact` measures 67% → **76%**, Beethoven and Mahler unchanged to
  the edit. This entry called the residue detector work, and it was — but
  `line_detection`, not the model, and two more constants that did not mean what
  they said:
  - **a stem was capped at 6.0 staff spaces.** A note beamed to notes far below
    it carries a longer one, so the notes furthest from their beam were
    un-stemmed, and the same distance put the beam beyond the 5.5-space fallback
    — the note lost every level it had. 8746 candidates over 13 pages of 8
    editions put the music population's end at 8 spaces and a second population
    (barlines, brackets) from 10 to the height of the cell; the constant sits on
    the 11× cliff between them, and the sweep agrees (7.0 and 8.0 tie, 9.0 costs
    6 edits and buys one barline).
  - **a beam bar was counted from its neighbour's ink.** `_stacked_bar_count`
    sampled the opened image inside the component's box rather than the label
    mask, and a sloped bar's box reaches over the bar beside it. The LilyPond
    beam ground truth was one over and is now exact.
  What is left is 18 wrong durations, 12 of them the **Viola**, whose bars are
  all `order` class — it plays double stops, and a two-note chord is where
  voice splitting and duration resolution meet. That is the next thread, and it
  is not a beam problem.
  ⚠️ **A green ground truth is not evidence when the case is outside what it
  engraves.** `benchmarks/omr-phase4-lines` is unchanged at every stem cap tried
  because its music has no long stems.

### 2. ~~Slurs that can span measures~~ — DONE 2026-09-01

**Pooled 0.2263 → 0.2209**, Brahms 0.3302 → **0.3185**, `wrong slur` 81 → 61,
edits 1584 → 1563. Measured on top of the ledger fix, not before it — the
earlier 0.2449 → 0.2394 reading was taken on the pre-ledger base and is
superseded. `benchmarks/omr-ned-2026-08/SLURS_2026-09-01.md`.

**The event model needed nothing.** A MusicXML slur may already open in one
measure and close in another, and LilyPond's `(` `)` never cared about barlines;
both need only a number meaning the same thing at both ends. What was
per-measure was the PAIRING, not the model — so it moved to the staff, in page
pixels, the same move `transcribe._pair_ties_in_staff` makes for ties.

Three things this step is worth carrying:

- **The merge alone was an ARTIFACT.** On the pre-ledger base it moved pooled
  0.2449 → 0.2436 while edits went UP (1715 → 1724) and `wrong slur` got worse
  (77 → 86): 74 new predicted symbols diluted a 9-edit loss, because the
  denominator sums both sides. Always read the edit count beside the ratio.
- **What made it real was padding the arc box** — a slur is drawn BETWEEN its
  noteheads, so its ink stops inside both outer centres and an unpadded x-test
  drops the outer note at each end. Same correction `rhythm._beamed_groups`
  makes to a beam box. The Contrabass went from `n1 -> n4` in every bar to 7/7
  exact against a truth of `n0 -> n5`.
- **A slur-stripped truth scores 0.2171**, so all 82 Brahms slurs are worth 82
  edits and a perfect reader lands near 0.2121. This took ~38% of that — the
  same fraction the pre-ledger measurement gave, which is some evidence the two
  fixes are independent. The residue is NOT slur work: the Cello's remaining
  errors have the right note indices and the wrong pitches.
- ~~**Slurs across a SYSTEM break**~~ — **DONE**, and it needed a FIXTURE before
  it needed a fix: every excerpt in this repo is one system, so the case was
  invisible rather than rare. `e2e_fixtures.build_systems` is the first
  multi-system fixture. 0.2416 → **0.2381** on it, orchestral byte-identical.
  Two lessons in `SYSTEM_BREAK_SLURS_2026-09-01.md` worth more than the fix: a
  fixture without a `StaffGroup` is read as one-staff systems and silently tests
  nothing, and slurring every barline made the bars stop summing to four (arcs
  read as beams), which the metric charged to the SLUR because musicdiff prices a
  slur by the duration it spans.

### 3. The `entire measure` bucket, still 22%

406 pooled edits. It halved on its own when the staff misfit was fixed, which is
the point: **it is amplification, not severity.** A measure differing by one
fermata or one slur is charged whole. Do not target it directly — open the op
list first (`benchmarks/omr-ned-2026-08/` shows how) and fix whatever it is
amplifying.

### 4. ~~Text expressions and tempo marks~~ — DONE 2026-09-01

Pooled **0.1861 -> 0.1624** on `2eee2a9`, 1315 -> 1171 edits, `wrong direction`
151 -> **7**, and every other category unchanged to the edit. Every direction on
the benchmark is now read exactly and placed on the correct beat; the 7 are
Mahler's `molto` (never proposed — printed against the staff below it) and the
`[` / `]` the lexicon refuses because they are not words. `tools/omr/direction_text.py`,
behind `--direction-text` (off by default; needs `.venv-surya`). Full reading in
`benchmarks/omr-direction-text-2026-09/FINDINGS.md`.

It was a genuinely different kind of work, as this entry said — no detections to
consume, and the detector deliberately untouched. What it reads text WITH is the
subtraction: every detection is erased from the page's ink, the curves are
refused by fill ratio, and what is left is OCRed by the Surya rung already here
for margin labels and gated on a lexicon of musical terms.

**All 14 Brahms directions and Beethoven's one were read exactly right, zero
false positives.** The remaining 61 is 54 edits of three correctly-read words
attached one beat out, plus Mahler's `molto` (never proposed — printed against
the staff below it on a 38-staff page) and `[` / `]` (not words).

Three things it settled, all in FINDINGS:

- **No distance separates a tempo mark from a title.** Mahler's title sits
  closer to its first staff than Beethoven's direction sits to that one. What
  separates them is alignment: a heading is centred on the PAGE, a direction is
  left-aligned to the music.
- **The detector reads the `p` of `espr.` as a dynamic `p`, correctly**, and
  subtracting it destroyed the word — on two staves, and only after the
  cross-staff fix changed which detections exist.
- **A mark on the wrong beat costs DOUBLE**, and the rule that places it went
  through a rejection that was itself wrong. Nearest-note scored worse on a
  POOLED comparison because a rest occupies x-space and nearness reaches
  backwards onto one — a correct mechanism, and the wrong conclusion: a rest is
  not a candidate at all. Excluding rests keeps what nearness buys and costs
  nothing. Worth 14 edits, and only visible once rules were compared MARK BY
  MARK (`score_placement_rules.py`, seconds per rule) instead of by pooled score.
- **Two of the three remaining misplaced words were not misplaced** — they sat
  on the correct note in a bar whose first note lost its augmentation dot. That
  diagnosis was right and is why nothing was papered over in the placement
  layer. The remedy proposed alongside it — widen `_reconcile_measure_to_meter`
  to move a dot — was **wrong**, and both bars were fixed without it by
  `ac5b3c3`, which found a dot measured against its own bounding box instead of
  the staff space. The printed dot had been on the page all along. Before
  proposing machinery to infer a missing signal, check whether the signal is
  already detected and being dropped.

### 5. Small and known

- Mahler regressed 0.0785 → 0.0826 when dynamics landed (8 edits on a 24-note
  excerpt). Outweighed by Beethoven's −30 but real.
- `gap_bridging_counts` does not implement its own docstring. Unresolved, and
  the prose is confident enough that someone will trust it.
- LEGATO 2 weights are not released; the watch entry in NOTES.md has the URLs,
  and `legato-1.5` is gated and needs Sean's access request.

## Do not spend time on these

Each is recorded with its measurement:

- **The system-break rule.** Five attempts, all rejected — `RULE_FIX_ATTEMPT_2026-08-31.md`.
  The ground truth is now 23 pages / 5 editions and it kills ideas in one run.
  Its three failures are one narrow case: systems printed so close their brackets
  nearly touch. LEGATO 2's segmenter is the lever, not a cleverer local signal.
- **Detector fine-tuning** on hand labels — seven documented collapses.
- **Synthetic augmentation** — disproven by a fair three-way test.
- **VLM transcription** — disproven twice here, and confirmed by LEGATO 2's own
  paper putting Gemini 3.1 Pro at 90-94 OMR-NED against Audiveris's 56-77.

## Environment

Two gitignored venvs, both bootstrapped on this machine:

```bash
python3 -m tools.omr.omr_ned --bootstrap            # musicdiff, Python >= 3.10
python3 -m tools.omr.staff_labels_surya --bootstrap  # surya-ocr
brew install llama.cpp                               # Surya's CPU backend
```

`OMR_SURYA_KEEP_ALIVE=1` is set in `~/.zshenv`; the resident server holds
~1.7 GB, and `--check` / `--stop` manage it. Both venvs self-disable when
absent, so a fresh clone degrades rather than breaks.
