# The stem exception space, and the missing adjacent-stems register

**Why this exists.** After two stems were read as one vertical run (a duration
fault), Sean's framing was: *"Stems are usually a similar length but not
always. They generally go in a particular direction based on where the note
they are connected to is based on the center of the staff — but not always.
The stem will be longer if it goes through multiple vertical notes that are a
chord. All of these feel like they fall short… We need to know every possible
scenario — I don't know of a few single rules that will give us what we need."*
His three base rules (length, direction, chord-length) are **already in the
merged registry** (`docs/engraving-conventions.md`, "Stems & beams", 18
entries). This document does not restate them. It does two things the
registry does not yet do:

- **(A)** enumerates, for each of those base rules, **every case it does not
  hold** — the "but not always" made exhaustive rather than said three times;
- **(B)** builds the register that is missing entirely: **when can two
  distinct stems be adjacent, touching, or collinear in print**, and what would
  tell a reader that ink is two stems and not one.

**What duplicates the registry: nothing, by design.** Every base rule cited
below is a link to its registry entry, not a restatement. Where this document's
research corroborates a registry entry from a new source, that is marked
`[confirms C#/L#]`; where it adds a genuinely new claim, `[NEW]`.

**Provenance discipline, inherited from the registry and from
`docs/ask-first-conventions.md`.** ⚠️⚠️ **Everything in this document is
`LITERATURE ONLY` unless stated otherwise, and none of it has been measured on
this project's own plates.** No entry here is promoted to `MEASURED HERE`. The
registry's own rule applies without qualification: *a font/engraving-software
default is not a measurement of a 19th-century plate*, and *nothing in the
literature is about scans*. Every entry states what a cheap test against this
project's already-gathered records would look like — described, not run.
Numbers are in **staff spaces**, never pixels.

**Sources used**, cited inline per entry: Elaine Gould, *Behind Bars* (Faber,
2011) — page numbers where locatable via the public sample and secondary
citation, otherwise "Gould" with topic; Wikipedia's *Stem (music)* article
(itself sourced largely from Gould and Ross, and already the registry's `L10`
source); SMuFL 1.4 specification and Bravura 1.x `glyphsWithAnchors` /
`engravingDefaults` metadata (the registry's `L10`/`L19`/`L20`/`L23` source);
LilyPond 2.23–2.25 Notation and Internals references (`note-collision-interface`,
`note-column-interface`, cross-staff-stems snippet); Finale user manual
(*Stems*, *Double or split stems*, *Cross-staff notation*); Dorico help centre
(*Grace note slashes*, *Notes crossed to staves*). Ted Ross, *The Art of Music
Engraving and Processing*, could not be searched directly (out of print, no
searchable web text found) — every place Ross would normally corroborate is
marked and left as a gap in §D.

---

## Contents

- [A. The complete exception space](#a-the-complete-exception-space) — per base rule, every case it does not hold
- [B. THE MISSING REGISTER — when can two stems be adjacent, touching, or collinear?](#b-the-missing-register--when-can-two-stems-be-adjacent-touching-or-collinear)
- [C. Grading summary](#c-grading-summary) — one table, every entry, HARD / STRONG TENDENCY / PREFERENCE and whether it is measurable on a scan
- [D. What is not established](#d-what-is-not-established)

---

## A. The complete exception space

Organized under the registry's own base rules. Each subsection names the rule,
links it, then enumerates exceptions **exhaustively as currently known** — not
"but not always" repeated, but every distinguishable case.

### A.1 — Stem attaches right-going-up / left-going-down
Base rule: [`A stem attaches on the RIGHT going UP, or on the LEFT going DOWN`](../engraving-conventions.md#a-stem-attaches-on-the-right-going-up-or-on-the-left-going-down) `[C9 + L10]` — registry already grades this **HARD**, "one of the most reliable conventions in all of notation," and already records its one exception (a chord containing a second, where one head sits on the "wrong" side — `[L19]`, §A.4 below).

There is, in the literature surveyed for this document, **no further exception
to which SIDE the stem attaches on.** This is the most rigid claim in the
entire stem family — nothing found here weakens it. What varies is not the
attachment side but **which direction the stem points**, covered next.

### A.2 — Stem direction from staff position (single voice)
Base rule: [`In a single voice, a note above the middle line is stemmed DOWN`](../engraving-conventions.md#in-a-single-voice-a-note-above-the-middle-line-is-stemmed-down) `[C10 + L16]` — registry already grades this REFUTED AS A READER on this project's own data (reverses at 6+ steps from the middle line) while CONFIRMED AS A RULER, and already records its two named exceptions: **two-voice writing** and **chords**.

Exhaustive list of what overrides plain staff-position:

| exception | what happens | tag | source |
|---|---|---|---|
| **Two (or more) independent voices on one staff** | direction becomes a **voice label**, not a position consequence — see §A.6/§B | HARD (within genuinely divided writing) | Wikipedia *Stem (music)*; `[L17]` |
| **Voice crossing** | the crossing voice keeps ITS voice's assigned direction even though its pitch has crossed the other voice's — i.e. direction stays **attached to the voice, not the note** `[NEW]` | HARD, by the same logic as `[L17]` | inferred from `[L17]`'s own wording — "regardless of position" — and corroborated by Finale's *reverse stem* documentation for cross-staff notes (below) |
| **"Reverse stem"** — a stem drawn on the opposite side/direction from what plain position would give, used when a note is engraved on a staff that is not its own (cross-staff notation) or when a voice's notes must stay visually distinct through a crossing | direction (and which staff it visually sits on) is decoupled from the note's own pitch | STRONG TENDENCY (software convention; period-plate frequency unmeasured) | Finale user manual, *Cross-staff notation*: *"A reverse stem is one that's drawn on the 'wrong' side of its notehead; it's encountered most frequently in conjunction with cross-staff notes."` `[NEW]` |
| **Some editions use down-stems exclusively** (already in registry as `[L15]`'s known exception, restated here because it also overrides §A.2, not only §A.7's ambiguous-case default) | staff position is ignored entirely for the whole part | PREFERENCE (edition-specific) | Gould, cited at `[L15]` |
| **Vocal music set with up-stems throughout, to keep text close to the staff** (already in registry at `[L15]`) | same override, opposite direction | PREFERENCE | Gould, cited at `[L15]` |
| **A chord straddling the middle line** — not covered by `[L16]`'s wording at all; direction must come from **which side of the middle line has more of the chord**, not from a single staff position | direction decided by chord majority/extreme, not by "the note's" position (there is no one note) | HARD as a chord rule, see §A.3 | Wikipedia *Stem (music)*: for a chord, "the direction is determined by the notehead that is furthest from the middle line" `[NEW, confirms the registry's own chord entry indirectly]` |

⚠️ **What the registry's own measurement adds here, restated for completeness
(not new):** the position rule REVERSES at 6+ steps from the middle line
(0.939 → 0.765) and the cause is diagnosed as **ledger-country position error**,
not a third notation exception — i.e. the convention itself does not have a
"far outside the staff" exception; the READING of far-outside positions does.
That is a reading-pipeline fact, not an engraving fact, and stays out of this
exception list for that reason.

### A.3 — Chord stem length and direction
No single registry entry states "a chord's stem reaches its furthest
notehead" as its own row — it is implicit in `[C13]`'s "as long as the music
needs it to be" and in the beam-length entries `[C12]`/`[C79]`. This document
makes it explicit because Sean named it directly ("The stem will be longer if
it goes through multiple vertical notes that are a chord").

- **Length**: a chord's stem extends from the **nominal default length past
  the notehead furthest from the stem's own end** — i.e. the stem is drawn
  long enough to clear every notehead in the chord, then the default length is
  measured from the OUTERMOST head, not from the notehead nearest the stem's
  point of origin. `[NEW]`. Wikipedia *Stem (music)*: "For a chord (multiple
  noteheads stacked on the same stem), the length of the stem is usually
  determined by the notehead furthest from the notehead nearest the stem's
  point of origin, i.e. the note closer to the end of the stem" — HARD.
- **Direction**: decided by the notehead furthest from the middle line (not
  the notehead nearest it), same source, HARD.
- **Exception — a chord spanning both sides of the middle line about equally**:
  direction becomes a tie-break the literature does not resolve numerically;
  Gould's general guidance (cited secondhand at `[L15]`/`[L16]`) is that where
  there is no clear-cut case, the convention defaults to down. **PREFERENCE**,
  unmeasured.
- **Exception — divisi chord on one stem vs. two separate voices**: see §A.6.
- **What could be measured**: this project already gathers `Q.STEM` per glyph
  and `Q.EVENT` groups noteheads into chords. A cheap test: for every DECIDED
  chord event, take the stem's measured length and the staff-position spread
  of its member noteheads, and check whether `stem_length ≈ default_length +
  (span_to_furthest_head − span_to_nearest_head)`. This is a test the project
  can run against its own committed records with **no re-gather** (stem and
  chord grouping are already GATHER-stage facts) — described here, not run.

### A.4 — Seconds and clusters (heads straddling the stem)
Base rule: [`In a chord containing a second, the two heads straddle the stem`](../engraving-conventions.md#in-a-chord-containing-a-second-the-two-heads-straddle-the-stem) `[L19]` — registry already flags this LITERATURE ONLY (untested here) and already flags it as a **live candidate explanation for Sean's "doubled notes connected to the same stem" complaint**, and already records ONE exception: "clusters of three or more adjacent notes, where middle notes appear on the opposite side."

Enumerated:

| configuration | placement | tag | source |
|---|---|---|---|
| single second (2 heads a step apart) | higher head RIGHT of stem, lower head LEFT | HARD | Wikipedia *Stem (music)*, `[L19]` |
| cluster of 3 adjacent seconds (e.g. a tight tone cluster) | **alternates**: the two outer heads sit on opposite sides from each other, and any head in the MIDDLE of the run sits on the opposite side from the general run-direction rule — i.e. not simply "outer=default side, all inner=flipped" but alternation by adjacency, confirmed only in general terms by the sources found | STRONG TENDENCY, mechanism not fully sourced numerically | `[L19]`'s own "Known exceptions" line; not independently re-found in this pass — **gap, see §D** |
| a second where one member is a **unison with the other voice** rather than a second within one chord | not a seconds-straddle case at all — becomes the unison-shared-notehead case, §B.4 | — | `[NEW]`, boundary case |
| **What could be measured**: the registry's own note is the strongest lead — this project's dedupe/ownership work already found "repeated-pitch chord events 122 → 108" and an unresolved same-cell residue it says a contest-based repair "structurally cannot reach." A seconds-straddle pair is same-cell, one-stem, adjacent-position — exactly that residue's shape. A cheap test: for every remaining same-cell repeated/adjacent-position pair, check whether the two heads are offset by ≈1 notehead width (1.18–1.328 sp, per Bravura `stemUpSE`/`noteheadBlack` anchors) on opposite sides of one detected stem, rather than being two full detections of one head. Described, not run.

### A.5 — Stem length: the ledger-line boundary cases
Base rule: [`A stem on ledger lines reaches the middle staff line`](../engraving-conventions.md#a-stem-on-ledger-lines-reaches-the-middle-staff-line) `[L12]`, already LITERATURE ONLY (untested here), already cross-referenced by the registry to `[C13]`'s long-stem population and to `[C10]`'s 6+-step reversal.

The requested boundary cases, which the registry entry does not separate out:

- **Exactly 1 ledger line outside the staff**: the "reaches the middle line"
  rule does **not** yet apply — Gould's rule (per `[L12]`) is stated for notes
  "on **more than one** ledger line," i.e. it activates at the 2nd ledger line
  and beyond. A note on exactly one ledger line still takes a normal-length
  stem (the 3.5 sp default, or whatever the beam/chord context sets). **HARD**
  as a threshold, restated from the literature's own wording, `[NEW]` (the
  registry's entry does not state the 1-vs-2+ boundary explicitly).
- **2+ ledger lines**: stem is drawn out to the middle line — so stem length
  is no longer a free default but a **computed distance** from the notehead's
  own (ledger) position to the middle line. This makes stem length a **second,
  independent reading of the notehead's staff position** wherever it applies:
  if a candidate stem's far end does not land near the middle line for a head
  claimed to be 2+ ledger lines out, either the stem reading or the pitch
  reading is wrong. `[NEW, but flagged by the registry itself as "the
  untested pitch check `[C3]` and `[C10]` both want"]`.
- **Double-stemmed (two-voice) writing outside the staff**: Gould's exception
  to the middle-line rule — outside-staff stems in double-stemmed writing are
  **progressively shortened** rather than both reaching the middle line
  (already flagged in the registry as `[L12]`'s "Known exceptions" and again
  under `[L13]`'s stem-length disagreement). This is the single most important
  exception for §B: it is the mechanism that is supposed to **prevent** two
  voices' outside-staff stems from ever actually meeting, by cutting them
  short before they collide. See §B.1.
- **A beamed group that spans in-staff and 2+-ledger-line notes in one
  stroke**: the middle-line target and the beam-slope/length rule (`[L21]`,
  `[C12]`/`[C79]`) are now in tension — the literature does not resolve which
  wins for the ledger-line member specifically, beyond the general beam-length
  literature already in the registry (`[C13]`: "a note two ledger lines above
  the staff beamed to notes inside it carries a stem far longer than any
  default" — measured HERE already, `[confirms C13]`). No further exception
  found for the SHAPE of that stem beyond what `[C13]`/`[C12]` already state.
- **What could be measured**: for every DECIDED notehead at ≥2 ledger lines
  with a read stem, check the stem's far-end y against the staff's own middle
  line (already a GATHER-stage fact, `Q.STAFF_SPACING` / the staff frame). A
  systematic offset would be evidence either that this plate does not follow
  the rule, or that the pitch/ledger reading is off by a constant — described,
  not run.

### A.6 — Divisi, unison, and "shared" noteheads
Not a registry entry at all today — this is a wholly missing sub-topic Sean
named directly ("if it goes through multiple vertical notes that are a
chord").

| configuration | how it is engraved | tag | source |
|---|---|---|---|
| **Divisi, written as two independent voices** | two separate noteheads, two separate stems, one up / one down, by `[L17]`'s rule — this is the PREFERRED modern orchestral convention because it shows unambiguously which desk plays which note | STRONG TENDENCY (stated as "generally preferred" rather than universal) | Orchestration Online, *Divisi vs. Double Stops*; general orchestration-pedagogy sources `[NEW]` |
| **Divisi written as a two-note chord on one stem** (both notes on ONE stem, i.e. treated as a dyad rather than two voices) | one stem, two noteheads a third or more apart (if closer, becomes the seconds-straddle case, §A.4) | PREFERENCE, less common in orchestral divisi specifically, more common in choral/keyboard reductions | same sources, `[NEW]` |
| **Unison written with a double (split) stem** | **one notehead**, TWO stems drawn from it in opposite directions (one up, one down) — "two parts sing the same note, one head serves both, and the stems say how many voices are meeting on it" | HARD as a description of the mark; STRONG TENDENCY as to WHEN an engraver chooses it over writing two identical noteheads side by side | Finale user manual, *To create a double or split stem*; corroborating discussion sources `[NEW]` — **this is the sharpest, most load-bearing entry for §B**, see §B.4 |
| **Divisi "a2" collapsed back to unison mid-passage** | the two stems of a prior divisi note MERGE into a single double-stemmed unison notehead at the reunification point — a genuinely two-stems-on-one-head event that is not a misread | HARD as a shape, unmeasured as a frequency | inferred from the double-stem convention above, `[NEW]` |
| **What could be measured**: this is the shape most likely to explain part of the residual same-cell repeated-pitch population the dedupe work left unrepaired (`122 → 108`, "the remainder is the SAME-CELL population"). A double-stem unison would show as: ONE notehead detection, ONE stem-attachment-adjacent pair of near-vertical strokes both touching that SAME head at x≈0 offset, one extending up and one down — geometrically indistinguishable at the notehead from a single very-long stem UNLESS the two strokes are checked for CONTINUITY through the head (a real double stem has a visible gap/notehead-fill between the two strokes at the head, where a single misdetected long stroke would be continuous ink straight through). Described, not run — see §B.4 for the full discriminator.

### A.7 — Cross-staff beaming
Not in the registry at all — Sean's brief asked for it explicitly.

- **What it is**: a single beam stroke joins stems whose noteheads sit on two
  DIFFERENT staves of the same system (most often a piano grand staff, but the
  same shape occurs on any bracketed pair — e.g. two divisi desks notated on
  adjacent staves in some 19th-century engravings). LilyPond's own cross-staff
  snippet documents this as a standard, supported case: `\change Staff` mid-beam,
  with the beam drawn to visually connect the two staves' noteheads. **HARD**
  as an existing, named convention; **STRONG TENDENCY** as to how *often* a
  19th-century orchestral plate (as opposed to a piano reduction) uses it —
  unmeasured, and orchestral full scores in this project's corpus are staves
  of DIFFERENT INSTRUMENTS, not one player's two hands, so the printed
  motivation for cross-staff beaming (one performer, one musical line, split
  across a grand staff) does not apply to most of what this project reads. The
  nearest analogue in orchestral full scores is a **cue** printed on a
  neighbouring staff, which is a different mechanism (small notes, own stems,
  not sharing a beam with the main staff).
- **Geometric consequence for adjacency**: where it does occur, a stem
  belonging to staff N's notehead can extend far enough to cross the
  inter-staff GAP and terminate at a beam positioned in staff N+1's band —
  i.e. **the physical location of a stem's far end is no longer bounded by
  that staff's own cell at all.** This is the single most severe case for the
  cross-staff notehead-ownership contest this project already has
  (`glyph_owner`, the "ownership is RESOLVED not relocated" work) — a
  cross-staff BEAM makes a cross-staff STEM correct rather than a detection
  fault, which the existing ownership machinery has no vocabulary for (it
  reasons about GLYPHS, and a stem currently has no `Q.STEM_OWNER` decision at
  all — `Q.STEM` is gathered and, per the registry's own `[C9]` entry, "read by
  nothing" downstream).
- **What could be measured**: reach first, per this project's own house
  discipline. Since orchestral full scores rarely if ever print cross-staff
  beams between different instruments' staves, the honest expectation is a
  **near-zero reach** on this corpus — worth stating explicitly rather than
  building for it. Described, not run.

### A.8 — Grace notes and cue notes
Not in the registry at all — Sean's brief asked for it explicitly.

- **Notehead and stem are both scaled down** as a unit (smaller notehead,
  thinner/shorter stem), not merely a shorter stem on a full-size head.
  **HARD** as a description. Source: Dorico help centre, *Grace note slashes*;
  general engraving-software documentation. `[NEW]`
- **Default stem length is shorter than a normal note's** — approximately
  **2–2.5 staff spaces**, against the normal 3.5 sp default (`[C13]`/`[L11]`).
  **PREFERENCE/software-default**, not independently corroborated by Gould in
  this pass beyond the secondary citation found. `[NEW, weakly sourced — see §D]`
- **Acciaccatura (grace note with a slash) vs. appoggiatura (no slash)**: the
  slash is drawn diagonally ACROSS the stem, near the notehead end — i.e. a
  short diagonal stroke crossing a short near-vertical stroke, at the grace
  note's own reduced scale. **HARD** as the shape distinction between the two
  grace-note kinds (this is how a reader tells them apart at all — duration is
  not otherwise notated). Source: Wikipedia *Grace note*; Dorico help centre.
  `[NEW]`
- **Gould's own stated hazard**: *"Ensure that a grace note on ledger lines has
  a sufficiently long stem for the diagonal stroke not to obscure a ledger
  line"* — i.e. the ledger-line-reach rule (`[L12]`, §A.5) is in TENSION with
  the grace note's normally-shorter stem, and Gould's guidance is to let the
  ledger-line rule win when they conflict. **STRONG TENDENCY**, `[NEW]`.
- **What could be measured**: grace notes are a genuinely small population in
  orchestral full scores of this repertoire. A cheap test: for any detected
  small-scale notehead (this project already has a size-based grace-note veto
  measured elsewhere — `benchmarks/omr-prefill-admission-2026-09/`, "grace-sized,
  < 0.85× the cell's median in both dimensions" — REUSE that discriminator,
  do not re-derive it), check whether its stem length falls in the 2–2.5 sp
  band rather than the 3.5–8.0 sp band the main stem-length work already
  measured. Described, not run.

### A.9 — Tremolo
Base rule: touched at [`A TREMOLO rides the stem, so it has no side at all`](../engraving-conventions.md#a-tremolo-rides-the-stem-so-it-has-no-side-at-all) — the registry entry is about SIDE (a tremolo has none, unlike an articulation), not about whether the stem's LENGTH or the number of strokes interacts with stem geometry. This document adds that.

- **A one-stroke tremolo may cross a staff line**; a tremolo of **two or more
  strokes must clear the notehead by at least one staff space.** **HARD** as a
  spacing rule (a specific, quotable number). Source: secondary citation of
  Gould's tremolo guidance found via web search — **could not verify the exact
  page or wording against the primary text in this pass; treat as
  moderately-confident LITERATURE ONLY, flagged for verification in §D.**
  `[NEW]`
- **Consequence for stem length**: a multi-stroke tremolo needs ROOM on the
  stem — 3+ strokes at typical stroke spacing (comparable to the beam-spacing
  figure already measured in this project, `BEAM_Y_CLUSTER_FACTOR` region,
  `[C79]`) plus the 1-space clearance above, can require a stem measurably
  longer than the plain 3.5 sp default even on an otherwise unremarkable
  in-staff note. **STRONG TENDENCY**, inferred rather than directly sourced.
  `[NEW]`
- **Whole notes and other stemless notes**: the tremolo strokes are centred
  ABOVE or BELOW the notehead instead of riding a stem — already implicit in
  the registry's tremolo entry title ("no side at all") but the "no stem to
  ride" case is worth naming explicitly as its own configuration, not merely
  the "no side" one. `[NEW]`
- **What could be measured**: this project already gathers `Q.STEM` and has a
  tremolo class in its detector space (`tremolo1`–`5`, per `CLAUDE.md`'s own
  record that the detector currently produces **zero** tremolo detections
  across 34,115 detections walked — a DETECTION gap, not a convention gap, per
  the existing `<ornaments>`/tremolo finding). No cheap test is proposable
  against real data until that detection gap closes — noted as a dependency,
  not run.

### A.10 — Collision avoidance and stem shortening under tight spacing
Not a single registry entry — spread across `[C13]`/`[L12]`/`[L13]` but never
stated as its own topic. This is also the mechanism most directly relevant to
§B, because it is what SHOULD prevent two independent stems from touching.

- **The base mechanism**: where two voices' noteheads sit closer than a
  threshold, an engraver/engraving system does not merely accept a collision —
  it **horizontally offsets** the noteheads (never merely lets the stems
  cross) so the stems clear each other. LilyPond's own operational rule gives
  an exact, quotable number: `note-collision-threshold = 1` (staff space) —
  simultaneous notes THIS close or closer are treated as colliding and are
  shifted. **HARD** as an operational default; **whether a specific
  19th-century hand engraver hit exactly this threshold is unmeasured.**
  Source: LilyPond Internals Reference, `note-collision-interface`. `[NEW]`
- **The shift step size**: LilyPond's `force-hshift`/`horizontal-shift`
  mechanism moves colliding note-columns in **steps of roughly half a
  notehead's width**, occasionally a full notehead width for tightly packed
  groups. Given a notehead width of ≈1.18–1.33 staff spaces (Bravura
  `noteheadBlack` bbox / `stemUpSE` anchor x-value, already cited at `[C9]`
  and `[L19]`), the minimum horizontal separation between two colliding
  voices' stems after a shift is on the order of **0.5–0.7 staff spaces** —
  enough that the two stems' ink no longer overlaps, but small enough that on
  a degraded scan the gap between them can be a single ink-bridge away from
  reading as one stroke. **STRONG TENDENCY** (software default, not a
  measured plate figure). `[NEW]`
- **Vertical shortening as the OTHER collision-avoidance route** (Gould,
  cited above at §A.5): *"stems are typically shortened to keep the music
  visually centered upon the staff"* when two voices share a staff — this is
  the mechanism specific to STEM LENGTH rather than notehead x-position, and
  it is the one that directly bears on §B: **a correctly engraved plate should
  almost never show two independent voices' stems actually touching in the
  region between them**, because the engraver is expected to shorten them
  first. **STRONG TENDENCY**, not independently re-derivable to a number in
  this pass — flagged for verification in §D.
- **Stems lengthened instead of shortened, to clear a slur/tie/articulation
  printed close to the notehead**: general engraving-software behaviour
  (Dorico, Finale, Sibelius all reposition or lengthen a stem to avoid a
  collision with an adjacent notation element) — **PREFERENCE, software-era
  only, no historical-plate evidence found**; on a hand-engraved 19th-century
  plate the more likely behaviour is that the ENGRAVER accepted a tighter
  spacing rather than lengthened a stem, since stem length is otherwise a
  fairly rigid convention (`[C13]`). Flagged as **UNESTABLISHED for this
  repertoire** rather than asserted either way. `[NEW]`

---

## B. THE MISSING REGISTER — when can two stems be adjacent, touching, or collinear?

**This register does not exist anywhere in `docs/engraving-conventions.md`,
`docs/conventions/from-the-literature.md`, or `docs/conventions/from-this-repo.md`
today.** Every entry below is `[NEW]`. This is the direct answer to the
question that prompted the research: a reader sees a vertical run of ink and
needs to know the enumerated set of what it could be, and — critically — what
would tell the two apart.

**The governing fact, established in §A.10 and repeated here because it is
the single most important finding of this document:** properly engraved music
is supposed to actively PREVENT two independent stems from touching, by
shifting noteheads apart (LilyPond's `note-collision-threshold = 1` staff
space) and by shortening stems where two voices approach the middle of the
staff (Gould, cited above). **So the base rate of two independent, distinct
stems genuinely touching on a WELL-engraved plate should be low**, and the
cases below split into (i) configurations where touching/collinearity is the
CORRECT, deliberate mark (not an error to resolve — a real second mark), and
(ii) configurations where the collision-avoidance machinery has failed, either
because the engraver ran out of room on a dense plate, or because we are
looking at plate wear/ink bleed on a scan rather than the engraver's ink at
all.

### B.1 — Two voices' stems approaching each other toward the middle line

**Configuration.** Voice 1 (upper, up-stem by `[L17]`'s rule, §A.2) and Voice
2 (lower, down-stem) both have notes near the middle line at the same
rhythmic position — this is the exact case Sean's example ink most plausibly
came from (two chords/notes on one beat, stems converging toward the centre
of the staff rather than diverging away from it, which happens whenever both
voices sit close to the middle line rather than at their extremes).

- **How far apart, in staff spaces**: **this is the one number this pass could
  not source directly and it is the most important number for the register.**
  Two lines of indirect evidence: (a) the default stem length is 3.5 sp
  (`[L11]`), so two notes each within ~3.5 sp of the middle line have stems
  that WOULD overlap at full length; (b) Gould's stated remedy is to SHORTEN
  both stems rather than let them meet — which implies the target minimum gap
  is **strictly positive but is not quoted as a number** in any source found
  in this pass. **UNESTABLISHED — flag directly to Sean or find the primary
  Gould text (§D).**
- **What distinguishes it from one long stem**: (1) **two separate noteheads**,
  one at each end of the apparent "long stroke," rather than one notehead at
  one end and nothing at the other; (2) the total length of the apparent
  stroke, if it really is two shortened stems meeting, will generally be
  **shorter than a single default-length stem projected the same distance**
  would require if it had to originate from only one of the two noteheads —
  because BOTH stems were shortened toward each other rather than one running
  the whole gap; (3) if a beam or flag is present on either end, it will sit
  on the OUTER side of its own notehead (away from the other voice), never on
  the inner/facing side; (4) **the two noteheads' staff positions, read
  independently, should each individually satisfy the position→direction rule
  for THEIR OWN voice** (voice 1's note is stemmed up regardless of how close
  it sits to the middle line; voice 2's note is stemmed down) — so a
  genuine two-voice pair reads as "up-stem note, short reach, meeting a
  down-stem note, short reach" and NOT as "one note at one end, an ordinary
  stem, and nothing distinguishing at the other end."
- **Tag**: STRONG TENDENCY that the two stems are SHORTENED rather than
  literally touching (Gould); the touching/near-touching CASE ITSELF is a real,
  attested configuration (two independent voices at close pitch) but its
  frequency and its exact clearance are unmeasured here.
- **What could be measured on this project's own plates**: this is directly
  testable against the `Q.VOICES` / two-stream grouping this project already
  has (`export._events`, the voice-split machinery the fermata/voices wiring
  session built — see `CLAUDE.md`'s "Three families wired in one pass"
  section). For every bar the record already marks as two-voice, take the
  paired up-stem/down-stem note nearest the middle line and measure the
  clearance between their stem ends. That single measurement would answer the
  question this entry currently cannot: is there a real minimum gap on THIS
  project's own plates, and is it closer to Gould's "shortened" ideal or to
  actual touching. Described, not run.

### B.2 — Voice crossing (stems pointing toward and past each other)

**Configuration.** A genuine voice crossing: voice 1 (assigned up-stem) is
temporarily LOWER in pitch than voice 2 (assigned down-stem). Per §A.2, each
voice KEEPS its assigned direction through the crossing — so voice 1's stem
now points UP from a LOW note, potentially running through or past the region
where voice 2's HIGHER note and its DOWNWARD stem sit, and vice versa. This is
geometrically the most severe convergence case in the whole register, because
unlike B.1 (both voices near the middle, stems shortened toward each other) a
crossing can put the two stems running in the SAME vertical band with **no
shortening convention to rescue it**, since Gould's shortening advice is
stated for stems approaching the middle line, not explicitly for a crossing.

- **How far apart**: unestablished; plausibly the SAME shortening mechanism as
  B.1 applies but no source found states so explicitly for the crossing case
  specifically.
- **What distinguishes it from one long stem**: the same four cues as B.1,
  PLUS one more that is unique to crossing: **the pitch order printed on the
  page will look "backwards" relative to the voices' usual registral roles**
  (the "up-stem" voice's note is, for this one instant, drawn LOWER on the
  staff than the "down-stem" voice's note) — a fact a pitch reader could check
  independently of stem geometry, and use as CORROBORATION rather than as the
  primary signal (the stem geometry finds the candidate; the pitch order
  confirms it is a real crossing and not a misread).
- **Tag**: STRONG TENDENCY as a described, real engraving event (Finale's
  documentation of "reverse stems," Wikipedia's *voice crossing* article);
  UNESTABLISHED as to frequency or clearance in this repertoire.
- **What could be measured**: same instrument as B.1 — restrict to two-voice
  bars where the voice-1/voice-2 pitch ORDER at that instant contradicts the
  bar's overall registral order. Described, not run.

### B.3 — A second between the two voices (near-unison, not exact unison)

**Configuration.** Voice 1 and voice 2 are a SECOND (or a third) apart at one
beat — close enough that plain up/down stemming alone would put the two
noteheads' stems directly in line with each other, so the ENGRAVER offsets
one notehead horizontally (the same `note-collision-threshold`/`force-hshift`
mechanism as §A.10, but now applied ACROSS voices rather than within one
chord).

- **How far apart**: the shift step gives a concrete number — roughly
  **0.5–0.7 staff spaces** of horizontal offset between the two noteheads
  (from the notehead-width-based shift steps in §A.10), which puts the two
  stems at that same horizontal offset rather than collinear. This is the
  **cleanest, most measurable case in the whole register** because it produces
  a specific, non-zero, non-touching geometric signature: two stems at a fixed
  small x-offset, both of normal-ish length, NOT collinear.
- **What distinguishes it from one long stem or from B.1/B.2**: the two
  noteheads are **offset in x**, not stacked at the same x — this alone rules
  out "one long vertical run of ink," because a single stem does not shift
  sideways partway up. A detector that already localizes noteheads and stems
  separately (as this project's does) should never confuse this case with a
  single stem UNLESS the offset is smaller than the detector's own positional
  noise floor.
- **Tag**: HARD as to the MECHANISM (an engraver never lets two different-pitch
  noteheads a second apart share one exact vertical stem line — this is one of
  the most basic spacing rules in all engraving, corroborated independently by
  the accidental-pair-deletion finding already in the registry, `[C14]`,
  which found that TWO VOICES a second/close apart are exactly the
  configuration its own "0.9 sp gap, drop both" heuristic was wrongly deleting
  — see the cross-reference below). **This entry and `[C14]`'s refutation are
  the same underlying shape, described from two directions.**
- **What could be measured**: this is not hypothetical — it is **already
  partially measured, by accident, in this project's own tree.** `[C14]`'s
  entry states: *"an up-stemmed upper voice and a down-stemmed lower voice in
  one column are two strokes within 0.9 spaces that overlap vertically"* is
  the refuted rule's own predicted failure mode, and the measured excess is
  **+13.8 / +64.1 points** on missing-stem-beside-close-partner across the two
  publisher corpora. **This document's contribution is to name that measured
  shape as an instance of a real, sourced engraving convention (the
  cross-voice second/collision offset) rather than leaving it as an
  unattributed geometric coincidence** — which changes the fix from "loosen a
  threshold" to "the 0.9 sp gap test IS finding real two-voice pairs and
  should stop deleting them, not merely widen its own tolerance." `[confirms
  C14, reframes it]`.

### B.4 — Unison, one notehead, two stems (the double/split stem)

**Configuration.** Two voices land on the exact same pitch at one beat. The
engraver's choice, per §A.6: draw ONE notehead with TWO stems, one extending
up and one extending down from the **same point**.

- **How far apart**: **zero** — by definition the two stems originate at the
  identical (x, y) point, the notehead's own centre/attachment point. This is
  the ONE case in the entire register where the two stems are not merely
  close but **share an origin**.
- **What distinguishes it from one long stem THROUGH a notehead (the fault
  class this document was commissioned to prevent)**: this is the sharpest,
  most answerable discriminator in the whole document.
  1. **Direction reversal at the head.** A genuine long single stem runs
     monotonically in one direction (all the way up, or all the way down)
     from its notehead. A double stem reverses DIRECTION exactly at the
     notehead: ink goes up above the head AND down below it, from the SAME
     point. A single mis-merged stem (two adjacent voices' short stems bled
     together by scan degradation, B.1/B.2) will instead show TWO noteheads,
     one near each end, not one notehead in the middle with ink on both
     sides of it.
  2. **Symmetry/length signature**: a double stem's two halves are each
     typically close to the SAME length as an ordinary single stem would be
     for that voice (i.e. up half ≈ 3.5 sp region toward its own beam/flag,
     down half ≈ 3.5 sp region toward its own beam/flag) — so the total
     ink span is roughly **2× a normal stem length**, centred symmetrically
     on ONE notehead, rather than the asymmetric, shortened-toward-each-other
     signature of B.1 (two different noteheads, likely two different
     lengths).
  3. **A double stem's notehead sits in the MIDDLE of the total ink run,
     not at either end** — the cheapest single test of all four in this
     document. A vertical run of ink with exactly one detected notehead
     roughly at its own midpoint, and no second notehead near either end, is
     the double-stem/unison signature; a run with a notehead at ONE end and
     nothing at the other is a plain long stem (possibly mis-capped, `[C13]`);
     a run with a notehead at EACH end is B.1/B.2/B.3 (two voices).
  4. **Each half may independently carry its own beam or flag**, since the
     two stems represent two independently-rhythmed voices that merely
     happen to share a pitch at this one instant — so a double stem is not
     necessarily "no flags," it can have a flag or beam on one or both ends.
- **Tag**: HARD as a description of the mark (Finale's own documentation
  states it plainly, and it is corroborated by general choral/keyboard
  engraving practice); STRONG TENDENCY as to WHEN an engraver reaches for it
  rather than simply printing one plain notehead with one stem and letting the
  unison go unmarked (the latter is also legitimate where the two voices'
  RHYTHM is also identical, in which case there is no visual need for a second
  stem at all — the double stem specifically signals "two voices, temporarily
  the same pitch, possibly different rhythm/duration").
- **What could be measured**: cross-reference to this project's own dedupe
  work again — the "repeated-pitch chord events 122 → 108" residue and the
  explicit statement "the remainder is the SAME-CELL population, which a
  contest-based repair structurally cannot reach" (`CLAUDE.md`, "A CONTEST is
  RESOLVED, not relocated"). A double-stem unison is EXACTLY a same-cell,
  same-pitch, two-detection event by construction (one notehead, but the stem
  detector may well fire twice, once per direction) — this predicts that at
  least some of that unrepaired residue is not duplicate detection error at
  all but a correctly-printed unison mark, and the fix is not "delete one
  copy" but "recognise the double-stem shape and keep both voices with one
  shared notehead." Described, not run — and flagged as a candidate
  explanation worth checking BEFORE any further dedupe work on that residue,
  per the registry's own note that `[L19]` (the seconds case) is "a live
  candidate explanation for Sean's own complaint" — this is the unison
  sibling of that same candidate.

### B.5 — Cross-staff stem (the far end lands on the neighbouring staff)

**Configuration.** Covered in full in §A.7. Restated here for the register's
completeness: a stem whose notehead sits on staff N terminates (at a beam) in
staff N+1's territory — the far end of the "stem" is not free-floating ink at
all but is anchored to a beam belonging to the other staff.

- **How far apart from a genuinely adjacent stem on staff N+1**: not
  applicable in the same sense — this is not two stems meeting, it is ONE
  stem crossing the gap. The discriminator from "two separate stems, one per
  staff, that happen to be vertically aligned and close" is: a cross-staff
  stem's far end terminates at a BEAM (horizontal ink), not at another
  notehead or in free space; two independent staves' stems terminating near
  each other without a connecting beam are NOT a cross-staff case, and should
  be read as coincidental adjacency, not a single mark.
- **Tag**: HARD as a description; near-zero expected reach on orchestral
  full-score plates of the kind this project reads (§A.7).
- **What could be measured**: reach-first, expected near-zero — described,
  not run.

### B.6 — Consecutive notes in a dense passage (same voice, no shared mark)

**Configuration.** Not a "two stems meeting" case in the engraving sense at
all — two SUCCESSIVE notes of the SAME voice, in a dense passage, whose stems
sit close together purely because the notes are close together in time and
the passage is tightly spaced. This is the negative case the register needs
to state explicitly, because it is what a false positive looks like.

- **How far apart**: bounded below by ordinary note spacing, which this
  project has already measured indirectly — *An engraver spaces notes roughly
  in PROPORTION TO DURATION* (registry, Score layout & systems) and the
  already-measured *"a bar's first note sits 2.0–2.5 staff spaces past the
  barline"* (registry, Slurs section, `[confirms nothing new, cross-reference
  only]`) both establish that this project already has SOME notion of typical
  intra-bar note spacing on its own plates. Two consecutive same-voice stems
  should never be genuinely touching except at extreme densities (fast
  passages, small noteheads) — and even then, they belong to the SAME voice,
  so BOTH point the SAME direction (§A.1's rigid rule), which is the cheapest
  possible discriminator from every case in B.1–B.4 (all of which require
  opposite-direction stems, except B.6 itself, where same-direction stems
  simply being close together is expected and unremarkable).
- **Tag**: HARD that same-voice consecutive stems share one direction; the
  distance at which they can visually crowd is PREFERENCE/density-dependent
  and this project already has instrumentation to measure it directly (bar
  spacing, `events_per_space`, cited in the registry's cross-staff-column
  entry, `[C64]`) — described, not run, but the instrument already exists.

---

## C. Grading summary

One row per distinguishable claim in this document. `Measurable on a scan`
states concretely what would have to be computed, or says plainly that the
claim is engraving-only (a writing-time decision with no reading-side
signature).

| # | claim | tag | measurable on a scan? |
|---|---|---|---|
| A.1 | Stem side (right-up/left-down) has no further exception beyond the seconds case already in the registry | HARD | Already measured (`[C9]`) |
| A.2-a | Two/more independent voices override plain position for direction | HARD (within divided writing) | Needs a two-voice detector — this project has one wired for events (`Q.VOICES`), unmeasured for this specific claim |
| A.2-b | Voice crossing keeps the VOICE's direction, not the note's | HARD (inferred) | Yes — cross-reference bar-level pitch order against assigned voice direction |
| A.2-c | "Reverse stem" for cross-staff notation | STRONG TENDENCY | Only relevant if A.7 reach is non-zero |
| A.2-d | Down-stems-only / up-stems-only editions | PREFERENCE | No per-note test; a whole-part statistic only |
| A.2-e | Chord straddling the middle line takes direction from the majority/extreme side | HARD | Yes — already-gathered `Q.EVENT` chord membership + staff positions |
| A.3 | Chord stem length reaches the furthest notehead | HARD | Yes — described in §A.3 |
| A.4 | Seconds straddle the stem; 3+ clusters alternate | HARD (pair) / STRONG TENDENCY (cluster) | Yes for the pair case — described in §A.4 |
| A.5-a | 1 ledger line ≠ "reaches the middle line"; 2+ does | HARD (threshold, restated from literature) | Yes — described in §A.5 |
| A.5-b | Double-stemmed outside-staff stems are progressively SHORTENED, not both reaching the middle line | STRONG TENDENCY | Yes — directly testable, and is the key mechanism behind §B |
| A.6-a | Divisi as two voices vs. one chord | STRONG TENDENCY / PREFERENCE | Partially — voice-count already gathered |
| A.6-b | Unison as ONE head, TWO stems | HARD (shape) | **Yes — the sharpest test in this document, §B.4** |
| A.7 | Cross-staff beaming exists as a convention; near-zero expected reach here | HARD (exists) / near-zero reach (orchestral) | Yes, reach-first |
| A.8 | Grace notes: scaled stem, 2–2.5 sp default, slash for acciaccatura | HARD (shape) / weakly-sourced (length number) | Yes, reusing the existing grace-size veto |
| A.9 | Tremolo: 1 stroke may cross a line, 2+ must clear by 1 sp | HARD (number), **unverified against primary source** | Blocked on a detection gap (zero tremolo detections currently) |
| A.10-a | `note-collision-threshold = 1` staff space (software default) | STRONG TENDENCY (software); unestablished for hand engraving | Yes — directly testable against any two-voice bar |
| A.10-b | Shift step ≈ 0.5–0.7 sp | STRONG TENDENCY | Yes |
| A.10-c | Stems shortened, not merely notes shifted, to avoid two-voice collision near the middle line | STRONG TENDENCY, **not independently re-numbered here** | Yes — §B.1's proposed test |
| B.1 | Two voices near the middle line: stems shortened toward each other, not colliding | STRONG TENDENCY | Yes — proposed test given |
| B.2 | Voice crossing: stems may genuinely converge past each other, weaker shortening evidence | STRONG TENDENCY | Yes — proposed test given |
| B.3 | Cross-voice second: notehead offset ≈0.5–0.7 sp, stems NOT collinear | **HARD** (mechanism), corroborated by this project's own `[C14]` finding | **Yes — already partially measured by accident (`[C14]`)** |
| B.4 | Unison double stem: one head at the MIDPOINT of the ink run, not at either end; direction-reversal at the head; roughly symmetric total length ≈2× normal | **HARD** (shape) | **Yes — cheapest and most concrete test in the whole document** |
| B.5 | Cross-staff stem terminates at a beam, not free space | HARD | Yes, reach-first, near-zero expected |
| B.6 | Same-voice consecutive stems: always same direction, crowding is a density fact this project can already measure | HARD (direction) / instrumented already (crowding) | Yes |

---

## D. What is not established

Listed plainly, per house discipline (`docs/ask-first-conventions.md` §3: *"a
convention is a hypothesis and a cheap test, never a licence"*).

1. **Every single claim in this document is LITERATURE ONLY or inferred from
   literature — NONE of it has been measured on this project's own plates.**
   Read this document as a set of hypotheses and proposed cheap tests, not as
   ground truth. Several claims (B.1's clearance number, B.2's crossing
   clearance, A.4's cluster-alternation mechanism, A.9's tremolo clearance)
   could not be traced to a page number or primary quotation in this pass and
   are marked accordingly — they came back only as secondary paraphrase in web
   search results, never as a verified direct quotation from Gould's text
   itself. **These four should be treated as the weakest entries in the
   document and re-verified against a physical or scanned copy of *Behind
   Bars* before anything is built on them.**
2. **Ted Ross, *The Art of Music Engraving and Processing*, could not be
   searched at all** — it has no indexed searchable text online (out of print,
   available secondhand or via a CD-ROM edition, and via the Internet Archive
   as a borrow-only scan). Every place this document would expect Ross to
   corroborate or diverge from Gould (Ross predates Gould and is the source
   Gould herself is said to summarize, per the registry's own note at
   disagreement #5) is a genuine gap, not a checked absence.
3. **The single most important unestablished number is B.1's clearance
   distance** — how close, in staff spaces, two independent voices' shortened
   stems are allowed to come to each other before an engraver would consider
   it a collision worth avoiding differently. Every other number in the
   register (B.3's ~0.5–0.7 sp offset, LilyPond's 1 sp collision threshold) is
   a SOFTWARE default, not a hand-engraving measurement, and this repertoire
   is hand-engraved 19th-century plate, not software output — the registry's
   own standing warning applies at full force: *"Nothing in the literature is
   about SCANS,"* and nothing found here is about HAND ENGRAVING specifically
   either, only about software that MODELS hand engraving.
4. **A.4's cluster-of-3+-seconds alternation rule** is stated only in the
   registry's existing `[L19]` entry's "Known exceptions" line, and this pass
   could not independently re-find or numerically strengthen it. It is
   repeated here rather than re-derived.
5. **A.6/B.4's divisi-as-chord vs. divisi-as-two-voices split** is sourced to
   general orchestration-pedagogy discussion rather than to Gould, Ross, or
   SMuFL directly, and carries no measured frequency for either choice in
   19th-century German orchestral plates specifically — this is squarely the
   kind of publisher/era variation the registry's own §A.10 discipline says
   must never be asserted without a source per document.
6. **A.7's cross-staff-beaming "near-zero expected reach" claim is a
   prediction, not a measurement.** It should be treated exactly as
   `docs/ask-first-conventions.md` instructs — as the thing to ask Sean before
   building anything for it, not as license to skip building a reader for it.
7. **Nothing in this document was checked against this project's own scanned
   plates in any way** — every "what could be measured" note describes an
   instrument that already exists in this repository (per the citations
   given) but was not run in the course of writing this document. The
   HAND-ENGRAVED-vs-SOFTWARE gap named in point 3 is exactly the kind of gap
   only a real measurement against Litolff/Breitkopf/Simrock/Peters plates can
   close.
8. **Flag directly to Sean**: B.1's clearance number and B.4's unison
   double-stem discriminator are the two entries most worth a direct question
   before any code is written — B.1 because it is the number the whole "two
   stems misread as one" bug most needs and this pass could not source it
   numerically; B.4 because it reframes a chunk of this project's own
   unresolved dedupe residue (the same-cell repeated-pitch population) as
   possibly containing CORRECT unison marks rather than only detection
   duplicates, which changes the shape of that unfinished repair.
