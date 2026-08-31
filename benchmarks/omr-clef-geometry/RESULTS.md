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
fix, so it is not a regression from any of them.

**Diagnosed, and fixed on a branch that is deliberately not merged.** The
F-clef dot veto was firing on the tenor clef: a C clef's right-hand lobes, cut
into pieces by the staff lines through them, are round, correctly sized,
aligned in x and a staff space apart — the dot signature exactly, and whether
it fires is luck of where the lines fall. Requiring the pair to stand ALONE in
its column (an F clef's dots do; a C clef's lobes have a stack around them)
restores 5/5 with treble and bass still declined, keeps Bach at 0 false
positives, and takes orchestral precision from 1/2 to 3/4. It is not merged
because it makes shipped key signatures worse — see
`NEXT_SESSION_HEADER_CLUSTER.md` → "The F-clef dot veto fires on C clefs".

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

### Precision on orchestral prints

Nottebohm is the material the locator was built for. Orchestral scores are what
most real work is, and they behave differently — a bracket, instrument names
and stacked part numbers in the header, and two thirds of the staves carrying
the G and F clefs the locator is supposed to decline. There is hand-read ground
truth for two such pages sitting in the key-signature benchmark, so:

```bash
python3 benchmarks/omr-clef-geometry/eval_orchestral_clefs.py
```

On `main` today: **2 staves located, 1 correct** — the viola's alto clef read
correctly on Beethoven 5 p.2, and a bassoon's bass clef misread as tenor. The
unmerged dot-veto fix takes it to 4 located, 3 correct; the bassoon error is
untouched by it and is the oldest thing on this list.

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

## The fused cluster: diagnosed, fixed, and held back (2026-08-28, second pass)

The cause is settled and the fix is written, tested and measured. It is
**off by default** (`ClefLocatorConfig.cluster_y_gap_spaces`), because the
coverage it buys lands disproportionately on staves where a different, older
hole is open. Both halves of that sentence are measured below.

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
`cluster_components` can now require proximity in **both** axes, as connected
components of the "near enough" relation.

### What it is worth

| | main | rule on |
|---|---:|---:|
| Nottebohm, 205 headers over 20 pages | 61 located | **72** |
| Beethoven 5, 396 headers over 20 pages | 27 located | **33** |
| reads lost or changed on either | — | **0** |

### The restriction that makes it safe, and how it was learned

The vertical limit applies **only to ink standing clear of the staff's own five
lines.** Ink that touches the staff belongs to whatever glyph is printed there,
however the morphology broke it up, and is never separated.

The first version did not have that restriction. Without it the rule takes a
treble clef apart at the waist on an orchestral scan and reads the upper half
as an alto clef: **seventeen invented clefs across twenty pages of Beethoven
5**, on a corpus where main invents none. It passed every check that existed at
the time — the hand-read page, the engraved reference sheet, and sixty staves
of braced piano — because all three are either vocal-clef material or clean
engraving. It took adding an orchestral scan to see it.

The same round produced three gates tuned on Nottebohm alone: an aspect floor
at 0.42, the height cap dropped to 4.5, a width floor at 1.0. Each sat in what
looked like a clean gap between two measured populations. All three are
**reverted**: against Beethoven 5 they reject genuine viola clefs, which
present at aspect 0.22 and 0.32 and at height 4.55 — well inside the range the
Nottebohm-only sample said was impossible. A threshold that separates two
populations on one corpus is a fact about that corpus until a second one
agrees.

### The tolerance

1.0 staff spaces, bounded on both sides. Below it a G clef comes apart even
when both halves touch the staff — the tail detaches at 0.49 spaces on
Beethoven 5 — and a G clef's body alone is the size and shape of a C clef:
measured, that invents two clefs at 0.6 and one at 0.8. Above it the heading
fuses back on and coverage falls. The populations are far apart (a glyph's
internal gaps are under half a space; a heading stands 1.68 spaces clear at the
median), so this is a gap, not a tightrope.

### Why it is off

Of the 19 staves the rule adds across both books, **14 are right and 5 are bass
clefs read as C clefs.** Every one of the five is the same pre-existing hole:
`_has_f_clef_dots` is the only thing separating an F clef from a C clef — by
width, height and symmetry a bass clef is a plausible C clef — and on these
prints the two dots merge into the clef's body under thresholding, so there is
no pair to find. One survives as a 0.23 × 0.41-space smear that fails the
roundness test; the other has run into the key-signature flat.

The rate is what decides it. Main's own located reads are wrong at roughly 8%
on this material — it has bass-clef misreads of its own, on Nottebohm p.44 and
elsewhere — and the reads this rule adds are wrong at 26%. Coverage bought at a
worse precision than the layer already has is the one trade this layer refuses.

Three candidate discriminators were measured and all three fail:

| | correct reads | the wrong ones |
|---|---|---|
| symmetry | 0.701 … (median 0.862) | 0.700 – 0.801 |
| horizontal ink centroid | 0.400 – 0.656 | 0.446 |
| largest internal hole in the ink profile | median 0.00 | 0.00 |

The last one is the sharpest disappointment: a glyph *should* be vertically
continuous, and the bass clef's two halves *are* separated — but the
key-signature flat standing beside them fills the gap in the column's profile.

The dot-veto change scoped on `main` will not close this either. It makes the
veto fire **less**, to stop it eating the engraved reference sheet's tenor clef,
which is the opposite of what these staves need.

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
  rather than a constant. No better than the constant, and the premise was
  wrong anyway: the erased band measures 0.18–0.27 spaces at the median on
  Nottebohm, Beethoven 5 and engraved piano alike, so line thickness is not
  what differs between them.
- **Dropping cluster members that lie wholly outside the staff's own lines**,
  with or without a margin. This is the clipping the handoff warns about, and
  the warning is right in both directions: at zero margin a treble clef's
  severed tail is dropped and its head passes as a C clef (9–12 piano false
  positives), and at a 0.75-space margin it costs four genuine orchestral
  clefs, because a C clef on the top or bottom line has real ink out there and
  dropping it destroys the symmetry the reading depends on.

### The corpus that was missing

The precision harness is now four corpora, not three, and the fourth is the one
that mattered:

    python3 benchmarks/omr-clef-geometry/check_clef_precision.py

`beethoven5-clef-spot-check.json` lists seventeen staves of a scanned
orchestral score, read off the rendered header crops by eye — fourteen carrying
a real C clef and three carrying a treble clef that must never yield one. Two
of those three are the staves the unrestricted vertical rule invented clefs on,
so the corpus encodes the specific failure rather than a general hope of
catching one. It is a spot check, not ground truth for the page, and it says
nothing about coverage; `probe_clef_rejection.py` is for that.
`eval_orchestral_clefs.py` complements it with real hand-read truth for two
pages.

### Two measurement traps worth recording

**Path pollution.** A helper written during this session carried an absolute
`sys.path` entry pointing at its own worktree, so runs launched inside a
`git worktree` of `main` silently imported the branch and reported the branch's
numbers as the baseline. It made a change look like it had gained two staves on
the hand-read page when it had gained none. `check_clef_precision.py` and
`probe_clef_rejection.py` both root themselves off `__file__`.

**Fixtures that do not survive the pipeline.** Three synthetic glyphs in
`test_clef_locator.py` were drawn as filled blocks, and
`strip_horizontal_rules` erases any run of 1.5 staff spaces or more — so the
G clef arrived as its 0.4-space tail, the heading was removed before it could
fuse with anything, and the tests were passing whatever the code did. A test
whose fixture is destroyed upstream asserts nothing, and it will not tell you.

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


---

## The veto could not see the dots (2026-08-31)

**The recorded diagnosis was wrong, and being wrong about it is why five sessions
of threshold work went nowhere.** `_has_f_clef_dots` was not failing because the
dots had merged into the clef's body. It was failing because it had never been
shown them.

Two crops stood between the veto and its evidence, and neither was a decision
about F clefs:

* `locate_clef` searches `mask[:, :hw]` — the left `header_frac` (0.30) of the
  cell — to keep note ink from becoming a candidate. That strip is about
  candidate SELECTION. It was then passed to the veto as if it were the page.
* `_has_f_clef_dots` looked only *inside* the candidate's own bounding box.

An F clef's dots sit to the RIGHT of its body. So on a clef whose body ends near
the strip's edge, the dots fall outside both crops, and no threshold anywhere
could have found them.

### The case that shows it

Beethoven 5 p.54 staff 8, an unmistakable bass clef, read as **alto**. Its header
window is 16.3 staff spaces wide and contains the dots plainly. The mask the veto
received was 106 px of a 352 px cell, and the candidate box ended at pixel 106 —
flush against the edge. The dots were four pixels past it.

Traced with the crops removed, the dots appear immediately, correctly paired,
0.59 × 0.86 and 0.64 × 1.00 spaces, one space apart, aligned in x, right of the
body — and are then rejected on **height**, against a 0.75-space ceiling.

Note what that says: the widths are exactly dot-sized. The corruption is
**vertical**, and it is the staff-line stripper leaving a stub where the line ran
under each dot.

### What shipped: the structural fix, which is neutral

The veto now gets the full mask and searches `dot_search_right_spaces` (1.5)
past the candidate's right edge, with the "right of the middle" test still
measured against the BODY so widening the window cannot move it.

Measured, and it is exactly neutral on every corpus:

| | located (Nottebohm, 206 cells) | orchestral misses | reference | FP |
|---|---:|---:|---:|---:|
| before | 69 | 6 | 5/5 | 0 |
| **after** | **69** | **6** | **5/5** | **0** |

One cell moves from the dot-veto branch to `ambiguous line snap`; nothing is
gained or lost. It is landed because it is a correctness fix — the veto can now
see what it is meant to judge — and because no threshold work on this veto means
anything until it can.

### What did NOT ship, and why

Loosening the height ceiling to 1.15 spaces (paid for by requiring the two dots
to have matching widths) **does** veto the p.54 bass clef. It also costs:

| arm | located | orchestral misses |
|---|---:|---:|
| baseline | 69 | 6 |
| clustering ON, veto as-is | 77 | 5 |
| **loosened veto** | 68 | **8** |
| clustering ON + loosened veto | 76 | **7** |

Two real orchestral C clefs and one Nottebohm cell, in both clustering states.

**And its benefit appears in no corpus at all.** The thing it fixes — a bass clef
read as a C clef — is not in the reference sheet, not in the piano set, not in
the orchestral spot check, and not on Nottebohm p.46. The only evidence it works
is one case found by rendering candidates and looking at them.

So the trade is: a measurable cost against an unmeasurable benefit. That is the
one trade this layer refuses, and refusing it is the same rule that keeps the
clustering off.

### The next step is a corpus, not a threshold

`check_clef_precision.py` grew its orchestral corpus once before, for exactly
this reason — three corpora had all passed a change that read seventeen treble
clefs as alto clefs. It needs to grow again: a set of staves that carry a **bass
clef the locator is liable to call a C clef**, so the benefit of a veto change
is a number rather than an anecdote.

Beethoven 5 p.54 staff 8 is the first member. Collecting the rest means running
the locator with clustering ON, rendering every located candidate, and reading
them by eye — the same method that produced the orchestral spot check.

Until that exists, the honest position is that the veto's blindness is **fixed**
and its **thresholds are still unmeasurable**, which is a better place to be than
before: the earlier note said the fix was "waiting behind a config default", and
it is not — it is waiting behind a corpus.


---

## The corpus the veto never had (2026-08-31)

The section above ended: *"the next step is a corpus, not a threshold."* Here it
is, and it changes the picture in a way no threshold sweep would have.

`beethoven5-clef-sweep.json` — **91 staves**, being every staff the locator
LOCATES a C clef on across pages 2-80 of the scanned Beethoven 5, with clustering
on, each header crop rendered and the glyph read by eye. **Seventeen are bass
clefs and seven are treble clefs.** Those twenty-four are the reads a veto exists
to remove, and not one of them appeared in any corpus before. The remaining
sixty-seven are genuine C clefs, and they are the counterweight — without them a
veto that fired on everything would score perfectly.

One staff was excluded rather than guessed at (p66 s10, crop too tight to read).

### The first thing it says is about the code that already ships

```
reference 5/5 exact | coverage 7/9 | orchestral misses 6 | sweep misses 10
                                                       | FALSE POSITIVES 10
```

**The shipped locator has ten false positives.** It had zero on all four previous
corpora, and that zero was the headline every change in this area was steered by.
It was not measuring what it appeared to measure: the corpora simply contained no
bass clef the locator was liable to call a C clef, so there was nothing there to
get wrong.

### And it settles the veto question, with both sides visible at last

| arm | orchestral misses | sweep misses | FALSE POSITIVES |
|---|---:|---:|---:|
| **shipped** — clustering off, veto as-is | 6 | 10 | **10** |
| clustering ON, veto as-is | 5 | 7 | **11** |
| clustering off, **loosened veto** | 8 | **37** | 7 |
| clustering ON, loosened veto | 7 | **36** | 7 |

The loosened height ceiling buys **three** fewer false positives and costs
**twenty-seven** genuine C clefs. That is not a close call, and it is not what the
one-case anecdote suggested — the previous pass could see the cost on two
orchestral staves and guessed the benefit was worth it. With the benefit measured
it is worth a third of what it costs.

**It stays refused, and now for a reason with a number on it.**

### What the corpus opens instead

Two things, both larger than the veto:

1. **Ten false positives in the shipped configuration.** Seventeen bass clefs and
   seven treble clefs get located; ten of the twenty-four survive every gate.
   That is the real state of the layer and it is now visible for the first time.
2. **Every `mezzosoprano` read in the sweep is a misread — 5 of 5.** *(An earlier
   draft of this section said "7 of 7 G clefs"; the sweep names mezzosoprano five
   times, four of them G clefs and one an F clef.)* Acted on below.

And the clustering question reads differently now. It costs **one** extra false
positive (10 → 11) and buys three fewer sweep misses and one fewer orchestral
miss. That is a far more defensible trade than "14 right and 5 wrong" implied —
but it is a trade to make deliberately, against the number above, not on the
strength of a zero that meant nothing.


---

## Mezzosoprano: a rarer answer has to be better evidenced (2026-08-31)

**False positives 10 → 6, and nothing else moves at all.**

Of the 101 candidates the locator names in the sweep, five are called
mezzosoprano and **all five are wrong** — four G clefs and one F clef. The G
clefs are not a random error: a G clef curls around the second line from the
bottom, which is exactly the line mezzosoprano names, so a surviving fragment of
one balances there and gets the one label that fits.

The separation is wide, and it is in symmetry:

| | symmetry |
|---|---|
| the one real mezzosoprano in any corpus (reference sheet, engraved) | **0.981** |
| the five misreads | 0.712 – 0.815 |

Banning the clef would have cost the real one and taken the reference sheet off
5/5. Raising the general symmetry floor would have cost the scanned alto and
tenor clefs, which live at 0.70–0.80 themselves — that is the gate the earlier
sessions kept running into. So the floor is applied **to this answer only**:
`min_symmetry_mezzosoprano = 0.90`, sitting between the two populations.

| | reference | coverage | orch misses | sweep misses | **FALSE POSITIVES** |
|---|---:|---:|---:|---:|---:|
| shipped, before | 5/5 | 7/9 | 6 | 10 | **10** |
| **shipped, after** | **5/5** | **7/9** | **6** | **10** | **6** |

Nottebohm is untouched — 69 located before and after — because twenty pages of
vocal-clef counterpoint name mezzosoprano **zero** times, with clustering on or
off. There was no cost to find.

### It also moves the clustering question

| arm | Nottebohm located | orch misses | sweep misses | FALSE POS |
|---|---:|---:|---:|---:|
| shipped + floor | 69 | 6 | 10 | **6** |
| clustering ON + floor | **77** | **5** | **7** | 7 |

Clustering now buys **eight** more located clefs and four fewer misses for **one**
more false positive. That is a far better trade than it has ever looked — the
false-positive RATE is roughly flat (6/69 against 7/77) rather than worse. It is
still not switched on here, because that is a deliberate decision to take against
these numbers rather than a side effect of a veto fix, but the case for it is now
a real one.


---

## The clustering goes on (2026-08-31)

The section above left it as "a real one, but a deliberate decision to take
against these numbers". Taken: `ClefLocatorConfig.cluster_y_gap_spaces = 1.0`.

| arm | located (Nottebohm) | reference | coverage | orch misses | sweep misses | FALSE POS |
|---|---:|---:|---:|---:|---:|---:|
| off, as shipped | 69 / 206 | 5/5 | 7/9 | 6 | 10 | **6** |
| **ON** | **77 / 206** | 5/5 | 7/9 | **5** | **7** | **7** |

Both harnesses, both re-measured from scratch rather than quoted forward.
**Eight more located clefs and four fewer misses for one more false positive**,
and the extra one is p54 s8 — the bass clef the previous session predicted it
would be, so the two items compose exactly as it said.

The test this layer applies is the RATE, not the count: 6/69 against 7/77 is
flat. "Coverage bought at a worse precision than the layer already has" is the
trade it refuses, and this is not that.

Also checked, because clustering changes what the whole header layer sees:
`eval_score_order` 11/12 position, 5/10 read clefs, 23/23 true clefs —
unchanged; and `eval_pipeline_clefs --contextual --dossier --assist vision`
**69/69**, base-3 52/52, with the CV locator supplying two of the sixty-nine and
both correct.

The two tests that pinned the old default now pin the new one, and the "when it
is off" test keeps its case by naming the config explicitly rather than relying
on the default — the behaviour it describes is still what the page does without
the rule, and is worth keeping visible.

---

## A second edition — and the number gets worse because the measurement got honest (2026-08-31)

`mahler5-clef-sweep.json` — **105 staves**, Edition Peters, Mahler 5, pages
4–220 every fourth page. Built exactly as the Beethoven sweep was: every staff
the locator LOCATES a C clef on, its header rendered, the glyph read by eye,
with the genuine C clefs kept as the counterweight. **64 are real C clefs. 41
are not** — 24 treble and 17 bass.

Two things are different this time. The tool that builds it is committed
(`sweep_located_clefs.py`), so a third edition costs an afternoon rather than a
session. And `check_clef_precision.py` now runs **every** sweep corpus on every
invocation, each naming its own score, so adding one is a file and no code.

### What a second printer's ink shows that the first could not

Beethoven's false positives are all misread CLEFS — an F clef, or a fragment of
a G clef, that survives the shape gates. **Twenty-four of Mahler's forty-one are
not a clef at all.**

Peters prints the stacked instrument numbers — `1/2`, `1/2/3` — and the brace's
curl to the LEFT of the system's bracket, close enough to fall inside the header
window. A stack of two or three numerals is glyph-sized, and it is vertically
symmetric, because a column of numerals is. The locator takes the leftmost
glyph-sized cluster, so it takes those. That family does not exist in the
Beethoven scan, and it is the single largest false-positive source here.

### So the headline number moves a long way

```
reference 5/5 exact | coverage 7/9 | orchestral misses 5 | sweep misses 7
                                                        | FALSE POSITIVES 48
```

The four oldest corpora said `FALSE POSITIVES 0`, and it meant "nothing here to
get wrong". The Beethoven sweep took it to 6, then 7 with clustering. The Mahler
sweep takes it to **48** — and not one of the 41 it adds is a regression. Every
one was already happening, on every run, unmeasured.

That is the second time in two sessions that the number this layer is steered by
turned out to be a property of the corpus rather than of the code. Worth stating
plainly: **the false-positive count of a CV reader measures the corpora you own,
until the corpora are built from the reader's own output.** Both sweeps are,
which is why they can say this and the others could not.

One caveat to keep when reading a sweep corpus's MISS column: it is built from
what the locator located, so at the moment of building its misses are ZERO by
construction. Beethoven's 7 are real because the config moved after it was built
(the mezzosoprano floor, then the clustering); Mahler's 0 is not yet evidence of
anything.

---

## The tenor symmetry floor: refused, by the second edition (2026-08-31)

The handoff's lead was a tenor-specific symmetry floor in the shape of
`min_symmetry_mezzosoprano`. On the Beethoven sweep the two populations carrying
the label `tenor` do not overlap, and such a floor removes every tenor misread
at no cost at all. The handoff also said, in bold, not to ship it on that
evidence: a 0.014-wide gap, on 9 clefs and 5 misreads, from one edition.

It was right to say so. `clef_symmetry_populations.py`, over both corpora:

```
beethoven5-clef-sweep.json
  alto     real  50 [0.783 - 0.932]   misread  3 [0.722 - 0.775]   GAP +0.008
  tenor    real  10 [0.809 - 0.959]   misread  4 [0.702 - 0.795]   GAP +0.015

mahler5-clef-sweep.json
  alto     real  45 [0.716 - 0.962]   misread 33 [0.712 - 0.868]   OVERLAP 0.152
  soprano  real   0                   misread  1 [0.740 - 0.740]
  tenor    real  19 [0.708 - 0.954]   misread  7 [0.711 - 0.845]   OVERLAP 0.137
```

**The +0.015 gap becomes a 0.137 overlap.** Mahler's real tenor clefs start at
0.708 — below every Beethoven misread — and its tenor misreads reach 0.845,
above most Beethoven real clefs. A floor anywhere in the Beethoven gap costs
real C clefs on the other edition's very first page. The alto gap of +0.008 dies
the same way, at 0.152.

**Refused, and the refusal is the result.** The mezzosoprano floor was not luck:
it works because a genuine mezzosoprano is essentially absent from this
repertoire, so its "real" population is one engraved reference glyph at 0.981
and there is nothing under the floor to lose. Tenor and alto are common, their
real instances run down to 0.708, and there is no room beneath them. Symmetry is
not the axis that separates these two populations.

The general lesson, which this area has now paid for three times: **a threshold
that separates two populations on a single corpus is a measurement of that
corpus.** The rule that survives is not "check the gap" but "check the gap on
ink from a different press".

---

## Where the false positives actually are — the lead that replaces the floor (2026-08-31)

If shape does not separate the numeral family, position might: a clef is printed
ON the staff, and those numerals are printed before the staff begins.
`probe_false_positive_geometry.py` measures the ceiling of that idea without
shipping anything — for every read in each sweep corpus, how far the located
cluster's right edge sits from the first column of the staff's own printed
lines, in staff spaces (positive = the cluster ends before the staff starts):

```
beethoven5-clef-sweep.json
  real      59 reads   median -3.33  range [-4.50, -0.38]   entirely before the staff:  0
  misread    6 reads   median -2.88  range [-3.94, -2.54]   entirely before the staff:  0

mahler5-clef-sweep.json
  real      64 reads   median -3.33  range [-4.59, +1.96]   entirely before the staff:  2
  misread   40 reads   median +0.90  range [-3.92, +2.70]   entirely before the staff: 27
```

**A rule refusing a cluster that ends before the staff's lines begin would
remove 27 of Mahler's 40 false positives and cost 2 of its 64 real clefs, and is
exactly neutral on Beethoven** — 0 removed and 0 lost, because every Beethoven
false positive is a real clef misread, sitting on the staff where it belongs.
(The probe abstains on a handful of rows where it cannot find staff metrics or a
full-width line, which is why the totals are 59/6 and 64/40 rather than 60/7 and
64/41.)

That is a far better shape of lead than a threshold: it is aimed at a family
whose cause is understood, it is measured on both editions, and it is honest
about its cost. **It is not shipped here.** It is a new mechanism rather than the
job that was scoped, and it would have to clear both harnesses on both editions —
including Nottebohm coverage, where the clef sits at the staff start and the rule
ought to be free, and the reference and piano sheets, where it must stay at 5/5
and 0 — before it could be.

### One measurement trap this probe fell into first, recorded because it is general

The first version took the staff's left edge to be the leftmost horizontal ink
in the cell, and reported that **every** staff began at column 0. At the
canonical scale (staff span 400 px, so a staff space is 100 px) a bold serif's
crossbar comfortably clears a 1.5-space horizontal opening, so the instrument
name and the numerals themselves leave "horizontal" fragments at the very left
of the window. The fixed version keeps only components at least four staff
spaces wide — a staff line is the one horizontal that runs the width of the
cell — and the misread median moves from −1.00 to +0.90, which is the difference
between "this idea does nothing" and "this idea reaches two thirds of them".
The lesson is the one this file keeps recording: when a geometric probe reports
that a property holds for everything, suspect the operator before the data.


---

## The position rule, shipped and measured — FALSE POSITIVES 48 → 21 (2026-08-31)

The section above measured a ceiling and did not ship it. Shipped now, as
`ClefLocatorConfig.require_cluster_on_staff`, and it hit that ceiling exactly.

| | before | after |
|---|---:|---:|
| Nottebohm located | 77 / 206 | **79 / 206** |
| reference sheet | 5/5 | 5/5 |
| piano false positives | 0 | 0 |
| coverage (Nottebohm p.46) | 7/9 | 7/9 |
| orchestral spot check, misses | 5 | 5 |
| sweep misses | 7 | 9 |
| **FALSE POSITIVES** | **48** | **21** |

Per edition, which is the split that matters:

| sweep | false positives | misses |
|---|---|---|
| beethoven5 | 7 → **7** | 7 → **7** |
| mahler5 | 41 → **14** | 0 → **2** |

Twenty-seven removed and two lost on Mahler; **exactly** neutral on Beethoven.
That is what `probe_false_positive_geometry.py` predicted, to the staff, which
is the strongest evidence available that the rule does the thing it was designed
to do and nothing else. Guards: 1114 tests, `eval_score_order` 11/12 · 5/10 ·
23/23 byte-identical, `eval_pipeline_clefs --contextual --dossier --assist
vision` 69/69 with base-3 52/52 and both of the CV locator's two staves correct.

### It is a SKIP, not a rejection — and that is where the extra coverage came from

The obvious implementation is "refuse this staff". The one that shipped is
"skip this cluster and keep looking", on exactly the reasoning the ink-fraction
and minimum-width tests already carry: **a cluster is only worth STOPPING for if
it could be the clef, and the real one is further right, behind the bracket.**

That choice is why Nottebohm coverage went UP, 77 → 79, on a change whose whole
purpose was to remove reads. Two staves there had glyph-sized margin ink
standing in front of a clef that the locator had been stopping short of. A
rejecting implementation would have scored the same 21 false positives and cost
those two.

The probe's branch tally shows where the cells went — `only debris` 25 → 11,
with 17 now reported under `margin ink only, before the staff`. They were being
attributed to debris, which is a different cause with a different remedy.

### What it costs, looked at rather than priced

The handoff said to look at the two real clefs before accepting the trade. They
do not share a cause, and only one of them is a real loss.

**p188 s12 is not a loss at all.** The corpus records it as a C clef, and it is
one — but the ink the locator was reading is the stacked instrument numbers, not
the clef (the corpus row says so: *"located ink is the stacked instrument
numbers, not the clef"*). The rule correctly refused them. The staff scored as a
hit before because the corpus asks whether the STAFF carries a C clef, not
whether the read was made of the right pixels. A right answer for the wrong
reason has stopped being given, and the score got worse for it.

**p48 s12 is a real loss, and its cause is diagnosed.** The clef sits plainly on
the staff, but the staff's printed lines are so broken at the head of the system
that no run four staff spaces long exists until 677 px in — well past the clef —
so "where the staff begins" is measured wrong and the clef is judged to be in
the margin.

This is the failure `staff_header` was written about, in its own words: *the
individual staff lines are broken, but the staff BAND is not*. The fix is to
take the left edge from the band's ink profile, the way `_walk_left` does,
rather than from the longest horizontal run — one genuine clef across two
editions is what it is worth, and it is not stacked onto this measurement here.

### Both editions now fail the same way, which they did not before

Of the 21 that remain, **19 are bass clefs and 2 are treble** — 7 on Beethoven
(6 bass, 1 treble) and 14 on Mahler (13 bass, 1 treble). Every one is a real
clef misread, sitting on the staff where a clef belongs.

Before this change the two editions had different problems: Beethoven's false
positives were misread clefs and more than half of Mahler's were margin ink.
They have converged, and what is left is a single cause on both — the F-clef
veto, `_has_f_clef_dots`, failing to fire on a degraded bass clef. That is now
the whole of the remaining false-positive count, and it can be worked on against
two editions at once instead of one.
