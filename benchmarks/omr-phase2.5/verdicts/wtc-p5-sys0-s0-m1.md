# Cell wtc-p5-sys0-s0-m1 — verdicts

**Image:** ![overlay](../overlays/wtc-p5-sys0-s0-m1.png)

**Clef assumed:** treble

**Staff lines (canonical y):** 209, 261, 313, 364, 418

**Source:** wtc-p5  ·  page 5  ·  sys 0  staff 0  measure 1


## Detections

For each detection below, replace `verdict: __` with one of:
- `TP` — true positive (right symbol, right location)
- `FP` — false positive (wrong symbol or hallucinated)
- `WRONG_PITCH` — notehead at the right location but the pitch field is wrong
- `unsure` — leave for human review

Add an optional 1-word reason after the verdict, e.g. `TP` or `FP barline-mistake`.

- [ ] D0  noteheadBlack (notehead) at (x=82, y=445) → D4  conf=0.83
       verdict: __________
- [ ] D1  noteheadBlack (notehead) at (x=292, y=367) → G4  conf=0.87
       verdict: __________
- [ ] D2  noteheadBlack (notehead) at (x=494, y=367) → G4  conf=0.87
       verdict: __________
- [ ] D3  noteheadBlack (notehead) at (x=654, y=340) → A4  conf=0.82
       verdict: __________
- [ ] D4  noteheadBlack (notehead) at (x=815, y=367) → G4  conf=0.87
       verdict: __________
- [ ] D5  noteheadBlack (notehead) at (x=975, y=394) → F4  conf=0.79
       verdict: __________
- [ ] D6  rest8th (rest) at (x=1128, y=213)  conf=0.81
       verdict: __________
- [ ] D7  noteheadBlack (notehead) at (x=1136, y=419) → E4  conf=0.87
       verdict: __________
- [ ] D8  noteheadBlack (notehead) at (x=1332, y=419) → E4  conf=0.81
       verdict: __________
- [ ] D9  noteheadBlack (notehead) at (x=1335, y=365) → G4  conf=0.80
       verdict: __________
- [ ] D10  noteheadBlack (notehead) at (x=1664, y=338) → A4  conf=0.77
       verdict: __________
- [ ] D11  noteheadBlack (notehead) at (x=1665, y=393) → F4  conf=0.78
       verdict: __________
- [ ] D12  noteheadBlack (notehead) at (x=1873, y=368) → G4  conf=0.80
       verdict: __________
- [ ] D13  noteheadBlack (notehead) at (x=1875, y=314) → B4  conf=0.80
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
