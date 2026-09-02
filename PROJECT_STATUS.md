# ReEngrave — Project Status

**Last updated:** 2026-09-01 (accuracy has an outside reference point at last — pooled OMR-NED 0.3164 → 0.1439, slurs shipped after all; the clef benchmark that redirected the work; the first end-to-end run on a real scan; five branches landed)

This document is a snapshot. For day-to-day reference docs see
[CLAUDE.md](CLAUDE.md). For parked research ideas see [NOTES.md](NOTES.md).

---

## Scope

**Personal-use only** (re-affirmed 2026-05-24). Sean is the sole user. The Stripe payment gate and multi-user infra are already built but no longer the optimization target — design decisions should minimize complexity and ongoing cost, not maximize generality. The only acceptable interaction surface for new tooling is Claude Code itself (Claude sessions running locally, calling Bash / Python / YOLO). No new long-running services / MCP servers / HTTP proxy routes / UI surfaces unless Sean explicitly promotes them.

## TL;DR

ReEngrave has **two converged tracks** living together on `main`, plus an optional theory layer:

1. **A web app for music-score quality control** — upload a PDF, run OMR, review diffs, export. Auth + payments wired in. Built March 2026, iterated through April–May.
2. **An in-house YOLO + classical-CV OMR pipeline** — `tools/omr/`, fine-tuned on DeepScoresV2 (F1 98.8% on the Bach WTC verdict set). Built May 2026 across 49 commits / Phase 1 → Phase 4m.
3. **Maestro theory layer** (shipped 2026-05-24) — `tools/maestro_bridge/` (TypeScript, runs host-side via node/tsx) + `backend/modules/theory_layer.py`. Env-gated: harmony/rhythm validation, scholarly cross-check against 5 seed works, and in-pipeline pitch re-ranking with auto-correction (M4, local-YOLO pipeline only). See [docs/maestro-integration-plan.md](docs/maestro-integration-plan.md).

**Current activity (August–September 2026): the pipeline acquired a metric other people also report, and it has been rearranging the work ever since.** The arcs, oldest first:

- **July — deterministic verification layers.** Five internal-consistency checks (time-sig, rhythm sums, measure counts, transposition-aware key agreement, advisory clef-from-register) that ABSTAIN where detection is blind rather than guess. Two training experiments were run properly and **disproven**: ScoreAug/Augraphy domain augmentation made real-cell recall worse, not better, and fine-tuning the detector on clef cells collapses dense-page noteheads. Both are dead recipes; don't retry them.
- **August — a trusted Phase-1 baseline.** Layout had no regression baseline at all, which had blocked several fixes. Now: a hand-verified ground-truth fixture, a corpus probe, and xfails for known gaps. That unblocked real bugs — phantom staves, music deleted after a false barline, staff-line removal being a no-op on thick-line prints, body text detected as staves.
- **August — the header layer.** Clef *reading* is now measured rather than classified (alto/tenor/soprano are the same glyph on different lines, so no classifier can separate them), and key signatures are read by fitting accidental POSITIONS to the slot table for (clef, N) and reconciling across the page.
- **August — contextual analysis, and the over-detection bug it turned up.** The pipeline now knows *which staff is which instrument*: systems from vertical connectivity (43% → 86%), instrument identity from the PDF text layer and, for scans, from a margin reader, and stable part slots across systems and pages. Re-running the whole-pipeline validation for the first time since May then exposed the single largest accuracy bug in the project — `imgsz` was set so high the detector was reporting 2–4× the notes that exist. Fixing it took end-to-end pitch precision from **0.144 to 1.000** on the keyboard fixture.
- **August 29 — external truth, and an orchestral benchmark to prove it on.** The pipeline can now be given a **dossier**: the meter, measure count and per-part written clef and key signature of the work it is reading, generated from MusicXML rather than hand-authored (`tools/omr/dossier.py`, 97 orchestral movements in `data/dossiers/`). It both CHECKS a reading and SEEDS it — clef detection has resisted a fine-tune, ensemble voting and a CV locator, and none of that matters if the clef is simply known. Alongside it, `benchmarks/omr-orchestral-e2e/` renders a Gradus MusicXML excerpt back to PDF, so every note on a conductor's page is known by construction — the first note-level accuracy measurement on orchestral texture. On it, Beethoven 5 now reads **recall 1.000, precision 0.988, duration 1.000**, and Mahler 5 reports 24 notes against a truth of 24. Four defects were found and fixed by that benchmark alone: overlapping measure cells letting two staves each keep the same notehead, a beam counter with no upper bound (it reported eight-beam notes — a 1024th), a beam cluster tolerance sitting inside the duplicate mode, and a meter parser that wrote `<beats>686</beats>` into MusicXML.

- **August 30 — a crash, a diagnosis, and three ideas that did not survive contact.** A probe written for an unrelated feature found that `resegment_fused_measures` never got the one-line-staff filter its two sibling functions have, so a percussion staff of span 0 asked OpenCV for a 1x0 kernel: **3 of 13 pages carrying a one-line staff could not be transcribed at all**, La Mer p.25 among them — the very page that support was validated on. Separately, the key-signature "blindness" on Beethoven 5 p.15 turned out to be a **class-role mismatch**: the detector finds the flats at conf 0.25 and labels them `accidentalFlat`, and every key-signature reader consumes only `keyFlat`. Three fixes were then implemented, measured, and **not shipped** — majority-steered re-segmentation (inert on all 27 systems of the corpus), accidental-role recovery (−1 on the only ground truth), and a foot-of-system anchor for the dossier join (50/52 → 44/52). The measurements are the deliverable; see the benchmarks below.

- **August 31 → September 1 — the clef layer, and a benchmark that changed the target.** Nineteen commits. The CV locator's false positives went **48 → 13** across two scanned editions, by POSITION rather than shape three times over: margin ink is ink that ends before the staff's printed lines begin; an F clef's dots are the ones standing clear of the body. Nine other ideas were measured and refused, each with numbers on both sides — including a tenor symmetry floor that separated cleanly on one edition and overlapped completely on a second. Then the hand-read ground truth was widened from 4 pages to 10 (187 staves, 24 C clefs, four publishers), and it reversed two conclusions and reframed the work: **the locator supplies three staves of 166.** The end-to-end benchmark had been reporting 52/52 = 100% on three easy pages — a benchmark that cannot go down cannot show an improvement — and on hard pages it reads **87%**, rising to 90% with the paid margin reader. Seventeen of its twenty-one errors are the positional default calling a bass or C-clef staff treble, and the machinery to replace it (instrument → conventional clef, vetoed by register) works and is starved of instrument names. **Labels, not clef reading, are the binding constraint.** Full story: [benchmarks/omr-clef-session-2026-09/RETROSPECTIVE.md](benchmarks/omr-clef-session-2026-09/RETROSPECTIVE.md). Also: Nottebohm removed from every harness and test (orchestral scores only), and Surya installed as the free label rung. Final numbers on that corpus, after a tie at the paid rung was made to go to the paid rung: **149/166 with the vision reader, 146/166 free**, against 145 free with Surya absent — so Surya is worth keeping, and it also stopped the paid reader being called on every page and used on one. **The mechanism is still open**, but narrowed: Surya's presence moves three staves while returning byte-identical labels, and the obvious suspect — batch load perturbing the decode — was probed at 45 replays and **refused**, so Surya is a fixed function of its input and the free-path numbers stand.

- **August 31 → September 1 — accuracy acquired an outside reference point, and it found seven bugs in two days.** OMR-NED (*Sheet Music Benchmark*, ISMIR 2025) is the metric OMR papers report, and `musicdiff` computes it, so adopting it cost a bridge rather than an implementation. Pooled **0.3164 → 0.2263** on the engraved orchestral benchmark. **Four of the seven were export or resolution bugs on data the pipeline had already computed correctly** — beams detected and dropped, augmentation dots counted twice, dynamics dropped, tuplet markers sitting unread in the JSON — and *none of them was visible to any number this repository had before*, because note recall called the Beethoven page **1.000** throughout. The other three were all **placement**: two staff windows that had locked onto a beam and onto ledger lines, and a cross-staff rule that awarded a contested notehead to the nearer staff — which is precisely backwards, since an engraver opens the gap above a staff *for* its ledger notes. Then `wrong note`, 40% of the edit budget and never opened, was attributed: it is **rhythm and one staff**, and the part that disagrees in no pattern at all is **3.3%**. Nothing in it argues for detector work. An eighth fix then followed the same day: **slurs**, held back in August because a barline cuts an arc in two, shipped once the PAIRING moved from the measure to the staff — the event model itself needed nothing — taking pooled **0.2263 → 0.2209**.

- **September 1 — the first end-to-end run on a real scan, and it is a different problem from the engraved one.** Every accuracy number this project held had been measured one element at a time, or on pages it rendered itself from the same MusicXML it then scored against. Beethoven 5 p.1 of a 600 dpi IMSLP scan, defaults, no dossier (the dossiers are generated from the file used as truth, so seeding would hand the run its own answer key): layout exact at **113 staves over six pages**, step recall **0.742**, exact-pitch recall **0.579**, duration recall **0.340**, and **OMR-NED 0.8706** against 0.3164 on rendered pages. Four fixes followed — a header meter reader, barlines fitted with Theil-Sen through a page that warps 40 px, key-signature accidentals found by sliding Bravura templates, and parts stitched across systems in the exporter. The headline diagnosis is **not** a fix: **the page prints 68 half notes and the output contains 8**, because at 600 dpi bitonal the hollow notehead's counter has closed and the detector has no reason to call it hollow. An engraved control with the same music and the same weights finds 31 against 30 — so the rhythm layer is fine, and the lever is a labeling batch, which is prepared and waiting.

- **September 1 — the system-break rule got its fix after all, and then its end-to-end guard.** The 2026-08 verdict ("five attempts, all rejected, stop") was about threshold-style rules tuned on two editions. What worked was a different question: instead of asking whether ANY ink crosses a gap (the wide window, which stems and measure numbers fake out), a second **narrow scan at the system's shared left edge** — empty at a true boundary even when body ink bridges the wide window (cue A, from the Audiveris "starting column" idea). Union-only, and it may never create a size-1 system. Measured across 964 library pages: **27 over-merged symphony pages fixed : 1 mild residual (Mozart K22) : 0 size-1**, grouping eval **20/23 → 22/23**, default ON (`OMR_LEFT_EDGE_SPLIT=0` reverts). Then the gap in its measurement was closed: the orchestral OMR-NED fixtures are LilyPond renders whose systems are always grouped correctly, so cue A never fired on any measured fixture — `tools/omr/tests/test_left_edge_split_e2e.py` now pins it end to end on **four scanned pages, three publishers**, against hand-read truth (`benchmarks/omr-system-grouping-2026-09/gt/e2e-ground-truth.json`): split on, each page reads its true two systems with every staff carrying the system's full measure row; split off, the pages still merge — and merged, Eroica p.36 reads **10 measures where the page prints 16**, because a barline must span the whole merged block to survive the vote. Full story: [benchmarks/omr-system-grouping-2026-09/FIX_PLAN.md](benchmarks/omr-system-grouping-2026-09/FIX_PLAN.md).

---

## What works today

### End-to-end OMR (CLI)

```bash
python3 -m tools.omr.transcribe score.pdf --out out.json
python3 -m tools.omr.export out.json --format lilypond --out out.ly
lilypond out.ly  # → out.pdf
```

All 5 benchmark PDFs (Bach WTC, Mozart, Beethoven, Chopin, Debussy) produce LilyPond that compiles to PDF with **zero errors** — only bar-check warnings on measures whose summed durations don't match the time signature exactly. F1 98.8% on the 25-cell Bach WTC verdict set. See [`benchmarks/omr-phase4-session/retrospective.md`](benchmarks/omr-phase4-session/retrospective.md) for the full Phase 4 story.

### OMR-NED — the first number here that can be set beside someone else's

Every accuracy figure in this repository had been bespoke — F1 over 25 cells, pitch
recall on an authored fixture, clef accuracy over 52 hand-read staves — so *how good is
this pipeline* had never had an answer with an outside reference point. **OMR-NED**
(*Sheet Music Benchmark*, ISMIR 2025) is what OMR papers report and `musicdiff` 5.2
computes it, so adopting it cost a bridge rather than an implementation.

```bash
python3 -m tools.omr.omr_ned --bootstrap                 # once — builds .venv-omrned
python3 -m tools.omr.training.orchestral_eval --omr-ned
```

**Pooled 0.3164 → 0.1439** on the engraved orchestral benchmark, in two days. Lower is
better.

| step | pooled | edits | commit |
|---|--:|--:|---|
| baseline | 0.3164 | 2224 | `380a36b` |
| beams never exported | 0.3045 | 2140 | `d272ac3` |
| a staff window fitted onto a beam | 0.2716 | 1908 | `f2e1991` |
| augmentation dots counted twice | 0.2624 | 1819 | `52ba215` |
| dynamics never exported | 0.2595 | 1811 | `89277a2` |
| tuplets detected and never consumed | 0.2489 | 1743 | `d5079d5` |
| a staff window fitted onto ledger lines | 0.2449 | 1715 | `9276122` |
| cross-staff notes awarded by distance | 0.2263 | 1584 | `81446a0` |
| slurs rejoined across the barline that cut them | 0.2209 | 1563 | `bae93b1` |
| the crop's own edge read as noteheads | 0.2137 | 1508 | `77f796e` |
| a dot measured against its own bounding box | 0.1917 | 1355 | `b445e66` |
| a YOLO beam box bounds the stack, not a stroke | 0.1861 | 1315 | `cf559ca` |
| a stem capped at 6 staff spaces | 0.1601 | 1136 | `50a3920` |
| a beam bar counted from its neighbour's ink | 0.1506 | 1068 | `c62b372` |
| a chord's members given opposite stem directions | 0.1505 | 1068 | `de99318` |
| ink across the whole bar read as a beam | 0.1436 | 1018 | `e4ff44b` |
| a chord written top-down (see note) | **0.1439** | 1020 | `b8ccc89` |

Currently Mahler **0.0455**, Beethoven **0.1775**, Brahms **0.1804**.

The last row goes UP by two edits on purpose: OMR-NED sorts a chord's pitches
before comparing, so it is indifferent to writing a chord bottom-up, while note
recall on Brahms goes 0.917 -> **0.950** and its `exact` measures 76% -> 84%.
Read the two together, as this section says.

**Five of the eleven were export or resolution bugs on data the pipeline had already
computed correctly** — beams, dots, dynamics, tuplets and slurs. The lesson is written down
because it keeps paying: when a category is large, check whether the signal already
exists upstream before concluding that detection needs work. `grep -c beam
tools/omr/export.py` returned 0 while `beam_levels` sat on 271 noteheads. Three more
were *placement* — two staff windows fitted onto the wrong ink, and a cross-staff
rule that resolved contested glyphs by distance.

The last three were the same lesson in a third form: **a threshold written in the
wrong unit.** A notehead clipped by the crop was measured against nothing at all, a
dot against its own bounding box rather than the staff space, and a stack of beams
against a box that bounds the stack rather than a stroke. Every one of them was a
signal already on the page, and none needed the detector, the meter, or a wider
`_reconcile_measure_to_meter` — which was the recommended lever for the last two and
is not what was failing.

**Four ways to misread it**, each of which cost real time here:

1. **The metric is symmetric.** Swapping prediction and truth does not change the score,
   only which file is parsed strictly — which is why `score_pair` is keyword-only.
2. **`entire measure insert/delete` is amplified, not severe.** A measure differing only
   by a fermata is charged delete-whole-bar plus insert-whole-bar; 25 missed fermatas
   cost 128 of Beethoven's 240 edits. Open the op list before believing the severity.
   Confirmed by removal rather than argument — the bucket fell 705 → 482 when one
   misplaced staff was fixed.
3. **`wrong note` does not mean wrong notes.** musicdiff maps `noteins`/`notedel` to
   `wrong note` and `pitchnameedit` to a separate `wrong pitch`, which is **zero on all
   three works**. Balanced insert/delete means the aligner declined to PAIR two notes,
   and what usually stops it is the DURATION — so one misread rhythm costs about eight
   edits and files them under `wrong note`.
4. **It scores recognition AND export together**, and the engraved benchmark says
   nothing about scan robustness. Read it next to note recall, not instead of it.

Attributing that `wrong note` budget (`benchmarks/omr-ned-2026-08/`) is what ranked
everything since: rhythm 25.0%, directions and text 17.6%, one misfitted staff window
17.6%, notation on otherwise-perfect bars 17.5%, note count 14.4%, and **scattered with
no pattern at all — 3.3%**. The residue is systematic. Nothing in it argues for
retraining the detector.

### Cross-staff notes — three kinds of evidence, in the order a reader uses them

A measure cell is padded above and below so ledger notes are not sliced off, and on a
conductor's page those bands overlap, so the same ink is detected once per staff. The
old rule kept the copy on the **nearer** five-line band — which is wrong for exactly the
case the padding exists for, because an engraver opens the gap above a staff *for* its
ledger notes, so they sit nearer the staff above. Measured on Brahms: Violin 1's `A6`
and `B♭6` exported as `A♭1`/`B♭1` **on a timpani**, while Violin 1's bars 3 and 4 came
out empty.

**Distance is a fact about the page, not about how a note is read.** Three kinds of
evidence now apply in order:

1. **The ledger ladder**, about the glyph. A ledger note is joined to its staff by an
   unbroken run of ledger lines and joined to nothing the other way — the violin's cells
   carry three rungs per note-column at exactly its own 1st/2nd/3rd ledger positions,
   and not one rung between those notes and the timpani. **Completeness before count:**
   an unbroken ladder outranks a broken one however long, because a gap is what you see
   when the rungs belong to something else lying in the way.
2. **The instrument's written range**, about the part. Two Beethoven bassoon staves
   contested one notehead and distance kept `A♭1` — MIDI 32, below the bassoon's (34,
   72) — discarding a `C4` inside it. *A player cannot sound the note we chose.*
   `instruments.written_range` already carried this; what was missing was which
   instrument each staff is, and since the contextual pass names parts *after* the
   dedupe, the names come from the dossier on its usual terms — staff count must equal
   part count, else it abstains. **A veto on the impossible only.**
3. **Distance**, unchanged, as the tie-break. With neither ledger lines nor a dossier it
   is still the whole rule, so those pages are byte-identical.

```
pooled OMR-NED  0.2449 -> 0.2263     edits 1715 -> 1584
brahms          0.3657 -> 0.3302     recall 0.824 -> 0.909, precision 0.819 -> 0.890
beethoven       0.1714 -> 0.1775     (+8 — the bassoon pair, still open)
```

⚠️ **The cell pad is 4 spaces or 6, never in between.** Arbitration is useless if the
note is not in its own staff's cell at all, so the pad grows where the neighbouring
staff is more than 6 spaces away — and it must not grow otherwise, because **cell height
is coupled to `OMR_IMGSZ`, so it moves DETECTIONS and not just crops**. A flat 6 costs
Mahler and Beethoven (+20, +59); bounding the pad by the gap starves Mahler's cells of
their own stems (duration rate 0.864 → 0.455); and a marginal 4.0 → 4.6 growth costs the
authored `ensemble` fixture three notes of 45 for no gain.

Two rewrites were measured and rejected: one-winner-per-cluster is the tidier
formulation and scores *worse* (0.2275 against 0.2263), because IoU overlap is not
transitive and chains distinct glyphs into one cluster.

### Tuplets — the signal was in the JSON and nothing read it

A triplet's noteheads are ORDINARY eighths on the page: the printed value is already
right, and the bracket says three of them occupy two's worth of time. So nothing is
re-read — `duration_beats` is multiplied by 2/3 and `duration_type` keeps the written
value, which is what MusicXML's `<type>` and LilyPond's `8` both want inside a tuplet.

All 15 of Mahler's wrong durations were one triplet figure read straight five times
over — 57% of that work's entire edit budget — while `tuplet3` and `tupletBracket`
detections sat in its JSON and `grep -ci tuplet` returned 0 in `export.py`, `rhythm.py`
and `transcribe.py`. Mahler **0.0826 → 0.0455**, duration rate **0.318 → 0.864**,
Beethoven and Brahms unchanged to the edit.

Two markers, read differently, because they sit differently on the page: the **digit**
is printed over the middle of its group, so its centre must fall inside the group; the
**bracket** encloses the group, so the group must fall inside the bracket — detected
brackets are far wider than the notes they cover (one measured 1846 px over a 478 px
group), and testing a bracket's centre rejects every one of them. Which notes belong to
the group is the **beam box**, not the marker.

⚠️ `export._compute_divisions` had to become an **LCM rather than a max**, and that is
load-bearing: a triplet eighth is a third of a quarter, and 16 thirds is not a whole
number. The LCM of powers of two IS their maximum, so tuplet-free scores get the
identical number — which Brahms's byte-identical output confirms.

### Slurs — paired over the STAFF, because the barline cuts the arc

Held back in August, shipped 2026-09-01 (`bae93b1`, re-measured on the post-ledger base
as `6f64bfa`). Cells are cut per measure, so a slur crossing a barline is detected as
**two arcs** — 120 arcs on the Brahms fixture against 82 slurs in the truth — and
emitting per measure wrote two slurs where the music has one, which is why
`export.annotate_slurs` sat implemented, tested and unwired since `89277a2`.

**The event model needed nothing.** A MusicXML slur may already open in one measure and
close in another, and LilyPond's `(` `)` never cared about barlines. What was
per-measure was the *pairing* — so `annotate_slurs_in_staff` runs once per staff in
**page pixels**, the only frame shared across cells, the same move
`transcribe._pair_ties_in_staff` makes for ties. **Pooled 0.2263 → 0.2209**, edits
1584 → 1563, `wrong slur` 81 → 61, Contrabass 7/7 exact. A slur-stripped truth scores
0.2171 and a perfect reader would land near 0.2121, so this takes about **38%** of what
slurs are worth here; the residue has the right note INDICES and the wrong pitches,
which is note recognition, not slur work. Beethoven and Mahler export
**byte-identically** — neither page carries a slur the detector reads.

Three constants, none of them tuned — each sits in a gap the measurement found
([SLURS_2026-09-01.md](benchmarks/omr-ned-2026-08/SLURS_2026-09-01.md)):

| what it decides | the two clusters | constant |
|---|---|--:|
| an arc was CUT by the boundary | 0.00–0.10 spaces vs 1.58 | 0.5 spaces |
| the two halves are ONE slur | 0.02–1.14 spaces vs 8.04 | 2.0 spaces |
| a notehead is UNDER the arc | 0.00–0.19 widths vs 0.32 | 0.25 nh widths |

⚠️ **The pad is what made the change real rather than cosmetic.** A slur is drawn
*between* its noteheads, so its ink stops inside both outer centres — unpadded, the
Contrabass read `n1 → n4` in every bar whose truth is `n0 → n5`. Merging *without* the
pad lowered the pooled ratio (0.2449 → 0.2436, pre-ledger base) while **raising** the
edit count and the `wrong slur` category — the metric's symmetric denominator rewarding
74 extra predicted symbols. That is **dilution, not recognition**: always read the edit
count beside the ratio. Both ends of a slur must also land in the same voice, because
MusicXML pairs `<slur>` within a `<voice>` stream — 3 of 75 straddled two voices and
left both halves unpaired, malformed rather than merely wrong.

A slur can also cross a **system break** (`annotate_slurs_in_slot`, `b95e558`), since
stitching made a part the same staff on every system. That junction is anchored on the
**first note**, not the cell edge — a resuming cell opens with a clef and key signature,
so the fragment begins ~5.3 spaces in — and heights compare relative to each staff's own
top line. Measured on the only multi-system fixture: 0.2416 → **0.2381**, orchestral
benchmark byte-identical. LilyPond deliberately never receives one — its slurs cannot
span two Staff contexts. See
[SYSTEM_BREAK_SLURS_2026-09-01.md](benchmarks/omr-ned-2026-08/SYSTEM_BREAK_SLURS_2026-09-01.md).

### Theory layer (optional, env-gated)

With `MAESTRO_BRIDGE_ENABLED=true`, OMR output is enriched with key detection, rhythm/beat-mapping validation, and a scholarly cross-check against curated reference analyses (5 seed works). With `MAESTRO_PITCH_RERANK_ENABLED=true`, ambiguous noteheads are re-ranked against the detected key during local-YOLO OMR and auto-corrected above a confidence threshold. Runs host-side (node/tsx + the `gradus` submodule) — **not available inside the Docker container by design** (personal-use scope; the container has no Node).

### Web app pipeline

```
Upload PDF → ReEngrave (pick: local YOLO or Claude Vision) → Review
  ├── Vision diff (paid)            — Claude Vision flags per-measure differences
  └── Theory check (free)           — music21 rhythm/range/enharmonic sanity
→ Export (musicxml | lilypond | pdf)

Parallel: Gradus Library
  ├── Upload master reference XMLs
  └── Multi-source comparison (2-6 XMLs, music21 measure agreement matrix)
```

Auth: JWT + httpOnly refresh cookie, 8-hr access tokens.
Payments: Stripe webhook, $5/score for Vision diff, admin-email bypass.

### Local YOLO pipeline modules (`tools/omr/`)

| Module | Function |
|---|---|
| `transcribe.py` | Entry point — PDF → structured JSON |
| `export.py` | JSON → LilyPond / MusicXML (incl. voice splitting via `<backup>`) |
| `yolo_detector.py` | ultralytics YOLOv8l wrapper |
| `line_detection.py` | Classical-CV stems + beams (Phase 4f) |
| `rhythm.py` | Note durations from notehead class + beam count + flag pairing + dots |
| `voicing.py` | Same-x notehead chord grouping + stem-direction voice splitting |
| `pitch_resolver.py` | Notehead y-position → diatonic pitch, with key sig + inline accidentals |
| `staff_detector.py` | 5-line staff detection via horizontal projection clustering |
| `measure_extractor.py` | Barline detection + canonical-cell extraction |
| `preprocessing.py` | PDF → PageImage (render, binarize, deskew) |
| `staff_line_removal.py` | Optional staff-removed cell variant |
| `system_grouping.py` | Systems from vertical connectivity, not gap size |
| `instruments.py` + `score_layouts.py` | Instrument lexicon + ten standard score orders |
| `staff_labels*.py` | Which instrument a staff is: text layer → Tesseract → Surya → Claude → human |
| `slots.py` + `contextual.py` | Stable part identity across systems; the contextual post-pass |
| `clef_geometry.py` / `clef_locator.py` / `clef_correction.py` | Clef by measurement, by CV, and from the instrument's range |
| `key_signature_*.py` | Signatures by slot geometry, by template match, reconciled by vote |
| `time_signature_locator.py` | Meter read from the header by composite Bravura templates |
| `dossier.py` | The work's own facts — checks a reading and seeds it |
| `omr_ned.py` | The published metric, out of process in `.venv-omrned` |
| `annotate/` | FastAPI labeling UI — triage mode + draw-from-scratch mode (2026-06-09) |
| `training/` | DSv2 prep + ultralytics training scripts |
| `tests/` | 1271 unit tests |

### The score library (`tools/library/`, new 2026-09-01)

One provenance-attached store instead of the same score under four names in four
trees. `editions/` is what a reader sees (OMR input), `reference/` is what the notes
are (ground truth), joined on `work_id` keyed on **genre and number, not title** —
which took measurable edition/truth pairs 1 → 8 on its own. The catalog currently holds
**235 editions and 1,745 encodings over 1,166 distinct works, with 27 paired** — 27,718
pages, of which 220 editions are scans of printed engravings, 6 are typesets and 9 have
no image type recorded. **No manuscripts**, which is the point: a manuscript is not what
this pipeline reads. 53 of the 235 carry a text layer (23%), which is the number that
decides whether instrument identity is free. The catalog is git-tracked; the 650 MB
store is not.

Four bugs found there are worth carrying, because **each installed a WRONG file rather
than failing**: case-insensitive filename matching collapsed Berlioz's autograph
manuscript onto the 1900 collected edition; IMSLP's `action=parse` returns a redirect
stub, so 18 works had no publisher or scan type at all and Mahler 1 got a manuscript
because the rejecting field was invisible; splitting the lookup URL on its last slash
broke every Mozart work with an alternate K number; and `cmd_reorganize` had a broken
tail that never showed because every run happened to need zero moves. The fetcher now
rejects any non-PDF response outright — regional linkhandlers serve a landing page to
non-interactive requests, which had quietly cost 16 works their best edition.

The ~20 benchmark scripts that hard-code `training/data/imslp/<work>/pdfs/...` keep
working: those paths are symlinks into the store, and `library_root()` resolves to the
main checkout from inside a worktree, so one machine keeps one store.

### Reading the staff header (`tools/omr/staff_header.py` + friends)

On by default in `transcribe`; `--no-header-reading` turns it off. No extra weights needed.

- **The header window is measured from the page**, not taken from the staff-start measure cell — on degraded prints that cell routinely begins *past* the clef. Measured over 26 pages of 20 scores, 233/455 staves have a clef inside their measured window (`benchmarks/omr-key-signature/probe_header_windows.py`).
- **Clefs are read by geometry** (`clef_geometry.py`) — which staff line the glyph is centred on. Exact rather than probabilistic, and it is the only thing that can separate alto from tenor from soprano. A classical-CV locator (`clef_locator.py`) finds C clefs the detector cannot see at any confidence.
- **Key signatures are read by position** (`key_signature_geometry.py`) and reconciled across staves and systems (`key_signature_vote.py`). Both the detector's markers and the locator's clusters go through the same vote.

**End-to-end clef accuracy is 90%, on a benchmark that can now go down.**
The old 52-staff set reported **52/52 = 100%**, and *a benchmark that cannot go down
cannot show an improvement either* — every page in it was one the detector already
reads. Widened 2026-09-01 to **166 staves over 10 pages and four publishers**
(`benchmarks/omr-clef-geometry/eval_pipeline_clefs.py --wide`):

| pipeline | correct |
|---|---:|
| free readers only (`--assist none`) | 146/166 (88%) |
| with the paid margin reader (`--assist vision`) | **149/166 (90%)** |

The error census is the finding, not the score:

| source | staves | correct |
|---|---:|---:|
| detector (measure cell) | 97 | 98% |
| **positional default** | **41** | **61%** |
| `detector_header` (header crop) | 12 | **100%** |
| dossier | 12 | 75% |
| CV locator | 3 | 100% |
| slot continuity | 1 | 100% |

Reading the header crop where the measure cell finds no clef moved twelve staves from
guessing to reading and **every one of the twelve is right** — but honest accounting
says it bought *one* staff, because the other eleven were trebles the positional
default would have got right for the wrong reason. Evidence rather than luck is still
worth having.

**Seventeen of the twenty-one remaining errors are the positional default calling a
bass or C-clef staff treble**, and the machinery meant to replace it — instrument →
conventional clef, vetoed by register — works and is *starved of instrument names*. So
**labels, not clef reading, are the binding constraint**, and two full days spent on the
CV locator bought three staves of 166. The widened corpus also overturned the
single-dot F-clef veto, which looked like a 13 → 5 win on the old set and cost five real
C clefs per false positive on this one: **a sweep corpus is built from the candidates
the locator fires on, so it cannot price what a rule costs.**

What moved the number was the part-to-staff join. A labelled staff now **pins** its
part and the aligner runs only on the spans between pins, taking Beethoven 5 p.48 from
**12/17 to 17/17** as printed — but pinning and the paired lexicon fix each make things
*worse alone* (11/17 and 10/17) and only win together.

On the older 69-staff corpus, which is still reported for continuity, the same work took
clef accuracy from 58/69 to **69/69** with vision labels and to **66/69** on the free
path — the latter via a Tesseract tier that cut API calls from several per page to
**one in the whole corpus**.

Measured, given a correct clef, on 42 hand-read orchestral staves: **18 correct / 0 wrong / 16 missed / 8 correct abstentions**. End to end on a clean engraving (Bach WTC p.17) 10/10. End to end on degraded orchestral prints it is far lower — 2 staves of 20 on Beethoven 6 p.2, none on Beethoven 5 p.2 — because a staff whose clef is only the positional default is skipped by design. **Key signatures inherit the clef problem, and clef coverage is the ceiling on both.**

### Contextual analysis — which staff is which instrument (`tools/omr/`)

A human reading a large score deduces most of it from context: which staves transpose,
what instrument order to expect, what the natural groupings are. The pipeline now does
some of that.

**It runs inside `transcribe` as of 2026-08-31** (`--no-contextual` opts out). Until
then `apply_contextual_analysis` was reachable only from benchmarks and tests, so the
clef figures this repository quotes described a path no transcription ever took. It is
a post-pass over the built page dicts — a clef hypothesis is arithmetic on
already-resolved pitches — so detection, rhythm and segmentation are untouched, and a
failure is recorded in `contextual.reason` rather than raised. The visible consequence:
a Beethoven 5 page with no text layer now exports as *Flute / Oboe / Clarinet /
Bassoon / Horn / Trumpet / Timpani / Violin / Viola / Cello* instead of
`Staff p47-s0-N`.

- **`system_grouping.py`** — systems from **vertical connectivity**, not gap size. A
  system break is a gap no vertical ink crosses, because barlines and the bracket run
  through a system and nothing runs between two of them. System-count accuracy **43% →
  86%** over 14 bracket-verified pages, and spurious single-staff "systems" 19 → 0. The
  same pass recovers the instrument-family grouping as `Staff.group_index` (verified on
  Beethoven 9: 4 woodwinds | 2 horns | 5 strings). The ground truth is now **23 pages
  over 5 editions** and connectivity + the left-edge split (cue A, 2026-09, default on)
  scores **22/23** on it — see the September 1 grouping entry above; the five
  threshold-style attempts that preceded cue A are in "Measured and held back".
  End-to-end guard on real scans: `tools/omr/tests/test_left_edge_split_e2e.py`.
- **`instruments.py` + `staff_labels.py`** — instrument identity from the PDF's text
  layer, free. 18/65 score PDFs had one on the old corpus and **53 of the score
  library's 235 editions do (23%)**; **79% of labelled staves resolve**. The
  lexicon maps a printed label to instrument, family, default clef, written range and
  transposition (`fifths_offset = -fifths(key_name)`). Scored against the `<part-list>`
  of 111 orchestral works in the Gradus MusicXML library — what engravers actually
  wrote, with no OCR in between — it reads **99% of 2,345 real part names**, and 95 of
  105 symphonic works come out in score order
  (`benchmarks/omr-score-order-2026-08/`). Monotone order turns out to be a sharper
  test of a lexicon than coverage, because a misread label usually still READS: `Basso`
  resolved cleanly and resolved *wrong*, and only the order showed it. The 10 that
  remain are real layout variation — voices printed below the strings, Tchaikovsky's
  banda — and are deliberately not encoded.
- **The label ladder, cheapest rung first** — text layer → Tesseract → Surya 2 → Claude
  → a human question. Each runs only where the one above came back empty, and the free
  rungs spend no budget.
  - **Surya 2** (`staff_labels_surya.py`, Apache-2.0, 650M on llama.cpp) reads the
    margin as accurately as `claude-opus-5` on everything free ground truth can check —
    **zero disagreements for both readers** — at **89% of the yield, for nothing**,
    1.5 s a system against about a cent. What it gives up is reach, not accuracy: Claude
    repairs a damaged label from the running order, and an OCR engine transcribes what
    is printed. Off unless `.venv-surya` exists, and `OMR_SURYA_KEEP_ALIVE=1` attaches
    to a resident server instead of re-loading the model (contextual pass 21.4 s → 6.9 s,
    identical output; the server holds 1.7 GB, hence off by default).
  - **Tesseract** (`staff_labels_tesseract.py`) transcribes the margin at **26/29
    labels**, but downstream that is 14/17 clefs against vision's 17/17 — one misread
    character (`Tr. Alt.` → `A.`) collapses a whole trombone block. Still worth it: the
    free path went 58/69 → **66/69** and the API is now called **once in the whole
    corpus**.
  - **`staff_labels_vision.py`** — Claude on the margin, opt-in because it costs money,
    bounded per *work* rather than per page since slots propagate one reading. Validated
    against the text layer as free ground truth: **25 agree, 0 disagree, 30 recovered,
    0 missed** on 76 staves.
  - ⚠️ **Measuring Surya exposed a bug in the crop, not in the reader**: `MARGIN_SPACINGS`
    was clipping first letters off spelled-out names ("Clarinetti" arriving as
    "arinetti"), which Claude had been silently repairing, so the damage was invisible
    for as long as a repairing reader was the only one. 14 → 20, free for the paid
    reader, and agreement with the text layer 91% → 94%.
  - ⚠️ **And a newly-readable page surfaces lexicon bugs that were dormant.** Beethoven 5
    p.48 went 0 → 12 labels and three resolved wrong at high confidence — `Tr. Alt.` →
    *Alto*, a singer. That is `instruments.lookup`, not the reader, so the paid reader
    returned the same answer. `Tr.` is Trombe **and** Tromboni, and the page settles it:
    a trombone section is scored by REGISTER and a trumpet section by number and key.
    Fixed, and `VOICE_QUALIFIERS` is now *derived* from the voice instruments' own
    aliases rather than hand-listed, which closes `Fl. Alt.`, `Cl. Alt.` and
    `Trb. Tenore` at the same time. Validated on **1,380 margin labels across 10
    editions**: 27 strings change, all of them `Tr.`+register, all to Trombone.
- **`slots.py`** — stable part identity across systems and pages, by **monotone sequence
  alignment**. Index matching fails because a system omits the staves of instruments
  tacet through it. **100% label purity**, 198/217 staves assigned.
- **`clef_correction.py`** — proposes a clef from the instrument's written range where
  no reader read one. Gated on `staff["clef_source"]` being absent, never on a scan for
  clef detections: the geometry readers emit no detection, so a scan would overwrite a
  confidently-read clef.

Benchmarks: `benchmarks/omr-system-grouping-2026-08/`, `benchmarks/omr-margin-labels-2026-08/`.

### Shipped 2026-08-30 — three recognition fixes, each measured

| change | measured |
|---|---|
| **Clef specialist wired and gap-filling** (`transcribe.py`) | Blind staves — where the positional default answers *treble* every time — **31% → 19% corpus-wide**, 420 of 1043 rescued over 3359 staves; **168 key signatures** newly read downstream. Per score: pastoral 45→10%, beet5 79→25%, lamer 59→27%. Four wiring defects fixed first, of which the DPI one was a **texture** bug, not scale: the canonical upscale factor is inversely proportional to render DPI, leaving the same glyph ~14× apart in sharpness. It fills gaps only — never overwrites a reader that spoke. |
| **Barline dedup by height** (`measure_extractor.py`) | Phase 1 loses **~1 measure in 15** on dense orchestral scans (Beethoven 5: 101 of 1572 missing; Pastoral: 91 of 1336). One cause fixed: the dedup kept the *leftmost* of two candidates within 60px, so a full-height note stem beat the real barline. A/B over 56 pages: **3 gained, 0 lost**, each verified by cropping the page. |
| **Violins are not a condensable pair** (`score_layouts.py`) | Canonicalisation collapsed "Violin 1"/"Violin 2" into a cheap same-name merge, so the aligner condensed the two violin sections and every string slot shifted. Beethoven 5 p.2: **8/11 → 10/11 slots**. |

### Clef ground truth now covers the pages that are broken

The 52-staff set (`eval_pipeline_clefs.py`) is all pages where the detector already
works, so a gap-filler measures **+0** there by construction — which is why the
specialist looked worthless for months. `eval_blind_page_clefs.py` is the
complement: two pages, two editions, where the shipped pipeline reads **no clef at
all**. Baseline **17/32**, specialist **25/32**; on Beethoven 5 p.48 alone 8/17 →
16/17, including both the alto and tenor trombone. **A benchmark can select
against the thing being tested.**

**This was the right instinct and it did not go far enough.** The same argument was
applied again on 2026-09-01 and the ground truth went to **166 staves over ten pages
and four publishers** (`--wide`), at which point the 52-staff set turned out to be
saturated at 52/52 and two conclusions drawn on it were reversed — see the header
section above. Beethoven 5 p.48 now reads **17/17**, reached by the part-to-staff join
rather than by the specialist. The lesson generalises further than it was first
written: **a corpus assembled from the cases a component fires on cannot price what
that component costs.**

### The part-to-staff join, measured for the first time (2026-08-30)

`dossier.join_parts_to_slots` gates every slot-level dossier fact and had only ever
been judged through the clefs it supplies. `benchmarks/omr-part-staff-join-2026-08/`
scores it directly against hand-read instrument-per-staff on three pages.

| page | no labels | perfect labels | as printed |
|---|---:|---:|---:|
| beet5-p2 (18 parts → 11 staves) | 10/11 | 11/11 | 10/11 |
| pastoral-p2 (15 → 10) | 3/10 | 9/10 | 9/10 |
| beet5-p48 (23 → 17) | 8/17 | **13/17** | 12/17 |

On the first two the algorithm is **sound and starved** — perfect labels make it
almost exact, and the missing evidence is the string section no edition labels. On
p.48 perfect labels do **not** rescue it, and that is the finding: three of four
errors are structural. The page prints `Timp.` then the trombones; the part list
has trombones *before* timpani. `align_to_layout` is **monotone**, so having
consumed Timpani it cannot go back and the trombones return `None` — costing
exactly the alto, tenor and bass clefs the dossier exists to supply.

Ranked: **order inversion** (structural, 3 of 17) → merge budget (1 of 11) →
singleton parts beside a conventional pair (2 of 17).

**Fixed 2026-09-01 by pinning.** A labelled staff pins its part, and the monotone
aligner runs only on the spans between pins — so an order inversion is bounded by the
labels either side of it instead of poisoning everything downstream. Beethoven 5 p.48
as printed **12/17 → 17/17**, and corpus-wide the join reads **69/69** with vision
labels. Three things that had to be right, all of them cheap to get wrong:

- **A pin fixes a BOUNDARY, not a run** — pinning has to leave the aligner free
  between pins, or it just relocates the inversion.
- **Never pin an ambiguous label** (`AMBIGUOUS_ALIASES` exists because `Tp.` and
  `Basso` genuinely are), and **never pin on clefs** — supplying clefs is the point, so
  that is circular.
- **Pinning and the lexicon fix each LOSE alone** (11/17 and 10/17 against a 12/17
  baseline) and only win together. The lexicon half is 10 corrections across 547 names
  over 97 dossiers, including a `normalize_label` that kept hyphens, so `A-Klar.`
  resolved to nothing — Mahler 5 p.4 went **9/17 → 17/17** labels and 12/21 → 21/21
  staves assigned on that one fix.

### Measured and held back (2026-08-29 → 09-01)

Plausible improvements built and rejected on evidence. They are recorded because
the reasoning is reusable, and because several were proposed inside this
repository's own handoff notes.

| idea | result | why it failed |
|---|---|---|
| **Majority-steered re-segmentation** (`benchmarks/omr-majority-steering-2026-08/`) | shipped **inert** | 27 systems across 12 real pages, **0** with a staff disagreeing from its system's majority. The conservative pass has already done the work; there is no shortfall left to steer. |
| **Accidental-role key recovery** (`benchmarks/omr-keysig-blindspot-2026-08/`) | **not shipped**, −1 | Routing `accidentalFlat` into the key readers takes beet5-p2 from 10 correct to 9. The accidental set is noisier than the marker set, and it displaced a better CV-locator reading. |
| **Foot-of-system anchor** (`benchmarks/omr-margin-labels-2026-08/`) | **not shipped**, −6 | 50/52 → 44/52; the dossier went from supplying 1 clef at 100% to 11 at 27%. "The strings at the bottom are the same in every tradition" is about which *instruments* are there, not how many *staves* they occupy — divisi and condensation are the actual unknown. |
| **Slurs, emitted per measure** (`export.annotate_slurs`) | **held back, then shipped 2026-09-01 in a different form** | The hold was right: cells are cut per MEASURE, so a slur crossing a barline is detected as two arcs, and emitting per measure writes two slurs where the music has one — dynamics alone scored pooled 0.2595; dynamics + slurs 0.2598, `wrong slur` 76 → 97, +24 edits. What was per-measure turned out to be the **pairing**, not the event model, and moving it to the staff shipped as `bae93b1` (0.2263 → 0.2209) — see the Slurs section above. The arc-to-note mapping kept with its tests was indeed the correct half. |
| **The system-break rule, five attempts** (`benchmarks/omr-system-grouping-2026-08/`) | **all rejected** — later superseded by cue A, the left-edge split (2026-09, shipped default-on; see the September 1 grouping entry) | Rightmost-reach separated 262 boundaries with ZERO overlap and scored 14/14 — then over-split **12 pages** outside the two Beethoven editions it was measured on (La Mer 1 → 16 systems). Two more ink variants and a bracket-only variant failed identically; instrument-label continuity's best variant makes 8 page-level errors against the shipped rule's 3. The mechanism: **orchestral engraving breaks barlines between instrument families, so what crosses a gap is a property of the edition's convention**, not of whether a system ends there. Two editions is not a sample. Kept: bracket-reach 0 is a NECESSARY condition (15/15 true breaks) and so a cheap first filter for some future combined rule. |
| **The single-dot F-clef veto** | shipped, then **reverted** | It looked like false positives 13 → 5 on the sweep corpora. On the widened unbiased corpus it costs **five real C clefs per false positive removed** (located C clefs 13 → 8). **A sweep corpus is built from the candidates the locator fires on, so it cannot price what a rule costs.** |
| **`slot_continuity` for the clef** | **dead, structurally** | Beethoven 9 p.60's true system break scores 324 bridged columns against a within-system median near 120 — inverted. And fixing it would gain nothing, because the same slot fails in every system it appears in. |
| **A conventional cello-and-bass merge** | **rejected a second time** | Beethoven 5 p.2 10/11 → 11/11, but the Pastoral join 10/10 → 5/10 and the corpus 69/69 → 65/69. The span bounds *how many* condensations happen, not *which*. |
| **Cut common time** | measured and **withheld** | A C with a stroke correlates with any vertical ink crossing any rounded blob, and claimed a meter on seven systems that print none, at 0.51–0.56 over a 0.50 threshold. No page in the corpus prints a real one to measure against. Plain C ships: 8 correct, 0 wrong, 21 correct abstentions. |
| **Key-signature inference and cross-system carry** | both **refused** | Each breaks Bach WTC p.17, the cleanest page in the corpus: inference turned five template matches into seven sharps, and carrying a reading across systems propagated one spurious fifth sharp onto every treble staff of all five systems (10 correct → 5 correct and 5 wrong). **A wrong signature costs more than a missing one**, so the reader speaks only into gaps. |
| **Four attempts on the hollow noteheads** | none shipped | Ink-fill reclassification (nothing to reclassify — 129 of the 159 existing boxes measure above 0.9 fill), enclosed-white counters (**662 candidates for 68 notes**), Bravura `noteheadHalf` template matching (15 of 68 at threshold 0.50 and none above it), and ink thinning (4 hollow → 9 on staves holding 26, while inflating `noteheadWhole` 1 → 5, which is a different wrong duration). Explicitly **not** ink-degradation augmentation — already disproven on this exact gap. |
| **Phase-1 geometry driving staff-line removal** | **disproven** | Feeding per-staff thickness and wander into removal in place of the constants moves cleared% by **−0.7 to +0.2**, worse on three scores of five. The two estimates agree closely enough that there is nothing to gain — median disagreement 2.4–7.3%. |

Two related ceilings were also measured. The **margin-label lever is closed**: the
vision reader scores 5 of 5 on what the Pastoral prints, and that edition labels
winds and horns on every page and never a string, so no better reader can obtain
the label the dossier join needs. And the **one-line-staff audit** established the
rule that anything which *measures* such a staff must skip it while anything that
*counts* it must not.

### Dossiers and the orchestral benchmark (2026-08-29)

```bash
python3 -m tools.omr.training.build_dossiers            # 97 works -> data/dossiers/
python3 -m tools.omr.transcribe score.pdf --dossier beethoven-sym5-mvt1
python3 -m tools.omr.training.orchestral_eval           # note accuracy on a conductor's page
```

| work | parts | measures | notes (omr/truth) | recall | precision | duration |
|---|---|---|---:|---:|---:|---:|
| beethoven-sym5-mvt1 | 18/18 | 8/8 | 82/81 | **1.000** | **0.988** | **1.000** |
| brahms-sym1-mvt1 | 21/21 | 7/7 | 508/505 | 0.717 | 0.713 | 0.865 |
| mahler-sym5-mvt1 | 38/38 | 8/8 | **24/24** | 0.917 | 0.917 | 0.318 |

**Read that table with its caption.** These are **LilyPond-ENGRAVED** renders of
8, 7 and 8 bars from each movement's opening, with the work's parts on their own
staves 1:1 — 81, 505 and 24 truth notes. They measure recognition on clean
engraving, and **nothing in this repository measures note accuracy on a real
SCAN**. The 1.000 is not comparable to the corpus sweep's `beet5` row (19% clefs,
79% defaulted): that row is a different PDF — a scanned pocket score at 600 DPI —
and the two have been mistaken for each other.

Facts are stored as **written** pitch, so a transposing staff needs no
correction. Slot-level checks abstain unless the parts join the page's staves;
forcing that join measured F1 0.064 and must not be retried. The MusicXML feeds
verification and benchmarking, **not** label generation.

Two cautions carried out of that work. The benchmark's paper size must scale
with the part count — rendering 38 parts on A4 leaves ~1 staff-space between
staves and manufactures a failure mode that does not exist
(`STAFF_LADDER_PHASING.md` records the wrong diagnosis it produced). And
`rhythm.py`'s tuning comments assume a canonical line spacing of 24–48 px; it is
**100**, so re-derive rather than scale when touching those constants.

### The first end-to-end run on a real scan (2026-09-01)

The sentence above — *nothing in this repository measures note accuracy on a real scan* —
is no longer true. `benchmarks/omr-first-run-2026-08/` hands the pipeline Beethoven 5
p.1 of a 600 dpi IMSLP scan at defaults, **no dossier** (the dossiers are generated from
the file used here as truth, so seeding would hand the run its own answer key), and the
page's ground truth is established without the pipeline.

| | opening | after the session's four fixes |
|---|--:|--:|
| staves / systems / pages | 113 / 11 / 6 exact | unchanged |
| meter | 4/4 written onto a 2/4 page | **2/4**, and carried to all six pages |
| barlines | 4 of 17 missed | **17/17, 0 false, 16 measures of 16** |
| key signatures | 2 of 12 | **7/12 correct, 0 wrong** |
| step recall | 0.742 | — |
| exact-pitch recall | 0.579 | **0.619** |
| duration recall | 0.340 | 0.381 |
| OMR-NED | **0.8706** | — |

**0.8706 against 0.3164 on rendered pages**, and it is explicitly *not yet* a tracking
number — read it as a starting point, not a regression baseline.

Four fixes, each with a lesson attached:

- **A header meter reader** (`time_signature_locator.py`). A time signature's placement
  is rigid — numerator in the upper two spaces, denominator in the lower — so its
  vertical position is known before the search and the search is one-dimensional.
  Composite Bravura templates slid in x, voted across the system, on a corpus
  deliberately half pages printing no meter at all: **4 correct, 0 wrong, 12 correct
  abstentions**. The page vote now counts **staves, not measures**, because a meter is
  carried onto every later measure of its staff — which had turned one 0.42-confidence
  box on one staff of nineteen into eighteen unanimous votes.
- **Barlines through a warped page.** One barline's x drifts monotonically by up to
  **40 px** top to bottom, over three times the clustering tolerance, so the fit follows
  the line — **Theil-Sen, not least squares**, because a note stem near the column joins
  the cluster and votes too. The cost is recorded rather than buried: re-cutting the
  fused cells changes the crops the detector sees, so noteheads went 170 → 159 and
  exact-pitch recall 0.612 → 0.571 on that page.
- **Key-signature accidentals by template match** (`key_signature_template.py`). The
  clef gate was the obvious suspect and was **not** the cause: given the correct clef
  for every staff, the existing locator still reads 2 of 12, because it finds
  accidentals by clustering ink and this scan leaves every glyph in pieces. A shattered
  glyph still correlates with its own outline. Standalone, given the clef: **11 of 12**.
- **Parts stitched across systems** (`export.to_musicxml`). It had been emitting one
  `<part>` per (page, system, staff), so a part was never continuous and two pages of a
  prelude came out as twenty-four parts of three bars. **This is why OMR-NED could not
  be read on anything longer than one system** — the benchmark had been shaped around
  the exporter's limitation. Staves now join by ordinal, and **refuse where the join
  cannot be proven** (two systems of eleven and eight staves → no stitch, visibly, in
  the part names). Bach WTC I Fugue 1: 20 parts of 3 measures → **2 parts of 27**,
  OMR-NED 0.9819 → 0.8668, and `entire staff insert/delete` 39.0% → 26.3%.

⚠️ **The ground truth was wrong before the pipeline was.** The first run scored the page
against seventeen measures; it has sixteen. The probe counted barlines as full-height
ink columns, and a 2/4's digits align into a column six pixels wide — exactly a
barline's width. All five tacet staves agreed, and **the agreement was worthless,
because they all print the same time signature and so all made the same mistake.
Agreement across staves cannot catch an error every staff shares.**

### The half noteheads are invisible — a diagnosis, not a fix

The largest single gap on that scan. Duration recall is **0.381** against a step recall
of 0.714, and twenty of the twenty-six errors are one shape: a half note read as
something shorter. **The page prints 68 half notes and the output contains 8.**

They are not misclassified — they are **not detected**. At 600 dpi bitonal on this print
the half notehead's counter has closed to a thin diagonal sliver inside an otherwise
solid head, and a detector trained on clean engraving has no reason to call that hollow.

**A control settles which layer is at fault**, which is the part worth keeping: same
music, same weights, engraved by LilyPond instead of scanned — **31 hollow noteheads
detected against 30 real ones, pitch recall 0.926 and pitch-and-duration recall also
0.926**. Every correctly-located note there carries the right duration. The rhythm layer
is fine. It also bounds what the meter work could ever have bought: a bar missing its
half note is not short by a beam level.

Four attempts to close it are recorded above under "Measured and held back". The lever
is a labeling batch, and it is prepared: **48 cells** from Beethoven 5 pp. 2/4/6 and
Boléro p.2, ranked by how far each bar falls short of its own meter — worth about **four
times uniform sampling** (20 of the top 20 by deficit contain a half note, against 5 of
a random 20). Its 262 pre-labels contain **zero hollow noteheads**, which is the batch's
whole reason to exist: the model boxes what it can see, and what it cannot see is
exactly what a human has to draw.

⚠️ Pre-labelling ran at **`imgsz` 512, not the 2048 the labeling doc still recommends** —
that recommendation predates the per-cell scale fix, and 2048 reproduces the detection
flood the doc then tells you to filter back out.

### Hand-labeled training data (`data/user-labeled/`)

| Version | Cells | Content |
|---|---|---|
| `v1-2026-05-18-orchestral` | 60 | Beet 5 + Mahler 5 orchestral cells; cleaned 2026-06 to remove structural-element boxes (staff/stem/beam → background) |
| `v2-2026-06-08-beet5` | 37 | Beethoven 5 pp. 45–75; heavy FP-drop batch (480 FPs dropped, 37 FNs added) |
| `v3-2026-06-09-mahler5` | 35 | Mahler 5, draw-from-scratch |
| `v4-2026-06-10-la-mer` | 29 | Debussy *La Mer*, draw-from-scratch |
| `v5-2026-07-12-clef` | 15 | Phase-0 clef batch — Mahler, 15 clefs incl. 3 alto + 2 tenor |
| `v6-2026-07-13-clef-diverse` | 47 | Cross-score clef diversity — 10 alto, 10 tenor, 14 bass, 13 treble |

v5 and v6 sat on `clef-phase0-eval` as the only copy until 2026-08-29. **v6's
label images were symlinks into a gitignored `cells/` directory** — one `git
clean` from being labels with no images; they are real PNGs now.

`catalog.yaml` still unions v1–v4 only, deliberately. Adding 62 clef-heavy cells
narrows the density prior, and that is precisely what collapsed dense-page
noteheads 2506 → 114 in the clef fine-tune. Preserving labels and training on
them are separate decisions.

---

## The catalog-training experiment (2026-05-23 → 05-25) — concluded, not merged

The headline NOTES.md idea — *train YOLO from symphony MusicXML × IMSLP editions instead of hand-labeling* — **was executed** across Phases A–L on branch `claude/interesting-curran-3ca1b7` (43 commits, never merged to main). Outcome:

- **The catalog itself worked.** 65/65 IMSLP editions aligned to MusicXML (Phase D); per-cell YOLO label generation shipped (Phase E); 154k labels emitted across 26 movements (Phase G).
- **Training on it failed, repeatedly.** Phase H (catalog-augmented fine-tune): collapsed. Phase I (fixed a ~50px x-offset in catalog labels): still collapsed. Phase J (mix-mode, briefly promoted): Phase K diagnosed a class-ID collision with DSv2 and the collapse stood. Phase L (slot remap to DSv2-free slots): **still collapsed** on Beethoven 5.
- **Verdict:** catalog-augmented YOLO training is a dead end with the current recipe. Structural elements (stems/beams/barlines) stay with classical CV; symbol-class improvement comes from **hand-labeling via the annotate UI** (the current June work).

**Loose end:** `omr-weights/deepscoresv2-yolov8l-phase-j-mix-30ep.pt` (84 MB, from the collapsed Phase J run) still sits next to the production weights. **Do not use it.** Production remains `deepscoresv2-yolov8l-imgsz2048-ft-30ep.pt`.

The branch also carries **post-experiment OMR improvements that may still be valuable** (see "Unmerged work" below).

---

## Unmerged work on branches

Audit **2026-09-01**, verified with `git cherry` and by comparing file contents —
not by commit count, which lies here. Anything not listed is an archive of a
concluded experiment.

**The 2026-09-01 merge queue.** Five branches were integrated on
`integrate/land-2026-09-01` (74 commits ahead of the previous `main`), in this order:
`part-alignment-label-pins` → `omr-score-order-prior` → `omr-info-retention-erasure` →
`imslp-scores-central-library` → `pdf-mxl-pipeline-test`, then `main` merged back in to
pick up the cross-staff fix. Their content is described throughout this document.

**Promoted to `main` as `d83b07e` and pushed**, so `main` now carries the cross-staff fix,
the whole OMR-NED arc and all five branches together.

Two notes for whoever audits it next:

- `claude/omr-info-retention-erasure-c26534` contributed **nothing new** — both of its
  real commits are patch-identical to commits already on `main` (`git cherry` marks both
  `-`), and `main` additionally carries a re-baseline the branch lacks. Its merge was a
  no-op with an add/add conflict, which is exactly what a duplicated commit looks like.
- `claude/part-alignment-label-pins-978a57` was merged at `c520f1b`, **not at its tip**.
  Its remaining commits — the cold-start job briefs and the Surya determinism work —
  came in afterwards as `45b15f7` and `bd1e09f`.

| Branch | State | Disposition |
|---|---|---|
| the five queue branches above | **Landed 2026-09-01** | See the merge-queue note. |
| `claude/reengraved-score-evaluation-cd4c92` | **Landed** | The paper-size fix and the beam-dedup corrections are on `main`. |
| `claude/recognition-improvement-next-2f1709` | **Landed** | Nothing unlanded. |
| `clef-phase0-eval` | **Labels landed 2026-08-29** | v5, v6, three labeling batches (79 verdicts) and the audit tooling are on `main`. Its code half was redundant, its docs conflict with two months of newer files, and its weights stay unused. The branch is now an archive. |
| `claude/omr-clef-tenor-fixture` | **Superseded 2026-09-01** | Its one commit — *an F clef's dots stand alone; a C clef's lobes have company* — is the same idea that landed as `bebc50f` (false positives 21 → 13), measured on a wider corpus. The stricter single-dot form was then shipped as `d9c1a58` and **reverted** as `5bd0624`. Archive it. |
| `claude/omr-dossier-verification-layer-eaf6d0` | **The one open decision** | 4 commits, July. A *parallel* dossier implementation: hand-typed `tools/omr/dossiers/*.json` where `main` generates `data/dossiers/` from the Gradus MusicXML. Slice 1 (meter back-fill + column notation-math) is superseded, but **Phase 2/3 and dossier-steered re-segmentation — acting on a known bar count — have no equivalent on `main`**, whose `resegment_fused_measures` is driven by cross-staff consistency instead. Worth an assessment, not a merge: it has drifted seven weeks and uses a different data model. |
| `claude/interesting-curran-3ca1b7` | Archive + one live thread | Catalog experiment Phases A–L (concluded; do not retrain from it) **plus** 2026-05-25 `line_detection` improvements still worth a cherry-pick review. Its label-EMITTER half is validated prior art for MXL-guided auto-labeling. |
| `claude/scoreaug-fair-test-a2928e`, `claude/training-domain-augmentation-a29baf` | Archives | The two **disproven** training experiments. Do not deploy their weights; do not retry the recipes. |
| `claude/magical-bhabha` | 1 commit (March) | **Real MusicXML measure-level patching in `export_module`** — the #1 web-app TODO. Pre-consolidation code; evaluate against current `export_module`. |
| `claude/peaceful-kapitsa` | 1 commit (March) | SQLite-backed persistent job queue replacing FastAPI `BackgroundTasks`. Same: pre-consolidation; evaluate or discard. |
| `claude/quizzical-bell` | 1 commit (April) | The parked `/engrave` skill (Claude Vision-only OMR). Superseded; safe to delete. |

**Method note.** `git merge-tree <base> <a> <b>` — the deprecated three-argument
form — reports no conflict on trees that plainly conflict. It said `clef-phase0-eval`
merged cleanly; `git merge-tree --write-tree main clef-phase0-eval` correctly
reports conflicts in `CLAUDE.md`, `tools/omr/README.md` and `transcribe.py`. Use
the two-argument form, and check its exit code.

---

## What does not yet work / known limitations


- **Detection was massively over-reporting until 2026-08-28.** `imgsz` defaulted to 2048
  in the CLI and 1280 in the backend, and both were far too large. `imgsz` is now derived
  **per cell** (`yolo_detector.imgsz_for_cell`, targeting a shown staff space of 16 px);
  `--imgsz 512` is the best fixed value and `--imgsz 2048` reproduces the old behaviour.
  Anything measured before that date — notehead counts, "100% pitch coverage", the
  July confidence probe's false-positive flood — was measured through this and may need
  re-reading. `benchmarks/omr-imgsz-sweep-2026-08/findings.md` and
  `benchmarks/omr-detector-scale/RESULTS.md`.

  The mechanism is *not* that "ultralytics letterboxes to `imgsz²` regardless of cell
  size" — an early account that this document repeated. `predict` builds
  `LetterBox(imgsz, auto=rect)` and scales the **longest side** to `imgsz`, padding only
  to a stride multiple, so what the model is shown is
  `canonical staff space × imgsz / longest side of cell`. That depends on the cell, which
  is why the fix is a rule rather than a number: a constant lands inside the good band on
  wide header cells and past its edge on the narrow interior cells of the same page.
- **The F1 98.8% was never measured at a setting the pipeline used.**
  `training/eval_on_score_cells.py` calls `detect()` without an `imgsz`, so it ran at the
  wrapper's old default of **640** while the pipeline ran 2048. It now inherits the
  per-cell rule, so re-running it would produce a comparable number for the first time —
  but the quoted 98.8% still refers to the old 640 run, and is repeated unqualified
  elsewhere in this file.
- **Instrument identity needs a text layer, a local OCR pass, or a paid vision call.**
  53 of the score library's 235 editions have a text layer. Tesseract and Surya now
  cover most of the rest
  for free; the paid rung is down to one call in the whole corpus, but it is still what
  the last few staves need.
- ~~**One-line percussion staves are invisible.**~~ **Fixed 2026-08-28, extended
  2026-08-31.** The remaining cases were two ways of charging the same stray ink twice:
  a trill line printed between two percussion parts was dropped as a cluster interloper
  and then came straight back through `_has_the_rest_of_a_staff`. Boléro's snare part
  had been invisible on every page. Mahler 5 p.10 is now 20 staves of 20, and nine pages
  across three scores match hand-read counts.

**OMR**

- **Custom YOLO classes (barlines, textDynamic) caused catastrophic forgetting.** Phase 3.4 expanded `nc` from 208 → 214; F1 collapsed to 79.3%. Currently: barlines via classical CV; textDynamic not detected. Re-introduce when there are 200+ examples per new class or seed with synthetic warm-up. See `benchmarks/omr-phase3.4b/comparison-trained-v4.md`.
- **OMR time-signature digit detection is unreliable** — the DSv2 model often misclassifies digit glyphs, so `time_signature` is `null` for many pages. The deterministic layer (merged 2026-07-11) filters left-edge instrument-number misreads, propagates a detected C / cut-C, and back-fills from a per-column beat-sum vote, but abstains rather than guessing on dense pages. Root cause is a synthetic→real domain gap, not a threshold.
- **The positional default, not clef coverage, is the ceiling now.** It answers *treble*
  for **53 of 166 staves at 68% accuracy**, and is 17 of the 21 remaining clef errors.
  The CV locator is not the lever — two full days on it bought three staves of 166 — and
  the machinery that would replace the default (instrument → conventional clef, vetoed
  by register) works and is **starved of instrument names**. The fused-cluster branch of
  `locate_clef` was measured and is **not** a target: 0 of 47 too-big cells carry a C
  clef. Corpus coverage figures quoted before 2026-08-31 were computed on Nottebohm,
  which oversampled by roughly 4× (37.4% against the real orchestral 8.1%) and has been
  removed from every harness.
- ~~**The header clef is computed and then thrown away.**~~ **Stale — corrected
  2026-09-01.** The CV locator and the clef specialist both set `active_clef` and a
  `clef_source`, and `transcribe` writes both onto the staff, alongside
  `clef_overridden_by_dossier` where the dossier overruled a reader. Reading the header
  crop where the measure cell finds no clef is worth 8 more staves, and **all 8 of those
  reads are correct**.
- **The key-signature vote can be captured by a repeated misread.** Cross-system agreement is treated as corroboration, but a systematic misread — same engraving, same glyph, same print quality — repeats by construction. Measured on Beethoven 6 p.2: two systems of one misread viola staff set the page's modal reference and rejected the one correct reading on it.
- **Two training recipes are DISPROVEN — do not retry.** ScoreAug/Augraphy domain augmentation made dense real-cell notehead recall *worse* than the clean control (0.652 → 0.384 → 0.122), and was best on synthetic validation while worst on real pages. Fine-tuning the shared detector on clef cells fixes clefs and collapses dense-page noteheads (2506 → 114). See `benchmarks/omr-phase*/` and the branch archives.
- **Per-measure beat sums on busy keyboard music** are close to but not exactly the time signature — LilyPond bar-check warnings typically report fractional offsets (1/32, 3/32) rather than full-beat errors.
- **Dense orchestral conductor's scores** (Mahler 5, Debussy La Mer) have more false negatives on small dynamics + grace notes. Path forward: the active hand-labeling rounds via `tools/omr/annotate`.
- ~~**Cross-staff attribution of ledger notes.**~~ **Fixed 2026-09-01 (`81446a0`) — see
  below.** What remains of it: on Beethoven, one bassoon pair still resolves the wrong
  way in one bar while the identical bar beside it resolves right, so the pair ordering
  reaches the range veto inconsistently. Worth about 8 edits.
- **Half noteheads on scans whose counters have closed are not detected at all** — 68
  printed against 8 in the output on the first real-scan page. An engraved control with
  the same music and weights finds 31 of 30, so this is detection, not rhythm. Four
  approaches are closed; the lever is a prepared labeling batch.
- ~~**Slurs are detected and not exported.**~~ **Fixed 2026-09-01 (`bae93b1`) — see the
  Slurs section above.** The event model needed nothing; the pairing moved to the staff,
  in page pixels. What remains under the arcs has the right note indices and the wrong
  pitches — note recognition, not slur work.
- ~~**There is no text detection in the pipeline at all.**~~ **Direction text is read
  now, behind `--direction-text` (shipped 2026-09-01, `ceb6714`; current numbers
  `df16665`).** The words printed inside a system — `legato`, `Allegro con brio` — are
  read by subtracting every detection from the page's ink, OCRing what is left with
  Surya, and gating the result on a lexicon of musical terms, so the detector is never
  touched (`textDynamic` remains the class that caused the Phase 3.4 collapse). On the
  current base: pooled 0.1861 → **0.1624**, edits 1315 → 1171, `wrong direction`
  **151 → 7** — every direction on the benchmark is read exactly AND placed on the
  correct beat, and the 7 that remain are Mahler's `molto` (printed against the staff
  below, so the band never proposes it) and the `[` / `]` the lexicon refuses because
  they are not words. **Off by default** because it needs `.venv-surya` and spends
  ~9 s of OCR on a 21-staff page even with the server resident. ⚠️ The reader's own
  candidate/read/accepted counts are identical on all six bases it has been measured
  on while the pooled delta moved four times — the counts are the invariant, the
  pooled score is not. See
  [benchmarks/omr-direction-text-2026-09/FINDINGS.md](benchmarks/omr-direction-text-2026-09/FINDINGS.md).
- **`gap_bridging_counts` does not implement its own docstring.** The prose says the
  band runs from the top line of the upper staff to the bottom line of the lower, and
  argues the gap-only version fails on exactly Beethoven 9 p.25; the code measures the
  gap. Implementing what is written separates nothing, so it is unclear whether the code
  or the comment is wrong — and **the prose is confident enough that someone will trust
  it**.

**Web app**

- **MusicXML correction patching is a stub** on main. Accepted diffs are written as XML comments, not actual measure replacements. (An unmerged March implementation exists on `claude/magical-bhabha` — unevaluated.)
- **PDF.js crop region in `DiffCard` is incomplete** — full crop viewport implementation has a TODO.
- **No database migrations.** Schema changes require dropping the DB.
- **Background tasks use FastAPI `BackgroundTasks` (no queue).** Server restart during a long OMR job loses the job. (Unmerged March job-queue implementation on `claude/peaceful-kapitsa` — unevaluated.)
- **Frontend type field names still say "audiveris"** (`audiveris_confidence`, `min_audiveris_confidence`, `pattern_type: 'audiveris_failure'`). They now refer to the primary OMR engine; rename when there's a migration story.

**Theory layer**

- Host-side only (needs node/tsx + the `gradus` submodule); the Docker backend container cannot run it. By design under the personal-use scope, but worth remembering when a web-app OMR run shows no theory enrichment.
- M4 pitch re-ranking applies to the **local YOLO pipeline only** (Vision OMR emits no pitch candidates).

---

## How we got here — major milestones

| Date | Milestone |
|---|---|
| 2026-03-25 | Initial ReEngrave scaffold — FastAPI + React + Audiveris OMR + Claude Vision diff |
| 2026-03-26 | Auth (JWT + httpOnly refresh) + Stripe payments + Docker stack + 79 backend tests |
| 2026-03-26 | Production deployment stack (Traefik + Let's Encrypt) + restructured 3-step UI |
| 2026-04-06 | Spiked a `/engrave` Claude Code skill (Claude Vision OMR only) — parked when Vision OMR proved too inaccurate on orchestral scores |
| 2026-05-22 | Phase 4 session — built full `tools/omr` pipeline: pitch / rhythm / voicing / line detection / LilyPond + MusicXML exporters / 156 tests / real-world validation on 5 PDFs. F1 98.8% on Bach WTC verdicts. |
| 2026-05-23 | Phase 1 connectivity-aware barline acceptance for orchestral pages + cross-cell tie pairing + voice splitting via `<backup>` + octave-clef pitch support |
| 2026-05-23 | **Consolidation.** Pruned 460MB of stale benchmark overlay dumps, merged YOLO pipeline into main. Local YOLO becomes primary OMR engine, Claude Vision OMR secondary, Audiveris removed entirely. Gradus library + multi-source XML comparison + theory checks landed in the same merge. |
| 2026-05-23 → 05-25 | **Catalog-training experiment** (Phases A–L, branch `claude/interesting-curran-3ca1b7`): IMSLP × MusicXML label generation worked (65/65 editions, 154k labels); every training attempt collapsed (H, I, J, K, L). Conclusion: stick with classical CV for structure + hand-labeling for symbols. Never merged. |
| 2026-05-24 | **Maestro theory layer shipped** (M0–M4 + follow-ups A/B, on main): bridge CLI, harmony/rhythm validation, scholarly cross-check (5 seed works), in-pipeline pitch re-ranking with auto-correction, wired into both OMR engines behind env flags. |
| 2026-06-08 → 06-10 | **Hand-labeling round on Beethoven 5.** Draw-from-scratch labeling mode + box delete (commit 1fe5484). Label set `v2-2026-06-08-beet5` (37 cells) created; v1 cleaned of structural-element boxes. Batches: 05-24 ✅ (became v2), 06-09 ✅ (35/36, not yet converted), 06-10 in progress (21/36), 06-08 abandoned. |
| 2026-06-10 | **Process audit** — docs refreshed, stale worktrees/branches pruned, orphaned label data committed. |
| 2026-07-10 → 07-13 | **Deterministic verification layers.** Five internal-consistency checks merged (time-sig disagreement, column rhythm sums, cross-staff measure counts, transposition-aware key agreement, advisory clef-from-register) — a safety net that abstains where detection is blind. Capstone: `docs/internal-consistency-checks.md`. Also the `catalog.yaml` nc=208 cap + `train_yolo.py` nc guard, closing the Phase-3.4 silent-head-reset footgun. |
| 2026-07-13 | **Two training recipes disproven, properly.** A fair three-way fine-tune showed ScoreAug/Augraphy domain augmentation is *worse* than the clean control on real cells, and best on synthetic validation — i.e. synthetic validation is misleading here. Separately, clef fine-tuning fixes clefs and collapses dense-page noteheads. Both dead; the real levers are verification layers and real data. |
| 2026-08-28 | **Phase 1 finally has a trusted baseline** — a hand-verified ground-truth fixture, a corpus probe and xfails for known gaps. That unblocked fixes that had been parked for want of one: phantom-staff collapse, music deleted after a false barline, staff-line removal being a total no-op on thick-line prints (0.9% → 89.7%), and paragraphs of body text being detected as staves. |
| 2026-08-28 | **The staff-header layer.** Clef reading by geometry rather than classification (`clef_geometry.py` + a CV C-clef locator), key signatures by fitting accidental positions to the slot table and reconciling across the page (`key_signature_*.py`), both working from one measured header window (`staff_header.py`). 18 correct / 0 wrong on 42 hand-read orchestral staves given a correct clef; 10/10 end-to-end on a clean engraving. |
| 2026-08-28 | **Retuned against the new Phase-1 geometry, and found a live defect.** The gap-bridging x-extent fix broke an invariant the header window relied on; correcting it took the two orchestral ground-truth pages from 6 correct / 7 wrong to 18 / 0, and turned two *shipped* wrong key signatures on Beethoven 6 p.2 into two correct ones. Also fixed brace residue blocking the clef search (Nottebohm coverage 32 → 43 cells). |
| 2026-08-28 | **Contextual analysis + the over-detection fix.** Systems by connectivity (43% → 86%), instrument identity from the text layer and, for scans, a margin reader, stable part slots (100% label purity), clef from instrument range. Re-running the whole-pipeline validation for the first time since May found `imgsz` over-reporting notes 2–4×; fixing it took end-to-end pitch precision 0.144 → 1.000 on the keyboard fixture, and every metric on every fixture improved. Also disproved clef-from-key-fit with measurements. |
| 2026-08-29 | **External truth, and an orchestral benchmark to prove it on.** Dossiers generated from the Gradus MusicXML (97 movements, stored as written pitch, two check tiers that abstain unless the parts join the page), the meter→rhythm loop closed, and `benchmarks/omr-orchestral-e2e/` rendering a Gradus excerpt back to PDF so every note on a conductor's page is known by construction. System grouping fixed by a connectivity veto — gap distance provably cannot separate systems — taking Beethoven's measure count to 8/8 exact. |
| 2026-08-30 | **A crash, a diagnosis, and three ideas that did not survive contact.** `resegment_fused_measures` asked OpenCV for a 1×0 kernel on one-line staves, so 3 of 13 such pages could not be transcribed at all. Majority-steered re-segmentation, accidental-role key recovery and a foot-of-system dossier anchor were each built, measured and **not shipped**. The part-to-staff join was scored directly for the first time. |
| 2026-08-31 | **OMR-NED adopted, Surya added as a free label rung, and the contextual pass wired into `transcribe`.** The first accuracy figure here with an outside reference point — pooled **0.3164** — which immediately found that Beethoven scores note recall 1.000 and OMR-NED 0.1958, because flags are emitted where beams are printed and dynamics are never emitted at all. Surya 2 reads the margin as accurately as Claude on everything free ground truth can check, at 89% of the yield and $0; measuring it exposed the margin crop clipping first letters. Part identity finally reaches the exported score, and the `Tr. Alt.` lexicon bug it surfaced was fixed and validated on 1,380 labels across 10 editions. |
| 2026-09-01 | **Eight OMR-NED fixes — pooled 0.3164 → 0.2209 — and the first end-to-end run on a real scan.** Beams, augmentation dots, dynamics, tuplets and slurs were all signal the pipeline had already computed and the exporter dropped, double-counted or split in two; the other three were placement — two staff windows locked onto the wrong ink, and cross-staff notes awarded by distance rather than by the ledger ladder and the instrument's range. The slur fix (0.2263 → 0.2209) moved the PAIRING to the staff in page pixels rather than changing the event model, and carried its own lesson: merging *without* the notehead pad lowered the ratio while **raising** the edit count — dilution from the metric's symmetric denominator, not recognition. `wrong note`, 40% of the budget and never opened, was attributed to **rhythm and one staff**, with the scattered residue at 3.3%. Separately: a scan measured end to end for the first time (OMR-NED 0.8706, and half noteheads that the detector cannot see), the clef benchmark widened to 166 staves and the target moved to **labels rather than clef reading**, the system-break rule abandoned after five rejected attempts, and a provenance-attached score library built. Five branches landed. |

---

## What's parked / next up

The ranked handoff is [`docs/next-steps-omr-2026-09-01.md`](docs/next-steps-omr-2026-09-01.md);
NOTES.md carries the long-form context for everything below.

The current figure is **0.1439** (Mahler 0.0455, Beethoven 0.1775, Brahms 0.1804), and
NOTES.md, CLAUDE.md and `next-steps-omr-2026-09-01.md` now all agree on it — NOTES.md's
START HERE block was three fixes behind until `6a1b601` and says so itself.

**Recognition, in the order the metric ranks them:**

1. **The Beethoven bassoon pair** — the residue of the cross-staff fix, and small. One
   bar resolves the wrong way while the identical bar beside it resolves right, so the
   pair ordering reaches the range veto inconsistently. Worth about 8 edits.
2. **The hollow noteheads** — a prepared 48-cell labeling batch, ranked by meter
   shortfall, worth about 4× uniform sampling. The best-defined ask in the project right
   now: hollow noteheads on scans whose counters have closed.
3. **Beam level ±1 and lost dots** — the rest of the 452-edit rhythm bucket. Partly
   reachable by widening `_reconcile_measure_to_meter` to move a dot as well as a beam.
4. ~~**Slurs that can span measures**~~ — **shipped 2026-09-01** (`bae93b1`,
   0.2263 → 0.2209, `wrong slur` 81 → 61, about 38% of the 82-edit slur opportunity).
   The residue under the arcs is note recognition, not slur work — see the Slurs
   section above.
5. **The `count` mechanisms** — 261 edits across three independent causes: seven
   spurious whole noteheads in staff-start measures, a whole staff (C Horn 2) emitting
   zero notes in all seven of its bars, and two flute staves trading a note. **Re-measure
   this one before working it** — the flute case was the same cross-staff mechanism the
   ledger-ladder fix addressed, so part of this budget may already be gone.
6. ~~**Text expressions and tempo marks**~~ — **read now, behind `--direction-text`**
   (shipped 2026-09-01 as `ceb6714`; on the current base 0.1861 → 0.1624,
   `wrong direction` 151 → 7 — see the limitations entry above). What remains is a
   default-on decision (the reader needs `.venv-surya` and ~9 s of OCR per dense page),
   not reading work.

**The header layer:**

7. **Replace the positional default.** 17 of 21 clef errors, and the machinery to fix it
   already works — it needs instrument names, not better clef reading. This is the same
   item as improving the label ladder's reach.
8. **Key signatures: 11 staves where the clef IS read and neither reader finds an
   accidental in the header.** The "detector is blind to those flats" diagnosis was
   corrected — it detects them and labels them `accidentalFlat`, while every
   key-signature reader consumes only `key*` classes. Routing them in was implemented,
   measured and **not shipped** (beet5-p2 10 correct → 9).
9. **Infer the key signature from the music** (roadmap #4b, explicitly wanted by Sean).
   Untouched by the #4 negative, which killed only the clef half. The evidence that it
   is a real unflagged error class: Beethoven 5 p.15 reads *0 sharps / 0 flats* on all
   18 staves of a C-minor movement carrying 33 inline flat detections, and Boléro p.10
   reads five different signatures across 32 staves. More tractable than the clef half
   because a key signature is global and corroborated across staves. **Do not reuse
   per-staff key-profile fitting — measured as noise.** First establish whether the
   failure is *reading* or *detecting*.
10. **Auto-populate the dossier** (roadmap #5, untouched). It still requires hand-input
    facts; the contextual layer would make it self-populating on the same
    model-proposes / human-adjudicates loop as the annotate UI.

**Watches and decisions:**

11. **LEGATO 2 weights.** The paper's weights are still "upon publication", but its
    **system segmenter is out** (`legato-1.5-YOLO`, ungated, 52 MB, 25.9M params) and
    scored **six for six** against our own grouping — independent corroboration rather
    than a gain. **`legato-1.5` (0.9B): the access request was submitted on Hugging Face
    on 2026-09-01 and is awaiting the author's review** — so this item is now waiting on
    someone else, not on us. NOTES.md still describes the request as un-submitted.
    ⚠️ **AGPL-3.0**, inherited from ultralytics: fine host-side, a problem the day this
    is served to other people through the Stripe gate.
12. ~~**Run `probe_surya_determinism.py`.**~~ **Done (`bd1e09f`) — the batching
    hypothesis is REFUSED and the free-path numbers stand.** 45 replays of frozen crop
    bytes at the production decode gave **one answer**, across serial warm, cold
    spawn/kill, concurrent ×4 and ×8, mixed batches holding another page's KV, and
    `PARALLEL=1` against `PARALLEL=16`. The mechanism says why load could never have
    been it: `_surya_worker` calls the predictor once per system, so a ten-page run
    issues one request at a time. Two things worth keeping from it — **`--load K` alone
    could not have settled this**, because llama.cpp may serve K copies of one image
    from a shared prompt cache, so those decodes are not independent; and the contested
    character is not a near-tie (`Tr. Teq.` is spelled at p ≥ 0.975 with a 5.53-nat gap,
    and batch order moves logits by parts in a thousand). *Measure how hard a thing
    would have to be pushed before reporting that you could not push it.*

    ⚠️ **What did not reproduce is recorded rather than explained away.** Staff 10 now
    reads `Tr. Teq.` and staff 0 `Fl. pic.`; the earlier session recorded the opposite
    on both, just as consistently, at the same commit and the same crop bytes with every
    binary untouched. The stated guess — offered as a guess — is that the earlier
    reading came off a silent retry, since retries sample (at temperature 0.8, 24
    decodes gave 17 sequences) and worker stderr is discarded unless the process fails.
    The earlier session has **not** been called wrong, because unreproduced is not wrong.
13. **Whether v5/v6 enter the training catalog.** Six label versions are on `main` (223
    cells); `catalog.yaml` unions only v1–v4. Adding the 62 clef cells narrows the
    density prior, which is what collapsed dense-page noteheads 2506 → 114 — so it wants
    a measured run behind `wtc_forgetting_eval.py`, not a rebuild. The retrain can no
    longer silently re-trigger the Phase 3.4 head-reset collapse (nc=208 cap + guard).
14. **Assess `claude/omr-dossier-verification-layer-eaf6d0`** — the last branch with a
    capability `main` lacks (dossier-steered re-segmentation on a known bar count). Then
    the two March web-app implementations: measure-level MusicXML patching and the
    persistent job queue.
15. **Ensemble recognition for clef + detail prediction** (Sean flagged, 2026-07-10).
    Partly overtaken — the clef half needed geometry, not an ensemble. **Still open: the
    time-signature half**, and clef/key/time state resets across pages.
16. **Publisher/era as a transfer-learning axis.** Research-only, and explicitly parked
    until Sean is actively working on ReEngrave: map Breitkopf & Härtel, Peters,
    Schirmer, Eulenburg, Universal Edition, Bärenreiter and Henle to their active
    windows and engraving conventions.

**Longer-standing, unchanged:**

17. **GKB access for OMR context** — unblocked now that the maestro bridge exists.
18. **DoReMi + MUSCIMA++ training data** — expand beyond DSv2 (download + class map +
    re-train).
19. **RTMDet / yolov8x @ 200 epochs escalation** — Sean has approved the full run; needs
    a comparison protocol (same verdict set, same `imgsz`) and a budgeted cloud run.
20. **Multi-type barline classification** — single / double / final / repeat, which Sean
    wants. Classical-CV post-processing is the likely route, and **MusicXML repeat signs
    are tied to it** — they are still dropped on export.
21. **"Just ink" label class** — verified 2026-06-10 that the annotate UI does not expose
    one. Revisit only if hard-negative-by-omission proves insufficient.
22. **Eleven IMSLP works never resolved** — named in NOTES.md with the one-command fix.
    IMSLP's JavaScript download redirect is deliberately not defeated; those need a
    logged-in browser.

Closed out, kept so they are not re-proposed:
~~YOLO training via symphony MusicXML × IMSLP editions~~ — **executed and concluded**
(see the catalog-experiment section). ~~Maestro Analyzer as a theory-constraint layer~~
— **shipped M0–M4** (2026-05-24). ~~One-line percussion staves~~, ~~body text detected
as staves~~, ~~the `Tr. Alt.` lexicon bug~~ and ~~the part-to-staff order inversion~~ —
all fixed and measured above.

### Do not spend time on these

Each is recorded with the measurement that closed it:

- **The system-break rule.** Five attempts across two families, all rejected. The ground
  truth is now 23 pages over 5 editions and it kills an idea in one run. The three
  remaining failures are one narrow case — systems printed so close their brackets
  nearly touch — and LEGATO 2's segmenter is the lever there, not a cleverer local
  signal.
- **Detector fine-tuning on hand labels** — seven documented collapses.
- **Synthetic augmentation** (ScoreAug / Augraphy) — disproven by a fair three-way test:
  worse than the clean control on real cells, and best on synthetic validation while
  worst on real pages. Explicitly **not** the answer to the hollow noteheads either.
- **VLM transcription** — disproven twice here, and confirmed externally by LEGATO 2's
  own paper putting Gemini 3.1 Pro at 90–94 OMR-NED against Audiveris's 56–77.
- **Catalog-augmented YOLO training**, and **the MXL→bounding-box label path** (F1
  0.064 on 76 hand-mapped cells).

---

## Repository layout (where to find things)

- **Web app entry:** [`backend/main.py`](backend/main.py) (all routes), [`frontend/src/App.tsx`](frontend/src/App.tsx) (all pages).
- **OMR pipeline:** [`tools/omr/`](tools/omr/) with [`tools/omr/README.md`](tools/omr/README.md) as the deep-dive.
- **Theory layer:** [`tools/maestro_bridge/`](tools/maestro_bridge/) (TypeScript CLI + `gradus` submodule), [`backend/modules/theory_layer.py`](backend/modules/theory_layer.py), [`backend/modules/maestro_bridge.py`](backend/modules/maestro_bridge.py), plan + results in [`docs/maestro-integration-plan.md`](docs/maestro-integration-plan.md).
- **Training:** [`tools/omr/training/`](tools/omr/training/). Cloud-GPU notes in `HANDOFF_PREMIUM_TRAINING.md` + `VAST_AI_SETUP.md`. Hand-labeled data: [`data/user-labeled/`](data/user-labeled/).
- **Score library:** [`tools/library/`](tools/library/) + `data/score-library/catalog.json`.
- **Benchmarks:** [`benchmarks/`](benchmarks/). The headline write-up is [`benchmarks/omr-phase4-session/retrospective.md`](benchmarks/omr-phase4-session/retrospective.md); for the current arc read [`benchmarks/omr-ned-2026-08/FINDINGS.md`](benchmarks/omr-ned-2026-08/FINDINGS.md), its `WRONG_NOTE_ATTRIBUTION_2026-09-01.md`, and [`benchmarks/omr-clef-session-2026-09/RETROSPECTIVE.md`](benchmarks/omr-clef-session-2026-09/RETROSPECTIVE.md).
- **The ranked handoff:** [`docs/next-steps-omr-2026-09-01.md`](docs/next-steps-omr-2026-09-01.md).
- **Setup & operational reference:** [`CLAUDE.md`](CLAUDE.md).
- **Open ideas:** [`NOTES.md`](NOTES.md) — including the **contextual analysis roadmap**.
- **Cross-session picture (2026-08-28):** [`docs/state-of-play-2026-08-28.md`](docs/state-of-play-2026-08-28.md).

---

## How to run things (quick reference)

```bash
# Full web stack (requires omr-weights/deepscoresv2-yolov8l-imgsz2048-ft-30ep.pt)
docker compose up -d
# → http://localhost

# Standalone OMR CLI (no Docker)
python3 -m tools.omr.transcribe score.pdf --out out.json
python3 -m tools.omr.export out.json --format lilypond --out out.ly
lilypond out.ly

# Theory layer (host-side; one-time setup)
git submodule update --init && (cd tools/maestro_bridge && npm install)
MAESTRO_BRIDGE_ENABLED=true MAESTRO_PITCH_RERANK_ENABLED=true python3 ... # see CLAUDE.md

# Hand-label more cells (full flow: CLAUDE.md → "Hand-label cells for OMR training")
python3 -m tools.omr.annotate.select_cells_orchestral --out-dir benchmarks/omr-labeling-NEW --plan "tag=/path/to/score.pdf:12:6"
python3 -m tools.omr.annotate.server --bench-dir benchmarks/omr-labeling-NEW
# → http://127.0.0.1:5050

# Train a new YOLO checkpoint
python3 tools/omr/training/train_yolo.py
```

See [CLAUDE.md](CLAUDE.md) for the full operational reference.
