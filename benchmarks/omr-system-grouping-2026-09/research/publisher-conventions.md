# Engraving conventions & the publisher hypothesis (Phase 1C, main memo)

2026-09-01. Conventions research agent (Opus). Tags: [SOURCED] = authoritative
source; [MEASURED] = the agent's own controlled LilyPond experiment this
session; [INFERENCE]; [FOLKLORE] = widely repeated, no authoritative source.
Full memo (with source ledger) in the session transcript; load-bearing content
preserved here.

## 0. Bottom line — the hypothesis is probably the wrong FRAME (but points at a real thing)

**The dominant hazard is a convention near-universal across publishers and eras,
not a house style: interior barlines in an orchestral full score are
deliberately broken between instrument-family groups.** The only ink crossing a
family boundary is the **left-edge systemic barline** — a rule ≈0.16 staff-
spaces wide (about a staff line's thickness), sitting at exactly the x where the
staff lines begin.

Our veto ("a column of ink runs through the entire gap") is therefore correct in
principle but at every family boundary its entire safety margin is that one thin
left-edge rule — **measured at 2 pixels** at pocket-score resolution.

This explains the symptom Sean reports (failures that *persist across editions*):
a publisher-specific cause predicts edition-dependent failure; a
convention-universal cause predicts exactly the cross-edition persistence we see.
**Where the publisher DOES enter is second order but real:** whether that 2-px
systemic barline survives a given edition's plate wear, scan quality, and page
size. So "publisher" is the wrong primary variable but a real modifier — and the
benchmark should measure both.

## The falsifiable prediction — RUN THIS BEFORE BUILDING ANYTHING

[INFERENCE] If a system over-splits when any one family boundary loses its
2-px bridge, and orchestral systems have ~4 bracket groups (3–4 boundaries):

| per-boundary detect rate | 3 boundaries | 4 boundaries |
|---|--:|--:|
| 0.97 | 0.913 | 0.885 |
| 0.96 | 0.885 | **0.849** |
| 0.95 | 0.857 | 0.815 |

**Prediction:** grouping failures cluster *at family (bracket-group) boundaries*,
and per-page failure rate scales with the number of bracket groups. **If they do
not, this analysis is wrong.** This is directly testable from the sweep data
(`sweep.jsonl` records per-gap bridging + `group_sizes`): correlate break-fired
vs. group_index boundary, and failure count vs. n groups. This decides the fix.

Note the reframe cuts against one instinct: F1 over-merges (our standing
failures) are the *opposite* of the over-split this convention predicts. Both
exist. The convention analysis predicts **over-splits** at family boundaries
(the systemic barline missed); the F1 cases are **over-merges** (stray ink faking
a bridge where a real break belongs). The benchmark must count both directions.

## 1. Barline conventions

**[SOURCED] Barlines follow BRACKETS, not systems.** MOLA *Guidelines for Music
Preparation* (rev. 2017): full-score barlines continuous *within each instrument
family*, not through the system; string divisi on separate staves DO get a
continuous barline between them. Encoded as a per-GROUP property by every engine:
Dorico (barlines extend across bracket/brace groups; **vocal staves never joined
by barlines even when bracketed**); LilyPond (`StaffGroup`=connected,
`ChoirStaff`=**not** connected, `GrandStaff`=connected); Sibelius (by family,
vocal separate). Both interchange formats make it a group attribute: MusicXML
`<group-barline>` ∈ {yes, no, **Mensurstrich**}; MEI `@bar.thru` on `<staffGrp>`.
Two independent standards committees chose a per-group tri-state → the convention
is real and general, not a house quirk. Gould *Behind Bars* ch.17 covers it; the
agent could not access the text (cited via table of contents + Scoring Notes).

**[MEASURED] The decisive experiment.** An 8-staff LilyPond score (WW group,
brass group, ChoirStaff, strings group), 200 dpi, staff-space 13.8 px, columns
≥99% inked through each gap:

| gap | bridged at x |
|---|---|
| Fl–Ob (inside WW bracket) | bracket 218–224, **systemic bar 235–237**, final barline 1493–1495 |
| Ob–Cor (**between groups**) | **235–237 only** |
| Cor–Tbn (inside brass bracket) | 218–224, 235–237, 1493–1495 |
| Tbn–S (**group → choir**) | **235–237 only** |
| S–B (**inside ChoirStaff, vocal**) | bracket 218–224, **235–237 — no barline** |
| B–Vln (**choir → group**) | **235–237 only** |
| Vln–Vc (inside string bracket) | 218–224, 235–237, 1493–1495 |
| **inter-system gap** (2-system page) | **nothing; max column ink 0.16** |

- The systemic barline bridges EVERY gap in the system (all 3 family boundaries
  + the vocal gap). Interior/final barlines bridge nothing across a group
  boundary. The bracket bridges only its own group. A brace is curved and never
  forms a full column (peaked 0.5–0.7).
- **[MEASURED] The systemic barline sits at exactly `x_start`.** Mimicking
  `Staff.x_start` (longest ink run on the middle line) gave x_start = 235 — the
  same 3 px as the systemic barline. **If the gap scan is `[x_start, x_end]`
  with any inclusive/exclusive slip, any +pad, or post-deskew resample, we lose
  the only column that bridges a family boundary.** Single most actionable
  finding → audit the scan window (repo-state §1.2: `_robust_x_window` uses
  median x_start ± WINDOW_MARGIN_SPACINGS; verify the boundary handling).

**[SOURCED+INFERENCE] Thickness (staff-spaces):** staffLine 0.13, **thinBarline
0.16**, **bracket 0.5** (Bravura). Systemic barline vs bracket in px:

| staff height | 300 dpi | 600 dpi |
|---|--:|--:|
| 4 mm (MOLA min, pocket score) | **1.9** / 5.9 | 3.8 / 11.8 |
| 7 mm (part size) | 3.3 / 10.3 | 6.6 / 20.7 |

*(bar / bracket, px)* — **a bracket is ~3× the barline's ink everywhere**, so it
survives scanning that kills the barline. Interacts with our OMR_DPI 300-vs-600
tradeoff: 300 dpi on a dense pocket score puts the systemic barline at ~2 px.

**[MEASURED] Degradation.** At staff-space ≤7.6 px, staff clustering collapses
and the analyser reported **17 bridging columns across a real inter-system gap —
a false MERGE produced purely by resolution.** Since our veto can only merge,
this failure is silent and unrecoverable downstream.

**[SOURCED] 19th-c. plate practice (Breitkopf GA, Peters, early UE, Durand,
Ricordi, Schirmer): the agent found NO authoritative source** on whether they
ran interior barlines full-height or family-broken. Refused to guess. This is
the biggest hole and is answerable only empirically from our own scans (recipe
below). Sean's instinct that publishers differ is separately supported in
general (Holab: "many publishers do things differently than Gould") but not
specifically for barline spans.

## 2–3. System dividers, brackets, braces

- **[SOURCED] Divider glyphs are U+E007–E009** (the brief's "U+E00A–E00C" was
  wrong; U+E00A = splitBarDivider, a different mark). In the margin, between
  systems; **not used in chamber/choral scores**; exist because orchestral pages
  alternate 1-system / multi-system (hidden empty staves). **Recall unknown,
  probably poor; treat as confirmatory only.**
- **[MEASURED+SOURCED] "A bracket spans exactly the system" is FALSE and is an
  error in our CLAUDE.md** (the system-grouping paragraph says "the bracket
  encloses exactly it"). Standard orchestral layout has NO outer whole-system
  bracket — per-family brackets (2 staves each in the test, 4 brackets for an
  8-staff system) plus the systemic barline. Bracket geometry rel. `x_start`:
  outer edge ≈1.23 sp left, inner ≈0.87 sp left, thickness ≈0.4 sp.
- Braces (piano/harp/divisi) are curved → never a full column [MEASURED].

## 4. Spacing — a formal proof of the "gaps can't separate" finding

[SOURCED] LilyPond shipped defaults (staff-spaces), basic / **minimum**:
staff-inside-group 9/**7**; **across-group-boundary 10.5/8**; system→system
12/**8**. Under compression both floor at **8** → no distance threshold can
separate them, by construction. [MEASURED] real 2-system page: within-group
4.98, across-group 6.50, between-system 8.02 — and a denser variant's
within-system gap hit 8.09, larger than the other page's inter-system gap.
[SOURCED] Worse in practice: "French scoring" hides resting staves, and
intra-system spacing is deliberately stretched to fill the page, so it is not a
stable quantity. Demote spacing to a tie-breaker at most.

## 5. Audiveris — the most useful prior art, and it already does what we should

[SOURCED, GRID step doc] Audiveris builds systems **constructively from a peak
graph**, with NO gap-distance stage at all:
1. vertical projection within each staff → peaks (barlines, half-braces,
   half-brackets, long stems);
2. peaks are graph vertices; an alignment between a peak in one staff and the
   next becomes an edge; each alignment is tested for **actual foreground ink
   between the two staff peaks** (a "concrete connection" — functionally our
   `gap_bridging_counts`);
3. staves gathered into systems by **transitive closure over connections**
   (union-find), refined by a privileged **starting column** at the left;
4. brackets & braces searched **to the LEFT of the starting column**; braces
   drive gathering into PARTS.

Three takeaways: our connectivity mechanism is state-of-the-practice; Audiveris
makes it **constructive, not a veto** over gap candidates; and it additionally
reads the bracket/brace column to the left — **the piece we are missing**.
Config `disconnectedBracedParts` (default false) "relaxes the requirement on
internal barline connections" — but only for 2-staff braced parts. No automatic
over-split recovery (manual `SystemMergeTask` in the UI); `largeSystemStaffCount
= 4` accommodation exists; no GRID regression tests, no published accuracy.

[SOURCED, HEADERS step] **Directly reusable positive system-start detector:**
within one system, header components align in columns across staves — a clef is
mandatory at every staff header, key-sig slices align, time sig is
present-and-identical or absent throughout. We already have `staff_header.py`,
`clef_geometry.py`, `key_signature_vote.py` — this turns them into positive
evidence of a system start.

## External ground truth found

[SOURCED] **AudioLabs measure bounding-box set** (Zalkow et al., ISMIR 2019 LBD)
— several hundred scanned pages with system-level measure boxes across **Wagner's
complete *Ring* (orchestral), Beethoven piano sonatas, Schubert Winterreise,
Carus pieces** — multiple publishers, real scans. A ready-made external
multi-edition test set.
https://www.audiolabs-erlangen.de/resources/MIR/2019-ISMIR-LBD-Measures

## Ranked page-measurable features (robustness across publishers)

1. **Left systemic-barline continuity**, scanned in a NARROW band at the staves'
   shared left edge — the only ink crossing family boundaries. Fails: ~2 px at
   300 dpi/pocket; sits exactly at x_start (off-by-one kills it); absent on
   single-staff systems; unverified for 19th-c. plates.
2. **Bracket span** searched LEFT of x_start — 3× the barline's ink; what
   Audiveris uses; we don't use it. Fails: bounds a family not the system;
   braces aren't columns.
3. **Header-column alignment** (clefs/key/time at same x across staves) —
   positive evidence; readers already exist. Fails: inherits clef-detection
   ceiling.
4. **Margin instrument-label column** (labels restart each system) — readers
   exist (text/Surya/vision). Fails: 18/65 PDFs have a text layer.
5. **Bar number at system start** — cheap positive marker.
6. **System-divider glyphs** — high precision, low/unknown recall.
7. **Spacing bimodality** — tie-breaker only (provably non-separating).
8. **Body-text exclusion** — already solved (`_line_ink_runs_per_space`).

## Traps where the ink-column veto is FALSE

1. **Family boundaries** — no interior barline crosses; only the ~2 px systemic
   barline. 3 of 7 gaps in the test. The big one.
2. **Vocal staves** (Beethoven 9, Mahler 2/8, opera/oratorio) — barlines NEVER
   joined across vocal staves even inside a bracket. A choral page can present a
   run of consecutive gaps with no barline ink.
3. **Braces** (piano/harp/celesta/organ/divisi) — curved, ~0.5–0.7 coverage,
   fail a ≥95% column test.
4. **Hidden staves ("French scoring")** — two systems on one page can have
   different staff counts and positions; intra-system spacing stretched. Breaks
   any assumption that a page's systems are structurally parallel, and any
   dossier join assuming constant staff count per page.
5. **x_start boundary aliasing** — the systemic barline occupies exactly the
   x_start columns; verify the window isn't `(x_start, x_end)` exclusive.
6. **Resolution-induced false merges** — below ~8 px/staff-space (see §1).
7. **Ossia staves** — sometimes joined by a dotted barline → fails a continuous
   test.
8. **Mensurstrich** — barlines only between staves; breaks reverse inferences.
9. **Single-staff systems** — systemic barline conventionally hidden.

## Recommended next steps (agent's, adopted into the plan)

1. Instrument first: per gap, log size, bridging-column x-positions, and whether
   it's a bracket-group boundary; test the family-boundary prediction. Decides
   everything. (Sweep already records most of this.)
2. Audit the x_start scan window (cheapest possible fix).
3. Detect brackets in `[x_start−1.5sp, x_start−0.5sp]` (Audiveris's approach).
4. Make connectivity constructive (union-find over connectors), no gap stage.
5. Add the positive header-column system-start test.
6. Pull the AudioLabs external GT.
7. Settle the era question empirically: x-histogram of gap-bridging columns per
   edition — single peak at x_start = family-broken; peaks at every barline x =
   full-height interior barlines.

## Addendum — publisher house styles: the literature is empty (which settles the method)

A dedicated sub-agent searched Gould (via Google Books snippets), the full
Sibelius Reference Guide 2024.3, LilyPond, Dorico, IMSLP publisher pages, and
Scoring Notes. Ted Ross / Gardner Read / Kurt Stone / Wanske were access-blocked.

**The central negative finding, stated plainly: there is NO documented
publisher-specific layout house style anywhere in the secondary literature** —
not for Breitkopf, Peters, Universal, Durand, Ricordi, Schirmer, Eulenburg,
Kalmus, Dover, or Boosey. Barline practice, bracket/brace style,
system-divider use, and systems-per-page all came back empty for every publisher.
**This confirms the project must be a measurement effort, not a literature one** —
exactly what the benchmark is. (The modern *normative* rules in the main memo
are well-sourced and unanimous; what's undocumented is any *deviation* by house.)

### What IS measurable — era/format discriminators to tag pages with

These let us stratify by *engraving era/format* even when the publisher string is
unknown or unreliable:

1. **Bracket-extent and barline-join-extent are two SEPARATE observables.**
   Sibelius states they often diverge; Gould's timpani and divided-string rules
   are cases where they do. Our detector should measure both, not assume the
   bracket bounds the barline group.
2. **Strongest era feature: brace-instead-of-sub-bracket on paired like
   instruments** (horns, Violin I/II). Two independent professional sources call
   the brace form "older"; Sibelius ships a "Draw as brace" switch to reproduce
   it. A brace (curved, non-column) at a same-instrument pair boundary = likely
   19th-century.
3. **Margin-label style**: traditional "2 Flutes" (counts instruments) =
   19th-century; modern "Fl. 1.2" = 20th-c.+ (Gould pp. 508–509). We already
   read margin labels.
4. **Page trim size** (well-sourced): ~185×135 mm European pocket score
   (Eulenburg/Philharmonia/Hawkes cluster) vs ~235×315 mm Dover/Kalmus American
   full-score reprint vs 11×17 in / A3 conductor's score. **Directly computable
   from the PDF mediabox** the sweep already records — a free stratifier.
5. **Line-thickness ÷ staff-space ratio distinguishes a re-engraved small score
   from a photo-reduced reprint** [agent inference from LilyPond optical-sizing
   docs]: a genuine small-rastral engraving is drawn proportionally heavier, so
   its line/space ratio is higher; a photographic reduction keeps the full-size
   ratio. We already retain measured line thickness (staff-frame retention work)
   — this becomes a reprint detector. Note it interacts with our
   target-pixel-height render normalization: normalizing height does NOT
   normalize this ratio, which is the point.
6. **Dating cues that survive scanning**: Peters "Edition Peters" page footer
   (from ~1894) + title-page colour periods; Breitkopf `B.###` / `W.A.M.###`
   plate prefixes; UE `U.E.` / Philharmonia `W.Ph.V.`; Eulenburg `E.E.` is
   **non-chronological — do NOT date from it**; Ricordi plate-before-publication
   lag.

### Concrete leads for our own corpus

- **Reprint→source plate mappings are documented by name, and several hit our
  library.** Dover Beethoven symphonies = **Litolff, Braunschweig** (our
  Beethoven cycle IS Litolff 1870 — so a Dover Beethoven and our scan share
  plates); Dover Brahms / Schumann / Schubert = **Breitkopf** Gesamtausgaben (we
  hold Breitkopf Brahms); **Dover Mahler 5 = C.F. Peters, Leipzig 1904, plate
  8951.** → **Lead on our UNKNOWN Mahler 5**: if Sean's `Mahler_5_.pdf` is the
  Dover reprint, the underlying engraving is Peters 1904 pl. 8951. A page-foot
  plate-number check on the scan would confirm it (photographic reprints keep the
  original plate number). Worth doing when we touch Mahler 5.
- **Ready-made engraving-comparison corpus with IMSLP ids** (from LilyPond's
  essay): Bärenreiter BA 320 (1950) & BA 5070 (1989), Henle 666 (2000),
  Breitkopf/Busoni 1894 = IMSLP #22081, Bach-Gesellschaft 1866 = IMSLP #02221 —
  known-provenance pages spanning engraving eras.
- **Unexploited lead**: the *G. Schirmer/AMP Manual of Style and Usage* (2001)
  is a real publisher house-style manual — orderable from Schirmer's rental
  dept, not online. The only publisher-authored style document found.

### Rastral ladder (Gould p. 482–483, matched exactly by Dorico presets)

Stave height mm by rastral: 0=9.2, 1=7.9, 2=7.4, 3=7.0, 4=6.5, 5=6.0, 6=5.5,
7=4.8, 8=3.7. Full scores sit at the small end (~4.8–3.7 mm); Sibelius
recommends **3–5 mm for orchestral scores**. Software staff-size defaults:
LilyPond 7.03 mm, Finale 8.47 mm, MuseScore/Sibelius 7 mm. Useful as detector
priors and as the physical basis for the ~2 px systemic-barline figure at
pocket-score size.
