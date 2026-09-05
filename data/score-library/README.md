# The central score library

Every score this project uses now lives in one place, under one naming scheme,
with its provenance attached. Before this, scores were spread across
`tools/omr/training/data/imslp/`, `~/Desktop/gradus-vercel/public/scores/`, two
copies of `~/Documents/Gradus-Assets/Scores/`, and `~/Downloads` — and the same
file existed in up to four of them under four different names.

## Two halves

| | what it holds | what it answers |
|---|---|---|
| `editions/` | printed editions as PDF | what a *reader* sees — a publisher's engraving, its scan quality, its errors. **OMR input.** |
| `reference/` | MusicXML | what the notes *are*. **Ground truth** — the dossier generator and every accuracy benchmark read from here. |

A PDF and an MXL of the same work share a `work_id` and join on it.

## Where the files are

The store is **machine-local and gitignored** — 650 MB of PDFs and MusicXML.
It lives at `<repo>/library/`, or wherever `SCORE_LIBRARY_ROOT` points.

```
library/
  editions/<composer>/<work>/<composer>--<work>--<edition>--<source>.pdf
                             <same stem>.json        <- provenance sidecar
  reference/<composer>/<work>/<composer>--<work>--<movement>--<source>.mxl
                             <same stem>.json
```

`--` separates fields, single hyphens live inside a field, so a filename read on
its own still says what it is:

```
beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp575951.pdf
strauss--till-eulenspiegels-lustige-streiche-op28--aibl-1896--imslp19118.pdf
mahler--symphony-5--mvt1--gradus.mxl
```

The sidecar sits next to the file, so a score carries its provenance even when
it is copied out of the tree.

## What IS committed

`catalog.json` — the merge of every sidecar. The store is gitignored but the
catalog is not, because provenance is hand-curated and network-fetched: losing it
to a gitignore would cost real work, and with the catalog in git a lost store is
re-fetchable from the IMSLP URLs it records.

Absolute paths (`origin_path`, `duplicate_origins`) are stripped on the way in —
they describe one machine's folders, not the work, and were 40% of the bytes. The
count survives as `local_copies`.

On a fresh clone every entry is `missing`. That is the expected state, not an
error, and `verify` reports it separately from a checksum mismatch.

## Commands

```bash
python3 -m tools.library.ingest imslp ~/Downloads/IMSLP*.pdf   # provenance from the wiki API
python3 -m tools.library.ingest musicxml <dir> --source gradus
python3 -m tools.library.ingest pdf score.pdf --composer "Mahler, Gustav" --work "Symphony No.5"

python3 -m tools.library.ingest catalog      # rebuild this index from the sidecars
python3 -m tools.library.ingest verify       # present / missing / checksum-changed
python3 -m tools.library.ingest reorganize   # re-derive names, repair the layout in place
python3 -m tools.library.ingest refresh      # re-fetch IMSLP provenance for held files
python3 -m tools.library.ingest set <path> --composer "Liszt, Franz"   # correct by hand
python3 -m tools.library.ingest relink       # legacy benchmark paths -> store (symlinks)

python3 -m tools.library.ingest instrumentation          # backfill work rosters
python3 -m tools.library.instrumentation --page "<IMSLP page title>"   # one work

python3 -m tools.library.ingest edition-instrumentation \
    --availability benchmarks/omr-edition-instrumentation-2026-09/roster-availability-hints.json
python3 -m tools.library.edition_instrumentation --path editions/<...>.pdf   # one edition
python3 -m tools.library.edition_instrumentation --compare                   # offline verdicts
```

Everything is **copied, never moved** — the sources are working folders and an
import must not empty them — and deduplicated by SHA-256, so re-running an import
changes nothing. Importing the four overlapping Gradus trees yielded 1745 unique
reference files out of 4167+ candidates; the rest were recorded as extra origins
on files already held.

## Provenance

IMSLP gates *file downloads* behind a JavaScript redirect, but the wiki and its
MediaWiki API are open, so `tools/library/imslp_meta.py` reads publisher, plate
number, editor, scan type and upload date without touching that gate. Requests
are spaced (`--delay`, default 5s).

Which file on a work page an id refers to is read from the **rendered page**
(`<div id="IMSLP19118">` names its own `File:`), not guessed from the wikitext —
guessing picked a 2016 typeset for a 2006 upload of Mozart's first symphony.

## What a work is scored for

`catalog.json` also carries a top-level **`works`** map, keyed on the same
`work_id` the entries use. It holds facts that are true of a WORK rather than of
one file, so they are not copied onto each of its editions — today, one fact:
the instrumentation IMSLP states on the work page.

```json
"works": {
  "beethoven--symphony-5": {
    "work_id": "beethoven--symphony-5",
    "instrumentation": {
      "source": "imslp", "source_kind": "catalog",
      "imslp_page": "Symphony No.5, Op.67 (Beethoven, Ludwig van)",
      "imslp_revid": 3268151, "fetched": "2026-09-05",
      "raw": { "Instrumentation": "orchestra", "InstrDetail": "{{More}} piccolo, 2 flutes, …" },
      "roster_field": "InstrDetail", "dialect": "prose", "parse_rate": 1.0,
      "roster": [ { "kind": "instrument", "instrument": "Flute", "count": 2,
                    "text": "2 flutes", "lexicon_alias": "flutes" }, … ],
      "unparsed": []
    }
  }
}
```

**The raw string is the evidence; the roster is derivative.** `raw` is stored
verbatim, always, and an `InstrDetail` fragment the lexicon does not know lands
in `unparsed` with its own text rather than being forced to a nearest match.

⚠️ **`source_kind` is load-bearing and cannot be retrofitted.** `"catalog"`
means the fact came from a bibliographic source that is independent of anything
a benchmark scores against; `"encoding"` would mean it was derived from a
MusicXML file — which IS the benchmark truth, so a measurement path must not
read it. `validate_fact` refuses a fact that does not say which it is.

⚠️ **N instruments is NOT N staves.** This describes the work. A printed score
condenses (Flute 1+2 on one staff) and splits (divisi), and the condensed count
is a property of the *encoding*, not derivable from the page.

⚠️ **`works` has no sidecar to be rebuilt from** — it is network-fetched, which
is the same reason the catalog is committed at all. `rebuild_catalog` carries it
forward explicitly; nothing else in the rebuild path knows about it.

⚠️ **Two IMSLP pages can share one `work_id`.** Clara Schumann's Op.7 and Robert
Schumann's Op.54 are both `schumann--piano-concerto`, because `work_key` keys on
genre + number and neither title carries a number. The key is not forked for
this (see below for why title-keying is worse); a second page's roster is kept
beside the first as `instrumentation_conflicts` and neither is trusted.

## What one PRINTING is scored for

The work tier above is complete and generic, and it is **confidently wrong about
a real population of the PDFs we actually run OMR on**. Bruckner's symphonies
exist in versions with different orchestration; Mahler retouched Beethoven and
Schumann; publishers add, absorb and re-cast parts; and most starkly the same
`work_id` can hold a full score AND a piano reduction — same piece, entirely
different lineup. This store holds two of those already
(`handel--messiah` as a vocal reduction and as a lead sheet).

So `catalog.json` carries a second top-level map, **`editions`**, keyed on the
file's own `path`. Same fact schema, told apart by provenance.

| tier | source | coverage | authority |
|---|---|---|---|
| **work** (`works`) | IMSLP catalog | 223/223 | generic; right about the piece |
| **edition** (`editions`) | read from that edition's own pages | partial | authoritative **for this PDF** |

```json
"editions": {
  "editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf": {
    "path": "editions/brahms/…imslp317803.pdf",
    "work_id": "brahms--symphony-1",
    "sha256": "…",
    "instrumentation": {
      "source": "page", "source_kind": "page", "reader": "surya",
      "describes": "edition", "acquired": true,
      "score_type": "full_score", "score_type_field": "file_description",
      "roster": [ { "kind": "instrument", "instrument": "Flute", "staves": 1,
                    "count_printed": [2], "texts": ["2 Flöten"],
                    "staff_indices": [0] }, … ],
      "unparsed": [ { "staff_index": 5, "text": "(C)" } ],
      "raw": { "labels": [ … verbatim OCR, every staff … ], "page_index": 1 },
      "quality": { "acquired": true, "roster_page": 1, "yield": 0.857,
                   "system_staves": 14, "named_staves": 12, "page_staves": 27,
                   "pages": 86, "pages_tried": [ … ], "dpi": 300 }
    }
  }
}
```

⚠️ **A page-derived fact is a THIRD `source_kind`, `"page"`.** `"catalog"` is
bibliographic and safe for a measurement path; `"encoding"` is derived from the
MusicXML a benchmark scores against and is off limits. A roster read off the
edition's own raster is neither — it is an **OMR output**, so a path that scores
OMR must not read it back as truth either. The two refusals have different
reasons and only a distinct kind can say so. `validate_fact` enforces it.

⚠️ **Neither tier may imply a staff count, and this is the tier that would be
believed.** An edition item carries `staves` (how many staves on the roster page
printed this name — an observation) **separately** from `count_printed` (what
the printed label itself claims, e.g. `2 Flöten` — a quotation). Nothing sums
one into the other. Brahms prints `1.Viol.` and `2.Viol.`: one instrument,
`staves: 2`.

⚠️ **The roster is ONE SYSTEM's, not one page's.** Brahms 1 / Breitkopf p.1 is
27 staves in two systems; reading the page reports Flute, Oboe, Clarinet … twice
over. The system with the most named staves wins.

⚠️ **`editions` has no sidecar either** — same trap as `works`, same fix:
`rebuild_catalog` carries both forward explicitly, and a test pins it. Catalog
schema 2 → 3.

**`quality` is an edition-quality index and nothing else in this project holds
one**: does this edition label its staves, on which page, at what yield, over
how many pages. Every field is a by-product of the read that had to happen
anyway.

**`score_type` makes an ARRANGEMENT a kind of edition, never a bad read.** A
piano reduction contradicting the work roster wholesale is the strongest signal
available that the PDF is not a full score — that is triage. ⚠️ IMSLP provenance
does not carry it for every file: 216 of the 235 held editions say only
"Complete Score", and the two non-full-scores are `source: local` with no
`file_description` at all, so the filename and variant slug are read too and
`unknown` is a legitimate answer rather than a default of `full_score`.

**The disagreement between the tiers is a first-class output.** "Work says 12,
edition reads 8" is three findings wearing one shape, and until this existed
nothing in the project could tell them apart. `compare_tiers` classifies each —
`agrees` / `edition_extra` / `edition_missing` (split by the read's own yield
into `read_incomplete` vs `variant_suspected`) / `doubling_suspected` /
`arrangement_suspected` / `no_edition_roster`.

**Measured 2026-09-05 over all 234 held editions**: acquired **189 (0.808)** in
68 minutes with 0 failures, **18 of them only on a page past p.2**. 181 rows are
comparable, and the mix — not the rate — is the result: 0.442 partial reads,
0.210 agree, **0.210 one lexicon word** (`Basso.` → Bass *voice*, 35 rows, the
only disagreement on 30 of them), 0.017 doubling, and **0 genuine editorial
variants** — all 9 `variant_suspected` rows were opened by hand and are movement
scope, condensation, an optional bracketed part, or an opera cast list. The full
reading, including why movement scope is a third systematic under-report, is the
module docstring of
[`benchmarks/omr-edition-instrumentation-2026-09/probe_tier_disagreement.py`](../../benchmarks/omr-edition-instrumentation-2026-09/probe_tier_disagreement.py);
`show_disagreement.py` prints one row's evidence from both tiers for a human.

⚠️ **`variant_suspected` means "worth a human", never "a variant"** — its
precision for a real editorial variant on this corpus is **0 of 9**.

⚠️ **The arrangement branch has never fired.** 2 of 235 held editions are not
full scores; a corpus that cannot express the case cannot price the rule.

⚠️ **A section is satisfied by a member, not expanded into all of them.** A work
roster says `strings` in one token and the page prints four or five staves for
it. Expanding the token would assert a lineup the page never stated; not
relating them at all would report every symphony in the corpus as a
disagreement.

## Five things that will bite

Each of these put a WRONG file in the library rather than merely a missing one,
which is the failure mode to watch for: the ranking still runs, still produces a
confident pick, and nothing looks broken.

**Filenames are case-sensitive after the first letter.** Berlioz's *Symphonie
fantastique* page carries both `Berlioz Symphonie Fantastique.pdf` and
`berlioz symphonie fantastique.pdf` — the autograph manuscript and the 1900
collected edition. A lowercasing match key collapsed them onto one entry and the
manuscript won. `_name_key` normalises spaces/underscores and the leading capital
only.

**`action=parse` returns the redirect STUB, not the target.** A guessed title
that happens to be a redirect yields no file blocks at all, so publisher, editor,
scan type and copyright are silently absent while the rendered page still lists
the files. Eighteen works were ranked on nothing; Mahler 1 got a manuscript
because the field that would have rejected it was invisible. `wikitext()` passes
`redirects=1` and follows `#REDIRECT` itself.

**IMSLP titles contain slashes.** `Symphony No.25 in G minor, K.183/173dB`
splits to `173dB (Mozart, Wolfgang Amadeus)` if you take the last path segment.
Every Mozart work with an alternate K number lost its provenance that way.
`page_for` strips the `/wiki/` prefix instead.

**Regional mirrors serve HTML, not PDFs.** `imslp.eu` and
`petruccimusiclibrary.ca` answer a non-interactive request with a landing page.
Twenty-six works across two rounds fell through to the next-best edition on their
page; all found a US-hosted substitute. `fetch.sh` rejects any non-PDF response
outright rather than storing markup as a score.

**Writes must be atomic.** Two overlapping `ingest` runs left a zero-byte sidecar
that took down the entire catalog rebuild. Sidecar and catalog writes go via a
temp file with cleanup on failure, one unreadable sidecar no longer aborts the
rebuild, and PDF metadata is sanitised — a Peters scan carries a NUL and an
unpaired surrogate in its title that `json` serialises and `utf-8` then refuses,
failing *after* the file is already copied in.

## Two more things that will bite

**Don't trust an embedded composer field.** The Mahler 5 export repeats
"I. Trauermarsch" as the movement title of *every* movement, one collection wrote
`Desktop` as the composer of 70 Bach chorales, and life dates arrive glued to the
name in every punctuation style there is (`Bach(1685 - 1750)` once made the store
grow a composer called `1750`). `reorganize` re-derives from the strongest
evidence available — a name a person supplied outranks the file's own metadata,
which outranks a folder name, and a folder name is only accepted if some *other*
file's metadata independently vouches for it.

**The legacy paths still work.** About 20 benchmark scripts hard-code
`tools/omr/training/data/imslp/<work>/pdfs/imslp-<id>/score.pdf`, and NOTES.md
quotes measured numbers from them. Those paths are now symlinks into the store,
recreated by `relink`. Don't delete them without re-pointing the benchmarks.
