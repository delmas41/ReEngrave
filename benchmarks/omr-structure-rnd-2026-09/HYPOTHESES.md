# Structure without a dossier — a ranked hypothesis list

> ## ⚠️ THE TARGET CHANGED ON 2026-09-05 — READ THIS BEFORE ANY NUMBER BELOW
>
> Sean redirected the workstream: **long-term there is no MusicXML to measure
> against, and the structural answer key should not be a reference encoding at
> all.** If a scan prints two players on one staff, two players on one staff IS
> the correct output — a reference file's part-splitting is a typing decision
> made later by someone else.
>
> **What that does to this document:**
>
> * **The refuted hypotheses stay refuted.** H1, H1′ and the page-side
>   multiplicity rules were about *detecting structure from the page*, which is
>   still exactly the goal. The redirect raises their stakes rather than voiding
>   them.
> * **H0 is promoted from a prerequisite to the centre.** It already scores
>   roster, continuity and identity against **hand-read printed truth**, with no
>   MusicXML in the loop.
> * ⚠️ **Every edit-count figure quoted below as a PRIZE is now suspect as a
>   goal** — above all `OMR_CONDENSED_PARTS`'s −7,118 / −9,369, which prices
>   agreement with an *encoder's* part-splitting. Those measurements are sound;
>   the target they were aimed at is not. They are kept, relabelled, not deleted.
> * **H4 is unchanged and is the hypothesis the redirect most favours** — it was
>   always about the printed page, and its recorded ceiling (a human can answer
>   *players as printed*, never *`<part>` elements the encoder emitted*) is now
>   the benchmark's definition rather than its limitation.
>
> The design that replaces the MXL-based structural key:
> [`PAGE_TRUTH_BENCHMARK_DESIGN.md`](PAGE_TRUTH_BENCHMARK_DESIGN.md).

**2026-09-05, on `3a85063c`. NOTHING BUILT, NOTHING MEASURED, NO PIPELINE CODE
TOUCHED.** This is the breadth pass Sean asked for: ten ideas triaged against
the settled negatives, each with the signal it exploits, why the existing
measurements do not already kill it, the cheapest experiment that would, and
what it is worth if true.

Read with [`benchmarks/omr-staff-identity-2026-09/FINDINGS.md`](../omr-staff-identity-2026-09/FINDINGS.md),
[`benchmarks/omr-structural-parts-2026-09/FINDINGS.md`](../omr-structural-parts-2026-09/FINDINGS.md),
[`benchmarks/omr-staff-structure-2026-09/FINDINGS.md`](../omr-staff-structure-2026-09/FINDINGS.md),
[`benchmarks/omr-staff-identity-labels-2026-09/FINDINGS.md`](../omr-staff-identity-labels-2026-09/FINDINGS.md).

---

## THE REFRAME — a signal too weak to NAME a staff can be strong enough to MATCH it

**Stated first because it is the general principle, not a motivation for one
hypothesis.** Placed here at the coordinator's direction, 2026-09-05.

The nine-signal audit scored **every** signal against **absolute** truth: is
this staff's instrument the right one? S3 0.645, S5 0.784, S4 0.819, S1 0.982 at
coverage 0.710. Those are the numbers that closed identity as "labels remain the
binding constraint."

But continuity does not ask what a staff **is**. It asks whether **these two
staves are the same one**, and that question is immune to precisely the errors
that cap the absolute numbers:

> **A systematic misreading repeats across systems.** A staff misread as treble
> in system 1 is misread as treble in system 2 — and still matches itself. A
> clef reader that is 0.848 accurate is far more than 0.848 reliable as a
> *pairwise agreement* feature, because its errors are correlated between the
> two things being compared, not independent. The same holds for a range
> envelope, a key-signature offset, a gap fingerprint, or a bracket index.

⚠️ **No measurement in the settled negatives scores any signal this way.** That
is a genuine gap in the audit rather than a disagreement with it: the audit
answered the question it asked, correctly, and this is a different question.

⚠️ **And the reframe cuts both ways — the same correlation that helps can
blind.** A signal whose error is correlated across systems agrees with itself
whether or not it is right, so **agreement between systems is not evidence that
either reading is correct.** That is the class-6 shape (`instrument` fields
agreeing at 99/99 positions *because* they were assigned by the join), and it is
why §H1 below insists on a *raw per-system* substrate rather than a derived one.
Use the correlation for matching; never read it as corroboration.

---

## Four framing results that reorder everything below

These are read out of the existing measurements, not derived here. Each one
changes which hypotheses are worth having.

### F1. `slots.py` ALREADY IS the alignment everyone would propose next

The obvious first idea — "stop joining systems by ordinal, do a monotone
sequence alignment with gaps, driven by labels + bracket group + position" — is
**built, shipped in `contextual`, and measured at 92%**
(`tools/omr/slots.py`, Needleman-Wunsch, `SCORE_LABEL_CONFLICT = -8.0` as the
only hard negative, `GAP_PENALTY = -1.0` for a tacet-suppressed part). On
Brahms 1 p.2 — the corpus's hardest continuity row — it is **12 of 13 correct**
where `export._stitch_slots` refuses outright.

⚠️ **So "align instead of index" is not a hypothesis. It is the status quo,
behind `OMR_SLOT_STITCH`, default off.** Anyone proposing it has not read
`slots.py`. What is *not* built is everything in H1–H3 below, which is about
what the aligner is ASKED and what it is FED — not about the aligner.

### F2. The aligner is never asked about a join that SUCCEEDS

`_stitch_slots_by_slot` is reached **only where the ordinal join already
refused** (`export.py:3415`, `if slots is None and _slot_stitch_enabled()`).
The Beethoven 5 p.4 silent mis-join is a row where the ordinal join **succeeds
and is wrong** — 11 staves in both systems, but not the same eleven — and it
was triangulated three independent ways (margin `Tp.` at system-2 position 6;
bracket shapes `[4,2,5]` vs `[4,3,4]`; a human's hand-correction note in
`works.json`). The one mechanism that holds a **hard negative for exactly this**
(`SCORE_LABEL_CONFLICT`) is switched off on that row by construction.

### F3. The aligner's reference roster is starved by the benchmark's page-at-a-time scope

`slots.build_reference` takes the largest **recurring** system across all pages
it is given, and `assign_slots(pages, ...)` is already written for a list of
pages. The scan benchmark hands it **one page**, so on a continuation page it
builds the roster from a continuation system — which is precisely the system
that prints no labels. Simrock labels a movement's **first page only**; Litolff
labels strings **only on p1**. The roster exists in the document, one or five
pages earlier, and nothing carries it forward. **This is a SCOPE limitation, not
a code one.**

### F4. ⚠️ On this corpus, structure work has almost no edit ceiling — judge it on a structure metric or not at all

Stated plainly because it should govern what we build:

* `omr-staff-structure` §6: **"(b) and (d) are zero. Slot assignment and staff
  segmentation are not costing anything in this bucket on this corpus."**
* **87% of `entire staff` is a condensation floor we tie Audiveris on exactly**
  — 513/513, 513/513, 0/0, 1001/1001, 649/649, 1674/1674 on all seven
  single-system rows.
* The class-6 mis-join costs **zero edits today**: `staff["instrument"]` reaches
  only `<part-name>`, and part naming is documented as moving OMR-NED by exactly
  nothing.
* Phase 1 showed the structural buckets **invert sign** depending on whether a
  count source exists (ES +2,864 without, −892 with, same stitching code).

⚠️ **OMR-NED cannot referee any hypothesis below.** A structure fix that is
entirely correct will move the pooled figure by a rounding error, and one that
is wrong may *improve* it (the symmetric metric's under-prediction reward, which
has already fooled this repo twice — the slur `drop` variant and the
fragments-are-cheaper trade). **H0 therefore is not optional.**

---

## H0 (PREREQUISITE, not ranked) — a structure metric, so the rest can be judged

**Signal:** none — this is an instrument, not a hypothesis.

**What:** score three things directly against `works.json`'s hand-verified rows,
reporting each separately and never pooled into edits:

| quantity | scored as |
|---|---|
| roster recovery | did we recover the document's ordered lineup, per printed staff |
| continuity | per (system, staff) → slot, against the hand-verified per-system lineup; the Beethoven p4 rows are the positives |
| identity | per staff, instrument name, already partly available from the audit's `evidence.json` |

**Why not refuted:** it does not exist. The audit scored *signals*; Phase 1
scored *edits*. Nobody scores the structure itself.

**Cheapest experiment:** it IS the experiment — ~a day, no detector time, reads
committed transcriptions and `works.json`.

**Worth if true:** every hypothesis below becomes falsifiable. Without it they
are all unfalsifiable, because F4 says the only available referee is blind to
them and occasionally lies.

⚠️ **Answer-key line:** `works.json` is scoring-only, as it already is
everywhere. Dossiers barred entirely.

---

## The ranked list

Ranked by **expected structural correctness per unit of work**, with edit value
reported honestly (usually near zero — see F4). Rank is not confidence: H1–H3
are ranked high because they are cheap and use built machinery, not because
they are more likely than H5.

---

### H1 — Ask the aligner about joins that SUCCEED, and use its own hard negative as a mis-join detector ★ top pick

**Signal:** `slots.align`'s `SCORE_LABEL_CONFLICT`. Two differently-named
instruments are certainly not the same part — the only hard constraint the repo
has ever identified for this question.

**The idea:** run the DP on rows where the ordinal join succeeds, and compare.
Ordinal and slot join agreeing is a confirmation; disagreeing is a mis-join
candidate. The aligner is *free at that point* — `contextual` has already run it.

**Why not refuted:**
* the block-shape mis-join detector scored precision 0.500 (n=4) — but that used
  **bracket shape**, whose boundary recall is 0.523 and *unevenly distributed
  across systems*, which is the diagnosed FP mechanism (Brahms p3 `[5,3,6]` vs
  `[9,5]`). A read label is a different and much stronger substrate: label
  precision is **0.982**;
* the "labels agree at 99/99 positions" circularity does **not** apply. That
  measured `contextual`'s per-slot `instrument` field, which is assigned BY the
  join. This reads the raw per-system label at its printed position — the labels
  workstream's own channel, which is exactly what broke the class-6 deadlock;
* the discussion doc's declined fix ("don't let the layout fit overturn a
  high-confidence lookup") is a *different* fix, refused for gutting
  `resolve_ambiguous_label`. This changes no resolution logic; it emits a flag.

**Pre-registered kill criterion:** it must flag **both** Beethoven p4 rows and
**neither** Brahms row — the two the bracket-shape detector false-positived on
at precision 0.500. Anything less is that coin flip again.

### ⚠️ MEASURED 2026-09-05, BEFORE BUILDING: H1 AS WRITTEN IS REFUTED

`probe_reference_roster.py`, `probe_union_guards.py`, over the 20-row set. No
detector time.

#### OBSERVED — and this alone closes H1

**On all 8 rows where the ordinal join succeeds, the slot join is IDENTICAL to
it** — every system reads `0,1,2,…,n−1`, **including both Beethoven p4 rows.**
The aligner does not see the mis-join. There is nothing to cross-tabulate, so
the pre-registered kill criterion cannot even be evaluated. **H1 is closed
empirically; nothing further is needed to close it.**

#### ✅ PROMOTED TO OBSERVED, 2026-09-05 — the label half is now measured

**This section was written under an "ARITHMETIC + DOCUMENTED BEHAVIOUR, NOT
OBSERVED" banner. H1′'s probe removed the banner for the label half**, and the
banner's own instruction — do not promote without a probe — is satisfied by
naming the probe: `probe_union_roster.py`, field `label_provenance` in
[`union-roster.json`](union-roster.json).

**Observed:** 13 labels over the 22 staff positions of `984073-p4` — **6 in
system 1, 7 in system 2** — with **`Tp.` read by Surya at system 2 position 6
and nothing at system 1 position 6**. The 6 + 6 + 1 arithmetic was right, and it
is now a reading rather than a deduction.

⚠️ **What is still NOT observed:** that this asymmetry is *why* the DP took the
diagonal. H1′ measures the deficit directly instead — see the insert margin
below — which is a stronger statement than the causal story it replaces. The
remainder of this subsection is kept as the original reasoning, and the
`align`-internals half of it remains inference.

`label_tiers` on `984073-p4` records **13 labels over 22 staff positions**,
`unresolved_labels` empty, `ambiguous_labels_resolved: 1`. Thirteen is exactly
6 + 6 + 1 — matching the labels workstream's reading, positions 0–5 named
identically in both systems plus `Tp.` at system 2 position 6 and nothing at
system 1 position 6. From that plus the code's documented behaviour:

1. `build_reference` picks **one system** as the roster, ties going to "most
   resolved labels" — so system 2 (7) beats system 1 (6) and slot 6 is
   `Timpani`;
2. system 1's position 6 carries **no label**, and `SCORE_LABEL_CONFLICT`
   requires **both** sides named. **A staff that prints nothing is silent, not
   contradictory** — no conflict is available, group and position decide, and
   the DP takes the diagonal.

> ⚠️ **STATUS: ARITHMETIC + DOCUMENTED BEHAVIOUR. NOT OBSERVED. DO NOT PROMOTE
> THIS TO A MEASURED RESULT IN ANY LATER SUMMARY.** The transcription retains
> the resolved instrument, never the raw margin string, so the per-staff label
> dict `slots.align` actually received is not on disk. Three independent
> readings agreeing is **corroboration**, and this document's own reframe says
> corroboration is not proof.
>
> The confirming probe — re-run the ladder, dump `labels_per_page` — is
> **named and deliberately UNRUN**, at the coordinator's direction: H1′ does not
> depend on it, and the time is better spent on H1′ than on proving why a dead
> hypothesis is dead.

---

## ⚠️ THE CORRECTED CENSUS — put here so a later reader finds it

**My first report said 7 succeeding rows and 4 multi-system rows. Both were
wrong**, and both came from the older **11-row `..graft09`** set in the main
checkout rather than the **20-row gate**, which lives ONLY in
`.claude/worktrees/reconciliation/benchmarks/omr-scan-e2e-2026-09/fixtures/`,
suffix `.reconciliation.omr.json`. This is the third time in one day that this
repo has hit that exact trap. Regenerate with `probe_union_guards.py`.

| | count |
|---|--:|
| rows | **20** |
| staves | **396** |
| multi-system rows | **11** |
| ordinal join SUCCEEDS (H1/H1′ test set) | **8** |
| ordinal join REFUSES (slot-stitch territory) | **3** |
| single-system (continuity silent) | **9** |
| rows with **more than two** systems | **0** |

⚠️ That last row is a real limit on anything measured here: every multi-system
row on this corpus has **exactly two** systems, so a progressive multi-system
union can only ever be exercised two-at-a-time.

### H1′ — the surviving form: build the roster as a UNION over systems

The defect is in `build_reference`, not in `align`. A single system cannot be
the roster when **different systems suppress different staves**, which is
exactly Beethoven 5 p.4: system 1 prints no Timpani, system 2 merges
Violoncello and Basso into `Bassi`. Both count 11; the union is **12**.

The DP already supports what this needs — `align` allows deletions on the
reference side, so each system simply gaps the slot it does not print. **Only
`build_reference` changes.** Paired with H7 (a "this staff prints nothing"
field) the silent case becomes an *informative* one.

#### The guard check, run FIRST — `probe_union_guards.py`

A guard written for one reason and firing for another is how the tenor symmetry
floor and the cap-at-2 both went wrong, so this was checked before anything was
measured.

**Finding: the guards target a different OBJECT, and a union does not trip
them — provided the union is taken over the already-filtered candidate pool.**

* `REFERENCE_MAX_SIZE_RATIO` and `_looks_merged` both filter **candidate
  systems** — they decide which *observed* system may become the roster. Their
  stated purpose is a **phase-1 segmentation failure**: a merged "system" that
  is two systems concatenated, ~2× its neighbours, which on Beethoven 9 became
  a 24-slot reference listing Flute..Trumpet twice.
* A union roster is **not a candidate system**. It is constructed *after*
  filtering. So the guards keep doing exactly their job, unchanged, upstream of
  the union.
* Measured: on **0 of 20 rows** does a union's lower bound (the largest system)
  exceed the 2× median cap. The legitimate union on p4 is **12 against a max of
  11** — plus one, nowhere near a doubling.

⚠️ **The residual risk is real and is recorded rather than dismissed.**
`_looks_merged` is label-based and is documented as **blind without labels** —
"a 24-staff concatenation of two 12-staff systems slipped through and became a
24-slot reference of entirely unlabelled parts". If a merged system survives
into the pool, a union incorporates its duplicated staves and inflates the
roster. That harm is comparable to today's (where the merged system simply *is*
the roster), not new — but it is not removed either.

**One thing the union form makes AVAILABLE that a single-system roster cannot
have:** a union whose size exceeds the largest observed system by more than a
small margin is itself evidence of a bad merge or a bad correspondence — a
self-check with no analogue today. ⚠️ Any such bound must be **read off measured
data, not chosen**; it is named here as an opportunity, and is not a proposed
constant.

### ⚠️ MEASURED 2026-09-05: H1′ IS REFUTED TOO — and the refutation is the useful half

Full reading: [`UNION_ROSTER.md`](UNION_ROSTER.md). Arm A is the shipped
`build_reference` + `align`, unmodified; arm B swaps only the roster
constructor. **Arm B is a strict NO-OP: identical to arm A on every row, every
slot, every decision, with 0 insertions across all 10 scored rows.**

The union is the correct *shape* — p.4's truth union really is 12, and `align`
really does support the gap — but **the roster constructor is not where the
information is missing.**

**The deficit is a size, not a mystery: 1.5, in the DP's own units.** On
`984073-p4` the diagonal scores 60.5 against the correct union's 58.6. Read
against the constants that produce it — `GAP_PENALTY` 1.0, a bracket-group swing
3.0, a label match 6.0, a label conflict −8.0 (a 14.0 swing) — **the union is
1.5 short of a signal it does not have**, because the four string staves that
would settle it print no label in either system.

#### Arm C closes the reweighting route — it is a refutation, not a proposal

Gap and insertion set to **zero**: the cheapest union obtainable from the terms
`_pair_score` already has. It fixes both p.4 rosters and **breaks
`brahms-…-p3`** (roster 15 against a truth of 14; 28/28 → 24/28). The two cases
are **indistinguishable by construction — the insert margin is 1.5 on p.4 and
1.5 on brahms-p3**, so anything that flips one flips the other.

> ⚠️ **So reweighting is CLOSED, not untried.** Do not close H1′ by lowering
> `GAP_PENALTY`: that *is* arm C, it is fitted to two rows of one engraving, and
> it is measured to break a correct row.

#### ⚠️ THE LESSON THAT GENERALISES: a shape criterion is necessary and not sufficient

**Arm C reaches a 12-slot roster on p.4 and is still wrong** — it inserts at
index 6, *before* Timpani, instead of gapping Timpani and appending Basso, so
continuity moves only 14/22 → 15/22. **The pre-registered criterion was met in
letter while the join stayed broken, and roster size alone would have declared
success.** Only the continuity column caught it.

> **Any future structural criterion needs a CORRECTNESS check, not just a SHAPE
> check.** Size, count and boundary-agreement are all shape tests. This one cost
> nothing because the arm was built to refute; the next one may not be.

#### The measured constraint this hands to H3 and H5

**`group_index` cannot be the discriminator.** On `brahms-…-p3` the *same*
fourteen staves are printed in both systems, and `system_grouping` reads their
blocks as `[0×5, 1×3, 2×6]` against `[0×9, 1×5]` — a detection disagreement
between two systems of **one page**, which is block recall 0.523 "unevenly
distributed across systems". On unlabelled staves `group_index` is the union's
only discriminator, and **it cannot tell a real lineup change (p.4) from its own
noise (brahms p.3)**.

**Worth if true:** the only position-independent mis-join detector with a
credible substrate; closes the class-6 case that three methods found and none
can act on. **Edits: ~0 today** (F4) — a correctness and prospective-safety
result, and the structural-parts FINDINGS already names it as a design
constraint for any future count source ("must abstain where the staff's IDENTITY
is unconfirmed").

⚠️ **n = 8 rows, of which the positives are 2 (one page, two editions).** This
can be *refuted* on 8 rows; it cannot ship on them.

### ⚠️ MEASURED 2026-09-05: H1′ IS REFUTED — [UNION_ROSTER.md](UNION_ROSTER.md)

`probe_union_roster.py`, A/B/C over the 11 multi-system rows (10 scored, 1
abstained for stating no lineup). Arm A is the shipped `build_reference` +
`align` called unmodified; arm B swaps only a benchmark-local
`build_reference_union`, insertion priced at `GAP_PENALTY` by symmetry.

**Arm B is a strict NO-OP: 0 insertions on 10 of 10 rows, roster identical to
arm A everywhere.** The p.4 union comes out 11, not 12 — criterion (1) failed;
criterion (2) passed trivially.

The deficit is **1.5 in the DP's own units** on both p.4 rows (a bracket-group
swing is 3.0, a label conflict 14.0): the union must give up a match to make
room for a twelfth slot, and the four string staves that would settle it print
no label in either system. **The label half of the INFERRED mechanism above is
now OBSERVED** — 13 labels over 22 positions, `Tp.` read by Surya at system 2
position 6 and nothing at system 1 position 6.

⚠️ **And the reweighting route is closed, not merely untried.** A refutation arm
with gap and insertion set to zero fixes both p.4 roster sizes and **breaks
`brahms-…-p3`** (28/28 → 24/28, a phantom 15th slot on a page whose two systems
print the same fourteen) — because that row's insert margin is **also 1.5**, its
`group_index` vectors disagreeing between systems from *detection noise* rather
than from a lineup change. On unlabelled staves `group_index` is the union's only
discriminator and it cannot tell the two apart. That is a measured argument for
**H5** before any new consumer of blocks, and it hands **H3** a threshold to
beat (>1.5) and a row that must not move.

⚠️ The same arm shows criterion (1) was **necessary and not sufficient**: it
reaches a 12-slot roster on p.4 by inserting at the wrong index and still scores
15/22. Roster size alone would have declared success.

---

### H2 — A document-scoped roster pre-pass: read the lineup where it IS printed, carry it where it is not ★ highest value

**Signal:** publisher convention, measured and already proved by ink — Simrock
labels a movement's **first page only**; Litolff labels winds and brass on every
system and **strings never after p1**; Breitkopf labels everything (0 in class
(a)). 115 of 407 staves print no label; **29 of 29** unresolved non-treble-family
staves are in that class.

**The idea:** the labels FINDINGS calls class (a) "a wall — nothing". It is a
wall *for that page*. It is **not a wall for the document**: the names are
printed, five pages earlier. Run a cheap **structure-only pre-pass** over the
document's early pages — `preprocessing.render_page` → `staff_detector.detect_staves`
→ `system_grouping` → the free label ladder, **no YOLO, no notes** (verified:
`detect_staves(page)` takes no detector) — feed those pages to
`slots.assign_slots`, and let `build_reference` build the roster from the
labelled first system. Every later page then aligns against a roster that has
names.

**Why not refuted:**
* the "wall" result is per-page by construction — the 20 rows are individual
  pages, and the FINDINGS says so explicitly ("this adds nine continuation
  pages, which is precisely where labels stop being printed");
* the paid vision rung was closed because 115 of 149 unresolved staves *print
  nothing* — which is an argument against **reading harder** and is precisely
  why **reading elsewhere** is the remaining move;
* `assign_slots` already accepts a page list and `build_reference` already
  prefers a **recurring** size with a merge guard. Nothing new is invented.

**Cheapest experiment (~1–2 days):** do not build the pre-pass first. **Count
the opportunity:** for each of the 20 rows, take its edition's page 1 (already
in `library/editions/`), run structure-only + labels, and ask how many of the
row's unlabelled staves would receive a name from a monotone alignment to that
roster. ⚠️ Assert the input counts (staves found on page 1, labels resolved
there) before reporting any coverage number — the labels workstream's own
methodological note. **Kill criterion:** if fewer than half the 115 class-(a)
staves sit in a document whose page 1 labels the corresponding slot, the wall is
real at document scope too and this dies.

**Worth if true:** the largest single block of unresolved identity in the
corpus, **and** it is the one thing that would let `build_reference` produce a
*named* roster on Litolff and Simrock. It feeds H1 (labels are the aligner's
dominant term), H3 and H4. ⚠️ Edits still ~0 directly (F4); its value is the
roster artifact, which is what H4 then hands to a human.

⚠️ **Answer-key line, and it is thin here — say it out loud.** The roster comes
from *another page of the same PDF*, which is page-side evidence. It is NOT the
reference encoding and NOT a dossier. Do not let it drift into "look the work up
somewhere" — that is H4's honest, human-in-the-loop version.

---

### H3 — Feed the aligner two features it does not have: measured inter-staff gaps, and register continuity

**Signal:** `_pair_score` uses exactly three terms — label, `group_index`,
relative position. Two free ones are missing.

1. **The gap fingerprint.** An engraver sets vertical gaps by family: wide
   between blocks, tight within a braced pair. A system's gap vector
   `[tight, tight, wide, tight, …]` is a shape that survives from system to
   system, and it is pure geometry — no detector, no OCR, no lexicon.
2. **Register continuity.** A part's median pitch does not jump across a system
   break. Free from the transcription.

**Why not refuted:** the audit refuted S8's **brace detection** (spoke on 18
staves) and S4's **absolute range veto** as *identity* signals. Neither is this.
This is a **relative pairwise match feature**, and that distinction is the
central argument of this whole document:

> ⚠️ **A signal too weak to NAME a staff can be strong enough to MATCH it.**
> The audit scored every signal against absolute truth — S3 0.645, S5 0.784,
> S4 0.819. But a systematic error repeats across systems: a staff misread as
> treble in system 1 is misread as treble in system 2, and still matches
> itself. Continuity asks whether two staves are the same, not what either is,
> so it is immune to exactly the correlated errors that cap absolute identity.
> **Nothing in the settled negatives measures a signal this way.**

**Cheapest experiment (~half a day, no detector time):** from committed
transcriptions, extract per-system gap vectors and register vectors; measure
whether the true correspondence maximises agreement, on the **11 multi-system
rows** (corrected 2026-09-05 — "four" was the older 11-row `..graft09` set;
`staff_geometry` is present on all 396 staves), **before** touching
`_pair_score`. Kill criterion: if the true pairing is not the argmax on rows
where labels are absent, the features are noise.

⚠️ **Run this only AFTER H1′, at the coordinator's direction** — as its control,
not beside it, so H1′'s number is not contaminated by new `_pair_score` terms.

### H3's SPEC, handed to it by H1′ — a number to beat and a row that must not move

H1′ turned H3 from "a feature idea" into a specified target:

| | |
|---|---|
| **the number to beat** | **> 1.5** in `_pair_score`'s units, on `beethoven-…-p4` |
| **the row that must not move** | **`brahms-…-p3`, 28/28**, whose insert margin is *also* 1.5 |
| **where the evidence must come from** | the **four unlabelled string staves** — the only place p.4's answer lives |

⚠️ **THE CENTRAL DESIGN CONSTRAINT, and it is what H3 must be judged on.**
H3's features earn their place by being **independent of BOTH labels AND
`group_index`**:

* **labels** — because the four staves that would settle p.4 print nothing in
  either system, so a label-derived feature is silent exactly where it is
  needed;
* **`group_index`** — because its between-system disagreement on brahms-p3 is
  detector noise of *the same magnitude* as p.4's real lineup change.

> **If H3's evidence correlates with `group_index`, it inherits that noise and
> H3 will have measured the same thing twice.** Testing that correlation is part
> of H3, not a postscript to it.

### ⚠️ MEASURED 2026-09-05, THEN PARKED BY A REDIRECT — [MATCH_FEATURES.md](MATCH_FEATURES.md)

`probe_match_features.py`, the **discriminator stage only** (the A/B through
`slots.align` was never started — clause (3) is unevaluated and no roster-size
claim exists). 10 scored rows, 1 abstained, the same fixtures, truth and partner
metric as H1′.

**Neither feature separates `beethoven-…-p4` from `brahms-…-p3`.** The gap
fingerprint holds every identical-lineup row at the diagonal (22/22, 28/28,
30/30 over wide skip-cost plateaus) but on p.4 its argmax **never** beats the
diagonal at any skip cost — best 14/22 against a computed ceiling of 21 — and
its margin toward the truth path is **+0.37 per unit weight**, so closing H1′'s
1.5 deficit would need a weight of **4.06**, larger than the whole bracket-group
swing. Register continuity is *worse* than the diagonal on every row that has
one (4/30 on Dvořák) and flips sign between two editions of the same page.

⚠️ **The `group_index` constraint was SATISFIED and the feature still failed.**
Gap-fingerprint AUC against `group_index` agreement: median **0.510**, and
**0.502** on `brahms-…-p3` itself — genuinely independent of both labels and
blocks. **Independence was never the binding problem; information was.** A future
label-free feature must clear an information bar, not an independence bar.

One positive worth keeping: on `brahms-…-p2` (a real lineup change, 14 staves
against 13) the gap fingerprint **alone** lifts continuity 14/27 → 24/27 with no
labels and no blocks. The corpus holds only two printed-lineup-change patterns
and the feature scores 0/2 on one and 1/1 on the other — **the next measurement
is a census of printed lineup changes, not another feature.**

**H5 is now motivated by measurement rather than tidiness** — arm C is a direct
argument for raising block recall *before* anything is built on blocks. It is
**deliberately NOT started**: it would raise the quality of a discriminator H3
is designed not to depend on. It stays ranked, and becomes the next build with a
real argument behind it only if H3 lands and something still wants block
evidence.

**Worth if true:** makes the aligner work on Litolff/Simrock continuation
systems where its dominant term is silent — the population H2 also targets, by a
route that needs no OCR at all. Cheap enough to run alongside H2 as its control.

⚠️ Do **not** use "this staff has no noteheads" as a feature. The retracted
alarm in the audit plan is explicit: five staves called resting on Dvořák p5
were all genuinely resting, and treating zero-detection as abstention would have
discarded five correct readings out of five. Record `n_noteheads_detected`
beside any register figure.

---

### H4 — Ask the human ONE question per document: confirm the roster

**Signal:** the operator.

**The idea:** the three questions have one shared artifact — an **ordered lineup
with player counts**. H2 produces a draft of it automatically. A human confirms
or corrects it once per document, in one screen, and it then supplies: identity
for every staff (via the alignment), the anchor for continuity, and — crucially
— **the only known source for multiplicity**.

**Why not refuted:** the multiplicity negative is a proof that the count is not
on the PAGE (62 vs 72 staves under identical printed labels, eleven signals, best
ensemble 0.526 against an `always 1` baseline of 0.538). It is not a proof that
the count is unknowable — the oracle arm is worth **−7,118 edits**, and
**stitch + oracle compose superadditively to −9,369**. A human is the only
non-dossier source anyone has identified.

**Cheapest experiment (~half a day, arithmetic only):** compute the leverage
ratio from committed data. 407 staves over ~6 editions ≈ **one question per
document**. Then report **coverage before gain**, as Phase 1 demands: the oracle
map misses 4 of 20 rows holding **4,944 of the 5,400 surviving `entire staff`
edits (92%)** — Mahler 5 is 38 reference parts against 13–18 printed staves — so
a roster question reaching *those* rows is worth more than one improving covered
rows.

**Worth if true:** the largest measured number in this whole area (−9,369), and
the only route to it. ⚠️ **Design constraint, already paid for:** the count
source **must abstain where the staff's IDENTITY is unconfirmed, not merely
where the count is ambiguous** — a label-keyed source on Beethoven p4 slot 6
would confidently hand a Trumpet's 2 players to a printed `Violino I` whose
truth is 1. So H4 depends on H1.

⚠️ **Answer-key line: this is the honest side of it.** The human is not reading
the reference encoding; they are reading the printed score. But an evaluation
where a human supplies the roster must say so in the arm name, every time, and
it can never enter a headline pooled figure.

---

### H5 — Raise bracket-block RECALL, rather than building a better classifier on top of it

**Signal:** bracket ink. Blocks are **precision 0.920–1.000, recall 0.523–0.564**
— Brahms 1 reads 2 blocks against 4 truth family runs on all three systems.

**The idea:** every consumer built on blocks has died of *recall*, not of the
idea. The family veto was vacuous (5 of 9,219 detections outside their family
union). The shape detector's FPs are diagnosed as under-detection distributed
unevenly across systems. `group_index` is also a `_pair_score` term at ±1.5,
so recall caps H1 and H3 too. **Fix the substrate instead of the consumer.**

**Why not refuted:** everything measured is a consumer. Nobody has asked *why* a
boundary is missed — is the bracket ink absent from the crop, is it a sub-brace
inside a bracket, is it a thresholding failure?

**Cheapest experiment (~1 day):** for the 21 missed boundaries, render the
bracket column and classify the cause by hand. That is a diagnostic with a
bounded answer and no code change; it says whether this is a CV fix worth doing
or a convention we cannot see.

**Worth if true:** lifts a term in the aligner, revives the position-independent
shape signal, and is the only structural signal that is genuinely free and
genuinely independent of both OCR and score-order priors.

---

### H6 — Measure-count conservation as a segmentation alarm

**Signal:** every staff of a system prints the same number of measures. A hard
engraving constraint.

**The idea:** `draft_windows` already takes the mode across staves and flags
disagreement — for windows, not for structure. Bach Brandenburg 3 p.1 segments
as `[12,3,3,3,1,2]` on a page printing one system, and **no signal in the audit
is meaningful on that row**. A conservation check would say so *automatically*
instead of a human noticing.

**Why not refuted:** it is the conservation-audit shape the taxonomy doc asks
for (class 2), applied to structure rather than to beams. Untried there.

**Cheapest experiment (~half a day):** run it over all 20 rows and see whether
it flags exactly the rows already known bad (Bach p1; Mahler p2/p3, where
re-detection reads 19/15 against the fixtures' 17/13) and nothing else.

**Worth if true:** cheap, and it protects every hypothesis above from being
scored on a row whose phase 1 failed — which is currently done by hand.

---

### H7 — Separate "printed nothing" from "read nothing", as a first-class field

**Signal:** ink. The labels workstream already proved this is cheap and reliable
**in the negative**: blank Litolff/Simrock margins measure **0 px** over bands of
100k–260k; a printed `Tr.` measures thousands.

**Why not refuted:** the audit's §7 asks for exactly this for key signatures
(`signed_fifths` returns 0 both for "C major printed" and "nothing read"), and
it is unbuilt. The label case is the one structure needs: the labels FINDINGS
warns that any join check must **abstain where labels are absent, not refuse**,
or stitching dies on Litolff and Simrock outright — and today the pipeline
cannot tell those two apart.

**Cheapest experiment:** none needed as a *hypothesis*; it is an enabler whose
value is measured through H1 and H2. Do not build it speculatively — build it as
H1's abstention gate, which is exactly the shape the discussion doc prescribes
("the fix taken instead is provenance, not logic … built as the abstention gate
of the arm that needs it, so it is measured by that arm").

---

### H8 — Per-staff-per-system identity provenance

**Signal:** none new. Bookkeeping.

`instrument_source: "label"` survives propagation across a mis-joined slot, so
it reads like a per-item provenance claim and is not one. Any consumer keyed on
`staff["instrument"]` inherits the corruption silently. Named in the discussion
doc as the fix that *should* be taken, and unbuilt.

**Worth:** zero edits, indefinitely — until something trusts the field, which is
what H4 would do. Build it **inside** H1/H4, never on its own.

---

### H9 — A learned instrument classifier over the 1,745 reference encodings

**Signal:** how a part BEHAVES — register, tessitura, rhythmic density, doubling
relationships with other parts.

**Why not (quite) refuted:** the audit tested only S4's crude "does the range
admit the truth" veto (precision 0.819, rescued 50 / contradicted 12 over S5). A
model over richer features across a large corpus is a different object.

**Why it is ranked low anyway, and this is the honest part:**
* **identity reaches ~0 edits** (F4), so the payoff is instrumental — it would
  serve as a label substitute inside the aligner, which H2 and H3 reach more
  cheaply;
* it inherits every detection error in the transcription, and the corpus's own
  in-block exact-instrument ceiling is **0.156**;
* it needs a training pipeline, which is weeks against H1–H3's days.

**Cheapest experiment if pursued anyway:** leave-one-work-out on the reference
encodings alone (no OMR), predicting instrument from the note stream. If it
cannot reach useful accuracy on **clean** data, it certainly cannot on ours —
a cheap kill, and it costs no detector time.

⚠️ **Answer-key line:** training on other works' encodings is legitimate;
the scored work's own encoding must be held out, and a work-level (not
movement-level) split is required — a movement of the same work is the same
orchestra.

---

### H10 — Publisher/era layout grammar learned across the 235 catalogued editions

**Signal:** `data/score-library/catalog.json` carries publisher and date.

**Why it is ranked last, having looked promising:**
* the three conventions that matter are **already known by hand** (Simrock /
  Litolff / Breitkopf, proved by ink) and there are only 5 publishers in the
  scan corpus — a learned grammar would be fitted to n≈5;
* the analogous survey has already burned once: Phase 0 swept all 1,745
  encodings and **could not be read by publisher at all** — `catalog.json`
  carries two `source` values and the variation is by **encoder** (MuseScore
  1,269 / music21 387 / Finale 83), not by publisher;
* the useful half of it — "derive the convention from THIS document" — is H2,
  which needs no publisher table and works on a document from a publisher we
  have never seen.

**Kept on the list** because the *diagnostic* version is cheap and would tell us
whether H2 generalises: across the catalogued editions, how varied is
"which systems get labels?" If it is three conventions, H2 is safe; if it is
thirty, H2 needs a per-document detector.

---

## What I would refuse outright

* **Any page-side multiplicity rule.** 62 vs 72 staves under identical printed
  labels, eleven signals, not one separating; best ensemble 0.526 against
  `always 1`'s 0.538. This is a proof, not a weak result.
* **Re-proposing sequence alignment for continuity.** F1 — it is `slots.py`.
* **Transferring a roster from another EDITION of the scored work.** It is
  page-side in form and answer-key-shaped in effect, and the honest version of
  the same move is H4, where a human does it and the arm is named for it.
* **More OCR reach as a route to clefs.** `probe_clef_reach.py`: **29 of 29**
  unresolved non-treble-family staves are class (a), behind the printing wall.
* **Calibrating anything on the reference encodings' placement conventions.**
  Phase 0 — it measures MuseScore.

## What I would build first, if the choice were mine

**H0, then H1 and H3 together, then H2.** H0 because F4 says nothing else can be
judged; H1 and H3 because they are days rather than weeks, need no detector
time, and reuse machinery that is already 92% accurate and switched off; H2
because it is the largest block of opportunity and H1/H3 are its controls. H4 is
the biggest number on the page (−9,369) and should be *designed* alongside them,
but it depends on H1's abstention gate and must not ship before it.
