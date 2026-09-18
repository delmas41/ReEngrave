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

Then [docs/handoff-2026-09-18-three-lanes-and-the-print.md](handoff-2026-09-18-three-lanes-and-the-print.md)
for the overnight batch.

---

## ⚠️ ONE AGENT WAS STILL RUNNING WHEN THE SESSION ENDED

`claude/vertical-runs-gather-2026-09` — building `Q.VERTICAL_RUN`: **one row per
candidate vertical run, accepted OR rejected, carrying PAGE PIXELS** so a run's
endpoints can meet `Q.STAFF_LINES`. **Default-OFF, producer only.** Check the
branch; it was told to commit and push incrementally.

**Why**: Sean asked whether the stages hold what is needed to tell one kind of
vertical line from another, and measured the answer is **no**, for two fixable
reasons — there is no quantity for *a vertical run* (only `Q.STEM`, the six
filters' survivors), and `Q.STEM` carries **no page coordinates** while
`Q.STAFF_LINES` is page px, so **the barline endpoint test cannot be computed at
all.** ⚠️ Its hard requirement: `Q.STEM` must not change, and flag-off must
reproduce **1,920 = 1,920** strokes on Litolff and **2,305 = 2,305** on
Breitkopf — `line_detection.py` is on the path every stem arm proves faithful
before reporting a delta.

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
