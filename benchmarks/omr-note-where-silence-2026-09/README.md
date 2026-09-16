# A pitched note where the page prints silence

Sean's one unanswered observation from the first cleanup artefact
(2026-09-11), taken to the ink.

> *"in bars where it should be just whole note rest in two four. It's showing
> an actual quarter note, not a quarter note rest."*

Read [FINDINGS.md](FINDINGS.md). The short version is that the brief's
hypothesis is **true of one bar in five and false of the rest**, and the
correction is worth more than the repair.

## What is here

| file | what it is |
|---|---|
| `FINDINGS.md` | the reading, the cause, the reach, and what is NOT established |
| `adjudicated-26.json` | ⚠️ **the hand verdict on all 26 bars**, one row per crop looked at |
| `arm.py` | the A/B: one gather, adjudicated twice, exported twice |
| `probe/population.py` | the population, from the exported FILE alone |
| `probe/cache.py` | the 132 MB record squeezed to the quantities this job reads |
| `probe/trace.py` | each lone note back to its own ink, against the page's own distributions |
| `probe/crops.py` | render the page and crop a suspect's bar, with a staff ruler |
| `probe/strip.py` | ⚠️ **one printed staff end to end**, labelled with what we exported |
| `probe/sheet.py` | a contact sheet, with `restWhole` and notehead controls on it |
| `probe/reach.py` | how far the fault reaches, and which witnesses separate it |
| `probe/fires.py` | every glyph a candidate rule would fire on, for adjudication |
| `probe/sweep.py` | is each cut on a plateau, or holding the answer up |

## Running it

Nothing here needs weights or a fresh gather. Everything reads the shared
record and the edition PDF, both machine-local:

```bash
R=library/_shared-records/beethoven5-p1-p4.record.json    # md5 d3620ba9...
P=library/editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf

python3 benchmarks/omr-cleanup-count-2026-09/export_arm.py --record $R --tag base --out-dir out
python3 benchmarks/omr-note-where-silence-2026-09/probe/population.py \
    --xml out/beethoven5-mvt1-base.musicxml --map out/system-map-base.json --json out/lone.json
python3 benchmarks/omr-note-where-silence-2026-09/probe/cache.py --record $R --out out/cache.json
python3 benchmarks/omr-note-where-silence-2026-09/probe/trace.py \
    --cache out/cache.json --lone out/lone.json --json out/trace.json
python3 benchmarks/omr-note-where-silence-2026-09/probe/sheet.py \
    --cache out/cache.json --trace out/trace.json --pdf $P --out out/sheet.png \
    --quarters-only --controls 5 --scale 34
python3 benchmarks/omr-note-where-silence-2026-09/arm.py $R --out-dir out/arm
```

⚠️ **`library/` is gitignored and lives in the MAIN checkout**, so from a
worktree every path above needs to be absolute. `crops.py` and `strip.py` take
`--pdf` for exactly that reason.

⚠️ **Every probe prints a positive control before any filtered figure**, and
exits non-zero where it measured nothing. The manager's own first probe of this
question returned `n=0` on both arms because it guessed the record's schema —
a dead instrument wearing a clean zero.
