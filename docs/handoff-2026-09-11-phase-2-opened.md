# Handoff — Phase 2 opened, five of seven observations answered

⚠️ **Written at a hard stop**: Sean hit his weekly usage cap at 98%, with three
jobs in flight. **Everything merged below is verified; everything in §6 is
UNVERIFIED WIP preserved on a branch.** Read §6 before resuming anything.

Predecessor: [docs/handoff-2026-09-10-three-families-wired.md](handoff-2026-09-10-three-families-wired.md)
(Phase 1). Plan: [docs/plan-2026-09-10-wire-first-then-reconcile.md](plan-2026-09-10-wire-first-then-reconcile.md).
Session log with the dispatch reasoning:
[docs/overnight-2026-09-10-manager-log.md](overnight-2026-09-10-manager-log.md).

---

## 1. WHAT HAPPENED — the calibration page did its job by STOPPING the count

Phase 1 closed (`adjudicate.stubs()` is `()`), the first cleanup artefact was
built, and **Sean read one page against the print and declined to count**:
*"we are pretty far off and need to do some more work before any calibration or
more pages."*

⚠️⚠️ **That is the instrument working, not failing.** The plan fixes the
categories first precisely so a count taken over output this wrong would be
measuring the WIRING. **No cleanup count exists and none should be quoted.**

He gave seven observations. They were worth more than a total, because five of
them named a MECHANISM rather than a quantity.

---

## 2. THE SEVEN, AND WHERE EACH STANDS

| # | Sean, from the print | state |
|--:|---|---|
| 1 | time signature is correct | ✅ nothing to do |
| 2 | key sigs: **3 flats** except **Cl. 1 flat**, **Tr/Cor none** | ✅ REPAIRED — file grade **33 → 44 of 75** |
| 3 | whole rests worth 2 beats show as a single quarter **NOTE** | ⚠️ **HALF DONE — see §3, the manager mis-paraphrased this** |
| 4 | almost no ties or slurs convert | ✅ REPAIRED — `<slur>` **32 → 40**, `<tied>` **84 → 91** |
| 5 | none of the measure math makes sense | ✅ DIAGNOSED + partly repaired — **one missing function argument** |
| 6 | doubled notes, two of the same note on one stem | ✅ REPAIRED — notes **1,793 → 1,618** |
| 7 | page prints only `ff`; ours has extra `f`s | ✅ REPAIRED — `ffff` **11 → 2** |

**Suite: 3,805 → 3,829 passed / 11 skipped**, every merge verified on the
MERGED tree, `health` / `inventory` / `gather_coverage` / `export_coverage` all
0 at every landing.

---

## 3. ⚠️⚠️ THE ONE THAT IS STILL OPEN, AND WHY — READ THIS FIRST

Sean wrote *"showing up as a single quarter **note**"*. **The manager briefed it
as a quarter REST.** The rest-sizing job then proved — rigorously, box aspect
separating with an empty interval, **0 of 209 overlapping** — that our quarter
rests ARE genuinely quarter rests. **A correct answer to a question Sean never
asked.** He corrected it:

> *"in bars where it should be just whole note rest in two four. It's showing
> an actual quarter note, not a quarter note rest."*

**Measured, current tree, one re-export of the shared record:**

| | |
|---|--:|
| bars whose ENTIRE content is one **PITCHED** note | **118** |
| ...of which UNDERFULL | **44** |
| ...of which a lone **QUARTER** in a 2/4 bar | **26** |

Named: `P1 m45 C5`, `P1 m85 D5`, `P1 m88 D5`, `P1 m89 D5`, `P2 m49 F5`,
`P2 m87 A5` — each `duration=96` against a bar of `192`.

⚠️ **A pitched note standing where the page prints silence is a DIFFERENT fault
from the mis-sized rest that was repaired**, and it is worse than a missing
note: a wrong note must be found and deleted, a missing one is visible as a
gap. **Unrepaired.** A job was dispatched and stopped mid-flight (§6).

⚠️ The hypothesis to KILL rather than confirm: in 2/4 a silent bar takes one
centred WHOLE REST — a small filled rectangle under a line — and a notehead is
a small filled oval, so they are confusable ink. The arc work found the MIRROR
on this same document: a `restWhole` at 0.56 *"where no whole rest exists"*.
⚠️⚠️ **Five of the six Phase 2 jobs refuted the mechanism their brief proposed.
Assume this one is wrong too.**

---

## 4. WHAT WAS REPAIRED, AND THE ONE FINDING EACH

### obs. 6 + 7 — a CONTEST is RESOLVED, not relocated (`e98338cf`)

⚠️ **The manager's hypothesis was right about the symptom and WRONG about the
mechanism.** There is no missing dedupe pass: `adjudicate_glyph_owner` runs on
every contest and gets **245 of 248** notehead pairs to agree. What was missing
is that **nothing consumed the verdict as a RESOLUTION** — both consumers
honour ownership by MOVING the copy, and both copies name the same owner, so
one piece of ink arrives twice on one staff in one bar. **688 of 1,386
ownership verdicts relocate and every one doubles.** `ffff` **IS** one printed
`ff` — 21 of 21 long words trace to an overlapping pair, no residue.

⚠️ **`ff` 47 → 39 is an unadjudicated COST, not a win** — only the print can
say whether those eight were one `f` seen twice.

### obs. 2 — key signatures against a hand-read truth (`2c07f225`)

⚠️ **NOT a clef problem**, which is what the brief asked: **68 of 75 clefs
correct**, and **all ten wrong key readings sit on a correctly-read clef**.

⚠️⚠️ **The biggest cause was a fourth mechanism nobody named: ELEVEN HEADER
CROPS CONTAINED NO CLEF AND NO KEY SIGNATURE AT ALL.** `system_left_edge` takes
the **MINIMUM** of one estimate per staff, one staff under-ran its ten siblings
by 70 px, and it set the window for the whole system. **One cause, two
different failures**: the locator abstained; the template found a "clean
window" and answered a confident `fifths: 0` — **a key signature fabricated
from an empty crop**, which is *a fallback converting "cannot tell" into a
definite answer*.

⚠️ **The tree is narrower than that job's own summary and the tree is right**:
the under-run is NOT repaired, only its consequence. The direct clamp was
measured and refused (3 correct lost for 6 new wrong).

### obs. 4 — arcs (`8b552a9e`)

⚠️⚠️ **THE BRIEF'S PREMISE WAS INVERTED: the detector is LONG on arcs, not
short** — **721 merged groups against 411 encoded curves**. A session starting
from "detect more arcs" goes the wrong way.

The 550 refusals split four ways and the brief's lead was the **smallest**:
376 have heads in the bar but none under the arc, **108 had nothing read in
those bars at all**, 66 are heads the exporter held back. ⚠️ One crop prints a
slur over **six legible noteheads** and the record holds **no notehead** for
that bar.

Repair: **an arc is drawn to a STEM, not a notehead** (median 0.52 notehead
widths) — the `_beam_levels` shape again, and **`Q.STEM` was gathered and read
by nothing on this path, 1,920 rows, the THIRD instance.**

### obs. 3 (the rest half) + 5 — the meter, and one missing argument (`3a725f07`)

**Rests**: `size_measure_rest` has **no fault**; it is the meter, and the
cross-tab is an **empty interval** — on the one system whose meter is DECIDED,
**92 of 92** eligible bars are sized; on the six that abstain, **0 of 195**.

⚠️⚠️ **What Sean's eye was reporting, and nothing in the pipeline was checking:
only 38.0% of 1,183 bars sum to the `<time>` the same file declares.** (The
manager reproduced it independently at 37.8%.) With `OMR_METER_CARRY` on it
goes to **69.2%** and unsized bars 168 → **0**. **RECOMMENDED, NOT FLIPPED —
a default is Sean's.**

**Measure math**: one defect, and it is **a missing function argument**.
`run_staged` took `pdf_path`, rasterised with it and **DROPPED it**, so
`margin_label` filed **75 abstentions on every staged run ever made** →
`instrument` 75/75 `no_evidence` → `slot_index` falls to the ordinal →
`part_partition` joins systems of **12, 11 and 8 staves BY POSITION**. That is
the key-signature session's *"12 of 75 joined to the wrong instrument"*,
reproduced from the measure math, **P7 Timpani holding the VIOLA's staff**
included. Partition balances exactly: `8×111 + 3×93 + 16 = 1183`, 0 unexplained.

⚠️ **The obvious repair is REFUSED with a reason**: a CORRECT join gives
**111/93/78/31**, so the eight parts reading 111 today read 111 **BECAUSE of
the graft**. Padding must follow the join and the numbering, or it hides wrong
notes behind right numbers.

---

## 5. ⚠️ THE DECISIONS WAITING FOR SEAN

1. **`OMR_METER_CARRY` — flip it ON?** 6 of 7 systems, supports +6…+18 against
   a floor of 2.0; bars that add up **38% → 69%**. Against: n = 1 document in a
   constant 2/4, and the standing Breitkopf objection is untouched *because
   this document cannot touch it*. **Cheapest thing that settles it: the same
   arm on Breitkopf Brahms 1 p0-3.**
2. **The part join costs 12 parts → 75 fragments on a FRESH gather.** Taken
   deliberately — *the graft is silent, fragments are loud* — **one predicate
   to revert**. ⚠️ Three states, not one: the old record still exports 12 parts
   (ADJUDICATE change, replay replays saved verdicts); a fresh default gather
   gives 75 fragments; **a fresh `--surya` gather ALSO gives 75**, because 50
   slots carry reason `named` and **the value is still the ordinal on all 75**.
   **The label reaches the record and does not reach the slot — that is the
   slot-index job.**

---

## 6. ⚠️⚠️ THREE JOBS STOPPED MID-FLIGHT — UNVERIFIED, PRESERVED, DO NOT MERGE BLIND

All three were killed at the usage cap. Their work is committed as **WIP on
their own branches** rather than lost with the worktree. **None has a passing
suite, a control, or a mutation battery. Re-run everything before trusting a
line of it.**

| branch | what it was doing |
|---|---|
| `claude/slot-index-by-name` (3 commits) | **the ranked next work** — §5.2 |
| `claude/arc-grammar-sean-rules` (1, WIP) | Sean's S1-S6 tie/slur rules |
| `claude/note-where-silence-is-printed` (1, WIP) | §3, the open observation |

### 6a. The slot index — start here

`adjudicate_slot_index`'s docstring **states in bold** that a short system
pairs by instrument NAME and abstains where unread. ⚠️ **The function contains
no such branch and returns the ordinal on every path.** A documentation shape
worse than a stale claim, because it reads as a claim about the code in front
of you. **Make the code true.**

The anchors are on the page: p3/s1 reads `Fl. Cl. Fag. Cor.` — **no `Ob.`** —
the print naming its own suppression exactly where the graft is. Reach: **50
labels over 75 staves**, 12 of 12 on the opening system.

⚠️ **The failure mode is measured**: the whole-work run's 7 residual errors are
an **off-by-three in this very monotone DP** (12 staves against a 17-slot
reference deleted 12/13/14 instead of 9/10/11), and `OMR_SPAN_REFERENCE_FIT` is
a 149-staff regression from the same path. ⚠️ **`p4/s0` vs `p4/s1` is
untouched** — 11 staves each, different lineups, equal-count branch accepts it,
**5 of the 12 grafts live there**.

### 6b. Sean's tie-vs-slur rules — recorded verbatim

`benchmarks/omr-arc-grammar-2026-09/SEAN_ARC_RULES.md`. **S2 and S5 exist as
`OMR_ARC_RECLASS` and are measured and REFUSED** (scan +149 edits) — but the
recorded reason is about S5's INPUT, not the rule: *a scan's resolved pitch at
an arc's ends is downstream of exactly what scans get wrong*. ⚠️⚠️ **S4 (the
stem's far edge) and S6 (stacked arcs: lower tie, upper slur) are implemented
NOWHERE, and they read GEOMETRY rather than resolved pitch — which is exactly
what makes them viable where the refused version is not.**

---

## 7. SEAN'S STAGE RULING — where the IMSLP roster belongs

> *"Does adjudicate take into account the instrument list from IMSLP? or should
> that happen in a different stage, like INFER?"*

**ADJUDICATE takes the roster; INFER does not need it.** A roster is evidence
about ONE thing, and ⚠️ **the structural argument is CLAUDE.md's own doctrine**:
*if you want a second witness that does not fall silent exactly when it is
needed, it must not come off the same raster.* The roster is
`source_kind: "catalog"` and **does not go silent when the scan is bad** —
which is what makes it ordinary evidence rather than something needing to be
weighed. INFER is for correlated witnesses and the residue, **after** the first
cleanup count.

⚠️ **It is NOT required for the slot index** — that rule is a monotone
alignment of read names, deterministic.

⚠️⚠️ **A SECOND MISSING PRODUCER, FOUND WHILE ANSWERING THIS.** `pipeline.py`
threads `roster` through both entry points and **`staged/__main__.py` has no
roster argument at all**, so nothing can supply one. **Second instance in two
days of a parameter threaded end to end with no producer** — the first cost 75
staves their margin labels on every staged run ever made. **Worth a derived
check rather than a third discovery.**

---

## 8. RANKED NEXT WORK

1. **`adjudicate_slot_index`** implements its own docstring (§6a) — unblocks
   the join, the key-signature cross-system vote, and probably some arcs.
2. **The pitched note where silence is printed** (§3) — the only unanswered
   observation, and the worst kind of error to ship.
3. **Number a measure by the document's bar sequence**, not the part's running
   count — makes `<measure number=N>` name one instant.
4. **Pad the tacet spans** — REST path, and **only after 1 and 3**.
5. **A derived check for parameters with no producer** (§7).
6. Sean's S4/S6 arc rules (§6b).
7. Re-price `OMR_METER_CARRY` on Breitkopf Brahms 1 (§5.1).

---

## 9. OPERATIONAL — measured this week, not guessed

* ⚠️⚠️ **A re-export of a saved record shows EXPORT-stage changes ONLY.**
  Verified three times: the dedupe repair's note half appeared (1,793 → 1,618)
  and its dynamics half did not; the part-join refusal does not appear at all.
  **An agent reporting "my change did nothing" off a re-export may be reporting
  the instrument.** ADJUDICATE needs `readjudicate.py` (~18 min/arm on this
  record); GATHER needs two full re-gathers.
* **The 132 MB record is gitignored** and was living inside one agent's
  worktree. Staged READ-ONLY at
  `library/_shared-records/beethoven5-p1-p4.record.json`
  (md5 `d3620ba9cb70fc93f6b7ee91b6cbe40a`).
* ⚠️ **zsh does not word-split unquoted variables** — `python3 -m tools.omr.$c`
  with a flag in `$c` fails as one module name and looks like a real failure.
  The manager hit this and briefly reported three green checks as FAILING.
* ⚠️ **The manager's own probe of §3 returned `n=0` on both arms** because it
  guessed the record's schema — *a dead instrument wearing a clean zero*. The
  real top level is `record / summary / adjudication / agreement / evaluation /
  stubs / provenance`. **Print a positive control before any zero.**
* **Parallel agents sharing `staged/export.py` worked** when ownership was
  assigned by PATH (rest / arc / part) and each was told who else was in the
  file. Two CLAUDE.md conflicts, both purely additive, both resolved by keeping
  both sections.
* ⚠️ **The Write tool refuses to let a subagent create `FINDINGS.md` in a
  benchmark directory.** One job lost its narrative to this and the manager
  wrote the file from its report. **Tell agents to return the narrative in
  their report if the write fails.**

---

## 10. THE PATTERN OF THE WEEK

⚠️⚠️ **FIVE OF SIX PHASE 2 JOBS CAME BACK BY REFUTING THE MECHANISM THEIR BRIEF
PROPOSED**, and in every case the refutation was worth more than the repair:

* "there is no dedupe pass" → there is; **nothing consumes its verdict**
* "this is a clef problem" → **68 of 75 clefs are correct**
* "we don't detect enough arcs" → **the detector is LONG, 721 against 411**
* "the slot join cannot help" → **it is not passive, it is ACTIVE AND WRONG**
* "the quarter rests are mis-sized" → **they are quarter rests; the fault is a
  pitched NOTE**

**Brief the mechanism you believe, say plainly that refuting it is a
first-class result, and make the agent measure before it builds.** That is what
produced every finding in this handoff.
