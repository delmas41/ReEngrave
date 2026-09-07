# Accent/diminuendo confusion — measured and REFUTED

**No.** Across the 20-row scan gate, the CV hairpin reader's 96 added hairpins
do not spatially coincide with detected accent marks (1 of 96, and that one is
a *crescendo*, not a diminuendo — zero of 43 diminuendo-classed hairpins land
near any accent). On `dvorak-sym9-mvt1-405834-p7` specifically — the row where
the damage concentrates — the detector found 28 accents on the same page, so
the coincidence test is not vacuous, and still **zero of the row's 23 CV
hairpins sit anywhere near one** (nearest distances 7.7–120 staff spaces). The
size story doesn't rescue the hypothesis either: p7's hairpins run 1.9–23
staff spaces wide, with only one candidate in the accent-like size range
(< 3 sp), and that one candidate doesn't coincide with an accent either. There
is also a **mechanistic** reason coincidence should be near-impossible for any
already-detected accent: the reader blanks every non-span point detection
(including `articAccentAbove`/`Below`) out of the search image before it looks
for hairpin ink (`hairpin_detection.blank_point_detections`), so an accent the
YOLO detector already called correctly cannot survive into a hairpin
candidate. Sean's hypothesis is a clean, well-motivated guess that this
specific evidence does not support — the Dvořák p7 damage needs a different
explanation.

---

## Method

Read the two already-committed, already-scored artefacts with no pipeline run:

- `results-scan-arm-hpon.json` — the row list (20 rows) for the scan gate.
- `<row_id>.omr.json` in
  `.claude/worktrees/fix-hairpin-wire/benchmarks/omr-scan-e2e-2026-09/fixtures/`
  — the transcription each row's `-hpon` (CV hairpins ON) arm actually
  produced.

Per row:

1. **CV-added hairpins** — every detection with `detector: "cv"` and class in
   `{dynamicCrescendoHairpin, dynamicDiminuendoHairpin}`. `bbox_page` is
   already page pixels `[x, y, w, h]` (`hairpin_detection.attach_to_page`
   writes it directly).
2. **Accent detections** — class in `{articAccentAbove, articAccentBelow,
   articulationAccent}`, canonicalized through `tools/omr/class_aliases.py`
   (`articulationAccent` is the coarse, no-side spelling and never appeared in
   this corpus — checked by grepping every `-hpon.omr.json` for any class
   containing "accent"; only the two fine spellings exist here).
3. **Coincidence** — for each CV hairpin, the nearest accent on the *same
   staff*, by center-to-center distance in that staff's own
   `line_spacing_px`. Threshold **1.25 staff spaces** — tight, because an
   accent glyph and a genuinely short hairpin both run roughly one staff
   space wide, so "coincides" has to mean the same ink, not merely nearby.
4. **Size** — hairpin bbox width divided by its staff's spacing, in staff
   spaces, split into the coincide / non-coincide groups.

`probe_accent_confusion.py` writes `accent_confusion_result.json` (full
per-hairpin detail) and prints the summary table reproduced below.

```
python3 benchmarks/omr-hairpin-cv-2026-09/probe_accent_confusion.py
```

## Cross-checks (the failure mode this area has hit three times before)

- **Route 1 vs. route 2 on the CV hairpin count.** Route 1: filter the built
  page dict for `detector == "cv"`. Route 2: the exporter's own top-level
  `n_cv_hairpins_added` counter, written by `attach_to_page`'s own `added`
  tally. **0 mismatches across all 20 rows** — the two numbers that should
  agree by construction do.
- **Accent count vs. raw string search.** For `dvorak-sym9-mvt1-405834-p7`,
  `grep -c '"articAccentAbove"'` / `'"articAccentBelow"'` on the raw JSON text
  gives 23 / 5 — identical to what the JSON-parsed probe reports (23 above, 5
  below, 28 total). The parser is not missing or double-counting detections
  nested under systems/staves/measures.
- **Pooled CV hairpin total (96) matches FINDINGS.md §8's "recovers 96
  hairpins where YOLO alone finds 3"** — the number this probe was built to
  explain is reproduced independently, not assumed.

## Fail-loud discipline

The probe raises `SystemExit` (non-zero) if: a fixture file is missing, a row
has no `pages`, the row-list JSON is empty or not 20 rows, or the **sum across
all 20 rows** of CV hairpins or of accent detections is zero. None of those
fired. A single row legitimately holding zero of either (e.g. the six pages
that carry no hairpins and no CV output at all) is reported as data, not
treated as a probe failure — the aggregate-zero guard is what catches a
silently-broken class match without also flagging an honest empty page.

---

## Results

### Per-row summary

| row | cv_hairpins | accents (above/below) | coincide w/ accent | diminuendo | dim. coincide |
|---|--:|--:|--:|--:|--:|
| beethoven5 984073-p1 | 0 | 0 | 0 | 0 | 0 |
| beethoven5 984073-p2 | 0 | 0 | 0 | 0 | 0 |
| beethoven5 984073-p3 | 0 | 0 | 0 | 0 | 0 |
| beethoven5 984073-p4 | 1 | 0 | 0 | 1 | 0 |
| beethoven5 575951-p1 | 0 | 0 | 0 | 0 | 0 |
| beethoven5 575951-p2 | 0 | 0 | 0 | 0 | 0 |
| beethoven5 575951-p3 | 0 | 0 | 0 | 0 | 0 |
| beethoven5 575951-p4 | 0 | 0 | 0 | 0 | 0 |
| dvořák9 p5 | 4 | 1 | 0 | 2 | 0 |
| dvořák9 p6 | 4 | 13 | 0 | 2 | 0 |
| **dvořák9 p7** | **23** | **28 (23/5)** | **0** | **10** | **0** |
| brahms1 p1 | 2 | 0 | 0 | 0 | 0 |
| brahms1 p2 | 39 | 1 | 1 | 14 | 0 |
| brahms1 p3 | 4 | 0 | 0 | 2 | 0 |
| brahms1 p4 | 1 | 4 | 0 | 0 | 0 |
| mahler5 p2 | 5 | 0 | 0 | 1 | 0 |
| mahler5 p3 | 2 | 1 | 0 | 2 | 0 |
| mahler5 p4 | 7 | 1 | 0 | 5 | 0 |
| mahler5 p5 | 4 | 13 | 0 | 4 | 0 |
| bach-brandenburg3 p1 | 0 | 0 | 0 | 0 | 0 |
| **total** | **96** | **62** | **1** | **43** | **0** |

### Coincidence: 1 of 96 (1.0%), and it is a crescendo

Only one CV hairpin, anywhere in the 20-row gate, has an accent within 1.25
staff spaces on its own staff — on `brahms-sym1-mvt1-317803-p2`, and it is
classed `dynamicCrescendoHairpin` at **3.51 staff spaces wide**, well outside
an accent's own footprint (measured below). **Zero of the 43
diminuendo-classed hairpins coincide with any accent** — the direction the
hypothesis specifically named, from the `wrong diminuendo` bucket the damage
concentrated in.

### Size: real hairpins are wide; accents are ~2.3 sp; there is a small
subpopulation but it isn't where the accents are

Accent detections in this corpus (`articAccentAbove`/`Below`, n=62) measure
**1.19–2.46 staff spaces wide, median 2.27**. The CV hairpins split:

| group | n | width_sp min | p50 | max |
|---|--:|--:|--:|--:|
| coincides with an accent | 1 | 3.51 | 3.51 | 3.51 |
| does not coincide | 95 | 0.81 | 5.24 | 29.83 |

The median non-coincident hairpin (5.24 sp) is roughly double the widest
accent measured — genuine hairpin scale. There **is** a small tail: 13 of 96
CV hairpins (14%) measure under 3.0 staff spaces, overlapping the accent size
band. But none of those 13 sit near a detected accent — most have no accent
at all on their staff (`nearest_accent_dist_sp: None`), and the three that do
(on `mahler5 p5`) sit 6–11 staff spaces away, not co-located. So an
accent-scale false hairpin exists as a *shape* population, but the evidence
does not connect it to *this corpus's actual accent marks* — it could as
easily be a `sf`/`fp` fragment, a stray dot, or scan noise the isolation test
happened to pass.

### `dvorak-sym9-mvt1-405834-p7` in detail — the row the damage concentrates in

28 accents are detected on this page (23 above, 5 below) — the coincidence
test is live here, not vacuous. Of the row's 23 CV hairpins: 22 measure
**7.7–23.2 staff spaces wide** (unambiguously hairpin-scale, not accent-scale)
and the one candidate under 3 sp (1.92 sp, a diminuendo on staff 24) has no
accent detected anywhere on its staff at all. Every nearest-accent distance
that does exist is large — 7.7 to 120 staff spaces, i.e. the nearest accent on
the page, not a nearby one. **Nothing in this row's hairpin population is
positioned where an accent is.**

## What this rules out, and what it leaves open

**Ruled out by this measurement:** the CV hairpin reader is not confusing
*detected* accent marks for diminuendo hairpins on this corpus. Neither the
spatial test (coincidence) nor the size test (accent-scale width at an
accent's own location) supports it, on Dvořák p7 or pooled. The mechanism
(`blank_point_detections` erasing point-class ink, accents included, before
the hairpin search runs) gives an independent, code-level reason this should
be true in general for anything the detector already called correctly.

**Left open:** why Dvořák p7's damage is concentrated in `wrong diminuendo`
specifically. FINDINGS.md §8 already narrows this to "the anchor rule" as one
of two live hypotheses (vs. structural non-correspondence); this probe adds
that it is not accent confusion, but does not identify the true cause. Two
candidates this data does not distinguish: (a) the direction call itself
(`measure_component`'s "crescendo opens to the RIGHT" rule, based on which end
of the isolated component is wider) reading a genuine hairpin's direction
backwards on this page's ink; (b) `_wedge_anchor_notes`/anchor placement
attaching a correctly-classified diminuendo to the wrong note pair, which
`musicdiff` would also charge as `wrong diminuendo` even though the shape was
read correctly. FINDINGS.md's own suggested next step — a per-measure op dump
via `dump_ops.py` on this row's truth/pred pair — is what would separate
those two, and is unaffected by this probe's negative result.

## Files

- `probe_accent_confusion.py` — the probe.
- `accent_confusion_result.json` — full per-hairpin detail for all 20 rows
  (staff, measure, kind, width/height in staff spaces, nearest accent
  distance, coincidence flag).
