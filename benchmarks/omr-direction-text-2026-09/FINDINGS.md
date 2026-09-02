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

Measured on `main` at `dc74488`, immediately before and after:

| | pooled | edits | `wrong direction` |
|---|--:|--:|--:|
| baseline | 0.1364 | 966 | 151 |
| **with `--direction-text`** | **0.1138** | **822** | **7** |

Per work, and **every other category is unchanged to the edit** — `wrong note`
247, `wrong flag/beam` 197, `entire measure` 130, `wrong accidental` 64, `wrong
slur` 38, all identical on both sides. It is a post-pass that adds a key to
measures that already exist.

| work | before | after |
|---|--:|--:|
| brahms-sym1-mvt1 | 0.1709 (675) | **0.1342 (547)** |
| beethoven-sym5-mvt1 | 0.1649 (205) | **0.1501 (189)** |
| mahler-sym5-mvt1 | 0.0455 (86) | 0.0455 (86) |

**All 14 of Brahms's directions and Beethoven's one are read exactly right, with
zero false positives, and every one of them is now on the correct beat.** The 7
that remain are Mahler's `molto`, which is never proposed at all, and the `[`
and `]` the lexicon refuses because they are not words. Nothing left in this
category is a reading or a placement fault.

### The delta grew as the tree improved, and that is the interesting part

The reader was measured on six mains during and after the work, and the number
it is worth kept changing while nothing in it changed:

| main | what had landed | baseline | `wrong direction` after |
|---|---|--:|--:|
| `81446a0` | cross-staff ledger notes | 0.2449 | 33 |
| `6a1b601` | the integration branch | 0.2263 | 33 |
| `7516768` | default-on left-edge split | 0.2263 | 33 |
| `6f64bfa` | slurs | 0.2209 | 61 |
| `0ec4849` | placement rule corrected here | 0.2209 | 47 |
| `2eee2a9` | **the dot-threshold fix** | 0.1861 | **7** |
| `dc74488` | stems, beams, voicing, viola; and the union rung | 0.1364 | **7** |

Two of those movements are worth understanding, because neither is about this
reader:

- **61 is worse than 33, and no code got worse.** The cross-staff fix changed
  which detections exist, and the subtraction inherits that — see finding 4.
- **47 → 7 is not this reader's doing at all.** `ac5b3c3` fixed a dot threshold
  written against a glyph's own bounding box instead of the staff space, and
  that fix landed on two Brahms bars whose misread rhythm was displacing a
  correctly-read word. See finding 7, which recorded those 40 edits as
  unreachable from here and was right about the diagnosis and wrong about the
  lever.

What the reader itself reports (`direction_text` in the result JSON), which is
the number to watch rather than the pooled score — see finding 4 for why:

| work | candidates | read | accepted | refused |
|---|--:|--:|--:|---|
| brahms | 17 | 14 | 14 | — |
| beethoven | 2 | 2 | 1 | `(♩=108)` |
| mahler | 0 | 0 | 0 | — |

Identical on all seven mains. It is the invariant the pooled score is not.

**And the reader's own contribution has been −144 edits on every tree since the
dot fix**, while the baseline it is subtracted from fell from 0.1861 to 0.1364
underneath it. `wrong direction` starts at 151 and ends at 7 regardless of what
else has landed. That is what a layer looks like when it is finished and the
rest of the pipeline is not: its number stops moving and its SHARE of the total
climbs, from 8.8% of the budget when this began to 15.6% of the baseline now.

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

### 6. Where a mark attaches — and how a rejected rule turned out to be right

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

### 7. Two of the three "wrong offsets" were never offsets

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

#### Right about the diagnosis, wrong about the lever — and the lever mattered

This section originally ended by naming the fix: widen
`_reconcile_measure_to_meter` to move a dot as well as a beam level, under the
uniqueness gate it already applies. **That was wrong, and both bars were fixed
without it four hours later.**

`ac5b3c3` (`claude/funny-villani-98dd46`) found the real fault while working a
different residue: a dot was being measured against **its own bounding box
instead of the staff space**, so dots on the page were being thrown away. Fixing
the unit recovered them. Both of the bars above now read their durations exactly
— staff 2 `[1.5, 1.5]`, staff 16 `[1.5, 1.0, 0.5]` — and the 40 edits went with
them, without the reconciler being touched. That session ALSO retired the
"widen the reconciler" advice explicitly, for its own residue, on the grounds
that the reconciler declines those bars correctly and is one CONCEPT short
rather than one edit short (a beam group whose members differ in level).

Two things to carry from that:

- **The reconciler was never the lever here either.** It declines these bars
  correctly. The signal — the printed dot — was on the page the whole time and a
  threshold in the wrong unit was discarding it. That is the seventh and eighth
  instance of the shape this repository keeps finding, and this section walked
  right past it to recommend new machinery instead. **Before proposing a
  mechanism that would infer a missing signal, check whether the signal is
  already detected and being dropped.**
- **A correct diagnosis does not imply a correct remedy.** "These are rhythm
  faults, not placement faults, and the placement layer must not paper over
  them" was right, and is why nothing was papered over. "And the fix is the
  reconciler" was a guess wearing the same confident tone, in a document whose
  whole purpose is to be trusted by whoever reads it next.

## What remains, all 7 edits of it

**Every word is read correctly and every one is on the correct beat.** What is
left is not a reading fault, a placement fault or a rhythm fault:

| | edits | why |
|---|--:|---|
| Mahler's `molto` — never proposed | 5 | printed against the staff BELOW it |
| `[` and `]` | 2 | not words. Correctly refused |

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

1. **Mahler's `molto`, 5 edits, and the general case behind it.** The band
   assumes a direction fits in the gap it is printed in. On a 38-staff page it
   does not — `molto`'s ink crosses the next staff's top line — and every dense
   page will lose its crowded directions the same way. The fix is
   `header_ink.erase_staff_lines` over a band that reaches into the staff below,
   not a wider band: a wider band fuses the letters to the lines.
2. ~~**Nothing here has been run on a SCAN.**~~ **DONE — see
   [SCAN_2026-09-01.md](SCAN_2026-09-01.md).** Five pages of an 1870 Beethoven 5
   scan: **precision survives perfectly** (17 accepted, 0 invented, on paper this
   layer had never met) and **recall falls to about 37%**. The candidate CV
   transfers largely intact — 72 of 74 crops contain ink a second OCR can read —
   and the loss is Surya being silent on 53 legible crops. Two things there
   outrank the numbers: Surya emitted **1307 characters of hallucinated prose**
   on one crop, which only the lexicon stopped; and Tesseract as a REPLACEMENT
   rung is refuted (reads 72 of 74 and yields fewer usable words than Surya's
   21, because its errors are in-word where Surya's are total) while Tesseract
   as a UNION rung is now SHIPPED — 12 → 17 accepted on the scan, and the
   engraved benchmark unchanged to the edit, because Surya already reads every
   crop here and the lexicon refuses Tesseract's extra noise.
3. **The lexicon is three pages wide.** It holds what these fixtures print plus
   the obvious neighbours. A German or French edition will need its own entries,
   and `instruments.py` is the cautionary tale: a newly-readable page surfaced
   lexicon bugs that had been dormant.
4. **`wrong direction` is 7 and this file is nearly out of work.** Do not read
   that as the reader being good on real material — read it as the benchmark
   having three engraved pages with sixteen directions between them. The next
   honest measurement is a scanned page, not a smaller residue on this one.
