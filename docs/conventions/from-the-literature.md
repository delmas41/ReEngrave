# Engraving conventions, from the literature

**What this is.** Conventions that the engraving literature, the font/format
specifications and the professional preparation guidelines state — collected so
that a reader (human or agent) can consult them *before* building a mechanism.
It is the complementary half of `from-this-repo.md`, which harvests what this
project has already MEASURED. **Nothing here has been measured by this project.**
Every entry is a LEAD until someone prices it.

**The filter applied.** This is for a machine READING a printed page, not for
setting one. Entries were kept where the convention is RIGID and yields a
geometric or positional constraint — *this ink can only be here, at this size,
on this side*. Taste, spacing aesthetics and house style were dropped unless
they bound a measurement.

---

## Status

| | count |
|---|--:|
| **Total entries** | **79** |
| Sourced (a source consulted in this session) | 75 |
| `UNSOURCED — believed true, not verified` | 4 |

**Entries per category**

| category | entries |
|---|--:|
| Staff & pitch geometry | 9 |
| Stems & beams | 14 |
| Rests & bar filling | 8 |
| Accidentals & key signatures | 8 |
| Time signatures & meter | 7 |
| Slurs, ties & phrasing | 6 |
| Dynamics & hairpins | 5 |
| Articulations & ornaments | 5 |
| Score layout & systems | 7 |
| Text & margin labels | 4 |
| Barlines & repeats | 6 |

---

## ⚠️ What could not be found or verified

**Gould, *Behind Bars*, is quoted only from the publisher's free sample.** The
book itself is not on this machine. What was consulted is
`behindbarsnotation.co.uk/contents/sample_pages.pdf` — pages **14, 15, 22, 29,
152, 153, 284, 404–405, 557–558, 566–567** — which is genuine typeset text and
gives real page numbers. **Every Gould citation below carries a page number from
that sample and nothing else.** Where the book certainly covers a convention but
the sample does not print it, the entry is marked `UNSOURCED` rather than given
a plausible-looking page number. That was the single largest constraint on this
document.

**Ted Ross, Gardner Read and Kurt Stone were NOT consulted.** None is online in
a form that could be read this session; each is a print monograph. Several
conventions here are attributed to them in secondary sources, and LilyPond's own
source comments cite Ross and "Roush & Gourlay" by name for stem shortening —
that comment is quoted, but the primary text was not read.

**The Gradus knowledge base yielded nothing on engraving, as forewarned.** Three
queries were run (`music engraving`, `stem direction notation rules`, and a
notation-conventions probe); the tool ran fine (pgvector / Voyage 3 Large, 10
chunks each). Top hits were Rameau's 1779 *Treatise*, a Renaissance part-book
chapter on white notation, and a Ludwin orchestration chunk tagged
`engraving,accidentals` about part preparation. **No source in it states a
geometric engraving rule.** It is a counterpoint and harmony base and should not
be queried for this again.

**Numeric defaults are FONT and APPLICATION defaults, not laws.** The Bravura
figures are what one reference SMuFL font recommends. Scoring Notes' survey of
Finale / Sibelius / Dorico / MuseScore shows staff-line thickness ranging
**0.08–0.16 staff spaces** across shipping applications — a factor of two. Treat
every number below as *the centre of a band*, never as a threshold, and expect
19th-century plates to sit outside the band entirely.

**Nothing here is about SCANS.** Every source describes ink as an engraver
intends it. Degradation, warp, bleed and broken lines are outside all of it.

---

## Sources consulted in this session

| tag | what |
|---|---|
| **Gould** | Elaine Gould, *Behind Bars: The Definitive Guide to Music Notation* (Faber, 2011) — publisher's free sample pages, `behindbarsnotation.co.uk/contents/sample_pages.pdf`, text extracted with `pdftotext -layout`. Page numbers as printed. |
| **SMuFL** | Standard Music Font Layout specification, latest, at `smufl.formats.music` (the `w3c.github.io/smufl` URLs now 301 there) — `specification/engravingdefaults.html` and `specification/scoring-metrics-glyph-registration.html`. |
| **Bravura** | `Bravura.json` v1.482, the reference SMuFL font's metadata, from `raw.githubusercontent.com/steinbergmedia/bravura/master/redist/Bravura.json` — downloaded and parsed directly, so `engravingDefaults`, `glyphBBoxes` and `glyphsWithAnchors` numbers below are read off the file, not quoted from prose. All values are in staff spaces. |
| **MOLA** | Major Orchestra Librarians' Association, *Guidelines for Music Preparation* (2017 rev.), `mola-inc.s3.eu-west-1.amazonaws.com/files/mola3/MOLA-Guidelines-for-Music-Preparation.pdf`, full text extracted. |
| **LilyPond** | GNU LilyPond 2.24.4 installed on this machine; `scm/lily/define-grobs.scm` read directly at `/opt/homebrew/Cellar/lilypond/2.24.4/share/lilypond/2.24.4/`. Line numbers given. |
| **Dorico** | Steinberg Dorico documentation, `archive.steinberg.help` — slur and articulation placement pages. |
| **Scoring Notes** | `scoringnotes.com/tips/spaces-and-the-units-of-measurement-for-music-notation/` — cross-application defaults. |
| **IU** | Indiana University Jacobs School of Music, Composition Department *Music Notation Style Guide*, `blogs.iu.edu/jsomcomposition/music-notation-style-guide/`. |
| **Wikipedia** | Articles consulted: *Accidental (music)*, *Key signature*, *Tie (music)*, *Stem (music)*, *Ledger line*, *Clef*, *Bar (music)*, *Dotted note*, *Rest (music)*. Used for the basic geometric conventions only. |

---

## Table of contents

- [Staff & pitch geometry](#staff--pitch-geometry) — 9
- [Stems & beams](#stems--beams) — 14
- [Rests & bar filling](#rests--bar-filling) — 8
- [Accidentals & key signatures](#accidentals--key-signatures) — 8
- [Time signatures & meter](#time-signatures--meter) — 7
- [Slurs, ties & phrasing](#slurs-ties--phrasing) — 6
- [Dynamics & hairpins](#dynamics--hairpins) — 5
- [Articulations & ornaments](#articulations--ornaments) — 5
- [Score layout & systems](#score-layout--systems) — 7
- [Text & margin labels](#text--margin-labels) — 4
- [Barlines & repeats](#barlines--repeats) — 6

---

## Staff & pitch geometry

### The staff space is the unit of everything
- **Says:** Every dimension in engraving is expressed as a fraction of the distance between two adjacent staff lines, so a page's absolute size carries no information a reader needs.
- **Category:** Staff & pitch geometry
- **Predicts (mechanically):** Measure the staff spacing once per staff and express every other measurement in it. Any constant in page pixels is a constant about one scan; any constant in staff spaces is a constant about engraving. This also means a reader must recover staff spacing BEFORE it can apply any other entry in this document.
- **Numbers:** SMuFL: "if a font uses 1000 upm (design units per em), as is conventional for a PostScript font, one staff space is equal to 250 design units" — i.e. **1 em = 4 staff spaces**, the height of a five-line staff.
- **Source:** SMuFL, *Metrics and glyph registration for scoring applications*.
- **Rigid or variable:** Rigid as a convention of measurement. The absolute mm value is entirely variable (see the staff-size entry).
- **Would be falsified by:** A body of engraving whose symbol proportions track page size rather than staff spacing.
- **Known exceptions:** None recorded.

### A glyph's baseline sits at the staff position it names
- **Says:** A notation glyph that belongs to a vertical staff position is drawn so that the font baseline lies exactly at that position.
- **Category:** Staff & pitch geometry
- **Predicts (mechanically):** For a notehead or an accidental, the glyph's vertical CENTRE is the pitch. For a clef, the pitch the clef names is at the baseline. For a rest, the baseline is its default staff position. So the y a reader should extract differs per family, and taking a bounding-box centre for everything is wrong for at least clefs, flags, whole rests and the flat sign.
- **Numbers:** SMuFL: "Glyphs for movable notations that apply to some vertical staff position shall be registered such that the font baseline lies exactly at that position." Horizontally: "Unless otherwise stated, all glyphs shall be horizontally registered so that their leftmost point coincides with x = 0."
- **Source:** SMuFL, *Metrics and glyph registration for scoring applications*.
- **Rigid or variable:** Rigid within SMuFL-conformant fonts; it is a description of how engravers have always placed these glyphs, so it should hold on plates too.
- **Would be falsified by:** A font or plate where a notehead's ink is systematically offset from the staff position it sounds.
- **Known exceptions:** The whole rest, which hangs from the baseline rather than centring on it — see that entry.

### A notehead is exactly one staff space tall
- **Says:** Black and half noteheads occupy precisely one staff space vertically, centred on their pitch.
- **Category:** Staff & pitch geometry
- **Predicts (mechanically):** A detection claiming to be a notehead whose height is far from one staff space is a misread. Measured in Bravura, black and half noteheads are 1.180 × 1.000 staff spaces, bbox SW `[0.0, −0.5]`, NE `[1.18, 0.5]` — an aspect of **1.18 : 1**, i.e. very nearly square and slightly wider than tall.
- **Numbers:** `noteheadBlack` and `noteheadHalf`: w **1.180**, h **1.000**. `noteheadWhole`: w **1.688**, h **1.000**. `noteheadDoubleWhole`: w **2.396**, h **1.240**.
- **Source:** Bravura `glyphBBoxes`.
- **Rigid or variable:** The one-space height is rigid across all traditions. The WIDTH varies a little by font and a lot by era of plate.
- **Would be falsified by:** A plate whose noteheads are consistently taller or shorter than a staff space.
- **Known exceptions:** Grace and cue noteheads are drawn small; the double-whole (breve) is taller because of its flanking strokes.

### A whole notehead is wider than a black one, and the same height
- **Says:** The semibreve head is drawn wider than a crotchet/minim head, but occupies the same single staff space.
- **Category:** Staff & pitch geometry
- **Predicts (mechanically):** Width, not height, separates a whole note from a half note; **1.688 vs 1.180 staff spaces is a 43% difference and is measurable**. Height cannot separate them at all. A reader distinguishing hollow heads should use width and the presence of a stem, never height.
- **Numbers:** `noteheadWhole` 1.688 sp wide; `noteheadHalf` 1.180 sp wide. Same height, 1.000.
- **Source:** Bravura `glyphBBoxes`.
- **Rigid or variable:** Rigid in direction; the exact ratio varies by font.
- **Would be falsified by:** A plate where whole and half heads measure the same width.
- **Known exceptions:** None recorded.

### A ledger line is drawn at the staff's own spacing, slightly longer than the notehead
- **Says:** Ledger lines continue the staff's ruling above or below it, at the same spacing, each one slightly longer than the head it carries.
- **Category:** Staff & pitch geometry
- **Predicts (mechanically):** Ledger rungs are PREDICTABLE in y from the staff's own line positions — they are not free-floating ink — and they overhang the notehead by a small, bounded amount on each side, so a rung is always a short horizontal run centred on a notehead's x. A run much longer than a notehead's width plus twice the extension is not a ledger line.
- **Numbers:** Wikipedia: "A line slightly longer than the note head is drawn parallel to the staff, above or below, spaced at the same distance as the lines within the staff." Bravura `legerLineExtension` = **0.4** staff spaces beyond the notehead **on each side**. LilyPond expresses the same thing as a fraction of head width: `LedgerLineSpanner` `length-fraction` = **0.25**, `minimum-length-fraction` = **0.25** (`define-grobs.scm:1909`).
- **Source:** Wikipedia, *Ledger line*; Bravura `engravingDefaults`; LilyPond 2.24.4 `scm/lily/define-grobs.scm:1906–1910`.
- **Rigid or variable:** The spacing is rigid. The extension is variable — Bravura states it absolutely (0.4 sp), LilyPond proportionally (0.25 × head width ≈ 0.30 sp) — so expect roughly 0.3–0.4 sp and do not thread a threshold between them.
- **Would be falsified by:** Ledger rungs whose pitch does not continue the staff's own spacing.
- **Known exceptions:** None recorded for the geometry. Usage is limited by taste — "notes that use at least four ledger lines make music more difficult to read" (Wikipedia) — so a long ladder is rarer than a short one.

### A ledger line is thicker than a staff line
- **Says:** Ledger lines are drawn somewhat heavier than the staff's own lines.
- **Category:** Staff & pitch geometry
- **Predicts (mechanically):** In a staff-line-erased image, ledger rungs should SURVIVE an erasure tuned to the staff lines, because they are heavier. A reader that erases at the staff-line weight and loses its ledger rungs has over-erased.
- **Numbers:** SMuFL defines `legerLineThickness` as "the thickness of a leger line (normally somewhat thicker than a staff line)". Bravura: `legerLineThickness` **0.16** vs `staffLineThickness` **0.13** — about **23% heavier**.
- **Source:** SMuFL, *engravingDefaults*; Bravura `engravingDefaults`.
- **Rigid or variable:** Variable in magnitude, consistent in direction. 23% is not a large margin and may not survive a low-resolution bitonal scan.
- **Would be falsified by:** A plate whose ledger rungs measure thinner than its staff lines.
- **Known exceptions:** None recorded.

### Staff line thickness is around an eighth of a staff space, and applications disagree by 2×
- **Says:** A staff line is thin relative to the space it bounds.
- **Category:** Staff & pitch geometry
- **Predicts (mechanically):** Bounds what a staff-line detector should accept as a line: a horizontal run around 0.1 staff spaces thick. It also bounds what STAFF RESIDUE after erasure can look like. The 2× spread across applications means a fixed thickness constant is fitted to whichever engraver you measured.
- **Numbers:** Bravura `staffLineThickness` **0.13**. Application defaults, from Scoring Notes: Finale **0.12**, Sibelius **0.1**, Dorico **0.16**, MuseScore **0.08** — a range of **0.08–0.16 staff spaces**.
- **Source:** Bravura `engravingDefaults`; Scoring Notes, *Spaces and the units of measurement for music notation*.
- **Rigid or variable:** **Variable, and this entry exists to say how variable.** Publisher and era will widen the band further.
- **Would be falsified by:** Nothing — it is already a measured spread; the useful form is the band, not a value.
- **Known exceptions:** None recorded.

### A staff is 4–8.5 mm tall, and the score end is the small end
- **Says:** Conductor's scores are set much smaller than parts; there are professional floors below which each is considered illegible.
- **Category:** Staff & pitch geometry
- **Predicts (mechanically):** Converts a rendering DPI into an expected staff-space size in pixels, which bounds every other measurement. A conductor's score at the 4 mm floor rendered at 300 dpi gives a staff space of about **11.8 px**; a part at 7.5 mm gives about **22 px**. **An orchestral score is at the hard end of this range by construction.**
- **Numbers:** MOLA: "The minimum legible staff size for scores is 4 mm (measured from the bottom to the top of each staff)"; "The most readable staff size for all instruments is 7.5 mm … Anything smaller than 7.0 mm is unacceptable, and anything larger than 8.5 mm should be avoided." Gould, p.557: "An ideal stave size in good lighting conditions is 6.7 mm", with 7 mm recommended where two players share a copy. IU: parts minimum 7.0–7.5 mm, scores minimum 4 mm.
- **Source:** MOLA, *Formatting*; Gould p.557 (*Performance conditions*); IU, *Page Layout*.
- **Rigid or variable:** Variable, and these are modern professional floors. 19th-century plates predate all of them.
- **Would be falsified by:** A held edition whose staves measure outside 4–9 mm.
- **Known exceptions:** Miniature/study scores go well below 4 mm.

### The first line of each movement is indented
- **Says:** A movement's opening system is set in from the left margin relative to the systems that follow it.
- **Category:** Staff & pitch geometry
- **Predicts (mechanically):** A system whose left edge is to the RIGHT of the page's other systems is a candidate movement START — an independent structural signal that needs no reading of the music. Conversely, a page whose systems are indented differently is not necessarily mis-segmented: it may print a movement boundary.
- **Numbers:** None given.
- **Source:** MOLA, *Formatting*: "The first line of each movement should be indented."
- **Rigid or variable:** Widely followed, and MOLA states it as a requirement; the AMOUNT is house style.
- **Would be falsified by:** Editions whose movement openings are flush with every other system.
- **Known exceptions:** The indent also accommodates the instrument-name block on a score's first system, so on a full score an indent can mean *first page* rather than *new movement*.

---

## Stems & beams

### A stem attaches on the right going up and on the left going down
- **Says:** An up-stem rises from the right-hand side of the notehead; a down-stem falls from the left-hand side.
- **Category:** Stems & beams
- **Predicts (mechanically):** Given a notehead box and a stem, the SIDE the stem sits on determines the stem direction with no need to measure which end is longer. Conversely, given a stem direction, the notehead is on a known side of the stem — which is how to associate a stem with its head rather than with a neighbour's. In Bravura the attachment points are explicit anchors: `stemUpSE` = `[1.18, 0.168]` (the head's right edge) and `stemDownNW` = `[0.0, −0.168]` (its left edge).
- **Numbers:** Attachment is at **x = 0 or x = notehead width**, and **y = ∓0.168 staff spaces** from the pitch centre — i.e. the stem meets the head just off its vertical middle, not at the extreme corner.
- **Source:** Wikipedia, *Stem (music)*: "If the stem points up from a notehead, the stem originates from the right-hand side of the note, but if it points down, it originates from the left." Bravura `glyphsWithAnchors` for `noteheadBlack` / `noteheadHalf`.
- **Rigid or variable:** Rigid. This is one of the most reliable conventions in all of notation.
- **Would be falsified by:** A plate with up-stems on the left of their heads.
- **Known exceptions:** Double-stemmed writing (one head carrying both an up- and a down-stem) puts stems on both sides; a chord containing a second puts one of the two heads on the wrong side of the stem (see that entry).

### A stem is one octave long — 3.5 staff spaces
- **Says:** The default stem reaches an octave from its notehead.
- **Category:** Stems & beams
- **Predicts (mechanically):** A near-vertical run of ink about 3.5 staff spaces long, starting at a notehead's left or right edge, is a stem. It also gives the expected position of the FLAG or BEAM: about 3.5 staff spaces from the head centre. A candidate stem far from this length needs one of the named exceptions to explain it.
- **Numbers:** Gould p.14: "The standard length of a stem is one octave (i.e. 3½ stave-spaces) from the centre of the notehead". LilyPond agrees and annotates the difference in reference point: `(lengths . (3.5 3.5 3.5 4.25 5.0 6.0 7.0 8.0 9.0))` with the comment "3.5 (or 3 measured from note head) is standard length" — the longer values are for 32nd notes and shorter, which need room for more flags.
- **Source:** Gould p.14 (*Stem length*); LilyPond 2.24.4 `scm/lily/define-grobs.scm:3118`.
- **Rigid or variable:** Rigid as a default; systematically modified by the three entries that follow.
- **Would be falsified by:** A plate whose in-staff stems cluster at a length other than ~3.5 sp.
- **Known exceptions:** Beamed notes (LilyPond `beamed-lengths . (3.26 3.5 3.6)`); notes far outside the staff; heavily flagged notes, which are longer.

### A stem on ledger lines reaches the middle staff line
- **Says:** For a note more than one ledger line outside the staff, the stem is drawn long enough to reach the staff's middle line.
- **Category:** Stems & beams
- **Predicts (mechanically):** A very long stem is not an error — it is positive evidence that its notehead is **two or more ledger lines outside the staff**, and it PREDICTS that the far end of the stem terminates at the middle line rather than at a free height. So a stem whose far end lands on the middle line constrains its head's pitch from the other direction, and gives a cheap check on a ledger-note pitch reading.
- **Numbers:** None beyond "to the middle stave-line".
- **Source:** Gould p.14 (*notes on ledger lines*): "Stems for notes on more than one ledger line extend to the middle stave-line". Corroborated by Wikipedia, *Stem (music)*.
- **Rigid or variable:** Rigid and long-standing.
- **Would be falsified by:** Ledger-note stems of standard 3.5 sp length, leaving a gap before the staff.
- **Known exceptions:** Gould notes that in double-stemmed writing stems outside the staff are progressively shortened instead (p.15).

### A stem is never shorter than 2.5 staff spaces
- **Says:** As stems fall further outside the staff they are progressively shortened, and there is a hard floor of a sixth.
- **Category:** Stems & beams
- **Predicts (mechanically):** A floor on stem length: no candidate shorter than **2.5 staff spaces** is a stem. Useful as a rejection rule, and it bounds how short a stem can be when several beams have to be accommodated.
- **Numbers:** Gould p.14: "The shortest stem length is a sixth (2½ stave-spaces): no stem should ever be shorter than this." LilyPond encodes the shortening as `(stem-shorten . (1.0 0.5 0.25))` — a forced-direction stem is shortened by **one staff space**, a flagged stem by half — with the source comment "Stems in unnatural (forced) direction should be shortened by one staff space, according to [Roush & Gourlay]."
- **Source:** Gould p.14 (*double-stemmed writing*); LilyPond 2.24.4 `scm/lily/define-grobs.scm:3136–3138`.
- **Rigid or variable:** Gould states it as absolute. LilyPond's shortening amounts are its own defaults.
- **Would be falsified by:** Engraved stems measuring under 2.5 sp.
- **Known exceptions:** Grace notes and cue-size notation are scaled down as a whole.

### A stem is about a tenth of a staff space thick
- **Says:** Stems are thin — thinner than a beam by roughly 4×, and comparable to a staff line.
- **Category:** Stems & beams
- **Predicts (mechanically):** Bounds the width of a vertical-run detector's target, and distinguishes a stem from a THIN BARLINE only weakly: Bravura's `stemThickness` 0.12 and `thinBarlineThickness` 0.16 are close, so **thickness alone cannot separate a stem from a barline** — height and position must.
- **Numbers:** Bravura `stemThickness` **0.12**. Application defaults: Finale 0.12, Sibelius 0.1, Dorico 0.16, MuseScore 0.13 — range **0.10–0.16**.
- **Source:** Bravura `engravingDefaults`; Scoring Notes, *Spaces and the units of measurement*.
- **Rigid or variable:** Variable within a narrow band.
- **Would be falsified by:** Engraved stems measurably thicker than barlines.
- **Known exceptions:** None recorded.

### Where there is no case for either direction, the stem goes DOWN
- **Says:** The convention for an undetermined stem direction is down.
- **Category:** Stems & beams
- **Predicts (mechanically):** A prior with a known direction. A reader guessing a stem direction from weak evidence should guess DOWN, not up, and a system where ambiguous cases resolve upward is mis-calibrated.
- **Numbers:** None.
- **Source:** Gould p.14: "When there is no clear-cut case for either direction, the convention is to use a down-stem. Some editions use down-stems exclusively." LilyPond encodes the same as `Stem` `(neutral-direction . ,DOWN)` (`define-grobs.scm:3148`).
- **Rigid or variable:** **Variable by edition and by genre, and Gould says so in the same breath.** She records that some editions use down-stems exclusively, and that "Some editions of vocal music use up-stems only, to allow the text to be placed close to the stave."
- **Would be falsified by:** Nothing — the exceptions are stated with the rule.
- **Known exceptions:** Vocal music set with up-stems throughout; editions that use down-stems exclusively.

### A note at or above the middle line takes a down-stem
- **Says:** In single-voice writing, stem direction is decided by the note's position relative to the staff's middle line.
- **Category:** Stems & beams
- **Predicts (mechanically):** Gives an EXPECTED stem direction from a notehead's staff position alone, with no ink. A detected stem contradicting it is either a multi-voice bar, a beamed group whose average pulls the other way, or a misread — and each is a distinguishable hypothesis rather than noise.
- **Numbers:** None.
- **Source:** Wikipedia, *Stem (music)*: within a single voice, stems point downward for notes at or above the middle line and upward for those below; for beamed notes the direction follows "the average position of the lowest and highest notes".
- **Rigid or variable:** Rigid within single-voice writing, and **completely overridden** by multi-voice writing (next entry).
- **Would be falsified by:** Single-voice engraving that ignores the middle line.
- **Known exceptions:** Multi-voice bars; beamed groups, where the group decides; forced directions.

### Two voices on one staff: upper voice up, lower voice down, regardless of position
- **Says:** Where two voices share a staff, the upper voice takes up-stems and the lower takes down-stems, and the middle-line rule is suspended.
- **Category:** Stems & beams
- **Predicts (mechanically):** **Stem direction becomes a VOICE label rather than a position consequence.** A bar containing both up- and down-stemmed notes at positions the middle-line rule cannot explain is a two-voice bar — which is a cheap, ink-level detector for divisi and for the `<backup>` an exporter must write. It also predicts that within such a bar every up-stemmed note is higher than or equal to its simultaneous down-stemmed note.
- **Numbers:** None.
- **Source:** Wikipedia, *Stem (music)* ("Different stem directions serve to distinguish separate voices in polyphonic music written on the same staff") and corroborating notation references consulted via search: "When two voices share one staff, the top part always stems up and the bottom part always stems down — the middle-line rule steps aside."
- **Rigid or variable:** Rigid where two voices genuinely share a staff.
- **Would be falsified by:** A two-voice bar whose voices are not separated by stem direction.
- **Known exceptions:** Unisons, where both voices may share one head; more than two voices, where the convention runs out.

### Stem direction is held constant through a beat or half-bar
- **Says:** Where stem direction would otherwise vary inside a bar, notes belonging to the same beat or half-bar keep one direction.
- **Category:** Stems & beams
- **Predicts (mechanically):** Stem direction is a piecewise-constant function over METRICAL units, not a per-note function. So a run of same-direction stems is evidence of a beat grouping, and a direction change inside a bar marks a beat or half-bar boundary — a metrical signal read off geometry with no duration reading at all.
- **Numbers:** None.
- **Source:** Gould p.14: "When the stem direction varies within a bar, maintain the stem direction of the notes that are part of the same beat or half-bar".
- **Rigid or variable:** Stated by Gould as the convention; strength varies by edition.
- **Would be falsified by:** Bars whose stem directions alternate note-by-note under the middle-line rule.
- **Known exceptions:** Multi-voice bars, where voice decides.

### In a chord containing a second, the two heads straddle the stem
- **Says:** Where two chord notes are a second apart, they cannot share a side: the higher goes right of the stem and the lower left.
- **Category:** Stems & beams
- **Predicts (mechanically):** **Two noteheads at adjacent staff positions, horizontally offset by about one notehead width, sharing one stem, are ONE chord — not two events and not a duplicate detection.** This is the printed signature of a chordal second and it is the case most likely to be misread as a spurious doubled note.
- **Numbers:** The offset is one notehead width, **1.18 staff spaces** in Bravura.
- **Source:** Wikipedia, *Stem (music)*: "the stem runs between the two notes with the higher being placed on the right of the stem and the lower on the left." Bravura carries dedicated anchors for this case (`splitStemUpSE`, `splitStemDownNW`, etc.).
- **Rigid or variable:** Rigid.
- **Would be falsified by:** Engraved chordal seconds drawn with both heads on one side.
- **Known exceptions:** Clusters of three or more adjacent notes, where Wikipedia records that "middle notes appear on the opposite side".

### A beam is half a staff space thick, with a quarter-space gap between beams
- **Says:** Beams are heavy horizontal strokes, separated by a gap narrower than the stroke itself.
- **Category:** Stems & beams
- **Predicts (mechanically):** **Gives the expected PITCH of a beam stack, which is what a beam-counting reader actually needs**: successive beams repeat every `beamThickness + beamSpacing` = **0.75 staff spaces**. A stack of N beams spans about `0.5 + 0.75(N−1)` staff spaces. It also says the gap is NARROWER than the stroke, so an erosion tuned to open the gaps will eat the strokes first.
- **Numbers:** Bravura `beamThickness` **0.5**, `beamSpacing` **0.25** — SMuFL defines the latter as "the distance between the inner edge of the primary and outer edge of subsequent secondary beams". LilyPond `Beam` `(beam-thickness . 0.48) ; in staff-space` (`define-grobs.scm:439`).
- **Source:** Bravura `engravingDefaults`; SMuFL *engravingDefaults*; LilyPond 2.24.4 `scm/lily/define-grobs.scm:439`.
- **Rigid or variable:** Narrow band across fonts; plates vary more.
- **Would be falsified by:** A plate whose beam pitch is not ~0.75 sp.
- **Known exceptions:** None recorded.

### A beam is angled by the OUTER interval, and is horizontal in three named cases
- **Says:** The beam's slope follows the interval between the first and last notes of the group, not the group's most extreme interval, and is flat in three specific situations.
- **Category:** Stems & beams
- **Predicts (mechanically):** **The beam's slope PREDICTS the pitch relation of the group's outer notes, independently of reading either notehead** — a rising beam means the last note is higher than the first. And a horizontal beam is positive evidence for one of three shapes: the group begins and ends on the same note; the pitches repeat a pattern; or an inner note is closer to the beam than either outer note (a concave group). That is a cross-check on a pitch reading using only the beam's geometry.
- **Numbers:** None given for the angle. LilyPond caps slope damping at `(damping . 1)` and uses `auto-knee-gap . 5.5` staff spaces as the interval at which it breaks a group into a knee (`define-grobs.scm:437`).
- **Source:** Gould p.22 (*Direction of beam angle*, *multi-directional beamed group*).
- **Rigid or variable:** Rigid as a principle; the magnitude of the slope is house style, and Gould separately advises avoiding deviation from horizontal where possible (p.29, of octave signs).
- **Would be falsified by:** Engraved groups whose beam slope tracks the inner extreme rather than the outer notes.
- **Known exceptions:** The three horizontal cases are the exceptions, and they are enumerated.

### Beaming follows the metre, and never crosses the middle of the bar
- **Says:** Divisions of a beat are beamed together to make beats legible, and notes are not beamed across the bar's midpoint.
- **Category:** Stems & beams
- **Predicts (mechanically):** **A beam group is a METRICAL unit, so beam boundaries are beat boundaries** — which gives a reader a metre signal from beam geometry alone, with no duration arithmetic. And the mid-bar prohibition means a beam that appears to span the middle of a bar is evidence that the bar segmentation is wrong, not that the engraver was permissive.
- **Numbers:** None.
- **Source:** Gould p.153 (*Beaming according to the metre*): "Divisions of a beat are beamed together in all metres, in order to simplify reading beats"; "notes should never be beamed over the middle of the bar, since the third beat carries a secondary stress which should always be indicated in the notation."
- **Rigid or variable:** Rigid in the modern convention. **Gould explicitly records that it is not historical:** "Music from the Classical and Romantic periods frequently uses this beaming – the context makes it clear that cross rhythm is not intended." **That exception matters for 19th-century plates, which is what this project reads.**
- **Would be falsified by:** Nothing — the era exception is stated with the rule.
- **Known exceptions:** Classical and Romantic engraving; deliberate cross-rhythm; half-bar beaming, which Gould permits in some metres.

### A flag hangs on the stem, starting at the stem's end
- **Says:** The flag (tail) is attached to the stem's far end, not to the notehead, and is registered against the stem.
- **Category:** Stems & beams
- **Predicts (mechanically):** **A flag must be associated with a note via its STEM, not via proximity to the notehead** — the flag sits about 3.5 staff spaces from the head. SMuFL states its registration exactly: "Flags are positioned such that y=0 corresponds to the end of a stem of normal length, and x=0 corresponds to the left-hand side of the stem." Bravura carries a `stemUpNW` anchor on `flag8thUp` at `[0.0, −0.04]`. The tail's own length also predicts where it ends relative to the head.
- **Numbers:** Gould p.15: "The engraved design of tail is 2½–3¼ stave-spaces long (3–3¼ is the norm). This ensures that the tail of an up-stemmed note finishes opposite or just above the notehead". Bravura `flag8thUp` bbox 1.056 × 3.276 sp. A flagged note carries **one flag per beam level** — two for a semiquaver — and Gould p.15 records that each additional tail or beam requires the stem to be lengthened.
- **Source:** SMuFL *Metrics and glyph registration*; Gould p.15 (*Tails*, *adding tails and beams*); Bravura `glyphBBoxes` / `glyphsWithAnchors`.
- **Rigid or variable:** Rigid in attachment; the tail's design length is a font/house matter within the stated band.
- **Would be falsified by:** Flags drawn at the notehead end of the stem.
- **Known exceptions:** Gould notes a down-stemmed note's tail "may curve as far as to touch the notehead" — so a flag's INK can reach the head even though its attachment does not.

---

## Rests & bar filling

### A whole rest HANGS from its line; a half rest SITS on it
- **Says:** The semibreve rest is drawn below the line it belongs to; the minim rest is drawn above.
- **Category:** Rests & bar filling
- **Predicts (mechanically):** **This is the ONLY thing that separates the two glyphs, and it is a vertical-position test, not a shape test** — see the next entry. The whole rest's ink lies entirely below its staff position; the half rest's entirely above. SMuFL states the registration directly, and Bravura's boxes confirm it numerically: `restWhole` runs y = **−0.540 to +0.036** (below the baseline), `restHalf` y = **−0.008 to +0.568** (above it).
- **Numbers:** In default position the whole rest hangs from the **fourth line** (the second line from the top) and the half rest sits on the **third**, i.e. middle, line.
- **Source:** SMuFL, *Metrics and glyph registration*: "The font baseline should represent this staff position, with the exception of the whole note (semibreve) rest, which should hang from the font baseline." Bravura `glyphBBoxes`. The specific line numbering is standard and is stated in the general references consulted (e.g. Wikipedia, *Rest (music)*, and the music-education references returned in search: "The whole rest hangs under the fourth line, while the half rest sits on the third").
- **Rigid or variable:** Rigid.
- **Would be falsified by:** A plate whose whole and half rests sit at the same height.
- **Known exceptions:** In multi-voice writing rests are displaced from their default position (LilyPond `Rest` `(voiced-position . 4)`, `define-grobs.scm`), which **destroys the absolute-position discriminator** and leaves only the relation to the surrounding voice.

### The whole and half rest glyphs are the same shape and the same size
- **Says:** The two rests are one rectangle, differing only in whether it hangs or sits.
- **Category:** Rests & bar filling
- **Predicts (mechanically):** **No shape, size or aspect-ratio classifier can ever separate a whole rest from a half rest.** Bravura gives both exactly **1.128 × 0.576 staff spaces** — an aspect of about **1.96 : 1**, wide and flat. A reader that reports confidence in `restWhole` vs `restHalf` from a crop alone is reporting something it cannot know; the discriminator is the y relation to the staff, and nothing else.
- **Numbers:** `restWhole` and `restHalf` both w **1.128**, h **0.576**. Aspect w/h ≈ **1.96**; h/w ≈ **0.51**.
- **Source:** Bravura `glyphBBoxes`.
- **Rigid or variable:** Rigid — they are deliberately the same glyph.
- **Would be falsified by:** A font drawing them at different sizes.
- **Known exceptions:** None recorded.

### Rest shapes separate strongly by aspect ratio, except whole vs half
- **Says:** The rest family's glyphs have very different proportions from one another.
- **Category:** Rests & bar filling
- **Predicts (mechanically):** Aspect ratio is a strong, publisher-independent discriminator ACROSS rest values even though it is useless WITHIN the whole/half pair. From Bravura: whole/half **1.128 × 0.576** (wide and flat, h/w ≈ 0.51); quarter **1.076 × 2.992** (tall, h/w ≈ **2.78**); 8th **0.988 × 1.700** (h/w ≈ 1.72); 16th **1.280 × 2.716** (h/w ≈ 2.12). **A whole rest and a quarter rest differ in h/w by more than 5×** and cannot plausibly be confused by shape — so a reader confusing them is failing on ink quality, not on geometry.
- **Numbers:** As above; also `restMaxima` 1.524 × 1.996, `restLonga` 0.500 × 1.996, `restDoubleWhole` 0.500 × 1.000.
- **Source:** Bravura `glyphBBoxes`.
- **Rigid or variable:** The ordering is rigid; exact ratios vary by font and by plate.
- **Would be falsified by:** A plate whose quarter rest is wider than tall.
- **Known exceptions:** Broken or bled ink on a scan will not respect any of it.

### One whole rest fills any bar, in any metre
- **Says:** A bar that is entirely silent is filled with a single semibreve rest whatever the time signature says, and that rest means THE BAR, not four beats.
- **Category:** Rests & bar filling
- **Predicts (mechanically):** **A lone whole rest in a bar is a statement about the bar's length, not about its own nominal value.** Its duration must be taken from the meter in force, so a reader that assigns it 4.0 quarters writes a wrong duration in every metre but 4/4. Conversely it carries NO information about what the meter is — it is the same glyph in 2/4 and 12/8 — so it must never be counted as evidence when deriving a meter from bar sums.
- **Numbers:** None.
- **Source:** Wikipedia, *Rest (music)*, and the general references returned in search: "When a bar is devoid of notes, a whole (semibreve) rest placed at the middle of the measure is used, regardless of the actual time signature."
- **Rigid or variable:** Rigid in modern practice.
- **Would be falsified by:** Bars of silence filled with a rest of the metre's actual length.
- **Known exceptions:** Historically recorded exceptions — 4/2 (a breve rest), 3/2 and 6/4 (a dotted whole rest), and metres shorter than 3/16 (a rest of the true length). **These are real in 19th-century and earlier plates.**

### A whole-bar rest is centred in the bar
- **Says:** The bar-filling rest is placed horizontally at the middle of the empty measure, not at its head.
- **Category:** Rests & bar filling
- **Predicts (mechanically):** A rest sitting near a bar's horizontal CENTRE with nothing else in the bar is a whole-bar rest. A mark at the bar's LEFT EDGE is more likely a clef, key signature, meter or barline fragment than a bar rest. This is a usable left/centre discriminator for ink at the head of an otherwise empty measure.
- **Numbers:** None.
- **Source:** Wikipedia, *Rest (music)* / general references: the whole rest is "placed at the middle of the measure".
- **Rigid or variable:** Conventional and widely followed.
- **Would be falsified by:** Bar rests engraved flush left.
- **Known exceptions:** None recorded.

### A rest is centred on or about the middle of the staff
- **Says:** Rests take a default vertical position in the staff's centre region rather than tracking the pitch around them.
- **Category:** Rests & bar filling
- **Predicts (mechanically):** A rest's y carries no pitch information, so a reader must not resolve it as one; and a mark in the staff's middle region that is not a notehead is a rest candidate. Where multiple lines or voices are in play, Gould says a rest that is part of a beat aligns HORIZONTALLY with adjacent notes — so its x is meaningful even though its y is not.
- **Numbers:** None.
- **Source:** Gould p.284 (*placing rests*, in the percussion chapter): "Centre each rest around the middle space or on the middle line"; "When there are multiple lines, place a rest that is part of a beat on a horizontal level with adjacent notes. Place other rests at the centre of the group of lines."
- **Rigid or variable:** Gould states it for percussion staves; the same default holds generally. Multi-voice writing displaces rests deliberately.
- **Would be falsified by:** Rests whose height varies with the surrounding pitch in single-voice writing.
- **Known exceptions:** Multi-voice displacement (LilyPond's `voiced-position . 4`).

### A multi-bar rest is an H-bar one staff space thick
- **Says:** Several bars of silence are shown as a thick horizontal bar between two vertical strokes, with a number above.
- **Category:** Rests & bar filling
- **Predicts (mechanically):** Gives an expected thickness for the horizontal stroke — **1.0 staff space, twice a beam's 0.5** — so an H-bar is the thickest horizontal ink on the staff and is separable from a beam by thickness alone. It also predicts a NUMERAL centred above the staff, and that the span consumes several bars of the document's bar sequence at once, which a bar counter must account for.
- **Numbers:** Bravura `hBarThickness` **1.0** staff space. SMuFL: "The thickness of the horizontal line drawn between two vertical lines, known as the H-bar".
- **Source:** SMuFL *engravingDefaults*; Bravura `engravingDefaults`.
- **Rigid or variable:** Reasonably rigid; some editions use the older stacked-rest forms instead.
- **Would be falsified by:** A plate whose multi-bar rests are drawn at beam thickness.
- **Known exceptions:** Older editions use church-rest stacks rather than an H-bar. MOLA requires the number range to be printed and requires multi-bar rests to be broken at rehearsal landmarks.

### An augmentation dot goes in a SPACE — above the line if the note is on one
- **Says:** A dot follows its notehead in the same space; where the note is on a line, the dot is raised into the space above.
- **Category:** Rests & bar filling
- **Predicts (mechanically):** **A dot is never at the same height as a notehead on a line — it is half a staff space above it.** So a dot reader keyed to the notehead's own y will systematically miss the on-a-line case, which is half of all notes; the search window must be asymmetric, reaching upward. The dot's own size is tiny and fixed: **0.400 × 0.400 staff spaces** in Bravura, i.e. under half a space square.
- **Numbers:** Bravura `augmentationDot` 0.400 × 0.400, bbox SW `[0.0, −0.2]` NE `[0.4, 0.2]` — symmetric about its own position. Vertical offset for an on-a-line note: **+0.5 staff spaces**.
- **Source:** Wikipedia, *Dotted note*: "If dotted note is on a space, the dot is placed in that space. If the note is on a line, the dot is placed in the space above." Bravura `glyphBBoxes`.
- **Rigid or variable:** Rigid for the single-voice case.
- **Would be falsified by:** Dots engraved level with on-a-line noteheads.
- **Known exceptions:** Wikipedia states them: "The placement of dots need not follow this convention when space does not allow for it" — specifically dots on adjacent notes of a chord, and dots in multi-voice passages.

---

## Accidentals & key signatures

### An accidental stands BEFORE its note, at the same staff position
- **Says:** The accidental is printed immediately to the left of the head it alters, at that head's height.
- **Category:** Accidentals & key signatures
- **Predicts (mechanically):** An accidental must be joined to the notehead to its RIGHT and at its OWN staff position — never to the nearest head in any direction. Two constraints, not one: side and height. The height constraint alone rules out most mis-attachments in a dense chord.
- **Numbers:** None for the horizontal gap.
- **Source:** Wikipedia, *Accidental (music)*: accidentals appear before the note they modify; "An accidental applies to the note that immediately follows it."
- **Rigid or variable:** Rigid.
- **Would be falsified by:** Accidentals printed after their notes.
- **Known exceptions:** Some 20th-century notation places accidentals above notes; not relevant to orchestral repertoire.

### An accidental holds to the end of the bar, at that staff position
- **Says:** Once printed, an accidental governs later notes at the same staff position until the barline.
- **Category:** Accidentals & key signatures
- **Predicts (mechanically):** **The accidental is a SPAN, not a mark on one note** — its scope is (staff position, from this x to the next barline). A reader that attaches an accidental only to its immediate note will read every later note in the bar a semitone wrong, and a record with nowhere to store a span cannot represent the fact at all.
- **Numbers:** None.
- **Source:** Wikipedia, *Accidental (music)*: "Accidentals apply to subsequent notes on the same staff position for the remainder of the measure where they occur, unless explicitly changed by another accidental. Once a barline is passed, the effect of the accidental ends".
- **Rigid or variable:** Rigid in common-practice notation.
- **Would be falsified by:** Editions restating an accidental on every affected note — which is a courtesy style, not a contradiction.
- **Known exceptions:** The tie across a barline (next entry); other octaves, where conventions vary (entry below).

### An accidental carries across a barline through a TIE
- **Says:** Where a note bearing an accidental is tied over the barline, the accidental continues to apply to the tied note.
- **Category:** Accidentals & key signatures
- **Predicts (mechanically):** **The tie is what makes a cross-barline pitch legal.** So a reader that resolves the far end of a tie by looking for its own accidental will spell it PLAIN and produce a tie between two different pitches — an internally impossible object. Conversely: a tie whose two ends resolve to different pitches is positive evidence that this rule was not applied, which is a truth-free self-check.
- **Numbers:** None.
- **Source:** Wikipedia, *Accidental (music)*: "If a note with an accidental is tied, the accidental continues to apply, even if the note it is tied to is in the next measure."
- **Rigid or variable:** Rigid.
- **Would be falsified by:** Engraving that restates the accidental on the tied note — common as a courtesy, and harmless.
- **Known exceptions:** None recorded.

### A courtesy accidental is real ink that changes nothing
- **Says:** Editors print reminder accidentals — often in parentheses — where a previous bar's accidental might mislead.
- **Category:** Accidentals & key signatures
- **Predicts (mechanically):** **An accidental's presence does not imply a pitch change.** A reader counting accidentals as evidence of chromaticism, or using them to infer a key, will be misled by courtesies. Parenthesised accidentals are a separate glyph family and should be read as such.
- **Numbers:** None.
- **Source:** Wikipedia, *Accidental (music)*. MOLA and IU both call for their use: IU requires "courtesy accidentals … for natural pitches in new bar following accidental in previous bar".
- **Rigid or variable:** **Entirely editorial.** Frequency varies enormously by publisher and era.
- **Would be falsified by:** Nothing — it is a described editorial practice.
- **Known exceptions:** None recorded.

### The order of sharps and flats in a key signature is fixed
- **Says:** Key-signature accidentals appear in one invariable sequence.
- **Category:** Accidentals & key signatures
- **Predicts (mechanically):** **A key signature's Nth accidental is fully determined by N** — so the reader's job is to count and locate, never to identify each accidental's letter name. It also means a partial reading is recoverable: if the 1st and 3rd slots are read, the 2nd is known. And a run of accidentals in the WRONG order is not a key signature.
- **Numbers:** Sharps: **F♯ C♯ G♯ D♯ A♯ E♯ B♯**. Flats: **B♭ E♭ A♭ D♭ G♭ C♭ F♭** (the reverse).
- **Source:** Wikipedia, *Key signature*.
- **Rigid or variable:** Rigid.
- **Would be falsified by:** A signature printing its accidentals in another order.
- **Known exceptions:** None in common practice.

### Key-signature accidentals occupy fixed staff positions that depend on the clef
- **Says:** Each accidental of a key signature sits at a prescribed height, chosen per clef so that ledger lines are avoided.
- **Category:** Accidentals & key signatures
- **Predicts (mechanically):** **The signature is a SLOT TABLE keyed on (clef, count), so it should be fitted by position rather than counted** — a missed accidental leaves a gap the table can fill, whereas counting cannot recover it. It also means a signature read against the WRONG clef produces a confidently wrong answer rather than an abstention, so the clef must be settled first or the fit must abstain.
- **Numbers:** None given as heights.
- **Source:** Wikipedia, *Key signature*: positions differ by clef, e.g. A♯ "occasionally … notated on the top line" in bass clef, and "Sharps in the tenor clef are arranged differently to avoid using a ledger line".
- **Rigid or variable:** Rigid per clef, with the documented tenor/bass variants.
- **Would be falsified by:** A signature whose accidental heights do not fit any clef's table.
- **Known exceptions:** The tenor-clef sharp arrangement is itself the exception, and it is well known.

### The key signature is reprinted at the start of every system
- **Says:** Clef and key signature appear at the beginning of each line of music, not only at the start of the piece.
- **Category:** Accidentals & key signatures
- **Predicts (mechanically):** **A key signature is expected at the head of every staff of every system**, so a staff that reads none on a continuation system is a READING failure, not an engraving fact — which makes cross-system voting legitimate, because all systems should agree. A time signature, by contrast, is NOT reprinted (see the meter entry), so the two families must not be treated alike.
- **Numbers:** None.
- **Source:** MOLA, *Parts*: "Clefs and key signatures must appear at the beginning of each line."
- **Rigid or variable:** Rigid in modern preparation, and standard in engraved orchestral scores.
- **Would be falsified by:** An edition omitting the key signature on continuation systems.
- **Known exceptions:** Instruments conventionally written without a key signature at all — see the next entry.

### Horns, trumpets, timpani and tuned percussion traditionally carry NO key signature
- **Says:** These parts are written with accidentals as needed rather than with a key signature, by long tradition.
- **Category:** Accidentals & key signatures
- **Predicts (mechanically):** **A blank key-signature window on a horn, trumpet or timpani staff is the CORRECT reading, not a missed one.** A reader that votes a system's key signature onto every staff will write a wrong signature onto exactly these staves; a reader that flags them as failures will mis-rank its own work. Which staves these are is knowable from the margin label or the score order before any ink is read.
- **Numbers:** None.
- **Source:** MOLA, *Parts*: "Traditionally, horns, tuned percussion, and timpani use any required accidentals rather than a key signature."
- **Rigid or variable:** **Traditional rather than absolute** — MOLA's own word is "traditionally", and modern editions increasingly do print signatures for horns. Expect it to hold on 19th-century plates and to weaken after.
- **Would be falsified by:** A held 19th-century edition printing key signatures on its horn and timpani staves.
- **Known exceptions:** Modern practice; transposing instruments other than these carry their own transposed signature normally (MOLA: "Parts for transposing instruments must be written in the transposed key").

---

## Time signatures & meter

### At a system's start the order is clef, key signature, time signature
- **Says:** The opening of a piece prints the clef first, then any key signature, then the meter.
- **Category:** Time signatures & meter
- **Predicts (mechanically):** **A hard left-to-right ordering for the header window.** Anything left of the key signature is the clef; anything right of it and left of the first note is the meter. This bounds each reader's search window using the others' results, and it means a meter template search must start AFTER the key signature — searching from the bar's left edge will find clef ink.
- **Numbers:** None. For scale: Bravura's `gClef` is **2.684 sp wide and 7.024 sp tall**, `fClef` 2.756 × 3.588, `cClef` 2.796 × 4.048 — so the clef alone consumes roughly 2.7 staff spaces of the header, and a key signature several more.
- **Source:** Gould p.152: "At the beginning of a piece, the time signature goes after a clef and any key signature." Bravura `glyphBBoxes`.
- **Rigid or variable:** Rigid.
- **Would be falsified by:** An edition printing the meter before the key signature.
- **Known exceptions:** None recorded.

### A time signature is printed once per movement and NOT repeated per system
- **Says:** The meter holds for a whole movement or until it changes, and is restated only at a new movement.
- **Category:** Time signatures & meter
- **Predicts (mechanically):** **A continuation system printing no meter is the normal case, not a reading failure** — the opposite of the key signature. So the meter must be CARRIED from an earlier system, and a reader that expects to find one on every system will read noise as a meter. It also predicts that a meter DOES reappear at a movement start, even when unchanged, which makes a restated meter a movement-boundary signal.
- **Numbers:** None.
- **Source:** Gould p.152: "It holds good for a whole movement or up to a change of metre. It should be repeated at the beginning of a new movement, even if this is the same as that of the previous movement, and even when the music follows on from the previous movement without a break".
- **Rigid or variable:** Rigid.
- **Would be falsified by:** Engraving that reprints the meter on every system.
- **Known exceptions:** MOLA requires meter changes to be indicated in PARTS even during extended rests, which can put a meter where a score would not.

### Time-signature numerals fill the staff's height — two staff spaces per digit
- **Says:** The numerals are set large, in a heavy font, spanning the staff.
- **Category:** Time signatures & meter
- **Predicts (mechanically):** **A gate on size that rejects small numerals outright.** Each digit should measure about **2 staff spaces tall**, centred on the middle line, so the pair spans the staff's full 4 spaces. A digit-shaped mark one staff space tall is a fingering, a tuplet number or a measure number — not a meter. Bravura confirms: `timeSig4` is 1.720 × **2.004** sp.
- **Numbers:** SMuFL: "Digits for time signatures should be scaled such that each digit is two staff spaces tall, i.e. 0.5 em, and vertically centered on the baseline." Gould p.152: "Time-signature numerals should exactly fill the height of the stave. Smaller numerals are not sufficiently conspicuous."
- **Source:** Gould p.152 (*Size and placing*); SMuFL *Metrics and glyph registration*; Bravura `glyphBBoxes`.
- **Rigid or variable:** Rigid. Gould notes the numerals use "a unique heavy font so that they stand out as clearly as possible against the stave", which is a further discriminator from body numerals.
- **Would be falsified by:** Meters set at body-text size.
- **Known exceptions:** Gould cross-references *Enlarging time-signature symbols* (p.519) for score layout — conductors' scores sometimes set the meter LARGER than the staff, spanning several staves.

### A time-signature change is placed AFTER the barline
- **Says:** The new meter belongs to the bar it governs, so it stands to the right of the barline that opens that bar.
- **Category:** Time signatures & meter
- **Predicts (mechanically):** **A meter glyph's position within its bar disambiguates it.** A meter at the HEAD of a bar (left fraction ≈ 0) governs that bar. Meter-shaped ink elsewhere in a bar is not a meter change. This gives a placement test that needs no reading of the digits.
- **Numbers:** None.
- **Source:** Gould p.152 (*Placing time-signature changes*): "The new time signature is always placed after the barline."
- **Rigid or variable:** Rigid.
- **Would be falsified by:** Meter changes engraved before the barline that opens their bar.
- **Known exceptions:** The cautionary, which is exactly the case of a meter printed before a barline — see the next entry.

### A cautionary time signature stands at the END of the previous system, after its last barline
- **Says:** Where the metre changes at a system break, a courtesy signature is printed at the end of the preceding line.
- **Category:** Time signatures & meter
- **Predicts (mechanically):** **A meter printed after a system's FINAL barline governs NO bar of that system** — it announces the next one. So a reader must not size any bar from it, and must not treat it as a meter change at that point. But it is real, correct evidence about the NEXT system's meter, read from a different physical printing — which makes it a genuine second witness for the same fact.
- **Numbers:** None.
- **Source:** Gould p.152: "When a change of time signature occurs between systems, add a cautionary indication at the end of the first system, after the last barline". MOLA generalises it: "When a clef, key signature, or time signature changes at the beginning of a line, a cautionary warning should be included at the end of the previous line."
- **Rigid or variable:** Standard modern practice; MOLA requires it. Older plates are less consistent.
- **Would be falsified by:** Editions that change metre at a system break with no courtesy.
- **Known exceptions:** None recorded.

### A double barline precedes a metre change ONLY at a new section
- **Says:** The thin double barline is a structural mark, not a consequence of the metre changing.
- **Category:** Time signatures & meter
- **Predicts (mechanically):** **A double barline is evidence about SECTION structure, not about the meter**, and the two must not be inferred from each other. A reader that treats every double barline as a metre change, or that expects one at every metre change, is wrong in both directions.
- **Numbers:** None.
- **Source:** Gould p.152: "A thin double barline precedes a change of time signature only when one coincides with a new musical section." IU states the converse as a house rule — "Double barlines for tempo changes and modulations … Do not use at meter changes."
- **Rigid or variable:** Gould states it as the convention; IU's stricter form shows houses differ.
- **Would be falsified by:** An edition using a double barline at every metre change.
- **Known exceptions:** IU's practice, which is the stricter reading of the same principle.

### `C` and cut-`C` are letter meters, and cut-C is measurably taller
- **Says:** Common time and alla breve are printed as letter symbols rather than as digit pairs.
- **Category:** Time signatures & meter
- **Predicts (mechanically):** **A meter reader that requires two stacked digits cannot see a letter meter at all** — the commonest metre in the repertoire. And the two letters ARE separable by geometry without reading the stroke: Bravura gives `timeSigCommon` **1.676 × 2.000** and `timeSigCutCommon` **1.672 × 2.880** — the same width, but cut-C is **44% taller**, because the vertical stroke extends beyond the C. So height alone separates them; the stroke does not have to be found.
- **Numbers:** `timeSigCommon` h **2.000**, `timeSigCutCommon` h **2.880**; both w ≈ 1.67.
- **Source:** Bravura `glyphBBoxes`. That both denote 4/4 and 2/2 respectively is universal.
- **Rigid or variable:** The glyph shapes are rigid; the height ratio will vary a little by font.
- **Would be falsified by:** A plate whose cut-C is no taller than its C.
- **Known exceptions:** Both are four and two crotchets' worth respectively, so a LENGTH-based reader cannot distinguish `C` from 4/4 at all — only the engraving differs.

---

## Slurs, ties & phrasing

### A tie joins two heads of the SAME pitch and curves away from the stem
- **Says:** The tie is a short curve between two noteheads at one staff position, drawn on the side opposite the stems.
- **Category:** Slurs, ties & phrasing
- **Predicts (mechanically):** **Two constraints, and the first is decisive: a tie's two ends are at ONE staff position.** A curve whose flanking heads sit at different staff positions cannot be a tie — it is a slur, or the pairing is wrong. That is a truth-free check on both the arc's class and its pairing. The second constraint gives the tie's side: opposite the stem, so a down-stemmed pair carries its tie above.
- **Numbers:** None for the vertical offset. Thickness: Bravura `tieEndpointThickness` **0.10**, `tieMidpointThickness` **0.22** — so a tie is thin at the ends and about twice as thick in the middle. LilyPond leaves `note-head-gap . 0.2` and `stem-gap . 0.35` staff spaces (`define-grobs.scm:3543–3544`).
- **Source:** Wikipedia, *Tie (music)*: "A tie is a curved line connecting the heads of two or more notes of the same pitch"; "Ties are normally placed opposite the stem direction of the notes, unless there are two or more voices simultaneously." Bravura `engravingDefaults`; LilyPond 2.24.4 `scm/lily/define-grobs.scm:3534–3555`.
- **Rigid or variable:** The same-pitch requirement is absolute — it is what a tie MEANS. The side is conventional and suspended in multi-voice writing.
- **Would be falsified by:** An engraved tie between two different pitches.
- **Known exceptions:** Multi-voice bars, where ties follow the voice rather than the stem.

### A slur joins DIFFERENT pitches and is drawn on the notehead side
- **Says:** The slur arcs over or under a run of notes, on the side away from the stems; with mixed stem directions it goes above.
- **Category:** Slurs, ties & phrasing
- **Predicts (mechanically):** **The slur's SIDE predicts the stem direction of the notes beneath it, and vice versa** — a slur above a run of down-stemmed notes is anomalous. It also means a slur and the notes it binds are on opposite sides of the noteheads, so the arc's ink does not overlap the heads: a reader testing for "noteheads under the arc" by box overlap will find none, and must probe toward the heads instead.
- **Numbers:** Bravura `slurEndpointThickness` **0.10**, `slurMidpointThickness` **0.22** — the same profile as a tie, so **thickness cannot separate a slur from a tie**. LilyPond `Slur`: `height-limit . 2.0`, `ratio . 0.25`, `thickness . 1.2` (`define-grobs.scm:2876+`).
- **Source:** Dorico, *General placement conventions for slurs*: "A slur on a single staff always curves upwards and is placed above the notes, unless all of the notes under the slur are up-stem, in which case it curves downwards and is placed below the notes." Wikipedia, *Tie (music)* for the different-pitch contrast. Bravura `engravingDefaults`; LilyPond 2.24.4.
- **Rigid or variable:** Conventional, and Dorico records that houses differ — "jazz scores sometimes treat slurs as articulations, preferring them consistently above the staff."
- **Would be falsified by:** An edition placing slurs on the stem side by default.
- **Known exceptions:** Jazz house style; multi-voice writing; Gould's rule for mixed outer stems (next entry).

### Where the outer notes have opposite stems, the slur end moves toward the noteheads
- **Says:** A slur spanning notes whose outer stems point in opposite directions is adjusted at the stem end so that it does not tilt against the pitch direction.
- **Category:** Slurs, ties & phrasing
- **Predicts (mechanically):** A slur's endpoints are not always at a uniform offset from their notes — they move toward the heads in this specific configuration. So an endpoint-to-head distance measured across a page will be BIMODAL rather than tight, and a fixed tolerance fitted to the common case will refuse this one.
- **Numbers:** None.
- **Source:** Attributed to Gould, *Behind Bars*, via Scoring Notes and the NOTATIO forum thread consulted: "When outer notes have opposite stem directions, move the slur at the stem end towards the noteheads so it does not tilt contrary to the direction of the pitches." **The primary text was not read — this is a secondary attribution.**
- **Rigid or variable:** Stated as a rule; the magnitude is unspecified.
- **Would be falsified by:** Slurs engraved at a uniform stem-end offset regardless of the outer stems.
- **Known exceptions:** None recorded.

### A slur or tie broken by a barline is ONE mark drawn in two pieces
- **Says:** A curve that spans a barline is still a single slur or tie; the printing simply crosses the line.
- **Category:** Slurs, ties & phrasing
- **Predicts (mechanically):** **A reader that cuts a page into per-measure cells will detect two arcs where the music has one**, and must merge them. The two fragments are recognisable: each terminates AT the cell's own boundary rather than in open space, and they are adjacent. A reader that emits both writes twice as many slurs as the page prints.
- **Numbers:** None.
- **Source:** Wikipedia, *Tie (music)*, which lists "when holding a note across a bar line" as the first use of a tie. The consequence for a cell-based reader is this project's own inference and is not itself in the literature.
- **Rigid or variable:** Rigid — it is a fact about what a tie is.
- **Would be falsified by:** Nothing.
- **Known exceptions:** At a SYSTEM break a slur is printed as two pieces that are far apart on the page and at different heights, which needs a different join from the barline case.

### A slur is narrower than the notes it binds
- **Says:** The arc is drawn BETWEEN its outer noteheads, so its ink stops short of both outer head centres.
- **Category:** Slurs, ties & phrasing
- **Predicts (mechanically):** **A slur's bounding box does not reach its own endpoints' note centres**, so a reader testing "which heads lie inside this arc" must pad the box outward by roughly a notehead width or it will lose the first and last note of every slur.
- **Numbers:** None given in the sources consulted.
- **Source:** `UNSOURCED — believed true, not verified`. It follows from the endpoint-offset rules that Dorico and LilyPond both parameterise (`note-head-gap`, `stem-gap`, "Vertical offset from end of stem"), but no source consulted states the horizontal inset directly. **Gould's *Behind Bars* almost certainly states it in the slurs chapter, which the sample pages do not include.**
- **Rigid or variable:** Believed rigid; magnitude unknown.
- **Would be falsified by:** Measuring engraved slurs and finding their ink reaching or passing the outer head centres.
- **Known exceptions:** Unknown.

### A slur must begin and end in the same voice
- **Says:** A phrase mark belongs to one voice and does not cross between them.
- **Category:** Slurs, ties & phrasing
- **Predicts (mechanically):** A candidate arc whose two ends fall in different voices of a two-voice bar is mis-paired. Since voice is readable from stem direction, this is a check available before any pitch is resolved.
- **Numbers:** None.
- **Source:** `UNSOURCED — believed true, not verified`. It is how MusicXML encodes slurs (within a `<voice>` stream) and how LilyPond scopes them, but no notation source consulted states it as an engraving rule.
- **Rigid or variable:** Believed rigid in single-staff writing; cross-staff slurs in keyboard music are a real and separate case.
- **Would be falsified by:** Engraved slurs joining two voices of one staff.
- **Known exceptions:** Cross-staff slurs in piano and harp writing.

---

## Dynamics & hairpins

### Dynamics go BELOW an instrumental staff and ABOVE a vocal one
- **Says:** The default side for a dynamic mark depends on the kind of staff, so that it never falls between noteheads and lyrics.
- **Category:** Dynamics & hairpins
- **Predicts (mechanically):** **A dynamic is expected in a band below its own staff — so a dynamic found ABOVE a staff on an orchestral page more likely belongs to the staff above it.** That is a cross-staff attribution rule that needs no confidence comparison. It is exactly the geometry that makes cell padding steal dynamics from a neighbour.
- **Numbers:** None for the distance.
- **Source:** Dorico documentation, *Placement of dynamics* / *Positions of dynamics*, as summarised in the Steinberg help and Scoring Notes: dynamics are placed below instrumental staves and above vocal staves by default; Gould is cited by those sources as recommending the same convention. **Gould's own text was not read on this point.**
- **Rigid or variable:** Strong convention; vocal/instrumental split is universal.
- **Would be falsified by:** An orchestral edition setting its dynamics above the staves.
- **Known exceptions:** Grand-staff instruments (next entry); a staff carrying two players may print one part's dynamics above and the other's below.

### On a grand staff, dynamics go BETWEEN the two staves
- **Says:** For piano and harp, a dynamic that governs both hands is placed in the gap between the staves.
- **Category:** Dynamics & hairpins
- **Predicts (mechanically):** In the inter-staff gap of a braced pair, a dynamic belongs to BOTH staves, not to the nearer one. A nearest-staff attribution rule is structurally wrong there and will assign a shared mark to one hand.
- **Numbers:** None.
- **Source:** Dorico documentation via Steinberg help: "For grand staff instruments, such as piano or harp, dynamics are usually placed between the two staves, but can be placed both above and below when each staff requires separate dynamics."
- **Rigid or variable:** Strong convention.
- **Would be falsified by:** Keyboard editions placing shared dynamics only below the lower staff.
- **Known exceptions:** Separate dynamics per hand, which are then placed above and below.

### Dynamics are not placed INSIDE the staff
- **Says:** The dynamic band lies outside the staff's five lines.
- **Category:** Dynamics & hairpins
- **Predicts (mechanically):** **A gate: dynamic-shaped ink within the staff's own lines is not a dynamic.** It also means the dynamic band is a strip of page, parallel to the staff and outside it — which is a place a reader can look for dynamics directly rather than waiting for a detector to fire inside a measure cell.
- **Numbers:** None.
- **Source:** Dorico documentation via Steinberg help: "In general, dynamics are not placed within the staff, as hairpins in particular become very hard to read."
- **Rigid or variable:** Strong convention; crowded 19th-century plates do violate it.
- **Would be falsified by:** A plate routinely setting hairpins across the staff lines.
- **Known exceptions:** Very congested engraving.

### A hairpin is a thin line, thinner than a stem
- **Says:** Crescendo and diminuendo wedges are drawn with a fine line.
- **Category:** Dynamics & hairpins
- **Predicts (mechanically):** **A hairpin is thin, long and diagonal — the shape a bounding-box detector is structurally worst at**, and the same shape class as a stem or a ledger line but even finer. At 0.16 staff spaces it is close to a staff line's 0.13, so on a staff-line-erased image a hairpin can be erased with the lines if the erasure is at all aggressive.
- **Numbers:** Bravura `hairpinThickness` **0.16** staff spaces — against `stemThickness` 0.12 and `staffLineThickness` 0.13. SMuFL: "The thickness of a crescendo/diminuendo hairpin".
- **Source:** SMuFL *engravingDefaults*; Bravura `engravingDefaults`.
- **Rigid or variable:** Narrow band.
- **Would be falsified by:** Hairpins engraved at beam weight.
- **Known exceptions:** None recorded.

### A dynamic letter's ink extends LEFT of its own origin
- **Says:** The `f` and `p` glyphs are italic letterforms whose flourishes overhang their nominal position.
- **Category:** Dynamics & hairpins
- **Predicts (mechanically):** **A dynamic glyph's bounding box is not centred on its placement point, and is not even entirely to the right of it** — so joining letters into a word by naive x-adjacency will get the spacing wrong, and a box-overlap test between adjacent letters will report overlap where the letters are separate. Bravura gives `dynamicForte` bbox SW x = **−0.564** (i.e. ink 0.56 staff spaces LEFT of the origin) with an `opticalCenter` anchor at x = 1.256, and `dynamicPiano` SW x = **−0.356**. The glyphs are also comparatively wide: `dynamicForte` **2.020 × 2.384** staff spaces.
- **Numbers:** As above. `dynamicFF` is a single ligature glyph 2.980 wide — **wider than two `f`s are apart**, which is why two adjacent `f` boxes can overlap and still be two real letters.
- **Source:** Bravura `glyphBBoxes` and `glyphsWithAnchors`.
- **Rigid or variable:** A property of the letterforms; consistent in direction across music fonts.
- **Would be falsified by:** A font whose dynamic glyphs are box-aligned to their origin.
- **Known exceptions:** None recorded.

---

## Articulations & ornaments

### An articulation goes on the notehead side, opposite the stem
- **Says:** Staccato dots, tenuto lines, accents and the rest are placed at the head end of the note, away from the stem.
- **Category:** Articulations & ornaments
- **Predicts (mechanically):** **The articulation's SIDE is determined by the stem direction, so a mark and its note are joined by a rule with a known sign** — an up-stemmed note's articulation is below its head, a down-stemmed note's above. A nearest-notehead attachment that ignores the side will take marks from the wrong note about half the time.
- **Numbers:** None. Bravura `articStaccatoAbove` is **0.336 × 0.336** staff spaces — a third of a space square, which is the smallest notation glyph a reader will meet.
- **Source:** Dorico, *Positions of articulations*: "Articulations are placed on the notehead side by default". IU, *Articulations*: "Place on note head side, outside staff (except staccato)". Bravura `glyphBBoxes`.
- **Rigid or variable:** Strong modern convention. **Dorico records the exception directly:** in multi-voice contexts "Articulations are placed at the end of the stem side of a note or chord" so that the reader can tell which voice they belong to.
- **Would be falsified by:** Single-voice engraving placing articulations at the stem end.
- **Known exceptions:** Multi-voice bars; marcato, which Dorico says "is always placed above the staff, regardless of the stem direction"; opposing stems generally.

### An articulation above SITS on its position; one below HANGS from it
- **Says:** The two orientations of an articulation glyph are registered differently.
- **Category:** Articulations & ornaments
- **Predicts (mechanically):** **The glyph name carries its side** (`…Above` / `…Below`), and the side determines which edge of the glyph's box is the meaningful y. So a reader can recover the intended staff position from a detected box only if it knows which variant it has — taking a box centre gives an answer that is wrong by the glyph's own half-height in one direction or the other.
- **Numbers:** SMuFL: "Articulations to be positioned above a note should sit on the baseline (y=0), while articulations to be positioned below should hang from the baseline." Bravura `fermataAbove` bbox SW `[0.012, −0.012]` — entirely above the baseline, confirming it.
- **Source:** SMuFL, *Metrics and glyph registration*; Bravura `glyphBBoxes`.
- **Rigid or variable:** Rigid within SMuFL fonts.
- **Would be falsified by:** A font registering both variants identically.
- **Known exceptions:** None recorded.

### A small articulation near the middle line is centred in the next free SPACE
- **Says:** Where a note sits near the staff's centre, a small articulation is moved into an unoccupied space rather than being drawn over a line.
- **Category:** Articulations & ornaments
- **Predicts (mechanically):** **An articulation's vertical offset from its notehead is not constant** — for notes near the middle line it is quantised to the next free space, so the mark-to-head distance is discrete rather than smooth. A fixed-distance window will therefore succeed for outer notes and fail for middle ones, which is a systematic and position-dependent failure rather than noise.
- **Numbers:** Dorico: applies to "articulations that are less than a space in height", i.e. in practice staccato and tenuto; the offset is to "the next unoccupied space".
- **Source:** Dorico, *Positions of articulations*: "If a note is placed on the middle staff line or on the space immediately on either side, articulations that are less than a space in height are centered in the next unoccupied space."
- **Rigid or variable:** Strong convention.
- **Would be falsified by:** Engraved staccato dots drawn over staff lines.
- **Known exceptions:** Larger articulations, which go outside the staff entirely — Dorico: "If an articulation cannot fit within a staff space, or if the note is placed high or low on the staff, the articulation is placed outside the staff."

### An articulation is horizontally centred on the notehead
- **Says:** The mark's x is the head's x, not the stem's.
- **Category:** Articulations & ornaments
- **Predicts (mechanically):** **The x offset between a mark and its note is ZERO**, which makes x a strong, tight join key, while y is the loose one (see the previous entry). A join built on x with a y side-test is therefore better conditioned than a Euclidean nearest-neighbour.
- **Numbers:** None.
- **Source:** Dorico, *Positions of articulations*: "Articulations on the notehead side are always centered horizontally on the notehead", with the stated exception of staccato and staccatissimo placed on the stem side, "which center on the stem itself".
- **Rigid or variable:** Strong convention.
- **Would be falsified by:** Articulations engraved off-centre from their heads in single-voice writing.
- **Known exceptions:** The stem-side staccato case, named above; ties, where Dorico offsets notehead-side articulations "by an additional 1/4 space in order to avoid the end of the tie".

### A fermata is drawn above the staff by default
- **Says:** The pause sign goes above the note, inverted below only when the staff carries two parts or the note is in a lower voice.
- **Category:** Articulations & ornaments
- **Predicts (mechanically):** A fermata is expected in the band ABOVE its staff, which on a conductor's page is the same band the staff above's dynamics occupy — so fermata and dynamic detections in one gap are competing for the same ink and need arbitration, not independent attribution. It also predicts that a fermata carrier can be a REST as readily as a note.
- **Numbers:** Bravura `fermataAbove` 2.408 × 1.328 staff spaces — wide and low, an easily separated shape.
- **Source:** `UNSOURCED — believed true, not verified` for the "above by default" claim; no source consulted states it. **The GEOMETRY is sourced** (Bravura `glyphBBoxes`; SMuFL's above/below registration rule), and SMuFL's provision of paired `fermataAbove` / `fermataBelow` glyphs implies the two-sided convention.
- **Rigid or variable:** Believed a strong convention.
- **Would be falsified by:** Orchestral engraving placing fermatas below by default.
- **Known exceptions:** Lower voice of a shared staff; below-staff placement when the music above is congested.

---

## Score layout & systems

### Barlines are continuous within each family of instruments
- **Says:** In a full score the barline runs unbroken through each instrumental family and BREAKS between families.
- **Category:** Score layout & systems
- **Predicts (mechanically):** **The family grouping is readable from where the interior barlines STOP** — the gaps a barline does not cross are the family boundaries. This is a structural fact recoverable from ink with no bracket detection at all, and it means a system's staves partition into runs rather than being a flat list. Conversely, a gap that every barline crosses is INSIDE a family.
- **Numbers:** None.
- **Source:** MOLA, *Formatting — Full Score*: "The barlines should be continuous within each family of instruments." IU, *Barlines*: "Break between choirs per large group bracketing."
- **Rigid or variable:** Standard in modern and 19th-century orchestral engraving. **Some editions bar through the entire system, and early-music editions use Mensurstrich (barlines only BETWEEN staves), so the signal can be absent.**
- **Would be falsified by:** A held orchestral edition whose interior barlines cross every gap.
- **Known exceptions:** Mensurstrich editions (Wikipedia, *Bar (music)*: a barline that "stretches only between staves of a score, not through each staff"); choir-barred vocal scores, where the breaks fall at choir edges rather than family edges; divisi staves, where MOLA requires the barline to be **continuous** between the split staves.

### A bracket encloses each instrumental family, with sub-brackets inside it
- **Says:** Brackets group the score vertically by family, and a second level marks like instruments within a family.
- **Category:** Score layout & systems
- **Predicts (mechanically):** A bracket is a heavy vertical rule at the system's left edge whose EXTENT names a family — so it spans exactly the same staves the continuous barlines do, giving a second, independent witness to the same partition. Bravura distinguishes the levels by weight: `bracketThickness` **0.5** staff spaces against `subBracketThickness` **0.16** — a **3× difference**, so the two levels are separable by thickness alone.
- **Numbers:** `bracketThickness` 0.5, `subBracketThickness` 0.16 staff spaces.
- **Source:** IU, *Brackets*: "Orchestra: bracket each choir (woodwinds, brass, percussion, strings); Secondary brackets on like instruments; third level for divisi". Bravura `engravingDefaults`; SMuFL *engravingDefaults*.
- **Rigid or variable:** **Variable by publisher, and some editions print no family bracket at all.** A brace (rather than a bracket) marks a grand staff.
- **Would be falsified by:** Nothing — the variability is the finding.
- **Known exceptions:** Editions with no bracketing; keyboard braces, which are a different mark.

### The vertical order of a full score is woodwind, brass, percussion, voices, strings
- **Says:** Instrument families appear top to bottom in a settled order, and within a family by sounding pitch, high to low.
- **Category:** Score layout & systems
- **Predicts (mechanically):** **A strong PRIOR on which instrument each staff is, before any margin label is read**, and therefore a prior on each staff's clef, written range and whether it carries a key signature. It also makes the staff order MONOTONE, so an alignment between a printed lineup and a reference roster can be a monotone join rather than a free assignment.
- **Numbers:** Five groups, in order: **Woodwind · Brass · Timpani/Percussion/Harp/Keyboard · Vocal · Strings**.
- **Source:** MOLA, *The Performance Material*: "the generally accepted layout is as follows" with that list, adding "Any instrument that does not easily fit in the layout above will usually be placed in the third group" and "Within these broad categories, instruments should be vertically ordered, for the most part, by sounding pitch high to low."
- **Rigid or variable:** **Variable — MOLA itself says "While it is possible to find many exceptions"**, and it describes modern practice. 19th-century placement of timpani, harp and solo instruments differs by publisher.
- **Would be falsified by:** Nothing; the exceptions are stated.
- **Known exceptions:** Solo instruments, which sit above the strings; percussion ordering by player rather than by pitch, which MOLA permits provided it is consistent.

### A tacet staff is SUPPRESSED from a system
- **Says:** A printed score omits staves whose instruments are silent for a whole system.
- **Category:** Score layout & systems
- **Predicts (mechanically):** **The number of staves in a system is NOT the number of instruments in the work, and it varies system to system on one page.** So joining staves to parts by ordinal position is unsafe on any system shorter than the full lineup; the suppression can be INTERIOR, which shifts every staff below it. A system's staff count is itself evidence about which instruments it holds.
- **Numbers:** None.
- **Source:** `UNSOURCED — believed true, not verified` as a stated rule; no source consulted states it directly. It is implied by MOLA's requirement that score pages "indicate the prevailing instrumentation" with staff styles and by IU's "Use staff styles to indicate prevailing instrumentation on every score page", both of which presuppose that the instrumentation shown varies by page.
- **Rigid or variable:** Universal in engraved orchestral scores; absent from parts, which are one instrument each.
- **Would be falsified by:** An orchestral edition printing every staff on every system.
- **Known exceptions:** Some editions print all staves throughout; study scores vary.

### A part is one instrument, and divisi go on separate staves
- **Says:** Parts are extracted one per player or section, with complicated divisions written on their own staves.
- **Category:** Score layout & systems
- **Predicts (mechanically):** In a SCORE, one printed staff may carry several players (Fl. 1+2 condensed), so the staff count and the part count are different quantities and neither implies the other. In a PART they are the same. Any reader joining a score's staves to a reference encoding must allow for this many-to-one.
- **Numbers:** None.
- **Source:** MOLA, *Formatting*: "Do not create wind parts with multiple instruments on a single staff; for instance, flutes 1 and 2 should be separate parts"; "String parts should be created with one part per section"; "Complicated string divisions should be written on separate staves. The barline should be continuous between these separate staves."
- **Rigid or variable:** MOLA's rules are for PARTS. **Scores condense freely and always have.**
- **Would be falsified by:** Nothing — the score/part asymmetry is the point.
- **Known exceptions:** The whole of score engraving.

### A measure number sits at the START of a system, upper left
- **Says:** Bar numbers are printed at the beginning of each system, or below the system if every bar is numbered.
- **Category:** Score layout & systems
- **Predicts (mechanically):** **A small numeral at a system's top-left corner, outside the staff, is a measure number, not a fingering, tuplet or meter digit.** Position separates it from every other numeral family on the page. And it names the DOCUMENT's bar index for that system, which is the join between a printed system and a reference encoding.
- **Numbers:** None.
- **Source:** MOLA, *The Performance Material*: "If every measure is to be numbered it should be placed below the system. Often just the first measure of each system is numbered, placed in the upper left corner and sometimes additionally … on a specific line of the grand staff, such as above the first violins." IU: "Place at system start".
- **Rigid or variable:** Two accepted placements, both stated; MOLA requires only that the choice be consistent throughout a work.
- **Would be falsified by:** Nothing.
- **Known exceptions:** Film and music-theatre scores number every bar, in both score and parts (MOLA).

### Tempo marks stand above the top staff and above the first violins
- **Says:** A tempo indication is printed twice on a full-score system, once at the top and once above the strings.
- **Category:** Score layout & systems
- **Predicts (mechanically):** **Text found above the first violin staff in mid-score is a TEMPO mark, not a direction belonging to that staff** — and it duplicates text that also appears at the top of the system. A reader that attributes it to the violins will attach a system-level fact to one part, and a reader counting distinct directions will double-count it.
- **Numbers:** None.
- **Source:** MOLA, *The Performance Material*: "All tempo indications should appear above the top staff and above the first violin line (or similarly positioned staff in the absence of strings) on each score page." IU, *Rehearsal Marks*: "at minimum, at top of score and above string section". IU also gives a horizontal rule: "The left edge of the tempo indication should align with the left edge of the meter or the first notational element."
- **Rigid or variable:** Standard in modern preparation; older plates are less consistent but the practice is old.
- **Would be falsified by:** Held editions printing tempo marks only once per system.
- **Known exceptions:** Scores with no strings place the second copy at the equivalent position.

---

## Text & margin labels

### Instrument names are printed IN FULL on the first system and ABBREVIATED thereafter
- **Says:** A full score names each instrument in full to the left of its staff at the beginning, and uses abbreviations on subsequent pages.
- **Category:** Text & margin labels
- **Predicts (mechanically):** **The first system of a work is the one page where the margin label is unambiguous**, and every later system prints a truncated form that a lexicon may not resolve. So identity should be established on the opening system and CARRIED, rather than re-read per system. It also predicts that a continuation system's labels are short, which is exactly the population a truncation-prone reader mishandles.
- **Numbers:** None.
- **Source:** MOLA, *The Performance Material*: "At the beginning of the full score, the full name of each instrument should be listed to the left of the corresponding staff/staves. (Example 1). On subsequent pages, abbreviations of the instrument names should be used. (Example 2)."
- **Rigid or variable:** Universal in orchestral engraving.
- **Would be falsified by:** A score printing full names on every system.
- **Known exceptions:** Some editions omit labels on continuation systems for some families — commonly the strings — leaving those staves with no label at all.

### A running head names the instrument on every page of a part
- **Says:** Each page after the first carries the instrument name as a header.
- **Category:** Text & margin labels
- **Predicts (mechanically):** In a PART, identity is available from page text independent of any staff label — a second, non-margin source for the same fact. On a SCORE this does not apply, and the margin is the only source.
- **Numbers:** None.
- **Source:** Gould p.558 (*Labelling the part*): "For subsequent pages it is good policy to label the top centre of each page with instrument name and player number, in case pages become separated later (this is known as a 'running head')." MOLA: "Include instrument names as a header on each subsequent page."
- **Rigid or variable:** Recommended practice rather than universal; Gould's word is "good policy".
- **Would be falsified by:** Parts with no running head — which are common.
- **Known exceptions:** Gould notes that for a doubling part "it is necessary to give only the principal instrument for the running head", so the running head can be less specific than the staff label.

### Instrument abbreviations are drawn from a short standard set
- **Says:** The abbreviations used in margins are conventional and few.
- **Category:** Text & margin labels
- **Predicts (mechanically):** Bounds the lexicon a label reader needs, and shows how SHORT the strings are — two to five characters, often with a trailing period. At that length, OCR errors and truncation are both likely to produce a string that is a valid abbreviation for a DIFFERENT instrument, so a match must be scored against the work's roster rather than accepted on its own.
- **Numbers:** IU's list: **Picc., Fl., Ob., E.Hn., Cl., Bcl., Bn., Hn., Tp., Trb., Btrb., Tba., Timp., Pc., Hp., Pn., Vn., Va., Vc., Cb.** — 20 entries, median length 3 characters.
- **Source:** IU, *Instrument Names*.
- **Rigid or variable:** **Highly variable by language and publisher** — this is one English-language house list. Italian (`Fl.`, `Ob.`, `Cor.`, `Tr.`, `Vni`), German (`Fl.`, `Hb.`, `Hr.`, `Trp.`, `Vl.`) and French traditions all differ, and the SAME abbreviation means different instruments across them (`Tp.` is timpani in one tradition and trumpet in another).
- **Would be falsified by:** Nothing — the variability is the finding, and it is the main hazard in reading margin labels.
- **Known exceptions:** The cross-language collisions named above.

### Performance directions are printed in Italian, English, German or French
- **Says:** Tempo, dynamic, technique and expression instructions use a conventional language.
- **Category:** Text & margin labels
- **Predicts (mechanically):** Bounds the vocabulary an in-system text reader must gate on, and says the gate is a MULTILINGUAL lexicon rather than an English one. It also means the printing TRADITION of a document is inferable from the words it uses — which in turn predicts which abbreviation set its margin labels are drawn from.
- **Numbers:** None.
- **Source:** MOLA, *The Performance Material*: "All instructions for tempi, dynamics, technique, and expression should be in a conventional language such as English, Italian, German, or French."
- **Rigid or variable:** Conventional; a single document is usually consistent in one language.
- **Would be falsified by:** Nothing.
- **Known exceptions:** Mixed-language editions, and Italian dynamics with German expression marks in the same score, which is common in 19th-century German publishing.

---

## Barlines & repeats

### A barline runs from the top staff line to the bottom one
- **Says:** An ordinary barline spans exactly the staff, sometimes continuing between staves.
- **Category:** Barlines & repeats
- **Predicts (mechanically):** **A barline's HEIGHT is exactly four staff spaces and its position spans the staff's own lines** — which is what separates it from a stem, since the two are close in thickness (0.16 vs 0.12) but a stem is ~3.5 spaces and is anchored at a notehead, while a barline is 4.0 spaces and anchored at the staff's edges. A vertical run that begins at the top line and ends at the bottom line is a barline.
- **Numbers:** Height **4.0 staff spaces** for a single-staff barline.
- **Source:** Wikipedia, *Bar (music)*: "Regular bar lines consist of a thin vertical line extending from the top line to the bottom line of the staff, sometimes also extending between staves in the case of a grand staff or a family of instruments in an orchestral score."
- **Rigid or variable:** Rigid.
- **Would be falsified by:** Barlines drawn short of the outer lines.
- **Known exceptions:** Systemic barlines spanning a whole family; Mensurstrich, which spans only BETWEEN staves.

### A thin barline is 0.16 staff spaces; a thick one is 0.5
- **Says:** The two barline weights differ by about 3×.
- **Category:** Barlines & repeats
- **Predicts (mechanically):** **A thick barline is exactly as heavy as a beam** (both 0.5 in Bravura) and **three times a thin barline**, so the thin/thick distinction is robust to a coarse measurement while the thick-barline/beam distinction is not — the latter needs orientation. It also gives the expected separation between paired lines: `barlineSeparation` 0.4 for two thin, `thinThickBarlineSeparation` 0.4 for a final barline.
- **Numbers:** Bravura `thinBarlineThickness` **0.16**, `thickBarlineThickness` **0.5**, `barlineSeparation` **0.4**, `thinThickBarlineSeparation` **0.4**. Application defaults span **0.12–0.24** for a thin barline (Scoring Notes).
- **Source:** Bravura `engravingDefaults`; SMuFL *engravingDefaults*; Scoring Notes.
- **Rigid or variable:** The ratio is consistent; absolute values vary by a factor of two across applications.
- **Would be falsified by:** A plate whose final barline's thick stroke is not markedly heavier.
- **Known exceptions:** None recorded.

### A final barline is thin then thick; a section barline is thin then thin
- **Says:** Two different double-barlines carry two different meanings, distinguished by the weight of the second stroke.
- **Category:** Barlines & repeats
- **Predicts (mechanically):** **The classification is a thickness comparison between two adjacent vertical runs, which needs no context.** Thin-thin = a section division; thin-thick = the end of a piece or movement. Getting it right matters structurally: a thin-thick barline is a movement boundary, which is exactly where a carried meter, key and lineup must all stop being carried.
- **Numbers:** As above — the second stroke is either 0.16 (section) or 0.5 (final).
- **Source:** Wikipedia, *Bar (music)*: "A double bar line (or double bar) consists of two single bar lines drawn close together, separating two sections within a piece, or a bar line followed by a thicker bar line, indicating the end of a piece or movement."
- **Rigid or variable:** Rigid.
- **Would be falsified by:** An edition ending a movement with a thin-thin barline.
- **Known exceptions:** None recorded.

### Repeat dots sit in the two middle spaces, flanking the middle line
- **Says:** The two dots of a repeat barline occupy the second and third spaces of a five-line staff.
- **Category:** Barlines & repeats
- **Predicts (mechanically):** **The dots are at FIXED staff positions**, one space above and one below the middle line — so a repeat sign is recognisable from two small round marks at known heights beside a heavy barline, with no need to read the barline's own structure. And the SIDE the dots fall on tells which way the repeat faces.
- **Numbers:** Dots centred in spaces 2 and 3, i.e. at staff positions ±1 space from the centre line. Bravura `repeatBarlineDotSeparation` **0.16** staff spaces — "the default horizontal distance between the dots and the inner barline" (SMuFL).
- **Source:** Wikipedia, *Bar (music)* and *Repeat sign*, with the general references consulted stating the positions: "one between the second and third lines of the staff and one between the third and fourth line"; "The dots will be on the same side of the line as the material which is to be repeated." Bravura `engravingDefaults`.
- **Rigid or variable:** Rigid on a five-line staff. Undefined for staves of other sizes.
- **Would be falsified by:** Repeat dots at other staff positions.
- **Known exceptions:** One-line percussion staves and other non-standard staves.

### A dashed barline has a dash twice the length of its gap
- **Says:** Dashed barlines are drawn with a specific dash-to-gap ratio.
- **Category:** Barlines & repeats
- **Predicts (mechanically):** A broken vertical run at a bar position is a DASHED BARLINE, not a damaged solid one, if its dashes and gaps are regular at roughly 2:1. That distinguishes an engraving choice from scan damage — which otherwise look identical to a run-length detector.
- **Numbers:** Bravura `dashedBarlineDashLength` **0.5**, `dashedBarlineGapLength` **0.25**, `dashedBarlineThickness` **0.16**.
- **Source:** Bravura `engravingDefaults`; SMuFL *engravingDefaults*.
- **Rigid or variable:** Font default; dashed barlines are rare in the orchestral repertoire.
- **Would be falsified by:** Dashed barlines with irregular dashes.
- **Known exceptions:** None recorded.

### A double barline is a SECTION mark, not a consequence of anything else
- **Says:** Editions place double barlines at tempo changes, modulations and structural divisions.
- **Category:** Barlines & repeats
- **Predicts (mechanically):** **A double barline is a positive structural signal available from ink alone** — it marks a place where a new section begins, and therefore a place where a carried fact (meter, key, tempo, occasionally the lineup) is most likely to change. It is the cheapest structural landmark on a page.
- **Numbers:** None.
- **Source:** IU, *Barlines*: "Double barlines for tempo changes and modulations; Heavy single barlines for phrase divisions". Gould p.152 for the meter-change case.
- **Rigid or variable:** **Variable by house** — IU's rules are one department's; other houses use double barlines at metre changes, which IU forbids. The presence of a double barline is meaningful; its absence is not.
- **Would be falsified by:** Nothing; the house variation is the finding.
- **Known exceptions:** As above.

---

## ⚠️ How to use this document

1. **Nothing here is a measurement of anything this project reads.** Every number is a font default, an application default, or a publisher's guideline. The band is usually wider than the number.
2. **Prefer the entries whose "Predicts" is a CONSTRAINT over those whose is a prior.** A constraint ("a tie's two ends are at one staff position") can refuse a reading; a prior ("stems go down when ambiguous") can only tilt one.
3. **Check "Rigid or variable" before building.** Roughly a third of these entries carry a stated exception that is normal in 19th-century orchestral engraving — the beaming-across-the-bar exception and the horns-carry-no-key-signature tradition are both directly relevant to the repertoire this project reads.
4. **Four entries are `UNSOURCED`.** They are marked in place, and they are: *A slur is narrower than the notes it binds*; *A slur must begin and end in the same voice*; *A tacet staff is SUPPRESSED from a system*; *A fermata is drawn above the staff by default*. Treat them as the weakest tier and source them before they carry weight.
5. **Do not add an entry without a source you actually read.** A registry with honest gaps is more useful than a confident one; that is the whole point of the status table at the top.
