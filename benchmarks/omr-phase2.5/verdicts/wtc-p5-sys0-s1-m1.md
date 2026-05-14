# Cell wtc-p5-sys0-s1-m1 — verdicts

**Image:** ![overlay](../overlays/wtc-p5-sys0-s1-m1.png)

**Clef assumed:** treble

**Staff lines (canonical y):** 209, 261, 314, 367, 418

**Source:** wtc-p5  ·  page 5  ·  sys 0  staff 1  measure 1


## Detections

For each detection below, replace `verdict: __` with one of:
- `TP` — true positive (right symbol, right location)
- `FP` — false positive (wrong symbol or hallucinated)
- `WRONG_PITCH` — notehead at the right location but the pitch field is wrong
- `unsure` — leave for human review

Add an optional 1-word reason after the verdict, e.g. `TP` or `FP barline-mistake`.

- [ ] D0  rest8th (rest) at (x=73, y=425)  conf=0.81
       verdict: __________
- [ ] D1  noteheadBlack (notehead) at (x=84, y=184) → G5  conf=0.85
       verdict: __________
- [ ] D2  noteheadBlack (notehead) at (x=292, y=420) → E4  conf=0.87
       verdict: __________
- [ ] D3  accidentalFlat (accidental) at (x=292, y=67)  conf=0.61
       verdict: __________
- [ ] D4  noteheadBlack (notehead) at (x=293, y=106) → C6  conf=0.86
       verdict: __________
- [ ] D5  noteheadBlack (notehead) at (x=496, y=210) → F5  conf=0.87
       verdict: __________
- [ ] D6  noteheadBlack (notehead) at (x=498, y=394) → F4  conf=0.79
       verdict: __________
- [ ] D7  noteheadBlack (notehead) at (x=815, y=368) → G4  conf=0.87
       verdict: __________
- [ ] D8  noteheadBlack (notehead) at (x=821, y=128) → B5  conf=0.74
       verdict: __________
- [ ] D9  noteheadBlack (notehead) at (x=1136, y=342) → A4  conf=0.80
       verdict: __________
- [ ] D10  noteheadBlack (notehead) at (x=1142, y=128) → B5  conf=0.74
       verdict: __________
- [ ] D11  noteheadBlack (notehead) at (x=1334, y=236) → E5  conf=0.80
       verdict: __________
- [ ] D12  noteheadBlack (notehead) at (x=1434, y=316) → B4  conf=0.87
       verdict: __________
- [ ] D13  noteheadBlack (notehead) at (x=1552, y=341) → A4  conf=0.79
       verdict: __________
- [ ] D14  noteheadBlack (notehead) at (x=1662, y=368) → G4  conf=0.87
       verdict: __________
- [ ] D15  accidentalFlat (accidental) at (x=1662, y=82)  conf=0.61
       verdict: __________
- [ ] D16  noteheadBlack (notehead) at (x=1668, y=128) → B5  conf=0.74
       verdict: __________
- [ ] D17  noteheadBlack (notehead) at (x=1877, y=289) → C5  conf=0.76
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
