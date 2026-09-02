# Key signatures: reading the glyph instead of reassembling the ink (2026-08-31)

The first end-to-end run read key signatures on **2 of 12 staves**, and that was
the largest remaining gap on the page: the pipeline put three quarters of the
noteheads on the right line and then spelled them wrong, because ten staves in
three flats were carrying no signature at all.

## Where it was failing

Not the clef gate, which was the obvious suspect. Given the *correct* clef for
every staff, `key_signature_locator` still reads only 2 of the 12 — and eight of
the ten it misses print three flats plainly enough to read by eye.

The locator finds accidentals by thresholding the header to an ink mask,
clustering connected components and keeping the accidental-sized ones. On this
scan the staff-line removal leaves every glyph in pieces; the clusters come back
0.1 to 1.9 staff spaces tall, and nothing of accidental size survives to be
found.

## What replaced it

`tools/omr/key_signature_template.py` finds them the way
`time_signature_locator` finds a meter — by sliding the Bravura `accidentalFlat`
and `accidentalSharp` templates the symbol library already ships. A shattered
glyph still correlates with its own outline; it just does not survive being
reassembled from components.

Two things made it work, and both were found by measuring:

**The search has to be bounded on both sides.** Matched over a whole header, a
flat's outline correlates with the clef well enough to produce a column of
eleven "flats" at one x, scoring 0.57–0.59 against the real flats' 0.65–0.76 —
too close to separate by score. So the window is closed to what lies between the
clef (found by matching its own template, since the caller knows which clef) and
the meter (from `locate_time_signature`, built last week). Both bounds come from
glyphs this repo can already find.

**Positions come from the ink, not the box.** `fit_key_signature` solves for a
constant anchor offset across a run, so what matters is the SPACING between
accidentals. Using the matched box's centre leaves ±0.5 step of jitter in that
spacing — enough for the fit to prefer a five-flat reading of three flats, which
it did on two of the twelve staves. Taking the centroid of the ink inside the
box fixed both.

Standalone, given the correct clef: **11 of 12 staves**, against the locator's 2.

## Two rules that had to be found by breaking things

**The template reader may not infer.** `fit_key_signature` will fill in slots
nothing was detected at, which is right for the locator — that one loses
accidentals to broken ink and cannot invent them. This reader fails the other
way: a spurious match adds an accidental and inference compounds it. On WTC I
p.17, four sharps on every staff, five matches on one staff were fitted as
**seven sharps**. Refusing to infer turns that into an abstention.

**It may not carry across systems.** `key_signature_vote` resolves a part across
systems by taking the reading with the most accidentals, which is sound while
every reader can only under-count. This one can over-count, and that broke the
rule globally: one staff's spurious fifth sharp was carried to *every* treble
staff of all five systems, taking WTC p.17 from 10 correct to 5 correct and 5
wrong. `StaffCandidate.can_carry` now keeps such a reading on its own staff,
where the system's own reference still has to accept it.

## Where it speaks, and why not everywhere

**Gaps only** — where neither the detector nor the locator found accidentals.
That restraint was measured, not assumed. Letting the FULLER reading win instead
— which the vote's own asymmetry argues for — is worth +1 staff on Beethoven 5
p.2 and +2 on the Pastoral, and costs a wrong reading on WTC I p.17, the
cleanest page in the corpus, where the detector was already right. On this
project's terms a wrong signature costs more than a missing one, so: gaps only.

The consequence is visible on page 1. Three staves print three flats, the
detector finds *one* of the three, and the vote then rejects the one-flat
reading for departing from the system — so those staves abstain, when a reader
that was allowed to speak would have got them right. That is a known, priced
loss, not an oversight.

**Staves with no clef read** get the reader too, against the positional default,
entered with a weight too small to justify a departure from the system's modal
signature (`DEFAULTED_CLEF_WEIGHT`). So the vote can keep such a reading where it
agrees with what the rest of the system printed and abstains where it does not —
which is what happens to the Viola, whose default of treble is wrong. It moves
the clef gate rather than lifting it: the check is now the page's, not the
staff's.

## Measured

Beethoven 5 p.1, 12 staves, against the printed page:

| | before | after |
|---|---|---|
| key signatures correct | 4/12 | **7/12** |
| ...of which genuinely read | 2 | **4** |
| wrong values | 1 | **0** |
| exact-pitch recall | 0.571 | **0.619** |
| exact-pitch precision | 0.528 | **0.572** |
| step recall (accidental ignored) | 0.714 | 0.714 |
| duration recall | 0.361 | **0.381** |

The gap between `step` and `exact` — which is the accidental loss, and the whole
reason for doing this — **halves, from 0.143 to 0.095**. Step recall is
unchanged, as it must be: reading a key signature does not move a notehead.

The five staves still wrong are all **abstentions**, not wrong values.

Against the curated ground truth (`benchmarks/omr-key-signature/`, pipeline
mode), where the numbers in `RESULTS.md` come from:

| page | before | after |
|---|---|---|
| beet5-p2 | 10 correct, 0 wrong, 6 missed | 10, 0, 6 |
| pastoral-p2 | 9 correct, 0 wrong, 9 missed | **11**, 0, 7 |
| wtc-p17 | 10 correct, 0 wrong | 10, 0 |

**No page loses a correct reading and none gains a wrong one.** The Pastoral is
where the new reader earns its place: +2 staves on a scan the locator could not
read.

Across the first six pages of the scan, staves the readers spoke for went
**33 of 113 (29%) to 44 of 113 (39%)**.

One honest note on a change that did not pay: readings weighted below one
accidental are now excluded from the system's modal reference, on the theory
that a weak reading should be able to agree with a system without defining it.
It was expected to recover a staff on the Pastoral and measured neutral on all
three pages. It is kept as an invariant, not for a gain.

## Reproducing

```bash
python3 benchmarks/omr-key-signature/eval_key_signatures.py --mode pipeline
python3 benchmarks/omr-first-run-2026-08/eval_first_run.py --stem beet5-p1-keyfix
```
