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
OMR-DED. The test firing says the FACT is available, not that anything uses it.

⚠️ **A PROCESS FINDING WORTH MORE THAN THE NUMBERS: the battery's first run
had 4 survivors and only ONE was a test gap.** The other three were controls
sitting at their CEILING on a page where the repair works — a control can only
be mutation-tested in a state where it FAILS. The arm now carries two positive
controls (`--blind-the-reader`, `--clip-like-a-cell`) and the battery judges
every arm on all three runs. Final: **17 arms, 17 RED, 0 survivors.**

Everything is on `claude/integration-2026-09-18` (**PR #57**, still open).
