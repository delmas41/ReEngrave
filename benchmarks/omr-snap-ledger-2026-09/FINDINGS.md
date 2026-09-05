# The click-to-box snap guessed ledger territory — now it reads the rungs

**Defect (Sean, from the hollow campaign):** the single-symbol UI's
click-to-box sometimes suggests *on-line* for a note that is in-space — on
LEDGER LINES only, never inside the staff.

**Verdict: confirmed, mechanism measured, fixed.** Inside the staff
`snap_to_staff` anchors on the cell's own measured line positions; beyond it,
it extrapolated at the median staff spacing — and ledger pitch is a fact
about the ENGRAVING, not derivable from the staff. The fix reads the ledger
rungs off the cell image at the clicked x (`tools/omr/annotate/ledger_grid.py`)
and anchors the outside grid on them, exactly the move the inside grid
already makes. In-staff behaviour is untouched (asserted over all 214
in-staff labels and pinned by `tools/omr/tests/test_ledger_snap.py`).

Ground truth throughout: the hollow-campaign verdicts — **357 labeled
noteheads over 10 batches / 9 publishers** (hollow-2026-08 + hollow2 ×5 +
hollow3 ×4), Sean's final classes vs the box centres as stored.

```bash
python3 benchmarks/omr-snap-ledger-2026-09/probe_snap_ledger.py   # defect + mechanism
python3 benchmarks/omr-snap-ledger-2026-09/eval_fix_on_verdicts.py # fix vs alternatives
python3 benchmarks/omr-snap-ledger-2026-09/diag_render_rows.py DIR # annotated crops
```

## 1. The failure profile is exactly the report

Re-running the exact server snap on every labeled box centre
(click-placed boxes only — centres the UI itself put ON the old grid, so a
stored class that disagrees is Sean explicitly pressing `c`):

| zone | n | disagree | rate |
|---|--:|--:|--:|
| inside the staff | 194 | 9 | **4.6%** |
| 1st ledger zone | 60 | 2 | 3.3% |
| 2nd ledger zone | 42 | 16 | **38.1%** |
| 3rd+ ledger zone | 28 | 11 | **39.3%** |

Fine inside and at the 1st ledger, breaks at the 2nd and beyond — and these
are **lower bounds**: a wrong suggestion Sean did not notice leaves no trace.
Two such silent misses were found by eye (§4).

## 2. The mechanism: ledger pitch is publisher-dependent, in BOTH directions

Measured off the ink of the labeled cells (a rung = thin band of long
horizontal spans crossing the note's x), 185 rung gaps over 117 notes:

| gap | n | median (× staff spacing) |
|---|--:|--:|
| edge line → 1st ledger | 105 | **1.055** |
| 1st → 2nd | 49 | 1.020 |
| 2nd → 3rd | 26 | 1.017 |

By publisher (all gaps pooled): Litolff hi-res **1.102**, hollow-08 Litolff
1.135, Eulenburg 1.050, Jurgenson 1.055, Universal 1.030 — but Breitkopf
**0.975**, Peters **0.977**, Simrock 0.975, Novello 0.975. The first gap is
systematically the widest; p90s reach 1.25–1.30. A parity flip needs a
quarter-space of accumulated error, so the 2nd-3rd ledger is exactly where
±5–13% per space (plus warp and click offset) starts flipping.

**This kills the corrected-constant fix before it is built**: no single
factor serves 1.10 and 0.975 at once. Swept anyway (§3) and it loses.

## 3. Fix vs alternatives, on all 357 rows

`measure_ledger_rungs` walks outward from the staff's measured edge line,
one rung per space (window 0.65–1.35 of the local pitch), and
`snap_to_staff(…, ledger_rungs=)` anchors line slots on the measured rungs,
spaces on their midpoints, extrapolating at the *last measured gap* past the
ladder — but only within one half-step of it: a real note has ledgers
printed all the way to it, so **a click beyond an incomplete ladder's reach
falls back to the old grid** (the ladder lost the trail; extrapolating a
whole ladder from one nearby rung measured worse than the constant).

Judged at the stored centres against Sean's classes:

| zone | baseline | **ink (shipped)** | const-1.03 | const-1.05 | const-1.08 |
|---|--:|--:|--:|--:|--:|
| inside (214) | 94.4% | 94.4% | 94.4% | 94.4% | 94.4% |
| 1st ledger (66) | 95.5% | **97.0%** | 95.5% | 95.5% | 95.5% |
| 2nd ledger (47) | 57.4% | **70.2%** | 59.6% | 61.7% | 66.0% |
| 3rd+ (30) | 60.0% | **66.7%** | 63.3% | 63.3% | 43.3% |

Transitions on the 143 out-of-staff rows: ink **recovers 16, breaks 7**;
const-1.03/1.05 recover 2/3 (breaking 0) and const-1.08 nets −1 — the
constant is dead, as §2 predicted. 117/143 rows had at least one measured
rung on their side; the 26 without fall back to the old grid (no
regression possible there, and no improvement either — see §6). A rung read
costs **3.4 ms** per click.

⚠️ **The stored centres are systematically HOSTILE to the fix**, so those
numbers are a floor. Click-placed boxes were re-centred onto the OLD grid's
chosen slot — distance zero to the old suggestion — so every marginal case
scores for the baseline, and a "break" may be an artifact of re-snapping a
displaced point no real click would produce. Two bias-free views agree the
fix is better than the transition table says:

- **Sean's 29 explicit `c`-press overrides** (the defect as he experienced
  it): the fixed snap now suggests his class on **13/29**. The rest are
  mostly reader abstentions (rungs=[]) that keep the old behaviour — no
  worse than today.
- **The 13 hand-positioned boxes** (centres free of the old grid — the only
  unbiased subset): baseline **7/13**, ink **10/13**.

## 4. The 7 "breaks", adjudicated by eye (crops via `diag_render_rows.py`)

| row | verdict |
|---|---|
| schehe-p3-s3-m3 WholeOnLine d=2.0 | **WRONG LABEL — ink is right.** The head hangs in the space below its single ledger; no line through it. The old snap suggested OnLine at the click and Sean didn't notice — a silent miss of exactly the defect's kind, shipped into v8. |
| schehe-p4-s2-m0 WholeInSpace d=2.5 | **Probable wrong label** — ledger wings poke through the head's middle (caveat: a whole's own pointed tips mimic short wings). |
| mahler5-p178-s16-m8 WholeOnLine d=2.0 | **Artifact.** The measured rungs sit on the two real ledgers; at the note's true centre ink answers OnLine = the label. Only the displaced stored point flips. |
| tchaik1-p42-s15-m6 HalfInSpace d=2.5 | **Artifact** — same shape; at the visually-read true centre ink agrees with the label. |
| schehe-p3-s2-m1 HalfInSpace d=1.5 | **Artifact** — tangent note; stored centre sits a quarter-space below the head's centre. |
| mahler1-p1-s14-m1 WholeInSpace d=3.5 | **Real miss.** A head TANGENT on its ledger merges rim+rung into one band and the measured centre drifts ~0.3 spaces into the head. |
| schehe-p3-s3-m0 WholeOnLine d=2.0 | Unresolved — degraded solid-ish whole, single rung read, geometry ambiguous at this resolution. |

Net: **2 wrong labels (the fix corrects them), 3 artifacts, 1 real miss, 1
unresolved.** The wrong labels are a data-quality finding for the v8
training export in their own right.

## 5. Built and REFUSED (measure, don't keep)

- **Corrected constant pitch** (§3): cannot serve both signs of the
  publisher spread; best variant recovers 3 of 29 wrongs.
- **Wing recentring** — centre a merged band on the columns a head cannot
  reach. Zone 0.55–1.1 spaces out: recovers 10 / breaks 13 (a WHOLE note is
  1.72 spaces wide — its own rim reaches 0.55 and re-imports the pollution).
  Zone 0.9–1.1: 16/10. Both worse than the peak-span subband alone (16/7).
- **Counter-centroid evaluation points** — de-bias the eval by re-deriving
  each note's centre from its white counter. Three variants all flipped
  10–15% of the *inside-staff* rows, where the grid is measured-correct and
  boxes sit on real notes: refinement noise exceeds a quarter-space on this
  corpus (degraded counters are WHY these cells were labeled). Kept in the
  eval output as a second table, not trusted for decisions; the per-row
  visual adjudication in §4 replaced it.

Three reader rules exist because their absence was measured to fail, not by
design foresight: **gap-bridging** (a rung THROUGH an on-line hollow head is
split by the white counter; contiguous-run detection was blind to exactly
the rung that matters most, and 0.55 spaces of bridge — a half's counter —
still split a whole's wide oval, hence 0.90); the **peak-span subband** (once
gaps bridge, a whole note's body rows all qualify and the merged band is
fatter than the 0.40-space thinness cap — rejecting it outright collapsed
rung coverage 116→69 of 143; the rung is the widest thing in its band, so
only the peak rows must be thin); and **Otsu `<=`** (a binary image splits at
t=0 and `<` selects nothing).

## 6. What remains, honestly

- **26/143 out-of-staff rows read no rungs** (faint/low-res: Jurgenson
  low-res scan, the 2026-08 Litolff batch's small cells) and keep the old
  error rate by fallback. The lever there is the reader's robustness on
  degraded ink, not the grid.
- **The 9 inside-staff disagreements (4.6%)** cluster in a few cells
  (dvorak9-p8-s4-m12 ×2, mahler1-p4-s0/s1-m9 ×3…) — consistent with
  mis-measured `staff_line_ys_canonical` on those specific cells, a
  different defect this work deliberately does not touch (in-staff snapping
  is measured correct in aggregate and frozen by test).
- The ~30 ledger-zone labels where the OLD snap's suggestion stood
  unexamined (§1's lower-bound caveat) deserve a re-audit before the next
  training round — §4 found 2 wrong of the 7 it examined.
