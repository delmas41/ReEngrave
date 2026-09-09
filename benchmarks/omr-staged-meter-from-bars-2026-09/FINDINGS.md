# The bars may name their own meter — measured, and it is narrower than it looks

**Beethoven 5 / Litolff `984073`, weights `hollow-graft-shift09`.** One
document throughout, so nothing else varies. ⚠️ **No benchmark was run and
nothing here is a score.** Every number is a control or a diagnosis.

The task, ranked first by
[docs/handoff-2026-09-09-meter-as-a-range-fact.md](../../docs/handoff-2026-09-09-meter-as-a-range-fact.md)
§5, is Sean's:

> *"If there is no meter glyph then we have to deal with bar sums... We have 12
> systems and 10 of them say 4/4 for 6 measures."*

and A-DUR-6's governing rule: *"If there is no established meter then it must
derive the most likely meter based off of the order of determination above."*

---

## 1. ⚠️ THE HEADLINE — A THIRD LEVEL UNDER A SPLIT THE REPO ALREADY MAKES

⚠️ **Not a new idea, a narrower one, and saying so matters.** This project
already separates a meter's NUMBERS from its GLYPH: `export.py` refuses `raw`
because `rhythm._propagated_meter` synthesises it, and `symbol` is set only
where a letter template actually matched — *"the numbers come from the work;
the glyph comes from the page"*.

**What is new is that a bar sum does not determine the NUMBERS either.**

**A bar sum is a LENGTH. It is not a meter.** 2.0 quarter-notes is `2/4` and
equally `4/8`; 3.0 is `3/4`, `6/8` **and** `12/16`; 4.0 is `4/4`, `2/2` and a
common-time `C`. No amount of arithmetic separates them, because they are the
same arithmetic.

So the thing the bars can propose is only half of a meter, and the half they
cannot propose is the half `<time>` prints. Everything below follows from
that:

* the bars name the **length**, on their own evidence, inside one system;
* the **engraving** is borrowed from a system that actually READ one, and only
  where its length already matches;
* where no such system exists the decision **says exactly that** —
  `bars_name_a_length_without_a_form`, with the length, the support and the
  candidate spellings on the record — rather than picking one.

⚠️ Naming a spelling we never saw would be the laundered guess `adjudicate`'s
own docstring bans, and it is not free: `raw` reaches `staged.export` as
`symbol="common"` / `"cut"`, which is a positive claim that a `C` is PRINTED
on a system that printed nothing we could read.

---

## 2. WHAT THE BARS ACTUALLY SAY, over 20 systems on 15 pages

Probed over **20 systems on 15 pages** of the one document (pages 1-2,
17, 61-62 and 63-72). The nine that bear on the question are below.

Measured with `probe_runs.py`, which drives `prepare -> gather -> adjudicate`
and then builds a real `Evidence` over the **live log**, so the bars it
reports are exactly the bars `_corroborate` and `_bar_run` see. Nothing is
re-derived from an exported file — the §6.2 lesson of the previous session.

⚠️ **Cross-checked against a figure written before this session.**
`benchmarks/omr-staged-meter-carry-2026-09/FINDINGS.md` §11 records p.62
system 0 as cell 3 = 4.0 at 9/11, cell 5 = 4.0 at 6/12, cell 6 = 3.0 at 9/16.
The probe reproduces all three exactly.

| system | truth | assessable bars | modal lengths | agree − disagree |
|---|---|--:|---|--:|
| `system/1/0` · meter READ (control) | 2/4 | 10 | 2.0 ×10 | **+10** |
| `system/2/0` · abstains `no_evidence` | 2/4 | 10 | 2.0 ×8, 4.0, 1.0 | **+6** |
| `system/2/1` · abstains `too_few_staves` | 2/4 | 9 | 2.0 ×8, 2.5 | **+7** |
| `system/63/0` · abstains `no_evidence` | 3/4 | 9 | 3.0 ×7, 2.0, 6.0 | **+5** |
| `system/63/2` · abstains `too_few_staves` | 3/4 | 8 | 3.0 ×6, 1.5, 1.0 | **+4** |
| `system/17/0` · *Andante* | 3/8 | 4 | 3.0, 3.5, 1.0, 1.5 | **−2** |
| `system/17/2` · *Andante* | 3/8 | 2 | 1.0, 3.0 | 0 |
| `system/61/0` · finale | 4/4 | 1 | 4.0 | +1 |
| `system/62/0` · finale | 4/4→3/4 | 3 | 4.0 ×2, 3.0 | +1 |

✅ **THE `3/4` ON PAGE 63 IS HAND-READ FROM THE PRINT.** It was written up as
an inference first — the reference encodes `beethoven--symphony-5--mvt4` as
4/4 → **3/4 at bar 155** → 4/4 at bar 209 → 2/2 at bar 364, and p.62 prints
bar 147 — and then the pages were actually rendered and looked at, because
that inference is the row the whole abstaining branch rests on. **p.62 prints
`147` at top-left (under the folio number `62`) and p.63 prints `160`.** 160
lies inside 155-208, so every system of p.63 is in **3/4**, read off the page
rather than derived from the same arithmetic the mechanism uses.

**The bars are a real reader of bar length**, and they separate: every system
whose bars name their truth scores **+4 or better**, and every system that
should say nothing scores **0 or less** except two that are simply too thin.

---

## 2b. THE ARMS — what the live pipeline does with it

`OMR_METER_FROM_BARS=1`, carry OFF, so nothing else is in play.

| run | system | before | after |
|---|---|---|---|
| `--pages 0-2` | `system/1/0` | `voted` 2/4 | unchanged |
| | `system/2/0` | abstained `no_evidence` | **`derived_from_bars` 2/4**, length 2.0, support +6.0 (8+/2−), form ← `system/1/0` |
| | `system/2/1` | abstained `too_few_staves_read_it` | **`derived_from_bars` 2/4**, length 2.0, support +7.0 (8+/1−) |
| `--pages 1,17` | all three *Andante* systems | abstained `no_evidence` | **unchanged** — the control holds |
| `--pages 0,63` | `system/63/0` | abstained `no_evidence` | **`bars_name_a_length_without_a_form`**, length 3.0, support +5.0 (7+/2−), forms `3/4` `6/8` `12/16` |
| | `system/63/2` | abstained `too_few_staves_read_it` | same, length 3.0, support +4.0 (6+/2−) |
| | `system/63/1` | abstained `too_few_staves_read_it` | unchanged — 2 assessable bars |
| `--pages 1,63` | `system/1/0` | `voted` 2/4 | unchanged |
| | `system/63/0`, `system/63/2` | as above | **same refusal** — the 2/4 is present and is NOT borrowed |

⚠️ **The last row is the discriminating control, and the first `0,63` run was
not.** Page 0 of this PDF carries no system, so in `--pages 0,63` there was no
source of ANY length and the refusal only showed "nothing to borrow from".
`--pages 1,63` puts a `voted` **2/4** (length 2.0) in front of bars that say
**3.0**, and the form is still refused — so the length gate is exercised on a
real page and not only in a unit test.

⚠️ **The live run reproduces the probe to the term** (+6.0 from 8+/2−, +7.0
from 8+/1−). That agreement is the control that makes §2's table a
measurement of the pipeline rather than of the probe.

**In the exported file, pages 0-2** (`--musicxml`, coverage report):

| | OFF | BARS |
|---|--:|--:|
| `empty_bars_padded_without_meter` | 47 | **0** (field gone) |
| `measure_rests_read` | 92 | **169** |
| `written.notes` | 648 | **665** |
| `not_written.duration_narrowed` | 163 | **146** |
| `written.rests` | 278 | 201 |

⚠️⚠️ **THESE ARE THE CARRY'S OWN NUMBERS, TO THE UNIT.** The previous
session's handoff §3 records exactly `648 → 665`, `163 → 146` and
`empty_bars_padded_without_meter: 47` disappearing, for
`OMR_METER_CARRY=1`. **So on this document the two mechanisms do the same
work on the same systems**, and it would be wrong to present this as a gain
on top of the carry. What it is instead is stated in §4a.

**Control.** Flag-off `--pages 0-2` matches the artefact committed *before
this session* (`omr-staged-meter-carry-2026-09/out/p012-OFF.meter.json`) on
every subject, outcome, reason and value — the one difference being the
`segments` field, which that session added afterwards.

## 3. ⚠️ THE LITERAL READING OF "FOR 6 MEASURES" IS THE WRONG ONE

Sean's phrase is a RUN of consecutive bars, and consecutiveness was measured
before it was designed away. Longest run of consecutive assessable cells at
one length:

| system | longest consecutive run | assessable bars |
|---|--:|--:|
| `system/1/0` (meter read) | 5 | 10 |
| `system/2/0` | 3 | 10 |
| `system/2/1` | 3 | 9 |
| `system/63/0` | 3 | 9 |
| `system/62/0`, `system/61/0` | **1** | 3, 1 |

A run breaks whenever one bar is **unassessable** — under three staves, or no
cross-staff majority — and that is a fact about the page's legibility, not
about its meter. Requiring consecutiveness spends the evidence on the wrong
question. **So "the longer the more likely" is expressed by the terms
ACCUMULATING** (+1.0 per agreeing bar, −1.0 per contradicting one) rather than
by a run-length constant: a long coherent stretch clears any floor and a short
one does not, with no second threshold to tune.

---

## 4. ⚠️⚠️ AND IT CANNOT CROSS A MOVEMENT BOUNDARY — WHICH IS THE POINT

The reason a bar-sum proposal was **not** admitted in the previous session is
p.17: the bars there *"name nothing coherent and would manufacture meters from
noise"*. Measured, that is exactly right and the mechanism handles it without
a special case:

* `system/17/0` — four assessable bars at **four different lengths**. The
  commonest plausible one scores **−2.0**, under a floor of 4.0.
* `system/17/1` — one assessable bar. `system/17/2` — two, at two values.
* ⚠️ And `1.0` quarter-notes is **not a candidate at all**: no meter in the
  template reader's own `DEFAULT_METERS` is one quarter long, and
  `rhythm._drop_implausible_meters` already names `1/4` in its docstring as
  garbage that survives upstream filtering.

**The structural claim, and it is why this is not a second copy of the
carry:** every term comes from bars inside ONE system. The *Andante* cannot be
handed movement 1's `2/4` by this route however many pages of `2/4` precede
it. The only thing that reaches across systems is the **spelling**, and that
is gated on the length already matching.

---

## 4a. ⚠️⚠️ WHAT THIS IS WORTH, STATED AGAINST ITSELF

On the one document available, **the DECIDED branch never fires on a system
the carry does not already serve.** Pages 0-2 are the whole of it, and there
the two mechanisms produce identical files.

That is not a reason to discard it, and it is not a reason to oversell it.
The two differ in **what they can be wrong about**, which is the thing a
layered model cares about:

* the carry's evidence is *"a previous system read this"* — it reaches across
  a movement boundary and is stopped only by the bars refusing it;
* this reads *"this system's own bars say this"* — it cannot reach across a
  boundary at all, because it never looks at another system.

**The case that separates them is a movement boundary on a page that READS
WELL**, where the old meter is refused AND the new one is coherently named.
That case is unmeasured here for the same reason §4 of the previous handoff
gives: the one boundary on this document is a page whose bars are noise.

**And the branch that IS new is the abstaining one.** `system/63/0` and
`system/63/2` are systems the pipeline previously had nothing at all to say
about, which now record *"these bars are three quarter-notes long; it is one
of `3/4`, `6/8`, `12/16`; nothing on this document has told us which"* —
**and the truth is `3/4`.** That is a fact a later reader, a roster, a
dossier or a second page can close, and it is on the record where it was not
before.

## 5. THE CONSTANT, AND THE ONE THAT WAS DELETED

`METER_FROM_BARS_FLOOR = 4.0`, in the same signed currency the carry uses
(`W_METER_BAR_FITS` / `W_METER_BAR_CONTRADICTS`, **imported rather than
restated** so the two mechanisms cannot drift about what a bar is worth).

It sits on the empty band between **+4** (the weakest correct system) and
**−2** (the *Andante*'s own first system) — a band no measured system falls
in. ⚠️ It is chosen to stay REACHABLE
by a real negative: the *Andante*'s four bars could score at most +4, so that
page reaches the floor and is refused by it rather than being excluded earlier
and leaving the floor justified by nothing.

⚠️⚠️ **A SECOND CONSTANT WAS WRITTEN, MEASURED INERT, AND DELETED.**
`METER_FROM_BARS_MIN_ASSESSABLE = 4` was added on `METER_CARRY_MIN_BARS`'s
reasoning that *"is there enough evidence to judge?"* and *"does the evidence
support it?"* are two questions. **A mutation arm proved it cannot fire**:
deleting the constant outright broke no test, because a bar is worth 1.0 so
support can never reach a floor of 4.0 without four assessable bars. It is
gone rather than left as decoration — **a gate that cannot fire reads to the
next person as a protection that is not there.** The reasoning still stands
and would need weights that separate the two, which n = 20 systems on one
document cannot supply.

---

## 6. NINE MUTATION ARMS, AND WHAT SURVIVED

Every rule was run RED before it was believed, clearing
`~/Library/Caches/com.apple.python/<abs path>/` between arms — the previous
session's §6.3 trap, where a reverted mutation stayed live.

| arm | tests that went RED |
|---|--:|
| unwire the `no_evidence` call site | 5 |
| drop the plausible-length filter | 1 |
| **drop the minimum assessable-bar count** | **0 — SURVIVED, see §5** |
| drop the support floor | 2 |
| borrow the source's `raw` spelling too | 1 |
| let a DERIVED meter lend its spelling onward | 1 |
| borrow a form of the WRONG length | 1 |
| ignore the flag (default ON) | 1 |
| ask the bars BEFORE the carry | 1 |

---

## 7. ⚠️ AND A CLEAN, BELIEVABLE ZERO THAT WAS THE HARNESS

The first `OMR_METER_FROM_BARS=1` arm came back **byte-identical to the
control** — three systems, same reasons, same values. That is exactly what a
mechanism with no reach looks like, and it was nearly written up as one.

It was the shell. The arm runner passed its environment as
`env $3 python3 -m tools.omr.staged ...`, and **zsh does not word-split an
unquoted parameter expansion** — the trap this repo already documents for
`${=IDS}` in the labeling runbook. So `env` received ONE argument and set

```
OMR_METER_FROM_BARS = "1 OMR_METER_CARRY=0"
```

which `meter_from_bars_enabled()` correctly reads as *not `1`*. The flag was
off in the arm that existed to turn it on.

**Nothing about the output invited suspicion** — same shape as the cached
`scan_eval` A/B and the cached bytecode of the previous session. The tell was
that the probe, reading the live log, had already said `system/2/0` scores
`+6`; the run disagreed with a measurement made an hour earlier on the same
tree. **Check a probe against the pipeline, and check the pipeline against the
probe — the arrow points both ways.**

## 7. Reproducing

```bash
ln -sfn <main checkout>/library library
ln -sfn <main checkout>/tools/omr/training/data/weights tools/omr/training/data/weights
PDF=library/editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf
W=tools/omr/training/data/weights/deepscoresv2-yolov8l-hollow-graft-shift09-2026-09-04.pt

# what the bars say, per system, off the LIVE log
PYTHONPATH=$PWD python3 benchmarks/omr-staged-meter-from-bars-2026-09/probe_runs.py \
    "$PDF" --pages 0-2 --weights "$W"

# the arms
OMR_METER_FROM_BARS=0 python3 -m tools.omr.staged "$PDF" --pages 0-2 --weights "$W" --out off.json
OMR_METER_FROM_BARS=1 python3 -m tools.omr.staged "$PDF" --pages 0-2 --weights "$W" --out bars.json
python3 benchmarks/omr-staged-meter-from-bars-2026-09/extract_meter.py bars.json
```

⚠️ **Multi-page runs only.** A single page has no earlier system to borrow a
spelling from, so the whole mechanism reads as inert — the same structural
blindness the scan gate's one-page-per-row cut imposes.
