# Cell beet5-p10-sys0-s1-m1 — verdicts

**Image:** ![overlay](../overlays/beet5-p10-sys0-s1-m1.png)

**Clef assumed:** treble

**Staff lines (canonical y):** 400, 502, 603, 698, 800

**Source:** beet5-p10  ·  page 10  ·  sys 0  staff 1  measure 1


## Detections

For each detection below, replace `verdict: __` with one of:
- `TP` — true positive (right symbol, right location)
- `FP` — false positive (wrong symbol or hallucinated)
- `WRONG_PITCH` — notehead at the right location but the pitch field is wrong
- `unsure` — leave for human review

Add an optional 1-word reason after the verdict, e.g. `TP` or `FP barline-mistake`.

- [ ] D0  noteheadBlack (notehead) at (x=182, y=896) → C4  conf=0.68
       verdict: __________
- [ ] D1  noteheadBlack (notehead) at (x=190, y=1057) → G3  conf=0.75
       verdict: __________
- [ ] D2  restHalf (rest) at (x=207, y=1076)  conf=0.96
       verdict: __________
- [ ] D3  noteheadBlack (notehead) at (x=230, y=539) → C5  conf=0.66
       verdict: __________
- [ ] D4  noteheadBlack (notehead) at (x=234, y=835) → D4  conf=0.67
       verdict: __________
- [ ] D5  noteheadBlack (notehead) at (x=253, y=1005) → A3  conf=0.67
       verdict: __________
- [ ] D6  noteheadBlack (notehead) at (x=536, y=540) → C5  conf=0.73
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
