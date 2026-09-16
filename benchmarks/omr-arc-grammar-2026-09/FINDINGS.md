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
