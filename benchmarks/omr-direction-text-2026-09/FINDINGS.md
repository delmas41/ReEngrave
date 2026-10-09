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

## 2026-10-08 -- the misses Sean listed on the 10 scan pages (lane `lane-direction-words-misses`, STAGED)

Sean's page-by-page review of `out/print/direction_text_scans_r2/` (DECISIONS 2026-10-08): no wrong readings; misses by kind. Pages: Litolff 4,6,9,12,15; Brahms 3,7,12,18,24. Harness: `benchmarks/omr-direction-text-2026-09/misses/` (`dump_page.py` gathers one page and pickles it; `raw_read.py` records every candidate's raw OCR; `run_pages.py` re-reads the pickles, times them and draws the review images). Review images: `out/print/direction_text_scans_r3/`.

**Result (STAGED, `scan_order=True`, which `staged/gather.py` now passes):** words read 42 -> 92 of ~113 printed (the ~113 is the previous lane's count, not re-counted here). Wrong readings seen on the r3 pages: none that I could see (cases of different capitalisation, e.g. `CrESC`, `eSpr.`, are Tesseract's case, accepted by the case-blind lexicon as before); Sean to confirm. Time per page, 10 pages: mean 19 s (3.5-35.5; the densest page, Brahms p12, 30-36 s, over the ~30 s line). Per page found, before -> after: Lit 4: 4->10, 6: 4->12, 9: 6->13, 12: 0->1, 15: 0->0, Brahms 3: 1->7, 7: 9->18, 12: 15->20, 18: 3->5, 24: 0->6. Cost of the new order against the old on the same pickles: it loses `Vcl` once (Litolff p6) and `arco`, `dim` once each (Brahms p12) -- Tesseract read under three letters on both crops, so Surya never saw them.

Each rule, stated before it was run, and what it did:

1. **Tempo word at the head/foot of a system (`Allegro`).** Cause (measured, Brahms p3): the bold capital is 3.1 spaces tall and `max_glyph_height_spaces` is 2.0, so the letters failed the size test; `Allegro` is already in the lexicon. Rule: in the strip above a system's first staff and the strip under its LAST staff only, a letter may be 3.6 spaces (`BandConfig.tempo_strip_max_glyph_spaces`). Result: both `Allegro` (above and foot) read on Brahms p3. Control: the same tall ink between two staves of one system is not a candidate (test).
2. **Part names inside a system.** Cause: the candidates existed (`Basso`, `Bassi.`, `Vcl.` were all boxed and OCR'd correctly) and the lexicon refused them. Lexicon ADDITIONS (category `part`): `basso bassi vcl vc violoncello violoncelli`. Result: Basso x3, Bassi. x2, Vcl x1 read. They are not echoed to other staves by rule 6.
3. **`pizz.` / `marc.` / `a2`.** `pizz.` is in the lexicon and its crop (`Basso pizz.` clustered into one box; the OCR read `Basso pizze`) is the miss -- NOT fixed. ADDITIONS: `marc` (expression); `a2` (also `a 2`, `a.2`) as category `part`, per Sean. `a 2` is two components, under the three a word needs, so a pair that is small, tight and level (`_is_a_due_pair`) becomes a candidate; and it is attributed to the staff BELOW the gap it is printed in (it sits over that staff's notes). Result: `a 2` read 8 times (Brahms p3 1, p12 2, p24 5), `marc.` twice (p12 `p marc.` needed rule 4).
4. **`piu` / a dynamic beside a word.** Two causes. (a) Brahms p3: the detector draws the `p` of `piu` as a dynamic and the blanking removed it, so the reader got `ui`; rule: a dynamic with ink touching its RIGHT edge (within 0.35 spaces, starting 3 px past the box) and none at its left is the first letter of a word and is not blanked (`word_initial_gap_spaces`). (b) The OCR returns `piu f`, `sempre molto p e dolce`, `pmarc.`: rule in `direction_lexicon.lookup`: if the string is refused, drop tokens that are only dynamic letters (`p f ff mf sf ...`) and a dynamic letter glued to the front of a term, and look again; the dropped letters are NOT in the returned text (the dynamic reader owns them). `piano`, `poco`, `pizz.` are untouched. Result: `piu` x3 on p3, `sempre molto e dolce` on p7. (This loosens what a dynamic beside a word does to the string; Sean has not ruled on it. No fuzzy matching: `CTESC.`, `Vel.`, `Crese.` are still refused.)
5. **Phrase (`sempre molto e dolce`).** Needed only rule 4(b) (`p` between the words); the OCR already read it.
6. **Half of the `cresc.`/`dim.`, especially the same word in the same bar on other staves.** Two mechanisms, both measured. (a) **The TIGHT crop** (`tight_crop_for`: the candidate's own box + 0.25 spaces, white margin): the standard crop pads 1.3 spaces sideways and takes in barlines and noteheads; the same box cut tight read where the wide crop returned '' or `CRESC. CRESC. CRESC.` -- 12 of 13 crops retried on three pages. (b) **Sibling windows** (`sibling_candidates`): where a word was read, look at the same x (+/-3 spaces) in each other staff's own band of that system, with relaxed letter tests, widened to the echoed word's width; read by the same OCR; counts only if the lexicon accepts what the OCR read (a place to look, never an assumption). Part names are not echoed. Yield of (b) alone: 12 words on 10 pages (Brahms p7 4, p3 2, p12 2, others 1) for ~4 s/page.

**Reading order for a scan (`scan_order`).** Fast rung (Tesseract) on the standard then the tight crop of every candidate; the slow rung (Surya) on the tight crop only of candidates where Tesseract saw >= 3 letters (`RETRY_MIN_LETTERS`), and on the standard crop of those with a 4-letter run, with a lower token ceiling (`8 + 2 x width in spaces`). Without this the same rules cost 28-38 s on the dense pages; the order is why the mean is 19 s. Precedence is therefore Tesseract-first for a word Tesseract already accepts (the old text said Surya first and noted it had never been load-bearing); `conflicts` are no longer recorded on this path. The legacy order is unchanged (`scan_order=False`, which `transcribe.py` still uses). Overlapping readings on one staff are reduced to the one cut from the smaller box (`piu` over `piu f`).

**Scan gate.** `OMR_DIRECTION_TEXT_SCAN_GATE` is no longer set by `acceptance_quick.py`, `gather_movement.sh` or `overnight/regather_20260930.sh` (default OFF = the reader runs). **Projected extra time per movement at the measured 19 s/page mean (3.5-35.5): Litolff 16 pages ~5 min (range 1-9), Brahms 27 pages ~9 min (range 2-16).** `staged/budget.py` still prices the reader at 267 s/page (and its tests pin it), so `gather_movement.sh` now prints that as its expected figure: conservative by about 13x; re-price it before trusting a budget line.

**Not done.** `pizz.` beside `Basso`; spaced-letter readings (`a r c o`, `p m u r c .`) -- joining them is exact but not asked; ~21 printed words still unread, mostly `cresc.`/`a 2` that no band proposed or Tesseract read under 3 letters of. Unit tests: `tools/omr/tests/test_direction_words_misses_2026_10_08.py` (RED against the tree before: `sibling_candidates` did not exist and every lexicon string above was refused; green now); `test_direction_text.py::test_a_two_letter_cluster_is_refused` now uses two far-apart letters because a tight level pair is `a 2`.

## 2026-10-08, round 4 (`lane-direction-words-r4`, STAGED)

Sean's round-3 notes: Litolff p9 missed `ten.`, `pizz.`, `Adagio`, a foot `cresc.`; p12 two `cresc.`; p15 `Vcl.` and `Basso`; Brahms p18 `cresc.`, `a2`, `più`. No wrong readings. Images: `out/print/direction_text_scans_r4/`.

**Result (10 pages):** 92 -> 93 words read of ~113 printed; mean 17.4 s per page (3.4-28.8), both dense Brahms pages under 30 s (p7 24.8, p12 28.8; were 34 and 36). Wrong readings seen: none (Sean to confirm). Gained: `a 2` x4 (Brahms p12/p18/p24). Lost against round 3 by the time guard below: `dolce` and `espr.` (p7), `marc.` (p12).

1. **Page foot strip.** Searched already: the last staff of the page gets a `below` band of 5 spaces, and the foot `Vcl.` of Litolff p15 (3.7 spaces below) is inside it and IS a candidate (box 1693..1757 x 2006..2055). It was not read because the OCR returned `val.` / `vi.` for the bold, fused `Vcl.` -- an OCR failure, not a finder miss, and no fuzzy matching.
2. **`ten.`** added to the lexicon (expression). Litolff p9's `ten.` has a candidate but the box is 30 px wide (the `t e n` pieces fused to the note stems were dropped), and the OCR read `nN,`.
3. **`Basso` + `pizz.`**: a run is cut where a gap of >= 0.25 spaces separates two groups whose letter centres differ by >= 0.55 spaces, taking the cut that leaves each side on one baseline (`_split_on_baseline`). Litolff p6 now yields `Basso` alone; `pizz.` beside it is still unread (the OCR read `pizze` / nothing). A gap alone never cuts (`espr. e legato` stays whole).
4. **Why the others were dropped (traced on the pickled pages):** the commonest cause is the candidate BOX covering only part of the word -- letters fused to a notehead, stem or slur fail the letter filters and are left out, so the OCR gets a fragment (`ten.` 30 px, `pizz.` 51 px on p9; `Adagio` clustered with the notes beneath it, read `nee`). Not fixed: it needs the letters recovered from the fused ink, not another read. Second cause: the OCR itself (`Vcl.`). `Vcl.` as two fused blobs was admitted as a candidate pair (`_is_a_due_pair` widened to 2.0-space letters, 4 spaces wide).

**Dynamic stays in the phrase (Sean, round 4).** `lookup` accepts a dynamic token inside a phrase (`più f`, `p dolce`, `f marc.`, `sempre p`, `p cresc.`; glued `pmarc.` -> `p marc.`), `DirectionHit.dynamics` lists them, a bare dynamic is still refused. `_link_dynamics` ties the marking to the detector's dynamic glyph beside it (`dynamic_links`), flags that glyph `in_direction_word`, and `export.measure_dynamics` skips flagged glyphs, so it is exported once. In STAGED the Q.DIRECTION_WORD row carries `includes_dynamic_glyphs` (glyph subject keys) and `dynamics`, read by `adjudicate_direction`. ⚠️ Joint export of the marking as one `<direction>` with `<words>` + `<dynamics>` is NOT built here: the staged exporter still writes the word and, unless the flag is honoured on its own dynamic path, the glyph; that is the next step. The staged gather also now files words against the READER's own candidate list (sibling-window and `a 2` words had no subject in round 3).

**Time.** The slow rung's standard-crop fallback stops after `SLOW_WIDE_BUDGET_S = 17` s of reading (the tight pass has already run on every lettered crop). That is the cheap way under 30 s and its price is the three words above on the two densest pages. **`staged/budget.py`: the reader is priced at the measured 18 s/page (was 267); `direction_text_scan_gate` defaults to False (the reader runs).** Whole movement: Litolff 16 pages ~5 min, Brahms 27 pages ~8 min of reader time.

## 2026-10-08, ROADMAP 2.66: the candidate BOX (STAGED; `claude/roadmap-start-27498c`)

START HERE 10-08 open item 2: words whose box covers only part of the print. Same 10 pages and pickles as round 4 (`/private/tmp/dtmiss/*.pkl`, `misses/run_pages.py`); a fresh baseline on the unchanged tree read **93** (= round 4). Images: `out/print/2.66/tile_01..05.png`. Summaries: `misses/summary_2.66_base.json`, `misses/summary_2.66_final.json`.

**What each miss was (measured on the pickles, crops in the session scratchpad):**
- `Adagio` (Litolff p9, the oboe's mid-system Adagio): `Ad` is ONE fused component 2.67 x 2.10 spaces. The fused-word branch would admit it, but the 2.0-space HEIGHT cap runs first; and three stem stubs left by the notehead subtraction joined `agio.` and pulled its box into the notes (`nee`, `Dun`).
- `pizz.` (Litolff p9 staff 10): the `p` descender's foot runs into the BARLINE, and through it into a beamed group -- `pi` is part of a 14.9 x 5.0-space component; only `zz.` reached the OCR (`NZZ.`).
- `ten.` (Litolff p9): the box already covers `ten.` on today's tree; the OCR reads `CP.` / `tp 21.` because the plate's `e` is broken into a `ρ` shape. An OCR limit, not a box.
- `Vcl.` (Litolff p15 foot): a stem stub over the word was in the box; with it gone the OCR still reads `vel.` / `val.` -- Litolff's bold `c` fills in to an `e` (also `Vel.` x3 on p6). An OCR limit; no fuzzy matching, so still unread.

**Rules (`find_candidates(refine_boxes=True)`, passed only by `read_directions(scan_order=True)` = the STAGED gather; the frozen legacy reader keeps its boxes):**
1. **Stub** (`_is_a_stub`): a component at most 0.45 spaces wide and at least 0.6 tall whose top or bottom row runs into ink the detection subtraction ERASED is the rest of that glyph (a stem), not a letter, and is dropped from the letters. It also removes 25 junk candidates across the 10 pages (stub clusters the OCR read as `FEE'?`, `TTY!`), which is why the time did not grow.
2. **Grow** (`_grow_along_baseline`): ink too big to be one letter may JOIN a word whose own letters passed, never start one -- looked for in the word's own line only (rows +/- 0.5 space; +/- 1.0 still reached the next staff down the `pizz.` stem), straddling the word's centre line, within 0.6 spaces, at least 1.0 space wide (scanned barlines/stems are 0.51-0.61; the first arm grew over three of them, one moving a `cresc.` a bar early), at most 3.6 x 4.0 spaces, fill >= 0.30, and NOT >= 90% inside the detector's dynamic boxes (Sean 10-08: read the dynamic and the word separately, then join; grown over, the `f` of `più f` -- 99% inside -- made Surya read `p rinf`, which the lexicon accepts, and the `p` of `pizz.` beside `Basso` -- 100% -- cost `Basso`; `pizz.`'s `pi` is 67% inside, the stem it is fused to being unboxed).
3. **Trim** (same function): a grown edge is cut just inside the innermost column where ONE unbroken run of ink crosses >= 95% of the line strip -- a barline or stem passing through the word. Unbroken, because `Adagio`'s `d` over a stub below it covers 91% with a 4-row gap. Without it `pizz.` started on its barline and was filed a bar early.
4. **Sibling windows are filed at the echoed word's x** (`sibling_candidates`): the window is padded 0.3 spaces left of that x, and the pad crossed the barline `pizz.` starts after (the staff-8 echo was filed a bar early). Pre-existing; visible only once `pizz.` was read.

**Result, 10 pages:** 93 -> **97** words; **none lost**; time 174.3 -> 175.8 s total (max page 28.4 -> 29.2 s, Brahms p12). Gained: `pizz.` (Litolff p9 staff 10, bar 8), `pizz` (staff 8, same bar, sibling), `Adagio.` (staff 12), `cresc.` (Litolff p12 staff 4). Changed: Brahms p3 staff 12 `piu f` -> `piu` (the first look now reads `piu` from its own box, so the sibling read that included the `f` is dropped as a second look at the same ink; the `f` stays the dynamic reader's and is no longer joined into the marking -- joining by geometry rather than by what the OCR saw is open item 1's business). Wrong readings seen: none (Sean to confirm on the tiles).

**Still unread, and why:** `ten.` and `Vcl.` (OCR on a broken/filled plate glyph; would need a confusion spelling such as `Vel.` -> `Vcl.`, which is fuzzy matching and Sean has not ruled); the many `CTESC.` / `Crese.` readings of `cresc.` (same class).

Tests: `tools/omr/tests/test_direction_word_boxes_2026_10_08.py` (12; RED against the unrepaired tree -- the functions did not exist and the sibling was filed in bar 0 -- green now, each rule beside a control that must be left alone); direction + staged-direction tests 222 passed; fast tier 6,344 passed before the trim/sibling commits.

### 2.66 continued -- Sean's tiles, the tempo rule, and word + dynamic

**Tiles (Sean, 2026-10-08):** 1 `pizz.` right; 2 `pizz` (sibling) right; 3 `Adagio.` read right but "belongs to the staff beneath it ... tempo is always above the staff" (built: `_give_tempo_to_the_staff_below`, DECISIONS 2026-10-08; on the 10 pages it moves only this `Adagio`); 4 `cresc.` right; 5 `più` right word, box a bit short (the detector boxes the `ù` as a dynamic `M`), but "we were not separating più from f".

**Word + dynamic read together** (`_dynamics_beside` + the re-read in `_read_scan_flow`): a word accepted without a dynamic, with a detected dynamic beside it on its line, is read once more from one tight crop over both, and replaced only if the lexicon accepts the SAME terms plus a dynamic token. 10 pages: 9 markings joined (`p cresc.` x3, `p espr.` x4, `p dolce`, `più f` on Brahms p3 staff 10), word count unchanged at 97, time 175.8 -> 190.2 s total (Brahms p12 34.6 s, over the ~30 s line). Summary `misses/summary_2.66_joined.json`. Brahms p3 staff 12 -- Sean's tile -- stays `più`: the OCR reads the joined crop as `pr f`, `piu J`, `pif`, `print`.
**Joining by POSITION was tried and refused** (the word reader's text + the detector's own dynamic letter boxes, only where every box is one letter): on the 10 pages it invented `f Adagio.` and glued `a 2 f`. Sean: *"We may just need a later stage to take the words and letters in a bar and determine if they belong together and what that means"* -- ROADMAP 2.68.

**Placement research** (`PLACEMENT-CONVENTIONS.md`, agent, read-only; caveats there: 99.4% MuseScore-encoded, the gap is defined by the same `placement` attribute it counts, literature second-hand): tempo, technique (`pizz.`, `arco`, `con sord.`, `div.`, `unis.`) and part words (`a 2`, `solo`, `tutti`) print ABOVE the staff they govern (technique 97.5%, `a 2` 99.8%); expression and dynamic words BELOW (a gap word to the staff above unless only the staff below has notes in that bar). Not built -- waits on Sean (the `pizz.` of tiles 1-2 is printed UNDER a staff, i.e. above the next one).

## 2026-10-08, ROADMAP 2.68: a word and its dynamic paired in a later stage (STAGED)

Sean: *"a later stage to take the words and letters in a bar and determine if they belong together and what that means"*; convention *"same line, close"* (DECISIONS 2026-10-08). Proof: Brahms p3 gathered once through EVALUATE (3 min, `--weights` scan production), then ADJUDICATE+EVALUATE re-run on the saved record with each fix (`readjudicate.rebuild`); export of the re-run record.

1. **The pairing** (EVALUATE, `consequences.pair_word_and_dynamic` -> `Q.MARKING` per cell). Reads the decided `Q.DIRECTION` and `Q.DYNAMIC` of one bar, page boxes from the word rows and the letter rows; pairs a word with ONE dynamic on the same line, nothing between, <= 1.5 spaces apart; a dynamic two words could claim, or a word with a dynamic each side, stays unpaired (`ambiguous`); a dynamic box mostly inside the word's own box is one of its letters, not a second dynamic. Markings the reader read whole (`più f` from one crop) are listed as `read_together`.
2. **Export** (`export._place_markings`, Sean: "wire the export"): a marking replaces its word and the dynamic(s) it absorbs with ONE `<direction>` holding a `<words>` and a `<dynamics>` in print order; both family counters count it. Brahms p3: both `più f` (staves 12 and 13, bar 9) written as one direction each.
3. **Three things the first run showed were in the way, each fixed and tested:**
   - `adjudicate_dynamic` dropped each run's letter ids into one flat `used` -- no consumer could tell which letters made which dynamic. Kept per run as `letters`.
   - The detector boxes letters of a word as dynamics (`p` of `più` as `dynamicP`, the `ù` as `dynamicM`), so staff 12's run spelled `pmf` and the bar's dynamic ABSTAINED. A dynamic letter mostly inside a word the OCR read (a second reader) is now that word's letter (`_inside_a_read_word`, counted as `letters_inside_a_read_word`); staff 12 then spells `f`. Risk, measured on these pages only: a padded sibling-window box could cover a real dynamic (here 4 px of 67).
   - GATHER filed one reading on TWO candidates that shared staff, bar and left x (staff 12: the word's box and a sibling window, both at x 4777) -- a duplicate `più`. The reader now stamps `DirectionText.candidate_index` and gather joins on it; visible only on a fresh gather.
4. **Result on Brahms p3:** `più f` paired on staves 12 and 13 (before: none; the first run paired nothing, because the letter boxes were unreachable). Unpaired, correctly: `Allegro` x2, `a 2`, `arco` (no dynamic beside). Noted, not changed: the staged export writes every word `placement="below"`, including tempo/technique words now filed ABOVE their staff (the legacy renderer hard-codes it).

Tests: `tools/omr/tests/test_staged_word_dynamic_marking.py` (16; RED against main), `test_staged_direction.py::TestOneReadingIsFiledOnce` (RED against main). `check` 192 -> 192 (the new quantity has its reader; `reach` 0 unaccounted).

### 2.68 open item: `sempre più p` read as `sempre p` (Litolff p8; lane `lane-sempre-piu`, STAGED)

Case: Litolff p8 (pdf index 8) prints `sempre più p` on every staff of system 0 (bars 11-12); the 2026-10-09 re-gather read `sempre p` on staves 3, 5, 6 and `sempre` on 7. Page dumped with `misses/dump_page.py` (`lit_8`), re-read offline with `run_pages.py`.

**Cause, measured (not the dynamic handling, not the barline trim, not the grow):** the candidate finder never saw the `iù`. The detector boxed it as a CLEF + REST (staff 5; 3 clef boxes on staff 6), an ORNAMENT (staff 8) or a stand-alone DYNAMIC (`dynamicM`, staves 3-4), and `_blank_detections` erased it (it spares only a dynamic with ink on both sides or touching its right edge) -- the raw ink was there, 11 x 21 px and 9 x 21 px, letter-sized; the mask was empty. The word's box stopped after the `p`; Tesseract/Surya read `sempre p`, which the lexicon accepts. Same defect, smaller: `dimin.` boxed as `dim` (an ornament box over the `in.`).

**Three rules (all STAGED-only: `refine_boxes` / `scan_order`; legacy untouched):**
1. `_ink_under_letterlike_detections` + `_grow_over_hidden_letters`: ink under a clef / rest / time-signature / ornament box, letter-sized and letter-dense, straddling the word's line and within 0.6 spaces of its end, joins the word. Notehead, stem, flag, accidental, dot, ledger line are not in the list (a note beside a word is a note). `dynamic` is NOT in the list: a mirror of the word-initial rule (ink touching a dynamic's LEFT edge = last letter) was built and refused -- it also swallowed the real `p` of `più p` standing 0.7 spaces after the word, because the bold dynamic's own swash touches. Growing over dynamic-boxed ink was tried and refused too (it absorbed the leading `p` of `p espr.`, lost `a 2` on Brahms p12 to a speck, changed readings on Brahms p7).
2. `confirm_readings` (inside `_read_scan_flow`, BEFORE the siblings are proposed -- a wrong reading seeds windows on every staff at its own x, and those read the neighbour's ink, which is how two `sempre` appeared): a reading that ENDS in a dynamic letter with another dynamic within 0.9 spaces (or a clef/rest/time-sig/ornament box within 1.5) against its box's end is read again over the box and the dynamics beside it; kept only if the longer reading has the same terms and more, else DROPPED. Sean's rule: a `p` among letters is the word's, a `p` alone is piano -- decided by the lexicon on the longer crop, not by a gap (the gap cannot tell: Litolff sets the dynamic 0.7 spaces after `più`, the `iù` 0.4 after the `p`).
3. `WIDE_BOX_SPACES_PER_LETTER` (2.0): a reading whose box is wider than 2.0 spaces per letter is read once more from the tight crop and dropped if any rung reads the same words and then MORE (`sempre` / `sempre piu: °`). 2.0 does not separate by itself (Brahms `dim` 2.2, Litolff `sempre` 2.25); it only decides which readings get the second look.

**A/B, same budget (`DT_SLOW_BUDGET=100000`, both arms on the 11 review pages: Litolff p4 6 8 9 12 15, Brahms p3 7 12 18 24; summaries kept in the session scratchpad):** 101 readings identical; only Litolff p8 changed. LOST (6): `sempre p` x2 and `Sempre p` (wrong), `sempre` (partial), `dim` (partial of `dimin.`), `sempre più` (a sibling-window reading, correct but for the dynamic `p` -- lost because its seeds were the wrong readings). GAINED: none. Litolff p8 went from 7 accepted readings (1 right, 1 right-but-the-p, 5 wrong or partial) to 1 (`sempre più p`, staff 8). Total 107 -> 101 words; time 245.9 -> 236.1 s. A 10-page run without a fixed budget shows 2 extra Brahms p7 readings (`p dolce`, `espr.`) -- that is the slow rung's wall-clock budget (`SLOW_WIDE_BUDGET_S`), which makes two runs on a busy machine differ; it reproduces on the unrepaired tree under the same load, so the A/B above fixes the budget.

**Still unread, and why:** the `iù` boxes are now inside the word on staff 5 and the OCR reads the longer crop as `sempre ptr` / `sempre pin` -- refused, unread, not wrong. `dimin.` is read by both rungs as `dimin` / `dimin.`, which is not in the lexicon (`dim` is): adding the abbreviation `dimin` is a lexicon entry, not fuzzy matching, and was NOT done (the lexicon is global; Sean's call). Brahms `più f` boxes are still a bit short (`ù` boxed as a dynamic next to the `f`); the hidden-letter rule does not cover dynamic-class boxes.

Crop for Sean: `out/print/2.68-sempre-piu/sempre_piu_p_old_red_new_green.png` (`misses/crop_sempre_piu.py`; cut from the PDF at 600 dpi, frame control against the gather's own render; staves 3, 5, 6, 8 named).

Tests: `tools/omr/tests/test_direction_cut_boxes_2026_10_09.py` (14; 9 RED against the tree before this change -- the box stopped at the `p`, the joined re-read skipped every reading that already carried a dynamic, the width rule did not exist -- the 5 refusal controls pass on both). Positive controls: the same ink under a notehead / 2.25 spaces away / in the legacy reader stays out; a dynamic 3 spaces after the word keeps `sempre p`; an ordinary-width box is not re-read.
