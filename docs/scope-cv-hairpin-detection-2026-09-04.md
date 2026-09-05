# Scope: reading hairpins with classical CV

*2026-09-04. Scoped at Sean's prompting — "a hairpin is a thin line that moves
diagonally, and it is always underneath the measure it belongs to". Both halves
of that turn out to be load-bearing, and neither was being used.*

---

## 0. ⚠️ Read this first: what already exists, so nobody builds it twice

This got built twice **today**, by me, and the check that would have prevented it
is one command.

| half | status | where |
|---|---|---|
| `<wedge>` **export** | **DONE, unmerged** | `53e6f233` on `claude/mystifying-curran-613606` |
| staff **attribution** for hairpins | **DONE, unmerged** | same commit — a dedup veto keyed to notehead presence |
| ⚠️ my duplicate of the export half | **INFERIOR, on this branch** | `2ad144fb` — no attribution fix |
| **detection** | **UNCLAIMED** | nothing on any branch touches `line_detection` for hairpins |

`53e6f233` does everything my `2ad144fb` does and the attribution fix besides,
and it *improves* pooled OMR-NED (0.1304 → 0.1299) where mine costs +11 edits
for want of exactly that fix. **Take theirs.** Its findings live in
`benchmarks/omr-hairpins-2026-09/FINDINGS.md` (346 lines), and it independently
reports the same scan blindness this scope is about — "the detector fires on no
hairpin at all on any of the five scanned pages".

```bash
git log --all --oneline -S "<the thing you are about to build>" -- tools/omr/
```

`export_coverage.KNOWN_GAPS` said `wedge` was open, and it was — **on main**. An
unmerged branch is invisible to it, and to a worktree scan for *uncommitted*
changes, which is what I checked.

---

## 1. Why this is worth doing

**The detector does not see hairpins on scans.** Two independent measurements:

| | truth | detected |
|---|--:|--:|
| engraved, exact page truth | 3 | 3 — reading F1 **1.000** |
| 11 scanned pages, `<wedge>` in truth (2 per hairpin) | **198** | **1** |
| their 5 verified scan rows | — | **0** |

Brahms 1 p2's window encodes 136 wedges — 68 hairpins — and we read one.

⚠️ **The engraved number is what hid this**, and it hid it from me for a full
commit: F1 1.000 on n=3 clean pages says nothing about a thin line on a scan.

**The ink is there.** A 300 dpi strip of that page shows hairpins under the
Bratsche, Cello and Kontrabass staves — thin, diagonal, legible, unambiguous.
This is not a degradation problem; the detector is simply not firing.

**And it is the shape this project already moved to CV.** Phase 4f took stems
and beams out of the detector on the stated grounds that *YOLO bounding boxes
are structurally bad at thin lines*. A hairpin is a thin line, diagonal like a
beam, and it is the member of that family still left to YOLO —
`line_detection.py` has no hairpin path at all, and `staff_detector` mentions
hairpins twice, both times as something to **reject** when finding staff lines.

---

## 2. The design, and why it is not per-cell

**Run it in the inter-staff BAND, in page pixels, per staff.** Not per measure
cell, which is where every other detector here works. Two reasons, both measured
today rather than assumed:

1. **A hairpin spans measures.** Cells are cut per measure, so a per-cell reader
   sees fragments — exactly what makes the current export emit Mahler's one
   crescendo as two, and the same position slurs were in before
   `annotate_slurs_in_staff` paired them over the staff.
2. **The band belongs to exactly one staff, so attribution is correct by
   construction.** The current pipeline gets this wrong the other way round: 3 of
   Mahler's 4 hairpin detections are filed under staff 18 while standing in
   staff 17's band, and have to be rescued afterwards by a dedup veto. A reader
   that searches *staff N's band* never creates the contest.

**The band.** From the staff's bottom line + ~0.5 spaces to the next staff's top
(bounded at ~6 spaces). ⚠️ **The bound is measured, not assumed**: every hairpin
in the page truth sits below a staff and none inside one — **8 of 8** — and the
dynamic-letter population that shares this band runs +0.0 to +5.6 spaces with a
2.5-space empty gap under it (`benchmarks/omr-dynamics-band-2026-09`).

**The pipeline**, following `line_detection.detect_beams` step for step:

1. Binarise the band. Prefer the staff-removed image where available — a hairpin
   is *below* the staff, so staff-line residue is less of a problem here than it
   is for beams, but the band's top edge still clips them.
2. **Subtract what is already known.** `direction_text._blank_detections` does
   exactly this in page pixels and is reusable as-is: it blanks every detection
   so "find the hairpin" becomes "find the ink". That removes noteheads,
   dynamics letters, rests and the rest at a stroke.
3. Near-horizontal morphological opening → candidate strokes.
4. Connected components, filtered on width, height and aspect.
5. **The discriminator** (see §3).

---

## 3. The discriminator, and what will not work

**What is left in that band after subtraction is: hairpins, slur and tie arcs
reaching down from the staff, and words** (`pizz.`, `espr.`, `arco`, `dolce`) —
all visible in the strip.

⚠️ **Fill ratio will not separate a hairpin from a slur, and it is the obvious
idea.** `direction_text` already uses `min_fill_ratio = 0.16` to tell *text*
from *curves*; a hairpin is as sparse as a slur, so that gate puts them in the
same bucket. It does remove the words, which is worth having, but it is not the
answer.

**The answer is that a hairpin is TWO STRAIGHT ARMS MEETING AT A POINT, and a
slur is ONE CURVED STROKE.** For a candidate component:

| test | hairpin | slur / tie |
|---|---|---|
| top boundary fits a straight line | yes | no — it is an arc |
| bottom boundary fits a straight line | yes | no |
| the two boundaries CONVERGE | to a point at one end | roughly parallel |
| height at the closed end | ≈ 0 | ≈ the arc's thickness |
| height at the open end | ~1–1.5 spaces | ≈ the arc's thickness |

That is four cheap measurements on the component's own boundary profile, and
**the same measurement gives the DIRECTION for free** — apex on the left is a
crescendo, apex on the right a diminuendo. That is the one thing the class label
currently supplies and it would no longer be needed.

⚠️ **Validate the shape constants on at least two publishers before believing
them.** This project has refused two CV discriminators that separated cleanly on
one corpus and inverted on another — ink coverage for time signatures, and the
tenor symmetry floor for clefs (`clef_symmetry_populations.py`). A hairpin's
angle and length are engraving choices and will vary.

---

## 4. Acceptance — the harnesses already exist

| what | how |
|---|---|
| reading, engraved | `score_reading`'s `hairpin` family — currently truth 3 / detected 3, F1 1.000. **Must not regress.** |
| reading, scans | no page truth exists for a scan; score against the scan benchmark's `<wedge>` truth via `score_translation` |
| translation | `score_translation` — detected → exported → truth, per work |
| both metrics | `orchestral_eval --omr-ned` and the scan e2e; `score_export_arm.py` (in `53e6f233`) does a controlled A/B re-transcribing only the affected work |
| no collateral damage | pooled reading F1 0.919 and the 11-work OMR-NED |

**The bar to clear is low and should be stated plainly: 1 of ~99.** Anything
that reads hairpins at all on a scan is a large gain, and the risk is not
failing to beat the baseline — it is false positives in a crowded band making
the *rest* of the page worse.

---

## 5. Risks, in the order they are likely to bite

1. **False positives on slur and tie arcs.** The band is full of them. This is
   what the straightness test is for, and it is the thing to measure first.
2. **The words.** `pizz.`, `espr.`, `arco` sit in the same band. Fill ratio
   removes them, and `direction_text` already owns that gate.
3. **A hairpin between two staves is ambiguous to a human too** — the strip
   shows several sitting closer to the midpoint than to either staff. The band
   rule assigns it to the staff above by construction, which is right *for
   orchestral scores* and would be wrong for a vocal part with dynamics above
   the staff. Bound the claim to instrumental scores, as this project already
   bounds several others.
4. **It must be measured on SCANS.** Measuring only on engravings would repeat
   exactly the mistake this scope exists to correct.

---

## 6. First step — one probe, before any detector

**Do not write the reader first.** Take the scan pages whose truth carries
hairpins, subtract the known detections from the band, and characterise what is
left: how many components, how many pass the straight-arms test, and how many of
those coincide with a hairpin the truth says is there.

That answers the only question that decides the whole approach — *does the
straightness test separate hairpins from arcs in real band ink* — and it costs a
probe rather than a detector. It is the same discipline
`probe_cluster_too_big.py` brought to the clef locator: measure what the rule
would cost before making it a rule.

If it separates, the reader is a day's work on top of `line_detection`'s
existing shape. If it does not, the finding is worth more than the reader would
have been.
