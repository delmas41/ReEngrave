> **SUPERSEDED (2026-08-31)** — its headline, that the coverage is "waiting
> behind a config default" blocked on the F-clef veto, is wrong twice over.
> The veto was not failing on merged dots; it was handed the wrong pixels
> and could not see the dots at all. And the coverage was not waiting on a
> threshold but on a CORPUS — with one built, the clustering costs a single
> false positive and is ready to ship. See `NEXT_SESSION_CLEF_2026-08-31.md`
> and the last three sections of `RESULTS.md`. Kept for its measurements and
> its list of dead ends, which stand.

# Handoff — splitting the fused header cluster

> **STATUS: cause found, fix written, held back on one blocker.**
>
> The fused cluster was not the brace and was not one big object: in all 105 of
> them the tallest connected component was under two staff spaces. It was small
> objects — the movement heading, the rehearsal letter, the neighbouring
> staff — stacked by a grouping rule that only looked sideways. Grouping header
> ink in both axes, for ink standing clear of the staff only, is worth
> Nottebohm 61 → 72 located of 205 header cells and Beethoven 5 27 → 33 of 396,
> with nothing lost on either.
>
> It ships **off** (`ClefLocatorConfig.cluster_y_gap_spaces`). Of the 19 staves
> it adds, 14 are right and 5 are bass clefs read as C clefs — every one of
> them the same pre-existing hole, where `_has_f_clef_dots` cannot find a dot
> pair because the dots have merged into the clef's body. Main's own reads are
> wrong at about 8% on this material; these are wrong at 26%.
>
> **So the next lever on this bucket is the F-clef veto, not the clustering.**
> Make it survive a merged or distorted dot pair and the coverage above is
> waiting behind a config default. Note the dot-veto change already scoped on
> `main` goes the OTHER way — it makes the veto fire less, to stop it eating
> the reference sheet's tenor clef — so the two want opposite things and want
> resolving together.
>
> Full write-up, five dead ends, and two ways the measurements were wrong
> before they were right: `RESULTS.md` → "The fused cluster: diagnosed, fixed,
> and held back". Measure with BOTH `probe_clef_rejection.py` (coverage) and
> `check_clef_precision.py` (precision) — the latter grew an orchestral corpus
> during this work because the other three all passed a change that read
> seventeen treble clefs as alto clefs.
>
> Everything below is the original scoping, kept for its measurements and its
> list of dead ends. Read it knowing the headline is settled.

---

## The state of things

Clef **reading** is solved. Where a clef reaches the reader it is named
correctly essentially every time: 7/7 on the hand-checked ground-truth page,
5/5 on engraved reference staves, zero false positives across ten pages of Bach
piano. Alto vs tenor vs soprano is decided by measuring which staff line the
glyph is centred on, not by classification, so it is exact rather than
probabilistic (`tools/omr/clef_geometry.py`).

Clef **coverage** is the open problem. On a 20-page sample of Nottebohm's
*Beethovens Studien* (every 12th page, p.20–248, 188 real music staves):

| | |
|---|---|
| clefs read | **36 of 188 (19.1%)** |
| — by the CV locator | 23 (9 alto, 8 tenor, 6 soprano) |
| — by the detector | 13 |
| no clef read → inherited or defaulted | 152 (80.9%) |

The misses are real, not correct abstention on continuation systems: eight were
sampled at random and rendered, and **seven have a clearly visible clef** at the
staff head.

**One caveat on that 19.1%, measured after the fact.** The key-signature
retune (`96ceca9`) clamped the header window's leftward walk, which moves the
window on some staves. Measured like-for-like over the 191-cell sample, that
took `located` from 36 to **32** on Nottebohm while taking it from 1 to **3**
on a Beethoven 5 orchestral scan — and moved 36 orchestral cells out of "no
clusters" / "only debris", i.e. from windows holding nothing to windows holding
real glyph ink. Roughly a wash on this metric, clearly positive for the window
itself and for key signatures, but the Nottebohm figure above is the pre-retune
one and the current number is 32. It is 8 cells lost (p44 s10, p56 s6, p92 s1,
p152 s2, p164 s0, p164 s6, p188 s6, p224 s7) against 4 gained (p92 s6, p164 s5,
p164 s7, p164 s8), net −4; `--per-cell` on each commit reproduces the list. In
6 of the 8 losses the cluster that now blocks is narrow and tall — 0.27×5.45,
0.82×6.05, 0.95×7.73 staff spaces — so it is rule-shaped, not clef-shaped, and
that is the thread to pull.

## Where the coverage goes — every header cell, by rejecting branch

190 header cells over 17 sample pages, on the current `main`:

| | share | reason |
|---|---|---|
| **105** | **55.3%** | **cluster too big — the clef is fused to something** |
| 21 | 11.1% | not symmetric enough |
| 36 | 18.9% | *located* (18 alto, 10 tenor, 8 soprano) |
| 12 | 6.3% | no clusters |
| 7 | 3.7% | only debris |
| 6 | 3.2% | ambiguous line snap |
| 3 | 1.6% | F-clef dot veto |

**One cause holds the majority.** And it has narrowed usefully: of the 105
fused clusters,

    too TALL only    98
    too WIDE only     2
    both              4

    width  median 2.5 spaces, max 4.8   (limit 4.5 — essentially fine)
    height median 6.0 spaces, max 9.6   (limit 5.0 — this is the problem)

The width is **already correct** — median 2.5 staff spaces is exactly
clef-sized. Before `staff_header.py` gave the readers a measured header window,
clusters ran 10.9, 16.1 and 27.2 spaces wide, chaining through the key
signature into the first notes. That half is fixed.

What remains is **vertical** fusion: a cluster of the right width and 6–9.6
staff spaces of height, where a C clef is under 5.

## What it is fusing with

The system **brace or bracket**, and ink from the staves above and below.

`header_ink.strip_vertical_rules` already removes rules by two signatures —
thin ones (≤0.5 staff spaces wide), and heavy-but-long ones (≤1.2 wide and ≥5
tall, which is what catches a straight system barline). A **curly brace** defeats
both: at its bulge it is wider than 1.2 spaces, so it survives, and it runs the
full height of the system, so once it touches the clef the cluster is 6+ spaces
tall and the "too big to be a C clef, stop" rule aborts the search.

`clef_locator.locate_clef` also has a band filter that keeps only components
whose **centre** lies within `staff_band_spaces` (2.2) of the staff. That is
deliberately on the centre rather than the extent, so a tall G clef still reads
as tall and gets rejected on height instead of being clipped into looking like a
C clef — but it cannot help here, because a fused brace-plus-clef component has
its centre inside the band.

## Measure it first — the probe is now committed

The per-branch breakdown below was originally produced ad hoc. It is now a
script, so a change can be aimed at a branch and its effect read off directly:

```bash
python3 benchmarks/omr-clef-geometry/probe_clef_rejection.py \
    --pdf /Users/seanjohnson/Downloads/Nottebohm-Beethovens-Studien-1873.pdf
```

It reads no ground truth and says nothing about whether a located clef is
RIGHT, so always pair it with `clef_ground_truth_eval.py`. `--per-cell` prints
one line per header cell, which diffs cleanly between two commits (run it in a
worktree of each).

**The bucket holds on completely different material.** Nottebohm's vocal
exercises and a Beethoven 5 orchestral scan agree that it is the one that
matters, and that the excess is vertical.

**Part of it has since been fixed** — see "Sparse residue" below — so the
current figures are:

| | Nottebohm (191 cells) | Beethoven 5 (168 cells) |
|---|---|---|
| cluster too big | 113 → **73** (38%) | 134 → **127** (76%) |
| located | 32 → **43** (23%) | 3 → **3** (2%) |
| height median / max | 5.8 / 9.0 | 7.2 / 12.0 |
| width median (limit 4.5) | 2.6 | 3.2 |

The orchestral half is untouched by that fix and is where the remaining
problem lives: those clusters are genuinely tall, not residue.

## Sparse residue — FIXED

One cause was not fusion at all. Stripping the system brace leaves a trail of
specks down the left edge of the header; x-clustering draws one box around
them; and a box 0.8 x 6.0 staff spaces reads as "bigger than any C clef", so
the locator STOPPED on it and never looked at the clef 1.5 spaces to its right.
On Nottebohm p.164 staff 6 the blocker was five specks at 6% of their bounding
box, standing in front of a textbook 2.3 x 3.2-space alto clef.

The size test was being asked a question about a thing that was not a glyph.
`locate_clef` now runs the ink-fraction test BEFORE the size test: a cluster
has to be a glyph before it is worth stopping for. A real G clef is solid, so
it still clears the ink test and still stops the search — which is the property
`test_a_g_clef_does_not_let_later_ink_stand_in_for_it` exists to protect, and
there is now a companion test that a C clef further in is still not taken.

Measured: Nottebohm located 32 → 43, "cluster too big" 113 → 73. Orchestral
unchanged at 3. Every precision check held — 0 false positives on Bach WTC
p.3-12, the hand-read page still 9/12 with 7/7 precision.

## The F-clef dot veto fires on C clefs — fixed on a branch, NOT merged

`claude/omr-clef-tenor-fixture`. The fix is right and its consequence is not,
which is the whole story.

**The bug.** A C clef's two right-hand lobes, cut into pieces by the staff
lines running through them, are round, the right size, aligned in x and about a
staff space apart: `_has_f_clef_dots`'s signature exactly. Whether it fires is
luck of where the lines fall. On the engraved reference sheet — where the
answer is known by construction — it vetoed the TENOR clef while soprano,
mezzo, alto and baritone survived. That is why `RESULTS.md` measured 4/5 rather
than the documented 5/5.

**The fix.** What separates them is not the dots but their company. An F clef's
dots stand alone to the right of the body; a C clef's lobes are part of a stack
running the height of the glyph. So a pair only counts as dots if nothing else
of substance shares their column. On the reference sheet the tenor pair has two
such neighbours and the real bass clef's pair has none.

    engraved reference sheet    4/5 -> 5/5 (7/7 with treble and bass declined)
    Bach WTC p.3-12             0 false positives, unchanged
    Nottebohm p.31              9/12, precision 7/7, unchanged
    Nottebohm coverage          43 located, unchanged
    orchestral coverage          3 -> 13 located over 9 pages
    orchestral PRECISION         1/2 -> 3/4 on the two hand-read pages
                                 (new: eval_orchestral_clefs.py)

**Why it is not merged.** It makes shipped output worse. The two clefs it gains
on Beethoven 6 p.2 are both correct — the viola's alto clef in each system —
and that opens the key-signature gate on those staves, where the reader
misreads the signature as +1 against a true -1. Two systems of the same part
then agree, so they SET the page's modal reference to one sharp, and the one
correct reading on the page is rejected against it:

    sys0 ord7 (viola)  read +1, true -1  kept: "agrees with the system's 1 sharp"
    sys1 ord7 (viola)  read +1, true -1  kept: "agrees with the system's 1 sharp"
    sys1 ord0          read -1, true -1  REJECTED: "differs ... on too little evidence"

Beethoven 6 p.2 end-to-end goes from 2 correct / 0 wrong to **0 correct / 2
wrong**. And the fix buys no clef improvement on that page to set against it,
because the CV clef is used ONLY to choose the slot table and is never written
to the output — the staves still export as treble either way.

**Three things this exposes, in the order they need solving:**

1. **The key-signature reader misreads the viola staff** as one sharp under a
   CORRECT alto clef. That is the root cause and the only one whose fix is
   unambiguously good. Reproduce with `eval_key_signatures.py --mode component
   --page pastoral-p2`; it is the ordinal-7 pair.
2. **Cross-system agreement is not independent evidence.** The vote treats the
   same part read alike in two systems as corroboration, but a systematic
   misread — same engraving, same glyph, same print quality — repeats by
   construction. Here it manufactured a majority out of one wrong reading.
3. **The header clef is thrown away.** `transcribe` reads it, uses it to pick a
   slot table, and discards it; the measure pass then defaults the staff to
   treble. Everything the locator learns about orchestral clefs is currently
   spent on key signatures alone.

## Approaches worth considering

Nothing here is proven; these are the directions the measurements suggest.

1. **Recognise the brace as a brace.** It is a specific, recognisable object —
   very tall, spanning multiple staves, with a distinctive curl — and it is
   drawn once per system, not per staff. Detecting it at page level and erasing
   it before any header reader runs would be reusable by the key-signature
   reader too.
2. **Split a too-tall cluster instead of giving up.** The abort is what costs
   the coverage. A cluster 6–9 spaces tall that contains a clef-sized,
   symmetric sub-region centred on a staff line could be split rather than
   rejected. Riskier: this is exactly the loosening that once let a treble clef
   be read as a tenor clef, so any split must keep the "measured at true full
   height" property that the band filter exists to protect.
3. **Cut the header window to the staff band before clustering.** Cheap, but
   note the warning above — clipping a G clef into band height is how it starts
   passing as a C clef. Whatever is clipped for *clustering* must still be
   measured unclipped for the height test.

## How to measure whether you have helped

Three checks, all fast, all already written:

    # 1. the hand-read ground-truth page (currently 9/12, precision 7/7)
    python3 -m tools.omr.training.clef_ground_truth_eval \
        --pdf /Users/seanjohnson/Downloads/Nottebohm-Beethovens-Studien-1873.pdf \
        --ground-truth benchmarks/omr-clef-geometry/nottebohm-p46-ground-truth.json \
        --weights omr-weights/deepscoresv2-yolov8l-imgsz2048-ft-30ep.pt

    # 2. the whole test suite — 670 passing, and test_pipeline.py is now a REAL
    #    Phase-1 regression baseline (verified to fail on pre-fix code)
    python3 -m pytest tools/omr/tests/ -q

    # 3. false positives must stay at zero on Bach piano, and the engraved
    #    reference sheet must stay 5/5 (soprano/mezzo/alto/tenor/baritone,
    #    with treble and bass declined) — benchmarks/omr-clef-geometry/RESULTS.md
    #    documents both.

**Report precision and coverage separately.** They measure different
subsystems, and averaging them hides which half moved. A wrong clef transposes
every note on its staff; a missed one leaves the staff where it already was.
The whole layer is built to prefer the second.

## Things already tried that DON'T work — don't repeat them

- **Swapping `cluster_components` for `cluster_components_2d`** (the 2-D
  version already in `header_ink`, used by the key-signature locator). Measured
  on the Nottebohm sample: located **32 → 24**, and 144 of 191 cells (75%) died
  as "only debris". The 1-D x-clustering is load-bearing, exactly as its
  docstring claims — an archaic ladder C clef is a stack of horizontal bars
  that do NOT overlap vertically, so requiring y-overlap shatters the glyph.
  Any vertical rule must keep stacked bars together.
- **Splitting a cluster on a large internal y-gap.** The distributions do not
  separate. Largest internal y-gap, over the same sample: clusters that pass
  the height test have median 0.23 spaces but 26% of them have a gap ≥ 0.8;
  clusters rejected as too tall have median 0.82, and only ~half have a gap
  ≥ 0.8. So a gap threshold splits a quarter of the glyphs that currently work
  while leaving half the problem untouched.
- **"The brace survives `strip_vertical_rules`."** It does not, on the cells
  checked. Dumping the opened vertical components at the left edge of three
  regressed cells, every one was caught — by the THIN rule (≤0.5 spaces), not
  the heavy one. Whatever makes these clusters tall, it is not an unstripped
  system rule.

### One partial lever, and it is material-specific

The band filter admits a component whose CENTRE is within `staff_band_spaces`
(2.2) of the staff, so its EXTENT can reach far outside; x-clustering then
unions those extents. Dropping cluster members that lie wholly outside the
staff's own lines ± 0.75 spaces before measuring height rescues

    Nottebohm     27 of 91 too-tall clusters (30%)
    Beethoven 5    9 of 129 (7%)

so on orchestral material the tall clusters genuinely span the staff and this
is not the cause. Note also that this is precisely the clipping the warning
above is about — it must not be adopted without the false-positive checks, and
the height test must still see the glyph's true extent.

- **Sweeping the horizontal-rule threshold** (`strip_horizontal_rules`, 1.5
  staff spaces) anywhere in 0.7–6.0 makes recall **worse in both directions**.
  Keeping more horizontal ink re-fuses the glyph with staff-line remnants.
  1.5 is the optimum.
- **Widening the heavy-rule width allowance** to catch the brace is not free:
  a clef's own vertical strokes are of similar width, and the ≥5-space height
  condition is the only thing keeping them. Any widening must keep that.
- **An unconstrained search for the axis of symmetry** scores lopsided glyphs
  far too kindly — every shape half-balances about something — and read 20
  treble clefs as tenor clefs across ten pages of Bach. The search is bounded
  to ±0.35 staff spaces for that reason.
- **Fine-tuning the detector on clef cells** fixes clefs and collapses
  dense-page notehead detection (2506 → 114). See
  `benchmarks/omr-clef-demo/DEMO_AND_AUDIT_RESULTS.md`. The decoupled reader
  exists because of this.

---

## The prompt

**Superseded — see the status note at the top.** This asked for the fused
cluster to be split, which is done for the vocal/keyboard case. What is left
for a fresh session is the orchestral one, where the clusters really are tall:
Beethoven 5 has 170 of 371 header cells in this bucket, at a median height of
6.9 staff spaces against a limit of 5.0, and the two-axis grouping barely moves
it. Different cause, so measure it before assuming it is the same problem —
that mistake has now been made twice on this bucket. Run
`probe_clef_rejection.py` and `check_clef_precision.py` together; the second is
not optional, because every promising idea in this area has turned out to buy
coverage with false positives until measured.

The original prompt follows.


> You're picking up OMR work in the ReEngrave repo. Everything is on `main`,
> 678 tests green. Read `benchmarks/omr-clef-geometry/NEXT_SESSION_HEADER_CLUSTER.md`
> first — it has the measurements, the approaches, a committed probe that
> reports where the coverage goes, and a list of things already tried that
> don't work (three of them, with numbers — don't spend the afternoon
> rediscovering them).
>
> **The task:** clef coverage on 19th-century prints is 19%, and one cause holds
> the majority of the rest. 55% of header cells are rejected because the clef
> has fused into an oversized ink cluster. That fusion is now almost entirely
> *vertical*: the clusters are the right width (median 2.5 staff spaces) but 6
> to 9.6 staff spaces tall, against a 5-space limit. They are fusing with the
> system brace and with ink from neighbouring staves. Fix that.
>
> Work on `tools/omr/clef_locator.py` and `tools/omr/header_ink.py`. The
> handoff doc suggests three directions; pick on evidence, not on which sounds
> best, and measure before and after with the three checks it lists.
>
> Two things to hold onto. **Measure before you conclude** — this problem has
> repeatedly looked like one thing and measured as another (the obvious
> discriminator for text-vs-staff was disproven by measurement; so was the
> horizontal-rule threshold). And **report precision and coverage separately**:
> a wrong clef transposes every note on its staff, a missed one costs nothing
> that wasn't already lost, so the layer abstains by design. Don't buy coverage
> with false positives — zero on Bach piano and 5/5 on the engraved reference
> sheet are hard constraints.
