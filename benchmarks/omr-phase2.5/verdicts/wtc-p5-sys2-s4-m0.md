# Cell wtc-p5-sys2-s4-m0 — verdicts

**Image:** ![overlay](../overlays/wtc-p5-sys2-s4-m0.png)

**Clef assumed:** treble

**Staff lines (canonical y):** 199, 249, 298, 349, 399

**Source:** wtc-p5  ·  page 5  ·  sys 2  staff 4  measure 0


## Detections

For each detection below, replace `verdict: __` with one of:
- `TP` — true positive (right symbol, right location)
- `FP` — false positive (wrong symbol or hallucinated)
- `WRONG_PITCH` — notehead at the right location but the pitch field is wrong
- `unsure` — leave for human review

Add an optional 1-word reason after the verdict, e.g. `TP` or `FP barline-mistake`.

- [ ] D0  barlineSingle (barline) at (x=40, y=399)  conf=1.00
       verdict: __________
- [ ] D1  noteheadBlack (notehead) at (x=78, y=438) → C4  conf=0.73
       verdict: __________
- [ ] D2  noteheadBlack (notehead) at (x=104, y=140) → A5  conf=0.63
       verdict: __________
- [ ] D3  flag16thUp (flag) at (x=109, y=293)  conf=0.66
       verdict: __________
- [ ] D4  noteheadBlack (notehead) at (x=328, y=150) → A5  conf=0.86
       verdict: __________
- [ ] D5  noteheadBlack (notehead) at (x=331, y=325) → A4  conf=0.79
       verdict: __________
- [ ] D6  rest8th (rest) at (x=336, y=575)  conf=0.57
       verdict: __________
- [ ] D7  noteheadBlack (notehead) at (x=484, y=276) → C5  conf=0.78
       verdict: __________
- [ ] D8  rest8th (rest) at (x=595, y=406)  conf=0.83
       verdict: __________
- [ ] D9  noteheadBlack (notehead) at (x=605, y=250) → D5  conf=0.87
       verdict: __________
- [ ] D10  noteheadBlack (notehead) at (x=724, y=175) → G5  conf=0.84
       verdict: __________
- [ ] D11  rest8th (rest) at (x=836, y=406)  conf=0.83
       verdict: __________
- [ ] D12  noteheadBlack (notehead) at (x=846, y=225) → E5  conf=0.80
       verdict: __________
- [ ] D13  flag8thDown (flag) at (x=1002, y=462)  conf=0.78
       verdict: __________
- [ ] D14  noteheadBlack (notehead) at (x=1004, y=400) → E4  conf=0.79
       verdict: __________
- [ ] D15  noteheadBlack (notehead) at (x=1075, y=250) → D5  conf=0.88
       verdict: __________
- [ ] D16  timeSig1 (time_sig_digit) at (x=1138, y=375)  conf=0.77
       verdict: __________
- [ ] D17  noteheadBlack (notehead) at (x=1214, y=376) → F4  conf=0.81
       verdict: __________
- [ ] D18  noteheadBlack (notehead) at (x=1216, y=250) → D5  conf=0.87
       verdict: __________
- [ ] D19  flag8thUp (flag) at (x=1235, y=185)  conf=0.86
       verdict: __________
- [ ] D20  rest8th (rest) at (x=1354, y=203)  conf=0.83
       verdict: __________
- [ ] D21  noteheadBlack (notehead) at (x=1361, y=350) → G4  conf=0.87
       verdict: __________
- [ ] D22  noteheadBlack (notehead) at (x=1659, y=125) → B5  conf=0.66
       verdict: __________
- [ ] D23  noteheadBlack (notehead) at (x=1666, y=326) → A4  conf=0.79
       verdict: __________
- [ ] D24  noteheadBlack (notehead) at (x=1895, y=300) → B4  conf=0.88
       verdict: __________
- [ ] D25  noteheadBlack (notehead) at (x=1991, y=325) → A4  conf=0.80
       verdict: __________
- [ ] D26  stem (stem) at (x=2044, y=399)  conf=1.00
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
