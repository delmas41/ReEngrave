# Rests are not sized to the bar — and `size_measure_rest` is not why

Sean, reading the first cleanup artefact against the print:

> *"Many whole note rest which equal 2 beats are showing up as a single quarter
> note - which doesnt even make sense because the measure needs 2 quarters to
> be filled."*

Document: Litolff Beethoven 5 mvt 1, pdf pages 1-4, **2/4 throughout**
(hand-read off the plate; the artefact's own truth). ONE staged record,
`beethoven5-p1-p4.record.json`, md5 `d3620ba9cb70fc93f6b7ee91b6cbe40a` —
adjudicated four times and exported four times.

**The one-line answer:** `size_measure_rest` fires on **92 of 92** eligible
bars where the meter is decided and **0 of 195** where it is not. It has no
fault. The meter is unsettled on **6 of 7 systems**, and settling it takes the
bars that add up from **38.0% to 69.2%**.

---

## 0. The instrument, and what it cannot see

⚠️⚠️ **A PLAIN RE-EXPORT OF THE SAVED RECORD IS BLIND TO THIS WHOLE QUESTION.**
`size_measure_rest` is an EVALUATE **consequence** and the meter is an
ADJUDICATE **decision**, and replaying a record replays saved verdicts — so a
re-export would have produced a byte-identical file under every arm here and
the run would have read as *"the flag does nothing"*.

Every arm rebuilds a `Log` from the record's GATHER rows
(`readjudicate.rebuild`), re-runs **ADJUDICATE and EVALUATE** under a named
environment, and only then exports: `rest_sizing_arm.py`.

**Control, run first and passing:**

```
CONTROL: 2993 of 2993 duration verdicts reproduced exactly, 0 differ, +0 extra
```

**Second control, stronger and end-to-end:** the OFF arm's MusicXML against the
file the pipeline itself wrote from this record is **identical outside the
`<direction>` / `<dynamics>` blocks** — 0 differing lines of any other kind.
⚠️ The dynamics DO differ, and that is not noise: this record was gathered
before the duplicate-detection repair landed, and `dynamic` is an ADJUDICATE
decision, so a rebuild picks up the current adjudicator while a re-export does
not. **That is the manager's own finding arriving from the other direction**,
and it is why the OFF arm rather than the committed file is the baseline for
every number below.

⚠️ **WHAT IT CANNOT SEE: a GATHER change.** New rows, new fields, a changed
frame never enter the rebuild, and every arm would come back identical whatever
such a change did. Nothing here is a GATHER change — but a later repair that
touches `gather.py` needs two full re-gathers, and **this control would pass
vacuously across it.**

⚠️ **REACH is printed before any arm's numbers**, so a document whose systems
all read their own meter cannot produce a clean-looking zero here.

---

## 1. REACH, and the sub-population split

The record holds **646 standing rest durations**; the file holds **842 rests**.
The two differ because the exporter also pads every bar it read nothing in, and
a probe reading only rows that exist cannot see those. They are counted apart
throughout.

### 1a. The file, baseline (`probe/rest_lengths.py`)

| `<duration>` | ql | count | what it is |
|--:|--:|--:|---|
| 384 | **4.0** | **471** | TWICE the bar — the glyph's nominal whole-rest value |
| 96 | **1.0** | **218** | HALF the bar — Sean's "single quarter note" |
| 192 | 2.0 | 109 | correct |
| 48 | 0.5 | 40 | eighth |
| 24 | 0.25 | 4 | sixteenth |

`<rest measure="yes"/>` appears 108 times. This reproduces the brief's table to
the unit.

### 1b. The 471 decompose EXACTLY, and only two thirds of them are a rest

| | count |
|---|--:|
| `restWhole` glyphs the record READ, left at 4.0 | **303** |
| bars the record holds **no duration at all** for, padded by the exporter | **168** |
| **= the file's count, to the unit** | **471** |

168 is the exporter's own `empty_bars_padded_without_meter`. **A third of the
worst population is not a mis-sized rest — it is a bar we read NOTHING in**, so
a repair aimed at rest sizing reaches only two thirds of it. Both halves have
the same cause.

### 1c. The cross-tab that attributes the fault (`probe/crosstab.py`)

Bars the convention covers — one standing duration, a dotless `restWhole`,
nothing else:

| the system's meter | eligible bars | **SIZED** | **NOT sized** |
|---|--:|--:|--:|
| **DECIDED 2/4** (1 system) | 92 | **92** | **0** |
| abstained `too_few_staves_read_it` (4 systems) | 90 | 0 | **90** |
| abstained `no_evidence` (2 systems) | 105 | 0 | **105** |

**An empty interval.** ⚠️ **`size_measure_rest` has no fault**, and the brief's
leading hypothesis is confirmed rather than merely plausible.

---

## 2. ⚠️⚠️ THE OBSERVATION IS NOT ABOUT THE 4.0 RESTS — ASKING THE RENDERER SETTLED IT

Sean's sentence names a **glyph** while our fault is a **duration**, so the two
are one complaint only if the renderer turns one into the other. The artefact
engraves our MusicXML with **Verovio**, so the renderer was asked rather than
reasoned about:

| what our file writes, inside a 2/4 bar | what Verovio draws |
|---|---|
| unsized `restWhole`, `<duration>384</duration><type>whole</type>` (379 bars) | **a whole rest** |
| sized `<rest measure="yes"/><duration>192</duration>` (108 bars) | a whole rest |
| lone `<duration>96</duration><type>quarter</type>` (19 bars) | **a quarter rest** |

**The 4.0 bars render as WHOLE rests and are not what his eye caught.** The
brief's framing — that the 4.0 population is Sean's complaint — is **refuted**.

### 2a. And the quarter rests are not misread whole rests either

`probe/rest_glyph_shape.py` — a shape question needing no truth file. A whole
rest is a short wide filled rectangle; a quarter rest a tall narrow squiggle.

| glyph | n | aspect h/w (p10 / med / p90) | median w × h | median conf |
|---|--:|---|---|--:|
| `restWhole` | 395 | 0.38 / **0.46** / 0.52 | 142 × 66 | 0.61 |
| `restQuarter` | 209 | 2.39 / **2.66** / 6.39 | 117 × 313 | **0.71** |
| `rest8th` | 38 | 1.13 / 1.38 / 2.41 | 138 × 200 | 0.48 |

**EMPTY INTERVAL** — `restWhole` max 0.91, `restQuarter` min 1.40, **0 of 209**
`restQuarter` boxes inside the `restWhole` range, at the *highest* median
confidence of any rest class.

⚠️ **THIS IS SHAPE CONSISTENCY, NOT ACCURACY, AND IT IS ONE-SIDED.** A tall
thin box is not thereby a correct reading — this repo already records
`arpeggiato` firing **377 times on this very document** as *"a stem or a
barline"*, which is the same shape. What it rules out is exactly one
hypothesis: **a whole rest read as a quarter rest did not happen.** It
establishes nothing positive about what the page prints.

### 2b. What his eye was reporting: the bar does not ADD UP

The checkable half of the sentence is *"the measure needs 2 quarters to be
filled"* — an **underfull bar**. Summing each bar's longest voice
(`probe/bar_fill.py`) over all 1,183 exported measures, baseline:

| | bars | share |
|---|--:|--:|
| **OVERFULL** | **516** | **43.6%** |
| exact | 449 | 38.0% |
| **SHORT** | **218** | **18.4%** |

**Only 38% of the bars we export add up to the `<time>` the same file
declares.** That is the fact behind the observation, it is far larger than the
rest table suggests, and **nothing in the pipeline reported it**: the coverage
report prints `empty_bars_padded_without_meter: 168` and `measure_rests_read:
92`, and no reader could get from those to 43.6%.

| overfull bar total | contents | count |
|--:|---|--:|
| 4.0 | one whole rest | **379** |
| 5.0 | one note + one whole rest | 19 |
| 5.0 | one quarter rest + one whole rest | 13 |

428 of the 516 overfull bars contain an unsized whole rest. **19 short bars
hold exactly one quarter rest and nothing else** — the literal reading of his
sentence. 19 is not "many", so his eye was most likely catching the *class* of
bar that does not fill rather than that one shape. ⚠️ **Only he can settle
which**, and this document does not claim to.

⚠️ 379 > the 287 bars the RECORD holds as lone, because the exporter writes
**730 fewer notes than the record carries** (`duration_narrowed` 339,
`owned_by_another_staff` 176, `no_pitch` 215). ~92 bars come out lone in the
file that were not lone in the record. Widening the rule to them is **refused**
— §5.

---

## 3. THE ARMS — one gather, four adjudications, four exports

Every constant shipped unchanged. `OMR_METER_SEGMENTS` is at its default.

### 3a. The meter

| system | OFF | `OMR_METER_CARRY=1` | `OMR_METER_FROM_BARS=1` |
|---|---|---|---|
| `system/1/0` | **decided** `voted` 2/4 | `voted` 2/4 | `voted` 2/4 |
| `system/2/0` | abstained `no_evidence` | **`carried` 2/4** +6.0 | **`derived_from_bars` 2/4** +5.0 |
| `system/2/1` | abstained `too_few_staves_read_it` | **`carried` 2/4** +13.0 | +12.0 |
| `system/3/0` | abstained `too_few_staves_read_it` | **`carried` 2/4** +9.0 | +8.0 |
| `system/3/1` | abstained `no_evidence` | **`carried` 2/4** +18.0 | +17.0 |
| `system/4/0` | abstained `too_few_staves_read_it` | **`carried` 2/4** +9.0 | +8.0 |
| `system/4/1` | abstained `too_few_staves_read_it` | **`carried` 2/4** +7.0 | +6.0 |

Every support clears `METER_CARRY_FLOOR` (2.0) by a wide margin; the nearest is
3× it.

⚠️⚠️ **TWO INDEPENDENT MECHANISMS REACH THE SAME METER ON ALL SIX SYSTEMS AND
THE THREE FILES ARE BYTE-IDENTICAL** (carry / bars / both — one md5,
`ac2faa10acd032b41615b879c247dca6`). The bars-only support is **exactly 1.0
lower in every row**, which is `W_METER_CARRIED` — i.e. the bar evidence is the
same in both and the carry adds only its own term. That matters for the
recommendation: `OMR_METER_FROM_BARS` **cannot cross a movement boundary** (it
never looks at another system), so the answer here does not depend on the
carry's one real hazard.

### 3b. The file

| | OFF | carry / bars / both |
|---|--:|--:|
| rests at **4.0** ql (twice the bar) | **471** | **115** |
| rests at **2.0** ql (correct) | **109** | **465** |
| rests at 1.0 ql | 218 | **218** |
| rests at 0.5 / 0.25 | 40 / 4 | 40 / 4 |
| `measure_rests_read` | 92 | **280** |
| `empty_bars_padded` | 184 | 184 |
| `empty_bars_padded_without_meter` | **168** | **0** |
| notes | 1618 | 1620 |
| `notes_not_written_total` | 730 | 728 |

**356 rests corrected.** The 1.0 population does not move by one — the two
faults are disjoint, as §2a predicted.

### 3c. The number that matters: do the bars add up?

| | OFF | carry |
|---|--:|--:|
| **exact** | 449 (38.0%) | **819 (69.2%)** |
| OVERFULL | 516 (43.6%) | **157 (13.3%)** |
| SHORT | 218 (18.4%) | 207 (17.5%) |

**+370 bars now sum to their own meter.** SHORT falls by 11 and is essentially
untouched — a separate, unaddressed reading shortfall.

### 3d. Blast radius, stated rather than buried

The diff between the OFF and carry files is confined to: 356 `<rest/>` →
`<rest measure="yes"/>` with `<type>whole</type>` dropped; 40 `<time>` blocks;
5 `<clef>` lines re-emitted with the changed `<attributes>`; and **72 note
`<type>` values** (31 quarter, 26 eighth, 9 half, 6 16th), with notes
1618 → 1620.

⚠️ **Those 72 are `reconcile_duration`, not this work** — settling the meter
feeds the pipeline's one sanctioned loop, which re-reads a beam level by ±1
where the corrected bar lands exactly and uniquely on the meter. It is a
documented, bounded consequence of having a meter at all; it is **not measured
against the print here**, and it is the part of the carry arm a human should
look at first.

**The accounting control held in every arm** — `to_musicxml` raises
`Unbalanced` rather than returning, and all four arms returned. It remains an
EQUALITY.

---

## 4. The fixpoint, and why nothing here creates one

⚠️⚠️ **A LONE WHOLE REST MAY NOT CORROBORATE A METER**: its 4.0 is our own
default for want of one, so counting it reads that default back as evidence —
and since `size_measure_rest` then re-sizes it from that meter, the record
would report a genuine fixpoint.

**The guard already in the tree is STRONGER than CLAUDE.md describes it.**
`_bar_lengths_for` excludes **any bar holding a whole rest at all**, not merely
a bar whose only event is one, and its own comment says why: `Q.EVENT`'s
grouping and `size_measure_rest`'s population can disagree about whether a rest
is alone, so the narrower rule left a real hole.

**Nothing in this work widens the corroboration basis.** That is the
load-bearing sentence, and it is a statement about what was *not* changed.

⚠️ It is not free. `probe/can_the_bars_speak.py` measures what the exclusion
costs on these pages: it removes **17 to 111 bars per system**, leaving 6 to 17
assessable — enough here, and the recorded hazard *"the bars are not an
independent umpire over a bad reading"* says it will not always be. **On a page
whose ink is worse this repair goes quiet rather than wrong**, which is the
right failure direction and is not a claim that it works there.

⚠️ That probe also predicted all six carries correctly and got **four of six
supports wrong** (it predicted 5/11/9/16/5/7 against the arm's 6/13/9/18/9/7).
Its offline replica reads the record's SAVED event groupings and
post-consequence durations while the live run re-derives them. **It is a screen,
not a substitute**, and saying so is why it is committed.

---

## 5. What is REFUSED

1. **Widening `size_measure_rest` to bars that come out lone in the FILE**
   (~92 of them). Its evidence would become *what the exporter failed to
   write* — a guess about silence we never read, and an **uphill** dependency:
   EVALUATE runs before EXPORT and may not read its output.
   `record.UphillConsequence` exists for exactly this.
2. **Sizing the 168 unread bars from a meter we do not have.** The exporter
   already withholds `measure="yes"` there and falls back to 4.0, and its own
   comment says why. The repair is to give it a meter, not to let it invent one.
3. **Touching `METER_CARRY_FLOOR`, `METER_CARRY_MIN_BARS` or
   `METER_CARRY_MIN_STAVES_PER_BAR`.** Not measured here, and CLAUDE.md records
   that closing `A-DUR-8` is not licence to tune them. Every arm uses the
   shipped constants.
4. **Flipping `OMR_METER_CARRY` myself.** Every default flip in this repo is
   Sean's. §7 is a recommendation with its evidence, not a change.
5. **Turning the bar-fill figure into a gate.** It is gamed by emitting FEWER
   symbols — the opposite direction from a cleanup count, and the same trap
   OMR-NED's symmetry set. `--check` fails only when the instrument assessed
   **nothing**.

---

## 6. The one code change, and why it is in the rest path

`empty_bars_padded_without_meter` was incremented **only on the bad branch**,
so it was simply **ABSENT** from the report once every padded bar had a meter —
and a reader could not tell *"we sized all 184 correctly"* from *"this figure
was never computed"*. It reads **168** in the OFF arm and **vanishes** in the
carry arm, which is the run whose success it exists to report.

It is now written unconditionally (`+= 1 if meter is None else 0`). Same lesson
as `decided_uncounted` — *"the report cannot tell" is a different fact from
"wrote zero"* — arriving in the rest path.

⚠️ **The test that should have caught it was written with `.get(..., 0)`**,
which accepts an absent key as a zero, so the counter could stop being written
and every assertion would still pass. It is now `assertIn` plus the value, with
a positive control on a page that DOES pad bars, so the assertion cannot be
satisfied by an exporter that padded nothing.

**Mutation battery** (`mutate.py`), snapshot trees, positive control green:
**4 arms, all red** — the pre-fix form, the counter deleted, the sense
inverted, and an always-zero arm that is present and no longer counting.

**No other behaviour changed.** The rest emission path, `size_measure_rest` and
the meter carry are untouched.

---

## 7. Recommendation: default `OMR_METER_CARRY` ON — Sean's call

The knobs-table entry holds it off on **n**, and the plan says *a cleanup count
is what says which abstentions are worth resolving.* This is that evidence:

* it reaches **6 of 7 systems** on the first page anyone read against the print;
* it takes bars that add up from **38.0% to 69.2%** and rests at twice the bar
  from **471 to 115**;
* **two independent mechanisms agree on every system and produce a
  byte-identical file**, and the bars-only one cannot cross a movement
  boundary, so the result does not rest on the carry's one real hazard;
* every support clears the floor by at least 3×.

⚠️ **Against it, unchanged:** this is still **one document, one publisher, one
movement in a constant 2/4**, which is the smallest possible test of a
mechanism whose whole hazard is a movement boundary. The blocking objection
recorded in CLAUDE.md — *on a Breitkopf scan the meter GLYPHS are misread badly
enough that the weighing never gets a fair candidate* — is **not touched by
anything here**, and this document cannot touch it: its one read meter is
correct, so the carry is never handed a wrong candidate to weigh.

⚠️ **The cheapest thing that would settle it** is the same arm on Breitkopf
Brahms 1 p0-3, which this repo already holds gathered and hand-windowed and
whose meter reading is known bad. **If the carry propagates a misread `9/4`
across four pages there, that is the cost side nobody has measured** — and it
would show up in exactly this bar-fill number.

---

## 8. What is NOT established

* **n = 1 document, 1 publisher, 4 pages, one movement in a constant 2/4.**
* **No word of the print was re-read.** The bar-fill figure is the file against
  its OWN declared `<time>` — self-consistency, not accuracy. A bar can sum to
  2.0 and hold entirely the wrong notes.
* **The 218 short bars are unexplained**, 54 of them holding a single note.
  A reading shortfall this work does not touch and the carry barely moves.
* **The 72 re-read note `<type>` values are unadjudicated.** They are
  `reconcile_duration` doing its documented job, and nobody has checked them
  against the print.
* **Whether the page prints a quarter rest** where we read one. §2a rules out
  one hypothesis and establishes no positive fact.
* **Which bars Sean's eye actually caught.** §2b narrows it to a class and says
  so; only he can close it.
