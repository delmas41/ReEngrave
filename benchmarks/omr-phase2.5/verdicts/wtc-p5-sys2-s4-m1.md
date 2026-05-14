# Cell wtc-p5-sys2-s4-m1 — verdicts

**Image:** ![overlay](../overlays/wtc-p5-sys2-s4-m1.png)

**Clef assumed:** treble

**Staff lines (canonical y):** 200, 250, 300, 351, 401

**Source:** wtc-p5  ·  page 5  ·  sys 2  staff 4  measure 1


## Detections

For each detection below, replace `verdict: __` with one of:
- `TP` — true positive (right symbol, right location)
- `FP` — false positive (wrong symbol or hallucinated)
- `WRONG_PITCH` — notehead at the right location but the pitch field is wrong
- `unsure` — leave for human review

Add an optional 1-word reason after the verdict, e.g. `TP` or `FP barline-mistake`.

- [ ] D0  noteheadBlack (notehead) at (x=76, y=352) → G4  conf=0.86
       verdict: __________
- [ ] D1  noteheadBlack (notehead) at (x=318, y=276) → C5  conf=0.77
       verdict: __________
- [ ] D2  noteheadBlack (notehead) at (x=559, y=377) → F4  conf=0.80
       verdict: __________
- [ ] D3  noteheadBlack (notehead) at (x=836, y=302) → B4  conf=0.86
       verdict: __________
- [ ] D4  noteheadBlack (notehead) at (x=1108, y=126) → B5  conf=0.66
       verdict: __________
- [ ] D5  noteheadBlack (notehead) at (x=1115, y=302) → B4  conf=0.87
       verdict: __________
- [ ] D6  noteheadBlack (notehead) at (x=1236, y=276) → C5  conf=0.80
       verdict: __________
- [ ] D7  noteheadBlack (notehead) at (x=1356, y=302) → B4  conf=0.86
       verdict: __________
- [ ] D8  noteheadBlack (notehead) at (x=1479, y=327) → A4  conf=0.80
       verdict: __________
- [ ] D9  rest8th (rest) at (x=1587, y=205)  conf=0.83
       verdict: __________
- [ ] D10  noteheadBlack (notehead) at (x=1596, y=352) → G4  conf=0.86
       verdict: __________
- [ ] D11  noteheadBlack (notehead) at (x=1717, y=377) → F4  conf=0.78
       verdict: __________
- [ ] D12  noteheadBlack (notehead) at (x=1837, y=404) → E4  conf=0.81
       verdict: __________
- [ ] D13  noteheadBlack (notehead) at (x=1839, y=350) → G4  conf=0.80
       verdict: __________
- [ ] D14  noteheadBlack (notehead) at (x=1956, y=429) → D4  conf=0.82
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
