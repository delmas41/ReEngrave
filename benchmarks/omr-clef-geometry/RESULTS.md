# Clef reading by geometry — results (2026-08-27)

Follow-up to `benchmarks/omr-clef-demo/DEMO_AND_AUDIT_RESULTS.md`, which
established that the clef *approach* worked but that no fine-tuned checkpoint
could be deployed, and left alto↔tenor confusion unsolved. This round stops
trying to solve it with a model.

**Headline: alto vs tenor is not a recognition problem, and treating it as one
is why it stayed broken.** They are the same glyph one staff line apart. So is
soprano, mezzo-soprano and baritone. The distinguishing information is the
glyph's *position*, which a class label discards — and DSv2 has only two C-clef
classes, so three of the five are unrepresentable in that label space at any
level of training. Measuring the position instead makes the answer exact.

Two modules, and one starting observation that turned out to matter more than
either.

---

## The starting observation

The user's case: Beethoven's counterpoint studies (Nottebohm, *Beethovens
Studien*, 1873) — species counterpoint and fugue exercises written throughout
in C clefs — came out with no clefs determined.

Reproduced on p.90 (printed p.75). The page has seven detected staves. Across
all of them the production model returns **one** clef detection, and it is
wrong (`clefF`, conf 0.10, on a staff carrying a C clef). Every staff falls back
to the position default, so the page transcribes as treble/bass.

Probing further: at conf **0.03**, over the staff-header crop, with *both* the
production model and the `clef-ft-boxfix` specialist, the number of C clefs
found on this page is **zero**.

| model | conf | C clefs found on p.90 |
|---|---|---|
| production | 0.25 | 0 |
| production | 0.03 | 2 spurious `clefCAlto` at 0.06–0.10, neither on a clef |
| clef-ft-boxfix specialist | 0.25 | 0 |
| clef-ft-boxfix specialist | 0.03 | 0 |

This is a **domain gap, not a threshold**. The glyph is the archaic "ladder"
C clef of 19th-century engraving, which looks nothing like the fonts DSv2 was
rendered from. No confidence setting reaches it, and the specialist — fine-tuned
on modern orchestral scans — is no better. Same conclusion the time-signature
work reached about orchestral meters (`docs/dossier-verification-plan.md`).

---

## Part 1 — `clef_geometry.py`: which line does the clef name?

The detector keeps the job it can do: find a clef and name its family (G / C /
F), which is a real visual distinction. Geometry does the rest — snap the
glyph's named line to the nearest of the five staff lines, look the clef up by
`(family, line)`.

A C clef is symmetric about the line it names, so its named line is the middle
of its box. No calibration constant, and true of an archaic engraving as much
as of a modern font.

`pitch_resolver._CLEF_ANCHORS` and `export._MXL_CLEF_SIGN` are now *derived*
from the same clef table, so all ten clefs are supported end to end without a
second list to drift out of sync. The four pre-existing anchors are unchanged.

**G and F clefs deliberately keep their class label.** They aren't symmetric,
so they'd need a calibrated offset, and the expected value is negative: treble
and bass dominate those families, french/varbaritone/subbass barely occur, and
a wrong guess transposes every pitch on the staff. Enabling them is a config
change (`ClefGeometryConfig(families=...)`), not a code change.

---

## Part 2 — `clef_locator.py`: is there a clef here at all?

Geometry can't help when there is no detection, which on the Nottebohm material
is every staff. So find the clef by shape, the way Phase 4f handles stems and
beams: morphology doesn't care what font a glyph is set in.

Strip the vertical rules (the barline sits ~3px from the clef — too close for
any proximity grouping to separate), strip the horizontal ones (staff lines,
and the substantial residue upstream removal leaves on these thick uneven
lines), cluster the surviving header ink, and take the first glyph-sized
cluster. Accept it only if it is symmetric about its own centre — the C-clef
signature — and then use that same symmetry to read the line, refined to the
axis the ink actually balances about.

Three design decisions did the work:

1. **C clefs only.** The one clef with a shape signature that survives any
   engraving style. G/F yield nothing.
2. **Stop at the first glyph-sized cluster; never scan past one.** This was the
   locator's one dangerous bug. A G clef is too tall to be a C clef, and
   skipping it landed the search on the key signature's first sharp — narrow,
   tall, and beautifully symmetric — which was then read as the staff's clef.
   Fixing this removed *every* false positive on Bach at a stroke, and let the
   crude "clef must start near the staff head" bound be relaxed from 3.0 staff
   spaces to a 6.0 backstop (orchestral clefs sit further in, behind brackets
   and stacked instrument numbers).
3. **It only speaks when nothing else did.** Gated on no clef having been read
   for that staff by either model, so it can add a reading but never overturn
   one, and pages that read correctly today cannot get worse.

---

## Validation

### Controlled ground truth — LilyPond reference staves

`reference-clefs.ly` engraves one staff per clef, so the right answer is known
by construction rather than by eye.

| engraved | read as | symmetry | residual (line spacings) |
|---|---|---|---|
| soprano | **soprano** ✓ | 0.990 | 0.17 |
| mezzosoprano | **mezzosoprano** ✓ | 0.991 | 0.14 |
| alto | **alto** ✓ | 0.9999 | 0.12 |
| tenor | **tenor** ✓ | 0.994 | 0.07 |
| baritone | **baritone** ✓ | 0.990 | 0.02 |
| treble | *(declined)* ✓ | — | — |
| bass | *(declined)* ✓ | — | — |

**5/5 exact, including the alto/tenor pair**, with treble and bass declined
rather than guessed.

**Re-measured 2026-08-28 through the header-cell path and it is 4/5** — tenor
declines; soprano, mezzosoprano, alto and baritone still read exactly, and
treble and bass are still declined, so there are no false positives either way.
Measured identically at `bcf87d4`, at `637f3cb` and after the sparse-residue
fix, so it is not a regression from any of them: the 5/5 above was taken via a
different route into the locator. Worth resolving before the row is quoted
again.

### False positives — Bach WTC, 10 pages of piano music

Piano music has no C clefs, so every hit would be a false positive.

| pages | hits |
|---|---|
| WTC I, p.3–12 | **0** |

Still 0 after the sparse-residue fix (2026-08-28), which is the check that
mattered for it — reordering the ink test in front of the size test could in
principle have reopened the G-clef-then-sharp trap, and did not.

Reproduce with the rejection probe, which reports `located` per page:

```bash
python3 benchmarks/omr-clef-geometry/probe_clef_rejection.py \
    --pdf <WTC I>.pdf --first 3 --last 12 --every 1
```

(Before the "stop at the first glyph-sized cluster" rule: 20 false "tenor"
reads across the same pages, all of them key-signature sharps behind a skipped
treble clef.)

### True positives — real scores

Every located clef below was checked against the rendered page.

| score | located | verdict |
|---|---|---|
| Handel *Messiah* (vocal part), p.2 | 4 × alto | correct — C-clef vocal part |
| Ravel *Boléro*, p.30–31 | 6 × tenor, 4 × alto | correct — trombones, violas |
| Debussy *La Mer*, p.26 | 1 × alto | correct — viola |
| Beethoven 5, p.9 | 1 × alto | correct — viola |
| Nottebohm p.90 / p.95 | 2 × soprano, 2 × tenor, 1 × alto | C clefs where nothing was detected before |

One Beethoven 5 read worth recording: the measured axis landed at y = 478.0
against a staff line at exactly 478 (residual 0.00), naming a tenor clef, on a
glyph a visual estimate had put on the middle line. The measurement was right
and the eyeball wasn't — which is the argument for the whole approach.

### Ground truth from the target book itself — Nottebohm p.31 (PDF 46)

Sean read the clefs off exercises Nr. 20–22 by eye: three systems of four
staves carrying the full vocal clef set, in the archaic square engraving. This
is ground truth on exactly the material the detector cannot touch, and it is
checked in (`nottebohm-p46-ground-truth.json`) with a scorer
(`tools/omr/training/clef_ground_truth_eval.py`).

| | first measured | after the Phase-1 fixes |
|---|---|---|
| clefs READ | 6 staves | **9 staves** |
| precision on those | 6/6 | **7/7** |
| overall (read + inherited + defaulted) | 6/12 | **9/12** |
| supplied by the CV locator | 4/4 | 7/7 |

The two numbers must not be averaged into one, because they measure different
subsystems. **Reading is right every time it happens.** Coverage is the problem.

Two cautions on reading this table. The intermediate figure of 12/12, reached
partway through the Phase-1 work, was measured when barline detection had
collapsed and every staff was a single cell — an easier and unrepresentative
input, not a real high-water mark. And the final 9/12 is scored against
*correct* measure segmentation, where the first cell is a real measure rather
than a whole system.

The locator separated **soprano from alto from tenor** on the square lattice
glyph — three clefs one staff line apart — repeatedly across the page.

### Why the misses were misses

Attributing every miss by hand, at the point where 6 of 12 were read:

| miss | cause | whose problem |
|---|---|---|
| Nr. 22 ×3 | the clef is **not in the cell** — it begins past it | Phase 1 (`_staff_x_extent`) |
| Nr. 20 tenor, Nr. 22 bass | staff lines **mis-grouped** | Phase 1 (`staff_detector`) |
| Nr. 21 alto | clef fused into an oversized cluster | the locator |

Five of six were Phase-1 layout failures — which is what prompted fixing them
(next section), and what took the page from 6/12 to 9/12.

### One negative result, recorded so it isn't retried

The fragmented-clef misses look like the horizontal-rule stripper eating the
archaic clef's bars (those bars are ~1–1.5 staff spaces wide and the threshold
is 1.5). Sweeping that threshold from 0.7 to 6.0 staff spaces makes it **worse
in both directions** (4 located → 1–3), because keeping more horizontal ink
re-fuses the glyph with staff-line remnants. 1.5 is already the optimum.

### No collateral damage

| run | noteheads | detections |
|---|---|---|
| Nottebohm p.90, before | 68 | 186 |
| Nottebohm p.90, after | **68** | **186** |
| Mahler 5 p.11 | **2506** | 4878 |

Byte-identical detection output on Nottebohm, and Mahler 5 p.11 sits exactly on
the 2506-notehead production baseline from `omr-clef-demo`. The clef work
touches clefs and nothing else — the opposite of the fine-tuned checkpoints,
which bought clefs by collapsing dense-page noteheads to ~5%.

### Export

`soprano` survives the whole chain: `<sign>C</sign><line>1</line>` in MusicXML,
`\clef soprano` in LilyPond, re-parsed by music21 as `SopranoClef`, and the
exported `.ly` compiles.

### Tests

65 new tests (`test_clef_geometry.py`, `test_clef_locator.py`); 513 passing in
`tools/omr/tests/` overall, no regressions. The locator's tests draw their own
cells, so they exercise rule stripping, clustering, the symmetry gate and the
snap against glyphs whose named line is known by construction — including the
G-clef-then-sharp trap that produced the Bach false positives.

---

## Phase 1: what the clef work forced open

Chasing the misses above led into the layout stage, and the fixes there
mattered more than the clef work itself. Full rationale in the commits; the
measured effect:

| page | systems | barlines | cells |
|---|---|---|---|
| Nottebohm p46 | 5 → **3** (correct) | 5 → **24** | 16 → **88** |
| Nottebohm p90 | 4 | 9 → **21** | 18 → **39** |
| Beethoven 5 p8 | 5 | 74 → 86 | 273 → 293 |
| La Mer p25 | 9 → 3 | 14 → 12 | 65 → 78 |
| Mahler 5 p11 | 3 | 23 → 27 | 221 (unchanged) |
| WTC ×3, Boléro ×2, Handel | unchanged | unchanged | unchanged |

p46 has 3 systems × 4 staves × ~7 measures, so 88 cells is about right where 16
was not. Three causes, each a rule quietly depending on something else:

1. **`_staff_x_extent` took the longest strictly-contiguous ink run.** Scanned
   staff lines are dashed, so it returned a fragment. Offset measured at 1.2
   staff spaces on Bach and **up to 46** on Nottebohm — past the clef entirely.
2. **The system's opening barline survived as a measure boundary**, because its
   margin was a fixed 10px where engravers set that rule a *fraction of a staff
   space* in (1.5 spaces = 20px on Boléro). It manufactured a sliver measure
   that swallowed the clef.
3. **The system's left edge was `min(x_start)`** across its staves. Staves are
   engraved flush, so that edge is a consensus: on Boléro p.31 one staff of
   seventeen read 4.3 spaces wide of its neighbours and cost that system its
   clefs. Now the median.

Fixing those broke barline detection, which had been depending on the damage:

4. **System grouping was being done by x-overlap**, accidentally. Staves whose
   broken extents disagreed were split apart; once every staff spanned the page
   they merged into one system and the barline vote threshold became
   unreachable. The vertical-gap rules could not take over because both are
   computed over ALL gaps, so on a page that is mostly system breaks the breaks
   drag the thresholds above themselves (p.90: gaps 65, 65, 65, 341, 394, 830 —
   a median of 203 sits above the 341 and 394 breaks). Added a threshold
   against the low quartile, which estimates within-system spacing whatever
   share of the page is breaks.
5. **Open-score barlines do not cross the gaps between staves.** Each voice's
   barlines stop at its own staff, so every real barline scored connectivity
   0.00 and the orchestral-tuned filter discarded all of them. Measured:
   Nottebohm p.31 is 4/4 votes and 0.00 connectivity on every barline; Mahler 5
   p.11 has real barlines at 0.4–1.0 and it is the *stem alignments* that score
   0.00. The filter now asks each system which kind it is.

## Book-scale measurement

A 20-page sample spread evenly through the book (every 12th page, p.20-248),
re-run on `main` after the staff-header/key-signature layer was merged in.

| | before the Phase-1 work | on current main |
|---|---|---|
| "staves" reported | — | 191 |
| — carrying noteheads (real music) | — | 188 |
| — **body text read as staves** | ~10% of all staves | **0** |
| measures on music staves | ~12/page | **742 over 18 pages (~41/page)** |
| **clefs read** | — | **36 of 188 (19.1%)** |
| — by the CV locator | — | 23 (9 alto, 8 tenor, 6 soprano) |
| — by the detector | — | 13 |

Two of the three results are good. The text filter finds **nothing** to reject
on a 191-staff sample where roughly a tenth used to be prose, and measure
segmentation has roughly tripled.

Clef coverage is the open problem at 19.1%, and the misses are real: eight
"not read" staves sampled at random and rendered, **seven with a clearly
visible clef**. This is lost recall, not correct abstention.

### Where the coverage is lost — and how the header window changed it

Every header cell on 17 sample pages, by the branch that rejected it:

| | share | reason |
|---|---|---|
| 105 | **55.3%** | **cluster too big — the clef is fused to something** |
| 21 | 11.1% | not symmetric enough |
| 36 | 18.9% | *located* (18 alto, 10 tenor, 8 soprano) |
| 12 | 6.3% | no clusters |
| 7 | 3.7% | only debris |
| 6 | 3.2% | ambiguous line snap |
| 3 | 1.6% | F-clef dot veto |

One cause holds the majority — but `staff_header.py` has already fixed half of
it. Of the 105 fused clusters, **98 are too tall only**, 2 too wide only, 4
both:

    width  median 2.5 spaces, max 4.8   (limit 4.5 — essentially fine)
    height median 6.0 spaces, max 9.6   (limit 5.0 — this is the problem)

The width is now correct. Before the readers were given a measured header
window, clusters ran 10.9, 16.1 and 27.2 staff spaces wide, chaining through
the key signature and into the first notes. What remains is **vertical**
fusion — with the system brace, whose curl is wider than the heavy-rule width
allowance, and with ink from neighbouring staves.

Scoped for a fresh session in `NEXT_SESSION_HEADER_CLUSTER.md`.

---

## The fused cluster, resolved (2026-08-28, second pass)

Measured with `probe_clef_rejection.py` (coverage) and
`check_clef_precision.py` (precision), on two corpora deliberately unlike each
other:

| | main | after |
|---|---:|---:|
| Nottebohm, 191 headers over 20 pages — **located** | 43 | **59** |
| — cluster too big | 73 | **48** |
| Beethoven 5, 371 headers over 20 pages — **located** | 12 | **14** |
| Nottebohm p.46, hand-read | 6/9, 0 FP | 6/9, 0 FP |
| engraved reference sheet | 5/5, 0 FP | 5/5, 0 FP |
| braced piano, 60 staves × 2 resolutions | 0 FP | 0 FP |

Every new read on both corpora was rendered and checked against the page:
**19 of 20 are a C clef with the box on the glyph**, and every one of main's
twelve orchestral reads survives. Two Nottebohm reads are lost (p56 s9,
p224 s7, both genuine). The one false positive is Nottebohm p.200 staff 7, a
bass clef — see below.

### It was not the brace, and there was never a big object

The handoff attributed the fusion to the system brace and to ink from
neighbouring staves. **In all 105 oversized clusters the tallest connected
component was under two staff spaces** — median 0.9 to 1.4. There was never a
large object in these headers. There were small ones, stacked, and a grouping
rule that could not see the stacking: `cluster_components` grouped ink by its
horizontal gap alone, on the reasoning — written in its docstring — that a clef
is the only thing in its strip. A staff header is a narrow column that also
holds the movement heading, the rehearsal letter, the page number and the
neighbouring staff's ink. Grouped on x alone, the clef and all of that became
one column 6–10 spaces tall.

So the fix is not to split an oversized cluster but never to build one:
`cluster_components` now requires proximity in **both** axes, as connected
components of the "near enough" relation.

### The restriction that makes it safe, and how it was learned

The vertical limit applies **only to ink standing clear of the staff's own five
lines.** Ink that touches the staff belongs to whatever glyph is printed there,
however the morphology broke it up, and is never separated.

That restriction is the whole safety argument, and the first version did not
have it. Without it the rule takes a treble clef apart at the waist on an
orchestral scan and reads the upper half as an alto clef: **seventeen invented
clefs across twenty pages of Beethoven 5**, on a corpus where main invents
none. It passed every check that existed at the time — the hand-read page, the
engraved reference sheet, and sixty staves of braced piano — because all three
are either vocal-clef material or clean engraving. It took adding an orchestral
scan to see it.

The same round produced three gates tuned on Nottebohm alone (an aspect floor
at 0.42, the height cap dropped to 4.5, a width floor at 1.0). Each sat in what
looked like a clean gap between two measured populations. All three are
**reverted**: against Beethoven 5 they reject genuine viola clefs, which
present at aspect 0.22 and 0.32 and at height 4.55, well inside the range the
Nottebohm-only sample said was impossible. A threshold that separates two
populations on one corpus is a fact about that corpus until a second one
agrees.

### The tolerance

1.0 staff spaces, and both bounds are measured.

| tolerance | Nottebohm located | Beethoven 5 | of which invented |
|---|---:|---:|---:|
| 0.30 | 63 | 37 | ~21 |
| 0.60 | 61 | 18 | 2 |
| 0.80 | 60 | 15 | 1 |
| **1.00** | **59** | **14** | **0** |
| 1.25 | 56 | 14 | 0 |
| 1.50 | 56 | 14 | 0 |

Below 1.0 a G clef comes apart even when both halves touch the staff — the
tail detaches at 0.49 spaces on Beethoven 5 — and a G clef's body alone is the
size and shape of a C clef. Above 1.0 the heading fuses back on. The two
populations are far apart (a glyph's internal gaps are under half a space, a
heading sits 1.68 spaces clear at the median), so this is a gap, not a
tightrope.

### The remaining false positive, and why it is not a threshold away

Nottebohm p.200 staff 7 is a bass clef read as alto. By the numbers a bass clef
is a plausible C clef — this one measured width 2.55, height 2.73, symmetry
0.79, all inside the range of real C clefs on the page — and the F-clef dot
veto is the only thing that separates them. On that print the dots merge into
the clef's body under thresholding: one survives as a 0.23 × 0.41-space smear
that fails the roundness test, the other has run into the key-signature flat.

Two candidate discriminators were measured and both fail. Horizontal ink
centroid: the false positive is 0.446, inside the real clefs' 0.400–0.656.
Left–right mirror symmetry: 0.785, *higher* than most real clefs (0.340–0.848).
And the cluster's vertical ink profile has no internal hole, because the flat
sign fills the gap between the clef's two halves.

So this needs a dot veto that tolerates a merged or distorted pair, or a G/F
family check from another source — not a threshold move. Loosening the dot
gates is the safe direction to try: a false veto costs a missed clef, which is
cheap, while a missed veto costs a wrong clef, which is not.

### Dead ends from this pass

- **The traced staff-line removal** (`erase_staff_lines`, which the
  key-signature locator uses) applied to the clef locator. It is better at
  keeping a glyph connected and worse here: it erases the archaic clef's rungs,
  which sit *on* the staff lines, and the glyph shrinks below the height floor.
  "Only debris" went 7 → 42. The generic stripper is right for this material
  precisely because it removes only runs ≥ 1.5 spaces, and an archaic clef's
  bars are shorter than that.
- **Bridging the generic stripper's cuts** — restoring ink inside a removed
  band where a stroke continues through it. No measurable change at all. The
  fragmentation is not what was fusing the clusters.
- **Making the tolerance adaptive** by bridging only where the horizontal
  stripper actually removed ink, so it follows the printed line thickness
  rather than a constant. No better than the constant. The premise was wrong
  anyway: the erased band measures 0.18–0.27 spaces at the median on Nottebohm,
  Beethoven 5 and engraved piano alike, so line thickness is not what differs
  between them.
- **Dropping cluster members that lie wholly outside the staff's own lines**,
  with or without a margin. This is the clipping the handoff warns about, and
  the warning is right in both directions: at zero margin a treble clef's
  severed tail is dropped and its head passes as a C clef (9–12 piano false
  positives), and at a 0.75-space margin it costs four genuine orchestral
  clefs, because a C clef on the top or bottom line has real ink out there and
  dropping it destroys the symmetry the reading depends on.
- **Splitting on the cluster's internal ink profile** (a glyph should be
  vertically continuous). Disproven on the case it was designed for: the bass
  clef's two halves are bridged in the profile by the key-signature flat beside
  them, so its largest internal hole is 0.0.

### A measurement trap worth recording

`clef_ground_truth_eval.py` and the harness around it must be run from the tree
being measured. A helper script written during this session carried an absolute
`sys.path` entry pointing at its own worktree, so runs launched inside a
`git worktree` of `main` silently imported the branch and reported the branch's
numbers as the baseline — which made a change look like it had gained two
staves on the hand-read page when it had gained none.
`check_clef_precision.py` and `probe_clef_rejection.py` both root themselves
off `__file__` for this reason.

## What this still does NOT fix

Clef coverage on this book is 20%. Where a cell contains its clef, the locator
reads it and reads it correctly; what remains is upstream. Two limits, both
measured, neither addressed:

### 1. Body text is detected as staves

`staff_detector._ink_profile` counts ink *pixels* per row and requires a row to
clear `MIN_LINE_LENGTH_FRAC` (35% of page width). A row of justified body text
easily clears that on total ink while containing no long run at all, and five
consecutive text baselines have regular enough spacing to pass the 5-line
grouping test. So a paragraph becomes a "staff", with a clef and measures of
its own. Two of Nottebohm p.90's seven staves are text columns; two of p.92's
twelve are.

The natural fix — score rows by longest contiguous run instead of total ink —
was measured and is **wrong**. Across 274 detected staves on eight scores, the
minimum per-line run fraction separates badly: genuine, full-width staves in
Boléro, WTC, La Mer and Handel score as low as 0.018, because heavy notation
ink interrupts the line. Rejecting on line continuity would discard real staves.

What *does* separate cleanly is **staff span versus the page's median span**:

| | span | page median span | x-extent (of page width) |
|---|---|---|---|
| Nottebohm p.92 text "staves" | 215, 216 | 62 | 0.021, 0.015 |
| every genuine staff measured | within ~10% of median | — | 0.147 … 0.908 |

Text baselines sit ~3.5× further apart than staff lines, and the x-extent of the
resulting "staff" is a couple of percent of the page (the longest ink run on a
text row is one word). Either signal rejects the text blocks without touching a
single genuine staff in the corpus.

**Not implemented here.** It is a Phase-1 change, and Phase 1 currently has no
trustworthy regression baseline — `test_pipeline.py`'s staff- and measure-count
assertions already fail in this tree from earlier drift (identically on `main`,
verified). Changing staff detection without a working Phase-1 baseline is how
this project has been bitten before. The measurements above are the input to
doing it properly.

### 2. Some staff-start cells still begin after the clef

The gross form of this is fixed (see the Phase-1 section above) and it is what
took p.31 from 6/12 to 9/12. It has not gone away entirely: on pages laid out
as several short exercise fragments side by side, `_staff_x_extent` can still
land past the clef, and the cell then opens mid-measure with nothing for any
reader to find. This is the largest single contributor to the 80% of staves
with no clef read.

### 3. Dense orchestral headers

The locator abstains on Mahler 5 p.11 — ink-heavy headers, no glyph-sized
cluster it will commit to. The decoupled `--clef-weights` specialist remains the
better route there, and the two compose: the specialist runs first, the locator
only where it stayed silent.
