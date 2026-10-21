# 2.183 -- the key signature as an area claim (claimed-area step 3)

Path: STAGED (GATHER files, ADJUDICATE consults). Flag `OMR_KEY_SIGNATURE_CLAIM`, default OFF, needs `OMR_CLAIMED_REGISTER`. Branch
`lane-2.183-key-signature-claim`. Measured on the 20261020-night records (main f1db97989) replayed from per-page slices (`replay_2_183.py`,
`compare_2_183.py`); OFF == main as recorded.

## 1. THE CAUSE (read this first)

**Twenty Litolff key-signature flats and four Brahms ones are written into the file as rests. The "2" was the tip.**
Census, not a diff: every cell-0 box written as a rest standing 3-10 staff spaces right of the cell edge, each looked at in a crop
(`out/print/` tiles, `key_flats_written_as_rests_litolff.json`): Litolff 20 of 20 are the bowl of a key flat (18 `rest8th`, 2 `restQuarter`);
Brahms 8 found, 4 flat bowls (`5/0/1/0/7`, `15/0/0/0/11`, `21/0/9/0/3`, `24/1/4/0/16`) and 4 real quarter rests after the signature (`7/0/*/0`).
The "2" (`glyph/15/1/7/0/1`, `15/1/8/0/3`) are the only two of the 20 that the 2.100-era 18-space `meter_column` happened to refuse as
`rest_is_a_meter_digit`; 2.177 retired that column and exposed them. The other 18 were never caught.

**Why the detector boxed them.** All 20 are PRODUCTION detector boxes (`reader=detector`; none is a 2.172 small-view box, `yolo_detector_view`),
class `rest8th`/`restQuarter` at confidence 0.26-0.77 (median ~0.4). The same ink also wears other names: 9 of 20 are doubled by another box
(`arpeggiato` 2, `accidentalFlat` 1, `noteheadBlackOnLine` 2, a second `rest8th` 4). They are the same glyph keys, same class, in every record
back to 20260930b, 20261010, 20261016, 20261018: not new, not caused by 2.172/2.177. Why the detector reads a flat's bowl as an eighth-rest
body is a training matter (class confusion on a shattered/merged flat): NOT explained here.

**Why the existing `in_a_key_signature_slot` gates missed them** (the window is `key_slots.key_slot_window`, drawn from the detector's own
key-class boxes on THAT staff), of the 20:
- 8: no window at all (the detector boxed no `key*` / accidental-shaped box near the clef on that staff);
- 11: a window exists but this flat stands beyond its last drawn slot (centre 0.04-1.9 sp past it; the next-slot rest rule needs <= 0.2 sp and
  missed by 0.3-0.64 sp in 3; a 1-slot window has no pitch to extend);
- 1: left of the window's start.
Unexplained: 0 of 20 for the gate miss. The CV header reader (`keysig_run_position`, a second look at the SAME raster) also undercounts on
16 of the 20 staves (own count < 3), so it falls silent with the detector (two witnesses off one raster); on 15 of 20 a SIBLING staff of the
same system reads the full 3.

**What the cause teaches.** (1) A gate whose evidence is built from the reader it polices catches exactly the cases where that reader was right
elsewhere on the same staff. (2) The page prints ONE key signature per system, at one x on every staff (page-facts §2), yet it is read per staff
-- the same single-staff blindness 2.177 fixed for the meter with `find_column`. (3) "2 key flats written as rests" was the residue of one
diff of one lane; the population needed a census of the class. (4) 16 of the 20 were once refused (20260930b, `rest_has_a_stem`) by an
accident that a later, unrelated change removed.

**The cleaner fix is upstream of this claim, so I stopped.** Read the key signature as ONE system object: find its columns across all staves
(the 2.177 `find_column` shape) and take the run's extent from the system's agreement (and the dossier's fifths), not from each staff's own
detector boxes. That is a new reader (a different source: other staves), not a window tweak; it would make the claim below catch the 18+4
(they would be NARROWED or refused by Sean's ruling on a column-derived area). The detector's class confusion is the deeper cause; neither
belongs in this lane without Sean.

## 2. What was built (flag OFF, parity-proved)

- GATHER `gather_key_signature_claim`: `Q.CLAIMED_AREA` owner `key_signature` per staff and cell, drawn from the 2.100 window
  (`key_slots.claim_window`) plus a run that opens with cancelling naturals (Sean 2026-10-20; `window_with_cancels`: naturals only BEFORE the first
  sharp/flat, one kind after, needs a clef). `boxes_inside[key]` = `named` (stands in the window, the 2.100 centre rule) + `stand_margin_spaces` +
  measured ink share. Cell 0: READ. A later cell: always NARROWED (see §3).
- ADJUDICATE `claimed_by.consult`: named -> REFUSE `claimed_by:key_signature` (margin = depth inside the run, staff spaces); ink inside the
  area but not standing, or any box of a NARROWED window -> NARROW `claim_narrowed:key_signature` (blue); flags / arpeggiati / arcs: refuse named only.
- ON retires the five gates (notehead, rest, flag, arpeggiato, arc): OFF runs them unchanged. `meter_rows_outside_key_slots` (the meter-glyph
  filter in `movement.py`) is not a gate on a box and stays on `key_slots`.
- The cancelling-natural path is covered by constructed tests only: neither movement changes key (0 windows with naturals on either plate).

## 3. Measures (both plates, OFF vs ON, exported file)

| | Litolff OFF | Litolff ON | Brahms OFF | Brahms ON |
|---|---|---|---|---|
| key claims (cell 0 READ / later cell NARROWED) | - | 207 / 69 | - | 497 / 38 |
| heads refused by the old gate / by `claimed_by:key_signature` | 12 | 12 (only-OFF 0, only-ON 0) | 2 | 2 (0, 0) |
| rests refused by the old gate / by the claim | 23 | 23 (0, 0) | 24 | 24 (0, 0) |
| narrowed by the claim | - | 1 real note (cell 1 of `6/1/3/1/4`, stays written) | - | 1 real rest (`11/1/0/10/6`, now blue) |
| notes in file | 11771 | 11771 (file byte-identical) | 22692 | 22690 (see note) |
| red bars | 508 | 508 | 650 | 650 |
| key flats written as rests | 20 | 20 | 4 | 4 |

Parity is exact for all five gates' refusals on both plates: the claim does the gates' job and nothing more. It fixes none of the 24 flats
(§1). First build error caught by the replay: a later-cell window with a witness staff was READ and refused a real eighth note
(`6/1/3/1/4`); 69 + 38 mid-system "key windows" exist on plates that never change key, so later cells are now always NARROWED -- the two
real marks narrowed above are the cost of keeping them at all (drop them if Sean prefers: they confirm nothing on these plates).
Brahms ON vs OFF also differs by 19 blue dynamics words, 2 notes and 3 glyph verdicts that no key claim touches (text/dynamics readers, beam
discount); a second Brahms OFF replay is the determinism control (§4).

## 4. Controls and checks

- Fast tier: `pytest -m "not slow" tools/omr/tests` 8713 passed, 12 skipped, 2 xfailed. `python3 -m tools.omr.staged.check` 193 (baseline 193).
- Tests `test_staged_key_signature_claim_2_183.py` (25): each control (a real rest/note/flag after the last flat) passes both ways, and mutating
  `stands_in_the_window` to "always" makes 3 fail.
- Blind tiles for Sean: `out/print/2.183-key-signature/` (12, orange box = where to look, means nothing; key `out/print/2.183-key.json`): 9
  drawn (seed 2183) from the 20 Litolff written-rest flats, 3 controls = real eighth rests after the meter. Purpose: Sean confirms the count
  (CLAUDE rule 7) before a key-object lane opens. The claim as built changes none of these.

## 5. Sean's tiles (2026-10-21)

"1-6 key flats 7-8. 8 rest 9. Key flat 10. 8 rest 11-12. Key flat" (`out/print/2.183-key-signature/answers.json`). All 9 cause-population
draws are key flats and all 3 controls are real eighth rests: 12 of 12 as the key. So the census count stands on his eye (20 Litolff + 4
Brahms key flats written as rests, not 2), and the claim as built keeps the controls. The per-system key reader proposed in §1 is NOT built;
it waits for Sean's go-ahead.
