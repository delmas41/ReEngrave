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
