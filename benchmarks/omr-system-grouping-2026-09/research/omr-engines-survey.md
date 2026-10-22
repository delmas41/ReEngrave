# How other OMR engines group staves into systems (Phase 1C, part 2)

2026-09-01. Engine survey (sub-agent of the conventions research agent). Tags:
(doc) = engine documentation states it, (src) = read from source code,
(not found) = checked and absent.

## The pattern across every engine that handles orchestral scores

**Bracket-anchored automatic grouping + a manual repair affordance.** No
shipping engine trusts pure automation on dense scores; every one that supports
orchestral input documents a way for the user to fix grouping by hand. Our
pipeline has neither bracket detection (repo-state §1.4 — the largest
unexploited signal) nor a repair affordance.

## Open-source engines

**oemer** (MIT): grouping inferred from barline information; piano-shaped —
`further_infer_track_nums` caps at **10 staves per system** (src); MusicXML
output carries no system breaks (issue #15, unanswered). Not a model for us.

**homr** (⚠️ **AGPL**): the closest existing implementation of
evidence-based grouping (doc+src):
- "Braces and brackets are identified to merge related staffs."
- Connection tests run **only between vertically adjacent staff pairs**; three
  tests — overlap of a detected connecting element **at bar lines / at clefs /
  at staff lines** — each thickening the candidate box and requiring overlap on
  BOTH staves; positive pairs become a `MultiStaff`; then transitive closure
  merges chains. No cap on group size.
- Note the difference from our rejected attempt 4: homr tests *pairwise overlap
  of localized connecting elements at specific anchors*, not an ink-fraction
  over a tall band.
- **License handling**: same pattern as LEGATO — if we ever run it, quarantine
  in `benchmarks/` as an out-of-process cross-check *miner*. Do NOT port or
  closely paraphrase its source into `tools/omr/`; design our rule from the
  documented behavior + first principles.

**Aruspix** — no grouping (16th-c. partbooks: one voice per staff) (src).
**Gamera MusicStaves** — staff-line finding/removal only; its "staff system"
phrase means one staff's *line count*, a terminology trap, not grouping (doc).
**Rodan/DDMAL chant pipeline** — single staff per line, nothing to group (doc).
**MuRET** — recognition unit is the staff; whether "system" is a region class
is unverified (paywalled), not a negative finding (doc).

## Commercial engines (public documentation)

| Engine | Automatic mechanism | Documented failure & manual fix |
|---|---|---|
| **capella-scan** | **"System Template"**: user selects per-staff identification criteria — **Bracket, Clef, Key** — explicitly for large orchestral scores where "all instruments may not be playing in each system"; "The larger the orchestra the more criteria you will need" | template edited by user; criteria chosen to be robust to misreads |
| **SmartScore 64** | **"Systems held by brackets"** | hole punches / faded lines break brackets → staves "become unlinked", appear as separate systems; fix = redraw bracket in Image Editor + re-recognize, or Part Linking tool (merge with next/previous system) |
| **ScanScore** | (unstated) | **documented over-merge causes: "vertical elements that appear to connect multiple systems"** — exactly our F1 — plus tight staff spacing and invisible connecting elements in PDFs; fix = System Editor (connect/disconnect staves) |
| **PhotoScore** | reads "where systems end"; 64 staves/page cap | no mechanism documented, no repair control found |
| **PlayScore 2** | unstated; no staff limit, playback degrades ">12 staves or so" | — |
| **Soundslice** | automatic staff linking | per-staff **"Starts new system"** toggle when linking is wrong |

Two design validations for us (doc):
1. **capella-scan's System Template is a user-supplied layout prior** — the
   commercial twin of our dossier/publisher-profile direction (Phase 4's
   "publisher profiles as dossier/catalog-supplied hints").
2. **SmartScore's documented failure direction is the mirror of ours**: it
   anchors on brackets and fails to *over-split* when brackets degrade; we
   anchor on gap connectivity and fail to *over-merge* when stray ink appears.
   A combined rule (bracket evidence + connectivity + repair affordance) is
   what the market converged on.

## Exchange formats — why engines skip systems

- **MEI**: no `<system>` container; `<sb>` is an empty milestone (doc).
- **MusicXML**: no `<system>` container; `<print new-system="yes">` is a layout
  hint; `<part-group>` encodes brace/bracket grouping at score level only (doc).
- Consequence: **neither export format can express per-system staff
  membership** — a structural reason several engines never build systems as
  first-class objects. (Our pipeline needs them anyway: measure extraction,
  dossier join, and clef inheritance are all per-system.)

## Addendum (2nd pass) — two fix-relevant ideas beyond connectivity

**1. MuseScore's experimental `omr/` module — the ONLY global joint formulation
found anywhere.** Its README ("Graphical Model for System Identification")
argues vertical-barline detection alone is unreliable, and solves grouping and
barline location **simultaneously**: with n staves there are 2^(n-1) gap-based
groupings; within a system "barline positions will be commonly shared (a very
strong and useful constraint!)"; solved by **nested dynamic programming**
`h(k) = max(h(i) + system(i+1..k))`, each hypothesized system scored by its
best-fitting shared-barline column configuration (optionally with negative
constraints from clefs/key-sigs/stems). A *wrong* grouping hypothesis is
penalized by its own inconsistent interior barlines — which is exactly the
signal our zero-tolerance rule throws away. Conceptually the strongest
alternative to both gap-distance and pure connectivity, and it dovetails with
the conventions memo: shared interior barlines are family-broken, so the
"shared column" score must be computed *per bracket group*, not per system.
(Source: MuseScore 2.x tree; authorship unverified; a candidate to prototype in
Phase 4, not to port.)

**2. Xu et al. 2026 (arXiv:2604.20522), a modern production pipeline** —
"For full scores, an additional staff-layout component can detect **left-side
brackets that define staff grouping**." Independent corroboration that
bracket-in-the-left-margin detection is the right full-score grouping cue
(matches Audiveris + SmartScore + capella-scan). No grouping accuracy reported.

Both reinforce the Phase-4 direction: constructive connectivity as the base,
explicit left-margin bracket detection for group boundaries, and — if a simple
rule still misses — a per-group shared-barline consistency score to arbitrate,
rather than a single global ink threshold.
