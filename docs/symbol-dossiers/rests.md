# Rests — one section per symbol

**2026-09-20.** Research, not repair. Nothing under `tools/` was changed.

**What this covers:** the nine rest classes the detector can emit, the dotted
rest, and the non-symbol that matters most here — the bar we read nothing in,
which leaves the file saying the same thing as a bar we read silence in.

## What is already answered elsewhere, and what this adds

Three documents answer parts of the five questions for this family. They are
cited, not re-derived, and where this dossier adds or disagrees it says so.

| document | what it already settles for rests | what this dossier adds |
|---|---|---|
| [`docs/position-grammar-confusables-2026-09-04.md`](../position-grammar-confusables-2026-09-04.md) | the mark alphabet and the rule that identity is position, not shape; the DOT roles; the BOWL/BLOB fragment cut; HORIZONTAL STROKE; VERTICAL STROKE; DIGIT | ⚠️ **it has no REST entry**, and whole-vs-half is the purest instance of its own principle — §Q1 of `restWhole` and `restHalf`. Three additions to its existing entries, below. |
| [`benchmarks/omr-family-positions-2026-09/FINDINGS.md`](../../benchmarks/omr-family-positions-2026-09/FINDINGS.md) + `staged/positions.py` + `staged/capture.py` | the per-family POSITION fact — *"which edge sits on which LINE, and on which side"* — with `attach_margin` keeping an ambiguous pick ambiguous; ten producers, no consumers, `OMR_FAMILY_POSITIONS` default OFF; its §11 ranks `Q.REST_POSITION → adjudicate_duration` as item 2 | the per-SYMBOL consequence: *which* rest values that fact decides (two), which it is irrelevant to (five), and what it would cost `size_measure_rest` to be wrong about it |
| [`docs/exploration-what-is-on-the-page-2026-09-09.md`](../exploration-what-is-on-the-page-2026-09-09.md) §B.1 | SILENT vs UNREAD is the ABSENT/DECLINED collapse in the musical content; the discriminator is cell ink coverage and it is unused | the exact decomposition of the population, and the **four** states the counters keep apart while the XML keeps none |

Sean's own warning from that second document governs every Q3 below: *"position
is an option for helping us determine something but will rarely be a clear rule
that determines by itself"* (`positions.py:328-330`).

Also read: `tools/omr/staged/ASSUMPTIONS.md` `A-DUR-5`, `A-DUR-6`, `A-DUR-7`.

## The documents, and the probe

Two committed staged records:

| short name | document | record | pages |
|---|---|---|---|
| **Litolff** | Beethoven 5 mvt 1, Litolff 1870, IMSLP `984073` | `library/_shared-records/beethoven5-p1-p4.record.json` | pdf 1–4 |
| **Breitkopf** | Brahms 1 mvt 1, Breitkopf & Härtel, IMSLP `317803` | `library/_shared-records/brahms1-breitkopf-p0-p3.record.json` | pdf 0–3 |

**A probe was used** — three greps, seconds, no transcribe run. The records are
pretty-printed one field per line, so it read them line by line and counted (a)
the value on every `Q.REST` row, (b) the `reason` on every duration verdict, (c)
which rest subjects also carry a `Q.GLYPH_BAND_DISTANCE` row (the cross-staff
contest). Findings marked **MEASURED HERE (probe)**. Its rest-row totals — 646
and 1,028 — reproduce the committed reach artefact
(`benchmarks/omr-family-positions-2026-09/FINDINGS.md` §5) exactly, which is the
control that says the read is right. Nothing was re-gathered, re-exported or
checked against a print.

### The population, which nothing in the repo had broken out

| class | Litolff | Breitkopf |
|---|--:|--:|
| `restWhole` | **395** | **398** |
| `rest8th` | 38 | **380** |
| `restQuarter` | 209 | 238 |
| `restHalf` | **1** | **3** |
| `rest16th` | 3 | 4 |
| `rest64th` | 0 | 1 |
| `restHBar` | 0 | 4 |
| `restDoubleWhole`, `rest32nd`, `rest128th`, `restHNr` | **0** | **0** |
| **total `Q.REST` rows** | **646** | **1,028** |

**MEASURED HERE (probe).** The totals and `restWhole`/`rest8th`/`restQuarter`
are published (`benchmarks/omr-shared-records-2026-09/FINDINGS.md` §4,
`benchmarks/omr-rest-sizing-2026-09/FINDINGS.md` §2a); the small classes are new.

Three things fall straight out and each has its own section:

1. **`restHalf` is 4 rows in 1,674.** The one discriminator the literature calls
   the rest's identity — whole hangs, half sits — has almost no population on
   either plate, so nobody has ever been in a position to check it.
2. **The value mix is a property of the PUBLISHER.** Litolff is 58% whole rests
   and 6% eighths; Breitkopf is 39% whole and 37% eighths. A constant read off
   one is read off a different population.
3. **Four of the nine classes never fire.** `restDoubleWhole` and `restHNr` have
   a duration-table entry and an abstention path and have never been exercised.

---

## `restWhole`

A short wide filled rectangle hanging under the fourth staff line from the
bottom. The commonest rest on both plates and, standing alone in a bar, it does
not mean four quarters — it means **that bar**. Produced by the YOLO detector
(class `restWhole`) and by nothing else.

### 1. What sets it apart — and what it is confused with

**Starting from the mark alphabet.** `docs/position-grammar-confusables-2026-09-04.md`
§2 lists DOT, ARC, WEDGE, HORIZONTAL STROKE, VERTICAL STROKE, DIGIT and
BOWL/BLOB — and **no REST**. ⚠️ **That is this dossier's first finding against
that document**, because a whole rest against a half rest is its own principle in
its strongest available form: one physical mark, two grammatical roles, and the
role decided by *which line it touches*, with the literature stating in terms
that no shape classifier can ever separate them. It belongs in §2 as its own
entry, and the entry it would most resemble is HORIZONTAL STROKE (tenuto vs
ledger line), which is also *"lies ON the lattice or does not"*.

Two facts separate a whole rest, and only the second is its identity.

| fact | separates it from | grade |
|---|---|---|
| **outline** — 1.128 × 0.576 staff spaces, w/h ≈ 1.96 | every *other value* of rest | LITERATURE (Bravura `glyphBBoxes`) `[C19 + L26]` |
| **which line it touches, and on which side** | `restHalf`, and nothing else | LITERATURE (SMuFL: the whole rest "should hang from the font baseline") `[C17 + L24 + L25]` |

The shape fact holds on our own ink: `restWhole` median aspect h/w **0.46, max
0.91** against `restQuarter`'s median 2.66, min 1.40 — **0 of 209 overlapping**
(MEASURED HERE, `benchmarks/omr-rest-sizing-2026-09/FINDINGS.md` §2a, Litolff,
n = 395 + 209). ⚠️ Two aspect conventions are in use and they are reciprocals:
that probe reports **h/w**, the shipped cuts in `rhythm.py` are **w/h**.

**What it is actually confused with, in order of measured size:**

* **A notehead — which is the BOWL/BLOB entry running in the direction that
  entry does not cover.** That entry is about hollow-notehead-shaped things that
  are not noteheads (the bowl of a *legato* "g", the lower bowl of a 6/8's "8",
  a clipped neighbour head). Here the traffic runs the other way: the detector
  calls a whole rest `noteheadBlackInSpace`. The decisive case is Litolff
  `p4/s0/st0` (Flauti, tacet mm 82–89): `glyph/4/0/0/1/2` is classed `restWhole`
  at h = 0.67 spaces, aspect 2.33; `glyph/4/0/0/3/1` is classed
  `noteheadBlackInSpace` at h = 0.79, aspect 2.22 — **the same ink in the same
  slot two bars apart, two class names** (MEASURED HERE,
  `benchmarks/omr-note-where-silence-2026-09/FINDINGS.md` §2). Of 26 bars whose
  whole exported content was one lone quarter in a 2/4 bar, **5 were a whole rest
  called a notehead**. And it runs both ways: the arc work found a `restWhole` at
  confidence **0.56** in a bar where the print shows no whole rest at all
  (`adjudicators/rhythm.py:3010`).
* ⚠️ **ADDITION TO THE BOWL/BLOB ENTRY, and it is a live constraint.** That entry
  ships `_drop_clipped_notehead_fragments`: *a notehead is a staff space tall;
  fragments run 0.29–0.56, genuine heads 0.60+, nothing between.* **A real whole
  rest is 0.576 staff spaces tall.** So the one filter in the pipeline that
  removes cell-edge slivers cuts at a height a whole rest fails, and it is
  restricted to `category == "notehead"` (`tools/omr/transcribe.py:544-571`).
  Extending it to rests as written would delete the family. The rest version has
  to be per-class, and nobody has tried it. MEASURED HERE (the 0.6 constant and
  the filter's scope, read from the tree); the Bravura height is LITERATURE.
* **A neighbouring staff's ink through the 4–6 space cell padding.** On
  Breitkopf **18.3% of `restWhole` detections stand outside their own staff**
  against Litolff's **3.5%**, and **64 sit more than a space BELOW** their staff
  where Litolff has **zero** (MEASURED HERE,
  `benchmarks/omr-second-publisher-pricing-2026-09/FINDINGS.md`). Of the 12
  glyphs `OMR_WHOLE_REST_INK` fired on there, hand adjudication read **8 as the
  upper hook of an eighth rest on the staff below**, 2 as real noteheads on a
  neighbouring staff, **1 as the top arc of the printed `6` of the `6/8`** — the
  DIGIT entry's *"type design moves under you"* arriving in this family.
* **A `restHalf`.** Not measured anywhere, because the population does not exist
  (1 and 3 rows). See the next section.

### 2. Best method: YOLO / CV / other

**Presence: YOLO, and it is already very good on clean ink.** Against exact
Verovio page truth over 11 engraved works the `rest` family scores precision
0.986 / recall 0.999 / **F1 0.993**, n = 929 truth against 941 predicted
(MEASURED HERE, `benchmarks/omr-reading-vs-reproduction-2026-09/FINDINGS.md`).
⚠️ That is family-level — *a rest is here* — not *this rest is a whole rest*.
**No instrument in this repo has ever scored the rest VALUE against a truth.**

**Identity (whole vs half): not a classifier at all.** It is a ruler reading, and
the literature says so directly `[C17]`. The right tool exists — `Q.REST_POSITION`
— and is unread; see §4.

**The shipped workaround is a two-witness rule** (`OMR_WHOLE_REST_INK`), and its
own measurement is the argument for the ruler: **SHAPE alone fires on 148 of
2,347 noteheads, POSITION alone on 310, together on 25 — all 25 cropped and
hand-read as whole rests** (MEASURED HERE,
`benchmarks/omr-note-where-silence-2026-09/FINDINGS.md` §3, Litolff).
⚠️ On Breitkopf the same rule fires 12 times and **1 is a whole rest**
(MEASURED HERE, `benchmarks/omr-second-publisher-pricing-2026-09/FINDINGS.md`).

### 3. Where on the page the deciding information lives

**Already answered per family**: `Q.REST_POSITION` — *which edge sits on which
LINE, and on which side* — comparative, both residuals kept, no threshold
(`benchmarks/omr-family-positions-2026-09/FINDINGS.md` §1; `positions.py:303`).

**Per symbol, a whole rest needs four more things and three have no reader:**

| where | what it decides | who reads it today |
|---|---|---|
| the **fourth staff line from the bottom** (step 5.5) | whole vs half | `WHOLE_REST_STEP` inside `OMR_WHOLE_REST_INK`; **not** `adjudicate_duration` |
| the **same staff, one or two bars away** — a tacet part prints one in every bar `[C18]` | whether ambiguous ink is a rest at all | `WHOLE_REST_NEIGHBOUR_BARS = 2` |
| the **rest of the bar** (is this the only event?) | whether it stands for the bar | `consequences.size_measure_rest` |
| the **meter in force** | its actual length | same |
| the **horizontal centre of the bar** `[L28]` | a bar rest is centred; ink at the bar's LEFT edge is a clef, key, meter or barline fragment | **nothing** |

⚠️ **The last row is not hypothetical and `ASSUMPTIONS.md` A-DUR-5 is the
receipt.** On Litolff p.62 the `timeSig3` + `timeSig4` detections sit at
`x_canonical = 0`, 0.33–0.40 staff spaces wide — *"a barline, at the head of an
empty rest bar"* — and the printed meter is at cell 6, where **zero `timeSig*`
detections exist on any of seventeen staves**. `[L28]` predicted that in advance
and nothing read it.

⚠️ **The slot is not reliable off a scan crop, measured twice.** The document's
own correctly-read whole rests spread over steps **2.5–5.9** against a nominal
5.5, because `Q.STAFF_LINES` models a staff as five ideal rows while a scanned
staff bows 8–17 page px across its width (MEASURED HERE,
`benchmarks/omr-note-where-silence-2026-09/FINDINGS.md` §3). Independently the
phantom-note census found the same printed mark reading step **3.78 → 5.18 across
seven consecutive bars** of one staff — *more than the 1.0-step gap between a
whole rest and a half rest* (MEASURED HERE,
`benchmarks/omr-phantom-notes-2026-09/FINDINGS.md` §5.3).

### 4. Stage by stage

| stage | what happens | where |
|---|---|---|
| **GATHER** | one `Q.REST` row per detection whose class starts `rest`, with the canonical box, the page box (declined, never defaulted) and the detector's confidence. **No filter of any kind.** | `gather.py:887-888` |
| **GATHER** | a `Q.GLYPH_BAND_DISTANCE` row where the same class overlaps on two staves of a system at IoU ≥ 0.5 | `gather.py:584-601` |
| **GATHER** | `Q.REST_POSITION` — behind `OMR_FAMILY_POSITIONS`, **default OFF**; zero rows on both records | `positions.py:303` |
| **ADJUDICATE** | `Q.DURATION` via `_rest_ruling`: the value is the class name through `rhythm._REST_DURATIONS`, imported not restated → 4.0, `written_type: "whole"` | `adjudicators/rhythm.py:579` |
| **ADJUDICATE** | `Q.NOTEHEAD_IS_A_WHOLE_REST` — runs on **noteheads**, asks whether *that* ink is a whole rest | `adjudicators/rhythm.py:3001` |
| **ADJUDICATE** | `Q.EVENT` — a rest is its own event; `Q.ONSET_COLUMN` then uses its x as an instant on the system | `adjudicators/rhythm.py:780`, `:2513` |
| **ADJUDICATE** | `Q.GLYPH_OWNER` decides its staff where a contest exists | `adjudicators/ownership.py` |
| **EVALUATE** | `size_measure_rest`: a bar whose **only** standing duration is **one dotless `restWhole`**, and whose **meter is decided**, has that duration rewritten to the bar's length and marked `measure_rest` | `consequences.py:123` |
| **EVALUATE** | `reconcile_duration` explicitly **skips rests** — a rest carries no beam to re-read, and a 4.0 whole rest in 2/4 would "land exactly" on 2.0 for the wrong reason | `consequences.py:298-307` |
| **INFER** | nothing reads a rest. Both duration rules name *"a rest the detector never read"* as a way they can be wrong, and refuse any witness whose provenance touches `Q.METER` — which excludes every duration `size_measure_rest` handed out | `inferences.py:342`, `:484` |
| **EXPORT** | `<rest measure="yes"/>` with **no `<type>`** where `measure_rest` is set; a plain `<rest/>` + `<type>whole</type>` otherwise | `staged/export.py:759`, `export.py:1059` |

**Reach of the consequence, exactly:** `size_measure_rest` fires on **92 of 92**
eligible bars where the meter is decided and **0 of 195** where it abstained — an
empty interval, and the reason the rule has no fault (MEASURED HERE,
`benchmarks/omr-rest-sizing-2026-09/FINDINGS.md` §1c). The records' own verdict
counts: **92** `whole_rest_means_the_bar` on Litolff, **105** on Breitkopf
(MEASURED HERE, probe).

⚠️ **Three things that do NOT happen, and each is a finding.**

1. **`Q.REST_POSITION` is exactly the fact that decides whole vs half, and is
   read by nothing.** `capture.py` classes `rest` as a **`gather_only`** family —
   *"a family whose quantity IS a gather quantity: the ink row is the whole
   answer and there is nothing declared to follow"* (`capture.py:1554`). That is
   the architecture saying out loud that this family never makes a decision about
   what it is. Both committed records carry **ZERO** `rest_position` rows
   (MEASURED HERE, probe). This agrees with, and is the per-symbol form of,
   `benchmarks/omr-family-positions-2026-09/FINDINGS.md` §11 item 2.
2. **`Q.NOTEHEAD_IS_A_WHOLE_REST` is decided before `Q.DURATION` and `Q.EVENT`
   and is read only by the exporter.** `grep -rn 'Q\.NOTEHEAD_IS_A_WHOLE_REST'
   tools/omr/staged/` returns the declaration, the producer, the `ORDER` entry
   and one reader, `export.py:660`. So a glyph the pipeline has decided is a whole
   rest still gets a note's duration, still joins the event grouping, and still
   votes in the bar sums. `adjudicate.py:783-789` says so in terms.
3. **The staged path has no rest filter; the legacy path has three.**
   `rhythm.resolve_rhythms_for_cell` drops a rest more than 2 line-spacings above
   or below the staff, a rest whose x-centre sits under a notehead, and a second
   rest of the same class within a notehead's width of one already kept
   (`tools/omr/rhythm.py:1471-1527`). None of that runs on the staged path.

### 5. Abstain or best-guess — and what leans on this mark's certainty

**(a) Can it abstain?** Per-value, no — `_rest_ruling` decides on every row it is
given, and on both records every `restWhole` row got a `rest_class` verdict (646
of 646 Litolff, 1,024 of 1,028 Breitkopf, the 4 being `restHBar`; MEASURED HERE,
probe). It has **no way to say "this ink might not be a rest"**, because the class
name arrived as an observation, not a decision.

The *bar-length* half abstains properly: no meter, no assertion — the consequence
returns `[]`, the exporter withholds `measure="yes"`, and `_measure_rest_beats(None)`
falls back to 4.0 with its own comment saying why (`export.py:145-156`). That is
why the fault Sean saw is a **meter** fault in a rest's costume: with the meter
unsettled on 6 of 7 systems, rests at 4.0 ql in a 2.0 ql bar number **471**;
settling it takes them to **115**, rests at 2.0 from 109 to **465**, and bars that
add up from **38.0% to 69.2%** (MEASURED HERE,
`benchmarks/omr-rest-sizing-2026-09/FINDINGS.md` §3b/§3c).

**(b) What leans on it, and does it fail on the same pages?**

* **The METER leans on it by NOT reading it, which is the loop closed.** A lone
  whole rest's 4.0 is *our own default for want of a meter*, so counting it in a
  bar sum reads that default back as evidence — measured on Litolff p.17, left in,
  **13 of 17 agreeing bars vote 4.0 and the true 1.5 gets none**
  (`ASSUMPTIONS.md` A-DUR-6; `adjudicators/rhythm.py:1197-1213`).
  `_bar_lengths_for` therefore excludes **any bar holding a whole rest at all**.
  Cost: that exclusion removes **17 to 111 bars per system**, leaving 6 to 17
  assessable (MEASURED HERE, `benchmarks/omr-rest-sizing-2026-09/FINDINGS.md` §4).
* ⚠️⚠️ **AND THE EXCLUSION SILENTLY DISABLES THE METER-CHANGE CORROBORATOR AT
  EXACTLY THE BARS THAT MATTER.** `ASSUMPTIONS.md` A-DUR-6: *"the bar-math
  corroborator contributed 0 fit / 0 not even on the case that works, because the
  whole-rest exclusion removes exactly the post-change bars — a change is
  typically followed by most instruments resting."* So the guard that keeps the
  loop honest also blinds the one check that could confirm a printed meter
  change. That is the sharpest instance of *the bars are not an independent
  umpire* in this family, and it is a property of rests specifically.
* **A bar's existence leans on it.** `transcribe._drop_furniture_measures` deletes
  a leading or trailing measure column where **not one staff of the system carries
  a notehead or a rest** — *"a genuine measure on even a fully tacet staff
  contains its whole-bar rest"*. Measured over 243 columns, 27 systems, 20
  transcriptions: exactly 2 such columns, 0.82%, both furniture
  (`tools/omr/transcribe.py:3635-3670`). A systematically missed rest would make
  real bars deletable.
* **INFER leans on its absence.** `collapse_duration_to_barline` and its sibling
  both list *"the note may be followed by a rest the detector never read"* as a
  way the answer is wrong (`inferences.py:342`).
* **`Q.ONSET_COLUMN` counts a rest as an onset** — `Q.EVENT` includes rests and
  the column layer groups event verdicts (`adjudicators/rhythm.py:2536`). A
  phantom rest puts a false instant on the system.

**Independence: poor, and stated rather than dressed up.** The neighbour witness
is *"not independent of the DETECTOR, only of THIS GLYPH"* (`record.py:812-815`).
The absolute slot is read off `Q.STAFF_LINES`, shared with every other reader. And
`benchmarks/omr-family-positions-2026-09/FINDINGS.md` §2 names the residual
correlation that `Q.REST_POSITION` would *not* escape either: the grid is
independent, **the box is the detector's**. The Breitkopf result is that hazard
made concrete — there the neighbour witness corroborates cross-staff crop
contamination **with more of the same**, which is why its split goes
`slot 20 / neighbour 5` → **`slot 1 / neighbour 11`** and its accuracy 25/25 → 1/12.

---

## `restHalf`

The same rectangle as a whole rest, sitting **on** the third line instead of
hanging under the fourth. Produced by the YOLO detector (class `restHalf`).

### 1. What sets it apart — and what it is confused with

**Nothing about its shape.** Bravura gives `restWhole` and `restHalf` *exactly*
the same box — **1.128 × 0.576 staff spaces** — and states the registration
difference directly (LITERATURE, SMuFL + Bravura, `[L24 + L25]`). The only
separating fact is which line the rectangle touches and on which side: whole runs
y = −0.540 to +0.036 about its staff position, half y = −0.008 to +0.568.

It is therefore confused with **`restWhole` and with nothing else**, and the
confusion is invisible to every shape-based check the repo owns.

⚠️ **This is the missing entry in the mark alphabet, and it is the cleanest case
in it.** `position-grammar-confusables` opens with Sean's own example — *"slurs
and ties look exactly the same; what makes them different are the notes they
connect"* — and its ARC entry admits an ambiguity floor (a two-note phrasing slur
on a repeated pitch is undecidable from print alone). **The whole/half pair has
no such floor**: the engraver has no freedom, SMuFL states the registration, and
the answer is a single geometric comparison. It is the strongest available
illustration of that document's thesis and it is not in it.

⚠️ **THE HEADLINE OF THIS SECTION IS THE POPULATION.** The detector emitted
`restHalf` **1 time on Litolff and 3 on Breitkopf, out of 1,674 rest rows**
(MEASURED HERE, probe). Against that, `restWhole` is 793. Two readings fit: the
plates genuinely print almost no half rests (plausible — a silent bar takes a
whole rest whatever the meter, so a half rest appears only *inside* a bar), or
**half rests are being read as whole rests and nothing can see it**. ASSERTED —
nobody has looked, and the one instrument that could is off.

The cost of the second reading is not symmetric. A half rest misread as
`restWhole` and standing alone in its bar becomes `size_measure_rest`'s
population, and its duration is rewritten to **the whole bar** — in 4/4, double.

### 2. Best method: YOLO / CV / other

**Not YOLO.** A model reporting confidence in `restWhole` vs `restHalf` from a
crop is reporting something it cannot know `[C17]`.

**A ruler**, and it is built: `positions._rest_discriminator` measures both box
edges against the staff's own line positions and compares the residuals. It
carries **no threshold** by design — the attachment is comparative, both
residuals are kept, `attach_margin` records how decisive the pick was, and an
exact tie records `attached_edge: None`
(`benchmarks/omr-family-positions-2026-09/FINDINGS.md` §3).

⚠️ **The ruler needs a straighter staff than a scan gives.** Same evidence as
`restWhole` §3 — the recorded step drifts 1.4 steps across one system while the
gap to resolve is 1.0 step. So the usable form is the comparative one measured
against the **local** line, which is what `_rest_discriminator` already does and
what the absolute-slot witness inside `OMR_WHOLE_REST_INK` does not.
`OMR_CELL_LINE_TRACE` (default ON) already slides each cell's grid onto the ink
beneath it for exactly this class of problem.

### 3. Where on the page the deciding information lives

**Already answered per family** (`Q.REST_POSITION`). Per symbol: the **third
staff line from the bottom**, and the rectangle's own top and bottom edges
relative to it. Nothing else on the page is relevant — not the bar's other
contents, not the meter, not the neighbours. LITERATURE `[L24]`.

⚠️ **Multi-voice writing destroys it.** In two-voice writing rests are displaced
from their default position on purpose (LilyPond `Rest` `(voiced-position . 4)`),
which removes the absolute-position discriminator and leaves only the relation to
the surrounding voice (LITERATURE, the known exception on `[C17]`). This pipeline
decides `Q.VOICES` **after** `Q.DURATION` (`adjudicate.py` ORDER), so at the
moment a rest's value is read nobody knows whether the bar is one voice or two.

### 4. Stage by stage

Identical plumbing to `restWhole` — one `Q.REST` row at `gather.py:888`, a
`rest_class` verdict reading `_REST_DURATIONS["resthalf"] = (2.0, "half")`, and a
`<rest/>` + `<type>half</type>` at export.

**The differences are all absences:**

* `size_measure_rest` will **not** fire on it — the glyph is part of the rule
  (`consequences.py:169`), a restriction that cost 34 edits to learn
  (`benchmarks/omr-rests-2026-09/FINDINGS.md` §9).
* `adjudicate_notehead_is_a_whole_rest` says *whole rest* or nothing; there is no
  half-rest counterpart, and its shape window would accept one.
* **Nothing anywhere compares a `restWhole` verdict against a `restHalf`
  hypothesis.** `_rest_ruling` takes `max(rest_rows, key=score)` over rows on
  **one glyph subject**, so it resolves nothing across glyphs.

⚠️ **And the staged path's NMS makes the two classes non-competing.**
`gather.py:292` calls the detector without `agnostic_nms`, taking the default
`False`, where `transcribe()` passes `True`. Class-wise NMS never compares
`restWhole` with `restHalf`, so if the model fires both on one piece of ink,
**both survive as separate `Q.REST` rows with separate duration verdicts** — the
mechanism measured on noteheads, where one head survives as three rows at IoU
0.91–0.96 (MEASURED HERE for noteheads,
`benchmarks/omr-staged-dedupe-2026-09/FINDINGS.md` §6.1; ASSERTED for rests —
Litolff has 15 same-cell rest duplicate pairs and their classes were not broken
out).

### 5. Abstain or best-guess — and what leans on this mark's certainty

**(a)** No abstention exists and none is possible today: the class name is an
observation, so *whole* and *half* are not two answers to one question — they are
two subjects' names. The tie case a ruler would need is already implemented and
records a tie as a tie (`positions.py:340-343`).

**(b)** Because the population is 4 rows, almost nothing leans on `restHalf`
today — but everything that leans on `restWhole` is exposed to a half rest being
*read as one*. Specifically `size_measure_rest`: a half rest alone in a bar is a
bar we read one symbol of, not a silent bar, and the whole reason the rule demands
the whole-rest glyph is that the first cut without it inflated exactly this case.

Independence: the ruler and the classifier read the **same box** off the **same
raster**, so they fail together on bled or clipped ink — the correlation
`benchmarks/omr-family-positions-2026-09/FINDINGS.md` §2 names and does not
escape. What the ruler adds is not a second witness; it is *the right measurement
instead of the wrong one*.

---

## `restQuarter`

A tall narrow squiggle spanning most of the staff. The second commonest rest on
both plates. Produced by the YOLO detector.

### 1. What sets it apart — and what it is confused with

**Its proportions, and they separate cleanly.** Bravura 1.076 × 2.992 staff
spaces, h/w ≈ **2.78** — more than 5× a whole rest's 0.51 (LITERATURE, `[L26]`).
On our own ink: `restQuarter` median h/w **2.66, min 1.40**; `restWhole` median
**0.46, max 0.91** — **0 of 209 overlapping**, at the **highest median confidence
of any rest class** (0.71 against `restWhole`'s 0.61 and `rest8th`'s 0.48)
(MEASURED HERE, `benchmarks/omr-rest-sizing-2026-09/FINDINGS.md` §2a, n = 209).

⚠️ **That separation is ONE-SIDED and establishes nothing positive** — which is
the same warning the mark-alphabet document gives for every shape cut. A tall thin
box is not thereby a quarter rest. The same document fires **`arpeggiato` 377
times** on what the record itself calls *"a stem or a barline"* — the identical
shape (MEASURED HERE, CLAUDE.md; `[C19]` known exceptions).

**What it is confused with,** mapped onto the mark alphabet's **VERTICAL STROKE**
entry (stem vs barline), which this adds a third role to:

* **A stem, a barline fragment, or `arpeggiato`.** Measured only in the reverse
  direction (`arpeggiato` firing on stems and barlines), n = 377 on Litolff.
  ⚠️ The VERTICAL STROKE entry calls its own case *already solved — classical CV
  owns both marks, the model never had to*. That is true of stems and barlines
  and **not** of `restQuarter`, which is a model class living in the same
  geometric neighbourhood with no CV counterpart and no span test.
* **The upper half of an eighth rest.** Not measured.
* **Ink from the staff above or below through the cell padding.** Rare for this
  class: only **2 of 646** Litolff rest rows carry a cross-staff contest at all
  (MEASURED HERE, probe) — see `rest8th` §1, where the rate is 30× higher on the
  other publisher.

### 2. Best method: YOLO / CV / other

**YOLO, and it is the right tool.** A distinctive outline, the family's highest
confidence, and a family-level reading F1 of 0.993 on engraved pages. A CV rung
would be re-deriving a shape test the model already passes.

**The useful CV addition is not a classifier but a sanity check the repo already
owns and does not run**: h/w against the Bravura ordering. A `restQuarter` box
measuring under 1.40 is either a misread or a clipped glyph, and nothing asks.

### 3. Where on the page the deciding information lives

**Already answered per family** — and for this symbol the per-family position
fact is *irrelevant*, which is worth saying: `Q.REST_POSITION` decides whole vs
half and nothing else. A quarter rest's identity is its outline.

* Its **vertical position carries no pitch information** and must not be read as
  one — a rest is centred on or about the middle of the staff `[L29]`
  (LITERATURE, Gould p.284).
* ⚠️ **Its x IS meaningful even though its y is not**: a rest that is part of a
  beat aligns horizontally with adjacent notes (LITERATURE, Gould). That is the
  one piece of rest evidence `Q.ONSET_COLUMN` could use, and the exploration doc
  named it — but `Q.EVENT`'s tolerance is measured off the bar's own *noteheads'*
  widths, so a rest gets a column position without contributing to the tolerance.

### 4. Stage by stage

The `restWhole` plumbing, with one branch missing and one hazard removed:

* **GATHER** → `Q.REST` row, no filter.
* **ADJUDICATE** → `rest_class`, 1.0 quarters, `written_type: "quarter"`.
* **EVALUATE** → `size_measure_rest` **cannot** fire (glyph must be `restWhole`).
  This is the 34-edit lesson: the first cut of the legacy rule accepted any lone
  rest and inflated bars holding a single detected quarter rest from 1.0 to 4.0
  (MEASURED HERE, `benchmarks/omr-rests-2026-09/FINDINGS.md` §9,
  `brahms-sym4-mvt1` pooled 0.1214 → 0.1225).
* **EVALUATE** → `reconcile_duration` skips it, like every rest.
* **EXPORT** → `<rest/>` + `<type>quarter</type>`.

⚠️ **The 218 lone-quarter-rest bars are the population Sean's sentence most
literally names and they are NOT the whole-rest fault.** Of 1,183 exported
measures, **19 short bars hold exactly one quarter rest and nothing else**
(MEASURED HERE, `benchmarks/omr-rest-sizing-2026-09/FINDINGS.md` §2b), and the
1.0-ql rest population **does not move by one row** when the meter is settled
(218 → 218, §3b). The two faults are disjoint.

### 5. Abstain or best-guess — and what leans on this mark's certainty

**(a)** No. It decides on the class name. There is no shape check, so a
`restQuarter` verdict on a stem fragment is indistinguishable from one on a
quarter rest.

**(b)** A quarter rest contributes **1.0 to its bar's sum**, and the bar sum is
what corroborates a carried or derived meter. Unlike a whole rest it is **not
excluded** — correctly, because its value is read off its own glyph and not
handed out by the meter. So a spurious `restQuarter` is a direct vote against the
correct meter.

Independence: it shares `Q.STAFF_LINES` and the same crop with everything else,
but its *identification* leans on the outline alone, which is the least
page-geometry-dependent reading in this family. On the ink-quality axis it is the
family's strongest member, so where it goes wrong, so does everything else.

---

## `rest8th`

A hook with a single flag. **The largest single difference between the two
publishers measured here: 38 rows on Litolff, 380 on Breitkopf** (MEASURED HERE,
probe). Produced by the YOLO detector.

### 1. What sets it apart — and what it is confused with

Bravura 0.988 × 1.700, h/w ≈ **1.72** — taller than wide, but much less so than a
quarter rest's 2.78 (LITERATURE, `[L26]`). On Litolff it is the fuzziest class in
the family: h/w p10 **1.13** / median **1.38** / p90 **2.41**, median confidence
**0.48**, the lowest of the three populated classes (MEASURED HERE,
`benchmarks/omr-rest-sizing-2026-09/FINDINGS.md` §2a, n = 38). Its p90 sits
squarely inside `restQuarter`'s body.

**Confused with:**

* **A `restQuarter`**, by aspect, at the overlap above. Not separately measured.
* ⚠️ **Its own upper hook, cut off by a cell boundary, read as a WHOLE REST on the
  staff above.** The measured one, and the largest single failure mode of
  `OMR_WHOLE_REST_INK` on the second publisher: of 12 fires, **8 were hand-read as
  the upper hook of an eighth rest on the staff below** (MEASURED HERE,
  `benchmarks/omr-second-publisher-pricing-2026-09/FINDINGS.md`, n = 12, one
  reader, corroborated by the record on 8 of 12 through page-pixel overlap with no
  class matching). The mechanism is the mark alphabet's own BOWL/BLOB story with a
  different glyph: the cell is cut with 4–6 spaces of padding, the hook alone is
  short and wide, and short-and-wide is the whole-rest shape window.
* **A dynamic letter or a fingering digit.** Shape-plausible; **not measured
  anywhere**. The DIGIT entry of the mark alphabet lists five roles for a digit
  and does not list *a rest hook*; the dynamics work measures over-emission of
  `dynamic*` classes and never a rest/letter crossing. ASSERTED.

⚠️ **Cross-staff contamination is a publisher property and the numbers are new.**
Rest detections carrying a cross-staff contest row (same class, different staff,
IoU ≥ 0.5): **2 of 646 on Litolff (0.3%)**, **97 of 1,028 on Breitkopf (9.4%)** —
a 30× difference (MEASURED HERE, probe). That matches, from a different
direction, the recorded *18.3% vs 3.5% of `restWhole` standing outside their own
staff*. ⚠️ And the contest gate requires the **same class**, so the
eighth-hook-read-as-whole-rest case is exactly the one it cannot see.

### 2. Best method: YOLO / CV / other

**YOLO for the glyph**, with the qualifier that this is where the detector is
least confident and the shape window least separated.

**CV for the thing that actually goes wrong**: whether the box is a *whole* glyph
or a *clipped* one. The repo has that discriminator for noteheads (an edge-touch
test plus a height cut in a measured empty band) and has never extended it to
rests — and, per `restWhole` §1, the notehead height cut of 0.6 spaces cannot be
reused because a whole rest is 0.576 tall. A rest version would have to be
per-class. ASSERTED; not tried.

### 3. Where on the page the deciding information lives

* The glyph's outline — hook plus one flag.
* **Whether the box touches its cell's top or bottom edge.** This is the fact that
  separates a real eighth rest from a neighbour's hook, and nothing on either path
  reads it for a rest. ⚠️ It is not a position on the staff lattice, so
  `Q.REST_POSITION` does not carry it and would not have caught these 8.
* Its x, aligning with the beat `[L29]`.

### 4. Stage by stage

The `restQuarter` plumbing exactly — `Q.REST` row, `rest_class` verdict at 0.5
quarters, no consequence, `<rest/>` + `<type>eighth</type>`. Nothing in any stage
distinguishes it from any other rest value.

⚠️ **`Q.GLYPH_OWNER` is its one cross-staff defence and it is narrow.** Where a
contest row exists, `export._place_notes` refuses the copy the verdict does not
own (`staged/export.py:722-734`) — a refusal, not a relocation, safe precisely
because the contested domain guarantees a twin. **97 Breitkopf rest rows are in
that domain; 931 are not.**

### 5. Abstain or best-guess — and what leans on this mark's certainty

**(a)** No. Same as every rest value.

**(b)** An eighth rest is 0.5 in its bar's sum, so it votes in the meter
corroboration like any read duration. Its measured failure mode hurts a
*different* family: a clipped eighth rest hook is what `OMR_WHOLE_REST_INK`
deletes a note for on Breitkopf, so **a rest reading failure in one staff deletes
music from the staff above** — 11 of the 12 deletions there were justified by the
wrong reason (MEASURED HERE, same source; that write-up's own conclusion is *"the
rule's outcome is good here and its reason is wrong eleven times in twelve"*).

Independence: the hook and the whole rest are read off the same crop by the same
model at the same moment. The correlation is the crop.

---

## `rest16th` / `rest32nd` / `rest64th` / `rest128th`

Hooks with two, three, four and five flags. Grouped because **their combined
population on both records is 8 rows** (MEASURED HERE, probe: `rest16th` 3 + 4,
`rest64th` 0 + 1, `rest32nd` and `rest128th` **0 and 0**).

### 1. What sets it apart — and what it is confused with

**The flag count, and only the flag count.** Bravura `rest16th` 1.280 × 2.716,
h/w ≈ 2.12 (LITERATURE, `[L26]`) — proportionally between an eighth and a
quarter, each further flag adding height. There is no positional fact and no
context fact; the whole identification is *count the hooks*.

**Confused with:** each other, and with `rest8th`. Nothing in this repo has
measured any of it — the population does not support a measurement.

⚠️ **`rest64th` fires once on Breitkopf.** Brahms 1 mvt 1 bars 1–58 do not print
64th rests; on the balance of evidence that row is a misread, but **it was not
checked against the print** and this dossier does not claim it. The structural
point: a spurious row here is worth **0.0625** in a bar sum and is harmless, while
the reverse (a 16th rest read as an eighth) is worth 0.25 and is not.

### 2. Best method: YOLO / CV / other

**YOLO, weakly.** The repo knows the analogous answer for NOTE flags: `_FLAG_LEVELS`
is derived from `rhythm._FLAG_DURATIONS` rather than restated, after a bug where
`levels = len(flags)` counted glyphs and one `flag16thUp` is one glyph and **two**
levels (MEASURED HERE, `docs/engraving-conventions.md` line 614). A rest carries
its flag count inside its class name, so that trap does not arise — but the
reverse does: a `rest16th` label is a *claim about a count* with nothing behind it.

**The CV alternative is real and unbuilt**: count the horizontal strokes on the
hook the way `line_detection._stacked_bar_count` counts beam bars. ASSERTED; the
population here could not price it.

### 3. Where on the page the deciding information lives

The hooks, stacked down the glyph's own stroke. Nothing else — and again
`Q.REST_POSITION` is irrelevant to this symbol. A rest of this value is never
alone in a bar in this repertoire, so there is no bar-level context to appeal to.

### 4. Stage by stage

Fully wired and fully generic: `Q.REST` row → `rest_class` via `_REST_DURATIONS`
(0.25 / 0.125 / 0.0625 / 0.03125) → `<rest/>` + `<type>`. `rest32nd` and
`rest128th` have a duration-table entry and a MusicXML type and **have never been
exercised on a committed record**.

⚠️ One historically-measured crossing sits in this size range: on the scan gate,
ours `32nd, 0.125` against a truth `16th, 0.4375` occurred **8 times**, and it is
the one entry in the rest-error table that is *not* the bar-filling convention
(MEASURED HERE, `benchmarks/omr-rests-2026-09/FINDINGS.md` §8). 8 of 618.

### 5. Abstain or best-guess — and what leans on this mark's certainty

**(a)** No. `_REST_DURATIONS` covers every class and `_rest_ruling` decides.

**(b)** Almost nothing, because there are almost none. Their contribution to a bar
sum is under a quarter each, so a wrong one is unlikely to flip a meter vote on its
own. The family's real exposure is the opposite: **these are the classes a dense
bar produces, and a dense bar is where every reader in this pipeline is worst** —
bar assessability falls with DENSITY, not with print quality (100% → 33% as events
per bar go 1.0 → 4.5, MEASURED HERE, CLAUDE.md /
`benchmarks/omr-staged-meter-boundary-2026-09/`).

---

## `restDoubleWhole`

A filled rectangle spanning the full space between two lines — a breve's worth of
silence. **Zero rows on both committed records** (MEASURED HERE, probe).

### 1. What sets it apart — and what it is confused with

**It is the only rest TALLER than it is wide by Bravura's own boxes** — 0.500 ×
1.000, w/h = 0.5 — and it touches two lines rather than hanging from or sitting on
one (LITERATURE, listed in the `[L26]` numbers). That makes it the one member of
the family whose outline is genuinely unlike the rest.

**Confused with:** a thick barline fragment, and a stem — i.e. the mark alphabet's
VERTICAL STROKE neighbourhood again. Unmeasured; there is no population. ASSERTED.

⚠️ **It matters more than its count, because of one literature exception.** The
whole-rest-fills-the-bar convention has recorded historical exceptions that are
**real in 19th-century plates**: 4/2 takes a **breve rest**, 3/2 and 6/4 take a
**dotted whole rest**, and metres shorter than 3/16 take a rest of the true length
(LITERATURE, `[L27]` known exceptions). This corpus is 19th-century plates. So on a
4/2 movement the bar-filling glyph is `restDoubleWhole`, and `size_measure_rest`
requires the class to be exactly `restWhole`.

### 2. Best method: YOLO / CV / other

**YOLO**, as for every shape-identified rest. It is in the 208-class space
(`tools/omr/training/deepscores_classes.py:126`) and the model has simply never
produced one here.

⚠️ **Before accuracy, reach** — the discipline
`benchmarks/omr-family-positions-2026-09/FINDINGS.md` §5 states and this family
needs: *a change that moves nothing because it is inert and one that moves nothing
because the page holds nothing are the same number.*

### 3. Where on the page the deciding information lives

Its outline, the two lines it spans, and — the reason it is in this dossier at all
— **the meter in force**: a breve rest is a bar-filling glyph only in the metres
the literature names.

### 4. Stage by stage

* **GATHER** → `Q.REST` row (the prefix test at `gather.py:887` is
  `name.lower().startswith("rest")`, so it routes correctly).
* **ADJUDICATE** → `rest_class`, **8.0** quarters, `written_type: "double_whole"`.
  ⚠️ `_rest_duration` prefix-matches over an ordered dict with `"restdoublewhole"`
  listed **first** (`tools/omr/rhythm.py:70-79`), so `"restwhole"` cannot shadow
  it. Verified by reading, not assumed.
* **EVALUATE** → `size_measure_rest` **refuses it by name** (`consequences.py:169`:
  `only.detail.get("rest") != "restWhole"`).
* **EXPORT** → `<rest/>` + `<type>breve</type>` at 8.0 ql.

**Net: on a 4/2 bar we would write 8.0 quarters where the bar holds 8.0 — right by
accident — and on any other metre using a breve rest we would be wrong with no
warning.** ASSERTED; nothing in the corpus exercises it.

### 5. Abstain or best-guess — and what leans on this mark's certainty

**(a)** No abstention; it decides from the class name like every other value.

**(b)** Nothing leans on it, because it never fires. Its one live risk is
`_bar_lengths_for`: the whole-rest exclusion that stops a bar-filling rest voting
on the meter is keyed on the **string `"restWhole"`**
(`adjudicators/rhythm.py:1232`, `:1237`), so a `restDoubleWhole` bar-filling a 4/2
bar would be **admitted as evidence at 8.0** and would vote for 4/4 — the exact
circularity the exclusion exists to prevent, one class over. ASSERTED, and it is
the cheapest thing in this dossier to make safe.

---

## `restHBar` / `restHNr` — the multi-measure rest

A thick horizontal bar between two vertical strokes, with a bar-count numeral
above it, standing for several bars at once. `restHBar` is the bar; `restHNr` the
number. **4 rows and 0 rows on Breitkopf; 0 and 0 on Litolff** (MEASURED HERE,
probe).

### 1. What sets it apart — and what it is confused with

⚠️ **ADDITION TO THE MARK ALPHABET'S HORIZONTAL STROKE ENTRY.** That entry pairs
*tenuto vs ledger line* and gives the discriminator as *lies ON the extended
half-space lattice and matches the staff's own measured line thickness*. An H-bar
is a **third role of the same mark** and the same axis separates it:

* **Thickness.** Bravura `hBarThickness` is **1.0 staff space**, exactly twice a
  beam's 0.5 and far more than a staff line's — so an H-bar is the thickest
  horizontal ink on a staff (LITERATURE, SMuFL `engravingDefaults`, `[L30]`).
* **A numeral centred above the staff** — the bar count.
* **Its span**: a whole measure cell, often a very wide one.

**Confused with, and this one is measured:** an **archaic C clef**, which is two
heavy horizontal bars. The detector reads it as `restHBar` at confidence
**0.60–0.86** on Nottebohm, sitting exactly on top of the clef. That is why
`clef_locator`'s occupancy list is **noteheads only** — rests were in it once and
had to come out, because they vetoed every C clef on the page (MEASURED HERE,
`tools/omr/transcribe.py:1957-1963`). The comment there states the general
principle the mark alphabet would endorse: *"a rest is a poor veto anyway — the
shapes that could be confused with a clef are the ones the detector misreads AS a
clef."*

Also confusable with a **beam** (same orientation, half the thickness) and a
**hairpin** (a long near-horizontal stroke). Unmeasured.

### 2. Best method: YOLO / CV / other

**CV, and the discriminator is already quantified.** Thickness in staff spaces is
a one-dimensional measurement with a stated expected value and a stated competitor
(1.0 vs a beam's 0.5). `line_detection` already measures horizontal ink runs for
beams; nothing asks it about H-bars.

**YOLO for the numeral is the wrong tool**, and the mark alphabet's DIGIT entry
says why: one numeral class covers meters, tuplet digits, fingerings, measure
numbers, stacked instrument numbers and plate numbers, and the distinction is
positional. `restHNr` is a sixth role of that mark and has never fired.

### 3. Where on the page the deciding information lives

| where | what it says |
|---|---|
| the horizontal stroke's **thickness** | this is an H-bar, not a beam |
| the **numeral above the staff** | how many bars it stands for |
| **how many measure cells this staff has** compared with its siblings | the same fact, arriving structurally |

⚠️ The third is the one the pipeline already computes and reads, and it reads it
**without ever consulting the glyph**. `_flag_measure_count_inconsistency`
down-weights a short staff whose wide cell contains **no noteheads** to
`likely_multimeasure_rest` and refuses to promote it, *"even under strong
consensus"* (`tools/omr/transcribe.py:4166-4186`). So the pipeline has a
multi-measure-rest hypothesis keyed on the **absence of noteheads**, not on the
presence of a `restHBar`.

### 4. Stage by stage

* **GATHER** → a `Q.REST` row like any other rest. The `Q.REST` docstring says why:
  *"Recording the ink and declining to read it is the honest pair; dropping it at
  the gather site is how this quantity came to be missing in the first place"*
  (`record.py:375-379`).
* **ADJUDICATE** → `_rest_duration` returns `None` and `_rest_ruling` abstains
  **`unreadable_rest`** — *"multi-measure indicator: names no single value"*
  (`adjudicators/rhythm.py:604-607`). **Measured: 4 `unreadable_rest` abstentions
  on Breitkopf, 0 on Litolff** (MEASURED HERE, probe), exactly the 4 `restHBar`
  rows. **This is the only place in the whole rest family where the pipeline
  abstains, and it is right.**
* **EVALUATE** → nothing. The bar-count consequence — *this glyph consumes N bars
  of the document's bar sequence* — **has no consumer anywhere** (`[L30]` code
  note: "No consumer for the bar-count consequence").
* **EXPORT** → no duration verdict, so no `<note>`. The bar falls to the padded
  measure rest.

⚠️ **`restHNr` is in the class space and has never been detected on either
record.** So the bar count — the one piece of information that would let the
structural consequence be handled — has never reached the pipeline at all.

### 5. Abstain or best-guess — and what leans on this mark's certainty

**(a) Yes, and this is the family's model citizen.** It records the ink, declines
to read a value, names the reason, and the exporter writes nothing.

**(b) The bar sequence leans on it, and that dependency is unhandled.** One printed
cell stands for N bars, so:

* `measure_partition` counts cells, and an H-bar staff has fewer than its siblings
  — which is what `_flag_measure_count_inconsistency` hedges against by declining
  to use its own check.
* `export._document_bar_offsets` numbers measures by *a system's bar count, the
  single value its staves AGREE on*. An H-bar staff disagrees by construction.
* `[C18]`'s whole-rest neighbour witness is **falsified by** a plate that uses
  H-bars across a tacet run — the convention entry says so itself. *A tacet part
  prints a whole rest in every bar* and *several silent bars are an H-bar* are
  **alternatives**, and which one a plate uses is a publisher fact nobody has
  recorded.

Independence: good, unusually. Thickness is a measurement off the raster but not
off the classifier, so an H-bar reader would fail on bad ink rather than failing
*with* the class reading. It is one of the few places in this family where a
genuinely second witness is available.

---

## The dotted rest — a rest plus an `augmentationDot`

Not a class: a `Q.REST` row and a separate `augmentationDot` detection standing to
its right. For the dot itself see the noteheads dossier; this section is only
about the joining.

### 1. What sets it apart — and what it is confused with

**Already answered by the mark alphabet's DOT entry**, which lists four roles —
augmentation dot, staccato, F-clef dots, repeat dots — plus *"none of the above →
ink noise, drop"*, with the augmentation window measured bimodal over 116 dots
(52 at 0.00 spaces, 52 at +0.50, nothing between +0.57 and +3.75).

⚠️ **ONE ADDITION AND ONE DISAGREEMENT WITH THAT ENTRY.** Its augmentation row is
written *"right of a head, at the head's space"* — a **notehead**. A dot after a
**rest** is a fifth position for that mark, and `rhythm._pair_dots_to_targets`
has always handled it (`dot_targets = noteheads + rests`, with the comment *"dots
after rests are rarer but real"*). The disagreement is about size rather than
existence: **on the measured evidence the role is real and vanishingly rare.**

Over both publishers: **656 `aug_dot` rows on Breitkopf, 1,129 decided rest
durations, exactly ONE dotted rest** — and that one is the **smallest `aug_dot` of
all 656** (0.180 staff spaces against a 0.490 median), on a crop showing a clean
*undotted* whole rest. Litolff: 35 aug_dot rows, **0** dotted rests. **691 rows
across two publishers attach to a rest once, and that once is wrong** (MEASURED
HERE, `benchmarks/omr-second-publisher-pricing-2026-09/FINDINGS.md`). The positive
control that makes the zero meaningful: **454 dotted NOTES of 2,828, 16.1%**.

So the honest form of the added row is: *a dot right of a rest, at or half a space
above it — real in the engraving, one measured firing in this corpus, and that one
a false dot.* Its practical confusable is **a speck**, which the entry's fifth row
already covers.

### 2. Best method: YOLO / CV / other

**YOLO detects the dot** (`augmentationDot`, reading F1 0.962 on engraved pages,
n = 102 truth / 108 predicted,
`benchmarks/omr-reading-vs-reproduction-2026-09/FINDINGS.md`). **Geometry joins
it**, and the geometry is paid for: an asymmetric window,
`DOT_ABOVE_NOTE_MAX_SPACES` 0.75 and `DOT_BELOW_NOTE_MAX_SPACES` 0.25, because a
dot goes above its note or level with it, never under, and a symmetric window ties
on a double stop.

⚠️ **The limit on a scan is DETECTION, not joining.** Litolff fires **49 flag boxes
and 35 dots** where Breitkopf fires **371 and 656** (MEASURED HERE, CLAUDE.md).
Litolff is catalogued *low-res bitonal*.

### 3. Where on the page the deciding information lives

To the **right** of the rest's box, within ~5 dot-widths, and vertically within
0.75 spaces above / 0.25 below the rest's centre. And — the rule that makes a
per-glyph decision safe — **reciprocally**: the dot is claimed only where *this*
rest is the best target the dot has in the cell.

⚠️ `Q.REST_POSITION` does not help here: a dot's position is measured against its
**target**, not against the staff lattice, which is why the DOT entry's window is
in notehead-relative units.

### 4. Stage by stage

* **GATHER** → the dot is its own `Q.AUG_DOT` row on the **dot's** glyph subject,
  not the rest's.
* **ADJUDICATE** → `_rest_ruling` calls `_attached_dots(ev, cell, rest_box, space)`
  (`adjudicators/rhythm.py:625`), which scores `Q.NOTEHEAD_CLASS` **and** `Q.REST`
  as **one pool** (`:322`). Each dot halves the running value.
* **EVALUATE** → `size_measure_rest` **refuses a dotted rest**
  (`consequences.py:169`: `or only.value.get("dots")`).
* **EXPORT** → `<dot/>` elements, `max`'d against the type's own implied dots.

⚠️ **This was broken until 2026-09-10 and the bug is the shape this architecture
exists to catch.** `_rest_ruling` did `ev.rows(Q.AUG_DOT)` on the **rest's own**
glyph subject, where GATHER does not put dots — *the exact fault fixed for
noteheads the day before, in the same function, one branch over*. So the module
dotted noteheads and silently not rests. The repair moved **zero verdicts** on
Litolff, and the write-up's own headline is that the zero is about REACH (MEASURED
HERE, `benchmarks/omr-staged-dotted-rest-2026-09/FINDINGS.md` §3–§4, n = 1,863
subjects, 20 aug_dot rows on 3 pages).

⚠️ **Widening the pool can TAKE a dot from a notehead**, because the reciprocity
only holds over the whole pool. That is the rule working, and it is the cost the
benchmark was built to measure. It measured **zero**, on a document with 20 dots.

### 5. Abstain or best-guess — and what leans on this mark's certainty

**(a) No abstention, and none is needed** — the absence of a dot in the window is a
definite answer (*this rest is undotted*), not a cannot-tell. But note what that
means on a plate the dot detector barely fires on: *undotted* and *we did not see
the dot* are the same output. That is the ABSENT/DECLINED collapse, in the dot
layer.

**(b)** A dotted rest's length feeds the bar sum like any other. The specific
dependency worth naming is the **literature exception under `[L27]`**: in 3/2 and
6/4 the bar-filling glyph is a **dotted whole rest**, and `size_measure_rest`
refuses anything with dots. So on those metres the convention silently does not
apply and the bar exports at the glyph's 6.0 quarters — right in 3/2, wrong by
half in 6/4.

Independence: the dot and the rest are two separate detections joined by geometry,
so this is one of the few joins in the family where the two facts really are
independent readings. What they share is the crop.

---

## The bar with no ink read in it — the padded measure rest

Not a symbol. A measure cell in which the record holds no duration verdict at all,
which the exporter fills with a whole-measure rest.

### 1. What sets it apart — and what it is confused with

**Already answered, and it is the project's own thesis violation.**
`docs/exploration-what-is-on-the-page-2026-09-09.md` §B.1: *"'this instrument
rests here' and 'the detector found nothing here' produce the identical output …
the ABSENT/DECLINED collapse the whole record exists to prevent, occurring in the
musical content rather than in the metadata"* — and it is common, because most
staves rest in most bars. The discriminator it names is **cell ink coverage**,
which `direction_text._blank_detections` already computes for another purpose.
`[C20]` is the same thing as a convention entry, graded **ASSERTED**.

**What this adds is the decomposition.** The population was never broken out:

| | Litolff pp.1–4 |
|---|--:|
| bars exported | 1,183 |
| `empty_bars_padded` | **184** |
| …of them, with no meter to size them by | **168 → 0** once the meter carry is on |
| `measure_rests_read` (a whole rest we actually read) | **92 → 280** |
| bars holding **no gathered ink at all** | **66** |
| bars coming out with **no event** | **178** |
| ⟹ bars where **the page gave us ink and no event came out** | **112** |

MEASURED HERE, `benchmarks/omr-rest-sizing-2026-09/FINDINGS.md` §1b/§3b and
`[C20]`.

⚠️ **Of the 471 rests exported at 4.0 ql in a 2.0 ql bar, 168 — more than a third
— are this, not a mis-sized rest.** 303 are `restWhole` glyphs the record read;
168 are padded bars. Same cause (no meter), different repair. MEASURED HERE, same
source §1b, exact to the unit.

### 2. Best method: YOLO / CV / other

**Neither — it is an ink question, and the instrument exists.** `Q.INK` gathers one
row per connected piece of a cell's ink, named or not, off the staff-line-erased
cell variant (`gather.py:1500-1545`), **default ON since 2026-09-17**.

⚠️ **`Q.INK` is read by nothing in any stage.** Grepping `tools/omr/staged/` for
`Q.INK` outside `gather.py` returns `trace.py` (an instrument), `capture.py` and
`meaning.py` (documentation tables) and `record.py` (comments). **No adjudicator,
no consequence, no inference, no exporter.** MEASURED HERE (grep, this session) —
and it agrees with the stage charter's §3a, which calls `Q.INK` *"the charter
implemented correctly and READ BY NOTHING"*.

⚠️ **The counter-argument is on record and is not fatal**: the ink is also badly
segmented — *Litolff MERGES and Breitkopf SHATTERS, and neither plate gives one row
per mark* (`docs/breakthrough-2026-09-18-the-unit-of-enquiry.md` §6). For *is there
ink in this bar at all*, that does not matter: the question is coverage, not
segmentation.

### 3. Where on the page the deciding information lives

Inside the measure cell: **how much ink is there, and how is it distributed**. A
silent bar printed with a whole rest holds one small blob near the bar's horizontal
centre `[L28]`; a bar we failed to read holds a lot of ink we could not name.

Secondarily, **the same bar on the other staves of the system**. A column through a
system is an instant, and `Q.ONSET_COLUMN` measured that the redundancy is real
(1,483 real instants against a phase-shuffled null's 2,409, MEASURED HERE,
`benchmarks/omr-onset-columns-2026-09/FINDINGS.md`). A bar whose neighbours are all
dense and which reads empty is a different proposition from one whose neighbours
are all resting.

### 4. Stage by stage

* **GATHER** → `Q.INK` rows exist for the cell; `Q.CELL_BOX` exists even for a cell
  with no detections. Nothing else.
* **ADJUDICATE** → `adjudicate_event` abstains `nothing_to_group`.
  `measure_partition` still counts the cell, so the bar exists.
* **EVALUATE / INFER** → nothing to work on.
* **EXPORT** → `staged/export.py:2167-2221`. `empty_bars_padded += 1`;
  `empty_bars_padded_without_meter += 1 if meter is None else 0`; then
  `_legacy._mxl_empty_measure(...)`, which writes the bar's marks and then
  `<rest measure="yes"/>` where the meter is known and `<rest/>` at a 4.0 fallback
  where it is not.

⚠️ **The exporter says so, at the site.** *"A bar with no notes gets a measure rest
because we read NOTHING in it, not because we read silence"*, and the two counters
are kept apart on purpose — *"conflating them would report a page as full of
measure rests when what it is full of is unread bars"*. The honesty is in the
coverage report and **not in the file**: MusicXML has nowhere to put *"a reader
could not run here"*.

⚠️ **FOUR STATES ARE COUNTED APART AND NONE IS DISTINGUISHED IN THE XML.**

| state | counter | in the file |
|---|---|---|
| we read a whole rest | `measure_rests_read` | `<rest measure="yes"/>` |
| we read nothing, meter known | `empty_bars_padded` | `<rest measure="yes"/>` — **identical** |
| we read nothing, meter unknown | `empty_bars_padded_without_meter` | `<rest/>` at 4.0 |
| the part is absent from this system | `tacet_bars_padded` (**149 refused / 0 padded**, `benchmarks/omr-tacet-padding-2026-09/FINDINGS.md`) | nothing, where the length is unknown |

⚠️ One small silent conversion in the same area: `export._mxl_note` writes
`<rest/>` when a note's pitch block cannot be built (`export.py:1063`), so an
unparseable pitch becomes silence rather than an abstention.

### 5. Abstain or best-guess — and what leans on this mark's certainty

**(a) It cannot abstain, and the reason is the output format.** Every bar of a
present part must be written. The one place it does abstain is on the LENGTH:
`measure="yes"` is withheld where the meter is unknown, because *"asserting this
bar is exactly 4.0 long on a page whose meter we never read would be a guess
dressed as a fact"*. The tacet path goes further and refuses to write the bar at
all — the asymmetry is stated: *a bar of a present part has to be written somehow;
a tacet bar does not have to exist at all.*

**(b) Everything downstream of the file leans on it, and the count is what Sean's
eye caught.** Only **38.0%** of exported bars sum to the `<time>` the same file
declares — 43.6% overfull, 18.4% short — and **428 of the 516 overfull bars contain
an unsized whole rest** (MEASURED HERE,
`benchmarks/omr-rest-sizing-2026-09/FINDINGS.md` §2b, n = 1,183). Nothing in the
pipeline reported that number.

Independence: **none.** A bar we read nothing in is, by construction, a bar every
reader failed on together — *the bars are not an independent umpire over a bad
reading*, in its purest form. The only witness that does not fail with it is
`Q.INK`, which is why it is worth having and why its being unread is the largest
open item in this dossier.

---

## What we do not know

1. **Whether the plates print half rests we are reading as whole rests.**
   `restHalf` is 4 rows in 1,674 and `Q.REST_POSITION` — the fact that would
   answer it — has never been produced on a committed record. A half rest read as
   a whole rest, standing alone, is resized **to the whole bar**.
2. **Whether any rest VALUE we export is right.** The 0.993 reading F1 is
   family-level (*a rest is here*). No instrument has scored
   whole-vs-half-vs-quarter against a truth, on either family.
3. **What fraction of `restWhole` detections are real whole rests on a scan.** The
   only evidence is the two hand-adjudicated fire sets of `OMR_WHOLE_REST_INK` (25
   and 12 glyphs), which are the rule's population, not the class's.
4. **Whether the rest/dynamic-letter and rest/fingering confusions exist.** Both
   are shape-plausible; neither appears in the mark alphabet's DIGIT or DOT rows
   and neither has been measured in either direction.
5. **Whether a clipped-fragment filter for rests would help or destroy the
   family.** The notehead version cuts at 0.6 staff spaces and a whole rest is
   0.576 tall.
6. **What `restDoubleWhole` and `restHNr` do**, on any page. Zero rows, both
   records.
7. **Whether the 168 unread bars hold ink.** `Q.INK` could say and no stage asks.
8. **n = 2 documents, 2 publishers, 8 pages, one movement each**, both scans, both
   19th-century. Nothing engraved was measured for rest *values*, and no third
   publisher exists.

---

## Questions for Sean

1. **Half rests.** We detect four of them across two whole orchestral movements.
   Is that what the plates print, or should we expect more? If they do print them,
   we are almost certainly reading them as whole rests and then stretching them to
   fill the bar.
2. **The bar-filling rest in odd metres.** The literature says 4/2 takes a breve
   rest and 3/2 and 6/4 take a *dotted* whole rest, and calls these real in
   19th-century plates. Our bar-filling rule refuses both (it demands an undotted
   `restWhole`). Do you meet those often enough to be worth handling, or is
   refusing them the right call?
3. **Multi-bar rests.** We meet four `restHBar` glyphs in 8 pages and no `restHNr`
   numerals at all. Do the editions you care about use H-bars, or do they write a
   whole rest in every tacet bar? And when they do use one, how much does it matter
   to you that the bar count comes out right — that is the piece we would have to
   build, and it changes the measure numbering rather than the notes.
4. **The three (really four) states of an empty bar.** Today the file says the same
   thing for *we read a whole rest here*, *we read nothing here*, and *this part is
   absent from this system*. Would a visible marker in the output be useful when
   cleaning up — something you could search for — or would you rather we keep the
   file clean and put it in the report?
5. **The whole-rest-that-is-really-a-notehead rule** (`OMR_WHOLE_REST_INK`) is the
   one thing in the pipeline that *deletes* notes. On the first publisher it removed
   22 notes and all 25 of its decisions were right; on the second it removed 11 and
   only one of its reasons was. It is on by default. Is deleting in that ratio the
   right trade for your cleanup, or would you rather it flagged and left the note in?
6. **The eighth-rest hook.** The single most common wrong deletion is the top of an
   eighth rest on the staff *below*, arriving through the measure cell's padding and
   looking exactly like a whole rest. Is there anything in the engraving that would
   let us tell those apart other than "the box is cut off at the edge of the crop"?
