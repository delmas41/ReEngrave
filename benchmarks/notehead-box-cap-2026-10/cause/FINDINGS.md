# Why notehead boxes come out too big (2.222 cause lane, 2026-10-28)

Written by the manager from the lane's report (the harness refused the lane's own FINDINGS write). Scripts: `cause/trace.py rows`, `trace.py count`.

**Cause.** Nothing in STAGED enlarges a box. Every exported note's box is the detector's own box. On Litolff p2 (426/426) and Brahms p5 (690/690) the kept box matches the raw detector output to within 0.25 px, re-gathered from the detector cache. 3 boxes match by position only: STAGED `stem_end_heads` relabels a whole-rest box as a head. The control can fail: the 2.221 census union box is caught, 2.46 px off. Spacing and corner/width handling are right; median head is 1.40-1.47 sp wide.
The detector boxes the ink it calls a head. On Litolff, touching heads or a head and its stem print as one blob, and it boxes the blob. On Brahms it boxes other marks. Oversized boxes are LOW CONFIDENCE: median 0.29 (Litolff p2) and 0.42 (Brahms p5), against 0.74 and 0.76 for the rest.

**How common** (written notes over 1.9 wide or 1.8 tall; causes by the lane's eye, not Sean's):

| cause | Litolff (108 of 3739) | Brahms (13 of 4430) |
|---|---|---|
| two heads in one blob | 31 (26 written as one note) | 0 |
| head merged with neighbour ink | 27 | 3 |
| one head, just over the cut | 24 | 0 |
| not a notehead | 19 | 10 |
| box runs along the stem | 7 | 0 |
| enlarged by our steps / format slip | 0 | 0 |

**Rescues let them in.** Rescue boxes are oversized far more often: 23% for low-confidence rescues and 10% for stem-end rescues, against 2.3% for production boxes. The gates that admit them:
- `gather.py:470`: floor 0.25;
- `gather.py:505/779/820`: low-confidence rescue at 0.10;
- `stem_end_heads.py:40/208` and `gather.py:1119/1146`: stem-end rescue at 0.05, and a rest relabelled as a head.

**Training labels** are head-only, with no stems. Versions v2-v4 are about 0.3 sp loose, which cannot make a box round two heads.

**Process lesson.** "Too big" measured our READING (one box = one note), not the box. Draw a box next to its ink before calling it loose. The tiles Sean saw were sampled from the oversized tail, which is about 3% of Litolff notes and 0.3% of Brahms notes.

**Proposed fix (words only).** Treat "one box = one head" as a claim to check against the ink. Split a box holding two heads' ink (route it to the stacked-pair readers), or mark it GUESSED/UNREAD; its near-floor score is evidence. Don't cap size: 24 oversized Litolff boxes are real single heads.

**Not traced.** Only 2 pages were checked against raw output. The 7 "beam piece" rectangles are uncertain (tiles for Sean). Box size across weights was not compared.
