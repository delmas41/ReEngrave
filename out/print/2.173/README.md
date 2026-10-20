# 2.173 -- bars that do not add up are written in red (not blind)

Each tile: the PRINT bar on top (nothing of ours drawn on it), and the SAME bar as our LilyPond engraving below,
with `OMR_RED_BARS=1`. Six tiles: Litolff (Beethoven 5) x3, Brahms 1 x3; per plate one SHORT bar, one OVERFULL bar,
one bar that holds a GUESSED note. Chosen at random (seed 173), frame-checked against the print's staff lines.

What red means:

* RED (every note, rest and the bracket over the bar) = **this bar does not add up** to the meter. Sean, 2026-10-19:
  *"Written in red instead of held out is the way to go."* Before, the whole bar was left out of the file.
* The words over the bracket say what was wanted and what was counted, in quarter notes
  ("should hold 2, counted 1.5").
* Every note is written exactly as it was read, at its own value. Nothing is invented and **no rest is added**.
  A short bar is left short (an invisible skip fills the time on the LilyPond clock; it prints nothing). An overfull bar keeps
  every printed note shape; only the engraver's clock is fitted, so the staves still line up.
* A note that was only GUESSED would be blue in an ordinary bar. In a red bar it is drawn red like the rest; the file's data
  still says READ or GUESSED for each note (`bars_written_red.bars_list[].rows[].status` in the export report).
* Black/blue elsewhere are unchanged: black = read, blue = guessed, red bracket reading "unread" = a stretch not read.
