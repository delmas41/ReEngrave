# Data the reader can use that does not come off the page

The score library, rosters, dossiers, the fact sheet and the conventions
registry. Moved out of `CLAUDE.md` §8 on 2026-10-13
(`docs/claude-md-migration-2026-10-13.md`).

- **The score library** (`library/`, catalog committed at
  `data/score-library/catalog.json`): 289 editions across 29 publishers,
  1,745 reference encodings, keyed on `work_id` = genre + number
  (`beethoven--symphony-5`), never the dossier id (`beethoven-sym5-mvt1`).
  Every fact carries `source_kind`: `catalog` (from IMSLP's work page --
  admissible in production, does not fall silent when the raster is bad),
  `page` (read off the plate -- an OMR output, refused as a second witness),
  `encoding` (from MusicXML -- a truth file, refused in any measurement
  path). Ingest: `python3 -m tools.library.ingest imslp <pdfs>`; downloads
  are manual through IMSLP's JavaScript gate (do not defeat it, pace
  requests). `verify` checks presence; nothing yet checks the mirror question
  (54 held editions were unindexed until 2026-09-20).
- **Rosters** (`works` tier, `edition_instrumentation`): what a work is
  scored for, parsed from the IMSLP page; N instruments is not N staves. The
  roster HOLDS over a whole work and costs nothing; instrument doubling is
  always within a family, so a known double is a confirmation, not a
  conflict.
- **Dossiers** (`data/dossiers/*.json`, 97 works, generated from MusicXML):
  meter, bar count, written clef and key per PART. `slot_facts_for_system`
  abstains unless part count equals staff count, i.e. on every condensed
  conductor's page -- which encoded part sits on which printed staff is a
  property of the engraving and is not in the file.
- **The fact sheet** (`tools/omr/factsheet.py`): auto-drafts 29-44 of ~55
  facts from catalog + dossier + record, a human corrects the rest, and every
  correction is recorded as a disagreement with a reader. It is the only
  rung by which a dossier reaches the pipeline (`--sheet`), and a supplied
  clef speaks GAPS ONLY. There is no `--dossier` and there will not be one.
- **The conventions registry** (`tools/omr/conventions.py`): which engraving
  convention each decision claims; the `conventions` check reports the
  entries read by nothing. The prose form is `docs/page-facts.md` and
  `docs/engraving-conventions.md`.
- **IMSLP's `image_type`** in the catalog is a crowd label; never key on it
  (`docs/detector.md`).
