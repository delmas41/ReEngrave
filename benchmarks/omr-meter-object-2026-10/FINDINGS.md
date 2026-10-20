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

- Detector `timeSig*` boxes (`Q.METER_GLYPH`, cell-wise): shattered and doubled (Litolff p1 system 0: boxes on 7 of 12 staves); Brahms p0: boxes on every staff
  at one x. Template reader (`Q.METER_TEMPLATE`, header crop): reads "2/4" on 12 of 12 Litolff staves, no x position; OCR abstains; `*_AT_BAR` reads for changes.
- Existing meter-ink rules: 2.12l pair test, 2.173 `on_a_read_meter` (whole-class only), `key_slots.meter_column` (18 spaces, rests only).

## Measurement (20261018-night records replayed from per-page slices; flag OFF vs ON; exported file) -- `replay_2_177.py`, `compare_2_177.py`

Method note: the records predate the new row, so `gather.gather_meter_object` was run on the page raster (600 dpi) with shim inputs rebuilt from the record's
own rows, then ADJUDICATE..INFER..EXPORT re-ran. Same function as the pipeline's.

| | Litolff | Brahms |
|---|---|---|
| objects found / expected | 12 / 12 (opening 2/4 on 12 staves; no change) | 52 / 56 (opening 6/8 14/14; 9/8 at measure 8: 10/14; the 9/8 repeated at p1 system start 14/14; 6/8 at measure 9: 14/14) |
| numbers read vs dossier | 2/4 read on 11 staves (7 numerator+denominator one-reader, 4 two-source), 1 numerator abstained; 0 wrong | 6/8, 9/8, 9/8, 6/8 all as the dossier; some staves abstain a digit; 0 wrong |
| heads refused `inside_the_meter` | 0 (no digits boxed as heads on Litolff) | 74 (67 already refused by another rule), 7 newly refused; every one of the 7 looked at: a loop of a 6/9/8 numeral |
| rests newly refused | 0 | 4 (all the numeral 6 boxed as a rest, looked at) |
| rests restored (18-space column no longer consulted) | 2 -- looked at: BOTH are key-signature flat ink, so 2 false rests now written (cost, owned by the key-signature claim, 2.178 step 3) | 19 -- 8 looked at: real eighth/whole rests |
| decided real notes lost | 0 | 0 (the 7 newly refused "decided notes" are numeral loops) |
| notes in the file | 10860 -> 10862 | 22151 -> 22164 |
| Sean's judged tiles (`judged score`) | unchanged (137/25/6/1/15/103) | not rerun on this plate (the judged set is Litolff/Brahms mixed: Litolff score unchanged) |
| claim ink-share list | 6 non-staff boxes >= 0.5, all already refused | 84 >= 0.5 (78 heads/rests refused, 2 ties not covered); 0 heads/rests between 0.1 and 0.5 (the only near-misses are ties and beams, not claimed) |

2.173's `on_a_read_meter` is unchanged; `test_2_173_and_2_177_both_refuse_the_tile_8_kind` pins both. Quantity renamed `Q.CLAIMED_AREA` (owner `meter`, unit
`area`, filed on the STAFF with `owner_row`, `standing`) per docs/plan-2026-10-20-claimed-area.md step 1; reason kept `inside_the_meter`.

Misses: 4 Brahms staves at the measure-8 change (9/8) have no pair found (shattered ink); 33 witness-less and 35 no-pair places are abstentions on the record.
Finder history: the C-clef is as dense and tall as a numeral pair, so detector clef/key boxes are `avoid` boxes; where the numeral touches a key flat (Brahms p0) the
detector's own timeSig x-column gives a window that cuts the neighbour off.
Blind tiles: `out/print/2.177-review/` (12), key `out/print/2.177-key.json`.
