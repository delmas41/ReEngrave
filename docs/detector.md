# The detector, labels and weights

Moved out of `CLAUDE.md` §9 on 2026-10-13
(`docs/claude-md-migration-2026-10-13.md`). The weights files and routing
are listed in `docs/running.md` §1.

The detector is the foundation every stage stands on and the one thing no
stage can repair: a box it never drew has no subject. Facts that govern
design here:

- **Fine-tuning on the label corpus DELETES classes -- in the last layer
  only** (re-checked against the print 2026-09-29: production and its raw
  fine-tune differ in exactly the six `cv3.*.2` tensors and read 127 vs 0
  beams; DECISIONS 2026-09-29). The fine-tune's features are kept; the
  base's class rows are put back for every class the corpus does not teach
  -- that is production, and it reads hollow heads better than the reverse
  graft (option A). It is CLASS DELETION, not suppression (confidence goes
  UP); rehearsal fails in one epoch; the fix is head surgery + a per-class
  bias floor (shipped 2026-09-04). Test new weights Sean's way:
  `--through adjudicate` A/B against a copy of production
  (`benchmarks/omr-weights-ab-2026-09/`, FINDINGS §5); the graft tool
  `benchmarks/omr-labeling-survey-2026-09/merge_class_head.py` prints a
  self-check on every build.
- **Never erase staff lines before the detector** (costs 7-13 reading
  points and up to a third of the noteheads). Erase for the CV consumers,
  bound the search for everyone else.
- **Weights route by input domain** (`input_domain._classify_page`, a
  measured vector-vs-raster test with an empty gap over 147 pages,
  `benchmarks/omr-weight-routing-2026-09/FINDINGS.md`) -- legacy path only
  until ROADMAP 3.2. `image_type` in the catalog is IMSLP's crowd label and
  reads `Typeset` on 7 of 289; never key on it. Publisher/era forks are
  deferred behind measured triggers.
- **The 208-class space is spelled twice**; `class_aliases.canonicalize_names`
  at the one place the model's names are read leaves 157 canonical names.
  `numeral*` and `tuple*` are coarser than the fine names and are not
  synonyms.
- **Anything unboxed on a training cell is background.** `stem` and `staff`
  are CV-only and cost nothing; `beam` and `ledgerLine` are consumed and a
  fine-tune takes them to zero in one epoch. Labeled cell PNGs are not
  regenerable; never re-run the converter on an existing version (use
  `heal_version_metadata.py`).
- **Synthetic augmentation (ScoreAug/Augraphy) is a dead recipe** on real
  cells; catalog-driven training collapsed every time; never load
  `phase-j-mix` weights. Detector knobs: `OMR_IMGSZ` 512, `OMR_DPI` 300 web
  / 600 CLI, `OMR_CONF_THRESHOLD` 0.25 (`docs/measuring.md` §4).
- Labeling: `tools/omr/annotate/` (server at `127.0.0.1:5050`, single-symbol
  passes with `batch_config.json`, click-to-box, `--blind` for scoring
  passes). Pre-filled verdicts are a QUEUE, not labels (blind out-of-sample
  0.915 under the 0.97 bar, `benchmarks/omr-prefill-admission-2026-09/`).
  Sean labels one symbol type per pass; a real symbol ANYWHERE in the crop
  is `t` (the pipeline decides the staff later), a second box on one mark is
  `f`, `unsure` is excluded. Workflow and hotkeys: chronicle §"Hand-label
  cells". Scan truth: hand-labeled pages (ROADMAP 1.7,
  `data/hand-truth/README.md`, `docs/plan-2026-10-08-hand-labeled-truth.md`).
- The CV stem finder (`line_detection.detect_stems`) is the root cause under
  missed beams, missed flags and most "bare stem" notes (ROADMAP 2.87, landed
  2026-10-11); the detector's own `stem` class is not used.
