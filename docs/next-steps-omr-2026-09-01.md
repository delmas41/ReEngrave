# Where the OMR work stands — 2026-09-01

Successor to `next-steps-omr-2026-08-29.md`. The change since then is that
**accuracy is measurable against an outside standard**, and the first four things
that measurement pointed at have been fixed.

## The number, and how to reproduce it

```bash
python3 -m tools.omr.omr_ned --bootstrap                 # once
python3 -m tools.omr.training.orchestral_eval --omr-ned
```

**Pooled OMR-NED 0.2209** on the engraved orchestral benchmark (Mahler 0.0455,
Beethoven 0.1775, Brahms 0.3185), down from **0.3164** at the start of
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

**Five of the eight were EXPORT bugs on data the pipeline had already computed
correctly.** Beams detected and dropped, dots detected and counted twice,
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
- **Beam level ±1 and lost dots** — the rest of the 452-edit rhythm bucket.
  `_reconcile_measure_to_meter` declines correctly because it can move a beam
  and not a dot.

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

Pooled **0.2209 -> 0.2040** on `6f64bfa`, 1563 -> 1473 edits, `wrong direction`
151 -> 61, and every other category unchanged to the edit. The -90 is the same
on all four mains this was measured against, which matters more than the
absolute figure — see FINDINGS. `tools/omr/direction_text.py`,
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
- **Attaching a mark to the NEAREST note rather than the next one was measured
  and rejected**: +2 on words, −14 on dynamics, because a rest occupies x-space
  and nearness reaches backwards onto it.

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
