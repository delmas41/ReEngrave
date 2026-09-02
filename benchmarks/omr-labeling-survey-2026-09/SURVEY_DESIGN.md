# A systematic hand-labeling survey — design (2026-09-02)

**Status: PLANNING. Nothing here has been cut, run, or trained.** This document
turns Sean's brief — *"systematically do this for all of the types of notes and
symbols that need retraining, getting a helpful amount of examples from every
different type of publisher in our central library"* — into a bounded, ordered,
evidence-ranked plan he can approve or trim. It ends with an explicit scope
decision (§5).

The survey is a **matrix**: symbol classes (rows) × engraving-house styles
(columns). Round 1 (`benchmarks/omr-labeling-hollow-2026-08`) and round 2
(`benchmarks/omr-labeling-hollow2-2026-09`) already cut the **first row**
(hollow noteheads) across the **first five columns** (Litolff, Breitkopf,
Peters, Eulenburg, Simrock). This design names the rest of the rows, normalises
the columns, sizes the whole thing, and says what is worth doing versus what a
non-labeling lever already closes.

Two reproducible scripts back the axes below:

```bash
python3 benchmarks/omr-labeling-survey-2026-09/publisher_families.py --orchestral
python3 benchmarks/omr-labeling-survey-2026-09/labeled_coverage.py --zeros
```

---

## §1. The symbol axis (rows) — evidence-driven and ranked

A class earns a row only if **all** of these hold:

1. YOLO detects the class (so a label moves it) — DSv2 class space,
   `tools/omr/training/deepscores_classes.py`;
2. it is **measured under-detected on real scans**, not merely imaginable;
3. it is **not better fixed by classical CV or by the exporter** — the
   September work closed four detected-and-dropped gaps (beams, augmentation
   dots, dynamics, tuplets) purely in `export.py` (`PROJECT_STATUS.md` lines
   150-181), and a labeling batch would have been wasted effort on any of them.

Current label coverage per class (from `labeled_coverage.py`, all of v1–v7
unioned) is the "have" against which each gap is the "need":

| well-covered | boxes | near-blind | boxes |
|---|--:|---|--:|
| noteheadBlack (On/InSpace) | **689** | noteheadWhole (On/InSpace) | **23** |
| restQuarter | 104 | timeSig digits (all but `2`) | **~0** |
| accidentalFlat | 81 | graceNote (all 4) | **0** |
| noteheadHalf (On/InSpace) | 130 | ornament (trill/turn/mordent) | **0** |
| slur / tie | 65 / 51 | tuplet digits (all but `3`) | **~0** |
| articStaccato/Tenuto/Accent | 40 / 30 / 28 | arpeggiato, tremolo1/4/5 | 0 |

### Ranked rows

**Row 1 — Hollow noteheads (`noteheadHalf*`, `noteheadWhole*`). THE lever.**
The strongest-evidenced gap in the project.
- *Evidence:* Beethoven 5 p.1 prints **68 half notes; the pipeline emits 8**
  (`benchmarks/omr-first-run-2026-08/DURATIONS.md`). On the scan benchmark,
  **duration is the weakest recall column on every one of the four rows with a
  hand-read staff map** — 0.39–0.63 against 0.70–0.85 for pitch position — and
  RESULTS.md states the diagnosis "is alive in every one of these pages and is
  not a Beethoven peculiarity" (`benchmarks/omr-scan-e2e-2026-09/RESULTS.md`,
  note-recall table). The
  condensation arm proves the scan residue is a **reading** problem (53.3%
  `wrong note` once the part convention is removed), not a part-model artifact.
- *Why not CV/export:* four code fixes were measured and **all failed** —
  ink-fill reclassification, enclosed-white counters (662 candidates for 68
  notes), Bravura template matching (15/68), ink thinning
  (`PROJECT_STATUS.md` line 638). The engraved control finds **31 hollow heads
  against 30 real** on the same music and weights — so the rhythm layer is fine
  and the failure is purely the scanned *appearance* of a closed counter. That
  is exactly what more labeled scan examples fix and nothing else does.
- *Class status:* four DSv2 classes exist; **adds examples, no new class, no
  Phase-3.4 risk.** Whole notes are barely covered (23 boxes) and want their
  own attention within the row.
- *State:* round 1 landed `v7` (24 cells, 28 boxes, one edition). Round 2 is
  **cut and waiting** — five 56-cell batches, `verdicts=0`, ≈196 boxes expected.

**Row 2 — Grace notes & small noteheads (`graceNote*` ×4, `notehead*Small`).**
A total blind spot that the pipeline is known to miss.
- *Evidence:* **zero labeled boxes across v1–v7** for all four grace classes
  and the `*Small` notehead variants. CLAUDE.md's orchestral limitation names
  it directly: *"more false negatives on small dynamics + grace notes"* on dense
  conductor's scores. A grace note is a small notehead the density-tuned
  detector is primed to drop.
- *Why not CV/export:* there is no CV path for a notehead-shaped glyph; the
  exporter can only emit what the detector finds.
- *Class status:* classes exist; adds examples. **Weaker tier than Row 1** — the
  evidence is a blind spot plus a qualitative flag, not a hard per-scan count,
  because nothing currently measures grace-note recall. Cutting a first batch is
  partly *to obtain that measurement.*

**Row 3 — Small dynamics glyphs (`dynamicLetterP/F/S`, `dynamicPiano/Forte`,
hairpins).**
- *Evidence:* CLAUDE.md's same orchestral flag ("small dynamics"); coverage is
  thin and lopsided (`dynamicF` 44 but `dynamicLetterP` 21, `dynamicLetterS` 8,
  hairpins ~17 each). On dense scans a bold italic **p** is missed or, worse,
  its bowl and stem fire as noteheads (round-1 AUDIT, `s3-m6`).
- *Caveat that lowers it:* the *export* half of dynamics was already fixed
  (dynamics-never-exported, `PROJECT_STATUS.md` line 153) — so the residual is
  genuinely detector recall of small letter-glyphs, a real but smaller slice.
- *Class status:* classes exist; adds examples.

**Row 4 — Ornaments (`ornamentTrill/Turn/TurnInverted/Mordent`).**
- *Evidence:* **zero labeled boxes.** A real blind spot, but **lower
  frequency** than rows 1–3 and with no measured scan count. Sits above the
  notehead, so it is not confused with structural ink.
- *Class status:* classes exist; adds examples. Low priority — include only in
  a deep scope.

### Candidates assessed and RANKED LOW (a non-labeling lever is primary)

- **Time-signature digits (`timeSig0-9`).** The detector reads **zero** time
  signatures on real scans (Beethoven 5 p.1: no `timeSig` digit found on a page
  printing `2/4` legibly twelve times — `PROJECT_STATUS.md` §"header meter
  reader"). *But the shipped lever is not the detector* — `time_signature_locator.py`
  reads the meter by **geometry / Bravura template**, and works. Labeling scan
  digits would help the detector, which the pipeline no longer needs to succeed
  here. **Low priority; the CV reader already closed it.**
- **Inline & key-signature accidentals (`accidental*`, `keyFlat/Sharp`).** The
  exact-vs-step recall gap on scans (0.571 vs 0.714 on Beethoven 5) is partly
  missed accidentals, and `wrong keysig` is 175 scan edits. *But* the shipped
  lever is again geometry — `key_signature_template.py` slides Bravura templates
  and reads 11/12 where the detector reads 2/12 (`PROJECT_STATUS.md`
  §"key-signature accidentals"). Inline accidentals already have moderate
  coverage (flat 81, sharp 39, natural 29). **Low priority.**
- **Tuplet digits & the `fingering3` confusion.** Triplet digits arriving as
  `fingering3` cost −464 on Mozart 41 (`PROJECT_STATUS.md` line 44) — but that
  was an *export/consumption* bug (tuplets detected and never read, fixed in
  `d5079d5`), on engraved music. The residual detector confusion (`tuplet3` vs
  `fingering3`, both barely labeled) is a thin, mostly-engraved slice.
  **Low priority.**

### Excluded, with the reason

| excluded | why |
|---|---|
| `staff`, `stem`, `beam`, `barline*`, `brace`, `ledgerLine` | Classical-CV structural elements (`staff_detector`, `line_detection`, `measure_extractor`). YOLO cannot bbox a thin line, and boxing them trains them as **background**. Never label. Round-1 AUDIT dropped 24 such pre-labels by class before looking. |
| Free text — tempo/expression words, instrument names, rehearsal letters | **No YOLO class** (`textDynamic` is only for *dynamic* words). Handled by the direction-text reader (Surya + Tesseract union, `PROJECT_STATUS.md` Sept-2 entry), not detection. |
| Beams, augmentation dots, plain dynamics, tuplet markers, articulations (as *export* targets) | **Already closed in `export.py`** — detected-and-dropped, fixed without any labeling (`PROJECT_STATUS.md` lines 150-181). Labeling would not have moved them. |
| Slurs / ties (as a *recall* target) | The detector *reads* them (65/51 boxes) and the scan problem is the **opposite** — it *over*-fires on bled arcs (round-1 AUDIT: 34 false slur/tie pre-labels), which `min_fill_ratio` gates address, not more positive labels. The 2026-09 win was pairing/export, not recall. Borderline; not a survey row. |

---

## §2. The publisher axis (columns) — normalized to engraving-house style

The catalog's `publisher` field holds **213 distinct raw strings** across 235
editions (`publisher_families.py`). They collapse to **36 engraving-house
families**; the ones that matter for a survey are the ~15 with orchestral
repertoire on disk. **All 235 edition PDFs are present on disk** — `disk == eds`
for every family — so nothing here is un-surveyable for lack of a file. The one
family that *cannot* be surveyed for scan appearance is the modern-typeset /
born-digital bucket (only 5 of 14 are real scans; the rest are Boléro/WTC/Farrenc
typesets with no raster — flagged below).

Engraving **style** is the real axis: a hollow notehead's counter, a flat's
outline, a clef's weight all close differently across press, decade, and
national tradition. Grouping by exact string would split one Litolff cycle into
nine columns and merge a 1739 Bach print with a 1930 Breitkopf reissue. The
families, ranked by edition count (`* = orchestral works on disk`; era = plate
year, not IMSLP upload date):

| # | house family | eds | orch | scans | text-layer | era | style / tradition | already surveyed? |
|--:|---|--:|--:|--:|--:|---|---|---|
| 1 | **German Collected-Works** (Breitkopf tradition: *Werke* / Gesellschaft) | 42 | 38 | 38 | 12 | 1862–1893 | German critical-edition, dense | **Brahms 1** (round 2, *Sämtliche Werke*) |
| 2 | **Breitkopf & Härtel** (Leipzig, Partitur-Bibliothek + Haydn) | 40 | 24 | 39 | 12 | 1842–1899 | German house, classical→romantic | partially (via #1) |
| 3 | **C.F. Peters / Edition Peters** (Leipzig) | 18 | 13 | 17 | 0 | 1851–1888 | German, no text layers | **Mahler 5** (round 2, Peters 3087b) |
| 4 | **Eulenburg** (miniature scores) | 15 | 7 | 15 | 2 | 1899–1926 | miniature = small staff, hard | **Scheherazade** (round 2, plate 2957) |
| 5 | **Durand** (Paris) | 13 | 7 | 13 | 0 | 1874–1921 | **French** tradition, distinct glyphs | **no** — high value |
| 6 | **Simrock** (Berlin/Bonn) | 12 | 10 | 12 | 1 | 1847–1896 | German, Brahms/Dvořák | **Dvořák 9** (round 2, plate 10139) |
| 7 | **Litolff** (Braunschweig 1870) | 10 | 10 | 10 | 9 | **1870** | uniform cycle, plates 2765-73 | **Beethoven 5** (rounds 1 & 2) |
| 8 | **Universal Edition** (Vienna) | 9 | 8 | 9 | 1 | 1906–1935 | **20th-c Viennese**, Mahler | **no** — high value |
| 9 | **Jurgenson** (Moscow) | 9 | 9 | 9 | 0 | 1875–1911 | **Russian** tradition, Tchaikovsky | **no** — high value |
| 10 | **Novello** (London) | 7 | 5 | 7 | 2 | 1892–1921 | **English** tradition, Elgar | **no** — high value |
| — | Bote & Bock, Goodwin & Tabb, Belaieff, Gutheil, Hansen, Bessel, Aibl, Schott, Enoch, Hamelle, Ricordi, Schirmer, … (21 minor families) | 1–4 each | mixed | all | mixed | 1827–1925 | one-off national houses | no |
| — | **Other / modern-typeset / unknown** | 14 | 7 | **5** | 9 | — | born-digital typesets | ⚠️ **9 of 14 are NOT scans — cannot survey scan appearance** |

**Style clusters** (what actually varies the appearance):
- **German 19th-c** — #1, #2, #3, #6, #7. The bulk of the library and of the
  five round-2 batches. Broadly one tradition, but each press's plates differ
  enough to be worth separate columns (round 2 treated them as five).
- **Miniature** — #4 Eulenburg. Small staff height is its own appearance axis.
- **French** — #5 Durand. Distinct engraving; **not covered.** (Round 1's
  "Boléro" control was a *born-digital Durand typeset*, not a real Durand scan —
  so the French *scan* style is genuinely unrepresented.)
- **Russian** — #9 Jurgenson (+ Bessel, Gutheil, Belaieff). **Not covered.**
- **English** — #10 Novello (+ Goodwin & Tabb). **Not covered.**
- **20th-c Viennese** — #8 Universal (the Mahler cycle). **Not covered.**

**The four highest-value missing columns are #5 Durand, #8 Universal, #9
Jurgenson, #10 Novello** — four distinct national/period traditions, all
orchestral, all on disk, none yet touched. Representatives, chosen for
orchestral + resolution (resolutions from `benchmarks/omr-scan-e2e-2026-09/SCOPING.md`
where known):

| column | best representative | imslp | note |
|---|---|---|---|
| Durand (French) | Debussy, *La mer* | 15420 | canonical French engraving; La Mer is already a project reference work |
| Universal (Vienna) | Mahler 1 or 4 | 17070 / 280767 | 20th-c Viennese; extends the Mahler-Peters comparison to a second press |
| Jurgenson (Russian) | Tchaikovsky 4 | 377460 | ⚠️ SCOPING flags it **skewed** — good rotation stress, needs care; Tchaikovsky 6 (922722, has text layer) is a cleaner alternative |
| Novello (English) | Elgar 1 | 56155 | has a text layer (free part labels); Dvořák 8 (405841) is the alternative |

---

## §3. The matrix + sizing

### The matrix (symbol × house style)

```
                 German-19c ── Miniature  French   Vienna   Russian  English
                 (Lit/Bkpf/    (Eulen)    (Durand) (UE)     (Jurg)   (Novello)
                  Peters/Simr)
  R1 Hollow      ████████████  ████       ○        ○        ○        ○
  R2 Grace       ○             ○          ○        ○        ○        ○
  R3 Dynamics    ○             ○          ○        ○        ○        ○
  R4 Ornaments   ○             ○          ○        ○        ○        ○

  █ = cut & waiting (round 2, verdicts=0)   ▓ = landed (v7)   ○ = not started
```
Row 1 is filled across the five German+miniature columns and empty across the
four missing-tradition columns. Every other row is empty everywhere.

### Depth per cell (one sitting)

Round 1 was **48 cells → 29 boxes**; round 2 standardised on **56 cells/batch**.
A batch of **~40–56 cells is one comfortable sitting**. Keep it there — a
single-symbol sweep of 56 draw-from-scratch cells is a manageable session, and
the enclosed-white ranker's yield band means ~50 cells returns roughly 20–56
target boxes depending on the print's richness (Peters/Mahler ≈56, Simrock/Dvořák
≈19 — round-2 README).

### The density-collapse bound — this sizes the whole survey

**This is the constraint that stops the matrix from being "just label
everything."** Fine-tuning the shared detector on **low-density cells narrows
the density prior**, and that is precisely what collapsed dense-page notehead
detections **2506 → 114** in the clef fine-tune
(`project_clef_finetune_conclusion`, and why v5/v6's 62 clef cells are *held out*
of the catalog in `data/user-labeled/catalog-versions.txt`). Scan cells of
sustained orchestral lines are **inherently low-density** (a bar of half notes
has few symbols), so a survey that dumps hundreds of them into the catalog is
the same failure mode wearing a different hat.

Three mitigations make the survey safe, and they bound its size:
1. **Complete labeling.** Every symbol in a touched cell is boxed (or the cell
   is skipped), so a cell is not *artificially* sparse. The round-1 AUDIT is the
   caveat: on bad scans completeness was scoped to noteheads/rests/accidentals
   and slurs/clefs/dynamics went unlabeled — a real cost recorded, not hidden.
2. **Train as a MIX, never scan-only.** Scan cells are added to the dense base
   (v1–v4 ≈161 engraved cells + DSv2), which the domain-augmentation work
   (`project_domain_augmentation`) confirmed is the regime where real data helps
   and synthetic augmentation hurts. Scan cells must stay a **minority of the
   mix.**
3. **Gate every training run on `wtc_forgetting_eval.py`** — the audit tool for
   exactly this collapse. A run that improves scan duration recall but drops WTC
   dense-notehead recall is rejected.

**What box count is "enough"?** The working classes sit at 300–700 boxes
(noteheadBlack), but those teach the class from scratch on engraved music. The
survey's goal is narrower — teach the *existing* half/whole classes the *scanned
appearance* — so the plausible first target is **~150–300 diverse-publisher
boxes per class, added to the dense base**, then *measured* (scan `duration
recall` up? `wtc_forgetting_eval` flat?) rather than assumed. The binding
variable is not box count but the **count of low-density scan cells**: v5/v6's
**62** cells are already treated as risky enough to hold pending a measured run,
and the hollow row alone is round-1 24 + round-2 280 = **304 low-density scan
cells.** That number is why the survey must be **measured after the first
tranche before widening** (see §5).

### Total-size estimate for the FULL matrix

4 rows × ~10 useful columns × ~50 cells ≈ **2,000 cells / ~40 sittings / ~1,000+
target boxes.** Too large to commit to as one plan, and — per the density bound
above — probably *unsafe* to fold into one catalog even if labeled. Hence the
scoped options in §5.

---

## §4. The mechanics — reusing what exists

### The five round-2 batches ARE row 1, already prepared

They are cut, ranked, stubbed, and **waiting for hands** (`verdicts=0`,
`detections/` = 56 empty stubs each):

| batch dir | edition | cells | expected boxes |
|---|---|--:|--:|
| `…-peters-mahler5` | Mahler 5 Adagietto, Peters 3087b | 56 | ≈56 |
| `…-eulenburg-scheherazade` | Scheherazade, Eulenburg 2957 | 56 | ≈56 |
| `…-litolff-hires` | Beethoven 5 finale, Litolff 1870 | 56 | ≈42 |
| `…-breitkopf-brahms1` | Brahms 1, Breitkopf *Sämtliche Werke* | 56 | ≈23 |
| `…-simrock-dvorak9` | Dvořák 9, Simrock 1894 | 56 | ≈19 |

**280 cells, ≈196 hollow boxes expected.** Labeling these is the first and
largest piece of committed human work the survey needs — it exists because the
selection compute is the expensive part and it is already spent.

### The selection signal is per-symbol — name it for each row

Round 1 ranked by **meter shortfall** (a bar short of its meter is missing
something) — worth 4× uniform *there*, but round 2 measured that it **does not
transfer**: it ranks bars wrong for any reason (beamed-quaver Allegros yield
zero hollow heads), and on most editions the meter is never read (cut-common
movements can't be ranked at all — `select_short_bar_cells` is blind on them).
The row-1 selector that *did* work is the **enclosed-white ranker**
(`hollow_score.py`): count ink-ring-around-white-lens regions of notehead-counter
size in a cell's staff-line-removed crop, sample the **band 2–6** (not top-N —
the count inflates on light prints). Validated **91% precision** against round
1's own hand labels.

**Each future row needs its own selector** — none exists yet for rows 2–4, and
naming the signal is part of this design:

| row | selection signal (proposed) | reusable machinery |
|---|---|---|
| Hollow (R1) | enclosed-white counter ranker, band 2–6 | `hollow_score.py` + `rank_and_trim.py` ✅ exists |
| Grace notes (R2) | a **small** notehead-shaped CC within ~1 space of a full notehead (grace notes cluster by their host); or draw from known-ornamented movements | none — needs a `grace_score.py` sibling; `select_cells_orchestral.py` for the base cut |
| Small dynamics (R3) | bold-ink CCs in the **sub-staff gap** matching `p`/`f` letter aspect | the direction-text reader already finds sub-staff ink — reuse its candidate geometry (`score_placement_rules.py` region) |
| Ornaments (R4) | Bravura trill/turn/mordent **template match** in the **above-staff band** | mirror `key_signature_template.py`'s slide-a-template approach |

Existing selectors on main: `select_cells_orchestral.py` (general),
`select_short_bar_cells.py` (meter), `select_clef_cells.py`,
`select_timesig_cells.py`. A grace/dynamics/ornament sweep can cut with
`select_cells_orchestral` and re-rank with a new per-symbol scorer.

⚠️ **Portability gotcha:** `rank_and_trim.py` hard-codes a *worktree* `REPO`
path (`.claude/worktrees/transcription-overnight-progress-426c90`). Reuse from
the main checkout must fix that to `library_root()` or a `--repo` arg, or it
will look for cells in a stale tree.

### The single-symbol pass UI is on main

`tools/omr/annotate/server.py` supports **single-symbol pass mode** via an
optional per-batch **`batch_config.json`** (server.py §266): a pass names the
class(es) it is for, so the picker shows one symbol instead of 174, and the
`on_line`/`in_space` pair is chosen by *click position* (geometry, not two menu
entries). Per-cell **`inspected_passes`** tracks which sweeps have swept a cell,
so "48/48 inspected" is provable from state even when an inspected-and-empty
cell writes no verdict file (the exact ambiguity round-1 AUDIT had to reconstruct
by hand). **The round-2 batches do not yet ship a `batch_config.json`** — adding
one per symbol pass is a one-file step that makes a multi-symbol sweep fast.

Draw-from-scratch is mandatory on scans: round-1 AUDIT measured **116 of 117
model pre-labels false** on that print, so `detections/` ships empty and every
box is a human one.

### How a batch flows, end to end

```bash
# 1. cut every measure cell on chosen pages (page 1-based on the CLI)
PYTHONPATH=. python3 benchmarks/omr-labeling-hollow2-2026-09/cut_candidate_cells.py \
    --out-dir benchmarks/omr-labeling-survey-2026-09-<house-work> \
    --plan "<tag>=/abs/score.pdf:P:999"
# 2. rank by the row's scorer, keep 56, write HINTS (avoid pages the scan
#    benchmark scores — labelling those trains on the benchmark)
python3 benchmarks/omr-labeling-hollow2-2026-09/rank_and_trim.py <batch-dir> 56
# 3. (optional) drop in batch_config.json naming the pass's classes
# 4. label — draw-from-scratch, complete per cell
python3 -m tools.omr.annotate.server --bench-dir <batch-dir>   # → :5050
# 5. convert verdicts → YOLO labels (--dry-run first)
python3 -m tools.omr.training.verdicts_to_yolo_labels --verdicts-dir <batch-dir>/verdicts \
    --manifest <batch-dir>/cells.json --version-name v<n>-2026-09-<row>-<house> \
    --out-root data/user-labeled --labeler sean --description "..."
# 6. COMMIT the verdicts (irreplaceable human work; cell PNGs are gitignored)
```

### Rolling the survey up into training WITHOUT triggering the collapse

Catalog membership is a **deliberate training decision**, not an inventory:
`data/user-labeled/catalog-versions.txt` lists exactly the versions
`build_catalog_yaml` unions, and `test_training_pipeline.py` pins it, so
admitting a survey version is a loud, reviewed edit. The rollup is therefore:

1. Land each labeled batch as its own `v<n>-…` (verdicts committed) — **but do
   not add it to `catalog-versions.txt` yet.**
2. After a *tranche* of the survey is labeled (e.g. all of row 1), do **one**
   measured training run that adds the tranche to the dense base, gated on
   `wtc_forgetting_eval.py`, and scored on `scan_eval.py` duration recall.
3. Admit the tranche to the catalog only if the gate holds. If it collapses,
   the labels are still safe on disk and the mix is retuned (weight down /
   subsample) rather than the labor lost.

This is the same discipline the v5/v6 hold-out already encodes, applied to the
survey.

---

## §5. Scope decision — what goes to Sean

The full matrix is ~2,000 cells / ~40 sittings and is probably unsafe to fold
into one catalog. Three bounded options, each a clean stopping point:

### Option A — Finish the hollow row (minimal, highest-confidence)
Label the **five already-cut round-2 batches** (280 cells, ≈196 boxes), convert,
and run **one measured, forgetting-gated training** on hollow across the five
German+miniature styles.
- **Cost:** ~5 sittings of labeling already-prepared cells. No new cuts, no new
  selectors, no new classes.
- **Buys:** the single measured #1 lever, across the five dominant engraving
  styles, and — critically — **the first evidence of whether 300 low-density
  scan cells move detection or collapse the density prior.** That answer
  gates everything else.

### Option B — Hollow row complete across ALL traditions + Tier-2 seed (**recommended**)
Option A, then **only if its training gate holds**:
- extend hollow to the **four missing traditions** — Durand (French), Universal
  (Vienna), Jurgenson (Russian), Novello (English) — 4 new batches (~200 cells);
- cut **one grace-note** and **one small-dynamics** batch on the richest
  publishers (~100 cells) to *obtain the measurement* those blind spots lack.
- **Cost beyond A:** ~6 new cuts + ~11 more sittings; ~600 new cells total;
  needs a `grace_score.py` and a dynamics selector (small, named in §4).
- **Buys:** the measured #1 lever across **every engraving tradition in the
  library**, plus a priced probe of the next two blind spots before any deep
  commitment.

### Option C — Full multi-symbol survey (deep)
Rows 1–4 × ~10 styles. **~2,000 cells / ~40 sittings.** Not recommended as a
single commitment — and per the density bound, not safely a single catalog.
Revisit *per row* only after Option B measures whether Tier-2 pays.

### Recommendation

**Sequence A → (gate) → B.** Start by labeling the five batches that already
exist — it is the highest-evidence work, it is already cut, and it doubles as
the experiment that tells us whether low-density scan cells are trainable at all.
Hold `catalog-versions.txt` until the forgetting gate passes. If it does, widen
hollow to the four missing traditions (the library's French, Russian, English
and Viennese styles are genuinely unrepresented) and seed grace-notes +
dynamics with one batch each to measure them. Treat Option C as a menu to draw
single rows from later, never as a block to commit to now.

The honest headline for Sean: **"a helpful amount" is Option B — roughly 11–16
sittings of labeling, front-loaded on the five batches already waiting, gated on
a training measurement after the first five so we never cut cells we can't safely
train on.**

---

### Files in this directory

| file | what |
|---|---|
| `SURVEY_DESIGN.md` | this design |
| `publisher_families.py` | normalises catalog publishers → 36 house families, checks disk presence (the §2 evidence) |
| `labeled_coverage.py` | counts hand-labeled boxes per class across v1–v7 (the §1 evidence) |
