# Worktree prune survey — 2026-09-06

**NOTHING WAS REMOVED. This is a survey. Sean decides what goes.**

The doctrine this obeys is `395e2193`'s: an agent's cleanup destroyed another
agent's multi-hour run, and what came out of it was **an orphan you cannot
identify is safer left alive**. Every row below therefore defaults to
NEEDS A LOOK unless something positive says otherwise, and three worktrees are
IN USE by processes that were alive while this was being written.

## Headline

| verdict | count |
|---|--:|
| **IN USE** — a live process or session holds it | **4** |
| **NEEDS A LOOK** — unmerged commits, or irreplaceable work on disk | **24** |
| **SAFE** — branch fully merged into main, nothing uncommitted found | **80** |

108 linked worktrees plus the main checkout — **not the ~25 the handoff
estimated**. `.claude/worktrees/` has 108 entries and `git worktree list` agrees
to the row; `git worktree prune` reports none prunable, so every one of them is
a live registration, not a stale record.

## ⚠️ The finding that matters: "merged into main" is NOT a safety test

The handoff said *"pruning ones whose branches are already in main is safe."*
**That rule would have destroyed 7,000 hand-cut cell PNGs.**

Six worktrees whose branches are **fully merged into main** hold cell images
that exist nowhere else:

| worktree | branch in main | cell PNGs held |
|---|---|--:|
| `weight-generalization-publishers-548504` | yes | **4,862** |
| `transcription-overnight-progress-426c90` | yes | 1,008 |
| `scan-weights-round4-continue-074940` | yes | 460 |
| `phase2-hollow-labeling` | yes | 448 |
| `epic-chatterjee-9e8c7d` | yes | 122 |
| `pdf-mxl-pipeline-test-46269e` | yes | 100 |
| | | **7,000** |

Three further worktrees hold cells and are *also* unmerged, so the merge rule
would not have reached them: `reengraved-scanned-weights-175fce` (1,704),
`agent-a451bd979ce2a9210` and `agent-aa1bd00566c677d4c` (252 each). **9,208
across all nine.**

Worked example, and the reason this is not theoretical:
`weight-generalization-publishers-548504` holds
`benchmarks/omr-labeling-grace1-2026-09/cells/` and `…grace2…/cells/`. Both
batches' `cells.json`, `detections/` and `verdicts/` **are** committed on main —
so the branch is genuinely, fully merged. But `benchmarks/omr-labeling-grace1-2026-09/`
**in the main checkout has no `cells/` directory at all**. The images are in that
worktree and in no other tree on this machine.

**The mechanism is that the two facts are about different things.** Merge state
is a statement about COMMITS. `cells/` is gitignored *by design* — CLAUDE.md
says so, because the PNGs are large and were meant to be reproducible — so it is
invisible to every merge check, and a fully-merged branch tells you nothing
about it.

⚠️ **"Reproducible" is weaker than it sounds, and that is the whole risk.**
`tools/omr/annotate/recut_cells.py` exists precisely to re-cut a checked-out
batch's missing images, so these *may* be recoverable. But it derives the cut
mode by matching the manifest's own `cell_canonical_w/_h` and
`staff_line_ys_canonical`, and **aborts the batch on a frame mismatch** — that
guard exists because phase 1 has drifted. CLAUDE.md records the drift having
already bitten: of v8's 122 source PNGs, **11 still existed** when it was
measured. So the honest status is *probably recoverable, not certainly*, and
that is not a standard on which to delete 4,862 images.

**If these worktrees are to be removed, re-cut or copy `cells/` out first, and
verify the re-cut succeeds rather than assuming it.**

## Method, and what it could NOT determine

Run from an isolated agent worktree, so `git -C <other worktree>` and
`cd <other worktree> && git` are both refused by the harness. Everything below
was therefore asked of the **shared object database** from this worktree, or of
the filesystem directly:

- **branch + HEAD + lock**: `git worktree list --porcelain` (the `locked` line
  carries the owning agent's pid).
- **merged into main**: `git merge-base --is-ancestor <head> main`; for the
  unmerged, `git cherry main <head>` splits genuinely-new commits (`+`) from
  patch-equivalent ones already in main (`-`). The `+` count is what the table
  reports.
- **liveness**: the CCD session list, cross-checked against `ps -p` on each
  worktree lock's pid.
- **irreplaceable work**: the worktree's committed file set from
  `git ls-tree -r <head>`, differenced against what is actually on its disk,
  restricted to `benchmarks/**/verdicts/*.json`, `data/user-labeled/**`, and
  `benchmarks/**/cells/*.png`.

⚠️ **`git status` could not be run inside any other worktree**, so ordinary
working-tree dirtiness — an edited `tools/omr/*.py` that was never committed —
is **UNVERIFIED for every row**. That is a second reason no row should be
removed on this survey alone: run `git -C <path> status` per worktree before
removing it. The `dir mtime` column is a weak proxy only; 23 of the 80 SAFE rows
contain files newer than their own HEAD commit, which may be build products
(`__pycache__`, fixtures) or may be uncommitted edits, and this survey cannot
tell those apart.

## IN USE — do not touch

Three worktrees carry a `git worktree` lock held by **pid 61864, confirmed alive
by `ps` during this survey** — sibling agents running right now:
`agent-a0569405039ef1349` (this one), `agent-ab5241e2aaf9a4278`,
`agent-abe066cff5c6c7283`.

The fourth is `project-progress-dashboard-3fb8e2`, held by session
`local_52073ef5` *"Fix `Tp.` resolving to Trumpet, not Timpani"*, reported
**running**, on branch `claude/agitated-bassi-e3a0ab` — which carries **two
commits not in main** (`5d6e76a8`, `4858594e`, the timpani fix and its own
scoping correction). Removing this would discard live, unlanded work.

⚠️ **A stopped session is not the same as an abandoned worktree.**
`distracted-hugle-218685` shows `isRunning: false`, but its branch
`claude/missing-dashboard-session-1f98a0` holds `cbdb5f8f` — the handoff
document itself — which is not in main. It is filed NEEDS A LOOK, not SAFE.

---

## Full table

Sorted IN USE → NEEDS A LOOK → SAFE, then by name. `in main?` shows `+N` = N
commits not in main (patch-equivalent commits already excluded).

### IN USE — 4

| worktree | branch | in main? | uncommitted cell PNGs | verdict json | dir mtime | why |
|---|---|---|--:|--:|---|---|
| `agent-a0569405039ef1349` | `worktree-agent-a0569405039ef1349` | yes | — | — | 2026-09-06 13:13 | git worktree lock held by LIVE pid 61864 |
| `agent-ab5241e2aaf9a4278` | `worktree-agent-ab5241e2aaf9a4278` | yes | — | — | 2026-09-06 13:13 | git worktree lock held by LIVE pid 61864 |
| `agent-abe066cff5c6c7283` | `worktree-agent-abe066cff5c6c7283` | yes | — | — | 2026-09-06 13:14 | git worktree lock held by LIVE pid 61864 |
| `project-progress-dashboard-3fb8e2` | `claude/agitated-bassi-e3a0ab` | **no, +2** | — | — | 2026-09-06 13:12 | local_52073ef5 'Fix `Tp.` resolving to Trumpet, not Timpani' — RUNNING |

### NEEDS A LOOK — 24

| worktree | branch | in main? | uncommitted cell PNGs | verdict json | dir mtime | why |
|---|---|---|--:|--:|---|---|
| `agent-a2daedd6d0b11d266` | `claude/roster-wholework-2026-09` | **no, +7** | — | — | 2026-09-06 00:41 | 7 commit(s) NOT in main |
| `agent-a33465d4058896096` | `claude/structure-rnd-2026-09` | **no, +13** | — | — | 2026-09-05 10:39 | 13 commit(s) NOT in main |
| `agent-a451bd979ce2a9210` | `claude/arc-anchor-round9` | **no, +14** | 252 | — | 2026-09-04 21:45 | 14 commit(s) NOT in main; 252 uncommitted cell PNGs (gitignored by design, NOT regenerable) |
| `agent-a844d0d7ab60d639c` | `claude/staff-identity-labels-2026-09-05` | **no, +2** | — | — | 2026-09-05 03:07 | 2 commit(s) NOT in main |
| `agent-aa1bd00566c677d4c` | `worktree-agent-aa1bd00566c677d4c` | **no, +7** | 252 | — | 2026-09-04 21:30 | 7 commit(s) NOT in main; 252 uncommitted cell PNGs (gitignored by design, NOT regenerable) |
| `agent-ab9199ea1c072b124` | `claude/structural-parts-2026-09` | **no, +13** | — | — | 2026-09-05 02:10 | 13 commit(s) NOT in main |
| `agent-ad9d80c680b7c9f30` | `claude/scan-attribution-2026-09-05` | **no, +1** | — | — | 2026-09-05 09:13 | 1 commit(s) NOT in main |
| `busy-curran-b250c5` | `claude/busy-curran-b250c5` | **no, +2** | — | — | 2026-09-03 13:29 | 2 commit(s) NOT in main |
| `distracted-hugle-218685` | `claude/missing-dashboard-session-1f98a0` | **no, +1** | — | — | 2026-09-06 12:33 | 1 commit(s) NOT in main |
| `elastic-hugle-bb1aca` | `claude/elastic-hugle-bb1aca` | **no, +1** | — | — | 2026-09-02 13:56 | 1 commit(s) NOT in main |
| `epic-chatterjee-9e8c7d` | `claude/epic-chatterjee-9e8c7d` | yes | 122 | — | 2026-09-03 13:08 | branch fully merged into main; 122 uncommitted cell PNGs (gitignored by design, NOT regenerable) |
| `imslp-scores-central-library-ebe0fa` | `claude/imslp-scores-central-library-ebe0fa` | **no, +1** | — | — | 2026-08-31 23:20 | 1 commit(s) NOT in main |
| `interesting-curran-3ca1b7` | `claude/interesting-curran-3ca1b7` | **no, +43** | — | 1 | 2026-05-24 20:44 | uncommitted labeling work: 1 verdict json, 0 data/user-labeled |
| `part-alignment-label-pins-978a57` | `claude/part-alignment-label-pins-978a57` | **no, +7** | — | — | 2026-09-01 14:44 | 7 commit(s) NOT in main |
| `pdf-mxl-pipeline-test-46269e` | `claude/pdf-mxl-pipeline-test-46269e` | yes | 100 | — | 2026-08-31 17:32 | branch fully merged into main; 100 uncommitted cell PNGs (gitignored by design, NOT regenerable) |
| `peaceful-mahavira-8dc765` | `claude/peaceful-mahavira-8dc765` | **no, +1** | — | — | 2026-09-01 20:22 | 1 commit(s) NOT in main |
| `phase2-hollow-labeling` | `claude/phase2-hollow-labeling` | yes | 448 | — | 2026-09-03 13:03 | branch fully merged into main; 448 uncommitted cell PNGs (gitignored by design, NOT regenerable) |
| `quizzical-bell` | `claude/quizzical-bell` | **no, +1** | — | — | 2026-04-06 09:19 | 1 commit(s) NOT in main |
| `reengraved-scanned-weights-175fce` | `claude/reengraved-scanned-weights-175fce` | **no, +4** | 1704 | — | 2026-09-05 01:01 | 4 commit(s) NOT in main; 1704 uncommitted cell PNGs (gitignored by design, NOT regenerable) |
| `scan-weights-round4-continue-074940` | `claude/scan-weights-round4-continue-074940` | yes | 460 | — | 2026-09-04 16:42 | branch fully merged into main; 460 uncommitted cell PNGs (gitignored by design, NOT regenerable) |
| `scoreaug-fair-test-a2928e` | `clef-phase0-eval` | **no, +14** | — | — | 2026-08-28 11:49 | 14 commit(s) NOT in main |
| `transcription-overnight-progress-426c90` | `claude/transcription-overnight-progress-426c90` | yes | 1008 | — | 2026-09-03 00:49 | branch fully merged into main; 1008 uncommitted cell PNGs (gitignored by design, NOT regenerable) |
| `unruffled-shtern-6855a1` | `claude/unruffled-shtern-6855a1` | **no, +2** | — | — | 2026-09-01 17:25 | 2 commit(s) NOT in main |
| `weight-generalization-publishers-548504` | `claude/weight-generalization-publishers-548504` | yes | 4862 | — | 2026-09-03 13:28 | branch fully merged into main; 4862 uncommitted cell PNGs (gitignored by design, NOT regenerable) |

### SAFE — 80

| worktree | branch | in main? | uncommitted cell PNGs | verdict json | dir mtime | why |
|---|---|---|--:|--:|---|---|
| `adoring-kare-52c6` | `claude/adoring-kare-52c6` | yes | — | — | 2026-03-25 23:53 | branch fully merged into main |
| `agent-a0b20b3e7c892c30d` | `claude/condensed-parts-split` | yes | — | — | 2026-09-04 21:22 | branch fully merged into main |
| `agent-a101225ac7058455a` | `claude/staff-structure-stitch` | yes | — | — | 2026-09-04 20:28 | branch fully merged into main |
| `agent-a1cfb16da98b055b7` | `worktree-agent-a1cfb16da98b055b7` | yes | — | — | 2026-09-04 18:42 | branch fully merged into main |
| `agent-a27ea6f49a3716925` | `claude/absent-instrument-veto-2026-09` | yes | — | — | 2026-09-06 09:26 | branch fully merged into main |
| `agent-a36a7c8b0ff74c6f9` | `claude/range-veto-2026-09-05` | yes | — | — | 2026-09-06 01:22 | branch fully merged into main |
| `agent-a3be076c463a599e3` | `claude/lexicon-substring-capture-2026-09-05` | yes | — | — | 2026-09-05 16:03 | branch fully merged into main |
| `agent-a42c860555e30921b` | `worktree-agent-a42c860555e30921b` | yes | — | — | 2026-09-05 10:38 | branch fully merged into main |
| `agent-a52eb66537f0568d5` | `claude/label-ladder-2026-09` | yes | — | — | 2026-09-06 10:29 | branch fully merged into main |
| `agent-a5db9c4b9aa5bfecb` | `claude/arc-attribution-2026-09` | yes | — | — | 2026-09-04 19:44 | branch fully merged into main |
| `agent-a720bd7767a81d205` | `claude/edition-instrumentation-2026-09-05` | yes | — | — | 2026-09-05 16:32 | branch fully merged into main |
| `agent-a775e95a5eeeb5ce7` | `claude/instrumentation-capture-2026-09` | yes | — | — | 2026-09-05 14:39 | branch fully merged into main |
| `agent-a956bedd94022f439` | `claude/roster-wiring-2026-09-05` | yes | — | — | 2026-09-05 22:55 | branch fully merged into main |
| `agent-abfe330be2a30a027` | `claude/staff-identity-audit-2026-09-04` | yes | — | — | 2026-09-04 22:17 | branch fully merged into main |
| `agent-acab31719126d0781` | `claude/movement-reference-2026-09` | yes | — | — | 2026-09-06 08:17 | branch fully merged into main |
| `agent-accd6ad05b6bfba42` | `claude/spans-veto-composition-2026-09` | yes | — | — | 2026-09-06 10:06 | branch fully merged into main |
| `agent-adbc52e4ddea7b706` | `claude/staff-identity-layer-2026-09-05` | yes | — | — | 2026-09-05 16:57 | branch fully merged into main |
| `agent-aeb8577880071129b` | `worktree-agent-aeb8577880071129b` | yes | — | — | 2026-09-05 23:47 | branch fully merged into main |
| `agent-afa78f2c3162c2166` | `claude/reference-selection-2026-09` | yes | — | — | 2026-09-06 08:56 | branch fully merged into main |
| `bach-choir-grouping` | `claude/bach-choir-grouping` | yes | — | — | 2026-09-04 18:45 | branch fully merged into main |
| `beautiful-ellis-826c8a` | `claude/beautiful-ellis-826c8a` | yes | — | — | 2026-09-01 17:52 | branch fully merged into main |
| `blissful-payne` | `claude/blissful-payne` | yes | — | — | 2026-03-25 23:47 | branch fully merged into main |
| `clef-specialist-wiring` | `claude/clef-specialist-wiring` | yes | — | — | 2026-08-30 15:57 | branch fully merged into main |
| `clef-string-staves` | `claude/clef-string-staves` | yes | — | — | 2026-09-04 19:07 | branch fully merged into main |
| `confident-colden-a5f298` | `claude/confident-colden-a5f298` | yes | — | — | 2026-08-31 13:54 | branch fully merged into main |
| `cool-dewdney-e642c5` | `claude/cool-dewdney-e642c5` | yes | — | — | 2026-08-31 22:34 | branch fully merged into main |
| `distracted-bartik` | `claude/distracted-bartik` | yes | — | — | 2026-03-28 18:12 | branch fully merged into main |
| `dsv2-rehearsal` | `claude/dsv2-rehearsal` | yes | — | — | 2026-09-04 15:45 | branch fully merged into main |
| `dynamics-letters-clef-approach-fba804` | `claude/dynamics-letters-clef-approach-fba804` | yes | — | — | 2026-09-04 22:36 | branch fully merged into main |
| `ecstatic-torvalds-e426cb` | `claude/ecstatic-torvalds-e426cb` | yes | — | — | 2026-09-02 10:59 | branch fully merged into main |
| `epic-lumiere-8f01aa` | `claude/epic-lumiere-8f01aa` | yes | — | — | 2026-09-01 14:07 | branch fully merged into main |
| `export-accents-arcs` | `claude/export-accents-arcs` | yes | — | — | 2026-09-04 17:12 | branch fully merged into main |
| `friendly-pike-395b8e` | `claude/friendly-pike-395b8e` | yes | — | — | 2026-09-03 16:28 | branch fully merged into main |
| `frosty-bhaskara-71c283` | `claude/salvage-lily-accidental` | yes | — | — | 2026-09-02 10:49 | branch fully merged into main |
| `frosty-burnell-91bcbd` | `claude/frosty-burnell-91bcbd` | yes | — | — | 2026-09-03 08:34 | branch fully merged into main |
| `funny-villani-98dd46` | `claude/omr-coverage-provenance` | yes | — | — | 2026-09-02 11:09 | branch fully merged into main |
| `gifted-mcnulty-3f6795` | `claude/gifted-mcnulty-3f6795` | yes | — | — | 2026-09-01 22:19 | branch fully merged into main |
| `gould-between-lines-engraving-5edd75` | `claude/gould-between-lines-engraving-5edd75` | yes | — | — | 2026-08-28 17:08 | branch fully merged into main |
| `inspiring-pascal-95626e` | `claude/recognition-improvement-next-2f1709` | yes | — | — | 2026-08-28 15:44 | branch fully merged into main |
| `kind-kapitsa-ca8e27` | `claude/kind-kapitsa-ca8e27` | yes | — | — | 2026-09-01 20:39 | branch fully merged into main |
| `laughing-mendel-e3470b` | `claude/laughing-mendel-e3470b` | yes | — | — | 2026-09-01 17:29 | branch fully merged into main |
| `lucid-moore-485ceb` | `claude/lucid-moore-485ceb` | yes | — | — | 2026-09-03 13:49 | branch fully merged into main |
| `magical-ardinghelli-8a7182` | `claude/magical-ardinghelli-8a7182` | yes | — | — | 2026-09-01 22:59 | branch fully merged into main |
| `mystifying-curran-613606` | `claude/mystifying-curran-613606` | yes | — | — | 2026-09-03 17:32 | branch fully merged into main |
| `nervous-pike-a27e33` | `claude/practical-chatterjee-61a6a0` | yes | — | — | 2026-09-02 13:22 | branch fully merged into main |
| `nice-nash-085307` | `claude/nice-nash-085307` | yes | — | — | 2026-09-04 22:25 | branch fully merged into main |
| `nostalgic-lichterman-c0bd57` | `claude/nostalgic-lichterman-c0bd57` | yes | — | — | 2026-09-01 19:13 | branch fully merged into main |
| `objective-chatelet-c060e5` | `claude/objective-chatelet-c060e5` | yes | — | — | 2026-09-03 13:49 | branch fully merged into main |
| `omr-clef-detector-demo-d51278` | `claude/clef-recognition-improvement-ab75f6` | yes | — | — | 2026-08-28 13:01 | branch fully merged into main |
| `omr-clef-fusion-fix-7e0fdd` | `claude/omr-score-order-prior` | yes | — | — | 2026-08-29 22:33 | branch fully merged into main |
| `omr-info-retention-erasure-c26534` | `claude/omr-next-steps-review-a1727b` | yes | — | — | 2026-08-28 20:47 | branch fully merged into main |
| `omr-key-signature-tuning-3144e5` | `claude/status-refresh-0828` | yes | — | — | 2026-08-28 16:04 | branch fully merged into main |
| `optimistic-nash-7011f7` | `claude/optimistic-nash-7011f7` | yes | — | — | 2026-08-31 22:40 | branch fully merged into main |
| `pdf-mxl-measure-matching-acce2c` | `claude/pdf-mxl-measure-matching-acce2c` | yes | — | — | 2026-09-02 14:12 | branch fully merged into main |
| `peaceful-shamir-d12e52` | `claude/peaceful-shamir-d12e52` | yes | — | — | 2026-09-03 12:32 | branch fully merged into main |
| `project-state-survey-a859c2` | `integrate/land-2026-09-01` | yes | — | — | 2026-09-01 16:55 | branch fully merged into main |
| `quirky-lalande-1bb7bd` | `claude/quirky-lalande-1bb7bd` | yes | — | — | 2026-09-02 11:53 | branch fully merged into main |
| `recognition-over-detection-3d4eba` | `claude/recognition-over-detection-3d4eba` | yes | — | — | 2026-08-29 22:41 | branch fully merged into main |
| `recognition-over-detection-96b67b` | `claude/reengraved-score-evaluation-cd4c92` | yes | — | — | 2026-08-29 22:38 | branch fully merged into main |
| `reconciliation` | `claude/reconciliation-2026-09-05` | yes | — | — | 2026-09-04 20:30 | branch fully merged into main |
| `reengrave-review-plan-930a81` | `claude/reengrave-review-plan-930a81` | yes | — | — | 2026-08-29 23:20 | branch fully merged into main |
| `reengraved-mxl-labeling-approach-392a81` | `claude/reengraved-mxl-labeling-approach-392a81` | yes | — | — | 2026-09-04 10:06 | branch fully merged into main |
| `reengraved-omr-artifacts-direction-fd3a21` | `claude/reengraved-omr-artifacts-direction-fd3a21` | yes | — | — | 2026-09-02 11:51 | branch fully merged into main |
| `reengraver-contextual-analysis-29cdd5` | `claude/reengraver-contextual-analysis-29cdd5` | yes | — | — | 2026-08-28 16:40 | branch fully merged into main |
| `sad-austin-7e16e7` | `claude/deepscoresv2-production-dependency-07bf07` | yes | — | — | 2026-09-06 12:41 | branch fully merged into main |
| `scan-e2e-determinism` | `claude/scan-e2e-determinism` | yes | — | — | 2026-09-04 14:24 | branch fully merged into main |
| `scan-forensics` | `claude/scan-error-forensics` | yes | — | — | 2026-09-04 16:57 | branch fully merged into main |
| `scan-gate-rows` | `claude/scan-gate-rows` | yes | — | — | 2026-09-04 14:30 | branch fully merged into main |
| `scan-gate-rows-2` | `claude/scan-gate-rows-2` | yes | — | — | 2026-09-04 16:59 | branch fully merged into main |
| `scan-rebaseline` | `claude/scan-rebaseline` | yes | — | — | 2026-09-04 15:38 | branch fully merged into main |
| `silly-bose` | `claude/silly-bose` | yes | — | — | 2026-03-26 09:42 | branch fully merged into main |
| `sleepy-cerf-72eea8` | `claude/sleepy-cerf-72eea8` | yes | — | — | 2026-09-03 12:59 | branch fully merged into main |
| `surya-determinism-probe-799f63` | `claude/surya-determinism-probe-799f63` | yes | — | — | 2026-09-01 15:59 | branch fully merged into main |
| `sweet-goldwasser-bdb45b` | `claude/sweet-goldwasser-bdb45b` | yes | — | — | 2026-09-02 10:57 | branch fully merged into main |
| `system-break-rule-publishers-62ead4` | `claude/system-break-rule-publishers-62ead4` | yes | — | — | 2026-09-01 17:02 | branch fully merged into main |
| `tech-advances-tools-review-4a43f9` | `claude/tech-advances-tools-review-4a43f9` | yes | — | — | 2026-08-31 13:52 | branch fully merged into main |
| `tilt-pricing` | `claude/tilt-pricing-widened` | yes | — | — | 2026-09-04 18:22 | branch fully merged into main |
| `upbeat-nash-04b323` | `claude/upbeat-nash-04b323` | yes | — | — | 2026-09-02 11:15 | branch fully merged into main |
| `vercel-upgrade-issues-213086` | `claude/vercel-upgrade-issues-213086` | yes | — | — | 2026-09-01 08:18 | branch fully merged into main |
| `zen-panini-fdc5ae` | `claude/zen-panini-fdc5ae` | yes | — | — | 2026-09-02 13:37 | branch fully merged into main |
