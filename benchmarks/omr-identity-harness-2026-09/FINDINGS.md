# A harness that can SEE staff identity — phase 0

2026-09-06. Phase 0 of [docs/scope-identity-upstream-2026-09-06.md](../../docs/scope-identity-upstream-2026-09-06.md).
**Measurement apparatus only** — no pipeline behaviour and no default is
touched by anything in this directory, and nothing here imports `tools.omr`.

## Why phase 0 exists

⚠️ **Neither standing benchmark can see identity at all.** Part names do not
reach OMR-NED — musicdiff does not score them — so the identity layer is
invisible to the headline figure, to the 20-row scan gate and to
`orchestral_eval`. That is not a theory: on 2026-09-06 a shipped default was
found to make a whole work **four times worse** (Brahms pre-finale impossible
names 36 → 149) and it sat under a green benchmark, and every identity fault
fixed that day was found by hand forensics on one work.

**Until identity can be measured, nothing built on it can be judged.**

## What this is

One harness out of two scorers and a pile of committed artefacts. It runs in
**about ten seconds off committed JSON** — no transcription, no weights, no
venv, no network — where a whole-work read pass is ~26 minutes.

    bash benchmarks/omr-identity-harness-2026-09/probe/run_all.sh

| file | what |
|---|---|
| `probe/corpus.py` | the hand-read truth: 7 lineups over 3 works, with provenance |
| `probe/load.py` | one staff-record shape out of the two artefact shapes identity is recorded in |
| `probe/arms.py` | 78 committed arms, each stamped with its **page-set regime** |
| `probe/score.py` | the four columns, side by side |
| `probe/selftest.py` | **the gate** — restore each known fault, prove the harness sees it |
| `probe/calibrate.py` | the calibration question, held out by engraving |
| `probe/diff_arms.py` | forensics: *which* staff records moved, on which page |
| `out/records.json` | the graded corpus, 1571 staff records, as data |

## The corpus

**1571 judgeable staff records**, 2 works, 2 publishers, 2 engravings — the
union of two earlier sessions' hand readings, unified here.

| work | judgeable | of document | full systems | lineups |
|---|--:|--:|--:|--:|
| Beethoven 5 / Litolff | 807 | 49.9% of 1616 | 51 of 140 | 2 |
| Brahms 1 / Breitkopf | 764 | 39.6% of 1927 | 53 of 151 | 4 |
| **pooled** | **1571** | **44.3% of 3543** | **104 of 291** | **6** |

Only **FULL systems** are scored: a system of exactly N staves in a page region
whose maximum is N IS that region's lineup, in printed order. Reduced systems
(tacet staves suppressed) are not scored, because which parts were dropped is a
fact about the page the harness does not know. The names are the canonical
`instruments.Instrument.name` values a musician would give, read off the print
at 600 dpi — deliberately **not** what `instruments.lookup` returns, so a
lexicon fault shows as an error instead of scoring correct against itself.

## The four columns, and why they are not one number

    IDENTITY      correct / wrong / unnamed, over JUDGEABLE records
    IMPOSSIBLE    a name the document cannot be printing there.  Can only
                  FALL, so it scores a categorically-wrong name traded for an
                  ordinarily-wrong one as free — never read it alone
    CONTRADICTED  the margin reader RESOLVED this staff's label and we export
                  something else.  Needs no hand-read truth
    HUMAN         staves a person would have to adjudicate, over ALL records

⚠️ Two denominators on purpose, both printed on every row. IDENTITY is over
judgeable records; HUMAN is over every staff record, because a person reviewing
a score reviews all of it.

---

# 1. THE GATE — three faults restored, and the proof they are not always seen

`probe/selftest.py` exits non-zero on any failure. `out/selftest.txt` is its
output. Each fault asserts **both** directions — with the fault restored the
harness reports it at the recorded magnitude AND signature; with the shipped
default it does not. The second half is what makes it falsifiable rather than a
scorer that prints numbers.

| # | flag | restored | shipped | the harness sees |
|---|---|--:|--:|---|
| 1 | `OMR_SLOT_GROUP_MAP=ordinal` | 750/807, impossible **89** | 756/807, impossible **43** | `Violin -> Trombone` ×4, `Viola -> Trombone` ×2 present, then absent |
| 2 | `OMR_SPAN_REFERENCE_FIT=off` | 642/764 = **0.8403**, impossible **149** | 741/764 = **0.9699**, impossible **0** | `Horn->Trumpet` ×33, `Trumpet->Trombone` ×33, `Timpani->Tuba` ×28, `Violin->Tuba` ×8 → all 0 |
| 3 | `OMR_BRACKET_COLUMNS` unset | within-page disagreement **0.3836** | **0.0548** | 73 same-count system pairs, one denominator in all three arms |

Every figure above **reproduces an independently recorded number exactly** —
36 / 149 / 36 / 0 from `omr-span-composition-2026-09`, 89 / 43 and 750 / 756
from `omr-slot-alignment-2026-09`, 0.8403 / 0.9712 / 0.9699 from
`omr-brahms-lineup-2026-09`, 0.3836 / 0.0548 from
`omr-bracket-stability-2026-09`. That agreement is the harness assertion, not
a result.

Two structural assertions license everything else:

* **SHAPE** — identity is recorded in two artefact shapes and they are one fact
  a join apart: deriving each staff's provenance from
  `slot_instruments[slot].source` reproduces the per-staff `instrument_source`
  on **1616 of 1616** records, 0 disagreements. That is what permits pooling
  arms recorded in different shapes.
* **KEYSET** — arms of one A/B share a staff-record KEY SET, not merely a
  count, or a difference between them is not the flag.

## ⚠️ The gate found two things nobody had asserted

**(a) Only SIX of the recorded seven Beethoven records are the group-map
fault.** The 7th, `Timpani -> Trombone` ×1 on p31 sys1, survives the fix in
every arm. The first draft of self-test 1 asserted "the signature is absent
under the shipped default" and **failed**, correctly. It is now asserted as a
residue rather than laundered away.

**(b) The two columns disagree about which span repair is better, and the
harness prints both.** `refuse` grades one staff higher than the shipped
`search` (742 vs 741 correct) while leaving 36 impossible names standing where
`search` reads 0. Neither column is a superset of the other. This is asserted
as a *disagreement*, per §8b: disagreement is additive information, not a
stain.

---

# 2. ⚠️ THE READ-PASS FLOOR — found by this harness, and it is larger than the faults

Two whole-work passes over the same Beethoven PDF at the same dpi differ by
**50 of 807 judgeable records** — identity **0.9913** vs **0.9368**. The
group-map flag, by comparison, moves **6**.

The whole difference is **one slot**: pass A names slot 8 `Timpani` from a
label; pass B names it `Trumpet` from `score_order_ambiguity`, and 50 judgeable
Timpani staves inherit it (`out/diff-readpass.txt`).

⚠️⚠️ **And the evidence stands in a strict superset relation the wrong way
round.** Pass B's margin evidence *contains* pass A's — **962 of 962 shared
rows agree, zero contradictions, and B read 11 MORE labels**, two of them
`Timpani` on exactly the staff position slot 8 covers (p50 s8, p52 s8). More
correct evidence, no contradiction, worse answer.

> **The identity join is not monotone in label evidence.**

That is precisely the property §8b's additive-evidence design assumes and which
nothing has ever checked. It is also the single most useful thing phase 0
found, because phase 1's write-only evidence store and phase 4's observers both
add evidence and neither would be safe under a non-monotone consumer.

⚠️ **Not attributed, deliberately.** The two passes also differ in CODE (pass A
predates the group-map and span-composition fixes), and committed artefacts
cannot separate "the extra evidence did it" from "the code drift did it". What
they *do* establish is the floor:

> **An identity figure from a different read pass is not a baseline** — the
> same lesson the scan gate learned as ±6 edits, at a much larger magnitude
> relative to the effects being measured.

**What would settle it:** one ~26-minute whole-work read pass at one commit,
serving both label sets off one cache — i.e. re-run pass B's arm with pass A's
962-row label evidence substituted through the same `_labels_for_page` patch
`compose.py` already implements. That isolates evidence from code. It is a
half-session and it is the first thing phase 1 should do.

**And the provenance split is what made it diagnosable at all**: pooled,
`score_order_ambiguity` is 51/51 = 1.000 in pass A and 51/102 = 0.500 in pass
B, while `label` is 0.9907 / 1.0000. The loss localises to one source. This is
the second time `instrument_source` has earned its keep in a week.

---

# 3. ⚠️ THE PAGE-SET REGIME DOMINATES EVERY FLAG MEASURED HERE

The scope warned that `--pages 0-4`, a window crossing a movement boundary, and
a whole work are three different regimes. They are worse than different: on
Beethoven the *same printed system* reads **4/12** in a five-page run and
**12/12** in a whole-work run (`out/diff-regime-front.txt`), with the entire
lineup slid one slot up — `Oboe -> Flute`, `Clarinet -> Oboe`,
`Bassoon -> Clarinet`, `Horn -> Bassoon`, `Trumpet -> Horn`.

| regime | pages | beet5 | brahms1 | pooled | HUMAN rate |
|---|---|--:|--:|--:|--:|
| **whole work** | 0-85 / 0-87 | 0.9368–0.9913 | 0.9699 | **0.9529–0.9809** | 0.055 |
| narrow at the front | 0-4 | **0.3333** (n=12) | 0.9286 | 0.8710 | 0.070 |
| crossing a boundary | 39-48 / 40-49 | **0.0000** (n=85) | 0.9722 | 0.5440 | **0.365** |
| two ad-hoc pages | 23,44 / 30,45 | 1.0000 (n=29) | **0.3125** (n=16) | 0.7556 | 0.149 |

⚠️ **`--pages 0-4` is what the web app runs** (`OMR_MAX_PAGES=5`), and it is
the regime with the least evidence and no benchmark at all. On the
boundary-crossing window Beethoven emits **0 correct of 85**, 65 of them
unnamed, and **36.5% of all staff records in that window would need a human**
against 5.5% for the whole work.

⚠️ **This is not a universal collapse and must not be reported as one.**
Brahms is essentially unhurt by the narrow regimes (0.9286 / 0.9722) and
Beethoven is perfect on the ad-hoc pair. n = 2 works and each narrow cell is
one window; the *variance* is the finding, not a rank order. What is certain is
that a single identity number for a work is meaningless without its regime, so
`run_harness.py` never pools across regimes and `--pool-selected` refuses when
asked to.

---

# 4. The shipped baseline

Whole-work regime, shipped defaults, 1571 judgeable records:

| | judgeable | correct | wrong | rate | impossible | not-in-work | contradicted | HUMAN | /records |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| pass-B Beethoven + Brahms | 1571 | 1497 | 74 | **0.9529** | 0 | 23 | 158 | 197 | 3543 (0.0556) |
| pass-A Beethoven + Brahms | 1571 | 1541 | 30 | **0.9809** | 91 | 23 | 65 | 195 | 3543 (0.0550) |

Per lineup (pass-B row): Brahms mvt 1 **392/392**, mvt 3 **72/72**, mvt 2 solo
pages 22/28, finale 255/272 (the `Trombone -> Tuba` ×17 residue, a *second*
trombone staff of a braced pair named as a tuba in a work with no tuba);
Beethoven 132/144 and 624/663.

Per `instrument_source`, pooled and **reported, never filtered**:

| source | judgeable | correct | rate |
|---|--:|--:|--:|
| `label` | 1399 | 1395 | **0.9971** |
| `roster` | 53 | 51 | 0.9623 |
| `score_order_ambiguity` | 102 | 51 | **0.5000** |
| `score_order` | 17 | 0 | **0.0000** |

## ⚠️ The human-cost axis is nearly ORTHOGONAL to identity here

Between the two rows above, identity moves **44 records** and human cost moves
**2** (197 → 195). The *mix* changes completely — pass A has 91 impossible and
17 contradicted, pass B has 0 and 158 — and the total barely moves.

That is exactly the failure §7 names: *a change that improves accuracy without
reducing review load has not delivered what it was built for.* It is now
measurable rather than a warning. The corollary matters for phase 2: driving
`impossible` to zero, which is what the span fix did, converted categorical
errors into contradictions and left the human with the same number of staves to
look at.

**Human cost decomposes** (pass-B row, over all 3543 records): 150 contradicted
only, 24 unnamed, 15 not-in-this-work, 8 both. Abstention is 24 of 197 — small
today, and the number to watch if any phase makes abstention cheaper.

---

# 5. CALIBRATION: still no. And the diagnosis was right but is sharper now

`out/calibration.txt`. The estimator is the earlier one **unchanged** —
hierarchical empirical frequency (cell → tier → global, Laplace smoothed),
held out by ENGRAVING — so the answer is attributable to the corpus and not to
a new model. Features are page-derived: tier (`instrument_source`),
`label_seen`, `size_bucket`.

| | n | ECE | note |
|---|--:|--:|---|
| `claude/staff-identity-layer-2026-09-05` | 197 | 0.1277 | emitted nothing |
| **this corpus** | **1571** | **0.0204** | **still emits nothing** |

**The lower ECE is not calibration.** Three measurements say so:

1. **Brier skill against a constant predictor: +0.0004.** A model that predicts
   the training base rate for every staff scores Brier 0.0191; the featureful
   one scores 0.0191. The features carry essentially nothing.
2. **95.8% of the mass is in one bin.** [0.98, 1.01) holds 1505 of 1571
   records, promises 0.999 and delivers 0.980. A low ECE over a monoculture is
   a property of the population.
3. ⚠️⚠️ **Every non-`label` tier is UNSEEN IN TRAINING in its own fold**,
   because each derived tier occurs in exactly one work:

   | fold held out | tier | n_test | n_train | predicted | observed |
   |---|---|--:|--:|--:|--:|
   | Brahms | `score_order` | 17 | **0** | 0.990 | **0.000** |
   | Brahms | `roster` | 53 | **0** | 0.990 | 0.962 |
   | Beethoven | `score_order_ambiguity` | 51 | **0** | 0.969 | 1.000 |

   The `score_order` row is the pre-registered failure exactly: the estimator
   promises 0.99 on 17 records that are **always wrong**, and it does so
   because the fold has never seen that tier. Shipping that number is the
   laundering the standard forbids.

**So: the n=197 diagnosis was right — the failure is the corpus — but it was
under-stated.** It said the `derived` tier was empty. It is no longer empty (17
+ 51 + 53 records), and that changed nothing, because **the binding constraint
is ENGRAVINGS, not records**. With two engravings, a leave-one-out fold can
only see a tier that appears in *both* works, and no derived tier does. n grew
8×; effective diversity did not: tier `label` was 89% of the old corpus and is
**89% of this one** (1399/1571).

## What would settle it, exactly

**Not more records from these two works.** The condition is:

> **Every tier must appear in at least two engravings**, so that a
> leave-one-engraving-out fold sees it in training.

Two routes, both already scoped by earlier sessions:

1. **More hand-read works.** Two more whole works from two more publishers,
   full-system lineups hand-read as `corpus.py` records them, would take the
   fold count to 4 and give each derived tier a chance of appearing twice. Cost
   is the *hand reading*, not the compute — one work is ~26 min of transcription
   and an afternoon of margin reading, and an agent stalled on exactly that step
   on 2026-09-06. `dvorak9`'s lineup is already in `corpus.py` awaiting an arm.
2. **The held-out-label design** the n=197 probe named, which is the cheaper
   one and manufactures derived records on demand: hide the margin labels on a
   label-everything publisher's full system and every staff on it becomes a
   `derived` record with known truth. Brahms alone has 53 full systems ≈ 742
   such records. Run on ≥3 editions this satisfies the condition directly.

Until one of those exists: **accumulate additively, in evidence units, and do
not call the sum a probability.** That is `slots.py`'s existing discipline and
it should stay.

---

# 6. What this harness still cannot see

* **Scans.** Every arm here is a whole-work run of an engraved 19th-century
  print at 600 dpi. `benchmarks/omr-scan-e2e-2026-09/works.json` now carries a
  hand-read `staves` map on **15 of 20 rows** across 5 publishers — roughly 180
  staff records in the single-page regime — and it is **not** wired in here, for
  two stated reasons: those maps carry the **printed** name (`Flauti`,
  `Violino I`), so admitting them needs a hand table from printed string to
  canonical instrument (resolving them with `instruments.lookup` would reinstate
  the exact self-scoring fault `corpus.py` exists to avoid — `Basso.` → *Bass
  voice* is already in the record); and no committed artefact carries emitted
  identity for those rows, so each needs a run. That is the highest-value next
  addition: it triples the publishers and it is the only single-page regime with
  truth.
* **Reduced systems.** 55.7% of the pooled document. A truth for them needs to
  know which parts a page suppressed.
* **Dvořák 9 and Mozart 41.** `movement_reference.lineup_spans` finds one span
  on each, so two of the three flags cannot execute on them at all — recorded in
  `omr-span-composition-2026-09` as reach, and unchanged here.
* **Whether a correct name reaches the EXPORT.** Identity is scored where it is
  produced, not in the MusicXML. `<part-name>` emission is a separate question.

---

## Reproduce

    bash benchmarks/omr-identity-harness-2026-09/probe/run_all.sh   # ~10s, gate + all outputs

    python3 probe/run_harness.py --pool                       # every arm, per regime
    python3 probe/run_harness.py --arms 'beet5/*' --detail     # one work
    python3 probe/selftest.py                                  # the gate alone
    python3 probe/calibrate.py                                 # the calibration verdict
    python3 probe/diff_arms.py ARM_A ARM_B [--intersect]       # which records moved
