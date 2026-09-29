# Placement conventions — where each glyph family shows up relative to ITS staff

ROADMAP 2.27b. Sean, relayed 2026-09-29 (verified genuine, `docs/DECISIONS.md`
and FINDINGS §2.27's "A note on scope"): *"neighbor ink needs to have well
thought out rules of what only shows up where (above below, etc)"*. The
measure cell is padded 4–6 staff spaces and the pad reaches the neighbour
staff's ink (CLAUDE.md §10); before any more code decides which staff a mark
sitting in that gap belongs to, this is the written table of where each
glyph family is allowed to sit, sourced, so a decision can CITE a rule
instead of asserting one.

**Method, per DECISIONS 2026-09-29 ("work through the wiring conceptually,
proved by microscopic tests"): no gathers, no crop batches, no pricing
runs.** Everything below is read from `tools/omr/training/deepscoresv2_
208_classes.json` (the 208-class vocabulary), `tools/omr/class_aliases.py`
(which names are twins), `docs/engraving-conventions.md` (the 114-entry
registry — cited as `[Cn]`/`[Ln]` exactly as it spells its own ids),
`docs/DECISIONS.md`, `CLAUDE.md` §10, and `tools/omr/staged/adjudicators/
ownership.py` / `text.py` (what is already wired). Six WebSearch look-ups
filled the families the registry does not cover (grace notes, pedal marks,
arpeggiato, cross-staff beaming, rehearsal marks) — those are marked
**ESTABLISHED PRACTICE (secondary source)** below and are weaker citations
than the registry's own Dorico/SMuFL/Gould-attributed entries; none of them
were verified against the primary text.

**Status key**
- **SEAN-CONFIRMED** — Sean said it, cited to `CLAUDE.md` §10 or a
  `DECISIONS.md` line, in his words where quoted.
- **ESTABLISHED PRACTICE** — a source in `docs/engraving-conventions.md`
  (Gould, Dorico/Steinberg, Ross-adjacent SMuFL/Bravura, Read/IU, MOLA), or a
  fresh citation below marked "(secondary source)" where the primary text
  was not read.
- **ASSUMED** — no source; this lane's own inference from the shape of the
  problem. Every ASSUMED row that matters to the gap question is repeated in
  "Questions for Sean" at the end.

---

## The table

One row per glyph family the detector produces, grouped as CLAUDE.md's brief
requested. "Registry ref" is the existing `docs/engraving-conventions.md`
entry that already states the rule, or **GAP** if none of the 114 entries
covers it (not a license to add one — `conventions.py`'s registry is a
parsed document with its own arithmetic; adding an entry is out of this
lane's scope, named in "Rules safe to wire").

### Noteheads
`noteheadBlack/Half/Whole/DoubleWhole{OnLine,InSpace}{,Small}`

- **Relative to its staff:** INSIDE — pitch is the staff line/space it sits
  on; there is no "above/below the staff" case except via ledger lines.
- **Distance:** 0 (it defines the position).
- **Attaches to:** nothing; everything else attaches to IT.
- **Gap signal:** the CONTESTED case itself — a notehead detected in the pad
  is the subject every other row's rule is trying to place. Decided by
  `glyph_owner`'s own ladder/hairpin/range terms (see Ledger lines and
  Hairpins below), never by nearest-staff distance alone.
- **Known exceptions:** a note on the FIRST ledger line and one 4.5 spaces
  out are geometrically identical to "in the pad" until the ladder is read
  (`[C5]`, measured: Brahms's C Horn 2 sits 4.5 spaces below a treble staff,
  four pixels past its own cell, and pad-5 sent it to the wrong horn "by 19
  px" — "distance is nearly a coin flip").
- **Status:** SEAN-CONFIRMED (the ownership rule, not the notehead itself) —
  DECISIONS 2026-09-28: *"the ledger lines are authoritative … nearness is
  only a hint and never overrides them"*.
- **Registry ref:** `[C4]` (ladder completeness), `[C5]` (why the pad
  exists and why distance is a coin flip).

### Rests
`restDoubleWhole/Whole/Half/Quarter/8th/16th/32nd/64th/128th/HNr/HBar`

- **Relative to its staff:** INSIDE — centred on or about the middle line;
  a whole rest hangs under the 4th line.
- **Distance:** 0.
- **Attaches to:** nothing (it is itself the note's stand-in); a lone whole
  rest can absorb a whole bar regardless of meter.
- **Gap signal:** same contest as a notehead — a rest detected in the pad is
  owned by the SAME rule (`glyph_owner` does not distinguish rest from
  notehead category for the contest). A whole-rest carrier is also the
  majority case for fermatas (see Fermatas).
- **Known exceptions:** in multi-voice bars a rest can be DISPLACED off the
  centre line to avoid a collision with the other voice's notes — this
  project has not measured or modelled displaced-rest position at all
  (ASSUMED gap; see Questions for Sean).
- **Status:** SEAN-CONFIRMED (whole-bar rule) — CLAUDE.md §10: *"A whole
  rest means the BAR whatever the meter."* Displacement: ASSUMED.
- **Registry ref:** `[L28]` (whole-bar rest centred), `[C84]`-adjacent
  entries in "Rests & bar filling"; displaced rests — **GAP**.

### Accidentals & key-signature markers
`accidentalFlat/Natural/Sharp/DoubleSharp/DoubleFlat{,Small}`,
`keyFlat/Natural/Sharp`

- **Relative to its staff:** INSIDE — at the SAME staff position as the
  note it modifies, printed BEFORE it in x.
- **Distance:** ~0 in y (same position as its note); a small negative dx.
- **Attaches to:** its note (in-bar) or the clef (key-signature marker, at
  fixed slots keyed on the clef).
- **Gap signal:** inherits its note's ownership — `accidental_owner`
  already reads `Q.GLYPH_OWNER` (pre-existing, per §2.27's map). A
  key-signature marker is NEVER an in-bar accidental candidate (the header
  exclusion, `is_a_key_signature_marker`, merged 2.7b).
- **Known exceptions:** a courtesy accidental changes nothing musically and
  its FREQUENCY is a property of the edition, not a rule; timpani/horns/
  trumpets are conventionally written with NO key signature at all.
- **Status:** ESTABLISHED PRACTICE + MEASURED HERE.
- **Registry ref:** `[C24]` (key change printed on every staff), the
  "Accidentals & key signatures" section generally; header exclusion is
  merged code (2.7b), not a registry entry.

### Augmentation dots
`augmentationDot`

- **Relative to its staff:** INSIDE, at the note's OWN space — half a
  space ABOVE for a note ON a line, and NEVER below.
- **Distance:** 0.00 spaces (note in a space) or +0.50 (note on a line);
  shipped window `DOT_ABOVE_NOTE_MAX_SPACES = 0.75`,
  `DOT_BELOW_NOTE_MAX_SPACES = 0.25`.
- **Attaches to:** its own notehead or rest, never the neighbour's.
- **Gap signal:** the dot's OWN position never reaches into the pad (it is
  within 0.75 sp of its note); what CAN reach the pad is the question of
  WHICH staff's note it is dotting when that note itself is contested —
  and `dot_role`'s search over `Q.GLYPH_BOX` in its own cell is the
  IDENTICAL shape to the bug 2.27 just fixed for articulations/fermatas/
  ornaments (picks a candidate note with no regard for a DECIDED
  `Q.GLYPH_OWNER` verdict already handing that candidate to the neighbour).
  **Named in ROADMAP 2.27 as a follow-up, not built** ("its own ORDER
  comment calls 'needs no verdict of any kind' load-bearing").
- **Known exceptions:** exactly one of 691 measured `aug_dot` rows across
  two publishers attaches to a rest, and it is FALSE (a clean undotted
  whole rest); double stops force an asymmetric window (two heads a space
  apart, each with its own dot — a symmetric window ties and double-dots
  the wrong one).
- **Status:** SEAN-CONFIRMED-adjacent (MEASURED HERE + the literature
  agree to the half-space) for the dot's own offset; the cross-staff
  candidate-filtering gap is this lane's own read of the tree, matching
  2.27's fix exactly — **ASSUMED that the same fix applies cleanly here.**
- **Registry ref:** `[C50 + L31]`.

### Articulations
`articAccent/Staccato/Tenuto/StaccatissimoAbove/Below`,
`articMarcatoAbove/Below` (twin of coarse `articulationMarcatoAbove/Below`)

- **Relative to its staff:** on the NOTEHEAD side, OPPOSITE the stem
  direction named by the class (`…Above` = stem down, `…Below` = stem up,
  as a rule of thumb — the class states the side directly).
- **Distance:** x offset ≈ 0 (centred on the head); y join window
  0.50–2.50 notehead widths (plateau), shipped
  `_ARTIC_MAX_DX_NOTEHEAD_WIDTHS = 0.75`.
- **Attaches to:** the notehead on the correct side; a mark with no
  notehead on the correct side is left UNATTACHED, never given to the
  nearest thing available.
- **Gap signal:** already wired (2.27): a candidate whose own
  `Q.GLYPH_OWNER` verdict is DECIDED for another staff is dropped from
  `articulation_owner`'s pool before the side/distance test runs at all
  (reason `owned_by_another_staff`). Side itself is not a cross-staff
  signal (it says which side of ITS OWN note, not which staff).
- **Known exceptions:** MARCATO is always ABOVE regardless of stem
  direction; multi-voice bars place articulations at the STEM end (so the
  reader can tell voices apart), not the head end; stem-side staccato/
  staccatissimo centre on the STEM, breaking the zero-x-offset join; a
  small mark near the middle line is quantised into the next free SPACE
  rather than sitting at a fixed y; "side derived from the class name fails
  together with the classification" (an independent ruler exists,
  `positions.py:473`, and is read by nothing).
- **Status:** MEASURED HERE (the join window) + ESTABLISHED PRACTICE
  (Dorico, IU).
- **Registry ref:** `[C51 + L58 + L61]`, `[L59]`, `[L60]`.

### Fermatas
`fermataAbove/Below`

- **Relative to its staff:** ABOVE by default; BELOW only for a lower
  voice or a shared staff (inverted).
- **Distance:** no measured figure; glyph itself is 2.408 × 1.328 staff
  spaces (wide and low).
- **Attaches to:** whatever sounds beneath it — a notehead OR a whole-bar
  rest. 26 of 51 measured fermata carriers on Litolff pp.1–3 are RESTS,
  the majority case — an articulation-style "nearest notehead" router
  structurally cannot reach more than half this population.
- **Gap signal:** already wired (2.27), same `owned_by_another_staff` gate
  as articulations. The ABOVE band it searches is the same page-pixel band
  the staff ABOVE's dynamics occupy on a conductor's page — a real
  contest for the SAME ink that is not yet arbitrated (see Dynamics
  letters).
- **Known exceptions:** below-staff placement when the music above is
  congested; a shared staff's lower voice.
- **Status:** MEASURED HERE (carrier population) + ESTABLISHED PRACTICE
  `UNSOURCED — believed true, not verified` for "above by default"
  (registry's own caveat — no source consulted states it directly, only
  the SMuFL paired-glyph geometry implies it).
- **Registry ref:** `[C52 + L62]`.

### Ornaments — trill, turn, mordent
`ornamentTrill/Turn/TurnInverted/Mordent`

- **Relative to its staff:** ABOVE its note, always — the side is FIXED by
  convention (unlike an articulation, whose class states the side).
- **Distance:** dx ≤ 1.0 notehead width, `_ORNAMENT_MAX_DX_NOTEHEAD_WIDTHS
  = 1.0` — declared UNMEASURED/unswept in the code itself.
- **Attaches to:** the nearest notehead in x, on the above side only.
- **Gap signal:** already wired (2.27), same gate as articulations/
  fermatas.
- **Known exceptions:** a tremolo is the exception in the SAME class family
  (rides the stem, no side at all — see below).
- **Status:** ASSERTED (untested here) for the side convention; only its
  REACH (4 of 8 detections find a notehead) was measured.
- **Registry ref:** `[C87]`.

### Dynamics letters
`dynamicP/M/F/S/Z/R` (twins: coarse `dynamicLetterP/M/F/S/Z/R`)

- **Relative to its staff:** in the BAND below the bottom line — or ABOVE
  a VOCAL staff (the default flips by staff KIND, not by anything on the
  page itself).
- **Distance:** own band `BAND_TOP_SPACES = 0.3` to `BAND_BOTTOM_SPACES =
  6.0` below the staff's bottom line; measured cross-staff population:
  73% stand in their OWN staff's band, 24% in the band of the staff
  immediately ABOVE — "**distance exactly 1, no exceptions**" — with a
  2.5-space EMPTY gap between the two populations.
- **Attaches to:** the staff whose band it stands in (not the cell it was
  detected in — cell padding is exactly what steals a dynamic into the
  wrong measure's crop).
- **Gap signal:** **DECISIVE and UNWIRED.** The belonging rule "has NO
  consumer" per the registry's own note: `Q.DYNAMIC_BAND_POSITION` exists
  (`tools/omr/staged/positions.py`, behind `OMR_FAMILY_POSITIONS`, default
  OFF) and `adjudicate_dynamic` does not read it — the band constants are
  consumed only by the hairpin reader today. **See "Rules safe to wire."**
- **Known exceptions:** grand-staff instruments (piano/harp) — see next
  row; a staff carrying two players may print one part's dynamics above
  and the other's below; on a SCAN the dominant error is a mark never
  found at all, not one on the wrong staff.
- **Status:** MEASURED HERE (the 73/24 split, "no exceptions" on the
  corpus measured) + ESTABLISHED PRACTICE (Dorico/Steinberg; Gould cited
  by those sources, not read directly on this point).
- **Registry ref:** `[C46 + L53]`.

### Hairpins
`dynamicCrescendoHairpin/DiminuendoHairpin`

- **Relative to its staff:** BELOW its staff, in the dynamics band — SPAN-
  anchored (between two or more note onsets), never note-anchored.
- **Distance:** same band as dynamics letters; the mark is also
  structurally distinct — "connected to NOTHING" (a beam joins stems, a
  slur meets noteheads, a barline meets staff lines; a hairpin touches no
  other ink), and it is the THINNEST stroke in the family
  (`hairpinThickness 0.16` vs `stemThickness 0.12` / `staffLineThickness
  0.13`).
- **Attaches to:** the note columns it spans, by nearest-note pointers at
  each end — NOT by box overlap (0 of 4 truth hairpins overlap a
  notehead box on the Mahler 5 fixture).
- **Gap signal:** **DECISIVE, ALREADY WIRED (2.6c, merged).** A hairpin
  always sits UNDER its staff, so a note between a staff and the hairpin
  beneath it belongs to THAT staff — `hairpin_separates` is one of
  `glyph_owner`'s terms, decisive over `range_veto`. Cited as precedent
  for how a decisive, sourced convention gets wired.
- **Known exceptions:** the band is CROWDED (slur/tie arcs, `pizz.`,
  `espr.`, `arco` text all share it) — "the band bounds the search; it
  does not identify the mark". An accent can look like a one-beat hairpin;
  the discriminator is note-anchor vs span-anchor, width alone fails.
- **Status:** SEAN-CONFIRMED — DECISIONS 2026-09-28: *"if the note is
  above the hairpin … it belongs to the staff that's between the hairpin
  and that staff."*
- **Registry ref:** `[C45 + L55]`, `[C78 + L56]`, `[C48]`, `[C49]`.

### Slurs
`slur`

- **Relative to its staff:** OVER its notes — the arc overlaps the
  noteheads VERTICALLY (opposite of a hairpin, which is BETWEEN them
  horizontally; the two are not contradictory — one claim is about the
  vertical axis, one about the horizontal).
- **Distance:** ink stops INSIDE both outer notehead centres, padded
  `_SLUR_ARC_PAD_NOTEHEADS = 0.25` notehead widths so the outer note is not
  dropped; for stemmed notes the arc is anchored stem-TOP to stem-TOP
  (median 0.52 notehead widths from the arc's edge to the nearest head
  centre outside it).
- **Attaches to:** notehead centres (unstemmed) or stem tips (stemmed); a
  slur crossing a system break re-anchors on the FIRST NOTE of the
  resuming staff instead.
- **Gap signal:** a slur is a WITHIN-staff mark by construction (it binds
  notes of ONE voice, `[L52]`) — it is not itself a cross-staff ownership
  vote, but ITS OWN endpoints inherit whichever staff its flanking
  noteheads were assigned to, so a wrong notehead-ownership call silently
  relocates the slur too. `arc_owner` already reads `Q.GLYPH_OWNER`
  (pre-existing per §2.27's map).
- **Known exceptions:** a piano/harp cross-staff slur is a real, separate
  case (`[L52]`'s exception); where the outer notes have opposite stems the
  endpoint moves toward the heads (a further, unmeasured mode in the pad
  distribution `[C36]` refused to tune on); one printed arc cut by a
  barline is still ONE arc (`[C38]`).
- **Status:** MEASURED HERE.
- **Registry ref:** `[C35 + L48]`, `[C36 + L51]`, `[C37]`, `[C38 + L50]`,
  `[L49]`, `[L52]`.

### Ties
`tie`

- **Relative to its staff:** shallow and close to its two heads (as
  against a slur's clear arc); drawn on the side OPPOSITE the stems.
- **Distance:** both flanking heads at ONE staff position — measured
  empty interval 0.168–0.435 staff spaces on eleven ENGRAVED fixtures.
  ⚠️ **NOT an empty interval on a scan** (same-pitch max 0.238 vs
  step-apart min 0.013) — the convention is true of the ink, the READING
  of positions is what fails.
- **Attaches to:** two statements of the SAME pitch — "the same-pitch
  requirement is absolute; it is what a tie MEANS."
- **Gap signal:** same as a slur — inherits its flanking noteheads' staff
  assignment; not an independent vote. Multi-voice bars suspend the
  opposite-stem side convention.
- **Known exceptions:** an accidental carries across a barline through a
  tie (comparing SPELLED pitch instead of STEP broke this — +21 engraved
  edits); the tie/slur "position grammar" (arc spans >2 notes ⇒ slur;
  different flanking pitches ⇒ slur) is MEASURED and REFUSED as a shipped
  veto on scans (+130 edits) though the underlying convention is sound.
- **Status:** MEASURED HERE + ESTABLISHED PRACTICE (Wikipedia states the
  same-pitch rule as absolute).
- **Registry ref:** `[C39 + L47]`, `[C40]`, `[C43]`.

### Beams
`beam`

- **Relative to its staff:** connects STEM TIPS within its own staff/voice
  — never isolated; "a beam is always connected to something."
- **Distance:** angled by the outer interval, horizontal in three named
  cases; runs from the FIRST stem it joins to the LAST (so the outer
  note's centre sits half a head past the stroke).
- **Attaches to:** the stems of the notes it groups; a stroke that touches
  the NEIGHBOUR staff's stems is the neighbour's beam, not this staff's
  (2.25b, merged).
- **Gap signal:** already wired (2.25/2.25b): a stroke touching the
  neighbour staff's stems, or lying inside a DECIDED slur/tie arc, is
  discounted; if discounting leaves a stemmed head bare, duration NARROWS
  rather than guessing.
- **Known exceptions:** **cross-staff beaming in keyboard music** — a note
  drawn on staff B for spacing reasons still LOGICALLY belongs to whichever
  staff was chosen as the beam's "home" voice; the visual staff and the
  logical staff can disagree. Orchestral strings/winds/brass essentially
  never do this; it is a piano/harp case. **WIRED 2026-09-29 (ROADMAP
  2.27d):** `_not_the_neighbours_beam` (`adjudicators/rhythm.py`) now
  tracks WHICH neighbour staff each touched stem belongs to and keeps a
  stroke where every staff it touches is a DECIDED brace partner
  (`structure.grand_staff_partner_staff`) — the "home voice" question
  itself (which of the pair's two staves the beam logically belongs to,
  where that differs from where the notes are drawn) remains unread; only
  the "is this really the neighbour's beam" discount is gated.
- **Status:** MEASURED HERE (the shipped rule) + ESTABLISHED PRACTICE
  (secondary source — Finale/LilyPond/MuseScore/Soundslice documentation,
  not Gould's primary text) for the cross-staff exception.
- **Registry ref:** `[C11]`, `[C12]`; cross-staff beaming — **GAP** (the
  discount is wired; the registry entry itself is still not written).

### Stems
`stem`

- **Relative to its staff:** attaches at the RIGHT going up, LEFT going
  down — "right-and-down does not exist" (96 of 96 against print).
- **Distance:** meets the head ~0.168 staff spaces off the pitch centre
  vertically; length ≥ 2.5 spaces, ~1 octave by default.
- **Attaches to:** its own notehead.
- **Gap signal:** not itself a cross-staff vote; supports the beam/arc
  reach rules above (a stem tip is where a beam or slur anchors).
- **Known exceptions:** two voices on one staff — upper voice up, lower
  voice down, REGARDLESS of position (a cheap divisi detector: up- and
  down-stemmed notes in one bar that the middle-line rule alone cannot
  explain is a two-voice bar).
- **Status:** SEAN-CONFIRMED — CLAUDE.md §10: *"Stems: up → right, down →
  left; right-and-down does not exist (96 of 96 against print)."*
- **Registry ref:** `[C9 + L10]`, `[L17]` (divisi via stem direction).

### Flags
`flag8th/16th/32nd/64th/128thUp/Down{,Small}`

- **Relative to its staff:** rides the STEM — no independent staff
  position; the class name states BOTH the duration and the stem's own
  direction.
- **Distance:** n/a (attached to the stem end).
- **Attaches to:** the stem, always.
- **Gap signal:** none directly — a flag inherits its stem's (and hence
  its note's) staff assignment; never itself contested.
- **Known exceptions:** none recorded.
- **Status:** ASSUMED (no dedicated registry entry, but the mechanism
  follows directly from the stem entry).
- **Registry ref:** **GAP** (adjacent to `[C9 + L10]`).

### Tremolo strokes
`tremolo1/2/3/4/5`

- **Relative to its staff:** rides the STEM — "unlike every other
  ornament, a tremolo is drawn ON the stem rather than above or below the
  note", so it has NO side at all.
- **Distance:** n/a.
- **Attaches to:** the stem.
- **Gap signal:** none — inherits the stem's/note's staff; moot in
  practice today (detector reach is ZERO of 34,115 detections against an
  eleven-work truth of twelve `<tremolo>`).
- **Known exceptions:** none recorded; LilyPond deliberately receives no
  tremolo count mapping at all (it would write a rhythm SUBDIVISION, not a
  mark).
- **Status:** ASSERTED (untested here).
- **Registry ref:** `[C55]`.

### Ledger lines
`ledgerLine` (twin: `legerLine`)

- **Relative to its staff:** OUTSIDE only — a box whose centre lies
  between line 1 and line 5 is NOT a ledger line, whatever its distance to
  a line.
- **Distance:** whole-number-of-spaces steps beyond the nearest staff
  line; exists only where a NOTE is on it or beyond it (vertical tolerance
  2.75 spaces to the nearest detected head).
- **Attaches to:** the note it extends the staff for; a rung with no head
  on or near it, or inside the five-line band, is not a rung at all.
- **Gap signal:** **THE decisive rule, ALREADY WIRED (2.6c/2.6d/2.6f,
  merged).** An unbroken ladder from staff A to a far note means the note
  is staff A's; a ladder with a rung missing abstains (`far_no_rungs`)
  rather than guessing; a rung that is really a DIFFERENT candidate's own
  ledger structure (an integer number of spaces beyond that candidate's
  own line) is excluded before it can count toward a farther staff
  (`[C90]`/`[C91]`'s "shared structure" fix, §2.6f).
- **Known exceptions:** a rung drawn through a hollow notehead is split by
  the head's white counter (bridged up to 0.9 spaces, `[C6]`); on a bowed
  scanned staff a first rung can register a whole space off; a ledger box
  can be a staff-line fragment, a tenuto, a barline slice, or a stem.
- **Status:** SEAN-CONFIRMED — DECISIONS 2026-09-24/28: *"the ledger lines
  will only be on the outside of the staff and only happen if there are
  actual notes"*; *"nearer to the staff is not always going to be right
  but ledger lines will be."*
- **Registry ref:** `[C4]`, `[C90]`, `[C91]`, `[C5]`, `[C6]`.

### Clefs
`clefG`, `clefCAlto/Tenor`, `clefF`, `clefUnpitchedPercussion`, `clef8/15`

- **Relative to its staff:** at the header of EVERY system, sized
  consistently with the staff and standing at the system's first-measure
  edge.
- **Distance:** clef-sized ink (~4.5 staff spaces) at the header; a
  notehead-sized box on top of it is the misread, not the clef.
- **Attaches to:** the staff/system it heads; an instrument's header clef
  is a property of the INSTRUMENT, not the page.
- **Gap signal:** not a cross-staff ownership case — clefs never contest
  between two staves (each staff has its own). Relevant only as a header
  fact that later disambiguates which family a header-region box belongs
  to (key markers vs clef vs notehead-on-clef-ink).
- **Known exceptions:** a clef unreadable on one system can take the same
  part's clef from OTHER systems, gaps only, in INFER, labelled; a generic
  C clef resolves to alto by convention but the line is measured from the
  staff geometrically, never guessed from the class name alone.
- **Status:** SEAN-CONFIRMED — DECISIONS 2026-09-23: *"the size of clefs
  are consistent to the staff and the edge of the first measure … that
  should be helpful geometrically."*
- **Registry ref:** `[C88]`.

### Key signatures & time signatures
`keyFlat/Natural/Sharp` (see Accidentals above); `timeSig0-9`,
`timeSigCommon/CutCommon`

- **Relative to its staff:** INSIDE the staff, between the clef and the
  meter (key), or filling the staff's HEIGHT (~2 staff spaces tall, meter)
  — both printed on EVERY staff of the system, always.
- **Distance:** fixed slots keyed on the clef (key); rigid x-placement,
  numerals fill the staff height (meter).
- **Attaches to:** the system (every staff shares the identical key/meter
  at a given bar), not to an individual note.
- **Gap signal:** DECISIVE but not a "which staff owns this ink" question —
  it is a "does this staff's OWN reading agree with the rest of its
  system" check: a lone staff disagreeing with every other DECIDED staff
  of its system is superseded to ABSTAINED and carried (already the shape
  of the 2026-09-23 key-signature decision). A meter digit found ~1 space
  tall in a cell is a fingering/tuplet/measure number, NOT a time
  signature — position/size separates the four roles of one printed digit.
- **Known exceptions:** a cautionary meter printed after a system's FINAL
  barline governs no bar; a meter holds until a PRINTED return (the return
  is always printed — where the bars overturn a carried change, the switch
  must be labelled, never silently switched); timpani/horns/trumpets
  conventionally carry no key signature.
- **Status:** SEAN-CONFIRMED — DECISIONS 2026-09-23/28.
- **Registry ref:** `[C24]`, `[C29]`, `[C53]` (digit-role discriminator).

### Tuplet numerals & brackets
`tuplet1-9`, `tupletBracket` (twin: `tupleBracket`)

- **Relative to its staff:** OUTSIDE the staff, OVER its own beam group —
  the digit centred on the group's SPAN, the bracket enclosing it.
- **Distance:** the digit's centre must fall inside the group's beam-box
  span (padded a notehead width so the first stem's note is not dropped);
  the group must fall inside the bracket's span (detected brackets run far
  wider than the group they cover — one measured at 1846px over a 478px
  group).
- **Attaches to:** its own beam group, which is itself a within-staff
  object; not a cross-staff case in the corpus measured.
- **Gap signal:** none directly for the digit/bracket ITSELF — but a
  stray tuplet-shaped mark reaching into the pad is resolved by which
  beam/group it centres over, the SAME question the beam-ownership rule
  (above) already answers.
- **Known exceptions:** the coarse `numeral` class covers meter digits,
  tuplet digits, fingerings AND measure numbers under one name — a
  `numeral4` is never safely renamed `timeSig4` (a real incident cost 390
  bar-check failures shipping a 2/4 page as common time); a group is a set
  of NOTES, not a beam STROKE (a sixteenth carries two strokes and the
  ratio must be applied once per note-set, not once per stroke).
- **Status:** MEASURED HERE.
- **Registry ref:** `[C53]`, `[C54]`.

### Grace notes
`graceNoteAcciaccatura/AppoggiaturaStemUp/Down`

- **Relative to its staff:** INSIDE, at the note's own staff position, at
  a reduced size (typically ~3/5 of a normal notehead — smaller than the
  ordinary "one staff space tall" notehead rule `[C1 + L3]` states, which
  is why a grace notehead is a NAMED exception to that entry rather than a
  misread: "grace noteheads are smaller (41×38 px against 51–83 in the
  same cell)").
- **Distance:** printed immediately before the main notehead it
  ornaments, on the same side conventions as an ordinary note (stem
  right-up/left-down still apply).
- **Attaches to:** the FOLLOWING main note it ornaments (Dorico/Steinberg
  help: grace notes attach to the notated rhythmic position of the note
  they precede).
- **Gap signal:** **ASSUMED, and the same shape as the dot/articulation
  gap** — a grace note's own staff assignment should inherit whichever
  staff its target main note was decided onto, not a fresh nearest-staff
  guess; this is unbuilt and unverified against a real record.
- **Known exceptions:** a grace note on ledger lines needs enough stem
  length that the diagonal acciaccatura stroke does not obscure a ledger
  line (Gould, per secondary attribution — chapter title only, primary
  text not read).
- **Status:** ESTABLISHED PRACTICE (secondary source — Dorico/Steinberg
  help, Gould cited but not read directly) for attachment; ASSUMED for the
  cross-staff inheritance.
- **Registry ref:** `[C1 + L3]` (size exception only); placement/gap
  ownership — **GAP.**

### Arpeggiato
`arpeggiato` (twin: `arpeggio`)

- **Relative to its staff:** a vertical wavy line immediately LEFT of the
  chord it decorates, spanning that chord's OWN noteheads.
- **Distance:** ~0 in x-adjacency to the chord's left edge; vertical span
  equal to the chord's own notehead range.
- **Attaches to:** a chord on ONE staff, ordinarily; a piano/harp chord
  spanning both hands of a grand staff can carry ONE arpeggiato sign
  spanning BOTH staves (secondary sources; not confirmed against Gould's
  primary text).
- **Gap signal:** ASSUMED same as a notehead's own ownership contest for
  the single-staff case; the grand-staff cross-staff case is a named
  exception this project's orchestral acceptance corpus (no piano/harp
  movement) does not exercise.
- **Known exceptions:** `[C78 + L56]` already notes `arpeggiato` fires 377
  times on the SAME document as "a stem or a barline" — a tall thin box is
  not thereby an arpeggio sign; the class is confusable at the detector
  level before placement is even asked.
- **Status:** ESTABLISHED PRACTICE (secondary source) for the sign itself;
  ASSUMED for ownership.
- **Registry ref:** **GAP** for placement; `[C78 + L56]`'s known-exception
  note is the only registry mention.

### Pedal marks
`keyboardPedalPed/Up`

- **Relative to its staff:** BELOW the entire grand staff (both hands),
  never between the two staves and never attributed to the nearer one by
  distance.
- **Distance:** below the bottom staff of a braced piano/harp pair, in a
  band analogous to (but distinct from) the dynamics band.
- **Attaches to:** the grand-staff PAIR as a unit, not to either hand's
  staff individually.
- **Gap signal:** DECISIVE if the corpus ever contains a grand staff: a
  nearest-staff rule is STRUCTURALLY WRONG here, the same shape as the
  grand-staff dynamics exception below. Not exercised by this project's
  current acceptance set (Beethoven 5 / Brahms 1 / Litolff / Breitkopf are
  all non-keyboard).
- **Known exceptions:** none recorded beyond the "always below, never
  between" placement itself.
- **Status:** ESTABLISHED PRACTICE (secondary source — MuseScore/Dorico
  forum documentation, not Gould's primary text). **WIRED (ownership half)
  2026-09-29, Sean's "build anyway" (ROADMAP 2.27d):** new decision `Q.
  PEDAL_OWNER` (`adjudicators/ownership.py`) files the LOWER staff of a
  DECIDED brace pair regardless of which cell detected the mark, abstains
  `no_brace` off one. `<pedal>` MusicXML emission is NOT built — no
  renderer for it exists anywhere in this repo; named as an export gap
  (`export._grand_staff_family_gap`).
- **Registry ref:** **GAP.**

### Dynamics on a grand staff (cross-cutting exception, not its own class)

- **Relative to its staff:** for piano/harp, a dynamic governing BOTH
  hands sits BETWEEN the two staves — belonging to NEITHER nearer staff,
  but to BOTH.
- **Gap signal:** a named STRUCTURAL exception to the dynamics-letter rule
  above: "a nearest-staff attribution rule is structurally wrong there and
  will assign a shared mark to one hand." Not exercised by this project's
  current acceptance set (see Pedal marks).
- **Status:** ESTABLISHED PRACTICE (Dorico/Steinberg help; strong
  convention, not measured here). **WIRED 2026-09-29 (ROADMAP 2.27d, "Rules
  safe to wire" item B, below):** `adjudicate_dynamic`'s own `_canonical_
  grand_staff_owner` (`adjudicators/text.py`) files a CONTESTED letter
  (ink both staves' padded cells caught) onto the pair's upper staff once,
  on a DECIDED brace only; an uncontested letter is never moved.
- **Registry ref:** `[L54]`.

### Direction words, tempo/expression text, rehearsal marks
(text layer; no dedicated detector class — read via OCR/Surya, not YOLO)

- **Relative to its staff:** direction words (`pizz.`, `espr.`, `dim.`,
  etc.) print INSIDE the system, in the band of the staff they modify.
  Tempo marks and rehearsal letters are SYSTEM-level: printed TWICE per
  system, above the TOP staff AND above the FIRST VIOLINS — never
  attributed to one staff by nearest-band distance.
- **Distance:** tempo/rehearsal marks stand clear ABOVE the system, at
  the top-left for measure numbers/rehearsal letters specifically —
  outside every staff's own band.
- **Attaches to:** the SYSTEM as a whole, duplicated, not a single part.
- **Gap signal:** ASSUMED gap — the direction-text reader currently clamps
  every candidate band to a staff's own `x_start..x_end` and measured ALL
  98 candidates on this project's two documents as `placement: below`,
  with the `above` band UNEXERCISED — a tempo mark printed clear above a
  system is exactly the shape this would misattribute (to the nearest
  staff below it) rather than recognise as system-level and duplicate.
  Neither the duplication nor the misattribution risk has been priced.
- **Known exceptions:** older plates are less consistent about the
  duplication than modern ones; rehearsal marks are boxed/circled
  specifically so they are not confused with bar numbers.
- **Status:** ESTABLISHED PRACTICE (MOLA, IU) for tempo/rehearsal
  placement; ESTABLISHED PRACTICE (secondary source, this lane's search)
  for the rehearsal-mark box convention specifically.
- **Registry ref:** `[L69]` (tempo), `[C75 + L68]` (measure numbers,
  mentions rehearsal marks in passing); a dedicated rehearsal-mark entry —
  **GAP.**

### Bowing marks
`stringsDownBow/UpBow`

- **Relative to its staff:** note-anchored, presumably on the notehead
  side like an articulation (this lane found no registry entry or
  external source stating the side explicitly).
- **Distance:** ASSUMED same order as an articulation's join window
  (untested).
- **Attaches to:** ASSUMED its own notehead.
- **Gap signal:** ASSUMED to inherit its note's staff assignment, same as
  an articulation — not verified.
- **Known exceptions:** none found.
- **Status:** ASSUMED — no source consulted, registry or web, states this
  family's placement directly.
- **Registry ref:** **GAP.**

### Fingerings
`fingering0-9`

- **Relative to its staff:** beside its own notehead (distinguished from a
  tuplet digit or time-signature digit, which are the SAME raw shape at a
  different position — `[C53]`'s digit-role discriminator).
- **Distance:** close beside the note, not over a group span.
- **Attaches to:** its own notehead.
- **Gap signal:** ASSUMED to inherit its note's staff assignment; not
  itself a cross-staff case in the measurements available (33 of 33
  measured `fingering3` sit in a cell holding a real triplet, i.e. the
  measurement is about digit ROLE, not about which staff a fingering
  belongs to).
- **Known exceptions:** none recorded for placement specifically.
- **Status:** MEASURED HERE (role discriminator) / ASSUMED (ownership).
- **Registry ref:** `[C53]`.

### Brace, bracket, ottava bracket
`brace`, `ottavaBracket`

- **Relative to its staff:** a BRACE means exactly ONE PLAYER (the
  grand-staff/two-staff-one-player signal the pedal and grand-staff-
  dynamics rows above both depend on to even fire); a bracket encloses a
  FAMILY of staves, not the system; an ottava bracket sits above (8va) or
  below (8vb) the staff whose octave it shifts.
- **Distance:** the only ink crossing a family gap besides the systemic
  barline is ~0.16 staff spaces wide (structural, not this row's own
  figure).
- **Attaches to:** brace/bracket attach to a STAVES-SPAN, not a single
  staff; the ottava bracket attaches to the staff whose notes it shifts.
- **Gap signal:** the brace is the detection that SHOULD gate the
  grand-staff exceptions above (pedal, between-staff dynamics) — currently
  "all three incumbent sites decide brace-vs-bracket by `len(staves) ==
  2`", which is unreliable (an organ-with-pedal is three staves; a wind
  pair is also two staves and is NOT a grand staff). The ottava bracket's
  own above/below convention is unconfirmed against any source.
- **Known exceptions:** organ-with-pedal is three staves; celesta and
  accordion are also braced outside the piano/harp pair.
- **Status:** SEAN-adjacent/MEASURED HERE for the brace-means-one-player
  claim; ASSUMED for ottava bracket side. **WIRED 2026-09-29 (ROADMAP
  2.27d):** the pedal/grand-staff-dynamics gate now reads `Q.GROUP_SYMBOL`
  DECIDED `"brace"` directly (`structure.grand_staff_partner_staff`,
  `adjudicators/structure.py`) rather than `len(staves) == 2`, resolving
  this row's own named unreliability for those two consumers — the
  coarseness `Q.GROUP_SYMBOL` itself inherits (it decides "brace" for a
  whole SYSTEM from the union of all its groups' instruments, so a system
  holding BOTH a piano and an unrelated bracket pair would gate both) is
  NOT fixed, only contained by the block-membership check (FINDINGS
  §2.27d). Ottava OWNERSHIP (above/below, off the bracket's own geometry,
  no brace needed) is also now wired, `Q.OTTAVA_OWNER`; the SIDE
  convention itself is still ASSUMED, untested against a primary source.
- **Registry ref:** `[C65]`; ottava bracket — **GAP.**

---

## Rules safe to wire

Only rows above that are SEAN-CONFIRMED or clearly ESTABLISHED, and
DECISIVE (not a mere hint) for the specific question "a mark sits in the
pad between staff A and staff B — which one is it." Three are already
wired and kept here as precedent; two are not (item C, and the ottava/
pedal export emission named in item B's own update).

### Already wired (precedent, not a pending action)
1. **Ledger lines are authoritative** (`glyph_owner`'s `ledger_direction`
   hard gate, 2.6c/2.6f) — feeds `glyph_owner`.
2. **A hairpin separates staves** (`glyph_owner`'s `hairpin_separates`
   term, 2.6c) — feeds `glyph_owner`.
3. **A candidate already handed to the neighbour by a DECIDED
   `glyph_owner` verdict is not this mark's to attach to**
   (`_owned_by_a_different_staff`, 2.27) — feeds `articulation_owner`,
   `fermata_owner`, `ornament_owner`.
4. **Grand-staff dynamics are BOTH, not nearer** — item B below, WIRED
   2026-09-29 (ROADMAP 2.27d) — feeds `adjudicate_dynamic`.

### Not yet wired — proposed

**A. The dynamic-letter band rule** (`[C46 + L53]`, MEASURED HERE, 73%/24%
split with a 2.5-space empty gap between populations) → feeds
`adjudicate_dynamic` (`Q.DYNAMIC_BAND_POSITION` already exists, unread).
- Test 1: a `dynamicF` box whose y sits 0.5 spaces below staff N's bottom
  line reads as staff N's, even though staff N's own cell padding put the
  detection in staff (N−1)'s measure crop.
- Test 2: a `dynamicP` box whose y sits 5.5 spaces below staff N's bottom
  line (i.e., roughly 1 staff-distance further, in staff N+1's own band)
  reads as staff N+1's, not staff N's, even though it was detected inside
  staff N's cell.
- Test 3 (negative control): a `dynamicF` box sitting exactly in the
  middle of the pad, further than either band's own +0.3/−6.0 window,
  ABSTAINS rather than picking the nearer one by raw distance.

**B. Grand-staff dynamics are BOTH, not nearer** (`[L54]`) → feeds
`adjudicate_dynamic`, gated on a DECIDED brace verdict naming a
piano/harp-shaped pair.

**WIRED 2026-09-29 (ROADMAP 2.27d, `benchmarks/omr-owner-domain-2026-09/
FINDINGS.md` §2.27d).** `_canonical_grand_staff_owner` (`adjudicators/
text.py`) reads `structure.grand_staff_partner_staff`'s own `Q.GROUP_
SYMBOL`/`Q.STAFF_GROUP` connection rather than a fresh Piano-specific
check — same gate, phrased as "is this staff one half of a decided brace
pair" rather than "is the instrument named Piano", which is the more
general form `BRACE_FAMILIES = {keyboard, harp}` already states. Filed
ONCE, on the pair's canonical (upper-ordinal) staff, not literally on
"both" in the file — there is no MusicXML representation for a single
direction shared by two `<part>`s on this exporter's current one-staff-
one-part model, so "both" is expressed as "the part's own single copy,
deterministically placed" rather than two written copies. Both test
shapes below are BUILT, in `test_staged_grand_staff_2_27d.py`:
- Test 1 (built as `TestDynamicsSharedOnceOnly::test_GREEN_...`): on a
  braced pair with `Q.GROUP_SYMBOL` DECIDED `"brace"`, a `Q.GLYPH_OWNER`-
  CONTESTED letter is filed on the upper staff, dropped from the lower as
  a duplicate — not "routed through rule A" since rule A (the band
  position rule) is a DIFFERENT, still-unwired mechanism (2.27c);
- Test 2 (built as `..._RED_off_a_brace_...`, the negative control): the
  identical fixture with the pair's instrument NOT keyboard/harp
  (`family="brass"`) is untouched — the letter stays with whichever
  staff `Q.GLYPH_OWNER` named, exactly as before this item.

**C. `dot_role` gets the same `owned_by_another_staff` gate as 2.27**
(mechanical parity, not a new convention — `[C50 + L31]` plus the 2.27
precedent) → feeds `dot_role` / `adjudicate_duration`'s dot pairing.
- Test 1: a dotted head on staff A and a bare head on staff B, both
  candidates for a stray `augmentationDot` in the pad, where `glyph_owner`
  has already DECIDED the nearer-looking candidate belongs to staff B —
  the dot is not attached to staff B's head.
- Test 2 (positive control, matches 2.27's own): an uncontested dot with
  only one candidate in reach is unaffected by the new filter.

---

## Questions for Sean

Every ASSUMED row above that matters to the gap question, one line each.

1. Displaced rests in multi-voice bars (Rests row) — does the acceptance
   corpus (Beethoven 5, Brahms 1, Litolff, Breitkopf) contain any true
   multi-voice single staves with off-centre rests, or is this moot for
   the orchestral corpus? (yes it occurs / no, park it)
2. Grand-staff exceptions (pedal marks, between-staff dynamics, cross-
   staff beaming) — none of the four acceptance documents is a keyboard or
   harp part. Should these three rows be parked entirely until a keyboard
   work enters the corpus, rather than built speculatively now? (park /
   build anyway) **ANSWERED 2026-09-29 (Sean, DECISIONS): build anyway —
   WIRED, ROADMAP 2.27d, `FINDINGS.md` §2.27d.** MusicXML emission
   (`<pedal>`) is still unbuilt, named as an export gap there.
3. Bowing marks (`stringsDownBow/UpBow`) — should these be treated exactly
   like an articulation (notehead side, opposite stem, centred in x) by
   default, or is there a reason (e.g. always above regardless of stem,
   like marcato) to treat them differently? (same as articulation /
   different — which way)
4. Direction/tempo text's unexercised `above` band (the text-layer row) —
   is a text detection sitting clear above a system's top staff a case
   worth wiring as "system-level, duplicate it," or is it low-enough
   volume (0 of 98 candidates so far) to leave abstaining? (wire it /
   leave it)
5. Grace notes and fingerings inheriting their target note's decided
   `glyph_owner` verdict (rather than running their own nearest-staff
   search) — same mechanical fix as 2.27/`dot_role`. Worth building
   alongside `dot_role`'s fix (item C above) in one pass, or should each
   family get its own adjudication and its own crops first? (batch them /
   one at a time)
6. Ottava bracket side (above staff = 8va, below = 8vb) — ASSUMED by
   analogy to hairpins/dynamics (above/below convention exists for
   *something* in this position); no source was found confirming it
   directly. Worth a quick confirm, or is it out of scope (no ottava
   brackets fire on the acceptance corpus today)? (confirm / out of scope)
   **ANSWERED 2026-09-29 (Sean, DECISIONS): occurs both above AND below on
   the real corpus, so not out of scope — the above=8va/below=8vb SIDE
   MAPPING itself remains ASSUMED (still no primary source), but OWNERSHIP
   (which staff, geometry only) is now WIRED, `Q.OTTAVA_OWNER`, ROADMAP
   2.27d, `FINDINGS.md` §2.27d — including the MusicXML `type` inversion,
   checked against `usermanuals.musicxml.com` and recorded there. Span and
   `<octave-shift>` emission remain unbuilt.**
