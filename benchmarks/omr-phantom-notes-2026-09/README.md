# omr-phantom-notes-2026-09 — a pitched note where the page prints silence

Sean's observation 3 on the first cleanup artefact, opened 2026-09-14.
**Read [FINDINGS.md](FINDINGS.md).** No code outside this directory changed.

⚠️⚠️ **THEN READ
[FINDINGS_2026-09-15_STALENESS.md](FINDINGS_2026-09-15_STALENESS.md), WHICH
CORRECTS FINDINGS §4's ATTRIBUTION AND CLOSES ITS §7.1.** The dedupe repair
**cannot reach 11 of the 13 offending bars (20 of the 25 notes)** — they hold
no cross-staff contest — so the artefact is not stale for them and the padding
half does not live in `Q.GLYPH_OWNER`. Run `probe/contest_join.py --check`.

⚠️ **Every probe here reads COMMITTED ARTEFACTS ONLY** — the cleanup artefact's
MusicXML, its system map, and the seven printed-system PNGs embedded in its
side-by-side HTML. None of them needs `omr-weights/`, `library/`, or the staged
record, and none of them can re-gather or re-export.

## The order to run them in

```bash
cd benchmarks/omr-phantom-notes-2026-09

# 0. the print, out of the committed side-by-side artefact (7 system crops)
python3 probe/extract_crops.py --out /tmp/crops

# 1. the population, as the handoff defines it (OUR OUTPUT)
python3 probe/population.py

# 2. that population put back on the printed staff it came off
python3 probe/locate.py

# 3. where each lone note stands on its staff, against the file's own null
python3 probe/steps.py

# 4. what the PRINT holds in those bars  (the census)
python3 probe/print_ink.py --crop /tmp/crops/crop00.png --page 4 --system 0

# 5. THE DECIDING ONE: bars the PRINT shows as silent, and what we wrote there
python3 probe/silent_bars.py --crop /tmp/crops/crop00.png --page 4 --system 0
python3 probe/silent_bars.py --crop /tmp/crops/crop04.png --page 3 --system 0 \
        --bl-frac 0.45
```

`out/` holds the recorded output of each, so the numbers in FINDINGS.md can be
diffed rather than re-derived.

## Which crop is which printed system

The seven PNGs come out of the HTML in the order the side-by-side ranks them,
which is NOT page order. `extract_crops.py` prints each section's heading, and
they map:

| crop | page / system | staves | bars |
|---|---|--:|--:|
| `crop00` | p4 / s0 | 11 | 15 |
| `crop02` | p4 / s1 | 11 | 15 |
| `crop04` | p3 / s0 | 11 | 16 |
| `crop06` | p2 / s1 | 11 | 15 |
| `crop08` | p2 / s0 | 11 | 16 |
| `crop10` | p1 / s0 | 12 | 16 |
| `crop12` | p3 / s1 | 8 | 18 |

⚠️ **Only `crop00` and `crop04` are usable.** `silent_bars.py` REFUSES a crop
whose own staff and barline grids disagree with the exporter's system map,
because a bar index read off a disagreeing grid names the wrong bar — which is
worse than no crop at all. The other five are refused at every barline
threshold swept (0.40 … 0.80) and are reported, not measured.

## Two helpers worth knowing about

* `probe/bar_crop.py` cuts one printed bar of one printed staff to a PNG, so a
  claim about the print can be looked at. `--expect <n>` makes it refuse when
  the grid disagrees.
* `probe/staff_rows.py` finds the five-line staves by ink row profile and groups
  them **by the gap between staves**, not greedily — see its docstring for why
  the greedy version silently renumbered every staff below a faint line.
