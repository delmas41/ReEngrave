# Facts about the page that are load-bearing

Each of these has cost at least one lane and is still true. Moved out of
`CLAUDE.md` §10 on 2026-10-13 (`docs/claude-md-migration-2026-10-13.md`),
with Sean's rulings of 2026-10-12/13 added at the end. Sean's rulings are
the dated lines in `docs/DECISIONS.md`. How the two relate (Sean,
2026-10-13):

1. **They must never quietly disagree.** When a ruling changes or narrows a
   fact here, this file is updated in the same commit, saying where it
   applies.
2. **Every ruling carries its scope**: general, or a named publisher /
   score / kind of staff. A scoped ruling is never applied outside it.
3. **A lane that finds the two disagreeing does not pick a winner.** It
   stops and asks Sean (with a crop where that helps).

The conventions registry (`tools/omr/conventions.py`) is the
machine-readable form.

## 1. Rhythm and notation

- A whole rest means the BAR whatever the meter; a lone quarter rest does
  not. A lone dotless whole rest is the bar, sized to the `<time>` in force
  (ROADMAP 2.98, print-confirmed 12 of 12, 2026-10-12).
- **A whole or half rest never touches two staff lines** (Sean, 2026-09-29:
  *"The rest should never touch 2 different staff lines."*; scope: whole and
  half rests only; ROADMAP 2.35). **A bar with no notes expects a whole rest**
  (2026-10-01: *"Every measure should have notes or rests."*; accidentals,
  ties and stems each imply notes there; ROADMAP 2.55). **Proximity proves
  nothing**: a rest box and a note box overlapping are two marks *"very close
  together"* (2026-09-29), and a whole rest in a bar refuses no notehead
  (2026-10-01, *"Leave the whole rest alone"*).
- **Reading order** (Sean, 2026-10-16: *"Notehead first, stem second, beam or
  flag third"*, then chords sharing a stem, then a tremolo slash or anything
  else; scope: general; ROADMAP 2.149): a later step reads the earlier
  answers and never overturns them, and a head reading *"should not be able
  to be overturned without significant proof"* (2.148).
- **Beam, flag, slash** (Sean, scope: general; ROADMAP 2.69-2.74, 2.126,
  2.146, 2.194): *"A beam must not only connect to its note but also to
  another note"* and *"A beam never has an arc"*, and it is thicker than a
  hairpin's line (2026-10-09); open heads are never beamed except tremolo
  (2026-09-30); *"A hollow note with nothing on the stem is always a half
  note"* (2026-10-09); a flag hook hangs from ONE side of the stem tip, a
  slash crosses both; a hook seen rules out a quarter (2026-10-09); a flag
  seen on a stem is a flag even inside a detector "beam" box (2026-10-22: *"if
  there is a flag it should be treated as a flag"*); *"Clean tip means no
  beam"* (2026-10-16); a staff line between a beam and its stem is not a gap
  (2026-10-15).
- **Heads sharing one stem** (Sean, 2026-10-17: two heads that disagree "can't
  be decided"; scope: general; ROADMAP 2.165): two that disagree leave the
  value UNDECIDED; with three or more, one dissenter makes the value GUESSED
  (blue) to the majority.
- **Stems and voices** (Sean, 2026-10-10/11; scope: general; ROADMAP 2.12m,
  2.87): *"All stems should be connected to a notehead"* -- a check at a LATER
  stage, never a GATHER refusal; *"When one note has stems going up and down it
  is always 2 voices"* (a unison), so such a head is never collapsed.
- **An augmentation dot always stands in a SPACE, never on a line** (Sean, 2026-10-14: *"Always in a space"*; scope: general engraving; ROADMAP 2.128): in its note's own space; after a note on a line, in the space **above** by default, and **below** for the lower (stems-down) voice of two on one staff or the lower note of a second in a chord (Sean, same day, *"Yes"* to the researched rule; PROVISIONAL for 19th-c. German plates -- Brahms p.0 labels: 41 above, 15 apparent "below" are the lower chord partner's above-dot, 4 are a lower voice, 0 contradictions). Registry: `docs/engraving-conventions.md`.
- **A tremolo slash is never oval: always a thick diagonal line** (Sean, 2026-10-15: *"They are never oval shaped - always thick diagonal lines"*; scope: general engraving; ROADMAP 2.137). **Its ends are square-cut, a head's are round** (Sean, 2026-10-27: *"The slash is octogonal and the notehead is oval. Both at a slant. The slash is a thick line without rounded edges."*; scope: general engraving; ROADMAP 2.214): slant and length do not separate them, the corners do. It crosses one stem and joins no other note (2.49, 2.71), so a box over one is never a notehead, and a slash never changes the written value.
- **A grace note never counts in the bar sum, and is significantly smaller than a regular note** (Sean, 2026-10-16: *"Grace Notes never take up math in the measure. They are significantly smaller by proportion to the regular note size. Som have a little slash through them but nit always."*; scope: general engraving; ROADMAP 2.156). **CORRECTION 2026-10-16 (Sean):** the slash being optional was his guess, not a confirmed fact (*"I am not sure the slash is optional… I was guessing. I don't know about notes after a trill. Your research would be the most reliable info we have."*) -- what a slash (or its absence) means, and where notes after a trill belong, rest on the 2.156 research (`benchmarks/omr-grace-notes-2026-10/RESEARCH.md`), each rule CONVENTION ASSUMED / NOT CONFIRMED until the sources and the print check it; no rule may yet treat a missing slash as evidence either way.
- **A dot may touch a flag but not mostly overlap it** (Sean, 2026-10-09;
  ROADMAP 2.69): overlap, not contact, makes it part of the flag. **A staccato
  is not an augmentation dot** (2026-10-07: *"they are staccato markings above
  the notes"*): a lengthening dot sits to the RIGHT of the head.
- A dot sits a space higher on a line note (the usual case); the box window is asymmetric and misses the below-line dots (`OMR_DOT_POSITION_JOIN`).
- A beam runs from the first stem it joins to the last, and a stem stands at
  the SIDE of its head -- so the outer note's centre is half a head past the
  stroke. Stems: up -> right, down -> left; right-and-down does not exist
  (96 of 96 against print, `benchmarks/omr-head-fill-2026-09/FINDINGS.md`).
- **A stem shared by a chord runs through its notes, and a second puts heads
  on BOTH sides of it** (Sean, 2026-10-26, on the 2.204 tiles: "main tip of
  stem is down but there is a note above sharing the same stem"; "stem shares
  seconds which put note heads on both sides of the stem"; "Stems that share
  notes are more complicated when it comes to which side the stem is on and if
  it goes up or down"; scope: general). So the side rule above reads only an
  isolated head: in a chord the direction is the stem's tip beyond its OUTER
  head, every head on it shares that stem, and a head of a second stands on
  the far side; a long stem through stacked heads is a chord stem, never a
  barline (2.204c: all 3 "barline" tiles were chord stems).
- **A chord's stem can run in both directions past its notes, and a short
  stem is not by itself a grace note** (Sean, 2026-10-26: "In a chord the stem
  can go in both directions"; a ~1-space stem beside a note "is either a grace
  note or could be connected to a beam with notes further and closer away to
  the beam"; scope: general). So a vertical that reaches past the touching
  heads at both ends may still be a chord stem; and a short stem means a grace
  note only with a small head, otherwise it is a full-size note whose beam
  passes close to it in a beamed group (stems shorten toward the beam).
- Every note on one stem shares one written value, and a whole note never
  has a stem (ROADMAP 2.78).
- **A note is an eighth (or shorter) ONLY on positive evidence on the page**
  -- a flag or a beam read on its stem, or a value shared from its stem
  (Sean, 2026-10-12: *"only when we see evidence of an eigth should it be
  called that"*). Bar arithmetic may never choose the shorter value for a
  stem with no flag and no beam seen; at most it settles the longer one, or
  abstains. The bar sum may CONFIRM a value the page already supports (a
  flag/beam reading, sub-threshold flag-tip ink, a refused-but-present beam
  stroke, the stem's shared value, at a measured likelihood), never SUPPLY
  one. A missed flag is recovered by reading it (ROADMAP 2.104), not by
  arithmetic.
- **The written value comes from the shape; a tuplet changes the sounding
  duration, not the written one.** A tuplet exists ONLY where its printed
  marking (the 3, with or without bracket) is SEEN; then the notes under it
  become tuplet notes, quarters or eighths alike. A tuplet is never inferred
  from the arithmetic, and a bar that would only add up under an unmarked
  tuplet gives no confirmation (Sean, 2026-10-13).
- An arc is drawn OVER its notes, a hairpin BETWEEN them. A tie's two heads
  are at one staff position (empty interval 0.168 vs 0.435 spaces,
  `benchmarks/omr-arc-grammar-2026-09/FINDINGS.md`). Of two stacked arcs
  the one NEARER the noteheads is the tie (ROADMAP 2.75). *"There is never a
  tie between 2 notes on the same beat"* (Sean, 2026-10-02; scope: general):
  a tie's heads are at different onsets.
- An articulation belongs to the note whose notehead side faces it, opposite
  the stem (ROADMAP 2.12f).
- A hairpin sits UNDER its staff, so a note between a staff and the hairpin
  beneath it belongs to that staff.
- **Words and marks between staves** (Sean, 2026-10-08/09/11; scope: general;
  ROADMAP 2.66, 2.68, 2.12m): tempo and technique words are printed ABOVE
  the staff they govern, so one in the gap belongs to the LOWER staff
  (*"It belongs to the staff below"*); expression and dynamic words keep the
  upper staff. A letter counts as a word only *"if it makes a word we know"*.
  A dynamic on a note anchors to it; between notes, to the NEXT one. Any other
  mark between two staves with nothing more specific to decide it belongs to
  the staff BELOW (2026-10-11, *"Yes, it's a convention"*).

## 2. Header: clef, key, meter

- **Only a clef stands before the key accidentals**; no rest or note is ever
  read there. **Key accidentals appear in the fixed order** of flats (Bb, Eb,
  Ab, Db, ...) or sharps (F#, C#, G#, ...), so an out-of-order or missing
  one marks where to look again (Sean, 2026-10-12; ROADMAP 2.99/2.100). A
  `flag`, `arpeggiato`, `tie` or `timeSig*` box standing in the key slots is
  a key accidental; a rest box where the printed time signature stands is a
  meter digit.
- A key change, and a meter change, is printed at one bar on every staff of
  the system (meter: Sean, 2026-09-30). **A majority of the system's staves
  showing it is enough** (Sean, 2026-10-01: *"if most of the bars confirm the time
  signature then it should run on all of the staves"*; reaffirmed "Yes",
  2026-10-27; scope: general; ROADMAP 2.47b): when more than half the staves
  read their trailing cell as signature-only, it is not a bar on any staff of
  that system.
- **Cancelling accidentals at a key change are part of the key signature**
  (scope: general): the naturals that cancel the old key, printed before the
  new key's accidentals, belong to the signature's run, not to any note
  (Sean, 2026-10-20: "Canceling accidentals should be considered key
  signature"; claimed-area step 3, ROADMAP 2.178).
- **A transposing instrument prints its own written key** (scope: general):
  its key signature has a different number of flats or sharps from the
  concert key the rest of the system prints, and its accidentals are
  transposed with it (Sean, 2026-10-22: "transposing instruments treat
  accidentals differently. So, yes they will have a different key and amount
  of flats or sharps"). So the system's key count never carries onto a
  transposing staff; its count comes from its own instrument's transposition
  (roster/dossier) or from what that staff reads (ROADMAP 2.187).
- A cautionary meter after a system's last barline governs no bar. A meter
  is printed at a movement's start and at every change, and a change HOLDS
  until a printed change back -- the return is always printed (Sean,
  2026-09-28). So where the bars overturn a carried change, a printed return
  was MISSED: label the switch and mark the bar, never switch silently. The
  carry is WEIGHED by the bars, not gated.
- Sean's middle-line convention is strong and where it looks wrong it is
  measuring the grid.
- **A page truth is not an encoding truth**: a clef prints per system and is
  declared once; MusicXML writes a slur at each end; Verovio draws one
  accidental per `<alter>`. Do not divide one by the other.
- **Two witnesses off the same raster fall silent together**: the bars are
  not an independent umpire over a bad meter reading; an arbiter correlated
  with one party sides with its family (through ink, convention, frame, or
  a shared assumption). A second witness must come from a different source
  (`source_kind: catalog`, the roster, a clef-free range check).

## 3. Geometry and ownership

- **An accidental belongs to a note of the staff it stands on** (scope:
  general; Sean, 2026-10-23: "Every accidental belongs to the same note that
  the staff belongs to"): the note to its right on that staff, never a note
  of the staff above or below. A neighbouring staff's padded crop boxing the
  same ink is a copy, not a second owner (ROADMAP 2.186, 2.201).
- **Shape from the class, role from the geometry** (Sean, 2026-09-23, scope:
  general): a detector class is a shape claim (good) plus a role guess (not);
  no gather filter keys on the role half. So all accidentals are ONE family
  and key-signature vs in-bar is decided by position (2026-10-22, *"treat all
  accidentals the same"*; ROADMAP 2.201); double sharps are real and the x is
  read (*"we definitely need the x for double sharps"*, ROADMAP 2.192); and
  colour is applied at EXPORT only (*"the color should just be applied at
  output"*, ROADMAP 2.194).
- **Boxes at a bar's left edge** with little head ink are *"almost entirely
  tie ends"* (Sean, 2026-10-17; ROADMAP 2.160): a GATHER fault, not notes.
  **A clef is sized to the staff** and clef-sized ink at the header IS the
  clef (2026-09-23).

- **The measure cell is padded 4 spaces (6 where the neighbour is far)** and
  on a conductor's page that reaches the next staff's ink; cross-staff
  ownership is a CONTEST resolved by `glyph_owner` (ladder completeness,
  then range, then distance), and a resolved contest DROPS the loser -- it
  never relocates it. Do not grow the pad.
- **The ledger lines name the owner, and they are authoritative** (Sean,
  2026-09-28): a note far from its staff has ledger lines TOWARD its own
  staff and none toward the other. Nearness is only a hint and never
  overrides them; where a ledger reading disagrees with the print, the RUNG
  FINDING is wrong, not the rule. **The head's STEM is a second, independent
  owner witness** (`OMR_STEM_OWNER`, ON, 2026-10-08, 10 of 10 tiles right):
  both agree -> the owner is decided; they disagree -> NOT decided, the head
  is written GUESSED (blue) with both staves as candidates; only one can be
  read -> use it. Sean, 2026-10-27, why a stem can point away from its own
  staff: *"multiple voices in a bar where the upper voice is above the staff
  and the lower voice is below the staff."* (*"I like that plan."* Scope:
  general; **not yet built**, ROADMAP 2.216.) **There is no such thing as a far note
  with no ledger line** (Sean, 2026-09-29: a head outside the staff touches
  the outer line, touches a ledger, or has one through it; farther than one
  notehead always has ledgers), so "no rungs found either way" is always OUR
  failure -- a missed rung, a misread head, or a note that is not far:
  abstain and count it, and a clean empty reading at a step the owner would
  need refutes that owner.
- **Measure against the staff LOCALLY** (Sean, 2026-09-30: *"scans will shift
  the geometry, and therefore anything that uses geometry compared to the
  staff needs to be measuring locally instead of globally"*): a scanned staff
  tilts and changes spacing across a system (Litolff p3: 7 px of wander, ~5%
  in spacing), and ~1 px at the head decides a near-boundary pitch. Any
  position relative to the staff reads the staff lines AT THE SUBJECT'S x
  **or its own bar's own five lines** (the per-bar find, `OMR_CELL_LINE_FIND`,
  ON: Sean, 2026-10-27, it is local enough and working; ROADMAP 2.57); a
  staff-wide or page-wide value is never local (ROADMAP 2.48, parked).
- **Ledger lines are their own read, by ink, beside the head** (Sean,
  2026-10-01: *"Most of them on these old scores were done by hand so they
  are not even necessarily even or predictable by geometry. It can only be an
  ink read for the lines."*; scope: general, measured on Litolff -- rungs at
  1.03-1.11 of staff spacing, a step wrong by the 4th rung -- while Breitkopf
  holds 1.00, `benchmarks/omr-ledger-extrapolation-2026-09/`): a head outside
  the staff is placed ONLY by counting its own printed ledgers, never by
  extending the staff spacing or any grid past the outer line
  (`OMR_FARHEAD_LEDGER`, `measure_ledger_rungs`). **The ledger lines are the
  ONLY far-head position witness** (Sean, 2026-10-27: *"I lean towards just
  focusing on ledger lines"*; scope: general): a spacing measured off the same
  raster is not a second witness (Litolff ledgers sit ~0.27 sp further out;
  on 2026-10-08 the ledger reader was right on 10 of 12 tiles, geometry on 1).
  This retires the 2026-10-01 *"combine that way"*
  (`combine_farhead_position`, `annotate/ledger_grid.py`, wired into no staged
  stage). The walk outward does not
  stop at a wide gap while the head is farther out; a ledger THROUGH a head
  (stubs on both sides) means the head is ON it; a head in the first space
  just outside the staff, touching the outer line with no ledger, is an
  on-staff note placed against the staff lines. Any new position reader
  defers to this read outside the staff (2.212 broke two heads by not).
  Sub-rulings (Sean, scope: general): ledgers exist only OUTSIDE the staff
  and only where there are notes (2026-09-24); a wide gap is a place to LOOK,
  never to assume a line you cannot see (2026-10-01/07); the line must touch
  the head's ink -- on either side is enough -- and text ink or an
  accidental's ink is never a ledger (2026-10-01/05); a visible ledger at the
  head's staff-side edge beats a "rung" hidden inside the head (2026-10-06,
  24 of 24); nothing lies above a tenuto, so a dash with a head on it or
  beyond it is a ledger (2026-10-10; ROADMAP 2.84).
- **A hollow head's position is its detector box centre, not its hole**
  (Sean, 2026-10-01, on the 2.50 sheet: *"The red is almost always right and
  better"*; scope: Litolff + Brahms): the white-interior centre was tried and
  dropped; a reader that re-centres a hollow head on its hole needs Sean's
  tiles first (2.212 did, unasked).
- **A cell index restarts per system**; key a bar on (page, system, cell).
- **A canonical cell frame cannot answer a cross-staff question**; page
  pixels are carried beside it, DECLINED rather than defaulted.
- **Litolff MERGES and Breitkopf SHATTERS**: ink components are not marks on
  either plate; 46 of 180 sampled "notehead" boxes were not noteheads
  (`benchmarks/omr-notehead-width-2026-09/FINDINGS.md`) and a third of
  Breitkopf's stemless heads are barlines. A notehead is ~1.3 staff spaces
  wide; the width floor costs 0 of 103 confirmed heads
  (`benchmarks/omr-shape-role-2026-09/FINDINGS.md`). On the Litolff plate a
  half note's hole is a thin slanted sliver, so a centre window reads mostly
  ink (ROADMAP 2.70).

## 4. Identity: which instrument is on which staff

- **The label lexicon** (`instruments.py`): aliases are GLOBAL, so a widening
  admitted for one score is admitted for every score; cross products are
  DERIVED; `Tp.` is Timpani in German and Trumpet in English and is resolved
  by the page's own other labels; a bare `Basso.` reads as a bass VOICE
  without the roster; 29 of 29 unresolved non-treble staves on the scan
  corpus print no label at all. A worn margin label is named only from the
  catalog roster + the system's gap + exactly one lexicon neighbour, never
  by widening the lexicon (ROADMAP 2.94).
- **A word printed between braced staves names every staff in the brace**
  (Sean, 2026-10-12, on Brahms `(C)` / `Hr.` / `(Es)`: *"the bracket makes
  them all horns"*): the word names the WHOLE braced group, each staff
  keeping its own crook; the extent is the BRACE, which may span more than
  two staves. The brace by itself names nothing -- it also groups
  Fag./K-Fag. and 1./2. Viol., which are different parts (ROADMAP 2.95;
  reading the brace is the named gap).
- **The condensed count cannot come from the page** (`Viola` = 1 part in one
  edition, 2 in another); it is an encoding property. **Identity loss on the
  staged path is PLACEMENT, never naming**: every part on both shared
  records is already named (the part takes its name from the first staff
  carrying one) and `OMR_HOLD_OUT_UNIDENTIFIED` gates on the SLOT. What is
  still held out is a condensed `Violoncello e Basso` staff narrowed to two
  slots, which is a convention decision (Sean, 2026-09-22: *the string
  family always includes all five; four lines means the bass doubles the
  celli or enters later*; confirmed for the five Litolff staves, ROADMAP
  2.93), not a reading gap.

## 5. Tried and rejected -- do not rebuild

Each is in `docs/DECISIONS.md` on its date. REJECTED = measured and dropped;
PARKED = kept off, not refuted; NOT LANDED = built, measured a net loss or no verdict, left OFF. Do not reopen either without new evidence and
Sean's tiles.

- REJECTED `OMR_DETECTOR_VIEWS_WHICH=close`: 0 of 3 of Sean's tiles right (2026-10-19, ROADMAP 2.172); only the small view runs.
- REJECTED `OMR_ARC_RECLASS` (the position grammar as a gate): +130 scan edits, all tie->slur, unreliable arc-end pitches (2026-10-09, 2.75).
- REJECTED 2.50 hole-centre for hollow heads: *"The red is almost always right"*, the box centre stays (2026-10-01).
- REJECTED `combine_farhead_position` (the "combine that way" far-head combine): ledger lines only, see §3 (2026-10-27).
- REJECTED 2.25b hairpin exclusion from beams: REVERTED, a real down-stem beam wrongly dropped, 2 of 2 crops (2026-10-09).
- REJECTED `OMR_DYNAMIC_INK_PICK`: the ink picked the wrong dynamic 2 of 2, so a narrowed dynamic exports blue with all candidates (2026-10-13, 2.107).
- REJECTED far-head head templates (`annotate/head_template.py`, `annotate/far_head_reader.py`): net negative or no gain beyond round 8 and breaks right heads where it misfits; stays on its branch (2026-10-02/04).
- REJECTED the 2.48 staff-line comb: five independently traced lines scored 134 right->wrong against 11 wrong->right (2026-09-30); ROADMAP 2.48 PARKED 2026-10-01.
- HELD, NOT REJECTED: `OMR_BEAMS_FROM_STROKES` (2.202) and `OMR_STEMS_FROM_STROKES` (2.204) are ink-map steps 3 and 4, OFF and waiting on the staff-line eraser path (the eraser thinned the beams 2.202 read); they are re-measured once the eraser lands -- build ON them, do not rebuild them elsewhere.
- PARKED `OMR_STACKED_HOLLOW_PAIR` (2.132, 2026-10-15), `OMR_SECOND_HOLLOW_DETECTOR` (2.114, 2026-10-14; gain small, Litolff-tuned cut-offs), `OMR_MARK_SHAPE_LINE_REMOVED` (2.133, 2026-10-15; line removal did not separate wedges from dots), `OMR_BEAM_LEVEL_NEEDS_A_JOINED_STEM` (2.153, 2026-10-16; the join reader came first), `OMR_WHOLE_REST_INK_LEAVES_BAR` (2.141 fix 3, 2026-10-15/16), `OMR_REST_WIDTH_FLOOR` (2.150, 2026-10-16), `OMR_REFUSED_HEAD_NO_DURATION` (2.143, 2026-10-16; a replay/tile aid only), `OMR_INFER_LEDGER_OWNER_HEADS` (2.136 W2, 2026-10-15; 1 of 3 on Litolff).
