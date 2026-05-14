<!-- pre-filled by claude as scaffold; verify before using -->
# Cell wtc-p5-sys0-s0-m2 — verdicts

**Image:** ![overlay](../overlays/wtc-p5-sys0-s0-m2.png)

**Clef assumed:** treble

**Staff lines (canonical y):** 191, 238, 285, 333, 381

**Source:** wtc-p5  ·  page 5  ·  sys 0  staff 0  measure 2


## Detections

For each detection below, replace `verdict: __` with one of:
- `TP` — true positive (right symbol, right location)
- `FP` — false positive (wrong symbol or hallucinated)
- `WRONG_PITCH` — notehead at the right location but the pitch field is wrong
- `unsure` — leave for human review

Add an optional 1-word reason after the verdict, e.g. `TP` or `FP barline-mistake`.

- [x] D0  stem (stem) at (x=15, y=382)  conf=1.00
       verdict: FP edge-fragment
- [x] D1  noteheadBlack (notehead) at (x=77, y=335) → G4  conf=0.87
       verdict: TP
- [x] D2  noteheadBlack (notehead) at (x=78, y=262) → C5  conf=0.81
       verdict: TP
- [x] D3  restQuarter (rest) at (x=201, y=358)  conf=0.56
       verdict: FP sharp-accidental-misclassified
- [x] D4  noteheadBlack (notehead) at (x=278, y=358) → F4  conf=0.80
       verdict: TP
- [x] D5  noteheadBlack (notehead) at (x=369, y=238) → D5  conf=0.87
       verdict: TP
- [x] D6  noteheadBlack (notehead) at (x=472, y=262) → C5  conf=0.80
       verdict: TP
- [x] D7  noteheadBlack (notehead) at (x=622, y=335) → G4  conf=0.82
       verdict: TP
- [x] D8  noteheadBlack (notehead) at (x=624, y=286) → B4  conf=0.80
       verdict: TP
- [x] D9  noteheadBlack (notehead) at (x=915, y=312) → A4  conf=0.78
       verdict: TP
- [x] D10  noteheadBlack (notehead) at (x=917, y=261) → C5  conf=0.79
       verdict: TP
- [x] D11  noteheadBlack (notehead) at (x=1208, y=312) → A4  conf=0.79
       verdict: TP
- [x] D12  noteheadBlack (notehead) at (x=1210, y=238) → D5  conf=0.87
       verdict: TP
- [x] D13  noteheadBlack (notehead) at (x=1396, y=335) → G4  conf=0.87
       verdict: TP
- [x] D14  noteheadBlack (notehead) at (x=1399, y=213) → E5  conf=0.78
       verdict: TP
- [x] D15  noteheadBlack (notehead) at (x=1582, y=312) → A4  conf=0.79
       verdict: TP
- [x] D16  noteheadBlack (notehead) at (x=1583, y=191) → F5  conf=0.88
       verdict: TP
- [x] D17  timeSig1 (time_sig_digit) at (x=1705, y=287)  conf=0.83
       verdict: FP accidental-misclassified
- [x] D18  noteheadBlack (notehead) at (x=1770, y=287) → B4  conf=0.87
       verdict: TP
- [x] D19  noteheadBlack (notehead) at (x=1864, y=166) → G5  conf=0.85
       verdict: TP
- [x] D20  noteheadBlack (notehead) at (x=1967, y=191) → F5  conf=0.87
       verdict: TP

## Missed noteheads (FN)

For each notehead in the cell image that the matcher did NOT find, add a row:

```
FN1 at (x=___, y=___) → pitch=___
```

(none confidently identified — the dense overlapping chords made some noteheads ambiguous but matcher captured the bulk of them)

## Wrong-pitch corrections

Only fill in for detections marked `WRONG_PITCH` above. Format:

```
D0 → correct pitch is C4
```
