# `Tr. Alt.` is a trombone, not an alto (2026-08-31)

Wiring Surya in as the free margin reader put labels on Beethoven 5
(IMSLP984073), which has no text layer. Three of them then resolved to the wrong
instrument, at high confidence:

| printed | before | should be |
|---|---|---|
| `Tr. Alt.` | **Alto** (a voice), alias `alt`, conf **high** | Trombone |
| `Tr. Ten.` | **Tenor** (a voice), alias `ten`, conf **high** | Trombone |
| `Tr. Bas.` | **Trumpet**, alias `tr`, conf medium | Trombone |

Reader-independent: `instruments.lookup` returns those for the strings whoever
produced them, so the paid reader gets the same answers.

## The page that settles it

Two causes, and only the second is a mechanism gap.

1. `Tr.` is Tromba **and** Tromboni in Italian editions.
2. `_prefer_instrument_over_voice` + `VOICE_QUALIFIERS` already exist for the
   voice half, but the set was **hand-listed** and held the spelled-out `alto`
   and `tenor`, so the abbreviated `Alt.` / `Ten.` never reached it.

The trap named in NOTES.md is real: fixing (2) alone yields **Trumpet** for all
three, which is wrong differently. So (1) has to be settled first, and the page
settles it — IMSLP984073 p.47 prints **both readings at once**:

```
 s7   'Tr.'        <- the trumpets
 s8   'Timp.'
 s9   'Tr. Alt.'   <- the three trombones of the finale
 s10  'Tr. Ten.'
 s11  'Tr. Bas.'
```

So the abbreviation cannot separate them and the **part name beside it can**: a
trombone section is scored by REGISTER and a trumpet section by number and key
(`Tr. I`, `Trombe in C`), never the other way round.

That is a printing convention rather than one scan's quirk, and a **second,
independent edition proves it for free**: imslp-575951 p.59 carries a PDF text
layer, and it prints `Tr.` over the trumpets and `Tr. Alt.` / `Tr. Ten` /
`Tr. Bas` over the trombones on the same page. No OCR, no model, no judgement
call — the publisher's own text.

## The change

`tools/omr/instruments.py`, two edits.

**Trombone gains the register-qualified aliases** `tr alt` / `tr alto` /
`tr ten` / `tr tenor` / `tr tenore` / `tr bas` / `tr bass` / `tr basso`. The
alias index is longest-first, so a qualified `Tr.` reads as the trombone it is
while a bare one keeps the Trumpet the table already named. **Not `tr b`** — on a
real score `Tr. B.` is a trumpet in B-flat far more often than a bass trombone,
the same trap as `Cl. B.`; and a bass TRUMPET prints `Tromba bassa` /
`Basstrompete`, which carries its own noun and never reaches these.

**`VOICE_QUALIFIERS` is now DERIVED** from the voice instruments' own aliases
instead of hand-listed. The hand-list *was* the bug: a register word that can win
the alias index is by construction an alias of a voice, so deriving the set
closes the whole family at once instead of one spelling at a time. `Chorus` is
excluded — "Coro" names an ensemble, never a register. This alone fixes
`Fl. Alt.` → Flute, `Cl. Alt.` → Clarinet and `Trb. Tenore` → Trombone, which
were all singers before.

## Validation — several editions, per the standing rule

The standing rule from the clef work is that a lexicon change passing on one
corpus means nothing. Three independent measurements, none of which invents a
new evaluation.

### 0. Every part name the Gradus library holds — the widest no-regression net

Cheapest first, and the broadest: 5507 distinct strings, being every
`<part-name>` / `<part-abbreviation>` / `<instrument-name>` in the Gradus
MusicXML library (**124 works** — Bach cantatas and the WTC, Mozart, Beethoven,
Brahms, Bruckner, Dvořák, Tchaikovsky, Mahler, Ravel, Holst, Boulanger) plus the
raw left-margin text spans of six PDFs. Resolved with both lexicons:
**0 of 5507 change.**

This proves the fix breaks nothing across a very wide vocabulary, and it proves
almost nothing about the fix WORKING — engraving software writes the spelled-out
`Bass Trombone`, not the printed `Tr. Bas.`, so this corpus cannot see the bug at
all. That is exactly why measurements 1–3 exist.

### 1. The reader benchmark that already exists

`score_readers.py` grades a reader against the free PDF-text-layer truth, on the
RESOLVED INSTRUMENT. Every results file in this directory, before and after:

| results file | before | after |
|---|---|---|
| `results.json` (Claude, `crops`) | 25/25 agree, 0 disagree | **unchanged** |
| `results-surya.json` (`crops`) | 24/24, 0 disagree | **unchanged** |
| `results-surya-w14.json` | 32/35 (91%), **3 disagree** | **34/35 (97%), 1 disagree** |
| `results-surya-w20.json` | 33/35, 2 disagree | **unchanged** |
| `results-surya-w26.json` | 33/35, 2 disagree | **unchanged** |
| `results-vision-w14.json` | 36/36, 0 disagree | **unchanged** |
| `results-vision-w20.json` | 36/36, 0 disagree | **unchanged** |

The `w14` gain is the fix: two of its three disagreements were
`text 'Tr. Ten'->Tenor vs reader 'Tr. Alt.'->Alto` and
`text 'Tr. Bas'->Trumpet vs reader 'Tr. Ten.'->Tenor`, both now Trombone on both
sides. Read that honestly: the READER is one staff off there, and grading on the
resolved instrument now scores it as agreement. The third disagreement, where the
reader genuinely read `Tp.` for `Tr. Alt.`, correctly survives.

### 2. Every margin label ten editions actually produce

The MusicXML part names and raw PDF spans are not what `lookup` is fed in
production, so neither can see a margin-abbreviation fix. This runs the real
readers — `staff_labels.read_staff_labels` where there is a text layer, Surya
where there is not — over pages sampled through each score, and resolves every
string with both lexicons in one process (`git show HEAD:` exec'd standalone, so
nothing in the tree has to move).

| edition | reader | labels | changed |
|---|---|---:|---:|
| Beethoven 5, imslp-575951 | text layer | 237 | **14** |
| Beethoven 5, IMSLP984073 | Surya | 118 | **13** |
| Beethoven 6, imslp-504082 | text layer | 220 | 0 |
| Debussy, *La Mer* | Surya | 56 | 0 |
| Mahler 5 | Surya | 136 | 0 |
| Handel, *Messiah* lead-sheet | text layer | 49 | 0 |
| Handel, *Messiah* reduction | text layer | 67 | 0 |
| Ravel, *Boléro* | text layer | 497 | 0 |
| Bach, WTC I | text layer | 0 | – |
| Kirchhoff, *L'ABC Musical* | text layer | 0 | – |
| **total** | | **1380** | **27** |

**All 27 changes are a `Tr.` + register string, and all 27 move to Trombone.**
Nothing else in 1380 labels moves:

```
   9x  'Tr. Alt.'    Alto     -> Trombone     both Beethoven 5 editions
   6x  'Tr. Bas.'    Trumpet  -> Trombone     both Beethoven 5 editions
   4x  'Tr. Ten.'    Tenor    -> Trombone     both Beethoven 5 editions
   3x  'Tr. Bas'     Trumpet  -> Trombone     imslp-575951
   1x  'Tr. Alt'     Alto     -> Trombone     imslp-575951
   1x  'Tr. . Bass'  Trumpet  -> Trombone     imslp-575951   <- OCR damage
   1x  'Tr, Ten'     Tenor    -> Trombone     imslp-575951   <- OCR damage
   1x  'Tr. Ten'     Tenor    -> Trombone     imslp-575951
   1x  'Tr. Bass.'   Trumpet  -> Trombone     IMSLP984073
```

The two Handel scores and Boléro are the ones that matter for the second half of
the change: 613 labels including 36 `Altos` and every SATB part name in the
*Messiah*, and widening `VOICE_QUALIFIERS` moves **none** of them. A genuine
voice is still a voice. Mahler 5 and *La Mer* matter for the first half — dense
German and French margins read by the same OCR engine that produced the bug, 192
labels, no `Tr.` in either tradition, nothing moves.

### 3. End to end, the page the bug was found on

Beethoven 5, IMSLP984073, pp.47–49 (no text layer, so Surya reads the margin),
`transcribe` → `export --format musicxml`, `<part-name>` per staff:

```
truth   Piccolo Flute Oboe Clarinet Bassoon Contrabassoon Horn Trumpet Timpani
        Trombone Trombone Trombone Violin Violin Viola Cello Contrabass

before  Flute   Flute Oboe Clarinet Bassoon Bassoon       Horn Trumpet Timpani
        Alto    Trumpet  Trumpet    Violin Violin Viola Cello Staff p47-s0-16

after   Flute   Flute Oboe Clarinet Bassoon Bassoon       Horn Trumpet Timpani
        Trombone Trombone Trombone  Violin Violin Viola Cello Contrabass
```

**11/17 → 15/17 correct, identically on all three pages.** The three trombones
are the fix; the contrabass comes along because the layout fit now sees a page
with trombones on it and switches `classical-condensed` → `romantic`, which
names 16 slots instead of 13. `contextual.reference` on p.47 alone goes 5/17 →
8/17 with **no slot other than the three changing**.

The two remaining errors — `Fl. pic.` read as Flute rather than Piccolo, and
`C. Fag.` as Bassoon rather than Contrabassoon — are older lexicon gaps,
untouched here.

## Two things this surfaced and did not fix

**A layout ordering no `ScoreLayout` can express.** This edition prints the
timpani BETWEEN the trumpets and the trombones; every layout that has Trombone
puts it before Timpani. It is invisible while the page's own `Timp.` is legible
(a label beats score order), and it bit exactly once: on p.47 alone, where Surya
misread `Timp.` as `Tinap`, the timpani staff took Trombone from the fit. With
pp.48–49 supplying the label it holds. Worth a `classical-trombones` layout —
but that is a change to the layout vocabulary and needs its own multi-edition
measurement.

**Other lexicon gaps, each its own bug.** `Gr. Tr.` (Grosse Trommel, a bass
drum) resolves to *Trumpet* and `Kl. Tr.` (Kleine Trommel) to *Clarinet*, both in
the Mahler 5 part names. `Altos` (French for violas, 36 of them in Boléro),
`Tromp.`, `Trbe.`, `Trbn.`, `Trbni.` and `Tbni.` resolve to nothing. Abstention is
the right failure and none of them is this bug, so none was touched — a lexicon
change that ships without its own corpus is the thing this file exists to avoid.

## Reproducing

```bash
python3 -c "from tools.omr.instruments import lookup; \
    print([(s, lookup(s).instrument.name) for s in ('Tr. Alt.','Tr. Ten.','Tr. Bas.')])"
python3 -m pytest tools/omr/tests/test_instruments.py -q
python3 benchmarks/omr-margin-labels-2026-08/score_readers.py \
    --crops benchmarks/omr-margin-labels-2026-08/crops-w14 \
    benchmarks/omr-margin-labels-2026-08/results-surya-w14.json --detail
```
