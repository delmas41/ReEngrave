# Instrument identification — REACH per channel, before any accuracy claim

**2026-09-22. No code under `tools/` changed** (`git diff -- tools/` is empty).
This measures what each of Sean's four channels is worth on the staves the
shipped reader says nothing about, in the order he ruled on 2026-09-22:

> *"margin names, instrumentation lists from the doc or a dossier, Order,
> family brackets should all come first in determining what the instrument is"*
> — and the clef only where we are SURE of it, because *"the clef is a small
> part of deciding what the instrument is and we would need to be sure of the
> clef to have it impact the instrument."*

Two shared records, both scans, both `OMR_INK` gathers:

| | staves | instrument DECIDED | ABSTAINED |
|---|--:|--:|--:|
| Litolff Beethoven 5 pp.1-4 (`ea80ae59`) | 75 | 50 | **25** |
| Breitkopf Brahms 1 pp.0-3 (`4df63a75`) | 97 | 57 | **40** |

---

## 0. ASK FIRST — the conventions, and what each predicts

Put to Sean before any code was written; his answers are in §0d.

**a. ORDER** (`[C62]`). A human reads down the system and knows a printed score
may OMIT a tacet part and may never REORDER one, so the staff between a named
Clarinetti and a named Corni can only be something the lineup prints between
them. *Predicts:* every unnamed staff's slot is bounded by its named
neighbours above and below.

**b. THE FAMILY BLOCK** (`[C58]`). A human sees where the interior barlines
break and knows that is a section boundary. ⚠️ This is NOT the printed bracket
(`[C59]`/`[C60]`: Litolff prints ONE bracket round the whole orchestra) —
`Q.STAFF_GROUP` reads `Q.BRACKET_BLOCK`, which is where the barlines STOP.
*Predicts:* the string block's first AND last staff are known without reading a
name. **Checked before it was used: on 7 of 7 Litolff systems the block
structure reproduces the printed family structure exactly, suppressions
included** — `4|3|5` on the full system, `3|1|4` on the 8-stave system that
drops Oboi/Trombe/Timpani, `4|2|5` where the Timpani goes and the bottom staff
splits.

**c. THE CLEF.** A human glances at the head of the system: two trebles, a C
clef on the third line, then bass. *Predicts:* the clef separates the block's
boundaries. ⚠️ It cannot separate Violino I from Violino II — both treble.

**d. SEAN'S ANSWERS, 2026-09-22.** *"The c clef is on the third line - alto for
viola."* *"Upper is always 1"* — so order alone distinguishes the two violins
and the clef's only job inside the block is finding boundaries. And *"string
family always includes all 5 instruments - if there are only 4 lines then the
bass is doubling the celli or it comes in later"* — which says the residue in
§3 is a CONDENSATION, not an ambiguity.

---

## 1. THE RESULT

Every arm is a CONSTRAINT on the order-preserving map, never a score. A staff
takes a slot only where EVERY surviving assignment agrees. **A channel may
narrow or abstain; where it makes a system unsatisfiable it is DROPPED for that
system and the refusal is counted** — Sean's *evidence contributes, it never
gates*, made mechanical.

| arm | Litolff forced /25 | GRAFTS | Breitkopf forced /40 | clef channel REFUSED |
|---|--:|--:|--:|--:|
| **order alone** | **0** | 0 | **38** | — |
| **+ family block** | **5** | 0 | 38 | — |
| + clef, the reference's own reading, all staves | 16 | 0 | 38 | 1 / **5 systems** |
| + clef, the reference's own reading, unnamed only | 18 | 0 | 38 | 0 / **5 systems** |
| + clef, treble-or-not | 15 | 0 | 38 | 0 / 0 |
| **+ clef, the INSTRUMENT's admissible clefs** | **18** | **0** | **38** | **0 / 0** |
| *order + clef, no block* — the prior art's shape | 16 | 0 | 38 | 0 / 5 systems |

**ZERO GRAFTS in every arm on both documents.** That is the bar
(`benchmarks/omr-slot-index-2026-09`: placing unnamed staves BY POSITION scores
*more* correct, 66 against 50, and grafts 9 doing it).

### 1a. ⚠️⚠️ ORDER ALONE FORCES NOTHING ON THE DOCUMENT THAT NEEDS IT

**0 of 25.** The channel the plan leans on hardest is worth nothing by itself
here, and the reason is structural rather than bad luck: Litolff's unnamed
staves are a TRAILING block, so there is no named neighbour below them and the
whole block slides — `[7,8]`, `[8,9]`, `[9,10]`, `[10,11]` on every system.

**And Breitkopf inverts it: order alone forces 38 of 40**, because that plate's
systems mostly print the full lineup and its unnamed staves are interleaved
among named ones, bounded on both sides. **Neither document could have shown
this on its own.**

### 1b. THE FAMILY BLOCK IS WHAT UNBLOCKS ORDER, AND IT IS WORTH 5

0 → 5 on Litolff. Those 5 are p4/s0, the one system whose string block is 5
staves for 5 slots, so the block's first slot is pinned and counting does the
rest. It reproduces the shipped `family_block` branch's own 5 decided exactly,
from a different instrument.

### 1c. ⚠️⚠️ "THE SLOT'S CLEF IS WHAT THE REFERENCE READ" IS REFUTED

`probe_clef_stability.py`, over staves the SHIPPED reader already placed:

| | agree | DISAGREE | one side silent |
|---|--:|--:|--:|
| Litolff | 37 | **1** | 0 |
| Breitkopf | 70 | **4** | 2 |

**Every slot's clef is constant across the document except the Cello and the
Bassoon** — the two instruments whose parts alternate bass and tenor as a
matter of course. Breitkopf's reference reads its cello slot **`tenor`** and
three later systems read the same slot **`bass`, all four at margin 4.5**. So
the reference's own reading is not a property of the slot, and using it as one
**makes 5 of Breitkopf's 6 systems unsatisfiable and the clef channel is
discarded on every one of them.**

The form that survives both plates takes each slot's admissible clefs from the
**instrument's own lexicon entry** (`Instrument.default_clef`, already on the
verdict this rule reads), widened for the four instruments measured to
alternate. It reaches the full 18 on Litolff and is **refused on no system of
either document**.

### 1d. THE CLEF IS WORTH 3 STAVES, AND ALL 3 ARE VIOLAS

18 with the clef against 15 with treble-or-not. The three are exactly the
staves whose C clef was read — Sean's *"if the first 2 clefs are treble the 3rd
is alto"*, priced. On Breitkopf the clef is worth **zero**, because order has
already forced 38 of 40 there.

### 1e. ⚠️ A CLEF READING ON A NAMED STAFF CAN ONLY SUBTRACT

A named staff is already pinned by its name, so a clef constraint on it adds
nothing — and on Litolff p2/s1 the Fagotti's FALSE `tenor` (the CV locator
firing unopposed at margin exactly `MARGIN_FLOOR`) names a clef **no reference
slot reads**, the system goes unsatisfiable, and the whole clef channel is
dropped for it: **four forced staves lost to one wrong reading on a staff the
clef was never needed for.** Either safeguard alone recovers them —
restricting the clef to UNNAMED staves, or the corroboration bar
(`CLEF_CORROBORATED_MARGIN = 2.0`, which excludes exactly the two margin-1.0
readings on this document). Both are cheap and both are recommended.

---

## 2. ⚠️⚠️ PLACEMENT REACH IS NOT NAMING REACH, AND BREITKOPF IS WHERE IT SHOWS

A staff can be placed perfectly and still have no name, because the reference
slot itself was never named.

| | forced | of those, the reference NAMES |
|---|--:|--:|
| Litolff | 18 | **18** (Violin ×12, Viola ×4, Cello, Contrabass) |
| Breitkopf | 38 | **28** |

**Ten Breitkopf staves are placed onto slots 0, 5 and 13, which the reader
itself could not name** — the Flöten, the horn staff whose label truncates to
`'(C)'` / `'(Es)'` (the fault the fact-sheet lane found on this same document),
and the Kontrabass.

**That is the population the instrumentation list exists for, and it is the
first measured one.** ⚠️ It can reach two of the three: both catalog rosters
name **no string instrument at all** — Beethoven 5 holds
`Bassoon, Clarinet, Contrabassoon, Flute, Horn, Oboe, Piccolo, Timpani,
Trombone, Trumpet` and Brahms 1 the same without Piccolo, with `string` present
only in the FAMILIES list — both marked `complete: true`. So the roster can
name a Flöten or a Horn slot and can never name a Kontrabass one.

⚠️ **The roster's naming reach on the abstaining population is ZERO today and
would stay zero if merely made reachable**: `work_roster.decide`'s recovery
tier needs a label TEXT to recover from, and these staves have none. Its
contribution is the FAMILY, which is what `[C58]`'s block already supplies from
ink.

---

## 3. THE RESIDUE IS A CONDENSATION, NOT AN AMBIGUITY

Litolff, best arm: **7 ambiguous of 25 — 5 `Violoncello e Basso` and 2 Viola.**

The five are one shape, and Sean named it before he saw the number: *"string
family always includes all 5 instruments - if there are only 4 lines then the
bass is doubling the celli or it comes in later."* Those staves come out
`[10, 11]` — Cello **and** Contrabass — and that is not a choice between two
slots, it is **one staff carrying two parts**, which the slot model cannot
express. Choosing either would be right about the music and wrong about the
part count.

The two Violas are the staves whose C clef nothing read (`no_candidates`), and
they are the clef reader's gap rather than this rule's.

Breitkopf: **2 ambiguous of 40**, both on reference slots the page never names.

---

## 4. CONTROLS

- **The named staves reproduce the shipped reader exactly.** On every arm and
  both records, the order channel's answer for a staff the record already
  placed agrees with `Q.SLOT_INDEX`: **Litolff 38 of 38, Breitkopf 54 of 54, 0
  differ.** The rule is not a new pairing; it is the shipped one with more
  constraints.
- **The prior art is reproduced.** `benchmarks/omr-unnamed-staves-2026-09/
  probe_forced_by_clef.py` published **16 forced, 16 ok, 0 grafts** on Litolff;
  the arm here with the same channels (order + clef, unnamed only, no block)
  reads **16 / 16 / 0** — from a different table builder and a different
  extraction.
- **The rule never sees the print.** The reference lineup is the document's
  own widest system with the pipeline's own `Q.INSTRUMENT` names;
  `printed-lineups.json` is joined on the slot index afterwards, for scoring
  alone. Scoring is opt-in per record because that file is **LITOLFF ONLY**.
- **Mutation battery: 8 RED, 0 survived, 4 dormant-by-design, 0 bad anchors,
  restore hash-verified.** Byte snapshot, in-flight sentinel,
  `PYTHONDONTWRITEBYTECODE=1`, and a judge that is the parsed JSON rather than
  any output text.

### 4a. ⚠️ TWO DEFECTS THE INSTRUMENTS FOUND IN THEMSELVES

**The order channel emptied the solution set, which is the one thing this probe
exists to forbid.** A reference slot the reader could not name excluded every
named staff instead of admitting them, and Breitkopf — whose reference has
THREE unreadable slots — reported `NO SOLUTION` on a real system. Caught by the
probe's own no-solution counter, not by review. `None` on the reference side
means *we do not know what this slot is*, and it excludes nobody.

**The battery could not see the headline claim.** Whether a channel
CONTRIBUTED or was REFUSED and order did all the work is invisible in the
forced/ambiguous counts — an arm that silently lost its clef channel scored
identically to one that used it. Adding `systems_channel_dropped` to the
recorded output turned two survivors RED (8 RED / 0 survived, from 6 / 1).

### 4b. THE FOUR DORMANT ARMS, NAMED

Each mutates a branch unreachable on BOTH documents; an arm that can never go
red trains the next reader to skim the list.

1. the block-count equality guard — every system of both documents prints the
   same number of family blocks as its reference (Litolff 3, Breitkopf 2);
2. `ALTERNATING_CLEFS` — Breitkopf is saturated by order alone, and Litolff's
   cello-slot staves stay ambiguous either way. **Its evidence is
   `probe_clef_stability.py`, not this battery**;
3. widest-system reference — on both documents the first system IS the widest;
4. the condensation test in `classify` — **no forced staff on either document
   is a condensed one**, so that branch is never reached.

---

## 5. ⚠️⚠️ THE TWO BREITKOPF RECORDS DISAGREE ABOUT 34 STAVES

The brief states Breitkopf as *"91 of 97 named, 6 abstaining"*. That is
`brahms1-breitkopf-p0-p3.record.json`, checked here and exactly right:
**91 `decided/label`, 6 `abstained/not_in_lexicon`.**

The INK record used throughout this measurement reads **56 `decided/label` + 1
`decided/roster`, 19 `not_in_lexicon`, 19 `no_evidence`, 1 vetoed.** Its margin
labels come from **Tesseract (77 rows) with 19 staves abstaining under
`text_layer`** — i.e. that gather ran without the rung the older one had.

So *"Breitkopf labels nearly every staff"* is true of one record and not the
other, and **the second publisher has a 40-staff population here only because
its label reader was weaker.** This repo's own lesson, arriving again: *a
shared record is a snapshot of the reader that made it.* Both figures are
reported; neither is corrected, because which gather is right is a question
about the reader and not about these channels.

---

## 6. WHAT THIS DOES AND DOES NOT ESTABLISH

**Does:** the reach of each channel, on two publishers, with the print as the
score on one; that the order of Sean's channels is measurable and that the
first two are worth 0 and 5 on the document that needs them and 38 and 0 on the
other; that a graft-free forced rule reaches 18 of 25 and 38 of 40; and that
the reference-clef premise is refuted while the instrument-clef premise
survives both plates.

**Does NOT:**

- **Nothing is wired.** No `tools/` file changed, no verdict moved, no file was
  exported. This is reach and a scored placement, not a shipped reader.
- **No accuracy figure for Breitkopf.** `printed-lineups.json` is Litolff only;
  the 38 forced there are **unscored**, and an arm that scored a Brahms record
  against that file once reported 21 grafts that were its own.
- **No naming has been checked against a print on either document.** §2's
  "the reference NAMES 18" is the reference's own reading, not the plate.
- **The condensed staff is unsolved**, and §3 argues it is not this rule's to
  solve.
- **n = 2 documents, 2 publishers, 8 pages, BOTH SCANS.** The engraved family
  is untouched.
- **No OMR-NED, deliberately** — musicdiff does not score `<part-name>`.
- The Litolff record predates the 2026-09-21 C-clef gather fix, so its **zero
  `clefC` detections understate what a fresh gather would give the clef
  channel** — which can only raise the 18, never lower it.

---

## 7. RANKED NEXT WORK

1. **Wire order + family block + the instrument-clef constraint into
   `adjudicate_slot_index`**, as a narrowing that decides only what is FORCED.
   It converts 13 of the shipped path's INFERENCES into entailments (the
   shipped path forces 5 in ADJUDICATE and collapses 15 more in INFER); the
   count barely moves, the **provenance** does.
2. **Let the roster name a reference SLOT**, not a staff — §2's 10 Breitkopf
   staves are placed and nameless, and two of the three slots are in the
   roster. This is the instrumentation list's first measured population.
3. **The condensed `Violoncello e Basso`** needs a representation before it
   needs a rule (§3).
4. **The C clef**: 4 of 7 Litolff violas are read, by the CV locator alone, and
   the detector fires on zero. Re-gathering on a post-2026-09-21 tree is the
   cheapest thing that would move §1d.

```bash
python3 extract.py litolff breitkopf     # ~2 min; caches out/slice-*.json
python3 probe_reach.py litolff           # the arms
python3 probe_clef_stability.py litolff  # the clef premise
python3 mutate.py                        # 8 RED, 0 survived
```

---

# ADDENDUM, same day — IT IS WIRED

Sean, 2026-09-22: *"wire it all up."* `OMR_SLOT_CONSTRAINTS`, **default ON**,
deny-list OFF test. `adjudicate_slot_index` now enumerates the order-preserving
maps under the three channels and takes a slot only where every surviving map
agrees.

## 8. WHAT IT DOES TO THE RECORD

One gather decided four ways on ONE tree (`slot_arm.py`). **CONTROL: 75 of 75
committed `slot_index` verdicts reproduced with both branches off.**

| | decided | narrowed | GRAFTS |
|---|--:|--:|--:|
| base (shipped ADJUDICATE) | 10 | 20 | 0 |
| base + INFER | **25** | 5 | 0 |
| **arm** (ADJUDICATE) | **23** | 7 | 0 |
| **arm + INFER** | **25** | 5 | **0** |

**The placements are IDENTICAL to the shipped path and 0 staves moved.** What
changes is the provenance:

| reason | base + INFER | arm + INFER |
|---|--:|--:|
| `forced_by_constraints` (ADJUDICATE, entailed) | 0 | **13** |
| `family_block` (ADJUDICATE) | 5 | 5 |
| `the_short_block_is_condensed_at_its_foot` (INFER, assumed) | **15** | **2** |
| still narrowed (the condensed `Violoncello e Basso`) | 5 | 5 |

⚠️ **THE COUNT DOES NOT MOVE AND MUST NOT BE QUOTED AS A GAIN.** Thirteen
placements stop being a convention applied in INFER and become an entailment of
the page, labelled as such and with the channels that forced them on the
verdict. That is the whole result on this document.

**Breitkopf** (unscored — `printed-lineups.json` is LITOLFF ONLY): **0 staves
moved, 3 gained**, all `forced_by_constraints`; 93 decided, 4 abstaining.

## 9. ⚠️⚠️ THE FIRST CUT WAS ADDITIVE AND STILL SUBTRACTED, THROUGH A RULE DOWNSTREAM OF IT

It decided directly instead of filtering. Deciding two members of a block
removed them from `inferences._block_members`, which requires the block's
narrowings to cover `0..k-1` — the block then had holes, INFER skipped it
whole, and **two Violas the shipped path places correctly came out narrowed**.

Every aggregate looked fine. Only the **per-staff** assertion *no staff the
base DECIDED may come out differently* caught it, and it is the one number in
`slot_arm.py` that is not a tally.

Two repairs, and the second is the general one:

1. the branch **filters** `_place_in_family_block`'s narrowing instead of
   replacing it, so the reason, the detail and the block all survive;
2. `_block_members` admits a member the page **FORCED** — *a member the page
   already settled is not a hole in the block.* It is admitted so the block
   RECONSTRUCTS and is never proposed for, because `infer.INFERABLE` is
   `{NARROWED, ABSTAINED}` and the stage cannot overturn a decided verdict
   whatever this returns.

## 10. WHAT THE FILE SAYS — and the symptom that is NOT there

`name_arm.py`, every arm: **12 parts, 12 NAMED, 0 falling back to a
coordinate.** `export.to_musicxml` takes a part's name from the first staff of
that part carrying one, and the opening system names all twelve — so a staff
the slot join places inherits the name whether or not its own instrument was
read.

⚠️⚠️ **So `export._default_name`'s `Staff p1-s0-3` does NOT appear on this
record**, and the symptom `docs/NEXT-2026-09-22-instrument-identification.md`
§5 describes is not present here. This change does not address it, and nothing
measured here should be quoted as though it did. What the slot placements buy
is the hold-out: `OMR_HOLD_OUT_UNIDENTIFIED` drops a staff with no slot, and
the arm takes staves with no slot from **25 → 5**.

## 11. CONTROLS ON THE WIRING

- **75 of 75** committed `slot_index` verdicts reproduced with both branches
  off, on both records the control runs on.
- **0 staves moved** on both documents, asserted per staff.
- **12 unit tests** (`tools/omr/tests/test_staged_slot_constraints.py`), with
  the positive controls in the same class as the refusals.
- **Mutation battery over `tools/`** (`mutate_rule.py`): **10 RED, 0 survived,
  2 dormant-by-design and named, 0 bad anchors, restore hash-verified.** Byte
  snapshot, in-flight sentinel, `PYTHONDONTWRITEBYTECODE=1`, and a judge that
  is `(returncode, failing test ids)` with **no elapsed time in it**.
- **All six derived checks exit 0** — `meaning`, `inventory`, `health`,
  `wiring`, `reach`, `capture` — and two of them had to be satisfied rather
  than waved through; see §11a. The derived flag-direction scan classifies
  `OMR_SLOT_CONSTRAINTS` default-ON deny-list, and
  `test_flag_docs_match_predicates` required the knobs row before the suite
  would pass.

### 11a. ⚠️ TWO DERIVED CHECKS FIRED ON THIS CHANGE AND BOTH WERE WORTH IT

**`inventory --check`: *`slot_index` declares `clef_glyph` and never reads
it.*** It follows a decision's own helpers **three deep**, and the read sat
four down (`adjudicate_slot_index` → `_apply_constraints` → `_constrained_slots`
→ `_clef_read_at`). That is a measure of code STYLE rather than of inertness —
the exact confusion that check's own docstring records repairing once already —
so the fix is the honest one: **the clef is collected in `_apply_constraints`,
where it is visible**, and the solver stays a pure function of what it is
handed.

**`meaning --check`: *a STAFF-scoped decision reads a `cell:*` quantity with no
page-frame key.*** Asked correctly, and the answer is that **no coordinate is
ever compared**: both clef quantities are read for their VALUE — the class name
`clefG`, the located `alto` — and `_clef_read_at` builds a set of NAMES. The
two frames are never brought into one comparison. Accounted in that module's
`KNOWN_GAPS` **with that reason**, and the entry is false the moment anything
here reads a glyph's x or y.

⚠️ **THE FULL SUITE WAS RUN TWICE AND THE FIRST RUN IS VOID.** It overlapped
this session's own mutation battery, which mutates the two files under test —
so its `2 failed, 4803 passed` was a reading of a MUTATED tree. Caught by the
in-flight sentinel, and by the same reflex that had already made a `git diff`
taken mid-battery unusable earlier the same session. *An instrument that reads
the working tree is not isolated from a battery that writes it.*

⚠️ **Three of my own test fixtures were wrong before the code was**: an alto
clef placed where no order-preserving map can put a viola (twice), and an
expectation that all three block members would be forced when the third reads a
BASS clef — which admits **both** the Violoncello and the Contrabasso slot, so
staying narrowed is the rule being right rather than short.

## 12. STILL NOT ESTABLISHED

Everything in §6 stands. Additionally: **no print was consulted by this
session** — correctness rests entirely on the 2026-09-14 and 2026-09-17 crop
passes; **Breitkopf is unscored**; **no export and no file**; and the
condensed `Violoncello e Basso` is still narrowed, deliberately (§3).

---

# ADDENDUM 2 — the roster naming, asked for and REFUTED by the plate

Sean, 2026-09-22: *"do the roster naming for those 10 staves."* **No code under
`tools/` changed** (`git diff -- tools/` is empty). The measurement says the
job as scoped has no effect, and the plate says why.

## 13. ⚠️⚠️ THE FIRST THING TO DO WAS OPEN THE PAGE, AND IT ANSWERED THE QUESTION

`out/print/brahms-system-head.png` — the Breitkopf system head at 600 dpi, all
14 staves. **All three "unnamed" reference slots are labelled on the plate, in
full:**

| slot | the plate prints | the reader got | the lexicon makes of it |
|---|---|---|---|
| 0 | **`Flöten`** | `Flo6ten 2` | **Tenor — a SINGER**, via the alias `ten` inside it |
| 5 | **`Hörner in C 1. 2.`** | `C in \|` | nothing |
| 13 | **`Kontrabaß`** | `KontrabaB` | nothing |

`Flöten` resolves to **Flute at coverage 1.00** and `Kontrabaß` to
**Contrabass at 1.00** when spelled correctly. So this was never a missing
instrumentation channel: it is **OCR damage on three characters** — `ö` read as
`o6`, `ß` read as `B`, and (on five further staves) `c` read as `e`, turning
`Vcl.` into `Vel.`.

⚠️⚠️ **AND THE SINGER IS THE SHARP END.** `Flo6ten 2` resolved to a **Tenor**
at a printed flute staff, and the only thing that stopped it reaching the file
was `vetoed_by_the_work_roster` — the family veto. On a work whose roster we do
not hold, that singer ships. It is `Tr. Alt.` → *Alto* again, from a different
cause.

⚠️ **THE OPENING SYSTEM IS THE ONE THE READER DOES WORST ON**, which is
counterintuitive and worth carrying: it prints the FULLEST names
(`Flöten`, `Kontrabaß`, `Hörner in C 1. 2.`) and the continuation systems print
the short forms (`Fl.`, `Hr.`, `K.-B.`) that the lexicon is keyed on and the
OCR gets right. A long German word gives the OCR more to spoil.

## 14. THE RULE WAS MEASURED ANYWAY, AND ITS REACH IN THE FILE IS ZERO

Two tiers, measured apart (`probe_name_from_slot.py`):

| tier | claim | Breitkopf |
|---|---|--:|
| **A** SIBLING | the slot is decided and another staff on it IS named — pure entailment, since the slot IS the part | **35 of 35**, 0 conflicts |
| **B** LINEUP | no staff anywhere names the slot; the canonical layouts + the roster force one | **0** |

**Tier B reaches nothing because Tier A reaches everything**: every one of the
three slots is named on a LATER system (`staff/1/0/0` reads `F1.` → Flute,
`staff/2/1/5` reads `(C) Hr.` → Horn, `staff/1/0/13` reads `K -B.` →
Contrabass). ⚠️ **That refutes §2 of this document**, which reported those 10
staves as *placed and nameless*: they are nameless **on the reference system**,
which `_pick_reference` chooses for being WIDEST — and the widest system here
is exactly the one whose labels the OCR spoiled. The slots are named; the
reference is not where they are named.

⚠️⚠️ **AND EVERY PART ON BOTH DOCUMENTS ALREADY CARRIES A NAME** — Breitkopf
14 of 14 slots, Litolff 12 of 12. `export.to_musicxml` takes a part's name from
the first staff of that part carrying one, so **naming these staves changes no
`<part-name>`, and `OMR_HOLD_OUT_UNIDENTIFIED` gates on the SLOT rather than on
the name, so it changes no held-out staff either.** The rule would be a
producer with no consumer and no file effect, on a fact the record already
holds by another route. It is therefore **NOT BUILT**, and this section is
what was delivered instead.

## 15. WHAT WOULD ACTUALLY HELP, PRICED

Two OCR repairs that are safe by this repo's own rule that a fold is admitted
**on rarity**, both tested against every refused label on both records:

| repair | why it is safe | recovers |
|---|---|--:|
| **a digit BETWEEN two letters is noise** (`Flo6ten` → `Floten`) | no instrument name has a digit inside a word; part numbers are separate tokens and the lexicon already handles them | **1** — and it is the SINGER |
| **`ß` read as `B` at a word end** (`KontrabaB` → `Kontrabaß`) | a DERIVED variant of aliases that already carry `ß`, the `_CONTRA_ALIASES` pattern; it adds no new word | **1** |

⚠️ **`c → e` (`Vel.` → `Vcl.`, FIVE staves) is NOT proposed**: CLAUDE.md
records it refused by name as a common-letter pair, priced at `Fug.`→`Fag.`,
`Oh.`→`Ob.` and Mahler's `Veelle.`. Re-litigating it would need the 1,422-label
corpus, not this page.

⚠️ **Neither changes the file either**, for the same reason as §14 — both slots
are already named elsewhere. Their value is that a wrong reading stops being
produced, and one of them is a singer on a symphony.

**The remaining 18 refused labels are noise** (`|`, `2`, `of`, `(Es)`,
`| | ©`) or the genuinely truncated horn labels. Nothing in the
instrumentation list reaches them.

## 16. WHAT IS NOT ESTABLISHED HERE

n = 1 document for the whole of §13-§15 (Litolff has **zero** refused labels
and **zero** staves in this population). The print truth for slots 0, 5 and 13
is one adjudicator reading one render, committed as a crop so it can be
checked. No code ran on a page; no export; no OMR-NED.

---

# ADDENDUM 3 — measured against the ROADMAP 2.1 gate

The manager session's acceptance criterion for roadmap item 2.1 is
**`staff_not_identified` 783 → under 100 on Litolff, ZERO grafts against the
print** — explicitly not a reach count. `export_arm.py`, one gather exported
three times:

| arm | `staff_not_identified` | events written | parts | coordinate names |
|---|--:|--:|--:|--:|
| control — both branches off | **783** | 1472 | 12 | 0 |
| base — the shipped family block + INFER | **141** | 2114 | 12 | 0 |
| **arm — + the constraints** | **141** | 2114 | 12 | 0 |

⚠️⚠️ **THIS SESSION'S WORK CONTRIBUTES ZERO TO THE 2.1 GATE.** The 783 → 141
was already won by `OMR_SLOT_FAMILY_BLOCK` on 2026-09-21; the constraints move
the PROVENANCE of those placements (13 inferences become entailments) and not
the count. The gate is **not met** — 141 against a bar of 100.

## 17. ⚠️⚠️ THE WHOLE RESIDUAL IS FIVE STAVES, AND THEY ARE ONE SHAPE

Every staff still held out of the file is a **`Violoncello e Basso`**:

```
staff/2/0/10  staff/2/1/10  staff/3/0/10  staff/3/1/7  staff/4/1/10
     ... each narrowed to candidates [10, 11] = Cello AND Contrabass
```

**141 notes, five staves, one cause.** Nothing else on these four pages is
unplaced. So 2.1's remaining distance is not a reading problem and not an
identity channel: it is that **a slot is one part and a condensed staff is
two**, which the record has nowhere to say. `inferences.collapse_slot_index_
to_family_block` leaves that member narrowed *deliberately* — its own
docstring says *"the last one covers both remaining slots and is left exactly
as the reader left it."*

⚠️ **THE CONVENTION IS ALREADY SEAN'S AND IT IS NOT AMBIGUOUS.** 2026-09-22:
*"string family always includes all 5 instruments - if there are only 4 lines
then the bass is doubling the celli or it comes in later."* So the fourth
string line IS the Cello **and** the Bass, and the question is representation,
not evidence.

⚠️ **AND THE MINIMAL MOVE WOULD CLEAR THE GATE AND IS NOT A GRAFT BY THIS
REPO'S OWN TEST.** Placing that member on the FIRST of its two slots takes
`staff_not_identified` **141 → 0**, and `classify` scores it a
**condensation** rather than a graft, because the printed name
`Violoncello e Basso` contains the slot's name — the 2026-09-15 membership
test, which exists precisely to keep those two apart. ⚠️ It would still be one
`<part>` where the music has two, which is what `OMR_CONDENSED_PARTS` is for
and which that flag records as **blocked on a COUNT the page cannot supply**.

**It is a DECISION and it is Sean's**, not this session's and not a peer
session's: it changes what a placed staff means. Nothing here takes it.
