# 2.173 -- bars that do not add up are written in red (not blind)

Each tile: the PRINT bar on top (nothing of ours drawn on it), and the SAME bar as our LilyPond engraving below,
with `OMR_RED_BARS=1`. Six tiles: Litolff (Beethoven 5) x3, Brahms 1 x3; per plate one SHORT bar, one OVERFULL bar,
one bar that holds a GUESSED note (blue). Chosen at random (seed 173), frame-checked against the print's staff lines.

What the colours mean (Sean, 2026-10-19: *"Each note with its own color"*):

* The red BRACKET and its words over the bar = **this bar does not add up** to the meter ("should hold 2, counted 1.5", in
  quarter notes). Before, the whole bar was left out of the file.
* Each note and rest keeps ITS OWN colour: **black = read, blue = guessed**; red is used on a note only where that note is itself
  unread, as in any other bar.
* Every note is written exactly as it was read, at its own value. Nothing is invented and **no rest is added**. A short bar is
  left short (an invisible skip fills the time on the LilyPond clock; it prints nothing). An overfull bar keeps every printed note
  shape; only the engraver's clock is fitted, so the staves still line up.
* The file's data also says READ or GUESSED per note (`bars_written_red.bars_list[].rows[].status` in the export report).
* Red bracket reading "unread" elsewhere = a stretch not read.
