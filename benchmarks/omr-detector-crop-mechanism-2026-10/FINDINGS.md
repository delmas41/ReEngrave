# Detector crop mechanism -- FINDINGS

## 2.171 -- why a wider crop reads better (STAGED GATHER, read-only; no product code, nothing written to a record)

Sean 2026-10-19: *"I would want to know what it is about the wider detector pass that actually is helping it read better - not just know if it works better."*
Probes `probe/2.171/` (`e1` subjects, `e2` the experiment, `e3` control, `e4` tables, `e5` sizes, `e6` rule decomposition, `e7` crops, `e8` stroke thickness, `e9` tables, `e10` lifts; data and per-run tables in `probe/2.171/data/`, the two raw run files are committed gzipped; `gunzip -k` them before re-running e3-e10). Crops: `out/print/2.171/` (6, README there). Records 20261018-night via the 2.167d extracts, same 45 + 45 held bars (44 Brahms had a cell). Weights: the routed production file `deepscoresv2-yolov8l-hollow-graft-shift09-2026-09-04.pt`, never phase-j-mix.

**CONVENTION ASSUMED:** a symbol "reads better" when the detector's best box of the right family over it scores higher. **WHAT WOULD FALSIFY IT:** a condition that raises scores as much on a change that moves nothing real. **NOT CONFIRMED:** the confidence is the detector's own number, ours, not evidence (rule 7). Whether a lifted box is a REAL symbol is only known from 2.167d's own look (Brahms new wide boxes about 0.9 right, Litolff about 0.15); this lane does not re-judge boxes.

### 1. What a bar crop is, as built (read from the code, then reproduced)
STAGED and LEGACY share this feed (`measure_extractor._build_measure_cell` -> `yolo_detector.YoloDetector.detect`):
1. Page crop at 600 dpi: x from barline to barline (nothing added left or right), y from 4 staff spaces above the staff to 4 below (6 where the neighbouring staff is far, `PAD_MAX_STAFF_LINES`).
2. Upscaled so the staff SPAN is 400 px (canonical staff space about 100 px, cubic), unless the width would pass 2048 (then scaled by width, so a wide bar is shown smaller canonically).
3. `imgsz = round32(16 * long_side / canonical_space)` (`imgsz_for_cell`, `TARGET_STAFF_SPACE_PX = 16`): the model is shown a 16 px staff space, whatever the crop. Ultralytics `LetterBox` then resizes the long side to imgsz (bilinear), centres the short side and pads it to a multiple of 32 with grey 114. A typical bar is therefore a 256 x 128 (Litolff) or 192 x 256 (Brahms) network input; a double-width crop is 256 x 256 or 192 x 512.
4. conf floor 0.25 in GATHER (this lane runs at 0.05 so sub-floor boxes can be read), iou 0.7, agnostic NMS off, role-twin collapse, weights routed by input domain (`scanned` for both plates).
Staff space shown, measured on all subject bars: median 16.0 px (Litolff 15.3-16.7, Brahms 15.1-17.0). The 16 comes from one sweep of NOTEHEAD counts on authored engraved fixtures (`benchmarks/omr-detector-scale/RESULTS.md`: plateau 8-22 px, cliff at 26-50); dots, flags, rests and scanned plates were not in it.

**The first thing the code says about the wider pass:** the wide crop is NOT shown larger or smaller. Both crops are resized to the same 16 px staff space, so "same pixel size" is true by design. What changes is context, the input's shape and, as a side effect, the rounding of `imgsz` (item 5).

### 2. Controls (a control must be able to fail)
- My letterbox re-implementation (the only part of the feed I rebuilt, so scale, canvas, fill, interpolation and placement can be set one at a time; the model, weights, conf, iou, NMS are the shipped ones) reproduces the record: subject conf vs record conf matched 61/61 Litolff and 121/121 Brahms, median difference 0.0002, max 0.0005 (MPS float noise). It reproduces 2.167d's base re-run boxes (Litolff 540 of 543, Brahms 1298 of 1321 at 0.10+, the rest are IoU rounding) and 2.167d's wide re-run (952/964 and 2015/2057). `probe/2.171/data/control.txt`.
- It CAN fail: a sub-pixel change of the crop edge (1-6 canonical px = 0.16-1 network px) moves scores by up to 0.4 (item 3), so a wrong letterbox is caught at once.
- **The selection effect, which every table below is read against.** The lost symbols were chosen because they scored under 0.25 in the production crop, the kept ones because they scored over it. Any change that merely re-rolls the number lifts the first group and lowers the second. So every effect is shown beside a NULL: the nine sampling-phase runs (crop left edge moved 1-6 canonical px, top edge 2/4/6; same ink, same size, same canvas), and beside the damage to the kept symbols. A condition that lifts lost symbols no more than the null lifts them is not an explanation. Foreign-ink runs exist for only about half the bars (Litolff 19 of 34, Brahms 21 of 44; 12 and 6 lost symbols), so that row is weak.

### 3. The score of a near-floor symbol is unstable before anything else is changed
Moving the crop's left edge by 1-6 canonical pixels (at most one network pixel; nothing else changes) lifts at least one run to 0.25+ for 8 of 17 lost Litolff and 9 of 17 lost Brahms symbols, and drops 11 of 44 / 17 of 80 kept symbols under 0.25 in at least one run. Per symbol the max-min conf over the 10 phase runs has median 0.14 (lost, Litolff) / 0.19 (Brahms), 0.07 / 0.14 for the kept. A single such run alone changes about 8-10% of all the 0.25+ boxes in the bars (Brahms phx6: 26 new, 36 lost of 337; Litolff phx6: 13 new, 9 lost of 113). **So "new boxes" at 0.25+ from any second pass are largely churn of this kind, and the box count does not grow**: at the same pixel size the wide crop holds 327 Brahms boxes against 337 (18 new, 20 lost) and 118 Litolff against 113 (13 new, 9 lost). 2.167d's "+33 / +25 boxes" counted only the new half. `probe/2.171/data/analysis.txt`.

### 4. One variable at a time (lost = 2.167d A/B/C symbols: means over all 17 Litolff / 20 Brahms, lifted counts over the 17 + 17 with prod < 0.25; kept = record boxes at 0.25+, n = 44 + 80)
Mean change of the best wanted-family conf versus production, how many lost symbols the ONE run lifts to 0.25+, and how many kept symbols it drops under 0.25. Null = mean of the nine phase runs. Intervals: paired bootstrap, 2000 draws, of (condition minus null) per lost symbol (`analysis.txt`). Per-condition numbers for every class are in section 8.

| variable (one run) | Litolff lost: change / lifted / kept dropped | Brahms lost: change / lifted / kept dropped |
|---|---|---|
| NULL: sampling phase (9 runs, mean) | +0.04 / 1-5 of 17 per run / 4-6 of 44 | +0.01 / 3-5 of 17 per run / 6-11 of 80 |
| SCALE x0.5 (8 px staff space) | +0.21 / 8 / 15 of 44 | **+0.30 / 13 / 15 of 80** (excess over null +0.29 [+0.20,+0.38]) |
| SCALE x0.7 (11 px) | +0.11 / 7 / 10 | +0.20 / 10 / 16 |
| SCALE x1.4 (22 px) | +0.13 / 8 / 10 | -0.08 / 3 / 18 |
| SCALE x2 (32 px) | +0.20 / 10 / 18 | -0.10 / 2 / **46 of 80** |
| CONTEXT: wider crop, same pixel size | +0.11 / 6 / 6 (excess +0.07 [+0.003,+0.13]) | +0.07 / 6 / **1** (excess +0.06 [-0.01,+0.13]) |
| CONTEXT: one bar each side / whole staff strip | +0.04, +0.13 / 3, 7 / 4, 7 | +0.15, +0.14 / 7, 9 / 4, 6 (excess +0.13 [+0.08,+0.19], +0.13) |
| CONTEXT: own ink mirrored into the sides | +0.05 / 4 / 7 | +0.07 / 4 / 3 (excess +0.06 [+0.005,+0.11]) |
| CANVAS: bar alone on a wide-crop-shaped WHITE canvas | **+0.11 / 7 / 8** (excess +0.07 [+0.01,+0.14]) | +0.00 / 3 / 6 |
| CANVAS: same, grey 114 letterbox fill | +0.11 / 6 / 6 | -0.00 / 2 / 7 |
| MARGIN: white 64/128/256 px each side | +0.08, +0.08, +0.10 / 6, 6, 6 | -0.03, -0.02, -0.03 / 1, 1, 1 |
| FILL only: stride padding white instead of grey | +0.01 / small | +0.01 / small |
| INTERPOLATION: area (anti-aliased) instead of bilinear | +0.14 / 6 / 8 (excess +0.10 [+0.02,+0.17]) | **+0.15 / 10 / 6** (excess +0.14 [+0.07,+0.20]) |
| wide + area | +0.21 / 7 / 10 | +0.27 / **13 / 7** |
| POSITION: grid phase (+8/+16/+24 px, same content) | spread median 0.04 | spread median 0.06 |
| POSITION: symbol at the left / right edge (the bar clipped) | +0.16, +0.09 / 8, 5 | +0.14, +0.12 / 10, 7 |
| what 2.167d ran: wide, production rule | +0.08 / 4 / 7 | **+0.14 / 11 / 7** (excess +0.13 [+0.04,+0.22]) |

Read-across (every statement below is about the detector's score, not about whether the symbol is real):
- **SCALE is the strongest single lever on both plates**, in both directions, and the kept symbols pay for it: x2 destroys the kept ones (46 of 80 Brahms under 0.25, new boxes 396 on 337), x0.5 drops 15-19%. The direction depends on the symbol: Brahms lost dots, flags, rests (8 + 9 + 3) want SMALLER (flags 0.25 -> 0.66 at x0.5, all 9 over 0.25), Litolff lost black heads want LARGER (0.11 -> 0.35 at x1.4, 0.46 at x2; 8-9 of 9 over 0.25) while Litolff lost rests want smaller (0.03 -> 0.35 at x0.5). One fixed 16 px cannot be right for both.
- **CONTEXT INK helps Brahms and does not help Litolff.** Brahms: the same-size wider crop is +0.06, a bar each side or the whole strip +0.13 with 4-6 of 80 kept dropped; blank canvas, white margins and grey margins do nothing (-0.03..+0.00), so the effect is not "a bigger image". Mirroring the bar's own ink in the sides gives the same +0.06 as true neighbours; foreign ink from other bars is not clean (+0.12 on 6 lost symbols, but -0.31 on the 40 kept ones: a seam of unrelated ink damages the reading). Litolff: the wide crop (+0.11) is no better than the bar alone on a blank white canvas of the same shape (+0.11), and the interval of the wide excess over null barely clears zero ([+0.003,+0.13]; nothing in it separates ink from blank space).
- **Interpolation matters about as much as context.** Re-sampling with `INTER_AREA` instead of the bilinear letterbox resize lifts 10 of 17 Brahms and 6 of 17 Litolff lost symbols, drops 6/80 and 8/44 kept. The network input is a 6x down-sampling of an already cubic-upscaled image by two-tap bilinear, so a 5-8 px dot or a 4 px line is sampled, not averaged.
- **Position is not a stride/tile effect.** Moving the same content by +8/+16/+24 network px inside a white canvas changes conf by a median 0.04-0.06; the edge placements lift because they CLIP the bar (the neighbouring head or stem leaves the picture), not because of a grid.

### 5. The 2.167d "wide pass" is context plus an unintended scale change plus a re-roll
`imgsz_for_cell` is applied to the wide cell on its own and rounds to a multiple of 32, so the wide pass is shown a staff space 0.92-1.08 times the bar pass's (median 1.00; on 17 of 34 Litolff and 24 of 44 Brahms bars it differs by more than 3%). Holding the pixel size equal to the bar's (`wide` above) and then letting the rule choose (`wide_rule`): Brahms lost +0.07 -> +0.14, lifted 6 -> 11 of 17, kept dropped 1 -> 7 of 80; Litolff +0.11 -> +0.08, 6 -> 4, 6 -> 7. For Brahms about half the rule's gain (52%) is NOT the context; on the |rho-1| <= 3% bars it is still +0.10, so it is not the scale alone either but the other thing the re-cut changes, the sampling grid (section 3). `probe/2.171/data/decomp.txt`. (n = 6-8 per bin; read as a direction, not a size.)

### 6. Which variable explains the dot (0.13 -> 0.60) and the 2.167d recoveries
**The dot (Brahms 3/0/3/5, page 3) is on a cliff, not at one variable.** Conf under production 0.13; wide crop at the same pixel size 0.46; the rule's wide crop 0.60; bar and a bar each side 0.49; strip 0.54; own ink mirrored 0.32; blank white canvas 0.08; white margins 0.09; sampling phase 0.14-0.20 (one y-phase 0.36); anti-aliased resize 0.51; scale x0.7 0.65, x0.5 0.44, x1.4 and x2 0.00. So of the +0.47: context ink alone gives +0.33 (70%; blank canvas gives none), the rest is the rule's scale/sampling detail; and smaller scale or anti-aliasing reach the same place with no context at all (crop 1, `out/print/2.171/`).
**The 2.167d recoveries (A/B/C lost, double-width found 16 of 36, any variant 23):**
- Brahms (n = 17 with this lane's matching): the same-size wide crop lifts 6, the rule's 11, a bar each side 7, strip 9, anti-aliased 10, scale x0.5 13, wide + area 13; a random single phase run lifts 4-5. Context ink is real here but is one of three levers of similar size, and scale alone beats it.
- Litolff (n = 17): wide 6, the rule's 4, blank white canvas 7, best of nine phase runs 8, scale x0.5 / x1.4 / x2 8 / 8 / 10. **The Litolff recovery is not distinguishable from a re-roll plus a blank canvas.** (2.167d's own cost figure, about 5 right of 33 new boxes, agrees.)

### 7. Litolff (merging) versus Brahms (shattering)
They are different failures, and the same crop mechanism serves one of them.
- Brahms: small, light, SEPARATE symbols (dot 0.5 x 0.5 staff space = 8 px, flag, quarter/eighth rest) next to a head. They are shown too large, are sampled thinly (bilinear), and gain from real neighbouring ink. Lost B (under the floor) is 14 of the 41 lost Brahms items in 2.167d; the lost Brahms symbols here respond to scale, context and interpolation, each lifting 6-13 of 17.
- Litolff: heads and rests WELDED to staff lines and to each other, blurred to a block (crop 4: a quarter head squared to a block between two lines, `restWhole` 0.35 in the record). The block needs a LARGER view (so the oval is resolvable) or none of the above; context is no better than blank space; the 33 extra boxes the wide pass added were mostly wrong in 2.167d.
- Stroke thickness: a staff line is 4 page px = 0.25 staff space on both plates, so 4.1 px thick at the detector's 16 px staff space (`e8`). Engraved training-style lines are thinner relative to the space (about 0.1-0.13 staff space by general engraving convention, NOT measured here, no training images on this machine), so one possibility for "smaller reads better" is that halving the size also halves the blur (2 px lines). It is a candidate, not a finding: the lane did not vary stroke thickness at constant size.

### 8. Per-plate, per-class tables (best wanted-family conf over the symbol, 0 where none; mean / median / share >= 0.25)
The full set (every condition, groups lost / D gate-dropped / kept / judged) is `probe/2.171/data/analysis.txt`. Subjects: Litolff 63 (lost 17 located of 20, kept 44, D 2), Brahms 124 (lost 20, kept 80, D 21, Sean-judged blackheads 3) -- all in the bars of 2.167d; the Sean-judged tiles with a glyph in these bars are 1 and 4 only (`judged/blackhead`, read correctly, conf 0.82 and nearly flat under every condition). Kept = the record kept the box at 0.25+ and wrote it (heads, rests; dots and flags have no exporter fate, so "kept" = detector box at 0.25+). "Read correctly" there is OUR record, not truth. Sizes: Brahms dot 0.50 x 0.51 staff space (8.0 x 8.1 px shown), flag 1.08 x 3.00, rest 1.18 x 1.97, head 1.38 x 1.20; Litolff dot 0.23 x 0.28 (4 px, 3 samples), flag 1.33 x 3.30, rest 1.32 x 1.97, head 1.46 x 1.33 (`probe/2.171/data/sizes.txt`; Brahms lost items are the same size as the kept ones, Litolff lost heads are flatter, 1.08 vs 1.33 staff spaces tall: size alone does not make a symbol lost).


#### Litolff (Beethoven 5, merging)

**dot, kept at 0.25+ in the record, n=3**

| condition | mean | median | share >= 0.25 |
|---|--:|--:|--:|
| prod (production) | 0.39 | 0.42 | 1.00 |
| phase null (mean of 9) | 0.34 | 0.37 | 0.85 |
| scale x0.5 | 0.00 | 0.00 | 0.00 |
| scale x0.7 | 0.08 | 0.00 | 0.00 |
| scale x1.4 | 0.00 | 0.00 | 0.00 |
| scale x2 | 0.00 | 0.00 | 0.00 |
| wide, same px | 0.11 | 0.00 | 0.33 |
| wide, production rule | 0.11 | 0.00 | 0.33 |
| mirror ink | 0.10 | 0.10 | 0.00 |
| bar on white wide canvas | 0.04 | 0.00 | 0.00 |
| area interp | 0.21 | 0.25 | 0.33 |

**flag, kept at 0.25+ in the record, n=4**

| condition | mean | median | share >= 0.25 |
|---|--:|--:|--:|
| prod (production) | 0.60 | 0.63 | 1.00 |
| phase null (mean of 9) | 0.59 | 0.61 | 0.94 |
| scale x0.5 | 0.62 | 0.71 | 1.00 |
| scale x0.7 | 0.73 | 0.73 | 1.00 |
| scale x1.4 | 0.42 | 0.48 | 0.75 |
| scale x2 | 0.02 | 0.00 | 0.00 |
| wide, same px | 0.66 | 0.65 | 1.00 |
| wide, production rule | 0.64 | 0.66 | 1.00 |
| mirror ink | 0.61 | 0.63 | 1.00 |
| bar on white wide canvas | 0.55 | 0.57 | 1.00 |
| area interp | 0.64 | 0.66 | 1.00 |

**rest, lost (A/B/C), n=7**

| condition | mean | median | share >= 0.25 |
|---|--:|--:|--:|
| prod (production) | 0.03 | 0.00 | 0.00 |
| phase null (mean of 9) | 0.08 | 0.00 | 0.16 |
| scale x0.5 | 0.35 | 0.42 | 0.71 |
| scale x0.7 | 0.23 | 0.10 | 0.43 |
| scale x1.4 | 0.06 | 0.00 | 0.00 |
| scale x2 | 0.09 | 0.00 | 0.14 |
| wide, same px | 0.14 | 0.00 | 0.29 |
| wide, production rule | 0.14 | 0.06 | 0.29 |
| mirror ink | 0.07 | 0.00 | 0.14 |
| bar on white wide canvas | 0.21 | 0.24 | 0.43 |
| area interp | 0.16 | 0.10 | 0.29 |

**rest, kept at 0.25+ in the record, n=11**

| condition | mean | median | share >= 0.25 |
|---|--:|--:|--:|
| prod (production) | 0.66 | 0.72 | 1.00 |
| phase null (mean of 9) | 0.62 | 0.72 | 0.86 |
| scale x0.5 | 0.51 | 0.64 | 0.73 |
| scale x0.7 | 0.53 | 0.55 | 0.91 |
| scale x1.4 | 0.43 | 0.55 | 0.64 |
| scale x2 | 0.12 | 0.00 | 0.18 |
| wide, same px | 0.66 | 0.75 | 0.82 |
| wide, production rule | 0.63 | 0.73 | 0.82 |
| mirror ink | 0.65 | 0.77 | 0.82 |
| bar on white wide canvas | 0.60 | 0.69 | 0.82 |
| area interp | 0.60 | 0.76 | 0.82 |

**blackhead, lost (A/B/C), n=9**

| condition | mean | median | share >= 0.25 |
|---|--:|--:|--:|
| prod (production) | 0.11 | 0.13 | 0.00 |
| phase null (mean of 9) | 0.14 | 0.15 | 0.11 |
| scale x0.5 | 0.26 | 0.00 | 0.33 |
| scale x0.7 | 0.11 | 0.00 | 0.33 |
| scale x1.4 | 0.35 | 0.33 | 0.89 |
| scale x2 | 0.46 | 0.42 | 1.00 |
| wide, same px | 0.22 | 0.24 | 0.44 |
| wide, production rule | 0.17 | 0.17 | 0.22 |
| mirror ink | 0.18 | 0.22 | 0.33 |
| bar on white wide canvas | 0.18 | 0.16 | 0.44 |
| area interp | 0.26 | 0.16 | 0.44 |

**blackhead, kept at 0.25+ in the record, n=26**

| condition | mean | median | share >= 0.25 |
|---|--:|--:|--:|
| prod (production) | 0.67 | 0.74 | 1.00 |
| phase null (mean of 9) | 0.65 | 0.74 | 0.92 |
| scale x0.5 | 0.49 | 0.71 | 0.65 |
| scale x0.7 | 0.55 | 0.68 | 0.77 |
| scale x1.4 | 0.63 | 0.71 | 0.92 |
| scale x2 | 0.59 | 0.63 | 0.92 |
| wide, same px | 0.67 | 0.73 | 0.92 |
| wide, production rule | 0.66 | 0.73 | 0.89 |
| mirror ink | 0.64 | 0.75 | 0.92 |
| bar on white wide canvas | 0.65 | 0.75 | 0.89 |
| area interp | 0.65 | 0.80 | 0.85 |


#### Brahms (Brahms 1, shattering)

**dot, lost (A/B/C), n=8**

| condition | mean | median | share >= 0.25 |
|---|--:|--:|--:|
| prod (production) | 0.10 | 0.09 | 0.00 |
| phase null (mean of 9) | 0.10 | 0.06 | 0.14 |
| scale x0.5 | 0.27 | 0.39 | 0.62 |
| scale x0.7 | 0.31 | 0.32 | 0.50 |
| scale x1.4 | 0.07 | 0.00 | 0.25 |
| scale x2 | 0.08 | 0.00 | 0.25 |
| wide, same px | 0.22 | 0.20 | 0.50 |
| wide, production rule | 0.38 | 0.41 | 0.75 |
| mirror ink | 0.17 | 0.18 | 0.25 |
| bar on white wide canvas | 0.10 | 0.07 | 0.12 |
| area interp | 0.29 | 0.29 | 0.62 |

**dot, kept at 0.25+ in the record, n=20**

| condition | mean | median | share >= 0.25 |
|---|--:|--:|--:|
| prod (production) | 0.59 | 0.62 | 1.00 |
| phase null (mean of 9) | 0.53 | 0.61 | 0.87 |
| scale x0.5 | 0.39 | 0.52 | 0.75 |
| scale x0.7 | 0.41 | 0.51 | 0.70 |
| scale x1.4 | 0.36 | 0.41 | 0.60 |
| scale x2 | 0.14 | 0.00 | 0.25 |
| wide, same px | 0.61 | 0.65 | 0.95 |
| wide, production rule | 0.59 | 0.72 | 0.85 |
| mirror ink | 0.60 | 0.64 | 0.95 |
| bar on white wide canvas | 0.56 | 0.58 | 0.95 |
| area interp | 0.59 | 0.65 | 0.90 |

**flag, lost (A/B/C), n=9**

| condition | mean | median | share >= 0.25 |
|---|--:|--:|--:|
| prod (production) | 0.25 | 0.22 | 0.33 |
| phase null (mean of 9) | 0.25 | 0.24 | 0.49 |
| scale x0.5 | 0.66 | 0.70 | 1.00 |
| scale x0.7 | 0.51 | 0.53 | 1.00 |
| scale x1.4 | 0.12 | 0.07 | 0.22 |
| scale x2 | 0.05 | 0.00 | 0.00 |
| wide, same px | 0.31 | 0.26 | 0.56 |
| wide, production rule | 0.31 | 0.29 | 0.67 |
| mirror ink | 0.32 | 0.26 | 0.56 |
| bar on white wide canvas | 0.25 | 0.20 | 0.44 |
| area interp | 0.37 | 0.33 | 0.67 |

**flag, kept at 0.25+ in the record, n=20**

| condition | mean | median | share >= 0.25 |
|---|--:|--:|--:|
| prod (production) | 0.59 | 0.63 | 1.00 |
| phase null (mean of 9) | 0.57 | 0.63 | 0.94 |
| scale x0.5 | 0.46 | 0.49 | 0.70 |
| scale x0.7 | 0.54 | 0.68 | 0.80 |
| scale x1.4 | 0.32 | 0.32 | 0.60 |
| scale x2 | 0.07 | 0.00 | 0.10 |
| wide, same px | 0.62 | 0.66 | 1.00 |
| wide, production rule | 0.55 | 0.65 | 0.85 |
| mirror ink | 0.62 | 0.65 | 0.95 |
| bar on white wide canvas | 0.56 | 0.64 | 0.85 |
| area interp | 0.63 | 0.68 | 0.95 |

**rest, lost (A/B/C), n=3**

| condition | mean | median | share >= 0.25 |
|---|--:|--:|--:|
| prod (production) | 0.06 | 0.00 | 0.00 |
| phase null (mean of 9) | 0.13 | 0.06 | 0.18 |
| scale x0.5 | 0.38 | 0.48 | 0.67 |
| scale x0.7 | 0.07 | 0.00 | 0.00 |
| scale x1.4 | 0.00 | 0.00 | 0.00 |
| scale x2 | 0.06 | 0.00 | 0.00 |
| wide, same px | 0.02 | 0.00 | 0.00 |
| wide, production rule | 0.08 | 0.07 | 0.00 |
| mirror ink | 0.10 | 0.08 | 0.00 |
| bar on white wide canvas | 0.05 | 0.00 | 0.00 |
| area interp | 0.19 | 0.00 | 0.33 |

**rest, kept at 0.25+ in the record, n=20**

| condition | mean | median | share >= 0.25 |
|---|--:|--:|--:|
| prod (production) | 0.65 | 0.70 | 1.00 |
| phase null (mean of 9) | 0.62 | 0.70 | 0.89 |
| scale x0.5 | 0.60 | 0.66 | 0.90 |
| scale x0.7 | 0.58 | 0.70 | 0.80 |
| scale x1.4 | 0.62 | 0.68 | 0.90 |
| scale x2 | 0.21 | 0.20 | 0.35 |
| wide, same px | 0.68 | 0.71 | 1.00 |
| wide, production rule | 0.63 | 0.70 | 1.00 |
| mirror ink | 0.67 | 0.71 | 0.95 |
| bar on white wide canvas | 0.62 | 0.67 | 0.95 |
| area interp | 0.73 | 0.81 | 0.95 |

**blackhead, kept at 0.25+ in the record, n=20**

| condition | mean | median | share >= 0.25 |
|---|--:|--:|--:|
| prod (production) | 0.72 | 0.77 | 1.00 |
| phase null (mean of 9) | 0.71 | 0.78 | 0.96 |
| scale x0.5 | 0.67 | 0.76 | 0.90 |
| scale x0.7 | 0.65 | 0.77 | 0.90 |
| scale x1.4 | 0.72 | 0.79 | 1.00 |
| scale x2 | 0.77 | 0.80 | 1.00 |
| wide, same px | 0.72 | 0.78 | 1.00 |
| wide, production rule | 0.71 | 0.76 | 0.95 |
| mirror ink | 0.73 | 0.78 | 1.00 |
| bar on white wide canvas | 0.70 | 0.75 | 0.95 |
| area interp | 0.73 | 0.83 | 0.90 |


### 9. The mechanism, in plain words
There is no single "wider crop" effect; the same pass bundles four different things, and which one matters depends on the plate.
1. **The detector is very sensitive to how big the symbol is in its input pixels, and 16 px is one number for all symbols.** A dot is 8 px, a flag 17 x 47 px, a Litolff welded head 23 x 21 px. Halving the view (staff space 8 px) turns 13 of 17 lost Brahms dots/flags/rests into 0.25+ boxes; enlarging it by 1.4 turns 8 of 9 lost Litolff heads into boxes; doubling it makes 46 of 80 good Brahms boxes vanish and creates about as many new ones as the old ones. The 16 was fitted on engraved NOTEHEADS. The wide crop does not change this scale on purpose; it changes it by accident (section 5).
2. **A symbol near the floor is on a steep part of an unstable curve.** A shift of the crop by less than one network pixel moves a symbol's confidence by a median 0.14-0.19; any re-cut, wide or not, re-rolls it. That alone lifts 1-5 of 17 lost symbols per run, and a second pass whose result is "any box at 0.25+" will always find some.
3. **Real neighbouring ink helps small, separate symbols (Brahms) and is no better than blank space for welded ones (Litolff).** Blank canvas, margins and fill do nothing for Brahms; the true neighbours (or the bar's own ink mirrored) give +0.06, a bar of context each side +0.13, and cost one kept box in 80 at the same pixel size. For Litolff the benefit of the wide crop is reproduced by blank space, within the re-roll noise.
4. **Down-sampling by two-tap bilinear from a 6x cubic upscale loses small things at random; averaging (`INTER_AREA`) recovers 10 of 17 Brahms lost symbols, 6 of 17 Litolff.**
For the dot of 2.167d: 0.13 -> 0.60 is context (+0.33) plus resampling/scale detail (+0.14), and the same box is reachable by smaller scale (0.65) or anti-aliasing (0.51) without any context.

### 10. A principled fix (none built)
Each item is a GATHER change that adds a candidate or makes a read deterministic, never a guess (rules 6, 8); each must be proven on Sean's blind tiles per plate, because correctness of the lifted boxes was not judged here.
1. **Key the resize to the staff space exactly and per symbol family, not to the crop width.** Feed the detector a pre-resized array at a chosen staff space (no `round32` on a per-crop `imgsz`), so a bar crop and a wider crop show the identical pixel size. That removes the accidental 0.92-1.08 scale of the second pass and makes any result independent of how wide the crop happened to be.
2. **Read dots, flags and rests at a smaller staff space (the lane's evidence: about 8-11 px for Brahms) and heads at 16-22 (Litolff welded heads), as separate passes whose boxes join the record with their own scale in the reason**, instead of one 16 px pass plus a floor. The 0.25 floor ruling stays: second-scale boxes enter as candidates with conf and scale, and only DECIDED rules choose.
3. **Anti-alias the final resize** (area / a pre-blur at the 6x down-sample) wherever the resize is large; it costs 6-8 kept boxes in 80 and lifts the most per box lost.
4. **Make a near-floor score a distribution, not a draw:** re-read at 3-5 sub-pixel phases and take the median, or keep a box seen in most of them; the lane's null shows a single run flips 8-10% of the 0.25+ boxes.
5. **If context is wanted, give real neighbouring ink at the same pixel size (half a bar to a bar each side)**, for Brahms-style plates; for Litolff it buys nothing the blank canvas does not. Do not feed unrelated ink (foreign filler cost 0.31 on kept symbols).
The tests to ask for first: Sean's blind tiles on (a) a second scale for dot/flag/rest on Brahms, (b) a 1.4x head pass on Litolff welded heads, each with the kept-symbol damage counted beside the lifted boxes.

### 11. Not done / caveats
- Whether a lifted box is a real symbol: not judged (only 2.167d's own look). Confidence is the detector's number.
- n is small for the lost set (17 + 17 with prod < 0.25; 17 and 20 means; dots 8, flags 9, rests 3 + 7, heads 9): intervals are per variable, the per-class tables are directions. Sean's judged tiles reach only 1 + 4 of these symbols (all read correctly, conf flat across conditions).
- "Kept" is selected on production conf, so every condition lowers it a little; it is a damage count, not a baseline. Foreign ink covers about half the bars.
- Training scale: no training images on this machine (`data/deepscoresv2*`, `cat-d25` absent). What is in the repo: the base is DeepScoresV2 pages at imgsz 2048; the hollow fine-tune ran at 896 on catalog cells (`train_args` of the checkpoint, `probe/2.171/e0_ckpt.py`); the 16 px figure is from authored noteheads. The response curve above is the measured stand-in, not a comparison with training sizes.
- Stroke thickness as the reason smaller reads better: a candidate, untested (needs a constant-size thinning run).
- Frames in `out/print/2.171/` are chosen by rule from the run (`e7_crops.py`), not blind.
