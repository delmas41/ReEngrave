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
- **An augmentation dot always stands in a SPACE, never on a line** (Sean, 2026-10-14: *"Always in a space"*; scope: general engraving; ROADMAP 2.128): in its note's own space; after a note on a line, in the space **above** by default, and **below** for the lower (stems-down) voice of two on one staff or the lower note of a second in a chord (Sean, same day, *"Yes"* to the researched rule; PROVISIONAL for 19th-c. German plates -- Brahms p.0 labels: 41 above, 15 apparent "below" are the lower chord partner's above-dot, 4 are a lower voice, 0 contradictions). Registry: `docs/engraving-conventions.md`.
- **A tremolo slash is never oval: always a thick diagonal line** (Sean, 2026-10-15: *"They are never oval shaped - always thick diagonal lines"*; scope: general engraving; ROADMAP 2.137). It crosses one stem and joins no other note (2.49, 2.71), so a box over one is never a notehead, and a slash never changes the written value.
- **A grace note never counts in the bar sum, and is significantly smaller than a regular note** (Sean, 2026-10-16: *"Grace Notes never take up math in the measure. They are significantly smaller by proportion to the regular note size. Som have a little slash through them but nit always."*; scope: general engraving; ROADMAP 2.156). **CORRECTION 2026-10-16 (Sean):** the slash being optional was his guess, not a confirmed fact (*"I am not sure the slash is optional… I was guessing. I don't know about notes after a trill. Your research would be the most reliable info we have."*) -- what a slash (or its absence) means, and where notes after a trill belong, rest on the 2.156 research (`benchmarks/omr-grace-notes-2026-10/RESEARCH.md`), each rule CONVENTION ASSUMED / NOT CONFIRMED until the sources and the print check it; no rule may yet treat a missing slash as evidence either way.
- A dot sits a space higher on a line note (the usual case); the box window is asymmetric and misses the below-line dots (`OMR_DOT_POSITION_JOIN`).
- A beam runs from the first stem it joins to the last, and a stem stands at
  the SIDE of its head -- so the outer note's centre is half a head past the
  stroke. Stems: up -> right, down -> left; right-and-down does not exist
  (96 of 96 against print, `benchmarks/omr-head-fill-2026-09/FINDINGS.md`).
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
  the one NEARER the noteheads is the tie (ROADMAP 2.75).
- An articulation belongs to the note whose notehead side faces it, opposite
  the stem (ROADMAP 2.12f).
- A hairpin sits UNDER its staff, so a note between a staff and the hairpin
  beneath it belongs to that staff.

## 2. Header: clef, key, meter

- **Only a clef stands before the key accidentals**; no rest or note is ever
  read there. **Key accidentals appear in the fixed order** of flats (Bb, Eb,
  Ab, Db, ...) or sharps (F#, C#, G#, ...), so an out-of-order or missing
  one marks where to look again (Sean, 2026-10-12; ROADMAP 2.99/2.100). A
  `flag`, `arpeggiato`, `tie` or `timeSig*` box standing in the key slots is
  a key accidental; a rest box where the printed time signature stands is a
  meter digit.
- A key change, and a meter change, is printed at one bar on every staff of
  the system (meter: Sean, 2026-09-30).
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

- **The measure cell is padded 4 spaces (6 where the neighbour is far)** and
  on a conductor's page that reaches the next staff's ink; cross-staff
  ownership is a CONTEST resolved by `glyph_owner` (ladder completeness,
  then range, then distance), and a resolved contest DROPS the loser -- it
  never relocates it. Do not grow the pad.
- **The ledger lines name the owner, and they are authoritative** (Sean,
  2026-09-28): a note far from its staff has ledger lines TOWARD its own
  staff and none toward the other. Nearness is only a hint and never
  overrides them; where a ledger reading disagrees with the print, the RUNG
  FINDING is wrong, not the rule. **There is no such thing as a far note
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
  position relative to the staff reads the staff lines AT THE SUBJECT'S x,
  never a staff-wide or bar-wide value (ROADMAP 2.48).
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
