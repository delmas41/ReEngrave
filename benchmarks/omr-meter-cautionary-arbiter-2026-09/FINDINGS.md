# The cautionary's arbiter — the score is not a currency, and a same-frame contest is BLIND

2026-09-15, branch `claude/meter-cautionary-arbiter`, base
`claude/meter-template-at-changes` (`6522d26c`).
**NO FILE UNDER `tools/` IS TOUCHED. No rule, no flag, no test in the suite.**
This is a measured REFUSAL, which the brief named as one of its two acceptable
outcomes, plus the arm that would settle what is left.

    python3 benchmarks/omr-meter-cautionary-arbiter-2026-09/arbiter_reach.py --check
    python3 benchmarks/omr-meter-cautionary-arbiter-2026-09/probe/score_frames.py --check
    python3 benchmarks/omr-meter-cautionary-arbiter-2026-09/probe/where_the_opening_sits.py --check
    python3 benchmarks/omr-meter-cautionary-arbiter-2026-09/probe/overlap.py --check
    python3 benchmarks/omr-meter-cautionary-arbiter-2026-09/mutation_battery.py

⚠️ **A NOTE ON PROVENANCE.** The harness refused the subagent that did this work
permission to create this file ("Subagents should return findings as text, not
write report files"). It returned the text and the managing session wrote it
here verbatim rather than burying it in a Python docstring or defeating the
guard with a shell heredoc — the shape this repo already records once, where a
23k-character FINDINGS was stranded inside a module docstring and had to be
extracted later.

---

## 0. ⚠️⚠️ n LEADS, BECAUSE IT IS STILL THE BLOCKER

**THREE cautionaries in the whole corpus, on ONE piece of music** (Brahms 1
mvt 1, engraved and scanned). One DISAGREE pair, one AGREE control, one
OPENING-UNKNOWN. The cost case — *a cautionary WRONG where the opening is
RIGHT* — **has never been observed**, so any "1 fixed / 0 broken" is scored on
a corpus with no opportunity to break. That was the cautionary session's
verdict and nothing here moves it.

Everything below is a reason the SUBSTITUTED arbiter cannot be built even if n
were larger. **Nothing here is a reason to stop wanting Sean's table**, which is
right; it is a statement about which quantity can serve as its arbiter.

---

## 1. REACH FIRST — the substituted arbiter has reach ZERO on the corpus

`arbiter_reach.py --check`, exit **3** (`DEAD`). Committed:
`out/arbiter-reach.json`, `out/arbiter-reach.log`.

```
cautionary/opening pairs in the whole corpus ......... 3
...with a hand-read print truth ...................... 3
...carrying a CAUTIONARY-side template score ......... 0
...carrying an OPENING-side template score ........... 0
...carrying BOTH — the arbiter's own reach ........... 0

committed *.meter.json files ......................... 68
...carrying a template `score` ....................... 0
...carrying `raw` (THE POSITIVE CONTROL for this grep) 66
...carrying any `meter_template_at_bar` row .......... 0
```

⚠️ **THAT ZERO IS ABOUT THE CONTAINER, NOT ABOUT THE SCORE, and the two are
reported apart on purpose.** `*.meter.json` is an EXTRACT of the meter verdicts,
so `score: 0 of 68` means *no committed artefact carries one* — the positive
control (`raw`, which `adjudicate_meter` does read, present on 66 of 68) is what
makes that a fact rather than a broken search. A cautionary-side score requires
`OMR_METER_TEMPLATE_AT_BAR=1` **and a re-gather**, which needs `omr-weights/`
and `library/`; neither exists in a cloud container.

**So nothing in §2-§5 scores the arbiter on the three pairs.** What it does
instead is ask whether the quantity could arbitrate AT ALL, on real scanned ink,
which is answerable without weights.

---

## 2. ⚠️⚠️ THE SCORE IS MONOTONE IN WINDOW WIDTH BY CONSTRUCTION — so the two sides are not on one scale

`locate_time_signature` is, in its own body:

```python
response = cv2.matchTemplate(strip, template, cv2.TM_CCOEFF_NORMED)
_, score, _, location = cv2.minMaxLoc(response)
```

— a **MAXIMUM over every x position in the strip**, with no normalisation for
how many positions there were. A wider strip contains the narrower strip's
positions as a subset, so its maximum can only be **greater than or equal**.

Measured on the base branch's own committed 1,612 real mid-staff windows
(`benchmarks/omr-meter-template-changes-2026-09/out/empty-window.json`, the same
window re-read at 4 and at 8 staff spaces):

| | |
|---|--:|
| paired windows | 1612 |
| score HIGHER at 8 spaces | **968** |
| score LOWER at 8 spaces | **0** |
| mean delta | +0.0725 |
| max delta | +0.463 |

**Not one window scored lower in the wider strip.** That is the identity showing
up in data, not a trend.

And the two sides of the proposed contest are read in windows of different
width, measured on real pages rather than assumed:

| | reader | window |
|---|---|--:|
| the OPENING | `gather_meter` → `header_cells_for_page` | **16.0 staff spaces** |
| the CAUTIONARY | `gather_meter_at_bars` → `_bar_head_window` | **4.0 staff spaces** |

> **A `caut_score > open_score` comparison is a maximum over a subset against a
> maximum over a superset. It is biased toward the OPENING — the same direction
> the staff count already fails in on the one contested pair.**

---

## 3. ⚠️⚠️ AND THE SAME-FRAME REPAIR IS NOT MERELY BIASED, IT IS BLIND — the distance is 10-12 staff spaces

The obvious fix is to read the OPENING in the bar-head frame too (cell 0, 4
spaces), so both sides are maxima over equal strips. **It cannot work, and the
reason is where the ink is.**

`probe/where_the_opening_sits.py --check`, exit **0**. Committed:
`out/where-the-opening-sits.json`, `out/where-the-opening-sits.log`.

The fixture is Brahms 1 / Breitkopf **p.45**, and its print was LOOKED AT rather
than inferred: page number 46, the word **Adagio**, full instrument names in the
margin (`2 Flöten`, `2 Oboen`, `2 Klarinetten in B`, `2 Fagotte`), and a
common-time **`C`** printed on every staff. A movement start, truth `C`, no
truth file needed.

| bar-head window | answered | RIGHT (`C`) | median best score |
|---|--:|--:|--:|
| 4.0 spaces (the shipped bar-head width) | **0 / 16** | 0 | 0.3571 |
| 6.0 | 0 / 16 | 0 | 0.3746 |
| 8.0 | 0 / 16 | 0 | 0.3794 |
| 10.0 | 0 / 16 | 0 | 0.3794 |
| 12.0 | 12 / 16 | 9 | 0.5996 |
| 14.0 | **16 / 16** | 15 | 0.6254 |
| 16.0 | 16 / 16 | 15 | 0.6254 |
| **HEADER window, 16.0 spaces (what ships)** | **16 / 16** | **15** | — |

**The same printed meter, the same sixteen staves: 0 of 16 at four spaces and
16 of 16 at fourteen.** A staff opens with a CLEF and a KEY SIGNATURE and only
then its meter, so the first four spaces of cell 0 hold a clef — and forced
below the floor the 4-space window spells `4/4`, `9/4`, `12/16` and `5/4`, i.e.
junk out of clef ink.

⚠️ **This does NOT argue against the base branch's mechanism.** A mid-staff
meter CHANGE is printed directly after a barline with no clef in front of it,
which is exactly why `_bar_head_window` is four spaces wide. What it kills is
the only construction under which the cautionary and the opening could be
compared in one frame.

⚠️ **The positive control is the header row**: had the reader failed at every
width, the zeros above would measure a dead instrument. It reads the meter on
16 of 16.

---

## 4. ⚠️⚠️ AND THE ABSOLUTE SCORE DOES NOT SEPARATE — not even inside ONE frame

`probe/score_frames.py --check` over all ten pages exits **2**, and the non-zero
is the PREMISE CHECK firing, which is the instrument working (§4b). The nine
continuation pages alone (`--exclude brahms1-p045`) exit **0**, `CHECK OK`.
Committed: `out/score-frames.json`, `out/score-frames-nine.json` and their logs.

Ten committed real scanned pages, two publishers, four populations read on the
SAME pages so the four are comparable to each other. **p.45 is separated out
because it prints a meter** — every other page is a continuation page of a
movement already under way, so every answer there is a FALSE POSITIVE and no
answer is a miss.

**p.45 — a real printed `C` on every staff (the TRUE population):**

| population | n | ≥ floor | median | max | spellings |
|---|--:|--:|--:|--:|---|
| header, 16 sp | 16 | **16 (100%)** | 0.6158 | 0.6850 | `C` ×16 |
| head0, 4 sp | 16 | **0 (0%)** | 0.3571 | 0.3951 | — |
| head_last, 4 sp | 16 | 0 (0%) | 0.1296 | 0.4108 | — |
| head_mid, 4 sp | 96 | 0 (0%) | 0.2600 | 0.4549 | — |

**The other NINE pages — every answer FALSE:**

| population | n | ≥ floor | median | p99 | max | spellings |
|---|--:|--:|--:|--:|--:|---|
| header, 16 sp | 191 | **32 (16.75%)** | 0.4459 | 0.5828 | **0.6318** | `C` 21, `4/4` 11 |
| head0, 4 sp | 191 | 3 (1.57%) | 0.3411 | 0.5188 | 0.5229 | `4/4` 3 |
| **head_last, 4 sp** | 191 | **5 (2.62%)** | 0.3428 | 0.5121 | **0.6141** | `C` 3, `4/4` 2 |
| head_mid, 4 sp | 1309 | 11 (0.84%) | 0.3294 | 0.4939 | 0.5408 | `C` 10, `7/4` 1 |

Positive control on the nine-page arm: a real Bravura `3/4` stamped into every
seventh window — **274 tried, 266 answered, 265 with the right `raw`**, min
0.5007. ⚠️ Deliberately OPTIMISTIC (clean template ink on a real scanned
surround) and never to be quoted as a true-positive distribution.

Three readings, and each is load-bearing (`probe/overlap.py --check`, exit 0):

1. **THE POPULATIONS OVERLAP, IN THE FRAME THAT MATTERS.** The TRUE header
   readings run **0.5563 – 0.6850**; the FALSE header readings reach **0.6318**,
   and **9 of 191 false readings score at or above the TRUE minimum**. No
   absolute floor separates them. The brief pre-registered this as the condition
   under which to stop, and it is met.
2. **THE CAUTIONARY LIVES IN THE WORST BAR-HEAD POPULATION.** `head_last` is
   **3.1× more likely to fabricate a meter than `head_mid`** (2.62% vs 0.84%),
   and the single worst bar-head false score anywhere — **0.6141** — is a
   last-cell window. That is *above* the TRUE header minimum of 0.5563, so a
   floor tuned to admit a real reading admits it.
3. **THE HEADER FRAME IS WHERE THE FALSE POSITIVES LIVE** — 16.75% against
   0.84%, a ~20× difference on the same pages and the same reader, which is
   §2's monotonicity arriving as a rate. The width buys the true positives and
   the false ones together.

### 4b. ⚠️ THE PREMISE CHECK FIRED, AND FINDING p.45 IS THE RESULT

`score_frames.py` does not assume its pages print no meter — it asks the
**SHIPPED** `vote_system_time_signature` of each system's header readings,
because the question is not *"do some staves agree"* but *"would this pipeline
declare a meter here"*. It flagged exactly one system: **p.45 s0, voted `C`,
16 votes of 16 voters, median score 0.6162** — and the print confirms it.

**18 continuation header systems, and the shipped vote declares a meter on NONE
of them.** So the shipped opening reader is not shipping false meters on these
pages; its 16.75% per-staff false rate is contained by the cross-staff vote.

⚠️⚠️ **BUT A FIXED 3-STAFF QUORUM WOULD NOT CONTAIN IT, AND THAT IS A CAUTION
FOR THE BASE BRANCH'S OWN CONSTANT.** Asking the base branch's
`METER_TEMPLATE_AT_BAR_MIN_STAVES = 3` question of each frame on the nine
continuation pages:

| frame | columns | columns where 3+ staves agree on a FALSE meter |
|---|--:|--:|
| **header, 16 sp** | 18 | **4** — `beet5lit-p057 s1` reaches **7 staves** agreeing on `C` |
| head0, 4 sp | 18 | **0** |
| head_last, 4 sp | 18 | **0** |
| head_mid, 4 sp | 119 | **0** |

The bar-head zeros reproduce the base branch's own empty-window result
independently, on the same pages. The header row is new: **three staves is not a
safe quorum at 16 spaces.** The shipped vote survives because
`min_staff_fraction` is a FRACTION of the system, not a count — 7 of ~22 does
not clear 0.70. **Do not port that 3 into the header frame.**

⚠️ `--exclude` exists so the nine-page arm can be run with a meaningful
`--check`, and it prints the exclusion as its FIRST line. **Excluding a page to
make a control green is how a control stops being one**, so it is documented as
usable only for a page the premise check has already named, with the reason
written down — which is this paragraph.

---

## 5. ⚠️⚠️ THE "ONE SHARED QUANTITY" IS TWO READERS — a correction to the cautionary session's negative

That session's decisive negative is that the only currency both sides state —
*how many staves read it* — prefers the WRONG reading (**9** for the true
cautionary against **10** for the false opening; 19 against 21 on the engraved
control). That is true of the numbers. It is weaker than it reads, and
`arbiter_reach.py` derives why FROM THE SOURCE rather than asserting it:

```
cautionary staves (_meter_changes.staves_reading_it)  `staves` <- Q.METER_GLYPH
opening staves    (adjudicate_meter.n_staves_spoke)   `rows`   <- Q.METER_TEMPLATE
⚠️⚠️ TWO DIFFERENT QUANTITIES: the one currency the contest shares is not one currency.
```

The cautionary's count is **detector staves** (stacked `timeSig*` digit pairs,
read inside a measure cell); the opening's is **template staves** (an NCC over a
16-space header window). So "9 against 10" compares a detector count with a
template count — **a third frame error in the same contest**, alongside the
score's width dependence.

⚠️ The derivation is NARROW on purpose: it finds the VARIABLE each field is
built from and then the `ev.rows(Q.X)` that assigned it, so a rename shows up as
`null` rather than as a quietly wrong answer. `adjudicate_meter` reads ten
quantities and listing all ten would prove nothing about this one count.

⚠️ **This does not rescue the staff count** — it makes it *unusable* rather than
*unfavourable*, which is a different and firmer reason to refuse it.

---

## 6. ⚠️⚠️ THE CAUTIONARY'S VALUE IS RIGHT; IT IS NOT A CHANGE AT THAT CELL — and the two must not be confused

A sibling session (`benchmarks/omr-meter-corroboration-2026-09/`) proved that
pooling the boundary benchmark's `out/*.meter.json` mixes **seven generations of
the code**, and that deduped on the newest generation the committed
`report_boundary.TRUTH_CHANGES` records **both cautionaries as `None`**:

> *p0's 9/8 is a CAUTIONARY printed AFTER the final barline; it announces the
> NEXT system's meter and governs no bar on this page. A change proposed at
> that page's last cell is WRONG — it would re-size m7.*

**That is a statement about placement, not about value.** `9/8` IS what the
plate prints there and IS the meter of the system that follows; CLAUDE.md already
records it as *"the document's own answer to the misread that follows it"*.
Proposing it as a CHANGE at page 0's last cell re-sizes a bar it does not
govern; using it to arbitrate the NEXT system's OPENING is exactly what a
courtesy signature is for.

> **A reader who meets `TRUTH_CHANGES ... None` and concludes the cautionary is
> junk has read the wrong column.** This job is about its VALUE, and that value
> is correct on both printings of the one true pair.

---

## 7. SEAN'S TABLE, BRANCH BY BRANCH, WITH WHAT IS NOW KNOWN

Sean: *"If the cautionary and real match then great. If the cautionary and real
disagree then see which matches the measure math and go with that one. If one is
unreadable and the other is still check the measure math to confirm."*

| branch | corpus instance | the briefed arbiter | the substituted arbiter | status |
|---|---|---|---|---|
| **AGREE** | engraved `9/8` vs `9/8`, truth `9/8` | not needed | not needed | **already satisfied** — the incumbent keeps it right (R0 `kept_right 1`) |
| **DISAGREE** | scan cautionary `9/8` (TRUE) vs opening `9/4` (WRONG) | **SILENT** — `bars_fit 0 / bars_contradict 1`, and not one of that system's seven bars clears the cross-staff quorum | **UNAVAILABLE and, where measurable, biased toward the opening** (§2-§5) | **no arbiter exists** |
| **OPENING UNKNOWN** | scan cautionary `4/4` (WRONG), truth `6/8` | **SILENT** — `0 fit / 0 contradict` | same | **the fill is measured WRONG on its only instance** — it converts an honest abstention into a confident error |

⚠️ The third row is the one to keep: the boundary FINDINGS parked "fill an
abstention" as *safe-but-unreached*; its reach is one, and that one is wrong.
**`ABSTENTION → WRONG` is counted apart from `kept_wrong` in the scorer for
exactly this reason** — netted in, the rule that commits the ABSENT/DECLINED
collapse reads as costless.

**The arbiter that DOES work in this family is the one already shipped and it is
not a score: CROSS-STAFF AGREEMENT.** §4b measures it holding on 18 of 18
continuation systems and firing correctly on the one movement start. The
cautionary already carries its own version (`staves_reading_it`: 9 and 19 on the
two true instances, **1** on the false one) — which is R3/R4 of the cautionary
session's table, *a floor on the cautionary's OWN evidence*, scoring 1 fixed / 0
broken / 0 abstentions lost **on three rows with one boundary point on each
side.** It is still fitted, and it is still the only shape that works.

---

## 8. THE SCORER — reused, not restated

`benchmarks/omr-meter-cautionary-2026-09/` is the cautionary-contest session's
deliverable, not this one's. `arbiter_reach.py` IMPORTS its `common.py` and
`probe_contest.py` rather than restating the pair-builder — two readings of one
artefact set is the failure this repo records for the accuracy figure held in
four files. Its table reproduces on this tree:

```
R0 do nothing (incumbent)     fixed 0  BROKEN 0  ABST->WRONG 0  kept-R 1  kept-W 2
R1 cautionary always wins     fixed 1  BROKEN 0  ABST->WRONG 1  kept-R 1  kept-W 0
R2 more staves wins           fixed 0  BROKEN 0  ABST->WRONG 1  kept-R 1  kept-W 1
R3 support >= 10.0            fixed 1  BROKEN 0  ABST->WRONG 0  kept-R 1  kept-W 1
R4 >= 3 staves read it        fixed 1  BROKEN 0  ABST->WRONG 0  kept-R 1  kept-W 1
R5 fill an unknown opening    fixed 0  BROKEN 0  ABST->WRONG 1  kept-R 1  kept-W 1
RX inverted (CONTROL)         fixed 0  BROKEN 1  ABST->WRONG 1  kept-R 0  kept-W 1
```

⚠️ **RX is the positive control for the `BROKEN` column and it goes non-zero**,
so the zeros above it are results rather than a column that cannot move.

⚠️ **No score-based arm is scored, and that is honest rather than an omission**:
§1 measures its reach at ZERO, so an arm would report `UNSCORED ×3`.

---

## 9. THE ARM SEAN RUNS — one gather, both sides in one unit for the first time

```bash
python3 benchmarks/omr-meter-cautionary-arbiter-2026-09/local_arm.py \
    --pdf "$HOME/Desktop/ReEngrave/library/editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf" \
    --weights "$HOME/Desktop/ReEngrave/omr-weights/deepscoresv2-yolov8l-hollow-graft-shift09-2026-09-04.pt" \
    --pages 0-3 --out-dir /tmp/meter-arbiter
```

**Page 0 is REQUIRED** — the cautionary is on it.

It gathers ONCE with `OMR_METER_TEMPLATE_AT_BAR=1`, **without `--musicxml`**
(the exporter is imported after the gather), and prints REACH first, exiting
non-zero and declaring itself **DEAD** if the bar-head reader answered nowhere.
Then, per system, THREE readings with **the window width printed beside every
score**:

```
A  the OPENING, header frame        16.0 spaces   (what ships today)
B  the CAUTIONARY, bar-head frame    4.0 spaces   (the base branch's new rows)
C  the OPENING at its OWN bar head   4.0 spaces   (the fair contest)
```

C is computed by the arm itself — re-running only the weightless half of the
pipeline and slicing cell 0 with the gatherer's OWN `_bar_head_window`, with the
page spec parsed by the staged CLI's own `parse_pages` — so **no file under
`tools/` has to change to measure it**.

⚠️ **§3 predicts C will be EMPTY**, and that prediction is the point: if it is,
the same-frame contest is dead end to end and not only on p.45. If it is not —
if some opening's meter does sit inside four spaces — that is a real
falsification of §3 and worth more than the arm's other columns.

**What to look for, in order:** (1) reach; (2) does B read `9/8` at page 0's
last cell, and on how many staves; (3) B against C, never B against A; (4) A
against C on the same opening, which is the width effect on a real opening; (5)
the five spurious `4/4` changes must not gain staves.

---

## 10. TESTS, BATTERY, CHECKS

**No test was added to the suite and none needed to be** — nothing under
`tools/` changed, so there is no new behaviour for the suite to pin. The
instruments ARE the deliverable, and the battery is over them.

**Mutation battery** (`mutation_battery.py`): **8 arms, 8 RED, 0 survivors**,
each breaking one guard and asserting the probe NOTICES — by exit code or by a
number it reports — with `POSITIVE_unmutated` run first so a probe broken to
begin with cannot pass every arm for free. Result: `out/mutation-battery.log`.

⚠️ **THE FIRST RUN REPORTED THREE SURVIVORS AND ALL THREE WERE THE BATTERY'S
OWN.** Two `BAD ANCHOR`s — one arm targeted `_bar_head_window`, which is
IMPORTED from the gatherer and is not in the probe at all, and one had the wrong
indentation — and one arm that survived because its mutation produced a
DIFFERENT failure from the one it checked for (a regex matching neither
function, so the probe printed `NOT FOUND` rather than the single-quantity
line). ⚠️ A fourth fault followed: arm 5's expectation (the `head_last` answer
rate) is **unreachable on a two-page fixture**, because widening the window does
not make a page that prints no meter answer. Re-expressed as **§2's identity
itself** — the `head_mid` MEDIAN must rise, since a maximum over a superset can
only be greater or equal — it goes red, and the arm now doubles as a live check
of the finding.

⚠️⚠️ **AND THE BATTERY WAS KILLED MID-ARM AND LEFT ITS SUBJECT MUTATED — a new
clause on a hazard this repo already records.** An edit was made to
`score_frames.py` while the battery was running (the recorded collision,
arriving against its author), the run was stopped with a task kill, and the byte
snapshot **died with the process**: `ranked = trace.get("scores") or []` stayed
mutated to `ranked = []` on disk. `git status` showed one modified file, which
was ALSO true of the legitimate edit made minutes earlier, so the state was
indistinguishable from an ordinary uncommitted change. **What found it was a
later probe run reporting an impossible zero** — `windows=0` on a page that had
given 100 — not review and not version control.

> **A mutation battery must leave the tree as it FOUND it — which is not the
> same as leaving it as GIT has it, AND AN INTERRUPTED BATTERY OBEYS NEITHER.**

Repaired in the battery: an **in-flight sentinel** (`out/.battery-in-flight`,
gitignored) written before the first arm and deleted on clean exit. A run that
finds one **refuses to start** and names every file at risk with the hash it
should have. The final run was uninterrupted, the sentinel is gone, and all
three probe files are byte-identical to `HEAD`.

| check | exit |
|---|---|
| `python3 -m tools.omr.staged.health --check` | **0** |
| `python3 -m tools.omr.staged.inventory --check` | **0** (14 problems, **0** not on `KNOWN_GAPS` — the base branch's own figure) |
| `python3 -m tools.omr.staged.gather_coverage` | **0** — 77 declared / 44 observed / 0 unaccounted; `METER_TEMPLATE_AT_BAR  TEMPLATE  gather_meter_at_bars` listed |
| `pytest tools/omr/tests/test_flag_default_direction.py` | **3 passed** — 21 rows, **10 default-ON / 11 default-OFF, all consistent**; `OMR_METER_TEMPLATE_AT_BAR` derived as default-OFF with an `In` allow-list, which is the direction its default requires |

⚠️ **The flag guard is blind to `==`, and the arbiter's own base is where that
showed.** On `claude/meter-template-at-changes`, `OMR_METER_CARRY` and
`OMR_METER_FROM_BARS` are read with `== "1"` and therefore appear in **neither**
column of those 21 rows. The sibling corroboration session converted both to
deny-lists, and on the MERGED tree they are visible (12 ON / 10 OFF there).
Reported rather than fixed here — widening the AST scan touches every flag at
once.

---

## 11. ⚠️ WHAT IS NOT ESTABLISHED

* **NO ARM RAN END TO END.** Nothing here re-gathered, re-adjudicated or
  re-exported. §9 is the measurement and it has not been run.
* ⚠️ **NO CAUTIONARY WAS EVER SCORED BY THE TEMPLATE READER**, because no
  committed artefact carries one (§1). §2-§4 say the score *cannot* arbitrate;
  they do not say what it *would* have said on the three pairs.
* **The three pairs are unchanged and unscored by any new rule.** n = 1 piece of
  music, and the cost case has never been observed.
* ⚠️ **§4's false populations are ONE-SIDED BY CONSTRUCTION** — every window on
  the nine continuation pages is empty, so the false-positive side is measured
  and the true-positive side rests on **one page, 16 staves, one meter (`C`)**.
  A single true `C` is not a true-positive distribution, and the overlap claim
  in §4.1 is therefore *a lower bound on the overlap*, not a characterisation of
  it.
* ⚠️ **`C` is the cheapest shape on a music page to fake** — 21 of the 32 false
  header readings and 13 of the base branch's 16 bar-head ones spell it — and
  the one TRUE reading available here is also a `C`. That is an uncomfortable
  coincidence and it is not controlled for.
* ⚠️ **The pages are DOWNSCALED renders** committed for other investigations,
  not 600-dpi originals. Staff spacing is normalised to the canonical cell
  before the reader sees it, so the reader's operating point is right — the ink
  is not the ink a production run reads.
* ⚠️ **§3 is one page, one publisher, one movement start.** "The opening meter
  enters at 10-12 staff spaces" is a fact about a 3-flat key signature in a
  Breitkopf plate; a page with no key signature would place it nearer the front.
  It does not need to generalise for the conclusion to hold (4 spaces is blind
  HERE, on the only movement start in reach), but do not quote 10-12 as a
  constant.
* **No print was consulted for the three pairs** — truth is
  `report_boundary.TRUTH`, hand-read by an earlier session. The ONE print this
  session read is p.45, and it was read to check this probe's own premise.
* **No OMR-NED, no edit count, no file.** Nothing here says what any of these
  rules would cost in an exported MusicXML.
* ⚠️ `min_score` was **not** moved and is not proposed to move. §4 is a reason
  it *could not* be set to separate here, which is the opposite of a licence.

---

## 12. VERDICT — DON'T SHIP. And the substitution is refuted, not merely unbuilt.

* the **BARS** route stays dead (boundary §4c, untouched here);
* the **STAFF COUNT** route is not merely unfavourable but **incoherent** — the
  two counts come from two readers over two windows (§5);
* the **SCORE** route is refuted three ways: **reach ZERO** on the corpus (§1),
  **monotone in window width** so a cross-frame comparison is biased toward the
  opening by construction (§2), and **overlapping** on real ink even inside one
  frame, with the cautionary's own population the worst of the four (§4);
* the **SAME-FRAME** repair that would have fixed §2 is **blind** — an opening
  meter is 10-12 staff spaces into its bar and a 4-space window reads 0 of 16
  where a 14-space one reads 16 of 16 (§3);
* the **FILL-AN-ABSTENTION** route is reachable and, on its one instance, WRONG;
* what remains is what the cautionary session already found: **a floor on the
  cautionary's OWN cross-staff evidence** (R3/R4), fitted on three rows, and
  **a second document** — `beethoven-sym5-mvt4` bar 364 first, whose fixture
  already exists.

**The cheapest thing that would move any of this is still that second document.
The cheapest thing that would close §1 is §9, on Sean's machine.**

---

## Files

| | |
|---|---|
| `arbiter_reach.py` | reach of the substituted arbiter (exits **3** while DEAD) + the two-readers derivation, each with a positive control |
| `probe/score_frames.py` | four frames, four populations, ten real pages; premise checked with the SHIPPED vote |
| `probe/where_the_opening_sits.py` | the width at which an opening meter enters the window |
| `probe/overlap.py` | do the TRUE and FALSE score populations separate — derived, not counted |
| `local_arm.py` | the end-to-end arm for Sean's machine — **never run** |
| `mutation_battery.py` | 8 arms, byte snapshot, **restore VERIFIED**, in-flight sentinel |
| `out/*.json`, `out/*.log` | the tables above, machine-readable |
| `benchmarks/omr-meter-cautionary-2026-09/` | the contest session's deliverable, IMPORTED rather than restated |
