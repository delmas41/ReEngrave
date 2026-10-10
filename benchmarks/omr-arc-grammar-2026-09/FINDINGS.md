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

- **A/B, RUN ON THE COMMITTED TREE** (`3a2e51b8`, working tree clean — a
  structural diff of the value path does not cover code that is not yet
  committed, so the empirical control was run against `HEAD` rather than a
  working copy):

  ```
  CONTROL: 779 of 779 arc_kind VALUES reproduced exactly, 0 differ, +0 extra
  WITNESSES: s4 recorded on 420 arcs (was 0), of which endpoint-on-a-stem 137;
             s6 recorded on 502 arcs (was 0)
  grammar 'says': [(None, 434), ('slur', 265), ('tie', 80)]
  ```

  ⚠️ **The witness counts are IDENTICAL to the first pass's, and that is the
  correct result rather than a stale one**: `t_axis` adds a FIELD to each
  endpoint, not a row, so the populations cannot move — 420 and 502 either
  side of the widening is what a field-only change must produce. The
  `grammar 'says'` distribution is unchanged too, so the existing position
  grammar's own output is untouched.
- **Full suite on the committed tree: `1 failed, 3861 passed, 19 skipped`
  (581s).** ⚠️ The single failure is the same PRE-EXISTING worktree Surya trap
  proved in §6 against a clean `origin/main` archive with none of this work
  present — not a regression, and named here so a reader does not attribute it
  to the widening.
- Mutation battery and the three derived checks were re-run on the committed
  tree: **18 arms all RED**, `inventory --check` / `health --check` /
  `gather_coverage` all exit 0.
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


## 16. ROADMAP 2.75 -- Sean's two-note rule DECIDES `Q.ARC_KIND` (2026-10-09), STAGED, GATHER+ADJUDICATE only

Branch `lane-2.75-tie-slur`. Path: **STAGED** (`adjudicators/ownership.py`
`adjudicate_arc_kind`; the legacy `OMR_ARC_RECLASS` is untouched and still off).

**Sean, 2026-10-09:** *"If an arc only goes from one note to the next and they
are both on the same pitch it can only be a tie - never a slur. A slur requires
different notes if only 2 are involved."* and *"if there are 2 arcs - one over
the other - then the tie will always be the bottom and the slur on top."*

### 16.1 What changed (and what did not)

* `adjudicate_arc_kind` no longer lets the detector's class decide where its
  arc's two END HEADS were READ. The class still decides everywhere else, and
  `detail["grammar"]["tie_slur_rule"]` records, for EVERY arc, what the rule
  saw (`two_note`: whether and why it was or was not evaluated; `stack`;
  `rule`; `conflict`; `detector_class`). A decided arc's `reason` stays `tie` /
  `slur`; the rule that decided it is `tie_slur_rule.rule`.
* The end heads are found by the tie pairing's own search -- moved, not
  rewritten, out of `adjudicate_tie_pair` into `_flank_search` -- so the kind
  and the pairing can never read different heads of one arc. A single head at
  each end, none between; an arc cut by ONE barline is judged by the nearest
  head across it (both halves of a tie get one answer).
* A head's step is `Q.NOTEHEAD_POSITION` where a far head's LEDGERS were read
  (an abstained far head is UNREAD: the geometry is never substituted, rule 8),
  else the geometry step; the step must AGREE with the heads' vertical offset
  (`TIE_SAME_POSITION_MAX_SPACES`, 0.25): two instruments, one question. A
  disagreement is `conflict` and the class stands.
* "Same sounding accidental" is PROVED only as no printed accidental on the
  stop head (and, across a barline, on either end); a printed accidental keeps
  the class; an UNCLAIMED accidental glyph beside a slur-classed same-step arc
  ABSTAINS (`same_pitch_accidental_unread`).
* Two `adjudicate.ORDER` moves: `accidental_owner` and `notehead_position` now
  stand just before `arc_kind` (ADJUDICATE reads a frozen log; both read GATHER
  rows and refusals only, so nothing else's inputs moved).
* Not judged (the class stands, `why` recorded): a chord or second voice at an
  end, an arc cut at BOTH barlines, an arc narrower than 1.5 head widths or
  ending more than 1.5 widths from its head (staff-line slivers), a box refused
  as not-an-arc (2.60 -- that refusal is untouched), any end whose position was
  not read.
* The stack rule is built (nearer the heads = tie, farther = slur; positions
  outrank it; an upper slur over two same-pitch notes abstains) and fires **0
  times** on both pages -- see 16.4.

### 16.2 Population (small re-gathers on `origin/main` 0a06e5c2: Brahms pdf 0-1, Litolff pdf 0-3; `out/2.75-*.rows.json`)

Control first: a replay of ADJUDICATE on the OLD code reproduces the records'
own `arc_kind` verdicts **1,034 of 1,034 (Brahms) and 512 of 512 (Litolff)**;
the new code changes 127 of them (81 + 46), so the control can fail.

| arcs kept (not refused as not-an-arc) | Brahms (630) | Litolff (407) |
|---|---:|---:|
| two notes, SAME step, detector said SLUR -> TIE | 66 | 30 |
| two notes, DIFFERENT step, detector said TIE -> SLUR | 4 | 15 |
| 3+ notes, ends DIFFERENT, detector said TIE -> SLUR | 9 | 0 |
| detector SLUR, same step, accidental unreadable -> ABSTAIN | 2 | 1 |
| two notes same step, detector TIE (confirmed) | 114 | 15 |
| two notes different step, detector SLUR (confirmed) | 6 | 26 |
| class stands: a printed accidental on the stop head | 31 | 2 |
| class stands: an end position UNREAD / the two instruments disagree | 4 / 0 | 27 / 9 |
| not judged at all | 317 | 270 |

Not judged splits (Brahms / Litolff): `no_head_near_the_arc` 93/86 (the arc is
the NEIGHBOUR staff's, caught in the cell pad), `chord_or_second_voice_at_an_end`
77/71, `no_start_head`+`no_stop_head` 62/54, `enters_from_previous_system`+
`runs_off_the_system` 44/39, `spans_a_whole_bar` 20/1, `arc_cut_at_both_
barlines` 11/12, `arc_end_far_from_its_head` 8/1, `arc_narrower_than_a_head_
and_a_half` 2/6.

### 16.3 Sean's hand-labelled Brahms page (`data/hand-truth/pages/imslp317803/0.json`, labeler `sean`, 73 tie/slur boxes, labelling in progress)

Each truth box matched to the kept arc with the highest IoU (>= 0.30); 61 of
73 match:

|  | before | after |
|---|---:|---:|
| truth SLUR -> ours slur | 30 | 31 |
| truth SLUR -> ours tie | 2 | 1 |
| truth TIE -> ours tie | 18 | 23 |
| truth TIE -> ours slur | 11 | 6 |
| **right, of 61 matched** | **48** | **54** |

Every arc the rule CHANGED that Sean has labelled is right (8 of 8: 7
slur->tie, 1 tie->slur); none of his labelled arcs was made wrong. The 6 truth
ties still read slur are arcs the rule did not judge (the neighbour staff's
copy, a chord end, no head near the arc) -- not a rule failure. In-sample
caveat: Sean's boxes are `prefill-confirmed` from the same detector, and 9
truth ties have no matching arc at all (a GATHER matter).

### 16.4 Stacked pairs (the second rule)

Strict stack (one staff by a DECIDED `arc_owner`, same two end heads, boxes
disjoint in y, same side of the heads, a single head at each end): **0** on
both pages. The geometry-only scan (`probe/tie_slur_2_75/nested.py`: x-spans
overlap >= 80% and share an end, y-disjoint, gap <= 3 spaces, one decided
owner) finds 138 pairs on Brahms (71 above, 17 below, 50 with the heads
between them) and 71 on Litolff (12 above, 7 below, 52 straddling) -- but the
crops show most are NOT one tie and one slur over the same notes: duplicate
detections, tied-chord ties, and the next staff's arc given the same owner
(`arc_owner` decided it onto this staff). Where a real pair exists it is the
usual nested one -- an inner two-note arc and an outer arc over 3+ notes -- and
the two-note rule already makes the inner a tie and leaves the outer a slur, so
the stack rule changes nothing there. Two clean below-the-notes pairs are
cropped for Sean (`out/print/2.75/stacked_below_*`); in both the arc NEARER
the heads is the inner two-note arc.

**CONVENTION ASSUMED / NOT CONFIRMED** for arcs under the notes: the nearer arc
(the UPPER of the two) is the tie -- an engraved tie hugs its heads -- where
Sean's sentence says "bottom". FALSIFIED by Sean answering B on either tile.

### 16.5 Risk side, and what was checked

The refused flag lost on tie->slur (+130 scan edits). Here that half fires 28
times (13 Brahms, 15 Litolff) and was looked at by eye: 12 Litolff and 4 Brahms
crops of the tie->slur arcs (short curves joining a note to the next note at a
different height, and arcs whose ends differ). Two Litolff boxes were not arcs
at all (staff-line ink 11 and 15 px wide) -- those are now
`arc_narrower_than_a_head_and_a_half` and not judged; one 43 x 5 px sliver in a
staff gap is still judged (what kind a non-arc is called is moot, and the
refusal of it belongs to 2.60). Frame control on the 10 arc crops: ink inside
the bracketed box 0.20-0.65 against 0.000 for the same box shifted 300 px,
every tile. On the 2 stacked tiles the shifted box landed on other notation
(dense page), so that control is inconclusive there and the brackets were
checked on the arcs by eye. 10 changed arcs + 2 stacked-below pairs are in
`out/print/2.75/` for Sean (blind; our reading only in `manifest.json`).

### 16.6 Reproduce

```bash
# small re-gathers (record on the tree under test)
python3 -m tools.omr.acceptance_quick --doc brahms1-breitkopf --out-root $OUT
python3 -m tools.omr.acceptance_quick --doc beethoven5-litolff --out-root $OUT
P=benchmarks/omr-arc-grammar-2026-09/probe/tie_slur_2_75
PYTHONPATH=. python3 $P/replay.py $REC rows.json      # ADJUDICATE through tie_pair, one row per arc
PYTHONPATH=. python3 $P/control.py $REC rows_old.json # OLD code must give the record's own verdicts N of N
python3 $P/pop.py rows.json                           # the table in 16.2
PYTHONPATH=. python3 $P/score.py rows.json --list     # 16.3 against the hand-labelled page
PYTHONPATH=. python3 $P/nested.py $REC --list         # 16.4
```

`out/2.75-brahms.rows.json` and `out/2.75-litolff.rows.json` hold the new
code's per-arc rows (`2.75-*-old.rows.json`: the old code's), so every figure in
16.2-16.4 re-reads from a checkout without the 108 MB / 48 MB records.

### 16.7 What is NOT established

* Whether the 31 Brahms arcs whose stop head wears a printed accidental hide
  further ties: a tie across a barline whose start head wears an accidental is
  left alone on purpose (the barline cancels it; a slur to the natural is
  indistinguishable by position).
* The `0.25` same-position limit (legacy) and the `1.5`-width arc floors
  (eyeballed on two slivers) are not swept.
* Litolff's merged plate: the 15 tie->slur on its count pages look right by eye
  (adjacent notes a step apart under a short curve) but none is Sean-judged.
* Not measured: EXPORT. Only the first two stages were run, per Sean's
  2026-09-30 instruction; `adjudicate_tie_pair` pairs a reclassified tie
  (tested), and whether the file then carries fewer edits is unmeasured.


### 16.8 Sean judged the 12 tiles (2026-10-09, `out/print/2.75-review/answers.json`) -- and the chord fix

Single arcs **8 of 10 right**; both stacked-below pairs **right** ("A tie, B
slur": the arc NEARER the noteheads is the tie -- the convention is now
CONFIRMED, not assumed). The two wrong: `litolff_02` and `litolff_03`, both
TIES -- a two-note chord tied across a barline, which the rule made slurs.
Measured on the records: at each end the detector had fused the chord into one
tall box (1.5-1.65 head heights) and/or refused the second head as a
`stacked_head_duplicate`; the arc was paired with the one head left, a step
away from the one at the other end.

Sean, judging `litolff_05`: *"as a rule, regardless of where the ties are and
if they are close to note heads that are the same it is a tie"*. Built so:

* an END is a column: every usable head in the column of the nearest head
  (chord members, a unison, another voice), plus the boxes refused as a
  DUPLICATE of a head (the ink is a real head's) and the two head-sized ends of
  a box taller than 1.4 head heights (`TALL_BOX_HEAD_HEIGHTS`, fused heads);
  a pairing at ONE pitch anywhere among them is a TIE (a half-box has no step,
  so its height alone can prove SAME, never DIFFERENT);
* different pitch -> SLUR fires only when no same-pitch pairing exists AND each
  end is a single head. At a chord end with no same-pitch pairing the class
  STANDS (`relation: chord_no_same_pitch`): the first version of this fix
  slurred tied chords on Brahms p0 bar 3 (a missing partner), caught in the
  crops before it was kept. Exception kept: an arc over 3+ onsets whose ends
  share no pitch is still a slur (a tie never skips a note);
* the stack rule skips chord ends (a tied chord prints one tie per note).

Result on the SAME 12 tiles after the fix, on a fresh small re-gather of the
merged tree (main f93f41d9 incl. 2.72 / 2.73 / 2.68): **single arcs 10 of 10,
stacked pairs 2 of 2** (in-sample: two of the ten were the cases the fix was
written for). Sean's hand-labelled Brahms page, 61 matched truth boxes: **55
right** (before this fix 54; before 2.75, 48): truth tie -> ours tie 24
(was 23), the only arc that got worse mid-fix (a truth slur over chord ends) is
back to slur. Changed vs the detector on the replay of the base records:
Brahms 98 (81 slur->tie, 14 tie->slur, 3 abstain), Litolff 75 (64, 8, 3);
the extra slur->tie flips over the first version are tied chords (34
Litolff, 15 Brahms; sampled by eye). Fast tier 6,719 passed; `check` 193 (the merge itself moved `reach` 22 -> 23; this lane adds no
quantity).

Open: `adjudicate_tie_pair` still pairs only single same-position heads, so a
tie recognised through a duplicate or a half-box abstains `no_pair_at_one_
position` there -- the kind is right, the `<tied>` pairing for these chord
ties is unwritten (EXPORT unmeasured).


### 16.9 Sean REJECTED 16.8's "any same-pitch pairing in the column" -- the top/bottom rule

Sean (DECISIONS 2026-10-09): *"It is possible for the notes to switch up and
have a tie on one end and a slur on another ... if the arc is above it needs to
match the notes at the top; if it is below it needs to match the notes on the
bottom."* Rebuilt: at each end the candidates are still the column (usable
heads, boxes refused as a duplicate, the two head-sized ends of a tall fused
box), but the arc joins only the EXTREME one on its own side -- the top note if
the arc lies above the end's notes, the bottom note if below -- and tie vs slur
is decided on that pair alone. An arc inside a chord's extent, or above one end
and below the other, has no extreme note (`side_unclear`); an extreme with no
staff step (a tall box's end) is unreadable (`unread`); both leave the
detector's class. A refused box that sits on a usable head (vertical overlap
>= half) is that head drawn twice and is not a candidate (it had made
litolff_06 a lower note a step below its own head).

Red first: six tests failed on a0d77e6a (top matches / bottom differs: arc above
tie, arc below slur; the reverse; the other side's pair never overturns the
class; an arc between the notes; a tall-box extreme with no step; and the
duplicate-on-a-head control).

**Sean's 12 tiles, fresh re-gather of the merged tree: single arcs 8 of 10,
stacked 2 of 2.** litolff_02 and litolff_03 (his two ties): both now keep the
detector's TIE -- by ABSTENTION, not by a reading: at each the start chord is
ONE tall box (`diag_litolff_*`: 32 and 38 px against a 21 px head), its bottom
end has no staff step, so the arc below it cannot be matched to a note;
`out/print/2.75-chords/`. Two tiles that the any-pair rule had right are now
wrong, and the rule is not bent for them:

* litolff_04 (Sean: tie, detector: slur): the stop "head" is a 48 x 45 px
  merged blob (head + barline ink). Its bottom end has no step -> unread -> the
  detector's SLUR stands. `diag_litolff_04.png`.
* litolff_06 (Sean: tie, detector: slur): not a chord at all. Two hatched
  heads of one height, boxes 6.5 px (0.28 spaces) apart, rounded to steps 7 and
  6 by the staff grid: both instruments say "different" (the dy is inside the
  0.25-0.43 band where a half-step should read ~0.5 and a unison 0). A
  threshold would only turn it into an abstention, and the detector's class is
  slur: still wrong. `diag_litolff_06.png`.

Hand truth (Brahms p0, 61 matched): **55 right**, unchanged. The ~79 chord
slur->tie flips of the any-pair rule (45 Litolff + 34 Brahms), under this rule:
Litolff 21 stay TIE, 24 return to the detector's slur (12 top/bottom notes
differ, 8 unread, 4 conflict); Brahms 30 stay TIE, 4 return to slur (2 differ
by the extreme pair, 2 unread). Chord tie->slur: Brahms 5 (4 stay slur -- the
extreme notes differ, e.g. p0 bar 3 `glyph/0/0/3/2/10`, top steps 2 vs 3 --
which Sean should judge, crop `chords_brahms_02`), Litolff 0 from the any-pair
version, 13 vs the detector in all. 5 blind chord crops of unjudged changed
arcs: `out/print/2.75-chords/`. Fast tier 6,724 passed; `check` 193 (merge's
`reach` +1).


## 16.10. 2.75b -- the two reading faults of 16.9: one is fixed, one is honestly unread (lane `lane-2.75-tie-slur-b`)

Path: **STAGED**, GATHER + ADJUDICATE only. Base = the merged tree `9b347c51`
(`lane-2.75-tie-slur` dc81fd1d + main 5e78fdf1), arm = `d75c0be9` (this lane's
one code commit), both CLEAN-tree small re-gathers (Litolff pdf 1-3, Brahms pdf
0-1, own `--out-root` each, arm run with `--against` the base record). Control
first: a replay of ADJUDICATE on the unchanged tree reproduces the base records'
own `arc_kind` verdicts **512 of 512 (Litolff) and 1,034 of 1,034 (Brahms)**, and
the base re-scores Sean's 12 tiles exactly as 16.9 recorded them (8 of 10 singles,
2 of 2 stacked), so the faults below are real and not a changed tree. After
merging main (2.12f, `40875f6a`, head `a336beaf`) the same replay reproduces the
ARM records' verdicts 512 of 512 and 1,034 of 1,034.

### 16.10.1 litolff_06 (Sean: tie) -- the position, not the rule: ONE HEAD, BOXED THREE TIMES

`dy_spaces` said 0.314 and the steps said 7 and 6. The record on the start head
(`glyph/3/1/3/8/5`, `diag_litolff_06_three_boxes_one_head.png`): the detector drew
the half note ON the fourth line three times -- a whole box (kept, y 2861.8-2879.8,
centre 2870.8, position 6.7 -> **7**), its upper half (`8/4`, 2855.7-2870.3, 5.7 -> 6,
refused `stacked_head_duplicate`) and its lower half (`8/3`, 2866.5-2879.5, 6.98 ->
7, refused `notehead_is_a_duplicate_box`). Sean's own 2.73: *half notes, especially
ones on lines, get split up into two smaller boxes*. The ring on the print spans
y ~2856-2879 (centre ~2867.5, on the line); the three boxes TILE it, and the
centre of their union is 2867.7 -> position 6.31 -> **6**. The stop head (a single
box, centre 2864.96, 6.1 -> 6) is on the same line. Nothing about the arc rule
was wrong and the arc decision read the right heads; the kept box's centre was
3-4 px low. "Measured locally" was not the fault either: the two heads' bar grids,
derived from their own glyph rows (canonical centre - position x half-step), agree
to ~1 px (7 canonical units = 1.1 px) -- it is the BOX centre that carries the
0.6-step error. The thresholds in the old note (0.25-0.43)
would have turned it into an abstention, and the class is slur: still wrong.

**Fix (ADJUDICATE, `adjudicate_arc_kind`, the end-head reading):** `_head_extent`.
A refused duplicate box SMALLER THAN A HEAD (<= `gather.HEAD_CUT_MAX_BOX_HEIGHT_
SPACES`, 0.95 spaces -- the 2.73 reader's own line between a half-head and a
head), standing on the kept head (overlap >= half its height, centre within half
a head width in x), is a PIECE of it; the head is read at the centre of the union
of the kept box and its pieces, in its own bar's grid (kept row's position + the
offset in that bar's half-steps; scale from the same glyph row's page/canonical
heights and `Q.CELL_STAFF_SPACE`, which closes a `KNOWN_GAPS` entry: `check`
193 -> 192). No pieces, a far head (ledger-read), a head 2.73 already placed, a
tall (fused) box, or no staff-space unit on the record: nothing changes. `detail
.grammar.tie_slur_rule.two_note.start_extent / stop_extent` record `members`,
`kept_step`, `union_spaces`, `pos`, `step`; `start_step_source` reads
`geometry_extent`.

**A first version took the union of EVERY refused box overlapping the head and was
thrown away on the crops.** It moved 9 Litolff arcs: litolff_06 (both halves), and
7 that went to "unread" because the union came out taller than 1.7 spaces. Crops of
the clusters (`glyph/3/1/3/0/6` and `glyph/3/1/5/11/3`, unions 1.74 spaces, and
`glyph/3/0/5/2/8`, 1.94, kept as `diag_one_head_two_boxes_union_1.94sp.png`): ONE head
each, the second box a full-size copy shifted a few px or stretched into blank paper;
and `glyph/2/1/3/12/6` (`diag_two_heads_boxes_union_2.01sp.png`, 2.01): TWO heads, a
fused box over both. Union height does not separate them (Litolff's 60 clusters --
Brahms has 8 -- run continuously from 1.0 to 4.1 spaces, and the centre offsets of
its 68 refused boxes from 0.00 to 1.25 spaces, with no gap), so no bound on "one
head" was kept: only boxes the size of a PIECE count, which is a statement about the
boxes' kind (2.73), not a threshold fitted to a tile.

Population (the arm prints it first; it is small, and said so): Litolff pdf 1-3 --
512 arcs, 407 kept (not refused as not-an-arc), **210 judged by the two-note rule**,
**2 reached by the piece reading** (both halves of litolff_06's tie), 2 changed
(`slur -> tie`). Heads: 3 of 1,109 kept Litolff heads and 3 of 1,154 Brahms heads
have a refused piece at all; the union moves a step on 2 Litolff heads (one is this
one, the other a ledger-read far head the arc rule does not use) and on 0 Brahms
heads. Brahms pdf 0-1 -- 1,034 arcs, 630 kept, 393 judged, **0 reached, 0 changed**.
`readout diff` base vs arm (`--arm code`): Litolff **2 differences** (both `arc_kind`
slur -> tie), GATHER identical on every family; Brahms **ZERO differences**.
Sean's hand-labelled Brahms page (`data/hand-truth/pages/imslp317803/0.json`, now
140 truth boxes, 125 matched): 109 right, base = arm. Not shown: any difference on
engraved or export, by design (first two stages).

Tests (`test_staged_arc_kind_head_extent_2026_10_09.py`, 10): **red first** -- 3
fail on the unrepaired `ownership.py` (litolff_06 as a tie, the one-step-lower
head, the half-box piece), 7 controls pass on it: two steps lower is a slur; a
refused box the size of a head, beside the head, not overlapping it, and a half-box
with no refusal are NOT pieces; a ledger-read head is never moved by its pieces.

What it does NOT do: the kept head's own PITCH (`restate_pitch` reads the kept box)
stays a step off for that head, and `adjudicate_tie_pair` for litolff_06 still
abstains `no_pair_at_one_position` (its boxes are 5.8 px apart): the KIND is right,
the `<tied>` pairing and that head's pitch are not. Both need the head's position
decided once for ordinary heads (`Q.NOTEHEAD_POSITION` is far heads only), a
decision that reaches 3 of 1,109 heads on these pages -- not built here.

### 16.10.2 litolff_04 (Sean: tie) -- NOT a barline blob; an oversize box, and it stays unread

The old note read the stop box as "head + barline ink". The record and the crop
(`diag_litolff_04_oversize_box_one_head.png`): `glyph/2/0/7/10/3`, 48.5 x 45 px
(2.05 head widths x 2.19 head heights), `noteheadBlackOnLine`, conf 0.26, holds ONE
hollow head (the ring and its slash, bottom space, ~1495.5) at its right, the rising
end of the same tie's right half-arc at its lower left, and the stem's column; the
barline touches its left edge but is not inside it. The box centre (1498.9) reads
7.48 -- on a rounding boundary (residual 0.48) -- while the head is at 7.0. The
reading that is wrong is the BOX, and the box is the same size class as the two
fused-chord boxes Sean judged as ties (litolff_03's start is 1.98 x 1.86), so size
cannot say "one head with other ink" from "two heads fused". ADJUDICATE has no
raster, so the head's own centre cannot be measured there; the arc's two readings
(one head at 7.0 -> tie; two heads, bottom at ~9 -> slur) are both live, the
decision says `unread` (`stop_step_source: tall_box_end`) and the detector's class
stands. **Still WRONG on the tile, honestly unread.** What would resolve it is a
GATHER ink reading of how many head rings a tall box holds and where (not built;
a new item). Its population: Litolff pdf 1-3 -- of the 54 judged arcs that stay
unread, **19 end on a tall box** (17 for that reason alone) and 37 on a far head
whose ledgers were not read (2 are both; the small re-gather pools too few heads
for the far-head reader); Brahms -- 7 unread of 393 judged, 3 on a tall box, 4 on a
far head.
Detector class on those 19: 11 tie, 8 slur, so the class is not noise there, and
litolff_02/03 (also tall-box ends) are right only because it stands.

### 16.10.3 Sean's 12 judged tiles, re-scored on the arm records

| tile | Sean | ours | before 2.75b |
|---|---|---|---|
| litolff_01 | slur | slur (different pitch) | right |
| litolff_02 | tie | tie (unread, class stands) | right by abstention |
| litolff_03 | tie | tie (unread, class stands) | right by abstention |
| litolff_04 | tie | **slur** (unread, class stands) | WRONG |
| litolff_05 | tie | tie (same pitch) | right |
| litolff_06 | tie | **tie (same pitch, extent)** | WRONG |
| brahms_01 | slur | slur | right |
| brahms_02 | slur | slur | right |
| brahms_03 | tie | tie | right |
| brahms_04 | tie | tie | right |
| stacked_below_01 | A tie, B slur | A tie, B slur | right |
| stacked_below_02 | A tie, B slur | A tie, B slur | right |

Singles **9 of 10** (8 before), stacked **2 of 2**; of the 9, two are right only
because the detector's class stands where the rule is unread. In-sample: litolff_06
is the case the fix was written for.

### 16.10.4 The five chord tiles (`out/print/2.75-chords/`, NOT shown to Sean)

Re-checked against the current build (and re-cut from the arm records; four of the
five PNGs came out byte-identical to the previous lane's, which says the gather is
stable there): the readings did not move. `chords_brahms_03` was the arc Sean
already judged as brahms_04 (glyph/1/0/2/5/8, "Tie"), so it was replaced by
`chords_litolff_03` (glyph/3/1/2/6/2): an arc BELOW whose top notes match and whose
bottom notes differ -- the discriminating shape for the top/bottom rule (the any-pair
rule would say tie; ours: slur). Readings are in `manifest.json` only. A unit worth
knowing: `dy_spaces` in the arc decision is measured in AVERAGE HEAD HEIGHTS, not
staff spaces (on Litolff a head box averages 1.2-1.3 spaces), so its 0.25 limit is
~0.3 spaces; the field name is misleading, the behaviour is as measured before.

### 16.10.5 Open

* the chord-tie `<tied>` pairing for export (`adjudicate_tie_pair` pairs single
  same-position heads only), unchanged;
* litolff_06's pairing and the kept head's pitch (16.10.1), litolff_04's head count
  and centre (16.10.2): two candidate items, neither built;
* Sean's judgement of the five chord tiles.

### 16.10.6 On the merged head (main 655407c2: 2.12f and 2.78 landed), `afaa217f`

`adjudicate.ORDER` merged without a conflict and keeps every lane's entries
(`accidental_owner` and `notehead_position` before `arc_kind`; 2.12f's
`articulation_owner` after `stem_direction`; 2.78's `head_stem` and `stem_value`).
2.78 changed `gather._stem_core`, so the proof is a FRESH clean-tree small
re-gather on the merged head (Litolff pdf 1-3, Brahms pdf 0-1, not a replay): the
replay control still reproduces its own `arc_kind` verdicts 512 of 512 and 1,034 of
1,034; Sean's tiles singles **9 of 10**, stacked **2 of 2** (litolff_04 the one
miss); arcs judged 210 / 393, reached by the piece reading 2 / 0, changed vs the
base 2 / 0 -- identical to 16.10.1 -- and the five chord tiles' readings are
unchanged. Fast tier **6,891 passed**, 11 skipped, 2 xfailed (6,830 on the
intermediate merge with 2.12f); `check` **192** against 193 on main 655407c2 (the
one finding left is the closed `KNOWN_GAPS` entry for `Q.CELL_STAFF_SPACE.half_step`).
