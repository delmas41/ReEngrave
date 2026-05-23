# Cell wtc-p5-sys1-s2-m2 — verdicts

**Image:** ![overlay](../overlays/wtc-p5-sys1-s2-m2.png)

**Clef assumed:** treble

**Staff lines (canonical y):** 400, 503, 597, 700, 800

**Source:** wtc-p5  ·  page 5  ·  sys 1  staff 2  measure 2


## Detections

For each detection below, replace `verdict: __` with one of:
- `TP` — true positive (right symbol, right location)
- `FP` — false positive (wrong symbol or hallucinated)
- `WRONG_PITCH` — notehead at the right location but the pitch field is wrong
- `unsure` — leave for human review

Add an optional 1-word reason after the verdict, e.g. `TP` or `FP barline-mistake`.

- [ ] D0  noteheadBlack (notehead) at (x=66, y=449) → E5  conf=0.77
       verdict: __________
- [ ] D1  noteheadBlack (notehead) at (x=68, y=344) → G5  conf=0.77
       verdict: __________
- [ ] D2  noteheadBlack (notehead) at (x=450, y=400) → F5  conf=0.88
       verdict: __________
- [ ] D3  noteheadBlack (notehead) at (x=708, y=350) → G5  conf=0.79
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
