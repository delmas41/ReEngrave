# Cell wtc-p5-sys0-s1-m0 — verdicts

**Image:** ![overlay](../overlays/wtc-p5-sys0-s1-m0.png)

**Clef assumed:** treble

**Staff lines (canonical y):** 194, 243, 292, 342, 389

**Source:** wtc-p5  ·  page 5  ·  sys 0  staff 1  measure 0


## Detections

For each detection below, replace `verdict: __` with one of:
- `TP` — true positive (right symbol, right location)
- `FP` — false positive (wrong symbol or hallucinated)
- `WRONG_PITCH` — notehead at the right location but the pitch field is wrong
- `unsure` — leave for human review

Add an optional 1-word reason after the verdict, e.g. `TP` or `FP barline-mistake`.

- [ ] D0  noteheadBlack (notehead) at (x=320, y=196) → F5  conf=0.88
       verdict: __________
- [ ] D1  noteheadBlack (notehead) at (x=323, y=366) → F4  conf=0.80
       verdict: __________
- [ ] D2  noteheadBlack (notehead) at (x=681, y=365) → F4  conf=0.66
       verdict: __________
- [ ] D3  rest8th (rest) at (x=681, y=199)  conf=0.83
       verdict: __________
- [ ] D4  noteheadBlack (notehead) at (x=876, y=221) → E5  conf=0.80
       verdict: __________
- [ ] D5  flag8thUp (flag) at (x=894, y=159)  conf=0.87
       verdict: __________
- [ ] D6  noteheadBlack (notehead) at (x=1067, y=196) → F5  conf=0.88
       verdict: __________
- [ ] D7  noteheadBlack (notehead) at (x=1259, y=171) → G5  conf=0.85
       verdict: __________
- [ ] D8  noteheadBlack (notehead) at (x=1565, y=148) → A5  conf=0.86
       verdict: __________
- [ ] D9  noteheadBlack (notehead) at (x=1868, y=119) → B5  conf=0.75
       verdict: __________
- [ ] D10  noteheadBlack (notehead) at (x=1970, y=148) → A5  conf=0.86
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
