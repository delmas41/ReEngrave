# Splitting the arcs the exporter refuses — and two hypotheses it kills

`benchmarks/omr-staged-arc-export-2026-09` landed the arc export and reported
one number: **`arc_binds_fewer_than_two_notes` = 361**, 76% of the merged arcs
on the page. Its handoff ranked splitting that number **first**, on the grounds
that *"arcs over notes that exist but were not detected, vs arcs whose notes are
there and the pad/geometry missed"* need different repairs and the number does
not distinguish them.

This is that split. **It needs nothing but the record** — no truth file, no
second document, no re-gather.

```bash
python3 split_arcs.py <staged.json>
python3 split_arcs.py <staged.json> --pad-sweep
```

---

## 1. THE CONTROL FIRST — a fresh gather reproduces the arm exactly

Litolff Beethoven 5 `984073`, pdf pages 1-3, gathered on a clean tree at
`7d1c9122` with the hollow graft: **514 arc rows → 46 `<slur>` / 98 `<tied>`,
23 slurs / 49 ties, 361 + 43 dropped, notes 1075 / rests 432** — the committed
`omr-staged-arc-export-2026-09/out/litolff-p2-p4.txt` to the unit. That is a
determinism result for the arc path in its own right, and it is what makes the
split below comparable to the figures already published.

---

## 2. THE SPLIT

| | | |
|---|--:|---|
| **A** no head anywhere in the arc's own bars | **170** | 47.1% |
| **B** bars hold heads, none under the padded span | **109** | 30.2% |
| **C** exactly one head under the span | **82** | 22.7% |
| paired | 115 | → 72 written (23 + 49) + 43 collapsed into one chord |

`170 + 109 + 82 + 115 = 476` merged groups, and `115 − 43 = 72 = 23 + 49`.
**Closed both ways**, and both are asserted in the probe rather than eyeballed.

⚠️⚠️ **SO "THE REMAINING THREE QUARTERS ARE THE DETECTOR'S" IS ABOUT HALF
RIGHT.** At most **170 of 361 (47%)** are *no notes were read there at all* —
and that is an UPPER bound, because an arc placed on the wrong staff also lands
in A. **The other 53% have the notes present and the pairing missing them.**

⚠️ **The premise that makes this a two-way question at all is checked, not
assumed.** `_paired_spans` refuses on four conditions, two of which need a
voice map; the staged export passes `voice_of={}`, so those two are
structurally unreachable and every refusal is the two-note minimum. The probe
asserts that **by reading the call site**, because if a voice map ever arrives
this classifier silently starts mixing two causes.

---

## 3. ⚠️ HYPOTHESIS 1 REFUTED — it is not `arc_owner`

`adjudicate_arc_owner` moves 12 of 199 arcs to an adjacent staff, so the
obvious story is that a mis-owned arc lands where the heads are not. Tested as
*"does a SIBLING staff of this system have noteheads under this arc's x?"*:

| | | |
|---|--:|--:|
| A | 163 of 170 | 95.9% |
| B | 104 of 109 | 95.4% |
| C | 75 of 82 | 91.5% |
| **PAIRED — the null** | **106 of 115** | **92.2%** |

⚠️⚠️ **THE NULL IS THE RESULT.** On a 12-part page almost any x has somebody
playing, so 95.9% against a base rate of 92.2% is a **base-rate artefact and
not a signal**. Quoted without the null it reads as *"96% of the refused arcs
belong to another staff"*, which is false. The null is computed by the same
code over the arcs that DID pair, in the same pass, for exactly that reason.

⚠️⚠️ **AND THE FIRST READING OF IT WAS INVERTED BY AN INDEX MAP.**
`_flatten_part` appends a measure for **every index of the run**
(`range(run.n_measures)`), including bars that grew no `Cell`; the first
version of this probe mapped measures back to staves with `sorted(run.cells)`,
which slides on the first empty bar. It reported **39 of 170 and 26 of 109** —
low numbers that would have read as *"the sibling test discriminates"*, i.e.
**wrong in the direction that FLATTERED the hypothesis under test.** The
corrected map reads 163 and 104, which the null then kills anyway. A length
assertion now makes the difference loud. *A plausible aggregate is not evidence
that its parts are real* — recorded here for the third time in this repo.

---

## 4. ⚠️⚠️ HYPOTHESIS 2 REFUTED — bucket B is NOT the pad, and the plateau is gone

B is *"the notes are in the bar and the span does not reach them"*, so the
cheap fix is to widen `_SLUR_ARC_PAD_NOTEHEADS`.

```
   pad  paired  A none  B miss   C one
  0.25     115     170     109      82     <- ships
   0.5     144     170      78      84
  0.75     161     170      57      88
   1.0     175     170      34      97
   1.5     193     170      16      97
   2.0     197     170      10      99
   3.0     201     170       2     103
```

**B decays smoothly out to three notehead widths with no plateau anywhere.**

That constant was read off a REAL GAP on an **engraved** Brahms page — 54 of 75
near-misses within 0.19 notehead widths and the next at 0.32 — and
`_noteheads_under`'s own docstring calls it a plateau. **On this scan the gap
does not exist**: the misses are spread continuously. So widening buys
pairings by reaching further with nothing to stop at, which is the symmetric
metric's *"emitting more scores better"* trap in a different currency — and the
arc export refused an OMR-NED figure for precisely that reason.

⚠️ **Column A is pad-INVARIANT by construction** (it is checked before the pad
applies), so its flatness is a wiring check on the sweep and **not evidence
about anything**.

**What this means:** B is not a tunable constant. The arc BOXES are
mislocalised relative to the heads on a scan, which merges B back toward A and
makes the real split roughly **279 detector/geometry vs 82 one-ended**, with no
cheap constant available. ⚠️ n = 1 document, 1 publisher, 3 pages — whether the
missing plateau is this scan's or scans' generally is the first thing a second
publisher would say.

---

## 5. ⚠️ THE MUTATION BATTERY, AND THE ONE THAT WAS INVALID

Six arms, one of them a deliberate equivalent mutant. **Five red, positive
control green.**

| arm | |
|---|---|
| origin map back to `sorted(run.cells)` | RED |
| the voice-map premise | RED |
| a bucket stops counting | RED |
| `paired` inverted | RED — **only after §5b** |
| the A branch never fires | RED — **only after §5c** |
| a no-op reformat | SURVIVED (equivalent, recorded so nobody chases it) |

⚠️⚠️ **THE FIRST RUN OF THIS BATTERY WAS WORTHLESS AND LOOKED PERFECT.** The
mutants were written to the scratchpad, where `parents[2]` does not resolve, so
**every arm was red on an import error rather than on its mutation** — while
the positive control ran from the benchmark directory and passed. *A battery of
refusal arms can pass by refusing everything*, and the control did not catch it
because **the control did not share the mutants' condition**. The mutants now
run from the same directory as the control. The general form: a positive
control only controls for what it shares with the arms.

### 5b. `paired` inverted survived a partition

Inverting the test still puts every group in exactly one bucket, so the
partition assertion stays green and the answer is wrong. It is the arc export's
own lesson arriving again — *counting spans cannot see a frame error; only
naming the NOTES can.* Closed by anchoring `PAIRED` **outside the classifier**:
it must equal what the exporter WRITES plus the chord collapse.

### 5c. The A branch never firing survived too

Collapsing A into B also partitions. Nothing in a partition can see two buckets
merged. Closed by making each bucket **assert the claim its own name makes** —
the bucket name is what a reader trusts and the only part they cannot check by
reading.

---

## 6. WHAT THIS DOES NOT SAY

1. **It does not say the 170 are undetectable.** A is *no head in the bar*,
   which is a reading shortfall OR a wrong-staff placement; this probe cannot
   separate those and does not claim to.
2. **No OMR-NED figure**, deliberately, for the arc export's own reason.
3. **n = 1 document.** Every rate here is Litolff `984073`'s.
4. **Nothing was changed.** No constant moved, no adjudicator was touched; the
   two repairs this bucket seemed to invite are both refused above, which is
   the result.
