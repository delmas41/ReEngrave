# GATHER by zoom layers — FINDINGS

## 2.152 -- GATHER by zoom layers (study; STAGED GATHER+ADJUDICATE; no product code)

**CONVENTION ASSUMED:** a reader takes in the page, then the system, then the cell (Sean 2026-10-16: *"My eyes adjust
when they are looking at a page and start by taking everything in and then zoom in by layers"*). So a symbol's reading
can be checked against (P1) this page's or document's own instances of its class, (S1) the band of the system it sits
in, and (S2) the other staves of its system at its x. **WHAT WOULD FALSIFY IT:** context facts that catch no more of
Sean's judged errors than the cell readers already do, or that flag right readings as often as wrong ones. **NOT
CONFIRMED:** the classification of each error is the lane's measurement against Sean's own tile answers; "the lane's
look" at held bars is not Sean's. Two plates only.

Lane `lane-2.152-zoom-layers` (`07940509`, probes and raw outputs in `probe/` and `probe/out/`). The lane agent could
not write this file (its harness refused the Write); the manager wrote it from `probe/out/*.txt`.

### 2.152-1. Method
* **Errors with truth:** every tile in Sean's judged index (`python3 -m tools.omr.staged.judged`) plus the 2.145-2.151
  answer files, de-duplicated: 327 tiles; **84 errors** (Litolff 34, Brahms night record 28, Brahms p0-p3 22) and 138
  right readings as the control. Kinds: 28 value errors, 21 rest-as-head, 15 phantom heads, 15 phantom rests, 3 lost
  rests, 2 lost notes (`probe/out/counts.txt`).
* **Facts measured on each box** (`probe/tiles.py`): P1 a robust z of the box's width/height against the page's (or
  document's) DECIDED readings of its class; S1 vertical/horizontal band (off-staff distance, nearer staff, the
  system-start/header column); S2 onset partner on other staves (a1/a1.5/a3 tolerance) and header-column echo (a
  head/rest box where at least half the system's other staves carry a clef, key or meter mark). The shipped fixed
  windows (2.148 head box, 2.150 rest width) are scored beside them.
* **Held bars** (record `20261014-night`): every kept glyph scored with the same facts; flagged rate in held bars vs
  other bars (`probe/sweep.py`, `sweep_*.txt`). Held bars have no truth: a ratio says "where held bars are", not "right".

### 2.152-2. Reach (errors caught / right readings wrongly flagged)
| fact | Litolff | Brahms night | Brahms p0-p3 | all |
|---|--:|--:|--:|--:|
| P1 page census, z > 4 | 15/33, 4/70 | 24/26, 1/61 | 7/22, 0/4 | 46/81, 5/135 |
| P1 document census, z > 4 | 17/34, 3/71 | 24/28, 2/62 | 6/22, 0/5 | 47/84, 5/138 |
| S1 staff band (any) | 1/34, 5/71 | 1/28, 10/62 | 7/22, 1/5 | 9/84, 16/138 |
| S2 header-column echo | 1/34, 0/71 | 0/28, 0/62 | 1/22, 0/5 | 2/84, 0/138 |

**The census mostly re-finds what the fixed windows already catch.** Head-class boxes only (`headtohead.txt`): on
the size-blind galleries (tiles NOT picked by box size, 36 errors / 126 right), P1 page z>4 catches 17 with 3 right
flagged; the shipped 2.148 window catches 15 with 1. Of the 36: census only 2, fixed window only 0, both 15, **neither
19**. On all galleries the Brahms night column (24/26) is inflated: the 2.150 tiles were picked BY width, so a width
census was bound to catch them. The census also refuses Sean's real 0.47-space quarter rest (2.150 tile 11, z 8.77),
the same box the fixed floor got wrong.
**A page is no tighter than its document:** across Brahms pages the median head width moves by sd 0.03 space, against
a within-page spread (MAD) of 0.05-0.09.
**Whole movements** (`sweep_*.txt`): P1 page z>4 flags 7.8% of Brahms kept glyphs (2,018 of 25,986) and 10.5% of
Litolff's; held bars carry a flag 2.4x / 1.9x as often as other bars, so most flags fall in bars that are not held. As
a narrowing it would turn about one glyph in ten blue. S1 vertical bands: ratio 1.2 (no signal: far notes on ledger
lines look the same). S2 header-column echo (S1h or S2b): 99 / 38 glyphs, held-bar ratio 9.5x / 6.1x, but only
3.0% / 2.4% of held bars.

### 2.152-3. What no context layer reaches
36 of 84 errors are reached by no page or system fact: mostly value errors (head value, beam count: e.g. 2.151 tiles
7, 21, 28, 8, 10) and slashes/rests that are head-sized. These need the cell (ink, stroke, beam count), not context.

### 2.152-4. Ranked proposal
1. **System header-column echo** as a NARROWING row (a head/rest box standing in the column where the other staves
   print a clef, key or meter is sent back, never decided): precise (0 right readings flagged on both controls,
   held-bar ratio 6-10x) but small (2-3% of held bars). Fix its system-start rule first: the lane saw it flag real
   Brahms notes at the first beat after the header.
2. **A per-document class census filed as a GATHER row with no behaviour change** -- its value is not new catches on
   these two plates (it re-finds the fixed windows) but PORTABILITY: on a third publisher it replaces numbers tuned on
   Litolff and Brahms with the plate's own (CLAUDE.md §4: "a cut-off is a measurement"). Only measurable on a third
   plate.
3. **Do not build** the staff-band or onset-partner facts (no separation; they flag ledger-line notes and second
   voices as often as errors).

### 2.152-5. Limits
Two plates; a third publisher (where the page layer should matter most) not checked. Tile galleries were cut for
other questions, so the error mix is theirs, not the movement's. The census baseline is built from our own decided
readings and contains their errors (rule 7: not an independent witness of the same raster). Held bars have no truth.
