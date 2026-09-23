# The notehead funnel — Litolff Beethoven 5, pdf page 3, Viola

**Roadmap:** START HERE, next action 2. **Date:** 2026-09-23. **Path:** STAGED.
**Status:** measured, read-only — nothing under `tools/` was changed.

## The question

Sean, looking at the Litolff count page (Beethoven 5 mvt 1, imslp984073, pdf
page index 3), Viola, **system 1** (the upper system, printed bars 49–64):

> *"there are a lot of notes on the original scan and almost nothing shows up
> on our version"*

He named three possibilities. This directory answers which one it is, with a
count for each, and prices the same funnel over the whole page so the Viola
answer is not mistaken for the page's answer.

## The answer, in one sentence

**It is the middle one, and it is nearly all of it: the detector boxed 48
noteheads on that staff and the exporter wrote 0 of them — 40 refused
`no_pitch` (this staff's `clef` ABSTAINED, `no_candidates`, so
`consequences.restate_pitch` produced no pitch for it at all), 3 refused
`owned_by_another_staff`, 3 `not_a_notehead:clipped_fragment`, 1
`not_a_notehead:too_narrow`, 1 `ink_is_a_whole_rest`; at most 2 of the
reference's 31 heads have no detector box at all (per-bar bound), and 0 heads
were given to another staff and written there.**

## Where the numbers came from

| what | command (from the worktree root) |
|---|---|
| the funnel + the export's own refusals | `python3 benchmarks/omr-notehead-funnel-2026-09/probe/funnel.py --record library/_shared-records/beethoven5-litolff-mvt1-whole-20260923.record.json --page 3 --system 0 --staff 9 --ref-part Viola --ref-first 49 --ref-last 64 --musicxml <scratch>/beet5-litolff-whole.musicxml --out-json <scratch>/funnel.json` |
| the control, seen FAILING first | same, plus `--break-control` → exit 1, `owned_by_another_staff 932 != 933` |
| the neighbour question | `python3 benchmarks/omr-notehead-funnel-2026-09/probe/neighbours.py --record <as above> --funnel <scratch>/funnel.json --out-json <scratch>/neighbours.json` |
| the tables below | `python3 benchmarks/omr-notehead-funnel-2026-09/probe/tables.py --funnel <scratch>/funnel.json` |
| the crop | `python3 benchmarks/omr-notehead-funnel-2026-09/probe/crop_funnel.py --funnel <scratch>/funnel.json --record <as above> --pdf library/editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf --first-cell 0 --last-cell 7 --staff-name Viola` |

**The refusal buckets are not restated here.** `export._place_notes` holds the
rule; `funnel.py` INSTRUMENTS it (wrapping `_parse_subject` and `_place_notes`
at runtime, no edit to `tools/`) so that the same `_drop` event is filed under
its staff and its cell as well as its system. The repo has paid for the other
choice once already: `omr-cleanup-count-2026-09/build_sheet.py` kept its own
copy of "the three refusals" and reported 542 where the exporter refused 738.

**The control, and it can fail (rule 7).** The per-subject log is summed back
up and compared to the exporter's own `notes_not_written` and
`notes_not_written_by_system`. `--break-control` drops one logged refusal on
purpose; the run then exits 1 naming the bucket that is off by one. It was run
that way first.

## Table 1 — the Viola staff, bar by bar

`staff/3/0/9`, printed bars 49–64. `ref heads` = sounding noteheads in
`library/reference/beethoven/symphony-5/beethoven--symphony-5--mvt1--gradus.mxl`,
part `Viola`, measures 49–64 (window and offset 0 from
`benchmarks/omr-scan-e2e-2026-09/works.json`, row `…984073-p3`, `confidence:
verified`). Chord members count as heads; there are no grace notes here.

| bar | ref heads | ink comps | all boxes | notehead boxes | R:too_narrow | R:clipped_fragment | R:ink_is_a_whole_rest | R:no_pitch | R:duration_narrowed | R:owned_by_another_staff | R:staff_not_identified | no verdict | WRITTEN |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 49 | 2 | 9 | 13 | 7 | 0 | 0 | 0 | 7 | 0 | 0 | 0 | 0 | 0 |
| 50 | 2 | 5 | 10 | 4 | 0 | 2 | 1 | 1 | 0 | 0 | 0 | 0 | 0 |
| 51 | 8 | 5 | 24 | 10 | 0 | 0 | 0 | 10 | 0 | 0 | 0 | 0 | 0 |
| 52 | 8 | 7 | 18 | 7 | 0 | 0 | 0 | 7 | 0 | 0 | 0 | 0 | 0 |
| 53 | 2 | 3 | 1 | 1 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 |
| 54 | 2 | 9 | 7 | 3 | 1 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 |
| 55 | 2 | 10 | 9 | 7 | 0 | 0 | 0 | 5 | 0 | 2 | 0 | 0 | 0 |
| 56 | 2 | 6 | 7 | 4 | 0 | 0 | 0 | 3 | 0 | 1 | 0 | 0 | 0 |
| 57 | 0 | 3 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 58 | 1 | 5 | 5 | 2 | 0 | 1 | 0 | 1 | 0 | 0 | 0 | 0 | 0 |
| 59 | 0 | 2 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 60 | 0 | 3 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 61 | 0 | 3 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 62 | 0 | 4 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 63 | 1 | 4 | 6 | 1 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 |
| 64 | 1 | 4 | 4 | 2 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 |
| **total** | **31** | **82** | **121** | **48** | **1** | **3** | **1** | **40** | **0** | **3** | **0** | **0** | **0** |

Balance: notehead boxes 48 = written 0 + refused 48 + no verdict 0 -> **True**


### Table 2 — every staff on pdf page 3


**The buckets are ordered, and that matters.** `_place_notes` tests in this
order: not-a-notehead (2.4a) → `ink_is_a_whole_rest` → `no_pitch` →
`duration_*` → `owned_by_another_staff` → `staff_not_identified`. A head is
counted under the FIRST test it fails. So the Viola's three NARROWED duration
verdicts (bar 51) show as `no_pitch`, not as `duration_narrowed`: the clef
abstention hides everything downstream of it.

**`ink comps` is a per-cell summary, not one row per component.** This record
was gathered with `ink_rows: False` (see `provenance.settings.args`), so
`Q.INK` is filed once per CELL carrying `detail.ink_n_components`. That number
is the population beneath the detector for the bar; it is not a set of
subjects this funnel can follow individually.

## Table 2 — the same funnel, every staff on the page

So the Viola answer is not mistaken for the page's answer. System 0 = printed
bars 49–64 (11 printed staves), system 1 = printed bars 65–82 (8 printed
staves — Oboi, Trombe and Timpani are suppressed at the system break).

| staff | part as printed | clef | ink comps | notehead boxes | R:too_narrow | R:clipped_fragment | R:ink_is_a_whole_rest | R:no_pitch | R:duration_narrowed | R:owned_by_another_staff | R:staff_not_identified | WRITTEN |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 3/0/0 | Flauti | treble | 116 | 24 | 1 | 0 | 1 | 0 | 7 | 0 | 0 | 15 |
| 3/0/1 | Oboi | treble | 97 | 25 | 0 | 5 | 0 | 0 | 7 | 0 | 0 | 13 |
| 3/0/2 | Clarinetti | treble | 110 | 17 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 9 |
| 3/0/3 | Fagotti | bass | 120 | 21 | 0 | 1 | 0 | 0 | 5 | 0 | 0 | 15 |
| 3/0/4 | Corni | treble | 112 | 29 | 0 | 0 | 0 | 0 | 7 | 0 | 0 | 22 |
| 3/0/5 | Trombe | treble | 92 | 15 | 0 | 0 | 1 | 0 | 4 | 0 | 0 | 10 |
| 3/0/6 | Timpani | bass | 87 | 20 | 0 | 5 | 1 | 0 | 1 | 3 | 0 | 10 |
| 3/0/7 | Violino I | treble | 82 | 43 | 1 | 0 | 0 | 0 | 6 | 0 | 0 | 36 |
| 3/0/8 | Violino II | treble | 104 | 43 | 0 | 0 | 0 | 0 | 5 | 2 | 0 | 36 |
| 3/0/9 | Viola | ABSTAINED (no_candidates) | 82 | 48 | 1 | 3 | 1 | 40 | 0 | 3 | 0 | 0 |
| 3/0/10 | Vc e Basso | bass | 76 | 20 | 2 | 1 | 0 | 0 | 3 | 2 | 0 | 12 |
| 3/1/0 | Flauti | treble | 95 | 10 | 0 | 0 | 1 | 0 | 1 | 0 | 0 | 8 |
| 3/1/1 | Clarinetti | treble | 89 | 11 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 9 |
| 3/1/2 | Fagotti | bass | 80 | 32 | 0 | 0 | 0 | 0 | 7 | 0 | 0 | 25 |
| 3/1/3 | Corni | treble | 89 | 13 | 0 | 0 | 0 | 0 | 6 | 0 | 0 | 7 |
| 3/1/4 | Violino I | treble | 107 | 28 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 26 |
| 3/1/5 | Violino II | treble | 82 | 27 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 26 |
| 3/1/6 | Viola | alto | 83 | 27 | 0 | 0 | 0 | 0 | 3 | 0 | 0 | 24 |
| 3/1/7 | Vc e Basso | bass | 77 | 21 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 20 |
| **system 0** | | | **1078** | **305** | **5** | **15** | **4** | **40** | **53** | **10** | **0** | **178** |
| **system 1** | | | **702** | **169** | **1** | **2** | **1** | **0** | **20** | **0** | **0** | **145** |
| **PAGE** | | | **1780** | **474** | **6** | **17** | **5** | **40** | **73** | **10** | **0** | **323** |

Balance: page notehead boxes 474 = written 323 + refused 151 -> **True**

`staff/3/0/9` is **the only staff on the page with a single `no_pitch`
refusal, and the only staff on the page that writes nothing.** It also carries
**more notehead boxes than any other staff on the page (48)** — more than
Violino I (43) and Violino II (43). The detector is not the bottleneck here.

The same part one system down, `staff/3/1/6`, reads its alto clef and writes
24 of 27 boxes. Those 24 are exactly the 24 Viola heads the file holds over
this page (see *the off-by-one* below).

## The three possibilities, priced

| Sean's possibility | count, Viola, printed bars 49–64 |
|---|---|
| heads the detector never boxed | **at most 2** of the reference's 31 (per-bar bound: Σ max(0, ref − boxes) over bars = 1 at bar 52 + 1 at bar 53; every other sounding bar has at least as many boxes as the reference has heads) |
| heads boxed and then refused | **48 of 48** — `no_pitch` 40, `owned_by_another_staff` 3, `clipped_fragment` 3, `too_narrow` 1, `ink_is_a_whole_rest` 1 |
| heads given to another staff | **0 written elsewhere.** 3 noteheads in the Viola's cells are owned by Violino II (`staff/3/0/8`) and refused here; 2 noteheads in the Cello's cells are owned by the Viola and refused there; **0** heads written by any neighbour stand inside the Viola's own staff band (`y` 1768.5–1894.5 page px, its five `Q.STAFF_LINES` ± 2 spaces) |

The last row is the strongest form of the neighbour question, because it needs
no verdict at all: it asks the page where the written ink is, not the record
who it belongs to. `neighbours.py --out-json` holds all of it.

⚠️ The `at most 2` is an AGGREGATE bound, not a per-head match. Nobody
hand-labelled these 48 boxes against the plate; a bar can hold a box that is
not a head AND miss a head that is one and still balance. The crop below is
where that gets settled by eye.

## Why the clef abstained — the one decision this all hangs on

`staff/3/0/9`, page 3, system 0:

| row | outcome |
|---|---|
| `Q.CLEF_GLYPH` | **abstained, `no_detections`** — the detector drew no clef-category box on this staff at all |
| `Q.CLEF_LOCATED` (CV locator, ×2) | **abstained, `occupied`** (`locator_branch: occupied`, one cluster 2.09 × 4.5 spaces / 3.36 × 4.5 spaces) |
| `keysig_clef_fit` | declined |
| `clef` verdict | **ABSTAINED, `no_candidates`**, 5 rows considered, 0 used |
| `key_signature` verdict | ABSTAINED, `needs_clef` |
| `instrument` verdict | ABSTAINED, `no_evidence` (the staff prints no margin label) |
| `slot_index` verdict | DECIDED 9, `the_short_block_is_condensed_at_its_foot` — so the staff is NOT held out; `staff_not_identified` is 0 |

What the detector did instead is visible in the crop: at the clef's own x
(page px 388–416, y 1828–1862) it fired **two `noteheadBlackOnLine` boxes**
(`glyph/3/0/9/0/1` conf 0.64, `glyph/3/0/9/0/6` conf 0.36) — the alto C-clef,
merged into the staff lines by the plate, read as noteheads. That is the
Litolff MERGES failure mode in its purest form, and it costs a whole staff.

**Estimate, clearly labelled as one.** If the clef had been decided and
nothing else changed, 37 of the 48 would have been written (48 − 5 refused
before the pitch test − 3 whose duration is NARROWED − 3 owned by Violino II).
That is an upper bound on what a clef unlocks, not a claim that those 37
pitches would be right: `restate_pitch` is an EVALUATE consequence and
re-deriving it needs a re-adjudication, which this read-only lane did not run.

## The crop

`benchmarks/omr-notehead-funnel-2026-09/out/print/litolff-p3-s0-st9-viola-bars49-56.png`
(with its sidecar `.json`). Printed bars 49–56, cut from the PDF at the
gather's own DPI (600, read from the record's `provenance.settings.args.dpi`),
zoom 4.

* **frame control PASSED**, contrast 152.5 — reused from
  `omr-infer-duration-print-2026-09/probe/crop_inferred._frame_ok`, imported
  rather than copied. A page that failed would have been refused, not cropped
  with a caveat.
* GREEN horizontals = the five `Q.STAFF_LINES` the heads are FILED on, so the
  crop says which staff it is about (Sean's own correction of 2026-09-23:
  *"there is a staff at the top and a staff at the bottom - i dont know which
  staff the cell is focussing on"*).
* GREY verticals = the bars the record read, numbered **as printed**.
* **RED box = a detector notehead box (43 in this window). GREEN box = a head
  the exporter wrote (0).** Every red box with no green around it is a head
  that was found and then refused; a printed head with no red box at all is
  one the detector never drew.

## What is committed here

```
FINDINGS.md
probe/funnel.py       the funnel + the instrumented export refusals + the control
probe/neighbours.py   the cross-staff question, both directions + the geometric test
probe/tables.py       renders the two tables above (no number here is typed by hand)
probe/crop_funnel.py  the print crop, frame control imported not copied
out/funnel-litolff-p3-s0-st9.json       every number above, per cell and per staff
out/neighbours-litolff-p3-s0-st9.json
out/print/litolff-p3-s0-st9-viola-bars49-56.png (+ .json sidecar)
```

The record itself (314 MB) and the exported MusicXML stay out of the tree;
both are regenerated by the commands in the table at the top.

## Caveats, and what could not be established

1. **The record is from a DIRTY tree.** `provenance.dirty: true`, commit
   `dbc9962b`. Per §4b it is not a baseline. Every number here describes THIS
   record; re-gathering could move all of them.
2. **The file's bar numbers run one behind the print from bar 48 on.** Our
   `measure_partition` reads 15 bars on pdf page 2 system 1 where 16 are
   printed (the dropped barline `works.json` already documents on p.2), so
   page 3 system 0 is file measures **48–63** and system 1 is **64–81**. The
   "24 Viola heads over bars 49–82" figure is the same 24 heads, attributed
   one bar late. The bar numbers in Table 1 are PRINTED bars and are the ones
   to compare with the reference.
3. **Reference totals, for the record:** part `Viola`, printed bars 49–82 —
   49 heads, 5 bars empty; bars 49–64 — 31 heads, 5 bars empty (57, 59–62).
   Ours over the same window: 24 heads, 19 bars empty, **all 24 from system 1
   and none from system 0**. Decomposed: system 0 loses all 31 of its
   reference heads and contributes 16 of the 19 empty bars (11 of them
   "extra", i.e. bars the reference sounds); system 1 writes 24 against the
   reference's 18 — 6 MORE, which this lane did not investigate — and
   contributes the other 3 empty bars. So the net −25 heads is one staff
   losing 31 while its sibling system over-writes by 6.
4. **Per-head correspondence was not established.** No hand-labelling pass was
   run over the 48 boxes, so "the detector never boxed it" is bounded per bar,
   not counted per head.
5. **`status_census` is a partition over FAMILIES, not over heads.** It is
   balanced (14 families, `unaccounted` empty, `emitted` holds `note`), and it
   cannot see this fault at all: the `note` family emitted 7,878 notes
   document-wide, so a staff writing zero leaves no trace in it. The per-head
   accounting that does see it is `notes_not_written` / `notes_not_written_by_system`,
   which this probe decomposes.
6. **The derived checks are blind to this too**, by construction (§4d): none
   of them sees the DETECTOR, and the missing clef box is a detector fact.

## What this suggests (not done here — read-only lane)

* A clef that abstains silently deletes an entire staff's music while the
  bars, the durations, the stems and the ownership all read fine. The 40
  `no_pitch` refusals on this page are ALL one staff. A roadmap item that
  hunts for *a staff with boxes and zero written* would have surfaced this
  without anybody looking at the page.
* The same part reads `alto` one system down on the same plate. §10 says a
  clef is printed per system, so a per-system clef is correct — but a staff
  that abstains in one system and decides in another, in the same part of the
  same page, is a second witness that exists and is read by nothing.
