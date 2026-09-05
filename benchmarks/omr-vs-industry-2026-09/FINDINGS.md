# ReEngrave vs industrial OMR — first measured comparison (2026-09-04)

Three outside engines ran on **the same 11 engraved fixtures** the headline
benchmark uses, scored by **the same musicdiff bridge** against the same
truths (`run_industry.py`, results in `results.json`). This is the comparison
published paper numbers cannot provide: a pooled OMR-NED is a property of the
work set it is pooled over, so the Audiveris 0.56–0.77 / VLM 0.90–0.94 figures
from LEGATO 2's paper (its own typeset corpus) and SMB's baselines (its own
685-page corpus) are context only.

## Headline

| system | pooled OMR-NED | edits | scored |
|---|--:|--:|--:|
| Audiveris 5.11.0 | **0.1252** | 2,569 | 11/11 |
| **ReEngrave** (default, `44a1745`) | 0.1306 | 2,745 | 11/11 |
| homr 0.7.0 | 0.3783 † | 2,780 | 4/11 |
| oemer 0.1.8 | 0.9801 | 18,461 | 11/11 |

**Audiveris — twenty years of industrial engineering — edges this pipeline by
4% relative on clean engraved orchestral pages, and each system wins where its
strengths are.** Per-work: ReEngrave 5, Audiveris 6, three of the eleven decided
by under 20 edits. Audiveris also runs ~20× faster per page (18–48 s vs our
minutes).

† homr's pool covers only the 4 works it produced output for and is dominated
by one garbage row (Mahler, 0.9731) — read its per-work rows, not the pool.

## Per-work (ours sorted best-first)

| work | ours | audiveris | oemer | homr |
|---|--:|--:|--:|--:|
| mahler-sym5-mvt1 | **0.0272** | 0.1241 | 0.9771 | 0.9731 |
| tchaikovsky-sym4-mvt2 | **0.0580** | 0.0598 | 0.9815 | failed |
| beethoven-sym5-mvt1 | **0.0595** | 0.0929 | 0.9802 | failed |
| bruckner-sym5-mvt1 | 0.0941 | **0.0649** | 0.9788 | failed |
| brahms-sym1-mvt1 | 0.1196 | **0.0805** | 0.9852 | failed |
| beethoven-sym3-mvt1 | 0.1294 | **0.0861** | 0.9760 | failed |
| mozart-sym41-mvt1 | **0.1447** | 0.1648 | 0.9780 | 0.2636 |
| mozart-sym40-mvt1 | 0.1772 | **0.0768** | 0.9788 | 0.1966 |
| tchaikovsky-sym6-mvt2 | 0.1916 | 0.1879 | 0.9851 | **0.0718** |
| brahms-sym4-mvt1 | **0.2238** | 0.2642 | 0.9751 | failed |
| dvorak-sym9-mvt4 | 0.3380 | **0.3357** | 0.9844 | failed |

## What the pattern says

- **We win the dense pages** — Mahler (0.0272 vs 0.1241, a 4.6× gap), Beethoven
  5, Brahms 4 — and the divisi-heavy Mozart 41. The mechanisms built for
  conductor-score texture (cross-staff arbitration, system grouping, tuplet and
  slur pairing over the staff) are exactly what a classical segmentation
  pipeline lacks.
- **Audiveris wins the cleaner classical pages** — Mozart 40 (0.0768 vs our
  0.1772, though ~41% of our charge there is the divisi voice-split convention,
  not recognition), Beethoven 3, Brahms 1, Bruckner 5. Its symbol recognition
  on clean typeset input is mature and fast.
- **Dvořák 9 is a tie at the top of both error lists** (0.3357 vs 0.3380, 239
  edits each) — two unrelated engines landing within 3 edits on the 3-bar
  fixture is evidence the *fixture's denominator* dominates that row, exactly
  as its ⚠️ flag in CLAUDE.md says.
- **oemer cannot compete on this corpus and the failure is architectural**:
  0.975–0.985 on every work. Its builder hard-asserts a 2-staff grand-staff
  layout (known since the 2026-07-11 survey); on orchestral pages it emits a
  collapsed reading. On its home texture (pianoform — most of SMB) it is a real
  system; that is a statement about corpus, not quality.
- **homr is the most interesting outsider.** Its MusicXML writer assigns one
  MIDI channel per part and crashes above the channel cap, so 7 of 11 works
  produce nothing. But on pages that fit, the transformer is strong — **0.0718
  on Tchaikovsky 6, beating both us (0.1916) and Audiveris (0.1879)** on what
  is our second-worst work. A transformer second-opinion on small-ensemble
  pages is worth remembering (AGPL, host-side only).

## Caveats — read before quoting

1. **Engraved only.** These fixtures are clean LilyPond renders — Audiveris's
   home turf and the easy half of our problem. The differentiating claim for
   this project is *scans* (the scan benchmark opened at 0.7960 for us);
   running Audiveris on the scan benchmark is the natural next measurement and
   has NOT been done.
2. **Configs differ in what they attempt.** Our row is the shipped default
   (direction reader on). All engines were scored on whatever they emit;
   musicdiff's symmetry rewards neither abstention nor verbosity consistently.
3. **One scorer, our implementation.** OMR-NED here is the repo's musicdiff 5.2
   bridge; SMB's own toolkit may differ in detail. Same scorer across all rows,
   so the *comparison* is internally valid even if absolute numbers shift under
   another implementation.
4. **Audiveris's process does not exit in batch mode on macOS** — the harness
   polls for the export and kills it (`run_audiveris`). Export completes in
   18–48 s; the hang is cosmetic.
5. **SMB corpus arm not yet run.** The public corpus
   (huggingface.co/datasets/PRAIG/SMB, CC BY 4.0, 685 pages) is gated behind an
   HF access request — Sean's account needs to request it. Textures are
   pianoform/monophony/quartet: no orchestral, so expect it to test the
   pipeline outside its specialty.

## Reproduce

```bash
python3 benchmarks/omr-vs-industry-2026-09/run_industry.py          # resumable
python3 benchmarks/omr-vs-industry-2026-09/run_industry.py --force  # re-measure
```

Engines: Audiveris 5.11.0 (`/Applications/Audiveris.app`, installed 2026-09-04),
oemer 0.1.8 (`~/Library/Python/3.9/bin/oemer`), homr 0.7.0
(`<main checkout>/.venv-homr/bin/homr`). Fixtures and `out/` are gitignored
build products; `results.json` is the record.

---

# Addendum, later on 2026-09-04 — the scan arm, the OCR decision, and current weights

## Scan benchmark: Audiveris measured, then our weights caught up

Audiveris ran on the five scored pages of `benchmarks/omr-scan-e2e-2026-09`,
same trimmed truths, same scorer (`run_audiveris_scan.py`,
`results-audiveris-scan.json`). Three operational findings first, because they
are part of the result: Audiveris **rasterizes PDFs at 300 dpi**, which drops
the small-format Litolff print below its minimum interline (fixed by feeding
page renders directly, at the highest DPI under its **hard 20-megapixel image
cap** — `input_dpi` recorded per row); its default **120 s per-step timeout
dies in CURVES** on the dense Breitkopf Brahms (raised to 900 s via
`-constant org.audiveris.omr.sheet.SheetStub.stepTimeOut=900`); and two of its
five exports **crash music21's makeTies** (overfull measures) and were scored
through a `makeNotation=False` pass-through re-serialization that adds/removes
no symbols. Out of the box it completes 3 of 5 scans; our pipeline completes
all five at defaults.

| page | ours (recorded, pre-hollow) | ours (graft09 weights) | audiveris |
|---|--:|--:|--:|
| Beethoven 5, low-res Litolff | 0.7119 | **0.7108** | 0.8492 |
| Beethoven 5, high-res Litolff | 0.7479 | 0.7595 | **0.7269** |
| Dvořák 9, Simrock | 0.5873 | **0.4310** | 0.5381 |
| Brahms 1, Breitkopf | 0.9351 | **0.9192** | 0.9268 |
| Mahler 5, Peters | 0.8149 | 0.6895 | **0.6534** |
| **pooled (5 rows)** | 0.7960 / 9,050 | **0.7482 / 7,864** | 0.7845 / 8,393 |

The recorded row is the canonical Sep 2 run — **pre-hollow weights**. The
graft09 arm pins `OMR_SCAN_EVAL_WEIGHTS` to
`hollow-graft-shift09-2026-09-04.pt` (the head-graft ship, commit `0e9f005b`,
not yet on main) and is recorded in the scan bench as
`results-graft09-arm.json`. **On current scan weights we lead Audiveris pooled,
3 pages of 5** — the hollow-notehead work closing exactly the `wrong note` /
`entire measure` deficit the category table below predicted.

Scan categories (recorded run vs Audiveris, `categories-audiveris-scan.json`):
both sides carry an **identical 2,676-edit `entire staff` floor** (the
condensation mismatch — no reader can move it); our deficit was missing notes
(+559 `wrong note`, +364 `entire measure`), Audiveris's was reading them wrong
(−290 `wrong note head` to its column, +46 hallucinated lyrics).

## OCR: measured both ways, left OFF

Audiveris with working Tesseract data (legacy+LSTM `eng.traineddata` — brew's
LSTM-only file fails with "legacy mode") scores **worse** under musicdiff on
the engraved benchmark: pooled **0.1252 → 0.1579** (2,569 → 3,331 edits),
mostly `wrong lyric` — it attaches read text as lyrics and every one is
charged. Its official rows therefore run OCR-off (its better configuration);
the OCR arm is preserved as `results-ocr-arm.json`.

## Standing after today

- **Engraved**: Audiveris 0.1252, us 0.1306 — 54 edits behind, and the entire
  gap is `wrong flag/beam` (ours 449 vs its 48; `categories-*.json`). A
  dedicated beam session is working that bucket in its own worktree.
- **Scan**: us 0.7482 (current weights), Audiveris 0.7845 — ahead.

---

# Addendum 2, 2026-09-04 evening — the widened scan pool reverses the scan verdict

The scan benchmark was re-stamped to **11 rows** on the integration line
(`ba3ad6a7`: the original five pages, their p2/p3 siblings, and a Bach
Brandenburg row; composed baseline tilt+choir ON, graft weights: **0.8303 /
35,046**). The Audiveris arm was widened to match (`scan-comparison.json`,
`results-audiveris-scan.json`).

**Over the same 10 rows both systems scored: Audiveris 0.7919 / 27,934 vs our
0.8345 / 28,849 — the 5-row lead did not survive widening.** Per-row Audiveris
wins 6, we win 4; it cannot process Bach at all (internal NPE in
`Measure.purgeVoices` — unrecoverable from outside), and Brahms p2 needed one
inexpressible duration snapped before musicdiff would type it (noted per-row).

The reversal's shape: our wins concentrate in FIRST pages
(984073-p1, Dvořák p5) and the added second pages go to Audiveris
(575951-p2 by 0.077, Brahms p2 by 0.195, Mahler p3 by 0.028). *A small pool
cannot falsify a story about its own pages* — the repo's corpus-widening lesson,
now paid on the scan side too. The next scan lever is attributing the
second-page gap (systems past the movement opening: carried meters, mid-page
lineups, tacet suppression) before believing any single mechanism.

Standing at end of day: **engraved ahead (0.1176 vs 0.1252, recorded on
`bc58defb`); scans behind on the widened pool (0.8345 vs 0.7919).**
