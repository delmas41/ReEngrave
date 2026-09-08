# A per-symbol ledger — an account, not a score

**2026-09-07.** Sean's commission:

> *"I don't like the idea of the measure going blank if we can't figure it out.
> Every symbol and note and word should be accounted for both in our tests and
> in our process. The second quarter note of Bar 3 is a B should be a distinct
> decision and able to be traced back to a test where that was predetermined."*

`tools/omr/symbol_ledger.py` is that account. It gives every symbol on both
sides a row, decides correspondence with **four keys instead of one**, reports
an attribute only from a pairing established by a key **blind to that
attribute**, and makes *"could not establish correspondence"* a first-class
outcome rather than a charge.

---

## 0. Read this first — the three things that are not claims

* **It changes nothing in the pipeline.** New files only:
  `tools/omr/symbol_ledger.py`, `tools/omr/tests/test_symbol_ledger.py`, and
  this directory. No existing metric, detail level or benchmark was touched.
* **Its numbers are not comparable to OMR-NED's as totals.** An OMR-NED edit is
  an operation in an edit script; a ledger row is a printed symbol. §3 measures
  one symbol costing up to twelve edits. Anyone differencing 74,956 against
  29,519 is comparing an edit count to a symbol count.
* **Nothing below is quoted unless the controls are green.** `run_ledger.py`
  runs them first and says so in its own output.

---

## 1. Why — the premature commitment

Measured on 2026-09-07 over the 20-row scan gate at `AllObjects`, the
benchmark's own detail level: **92.5% of all edits (69,349 of 74,956) are in a
bucket that names no specific error** — `wrong note` 22,174, `entire measure
insert/delete` 29,655, `entire staff insert/delete` 17,520. Only 5,607 name a
symbol attribute. (Re-derived here from the committed
`benchmarks/omr-wrongnote-decomposition-2026-09/arm-allobjects.csv`; the
16,777 quoted elsewhere for `entire staff` is the `AllObjects|Voicing` arm,
not this one.)

⚠️ The mechanism is a **premature commitment**. Without `Voicing`, musicdiff
pairs notes **by pitch** — it decides which note corresponds to which using the
quantity under measurement. A wrong pitch destroys the correspondence, so it
cannot be *reported* as a wrong pitch; it becomes a deletion plus an insertion,
and enough of those in a bar are charged as the whole bar. That is circular in
exactly the way this codebase refuses at `clef_correction.py:396` and `:566`,
`dossier.py:434` and `score_layouts.py:682`.

The ledger's answer is not a better key. **It is refusing to pick one.**

| key | pairs on | blind to | contaminated for |
|---|---|---|---|
| `ord`   | ordinal position, **only when the counts are equal** | everything | nothing |
| `onset` | beat position in the bar | pitch | duration (onset accrues durations) |
| `pitch` | step + octave | duration | pitch |
| `joint` | onset AND pitch | — | both (corroboration only) |

⚠️ **An attribute is reported only from a basis containing a key blind to it.**
`pitch` needs `ord` or `onset`; `duration` needs `ord` or `pitch`. Where no
such basis exists the attribute is `not_assessable` and is **counted as
such** — never silently scored, never silently dropped. `KEY_BLIND_TO` is that
rule as one table; `probe/mutate_ledger.py` turns it off and the suite goes red.

⚠️ `ord` **abstains** when the counts differ rather than pairing i↔i. One
missing symbol shifts every later one, and a positional pairing across unequal
counts is a guess — the same abstention `dossier` makes when staff count ≠ part
count.

Where the keys **disagree**, the row is `ambiguous` and each key's proposal is
kept on it. The table is not tidied.

---

## 2. The controls, and which number each guards

An instrument that cannot detect its own failure is the thing this project
keeps getting burned by — `page_truth.render_fidelity` exists because that
harness caught **itself** being wrong about accidentals. Five controls here.

| control | what it guards | state |
|---|---|---|
| `self_check_identity(f)` — a file scored against ITSELF | **every count.** Any outcome but `matched_exact`, or an unbalanced coverage, is a defect in the instrument | clean on all 40 scan-gate files |
| `cross_check_note_extraction(f)` — this extractor vs `training/musicxml_truth`, an **independent** parser sharing no ancestor | the note/rest counts and every onset | clean on all 40 |
| `LedgerResult.coverage_check()` | that no symbol was dropped or double-counted: *every truth symbol owns one row; every pred symbol is a partner on a truth row or owns one — never both, never neither* | balanced on every row measured |
| `mutation_matrix.py` | that a **named** error is named, and named **correctly** | 20 of 20 truth files pass with `--assert` |
| `probe/mutate_ledger.py` | that the **tests** can fail | 7 of 7 mutations fell the suite |

**Three of them ran RED before they ran green, on real defects:**

1. **The identity check caught the first defect within a minute of existing.**
   `_merge_truth_parts_symbols` sorted a single part by pitch, reordering a
   chord against the same file's own document order — so `ord`/`onset`
   proposed one pairing and `pitch` another, and a file scored **against
   itself** came out `ambiguous` on every double stop. Fixed to keep document
   order.
2. **The mutation matrix caught the second, and it is the commission's own
   failure mode.** The cell set was driven off the **prediction**: delete the
   only `<slur>` of a bar and that cell vanishes from the prediction, so the
   truth slur was never visited and fell through as
   `uncorresponded/measure_unresolved` — *the measure going blank, inside the
   instrument built to stop that.* The cell set is now the union of both sides.
3. **The mutation matrix forced the third distinction.** Delete the 2nd of four
   quarters and every later note becomes `ambiguous` (onset says one partner,
   pitch another) **except the one at the boundary**, where only `onset` names
   anything. That lone uncorroborated pairing is where the ledger's **own**
   residual misattribution lives. `basis_strength` splits `corroborated` from
   `single_key`, and single-key verdicts are reported apart and never pooled.
   **One key is one signal.**

⚠️ `probe/mutate_ledger.py` found two holes in the test suite on its first run,
and both were real: nothing asserted that a single-key pairing is flagged
(hard-coding `"corroborated"` passed all 20 tests), and one of my own mutations
was a no-op that tested nothing. Both fixed; all 7 now fell the suite.

⚠️ **A vacuous mutation is not a blind instrument, and three of them are.**
Mahler 5 p.3 and p.5 print two reference parts whose symbol streams are
identical — they differ only in `<print>` page furniture — so swapping them
changes no symbol, and both instruments correctly report nothing. Detected from
the extracted symbols, and `--assert` additionally requires musicdiff to agree
that nothing changed: an independent instrument seeing a change the ledger
calls a no-op would be a blind spot and is a failure.

---

## 3. The mutation matrix — the comparison, with no appeal to real data

⚠️ **This is the one measurement here that depends on no claim about the
corpus.** A truth file is copied, exactly one thing is changed, and the mutant
is scored against the original as if it were a prediction. The right answer is
known by construction. Pooled over **20 truth files** (`out/mutation-matrix-*.json`):

| the one thing changed | **ledger** | **musicdiff (`AllObjects`)** |
|---|---|---|
| one note's step | `note.pitch` ×1 | `wrong note` **4–12** (median 6) |
| one note an octave down | `note.pitch` ×1 | `wrong note` **4–12** (median 6) |
| one note's written `<type>`, duration untouched | `note.type` ×1 | **0–4 — and ZERO on 10 of 20 files** |
| two adjacent notes exchange durations | `duration_ql` ×2, `type` ×2 | 0–43, incl. `entire measure insert/delete` |
| one note deleted | 1–34, mostly **`ambiguous` (declared)** | 4–204, spread over `wrong note`, `wrong flag/beam`, `wrong accidental`, `wrong slur` |
| one note duplicated | 3–38, mostly `ambiguous` | 2–203 |
| one printed `<accidental>`, pitch untouched | `note.accidental` ×1 | `wrong accidental` ×2 ✓ |
| one dynamic `f`→`ff` | `dynamic.text` ×1 | `wrong dynamic` ×2 ✓ |
| one `<slur>` endpoint deleted | `slur:missing` ×1 | 2–48 |
| one measure deleted from one part | 1–33 **named** missing symbols | `entire measure insert/delete` 2–128 |
| two parts exchange all their music | 4–174 | **34–590**, `wrong note` 2,592 pooled |

Five things fall straight out of that table.

1. **A single wrong pitch is charged a median of 6 edits and is never called a
   pitch error.** It lands in `wrong note`, a bucket whose name says *note*.
   The ledger names it, once, at its address.
2. **`wrong note` mixes pitch and duration.** The duration swap — no pitch
   moved — puts most of its mass in `wrong note` too. CLAUDE.md warns of this;
   here it is demonstrated rather than inferred.
3. ⚠️ **A wrong written value with a right sounding length is INVISIBLE to
   musicdiff on half the files** (0 edits, 10 of 20). Where it does register it
   arrives as `wrong flag/beam` or `wrong note head` — the *consequences* of
   the type, not the type. Given that this project's entire rhythm thread is
   about beam levels and written values, that is a blind spot worth knowing.
4. **Amplification differs by error kind — 6× for a pitch, 2× for an
   accidental — so bucket sizes are not comparable to each other as error
   counts.** ⚠️ **You cannot rank what to fix by comparing bucket totals.**
   That is the single most consequential line in this document.
5. **A deleted note lands edits in buckets about symbols that were not
   touched** — `wrong accidental`, `wrong slur`. Named buckets are contaminated
   by unpaired neighbours, so even the 7.5% that names something is not clean.

And one about the ledger: for a deletion or an insertion it mostly answers
**`ambiguous`**, and that is the correct answer. Removing a note from the
middle of a bar leaves two readings genuinely consistent with the encoding —
"note 2 is gone and the rest shifted", or "note 2 has the wrong pitch and
length". An instrument that picks one silently is the one being replaced.

---

## 4. The 20-row scan gate

`run_ledger.py` takes all three joins from `works.json` as **input**: the
measure window, the hand-verified `staves[i].parts`, and the arity check.

### 4a. Part correspondence, first — because it is upstream and it is the big one

⚠️ **8 of 20 rows have no part correspondence at all**, and the ledger says so
instead of billing them. The join is positional (`staves[i]` ↔ predicted part
`i`) and is taken **only where the arity agrees**. The failures are not one
thing, and this taxonomy is the diagnostic OMR-NED cannot give — today all of
it is one bucket, `entire staff insert/delete`:

| rows | lineup vs predicted parts | why |
|---|---|---|
| `beethoven-984073-p3`, `beethoven-575951-p3`, `brahms-p2` | 11 vs 19, 11 vs 19, 14 vs 27 | `export._stitch_slots` **refused** (systems disagree about staff count) and emitted one part per system-staff |
| `mahler-p3`, `p4`, `p5` | 15 vs 13, 21 vs 18, 21 vs 17 | the lineup counts **one-line percussion staves** a five-line detector cannot find |
| `mahler-p2` | no `staves` map | the row carries `staves_as_printed` instead |
| `bach-p1` | 11 vs 12 | the lineup's `Cembalo (grand staff, 2 printed staves)` is **one entry for two printed staves** — an arity convention mismatch, not a reading error |

Three different fixes. `OMR_SLOT_STITCH` addresses the first group and is
already measured and dormant; the second is a detector limit; the third is a
data-format convention in `works.json` itself.

⚠️ **A data hazard found on the way, recorded not fixed.**
`works.json` lets `staves` be the string `"same-as:<row_id>"`. Five separate
resolvers exist in this repo and **`mxl_verdicts._staff_specs` is not one of
them** — it reads the string as 37 one-character staff names carrying no parts,
and abstains. It fails safe today; it is a trap for the next consumer.

### 4b. What the ledger says, over the whole gate

29,519 symbol rows over 20 pairs. Controls clean on all 40 files.

| outcome | rows | share |
|---|--:|--:|
| `uncorresponded: part_unresolved` | 14,992 | 50.8% |
| `spurious` | 3,186 | 10.8% |
| `ambiguous` | 2,904 | 9.8% |
| `matched_attribute_error` | 2,879 | 9.8% |
| `missing` | 2,783 | 9.4% |
| `matched_exact` | 2,723 | 9.2% |
| `uncorresponded: measure_unresolved` | 52 | 0.2% |

⚠️ **The 92.5% and the 51% look alike and are not the same quantity.**
musicdiff's unnamed mass is what it **charged without diagnosing**; the
ledger's is what it **declined to charge** because the correspondence was not
established. That difference is the whole point.

### 4c. Restricted to the 12 rows whose part join RESOLVED

14,527 symbol rows. Pooling these with the other eight would let a page with no
correspondence dilute the attribution for pages that have one — the same reason
`boulanger` is not pooled into the engraved benchmark.

| outcome | rows | share |
|---|--:|--:|
| `spurious` | 3,186 | 21.9% |
| `ambiguous` | 2,904 | 20.0% |
| `matched_attribute_error` | 2,879 | 19.8% |
| `missing` | 2,783 | 19.2% |
| `matched_exact` | 2,723 | 18.7% |

Pairings: **4,265 corroborated, 1,337 single-key.**

⚠️ **One symbol in five is `ambiguous` even where the part join holds.** That
is a number nothing in this project has reported before, and it is not an
instrument limitation to be tuned away — it is the honest size of the
population where the encoding admits more than one reading.

**And it is LOCALISED, which is the encouraging half.** Of 7,577
(staff, bar, family) cells on the joined rows, **1,304 — 17.2% — hold any
ambiguity at all**, and **594 of those hold exactly one**. The mode is a single
symbol at an insert/delete boundary, not a bar dissolving: the mechanism §2
item 3 describes, where `onset` proposes the shifted partner and `pitch` the
unshifted one. It is 2,533 notes, 139 ties, 87 articulations, 83 slurs, and it
splits almost exactly evenly between the two sides (1,432 truth, 1,472 pred),
which is what a boundary effect looks like and what a systematic bias would
not.

**Named attribute errors, corroborated pairings only.** ⚠️ Counted by SYMBOL,
not by attribute: `duration_ql` and `type` are not independent (a rest read as
the wrong value has both wrong), and adding them double-counts.

| | symbols |
|---|--:|
| pitch-only (notes) | 895 |
| duration-only (**rests**) | **476** |
| duration-only (notes) | 235 |
| both pitch and duration | 152 |
| key signature `fifths` | 68 |
| dynamic text | 48 |
| tie endpoint / clef | 15 / 15 |
| time signature | 13 |

* **Notes alone: pitch 1,047 vs duration 387 — 2.71 : 1.** This **corroborates**
  `omr-wrongnote-decomposition`'s finding that pitch outweighs duration, from a
  different instrument with a different unit, and puts the ratio higher.
* **Counting every symbol: 1,047 vs 863 — 1.21 : 1**, because **476 rests have
  a wrong duration and no pitch to be wrong about.** ⚠️ Rests are 55% of the
  duration mass and are **invisible to any note-level analysis.** That is new.
* This is exactly what the decomposition's own §3 warned: *"the grouping is a
  judgment, and a different one moves the ratio."* Both readings are here, with
  the grouping stated.

### 4d. Families that are wholly absent — the inventory a bucket total hides

On the 12 joined rows, some families are **100% `missing`**:

| family | truth rows | matched |
|---|--:|--:|
| `hairpin` | 140 | **0** |
| `ornament` | 64 | **0** |
| `barline` | 43 | **0** |
| `word` | 111 | 16 |
| `metronome` | 5 | **0** |

⚠️ **`hairpin` is not a bug** — `OMR_CV_HAIRPINS` is **off by default**, priced
and deliberately dormant because the reader costs OMR-NED. Verified on my own
`origin/main` run: 3 hairpin detections across 19 scan pages. *Comparison
validity before mechanism* — this is the knob, not a defect.

`barline` and `metronome` are on `export_coverage.KNOWN_GAPS`. **`ornament` is
not**, and §7a is about why.

---

## 5. Where the ledger and OMR-NED disagree, per row

`compare_to_omrned.py` prints this and writes `out/comparison.json`. The
musicdiff side is read from the **committed** `arm-allobjects.csv`, never
re-measured, so it cannot drift from the figure the project already reports.

The pattern is uniform and stark: **musicdiff's unnamed share is 85–96% on
every one of the 20 rows** — it does not fall on the rows where the ledger
corresponds everything. On `beethoven-984073-p1`, where the part join resolves,
the measure map is verified and the ledger corresponds **100%** of symbols,
musicdiff still puts **88%** of its 1,273 edits in buckets that name nothing.

That is the finding in one line: **the unnamed mass is not a property of how
badly we read the page. It is a property of the metric.**

---

## 6. What this changes about which fixes are worth doing

1. ⚠️ **Stop ranking work by bucket size.** §3 measures amplification differing
   6× to 2× by error kind, and §5 shows the unnamed share is flat across rows
   of very different quality. A bucket total is not an error count and two
   buckets are not comparable to each other.
2. **Part correspondence is the top item, and it is three items.** 51% of all
   symbol rows sit behind it. The taxonomy in §4a splits it into a stitching
   refusal (already measured — `OMR_SLOT_STITCH`), a detector limit (one-line
   percussion staves), and a `works.json` arity convention. Only the first is
   currently on anyone's list.
3. **Rests are a duration population nobody is counting.** 476 rests with a
   wrong duration against 235 notes — twice as many — and every note-level
   analysis this project has run is blind to them.
4. ⚠️ **A wrong written value with a right sounding length is invisible to the
   metric on half the corpus.** Any rhythm work whose effect is on `<type>`
   rather than on `<duration>` will measure as approximately nothing. Price it
   with the ledger, not with OMR-NED.
5. **`ambiguous` at 20% is a target in its own right.** These are symbols whose
   correspondence the *encoding* cannot settle. Some of it would fall to better
   reading; some of it is irreducible. Nobody has had a number for it before.
6. **`export_coverage`'s inventory is bounded by a hand-written list, and the
   bound is not stated in the module.** See below.

---

## 7. Pipeline observations — recorded, deliberately NOT fixed

Per the brief: found while measuring, written down, left alone.

### 7a. ⚠️ `export_coverage` cannot report a gap in an element nobody listed

`export_coverage.compare()` iterates `sorted(VISIBLE)` — a **hand-written list
of 19 element names**. An element absent from that list can never be reported,
however large the disparity. `KNOWN_GAPS`'s docstring says *"Anything NOT here
is a new gap and fails the test"*; the real gate is `VISIBLE ∖ KNOWN_GAPS`, and
an element in **neither** list fails nothing.

Measured over the **engraved** benchmark's own 11 committed fixture pairs —
the corpus `export_coverage --all` runs on — and over the 20 scan pairs:

| element | engraved truth | scan truth | ours (both) | in `VISIBLE`? |
|---|--:|--:|--:|---|
| `ornaments` | 12 | 131 | **0** | **no** |
| `tremolo` | 12 | 123 | **0** | **no** |
| `transpose` | 92 | 176 | **0** | **no** |
| `grace` | 0 | 25 | **0** | **no** |
| `bracket` (direction) | 0 | 146 | **0** | **no** |

`python3 -m tools.omr.export_coverage --all` reports six gaps and none of
these. **`ornaments` is the one that matters**, and it has the exact shape of
the nine "detected, then dropped on the way out" bugs this project has already
paid for by forensics: `ornamentTrill` ×12 and `ornamentMordent` ×1 **are
detected** on my `origin/main` scan run, and `grep -c ornaments
tools/omr/export.py` is **0**. The exporter has no code for them at all.

⚠️ Stated precisely, so nobody overclaims: 13 detections against a truth of
131 makes this **mostly a recognition shortfall as well**. What is categorical
is the export half — nothing that *is* read can reach the file.

⚠️ `transpose` is arguably an encoding fact rather than a printed symbol, so
excluding it may be right — but it should be *stated* in `NOT_SCORED`-style
prose the way `page_truth` states its exclusions, not left off a list silently.

### 7b. Tuplet markup is fine — checked before claiming

`time-modification` and `<tuplet>` are absent from all 20 scan exports, which
looks like a tenth export gap. It is not: `export.py` emits both (4 mentions
each) and does so on the engraved benchmark (132 and 88 against a truth of 141
and 94). Scans simply detect no tuplet markers. **Recognition, not export.**

### 7c. `arpeggiato` ×893

893 `arpeggiato` detections across 19 orchestral scan pages, the sixth-largest
class on the corpus and larger than `slur`. Not investigated; recorded because
an implausible count is worth someone's eye.

---

## 8. What this instrument CANNOT measure — an inventory, not a silence

* **It compares two ENCODINGS, not the page.** `page_truth.py` does the
  page-level job for pages we render, and its lesson stands: a clef is printed
  at every system and declared once. Both sides here are MusicXML so the
  convention is shared — but **a symbol the print carries and neither file
  encodes is invisible to this instrument, exactly as it is to OMR-NED.**
  Ink is out of scope.
* **Chord members' pitch verdicts are contaminated, and are flagged.** Chord
  members share an onset, so `onset` cannot order them; both sides order a
  chord by pitch, which makes the within-chord pairing pitch-derived. Those
  rows carry `chord_member=True`.
* **A condensed staff's unison collapse uses pitch.** It is a **truth-side**
  transformation — nothing about the prediction enters it — so it cannot create
  the circularity this module removes, but it is a pitch-keyed decision and is
  stated rather than hidden. Rows from a condensed staff carry `condensed=True`.
  Within one onset the merged parts keep **roster order**, not pitch order.
* **It cannot say whether a `hypothesised` measure map is right.** Where the
  bar count disagrees with the verified window (4 of 20 rows) the offset map is
  a hypothesis and every row it produced says so. It does not search for the
  bar that went missing.
* **It has its own residual misattribution**, and it is localised: the
  single-key pairing at a deletion boundary (§2, item 3). 1,337 of 5,602
  pairings on the joined rows are single-key; their verdicts are reported apart
  and are **never** pooled with the corroborated ones.
* **It says nothing about DIRECTION.** OMR-NED remains the right tool for
  "did this change help", because both arms are scored identically. The ledger
  is for "what kind of error do we have". Use each for its own question.

---

## 10. Reproducibility — a second, independently transcribed arm

⚠️ Everything in §4 is measured on the `basectl` predictions from another
agent's worktree. A single set of predictions is a single set of predictions,
so the whole gate was **re-transcribed from `origin/main` in this worktree**
(`scan_eval.py --tag=-ledger`, own fixtures dir, own `results-ledger.json` —
the caching trap the scan-gate notes warn about needs a distinct `--tag=` and
that is what this used) and the ledger run again over the new pairs.

The two transcription runs agree with each other on OMR-NED to within the
gate's documented noise: **74,873 edits (0.8438) against the basectl arm's
74,956**, ~4 edits a row.

And the ledger's picture is the same to within a few rows in twenty-nine
thousand:

| | basectl arm | own `origin/main` arm |
|---|--:|--:|
| `spurious` | 21.9% | 21.8% |
| `ambiguous` | **20.0%** | **20.1%** |
| `matched_attribute_error` | 19.8% | 19.8% |
| `missing` | 19.2% | 19.2% |
| `matched_exact` | 18.7% | 18.8% |
| corroborated `note.pitch` | 1,034 | 1,031 |
| corroborated `rest.duration_ql` | 471 | 471 |
| rows with a resolved part join | 12 of 20 | 12 of 20 |

So none of §4 is an artefact of which tree produced the predictions.
`out/` holds the first arm, `out-ownrun/` the second.

---

## 9. Reproducing

```bash
# controls + the whole gate (musicdiff on the same pairs)
python3 benchmarks/omr-symbol-ledger-2026-09/run_ledger.py \
    --pairs benchmarks/omr-wrongnote-decomposition-2026-09/scan-pairs.json \
    --out-dir benchmarks/omr-symbol-ledger-2026-09/out

# the comparison, off committed musicdiff data
python3 benchmarks/omr-symbol-ledger-2026-09/compare_to_omrned.py

# one known error at a time, both instruments, --assert exits non-zero
python3 benchmarks/omr-symbol-ledger-2026-09/mutation_matrix.py \
    --truth <a truth .musicxml> --assert

# look a symbol up by its address
python3 benchmarks/omr-symbol-ledger-2026-09/lookup.py \
    --row beethoven-sym5-mvt1-984073-p1 --part Violin --measure 3 --beat 2

# the tests, and the proof they can fail
python3 -m pytest tools/omr/tests/test_symbol_ledger.py -q
python3 benchmarks/omr-symbol-ledger-2026-09/probe/mutate_ledger.py

# the instrument's own controls, on any file
python3 -m tools.omr.symbol_ledger --self-check  <file>.musicxml
python3 -m tools.omr.symbol_ledger --cross-check <file>.musicxml
```

`out/ledger-rows.csv` is the account itself — one row per symbol, with its
address, its outcome, the keys that agreed, and what disagreed.
