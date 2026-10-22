# The scan benchmark's `entire staff` bucket — who owns it

2026-09-04. Based on `b5f91c71` (the arc-attribution merge).

The vs-industry Addendum 3 measured that our whole deficit against Audiveris on
the widened 10-row scan pool is **one bucket** — `entire staff insert/delete`,
ours 5,491 against its 2,900 on the five second/third pages, identical (2,676)
on the five first pages — and posed the next lever as *"attribute which staves
fail to pair on the five p2/p3 rows. One sitting likely explains most of the
2,591."*

This is that sitting. **The documented suspicion is wrong**, and the axis the
deficit actually lies on is not the one it was cut along.

---

## 1. What the bucket IS

`entire staff insert/delete` is musicdiff's `inspart` / `delpart`: **one op per
part that pairs with nothing, costing that whole part's content.** Confirmed by
op dump on `beethoven-sym5-mvt1-984073-p2` — 7 `inspart` ops, 1,551 edits, and
zero of any other op in that category.

So the bucket is not a reading measurement at all. It counts *how many parts the
two files disagree about*, priced by how much music sits in them.

---

## 2. Phase 1 — the ownership table

Every page's structure was read out of the transcription the benchmark already
committed (`fixtures/*.restamp-composed.omr.json`) and its export, then scored
against the **hand-verified `staves[i].parts` rows in `works.json`** — used only
to grade the attribution, never as pipeline input.

`probe_staff_ownership.py`, output in `ownership.json`.

| row | page shape | mechanism | pred parts | truth parts | ES ours | ES Audiveris |
|---|---|---|--:|--:|--:|--:|
| beethoven-984073-p1 | 1 system | condensation | 12 | 18 | 513 | 513 |
| beethoven-984073-p2 | 2 systems, **stitched** | condensation | 11 | 18 | 1,551 | 682 |
| beethoven-575951-p1 | 1 system | condensation | 12 | 18 | 513 | 513 |
| beethoven-575951-p2 | 2 systems, **stitched** | condensation | 11 | 18 | 1,551 | 401 |
| dvorak-p5 | 1 system | — (exact) | 15 | 15 | **0** | **0** |
| dvorak-p6 | 1 system | — (exact) | 15 | 15 | **0** | **0** |
| brahms-p1 | 1 system | condensation | 14 | 21 | 1,001 | 1,001 |
| brahms-p2 | 2 systems, **stitch REFUSED** | fragments | 27 | 21 | 715 | 143 |
| mahler-p2 | 1 system | condensation | 17 | 38 | 649 | 649 |
| mahler-p3 | 1 system | condensation | 13 | 38 | 1,674 | 1,674 |
| bach-p1 | 2 systems, stitched | (Audiveris cannot process) | 12 | 11 | 286 | — |

**Ownership of the 5,491 on the five later pages:**

| mechanism | edits | share | rows |
|---|--:|--:|---|
| **(c) condensation** — one printed staff carries several reference parts; our detection is CORRECT | **4,776** | **87.0%** | beethoven x2 p2, mahler p3 |
| (a) stitching refused on count mismatch -> per-system fragments | 715 | 13.0% | brahms p2 |
| (b) staff detected, slot unassigned or mislabeled | 0 | 0% | — |
| (d) genuine segmentation error (missed / spurious staff) | 0 | 0% | — |

### (a) does not dominate — it is 13%, on one page

And the mechanism it names is **working as designed**. `works.json` hand-reads
Brahms 1 p.2 as *"system 1 = 14 staves (the full p.1 lineup); system 2 = 13 (the
2 Trompeten in C staff is suppressed)"*. We detect exactly `[14, 13]`.
`_stitch_slots` refuses, which is the correct call — grafting by position would
put the Timpani's music on the Trumpets. The refusal is right; its *fallback* is
what costs.

### (c) is the bulk, and our reading of those pages is exact

The condensation figures are not approximate — they land on the answer key to
the part:

* **beethoven-984073-p1** — the key prints 12 staves for 18 reference parts:
  `Flauti [0,1]`, `Oboi [2,3]`, `Clarinetti [4,5]`, `Fagotti [6,7]`,
  `Corni [8,9]`, `Trombe [10,11]`, then six solo staves. Exactly **6** parts
  share a staff with another => exactly **6 `inspart`** => 513 edits.
* **beethoven-984073-p2** — from p.2 the lineup condenses by one more: the key's
  bottom staff is `Violoncello e Basso [16,17]`. 11 staves for 18 parts =>
  exactly **7** shared => exactly **7 `inspart`** => 1,551 edits.

We detect 11 staves in each of two systems and stitch them to 11 continuous
parts. **There is no detection error, no slot failure and no stitching refusal
on those pages.** The exporter emits one part per *printed staff*; the reference
holds one part per *instrument*. That gap is the whole charge.

(mahler-p3 carries a small genuine shortfall alongside — the key notes 13
five-line staves *plus 2 one-line percussion staves*, and we find the 13. It
does not move the attribution: its ES ties Audiveris exactly.)

---

## 3. The axis is SYSTEM COUNT, not page position

Re-cutting the same ten rows by the property the exporter actually branches on
(`probe_structural_axis.py`, `structural-axis.json`):

| page shape | rows | ES ours | ES Audiveris | delta | EM ours | EM Audiveris | delta |
|---|--:|--:|--:|--:|--:|--:|--:|
| **1 system** | 7 | 4,350 | 4,350 | **+0** | 3,477 | 4,545 | **-1,068** |
| **2 systems** | 3 | 3,817 | 1,226 | **+2,591** | 7,147 | 6,883 | +264 |

Against Addendum 3's cut (first page +0 over 5 rows, later page +2,591 over 5):

**the totals are the same, but the system-count cut puts SEVEN rows at exactly
zero instead of five, and it explains the two it gains.** `dvorak-p6` and
`mahler-p3` are later pages that tie Audiveris to the edit — because they hold
one system. `bach-p1` is a *first* page with two systems. Page position is a
confound; system count is the variable.

WARNING: **On every single-system row our `entire staff` equals Audiveris's
exactly** — 513/513, 513/513, 0/0, 1001/1001, 649/649, 1674/1674. Seven exact
ties is not coincidence: both systems read the printed lineup correctly and both
pay the same condensation floor. **87% of the bucket is a floor we share with
the industry tool and cannot win by matching it.** On those same rows we *beat*
it on `entire measure` by 1,068.

---

## 4. Phase 2 — the proposed fix, built and measured

The brief's Phase 2 was slot-aware stitching: where contextual assigned slots,
join by SLOT identity instead of ordinal, refusing only where contextual
abstained. Phase 1 says (a) does not dominate, so this was **not shipped** — but
it was built and priced, because an estimate is not a measurement (my own
pre-measurement estimate was **+190 worse**; the truth is -216 better, in the
opposite direction).

`export._stitch_slots_by_slot`, behind `OMR_SLOT_STITCH` (**default off**). It
is reached only where the ordinal join already refused, and abstains whole
unless every staff of every system carries a slot and no system repeats one.

**The join it produces is structurally correct.** On Brahms 1 p.2 contextual
reads system 1 as slots `[0..13]` and system 2 as `[0,1,2,3,4,5,7,8,9,10,11,12,13]`
— it has *already* identified that slot 6 is the missing one, which is exactly
the Trompeten staff the key says is suppressed. Joining on it recovers **14
continuous parts from 27 per-system fragments**, with slot 6 correctly short.

Priced over all 11 scan rows (`run_arms.py`, `arms.json`; re-exported from the
committed transcriptions, so the two arms differ in the exporter and nothing
else):

| | pooled OMR-NED | edits | `entire staff` |
|---|--:|--:|--:|
| baseline (flag off, this tree) | 0.8283 | 34,962 | 8,453 |
| **slot stitch** | **0.8235** | **34,746** | **9,370** |
| | **-0.0048** | **-216** | **+917** |

Ten of eleven rows are **byte-identical** between the arms; the flag touches
`brahms-sym1-mvt1-317803-p2` and nothing else. On that row:

| | total | `entire staff` | `entire measure` | `wrong note` |
|---|--:|--:|--:|--:|
| ordinal refuse (default) | 6,562 | 715 (6 `delpart`) | 3,628 | 1,832 |
| slot stitch | 6,346 | 1,632 (7 `inspart`) | 2,810 | 1,457 |

WARNING: **THE FIX IMPROVES THE POOL AND MAKES THE NAMED BUCKET MORE THAN TWICE
AS BAD.** That is not a contradiction, it is what the bucket measures: 27
fragments pair with more of the 21 truth parts than 14 continuous parts do, so
fragmenting *buys* `entire staff` and *pays* in `entire measure` — each fragment
has 7-8 measures against the truth part's 15, so half of every truth part's bars
go unpaired. Attributing this work by the ES bucket alone systematically
under-counts the refusal, because the refusal books most of its cost in the
other bucket.

The honest ledger is structural cost (ES + EM) against Audiveris on the three
multi-system rows: ours 10,964, its 8,109, **+2,855** — the ES/EM shuffle does
not cancel, and brahms-p2 is the worst single row at +1,719.

**Why it stays off.** The trade has been priced on exactly one page — the only
page in the corpus whose systems disagree about staff count. -216 edits from
n=1, against +917 on the bucket the work was scoped to reduce, is not enough to
change a default. It is a flag so the finding is reproducible, not because the
default is in doubt.

---

## 5. What the engraved side does

**All eleven engraved works are single-system excerpts**, so the flag is a
structural no-op there — verified by exporting each committed
`omr-orchestral-e2e/fixtures/*.omr.json` under both arms: **11/11
byte-identical**. That is stronger than re-running `orchestral_eval` (which
would add detector nondeterminism to a question that has an exact answer) and
costs no shared CPU.

WARNING: **The engraved benchmark cannot see this change at all, and could not
have caught a regression in it.** Same shape as the direction-text finding: a
corpus that cannot express a fault cannot regression-test its repair. The guard
is `tools/omr/tests/test_export_slot_stitching.py` (13 tests), and it stands in
that benchmark's place.

One of those tests earns its keep specifically: a slot that *enters* on the
second system must take that system's measure start, which a naive
`zip(slot, starts)` gets wrong. Verified by reverting to the naive form — the
test fails `['1','2','3'] != ['3','4','5']` — because the Brahms shape (every
slot present in system 1) cannot tell the two implementations apart.

---

## 6. Where the lever actually is

Not in stitching. The ranked reading of the 5,491:

1. **Condensation, 4,776 edits (87%) — and it is a scoring-model question, not a
   recognition one.** Our reading of those pages is exact against the answer
   key. A printed `Flauti` staff *is* Flute 1 and Flute 2; the reference splits
   them and we do not. Two directions exist and both are real work: emit a
   condensed staff as several MusicXML parts sharing its notes (the engraving's
   own semantics, and `works.json` already records the `parts` mapping by hand
   for every benchmark page), or condense the truth to the print. WARNING:
   Audiveris pays this floor identically on every single-system row, so **it is
   not where the pool against Audiveris is lost** and closing it is worth
   accuracy, not competitive ground.

2. **The +2,591 vs Audiveris, entirely on the three multi-system rows.** Two of
   those three stitch correctly and still pay 1,551 against its 401/682 — which
   means Audiveris emits *more* parts than the page has printed staves and pairs
   more truth parts as a result. That is the same trade the slot-stitch
   measurement just priced, run the other way. WARNING — **unresolved here**:
   its MusicXML outputs are not on disk (`out/audiveris-scan/` is absent), so
   its part counts are inferred from cost arithmetic and not measured. Getting
   those files is the cheapest next step and would settle it.

3. **(b) and (d) are zero.** Slot assignment and staff segmentation are not
   costing anything in this bucket on this corpus. `contextual` is doing its job
   — including, on the one page it mattered, correctly naming the suppressed
   slot.

---

## Reproducing

```bash
python3 benchmarks/omr-staff-structure-2026-09/probe_staff_ownership.py \
    --fixtures benchmarks/omr-scan-e2e-2026-09/fixtures \
    --results  benchmarks/omr-scan-e2e-2026-09/results-restamp-composed.json \
    --audiveris <categories-audiveris-scan11.json> --json ownership.json

python3 benchmarks/omr-staff-structure-2026-09/probe_structural_axis.py \
    --ownership ownership.json --audiveris <...> --json structural-axis.json

export OMRNED_PYTHON=.../.venv-omrned/bin/python
python3 benchmarks/omr-staff-structure-2026-09/run_arms.py --json arms.json
```

`out/` is gitignored — every file in it is a re-export of a committed
transcription and is reproduced by `run_arms.py`.

WARNING: This tree's baseline is **0.8283 / 34,962**, not the committed
`results-restamp-composed.json`'s 0.8303 / 35,046: that baseline was exported on
an earlier commit and this tree carries the arc-attribution merge, so a
re-export is not byte-identical to it on any row. The A/B above is against this
tree's own flag-off export, which is the only valid comparison.
