# Can classical CV read hairpins? — the probe says yes

*2026-09-04. The question Sean asked and the one this had to come back to: not
"how would we build it" but **can we**. Answered by probe, before any detector.*

**Yes, on the evidence here.** The ink is present and well formed on a real
scan, and three tests cut 471 band components to **44 candidates that are almost
all `<` and `>` wedges**, on a page where the YOLO detector found **one**. Two
of the three are shape; the third, and the sharpest, is that **a hairpin touches
nothing** (§3b).

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

## 3b. ⚠️ The third test, and it is the best one: a hairpin touches NOTHING

*Sean's, and it beats what the scope proposed.* **A beam is always connected to
something — its stems. A hairpin is connected to nothing.**

The scope came at the contaminants from the beam's side: reuse
`detect_beams`' "at least two stem ends" rule. That works but needs stems found
first. This is a property of the *hairpin*, so it needs nothing found first.

⚠️ **It has to be measured on the WHOLE PAGE, not the band crop.** A beam dipping
into the band is cut off by the crop, its stems are above the cut, and inside the
crop it looks exactly as isolated as a hairpin does.

Applied to the 69 shape candidates, `full-page component area / candidate area`:

```
   p25   1.0x        44 isolated — the component IS the candidate
   p50   1.0x
   p75   3248.0x     25 attached — part of the page's single giant ink mass
   p90   9167.3x
```

**Nothing lies between 1× and 3248×.** That is what a constant read off a gap
looks like, and it is a binary rather than a threshold.

Rendered and inspected, the split is what the rule predicts: **the 44 isolated
are almost all `<` and `>` wedges; the 25 attached are almost all beams with
their stems, plus a few text fragments.**

⚠️ It costs some recall, honestly: a couple of real hairpins appear in the
attached set, having touched a slur or a staff line, and one trill squiggle
survives in the isolated set — a wavy line is isolated too. Isolation removes
beams; it does not by itself remove everything else.

## 4. What did NOT work, so nobody retries it

⚠️ **Fill ratio does not remove the beam-like contaminants.** A hairpin is two
thin lines with air between them, so a low fill seemed the obvious way to reject
a solid beam. Measured over the 69 candidates, fill runs **p10 0.375, median
0.437, p90 0.737** — nothing survives below 0.35. A long shallow hairpin is much
denser than the intuition suggests: its bbox height is the *opening*, and along
most of its length the two arms are only a few pixels apart.

The discriminator that does work is **isolation** (§3b) — and note that
`line_detection.detect_beams` step 4 is the same fact seen from the other side:
"a beam has at least two stem ends on it". That rule was introduced for exactly
this problem — "without step 4 the count is dominated by things that are
horizontal but are not beams" — but it needs stems found first, and isolation
does not.

## 5. ⚠️ Bugs this probe had, both of which would have sunk it silently

1. **Erasing the span detections wiped the hairpins.** The first cut blanked
   *every* detection box before looking at the band. A slur, tie or beam box is
   mostly the paper its arc crosses, so blanking it erased whatever stood under
   it — in this band, the hairpins. `direction_text` documents the same rule and
   avoids the same trap (`max_blank_width_spaces`): the probe now skips spans.
2. **Half the discriminator was implemented and reported as the whole.** The
   first run measured extent only, found no separation, and would have read as
   "CV cannot do this" had it stopped there.

## 5b. The second-publisher gate — and the test that matters is the BLANK pages

⚠️ One page and one publisher was never enough: this project has twice refused CV
discriminators that separated on one edition and inverted on another. Run
unchanged across the eleven scan-benchmark pages, which carry hand-verified
windows and therefore a truth wedge count:

| page | truth hairpins | candidates | YOLO |
|---|--:|--:|--:|
| bach-brandenburg3 p1 *(Peters)* | 0 | **0** | 0 |
| beethoven-5 575951 p1 *(Litolff)* | 0 | **0** | 0 |
| beethoven-5 575951 p2 | 0 | **0** | 0 |
| beethoven-5 984073 p1 *(Litolff)* | 0 | **0** | 0 |
| beethoven-5 984073 p2 | 0 | **0** | 0 |
| brahms-1 p1 *(Breitkopf)* | 0 | **1** | 0 |
| brahms-1 p2 | 68 | 44 | 1 |
| dvorak-9 p5 *(Simrock)* | 7 | 4 | 0 |
| dvorak-9 p6 | 4 | **4** | 0 |
| mahler-5 p2 *(Peters)* | 3 | 5 | 0 |
| mahler-5 p3 | 17 | 2 | 0 |
| **total** | **99** | **59** | **1** |

**THE ABSTENTION IS THE RESULT.** Six pages carry no hairpin at all, across four
editions and three publishers, and the filter returns **zero on five of them and
one on the sixth**. A shape filter loose enough to be useless would have fired on
every page; this one is silent where the music is.

On the pages that do carry hairpins it recovers **59 of 99 against the
detector's 1** — Dvořák p6 exact at 4 of 4, Brahms p2 44 of 68.

⚠️ **Mahler 5 p3 is the weak row: 2 candidates against 17.** Not explained here,
and it is the first thing a reader should be measured against rather than the
aggregate. Peters p2 on the same edition returns 5 for 3, so it is not the
publisher.

⚠️ Still a count against a count — no positional truth for a scanned page — so
"59 of 99" bounds the yield, it does not claim 59 correct.

## 6. What this does and does not establish

**Does:** the ink is available on a real scan, and a three-test filter — extent,
straightness, isolation — cuts 471 components to 44 that are almost all
hairpins. The contamination it removes is beams, by the cleanest rule in the
set.

**Does not:** any accuracy figure. There is no positional truth for a scanned
page, so every number here is a count against a count and none of them says
"correct". ⚠️ **The constants were not tuned across the corpus** — they were set
on Brahms p2 and then run unchanged, which is why the blank-page abstention is
evidence rather than a fit. Mahler p3's 2-against-17 is unexplained and is the
row to chase, not the aggregate.

```bash
python3 benchmarks/omr-hairpin-cv-2026-09/probe_band_ink.py \
    --pdf <scan.pdf> --page N --transcription read.json \
    --out-dir out/ --json-out band.json
```

Design and the surrounding decisions:
[docs/scope-cv-hairpin-detection-2026-09-04.md](../../docs/scope-cv-hairpin-detection-2026-09-04.md).
