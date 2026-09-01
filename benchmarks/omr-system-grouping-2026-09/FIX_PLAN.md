# The fix — plan & staging

2026-09-01. Corpus priority (Sean): **mostly instrumental symphonies.** So the
fix targets the INSTRUMENTAL failure first.

## What actually fails on instrumental symphonies

Not over-splitting (instrumental fragmentation is ~0% across every publisher —
`DIAGNOSIS.md`). The instrumental failure is **over-MERGE**: two stacked systems
on one page read as one, because the break rule fires only where gap bridging is
EXACTLY 0, and stray ink in the gap (measure numbers, restarted instrument
labels, or two systems printed so close their brackets nearly touch) makes
bridging nonzero. The 3 known GT failures are all this: B9 p25 (bridging 66 at
the true break), B9 p60 (324), B5 p40 (3 and 11). Five prior threshold-style
fixes were tried and rejected (`RULE_FIX_ATTEMPT_2026-08-31.md`) — each fixed the
failures but broke currently-correct pages, because all were validated on
one-publisher GT.

**Over-merges are also under-counted:** an over-merge produces one big system
that looks like a legitimate dense single-system page, so the sweep's
fragmentation metric can't see them. True instrumental over-merge prevalence is
unknown — Phase 1 will estimate it.

## Approach — the Audiveris way (from `research/audiveris-reference.md`)

Stop asking "is there ANY ink in this gap" (the veto). Instead detect, positively
and constructively, **where a system STARTS**, and let that force a boundary even
when the gap has stray ink. Two scan-robust start cues (barline-independent, so
they survive what the thin 2px systemic barline does not):

- **Left-margin bracket restart** — a fresh bracket stack begins at a system's
  top staff (Audiveris reads brackets left of its "starting column"; ~3× the ink
  of the systemic barline).
- **Clef-header column** — every system restarts with a clef on each staff at the
  left; a vertical column of header glyphs marks a start. (We need only DETECT the
  header cluster, not classify the clef — sidesteps the clef-detection ceiling.)

This is Tier-1 items #2 (bracket detector) and part of #4 (combine cues by
confidence) from the Audiveris reference, aimed at exactly the over-merge failure.

## Staging

**Phase 1 (now) — measurement-first prototype, no live pipeline edits.**
Build a `system_start_detector` (bracket-restart + clef-header-column) and measure
whether it identifies the correct NUMBER and LOCATION of system starts on:
- FAILURE set (must fix ≥2/3): B9 p25, B9 p60, B5 p40.
- CONTROL set (must regress 0): the 20 correct `eval_grouping.py` cases + all
  `probes/fulldist.py` partition cases + the 3 `phase1-baseline` pages + ~15 clean
  instrumental multi-system sweep pages.
Deliverable: does a positive start-detector separate the failures from the
controls? Report the discriminator and its exact failure/control confusion.
**The bar the 5 prior attempts missed: fix ≥2/3 failures AND break 0 controls.**

**Phase 2 — integrate the winning cue** into `system_grouping` as a constructive
splitter (only adds boundaries at detected system-starts; cannot merge), behind a
flag; full-corpus regression via the sweep harness; confirm the 20/23 stays ≥20/23
and instrumental fragmentation stays ~0%.

**Phase 3 — the harder cases + vocal:** the SCALE step (Tier-1 #1) for robust
units, and extend the start-detector to vocal/sparse pages (over-split side) with
the dossier-supplied structure as the guaranteed fallback for known works.

## Ground rules (the 5-failure lesson)

- Measure failures AND controls together, every iteration. A fix that breaks one
  control is not a fix.
- Prototype in `fix/`; do not touch `tools/omr/` live rules until Phase 2, and
  only behind a flag.
- No tuning a threshold on one corpus.

## Log
- 09-01: Phase 1 launched (Opus): positive system-start detector, measurement-first.
- 09-01: **Phase 1 cleared the bar** (`fix/PHASE1_RESULTS.md`). Winning cue was neither
  named cue — it's **cue A, narrow left-edge systemic-barline continuity**: the wide
  window counts staff-body music ink as bridging; a narrow band at the shared left edge
  is empty at a true boundary. Params L=2.0, R=4.5sp, min_cross=1, gate 0.7. Fixed 2/3
  known over-merges + discovered Eroica p36, 0/37 control regressions, robust R≥3 and
  300/600 dpi. Cues B (clef-header, uniform) and C (bracket, per-family) measured dead.
  B9 p25 (brace curvature) + vocal over-splits deferred.
- 09-01: **Phase 2 integration DONE** — cue A added to `tools/omr/system_grouping.py`
  (`left_edge_barline_counts` + union splitter in `assign_systems`), behind
  `OMR_LEFT_EDGE_SPLIT` (default OFF). Flag off = byte-identical (25/25 tests pass,
  eval reproduces 20/23 exactly). Flag on = **eval 22/23 (was 20/23), 0 spurious
  single-staff systems**, all prior-correct pages kept. Full-corpus regression sweep
  (flag on → `sweep_leftedge.jsonl`) running; diff = `fix/diff_leftedge.py`. Flip
  default to ON only after the regression confirms 0 instrumental over-splits.
- 09-01: **Full-corpus regression + size-1 guard + DEFAULT ON.** Flag-on sweep of the
  whole library (`sweep_leftedge.jsonl`) diffed vs baseline: 43 pages changed, all
  union-only (systems only ever gained). 27 clean over-merge FIXES ([24]→[12,12] etc.
  across Bach/Beethoven/Schubert/Schumann/Wagner/Tchaikovsky/Dvořák/Haydn/Mendelssohn)
  but 16 REGRESSIONS — all the same signature: a small system (keyboard grand staff,
  chamber group, partial last system) split into size-1 fragments. Added
  `_suppress_orphaning_breaks`: **cue A may never create a size-1 system** (a lone
  staff is never a real orchestral system). Because the guard only removes cue-A
  breaks, the 43 pages are the COMPLETE change set (subset argument) — targeted
  recheck (`fix/recheck_guard.py`): 15 regressions reverted to baseline, 28 fixes
  kept, **0 size-1 created**. One residual over-split survives — Mozart K22 p4
  `[6,6,6]→[6,2,4,6]` (adjudicated by eye: the Andante movement-start 2/4 stack breaks
  the left-edge barline between staves 2-3; same within-system-defect family as B9 p25,
  Phase 3). Net: **27 fixes : 1 mild off-corpus residual : 0 size-1**. eval 22/23
  (was 20/23), 0 spurious, 25/25 unit tests pass default-on AND explicit-off; off
  reproduces 20/23 exactly. **Default flipped ON** (`OMR_LEFT_EDGE_SPLIT`, set 0 to
  disable). Not yet committed.
- Remaining (Phase 3): B9 p25 + Mozart K22 (brace/movement-start left-edge defect,
  needs a curvature/solidity discriminator, separately validated); vocal over-splits.
