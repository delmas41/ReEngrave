# Widening the engraved orchestral benchmark — 3 works to ten

**2026-09-01.** Sixteen fixes have been landed against the same three pages
(`beethoven-sym5-mvt1`, `brahms-sym1-mvt1`, `mahler-sym5-mvt1`), taking pooled
OMR-NED 0.3164 -> 0.1364. Every one of them was measured on those three and on
nothing else.

This project's own repeated lesson — *a sweep corpus is built from the
candidates the locator fires on, so it cannot answer "what does this rule cost
in the wild"*; *never tune a clef threshold on one edition* — now applies to its
main benchmark. Nothing measures whether those sixteen fixes generalise even to
other **engraved** pages, let alone scanned ones.

This file is that measurement.

```bash
python3 -m tools.omr.training.orchestral_eval --works <ids...> --omr-ned \
    --work-dir benchmarks/omr-corpus-widening-2026-09/fixtures \
    --out benchmarks/omr-corpus-widening-2026-09/out/<batch>.json
```

WARNING: `--works` off the default prints a not-the-benchmark warning; that is
expected. The canonical figure remains the three-work pooled number in
CLAUDE.md's OMR-NED section, and nothing here rewrites it. A separate
`--work-dir` is used throughout so a parallel canonical run cannot collide with
these fixtures.

## Baseline this was run against

`d7bfc37`, reproduced in this worktree before anything was touched:

    pooled 0.1364, 966 edits   (mahler 0.0455, beethoven 0.1649, brahms 0.1709)

---

## 1. Selection — ten works, and why each one

97 dossiers exist and **all 97 have a source score** under `SCORE_DIR`, so the
constraint is not availability, it is choosing. Every candidate was ranked on
the three axes that could plausibly break a fix tuned on three pages: **era /
composer**, **part count** (the paper size and therefore the staff spacing scale
with it), and **texture / meter**.

Two rules applied before diversity:

- **Orchestral only** — standing instruction. `h186` (C. P. E. Bach, 2 parts)
  and `ravel-bolero` (9 parts, labelled in its own dossier "study reduction")
  are excluded as not conductor's pages.
- **A near-neighbour control for each incumbent.** `beethoven-sym3-mvt1` and
  `brahms-sym4-mvt1` are the same composer and idiom as two of the three works
  every fix was tuned on. If a fix is page-tuned rather than mechanism-true,
  the near neighbour is where it shows first — a distant composer failing is
  ambiguous (could be genuinely harder music), a near neighbour failing is not.

| # | work | parts | meter | why this one |
|---|---|--:|---|---|
| 1 | `mozart-sym40-mvt1` | 11 | 2/2 | Smallest true orchestra in the corpus. Classical, sparse texture — the opposite end of the density axis from Mahler, and the DPI/imgsz note in CLAUDE.md says sparse and dense pages want different settings. |
| 2 | `mozart-sym41-mvt1` | 17 | 4/4 | Classical with trumpets and timpani. Same era as 1, half again the parts — isolates part count from era. |
| 3 | `beethoven-sym3-mvt1` | 19 | 3/4 | **Near-neighbour control** for the incumbent `beethoven-sym5-mvt1`. Same composer, same forces, different meter and key. |
| 4 | `brahms-sym4-mvt1` | 20 | 2/2 | **Near-neighbour control** for the incumbent `brahms-sym1-mvt1`, which is the worst incumbent row and the one most fixes were aimed at. |
| 5 | `dvorak-sym9-mvt4` | 19 | 4/4 | New composer, mainstream romantic. Carries `bass_8vb`, a clef family the incumbents do not have. |
| 6 | `tchaikovsky-sym4-mvt2` | 20 | 2/4 | New composer, romantic. Same meter as Beethoven 5 at a larger part count. |
| 7 | `tchaikovsky-sym6-mvt2` | 17 | **5/4** | **Odd meter.** `_reconcile_measure_to_meter` and `drop_uncorroborated_meter_changes` are written against a meter; nothing in the benchmark has ever printed a quintuple one. |
| 8 | `bruckner-sym5-mvt1` | 25 | 2/2 | Late romantic, larger than any incumbent except Mahler, and long-breathed rather than dense — a different way to be big. |
| 9 | `mahler-sym5-mvt4` | 9 | 4/4 | The Adagietto — **strings and harp only**, no winds. Late-romantic idiom at 9 staves. The composer-matched control for the incumbent Mahler at the opposite extreme of forces. |
| 10 | `boulanger-printemps-mvt1` | 46 | 3/4 | Impressionist, and the largest score attempted. Paper goes to a2 here (>40 parts), which no incumbent triggers. |

Deliberately **not** chosen: `holst-planets-*` (64 parts) and
`ravel-bolero-pt2` (95 parts). Beyond a2 the staff spacing question the fixture
docstring documents ("a4 gave Mahler 1.0 spaces between staves and the page
became one continuous ladder") re-opens, and a row that measures the fixture's
paper size rather than the pipeline is worse than no row.

---

## 2. The work table

Nine works ran; **one failed and is recorded as a failure, not fought for**:

    mahler-sym5-mvt4  FAILED: CalledProcessError: Command '['musicxml2ly', '-o',
      'benchmarks/omr-corpus-widening-2026-09/fixtures/mahler-sym5-mvt4.ly',
      '.../mahler-sym5-mvt4.musicxml']' returned non-zero exit status 1.

`boulanger-printemps-mvt1` ran and is reported, with a caveat: at 46 parts it
is the only work whose STRUCTURE fails. It emits 43 parts against 46 and its
budget is 54% `entire measure insert/delete` plus 22% `entire staff
insert/delete` — it is measuring page segmentation on an a2 sheet, not note
recognition, and it dominates any pool it is in. It is kept as an honest row
and excluded from the pooled line, which is stated both ways.

| work | bars | parts | OMR-NED | edits | truth | pred | recall | prec | dur |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| `tchaikovsky-sym4-mvt2` | 8 | 20/20 | **0.0571** | 88 | 786 | 755 | 0.925 | 0.925 | 1.000 |
| `bruckner-sym5-mvt1` | 8 | 25/25 | **0.1431** | 284 | 1007 | 977 | 0.962 | 0.962 | 1.000 |
| `beethoven-sym3-mvt1` | 8 | 19/19 | **0.1553** | 252 | 882 | 741 | 0.975 | 0.975 | 1.000 |
| `tchaikovsky-sym6-mvt2` | 4 | 17/17 | **0.2321** | 328 | 730 | 683 | 0.756 | 0.747 | 0.892 |
| `mozart-sym40-mvt1` | 6 | 11/11 | **0.2468** | 363 | 788 | 683 | 0.762 | 0.762 | 0.952 |
| `brahms-sym4-mvt1` | 6 | 20/20 | **0.2849** | 520 | 949 | 876 | 0.959 | 0.943 | 0.933 |
| `dvorak-sym9-mvt4` | 3 | 18/19 | **0.4106** | 294 | 373 | 343 | 0.975 | 0.975 | 1.000 |
| `mozart-sym41-mvt1` | 6 | 17/17 | **0.5674** | 1562 | 1454 | 1299 | 0.991 | 0.991 | 0.465 |
| `boulanger-printemps-mvt1` | 8 | 43/46 | 0.6971 | 5155 | 3969 | 3426 | 0.783 | 0.768 | 0.880 |
| **pooled (8, without Boulanger)** | | | **0.2770** | 3691 | 6969 | 6357 | | | |
| pooled (all 9) | | | 0.4269 | 8846 | 10938 | 9783 | | | |

**The headline: the new corpus scores 0.2770 against the incumbents' 0.1364 —
almost exactly twice the error rate**, on music of the same kind, engraved by
the same LilyPond from the same kind of source. Whatever the sixteen fixes
bought, roughly half of it does not appear on a page they were not measured on.

Three readings that matter more than the pooled number:

- **The near-neighbour controls PASS.** `beethoven-sym3-mvt1` scores 0.1553
  against the incumbent Beethoven 5's 0.1649, with **96.2% of its notes in
  `exact` measures** and a duration rate of 1.000. `brahms-sym4-mvt1` is 0.2849
  against Brahms 1's 0.1709 — worse, but its recall is 0.959 and its duration
  rate 0.933, both close to the incumbent. Nothing in the sixteen fixes is
  Beethoven-5-shaped or Brahms-1-shaped. That is the single most reassuring
  result here and it was the thing most worth checking.
- **`tchaikovsky-sym4-mvt2` at 0.0571 is the best score any work has ever
  posted on this harness**, incumbents included. A new composer, 20 parts, and
  a duration rate of 1.000. The pipeline is not fragile in general.
- **The spread is enormous — 0.0571 to 0.5674, a factor of ten.** The pooled
  figure over three works was hiding a distribution, not summarising one.

⚠️ **Read `dvorak-sym9-mvt4` with care.** Its excerpt auto-shrank to **3 bars**
(the one-page fit), so its denominator is a third of everyone else's and its
ratio is the noisiest in the table. It also reports 18 parts against 19.

---

## 3. Ranked failure modes

Ranked by edits, and by how many works carry them — *a failure on three new
works outranks one work\'s quirk*. All three of the top items are the same shape
this repository has now paid for eight times: **the signal is already detected
and something downstream throws it away.**

### 1. The time signature SYMBOL is detected at 0.89-0.96 and exported as digits — 273 edits, 5 works

The numbers are right on **every single work in the corpus**. What is lost is
the `symbol` attribute:

| work | truth | prediction | staves | edits |
|---|---|---|--:|--:|
| `bruckner-sym5-mvt1` | `2/2 symbol="cut"` | `2/2` | 25 | 75 |
| `brahms-sym4-mvt1` | `2/2 symbol="cut"` | `2/2` | 20 | 60 |
| `mozart-sym41-mvt1` | `4/4 symbol="common"` | `4/4` | 17 | 51 |
| `dvorak-sym9-mvt4` | `4/4 symbol="common"` | `4/4` | 18 | 54 |
| `mozart-sym40-mvt1` | `2/2 symbol="cut"` | `2/2` | 11 | 33 |
| **incumbents (all three)** | digit meters | digit meters | | **0** |

It is **exactly 3 edits per staff** — `extrainfoedit`, one op per staff at cost
3 — which is how the arithmetic closes: Mozart 41 17 staves x 3 = 51 and Mozart
40 11 x 3 = 33 sum to the 84 the eval reported as `wrong timesig` for batch 1.

**Zero on the incumbents, because all three print digit meters.** Beethoven 5 is
2/4, Brahms 1 is 6/8, and Mahler 5\'s source does not mark its 2/2 as cut. A
category worth 270 edits was invisible because three pages happened not to print
a C or a stroked C.

**The glyph is read, and read well.** `parse_time_signature` returns
`{"numerator": 2, "denominator": 2, "raw": "C|"}` for cut common and
`raw: "C"` for common, off `timeSigCutCommon` / `timeSigCommon` detections at
confidence **0.92-0.96** (Mozart 40, 11 of 11 staves) and **0.89-0.92**
(Mozart 41, 17 of 17). Two things then discard it:

1. `dossier.apply_meter` replaces the whole dict with
   `{numerator, denominator, source: "dossier"}` — including on the branch where
   the detector **agreed** (`if got == want`). `raw` is dropped there.
2. `export.to_musicxml` emits `<beats>` and `<beat-type>` and never reads `raw`
   at all, so even Brahms 1 (which keeps `raw: "6/8"`) gains nothing from it.

The division that fixes it is the one the pipeline already believes elsewhere:
**the dossier knows what the meter IS; only the page can say how it was
PRINTED.** A cut-common glyph is a property of the edition, not of the work, so
it cannot come from the dossier — and it does not need to.

### 2. Triplet digits are classified `fingering3` and filtered out — Mozart 41, and it is 57% of its notes

`mozart-sym41-mvt1` has note recall **0.991** and a duration rate of **0.465**:
the notes are found and pitched correctly and more than half are the wrong
length. The whole of it is one thing:

    by TRUE duration (wrong / total)
        1/6 ql   120 / 120     <- every triplet sixteenth on the page
          1 ql     9 /  91

Dominant ratio **3/2, 70 notes** — a triplet read straight, the signature the
attribution report named. The truth has 40 triplet groups (`actual-notes 3,
normal-notes 2`); the prediction emits 11.

**The digits are detected. They are filed under the wrong class:**

    tuplet3     13   category "structural"
    fingering3  30   category "ornament"     <- dropped

43 detections for 40 printed groups. Correlating them against the truth
group-by-group: of the **20 cells that contain triplets, 18 carry a detected
digit**, and exactly **1** detection sits in a cell with no triplet in it. This
is not a detection failure at all — coverage is 90% — it is a class label.

`rhythm._tuplet_groups` collects digits with
`if getattr(d, "category", "") != "structural": continue`, so every
`fingering3` is discarded before the gate that would have judged it.

⚠️ **A DOCUMENTED CLAIM ABOUT THE INCUMBENT MAHLER IS WRONG, and this is how
the widening earned its keep.** CLAUDE.md and the attribution report both say
its fifth triplet group "carries no marker at all, at any confidence", and it
has stood as that work\'s named residue since the tuplet fix. Mahler\'s five
triplet groups are all on staff 17, `Vier Trompeten in B.`, measures 0, 1, 3, 4
and 5:

    m0  tuplet3 0.32
    m1  tupletBracket 0.25
    m3  tuplet3 0.51 + tupletBracket 0.45
    m4  fingering3 0.72        <- the "missing" fifth marker
    m5  tuplet3 0.50

The fifth marker is not missing and is not faint. It is the **highest-confidence
tuplet marker on the page** and it came back under the other class name. Nobody
looked because the work had a plausible story, and a plausible story about one
page is exactly what three pages cannot falsify.

Beethoven 5 and Brahms 1 have no `fingering3` at all, so they cannot move.

### 3. Articulations are detected and never exported — 6 works

`export.py` contains the string "articulation" **once, in a docstring.** There
is no articulation code in the pipeline at all, while the detector maps every
`artic*` class to category `ornament` and fires freely:

| work | artic detections | `insarticulation` edits |
|---|--:|--:|
| `mozart-sym40-mvt1` | **102** (51 above + 51 below) | **102** |
| `brahms-sym4-mvt1` | 58 | |
| `beethoven-sym3-mvt1` | 26 | **38** |
| `dvorak-sym9-mvt4` | 10 | |
| `mozart-sym41-mvt1` | 4 | |
| `mahler-sym5-mvt1` (incumbent) | 6 | 6 |
| `brahms-sym1-mvt1` (incumbent) | 2 | |
| `beethoven-sym5-mvt1` (incumbent) | **0** | 0 |

Mozart 40 detects **exactly 102** staccato marks and is charged **exactly 102**
`insarticulation` ops — 28% of that work\'s entire budget, and the single
largest line in its op list after wrong notes.

Again the incumbents could not show it: 0, 2 and 6 detections across the three
pages every fix was measured on.

**An attachment rule was measured before it was written**
(`probe_articulations.py`), because emitting a mark on the wrong note costs the
same as not emitting it. The rule under test is the obvious one, in the unit the
dot fix insisted on: take the notehead whose x-centre is nearest the mark\'s, on
the side the DSv2 class names (`...Above` / `...Below`), within N notehead
widths. Scored by index against the truth over eight works:

| max_dx (notehead widths) | placed | on an articulated note | precision | placement rate |
|--:|--:|--:|--:|--:|
| 0.30 | 106 | 102 | 0.962 | 0.486 |
| **0.50** | 197 | 193 | **0.980** | **0.904** |
| **0.75** | 197 | 193 | **0.980** | **0.904** |
| **1.00** | 197 | 193 | **0.980** | **0.904** |
| **1.50** | 197 | 193 | **0.980** | **0.904** |
| **2.50** | 197 | 193 | **0.980** | **0.904** |

**A flat plateau from 0.50 to 2.50 — identical to the mark — with a cliff below
it.** That is what a constant read off a gap looks like rather than one tuned to
a corpus: a mark is x-centred on its notehead to within half a width, and on the
correct side there is nothing else within 2.5. The 21 marks of 218 that are
never placed have no notehead on the correct side in their cell, and abstaining
there is right.

⚠️ **`boulanger-printemps-mvt1` is excluded from that table and the reason is a
trap worth naming.** Scored with it, precision reads **0.525** — because the
probe joins prediction to truth by INDEX, and Boulanger emits 43 parts against
46, so the join is meaningless there and every mark is scored against the wrong
part. The rule is not worse on Boulanger; the measurement is. Any index-joined
metric over this corpus has the same hole, and it is the only work in it wide
enough to fall through.

### 4. Smaller, recorded but not yet acted on

- **`tchaikovsky-sym6-mvt2` (5/4) has recall 0.756**, the second-worst in the
  corpus, and 22 truth time signatures against 17 predicted. The odd meter is
  the reason it was chosen and it is the only work whose *structure* count
  disagrees. Not yet attributed.
- **`mozart-sym40-mvt1` puts 41.5% of its notes in `order` bars**, essentially
  all of them the Viola\'s divisi double stops (96 notes, 4 of 6 bars). The
  `order` class was shown to cost nothing directly in the Brahms Viola work;
  what it costs here is the eval\'s own note recall, which reads 0.762 while
  every pitch is present.
- **Margin-label lexicon misses**, all engraved pages with a clean text layer:
  `'larinetti in B.'` and `'mpani in C-G'` (Mozart) are **leading characters
  lost**, `'Oboes'` (batch 2) is an English plural absent from
  `tools/omr/instruments.py`. Cheap, and separate from the three above.

---

## 4. Fixes and refusals

### FIX 1 — the time signature carries its glyph (`symbol="common"` / `"cut"`)

**The canonical three do not regress.** Measured on the same tree, same
harness, in this benchmark\'s own `--work-dir`:

| work | before | after | |
|---|--:|--:|---|
| `beethoven-sym5-mvt1` | 0.1649 / 205 | 0.1649 / 205 | identical |
| `mahler-sym5-mvt1` | 0.0455 / 86 | 0.0455 / 86 | identical |
| `brahms-sym1-mvt1` | 0.1709 / 675 | **0.1707 / 674** | **−1 edit** |
| **pooled** | 0.1364 / 966 | **0.1363 / 965** | |

⚠️ **Brahms 1 moved by one edit and it is NOT a recognition gain — it is a
misread reported more completely.** That page is 6/8, and on one staff of
twenty-one the detector reads `timeSigCommon`. `brahms-sym1-mvt1` has
`constant_meter: false`, so `expected_meter` abstains and `apply_meter` never
runs — the misread stands, exactly as it did before. What changed is that the
export now says which glyph was read, so that staff emits
`<time symbol="common">4/4` instead of `<time>4/4` against a truth of `6/8`,
and musicdiff happens to price the two forms one edit apart. Counted:
**Brahms gains exactly 1 `symbol=` attribute, Beethoven and Mahler gain 0**, so
the other two works are byte-identical by construction rather than by
comparison.

That is worth stating plainly rather than banking: the fix is justified by the
five works below, not by this edit.

### What it bought — 273 edits, and every work moved by exactly 3 x its staves

| work | before | after | delta | staves x 3 |
|---|--:|--:|--:|--:|
| `bruckner-sym5-mvt1` | 0.1431 / 284 | **0.1067 / 209** | −75 | 25 x 3 = 75 |
| `brahms-sym4-mvt1` | 0.2849 / 520 | **0.2548 / 460** | −60 | 20 x 3 = 60 |
| `dvorak-sym9-mvt4` | 0.4106 / 294 | **0.3438 / 240** | −54 | 18 x 3 = 54 |
| `mozart-sym41-mvt1` | 0.5674 / 1562 | **0.5523 / 1511** | −51 | 17 x 3 = 51 |
| `mozart-sym40-mvt1` | 0.2468 / 363 | **0.2260 / 330** | −33 | 11 x 3 = 33 |
| `beethoven-sym3-mvt1` | 0.1553 / 252 | 0.1553 / 252 | **0** | 3/4, no glyph |
| | | | **−273** | |

**Every delta is exactly three times the staff count**, which is the strongest
form this evidence could take: the mechanism predicted the size of its own fix
before the run, per work, and was right five times out of five. `wrong timesig`
has disappeared from the category list of every batch.

`beethoven-sym3-mvt1` is the control and is **identical to the edit** — it is in
3/4, prints digits, and nothing about it changes. The exports confirm the same
thing by count: Mozart 40 emits 11 `<time symbol="cut">` for its 11 staves and
Mozart 41 emits 17 `<time symbol="common">` for its 17, matching their truths
exactly, while Beethoven 5 and Mahler 5 emit none at all.

### What the fix is

Three changes, and the division between them is the point:

1. `rhythm.parse_time_signature` sets a new **`symbol`** key ("common" / "cut")
   on the two branches where a `timeSigCommon` / `timeSigCutCommon` GLYPH was
   detected.
2. `dossier.apply_meter` keeps that `symbol` when the detected numbers equal
   the dossier\'s, and drops it otherwise.
3. `export.to_musicxml` emits `symbol=` from it.

⚠️ **`symbol` is a new key rather than a reuse of `raw`, and that is
load-bearing.** `raw` looks like it already holds the glyph — it is `"C"` for
common time and `"C|"` for cut — but `_propagated_meter` **synthesises** it from
the winning numbers (`"C" if (num, den) == (4, 4)`), so a `raw` of `"C"` is not
evidence that a C was printed. Exporting off `raw` would have stamped
`symbol="common"` on every 4/4 page in the corpus whether or not the glyph is
there, which is the same class of mistake as inferring a signal that was never
read. `symbol` is set in exactly one place, off the glyph.

**The numbers come from the work; the glyph comes from the page.** A dossier is
generated from one MusicXML file and can say that a movement is in 2/2 — it
cannot say whether the edition in hand set that as `¢` or as two digits, because
that is a fact about the engraving. So the symbol could not have come from the
dossier and did not need to: the detector reads it at 0.89-0.96.

### Refused along the way

- **Deriving the symbol from the numbers.** Rejected before measurement, on the
  grounds above: it asserts a difference nobody read. The distinction is now
  guarded by `test_raw_alone_does_not_produce_a_symbol`.
- **Teaching the LilyPond exporter to match.** `\\time 4/4` already renders as a
  C in LilyPond and `\\time 2/2` as a stroked C, so the LilyPond path is right
  for these five works by accident and wrong for a page that prints digits —
  `\\numericTimeSignature` is the lever. Not touched: LilyPond is not what
  OMR-NED scores, and an unmeasured change to it is churn.

---

### FIX 2 — a triplet digit is a triplet digit whichever class it arrives under

`rhythm._tuplet_groups` collected digits only from `category == "structural"`,
so every `fingering3` was discarded before the gate that would have judged it.
The class is now admitted and **the gate is untouched** — the digit\'s centre
must still fall inside a BEAMED group\'s span, and the group must still hold
exactly as many notes as the digit claims.

Measured on its own, before the second fault below was found:

| work | before | after | |
|---|--:|--:|---|
| `mahler-sym5-mvt1` (incumbent) | 0.0455 / 86 | **0.0364 / 69** | **−17** |
| `tchaikovsky-sym6-mvt2` | 0.2321 / 328 | **0.1958 / 279** | **−49** |
| `beethoven-sym5-mvt1` | 0.1649 / 205 | 0.1649 / 205 | identical |
| `brahms-sym1-mvt1` | 0.1707 / 674 | 0.1707 / 674 | identical |
| `mozart-sym40-mvt1` | 0.2260 / 330 | 0.2260 / 330 | identical (no `fingering3`) |

Tchaikovsky 6\'s duration rate went **0.892 → 0.985** and its six triplet notes
from 6 wrong to **0**. Mahler\'s recovered fifth group is the one this file
said above was never missing.

### And the fault that fix 2 uncovered — the ratio applied TWICE

`mozart-sym41-mvt1` is why the edit count has to be read beside the ratio. Its
OMR-NED fell 0.5523 → 0.5239 while its **edits ROSE, 1511 → 1515**, and its
predicted symbols rose by 156. That is the dilution signature the FINDINGS file
warns about, and here it was hiding a real bug rather than a null result: the
duration probe showed the dominant ratio had flipped from **3/2 on 70 notes**
(read straight) to **2/3 on 89** — and `(1/4) × (2/3) × (2/3) = 1/9`.

`_beamed_groups` returns one group per BEAM BOX. **A sixteenth carries two beam
strokes**, the CV detector finds both, and each produced its own group over the
same three noteheads — so `resolve_rhythms_for_cell` scaled them once per
stroke. A group is a set of NOTES, not a stroke, and identical member sets are
now collapsed.

⚠️ **This bug predates all of tonight\'s work and the old benchmark could not
show it.** Every triplet in Beethoven 5, Brahms 1 and Mahler 5 is an EIGHTH
triplet — one stroke, one group, no duplication. `mozart-sym41-mvt1` prints 40
groups of triplet SIXTEENTHS, and it took both the wider corpus and the class
admission for the fault to become visible at all: with only 11 of 40 groups
claimed it was there, quiet, in a work nobody was measuring.

---

### FIX 3 — articulations reach the export, both of them

`export.py` contained the string "articulation" once, in a docstring. Nothing in
the pipeline attached a mark to a note, and nothing emitted one.

| work | before | after | |
|---|--:|--:|---|
| `mozart-sym40-mvt1` | 0.2260 / 330 | **0.1772 / 273** | **−57** |
| `mahler-sym5-mvt1` (incumbent) | 0.0364 / 69 | **0.0331 / 63** | **−6**, its 6 detections exactly |
| `beethoven-sym5-mvt1` | 0.1649 / 205 | 0.1649 / 205 | identical |
| `brahms-sym1-mvt1` | 0.1707 / 674 | 0.1707 / 674 | identical |
| `tchaikovsky-sym6-mvt2` | 0.1958 / 279 | 0.1958 / 279 | identical (prints none) |

`wrong articulation` over the batch that holds Mozart 40 fell **102 → 37**.

**Coverage, detected -> attached -> exported**, on the works whose fixtures had
been regenerated when this was taken:

| work | detected | attached | exported | truth |
|---|--:|--:|--:|--:|
| `mozart-sym40-mvt1` | 102 | 101 | 81 | 110 |
| `brahms-sym4-mvt1` | 58 | 55 | 55 | 60 |
| `beethoven-sym3-mvt1` | 26 | 21 | 21 | 38 |
| `dvorak-sym9-mvt4` | 10 | 9 | 9 | 10 |
| `mahler-sym5-mvt1` | 6 | 6 | 6 | 6 |

Mozart 40\'s 101 → 81 is the chord rule working: its Viola plays divisi double
stops, both noteheads attach their own staccato, and a chord takes ONE mark.

⚠️ **An articulation on a note the aligner cannot pair buys nothing.**
`dvorak-sym9-mvt4` exports 9 of its 10 accents correctly and moves by **one
edit** (240 → 239), because its marks sit in bars already charged as whole-bar
inserts and deletes. That is the `entire measure` amplification caveat running
in the unhelpful direction, and it is why the articulation gains are so uneven
across works — 57 on Mozart 40, 1 on Dvorak, for comparable per-mark accuracy.

**The residue is named, not scattered.** Mozart 40\'s truth carries 96
`<staccato/>` and **14 `<detached-legato/>`**; the prediction emits 81
staccato. Detached legato is *portato* — a staccato dot printed UNDER A SLUR —
and DSv2 has no class for it, because on the page it is a staccato dot. The
detector is right about the glyph and the truth is right about the meaning, and
nothing between them can bridge that without reading the slur and the dot
together. The other ~15 are marks with no notehead on the correct side of them,
which the rule declines by design.

---

### All three fixes, over the whole corpus

| work | before | after | delta |
|---|--:|--:|--:|
| `mozart-sym41-mvt1` | 0.5674 / 1562 | **0.3632 / 1051** | **−511** |
| `brahms-sym4-mvt1` | 0.2849 / 520 | **0.2296 / 427** | −93 |
| `mozart-sym40-mvt1` | 0.2468 / 363 | **0.1772 / 273** | −90 |
| `bruckner-sym5-mvt1` | 0.1431 / 284 | **0.1042 / 205** | −79 |
| `dvorak-sym9-mvt4` | 0.4106 / 294 | **0.3380 / 239** | −55 |
| `tchaikovsky-sym6-mvt2` | 0.2321 / 328 | **0.1958 / 279** | −49 |
| `beethoven-sym3-mvt1` | 0.1553 / 252 | **0.1405 / 231** | −21 |
| `tchaikovsky-sym4-mvt2` | 0.0571 / 88 | 0.0571 / 88 | 0 |
| `boulanger-printemps-mvt1` | 0.6971 / 5155 | 0.7017 / 5374 | **+219** |
| **pooled (8, without Boulanger)** | 0.2770 / 3691 | **0.2057 / 2793** | **−898** |
| pooled (all 9) | 0.4269 / 8846 | **0.3846 / 8167** | −679 |

Note recall and duration rate moved only where the fixes touch rhythm:

| work | recall | duration rate |
|---|--:|--:|
| `mozart-sym41-mvt1` | 0.991 → **1.000** | 0.465 → **0.868** |
| `tchaikovsky-sym6-mvt2` | 0.756 → 0.756 | 0.892 → **0.985** |
| every other work | unchanged | unchanged |

**The canonical three, measured on the same tree:**

| | before | after |
|---|--:|--:|
| `beethoven-sym5-mvt1` | 0.1649 / 205 | 0.1649 / 205 |
| `brahms-sym1-mvt1` | 0.1709 / 675 | 0.1707 / 674 |
| `mahler-sym5-mvt1` | 0.0455 / 86 | **0.0331 / 63** |
| **pooled** | **0.1364 / 966** | **0.1328 / 942** |

### The one regression, kept deliberately — `boulanger-printemps-mvt1` +219

⚠️ **Its articulations are RIGHT and the metric charges for them anyway.** The
work carries no tuplets at all (0 detections, 0 `<time-modification>` on either
side), so fix 2 is not involved; the whole +219 is fix 3. And fix 3 reads it
almost perfectly:

    detected 269   attached 264   exported 263
    truth 271 articulations:  258 staccato + 13 tenuto
    pred  263 articulations:  254 staccato +  9 tenuto

263 of 271 marks, with the right kinds in the right proportions, on a work that
previously emitted zero. Its OMR-NED still rose, because **43 parts against 46
and 76% of its budget in whole-measure and whole-staff operations means its bars
do not pair** — and every correct symbol added to a bar that is already charged
delete-whole-bar-plus-insert-whole-bar makes that bar more expensive.

**Per-fix arithmetic, since the combined table hides this and should not.**
Isolating fix 3 by differencing the runs that bracket it:

| work | fix 3 alone |
|---|--:|
| `mozart-sym40-mvt1` | −57 |
| `brahms-sym4-mvt1` | −33 |
| `beethoven-sym3-mvt1` | −21 |
| `mahler-sym5-mvt1` (canonical) | −6 |
| `bruckner-sym5-mvt1` | −4 |
| `dvorak-sym9-mvt4` | −1 |
| `tchaikovsky-sym4/6`, `mozart-sym41-mvt1` | 0 |
| **subtotal, works that segment** | **−122** |
| `boulanger-printemps-mvt1` | **+219** |
| **net across the measured corpus** | **+97** |

⚠️ **So fix 3, taken alone and across every work measured, makes OMR-NED
WORSE by 97 edits.** That is the honest headline for it and it is not what the
combined −679 suggests. Fixes 1 and 2 carry the improvement; fix 3 is −122 on
eight works and +219 on one.

**Kept anyway, and the case is not the arithmetic.** The precedent is `b8ccc89`,
where writing chords bottom-up cost two edits and shipped because the export
then matched the convention its own truth is written in. Here the export
now carries 263 of Boulanger\'s 271 printed marks where it carried none, and the
same rule is 55/60, 81/110, 21/38, 9/10 and 6/6 on the works beside it. What
makes Boulanger expensive is that **43 of its 46 parts survive segmentation**,
so its bars are already charged whole and every correct symbol added to one
raises the charge. That is a fact about `entire measure` amplification on a
mis-segmented page, not about the marks.

⚠️ **The counter-argument deserves stating rather than dismissing:** +97 is not
2, and a reader who trusts OMR-NED as the arbiter should reject this fix. The
reason to keep it is that Boulanger is the one work in the corpus whose
STRUCTURE fails — 76% of its budget is whole-measure and whole-staff operations
before any of tonight\'s work — and the fixture docstring already warns that
such a render measures page segmentation rather than recognition. Fixing that
segmentation (handoff item 6) is what would let this row be read at all. **If a
later session decides otherwise, the fix is one commit (`0eb1271`) and reverts
cleanly.**

---

## 5. Two findings that are about the MEASUREMENT, not the pipeline

### `pitch_recall` understates a divisi part, badly

`mozart-sym40-mvt1` reports note recall **0.762** and puts **41.5% of its notes
in `order` bars** — 96 of them the Viola. Reading the two files side by side,
the Viola is not misread at all:

    TRUTH  m1: B-3(v1) B-3(v1) G4(v1) G4(v1) ... G3(v2) G3(v2)
    PRED   m1: G3/B-3(v1) G3/B-3(v1) G4(v1) G4(v1) ... B-3(v2) B-3(v2)

Every pitch is present on both sides. The truth separates the violas\' divisi
into two independent VOICES — an inner G3 held under an alternating line — while
the prediction reads the page, which prints G3 and B♭3 as one two-note chord on
one stem. The disagreement is about voice assignment, a semantic layer the
engraving does not carry, and the sequence aligner charges it as a quarter of
the part\'s notes.

This is the same caveat the Brahms Viola work recorded from the other side
("writing a double stop high-to-low is free" in OMR-NED, and not free in note
recall). It is worth carrying: **on a divisi part, `pitch_recall` is not a
recognition number.** Mozart 40\'s op list confirms it — the Viola\'s 160 edits
are 88 articulation, 40 flag/beam and 32 wrong note, none of them pitch.

### `dvorak-sym9-mvt4` is a 3-bar row and should be read as one

The one-page fit shrank its excerpt to 3 measures against everyone else\'s 6-8,
so its 0.4106 rests on a third of the symbols and is the noisiest ratio in the
table.

---

## 6. Recorded, not fixed

- **The margin-label lexicon is missing two English plurals.**
  `instruments.lookup("Oboes")` and `lookup("Cellos")` both return `None`,
  while `Flutes`, `Violins`, `Violas`, `Bassoons`, `Horns` and `Trumpets` all
  match. It is an inconsistency rather than a decision — `Oboe` has aliases
  `(oboe, oboen, oboi, hoboen, hautbois, ob)` and simply never got its plural.
  Batch 2 dropped a real `'Oboes'` for it. **Not fixed here on purpose:** a new
  label changes the part-staff join, which changes seeded clefs and keys, which
  changes the score — so it needs its own measured run and must not be folded
  into another fix\'s numbers.
- **Two labels lost their leading characters** — `'larinetti in B.'`
  (Clarinetti) and `'mpani in C-G'` (Timpani), on LilyPond pages whose text
  layer contains the names in full (`'Flauto.'`, `'Oboi.'` read cleanly on the
  same page). That is a reader/window fault, not a lexicon one, and the two
  should not be confused: adding `larinetti` as an alias would paper over it.
- **`tchaikovsky-sym6-mvt2` carries `shift:-4` on the Fagotti (2 bars) and
  Violoncello (1 bar)** — 11 notes. `shift:k` is the misfitted-staff-window /
  wrong-clef signature the Brahms Violin 1 work chased. Small here, and the
  only instance of it in the corpus.


---

## 7. What the next session should pick up

Ranked, with the evidence already gathered.

1. **`mozart-sym41-mvt1` is still the worst work at 0.3632**, and its residue is
   named: `wrong note` 886 of its 1051 edits, concentrated in the **Viola (156)**
   and the **two Oboes (~78 each)**. `exact` measures went 27.2% → 41.2% and its
   wrong durations 129 → **40**, of which the Viola holds 11. The dominant
   surviving ratio is **×2 on 18 notes — a beam level one too few**, which is
   `line_detection` territory, the same place the stem-cap fix lived.
2. **Six of its forty triplet groups are still read straight** (ratio 3/2 on 6
   notes). Those are groups where no digit was detected under EITHER class name.
   That is a genuine detection gap, unlike the 30 that were a label.
3. **`detached-legato` has no glyph of its own.** Mozart 40\'s truth has 14 of
   them and the page prints a staccato dot under a slur. Reading it needs the
   dot and the slur together; the detector cannot be blamed and neither can the
   truth. Worth a decision rather than a fix.
4. **The margin-label lexicon misses `Oboes` and `Cellos`** (section 6). Cheap,
   but it changes the part-staff join and therefore the score, so it needs its
   own measured run and must not be folded into another fix.
5. **`tchaikovsky-sym6-mvt2` carries `shift:-4` on the Fagotti and
   Violoncello** — 11 notes, the misfitted-window/wrong-clef signature, and the
   only instance in the corpus.
6. **`boulanger-printemps-mvt1` at 46 parts is a STRUCTURE failure**, 43 parts
   against 46 with 76% of its budget in whole-measure and whole-staff ops. It is
   the only work that exercises a2 paper. Nothing here touched it and nothing
   here should be read as evidence about it.
7. **`mahler-sym5-mvt4` never rendered** — `musicxml2ly` exits 1 on it. One
   line of diagnosis would add a 9-part late-romantic string texture to the
   corpus, which nothing else covers.

### Two standing warnings this round produced

- **A benchmark of three pages cannot falsify a story about one of them.**
  Mahler\'s "fifth triplet group carries no marker at any confidence" survived
  in CLAUDE.md and in the attribution report because nothing forced anyone to
  look again. It carries a `fingering3` at 0.72.
- **Read the edit count beside the ratio, every time.** Fix 2\'s first
  measurement showed Mozart 41\'s OMR-NED falling while its edits ROSE — and
  that was not dilution-as-noise, it was a real bug (the ratio applied twice)
  that the ratio alone would have reported as a success.
