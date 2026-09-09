# Cross-staff simultaneity — the column through a system

**2026-09-09.** `Q.ONSET_COLUMN`, its adjudicator, and the frame change that
made it reachable at all.

Sean's question that started this line of work was *"how many other things are
we missing"*; the exploration doc it produced
([docs/exploration-what-is-on-the-page-2026-09-09.md](../../docs/exploration-what-is-on-the-page-2026-09-09.md))
put ONE thing at the top: a column through a system is an instant of music, a
21-staff system is 21 independent readings of one stretch of time, and it is
**the only large source of REDUNDANT evidence on a page**. Nothing read it.

---

## 1. Why it was unreachable, which is not the same as unimplemented

`Q.EVENT` (2026-09-09) decides *which glyphs of a bar sound together* and is
scoped `Kind.CELL` — one staff, one bar. Widening it to the system was not a
matter of changing a scope: **`Q.GLYPH_BOX` carried only a CANONICAL x.**

A measure cell is sliced and rescaled so the staff span is constant — that is
the whole point of the canonical frame, and it is why the detector sees a
scale-invariant input. It also means two staves' canonical frames **coincide by
construction**: agreeing there is not evidence of anything. `Q.EVENT` is right
to use it (it never crosses a staff); a column cannot.

This is the same fault CLAUDE.md already records for the dynamics, in both
directions: `hairpin_detection` works in page pixels per staff and its
attribution is right **by construction**, while the dynamic LETTERS go through
per-measure cells and lose 24% of themselves to the staff above.

So `gather_detections` now carries the PAGE box beside the canonical one —
`bbox_page_px`, `x_center_page`, `y_center_page` in the row's detail. ⚠️ A cell
that cannot supply one gets a `frame_note` and **no page fields**, never a
fallback to the canonical x: a glyph whose page position is unknown and one
measured at page x 1841 are different facts, and only the second may reach a
cross-staff consumer.

---

## 2. The decision

`adjudicate_onset_column` (`adjudicators/rhythm.py`), scope `Kind.SYSTEM`,
`Mode.ADDITIVE`.

- **It CONSUMES `Q.EVENT`; it does not re-cluster the glyphs.** Within-staff
  simultaneity is already decided per cell under a tolerance measured off that
  bar's own noteheads. Re-clustering here would answer one question twice and
  let the two answers disagree. (Pinned:
  `test_a_chord_reaches_the_column_as_ONE_event` — a chord is one point, not
  two witnesses, or a staff playing chords would look like the
  best-corroborated staff on the page.)
- **It records; it does not overturn.** `implicates=(Q.ONSET_COLUMN, Q.EVENT)`
  and nothing else: a misaligned event says *this staff read a different set of
  onsets*, which is `Q.EVENT`'s business one scope down, and says nothing about
  how long any of them are. It never touches a pitch or a duration.
- **The unit is staff spaces and the frame is the page**, both load-bearing.
  Pixels are a property of one scan's resolution. `Q.STAFF_SPACING` is in
  `wants` AND `composed_from` because the tolerance IS a staff-space count: a
  wrong spacing moves every column boundary on the system, and a consumer
  weighing the verdict has to be able to see where its unit came from.
- **Single-link chaining is refused.** A first cut walked neighbour to
  neighbour and merged onsets **323 px apart** on a dense bar. A column must
  stay within the tolerance of its OWN centre — the same discipline
  `_dedupe_cross_staff_detections` needed when one-winner-per-cluster chained
  distinct glyphs together.
- Four named abstentions: `single_staff`, `no_page_frame`, `nothing_to_align`,
  and the decided `columns_read`.

Constants: `ONSET_COLUMN_TOLERANCE_SPACES = 0.10`,
`ONSET_COLUMN_MIN_WITNESSES = 2`.

---

## 3. ⚠️⚠️ A BUG THAT WAS WRITTEN, SHIPPED INTO A MEASUREMENT, AND CAUGHT BY A NUMBER THAT WAS TOO GOOD

The first run on real ink reported **1,062 columns, 76.6% corroborated** — a
better result than the one that survives. It was wrong.

`Subject.glyph` counts **within its CELL**. Keying the page-x lookup on that
ordinal alone is correct at `Kind.CELL`, where `adjudicate_event` may do it,
and WRONG at `Kind.SYSTEM`: glyph 3 of staff 0 and glyph 3 of staff 9 are
different ink at the same ordinal, and one dict entry silently took the
other's x.

**The tell was not the corroboration rate, which looked plausible. It was the
residual: 699 of 814 corroborated columns had a spread of EXACTLY ZERO** —
fourteen staves agreeing to the float, which no scan does. Corrected:

| | before (bug) | after |
|---|--:|--:|
| columns | 1,062 | **1,483** |
| corroborated | 814 (0.766) | **739 (0.498)** |
| residual exactly 0 | **699** | 0 |

Pinned by `test_glyph_ORDINALS_that_collide_across_staves_are_NOT_one_column`,
and the guard was mutation-tested: restoring the ordinal key turns **four**
tests red.

**A plausible aggregate is not evidence that its parts are real.** The rate was
believable; the distribution underneath it was impossible.

---

## 4. Measured on real ink, against its own null

No weights in this container, so the page cannot be read here — the log is
built from the **committed** transcription (Brahms 1 / Breitkopf p1–p3, 83
staves, 10,523 detections) by `run_on_transcription.py`, which emits the four
quantities the two decisions need at the same subject addresses `gather` uses,
and then runs the **registered** decision through `adjudicate.run`. It is a
harness, not a second gatherer; nothing in the tree imports it.

**51 bars, 6 systems, 703 cells grouped by `Q.EVENT`, 0 abstentions.**

⚠️ **RE-RUN ON THE MERGED TREE AND IDENTICAL.** A concurrent session landed
`OMR_METER_FROM_BARS` in the same file (`adjudicators/rhythm.py`, +222 lines)
while this was measured; git merged the two without a conflict there, which is
not by itself evidence that they compose. Re-run after the merge the harness
reports **1,483 columns, 739 corroborated (0.498), 744 alone, median residual
0.0734** — every figure below to the unit.

### The null is a CIRCULAR SHIFT, and that makes it the stronger control

Each staff-bar's page x values are rotated by a random offset within that
bar's own span. This keeps **every within-staff interval and every chord
exactly as printed** and destroys the PHASE alone — so what it tests is
precisely the claim: that the staves agree about *where in the bar* the
instants are. A re-draw would destroy the within-staff spacing too, and
beating it would only show that music is not uniform noise.

| | real | null (5 seeds) | ratio |
|---|--:|--:|--:|
| columns needed for the same events | **1,483** | 2,409 (2,373–2,420) | **1.62×** |
| corroboration rate | **0.498** | 0.292 (0.282–0.303) | **1.71×** |
| events standing alone | **744** | 1,706 (1,653–1,738) | **2.29×** |
| median residual (staff spaces) | 0.0734 | 0.0704 | **1.00×** |

**The column COUNT is the finding.** The same 3,006 events, the same
within-staff spacing, only the phase changed — and the page needs **62% more
distinct instants** to describe it. Half the events that stand alone in the
null are corroborated in the print.

### ⚠️ The residual does NOT separate, and an earlier draft of this said it did

`median_residual_spaces` is 0.0734 real against 0.0704 null — no separation at
all. That is not surprising once stated: a column is BUILT to lie within the
tolerance, so its spread is bounded by construction in both arms.

The claim that it separated came from a different instrument — the
nearest-neighbour probe (`probe_nn.py`), which measures the distance from an
event to the nearest event in another staff, an unbounded quantity. **A figure
measured under one definition was carried into another**, which is the same
failure shape CLAUDE.md files as *fixed-then-kept-open-in-prose*: it was
written into `Q.ONSET_COLUMN`'s own docstring before this run corrected it.
Read the residual as a diagnostic (a real 0-to-the-float residual meant a bug),
never as evidence of alignment.

### ⚠️ It is density-dependent, and the verdict carries the density so a consumer can tell

Bands are **tertiles of the real arm's own distribution** (4.71 and 5.82 events
per staff space, summed over the system's 14 staves), applied unchanged to both
arms. ⚠️ A first cut used fixed cuts at 1 and 2 and put **all 51 bars in one
bucket**, reporting a split that did not exist — `events_per_space` is summed
over every staff, so on a conductor's page it is an order of magnitude above a
per-staff figure. Bands read off the data cannot be wrong about the data.

| band | bars | real | null | ratio |
|---|--:|--:|--:|--:|
| sparse | 16 | 0.437 | 0.212 | **2.06×** |
| mid | 18 | 0.510 | 0.251 | **2.03×** |
| dense | 17 | 0.530 | 0.348 | 1.52× |

The RATE rises with density and the INFORMATION falls — on a crowded bar
alignment is substantially available by chance. So `events_per_space` travels
on every bar of the verdict: **a consumer that reads corroboration without it
cannot tell evidence from crowding**, and would rank a 1.52× bar above a
2.06× one for having a higher number.

This is why the decision is `Mode.ADDITIVE` and not a gate. A rule that
re-grouped a staff's events to match its neighbours would, on a 26-staff page,
be enforcing density.

---

## 5. What this is worth, stated narrowly

- **n = 1 document, 1 publisher, 3 pages.** Brahms 1 / Breitkopf is the one
  work fully reproducible in a cloud container from committed files alone
  (CLAUDE.md, cloud-session capabilities). One row is not a gate.
- **Nothing consumes the verdict yet.** It is on the record and reported; no
  export, no other decision and no metric reads it. That is deliberate — the
  measurement above says what a consumer would have to respect (density) and
  what it must not read (the residual).
- **It is not evidence about pitch, duration or meter**, and `implicates` says
  so. What it establishes is that the staves of a printed system agree about
  where the instants are **far more than their own rhythm alone accounts for**,
  which is the precondition for using them as redundant readings of one moment.
- The obvious next consumer is the one the exploration doc named: a staff
  standing ALONE at an x that every one of its 13 neighbours skips is the staff
  to look at — 744 such events here, against 1,706 in the null. Ranking them by
  the bar's own density is the first thing such a consumer must do.

## 6. Reproduce

```bash
PYTHONPATH=. python3 benchmarks/omr-onset-columns-2026-09/run_on_transcription.py \
    benchmarks/omr-labeling-hollow2-2026-09-breitkopf-brahms1/transcription.json
PYTHONPATH=. python3 benchmarks/omr-onset-columns-2026-09/compare_null.py \
    benchmarks/omr-labeling-hollow2-2026-09-breitkopf-brahms1/transcription.json \
    --json-out benchmarks/omr-onset-columns-2026-09/out/real-vs-null.json
PYTHONPATH=. python3 -m pytest tools/omr/tests/test_staged_onset_column.py -q
```

`probe_columns.py`, `probe_nn.py` and `probe_density.py` are the exploratory
first look that preceded the decision. ⚠️ **Their figures are NOT this
decision's** — they measure nearest-neighbour distance under fixed tolerances,
not the columns the adjudicator builds — and §4 above corrects a claim of
theirs that was carried across.
