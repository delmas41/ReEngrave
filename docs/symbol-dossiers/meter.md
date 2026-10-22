# Symbol dossier — METER

**2026-09-20.** Six symbols: the stacked digit pair, `timeSigCommon`,
`timeSigCutCommon`, the mid-movement change, the cautionary, and the meter that
is not printed at all. Research only — nothing here was changed; two things
were run and both take seconds (§"Probe" at the end).

The plan puts this family **last** because it is the declared cycle
(`meter <- meter`) and the least certain thing we read — on Litolff the meter
is decided on **1 system of 7**
(`docs/plan-2026-09-18-what-distinguishes-each-mark.md` §9.3, certainty table).

**Two structural facts govern everything below. Both are grep results, not
prose.**

| | |
|---|---|
| **The two readers are split by POSITION on the page, not by quality.** | `adjudicate_meter` votes the opening off `Q.METER_TEMPLATE` **only** (`adjudicators/rhythm.py:2391`). `_meter_changes` reads `Q.METER_GLYPH` **only** and drops cell 0 (`:1711`, `:1715`). So the **template reader never sees a change** and the **detector never gets a vote on the opening** — and cell-0 `timeSig*` rows are gathered (`gather.py:2345`, every cell) and read by nothing. |
| **The bar sums are the second witness for all five printed symbols, and they are not independent.** | A page whose meter the reader mangles is a page whose bars do not sum. Measured on the one system where an arbiter was needed: **0 of 7 bars clear the quorum** (`benchmarks/omr-staged-meter-boundary-2026-09/FINDINGS.md` §"9/4", hypothesis 3). |

### What this dossier does NOT re-derive

Four documents already answer parts of these questions and are cited rather
than repeated. Where this dossier ADDS to one or DISAGREES with one, it says so
at the point of disagreement.

| already answered | where |
|---|---|
| **Q1 by MARK**: the digit's five roles and their positional discriminators | `docs/position-grammar-confusables-2026-09-04.md` §2 *DIGIT* (and the `8`'s own counters in §2 *BOWL / BLOB*) |
| **Q3 the per-family POSITION fact**, and why position is rarely a rule by itself — Sean's own example there **is a meter** | `benchmarks/omr-family-positions-2026-09/FINDINGS.md`; `tools/omr/staged/positions.py`; `tools/omr/staged/capture.py` |
| **Sean's own TARGET MODEL for this family** — a meter decided PER BAR from seven ranked pieces of evidence | `tools/omr/staged/ASSUMPTIONS.md` **A-DUR-6**, with **A-METER-1..6** and **A-DUR-2 / -4 / -7** as the shipped pieces |
| **What absence means**, including "no meter on a continuation system means UNCHANGED" — named there as *the precedent every other entry should copy* | `docs/exploration-what-is-on-the-page-2026-09-09.md` §C1.3 |

**Where the effort went instead:** per-SYMBOL rather than per-family; Q2
(method) which none of the four covers; Q4 as a grep-backed stage trace; and
Q5b, the loop.

---

## `timeSig0`–`timeSig9` as a STACKED PAIR

Two digits, one in each half of the staff, centred on each other. Two readers
produce it: the **detector** (`Q.METER_GLYPH`, one row per `timeSig*` box, every
cell) and the **template reader** (`Q.METER_TEMPLATE`, a Bravura composite slid
along the 16-space header window, `tools/omr/time_signature_locator.py:400`).

### 1. What sets it apart — and what it is confused with

**The distinguishing facts, in the order the repo has evidence for them:**

| fact | strength |
|---|---|
| **It fills the staff's height** — each digit ≈ 2 staff spaces, numerator in the upper two spaces, denominator in the lower two | Bravura `timeSig4` **1.720 × 2.004 sp**; SMuFL *Metrics*: "two staff spaces tall, i.e. 0.5 em"; Gould p.152 "should exactly fill the height of the stave". **LITERATURE**, and it is the fact the repo is NOT using — see §4. |
| **It is set in a heavy font unlike any body numeral** | Gould p.152. **LITERATURE**, unmeasured here. |
| **Where it stands** — 10–12 spaces into cell 0 for an opening, ≈0 spaces into a later cell for a change | **MEASURED HERE** `[C32]`: a 4-space window at cell 0 reads **0 of 16** on a real printed `C` page; 14 spaces and the shipped 16 read **16 of 16** (`benchmarks/omr-meter-cautionary-arbiter-2026-09/FINDINGS.md` §3, Brahms 1 / Breitkopf p.45). |
| ~~Two digits aligned in x and adjacent in y~~ | **REFUTED HERE** `[C34]`: TRUE `dy` **32–548** vs FALSE **26–555**, total overlap. Do not re-try it. |

**What it is confused with — START FROM SEAN'S OWN TABLE.**
`docs/position-grammar-confusables-2026-09-04.md` §2 *DIGIT — one glyph, five
roles* already lists them: **tuplet digit · fingering · time-signature digit ·
measure number at a system start · stacked instrument numbers left of the
bracket · plate number** (margin). Its own summary of this symbol —
*"time-signature digits (read by header slot geometry + system vote, 12 correct
/ 0 wrong / 40 correct abstentions)"* — and its **R6** (*never tune a digit
threshold on one edition*, from the Litolff `3` matching Bravura's `6`) are
both reproduced below, and I agree with both.

**AGREES:** all five roles, the positional principle, and R6. The
tuplet/fingering gate is the shipped instance and it works (33 `fingering3` on
the widened corpus, **all 33 in cells holding a real triplet**).

**ADDS:** ⚠️⚠️ **the dominant live fault for this symbol is not a digit in the
wrong role — it is a `timeSig*` class fired on ink that is not a digit at
all.** Sean's table is organised by *what a printed digit can mean*; the
Litolff fault is *what gets called a digit*. A positional grammar over those
five roles cannot reach it, because the mark is a barline.

**The same doc already holds the other half, one entry away.** Its *BOWL /
BLOB* entry names **"the lower bowl of a 6/8's `8`"** among the
hollow-notehead confusables — so a printed `8` appears in Sean's alphabet
**twice**: once as a digit that can be misread, once as the thing whose own
counters get read as two noteheads. The crop pass measured that second
direction (**46 of 180 "notehead" boxes are not noteheads**, the `8`'s two
counters among them — `docs/breakthrough-2026-09-18-the-unit-of-enquiry.md`
§3). **One mark can be merged into its neighbour and carved into sub-parts in
the same family.**

**DISAGREES — one line, and it is a scope claim rather than a factual one.**
*"Time-signature digits (read by header slot geometry + system vote, 12 correct
/ 0 wrong / 40 correct abstentions)"* is true of **one of the two readers in
one of the two positions** — the TEMPLATE at the HEADER — and it reads as a
score for the symbol. The DETECTOR, which is the only reader of a mid-staff
change, has no such record: driven over 706 staff-cells it forms an opening
stack on **1 of 6 systems** (and that one is `1/1`), with **67 spurious `4/4`**
elsewhere (§2). **This symbol is well read in one frame and unread in the
other, and that one number covers only the first.**

Every row below is measured on a real page:

| confused with | where measured |
|---|---|
| **A barline broken into two fragments.** Litolff Beethoven 5 p.62 cell 8: one `timeSig3` + one `timeSig4` on staff 11, **both at `x_canonical = 0.00`, 0.35 and 0.40 staff spaces wide**, at the head of an empty rest bar. `_meter_from_digits` wants two glyphs at two `y_center` values and a broken barline supplies exactly that. | **MEASURED HERE**, n = all 17 staves of that page: `benchmarks/omr-ink-gather-2026-09/FINDINGS.md` §6.2 |
| **A barline fragment mid-bar.** Beethoven 5 p.1: five `timeSig4` in the middles of bars 6–12, propagated as common time across the page. | **MEASURED HERE**: `tools/omr/time_signature_locator.py` module docstring |
| **Clef ink**, when the window is too narrow. A 4-space window at cell 0 spells `4/4` / `9/4` / `12/16` / `5/4` out of a clef. | **MEASURED HERE**, n = 16 staves: cautionary-arbiter FINDINGS §3 |
| **Another digit role.** One printed digit has four meanings — meter, tuplet number, fingering, measure number — separated only by position. The 208-class space also spells it twice: `numeral4` is a coarse class covering all four and is **not** `timeSig4`. | **MEASURED HERE** `[C53]`; `tools/omr/class_aliases.py:25-97` |
| **Stacked instrument-grouping numbers in the margin**, which clamp to `x == 0`. | **MEASURED HERE**: `tools/omr/rhythm.py:189-203`, legacy veto `_TIMESIG_MIN_X_CANONICAL = 16` |
| **Its own counters read as noteheads.** The crop pass found **46 of 180 "notehead" boxes are not noteheads**, and among them **the two round counters of a printed time-signature `8`** — the mark carved into sub-parts rather than merged. | **MEASURED HERE**: `docs/breakthrough-2026-09-18-the-unit-of-enquiry.md` §3 |
| **A different digit.** `9/8` voted `9/4` — the numerator right, the denominator wrong, and `9/8` not even the runner-up. A Litolff `3` matching Bravura's `6` is the one wrong reading in the whole 11-source vote corpus. | **MEASURED HERE**: boundary FINDINGS §"9/4", n = 14 staves; `time_signature_locator.py:183-192` |
| **Nothing at all — spurious digits concatenating.** An engraved Brahms excerpt emitted `686/868`, `786/86`, `68/862` into MusicXML, unparseable by music21. | **MEASURED HERE**: `tools/omr/rhythm.py` `_plausible`, legacy guard |

### 2. Best method: YOLO / CV / other

**Classical CV (template correlation), decisively — and the margin is not
close.** The detector is not a weak reader of stacked digits on a scan; on the
one document where both were driven over the same cells it has **zero recall**:

```
Breitkopf Brahms 1, pdf pp.1-3, 706 staff-cells, driving the pipeline's own
_meter_from_digits over the committed transcription:

  staff-cells holding any timeSig glyph ......... 116
  ...forming a DIGIT STACK ......................  69
  systems where it forms an OPENING stack ....... 1 of 6   (and that one is 1/1)
  glyph census: {timeSig4: 234, timeSig1: 8, timeSig3: 1, timeSig6: 1}
                on a movement printing only 6/8 and 9/8
```
**MEASURED HERE**, `benchmarks/omr-meter-cautionary-2026-09/FINDINGS.md` §3.
At cell 0 of the very system that votes `9/4` the detector holds one `timeSig1`
and one `timeSig6` and forms nothing; at cell 1, where the page prints the
change back to `6/8`, one `timeSig4` and nothing. **It is silent at exactly the
two cells where a meter is printed, and forms 67 spurious `4/4` elsewhere.**
⚠️ These counts are a LOWER bound — they come from the legacy transcription's
NMS settings, and GATHER sees at least as many boxes.

The template reader, over 11 sources: **12 correct, 0 wrong, 3 missed, 40
correct abstentions** (`benchmarks/omr-timesig-2026-09/FINDINGS.md`).

**Why CV wins here and not elsewhere:** the vertical extent is *pinned* to the
staff, so the 2-D search collapses to a 1-D slide and a bare NCC score becomes
usable. That is a property of this symbol, not of NCC.

⚠️ **Two other CV discriminators were tried and rejected because they move with
the PRINTING rather than with the answer** — ink coverage (a scan's heavy type
covers 0.86–0.97, LilyPond's thin engraving 0.72–0.79, so engraved TRUE reads
score below scanned FALSE ones) and whitespace gutters (TRUE 0.00–0.33, FALSE
0.00–1.00, no separation). `time_signature_locator.py` docstring, **MEASURED
HERE**.

### 3. Where on the page the deciding information lives

1. **The header window** — 16.00 staff spaces from the staff's left edge
   (`tools/omr/staff_header.py` `measure_header_window`). The opening meter
   sits 10–12 spaces in, behind the clef and the key signature `[C32 + L40]`.
   ⚠️ The width is not free: on nine continuation pages the header frame's
   per-staff false rate is **16.75%** against **0.84%** for a 4-space mid-bar
   window — ~20× on the same pages with the same reader. *The width buys the
   true positives and the false ones together.* (cautionary-arbiter FINDINGS
   §4a, n = 191 staff-windows.)
2. **The other staves of the same system.** A meter is printed on every one of
   them `[C29]`, so a 12-staff system is twelve readings of one fact. The
   agreement floor is **0.70 as a FRACTION** — every one of 12 correct readings
   is agreed by ≥ 0.909 of its system, the one wrong reading by exactly 0.500.
3. **The bars the meter governs.** Second witness, and see §5 for why it is not
   an independent one.
4. **Where the digit stands within the staff's height** — the family POSITION
   fact, `Q.METER_GLYPH_POSITION`: which HALF of the staff the mark occupies
   and how far its centre is from the middle line
   (`benchmarks/omr-family-positions-2026-09/FINDINGS.md` §1). ⚠️ It is
   **default OFF** (`OMR_FAMILY_POSITIONS`) and read by nothing — see §4.
   ⚠️⚠️ **And Sean's standing warning about position facts is stated with a
   METER as its worked example, so it applies here before anywhere else:**
   *"position is an option for helping us determine something but will rarely
   be a clear rule that determines by itself. 2 numbers not connected, one in
   the upper half and one in the lower half, could be a time signature. Due to
   ink bleed they may appear connected… Quick rules will give us quick results
   that could be poor."* (2026-09-17.) The measurement agrees with him — see
   *What we do not know* #4.

### 4. Stage by stage

| stage | what happens | where |
|---|---|---|
| **GATHER** | `gather_meter` files `Q.METER_TEMPLATE` (one row per staff, header window, with `score`, `raw`, `runner_up`, `runner_up_score`, `score_margin`) and `_gather_meter_glyphs` files `Q.METER_GLYPH` (one row per detector `timeSig*` box, **every cell**, with `cell`, `x`, `y_center`, `letter`). | `gather.py:2251`, `:2313` |
| | `gather_meter_positions` files `Q.METER_GLYPH_POSITION` — `half` (upper/lower/spans/outside), `crosses_middle_line`, `centre_steps_from_middle` — against the staff's own middle line. ⚠️ **Behind `OMR_FAMILY_POSITIONS`, default OFF** (`positions.py:180`), so on a default run it is not even gathered. | `positions.py:603` |
| **ADJUDICATE** | `adjudicate_meter` tallies `Q.METER_TEMPLATE` rows by **printed form** (`raw`), applies `METER_COVERAGE_FLOOR = 0.5` then `METER_AGREEMENT_FLOOR = 0.70`, and returns `reason="voted"`. | `adjudicators/rhythm.py:2374` |
| **EVALUATE** | Nothing consumes the digits directly; the *decided meter* drives `size_measure_rest` and `reconcile_duration`. | `consequences.py:117`, `:215` |
| **INFER** | Nothing. `Q.METER` is deliberately absent from both inference rules' `reads` lists, and a duration witness whose provenance closure contains `Q.METER` is **refused** (`inferences.py:484` `_witness_is_meter_derived`). | — |
| **EXPORT** | `<time>` per bar via `record.meter_at`, `symbol=` from the matched letter glyph. | `staged/export.py:2005`, `:2136` |

⚠️⚠️ **THREE FACTS ARE GATHERED AND READ BY NOTHING, and all three are
grep-confirmed:**

| gathered | read by |
|---|---|
| `Q.METER_GLYPH` rows **at cell 0** — the detector's own opinion of the opening | **nothing.** Its only consumer is `_meter_changes` (`rhythm.py:1711`), which drops cell 0 three lines later. |
| `Q.METER_GLYPH_POSITION` — the whole placement convention. ⚠️ Worse than unread: **default OFF**, so on a normal run it is not produced either. | **nothing.** `grep -rn 'Q.METER_GLYPH_POSITION' tools/omr/` returns the producer, two inventory entries and tests — **one of ten producers with no consumers**, which is the whole subject of `benchmarks/omr-family-positions-2026-09/FINDINGS.md` and is deliberate (*"a producer and its first consumer landing in one change makes the reach measurement circular"*). `reach.py:188` names its intended first consumer: `_meter_from_digits`, "which accepts ANY two `timeSig*` glyphs at two different `y_center` values — no width, height, x or half test". |
| `Q.METER_TEMPLATE.score`, `.runner_up`, `.runner_up_score`, `.score_margin` | **nothing.** `adjudicate_meter` reads `row.detail["raw"]` and `row.value` only. `score_margin` was tested as a discriminator and **refuted** (TRUE 0.0681–0.3840, FALSE 0.0675 — a gap of 0.0006). The ABSOLUTE score does separate on the one case (TRUE 0.744–0.781, the FALSE one 0.514, empty interval 0.531–0.656) and was **not shipped on scope**: `min_score` is shared with the legacy path. |

⚠️ `Q.METER_GLYPH.letter` is written (`gather.py:2349`) and read by nothing —
`_meter_from_letter` keys on the glyph NAME. Harmless today.

⚠️ A small dead patch inside the meter's own corroborator: `_corroborate`
(`rhythm.py:1187`) computes `whole_rests`, `agree`, `disagree` and `observed`
and then returns `_score_bars(bars, expected)` without using any of them. The
whole-rest exclusion it documents does happen — in `_bar_lengths_for`. Cosmetic,
but it is *computed-and-unread* inside the function whose docstring explains why
it matters.

### 5. Abstain or best-guess — and what leans on this

**(a) Can it abstain? Yes, in five named ways, and it does.** `no_evidence`,
`too_few_staves_read_it` (with `coverage` and `would_have_been`),
`no_agreement` (with the full `readings` tally), then the fallbacks. Measured
on the corpus: on Litolff pp.0-2 `system/2/1` abstained `too_few_staves_read_it`
at coverage 0.273 with **`would_have_been: "C"`** on a 2/4 document — the gate
holding back a latent length misread (`benchmarks/omr-meter-abstain-and-misread-2026-09/FINDINGS.md`
§7). The abstention is real and it is doing work.

⚠️ **The legacy path does best-guess and the staged path does not.**
`rhythm.parse_time_signature` step 3: *"Single digit → assume denominator=4
(best guess)"*. `_meter_from_digits` refuses (`len(digits) < 2 → None`). Two
different answers to the same ink, in one tree.

**(b) What leans on it, and does the witness fail on the same pages?**

| leans on the meter | how |
|---|---|
| **Every rest in an otherwise empty bar** | `size_measure_rest` fires on **92 of 92** bars where the meter is DECIDED and **0 of 195** where it abstained. Litolff, `benchmarks/omr-rest-sizing-2026-09/FINDINGS.md`. |
| **Durations** | `reconcile_duration` re-reads one note per bar against the settled meter. |
| **Bar fill in the file** | With the carry on, bars that add up go **54.4% → 81.2%** like-for-like over 1,109 bars. |
| **The exporter's `measure="yes"`** | withheld where the meter is unknown. |

⚠️⚠️ **THE INDEPENDENCE CHECK FAILS IN TWO DIRECTIONS AND BOTH ARE MEASURED.**

1. **The bars are not independent of the reading.** On Brahms 1 / Breitkopf p1
   s0 — the exact system voting `9/4` — **not one of 7 bars clears the
   cross-staff quorum**, so the arbiter is silent precisely where it is needed.
2. **Cross-staff agreement is not independent either.** The wrong `9/4` is
   **unanimous: all 10 staves that spoke agree (`share` 1.0)**, so the coverage
   and agreement floors both pass. *Every staff feeds the SAME reader the SAME
   typeface.* Twelve readings of one fact are not twelve witnesses when one
   reader reads all twelve.

**The one genuinely independent witness has no producer.** `adjudicate_meter`
declares `Q.DOSSIER_FACT` in `wants` and never reads it; `--dossier` exists on
`tools.omr.transcribe` and **not** on `staged/__main__.py`, so the row abstains
on every staged run this repo has made (`tools/omr/no_producer.py:596`,
`staged/wiring.py:152`, `staged/reach.py:71`). The exclusion is deliberate — a
dossier is built from the same MusicXML the benchmarks score against — but the
consequence is that **on the staged path there is no meter witness that does
not come off the same raster.**

---

## `timeSigCommon` (the `C`)

One glyph, two staff spaces tall, centred on the middle line, stating a
complete meter. Produced by the detector as class `timeSigCommon`, and by the
template reader as `raw = "C"` (it is in `DEFAULT_METERS`).

### 1. What sets it apart — and what it is confused with

**Apart:** it is a complete meter in ONE glyph — which is why
`_meter_from_letter` earns `W_CHANGE_GLYPH_PAIR = 3.0` and not the loose weight
(`rhythm.py:1493` docstring). And it is the strongest single reading in the
corpus: **five common-time pages at 0.745–0.761** NCC, against 0.50–0.62 for
scanned digit meters (**MEASURED HERE**, `time_signature_locator.py` docstring).

**Confused with — and this is the symbol most often faked:**

| confused with | where measured |
|---|---|
| **Nothing — a blob.** *"A common-time glyph is a small rounded blob two spaces tall, the cheapest shape on a music page to fake."* Of the top 16 false answers the mid-bar template reader gives over 1,612 empty windows, **13 are `C`**. | **MEASURED HERE**, n = 1,612 windows / 10 pages / 2 publishers: `benchmarks/omr-meter-template-changes-2026-09/FINDINGS.md` |
| **Clef ink and general header noise.** The detector fires one `timeSigCommon` at confidence **0.377** on one staff of seventeen on Litolff p.61 — a page that prints bar 140 and **no time signature anywhere**. | **MEASURED HERE**: `benchmarks/omr-staged-meter-boundary-2026-09/FINDINGS.md`; the committed record `out/m7lit6162-OFF.meter.json` still carries it as a decided `change_only` `C` at support 4.5. |
| **A `¢`.** A `C` is a strict SUBSET of a cut-C's ink, so both templates match a real `¢` and the one with less to account for scores higher. | **MEASURED HERE**, `benchmarks/omr-timesig-2026-09/sweep_cutC.json` |

⚠️ **Confidence separates the true from the false populations cleanly — 0.887–0.927
engraved, 0.377–0.560 scan — and is deliberately NOT gated on**: four rows on two
documents is not a threshold.

### 2. Best method: YOLO / CV / other

**This is the one symbol in the family where YOLO is genuinely good**, and the
repo says so in terms: *"`timeSigCommon` and `timeSigCutCommon` are the two the
detector reads WELL and the template library has no digits for — so the two
readers are complementary, not redundant"* (`gather.py:2313`).

**Both, and they are wired to different questions:** the template reads `C` at
the header (a vote on the opening); the detector reads `timeSigCommon`
anywhere (a candidate change). Neither can do the other's job today.

⚠️ A SIZE gate is the obvious available defence and is not built. Gould and
SMuFL both give the number — the glyph is ~2 staff spaces tall — and a small
rounded blob is not. `Q.METER_GLYPH_POSITION` records the height fact; nothing
reads it.

### 3. Where on the page the deciding information lives

Same three places as the digits, plus one specific to the letter: **the centre
column of the matched box**, which is what separates it from `¢` (next section).
The false `C`s all sit where an *empty* window was given to a reader that can
say "zero" — the lesson the key-signature family already paid for: *the reader
that can say "zero" must never be given an empty window.*

### 4. Stage by stage

GATHER files it twice — as `Q.METER_GLYPH` (`letter=True`) and, where the
template matches, as `Q.METER_TEMPLATE` with `raw="C"`. ADJUDICATE:
`adjudicate_meter` votes it off the template rows; `_meter_from_letter` reads
the glyph rows at cells > 0 for a change. The two tables
(`_LETTER_BY_GLYPH`, `_tsl.LETTER_METERS`) are held equal by two module-level
`assert`s so they cannot drift (`rhythm.py:1487`). EXPORT writes
`symbol="common"` from `raw` — and here `raw` **is** evidence, because the
staged `raw` is a matched glyph, where the legacy `raw` is synthesised from the
numbers (`staged/export.py:2005`).

### 5. Abstain or best-guess — and what leans on this

**Abstains:** yes. `_meter_from_letter` refuses outright where one staff carries
**both** a `timeSigCommon` and a `timeSigCutCommon` at one bar — *"it has not
read a meter, it has read two"*.

**What leans on it:** a `C` is 4.0 quarter notes, so everything in §5 of the
digits section applies. ⚠️ And the specific hazard of the false `C`: because
one staff reading a *complete* meter clears `METER_CHANGE_FLOOR = 3.0` alone by
design, **a single 0.377-confidence blob is enough to put a meter change on the
record.** The repo's own note: *"the hazard is `METER_CHANGE_FLOOR`, not the
letter path"*.

---

## `timeSigCutCommon` (the `¢`)

A `C` with a vertical stroke through it. In the 208-class space as
`timeSigCutCommon`; **not** in the template reader's `DEFAULT_METERS`, and read
anyway.

### 1. What sets it apart — and what it is confused with

**It is confused with exactly one thing: a plain `C`** — and before 2026-09-01
it was read as one, unanimously: Mozart 40 i **11 staves of 11**, Brahms 4 i
**13 of 13**, so a 2/2 page shipped as 4/4 with every bar measured against a
meter twice too long. **Fifteen of the 97 dossier works open on a `¢`.**
(**MEASURED HERE**, `benchmarks/omr-timesig-2026-09/FINDINGS.md`.)

**What sets it apart — and the two sources disagree about which fact to use.
This is recorded as disagreement #3 in the conventions registry.**

| source | proposed discriminator | outcome |
|---|---|---|
| **LITERATURE** (Bravura `glyphBBoxes`) | HEIGHT. `timeSigCommon` **1.676 × 2.000**, `timeSigCutCommon` **1.672 × 2.880** — same width, **cut-C 44% taller**, "so height alone separates them; the stroke does not have to be found". | not tried here |
| **MEASURED HERE** | The centre-column fill, after `C` has won. Over **87 staves that matched C**: the **24 cut ones fill 1.00** of the centre column and **no other exceeds 0.48**. Gap 0.48→1.00 with nothing in it; every threshold in 0.50–1.00 gives the same answer. `cut_stroke_min_fill = 0.75` is its middle. | **shipped** |

⚠️⚠️ **The length cannot tell them apart and never will.** `C` and `¢` are both
**4.0 quarter notes** — `report_boundary.length_of` returns 4.0 for both, with
the comment *"the bars cannot tell `C` from `¢`, so only ink can"*. This is the
one symbol in the family where the bar-sum witness is **structurally** useless,
not merely often silent.

### 2. Best method: YOLO / CV / other

**A hybrid, and the hybrid is the finding.** The detector reads the CLASS
`timeSigCutCommon` well. The template reader must **not** search for it:
adding the template was measured and fails **both ways** — nine false systems,
*and* it still loses to plain `C` on the real `¢` pages, because a `C` is a
subset of a cut-C's ink and NCC does not reward a template for the extra ink it
explains. **No threshold between two scores fixes that.**

So: **shape for the letter, POSITION for the stroke.** The stroke is read by
asking whether the middle of an already-matched `C` is inked — a plain C's
middle is hollow, its aperture faces right. A row counts as inked if *anything*
in the centre column is inked rather than if the mean is high, because the
stroke is thin and a degraded print thins it further (`_looks_cut`,
`time_signature_locator.py:363`).

⚠️ **This adds no false-positive surface by construction** — the cut reading
rides on a `C` that already cleared the threshold and the vote, so the only
outcome that can change is a `C` becoming a `C|`.

### 3. Where on the page the deciding information lives

**The centre fifth of the matched box, over the glyph's own two-space height**
— not the padded four-space box, or the padding would halve every reading.
`cut_stroke_centre_frac = 0.10` either side of the middle, because the C's own
arcs are at the edges.

### 4. Stage by stage

GATHER: `Q.METER_GLYPH` with `letter=True` from the detector; `Q.METER_TEMPLATE`
with `raw="C|"` where `_looks_cut` upgraded a matched `C`. ADJUDICATE: voted
like any other form — **the vote key is the printed FORM, not the bar length**,
so `C` and `C|` and `4/4` can never be averaged into one answer. EXPORT:
`symbol="cut"`.

Measured reaching the file: Brahms 1 iv's `¢`, read on **24 staves of 24 at
support 74.0**, went from reaching **no** file to reaching all 24 parts when
`OMR_METER_SEGMENTS` shipped on (`staged/export.py:103`).

### 5. Abstain or best-guess — and what leans on this

**Abstains:** only via the `C` it rides on. There is no "`C` or `¢`, cannot
tell" outcome — `_looks_cut` returns a bool. Given the empty interval
(0.48 / 1.00) that is defensible on this corpus, and it is n = 87 staves on two
corpora.

**What leans on it:** nothing arithmetic — the length is identical either way,
which is exactly why a mistake here is invisible to every bar-sum check, every
rest sizing, and `probe/bar_fill.py`. It is visible only in the engraving:
musicdiff charges the difference at a **flat 3 edits per staff** (25 staves of
Bruckner 5 = 75). **This is the family's one purely-engraving fact, and the only
thing that can check it is a human or a second reading of the ink.**

---

## The mid-movement meter CHANGE

A new time signature standing immediately right of the barline that opens the
bar it governs. No class of its own — it is a `timeSig*` glyph whose **cell
index is not 0**.

### 1. What sets it apart — and what it is confused with

**It is set apart by POSITION and by nothing else.** `[C33 + L43]`, Gould p.152:
*"The new time signature is always placed after the barline."* So a meter glyph
at a bar's HEAD (left fraction ≈ 0) governs that bar; meter-shaped ink elsewhere
in a bar is not a change. Unlike an opening, **there is no clef in front of it**
— which is why a 4-space window is right here and a 16-space window is right
there, and why the two are not interchangeable.

| confused with | where measured |
|---|---|
| **A broken barline at the bar head.** The flagship case. Litolff p.62: the pipeline's `3/4` is two fragments of one barline at `x = 0.00`, 0.35 and 0.40 sp wide, at **cell 8** — while the print puts the `3/4` at **cell 6**, where the detector fires **ZERO `timeSig*` on any of 17 staves**. | **MEASURED HERE**, crops in `benchmarks/omr-ink-gather-2026-09/out/print/`, table in FINDINGS §6.2 |
| **A CAUTIONARY** at the system's last cell. See next section. |  |
| **A RESTATEMENT of the meter already in force.** Comparing each candidate against the system's OPENING rather than the meter in force produced **five consecutive `4/4` segments on one system** — *a system does not change meter five times to the meter it is already in*. Fixed. | **MEASURED HERE**, boundary FINDINGS §4c |
| **A change BACK to the opening, dropped.** The same comparison failing the other way: a `3/4 → 4/4 → 3/4` movement recorded the departure and never the return. Beethoven 9's finale does it repeatedly. Fixed. | same |
| **One spurious digit at one staff.** `4/4` at support 4.0 and 3.0 on Brahms p1, both read on **one staff** of ~20. | committed record `out/m7brahms1scan-OFF.meter.json` |
| **An implausible meter.** `1/1` at support 5.0 out of `timeSig1` detections — *a confident reading of a meter nobody has ever engraved*. Refused by `_PLAUSIBLE_METERS`. | boundary FINDINGS |

⚠️⚠️ **THE SCAN-SIDE SCORECARD, newest generation, deduped, from the committed
records** (`benchmarks/omr-meter-corroboration-2026-09/FINDINGS.md` §1c, joined
to the `m7` records I read):

```
TRUE   24 staves  support 74.0  C|    cell 6   brahms4-m386-412  ENGRAVED
TRUE   23         71.0          C     cell 3   boundary-m204-232 ENGRAVED
TRUE   21         70.0          6/8   cell 1   brahms1-m1-22     ENGRAVED
TRUE    1          3.0          3/4   cell 8   litolff-984073 p62  SCAN  <- and see below
FALSE   1          4.0          4/4   cell 2   brahms1-317803 p1   SCAN
FALSE   1          3.0          4/4   cell 4   brahms1-317803 p1   SCAN
FALSE   1          4.5          C     cell 3   litolff-984073 p61  SCAN
```

**Three true changes, all engraved, all read on 21–24 staves. Four scan rows,
all read on one staff — and the one scored TRUE is the barline fragment at the
wrong cell.** The value `3/4` is right and the page really does change to 3/4;
the cell index and the ink are not. ⚠️ `report_boundary.TRUTH_CHANGES` still
records `("litolff-984073", 62): (8, "3/4")` — **the committed truth file carries
the stale cell index.**

So: **stated honestly, this project has never read a mid-movement meter change
off real meter ink on a scan.** The populations that a guard would have to
separate — TRUE and FALSE — **overlap at exactly one staff**, and stave count,
support and bar math all fail in the same place.

### 2. Best method: YOLO / CV / other

**Today: YOLO only, and it is the weak reader on the ink it is worst at.**
`_meter_changes` reads `Q.METER_GLYPH` and nothing else by default.

**The measured alternative exists and is default-OFF:**
`OMR_METER_TEMPLATE_AT_BAR` asks the **template** reader at candidate bar heads
— *on every staff of the system, including staves that detected nothing*, which
is the only thing the detector cannot do. Its safety is a **cross-staff quorum**,
measured on the empty-window hazard:

| admitted on | spurious columns over 1,612 empty windows |
|---|--:|
| 1 staff | 16 |
| 2 staves | 2 |
| **3 staves (shipped constant)** | **0** |

⚠️ **The quorum is safe AT 4 SPACES AND NOT AT 8** — at 8 spaces a three-staff
false consensus appears. *The width and the quorum are one safeguard at one
operating point, not two independent ones.* ⚠️ `min_score` was deliberately not
moved: the positive control's own minimum (**0.542**) sits **below** the worst
false answer (**0.6141**), so the populations overlap and no score threshold
separates them. ⚠️⚠️ **Its accuracy is unmeasured in one direction: no page in
reach prints a mid-staff change, so it has never been shown to read a real one.**

⚠️ The briefed assumption that a detection names a few candidate bars is **false
on a scan** — **38 of 51 columns (74.5%)** on Brahms 1 pp.1-3 are candidates, so
candidacy is not where the safety is.

### 3. Where on the page the deciding information lives

1. **The first 4.0 staff spaces of the measure cell** — a slice of the cell the
   pipeline already cut, not a second cutting path.
2. **The same bar on the other staves of the system.** A change is printed on
   every staff at one bar; that is what an engraver does.
3. **Whether it is the staff's LAST cell** (cautionary, next section).
4. **The bars from that bar onward** — `W_CHANGE_BAR_FITS = +1.0` each,
   `W_CHANGE_BAR_CONTRADICTS = -1.0` each, accumulating over the run rather than
   through a run-length constant.

### 4. Stage by stage

GATHER files `Q.METER_GLYPH` at every cell with `cell` on the row; with the flag
on, `gather_meter_at_bars` also files `Q.METER_TEMPLATE_AT_BAR` **filed under a
separate quantity on purpose** — `adjudicate_meter` votes every
`Q.METER_TEMPLATE` row as an opinion about the OPENING, so a mid-staff reading
filed there would make a change at bar 9 argue about bar 1.

ADJUDICATE: `_meter_changes` scores each distinct reading per cell —
`W_CHANGE_GLYPH_PAIR = 3.0` per staff reading a complete meter,
`W_CHANGE_GLYPH_LOOSE = 0.5` per unpaired digit, plus the bar run — against
`METER_CHANGE_FLOOR = 3.0`. **One staff reading a complete meter clears the
floor alone, by design**, and two contradicting bars sink it again.
Template readings are admitted **GAPS ONLY** (a staff that read its own digits
keeps that reading) and reported apart as `staves_from_bar_head_template`,
never folded into `staves_reading_a_meter`.

EVALUATE / EXPORT: the change becomes a `segments` entry, and `record.meter_at`
gives the exporter the meter in force at each bar.

⚠️ **The one thing ADJUDICATE does not read is where the glyph stood in the
staff.** `Q.METER_GLYPH_POSITION` exists for exactly this case and no decision
consumes it — which is why the Litolff fragments are still not refused.

### 5. Abstain or best-guess — and what leans on this

**Abstains:** the floor is a genuine refusal and it is recorded, not defaulted.
`reason="change_only"` is the interesting outcome: *"unknown until bar 8, 3/4
from there"* — a system whose OPENING is unknown but which prints a change.
That is the range-scoped fact earning its keep.

**What leans on it:** a change re-sizes every bar from that point in the file
(`OMR_METER_SEGMENTS`, default ON). ⚠️ **The flip's own standing objection:**
with segments on, the scanned arm's false segments do not sit inertly on the
record — **each one re-sizes bars in the file.** On one page `<time>` elements go
**41 → 138**. The repo's attribution is that the lever is the meter GLYPH
READERS, not the weighing, and the left-fractions confirm it from the other
side: each false segment reads 0.000, at the head of its bar where a real change
stands, so no placement rule can reach them.

**And the reach was confined rather than refused (A-METER-6):** an uncorroborated
change (`< METER_CHANGE_MIN_STAVES = 2`) still governs its own system's bars,
and may no longer be the meter **carried** onto later systems. That pairing —
the STRONGER witness (other staves reading the SAME meter) with the WEAKER
action — is deliberate: `key_signature_corroboration` takes the opposite pair
because it REVERTS, and needs the weakest witness or it breaks transposing
instruments. **Confining costs at most a carry; reverting costs the music.**
Measured: 7 change segments, 3 corroborated / 4 confined, **every TRUE change
still in `segments` 4 of 4**, corroborated carries moved 0 of 3, uncorroborated
4 of 4. ⚠️ One confinement swaps one wrong answer for another.

---

## The CAUTIONARY meter

A courtesy time signature printed **after the final barline** of the system that
is ending, announcing the one that begins. It governs no bar. Same classes as
any meter; what identifies it is that it stands in a staff's **last cell**.

### 1. What sets it apart — and what it is confused with

**The fact: it is in the LAST cell, and its own bar does not fit it.** The rule
was checked against the corpus **before it was written**, which is what
separates it from a story fitted to its own data:

| | cell position |
|---|---|
| **all four TRUE changes** | a NON-last cell — Litolff p.62 cell 8 of 13, Brahms 1 i cell 1 of 8, Beethoven 5 iv cell 3 of 9, Brahms 1 iv cell 6 of 8 |
| **both cautionaries** | a LAST cell — 6 of 7 and 7 of 8 |

**MEASURED HERE**, `benchmarks/omr-staged-meter-boundary-2026-09/FINDINGS.md`
§4c. With the meter-in-force fix: **false meter changes 10 → 3, no true change
lost**, engraved arms **4 printed / 4 found / 0 false**.

**Confused with:** a genuine meter change at a system's last bar — which is why
the rule carries the escape `not best["bars_fit"]`: a last-cell candidate whose
own bar FITS is still treated as a change. And with **noise in the worst frame
there is**: the `head_last` window is **3.1× more likely to fabricate a meter
than `head_mid`** (2.62% vs 0.84%), and the single worst bar-head false score
anywhere — **0.6141** — is a last-cell window, *above* the true header minimum
of 0.5563. On Brahms pages 1–3, which print no cautionary at all, there are
**3 false last-cell stacks, all `4/4`, one per page-system**.

### 2. Best method: YOLO / CV / other

Today: the detector, via `_meter_changes` at the last cell. Both committed
cautionaries were found that way — the engraved Brahms `9/8` on **19 staves at
support 57.0**, the scanned one on **9 staves at support 26.5**.

An independent second reading of the same convention exists and used a
completely different measurement: **ink fraction**, where the one visible
cautionary reads **1.000 on all 19 staves** against **≤ 0.118 for every other
segment**. That was kept as a cross-check rather than a second implementation.

### 3. Where on the page the deciding information lives

**Its cell index against the staff's own last cell** —
`_last_cell_per_staff` reads `Q.MEASURE_PARTITION` **per staff, not per
system**, because the staves of one system do not always agree how many bars
they hold: on the Breitkopf Brahms the scan reads 8 cells where the print has
7 bars, and the extra one is the trailing sliver the cautionary sits in.

⚠️ That makes the cautionary's identification **dependent on the barline
reader**, which is a different reader from either meter reader — genuinely
independent of the meter ink, and a real strength of this rule.

### 4. Stage by stage

GATHER: nothing special — it is an ordinary `Q.METER_GLYPH` row.
ADJUDICATE: `_meter_changes` returns `(changes, cautionaries)`; the cautionary
test runs **before** the restatement test, because a courtesy signature is not a
restatement of anything on this system and calling it one would lose it.
`_with_segments` puts it on the meter's VALUE as `cautionary`, **not in
`detail`** — *"a consumer reading this system's meter is exactly who needs to
find it"*. `_meter_in_force_at_end` strips it when carrying, because it is a
statement about the system AFTER the source.
**EXPORT: nothing. `grep -rn cautionary tools/omr/staged/export.py` returns
zero.** MusicXML has no way to say it in this exporter, so the fact is recorded
and never written.

### 5. Abstain or best-guess — and what leans on this

**It is RECORDED, not discarded, and that is the whole design.** Its VALUE is
right even though its placement is not a change — and the document's own answer
to a misread opening is often exactly that: on the Breitkopf scan the opening is
voted `9/4` while the cautionary one system earlier reads `9` over `8` on nine
staves.

⚠️ **`report_boundary.TRUTH_CHANGES` records both cautionaries as `None` — a
statement about PLACEMENT, not about VALUE. A reader who meets that `None` and
concludes the cautionary is junk has read the wrong column.** That confusion
already cost one session its reach figures.

**Nothing consumes it.** Using it as an arbiter against a misread opening was
designed and measured and **could not be decided**:

| | |
|---|---|
| no common currency | the cautionary carries `support`, the opening carries `share` |
| the one shared quantity points the wrong way | staves reading it: **9 for the correct cautionary, 10 for the wrong opening** (19 vs 21 on the engraved control) |
| and the two counts are not comparable | it compares a **DETECTOR** count with a **TEMPLATE** count — incoherent rather than merely unfavourable |

⚠️ **REACH IS THE RESULT: three cautionaries exist in the whole committed
corpus, on one piece of music.** And the cheaper, higher-reach version — let the
detector's digit reader read cell 0 so no cautionary is needed — is **refuted**:
that reader forms an opening stack on **1 of 6 systems** and that one is `1/1`.
Its one right answer on the whole document IS the cautionary, so *its
correctness cannot be attributed to the reader being good.*

⚠️ **And the branch that looked safest is the one that converts an honest
abstention into a confident error**: `system/1/1` abstains on its opening and is
preceded by a cautionary reading `4/4` against a printed `6/8`. Filling
abstentions from cautionaries has reach **one** on this corpus, and that one
would be filled **wrong**.

**Structurally, this is the family's only genuinely independent witness of a
printed meter** — a DIFFERENT PHYSICAL PRINTING of the same fact, at the end of
the previous system. A toner blob ruins one printing, not both. That is an
argument about evidence structure, and it is not evidence.

---

## The meter that is NOT printed — carried, or derived from the bars

Not a symbol. A continuation system printing no time signature is the **normal
case** `[C28 + L41]` — Gould p.152: *"It holds good for a whole movement or up
to a change of metre."* This is the exact opposite of the clef and key
signature, which are reprinted every system, and it is why the two families need
opposite flags.

Produced by: `_carry_meter` (`OMR_METER_CARRY`, **default ON since 2026-09-15**)
and `_meter_from_bars` (`OMR_METER_FROM_BARS`, **default ON**).

### 1. What sets it apart — and what it is confused with

There is no ink. **The absence is itself the statement**, and
`docs/exploration-what-is-on-the-page-2026-09-09.md` §C1.3 already names this
as the pipeline's best-handled case of that kind: *"No clef / key / meter on a
continuation system means UNCHANGED. Already handled, and handled well —
`source='carried_from_previous_page'` tags the carry so it cannot be mistaken
for a reading. **This is the precedent every other entry here should copy**…
an inferred value is kept, and it is labelled with the fact that it was
inferred."* The staged path keeps that discipline in `reason=` (`carried` /
`derived_from_bars`) and in `pages_since_read`.

What must still be distinguished is **which absence this is**:

| the absence | what it means | how the pipeline tells |
|---|---|---|
| a continuation system | carry the last meter that was READ | the normal case |
| a new movement | the old meter must NOT cross | ⚠️ **no movement detector, and none is needed — the bars refuse it.** Litolff p.63: the carried `2/4` is refused at **−6.0** while the same bars name **3.0 at +5.0**, the printed `3/4`. |
| a page too badly read to say | abstain | ⚠️ the *Andante* refusal is **SAFE but NOT discriminating** — scored against the `3/8` that page actually prints it refuses **that too** (−1.0 and −1.0). A noisy page refuses everything. |

**Confused with, on the bars side:** two engravings that share a bar length.
`2/4` and `4/8` are one length; `3/4`, `6/8` and `12/16` are one length. **No
arithmetic separates them**, which is why `_meter_from_bars` names the LENGTH
and borrows the FORM from a system that actually read one — and abstains
`bars_name_a_length_without_a_form` when there is none, recording the length,
the support and every spelling it could be.

⚠️ **A lone whole rest is never counted as evidence here**, for two reasons and
both are real: the glyph stands for THE BAR whatever the meter, so its 4.0 is
our own default *for want of a meter* and counting it reads that default back as
evidence (measured on p.17: left in, **13 of 17** agreeing bars vote 4.0 and the
true 1.5 gets none); and `size_measure_rest` supersedes exactly those durations
using the meter, so touching them puts them in the meter's own basis.
⚠️ The guard is stronger than "a lone one": **ANY** whole rest disqualifies the
bar, because `Q.EVENT`'s grouping and `size_measure_rest`'s population can
disagree about whether a rest is alone.

### 2. Best method: YOLO / CV / other

**Neither — it is arithmetic, plus a provenance rule about where a spelling may
come from.** Both mechanisms are signed-term sums in one currency:

```
_carry_meter          carried_from_read_meter  +1.0
                      each bar that FITS       +1.0
                      each bar that does NOT   -1.0
                      floor 2.0, min 2 bars, min 3 staves per bar

_meter_from_bars      same bar weights, imported not restated
                      floor 4.0
```

⚠️ **The ordering is STRUCTURAL, not tuned, and is asserted on the constants:**
two net contradicting bars outweigh ANY carry, and no amount of carrying
outweighs the bars. Sean's rule that *"the math that can be determined by its
own equation"* outranks what can only be derived.

⚠️ **The carry never chains** — `METER_SOURCE_REASONS = ("voted",
"change_only")` admits only verdicts built from ink on the source's own page, so
`pages_since_read` is the true distance back to ink.

⚠️ **The carry takes the source's END meter, not its opening.** Reading the
opening handed Brahms 1 i the ONE-bar `9/8` instead of the `6/8` governing seven
of eight bars, and Brahms 1 iv a `C` instead of the `¢` the same system had just
read on 24 staves of 24.

**A third method exists and is unbuilt: a metre signal from BEAM GEOMETRY.**
This is **A-DUR-6 item 6** (*beat subdivision agrees with the meter*, ❌ not
built) and convention `[L22]` arriving from two directions — a beam group is a
metrical unit, so beam boundaries are beat boundaries, and notes are not beamed
over the middle of the bar. ⚠️ The association such a rule needs now exists: a
note is joined to its beam by its STEM (A-DUR-8). The exploration doc states
the same thing as an absence (§C1.6: *"No beam between two eighths — they are
flagged instead, which says something about beat grouping, which says something
about the METER. Beaming is meter evidence the meter vote does not consult."*). **It does not
share the bars' failure mode** — it needs no duration arithmetic at all. It is
LITERATURE ONLY, `Code: no consumer found`, and ⚠️ Gould explicitly records that
the mid-bar prohibition **is not historical**: *"Music from the Classical and
Romantic periods frequently uses this beaming"* — which is precisely the
repertoire this project reads.

### 3. Where on the page the deciding information lives

**In the bars of this system**, and nowhere else for the bars reader (every term
comes from inside one system, which is why it cannot cross a movement boundary
and the carry can). For the carry: **in an earlier system's ink**, plus this
system's bars as the arbiter.

⚠️ **Bar assessability falls with DENSITY, not with print quality** — 100% /
100% / 78% / **33%** over four systems as events per bar go 1.0 / 1.5 / 3.1 /
**4.5**. These mechanisms are strongest exactly where the music is SPARSE.

### 4. Stage by stage

All of it is ADJUDICATE, inside `adjudicate_meter`'s fallback ladder
(`_meter_fallbacks`, `rhythm.py:2310`), ordered **by what each rung KNOWS**:

1. a CARRY the bars corroborated — it names an engraving that was read;
2. this system's OWN BARS — self-checking arithmetic;
3. a CHANGE printed on this system;
4. failing all three, **the most INFORMATIVE refusal, which is not the last one
   tried**.

⚠️ These were once chained with `or`, and `_carry_meter` returns a truthy
`Ruling` when the bars REFUSE it — so **a refusal blocked every rung behind it**,
including a meter change printed on that same system. Measured on Litolff p.63,
the exact case the mechanisms exist for.

EVALUATE and EXPORT treat a carried or derived meter exactly like a read one,
with one exception: **the LETTER is never borrowed.** `raw` reaches the export
as `symbol="common"`, a positive claim that a `C` is printed on a system that
printed nothing we could read — so a borrowed meter is spelled in digits and the
source's own `raw` is recorded beside it.

### 5. Abstain or best-guess — and what leans on this

**(a) It abstains, in five distinct named ways**, and the distinctions are the
point: `carry_not_corroborated` (nothing to check against),
`carry_outweighed_by_the_bars` (the bars refused it),
`carry_source_uncorroborated` (every source back to the document's start had
nothing corroborated to hand on, **naming the sources it walked past**),
`bars_name_a_length_without_a_form`, and `no_evidence`.

⚠️⚠️ **AND ON THE ONE DOCUMENT IN THE CORPUS THAT BOTH ABSTAINS *AND* MISREADS,
THE ABSTENTION IS THE RIGHT ANSWER ARRIVING WITH NOWHERE TO GO.** Brahms 1 /
Breitkopf, `system/3/0`, newest generation:

```
BARS arm   ABSTAIN  bars_name_a_length_without_a_form
           length 3.0   support +7.0   (floor 4.0)   agree 8 / disagree 1
           bar_lengths_seen {3.0: 8, 5.0: 1}

CARRY arm  ABSTAIN  carry_outweighed_by_the_bars
           carried_from system/0/0  (the system that misread `C`)
           support -8.0  agree 0 / disagree 9
```

**3.0 IS 6/8, the printed meter.** The bars have the right answer at +7.0, above
their own floor, and the pipeline abstains anyway — because the printed FORM may
only be borrowed from a preceding system whose meter was read **and whose length
already matches**, and the only candidate source read `C` = 4.0. **The misread
poisons the borrow.** That rule is right to refuse; inventing `6/8` from a
length would be the laundered guess its own docstring bans. But it means
`bars_name_a_length_without_a_form` **is not a rare fallback here — it is the
outcome on the fixture the flags were held off for.**
(**MEASURED HERE**, `benchmarks/omr-meter-abstain-and-misread-2026-09/FINDINGS.md`
§5; I reproduced the two rows from `out/m7p0p3-BARS.meter.json` and
`out/m7p0p3-CARRY.meter.json`.)

⚠️ This is also the **first and only observation in the thread of the bar
arbitration doing the exact job the flag was held off for** — positively naming
the right length rather than falling silent. On the weaker second instance
(`brahms1scan`) the bars refuse the carry at −1.0 while naming **4.0**, which is
neither the truth (3.0) nor the misread (9.0): the safe-but-not-discriminating
shape. **The two must not be pooled.**

**(b) What leans on it, and the independence check.**

Everything the printed meter feeds — rest sizing, `reconcile_duration`, bar
fill, `measure="yes"` — plus one more thing that is specific to the carry: it is
a **document-wide** claim. `OMR_METER_CARRY` going default-ON is what turns a
misread change from a one-system fact into a document-wide one, which is why
A-METER-6 landed with it.

⚠️⚠️ **THE CYCLE, NAMED PRECISELY.** It is one loop, unrolled once, and both
halves are declared in the tree:

```
Q.DURATION decided   (ORDER position ~32, adjudicate.py)
      |  _bar_lengths_for -> _score_bars -> the signed terms
      v
Q.METER decided      (ORDER position ~64 — DURATION comes first)
      |  consequences.reconcile_duration (single_pass=True)
      v
Q.DURATION revised   — at most ONE note per bar, landing EXACTLY on the meter,
                       and only where the answer is UNIQUE
```

`reconcile_duration` carries `single_pass=True` and a stated bound, because the
fixpoint guard refuses a loop it cannot see terminating. *"Vote once, repair
once."* **It goes silent where more than one re-reading lands the bar exactly** —
which is what keeps it in EVALUATE rather than INFER.

**What is independent of this loop:**

| candidate witness | independent? |
|---|---|
| the other staves of the system | ⚠️ **NO for the reading** — the `9/4` is unanimous on all 10 staves that spoke. One reader, one typeface, twelve copies. |
| the bar sums | ⚠️ **NO** — the case that most needs the arbiter is the case where the arbiter is silent (0 of 7 bars clear the quorum on the `9/4` system). |
| the cautionary | ✅ **YES in structure** — a different physical printing. But n = 3 in the whole corpus, and the contest is incoherent (§ cautionary). |
| beam geometry `[L22]` | ✅ **YES in structure**, and **unbuilt**. |
| **the dossier** (`source_kind: catalog` / an encoding's own meter) | ✅ **YES — it does not come off this raster at all.** ⚠️ **AND IT HAS NO PRODUCER.** `Q.DOSSIER_FACT` is an inert `wants` on `adjudicate_meter`, `--dossier` does not exist on the staged CLI, and the exclusion is deliberate (a dossier is built from the truth MusicXML). The catalog `works` tier, which IS admissible, carries **instrumentation and not meter**. |
| `Q.INK` | ✅ **YES** — and it already holds a row for the printed meter on **17 of 17 staves** of Litolff p.62 cell 6, **16 of 17 unclassified**, where the detector has none. **Read by nothing.** |

**So the honest answer to "does the pipeline say *I don't know* on a continuation
page?" is: yes, and with more precision than any other family here — five named
abstention reasons, each carrying its support, its bar counts and the sources it
walked past. What it cannot do is use the one witness that would not fail with
the raster, because that witness has no producer.**

---

## Sean's own target model for this family — status, not a restatement

`tools/omr/staged/ASSUMPTIONS.md` **A-DUR-6** records his design verbatim: *a
meter is decided PER BAR, from layered evidence, in a stated order.*
**Persistence by default; a change must be argued for.** Cited rather than
re-derived; what is added here is the status column checked against this tree.

| # | Sean's evidence | today |
|--:|---|---|
| 1 | a meter glyph at this bar | ✅ `Q.METER_GLYPH`, gathered at every cell |
| 2 | meter glyphs at the same bar on other staves | ✅ voted in `_meter_changes` |
| 3 | this bar's own duration sum | ✅ `_bar_lengths_for` |
| 4 | the same bar's sum on every other staff | ✅ the per-bar modal vote |
| 5 | the surrounding bars' sums | ⚠️ PARTIAL — forward of a candidate only (`_bar_run`), plus the whole system's bars as a proposer of the LENGTH (A-DUR-7) |
| 6 | beat subdivision agrees with the meter | ❌ not built. Beams are gathered; grouping is not read |
| 7 | undefined blobs of ink | ⚠️ GATHERED (`Q.INK`, default ON) and **consumed by nothing, deliberately** |

Three carried constraints, each paid for by a measurement and none of them
mine: **the run must be DIRECTIONAL** (bars after a candidate are evidence for
the NEW meter; a symmetric ±4 window blurs the boundary it is meant to find);
**a run may propose only a LENGTH**, and consecutiveness turned out to measure
the page's legibility rather than its meter, so the evidence ACCUMULATES
instead; and **evidence still has to be independent** — ten bars whose
durations all trace to one misread beam level are ONE signal.

⚠️ **Two entries in A-DUR-6's own addendum need correcting against this tree:**

* **The double barline.** A-DUR-6 already corrected its own first estimate —
  `Q.BARLINE_COLUMN` is a per-staff COUNT of cells cut, not positions and not
  types, and the repo has no barline-type classification at all — so this needs
  new CV *and* a new quantity. That correction stands. ⚠️ **It is still the
  most attractive unbuilt witness in the family**, because it is read by a
  reader that does not fail with the meter ink: Litolff p.62 prints a **double
  barline** at cell 6, exactly where the meter is printed and where the
  detector fires nothing.
* ⚠️⚠️ **The tempo word is NO LONGER BLOCKED, and A-DUR-6 says it is.** That
  entry reads *"a tempo word at that bar ("Tempo I.", "Allegro") … blocked only
  on `direction` being a stub."* `adjudicate.stubs()` is now **`()`** — I ran
  it — and `direction` graduated on 2026-09-11. **And the case is the same
  page**: the crop of Litolff p.62 shows the double barline *"under **Tempo
  I.**"*, at cell 6. So on the one page where every meter reader fails, **two
  independent markers of the section boundary are present in the print, one of
  them now readable, and nothing joins either to the meter.**

---

## What we do not know

1. **Whether the template-at-bar reader can read a REAL mid-staff change.** No
   page in reach prints one. The false-positive side is measured at 1,612
   windows; the true-positive side has never been observed.
2. **What `OMR_METER_CARRY` costs end to end.**
   `benchmarks/omr-meter-corroboration-2026-09/local_arm.sh` is written and
   **has never been run**. The misread `9/8 → 9/4` opening is untouched by the
   corroboration guard — there the majority is wrong, and asking for a second
   witness gets ten. **The flip makes that misread travel.**
3. **Whether raising `min_score` from 0.50 would help.** The absolute score has
   an empty interval on the one case (TRUE 0.744–0.781, the FALSE one 0.514,
   nothing between 0.531 and 0.656). Not shipped because `min_score` is shared
   with the legacy path and was set on an 11-source corpus; moving it on 7
   correct / 1 wrong over 4 documents is tuning on a fraction of the evidence.
4. **Whether a SIZE gate would refuse the Litolff fragments — half of this is
   now measured, and the measured half REFUTES the obvious gate.**
   `benchmarks/omr-family-positions-2026-09/FINDINGS.md` §4 ran the position
   fact over that exact page (10 rows, flag on):

   * **HEIGHT does not separate.** The staff-11 pair measures **4.16 and 4.34
     steps** — i.e. 2.08 and 2.17 staff spaces — **against a real digit's ~4
     steps** (Bravura `timeSig4` 2.004 sp). The fragments are if anything
     slightly *taller* than a real numeral.
   * **`half` does not separate either.** The pair comes out `upper` + `spans`,
     roughly one in each half of the staff, which is the printed-meter shape.
     Over the ten rows `half` reads `lower` 4, `upper` 3, `spans` 3.
   * **And the comparison that would settle it cannot be run**: it would ask
     whether the fact distinguishes cell 6 (two marks, two halves, 17 staves)
     from cell 8 (one stroke) — and **the detector fires nothing at cell 6**,
     so the comparison has one side. That is a DETECTION gap and no position
     fact reaches it.

   ⚠️ **So Sean's warning is not a caution here, it is the result**, and both
   `capture.py` and the family-positions findings withdrew an earlier draft
   that claimed geometry refuses these fragments. **What survives untried is
   WIDTH, and therefore ASPECT**: the fragments are **0.35–0.40 staff spaces
   wide** against Bravura's **1.720**, an aspect of roughly 5–6 : 1 against a
   real digit's 0.86 : 1. Nobody has measured whether that separates, on any
   corpus, and R6 says it must not be settled on one edition.
5. **The Litolff p.62 bar NUMBER.** The page prints `147` at its first bar and
   the pipeline segments 13 cells, so cell 6 is the page's seventh bar; the
   reference encodes the change at bar 155. Reconciling those needs a
   hand-verified `works.json` window row that does not exist.
6. **n throughout.** Four documents, two publishers, seven change segments,
   three cautionaries, one document with a real movement boundary measured on an
   ENGRAVED render. **No OMR-NED figure anywhere in this family, deliberately.**

## Questions for Sean

1. **The two readers are split by position on the page, not by quality** — the
   template never sees a change, the detector never gets a vote on the opening,
   and cell-0 detector glyphs are gathered and read by nothing. The detector
   reads `C`/`¢` *well* and digits *terribly*; the template reads digits *well*
   and has no `¢` at all. **Should each reader speak wherever it is good, with
   a declared normalisation between a SMuFL name and a `(num, den)` pair?**
   That normalisation is the reason the cross-reader group was parked (`D17`),
   and the park says it is *"plausibly the most valuable kind"*.
2. **You already said the position fact would not settle this, and the page
   agrees with you** — on p.62 the fragments come out one in each half, 4.16
   and 4.34 steps tall against a real digit's ~4. So the question is narrower
   than "wire the position fact": **the only untried geometric separator is
   WIDTH / ASPECT** — 0.35–0.40 staff spaces against Bravura's 1.720. Is that
   worth measuring, given R6 says it cannot be settled on one edition and the
   only page we have it on is Litolff?
3. **A cut-C cannot be checked by anything except ink.** `C` and `¢` are both
   4.0 quarter notes, so every arithmetic witness in the pipeline is blind to
   the difference, and we get 15 of 97 dossier works wrong if the stroke test
   fails. Is a second, independent reading of the stroke worth building, or is
   the 0.48 / 1.00 gap on 87 staves enough?
4. **The one witness that would not fail with the raster is the dossier, and it
   has no producer on the staged path** — correctly, because it is built from
   the truth file. Is there a *legitimate* external meter source (a catalog tier
   that is not an encoding of the page, the way the `works` roster is for
   instrumentation)? Today the catalog carries instrumentation and no meter.
5. **On the fixture that both abstains and misreads, the bars name the right
   LENGTH (3.0, +7.0 support) and we abstain because we cannot borrow a
   SPELLING.** Borrowing the form from a dossier, or from the work's own
   catalogued meter, is INFER-shaped work. **Is the right move to let INFER
   spell a length the bars have already named — labelled as inferred — or to
   leave it abstaining?**
6. **`report_boundary.TRUTH_CHANGES` still records Litolff p.62's change at
   cell 8**, and the crops put it at cell 6 with zero `timeSig*` there on any of
   17 staves. Correcting that truth file changes the TRUE/FALSE table every
   meter measurement in the repo is scored against. Should it be corrected now,
   or held until someone re-reads the page against a window row?
7. **A-DUR-6 says the tempo word is blocked on `direction` being a stub. It is
   not — `stubs()` is `()`.** On the one page where every meter reader fails,
   the print carries a **double barline** and **"Tempo I."** at exactly the bar
   the meter changes, and the tempo word is now readable. **Is "a section
   marker at this bar" the witness you want next for this family** — ahead of
   any further work on the digit readers — given it is the only candidate that
   does not fail with the meter ink or with the bar sums?

---

**Probe:** no transcribe run, no battery, no OMR-NED. Two things were run,
both seconds: a read of committed records —
`benchmarks/omr-staged-meter-boundary-2026-09/out/m7*.meter.json` (10 files,
newest generation) — to reproduce the per-system outcome / reason / segment /
cautionary table quoted above; and `adjudicate.stubs()`, which returns `()`
and is what falsifies A-DUR-6's tempo-word blocker. Everything else is read out
of the tree and the committed FINDINGS files.
