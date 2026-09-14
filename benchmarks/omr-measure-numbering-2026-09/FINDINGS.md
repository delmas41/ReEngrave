# A measure is numbered by the DOCUMENT's bar sequence, not the part's own count

2026-09-14, no flag. Ranked item 3 of the Phase 2 handoff, and the second of
the three repairs `benchmarks/omr-part-join-phase2-2026-09/` put in order —
*"a measure must be numbered by its place in the DOCUMENT's bar sequence rather
than its part's own running count, **which alone makes `<measure number=N>`
mean one instant, writes no music and needs no meter**."*

**This job writes no music. It changes one attribute.**

---

## 1. THE DEFECT

`staged/export.py:_part_xml` counted `number += 1` down each part from its own
first bar. A printed orchestral score suppresses tacet staves, so a part absent
from a system simply skipped that system's bars and **every later number in
that part was short by exactly the skipped system's length**.

On the measured document — Litolff Beethoven 5 mvt 1, pdf pp.1-4, 7 printed
systems, 12 parts, 1,183 measures — `probe/partition.py` already had the
arithmetic: eight parts hold 111 bars, `P9-P11` hold 93 (missing p3/s1's 18)
and `P12` holds 16. So page 4's first system opened at **measure 64 or 82
depending on which part you read**, and p4/s1 at 79 or 97. Verovio said
`Mismatching measure number 87` out loud.

---

## 2. THE RULE, AND WHAT IT DOES WHEN IT CANNOT TELL

`export._document_bar_offsets(parts)`. Systems in reading order `(page,
system)`; a system's offset is the sum of the bars of every system before it; a
measure is `offset + i + 1`.

**A system's bar count is the single value its own staves agree on** — over the
staff-runs whose `measure_partition` DECIDED. ⚠️ An ABSTAINING staff says
nothing and is not a vote for zero, which is why `StaffRun` gained
`n_measures_decided`: `n_measures` reads 0 for an abstention *and* for a decided
zero, and the tally must not confuse them.

⚠️⚠️ **Three conditions leave a document unnumberable, and none of them is
converted into an answer** — CLAUDE.md's governing rule, *a fallback must never
convert "cannot tell" into a definite answer*:

| condition | reported as |
|---|---|
| no staff on a system decided its bar count | `no_staff_decided_its_bar_count` |
| two staves of one system read different lengths | `staves_disagree_about_the_bar_count` |
| one part holds two runs on one system (slot join only) | `a_part_holds_two_runs_on_one_system` |

⚠️ **A MAJORITY VOTE IS AVAILABLE AND IS REFUSED.** Nine staves reading 4 and
one reading 3 is *most likely* 4 — which is INFER-stage work by this repo's own
stage table, and *a wiring pass may CONNECT a decision, it may not let one
GUESS*. A test pins it (`test_a_MAJORITY_is_not_taken_it_is_refused`).

⚠️ **The refusal is WHOLE-FILE, and that is the load-bearing choice.** A file
numbered document-wide up to the bad system and part-wise after it is a file
where `<measure number=N>` means two different things with nothing saying where
the boundary lies — *"cannot tell"* converted into a definite answer by the
SHAPE of the output. Refusing returns the exporter to EXACTLY its previous
behaviour, so this change can never leave a file worse numbered than the one it
replaces; what it can do is leave it unimproved, **out loud**, in
`report["measure_numbering"]`, which is written whether or not the scheme fires
— *"we numbered the document"* and *"this figure was never computed"* must not
read alike.

---

## 3. REACH — and why this is not a re-export

⚠️⚠️ **A CLOUD CONTAINER HAS NO WEIGHTS AND NO LIBRARY, AND NO STAGED RECORD IS
COMMITTED.** `benchmarks/omr-cleanup-count-2026-09/out/` holds the exported
MusicXML and the SYSTEM MAP; `record-p1-p4.json` is not in the tree. So
`to_musicxml` cannot be called on the real document here.

`probe/numbering_arm.py` does what `export_arm.py` did when it built that map:
it reconstructs the exporter's own `StaffRun` objects from the map — which was
asserted measure-for-measure against this very XML when it was written — and
calls the **SHIPPED `export._document_bar_offsets`** on them. The rule under
test is the one in the tree; only its INPUT is reconstructed.

```
   document        : benchmarks/omr-cleanup-count-2026-09/out/record-p1-p4.json
   record commit   : 9d4ccc85 (dirty=True)
   parts           : 12
   systems         : 7  (p1/s0, p2/s0, p2/s1, p3/s0, p3/s1, p4/s0, p4/s1)
   staff-systems   : 75
   measures in file: 1183
   staves/system   : {8: 1, 11: 5, 12: 1}
   parts TACET on at least one system: 4 of 12  <-- the population
```

The arm **exits non-zero declaring itself DEAD** when that last line is 0: a
document where every part appears on every system numbers identically under both
schemes and this instrument has nothing to measure.

⚠️ **One fidelity condition is CHECKED rather than assumed.** The map drops a
staff-run with zero measures, so a run whose partition DECIDED zero would be a
vote the map cannot show. The arm asserts every system's map entries account for
every staff the export's own `staves_per_system` provenance records — 75 of 75
here, so no such run exists on this document — and refuses to score otherwise.

⚠️ **THE BLIND SPOT, NAMED.** An arm that re-numbers an already-exported file is
blind by construction to everything upstream of `_part_xml`. It cannot say the
exporter as a whole still behaves; that is the unit suite's job, and
`tools/omr/tests/test_staged_measure_numbering.py` drives `to_musicxml` end to
end on synthetic records for exactly that reason. **The two instruments have
opposite blind spots on purpose.**

---

## 4. THE RULE'S ANSWER, AND THE A/B

```
   scheme: document   document_bars: 111   refused: —

   system     bars   offset  deciding  readings
   1/0          16        0        12  [16]
   2/0          16       16        11  [16]
   2/1          15       32        11  [15]
   3/0          16       47        11  [16]
   3/1          18       63         8  [18]
   4/0          15       81        11  [15]
   4/1          15       96        11  [15]
```

All seven systems are unanimous; `16+16+15+16+18+15+15 = 111`, the length of a
part present on every system, which is `partition.py`'s own figure.

**Measures whose number MOVES: 90 of 1,183 (7.6%)** — 30 each on P9, P10, P11,
and **zero on the other nine parts**, which is the result agreeing with itself:
only a part tacet on an EARLIER system can be mis-numbered, and P12 (present on
p1/s0 alone) is tacet only on later ones.

| part | measures | moved | p4/s0 opens | p4/s1 opens |
|---|--:|--:|---|---|
| P1-P8 | 111 | 0 | 82 | 97 |
| P9-P11 | 93 | **30** | **64 → 82** | **79 → 97** |
| P12 | 16 | 0 | — | — |

---

## 5. DOES `<measure number=N>` NAME ONE INSTANT? — music21 read-back

⚠️ The defect was reported by a PARSER (Verovio), so the repair is verified by
one. `probe/read_back.py` parses both files with music21 (Python 3.11 here, so
it imports in process), takes the measure numbers each part carries in order,
and joins them against the system map's own `(page, system, bar-in-system)`
sequence per part. The map is used only for the TRUTH side, never to produce
the numbers being checked.

```
   per-part (committed)   numbers  111   AMBIGUOUS  30   parts the map could not align 0
        number 64   names p3/s1 bar 0, p4/s0 bar 0
        number 65   names p3/s1 bar 1, p4/s0 bar 1
        number 66   names p3/s1 bar 2, p4/s0 bar 2
   document (renumbered)  numbers  111   AMBIGUOUS   0   parts the map could not align 0
```

**30 ambiguous numbers → 0.** And the converse, which the count above cannot
see: **0 instants carry more than one number** under the new scheme.

---

## 6. THE IDENTICAL-MUSIC CONTROLS — all three can fail

**Text level** (`numbering_arm.py` §4):

| control | result |
|---|---|
| byte-identical outside the `number=` attribute | **True** |
| the two files DO differ with the attribute in (positive control) | **True** |
| re-applying the INCUMBENT scheme reproduces the committed file byte for byte | **True** |

That third one is what makes the first two mean something: it shows the
renumbering machinery is faithful, so the only thing separating the arms is the
scheme.

**Parse level** (`read_back.py` §1, music21): same 12 part ids, same 1,183
measures, **the same 1,986-event NOTE SEQUENCE per part** (pitch and
quarter-length, in order), and the measure NUMBERS parsed back do differ — the
positive control without which "the music is identical" would also be satisfied
by comparing a file with itself.

**Unit level** (`test_staged_measure_numbering.py::TestItWritesNoMusic`): the
same `parts` rendered by `_part_xml` under both schemes are byte-identical once
`number=` is blanked, the counters are identical, and the `assertNotEqual`
before it is the positive control.

⚠️ **If any of these had failed the job had left its scope** — that is what they
are for, not decoration.

---

## 7. MUTATION BATTERY — 10 arms, all red, positive control green

`probe/mutate_numbering.py`, run alone (never beside the A/B arm, which imports
the module it mutates).

`off_by_one` · `offsets_ignored` · `abstention_votes_zero` · `majority_wins` ·
`empty_system_is_zero_bars` · `collision_unguarded` ·
`collision_numbers_anyway` · `offset_never_advances` · `report_not_written` ·
`everything_refuses`

**0 survivors, 0 bad anchors**, with the unmutated tree GREEN first.
`everything_refuses` is the POSITIVE CONTROL in the same class — a battery of
refusal tests can pass by refusing everything, so an arm that makes the rule
never fire must fail the tests asserting a document IS numbered. It does.

⚠️⚠️ **AND THE FIRST RUN OF THAT BATTERY DESTROYED THE CHANGE IT HAD JUST
CERTIFIED.** The recorded recipe ends its battery by restoring the mutated file
from version control as a safety net. Against an UNCOMMITTED change that net is
the hazard: ten arms went red, the battery then restored the file from **HEAD**,
and HEAD did not have the function. The diff afterwards listed only the
benchmark script; the tests that had just passed were testing code no longer on
disk.

**The battery now restores byte-for-byte from the snapshot it took before the
first arm, and VERIFIES the restore**, exiting 3 if it does not match. The
generalisable form, one clause wider than CLAUDE.md's existing warning:

> **A mutation battery must leave the tree as it FOUND it — which is not the
> same as leaving it as VERSION CONTROL has it.**

The recorded hazard was *"a battery checks out the files it mutates, so an A/B
arm that reads the working tree is not isolated from it"*, which is about a
CONCURRENT reader. This is the same line harming the battery's own subject with
nothing else running. Cost here: the edits had to be re-applied. The cheap
prophylactic is the one taken second time round — **commit a checkpoint before
running a battery**, so the restore and the snapshot agree.

---

## 8. WHAT ELSE CHANGED

`benchmarks/omr-cleanup-count-2026-09/export_arm.py` builds the system map with
its own running count and **asserts the map against the emitted XML**
measure-for-measure. Left alone it would now name the wrong bars — the single
failure that map exists to prevent, since it sends a human to the wrong music —
so `system_map` calls the SHIPPED `_document_bar_offsets` rather than restating
it, and falls back to the per-part count only where the rule refused, which is
again exactly what the exporter does.

⚠️ **Its assertion is a real control and it was CHECKED IN BOTH DIRECTIONS**, on
a synthetic record carrying a tacet part (no staged record is committed, so this
is the only way to drive it here). With the change: the map and the file agree
on **7 of 7 `(part, measure)` pairs, 0 problems**. With the OLD per-part map
formula against the same document-numbered file: **4 problems** — `P2 m1`/`m2`
named by the map and absent from the file, `P2 m4`/`m5` in the file and claimed
by the map zero times. So the export_arm change was necessary and the control
that would have caught its absence is not vacuous.

---

## 9. WHAT IS **NOT** ESTABLISHED

* **n = 1 document, 1 publisher, 4 pages of ~16.** Litolff `984073` is the
  *low-res bitonal* scan this repo already calls the pessimistic end of the
  corpus.
* **No print was consulted.** This says a number now means one instant across
  parts; it says NOTHING about whether the bars under those numbers hold the
  right music. The graft `probe/partition.py` measured — 12 of 75 staff-systems
  filed under the wrong instrument — is untouched here and is repair (1) of the
  three, landed separately.
* **The three refusal branches are exercised only by synthetic records.** No
  real record in this repo has ever carried a system whose staves disagree, a
  system no staff read, or a part with two runs on one system; the first is
  plausible on worse ink, the third is reachable only through the slot join.
  The tests INJECT them, which is the honest statement of their status.
* **An export-only arm is structurally blind to a GATHER change** (§3), and
  **no end-to-end staged run was possible here** — no weights, no library.
* **No OMR-NED figure is claimed.** musicdiff pairs measures positionally
  within a part, so the metric is expected to be blind to a renumbering by
  construction — and an unmeasured expectation is not a measurement, which is
  why it is written here rather than as a result.
* **The three short parts are still short.** Padding the tacet spans is repair
  (3) and is deliberately NOT done here: padding first would make the numbers
  line up while the wrong notes stayed put, and it needs a bar length the meter
  does not supply on this document (decided on 1 system of 7).

---

## 10. RUN IT

```bash
python3 benchmarks/omr-measure-numbering-2026-09/probe/numbering_arm.py --check --write
python3 benchmarks/omr-measure-numbering-2026-09/probe/read_back.py --check
python3 benchmarks/omr-measure-numbering-2026-09/probe/mutate_numbering.py   # ALONE
python3 -m pytest tools/omr/tests/test_staged_measure_numbering.py -q
```
