# Cell beet5-p10-sys0-s1-m2 — verdicts

**Image:** ![overlay](../overlays/beet5-p10-sys0-s1-m2.png)

**Clef assumed:** treble

**Staff lines (canonical y):** 300, 376, 452, 524, 600

**Source:** beet5-p10  ·  page 10  ·  sys 0  staff 1  measure 2


## Detections

For each detection below, replace `verdict: __` with one of:
- `TP` — true positive (right symbol, right location)
- `FP` — false positive (wrong symbol or hallucinated)
- `WRONG_PITCH` — notehead at the right location but the pitch field is wrong
- `unsure` — leave for human review

Add an optional 1-word reason after the verdict, e.g. `TP` or `FP barline-mistake`.

- [ ] D0  noteheadBlack (notehead) at (x=305, y=403) → C5  conf=0.61
       verdict: __________
- [ ] D1  noteheadBlack (notehead) at (x=807, y=696) → B3  conf=0.64
       verdict: __________
- [ ] D2  noteheadBlack (notehead) at (x=823, y=402) → C5  conf=0.66
       verdict: __________
- [ ] D3  noteheadBlack (notehead) at (x=1069, y=478) → A4  conf=0.61
       verdict: __________
- [ ] D4  noteheadBlack (notehead) at (x=1082, y=399) → C5  conf=0.76
       verdict: __________
- [ ] D5  noteheadBlack (notehead) at (x=1341, y=613) → E4  conf=0.61
       verdict: __________
- [ ] D6  noteheadBlack (notehead) at (x=1682, y=398) → C5  conf=0.63
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
