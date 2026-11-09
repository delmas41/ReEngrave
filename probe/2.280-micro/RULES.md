# 2.280 micro test -- pre-registered bars (copied verbatim from benchmarks/omr-unwritten-notes-2026-10/FINDINGS.md, "Micro test (pre-registered here, before any code ...)")

Population: the 83 narrowed no-stem heads, the 299 decided no-stem heads (193 + 106), and 200 seeded heads that already have a shipped stem row (100 a plate, same 17 pages). Arms: (A) the shipped ruler as it stands (the numbers above: reach 29 of 51, false 8 of 14 accidentals); (B) the ruler on unclaimed ink with the chord-through rule.
1. **Reach (must pass):** arm B files a stem for at least 85% of the 51 real heads (arm A: 57%); baseline 0 by construction. Sean's tiles confirm the sample.
2. **False stems (must pass):** at most 1 of the 30 not-a-note heads (arm A: 8 of 30; the control can fail, and it does).
3. **Agreement (must pass):** on the 200 heads that already have a stem, the same stem (box IoU >= 0.5) and the same direction in at least 98%; every disagreement is looked at on a crop, never settled by our own reading.
4. **Side control (must fail when broken):** arm B with the engraving side flipped (up -> left): reach must drop by at least 30 points, or the convention is not doing the work.
5. **Sean's tiles** (the 12 in `out/print/2.280/`: "Does the boxed note have a stem, and which way does it go?"): arm B's answer matches his on at least 9 of the 10 test tiles and 2 of 2 controls.
6. **Judged:** Sean's judged answers right -> wrong = 0 (`python3 -m tools.omr.staged.judged score`).
**Kill:** 2, 3 or 6 fails, or reach under 60%. The whole movement is the overnight's job; this measures 17 frozen pages.

Prototype (from "The one change at the source"): ruler (`gather.measure_head_stem`) for every kept head with no stem row, on UNCLAIMED ink; `both` is a chord stem when the run ends in another kept head's box, a barline when it ends in none; abstain on `none`, on `both` with no head at an end, or on disagreeing sides.

Sean's 2.280 tiles: not answered yet -> bar 5 reported PENDING.
