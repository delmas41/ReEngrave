# OMR next steps — handoff, 2026-08-28

Written at the end of the contextual-analysis session, after its work merged to `main`
(`bf8ed2d`) along with the `imgsz` fix (`4f39fe4`). Four threads are open and ranked.
Each says what it is, why it matters, where to start, and what would count as done.

**Read `PROJECT_STATUS.md` first for the current state.** This file is only the
forward-looking part.

> **Progress, 2026-08-28 (later the same day).** Thread 1 is **done** — see below.
> Before it, three branches carrying finished, measured work were merged to `main`,
> because two of them were about to change the ground the remaining threads stand on:
> the **dossier layer** (external truth from the Gradus MusicXML, seeding clef and key
> per staff — Beethoven 5 R .642→.691, Brahms 1 R .206→.253), the **per-cell `imgsz`
> rule** with the mechanism correction below, and the **clef header-cluster** work
> (measured, shipped off by default). PR #4 also merged, so that bullet is gone.
> Threads 2, 3 and 4 are still open and are still ranked as written.

---

## The one thing to know before starting anything

**Every measurement taken before 2026-08-28 went through a broken `imgsz`.** The CLI
defaulted to 2048 and the backend to 1280, and the pipeline was reporting **2–4× the
notes that exist**. `imgsz` is now derived **per cell** rather than fixed
(`yolo_detector.imgsz_for_cell`); `--imgsz 512` is the best fixed value and
`--imgsz 2048` reproduces the old behaviour.

Fixing it moved end-to-end pitch precision on the `keyboard` fixture from **0.144 to
1.000**, and improved every metric on all three fixtures
(`benchmarks/omr-imgsz-sweep-2026-08/findings.md`).

> **Correction to the mechanism.** This section previously said ultralytics
> "letterboxes to `imgsz²` regardless of cell size, so both were buying anchors".
> It does not: `predict` builds `LetterBox(imgsz, auto=rect)` and scales the
> *longest side* to `imgsz`, padding only to a stride multiple — a 300×1200 cell at
> `imgsz 512` is fed as 128×512. What the model is shown is
> `canonical staff space × imgsz / longest side of cell`, so the right setting
> depends on the cell. That is why the fix is a rule and not a number: a constant
> lands inside the good band on wide header cells and past its edge on the narrow
> interior cells of the same page. Measured in
> `benchmarks/omr-detector-scale/RESULTS.md`, which reconciles the two independent
> findings; the practical advice above is unchanged, and 512 remains far better
> than 2048.

So: any older number is suspect, including "100% pitch coverage" in
`benchmarks/omr-real-world/README.md` — which measures *coverage*, not correctness — and
the July probe's false-positive flood. Re-measure before building on one.

---

## 1. One-line percussion staves — DONE, 2026-08-28

**What it was.** `_group_into_staves` accepted only five-peak windows, so a percussion
part printed as a single rule produced **no `Staff` at all**, and every staff below it
carried a `staff_index` one lower than its true slot.

**What it cost, measured.** La Mer p.25 has 21 parts in one system, the twelfth being
Cymbales on one rule. The detector reported 20, so both harp staves, four divided violin
staves, violas, celli and basses — nine parts — were each read as their neighbour.

**What was not obvious.** Nothing about the row identifies a percussion staff: it is a
long inked row between the page's staves, and so is the single surviving line of a
five-line staff printed too lightly for the peak gates. That second case turned out to
be the **commoner** one — the first version of the rule fired on 4 of 10 sampled
Beethoven 5 pages, a score with no one-line parts, finding a clarinet staff and a
first-violin staff. The condition that carries the rule therefore asks the *page*, not
the peak list: is there a line-length run one or two staff spaces above or below? The
other four lines are printed whether or not the row pass saw them.

Over 47 pages of five scores it now fires 14 times, all on La Mer and Mahler 5; twelve
were rendered and read (Cymb., Trg., Becken, Gr. Tr., Kl. Tr.) and every one is a
labelled percussion part. On the 12-page Phase-1 corpus exactly one page moves.

**Where it lives.** `staff_detector._single_line_staff_rows`, evidence and the full
measurement in `benchmarks/omr-phase1-baseline/RESULTS.md`, ground truth for La Mer p.25
in `ground-truth.json`, regression in `test_pipeline.py::TestLaMerPage25`.

**What it deliberately does not do.** Percussion CONTENT is not read: one-line staves are
skipped by barline detection and cell extraction, because a cell is canonicalised by a
five-line span a single rule does not have, and a staff two spaces tall would vote
"barline" for every stem crossing it. The slots were the fix.

---

## 2. Infer the key signature from the music — SEAN ASKED FOR THIS EXPLICITLY

**What.** Recover the key signature from the notes rather than from the header glyphs.
Sean's framing: *"I can determine a key signature because of the clear repetition of a
root note — it starts and ends on an A, so I look for no sharps and flats, or 3 sharps."*

**Why it matters — the evidence is stark.** Beethoven 5 p15 reads `0 sharps / 0 flats` on
**all 18 staves** of a C-minor movement, with **one** `keySharp` detection on the entire
page. Boléro p10 reads five different signatures across 32 staves for a piece in C major,
and the shipped consistency check (b) catches only one of them.

**Where to start — and the important caveat.** This is most likely a *detection* failure,
not a *reading* failure. Before building an inference layer, check whether the glyphs are
being seen at all: `_detect_key_sig_from_cell` (`tools/omr/transcribe.py:624`) and the
positional reader in `key_signature_geometry.py` / `key_signature_locator.py`. If the
glyphs are invisible, the fix belongs with those readers.

If inference is still wanted after that, the signals worth trying, in order:
- **Inline-accidental letter statistics aggregated over a page**, not a staff. A staff
  showing repeated G♯s and nothing else is A minor; recurring inline B♭s against a
  0-flat signature means the signature is missing flats.
- **Cross-staff voting**, which check (b) already has the transposition machinery for.
- **Tonal frame** (first/last notes, weighted pitch-class distribution).

**Do NOT reuse per-staff Krumhansl-Schmuckler profile fitting.** It was measured and is
noise: median margin between best and second-best signature **0.0000**, 62 of 80 staves
under 0.01 (`benchmarks/omr-clef-key-fit-2026-08/findings.md`).

**Done when.** Beethoven 5 p15 reads 3 flats, or abstains loudly instead of asserting 0.

---

## 3. Score-order prior — the principled fix for something hard-coded today

**What.** Score order is **monotone** — instruments never appear out of family order — so
"which instrumentation is this?" is a dynamic-programming alignment of the observed
staves against a small library of standard layouts, not a classification.

**Why it matters.** Today a real ambiguity was resolved by convention rather than
evidence: `Tp.` was resolving to Trumpet on a staff sitting directly below `Tr.`. The
page reads Fl / Ob / Cl / Fag / **Cor / Tr / Tp** — Horns, Trumpets, **Timpani**. It was
fixed by moving the `tp` alias to Timpani
(`tools/omr/tests/test_instruments.py:107::test_tp_is_timpani_not_trumpet`), which is
right for the German/Italian editions in the corpus and wrong for an English score using
`Tp.` for trumpet. Position would settle it properly.

**Where to start.** `tools/omr/slots.py` already does monotone alignment against a
reference layout, and `Staff.group_index` already carries the bracket grouping from
`system_grouping.py`. The missing piece is a library of standard layouts (Classical
pairs / Romantic / large late-Romantic / string quartet / piano / lead sheet) to align
against when no labels are available.

**Done when.** An unlabelled orchestral system gets a plausible instrument assignment
from position and bracket structure alone, and `Tp.` after `Tr.` resolves to Timpani
without the alias hack.

---

## 4. Re-read the July "domain gap" conclusion now that `imgsz` is fixed

**What.** `benchmarks/omr-detection-probe-2026-07/findings.md` concluded the orchestral
wall is a **synthetic→real domain gap, not a threshold problem**, resting partly on a
conf-0.10 probe that "floods noteheads with 2.4–3.5× false positives".

**Why it matters.** That probe ran on narrow orchestral cells — exactly the geometry
where the old `imgsz` inflated detections. Some of that flood was probably an `imgsz`
artefact. This is a **strategic** conclusion: it is the stated reason the project stopped
trying to improve detection and moved to deterministic verification layers.

**What is NOT in doubt.** The probe also found **zero** real time-signature digits
recovered at conf 0.10, and mostly-treble clefs. That stands on its own and is not an
`imgsz` artefact.

**Where to start.** Re-run the probe at `imgsz=512`. It is cheap.

**Done when.** The false-positive multiple is re-measured and the findings file either
confirms or qualifies its conclusion.

---

## Also open, lower priority

- **Clefs are still defaulted on the densest pages.** The whole-pipeline rerun found
  **12/12 DEFAULTED** on handel-reduction p20 and **19/19** on Beethoven 5 p15 — not one
  clef read, so every pitch there rests on a positional guess. `clef_correction.py` can
  fix these given instrument identity, but those PDFs have no text layer, so it needs
  `vision_fallback=True` (`tools/omr/contextual.py`). Cheap to try: ~1c per system,
  bounded per work.
- **`benchmarks/omr-real-world/README.md` records no settings** — no DPI, no `imgsz`, no
  conf. That is why the May table could not be used as a baseline. Record settings with
  results from now on; `rerun_baseline.py` does.
- **Host `anthropic` SDK is 0.28.0 against a 0.116.0 pin.** The July upgrade only reached
  the Docker container. Structured outputs fail on the host; the margin-label pilot works
  around it with a venv.
- **The merge queue is empty as of 2026-08-28.** `reengraved-score-evaluation`,
  `recognition-over-detection` and `omr-clef-fusion-fix` are all on `main`, and PR #4 is
  merged. Note for next time: the dossier branch had drifted 41 commits behind and its
  merge needed three conflicts resolved by hand. Finished work costs more the longer it
  sits.

---

## Two method lessons that cost real time today

**1. A confident number can be measuring the wrong thing.** Twice:

- System grouping was first evaluated with a ground-truth-free proxy ("instrumentation is
  constant, so staves-per-system should cluster tightly"). It *rewards merging every page
  into one system* and duly reported success for a variant that was merging two systems
  into one on 6 of 12 pages.
- The replacement ground truth — counting systems off whole-page thumbnails — was also
  wrong, because at that scale a brass-to-strings bracket gap is indistinguishable from a
  system break. Five single-system pages were labelled as two.

**What worked: render the left margin and count the BRACKETS.** One bracket, one system.
More generally: render the thing and look at it before believing a metric.

**2. Record the settings with the result.** The May benchmark's missing DPI/`imgsz`/conf
made a three-month comparison unrecoverable, and cost a false regression report along the
way.
