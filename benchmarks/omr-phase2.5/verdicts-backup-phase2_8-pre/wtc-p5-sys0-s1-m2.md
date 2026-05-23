# Cell wtc-p5-sys0-s1-m2 — verdicts

**Image:** ![overlay](../overlays/wtc-p5-sys0-s1-m2.png)

**Clef assumed:** treble

**Staff lines (canonical y):** 191, 238, 287, 335, 381

**Source:** wtc-p5  ·  page 5  ·  sys 0  staff 1  measure 2


## Detections

For each detection below, replace `verdict: __` with one of:
- `TP` — true positive (right symbol, right location)
- `FP` — false positive (wrong symbol or hallucinated)
- `WRONG_PITCH` — notehead at the right location but the pitch field is wrong
- `unsure` — leave for human review

Add an optional 1-word reason after the verdict, e.g. `TP` or `FP barline-mistake`.

- [ ] D0  noteheadBlack (notehead) at (x=77, y=360) → F4  conf=0.79
       verdict: __________
- [ ] D1  noteheadBlack (notehead) at (x=78, y=145) → A5  conf=0.86
       verdict: __________
- [ ] D2  noteheadBlack (notehead) at (x=275, y=289) → B4  conf=0.87
       verdict: __________
- [ ] D3  noteheadBlack (notehead) at (x=277, y=192) → F5  conf=0.87
       verdict: __________
- [ ] D4  noteheadBlack (notehead) at (x=622, y=289) → B4  conf=0.87
       verdict: __________
- [ ] D5  noteheadBlack (notehead) at (x=623, y=96) → C6  conf=0.85
       verdict: __________
- [ ] D6  noteheadBlack (notehead) at (x=769, y=264) → C5  conf=0.80
       verdict: __________
- [ ] D7  noteheadBlack (notehead) at (x=915, y=289) → B4  conf=0.87
       verdict: __________
- [ ] D8  noteheadBlack (notehead) at (x=1061, y=313) → A4  conf=0.79
       verdict: __________
- [ ] D9  noteheadBlack (notehead) at (x=1208, y=336) → G4  conf=0.87
       verdict: __________
- [ ] D10  noteheadBlack (notehead) at (x=1214, y=116) → B5  conf=0.74
       verdict: __________
- [ ] D11  flag16thUp (flag) at (x=1220, y=75)  conf=0.64
       verdict: __________
- [ ] D12  flag8thDown (flag) at (x=1326, y=307)  conf=0.70
       verdict: __________
- [ ] D13  rest8th (rest) at (x=1389, y=195)  conf=0.85
       verdict: __________
- [ ] D14  noteheadBlack (notehead) at (x=1397, y=336) → G4  conf=0.87
       verdict: __________
- [ ] D15  noteheadBlack (notehead) at (x=1574, y=168) → G5  conf=0.66
       verdict: __________
- [ ] D16  noteheadBlack (notehead) at (x=1585, y=360) → F4  conf=0.80
       verdict: __________
- [ ] D17  noteheadBlack (notehead) at (x=1770, y=383) → E4  conf=0.87
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
