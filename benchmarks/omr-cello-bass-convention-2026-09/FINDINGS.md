# The shared cello/bass staff — the convention, measured on the plates we hold

2026-09-22, roadmap 2.1. Research lane (sonnet), written up by the manager.
Crops in `out/print/` (28 PNGs), measurements in
`out/duplication_measurements.json`. No code under `tools/` changed.

**Question.** Every staff still held out of the Litolff Beethoven 5 export is
a condensed `Violoncello e Basso` staff narrowed to [Cello, Contrabass]. What
does that staff MEAN, and what should the file contain? Sean's rule: *"the
string family always includes all five; if there are only four lines the bass
is doubling the celli or it comes in later."*

## 1. The convention

A staff labelled `Violoncello e Basso` / `Bassi` / `Vc. e Cb.` /
`Violoncell u. Contrabass` carries ONE written line played by both sections.
The double bass sounds an octave lower by its own transposing convention; the
octave is never written. Classical-era plates condense by default and mark a
division by TEXT (`senza Bassi`, `Bassi`, `col Basso`, `Vc. soli`); Beethoven
and Rossini are where separate parts become frequent; Verdi and Wagner make
them the norm. **Neither held plate prints any inline division text** — where
the material diverges the engraver prints a SEPARATE staff on that system and
re-condenses afterwards.

## 2. The plates (crops, hand-read lineups from `works.json`)

| Litolff Beethoven 5, pdf page / system | printed | reference duplication (mm.) |
|---|---|--:|
| p1 (idx 1), 12 staves | `Violoncello.` and `Basso.` APART from bar 1 | 37.5% |
| p2 (idx 2), 11 + 11 | one staff, condensed | **93.8%** |
| p3 (idx 3), 11 + 11 | one staff, condensed | **100%** |
| p4 (idx 4) system 1, 11 | `Vcl.` (tenor clef) / `Basso.` APART | 26.7% |
| p4 system 2, 11 | `Bassi.` one staff, re-condensed | **100%** |

The engraver's choice tracks the music exactly: condensed where the two
lines are the same, split where they are not. Breitkopf Brahms 1 prints
`Violoncell` and `Kontrabass` apart on every held page (32.8% duplication —
divergent from bar 1). Simrock 1877: apparently apart, labels illegible at
the held resolution.

## 3. The encodings

Both reference files encode two parts; the contrabass carries
`<transpose><octave-change>-1</octave-change></transpose>` and its written
pitches equal the cello's where the plate is condensed. Pooled over the
condensed Litolff systems: **97.5%** of bars identical or both resting. This
sharpens `benchmarks/omr-condensed-parts-2026-09`'s corpus-wide 69.8%: for
THIS pair, condensation is near-perfect duplication by construction.

## 4. The corpus, and a reader fault

26 held editions print an explicit dual label; 14 a bare `Bassi`. ⚠️
**`instruments.lookup` resolves every dual spelling to `Cello` alone** — it
matches the first recognised word and stops, silently discarding the second
instrument on all 26. A bare `Basso.` still resolves to a bass VOICE without
the roster. Roadmap 2.1c.

## 5. What the file should contain — decided

Sean's rule is **corroborated on both plates and falsified nowhere**: the
falsifier (a four-string-staff system where the bottom staff is not the
cello's line and the bass is not entering later) does not occur. Three
options were priced:

| option | what the musician gets | cleanup charge on Litolff |
|---|---|---|
| (a) one part, two `<score-instrument>`s | a Contrabass part with HOLES on the condensed systems of a document that also prints it apart | `missing` per condensed staff-system — hand-copying the line |
| **(b) both slots get the line, bass `<transpose>`d −8ve** | both parts complete; the page says both play it | none where condensed; nothing to split |
| (c) hold out (today) | neither part | `missing`, 141 notes |

**Decision (b), restricted to a staff the family-block rule has narrowed to
exactly [Cello, Contrabass].** The count is not read off a name or an
encoding — the one thing that made `OMR_CONDENSED_PARTS` undecidable — it is
the narrowing's own candidate set, derived from the reference's trailing
family run. Where the plate prints the bass apart, the identity decision
already treats it as its own staff. The record keeps `condensed_from` on the
bass slot's placement so a later reader can tell a doubled line from a read
one, and any printed division text reaches the file as `<words>`.

## NOT ESTABLISHED

No verbatim Gould / Read citation (search returned no excerpts); no IMSLP
critical notes fetched; Simrock labels unread; no `senza Bassi` observed on a
held plate (literature only); the 26/14 corpus split is label text, not
per-edition page verification; the rule is corroborated on two works and not
stress-tested against a genuine exception.
