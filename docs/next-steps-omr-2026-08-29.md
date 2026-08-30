# OMR next steps — handoff, 2026-08-29

Supersedes [`next-steps-omr-2026-08-28.md`](next-steps-omr-2026-08-28.md), whose four
ranked threads are now all closed. That file is still worth reading for how each one
turned out — three of the four ended somewhere other than where they started.

**Read `PROJECT_STATUS.md` for the state of the system.** This file is the
forward-looking part, and the thing to know before starting anything is in the next
section.

---

## The one thing to know before starting anything

**Several of this project's load-bearing conclusions were measured through broken
inputs, and three of them did not survive re-measurement this week.** In order of how
much they cost:

| the record said | it actually is |
|---|---|
| the orchestral wall is a synthetic→real domain gap, meters invisible at any threshold | an `imgsz 2048` artefact — Boléro p.1 reads **36 time-signature digits and 24/24 clefs** at per-cell `imgsz`, against 0 and 13 |
| clef coverage ~23%, "every staff reads as treble" | end-to-end clef accuracy is **96%**, the detector supplying 38 of 52 staves at 97% |
| Beethoven 5 p.15 reads no key signature because the readers are blind | the header was **cropped out of every cell** — the staff's left edge was lost |
| beet5 p.10 staff lines break into 28 runs with 11-space gaps | **2 runs, 0.3-space gap** — the reader was slicing a 2px band around a line that wanders 4 |

The pattern is the same every time: a confident number that describes the *instrument*
rather than the page. Before concluding that the pipeline cannot see something, check
what it was shown — and record the settings next to the result, which is the habit that
would have caught all four.

---

## Where the numbers stand

Everything below is reproducible from a committed script.

| | measure | script |
|---|---|---|
| **Clefs, end to end** | **50/52 (96%)** hand-read staves | `benchmarks/omr-clef-geometry/eval_pipeline_clefs.py` |
| Key signatures, end to end | 29 correct, 0 wrong, 15 missed of 52 | `benchmarks/omr-key-signature/eval_key_signatures.py` |
| Phase-1 layout | all three ground-truth pages exact, no xfails | `tools/omr/training/phase1_layout_eval.py` |
| Instrument identity by position | 23 named / 23 right with clefs; 12 / 11 without | `benchmarks/omr-score-order/eval_score_order.py` |
| Detection vs threshold | conf 0.25 → 0.05 adds **no** key markers, +75% clefs | `benchmarks/omr-detection-probe-2026-08/rerun_july_probe.py` |

992 tests, no xfails.

---

## 1. Read more margin labels — SMALL, AND IT UNBLOCKS TWO THINGS

**What.** `contextual.apply_contextual_analysis(vision_fallback=True)` reads the margin
with Claude where the text layer has nothing, at roughly a cent per system, capped by
`vision_system_budget`. It is off by default and has never been measured on the
orchestral ground-truth pages.

**Why it matters — it is now the binding constraint on two separate layers.** The
part-join that supplies clefs from the dossier is trusted only *between* label anchors,
and the Pastoral p.2 string section carries no labels at all: two staves (the viola,
alto in both systems) are wrong for exactly that reason. The score-order prior calls the
same staff a violin for the same reason. **One label anywhere below the strings anchors
the whole section**, and the dossier already knows that part is a viola.

**Where to start.** `benchmarks/omr-margin-labels-2026-08/` measured the vision reader at
100% agreement with the text layer where both resolve, plus 30 staves the text layer had
garbled. Run `eval_pipeline_clefs.py --dossier` with `vision_fallback=True` wired in and
see whether 50/52 becomes 52/52.

**Done when.** The Pastoral viola reads alto, and the run cost is recorded.

---

## 2. The pipeline reads clefs, then never uses the corrections — STRUCTURAL

**What.** `transcribe` resolves pitches and reads key signatures; `contextual` fixes
clefs afterwards. So a clef corrected by the dossier join or by slot continuity **never
reaches the pitches on that staff**, or the slot table its key signature was fitted
against.

**Why it matters.** This mattered less when clef correction changed almost nothing. It
now fixes real staves, and a corrected clef is exactly the input the two weakest layers
need: `key_signature_geometry` picks its slot table by clef, and `pitch_resolver` shifts
every note on the staff by it.

**Where to start.** The cheapest honest version is a second pass: after
`apply_contextual_analysis`, re-resolve pitches and re-read the key signature for staves
whose clef changed, rather than re-running the whole pipeline. `clef_correction`
already restates pitches when it applies a proposal (`noteheads_restated`) — the same
machinery, extended to the dossier and slot-continuity paths.

**Done when.** A staff whose clef the dossier corrected has pitches consistent with the
corrected clef, and beet5-p15's key-signature count is re-measured with the better clefs.

---

## 3. Key signatures on degraded prints — the reader is close, the detector is blind

**What is known, precisely.** On Beethoven 5 p.15 the printed flats *are* in the header
mask and correctly placed — staff 7's three sit at slot positions 3.91, 1.01, 4.96
against a treble table of 4, 1, 5. The locator now reads some of them (the tail pass,
for runs that begin inside a fragmented clef): 3 of 12 staves correct with true clefs, 1
end to end. Separately, the detector fires on **none** of those flats at conf 0.25, 0.10
or 0.05 alike, while clefs go 16 → 28 over the same sweep. That one is a real
class-specific blindness, not a threshold.

**Where to start.** The header ink mask, which fragments a printed flat into pieces
0.35 staff spaces wide against a real flat's 0.7–0.9, and lets clef fragments into the
run ahead of the signature. Five approaches are already measured and closed in
`benchmarks/omr-key-signature/RESULTS.md` — do not re-run them.

**Done when.** More than one staff of p.15 reads its printed signature end to end,
with no wrong readings on the three ground-truth pages.

---

## 4. Percussion staves are detected but not read

**What.** A one-line percussion staff is now found and keeps its slot, which was the
point — but it is skipped by barline detection and cell extraction, so nothing reads
what is on it. A cell is canonicalised by a five-line span a single rule does not have.

**Why it matters.** Less than the above: it is a whole part's content, but percussion is
the least pitch-critical part of a score. Listed because it is well-scoped and the
detection half is done.

**Done when.** A cymbal staff's notes appear in the JSON with sensible durations.

---

## Also open, smaller

- **`handel-red-p1` and `handel-lead-p1` report zero staves** in the Phase-1 corpus
  (`phase1_layout_eval`). Probably title pages, never checked. Two minutes with a render
  would settle it, and if they are music, something is badly wrong on them.
- **Benchmarks that predate 2026-08-28** carry numbers measured through the old `imgsz`
  and the old staff extent. `benchmarks/omr-real-world/README.md` still records no DPI,
  no `imgsz`, no conf. Re-measure before trusting any of them.
- **Host `anthropic` SDK is 0.28.0 against a 0.116.0 pin.** Structured outputs fail on
  the host; the margin-label pilot works around it with a venv. Item 1 above needs this.
- **A git worktree cannot see the score corpus or the weights** until
  `tools/omr/training/data` and `omr-weights` are symlinked into it. This cost half a
  measurement session — the corpus was assumed gone. `.gitignore` now matches both
  without a trailing slash so the symlinks stay untracked.

---

## What was done this week, in one line each

- **Merged three stalled branches** — the dossier layer, the per-cell `imgsz` rule, and
  the clef header-cluster work — one of which had drifted 41 commits behind.
- **One-line percussion staves** are staves, so the parts below them keep their slots.
- **The staff's left edge** is read with a scaled band and a five-line vote, which fixed
  Phase-1 layout on three pages, retired two xfails, and unblocked the whole header.
- **Key signatures say when they were not read**, instead of reporting zero sharps.
- **The July domain-gap conclusion** was re-measured and retracted where it is cited.
- **The score-order prior** names instruments from position alone on unlabelled pages.
- **Clef accuracy was measured end to end for the first time** — 92%, not the ~23% the
  docs implied — and taken to 96% by two layers: a part keeps its clef between systems,
  and the work's own parts are joined to a condensed page on its margin labels.

Six things were measured and **rejected** along the way; each is written up where
someone would look for it rather than in a scratch file. The most useful of them:
score-order identity must not drive clef correction (it fixes one staff and breaks
another), and the part join must not supply key signatures (the dossier is right about
the work and wrong about the edition).
