"""Writes FINDINGS.md for this benchmark directory (kept as a script so the
record can be regenerated; the .md itself is the committed deliverable)."""
from pathlib import Path

BODY = r"""# Arc CV — round 8: reading slurs and ties by stroke geometry

2026-09-04/05, branch `claude/scan-weights-round4-continue-074940` (continued
in a worktree). Follows round 7 (`benchmarks/omr-queue-arcs-2026-09/
ROUND7_FINDINGS.md`), which closed the learning path with a measured pincer:
production's arc precision on the adjudicated scan gauntlet is **0.232** at
recall 0.824, a frozen-head specialist cannot separate real arcs from the
certified fakes because the trunk's features do not, and full fine-tuning
deletes whole classes (rounds 3-6). The surviving lever is the project's
oldest move — geometry where YOLO is structurally weak (Phase 4f: "YOLO
bounding boxes are structurally bad at thin lines", and a slur IS a thin
curved line).

**What shipped:** `tools/omr/arc_detection.py` — a classical-CV arc reader —
and an `OMR_ARC_CV` arbitration in `transcribe._detections_for_cell`,
**default OFF**. CV arcs are `LineDetection`s with class `tie`/`slur` and
category `structural`, so they flow into the SAME event machinery YOLO arcs
do (`_pair_ties_in_cell` / `_pair_ties_in_staff`, `annotate_slurs_in_slot`) —
no parallel event model, per the round brief.

## The gauntlet

`benchmarks/omr-queue-arcs-2026-09`: 126 scan cells (Breitkopf Brahms 1
pp. 2-3), every teacher arc candidate hand-adjudicated by Sean — **176 real
arc boxes** (107 tie, 69 slur) and **260 certified fakes** (179 tie-classed,
81 slur-classed). Scoring protocol identical to `probe_arcs_vs_human.py`:
IoU >= 0.3 against the human boxes, conf 0.25 for the model side.

The two documented fake families, proxied by band position
(`probe_box_positions.py`): 72 fakes centre INSIDE the five-line band (the
jagged-staff-line family), 188 outside it (the neighbouring-staff bleed
family). The same probe measured where real arcs live, and the asymmetry
became a load-bearing constant (below).

## The reader

`detect_arcs(cell)`, on the staff-removed image (same preference as
`detect_stems`):

1. **Thin-run mask** — keep only ink pixels whose vertical run is <= 0.45
   staff spaces (`ARC_THIN_RUN_MAX_SPACES`). Real arc strokes measure a
   median 0.20-0.37 spaces per column (p95 0.371); noteheads ~1.0, beams
   0.4-0.6. This one cap cuts arc strokes free of every solid symbol they
   touch. WARNING: there is deliberately NO separate per-stroke thickness
   gate: a gate at the population's p75 (0.32) was measured refusing **31 of
   the 176 real arcs** for no fake refused (`probe_recall_losses.py`,
   `gate:thickness`) — scanned arcs are thick.
2. **Fragment chaining** — connected components of the mask are fragments; a
   scanned arc is routinely cut where a stem crossed it or removal chewed it.
   Facing ends within 0.8 spaces of x-gap and 0.4 spaces of height rejoin
   (both plateaus: the gauntlet score is identical for gap 0.6-1.0 and dy
   0.3-0.5, `sweep_gates.py` arms1).
3. **Dissolved-gap join** — a faded stroke can crumble to dust for several
   spaces mid-arc (measured up to ~7 on the gauntlet). Two substantial
   pieces (>= 1.5 spaces) join across up to 8 spaces when the left piece's
   fitted quadratic predicts the right piece's opening midline within 0.2
   spaces. WARNING: at tolerance 0.35 this MERGED DISTINCT CONSECUTIVE TIES
   and recall went DOWN (0.545 -> 0.523) — 0.2 is the value at which the
   join stops inventing arcs (arms2 sweep); its net worth is +1 TP and
   +1.5pt precision, i.e. marginal, and it is kept mainly because a joined
   stroke's evidence is fit agreement rather than coverage.
4. **Gates**, each read off the measured populations
   (`probe_arc_features.py`, `probe_curve_rise.py`):
   - width >= 1.4 spaces (real p5 = 1.6);
   - coverage >= 0.8 of columns inked (0.3 for dissolved-joins);
   - quadratic-fit RMS residual <= 0.10 spaces (real p95 = 0.051 — smooth;
     staff jags are not);
   - **rise** >= 0.12 spaces, where rise = max(chord deviation,
     |a2|*w^2/8) — the second term is the fitted curvature's own deviation,
     which keeps a HALF arc cut at a barline (chord deviation under-reads a
     half arch ~4x) while refusing flat strokes (ledger lines, beam
     fragments, staff residue: OTHER population p75 = 0.073);
   - one-sidedness >= 0.95 of |deviation| on the majority side (an arch, not
     a wiggle; real p25 = 0.992);
   - **top/bottom slice refusal** — a stroke whose ink reaches the crop's
     top or bottom edge is refused; LEFT/RIGHT-touching strokes are KEPT,
     because they are arcs continuing across a barline, which the cross-cell
     pairing machinery exists to rejoin (real strokes touch left/right 25 of
     206 against top/bottom 12);
   - **below-staff cap** — a stroke whose midline centre sits > 2.5 spaces
     BELOW the bottom line is the staff below's ink. The populations are
     asymmetric and the asymmetry is an engraving fact: above the staff real
     arcs follow ledger notes up (29 of 176 real boxes at 2.5+ spaces above,
     15 beyond 4), but BELOW they stop — 4 of 176 in [2.5, 4), none at 4+ —
     because the space below a staff on a conductor's page belongs to the
     next staff. The certified fakes bloom exactly there (68 of 260).
5. **Tie/slur split** by width <= 6 spaces AND rise/width <= 0.11 -> tie,
   else slur. The width populations overlap heavily (tie p50 4.4, slur p50
   5.7), so CV kind accuracy is 0.54 — production's 0.72 is better, which is
   one reason the shipped arrangement keeps YOLO's class where YOLO's box
   survives.

Cost: **~66 ms per cell** (2048-wide canonical cells, pure numpy/OpenCV, no
model).

## Refused, with the measurements that refused them

- **A sliced-vs-grazing edge discrimination** (refuse only strokes that EXIT
  through the top/bottom edge, keep an apex that merely grazes it). Refused:
  real high arcs are genuinely cut by the crop too — the stroke-end
  distances to the touched edge are the same population for real and fake
  (real p50 0.04 spaces, fake p50 0.06; `probe_curve_rise.py`). The edge
  cannot decide ownership more finely than refuse/keep.
- **A per-stroke median-thickness gate** (0.32 spaces): cost 31 real arcs,
  refused 0 fakes beyond what the run mask already refuses.
- **Chord rise alone** as the arc test: under-reads barline-cut half arcs
  ~4x; replaced by max(chord, curvature) — see gate 4.
- **An above-staff position cap** (mirror of the below cap): real arcs live
  to 6+ spaces above (violin ledger territory, 15 of 176 beyond 4) — no gap
  exists on that side.
- **Coverage/fragment/gap loosening** to recover speckle-dissolved arcs
  (`arms1.json`): every arm lands within +/-0.02 of recall 0.55 / precision
  0.51 — a plateau, not a lever. The dissolved-arc loss is structural: the
  middle of the stroke is GONE at threshold 180, not fragmented.

## Standalone gauntlet numbers (the table the round was for)

`score_arrangements.py`, production = `hollow-graft-shift09-2026-09-04` at
conf 0.25 (sanity arm reproduces round 7's recorded row exactly):

| arm | dets | recall | precision | kind | fakes fired (of 260) |
|---|--:|--:|--:|--:|--:|
| production | 625 | 0.824 | 0.232 | 0.717 | 241 |
| CV alone | 179 | 0.551 | 0.542 | 0.536 | 33 |
| union (CV + unmatched YOLO) | 654 | 0.852 | 0.229 | 0.627 | 242 |
| CV + YOLO-where-no-x-overlap (beam rule verbatim) | 410 | 0.670 | 0.288 | 0.559 | 154 |
| **YOLO ∩ CV veto** | 185 | **0.602** | **0.573** | **0.726** | **37** |
| veto + CV extras | 230 | 0.648 | 0.496 | 0.702 | 38 |

The fake split for CV alone: **0 of 72** jag-family fakes fired (the
curvature gates close that family completely), 33 of 188 bleed-family — the
bleed family is real arcs belonging to the neighbouring staff, so geometry
alone cannot close it; only position and the crop edge speak, and both are
in use.

The **veto** (keep a YOLO tie/slur only where a CV arc overlaps it — IoU >=
0.1 or x-overlap >= 0.5, a plateau: 0.3 and 0.7 score identically) is the
best arrangement by precision (0.232 -> 0.573), kind accuracy (0.717 ->
0.726, best of all arms) and fake refusal (241 -> 37), at recall 0.824 ->
0.602. The beam-style keep-where-no-overlap rule — the arrangement the beam
work measured best — is NOT best for arcs: arcs invert beams' failure mode
(the beam problem was CV missing strokes; the arc problem is YOLO inventing
them), so the arbitration that wins is the veto, and this was measured
rather than assumed, per the brief.

## End-to-end

Flag-off is byte-identical by construction (`OMR_ARC_CV` unset returns the
detections list untouched; `test_arc_detection.py` pins the identity), so
the baselines are the recorded ones: engraved **0.1306 / 2745** (CLAUDE.md
OMR-NED block, `44a1745`), scan widened **0.8535 / 35817** 11-row,
**0.8387 / 29082** 10-row-excl-Bach (`WIDENED_BASELINE_2026-09-04.md`,
production graft column; this branch's `works.json` predates the Bach
`pooled: false` addendum, so both readings are stated).

RESULTS PENDING — this section is filled by the runs in
`results-scan-arccv-veto.json` / the orchestral_eval arm.

## Where the next round starts

- The recall ceiling standalone is extraction, not gating: 37 of 176 real
  boxes dissolve into sub-threshold speckle mid-stroke (`iou_low` bucket in
  `probe_recall_losses.py`). An adaptive threshold (Sauvola on the cell
  rather than the global 180) is the untried lever there.
- Ownership of an arc at the crop's top edge is undecidable from the cell
  alone (measured — see refused list). The pipeline HAS the disambiguating
  signal: the staff's own noteheads and `_dedupe_cross_staff_detections`'s
  cross-cell view. An anchor-aware veto at export time (an arc kept only if
  noteheads of this staff sit under both ends) is the natural next
  arrangement, and it is exactly the "grammar needs anchors" counterweight
  the `00b68e24` arc-grammar round recorded.
"""

Path(__file__).with_name("FINDINGS.md").write_text(BODY)
print("wrote FINDINGS.md")
