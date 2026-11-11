# 2.299 — the key's kind from where its signs sit (STAGED, ADJUDICATE)

Written by the manager from the lane's report (agent FINDINGS writes are
refused). Branch `lane-2.299-key-kind-from-slots` b72d3dcb6, flag
`OMR_KEY_KIND_FROM_SLOTS` default OFF. NOT LANDED: waiting on Sean's 12 tiles
(`out/print-from-worktrees/2.299-r1/tiles/sheet.png`).

## Cause and process lesson

The signs' positions are already measured at GATHER (`key_object.read_pieces`,
a step against the staff's own lines) and `header._marker_run` ignores them
for the kind. Reading those steps against the fixed flat/sharp order works —
but only where the key object counted every printed sign. On 11 of the 15
crushed (K1) staff-systems the key object itself counts 1-2 of 3 flats; 4
more carry an extra piece; others fuse 2-3 flats into one blob.

**Lesson:** 2.292's "the answer was in hand" was true of the KIND on most
staves and of the COUNT on about 15 of 31. The estimate of ~236 notes was a
count from one stage alone, not re-measured through the reader that would use
it (CLAUDE rule 7, "a rate from another population"). A kind from slots
cannot supply a count the slots did not measure, and the system's count is
not the staff's to take.

## What was built

`tools/omr/staged/key_kind_slots.read`, called from
`adjudicators/header.py:_staff_reading` only where the boxes gave no reading.
READ only when: slot count equals the system's agreed count; every slot within
1.0 step of one order for the staff's READ clef; no slot nearer the other
order and the other order misses by >= 1.0 step on average; no natural-shaped
slot. Never overrides a reading, never lowers a count, never promotes the
INFER fill. `_system_checked` / `_part_checked` still judge its output.

## Measured (flag OFF vs ON, same tree, same slice: 9 Litolff pages + Brahms p0, p4)

- Litolff: blue marks -54; notes gained 0, lost 0, changed 0; red bars 189 -> 189.
  48 notes go blue -> plain on 4 staff-systems, 0 pitch changes. Blue-for-key
  notes 368 -> 320.
- Brahms: nothing changed.
- Every key it reads equals the INFER fill.
- judged right->wrong 0; `judged_claims` no new contradiction (it reads GATHER rows this flag cannot touch).
- Flag OFF byte-identical on all ten pages. Fast tier 10410 passed; check 228.
- Reach by 2.292 bucket: K1 0/15, K2 1/2, K3 1/5, K4 2/4, K6 0/3, K7 0/2, K8 0/1.
- Sean's 2.292 tiles as real cases (19 tests): tile 1 READ flats 3 (matches Sean);
  the rest abstain with a named reason; none gives a different key.

## Not confirmed

- Sharps: no saved page of either plate prints a sharp signature; the sharp
  order is tested on constructed rows only. CONVENTION ASSUMED (fixed sharp
  order) / WOULD FALSIFY: a real sharp-key page / NOT CONFIRMED.
- Tolerance 1.0, flat anchors 1.25, margin 1.0 are measurements on two plates:
  by §4 they may only narrow until another publisher confirms them.
- The baseline does not reproduce the saved record (54 of 9560 duration/rest
  verdicts differ, identically in both arms) — unexplained.

## Next (upstream, the real lever)

The key object's COUNT: keep the extra pieces on the record and count fused
blobs (`key_object.read_pieces`, GATHER). That is where the other ~190 blue
notes are. Nothing retired: `raise_count` still fires where this reader
abstains (23 of 49 Litolff staff-systems).
