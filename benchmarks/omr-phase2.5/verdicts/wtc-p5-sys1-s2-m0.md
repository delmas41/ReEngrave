# Cell wtc-p5-sys1-s2-m0 — verdicts

**Image:** ![overlay](../overlays/wtc-p5-sys1-s2-m0.png)

**Clef assumed:** treble

**Staff lines (canonical y):** 130, 163, 194, 227, 260

**Source:** wtc-p5  ·  page 5  ·  sys 1  staff 2  measure 0


## Detections

For each detection below, replace `verdict: __` with one of:
- `TP` — true positive (right symbol, right location)
- `FP` — false positive (wrong symbol or hallucinated)
- `WRONG_PITCH` — notehead at the right location but the pitch field is wrong
- `unsure` — leave for human review

Add an optional 1-word reason after the verdict, e.g. `TP` or `FP barline-mistake`.

- [ ] D0  noteheadBlack (notehead) at (x=51, y=286) → C4  conf=0.75
       verdict: __________
- [ ] D1  noteheadBlack (notehead) at (x=69, y=90) → A5  conf=0.64
       verdict: __________
- [ ] D2  noteheadBlack (notehead) at (x=216, y=145) → E5  conf=0.77
       verdict: __________
- [ ] D3  noteheadBlack (notehead) at (x=217, y=179) → C5  conf=0.78
       verdict: __________
- [ ] D4  noteheadBlack (notehead) at (x=382, y=96) → A5  conf=0.87
       verdict: __________
- [ ] D5  noteheadBlack (notehead) at (x=463, y=162) → D5  conf=0.88
       verdict: __________
- [ ] D6  noteheadBlack (notehead) at (x=550, y=179) → C5  conf=0.79
       verdict: __________
- [ ] D7  noteheadBlack (notehead) at (x=631, y=195) → B4  conf=0.83
       verdict: __________
- [ ] D8  noteheadBlack (notehead) at (x=632, y=162) → D5  conf=0.81
       verdict: __________
- [ ] D9  noteheadBlack (notehead) at (x=800, y=146) → E5  conf=0.79
       verdict: __________
- [ ] D10  noteheadBlack (notehead) at (x=801, y=113) → G5  conf=0.84
       verdict: __________
- [ ] D11  noteheadBlack (notehead) at (x=966, y=212) → A4  conf=0.81
       verdict: __________
- [ ] D12  noteheadBlack (notehead) at (x=967, y=113) → G5  conf=0.84
       verdict: __________
- [ ] D13  noteheadBlack (notehead) at (x=1093, y=96) → A5  conf=0.87
       verdict: __________
- [ ] D14  restHalf (rest) at (x=1216, y=368)  conf=0.60
       verdict: __________
- [ ] D15  noteheadBlack (notehead) at (x=1219, y=162) → D5  conf=0.87
       verdict: __________
- [ ] D16  noteheadBlack (notehead) at (x=1219, y=113) → G5  conf=0.85
       verdict: __________
- [ ] D17  noteheadBlack (notehead) at (x=1344, y=130) → F5  conf=0.88
       verdict: __________
- [ ] D18  noteheadBlack (notehead) at (x=1527, y=145) → E5  conf=0.80
       verdict: __________
- [ ] D19  noteheadBlack (notehead) at (x=1569, y=162) → D5  conf=0.88
       verdict: __________
- [ ] D20  rest8th (rest) at (x=1692, y=374)  conf=0.56
       verdict: __________
- [ ] D21  noteheadBlack (notehead) at (x=1697, y=146) → E5  conf=0.76
       verdict: __________
- [ ] D22  noteheadBlack (notehead) at (x=1821, y=162) → D5  conf=0.88
       verdict: __________
- [ ] D23  noteheadBlack (notehead) at (x=1821, y=96) → A5  conf=0.87
       verdict: __________
- [ ] D24  noteheadBlack (notehead) at (x=1948, y=179) → C5  conf=0.79
       verdict: __________
- [ ] D25  stem (stem) at (x=2046, y=260)  conf=1.00
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
