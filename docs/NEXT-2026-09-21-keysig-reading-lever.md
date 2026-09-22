# NEXT SESSION — measure the key-signature READING lever

> # ⚠️⚠️ DONE, 2026-09-21 — AND **DO NOT RE-RUN IT**
>
> **This brief was executed. Its answer is NO, and its central premise was
> FALSE.** Findings, with every number:
> [benchmarks/omr-keysig-marker-fit-2026-09/FINDINGS.md](../benchmarks/omr-keysig-marker-fit-2026-09/FINDINGS.md).
> CLAUDE.md carries the summary under *"The marker slot-fit: the lever was
> ALREADY SHIPPED on the legacy path"*.
>
> **THE PREMISE.** §"The proposition is different" below says
> `fit_key_signature` *"has never been given the detector's markers as its ink
> source"*. **It has, since `7c6b6481`, 2026-08-28** — `transcribe.py:856`,
> through `_staff_positions_for` and a `_DETECTOR_FIT_CONFIG` written for that
> ink. ⚠️ And **this document contradicts itself**: its own TRAP section says
> the legacy path *"falls back to counting them where **the slot fit
> abstains**"*, which presupposes the fit. So the job was never "same reader,
> different ink" — it is a **PORT of a shipped LEGACY reader**, the sixth
> instance of the symbol sweep's §2a family.
>
> **WHAT IT MEASURED.** Reach 6 and 10 of the 10-and-10 below (four Litolff
> staves have no notehead in cell 0, hence no unit, hence abstain). The fit
> ANSWERS 2 and 3. Scored on Litolff — the only document with print truth —
> **right 1, wrong 1, abstained 4, against a NULL of 6/6**. ⚠️ And the
> reachable population is **biased toward where the constant wins**: all 6 are
> truth −3, where the full 26 are `{-3: 17, 0: 8, -1: 1}`.
>
> **WHY IT IS REFUSED, AND IT IS NOT THE SCORE.** The reader is correct on both
> plates. **The INK is not ready**, and the two publishers fail differently:
> Litolff's markers are CENTRED and NOISY (median −0.100, spread 5.66);
> Breitkopf's are TIGHT and DISPLACED (median **−1.256** against
> `max_offset = 1.25` — the cap sits ON its bias). **The obvious cause is
> REFUTED**: a glyph-shape bias would be identical on both plates and the two
> want different reference points.
>
> **THE ONE THING STILL WORTH DOING** is §4 of the findings: a **SHARP-KEY
> document**, which would say whether the Breitkopf displacement is the flat
> glyph or the detector's box. Both documents here are C minor, so the
> discriminator is unavailable. `data/dossiers/*.json` say which works qualify,
> and answering it needs no weights.
>
> ⚠️ **A LIVE GAP THIS FOUND AND DID NOT FIX**: `_cell_grid` returns
> `(top_y, half_step)` and `Q.CELL_STAFF_SPACE` files `half_step` and **DROPS
> `top_y`** — 0 of 40,878 rows carry the cell's top line in the cell frame,
> which is verbatim the consumer that function's own docstring says had
> *"nothing to ask with"*. Named and half-fixed.
>
> **Everything below is the brief AS WRITTEN and is kept unedited**, because a
> superseded work order with its correction beside it is worth more than a gap.
> Read it as history, not as a task.

---

**Written 2026-09-21, low on context, handing off one measurement.** Branch
`claude/part-instrument-check-2026-09`, tree clean at `9b4d0551`, everything
below is committed.

---

## The one thing to do

**Run the slot-table fit on the DETECTOR's key markers, and score it against
the hand-read print truth.** Reach first, accuracy second.

## Why this and not the other thing

Two levers were on the table this morning. **The first is now REFUSED and must
not be re-run** — `benchmarks/omr-keysig-carry-2026-09/FINDINGS.md`: the
cross-system carry fails because a part does not agree with itself (6 of 7
parts on Litolff, 11 of 14 on Breitkopf), and on the staves it does reach it
does not out-predict writing "3 flats" blindly. **That recommendation was made
and withdrawn the same day.** Do not spend a session re-measuring it.

This is the other one. `adjudicate_key_signature` abstains on staves where the
DETECTOR found key accidentals the CV fitter could not use:

| | abstaining staves | **of those, carrying detector markers** |
|---|--:|--:|
| Litolff Beethoven 5 pp.1-4 | 26 | **12** |
| Breitkopf Brahms 1 pp.0-3 | 21 | **10** |

⚠️ **Not all 12 are reachable**: a slot fit needs a CLEF to choose the table,
so the 2 Litolff staves abstaining `needs_clef` are out. **Reach is 10 and
10**, and confirming that is step one.

## ⚠️⚠️ THE TRAP: COUNTING THE MARKERS IS ALREADY MEASURED AND REFUTED

Do not count them. `_marker_ink`'s docstring has the numbers: the legacy path
counts markers where the fit abstains and it cost **7 spurious key flips, all
7 wrong**; and on staves this pipeline DECIDES, the marker count equals the
settled `|fifths|` on only **19 of 49 (39%)** and **39 of 76 (51%)**.

**The proposition is different and that is the whole point.** A marker carries
a POSITION, and this project's paid-for method reads key signatures by fitting
positions to the slot table for (clef, N) — which *recovers* a missed
accidental instead of miscounting it. `key_signature_geometry.fit_key_signature`
is that reader, and it has never been given the detector's markers as its ink
source; it is fed the CV locator's ink only.

So: **same reader, different ink.**

## The pieces, all present

| what | where |
|---|---|
| the reader | `fit_key_signature(observed, clef, accidental, config)` — `observed` is staff positions **in steps below the top staff line, in x-order**; returns `None` when nothing fits, which is the abstention you want |
| the ink | `Q.KEYSIG_MARKER` rows, carrying `x` (canonical) and `y_center`, plus the class (`keySharp`/`keyFlat`/`keyNatural`) |
| the clef | `Q.CLEF` verdict on the same staff |
| the truth | `benchmarks/omr-keysig-truth-2026-09/truth.json` — per INSTRUMENT, joined by each system's `lineup` at the staff index. **Alignment verified exact: 12/11/11/11/8/11/11 on both sides** |
| worked examples of all of the above | `benchmarks/omr-keysig-carry-2026-09/reconcile_arm.py` |

## ⚠️ The likely place to go wrong: the UNIT

`fit_key_signature` wants **staff steps below the top line**. The markers carry
`y_center` in the CELL's canonical pixels. Converting needs that cell's own
staff geometry — `Q.CELL_STAFF_SPACE` exists for exactly this, and
`A-DUR-8`'s record is the warning: `Q.STAFF_SPACING` is the PAGE's and a cell's
boxes are canonical, and **184 of 368 cells read 100 px while the rest read
38.5-56**. A wrong unit here produces a confident wrong fit, not an error.
**Where no unit exists, abstain** — that is the precedent.

## The controls that must run

1. **NULL.** Of Litolff's 26 abstaining staves the truth is `{-3: 17, 0: 8,
   -1: 1}`, so writing **"3 flats" on every one scores 17** against today's 8.
   Any reader that gains less than that on the same population is not obviously
   better than a constant — say so out loud, as the carry arm had to.
2. **FILE vs READING.** An abstention exports no `<key>`, which reads as *no
   accidentals* — so on the horns, trumpets and timpani (8 staves here,
   truth 0) abstaining is **accidentally right**, and a reader that writes
   −3 onto one makes the file WORSE. Score both columns.
3. **OVERLAP with the template.** `Q.KEYSIG_TEMPLATE_FIT` already answers GAPS
   ONLY and decides 28 of 75. Check how many of the 10 it already serves before
   claiming them — reach that is already covered is not reach.

## What would falsify it

If the fit abstains on most of the 10 (too few markers, or positions that fit
no slot table), the lever is small and should be reported as small. **A clean
"it reaches 3 of 10" is a good result and ends the thread honestly.**

## Not established, standing

n = 2 documents, 2 publishers, 8 pages, both scans. The Breitkopf truth is an
ENCODING (a dossier), not the page — usable to show a value is impossible,
never to score accuracy. No export, no file, no OMR-NED.
