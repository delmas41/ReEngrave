# Cell beet5-p10-sys0-s1-m3 — verdicts

**Image:** ![overlay](../overlays/beet5-p10-sys0-s1-m3.png)

**Clef assumed:** treble

**Staff lines (canonical y):** 362, 454, 547, 633, 725

**Source:** beet5-p10  ·  page 10  ·  sys 0  staff 1  measure 3


## Detections

For each detection below, replace `verdict: __` with one of:
- `TP` — true positive (right symbol, right location)
- `FP` — false positive (wrong symbol or hallucinated)
- `WRONG_PITCH` — notehead at the right location but the pitch field is wrong
- `unsure` — leave for human review

Add an optional 1-word reason after the verdict, e.g. `TP` or `FP barline-mistake`.

- [ ] D0  noteheadBlack (notehead) at (x=1526, y=468) → D5  conf=0.61
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
