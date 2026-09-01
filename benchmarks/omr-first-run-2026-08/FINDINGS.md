# A real scan, start to finish, with nothing helping it (2026-08-31)

Every accuracy number this project holds was measured on one element at a time
— clefs on 52 hand-read staves, key signatures on 42, the part-staff join on
three pages, note recall on pages the project **rendered itself** from the same
MusicXML it then scored against. Each is valid for its own question. None of
them answers *what comes out if someone hands the pipeline a scan.*

This is that run. One page of a real IMSLP scan of Beethoven 5, defaults, no
dossier, scored against the Gradus reference for the work.

The short version: **the parts of the pipeline that have been measured are in
decent shape, and the parts that have never been measured are what make the
output unusable.** Layout is exact, clefs are 10/12, and three quarters of the
noteheads land on the right line — and the final engraved page is still not a
transcription of Beethoven 5, because the meter was read wrong, three barlines
were missed, and ten of twelve key signatures were never found.

**Two of those three are fixed since**, on 2026-08-31 — the meter
(`../omr-timesig-2026-08/`) and the barlines ([BARLINES.md](BARLINES.md)) — and
the correction that mattered most was to this file's own ground truth. The
sections below are the original run, with the numbers restated against the
corrected 16-measure window; each fixed section says so.

---

## What was run

```bash
python3 -m tools.omr.transcribe \
    "…/IMSLP984073-PMLP1586-symphonyno5incmi0000beet_o2b7.pdf" \
    --pages 1 --out benchmarks/omr-first-run-2026-08/out/beet5-p1.omr.json
python3 -m tools.omr.export  …/beet5-p1.omr.json --format musicxml --out …/beet5-p1.omr.musicxml
python3 -m tools.omr.export  …/beet5-p1.omr.json --format lilypond --out …/beet5-p1.ly
lilypond beet5-p1.ly
python3 benchmarks/omr-first-run-2026-08/eval_first_run.py
```

Input: a 600 dpi bitonal scan (2897×3813), page 1 of the movement — twelve
staves, one system, sixteen measures. 18.0 s of pipeline time.

Truth: `beethoven-sym5-mvt1.mxl` from the Gradus library — 18 parts, 502
measures, written pitch.

**No dossier**, deliberately. `data/dossiers/` is generated from the same
MusicXML used here as truth, so `--dossier` would hand the run its own answer
key. A second run *with* the dossier is reported at the bottom, separately.

### The truth for the page was established without asking the pipeline

Two things had to be known independently: how many measures the page holds, and
what clef and key signature each staff actually prints.

*Measures.* On a staff of whole-bar rests almost the only full-height ink is a
barline, so counting columns dark across the whole staff height counts measures
(`probe_page_measures.py`). Five such staves — Flauti, Oboi, Corni, Trombe,
Timpani — **each independently give 16**.

⚠️ They each independently gave **17** first, and were believed, because five
staves agreeing looked like a check. It is not one when the error is shared: a
TIME SIGNATURE is full-height ink too, and all five print the same one. The
probe now also requires the column to continue past the staff into the gap,
which a barline does and a time signature does not — 1.00 against 0.05.

A cross-staff variant of the same probe — a column dark in ≥8 of the 12 staves —
returns 12, because where the strings play thickly the barline meets noteheads
and stops being a clean column. It was discarded for failing in the same place
the pipeline fails, which is the one thing an independent check may not do.

*Clefs and key signatures* were hand-read off the scan, because **the reference
and the edition genuinely disagree**. The print gives Trombe and Timpani no key
signature; the Gradus file gives them three flats. The page is what a reader
sees, so the page is the truth, and a correct reading must not be scored wrong
for it.

---

## Layout: exact

| | truth | OMR |
|---|---|---|
| systems | 1 | **1** |
| staves | 12 | **12** |

Twelve staves spanning a 1900 px vertical gap, bracketed into one system, on a
scan with broken staff lines. The connectivity-veto grouping work holds up on a
page it has never seen.

## Measures: 13 of 16 — ✅ FIXED 2026-08-31

Three barlines missed, all three consecutive at the right-hand end of the
system, fusing four bars into one. Everything else was exact.

⚠️ **This section said "four missed, of seventeen measures" and both numbers
were wrong.** The ground-truth probe counted the page's TIME SIGNATURE as a
barline — its digits align into a column six pixels wide, exactly a barline's
width — so the page was credited with a bar it does not have, and the pipeline
blamed for a miss at x=833 that was not a barline to miss. All five tacet staves
agreed on the wrong answer, because all five print the same time signature.

Now **17 of 17 barlines, 0 false, 16 measures of 16**. The cause of the three
real misses was that the scan is warped and the connectivity probe assumed
barlines are vertical. Full account in
[BARLINES.md](BARLINES.md), including what the fix cost in note recall.

## Clefs: 10 of 12

| staff | printed | read | |
|---|---|---|---|
| Timpani in C.G. | bass | treble | ✗ |
| Viola | alto | treble | ✗ |

Both errors are the documented failure mode — a non-treble clef read as treble —
and the Viola one is expensive: its `step` recall is 0.23 against 0.65–0.78 for
the other string staves, because every pitch on the staff is displaced.

## Key signatures: read on 2 of 12 — ✅ IMPROVED 2026-08-31

Only Flauti and Violoncello were read at all. Violoncello got 3 flats — correct.
Flauti got **1 flat where the page prints 3**. The other ten staves report zero
because nothing read them, which is accidentally right for the three that
genuinely carry none (Corni, Trombe, Timpani), giving a flattering 4/12.

The cost is measurable, and it is the gap between the two note metrics below.

Now **7/12 correct, 4 genuinely read, 0 wrong values** — and the accidental gap
those numbers cause halves, exact-pitch recall 0.571 to 0.619 against an
unchanged step recall. A template reader
(`tools/omr/key_signature_template.py`) matches the Bravura outlines instead of
reassembling ink into components, which is what the locator cannot do on a scan
whose staff-line removal leaves every glyph in pieces. Full account, including
two rules that had to be found by breaking WTC p.17, in
[KEY_SIGNATURES.md](KEY_SIGNATURES.md).

## Time signature: reported, and wrong — ✅ FIXED 2026-08-31

The page did not report `null`. It reported common time, on all twelve staves,
`source: detected_propagated, votes: 3` — and the exporter duly wrote **4/4 onto
a 2/4 page** after a `2` and a `4` are printed on every one of them. The three
votes came from `timeSig4` boxes fired on **barline** fragments in the middles of
bars 6 to 12, each turned into 4/4 by the single-digit guess.

Fixed in `benchmarks/omr-timesig-2026-08/` — a header meter reader
(`tools/omr/time_signature_locator.py`) that reads the meter by its geometry and
votes across the system, plus a guard that stops one misread bar rewriting the
rest of its staff. The page now emits **2/4**, and its LilyPond bar-check
failures fall 154 → 104. The numbers below are from the run before that fix,
except where a row says otherwise.

## Notes: 147 reference pitches, 170 emitted

Pitches are compared as multisets per printed staff, because six of the twelve
staves carry two reference parts each (Flauti is Flute 1 + Flute 2) and the
reading order of two condensed parts on one staff is genuinely ambiguous.

| | recall | precision |
|---|---|---|
| exact pitch (`E-4` ≠ `E4`) | **0.612** | 0.529 |
| letter + octave, accidental discarded | **0.782** | 0.677 |
| pitch **and** duration | **0.360** | 0.312 |

Three things fall straight out of those rows:

1. **17 points sit in the accidentals.** The pipeline puts three quarters of the
   noteheads on the right line and then spells them wrong, which is exactly what
   ten unread key signatures do to a page in three flats.
2. **Duration is the weakest link by a distance** — 0.360 against 0.782 for
   position. Half of the correctly-located notes carry the wrong value.
3. **24 of the 170 emitted notes are on staves that print nothing but rests**
   — Trombe 11, Flauti 5, Corni 4, Timpani 4. Four staves that are silent for
   the whole page, and the pipeline hears notes on all four.

Per-staff detail is in `beet5-p1-firstrun.json`.

## OMR-NED: 0.8706 — and two thirds of it is structure

Against the reference trimmed to mm.1–16. The harness is not on this branch —
it lives on `claude/tech-advances-tools-review-4a43f9`, unmerged, so reproducing
this row means borrowing it and building its venv:

```bash
git checkout claude/tech-advances-tools-review-4a43f9 -- \
    tools/omr/omr_ned.py tools/omr/_omrned_worker.py
python3 -m tools.omr.omr_ned --bootstrap
python3 -m tools.omr.omr_ned out/beet5-p1.omr.musicxml truth/beet5-mm1-16.musicxml
```

```
0.8706 — 1723 edits over 1123 truth + 856 predicted symbols
  entire measure insert/delete    585  34.0%
  entire staff insert/delete      548  31.8%
  wrong note                      288  16.7%
  wrong note head                 208  12.1%
```

For scale, this repo's own rendered-page baseline is **0.3164 pooled**. Almost
none of the difference is note reading. 66% of the edits are whole-measure and
whole-staff inserts: the reference has 18 parts and the printed edition
condenses them onto 12 staves, and 13 measures were emitted where 16 exist.

**So OMR-NED is not yet a usable tracking number for scans.** It is measuring
the export's part model against the edition's engraving decisions. It becomes
meaningful once `to_musicxml` emits a score rather than one part per
(page, system, staff).

## The end of the pipeline

The MusicXML exports, LilyPond compiles (2 bar-check failures), and the engraved
page — `out/beet5-p1-reengraved.pdf` — is **not a usable transcription**: 4/4
throughout, key signatures on two staves, notes on staves that print rests, bars
that do not line up.

That is the finding worth keeping. Layout exact, clefs 10/12, three quarters of
noteheads correctly placed, and the artifact at the end is still unusable —
because component accuracy does not compose. A missed meter and four missed
barlines misplace everything downstream of them, and neither has ever been on
the measured list.

## The dossier does not engage on this page

Re-running with `--dossier beethoven-sym5-mvt1`:

```
dossier: 3 disagreement(s) — dossier_meter_disagreement=3
page 1: 156 measures … key signatures: read on 2/12 staves
```

Identical measure count, identical key-signature coverage. The slot-level checks
abstain, correctly, because 18 parts do not join 1:1 to 12 staves — and **real
editions condense; that is what a printed score is.** The abstention rule was
measured on pages chosen for the join work; this is the first time it has been
watched on a page picked only because it is page 1 of a scan, and the result is
that the project's strongest external-truth tool contributes one meter check.

---

## Six pages of layout, and the thing it says about the dossier

Page 1 is one system, so it says nothing about how the pipeline handles a page.
Running the first six pages (`out/beet5-p1-6.omr.json`, 154 s) and hand-counting
the staves in each printed system:

| page | printed systems | printed staves | OMR systems | OMR staves |
|---|---|---|---|---|
| 1 | 1 | 12 | 1 | **12** |
| 2 | 2 | 11 + 11 = 22 | 2 | **22** |
| 3 | 2 | 11 + 8 = 19 | 2 | **19** |
| 4 | 2 | 11 + 11 = 22 | 2 | **22** |
| 5 | 2 | 9 + 7 = 16 | 2 | **16** |
| 6 | 2 | 10 + 12 = 22 | 2 | **22** |

**113 staves and 11 systems, all six pages exact** — on a bitonal scan, with no
dossier, at 26 s a page.

And note *why* the counts are ragged. This edition suppresses tacet staves, so
the staff set changes **between the two systems of one page**: page 3 is 11 then
8, page 5 is 9 then 7, page 6 is 10 then 12. That is not an edge case, it is how
orchestral scores are printed.

Which puts a number on the dossier problem from a new direction. The join
abstains when staff count ≠ part count; against this movement's 18 parts, the
eleven systems here present 12, 11, 11, 11, 8, 11, 11, 9, 7, 10 and 12 staves.
**It abstains on all eleven.** The current fallback is page-level
(`slot_facts_for_page`), and on a page whose two systems hold different
instruments a page-level join is not merely unavailable — it is the wrong
object.

Key signatures read across the six pages: 2/12, 6/22, 9/19, 6/22, 2/16, 8/22 —
**33 of 113 staves, 29%**.

## Ranked from this page

1. ~~**Read the meter.**~~ **DONE 2026-08-31** — `benchmarks/omr-timesig-2026-08/`.
   4 correct and 0 wrong over a corpus that is half pages printing no meter;
   duration recall 0.340 → 0.352, bar-check failures 154 → 104.
2. ~~**The four barlines.**~~ **DONE 2026-08-31** — three, not four, and the
   fourth was an error in this file's ground truth. 17/17 with 0 false;
   [BARLINES.md](BARLINES.md).
3. ~~**Key-signature coverage, 2/12.**~~ **IMPROVED 2026-08-31** — 7/12 correct,
   0 wrong, and the accidental gap halved. Five staves still abstain;
   [KEY_SIGNATURES.md](KEY_SIGNATURES.md) prices what is left.
4. **Durations at 0.360.** The largest single gap between "found the notehead"
   and "wrote the right note", and much less studied than pitch.
5. **Stitch the export.** One part per (page, system, staff) makes every
   whole-score metric — OMR-NED included — measure the wrong thing.
6. **Join parts to staves per SYSTEM, not per page.** Six pages, eleven systems,
   eleven abstentions — and two pages whose two systems print different
   instruments, where a page-level join has no correct answer to give.

Notably absent: detection *and layout*. The detector put 170 notes on the page
against 159 real ones and got three quarters of them on the right line, from a
bitonal scan, in 18 seconds; the layout reader got every staff and every system
on six consecutive pages. Neither is the bottleneck. What is missing is
everything that has to be true *about the page as a whole* before those readings
can be assembled into a score — its meter, its bar lines, its key signatures,
and which part each staff belongs to.
