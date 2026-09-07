# A lineup SWAP at constant staff count: found, and finding it does not help

2026-09-06. Branch `claude/lineup-swap-2026-09-06`.
Everything here is **default OFF** and nothing in `tools/omr/` changes any
shipped answer — asserted, not assumed (§6).

> **The boundary is detectable from the printed names, and detecting it makes
> the work WORSE.** The residual is not a segmentation fault. The document
> reference is one printed system and a slot carries one name for the whole
> document, so a movement whose lineup is not a subsequence of that system
> cannot be named however its staves are grouped. Brahms 4's shipped output is
> already **exactly at** that ceiling, so the split has nothing to win, and
> it lost 44 names.
>
> **The lever is the reference contest, not the boundary rule.** A one-line
> tie-break in `slots.reference_candidates` — the shape-frequency term its own
> tail already uses and its head does not — scores **556 → 682** correct on
> Brahms 4 and is **byte-identical** on Beethoven 5 and Beethoven 6.

Reproduce, in seconds, off committed artefacts:

    bash benchmarks/omr-lineup-swap-2026-09/probe/run_all.sh   # -> out/report.txt

---

## 1. The task, and the signal it named

`movement_reference.lineup_spans` keys on staff COUNT:

> *a page whose largest system is larger than every page before it has proved
> the lineup GREW there.*

Brahms 4 / Breitkopf breaks that axiom. Movements III and IV both print sixteen
staves with different lineups, so pages 41-98 are one span and every
movement-IV wind is named one slot low. The span-reach session named the
candidate signal: **the margin labels on pages 41 and 67 disagree.**

They do. Read off the committed caches (`probe/dump_full_systems.py`), the two
movement openings are unambiguous, and Breitkopf labels **every** system —
97 of 99 pages are label-rich, against 42 of 88 for Litolff's Beethoven 5.

---

## 2. The detector, and its noise floor

A **full system** is one whose staff count equals the span's own recurring
maximum — `score_full_systems.py`'s definition and its argument: a system
carrying every staff its region has IS that region's lineup, in printed order,
so ordinals correspond across full systems of one lineup and across nothing
else. An ordinal **supports** a split page *q* when the full systems left of
*q* hold one clear majority name and those from *q* on hold a different one.

**Measured over 122 candidate split pages, 7 count-derived spans, 4 hand-read
works** (§1 of `out/report.txt`):

| work | span | candidates | max support | what it is |
|---|---|--:|--:|---|
| Brahms 4 | 0-40 | 14 | **0** | one lineup |
| Beethoven 5 | 1-43 | 7 | **0** | one lineup |
| Beethoven 5 | 44-87 | 34 | **1** | one lineup — the noise floor |
| Beethoven 6 | 0-26 | 14 | **0** | one lineup |
| Brahms 1 | 45-85 | 12 | **0** | one lineup |
| Brahms 1 | 0-44 | 14 | **2** at q=25 | a REAL small swap, located exactly |
| **Brahms 4** | **41-98** | 27 | **8 at q=67** | the swap, located exactly |

Two things worth having beyond the headline:

⚠️ **Brahms 4 is not n=1.** `omr-identity-harness-2026-09/probe/corpus.py`
already records a second constant-count swap, hand-read: Brahms 1's second
movement is FOURTEEN staves like its first, with a horn staff out and a solo
violin in. The detector puts its best candidate at page 25 — mvt 1 is pages
0-25 — and scores 2, under the bar, so it abstains. A small swap being
invisible is the safe direction and is asserted as a test.

⚠️ **`MIN_SWAP_SUPPORT = 4` sits in the gap 2 &lt; 4 &lt; 8, not on a cliff.**
Anywhere in 3..8 reproduces every result here. It is a threshold on OCR, not an
axiom, and that is the first reason the flag is off.

### Two statistics, because one of them is flat

Support alone does not LOCATE the boundary. On a clean document a split five
pages early still leaves the right-hand side a two-thirds majority for the new
lineup and scores identically — the synthetic fixture ties at nine across the
whole span. **Purity** (the share of observations agreeing with their own
side's majority) is 1.0 only where both sides are one lineup, so the pair
`(support, purity)` peaks uniquely. Same division of labour as
`_first_page_above`: the coarse test CONFIRMS a boundary, something finer has to
PLACE it. A remaining tie **refuses** rather than picking — a boundary in the
wrong place hands one movement's pages the other's reference.

### Two fragilities found and fixed, both by the real data

* **The span's width must RECUR.** Brahms 1's finale span reads 17 staves on
  exactly one page against a printed 16; taking the maximum left the span with
  ONE full system and no detector at all over 41 pages. That is
  `build_reference`'s own recurrence test, for its own reason.
* **`MERGE_CAP_RATIO` applies here as in `_peaks`** — the same span read a
  28-staff merged system.

---

## 3. ⚠️ IT WORKS AND IT MAKES THE WORK WORSE

The rule fires on Brahms 4 at page 67, the hand-read boundary, and on nothing
else across the five label dumps. Then, off ONE warm read cache
(`probe/run_brahms4_2x2.sh`), graded on 772 judgeable staves of 52 full systems
against three hand-read lineups:

| arm | r0 (mvt I/II, 13) | r1 (mvt III, 16) | r2 (mvt IV, 16) | **total c/w/u** |
|---|---|---|---|---|
| no spans | 234/26/0 | 140/20/0 | 176/176/0 | 550/222/0 |
| **shipped** | 240/20/0 | 140/20/0 | 176/176/0 | **556/216/0** |
| **+ swap split** | 240/20/0 | 140/20/0 | **132/154/66** | **512/194/66** |
| + shape tie-break | 260/0/0 | 70/90/0 | 352/0/0 | **682/90/0** |
| + both | 260/0/0 | 60/60/40 | 352/0/0 | 672/60/40 |

**The split costs 44 correct names on the very region it was built to repair,
and it costs them in BOTH reference regimes.** `OMR_SPAN_REFERENCE_FIT=refuse`
does not rescue it: it abandons the span path entirely and returns the
no-spans row, 550.

⚠️ `wrong` FALLS from 216 to 194 while `correct` falls from 556 to 512, because
66 staves become `unnamed`. Reading the wrong-count alone would call this an
improvement. It is the same trap the identity harness records for
`impossible` — a column that can only fall is not a score.

---

## 4. Why: the reference cannot SAY the second lineup

`slots.build_reference` picks ONE printed system as the document reference and
`slot_instruments` gives each slot one name for the whole document. Spans decide
which SLOT a staff takes; they cannot decide what a slot is CALLED. So a span's
lineup is nameable only if it is a **subsequence** of the reference's names.

`probe/expressibility.py`, over four hand-read works:

| work | boundaries | union of lineups | largest printed system | every span expressible? |
|---|---|--:|--:|---|
| Beethoven 5 / Litolff | growth only | 17 | 17 | **YES** |
| Beethoven 6 / Litolff | growth only | 14 | 14 | **YES** |
| Brahms 1 / Breitkopf | holds a swap | 17 | 16 | **NO** — short a 3rd Violin |
| Brahms 4 / Breitkopf | holds a swap | 18 | 16 | **NO** — short 2 Trombones |

> **The count axiom is not merely a way of FINDING boundaries; it is what makes
> the span mechanism sound.** Taking a boundary only where the lineup grew
> guarantees the largest printed system is a superset of every span's lineup,
> so every span composes exactly. The two works spans repair are exactly the two
> that are growth-only. A swap boundary carries no such guarantee — that is what
> "no span arrangement can reach it" means, mechanically.

### The ceiling, and the fact that we are already on it

For a region whose size equals the reference's, the order-preserving placement
is the IDENTITY — there is no choice left — so the score is fixed the moment the
reference is chosen (`probe/ceiling.py`):

| region | systems | ceiling / system | ceiling | **achieved, shipped** |
|---|--:|--:|--:|--:|
| mvt III, 41-66 | 10 | 14 of 16 | 140 | **140** |
| mvt IV, 67-98 | 22 | **8 of 16** | 176 | **176** |

**Both regions are already at the ceiling.** There is no arrangement of spans
that scores one name more, which is why every arm that moves them moves them
down. `wrong direction` for a segmentation fix: the segmentation is not the
fault.

(mvt III's ceiling is 14 rather than 16 for two reasons that are not span work:
the reference's slot 7 is named `Trumpet` where the page prints a second horn
staff, and `Triangel` resolves to the lexicon's coarse `Percussion`.)

---

## 5. The lever that does move it: a tie-break, not a boundary

`slots.reference_candidates` ranks its TAIL by `(-size, -labels, -shapes[shape])`
— how many systems share the lineup is already in the ordering. Its HEAD does
not use that term:

```python
best = max(recurring, key=lambda v: (v.size, len(v.labels)))
```

`max` returns the FIRST maximum, so **a tie is broken by document order.** On
Brahms 4 seven systems tie at 16 staves and 15 labels — movement III's page 41
and six of movement IV's — and page 41 wins by being earlier. One margin read on
one page decides the vocabulary of the whole document.

Breaking that tie by shape frequency instead (`probe/compose_shapetie.py`,
measured by monkeypatch, **not** committed to `slots.py`):

| | Brahms 4 | Beethoven 5 | Beethoven 6 |
|---|---|---|---|
| correct, shipped | 556 / 772 | — | — |
| correct, shape tie-break | **682 / 772** | — | — |
| arm vs committed run | +126 | **byte-identical** | **byte-identical** |

The reference gains real `Trombone` slots; movement IV goes 176 → **352 of 352**
and movement I/II 240 → **260 of 260**; movement III pays 140 → 70, which is
exactly ITS counterfactual ceiling (7 of 16), and 22 systems outvote 10.

⚠️ **This is n=1 for the gain and its two controls cannot exercise it.** Litolff
labels winds and brass on every system and the strings on none, so a movement
OPENING carries strictly more labels than any other system and no tie arises —
which is why both are byte-identical, and why byte-identical is a weaker control
than it looks. The control that matters is a second **label-everything**
publisher.

⚠️ **Brahms 1 is that control, and it is half-run.** Computed off its committed
label evidence with no new read (`probe/tiebreak_ceiling.py`): the tie-break
*does* change its pick, p45 → p59, but **both are the finale lineup and the
ceiling is identical, 238 = 238.** So it is ceiling-neutral on the region the
arithmetic covers. Its three other regions are of different sizes and are
aligned by subsequence, which this arithmetic cannot settle — that needs a read
pass, which is the open item in §7.

⚠️ **It also trades.** It is not a free fix: movement III loses 70 names so that
movement IV can gain 176. The trade is right on this document because 22 systems
outvote 10, and it is right for the same reason `_shape` is already in the tail
— *a lineup recurs because the orchestra is the same on every page* — but a
document whose swap is the other way round would pay the other side. **Two
lineups, one vocabulary: something loses. That is the real shape of this
problem, and the only escape is a reference that is the UNION of the spans'
lineups rather than one printed system.**

---

## 6. What is committed, and the controls on it

* `tools/omr/movement_reference.py` — `swap_split_enabled()`
  (`OMR_LINEUP_SWAP_SPLIT`, **default off**) and the detector, ~90 lines, no
  new dependency and no new read. `lineup_spans` gains an OPTIONAL second
  argument; with it absent the function is unchanged.
* `tools/omr/tests/test_lineup_swap.py` — 16 tests, **verified RED**: neutering
  the split makes 6 of them fail, and the inertness test asserts BOTH
  directions (the same fixture must split under the flag) so it cannot pass
  vacuously.
* Flag-off is byte-identical at the ARTEFACT level too: `swap0-spans-on.json`
  md5-matches the span-reach session's committed `spans-on.json` for Brahms 4,
  through the patched call site.

**Neither standing benchmark can see any of this.** Part names do not reach
OMR-NED, and every `orchestral_eval` excerpt and all 20 scan-gate rows are
single-page, so spans take no boundary there and every flag here is a no-op.
That is why the grading is hand-read lineups.

⚠️ **`slots.py` is not touched.** Its owner today is another session. The swap
split is reachable only through a five-line change in `_span_views`, which
`probe/compose_swap.py` installs and which is exactly:

```python
page_labels = [(pws.page.page_index,
                [[v.labels.get(s.staff_index) for s in v.staves] for v in views])
               for pws, views in zip(pages, all_views)]
... movement_reference.lineup_spans(page_systems, page_labels)
```

`SystemView.labels` is already `{staff_index: instrument name}` filtered to
`MIN_LABEL_CONFIDENCE`, so the detector sees exactly what the aligner sees and
costs nothing. **Given §3, that change should NOT be made** unless a reference
that can express a swap lands first.

---

## 7. What I refused, and what would change the answer

**Refused: turning the swap split on, in any form.** It is measured worse in
both reference regimes on the only document that exercises it, and §4 says why
it must be, so a second document would not rescue it.

**Refused: making the split conditional on expressibility.** `movement_reference`
could compute from the labels alone whether the two sub-spans contain each
other, and refuse where they do not. It would be correct and it would be
vacuous: a constant-count swap is *by definition* two lineups neither of which
contains the other, so the guard fires always and the flag becomes a no-op with
extra code.

**Refused: a lower `MIN_SWAP_SUPPORT`.** Brahms 1's real small swap scores 2 and
the one-lineup noise floor is 1. A bar of 2 would catch it — and the whole point
of catching it is to split, which §3 says costs names.

**Refused: reporting the one-span read-pass controls.** Brahms 3 / Breitkopf and
Dvořák 9 / Simrock were launched as one-span controls for the detector and
abandoned at 13 of 166 pages, and their partial cache is not committed. The first attempt ran `OMR_SURYA_KEEP_ALIVE=0` —
correct for an unattended run, and 65 s/page; attaching to the machine's
resident server was *slower* at 2.6 min/page because four sibling sessions had
the load average at 51. Stopped by pid rather than left to compete with them.
`probe/run_controls.sh` is committed and re-runnable. It would strengthen the
detector's noise floor and would not change the recommendation.

**What would change the answer, in order:**

1. **A read pass on a second label-everything publisher** — Brahms 3 /
   Breitkopf is the cheapest, Brahms 1 / Breitkopf the most informative (its
   truth is already in `corpus.py` and §5's arithmetic covers only one of its
   four regions). That is the control the shape tie-break needs before anyone
   ships it.
2. **A document reference that is the UNION of the spans' lineups** rather than
   one printed system, with per-span slot names. That is the only thing that
   removes the ceiling instead of choosing which side pays it, and it makes the
   swap split useful for the first time. It is a `slots.py` change of real size
   and it needs its own measurement — `probe/expressibility.py` computes the
   union (shortest common supersequence in score order) if it is wanted.
3. **A unit smaller than the page.** The detector asks one question per pass and
   needs a majority on each side, so three lineups in equal measure inside one
   count-span defeat it (asserted as a test). Splitting on systems rather than
   pages would fix that; nothing measured needs it yet.

---

## Files

| file | what |
|---|---|
| `probe/run_all.sh` | everything off committed artefacts, seconds → `out/report.txt` |
| `probe/dump_labels.py` | label evidence per page, out of a read cache |
| `probe/labels_from_blob.py` | the same, out of a composed run's own blob — **no re-read** |
| `probe/changepoint.py` | the support profile over every candidate split |
| `probe/dump_full_systems.py` | the per-ordinal label sequences a profile is made of |
| `probe/ordinal_agreement.py` | within- vs across-region agreement, the first cut |
| `probe/run_spans.py` | `lineup_spans` flag off vs on, five dumps |
| `probe/expressibility.py` | can the reference SAY each span's lineup |
| `probe/ceiling.py` | the best any span rule could reach, per region |
| `probe/tiebreak_ceiling.py` | the reference contest and both winners' ceilings |
| `probe/score_arms.py` | correct/wrong/unnamed per REGION, any number of arms |
| `probe/compose_swap.py` | `compose.py` + the one call-site change |
| `probe/compose_shapetie.py` | `compose.py` + the reference tie-break (and the swap arm) |
| `probe/run_brahms4_2x2.sh` | the 2×2, off the warm cache |
| `probe/run_shapetie_controls.sh` | the tie-break on Beethoven 5 and 6 |
| `probe/run_controls.sh` | the abandoned one-span read passes, re-runnable |
