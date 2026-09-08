# Step 4 — `entire staff` separated: four causes, and only one is the reader's

Step 4 as the handoff sets it: *"8 of 20 rows have NO part correspondence —
51% of symbols. Larger than everything about notes, and upstream of all of it.
… Any structural fix priced against that bucket is priced against a mixture.
Separate the causes before attempting any of them."*

Instrument: `tools/omr/symbol_ledger` over the scan-gate pred/truth MusicXML
pairs already on disk, with the part join fed from `works.json` as
`run_ledger.py` intends. **No re-transcription.**

---

## 1. THE SEPARATION

`separate_causes.py`. The classifier is **derived**, not hand-assigned, from
three hand-verified facts already in `works.json` (`page.n_systems`,
`page.n_staves` — FIVE-LINE staves summed over systems — and `len(staves)`,
one entry per PRINTED staff) plus one from the prediction (how many `<part>`
elements we emitted):

| | rows | symbol rows | share | what it is | whose fault |
|---|--:|--:|--:|---|---|
| **A** `_stitch_slots` refuses | 3 | 6,937 | **46.3%** | one part per system-staff | **the reader** |
| **B** lineup names undetectable staves | 3 | 4,815 | 32.1% | one-line percussion rules | the ledger's arity gate |
| **C** one lineup entry, several printed staves | 1 | 2,469 | 16.5% | bach's cembalo grand staff | the ledger's arity gate |
| **D** no lineup at all | 1 | 771 | 5.1% | mahler p2 has no `staves` map | a missing hand-verified fact |
| | **8** | **14,992** | | | |

⚠️ **CONTROL: the four causes sum to the pooled `part_unresolved` mass
exactly** — 14,992 against 14,992 — and **0 rows classify as `unexplained`**
against a positive control of 8 rows classified at all. The classifier is not
a partition of convenience; it accounts for the bucket to the symbol.

⚠️ **THE HANDOFF NAMED THREE CAUSES AND THERE ARE FOUR.** D (mahler p2, no
staves map) was silently inside the bucket. It is not a reading fault of any
kind, and it is the only one of the four that **cannot** be priced from what is
on disk: relaxing an arity gate is a judgement about a fact we hold, inventing
a lineup is a guess about one we do not.

### The arithmetic of B and C, checked rather than asserted

**B.** The lineup lists PRINTED staves, `page.n_staves` counts FIVE-LINE ones,
and the difference is exactly the one-line percussion rules — on all three
rows, to the staff:

| row | lineup | one-line rules named in the row's own note | five-line | we emitted |
|---|--:|---|--:|--:|
| mahler p3 | 15 | Becken, Gr.Tr. (2) | 13 | **13** |
| mahler p4 | 21 | Becken, Gr.Tr., Kl.Tr. (3) | 18 | **18** |
| mahler p5 | 21 | + Tamtam (4) | 17 | **17** |

`page.n_staves_note` on every one of them already says, in words, *"Compare
`detected` against 13/18/17."* **Our staff count is right and the gate is
comparing it to the wrong number.** The 2–4 one-line staves' music is
genuinely unread — a real, bounded recognition gap — but today it costs the
assessability of all 13/18/17 staves on the page.

**C.** bach's lineup entry 10 is literally named `Cembalo (grand staff, 2
printed staves)`; we emit `Piano` + `Staff 11`. 11 versus 12.

**A.** brahms p2's 27 part names are `Flute, Oboe, … Contrabass, Flute, Oboe,
… Contrabass` — 14 + 13, the two systems, unstitched. This is the documented
`_stitch_slots` refusal, and **cause A's three rows are exactly
`OMR_SLOT_STITCH`'s measured reach of 3 of 20 rows.**

## 2. ⚠️ WHAT THIS DOES TO THE CASE FOR `OMR_SLOT_STITCH`

The flag is default-off, and CLAUDE.md records the reason: −240 raw / −2,278
page-normalised edits is *"3 rows … 2 distinct pages of ONE structural
shape"*, too little **n** to move a default.

That reason is about edits. **It is now also true that cause A owns 46.3% of
the unassessable symbol mass** — the largest single block of the corpus that
no instrument can currently say anything about. That does not answer the **n**
objection (it is the same 3 rows), and it is not a new score. It is a
different argument for the same change: the flag is the only one of the four
causes whose fix already exists, is measured, and has never once scored worse.

## 3. ⚠️⚠️ AND UNDERNEATH ALL OF IT, THE INSTRUMENT WAS LOSING 1,771 TRUTH SYMBOLS

Found while separating the causes, because `price_unlocks.py` printed
`balanced=False` and the ledger's own docstring says *"balanced=False is an
instrument defect. Nothing downstream may quote a figure from an unbalanced
ledger."*

`coverage_check()` was **computed on every row, written into
`out/ledger-summary.json`, and read by nothing.** It had been reporting
`balanced=False` on **5 of 7** joined committed rows (9 of 20 in the committed
summary) for as long as it existed, and no run ever said so. That is Class C —
*formed, kept, consumed by nobody* — inside the instrument built to make the
metric legible.

**What it was catching**, measured over the 7 joined rows:

    1,771 truth symbols owning no row at all
      rest 1,066   note 190   tie 163   dynamic 126   fermata 50   slur 48 …

`_merge_truth_parts_symbols` collapses a condensed staff's reference parts,
and `seen_truth` marked every input symbol as seen — so the collapsed twins
fell through both loops and vanished.

⚠️ **AND THE REST RULE WAS 98.5% WRONG.** It dropped **every** rest of a
condensed staff, on the stated ground that *"one part rests while the other
plays: no rest is printed"*. True — but only when another part **plays**.
Where every part of the staff rests, the engraver prints exactly one rest, and
that rest is on the page for us to read. Split by whether any part of the
staff has a note at that onset:

| absorbed rests | n |
|---|--:|
| **every part rests — a rest IS printed** | **1,050** |
| some part plays — correctly not printed | 16 |

Beethoven 5 / Litolff p1 bars 2 and 3: both flutes rest, the Flauti staff
prints one rest, and the ledger could not see either of them.

### Fixed, and the A/B is the control this deserves

`_merge_truth_parts_symbols` now returns `(merged, absorbed)`; every absorbed
symbol owns a row with the new first-class outcome
**`absorbed_by_condensation`**; a rest is dropped only at an onset where some
part of the staff has a note; and `run_ledger` **reads** the coverage control
and refuses to quote a figure without it.

⚠️ `playing` must be supplied by the CALLER: `truth_by` is keyed by FAMILY, so
the `rest` cell holds only rests and the notes that decide the question are in
another cell. Deriving it locally looked right and kept all 1,066 rests
including the 16 — caught by
`test_a_condensed_staff_DROPS_a_rest_another_part_plays_through`, which is one
of two new tests, both run RED against two separate mutants.

Pooled over the committed 20-row summary, same fixtures, same pairs:

| | before | after |
|---|--:|--:|
| unbalanced rows | **9 of 20** | **0** |
| `absorbed_by_condensation` | — | 2,430 |
| `spurious` | 3,186 | **2,327** |
| **`rest.type`** | 471 | **963** |
| **`rest.duration_ql`** | 471 | **942** |
| `note.pitch` | 1,034 | 1,034 |
| `note.duration_ql` | 383 | 383 |
| `note.type` | 371 | 371 |
| `note.accidental` / `key.fifths` / `dynamic.text` / `clef.clef` / `tie.endpoint` / `time.*` / `word.text` | — | **all identical** |

**Every non-rest figure is unchanged to the unit, and 859 of our rests stop
being `spurious` because they now pair with a truth rest that existed all
along.** So `rest.type` at 963 sits level with `note.pitch` at 1,034 as the
largest named error family on the scan gate — and was being reported at less
than half of it.

## 4. ⚠️ A CORRECTION TO `benchmarks/omr-rests-2026-09/FINDINGS.md`

That file reports **416 of 4,239 rest rows assessable (9.8%), from 2 of 11
rows**, and its repro block runs `python3 -m tools.omr.symbol_ledger PRED
TRUTH` — the bare CLI, which takes **no `part_join`** and therefore falls back
to a positional join *only where the part counts already agree*. Against a
38-part Mahler reference they never do.

Fed its tier-1 input as `run_ledger.py` does it, the same 11 committed pairs
give **7 of 11 rows resolved and 6,016 assessable symbol rows at 99.7%
correspondence** (6,057 after the merge fix below — that fix changes what the
assessable rows SAY about rests, not how many there are). The 9.8% figure is a
property of how the instrument was invoked, not of the corpus.

⚠️ The rests findings' *direction* survives: rests really are the larger half,
by more than it said.

## 5. What each cause needs next, and what is NOT claimed

* **A** — `OMR_SLOT_STITCH`, already built and measured. Not flipped here: the
  **n** objection stands and flipping a default is Sean's call.
* **B, C** — an arity gate that compares like with like. `price_unlocks.py`
  measures the ceiling on the two committed rows: mahler p3 **+1,059** and bach
  p1 **+1,846** assessable rows, from 0. ⚠️ **NOT SHIPPED into
  `run_ledger.part_join_for`**: WHICH lineup entries are one-line is not a
  structural field in `works.json` — only the COUNT is derivable — so the
  probe hand-reads the indices from each row's own prose note and asserts the
  count. **The durable fix is a field in `works.json`** (`one_line: true`, or
  `printed_staves: 2` on the cembalo entry), which is a hand-verified-data
  change, not code.
* **D** — mahler p2 needs a `staves` map. Nothing on disk can supply it.

⚠️ **No OMR-NED arm was run and none is claimed.** Every figure here is the
ledger's, over stored MusicXML; the `entire staff` musicdiff bucket is where
this bucket got its name and this file does not re-price it.

## 6. Reproduce

```bash
python3 benchmarks/omr-symbol-ledger-2026-09/run_ledger.py \
    --pairs benchmarks/omr-wrongnote-decomposition-2026-09/scan-pairs.json \
    --out-dir benchmarks/omr-symbol-ledger-2026-09/out --no-musicdiff
python3 benchmarks/omr-part-join-2026-09/separate_causes.py \
    --ledger benchmarks/omr-symbol-ledger-2026-09/out/ledger-summary.json
python3 benchmarks/omr-part-join-2026-09/price_unlocks.py
```
