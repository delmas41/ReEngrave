# Horn crook bare-label research (ROADMAP 2.26, `unnamed_in_short_system`)

**ANSWER: Yes, for this work — a bare `(C)`/`(Es)` on a Brahms 1 mvt 1 horn
staff always names the OTHER crook of the same braced Horn pair, never an
unrelated instrument.** Confidence: high for THIS movement (structural,
not just probable); the convention is general but not universal — see
caveat below.

## Evidence, this work

- **Dossier** (`data/dossiers/brahms-sym1-mvt1.json`, `source_kind: encoding`)
  gives 4 horn parts: `C Horn 1`, `C Horn 2`, `Eb Horn 3`, `Eb Horn 4` (all
  `transposition_semitones: -7`, i.e. horn-in-F-equivalent written interval —
  the field records the CROOK by name, not by the transposition math). Two
  trumpets are both `C Trumpet` (one crook only, no `(C)`/`(Es)` ambiguity
  possible for them here). Clarinets are `Bb Clarinet 1/2` only (no C or Es
  clarinet in this movement). Timpani carries no crook label at all
  (untransposed instrument; tuning is written as pitches, not `(C)`/`(Es)`).
  **No other instrument in this movement is crooked in C or Es**, so a bare
  crook fragment has exactly one plausible referent: the horns.
- **Catalog** (`data/score-library/catalog.json`, `source_kind: catalog`,
  IMSLP `InstrDetail`): confirms `4 horns, 2 trumpets, ... timpani` — same
  roster, work-level, independent of the encoding.
- **The plate itself** (crops `o226-01/02/07/08.png`, 600 DPI, this
  benchmark): the REFERENCE (widest) system prints `Hr.` once as a brace
  label spanning both staves, then `(C) Hr.` on the upper staff and `Hr.
  (Es)` on the lower — one shared instrument word, two crook qualifiers.
  Every other (short) system reprints the brace `Hr.` and the upper staff's
  `(C) Hr.`/`(C) Hr` but drops the instrument word on the lower staff,
  leaving only `(Es)` (19 systems) or, symmetrically, only `(C)` (1 system).
  Crop 07 shows a system where BOTH staves are reduced to bare crooks —
  `(C)` then `(Es)` — under one `Hr.` brace, with nothing else nearby the
  crook could name. This is a margin-space economy, not a different
  instrument entering: the brace + shared label already commits the pair to
  Horn; the per-staff parenthetical exists only to say which of the two
  already-named horns is which.

## General convention (secondary sources)

Two horns crooked differently and printed as a braced pair is Brahms's
normal practice — a horn-crook study of his four symphonies states he
"prescribes the C crook in 11 of his 16 symphonic movements and the E
[-flat] crook in 7" ([A Look at the Nineteenth-Century American Horn
Player's Instru...](https://scholarworks.calstate.edu/downloads/t722hh29f)),
i.e. mixed-crook horn pairs like this movement's are the documented norm,
not an edge case. General score-reading guidance confirms braced
instrument pairs carry one shared label and per-staff qualifiers distinguish
them ([vi-control: Horn pairings on the
score](https://vi-control.net/community/threads/horn-pairings-on-the-score.31161/)
— "Staves for pairs of instruments must always be clearly labeled"). Gould's
*Behind Bars* was consulted for an explicit rule on continuation-system
abbreviation but returned nothing specific enough to quote — its content on
this point is idiomatic/example-driven rather than a stated rule, so it is
not cited as a source here.

## Where the answer would be wrong

The convention "bare crook = continuation of the braced neighbour above" is
NOT a universal claim about all engraving — it depends on there being only
one crooked-instrument-family occupying that key at that point in the
score. It would fail if:
- **Two different transposing families shared a crook name nearby** — e.g.
  a page with Horns AND Trumpets both crooked in Es, printed as adjacent
  braced pairs; a bare `(Es)` between them would be genuinely ambiguous
  without checking which brace it sits under. Not the case in Brahms 1 mvt 1
  (trumpets are single-crook C only), but general enough that the rule
  should key off the SAME brace/margin-label group, not proximity alone.
  This is exactly `_forced_pairing`'s own caution in `identity.py`.
- **Timpani tuning shorthand** can look similar in some editions (a bare
  key letter near the timpani staff) but is conventionally written as pitch
  letters (e.g. tuning to specific notes), not as a crook parenthetical —
  low collision risk but worth a reader guard if timpani ever abbreviates
  this way in a corpus edition.

Sources: [A Look at the Nineteenth-Century American Horn Player's
Instrument](https://scholarworks.calstate.edu/downloads/t722hh29f) ·
[Crook (music) — Wikipedia](https://en.wikipedia.org/wiki/Crook_(music)) ·
[vi-control: Horn pairings on the
score](https://vi-control.net/community/threads/horn-pairings-on-the-score.31161/)
· repo: `data/dossiers/brahms-sym1-mvt1.json`, `data/score-library/catalog.json`,
`library/reference/brahms/symphony-1/brahms--symphony-1--mvt1--gradus.mxl`,
`benchmarks/omr-staff-identity-2026-09/out/print/o226-{01,02,07,08}.png`.
