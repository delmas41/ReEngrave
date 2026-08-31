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
