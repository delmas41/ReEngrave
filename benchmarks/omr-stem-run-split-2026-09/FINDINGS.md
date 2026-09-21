# TWO STEMS AS ONE RUN — Sean's diagnosis is CONFIRMED, and its population is THREE runs

⚠️⚠️ **THE RESULT IS A NEGATIVE AND IT IS THE POINT.** Sean read three crops on
2026-09-20 and diagnosed *"two separate stems that are being measured as one
stem."* **He is right** — the case he was shown is exactly that, and this lane
confirms it against the plate. What this lane adds is the number he could not
have: across **8 pages of 2 publishers the fault reaches 3 vertical runs of
4,225**, and at most **13 noteheads of 5,684 (0.23%)** can take a wrong stem
direction from it. **Nothing under `tools/` changes.** No flag, no split rule.

`git diff main..HEAD --stat -- tools/` is EMPTY.

## 0. WHAT WAS RE-DERIVED, AND THE TWO THINGS THAT DID NOT REPRODUCE

The brief's four measurements come from
`benchmarks/omr-stem-attribution-2026-09/FINDINGS.md` §0(d). ⚠️ **The probe
that produced them was never committed** — `git log --all -S overshoot`
returns exactly one commit, `94210726`, which touches `CLAUDE.md` and that
FINDINGS and nothing else. So this is a re-derivation from the two shared
records, not a re-read of an artefact.

| §0(d) claim | stated | re-derived | |
|---|---|---|---|
| head at an END of its stroke | 1,526 / 1,635 | **1,526 / 1,635** | ✅ exact, both plates |
| chord (companion at the same x) | 182 / 246 | 180 / **246** | ✅ Breitkopf exact; Litolff ±2 |
| FLAGGED residue | 51 / 14 | 53 / **14** | ✅ Breitkopf exact; Litolff ±2 |
| overshoot at BOTH ends | 9 of 51 / 7 of 14 | **9 of 51** / 6 of 13 | ✅ Litolff exact |
| flagged runs are LONGER | 5.72 / 4.12 · 4.43 / 3.46 | 5.97 / **4.12** · 4.48 / 3.817 | ⚠️ see §0b |
| flagged runs are ~18% WIDER | 0.38 / 0.32 · 0.21 / 0.18 | **0.38 / 0.32** · 0.25 / 0.214 | ⚠️ see §0b |

**The direction of every one of the four holds.** The ±2 on Litolff is the
*"same x"* cut, which §0(b) states as a band and never as a number — mine is
0.1 notehead widths. The prior lane's own note that *"the widest empty interval
in the offset distribution is 0.08 notehead widths, i.e. noise"* is why two
rows can cross it.

### 0b. ⚠️⚠️ THE BREITKOPF STAFF-SPACE FIGURES WERE COMPUTED WITH A FLAT 100 px

Every Breitkopf length and width in §0(d) is out by up to 25%, and the cause is
the trap `Q.CELL_STAFF_SPACE`'s own docstring exists to prevent: *"THE UNIT IS
THE CELL'S OWN STAFF SPACE, never a flat 100 px. `_upscale_to_canonical` scales
a too-wide cell by WIDTH."*

Recomputed under a flat 100 px my figures become §0(d)'s, **to the third
decimal**:

| | per-cell space (correct) | flat 100 px | §0(d) states |
|---|--:|--:|--:|
| Breitkopf unflagged length | 3.817 | **3.46** | **3.46** |
| Breitkopf width, flagged / unflagged | 0.25 / 0.214 | **0.20 / 0.18** | 0.21 / 0.18 |
| the named extreme case `glyph/1/0/3/4/0` | 7.12 sp | **5.66** | **5.7** |

⚠️ **Litolff is unaffected either way** — `record.py` records 1,167 of its 1,180
cells sitting at exactly 100 — which is why §0(d)'s Litolff numbers are exact
and its Breitkopf numbers are not. Measured here: **18 of Litolff's 1,305
strokes stand on an off-nominal cell against 846 of Breitkopf's 1,558.**

⚠️ **The extreme case reconciles completely once a second convention is
named**: §0(d) measures overshoot from the head's **CENTRE** and this lane from
its box **EDGE**. 1.96 + 0.5 = 2.46 ≈ its *"2.5 noteheads above"*, and
2.31 + 0.5 = 2.81 ≈ its *"2.8 below"*. Both are defensible; the edge is used
here because a stem attaches at the head's SIDE, so measuring from the centre
charges half a notehead of free overshoot to every correct stem.

## 1. THE CONTROL §0(d) NEVER REPORTED, AND IT IS THE STRONGEST NUMBER HERE

§0(d) reports the both-ends rate among FLAGGED runs and never among the rest.
Run on the unflagged population:

| | flagged | **unflagged** | enrichment |
|---|--:|--:|--:|
| Litolff | 9 of 51 (18%) | **1 of 1,254 (0.08%)** | ~230× |
| Breitkopf | 6 of 13 (46%) | **1 of 1,545 (0.06%)** | ~700× |

**The both-ends signature is essentially absent from ordinary stems.** That is
a real corroboration of the convention (*a stem starts at its notehead, so it
can overshoot at one end only*) and it was available for free.

## 2. ⚠️⚠️ THE THRESHOLD HAS NO EMPTY INTERVAL — IT IS A FITTED CONSTANT

`min(over_top, over_bot)` over every run carrying a claimant:

| band | ≤ −0.5 | −0.5..0 | 0..0.25 | 0.25..0.5 | 0.5..0.75 | 0.75..1 | 1..2 | > 2 |
|---|--:|--:|--:|--:|--:|--:|--:|--:|
| **Litolff** (n=1,305) | 19 | 1,057 | 212 | 7 | 3 | 3 | 4 | 0 |
| **Breitkopf** (n=1,558) | 21 | 1,381 | 145 | 4 | 3 | 2 | 2 | 0 |

The mass sits at or below zero — the convention working — then **decays
smoothly**: 212, 7, 3, 3, 4. The widest gap among positive values is **0.274**
(Litolff, between 1.10 and 1.37) and **0.996** (Breitkopf, 0.94 → 1.94), both
in the far tail rather than at any separation point.

**So the 0.5 cut is a constant fitted to a smooth distribution**, which is the
thing this repo refuses — the test that killed `_SLUR_ARC_PAD_NOTEHEADS`
(*"a pad read off it would be fitted to a wish"*) and that §3 of the prior lane
already applied to the sibling question. It refuses here too, and no other cut
is better: every value from 0.25 to 1.0 sits inside the decay.

## 3. THE REACH, IN THE CURRENCY THAT DECIDES

| | Litolff | Breitkopf | both |
|---|--:|--:|--:|
| stem rows in the record | 1,920 | 2,305 | 4,225 |
| …carrying a claimant head | 1,305 | 1,558 | 2,863 |
| overshooting at BOTH ends (> 0.5) | **10** | **7** | **17** (0.40%) |
| …and carrying 2+ claimants | 1 | 2 | **3** |

### 3a. A SECOND, THRESHOLD-FREE FORMULATION SELECTS THE SAME THREE RUNS

Sean's shape has a structural signature that needs no overshoot constant at
all: two voices stemming toward each other put **both heads in the MIDDLE** of
the fused run, so **no claimant is at either end**. Asked that way:

| | runs with 2+ claimant heads | …and NOT ONE at an end |
|---|--:|--:|
| Litolff | 336 | **1** (`obs:022559`) |
| Breitkopf | 298 | **2** (`obs:021335`, `obs:053295`) |

**All three are also in the both-ends set.** Two independent formulations —
one per-head, one per-run, sharing no constant — converge on the same three
runs out of 634. That is the reach of a rule aimed at the diagnosed fault.

### 3b. AND THE DOWNSTREAM COST IS SMALLER STILL

`adjudicate_stem_direction` reads these strokes. Its verdicts for every head
standing on a both-ends run, off the records:

| | heads on such a run | **DECIDED** (a wrong answer is possible) | abstained |
|---|--:|--:|--:|
| Litolff | 11 | **8** (5 down, 3 up) | 3 |
| Breitkopf | 9 | **5** (4 down, 1 up) | 4 |

**At most 13 noteheads of 5,684 (0.23%)** across 8 pages of 2 publishers can
take a wrong direction from this, and only the subset whose run really is two
stems is actually wrong. ⚠️ The remaining 7 already ABSTAIN — `stems_disagree`
and `no_stem` are the decision working, not the fault propagating.

## 4. ⚠️⚠️ AND THE POPULATION IS NOT WHAT THE DIAGNOSIS PREDICTS — 1 OF 13

All 17 runs were cropped as full-width staff strips (frame control passed
17 of 17, 0 refused) and **13 were adjudicated against the plate**:
[out/ADJUDICATED.md](out/ADJUDICATED.md).

| what the print shows | n |
|---|--:|
| ✅ **two voices, two stems, fused** — the diagnosed fault | **1** |
| a fusion of a different kind — **cross-staff**, through the measure-cell padding | 2 |
| ONE stem whose pair's other head was **never detected** | 2 |
| a **spurious notehead** on a perfectly good stem | 1 |
| ink that is not a stem: an accidental, a dynamic, a rest, blotch | 4 |
| ambiguous / not adjudicable on this plate | 3 |
| not opened | 4 |

⚠️ **The confirmed case is `glyph/1/0/3/4/0` — the one §0(d) already names**,
and the crop shows precisely what Sean said: one run at x≈588 from the upper
beam to the lower one, two adjacent heads in the middle, upper voice up and
lower voice down. **His reading of the plate is vindicated. The generalisation
from three crops to a population is what does not hold.**

⚠️⚠️ **THE BRIEF'S LITOLFF QUESTION IS ANSWERED, AND THE ANSWER INVERTS IT.**
It asked why the both-ends test catches 50% on Breitkopf and 18% on Litolff,
and expected *"something else is also happening on the blotchier Litolff
plate"* OUTSIDE the set. It is happening INSIDE it: **6 of 6 Litolff cases
opened are blotch, furniture or a spurious head, and not one is a fused pair of
stems.** The 18% is not a smaller share of the same fault — it is a different
population wearing the same signature.

### 4a. THE RESIDUAL THE TEST DOES *NOT* CATCH IS ALREADY ON THE RECORD

42 of Litolff's 51 flagged runs and 7 of Breitkopf's 13 do not overshoot at
both ends. Decomposed, **every single one has at least one head AT AN END**:

| | Litolff | Breitkopf |
|---|--:|--:|
| 2 heads, 1 at an end | 23 | 5 |
| 3 heads, 1-2 at an end | 12 | 0 |
| 4-5 heads, 1-3 at an end | 7 | 2 |

So the run **is** a stem with a legitimate owner at its end, and the flagged
head is a passenger on it. That is the prior lane's §2 *"far pairs where
ANOTHER head claims the same stroke from an end"* — **an ATTRIBUTION question,
not a segmentation one**, and §3 already measured that no constant-free rule
separates it from a chord. **The 82% is not a missed fault; it is a different,
already-characterised one.**

## 5. WHY NOTHING WAS BUILT

Four reasons, and any one of them is sufficient:

1. **Reach is 3 runs** by the formulation that matches the diagnosis, 17 by the
   looser one — of 4,225. The downstream cost is at most **13 heads of 5,684**.
2. **The threshold has no empty interval** (§2). A split rule would ship a
   constant fitted to a smooth tail, on a quantity every stem arm in this repo
   proves faithful.
3. **The population is heterogeneous** (§4) — 1 of 13 is the diagnosed fault.
   A rule keyed on the signature would split cross-staff fusions, spurious
   noteheads and accidental ink with the same confidence, and the repair for
   each of those is somewhere else entirely.
4. ⚠️ **`Q.STEM` is the faithfulness control of a whole thread.** Litolff 1,920
   and Breitkopf 2,305 are what every stem arm here reproduces before reporting
   a delta. Moving them for 3 runs would cost that control more than the 3 runs
   are worth.

⚠️ **This is not a recommendation to stop reading Sean's diagnosis as correct.**
It is correct. It is a measurement of how much of the file it explains.

## 6. WHAT IS NOT ESTABLISHED

* **n = 2 documents, 2 publishers, 8 pages, both SCANS.** The engraved family
  is untouched.
* **4 of 17 strips were not opened**, and 3 of the 13 opened are ambiguous. A
  musician looking at all 17 could move the 1-of-13 figure — in either
  direction. **These verdicts are mine, not Sean's.**
* **No repair was attempted**, so nothing here says what a split would cost.
  The reach and the downstream figures BOUND the benefit; they do not measure
  a change that was never made.
* **The 0.5 cut is mine.** §2 shows no cut is defensible; a different one moves
  §3's 17 but not §3a's 3, which is the threshold-free count.
* **The crop verdicts are a reading of a bitonal scan**, and §4 records that
  the Litolff plate defeats the question on 6 of 6 tries. *"Not adjudicable"*
  is not *"not a fault"*.
* **No OMR-NED figure is claimed, deliberately.** The metric is symmetric and
  rewards under-prediction, so it would pay for emitting fewer strokes whether
  or not the split were right.
* **Nothing was re-gathered.** Everything is read off the two committed shared
  records; a GATHER change would be invisible to this instrument.

## 7. CONTROLS

* **Re-derivation**: 4 of §0(d)'s figures reproduce exactly on at least one
  plate; the two that do not are explained to the third decimal by a named unit
  error (§0b), and the explanation is itself checked by recomputing under the
  wrong unit and recovering the published numbers.
* **Reach-first**: the probe exits **2** and prints `DEAD` on a record carrying
  no stem — exercised for real by the battery, not merely asserted.
* **Positive control on the null**: the same both-ends test on the unflagged
  population reads 0.08% / 0.06% against 18% / 46% (§1).
* **Two independent formulations** converge on the same 3 runs (§3a).
* **Frame control** passed on 17 of 17 strips; 0 refused.
* **Mutation battery**: `mutate.py`, **12 arms, 12 RED, 0 survivors, 0 bad
  anchors**, restore VERIFIED by md5, byte snapshot on disk, in-flight
  sentinel, refuses a dirty tree. Output: [out/mutate.txt](out/mutate.txt).
  ⚠️ **Its first run had ONE SURVIVOR and the survivor was the finding**: an
  arm replacing `Q.CELL_STAFF_SPACE` with a flat 100 px — the exact §0(b) fault
  — left the Litolff headline unmoved, because 1,167 of 1,180 of that plate's
  cells sit at 100. *The arm reproduced the historical bug's own invisibility.*
  Closed by printing the off-nominal subpopulation (18 strokes on Litolff, 846
  on Breitkopf), which moves under it. ⚠️ One arm is a declared **EQUIVALENT
  MUTANT**, named and HELD OUT of the verdict with its own separate control,
  rather than left in the list to go green for free.
