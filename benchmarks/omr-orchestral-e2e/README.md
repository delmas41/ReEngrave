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

## It also settled the DPI question

Running this at 300 DPI — which the authored fixtures prefer — collapses
Mahler (recall 0.208 → 0.042, duration accuracy to zero) and costs Beethoven
recall and duration. Sparse and dense music want opposite settings, so the
CLI's 600 and the backend's 300 are not simply a drift to be unified. Full
numbers and the mechanism in `benchmarks/omr-dpi-imgsz-2026-08/RESULTS.md`.

That is the specific value of this benchmark: the authored fixtures alone would
have recommended a change that quietly wrecks the case the project exists for.

## Limits worth stating

* An excerpt is re-engraved by LilyPond, so its layout is LilyPond's, not the
  publisher's. Staff spacing, beaming decisions and page turns differ from the
  print the same music appears in.
* `measures 1-8` of a movement is its opening, which is systematically
  atypical — often sparser, and always carrying the clef/key/meter header.
* Part count is the MusicXML's, which does not condense: a printed score puts
  Flute 1 and 2 on one staff where the XML keeps two parts. So `parts` matching
  is a weaker claim than it looks on works that print condensed.
