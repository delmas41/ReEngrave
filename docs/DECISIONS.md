# Decisions

Append-only. One dated line per decision, who made it, and the reason in a
clause. A decision is a fact about what the project does from that day; the
measurement behind it lives in the benchmark `FINDINGS.md` it names. Nothing
here is ever edited in place — a reversal is a new line.

Format: `YYYY-MM-DD · who · the decision · because · (pointer)`

---

- 2026-09-22 · Sean · **The staged pipeline is the product path. The legacy
  reader (`transcribe.py`, `export.py`, `contextual.py`) is FROZEN: bug fixes
  only, no new mechanisms, no new flags.** · because every decision since
  09-08 is on staged and the product was still running legacy ·
  (`docs/plan-2026-09-22-from-here-to-a-finished-score.md` §5 Phase 0.1)
- 2026-09-22 · Sean · **CLAUDE.md is archived as `docs/chronicle-2026-09.md`
  and replaced by a spec under 6,000 words; `DECISIONS.md` and `ROADMAP.md`
  are the two living documents beside it; handoff documents stop.** ·
  because a 132,000-word chronicle read as a spec is where the bad premises
  came from · (plan §5 Phase 0.3)
- 2026-09-22 · manager, on Sean's delegation · **The acceptance set is:
  Beethoven 5 mvt 1 / Litolff `984073` (scan); Brahms 1 mvt 1 / Breitkopf
  `317803` (scan); Beethoven 5 mvt 1 bars 1–24 rendered by Verovio
  (engraved).** · because they are the two publishers every lane measured on,
  the only scans with hand-verified windows, and the only input with an exact
  page truth · (plan §4)
- 2026-09-22 · manager, on Sean's delegation · **The cleanup-count pages are
  Litolff pdf page index 3 (works row `…984073-p3`: two systems, 19 staves,
  the 8-staff suppressed system, bars 49 on), Breitkopf pdf page index 1
  (works row `…317803-p2`: two systems, 27 staves, bars 8 on, holds the 9/8
  bar), and page 0 of the engraved render.** · because each is the hardest
  page its document offers that still has a hand-verified window · (plan §4)
- 2026-09-22 · Sean · **No lane cap while a manager session is in charge.**
  · because the cap was a substitute for coordination, and the manager is the
  coordination · (plan §5 Phase 0.5, amended)
- 2026-09-22 · Sean · **Flag triage proceeds: every flag gets promote /
  delete / research; the product path reads at most 15.** ·
  (`docs/flags-2026-09.md`)
- 2026-09-22 · manager · **Legacy-only flags (39) are frozen with the legacy
  path and are not triaged**; they are listed in `docs/flags-2026-09.md` as
  FROZEN and may not be read from `tools/omr/staged/`. · because triaging a
  frozen path is work with no consumer.
