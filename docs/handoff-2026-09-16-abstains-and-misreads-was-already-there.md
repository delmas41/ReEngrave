# The document that abstains and misreads was already in the corpus — merged, and what's left

**2026-09-16 (later).** Short pointer, not a session narrative — the narrative
is [PR #39](https://github.com/delmas41/ReEngrave/pull/39)'s own body and
`benchmarks/omr-meter-abstain-and-misread-2026-09/FINDINGS.md`, both now on
main. This doc exists because
[docs/handoff-2026-09-16-the-fourth-stage-and-the-second-publisher.md](handoff-2026-09-16-the-fourth-stage-and-the-second-publisher.md)
closed §6 with a claim PR #39 refuted the same day, and CLAUDE.md's own rule is
that a refuted claim gets corrected **at its site**, not superseded silently by
a newer doc further down the chain. Both are corrected now; this is the pointer
between them.

## What changed

`p0p3` (Breitkopf Brahms 1 mvt 1) has both halves of the `OMR_METER_CARRY`
hazard — abstains, and misreads — in 11 of 11 committed arms across 5
generations, found by re-reading **105 already-committed meter records**.
Nothing was gathered. `system/0/0` reads `C` (4/4) where the dossier says 6/8;
`system/3/0` abstains, carried from it, and is refused by the bars at support
−8.0.

**Verified independently before merge, against the raw records, not the PR's
own prose**: `find_fixture.py` re-run from scratch reproduces the committed
output byte-for-byte; the CARRY and BARS verdicts for `system/3/0`
(`m7p0p3-CARRY.meter.json` / `m7p0p3-BARS.meter.json`) match the quoted
numbers to the decimal; the dossier's `6/8`, 513 measures, one bar of 9/8 at
m8 checks against `data/dossiers/brahms-sym1-mvt1.json`; the mutation battery
is 5 arms red with a passing positive control. Touches zero files under
`tools/` — CLAUDE.md, PROJECT_BRIEF.md, version_memory.md, and one new
`benchmarks/` directory.

⚠️ **It does NOT price the flip, and does not narrow to "gather a third
document."** The new blocker is sharper than a missing corpus: the bar
arithmetic already names the correct length (3.0 = 6/8) on the fixture the
flag was waiting for, and abstains `bars_name_a_length_without_a_form` because
the only system it could borrow a *spelling* from is the one that misread
`C`. **The misread poisons the borrow.** Borrowing a form from the dossier
instead is INFER-shaped and is not proposed here.

## What's still waiting for Sean, unchanged by tonight

Carried forward from the 09-15 and 09-16 handoffs, none of it touched in this
pass:

1. **`OMR_METER_CARRY`** — still off. The flip is his; the question it's
   waiting on has moved from *"does a fixture exist"* to *"is refusing to
   borrow a poisoned spelling the right call, or should the form-borrowing
   rule widen."*
2. **S6's seventy crops** — the arc-grammar witness that's recorded but not
   gated, cheap enough to settle by eye.
3. **Part order** (stranded fragments write first) and **`Bass voice` at
   slot 11** — both now reaching real files, neither repaired.
4. **`OMR_WHOLE_REST_INK` hardening** — wants a third publisher before anyone
   takes the *"glyph must stand inside its own staff"* trade.

## Session state

Worktree clean, on `origin/main` (`4c36ef24` at merge), nothing uncommitted,
nothing of this session's running. `git log --all -S` and `origin/main` were
checked before every dispatch in this pass, including this one — PR #39 was
found in exactly that check, seconds before it would otherwise have been
re-measured.
