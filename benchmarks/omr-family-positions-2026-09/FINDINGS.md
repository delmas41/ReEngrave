# Every family's own POSITION fact — ten producers, no consumers

2026-09-17. `tools/omr/staged/positions.py`, behind `OMR_FAMILY_POSITIONS`,
**default OFF**. Eleven families that `capture.py` graded `position: NONE` now
have a staff-relative, scoreless position quantity of their own. **Nothing
reads one**, deliberately.

> Sean, 2026-09-17: *"send an agent out to give the families real position
> information — or if it should be symbol specific then make it so"*

> And the same day, on what such a fact is FOR: *"I want to make sure that we
> keep clear that position is an option for helping us determine something but
> will rarely be a clear rule that determines by itself. 2 numbers not
> connected, one in the upper half and one in the lower half, could be a time
> signature. Due to ink bleed they may appear connected, or other things that
> we can't determine... Quick rules will give us quick results that could be
> poor."*

---

## 0. WHAT IS AND IS NOT ESTABLISHED — read this first

**ESTABLISHED.** Ten quantities exist, are produced on real pages of two
publishers, and are registered with every derived instrument that grades this
area. Flag-off is byte-identical over the record, proved by a control that was
shown to go red. The geometry is a ruler reading, and a handful of values are
hand-derived from engraving convention and asserted as such.

**NOT ESTABLISHED — ACCURACY, AND IT IS NOT CLAIMED ANYWHERE BELOW.** Nothing
consumes these rows, so no reading changed and no output moved. **No number
here is an accuracy figure.** The only values checked against something outside
the code are the synthetic fixtures, which encode engraving conventions a
musician can check, and one hand-read page (§4). Everything else is a COUNT.

**NOT ESTABLISHED — that any of this helps.** That is step three, and Sean's
own ordering puts it after this one: *"First we needed the stages... Next we
need to make sure that ALL information that could ever be possibly helpful is
gathered and available to all stages and decision points. Then we have to test
each point to see what is helpful in making a decision."*

**n = 2 documents, 2 publishers, 8 pages, all SCANS.** The engraved family is
untouched by construction and was not measured.

---

## 1. THE POSITION FACT PER FAMILY, AND WHY IT IS THAT ONE

⚠️ **The second clause of the instruction is the design.** These are ten
quantities, not one field used eleven times, because the musically meaningful
measurement differs by symbol and a schema wide enough for all of them would
hold none of them well.

| family | quantity | the fact | why THAT fact |
|---|---|---|---|
| rest | `Q.REST_POSITION` | which edge sits on which LINE, and on which side | a whole rest and a half rest are the **same rectangle** and differ only in this |
| time | `Q.METER_GLYPH_POSITION` | which HALF of the staff the mark occupies, and how far its centre is from the middle line | a printed meter is two marks, one per half, centred on each other |
| tuplet | `Q.TUPLET_MARKER_POSITION` | whether the digit clears the staff, and by how much | one `numeral` class covers meters, tuplet digits, fingerings and measure numbers — *a POSITIONAL distinction* |
| articulation | `Q.ARTICULATION_POSITION` | measured above / below / inside, and steps clear | a ruler beside the class name's own suffix, which is not an independent witness |
| fermata | `Q.FERMATA_POSITION` | the same measurement, **apart** | a fermata hangs over whatever sounds beneath it; an articulation attaches to one notehead. Two distributions |
| ornament | `Q.ORNAMENT_POSITION` | the same again, **apart** | a tremolo rides the STEM and its class states no side at all |
| slur + tie | `Q.ARC_POSITION` | the arc's own vertical extent, `depth_steps`, which side | `adjudicate_arc_kind` reads the NOTES' positions and has nothing about the curve |
| dynamic | `Q.DYNAMIC_BAND_POSITION` | staff SPACES below the bottom line | **PROMOTED**, not invented — see §2 |
| wedge | `Q.WEDGE_BAND_POSITION` | the same | **PROMOTED** for the CV rung, newly measured for the detector rung |
| direction | `Q.DIRECTION_BAND_POSITION` | the same | the only genuinely new one: this family has no detector row at all |

Plus `Q.CELL_POSITION_BASIS` — **the refusal**, filed once per cell when there
is no five-line grid (a one-line percussion staff), carrying the number of
marks it could not measure. Never a position; abstain-only by construction.

### 1a. TWO UNITS, ON PURPOSE

* **STEP frame** — staff steps off the cell's own line grid, top line `0.0`,
  bottom line `8.0`. The unit `Q.NOTEHEAD_STAFF_POSITION` already uses.
* **BAND frame** — staff SPACES below this staff's own bottom line. The unit
  `_band_offset_spaces` and `hairpin_detection`'s own constants already use.

⚠️ A dynamic, a hairpin and a direction word live in a ROW OF THE PAGE, not on
the grid. Giving a `ff` a step coordinate reports it at step 14 — a number that
composes across documents and means nothing. Every row names its `unit` and its
`frame` so the two cannot be mixed by accident.

### 1b. WHAT IS *NOT* CLAIMED PER FAMILY

* **An arc's CURVATURE.** A bounding box is identical for an arc opening up and
  one opening down, so `opens` is `None` with a note saying reading it needs the
  ink. `Q.INK` now gathers that ink and nothing joins the two.
* **Whether a measured side AGREES with the class name.** That comparison is a
  decision — it has a right to abstain and a right to say which is wrong — and
  decisions do not belong in GATHER. The two facts sit side by side, unjoined.
* **A rest's attachment where the measurement does not separate.** See §3.

---

## 2. TWO OF THE ELEVEN ARE A PROMOTION, NOT AN INVENTION

`Q.DYNAMIC_LETTER` and the `CV_HAIRPINS` half of `Q.WEDGE_BOX` **already
carried `band_offset_spaces`**: staff-relative, measured, scoreless. What they
lacked was a row of their own.

⚠️⚠️ `groups.correlated_groups` treats one reader's rows on one crop as **ONE
SIGNAL**, so an offset hung off the glyph's row is absorbed into that glyph's
own detector term and can never act as a second witness. `Q.CLEF_POSITION`'s
docstring already states this and cites the measurement: *a 1.5 added beside a
3.0 left the contest at 3.0 against 3.0*. `capture.py` grades those two families
`band*` for exactly that shape. **The number does not change; what changes is
that it becomes sayable on its own.**

### ⚠️ THE CORRELATION THIS DOES *NOT* ESCAPE, STATED PLAINLY

A position row carries no `derived_from`, following
`Q.NOTEHEAD_STAFF_POSITION` exactly: it is read off this raster against the
staff's own lines, so by `Observation`'s own invariant it has no ancestors.
**But the BOX it measures is the detector's.** If the detector mis-localises a
glyph, its class and its position are wrong together — the grid is independent,
the localisation is not. A consumer counting a shape row and a position row as
two independent witnesses is **right about the grid and wrong about the box**.

This is the same one-sidedness `independent_groups` already carries (*disjoint
closures prove the ROWS differ, not that the READINGS fail independently*), and
it is **UNMEASURED**. A promoted row records `promoted_from` — the source row's
id — which is deliberately *not* `derived_from`: the id lets a human follow the
join while the closure stays disjoint, which is the whole point of promoting.

---

## 3. AMBIGUITY IS RECORDED, NOT RESOLVED

⚠️ Sean's correction arrived mid-build and changed the framing rather than the
code. Nothing in the module vetoes, thresholds or rules anything out — every
field is a measurement or a COMPARATIVE with both sides kept — but three fields
exist specifically to keep an ambiguous reading ambiguous:

* **`attach_margin`** — how decisive a rest's edge pick was. Near zero, the two
  edges are equally near a line and the fact separates nothing; `hangs: below`
  read as a fact there would be a coin flip wearing a field name. An exact tie
  records `attached_edge: None`. Both edges' own lines and residuals are kept
  regardless, so a consumer that distrusts the pick loses nothing.
* **`centre_steps_from_middle`** — recorded FOR the fused-stroke case, not to
  settle it. A bled-together numerator/denominator pair is centred on the middle
  line; a barline fragment is centred wherever the break fell.
* **`opens: None`** — see §1b.

**There is not one threshold in the file.** Where a discriminator is needed it
is either a pure geometric predicate against the staff's own lines (which half;
inside or outside) or a comparative with the margin recorded. A constant read
off one document would be a constant fitted to a wish, and a threshold in GATHER
is the one decision no later stage can revisit.

---

## 4. THE LITOLFF p.62 CASE — a demonstration, and it CONFIRMS the warning

⚠️⚠️ **THE BRIEF THAT COMMISSIONED THIS WORK CALLED p.62 *"the falsifier for
the whole idea"* AND SAID A POSITION FACT *"refuses it on geometry alone"*.
BOTH ARE WITHDRAWN — by the coordinator who wrote them, and by the
measurement.**

**What the print holds** (`benchmarks/omr-ink-gather-2026-09/FINDINGS.md` §6,
committed crops under its `out/print/`): the `3/4` is printed at **cell 6** on
all 17 staves; the detector fires **nothing** there; at **cell 8**, an empty
rest bar, it fires `timeSig*` boxes at the cell's left edge which are fragments
of **one broken barline**.

**Measured** (`probe/meter_p62.py`, one page, flag on, 10 position rows; steps
from the top line, bottom line = 8.0):

| staff | cell | class | conf | top | bottom | height | half | centre off middle |
|--:|--:|---|--:|--:|--:|--:|---|--:|
| 11 | 8 | timeSig4 | 0.56 | −0.70 | 3.46 | 4.16 | **upper** | −2.62 |
| 11 | 8 | timeSig4 | 0.56 | 3.80 | 8.14 | 4.34 | **spans** | +1.97 |
| 9 | 8 | timeSig4 | 0.70 | 2.02 | 4.36 | 2.34 | spans | −0.81 |
| 9 | 8 | timeSig4 | 0.70 | 4.12 | 6.64 | 2.52 | lower | +1.38 |

Over the ten rows the `half` field reads `lower` 4, `upper` 3, `spans` 3.

⚠️⚠️ **THE BARLINE FRAGMENTS LOOK LIKE A METER, AND THAT IS THE RESULT.** The
staff-11 pair — the one `_meter_from_digits` reads as the `3/4` — comes out
`upper` + `spans`, sitting roughly one in each half of the staff, **4.16 and
4.34 steps tall against a real digit's ~4**. Neither the `half` field nor the
height separates them from a printed numerator and denominator.

**So the position fact does not refuse it, exactly as Sean said it would not.**
On a bitonal plate bleed fuses two digits into one stroke, so a `spans` reading
is compatible with a real meter; and two fragments in two halves are what a
broken barline also looks like. **Geometry alone settles neither direction, and
a rule treating either shape as decisive would be the quick rule with the poor
result.**

⚠️ **THE COMPARISON THE BRIEF ASKED FOR CANNOT BE RUN AT ALL.** It asked
whether the fact distinguishes *cell 6 (two marks, two halves, 17 staves)* from
*cell 8 (one stroke)*. **The detector fires nothing at cell 6**, so the
comparison has one side. That is a DETECTION gap and no position fact reaches
it. Reported rather than worked around, and **nothing was tuned to make this
case come out right.**

**What it DOES contribute**: the measurement is on the record, per glyph,
staff-relative and scoreless, where before this page's meter ink carried a
class, a confidence and an `x` and no vertical position at all. A later stage
weighing it against the ink, the other staves and the `cautionary` this document
already records has one more thing to weigh. Whether that is worth anything is
step three.

⚠️ One incidental observation, not chased: this run reads staff 11's pair as two
`timeSig4`, where the ink-gather findings record `timeSig3` + `timeSig4`. Two
`timeSig4` cannot spell `3/4`. Detector variation between runs is documented in
this repo; **this is noted, not explained, and nothing here depends on it.**

---

## 5. REACH, PER FAMILY, ON TWO PUBLISHERS

⚠️ **REACH FIRST, and the probe exits non-zero declaring itself DEAD at zero.**
A change that moves nothing because it is inert and one that moves nothing
because the page holds nothing are the same number, and this repo has paid for
that twice (the dotted-rest arm's clean zero; the wedge arm run on a document
with no hairpins).

| family | Litolff Beethoven 5, p1-4 | Breitkopf Brahms 1, p0-3 |
|---|--:|--:|
| slur + tie (`arc_position`) | **779** | **2207** |
| rest | **646** | **1028** |
| dynamic | **485** | **531** |
| articulation | **98** | **196** |
| fermata | **67** | **0** |
| time | **22** | **197** |
| direction | **6** | **10** |
| ornament | **1** | **7** |
| tuplet | **1** | **0** |
| wedge | **1** | **47** |
| rows in the record (flag off) | 44,879 | 70,444 |

⚠️ **EVERY ONE OF THE TEN FAMILIES PRODUCES ROWS ON AT LEAST ONE DOCUMENT, AND
NO FAMILY IS DEAD.** On Litolff all ten fire; on Brahms eight do.

⚠️ **THE TWO ZEROS ARE THE DOCUMENT AND NOT THE PRODUCER, AND THE PROBE SAYS SO
ON THE SAME RUN.** It prints the count of GATHER-stage INK rows beside each
family (`INK_OF`), because *zero positions with zero ink* is a fact about the
plate while *zero positions with ink present* would be a fault in me. On Brahms
both `fermata` and `tuplet` read **0 ink rows** — that plate yields no fermata
and no tuplet detection at all — and the same families fire 67 and 1 on Litolff.

⚠️ **THE `ink` COLUMN IS EXACT FOR THE TEN NEW FAMILIES AND DELIBERATELY LOOSE
FOR THE THREE OLD ONES.** Each of the ten measures one position per ink row and
the two columns match to the unit. The three pre-existing families are in the
table only as a control and their `INK_OF` entry is an approximation — `note`
maps to `Q.GLYPH_BOX`, which counts EVERY detection and not just noteheads
(8,486 against 2,347 positions on Litolff), and `key` maps to the per-accidental
marker rather than the per-staff run. **Those two gaps are a property of this
probe's convenience mapping, not a shortfall in the readers**, and no conclusion
here rests on them.

⚠️ **AND THE THIN ONES ARE THIN, WHICH IS ALSO THE DOCUMENT.** `tuplet` fires
ONCE across eight pages of two publishers; `wedge` and `ornament` once each on
Litolff. Those are DETECTION figures, the same shape this repo already records
for hairpins on scans (1 detected against 198 encoded). **A position fact cannot
measure ink nobody found.**

⚠️ **n = 2 documents, 2 publishers, 8 pages, all SCANS**, and both are pages
this repo has measured before — Litolff `984073` is catalogued *low-res
bitonal*, the pessimistic end of the corpus. The engraved family is untouched by
construction.

### Cost

**Below the noise floor.** On Brahms p0-3 the ON arm ran 191.7 s against the OFF
arm's 192.7 s — i.e. *negative* — and two separate ON arms of the same four
pages differed by 10.1 s. The honest statement is that the position pass costs
less than the gather's own run-to-run variance, **not** that it is free.

---

## 6. THE CONTROL: flag-off changes nothing the pipeline reads DETERMINISTICALLY

Both arms run over the **same prepared pages with the same detector object in
one process**. The claim is exact:

> every row the OFF arm produced is in the ON arm, unchanged, and the ON arm's
> surplus is EXACTLY the position rows

**Brahms p0-3: 70,444 OFF rows, 0 changed or missing.** **Litolff p4 alone:
15,991 OFF rows, 0 changed or missing.** In both, the surplus is entirely
position quantities and no position quantity appears in the OFF arm at all.

⚠️ **AND THE CONTROL WAS SHOWN TO GO RED.** `--prove-the-control-can-fail`
perturbs one already-present `Q.GLYPH_BOX` row and asserts the comparison
fails; it does. Without that, an arm comparing a log with itself would pass
identically and the green result would mean nothing.

### ⚠️⚠️ 6a. IT FAILED ON LITOLFF p1-4 — AND ONE GREEN ATTRIBUTION ARM NEARLY BOUGHT A FALSE ACCUSATION

On the four-page Litolff run the control reported **23 `Q.DIRECTION_WORD` rows
CHANGED**, reproducibly, all with page-4 subjects. What happened next is the
part worth recording.

| # | what was run | result | what it seemed to show |
|--:|---|---|---|
| 1 | ON vs OFF, p1-4 | **23 differ** | something changed a row |
| 2 | ON vs OFF, p4 alone | **23 differ**, same subjects | deterministic, so not jitter |
| 3 | **OFF vs OFF, p1-4** | **identical** | **⚠️ it is the FLAG** |
| 4 | row-count census, p4 | only the 9 position quantities differ | the record is clean |
| 5 | ON vs OFF, p4, canonical detail key | **passes** | the comparison was at fault |
| 6 | ON vs OFF, p1-4, canonical key | **23 differ** | ⚠️ that hypothesis is REFUTED |
| 7 | **OFF vs OFF, p1-4, second run** | **23 differ, same rows** | **it is the PIPELINE** |

**Row 3 is the trap.** One green attribution arm reads as proof that the flag
is responsible — and on the strength of it I was one step from reporting a
pipeline-wide non-determinism as a defect in my own change. Row 7 is the same
command on the same pages and it fails, **with the flag OFF in both arms**. One
pair that happens to agree is not evidence of determinism.

⚠️⚠️ **AND ROW 5 IS THE SECOND TRAP, WHICH I FELL INTO.** Canonicalising the
detail comparison made the single-page arm pass, and I wrote the mechanism into
the code as fact — *a set's `repr` orders by hash* — **before re-running the
four-page arm**. Row 6 refutes it. That is *asserting a mechanism without
measuring it*, from the one docstring in the change that claimed to explain
something. Corrected in place rather than deleted.

**The cause is upstream and already documented.** The Surya rung refuses a
*runaway read* on this page — 358 and 431 characters from a crop a few staff
spaces tall — and **the hallucinated text differs between runs** (*"Computer
Science Programming Course"* one run, *"Consulting Companies for Consulting
Companies"* the next). A stochastic decoder changes the page-level counts the
reader stamps on every abstention, and page 4 carries 23 of them.
`benchmarks/omr-direction-text-2026-09/NONDETERMINISM_2026-09-02.md` measured
the same thing at **485 differing lines between two flag-OFF runs**, and
diagnosed it with the same OFF-vs-OFF control, re-derived here independently.

⚠️ **SO THE HONEST STATEMENT OF THE CONTROL IS NARROWER THAN "BYTE-IDENTICAL":**
on every quantity the pipeline reads deterministically, flag-off is unchanged
and the surplus is exactly the position rows. On `Q.DIRECTION_WORD` the
pipeline is not deterministic between gathers, with or without this flag, so
no control of this shape can say anything about it. **The canonical-key
change stays** — comparing records by `repr` is wrong regardless — but it
fixed nothing, and the FINDINGS must not imply it did.

> **A control that fails is not evidence about your change until an
> attribution arm says so — and one attribution arm is not enough.**

---

## 7. FOUR THINGS THIS FOUND THAT IT WAS NOT LOOKING FOR

### 7.1 ⚠️⚠️ A BUG I SHIPPED, CAUGHT BY A NUMBER THAT NEEDED EXPLAINING

The first Brahms run reported `direction: 10 observed, 22 abstained` and
`wedge: 47 observed, 88 abstained`. The abstentions had no business existing.

`gather()` calls the position pass **once per page**, and `Log.all_rows()` is
the **whole log** — so the two families read from the record (the CV hairpins
and the direction words, whose ink no detection carries) had page 2's pass
re-walking page 0's and page 1's rows and measuring them against page 2's staff
bands, which do not contain an earlier page's staff keys. Every earlier page got
duplicate rows, filed as spurious refusals.

**Fixed with a page filter; 110 spurious rows went to 0.** ⚠️ The per-page
gatherers never had this problem — they iterate `detections`, which `gather()`
rebuilds per page. **Only a reader of the LOG has it, and that is the price of
reading the record instead of the detections.** Pinned by two tests, one of which
is the positive control that the rule measures its own page at all.

**The process point is the reusable one: the bug was found by refusing to report
a number I could not explain.** Both figures were small and plausible.

### 7.2 ⚠️⚠️ TWO DERIVED INSTRUMENTS HARD-CODED `gather.py` AND WENT BLIND

`positions.py` is the second GATHER-stage module this package has ever had, and
**both instruments that walk gather-stage source assumed there was one**:

* **`wiring.details()`** excluded `gather.py` from its READ scan as *"the write
  site is not a read"*. My module's `_band_core` writes
  `staff_bottom_line_page`, and because it is not `gather.py` that **second
  WRITE registered as a READ** and silently closed
  `DETAIL Q.WEDGE_BOX.staff_bottom_line_page` — a gap that is still completely
  open. This is the **fifth** instance of that family (a test naming a key, a
  benchmark probe naming one, the tool's own gap list naming one), and the first
  where the false reader is another write site.
* **`capture.observe_sites()`** parsed `gather.py` alone, so it could not see ten
  observe sites and reported ten declared position quantities as *declared and
  never observed*.

**Both now derive the set from `reach.STAGE_OF_FILE`**, which
`reach.unaccounted_modules()` already forces to be complete — and that check is
what caught `positions.py` being in neither list on the day it landed. Walking
the second module surfaced **two further real findings** in `wiring`, both
registered.

### 7.3 ⚠️ AN INSTRUMENT LIMIT I DECLINED TO CODE AROUND

`positions.py` emits its ten quantities through two helpers that take the
quantity as a **parameter**, so `capture._ObserveWalker` reads a name where it
needs a literal and reports both sites UNRESOLVED. Inlining six copies of the
`log.observe` call inside one data-driven loop would satisfy the walker and
**restate the scoreless / `READERS.GEOMETRY` / no-ancestors contract six times**,
which is the thing that drifts. Registered in `KNOWN_GAPS` with the argument
instead; `wiring` already accepts the same shape
(`Q.<loop-bound>.promoted_from`).

⚠️ **WHAT IS LOST, STATED: `capture` can confirm the ten are DECLARED and not
that they are OBSERVED.** What covers that instead is the reach measurement in
§5, on real pages. The related blind spot: `wiring`'s DETAIL question cannot see
through a `**dict` splat either, so it audits **2 of this module's ~30 detail
keys**. Reported, not worked around.

### 7.4 ⚠️ `Q.TUPLET_MARKER` RECORDS NO `y` AT ALL

It carries `x0`, `x1`, `x_center` and `is_bracket` — a horizontal span, which is
what group membership needs — and **no vertical position**. That is why the
tuplet position is measured from the detections rather than from that row.
**Reported and deliberately not patched**: adding a field to a shape row would
change a row this flag is required to leave byte-identical.

---

## 8. WHAT WENT RED ON SUCCESS

Five tests in `test_staged_capture.py` failed when the ten producers landed —
the shape CLAUDE.md records from the day the last stub closed. **None was
deleted and none was replaced by a weaker assertion alone.** Each is rewritten
to the new contract and still exercises its mechanism in both directions:

* *there is no position* and *there is one and nothing reads it* are **different
  findings and different repairs** — write the adjudicator's input against wire
  the input it already has. `capture.problems()` now says the second where it is
  true, which made eleven `POSITION <family>` gap entries STALE. **They left the
  list**, as the contract requires, replaced by ten `UNREAD-POSITION` entries
  each naming its first consumer.
* the test asserting *nothing is unresolved* is now *every unresolved site is
  accounted for*, **with a positive control that an unaccounted one still
  fails** — a relaxation is only safe if the thing it relaxes still bites.

## 9. THE MUTATION BATTERY

**27 arms, 27 red, restore VERIFIED**, positive control in the same class (one
arm breaks the ACCEPTING path, because a battery of refusal arms passes against
a module that writes nothing). Byte snapshot before the first arm, in-flight
sentinel, refuses a dirty tree without `--force`.

⚠️ **Its first run found four problems and THREE WERE REAL TEST GAPS**, which is
the value:

1. an arm restating `_band_offset_spaces` for the **top edge only** survived,
   because the test asserted `row.value` (the centre) alone — *a helper used
   three times needs all three answers checked*;
2. an arm setting `UNIT_BAND` equal to `UNIT_STEP` survived, because the test read
   `assertEqual(detail["unit"], POS.UNIT_BAND)` — **comparing the constant with
   itself**, the vacuous-assertion family inside a test written to prevent unit
   confusion;
3. an arm moving the middle-line constant to 6.0 survived, because the fixture's
   two boxes touch the middle line from both sides and stay correct for any cut
   in [4.0, 8.0] — closed with boxes that sit wholly inside one half.

The fourth was the battery's own bad anchor, and one arm needed retargeting onto
the narrow test rather than the obvious one.

## 9a. THE SUITE AND THE DERIVED CHECKS

Full `tools/omr/tests/` on the MERGED tree: **4325 passed, 17 skipped, 0 failed** (717 s).
`capture --check`, `reach --check`, `wiring --check`, `inventory --check`,
`health --check` and `gather_coverage` all exit **0**.

⚠️ `capture --check` and `wiring --check` were each run on the BASE tree first:
`capture` exits 0 there too, and `wiring` exits 0 with 61 problems against my
63 — so neither green is a green I inherited, and neither of my two extra
`wiring` problems is a regression (both are this module's own detail keys,
newly VISIBLE because that question now walks a second write site).

## 10. REPRODUCING

```bash
python3 -m tools.omr.staged.capture              # the table this answers
python3 benchmarks/omr-family-positions-2026-09/probe/position_reach.py \
    <pdf> --pages 0-3 --weights <weights> --no-surya --out out/reach.json
python3 benchmarks/omr-family-positions-2026-09/probe/position_reach.py \
    <pdf> --pages 1 --weights <weights> --prove-the-control-can-fail
# ⚠️ run this TWICE before believing any control failure — see §6a
python3 benchmarks/omr-family-positions-2026-09/probe/position_reach.py \
    <pdf> --pages 0-3 --weights <weights> --no-surya --off-vs-off
python3 benchmarks/omr-family-positions-2026-09/probe/meter_p62.py \
    <litolff.pdf> --page 62 --weights <weights>
python3 benchmarks/omr-family-positions-2026-09/mutate.py
```

⚠️ A worktree needs the symlinks CLAUDE.md lists (`library`, `omr-weights`,
`tools/omr/training/data/weights`, `.venv-surya`); three of the four fail on the
scan side only, so a clean `orchestral_eval` proves nothing about these runs.

## 11. THE RANKED NEXT WORK — and it is NOT a rule

**Step three, per Sean's ordering: test each decision point to see what actually
helps.** The ten `UNREAD-POSITION` entries in `capture.KNOWN_GAPS` and the ten in
`reach.KNOWN_GAPS` each **name their first consumer**, which is where that
testing starts. The two with the most prior evidence behind them:

1. **`Q.DYNAMIC_BAND_POSITION` → `adjudicate_glyph_owner`.** That decision
   resolves a contested letter by DISTANCE, which this repo has already measured
   being a coin flip (5-62 px), while `benchmarks/omr-dynamics-band-2026-09`
   measured 24% of letters standing in the band of the staff immediately above,
   **distance exactly 1, no exceptions**, with a measured empty interval. The
   evidence for weighing it is already taken; only the wiring is missing.
2. **`Q.REST_POSITION` → `adjudicate_duration`**, which reads a rest's class name
   and nothing else — and `OMR_WHOLE_REST_INK`, the one staged rule that DELETES
   music, whose position witness is reconstructed per-document from the
   detector's boxes and **inverts between the two publishers measured here**.

⚠️ **Neither is a rule to write; both are an input to weigh**, and each needs its
own measurement of whether it helps before anything defaults on.

Two smaller, cheap follow-ups: a **third publisher**, to say whether the fermata
and tuplet zeros are these two plates or the repertoire; and the **arc's
curvature**, which needs `Q.INK` joined to `Q.ARC_POSITION` and would turn a
bounding box into an actual curve.

---

## 12. ⚠️⚠️ A SIBLING SESSION BUILT THE OTHER HALF WHILE THIS RAN — and the two fit

The base branch moved **12 commits** during this work, and one of them is
`832fbfab A position-keyed store: where things fall, kept at full grain`, with
`Q.DOCUMENT_IDENTITY` and `tools/omr/positional_store.py`. This is the §7
pattern CLAUDE.md records — *three briefs overtaken by work already on main in
one session* — arriving a fifth time. **`git log --all -S` before dispatching,
and again before pushing.**

⚠️ **THEY DO NOT DUPLICATE EACH OTHER; THEY ARE THE TWO HALVES OF ONE THING**,
and the join is Sean's own framing: *"it might be helpful to have general
information based on publisher or common practice of where a certain things
fall so if we have an undiagnosed blob or dot, we have gathered a lot of
information on what sorts of things are more likely where."*

| | this branch | the sibling |
|---|---|---|
| what it adds | a POSITION fact per family, per mark | a STORE those facts accumulate in, and the key it conditions on |
| the gap it closes | `capture`'s `position: NONE` on eleven families | `capture`'s `CROSS-DOCUMENT` finding |
| without the other | positions with nowhere to accumulate | a store with three families' positions to hold |

**Together they are the aggregate Sean asked for**: eleven more families'
worth of *where things actually fall*, keyed by the edition and publisher that
`Q.DOCUMENT_IDENTITY` now puts on the record.

### The merge, and what the tool arbitrated

Three conflicts, all additive collisions in the same registries, and **the
derived checks decided two of them rather than my judgement**:

* `record.py` — both sides added a quantity block at the same point. **Both
  kept.**
* `wiring.py` — they removed `DETAIL Q.WEDGE_BOX.y_center_page` with a measured
  argument (`positional_store` reads that LEAF NAME off other quantities, so
  the credit is a textual coincidence their comment documents). **Their
  treatment kept, plus this branch's two new entries** — and my
  `_row_writer_files` repair is what stops `positions.py` writing
  `staff_bottom_line_page` from closing their remaining entry the same way.
* `capture.py` — their side still carried `"POSITION tuplet"`, which **this
  branch's producers make stale**; mine supersedes it. Then `--check` reported
  **`CROSS-DOCUMENT` STALE**, because THEIR change closed it. It has left the
  list, with a note saying why, exactly as the contract requires.

⚠️ **I did not decide that last one — the instrument did.** A closed gap must
LEAVE the list, and neither session could have seen it alone: the entry was
live on both branches and dead only on the merge. **The merged tree is the one
thing no session ran**, which is why it was checked before anything was pushed.
