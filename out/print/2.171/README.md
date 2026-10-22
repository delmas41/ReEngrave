# 2.171: one symbol under three conditions (6 crops, NOT blind, our own picks)

Each crop is ONE symbol shown to the detector three ways, side by side. Each frame is the actual input the detector was handed (the letterboxed array), cut to a
112 x 112 network-pixel window around the symbol and enlarged x4 without smoothing, so the pixel size you see is the pixel size the detector saw.
Frames of different staff-space sizes are cut to the same number of network pixels, so a smaller view shows more music around the symbol.

Colours and marks
- BLUE thin frame = where the symbol is (our look at 2.167d, not Sean's and not evidence). For crop 2 (a flag with no box at all) it is a tall band over the staff at the symbol's place.
- GREEN frame = the detector's best box of the right family over it, at 0.25 or more (kept by GATHER).
- ORANGE frame = the same, under 0.25 (GATHER throws it away).
- No frame = no box of that family at 0.05 or more.
- The line under each title prints the conf and class; the line under that prints the staff space the detector was shown (16 px is production) and the size of its input.
- Light grey = outside the input the detector was given; darker grey = the letterbox fill (114) the production feed adds.
- The conf printed is checked against the experiment (`probe/2.171/e7_crops.py`); every frame agrees to 0.01.

Frames: "production bar crop" = exactly what the pipeline does. "wider crop, same pixel size" = half a bar added each side, resized so the symbol has the same pixel size as in
the bar crop. "0.5 x / 0.7 x smaller", "1.4 x larger" = the same bar crop shown at that fraction of the staff space. "bar on wide WHITE canvas" = the bar crop alone, with blank white
on both sides instead of the neighbouring bars.

1. Brahms dot, 0.13 in the bar crop. Wider crop 0.46; a 0.7 x smaller view 0.65. Same ink, same pixels.
2. Brahms flag with no box at all in the bar crop. Smaller view 0.77; the wider crop only 0.06.
3. Brahms dot read well (0.79). Smaller view 0.51 (still read); the wider crop 0.77. Shows what the same changes do to a symbol that was fine.
4. Litolff black head squared into a block between two lines (the record called it a rest at 0.35). Larger view 0.47 as a head; wider crop 0.20.
5. Litolff quarter rest, only a 0.10 black-head box in the bar crop. Smaller view 0.46 as a rest; the wider crop finds nothing.
6. Brahms dot 0.16. Wider crop 0.41; the same bar on blank white canvas finds nothing: the neighbouring ink did it, not the bigger canvas.

`index.json` lists page, system, staff, cell, the box in page pixels and every frame's conf. Made by `probe/2.171/e7_crops.py`.
