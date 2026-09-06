# Pre-registration — how the reference system is CHOSEN

Written 2026-09-06, from the coordinating session's brief. Recorded here BEFORE
the end-to-end transcription arms were scored; the slot-level probe
(`probe_window_slots.py`) had already reproduced the mechanism at that point and
that is said plainly rather than dressed as a prediction.

## The claim under test

`slots.build_reference` prefers the largest RECURRING system size. On a
multi-page run of a movement whose first page prints the full lineup and whose
later pages condense (`Violoncello e Basso` onto one staff), the condensed shape
is the one that recurs — so the reference is built from it, and `slots.align`,
which deletes on the reference side only, then drops the full system's TOP staff
and slides every name up one.

The fix under test: build the reference from the MOST-LABELLED system instead.

## What would make it right, and what would kill it

1. **Headline** — `--pages 0-2` on the Litolff Beethoven 5 (imslp984073) must
   recover the naming that `--pages 1` gets.
2. **Control** — `--pages 1` must not move. Fixing the three-page case by
   breaking the one-page case is not a fix.
3. **Scan gate** — 20 rows, all short runs. Run a control arm on THIS merge
   base; `0.8444` is not a baseline for this tree and the noise floor is ≥ ±6
   edits.
4. **Coverage, stated as a limitation** — the scan gate's rows are single-PAGE
   runs, i.e. a corpus that mostly cannot exercise a rule about pooling pages.
   A flat result there is expected, and reporting it as "no regression" would
   overstate it.
5. **Kill criterion** — if the rule wins under one publisher's labelling
   convention and loses under another, report the split rather than the arm that
   flatters it. Litolff labels winds and brass on every system and strings
   never; Breitkopf labels everything; Simrock labels a movement's first page
   only. The rule must also ABSTAIN where no system carries labels at all (27 of
   234 documents print none) and fall back to today's behaviour.

## Refused in advance

* A default flip. The flag ships OFF; flipping it is Sean's call with a number.
* Touching system grouping, arc/slur/tie code, or `hairpin_detection.py`.
* `--record`, `current-accuracy.json`, CLAUDE.md's generated accuracy block.
