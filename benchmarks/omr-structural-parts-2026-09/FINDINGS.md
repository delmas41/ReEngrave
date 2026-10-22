# Structural parts — re-pricing the two dormant flags on the 20-row gate

**Phase 1, 2026-09-05.** Written by the coordinating session from the workstream
agent's reports; the agent's harness refuses it `.md` writes, so the primary
record is its commit messages, `run_arms20.py`'s docstring, and the committed
score files. This file is the conventional location, not a second source —
where it disagrees with `arms20-part1.json` / `arms20-oracle.json`, the JSON
wins.

Branch: `claude/structural-parts-2026-09` (`b84d5ab4`, `fe0f934b`), rebuilt on
`24911c35`. Scripts: `run_arms20.py`, `probe_misjoined_slots.py`.

## Fixture provenance — state this in every arm

> 20-row transcriptions from
> `.claude/worktrees/reconciliation/benchmarks/omr-scan-e2e-2026-09/fixtures/`,
> suffix `.reconciliation.omr.json`. ⚠️ The main checkout's `fixtures/` still
> holds the **11-row** `.restamp-composed` set — a script pointed there measures
> the old gate and says nothing about it.

Both flags change `export.to_musicxml` and nothing upstream, so the arms are
produced by re-exporting committed transcriptions: an exact A/B with no detector
time and no nondeterminism.

## Two controls, run because the arms are worthless without them

1. **Flag-off reproduces the committed baseline**: 74,962 / 0.8441 against the
   recorded 74,968 / 0.8444 — 6 edits of drift between trees, so every delta
   below is measured against this tree's own flag-off export. Re-run after the
   rebase onto `24911c35`: **identical in every field**, so the table is current.
2. **`OMR_CONDENSED_PARTS=1` with no count source is byte-identical on 20/20
   rows.** Nothing in the pipeline writes `condensed_parts`, so the flag alone
   is provably inert rather than assumed to be.

## The table

| arm | OMR-NED | edits | Δ | ES | ΔES | EM | ΔEM |
|---|--:|--:|--:|--:|--:|--:|--:|
| base (flags off) | 0.8441 | 74,962 | — | 17,520 | — | 29,661 | — |
| condensed, no count source | 0.8441 | 74,962 | **0** | 17,520 | 0 | 29,661 | 0 |
| **slot stitch** | **0.8417** | **74,720** | **−242** | 20,384 | +2,864 | 26,964 | −2,697 |
| oracle split (answer key) | 0.6919 | 67,844 | −7,118 | 6,292 | −11,228 | 24,246 | −5,415 |
| **oracle + slot stitch** | **0.6481** | **65,593** | **−9,369** | 5,400 | −12,120 | 19,133 | −10,528 |

**How much evidence exists at all.** The ordinal join refuses on **3 of 20 rows**
— Beethoven p3 in two editions (11 vs 8 staves) and Brahms p2 (14 vs 13). Ten
rows are single-system, seven join cleanly, none are fragmented. Slot stitch's
evidence base went from one page to two pages / three rows.

**The ES/EM trade holds — it was not a Brahms property.** All three rows improve
and each pays identically: ES +917/+975/+972 against EM −818/−1,008/−1,001.
musicdiff really does charge an unpaired truth PART more than that part's
unpaired MEASURES, so the fragments were buying a cheaper charge for a worse
structure. ⚠️ The corollary stands and generalises: **attributing structural
work by the `entire staff` bucket alone systematically under-counts
fragmentation.**

**The flags compose superadditively.** −242 + −7,118 = −7,360 predicted against
**−9,369 measured**. The extra −2,009 is the three refusal rows, where the split
is gated off until stitching establishes continuity (Beethoven p3: 0 alone →
−767 and −1,122 together; Brahms p2: 0 → −362). At 11 rows that composition was
worth −362, all on one page.

**The ceiling is a floor.** The oracle map covers 16/20 rows; the four it misses
(`bach-brandenburg3-mvt1-468678-p1`, `mahler-sym5-mvt1-local-p3/p4/p5`) hold
**4,944 of the 5,400 `entire staff` edits (92%) surviving the best arm**. So
−9,369 is what a *perfect* count source is worth on the rows that have one, and
Phase 2 must report **coverage before gain** — a source reaching those four is
worth more than one improving rows already covered (Mahler 5 alone is 38
reference parts against 13–18 printed staves).

## The default question, unresolved on purpose

Against flipping slot stitch: −242 is **0.32% of the pool**, from 3 rows over 2
pages, and it makes `entire staff` **16% worse** (17,520 → 20,384) — the bucket
every structural report reads first. For: it is a strict win on every row it
touches, the structure it produces is the correct one (Brahms p.2: 27 fragments
→ 14 continuous parts, correctly leaving the suppressed Trompeten slot short),
and the ES penalty is now shown on three rows to be an artifact of not splitting.

**Recommendation, adopted: flip it together with a real count source, or not at
all.** The decision is Sean's, not the workstream's.

## A silent mis-join, found in passing and not acted on

`probe_misjoined_slots.py`, `misjoined-slots.json`. Rows
`beethoven-sym5-mvt1-984073-p4` and `beethoven-sym5-mvt1-575951-p4` (one page,
two editions).

Both systems count 11 staves, so the ordinal join **succeeds** — but they are
not the same eleven: system 2 prints a Timpani staff system 1 does not, so
everything from slot 6 down shifts by one.

| slot | printed, system 1 | printed, system 2 | truth parts | pipeline reads |
|--:|---|---|--:|---|
| 0–5 | Flauti … Trombe | same | [2,2] | correct |
| **6** | **Violino I** | **Timpani in C.G.** | [1, 1] | **Trumpet / Trumpet** |
| 7 | Violino II | Violino I | [1, 1] | Violin / Violin |
| 8 | Viola | Violino II | [1, 1] | Violin / Violin |
| 9 | Violoncello | Viola | [1, 1] | Cello / Cello |
| 10 | Basso | Bassi (Vc e Basso) | [1, **2**] | None / None |

⚠️ **A join that succeeds wrongly is worse than one that refuses**, because a
refusal is visible and this is not: Violino I's music is grafted onto the
Timpani part and nothing reports it. `works.json`'s `_purpose` on the 984073 row
already warns that both systems count 11. It is the only succeeding mis-join in
the corpus that `works.json` maps per system; the other five succeeding rows
assert one lineup for the page.

**Not a Phase 2 blocker**: every mis-joined slot here is count-1 on both sides
except slot 10, where the counts disagree and `_condensed_count` abstains — so
the oracle split never fires on a mis-joined slot on this page. ⚠️ That is a
property of this page, not a guarantee.

**But it sharpens Phase 2's design.** A count keyed on SLOT POSITION inherits
the bad join outright. A count keyed on INSTRUMENT IDENTITY is position
independent and cannot — except that **the naming is wrong on exactly the slots
where the join is wrong**: slot 6 reads `Trumpet` in both systems against
printed `Violino I` / `Timpani`, so a label-keyed source would confidently
supply a Trumpet's **2** players against a printed truth of **1**. The oracle
arm does not exhibit this because it reads printed truth. **So Phase 2's count
source must abstain where the staff's IDENTITY is unconfirmed, not merely where
the count is ambiguous.** Recorded as a design constraint before building.

---

## Why slot stitch is a gain overall and a loss on the headline bucket

Asked by Sean 2026-09-05; answered from `arms20-part1.json` / `arms20-oracle.json`
rather than by reasoning. **The two effects are unrelated: the structural
buckets are a REPRICING that nearly cancels, and the actual gain is note
alignment.**

Only 3 of 20 rows change (the ones where the ordinal join refuses). Pooled over
those three, parts collapse 19 → 11, 19 → 11, 27 → 14:

| category | base | stitch | Δ |
|---|--:|--:|--:|
| entire staff insert/delete | 892 | 3,756 | **+2,864** |
| entire measure insert/delete | 8,124 | 5,427 | **−2,697** |
| **wrong note** | 2,720 | 2,228 | **−492** |
| wrong note head | 520 | 626 | +106 |
| everything else | ~510 | ~489 | ≈ −23 |
| **total** | **12,768** | **12,526** | **−242** |

**1. The ES/EM swap is the same failure, repriced.** `entire staff` is charged
by the CONTENT of the unmatched part. Fragments are SHORT — a fragmented page
gives each part one system's worth of music — so an unmatched fragment costs
little at part level and most of its damage lands in `entire measure` (8,124).
Stitching produces FEWER, LONGER parts, so when a stitched part fails to pair
with its truth part the whole thing is charged at once. ES +2,864 against EM
−2,697 nets **+167**: the same unmatched music, moved from many cheap
measure-charges to a few expensive part-charges.

**2. The real gain is `wrong note` −492**, which is recognition, not
bookkeeping. A continuous part lets the aligner pair notes ACROSS the system
boundary instead of restarting at each system. That −492 is what pays for the
+167 and produces the −242.

**3. The decisive control: the ES penalty REVERSES SIGN once the parts can
pair.** Same stitching code, both directions measured:

| | ES without stitch | ES with stitch | Δ |
|---|--:|--:|--:|
| no count source | 17,520 | 20,384 | **+2,864** |
| oracle count source | 6,292 | 5,400 | **−892** |

So stitching does not damage the headline bucket; **fragmentation was hiding a
pairing failure in a cheaper bucket, and stitching exposes it until the split
lets the parts actually match.** This is the corollary above stated at full
strength: reading structural work off `entire staff` alone does not merely
under-count fragmentation, it inverts the sign of this change.

**Consequence for the default decision.** "Flip with a count source or not at
all" is not a stylistic preference — it is what the arithmetic says: alone,
stitch trades +167 of repricing for −492 of alignment and nets a rounding error
while making the most-read bucket 16% worse; paired, the same code takes ES
DOWN and contributes −2,009 beyond its standalone value.


---

## Phase 4 — bracket blocks: evidence real, both consumers dead

**Step 1 replicated the audit on this corpus** rather than inheriting it: block
boundary precision **0.920** (23/25), recall **0.523** (23/44), within-block
family purity **0.872** (34/39). All 20 rows carry blocks; 279 staves, 39 blocks.

⚠️ A first purity reading of 22/39 was a **metric artifact**, caught before
publication: a bracket block is an ENGRAVING unit, not a taxonomy (timpani
bracketed with the brass is the block working), plus the documented `Basso`
lexicon ambiguity, plus counting a boundary-not-found as a precision failure
when the audit counted it as recall. ⚠️ And 22/39 is numerically identical to
the audit's *recall* figure while being a different quantity — flagged so the
two are never conflated.

**Consumer #2 (family veto in `_dedupe_cross_staff_detections`) — vacuous.**
A veto on the impossible needs a NARROW range, and a family's range is the
**union** of its members', containing both the smallest and the largest:
percussion 0–127, woodwind 22–108, string 28–100, brass 26–84. Against the
corpus's own detected pitches, **5 of 9,219 fall outside their family union
(0.0005)**. Killed by the audit's own sentence — *a block supplies a family, not
a name*. The two-arm A/B was deliberately NOT run: spending an hour of shared
CPU to confirm a ≤5-detection bound derived structurally is theatre.

**Consumer #1 (block-shape mis-join detector) — precision 0.500.** Among rows
where the ordinal join succeeds:

| | n | rows |
|---|--:|---|
| shapes differ, join wrong (TP) | 2 | beethoven p4, both editions |
| shapes differ, join correct (FP) | **2** | **brahms p3, brahms p4** |
| shapes agree, join wrong (FN) | 0 | — |
| shapes agree, join correct (TN) | 3 | beethoven p2 ×2, dvořák p7 |

A coin flip, and **a false positive is not free**: a refusal sends
`_stitch_slots` back to per-system fragments, which Phase 1 measured as costing
more `entire measure` than stitched parts. The FP mechanism is the one step 1
predicted — recall 0.523 unevenly distributed, so a row whose blocks are
under-detected in ONE system shows a shape difference meaning nothing about the
music (brahms p3 `[5,3,6]` vs `[9,5]`; brahms p4 `[9,5]` vs `[14]`, one block
for all fourteen staves).

⚠️ **Observed and deliberately NOT proposed**: the two TPs share a block COUNT
and differ only in sizes, while both FPs differ in count — that would separate
4/4. **n = 4**, and this workstream already refuted its own cap-at-2 guard for
exactly this shape ("a guard tuned to the error mode I could see loses to the
errors I could not"). Recorded as an observation; it needs a corpus with more
equal-count multi-system pages.

**So Phase 4 closes complete**: bracket evidence is real and genuinely
position-independent — it sees a mis-join the staff instrument field cannot,
that field being a restatement of the join at 99/99 positions — and it has no
consumer that reaches edits.

## The mis-join is triangulated three ways

Three independent methods, one defect, which is why Beethoven 5 p.4 is not an
artifact of any one of them:

1. **labels workstream** — per-rung margin reading, `Tp.` at system 2 position 6,
   Surya and Tesseract agreeing;
2. **structural workstream** — per-system bracket shapes, `[4,2,5]` vs `[4,3,4]`,
   on both editions;
3. **`works.json`'s own note** — *"the drafter trap fired here and was
   hand-corrected"*, a human finding it earlier with a third tool.
