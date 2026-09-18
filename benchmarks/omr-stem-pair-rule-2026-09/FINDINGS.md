# The stem misses: one hypothesis refuted, one supported and bounded at 9.2%

**2026-09-17. No code under `tools/` is changed** — `git diff` against the
branch point touches `benchmarks/` only. Everything here is a measurement.

Sean's question, verbatim: *"Can you look at the stem issue and see if it is
related to multiple notes sharing stems or the sharps and flats issue"*.

| | verdict | the number |
|---|---|---|
| **A — multiple notes sharing one stem** | **REFUTED** | shared stems WORK (337 of 1,920 stems carry 2-5 heads); x-columns share their outcome **more** than a bar-matched null (118 mixed against 156.1, 0/400 draws below); the displaced head of a second is **1 of 793** |
| **B — the sharps-and-flats pair rule** | **SUPPORTED, and bounded** | `_drop_paired_strokes` deletes 244 strokes and **73 of the 793 stemless heads (9.2%)** would stop abstaining without it |
| **B's stated premise** | **FALSE on this plate** | of the 80 deleted strokes that carry a notehead, **62 (77.5%) were paired with ANOTHER stroke that carries a notehead** — two genuine stems eating each other, not an accidental |

⚠️ **Neither hypothesis explains most of the 793.** B accounts for 9.2%; A for
essentially none. **~90% remains where the 2026-09-17 handoff §4 left it —
ink the CV rung did not read.** Nothing here moves that.

Document: Litolff Beethoven 5 pp.1-4, the committed
`library/_shared-records/beethoven5-p1-p4-ink-identity.record.json`
(provenance commit `e38dbc25`, clean). **n = 1 document, 1 publisher, 4 pages
of ~16**, the low-res bitonal end of the corpus, for every Litolff figure
below.

---

## 0. Controls, before any finding

Three, each able to fail, and the first two announced themselves by matching
rather than by passing silently.

**POSITIVE (record joins).** `probe_shared_stems.py` reproduces the committed
`omr-stem-direction-2026-09/out/is-the-ink-there.json` before reporting
anything of its own: `no_stem` **793**, half notes **309 stemmed / 103 not**,
whole notes **8 / 9**, `no stem ink anywhere in the bar` **211**. The three
join traps this thread already paid for (`Q.GLYPH_BOX`'s name-first tuple,
`Subject.at(Kind.CELL)` rather than string surgery, stem rows on the CELL) are
all live in these probes and a slip in any of them shows here.

**STRUCTURAL (the re-gather).** The hypothesis-B arm re-rasterises the PDF and
re-runs phase 1 rather than reading the record's stems. dpi was **derived, not
assumed**: at 600 dpi `staff/1/0/0`'s line_ys come back `[1148, 1163, 1179,
1195, 1210]`, the record's own values **to the pixel** (300 dpi gives
`[574, 582, 589, 597, 605]`). Then, with the rule ON:

| | |
|---|--:|
| cells cut | **1,183** |
| stems found | **1,920** |
| record cells carrying stem ink | 783 |
| cell subjects in both | 783 |
| **cells where the stem box sets match EXACTLY** | **783 (100.0%)** |

So the ON arm is not *similar to* the record's gather, it **is** it.

**POSITIVE (the flag reaches the code).** Every arm refuses to report when its
two sides are identical — `probe_pair_rule.py` and `probe_rule_cost.py` both
exit 2 on that, and `probe_who_is_the_partner.py` asserts the shipped defaults
off `inspect.signature(detect_stems)` before restating them.

**And one more, because the partner attribution rests on it:** the pairing this
work re-derives must be the pairing the shipped function found. Scored as *the
set my restatement calls dropped vs `OFF minus ON`* — **0 cells disagree, of
1,183**.

---

## 1. HYPOTHESIS A IS REFUTED, on four independent readings

### 1a. Shared stems are not broken — they are the commonest thing on the page

Heads carried by each of the 1,920 detected stems, by the adjudicator's own
attachment test (`_boxes_overlap`, imported, not restated):

| heads on the stem | stems | |
|---|--:|--:|
| 0 | 614 | 32.0% |
| 1 | 969 | 50.5% |
| **2** | **243** | 12.7% |
| **3** | **74** | 3.9% |
| **4** | **16** | 0.8% |
| **5** | **4** | 0.2% |

**337 stems (17.6%) already carry more than one head.** Hypothesis A requires
the multi-head attachment to be failing; it is the second commonest outcome in
the table.

⚠️ **The 614 stems carrying NO head are a finding this work does not explain**
and are reported rather than folded in — a third of detected stems meet no
detected notehead. That is the same shortfall from the other side and belongs
with the handoff's §4, not here.

### 1b. Heads at one x SHARE their outcome — the opposite of A's prediction

A is a claim about *columns*: heads sharing a stem stand at one x, so if the
stem reaches the outer member and not the inner, columns should come out
**MIXED**. At a tolerance of 0.35 notehead widths there are **509 columns of
two or more heads** and **118 are mixed (23.2%)**. A share is not evidence
without a null, and there are two:

| null | mean | p5 | p95 | observed 118 |
|---|--:|--:|--:|---|
| labels shuffled across the whole column population | 300.2 | 283 | 317 | **0 of 400 draws ≤ it** |
| **labels shuffled WITHIN EACH CELL** | **156.1** | **146** | 167 | **0 of 400 draws ≤ it** |

⚠️ **The second null is the one that answers A, and the first alone would have
been unsound.** 211 of the 793 stemless heads sit in a bar where the CV rung
read no stem at all; those bars' columns are all-stemless for a reason that has
nothing to do with sharing a stem, and that drives the observed count below
chance on its own. Holding each bar's own mix constant, columns are **still**
less mixed than chance. **Standing at one x makes two heads MORE likely to
share an outcome, not less.**

The mixed share is flat across the tolerance sweep (22.7% at 0.20 through 28.6%
at 1.00), so nothing here rests on where the column boundary is drawn.

### 1c. The "stem stopped just short" population is 2 heads, not hundreds

The sharpest geometric form of A: a stem that **already serves a head**, whose
x-span covers a **stemless** head it fails to reach in y. That shape holds
**163 heads (20.6% of 793)** — and the y-gap says they are not near misses:

| median | p10 | p90 | within 0.25 sp | within 0.5 | within 1.0 | within 2.0 |
|--:|--:|--:|--:|--:|--:|--:|
| **3.19 spaces** | 1.23 | 7.16 | **2** | 3 | 13 | 47 |

A chord's heads sit inside its own stem's span. A stem three staff spaces away
is a different note's.

### 1d. The displaced head of a SECOND — the sharpest case A has — is 1 of 793

Sean's refinement, and it is the right general statement: **any notes sounding
on the same beat in one voice share ONE stem, at any interval** — a third, a
fifth, an octave. The second is special only because the two heads cannot both
sit on the same side of that stem, so one is **displaced to the far side**, and
that displaced head is the one whose box might miss the stem. Everything above
is already framed on **same x**, not on adjacent pitch, so the refinement
confirms the test rather than changing it — but it names the case that should
fail hardest.

Measured against `Q.NOTEHEAD_STAFF_POSITION` (2,347 heads carry one; a second
is 1.0 staff step):

**1 stemless head of 793 sits a second from a stemmed head at the same x.**

The interval histogram over all **223** stemless/stemmed same-x pairings:

| half steps | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13-24 |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| pairs | 3 | **2** | 3 | 4 | 4 | 5 | 8 | 3 | 5 | 5 | 10 | 19 | 26 | 126 |

The mass is at an octave and beyond — **138 of 223 pairs are 10 half steps or
wider**, which on one staff at one x is far likelier to be two voices than a
chord. The chordal intervals are nearly empty.

⚠️ **Caveat on 1d**: the position is our own reading, and the handoff §3a
measures 44% of ledger-country heads off-grid. The histogram bins by rounding,
so a head half a step off-grid lands in a neighbouring bin. That cannot
manufacture the shape — it would have to move ~130 pairs from bin 1 into bins
10+ — but a precise count of "exactly 2" should not be quoted.

---

## 2. HYPOTHESIS B IS SUPPORTED, AND ITS PREMISE IS FALSE

`line_detection._drop_paired_strokes` deletes **both** members of any pair of
verticals whose centres sit within **0.9 staff spaces** and which overlap
vertically by ≥ **0.6 of the shorter**. On these four pages:

| | |
|---|--:|
| stem candidates before the rule | 2,164 |
| after (shipped) | 1,920 |
| **strokes the rule deletes** | **244** (11.3%) |
| … landing on no detected notehead | 164 (67.2%) |
| … **carrying a notehead** | **80** |
| **heads that would stop abstaining `no_stem`** | **73 (9.2% of 793)** |
| already-decided heads gaining an AGREEING stem | 5 |
| already-decided heads gaining a CONTRADICTING stem | 2 |

So the rule is a real cause, and it is **9.2% of the population** — not the
explanation for the 793.

### 2a. ⚠️ THE MECHANISM IS NOT SHARPS AND FLATS. IT IS ADJACENT STEMS.

Every deleted stroke, by what its partner is (partner classes are tested in
this order, so a stroke with both kinds of partner is counted as the first):

| | all 244 | **the 80 that carry a notehead** |
|---|--:|--:|
| partner **CARRIES A NOTEHEAD** (two stems) | 81 (33.2%) | **62 (77.5%)** |
| partner is an **ACCIDENTAL** glyph | 57 (23.4%) | 14 (17.5%) |
| partner is unattributed ink | 106 (43.4%) | 4 (5.0%) |

Heads rescued, attributed: **51** two stems, **17** an accidental, **5**
unattributed — 73 distinct.

When an accidental did eat a stem it was a **natural 7, a flat 5, a sharp 2**.

The rule's own justification, `c2d640eb`:

> *"A stem is single. Two noteheads a second apart share one stem rather than
> standing side by side, and successive notes are set further apart than an
> accidental's own strokes, so the pair is the accidental's signature."*

The first sentence is right and §1 confirms it. **The second is false on this
plate**: successive notes in dense low-res orchestral writing are NOT set
further apart than an accidental's strokes, and the rule eats both of them
77.5% of the time it costs us a stem.

⚠️ **Its truth set could not have caught this.**
`benchmarks/omr-phase4-lines/hand-labeled-stems.json` is 15 cells over **La
Mer, Boléro, Mahler 5 and WTC** — **not one of them is this Litolff Beethoven 5
plate**, which is the document where the 793 was measured. The rule has never
been scored on it.

⚠️ **And the two truth sets are not in the same currency.** The labeler's
counting rule is *"one stem per note OR CHORD — three noteheads sharing one
stem count once"*. A stem the rule eats costs **1** against that truth and **N
heads** against the staged record. Do not difference them.

### 2b. ⚠️ THE TWO-VOICE DIRECTION SIGNATURE IS A MINORITY — this contradicts the refinement, and I am reporting it rather than accommodating it

Sean's refinement (3): since same-beat notes share one stem, two genuine stems
inside the pair window cannot be a chord — they must be **two voices** (stems
pointing opposite ways) or **successive notes set very close** — and the
direction is therefore a discriminator the shipped rule lacks.

The first half is confirmed and is exactly §1. **The discriminator is not.**
Every dropped pair, by where its two stems point (direction computed with the
adjudicator's own `_project` logic over the heads each stroke carries):

| | pairs | | median centre dx |
|---|--:|--:|--:|
| neither carries a head (accidental-shaped) | 94 | 63.1% | 0.56 sp |
| both carry a head, **SAME way (down)** | 23 | 15.4% | 0.64 sp |
| only ONE carries a head | 19 | 12.8% | 0.73 sp |
| both carry a head, **OPPOSITE ways (two voices)** | **10** | **6.7%** | 0.59 sp |
| both carry a head, SAME way (up) | 3 | 2.0% | 0.70 sp |

Of the **36** pairs where both strokes carry a notehead, only **10 (27.8%)**
point opposite ways. **26 point the same way** — the *successive notes* branch
the refinement also allows, and on this plate it is nearly three times the
two-voice one. So a rule keyed on *opposite directions* would protect 10 of 36
and still eat 26.

What the refinement gets exactly right is the other clause: **an accidental's
strokes carry no notehead and so point nowhere.** But that is the NOTEHEAD
test, not the direction test — the direction is derived from the notehead and
can only ever be weaker than it. Measured that way it is 10 against 36, and
§3 uses the notehead directly.

---

## 3. THE REPAIR — measured on an INDEPENDENT truth set, and not free

### 3a. Removing the rule is refused

Re-running the rule's own hand count with `drop_accidental_pairs=False`:

| | summed abs. error |
|---|--:|
| rule **ON** (shipped) | **15** |
| rule **OFF** | **53** |

OFF is worse on 7 of the 10 scoreable cells and better on **0**. Boléro and
Mahler cells go 5 → 16 and 3 → 14 against truths of 5 and 3.

⚠️ **My ON = 15 is NOT the 24 the commit records**, and the reason is in the
harness rather than in the detector: **4 of the 14 La Mer cells now report
`region no longer resolvable`**, exactly the re-segmentation instability that
file's own `_resolve_cells` docstring documents. **Reach is 10 of 14**, and the
two arms are compared to each other on the same 10, which is the comparison
that is valid.

### 3b. A geometry-only repair is NOT available

`detect_stems(cell)` takes nothing but the cell, so a repair living inside it
must separate the two populations on stroke geometry alone. The four
quantities it could read, over the 36 stem pairs and 94 accidental pairs:

| | stem pair (median, p10-p90) | accidental pair | best single cut | separates |
|---|--:|--:|--:|--:|
| height of the shorter | 2.32 [2.03-3.00] | 2.69 [2.29-3.25] | 2.28 | 0.785 |
| height of the taller | 4.89 [2.60-5.90] | 3.24 [2.71-4.69] | 4.69 | 0.808 |
| top offset | 0.33 [0.07-2.54] | 1.01 [0.12-2.73] | 0.44 | 0.785 |
| bottom offset | 1.84 [0.19-3.76] | 0.70 [0.11-1.33] | 1.44 | **0.823** |
| centre dx | 0.64 [0.51-0.77] | 0.56 [0.41-0.85] | 0.90 | 0.723 |

The majority baseline (*call everything an accidental pair*) is **0.723**. The
best feature buys **ten points** and there is **no empty interval anywhere**.
⚠️ A cut read off this table would be a constant fitted to this plate.

### 3c. What IS available: the notehead — and the staged gather already holds it

`gather_cv_lines` runs at `gather.py:3291`, **after** `gather_detections` at
`:3276`, and simply does not pass the detections on. So the proposal needs no
new reading:

> **Keep a stroke that meets a notehead; drop a pair only where NEITHER member
> does.**

⚠️⚠️ **Scoring that on the Litolff partition would be CIRCULAR** — the classes
in §2a are *defined* by notehead overlap, so the gate scores 80/80 there by
construction and the number would mean nothing. Scored instead on the rule's
own independent hand count (with the detector supplying noteheads,
`hollow-graft-shift09`, 89 noteheads over the 10 cells):

| arm | summed abs. error | worse than ON | better than ON |
|---|--:|--:|--:|
| ON (shipped) | **15** | — | — |
| OFF | 53 | 7 cells | 0 |
| **notehead-GATED** | **20** | **3 cells** | **0** |

**The gate recovers most of what removing the rule destroys (53 → 20) and is
still not free: +5, all of it over-counting, never under.** Boléro cell 18
goes 6 → 11 against a truth of 7. On Litolff it would protect 73 heads.

⚠️ **Three things a reader must weigh before this ships, and none is settled
here:**

1. **It couples `Q.STEM` to the detector.** Today the CV stem rung is an
   independent reader of the ink; gated, it is not, and the handoff §3b's
   *arbiter correlated with one party* applies in reverse. Where the detector
   misses a notehead the gate cannot protect that stroke — which fails toward
   the shipped behaviour, not toward a new one, but it also means the gate is
   weakest exactly on the pages where stems are most often missed.
2. **The legacy path would diverge.** `transcribe` reaches this through
   `detect_lines(cell)`, which passes no detections; gating only the staged
   path makes two readers of one page disagree about stems.
3. **+5 on the truth set is a real cost** and no crop was cut to decide whether
   those 5 are the labeler or the gate.

**Recommendation: do NOT simply turn the rule off.** The gate is the shape of
the fix; it is a DEFAULT and therefore Sean's call, and it wants a third
document before it is worth taking.

---

## 4. WHAT IS NOT ESTABLISHED

* **~90% of the 793 is still unexplained.** B is 9.2%, A is ~0. The handoff
  §4's *"not read"* stands for the remainder and nothing here narrows it.
* **No crop was cut. No note was checked against the print** — not one of the
  73 rescued heads, not one of the 5 cells the gate costs. Every accuracy
  statement here is agreement between two of our own readings.
* **n = 1 document, 1 publisher, 4 pages** for §1 and §2; **4 documents, 10
  cells** for §3, and those 10 are not this plate.
* **No export, no file, no OMR-NED.** This is a GATHER-stage measurement of
  what the adjudicator WOULD see. The proposed gate has never been run end to
  end, and `readjudicate`/`reexport_arm` are structurally blind to it.
* **The geometry table's labels are mine**, derived from notehead overlap, so
  §3b measures the separability of *my* partition and not of ground truth.
* **614 stems carry no detected notehead** and this work does not say why.
* **The direction reading in §2b is derived** from the same head boxes as the
  attachment, so it inherits their errors.

## 5. RETRACTED WHILE WORKING

* **The first mixed-column null was unsound and its verdict would have been
  right for the wrong reason.** Shuffling labels across the whole column
  population ignores that 211 stemless heads sit in bars with no stem ink at
  all; that bar-level clustering alone pushes the mixed count below chance.
  The within-cell null was added before any conclusion was drawn and it happens
  to agree — but *"0 of 400 draws"* against the wrong null is not evidence, and
  the first table was not reported as a finding on its own.
* **I framed hypothesis A as "a second apart" from the brief and that framing
  is too narrow.** Corrected to SAME BEAT / same x throughout (which is what
  the probes had always measured) — see §1d.
* The correlational accidental-proximity read in
  `probe_shared_stems.py` (stemless rate 0.464 within half a space of an
  accidental against a 0.359 baseline, but 0.286 at 0.5-0.9 and 0.188 at
  1.5-3.0, on 140/14/48 heads) was **not** promoted to a finding: the bands are
  non-monotone and small. §2a answers the same question by re-running the rule
  instead, which is the test rather than the correlate.

## 6. RUNNING IT

```bash
R=library/_shared-records/beethoven5-p1-p4-ink-identity.record.json   # machine-local, 146 MB
python3 benchmarks/omr-stem-pair-rule-2026-09/probe_shared_stems.py      "$R"  # §0 control, §1 geometry
python3 benchmarks/omr-stem-pair-rule-2026-09/probe_chord_columns.py     "$R"  # §1a-1d
python3 benchmarks/omr-stem-pair-rule-2026-09/probe_pair_rule.py         "$R"  # §0 structural, §2
python3 benchmarks/omr-stem-pair-rule-2026-09/probe_who_is_the_partner.py "$R" # §2a, §2b, §3b
python3 benchmarks/omr-stem-pair-rule-2026-09/probe_rule_cost.py               # §3a  (no record)
python3 benchmarks/omr-stem-pair-rule-2026-09/probe_proposed_gate.py           # §3c  (needs weights)
```

Every probe prints REACH first and exits **2** declaring itself DEAD at zero.
`out/*.json` is each one's own output, committed beside it.
