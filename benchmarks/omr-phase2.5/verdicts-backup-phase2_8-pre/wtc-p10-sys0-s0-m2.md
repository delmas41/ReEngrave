# Cell wtc-p10-sys0-s0-m2 — verdicts

**Image:** ![overlay](../overlays/wtc-p10-sys0-s0-m2.png)

**Clef assumed:** treble

**Staff lines (canonical y):** 400, 497, 597, 697, 800

**Source:** wtc-p10  ·  page 10  ·  sys 0  staff 0  measure 2


## Detections

For each detection below, replace `verdict: __` with one of:
- `TP` — true positive (right symbol, right location)
- `FP` — false positive (wrong symbol or hallucinated)
- `WRONG_PITCH` — notehead at the right location but the pitch field is wrong
- `unsure` — leave for human review

Add an optional 1-word reason after the verdict, e.g. `TP` or `FP barline-mistake`.

- [ ] D0  noteheadBlack (notehead) at (x=194, y=350) → G5  conf=0.84
       verdict: __________
- [ ] D1  noteheadBlack (notehead) at (x=432, y=549) → C5  conf=0.77
       verdict: __________
- [ ] D2  noteheadBlack (notehead) at (x=718, y=350) → G5  conf=0.84
       verdict: __________
- [ ] D3  noteheadBlack (notehead) at (x=953, y=549) → C5  conf=0.77
       verdict: __________
- [ ] D4  noteheadBlack (notehead) at (x=1240, y=350) → G5  conf=0.84
       verdict: __________
- [ ] D5  noteheadBlack (notehead) at (x=1478, y=549) → C5  conf=0.76
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
