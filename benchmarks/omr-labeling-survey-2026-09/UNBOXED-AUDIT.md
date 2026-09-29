# Unboxed-instance audit: is the rests/accidentals 41% sound?

**Date:** 2026-09-29 · Audits round 6's claim (`ROUND6_SPECIALISTS_2026-09-04.md`,
`probe_spec_residual.py`, `specialist_residual.txt`): "teacher-visible instances
UNBOXED inside each family's own corpus: rests 41%, accidentals 41%." No
training or fine-tuning was done for this audit; the production teacher
(`deepscoresv2-yolov8l-hollow-ft-2026-09-03.pt`, the exact weights round 6
used) was only run for inference on the existing hand-labeled corpus.

## ANSWER

**The 41% is not sound as reported — it is inflated by roughly 2x, for two
different reasons per family.** Correcting for per-instance matching and
eyeballing the residual: the true missed rate is **about 19–21% for both
families**, not 41%. For **accidentals**, Sean's hypothesis is confirmed for
part of the gap: **44 of 376 teacher "accidental" detections (12%, ~29% of the
naive miss count) are the teacher firing an inline class
(`accidentalFlat`/`Sharp`/`Natural`) directly on top of a KEY-SIGNATURE glyph
the labeler correctly boxed under a different, in-scope class
(`keyFlat`/`Sharp`/`Natural`)** — not a miss, a class-label mismatch on ink
that was labeled. For **rests**, key signatures are irrelevant (rests have no
key-sig analog); nearly all of the inflation there is the teacher's own
documented false-positive mode — `restWhole`/`restHBar` hallucinated on
staff-line, slur, and beam-bleed ink — being counted as something the labeler
missed. **The original probe formula also isn't a per-instance match at all**
— it is `unboxed = max(0, sum(teacher detections) − sum(human boxes))`,
a bulk subtraction across the whole corpus, so a cell where the teacher
over-detects is never offset by a cell where it under-detects.

## 1. The matching bug (question 2)

`probe_spec_residual.py` never matches an individual teacher detection to an
individual human box. It sums teacher detections and human boxes separately
across the whole corpus and subtracts the totals. A per-instance,
nearest-neighbour match (center distance ≤ 0.6 average box diagonals, against
the FULL human label file for the cell — not just the family-filtered
subset the specialist corpus keeps) gives a materially different number:

| family | human (full file) | teacher dets | naive "%unboxed" | matched same-class | matched KEY-SIG | matched other-class | **unmatched** | **corrected %unboxed** |
|---|--:|--:|--:|--:|--:|--:|--:|--:|
| rests | 226 | 385 | 41% | 204 | 13 | 21 | 147 | **38%** |
| accidentals | 223 | 376 | 41% | 187 | 44 | 24 | 121 | **32%** |

The bulk-diff artefact itself is a small correction (41→38% for rests). The
big correction for accidentals is the **KEY-SIG** column: 44 teacher
`accidentalFlat/Sharp/Natural` detections land, at essentially zero offset
(center distance 0.04–0.06 diagonals, confidence 0.39–0.86), directly on a
human-boxed `keyFlat`/`keySharp`/`keyNatural` glyph. `benchmarks/omr-labeling-survey-2026-09/out/unboxed-audit/keysig_confusion_mahler5-p176-sys1-s10-m6.png`
shows this directly: five teacher `accidentalFlat` boxes sitting exactly on
the five flats of a printed key signature the labeler boxed correctly as
`keyFlat`.

## 2. Key signatures (question 1) — confirmed, for accidentals only

- The labeling passes were never out of scope for key signatures: both
  `pass-configs/accidentals.json` and `pass-configs/rests-accidentals.json`
  explicitly instruct "Box each accidental of a KEY SIGNATURE individually...
  under `keyFlat`/`keySharp`/`keyNatural`... keep the two apart." Labelers
  DID box key signatures — just under the class DSv2 itself defines for them,
  which `build_specialist_versions.py`'s family filter (correctly) excludes
  from the "accidentals" corpus's positive count.
- `class_aliases.py` (the one place a coarse/fine class-name collision is
  resolved) has no entry pairing `keySharp`/`keyFlat`/`keyNatural` with the
  inline `accidentalSharp`/`Flat`/`Natural` classes — so this is not a
  labeling-vocabulary bug, it is the DETECTOR itself failing to keep the two
  visually similar glyphs apart on a meaningful fraction of key-signature ink.
- No such mechanism exists for rests — there is no rest analog of a key
  signature, and the matched-KEY-SIG count for the rests family (13 of 385,
  none reproduced on eyeball) is noise from the match radius, not a real
  confusion.

## 3. Eyeball sample: 20 unboxed rests + 20 unboxed accidentals

Sampled from the per-instance-matched residual (`/tmp/unmatched_rests.json`,
`/tmp/unmatched_accidentals.json`), spread across classes and confidence,
cropped with the teacher box drawn and the nearest human box (of any class)
noted. 12 representative crops are committed under
`benchmarks/omr-labeling-survey-2026-09/out/unboxed-audit/`.

| classification | rests (20) | accidentals (20) |
|---|--:|--:|
| truly missed by the labeler (genuine) | 10 (50%) | 13 (65%) |
| teacher false positive | 9 (45%) | 5 (25%) |
| key signature / header (beyond the matched-44) | 0 | 0 |
| matching artefact (a human box sits just outside the match radius, same ink) | included above (3 of the FPs: dist 0.63–0.84) | 0 sampled |
| other / ambiguous | 1 (5%) | 2 (10%) |

Applying the eyeball true-positive rate to the corrected matched-residual
gives the estimated genuine miss rate:

- rests: 38% × 50% ≈ **19%**
- accidentals: 32% × 65% ≈ **21%**

Both land at roughly HALF the reported 41%.

**The dominant rests FP mode is exactly the one already documented**
(`ROUND6_SPECIALISTS_2026-09-04.md`: "production's `restWhole`-on-slur-arcs
mode"). `restWhole` is 58 of 147 unmatched rests candidates (39%); every
sampled `restWhole`/`restHBar` FP crop shows the teacher's box centered on
a thick, undifferentiated black mass — a bled slur, a beam, or the staff
line itself — with no rest-shaped glyph inside it
(`out/unboxed-audit/rests_restWhole_dvorak9-p17-sys1-s26-m7.png`,
`rests_restWhole_schehe-p4-sys0-s6-m0.png`,
`rests_restHBar_dvorak9-p9-sys1-s28-m6.png` — the last one is a plain
staff-line segment). All 3 sampled `restHBar` candidates were false
positives. Genuine misses look like an actual rest glyph
(`rests_restQuarter_dvorak9-p16-sys1-s25-m2.png`,
`rests_restHalf_schehe-p2-sys0-s5-m4.png`,
`rests_restWhole_brahms1-p4-sys1-s20-m0.png` — a rectangle hanging correctly
under line 4).

Accidentals FPs are spread across all three classes rather than concentrated
in one: `accidentalFlat` on what is shaped like a rest
(`accidentals_accidentalFlat_dvorak9-p20-sys0-s12-m1.png`), `accidentalSharp`
on a bare stem/beam fragment with no cross-hatch
(`accidentals_accidentalSharp_brahms1-p3-sys0-s9-m1.png`), `accidentalNatural`
on a notehead-shaped blob with a hole
(`accidentals_accidentalNatural_dvorak9-p18-sys0-s23-m4.png`). Genuine misses show the real glyph
clearly (`accidentals_accidentalFlat_mahler5-p176-sys1-s13-m3.png`,
`accidentals_accidentalSharp_schehe-p3-sys0-s14-m3.png`).

## 4. Scope/sweep (question 4)

`build_specialist_versions.py` includes a cell in the family corpus if ANY
stamped pass's palette covers the family — not only the dedicated
single-symbol pass. Of the 424 cells in each corpus, **270 (64%) were swept
by the dedicated `rests+accidentals` (or `keysig`) pass; 154 (36%) reach the
corpus only via a multi-class pass** (`completion`/`draw-rich`, whose
palettes list rests/accidentals among a dozen other classes at once).
`ROUND3_COMPLETENESS.md` records that an early "completion" pass in practice
boxed mostly noteheads and dots despite rests/accidentals being nominally in
its palette — exactly the population `feedback_labeling_single_symbol.md`'s
one-symbol-per-pass rule exists to protect against. This is a real,
plausible source of GENUINE misses in that 36%, not a test artefact — but it
means the 154 cells deserve a re-sweep before being trusted as "complete for
this family," while the 270 dedicated-pass cells can be trusted at face
value.

## 5. Teacher false-positive precision, roughly (question 3)

No global confidence floor was applied by the original probe. In the eyeball
sample, false-positive confidence spanned 0.27–0.76 and genuine-miss
confidence spanned 0.26–0.76 — the two distributions overlap enough that a
single confidence floor will not clean this up by itself. What DOES
separate them is class + shape: `restWhole`/`restHBar` in this population is
~75–100% false positive regardless of confidence; the other four rest
classes and all three accidental classes are closer to even odds.

## 6. Was round 6's conclusion sound? (Sean's follow-up)

Sean: *"this makes me wonder if our decision to not do symbol-specific
processes was tainted by bad test results."* Round 6 blamed the specialist
collapse (`tie 19→0`, `rest8th 12→0`, `accidentalSharp 15→0`, one graft each)
entirely on unboxed labels: "Not drift, not warmup, not scale: the LABELS."
Checked three ways, no new training:

**(1) Class-ID mapping — RULED OUT, verified empirically.** Loaded the exact
checkpoint round 6 used (`deepscoresv2-yolov8l-hollow-ft-2026-09-03.pt`) and
diffed its own `model.names` against `deepscoresv2_208_classes.json`
index-by-index: **0 mismatches across all 208 ids**, including every rest,
accidental, keysig and tie id this audit and round 6 both use. That check is
almost beside the point, though: `YoloDetector` — the tool behind every count
in round 5, round 6, the rehearsal control, and this audit — never reads that
JSON to build a detection's label; it reads `model.names` straight off the
loaded checkpoint (`yolo_detector.py:281-296`). A labeling-side ID skew (the
July nc=214 shape) cannot silently corrupt a printed count here. This audit's
own reproduction of round 6's numbers bit-for-bit (424/226/385 for rests,
424/223/376 for accidentals) is further evidence the indexing is consistent
end to end.

**(2) "~10 head-only steps zeroing a class from 41%-negative labels" —
plausible, but for the wrong reason to trust.** Ties (164 cells, ~139 train
images at the repo's standard 0.15 val split) gives ~9 steps/epoch at
batch 16 — round 6's number. Rests/accidentals (424 cells) give ~22–23,
roughly double what round 6 quotes — a minor inaccuracy, not the real issue.
The real issue: **`benchmarks/omr-dsv2-rehearsal-2026-09/FINDINGS.md`, run
the same day on the same architecture and LR regime, collapses `beam` (mAP50
0.752 → 0.022) after ONE FULL EPOCH — thousands of steps — while training on
69,016 labeled beam instances, "boxed at volume on three quarters of the
images."** That document's own words: *"That also retires the last innocent
explanation from round 5 (corpus silence: 'everything unboxed trains as
background')... Whatever deletes them operates through the optimization
dynamics of a 208-class fine-tune at this LR scale, not through the
labels."* Round 6 does not cite or engage this sibling result anywhere.

**(3) How "12→0" was measured.** Both documents cite the same instrument
(`probe_class_inventory.py`, conf 0.25 default) on the same 30 held-out dense
cells (`benchmarks/omr-phase2.5/cells.json`) — confirmed because their
baseline columns are IDENTICAL (tie 19, rest8th 12, accidentalSharp 15 appear
verbatim in both). No rename/alias issue: `class_aliases.ALIASES` has no
entry for `rest8th`/`accidentalSharp`/`tie`. But **the round-6-specific raw
JSON was never committed** — "Box: vast.ai... destroyed" the same day — so
the per-family after-counts rest on ROUND6's prose alone in this tree; they
are corroborated (not contradicted) by the rehearsal doc's independent
baseline, but not independently re-derivable from anything committed.

**One-line verdict: round 6's collapse is real, but its cause was
UNDER-determined, not proven** — the same-day rehearsal control shows this
architecture zeroes minority classes from optimization dynamics ALONE, even
with abundant, complete labels, so fixing the corpus (which this audit shows
needed a smaller fix than 41% implied) would likely not by itself have saved
round 6's specialists. The decision to park per-symbol training isn't
undermined by this audit — but the stated REASON for it was incomplete, and
the open question is a method fix (head surgery already works for `hollow`;
real rehearsal was tried and failed), not more labeling.

## What a queue for Sean should EXCLUDE

1. **Drop any `accidentalFlat`/`Sharp`/`Natural` candidate whose nearest
   human box (any class) is a `keyFlat`/`Sharp`/`Natural` within ~1 box
   diagonal.** This alone removes 44 of 376 candidates (12% of the raw
   population, ~29% of the naive miss count) and is unambiguous on the
   evidence (`keysig_confusion_mahler5-p176-sys1-s10-m6.png`).
2. **Drop any candidate whose nearest human box of ANY class sits within
   ~1.0 box diagonal**, even outside the strict 0.6 match radius used here —
   three of the sampled rests FPs (dist 0.63–0.84, against `noteheadBlackOnLine`
   and `slur`) were the teacher re-detecting ink a human had already boxed
   under a different, correct class.
3. **Drop `restHBar` candidates outright, or gate them on a shape check**
   (a genuine multi-measure-rest bar is a short, isolated horizontal stroke,
   not a full-width run matching the staff line's own thickness) — 3 of 3
   sampled were the staff line itself.
4. **Flag (do not auto-drop) `restWhole` candidates for extra scrutiny** —
   only 1 of 4 sampled was genuine; require the box to contain an actual
   rectangle-shaped connected component distinct from the surrounding beam/
   slur ink, not just conf ≥ some floor.
5. **Weight the 154 of 424 cells swept only by a multi-class pass
   (`completion`/`draw-rich`) lower than the 270 swept by the dedicated
   `rests+accidentals` pass** — the former is where a genuine miss is most
   plausible per Round 3's own finding, but it should be re-swept with the
   single-symbol pass, not queued as if already-audited residue.

## Reproduction

```
python3 benchmarks/omr-labeling-survey-2026-09/build_specialist_versions.py --family rests --out data/specialist-rests
python3 benchmarks/omr-labeling-survey-2026-09/build_specialist_versions.py --family accidentals --out data/specialist-accidentals
python3 benchmarks/omr-labeling-survey-2026-09/probe_spec_residual_matched.py rests
python3 benchmarks/omr-labeling-survey-2026-09/probe_spec_residual_matched.py accidentals
```

`data/specialist-*/` is gitignored and regenerated by the first two commands
(carved from the already-committed `data/user-labeled/` — no new labeling).
`probe_spec_residual_matched.py` is committed alongside `probe_spec_residual.py`
and reproduces the table in §1 exactly (`specialist_residual.txt`'s naive
figures for rests/accidentals were reproduced bit-for-bit: 226/385/41% and
223/376/41%). It writes `/tmp/unmatched_<family>.json` and
`/tmp/keysig_matched_<family>.json`, which the crops above were cut from.
