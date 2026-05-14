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

- [ ] D0  noteheadWhole (notehead) at (x=892, y=477) → F4  conf=0.62
       verdict: __________
- [ ] D1  flag16thDown (flag) at (x=901, y=130)  conf=0.59
       verdict: __________
- [ ] D2  noteheadWhole (notehead) at (x=902, y=410) → A4  conf=0.66
       verdict: __________
- [ ] D3  flag16thDown (flag) at (x=1047, y=148)  conf=0.57
       verdict: __________
- [ ] D4  noteheadBlack (notehead) at (x=1114, y=286) → E5  conf=0.80
       verdict: __________
- [ ] D5  noteheadBlack (notehead) at (x=1264, y=351) → C5  conf=0.80
       verdict: __________
- [ ] D6  noteheadBlack (notehead) at (x=1414, y=445) → G4  conf=0.88
       verdict: __________
- [ ] D7  noteheadBlack (notehead) at (x=1456, y=150) → B5  conf=0.92
       verdict: __________
- [ ] D8  noteheadBlack (notehead) at (x=1596, y=351) → C5  conf=0.80
       verdict: __________
- [ ] D9  noteheadBlack (notehead) at (x=1778, y=286) → E5  conf=0.80
       verdict: __________
- [ ] D10  flag16thDown (flag) at (x=1822, y=131)  conf=0.62
       verdict: __________
- [ ] D11  flag8thUp (flag) at (x=1886, y=138)  conf=0.63
       verdict: __________
- [ ] D12  noteheadBlack (notehead) at (x=1929, y=351) → C5  conf=0.81
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
