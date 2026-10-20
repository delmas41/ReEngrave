# 2.176 -- non-notes written as notes on Brahms (and Litolff for contrast)

STAGED GATHER+ADJUDICATE (notehead precision). Records: 20261018-night (Brahms 317803, Litolff 984073), main 07608d9c6. Probes in this directory:
`sample_2_176.py` (random sample), `crops_2_176.py` (my looking aid: plain crop beside the same crop with the box in blue; mine, not evidence),
`census_2_176.py` (other-class overlap census), `replay_2_176.py` / `compare_2_176.py` (whole-record replay through export, flag OFF vs ON),
`tiles_2_176.py` (blind tiles). Everything below that says "non-note" is my own reading of crops, not Sean's and not the print's reference.

## 1. The premise is half wrong: most of the non-notes 2.174 saw are already refused

2.174 said over half of Brahms's "decided quarters with beam ink nearby" are not notes. Joined to the live `notehead_is_not_a_notehead` verdicts of the same
record, 1,044 of that population's 2,042 (51%) are already REFUSED (`too_narrow` 937 = barline slivers, `clipped_fragment` 45, `is_a_rest_twin` 24,
`belongs_to_a_nearer_staff` 9, `is_a_clef` 9, duplicate/stacked 17, ...). Export drops a refused head and counts it under `not_a_notehead:<reason>`; it never
reaches the file. Litolff: 118 of 651 (18%). 2.174's census and sample counted the duration rows without the refusal verdict, so its sample included them. The sample
was right that they are not notes; it was wrong that they are written.

## 2. Step 1 -- what is left, by random look

Duration-decided, not-a-rest heads, split by whether their bar is held out (`bars_held_out_sum`), seeds 2176 and 2177, never filtered on how they look.

| sample | drawn | already refused by a shipped gate | looked at, not refused | non-notes among those |
|---|---|---|---|---|
| Brahms WRITTEN (decided, bar not held) | 90 of 14,295 | 9 (`too_narrow` 7, `clipped_fragment`, key slot) | 81 | **0** |
| Brahms HELD bars, draw 1 | 45 of 4,345 | 5 (duplicate box 2, `too_narrow` 3) | 40 | 3 |
| Brahms HELD bars, draw 2 (unrefused only) | 100 of 2,851 | 0 | 70 looked at (30 not) | 6 |
| Litolff WRITTEN | 45 of 7,698 | 6 (stacked/duplicate 5, beam piece 1) | 39 | 2 clear, 3 unclear blobs |

Non-note rate among heads that reach the file or sit in a held bar: **Brahms written 0 of 81** (95% upper bound about 4%); **Brahms held 9 of 110 (8%)**;
**Litolff written 2 of 39 clear (5%), up to 5 of 39 with the unclear blobs** (merged ink: a head, an accidental and a beam are one black mass, so I could not always say).
Brahms's held bars carry them (2,851 unrefused held heads; 8% is about 230 boxes in about 890 held bars), Brahms's file does not.

What the 9 Brahms held non-notes are (each passed every gate: the box is head-sized, so `too_narrow`/`is_a_dot` do not fire; no rest box (2.142); no stem for 2.49):

| kind | n | what it is |
|---|---|---|
| the staff's leading barline / brace | 3 | a box on the thick vertical bar left of the first clef, in the system's first cell |
| accidental (a sharp stack, a key-signature flat bowl) | 2 | detector class `noteheadBlack*`/`Half*` on an accidental's ink |
| a piece of a curled rest | 1 | `noteheadWhole*` on a rest's curl (2.173's) |
| the hook of a dynamic ff | 1 | other gates (2.73, 2.107) own dynamic letters; this one is a hook |
| meter digit "8" of a 6/8 | 1 | the hollow loop (2.12l's pair test did not fire) |
| a slur's end | 1 | a slur fragment boxed as a head |

Census over every unrefused decided Brahms head (15,469): how many sit ON a box of a different detector class (cover >= 0.5): rests ~46, accidentals ~25, dynamics ~14,
clefs ~7, flags ~260 (real heads: a down-flag's box holds its head, not a signal), ties/slurs (normal). Most of the rest/accidental ones are REAL notes (a restWhole
box on a head with a flag: the detector's rest class was wrong, the head right). The only kinds with a clean cut were the leading barline and clef boxes.

## 3. Step 2 -- the fix, and the families I tried and dropped

Flag **`OMR_HEAD_ON_ANOTHER_MARK`, default OFF** (`adjudicators/head_on_mark.py`, called from `adjudicate_notehead_is_not_a_notehead`). A refused head is
refused (unread), never re-valued. Two reasons, both with a signed margin (`margins.PARTIAL`):

* `on_the_staffs_leading_barline` -- cell 0 of a system, head box's left edge within 0.5 staff space of the cell's left edge. Connects to cell geometry: that is where
  the system barline and brace are printed, and CLAUDE.md §4 says only a clef stands before the key accidentals. **The cut is FITTED on Brahms: 23 boxes between 0.00 and
  0.44 sp, none between 0.44 and 1.0 (Litolff: 1 at 0.01). NOT CONFIRMED on another publisher; WHAT WOULD FALSIFY IT: a print-confirmed head within 0.5 sp of a
  system's left end.**
* `on_another_symbols_box` -- the head box lies inside a `clef*` box (cover >= 0.9) that starts within 6 staff spaces of its cell's left edge, the clef box's detector
  score is at least the head's, and no `Q.STEM` touches the head. Connects to the detector's own other-class box and its confidence. The guards each came from a real note
  the first build fired on: a "clefF" box 12 sp into a bar on a head under "a 2" (`glyph/6/0/3/0/20`), and Litolff half/quarter heads inside `clefG`/`clefF` boxes the
  detector scored higher (`glyph/9/0/3/11/1`, `16/1/7/2/6`).

**Tried and DROPPED**: the same cover test on ACCIDENTAL boxes and curled-REST boxes (detector score >= the head's, no stem). Brahms: 1 refusal, a non-note. Litolff: 4
of its 11 boxes looked like real heads in the print (a hollow half-note head among them): its merged blobs put the accidental and the head in one ink. A rule that is right
on one plate and wrong on the other is not a connection, so it is out; accidentals remain an open kind (Brahms held 2 of 110).

## 4. Step 3 -- measured on the EXPORTED FILE (whole-record replay, OFF vs ON, current main defaults)

| | Brahms OFF | Brahms ON | Litolff OFF | Litolff ON |
|---|---|---|---|---|
| notes in the file (`written.notes`) | 12,176 | 12,200 (+24) | 6,686 | 6,688 (+2) |
| notes held out by the bar sum | 3,896 | 3,837 (-59) | 1,536 | 1,532 (-4) |
| held bars | 890 | 882 (-8: 9 released, 1 newly held) | 618 | 616 (-2) |
| partial bars | 519 | 520 | 169 | 169 |
| bars that add up (events - held - partial) | 4,886 | 4,893 (+7) | 4,269 | 4,270 (+1) |
| heads refused | 4,722 | 4,759 (+37: 32 leading edge, 5 clef) | 1,645 | 1,647 (+2) |

The OFF arm reproduces 2.174's OFF arm to the unit (12,176 / 890). Notes in the file rise because a bar that held out for a fake event now sums (9 Brahms bars released).
The newly held Brahms bar (`6/1/9/0`) was not examined; it lost an event that was a bass-clef curl.

**Non-notes removed**: 37 Brahms + 2 Litolff boxes, every one looked at in a crop. **Real notes lost: 0 of 39.** By reason: Brahms 32 leading edge (31 barline/brace boxes,
1 caesura sign "//" at a bar start) and 5 clef (bass-clef head or dots); Litolff 1 leading edge, 1 clef. 25 of the 37 Brahms boxes were duration-decided, 9 narrowed, 3 abstained.
**Judged (Sean's answers, `judged score`): identical totals OFF and ON** on both plates (Brahms right 129 / wrong 22 / narrowed 5 / abstained 0 / not found 19 / unscored 191;
Litolff 159 / 29 / 6 / 1 / 20 / 129). No judged tile is touched, which is also a limit: none of his tiles stand at a system's left edge.

## 5. What did not get fixed (the next kinds, 1 in 110 each on Brahms held bars)

Accidental stacks and key-signature flat bowls boxed as heads; a dynamic's hook; a meter-digit loop; a slur's end; a curled rest piece; text letters ("e" of "cresc."); and on
Litolff, merged black blobs (an accidental, a head and a beam in one mass) that no overlap test separates. These need a different witness than another class's box.

## 6. Blind tiles

`out/print/2.176-review/` (12): 9 refused boxes (7 Brahms, 2 Litolff) and 3 controls (real heads the flag keeps: a half head in a clefG box the detector scored
higher; a head under "a 2" inside a clefF box 12 sp into the bar; a head 4.5 sp into a system's first bar). One blue box each, nothing else of ours. Key
`out/2.176/tiles-key.json` (outside the tiles folder), made by the same `tiles_2_176.py` run, and the script asserts every tile's blue box equals its key row's box.
Question: is the thing in the blue box a notehead? If not, what is it?
