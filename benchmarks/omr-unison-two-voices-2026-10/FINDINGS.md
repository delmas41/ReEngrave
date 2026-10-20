# omr-unison-two-voices-2026-10 -- ROADMAP 2.175: one head with a stem each way is two notes

STAGED ADJUDICATE + the events/voices decisions + EXPORT. Flag `OMR_UNISON_TWO_NOTES`, **default OFF**. Records 20261018-night (main 6e0787f78). Branch `lane-2.175-unison-two-voices`.

**CONVENTION ASSUMED:** a notehead with a stem on BOTH sides (an up stem at its right, a down stem at its left) belongs to two voices that share one pitch (an a 2 or a divisi unison); each stem carries its OWN value (flag, beam, or neither); two notes are written at that pitch, one per voice, each valued from its own stem. (Sean 2026-10-11 "They would go in different directions"; 2026-10-19 "Why are we not getting flags on both sides of the unison notes?"; and on beams 2026-10-19: the beams are both above and below, easier to see the one outside the staff, "just helps as corroboration".)
**WHAT WOULD FALSIFY IT:** a head that prints one stem each way and means ONE note (a stem plus a barline or slur boxed as a stem; one stem the stem finder cut in two); a flag or beam that belongs to a neighbour's stem; a unison where the two voices differ in a way the stems do not show. The 12 blind tiles ask Sean exactly this.
**NOT CONFIRMED:** by Sean beyond 2.167e tile 3. Everything below that says "real" is MY look at crops (ours, not Sean's, not evidence).

## What existed (rule 1) and what was tried
The tree search for `unison_two_voices`: 2.87 (`stem_value._one_stem_per_head`, rule `unison_two_voices`: one head, a stem each way, no other head under the stems; both stems kept as candidates) and 2.141h (`rhythm._unison_two_voices` counts each stem's beams on its own side; the head stays ONE note valued by the voices' range). Nothing made a second note: `adjudicate_event` filed one glyph as one event, `adjudicate_voices` gave it one voice, EXPORT wrote each glyph once (2.167e Q1). No earlier attempt at a second note.

## What was built (all behind the one flag; OFF is the old behaviour)
- `stem_value._one_stem_per_head`: a stem pair that TOUCHES at the head (the up stem's row also runs below it: the 2.167e tile-3 shape) still reads `unison_two_voices` when the stem runs more than 2x further away from the head than its touch (`UNISON_TOUCH_RATIO`; a barline, as long each way, fails it). **A cut tuned on tile 3 and a plate sample: it may only NARROW (CLAUDE section 4).**
- `adjudicators/unison_two.py`: new `Q.UNISON_VOICES` (after `Q.STEM_VALUE`, before `Q.EVENT`). Per voice: a beam on that stem's own side (`Q.DURATION`'s `beam_voices`) or a flag attached to that stem (`rhythm._attached_flags` on that voice's stems); DECIDED only when both voices read. A voice with no mark while the other has one is NOT a quarter by absence (`one_voice_unmarked`); a dotted head, a tuplet member, a head whose fill disagrees with its class, a flag attached to both stems, a beam count that is a range: refused, with the reason and each voice's reading. Both stems unmarked = two plain quarters (the head's own reading, doubled).
- **Beam corroboration (Sean 2026-10-19, via the manager), same flag:** where one voice's beam count is a RANGE and the other voice's level is READ (a beam or a flag) and lies inside it, the other stem's beam confirms that level (`source: beam_corroborated`). It never supplies a value where the other stem shows no beam ink.
- `rhythm.adjudicate_event`: the head stays ONE event (every single-stream consumer of `Q.EVENT` -- bar_length, meter witnesses, reconcile_duration, INFER -- counts it once, so a second event cannot refuse a bar that adds up per voice) and carries `unison` = each voice's value. **First attempt (two events in `Q.EVENT`) was measured and reverted:** on Litolff p4 bar 110 the doubled head changed the bar sum 2.0 -> 2.5 and made 2.165's `bar_corrects_one_note` stop correcting one note; one event per head keeps every EVALUATE/INFER sum identical to OFF.
- `rhythm.adjudicate_voices`: stands the one event in two streams, one per stem, each on its own value (`_sum_beats` reads `unison_beats`) -- but only where the two streams then sum alike; else it keeps the head as one event and records `unison_two_voices_declined` (`streams_unequal` / `stream_sum_unknown`). Rule 1 (same beat, opposite stems) then decides two voices.
- EXPORT (`export_unison.py`, hooks in `export.py`): the head becomes the up-voice note plus a down-voice twin (same box and pitch, own value); the exporter's own divisi test (`_settle_divisi_pairs`, 2.90) decides which bars are written as two voices; in a bar left fused the twin is dropped and the head restored (`settle`), and at render a bar whose voice split fails is un-fused (`unfuse`) -- nothing sits twice in one stream. The accounting stays an EQUALITY: twins are subtracted under `notes_unison_second_voice` (not on a doubled-staff copy, whose notes are already subtracted), twins are never counted as log rows in held/partial bars, and the rest-duplicate count is not taken twice on a doubled copy (a latent double subtraction that only a two-voice doubled bar exposes).

## Measure (replay ADJUDICATE..INFER..EXPORT of the 20261018-night records, flag OFF vs ON, everything else main; `probe/replay_2_175.py`; the exported FILE is measured)
**Litolff, whole movement.**

| | OFF | ON |
|---|---|---|
| shared heads: `Q.HEAD_STEM` `unison_two_voices` / `two_stems` | 504 / 142 | 515 / 131 |
| `Q.UNISON_VOICES` decided (two notes) | -- | **416** |
| ...both voices agree / differ | -- | 414 / 2 (eighth + sixteenth) |
| ...source: beams on both stems / two plain quarters / two open heads / flags | -- | 174 / 155 / 85 / 2 |
| refused: head refused 34, fill disagrees 17, one voice unmarked 33, shared flag 11, dotted 1, tuplet 3 | -- | 99 |
| notes in the file (`written.notes`; MusicXML `<note>` incl. rests) | 6,686 (9,203) | **6,942 (9,548)** |
| second-voice notes written | 0 | **260** (299 twins kept by the bar test, 95 dropped because the bar was left fused) |
| two-voice bars written | 8 | **208** (kept as two voices at the bar test 4 -> 222) |
| held-out bars (bar does not add up, 2.8) | 618 | 618 |
| partial bars / unread gaps | 169 / 170 | 169 / 180 |
| accounting equality | balanced | balanced |
| Sean's judged tiles (`judged score`, right/wrong/narrowed/abstained) | 159/29/6/1 | 159/29/6/1, **0 tiles move** |

**Brahms, 3 page chunks (pages 0-8, 9-17, 18-26).** Another python held 15-35 GB, so the whole 7 GB record was not loaded. The A/B is fair inside each chunk, but the meter carry is cut at the chunk edges (chunks 2 and 3 have no meter, so no bar is held there): the held-out count is NOT the whole movement's.

| | OFF | ON |
|---|---|---|
| shared heads `unison_two_voices` / `two_stems` | -- | 233 / 63 |
| `Q.UNISON_VOICES` decided | -- | **120** (70 beams on both stems, 45 plain quarters, 1 open, 1 flag; 3 differ: eighth + sixteenth) |
| refused: dotted 67, shared flag 32, one voice unmarked 8, head refused 6 | -- | 113 |
| MusicXML `<note>` count | 20,445 | **20,550** |
| second-voice notes written | 0 | **118** (59 kept, 36 dropped with a fused bar) |
| two-voice bars | 72 | 98 (kept as two voices 28 -> 53) |
| held-out bars (chunk 1 only) | 266 | 266 |
| balance | balanced x3 | balanced x3 |
| judged (156 scored on these pages) | 125/22/9 | 125/22/9, **0 move** |

**Bars that now add up: none.** The twin puts the second note and the two voices in the FILE; it does not change what any bar sum sees (by design: every single-stream sum counts a head once), so the held-out count does not move on either plate. What changes is notes and voices written.

## Real-unison rate (my look at 36 crops per plate, seeded 2175; `probe/sample_2_175.py`; contact sheets `out/print/2.175-look/`)
Litolff: of the 515 candidate heads, about **32 of 36 (89%)** show a head with an up stem at its right and a down stem at its left (many are beamed eighth groups with a beam above AND below, Sean's note). Doubtful: one whose "down stem" may be a flat's stem, one beside a long vertical stroke, one with a single stem. Brahms: of 233 candidates about **25 of 36 (70%)**; the false ones are a head beside a barline (the barline read as a stem), a hollow head under a tie, a single stem on a ledger line. The Brahms scan is coarser, which is also why 67 heads are refused as dotted and 32 for a flag attached to both stems. 2.167e's upper bound was 522 / 245; with the flag ON the candidates are 515+131 / 233+63 and 416 / 120 are decided.

## Corroboration, its own line (Sean's beam remark)
- Heads with beam ink on BOTH stems: Litolff **174** of 515 (all agree), Brahms **73** of 233.
- A beam range on one stem that the other stem's read beam could confirm: **0** on both plates (no head had a ranged voice), so **corroboration settled 0 notes**. 2.141h's per-voice count already settles a stem's beams when that stem's own beam is certain.
- The case the remark targets -- the outside beam is read and the inside stem shows nothing -- is the `one_voice_unmarked` refusal: Litolff **33** (25 with only a beam read: 20 on the down stem, 5 on the up stem; 8 with only a flag), Brahms **8**. These are NOT filled (CLAUDE section 4: two voices on one head can carry different rhythms, and the other stem shows no ink). If Sean says "two: 8 and 8" for such a head, the other voice's beam ink is being missed, and a corroboration rule WITH a second witness (the stem tip, a stroke between the two stems) is the measured next step. None of the 12 tiles is one of these (they are all decided heads); a second tile set can ask.

## Interaction with the bar sums (2.162 bar_length, 2.165 correction)
Unchanged by construction: `Q.EVENT` keeps one event per head, so `bar_length`, the meter carry/vote, `reconcile_duration` and 2.165's one-note correction see the same bars as OFF. The per-voice sums live only in `adjudicate_voices` (a unison is two voices only where both streams sum alike) and in EXPORT's own equal-time test. 2.173 (red bars) and 2.174 (decided quarters under beams) own EXPORT / value assembly; this lane touches EXPORT in `_place_notes` (split / expand / settle), the note counter, `_bar_event_rows`, the voice-split fallback and the rest-duplicate count only.

## Controls (rule 7) and checks
- The first design (two events in `Q.EVENT`) failed its own control: P4 bar 110, the second event made the bar 2.5 quarters where OFF summed 2.0, and 2.165's correction of one note stopped (glyph `4/1/3/12/5`: 0.5 -> 1.0). Reverted, not tuned.
- The accounting equality raised `Unbalanced` four times on the way (twins held out with their bar; twins on a doubled copy; two rests double-subtracted on a doubled copy; a record's two-voice bar whose head the exporter then dropped); each was found by a per-measure diff of the OFF and ON files, none by loosening the equality.
- Fast tier `pytest -m "not slow" tools/omr/tests -q`: 8,551 passed, 3 failed on the first run (flag-table row wording; the human-box quantity set now includes `unison_voices`, filed as an abstention on every notehead; `export_unison.py` not registered in `reach`); all three fixed and the three files re-run (97 passed). 17 new tests, `test_staged_unison_two_notes_2_175.py`. `staged.check` TOTAL open 193, status ok; `reach --check` 0 unregistered modules.

## Not done / limits
- Brahms whole-movement bar sums (chunked). Dotted unisons (67 Brahms) are refused: which voice owns the dot is not read. A head whose single duration is a range between its voices (5 in 9 Litolff pages) is not written: EXPORT drops a narrowed head before the split. A unison head that shares an onset column with another head stays one event.
- LilyPond: the same cell detections and the same voice split feed it; no PDF was compiled in this lane.
- Tiles: `out/print/2.175-review/` (12: 10 shared heads the arm reads as two notes, 2 controls); `key.json` is ours and is never shown to Sean.

## Sean's answers (2026-10-19) and the score (`out/print/2.175-review/answers.json`, `out/2.175/score.json`)
Sean: all 10 shared heads are TWO notes; the two controls are one note each. The ON arm decided two notes for 10 of 10 and the controls were never split. Per tile, both voices' values right: **8 of 10** (tiles 1, 3, 4, 5, 7, 8, 9, 10: 8+8 or 4+4 as Sean says). **Value-wrong: tiles 11 (Litolff) and 12 (Brahms)** -- the up voice reads 8, the down voice reads 16th (two beams counted under the down stem) where Sean hears 8 and 8; one voice wrong each, 2 of 20 voices. **In the file: only 1 of 10 (tile 9)** has its second note written: the exporter keeps a bar as two voices only where every chord has a decided direction and both streams sum alike (`_settle_divisi_pairs`), and the other 9 bars fail that, so the twin is dropped and the head stays one note. The conclusion that the second voice reads right but rarely reaches the file is the finding for the landing question.

## LilyPond, Litolff, flag ON (`probe/lily_2_175.py`)
`staged.lilypond.to_lilypond` first raised `Unbalanced` (its own balance did not subtract the twins; 258 surplus); fixed the same way as MusicXML (twin counter, no rest-duplicate count on a doubled copy). Then: `lilypond` exit 0, **22 warnings (17 unterminated tie, 4 cannot end slur, 1 already have slur), 0 errors, 48 pages**; log `out/2.175/lilypond_litolff_on.log`. Whole fast tier after the change: 8,554 passed, 0 failed.
