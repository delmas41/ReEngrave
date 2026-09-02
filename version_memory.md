# version_memory.md — running list of changes

Newest first. One entry per commit or merged arc, with the measured effect
where one exists. Update this file with every commit.

## 2026-09-02

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
