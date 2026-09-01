# A part is the same staff on every system (2026-08-31)

`export.to_musicxml` emitted one `<part>` per **(page, system, staff)**. A part
was therefore never continuous: two pages of a piano prelude came out as
twenty-four parts of three bars each rather than two parts of thirty-six.

It is the reason OMR-NED could not be read as a recognition score on anything
longer than one system — two thirds of its edits were whole-measure and
whole-staff inserts — and the reason `orchestral_eval` has a comment forbidding
excerpts that spill onto a second page: *"transcribing three pages of a 21-staff
score yields 63 parts, not 21 parts three times as long."* The benchmark was
shaped around the exporter's limitation.

## The join, and where it refuses

Staves are joined by **ordinal**: the second staff of one system is the second
staff of the next. That is sound only while every system agrees on how many
staves it has, so `_stitch_slots` returns None the moment they do not, and the
old per-system parts stand.

That refusal is not a corner case. Printed orchestral scores suppress tacet
staves — the two systems of Beethoven 5 scan p.3 hold **11 staves and 8** — and
joining those by position would graft the horn's music onto the trumpet's. A
fragmented row (the layout detector splitting one line into many one-measure
"staves") also refuses, because it is already handled by its own path.

So the exporter now produces a real score where it can prove the join, and says
so through the part names where it cannot.

## Measured

WTC I, Fugue 1, two pages, ten systems of two staves, against the Gradus
reference for the work:

| | per-system | stitched |
|---|---|---|
| parts emitted | **20** | **2** |
| measures per part | 3 | **27** |
| OMR-NED | 0.9819 | **0.8668** |
| dominant error | entire measure insert/delete | **wrong note** |

The reference has 27 measures, which is exactly what a part now holds. The
change in the *dominant error* is the point: the metric has stopped measuring
the exporter's part model and started measuring the reading. In the edit
breakdown, `entire staff insert/delete` falls from 39.0% to 26.3% and `wrong
note` rises from below the fold to 35.4% — the same recognition errors were
always there, buried under structural ones.

Two parts against the reference's four is a real remaining difference and not
one stitching can fix: Bach's four voices are printed on two staves, and
condensation is the same problem the dossier's part-to-staff join exists for.

Single-system pages are unaffected — Beethoven 5 p.1 scores identically, since
one system was already one part per staff.

## What this unblocks

`orchestral_eval` can stop capping its excerpts at one page. That cap was there
only because a part broke at every system boundary, and the note explaining it
should now be re-read rather than trusted.

## Reproducing

```bash
python3 -m pytest tools/omr/tests/test_export_part_stitching.py
```

The before/after above is two `to_musicxml` calls on one transcription, with
`_stitch_slots` monkeypatched to return None for the "per-system" column, scored
with `tools/omr/omr_ned.py` from branch
`claude/tech-advances-tools-review-4a43f9`.
