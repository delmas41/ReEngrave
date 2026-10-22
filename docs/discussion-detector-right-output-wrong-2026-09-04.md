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
this for notes; the arc case was then worked (2026-09-04, arc-attribution
session, merged `b5f91c71`: 0.1176 → 0.1127) and it **split this class in
two**. The beam session's hypothesis — the neighbour's arcs caught in the
padding, a duplicate resolved wrong — was WRONG: the Brahms arcs are the
*lower* staff's, drawn high where its ledger notes live, and the Timpani's
grown pad swallowed them while Violin 1's own cell never contained them. **The
arc existed only in the wrong staff — there was no duplicate to arbitrate**, so
no duplicate-resolution rule could ever have seen it. The two subclasses need
different machinery:

- **3a. Duplicated, wrong winner** — both owners detect it; arbitration picks
  (notes, solved).
- **3b. Captured only by the wrong owner** — the pad reaches it, the true owner
  never sees it; the fix is a comparative ownership test on the evidence the
  symbol binds (an arc hugs its noteheads — `OMR_ARC_ATTRIBUTION`, shipped).

The session also recorded a textbook metric trap: the `drop` variant scored
BETTER pooled (2,388 vs 2,371) by deleting 12 real slurs — the symmetric
metric's under-prediction reward — and was refused on an arc-count-vs-truth
control. Margin labels had the class-3 shape too (`Tr. Alt.` → Alto) before
the lexicon fix.

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

### 6. A working mechanism fed a corrupted premise — whose output then corroborates the corruption

Found 2026-09-05, by two workstreams disagreeing about one page and one of them
checking its own substrate instead of arguing. **This class is not "something
was lost" at all**, which is why the first five do not contain it: every
component behaves exactly as designed, and nothing is dropped.

The worked case, Beethoven 5 p.4, position 6:

1. Both free OCR rungs read `Tp.` correctly. `lookup("Tp.")` → Timpani, high
   confidence, and the alias is legitimately ambiguous (`tp` →
   `('Timpani', 'Trumpet')`).
2. `contextual.resolve_ambiguous_label` therefore consults the layout fit — a
   sound design — and the fit names that slot a **trumpet**, so the correct
   reading is overturned.
3. The fit is wrong *because* system 1 prints no Timpani at that position and
   the ordinal join has forced two different staff sequences into one slot
   sequence.
4. The resulting wrong instrument then reads as **independent evidence for the
   wrong join** — which is what made the mis-join invisible in the first place,
   and what made a label-disagreement check circular when it was proposed
   (measured: 99/99 positions agree across systems wherever the join succeeds,
   because `contextual` assigns instruments *by slot* and the slot assignment
   IS the join).

The control that separates it from every other class: the **other edition of
the same page**, same label, same alias, an uncorrupted fit — keeps `Timpani`.

**Why it deserves its own class.** Classes 1–5 are all findable by asking "did
this signal survive?" Here the signal survives, is consumed by working code, and
emerges wrong; and the error is *self-confirming*, so the usual corroboration
check makes it stronger rather than weaker. The tells are structural rather than
local:

- an output that is used as evidence for the thing that produced it (here:
  instrument identity, derived from the join, proposed as a check ON the join);
- a "source" field that records a slot-level or page-level fact but reads like
  a per-item provenance claim (`instrument_source: "label"` survives
  propagation across a mis-joined slot, so it is not a confirmation that a label
  was printed on *that* staff in *that* system);
- **two independent readings that appear to disagree and turn out to be two
  halves of one mechanism** — the disagreement is the diagnostic, not the noise.

⚠️ **What it costs TODAY is zero edits, and saying so is part of the finding.**
`staff["instrument"]` reaches only `<part-name>` (`export.py:3448`, `3638`), and
part naming is recorded in CLAUDE.md as changing OMR-NED by exactly nothing. The
visible symptom in the exported file is two `<part-name>Trumpet</part-name>` in a
row where the page prints `Violino I`. **The harm is entirely PROSPECTIVE**: any
future consumer keyed on that field inherits the corruption — a condensed-part
count source would hand a Trumpet's 2 players to a Violino I staff whose printed
truth is 1. A class-6 defect can sit at zero cost indefinitely and become
expensive the moment something starts trusting the field, which is an argument
for recording it rather than for fixing it immediately.

⚠️ **And the obvious local fix was declined, with a reason worth keeping.** "Do
not let the layout fit overturn a high-confidence direct lookup" would gut the
function it guards: for an ambiguous alias the direct lookup IS the corpus-wide
guess that `resolve_ambiguous_label` exists to replace — its docstring says the
lexicon "picks the commoner reading for this corpus" and "the page itself
answers". Such a guard reverts the feature on every page where it currently
works, and neither workstream holds a label-accuracy benchmark that could price
that regression. Same shape as the tenor symmetry floor and the corrected-constant
ledger pitch, both refused here before. **The fix taken instead is provenance,
not logic** — a per-staff-per-system record of whether an identity was confirmed
*here*, built as the abstention gate of the arm that needs it, so it is measured
by that arm rather than shipped on the strength of one page.

**What it costs to find:** the two workstreams held the two halves for hours,
each internally consistent. It was resolved only when one of them answered an
absence-or-presence question **from its own channel** rather than re-deriving
from the other's substrate. Cross-reference
`[[feedback_corroboration_is_not_evidence]]`: agreement is not evidence, and
here *disagreement* was the evidence.

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
3. ~~Tie-pairing attribution~~ — **attributed by the arc session**: 12 of 18
   `tieins` are excerpt-boundary artifacts a perfect reader would also be
   charged for (the truth's last bar opens a tie whose partner is outside the
   window — a FIXTURE honesty issue, not a defect); 8 of 10 `tiedel` are one
   system-wide invented tie (Mozart 41 m5, eight parts at once), upstream in
   tie pairing, left open with coordinates.
4. **Voice-model translation on divisi** (largest known class-2 budget; hard —
   the convention question, not a bug hunt).
5. **Re-measure accidental-role recovery** on the widened corpus.
