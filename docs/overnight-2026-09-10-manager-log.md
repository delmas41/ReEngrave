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
