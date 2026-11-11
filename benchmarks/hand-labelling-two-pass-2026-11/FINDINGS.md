# 2.287 — Hand labelling in two passes, the way the page is read (2026-11-10)

LABELLING TOOL only (`tools/omr/annotate/`, `tools/omr/hand_truth/pagepass.py` + cell pass); no pipeline change.
Branch `lane-2.287-page-labelling` (r1 47ed1affe, r2 44957bc71, r3 46da325e2; Sean's labels merged at 7080ca094 and
later snapshots). NOT on main yet: held until Sean has used the cell pass. Written by the manager from the lane
reports (the lanes' Writes were refused).

## Cause and process lesson
Sean labelled Brahms p0 one cell at a time, so a slur, tie or hairpin crossing a barline was drawn as cut pieces, while
the reader now reads those marks once on the whole page: the truth was at a finer grain than the reader. Sean
(2026-11-10): "I probably need to label it the way it is being read. I take a pass at a page where I label what the
pipeline will label at a page level and then take another pass after all of that ink is claimed on a cell level."
Lessons: the labelling tool moves with the reader whenever the reader changes grain; ink accounting must be VISIBLE
(his eyes are the cheapest check); a pass the user cannot reach in one command does not exist for him.

## What the tool does
One command gives both passes:

    python3 -m tools.omr.annotate.server --page-pass --page-store data/hand-truth/pages/imslp317803/0.json \
        --arc-key data/hand-truth/prefill/imslp317803-0.arc-key-2.281.json --port 5070
    # http://127.0.0.1:5070/page   and   /cellpass

- PAGE PASS (r1): whole page, kinds in claim order (staff, barline, bracket, clef, key, meter, word, dynamic, arc,
  hairpin, repeat), one kind active; a label claims INK by a per-kind rule, not its rectangle; ink coloured live —
  vermilion unclaimed, blue confirmed, purple dashed pre-fill, green cell pass — with a legend and "% of the page's
  ink claimed". Pre-fills (never truth): his old labels for page-wide kinds and the 2.281 corrected arc key.
- r2 (Sean's six points): a bracket takes only its own tall stroke; a rectangle takes a connected piece whole if at
  least half is inside, none otherwise (a polygon cuts at its edge); between two confirmed labels the TIGHTER shape
  wins whatever the kinds; contested ink shown yellow; selecting a label shows exactly the ink it owns; full-height
  barline pre-fills; a meter is ONE box with a typed value (digits kept underneath in `parts`); a word BLOCK (title /
  subtitle / composer) as one box; +/- and wheel zoom at the pointer; the view pans while a box is dragged past the
  edge. Keys moved: hairpin `v`, repeat `r`.
- CELL PASS (r3): built from the page file's recorded cells + the page render (no bench, no detector); page-pass ink
  is final (blue) and cannot be labelled again; his 1,232 old cell boxes return as pending pre-fills for cell-level
  kinds (334 page-wide ones dropped); the left-over ink is split by shape so a head label does not take the stem;
  `Shift+T` confirms all pending of one kind in one cell (`u` undoes); a cell list with % of ink still unclaimed;
  "PAGE DONE" when no ink is unclaimed and nothing waits. Labels go to `0.cellpass.json`.

## Sean's truth so far (Brahms p0, page pass complete)
14 staves, 15 full-height barlines, 4 brackets, 15 clefs, 10 keys, 27 meters, 34 words, 14 dynamics, 98 arcs confirmed
(`0.pagepass.json` on the lane branch; a copy at out/print-from-worktrees/2.287-r1/0.pagepass.sean-snapshot2.json).
His original `0.json` is untouched. Used read-only by 2.293 (ink count vs his labels) and the arc gate (98 arcs).

## Rulings that bind the next round
- Where a mark crosses a staff line the crossing ink is the MARK's (page-facts §3, 2026-11-10): the staff label must
  stop taking crossing pixels — follow the eraser's rule (ink no taller than the line is the line).
- Brahms p0's old per-cell labels are NOT a standing test (DECISIONS 2026-11-10).

## Not verified / open
Nobody has done a real cell-pass session; 61 old boxes claim no ink under their kind's rule (many beams); the ink
rule constants are tuned on Brahms p0 only (Litolff, which merges more, untried); only Chrome tried. Fast tier on the
branch: r1 10130, r2 10144, r3 10165 passed, 0 failed.
