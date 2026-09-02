# The meter, read from the header (2026-08-31)

The first end-to-end run on a real scan (`benchmarks/omr-first-run-2026-08/`)
found the pipeline writing **4/4 onto a 2/4 page**. This is that fixed, and the
fix has two halves, because the failure did.

## What was actually wrong

Not "the meter was missing". The page reported a meter, confidently, on all
twelve staves, and it was wrong:

```
staff time_signature: {'raw': 'C', 'source': 'detected_propagated', 'votes': 3}
```

Two defects in series produced it.

**The detector never sees a time signature in a header.** On page 1 of the
IMSLP Beethoven 5 there are zero time-signature detections in any staff's
header — on a page that prints `2` over `4`, legibly, on every one of the twelve
staves. The five `timeSig4` boxes it did fire were at x = 1463, 1782, 2157,
2157 and 2024, which are **barline positions** in the middles of bars 6 to 12.

**And a lone digit becomes a meter.** `parse_time_signature` guesses
denominator 4 from a single digit, so each barline fragment became 4/4. Three
of them agreed, `_dominant_detected_meter` propagated the majority, and a meter,
once read, is carried onto every later measure of its staff — so each false
reading also voted for itself once per remaining bar. The page went out as
common time and nothing downstream was placed to doubt it.

## The two halves of the fix

**A reader**, `tools/omr/time_signature_locator.py`. The clef got a CV locator
and the key signature got a slot-table geometry reader; the meter never got one,
and it is the easiest of the three to read by shape, because its geometry is
rigid: the numerator fills the upper two staff spaces, the denominator the lower
two, centred on each other. So its vertical position is known before the search
starts and the search is one-dimensional. A composite template per candidate
meter — built from the Bravura `timeSig0-9` glyphs this repo already ships in
`tools/omr/symbol_library/` — is slid along the header window in x. Readings are
then **voted across the staves of the system**, because a meter is printed on
all of them.

**Two guards**, both in `rhythm.py`, because the false meter arrived by two
routes.

`drop_uncorroborated_meter_changes` — a time signature is printed at the start
of a staff or where the meter changes, and a change is a system-wide event,
printed on every staff at the same bar. A change appearing mid-system on one
staff alone is reverted to the meter in effect before it. That is what stops one
misread bar from rewriting the rest of its staff. It alone takes page 1 from a
confident 4/4 to an honest silence, with no reader involved.

`_dominant_detected_meter` now counts **staves, not measures**. A meter is
carried onto every later measure of its staff, so counting measures counts one
reading many times over — see the six-page table below, where a single detection
at confidence 0.42 became eighteen unanimous votes. A staff is the unit that
witnesses a meter, and the winner must additionally be read on half the page's
staves, because that is where a meter is printed.

## Measured

`sweep_time_signatures.py`, over a corpus that is deliberately **half
negatives** — pages that print no time signature, which is every system after
the first in almost any score. A reader that answers more often would look
better on any metric that only counts answers, so the negatives are the test
that matters.

```
beet5-scan-p1      sys0  OK   want=2/4  got=2/4  votes=11/12  median 0.55
beet5-scan-p2..p6  (10 systems)  want=None  got=None       — silent
e2e-beethoven      sys0  OK   want=2/4  got=2/4  votes=18/18  median 0.76
e2e-brahms         sys0  OK   want=6/8  got=6/8  votes=19/21  median 0.78
e2e-mahler         sys0  OK   want=2/2  got=2/2  votes=38/38  median 0.69
ravel-bolero       sys0  OK   want=C    got=C    votes=24/27  median 0.76
handel-reduction   sys0  OK   want=C    got=C    votes=12/12  median 0.76
bach-wtc           sys0  OK   want=C    got=C    votes=10/11  median 0.75
wtc-book-p2        sys0  OK   want=C    got=C    votes=2/2    median 0.76
wtc-book-p2        sys1..5       want=None  got=None       — silent
wtc-book-p3        (6 systems)   want=None  got=None       — silent

correct 8   wrong 0   missed 0   correct silences 21
```

Eight readings, **zero wrong**, twenty-one correct abstentions — across a 600
dpi scan of 19th-century type, a third-party engraved PDF, and pages set by
LilyPond in a different font from the templates.

## Common time, added 2026-08-31, and the one withheld with it

The first version read every meter written as digits and none of the two written
as a letter, which is most of the repertoire. `timeSigCommon` and
`timeSigCutCommon` were added to `symbol_library/builder.py` and the library
rebuilt — every pre-existing template came back byte-identical, which is the
check that mattered, since the clef and key-signature readers share it.

A letter meter is one glyph two spaces tall centred on the middle line, so it is
padded into the same four-space box and the search stays one-dimensional. `C`
turned out to be the strongest reading in the corpus: five common-time pages at
0.745 to 0.761, against 0.50 to 0.62 for the scanned digit meters.

**Cut common was measured and withheld.** A C with a stroke through it
correlates with any vertical ink crossing any rounded blob, and with it enabled
the sweep read a meter on **seven systems that print none** — Beethoven 5 scan
pages 4 and 5, and four systems of WTC I Prelude 1 — at 0.51 to 0.56, over a
threshold of 0.50:

```
beet5-scan-p4  sys0  WRONG  want=None  got=C|  votes=7/11  0.5314
beet5-scan-p5  sys0  WRONG  want=None  got=C|  votes=5/9   0.5109
wtc-book-p3    sys0  WRONG  want=None  got=C|  votes=2/2   0.5554
```

No page in the corpus prints a real cut-C, so there was no evidence for what a
true one scores and no basis for a threshold between them. 2/2 spelled in digits
is still read — the Mahler fixture, 38 staves of 38. The glyph stays in the
library, so restoring it is one line plus the corpus page that would justify it.

### End to end on the page that started it

All figures against the corrected 16-measure window — the page was scored
against 17 until the ground-truth probe was found to be counting the time
signature itself as a barline (`../omr-first-run-2026-08/BARLINES.md`).

| | before | after |
|---|---|---|
| meter emitted | `C` (4/4) | **`2/4`** |
| staves carrying it | 12, from `detected_propagated` | 12, from `header_reader` |
| LilyPond bar-check failures | 154 | **104** |
| pitch recall | 0.612 | 0.612 (unchanged, as expected) |

The bar-check figure is the one that moved: a third of the failures were bars
measured against the wrong meter. Duration recall was unchanged at 0.360 on this
page once the window was corrected — `_reconcile_measure_to_meter` re-reads a
beam level to make a bar land exactly on the meter, and giving it the right
meter to land on helped less here than the earlier mis-scored comparison
suggested.

### Six pages, which is where the second defect showed itself

| page | before | after | truth |
|---|---|---|---|
| 1 | `C` on 12 staves | **`2/4`** on 12 | 2/4 printed |
| 2 | silent | silent | none printed |
| 3 | **`C` on 17 staves** | **silent** | none printed |
| 4, 5, 6 | silent | silent | none printed |

Page 3 is the one that made the vote per-staff. Its common time came from a
**single** `timeSig4` box at confidence 0.42, on one staff of nineteen, in that
staff's first bar — carried forward onto all eighteen of its measures and
arriving at the page vote as eighteen unanimous votes. The mid-staff guard could
not touch it, because it was not a change; it was the staff's opening meter, and
wrong. Counting staves instead of measures makes it one vote out of nineteen,
and the page falls silent.

## Three things that were tried and are not in the code

Each looked good on the corpus it was invented on and failed on the next one.
They are recorded because the next person to touch this will think of them.

**Independent digit matching, then pairing.** Match the numerator band and the
denominator band separately and accept a pair at the same x. The system's
opening barline correlates with `timeSig1` well enough to win the numerator band
on every staff of Beethoven 5 p.1, and the pairing rule then found a `1`
underneath it. Matching the meter as one four-space block removes the failure
by construction.

**Ink coverage** — the fraction of the template's ink actually inked on the
page. It separates cleanly on the scan (true 0.86–0.97, false 0.54–0.83) and
then inverts across corpora: LilyPond's thinner engraving covers only 0.72–0.79,
so engraved TRUE readings score below scanned FALSE ones. A gate tuned on the
scan alone would have rejected every engraved page.

**Whitespace gutters** — blank columns either side, on the theory that a meter
is isolated from the key signature and the first note. True readings measured
0.00–0.33 and false ones 0.00–1.00. No separation at all.

What survived is plain NCC, at 0.50. The honest statement of that margin is that
the closest pair is a single staff — the scan's weakest true reading at 0.505
against its strongest false one at 0.492 — and that **the margin is not what the
decision rests on**. The vote is: a meter must be read on half the system's
staves, and on the negative pages the whole system sits below the bar, so one
staff drifting over it cannot carry a page.

## What is still not read

`timeSigCommon` and `timeSigCutCommon` — the C and ¢ — have no templates in the
symbol library, so a common-time page abstains here. Both entries in the corpus
that print a C are in it precisely to hold that gap open and prove the
abstention. It is a smaller gap than it looks: those two glyphs are distinctive,
the detector reads them well, and `parse_time_signature` already has a path for
them. This reader exists for the case the detector cannot do.

Mid-system meter changes are not searched for either; the reader reads the
meter at the head of a system, and the guard only decides whether to believe a
change the detector claims.

## Reproducing

```bash
python3 benchmarks/omr-timesig-2026-08/sweep_time_signatures.py
python3 benchmarks/omr-timesig-2026-08/sweep_time_signatures.py --per-staff --min-score 0.0
```

The second form shows every staff's best candidate with the threshold removed,
which is how the separation above was measured. The engraved fixtures are
gitignored and rebuilt by `tools.omr.training.orchestral_eval.excerpt`.
