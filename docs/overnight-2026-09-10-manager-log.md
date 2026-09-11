# Overnight session log — 2026-09-10 into 09-11

A manager session: one agent at a time, each job merged and verified before the
next is dispatched. Picked up from
[docs/handoff-2026-09-10-three-families-wired.md](handoff-2026-09-10-three-families-wired.md),
executing the remainder of **Phase 1** of
[docs/plan-2026-09-10-wire-first-then-reconcile.md](plan-2026-09-10-wire-first-then-reconcile.md).

⚠️ **This is a LOG, not a findings document.** Every number in it is a pointer
to the arm that produced it. Nothing here is a measurement of its own.

---

## The standing order

Phase 1 wires every remaining decision end to end — adjudicator, emission,
counter — and then **STOPS**. It does not tune. The plan's §2b is the condition
that makes that safe:

> A wiring pass may connect a decision. It may not let one GUESS.

Phase 2 (the first cleanup count on one real movement) is explicitly **not**
this session's work, and its categories must be fixed before anything is
looked at, or the count fits itself to what was found.

---

## 0. The merge that opened the night

`origin/claude/reengraved-fermata-wiring-6958e6` was **18 commits ahead of
main and 0 behind** — a clean fast-forward, landed at `dfc6f409`.

**Verified on the merged tree rather than on the branch's word:**
`python3 -m pytest tools/omr/tests -q` → **3,661 passed, 11 skipped** in 9m18s,
which is the figure that handoff claims to the test. That is the baseline every
job below is measured against; anything under it is a regression.

⚠️ A fast-forward makes the merged tree identical to the branch tip, so this
particular check is cheap. It is run anyway because *measure the MERGED tree*
has been paid for here before.

---

## The jobs

| # | Phase 1 item | branch | state |
|--:|---|---|---|
| 1 | `wedge_anchor` (item 3) | `claude/staged-wedge-anchor` | dispatched |
| 2 | tie CHAIN, `tied_to_next` / `_from_prev` (item 5) | — | queued |
| 3 | `direction` (item 6) | — | queued |

Each entry below is filled in when the job lands, with what it measured and
what it refused.

### Job 1 — `wedge_anchor`

Dispatched with handoff §6 as the brief, and with its one open **stage-boundary
decision** named as the thing to settle before writing code: calling
`_legacy._wedge_anchors` from the exporter is the `_pair_arcs` precedent but
leaves the adjudicator nothing to decide, while deciding in the adjudicator
restates three measured constants unless the legacy function is refactored.

⚠️ Reach is **0 on Litolff and 47 on Brahms**, so Brahms is the only fixture
and a Litolff run would produce a meaningless clean zero. Carried into the
brief explicitly.

⚠️ Also carried: `coverage()` reports this family's `detector_glyphs` as **1**
against **47** rows on the record, because the count is over the DETECTOR's
class space and 46 of the 47 came from the `cv_hairpins` rung. **A family whose
ink comes from a CV reader is under-reported by that headline** — anyone
sizing this work off the coverage report reads its reach as 1. Folded into the
job as a reporting fix rather than left as a footnote.

### Job 2 — the tie CHAIN (`tied_to_next` / `tied_from_prev`)

Dispatched **in parallel** with job 1 on Sean's instruction: a Brahms 4-page
gather is ~45 minutes of pure waiting, and one-at-a-time was costing that time
for nothing. Chosen as the parallel job on a **collision** argument rather than
a priority one — it is the one Phase 1 item that barely touches
`staged/export.py`, because the exporter ALREADY sets both flags
(`staged/export.py:765-766`, from `_pair_arcs`). Job 1 is working in the
`<direction>` / `<wedge>` emission path; these two do not meet.

⚠️ **It runs the OPPOSITE direction from every other wiring item, and that is
its whole hazard.** Everywhere else the record knows something no file carries.
Here the exporter already does the job and the RECORD cannot name it — so the
failure mode is not a missing feature, it is a **decorative quantity**: one
that closes `gather_coverage`'s last two `NO VOCABULARY` entries, reports
green, and is read by nothing. CLAUDE.md already names that shape (*a `wants`
entry the decision never reads is INERT*). The brief sets the bar accordingly:
**the quantity must be READ by something, or the job returns an argued
negative** — and an argued negative was declared an acceptable deliverable up
front, so the agent is not pushed into shipping a green line.

Three things it was told to settle before writing code, not during: what the
SUBJECT of a chain is (a chain is not one arc, and `Q.ARC_KIND` already decides
per-arc); which STAGE owns it (a chain may be *entailed* rather than
adjudicated, which would make it an EVALUATE consequence — and EVALUATE may
not contain a tie-break); and whether `export.py:3282`'s
`tied_to_next=(tied_to_next and ni == 0)` has the **chord-first-member** defect
the fermata work found one week ago in a different function. That last one was
put in as *look, do not assume in either direction*.

**LANDED** — merged at `4ef4a21b`. Suite on the MERGED tree: **3,707 passed /
11 skipped**, matching the branch's claim and +46 over the 3,661 baseline.
`health --check`, `inventory --check`, `gather_coverage` all exit 0.
Findings: [benchmarks/omr-staged-wedge-2026-09/FINDINGS.md](../benchmarks/omr-staged-wedge-2026-09/FINDINGS.md).

`<wedge>` **0 → 20** on Brahms, byte-identical outside the wedge elements,
music21 reading back exactly 20. **46 of 47 decided, 1 abstained
`no_page_frame`** — and that one is precisely the box-less `detector` row, so
the abstention branch is exercised by the page rather than merely defended.
**`stubs()` is now `('direction',)` — one left.**

⚠️ **Its own report of what it got wrong is the most useful part**, and two
items are worth carrying:

* **A `wants`-shaped ordering bug that NO behavioural test could have found.**
  Placed beside the fermata in `ORDER`, `wedge_anchor` ran *before* `Q.VOICES`
  and read `None` every time — and *"one voice"* and *"voices unknown"* give
  the same answer on every one-voice page, so the page cannot tell them apart.
  `inventory --check` caught it. That is the *silent arbiter* shape arriving in
  a new place: **the test that would distinguish the two readings is the one
  the corpus cannot supply.**
* **A byte-identity control that was VACUOUS and nearly shipped.** Exporting
  three committed transcriptions before/after matched — and `grep -c '<wedge'`
  on all three is **zero**, so the code never ran. This is CLAUDE.md's second
  family (*a control that was never testing what its name says*) for the eighth
  recorded time. Replaced with a probe that drives the function directly and
  prints how many cases ANSWERED (10 of 12) as its own positive control.

⚠️ It also shipped and then found **its own accounting bug**: a per-part head
index made *"not in this part"* and *"never written"* the same condition, so
ten decided hairpins were counted by nobody while the balance reported
`True` — **because it had been written as `<=`**. The previous session's
warning (§2 of the three-families handoff: relaxing the balance to an
inequality would have shipped a real bug) **came true within a day, in a new
counter, written by someone who had read the warning.** It is now an exact
equality: 20 + 26 = 46.

⚠️ Its mutation battery paid **twice** — 9 of 19 arms not red on the first run
(2 mis-anchored onto `arc_owner`, 1 equivalent mutant, **6 genuine gaps**), and
it caught more again after the repair. Final: 21 arms red, positive control
red.

#### A hazard it found in passing, recorded and deliberately NOT fixed

The Brahms record is stamped `e3d0d455, dirty: false` — **a commit that did not
exist when the run began.** `_provenance()` reads git at the END, so a long
gather started on tree A and finished on tree B is stamped B, and **a clean
stamp is no evidence the tree was clean while the page was read.**
`regather_control.py` compares exactly those stamps to decide whether two
records may be compared. Queued as its own job: fixing it means stamping at the
START as well, and whether a mismatched pair should then REFUSE is a decision
rather than an edit.

### Job 3 — `direction` (the LAST declared stub)

Dispatched off `9f1ea83e`, in parallel with job 2. Job 1's `<direction>`
emission work is already IN main, so the collision that kept this item back
earlier tonight no longer exists.

⚠️ **It is two jobs, not one**, which is why it was left for last:
`Q.DIRECTION_WORD` is the last input-starved quantity on the record, so the
gatherer must be written as well as the adjudicator. The READING half already
exists on the legacy path (`direction_text.py`, default-on, gated on a
181-word musical lexicon that CLAUDE.md marks *never loosen*) and the brief
forbids rebuilding it.

**The one line that matters most in that brief** is CLAUDE.md's own governing
rule, because this family walks straight into it: the direction reader
**self-disables where neither `.venv-surya` nor Tesseract exists**, so

> A fallback must never convert *"cannot tell"* into a definite answer.

An unavailable OCR rung gathering zero words is otherwise indistinguishable
from a page with no words printed on it. Making those two states
unrepresentable-as-one is the acceptance condition, ahead of any coverage
figure.

Three hazards measured in the last 24 hours were carried in by name, because
each has already cost someone a re-run: **ORDER placement** (a decision reading
`None` from a quantity settled later, which no page can detect); **a
byte-identity control passing while the code never runs**; and **a mutation
battery anchored on a fragment that occurs three times**, silently mutating a
different function. The `<=` balance warning was repeated in the strongest
terms available — it has now been ignored once by someone who had read it.
