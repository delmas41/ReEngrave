# 2.283 — Audit: what works against read once, claim once (2026-11-09)

STAGED path. Audit only: no pipeline code changed. Branch `lane-2.283-claim-audit` (f85dd183b). The lane's Write tool
refused this file; the manager wrote it from the lane report.

Sean (2026-11-09): "I feel like a lot of these tests are not interacting with ink that has been claimed. Is that a test issue or
a pipeline wiring issue?" / "we probably need a deeper audit of the pipeline and code to see what is working against our read
once, claim once plan. Why did we say arc ink should be reread or not claimed? That doesn't make sense."

## Cause and process lesson

The claim idea is sound, but it is held at the wrong GRAIN and read by too few readers.

- **Grain.** A claim is a whole per-cell connected stroke, resolved once per padded cell (`stroke_owner.adjudicate_stroke_owner`).
  `arc_claim.claim_strokes` claims a stroke when at least 0.5 of its ink lies on the trace. A mark's ink is pixels, and the page
  is one. 17–19% of per-cell stroke ink is the same page ink seen in two cells. Every exception (`MARK_ONLY`,
  `CONSULTED_ELSEWHERE`, the "owns a stroke of its own family" escape) compensates for that grain.
- **Coverage.** Only the notehead, ledger, accidental, rest and arpeggiato boxes (plus the keysig marker) consult the claim, and
  they do it through three mechanisms (`claimed_by.consult`, `claim_final.finding`, `stroke_owner.box_says`). Dynamic, flag,
  articulation and tuplet boxes consult none.
- **Page ledger.** `OMR_PAGE_CLAIM_NAMES`, `OMR_PAGE_HEADS`, `OMR_PAGE_BEAMS` and `OMR_PAGE_CLAIM_BOXES` are all OFF or
  file-only (manager verified the defaults on main 8ad741838). The page-stroke map is ON.
- **Tests.** None of the 20 claim test files reads a real page.

**Process lesson:** when a claim has to be made optional, ask "what unit is the claim in" before "which claim may skip". Four
exceptions in four lanes were one wrong unit.

## Test issue or wiring issue

- **By ink, it is wiring.**
  - 68–75% of non-staff ink has exactly one owner (17 pages).
  - ORDER-VIOLATION is 0.3% (137k of 40.2M px).
  - About 12% is read by no layer, about half of it staff-line residue.
  - 7–10% is claimed twice by twin boxes.
  - A few thousand px of real heads, sharps and dynamics lose ink or take another mark's: small in ink, large in notes.
- **By visibility, it is the tests.**
  - The claim tests use constructed strokes.
  - Re-adjudicate replays a fixed gather (`review/rerun.py`: "a GATHER change never enters the rebuild"), so a lane that adds a
    GATHER claim cannot see its own claim that way.
  - The newest saved slice (20261104-night) predates 2.273.
- Of 19 inventory rows, 14 are pipeline, 2 test, 1 convention, and 2 other.

## Readout (`claim_readout`, slices `lane-report-slices-20261104-night`)

**Controls fail when they should** (Brahms p0):
- ARC_CLAIM=0 drops register arc ink from 292,857 to 0 px.
- A planted double claim raises contested ink from 177,913 to 495,372 px.
- The re-cut cells match the record (112 cells, 3,256 strokes).

Share of non-staff ink (Brahms 31.3M px over 8 pages; Litolff 9.17M px over 9 pages):

| state | Brahms | Litolff |
|---|---|---|
| one owner | 68.4% | 74.5% |
| twin | 9.8% | 7.3% |
| contested, settled / open | 8.4% / 0.4% | 4.0% / 0.4% |
| unclaimed or weak | 13.1% | 13.8% |
| – staff-line residue | 6.4% | 2.1% |
| – no detector box | 4.1% | 9.4% |
| – weak (heading text) | 1.6% | 1.7% |
| same ink in 2+ cells | 19.0% | 16.9% |

- The biggest contested pairs:
  - Brahms arc+beam: 953k px (3.0%). Beam boxes are drawn on slurs and hairpin arms; the arc claim wins.
  - Litolff accidental+clef_key_meter: 100k px (1.1%).
- Order classes, Brahms / Litolff:

  | class | Brahms | Litolff |
  |---|---|---|
  | ORDER-OK | 8.1% | 4.2% |
  | EARLIER-UNREAD | 78.3% | 81.6% |
  | VIOLATION | 0.35% | 0.31% |
  | OPEN | 0.52% | 0.95% |
  | SPLIT | 0.70% | 0.79% |
  | NO-READER | 12.1% | 12.2% |

- About 87k of the 137k violation px are pairs where `stroke_owner.TIERS` and `claim_order.LAYERS` disagree by design.
- **Brahms p0 vs Sean's labels:** 1287/1566 right, 85 nothing, 185 wrong kind.
  - `ledgerLine`: 38 of 40 held by another kind.
  - `tremolo1`: 16 (2.276 is not on this tree).
  - `barlineDouble`: 3 of 3 nothing.
  - `barlineSingle`: 6 of 27 nothing.
  - Dynamics: 10 of 17 claimed page-wide; 7 only at the late per-cell tier.

## Ranked inventory

1. **Per-cell ownership; the page ledger OFF.** 17–19% of ink is seen twice; twins hold 3.74M px (9.3%). Bug (structure).
2. **Staff-line residue unclaimed** (eraser). 2.2M px (5.4%); crop 11 shows a whole staff line. Bug.
3. **Ink with no detector box.** Brahms 1.28M px (4.1%), Litolff 860k px (9.4%); crops 02, 04. Bug / open design.
4. **LAYERS vs TIERS.** 137k px of order violation. Sean: 3 of 8 stem tiles and 2 of 12 blue tiles are sharp pieces (2.282).
   Open design.
5. **Dynamics claim page-wide only as 2+ letter runs.** A single `p` or `f`, or an in-staff word, claims only at tier 4
   (`gather_page_claims`, `family_precision.adjudicate_dynamic_is_not_a_dynamic`). Sean's 2.276 r2 tiles 6 and 10.
   Workaround / bug.
6. **Heading and rehearsal-letter text: no reader.** 640k px (1.6%); crop 06. Open design.
7. **`stroke_map` cuts a clef or bracket;** only the largest piece is claimed. 289k px (0.7%). Bug.
8. **Double and final barlines read but unowned** (`measure_extractor.detect_barlines`, `barline_columns`, `gather.py:296`).
   81k px; crops 03, 07. Bug.
9. **`claim_final.MARK_ONLY` / `arc_claim.claim_strokes`.** 3.7k px of head ink on 4 Litolff pages. Workaround.
10. **Dynamic, articulation, flag and tuplet deciders consult no claim;** `BOX_FAMILIES` lists dot, mark, dynamic and text
    with no consumer. Bug (coverage).
11. **Three refusal mechanisms plus `CONSULTED_ELSEWHERE`;** `page_claim_names._areas` repeats `stroke_owner._areas`.
    Claim reasons are about 9% / 5% of head and rest refusals; shape rules carry the rest.
12. **Five clef, three key and three meter readers in `gather.py`.** Extra reads, not wrong ink.
13. **`gather_arc_ink` recomputes the `Q.SYSTEM_ARC` trace coverage;** arcs are seeded from detector boxes only.
14. **Claims are filed last in GATHER,** after about 60 box readers. `direction_text._blank_detections` erases boxes before
    reading words.
15. **LAYERS vs TIERS pairs differ by design.**
16. **The "owns a stroke of its own family" escape** in `claim_final`.
17. **Re-adjudicate is blind to GATHER claims** (test).
18. **No claim test reads a real page** (test).
19. **Stale comment at `gather.py` ~17764:** it says arc erase is ON; the code says OFF.

## Arc MARK-ONLY

**A workaround, not a convention or a ruling.** The manager added it on 2026-11-08 after Litolff tiles showed arc-held heads
were real.

**Cause** (probes `arc_trace_probe.py`, `arc_end_probe.py`):
- 49 of 1565 arc-claimed strokes carry a head box on Litolff pages 2, 4, 6 and 10; 3 of 1329 on Brahms p4–5.
- 48 of 60 links are hollow half-note heads. Their thin rim leaves tiny strokes, and a sliver on the slur end meets the 0.5 cut.
- The trace ends inside the head box for 36 of 43 boxes.

So it is the trace overrunning the arc's end, combined with the stroke as the claim unit. The eraser already uses the right
unit: `arcs_system.erase_in_cell` takes traced pixel runs only and protects non-arc boxes.

**Fix:**
1. Claim trace pixels, not strokes.
2. Stop the trace at its bound head (`anchor_left`/`anchor_right`), or skip pixels inside head boxes.
3. Compute `held_share` on pixels, then delete `MARK_ONLY`.

**Falsifier:** the 14 Litolff arc-held head boxes still show at least 0.5 held after steps 1–2.

## Proposed lanes (none built; Sean picks)

1. **Claim what nobody owns** (rows 2, 3, 7, 8; about 4.6M px, 11%).
   - Plan: 12 residue tiles first, then a staff-layer claim for line residue and an UNREAD mark for boxless strokes.
   - Falsified if the residue is mostly not line-shaped, or if Sean reads more than ~10% of the boxless blobs as real heads
     (then it is a detector lane).
2. **The page ledger owns: one owner per page stroke, one consult** (rows 1, 4, 5, 10, 11, 15).
   - First, measure cross-cell owner disagreement and take the 2.282 result.
   - Falsified if disagreement is under ~1%, or if 2.282 says the code order is right.
3. **Arcs claim only their own ink; `MARK_ONLY` goes** (row 9, about 0.1% of ink).
   - Runs after 2.281's `bind_end` edit lands, or that lane is retired.

## Not verified

- The sample predates 2.273; a fresh 2–3 page gather is the control before lane 2.
- Crop 05's contested kinds.
- The residue class beyond one crop.
- How the 2.276 r2 tiles were produced.
- `claim_order` was run with no OFF arm.

## Files

- `out/`: readouts and logs.
- Probes: `arc_trace_probe.py`, `arc_end_probe.py`, `crops.py`, `residue_crops.py`, `kind_table.py`.
- Crops: `out/print-from-worktrees/2.283-audit/` in the main checkout (not committed).
