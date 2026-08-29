# Orchestral end-to-end accuracy, with truth from the Gradus score library

## Why this exists

Every accuracy figure in this repository was measured on one of three things:

* **Symbol-level F1 on hand-labeled cells** — the headline 98.8%. Real, but it
  measures whether a box is in the right place, not whether the music is right.
* **Coverage** — `benchmarks/omr-real-world` reports "100% pitch coverage",
  meaning every detected notehead got *a* pitch. A page can score 100% while
  reading entirely the wrong music.
* **The three `omr-end-to-end` fixtures** — the first honest note-level
  measurement, but hand-authored and topping out at four staves.

Nothing measured a conductor's page. That is the texture this project exists
for, and it is the one where the pipeline is weakest.

## What this measures

The Gradus score library (`~/Desktop/gradus-vercel/public/scores/`) holds ~97
orchestral movements as MusicXML — Beethoven 1–9, Brahms 1–4, Bruckner 5,
Dvořák 9, Mahler 5, Mozart 40/41, Tchaikovsky 4/6, Boléro, 1812. An excerpt
rendered back to PDF through `musicxml2ly` + LilyPond is a dense orchestral
page whose every note is known exactly, for free.

```bash
python3 -m tools.omr.training.orchestral_eval
python3 -m tools.omr.training.orchestral_eval --works mahler-sym5-mvt1 --measures 1-8
python3 -m tools.omr.training.orchestral_eval --no-dossier    # what the dossier adds
```

**The input is engraved, not scanned.** No foxing, no bleed-through, no skew,
no broken staff lines. So a failure here is a failure of recognition *on dense
music*, and cannot be blamed on print quality — which is exactly the confound
that makes every other orchestral number in this repository hard to read. It
says nothing about scan robustness. Both matter; this isolates one.

## Reading the numbers

`parts` and `measures` are structure — Phase 1. A structural error moves every
note after it, so it is reported separately rather than folded into the note
score. `recall`/`prec`/`dur` come from the same LCS alignment
`end_to_end_eval` uses, per part where both sides agree on the part count.

`dossier` is the count of disagreements the external-truth layer raised against
what the work actually contains (see `tools/omr/dossier.py`).

## What it found immediately

**A meter parser with no upper bound.** `parse_time_signature` concatenates
digit detections positionally, so a run of spurious digits produced arbitrarily
large numbers rather than failing. On the Brahms 1 excerpt it emitted 686/868,
786/86 and 68/862, and the exporter wrote those straight into MusicXML as
`<beats>686</beats>` — a file music21 refuses to parse and notation software
would reject. Nothing downstream was positioned to notice, because a meter is
the kind of fact the rest of the pipeline trusts. Fixed by requiring a
denominator to be a power of two and a numerator ≤ 32.

**Meters read on a page that has one meter.** On the engraved Beethoven 5
excerpt the detector reported 4/4, 4/24 and 7/24 across a movement that is 2/4
throughout. The dossier now overrides them and reports each override.

**The meter → rhythm loop working on a known bar.** Beethoven 5's opening
motif came back as three sixteenth notes, summing the bar to 1.25 beats against
the 2.0 that 2/4 requires. Re-read at one beam level instead of two they are
eighths, the bar is exact, and that is what the page says. Duration accuracy on
the excerpt moved 0.673 → 0.731 with note recall and precision unchanged — the
correction re-reads durations and never adds or drops a note.

## Seeding: the dossier as an input, not only a judge

Clef DETECTION is the documented ceiling on the header layer — 2% coverage on
orchestral scans — and it has resisted a fine-tune (which collapsed dense-page
noteheads), ensemble voting, and a CV locator. None of that matters if the clef
is simply known. With `--dossier` the pipeline now also SEEDS each staff's
written clef and key signature, where the parts join 1:1 to the staves.

| work | recall | precision | duration | matched notes |
|---|---|---|---|---|
| beethoven-sym5-mvt1 | 0.642 → **0.691** | 0.559 → **0.602** | 0.731 → **0.750** | 52 → 56 |
| brahms-sym1-mvt1    | 0.206 → **0.253** | 0.274 → **0.337** | 0.397 → 0.377 | 136 → **167** |
| mahler-sym5-mvt1    | 0.208 → 0.208 | 0.109 → 0.109 | 0.200 → 0.200 | 5 → 5 |

Brahms's duration *rate* dips only because the denominator grew faster than the
numerator: absolute `duration_ok` went 54 → 63 on 31 more matched notes.
Mahler is unchanged because it detects 31 staves against 38 parts, so the join
is unsafe and seeding correctly abstains — which is the behaviour that makes
this safe to leave on.

### It exposed system grouping as the real blocker — since fixed

Seeding did nothing at first. The per-system join could never match, because
**Phase 1 reports one musical system of 21 Brahms staves as TWELVE systems** of
1–5 staves each; Beethoven's 18 staves come back as 4 systems. The counts are
right, the grouping is not.

A page-level join (page staff total == part count) worked around it. The
fragmentation itself is now fixed at source.

**Gap distance cannot separate these cases and never could.** Within ONE Brahms
system the inter-staff gaps run 17–237 px, and within one Beethoven system
130–345 px — both wider than the gaps BETWEEN systems on a piano page. Every
adjacent pair on both pages also had x-overlap 1.00, so that rule is silent
here too. No threshold on distance can work.

What defines a system is what CONNECTS it: barlines run its full height, and
the bracket encloses exactly it, and neither crosses a break. `_gap_is_bridged`
in `staff_detector.py` asks for one column inked through the whole gap, scanned
across the full page width so the bracket in the margin counts. It VETOES a
gap-based break and never creates one, so a page that grouped correctly before
is untouched — WTC p.5 still reports its 5 grand-staff systems.

| | before | after |
|---|---|---|
| brahms-sym1-mvt1 (21 staves) | 12 systems of 1–5 | **1 system of 21** |
| beethoven-sym5-mvt1 (18 staves) | 4 systems | **1 system of 18** |
| mahler-sym5-mvt1 (31 staves) | 4 systems | **1 system of 31** |

End-to-end, with seeding already on:

| work | bars | parts | measures | notes (omr/truth) | recall | precision | duration |
|---|---:|---|---|---:|---:|---:|---:|
| beethoven-sym5-mvt1 | 8 | 18/18 | **8/8** | 80/81 | 0.691 | 0.700 | **0.911** |
| brahms-sym1-mvt1 | 5 | 21/21 | **5/5** | 400/337 | 0.599 | 0.505 | 0.262 |
| mahler-sym5-mvt1 | 7 | 31/38 | **7/7** | 36/22 | 0.136 | 0.083 | 0.000 |

Beethoven now reports **80 notes against a truth of 81** — the note count is
essentially exact, where before deduplication it reported 88.

**Every measure count is now exact**, on all three works — that is what the
grouping fix bought. Structure is solved on this benchmark.

Most of the over-detection was **one glyph counted twice**. Cells are padded 4
staff-spaces each way so ledger notes are not sliced off; on a conductor's score
those bands overlap and nothing arbitrated between them. On the Mahler page,
staves 14 and 15 reported 24 and 29 noteheads and **16 were the same notehead**
at IoU > 0.5. `_dedupe_cross_staff_detections` now keeps such a glyph on the
staff it is nearest. Threshold chosen by a sweep over all three works —
`DEDUPE_THRESHOLD.md`.

  brahms   661 -> 400 notes,  F1 0.443 -> 0.548
  beethoven 88 ->  80 notes,  F1 0.662 -> 0.695
  mahler     54 ->  36 notes,  F1 0.079 -> 0.105

Residual over-detection is real, not duplication: Brahms still reports 400 for
337 and Mahler 36 for 22 on a page that is almost entirely rests — close to a
pure false-positive measurement of the detector inventing notes on empty staves.
Precision remains the weak metric on dense pages.

### Durations: beams stack at one end, and the fallback did not know that

Brahms's duration errors were almost all **too short by a power of two** —
0.5 → 0.25, 0.5 → 0.125, 1.5 → 0.5 — which is beam levels being over-counted,
each extra level halving the note.

`rhythm.py` has two ways to count a notehead's beams. The stem-anchored one
requires the beams to stack at one END of the stem and stays sane because of
it. The no-stem fallback had no such rule and swept every beam in a window 5.5
staff-spaces tall — 550 canonical px, taller than a whole staff. On this page
183 noteheads went through the fallback:

| fallback beam levels | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| before | 20 | 56 | 31 | 39 | 14 | 11 | 9 | 3 |
| after | **151** | 22 | 5 | 5 | – | – | – | – |

**An eight-beam note is a 1024th.** The counts were then capped at 4, so the
page reported 29 sixty-fourth notes in a passage containing none. Applying the
same one-end rule to the fallback removes every impossible depth and leaves a
distribution that looks like music. Duration accuracy: Beethoven 0.857 →
**0.911**, Brahms 0.243 → 0.262, with recall and precision untouched.

Brahms's duration accuracy is still poor. The stem-anchored path also reports
56 threes and 10 fours on that page, which the truth does not support, so the
same over-counting is present there in milder form.

Mahler's part count differs from truth (31 printed against 38 in the XML)
because LilyPond suppresses its empty staves, so its part-aligned recall falls
back to a concatenated alignment and should not be read as a recognition rate.
Its note-count ratio is the number to watch there.

## It also settled the DPI question

Running this at 300 DPI — which the authored fixtures prefer — collapses
Mahler (recall 0.208 → 0.042, duration accuracy to zero) and costs Beethoven
recall and duration. Sparse and dense music want opposite settings, so the
CLI's 600 and the backend's 300 are not simply a drift to be unified. Full
numbers and the mechanism in `benchmarks/omr-dpi-imgsz-2026-08/RESULTS.md`.

That is the specific value of this benchmark: the authored fixtures alone would
have recommended a change that quietly wrecks the case the project exists for.

## A measurement bug of my own, and what it hid

The first version of this harness rendered an 8-measure excerpt and transcribed
**page 0**. Brahms's 8 measures render to THREE pages and Mahler's to two, so it
was scoring one page's output against the whole excerpt's truth and capping
recall at whatever fraction of the music happened to land on page 1.

  brahms-sym1-mvt1 recall  0.262 (as reported)  ->  0.656 (measuring one page
  against that page's truth)

Transcribing all the pages instead is not the fix: `export.to_musicxml` emits
one `<part>` per (page, system, staff), so **a part is not continuous across a
page break** — three pages of a 21-staff score come back as 63 parts, not 21
parts three times as long. That is a real limitation worth knowing about for
multi-page scores; here it means a page-recognition benchmark must stay on one
page. `excerpt()` now shrinks the measure range until LilyPond returns a single
page, and reports how many bars it actually used.

It also corrected a claim about Mahler. Its page 0 carries **31 staves and that
is correct** — LilyPond suppresses empty staves on the first system, and the
movement opens with a solo trumpet. Staff detection was never failing there.

## Limits worth stating

* An excerpt is re-engraved by LilyPond, so its layout is LilyPond's, not the
  publisher's. Staff spacing, beaming decisions and page turns differ from the
  print the same music appears in.
* `measures 1-8` of a movement is its opening, which is systematically
  atypical — often sparser, and always carrying the clef/key/meter header.
* Part count is the MusicXML's, which does not condense: a printed score puts
  Flute 1 and 2 on one staff where the XML keeps two parts. So `parts` matching
  is a weaker claim than it looks on works that print condensed.
