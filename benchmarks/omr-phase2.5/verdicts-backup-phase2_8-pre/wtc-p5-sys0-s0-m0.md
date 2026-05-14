# Cell wtc-p5-sys0-s0-m0 — verdicts

**Image:** ![overlay](../overlays/wtc-p5-sys0-s0-m0.png)

**Clef assumed:** treble

**Staff lines (canonical y):** 194, 243, 291, 339, 389

**Source:** wtc-p5  ·  page 5  ·  sys 0  staff 0  measure 0


## Detections

For each detection below, replace `verdict: __` with one of:
- `TP` — true positive (right symbol, right location)
- `FP` — false positive (wrong symbol or hallucinated)
- `WRONG_PITCH` — notehead at the right location but the pitch field is wrong
- `unsure` — leave for human review

Add an optional 1-word reason after the verdict, e.g. `TP` or `FP barline-mistake`.

- [ ] D0  noteheadBlack (notehead) at (x=321, y=317) → A4  conf=0.80
       verdict: __________
- [ ] D1  noteheadBlack (notehead) at (x=497, y=439) → C4  conf=0.85
       verdict: __________
- [ ] D2  noteheadBlack (notehead) at (x=681, y=170) → G5  conf=0.65
       verdict: __________
- [ ] D3  noteheadBlack (notehead) at (x=689, y=415) → D4  conf=0.83
       verdict: __________
- [ ] D4  noteheadBlack (notehead) at (x=874, y=390) → E4  conf=0.87
       verdict: __________
- [ ] D5  noteheadBlack (notehead) at (x=1070, y=364) → F4  conf=0.79
       verdict: __________
- [ ] D6  noteheadBlack (notehead) at (x=1351, y=342) → G4  conf=0.87
       verdict: __________
- [ ] D7  noteheadBlack (notehead) at (x=1463, y=364) → F4  conf=0.78
       verdict: __________
- [ ] D8  noteheadBlack (notehead) at (x=1564, y=390) → E4  conf=0.87
       verdict: __________
- [ ] D9  noteheadBlack (notehead) at (x=1770, y=317) → A4  conf=0.81
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
