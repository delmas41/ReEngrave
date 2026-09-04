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

```bash
# from the MAIN checkout — cells/*.png are gitignored, absent in a worktree
python3 benchmarks/omr-snap-ledger-2026-09/audit_ledger_zone_labels.py
python3 benchmarks/omr-snap-ledger-2026-09/audit_ledger_zone_labels.py \
    --batch benchmarks/omr-labeling-simrock-2026-09
```

The Simrock batch is the honest next test: same publisher family, drawn
from scratch, and not one of the batches any of this was developed on.
