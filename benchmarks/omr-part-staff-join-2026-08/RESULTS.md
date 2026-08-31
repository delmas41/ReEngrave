# The part-to-staff join — first measurement, and one bug fixed — 2026-08-30

`dossier.join_parts_to_slots` is the gate on every slot-level dossier fact. It
matters because a printed score condenses and divides, so a work's part count
almost never equals a page's staff count — Beethoven 5 is written for 18 parts
and printed 11 staves to a system — and without the join the dossier simply
abstains.

Until now it had **no direct measurement**. It was judged only through what it
supplies downstream (clefs), which conflates the join with the readers around it.
`benchmarks/omr-key-signature/ground_truth.json` already carries a hand-read
instrument for every staff of two pages, so it can be scored on its own.

```bash
python3 benchmarks/omr-part-staff-join-2026-08/eval_join.py
```

## Result

| page | evidence | before | after |
|---|---|---:|---:|
| beet5-p2 (18 parts, 11 staves) | labels these editions print | **8/11** | **10/11** |
| beet5-p2 | perfect labels | 11/11 | 11/11 |
| pastoral-p2 (15 parts, 10 staves) | labels these editions print | 9/10 | 9/10 |
| pastoral-p2 | perfect labels | 9/10 | 9/10 |

**The algorithm is sound and starved, not broken.** Given a label on every staff
it gets 11/11 and 9/10. The gap between that and the realistic column is entirely
missing evidence, and the missing evidence is the string section, which these
editions never label
(`benchmarks/omr-margin-labels-2026-08/VISION_CEILING_2026-08-30.md`).

## The bug: the violins were a cheap condensable pair

`MERGE_SAME_PENALTY` (-0.3) is cheap because numbered parts of one instrument
share a staff — Flauti 1 and 2, Oboi 1 and 2. `MERGE_OTHER_PENALTY` (-1.5) is
dear because joining different instruments is rarer.

Canonicalisation collapses "Violin 1" and "Violin 2" to a single name, so the
aligner saw a cheap same-name pair where every orchestral tradition prints two
staves. The arithmetic then does the damage: Beethoven 5 p.2 requires 7 merges,
and the work offers exactly 7 same-name merges **only if the violins count**. So
the aligner condensed the two violin sections onto one staff, left cello and bass
on separate staves, and every string slot below shifted by one — Violino II read
as Viola, Viola as Violoncello, the cello-and-bass staff as Contrabass.

`NEVER_CONDENSED = {"Violin"}` removes the pair. 8/11 → 10/11, Pastoral unchanged.

## What was tried at the same time and rejected

Naming the cello-and-bass condensation as a cheap PAIR is the obvious partner —
"Violoncello e Basso" is a printed convention and it is exactly the merge
Beethoven 5 p.2 needs. Measured in four arms:

| arm | beet5-p2 | pastoral-p2 | total |
|---|---:|---:|---:|
| baseline | 8/11 | 9/10 | 17/21 |
| **violins excluded (shipped)** | **10/11** | **9/10** | **19/21** |
| cello/bass pair only | 9/11 | **7/10** | 16/21 |
| both | **11/11** | **7/10** | 18/21 |

Both together get Beethoven 5 perfect and cost the Pastoral two slots, for no net
gain. A cheap cross-instrument merge lets the aligner condense **whenever it is
short of staves** rather than only where the engraving does: on the Pastoral,
where cello and bass genuinely take separate staves, it merged them anyway and
then extended Violin 2 across two staves to make the arithmetic work.

Which parts share a staff is a fact about the PAGE, and a flat price cannot
express it. The counting constraint that would — *this page needs k merges and
the work offers j conventional ones* — is global, and the DP scores locally.
That is the open problem, and it is the honest next step rather than another
price.

## A third page, and a second failure mode that labels cannot fix

Two pages was too little to design against, so the ground truth was extended with
Beethoven 5 p.48 — the fourth movement, **23 parts printed on 17 staves**, hand-read
from the page's own margin labels. It is the most condensed page in the set and the
assignment has no freedom: six merges are required and the work offers exactly six
conventional same-instrument pairs, so every other staff is 1:1.

| page | no labels | perfect labels | as printed |
|---|---:|---:|---:|
| beet5-p2 (18→11) | 10/11 | 11/11 | 10/11 |
| pastoral-p2 (15→10) | 3/10 | 9/10 | 9/10 |
| **beet5-p48 (23→17)** | 8/17 | **13/17** | **12/17** |

**Perfect labels do not rescue p.48.** That is the finding: on the other two pages
the gap between "perfect" and "as printed" is missing evidence, and here it is not.
Three of the four remaining errors are structural.

### The part list and the print disagree about order

The page prints `Timp.` at slot 8 and the three trombones at 9, 10, 11. The
MusicXML part list has Alto, Tenor and Bass Trombone at indices 14-16 and Timpani
at 17 — trombones BEFORE timpani, which is the standard orchestral order; this
edition's print is the one that deviates, and Beethoven editions commonly do.

`align_to_layout` is a **monotone** alignment. It can skip a part, extend one part
over several staves, or merge several onto one — but it cannot go backwards. Having
consumed Timpani at part index 17 for slot 8, the trombones at 14-16 are behind it
and permanently unreachable, so slots 9-11 come back `None`.

No amount of labelling fixes this, which is why the perfect-label column is 13/17.

**It costs exactly the parts that matter most.** The three trombones are the alto,
tenor and bass clefs — the readings the dossier exists to supply and that no
detector reads reliably (`benchmarks/omr-clef-geometry/`). The dossier knows all
three and the join cannot deliver them.

### So the merge budget is the second problem, not the first

The global constraint identified above — *this page needs k merges and the work
offers j conventional ones* — is real, and p.48 is the case where it holds
perfectly (6 required, 6 available, and the winds all come out right). But it is
not what is losing slots here.

Ranked by what the ground truth actually shows:

1. **Order inversion (structural, 3 of 17 slots).** The aligner assumes both
   sequences are in the same order and they are not. Normalising the dossier into
   canonical score order does not help — the dossier is already in it. What knows
   the PRINT's order is the margin labels, so the fix is to let a labelled slot PIN
   its part and align only between pins, which permits the transposition the
   monotone path forbids. That is a different use of labels from today's, where
   they only score pairs and mark trust.
2. **Merge budget (1 of 11 on p.2).** The cello-and-bass staff, which needs a
   cross-instrument merge no flat price can license safely — see the four arms above.
3. **Piccolo and contrabassoon (2 of 17 on p.48).** Singleton parts adjacent to a
   conventional pair; the aligner attaches them to the pair rather than giving them
   their own staff.

## Unchanged

Suite 1040 passed. `benchmarks/omr-score-order/eval_score_order.py` byte-identical
(position 11/12, read clefs 5/10, true clefs 23/23) — that path aligns against
standard layouts with `allow_merge=False`, so merge pricing cannot reach it.
`eval_pipeline_clefs.py --contextual --dossier` unchanged at 50/52 with an
identical per-source breakdown.

The one remaining beet5 slot and the one Pastoral slot are both the cello/bass
staff, which is the merge no evidence currently licenses.


---

# Pinning: the labels know the print's order — 2026-08-30 (second pass)

The order inversion above is fixed, and Beethoven 5 p.48 now reads **17 of 17
staves from the labels the page actually prints** — up from 12. It took two
changes that each LOSE on their own, which is the finding worth keeping.

```bash
python3 benchmarks/omr-part-staff-join-2026-08/eval_join.py
```

| page | evidence | before | after |
|---|---|---:|---:|
| **beet5-p48** (23 parts, 17 staves) | **as printed** | **12/17** | **17/17** |
| beet5-p48 | perfect labels | 13/17 | **17/17** |
| beet5-p2 (18 → 11) | as printed | 10/11 | 10/11 |
| pastoral-p2 (15 → 10) | as printed | 9/10 | 9/10 |

The two other pages do not move, in either direction. p.48's realistic column
now equals its perfect one: on this page the margin is enough.

## Neither half works alone. Both halves lose.

| arm | p48 perfect | p48 **as printed** |
|---|---:|---:|
| baseline | 13/17 | 12/17 |
| pins only | **17/17** | 11/17 |
| lexicon only | 13/17 | 10/17 |
| **pins + lexicon** | **17/17** | **17/17** |

That is not a near-miss on each side that adds up. Each change on its own makes
the as-printed reading WORSE than doing nothing, and the reason is the same one
in both directions.

**Better labels alone make the page worse**, which is the more surprising half.
Teaching the lexicon to read `Tr. Alt.` fixes the winds and then costs the whole
lower half of the page: the aligner now knows the trombones are at staves 9-11,
cannot reach them because the timpani it consumed at staff 8 sits later in the
part list, and pays for the transposition by sliding everything below down one —
staff 12 reads Timpani, 13 reads Violin 1, 15 reads Viola. Twelve correct
becomes ten. A monotone aligner handed a correct but out-of-order label set has
to put the error somewhere, and giving it better evidence only moves the error,
it does not remove it.

**Pins alone lose too**, for the dual reason: the pins are only as good as the
names, and three of p.48's printed labels resolved to the wrong instrument
outright — not to nothing. Pinning a wrong name is worse than scoring it.

So the honest statement is that pinning is what removes the inversion, and the
lexicon is what makes the evidence good enough to pin ON. Reporting either
number alone would have been misleading in opposite directions.

## What pinning is

`score_layouts.align_to_layout_pinned`. A labelled staff pins its part; the
alignment then runs only on the spans BETWEEN pins, and two pins may sit in
either order — which is exactly the transposition the monotone path forbids.

**A pin fixes a boundary; it does not consume a run.** This was measured, not
assumed, and the first version had it wrong. Pinning a labelled staff to its
instrument's whole run of parts costs the Pastoral a staff: `Violino I` labels
ONE staff, a run pin hands it both violin parts, and the unlabelled second-violin
staff below has to start at the viola, so the section shifts down (9/10 → 8/10).
A label says where an instrument BEGINS. How many staves it takes is what the
alignment is for, so only the FIRST part of the run is pinned.

**Score order resumes after a transposition.** Every part no pin holds goes to
the last span, in STAFF order, whose own part lies above it — not to the pin
holding the numerically nearest part. On p.48 the timpani pin sits on an early
staff while holding a late part; sending the strings to it because 17 is the
nearest anchor below 18 strands all five string staves with nothing to read.

**Between two pins the merge budget becomes local.** RESULTS.md above records
the counting constraint — *this page needs k merges and the work offers j* — as
global, and the DP as scoring locally. Pins make both counts known within a
span, and a span with as many parts as staves needs no condensation at all. This
is not optional bookkeeping: a merge is rewarded with another full pair score,
so on a span whose parts share one name — the three trombones, the two violins —
every label matches every part and the DP condenses all three staves onto one.
With merge left available, the trombone staves the pins finally reach all come
back "Alto Trombone" (perfect labels 14/17, not 17/17).

**Positions stay the page's, not the span's.** A span is a slice of both
sequences; renormalising it stretches that slice back over the full 0..1 range,
moving the two sides relative to each other and deciding merges on an axis the
page never had. Measured: the local axis makes condensing Violin 2 with the
viola look no worse than the cello-and-bass staff the engraving prints, and
costs Beethoven 5 p.2 and the Pastoral a staff each.

### The four things that withdraw a pin

A pin is a hard constraint, so it is only taken on unambiguous evidence.

* **An ambiguous alias.** `Tp.` is Timpani or Trumpet, `Basso` is a voice or the
  contrabasses. POSITION settles those, and a pin is the one move that takes
  position off the table. p.48's `Cor.` is in this class and does not pin; the
  span reads it correctly anyway. It is the **alias that matched** that is
  tested, not the label — a margin prints `Cor. 1. 2.` as often as `Cor.` and
  the two are the same ambiguity, so testing the whole label would let the
  numbered form through and pin on a reading the lexicon will not commit to.
  `Corni 1. 2.` stays pinnable: only the abbreviation is ambiguous.
* **A name the work prints in two places**, so the run is not unique.
* **The same name claimed by two separated blocks of staves.** That is a
  contradiction, not evidence — and it is what a misread produces. Before the
  lexicon fix, p.48's `Tr.` (trumpets) and `Tr. Bas.` (bass trombone) both read
  as Trumpet; neither pinned.
* **A clef — never.** Supplying clefs is what the join exists to do.

## The lexicon half

Three standard Italian abbreviations resolved to a different instrument, and the
corpus check over every part name in all 97 dossiers plus every label in
`benchmarks/` says the fix touches exactly these and nothing else — 10 of 547
names, all corrections:

| printed | was | now |
|---|---|---|
| `Fl. Pic.` | Flute | **Piccolo** (`fl picc` was there; the one-c spelling missed) |
| `C. Fag.` | Bassoon | **Contrabassoon** (`cfag` was there; normalization keeps the space) |
| `Tr. Alt.` | Alto *(the voice)* | **Trombone** |
| `Tr. Ten.` | Tenor *(the voice)* | **Trombone** |
| `Tr. Bas.` | Trumpet | **Trombone**, and listed ambiguous |

`Tr. Bas.` is Trombone basso in the Italian tradition and Tromba bassa — the
bass trumpet Wagner and Strauss write for — in the German. It is therefore added
to `AMBIGUOUS_ALIASES` as well: the lexicon answers with the commoner reading,
and the listing is what stops a staff being pinned on it. There is no tromba
alta or tromba tenore, so the other two are the trombone outright. Bare `Tr.` is
untouched and still the trumpets.

### And it corrects item 3 of the ranking above

The first pass ranked the third failure as *"Piccolo and contrabassoon —
singleton parts adjacent to a conventional pair; the aligner attaches them to
the pair rather than giving them their own staff."* That was wrong, and wrong in
a way worth recording: it read a lexicon failure as an alignment one. The
aligner was not attaching the piccolo to the flutes on any judgement of its own.
`Fl. Pic.` resolved to **Flute**, so the label was literally telling it that
staff was a flute, and the aligner did as it was told. Nothing about merge
pricing or singleton handling was involved.

The diagnosis was made by reading the assignment and inferring the cause. What
found the real one was printing what each label resolved to — a step that costs
nothing and was skipped.

**It costs exactly the parts that matter most** — the same sentence as above,
now on the other side of the ledger. The three trombones are the alto, tenor and
bass clefs, the readings no detector supplies and the dossier exists to provide.
p.48 delivers all three.

## Guards

All four held, and none moved.

* `python3 -m pytest tools/omr/tests -q` — **1055 passed** (1043 before, plus 12
  new: 8 for pinning, 2 for the lexicon, 2 for the join's pin gate).
* `benchmarks/omr-score-order/eval_score_order.py` — byte-identical: position
  11/12, read clefs 5/10, true clefs 23/23. That path aligns against standard
  layouts with `allow_merge=False` and does not call the pinned entry point.
* `eval_pipeline_clefs.py --contextual --dossier` — **50/52, with an identical
  per-source breakdown**: detector 38 staves at 97%, default 10 at 90%,
  cv_locator 2, dossier 1, slot_continuity 1, and the same two alto-read-as-
  treble errors. `anchored` is untouched by design — pinning changes which part
  a staff gets, never which staves are labelled — so the foot-of-system anchor
  that measured 50/52 → 44/52 is not reintroduced.
* `python3 -m tools.omr.training.orchestral_eval` — identical to the baseline
  recorded in `benchmarks/omr-orchestral-e2e/README.md` on all three works, row
  for row: Beethoven 5 recall 1.000 / precision 0.988 / duration 1.000, Brahms 1
  0.717 / 0.713 / 0.865, Mahler 5 0.917 / 0.917 / 0.318, with the same part and
  measure counts. This is the guard that would catch the join going wrong
  end-to-end, and Beethoven 5 mvt 1 runs through it with a dossier.

## What this does NOT show

*(Superseded by the section below — p.48's clefs have since been hand-read, and
the downstream measurement is there.)*

p.48 has part-to-staff ground truth but no hand-read CLEFS, so the gain is
measured at the join and not yet downstream of it. The clef benchmark's two
pages are the ones that do not move here — beet5-p2 and the Pastoral both sit at
their previous score — so 50/52 is a proof of no harm, not a demonstration of
the benefit. Hand-reading p.48's clefs is what would close that.

The merge budget is still open, exactly as ranked before. The one remaining
beet5-p2 staff and the one Pastoral staff are both the cello-and-bass staff,
which needs a cross-instrument merge no flat price licenses safely. Pinning
makes the counting constraint local WHERE THERE ARE PINS; on the string section
of these two editions there are none, because the strings are never labelled
(`benchmarks/omr-margin-labels-2026-08/VISION_CEILING_2026-08-30.md`). That is
the same starved-for-evidence finding as the first pass, unchanged.


---

# Downstream: p.48's clefs, hand-read — 2026-08-30 (third pass)

The gain above was measured AT the join. This closes it: all 17 of p.48's clefs
are now hand-read from the print, so what the join is worth can be measured
where it actually matters — on the clef each staff ends up with.

```bash
python3 benchmarks/omr-clef-geometry/eval_pipeline_clefs.py --contextual --dossier
python3 benchmarks/omr-part-staff-join-2026-08/eval_clefs_with_labels.py
```

The clefs live in `ground-truth-beet5-p48.json` beside the part assignment, and
NOT in `benchmarks/omr-key-signature/ground_truth.json` — five other benchmarks
read that file, and adding a page to it would move their denominators silently.
`eval_pipeline_clefs.py` picks the extra page up and reports the original three
pages as a subtotal, so **50/52 stays directly comparable across sessions**.

## How they were read

Hand-read from the page at 600 dpi, glyph by glyph, and **not** taken from the
dossier — the dossier is the thing being measured, and seeding truth from it
would be circular. Clef TYPE (G/F/C) was read visually. Which line a C clef
names was **measured**, because alto and tenor are the same glyph one line apart
and that is the entire difficulty: the glyph's ink centre against the staff's own
five detected lines puts staff 9 at line 3.25 and staff 10 at line 4.30, a clean
one-line separation. Visually the same — staff 9's clef fits inside the staff
(waist on the middle line, ALTO), staff 10's rides above the top line (waist on
the 4th, TENOR), and the viola measures with staff 9. All six F clefs are bass;
no baritone. The page carries no key signature anywhere: the finale is C major
and every transposing part is in C.

As a cross-check — not a source — the dossier generated from the Gradus MusicXML
gives the same clef on all 17 staves. The two are independent, a modern digital
edition against this 19th-century print, so the agreement is worth something.

## The result, and it is not what the join predicted

**In production p.48 scores 8/17, and the join has nothing to do with it.**

```
beet5-p48: contextual — 0 labels, 0 from the dossier
```

**Zero labels.** This edition (IMSLP984073) has **no text layer at all** — zero
characters on every page, where the other Beethoven 5 edition carries OCR text
and yields 9 labels on p.2. So `read_staff_labels` returns nothing, the join
never sees a label, nothing pins, the dossier abstains, and every clef falls to
the detector or the positional default. The chain breaks one step before the
work of the last two passes begins.

That is a failure of label ACQUISITION, and it is its own thread
(`benchmarks/omr-margin-labels-2026-08/VISION_CEILING_2026-08-30.md`); there is
a Claude Vision fallback for exactly this case, which this benchmark does not
spend credits on.

## So: what is waiting behind the label reader

`eval_clefs_with_labels.py` hands the join the labels the page PRINTS — only
those, so the five string staves stay unlabelled exactly as the engraving leaves
them — and holds everything else fixed.

| p.48, labels supplied | clefs correct |
|---|---:|
| no dossier | 12/17 |
| dossier, **pinning off** | 12/17 |
| **dossier, pinning on** | **14/17** |
| *(production today: 0 labels)* | *8/17* |

**On this page the dossier layer is worth nothing without pinning.** 12/17 either
way — because without pins the join cannot reach the trombones at all, and the
two slots it does reach it fills wrongly:

```
pins OFF   slot  9 Trombone  want=alto   got=alto   (dossier)
           slot 10 Trombone  want=tenor  got=alto   (dossier)   <- the extend
           slot 11 Trombone  want=bass   got=alto   (dossier)   <- degeneracy
           slot  8 Timpani   want=bass   got=bass   (default)   <- not reached
```

With pins, six clefs come from the dossier and all six are right — the two
bassoons, the timpani, and **the alto, tenor and bass trombones**. Those three
are the readings no detector supplies and the whole reason the dossier exists;
the sentence "it costs exactly the parts that matter most" now has its
counterpart on the other side.

The three remaining errors are slots 14, 15 and 16 — viola, cello and bass, all
reading treble by default. They sit below the last printed label, so they are
outside `anchored` and the dossier correctly declines to speak for them. That is
the same starved-of-evidence ceiling as every pass before: these editions never
label the strings.

## Guards

* `pytest tools/omr/tests -q` — 1055 passed.
* `eval_pipeline_clefs --contextual --dossier` — the three original pages
  **unchanged at 50/52** (reported as `(base 3)`), overall 58/69 with p.48
  included. Without `--dossier` the same three score 49/52, so the dossier is
  still worth its one staff there.
* `eval_score_order` — byte-identical (11/12, 5/10, 23/23), and
  `eval_key_signatures` unchanged: the shared ground-truth file was not touched.

## What this still does not show

One page, one edition. And the headline number a future session will see from
`eval_pipeline_clefs` is **8/17 on p.48**, which is honest — that IS what the
pipeline does on this scan today. The 14/17 is a ceiling measured with the labels
handed over, and it only becomes real when the margin-label thread delivers them
on a page with no text layer.

The ranking that comes out of this is therefore not the one the join work
implied. Pinning is done and is worth +2 clefs here. What now gates the dossier
layer on scanned orchestral pages is **reading the margin at all**.

*(Run in the next section — the margin reader clears it.)*

---

# The margin reader clears it — 2026-08-30 (fourth pass)

The gate named above is open. One call to `staff_labels_vision` on p.48's single
system reads **all twelve printed labels correctly and returns nothing for the
five unlabelled string staves**, and the page goes **8/17 → 14/17** — the same
number the hand-read labels reach. On this page the reader is at ceiling.

```bash
python3 benchmarks/omr-part-staff-join-2026-08/eval_clefs_with_labels.py --vision
```

The read is cached in `evidence/p48-vision-labels.json` beside the crop it was
given, so the number is reproducible without spending credits again.

| p.48, end to end | clefs |
|---|---:|
| production today — no text layer, fallback not enabled | **8/17** |
| vision labels, pinning **off** | 12/17 |
| **vision labels, pinning on** | **14/17** |
| printed labels (the ceiling), pinning on | 14/17 |

The last two rows being equal is the finding: nothing is lost between what the
page prints and what the reader recovers. Pinning is worth the same +2 on the
real labels as on the hand-read ones, and for the same reason — without it slots
10 and 11 both come back "Alto Trombone" and the timpani is never reached.

## What it read

| staff | printed | read |
|---:|---|---|
| 0-8 | Fl. pic. / Fl. / Ob. / Cl. / Fag. / C. Fag. / Cor. / Tr. / Timp. | all nine, exactly |
| 9-11 | Tr. Alt. / Tr Ten. / Tr. Bas. | all three, exactly |
| 12-16 | *(nothing printed)* | **nothing returned** |

12 of 12 printed, 5 of 5 correct abstentions. Compare the Pastoral, where the
same reader was also at ceiling but the ceiling was 5 labels of 10
(`benchmarks/omr-margin-labels-2026-08/VISION_CEILING_2026-08-30.md`): this page
labels every wind and brass staff down to the bass trombone, which is exactly
where the dossier needed an anchor.

**It out-read the hand reading on two labels.** The ground truth here said
`Fl. Pic.` and `Tr. Ten.`; the page prints `Fl. pic.` with a lower-case p and
`Tr Ten.` with no stop after Tr. Checked against the print at 5x and the ground
truth is corrected. Nothing downstream moves — `normalize_label` folds case and
punctuation away — but it is worth recording which reader was right.

**And it lands on the lexicon fix from the first pass.** `Fl. pic.`, `C. Fag.`,
`Tr. Alt.` and `Tr Ten.` are precisely the four abbreviations that resolved to
the wrong instrument before, and `Tr. Bas.` is the one now marked ambiguous so it
cannot pin. Without that fix these twelve labels would have been read perfectly
off the page and then thrown away by the lexicon.

## The reason it had never run here: a stale SDK, failing silently

The first attempt returned zero labels. Not a reading failure — the call never
happened:

```
TypeError: create() got an unexpected keyword argument 'output_config'
```

Structured outputs need `anthropic>=0.116`, which `backend/requirements.txt`
pins **for the container**. This module also runs host-side, outside it, and the
host carries **0.28.0**. The measurement above was taken with a current SDK in a
throwaway venv; **the host still needs upgrading before the production path can
work.**

It was logged at `warning` and swallowed, so a broken dependency and a margin
with nothing printed on it produced the identical observation: zero labels. On a
page whose whole question is "are there labels here?", that is the worst possible
place to be quiet. Now it is an ERROR naming the exception type and the systems
that failed:

```
ERROR margin label read FAILED on system 0 (TypeError: create() got an
      unexpected keyword argument 'output_config') — 0 labels here means the
      reader did not run, not that the margin is empty
ERROR margin label read: 1 of 1 systems FAILED; the 0 labels returned are from
      the systems that ran
```

The per-system catch stays: one bad page must not kill a batch.

## Where the last three staves go

Slots 14, 15 and 16 — viola, cello, bass — still read treble by default. They sit
below the last printed label, so they are outside `anchored` and the dossier
declines to speak for them. That is the same ceiling every pass has hit, and the
margin reader cannot lift it, because it already reported correctly that there is
nothing printed beside those staves. Lifting it needs a different anchor than a
label: the foot of the system, which was measured at 50/52 → 44/52 and rejected.

## Cost

One API call, one system, `claude-opus-5`. About a cent.

## Guards

1055 tests. The clef benchmark, `eval_score_order` and `eval_key_signatures` are
untouched by this pass — `--vision` is a separate harness and the production
default still reads 0 labels on this scan until the host SDK is current.


---

# The tail that has no freedom left — 2026-08-30 (fifth pass)

**Beethoven 5 p.48 now reads 17 of 17 clefs end to end, from its own printed
margin.** The three staves the last pass left — viola, cello, bass — sit below
the last label, and the rule that released them is a counting one.

```bash
python3 benchmarks/omr-part-staff-join-2026-08/eval_clefs_with_labels.py --vision
OMR_TAIL_RULE=none|exact|all   # to compare the three arms
```

| p.48, vision labels | clefs |
|---|---:|
| `TAIL_RULE=none` (previous behaviour) | 14/17 |
| **`TAIL_RULE=exact` (shipped)** | **17/17** |
| `TAIL_RULE=all` | 17/17 |

## Why the tail was gated, and why that was too blunt

`anchored` has always stopped at the last label, because past it the alignment is
guessing — and trusting it to the foot of the system was measured and rejected at
50/52 → 44/52.

But "guessing" is not one thing. **Count what is left.** If the staves below the
last label are exactly as many as the parts still unassigned above them, a
monotone alignment has *one* option: it cannot merge, extend, or skip a part
without leaving a staff empty. There is nothing left to get wrong. Where the
count has slack, the guess is real and the gate should hold.

This is the same local-counting argument that already licensed the merge gate
inside a span — pins make both counts known — applied one step further.

The three ground-truth pages split cleanly on it:

| page | tail below the last label | join correct on the tail |
|---|---|---:|
| beet5-p48 | 7 staves vs **7** free parts — **exact** | **7/7** |
| pastoral-p2 | 4 staves vs **4** free parts — **exact** | **4/4** |
| beet5-p2 | 5 staves vs 7 free parts — *slack* | 4/5 |

11 of 11 on the exact tails; the slack one is the page that gets it wrong, and it
stays gated. The rejected rule and this one differ on exactly that row.

## Guards

* `pytest tools/omr/tests -q` — **1056 passed**. One existing test changed
  meaning and was rewritten rather than deleted: it asserted that everything past
  the last label is unanchored, using a 4-part work on 4 staves — which is an
  *exact* tail, so the old assertion was the conservative answer, not the correct
  one. It is now two tests, one per side of the distinction.
* `eval_pipeline_clefs --contextual --dossier` — **base 3 unchanged at 50/52**,
  with beet5-p2 22/22, pastoral-p2 18/20, wtc-p17 10/10. The new rule is neutral
  there: the Pastoral's production run reads only 4 labels from its text layer, so
  its tail is larger than the 4-label arm above and does not close exactly.
* `eval_score_order`, `eval_key_signatures` — untouched.

## What it does not do

It does not fix the Pastoral viola, the base corpus's remaining error. That page
gets 4 labels from its text layer in production, not the 6 the join benchmark
supplies, and with 4 the tail no longer closes. The margin reader recovers 10
labels there (`VISION_CEILING_2026-08-30.md`) — so this rule and the vision
fallback are complementary, and the Pastoral is the page that needs both.

And p.48 still reports **8/17** from the standard benchmark, because the
production path reads no labels on that scan at all. The 17/17 is what it scores
once the labels arrive.


---

# The fallback, switched on for real — 2026-08-30 (sixth pass)

Host SDK upgraded to `anthropic` 0.125 (from 0.28), so the margin reader runs on
the host and not only in a throwaway venv. `eval_pipeline_clefs` now takes
`--vision-labels`, which costs credits — up to three systems a page, about a cent
each.

```bash
python3 benchmarks/omr-clef-geometry/eval_pipeline_clefs.py --contextual --dossier --vision-labels
```

| corpus | without | **with `--vision-labels`** |
|---|---:|---:|
| overall (69 staves) | 58/69 | **67/69 = 97%** |
| beet5-p48 | 8/17 | **17/17** |
| base 3 | 50/52 | 50/52 |

**p.48 is 17 of 17 in the production harness**, not in an oracle arm — a whole
conductor's page, every clef, read from its own printed margin. The dossier now
supplies 10 staves across the corpus and is right on all 10. The only two errors
left in 69 staves are the Pastoral viola, in both its systems.

## Two things this turned up, and neither is comfortable

### 1. The rejected tail rule is no longer worse. It is better.

`TAIL_RULE=all` — trust everything below the last label — is recorded elsewhere
in this project as costing 50/52 → 44/52. **It does not reproduce.** Measured now:

| arm | base 3 | beet5-p48 (no vision labels) |
|---|---:|---:|
| `none` | 50/52 | 8/17 |
| **`exact` (shipped)** | 50/52 | 8/17 |
| `all` | **52/52** | 8/17 |

`all` fixes the Pastoral viola and takes the base corpus to perfect. Whatever the
earlier measurement was of, it is not what this flag does today — the pinning work
changed the join underneath it.

**It is still not shipped, and the reason matters.** On Beethoven 5 p.2 the tail
join is measurably WRONG — 4 of 5 — and `all` gets away with it only because the
part it picks there (Contrabass instead of the cello-and-bass staff) happens to
carry the same clef. A rule that is right because two wrong answers share an
answer is not a rule that has been tested. `exact` trusts only where there is
provably no freedom, and the benchmark cannot currently tell the two apart.

The honest resolution is not to pick by score. It is to ask whether the
uncertainty changes the ANSWER: re-run the join with the tail perturbed by one
part and supply the clef only if it does not move. That tests the thing actually
being relied on, and it would license the Pastoral (whose tail is right) without
licensing beet5-p2's (whose tail is wrong). Not built.

### 2. The fallback never fires on a page with a partial text layer

The Pastoral reads **4 labels** with `--vision-labels` on — the same 4 as without
it. The margin reader is never consulted, because the fallback is all-or-nothing:

```python
if labels or not vision_fallback or budget[0] <= 0:
    return labels          # <- any text-layer label at all, and we stop here
```

`VISION_CEILING_2026-08-30.md` measured that reader recovering **10** labels on
that exact page, all correct, where the text layer finds 4. Those 6 extra labels
are the ones that would carry the join down to the strings — and with 10 labels
the Pastoral's tail is 5 staves against exactly 5 free parts, so `exact` would
license it and the viola would be fixed **by better evidence rather than by a
looser trust rule.**

That is the next change, and it is the right one to make before touching the tail
rule again.


---

# 69 of 69 — 2026-08-30 (seventh pass)

**Every staff in the corpus reads its correct clef.** Base 3 at 52/52, p.48 at
17/17, and the Pastoral viola — the error every pass since the clef benchmark
began has left standing — is gone.

```bash
python3 benchmarks/omr-clef-geometry/eval_pipeline_clefs.py --contextual --dossier --vision-labels
```

| corpus | free path | **with `--vision-labels`** |
|---|---:|---:|
| overall (69 staves) | 58/69 | **69/69 = 100%** |
| base 3 | 50/52 | **52/52** |
| beet5-p48 | 8/17 | **17/17** |

The dossier supplies 12 staves and is right on all 12. The free path is
unchanged — both changes below are inert without labels, so nothing regressed.

It took two fixes, and the first was a bug in the rule shipped one pass earlier.

## The exact-tail rule was counting wrong

`_determined_tail` asks whether the staves below the last label are exactly as
many as the parts left over. It counted the leftovers from the assignment — and
**the assignment cannot express a condensed staff.** A staff carrying two parts
gets one index, the lower, so the second looks unconsumed.

The Pastoral is exactly that shape: five labelled wind staves carrying ten parts,
two to a staff. Counting from the assignment left five horn-and-friends parts
looking available, so the five string staves read as five staves chasing six
parts, the count did not close, and the tail stayed gated — **with the join
already 10 of 10 correct on that page, viola included.** The rule was rejecting
an answer it had.

`align_to_layout` now fills an optional `absorbed` map, `{staff: every part it
took}`, and the tail rule counts from that. The information was being computed
and thrown away in the traceback.

## The margin reader never fired on a partial text layer

The second fix, and the more general one:

```python
if labels or not vision_fallback or budget[0] <= 0:
    return labels          # <- any text-layer label at all, and we stop here
```

All-or-nothing. A scanned score's OCR layer is routinely *patchy* rather than
absent, and that is the case this skipped. The Pastoral got 4 labels of 10 staves
and never asked the reader, which `VISION_CEILING_2026-08-30.md` had already
measured recovering all 10.

Now `_well_covered` requires the text layer to name 75% of the widest system
before the margin is left alone, and where it does not, both are read and the
larger set wins. The margin reader abstains on unlabelled staves, so more labels
from it is more evidence rather than more guessing; if it returns fewer, or
fails, the text layer stands.

Measured effect on labels: Pastoral **4 → 10**, Beethoven 5 p.2 **9 → 14**.

Those six extra Pastoral labels are what close its tail: the last label moves
from staff 3 to staff 4, and below it sit five staves against exactly five
remaining parts. The viola is then supplied by the dossier — **by better
evidence, not by a looser trust rule**, which is what the previous pass said the
right fix would be.

## And the rejected tail rule stays rejected

`TAIL_RULE=all` also reaches 52/52, and the last pass recorded why that is not a
reason to ship it: on Beethoven 5 p.2 the tail join is wrong (4 of 5) and `all`
survives only because the part it picks carries the same clef as the right one.
That page's tail still has slack, `exact` still gates it, and it is still the row
where the two rules differ. Nothing about reaching 100% changes that — the
corpus simply cannot currently distinguish them, and the one page that could is
the one `exact` declines to answer.

## Guards

* `pytest tools/omr/tests -q` — **1061 passed** (+5: two for `absorbed` and the
  condensed tail, three for the coverage gate).
* free-path clef benchmark — 58/69, base 3 at 50/52, unchanged.
* `eval_join` — beet5-p48 17/17 as printed, beet5-p2 10/11, pastoral 9/10, all
  unchanged; beet5-p2's slack tail confirmed still gated.
* `eval_score_order` byte-identical (11/12, 5/10, 23/23); `eval_key_signatures`
  unchanged.

## What 100% does and does not mean

Four pages, 69 staves, three works, all Beethoven or Bach. It means the layer is
sound on what has been hand-read, not that clefs are solved. The next honest move
is more pages and other editions — which is where the misfires will be.


---

# The merge budget, rejected a second time — 2026-08-30 (eighth pass)

**The conventional cello-and-bass pair is not shipped. Again.** It fixes the page
it was designed for and breaks a different one, and the argument for why it would
be safe this time was wrong in a way worth writing down.

## Why it looked right

Beethoven 5 p.2 needs two condensations below the trumpets and makes two — but
it pairs the **viola** with the cello rather than the cello with the bass. Both
are ordinary cross-instrument merges at one price, so the choice falls to the
position term:

```
correct pairing (Vc+Cb on the last staff): position cost 0.0765
chosen  pairing (Vla+Vc on staff 9):       position cost 0.0588
-> the wrong one wins by 0.0176
```

That is not a threshold to tune. It is a fact the aligner does not have:
"Violoncello e Basso" is a printed convention and "Viola e Violoncello" is not.
Naming `(Cello, Contrabass)` as a cheaper conventional pair takes p.2 from
**10/11 to 11/11**, with the Pastoral apparently unmoved at 9/10.

## Why it was wrong

The pair was rejected in an earlier session (the Pastoral 9/10 → 7/10) because
"a cheap cross-instrument merge lets the aligner condense whenever it is short of
staves rather than only where the engraving does." The argument for reopening it
was that the ground had moved: merging is now offered only inside a span that is
genuinely short of staves, so the price can no longer run loose.

**That argument is wrong, and precisely how is the thing to keep:**

> The span bounds HOW MANY condensations happen. It does not bound WHICH.

The Pastoral's last span needs exactly one condensation. The cheap pair moves it
from the horns to the cello and bass; the horns then stretch across two staves to
keep the count, and every string staff below shifts by one.

| Pastoral p.2 | join | clefs |
|---|---:|---:|
| without the pair | 10/10 | 20/20 |
| **with it** | **5/10** | **16/20** |

And because the tail is now anchored, those wrong parts go straight into the
clefs. The corpus went **69/69 → 65/69**.

## How it nearly shipped, which is the more useful failure

`eval_join`'s realistic arm supplies **six** labels. The pipeline's margin reader
returns **five**. The sixth is `Violino I` — and it pins the string section,
concealing the entire failure. In the six-label arm the change scored a clean
10/10 on the Pastoral; under the pipeline's own conditions it scores 5/10.

The harness was measuring a condition the pipeline never sees, and it was the
harness that said ship. A fifth arm — **AS THE PIPELINE READS IT (5 labels)** —
now covers the real one, on every page:

| page | no labels | perfect | as printed | **as the pipeline reads it** |
|---|---:|---:|---:|---:|
| beet5-p48 | 8/17 | 17/17 | 17/17 | — *(labels are the print's own)* |
| beet5-p2 | 10/11 | 11/11 | 10/11 | **10/11** |
| pastoral-p2 | 4/10 | 9/10 | 10/10 | **10/10** |

## One fix kept from the attempt

The Pastoral's bottom staff is hand-read `Basso`, which the lexicon reads as the
bass VOICE; the join answers `Contrabass`, and the harness counted that wrong.
That is a measurement artifact — `Basso` is in `AMBIGUOUS_ALIASES` precisely
because it is both — and it has been reported as a join error since this harness
was written. The comparison now accepts any reading the alias allows, which is
why the Pastoral reads 10/10 above rather than 9/10.

## So the merge budget is still open

Which parts share a staff remains a fact about the PAGE. A price is a fact about
the WORK, and no price has yet been found that can express it. Two attempts have
now failed the same way, from opposite directions, and the second failed *after*
an explicit argument that the first no longer applied.

What is left costs **one staff on one page** — beet5-p2's bottom staff, whose
clef is right anyway because cello and contrabass are both bass. It is the
cheapest open item in this file, and the two rejections are worth more than
closing it would have been.

## Guards

1061 tests. Clef corpus back to **69/69** with `--vision-labels` (base 3 52/52,
p.48 17/17), free path 58/69 with base 3 at 50/52. `eval_score_order`
byte-identical. `eval_join` gains an arm and loses none.
