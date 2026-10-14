# ROADMAP 2.112 -- test-set leakage audit (TEST cells inside training versions)

Branch `lane-2.112-leakage-audit`, not merged. Light lane: files and image hashes only (no detector, gather, training, full pytest).
Everything here regenerates with `nice -n 15 python3 benchmarks/omr-test-leakage-2026-10/audit.py` (-> `leakage_audit.json`, `audit_output.txt`),
`controls.py` (-> `controls.json`), `python3 -m pytest benchmarks/omr-test-leakage-2026-10/test_guard.py -q`.

## CONVENTION ASSUMED / WHAT WOULD FALSIFY IT / NOT CONFIRMED
* **ASSUMED:** a cell is "the same cell" when its SOURCE key matches: (edition by PDF content, pdf page index 0-based, system, staff, measure), read from
  `benchmarks/**/*cells*.json` (names are 1-based, manifests 0-based: `beet5-p2` = Litolff 984073 idx 1). **Falsified if** an old cutter numbered
  systems/staves/measures differently from the product cutter on some page. **Checked only on 984073 idx 1** (9 of 9 key pairs are the same pixels
  re-cut: near score 0.92-1.0, one SHA-identical; `controls.json`). On every other page the key match is an assumption; the page-level counts do not depend on it.
* **ASSUMED:** the first number of a judged-tile subject (`glyph/<p>/<sys>/<staff>/<meas>/..`) is the pdf page index.
* **NOT CONFIRMED:** DeepScoresV2 (base pretraining, not in the tree) vs the WTC plates / Verovio render; whether `v23` or `v5/v6` fed any *tested*
  weights (not in `weights-lineage.json`); which thresholds were tuned on which page (only `2.101` is cited); the SHIP "Mahler p.173" file identity;
  per-head hits of the 2.4b arms (`ab/score.json` stores counts, not which heads), so no re-score without the 9 cells was possible.
* Edition identity is by PDF SHA-1 (`pdf_sha1.json`): `Mahler_5_.pdf` (Gradus-Assets, cells of v1/v3/v5) **is** the library's `...unidentified-scan-2016--local.pdf`
  (same 21,131,629 bytes), so v3/v5 cells share pages with the Mahler gate rows; the two Gradus/library Beethoven and La Mer paths are also one file each.

## Scope: 9 test sets x 38 training version dirs (23 versions x 2 roots + `user-labeled-clef-fix`, 130 imgs, checked separately)
Training versions: `data/user-labeled` v1-v24 (24 dirs) and `data/user-labeled-distill25` (14 dirs, same cell keys as their `user-labeled` twins). Roles from
`catalog-versions.txt`, `weights-lineage.json`, `SHIP_RESULTS.md`: PRODUCTION scan graft features = distill25 mix (v1-v4, v13-v22); hollow-ft teacher = v1-v4, v7, v8;
2.4b/2.110 arms add v24; v23 arcs experiment (never admitted); v5/v6 clef fine-tune (rejected, never deployed); v9-v12 ablations. Control that the key matcher is right:
it reproduces `INVENTORY.json held_out_cells_trained_by_production` (Brahms idx1: 19, Litolff idx3: 7) exactly.

## Table: test set x training version (cell-key hits / training cells on the same pages)
| test set (what, where used) | size | version | same cell | train cells on same pages |
|---|--:|---|--:|--:|
| **TS1** Litolff 984073 idx1 hollow4 TEST (Sean, 2026-10-13; 2.4b A/B, 2.110) | 104 cells, 59 hand heads | v13 (both roots) | **9** | 9 |
| | | v7-hollow (hollow-ft lineage) | **9** | 9 |
| **TS3** Litolff idx1 whole page = `beet5-p1`, 12 staves (GATE_RESULTS 4b, SHIP_RESULTS 4b, every later hollow-payoff re-gate) | 1 page | v13, v7 | n/a (page) | 9 each |
| **TS4** held-out.json (Sean 2026-10-08): Brahms idx1 | 1 page | v18 / v23 / v8 | n/a | 19 / 16 / 4 |
| ... Litolff idx3 (count page) | 1 page | v13 / v7 | n/a | 7 / 7 |
| ... Brahms idx0, Litolff idx2, Simrock 405834 idx4 | 3 pages | none | - | **0** |
| **TS5** 20-row scan gate pages (19 distinct rows' pages) | 20 pages | v18 (Brahms idx1-3) / v23 | n/a | 56 / 38 |
| | | v13 (984073 idx1: 9, idx3: 7) / v7 | n/a | 16 / 16 |
| | | v1 (984073 idx4) | n/a | 9 |
| | | v3 (Mahler local idx3) / v5 (idx1, clef, rejected) | n/a | 4 / 11 |
| | | v17 / v8 (Dvorak 405834 idx6) | n/a | 2 / 2 |
| **TS7** `held_out_rests` (35 cells held out of the rest-specialist corpus only; round 6, WITHDRAWN) | 35 cells | v14 6, v15 3, v16 5, v18 7, v20 1, v22 13 (= all 35, production lineage) | **35** | |
| **TS8** Sean's blind tiles, Litolff (168 tiles, 138 cells) | | v13/v7/v1/v24 | **0** | 16/16/19/10 |
| **TS9** Sean's blind tiles, Brahms (171 tiles, 136 cells) | | v18 (and v23) / v8 | **7** (13 tiles) / 1 | 56 |
| **TS2** Brahms 317803 idx0 hand truth (112 product cells; 1,352 boxes) | | all 38 | **0** | 0 |
| **TS6** omr-phase2.5 "30 held-out dense cells" (WTC 932182 idx5,10 + Litolff idx10; forgetting axis, class-inventory screen) | 30 cells | all 38 | **0** | 0 |
| `2.101` held-out Dvorak 8 (405841), Schumann 2, Tchaikovsky 4 | 12 pages | no training version is any of these works | **0** | 0 |
| `user-labeled-clef-fix` (130 imgs) vs TS1-TS9 | | | **0** | 19 on TS5 pages (Mahler idx1,3; 984073 idx4), 10 on TS8 pages |
| Same-plate other scan ("twin": Litolff 984073 vs 575951; idx p <-> p-1 per `structure_truth`) | | v13 (984073:1,3), v1 (984073:4) vs gate rows 575951:0,2,3 | not a key match | 16, 9 |
Also: `v6` 47 cells have no page in any manifest; checked by image against all 104 TS1 cells: 0 exact, max near 0.816 (< 0.9).

## What the checks are, and their controls (`controls.json`)
EXACT = SHA-256 of decoded pixels (TS1: 1 pair: `beet5-p2-sys0-s2-m3`). KEY = above. NEAR = both cells scaled to staff space 6 px, smaller template-matched
inside the larger (TM_CCOEFF_NORMED), **only on same-page candidate pairs**. Positive control (the 9 key pairs): min 0.920, median 1.0. Negative, same page other cell
(2,591 pairs): median 0.484, p99 0.734, **max 0.857** (the neighbouring measure). So the threshold is 0.90 on same-page pairs. Negative, other page/edition (1,702 pairs):
max **0.941** (blank-ish staff cells match each other), so a near score is **not usable across pages** (same lesson as 2.110's whole-page matching); that is why NEAR is gated on KEY/page.
Guard: `leakage_guard.py` (`check_leak`, `refuse_if_leaked`, `load_mix`). `test_guard.py`: the known 9 -> 9 key + 9 near + 1 exact, `refuse_if_leaked` raises;
9 neighbouring clean TEST cells -> 0/0/0; Brahms p0 hand truth vs the production mix -> 0; and with the near threshold at 0.0 the clean pair IS flagged (the check can fail). 5 passed.

## Verdicts at risk (ranked by how much they could change)
Direction rule: training on the test inflates the arm that saw it. A *gain* claim is at risk; a *no gain / KILL* is conservative unless the arms had unequal exposure.
A pure geometry/reader rule never trained on anything is **not** contaminated by training overlap; it only receives detector boxes that are cleaner on cells the detector trained on.

1. **GATE/SHIP "hollow payoff" on `beet5-p1` (TS3), the evidence behind shipping hollow-ft and the distill25 line.** GATE_RESULTS 4b calls the page "a HELD-OUT page ... different
   from any training cell"; it is Litolff 984073 idx 1 and **v7 (in treatment@12 and the shipped hollow-ft corpus) holds 9 hand-labeled hollow cells of it**; v13 (distill25) the same 9.
   Page prints 68 halves (DURATIONS.md); 9 = 13% of them. Could flip: treatment-vs-control "what the hollow cells buy" (half notes 21 -> 25, `with_duration` 0.395 -> 0.456, +0.061):
   the half-note increment is 4 and the leak is up to 9. Does not flip in sign: production 8 -> 21 by the clean control (v1-v4 only), and the independent Mahler p.173 page
   (9 -> 23; training pages of that scan are 3,6,9,24,...,174-177, not 172/173, file identity not confirmed). Every later hollow-payoff re-gate on this page (epoch0 27, rounds 4-5, shift09) carries the same 9.
2. **2.4b / 2.110 absolute hollow recall on TS1.** 9 of 59 truth heads (15.3%, one head per leaked cell) were hand-labeled in v13/v7, so production (via distill25 + hollow-ft), the
   control arm and the v24 arm all saw them; relative comparisons of arms are fair, absolute numbers are not. Bound (production 43/59, raw fine-tune 54/59): clean-50 recall lies in
   [68%, 86%] for production and [90%, 100%] for the raw fine-tune; the +18.6-point gap Sean's "REVISIT 2.4b" rests on becomes anywhere from +4 to +32 points: **sign cannot flip, size is unknown.**
   The grafts' exact zero gain and the class-deletion KILL are unaffected. Re-score without the 9 keys needs per-head records (not committed; follow-up).
3. **20-row scan gate / acceptance pages (TS5): every weights decision judged on pooled OMR-NED** (rounds 3-5 gate, routing, shift09). Trained cells sit on Litolff idx1/3/4 (25), Brahms idx1-3
   (56 production), Dvorak idx6 (2), Mahler idx3 (4), and the twin-scan rows 575951 idx0,2,3 are the same plates (25). Fractions of each page are not computed (cell totals per page not collected).
   The round-3 failure (Dvorak +0.155) has only 2 trained cells on its page, so it stands.
4. **Sean's held-out ruling pages (TS4):** the 19 + 7 production cells are already disclosed in INVENTORY; **not disclosed:** v23 trained 16 cells of Brahms idx1 and v8 4. Any slur/arc verdict
   on Brahms idx1 by weights that saw v23 is contaminated (which weights saw v23: NOT CONFIRMED).
5. **Rest specialist round 6 (TS7), already WITHDRAWN:** the "held-out" 35 cells are in the production versions by construction (held out of the specialist corpus only), so base and arms both saw them.
6. **Sean's blind tiles (TS9):** 13 tiles lie on 7 cells that are v18 training cells; reader rules, not weights: the cells' boxes are only likelier to be clean. TS8: none. Tuned thresholds: the
   2.80-2.108 rules were cut on Litolff idx3 / Brahms idx1 and judged by tiles of the same pages; `2.101` is the one existing check on other scores (it flags the 2.99 45% stroke cut as sitting near real rests on a thin plate). Not inventoried further.
Clean: TS2 (Brahms idx0 hand truth, 2.87 stem finder, 1.7 scorer, 2.4b Brahms side), TS6, 2.101 held-out set, TS1 against v1-v6, v8-v12, v14-v22, v24; the Verovio-rendered Beethoven (no manifest cell).

## Follow-ups (need records or a detector; not done here)
(a) Re-score 2.4b/2.110 and the GATE hollow table without the 9 keys (per-head matches; `litolffp1-p2-sys0-{s2-m3,s3-m6,s3-m7,s3-m8,s3-m11,s3-m14,s7-m1,s8-m8,s9-m15}`). (b) Wire `refuse_if_leaked` into the next A/B harness. (c) Collect page cell totals to give the TS5 fractions.
(d) Confirm the cutter-index assumption on a second page (render + cut). (e) Add the 9 keys to `held-out.json` thinking: Litolff idx1 is not a held-out page.
