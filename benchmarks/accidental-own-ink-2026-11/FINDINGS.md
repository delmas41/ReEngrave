# 2.285 — An accidental claims its own ink where the detector drew no accidental box (2026-11-10)

STAGED, GATHER (page-wide step) -> ADJUDICATE -> EVALUATE -> EXPORT. Flag `OMR_ACCIDENTAL_OWN_INK`, LANDED ON
2026-11-10 (`=0` opts out). Code `tools/omr/staged/page_accidental_ink.py`, call site in `gather.py`,
`gather.file_accidental_position`. Written by the manager from the lane reports (the lanes' writes were refused).

## Cause and process lesson

Some printed sharps, flats and naturals get no accidental box from the detector (Sean's tiles 2.280 r2, 2.279 r3,
2.282). Their ink was then left unclaimed or boxed as heads/stems. No claim ORDER could fix it (2.282) because
nothing claimed that ink as an accidental at all.

Round 1 read those accidentals and filed the result on a claim row that NOTHING READ ("the value existed and
nothing read it"): 33 of 37 real ones changed nothing in the file, and the note beside each stayed at the key's
pitch, unmarked. Lessons: (1) a reader that claims ink is run through to the WRITTEN FILE at once, not judged by
its claim count; (2) "what was read earlier" is checked against what actually exists as a claim at that step, not
against what the claim order says should exist; (3) a lane's own "a handful" is read against what the file is
missing, not only what it changes.

## Prior work

`accidental_family` is the one shape reader (2.263 / 2.263b naturals READ at stagger margin >= 0.25; 2.266b the
family read is not re-flagged by the one-ink guess). 2.196's "20% of accidentals missed" was 2-4% on Brahms.
2.282: accidental-first vs heads-first claim order, neither landed (Sean 2/6 and 1/6).

## Round 1 (9497715ad) — reader + claim, no consumer

4-page control (Litolff p2, p8; Brahms p14, p19; all in the frozen sample). 40 claims. Sean's tiles
(answers-2.285-r1.json): kind right on 9/9 real accidentals; 3 of 12 claims not accidentals — two QUARTER RESTS
claimed as flats (and removed from the file), and the "(" of a horn crook "(C)" claimed as a sharp. `check` 229 ->
234 (producer-only keys).

## Round 2 (67ad46114) — both causes, wiring

A. Why the reader saw that ink as free.
- Rests: a rest the detector boxed is NOT a claim at GATHER (only a whole rest names strokes, behind
  `OMR_PAGE_CLAIM_BOXES`, OFF); rests sit last in `claim_order.LAYERS`; a quarter rest's shape (a stem with a curl)
  reads as a flat. Fix in place: ink under a detector rest box is an earlier read (`rest_box`). THIS IS A PRIVATE
  LIST, NOT A LEDGER CONSULT — a workaround. Proper fix: rests claim page-wide before this reader (ROADMAP 2.288).
- "(C)": Brahms p14 staff 5 has a detected `x_start` ~110 px left of the true start, so the crook falls outside the
  word claim strip. The reader now refuses ink left of a READ cell-0 clef / leading-column claim
  (`left_of_the_clef`; page-facts: only a clef stands before the key accidentals). The staff-extent error is NOT fixed.

B. The path to the note. Each claimed mark files the `Q.ACCIDENTAL_STAFF_POSITION` row a boxed accidental gets
(`gather.file_accidental_position`), then `ownership.adjudicate_accidental_owner` ->
`consequences.apply_printed_accidental` -> export. Flats and sharps are written GUESSED (blue); a natural at
stagger margin >= 0.25 is READ (plain). The four KNOWN_GAPS rows are gone; `check` 229.

## Measures (OFF vs ON, same tree, same four pages, small per-page gathers)

- Litolff p2, p8: accidentals +7, pitches changed 7, blue +5, nothing lost. 7 claims, 7 written.
- Brahms p14, p19: accidentals +26, pitches changed 30, blue +18, flags +1; notes -2, beams -2, blue -5, rests 0.
  29 claims, 28 written, 1 abstained `no_candidate` (not examined). The 2 lost notes are heads invented on a
  sharp's ink (`glyph/14/0/3/5/9`, `glyph/19/1/5/3/9`).
- Sean's r2 tiles (answers-2.285-r2.json): kind 12/12 (both removed notes are "part of a sharp"); owner 10/10
  ("just to the left of the note").
- `judged` right->wrong 0 (Litolff 186, Brahms 173). It is blind where it has no tile: round 1's two lost rests
  were found by listing every rest/note present OFF and absent ON, which is now part of the measure.
- Fast tier on the landing branch: 10155 passed, 2 failed (the test pinning the OFF default; the stale ink-rules
  page), both fixed and their files re-run; the full tier was not re-run after those two edits. `conservation`:
  invariant holds, unaccounted 0 (saved gather: cannot see this GATHER change).

## Old mechanisms, flag ON (nothing retired by this lane)

`accidental_owner: one_ink_absorbed` 23 Litolff / 155 Brahms fires, none on this reader's ink;
`export.one_ink_guess_of` (accidental) 0; heads refused on this reader's ink 3 (Brahms).

## Open

1. The rest-box list is a workaround -> 2.288 (rests claim page-wide first), then delete the list.
2. Brahms p14 staff 5 `x_start` (staff-extent detector).
3. The one claimed-but-abstained Brahms mark.
4. Measured on 4 pages; the next overnight is its whole-movement measure. How many printed accidentals the reader
   REFUSES is not recorded.
5. A head in a neighbouring staff's cell is guarded only by `adjudicate_accidental_owner`'s height rule.
