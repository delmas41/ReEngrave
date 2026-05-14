<!-- pre-filled by claude as scaffold; verify before using -->
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

- [x] D0  flag8thUp (flag) at (x=57, y=389)  conf=0.64
       verdict: FP clef-body
- [x] D1  noteheadBlack (notehead) at (x=76, y=427) → C4  conf=0.72
       verdict: FP clef-tail
- [x] D2  noteheadBlack (notehead) at (x=102, y=136) → A5  conf=0.64
       verdict: FP clef-curl
- [x] D3  flag16thUp (flag) at (x=106, y=286)  conf=0.66
       verdict: FP clef-inner
- [x] D4  rest8th (rest) at (x=311, y=444)  conf=0.86
       verdict: unsure rest-or-flag
- [x] D5  barlineHeavy (barline) at (x=320, y=242)  conf=1.00
       verdict: FP stem-of-quarter
- [x] D6  noteheadBlack (notehead) at (x=321, y=317) → A4  conf=0.80
       verdict: TP
- [x] D7  noteheadBlack (notehead) at (x=497, y=439) → C4  conf=0.85
       verdict: TP
- [x] D8  noteheadBlack (notehead) at (x=681, y=170) → G5  conf=0.65
       verdict: unsure small-glyph
- [x] D9  noteheadBlack (notehead) at (x=689, y=415) → D4  conf=0.83
       verdict: TP
- [x] D10  noteheadBlack (notehead) at (x=874, y=390) → E4  conf=0.87
       verdict: TP
- [x] D11  noteheadBlack (notehead) at (x=1070, y=364) → F4  conf=0.79
       verdict: TP
- [x] D12  restHalf (rest) at (x=1070, y=178)  conf=0.93
       verdict: FP above-staff-artifact
- [x] D13  noteheadBlack (notehead) at (x=1351, y=342) → G4  conf=0.87
       verdict: TP
- [x] D14  noteheadBlack (notehead) at (x=1463, y=364) → F4  conf=0.78
       verdict: TP
- [x] D15  noteheadBlack (notehead) at (x=1564, y=390) → E4  conf=0.87
       verdict: TP
- [x] D16  noteheadBlack (notehead) at (x=1770, y=317) → A4  conf=0.81
       verdict: TP

## Missed noteheads (FN)

For each notehead in the cell image that the matcher did NOT find, add a row:

```
FN1 at (x=___, y=___) → pitch=___
```

(none confidently identified in this cell beyond what's already detected)

## Wrong-pitch corrections

Only fill in for detections marked `WRONG_PITCH` above. Format:

```
D0 → correct pitch is C4
```
