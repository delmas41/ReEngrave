# Cell wtc-p5-sys2-s4-m2 — verdicts

**Image:** ![overlay](../overlays/wtc-p5-sys2-s4-m2.png)

**Clef assumed:** treble

**Staff lines (canonical y):** 193, 241, 289, 339, 387

**Source:** wtc-p5  ·  page 5  ·  sys 2  staff 4  measure 2


## Detections

For each detection below, replace `verdict: __` with one of:
- `TP` — true positive (right symbol, right location)
- `FP` — false positive (wrong symbol or hallucinated)
- `WRONG_PITCH` — notehead at the right location but the pitch field is wrong
- `unsure` — leave for human review

Add an optional 1-word reason after the verdict, e.g. `TP` or `FP barline-mistake`.

- [ ] D0  noteheadBlack (notehead) at (x=79, y=389) → E4  conf=0.86
       verdict: __________
- [ ] D1  noteheadBlack (notehead) at (x=80, y=316) → A4  conf=0.79
       verdict: __________
- [ ] D2  noteheadBlack (notehead) at (x=312, y=291) → B4  conf=0.88
       verdict: __________
- [ ] D3  noteheadBlack (notehead) at (x=579, y=414) → D4  conf=0.82
       verdict: __________
- [ ] D4  noteheadBlack (notehead) at (x=580, y=267) → C5  conf=0.80
       verdict: __________
- [ ] D5  noteheadBlack (notehead) at (x=916, y=243) → D5  conf=0.87
       verdict: __________
- [ ] D6  noteheadBlack (notehead) at (x=1000, y=269) → C5  conf=0.75
       verdict: __________
- [ ] D7  noteheadBlack (notehead) at (x=1093, y=414) → D4  conf=0.82
       verdict: __________
- [ ] D8  noteheadBlack (notehead) at (x=1094, y=291) → B4  conf=0.87
       verdict: __________
- [ ] D9  noteheadBlack (notehead) at (x=1225, y=315) → A4  conf=0.79
       verdict: __________
- [ ] D10  noteheadBlack (notehead) at (x=1337, y=340) → G4  conf=0.87
       verdict: __________
- [ ] D11  noteheadBlack (notehead) at (x=1338, y=219) → E5  conf=0.79
       verdict: __________
- [ ] D12  noteheadBlack (notehead) at (x=1470, y=365) → F4  conf=0.79
       verdict: __________
- [ ] D13  noteheadBlack (notehead) at (x=1587, y=389) → E4  conf=0.86
       verdict: __________
- [ ] D14  noteheadBlack (notehead) at (x=1588, y=316) → A4  conf=0.80
       verdict: __________
- [ ] D15  noteheadBlack (notehead) at (x=1714, y=340) → G4  conf=0.87
       verdict: __________
- [ ] D16  noteheadBlack (notehead) at (x=1832, y=243) → D5  conf=0.87
       verdict: __________
- [ ] D17  noteheadBlack (notehead) at (x=1835, y=364) → F4  conf=0.77
       verdict: __________
- [ ] D18  noteheadBlack (notehead) at (x=1958, y=317) → A4  conf=0.79
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
