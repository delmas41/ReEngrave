# A broken ladder is not evidence, and a notehead outside the staff must hang on something

**2026-09-01.** Two items from `docs/next-steps-omr-2026-09-01.md` — the
bassoon pair Beethoven still got wrong, and the spurious whole note on its
Flute 1 — turned out to be the same subject: what a ledger ladder is allowed
to prove. Pooled OMR-NED **0.1506 → 0.1431**, edits 1068 → **1014**.
Beethoven's note row goes to **81/81, recall 1.000, precision 1.000** — the
first perfect note row on the orchestral benchmark. Mahler is unchanged to
the edit. Suite 1420 → 1429 green; authored fixtures identical (see below).

| | before | after |
|---|--|--|
| pooled OMR-NED | 0.1506 (1068) | **0.1431 (1014)** |
| beethoven | 0.1775 (221) | **0.1649 (205)** |
| brahms | 0.1922 (761) | **0.1828 (723)** |
| mahler | 0.0455 (86) | 0.0455 (86) — identical |

## The bassoon pair was a truncation cliff, not verdict ordering

The next-steps entry guessed "the pair ordering reaching the veto
inconsistently". The instrumented dedupe says otherwise. Both bars have the
same three copies pre-dedupe: Bassoon 1's own C4, Bassoon 2's own C4, and a
ghost — Bassoon 2's C4 seen from Bassoon 1's cell and resolved against the
wrong staff as `Ab1`. The verdicts:

    bar 8:  ghost (0,1) vs C4 (1,1)   complete wins — ghost loses. Right.
    bar 7:  ghost (0,1) vs C4 (0,0)   broken beats broken on COUNT — C4 loses.

Why bar 7's C4 read `(0,0)`: the note sits ON the first ledger line, one
spacing above Bassoon 2's top line, and `_ledger_ladder` computed its
expected rungs as `int(distance / spacing)`. Bar 8 measured 42px/41.25 →
`int(1.018) = 1`, rung found, complete. Bar 7 measured 41px/41.25 →
`int(0.994) = 0` — **no rungs expected**, indistinguishable from a broken
ladder. One pixel of jitter across a truncation boundary, and the same note
needed its ledger in one bar and not in the next.

And the ghost's one found rung is the C4's own ledger line: the physical
ledger at y 2971 is rung 3-of-3 from Bassoon 1's anchor (2966.75 expected)
and rung 1-of-1 from Bassoon 2's (2971.75). The rung that made the ghost's
ladder "better" belongs to the note it was beating.

Two fixes, each principled alone:

- **`_LEDGER_RUNG_EXPECTED_SLACK` = 0.25.** A note ON the k-th ledger sits
  k.0 spacings out; a note in the space above it sits k.5. `int(d + 0.25)`
  puts the boundary halfway between the two populations a notehead can
  occupy, where `int(d)` put it exactly ON one of them.
- **Completeness only.** The dedupe's ladder verdict now fires only when
  exactly one side's ladder is unbroken. The doctrine was already
  "completeness before count — a gap is what you see when the rungs belong
  to something else"; the same cut runs the other way: one rung found out
  of three expected is what you see when that rung belongs to the OTHER
  staff's note. Two broken ladders fall through to the range veto, then
  distance — and in bar 7 both of those get it right (Ab1 is MIDI 32
  against the bassoon's written floor of 34; the C4 copy is 1 spacing from
  its band against the ghost's 3.1).

## The Flute 1 whole note is the 'g' in "Allegro", and it had three siblings

`noteheadWholeOnLine`, pitch Ab5, confidence 0.53, 27px in a 41px-spacing
staff — the descender bowl of the **g** in *Allegro con brio*, printed above
the page's top staff. The edge-fragment rule (`_drop_clipped_notehead_
fragments`) cannot see it: it is whole, interior, and at 0.65 spaces it
clears the 0.6 sliver cutoff. Sweeping all outside-staff noteheads across
the three works (expected vs found rungs, `_ledger_ladder`'s own tolerances)
found three more of the same kind on Brahms, each confirmed against the ink:

    beethoven staff 0   Ab5 whole  conf 0.53   the 'g' of "Allegro"
    brahms    staff 3   D6  whole  conf 0.45   a letter bowl of "legato"
    brahms    staff 8   Ab4 whole  conf 0.52   a key-sig flat's bowl (staff above)
    brahms    staff 17  G2  black  conf 0.45   a bare ledger line, 14px tall

**Neither available signal carries a veto alone.** Ledger recall is
imperfect: 30+ REAL outside-staff noteheads have zero found rungs (Beethoven
cello D3 at 0.86-0.89, Brahms A5/Ab5 at 0.82-0.88...), so zero-rungs-alone
deletes music. And a global confidence floor is the blunt lever the repo has
measured and rejected elsewhere. Together they separate cleanly:

    fakes:                                conf 0.45-0.53
    (empty)
    lowest real outside-staff notehead:   conf 0.76
    lowest real ZERO-RUNG notehead:       conf 0.82

`_drop_unladdered_noteheads`: centre outside the five-line band, at least
one rung expected, none found, confidence under **0.65** (mid-gap). Runs
before the dedupe. Inside-staff detections are never touched at any
confidence — dense pages keep their low-conf interior noteheads. Fires 1 on
Beethoven, 3 on Brahms, 0 on Mahler, 0 on the authored fixtures.

## Per-layer counts, not the pooled delta

Brahms, same truth, category by category: **`wrong note` 313 → 275 (−38)**,
`wrong slur` 42 → 39, `wrong flag/beam` 156 → 159 (+3 — notes that now PAIR
are charged for their beam differences instead of a delete+insert), and all
eleven other categories identical to the edit. Beethoven: `wrong note`
11 → 2, `wrong tie` 6 → 5, entire-measure 111 → 105. Nothing moved anywhere
a fix has no business reaching.

Note recall/precision: beethoven 0.988/0.976 → **1.000/1.000**, brahms
0.923/0.917 → 0.929/0.927, mahler identical.

## What the remaining beethoven `wrong note: 2` is

The Flute bar-2 fermata rest read as two whole rests — a rest over-detection
under the fermata, out of scope here and now visible exactly because the
noteheads around it stopped drowning it.

## Verification

    python3 -m tools.omr.training.orchestral_eval --omr-ned      # exit 0
    python3 -m pytest tools/omr/tests/ -q                        # 1429 passed
    python3 -m tools.omr.training.end_to_end_eval \
        --out after.json --compare before.json                   # identical

New regression tests in `test_transcribe_helpers.py`:
`TestLedgerLadder.test_a_note_on_the_first_ledger_needs_that_rung` (the
truncation cliff, at ±jitter), `TestBrokenLaddersAreNotEvidence` (the bar-7
inversion shape, plus complete-still-wins), `TestDropUnladderedNoteheads`
(each leg of the veto, and the abstentions).
