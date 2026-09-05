# Dynamics letters: should they be read the way clefs are?

*2026-09-04. Asked by Sean; measured rather than reasoned about.*

**Short answer: half of it, and not the famous half — and the half that
transfers is proven on engraved pages and NOT on scans.**

The clef work is two separable ideas that get remembered as one. The idea it is
known for — *stop classifying, start measuring, because the glyph's position IS
its meaning* — does not transfer to dynamics at all. The idea that actually
earned the clef locator its numbers — **POSITION BEFORE SHAPE**, which took its
false positives 48 → 13 → 5 while every shape threshold tried on the same
problem either failed or cost real clefs — transfers directly, and nothing in
the dynamics path uses it today.

---

## 1. Why the famous half does not transfer

A clef needed geometry because alto and tenor are **the same glyph on different
lines**: a class label cannot separate them even in principle, so
`clef_geometry` measures which line the glyph names. There is no analogue for a
dynamic letter. A `p` is a `p` at any height; height carries no part of its
identity. What a dynamic letter's meaning does depend on is its **horizontal
neighbours** — `f`+`f` is one `ff`, not two `f` — and that assembly already
exists and works: `export.measure_dynamics` joins letters into words by
x-adjacency, and `_DYNAMIC_WORDS` drops runs that spell nothing.

The clef **locator** half does not transfer either, and for a sharper reason:
it exists because the model is *blind* to clefs on orchestral scans (2% coverage,
and a fine-tune, ensemble voting and a CV locator have all failed to move it).
The detector is not blind to dynamics. It finds 47 letters on one scanned
Brahms page. **The dynamics failure is over-eagerness, not blindness** — which
needs a gate or an arbitration, never a finder.

The clef/key-signature **vote across staves** is the one that looks tempting and
is dangerous. An orchestral tutti prints the same dynamic on twenty staves at
one x, so a column vote has plenty of signal — but a `p` standing against
neighbouring `f`s is real music, a soloist against a section, and a vote would
delete exactly the information a reader wants. That is what
`StaffCandidate.can_carry` was invented to stop for key signatures.

---

## 2. What the letters do carry: a placement band

`measure_dynamics` uses **no vertical information at all** beyond "these two
letters are level with each other". Nobody asks whether a letter is standing
where a dynamic is printed. It turns out that question has a very clean answer.

Measured in staff spaces **below the bottom staff line** of the staff whose cell
holds the detection — in page pixels through `bbox_page_px` and
`upscale_factor`, never in the cell's own frame, because cell padding varies
with how crowded the staves are and would move the number without moving the
ink.

**Corpus: 9 editions, 9 publishers, 18 pages, 1246 dynamic letters.** Nine
because the clef work's own rule is that a threshold measured on one edition is
not a threshold — adding a second edition to the clef sweep took the reported
false positives from 7 to **48** without a single regression; they had always
been there and one corpus could not see them. The pages are the ones the hollow
labeling campaign already sampled, so they are known to carry orchestral music.
`corpus.json` has the list.

```
edition                    pg  let  own above below  none    own population  empty gap
breitkopf-brahms1           2  164  109    52     0     3    +0.02 .. +4.18  -5.29 .. -0.15
durand-lamer                2  104   81    18     0     5    +0.92 .. +5.18  -4.52 .. +0.92
eulenburg-scheherazade      2   97   61    29     0     7    +0.56 .. +5.54  -4.74 .. +0.56
jurgenson-tchaikovsky1      2    1    0     1     0     0                 -            -
litolff-beethoven5          2   91   82     9     0     0    +0.24 .. +5.32  -7.32 .. +0.24
novello-elgar1              2   82   40    42     0     0    +0.17 .. +2.93  -4.75 .. +0.17
peters-mahler5              2  302  231    66     0     5    +0.22 .. +4.28  -4.34 .. -0.52
simrock-dvorak9             2  234  178    50     0     6    +0.02 .. +3.56  -3.04 .. -0.19
universal-mahler1           2  171  129    33     0     9    +0.50 .. +5.59  -5.74 .. +0.50
POOLED                        1246  911   300     0    35
```

**The band holds across all nine publishers**: every edition's own-population
starts within 0.9 spaces of the bottom staff line and ends by +5.6, and the
pooled widest empty interval is **−3.04 to −0.52 spaces, 2.53 wide**, with
nothing in it. That is a constant read off a gap rather than tuned into one —
the same shape as the augmentation-dot offsets (bimodal at 0.00 and +0.50, empty
from +0.57 to +3.75) and the clipped-notehead height floor.

⚠️ **The first cut of this probe used a lower edge of +0.5 and manufactured its
own outliers**: 27 of the 44 letters it called unattributable were sitting
within half a space of the bottom line, where a dynamic printed tight against
its staff belongs. The band's lower edge has to come from the gap, and the gap
is below zero. `--band-lo` sweeps it.

⚠️ **`jurgenson-tchaikovsky1` finds ONE letter on two pages** and is not
evidence about placement either way. It is left in the table rather than dropped
because it is evidence about something else — that edition is close to blind for
dynamics, which is a detection problem this measurement does not address.

---

## 3. ⚠️ An out-of-band letter is NOT a false positive, and that decides the fix

This is the finding that changed the recommendation, and it is why the probe
classifies rather than thresholds.

A measure cell is cut with 4–6 staff spaces of padding so ledger notes are not
sliced off (`measure_extractor.PAD_ABOVE_STAFF_LINES`), and on a conductor's
page that padding reaches into the gap where the **neighbouring** staff prints
its dynamics. So a letter 5.8 spaces above its own staff's bottom line is
usually not junk — it is the staff above's `f`, seen from the cell below it.
Every letter is therefore classified as one of:

| | meaning |
|---|---|
| `own` | standing in its own staff's band — the mark, where marks go |
| `above:N` | standing in the band of staff N above it — the neighbour's ink through this cell's padding |
| `none` | in no staff's band — the candidate false positive |

Over the 1246 scanned letters: **911 `own` (73%), 300 `above` (24%), 35 `none`
(2.8%), and 0 `below`.**

**Every single `above` letter belongs to the immediately preceding staff — a
distance of exactly 1, with no exceptions anywhere in the corpus.** That is the
padding mechanism confirming itself: the pad reaches one staff and no further.
A positional story that produced a scatter of distances would be describing
something else.

---

## 4. Three policies, scored

The only arms that can be *scored* are those with truth. Words are counted, not
letters, because the exporter emits one `<direction>` per word and `ff` is two
letters — and the probe restates `measure_dynamics`'s joining rule in page
pixels (re-attribution moves a letter into a staff whose cell it was never cut
into, and no canonical frame holds both), so it **cross-checks its own joiner
against `export.measure_dynamics` on every page** and reports whether they agree.

| policy | what it does |
|---|---|
| `now` | every letter — what ships today |
| `gate` | keep only letters in their **own** staff's band |
| `re-attribute` | give each letter to the staff whose band it stands in, then drop copies that are the same physical ink |

### Engraved — the canonical 11 works

```
work                            let  own  abv none |   now  band reattr  truth |    staves exact (contested)
beethoven-sym3-mvt1              25    6   19    0 |    23     6     23     23 | 13->19 count, 12->17 words /19
beethoven-sym5-mvt1              22   14    8    0 |    16    10     13     13 |  3-> 9 count,  3-> 7 words / 9
brahms-sym1-mvt1                 29   18   10    1 |    29    18     23     19 |  9->14 count,  9->12 words /20
brahms-sym4-mvt1                 20   14    6    0 |    14     8     14     15 | 13->15 count, 12->14 words /16
bruckner-sym5-mvt1               34   21   13    0 |    23    12     19     16 |  1-> 3 count,  1-> 3 words / 8
dvorak-sym9-mvt4                 10    4    6    0 |     6     2      5      5 |  3-> 5 count,  3-> 5 words / 5
mahler-sym5-mvt1                  5    2    3    0 |     4     2      4      3 |  0-> 1 count,  0-> 1 words / 2
mozart-sym40-mvt1                 6    5    1    0 |     6     5      5      5 |  4-> 5 count,  3-> 4 words / 5
mozart-sym41-mvt1                25   15   10    0 |    25    15     25     25 |  8->16 count,  8->16 words /16
tchaikovsky-sym4-mvt2            13    9    4    0 |     5     2      3      5 |  3-> 5 count,  1-> 4 words / 7
tchaikovsky-sym6-mvt2            32   16   15    1 |    18     9     14     13 |   abstains (parts != staves)
TOTAL                                              |   169    89    148    142 | 57->92 count, 52->83 words /107

emitted/truth   now 1.19   gate 0.63   re-attribute 1.04
```

**Re-attribution is a large, consistent win here**: over-emission 1.19 → 1.04,
and staves whose dynamics are exactly right by WORD go **52 → 83 of 107**. Not
one work gets worse.

### Scanned — 11 pages, 5 publishers, hand-verified windows

```
page                            let  own  abv none |   now  band reattr  truth |    staves exact (contested)
bach-brandenburg3-mvt1-468678-p1  2    1    0    1 |     2     1      1      0 |   abstains (parts != staves)
beethoven-sym5-mvt1-575951-p1    17   15    2    0 |    11    10     11     13 |   abstains (parts != staves)
beethoven-sym5-mvt1-575951-p2   144  125   18    1 |    92    78     88    154 |   abstains (parts != staves)
beethoven-sym5-mvt1-984073-p1    18   16    2    0 |    12    11     11     13 |  6-> 5 count,  5-> 5 words / 7
beethoven-sym5-mvt1-984073-p2   142  121   21    0 |    86    70     85    154 |   abstains (parts != staves)
brahms-sym1-mvt1-317803-p1       38   28    9    1 |    22    13     14     19 |  5-> 5 count,  4-> 2 words /14
brahms-sym1-mvt1-317803-p2       90   61   27    2 |    65    41     49     48 |   abstains (parts != staves)
dvorak-sym9-mvt1-405834-p5       25   22    2    1 |    15    11     13     15 |  5-> 5 count,  4-> 4 words / 8
dvorak-sym9-mvt1-405834-p6       47   45    2    0 |    22    21     22     28 |  7-> 9 count,  3-> 5 words /13
mahler-sym5-mvt1-local-p2        12    7    5    0 |     8     4      8      4 |   abstains (parts != staves)
mahler-sym5-mvt1-local-p3        63   51   11    1 |    41    29     32     43 |   abstains (parts != staves)
TOTAL                                              |   376   289    334    491 | 23->24 count, 16->16 words /42

emitted/truth   now 0.77   gate 0.59   re-attribute 0.68
```

⚠️⚠️ **AND ON SCANS IT DOES NOTHING — 16 → 16 staves exact by word.** The
engraved result does not carry. The pooled ratio says we under-emit here (376
words against 491, 0.77) — but see §8: that is **two pages of the same music**,
and across the other nine we over-emit slightly, just as the engraved arm does. Re-attribution cannot fix an absence, and moving letters
lowers the count further (0.77 → 0.68) — some of that legitimately, by reuniting
an `ff` split across two cells into one word, which is why the ratio alone is
not the verdict and the word-exactness column is.

⚠️ **The scan attribution evidence is thin**: 4 of 11 pages, 42 contested
staves. Seven pages abstain because the staff→part join does not resolve, and
`brahms-sym1-mvt1-317803-p1` gets *worse* by word (4 → 2). A "no effect" over
42 staves is a weak negative, not a strong one — but it is what there is, and it
is not the engraved arm's answer.

### The band's lower edge is a plateau, not a peak

```
 band lo | ENGRAVED                        | SCANNED
   -1.50 | reattr/truth 1.04  exact 92/107 | reattr/truth 0.68  exact 24/42
   -1.00 | reattr/truth 1.04  exact 92/107 | reattr/truth 0.68  exact 24/42
   -0.50 | reattr/truth 1.04  exact 92/107 | reattr/truth 0.68  exact 24/42
   +0.00 | reattr/truth 1.04  exact 92/107 | reattr/truth 0.68  exact 24/42
   +0.25 | reattr/truth 1.04  exact 92/107 | reattr/truth 0.68  exact 24/42
   +0.50 | reattr/truth 1.04  exact 92/107 | reattr/truth 0.67  exact 24/42
   +1.00 | reattr/truth 1.04  exact 92/107 | reattr/truth 0.66  exact 24/42
```

Nothing moves anywhere in −1.5 … +0.25 on either arm, which is what a constant
read off a gap should look like.

**The gate is the obvious fix and it is the wrong one on both arms.** It
under-emits (0.63 engraved, 0.59 scanned), because a mark whose only surviving
detection sits in the neighbour's cell is deleted rather than moved.
Re-attribution is the arbitration this actually needs — the same shape as
`_dedupe_cross_staff_detections`, which already resolves contested *noteheads*
by ledger ladder, then instrument range, then distance. Dynamics reach that
function today and fall through to **distance alone**, which is precisely the
rule the ledger work found to be wrong for ink sitting in a gap the engraver
opened on purpose.

**Per-staff exactness is the control that separates "the right number of marks"
from "the right marks on the right staves"** — a count can be right for the
wrong reason. It joins parts to staves by ordinal and **abstains unless the two
counts agree**, the same rule the dossier slot-level checks use.

---

## 5. Refuted: confidence

```
CONFIDENCE as a filter (own n=911, unattributable n=35):
  threshold  none removed   own LOST
       0.30        1/35       25/911
       0.40        6/35       87/911
       0.50       13/35      140/911
       0.60       18/35      233/911
       0.70       19/35      338/911
       0.80       27/35      557/911
```

Priced as the trade a threshold actually makes, rather than by comparing
medians — which differ (0.76 against 0.56) and would flatter it. To remove half
the unattributable letters you discard **233 of 911** good ones.

The obvious cheap filter does not work, which is worth recording so nobody
re-tries it. It is the same result shape as the clef work's rejected
discriminators — ink coverage and whitespace gutters both separated on one
corpus and inverted on another.

---

## 6. ⚠️ What this measurement cannot decide

**A dynamic printed ABOVE staff N sits in the same place on the page as one
printed BELOW staff N−1.** Position cannot separate those two, in principle,
and the re-attribution policy always chooses the second reading. On the
LilyPond fixtures that is simply correct, because LilyPond puts dynamics below.
On real editions it is a convention that varies — some print above the top
staff of a group, vocal scores print above the voice.

Measured over the scan corpus: of the 300 letters re-attribution moves, **50
are a dedupe** (the target staff already holds its own in-band copy) and **250
(83%) are that staff's sole evidence**.

⚠️ **That 83% is not a measure of doubt — it is the upstream dedupe's
signature.** `transcribe._dedupe_cross_staff_detections` runs before the
exporter and removes the twin copy already, resolving the contest **by distance
to the nearer five-line band** — and for ink sitting in the gap the engraver
opened between two staves, the nearer band is often the wrong one. So the mark
exists once, in the wrong cell, and the letter is sole evidence because the
pipeline made it so. **This is the same failure the ledger-ladder work found for
noteheads** — distance is wrong for exactly the case the cell padding exists
for — and it is why the fix belongs in that function, as another evidence tier
beside the ledger ladder and the instrument range, rather than as a filter in
the exporter.

Where the target staff already holds its own in-band copy, the move is a
**dedupe** and the ambiguity does not arise. Where the moved letter is the
staff's only evidence, re-attribution is making a judgement about the edition's
placement convention, and that is the fraction to worry about.

The disambiguator would have to be something other than position — which staff
has notes at that x, or the edition's own convention learned from the pages
where the answer is unambiguous. That is a further measurement, not a
refinement of this one.

---

## 7. ⚠️ What the corpus cannot see

- **The scored scan truth's notes come from the reference encoding, not from
  reading the scan.** A dynamic the engraver printed and the encoder omitted
  counts against us and is not our error. The windows themselves are
  hand-verified, which is what makes the page-to-measure join trustworthy.
- **The engraved fixtures are all LilyPond renders** — eleven works, but one
  engraving convention and one placement rule between them. That is why the
  engraved arm agreeing is not evidence that the band generalises, and why the
  scan arm is nine publishers. ⚠️ Those fixtures are build products and were
  being regenerated by a concurrent session while this was measured; the numbers
  above come from a snapshot of the complete canonical 11 taken at once, not
  from a directory read progressively.
- **Counts, not alignments.** Except for the per-staff control, a policy that
  emits the right number of marks in the wrong measures scores the same. Even
  the per-staff control compares a staff's SET of words, so two dynamics swapped
  between measures of one staff score as correct.
- **The probe's joiner is a restatement of `export.measure_dynamics`, not the
  function itself**, because re-attribution moves a letter into a staff whose
  cell it was never cut into and no canonical frame holds both. It is checked
  against the real one on every page — and that check earned its keep: the first
  version compared box CENTRES where the exporter compares LEFT and TOP edges,
  and disagreed on 4 of the 11 scanned pages until it was corrected.
- **Hairpins are out of scope.** `dynamicCrescendoHairpin` /
  `dynamicDiminuendoHairpin` are the ninth export gap, still open in
  `export_coverage.KNOWN_GAPS`, and they are a different problem: partial
  detection rather than misplacement.

---

## 8. Status: measured, NOT shipped — and the scan arm is why

Nothing in this directory changes the pipeline, and on this evidence nothing
should yet. The mechanism is established: the band is real across nine
publishers, the out-of-band letters are the neighbour's ink through the cell
padding, and the upstream dedupe is keeping the wrong copy by distance. The
*fix* is established on engraved pages (52 → 83 staves exact by word) and
**flat on scans** (16 → 16), which is the domain that matters most for this
project and the one where the pipeline's dominant dynamics error turns out to be
recall, not placement.

### Why scans under-emit — answered (`--funnel`)

```
page                                let  words  lost:empty  exported  truth
beethoven-sym5-mvt1-575951-p2       144     92           4        88    154
beethoven-sym5-mvt1-984073-p2       142     86           3        83    154
mahler-sym5-mvt1-local-p3            63     41           5        36     43
brahms-sym1-mvt1-317803-p2           90     65           0        65     48
  ... 7 more pages ...
TOTAL                               598    376          14       362    491

  letters whose run SPELLS a dynamic :  549  -> 376 words
  letters whose run spells NOTHING   :   49  in 31 runs, all discarded
  discarded runs: {'s': 15, 'fs': 3, 'z': 3, 'fmp': 2, 'm': 2, 'ffs': 1, ...}
```

**"Read but not written" is real and is the MINORITY.** Of the 129-mark
shortfall:

- **14 marks are computed and thrown away.** A measure with no detected events
  takes the whole-measure-rest branch, which never calls `_mxl_voice_events` —
  the only `<direction>` emitter — so `measure_directions()` is called, its
  result assigned to `_dyn`, and `_dyn` never used. Both of `export.py`'s two
  measure emitters have it, identically. ⚠️ **This is the bug CLAUDE.md records
  the 11-work engraved benchmark provably cannot see, and it predicted that a
  SCANNED work would be where it finally triggers — because a staff genuinely
  rests through a marked bar and the detector finds nothing in it, where an
  engraved page puts an event in every bar. It does.** The attribution is exact:
  `words formed − words in an eventless measure == words exported` on **all
  eleven pages, to the mark**.
- **≤31 more are the same family one step earlier.** 49 detected letters sit in
  runs that spell no dynamic and are discarded whole — dominated by a lone `s`
  (15 of 31), which is an `sf` whose `f` was not detected. The partial read is
  thrown away rather than kept as what it is.
- **The remaining ~84 were never read at all**, and they are not spread out:
  **the two Beethoven 5 p.2 scans (the same 32-bar window in two editions)
  supply 137 of the shortfall between them**, reading ~85 of 154. Across the
  other nine pages we emit **191 against a truth of 183** — over-emitting
  slightly, exactly like the engraved arm.

⚠️ **So "scans under-emit" was too broad a claim.** One dense, small-print page
under-reads badly; the rest behave like the engraved corpus. The re-attribution
result is still flat on scans, but the reason is not a general recall collapse.

### Still open

**A scan arm that can actually see attribution.** Seven of eleven pages abstain
on the staff→part join; the hand-verified `staves[].parts` rows in
`omr-scan-e2e-2026-09/works.json` resolve four. More verified rows would turn a
weak negative into a real one either way.

When it is shipped, re-attribution belongs in
`transcribe._dedupe_cross_staff_detections` as another evidence tier beside the
ledger ladder and the instrument range — not as a filter in the exporter, since
by then the wrong copy has already been deleted. The band constant should be
read off the gap the population shows, not off `REPORT_BAND`, which exists only
to label letters for reporting.

```bash
python3 benchmarks/omr-dynamics-band-2026-09/probe_dynamic_band.py \
    --scans <dir of scan transcriptions> \
    --scored <dir of scan-e2e row transcriptions> \
    --fixtures benchmarks/omr-orchestral-e2e/fixtures \
    --json-out benchmarks/omr-dynamics-band-2026-09/results.json
```

## Related: the alias fault this work tripped over

Looking for the dynamics consumers turned up a separate, live problem, fixed in
`776b6bc`: the 208-class space spells 32 glyphs under a **second, coarser name**
(`dynamicLetterF` at id 192 for `dynamicF` at id 95) and every consumer in this
pipeline was written against one spelling. It costs nothing today — the coarse
block fires zero times across this whole corpus — but 26 of the hollow
campaign's hand-drawn boxes are classed `dynamicLetterF`/`P`/`S` and
`catalog.yaml` carries the coarse spelling, so the next fine-tune trains those
ids into a detector whose exporter cannot spell them.
