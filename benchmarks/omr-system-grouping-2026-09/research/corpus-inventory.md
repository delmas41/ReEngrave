# Corpus inventory — publisher-stratified benchmark (Phase 1B)

2026-09-01. Produced by the corpus-inventory research agent (Sonnet). Read-only
survey of `~/Desktop/gradus-vercel/`, the ReEngrave main checkout (incl. git
history), `~/Desktop`, `~/Downloads`. No web access, nothing modified.

## Headline

**The benchmark corpus mostly already exists — it's just not merged and not
indexed.** A prior session built a provenance-tagged, deduplicated central score
library on the unmerged branch `claude/imslp-scores-central-library-ebe0fa` and
**actually ran the ingest**, leaving the real files on disk at
`/Users/seanjohnson/Desktop/ReEngrave/library/` (gitignored via
`.git/info/exclude`; data present, branch never merged):

- **122 scanned PDF editions** in `library/editions/`, each with a JSON
  provenance sidecar (composer, work, publisher, plate/year, editor, IMSLP id,
  page count, scan-vs-typeset) fetched from IMSLP's wiki API —
  **118 of 122 have a network-verified publisher/date**.
- **1,745 reference MusicXML files** in `library/reference/` (965 distinct
  works, 62 composers), deduplicated from four source trees including
  `~/Desktop/gradus-vercel/public/scores/`.
- **24 works with both a PDF edition and reference MusicXML**, joined on a
  shared `work_id`.

Path convention: `library/editions/<composer>/<work>/<composer>--<work>--<publisher-year>--imslp<ID>.pdf`
with a matching `.json` sidecar beside each PDF. The aggregate `catalog.json`
exists only inside the unmerged branch; the sidecars on disk are the source of
truth and carry the identical schema. All 122 page counts PyMuPDF-verified
against sidecars (0 mismatches).

Also found: **147 IMSLP PDFs in `~/Downloads/` (4.9 GB)** — 111 are the source
copies of already-ingested editions (ingest copies, never moves), **36 are not
yet in the library** (all with cleanly parseable IMSLP ids). The banned
Nottebohm scan is in Downloads (254 pp), is NOT in the library, and stays
excluded.

## Gradus (`~/Desktop/gradus-vercel/`)

- `public/scores/`: 557 `.mxl` + 3 `.musicxml`, **zero PDFs**. Its README is
  badly stale (documents 3 files vs 561 actual).
- **No publisher/edition metadata anywhere in Gradus** — its works database is
  Firestore-only (`lib/works/provider.ts`); the `Work` type has no
  publisher/year field. Print-edition truth lives only in the ReEngrave
  library sidecars.
- Extra: `books-pdf/mahler-5.pdf` — a second, independent Mahler 5 PDF, not
  cross-checked against the library's `unidentified-scan-2016` copy.

## Publisher histogram (122 editions)

| Publisher | PDFs | Pages | Works |
|---|--:|--:|--:|
| Breitkopf & Härtel (all variant strings) | **38** | **3,283** (31% of all pages) | 36 |
| Henry Litolff's Verlag | 10 | 861 | 9 |
| N. Simrock | 8 | 784 | 8 |
| Ernst Eulenburg | 6 | 1,069 | 6 |
| P. Jurgenson | 5 | 665 | 5 |
| Novello | 5 | 649 | 5 |
| Durand (& Fils / & Schoenewerk) | 4 | 604 | 4 |
| **UNKNOWN** | 4 | 816 | 3 |
| C.F. Peters | 3 | 389 | 3 |
| Universal Edition | 3 | 474 | 3 |
| Jos. Aibl Verlag (3 spellings) | 3 | 280 | 3 |
| Goodwin & Tabb; Wilhelm Hansen; BerliozComplete | 2 each | — | 2 each |
| ~21 singletons (Snortum typeset, A.P. Schmidt, Bessel, BrucknerAGA, Enoch, Fromont, Hamelle, Edition Peters Leipzig, Hofmeister, Kahnt, MendelssohnComplete, Augener, Éd. Russes, Belaieff, SchubertComplete, Lienau, Leuckart, Fürstner, Bote & Bock, Univerzitet Beograd, "2016" Boléro typeset) | 1 each | — | 1 each |

**UNKNOWN bucket:** both Handel Messiah arrangements (lead-sheet + vocal
reduction, non-orchestral), Kirchhoff, and — notably — **Mahler Symphony No.5**
(`unidentified-scan-2016--local.pdf`, 245 pp, from Sean's personal
Gradus-Assets folder, no IMSLP id).

**Publisher-string caveats:** raw IMSLP wiki text, unnormalized. Known-messy
rows: Sibelius Sym.2 = "(Breitkopf und Härtel from 1905)"; Smetana Má vlast =
literally `*`; Bruckner 8 = truncated MediaWiki markup; Weber Freischütz year
"1688" is an IMSLP data error (19th-c. print). Human-glance any publisher
string before trusting it as GT.

## Works with BOTH scanned PDF and reference MusicXML (24)

Full Beethoven 9-symphony cycle (all Litolff 1870) and full Brahms 4-symphony
cycle (B&H ×3 + Simrock Sym.2) covered on both sides. Also: Bach WTC I
(Snortum typeset), Bruckner 5 (AGA 1935), Dvořák 9 (Simrock 1894), Holst
Planets (Goodwin & Tabb 1921), Mahler 5 (unknown), Mozart 40 + 41 (B&H 1880),
Ravel Boléro (2016 typeset), Tchaikovsky 1812 + Sym.4 (Jurgenson) + Sym.6
(B&H). Strong for layout benchmarking; weak alone for isolating *publisher*
effects (each cycle is one publisher).

## Multi-edition works — the mixed news

**Zero true cross-publisher pairs inside the catalogued 122.** The four
duplicate `work_id`s are:

| Work | Pair | What it actually is |
|---|---|---|
| Beethoven Sym.5 | imslp575951 + imslp984073 | same 1870 Litolff plate, two scans — **scan-variance control**, not publisher pair |
| Brahms Sym.1 | imslp317803 + imslp516790 | same B&H Sämtliche Werke plate, two scans — same |
| Mozart Sym.41 | imslp73 + imslp984556 | same B&H 1880 plate, two scans — same |
| Handel Messiah | lead-sheet + vocal-reduction | different arrangements, not a publisher pair |

**One genuine cross-publisher pair is one step away:**

> **Mozart Symphony No.25, K.183** — library holds the 1880 **Breitkopf &
> Härtel Gesamtausgabe** (imslp57, 19 pp).
> `/Users/seanjohnson/Downloads/IMSLP849180-PMLP1544-Mozart,_Wofgang_Amadeus-NMA_04_11_Band_04_06_KV_183_scan.pdf`
> (20 pp, verified) is the **Neue Mozart-Ausgabe (Bärenreiter)** — the same
> symphony in a different engraver/era. Same notes, two publishers. The
> benchmark can reference the Downloads path read-only; no library mutation
> needed.

No other same-work match exists among the 36 not-yet-ingested Downloads files
(they are different works by held composers — Mozart piano concertos, Beethoven
concertos, Haydn 45/92/96/99/102, Bach Brandenburgs/B-minor Mass, etc. — good
future acquisitions, not multi-edition gold).

## Publisher-truth authority tiers

| Tier | Count | Path to truth |
|---|--:|---|
| Authoritative (IMSLP wiki API, in sidecar) | 118/122 | done |
| Filename id known, not yet looked up | 36 (Downloads) | run the branch-only `tools/library/ingest.py` imslp lookup (network) — an action for Sean |
| Absent, no id | 4 (2× Messiah, Kirchhoff, Mahler 5) | manual — ask Sean / read plate off the scan |

## Other findings

1. `data/score-library/wishlist.md` (branch-only, via `git show
   claude/imslp-scores-central-library-ebe0fa:data/score-library/wishlist.md`)
   is a hand-checked publisher-tagged table of the same 122 — worth merging the
   branch for it and for the full CLI.
2. `tools/library/` on main is a **half-merge**: `imslp_meta.py` tracked;
   `ingest.py`, `score_library.py`, `build_wishlist.py` branch-only.
3. ~20 benchmark scripts hard-code legacy paths
   `tools/omr/training/data/imslp/<work>/pdfs/imslp-<id>/score.pdf` — now
   **symlinks into `library/editions/`**. Deleting `library/` breaks them
   silently.
4. `backend/uploads/PMLP106104-Op.10.pdf` is an **IMSLP bot-check page saved as
   PDF** (1 page, "verify you are human") — janitorial delete candidate.
5. Nottebohm: in Downloads only, not in library, excluded. Two pre-ban
   artifacts still reference it by name (`omr-clef-geometry/nottebohm-p46-ground-truth.json`,
   `omr-system-grouping-2026-08/evidence/nottebohm-p90-staves.png`).
6. Gradus `public/scores/README.md` stale (3 vs 561 files).

## Full 122-row registry

Not duplicated here — regenerate any time from the sidecars
(`library/editions/**/*.json`); the sweep harness records
publisher/year/imslp-id per swept page from those sidecars. The agent's
PyMuPDF-verified row-by-row table (with per-work reference-MXL joins) is
preserved in the session transcript; key rows are already cited above and in
`repo-state.md` §5.
