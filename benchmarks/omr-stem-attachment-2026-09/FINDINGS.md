# The attachment convention: REFUSED as a tier, and the marginal reach is 371 / 483

`OMR_*`: **nothing shipped.** `git diff origin/main -- tools/ backend/ CLAUDE.md`
on the source branch is **empty** — checked at integration, not claimed.

⚠️ **PROVENANCE OF THIS FILE.** The measuring session was a subagent and the
harness refused to let it write a findings file, so it put the synthesis in the
message of commit `708d6c63`. This file is that message, transposed at
integration by the managing session, plus two things the manager verified or
reconciled independently (marked **[mgr]**). **The commit message is the
primary source and this file is a transposition of it** — which is worth saying
out loud, because this repo's own rule is that *a commit message is a ledger and
the tree outranks a ledger*, and a benchmark directory with no `FINDINGS.md` is
where the next reader looks first and finds nothing.

---

## CONVENTION ASSUMED / WHAT WOULD FALSIFY IT / NOT CONFIRMED WITH SEAN

The unattended clause of Sean's 2026-09-18 standing instruction
(`docs/ask-first-conventions.md`).

**ASSUMED**: `docs/engraving-conventions.md` `[C9 + L10]` — *a stem attaches on
the RIGHT going UP, or on the LEFT going DOWN; right-and-down does not exist.*
A human reads it by looking at which side the vertical line leaves the
notehead. It was not assumed-and-built: `[C11]` (a beam joins stem TIPS) and
`[C10]` (the position convention, already refuted as a reader) were consulted
first, and this branch never quotes one's figure for the other.

**FALSIFIED BY**: agreement falling toward the 0.506 baseline, or a plate with
up-stems on the left. ⚠️ **NEITHER TEST SETTLED THIS — the convention SURVIVES
both, everywhere measured.** What is refused is the convention **AS A TIER**,
which is a different claim and must not be quoted as a refutation of it.

**NOT CONFIRMED WITH SEAN**: nothing here was put to him. Three questions for
him are at the foot of this file.

---

## 1. MARGINAL REACH — the number the job was dispatched for

Both shared records are **PRE-tier** (`no_stem` 793 Litolff / 1,529 Breitkopf;
no `beam_mate` verdict anywhere), so the published 472 / 653 still contain the
heads the shipped beam-mate tier now serves.

| | gross (published) | overlap | **MARGINAL** | gated [2.0, 8.0] |
|---|--:|--:|--:|--:|
| Litolff | 472 | 101 | **371** | 281 |
| Breitkopf | 653 | 170 | **483** | 420 |
| **pooled** | **1,125** | **271** | **854** | **701** |

⚠️ `[C9 + L10]` stated the pooled reach as *"1,125 heads that currently
abstain"*, which inherits the double count: **the registry overstated the
remaining job by 271 heads (24%)**. Corrected in place at integration.

⚠️ The two mechanisms are **POSITIVELY CORRELATED in availability, not
complementary** — the convention speaks for 66.4% / 58.6% of the beam-mate
population against 58.7% / 41.9% of the rest. So they are strong in the same
places, which is the opposite of what a tier wants.

⚠️ **[mgr] The two committed Breitkopf figures differ by six and that is
self-explaining, not drift**: `out/breitkopf-beammate.json` reads
`reach: 296` and `out/breitkopf-marginal.json` reads `beam_mate_reach: 290`.
The difference is exactly the **six whole notes** §7(a) reports the tier
borrowing a direction for. Reconciled at integration rather than left as an
inconsistency a later reader would have to chase.

**The replay is the control**: `beam_mate_set.py` reproduces the shipped tier's
published reach of **152** and `no_stem` **793 → 641 exactly** before any
marginal figure is read. ⚠️ `stem_arm.py`, the full re-adjudication, **never
completed a pass** (killed at 26 min, consistent with the 40-min report in the
2026-09-10 handoff), so the fire set rests on that replay.

## 2. THE STAGE — the ground that decides it, and §4a of the handoff does not mention it

The convention is a reading of **PIXELS**. `Evidence` (`adjudicate.py:255`)
exposes `rows()` and `refusals()` and nothing else, and **no adjudicator in the
tree imports cv2, numpy, fitz or PIL** — ⚠️ **[mgr] verified independently at
integration: the grep over `tools/omr/staged/adjudicators/` and
`adjudicate.py` is empty, while `gather.py` carries four such imports.** That
contrast is what makes this a stage argument rather than a style preference.

So it cannot be a tier until a GATHER producer files it; a GATHER change is
exactly what `readjudicate` is **structurally blind** to, and pricing needs
**two full re-gathers**. `Q.INK` does not substitute — the ink is FUSED, and a
fused component's bounding box cannot say which **SIDE** a run is on, which is
the convention's whole discriminating power. `Q.STEM.detail["image"]` is the
*string* `'no_staff'`: the record names which raster a reader used and carries
no pixels.

**§4a is right that the reading works and wrong that consuming it is cheap.**

## 3. THE POPULATION — 95.9% / 98.2% is measured on the easy half

Those figures are agreement with stems a reader **already decided**, i.e. the
half that was legible enough to read once. The registry NAMES this; this branch
QUANTIFIES it. Runs over `STEM_MAX_HEIGHT_LINES = 8.0` (imported, not restated;
its own comment says a longer run *"is a barline"*): Litolff **4.6% → 16.9%
(3.7×)**, Breitkopf **0.1% → 4.7% (35.5×)** — independently reproducing
`[C13]`'s own 3.7× from a different instrument. Agreement by arm length is
**U-SHAPED, worst at both ends**. Re-weighted onto the target's arm mix both
publishers land at **0.929 / 0.931**.

## 4. ⚠️⚠️ THE DECIDING MEASUREMENT, AND IT REFUTES THIS SESSION'S OWN ESTIMATE

Where the convention and the shipped tier **both** speak, on the population the
convention is FOR — the first comparison of these two mechanisms ever made:

| | heads | agree |
|---|--:|--:|
| Litolff | 101 | **97.0%** |
| Breitkopf | 170 | **84.7%** |

⚠️⚠️ **THE ORDERING INVERTS AGAINST THE HEADLINE**: the plate with the *better*
published figure (98.2%) is the **worse** reader exactly where it would be used.

⚠️ **The physical gate does NOT rescue it** — 23 of Breitkopf's 26
disagreements sit **INSIDE** [2.0, 8.0] (85.2% in, 80.0% out).

⚠️ So §3's re-weighted estimate and §4's direct cross-check **contradict each
other, and the direct one is the better evidence** because it is taken on the
target population instead of assuming a transfer. **§3's stated assumption is
FALSE on this corpus.** Do not quote the gated 0.978 / 0.990 as accuracy.

⚠️ **It does NOT say which mechanism is wrong.** The beam-mate's 0.984 is
Litolff-only, leave-one-out, and has **never been measured on Breitkopf**. One
of the two is wrong ~15% of the time and no instrument here can say which.

⚠️ **It is a CROSS-CHECK, not an arbiter**: the two share the notehead boxes and
the plate. *An arbiter correlated with one party sides with its own family* —
which has already happened on this very quantity, through the FRAME.

### 4a. The bar this quantity already set

`0.829` **REFUSED**; beam-mate **majority 0.938 REFUSED** in favour of
**unanimous 0.984**. A mechanism whose best cross-check on the second publisher
is **0.852 inside its own physical gate** is below a standard this quantity has
rejected **twice**. That is the decision.

## 5. THE CEILING, inherited

The shipped tier's 152 heads moved the file by **two `<voice>2</voice>` tags**.

## 6. THE CONVERSE — refused on REACH, and it needs no raster

`[C9 + L10]`'s second prediction (*given a stem direction, the notehead is on a
known side of the stem*) is a statement about two boxes already on the record,
so it **is** shippable in ADJUDICATE with no gather change. Its target is
`stems_disagree`: reach **2 of 111** (Litolff) and **7 of 17** (Breitkopf) =
**nine heads**. ⚠️ Structural, not bad luck — **108 of Litolff's 111 have BOTH
legal cells filled**, which is a two-voice column, so the convention is silent
exactly where the contest is.

## 7. TWO LIVE DEFECTS, reported with their reach and NOT fixed

**(a) A whole note has no stem, and 31 carry a direction** across the two
records: 8 (Litolff) + 17 (Breitkopf) by projection, plus **six the new
beam-mate tier BORROWS one for** on Breitkopf (0 on Litolff). Not fixed because
the repair's correctness rests on `notehead_class` being right on 31 heads
**nobody has looked at**, and a half note misread as whole *does* have a stem —
the hazard `OMR_WHOLE_REST_INK` exists for. **The test is 31 crops.**

**(b)** `probe_stem_convention.py` thresholds `exactly_one` on the **ROUNDED
display value**, so 1.2456 counts as reaching a 1.25 floor. Worth **2 of
Breitkopf's 1,774** heads. Found by a control FAILING, and reproduced
deliberately here rather than silently fixed.

## 8. THE THIRD PUBLISHER — reachable, and the catalog says otherwise

⚠️ **The dispatching brief's premise was false.** The catalog holds 235 editions
and names only 4 for these works — second *scans* of the same two publishers.
**On disk but in the catalog NOWHERE**: Breitkopf 1862 Beethoven 5, **Eulenburg
1938** Beethoven 5, Simrock 1877 Brahms 1 — two of them the same music as the
Litolff record. `docs/cloud-session-capabilities-2026-09-09.md` invites the same
error. A gather is cheap (reached ADJUDICATE in ~3 min with the expensive
readers off); a Eulenburg run was launched, was still inside `glyph_owner` at 14
min, and **was stopped rather than left as an orphan — no figure from it is
claimed.**

---

## RANKED NEXT WORK, cheapest first

1. **26 CROPS, not more probes** — the Breitkopf heads where the two mechanisms
   disagree (`out/breitkopf-marginal.json`). It is the **only** thing that can
   settle §4, and it would test the shipped tier's 0.984 on a second publisher
   for the first time.
2. **31 crops** for §7(a).
3. A third-publisher record — one cheap gather, already demonstrated.
4. Only then, if 1 and 2 favour it: a `Q.STEM_ATTACHMENT` GATHER producer,
   priced by two full re-gathers, with the gate **IMPORTED, not restated**.

## FOR SEAN, one line each

* Is our `Whole` class trustworthy enough to refuse a stem on? (§7a, 31 crops)
* Where a beam says one thing and the ink beside the head says another, which
  does he trust? His own correction on this quantity — *"The convention is
  strong. The failure is elsewhere."* — is why to ask rather than assume.
* Is **854 heads of RECORD honesty, with no expected file change**, worth a
  GATHER quantity at all?

## WHAT IS NOT ESTABLISHED

**No note was checked against the print in any arm** — every figure is one of
our readings against another, and §4's 84.7% names a **disagreement, not a
winner**. n = 2 documents, 2 publishers, 4 pages each — the same two plates this
thread has always used. The marginal figures are **REACH, not accuracy**. No
OMR-NED, deliberately. No export arm ran. The gate's 2.0 floor is
`min_height_lines` read conservatively, and its sweep runs on the **CONTROL**
population so its optimum is not claimable. Nothing touches the engraved family.
