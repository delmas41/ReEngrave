# 2.210 -- a box counts as a note on a stem only if its own ink looks like a notehead (STAGED ADJUDICATE `stem_value`)

CONVENTION ASSUMED: a notehead is an oval blob of its own ink about one space tall at a staff position; a tremolo slash is "never oval, always a thick
diagonal line" crossing the stem (page-facts section 1, Sean 2026-10-15); a stem runs ~3.5 sp past its outermost head.
WHAT WOULD FALSIFY IT: a real head that is flat or fused to its stem and beam (Brahms prints heads as black rectangles beside a sharp and a dot; 5 of 8
boxes read as slashes by the ownership layer are such heads). NOT CONFIRMED by Sean: his 12 tiles (`out/print/2.210/tiles/sheet.png`) are not sent.

## Cause and process lesson (first)

1. Why a non-head is a member: `Q.HEAD_STEM` joins any notehead-classed box that touches a stem; the detector (and GATHER's `stem_end_head`, which
   synthesizes a head at an orphan stem's end from whatever ink is there) boxes beam ends, clef bodies, "ff", slurs and tremolo slashes as heads, and
   no stage asks whether the box's ink is a head.
2. The upstream cause of Sean's two tiles is not the membership: TWO READERS MEASURE THE SAME INK AND DISAGREE. Brahms p12 `/12/0/10/5/8` (tremolo
   slash): the 2.137 refusal (`notehead_precision`, decides `notehead_is_not_a_notehead`) reads the whole box's principal axis at 7.9 degrees, under its
   10-degree floor, and keeps it a note; the 2.205 ownership layer reads the stroke at 15.9 degrees and refuses it as `tremolo_slash_across_a_stem`.
   Nothing consumes that box verdict ("no precision decision reads them yet"). Process lesson: a second measurement of one stroke is a second opinion
   nobody asked for; the rule lives where the stroke is measured (2.205), and every reader consumes it (as the shared ink map says).
3. The membership exclusion cannot remove the phantom note: ON, the slash is no longer a member, still written (own duration quarter) in a chord with
   the real dotted-quarter `/2`; the bar's chord members disagree, so the exporter refuses both notes and the bar goes red (notes -2, dots -2).
   Marked unread, not invented -- but a real note is lost. Hence the flag stays OFF. The fix is upstream (ownership verdict into
   `notehead_is_not_a_notehead`), outside this fence, and only after Sean reads the 8 boxes (below).

## Count (frozen pages, saved 2.202strokes records, ADJUDICATE replay, no gather): 4,415 Litolff + 4,903 Brahms stem members

By kind, from the crops I looked at (rule 7; strata, not a census):
- beam end boxed as a head: the 2.209 set, 7 excluded (2 Brahms, 5 Litolff; Sean tiles 5/5 beam ink); more beam blocks remain members (flat boxes
  with width >= 2.6 x height: 63 members, 20 viewed: 6 beam bars, 1 slur, 1 "ff" bar, 12 slivers (0.2-0.5 sp tall) standing on the edge of a REAL head).
- clef body / clef ink boxed as a head: 6 alto-clef bodies on Litolff (the ownership refusals `head_lens`; records predate 2.208) + 3 clefs/key ink
  among `stem_end_head` boxes.
- dynamic "ff": 1 (Litolff p4 `/4/1/1/4/17`, a 3.3 x 3.3 sp `stem_end_head` over 15 strokes; it already writes no note).
- tremolo slash: 2 of the 8 boxes the ownership layer refuses as one (Brahms p12 `/10/5/8` and `/11/4/6`; the 6 others look like real dotted heads
  with a sharp or flat; Litolff p2 `/1/1/5` is the lower head of a chord).
- a non-head that PASSES A VALUE to another note: of 98 distinct source members of the 88 values `share_stem_value` rewrote, 2 (Brahms beam ends, 2.209).
  So the value harm is small; the file harm is the phantom note.
Ownership `refused` (65 members) is NOT a head test: ~70% of sampled refusals are real heads fused to a stem or beam (`not_a_head_piece`).
Box shape alone is NOT a head test either: boxes 0.5-0.8 sp tall (aspect 2.0-2.6) are mostly real heads with a truncated box.

## What was built (flag `OMR_STEM_MEMBER_INK`, OFF; ON includes the 2.209 test it generalises)
`_non_head_boxes` = beam_end (2.209, two witnesses) + merged_ink (`stem_end_head` box > 2.6 x 2.2 sp over >= 8 strokes: box + stroke map; 4 of 213
qualify, all clef/ff/accidental cluster) + tremolo (ownership REFUSED as a slash AND within 1.5 sp of the tip with a head >= 2.5 sp away, or between two
members). Real heads excluded: 0 of the 9 boxes it excludes on the frozen pages (Litolff 6 = 5 beam ends + the ff; Brahms 3 = 2 beam ends + Sean's slash).
Its first tremolo test (tip witness without the tip distance) excluded a real Litolff chord head and 2 real Brahms heads; the 8-box tip-distance table is the
control (true slashes 0.69 and 1.29 sp from the tip; the others 1.95-3.77). n = 2: it only NARROWS who may vote.

## Measures (frozen sample, `out/lane-report/2.210`, tag = the 2.209 slices; 2.209 was still OFF in that tree, so Brahms includes its changes)
1. File: Litolff nothing changed. Brahms notes -2, dots -2, flags -1 ~1, beams ~1, values ~3, blue +1, words +2; red bars 171 -> 172; notes not written
   3196 -> 3198. Beyond 2.209's own report: notes -2 (the slash and the real `/2`), dots -2, blue +1 (`/12/0/10/5/1`).
2. Tiles: `out/print/2.210/tiles/sheet.png` (key `out/print/2.210/key.json`): 8 ownership "slash" boxes, the ff, the real note `/2`, 2 controls. Not yet sent.
3. Judged right -> wrong: 0 on both plates (wrong -> right 1, Brahms, 2.209's).
Verdict: do not turn ON. Next row (proposal): feed the ownership box verdict into `notehead_is_not_a_notehead` for slashes, after Sean reads the 8 tiles.
Control note: lane_report prints "NEITHER ARM REPRODUCES THE RECORD" (the tree moved since the 2.202 records; same on 2.209).
