# Hand-labeled truth: what we have, how it is used, and the plan to test only against it

**Date:** 2026-10-08 · **Status:** ACCEPTED by Sean 2026-10-08 (decisions in §5). This is ROADMAP **1.7**. Phases A (but A3), B and the Phase C tools built 2026-10-08 in `tools/omr/hand_truth/`; the runbook for the first page is in `data/hand-truth/README.md`.
**Path:** STAGED for everything this plan would score. LEGACY is touched only where §3 says it is.

Every number below was measured on this tree on 2026-10-08. The commands are in §6. Where a number comes only from a FINDINGS.md or DECISIONS line, it says so.

---

## 1. What we have

### 1a. YOLO box labels: `data/user-labeled/v1…v23`

There are 23 versions, 670 unique measure-cell crops from 85 source pages and 13 PDFs, 288 MB, all committed. Of these, 590 cells are in the training catalog (`catalog-versions.txt`).

**No cell is labeled for everything on it, and no page has every cell labeled.** What a pass covered is recorded in `inspected_passes` on the source verdicts. A version's palette only says what someone *could* have boxed (ROUND3_COMPLETENESS.md).

| tier | versions | cells | what a HUMAN did | truth for |
|---|---|--:|---|---|
| **1. Drawn from scratch, palette recorded** | v22 (Dvořák 9, Simrock pp. 9–20) | 110 | Sean drew every symbol in the 27-class `draw-rich` palette (109 cells carry the stamp; `dvorak9-p19-sys0-s0-m0` saved none); 88 cells also had a ties/slurs reconcile | those 27 classes |
| **1b. Drawn from scratch, palette NOT recorded** | v3 (Mahler 5), v4 (La mer) | 64 | drawn by hand; no record of which classes were in scope | unknown until checked |
| **2. Completion pass on a model pre-label** | v18 (Brahms 1, Breitkopf pp. 2–4) | 56 | confirm/reject/add over the 23-class `completion-full` palette, plus a hollow-head pass | 23 classes; recall partly bounded by what the model showed |
| **3. Hand-labeled for some symbols only** | v13–v17, v19–v21 (Litolff, Peters, Eulenburg, Simrock, UE, Novello, Durand) | 264 | by hand: hollow heads, rests, accidentals, clefs (on 23 cells). **Model boxes, spot-checked 8 per class:** black heads, dots, dynamics, slurs, ties | hollow / rests / accidentals / clefs only |
| **4. Verdicts on an older model's boxes** | v1, v2 (Beethoven 5, Mahler 5) | 97 | TP/FP on what that model drew, plus 38 added boxes | nothing complete; the model's misses are silently absent |
| **Single family, not in the catalog** | v5–v6 (clefs), v7–v12 (hollow, superseded), v23 (arcs) | ~250 | one pass each | that family only |

**Never labeled, in any tier:** beams, stems, ledger lines (5 boxes in total), time signatures, most flags, articulations, tremolos, barlines (capped out at nc=208) and text. Even inside swept cells, about 20% of rests and accidentals are still unboxed (UNBOXED-AUDIT.md).

### 1b. Human-checked work that never became a version

| set | cells | content |
|---|--:|---|
| `omr-queue-rests-2026-09` | 192 | 265 real / 84 not / 7 unsure. ROADMAP calls it "a clean truth for rests" |
| `omr-labeling-marks-focus-2026-09` | 101 | 166 human boxes |
| `omr-labeling-clefs-2026-09` | 24 | 85 human boxes |
| `omr-labeling-grace{1,2}-2026-09` | 255 | inspected for grace notes; 30 found. The rest are real negatives |
| `omr-labeling-brahms1-focus-2026-09` | 11 | 20 human boxes |
| `omr-labeling-timesig-2026-07-13` | 11 | 22 human boxes |
| `omr-queue-accidentals-2026-09`, `omr-queue-ties-2026-09` | 155 / 104 | **pre-filled, never reviewed.** A queue, not labels |

### 1c. Structure truth (whole page, no notes)

- `benchmarks/omr-scan-e2e-2026-09/works.json`: 20 hand-read page rows giving the bar window, staff→part map and clef/key per staff. Litolff 984073 p1–4, Litolff 575951 p1–4, Dvořák p5–7, Brahms p1–4, Mahler 5 p2–5, Bach p1.
- `omr-keysig-truth-2026-09/truth.json`: key and clef per staff, Litolff p1–4 (75 staves). Read by a session; Sean confirmed it in one line.
- `omr-phase1-baseline/ground-truth.json`: systems, staves and bars on 3 pages (2 by Sean).
- `omr-phase4-lines/hand-labeled-{stems,beams}.json`: 94 stems and 46 beams on about 15 cells.

### 1d. Sean's print checks on crops

- 10 `out/print/ADJUDICATION-sean-*.json` files, each 3–28 crops, almost all on Litolff p1–4 and Brahms p0–3.
- Sean's box edits in the review UI on 3 Litolff staves (305 actions, `omr-stage-review-2026-09/out/sean-*`).
- About 82 more verdicts exist only as prose in DECISIONS.md. **The raw sheets for at least 15 of them are gone** (e.g. `night_1008/`, `farhead_vs_geometry/`, `ledgers/*`).

### 1e. Not Sean's, though often cited as if it were

These were judged by a Claude session:
- `omr-stem-crop-pass-2026-09/ADJUDICATION-*.json`: 255 crops, `"adjudicator": "Claude Opus 5, by eye"`. These are the source of "96 of 96 stems", "103 confirmed heads" and "46 of 180 not noteheads".
- stem-attribution, chord-stroke-join, note-where-silence, veto-refusal, label-contradiction (158 rows), and most of the 08-28 → 08-31 clef/key/score-order "ground truth" files.

Under rule 7 these are a model's own judgment. The inventory (A1) marks them `labeler: claude`.

### 1f. The acceptance count pages

| page | cells on page | cells with any hand label | which tier |
|---|--:|--:|---|
| Brahms, Breitkopf 317803, PDF index 1 | 210 (28 staff-systems) | 19 (9%) | tier 2 (completion) |
| Beethoven 5, Litolff 984073, PDF index 3 | 408 (24 staff-systems) | 7 (2%) | rests + accidentals only |

⚠️ **Leakage:** 19 Brahms count-page cells (15 train / 4 val) and 7 Litolff count-page cells (5 / 2) are in the catalog that production weights were trained from. A detector score on those pages is partly scored on training data.

---

## 2. How it has been used

| use | truth source | hand labels? |
|---|---|---|
| Detector training and its val mAP | `data/user-labeled` catalog | yes; this is almost the only use of the box labels |
| Forgetting gate (`wtc_forgetting_eval.py`) | Sean's verdicts on an OLDER model's boxes | partial: complete only for noteheads |
| Hollow axis (`hollow_eval.py`) | **reference MusicXML**, one page | no |
| Scan end-to-end (`scan_eval.py`, 20 rows) | **movement MXL trimmed to the page**, plus works.json | structure only |
| `acceptance_quick --full` per-bar score | **reference MXL** via works.json | no |
| Far-head truth set (2.44c) | staff positions **from the encoding**, Sean overriding 2 heads | no |
| `acceptance.py` on scans | proxies only, plus Sean's count | the count was **never taken** (all 4 SEAN sheets are blank; 1.4 deferred 09-30) |
| Engraved headline and engraved acceptance doc | Verovio render / MusicXML | n/a: exact by construction |
| `tools/omr/tests` (310 files) | ~252 unit/synthetic; 18 load a hand-truth file; 15 use an encoding | a few |

**No benchmark or test scores the pipeline's reading of a scanned page against hand-labeled symbols.** Every music-level number on a scan comes from an MXL.

### Why the MXL is not page truth (documented failures)

1. **Condensed staves ≠ encoded parts.** For example, 12 printed staves against 18 parts. 87% of the "entire staff" edits came from condensation. Sean, 09-05: *"I am not sure our MXL will work as a ground truth — unless we can determine that the amount of staves matches."* Only 10 of 20 rows were usable per staff (`omr-truth-divergence-2026-09`).
2. **Encoding conventions.** A clef is printed per system but declared once; a slur is encoded at both ends; `C` vs `4/4` costs 3 edits per staff.
3. **The references are themselves wrong.** Two far-head references were overruled by Sean (DECISIONS 10-01, 10-04). A dossier key of −3 disagrees with a plate that prints none. Two truth files disagree on Mahler's part count.
4. **Alignment.** Bar numbering after tacet systems, a lone-page offset, and measures paired by position.
5. **The metric can be gamed.** OMR-NED pays for emitting fewer symbols. It was retired 09-08 for scans.
6. **Edition.** References join on `work_id`, not on the edition that was scanned.

---

## 3. The plan

**Goal:** every MEASUREMENT on a scan — benchmarks, acceptance, A/B gates, weights tests — is scored against hand-labeled page truth. **Every box Sean draws or confirms is also training data** (Sean 10-08), except on pages held out for testing (§5 Q7). Unit tests are not in scope. GATHER + ADJUDICATE first, per Sean 09-30.

**Why full-ink labeling is also the training fix:** a fine-tune treats any unboxed ink on a training cell as background. That is how beams went 127 → 0 and how rests and accidentals were suppressed in round 3 (CLAUDE.md §9; ROUND3_COMPLETENESS.md). A page with every bit of ink boxed is the first labeling that cannot teach the detector to delete a class.

### The labeling unit (Sean 10-08)

- **Sean labels one cell at a time**, as now.
- **Every box is STORED in page pixels**, at a stated DPI, in one per-page store. The cell is only a window onto the page.
  - When a cell is cut, the cutter records its exact page rectangle and scale, so cell ↔ page is an exact transform, never a re-derivation.
  - Because the store is per page, a mark in the padded overlap of two cells is ONE box: drawn in one cell, it shows as already present in its neighbour.
- **Every bit of ink must sit in some cell.** Measure cells do not reach the page furniture, so a page also gets:
  - a left-margin cell per system: instrument names, braces, brackets, the first clef / key / time signature;
  - a top cell: title, tempo, composer, movement heading;
  - a bottom cell: page number, plate number, footnotes.

  This is what captures the global information on a first page.

### Phase A: Make what exists honest (no labeling)

- [x] **A1. One generated inventory** (2026-10-08). `python3 -m tools.omr.hand_truth.inventory` writes `data/hand-truth/INVENTORY.json` from the tree: every label version (tier, cells, boxes, pages, recorded passes, box origin), every cell-verdict set under `benchmarks/` (cells a human acted on vs pre-fill only), every adjudication file, the structure rows. `--check` exits 1 when the committed file is stale. Nothing in it is typed except the per-version tier (`inventory.TIERS`, with its basis).
- [x] **A2. Provenance in the inventory** (2026-10-08), not by editing other benchmarks' files. Who judged comes from each file's own `adjudicator` field or its own text ("not Sean's"): 10 Sean, 7 Claude, **9 unrecorded** — never guessed.
  - Not done: the §1d prose-only numbers (`raw: gone`) — they live in DECISIONS, not in files the generator can read. Folded into A3.
- [ ] **A3. Fold Sean's scattered crop verdicts** (10 JSON files plus the prose entries whose sheets survive) into one append-only ledger keyed by page + box.
- [x] **A4. Hold-out list** (2026-10-08, §5 Q7): `data/hand-truth/held-out.json`. The inventory computes which held-out pages production already trained on: **Brahms PDF index 1, Litolff 984073 index 1 and 3**.
- [x] **A5. Weights lineage** (2026-10-08, Sean: *"How do we know where the individual notes from our current weights came from?"*). Declared with evidence in `data/hand-truth/weights-lineage.json`; the inventory expands it into cells, pages and box origin — production's features were trained on 7,288 boxes, **3,871 from label files and 3,417 (47%) added by the previous model**. `--verify-checkpoints omr-weights/` compares the declaration with each `.pt`'s own `train_args` (needs torch; on Sean's machine — not yet run).

### Phase B: The page-truth store (code; runs anywhere)

- [x] **B1. Schema** `data/hand-truth/pages/<edition>/<pdf_page_index>.json` (2026-10-08, `tools/omr/hand_truth/store.py`). Pre-fills wait in a `queue` and become truth only through `confirm_prefill` / `fix_prefill`; the store refuses any labeler but Sean; states advance one step at a time.
  - Page DPI and size.
  - Per box:
    - page-pixel box and class (the 208-class space plus customs: barlines, text, noise);
    - `origin` (`drawn` / `prefill-confirmed` / `prefill-fixed`) and `labeler`;
    - for text: the transcribed string;
    - for a notehead: owner staff and staff position.
  - Per cell: its page rectangle and `inspected_passes`.
  - Per staff: "lines right" (yes / no).
- [x] **B2. Completeness is computed, never asserted** (2026-10-08, `completeness.py`; ink components by the repo's own `cv2.connectedComponentsWithStats`, 8-connected, staff lines removed first, specks counted not dropped). The scorer side of the refusal waits for D1.
  - A family is complete on a page only when every cell on it is inspected for that family.
  - The **ink-coverage control**: every connected ink component on the page lies inside a box or a `noise` mark, or it is listed for Sean.
  - The scorer refuses to score an incomplete family. It does not score it as zero.
- [x] **B3. Training export** (2026-10-08, `export_yolo.py`): page boxes → YOLO cell labels with the existing converter's vocabulary and line format. Refuses a held-out page and a page still `labeling`; SKIPS any cell not inspected for every bit of ink (its unboxed ink would train as background). Writing the result as a `data/user-labeled/vN` version waits for the first checked page.

### Phase C: Labeling, cell by cell, with pre-fills (Sean's time; the main cost)

- [x] **C1. Annotate server on the page store** (2026-10-08: `hand_truth/session.py` cuts the page — product-path measure cells at their own `bbox_page_px` plus margin/top/bottom REGION cells for every other bit of ink; `hand_truth/bench.py` lays it out as an ordinary bench and folds every save back in page pixels, idempotently, refreshing overlapping cells; `annotate/server.py --page-store`, a sync failure answers 500; `text` and `noise` join the picker in that mode only; staff lines are five thin `staff` boxes on each staff's first cell).
  - Same cell-at-a-time UI and hotkeys.
  - Reads and writes the page store; adds the margin / top / bottom cells and a staff-lines check.
  - Every box carries its origin.
- [x] **C2. Pre-fills, in order of trust** (2026-10-08: old labels re-projected through `recut_cells`' exact frame check, newest version first, a wrong-frame cell refused; the detector per cell; page-level dedupe, an old human box always wins. NOT BUILT: a pre-fill from the CV stem/beam/ledger readers — the detector supplies beams and ledger lines, stems will mostly be drawn) (Sean 10-08: pre-fills allowed). A pre-fill is a queue, never truth, until Sean acts on it.
  1. Sean's existing labels on that page, re-projected into page pixels (`recut_cells`' frame check; refused where the frame does not match).
  2. Production weights.
  3. The CV readers: staff lines, stems, beams, ledger rungs, barlines.
  4. OCR for text.
- [ ] **C3. Time the first system**, and price the rest of the plan from that, not from a guess.
- [ ] **C4. Blind re-label of one system a week later.** The agreement is the noise floor for every score on these pages (rule 7).
- [x] **C5. Claude double-checks the page** (Sean 10-08; built 2026-10-08: `hand_truth/checks.py` — the fixed checks below plus the ink control, raised once and never again after Sean resolves them; the visual pass files flags with `session raise`; `advance --to checked` refuses while any flag, pre-fill or unswept cell remains).

  Claude only FLAGS. Sean decides every flag, and Claude never edits the truth: a model's judgment is not evidence (rule 7).

  1. **Fixed checks first** (no model, cheap, cannot hallucinate):
     - ink left over by the coverage control;
     - duplicate boxes on one mark;
     - a dot with no head to its left; an accidental with no head to its right;
     - a stem with no head; a beam that touches fewer than two stems;
     - a head outside the staff with no ledger line (Sean 09-29: none exists);
     - tied heads at different staff positions;
     - a system that starts with no clef or key;
     - a head whose stated staff position disagrees with its box against the local staff lines.
  2. **Then a visual pass:** Claude looks at each cell with its boxes drawn and lists suspected misses and wrong classes.
  3. **Flags open as a queue** in the same annotate UI, and each one is accepted or rejected by Sean. The share Sean accepts is recorded per page, so we learn whether the check earns its time.
- [x] **C6. LilyPond side by side, one measure at a time** (Sean 10-08; built 2026-10-08: `hand_truth/perfect_eyes.py` runs `pipeline.run_staged` with a detector stand-in that returns the page's boxes; `hand_truth/review.py` slices each printed bar by ordinal with clef/key/time carried, renders it with `musicxml2ly` + `lilypond -dcrop`, and serves the marks into `<page>.review.json` keyed to a hash of the boxes; a part whose bar count differs is shown NOT ALIGNED, never guessed; `advance --to verified` needs every bar ok on the current labels).
  - **Boxes are not music.** Something has to turn them into notes and rhythm.
  - **Proposed: feed the hand boxes to the STAGED pipeline in place of the detector** ("perfect eyes").
    - Sean's labels supply the staff owner and staff position, so what remains is mainly rhythm grouping.
    - Run ADJUDICATE → EXPORT, then `--lilypond --pdf` through the existing `staged/lilypond.py`.
  - **Render per measure.** Each measure becomes one small LilyPond score, carrying the clef / key / meter in force. It sits beside the print crop of the same measure, cut at the gather's DPI, on a page built from `build_count_sidebyside.py`'s pieces.
  - **Sean marks each measure:**
    - `ok`;
    - `label wrong` → back to that cell;
    - `reader wrong` → the reader misread perfect boxes, which is a free finding for Phase 2 (traceable with `staged.trace`).

    Bars the pipeline holds out show as marked-unread, never as silence.
  - **Byproduct:** the same run is the ceiling measurement — what the reader produces with perfect eyes.

**A page's life:** `labeling` → `checked` (C5 flags all resolved) → `verified` (C6, every measure `ok`). Only a `verified` page is truth for D, and the export to training (B3) uses `checked` or later.

**Page order** (Sean: start on a first page for the global information):

| # | page | why | cells (est.) | already labeled |
|---|---|---|--:|--:|
| 1 | **Brahms, Breitkopf 317803, PDF index 0** — mvt 1 first page | smallest first page (14 staves, bars 1–7); names, meter, key, tempo | ~98 + margins | 0 |
| 2 | Brahms, Breitkopf, PDF index 1 — count page | acceptance count page, next to #1 | 210 | 19 (tier 2) |
| 3 | **Litolff 984073, PDF index 1** — mvt 1 first page | second publisher; first page (12 staves, bars 1–16) | ~192 | 9 (tier 3) |
| 4 | Litolff 984073, PDF index 3 — count page | acceptance count page | 408 | 7 (tier 3) |
| 5 | **Simrock Dvořák 9, PDF index 4** — mvt 1 first page | third publisher; v22 tier-1 labels on later pages | ~120 | 0 |
| 6+ | one first page each: Peters, Eulenburg, Universal, Novello, Durand | multiple publishers (Sean 10-08) | — | tier-3 cells on nearby pages |

Each first page has a hand-read `works.json` row (bar window, staves, clef/key) to check the structure labels against.

### Phase D: The scorer (STAGED, GATHER + ADJUDICATE)

- [ ] **D1. `hand_truth` scorer.** For a record and a hand-labeled page, report:
  - per family: box recall / precision;
  - per notehead: owner right / wrong / abstained, and staff position right / wrong / abstained;
  - per staff-system: clef / key / meter and instrument name.

  Matching is by box overlap, the same as `readout diff`. Results feed `acceptance_quick` as a third view.
- [ ] **D2. Controls that can fail (rule 7).**
  - One-staff shift of the truth: owner accuracy must collapse.
  - The truth scored against itself: must be perfect.
  - Each is run RED first and the commit says so.
- [ ] **D3. Retire the MXL as a scan headline.** `scan_eval`, `acceptance_quick --full`'s per-bar score, the 2.44c far-head set and `hollow_eval` either move to the hand pages or are marked "control: encoding" in their FINDINGS. **The engraved Verovio page truth stays** as the engraved control (Sean 10-08).

### Phase E: Grow the set

- [ ] **E1.** The remaining carry pages (Litolff PDF index 2, Brahms indices 2–3), so a whole gather to the count page is scored on every page it reads.
- [ ] **E2.** Pages 6+ above.
- [ ] **E3.** Promote the §1b human sets (rests, marks-focus, clefs, grace negatives) and review the two pending queues, so the old cell labels and the new pages are one corpus.

---

## 4. Running progress

| phase | items | done |
|---|--:|--:|
| A. honest inventory + lineage | 5 | 4 (A3 open) |
| B. page-truth store | 3 | 3 |
| C. label, Claude check, LilyPond side by side; pages 1–5 | 6 + 5 pages | tools 4 of 6 (C3 timing and C4 blind re-label need a labeled page); pages 0 |
| D. scorer + controls | 3 | 0 |
| E. grow the set | 3 | 0 |

---

## 5. Decisions

**Made by Sean 2026-10-08:**

1. **Classes: everything on the page — every bit of ink.** Two items are labeled differently, never skipped:
   - staff lines are CONFIRMED per staff, not drawn;
   - stems, beams and ledger lines are always pre-filled from the CV readers and confirmed or fixed, not drawn from nothing.
2. **Unit:** Sean labels one cell at a time; storage is page pixels (the unit section above).
3. **Engraved control:** keep the Verovio page truth.
4. **Pre-fills:** allowed; existing labels first.
5. **First pages first**, for instrument names, time signatures and the other global information; **multiple publishers**.
6. **After each page:** Claude double-checks it (flags only; C5), then the labels are rendered through LilyPond beside the print, one measure at a time, for Sean's visual check (C6).

7. **Training vs testing** (Sean 2026-10-08: "Yes"). Brahms PDF index 0–1 and Litolff 984073 index 1 and 3 never train any weights that are TESTED on them (`data/hand-truth/held-out.json`); every other labeled page trains. Shipped weights may train on everything, and their score on the held-out pages is then never quoted as evidence. The leak is to be MEASURED on the Brahms count page once it is complete: production's recall on the 19 cells it trained on vs the other 191.

   A reader-stage A/B on one set of weights is unaffected either way, because both arms see the same detector. A weights test is not.

---

## 6. How these numbers were measured

- **Per-version cells and boxes:** `data/user-labeled/v*/labels/*.txt`. Cell ids are mapped to PDF and page through every `benchmarks/**/cells*.json` manifest (all mapped except v6's 47 clef cells, whose manifest names no PDF). All of §1a is now regenerated by `python3 -m tools.omr.hand_truth.inventory`.
- **Completeness:** the union of `inspected_passes` over every `benchmarks/**/verdicts*/` and `*merged*/` verdict file per cell_id. Versions v1–v6 record none; their tier comes from the metadata totals (`n_tp` / `n_fn_added`) and descriptions.
- **Count-page size:** the sum of printed bars × staff-systems in the `counts/*-SEAN-*.csv` sheets. First-page sizes are staves × bars from `works.json`, before margin cells.
- **Leakage:** `grep` of the count-page cell ids in `_catalog_train.txt` / `_catalog_val.txt`.
