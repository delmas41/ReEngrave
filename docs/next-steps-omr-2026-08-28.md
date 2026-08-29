# OMR next steps — handoff, 2026-08-28

Written at the end of the contextual-analysis session, after its work merged to `main`
(`bf8ed2d`) along with the `imgsz` fix (`4f39fe4`). Four threads are open and ranked.
Each says what it is, why it matters, where to start, and what would count as done.

**Read `PROJECT_STATUS.md` first for the current state.** This file is only the
forward-looking part.

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

## 1. One-line percussion staves are invisible — SMALL, UNBLOCKED, DO FIRST

**What.** `_group_into_staves` (`tools/omr/staff_detector.py:101`) accepts only windows of
five evenly-spaced peaks, so a single-line percussion staff produces **no `Staff` at
all**. Every staff below it then carries a `staff_index` one lower than its true slot.

**Why it matters.** It silently corrupts part identity for the whole lower half of an
orchestral system — which now feeds slots, transposition, expected clef and register. A
wrong slot means a wrong instrument means a wrong clef means wrong pitches.

**Proof already written:**
`tools/omr/tests/test_system_grouping.py:202::test_detect_staves_misses_a_single_line_percussion_staff`
draws three five-line staves plus one one-line staff and asserts the detector returns 3.

**Where to start.** The five-peak rule itself. A one-line staff has no spacing to
calibrate against, so it cannot be found the same way; the likely route is a second pass
that looks for long horizontal rules *between* detected staves, at the page's own staff
pitch, and admits them as single-line staves.

**Done when.** The synthetic test asserts 4 staves, a real percussion page keeps its
slots aligned, and no regression on `test_pipeline.py`'s Phase-1 fixtures.

**Note.** The old reason for deferring this — "Phase 1 has no regression baseline" — is
retired. `benchmarks/omr-phase1-baseline/ground-truth.json` exists now.

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
- **PR #4 is open** on `claude/omr-info-retention-erasure-c26534` with its session
  stopped — work sitting in review with nobody driving it.

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
