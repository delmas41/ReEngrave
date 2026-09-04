# Round 6 — per-symbol specialists: rows compose exactly, corpora betray their own class

**Date:** 2026-09-04 · **Box:** vast.ai RTX 4090 24 GB (Taiwan), destroyed ·
**Session GPU total so far: $0.65.** Production scan weights untouched.

Sean's architecture question opened this round: *train one YOLO per symbol and
sweep the page once per model?* The literal form costs one forward pass per
specialist (20 specialists ≈ 50 min/page), but a YOLOv8 head is per-class in
its last 1×1 conv, so a specialist's knowledge of its own symbol lives in that
symbol's rows and nowhere else — transplant the rows and the ensemble compiles
into ONE model, one pass. Round 5's graft was the two-model case; this round
built the general machinery and tested it.

## 1. What was built

* `build_specialist_versions.py` — carve a per-family corpus out of the labels
  that already exist: filter each label file to the family, keep only cells
  whose stamped passes swept it. **No new labeling.** Cells not swept are
  EXCLUDED, not included empty; v1-v4 triage batches excluded by default.
* `run_specialist_sweep.sh` — train each family from production at nc=208,
  free and with `freeze: 22`, per-epoch checkpoints.
* `merge_class_head.py --export-rows / --import-rows` — a specialist's whole
  transferable artifact as a ~10 KB npz instead of an 88 MB checkpoint. This
  round's box uploaded at ~100 KB/s; the fleet as checkpoints would have been
  2 GB and was 356 KB as rows.
* `compose_specialists.sh` — chain grafts: family 1 onto production, family 2
  onto that, etc.

## 2. Composability: CONFIRMED, bit-exactly

Grafting a specialist's rows into production leaves every non-grafted class
IDENTICAL on the 30 held-out cells — noteheadBlack 142, beam 126, ledgerLine
31, clefG 12, column after column across five different grafts
(`class_inventory` runs r6/r6e0). The frz specialists were trained FROM
production with `freeze: 22`, so their rows are readouts of production's own
features and drop in exactly. A 5-family composite built in seconds
(`composite5_frz.pt`). **The ensemble-in-one-model mechanism works.**

## 3. The specialists themselves: every one kills its own class

| graft onto production | its own class, before → after |
|---|---|
| ties (e0 AND e4, frz AND free) | tie 19 → **0** |
| rests (e0, frz) | rest8th 12 → **0**, restQuarter 7 → **0** |
| accidentals (e0, frz) | accidentalSharp 15 → **0**, accidentalNatural 8 → **0** |
| hollow (e0/e4, frz/free) | survives — 28 classes, 0 collapsed |
| slurs (e0, frz) | "survives" — ⚠️ see below |

⚠️ **The slurs "survival" is screen blindness, not survival.** Production reads
**0 slurs on the 30 held-out dense cells** (checked in the inventory JSON), so
a suppressed slur class cannot show up there — the cells are Beethoven
orchestral bars with almost no slurs. Given the slurs corpus has the WORST
residue of all (61% of teacher-visible slurs unboxed), the honest reading is
that only **hollow** demonstrably survives, and every specialist whose corpus
fails the residue test should be presumed suppressed until screened on cells
that actually contain its symbol.

Epoch 0 with a frozen backbone+neck is ~10 optimizer steps touching only the
head — and the class still zeroes. Not drift, not warmup, not scale: the LABELS.

## 4. The diagnosis, measured: the corpora accuse their own symbol

`/tmp/probe_spec_residual.py` (committed inline below) runs the production
teacher over each specialist corpus and counts its family's detections vs the
human boxes:

| family | cells | human boxes | teacher sees | unboxed | % unboxed |
|---|--:|--:|--:|--:|--:|
| hollow | 398 | 318 | 444 | 126 | 28% |
| ties | 164 | 102 | 245 | **143** | **58%** |

| slurs | 164 | 67 | 172 | **105** | **61%** |

(rests and accidentals land in `specialist_residual.json` when the probe
finishes.)

**58% of the ties the teacher can see in the ties corpus are unboxed.** The
`inspected_passes` stamp says a human swept the cell for ties; the ink says
half of them were missed or the stamp's palette claim is too generous. Every
unboxed tie is a hard negative aimed at exactly the class the specialist
exists for, and with ~100 positives against ~143 negatives-that-are-really-
positives, suppression is the correct thing for the loss to learn. Hollow
survives at 28% residue; ties dies at 58% — the boundary is somewhere between.

⚠️ The teacher count is an UPPER bound (it has false positives — production's
`restWhole`-on-slur-arcs mode is documented), so read the % as ceiling. But a
ceiling of 58% on the corpus's own subject is disqualifying either way.

## 5. What this means

1. **The mechanism is proven; the corpora are not clean enough to use it yet.**
   Composing grafts works exactly. What failed is the assumption that a
   stamped pass = complete labels for its palette.
2. **The path to a working specialist is teacher-reconciliation of its corpus**:
   run the teacher over the family's cells, surface disagreements (teacher-sees
   / human-didn't-box) for a human to adjudicate — the same reconcile-and-audit
   pattern the pre-fill work already built for noteheads. For ties that is ~143
   candidate boxes to look at, an hour, not a campaign.
3. **Hollow's specialist survives**, consistent with it being the one family
   whose sweep was audited and completed. It is also redundant — round 5's
   candidate already carries its rows.
4. ⚠️ **Do not gate a specialist on axis-2/OMR-NED alone**, for the same reason
   as ever: a specialist that suppresses emits less and is flattered.

## 6. Loose end

`freeze22` (head-only fine-tune of the full round-5 mix, from the base) trained
fine but its full checkpoint could not be pulled — the box's uplink degraded to
~100 KB/s and two attempts truncated (37 MB of 88). Its trained rows ARE local
(`freeze22_e0_all.npz`, all 119 classes), so the checkpoint is reconstructable
onto the base up to the box-regression branch. Not blocking: the per-family frz
arms answer the composability question more directly, and did.
