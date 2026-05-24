# IMSLP × symphony MusicXML pipeline — scores

Goal: assemble a training set where each work has (a) authoritative MusicXML as ground truth and (b) multiple IMSLP PDF editions across different publishers/eras. The XML back-labels structural classes (measure lines, stems, rhythms) on the PDFs, replacing hand labeling for those classes.

Background: parked write-up in [NOTES.md](../../NOTES.md). Limit — MusicXML rarely carries dynamics/expression/articulation, so this pipeline only helps **structural** classes.

---

## Already in the drop folder

[`fetch_openscore.py`](fetch_openscore.py) in this directory was run on 2026-05-23 and pulled the following from the [OpenScore Orchestral Corpus](https://github.com/MarkGotham/Hauptstimme) into [`tools/omr/training/data/imslp/`](../../tools/omr/training/data/imslp/):

| Composer | Works | Movements |
|---|---|---|
| Beethoven | Symphonies 1, 2, 3 (Eroica), 4, 5, 6 (Pastoral), 7, 8, 9 | 37 |
| Brahms | Symphonies 1, 2, 3, 4 | 16 |

53 `.mxl` files total, ~14 MB on disk. Scores are CC0 (per the Hauptstimme repo). One `source.yaml` per work documents where it came from.

Re-run anytime — the script is idempotent and skips existing files:

```bash
python3 benchmarks/omr-imslp-pipeline/fetch_openscore.py
```

---

## Drop folder layout

```
tools/omr/training/data/imslp/
└── beethoven-symphony-5/
    ├── musicxml/                       # already populated
    │   ├── mvt-1.mxl
    │   ├── mvt-2.mxl
    │   ├── mvt-3.mxl
    │   └── mvt-4.mxl
    ├── pdfs/                           # you create — IMSLP downloads go here
    │   ├── breitkopf-1862/
    │   │   ├── score.pdf
    │   │   └── metadata.yaml
    │   ├── peters-1888/
    │   │   ├── score.pdf
    │   │   └── metadata.yaml
    │   └── eulenburg-1932/
    │       ├── score.pdf
    │       └── metadata.yaml
    └── source.yaml                     # already populated
```

`metadata.yaml` template — capture this off the IMSLP page when you download:

```yaml
publisher: Breitkopf & Härtel
publisher_slug: breitkopf
year: 1862
plate_number: B&H 22.000
country: Germany
imslp_url: https://imslp.org/wiki/Symphony_No.5,_Op.67_(Beethoven,_Ludwig_van)
notes: ""    # revised edition, missing pages, etc.
```

`publisher_slug` + `year` are what the training pipeline will slice on (the publisher × era axis from NOTES.md).

---

## What you still need: IMSLP PDFs

Browse [imslp.org](https://imslp.org/wiki/Main_Page), find the work page, scroll the "Complete Score" section. Each scan lists publisher, plate number, year.

**Target per work: 3+ editions across ≥2 distinct publishers.** The transfer-learning hypothesis only pays off when publishers can be compared.

### Priority order

Start at the top.

| Priority | Work | Notes |
|---|---|---|
| **T1** | Beethoven Symphony No. 5 (Op. 67) | The anchor work — first to align end-to-end. |
| **T1** | Beethoven Symphony No. 9 (Op. 125) | Largest scale; stress test for alignment. |
| **T1** | Beethoven Symphony No. 7 (Op. 92) | Medium density. |
| **T1** | Beethoven Symphony No. 3 "Eroica" (Op. 55) | Wide era coverage. |
| **T2** | Brahms Symphony No. 1 (Op. 68) | Simrock 1877 — different publisher cluster. |
| **T2** | Brahms Symphony No. 4 (Op. 98) | Same cluster, later. |
| T3 | Remaining Beethoven (1, 2, 4, 6 Pastoral, 8) | Defer until T1+T2 end-to-end. |
| T3 | Remaining Brahms (2, 3) | Defer. |

---

## Also in Hauptstimme but not auto-fetched

The fetch script only pulls Beethoven and Brahms symphonies. If you want more, add to the `COMPOSERS` dict in [`fetch_openscore.py`](fetch_openscore.py). Also present in the repo:

- **Bruckner Symphony No. 5** — useful for late-Romantic publisher coverage.
- **Beach Symphony in E minor "Gaelic"** (Op. 32) — American 1896; tests A.P. Schmidt conventions.
- Bach B Minor Mass + Brandenburgs 3-4 — not symphonies; skip for this pipeline.
- Boulanger — short vocal works; skip.

---

## Works NOT covered by Hauptstimme

If you want these, you'll need authoritative MusicXML from elsewhere (community uploads on MuseScore are NOT reliable as ground truth — they must be proofed):

- **Mozart Symphony No. 40 (K. 550)** — check the [music21 corpus](https://music21.org/music21docs/about/referenceCorpus.html) or [MuseScore community](https://musescore.com).
- **Schubert Symphony No. 8 "Unfinished" (D. 759)** — small scale; consider deferring.

Recommendation: defer until the Beethoven+Brahms pipeline is end-to-end. 53 movements of authoritative XML is plenty to start.

---

## Where to get more MusicXML (general)

- **[OpenScore on MuseScore](https://musescore.com/openscore)** — the source for Hauptstimme. Free account required to download MusicXML; we used the GitHub mirror to avoid that.
- **[MarkGotham/Hauptstimme](https://github.com/MarkGotham/Hauptstimme)** — what `fetch_openscore.py` pulls from. CC0 scores.
- **[musetrainer/library](https://github.com/musetrainer/library)** — public-domain MusicXML, mostly piano repertoire. Limited symphonic content.
- **[music21 corpus](https://music21.org/music21docs/about/referenceCorpus.html)** — bundled with `pip install music21`. Strong on Bach chorales / Beethoven quartets; weak on full symphonies.
- **[PDMX dataset](https://arxiv.org/html/2409.10831v1)** — 250K+ MusicXML files scraped from MuseScore. Community quality varies — verify before using as ground truth.
- **[MusicXML.com sites list](https://www.musicxml.com/music-in-musicxml/)** — curated index.

---

## What to skip

- **Mahler / 20th-century scores** — copyright varies; fewer competing public-domain editions.
- **Chamber music** — too few pages per work for symphony-page training.
- **Operas, concerti, vocal works** — orchestration patterns differ; defer.

---

## Next step

Pull IMSLP PDF editions for the T1 set first (Beethoven 5, 7, 9, Eroica). Per work: 3+ editions spanning publishers, dropped into `pdfs/{publisher-slug}-{year}/` with `metadata.yaml`. Once T1 has PDFs in place, ping back and I'll start on the alignment-design phase (XML measure index → PDF pixel region), using Beethoven 5 as the anchor.
