# Plan 2026-11-06 — arcs read from the page's ink, claimed once, bound to notes after the heads (no ROADMAP number yet)

STAGED. Design + a feasibility measurement, no production code (design agent, branch `plan-page-ink-arcs` off main a29652a24). Paths under
`tools/omr/staged/` unless named. Sean, 2026-11-06: *"I still think we are circling the fix and missing a process that take the first ink run
from the page reads and attaches it to notes without cutting up the arcs."*

## 1. Cause and process lesson

**Cause.** An arc's IDENTITY on STAGED today is a detector box, and the detector runs per cell, barline to barline
(`gather.gather_detections`). Everything after it inherits the cut:
- the page "curve" is that box + 0.5 sp, 3 sp past a cut edge (`arcs_system.gather_system_arcs` / `trace_arc` / `_follow`), so it stops where
  the box stops; `join_traces` then stitches boxes and also over-joins arcs that meet at a note (Brahms 15 curves hold 71 boxes);
- a barline-crossing arc is boxed on ONE side only on 91% (Litolff) / 71% (Brahms) of cut arcs (branch `arc-barline-cut-test` ef226deba);
- ADJUDICATE and EXPORT re-read the boxes (`ownership._flank_search`, `_two_note_reading`, `adjudicate_tie_pair`; export's LEGACY
  `_merge_arcs_across_barlines` / `_paired_spans`): the deep dive (`arc-deep-dive-2026-11`) found end-binding failures are ~63% (Litolff) /
  ~44% (Brahms) of dropped arcs, and of 138 Litolff ends > 4 sp from any head, 111 have NO neighbouring box.

**Why every fix circled.** Each worked DOWNSTREAM of the box: 2.271 bound the curve's ends to the closest note, but the curve was a half arc
(Sean's tiles 2, 4, 5, 9, 10, 12: "the orange box not capturing the full arc"); 2.272 walked the ends on along the ink, but still SEEDED
from a box (an arc never boxed is never walked); the curve-only bind (`arc-curve-only-test`) dropped +3% / +20% more; 2.273 (`OMR_ARC_STRIP`,
Sean 11/12) recovers far halves with a second detector pass -- still box-first: ink is found only where a box says to look. All four asked
"how do we repair the pieces?" instead of "what is the arc on the page?".

**Process lesson.** page-facts already ruled it (2026-10-30): *"a detector box in a cell is only a witness to it, never the mark."* The
lanes kept the detector as the identity because the page stroke map (M2, 2.260a) arrived after the arc readers and nobody re-asked which
reader should be FIRST once the page raster existed. When a new frame lands, re-ask which reader each mark should start from, not only
which claims to translate (the 2.269 lesson, one step earlier).

## 2. Prior ink-first arc readers and why they made fakes

- **Round 7 (09-04, `project_round7_arcs_pincer`):** 260 of 268 "teacher" arc candidates were fake: 188 a NEIGHBOUR staff's real arcs bleeding
  into the cell's padding, 72 jagged scanned staff lines. Cause: candidates read on a CELL crop with its padding, staff lines present.
- **Rounds 8-9 (`claude/arc-cv-round8`, `claude/arc-anchor-round9`; `benchmarks/omr-arc-anchor-2026-09`):** classical CV shape gates closed the
  jag family (0/72) but not bleed; anchors (an end must land on this staff's heads) closed bleed (38/188) but fired on jags; a one-edition
  gauntlet mispriced the flat Litolff ties (rise 0.06-0.12 sp). Withdrawn 09-05 when `OMR_ARC_ATTRIBUTION` landed the anchor idea export-side.

**How this design avoids each:**
| old fake | why it cannot recur here |
|---|---|
| neighbour-staff bleed | read ONCE on the PAGE: the neighbour's arc is its own single run, not a fragment in another cell's padding |
| jagged staff lines | staff lines are claimed first (each staff's own erased band, M2) and a run that sits on a line row is refused (`on_a_line`); smoothness is measured off the run's own running mean, not a global fit |
| flat ties under a rise gate | no rise gate for short runs; only a run longer than 4 sp AND straighter than 0.1 sp is refused (a hairpin leg, a beam, a line) |
| beams, words, hairpins, heads taking or giving ink | claim order: barlines carved (M1/M2), page claims (words, clef/key/meter, brackets) take the components WHOLLY inside them (`stroke_owner._areas`' predicate, as 2.269 names strokes); compact detector marks (heads, accidentals, dots, rests, flags, fermatas, letters, ledgers) blank their box; a run is built only from THIN column runs, so stems, heads and beams are holes it crosses, never ink it takes |
| two arcs fused at a note | a track splits at a bridged hole where its slope turns from one sign to the other (a V at a claimed head); an arc's own apex is shallow and does not sit on a hole |
| the detector deciding | the detector's arc box is a WITNESS: it confirms a run (overlap) or, where no run exists, seeds a bounded local read; it never sets the arc's extent |

## 3. The stages (STAGED; GATHER page-wide pass, then ADJUDICATE after the heads)

1. **GATHER, page-wide pass, after structure and the page claims (claim order layer 4, CLAUDE §3):** new `page_arcs.read_page_arcs(page_map,
   claims, detections)` in a new module, called where `arcs_system.gather_system_arcs` is called today. Input: the M2 raster
   (`page_strokes.map_page` -> `Assembly.canvas`, bands erased, barline columns carved), with the 2.269 claims (`page_claim_names.
   gather_page_claim_names`) and the compact detector boxes blanked. Output: one `Q.PAGE_ARC` row per RUN: its centre line (page px), width,
   sagitta, thickness, the page strokes it runs along (named, for the claim), the witnesses (detector arc boxes it overlaps), its two ends
   with their tangent. Reads no cell.
2. **Claim, once:** `gather_arc_claim` (gather.py) claims the run's page strokes for the arc owner (as M3 does for curves today); later readers
   mark, never take (beams already ask `_not_a_decided_arc` / `_strokes_on_a_system_arc` -- they keep reading the claim).
3. **Witness reconciliation (GATHER, no decision):** a detector arc box no run overlaps is filed as a WITNESS ONLY, with a bounded local read
   (today's `trace_arc` inside the box) as a candidate run marked `seeded`; a fermata/staff-line box is left to its existing refusal
   (`family_precision.adjudicate_arc_is_not_an_arc`). Counted both ways: runs with no box, boxes with no run.
4. **ADJUDICATE, after the heads are read (page heads M6 when on; today's boxes otherwise):** `arc_claim.bind_curve` / `bind_end` bind each
   run END: the nearest usable head on the curve's concave side; "closest note" when it stops short; two equally near abstain; a run that
   reaches a system's edge is joined to the run that starts at the next system's edge on the same part's staff, one candidate only (2.271's
   join, unchanged). The kind follows from the two bound heads (page-facts §1). `ownership._page_binding` reads the run, never the boxes.
5. **EXPORT:** writes one tie/slur per run from its two bound heads (`export._record_tie_pairs`, `_page_bound_slur_spans`). An unbound end
   is UNREAD (red), never invented.

**Retire (only once the run path covers each case; each its own sub-step and flag):** `arcs_system.trace_arc` as the identity (kept as the
seeded witness read), `join_traces` / `same_curve` (a run is already one arc), `gather_arc_ink` (recomputes coverage), the box re-reads
`ownership._flank_search` / `_two_note_reading` / the box branch of `adjudicate_tie_pair`, and export's LEGACY `_merge_arcs_across_barlines` /
`_paired_spans` / `_noteheads_under` on the STAGED path; 2.273's strip pass becomes a witness source, not the arc.

## 4. The rule that owns each value

| value | owner |
|---|---|
| that it is an arc, and its extent | page-facts "Arcs and hairpins are READ PAGE-WIDE ... a detector box is only a witness" (2026-10-30); DECISIONS 2026-11-03 "Read once. Claimed once.", 2026-11-05 "Arcs should be read page level so they shouldn't be reread and broken up later" |
| order of claims | CLAUDE §3 claim order; plan-2026-10-28 §9-10; `claim_order.py` layers |
| which head an end binds | page-facts "An arc often stops short ... binds to the CLOSEST note" (2026-11-05); equally near = abstain |
| cross-system joins | page-facts / DECISIONS 2026-11-05 "Anything that needs to be done to connect arc separated by systems is fine" (one candidate only) |
| tie vs slur | page-facts §1 "A tie joins exactly TWO ADJACENT notes of the SAME pitch" (2026-10-29); DECISIONS 2026-11-05 "This should be easy" |
| same position | DECISIONS 2026-11-03 "a tie is read from POSITION, not pitch" (local staff position at each head) |
| head position under a ledger | page-facts "The ledger lines name the owner" (2026-10-28) -- untouched here |
| what is UNREAD | CLAUDE §4: an unbound end is red, never invented; rule 8 |

## 5. Feasibility (measure only; `benchmarks/omr-arc-binding-2026-10/page-ink-2026-11/`, FINDINGS "2026-11-06 PAGE-INK ARCS")

Brahms p0 (Sean's 153 hand arcs = 109 printed arcs after joining cell pieces) and Litolff p16, from the M2 raster rebuilt with GATHER's own
functions (no detector run) and the saved 20261104-night gather for claims; detector path = that gather's page curves (pre-2.273).
- Brahms p0, corrected scorer: ink-first WHOLE 96/109 vs detector 92/109; arcs over 2+ bars 23/26 vs 19/26; per hand box 135 vs 134.
  Literal pre-registered scorer: 69 vs 72 (it counts a run longer than the boxed half as off the arc; the look showed 14 of its 16 "fakes"
  are real arcs Sean boxed in one cell only).
- Fakes by look: Brahms 2 (both two ledger lines between chord heads), Litolff 1 (same kind).
- Litolff p16 (no truth, untuned): 7 real ties the detector path has no curve for; about 9 distinct real arcs (13 curve rows with twins) the detector found and the ink runs miss
  (short ties hugging a staff line inside the band, ties into a barline/stem, two on a staff line inside the staff).
- The run parameters were adjusted four times on Brahms p0 (v1 45 whole / 23 "fakes"): the Brahms figures are in-sample.

## 6. Risks

- **Inside-the-staff arcs.** The erased band damages short ties that hug a line (Litolff p16's misses): the seeded witness read (§3.3) is the
  fallback; measure it before retiring any box path.
- **Unboxed ledgers** pair into flat runs (all 3 fakes): claim ledger ink first (2.269 step 3 / M6 ledgers), or refuse a flat run whose ends
  sit on head boxes at ledger rows.
- **Compact boxes blanked as rectangles** can still cut an arc a false box covers (a false `beam` box took half a Brahms slur until beams were
  left unblanked). The 2.269 page-stroke claims should replace rectangles.
- **Steep arc ends** are lost (a column run over 0.62 sp is not arc ink): the bind relies on closest-note, which Sean has ruled.
- **Cusp split** could cut a real S-shaped slur at a hole; count splits and tile them.
- **Cost:** the run tracker is ~1 s/page in Python at 16 px/sp; no OCR, no detector pass (the M2 raster exists already).
- **Hand truth is per cell and incomplete for arcs** (the first system's left halves are unboxed): scoring needs the clipped rule, and the
  next measure needs Sean's tiles, not only the hand file.

## 7. Question for Sean (grep of page-facts and DECISIONS: arcs read page-wide with the box as a witness is ALREADY his ruling, 2026-10-30)

One question: *"The arcs can be read straight from the page ink as one piece each, crossing barlines, with the detector box only as a
check. On the first Brahms page that finds slightly more whole arcs than today (96 vs 92 of 109) with 2 false ones. Build it behind a
switch, file-only first?"*
