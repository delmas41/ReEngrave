# The time-signature issue, re-asked (2026-09-01)

Sean asked to "consider the time signature issue if it still exists."

It does, and **not in the shape the record describes.** The August work
([`../omr-timesig-2026-08/FINDINGS.md`](../omr-timesig-2026-08/FINDINGS.md))
closed with 8 correct / 0 wrong / 21 correct abstentions and a statement that
the reader's remaining gap was silence: cut common "abstains", roughly half of
printed meters go unread. Both halves of that turn out to be artefacts of the
corpus it was measured on.

On a corpus widened from 5 sources to 11, the reader is **wrong three times**,
and the largest wrong class is the one the 08 work believed it had made safe by
*withholding* a template.

| | 08 corpus (14 pages, 5 sources) | + 09 corpus (16 pages, 6 more sources) |
|---|--:|--:|
| WRONG | 0 | **3** |
| correct | 8 | 10 |
| missed (printed, unread) | 0 | 2 |
| correct silences | 21 | 40 |

The 08 half reproduces **exactly** on today's tree — 8 / 0 / 0 / 21, unchanged
since 2026-08-31. Nothing regressed. The new pages were always failing; there
was no page in the corpus that could say so.

---

## 1. The candidate-list gap is ~1%, and it is not the problem

`DEFAULT_METERS` holds 20 digit meters plus `C`. Against the two populations
that say what the repertoire actually prints (`survey_meters.py`,
`meter_survey.json`):

| population | starting meters searchable |
|---|--:|
| 97 dossiers (`data/dossiers/*.json`, orchestral, exact from MusicXML) | **96 / 97 = 99.0%** |
| 1691 library reference encodings (`library/reference/`, wider repertoire) | **1680 / 1691 = 99.4%** |

The single missing meter is **4/8** — Dvorak 9 i in the dossier set, and 8 of
the library's 11 misses. The rest of the library tail is one 2/8, one 4/16 and
one 24/16. In mid-work meter *changes* the dossiers add 5/2 (Holst, 4
occurrences), which the reader does not look for anyway: it reads the meter at
the head of a system and never a mid-system change.

Two-digit numerators are already supported and already work: `_row` lays digits
out left to right before the stack is scaled to the four-space box, and
`brahms3-p1` reads **6/4 on 16 staves of 16** — two-digit `12/8` uses the same
path.

**So "a printed meter the reader cannot even search for" costs one work in 97.**
That is the cheap question, and its answer is that adding templates is not the
lever.

### The gap that matters is fifteen times bigger, and it is a template the repo already has

`timeSigCutCommon` was built into the symbol library on 2026-08-31 and
deliberately left out of the candidate list. Cross-tabulating each dossier work
against the `<time symbol="...">` its own MusicXML carries:

| how the opening meter is printed | dossier works | library encodings |
|---|--:|--:|
| digits | 66 | 966 |
| `C` (common) | 16 | 646 |
| **`C\|` (cut common)** | **15 (15.5%)** | **79 (4.7%)** |

Fifteen of the ninety-seven orchestral works this project is aimed at open on a
cut common — Mozart 40 i and iv, Mozart 41 iv, Brahms 2 iv, 3 iv, 4 i,
Beethoven 2 iv, 4 i, 8 iv, Bruckner 5 i, ii, iv, Mahler 5 ii, v, Tchaikovsky 4
iv. Every one of them has an edition in the score library.

---

## 2. Withholding the cut-C template does not produce an abstention. It produces `C`.

This is the finding. The 08 note says "2/2 spelled as digits is read; the cut C
abstains", and that is not what happens, because a cut common is a common with a
stroke through it and NCC does not care about the stroke:

```
mozart40-p1  sys0  WRONG  want=C|  got=C   votes=11/11  median 0.5789
brahms4-p1   sys0  WRONG  want=C|  got=C   votes=13/13  median 0.5649
```

Unanimous, on every staff of the system, comfortably over the 0.50 threshold —
which is exactly the shape of evidence the vote was built to trust. The page
then goes out as 4/4 over music in 2/2: **every bar of it is measured against a
meter twice too long**, which is the identical failure mode the whole layer was
written to stop on Beethoven 5 p.1.

The 08 work could not see this. It withheld the cut C because enabling it read a
meter on seven systems that print none, and it recorded honestly that "no page
in the corpus prints a real cut-C, so there was nothing to measure the other
side of that against." The other side is now measured: **the cost of the
abstention is not silence, it is a wrong answer on 15% of the repertoire.**

## 3. `3` and `6` are one template apart on Litolff's plates

```
beet3-p1     sys0  WRONG  want=3/4  got=6/4  votes=6/12  median 0.5713
```

The Eroica's 3/4 read as 6/4 on exactly six staves of twelve — the vote's floor
is `max(2, round(0.5 x 12)) = 6`, so this cleared by nothing at all. Bravura's
`timeSig3` and `timeSig6` share their lower bowl, and on a 19th-century plate
the `3`'s open upper arm inks up.

## 4. The two misses

```
bruckner5-p1 sys0  MISSED  want=C|   got=None  votes=-/19
dvorak9-p5   sys0  MISSED  want=4/8  got=None  votes=-/15
```

`dvorak9-p5` is the missing template, and is the whole of the section-1 gap.
`bruckner5-p1` is the worst print in the corpus: at 500 dpi the clef, key and
meter are one fused blob on every staff, which is a header-reading problem
rather than a meter one — and a *correct* place for the reader to give up.

---

## The widened corpus

`corpus.json` — 16 pages, hand-read off renders, with the provenance of each
reading. Eleven sources in total once the 08 corpus is included:

| source | publisher | what it contributes |
|---|---|---|
| Mozart 40 i | Breitkopf & Haertel 1880 | **cut C**, and its page-2 negative |
| Mozart 41 i | Breitkopf & Haertel 1880 | **C** from the *same plate house* — the control the cut-C question needs |
| Brahms 4 i | Breitkopf & Haertel (SW) | **cut C** |
| Bruckner 5 i | BrucknerAGA 1935 | **cut C** on a degraded print |
| Beethoven 3 i | Henry Litolff 1870 | **3/4** — the commonest meter in the dossier set, absent from the 08 corpus |
| Brahms 3 i | Breitkopf & Haertel (SW) | **6/4**, and the two-digit numerator path |
| Dvorak 9 i | N. Simrock 1894 | **4/8** — the one meter with no template |
| Tchaikovsky 4 | P. Jurgenson | dense negative |
| Mahler 5 | unidentified scan | two dense negatives |

Half the pages are negatives, on the same reasoning as the 08 corpus: a reader
that answers more often looks better on any metric that only counts answers.

```bash
python3 benchmarks/omr-timesig-2026-09/survey_meters.py
python3 benchmarks/omr-timesig-2026-09/sweep_widened.py            # 08 + 09, ~131 s
python3 benchmarks/omr-timesig-2026-09/sweep_widened.py --only-09
python3 benchmarks/omr-timesig-2026-09/sweep_widened.py --per-staff --min-score 0
```

The 08 sweep is untouched and still runs.

<!-- sections 5 (attribution), 6 (downstream cost) and 7 (fixes) follow as they
     are measured -->
