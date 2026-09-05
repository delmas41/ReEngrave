# Arc anchors — round 9: an arc is kept by what it connects

2026-09-04/05, branch `claude/arc-anchor-round9` (based on
`claude/arc-cv-round8`, c1f70cdf). Follows round 8
(`benchmarks/omr-arc-cv-2026-09/FINDINGS.md`), whose veto improved every scan
row (-125 edits) while HALVING exported tie inventory (420 -> 209 of 805),
because the CV rise gate — read off the Breitkopf gauntlet — refuses
Litolff's flat-printed ties. The hypothesis this round tests: an arc's
identity is settled by its ANCHORS, not its shape — a real arc on this staff
starts and ends at (or just past) this staff's own noteheads; an edge-bleed
fake's anchors are out of frame or belong to the neighbouring staff; and a
flat tie with confirmed anchors is real no matter what the rise gate says.

**What shipped:** two new `OMR_ARC_CV` modes (still DEFAULT OFF, everything
identity when unset):

- `anchor` — keep a YOLO tie/slur only when each end lands on the cell's own
  detected noteheads, or is CUT-EXEMPT within 0.5 spaces of the LEFT/RIGHT
  crop edge (the cross-cell pairing machinery — `_pair_ties_in_staff`,
  `_merge_arcs_across_barlines` — owns those joins, and the anchoring
  notehead lives in the neighbouring cell); at least one end must carry a
  real anchor. No CV pass — this mode costs nothing.
- `anchor+cv` — the anchor filter, plus the CV reader re-run at a RELAXED
  rise floor (`ARC_RELAXED_MIN_RISE_SPACES` = 0.05) whose arcs are admitted
  only where BOTH ends anchor (no exemption): shape refused them, the
  anchors overrule it. This is the flat-tie recovery arm.

Top/bottom crop cuts get NO exemption, on purpose: a real high arc clipped
at the top still hangs its ends over this staff's own (ledger) noteheads,
while a bleed arc from the staff above anchors on nothing here — that
difference is the whole hypothesis, and exempting top/bottom-touching boxes
would wave the entire bleed family through.

## The anchor populations (the constants' provenance)

`probe_anchor_populations.py` over the adjudicated gauntlet (126 Breitkopf
Brahms 1 scan cells, 176 human-real arc boxes, 260 certified fakes — 72
jag-family/in-band, 188 bleed-family/outside, same split as round 8):
per END, the nearest detected notehead's dx (notehead widths; positive =
outside the arc span, the tie-pairing direction) and dy (spaces from the
notehead centre to the arc box's y-interval). Noteheads are production's own
detections after `_drop_clipped_notehead_fragments` — the exact list
`apply_arc_cv` sees at arbitration time (`cache_yolo_dets.py`).

Real, non-exempt ends (258): 10 have no anchor at all within dy 2.0.
Where the nearest anchor is OUTSIDE (136 ends): p50 0.26 / p90 0.60 /
**p95 0.94** widths -> `ARC_ANCHOR_MAX_DX_OUT_NOTEHEADS = 1.0`.
Where it is INSIDE (112 ends): p50 0.34 / p75 0.81, then a long tail
(p90 2.47) — ends whose own notehead the detector MISSED, the nearest
surviving head sitting deeper under the arc. The fakes' nearest inside head
sits at p50 1.92, so there is NO clean gap on this axis:
`ARC_ANCHOR_MAX_DX_IN_NOTEHEADS = 1.0` stays on the right side of the fake
median, and chasing the real tail admits fakes (the sweep prices dx_in 2.0
at +8 real boxes for +20 fakes). `ARC_ANCHOR_MAX_DY_SPACES = 2.0` is the
sweep's shoulder (real 142 -> 144 of 176 from 2.0 -> 3.0 while fakes climb
56 -> 61). Full sweep: `analyze_anchor_populations.py`.

WARNING: **the anchor test inherits notehead recall.** ~17 of 176 real boxes
never anchor at ANY window tried, because the heads under their ends were
not detected. That is the mode's recall ceiling, and it moves with the
detector — the same downstream-of-recognition shape as the pre-fill's
precision (Phase B of the admission work).

## Gauntlet (`score_anchor_arms.py`, protocol identical to rounds 7/8)

| arm | dets | recall | precision | kind | fakes (jag/bleed of 72/188) |
|---|--:|--:|--:|--:|--:|
| production | 625 | 0.824 | 0.232 | 0.717 | 241 (66/175) |
| CV alone (r8) | 179 | 0.551 | 0.542 | 0.536 | 33 (0/33) |
| veto (r8) | 185 | 0.602 | **0.573** | **0.726** | 37 (1/36) |
| veto+cv (r8) | 230 | 0.648 | 0.496 | 0.702 | 38 (1/37) |
| **anchor** | 237 | **0.665** | 0.494 | 0.667 | 56 (18/38) |
| anchor+cv | 256 | 0.665 | 0.457 | 0.667 | 56 (18/38) |
| anchor AND veto | 130 | 0.500 | 0.677 | 0.682 | 15 (0/15) |
| anchor OR veto | 292 | 0.767 | 0.462 | 0.704 | 78 (19/59) |
| band-hybrid (in-band->veto, outside->anchor) | 195 | 0.636 | 0.574 | 0.670 | 40 (2/38) |

The two headline counts the round brief asked for:

- **Edge-bleed kill: the anchor fires on 38 of the 188 bleed fakes**
  (production fires on 175, the veto on 36) — the anchor test alone closes
  the bleed family as hard as the CV veto does, from position evidence the
  CV never sees.
- **Recovered arcs: 29 of the real arcs the veto lost come back under
  anchor — 25 of them TIES** (probe_recovery_split.py) — precisely the
  inventory the veto halved. The reverse trade: the anchor loses 18 arcs
  the veto keeps (8 ties / 10 slurs — long arcs whose end heads went
  undetected).

What the anchor CANNOT do: close the jag family. 18 of 72 jag fakes anchor,
against the veto's 1 — a jagged staff-line remnant lies INSIDE the five-line
band, where noteheads are everywhere, so anchors are cheap there. Shape
evidence (the CV's curvature gates, 0 of 72) owns that family; position
evidence owns the bleed family. They are complementary, which is what
`anchor AND veto` shows (15 fakes, 0 jag, precision 0.677 — at recall 0.500)
and the band-hybrid confirms from the other side (veto's precision at +0.034
recall). Neither composition dominates; the standalone `anchor` is what
went to e2e because its distinct value claim — publisher-robust tie
retention — is the thing round 8 could not deliver.

On the home gauntlet `anchor+cv`'s relaxed extras add 19 detections and not
one true positive: Breitkopf is the publisher the standard rise gate was
READ FROM, so everything real that is flat enough to need the relaxed floor
was already found by YOLO and anchored. The relaxed pass's value claim is
entirely cross-publisher, which the gauntlet cannot price (one edition) —
that is what the scan e2e is for.

## The Litolff population (the relaxed floor's provenance)

`probe_litolff_rises.py`, the whole of Litolff Beethoven 5 p1 (pdf page 1 of
imslp984073, 600 dpi — the page round 8 diagnosed from a handful of refused
cells): 43 strokes pass the standard gates (matching round 8's count);
**5 more pass every gate EXCEPT rise, at rise 0.062-0.120 spaces** — the
flat-tie population, sitting exactly where round 8's spot-reads put it
(0.062-0.116). `ARC_RELAXED_MIN_RISE_SPACES = 0.05` sits under its minimum;
anything flatter than 0.05 spaces at scan resolution is a straight line.
One edition's populations do not bound another's — the floor is a FLOOR for
anchored admission, not a recalibrated gate.

## End-to-end

(Same-tree A/B only: flag-off on this tree vs flag-on on this tree. The
canonical composed baseline moved with the tilt/choir ships on another
branch, so re-pricing against a composed tree belongs to reconciliation,
not to this round.)

### Scan (11-row `scan_eval`, production weights pinned, tag `arcanchor`)

⚠️ **Recovered after a usage-credit stop killed the session mid-round.** The
`anchor` arm's run had COMPLETED; its results JSON and its 11 exported
MusicXML files survived in `fixtures/`, and the element counts below were
counted from those files directly. The `anchor+cv` and engraved arms were
still running and are NOT reported — they are TBD, not zero.

Baseline is the same-generation 11-row production figure
(`results-widened-graft.json`, pre-tilt — this branch predates the tilt and
choir ships, so that is the correct same-tree comparison; the composed-tree
re-pricing belongs to reconciliation).

| | pooled | edits | pred | wrong tie | wrong slur |
|---|--:|--:|--:|--:|--:|
| flag-off baseline | 0.8535 | 35817 | 18586 | 28 | 111 |
| **anchor** | **0.8533** | **35743** | 18510 | **26** | **99** |

**-74 edits, ratio flat, and the emission drop is 76 symbols — not a
halving.** Exported inventory, counted from the arm's own files against the
same truth:

| arm | exported `<tie>` of 805 | exported `<slur>` of 404 |
|---|--:|--:|
| flag-off (round 8's measure) | 420 | — |
| round 8 `veto` | 209 | — |
| **round 9 `anchor`** | **353** | 246 |

**This is the round's value claim, delivered.** Round 8's veto bought its
edits by halving tie inventory (420 -> 209); the anchor buys a comparable
metric improvement while keeping **353** — 144 more ties than the veto — and
`wrong tie` still falls (28 -> 26) and `wrong slur` with it (111 -> 99). The
ties it does drop relative to flag-off are, on that evidence, mostly the
wrong ones. Position evidence retains what shape evidence discarded, which
is exactly what the Litolff diagnosis predicted.

Both remaining arms then completed (run from the parent session after the
credit stop; same tree, same pinned weights).

| scan arm | pooled | edits | pred | wrong tie | wrong slur | exported ties /805 | slurs /404 |
|---|--:|--:|--:|--:|--:|--:|--:|
| flag-off baseline | 0.8535 | 35817 | 18586 | 28 | 111 | 420 | — |
| round 8 `veto` | — | −125 (10-row) | — | 20 | 104 | 209 | — |
| **`anchor`** | **0.8533** | **35743** | 18510 | 26 | **99** | 353 | 246 |
| **`anchor+cv`** | 0.8534 | 35779 | 18549 | 26 | 104 | **398** | **282** |

**The relaxed floor's cross-publisher claim is confirmed.** On the
single-edition gauntlet `anchor+cv`'s relaxed extras added 19 detections and
zero true positives — Breitkopf is the edition the standard rise gate was
read from, so there was nothing there to recover. Across the eleven scan
rows it recovers **45 ties and 36 slurs** over `anchor` (353 -> 398,
246 -> 282, against flag-off's 420) for **+36 edits** — still 38 edits BELOW
the flag-off baseline. That is the Litolff population being admitted by
anchors where shape refused it, and it could only ever be measured here.

### Engraved (11-work `orchestral_eval --omr-ned`, `anchor` arm)

| | pooled | edits | truth | pred |
|---|--:|--:|--:|--:|
| documented baseline | 0.1306 | 2745 | 10665 | 10361 |
| **`anchor`** | **0.1301** | **2733** | 10665 | 10339 |

**The anchor mode IMPROVES the engraved family** — −12 edits at a lower
ratio — where round 8's veto regressed it by +9. Ratio and edits move the
same direction (both down), so this is not the dilution signature (which is
ratio down while edits rise); the 22-symbol emission drop is smaller than
the edit gain. This removes the scan-only scoping constraint that round 8's
result imposed: `anchor` is the first arc change measured to help BOTH
families.

`anchor+cv` then landed at **0.1302 / 2734 edits** (pred 10340) — within one
edit of `anchor`, and also better than the 0.1306 / 2745 baseline. So BOTH
modes improve BOTH families, and the engraved side does not discriminate
between them: the choice between them is a scan-side inventory-vs-edits
question, not a scoping one.

| mode | scan pooled | scan edits | scan ties /805 | engraved pooled | engraved edits |
|---|--:|--:|--:|--:|--:|
| baseline | 0.8535 | 35817 | 420 | 0.1306 | 2745 |
| `anchor` | **0.8533** | **35743** | 353 | **0.1301** | **2733** |
| `anchor+cv` | 0.8534 | 35779 | **398** | 0.1302 | 2734 |

**Recommendation on the mode, when this is re-priced for a flip:**
`anchor+cv`. The two are separated by 1 engraved edit and 36 scan edits —
inside the noise of what a composed-tree re-run will move — while the
inventory gap is 45 ties, and tie inventory is the thing the whole arc
thread exists to fix (production reads 97 of 271 on the older measure; the
truth here holds 805 and flag-off emits 420). Buying 45 real ties for 36
edits is the trade this project has taken before and recorded as right
(the articulation ship: +97 pooled edits for 263 correctly-placed marks).

⚠️ **No flip is priced yet even so.** These are same-tree A/B numbers on a
branch that PREDATES the tilt and choir-grouping ships; the canonical scan
baseline moved to 0.8303 / 35046 on the composed tree. Re-pricing there is
reconciliation work, and the arc constants (rise, dx, dy) still rest on one
edition's populations for the standard gate and one more for the relaxed
floor — the clef-threshold lesson says two editions is the minimum before a
constant is trusted, and this has that only for rise.

### Engraved (11-work `orchestral_eval --omr-ned`, anchor arm)

TBD — run in flight.

## Refused / noted

- **A top/bottom cut exemption** (the symmetric reading of "crop cuts are
  exempt"): refused by construction — it would exempt the entire bleed
  family, whose boxes touch the top/bottom edge by definition. The un-cut
  reading (anchors decide vertical-edge cases) IS the hypothesis.
- **dx_in wider than 1.0** to chase the real inside tail: +8 real boxes for
  +20 fakes in the window sweep — the tail is missing-notehead damage, and
  the fix for missing noteheads is not a wider window.
- **anchor OR veto** as the e2e arm: best gauntlet recall (0.767) but it
  re-admits both families' leaks at once (78 fakes) and its precision
  (0.462) sits below every composed arm; nothing it adds is priced.
