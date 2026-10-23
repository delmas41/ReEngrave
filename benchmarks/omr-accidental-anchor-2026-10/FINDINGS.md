# 2.199 -- the accidental owner's anchor without a class guess (flag `OMR_ACCIDENTAL_ANCHOR_UNCLASSED`, default OFF)

**Cause (STAGED, `adjudicate_accidental_owner`).** The owner reads the head's height against the glyph's CLASS anchor (`gather._ANCHOR_FRACTION`, from Bravura: a flat's bowl at 0.715 of its box, because its stem rises above the line it names; sharp/natural 0.50). Right when the class is right; a natural boxed as a flat is searched from ~1.4-2 positions below its real height and misses the owner's 1.4 bound -> `no_candidate`. The row already filed `box_centre_position`; nothing used it. **Lesson:** a wrong class is not a local error, it moves a different stage's geometry. Where the class is only a guess, the head search must not rest on it, and a repair must not move any head the class already finds.

**Options measured offline on tree B of 2.197 (frozen sample, `a1_options.py`; control: today's rule reproduces the live verdict 437/439 Litolff, 1383/1384 Brahms, the rest are shape-switched).**
| option | decided heads (Litolff 272 / Brahms 1148) | no_candidate recovered (167 / 236) |
|---|---|---|
| (a) centre for every class | Litolff 12 -> none; Brahms 52 -> none/ambiguous, **12 -> a different head** | 14 / 25 |
| (b) union of offered classes' anchors, all must agree | 26 / 65 become "disagree" | 0 |
| (c) the 2.190 shape reader's class anchor | 145 Brahms / 40 Litolff unread; 5 Brahms -> other head | 9 / 13 |
| **fallback: centre ONLY where the class anchor finds no head AND the shape does not confirm the class (+ no twin box on the same ink)** | **0 moved, 0 lost** | 11 / 21 |
Chosen: the fallback. Strictly additive, so it cannot fail the 2.200 control (every decided pair keeps its head: 272 + 1148 same head offline; no accidental lost or changed in the exported file, below). Re-centring the flat anchor (2.200's advice) was measured too (`a2_recentre.py`): the flat bias is real on Litolff (median head-anchor -0.30) and absent on Brahms (-0.04); shifting by -0.42 changes 1 Litolff and 3 Brahms decided heads, so it fails the control and was not built.

**A bug the first run found (and the lane report caught).** First version lost 22 correct naturals on Litolff: the recovered flat box was a TWIN of an ink whose natural already owned the head, and EVALUATE's contradiction rule (two glyphs, two alterations on one head -> nothing written) dropped both. Fix: no second search when another accidental box covers >= 0.3 of the smaller box (`twin_of`). After it: accidentals lost 0.

**Three measures (`lane_report`, frozen sample, replay).** (1) Litolff: accidentals +5, pitches ~1, blue +2. Brahms: accidentals +13, pitches ~6, blue +12; red bars 266->266, 166->166, nothing lost. Brahms control: ON moves 2 of 12324 duration verdicts (glyph/14/0/12/8/0, /6) -- the consequence of a changed pitch, not looked at further. (2) Tiles: `out/lane-report/2.199b/tiles/sheet.png` (12; 9 changes, 3 controls; key in `out/lane-report/2.199b/key.json`). (3) Judged: right->wrong 0, wrong->right 0.
Near-misses recovered on the sample: 11 of 167 Litolff, 21 of 236 Brahms `no_candidate` (2.197 counted 8 and 22 inside the bound from the centre).

**What my own look at the tiles says (not evidence; Sean's answers are).** The HEAD looks right on every changed tile. The printed accidental is a NATURAL on tiles 3, 4, 5, 8, 10, 11 and a flat on 2, 7(?), so the written type is the detector's label (flat) for most recoveries: written GUESSED (blue, candidates: label + the measured shape), but still the wrong type. 2.199 fixes WHERE the head is; WHAT the glyph is stays a separate problem (shape says natural / unclear on most recovered inks; choosing a class the detector did not offer is INFER, rule 6).
Question for Sean, per tile: "Which accidental is printed directly in front of the boxed note: sharp, flat, natural, or none?" Compare to the label (flat).
