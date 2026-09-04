# Auditing the labels the parity auditor cannot see (2026-09-03)

`../omr-cell-grid-tilt-2026-09/audit_labels_vs_measured_grid.py` audits
INSIDE-staff parity and found the campaign in good shape (3 disagreements in
331 labels). `audit_ledger_zone_labels.py` covers the two blind spots beside
it, and both were found the hard way on the Brahms 1 / Breitkopf completion
pass.

## 1. Ledger-zone parity — measure the INK, never the BOX

Out-of-staff noteheads are where the click-to-box snap extrapolates the
parity grid past the staff and can hand the labeler the wrong
OnLine/InSpace. On the Brahms completion pass: **6 suspect of 76
ledger-zone labels (~8%)**, against **0** inside-staff parity errors in the
same cells.

⚠️ **A click-placed box inherits the slot the snap chose**, so its centre is
biased toward the grid that placed it — measuring parity at stored box
centres re-measures the old grid rather than testing it. This is already
recorded from the snap-ledger work, and it bit again anyway: the
scanned-weights session checked three of these labels at box centres, read
`InSpace` for two, and was wrong on both — rendering the cells with the
half-space grid drawn showed a printed line running through each head. The
parity here therefore comes from the notehead's own ink blob on
`*_nostaff.png`. Three independent methods were tried on these cases and
only the blob one is trustworthy:

| method | result |
|---|---|
| ink inside the HUMAN's box | says the human is right, every time |
| ink inside the PRE-FILL's box | says the pre-fill is right, every time |
| **blob on the staff-removed image** | **agrees with the rendered grid** |

The first two are not evidence — each box biases its own centroid, which is
the same trap in miniature.

## 2. Shape vs class — what no parity audit can catch

A rest labeled as a notehead has no parity to be wrong about. The
discriminator is the box's own geometry, and the populations do not overlap:
the whole rest mislabeled `noteheadBlackInSpace` on the Brahms pass measured
**2.13 × 0.72 staff spaces, aspect 2.97:1**, against a median black notehead
in the same batch of **1.19 × 1.00, aspect 1.19:1** (n=189). That label sits
INSIDE the staff, so neither parity auditor would ever have reached it.
Credit to the scanned-weights session for the discriminator.

## Validation, and the campaign-wide result

Run against the Brahms batch's pre-correction verdicts the tool reproduces
**exactly the 7 corrections** that were made by hand — 6 parity + 1 shape —
and against the corrected verdicts it reports **0**.

Over every labeling batch (**1666 human labels, 275 in the ledger zone**):

- **19 ledger-zone parity candidates = 6.9% of ledger-zone labels**, which
  corroborates the Brahms 8% on eight batches the method was not tuned on;
- **3 shape-vs-class candidates**, all wide flat blocks labeled as
  noteheads.

⚠️ **These are CANDIDATES for a human, not corrections.** The tool writes
nothing. Read `box_is_Npx_from_ink` before believing a row: a large value
means the nearest notehead-sized blob may not be the glyph that was labeled
(`beet5-p6-sys0-s8-m13` at 106px is the clearest suspect-of-a-suspect),
while the rows where the box sits on the ink and the parity still disagrees
are the strongest. `off-grid` is the second filter — the tool already
refuses anything above 0.35.

## The rung-merge failure mode, and why the raw 6.9% overstates the true rate

The scanned-weights session ran this tool on the Simrock/Dvořák 9 batch —
110 cells, cut, selected and labeled entirely AFTER this tool existed, the
first genuine out-of-sample test. It flagged **7 of 102 ledger-zone labels
(6.9%)**, reproducing the Brahms rate closely. Adjudicated by hand, one by
one: **6 were false positives and 1 was real.** Post-adjudication true rate
on that batch: **~0.9% (1 of 759 boxes)** — an order of magnitude below the
raw flag rate, and the real one (`dvorak9-p11-sys1-s27-m0`) was worth
finding precisely because nobody would otherwise have looked for it.

**The mechanism, independently reproduced on the actual pixels**
(`dvorak9-p12-sys1-s26-m7`, four heads): a printed LEDGER LINE survives
staff-line removal (it is not a staff line, so `remove_staff_lines` leaves
it) and, on this scan, print-merges into the SAME connected component as
the notehead it sits beside — touching or overlapping it, sometimes with
the stem too. `blob_centre`'s centroid is then pulled toward the rung's own
mass, by up to a full half-step: measured `step ≈ 10.1–10.25` (rounds to
OnLine) against a true centre of `step ≈ 10.8–11.0` (InSpace, matching both
the stored label and a careful manual re-derivation). Confirmed by
rendering each cell with the exact known staff/ledger step positions
overlaid — no algorithm, just the printed pixels against arithmetic — which
is the same standard the 6 Brahms corrections were held to and passed.

**Five candidate fixes were tried against BOTH datasets, and none
generalises — recorded here so nobody re-tries them without the numbers:**

| candidate | Brahms (6 confirmed-correct) | Simrock (4 known false positives) |
|---|--:|--:|
| current shipped `blob_centre` | 6/6 | 0/4 (the bug) |
| row of maximum local width ("peak row") | 2/6 | 4/4 |
| trim rows > 1.3× the component's own median width | 6/6 | 0/4 |
| binary erosion (3–8px) before centroid | 3–5/6 | 0/4 |
| component width > threshold (1.6–2.0sp) as a reject flag | — | flags 4/4 real, but also 40/76 Brahms labels that are correct |
| literal peer proposal: keep rows whose ink run *through the box's own centre column* stays under ~1.6× the box width | 0/6 | 4/4 |

The last row is the peer's own proposal, implemented as literally
described. It resolves Simrock perfectly and breaks Brahms completely, and
the reason is diagnostic in itself: **it only has room to work where the
human's drawn box carries generous padding around the head.** Simrock's
boxes do (there is slack for the rung's excess width to become visible
inside the box); Brahms's are drawn tight to the ink (a box's own edge can
sit within a few px of the head, so the "row's run" saturates at the box
width on nearly every row regardless of what's really there), and the
filter silently degenerates to plain box-centroid — already the least
reliable measure of all, per the very first finding in this document.
**Box-padding convention is therefore a hidden confound on any fix built
from box-relative geometry**, and differs across labelers/batches without
being recorded anywhere.

`blob_centre` now returns the winning component's `height_sp`/`width_sp`
alongside its centroid, and the tool prints them next to every parity
suspect — **as context, not a verdict.** ⚠️ Width alone does not separate a
rung-merge from a normal label: the four Simrock false positives measure
1.91–2.14sp wide, but so do 40 of Brahms's 76 ledger-zone labels, all
independently uncontested. Nothing here is filtered or reweighted by it.

**Standing recommendation, now on two independent adjudications rather than
one:** every candidate this tool prints needs a HUMAN looking at the actual
ink against the known staff/ledger positions — rendering the cell with the
true step lines overlaid, the same check both this file's Brahms
corrections and the Simrock false positives were settled by. No
second-order geometric re-measurement substitutes for it. Read a raw
flag rate as an UPPER BOUND on the true defect rate, not the rate itself —
Simrock's 6.9% raw against 0.9% true is the calibration to keep in mind
when the campaign-wide 19 parity candidates are eventually adjudicated.

```bash
# from the MAIN checkout — cells/*.png are gitignored, absent in a worktree
python3 benchmarks/omr-snap-ledger-2026-09/audit_ledger_zone_labels.py
python3 benchmarks/omr-snap-ledger-2026-09/audit_ledger_zone_labels.py \
    --batch benchmarks/omr-labeling-simrock-2026-09
```

The Simrock batch is the honest next test: same publisher family, drawn
from scratch, and not one of the batches any of this was developed on.
