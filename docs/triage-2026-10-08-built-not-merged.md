# Triage of the roadmap's "built, not merged" rows (2026-10-08, ROADMAP 0.8)

**Question (Sean):** sort the roadmap rows that say "built, not merged".
**Method (rule 10, the tree outranks every ledger):**
1. Took every open Phase 2/3 row (status not `done`, `todo` or `dropped`): 83 rows naming 72 branches.
2. Fetched the full history (the cloud clone is shallow) and every `origin/*` branch.
3. Ran `git merge-base --is-ancestor <branch> origin/main` and `git cherry origin/main <branch>` on each one.
4. For each branch that IS on main: found the first `main` commit containing it, checked that this merge was not empty, and checked that the functions it added are still defined on `main`.
5. Checked the flag defaults on `main` (deny-list or allow-list) for the flags these rows name.

Nothing was re-gathered, re-adjudicated or run: this is a ledger-vs-tree check, not a measurement.

**Base:** `origin/main` 6e96227b.

## Result

| bucket | rows | what it means |
|---|---|---|
| **A. Already merged, row says "not merged"** | 41 | Every one landed through a real merge (most on 2026-09-29, the rest on 10-01 to 10-07). Their functions are on `main` (spot checks: `execution_order`, `_body_reads`, `Q.PRINTED_BAR_NUMBER`, `Q.TIE_PAIR`, `_trailing_cell_is_cautionary_only`). The row text was simply never updated. |
| **B. Not on main, superseded** | 4 | 2.21 first draft, 2.44, 2.44c, 2.44d |
| **C. Not on main, dead at zero** | 2 | 2.6h, 3.2c |
| **D. Not on main, evidence only (no reader code)** | 2 | 2.51, 2.53 |
| **E. Not on main, parked by Sean** | 1 | 2.48 (unchanged) |

Bucket A rows now carry a bold `MERGED to main (<sha>, tree-verified 2026-10-08)` prefix. The lane's own text after it is kept as written, because it is the measurement record. The words "merged" and "done" are kept apart on purpose: a merged row whose item still has an open question stays open until Sean closes it.

### A. Merged (prefix added, nothing else changed)

2.3b, 2.6d, 2.6e, 2.6f, 2.10b, 2.12i (merged as a measurement; still not promoted), 2.13, 2.18, 2.18b, 2.18c, 2.19, 2.22, 2.23, 2.24 (diagnosis), 2.25, 2.25b, 2.26, 2.26b, 2.27, 2.27c, 2.27d, 2.30, 2.33, 2.34, 2.47b ×2 (via `lane-2.47bc-finish`, `deaa4fbc`), 2.56, 2.56b, 2.56c, 2.57, 2.57b, 2.57c, 2.58c, 2.58d, 2.59 ×2, 2.60, 2.62, 2.63, 2.64, 3.2b.

Flags named "OFF" in those rows that are **default ON on main today**:
- `OMR_CELL_LINE_FIND`
- `OMR_OWNER_FROM_STAVES`
- `OMR_FARHEAD_OWNER_LEDGERS`
- `OMR_MARK_GROUPS`
- `OMR_DOT_FOLLOWS_NOTE`
- `OMR_STEM_OWNER`

`OMR_RELOCATE_AT_EXPORT` stays OFF (parked, Sean 10-07).

### B to D: the nine rows that are genuinely not on main

| row | branch | unique commits | recommendation | why |
|---|---|---|---|---|
| 2.21 (first draft) | `claude/voice-split-2.21` | 2 | **superseded** | 2.21b, built on Sean's own convention, is merged (`ee7f303b`). |
| 2.44 | `claude/affectionate-mendeleev-db20a1` | 1 | **superseded** | Option B was stopped and its rescue branches were retired by Sean on 2026-10-06 (DECISIONS). Far heads now go through the note-first reader. |
| 2.44c | `worktree-agent-ac053ee5c8a371951` | 10 | **superseded** | Carries 2.44's option-B wiring; retired with 2.44. |
| 2.44d | `lane-farhead-combined` | 34 | **superseded** | The note-first reader beat plain geometry 10:1 on Sean's tiles (DECISIONS 10-08). The ledger-rung rounds this branch carried landed separately (`990ea5ba`). What is unique to it is the comb (2.48, parked) and the OFF combined-position wiring. |
| 2.6h | `claude/no-ink-head-2.6h` | 1 | **drop** (Sean to confirm) | Dead at zero: 0 of 2,497 heads refused. Its GATHER half was ported by 2.23. |
| 3.2c | `claude/tie-chords-3.2c` | 1 | **drop** (Sean to confirm) | Dead at zero: 0 chord pairings on both scans. |
| 2.51 | `lane-2.51-unboxed-ink` | 2 | **land the evidence** | Scripts, FINDINGS §14 and two contact sheets; no reader code. It led to 2.52. |
| 2.53 | `lane-2.53-unboxed-bars` | 1 | **land the write-up + sheets only** | The branch also rewrites `benchmarks/acceptance/quick/` outputs, which must not overwrite main's. It led to 2.55. |
| 2.48 | `lane-2.48-seeded`, `lane-2.48-pinned` | 14 / 15 | **leave parked** | Sean 10-01: "park, do not forget". |

Nothing is dropped or retired by this triage. Those are Sean's calls, and each needs its own DECISIONS line. The branches stay on origin either way.

## What the triage changes about the backlog

The "about 30 built-not-merged rows" in the 2026-10-08 overview were not a merge backlog. Forty-one of them had already landed. The real open work hiding under those rows is the question each one still carries (an ASKED half, an unpriced wiring, a missing print check). The next step is a per-row close-or-keep pass with Sean, not a merge pass.

## Rows that still name no branch

These are open for other reasons and were not touched:

| row | what is holding it open |
|---|---|
| 1.1 | records exist; regather pending |
| 1.4 | the count was done by a session, not by Sean |
| 2.5 | blocked on 2.4 |
| 2.16 | parked |
| 2.20 | diagnosed |
| 2.28 | parked |
| 2.38c | diagnosed |
| 2.41 | measured |
| 3.3 | web-app engine switch |
