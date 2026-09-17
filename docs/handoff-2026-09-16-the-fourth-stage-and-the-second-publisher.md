# Handoff — the fourth stage exists, the second publisher arrived, and three briefs were overtaken mid-flight

**2026-09-16.** Picks up from
[handoff-2026-09-15-six-jobs-in-parallel.md](handoff-2026-09-15-six-jobs-in-parallel.md),
which is still correct about everything it measured. **Its §11 is CLOSED** (§5
below) and its §10 has moved (§9 below).

⚠️⚠️ **READ §7 FIRST IF YOU ARE SHORT OF TIME.** The transferable finding of
the day is not any measurement — it is that **three separate briefs were
overtaken by work already on main**, in one session, and each was caught only
because somebody checked. In a week with this many parallel sessions, *"has
this already been done"* is a measurement to take, not a courtesy to extend.

---

## 1. WHAT LANDED

Six PRs merged today. Verified against the tree, not against the reports.

| PR | what |
|---|---|
| **#33** | `OMR_WHOLE_REST_INK` — the note-deleting rule behind a flag, **default ON** (Sean's call, §4) |
| **#34** | Surya scoped in the staged pipeline, both OCR rungs default ON |
| **#35** | PR #31's meter / numbering / phantom work, reconciled |
| **#37** | Four branches: **`infer-stage`** (§2), **`info-reaches-its-consumer`** (§3), the Breitkopf shared record (§5), the meter-carry cost arm |
| **#38** | The meter pricing arm — **reach zero**, and two instruments that were wrong (§6) |
| **#40** | `OMR_DIRECTION_TEXT_SCAN_GATE`, default off |

On main and verified by `git cat-file`: `tools/omr/staged/infer.py`,
`staged/inferences.py`, `staged/wiring.py`, `tools/omr/no_producer.py`.

**Both new flags have the right direction**, checked at the predicate rather
than in prose: `OMR_INFER` defaults `"0"` with an **allow-list** (`in
_ON_WORDS`), `OMR_WHOLE_REST_INK` defaults `"1"` with a **deny-list** (`not in
(...)`). CLAUDE.md's *"A flag's OFF test must follow its DEFAULT"* satisfied in
both directions.

---

## 2. THE FOURTH STAGE EXISTS — and its REACH NUMBER is the finding

`tools/omr/staged/infer.py` + `inferences.py`, behind `OMR_INFER`, **default
OFF**. Sean directed it built ahead of the plan's phasing
([plan-2026-09-10](plan-2026-09-10-wire-first-then-reconcile.md) §5d says *"may
not be built before the first cleanup count"*); the override is recorded rather
than quietly taken, on the reasoning that Phase 2 IS open and produced seven
observations.

**Five disciplines, each enforced by the harness rather than described:**
`run()` *requires* EVALUATE's report, so it cannot run early; it cannot run on
an unfrozen log; `INFERABLE = {NARROWED, ABSTAINED}`, so it **can never
overturn a DECIDED reading**; it must pick one of *that reader's own*
candidates, so it cannot invent a value; and a rule returns a `Proposal` with
**no `decider` and no `outcome` field**, so there is no code path to an
unlabelled verdict. `export.py`'s refusal to argmax is **untouched** — INFER
collapses a narrowing visibly and the exporter then writes a DECIDED value.

**Bypass is provable, not merely default-off:** off means the `inference` key
is **ABSENT, not null**, so a flag-off record is byte-identical to one from a
tree without the stage, and the arms that isolate an earlier stage stay
structurally blind to it.

⚠️ **Hazard (b) — correlated witnesses — came out as a COMPUTATION, not an
argument.** `independent_groups` partitions witnesses by whether their
provenance closures intersect and writes the result to `Verdict.correlated`, a
field built for exactly this and consumed by nothing until now.

⚠️⚠️ **REACH WAS MEASURED BEFORE THE RULE WAS CHOSEN, AND THE NUMBER IS THE
RESULT: 357 narrowed durations yielded 7 inferred, 6 reaching the file.** Read
that as the stage answering the question the cleanup count was supposed to
answer — **the narrowed-duration population is not resolvable by cross-staff
agreement** — rather than as a disappointing yield. The `no_pitch` population
(215) was refused **on the data's own evidence**: those staves' clef verdicts
are abstained 108 / narrowed 107 / **decided ZERO**, so filling a pitch means
inferring a clef across the part join this document is already known to get
wrong on 12 of 75 staff-systems.

⚠️ **The first rule was wrong and the funnel said so.** It required the next
onset to be the *adjacent* column and inferred **1 of 357** — a column is an
instant on the SYSTEM, so a staff playing a half note against neighbours'
eighths skips columns, and adjacency admitted only the finest-subdivided staff
per bar, which is the one least likely to be narrowed. Generalised to *"the
witness ends where this note ends"*: **1 → 7**.

**Refused, deliberately:** calibration from the score library (a corpus run,
and the one thing this repo measured failing at ECE 0.1277); argmax on
`support`; pitch inference; majority voting; and a **bar-sum rule** — partly
because that arbiter falls silent where the reading is worst, but decisively
because it would make `bar_fill` a measurement of the quantity the rule
optimises.

⚠️ **NOT ESTABLISHED: the six added notes have not been checked against the
print.** On a cleanup count they are six things a human might take back out.

---

## 3. THE WIRING CHECK — and the roster finally reaches a decision

`tools/omr/staged/wiring.py` (`--check` / `--json` / `--run`), a derived check
for *the value existed and nothing read it* — the pattern this repo has found
ten or more times, always by accident. Three questions, **each with a positive
control that exits 2 before any finding is examined**, because a question that
can only answer *"nothing wrong"* is not a question.

| question | examined | findings |
|---|--:|--:|
| **FRAME** — a declared input read at a Kind where nothing files it | 81 declared reads | **0 broken, 6 LATENT** |
| **DETAIL** — a key written on a row and named nowhere else | 113 keys | **22 unread** |
| **ROUNDTRIP** — a field dropped by its own `to_json` | 9 classes, 56 fields | **1, and it is READ** |

**The roster now reaches ADJUDICATE** — Sean's own stage ruling
([handoff-2026-09-11](handoff-2026-09-11-phase-2-opened.md) §7), dead on every
staged run this repo had ever made. **Three faults wearing one name:** no CLI
producer (`--work-id` / `--no-roster` now exist), a read at the wrong scope
(`Q.ROSTER_ENTRY` is filed on the DOCUMENT and the decision runs at STAFF, so
the obvious `ev.rows(...)` would have returned nothing forever), and a
near-miss of restating `work_roster.decide` instead of importing it.

⚠️ **Reach is small and stated as such: 1 of 50** verdicts on the cleanup-count
pages — `Basso.` **Bass voice → Contrabass**, the singer-on-an-orchestral-score
the slot-index session recorded and left open — and **20 of 1236** on the
lexicon corpus, reproducing the legacy layer's recorded 1.4%.

⚠️⚠️ **THE SHARPEST RESULT IS SELF-REFERENTIAL: the check flagged that scope
trap as LATENT before the line existed.** The instrument caught the bug its own
author was about to write.

⚠️ **It went RED on the merged tree, and that is the tool working** — seven
detail keys PRs #34 and #35 landed while it was in flight, each checked at
landing and **inventoried in `KNOWN_GAPS` with a reason, never suppressed.**

**Still unanswered, both honestly:** *decided-but-unwritten* is out of reach
statically — `export.status_census` owns it at run time as a partition and a
static twin would be a second record nothing forces to agree with it; and
*projection drops* only partly — ROUNDTRIP works at class grain and **would not
have caught `works.json`'s `lines`**, which four modules each named and each
dropped.

---

## 4. THE NOTE-DELETING RULE IS FLAGGED, AND SEAN SET IT ON

`OMR_WHOLE_REST_INK`, **default ON**, merged as PR #33 (`fa054a61`).

It gates **only the exporter's refusal**: the verdict stays DECIDED and on the
record either way, so turning the flag off never throws the evidence out with
the behaviour. `OMR_WHOLE_REST_INK=0` restores the pre-2026-09-15 exporter
exactly.

**Why it is flagged when nothing else in its family is: it DELETES NOTES.**
Every other staged repair adds an element or withholds one the record never
decided; this one removes 22 pitched `<note>` elements a human would otherwise
have kept. Its evidence is the right kind — 25 of 25 fires cropped and read
against the print, zero of them a real note, then **independently re-verified
by a second agent who re-rendered every crop with its own instrument** and also
cropped the 18 rows called *real notes* (ovals with stems, structurally outside
the rest band). But it is **one document, one publisher, four pages**, and the
six cuts are the p05/p95 of *that plate's own* 395 `restWhole` glyphs, with
**two of the six on a plateau one step wide or less**.

⚠️ **The crops are NOT in the tree.** Commit `0bb2d6f9` says they *"are
committed under `crops/`, 1.5 MB on purpose: a reader who cannot see them has
to take the adjudication on trust"* — and `.gitignore:112` excludes
`benchmarks/**/crops/` and always has. The `a907e41` pattern: a commit message
claiming what the tree contradicts, and this one claims to remove exactly the
trust it requires. Not fatal (they regenerate), but do not go looking for them.

---

## 5. ⚠️ §11 OF THE 09-15 HANDOFF IS CLOSED — the shared records exist

That handoff called it *"the standing gap three jobs found independently"* and
judged making the record *"probably worth more than the next feature"*. It was
built the same night:

```
library/_shared-records/beethoven5-p1-p4.record.json         133 MB   Litolff Beethoven 5 i, pdf 1-3
library/_shared-records/brahms1-breitkopf-p0-p3.record.json  444 MB   Breitkopf Brahms 1 i, pdf 0-3
```

`library/` is gitignored; **the recipe and the receipt are committed** at
`benchmarks/omr-shared-records-2026-09/`, with md5
`52b98f1cdfee3b39f10e56c592828ea4` and a git tag
`record/brahms1-breitkopf-p0-p3` naming the tree that made it.

**Check the md5 before reading either record.** A record whose bytes you have
not checked is a record whose provenance you are taking on trust.

---

## 6. THE METER CARRY — the blocker is NAMED at last, and it is the CORPUS

Two commits in one day, and the second supersedes the first's usefulness.

`486772aa` stamped the Brahms cost arm as having **measured a tree that no
longer exists**: its gather provenance names `ce7b8ba7`, while `A-METER-6` /
`METER_CHANGE_MIN_STAVES` landed in PR #35 afterwards and governs exactly the
mechanism the arm measured. The direction was recorded as **a prediction, not a
measurement**. That stamp is a model of the right behaviour and should be
copied.

Then `89620d27` (PR #38) ran the arm properly, and the answer dissolves the
question: **REACH IS ZERO, and it is not a null cost.** The meter is decided on
**7 systems of 7** (voted 2, change_only 5) with **no abstention**, and
`_meter_fallbacks` is reached only where a system's own reading FAILED.
**Neither flag has a domain on this document**; carry sources SKIPPED = 0 says
the same of A-METER-6, so the stale-tree worry is void — a tree change cannot
matter where the domain is empty. **`OMR_METER_CARRY`'s cost side is STILL
UNPRICED.**

⚠️⚠️ **AND THE BLOCKER IS NOW NAMED, WHICH IS WORTH MORE THAN THE NUMBER WOULD
HAVE BEEN: the flag is waiting for a document that ABSTAINS *and* MISREADS.**
Litolff abstains on 6 of 7 systems but reads its one meter correctly; Breitkopf
misreads badly but abstains nowhere. **The two halves of the hazard have never
been present in one document.** That is a CORPUS problem, and no record on this
machine can solve it.

⚠️⚠️ **CORRECTED THE SAME DAY, PR #39, MERGED — THAT LAST SENTENCE WAS WRONG
AND WAS REFUTED BY LOOKING, NOT BY GATHERING.** `p0p3` (Breitkopf Brahms 1
mvt 1) has had both halves the whole time, stable in 11 of 11 committed arms
across 5 generations: `system/0/0` reads `C` (4/4) where the dossier says 6/8,
and `system/3/0` abstains, `carried_from: system/0/0`, refused at support
**−8.0** with `bars_agree 0 / disagree 9`. **It still does not price the
flip** — the newer finding is narrower and sharper: the BARS arm on that same
system reaches length **3.0 at +7.0** (which IS 6/8) and abstains
`bars_name_a_length_without_a_form`, because the only system it could borrow a
*spelling* from is the one that misread `C`. **The blocker is the
form-borrowing rule, not a missing corpus.** See
[docs/handoff-2026-09-16-abstains-and-misreads-was-already-there.md](handoff-2026-09-16-abstains-and-misreads-was-already-there.md)
and `benchmarks/omr-meter-abstain-and-misread-2026-09/FINDINGS.md`.

⚠️ **Two instruments were wrong, and one of them is quoted in CLAUDE.md.**
`probe/bar_fill.py`'s `--bar-beats` **defaulted to 2.0** — Litolff's 2/4 — so
on a 6/8 document it reported 96.3% OVERFULL / 0.6% exact, with 684 bars
holding a measure rest at exactly the right length counted OVERFULL. Repaired
as a **REFUSAL** (`--bar-beats` is now REQUIRED), because a default converts
*"I do not know this document's bar length"* into a definite answer.
**CLAUDE.md described that probe as reading "the `<time>` the same file
declares". It never did** — on a 2/4 document the constant and the declaration
merely coincided. ⚠️ Also: **no bar-fill figure on Breitkopf is comparable to
Litolff's 38.0% → 69.2%**, because the denominator is the part join — 3,407 of
4,225 bars (80.6%) are tacet padding across 97 fragment parts.

---

## 7. ⚠️⚠️ THE PATTERN OF THE DAY — THREE BRIEFS OVERTAKEN BY WORK ALREADY DONE

The 09-15 handoff's §7 was *five of six REPORTS contained a claim the tree
contradicted*. Today's is its dual, and it is about **plans** rather than
reports:

1. **A brief sent an agent to land a branch that was already merged.** The
   silence work had gone in via PR #32 while the brief was being written. The
   agent caught it with `git rev-list --count` and pivoted to independently
   verifying shipped code — which was the more useful job, since that rule
   deletes notes and had never been checked by anyone but its author.
2. **An agent wrote ~200 lines of a PRODUCER check a sibling had landed the
   same day** as `tools/omr/no_producer.py`. Deleted as a duplicate and
   recorded in FINDINGS rather than buried. ⚠️ **The brief is at least half to
   blame**: it led with the producer question and never said *check whether this
   exists*. CLAUDE.md states the rule — `git log --all -S` before building.
3. **A brief to run a Breitkopf gather, and to re-run the meter arm, was
   overtaken twice** — the record had been built the previous night (§5) and
   the arm had been run that morning with reach zero (§6). Caught before
   dispatch on the first count and mid-flight on the second.

**The cost was roughly 200 lines, one agent's premise and nearly a redundant
30-minute gather — all of it recoverable, and all of it avoidable by one
command.** The rule to carry: **before dispatching or building, check
`origin/main` and `git log --all -S`.** Main moved four times during this one
session.

---

## 8. THE SECOND-PUBLISHER PRICING — landed, and the cuts DO NOT transfer

PR #41 (`d8341787`). `OMR_WHOLE_REST_INK` priced on Breitkopf against the
shared record. **The rule's OUTCOME survives and its stated SAFETY CASE does
not.**

| | Litolff (the cuts came from here) | **Breitkopf** |
|---|--:|--:|
| shipped band over that document's OWN whole rests | **89.9%** | **52.5%** |
| `restWhole` more than a space BELOW its own staff | **0** | **64** |
| witness split of the fires | slot 20 / nb 5 | **slot 1 / nb 11** |
| hand-adjudicated as a whole rest | **25 of 25** | **1 of 12** |

The two cuts move in **opposite** directions (max height p95 0.840 → 0.670,
max aspect p95 3.087 → 4.633) and the witness inverts. The mechanism is the
neighbour witness, which assumes rests stand inside their own staff and here
vouches out of a 64-row cross-staff population Litolff does not have.

⚠️⚠️ **THE FLAG STAYS ON, AND THE REASON IS NOT THE ONE ON RECORD.** The 11
non-whole-rest fires are not real music either — committed adjudication
(`adjudicated-12-fires.json`, verified against the artefact rather than the
report): **8 eighth-rest hooks from the staff below, 2 noteheads on
neighbouring staves, 1 the top arc of the printed `6` of the `6/8`.** Off puts
11 spurious notes back here and 22 on Litolff. **So the rule does the right
thing for the wrong reason, and "25 of 25, zero real notes" is a LITOLFF
FIGURE that must stop being quoted as its warrant.** Sharper still: the one
real note among the fires is spared by the 2026-09-11 **ownership contest**, a
different mechanism — so even *"zero real notes deleted"* is not this rule's
doing.

⚠️ **The false-negative side, which nobody had ever looked at, found §3 of the
09-11 handoff UN-REPAIRED on this publisher**: the closest of 248 non-fires is
a **real whole rest**, refused because its clipped box reads aspect 1.51
against the 1.63 floor — and exported as an **eighth note C5**. A pitched note
where the page prints silence, which is Sean's original observation.

⚠️ **Priced as a measurement and explicitly NOT recommended:** *the glyph must
stand inside its own staff* takes Litolff 25 → 22 fires (still 22 of 22 whole
rests) and Breitkopf 12 → 1, costing 3 correct Litolff catches and **11 useful
Breitkopf deletions**. Needs a human and a third publisher.

**Dotted rest, at 33× the dot density:** 691 `aug_dot` rows across two
publishers attach to a rest **once**, and that once is a **false dot** — the
smallest of all 656 — on a crop showing an undotted whole rest. Consistency,
not payoff; **an argument that no work should be ranked by it.**

⚠️ **Its meter half was WITHDRAWN mid-flight** per §6, after `89620d27` landed
the same arm on the same document at reach zero. Two arms had run 20 minutes
and were killed **by PID, never by name.**

⚠️ **FINDINGS.md was written by a DIFFERENT session from the one that
measured.** That environment refused both the Write tool and a heredoc, so the
write-up went into the PR body; it was transcribed verbatim into
`benchmarks/omr-second-publisher-pricing-2026-09/FINDINGS.md` before merge,
with a provenance note saying so. **Nothing was re-derived or re-worded.**

---

## 9. WHAT IS WAITING FOR SEAN

1. **`OMR_METER_CARRY`** — ⚠️⚠️ **CORRECTED 2026-09-16: NOT "still off" — ON by
   default since 09-15 (`rhythm.py:1016`, deny-list), so the question is
   whether to KEEP it and widen the form-borrowing rule, not whether to flip.
   And "the experiment that closes it" named below WAS RUN ON 09-15:
   `benchmarks/omr-meter-carry-brahms-2026-09/FINDINGS.md` — carry asked on 5
   of 7 systems, refused on all 5, four exports byte-identical, candidate `4/4`
   never the voted `9/4`. This entry is the §7 pattern a fourth time, in the
   section written to prevent it.** As originally written: still off, and ⚠️ **NOT blocked on a corpus; that
   claim was refuted the same day and §6 carries the correction.** This entry
   said *"nothing on this machine settles it"* while §6 above already said the
   opposite — the document contradicted itself in the section headed *what is
   waiting for Sean*, which is the one most likely to be read as a work order.
   **Where it actually stands:** the blocker is the **form-borrowing rule**
   (the bars reach length 3.0 at +7.0 and cannot SPELL it, because the only
   system to borrow a spelling from is the one that misread `C`), and the
   evidence FOR the flip is now the strongest it has been —
   `local_arm.sh` on Litolff p1-3 takes systems decided **1 of 5 → 5 of 5** and
   bars that add up **54.4% → 81.2%** like-for-like, with **298 wrong→exact and
   0 exact→wrong**. ⚠️ **What is still missing is one CELL, not a document:**
   a **VOTED** misread propagating across many systems. Brahms `p0p3` has the
   voted misread but only 2 systems; Litolff p1-3 runs across a movement but
   its misreads are SUPPRESSED by the coverage gate before the carry sees them.
   **The experiment that closes it is named**: the arm on `p0p3` with
   `--bar-beats 3.0`. See
   `benchmarks/omr-meter-corroboration-2026-09/out/local/RUN_2026-09-16_litolff-p1-p3.md`.
2. **`OMR_WHOLE_REST_INK`** — ANSWERED for the default (**stays ON**, §8) and
   OPEN for the hardening: *the glyph must stand inside its own staff* trades
   11 useful Breitkopf deletions for 11 fewer wrong-reason fires, and **wants a
   third publisher** before anyone takes it.
3. **`Verdict.single_pass_revision` is never serialised** — declared at
   `record.py:835`, read by the fixpoint guard at `:1026`, absent from
   `to_json`. Verified on main. ⚠️ **The recommended repair is NOT the
   `to_json` key** (which changes every record in the tree and breaks every
   byte-identity control) **but making the guard RAISE on a record that cannot
   carry the flag** — today an absent field is read as `False`, which is
   precisely *a fallback converting "cannot tell" into a definite answer*. That
   costs no record change and turns a silent latent into a loud one.
4. The 09-15 handoff's §10 items that remain: the part join, **S6's seventy
   crops**, part order.

---

## 10. WHAT IS NOT ESTABLISHED

**Accuracy, almost everywhere.** It is established only where crops were
adjudicated — the 25 fires and the 26 bars — and even there the verdict is one
reader's against the print, not Sean's. The fourth stage's six added notes,
every roster re-decision, and every wiring finding are **unchecked against any
page**. No OMR-NED figure is claimed for anything here, and for the
note-deleting rule none can be: the metric is symmetric and rewards
under-prediction, so it would pay for those deletions whether or not they are
right.

**n is still 1 for most of it.** The second publisher's record now exists and
has priced two things: the meter flags, to a **reach of zero** (§6), and
`OMR_WHOLE_REST_INK`, whose **cuts do not transfer** (§8). Everything else here
— the fourth stage, the wiring findings, the roster re-decisions — remains
n = 1 document, 4 pages, on the pessimistic end of the corpus. ⚠️ And the
whole-rest result is n = 2 **documents**, 7 pages: it establishes that the cuts
are a property of a plate, **not** how a third publisher behaves.
