# The unnamed block at the foot of a system — placed, and the split is the point

2026-09-17. `adjudicate_slot_index` gains a branch; `inferences` gains the
stage's **third rule and its first non-duration target**. No flag.

Sean, on a plate that labels its strings on the opening system and nowhere
else: *"If we had 4 or 5 staves that showed up last in the system without a
name in the margin they are almost surely strings. If the first 2 clefs are
treble the 3rd is alto and the 4th is bass clef it is further reinforcement."*

That rule was **measured on 2026-09-17** (`benchmarks/omr-unnamed-staves-2026-09`)
and deliberately **not shipped**. This ships it, and splits it where the page
stops forcing the answer.

---

## 1. The headline

| | Litolff Beethoven 5, pp.1-4 |
|---|---|
| CONTROL — branch disabled | **75 of 75** committed slot verdicts reproduced exactly |
| OFF | 25 staves `abstained / unnamed_in_short_system` |
| ON (ADJUDICATE only) | **5 DECIDED** `family_block`, **20 NARROWED** |
| + INFER | **15 collapsed**, 5 left narrowed |
| against the hand-read PRINT | **25 of 25 placements correct, ZERO grafts** |
| in the FILE | pitched `<note>` **965 → 1527 (+562)**, `staff_not_identified` **783 → 141 (−642)** |

⚠️ **THE 5 LEFT NARROWED ARE THE CONDENSED `Violoncello e Basso`** — one
printed staff carrying two reference parts. They are abstained on, not picked,
which is the same answer the probe reached and the right one: placing that
staff on either slot alone is a claim the page does not make.

⚠️⚠️ **THE EXPORT DELTA IS ATTRIBUTABLE TO THE UNIT: ONE DROP BUCKET MOVES
AND NOTHING ELSE DOES.** Over the four pages, with this rule running ALONE:

| bucket | off | this rule | delta |
|---|--:|--:|--:|
| `staff_not_identified` | 783 | 141 | **−642** |
| `duration_narrowed` | 335 | 335 | 0 |
| `no_pitch` | 205 | 205 | 0 |
| `owned_by_another_staff` | 173 | 173 | 0 |
| `ink_is_a_whole_rest` | 25 | 25 | 0 |
| **`events_written`** | 1472 | 2114 | **+642** |

`events_in_log` is 2,993 in every arm and the accounting control is an
EQUALITY (`balanced: True`) in every arm, so the 642 released events are the
642 written: nothing appeared and nothing went missing.

⚠️ Per part, music21 reading the file back: **Violin I +189, Violin II +176,
Viola +74, Contrabass +27**. The music went to the instrument it belongs to.
⚠️ **Cello gains NOTHING**, which is the result agreeing with itself: its
staves are the condensed `Violoncello e Basso` this rule deliberately leaves
narrowed, and the one `Violoncello` it does place (p4/s0) carries no notes we
read.

⚠️⚠️ **AND THE FIRST VERSION OF THIS TABLE WAS CONFOUNDED.** `infer.run` fires
EVERY registered rule, so an `off -> infer` delta mixed this rule with
`collapse_duration_by_column` and `collapse_duration_to_barline`. Those two
collapse 16 narrowed durations and put **13 more events in the file, on WIND
staves this rule never touches** — `duration_narrowed` −15, then +2 of those
refused by the ownership contest they could suddenly reach. **The tell was
four wind parts gaining notes in a change about strings**, not a failing
assertion. The arm now runs this rule alone and the two duration rules are
reported apart: with all three, pitched notes reach 1,540 rather than 1,527,
and **those 13 are not this rule's.**

⚠️ **PARTS STAY AT 12 AND MEASURES AT 1,332.** The placed staves join the
parts the opening system already established; nothing new is invented. That is
a stronger result than a part count moving — the music went to the instrument
it belongs to, not into a new part of its own.

---

## 2. What is FORCED and what is BEST — the whole design

The rule has two halves and they are not the same kind of claim, so they are
not in the same stage.

**FORCED (ADJUDICATE).** The reference's trailing run of same-family slots is
five long. A bottom-contiguous unnamed block of five has exactly one
order-preserving map onto it. Nothing is guessed; `Ruling` DECIDES, reason
`family_block`. Reach on this document: **p4/s0, five staves**.

**BEST (INFER).** A block of FOUR sits on five slots five ways, and position
alone cannot choose. ADJUDICATE NARROWS — *"it is one of these"* — and the
convention that finishes it (*a short string section is short at its FOOT,
because the bottom pair is condensed*) is a claim about engraving practice
rather than about this page. It is labelled, it supersedes visibly, and the
narrowing stays in the log underneath it. Reach: **15 staves on five systems**.

⚠️⚠️ **THIS IS THE COROLLARY OF THE 2026-09-17 GOVERNING FINDING, BUILT.** *A
brake whose reason was "no stage may do this", where a stage now exists, is
not a brake to remove — it is a HANDOFF THAT MAY NOT BE WIRED.* The blanket
abstention here was written when the only options were ANSWER or DISCARD.
Two of the six capabilities that finding names are exactly what dissolve it:
a PARTIAL answer has somewhere to live, and a FOURTH STAGE exists for
best-rather-than-forced.

⚠️ It is also the second target quantity INFER has ever had.
`staged/brakes.py` measured **1 of 28 decisions able to hand work to the
stage**; this is the second, and it came from the largest population a human
had actually looked at.

---

## 3. Three claims that are NOT in this rule, and were in the probe

**No word list.** The probe found the string slots with a tuple of spellings
(`Violino`, `Viola`, …). Here the run is *the reference's trailing run of
slots whose instrument verdict names ONE family* — derived, and it names no
instrument and no publisher. ⚠️ A family test over the PRINTED names would
have been wrong anyway: the lexicon reads a bare `Basso` as a **BASS VOICE**,
so the bottom slot would have dropped out of the run and the whole block would
have slid. (On the real record slot 11 reads `Contrabass`, because the roster
layer already repairs that — the fixture in the unit tests uses
`Contrabasso` so it cannot depend on the bug in either direction.)

**No clef in ADJUDICATE.** `adjudicate_clef` weights the instrument at 1.0 in
the other direction and is ORDER 9 against `slot_index`'s 6, so reading
`Q.CLEF` would close a cycle *and* read `None`. Asserted behaviourally:
contradicting **every** glyph in the block changes nothing about the
adjudicator's answer.

**No "4 or 5" constant.** `FAMILY_BLOCK_MAX_DEFICIT = 1` is the structure that
produces Sean's window: on a five-slot run, a deficit of at most one admits
exactly a block of four or five. Written as a deficit it carries to a plate
whose string run is a different length, and it says why the window is where it
is. ⚠️ It is also what refuses a block of 1-2 — the case the probe records as
**untested, because this plate never prints one**.

---

## 4. The clef is a TERM that can pull into abstention, never a gate

Sean's *"further reinforcement"*, built as INFER's witness and honest about
what it can see.

* It is consulted to **CONTRADICT**, never to choose. A block with no clef
  readings at all is inferred exactly as before — silence is not
  contradiction.
* The refusal is **whole-block**. One member's clef disagreeing means the
  alignment is shifted, and the staves above it are wrong too; refusing only
  the contradicting member would keep the errors the contradiction is evidence
  for.
* ⚠️⚠️ **IT IS HALF-BLIND ON THE ONLY DOCUMENT IT IS MEASURED ON.** The record
  holds **74 `clefG`, 17 `clefF` and ZERO C clefs** — and the tree's own
  `_GLYPH_TO_CLEF` maps `clefC` to nothing by design. So the ALTO clef, the
  one clef that uniquely names a member of a string block, never speaks. What
  the BASS clef still catches is a block shifted by one, which is the failure
  the term is here for, and that direction is tested only in a fixture.
* The witnesses are the block's own `Q.CLEF_GLYPH` **observations**, so
  `independent_groups` returns one group per staff — separate detections of
  separate ink. ⚠️ They corroborate the ALIGNMENT, which is ONE claim; they do
  not independently establish each staff's slot, and the rule's
  `why_witnesses_are_independent` says so in those words.

---

## 5. ⚠️⚠️ THE SECOND PUBLISHER HAS NO POPULATION AT ALL — reach ZERO, and that is not a failure

Breitkopf Brahms 1, pp.0-3, same arm, control **97 of 97**:

| slot reason | staves |
|---|--:|
| `named` | 78 |
| `paired_by_name` | 13 |
| `full_lineup` | 6 |
| **abstained** | **0** |

(78 + 13 + 6 = 97.)

**That plate labels nearly every staff on every system**, so `slot_index`
never abstains and this rule has nothing to do. The domain is a property of a
publisher's LABELLING PRACTICE, not of the rule — so the second publisher
cannot corroborate it and cannot refute it either. **n = 1 document for
correctness.**

⚠️ Six Brahms staves take `full_lineup` — unnamed staves on a system that is
the reference's own size, decided positionally by the pre-existing branch.
This rule does not reach them and should not: where the system prints the full
lineup, position IS the answer.

---

## 6. Two instrument defects, both found by the instrument disagreeing with itself

⚠️⚠️ **THE ARM SCORED A BRAHMS RECORD AGAINST LITOLFF'S PRINT TRUTH AND
REPORTED 21 GRAFTS.** `printed-lineups.json` is keyed on `(page, system)` and
so is every other record, so the join was an **id-space collision** — the same
shape as the `--work-id` collision the scan gate already pays for, where two
scans of one plate land on the same `pdf_page_index`. Fixed by making scoring
**opt-in per record** (`--truth`): an arm with no truth file reports REACH and
refuses to classify a single placement. The 21 grafts were the instrument's.

⚠️ **THE EXPORT ARM READ A REPORT KEY THAT DOES NOT EXIST** and printed
`None` for `held_out_staves`, `join_used` and `balanced` — the report carries
`part_join`, not `provenance`. A `.get` on the wrong key is the quietest way
to measure nothing, and `None` renders beside real integers as a zero: the
first table said *no staff is held out* on a run holding twenty-five out. The
arm now names each field it could not read, on stderr, before any number is
read.

⚠️ **THE FIRST VERSION OF THE RULE REACHED NOTHING, AND THE CAUSE IS THIS
REPO'S OWN FAILURE FAMILY IN A LOCAL VARIABLE.** `_names_by_system` grows its
row only when it has a NAME to put in one, so a system of eleven staves whose
last four are unnamed hands back a list of **seven** — and a list that ends
early is indistinguishable from a system that ends early. The unnamed suffix
this rule is entirely about is exactly the part the structure could not
represent: the ABSENT/DECLINED collapse `record.py` exists to prevent,
happening between two functions of one module. The system's own
`Q.SYSTEM_STAFF_COUNT` is the only thing that says how long the row really is.

---

## 7. What is NOT established

* **n = 1 document, 1 publisher, 4 pages of ~16**, on the low-res bitonal
  Litolff `984073` this file's own CLAUDE.md calls the pessimistic end of the
  corpus. The second publisher has no population (§5).
* **The 562 notes are in the right PART; whether they are the right NOTES is
  not measured here.** Slot correctness is scored against the print; pitch,
  duration and placement are not, and on a cleanup count they are what a human
  would actually be reading.
* **No OMR-NED figure is claimed**, deliberately: the metric is symmetric and
  rewards under-prediction, so it would pay for holding this music OUT.
* **`part_partition` is held at the committed value** in every arm, so this
  says nothing about a run where a fuller slot table changes which join the
  exporter picks.
* **The deficit cap's real job is untested on a page.** A block of 1-2 staves
  is refused in a fixture and this plate never prints one.
* **The clef's refusal direction is untested on a page** — no real block here
  contradicts, because no real block here is shifted.
* An ADJUDICATE/INFER arm over a FIXED gather is **structurally blind to a
  GATHER change**; nothing here is evidence about one.

## 8. Reproduce

```bash
python3 benchmarks/omr-unnamed-block-slot-2026-09/block_arm.py \
    library/_shared-records/beethoven5-p1-p4-ink-identity.record.json \
    --truth benchmarks/omr-part-join-phase2-2026-09/printed-lineups.json
python3 benchmarks/omr-unnamed-block-slot-2026-09/export_arm.py \
    library/_shared-records/beethoven5-p1-p4-ink-identity.record.json
python3 -m pytest tools/omr/tests/test_staged_unnamed_block.py -q
```
