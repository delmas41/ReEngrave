# The detector was right and the output was wrong — where else? (2026-09-04)

The beam-gap session closed 418 of 449 `wrong flag/beam` edits without touching
the detector: 430 of the 449 were `editbeam` — notes the aligner *paired*, whose
beam state disagreed — and the mechanisms were all in `export.annotate_beams`.
Sean asked the right question: **where else could the pipeline already know the
answer and still write the wrong one?** This document answers it by taxonomy,
because "detected, then lost" is not one failure mode — it is five, and each is
caught by a different kind of check.

## The taxonomy, with the guard that catches each

### 1. Dropped to zero — the guarded class

The signal is computed and *nothing* downstream emits it. This is the shape the
repo has now paid for nine times (beams, dots, dynamics, tuplets, slurs,
articulations, the time-signature glyph, triplet digits under `fingering3`,
accents), and it is the ONLY class the existing guard sees:
`tools/omr/export_coverage.py` asks "the truth has N, we emit zero" on every
suite run. Its `KNOWN_GAPS` ledger currently carries accents, hairpins,
metronome marks and repeat signs — inventoried, not suppressed.

**Status: guarded, keep feeding the ledger.** But note what the beam bug just
proved: this guard has a structural blind spot, which is class 2.

### 2. Emitted but degraded in translation — the beam class, UNGUARDED

The beams were never zero. They were emitted with the wrong *grouping* — the
count survived, the structure didn't — so `export_coverage`'s presence test
passed while 430 edits flowed. The same is true of any signal whose export
involves a re-derivation: the element appears, so no categorical check fires,
and only the metric's bucket grows.

Candidates with evidence today:

- **Rest values.** Phase C measured rests at 0.722 precision against noteheads'
  0.943, with `restQuarter`-vs-`rest8th` disagreements at IoU 0.65–0.82 — the
  same glyph, located correctly, valued differently on the way out.
- **Voice assignment.** Mozart 40's divisi puts ~41% of its notes in `order`
  bars with *every pitch present on both sides* — detection right, the
  voice-split convention loses them. `voicing.py` decides voices from stem
  direction; the truth's part-model disagrees. This is the largest known
  instance of class 2 by edit count.
- **Tie pairing.** Ties are paired in `transcribe._pair_ties_in_staff`, slurs
  in `export.annotate_slurs_in_staff` — two implementations of "pair arcs over
  the staff frame" in two modules. 29 `wrong tie` edits engraved; nobody has
  attributed them.

### 3. Attributed to the wrong owner

The symbol is read correctly and given to the wrong staff, part, or note. The
cross-staff notehead arbitration (ledger ladder → range veto → distance) fixed
this for notes; the beam session just exposed it for **arcs**: ~150 edits on
Brahms 1 from four slur/tie arcs that are the *Violin's*, caught in the
Timpani's cell padding and exported there — verified against the rendered
page. Arcs never got the arbitration notes got. **This is the top open
candidate, already scoped.** Margin labels had the same shape (`Tr. Alt.` →
Alto, a singer) before the lexicon fix.

### 4. Class-role mismatch — right detection, wrong consumer

The detector speaks one vocabulary, the consumer listens for another:

- Beethoven 5 p.15's flats are detected as `accidentalFlat` while every
  key-signature reader consumes only `key*` classes (measured once, routing
  them in scored −1 on the old 3-page truth — worth re-measuring on the widened
  corpus, where the vote bugs it interacted with are now fixed).
- Grace notes are detected as ordinary noteheads — the *size* information the
  page prints (41×38 vs 51–83 px neighbours) is discarded at classification,
  which is the pre-fill's measured ceiling. The geometry route is named in
  CLAUDE.md and untried.
- `fingering3` vs `tuplet3` was this class, fixed by reading both through a
  positional gate.

### 5. Right value, wrong unit or frame

The threshold family: a dot measured against its own bounding box instead of
the staff space, a stem capped in the wrong unit, a snap grid extrapolated past
measured ledger rungs, ideal staff lines on tilted scans. All documented; the
lesson is already written ("a threshold written in the wrong unit"). New
instances arrive whenever a constant is expressed in something the engraving
doesn't hold constant.

## The root cause underneath the beam bug, stated once

The pad existed. `rhythm._beamed_groups` learned on Sep 1 that a beam box
bounds ink stem-to-stem and must be padded by a notehead width — and
`export.annotate_beams`, answering the *same geometric question* for the same
data, never got it. **The bug was not missing knowledge; it was two
implementations of one concept that diverged.** That generalizes into a
checklist question sharper than "is anything dropped": *where do two modules
independently answer the same question about the same ink?*

Known duplicated-concept seams, from this survey:

| concept | implementations |
|---|---|
| beam group membership | `rhythm._beamed_groups` / `export.annotate_beams` (now both padded — should share code) |
| arc-to-note pairing | `_pair_ties_in_staff` / `annotate_slurs_in_staff` / `annotate_slurs_in_slot` |
| which staff owns contested ink | `_dedupe_cross_staff_detections` (notes) / nothing (arcs, dynamics, directions) |
| staff-position → pitch/variant | `pitch_resolver` / annotate-UI snap / pre-fill variant rule |

## What would catch class 2 systematically

`export_coverage` should grow a **conservation audit**: for each class that maps
detection → JSON → export element, compare *counts and groupings* per work, not
just zero-vs-some — e.g. beam levels summed on noteheads vs `<beam>` elements
emitted, arcs detected vs `<slur>`/`<tie>` pairs closed, rest glyphs vs rest
durations by value. Big attrition or big inflation between stages is the beam
signature, visible without any truth file. The second tool is a one-off
**duplicated-geometry review** of the seams table above, sharing code where two
implementations answer one question.

## Ranked next steps out of this discussion

1. **Cross-staff arc attribution** (~150 edits, Brahms 1, mechanism verified) —
   give arcs the arbitration notes already have.
2. **Conservation audit in `export_coverage`** — the guard for the class the
   beam bug lived in.
3. **Tie-pairing attribution** (29 edits, unattributed — cheap to open).
4. **Voice-model translation on divisi** (largest known class-2 budget; hard —
   the convention question, not a bug hunt).
5. **Re-measure accidental-role recovery** on the widened corpus.
