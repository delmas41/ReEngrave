# Can classical CV read hairpins? — the probe says yes

*2026-09-04. The question Sean asked and the one this had to come back to: not
"how would we build it" but **can we**. Answered by probe, before any detector.*

**Yes, on the evidence here.** The ink is present and well formed on a real
scan, and two shape tests already cut 471 band components to **69 candidates
that are visibly dominated by hairpins**, on a page where the YOLO detector
found **one**.

---

## 1. The baseline this is against

| | truth | detected |
|---|--:|--:|
| engraved, exact page truth | 3 | 3 — reading F1 1.000 |
| 11 scanned pages, `<wedge>` (2 per hairpin) | **198** | **1** |

Brahms 1 p2 encodes 136 wedges — ~68 hairpins — and the detector reads one. A
hairpin is a thin diagonal line, which is the shape Phase 4f moved stems and
beams to classical CV for, on the stated grounds that YOLO bounding boxes are
structurally bad at thin lines. Hairpins are the member of that family left
behind.

## 2. The ink is there, and it is clean

A 600 dpi crop of that page's inter-staff band shows `<` and `>` with **straight
arms and connected apexes**, sitting where the placement rule says — below the
staff, beside the slur arcs and the `espr.`/`arco` text. This is not a
degradation problem. The detector simply is not firing.

## 3. What separates a hairpin from a slur — measured, one test at a time

The band below a staff is full of arcs reaching down from the notes above. Two
tests were proposed in the scope; only both together work.

**Per-column vertical extent** — `h(x) = max_y(x) − min_y(x)`. A single stroke
gives its own thickness at every column however much it curves; two arms with
air between them give the distance between the arms.

⚠️ **On its own it is REFUTED.** Of 312 band components, **302** clear an open
extent of 0.4 staff spaces, against ~68 hairpins on the page. Extent says a
component is tall *somewhere*; it does not say it is a wedge.

**Outline straightness** — fit a line to the top outline and to the bottom
outline, and take the worse rms. A hairpin's two arms are straight; a slur is
one curved stroke, so both its outlines are arcs and neither fits a line.

**Together:**

```
471 components with measurable outlines
     ↓  open extent ≥ 0.5 sp  AND  outlines straight within …
  0.05 sp →  19 candidates
  0.10 sp →  69 candidates      ← against ~68 hairpins on the page
  0.15 sp →  98
  0.20 sp → 130
```

Rendered and inspected, the 69 are **overwhelmingly `<` and `>` wedges**, with a
handful of solid beam-like bars mixed in.

⚠️ **The 69-against-68 agreement is suggestive, not a score.** There is no
positional truth for a scanned page, so this is a count against a count — the
encoding's hairpins against our candidates — and they could agree while pairing
badly. It says the order of magnitude is right and the filter is not producing
noise; it does not say 69 correct.

## 4. What did NOT work, so nobody retries it

⚠️ **Fill ratio does not remove the beam-like contaminants.** A hairpin is two
thin lines with air between them, so a low fill seemed the obvious way to reject
a solid beam. Measured over the 69 candidates, fill runs **p10 0.375, median
0.437, p90 0.737** — nothing survives below 0.35. A long shallow hairpin is much
denser than the intuition suggests: its bbox height is the *opening*, and along
most of its length the two arms are only a few pixels apart.

**The discriminator that should work is already implemented, in
`line_detection.detect_beams` step 4: a beam has at least two STEM ENDS on it,
and a hairpin has none.** That rule was introduced for exactly this problem —
"without step 4 the count is dominated by things that are horizontal but are not
beams — slurs, ties, ledger lines, staff-line residue" — and it removes four
classes at once without a rule per class.

## 5. ⚠️ Bugs this probe had, both of which would have sunk it silently

1. **Erasing the span detections wiped the hairpins.** The first cut blanked
   *every* detection box before looking at the band. A slur, tie or beam box is
   mostly the paper its arc crosses, so blanking it erased whatever stood under
   it — in this band, the hairpins. `direction_text` documents the same rule and
   avoids the same trap (`max_blank_width_spaces`): the probe now skips spans.
2. **Half the discriminator was implemented and reported as the whole.** The
   first run measured extent only, found no separation, and would have read as
   "CV cannot do this" had it stopped there.

## 6. What this does and does not establish

**Does:** the ink is available on a real scan; a two-test shape filter isolates a
candidate set of the right size that is visibly mostly hairpins; the remaining
contamination has a known, already-implemented discriminator.

**Does not:** any accuracy figure. One page, one publisher, no positional truth.
⚠️ **Do not tune these constants on this page** — this project has twice refused
CV discriminators that separated on one edition and inverted on another (ink
coverage for time signatures, the tenor symmetry floor for clefs). The next step
is a second publisher, then the stem-end veto, then a reader.

```bash
python3 benchmarks/omr-hairpin-cv-2026-09/probe_band_ink.py \
    --pdf <scan.pdf> --page N --transcription read.json \
    --out-dir out/ --json-out band.json
```

Design and the surrounding decisions:
[docs/scope-cv-hairpin-detection-2026-09-04.md](../../docs/scope-cv-hairpin-detection-2026-09-04.md).
