# The notehead gate, built and run — and the fixture that justified the rule inverts

**2026-09-20.** `OMR_STEM_NOTEHEAD_GATE`, **default OFF**, allow-list ON test.
`benchmarks/omr-stem-pair-rule-2026-09/FINDINGS.md` §3c proposed this repair
and §4 recorded that it *"has never been run end to end"*. It has now.

| | verdict | the number |
|---|---|---|
| **Phase 0 — re-derive before building** | **every figure matches to the unit** | 244 deleted / 80 on a head / **62 = 77.5%** / 73 heads (9.2% of 793) / 1,920 ON / 2,164 OFF / 783 of 783 cells match the record EXACTLY |
| **the gate, both plates, end to end** | **faithful and one-sided** | OFF reproduces **1,920** and **2,305** exactly; **+80 / +152** strokes, **all of them on a head**, **0 lost** |
| **downstream** | the sibling lane's own figure, from the other direction | heads with no stem **793 → 720 (−73)** and **1,529 → 1,351 (−178)** |
| **the hand cells (the rule's fixture 2)** | reproduced exactly, and the gate costs +5 | ON **15**, OFF **53**, GATED **20**; GATED worse on 3 cells, better on 0 |
| **the reference sheet (the rule's fixture 1), PAGE total** | **the gate gives back the whole win** | ON **3**, OFF **27**, GATED **27** |
| **the reference sheet, PER BAR** | ⚠️⚠️ **the page total is two errors cancelling, and it inverts** | ON **7**, OFF **3**, GATED **3** — the shipped rule **EMPTIES a bar of four chords** |
| **the sheet's premise** | ⚠️⚠️ **it prints NO ACCIDENTAL AT ALL** | so the rule's cited win there was never a measurement of accidental rejection |

---

## Ask-first block

**CONVENTION ASSUMED.** *A vertical stroke that overlaps a detected notehead's
box is that note's stem.* This is the sibling lane's proposal, not a
convention Sean has stated, and it is the single claim everything here rests
on.

**WHAT WOULD FALSIFY IT.** A crop showing a stroke that meets a notehead box
and is not a stem — an accidental printed hard against its own note, a
neighbouring staff's ink reaching into the measure cell's 4-6 space padding,
or a notehead box so generous it swallows ink beside it. **§5 measures one
such family on a clean engraving and it is real**: on the LilyPond reference
sheet every deletion the rule makes stands on a notehead, and at least two of
the four rescued strokes per affected chord are not separate printed stems.

**NOT CONFIRMED WITH SEAN.** That the gate should ship at all; that a default
flip is wanted; that giving back the reference sheet's page-level number is
acceptable in exchange for the per-bar behaviour; and whether *"strokes on 2
of 4 printed chords against 0"* is the improvement it looks like.

---

## 0. Phase 0 — re-derived before anything was built

Run on the committed
`library/_shared-records/beethoven5-p1-p4-ink-identity.record.json` with the
sibling lane's own probes, unmodified, before a line of the gate existed.

| | that lane | here |
|---|--:|--:|
| stem candidates before the rule | 2,164 | **2,164** |
| after (shipped) | 1,920 | **1,920** |
| strokes the rule deletes | 244 | **244** |
| … landing on no detected notehead | 164 (67.2%) | **164 (67.2%)** |
| … carrying a notehead | 80 | **80** |
| … of those, partner ALSO carries one | **62 (77.5%)** | **62 (77.5%)** |
| heads that would stop abstaining | 73 (9.2% of 793) | **73 (9.2%)** |
| record cells whose stem boxes match EXACTLY | 783/783 | **783/783 (100.0%)** |
| that lane's restatement vs the shipped rule | 0 mismatching cells | **0 of 1,183** |

**Nothing differs.** The accidental attribution reproduces too (natural 7,
flat 5, sharp 2), as does the geometry table's best single cut (**0.823**
bottom-offset against a **0.723** majority baseline, no empty interval).

---

## 1. What shipped

`line_detection.py`:

> **A stroke that MEETS A NOTEHEAD is a stem and is kept. A pair is dropped
> only where the SUBJECT meets none.**

**No new constant.** That is the reason for this shape rather than a
threshold: the geometry `detect_stems` can see does not separate the two
populations, so a cut read off that table would be fitted to one plate.

**It takes TWO things to fire — the FLAG and the DATA.** `detect_lines(cell)`
passes no detections, so the legacy `transcribe` path is unchanged **by
construction** rather than by a second decision. That closes the sibling
lane's objection 2 (*"the legacy path would diverge"*) without a rule.

`gather.py` now hands `gather_cv_lines` the detection map `gather()` already
held. `None` (no detector — a supported mode) and `[]` (a cell with no
notehead) are kept distinct end to end.

### 1a. ⚠️ THE PROPOSED FORM WAS NOT THE BEST FORM OF ITSELF, and a unit test found it

`probe_proposed_gate.py` excludes an on-head stroke from being a **partner**
as well as from being a **subject**. A test written for the accidental case
failed against it, and the failure is real: **an accidental's stroke standing
beside a genuine stem loses its only partner and SURVIVES as a false stem.**

A stroke on a head is never dropped whichever way the partner is treated, so
the 62 are safe either way. What the partner rule decides is the *other* case:

| | shipped rule | both-sides gate | **subject-only (shipped here)** |
|---|---|---|---|
| both on a head (two stems) | both dropped | both kept | **both kept** |
| one on a head (stem + sharp) | both dropped | **both kept** ⚠️ | **stem kept, stroke dropped** |
| neither on a head (accidental) | both dropped | both dropped | **both dropped** |

**Measured, not argued.** On the hand cells the two forms are identical
(GATED 20 either way — that fixture does not exercise the middle row). On the
plates they differ exactly as predicted: the both-sides form rescues **89** on
Litolff and **178** on Breitkopf, of which **9** and **26** carry no head of
their own; the shipped form rescues **80** and **152**, **all on a head**.

⚠️ The test's OWN first fixture was wrong and is recorded at its site: the
notehead box was 120 px wide and covered BOTH strokes, so the partner met the
head too and the test failed against a correct gate. *A fixture that does not
isolate the case tests the fixture.*

---

## 2. Controls, before any finding

**FAITHFULNESS.** The OFF arm must reproduce each shared record's stem set,
because that is what every stem arm in this repo proves before reporting a
delta. **1,920 = 1,920** and **2,305 = 2,305**, exactly, and the arm exits 2
if not.

**POSITIVE.** The two arms must differ, or a flag that never reaches the code
reads as *the gate is harmless*. They differ on 44 and 121 cells.

**STRUCTURAL.** The gate can only ever UN-condemn, so **0 strokes lost** is a
checked property and not a claim.

**NO INHERITED FLAG.** The arm **refuses to start** with
`OMR_STEM_NOTEHEAD_GATE` already in the environment — under a per-arm
assignment an inherited value makes both arms the same one, the hazard this
repo records twice.

**THE BOX-CONVENTION TRAP FIRED, LOUDLY.** The downstream block first passed
detection *objects* to `rhythm._boxes_overlap`, which takes plain
`(x, y, w, h)` tuples, and **crashed**. Three disagreeing box spellings live
in this tree and this one usually shows up as a clean believable zero.

**AND A MID-RUN EDIT WAS CAUGHT RATHER THAN MEASURED.** The subject-only fix
landed while two plate arms were running; an already-imported module keeps its
code, so those runs were measuring the rejected form. Both were killed and
re-run rather than reported.

---

## 3. Both plates, end to end

`gate_arm.py`, re-cutting the page at 600 dpi (a GATHER change, so
`readjudicate` and `reexport_arm` are structurally blind to it).

| | Litolff Beethoven 5 p1-p4 | Breitkopf Brahms 1 p0-p3 |
|---|--:|--:|
| cells cut | 1,183 | 818 |
| cells holding a detected notehead | 814 | 643 |
| noteheads detected | 2,347 | 3,337 |
| **stems, gate OFF (faithful)** | **1,920** | **2,305** |
| stems, gate ON | **2,000** (+80) | **2,457** (+152) |
| cells whose stem set changes | 44 | 121 |
| rescued strokes standing on a head | **80 / 80** | **152 / 152** |
| strokes lost | **0** | **0** |
| **heads with NO stem, OFF** | 793 (33.8%) | 1,529 (45.8%) |
| **heads with NO stem, ON** | **720 (30.7%)** | **1,351 (40.5%)** |
| **heads that stop abstaining** | **73** | **178** |
| CV beams, OFF → ON | 322 → 337 | 412 → 444 |

⚠️ **THE −73 IS THE SIBLING LANE'S OWN 9.2%, REPRODUCED FROM THE OTHER
DIRECTION.** They joined the committed record; this re-cuts the page and
counts heads with no overlapping stroke using `rhythm._boxes_overlap`
**imported** from the adjudicator. Two instruments, two routes, **73 = 73**.
The Breitkopf **1,529** likewise matches `rejection_census`'s published
stemless-head count for that plate.

⚠️ **The beam delta is the STEM SET moving, not a beam change** —
`detect_beams` takes the stems as its input. Stated so it is not re-found
later as a beam regression.

⚠️ **The two plates behave differently and are never pooled**: Breitkopf
begins with a far worse stemless rate (45.8% against 33.8%) and the gate takes
a larger absolute bite there.

---

## 4. The hand cells — the rule's second fixture, reproduced exactly

| arm | summed abs. error | worse than ON | better than ON |
|---|--:|--:|--:|
| ON (shipped) | **15** | — | — |
| OFF | 53 | 7 cells | 0 |
| **notehead-GATED** | **20** | **3 cells** | **0** |

Reach **10 of 14** (4 La Mer cells report `region no longer resolvable`, which
`_resolve_cells`' own docstring predicts and which is not this gate's doing).
Running the sibling lane's `probe_proposed_gate.py` beside this arm gives the
**same three numbers**, so the shipped code and their restatement agree.

**The gate costs +5 here, all of it over-counting, never under.**

---

## 5. ⚠️⚠️ The reference sheet — the rule's FIRST fixture, never scored until now

The page total says the gate is a disaster:

| thickness | truth | ON | OFF | GATED |
|---|--:|--:|--:|--:|
| 1 | 48 | 47 | 56 | 56 |
| 2 | 48 | **48** | 56 | 56 |
| 3 | 48 | 49 | 56 | 56 |
| 4 | 48 | 47 | 51 | 51 |
| **summed \|error\|** | | **3** | **27** | **27** |

That reproduces the rule's own docstring (*"from +7/+8/+5/+2 to −1/0/+1/0"*)
to within the phase-1 drift since: today's OFF reads +8/+8/+8/+3 and today's
ON −1/0/+1/−1.

**GATED == OFF at every thickness**, which is only possible if every stroke
the rule deletes there meets a notehead. `probe_reference_sheet.py`:
**28 of 28 do**, across all four thicknesses.

### 5a. ⚠️⚠️ THE SHEET PRINTS NO ACCIDENTAL AT ALL

`benchmarks/omr-phase4-lines/reference-lines.ly` is plain C major and G major
— `c'4 d'4 e'4 f'4`, `c'16[ d'16 e'16 f'16]`, `<c' e' g'>4`, `g2 b2` — **not
one sharp, flat or natural in 48 stems.**

So the rule's cited win on this fixture was **never a measurement of
accidental rejection**. Something else on this sheet comes in pairs, and until
now nobody had asked what.

### 5b. It is ONE BAR, and it is the CHORDS

All 28 deletions fall in **one cell of staff 0**. At thickness 4 the page cuts
**6 cells per staff against the sheet's 6 bars**, so the per-bar truth
`ground-truth.json` has carried all along IS usable there.
`probe_per_bar.py` **REFUSES** the other three thicknesses by name — the
caveat `score_pdf` states, checked rather than inherited.

| staff | bar | content | truth | ON | OFF | GATED |
|--:|--:|---|--:|--:|--:|--:|
| 0 | 1 | four quarter notes | 4 | 6 | 6 | 6 |
| 0 | 3 | eight eighths, beamed in pairs | 8 | 8 | 8 | 8 |
| 0 | 4 | sixteen 16ths in four beamed groups | 16 | 16 | 16 | 16 |
| **0** | **5** | **four three-note chords** | **4** | **0** | **4** | **4** |
| 1 | 1 | two half notes | 2 | 3 | 3 | 3 |
| | | **summed \|error\| per bar** | | **7** | **3** | **3** |

(the five bars not listed read the truth exactly in all three arms)

**THE SHIPPED RULE EMPTIES A BAR OF FOUR CHORDS.** The page total reads the
other way because two errors cancel — the page over-detects by 3 elsewhere and
the rule deletes 4 chord strokes, netting −1 against a truth of 48.

**A whole-page total cannot see a bar emptied and a bar inflated at once**,
and that is how the rule's justification survived on a fixture that does not
contain the thing it names.

### 5c. ⚠️⚠️ And GATED 4 against a truth of 4 is a COINCIDENCE OF COMPOSITION

The bar's four strokes stand at x = **2.29, 2.73, 11.15, 11.58** staff spaces
in a **19.7-space** bar holding four chords. That is **two x-clusters**, not
four: two chords contribute two strokes each (one **6.0-6.2 spaces** tall —
consistent with a stem fused through its own stacked noteheads — and one
**3.13-3.14** beside it) and **two chords contribute nothing at all**.

So the honest statement is **not** *"the gate gets the bar right"*. It is:

> **strokes on 2 of the 4 printed chords, against the shipped rule's 0.**

`probe_per_bar.py` prints that line itself, so the count cannot be quoted
without it.

⚠️ Corroboration from the data rather than from the story: staff 1's bar 5 is
**two-NOTE chords** (one staff space of stacked heads instead of two) and has
**zero deletions at every thickness**, which is what a *stacked heads survive
the vertical opening* mechanism predicts.

### 5d. ✅ THE CROP WAS CUT, and it confirms the composition and corrects the story

`out/print/reference-chordbar-t4.png` — the bar at thickness 4 with every
OFF-arm stroke marked by a red tick in the TOP MARGIN ONLY, so no annotation
covers the ink.

**CONFIRMED, by eye:** the bar prints **four three-note chords, each with one
stem**, and the four red ticks sit in **two clusters over chords 1 and 3**.
Chords 2 and 4 carry a clearly printed stem and produce **no stroke at all,
even with the rule off** — a detection shortfall that has nothing to do with
this rule. So *"strokes on 2 of the 4 printed chords, against the shipped
rule's 0"* is what the print says, and the per-bar count of 4 is a
coincidence, exactly as §5c states.

⚠️ **WHAT THE CROP DOES NOT CONFIRM is §5c's mechanism.** That the taller
stroke is *a stem fused through its own stacked noteheads* and the shorter one
*a head column beside it* remains an inference from the heights and the
x-clusters. The crop settles the COMPOSITION (four strokes, two printed
objects) and not the identity of each stroke; separating those would need the
component masks, which this lane did not cut.

---

## 6. So what is the answer?

**The gate does what it was proposed to do, and the fixture that justified the
rule it narrows does not say what it was thought to say.** Three separate
statements, none of which settles the default:

1. **On real orchestral scans it is a clear gain in reach.** +80 and +152
   strokes, every one on a notehead, 0 lost, and **73 and 178 heads stop
   abstaining** — the second of those on a plate nobody had measured this on.
2. **On the rule's hand-counted cells it costs +5**, all over-counting.
3. **On the rule's reference sheet it costs 24 points of a page total that is
   confounded**, and *gains* 4 points of a per-bar score that is not — while
   the per-bar win is itself two chords, not four.

⚠️ **THE STANDING OBJECTION IS UNTOUCHED AND IS NOT AN n ARGUMENT.** The gate
**couples `Q.STEM` to the detector**. The CV stem rung is today an independent
reader of the ink — `gather_cv_lines`' own docstring says the two readers see
different images on purpose — and gated it is not. It fails toward the shipped
behaviour, never toward a new one, but it is weakest exactly where stems are
most often missed. **That is a reason a human must weigh, not a number.**

**RECOMMENDATION, NOT A CHANGE: leave it OFF and put §5 in front of Sean.**
The gate is not the most interesting result here. The most interesting result
is that a rule running in production is justified by a page total on a sheet
with no accidentals in it, and that the same fixture read at its own per-bar
resolution says the rule empties a bar of chords.

---

## 7. Mutation battery

⚠️⚠️ **THE RESULT PUBLISHED HERE ON 2026-09-20 IS VOID, AND THE REASON IS IN
THE JUDGE.** `headline()` compared pytest's summary line **verbatim**, and
that line ends `" in 0.57s"` — which differs between two runs of an
UNMUTATED tree. So `out != b_out` was true for every arm and **all 21 scored
RED for free**: the battery could not have told a real mutation from a
no-op. Found 2026-09-21 by a sibling lane that had COPIED this `headline()`
and whose own first run came back 13 of 13 red; stripping the duration there
turned it into 10 red and **three survivors, every one real**. Measured on
this repo's own suite: two identical runs gave `13 passed, 5 warnings in
0.57s` and `... in 0.61s`. **Only two of the repo's 30 batteries carry the
shape** — this one and the sibling that copied it — so it is a 2026-09-20
regression rather than anything historic. The duration is stripped now.

⚠️ **THE RE-RUN'S RESULT IS BELOW, and the original text is kept beside it
rather than deleted: a superseded measurement with its correction beside it
is worth more than a gap.**

**RE-RUN, ON A JUDGE THAT CAN FAIL: 21 arms, 18 RED, 0 bad anchors, restore
VERIFIED by md5 — and THREE SURVIVORS, every one on this gate's OWN SAFETY
ARGUMENT rather than on its behaviour** (`out/mutation-battery-rerun.txt`):

1. ⚠️⚠️ **The flag alone arming the gate** (`list(noteheads or [])`), which is
   **BEHAVIOURALLY EQUIVALENT** — an empty head list condemns exactly what
   `None` condemns, so no output moves and
   `test_the_flag_alone_with_no_noteheads_changes_nothing` passes against the
   mutant. What it destroys is the CONTRACT `_drop_paired_strokes`' own
   comment spells out — *"`None` and `[]` MUST NOT BE THE SAME THING HERE"* —
   and with it **the legacy path's whole "unchanged BY CONSTRUCTION" claim.**
   Closed by a spy asserting the VALUE HANDED OVER, not the result.
2. **The overlap test loosened from `> 0` to `>= 0`**, so a stroke merely
   ABUTTING a head's box — the neighbouring note's stroke — is protected too.
   Every existing fixture puts its head well under its stroke, so none sat on
   the boundary and the loosening was free. Closed with a fixture built AT it.
3. **The notehead class filter deleted** in `_notehead_boxes_for_cell`, so an
   accidental, a rest or a clef would protect a stroke — **the rule that
   exists to tell a sharp's two strokes from two stems, protecting the
   sharp.** Closed directly.

**All three are now red: the closing re-run is 21 arms, 21 RED, 0 survivors, restore VERIFIED** (`out/mutation-battery-after-closing.txt`). ⚠️⚠️ **It reads IDENTICALLY to the void original and means the opposite thing**: the original could not have said anything else, and this one survived a judge that CAN say two identical trees are identical. *A number is not a result until the instrument that produced it can fail.* ⚠️ Note what the three survivors have in common: none changed
an output on any fixture in the suite, which is exactly the population a
battery exists to reach and a green suite cannot.

**AS PUBLISHED (VOID): 21 arms, 21 RED, 0 survivors, 0 bad anchors, restore
VERIFIED by md5**,
baseline green (115 tests) before any arm was read. Byte snapshot on disk, an
in-flight sentinel written before the first arm, and a refusal to start on a
dirty target without `--force`.

Nine arms attack the gate itself (the partner form, `None`-vs-`[]`, the flag
firing without data, the data firing without the flag, the default flipping
ON, the OFF test becoming a deny-list, touching-counts overlap, x-only
matching, the `detect_lines` forward being dropped), three the wiring, five
the arms' own controls, and three the per-bar probe's refusal and composition
check.

⚠️ The battery does **not** run the plate arms (~110 s each); every arm here is
a claim about the RULE, and the plate arms' own faithfulness, one-sidedness and
positive controls are what guard those.

---

## 8. WHAT IS NOT ESTABLISHED

* **ACCURACY. No crop was cut.** Not one of the 80 or 152 rescued strokes has
  been checked against the print, and neither have the 3 hand cells the gate
  makes worse. Every accuracy statement here is agreement between two of our
  own readings — the CV rung and the detector — which §5 shows can agree and
  both be wrong about the same ink.
* **§5c's mechanism is measured only as far as the geometry goes.** That the
  ~6-space stroke is *a stem fused through its own stacked noteheads* and the
  ~3.1-space one *the head column beside it* is consistent with the heights,
  the x-clusters and with staff 1's two-note chords producing zero deletions —
  it is **not** confirmed against a crop.
* **No OMR-NED figure is claimed, deliberately.** The metric is symmetric and
  rewards under-prediction, so it would pay for emitting fewer strokes whether
  or not that was right.
* **No export, no file.** This is a GATHER-stage measurement of what the
  adjudicator WOULD see; nothing was re-adjudicated and no MusicXML was
  written. The 73 and 178 are heads that stop abstaining, **not** notes that
  come out right.
* **n = 2 documents, 2 publishers, 4 pages each**, plus 4 other scores at 10
  hand-counted cells. Both plates are scans; **the engraved family is
  untouched except by the reference sheet**, which is a LilyPond render and not
  a publisher.
* **The per-bar result is ONE thickness of four** — the other three refuse
  because the page re-segments, so `n = 1` there and the refusal is honest
  rather than a workaround.
* **`_resolve_cells` drops 4 of 14 hand cells** on today's tree. The two arms
  are compared on the same 10, which is the comparison that is valid, but the
  fixture is 71% of what it was when the rule was measured on it.
* **The 614 stems carrying no detected notehead** (sibling lane §1a) are
  untouched by this and the gate cannot protect them.
* **~90% of the 793 is still unexplained**, exactly as the sibling lane left
  it. This is 9.2% of it on one plate and 11.6% on the other.

---

## 9. Running it

```bash
B=benchmarks/omr-stem-notehead-gate-2026-09
L=library/editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf
K=library/editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf

python3 $B/gate_arm.py --pdf "$L" --pages 1,2,3,4 --tag litolff-beethoven5-p1-p4
python3 $B/gate_arm.py --pdf "$K" --pages 0,1,2,3 --tag breitkopf-brahms1-p0-p3
python3 $B/fixture_arm.py            # both fixtures that justified the rule
python3 $B/probe_reference_sheet.py  # why the sheet loses the page-level win
python3 $B/probe_per_bar.py          # the per-bar truth, where it is usable
python3 $B/mutate.py                 # 21 arms
python3 -m pytest tools/omr/tests/test_stem_notehead_gate.py
```

Every arm prints REACH first and exits **2** declaring itself DEAD at zero.
`out/*.json` is each one's own output, committed beside it.
