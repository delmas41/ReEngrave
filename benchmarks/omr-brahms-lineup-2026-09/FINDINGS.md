# Brahms 1 / Breitkopf, hand-read — and the span fix graded properly

⚠️ **Written by the coordinating session from the committed artefacts**, after the
agent that did the reading stalled (watchdog, no progress for 600s) before it
could write up. Everything below comes from `probe/score_brahms_lineups.py`,
`out/grade.txt` and `out/crops/`, committed as `0a3c50f6` — ⚠️ **except the
crops, which are NOT committed.** `benchmarks/**/crops/` is gitignored, so
`git ls-files` returns none of them and a reader cannot open a single image this
file cites. The page citations below are a record of what was looked at, not
retrievable evidence. Corrected 2026-09-07, after the bracket-reading session
tried to follow them and could not. **The page reading
is the agent's; I did not re-read the pages.** Where this file states what a
crop shows, that is its claim, sourced to the crop, not an independent one.

## Why

`OMR_SPAN_REFERENCE_FIT` took Brahms 1's pre-finale **impossible** names from
149 to 0. "Impossible" is a weak grade — it counts only names that cannot be
right (an instrument that has not entered yet) and says nothing about whether
the rest are correct. Beethoven 5 can be graded properly because someone hand-read
its pages. This does the same for Brahms.

## The four lineups, read off the print at 600 dpi

| pages | staves | what the margin sets |
|---|--:|---|
| 0-25 | **14** | mvt 1, full names at `p000-margin-all-sys0{,b}.png` |
| 33-35 | **14** | mvt 2 from the violin-solo entry — **a different lineup of the same size** |
| 36-44 | **12** | mvt 3, `p036-margin-all-look.png` |
| 45-85 | **16** | finale, `p045-margin-all-{A,B,C}.png` |

Corroborated on abbreviated continuation systems (p004, p017, p025, p041, p049,
p076, p084). Independently corroborated for INVENTORY by the work's IMSLP roster
(`source_kind: catalog`, independent of the encoding the benchmark scores
against): 2 fl, 2 ob, 2 cl, 2 bsn + contrabassoon, 4 hn, 2 tpt, **3 trombones,
0 tuba**, timp, strings.

⚠️ **Two facts nobody had recorded, and both matter.**

1. **Movement 3 is TWELVE staves — no Kontrafagott and no Pauken.** The work does
   not use them in that movement, which is why its full system is twelve and not
   fourteen. A span model that assumes lineups only GROW toward the finale is
   wrong about this document.
2. **The finale's 3 trombones are braced over TWO staves** (alto C clef, then
   bass). So slot 9 is the *second trombone staff*, not a tuba — and Brahms 1
   has no tuba at all.

## The grade

53 full systems, **764 staff records = 39.6% of the document's 1927**. Every arm
shares one staff-record key set (asserted on the KEY SET, not its size), so a
difference is the flag.

| arm | judgeable | correct | wrong | rate |
|---|--:|--:|--:|--:|
| `fit-off` (pre-fix) | 764 | 642 | 122 | 0.8403 |
| `fit-refuse` | 764 | **742** | 22 | **0.9712** |
| **`fit-search`** (shipped) | 764 | 741 | 23 | 0.9699 |

**The span fix is worth 0.8403 → 0.9699**, and the confusion list shows what it
removes: `Horn -> Trumpet` ×33, `Trumpet -> Trombone` ×33, `Timpani -> Tuba` ×28,
`Violin -> Tuba` ×8 all go to zero.

## ⚠️ The two columns disagree about which arm is better

`refuse` grades one staff BETTER than the shipped `search` (742 vs 741) — it
reads 24/28 on the `p33-35/14` lineup where search reads 22/28. But on the
`impossible` column `search` is **0** and `refuse` is **36**.

Both are true. `search` fixes 149 staves and mis-slots 6 on the solo-violin
pages; `refuse` declines to place that span at all and leaves 36 categorically
impossible names standing. **A correct/wrong grade and an impossible count
reward different things, and neither is a superset of the other** — impossible
can only fall, so it scores a categorically-wrong name traded for an
ordinarily-wrong one as free.

The shipped default remains `search`. This is not evidence to change it — a
16-fold reduction in impossible names against one staff of correct/wrong — but
it IS the kind of disagreement that should be visible rather than averaged away.

## The residue the span fix does not touch

`p45-85/16` reads **255/272 = 0.9375 in every arm**, with `Trombone -> Tuba` ×17
surviving all three. Given fact (2) above, that is the **second trombone staff of
a braced pair being named a tuba in a work that has no tuba** — a separate fault,
untouched by anything landed today, and now precisely located.

## Reproduce

    python3 probe/score_brahms_lineups.py off=BLOB.json search=BLOB.json --veto off

⚠️ Judgeable coverage is **39.6%**, much lower than Beethoven's 807/1616 (49.9%),
because only full systems are scored and this document's reduced systems are
common. A figure over 764 records is not directly comparable to one over 807.
