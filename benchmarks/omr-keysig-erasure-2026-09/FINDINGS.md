# Verovio's spacing, or the erasure? — it is the ERASURE, and it is NOT everywhere

**2026-09-22.** The ranked **#1** of
[docs/handoff-2026-09-22-four-lanes-and-three-refutations.md](../../docs/handoff-2026-09-22-four-lanes-and-three-refutations.md)
§6, taken the same night. **No file under `tools/` changed. Nothing is
proposed for any constant, flag or default.**

## The question

Lane A found `adjudicate_key_signature` preferring a reader that is right 6 of
30 over one that is right 20 of 20, and traced the mechanism to
`key_signature_locator.min_height_spaces = 1.10` against flats measuring
**0.94 staff spaces** after `header_ink_mask`. It could not say whether that was

* **Verovio's key-signature spacing** — an artefact of one renderer, or
* **the ERASURE** — `erase_staff_lines`, in which case *"it is everywhere."*

Its §11 said the test is one LilyPond render. **Two tests were run: the second
renderer, and then the erasure itself — and the second one is why the answer is
not the one the handoff expected.**

## CONVENTION ASSUMED / WHAT WOULD FALSIFY IT / NOT CONFIRMED WITH SEAN

**ASSUMED** — a key-signature flat is printed at a fixed height of about 2.5
staff spaces, *whoever* sets the page, because SMuFL fixes it; so two
independent engravers should measure it alike and a disagreement is ours.
**WHAT WOULD FALSIFY IT** — LilyPond measuring the flats at their full height
where Verovio does not. **It does not.**
**NOT CONFIRMED WITH SEAN.**

## 1. IT IS NOT THE RENDERER — two engravers agree to 0.03 staff spaces

The same MusicXML, through `musicxml2ly` + LilyPond 2.24.4, read by the same
`locator_vs_template.py` the lane shipped, staff 0:

| | flat 1 | flat 2 | flat 3 | kept |
|---|--:|--:|--:|--:|
| **Verovio** | 1.19 | **0.94** | **0.94** | 1 of 3 |
| **LilyPond** | 1.22 | **0.95** | **0.96** | 1 of 3 |

**Same three flats, the same two dropped, the same one kept — to within 0.03
staff spaces.** ⚠️ **Lane A's "observation, not a mechanism" also reproduces**:
it noted the two dropped clusters begin *exactly on a staff line* (Verovio
y = 600, 800) and the kept one mid-space (749). LilyPond: dropped at **597 and
795**, kept at **746**, against staff lines at 598/699/800/901/998. **Two
renderers, the same three positions to within 5 px** — so it is no longer only
an observation.

## 2. IT IS THE ERASURE — asked directly, the same crop clustered twice

`erasure_cost.py` calls the SHIPPED `header_ink_mask` for the erased arm and
reproduces it with an EMPTY line list for the intact arm, so the two differ in
exactly one thing and nothing is reimplemented.

| render | staff lines INTACT | staff lines ERASED | |
|---|--:|--:|---|
| **Verovio** | **3 kept** — 1.18, 1.19, 1.19 | **1 kept** | ⚠️ **costs 2 of 3**, pushing 0.94 / 0.94 under the floor |
| **LilyPond** | **3 kept** — 1.22, 1.22, 1.22 | **1 kept** | ⚠️ **costs 2 of 3**, pushing 0.95 / 0.96 under |

**With the staff lines left in, every flat clears `min_height_spaces` on both
renderers. The erasure is what puts two of three under it.** That answers the
handoff's question.

## 3. ⚠️⚠️ AND IT IS *NOT* "EVERYWHERE" — THE SCAN INVERTS IT

The same probe on the real Litolff plate (`imslp984073`, pdf page 1, 600 dpi,
staff 0):

| | accidental-sized clusters kept |
|---|--:|
| staff lines INTACT | **5** |
| staff lines ERASED | **11** |

⚠️ **The erasure roughly DOUBLES them, in the opposite direction to the
engraved arms.** On a scan the staff lines MERGE glyphs into each other and
erasing them SEPARATES the components — **which is the reason `erase_staff_lines`
exists at all**, and the reason the refusal that prefers the locator was
defensible when it was priced on scans.

⚠️ **The mechanism is still present there** — two clusters are pushed under the
floor (0.95 and 1.07) — **it is simply swamped.**

> **So the honest statement is narrower than the handoff's, and it is the
> finding: the erasure's COST is a property of ENGRAVED input, where the ink is
> thin and clean and the lines lie across the glyph with nothing to separate.
> On a scan the same erasure pays for itself. *"If it is the erasure, it is
> everywhere"* is FALSE.**

## 4. What this does and does not license

**It does license** reading Lane A's §1 as *engraved-specific*: the locator's
under-counting there is an artefact of a repair aimed at scans, applied to a
domain that does not need it.

⚠️ **It does NOT license flipping the precedence globally.** The template's
20/20 is engraved-only; on a scan the locator has the erasure working FOR it
and the template's over-counting risk is real and is what the refusal was
written about. Two shapes are conceivable — a domain-aware precedence (the
machinery exists: `input_domain._classify_page` is `OMR_WEIGHT_ROUTING`'s
measured classifier, and answers False on any doubt) or a lower floor — and
**neither is measured here and neither is proposed.** ⚠️ Note the staged CLI
does no weight routing at all today, so a domain-aware rule there would be the
first consumer of that classifier on the staged path.

## 5. ⚠️ A defect in this probe's own first draft

It matched an intact cluster to its erased counterpart **on x alone** and
reported *"lost −1.38 spaces (−431%)"*. Erasure SPLITS and reshapes components,
so a cluster's bounding box MOVES, and the match paired a flat with whatever
else sat near that column. **Fixed by reporting a COUNT rather than a pairing**
— which is also what the locator's pre-fit actually consumes — with the heights
printed as two sorted lists and no pairing claimed.

## 6. What is NOT established

- **n = 1 work, 1 staff, 3 pages of engraved and 1 page of scan.** §3 is ONE
  staff of ONE scanned plate.
- ⚠️ **§3's two arms are not like-for-like**: a scanned header holds different
  content from a rendered one, there is no truth for the scan's clusters, and
  **"11 kept" is not "11 correct"** — only that the count moves the other way.
- **No accuracy is measured anywhere in §2 or §3** — this counts what the
  locator's pre-fit would keep, not what it would get right.
- **No print was consulted by eye and no crop was cut.**
- Nothing was re-gathered, exported or scored; **no OMR-NED**, deliberately.
- **Nothing is proposed.** §4 names two shapes and measures neither.
