# Using LEGATO's system detector to find our own grouping bugs

**2026-08-31.** `findings.md` put connectivity grouping at 12/14 pages against
ground truth read off the left brackets by eye. Fourteen pages is what hand
labelling buys, and both remaining failures are MERGES — a real break that
something crosses — which is the case a bracket count is slowest to find.

`guangyangmusic/legato-1.5-YOLO` is a single-class `system` detector, 25.9M
params, trained on 1,024 annotated pages from single-staff to orchestral. The
question was whether it can improve our segmenter.

**It can, and not by replacing anything.** It is a model, trained by other people
on data we cannot see, so on a scan it has never met it can be wrong in ways its
own val set never showed. What it is, is *cheap* — so it can look at hundreds of
pages and say which handful deserve a human's eye. **A miner, not a label
source.** Every disagreement still gets adjudicated by looking.

```bash
python3 benchmarks/omr-system-grouping-2026-08/legato_crosscheck.py \
    --weights /path/to/legato-1.5-YOLO.pt
```

## The sweep

47 pages — Beethoven 5 and 6 from the IMSLP corpus, an 88-page Beethoven 5
scan, La Mer, Boléro, Mahler 5, the WTC, two Handel reductions.

| verdict | pages |
|---|--:|
| agree | 46 |
| **we_merge** | **1** |

A 2% flag rate is the useful part: it is cheap enough to run over a whole
library and hand-check everything it raises.

**Compare partitions, not counts.** Two groupings can both say "2 systems" and
disagree about which staves are in which. Each of our staves is assigned to
whichever LEGATO box contains its centre and the two partitions of the SAME
staves are compared. This immediately paid off — on Boléro p10 LEGATO returned
**3 boxes for a 2-system page**, one of them spanning almost the whole page and
overlapping the other two:

```
box y   32.5-2501.4  conf 0.63
box y   53.5-4869.3  conf 0.88     <- overlaps both
box y 2408.8-4902.8  conf 0.42
```

A count comparison would have logged that as a disagreement and sent someone to
look at a page that is fine. **LEGATO's raw box count is not a system count** —
it needs dedup before it means anything.

## The one real hit: Beethoven 5 (IMSLP984073) p40

We read **one system of 21 staves**. LEGATO read **three of seven**, at conf
0.94/0.95/0.95, in clean non-overlapping bands.

Adjudicated by rendering the left margin: there are **three brackets, three
measure numbers (229, 243, 256), and the instrument labels restart at each**
(Cl./Fag./Cor. — Cl./Fag./Cor. — Ob./Cl./Fag.). LEGATO is right; we merged three
systems into one. Evidence: `evidence/b5-p40-margin.png`.

That matters more than one page suggests, because `findings.md` already records
that **one bad system boundary poisons the whole document** — slots are assigned
per system and propagate.

## The cause, which is a one-line rule

`system_grouping.assign_systems`:

```python
elif bridging[i] == 0:
    system += 1
```

**A system break requires bridging of exactly zero.** Measured on p40, the two
true breaks are bridged 3 and 11, so neither fires and all 21 staves collapse
into one system:

| gap | px | bridged | what it is |
|---|--:|--:|---|
| 6→7 | 64 | **3** | **true system break — missed** |
| 13→14 | 71 | **11** | **true system break — missed** |
| 8→9 | 51 | 11 | bracket-group boundary |
| 9→10 | 54 | 11 | bracket-group boundary |
| 16→17 | 57 | 12 | bracket-group boundary |
| others | 25–47 | 42–66 | inside a group |

On the pages where we agree, the true break is bridged **exactly 0**:

| page | staves | break at | bridged | group boundaries |
|---|--:|--:|--:|---|
| p10 | 22 | 10 | **0** | 12–13, gaps 45–53 |
| p25 | 19 | 7 | **0** | 13–14, gaps 47–59 |
| p35 | 21 | 10 | **0** | 12–14, gaps 49–58 |

So the rule is not wrong so much as **zero-tolerance**: it works whenever
nothing at all crosses the break, and fails silently the moment a little ink
does — margin text, a measure number, scan noise. p40 prints its measure number
and restarts its instrument labels inside the very window the scan looks at.

## What would fix it, and why it is NOT implemented here

Neither signal separates the two cases alone:

- **Bridging alone cannot.** 11 at a true break on p40 against 11–14 at
  bracket-group boundaries on the same page.
- **Gap size alone cannot.** That is the original finding that motivated
  connectivity in the first place — inter-staff gaps inside one system run wider
  than the gaps between systems on other pages.

**The pair does**, on these four pages: true breaks are gap 64/71 with bridging
3/11, and the confusable group boundaries are gap 45–59 with bridging 11–14. So
"a large gap that is *nearly* unbridged" is the shape of the rule.

That is a hypothesis from four pages of one edition, and this repo's standing
rule — earned on the clef thresholds — is that a change passing on one corpus
means nothing. **It also cannot be regression-tested on this machine:**
`eval_grouping.py`'s 12-page ground truth is Beethoven 9, and the local IMSLP
corpus holds only symphonies 5 and 6. Changing a rule that currently reports
12/14 without being able to re-run those 14 pages is how a fix becomes a
regression.

So this stops at diagnosis. To finish it:

1. Restore the Beethoven 9 PDF so `eval_grouping.py` runs.
2. Add p40 to `CASES` with truth 3 — it is a free ground-truth page now that it
   has been adjudicated, and it is the first MERGE case in the set.
3. Run the crosscheck over a wider library to collect more merge candidates
   before touching the threshold, so the rule is fitted to more than one edition.
4. Only then relax `bridging == 0`.

## The other thing worth keeping

LEGATO placed every staff on all 47 pages — `staves_legato_missed` was 0
throughout, including the 32-staff Boléro page and the 38-staff Mahler. It never
disagreed with us in the `we_split` direction. On this corpus its recall for
systems is not the weak point; its precision (those overlapping Boléro boxes) is.
