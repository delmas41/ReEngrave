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
