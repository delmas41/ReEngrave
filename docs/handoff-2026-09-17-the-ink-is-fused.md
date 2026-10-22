# Handoff: the stems are not a filter problem — the ink is FUSED

**START HERE.** One branch, `claude/ledger-extrapolation-2026-09`, open as
**PR #56**. **Nothing under `tools/` or `backend/` was touched all session** —
`git diff origin/main -- tools/ backend/ CLAUDE.md` is empty. Everything is
measurement, under `benchmarks/` and `docs/`.

**The next job is a RASTER READER for stems.** Section 4 says which one and
why, section 5 says what would falsify it, and section 6 is the part you must
read before trusting any number here.

---

## 1. ⚠️⚠️ FOUR HYPOTHESES DIED THIS SESSION, INCLUDING BOTH SEAN'S AND MINE

This is the most useful thing in the document, because each one was plausible
enough to be built.

| hypothesis | whose | how it died |
|---|---|---|
| ledger drift explains the stem-convention reversal | mine (P4) | correcting to ink truth changes the convention's agreement by **exactly nothing**, 17/32 either way — a one-step error six steps from the middle line cannot flip it |
| `_drop_paired_strokes` is the main stem loss | mine | the arm recovers **73 of 793 (9.2%)**; my raster proxy had implied far more |
| staff-line ERASURE breaks the stems | **Sean's** | reading the ORIGINAL raster recovers **fewer** — 268 vs 287 |
| the 1-pixel opening kernel vs a bowed plate | mine | horizontal pre-dilation at 2/3/5px recovers **3, 3 and 4 heads of 793** |

⚠️ **Two of mine reached Sean as recommendations before the arm ran.** The
cause was one thing and it is worth carrying: **a raster proxy for a filter's
predicate is not a proxy for the filter**, because the filter's input
population is connected COMPONENTS after a morphological opening, not ink.
That proxy over-stated the pair rule and over-stated the height cap (80 heads
→ **17**).

---

## 2. THE STEM DIAGNOSIS IS COMPLETE AND THE REASONS SUM

Litolff Beethoven 5 pp.1-4. `rejection_census.py` replicates the shipped
chain component by component and **asserts per cell that its accepted set is
identical to the real `detect_stems`** — 0 cells drifted.

| why the head has no stem | n | share |
|---|--:|--:|
| **too WIDE** (w > 0.6 spaces) | **237** | 29.9% |
| **too SHORT** (h < 2.0 spaces) | **199** | 25.1% |
| **no component overlaps it at all** | **167** | 21.1% |
| an accepted component, dropped by the pair rule | 73 | 9.2% |
| at a CELL EDGE (0.8 spaces) | 70 | 8.8% |
| too TALL (h > 8.0 spaces) | 47 | 5.9% |

**= 793 exactly.** No residue bucket.

### And the SECOND PUBLISHER was run — the top cause INVERTS

Breitkopf Brahms 1 pp.0-3, same census, same faithfulness assertion, 0 drift.

| why the head has no stem | Litolff | | Breitkopf | |
|---|--:|--:|--:|--:|
| too TALL (h > 8.0 spaces) | 47 | 5.9% | **476** | **31.1%** |
| too WIDE (w > 0.6 spaces) | **237** | **29.9%** | 358 | 23.4% |
| too SHORT (h < 2.0 spaces) | 199 | 25.1% | 298 | 19.5% |
| no component overlaps it | 167 | 21.1% | 197 | 12.9% |
| pair rule dropped an accepted one | 73 | 9.2% | 178 | 11.6% |
| at a CELL EDGE | 70 | 8.8% | 22 | 1.4% |
| **total** | **793** | | **1,529** | |

Both sum exactly. ⚠️⚠️ **The largest bucket INVERTS**: Litolff's is WIDE at
29.9% where Breitkopf's is only 23.4%; Breitkopf's is TALL at **31.1% where
Litolff's is 5.9%** — a 5× difference on the same filter. **A repair tuned to
the Litolff table would miss the biggest Breitkopf cause entirely**, which is
why this ran before the handoff rather than after it.

⚠️ **AND THE GENERALISABLE PART IS WHAT SURVIVES THE INVERSION.** On both
plates the overwhelming majority is *a component EXISTS and is the wrong
SHAPE* — WIDE+TALL+SHORT is **683 of 793 (86%)** and **1,132 of 1,529 (74%)**
— while *no component at all* is only 21% and 13%. **So on both publishers
the ink is there and forms components; they are simply not stem-shaped.**
That is the claim a within-blob reader rests on, and it holds on two plates
whose failure modes otherwise disagree.

⚠️ **The cell-EDGE row is where the two differ most in RATIO** (8.8% vs 1.4%),
which is a fact about how the two plates are BARRED, not about stems.

⚠️ **Three of those filters are NOT keyword parameters** — the edge margin,
the area floor and the 3:1 aspect. That is why `filter_sweep_arm.py`'s
"all four relaxed" ceiling of **287 of 793 (36.2%)** could not see them, and
why that ceiling is a floor on the filters' true cost rather than the whole.

---

## 3. ⚠️⚠️ WHAT IT IS: THERE IS NO STEM COMPONENT TO FIND

Opening one real cell and counting: the morphological opening yields **3
connected components with a median height of 811 px**, in a cell whose staff
spacing is **100 px**. That is **8.1 staff spaces — one blob holding stems,
beams and noteheads together** — and the cap it fails is `> 8.0`.

`detect_stems` is a **connected-component reader**, and on a plate where the
ink is one component there is no stem to isolate. That single fact explains
every result above at once:

* why `too WIDE` is the largest bucket — the notehead survives the opening
  still joined to its stem, which is **the failure `detect_stems`' own comment
  describes** and shrank its kernel from 1.0 to 0.8 spaces to mitigate;
* why the erasure is irrelevant — the fusion is not the staff lines;
* why smearing the page sideways is irrelevant — it fuses it further.

**It is the third independent arrival at the same property.** CLAUDE.md
already records *"Litolff MERGES and Breitkopf SHATTERS"*, and `Q.INK`
measured *the median Litolff cell's largest component holds 46% of its ink*.

---

## 4. THE NEXT JOB: A RASTER READER. TWO OF THEM, AND THEY ARE NOT EQUAL

A merged plate needs a reader that finds a stem **inside** a blob, not one
that hopes the blob is a stem.

### 4a. The one that already works — DIRECTION, and it is cheap

Sean named the convention and it is the tightest discriminator on the thread:
**a stem is attached on the RIGHT going UP, or on the LEFT going DOWN.**
Right-and-down does not exist. `probe_stem_convention.py` measures a run of
ink in a hairline column beside the head, uses **no connected components at
all**, and:

| | Litolff | Breitkopf |
|---|--:|--:|
| agreement with stems we ALREADY read (the control) | **95.9%** (900/938) | **98.2%** (1,468/1,495) |
| `no_stem` heads it can speak for | **472** | **653** |

⚠️ It goes **silent rather than wrong** where it cannot speak — "both legal
cells filled" is 16% of Litolff's abstaining heads and **44% of Breitkopf's**,
the dense-column signature.

⚠️ **It is NOT the convention PR #54 measured at 0.787.** That one is *stem up
if the head is below the middle line*, which chords and two-voice writing
break constantly. This one they do not break.

⚠️⚠️ **AND ITS CEILING IS LOW: PR #54 measured direction as worth
`<voice>2</voice>` 24 → 26. TWO TAGS.** Direction feeds voice separation and
chord grouping and nothing else. **Do not build this expecting a file to
change.** Build it because it is nearly certain and it makes the record
honest.

### 4b. The one worth more — THE STROKE, and it is uncertain

The stroke feeds **beams**, and beams feed **duration**. That is the large
prize, and `A-DUR-8`'s history says so: attaching a note to its beam by its
STEM took an engraved fixture from 12 assessable / 7 correct to **16 / 16**.

What it needs is a reader that recovers the stroke from inside a fused
component — a column-profile or projection method, not a component filter.
**Nothing has been built or measured for this.** Its reach is bounded by
§2's table only in the sense that all 793 are candidates.

⚠️ **Where to start is measured**: the `too WIDE` 237 are components that
CONTAIN the stem (the notehead is joined to it), so they are the population
where a within-blob reader has the most to work with and the truth is nearest.

---

## 5. WHAT WOULD FALSIFY THE PLAN

* **4a**: if the convention's agreement on heads we already read falls below
  ~90% on a third publisher, it is not a reader. It is 95.9 / 98.2 on two.
* **4b**: if the stem's ink inside a fused component cannot be separated from
  the notehead's by a column profile, a within-blob reader is not available
  and the answer is upstream (binarisation, or the detector).
* **Both**: if `probe_stem_ink_raster.py`'s positive control ever falls below
  ~95% — it reads 100.0% / 99.8% today — the raster probes are not measuring
  what they claim and every figure in §4 goes with it.

---

## 6. ⚠️ WHAT IS NOT ESTABLISHED — READ BEFORE QUOTING ANYTHING

* **§3's blob measurement is ONE DOCUMENT** and one spot-checked cell.
  The rejection census IS two publishers (§2) and they disagree at the top —
  see the inversion table. Everything else in §1 (the three dead hypotheses)
  is **Litolff only**: the erasure arm and the slant arm were NOT run on
  Breitkopf, so *"the erasure is not the cause"* is established on the
  merging plate and not on the shattering one.
* **No note has been checked against the print in any stem arm.** Every
  accuracy figure is one of our readings against another — the convention
  against `stem_projection`, both off the same page by different methods.
  **The crop pass is owed and has never been done for stems.**
* **The 8.1-space blob is one spot-checked cell**, not a distribution. It
  explains the direction of the result and does not measure how often.
* **No OMR-NED figure**, deliberately: the metric is symmetric and would pay
  for emitting fewer symbols.
* **Nothing is proposed for a constant move.** The width cap is the largest
  single filter cost (217 heads) and is explicitly NOT recommended: its
  recoveries agree with the convention **83.6%** against a **95.8%** bar,
  i.e. roughly 73% real and 27% junk.

---

## 7. THE OTHER THREADS, PARKED CLEANLY

* **Ledger extrapolation (PR #56's original subject).** The grid extrapolates
  past the staff at 1.000× while Litolff prints rungs at 1.032/1.079/1.048/
  1.111 — half a step behind by the 4th ledger line, **66 of 2,347 heads read
  a diatonic step wrong**, against **0 of 3,337** on Breitkopf, which prints
  0.990/0.992/0.991. Sean's call: **not the next work**, and a
  publisher-specific constant is refused (no factor serves 1.10 and 0.975).
* **The conventions registry.** `docs/engraving-conventions.md`, 114 entries
  merged from 87 measured here + 79 from the literature, conservation
  balancing both ways with none dropped. Sources kept beside it in
  `docs/conventions/`.
* ⚠️ **TWO ERRORS IN `CLAUDE.md` FOUND AND NOT FIXED — Sean's call.**
  1. **`CLAUDE.md:4897`**: *"A barline runs a system's full height and the
     bracket encloses exactly it."* `benchmarks/omr-system-grouping-2026-09/
     research/publisher-conventions.md:127` already calls the bracket half
     *"FALSE and an error in our CLAUDE.md"*. **And the barline half is false
     too**, measured this session: on Litolff the first barline crosses every
     inter-staff gap 7 of 7 and **interior barlines 0 of 68**; on Breitkopf
     nothing crosses every gap, first included. Sean's own statement — *full
     height at the beginning and end, not the bars between* — holds on
     Litolff and is itself publisher-dependent.
  2. `OMR_ARC_RECLASS`'s "+2 edits" is stale (+6/+149 on the current tree),
     and CLAUDE.md contradicts itself on this already.

---

## 8. THE INSTRUMENTS, AND WHAT EACH IS BLIND TO

All under `benchmarks/omr-stem-ink-2026-09/` unless noted.

| file | asks | blind to |
|---|---|---|
| `probe_stem_ink_raster.py` | is there ink beside the head | everything — it fires on 100% of controls too |
| `probe_stem_shape.py` | is the ink stem-SHAPED | cannot tell a stem from a barline alone |
| `probe_stem_convention.py` | right-up / left-down | silent on dense columns by design |
| `pair_rule_arm.py` | the pair rule, for real | one filter |
| `filter_sweep_arm.py` | every KEYWORD filter, and the ceiling | the 3 hardcoded filters |
| `rejection_census.py` | the first test each component fails | is a replication — asserts faithfulness per cell |
| `erasure_arm.py` | erased vs original raster | checks the erased variant EXISTS first |
| `slant_arm.py` | the 1-px kernel vs a bowed plate | widens the width cap with the dilation |
| `width_cap_check.py` | are the width recoveries real | convention vs convention, not print |

⚠️ **Every arm re-cuts the cells and proves the re-cut reproduces the record
(783/783 cells, 1,920 = 1,920 strokes) before reporting a delta.** The whole
cutting and reading path is byte-identical between the record's own commit
(`9d4ccc85`, `dirty: true`) and this tree — checked, because the record was
gathered dirty.

⚠️ `library/_shared-records/` holds both records; `recordstream.py` (under
`benchmarks/omr-ledger-extrapolation-2026-09/`) streams the 443 MB Breitkopf
one without parsing it whole — `json.load` on it is several GB.
