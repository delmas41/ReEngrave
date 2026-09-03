# version_memory.md — running list of changes

Newest first. One entry per commit or merged arc, with the measured effect
where one exists. Update this file with every commit.

## 2026-09-03

- **pre-fill run on the Brahms 1 batch from this session** (inputs pushed by Sean): 51 of 56
  cells pre-filled, 179 TP, 15 relabels, 22 missing-note hints, 5 abstentions all on the right
  bar. Three fixes on the way: a weighted LCS that tolerates a half-space of rounding but needs
  at least one EXACT match before near ones count (a wrong bar's notes often sit a step away);
  recall over the reference's NOTES, not its rests; a rests-only bar pre-fills with hints instead
  of abstaining. `prefill/` (hints only) committed into the batch so labeling can start.
- **pre-fill: the gate is recall of the reference, and neighbours' heads stay out of the
  alignment** — a flute bar of 4 reference notes read 21 heads, 17 of them the oboe's and
  piccolo's from the cell's padding (positions 7 spaces off the staff); only heads within the
  reference's own vertical range align, and a bar passes when ≥ 50% of its reference notes
  (and at least 2) are found. Also fixed: `bbox_page_px` is `[x0, y0, x1, y1]`, not
  `[x, y, w, h]` — the x-scale into the batch frame and the width check were wrong.
- **pre-fill: diagnostics for the abstentions** — `--debug-cell` prints both token sequences
  and the geometry for a cell; every cell records a width ratio that says whether the batch
  cell and the transcription measure are the same bar (the batch was cut by a separate
  segmentation run). A reference part with no clef (percussion) falls back to step keys on
  BOTH sides. Second Brahms run: 29 of 56 pre-filled.
- **training: pre-fill aligns on STAFF POSITION, not pitch** — the reference's written clef
  (now parsed by `musicxml_truth`, per note) places each truth note; a detection's position
  comes from its box. Sean's first Brahms 1 run: 26 of 56 cells pre-filled, 30 abstained with
  `0 of N matched` — the misread-clef signature. `--match step|exact` kept as options; the
  summary now lists abstained cells with their match ratio.

## 2026-09-02

- **training: draft fills an unnamed staff by ORDER** — on a shorter system, a staff the reader
  could not name takes the only unused base entry between its paired neighbours (Sean's page 1
  bottom system: the Kontrafagott between the Fagotte and the Hörner); two candidates → still
  empty for the human. Brahms 1 batch draft now needs no hand edits.
- **training: page-global staff numbering** — `transcribe` numbers `staff_index` across the
  page; the draft summed bars per index across systems (page 1 of the Brahms batch came out
  as 7 bars instead of 15) and the pre-fill joined a staff to the row by index. Both now go by
  position within the system; a full-lineup system pairs by position with the reader's word as
  a cross-check only. Found on Sean's first real draft of the Brahms 1 batch.
- **training: `draft_windows.py` + `--write-hints`** — window rows are drafted from the
  transcription and a base benchmark row (measure window chained page by page, staves paired
  to parts by instrument name, everything marked `draft` with a `check` list); hints-only
  mode writes `prefill/` without touching `verdicts/`. Runbook for the first real-batch
  measurement (Brahms 1 / Breitkopf): `docs/runbook-prefill-brahms1.md`. Finding: the Mahler
  batch cannot be scored — the library has no Adagietto reference.
- **training: MXL-guided verdict pre-fill** — `tools/omr/training/mxl_verdicts.py`
  (+ `measure_align.py`, `musicxml_truth.py`): the detector's boxes are confirmed or
  relabelled by the reference encoding through per-measure sequence alignment; unmatched
  detections stay pending, unmatched reference notes become ghost hints. Annotate server
  serves `<bench>/prefill/`; the cell list gains a queue order and the cell page a hints
  layer (`h`). `--score` measures the pre-fill against human verdicts. 43 new tests, full
  annotate + training suites green. Not yet run on a real batch — that measurement is
  Sean's next step on the Mahler 5 / Peters hollow batch.
- **docs: status brief, project brief, version memory** — consolidated where
  the labeling campaign, the movement-start data, the score-library ingest and
  the MXL-guided auto-label training system stand; created `PROJECT_BRIEF.md`
  and this file. No code change.
- `6a17de7` docs: export-gap ordinal moves out of prose into the numbered list.
- `b5b7db3` / `0a6382c` / `d282371` **eleven-work benchmark landed** — headline
  3 → 11 works; `0.1306 / 2745` default (reader on), `0.1399 / 2915` reader off,
  both on `44a1745`; boundary stamped and checked by `accuracy_record`.
- `52e9945` labeling: Mahler 5 Adagietto (Peters) hollow batch — 49 boxes, 55/56 cells.
- `2a8bf79` labeling survey: symbol × publisher-family plan; scope decision
  PROVE-IT-FIRST (finish the 280 cut cells, one gated training run, extend only if it holds).
- `54d19da` labeling: `batch_config.json` (single-symbol hollow pass) on all five round-2 batches.
- `44a1745` scan-e2e: `works.json` pinned the direction reader off while claiming defaults; now pins `null`.
- `fb4c500` … `59c1eca` labeling: hollow-notehead round 2 cut — five 56-cell batches
  (Peters, Eulenburg, Litolff 4×, Breitkopf, Simrock); enclosed-counter ranker replaces
  meter shortfall (did not transfer).
- `fa9853a` labeling: round-1 hollow batch landed as `data/user-labeled/v7-2026-09-02-hollow`
  (24 cells / 28 boxes); 116 of 117 model pre-labels were false.
- `2b900c4` annotate: `inspected_passes` stamp — a swept-empty cell is provably distinct from a never-opened one.
- `eb3530c` / `9b3cec4` / `6cad993` / `9998390` annotate UI: single-symbol pass mode —
  click places a measured, staff-snapped box; tests 18 → 52.
- `96df4fb` / `a907e41` / `f238ce9` export: a bar with no detected notes still carries its
  `<direction>` and dynamics (eighth detected-then-dropped gap). Neutral on engraved pages by construction.
- `4952005` direction text ON by default (−144 edits, stable across seven mains).
- `de09383` / `fc073f2` finding: same scan page transcribed twice differs; isolated to
  `contextual._labels_for_page`; geometry bit-identical with contextual off.
- `d3d5ec5` export_coverage surveys all eleven works.
- `bc4214d` gitignore: alternate `--work-dir` fixtures are scratch.

## 2026-09-01

- Overnight generalization session: engraved corpus widened 3 → 10 (opened at ~2× the
  incumbents' error), first five-row scan benchmark (pooled 0.7960), cut-common meter
  bug fixed (3 wrong → 0), two key-signature vote bugs fixed, fermata render completed
  in the Beethoven fixture (0.1519 → 0.0727). See `docs/overnight-2026-09-01-summary.md`.
- Evening queue: edge fragments, dot height, YOLO beam stack, stem cap, beam-bar mask,
  ledger evidence (Beethoven 81/81), viola double stops, slurs paired per staff,
  Tesseract union rung, accuracy figure made single-sourced.

## Earlier

See `PROJECT_STATUS.md` (narrative) and `git log`; this file starts on 2026-09-01.
