# Cell wtc-p5-sys1-s2-m1 — verdicts

**Image:** ![overlay](../overlays/wtc-p5-sys1-s2-m1.png)

**Clef assumed:** treble

**Staff lines (canonical y):** 155, 195, 232, 271, 310

**Source:** wtc-p5  ·  page 5  ·  sys 1  staff 2  measure 1


## Detections

For each detection below, replace `verdict: __` with one of:
- `TP` — true positive (right symbol, right location)
- `FP` — false positive (wrong symbol or hallucinated)
- `WRONG_PITCH` — notehead at the right location but the pitch field is wrong
- `unsure` — leave for human review

Add an optional 1-word reason after the verdict, e.g. `TP` or `FP barline-mistake`.

- [ ] D0  noteheadBlack (notehead) at (x=73, y=233) → B4  conf=0.81
       verdict: __________
- [ ] D1  noteheadBlack (notehead) at (x=75, y=193) → D5  conf=0.81
       verdict: __________
- [ ] D2  accidentalFlat (accidental) at (x=222, y=74)  conf=0.85
       verdict: __________
- [ ] D3  noteheadBlack (notehead) at (x=282, y=136) → G5  conf=0.66
       verdict: __________
- [ ] D4  noteheadBlack (notehead) at (x=283, y=93) → B5  conf=0.73
       verdict: __________
- [ ] D5  noteheadBlack (notehead) at (x=579, y=115) → A5  conf=0.85
       verdict: __________
- [ ] D6  noteheadBlack (notehead) at (x=582, y=213) → C5  conf=0.81
       verdict: __________
- [ ] D7  noteheadBlack (notehead) at (x=879, y=194) → D5  conf=0.87
       verdict: __________
- [ ] D8  noteheadBlack (notehead) at (x=880, y=135) → G5  conf=0.82
       verdict: __________
- [ ] D9  noteheadBlack (notehead) at (x=1030, y=155) → F5  conf=0.86
       verdict: __________
- [ ] D10  noteheadBlack (notehead) at (x=1181, y=134) → G5  conf=0.80
       verdict: __________
- [ ] D11  noteheadBlack (notehead) at (x=1181, y=174) → E5  conf=0.76
       verdict: __________
- [ ] D12  noteheadBlack (notehead) at (x=1330, y=155) → F5  conf=0.86
       verdict: __________
- [ ] D13  noteheadBlack (notehead) at (x=1480, y=134) → G5  conf=0.81
       verdict: __________
- [ ] D14  noteheadBlack (notehead) at (x=1482, y=213) → C5  conf=0.80
       verdict: __________
- [ ] D15  noteheadBlack (notehead) at (x=1620, y=175) → E5  conf=0.75
       verdict: __________
- [ ] D16  noteheadBlack (notehead) at (x=1770, y=195) → D5  conf=0.80
       verdict: __________
- [ ] D17  noteheadBlack (notehead) at (x=1771, y=155) → F5  conf=0.78
       verdict: __________
- [ ] D18  noteheadBlack (notehead) at (x=1921, y=135) → G5  conf=0.81
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
