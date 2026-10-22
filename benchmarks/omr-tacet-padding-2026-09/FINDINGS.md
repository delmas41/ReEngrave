# The tacet spans are PADDED — where the bar length is known, and refused where it is not

2026-09-15, no flag. Repair **(3)** of the three the *measure math* work put in
order, and the last of them. Its two predecessors landed first on purpose:

1. the join must stop guessing — **landed** (`ce7b8ba7`, slot index by name)
2. a measure is numbered by the DOCUMENT's bar sequence — **landed**
   (`9e2c695c`), and it *"writes no music and needs no meter"*
3. **the tacet spans must be PADDED** — this

⚠️⚠️ **THE ORDER IS LOAD-BEARING AND THIS JOB IS WHY.** CLAUDE.md: *"Padding
first would have hidden the graft — the numbers would line up and the wrong
notes would remain, which is worse, because a graft counted as a note error
ranks the work into the wrong module."* Going last is what makes it safe to
write bars nobody printed.

---

## 1. THE DEFECT

`_part_xml` walked the part's own `StaffRun`s. A printed orchestral score
SUPPRESSES a tacet staff, so a part absent from a system wrote nothing at all
for those bars and came out short. On the measured document — Litolff Beethoven
5 mvt 1, pdf pp.1-4, 7 printed systems, 12 parts — eight parts hold **111**
measures, `P9-P11` hold **93** (missing p3/s1's 18 bars) and **`P12` holds 16
and then simply stops**, the lineup having condensed at p.2.

Repair (2) made the surviving measures *named* consistently. It deliberately
wrote no music, so the parts are still of four different lengths and a reader
asking the score for a stretch of bars gets some parts and not others.

---

## 2. THE RULE, AND EXACTLY WHAT IT DOES WHEN THE BAR LENGTH IS UNKNOWN

`export._tacet_walk` + `export._pad_tacet_span`, called from `_part_xml`.

A part's systems are walked in **document order** rather than the part's own
run order; where the part has no run, that system's bars are written as
**full-measure rests**, numbered `offset + i + 1` from the same offsets repair
(2) computed. The meter is asked **per bar** (`meter_at`), not per system,
because a system can print a mid-system meter change.

⚠️⚠️ **WHERE THE METER IS UNKNOWN THE BAR IS NOT WRITTEN, AND IS COUNTED.**
A MusicXML rest must carry a `<duration>`, and `_measure_rest_beats(None)`
falls back to **4.0 quarters** — a whole rest, which on this 2/4 movement is
twice the bar. That is CLAUDE.md's governing rule violated in one line: *a
fallback must never convert "cannot tell" into a definite answer*. So:

| the system's meter | what the padded bar gets |
|---|---|
| **known** | `<rest measure="yes"/>` at the bar's own length, no `<type>` |
| **unknown** | **nothing** — no `<measure>` at all, `tacet_bars_not_padded_without_meter += 1` |
| the numbering REFUSED | nothing anywhere; `report["tacet_padding"]["refused"]` |

⚠️ **THE ASYMMETRY WITH THE EVENTLESS BRANCH IS THE ARGUMENT, and a test pins
it.** A bar of a PRESENT part that we read nothing in *has* to be written
somehow — the record says that staff has N bars — so the exporter takes the 4.0
fallback with `measure="yes"` withheld, which is the standing behaviour and what
`OMR_METER_CARRY` is for. **A tacet bar does not have to exist at all.** It is
ours to invent or not, so inventing one at a length nobody read buys alignment
with fiction. `test_the_refusal_INVENTS_NO_BAR_and_the_4_0_fallback_is_not_ours`
asserts both halves on one fixture.

⚠️ **AND IT IS NOT THE SAME COUNTER.** `empty_bars_padded` is *a bar the page
prints for this staff and we read nothing in*; `tacet_bars_padded` is *a bar the
page prints for this part not at all*. One is a reading gap, the other a join
fact, and the repairs differ — so they are reported apart and a test asserts
`empty_bars_padded` never absorbs a padded tacet bar.

**Three further design points, each with a test:**

* **`prev` is not touched by a padded bar.** A padded span states no clef and no
  key — this part is not printed here, so we have neither — so leaving the
  attribute state alone means the next REAL run emits exactly the attributes it
  emits today, and the file is byte-identical outside the inserted `<measure>`
  blocks. That control is worth more than a tidier attribute stream.
* **The one exception is `divisions`**, which is a fact about the FILE. A part
  tacet on the document's first system would otherwise open with a measure
  carrying no `<attributes>` at all, so a LEADING pad emits the divisions block
  and hands `first=False` on; `prev` still holds its sentinels, so the first
  real run writes its clef as usual.
* **No directions and no wedges** on a padded bar, unlike the eventless branch.
  Those come off THIS STAFF's cells and a tacet part has no staff here.

⚠️ **PADDING DEPENDS ON THE NUMBERING, structurally.** `_tacet_walk` returns the
part's own runs when `offsets is None`. A tacet span has to be written at a
definite place in the bar sequence, and when repair (2) REFUSED there is no such
sequence — padding anyway would convert *"cannot tell"* into a definite answer by
a second route. `report["tacet_padding"]["refused"]` says so, and
`tacet_bar_total` is **`null` rather than 0**: nothing was even looked at.

⚠️ `spans` and `meters` are both **derived from the one tally**
`_document_bar_offsets` already does — `numbering["systems"]` gained `page` /
`system_index` ints beside its display string — so a padded span and the number
written on it answer to the same arithmetic. Nothing is re-counted.

---

## 3. REACH — and ARM A is a clean, correct, completely INERT zero

`probe/padding_arm.py`, which prints reach before anything else and **exits
non-zero declaring itself DEAD** when no part is tacet anywhere.

```
   document        : benchmarks/omr-cleanup-count-2026-09/out/record-p1-p4.json
   record commit   : 9d4ccc85 (dirty=True)
   base file       : beethoven5-mvt1-p1-p4.document-numbered.musicxml
   parts 12   systems 7   measures in file 1183
   parts TACET on at least one system: 4 of 12
   TACET BARS the document holds     : 149   <-- the population
       P9    18 bars  (p3/s1)
       P10   18 bars  (p3/s1)
       P11   18 bars  (p3/s1)
       P12   95 bars  (p2/s0, p2/s1, p3/s0, p3/s1, p4/s0, p4/s1)
```

**The meter of each system, read off the file's own attribute stream** — derived,
not assumed, and all 12 parts agree on every system (see §5):

```
       p1/s0  2/4
       p2/s0  —  (no meter was read)     p3/s1  —
       p2/s1  —                          p4/s0  —
       p3/s0  —                          p4/s1  —
   systems with a meter: 1 of 7
   TACET BARS WHOSE LENGTH IS KNOWN  : 0 of 149   <-- ARM A's reach
```

⚠️⚠️ **SO ARM A PADS ZERO BARS AND REFUSES 149, AND THAT IS THE RULE WORKING.**
Every tacet bar on this document sits on a system whose meter was never read.
`P12`'s missing systems are 2-7; `P9-P11`'s is p3/s1; **`p1/s0`, the one system
with a meter, is the one system no part is tacet on.** The reach of *"pad only
where the length is known"* is exactly zero here, and the lever on that number
is the METER, not this rule.

---

## 4. ARM B — the counterfactual, and the A/B

⚠️ **A zero that means "the rule declined" and a zero that means "the instrument
is dead" must not read alike**, so the arm supplies the meter and measures what
padding is worth once it is settled. **It is labelled a counterfactual** — the
meter supplied is the **2/4 this file's own `p1/s0` READS**, and CLAUDE.md's
rest-sizing section records `OMR_METER_CARRY=1` deciding `carried` 2/4 on all six
abstaining systems of this exact document at support +6/+13/+9/+18/+9/+7. Nothing
here reads a meter off page 2.

| | ARM A (as the document stands) | ARM B (meter settled) |
|---|--:|--:|
| tacet bars padded | **0** | **149** |
| refused, no meter | **149** | 0 |
| the partition balances | **True** | **True** |
| measures in the file | 1183 | **1332** |

```
   part    before    after   numbers
   P1-P8      111      111   1..111 contiguous
   P9          93      111   1..111 contiguous
   P10         93      111   1..111 contiguous
   P11         93      111   1..111 contiguous
   P12         16      111   1..111 contiguous
```

`12 × 111 = 1332`, and every part now holds the same 111 measure numbers.

**WHAT IT BUYS, which is not the measure count.** music21 slices each part by its
own measure NUMBERS, so a part with a hole there comes back empty and a reader
cannot tell *silent* from *absent* — the ABSENT/DECLINED collapse, in the music:

```
   asking the SCORE for a stretch of bars — parts with a measure at all:
       bars   5-7   : 12 of 12  ->  12 of 12
       bars  70-72  :  8 of 12  ->  12 of 12
       bars 100-102 : 11 of 12  ->  12 of 12
```

---

## 5. THE CONTROLS — every one of them can fail, and one is the point

| control | result |
|---|---|
| **every existing measure byte-identical and in order** | **True** |
| the padded file DIFFERS from the base (positive control) | True |
| **deleting exactly the inserted blocks restores the base BYTE FOR BYTE** | **True** |
| a padded bar is a sized full-measure rest and nothing else (0 `<pitch>`, 149 `<rest>`, 149 `measure="yes"`) | True |
| after padding every part holds the SAME measure numbers | True (111) |
| **and before padding they did NOT** (positive control) | True (16 / 93 / 111) |
| music21: parts 12 → 12, measures 1183 → **1332** | — |
| **the NOTE SEQUENCE of every part is unchanged** | **True** |
| (positive control: it holds 1151 note events, not zero) | True |

The third is the strong form of the first: the padded file with exactly the
inserted blocks deleted is the base file, byte for byte. That is what `prev`
being left alone buys.

⚠️ **The per-system meter is RECONSTRUCTED and the reconstruction is checked.**
`_part_xml` writes an `<attributes>` block at a bar whose clef, key or meter
CHANGED, and a `<time>` appears in it iff the meter is not None — so walking each
part's measures and updating a running meter at every attributes block recovers
exactly what `Q.METER` held. **All 12 parts are walked and must AGREE per
system** (`Q.METER` is system-scoped, so a disagreement would mean the
reconstruction is wrong); the arm exits 2 if they ever disagree. They do not.

⚠️ The arm also re-checks repair (2)'s own fidelity condition — every system's
map entries account for every staff the export's `staves_per_system` provenance
records — and refuses to score otherwise.

---

## 6. MUTATION BATTERY — 12 arms, all red, 0 survivors, 0 bad anchors

`probe/mutate_padding.py`, run ALONE, against
`test_staged_tacet_padding.py` + `test_staged_measure_numbering.py`.

`pads_without_a_meter` · `meter_per_system_not_per_bar` · `off_by_one_number` ·
`walk_ignores_spans` · `report_not_written` · `counters_not_preinitialised` ·
`empty_bars_absorbs_it` · `rest_not_sized_to_the_bar` · `pad_states_a_clef` ·
`refusal_reports_a_zero` · `system_key_swapped` · **`everything_refuses`**

`everything_refuses` is the POSITIVE CONTROL in the same class — *a battery of
refusal tests can pass by refusing everything*, so an arm that makes the rule
never fire must fail the tests asserting a document IS padded. It does.

⚠️ **The battery takes a BYTE snapshot before the first arm, restores from it,
and VERIFIES the restore**, exiting 3 if it does not match — the hazard repair
(2) paid for, where a battery restored its subject from `HEAD` and destroyed the
change it had just certified. **A checkpoint commit was made before running it**
so the snapshot and version control agree.

---

## 7. WHAT IS **NOT** ESTABLISHED

* **The 149 bars were never written on this document.** ARM A is a zero. Every
  number in §4 is the COUNTERFACTUAL arm.
* **n = 1 document, 1 publisher, 4 pages of ~16.** Litolff `984073` is the
  *low-res bitonal* scan this repo already calls the pessimistic end of the
  corpus.
* **No print was consulted.** This says the parts now agree about how many bars
  there are and that the instrument is silent where the plate suppresses its
  staff; it says NOTHING about whether the bars around them hold the right music.
* ⚠️⚠️ **THE ARM PADS THE JOIN IT IS GIVEN, AND THAT JOIN IS STALE.** The
  committed record was gathered **before** `adjudicate_slot_index`'s short-system
  rule landed, so its 12-part join still carries the 12-of-75 graft repair (1)
  measured. On the current tree a fresh gather of this document would place 50
  slots and abstain on 25, `_slots_are_ordinals` would be False, and the join —
  and therefore the tacet population — **would differ in a way no cloud session
  can determine**. The rule under test is the shipped one; its input is not
  current. *A re-gather is the only instrument that can say.*
* **An export-only arm is structurally blind to a GATHER change**, and no
  end-to-end staged run was possible here: **no weights, no library, no committed
  record.** The unit suite drives `to_musicxml` end to end on synthetic records
  for exactly that reason; the two instruments have opposite blind spots.
* **No OMR-NED figure is claimed.** There is no committed reference for these
  pages, and musicdiff pairs measures positionally within a part, so its response
  to 149 inserted measure rests is unmeasured rather than expected-to-be-zero.
* **`OMR_METER_CARRY` was not flipped** and must not be — that default is Sean's.
  ARM B is evidence about what the flip is worth on the padding side and is not
  a recommendation of its own.

---

## 8. THE RANKED NEXT WORK

**The meter, and nothing else.** This rule is correct and reaches zero bars on
the only document available, for exactly one reason: the meter is decided on
**1 system of 7**. The same lever is already recorded twice — the rest-sizing
work measured `OMR_METER_CARRY=1` taking bars-that-add-up **38.0% → 69.2%** and
`empty_bars_padded_without_meter` **168 → 0** on this same record — so the flip
would light up three repairs at once. Its standing blocking objection is
unchanged and this document cannot touch it; the named next arm is still
**Breitkopf Brahms 1 p0-3**, whose meter reading is known bad.

Until then this change is **inert by design and loud about it**:
`report["tacet_padding"]` names the 149 bars it declined and why.

---

## 9. RUN IT

```bash
python3 benchmarks/omr-tacet-padding-2026-09/probe/padding_arm.py --check --write
python3 benchmarks/omr-tacet-padding-2026-09/probe/mutate_padding.py   # ALONE
python3 -m pytest tools/omr/tests/test_staged_tacet_padding.py -q
```
