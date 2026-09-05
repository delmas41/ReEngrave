# Does screen 1 reproduce across two scans of the SAME engraving?

**2026-09-05. MEASURED. Detector-free, ~9 min CPU, no pipeline code touched.**
Probe: [`probe_litolff_reproducibility.py`](probe_litolff_reproducibility.py) →
[`litolff-reproducibility.json`](litolff-reproducibility.json).

```bash
python3 benchmarks/omr-structure-rnd-2026-09/probe_litolff_reproducibility.py --n-pages 24
```

## Why this control, and why it is free

`imslp984073` and `imslp575951` are two scans of the **same Litolff 1870
plate** — a re-print, not a replication. For any printed page the ink is
identical, so the two scans **must** get the same screen-1 verdict. Every
disagreement is measurement noise in screen 1 itself, on the exact quantity
screen 1 reads.

The census validated screen 1 at **3 TP / 0 FP / 5 TN** and said so plainly:
"a clean result and a *tiny* denominator… **the 246 is a candidate count, not a
count of confirmed lineup changes**". This replaces five negatives with 23
reproducibility pairs. It is the same instrument that produced the census's
sharpest negative — screen 2 disagreeing with itself across these two scans —
turned on the screen we propose to **rely** on.

## The alignment, and the circularity avoided

`works.json`'s recorded `pdf_page_index` on the eight gate rows gives
**984073 pdf page N ↔ 575951 pdf page N−1** (984073 carries one extra
front-matter page).

⚠️ **`works.json` is used here ONLY as bibliographic alignment metadata — which
pdf page carries which printed page — never as a structural answer.** The
tempting alternative, picking the offset that maximises staff-count agreement,
is viciously circular: the reported quantity would be fitted to agree. The
offset was fixed **before any verdict was computed**.

**The alignment is independently corroborated by the run itself**: at this
offset, printed 2 reads `[11, 11]` on both scans, printed 3 reads `[11, 8]` on
both, and printed 4 reads `[11, 11]` on both — reproducing the 20-row gate's own
fixture counts for `-p2`, `-p3`, `-p4` on both editions.

⚠️ **The existing sweep could not answer this.** It sampled both scans at nearly
the same *pdf indices*, which under a +1 offset compares **different printed
pages**; only 6 of its 28 Beethoven rows happen to align. Hence a fresh run.

---

## The result

| | |
|---|--:|
| page pairs screened | 24 |
| screenable on both sides | 23 |
| abstain-status agrees | **24/24** |
| **screen-1 verdict agrees** | **20/23 = 0.870** |
| tier agrees | 20/23 = 0.870 |
| **raw staff counts identical** | **15/23 = 0.652** |

**Screen 1 does not fully reproduce across two scans of one plate: it disagrees
with itself on 13% of pages, and the underlying staff counts disagree on 35%.**

### All three disagreements run the same way

| printed | 984073 | 575951 | verdict |
|--:|---|---|---|
| 7 | `[8, 11]` → **A** | `[11, 11]` → none | A fires, B does not |
| 15 | `[8, 11]` → **A** | `[11, 11]` → none | A fires, B does not |
| 20 | `[8, 6]` → **A** | `[8, 8]` → none | A fires, B does not |

Tier-A totals: **984073 → 17, 575951 → 14**, over the same 24 printed pages.

In every case the firing scan read a **smaller first system** where the other
read a full one. That is the signature of **phase-1 under-detection
manufacturing a tier-A candidate**, not of a real lineup change — precisely the
mechanism census §6(b) named ("a 2-staff disagreement on a two-system page would
manufacture a tier-A page out of nothing"). ⚠️ The census's DPI control could
not see this: it varied rendering resolution on **one** scan, and this varies
the **scan**, which is the larger source of variation and the one a library
sweep actually encounters.

⚠️ **Which side is right is NOT established here.** Agreement is a lower bound on
correctness — two scans can make the *same* error — and adjudicating the three
requires rendering those pages and looking at them. Named, not done.

---

## What this means for the 246

**1. The 246 carries a ~13% verdict-level noise floor**, and it is **directional**
— the noise creates tier-A candidates rather than hiding them, because
under-detection lowers one system's count. So 246 is an **over-count** of
candidates, not a symmetric error bar. It remains a *candidate* count, which is
all the census ever claimed.

**2. It does not overturn the census's headline.** Even discounted, the library
holds far more informative pages for the **tacet-suppression** case than the
12–15 the design hoped for. The reading changes from "246 candidates" to
"a few hundred candidates of which roughly one in eight is a detection
artifact" — a queue to be triaged, which is what a queue is for.

**3. The queue must be de-duplicated by PRINTED page, not by pdf index.** These
two scans contribute **11 tier-A rows** to the 246 between them (6 from 575951,
5 from 984073) from **one engraving**. And because the sweep sampled them at
misaligned indices, those 11 largely represent *different* printed pages — so
de-duplication is a page-level join, not "drop one edition". Census §6(d)
flagged this; it is now quantified.

**4. Triage should prefer pages where BOTH systems are wide.** All three
disagreements involve a system read at 6–8 staves beside one read at 11–12. A
tier-A page whose two systems differ by a large margin is more likely a phase-1
failure than a lineup change — consistent with the census's own `doubtful`
heuristic, which fires only at ≤3-beside-≥6 and therefore misses this band.

---

## How this probe could have produced a falsely encouraging number

1. **The offset could be wrong**, which would compare unrelated pages and
   *understate* reproducibility. Mitigated: it comes from `works.json` rather
   than from a fit, and three independent printed pages reproduce the gate's own
   fixture counts on both scans.
2. **Agreement is not correctness.** 20/23 counts pages where the two scans
   agree, including any page where both are wrong the same way. This measures
   *reproducibility*, which is a ceiling on precision, not precision.
3. **n = 23 pairs, one engraving, one publisher.** A second re-print pair — if
   the library holds one — would test whether 0.870 is a property of screen 1 or
   of these two scans.
4. **300 dpi, matching the sweep.** The gate fixtures are 600 dpi, and the
   census measured staff counts moving between DPIs on dense pages. This
   number describes the sweep's own configuration, which is the right one to
   describe, but it is not a claim about phase 1 generally.
