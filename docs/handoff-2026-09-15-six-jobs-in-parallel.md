# Six jobs in parallel, five landed, and what the TREE said that the REPORTS did not

**2026-09-15.** A managing session dispatched six agents down
[docs/handoff-2026-09-11-phase-2-opened.md](handoff-2026-09-11-phase-2-opened.md)
§8's ranked list, verified each result against the tree, and merged five.

⚠️⚠️ **READ §7 FIRST IF YOU ARE SHORT OF TIME.** The single most transferable
result of the day is not any of the five repairs: it is that **five of six
agent reports contained a claim the tree contradicted**, every one caught by a
one-line check and none by reading the report. That is this repo's own *the
tree outranks the ledger* rule, and it now has a measured hit rate.

---

## 1. WHAT LANDED

| branch | result | touches the FILE? |
|---|---|---|
| `claude/slot-index-e2e` | 75 fragments → **37 parts, 12 grafts → 0** | **yes** |
| `claude/note-where-silence-opened` | **22 notes deleted**, 25/25 adjudicated vs the print | **yes** |
| `claude/measure-numbered-by-the-document` | 90 measures renumbered, music provably unmoved | numbers only |
| `claude/arc-grammar-s4-s6` | S4 **refuted at full width**, S6 recorded not gated | no |
| `claude/no-producer-check` | 9,143 params → **2 findings**, a third instance found | no |

A sixth (`OMR_METER_CARRY` re-priced on Breitkopf Brahms 1) was still running
when this was written. **Its result is NOT in this document.**

⚠️ **Only two of the five change the exported music**, and they are the two with
hand-adjudicated crops behind them. That was not a coincidence of scheduling —
it is what the briefs demanded.

---

## 2. ⚠️⚠️ THE ONE THAT DELETES NOTES, AND WHY IT IS SAFE

Sean's observation 3, the last of his seven still open: *"in bars where it
should be just whole note rest in two four. It's showing an actual quarter
note, not a quarter note rest."*

⚠️⚠️ **THE BRIEF'S POPULATION WAS 26 BARS AND 18 OF THEM WERE THE OPPOSITE
FAULT.** All 26 were cropped and hand-adjudicated against the print
(`adjudicated-26.json`, committed with the record's md5):

| what the page actually prints | n |
|---|--:|
| a **whole rest** called a notehead — Sean's fault exactly | **5** |
| a **real note** in a bar whose other music was never read | **18** |
| neither — the box sits on a slur apex or a stem/staff-line junction | **3** |

**A repair that emptied all 26 bars would have deleted 18 real notes.** Those 18
are a *missing-note* problem wearing an *invented-note* costume — the same
detection shortfall the arc work measured from the other side (*108 of 550
refused arcs sit in bars with no notehead at all*). **A reader sizing this job
off the handoff's "26" would have sized it five times too big.**

**What settled it was not counting — it was a STRIP.** `probe/strip.py` renders
one printed staff end to end labelled with what our file says. On the Flauti's
tacet run the page prints one identical blob per bar and our file reads
`R · R · R · D5/quarter · R · R · D5/quarter`. The record then closes it without
leaving the record: two of those identical blobs are classed `restWhole`
(h 0.67 spaces, aspect 2.33) and `noteheadBlackInSpace` (0.79, 2.22).
**Same ink, same slot, two class names — a detector classification error
UPSTREAM of GATHER**, where `gather_glyph_families` routes by class, so it can
never become a `Q.REST` row. ⚠️ One case the contact sheet got wrong and the
strip got right: **a crop shows you the ink; only its neighbours tell you what
the engraver was doing.**

**What shipped:** `Q.NOTEHEAD_IS_A_WHOLE_REST` (ADJUDICATE, `Kind.GLYPH`),
consumed by `export._place_notes` as a **REFUSAL TO WRITE A NOTE** — it never
manufactures a rest; the bar falls to the existing padded measure rest.
**Two witnesses, neither admissible alone**: shape alone fires 148 times,
position alone 310 and on real music, **together 25**.

**The safety evidence, and the reason it is in the tree**
(`adjudicated-25-fires.json`):

| | |
|---|--:|
| cells the rule fires on | **25** |
| hand verdict `whole_rest` | **25** |
| hand verdict `notehead` — **a real note deleted** | **0** |
| fires on a row the 26 adjudicated as a REAL NOTE | **0** |
| fires OUTSIDE Sean's observed population | **20** |

⚠️⚠️ **THAT ARTEFACT EXISTED ONLY IN A TRANSCRIPT UNTIL THE MANAGER ASKED FOR
IT.** The first report said *"all 25 fires were cropped, 25 of 25 are whole
rests"* and committed only the **26**-bar file. The two sets overlap in 5 rows
and are not the same population — **the rule's safety rests on the 25, and an
18-of-26 error rate in the first population is exactly what makes a hand
adjudication of the second something that has to be on disk.**

⚠️ **20 of the 25 sit outside the lone-quarter-in-2/4 window Sean was looking
through**, so that filter would have found a fifth of the fault. And the
detector's classes on the 25 are **22 black noteheads and 3 whole** — this is
not a hollow-vs-filled confusion; the class it lands on is close to arbitrary.

**Measured:** notes **1618 → 1596, 22 removed, 0 added**; 9 bars take a padded
measure rest, **7 already held one** (the file was printing a measure rest *and*
a quarter note in one silent bar), 6 phantoms stood among real music. 25 − 3 =
22, the three already unwritten for `no_pitch` ×2 and `duration_narrowed` ×1,
matching the arm's bucket movement to the unit. Ties 91 → 90 — one arc bound to
a phantom, **an unadjudicated cost**. ⚠️ **No OMR-NED figure is claimed**: the
metric rewards under-prediction and would have paid for these deletions either
way, **which is why the evidence is crops.**

⚠️ **Two of the six cuts sit on a plateau one step wide or less**, derived from
this document's own 395 whole rests. **n = 1 document, 1 publisher, 4 pages.**

---

## 3. THE PART JOIN — Sean's §5.2 decision has CHANGED SHAPE

The `adjudicate_slot_index` name rule landed 2026-09-14 measured only against
*recorded reader output* in a container with no weights. The end-to-end arm had
never run.

**It reproduces the probe EXACTLY — in every cell, not just the total:**
50 placed / 50 correct / **0 wrong** / 25 abstained, cross-tab identical
(wrong→ok 3, wrong→abstain 9, ok→abstain 16, ok→ok 47, **ok→wrong 0**).
⚠️ The control that makes that a result rather than a tautology: the arms are
compared per staff **before any count is read** and differ on **28 of 75**.

**Reach, checked first:** 50 margin labels over 75 staff-systems
(12/7/7/7/4/6/7), and — the thing the probe could not check — **our
segmentation agrees with the print on 7 systems of 7**, which matters because
`_pick_reference` takes the widest system *we read*, not the widest the page
prints.

| | before | after |
|---|--:|--:|
| exported `<part>`s | **75 fragments** | **37** |
| join | ordinal | **slot** |
| grafts | **12** | **0** |
| measures / notes | 1183 / 2473 | identical |

⚠️⚠️ **THE DECISION IS NO LONGER *12 parts with a silent graft* vs *75 loud
fragments*. It is *37 parts with ZERO grafts*,** and the 25 extras are exactly
the staves the page never labelled (this edition stops labelling strings on
continuation systems). **The flip is still Sean's.**

**The phase-2 prediction is confirmed to the measure, from a different
direction**: the file reads Flute/Clarinet/Bassoon/Horn **111**,
Oboe/Trumpet **93**, Timpani **78** — exactly the 111/93/78 derived from the
measure math alone.

⚠️ **TWO THINGS NOW REACH A REAL FILE AND ARE NOT REPAIRED:** the 25 stranded
fragments are written **first**, so part order is no longer the printed
top-to-bottom order; and **slot 11 exports as `Bass voice`** — the lexicon
defect this file documents at length, **previously inert, now a joined part's
`<part-name>` on an orchestral score.**

---

## 4. MEASURE NUMBERING — and a witness that was not what it seemed

A part whose staff is suppressed gets no measures for those bars, so
`<measure number="82">` named a different instant in different parts.
`system_bar_starts` numbers by the DOCUMENT's bar sequence: **90 of 1,183
measures renumbered, every one by +18** — the width of the 8-stave system —
3 parts affected, systems carrying two number ranges **2 of 7 → 0 of 7**.

**The music is provably unmoved**: normalise the numbers away and the two
exports are **byte-identical**; ordinal-for-ordinal, 1,183 measures identical,
0 different. **It is a relabelling, not a reordering.** The control can fail:
five arms including *"the same file twice"*, which exits 1 with *"no measure
number moved: the instrument is DEAD"*.

⚠️⚠️ **VEROVIO IS SILENT ON THE WHOLE FILE IN BOTH ARMS — 0
`Mismatching measure number` lines before AND after.** The recorded warning is
**not a property of the file; it is a property of an OPERATION on it.** Verovio
lays a full score out along each part's own measure *order* and never
reconciles two parts' numbers; only `build_sidebyside.py`'s question — *take
one printed system's bars BY NUMBER from every part* — can see it. On the
before file that raises **30** errors; after, one window serves all 11 parts
and it is silent. ⚠️⚠️ **And the simplified single-window route on the BEFORE
file raises nothing and silently returns twelve bars of the WRONG SYSTEM** — a
reader who tidied the workaround would have got a clean render of the wrong
music.

⚠️⚠️ **THE REFUTATION THAT OUTRANKS THE FIX: `tools/omr/export.py` ALREADY DOES
THIS, and says so at `export.py:3871`** — *"A slot need not appear in every
system (a suppressed tacet staff), so each staff takes ITS OWN system's measure
start rather than the n-th one."* **The staged exporter re-converged on a
position the legacy one had already paid for** — the `_rest_ruling` /
`_pair_dots_to_targets` shape again. Nothing in the legacy path needed repair
and none was made; the rule is RESTATED with cross-references (the `_meter_dict`
precedent) rather than duplicated silently.

⚠️ **A SELF-INFLICTED CORRECTION TO THIS FILE'S OWN OPERATIONAL RECORD.**
CLAUDE.md files *"a mutation battery `git checkout`s the files it mutates"* as a
**sibling-session** collision. **It is also SELF-destructive**: run over an
uncommitted change, arm 1's cleanup restored `export.py` from the index and the
change under test vanished, noticed only because every later arm reported
`anchor occurs 0 times`. `mutate.py` now **refuses to start on a dirty tree,
with no `--force`.**

⚠️ **NOT established:** that bar 82 is *printed* bar 82. This says the numbers
are CONSISTENT ACROSS PARTS. And the join is the bigger defect — **a correct
join gives 111/93/78/31, so the eight parts reading 111 read 111 BECAUSE of the
graft.**

---

## 5. THE ARC RULES — S4 refuted at FULL WIDTH, and a joint result

Sean, on being shown the first (narrow) refutation: ***"don't give up — adjust
the rules to be broader."*** He is the author of S1-S6 and they are a statement
about how music is ENGRAVED; **a narrow operationalisation failing is evidence
about the operationalisation, not about the convention.** The agent was sent
back with its context intact.

⚠️⚠️ **THE FIRST PASS MEASURED A PRECONDITION AND THREW IT AWAY.** Its own
funnel read 420 arcs with a stemmed head → **206 on the stem's side** → 143
whose endpoint lands ON stem ink. **It used "on the stem's side" as a FILTER on
the way to the narrow test and never scored it** — although a tie hugging the
notehead against a slur running stem-tip to stem-tip is a cleaner reading of
Sean's sentence than distance-along is.

**Widened — contact dropped, projected onto the head→stem-tip axis, scored
ONE-SIDED as Sean stated it (far ⇒ slur, near ⇒ abstain, S3 being explicitly
ambiguous) — S4 is REFUTED:**

- reach **143 → 420 of 779**, with a declared 359-arc abstention;
- **SIDE is flat: −0.001 (low confidence) / −0.030 (high)**;
- the distance sweep **never clears p = 0.079**;
- conditioned on either other witness, S4's lift is **negative in all four strata**;
- the refutation is not the probe's: its side determination disagrees with a
  per-endpoint one on **21 of 763 endpoints (2.75%)**.

⚠️ **It is the WIDE test that fails, which is the strong negative.** The narrow
one's non-monotonic sweep (max lift +0.114 at n=30, bracketed by +0.048/+0.047)
was a **POWER** problem and was correctly distrusted.

⚠️⚠️ **S4'S AVAILABILITY GRADIENT INVERTS THE RECORDED ONE.** This file records
that a second reader falls silent where the first is worst (grammar available at
median confidence 0.563 vs 0.408). **S4's arcs sit at 0.4196 against 0.5409 for
those it cannot reach** — a confident long slur is drawn clear of the stem tips,
so S4 speaks *preferentially about the weakest readings*. **That is a harder
shape than an arbiter that merely goes quiet, and it is new.**

**S6 survives every relaxation and the widenings buy almost nothing** —
428 → 463 candidate pairs (+8%, not a doubling), agreement unmoved at 0.62-0.66,
tight band 73 → 77 at **0.740**. That is *robustness*, not a bigger result. The
only relaxation that helps is same-`arc_owner` (0.651). ⚠️ The absolute-position
form is **already refuted** — *"the arc nearer the noteheads is the tie"* scores
**0.517** — so S6's power is in the PAIRWISE comparison and a widening must keep
the pair.

⚠️⚠️ **THE JOINT RESULT IS THE LARGEST FINDING OF EITHER PASS, AND IT IS ABOUT A
MECHANISM THIS REPO HAS ALREADY REFUSED.** **S2/S5 alone scores BELOW its own
majority baseline (0.5043 vs 0.5275 over 345).** S6 alone 0.6139 vs 0.4158.
They concur on only 40 of 83 — and **where they concur: 0.750**, against 0.602
and 0.639 for either alone on those same 83. A 20,000-draw permutation null
(median 0.625, p95 0.711) puts that at **p = 0.0104**, so it is not the
selection effect. **`OMR_ARC_RECLASS` is marginally uninformative alone and
jointly informative. The refusal STANDS** — it was refused for what it COSTS,
and this measures what it is WORTH; nothing here argues for turning it on.

**Neither rule is promoted.** S6 would flip ~30 arcs a page on 73 pairs of one
low-res bitonal scan, roughly half in the tie→slur direction measured at +149
scan edits, and **get 19 of 73 wrong against a detector that is not truth.**
⚠️ **The price to settle S6 is SEVENTY CROPS, not more arcs** — small enough for
a human eye, and this session did not have the print.

⚠️ **A new member of the *control that computes the wrong thing* family**: the
first combined table was **vacuous by construction** — a one-sided rule's
"agreement" *is* the subset's base rate, so every cell read
`agreement == base_rate` to four decimals. **The diagnostic is "is this number
suspiciously EXACTLY some other number on the page", not "is this number
believable".**

---

## 6. THE NO-PRODUCER CHECK — and a third instance

The fault — a parameter threaded end to end that nothing supplies — had been
found **twice in two days, by accident both times** (`pdf_path`, which cost 75
staves their margin labels on *every staged run this repo has ever made*; and
`roster`). This derives it.

| | count | |
|---|--:|---|
| **D0** | **9,143** | parameters declared |
| D1 | 324 | ...defaulting to `None` |
| D2 | 148 | ...touched by a forwarding edge |
| D3 | 39 | ...with no producer at the fixpoint |
| D4 | 9 | ...as CHAINS crossing ≥ 2 layers |
| **D5** | **2** | ...**one of whose layers ABSTAINS when absent** |

⚠️ **The naive check reports the 323 of D1** — the *reports 200 things, gets
ignored, gets deleted* outcome `export_coverage`'s own docstring warns about.
⚠️ **D2 is SYMMETRIC and that is load-bearing**: `run_staged(roster)` is the
HEAD of its chain, so a target-only test reports every chain **without the layer
the repair lives in**. ⚠️ **D4 — the CHAIN is the reporting unit**, because
either end alone is an ordinary optional argument. ⚠️ **D5 is the
discriminator, 9 → 2**; `p = p or DEFAULT` is not a guard.

**Both known instances are caught with no hint**, and instance 1 is caught on
the tree where it was live (`3a725f07^1`: 3 findings) and **gone on the tree
where it was fixed** (2) — the delta IS the repair, not a threshold move.

⚠️⚠️ **A THIRD INSTANCE, FOUND BY THE CHECK — `dossier`.** Same four functions,
recorded nowhere. `grep -rn dossier tools/omr/staged/__main__.py` returns
**nothing**, while `tools.omr.transcribe` has had `--dossier` since the dossier
layer landed, so `Q.DOSSIER_FACT` abstains on **every staged run** beside
`Q.ROSTER_ENTRY`. **The staged pipeline can currently receive NEITHER a roster
NOR a dossier.** ⚠️ Not a claim it should be seeded — the scan benchmark runs
dossier-free BY PROTOCOL — but *no route exists*, which is a different fact from
a deliberate default and is currently indistinguishable from one.

⚠️⚠️ **WIDENING THE SCAN SILENCED IT, 2 FINDINGS → 0.** `asyncio.gather(*tasks)`
in `backend/` matched `staged.gather` by name and its splat marked every
parameter supplied. **The failure direction was SILENCE — the check reported a
clean tree, which is exactly what a working check reports.** Repaired; every
remaining imprecision also runs toward silence, so **the findings can be
trusted and the silence cannot.**

⚠️ **`pdf_path` was invisible to `inventory --check` AND `gather_coverage`**,
because `gather_margin_labels` *was* reading its input and reporting honestly.
**Read-by-nothing and supplied-by-nothing are different questions.**

⚠️ **A DEFECT IN IT, FOUND AT MERGE TIME AND NOT REPAIRED:** `--check` exits
**1** while reporting both findings as `RECORDED`, although its own contract
says recorded entries exist so the gate fires on a *fourth* instance. **As
written it can never pass, so it cannot be used as a CI gate.** Nothing wires it
in yet.

---

## 7. ⚠️⚠️ THE PATTERN OF THE DAY — FIVE OF SIX REPORTS CONTAINED A CLAIM THE TREE CONTRADICTED

**Every one was caught by a one-line check. None was caught by reading the
report.** This is *the tree outranks the ledger* with a hit rate attached.

| # | the report said | the tree said |
|--:|---|---|
| 1 | committed on `claude/work-priorities-ee5b1c` (the MANAGER's branch) | on its own worktree branch, **and on no remote at all** |
| 2 | (same, a second agent) | same |
| 3 | *"all 25 fires were cropped, 25 of 25 whole rests"* | that artefact **was not committed**; only the 26-bar one was |
| 4 | the second pass complete | **STAGED, NOT COMMITTED** — `HEAD` was still the first pass |
| 5 | the arm reports 10 grafts | two prior measurements say **12**; its own classifier was wrong |
| 6 | *"only the A/B remains"* | the A/B had been launched against **uncommitted** code |

⚠️ **THE TWO THAT MATTER MOST ARE 3 AND 4.** (3) is the safety evidence for a
change that DELETES MUSIC existing only in a transcript. (4) is an entire
measurement pass one `git checkout` from annihilation — which is precisely the
hazard that agent's *own* mutation battery had bitten it with hours earlier.

⚠️ **A stale artefact is the quiet member of the family.** `out/slot-arm-e2e.txt`
(pre-fix, `GRAFTS: 10`) sat in the same directory as `out/part-join-arm.txt`
(post-fix, 12) **under the headline arm's own name**, so the next reader hits
the wrong number first. The arithmetic identifies the stale one — the two rows
absent from it are exactly the two the broken classifier mis-filed, and
10 + 2 = 12, 6 − 2 = 4. **It was STAMPED, not deleted**: a superseded
measurement with its correction beside it is worth more than a gap.

⚠️ **And the manager's own instruments failed the same way twice**: a background
suite invoked with `timeout` (**which macOS does not have**) exited **0** having
run nothing, and a `| tail` swallowed a real failure's exit code. **Reading the
OUTPUT rather than the STATUS is what caught both** — the `&&`-chain lesson,
arriving at the manager.

---

## 8. THE MERGE

All five merged clean into `integrate-2026-09-15`, `tools/omr/staged/export.py`
**auto-merging across the two fenced lanes** — the measure-number emission
(~line 1603) and the notehead refusal in `_place_notes` (~line 474) never
touched the same hunks. **Lane discipline set at BRIEF time paid at MERGE
time.**

⚠️ **The merged tree is the one thing no agent ever ran**, and this repo has a
recorded merge-only failure neither branch could produce. Derived checks on the
merged tree: `health --check`, `inventory --check`, `export_coverage --all` and
`accuracy_record --check` exit non-zero — **and exit non-zero IDENTICALLY on
`origin/main`**, so they are pre-existing. `gather_coverage` exits 0.
⚠️ **The control was run before any conclusion was drawn**: *"checks fail after a
merge"* and *"checks were already failing"* look identical in a terminal.

---

## 9. THE LANE MAP — how four agents shared one hot file

`tools/omr/staged/export.py` was reachable by three of the four concurrent jobs.
Lanes were fenced **by function name, before dispatch**, after grepping the
file:

| agent | owned | forbidden |
|---|---|---|
| slot_arm e2e | `identity.py`, `part_partition`, **the long gather + Surya server** | export.py |
| note-where-silence | the rest/empty-bar path, `_place_notes` | numbering, arcs |
| measure numbering | the `<measure number=>` emission only | `_place_notes`, `_place_arcs`, `_pair_arcs`, padding |
| S4/S6 arcs | `adjudicate_arc_kind` in `ownership.py` | **all** of export.py, both exporters |

⚠️ **The arc agent was deliberately pushed OUT of the exporter.** The obvious
home for tie-vs-slur geometry is `_pair_arcs` — which was another agent's file
*and* the wrong stage. `adjudicate_arc_kind` already records the position
grammar without acting on it. **The collision fix and the architectural fix were
the same move.**

⚠️ **Only one agent was permitted a long gather**; the others were pointed at
committed records. All four were told never to blanket-kill the shared
`llama-server`, which has already cost a sibling session a multi-hour
transcription. **Nothing was killed and nothing collided.**

---

## 10. WHAT IS WAITING FOR SEAN

1. **`OMR_METER_CARRY`** — the flip is his; the Breitkopf cost arm was still
   running when this was written.
2. **The part join** — now *37 parts with the graft gone*, not *75 fragments*.
3. **S6 — seventy crops.** The only thing that can settle it.
4. **`Bass voice` at slot 11** now reaches a real file's `<part-name>`.
5. **Part order** is no longer printed top-to-bottom.

## 11. THE STANDING GAP THREE JOBS FOUND INDEPENDENTLY

**There is no Breitkopf Brahms 1 staged record on this machine.** The arc
thread, the note-deletion thread and the meter thread each hit it separately and
each stopped at the same missing artefact; `library/_shared-records/` holds only
the Beethoven one. **Making that record once and sharing it is probably worth
more than the next feature**, because it is what stands between four `n = 1`
results and knowing whether any of them generalise.

## 12. WHAT IS NOT ESTABLISHED, ACROSS ALL OF IT

**n = 1 document, 1 publisher, 4 pages of ~16**, on Litolff `984073` — the
*low-res bitonal* end of the corpus this file already calls pessimistic. No
OMR-NED figure is claimed for any of the five. Accuracy is established **only**
where crops were adjudicated: the 25 fires and the 26 bars. Everything else is
an agreement rate between two readings of the same ink.
