# The fermata reaches the file — reach, result, and the control

2026-09-10. No flag. `fermata` was the **largest unwired family on the
record**: 63 detections on Litolff `984073` p1-3, with no quantity anywhere —
not a stub, not a `wants`, nothing declaring the absence. It is now gathered,
adjudicated and exported.

```bash
python3 benchmarks/omr-staged-fermata-2026-09/fermata_arm.py <staged.json>
```

---

## 1. REACH, before anything else

Measured off `Q.GLYPH_BOX` on records that **predate the quantity**, so this
number was available before a line was written.

| | Litolff `984073` p1-3 | Breitkopf Brahms 1 p0-3 |
|---|--:|--:|
| `fermataAbove` glyphs | **63** | **0** |
| `fermataBelow` glyphs | 0 | 0 |
| cells holding one | 46 | 0 |
| cells with **no notehead and no rest** for it | **9** | — |
| confidence | 0.254 / 0.807 / 0.911 (min/med/max) | — |

⚠️ **Brahms is ZERO, and the same script run there would print a clean,
meaningless line.** A change that moves nothing because it is inert and one
that moves nothing because the page holds nothing to move are the same number.
`fermata_arm.py` prints REACH first for that reason.

⚠️ **The 9 carrier-less cells are why `no_carrier` is a real population and
not a defensive branch**, and they are the reason the abstention exists at all.

---

## 2. WHAT IT DID — one record, exported twice

Litolff `984073` p1-3, `--pages 1-3`, hollow-graft weights. ⚠️ The record was
gathered on a **dirty tree** (`0982864e`, edits in flight), which is fine for a
reach-and-result report and **not usable as one arm of an A/B**; the arm says so
before it says anything else.

| | |
|---|--:|
| marks gathered | **63** |
| decided | **51** |
| abstained `no_carrier` | **12** |
| owner named a glyph the exporter never wrote | 1 |
| absorbed into an element another mark already wrote | 13 |
| **`<fermata>` elements in the file** | **37** |

`fermata_balance` holds: `written + not_written <= marks_in_log`, with the
remainder named. music21 reads back **37 Fermata objects, 20 of them on a
Rest**.

### 2a. ⚠️ 26 OF 51 CARRIERS ARE RESTS — the routing is not a taxonomy preference

| carrier | n |
|---|--:|
| **rest** | **26** |
| notehead | 25 |

`fermataAbove` carries the detector's **`ornament` category**, which it shares
with all ten `artic*` classes, `ornamentTrill` and `arpeggiato`. A
category-keyed router would have filed a pause as an articulation and then
applied the articulation attach rule — *nearest notehead on the side the class
names* — which **structurally cannot reach 26 of these 51**, and would have
mis-sided many of the rest: a `fermataAbove` over a whole-bar rest stands well
above ink it belongs to. `gather_glyph_families` is routed **by CLASS**, and
both directions of the confusion are tested.

### 2b. ⚠️ THE `nearest_in_bar` FALLBACK FIRED **ZERO** TIMES HERE

All 51 decisions are `contains_the_mark`. So on this document the fallback's
correctness rests on its unit test alone — **the page does not exercise it**,
and no claim is made that it is right on real ink. It is kept because the
legacy rule's own docstring says why it is load-bearing (a fermata over a
bar's only rest is engraved at the BAR's middle while the rest glyph sits at
its own centre), and because reporting the two branches APART is what will let
a cleanup count tell *stood over* from *stood nearest* when one does fire.

### 2c. ⚠️ THE 13 "ABSORBED" ARE DUPLICATE DETECTIONS, NOT CHORDS

The hoist rule is *one pause per event, on the chord's first `<note>`*, and it
was written for chords. On this document **all 13 absorbed marks are a second
detection of ONE printed fermata** — 13 carriers named by exactly 2 marks each,
heavily overlapping boxes, one confident and one not:

```
carrier glyph/1/0/8/1/6   fermataAbove x0=88  x1=389  conf 0.852
                          fermataAbove x0=77  x1=353  conf 0.754
```

So the hoist is doing DEDUPE work it was not designed for. That is a happy
accident and is named as one rather than claimed as design — and the 13 is a
**DETECTION** figure (the detector fires twice on one pause) that belongs
beside the other duplicate-detection findings in this repo, not a fermata
reading figure.

---

## 3. THE ADDITIVE CONTROL

One record exported twice — with and without the `fermata_owner` verdicts — so
no detector jitter enters.

* With the `<fermata>` elements removed, the two files are **byte-identical**
  (`529bc883…` both ways).
* **Every other counter is unmoved**: notes 1075, rests 432, measure rests 92,
  slurs 23, ties 49, dynamics 132, articulations 14, accidentals 155.

⚠️ **THE STRIP IS STRUCTURAL, NOT LINE-BASED, and that is the previous
session's finding rather than a preference.** `_mxl_note` emits `<notations>`
only when non-empty, so a note whose ONLY mark is a fermata gains a **wrapper**
as well as the element. A line strip removes the element, leaves an empty
wrapper, and reports the files as DIFFERENT outside the family — *a control
reporting a defect it was not built to see is how a real regression hides
behind an expected one.*

⚠️ **No `difflib`.** One ran 50 minutes on ~50k lines and produced nothing.
Everything here is a count or an md5.

---

## 4. WHAT IS NOT CLAIMED

* **No accuracy claim.** Nothing here compares a fermata against the print.
  What is measured is that the family is wired, that it accounts for every
  mark, and that it changes nothing else.
* **No constant was introduced.** The legacy rule has no distance limit — the
  bar bounds the search — and inventing one would be tuning a family on its
  first day against one document. Every verdict carries `dx_canonical_px`
  instead, so a constant can be read off a measured population later.
* **The SIDE is recorded and read by nothing.** `_mxl_note` writes
  `type="upright"` unconditionally, so `fermataBelow` has nowhere to go today.
  Written onto the record rather than dropped at the gather site.
* **One document, one publisher.** The second fixture in hand carries zero
  fermatas, so nothing here has been seen on a second printing.
* ⚠️ **The `no_carrier` 12 is a READING shortfall, not a fermata one.** Those
  bars hold a pause and no notehead and no rest that we read — the mark is
  right and the bar is empty.
