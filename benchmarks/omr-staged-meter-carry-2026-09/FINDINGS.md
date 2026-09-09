# The meter carry — measured on both sides, and OFF because of the second one

`OMR_METER_CARRY`, `tools/omr/staged/adjudicators/rhythm.py`. Default **`0`**.

A meter is a fact of the **MOVEMENT**: printed at its start and nowhere else.
Everything in the staged pipeline works a system at a time, so the second page
of a 2/4 movement has no meter at all — and the right answer is sitting in the
same log one page earlier, with nothing looking for it. `transcribe` carries it
(`source="carried_from_previous_page"`); the staged pipeline had no carry.

This adds one. It fires **only from an abstention branch**, so it can never
overturn a reading, and it records where the value came from and how far.

---

## 1. Both arms, one document, one call each

Beethoven 5 / Litolff `984073`, weights `hollow-graft-shift09`, `--pages 0-2`.

⚠️ **The control first, because it is what makes the rest attributable.**
Flag-OFF reproduces the pre-change run **exactly** — all 4,498 verdicts
identical in outcome, reason and value, and all 12,782 observations. So the
change is inert when off, *and* this document runs deterministically, which is
the only reason an ON/OFF delta on two separate runs can be read as the flag's.

### What the carry decided

| system | flag OFF | flag ON |
|---|---|---|
| `system/1/0` | **decided `2/4`**, `voted`, 12 of 12 staves | unchanged |
| `system/2/0` | abstained `no_evidence` | **decided `2/4`**, `carried` |
| `system/2/1` | abstained `too_few_staves_read_it` | **decided `2/4`**, `carried` |

Both carries record `carried_from: system/1/0`, `pages_since_read: 1`,
`source_share: 1.0`, `source_staves_spoke: 12`, and the abstention they
replaced.

### What that changed downstream

**Exactly two quantities move: `meter` (2) and `duration` (111).** Every one of
the 111 is on page 2. Nothing else in the log moves at all.

| durations that moved | OFF → ON | reason |
|--:|---|---|
| **77** | 4.0 → **2.0** | `rest_class` → `whole_rest_means_the_bar` |
| **20** | *none at all* → 0.5 | `beams_ambiguous` → `meter_reconciliation` |
| 5 | 2.0 → 1.0 | `head_and_marks` → `meter_reconciliation` |
| 4 | 0.5 → 1.0 | `head_and_marks` → `meter_reconciliation` |
| 2 | 0.25 → 0.5 | `head_and_marks` → `meter_reconciliation` |
| **2** | *none at all* → 1.0 | `beams_ambiguous` → `meter_reconciliation` |
| 1 | 1.0 → 2.0 | `head_and_marks` → `meter_reconciliation` |

⚠️ The predecessor handoff estimated **83** mis-sized lone whole rests on this
page. Measured, it is **77**. Quoted as measured.

### And in the file

`--musicxml`, same two arms:

| | OFF | ON |
|---|--:|--:|
| `<time>` elements | 12 | **25** |
| whole rests written `<type>whole</type>` at **4.0 ql** in a **2.0 ql** bar | **194** | **70** |
| `<rest measure="yes"/>` at 2.0 ql | 108 | **231** |
| `written.notes` | 646 | **664** |
| `notes_not_written_total` | 219 | **201** |
| `not_written.duration_narrowed` | 165 | **147** |
| `not_written.no_pitch` | 54 | 54 |
| `written.empty_bars_padded_without_meter` | **47** | *field gone* |
| `detected_and_unrepresented_total` | 659 | 659 |

**123 whole rests stop being 4.0 quarters of silence in a 2.0-quarter bar.**
The arithmetic is checked against each part's own `divisions` and not assumed:
`divisions=48`, `<duration>96` = 2.0 ql = one bar of 2/4, in both arms — what
changes is how many bars *reach* it. The ON file parses under music21, 12 parts.

⚠️ **Two of those rows are controls, and they are the ones that did NOT move.**
`no_pitch` is unchanged because a meter says nothing about pitch, and
`detected_and_unrepresented_total` is unchanged because the carry reads no new
ink. A carry that had moved either would have been doing something it has no
business doing.

⚠️ **A −1 was chased rather than rounded off.** Total rests went 433 → 432, so
one rest is *not* accounted for by the 123 conversions. It is P4 measure 44: in
the OFF arm a whole rest at 192 (4.0 ql), in the ON arm a **B3 quarter note**.
Nothing was lost — that bar had been *padded* because its only note had no
duration (`beams_ambiguous`), and `meter_reconciliation` gave the note a value,
so the pad is no longer needed. It is one of the 18 recovered notes, arriving
in the rest column.

The three counts agree to the unit: **18 notes recovered = 18 fewer
`duration_narrowed` = +18 `written.notes`.**

---

## 2. ⚠️⚠️ THE HAZARD, ON THE SAME DOCUMENT — WHY THE FLAG IS OFF

Page 17 of `984073` is the ***Andante con moto***: a **new movement**, printing
`3/8` on every one of its staves. Run `--pages 1,17`:

| system | flag OFF | flag ON |
|---|---|---|
| `system/1/0` (mvt 1) | decided `2/4`, `voted` | unchanged |
| `system/17/0` (mvt 2) | abstained `no_evidence` | **decided `2/4`** ← **wrong, it is 3/8** |
| `system/17/1` | abstained `no_evidence` | **decided `2/4`** ← wrong |
| `system/17/2` | abstained `no_evidence` | **decided `2/4`** ← wrong |

Each carries `pages_since_read: 16`.

**The movement start reads nothing, and this is diagnosed, not guessed.** The
template reader **ran on all 20 staves of page 17** and declined
`below_threshold` on every one — the record says so, it is not silence. `3/8`
*is* in `DEFAULT_METERS`, so it is not a missing template. Rendering the ink
shows why: Litolff sets `3` over `8` as heavy, nearly-touching digits that do
not correlate with the Bravura templates. That is the digit-template family
CLAUDE.md's standing rule says is **never tuned on one edition**.

So an unconditional carry does not merely risk crossing a movement boundary on
this document — **it does cross it**, and then keeps the wrong meter for the
rest of the movement, since nothing later in the Andante reads one either.

### Four guards were looked for. All four are REFUTED by measurement.

1. **"A movement start reads SOME meter; a continuation reads none."**
   **Inverted.** The continuation systems on pages 14-16 read **1-4** spurious
   `C`/`4/4` each; the movement start reads **0**.
2. **The key signature changes at a movement boundary.** Unusable on a scan.
   Only a handful of staves per system decide a key and they disagree with each
   other — `p14/s1` reads `{-5, -3, -1, 2}` — and the Andante's true **−4** is
   never among the readings anywhere on page 17.
3. **The printed tempo heading.** Page 17 prints "Andante con moto." three
   times and this is the right signal *in principle* — the engraver's own mark
   for "a new movement starts here". `direction` yields **0 decided verdicts**
   in the staged record today, on both runs, so it cannot be asked.
4. **A distance bound.** Decisive, and it is arithmetic rather than a sweep:
   movement 1 occupies pages 1-16, so a meter read on page 1 legitimately
   governs **16 pages**. Any bound under 16 truncates a legitimate carry *in
   this document*; any bound of 16 or more reaches the Andante. **No reach
   constant separates benefit from hazard.**

**So the blocking input is named, and it is a MOVEMENT-START signal — not a
threshold.** Flip the flag the day one exists. The likeliest source is (3): the
tempo heading is genuinely printed and genuinely diagnostic, and it is blocked
on `direction` being a stub rather than on anything about movements.

---

## 3. Two design rules, and why each is in the code rather than here

**A carry NEVER chains onto a carry.** Only a `voted` verdict is a source, so
`pages_since_read` is the true distance back to *ink*. That is what makes the
number worth reading: a meter carried 16 pages is visibly suspect in the
record, where a chain of sixteen one-page hops would each have looked local.
Pinned by `test_a_carry_NEVER_chains_onto_a_carry`, which goes RED when the
`voted`-only line is removed.

**A carry never overturns a reading.** It is reached only from the three
abstention branches, so it is structurally incapable of overwriting a system
that read its own meter — which is also why the coverage floor (`9dec5cb6`)
had to land first: without it, the 3-of-11 spurious `C` on `system/2/1` would
have been a *decision*, and would then have been the thing that carried.

---

## 4. Reproducing

```bash
ln -sfn <main checkout>/library library        # the PDF; no venv needed
PDF=library/editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf
W=tools/omr/training/data/weights/deepscoresv2-yolov8l-hollow-graft-shift09-2026-09-04.pt

# benefit — the two arms of §1
OMR_METER_CARRY=0 python3 -m tools.omr.staged "$PDF" --pages 0-2 --weights "$W" \
    --out off.json --musicxml off.musicxml
OMR_METER_CARRY=1 python3 -m tools.omr.staged "$PDF" --pages 0-2 --weights "$W" \
    --out on.json  --musicxml on.musicxml

# hazard — §2
OMR_METER_CARRY=1 python3 -m tools.omr.staged "$PDF" --pages 1,17 --weights "$W" \
    --out hazard.json
```

`out/` holds the meter verdicts of all four runs and the two coverage reports.

⚠️ Measure a carry on a **multi-page run only**. The scan gate transcribes ONE
PAGE PER ROW, which silently disables every page-spanning mechanism — it would
report this change at exactly zero, twice.

---

## 5. THE SECOND WITNESS — do the bars name the meter? (added after review)

Sean, on the §2 conclusion: *"I want to make sure we don't get stuck in binary
on/off based on current measurements... it may be that the time sig gives the
measure context or it may be that the measure math helps determine the time
signature — which is why we separated reading from adjudication."*

**That is the right reading and §2 was the wrong shape.** The carry was built
to DECIDE, so a case where it decides wrongly could only be answered by
switching it off. It should arrive as a **candidate** and be confirmed or
refuted by the bars it claims to govern — then a movement boundary needs no
movement detector, because the Andante's bars simply contradict the previous
movement's meter.

`probe_bar_sums.py`, on the **flag-OFF** exports (with the carry on,
`reconcile_duration` rewrites durations FROM the meter, so bar sums there are
downstream of what is being tested). Chord members skipped, lone measure/whole
rests skipped, empty bars skipped — each for a measured reason, see the
module docstring.

| | page 1 — meter IS read (**control**) | page 17 — Andante, meter reads nothing |
|---|--:|--:|
| printed meter | 2/4 = 2.0 ql | 3/8 = 1.5 ql |
| assessable bars | 84 | 135 |
| **modal bar sum** | **2.0 ✓** | **1.5 ✓** |
| bars exactly on the printed meter | 42 (0.500) | 18 (0.133) |
| bars at 2.0 vs 1.5 | 42 vs 4 — **10.5× for 2/4** | 11 vs 18 — **1.6× for 3/8** |

**The mode is the printed meter on BOTH pages, including the one where nothing
read it.** So the bar math does carry the signal, and the page-1 row is the
positive control that the method works where the answer is independently known.

⚠️ **But on page 17 it is a lean, not a plateau.** 18 against 11 is a 7-bar
margin over the meter the carry would have imposed. That is enough to REFUSE a
carried `2/4` — which is all the second witness has to do — and **not** enough
to name `3/8` on its own. The honest design is therefore: a carried meter is a
candidate, the bars may veto it, and where they veto without naming a
replacement the system ABSTAINS. That is strictly better than today's flag,
because the wrong answer is removed without the right one being invented.

## 6. ⚠️⚠️ THE CHORD IS GROUPED AFTER THE STAGE THAT NEEDS IT

Sean, same review: *"we may need to reconsider where the chord happened in
precedence?"* **Confirmed, and it is a live defect rather than a probe detail.**

`grep -rn chord tools/omr/staged/` outside `export.py` returns **nothing**, and
the record has **no chord, event, onset or voicing quantity at all**.
`group_chords_in_measure` is called from exactly one place —
`export._events`, at serialisation time.

So every stage before EXPORT treats each chord member as a separate
time-advancing event. That includes **`consequences.reconcile_duration`**,
which runs in EVALUATE, sums `Q.DURATION` over a cell, and compares the total
to the meter — the pipeline's own bar-sum check, computed on ungrouped
durations.

Measured on the same two exports, grouped (what the file says) against
ungrouped (what `reconcile_duration` sums):

| | page 1 | page 17 |
|---|--:|--:|
| bars containing a chord | 11 of 83 (13.3%) | **50 of 131 (38.2%)** |
| bars exactly on the meter, **grouped** | 42 | **18** |
| bars exactly on the meter, **ungrouped** | 41 | **13** |

**On page 17 the double-count destroys 5 of the 18 correct bars — 28% of the
evidence — before any consumer sees it.** The inflation is not a constant to
subtract, either: it ranges 0.125 → 6.0 quarter-lengths across 13 distinct
values.

Two consequences worth carrying:

1. **`reconcile_duration` is silently under-firing** wherever a bar holds a
   chord, because its total can never match the meter there. It fired 13 times
   on the `--pages 0-2` run.
2. **The second witness of §5 cannot be built on the record as it stands.**
   Making the bar sum the meter's corroborator requires the chord grouping to
   become a decided quantity — one event, N noteheads — *before* EVALUATE,
   rather than an export-time convenience. That is the precedence fix, and it
   is the real prerequisite for §5.

⚠️ Note this also means §5's own table, measured off the EXPORT, is the
*optimistic* one: it is what the bar sum could say once grouping precedes it,
not what any stage can read today.


---

## 7. THE CARRY IS NOW WEIGHED, NOT GATED — and the flag can come off the binary

Sean, 2026-09-10, on §2's default-OFF conclusion:

> *"I want to make sure that we don't get stuck in binary on or off based on
> current measurements ... We need probability based decisions with layers of
> information ... this is where the math that can be determined by its own
> equation could be weighed more heavily than information that can only be
> derived. If the measure is what we think it is - does the math of the notes
> make sense. If not then the meter should decrease in probability."*

§2 was the wrong shape. The carry was built to DECIDE, so a case where it
decided wrongly could only be answered by switching it off. It now arrives as
a **candidate** whose standing the bars move.

### The mechanism

A carried meter enters as one signed term and every bar it claims to govern
adds another:

| term | weight |
|---|--:|
| `carried_from_read_meter` | **+1.0** |
| each bar that FITS | **+1.0** |
| each bar that does NOT | **−1.0** |
| `METER_CARRY_FLOOR` (support needed) | **2.0** |
| `METER_CARRY_MIN_BARS` (evidence needed) | **2** |

⚠️ **The ordering is structural, not tuned.** At these weights two net
contradicting bars outweigh ANY carry, and no amount of carrying outweighs the
bars — Sean's principle made a property of the constants, asserted directly by
`test_the_BARS_outweigh_the_carry_and_the_carry_never_outweighs_them` so that a
sweep breaking it fails even if every behavioural test still passes.

⚠️ **NOT a probability, and the ban it respects is narrower than it reads.**
`adjudicate`'s docstring forbids probabilities because the one attempt at
calibrated identity probabilities reached ECE 0.1277 and failed worst at the
top of the range (a bin promising 0.989, delivering 0.692). Signed terms summed
against a threshold are the same shape without the claim. ⚠️ **And that
objection does not extend to this family**: the failure was diagnosed as the
CORPUS, and a bar sum is `Checkable.CHECKABLE` — provable against itself on any
document with no truth file — so it could generate its own calibration data
from the score library alone. Nothing here does that yet; it is the open route
to genuine probabilities where the math self-checks.

### Measured, same document, same weights

| system | outcome | support | bars |
|---|---|--:|---|
| `system/2/0` — continuation, truth 2/4 | **carried** | **+7.0** | 8 fit / 2 not |
| `system/2/1` — continuation, truth 2/4 | **carried** | **+8.0** | 8 fit / 1 not |
| `system/17/0` — *Andante*, truth 3/8 | **refused** | **−3.0** | 0 fit / 4 not |
| `system/17/1` — *Andante* | **refused** | — | only 1 assessable bar |
| `system/17/2` — *Andante* | **refused** | **−1.0** | 0 fit / 2 not |

**All three Andante systems refuse the wrong meter, with no movement detector
anywhere in the pipeline**, and both continuation systems carry.

⚠️ **A LEAK WAS FOUND AND CLOSED, and it is why `METER_CARRY_MIN_BARS` exists.**
At first `system/17/1` **carried `2/4` onto the Andante** at support exactly
+2.0 — one bar that happened to sum to 2.0, nothing contradicting it, landing
precisely on the floor. The fix is a SEPARATE constant rather than a higher
floor: `A-CLEF-6` records that `MARGIN_FLOOR` carries two jobs and that a sweep
of it moves both behaviours at once. *"Is there enough evidence to judge?"* and
*"does the evidence support it?"* are two questions.

### In the file (pages 0-2, carry OFF vs ON)

| | OFF | ON |
|---|--:|--:|
| whole rests written at **4.0 ql in a 2.0 ql bar** | **194** | **70** |
| `<rest measure="yes"/>` | 108 | **232** |
| `written.notes` | 648 | **665** |
| `not_written.duration_narrowed` | 163 | **146** |
| `written.empty_bars_padded_without_meter` | **47** | *field gone* |
| `not_written.no_pitch` (control) | 54 | 54 |
| `reconcile_duration` fired | 13 *(pre-`Q.EVENT`)* | **47** |

## 8. ⚠️ THE PIPELINE'S ONE SANCTIONED LOOP, NOW DECLARED

Corroboration makes the meter depend on the durations, and
`reconcile_duration` rewrites those same durations FROM the meter. The record
detected it and refused: `UphillConsequence`, *"the new value was derived
through something that depends on the value it replaces."*

**The guard was right to stop and it is not a fixpoint.** Unrolled it is
`duration_v1 -> meter -> duration_v2` — a straight line, run once and stopped,
which is the rule `transcribe` has always stated as *"vote once, repair once"*.
Sean's call was to allow it, and the exemption is **declared per rule**
(`rule(single_pass=True)` → `Verdict.single_pass_revision`) rather than as a
global loosening, so it cannot spread by accident. What makes it safe is the
BOUND, not the flag: at most one note, an exact landing, a unique answer.

⚠️ The error message now names the exemption, so the next person meets a
choice rather than a wall — and the guard escalated exactly as its own text
instructs.

## 9. ⚠️ AN OPERATIONAL TRAP THAT INVALIDATED A MUTATION RUN

macOS system Python caches bytecode **outside the source tree**, in
`~/Library/Caches/com.apple.python/<abs path>/`. `find . -name __pycache__` does
not see it and `rm -rf __pycache__` does not clear it.

Live consequence: after a mutation was reverted, the *mutated* constant stayed
live — `grep` showed `-1.0` in the file while `import` returned `-0.0`, on a
file whose md5 matched `inspect.getsource`. A restored tree kept failing a test
it should have passed, and, worse, a later mutation ran on top of an earlier
one without saying so.

**So: clear that path between mutation arms**, and treat a disagreement between
`grep` and `import` as this until proved otherwise. Same family as the cached
`scan_eval` A/B already recorded in CLAUDE.md — the arms did not run the code
you think they ran, and nothing in the output says so.


---

## 10. ⚠️⚠️ CORRECTION TO §7 — THE ANDANTE REFUSAL IS SAFE BUT NOT DISCRIMINATING

Sean, on reading §7: *"Did we solve this? It feels a ways out to me."* He was
right, and the control that settles it is one I had not run.

§7 reports that all three *Andante* systems refuse the carried `2/4` and reads
that as **the bars contradicting the old movement's meter**. An alternative
explanation fits the same numbers: **page 2 reads well and page 17 reads
badly, and a noisy page refuses everything.** The two are distinguished by one
question — *would page 17 refuse the CORRECT meter too?*

It would. Scored against `3/8`, the meter page 17 actually prints:

| page/system | candidate | fit | not | support | verdict |
|---|---|--:|--:|--:|---|
| p1/sys0 | **TRUE 2/4** | 13 | 0 | **+14.0** | carries |
| p1/sys0 | other (3/8) | 0 | 13 | −12.0 | refuses |
| p2/sys0 | **TRUE 2/4** | 8 | 2 | **+7.0** | carries |
| p2/sys0 | other (3/8) | 0 | 10 | −9.0 | refuses |
| p2/sys1 | **TRUE 2/4** | 15 | 0 | **+16.0** | carries |
| p2/sys1 | other (3/8) | 0 | 15 | −14.0 | refuses |
| **p17/sys0** | **TRUE 3/8** | 1 | 3 | **−1.0** | **refuses** |
| p17/sys0 | other (2/4) | 0 | 4 | −3.0 | refuses |
| **p17/sys2** | **TRUE 3/8** | 0 | 2 | **−1.0** | **refuses** |
| p17/sys2 | other (2/4) | 0 | 2 | −1.0 | refuses |

**So what is actually established, and what is not:**

* ✅ **Where the bars can speak, they discriminate, in both directions.** On the
  three well-read systems the true meter scores +14, +7, +16 and the wrong one
  −12, −9, −14. That gap is real and it is the mechanism working.
* ❌ **The *Andante* refusal is NOT evidence that the mechanism detects a
  movement boundary.** Page 17 refuses everything, the right answer included.
  The protection there comes from *"when the page cannot speak, abstain"* — a
  safe default, not a reading.
* ⚠️ So the boundary case remains **untested on a page that reads well**. A new
  movement whose page reads badly is protected by the abstention; a new
  movement whose page reads WELL should be caught by the bars (p2's "other"
  column shows what a well-read page does to a wrong meter — 0 fit, 10-15 not)
  but **no such page has been measured.**

⚠️ **A methodological note, because it nearly produced a second wrong claim.**
The first run of this control keyed bars by SYSTEM INDEX and dropped the page,
so page 1's systems merged with page 17's and p17/sys0 appeared to score
**+7.0 for 2/4** — it would have been reported as "the mechanism carries a
wrong meter onto the Andante". The tell was that it contradicted the live run's
own recorded detail (`0 fit / 4 not`). **Check a probe against the pipeline's
own record before believing it.**

### What "solved" would take

1. A movement boundary on a page that reads well — the case the mechanism is
   actually claimed to handle, and the one no measurement covers.
2. A second document and publisher. Everything above is one edition.
3. Weights that are measured rather than asserted. They are symmetric and
   declared unmeasured; `METER_CARRY_MIN_STAVES_PER_BAR = 3` is set by analogy
   to `METER_COVERAGE_FLOOR` and never measured at all.
4. A calibration pass. The `CHECKABLE` route (a bar sum needs no truth file)
   makes this reachable across the library and nothing has built it.

**Until then the honest summary is: the carry is SAFE — it never writes a
wrong meter on any page measured — and its boundary behaviour is
under-determined.** Default `0` stands, and the reason is now (1) above rather
than "n".


---

## 11. A REAL MID-MOVEMENT METER CHANGE, LOCATED — and what it shows

§10 says the boundary case is untested because the one boundary available is on
a page that cannot speak. So one was looked for. **Found, on the same document,
so nothing else varies.**

Scanning all 1,745 reference encodings for a part whose `<time>` changes
mid-piece returns **230 works**. The best is Beethoven 5 itself:
`beethoven--symphony-5--mvt4` encodes **4/4 → 3/4 at bar 155 → 4/4 at bar 209
→ 2/2 at bar 364**.

**In the Litolff print that is page 62** (bar 147 top-left): a double barline
mid-system, "Tempo I. ♩=96", and a new time signature on every staff. ⚠️ The
change is **MID-SYSTEM**, so one system contains two meters — a harder and more
useful case than a page boundary.

Run `--pages 61-62`:

* ⚠️ **The printed 3/4 is NOT read.** `meter_template` returns `C` on 2 staves
  and nothing else; the system abstains `too_few_staves_read_it`. Same as page
  17 — on this edition the glyph route to a meter change is closed.
* ✅ **The BAR SUMS see it.** Page 62 system 0, modal sum per bar across staves:

  | bar # | staves | mode | agreement |
  |--:|--:|--:|--:|
  | 3 | 11 | 4.0 | 9/11 |
  | 5 | 12 | 4.0 | 6/12 |
  | **6** | **16** | **3.0** | **9/16** |
  | 9, 10 | 1 each | 3.0 | — |

  Bar 6 carries the **strongest cross-staff agreement on the page** and it
  agrees on the NEW meter. The arithmetic finds the change the reader missed.

⚠️ **BUT THE PROPOSED DISCRIMINATOR CANNOT FIRE HERE, and that is the finding.**
The rule Sean describes — *if the dissenting bars agree with EACH OTHER it is a
meter change; if they are incoherent it is noise* — needs at least two
dissenters. Against a carried 4/4 only three bars clear the quorum (≥3 staves,
≥50% agreeing): two at 4.0 and **one** at 3.0. The bars that would prove
coherence (9 and 10, both 3.0) read on **one staff each** and fall below it.

So the evidence exists on the page and sits under the quorum. **Building the
coherence rule against this page would repeat §10's mistake one step earlier:
a mechanism validated where it cannot be exercised.**

### The route that avoids it

Test the rule where reading quality is NOT the confound first.
`orchestral_eval` renders a truth MXL through LilyPond, and
`beethoven--symphony-5--mvt4` is in the library — so the same meter change can
be produced engraved. If the rule fires there it is a rule; if it does not, no
amount of scan work would have said so. Only then is the scan number about
reach rather than about legibility.

⚠️ **Two things unverified here**, recorded rather than smoothed over: the page
prints bar 147 so cell 6 should be bar 153 against the reference's 155 — the
cell→bar alignment is off by about two and the cause is unchecked; and the
page's early bars read 6.0, 5.0, 6.0, so it is noisy too, only less so than
page 17.

**Not built. Parked at Sean's request for a design pass.**


---

## 12. WHAT WAS ACTUALLY PREVENTING "3/4" — three wiring facts, no evidence problem

Sean: *"Modal sum + some written 3/4 should be more than enough. What is
actually preventing us from saying 3/4 with what we have?"*

Nothing about the evidence. Three things in the wiring, in order of cost:

1. ⚠️ **BOTH METER READERS LOOKED ONLY AT THE STAFF HEADER.**
   `_gather_meter_glyphs` hardcoded `R.cell(p, ..., 0)` and the template reader
   uses `header_cells_for_page`. A meter printed at a CHANGE is outside both
   windows by construction — so on p.62 the detector's `timeSig3` and five
   `timeSig4` sat on the record as ordinary `glyph_box` rows while
   `meter_glyph` abstained `no_detections` on all **17** staves. **FIXED**: the
   gather now walks every cell and records the CELL on each row, because WHERE
   a meter glyph stands is the whole of its meaning — at cell 0 it states the
   staff's meter, anywhere else it announces a change at that bar.
2. **The decision ignores `Q.METER_GLYPH`.** Declared in `wants`, never read —
   already on `KNOWN_GAPS` in those words. The vote runs on `meter_template`
   alone, so even a header detection reaches no decision. **NOT YET FIXED**,
   which is why the widening above is measured INERT (meter verdicts
   byte-identical on `--pages 0-2`).
3. **`Q.METER` is `scope=Kind.SYSTEM`.** One verdict per system, so "4/4 until
   bar 8, 3/4 after" is inexpressible even with perfect evidence. This is the
   real design change and it is a SUBJECT question: a meter is a property of a
   RANGE OF BARS, not of a system.

### ⚠️ CORRECTION TO §11: the alignment was NOT off by two

§11 records the cell→bar alignment as off by about two and the cause as
unchecked. **It is not off.** The page prints bar **147** at top-left, so cell
8 is bar **155** — and the reference's change is at bar **155**. The
`timeSig3`+`timeSig4` lands on it **exactly**.

What §11 actually compared was the BAR-MATH signal (a modal 3.0 at cell 6),
which is two cells early and is therefore *not* the change. So on this page:

| signal | says | truth |
|---|---|---|
| **meter glyph** | change at **cell 8** | **bar 155 = cell 8 ✓** |
| bar math | anomaly at cell 6 | ✗ two cells early |

**That inverts the weighting rationale, in Sean's favour**: the glyph is the
precise signal and the arithmetic is the noisy corroborator, not the other way
round. `measure_partition` decided **13 cells on all 17 staves**, so cell
indices do align across the system and the comparison is sound.

### ⚠️ Two things the same measurement rules out or complicates

* **The "undefined blob" tier cannot be built from the detection record.**
  Sean: *"an undefined blob should also be a factor — there is something there
  but we aren't sure what it is."* Sound idea, and there is precedent
  (`direction_text._blank_detections` subtracts every detection from the page
  ink so "find the text" becomes "find the ink"). But at p.62 cell 8 the other
  15 staves carry **no unclassified detection** at the meter column — the ink
  was not detected at all, rather than detected and unnamed. So the tier needs
  a RASTER pass in GATHER, not a re-weighting of what is already recorded.
* ⚠️ **The whole-rest exclusion thins the evidence exactly where a change
  happens.** It is necessary (§7) — a whole rest would read our own default
  back as evidence — but a meter change is typically followed by most
  instruments RESTING, so cells 7-12 of this system drop to one assessable
  staff each. **The bar-math corroborator is systematically weakest
  immediately after a change**, which is another reason the glyph must carry
  the weight.


---

## 13. THE METER CHANGE, BUILT — glyph opens it, math settles it

Sean's ordering, implemented and measured.

**The value shape changed.** `Q.METER` now carries `segments` — one entry per
stretch of bars with the `from_cell` it starts at — and `record.meter_at(value,
cell)` is how a bar's meter is read. One fact, not two; the alternative (a
separate change fact beside an unchanged system meter) was refused on this
project's own history of two records of one thing drifting apart.

**Weights, in Sean's order:**

| term | weight |
|---|--:|
| a staff reading a COMPLETE meter (numerator over denominator) at that bar | **+3.0** |
| a digit at that bar that does not pair | +0.5 |
| each following bar whose length matches | +1.0 |
| each that does not | −1.0 |
| `METER_CHANGE_FLOOR` | 3.0 |

So **one staff reading a printed time signature clears the floor alone**, and
two contradicting bars sink it again. `_meter_from_digits` reads the stack: the
numerator is simply the higher digit, which is what `y_center` is for.

### Measured

| run | result |
|---|---|
| **p.62** (prints 3/4 at bar 155 = cell 8) | **`3/4` at cell 8** — support 3.0, staff 11 |
| p.61 | abstains, no change |
| pages 0-2 (no change) | 1 segment each, **no spurious change** |
| p.17 (new movement, no mid-system change) | no change proposed |

**The change lands on the exact printed bar**, and the negative controls are
clean.

⚠️ **A FALSE POSITIVE WAS FOUND AND GATED.** Before the plausibility gate, p.61
proposed a change to **`1/1`** at support 5.0, out of `timeSig1` detections — a
confident reading of a meter nobody has ever engraved. Proposals are now
restricted to `time_signature_locator.DEFAULT_METERS`, imported rather than
restated so the two readers cannot drift about what a meter is.

⚠️ **AND THE GATE ITSELF FAILED SILENTLY FIRST.** It was written as
`try: ... except Exception: frozenset()`, which swallowed a wrong relative
import and left the set EMPTY — so the gate admitted nothing and every change
was refused. That is this repo's own *"an optional pass may abstain quietly, it
may not fail like a defect quietly"*, reproduced inside the fix for a different
quiet failure. It is now a hard module-level import.

### ⚠️ What is NOT established

* **n = 1 change, 1 document.** One true positive is one.
* **The bar-math half is barely exercised.** Even on the case that works it
  contributed `0 fit / 0 not`, because the whole-rest exclusion removes exactly
  the post-change bars — a change is typically followed by most instruments
  resting. So the measured result rests on the GLYPH alone.
* ⚠️ **A change with NO glyph cannot be proposed at all.** Sean: *"If there is
  no meter glyph then we have to deal with bar sums... We have 12 systems and
  10 of them say 4/4 for 6 measures."* That is right and is NOT built. The
  reason a run was not admitted as a proposer is p.17, where the bars name
  nothing coherent and would manufacture meters out of noise — but the
  discriminator is the RUN (10 staves × 6 bars is not 4 bars at 4 different
  values), which is exactly Sean's *"for how long — the longer the more
  likely"*. **This is the next piece of work.**
