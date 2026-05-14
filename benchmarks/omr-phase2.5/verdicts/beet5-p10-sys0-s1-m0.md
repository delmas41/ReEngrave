# Cell beet5-p10-sys0-s1-m0 — verdicts

**Image:** ![overlay](../overlays/beet5-p10-sys0-s1-m0.png)

**Clef assumed:** treble

**Staff lines (canonical y):** 169, 212, 255, 295, 338

**Source:** beet5-p10  ·  page 10  ·  sys 0  staff 1  measure 0


## Detections

For each detection below, replace `verdict: __` with one of:
- `TP` — true positive (right symbol, right location)
- `FP` — false positive (wrong symbol or hallucinated)
- `WRONG_PITCH` — notehead at the right location but the pitch field is wrong
- `unsure` — leave for human review

Add an optional 1-word reason after the verdict, e.g. `TP` or `FP barline-mistake`.

- [ ] D0  noteheadBlack (notehead) at (x=114, y=230) → C5  conf=0.75
       verdict: __________
- [ ] D1  noteheadBlack (notehead) at (x=142, y=194) → E5  conf=0.68
       verdict: __________
- [ ] D2  noteheadBlack (notehead) at (x=440, y=127) → A5  conf=0.60
       verdict: __________
- [ ] D3  noteheadBlack (notehead) at (x=451, y=101) → B5  conf=0.68
       verdict: __________
- [ ] D4  noteheadBlack (notehead) at (x=1453, y=232) → C5  conf=0.61
       verdict: __________
- [ ] D5  noteheadBlack (notehead) at (x=1701, y=130) → A5  conf=0.63
       verdict: __________
- [ ] D6  noteheadBlack (notehead) at (x=1744, y=60) → D6  conf=0.76
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
