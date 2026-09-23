# Committed counts

One file per count: `<doc>-<page>-<date>.csv`, on the categories and the unit
fixed in [CATEGORIES.md](../CATEGORIES.md). Roadmap 1.4.

⚠️ **Who counted is part of the datum.** CATEGORIES §2c defines
`would-not-notice` as **the editor's** eye — Sean's, doing the pass — so a
count taken by anyone else is a PROXY for the instrument, not the instrument.
Each file's header row and the table below say who took it. A count taken by
the same system that produced the output is the weakest form of the evidence
and is marked as such; it does not replace Sean's and must not be read as a
baseline for "is the count going down".

| count | document / page | counter | total | note |
|---|---|---|---|---|
| `beethoven5-litolff-p3-2026-09-23.csv` | Beethoven 5 mvt 1, Litolff `984073`, pdf page index 3 (bars 49–82) | **Claude (landing session), NOT Sean** | 34 | first count on the whole-movement record; see below |

## beethoven5-litolff-p3-2026-09-23 — what it found

Against `benchmarks/acceptance/out/beethoven5-litolff/side-by-side/` (print
crop and our Verovio render of the same bars) and the whole-movement MusicXML
`…-whole-movement-20260923T025457Z.musicxml`.

| category | units | where they are |
|---|--:|---|
| `missing` | 8 | staff-systems short of the reference's sounding bars by 3 or more |
| `wrong` | 22 | **4** key signatures + **18** counted printed accidentals (sampled — see below) |
| `spurious` | 2 | stray key changes written at m82 in two otherwise-correct parts |
| `would-not-notice` | 2 | both violin parts named only `Violin` |
| **total** | **34** | |

### ⚠️ The `missing` column was MEASURED on a second pass, and it moved 5 → 8

The first pass read "how many bars does the print sound here" off the 725-px
side-by-side crop and, where our count was within one or two, declined to
count — which was the right instinct and the wrong instrument. The second pass
replaced the eyeball with the **reference encoding**, joined through the
hand-verified `beethoven-sym5-mvt1-984073-p3` window row (mm 49–82, and its
per-system staff→part map). Three calls changed, all in the same direction:

| staff-system | first pass (eyeballed) | reference | our bars | corrected |
|---|---|--:|--:|---|
| Corni, system 1 | "11 of ~13, within reading error" | **15** | 11 | short 4 → counted |
| Fagotti, system 2 | "13 of ~17, borderline" | **16** | 13 | short 3 → counted |
| Viola, system 2 | "14 of ~18" | **18** | 14 | short 4 → counted |

One call changed the other way and is recorded because it acquits us: the first
pass suspected the Flute of *spurious extra* content in system 2 and declined
to count it; the reference says 4 against our 4 — **exact**.

⚠️ **The join has a control that can fail, and it passes.** The three staves
the print SUPPRESSES in system 2 — Oboi, Trombe, Timpani — sound in **0**
reference bars of mm 65–82, and our file writes measure rests for exactly those
bars. If the window or the staff→part map were off by a system, that would not
hold.

⚠️ **A page truth is not an encoding truth** (CLAUDE.md §10). "Does this staff
sound in this bar" is a question the two agree on and the window row was
verified against the print, which is why it is used here; nothing finer (which
note, what duration) is taken from the encoding in this count.

**The two findings that dominate it:**

1. **No printed accidental reaches the file — anywhere in the movement.**
   1,531 accidental glyphs are DETECTED and **0 are read into a verdict**
   (`coverage.json` → `accidental_reading`), and the file carries **0
   `<accidental>` elements across 7,878 sounding notes**. Every `<alter>` in
   the file comes from the key signature alone. This is a whole-quantity gap,
   not a page's bad luck, and it is `missable` by CATEGORIES §0's own
   definition — a wrong pitch inside a run is the scattered error that
   survives the pass.
   ⚠️ **18 is a SAMPLE, not a page total.** It is what I counted in a declared
   window — the four string staves of bars 49–56 — at ±3 for reading a 725-px
   scan. The rest of the page is UNCOUNTED, not zero, and the sheet says so
   rather than extrapolating.

2. **Key signatures are re-read per system and wander.** Four of twelve parts
   carry a wrong key at bar 49 (Flute −2, Bassoon −1, Violin II **+1**, Viola
   −1 where the print has −3), and the Viola jumps to **+7 (C♯ major)** at
   m64. The two that are *correct* are the interesting controls: Clarinet −1
   and Horn/Trumpet 0 are right because those are the transposing parts'
   written keys, so the reader is not simply defaulting.

**What went right, recorded so the count is not read as uniformly bad:** the
suppressed 8-staff system is handled correctly — Oboe, Trumpet and Timpani are
tacet in the print's second system and ours writes measure rests for exactly
those bars; all twelve parts are named with real instrument names; the meter is
2/4 throughout and right; Timpani, Cello and Contrabass need no fix at all in
system 1; and the 1,971 `arpeggiato` misdetections cost the human nothing
because none of them reaches the file.

## What this count does NOT establish

* **It is not Sean's count.** See the warning above. `would-not-notice` in
  particular is defined as his judgement and mine is a stand-in.
* **It is not a baseline to drive down** (CATEGORIES §5). It is read as *what
  to fix next*, and what it says to fix next is accidentals.
* **Bar-level content calls are at the resolution of a 725-px scan.** Where our
  sounding-bar count is within one or two of the print's, the sheet records the
  numbers and does NOT count a unit; those rows say so explicitly. Only
  unmistakable gaps (Viola system 1: one sounding bar of ~10; Horn system 2:
  four of ~12) are counted.
* **The `scope` vocabulary is still short a term, and this is the second count
  to hit it.** A key signature wrong across a part's whole page-range is
  repaired by ONE gesture that is neither `staff-system` nor `page`. §4b
  already raised this for a document-wide fix and left it as `other`; it
  recurs here. The next counter should decide whether to add a `part-range`
  scope rather than inherit another `other` row.
