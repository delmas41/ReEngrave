# The time-signature issue, re-asked (2026-09-01)

Sean asked to "consider the time signature issue if it still exists."

It does, and **not in the shape the record describes.** The August work
([`../omr-timesig-2026-08/FINDINGS.md`](../omr-timesig-2026-08/FINDINGS.md))
closed with 8 correct / 0 wrong / 21 correct abstentions and a statement that
the reader's remaining gap was silence: cut common "abstains", roughly half of
printed meters go unread. Both halves of that turn out to be artefacts of the
corpus it was measured on.

On a corpus widened from 5 sources to 11, the reader was **wrong three times**,
and the largest wrong class was the one the 08 work believed it had made safe by
*withholding* a template. Two fixes later it is wrong none.

| | 08 corpus (14 pages, 5 sources) | + 09 (16 pages, 6 more sources) | after |
|---|--:|--:|--:|
| WRONG | 0 | **3** | **0** |
| correct | 8 | 10 | 12 |
| missed (printed, unread) | 0 | 2 | 3 |
| correct silences | 21 | 40 | 40 |

The 08 half reproduces **exactly** on today's tree — 8 / 0 / 0 / 21, unchanged
since 2026-08-31, and unchanged again by both fixes. Nothing regressed. The new
pages were always failing; there was no page in the corpus that could say so.

`orchestral_eval --omr-ned` is **identical to the edit** across both fixes —
0.1328 / 942, A/B'd on this tree with the other agents' files held fixed. It
could not have moved: all three canonical fixtures print DIGIT meters, read
18/18, 21/21 and 38/38, so neither the letter path nor any agreement floor
below 1.0 can touch them. (The 942 differs from the 965 recorded at `197199a`
because of another workstream's uncommitted work in this shared tree, not this.)

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

---

## 5. Attribution — every page that does not read its printed meter

Ranked by count, over the four failing systems of the widened corpus.

| # | cause | pages | evidence |
|--:|---|--:|---|
| 1 | **cut common read as `C`** | 2 | Mozart 40 i, Brahms 4 i — section 2. FIXED |
| 2 | **template-vs-font: a Litolff `3` matches Bravura's `6`** | 1 | Beethoven 3 i — section 3. Now an abstention, not a wrong answer |
| 3 | **the header window is the BRACKET, not the header** | 1 | Dvořák 9 i — below |
| 4 | **the print is illegible** | 1 | Bruckner 5 i — clef, key and meter fuse into one blob at 500 dpi |
| — | ~~missing candidate meter~~ | **0** | measured and refuted — below |

### The missing candidate meter costs nothing, because it is not what stops that page

`--add-meters 4/8` was run over the full corpus and changed **not one line**:
Dvořák 9 i is still `MISSED`. With the threshold removed entirely, no staff on
that page reads 4/8 at any score — the twelve best candidates are `4/4` and
`7/4` at **0.366–0.478**, every one of them inside the false-read band the
docstring gives as 0.31–0.49.

The cause is upstream of the meter. Dvořák's header cells come out **301 px
wide** at 600 dpi against Beethoven 3's 1600, on a staff whose spacing is 100 px
either way — three staff spaces of window. Dumping them shows what is in there:
solid black. The staff's left edge landed on the **system bracket**, so the
window is the bracket and the clef, key and meter are all outside it. That is a
`staff_header` / `staff_detector` fault and it is left where it is, named.

**So the whole of section 1's candidate-list gap is a gap in name only.** Adding
a template for a meter the reader cannot see is not a fix; it took one page and
one flag to find that out, which is why it was the first question asked.

### Bruckner, for completeness

The clef, key signature and meter are one fused blob on all 19 staves at 500 dpi
(`probe_cut_stroke.py` finds no `C` match above threshold anywhere on it). No
meter reader can be asked to do better here, and abstaining is the right answer;
its truth is carried by the work's MusicXML, not by anything legible on the page.

---

## 6. What an unread meter costs downstream, and what the instrument gets wrong

`downstream_cost.py` transcribes Beethoven 3 i **once** and then rewrites the
meter on the built result before each export, so the arms differ in one field and
nothing else — same detections, same durations, same clefs.

⚠️ **The obvious construction is not a control, and was run first.** Re-running
the page with `--dossier` does supply the right meter, but a dossier also seeds
every staff's clef and key signature, so that arm differs in the pitches too and
its bar-check count cannot be attributed to the meter.

| arm | `\time` emitted | LilyPond bar-check failures |
|---|---|--:|
| **wrong** — `6/4`, how the page read before today | 6/4 × 12 | **390** |
| **as read now** — abstains, exporter falls back | 4/4 × 12 | **164** |
| **right** — the work's own 3/4 | 3/4 × 12 | 270 |

**The wrong meter costs +226 bar-check failures over no meter at all** — 138%
more — on a page of 12 staves and 144 measures. That is the number that prices
today's fix: turning that reading into an abstention is worth more than every
reading the layer has ever added on this page. A meter is believed by every bar,
and being wrong about it is not a cosmetic `<time>` element.

⚠️ **And the third row is a warning about the instrument, not about 4/4.** The
truth scores WORSE than the fallback here, and it is not because 4/4 is better:
a bar check fires when a bar's durations do not sum to its meter, and this page's
durations are over-long (`phase1_warning` on the cells: "measure width is >2× the
staff median — Phase 1 likely missed a barline"). A longer nominal bar absorbs
more over-long content, so the count rewards the LONGER meter whenever the
recognition over-fills its bars. The 08 work's Beethoven 5 measurement (154 →
104) is safe from this because it moved 4/4 → **2/4** and improved anyway, which
is the direction the bias works against. Read this instrument as evidence only
when the meter it favours is the shorter one.

---

## 7. Fixes and refusals

| | | full corpus (30 systems, 11 sources) | canonical benchmark |
|---|---|---|---|
| baseline | | WRONG 3, correct 10, missed 2, silences 40 | 0.1328 / 942 |
| **fix 1** | read the stroke through the `C` by position | WRONG **1**, correct **12** | identical, A/B'd |
| **fix 2** | the vote's agreement floor 0.5 → 0.70 | **WRONG 0**, correct 12, missed 3 | identical |
| refused | adding `timeSigCutCommon` to the candidate list | WRONG 3 → **12** | — |
| refused | adding `4/8` to the candidate list | no line changes | — |
| refused | ranking the vote by median score | identical to fix 2 | — |

**Fix 1 — the stroke, read by position** (`_looks_cut`). Detailed in section 2.
The construction matters as much as the number: the cut reading rides on a `C`
that has already cleared the threshold and the vote, so **no new false-positive
surface exists** — a page that abstains still abstains, a page that reads 3/4
still reads 3/4, and the only outcome that can change is a `C` becoming a `C|`.
The template stays out of `DEFAULT_METERS`; the 08 measurement of what putting
it in costs is still correct.

The locator now also carries `symbol` ("common" / "cut") the way
`rhythm.parse_time_signature` does from a detection. Commit `197199a` earlier
tonight made the exporter write the glyph and measured it at 3 musicdiff edits
per staff; the locator exists for the pages the DETECTOR cannot read, and was
dropping the fact that it had just matched a letter template to get its answer.

**Fix 2 — half a system is not agreement.** Detailed in section 3. Every one of
the 12 correct readings across both corpora is agreed by **0.909 of its system or
more**; the one wrong reading by exactly **0.500**; every floor in 0.55–0.90
gives the identical table. 0.70 is the middle of that plateau.

**Refused: putting the cut-C template in the candidate list.** WRONG 3 → 12 —
nine systems that print no meter claim one — *and* it does not even fix what it
was for: Mozart 40 still votes `C` 10/11 and Brahms 4 12/13, because a `C` is a
subset of a cut-C's ink and the template with less to account for scores higher.
`sweep_cutC.json`.

**Refused: adding 4/8.** Section 5 — it changes nothing, because the page that
prints it has no header window to read.

**Refused: ranking the vote by median score instead of by count.** It picks the
right answer on the one page where the majority is wrong — Beethoven 3's correct
`3/4` reads have median 0.620 against the winning `6/4`'s 0.561 — and buys
exactly nothing, because `3/4` is read on 3 staves of 12 and the agreement gate
refuses it under either rule. Identical verdict table, one documented principle
("agreement across staves is the evidence, not the strength of any one reading")
weakened for it.

### The margin that is left, stated honestly

A cut common scores **0.545–0.608** as a `C` where a plain `C` scores
**0.741–0.821**: the stroke is ink the C template cannot account for, and it
costs about 0.20 of NCC. Every cut staff in the corpus clears the 0.50 floor, but
the worst does so by 0.045. **Do not lower the floor to widen that margin** —
0.49 is where the false reads on meterless pages sit, and the whole layer is
built on preferring an abstention to a wrong answer. Bruckner 5, which misses
entirely, misses on print quality rather than on this margin.

---

## What still does not read a printed meter

* **A header window that is not the header** — Dvořák 9 i. `staff_header`, not
  this layer. It is the largest single remaining cause and it is one page here
  only because the corpus is small; the same fault would silence any page whose
  staff left-edge lands on the bracket.
* **A print too degraded to separate clef from meter** — Bruckner 5 i.
* **A font whose `3` is Bravura's `6`** — Beethoven 3 i, now an honest silence.
  Fixing it means either per-publisher templates or a numerator read that is not
  a whole-glyph correlation; neither is a small change and neither was attempted.
* **Mid-system meter changes**, unchanged since 08: the reader reads the head of
  a system, and `rhythm.drop_uncorroborated_meter_changes` only decides whether
  to believe a change the detector claims.
