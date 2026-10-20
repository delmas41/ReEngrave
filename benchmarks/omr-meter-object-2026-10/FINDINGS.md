# ROADMAP 2.177 -- the meter is ONE object: two numbers, one claimed area

Path: STAGED. GATHER (a new `Q.METER_OBJECT` row) + ADJUDICATE (one refusal, `inside_the_meter`). Flag `OMR_METER_OBJECT`, default OFF.
Sean, 2026-10-20: "we need a real fix for digit meter- Something that sees the meter as 2 numbers and blocks the whole thing out and
thepulls out the 2 numbers and doesnt allow anything else to box that area."

## DESIGN NOTE (written before the build; plain words, for Sean)

**What is wrong today.** Meter ink is read by readers that never meet: the detector draws `timeSig*` boxes (often one per
numeral, often shattered or doubled: on Litolff p1 system 0 it draws boxes on 7 of the 12 staves, with classes `timeSig2` and
`timeSig4` stacked on one staff); the template reader says "2/4" for a whole staff but gives no place; Tesseract mostly
abstains; and the notehead decider has three separate per-class patches (2.12l pair test, 2.173 whole-class `on_a_read_meter`,
the parked 2.176b stemless rule). The digit loops of a 6/8 get boxed as black/half/whole heads; each patch catches some.

**How the meter object is found.** One object per printed time signature, per staff, at every place one is printed (the movement's
opening system, every meter change; a printed cautionary meter at a system's end is the same ink and is found the same way). Three
things connect and none guesses:
1. *Ink.* On the page raster, with the bare staff lines taken out, a printed meter is two bold numerals one above the other in one
   column, one in the upper two spaces of the staff and one in the lower two (or a single C / cut-C of two to three spaces tall).
   The finder looks for exactly that pair of ink pieces, in the staff's header or in the first few spaces after a barline.
2. *A witness that a meter stands here.* The pair becomes an object only if existing evidence agrees: a detector `timeSig*` box
   overlaps it, or the template/OCR reader read a meter on this staff (header) or at this bar (`*_AT_BAR`). A stacked pair of ink
   pieces with no such witness is NOT claimed.
3. *The same column on the other staves.* A meter is printed on every staff of a system at one bar (page-facts). Each object records
   how many other staves of its system have an object in the same column; a lone object is kept but marked, never upgraded.

**How its area is drawn.** The box around the ink of the two numerals themselves (measured on the raster, not copied from a detector
box and not a column rule), padded by one stroke width; one box per staff. It must be about two numerals wide (up to ~2.6 spaces),
2 to 4.6 spaces tall, and stand clear of the clef and key accidentals: ink that merges with a neighbour (one piece wider or taller
than a numeral pair can be) makes the finder ABSTAIN with that reason, never shrink or guess.

**How the two numbers are read.** Pulled out of the object from sources already on the record, never invented: the top numeral from
the detector's digit boxes inside the object's upper half and the template reader's numerator; the bottom likewise from its lower
half and the denominator (a C / cut-C from `timeSigCommon` / `timeSigCutCommon`). They agree -> recorded as read, with sources. One
source only -> recorded, marked one-reader. Disagree or none -> the object still claims its area but the numbers abstain with every
candidate listed. The meter DECISION (`Q.METER`) is untouched: this row feeds the box refusal; the reading is reported beside the dossier.

**What is refused.** Any other box whose own INK lies inside the object's area: a notehead box of every class (black, half, whole,
double whole), a rest box, and where their decisions can already read it an accidental, a flag, a dot. Reason `inside_the_meter`.
Refused, never re-valued; they stay on the record as boxes and export counts them under `not_a_notehead:inside_the_meter`. The
measure is the share of the OTHER box's ink that lies inside the area (ink on ink, not box on box). 2.173's `on_a_read_meter` stays
as it is (whole-class boxes, needs no object); a test pins that both refuse the 2.176 tile-8 kind (the top loop of a numeral 8).

**What is protected.**
- *The first note after the meter*: a head that only touches the object's edge is kept; refusal needs most of the box's ink inside.
- *Stemmed heads*: a head a stem touches is a note and is never refused by this rule (rule 8); the 24 stemmed chord notes of 2.176b
  are the must-keep controls.
- *Key-signature accidentals and the clef*: the area is measured from numeral ink only, starts right of them, and an area that would
  swallow them is not drawn (abstain `merged_with_neighbour`).
- *Anything where no pair is found*: nothing claimed, nothing refused.

CONVENTION ASSUMED: a printed meter is two stacked bold numerals (or C) between the key signature and the first note, at one x on
every staff of the system. WHAT WOULD FALSIFY IT: a print-confirmed head inside a claimed area, or numerals printed side by side.
NOT CONFIRMED beyond the two plates measured below; blind tiles `out/print/2.177-review/`.

**Sean, 2026-10-20 (asked: "At a 6/8 change bar, is anything ever printed between the two numerals and the first note?"):** "it is posible for
there to be things in between the meter and the first notes but nothing that would overlap with the meter digits." The claim is therefore exactly the
digits' own ink box (+ one stroke), never the gap after it; a must-keep control (`test_CONTROL_ink_just_right_of_the_numerals_is_outside_the_claim`) pins it.

## Brief from the tree (what finds meter ink today)

(filled in below as measured)
