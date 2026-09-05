# Grace-notehead batch 2 — eye-verified cells (2026-09-03)

Sitting 1 (`../omr-labeling-grace1-2026-09`) swept 104 blind-sampled cells
and found **zero graces** — sampling 8 cells of a ~150-cell page against
ornaments concentrated in a few staves of a few measures. This batch fixes
that the honest way: **every served cell comes from a page region where
grace figures were SEEN before serving.**

Two arithmetic shortcuts failed first, and both are worth recording:

1. **Reference-measure targeting drifted.** The Gradus reference numbers
   measures **from 0**, and the phase-1 cumulative measure count
   undercounted by ~5 by page idx 5 (the print's own rehearsal numbers say
   m32 where the cumsum said m27). Two independent off-by-N sources — either
   alone breaks cell-level addressing.
2. So the method became: render each cut page, READ it (the Peters print
   marks every grace run with a ★ and a footnote — *"Vorschläge so schnell
   als möglich"*), and select cells by what is visibly there. Verified
   directly on a crop before serving (`mahler5-p6-sys0-s0-m7` shows the
   ★ + small triple-beamed grace cluster beside full-size heads).

**The served 153 cells** (`cells.json`; the full 2,327-cell dense cut is
`cells-all.json`):

| page (pdf idx / printed) | where | why |
|---|---|---|
| idx 5 / p.7, mm.32–50 | sys0 A-Klar+Fag+low strings, ords 5–8; sys1 all staves, ords 0–4 | **eye-verified ★ Vorschläge** (printed mm.38–44) |
| idx 4 / p.6, mm.24–30 | top 3 staves ords 3–6; bottom 6 staves ords 0–6 | visible small-note runs in Fag./Contraf. + divisi celli/basses; the reference's mm.28–30 run |
| idx 3 / p.5, mm.17–23 | all staves, ords 0–1 | visible clusters in Hoboen/A-Klar at mm.17–18 |

Mozart 40 was cut (pages idx 8–12, in `cells-all.json`) but is **not
served**: its absolute measure anchor is unresolved (the cut window doesn't
reach measure 1) — a follow-up if Mahler alone under-delivers.

Same single-symbol pass as batch 1 (`batch_config.json`): click the small
grace HEADS only (0.62-space box), never the slash/stem/flag; Esc steps
out; Tab records an inspected-empty cell. These verdicts are the first
grace ground truth in the project — they calibrate `grace_score.py`'s
provisional bands and the pre-fill's grace-size veto.

## RESULT (2026-09-03): 30 grace boxes in 15 cells — targeting verified, bands calibrated

Sean swept 152/153 cells: **30 grace heads labeled across 15 cells**, all in
the regions the eyes + reference predicted (p6 sys0 s0/s1/s9/s11/s12 ords
7–8; p5 sys0 s1/s2/s17/s19 ord 5). All boxes click-placed (no manual
drags); snap variants 15 on-line / 15 in-space. The labels recalibrated
`grace_score.py` — selector recall on these cells went 0.53 → **1.00**
(details in `../omr-labeling-survey-2026-09/GRACE_SELECTOR_2026-09-03.md`).
⚠️ Conversion to YOLO labels WAITS for the campaign rule: these cells have
had one pass; everything unboxed would train as background. A completion
pass (the pre-fill tooling) comes first.
