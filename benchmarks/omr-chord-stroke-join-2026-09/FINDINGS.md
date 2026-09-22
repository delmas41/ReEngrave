# Join a chord to its stroke — REFUSED BY THE PRINT: reach 1.3%, 2 of 17 settled

**2026-09-22, Lane B.** The 2026-09-21 stem-attribution re-derivation ranked
this **first** (*"Same line, widened rather than narrowed"*). Measured and
**not shipped**: `git diff <base> -- tools/` is **EMPTY**, no flag added, no
default moved.

⚠️ **PROVENANCE.** The harness blocks subagents from writing `.md` report
files — the **sixth** time in this repo (see
`benchmarks/omr-ink-first-breitkopf-2026-09/FINDINGS.md` and
`benchmarks/omr-ink-first-2026-09/FINDINGS.md` for the others). **This file is
the measuring session's own report transposed at integration.** Every number
below is re-derived by the managing session from `out/RESULT.json`, which
`probe/collate.py` regenerates from the committed artefacts and which was never
typed by hand. `[mgr]` marks a managing-session check.

## CONVENTION ASSUMED / WHAT WOULD FALSIFY IT / NOT CONFIRMED WITH SEAN

**ASSUMED** — *a chord is several noteheads sharing ONE stem.* An engraver
draws one vertical stroke for the whole chord and the heads sit stacked on it,
so only the outermost is at the stroke's end. **It is Sean's own**, said on
2026-09-20 of a crop the software had filed as a fault: *"it is an octave of
C's and the stem belongs to both."*

**WHAT WOULD FALSIFY IT** — the pairs the widened join reaches turning out not
to be chords when read against the print. **That is what happened.**

**NOT CONFIRMED WITH SEAN** (asleep). The adjudication calls are the lane's.

---

## 0. [mgr] Checked against the tree before believing the report

| claim | check | result |
|---|---|---|
| branch pushed | `git ls-remote --heads origin` | `596f38b0` present |
| nothing under `tools/` | `git diff --stat origin/main...<branch> -- tools/` | **empty** |
| reach 31 / 1.3% | `out/RESULT.json` | `pooled_heads_reached = 31`, `pooled_share_of_no_stem = 0.0134` |
| 2 of 17 settled | `out/RESULT.json` | `candidates_the_print_SETTLES = 17`, `one_shared_stem = 2`, `share = 0.1176` |
| 13 non-noteheads | `out/RESULT.json` | `red_is_not_a_notehead 9` + `blue_is_not_a_notehead 4` |
| controls 12/15, 0 wrong | `out/RESULT.json` | `controls 15`, `controls_correct 12`, `controls_WRONG 0` |

## 1. ⚠️⚠️ THE RANKED ITEM WAS SIZED OFF A POPULATION TWO THIRDS TOO LARGE

The work was ranked on *"reach 115 of 124 profile pairs, 98 / 73 shipped"*.
The premise check reproduced `solo_pairs` 969/1,256 and
`solo_pairs_with_a_chord_shadow` 73/98 **exactly** — and then found that
**73/98 is not a reach at all**: `chord_shadow.py` asks whether a solo-claimed
stroke has another head at its x inside its y-span, and **never asks whether
that head is stemless.** Decomposed, only **24 / 33** of those rows are a
stemless head. **Two thirds already carry a stroke of their own** — second
voices, neighbours, heads read correctly.

⚠️ **A shadow says a partner EXISTS; it does not say a join is MISSING.** The
predecessor's own §7 said as much (*"the shadow curve says a partner exists,
not that the pair is a chord"*) and the ranking still used it as a reach.

## 2. REACH — 31 heads of 2,322 (1.3%)

| | Litolff | Breitkopf |
|---|--:|--:|
| `no_stem` today | 793 | 1,529 |
| **heads the widened join reaches** | **20 (2.5%)** | **11 (0.7%)** |
| candidate pairs | 23 | 11 |
| strokes whose DIRECTION would FLIP | 4 | 2 |

All 31 are `abstained/no_stem` on the record and **none is already answered by
the beam-mate tier** (20/20, 11/11), so the reach is real rather than
overlapping. Their 41 mates: 40 `decided/stem_projection`, 1 `stems_disagree`.

## 3. THE PRINT — and the convention is not what failed

48 full-width strips at 100 px/space, NEAREST resampling (both plates are
`bpc: 1`), margin ticks plus corner brackets clear of the ink, with a zoom as a
second view. Frame control, geometry and marking **imported** from the sibling
`crop_strips.py` rather than restated. ⚠️ **The frame control FIRED and was not
relaxed: 2 Litolff strips refused** (delta −5.4 and +13.7), one of them
`staff/3/1/7` — the tilting staff the sibling crop pass also refused.

| | CONTROLS | CANDIDATES |
|---|--:|--:|
| **one_shared_stem** | **12** | **2** |
| separate_stems | 0 | 2 |
| **not a notehead** | 0 | **13** |
| cannot_tell | 3 | 16 |

⚠️⚠️ **CONTROLS 12 OF 15 WITH ZERO WRONG** — so the question is answerable by
eye and **the convention is not what failed.** Of the 17 candidates the print
settles, **2 are a real chord (11.8%) and 15 are not.**

**What the 13 non-noteheads are, read off the plate:** a BASS CLEF ×2, a C
CLEF, a printed `ff` ×4, a BARLINE, a BEAM ×3, a QUARTER REST, an AUGMENTATION
DOT. On Breitkopf that is **8 of 11 candidates.** ⚠️ This reproduces the crop
pass's *"46 of 180 boxes are NOT NOTEHEADS"* from a different direction and
harder — **the third independent lane to land on the same contamination.**

The two real ones are genuine — `glyph/3/0/5/0/9` and `glyph/2/0/5/4/10`, each
two dotted half notes on one stem below the staff. ⚠️ **Litolff yielded ZERO
real chords in 22 candidates**, and one case would have been right for the
wrong reason (the partner is a quarter rest and the stroke is the other head's
own stem).

## 4. The obvious cleaning helps and does not save it

A **1.0-staff-space notehead width floor** — the sibling crop pass's, with the
unit taken from `Q.CELL_STAFF_SPACE` **per cell** and the absent case
abstaining, never a flat 100 px (the trap that made a sibling lane's Breitkopf
figures wrong by up to 25%) — removes **5 of 34** pairs, 4 of them adjudicated
not-a-notehead, and leaves **9 non-noteheads** and both `separate_stems` cases
standing. After it the rule scores **2 of 13 settled**.

## 5. One clean separation, at n = 2, DELIBERATELY NOT PROPOSED

| the box's class | one_shared_stem | wrong |
|---|--:|--:|
| `noteheadHalf*` / `noteheadWhole*` (hollow) | **2** | 1 |
| `noteheadBlack*` (filled) | **0** | **14** |

Solid furniture ink — a clef bowl, an `ff` loop, a barline, a beam — gets
called a BLACK notehead; a hollow head is hard to fake. ⚠️ **Not offered as a
gate**: n = 2 positives, and **a class name is the detector's own word about
the SAME box — one signal, not a second witness**, which
`Evidence.correlated_groups` already settles.

## 6. Instrument

33 tests; battery **24 arms, 24 RED, 0 survivors, restore hash-verified**, with
all four prophylactics (`PYTHONDONTWRITEBYTECODE=1` per arm, pytest's elapsed
time stripped from the judge, byte snapshot + in-flight sentinel, every
mutation hash-verified to have changed the file). ⚠️ **Its first run had 7
survivors and 1 bad anchor and every one was real**: six genuine test gaps —
two of them in the scorer's POOLED report, *which is where the headline
denominator lives* — one equivalent mutant named and held out, one guard
**deleted** rather than tested around, one indentation anchor. A dead parameter
was also deleted (`extra_members` took a `joined` list and recomputed it).

## 7. What is NOT established

One adjudicator, who also wrote the crop tool — **no inter-rater figure**, and
that adjudicator measured **2 of 24 wrong at tile magnification** on a sibling
lane. ⚠️ **The adjudicator was not blind to the geometry**: the stratum was
blind, the x-gap and dy were not. The print settles only 17 of 33, and **15 of
the 16 `cannot_tell` are Litolff — the Breitkopf half is carrying the
conclusion.** n = 2 documents, 2 publishers, 8 pages, both scans; the engraved
family is untouched. No re-gather, no export, no OMR-NED (deliberately — the
metric is symmetric and would pay for emitting fewer stems either way).
⚠️ Record counts here are GATHER facts and stable; a `readjudicate` control
against those records' committed verdicts is **not** on today's tree, and no
arm here depends on one.

## 8. Ranked next work

1. **NOT this rule.** The entry condition for a revisit is a **third
   publisher** on which the hollow/black separation holds — not a better
   threshold.
2. **The contamination is the item, and no adjudicator can reach it**: it is a
   DETECTOR fault upstream of GATHER, where routing is by class. Three lanes
   have now measured it independently.
3. ⚠️ **The 4+2 direction flips are the un-refuted half.** `_project` builds
   its group from heads that OVERLAP, so a dropped member is missing from the
   direction computation too — a stroke whose only joined head sits at one end
   may be reporting a direction computed from an incomplete group. That is a
   question about `_project`, needs no new rule, and was not touched.
4. The 2 `separate_stems` pairs say the head-against-head x ruler is too loose
   on a dense plate **even when both boxes ARE noteheads.**
