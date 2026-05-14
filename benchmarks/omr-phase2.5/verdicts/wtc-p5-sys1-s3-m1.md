# Cell wtc-p5-sys1-s3-m1 — verdicts

**Image:** ![overlay](../overlays/wtc-p5-sys1-s3-m1.png)

**Clef assumed:** bass

**Staff lines (canonical y):** 155, 194, 233, 273, 310

**Source:** wtc-p5  ·  page 5  ·  sys 1  staff 3  measure 1


## Detections

For each detection below, replace `verdict: __` with one of:
- `TP` — true positive (right symbol, right location)
- `FP` — false positive (wrong symbol or hallucinated)
- `WRONG_PITCH` — notehead at the right location but the pitch field is wrong
- `unsure` — leave for human review

Add an optional 1-word reason after the verdict, e.g. `TP` or `FP barline-mistake`.

- [ ] D0  noteheadBlack (notehead) at (x=75, y=135) → B3  conf=0.81
       verdict: __________
- [ ] D1  noteheadBlack (notehead) at (x=76, y=175) → G3  conf=0.76
       verdict: __________
- [ ] D2  noteheadBlack (notehead) at (x=280, y=78) → E4  conf=0.87
       verdict: __________
- [ ] D3  noteheadBlack (notehead) at (x=378, y=156) → A3  conf=0.85
       verdict: __________
- [ ] D4  noteheadBlack (notehead) at (x=481, y=175) → G3  conf=0.78
       verdict: __________
- [ ] D5  noteheadBlack (notehead) at (x=579, y=195) → F3  conf=0.87
       verdict: __________
- [ ] D6  noteheadBlack (notehead) at (x=579, y=78) → E4  conf=0.86
       verdict: __________
- [ ] D7  noteheadBlack (notehead) at (x=880, y=78) → E4  conf=0.87
       verdict: __________
- [ ] D8  noteheadBlack (notehead) at (x=882, y=137) → B3  conf=0.66
       verdict: __________
- [ ] D9  noteheadBlack (notehead) at (x=1033, y=94) → D4  conf=0.72
       verdict: __________
- [ ] D10  noteheadBlack (notehead) at (x=1178, y=117) → C4  conf=0.86
       verdict: __________
- [ ] D11  noteheadBlack (notehead) at (x=1182, y=214) → E3  conf=0.81
       verdict: __________
- [ ] D12  flag8thUp (flag) at (x=1192, y=69)  conf=0.86
       verdict: __________
- [ ] D13  noteheadBlack (notehead) at (x=1479, y=157) → A3  conf=0.86
       verdict: __________
- [ ] D14  noteheadBlack (notehead) at (x=1770, y=157) → A3  conf=0.85
       verdict: __________
- [ ] D15  noteheadBlack (notehead) at (x=1921, y=136) → B3  conf=0.82
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
