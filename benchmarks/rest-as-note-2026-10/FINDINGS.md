# 2.215 Part B: how often is a rest written as a note? (count, no fix; STAGED)

**Cause and lesson first.** 2.213 tile 3 (Brahms p14 `glyph/14/1/0/0/5`) was NOT a rest written as a note: the detector
boxed it `restQuarter` and the exported file writes a quarter REST there on both the OFF and ON arm. The tile boxed a REST
because `lane_report.place()` gave the changed word "dol" its host's box (Part A, fixed in this commit). Lesson (rule 7): the
claim "we write a rest as a note" came from reading a tile whose box was the wrong mark; check the written element in the file
before opening a lane.

**Count** (2.213 OFF arm saved records, `lane-2.206/out/lane-report/2.213/work`, 8 pages per plate; Brahms 4471 notes,
Litolff 3905):
- written note whose own detector box is a rest class: **0 / 0**.
- written note whose box overlaps (>30%, same staff cell) another detector box of a rest class: Brahms **11**, Litolff **48**
  (59 of 8376 = 0.7%). By cause: **head and rest twin-boxed**, 59. Split: restWhole 42 (a black block under a line: head vs
  whole rest, genuinely ambiguous), other rest classes 17 (a rest box on a stem or stem+ledger of a real head: the head is right).
- detector called a rest a head: not countable here (no ink-owner data in the saved mini-record; `unboxed_ink_is_a_rest`
  verdicts are 2146 / 827 but their boxes are not in the record; not located).
- Crops (6 of 59; orange = written note, blue = rest box): 3 restWhole twins ambiguous (block under a line, one in a beamed
  group), 2 rest boxes on a stem of a real head (right note), 1 rest16th on a stem tip. No clear rest written as a note.

**Belongs to:** 2.212 (twin boxes: head and rest of one ink; add the rest classes to its pair list) and 2.205/ink-map ownership
for the stem-hung false rest boxes. No new item; at 0.7% and no clear wrong note, it does not open a lane.
