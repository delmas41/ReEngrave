# Cell wtc-p5-sys1-s3-m0 — verdicts

**Image:** ![overlay](../overlays/wtc-p5-sys1-s3-m0.png)

**Clef assumed:** bass

**Staff lines (canonical y):** 130, 162, 195, 229, 260

**Source:** wtc-p5  ·  page 5  ·  sys 1  staff 3  measure 0


## Detections

For each detection below, replace `verdict: __` with one of:
- `TP` — true positive (right symbol, right location)
- `FP` — false positive (wrong symbol or hallucinated)
- `WRONG_PITCH` — notehead at the right location but the pitch field is wrong
- `unsure` — leave for human review

Add an optional 1-word reason after the verdict, e.g. `TP` or `FP barline-mistake`.

- [ ] D0  noteheadBlack (notehead) at (x=217, y=245) → A2  conf=0.79
       verdict: __________
- [ ] D1  noteheadBlack (notehead) at (x=381, y=164) → F3  conf=0.82
       verdict: __________
- [ ] D2  noteheadBlack (notehead) at (x=382, y=130) → A3  conf=0.81
       verdict: __________
- [ ] D3  noteheadBlack (notehead) at (x=631, y=147) → G3  conf=0.78
       verdict: __________
- [ ] D4  noteheadBlack (notehead) at (x=632, y=114) → B3  conf=0.82
       verdict: __________
- [ ] D5  noteheadBlack (notehead) at (x=801, y=97) → C4  conf=0.87
       verdict: __________
- [ ] D6  noteheadBlack (notehead) at (x=803, y=180) → E3  conf=0.78
       verdict: __________
- [ ] D7  noteheadBlack (notehead) at (x=966, y=196) → D3  conf=0.88
       verdict: __________
- [ ] D8  noteheadBlack (notehead) at (x=971, y=78) → D4  conf=0.72
       verdict: __________
- [ ] D9  noteheadBlack (notehead) at (x=1344, y=65) → E4  conf=0.86
       verdict: __________
- [ ] D10  noteheadBlack (notehead) at (x=1432, y=78) → D4  conf=0.72
       verdict: __________
- [ ] D11  noteheadBlack (notehead) at (x=1527, y=97) → C4  conf=0.87
       verdict: __________
- [ ] D12  noteheadBlack (notehead) at (x=1528, y=180) → E3  conf=0.79
       verdict: __________
- [ ] D13  noteheadBlack (notehead) at (x=1821, y=163) → F3  conf=0.88
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
