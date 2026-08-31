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
