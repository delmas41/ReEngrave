# Reading the words printed inside a system

`wrong direction` was the largest OMR-NED category with **nothing upstream to
consume it**. The four fixes before this one — beams, augmentation dots,
dynamics, tuplets — were all export-and-resolution gaps: the detections were
already sitting in the JSON and nothing read them. Directions are not that
shape. The pipeline had no text detection at all, and the DeepScoresV2 class
that would have supplied one, `textDynamic`, is the class that caused the
Phase 3.4 catastrophic forgetting.

So this reads text **without touching the detector**, and this file is the
measurement.

## Reproduce

```bash
python3 -m tools.omr.staff_labels_surya --serve     # keeps the 650M GGUF loaded
export OMR_SURYA_KEEP_ALIVE=1
python3 -m tools.omr.training.orchestral_eval --omr-ned                     # baseline
python3 -m tools.omr.training.orchestral_eval --omr-ned --direction-text    # with
```

The two probes that decided the design, both of which run on their own:

```bash
python3 benchmarks/omr-direction-text-2026-09/probe_direction_bands.py
python3 benchmarks/omr-direction-text-2026-09/probe_direction_candidates.py \
    benchmarks/omr-orchestral-e2e/fixtures/brahms-sym1-mvt1.pdf \
    --read --crops-dir /tmp/cands
```

## The prize, sized before anything was built

`wrong direction` is `directionins` / `directiondel` and their edits — the
`<words>` a score prints, and nothing else. Opening it with `dump_ops.py`:

| work | direction edits | what they are |
|---|--:|---|
| brahms-sym1-mvt1 | 130 | 8 × `legato`, 4 × `espr. e legato`, `Un poco sostenuto`, `pesante`, `[`, `]` |
| beethoven-sym5-mvt1 | 16 | `Allegro con brio` |
| mahler-sym5-mvt1 | 5 | `molto` |
| **pooled** | **151** | |

**A direction costs its own character count, on either side.** `legato` is 6,
`espr. e legato` is 14, `Un poco sostenuto` is 17 — `AnnExtra.notation_size`
adds `len(content)`. Two consequences that shaped everything below:

1. **Precision and recall are worth the same.** An invented `IIII` costs 4
   exactly as a missed `legato` costs 6. A reader that guesses trades one for
   the other at par, so the gate is arithmetic and not taste.
2. **A near miss is cheap.** `extracontentedit` charges the Levenshtein
   distance, so `Iegato` for `legato` costs 1 rather than 12. It is worth
   reading a word imperfectly; it is not worth inventing one.

## The result

Measured on `main` at `6f64bfa`, immediately before and after:

| | pooled | edits | `wrong direction` |
|---|--:|--:|--:|
| baseline | 0.2209 | 1563 | 151 |
| **with `--direction-text`** | **0.2020** | **1459** | **47** |

Per work, and **every other category is unchanged to the edit** — `wrong note`
831, `wrong flag/beam` 171, `entire measure` 136, `wrong slur` 61, `wrong
accidental` 57, all identical on both sides. It is a post-pass that adds a key
to measures that already exist.

| work | before | after |
|---|--:|--:|
| brahms-sym1-mvt1 | 0.3185 (1256) | **0.2869 (1168)** |
| beethoven-sym5-mvt1 | 0.1775 (221) | **0.1626 (205)** |
| mahler-sym5-mvt1 | 0.0455 (86) | 0.0455 (86) |

**The −104 edits is the same on every tree this was measured against**, which is
worth more than any one absolute figure. Main moved four times during the work
— `81446a0` (cross-staff ledger notes), `6a1b601` (the integration branch,
including the `_staff_measures_xml` refactor these call sites now go through),
`7516768` (default-on left-edge system split), `6f64bfa` (slurs) — and on each
one the baseline differed and `wrong direction` fell by the same amount
regardless (to 61 before the placement rule was corrected, 47 after). The
reader and the slur work compose without interacting: they reach
`_mxl_voice_events` by different doors, slurs riding on the events as
`slur_states` and directions arriving as the `directions=` argument.

**All 14 of Brahms's directions and Beethoven's one were read exactly right,
with zero false positives on either page.** Everything left in the 61 is where
a correctly-read word was attached, not what it says.

What the reader itself reports (`direction_text` in the result JSON), which is
the number to watch rather than the pooled score — see finding 4 for why:

| work | candidates | read | accepted | refused |
|---|--:|--:|--:|---|
| brahms | 17 | 14 | 14 | — |
| beethoven | 2 | 2 | 1 | `(♩=108)` |
| mahler | 0 | 0 | 0 | — |

## The findings, in the order they were forced

### 1. Whole-band OCR does not work, and the subtraction is not optional

The cheapest possible design is to skip the CV entirely: cut the strip between
two staves, hand it to Surya, keep what the lexicon accepts. It was tried first,
on the Brahms page, and it fails on both axes:

- **Recall 3 of 8.** Only bands 4, 5 and 7 gave up their `legato`; all four
  `espr. e legato` were missed.
- **Precision: dozens of invented letters.** One band returned eighteen `p`s and
  another ten `f`s and two `O`s — noteheads and stems read as text.
- **About fifteen minutes for one page.**

The cause is the aspect ratio. A band on that page is 5900 × 183 px, 32:1; an
OCR model resizes its input to a fixed frame, and a six-letter word arrives as
about four pixels of height. Cut at the barlines instead, the same word arrives
at 4:1 and is legible — and the measure attribution comes for free, because the
crop already knows which measure it is.

### 2. No distance separates a tempo mark from a title

The band below a staff is bounded on both sides by staves, so how far to reach
is not a question. Above the first staff of a page there is no bound but the
paper, and what occupies that space is the movement's heading — the one thing
that most looks like a tempo direction and is not one at that place.

Ink above the first staff, in staff spaces above its top line
(`probe_direction_bands.py`):

```
brahms      Un poco sostenuto  0.0-6.4    [ ] 6.9-11.0   composer 11-17   title 21-25
beethoven   Allegro con brio   3.1-8.2                                    title 13-16
mahler      -- no direction --            subtitle 3.3-5.6                title 6.6-9.9
```

**Mahler's title sits closer to its staff than Beethoven's direction sits to
that one.** The populations overlap, so no value of `above_spaces` separates
them, and a reach that finds `Allegro con brio` necessarily also finds
`Symphonie No. 5`.

What does separate them is position, again: **a heading is centred or
right-aligned on the PAGE; a direction is left-aligned to the music it starts.**
Above a staff — and only there, since a direction under a staff may legitimately
appear anywhere — a candidate is required to begin inside the staff's first
measure. On these three pages that keeps both real directions and refuses all
four heading blocks, which nothing vertical did.

Measured, with the reach then set to 8 spaces so nothing is clipped:

| page | above-band candidates | accepted |
|---|--:|---|
| brahms | 1 | `Un poco sostenuto` |
| beethoven | 2 | `Allegro con brio` (`(♩=108)` refused — digits) |
| mahler | 0 | — (title and composer both outside measure 0) |

### 3. A slur fills a fortieth of its box and a letter a fifth

The subtraction removes every detection, but a page's curves are not detections:
slurs, ties, ledger lines and beam ink survive it. What separates them from
letters is not size — a slur's bounding box is a plausible word — but **fill
ratio**, which is scale-free and does not care how long the curve is.

Two more cluster-level tests were needed and each came from a specific failure:

- **Cluster height ≥ 0.55 spaces.** Six pieces of a broken rule each pass the
  letter tests individually and cluster into a run 14 spaces wide and 0.2 high.
  Every true direction on the Brahms page is 1.1–1.8 spaces tall; both false
  runs are 0.2.
- **Letter size up to 2.0 spaces.** A tempo mark is set larger than an
  expression mark: the bold capital `U` of `Un poco sostenuto` is 1.79 × 1.65
  spaces where the italic `l` of `legato` is 0.4 × 1.1. At a 1.6 ceiling the `U`
  was dropped and the phrase arrived as `n poco sostenuto`, which the lexicon
  then refused. Nothing depends on the ceiling excluding noteheads — the
  detection subtraction does that, by knowing where they are.

And one clustering bug worth naming because it is generic. Components arrive in
x order, and a page has several rows of ink at the same x. Chaining each
component onto only the most recent run means **anything at another height that
falls between two letters takes over the chain and splits the word** — it split
`Un poco sostenuto` at a six-pixel gap, because a staff-top mark 200 px lower
sat between the `c` and the `o`. Every open run has to be a candidate.

### 4. The detector reads the `p` of `espr.` as a dynamic `p` — and it is right to

This one was found by accident and is the most important thing here, because it
is about the reader's dependence rather than about a page.

The subtraction erases every detection. Two of Brahms's four `espr. e legato`
vanished — not misread, never proposed — and the cause was that the detector had
found `dynamicP` at confidence 0.87 sitting exactly on the letters of the word.
A dynamic `p` and the italic `p` of `espr.` are the same letter in the same
family; the detector is not making a mistake that better weights would fix.

**What made it worth naming is that it appeared only after an unrelated change.**
The same four words survived before the cross-staff ledger fix landed and two
did not after, because that fix moved which detections exist. A reader whose
recall turns on which boxes the detector happened to draw is not a reader.

The fix is a gap, not a shape: **the letters of one word touch, while a dynamic
beside a word stands clear of it.** Measured on that page, `f` sits about 1.7
spaces from the `legato` next to it, and `es` sits against the `p` inside
`espr.` with nothing between. So a `dynamic` detection with ink hard against it
on both sides at its own rows — within half a space — is excused from the
subtraction.

Only dynamics are excused, deliberately. A notehead in a beamed run also has ink
on both sides, and excusing those would put the notes back into the very mask
that exists to take them out.

### 5. The OCR is marginal at 600 dpi, and it fails silently

After the fix above, one staff's `espr. e legato` was proposed as a clean
12.5 × 2.1-space cluster and still came back as the empty string. The crop is no
worse to a human eye than the three identical ones beside it that read fine:

    as printed (124 x 625 px)     ''
    upscaled 2x                   'espr. e legato'
    top 15% trimmed off           'espr. e legato'
    an extra white border          "'espr. 'e legato"

So the reader is near a cliff at the size a 600-dpi page gives it, and it goes
over the cliff by returning nothing — indistinguishable from a candidate that
was never a word. Crops are now enlarged until one staff space is at least 80
px, which is about 2× at 600 dpi and 4× at 300. Expressed in staff spaces
because that is what makes it independent of `--dpi`.

This is the same fact as finding 1 seen from the other end: whole-band OCR
failed because the band downscales the text, and this failed because the page
never scaled it up enough.

## 6. Where a mark attaches — and how a rejected rule turned out to be right

`_direction_slots` decides which note a mark is emitted before, and getting it
wrong costs DOUBLE: musicdiff deletes the mark where we put it and inserts it
where it belongs, each charged the mark's full character count. One misplaced
`espr. e legato` is 28 edits.

The rule shipped first was **the first event at or past the mark's left edge**,
which is only correct if a mark's left edge is at or left of its own note. It is
not, in either direction: measured in canonical pixels on one Brahms page,
`legato` begins 48 px LEFT of the note it belongs to and `pesante` 47 px RIGHT
of its own. A mark is set against its own width, and a word's width has nothing
to do with the music.

**The obvious repair — nearest note — was tried, measured, and rejected, and
that rejection was wrong.** It scored worse (`wrong dynamic` 29 → 43) for a real
reason: a rest occupies x-space, so nearness reaches BACKWARDS onto one, and
Beethoven 5's `ff` belongs to the note at beat 0.5 but is printed after an
eighth rest at 0.0, standing nearer the rest. The mechanism was correct. The
conclusion drawn from it — that the rule was wrong — was not. **A rest is not a
candidate at all**; you do not mark a rest `ff` or `legato`. Excluding rests
keeps everything nearness buys and costs nothing.

One clause more was needed, and it comes from a bar where a note was MISSED.
Brahms's Bassoon 2 detects one note where the truth has two, and its `legato` is
printed under the second, so the mark falls past every event we have. Landing it
after what we detected puts it at beat 1.5, which is right; snapping it back to
the single note we found puts it at 0.0, which is not. So a mark right of every
event keeps the past-the-end position — the one clause of the original rule that
survives.

Scored mark-by-mark against the truth's own offsets, all 47 marks
(`score_placement_rules.py`):

| rule | misplaced | word edits | dynamic edits |
|---|--:|--:|--:|
| first event at or past x | 4 | 54 | 2 |
| nearest event | 12 | 52 | 28 |
| nearest NOTE | 4 | 52 | 2 |
| **nearest note, keeping the tail** | **3** | **40** | **2** |

Confirmed end to end: `wrong direction` 61 → 47, `wrong dynamic` unchanged, the
no-flag baseline byte-identical at 0.2209 / 1563.

**The method matters more than the rule.** The first rejection was decided on a
POOLED score, which cannot see that a rule fixed one case and broke another —
and that is exactly what happened. `score_placement_rules.py` replays every rule
over the same marks and reports each miss by name, in about two seconds against
the hour a benchmark run costs. It is what made the next finding visible at all.

## 7. Two of the three "wrong offsets" were never offsets

This is the finding the mark-by-mark view produced, and it is the reason the
remaining 40 edits are not worth attacking from here.

Of the three misplaced words at 61 edits, only ONE was a placement error. The
other two sit on the **correct event**, and the event sits at the wrong time
because an earlier note in the bar lost its augmentation dot:

| staff | mark | truth durations | detected | sum |
|---|---|---|---|--:|
| 20 | `pesante` | `[.5 × 6]` | `[.5 × 6]` | 3.0 ✓ — a real placement error |
| 2 | `legato` | `[1.5, 1.5]` | `[1.0, 1.5]` | **2.5** in a 3.0 bar |
| 16 | `espr. e legato` | `[1.5, 1.0, 0.5]` | `[1.0, 1.0, 0.5]` | **2.5** in a 3.0 bar |

Both short bars are the FIRST note of the measure reading a quarter where the
truth has a dotted quarter. Every onset after it is early by exactly the missing
dot, so a mark on the second note reports beat 1.0 where the truth says 1.5.

That is the lost-dot half of the rhythm budget showing up in the direction
column. `transcribe._reconcile_measure_to_meter` declines these correctly and
says so in its own docstring — it re-reads a beam level by ±1 and cannot move a
dot, and `[1.0, 1.5] → [1.5, 1.5]` needs a dot.

⚠️ **Do not "fix" this in the placement rule.** Correcting the offset while the
note keeps its wrong duration would put the direction at a time no note in the
bar occupies. A consistently wrong file beats an internally contradictory one,
and the metric would charge for it either way.

The reachable fix is in the rhythm layer, and it is only partly reachable there:
adding a dot to make staff 2's bar sum to 3.0 has a UNIQUE answer, but staff 16
has two (`[1.5,1.0,0.5]` and `[1.0,1.5,0.5]` both total 3.0), so a
uniqueness-gated dot pass — the same discipline `_reconcile_measure_to_meter`
already applies to beams — would take one of the two and abstain on the other.
That is a change to note durations, with the note budget at stake, not a
direction change.

## What remains, all 47 edits of it

**Every word is read correctly, and only one of them is on the wrong beat for a
reason this layer could reach.**

| | edits | why |
|---|--:|---|
| one `espr. e legato` at beat 1.0, truth 1.5 | 28 | its bar lost a dot — finding 7 |
| one `legato` at 1.0, truth 1.5 | 12 | same |
| Mahler's `molto` — never proposed | 5 | printed against the staff BELOW it |
| `[` and `]` | 2 | not words. Correctly refused |

So 40 of the 47 is one rhythm fault (a quarter read where the truth has a dotted
quarter, twice) wearing a direction's clothes, 5 is a band that cannot reach a
crowded page, and 2 is the lexicon doing its job.

## Cost

About **9 seconds on a 21-staff page** with the Surya server resident
(`staff_labels_surya --serve`), and about 70 seconds more on the first call of a
run without it, to spawn llama.cpp and load a 650M GGUF. `--direction-text` is
therefore **off by default**: it is a cost a caller should ask for.

The CV half is the cheap part — 17 candidates from a page of 21 staves and about
4000 detections — which is the point of subtracting first. The OCR is only ever
shown word-sized crops, and on these three pages it was shown 19 of them in
total.

## For whoever picks this up

1. **The lost dot, 40 of the 47.** Not a reading problem and not a placement
   one — finding 7 has the proof. It is `_reconcile_measure_to_meter` learning
   to move a dot as well as a beam level, under the same uniqueness gate. Worth
   40 edits here and an unknown amount of the much larger note budget, which is
   the real reason to do it.
2. **Mahler's `molto`, 5 edits, and the general case behind it.** The band
   assumes a direction fits in the gap it is printed in. On a 38-staff page it
   does not, and every dense page will lose its crowded directions the same way.
   The fix is `header_ink.erase_staff_lines` over a band that reaches into the
   staff below, not a wider band — a wider band fuses the letters to the lines.
3. **Nothing here has been run on a SCAN.** The benchmark is engraved, so the
   letter filters have never met broken ink, foxing or bleed-through, and the
   lexicon has never met a genuinely garbled read. The gate is built to abstain,
   so the expected failure is silence rather than nonsense — but that is a
   prediction, not a measurement.
4. **The lexicon is three pages wide.** It holds what these fixtures print plus
   the obvious neighbours. A German or French edition will need its own entries,
   and `instruments.py` is the cautionary tale: a newly-readable page surfaced
   lexicon bugs that had been dormant.
