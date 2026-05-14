# Cell wtc-p10-sys0-s0-m0 — verdicts

**Image:** ![overlay](../overlays/wtc-p10-sys0-s0-m0.png)

**Clef assumed:** treble

**Staff lines (canonical y):** 254, 316, 379, 443, 508

**Source:** wtc-p10  ·  page 10  ·  sys 0  staff 0  measure 0


## Detections

For each detection below, replace `verdict: __` with one of:
- `TP` — true positive (right symbol, right location)
- `FP` — false positive (wrong symbol or hallucinated)
- `WRONG_PITCH` — notehead at the right location but the pitch field is wrong
- `unsure` — leave for human review

Add an optional 1-word reason after the verdict, e.g. `TP` or `FP barline-mistake`.

- [ ] D0  barlineSingle (barline) at (x=52, y=507)  conf=1.00
       verdict: __________
- [ ] D1  noteheadBlack (notehead) at (x=100, y=558) → C4  conf=0.74
       verdict: __________
- [ ] D2  noteheadBlack (notehead) at (x=133, y=176) → A5  conf=0.63
       verdict: __________
- [ ] D3  flag16thUp (flag) at (x=140, y=373)  conf=0.65
       verdict: __________
- [ ] D4  accidentalNatural (accidental) at (x=458, y=221)  conf=0.58
       verdict: __________
- [ ] D5  noteheadWhole (notehead) at (x=892, y=477) → F4  conf=0.62
       verdict: __________
- [ ] D6  flag16thDown (flag) at (x=901, y=130)  conf=0.59
       verdict: __________
- [ ] D7  noteheadWhole (notehead) at (x=902, y=410) → A4  conf=0.66
       verdict: __________
- [ ] D8  restWhole (rest) at (x=980, y=147)  conf=0.96
       verdict: __________
- [ ] D9  flag16thDown (flag) at (x=1047, y=148)  conf=0.57
       verdict: __________
- [ ] D10  timeSig1 (time_sig_digit) at (x=1105, y=718)  conf=0.56
       verdict: __________
- [ ] D11  noteheadBlack (notehead) at (x=1114, y=286) → E5  conf=0.80
       verdict: __________
- [ ] D12  timeSig1 (time_sig_digit) at (x=1133, y=147)  conf=0.66
       verdict: __________
- [ ] D13  timeSig4 (time_sig_digit) at (x=1214, y=147)  conf=0.55
       verdict: __________
- [ ] D14  noteheadBlack (notehead) at (x=1264, y=351) → C5  conf=0.80
       verdict: __________
- [ ] D15  barlineHeavy (barline) at (x=1394, y=138)  conf=1.00
       verdict: __________
- [ ] D16  noteheadBlack (notehead) at (x=1414, y=445) → G4  conf=0.88
       verdict: __________
- [ ] D17  barlineHeavy (barline) at (x=1455, y=90)  conf=1.00
       verdict: __________
- [ ] D18  noteheadBlack (notehead) at (x=1456, y=150) → B5  conf=0.92
       verdict: __________
- [ ] D19  noteheadBlack (notehead) at (x=1596, y=351) → C5  conf=0.80
       verdict: __________
- [ ] D20  timeSig4 (time_sig_digit) at (x=1743, y=131)  conf=0.62
       verdict: __________
- [ ] D21  noteheadBlack (notehead) at (x=1778, y=286) → E5  conf=0.80
       verdict: __________
- [ ] D22  flag16thDown (flag) at (x=1822, y=131)  conf=0.62
       verdict: __________
- [ ] D23  barlineHeavy (barline) at (x=1886, y=138)  conf=1.00
       verdict: __________
- [ ] D24  timeSig4 (time_sig_digit) at (x=1919, y=707)  conf=0.59
       verdict: __________
- [ ] D25  noteheadBlack (notehead) at (x=1929, y=351) → C5  conf=0.81
       verdict: __________
- [ ] D26  barlineHeavy (barline) at (x=1992, y=706)  conf=1.00
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
