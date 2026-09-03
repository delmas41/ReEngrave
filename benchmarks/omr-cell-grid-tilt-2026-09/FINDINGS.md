# A cell's stored staff lines are the staff's IDEAL lines — on a tilted scan, end-of-staff cells are up to half a space off

**Question (snap-ledger FINDINGS §1/§6):** 9 of 194 click-placed INSIDE-STAFF
labels disagreed with the snap suggestion, clustered in a few cells
(dvorak9-p8-s4-m12 ×2, mahler1-p4-s0/s1-m9 ×3, …). Inside the staff the grid
uses each cell's own `staff_line_ys_canonical`, measured-correct in aggregate —
so are THOSE cells' stored line positions wrong, and if so, where did the
geometry go wrong: the cell cutter or phase-1 staff detection?

**Verdict: confirmed for 8 of the 9 — the stored grid is displaced 0.25–0.55
staff spaces from the printed lines at those cells, and rebuilding the grid
from the printed ink reproduces Sean's class on all 8.** The 9th (beet5hr) has
near-correct geometry and is a tangent-note click ambiguity. The fault is
**phase-1's staff model, not the cutter**: `Staff.line_ys` is "five ideal
horizontal lines at integer rows" (`types.py`), the flagged scans' staves tilt
or bow **8–17 page px (0.3–0.65 spaces) across their width**, the ideal fit
crosses the real line mid-staff, and every measure cell of the staff inherits
the same five constants (`measure_extractor._build_measure_cell`:
`local_ys = staff.line_ys - y0`) — so **end-of-staff measures carry the full
residual, and the canonical cell frame cannot express it**. Every flagged cell
is an end-of-staff measure on a visibly warped staff (m9/m12/m5/m6 at the right
end; two m0 at the left end).

Scripts (paths hardcoded to this machine's main checkout + the
`peaceful-shamir-d12e52` worktree, where the snap-ledger probe and the hollow3
manifests live):

```bash
python3 benchmarks/omr-cell-grid-tilt-2026-09/diag_inside_staff.py OUTDIR   # cell-level: printed lines vs stored, overlays
python3 benchmarks/omr-cell-grid-tilt-2026-09/page_probe.py                 # page-level: residual vs x, recut reproduction
python3 benchmarks/omr-cell-grid-tilt-2026-09/audit_labels_vs_measured_grid.py  # all 225 inside-staff labels vs ink-measured grids
python3 benchmarks/omr-cell-grid-tilt-2026-09/render_candidates.py OUTDIR   # zoom renders for the silent-miss candidates
```

## 1. The 9, adjudicated against the ink

"Grid err" is the median displacement (printed − stored, in staff spaces) of
the five lines measured at the label's own x in the cell image. "Measured
parity" is the nearest half-step slot on the grid rebuilt from those printed
lines. Cell-level and page-level measurements (two independent rasters: the
labeled cell PNG re-binarized, and the 600 dpi page binary) agree within
0.03 sp on every row.

| label | grid err (sp) | measured parity | Sean |
|---|--:|---|---|
| dvorak9-p8-sys0-s4-m12 ×2 | **−0.55** | on_line ×2 | on_line ✓✓ |
| mahler1-p4-sys0-s1-m9 ×2 | +0.33 | on_line ×2 | on_line ✓✓ |
| mahler1-p3-sys0-s7-m5 | +0.36 | in_space | in_space ✓ |
| mahler1-p4-sys0-s0-m9 | +0.25 | on_line | on_line ✓ |
| brahms1-p2-sys1-s21-m6 | −0.40 | on_line | on_line ✓ |
| schehe-p4-sys0-s3-m0 | +0.28 | on_line | on_line ✓ |
| beet5hr-p48-sys0-s14-m0 | −0.11 (fine) | on_line | in_space ✗ — see below |

(dvorak's per-line matcher output reads +0.45 on lines 0–3 and −0.52 on line 4
— that is ALIASING: the true −0.55 displacement exceeds the 0.55-spacing match
window, so stored line k matches printed line k+1. The overlay render shows it
plainly: every stored line floats mid-space, half a space below its printed
line, and stored lines 3 and 4 bracket one printed line.)

**beet5hr is not a geometry case.** Its grid is off by only −0.11 sp; the
labeled whole note **straddles the bottom staff line and hangs mostly below
it**, the click landed in the head's upper half, and the UI re-centred the box
onto the line slot. Sean corrected the class (the head reads in-space); the
box centre still sits ~0.4 sp above the true head centre. Same family as the
tangent-note artifacts in the snap FINDINGS §4 — a click-point-vs-head-centre
limitation, only aggravated by the small grid offset.

**The 3 hand-drawn 2026-08 disagreements are the same geometry defect.**
beet5-p4-sys1-s14-m0/m1/m2 (excluded from the click-placed 194 by their
free-drawn centres) measure grid errors of 0.30–0.43 sp — one tilted staff,
three consecutive measures. Sean's classes are fine there because that batch
predates the suggester: he drew boxes and classes by eye. So all 12
inside-staff disagreements resolve: **11 geometry, 1 tangent-click.**

## 2. Where the geometry goes wrong — measured on the page

`page_probe.py` re-runs the cutter's exact phase-1 (600 dpi render →
`detect_staves` → `detect_barlines` → `extract_measures`) and traces the
printed line y at 21 x-positions across each flagged staff. The residual
(printed − `line_ys`) is a smooth **ramp**, near zero mid-staff, largest at
the ends:

| staff | residual left → right (page px) | at flagged measure | spacing | wander_px |
|---|---|--:|--:|--:|
| dvorak9 p8 s4 | +2 → **−15** | −15 (m12, right end) | 25.3 | 9.0 |
| mahler1 p3 s7 | −2.5 → **+13.6** | +9 (m5) | 26.8 | 10.0 |
| mahler1 p4 s0 | −2 → +10.5 | +7.5 (m9) | 26.5 | 8.5 |
| mahler1 p4 s1 | −1 → +11.5 | +9 (m9) | 26.2 | 9.0 |
| brahms1 p2 s21 | +3 → **−14** | −12 (m6, ~85% across) | 27.2 | 10.0 |
| schehe p4 s3 | **+7** → −1 | +6 (m0, LEFT end) | 22.0 | 7.0 |
| beet5hr p48 s14 | −4.5 → +9 | −4 (m0) | 30.8 | 8.0 |

Signs differ per staff (brahms/dvorak rise rightward, mahler/beet5hr fall,
schehe bows at the left), so this is per-staff tilt/bow of the scan, not a
global rotation the deskew could remove. mahler1-p4 s0 and s1 — two adjacent
staves — ramp together, which is why one measure column (m9) flipped labels on
both: the page's right side is warped as a region. The dvorak overlay also
shows the lines **bending ~10 canonical px within one measure** (the residual
is not even linear at the extreme).

**Today's phase-1 reproduces the stored geometry exactly.** The re-cut cells'
`staff_line_ys_canonical` equal the batch manifests' — byte-equal for the
mahler cells (pad grown to the 6-space ceiling either way), and offset by
exactly one spacing for the pad-4 batches because the probe patches
`PAD_*_STAFF_LINES = 5.0` the way `select_cells_orchestral` does while those
batches were cut at the pipeline's own pads (manifest top line at 4·spacing).
The defect is live, not stale batch data, and it is **not the cutter**: both
cutters copy `staff.line_ys − y0` — exact arithmetic — and it is **not a
mis-locked window** (`_refit_misaligned_group`'s failure shape is absent; the
lines match the right printed lines, modeled as horizontal).

**The pipeline already measures the thing it then discards.**
`measure_line_geometry` traces each line column by column
(`header_ink.measure_staff_line`) and keeps only thickness and max wander;
`line_wander_px` is 7–10 px on every flagged staff — at these spacings, ≥ a
quarter space, i.e. "parity can flip somewhere on this staff." The wander
UNDERSTATES the extremes (brahms measures 10 against an observed 14; the
trace window is about a third of a space, so wander saturates near it), and it
reaches the transcription JSON per staff but **not** cells.json — the labeling
UI has no way to know a cell's grid is suspect.

## 3. Impact on training labels — the campaign audited

`audit_labels_vs_measured_grid.py` re-measures the grid from ink at every
inside-staff added-notehead label across all 10 hollow batches (225 labels,
every one with a usable image):

- **|grid error| at the label: median 0.048 sp, p90 0.178, max 0.451; 15
  labels sit past 0.25 sp** — the parity-flip line. The worst-cells list is
  exactly the flagged cells plus their staff-neighbours (brahms1-p2-s20-m6 at
  0.40, lamer-p5-s2-m0 at 0.45, the beet5 s14 trio).
- **Box centres are bounded, classes are not.** Click-placed centres sit
  ≤ 0.25 sp from the nearest TRUE slot (median 0.05, max 0.248, none past
  0.25) — because a near-half-space grid error snaps the box onto (nearly) the
  true position of the *other* slot. The damage concentrates in the CLASS.
- **Two silent misses found — labels whose class equals the old grid's wrong
  suggestion** (Sean's 9 overrides were the ones he *noticed*; these he
  didn't):
  - **`brahms1-p2-sys1-s20-m6` noteheadHalfInSpace → should be
    noteheadHalfOnLine.** Grid −0.40 sp; the dotted half's centre sits 0.10 sp
    off the printed bottom line, margin 30 px — decisive. One staff above the
    s21-m6 label Sean *did* catch, same measure column, same warp. **Shipped
    in v8.** (Concurrent state, 2026-09-03: the ledger-zone audit on
    `claude/epic-chatterjee-9e8c7d`, commit `7fe2d7b`, corrected THREE
    Scheherazade labels — snap FINDINGS §4's two plus the formerly-unresolved
    row — and re-exported v8; this brahms label was the one wrong v8 label
    still standing after that. **FIXED same day**: `3baadcd` on
    `claude/score-labeling-training-system-iech0i` — batch verdict + survey
    `v8-merged-verdicts` + the v8 label line, class 30 → 28, decode-verified
    against the cell, which is 1603×1200, not s21's 1618.)
  - **`lamer-p5-sys0-s2-m0` noteheadWholeOnLine → should be
    noteheadWholeInSpace.** Grid −0.45 sp (the campaign's largest); the whole
    note floats dead-centre in the top space, 0.10 sp off the space slot.
    ⚠️ An earlier draft of this bullet said hollow3 was "not yet exported" —
    **stale since `780cbf6`**, which converted hollow3 to **v9–v12** (held out
    of the catalog): v11-2026-09-03-hollow3-lamer already carries this cell
    with the wrong class (32). v11's export source is
    `benchmarks/omr-labeling-survey-2026-09/phase2-merged/lamer/verdicts/` —
    a THIRD edit-both copy, the same trap as v8-merged-verdicts. The
    correction (32 → 34, three copies) landed as `c827279` on
    `claude/peaceful-shamir-d12e52` and was cherry-picked into the gate
    re-run's branch (§5), which confirmed it: the cell still tops the
    campaign's grid-error list (−0.45 sp) and its label now agrees with the
    measured grid.
  - A third candidate (`mahler1-p4-sys0-s0-m9` HalfInSpace) is a 2 px
    geometric coin toss; the figure is two half-note heads a FOURTH apart
    (line + space — the Mahler 1 fourths motif), which supports Sean's
    reading. Not a wrong label.

## 4. What follows (recorded, not implemented here)

- **Do not touch in-staff snap behaviour** — it is measured-correct where the
  stored geometry is correct, and pinned by `test_ledger_snap.py`. The defect
  is in the GEOMETRY the cells store, not in the snapping.
- The natural fix is at the source: a cell knows its own x-range at cut time
  and the trace machinery already exists (`measure_staff_line` follows the
  line column by column) — store per-cell line ys measured over the cell's own
  x-span, or carry a per-cell slope, instead of the staff-global constants.
  That would correct the labeling UI and `pitch_resolver` together.
- **The same defect feeds production pitch resolution.** `pitch_resolver`
  reads the same per-cell constants, so on warped scans every note in an
  end-of-staff measure is resolved against a grid up to half a space off —
  step-off-by-one pitches for whole measures (dvorak9-p8-s4-m12 at −0.55 sp is
  past the flip line for EVERY note in the bar). The engraved orchestral
  benchmark cannot see this — LilyPond pages are straight — which fits the
  scan-vs-engraved error gap. Worth its own measurement before any fix.
- `line_wander_px ≥ ~0.25·spacing` is a ready-made per-staff flag for "this
  staff's end cells are suspect" (all 7 flagged staves: 7–10 px). It just
  needs to reach cells.json / the annotate server if the labeling UI should
  warn.
- The brahms1 s20 v8 fix LANDED (`3baadcd`); the lamer fix LANDED (`c827279`,
  confirmed by §5's re-run). The remaining gate — **re-run the audit over the
  hollow3 batch set before v9–v12 enter `catalog-versions.txt`** (they were
  converted by `780cbf6` and deliberately held out) — was run 2026-09-03 and
  PASSED; see §5. ⚠️ The general trap, learned from `7fe2d7b` and
  confirmed on v11: **every exported version has its own merged export
  source** (v8 → survey `v8-merged-verdicts`, v11 → survey
  `phase2-merged/lamer/verdicts`), so a label fix edits the BATCH verdict,
  the version's export-source copy, AND the `labels/*.txt` line — and must
  NOT re-run the version builder (`build_v8.py` would pull the later Brahms
  completion-sweep boxes into v8) nor rebuild the catalog (training reads
  `labels/*.txt` directly). One residue the hand-edit leaves (fix session's
  finding): the version's `metadata.json` (`per_cell.classes_written`) still
  records the OLD class — provenance drift only, training unaffected; the
  clean resolution is a single converter re-run with the version's original
  arguments once all corrections are on main.

## 5. The hollow3 gate re-run — PASSED (2026-09-03)

Run in the `busy-curran-b250c5` worktree over the four hollow3 batches
(`universal-mahler1`, `novello-elgar1`, `jurgenson-tchaikovsky1`,
`durand-lamer`) at their v9–v12 state: batch `verdicts/` after `c827279`
(cherry-picked), whose `added_detections` were first verified identical to
the survey `phase2-merged/*/verdicts` export sources — the copies differ only
in `inspected_passes` / `labeled_at_utc` (and a few model-`detections`
lists), never in a human label. `audit_labels_vs_measured_grid.py` was
re-pointed for this run: repo-root-relative, the four batches, and cell
images from the **v9–v12 `images/` export copies** (the batches' own
gitignored `cells/` are absent in a fresh worktree; the export copies are the
same PNGs the labeling UI served, copied by the converter at `780cbf6`, and
they covered every audited cell — 0 lacked images, every one matched its
manifest's canonical height).

**68 inside-staff added-notehead labels; |grid error| median 0.053 sp, p90
0.196, max 0.451; 5 labels past the 0.25 sp flip line; box centres ≤ 0.246 sp
from the true slot (none past 0.25). Exactly 1 of 68 disagrees with the
measured grid, and adjudication on the ink says the LABEL is right — zero
label changes.**

- The 1 disagreement is `mahler1-p4-sys0-s0-m9` `noteheadHalfInSpace`
  (grid +0.25 sp, margin 2.1 px) — §3's "third candidate", the 2 px coin
  toss. The prior adjudication argued from the fourths motif; this run
  measured the ink. The head's counter is **one unbroken hole** (108×64 px —
  no printed line crosses it), centroid y 874.7 against the measured space
  slot at 872.5 — **2.2 px off the space slot**, 52 px from the measured
  line. Its partner head in the same figure straddles the printed line at
  723 (counter split by the line). So the pair reads line + space, a fourth
  apart — Sean's classes are correct on both, and the flag is the box-centre
  artifact §3 predicted: both boxes snapped onto the displaced STORED grid
  (747/847, exactly 1.0 spacing apart — a parity-impossible separation for
  the true fourth), so the InSpace box lands 24.1 px from the measured line
  slot vs 26.2 px from the measured space slot. Box centres stay valid as
  training boxes (0.24 sp off the true slot, inside the campaign bound); the
  class is what the audit protects, and the class is right.
- `lamer-p5-sys0-s2-m0` — the campaign's largest grid error, 0.451 sp —
  now AGREES: the audit itself confirms `c827279`.
- The other >0.25 sp rows (`mahler1-p3-sys0-s7-m5` 0.379,
  `mahler1-p4-sys0-s1-m9` ×2 0.324) are §1's adjudicated overrides, and the
  re-run confirms their classes agree with the measured grid.
- **Decode verification, all three copies:** every one of the four batches'
  **135 added noteheads** (inside- and outside-staff) appears in its
  version's `labels/*.txt` at the same normalized position and the correct
  class id under the converter's committed 208-name vocabulary
  (`deepscoresv2_208_classes.json`: HalfOnLine 28, HalfInSpace 30,
  WholeOnLine 32, WholeInSpace 34) — 135/135, including the corrected v11
  lamer line. ⚠️ Do not decode-check against `DEEPSCORES_V2_CLASSES`
  indices — the trained vocab sits 4 ids below it for the notehead block,
  and the first pass of this check "failed" 135/135 on exactly that.

**The grid-tilt gate on v9–v12 is cleared.** Admitting them to
`catalog-versions.txt` remains a training-time decision (the same open call
as v7, PROJECT_STATUS #13 for v5/v6) — but no longer blocked on this audit.
