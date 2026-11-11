# 2.289 — Where read notes are dropped (2026-11-10)

STAGED, measure only. Branch `lane-2.289-note-loss-look` cfd1dba5e. Written by the manager from the lane report (the lane's own Write was refused by a hook). Scripts are on the lane branch named below.

## Cause and process lesson
Nobody knew what the two biggest "not written" buckets held because the conservation count (2.286) proves only that
a reason is NAMED, not that the surviving copy was written. `owned_by_another_staff` is the losing copy of a box
contested between two staves (`adjudicate.is_relocated_copy`); dropping it is right only if the owner staff's copy is
written, and nothing checked that. Lesson: a named reason is not an explained loss.

## Counts (Litolff p1-2, Brahms p0,4; saved 10-29 slices replayed on main with 2.285 ON; pipeline's own data)
- `owned_by_another_staff` 250 (88 L / 162 B): 231 have a WRITTEN twin on the owner staff; 1 written on another
  staff; 1 twin a `mark_group_duplicate`; **17 candidate-lost** (9 L / 8 B).
- `claimed_by:barline` heads 106 (7 L / 99 B): all narrow slivers (< 0.4 head width), none over a written head.
- The 17: 10 have a twin refused `duration_narrowed`, 3 `chord_value_undecided`, 3 a shape refusal, 4 no box on the
  owner staff at all. The ownership rule and the barline claim are not the cause; the owner copy's VALUE refusal is.

## Sean's tiles (answers/answers-2.289-r1.json)
Barline drops right 3/3. Of five candidate-lost heads, four are real noteheads missing from the file (tiles 3, 4, 7, 8)
and one is the note of a metronome mark (rightly not a staff note). Controls 2/2. Which staff each head is on was asked
and not answered.

## Follow-ups (not built)
1. Notes between two staves whose owner copy is refused for value (≈13 of 17) — a value-reading problem.
2. Four heads with no owner-staff box (relocation is OFF by default).
The written-twin test (`classify.py`) should join the standing conservation count.

## Not verified
Two pages per plate on a saved gather; the 231 "twin is written" cases are by position only.
