# Slurs across a SYSTEM break — and the fixture that had to exist first

**2026-09-01**, following `SLURS_2026-09-01.md`. That change made a slur able to
cross a BARLINE. The stitching merge then made a part the same staff on every
system, which makes a slur crossing a **system break** expressible for the first
time — and nothing measured it, because nothing could.

**Result on the new fixture: OMR-NED 0.2416 → 0.2381, edits 86 → 85,
`wrong slur` 7 → 6.** The orchestral benchmark is **byte-identical** and stays at
pooled **0.2209**.

---

## The case was invisible, not rare

Every fixture in this repository is ONE system:

- `orchestral_eval` shrinks each excerpt until it fits a single page, and a
  conductor's page of 18–38 staves holds exactly one system.
- `end_to_end_eval`'s three authored fixtures are 4–6 bars, one system each.

So a slur across a system break could not be scored, seen, or regressed against.
The first job was therefore not the fix but a **fixture**: `build_systems` in
`tools/omr/training/e2e_fixtures.py` — four staves over eight bars, laid out as
two systems of four bars, with slurs placed on either side of the break.

Two things about that fixture were learned the hard way, and both are now
asserted in `test_e2e_fixtures.py` so they cannot rot:

**1. It needs a `StaffGroup` with barlines run through it.** Without one,
LilyPond draws each staff its own barlines that stop at its own five lines.
`staff_detector` decides what belongs to one system by CONNECTIVITY — a column
of ink through the gap vetoes a break — so with nothing bridging the gaps the
second system came back as **four one-staff systems**. `_stitch_slots` refuses
to join systems of unequal size, so the stitched path never engaged and the
fixture tested nothing while appearing to work.

**2. Slurring every barline made the fixture measure rhythm instead of slurs.**
The first cut slurred all seven barlines of the top part, so that a slur crossed
the break wherever LilyPond chose to put it — a design meant to avoid predicting
the layout. It backfired. With an arc over every barline the bars stopped summing
to four:

```
part 0 bar sums:  6.00  5.00  6.00  2.00  4.00  3.50  4.00  4.00   (truth: 4.00)
```

`line_detection` reads a beam as ink that stems run into, and a slur drawn
between two noteheads looks like one — the hazard `test_line_detection_beams`
already names. Four quarter notes came back as four eighths.

That confound lands **squarely on the thing under test**, because
`musicdiff` prices a slur by the DURATION it spans. The system-break slur was
recovered onto exactly the right notes — `G5 → F5`, matching the truth — and was
still charged as an invention, because our span was `dur=1.5` against a truth of
`dur=2.0`:

```
extradel   pred='dur=1.5'   truth=None
```

So the metric went the wrong way (0.3000 → 0.3017) on a change that was working.
**A fixture that is hard for an unrelated part of the pipeline cannot measure the
part you care about.** The notes either side of the break are now HALF notes,
unbeamable by construction, and every bar sums to four.

## The junction geometry is not the barline's

| | barline | system break |
|---|--:|--:|
| the arc that ENDS, distance to its cell's right edge | 0.00–0.10 sp | **0.10 sp** |
| the arc that RESUMES, distance to its cell's left edge | 0.00–0.10 sp | **5.28 sp** |

The resuming half does not touch the cell edge, because that cell opens with a
**clef and a key signature**. A constant for that distance would be a constant
for how wide a clef is, and would be wrong on any score with more accidentals.

So the resuming half is anchored on the **first note** instead — what it actually
attaches to, and independent of the header's width. The discriminator is which
side of that note the ink is on:

- a **resuming** fragment runs in from the margin and ENDS on the first note
  (measured: arc `x[400,503]`, first notehead centred at `504`);
- a slur that merely **begins** on the first note runs the other way, from the
  note rightwards.

That is a categorical test, not a threshold. The height test is the existing
continuation tolerance applied to a height **relative to each staff's own top
line** — absolute page y is meaningless across a break, where the two staves are
a whole system apart. Measured on the recovered pair: `-1.07` against `-1.29`
staff spaces, both above their staves, 0.22 apart.

## What it recovers, and what limits it

Of the two authored break-crossing slurs, **one is recovered**. The second fails
for a reason outside this layer: its OUT arc is detected (right-gap 0.10 sp) and
**no resuming arc is detected at all** on the far side. The layer recovers what
the detector gives it.

```
slot 0   OUT right-gap 0.10 sp   IN left-gap 5.28 sp    -> joined
slot 1   OUT right-gap 0.10 sp   (no IN arc detected)   -> abstains
```

## Containment

- **The orchestral benchmark is byte-identical** on all three works, and stays
  at pooled 0.2209. `_stitch_slots` returns None for a single-system page, so
  the slot pass is never reached with more than one staff and the new junction
  logic cannot fire.
- **LilyPond never gets a cross-system slur**, and must not: `to_lilypond` emits
  one `\new Staff` per system-staff and a LilyPond slur cannot span two Staff
  contexts, so such a slur would be unpaired. `_lily_staff_block` passes a
  single staff, which is the one-system case by construction. Output compiles;
  parens balanced.
- A staff with no five-line geometry **ends the chain without discarding the
  rest** — the slot is paired in contiguous runs, so one unmeasurable system
  does not cost the slurs on the others.

## The fixture is deterministic; its PDF bytes are not

Rendered twice, the truth's music hashes identically (14 slurs, 73 notes) and
the rasterised page is **pixel-identical** — same SHA at 300 dpi, same file size
— but the PDF BYTES differ, because LilyPond stamps a creation date into them.
So `diff` on the PDFs is not a determinism check and will always report a
difference; rasterise and compare pixels instead. Same pixels in, same
transcription out, which is all the benchmark needs.

## Reproducing

```bash
python3 -m tools.omr.training.e2e_fixtures --out-dir benchmarks/omr-end-to-end/fixtures
python3 -m tools.omr.training.orchestral_eval --omr-ned     # must stay 0.2209
```

The fixture's own A/B was run by exporting one cached transcription twice, with
and without the change, so only `export.py` differed between arms.
