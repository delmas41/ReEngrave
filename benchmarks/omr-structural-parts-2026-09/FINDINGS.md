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
