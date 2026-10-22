# 2.167e -- the six crops behind Sean's four questions (2026-10-19)

Bar crops are page pixels, nothing of ours drawn. ONE blue box = the symbol the caption names.
STAGED, records 20261018-night. Read with `benchmarks/omr-unwritten-notes-2026-10/FINDINGS.md` section 2.167e.

1. `crop_01` Litolff p5 flute-staff bar 115 (tile 3): one head, a stem and a flag each way. The detector boxed both flags (up 0.59, down 0.48); the record holds ONE head, so the file gets ONE note.
2. `crop_02` Brahms p5 cello bar 79 (tile 4): the second eighth rest. Boxed 0.32 as `rest8th`, refused `rest_is_a_duplicate_box` because a wider box over both rests (itself refused) outranked it.
3. `crop_03` Brahms p19 bar 355 (tile 6): the dot after the quarter. Boxed 0.44 as `augmentationDot`, then `dot_role` read its shape as a staccatissimo wedge, found no head to point at, and abstained.
4. `crop_04` Brahms p8 bar 160 (tile 5): the lower curl of a quarter rest, boxed `noteheadWholeInSpace` 0.28. The rest's own body was read as its "stem". Written a whole note, status READ.
5. `crop_05` Brahms p1 header: the lower loop of the 8 of 6/8, boxed `noteheadWholeOnLine` 0.58. 39 of the 67 whole-valued heads in Brahms are digit loops like this.
6. `crop_06` Litolff p2: a whole REST (black block under a line) boxed `noteheadWholeOnLine` 0.34. 7 of the 8 whole-valued heads in Litolff are rest blocks like this.

Made by `probe/2.167e/e13_crops.py`. The blue box is the glyph's `bbox_page_px` from the record; the look at all 75 whole-valued heads is mine (ours, not Sean's, not evidence).
