# Where the OMR work stands — 2026-09-01

Successor to `next-steps-omr-2026-08-29.md`. The change since then is that
**accuracy is measurable against an outside standard**, and the first four things
that measurement pointed at have been fixed.

## The number, and how to reproduce it

```bash
python3 -m tools.omr.omr_ned --bootstrap                 # once
python3 -m tools.omr.training.orchestral_eval --omr-ned
```

**Pooled OMR-NED 0.2489** on the engraved orchestral benchmark (Mahler 0.0455,
Beethoven 0.1714, Brahms 0.3730), down from **0.3164** at the start of
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

**Three of the four were EXPORT bugs on data the pipeline had already computed
correctly.** Beams detected and dropped, dots detected and counted twice,
dynamics detected and dropped. None was visible to any metric this repo had
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
- **Cross-staff attribution of ledger notes — NEW, and now the top item.** With
  Violin 1 placed correctly its highest notes (`A6`, `B♭6`) sit in the gap
  ABOVE its own cell and INSIDE the Timpani's, and export as `A♭1`/`B♭1` on a
  timpani: +59 edits on that part. `_dedupe_cross_staff_detections` awards a
  contested glyph to the nearer five-line band, and LilyPond opened that gap
  *for* those notes, so nearness is the wrong rule. Raising
  `PAD_ABOVE_STAFF_LINES` does not fix it — the note then lands in both cells
  and the same distance rule still picks the timpani. Needs the ledger lines
  (299 detected on that page) or the stem.
- **Beam level ±1 and lost dots** — the rest of the 452-edit rhythm bucket.
  `_reconcile_measure_to_meter` declines correctly because it can move a beam
  and not a dot.

### 2. Slurs that can span measures

`export.annotate_slurs` is written and tested and **not wired**, with the reason
measured in its docstring: cells are cut per MEASURE, so a slur crossing a
barline is detected as two arcs (118 arcs against 82 true slurs) and emitting
per measure writes two slurs where the music has one. Wiring it in costs 24
edits. The arc-to-note mapping is right; what is missing is a slur that can
outlive a measure in the event model. Worth ~70 edits when it exists.

### 3. The `entire measure` bucket, still 22%

406 pooled edits. It halved on its own when the staff misfit was fixed, which is
the point: **it is amplification, not severity.** A measure differing by one
fermata or one slur is charged whole. Do not target it directly — open the op
list first (`benchmarks/omr-ned-2026-08/` shows how) and fix whatever it is
amplifying.

### 4. Text expressions and tempo marks

17 of the truth's directions on the Brahms page. Unlike the last four this is
NOT an export bug — there is no text detection in the pipeline at all, and
`textDynamic` was the class that caused the Phase 3.4 collapse. A genuinely
different kind of work; do not start it expecting the last four's economics.

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
