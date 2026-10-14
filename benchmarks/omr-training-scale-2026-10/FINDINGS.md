# ROADMAP 2.110 -- is the training scale (not the labels) why every fine-tune deletes beams / ledgers / ties?

2026-10-13, branch `lane-2.110-train-scale`, not merged. Detector only (GATHER+ADJUDICATE records, `--through adjudicate --no-surya --no-ocr`).
Production weights NOT switched; no product code touched. Weights in `omr-weights/candidates/scale2110-*` (gitignored), records in `runs/2.110/` (gitignored).

**CONVENTION ASSUMED:** the model's features are tuned to a staff space; inference shows it 16 px (`yolo_detector.TARGET_STAFF_SPACE_PX`), the 2.4b
fine-tune recipe shows it ~48 px, and that mismatch (not the labels) drives the class deletion.
**WHAT WOULD FALSIFY IT:** beams / ledger lines / ties still collapse (and the hollow gain is lost) when the same fine-tune is shown cells at staff space 16.
**NOT CONFIRMED:** by Sean on any print; every number below is against Sean's Brahms hand truth or his Litolff TEST cells, one epoch, one seed.

**One-line verdict: NOT SUPPORTED.** Matched scale (the packed arm) keeps beams (Brahms recall 78% vs production 80%, OLD 54%) but loses ledger lines (45% vs 71%; Litolff
page 2 boxes vs production's 103), ties on Litolff (5 vs 18 boxes), time-sig digits (38% vs 79%) and the hollow gain (Litolff clean recall 34% vs production 74% vs OLD 88%).
It does not keep ledgers/ties within ~10% of production and does not keep a hollow gain. The damage is not simply the scale mismatch.

## 0. What the cell check changed (Sean 2026-10-13: "Yes leave them out")
Staffless cells (width < 500 px: barline slivers, black blocks, fragments with no five-line staff) are **dropped from BOTH arms** (train list and val list), so the arms
differ only in scale. Count: **18 unique train cells + 2 unique val cells** (all in v1-v4), of the 495 + 96. Survey check: `out/print/2.110-staff-space-check/` (26 cells,
independent run-length method vs the comb: 18 of 26 within 2%; 567/595 within 5% over the whole set; ~8/595 cells have no staff in view). OLD is therefore NOT the 2.4b raw control
bit for bit (that run used the unfiltered mix; its last.pt is not on disk anyway) -- it is the same recipe on the filtered list, and it reproduces the 2.4b damage on Litolff (below).
Distribution after the exclusion, one tool (`verify_shown.py`, the real ultralytics `YOLODataset.load_image`, measured on the ink columns): OLD @896 p10/median/p90 = 28.0/48.2/72.7
(5.5% of cells within 8-22); MATCHED @640 = 15.8/16.0/16.0 (and the loader rescaled 0 of 515 images again; OLD rescaled all 477); inference (product cells at `imgsz_for_cell`) = Brahms 16.0
(p10 16.0, p90 16.8), Litolff 16.0 (15.5-16.2). Default mosaic/scale aug (scale=0.5, x U(0.5,1.5)) multiplies all arms alike.

## A. Making the test airtight
**A.1 Leakage -- FOUND, 9 test cells.** `leakage.py` (SHA-256 of pixels, then template match of every training/val image against both test pages rendered at 600 dpi and scaled to staff space 25;
cells are cut by the product cutter). Result (`leakage.json`, `leakage.log`): **Brahms 317803 pdf 0: no leak** (best template 0.911; controls = product cells cut from the page and cropped score 0.975-0.979).
**Litolff 984073 idx 1: v13 (`beet5-p2-*`, Beethoven 5 Litolff, page index 1) holds 9 cells that carry the same (system, staff, measure) key as 9 of Sean's 104 TEST cells** -- 1 pixel-identical
(`s0-st2-m3`), the others the same cell re-cut (template scores 0.953-0.996). They hold 9 of the 59 TEST truth heads. The 2.4b FINDINGS' "never trained on" is wrong for those 9 cells, and
production itself was trained on v13, so the leak is in production AND every fine-tune. Control caveat: one of three control crops on the Litolff page scored 0.777 (the other two 0.961, 0.985), and the
dHash near-duplicate net (708 pairs <= 10 bits) is useless on mostly-white cells; only the exact hash and the template match are evidence. **Handling:** every Litolff number below is shown on all 104
cells AND on the 95 clean cells (50 heads); the training mix is unchanged (v13 stays in all arms, as in the 2.4b recipe).
**A.2 Damage scored against truth** (`score_truth.py`): Sean's Brahms 317803 pdf 0 hand truth (1,566 boxes; now 32 hollow heads in scope, not the 27 of the 2.4b text -- Sean has labelled more since), per
class group over the cells he inspected for that family; recall = truth boxes matched by a same-class read box / truth boxes, precision = read boxes matching a truth box / read boxes (IoU >= 0.3,
`readout.match_glyphs`, each box once); loose recall (IoU >= 0.1) is printed so thin-box IoU is not the reason (it never differed by more than 0.03).
**A.3 Controls that fail** (printed before any number, run on production's real glyph list, abort otherwise): truth vs itself = 1.0/1.0 for every group PASS; all beams deleted: beam recall 0.80 -> 0.0, no other
group moves PASS; every box shifted 3 spaces (96 px): max recall 0.077 PASS; beams x3 (shifted copies): recall unchanged, precision 0.23 -> 0.08 PASS. `score_hollow.py` reuses `score_ab.py`'s controls
(self-match 59/59, shifted 0/59).
**A.4 Production re-scored in the same run, same tool**: Litolff hollow 43/59 = 72.9% recall, 48/54 = 88.9% precision, Brahms hollow boxes 64 (26 extra) -- identical to the 2.4b record (independent reproduction of
the frame; no number copied). **A.5** shown-space: section 0.

## B. The experiment (`train_2110.sh`; `build_arms.py`, `build_packed.py`)
All arms: from PRODUCTION (`hollow-graft-shift09`), 1 epoch, seed 0, mps, `nice -n 10`, flags of `train_2.4b.sh` (batch 8 / workers 2 / fliplr 0 / flipud 0 / hsv_h 0 / hsv_s 0; default mosaic, scale aug, hsv_v 0.4), the CONTROL mix
(v1-v4 2x dense + v13-v22 distill25; NO v24), filtered list (600 train lines). Raw `last.pt` read as the fine-tune (no graft), as in the 2.4b diagnostic rows.
* **OLD**: imgsz 896 (the 2.4b CONTROL recipe), cells untouched.
* **MATCHED** (first attempt, CONFOUNDED): each cell resized by 16/its measured space, ONE cell centred on a white 640x640 canvas (cells wider than 640 cut into overlapping tiles, box kept if >= 50% inside; 31 boxes dropped),
  imgsz 640, 666 canvases. ~80% of every canvas is white pad, which changes the image statistics (BatchNorm, mosaic of white canvases) as well as the scale.
* **PACKED** (the real test of scale alone): the same pieces, shelf-packed 3.5 to a 640 canvas (191 canvases), batch 2 / nbs 18 (accumulate 9) so iterations (96 vs 75) and optimizer steps (~11 vs ~9) are close to OLD's; each cell is presented once.
Shown space verified for OLD and MATCHED (section 0); PACKED uses the same resize code, not re-measured (a multi-cell canvas has no single staff for the tool).
Disk was full (< 1 GB) during the PACKED run: it crashed writing the extra `epoch0.pt` after the final epoch's `last.pt`; `last.pt` (complete, optimizer state) was stripped with `strip_optimizer` and used. No training effect.

### Brahms 317803 pdf 0 vs Sean's truth (GATHER view = every detector box; `score-truth-brahms.txt` has the ADJUDICATE view too)
| group (truth n) | production R / P | OLD 896 | MATCHED (white-padded) | PACKED 16 |
|---|--:|--:|--:|--:|
| beam (50) | 0.80 / 0.23 | 0.54 / 0.40 | 0.30 / 0.65 | **0.78** / 0.53 |
| ledgerLine (248) | 0.71 / 0.81 | 0.67 / 0.88 | 0.08 / 1.00 | 0.45 / 0.98 |
| tie (79) | 0.57 / 0.25 | 0.51 / 0.59 | 0.37 / 0.74 | 0.52 / 0.51 |
| hollow heads (32) | 1.00 / 0.55 | 0.91 / 0.46 | 0.62 / 0.42 | 0.62 / 0.41 |
| timeSig digits (48) | 0.79 / 0.69 | 0.69 / 0.79 | 0.23 / 0.73 | 0.38 / 0.72 |
| augmentationDot (117) | 0.99 / 0.98 | 0.98 / 0.97 | 1.00 / 0.97 | 1.00 / 0.96 |
| slur (65) / black heads (350) | 0.92 / 1.00 | 0.92 / 1.00 | 0.68 / 0.99 | 0.86 / 0.99 |
(Beam/tie/slur precision is low for every arm incl. production -- the detector emits several boxes per beam/arc where Sean boxed one; read it as a relative column.)

### Litolff 984073 idx 1, Sean's TEST cells (`score-hollow.txt`) and whole-page box counts (`readout`, GATHER+ADJ glyphs)
| | production | OLD | MATCHED | PACKED |
|---|--:|--:|--:|--:|
| hollow recall, 104 cells (59 heads) | 43/59 = 72.9% | 52/59 = 88.1% | 15/59 = 25.4% | 19/59 = 32.2% |
| hollow recall, 95 CLEAN cells (50 heads) | 37/50 = 74.0% | 44/50 = 88.0% | 14/50 = 28.0% | 17/50 = 34.0% |
| hollow precision, 104 / clean | 88.9% / 86.7% | 89.1% / 86.5% | 93.8% / 100% | 100% / 100% |
| Brahms hollow found (of 33) ; extra boxes (on time-sig digits) | 33 ; 26 (15) | 31 ; 35 (22) | 21 ; 32 (25) | 21 ; 32 (25) |
| page boxes: beam / ledgerLine / tie (Litolff) | 63 / 103 / 18 | 10 / 32 / 18 | 8 / 0 / 4 | 46 / 2 / 5 |
| page boxes: beam / ledgerLine / tie (Brahms) | 178 / 231 / 193 | 68 / 202 / 74 | 23 / 23 / 45 | 75 / 120 / 91 |
OLD reproduces the 2.4b damage on Litolff (beam 63 -> 10, ledger 103 -> 32) and its hollow gain (88% vs 73%) -- the control is alive.

## Reading (what the numbers support, and not more)
* Hollow gain: only OLD (shown ~3x larger than inference) has it. Both matched-scale arms LOSE hollow recall (Litolff -38 to -48 points vs production; Brahms 33 -> 21 of 33), mostly "a BLACK head box sits on it" (25 of 33 missed in PACKED): at staff space 16 the 1-epoch fine-tune pushes half/whole heads toward the filled-head class.
* Beams: packed scale keeps them (Brahms recall 0.78 vs 0.80; Litolff 46 vs 63 boxes) where OLD loses ~1/3 to 5/6. That part of the hypothesis holds.
* Ledger lines and ties are NOT kept at matched scale: Litolff ledgers 103 -> 2, ties 18 -> 5; Brahms ledger recall 0.45. Time-sig digits fall too (38%).
* So the single factor "scale" does not explain the deletion: fixing it protects beams, but a different set of classes breaks. The white-padded variant shows how much image statistics alone matter (it is worse than PACKED on every class).

## Caveats
One epoch, one seed, ~10 optimizer steps; PACKED's batch/iteration structure (batch 2, nbs 18, 96 iterations) cannot be made identical to OLD's; the test is 1 Brahms page (truth, 1,566 boxes) + 1 Litolff page (104 cells, 59 heads); 9 of those cells leaked into
all arms and production (reported both ways); v13 not removed from training. Packed canvases mix cells from different scores; tile cuts of wide cells drop partly-visible boxes. `last.pt` is the fine-tune as is
(raw, no graft); 2.4b's raw rows used the same convention. Not tried: more epochs at 16, scale-jitter around 16, 2048 on a cloud GPU, freezing BN.

## Commands
`bash make_old_catalog.sh; python3 survey_train_spaces.py ...; python3 verify_cells.py pick.json out/print/2.110-staff-space-check; python3 build_arms.py; python3 build_packed.py; python3 verify_shown.py;`
`python3 leakage.py; ARM=old|matched|packed ./train_2110.sh; ./run_ab.sh prod=... old=... matched=... packed=...;`
`python3 score_truth.py --records prod=rec-bra-prod.json old=... matched=... packed=...; python3 score_hollow.py prod=rec-lit-prod.json:rec-bra-prod.json ...` (outputs: `score-truth-brahms.{txt,json}`, `score-hollow.{txt,json}`, `verify_shown.json`, `leakage.json`).
