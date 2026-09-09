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


---

## 7. RESOLVED, 2026-09-08 later the same day: causes B, C and A all closed

### B and C — the arity gate now compares like with like

The two engraving facts are **fields in `works.json`** rather than prose:
`one_line: true` on nine percussion-rule entries, `printed_staves: 2` on bach's
cembalo. `run_ledger.expand_lineup` turns the lineup into one entry per part we
could emit — a one-line rule contributes none, a `printed_staves: N` entry
contributes N with only the first carrying the reference parts (⚠️ **not all N
mapped to the same truth part**, which would visit those symbols N times and
unbalance the accounting control).

⚠️ Each declaration is **asserted against the number that IS derivable**
(`len(staves) - page.n_staves`) at write time, and `test_works_json_staff_lineup.py`
re-asserts it on every suite run — **run RED against two mutants** (a removed
`one_line`, a removed `printed_staves`). A future hand-verified row that gains a
one-line staff without its flag fails there rather than surfacing weeks later
as an unexplained refusal.

### A — `OMR_SLOT_STITCH` is DEFAULT ON (Sean's call, 2026-09-08)

⚠️ **The flag site's own docstring carried the refuted claim** — *"it still
costs more OMR-NED than the fragments do"* — which was the stated reason to
leave it off, and which `benchmarks/omr-staff-structure-2026-09/FINDINGS.md` §4
and the 2026-09-07 re-price both contradict. CLAUDE.md had carried the
correction for a day; the code had not. Corrected in place.

⚠️⚠️ **AND THE CANARY THIS FILE'S AUTHOR RECOMMENDED DOES NOT REACH THE FLAG.**
`label_contradiction` looked like the free check for a grafting join — it needs
no truth file and asks whether `staff → slot → name` is broken. It is computed
in the CONTEXTUAL pass and stored in the transcription; `OMR_SLOT_STITCH` is
read in `export.py`, strictly downstream. A transcription's contradiction count
is identical with the flag on and off **by construction**. Naming a mechanism
is not measuring one, and this was recommended before it was checked.

Its QUESTION does reach it, applied at the join instead of at the staff:
`slot_stitch_canary.py` asks, for each part the slot join builds out of several
staves, whether **those staves' own margin labels agree with each other**. No
truth file; the document is asked to agree with itself.

    reached 4 of 11 rows   agree 30   DISAGREE 0   no_evidence 18
    positive control: 30 stitched parts had label evidence at all

⚠️ The `no_evidence` column is reported, never folded into `agree`: on a scan
most staves carry no printed label, and a part of unlabelled staves is not
corroboration. ⚠️ The canary reaches a SUPERSET of the flag — it scores the
slot join wherever it is computable, including rows where the ordinal join
succeeds and the flag never fires, which is corroboration that the join is
sound where an independent join can be checked against it.

### The arc, measured on the 11 committed pairs

| | rows with a resolved part join |
|---|--:|
| session start (ledger fed `works.json` as it stood) | **7 of 11** |
| + `one_line` / `printed_staves` fields (B, C) | **9 of 11** |
| + `OMR_SLOT_STITCH` default ON (A) | **10 of 11** |

Brahms 1 p2 goes from **0% correspondence to 100%**; 10 of 11 exports are
**byte-identical** with the flag on and off, and the one that changes is
exactly the 27 fragments becoming 14 continuous parts. On the 20-row gate the
arity fields alone take pooled `part_unresolved` **14,992 → 7,985** and joined
rows 12 → 16.

**Only cause D remains** — mahler p2 needs a `staves` map, and nothing on disk
can supply it.

---

## 7. ⚠️ CAUSE D WAS CLOSED AND THE ROW LANDED IN CAUSE **B** — the map arrived without its arity fields (2026-09-08)

`1cf44dbc` supplied the fact §5 said nothing on disk could supply: Sean's
confirmation pass gave mahler p2 a 21-entry `staves` map, every entry
`confirmed`, and the scan gate went **20/20 mapped**. That closes D as stated.

**It did not make the row assessable.** The map lists PRINTED staves and the
row prints four one-line percussion rules, so `expand_lineup` read 21 five-line
slots against our 17 parts and the arity gate refused — the row moved from
`D_no_lineup` straight into `B_undetectable_staves`, which is
`separate_causes.classify` doing exactly what it says (`n_map > n_pred`).
The bucket total did not move; only its label did.

⚠️ **`test_works_json_staff_lineup.py` caught it, and it is the only thing that
did.** Both tests written with the B/C fields failed the moment the row landed:

```
mahler-sym5-mvt1-local-p2: the lineup expands to 21 five-line staves but the
page prints 17 per system.
mahler-sym5-mvt1-local-p2: 0 entries flagged lines:1 and 0 extra printed
staves, but len(staves) - n_staves = 4
```

Nothing else notices. `merge_additions` proved the map NORMALISES, every
`page_normalise` check passed, and the ledger's own refusal reads as an honest
abstention rather than a defect.

### The fix: four fields, and the row already carried the answer twice

`Becken`, `Grosse Trommel`, `Kleine Trommel`, `Tamtam` take `lines: 1`.
**Neither the identity nor the count was inferred from the instrument names** —
both are read off facts the row already holds, and they agree:

* `page.n_staves_note` names the rules in prose (*"FIVE one-line percussion
  staves — Becken, Grosse Trommel, `Becken/Gr.Trommel von einem geschlagen`,
  Kleine Trommel, Tamtam … Compare `detected` against 17, not against 22"*);
* `condensation.staves_as_printed` carries a `lines` value for **all 21**
  entries independently, and after the fix every one of the 21 agrees with it.

⚠️ **`Pauken` is a five-line staff and is NOT flagged** — the one entry a
name-matching rule would have got wrong.

⚠️ **The prose says FIVE rules and only FOUR entries are flagged.** The fifth
is `Becken u. Gr.Trommel von einem geschlagen`, the combined-player staff the
Gradus reference has no part for, so it is not a lineup entry at all — the
row's own `condensation.notes` records it as the 22nd printed staff. 21 − 4 =
17 = `page.n_staves`, exactly.

Extending §1's B table with the row that belongs in it:

| row | lineup | one-line rules named in the row's own note | five-line | we emitted |
|---|--:|---|--:|--:|
| mahler p3 | 15 | Becken, Gr.Tr. (2) | 13 | **13** |
| mahler p4 | 21 | Becken, Gr.Tr., Kl.Tr. (3) | 18 | **18** |
| mahler p5 | 21 | + Tamtam (4) | 17 | **17** |
| **mahler p2** | **21** | **Becken, Gr.Tr., Kl.Tr., Tamtam (4)** | **17** | **17** |

### Measured — controlled A/B, same tree, only `works.json` differing

`run_ledger.py` twice over the same fixtures and the same pairs file, control
at `2017fb11` with the map as `1cf44dbc` left it, arm adding the four fields
and nothing else. Full record: `mahler-p2-oneline-ab.json`.

| | control | arm |
|---|--:|--:|
| rows with a resolved part join | 16 of 20 | **17 of 20** |
| pooled `part_unresolved` | 7,985 | **7,266** (−719) |
| pooled `uncorresponded` | 8,179 | **7,460** |
| p2 `n_lineup_slots` / `n_one_line_dropped` | 21 / 0 | **17 / 4** |
| p2 `uncorresponded` | 771 | **52** |

⚠️ **EXACTLY ONE ROW CHANGES.** The other 19 are identical outcome for
outcome, and pooled musicdiff is identical between the arms — it must be,
because `works.json` does not reach it, which makes it a live control on the
harness rather than a claim.

⚠️ **THE ROW'S ASSESSABLE MASS IS NOT 719 NEW SYMBOLS.** The same 527 truth and
244 predicted symbols enter both arms and `coverage.balanced` is `True` in
both; what changes is that 194 predicted symbols stop owning a row of their own
and become a truth row's PARTNER (`pred_rows_own` 244 → 50). The 771 → 52 fall
is that pairing, not new evidence. p2 gains `matched_exact` 46,
`matched_attribute_error` 148, `missing` 59, `ambiguous` 17, `spurious` 44 and
`absorbed_by_condensation` 211, all of which were unsayable before.

### ⚠️ The 52 that remain are the right 52

Broken out, they are **13 rows each on truth parts 23–26 — `Becken.`,
`Grosse Trommel.`, `Kleine Trommel.`, `Tamtam.`** — a clef, a key, a time
signature and 10 rests apiece. That is `expand_lineup`'s declared behaviour,
not a residual fault: a five-line staff detector cannot find a single printed
rule, so those four staves' music is genuinely unread and the fields say so
instead of joining it to something. **The fix buys the assessability of 17
staves and declares 4 unread; it does not claim to read them.**

### ⚠️⚠️ THE GENERATOR CANNOT CARRY THE FIELD, SO THIS WILL RECUR

Not a typo in one row — a gap in the path that writes them.
`merge_additions.shape_problems` **refuses** any key beyond `name`/`parts`:

```python
extra = set(s) - {"name", "parts"}
if extra:
    out.append(f"entry {k} has unexpected key(s) … entries are exactly name+parts")
```

and the confirmation pipeline never offers one: p2's row in
`works.staves-additions.json` carries `{name, parts, proposed, verdict}` and
its `proposed` entries are `{name, parts}`. So a map with `lines: 1` would have
been **rejected at merge time**, and the UI had nothing to propose.

⚠️ `build_cache.py` DOES compute it — `"lines": spec.get("lines", 5)` at line
496, over a `lines: 1` band-splicing path with its own comment saying *"a map
entry carries `lines`, because 1 vs 5 is exactly what tells a …"*. **The value
is computed upstream and dropped between the cache and the file** — the pattern
CLAUDE.md now records four instances of in one day. The `lines` field landed in
`166759fc`; this writer predates it and was never widened.

⚠️ **FIXED 2026-09-08, in §8 below** — the deferral above was reversed the same
day, and the reason is worth keeping: *"no unmapped row remains to exercise
it"* is an argument for a cheap fix, not against one, because the failure costs
a HUMAN CONFIRMATION PASS rather than compute, and corpus widening is what the
score library is for.

### Reproduce

```bash
python3 -m pytest tools/omr/tests/test_works_json_staff_lineup.py -q
python3 benchmarks/omr-symbol-ledger-2026-09/run_ledger.py \
    --pairs benchmarks/omr-wrongnote-decomposition-2026-09/scan-pairs.json \
    --out-dir /tmp/ledger-arm
```

⚠️ Give each arm its own `--out-dir`, and check the clock: a run over the
20 rows is ~4 minutes here. (The `scan_eval` caching trap CLAUDE.md records is
a different harness, but the same instinct applies — an A/B that returns
instantly did not run.)


---

## 8. The writer now carries the fields — and asks the arity question BEFORE the merge (2026-09-08)

§7's gap, closed. The chain was never one broken link: `build_cache` computed
`lines` and **four** projections between it and the file dropped it.

| site | was | now |
|---|---|---|
| `server.py` row seed | rebuilt `{name, parts}` from `seed["proposal"]["staves"]` | carries `ARITY_FIELDS` |
| `server.py` `staves_for_works_json` | rebuilt `{name, parts}` inline | calls the shared projection |
| `merge_additions.check_row` | rebuilt `{name, parts}` | calls the shared projection |
| `merge_additions.shape_problems` | refused any key but `name`/`parts` | allows the two, **validated** |

**One projection, `_entry_for_works_json`, imported by the UI from the merge
step** — the same "two consumers cannot drift apart" move `prove_normalises`
already makes in this file. A projection repeated is a projection that drops
something.

⚠️ **ALLOWED IS NOT UNCHECKED.** A typo'd `lines` silently changes how many
parts a row is expected to emit — the exact failure the field exists to
prevent — so `lines` must be 1 or 5 (anything else "needs a decision, not a
default"), `printed_staves` a positive int, and an entry may not be both a
one-line rule and several printed staves. Unknown keys still refuse, which the
pre-existing `test_the_other_shape_refusals_are_untouched` pins.

### The guard that was missing, and where it belongs

`arity_problems(row, staves)` asks of the map about to be WRITTEN exactly what
`test_works_json_staff_lineup.py` asks of the file: does the lineup expand to
the five-line count `page.n_staves` states? It calls
**`run_ledger.expand_lineup` rather than recomputing** — that function *is* the
definition of how many parts a lineup expects, and a second copy would drift
from the consumer. It abstains on non-uniform pages (beethoven p3 is 11 then 8)
exactly as the test does.

⚠️ **The point is WHEN it fires.** A test on the data fires after a map is
merged — on mahler p2 that meant after a 21-staff human pass had been spent.
The same question asked at the writer refuses the merge, with the missing field
named in the message.

### ⚠️ Retrospective control: it refuses ALL FIVE historical rows

Dry-running the merge step against the additions file as it stands today, the
guard fires on mahler p2/p3/p4/p5 **and** bach — every row whose additions
entries predate the `lines` field:

```
REFUSE mahler-sym5-mvt1-local-p2: the lineup expands to 21 five-line staves
       but the page prints 17 per system (21 entries, 0 flagged `lines: 1`)
REFUSE bach-brandenburg3-mvt1-468678-p1: … 11 … but the page prints 12 …
```

So it reproduces the defect on the whole population that had it, not only on
the row that was noticed. **No behaviour changes for them** — all five already
refuse on *"works.json already carries a `staves` map"*; the guard adds a line
to an already-refusing row. And a stale additions file whose
`staves_for_works_json` was stamped by the old UI now fails LOUDLY instead of
writing an unflagged map.

### Tests, each run RED against a mutant

`tools/omr/tests/test_staves_map_validation.py`, +200 lines. Five mutants, each
failing exactly the intended test and nothing else:

| mutant | red test |
|---|---|
| `check_row` stops calling the guard | `test_check_row_asks_it` |
| the guard always returns `[]` | `test_THE_REAL_MAP_THAT_SLIPPED_THROUGH_is_refused` |
| `shape_problems` refuses extras again | the two acceptance tests |
| the projection drops the fields | `test_the_projection_preserves_them` |
| the UI rebuilds `{name, parts}` inline | `test_the_ui_uses_the_shared_projection` |

⚠️ **The decisive test is not synthetic**: it feeds `arity_problems` mahler p2's
map *exactly as `1cf44dbc` merged it* and asserts the refusal names the missing
field. And `TestAOneLineRuleSurvivesTheWholeWritePath` proves the chain rather
than the links — a declared one-line rule passes every gate and reaches
`works.json` with the field intact, against a control that removes only that
field and is refused.

### ⚠️ A regression made and caught while building the guard

Gating `arity_problems` on `problems` rather than on the SHAPE problems
specifically silences it wherever a row *already carries a map* — that is, on
every historical row, which is exactly the population the retrospective control
above is made of. **The dry run went 5 refusals → 0 and nothing else moved.**
The narrow gate exists only so a malformed `lines` cannot RAISE inside
`expand_lineup`; it must not also swallow the report. Both halves are now
pinned (`test_an_ALREADY_MERGED_row_still_gets_the_arity_report`, run red
against the broad gate; `test_a_malformed_shape_does_not_reach_the_guard`).
**A gate that suppresses a report is a second thing, and it needs its own
test.**

⚠️ **One existing test was left alone rather than loosened.**
`test_the_confirmation_ui_asks_it_too` asserts the literal
`from merge_additions import prove_normalises`, which a tidy parenthesised
import broke. The import was written back out as separate single lines: a guard
is not to be relaxed to suit a later edit.
