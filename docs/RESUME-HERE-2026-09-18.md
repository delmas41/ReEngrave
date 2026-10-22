# RESUME HERE — state at the end of 2026-09-18

One branch, **`claude/integration-2026-09-18`**, pushed, **85 commits ahead of
`origin/main`**, open as **PR #57**. Tree clean, nothing unpushed. Suite **4521
passed / 19 skipped / 0 failed**; `inventory`, `health`, `wiring`, `capture`,
`reach`, `brakes`, `trace --check`, `no_producer` all exit 0.

**Read these four, in this order. They are the session's product — the code is
secondary.**

1. [docs/breakthrough-2026-09-18-the-unit-of-enquiry.md](breakthrough-2026-09-18-the-unit-of-enquiry.md)
   — **the governing document.** Every decision is filed against an address
   whose last coordinate is an index into the detector's output list, so the
   stages are rigorous about a population the detector invented. ⚠️ Its §7
   records a **failed** falsification test (mine), and §6 the counter-argument
   (the ink is badly segmented too).
2. [docs/stage-charter-2026-09-18-what-each-stage-does.md](stage-charter-2026-09-18-what-each-stage-does.md)
   — what each stage does, Sean's own statement of intent verbatim, and the
   three places the build diverges from both.
3. [docs/diagnosis-2026-09-18-who-actually-decided-it.md](diagnosis-2026-09-18-who-actually-decided-it.md)
   — why *"we couldn't read it"* and *"a stage broke it"* are currently
   indistinguishable.
4. [docs/proposal-2026-09-18-boxing-is-a-decision.md](proposal-2026-09-18-boxing-is-a-decision.md)
   — boxing is a decision; **its §9 addendum is Sean's sharpest contribution**:
   length positively identifies every vertical mark whose length is
   ENUMERABLE and identifies a STEM not at all, so a stem must be identified by
   **ATTACHMENT**, never dimension — which indicts all six of `detect_stems`'
   filters as dimension bounds on a variable-length object.

**And the FORWARD PLAN those four imply, agreed with Sean at the end of the
session:** [docs/plan-2026-09-18-what-distinguishes-each-mark.md](plan-2026-09-18-what-distinguishes-each-mark.md)
— *for every family: what fact DISTINGUISHES it, in what FRAME, at what
STAGE, and can that decision ABSTAIN?* ⚠ Its §4 is the one exception to
*"it is not the later stages"* — Breitkopf's dominant loss is INFER's own
population with INFER default OFF, which is **a flag, not a rebuild**, and
must not be swept into the architecture work.

Then [docs/handoff-2026-09-18-three-lanes-and-the-print.md](handoff-2026-09-18-three-lanes-and-the-print.md)
for the overnight batch.

---

## ✅ THAT AGENT FINISHED AND IS MERGED — and its negative is a diagnosis

`claude/vertical-runs-gather-2026-09` — building `Q.VERTICAL_RUN`: **one row per
candidate vertical run, accepted OR rejected, carrying PAGE PIXELS** so a run's
endpoints can meet `Q.STAFF_LINES`. **Default-OFF, producer only.** Check the
branch; it was told to commit and push incrementally.

**RESULT**: `Q.VERTICAL_RUN` is merged, default-OFF, producer only. **The record
was carrying about a THIRD of the vertical lines the pipeline looked at** — 6,128
candidates against 1,920 strokes, with **64.7% refused by a dimension bound** and
leaving no row at all. Flag-off reproduces both records exactly (**1,920 = 1,920**,
**2,305 = 2,305**, 0 cells disagreeing). ⚠⚠ **Sean's barline test is now askable
and the answer is NO — 0 of 19 print-settled barlines fire at any tolerance while
6 of 58 adjudicated STEMS do.** The cause is the finding: the tall runs' end
offsets are **−4.00 / +4.00 staff spaces on both publishers — exactly the measure
cell's padding** — so **a barline taller than the cell has its ends clipped BY the
cell.** His test is **structurally UNAVAILABLE, not refuted**, and the fix is a
page-BAND reader (the `cv_hairpins` precedent), the ranked next work.
⚠⚠ **It also found TWO OF THE SIX FILTERS CANNOT FIRE** at the shipped defaults
(zero over 12,944 candidates) — so every document saying *"six filters"* was
wrong, including two written the same day; corrected in place. ⚠ **COST 0.96-1.11
MB/page, 1.6-2× the ink layer** — a real argument against flipping the default.
Findings: [benchmarks/omr-vertical-runs-2026-09/FINDINGS.md](../benchmarks/omr-vertical-runs-2026-09/FINDINGS.md).

**Why it existed**: Sean asked whether the stages hold what is needed to tell one kind of
vertical line from another, and measured the answer is **no**, for two fixable
reasons — there is no quantity for *a vertical run* (only `Q.STEM`, the six
filters' survivors), and `Q.STEM` carries **no page coordinates** while
`Q.STAFF_LINES` is page px, so **the barline endpoint test cannot be computed at
all.** ⚠️ Its hard requirement: `Q.STEM` must not change, and flag-off must
reproduce **1,920 = 1,920** strokes on Litolff and **2,305 = 2,305** on
Breitkopf — `line_detection.py` is on the path every stem arm proves faithful
before reporting a delta.

## ⚠⚠ ASK SEAN ON SUNDAY (his limit resets Sun 15:00) — he asked for this note

**The ORDER of the family sweep**, and he reframed it better than the plan's
own dependency framing: *"maybe not a pure order, but can the order be
INTENTIONAL? ... we will be able to read some things better than others and
have more certainty about some symbols over others, and therefore could lean
into what we know more to help us with what we know less."*

Current thoughts and the four questions to put to him are
[plan §9](plan-2026-09-18-what-distinguishes-each-mark.md#9--open-question--ask-sean-about-this-on-sunday-his-limit-resets-sun-1500).
Short version: **the ordering principle is CERTAINTY, not dependency** — a
pure order is impossible anyway (`meter <- meter` is a declared cycle), the
gradient is **already measured** (noteheads 0.999 engraved / 0.980 recall
scanned, against stems missing on 793 of 2,347 heads and the meter decided on
1 system of 7), and the repo has **instantiated his principle five times
without ever stating it**. ⚠ The qualifier that can make it backfire: lean on
what we know more **only where the anchor fails independently** of what it is
anchoring — measured favourable for noteheads→stems on Brahms p2, where
notehead recall is 0.980 while half the stems are missing. ⚠ **The sharpest
open thing: should noteheads anchor everything when the notehead fault is
PRECISION rather than recall?**

## ⚠️ DECISIONS WAITING FOR SEAN — none was taken

Four from the overnight batch, each with its counter-argument in
[the handoff](handoff-2026-09-18-three-lanes-and-the-print.md) §4: the
**beam-mate tier's default** (it lost **16-0** to the print on its first second
publisher — ⚠️ but its error looks like ATTRIBUTION, so the repair may be a fix
rather than a flip); **`OMR_STEM_STROKE`** (off only because 581-1,074 extra
strokes reach `detect_beams` unpriced); the **width cap** (its discards are
**33 of 33 real**, and the cap is still unpriced); and a **box-width floor**
(catches 39 of 46 non-noteheads at zero cost to real stems).

**Plus three one-line questions the lanes put to him**, and one new one from
tonight: **should an accidental's vertical stroke be in the stem-veto's domain
at all?** It fired on **24 accidentals, clefs and rests of 33** — the whole
thread had framed it against barlines.

## What tonight actually established

* **The stages are not the problem.** They abstain, correct each other and
  balance. The complexity is sound and **pointed at the wrong population.**
* **The two most basic questions never reach a stage**: *what is this* (the
  detector's word, `observe`d as fact) and *is there a stem* (six filters inside
  GATHER, survivors only).
* **2,377 places on one record where a stage claims the page is empty and the
  ink layer shows ink** — and `Q.INK`'s own `no_ink` fires **zero** times there,
  so every one is false about the ink. ⚠️ Sharpest instance is **ten lines apart
  in one gatherer and backwards**: `gather.py:1070` says `NO_INK` for a cell
  that HAD detections (997 firings) while `:1079` says the honest
  `NO_DETECTIONS` for a cell with none (3).
* **Where the loss falls is not recognition**: on Litolff **988 refused
  noteheads are `staff_not_identified` + `no_pitch`, both ZERO on Breitkopf.**
* ⚠️ **The ~40% "unexplained ink" figure is NOT missed music** — 72.4% of it is
  specks carrying 0.3% of the area; 43 pieces carry 84.9%.

## What is still owed

**26 crops** on the Breitkopf heads where the two stem mechanisms disagree (the
only non-correlated arbiter available), **31 crops** for the whole-note
contradiction, the **ATTRIBUTION repair** in `adjudicate_stem_direction` that
two lanes converged on independently, and an **engraved staged record** — the
funnel says where symbols are LOST and can never say whether the survivors are
RIGHT, because both records are scans.

⚠️ **Read every figure with its limits.** n is **2 publishers, 8 pages, one
adjudicator** throughout, and on the Litolff plate **~60% of noteheads cannot be
adjudicated by eye at all**, controls and sample alike. **No OMR-NED figure
anywhere, deliberately.**

---

## ✅ 2026-09-20 — THE RANKED NEXT WORK IS DONE, AND IT INVERTED A CLEAN NEGATIVE

**The page-BAND reader this note ranks first is built** (`tools/omr/
vertical_runs_page.py`, `benchmarks/omr-vertical-runs-page-2026-09/`), and
**Sean's barline test is no longer a negative.** Read off the whole page with
nothing else moved — same print-adjudicated population, same tolerance sweep,
same two forms of the rule — it fires on **11-13 of 19 barlines between 0.25
and 0.60 staff spaces and on ZERO of 63 stems**, where the cell frame read 0
and 0. **The window was the whole of it.**

⚠️ **THE DECISIVE COLUMN IS THE STEM ONE.** The barline half inherits the
predecessor's circularity (its sample was drawn FROM the `too TALL` bucket);
the stem half was sampled across all six buckets and its false-positive side
is EMPTY across four tolerances.

⚠️ **THE NARROW FORM IS STILL 0 OF 19**, same selection effect, so nothing
there speaks for a ONE-STAFF barline — and `omr-barline-height-2026-09` prices
that: **7 of 82** Litolff and **4 of 49** Breitkopf barlines cross every gap,
so the kind measured is ~8% of the barlines on the page. **The ranked next
work is a crop pass sampling from ACCEPTED and `too WIDE`, never again from
`too TALL`** — a print pass, not code.

⚠️ **NOTHING IS NAMED AND NOTHING READS IT.** No record row, no file moved, no
OMR-NED figure. The test firing says the FACT is available, not that anything uses it.

⚠️ **A PROCESS FINDING WORTH MORE THAN THE NUMBERS: the battery's first run
had 4 survivors and only ONE was a test gap.** The other three were controls
sitting at their CEILING on a page where the repair works — a control can only
be mutation-tested in a state where it FAILS. The arm now carries two positive
controls (`--blind-the-reader`, `--clip-like-a-cell`) and the battery judges
every arm on all three runs. Final: **17 arms, 17 RED, 0 survivors.**

Everything is on `claude/integration-2026-09-18` (**PR #57**, still open).

## ✅ 2026-09-20 (second lane) — STEM ATTRIBUTION: measured, and geometry cannot apply it

**The ranked first item of the three-lanes handoff §5 is taken as far as
geometry can take it, and it stops at the print.** `tools/` diff **EMPTY**;
no weights, no re-gather, both figures read off the committed shared records.
[benchmarks/omr-stem-attribution-2026-09/FINDINGS.md](../benchmarks/omr-stem-attribution-2026-09/FINDINGS.md).

⚠️ **The convention is now MEASURED and bimodal** — Litolff peaks 412 at t=0.0
and 450 at t=0.8 against 29 at the trough, Breitkopf 732 and 443 against 10;
**71.8% / 77.3%** of pairs within half a notehead height of an end.

⚠️⚠️ **The fault is real: 148 and 228 heads take a confident direction from a
stroke that does not end at them**, and the owner is already on the record in
**153 of 169 and 231 of 246** far pairs. Only 9 and 5 are claimed alone —
a READING gap no attribution rule can reach.

⚠️⚠️ **AND NO CONSTANT-FREE RULE SEPARATES A CHORD FROM A PASSING STROKE.**
Three forms priced before any was written: strict-minimum takes the faults and
**destroys chords** (113/115, 32/36), near-half does neither well,
chord-chain sits between. The discriminating gap has **no empty interval on
either plate.** ⚠️ And the cost column may BE the fault: `chord_interior`
means *a mate above AND below*, which three unrelated heads crossed by one
stroke satisfy exactly as a chord does.

**So: 79 full-width strips, pre-registered and committed BEFORE any was
rendered, two strata sampled equally, ids opaque so the pass can be blind.**
⚠️ **What is owed is a human with the plate.** If the strata adjudicate
DIFFERENTLY the repair is rule A plus a chord rescue; if they adjudicate ALIKE
the box test is not seeing what we think and the repair is upstream, in the
notehead boxes.

⚠️ Two frame faults in this lane's own instrument, both caught by a control
and both recorded: the frame control refused 38 of 40 (right to fire, wrong
about the cause — it was asked of a one-bar strip instead of the page), and
every mark then landed outside its bar because a `Q.GLYPH_BOX` value is
CANONICAL-CELL while a crop is placed in PAGE pixels. Battery **17 arms, 17
RED, 0 survivors.**

## ✅ 2026-09-20 (third lane) — "n = 2 publishers" WAS A PROPERTY OF THE CATALOG

Opened to check one passing line of the three-lanes handoff §5.4. **True, and
18x bigger than the three plates it names: 54 editions were on disk with a
complete provenance sidecar each, and none of them in the tracked catalog.**
Entries 1,980 -> 2,034; editions 235 -> 289; **29 publishers**.
[benchmarks/omr-catalog-gap-2026-09/FINDINGS.md](../benchmarks/omr-catalog-gap-2026-09/FINDINGS.md).

| work | catalog reported | reports now |
|---|---|---|
| **Beethoven 5** | Litolff x2 | **Litolff, Breitkopf 1862, Eulenburg 1938** |
| **Brahms 1** | Breitkopf x2 | **Breitkopf, Simrock 1877** |

⚠️⚠️ So **"a third publisher for the DENOMINATOR" (ranked 4th) stops being
blocked on acquisition** — a third Beethoven 5 plate and a second Brahms 1
plate have been on this machine the whole time. ⚠️ It retroactively changes NO
measurement; those results are correct about the plates they ran on.
⚠️ And it says **nothing about LEGIBILITY** — `image_type: "Normal Scan"` is
IMSLP's label, not a measurement, nothing has been gathered on any of the 54,
and none has a hand-verified window row.

✅ **AND THE GUARD IS BUILT**: `score_library.unindexed()`, reported by
`ingest verify`, which now EXITS NON-ZERO on it. The control is the historical
case and **the delta IS the repair** — 54 against the pre-rebuild catalog, 0
against the rebuilt one.

⚠️ **A PROCESS GOTCHA, PAID FOR HERE:** backticks inside a `git commit -m
"..."` string are COMMAND SUBSTITUTION under zsh. Commit `402c4d18`'s body
reads *"the catalog is behind -- , additive"* where it should read *"-- run
`ingest catalog`, additive"*; the two words were executed and swallowed.
**Not amended, because the branch is pushed and force-pushing a shared branch
is the larger risk** — recorded here instead. Use a heredoc for any message
containing backticks.

## ✅ 2026-09-20 (fourth lane) — THE SUITE FIGURE ABOVE IS SCOPED, AND THE DASHBOARD WAS RED

⚠️⚠️ **THIS NOTE'S OWN "4521 passed / 19 skipped / 0 failed" IS TRUE OF
`pytest tools/omr`, NOT OF `pytest tools`.** The whole tree gave **15 failed /
20 errors**, all in `tools/dashboard/tests/test_registry_report.py`, and the
CONTROL says they were pre-existing: an identical 15/20 at `a01f3c61`, the
pre-session tip. **Read the OUTPUT, not the STATUS** — the task harness
reported "exit code 0" while pytest returned 1.

**The cause was a refusal working.** `metric-registry.json` went to schema
**0.7.0** while `registry_report.py` understood only **0.5.0**, so
`gate_schema_version` refused to render — loudly, by design — and had been red
since v0.6.0 landed.

✅ **CONFORMED, by handling the fields rather than widening the tuple.** The
two the contract says a consumer may never drop are now rendered:
`scored_at_detail_level` (19 of 19 rows) and `ceiling.measured_under` with its
`stop_condition` (21 of 21 ceilings, **2 marked flag-conditional**, which
independently reproduces the registry's own *"the two ESTIMATOR-based floors
ARE"*). 0.6.0 is deliberately NOT admitted — it is `superseded` with a reason.

⚠️⚠️ **AND THE FIRST CUT DROPPED BOTH FROM THE MARKDOWN**: the handled set was
widened and the HTML verified row by row while `render_md` carried neither —
the `ceiling.edition` failure one consumer surface further along. **A field is
handled when EVERY surface shows it, not when one does.** Caught by counting
the md output, not by review.

**Whole tree now: 4,621 passed / 19 skipped / 0 failed.**

⚠️ **AND A GOTCHA IN THE VERIFICATION ITSELF**: `pytest ... | tail -3 > f;
echo $?` reports **`tail`'s** status, not pytest's. The result above rests on
the summary line (pytest prints `N failed` whenever there are failures), not
on that exit code. Use `${pipestatus[1]}` in zsh.

## ⚠️⚠️ 2026-09-20 — THE STEM-ATTRIBUTION LANE IS WITHDRAWN (refuted by the print)

The second lane above measured *"148 and 228 heads take a direction from a
stroke that is not theirs"*. **Do not quote it.** Its chord test could not see
a two-note chord (it required a companion above AND below), so octave pairs
were filed as faults — **64% / 95% of the flagged group**. Corrected to Sean's
rule the population falls to **51 and 14**, and three of the residual cases,
cropped and shown to him, are *"clean notes with basic stems"*. The flagged
strokes are **systematically longer** than ordinary ones (5.72 vs 4.12; 4.43 vs
3.46 staff spaces), so **the stem is measured too long and the repair is
upstream in stroke extent, not in `adjudicate_stem_direction`.**
[FINDINGS](../benchmarks/omr-stem-attribution-2026-09/FINDINGS.md) §0.
