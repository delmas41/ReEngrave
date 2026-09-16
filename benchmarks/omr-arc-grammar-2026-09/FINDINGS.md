# S4 and S6 — Sean's two GEOMETRIC arc rules, built and measured

2026-09-15, no flag. `SEAN_ARC_RULES.md` (committed first, verbatim) records
six rules for telling a tie from a slur. **S2 and S5 already exist as
`OMR_ARC_RECLASS` and are REFUSED** — engraved roughly neutral, scan **+149
edits** — for a reason that is about the INPUT and not the grammar: *a scan's
resolved pitch at an arc's ends is downstream of exactly what scans get
wrong*, with 25 scan links sitting at ONE staff position and disagreeing about
pitch anyway.

**S4 and S6 read GEOMETRY — a stem's edge, the vertical stacking of two arcs —
and never a resolved pitch.** That is what makes them admissible where the
refused pair is not, and it is asserted on the source rather than promised:
`test_it_reads_no_pitch` greps the body of each helper, and a mutation arm
promoting either to a gate is in the battery as a positive control.

**Both are RECORDED as additional witnesses in `adjudicate_arc_kind` and
neither is a gate.** The detector's class still decides, unchanged, on every
arc.

---

## 1. REACH FIRST — and it falls in stages, which is the first result

`probe/reach.py`, over the committed staged record for Litolff Beethoven 5
mvt 1, pdf pages 1-4 (`library/_shared-records/beethoven5-p1-p4.record.json`,
the shared artefact of the cleanup count). **779 arc rows, 1,920 `Q.STEM`
rows, 2,347 noteheads.**

| stage | arcs | of 779 |
|---|--:|--:|
| every arc | 779 | 100% |
| ...with ANY flanked head | 535 | 68.7% |
| ...with TWO flanked heads — **what the existing grammar needs** | **345** | **44.3%** |
| ...with a flanked head that has a STEM | 420 | 53.9% |
| ...and the arc lies on the STEM's side of that head | 206 | 26.4% |
| ...and its endpoint lands ON the stem — **S4's own precondition** | **143** | **18.4%** |
| a y-disjoint sibling arc overlapping it in x — **S6's precondition** | **442** | **56.7%** |
| ...of which the pair's two readings DISAGREE — **what S6 addresses** | **181 pairs** | — |

⚠️ **THE 345 IS AN INDEPENDENT CORROBORATION OF THE UNVERIFIED WIP.** The
stopped branch `claude/arc-grammar-sean-rules` claims the grammar's
availability is "345 of 779" on this document. Re-derived here from the record
with no line of that branch trusted, it is 345. Its other claim — that a
stem-reachability repair takes it to 371 — is **not** reproduced here and was
not attempted: that is a change to which heads the FLANKING rule reaches, i.e.
a change to the existing grammar, not to S4 or S6, and it is out of this job's
scope.

### ⚠️⚠️ S4's availability gradient INVERTS the one this family already records

`ARC_KIND.md` measured the position grammar available on the STRONGER
readings: median detector confidence **0.563** where available against
**0.408** where not, and this project's standing rule is *wherever the first
reader is worst, the second is most often absent*. Split the same way:

| witness | available | median conf. available | median conf. UNavailable |
|---|--:|--:|--:|
| the existing grammar (two flanked heads) | 345 | 0.5306 | 0.4955 |
| any stemmed flanked head | 420 | 0.5391 | 0.4748 |
| **S4 — endpoint ON the stem** | **143** | **0.4196** | **0.5409** |
| S6 candidate stack | 442 | 0.5275 | 0.4936 |

**S4 is the exception and it runs the wrong way.** The grammar merely goes
quiet on bad ink; S4 goes quiet on GOOD ink and speaks preferentially about
the weakest readings — 23.9% of low-confidence arcs against 12.8% of
high-confidence ones. The mechanism is visible in the stage table: a confident
long slur is drawn CLEAR of the stem tips, so its endpoint does not land on a
stem at all, and the arcs that do land on one are the short, faint, close-in
ones.

⚠️ That is a *harder* problem than the recorded hazard, not the same one. An
arbiter that is absent where it is needed fails safe. An arbiter that is
present mainly where the first reader is worst is an arbiter whose own inputs
are drawn from the degraded population.

---

## 2. S4 — REFUTED on this document, and the direction is the only thing right

`probe/separate.py`. `t` is the fraction along the stem from the HEAD end
(0.0) to the FAR end (1.0) — **unit-free by construction, so there is nothing
here to tune**. S4 predicts a slur near or past 1.0.

Over the 143 arcs whose endpoint lands on a stem:

| the detector reads | n | min | p25 | median | p75 | max |
|---|--:|--:|--:|--:|--:|--:|
| `tie` | 83 | 0.057 | 0.341 | **0.535** | 0.692 | 1.044 |
| `slur` | 60 | 0.213 | 0.446 | **0.592** | 0.756 | 1.048 |

**The distributions overlap completely. Widest empty interval: −0.83 — i.e.
there is none.** This repo's own standard for a constant is a MEASURED empty
interval (`TIE_SAME_POSITION_MAX_SPACES` at 0.168 against 0.435); the slur pad
was refused because the same distribution is a smooth slope. This is a smooth
slope.

**The one-sided sweep (S4 says only *far ⇒ slur*, never *near ⇒ tie*):**

| `t` ≥ | fires | reads slur | reads tie | agreement | lift over base (0.420) |
|--:|--:|--:|--:|--:|--:|
| 0.25 | 133 | 57 | 76 | 0.429 | +0.009 |
| 0.40 | 106 | 50 | 56 | 0.472 | +0.052 |
| 0.50 | 83 | 38 | 45 | 0.458 | +0.038 |
| 0.60 | 62 | 29 | 33 | 0.468 | +0.048 |
| 0.75 | 30 | 16 | 14 | 0.533 | +0.114 |
| 0.90 | 15 | 7 | 8 | 0.467 | +0.047 |

⚠️ **NON-MONOTONIC.** A real rule's agreement rises with the evidence; this
peaks at n=30 and falls again. The largest lift in the table is +0.114 on
thirty arcs, and it is bracketed by +0.048 and +0.047.

**What IS consistent with S4** — and it is worth recording precisely because
it is the only positive thing here — is the DIRECTION, and it holds in both
confidence bands separately, so it is not a mix artefact:

| band | reading | n | median `t` |
|---|---|--:|--:|
| low conf. | tie | 69 | 0.506 |
| low conf. | slur | 24 | **0.592** |
| high conf. | tie | 14 | 0.583 |
| high conf. | slur | 36 | **0.622** |

The slur median is further from the head in both. The gap is **0.04–0.09 of
the stem's length** against interquartile ranges near 0.35. ⚠️ The class MIX
flips across the bands (69/24 against 14/36), which is why the pooled
comparison alone would have been unreadable.

The near half is the mirror and is equally weak: at `t` < 0.5, 38 ties against
22 slurs (36.7% slur, against a base of 42.0%).

**Verdict: S4 must not be promoted past RECORD on this evidence.** Its
direction agrees with Sean; its magnitude is a tenth of what a gate needs, it
has no empty interval anywhere, its sweep is non-monotonic, and it can speak
only about 18.4% of arcs — the least reliable 18.4%.

---

## 3. S6 — SUPPORTED, on a narrow and thin population, with a real control

`probe/separate.py` and `probe/s6_control.py`. A pair is a candidate stack
when the two arcs overlap in x by at least half the narrower one AND are
disjoint in y. **442 arcs have such a sibling; 428 distinct pairs; 181 of
those read DIFFERENT kinds, which is the only population S6 addresses.**

Over the 181: *the lower one is the tie* agrees with the detector on **114,
0.6298, p = 2.9e-4** (exact binomial against 0.5).

### The dose-response, which is the actual result

If *the lower of two stacked arcs is the tie* is a fact about engraving, it
must hold where the arcs are genuinely stacked and decay to chance as the pair
becomes two unrelated curves. A staff space is 100 canonical px by
construction (`CANONICAL_STAFF_SPAN_PX / 4`), so these bands are a
DESCRIPTION, not a threshold:

| separation | pairs | disagreeing | S6 right | agreement | p |
|---|--:|--:|--:|--:|--:|
| 0–1 space | 41 | 9 | 8 | **0.889** | 0.020 |
| 1–2 | 49 | 16 | 12 | **0.750** | 0.038 |
| 2–3 | 84 | 48 | 34 | **0.708** | 0.0028 |
| **0–3 pooled** | **174** | **73** | **54** | **0.740** | **3e-5** |
| 3–5 | 128 | 66 | 37 | 0.561 | 0.19 |
| 5–8 | 76 | 25 | 13 | 0.520 | — |
| 8+ | 50 | 17 | 10 | 0.588 | — |

Monotonic across the first four rows and at chance beyond three staff spaces.

### The control that could have failed, and did not

On a page whose arcs sit above the staff, the LOWER arc is also the one NEARER
the noteheads — so S6 might be nothing but the hugging rule `arc_owner`
already runs. An independent arm (*of the pair, the arc nearer the cell's
noteheads is the tie*) scores:

| population | S6 | HUGS | arms make the SAME prediction |
|---|--:|--:|--:|
| all 181 disagreeing pairs | **0.630** | 0.580 | 43.7% |
| 0–3 staff spaces (73) | **0.740** | 0.517 | 52.1% |
| 3–5 (66) | 0.561 | 0.672 | 37.9% |

**S6 is not the hugging rule restated.** The two arms coincide on fewer than
half of all pairs, and in the tight band where S6 is strongest the hugging
rule is at chance.

### The second control: `arc_owner`

| pairs | disagreeing | S6 agreement |
|---|--:|--:|
| both arcs owned by the SAME staff | 171 | **0.655** |
| owned by DIFFERENT staves | 10 | **0.200** |

A pair the record gives to two different staves is not a stack at all — it is
the measure-cell padding reaching into the neighbour, the signature
`arc_owner` already measured (all twelve of its moves went to an ADJACENT
staff). S6 *anti*-agrees there, which is what it should do if those are not
stacks. This arm could have come back at 0.65 and did not.

---

## 4. ⚠️⚠️ A CONTROL I WROTE WAS DEGENERATE, and it is recorded rather than replaced

The first control for S6 classified each arc ALONE as above or below its
CELL's median arc height, and reported **0.702 — better than S6's 0.630** in
every band. It is worthless, and the reason is worth more than the number:
for a pair drawn in one cell, "the median lies between them" is exactly when
that arm answers, and there it makes the SAME prediction as S6 **by
construction**. It was S6's own rate on the easier subset, dressed as a second
opinion.

**An arm that IS the arm under test, restricted, cannot control it.** This is
this repo's recorded *control that was never testing what its name says*,
arriving against its author — and the tell was that it beat the rule it was
controlling on every single row, which is not what a weaker independent
predictor does.

---

## 5. What is NOT established

- **ACCURACY.** Neither the detector's class nor a geometric rule is truth.
  Every number above is an AGREEMENT RATE between two readings of the same
  ink, and **no arc was checked against the print.** S6 agreeing with the
  detector 74% of the time in the tight band is consistent with S6 being right
  and the detector being right together; it is also consistent with both
  sharing a bias.
- **n = 1 document, 1 publisher, 4 pages of ~16.** Litolff `984073` is the
  *low-res bitonal* scan this project calls the pessimistic end of its corpus.
  **Breitkopf Brahms 1 is the second publisher this thread repeatedly needs
  and no staged record for it exists on this machine** — the only committed
  shared record is the Beethoven one. A print whose slurs are drawn over
  noteheads rather than over stems would give S4 a different distribution
  entirely, and a print that stacks arcs more often would move S6's n.
- **The informative end of S6 is the THIN end: 9 and 16 pairs.** The pooled
  0–3 figure (73 pairs, p = 3e-5) is the one to quote; the 0.889 is not.
- **The ENGRAVED family is untouched by construction** and was not measured.
- **S6's candidate population is contaminated and the contamination was not
  removed, deliberately.** `_place_arcs` has no dedupe — 48 pairs in one cell
  at IoU ≥ 0.7, 19 of them detected on two different staves — so some
  "siblings" are one curve counted twice. They are RECORDED with their own
  IoU and y-gap rather than filtered, because a rule that dropped them would
  hide the population instead of letting it be measured. That defect is in a
  lane this job does not own and was not touched.
- **S1 and S3 are not implemented and were not attempted** — both say
  *ambiguous*, so neither has anything to record.

⚠️⚠️ **AND THE DUPLICATE POPULATION HERE IS NOT THE ONE THE DEDUPE FINDING
MEASURED, which is worth stating because the two numbers look like they should
match and do not.** `benchmarks/omr-arc-recovery-2026-09` records *48 pairs of
arcs placed in ONE cell at IoU ≥ 0.7*; the same test over the same record here
returns **29 of 593**. Both are right: that figure is taken over `_place_arcs`'
OUTPUT, after `arc_owner` has relocated each arc onto the cell its owner names,
while S6 reads the cell the DETECTOR found the arc in. **19 of the 48 were
detected on two different staves** — which is the whole of the difference, to
within the two runs' own populations. So S6's candidates are the
pre-relocation pairs, and a session that expected 48 here would have gone
looking for a bug that is not there.

---

## 6. What shipped

`tools/omr/staged/adjudicators/ownership.py` only, plus its tests and this
directory. **No exporter was touched, on either path.**

- `_s4_stem_view` → `detail["grammar"]["s4_stem_position"]`: per endpoint
  `t`, `same_side`, `dx_widths` (in NOTEHEAD WIDTHS — the unit the arc work
  already uses), plus `t_median`, `arc_above_heads` and
  `any_endpoint_on_a_stem`. **No threshold anywhere**: raw measurements, so a
  later session can price any cut from the record alone.
- `_s6_stack_view` → `detail["grammar"]["s6_stacked_with"]`: per sibling
  `y_gap`, `x_overlap_frac`, `iou`, `this_is_upper`. Again no threshold — a
  DUPLICATE is recorded with a negative `y_gap` and a high `iou` rather than
  dropped, because a rule that dropped it would hide the population instead of
  letting it be measured.
- `Q.STEM` added to `arc_kind`'s `wants` and `composed_from`. ⚠️ It was
  already gathered — **1,920 rows on this record** — and read by nothing on
  this path: the FOURTH time `Q.STEM` has been found gathered-and-unread.
  `inventory --check` does not list the new declaration among its inert ones,
  which is the check that it is genuinely read.
- `_boxes_overlap` is **IMPORTED** from `rhythm`, never restated — the
  attachment rule is measured (819 heads take exactly one stem; the nearest
  miss is 94 px) and two spellings of a measured number is how they drift.

### Controls

**A/B, one gather adjudicated twice** (`arc_grammar_arm.py`, 18m43s over the
132 MB record):

```
CONTROL: 779 of 779 arc_kind VALUES reproduced exactly, 0 differ, +0 extra
WITNESSES: s4 recorded on 420 arcs (was 0), of which endpoint-on-a-stem 137;
           s6 recorded on 502 arcs (was 0)
```

⚠️ **The `(was 0)` is the positive control**, not decoration: without it, *779
of 779 reproduced* is indistinguishable from an arm that never ran the new
code — this repo's *control that was never testing what its name says*. The
arm exits non-zero if the base record already carries the witnesses.

⚠️ `readjudicate`'s blind spot is NOT engaged. It is structurally blind to a
GATHER change; **this change gathers nothing**, it only reads rows already in
the log, so an ADJUDICATE-only arm is the right instrument. It would **not**
be the right instrument for the WIP branch's flanking change, which is about
which heads the rule reaches.

⚠️ **The adjudicator's two counts differ from the probe's and both reconcile
to the unit**, checked rather than waved past: `137` against the probe's `143`
is the probe's declared ±0.05 tolerance band on `t` (the shipped
`any_endpoint_on_a_stem` uses a strict `[0, 1]`); `502` against `442` is
*every arc with an x-overlapping sibling* versus *every arc with a
y-DISJOINT one*, and 502 is exactly the probe's own `s6_any_x_overlap`.

**Mutation battery: 15 arms, ALL RED** (`mutants.py`), including **two
positive controls in the same class** — S4 promoted to a gate, S6 promoted to
a gate — because a suite whose every test says *recorded and changed nothing*
can pass by recording nothing and changing nothing. Every arm asserts its
anchor occurs EXACTLY once and returns `BAD ANCHOR` rather than passing
(`Ruling.abstain(` occurs twice in this file, which is how the fermata battery
silently mutated a different function).

`inventory --check`, `gather_coverage` and `health --check` all exit 0.

**Full suite: `1 failed, 3855 passed, 19 skipped` in 583s.** ⚠️⚠️ The single
failure is **PRE-EXISTING AND IS THE WORKTREE SURYA TRAP THIS PROJECT ALREADY
DOCUMENTS**, not a regression — and that was PROVED rather than assumed.
`test_direction_text.py::TestReaderSelection::test_the_env_var_restricts_the_rungs`
fails **identically on a clean `origin/main` checkout with none of this work
present**, because `default_readers()` returns `[]`: `.venv-surya` is
repo-root-relative and gitignored, so a worktree silently self-disables it.
Symlinking the venv into that same clean checkout takes the class to
`2 passed`. **The mechanism is named because "1 failed" is exactly the shape
that gets attributed to the change under test** — CLAUDE.md's own
`inspect.getsource` hazard arriving from a different direction. ⚠️ This suite
was also killed and restarted once after `tools/` was edited mid-run, which is
that hazard's recorded recipe; the figure above is the clean re-run.

`tools/omr/tests/` filtered to `staged or arc or ownership`: **881 passed**;
the three source-level-assertion files (`test_staged_export`,
`test_staged_voices`, `test_staged_stage_contract`): **190 passed**.

---

## 7. RECOMMENDATION — keep both at RECORD

**Neither is ready to be a gate, and they are not ready for the same reason.**

- **S4: do not promote, and do not re-try it on this document.** It is refuted
  here — no separation, no empty interval, a non-monotonic sweep, and an
  availability gradient that runs the WRONG WAY. What would change the
  picture is a second publisher whose slurs are drawn over stems rather than
  over noteheads; nothing else will.
- **S6: the only candidate, and the price is stated rather than implied.**
  Restricted to pairs under 3 staff spaces apart, owned by the same staff, and
  disagreeing about their kind, it is right on 54 of 73 (p = 3e-5) against a
  genuinely independent control at 0.517. **That is 19 arcs it would get
  wrong out of the 73 it touches, on one publisher, against a detector that
  is not truth** — and roughly half of its flips would be in the tie→slur
  direction, the one `OMR_ARC_RECLASS` measured at +149 scan edits. A rule
  measured on seventy-three pairs of one low-res bitonal scan is not a
  default anyone should choose.

**The cheapest thing that would settle S6 is not more arcs — it is seventy
crops.** The population is small enough to adjudicate by eye: render the 73
pairs under 3 staff spaces and ask whether the lower one is a tie. That is a
print question, this session did not have the print, and it is the one
measurement that would turn a 0.740 AGREEMENT RATE into an ACCURACY.

---

## 8. How to reproduce

```bash
R=library/_shared-records/beethoven5-p1-p4.record.json
python3 benchmarks/omr-arc-grammar-2026-09/probe/reach.py      $R --out /tmp/reach.json
python3 benchmarks/omr-arc-grammar-2026-09/probe/separate.py   /tmp/reach.json
python3 benchmarks/omr-arc-grammar-2026-09/probe/head_y.py     $R /tmp/heads.json
python3 benchmarks/omr-arc-grammar-2026-09/probe/s6_control.py /tmp/reach.json --heads /tmp/heads.json
python3 benchmarks/omr-arc-grammar-2026-09/arc_grammar_arm.py  $R --control   # ~19 min
python3 benchmarks/omr-arc-grammar-2026-09/mutants.py
```

`out/` holds the three probe outputs as committed artefacts, so every number
above re-reads from a checkout without the 132 MB record. ⚠️ `reach.py` and
`s6_control.py` exit **non-zero** when their rule can speak about nothing —
a dead instrument and a clean negative are the same number.

---
---

# 2026-09-15, SECOND MEASUREMENT — the rules BROADENED

Sean, on reading the narrow result: **do not give up on the arc rules —
broaden them.** He is the author of S1-S6 and they are his statement about how
the music is ENGRAVED, so *a narrow operationalisation failing is evidence
about the operationalisation, not about the convention.*

⚠️ **NOTHING ABOVE IS REWRITTEN.** The narrow numbers stand; this is a second
measurement on the same record, and where the two disagree the widened one is
named as the one that governs.

**The central objection was right and it was mine to have missed**: my own
funnel read *420 arcs with a stemmed head → 206 on the stem's side → 143 whose
endpoint lands ON the stem*, and I used **"on the stem's side" as a FILTER on
the way to the narrow test instead of scoring it as the RULE.** It is the
cleaner reading of Sean's sentence — a tie is drawn on the side of the head
AWAY from its stem, a slur over stemmed notes runs stem-tip to stem-tip — and
it had never been scored.

## 9. S4 at full width — and it is REFUTED THERE, which is the stronger result

`probe/widen.py`. Three widenings, all of which are one quantity:

* **`t_axis`** projects the arc's near edge onto the axis from the **NOTEHEAD
  CENTRE (0.0) to the STEM TIP (1.0)**, with **NO contact requirement** — a
  scan breaks ink constantly and demanding pixel contact is our limitation.
* **SIDE is `sign(t_axis)`**, so widening 1 and widening 2 are the same
  measurement rather than two rules that could drift.
* **The abstain population is COUNTED**: 359 arcs have no stemmed flanked
  head and the rule says nothing about them.

**REACH: 143 → 420 of 779 (18.4% → 53.9%), abstaining on 359.**

⚠️ **AND IT IS SCORED ONE-SIDED WITH AN ABSTENTION, which is Sean's own
construction** — near the head is S3, which he states is AMBIGUOUS. The narrow
pass's "only the direction survives" was a two-sided reading of a one-sided
rule, and that was a real error in how it was scored.

### Widening 1: SIDE alone — FLAT, and flat within band

| | arcs | reads slur | share | base | lift |
|---|--:|--:|--:|--:|--:|
| arc on the STEM's side | 225 | 111 | 0.4933 | 0.5571 | **−0.064** |
| arc on the HEAD's side | 195 | (72 tie) | 0.3692 tie | 0.4429 tie | **−0.074** |

Both strata fall *below* their base rate; p = 0.977 one-sided.

⚠️⚠️ **AND THE POOLED FIGURE IS CONFOUNDED, WHICH MATTERS MORE THAN THE
FIGURE.** The detector's own class mix differs enormously between confidence
bands on this document — base slur rate **0.2513 low** against **0.8222
high** — so any pooled lift here can be pure Simpson. Within band, SIDE's lift
is **−0.0013** (low, n=195) and **−0.0301** (high, n=225). *Sean's cleanest
binary reading of his own sentence carries no signal on this document, pooled
or split.*

### Widening 2: the one-sided distance sweep at 420, WITHIN band

| `t_axis` ≥ | low conf. fires | lift | p | high conf. fires | lift | p |
|--:|--:|--:|--:|--:|--:|--:|
| 0.0 | 124 | −0.001 | 0.55 | 101 | −0.030 | 0.82 |
| 0.5 | 71 | +0.030 | 0.32 | 73 | −0.028 | 0.78 |
| 1.0 | 31 | +0.007 | 0.53 | 52 | +0.005 | 0.55 |
| 1.5 | 16 | +0.061 | 0.37 | 24 | +0.053 | 0.36 |
| 2.0 | 7 | +0.034 | 0.56 | **13** | **+0.178** | **0.079** |

**Not one cell reaches significance.** The single non-flat cell is 13 arcs of
13 at `t_axis ≥ 2.0` — an arc whose near edge sits *more than twice the
head-to-tip distance beyond the head*, which is barely a stem-connected arc at
all and is closer to "drawn high above the notes" than to Sean's rule.

⚠️ **The pooled sweep looks better than the within-band one and that is the
Simpson effect, named**: pooled it reads +0.193 at `t_axis ≥ 2.0` (15 of 20),
because far-`t_axis` arcs are disproportionately high-confidence arcs and
high-confidence arcs are 82% slurs on this page. The within-band table is the
one that cannot be fooled that way.

### Widening 3: conditioned on the other witnesses — S4 adds nothing

Difference in slur share between the arcs S4 FIRES on and those it is SILENT
on, inside each stratum (`probe/combine.py`):

| `t_axis` ≥ | S6 says slur | S6 says tie | S2/S5 says slur | S2/S5 says tie |
|--:|--:|--:|--:|--:|
| 0.0 | −0.125 | −0.191 | −0.127 | −0.239 |
| 1.0 | −0.105 | +0.176 | +0.093 | +0.116 |
| 2.0 | −0.610 (n=1) | −0.418 (n=2) | +0.145 (n=9) | +0.223 (n=4) |

Negative in all four strata at `t_axis ≥ 0`, sign-unstable above, and the
positive cells are n ≤ 9.

### ⚠️⚠️ VERDICT: S4 is REFUTED, and it is the WIDENED test that fails

This is the distinction Sean asked for. The narrow refutation was weak — 143
arcs, a non-monotonic tail at n=30, a two-sided scoring of a one-sided rule.
**The widened one is not**: 420 arcs, contact dropped, scored one-sided with an
explicit abstention, split by confidence so the class mix cannot confound it,
and conditioned on both other witnesses. **SIDE is flat to within ±0.03 in both
bands and the distance sweep never clears p = 0.079 at n = 13.**

### ⚠️ The refutation was checked for being the PROBE's fault, and is not

SIDE is `sign(t_axis)`, and the side is decided from the MEDIAN y-centre of the
flanked heads. **An arc spanning heads at very different heights could get the
wrong side for one endpoint**, which would flatten the SIDE rule for a reason
having nothing to do with Sean's convention. Measured
(`probe/side_robustness.py`) against a per-endpoint determination — above or
below THAT endpoint's own outer head:

| | |
|---|--:|
| stemmed outer endpoints | 763 |
| the two determinations AGREE | 742 |
| they DISAGREE | **21 (2.75%)** |

**21 endpoints of 763 cannot turn a −0.001 / −0.030 within-band lift into a
signal.** The refutation stands as the rule's, not the instrument's. ⚠️ A
refutation produced by a probe defect is worth nothing, and this project's
record is that the expensive mistakes are instruments confidently answering a
different question — so this was measured before the refutation was reported,
not after it was doubted.

⚠️⚠️ **THE SAME PROBE FOUND A LIMITATION BOTH S4 AND S2/S5 INHERIT AND NEITHER
CAN SEE.** The vertical spread between an arc's two outer flanked heads has a
median of **121 canonical px (1.2 staff spaces)** — fine — but a **p90 of 728
(7.3 spaces)** and a **max of 1323 (13 spaces)**. A measure cell is the staff
plus four staff spaces of air, so a pair of "flanked heads" thirteen spaces
apart is the padding reaching into a neighbouring staff, and the arc is being
compared against a head that is not its own. **That is a defect in the FLANKING
rule, upstream of both witnesses**, and it is not repaired here: it is
`adjudicate_arc_kind`'s existing rule, which this job may record against but
not silently change. It is a candidate cause for S2/S5 scoring below its own
majority baseline (§11).

⚠️ What is NOT refuted is Sean's CONVENTION. What is refuted is that **our
boxes can see it on this document**: `Q.ARC_BOX` is a bounding box, so which
edge carries the arc's endpoints is inferred from the flanked heads rather
than measured, and on a low-res bitonal scan the stem the arc is compared
against is itself a CV reading. A reader that traced the arc's actual
endpoints would be testing something this cannot.

## 10. S6 at full width — it SURVIVES every relaxation, and buys almost no reach

`probe/widen_s6.py`. ⚠️ **The absolute-position widening is deliberately NOT
re-tried: §3 already refuted it** (*"the arc nearer the noteheads is the tie"*
scores 0.517). S6's power is in the PAIRWISE comparison, so every relaxation
keeps the pair and loosens only what qualifies as one.

| relaxation | candidate pairs | disagreeing | agreement | p | inside 3 spaces |
|---|--:|--:|--:|--:|---|
| NARROW (x-overlap ≥ 0.5, y-disjoint) | 428 | 181 | 0.6298 | 3e-4 | 73 @ **0.7397** |
| A: x GAP up to 0.25 widths | 446 | 189 | 0.6243 | 4e-4 | 76 @ 0.7368 |
| A: x gap up to 0.5 | 450 | 190 | 0.6263 | 3e-4 | 76 @ 0.7368 |
| A: x gap up to 1.0 | 461 | 193 | 0.6218 | 4e-4 | 77 @ **0.7403** |
| B: y OVERLAP up to 0.25 of the shallower | 448 | 186 | 0.6344 | 1.5e-4 | 73 @ 0.7397 |
| B: y overlap up to 0.5 | 457 | 187 | 0.6364 | 1.2e-4 | 73 @ 0.7397 |
| A+B | 463 | 194 | 0.6340 | 1.2e-4 | 76 @ 0.7368 |
| **C: same `arc_owner` only** | 409 | 172 | **0.6512** | 4e-5 | 71 @ **0.7465** |
| **A+B+C** | 434 | 182 | **0.6538** | 2e-5 | 73 @ 0.7397 |

**Dose-response on the LOOSEST relaxation** (A+B), which is the test that the
widening is not dilution:

| separation | pairs | disagreeing | S6 right | agreement | p |
|---|--:|--:|--:|--:|--:|
| y-OVERLAPPING (not a stack) | 13 | 4 | 4 | 1.000 | 0.063 |
| 0–1 space | 45 | 11 | 10 | **0.909** | **0.006** |
| 1–2 | 50 | 16 | 12 | 0.750 | 0.038 |
| 2–3 | 89 | 50 | 35 | 0.700 | 0.003 |
| **0–3 pooled** | **184** | **77** | **57** | **0.7403** | **1e-5** |
| 3–5 | 135 | 69 | 38 | 0.551 | 0.24 |
| 5+ | 131 | 44 | 24 | 0.545 | 0.33 |

⚠️⚠️ **THE FOURTH RELAXATION — PAIRING BY VOICE — WAS SCOPED AND IS NOT
AVAILABLE, and the reason is a number rather than a story: AN ARC HAS NO VOICE
ON THE RECORD.** `Q.VOICES` partitions a cell's EVENTS, so an arc's voice would
have to be derived from the noteheads it binds — and only **345 of 779** arcs
bind two. A voice-keyed pairing would therefore REACH LESS than the geometry it
was meant to widen, which is the opposite of a relaxation. Recorded at the site
in `probe/widen.py` so it is not re-scoped.

**The honest reading: the widenings buy 428 → 463 candidate pairs (+8%), not a
doubling, and agreement does not move.** So this is NOT "agreement holds while
the population doubles"; it is **robustness** — the result does not depend on
how a stack is defined, which is a different and smaller claim than the one
the widening was hoping for. ⚠️ **The one relaxation that helps is C**: pairing
only arcs the record gives to the same staff takes agreement to 0.6512 and the
tight band to 0.7465, corroborating §3's `arc_owner` control from the other
direction.

## 11. ⚠️⚠️ COMBINED — the joint result is the largest finding of either pass

`probe/combine.py`. Three witnesses over one arc.

**Each alone, over its own population:**

| witness | speaks about | agreement | base rate (majority class) | lift |
|---|--:|--:|--:|--:|
| **S2/S5** (the existing grammar) | 345 | **0.5043** | 0.5275 | **−0.023** |
| **S6** (within 3 spaces) | 202 | **0.6139** | 0.4158 | **+0.198** |
| S4 (one-sided) | 420 | — | — | see §9 |

⚠️⚠️ **S2/S5 IS WORSE THAN ALWAYS SAYING "SLUR"** on its own 345 arcs. That
extends this project's recorded *42 agree / 39 disagree, a coin flip* from 81
arcs to 345 and makes it sharper: the position grammar is not merely
uninformative, it is **below the majority-class baseline**.

⚠️⚠️ **AND THAT IS A USEFUL FACT ABOUT A MECHANISM THIS REPO HAS ALREADY
REFUSED, SO BOTH HALVES HAVE TO BE STATED.** `OMR_ARC_RECLASS` is the shipped
form of S2/S5 and it is default-OFF, refused on EDITS — engraved roughly
neutral, scan **+149**. **The refusal stands, and the reason for it is now
better understood than it was**: the flag was refused for what it COST, and
this measures what it is WORTH, which nobody had done. Alone, on this
document, it is worth slightly less than nothing. ⚠️ But the second half is
what would be lost by stopping there: **the same witness carries real
information in CONCURRENCE** (0.750, p = 0.0104 against the permutation null).
A rule can be below its own baseline marginally and informative jointly, and
those are not in tension — they are the reason this project's architecture is
ADDITIVE EVIDENCE rather than a stack of gates. ⚠️ **Nothing here argues for
turning `OMR_ARC_RECLASS` on.** It argues that the right consumer of S2/S5 is
a decision that already has a second witness in hand.

**Together, on the 83 arcs where both speak:**

| | n | agreement |
|---|--:|--:|
| they CONCUR | 40 (48.2%) | **0.750** |
| they CONFLICT — S2/S5 right | 43 | 0.465 |
| they CONFLICT — S6 right | 43 | 0.535 |
| S2/S5 alone on those same 83 | 83 | 0.602 |
| S6 alone on those same 83 | 83 | 0.639 |

**0.750 where they concur, against 0.602 and 0.639 for either alone on the
identical population.** That is the SUPER-ADDITIVITY the duration work
predicted, in a family it was not measured in.

### ⚠️⚠️ THE CONTROL THAT MAKES IT A RESULT

**Conditioning on two noisy predictors AGREEING raises measured accuracy even
when one of them is pure noise** — it is a selection effect, and this repo's
own rule is that *a plausible aggregate is not evidence that its parts are
real*. So S2/S5's labels were PERMUTED 20,000 times within the joint
population (seed 20260915), keeping its marginal mix exactly, and the
concur-subset agreement recomputed:

| | |
|---|--:|
| observed concur agreement | **0.750** (n = 40) |
| permutation null, median | 0.625 |
| permutation null, p95 | 0.711 |
| **p-value** | **0.0104** |

**It clears the null.** And the finding is stranger than it looks: **S2/S5 is
MARGINALLY UNINFORMATIVE and JOINTLY INFORMATIVE.** A witness that is worse
than the majority class on its own carries real information conditional on
S6 — which is an argument for the ADDITIVE-evidence architecture this project
already has, arriving from a direction nobody was looking in.

⚠️ n = 40 concurring arcs. This is the thinnest number in either pass and the
one most likely to move on a second document.

## 12. What the second pass changes, and what it does not

| | narrow pass | widened pass |
|---|---|---|
| **S4** | refuted at 143 arcs, weakly | **REFUTED at 420**, one-sided, within band, conditioned — the strong refutation |
| **S4 SIDE** | never scored (used as a filter) | **flat: −0.001 / −0.030 within band** |
| **S6** | 0.740 at 73 pairs | unchanged, and **robust to every relaxation**; reach +8%, not a doubling |
| **S2/S5** | not scored here | **below the majority baseline over 345** |
| **joint** | not measured | **0.750, p = 0.010 against a permutation null** |

**What shipped in the second pass:** `t_axis` recorded beside `t` on every
endpoint — the widened quantity, defined for 420 arcs against 137, with no
contact requirement and no threshold. **Still RECORD, still not a gate.**

### Controls, second pass

- **A/B unchanged in kind:** `arc_kind` VALUES must still reproduce exactly.
- **Mutation battery: 18 arms, ALL RED** — the original 15 plus three for
  `t_axis` (measured from the stem's head end rather than the head centre; an
  alias of `t`, i.e. the widening silently undone; running to the head end
  rather than the tip). The two gate-promotion positive controls are still in.
- ⚠️⚠️ **A DEFECT IN MY OWN COMBINED PROBE — and it is the more instructive of
  this session's two self-corrections.** The first draft scored S4 jointly as
  *"agreement of S4 on the subset where S6 also says slur"*. **S4 is
  ONE-SIDED: it only ever says slur.** So that "agreement" is identically the
  subset's own SLUR SHARE, and comparing it against the subset's base rate
  compares a number with itself. **Every cell read `agreement == base_rate` to
  four decimals.** A one-sided rule can only be scored by comparing the
  population it FIRES on against the population it does NOT, which is what
  §9's third table now does.

  ⚠️⚠️ **THE TELL IS WORTH MORE THAN THE FIX, AND IT IS A NEW MEMBER OF A
  FAMILY THIS PROJECT ALREADY KEEPS.** Nothing about the numbers looked
  *wrong* — they were plausible, in range, and stable across the sweep. What
  gave it away was that **one column was EXACTLY another column, to four
  decimal places, in every row.** That is *a control that computes the wrong
  thing* — the family holding `symbol_ledger.coverage_check` (computed and
  read by nothing), `EMPTY CELLS: none` (a check that could not fail), and the
  fermata battery's duplicated anchor — arriving in a new disguise: not a
  check that cannot fail, but a check **silently comparing a quantity with
  itself**. The diagnostic that catches this class is not *"is this number
  believable"*; it is ***"is this number suspiciously EXACTLY some other
  number on the page"***.

## 13. What is STILL not established

Everything in §5 stands. Added by this pass:

- **n = 40** for the joint result, **13** for S4's only non-flat cell, and
  still **1 document / 1 publisher / 4 pages** for all of it.
- **The joint result is an agreement rate, not an accuracy**: three readings of
  one piece of ink concurring is not the same as being right, and the
  permutation null tests only that the concurrence is informative, not that it
  is correct.
- **S4's refutation is about OUR BOXES, not about Sean's convention.**
  `Q.ARC_BOX` is a bounding box, so which edge carries the endpoints is
  INFERRED from the flanked heads rather than measured, and the stem it is
  compared against is itself a CV reading on a low-res bitonal scan. A reader
  that traced an arc's actual endpoints would be testing something this
  cannot, and that is the experiment that would revive S4.

## 14. How to reproduce the second pass

```bash
R=library/_shared-records/beethoven5-p1-p4.record.json
P=benchmarks/omr-arc-grammar-2026-09/probe
python3 $P/widen.py           $R --out /tmp/widen.json   # S4 at full width
python3 $P/widen_s6.py        /tmp/widen.json            # S6 relaxations
python3 $P/combine.py         /tmp/widen.json            # joint + permutation null
python3 $P/side_robustness.py $R                         # is the refutation ours?
python3 benchmarks/omr-arc-grammar-2026-09/mutants.py    # 18 arms
```

`out/` carries all four outputs, so every figure in §9-§13 re-reads from a
checkout without the 132 MB record. `widen.py`, `widen_s6.py` and `combine.py`
were each re-run after the lint cleanup and are **byte-identical**;
`combine.py`'s permutation null is seeded (20260915) and therefore
reproducible.

## 15. ⚠️ THE RANKED NEXT WORK, changed by this pass

1. **S6 + S2/S5 jointly is the live result, and it is a PRINT question now.**
   40 concurring arcs at 0.750 (p = 0.010) is small enough to adjudicate by
   eye. Render those 40, plus the 43 where the two witnesses CONFLICT, and ask
   which witness is right. That turns two agreement rates into an accuracy and
   is the single cheapest experiment in this directory.
2. **The FLANKING rule, not the arc rules.** Outer flanked heads up to 13
   staff spaces apart (§9) means both witnesses are sometimes comparing an arc
   against a neighbouring staff's notehead. Fixing that is upstream of
   everything measured here and would move S2/S5's sub-baseline score.
3. **A second publisher.** Breitkopf Brahms 1, which this thread has now
   needed four times and for which no staged record exists on this machine.
4. **S4 only if an arc's ENDPOINTS are traced rather than boxed.** Nothing
   short of that will revive it, and it should not be re-tried on box geometry
   on any document.
