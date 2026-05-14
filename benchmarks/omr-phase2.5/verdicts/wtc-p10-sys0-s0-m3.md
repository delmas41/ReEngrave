# Cell wtc-p10-sys0-s0-m3 — verdicts

**Image:** ![overlay](../overlays/wtc-p10-sys0-s0-m3.png)

**Clef assumed:** treble

**Staff lines (canonical y):** 400, 497, 597, 697, 800

**Source:** wtc-p10  ·  page 10  ·  sys 0  staff 0  measure 3


## Detections

For each detection below, replace `verdict: __` with one of:
- `TP` — true positive (right symbol, right location)
- `FP` — false positive (wrong symbol or hallucinated)
- `WRONG_PITCH` — notehead at the right location but the pitch field is wrong
- `unsure` — leave for human review

Add an optional 1-word reason after the verdict, e.g. `TP` or `FP barline-mistake`.

- [ ] D0  noteheadBlack (notehead) at (x=192, y=299) → A5  conf=0.85
       verdict: __________
- [ ] D1  barlineHeavy (barline) at (x=229, y=1095)  conf=1.00
       verdict: __________
- [ ] D2  noteheadBlack (notehead) at (x=432, y=549) → C5  conf=0.77
       verdict: __________
- [ ] D3  noteheadBlack (notehead) at (x=718, y=298) → A5  conf=0.86
       verdict: __________
- [ ] D4  noteheadBlack (notehead) at (x=956, y=549) → C5  conf=0.76
       verdict: __________
- [ ] D5  flag16thDown (flag) at (x=1162, y=1087)  conf=0.62
       verdict: __________
- [ ] D6  noteheadBlack (notehead) at (x=1242, y=298) → A5  conf=0.85
       verdict: __________
- [ ] D7  restHalf (rest) at (x=1432, y=1119)  conf=0.96
       verdict: __________
- [ ] D8  noteheadBlack (notehead) at (x=1478, y=549) → C5  conf=0.76
       verdict: __________

## Missed noteheads (FN)

For each notehead in the cell image that the matcher did NOT find, add a row:

```
FN1 at (x=___, y=___) → pitch=___
FN2 at (x=___, y=___) → pitch=___
```

## Wrong-pitch corrections

Only fill in for detections marked `WRONG_PITCH` above. Format:

```
D0 → correct pitch is C4
```
