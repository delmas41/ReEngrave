# "Almost no ties or slurs are converting" — the partition, and what is under the arcs

2026-09-11, Sean's Phase 2 observation 4. Litolff Beethoven 5 mvt 1, pdf pages
1-4, the committed staged record (`beethoven5-p1-p4.record.json`, md5
`d3620ba9cb70fc93f6b7ee91b6cbe40a`). One record, exported twice, so no detector
jitter enters any figure here.

⚠️ **EVERY NUMBER BELOW IS AN EXPORT-STAGE NUMBER.** The instrument replays a
SAVED record, so it is blind by construction to a GATHER or an ADJUDICATE
change — `readjudicate.py` is the instrument for the second and two full
re-gathers for the first. That blindness is why §5's detection finding is
stated as a *count of what the record holds*, never as a recall rate.

---

## 1. REACH FIRST, AND THE DENOMINATOR IS HAND-VERIFIED

Sean is right about the file and the size of it is worth stating exactly. The
`works.json` rows for `…-984073-p1..p4` carry hand-verified windows into the
reference encoding: **measures 1-112**.

| | truth (encoding, 18 parts) | exported |
|---|--:|--:|
| slurs (`<slur type="start">`) | **111** | **32** |
| tie links (`<tied type="start">`) | **300** | **80** |

⚠️ **A PAGE TRUTH IS NOT AN ENCODING TRUTH**, and the correction runs in our
favour twice, so it must be stated rather than quietly enjoyed: MusicXML writes
a `<slur>` at EACH END (222 elements → 111 curves), and the Litolff plate
**condenses 18 encoded parts onto 12 printed staves**, so the number of curves
the *page* prints is lower than 111 + 300. No recall rate is claimed from this
pair; what it establishes is the ORDER of the shortfall — we write roughly a
quarter to a third of what the music has — and that Sean's *"almost no"* is an
understatement of the right sign.

## 2. THE PARTITION, REPRODUCED ON THE POST-DEDUPE TREE

`arc_partition.py`. The arc-export session's partition is unchanged in shape by
the duplicate-detections repair that landed hours earlier:

```
arc rows on the record   779
placed in a cell         779        (dropped before placement: none)
merged groups            721        (58 arcs, 7.4%, are one half of a
                                     cross-barline pair — the recorded rate)
    slur binds_0  178   binds_1  69   binds_2+  76
    tie  binds_0  241   binds_1  62   binds_2+  95
REFUSED (bind fewer than two heads)  550  = 76.3%
```

**76.3%** reproduces CLAUDE.md's recorded 76% to the tenth. ⚠️ So the dedupe
repair did **not** reach the arcs, exactly as its own report said it did not.

⚠️⚠️ **THE DETECTOR IS NOT SHORT OF ARCS — IT IS LONG.** 721 merged groups
against an encoding truth of 411 curves across 18 parts condensed onto 12
staves. Whatever is wrong here, *"we do not detect enough arcs"* is not it, and
a session that started from that premise would have gone the wrong way.

## 3. FOUR STORIES KILLED BEFORE ANY CODE WAS WRITTEN

Each of these is the kind of aggregate that reads like a cause. None is.

| hypothesis | measurement | verdict |
|---|---|---|
| the refused arcs are weak ink | detector confidence, refused vs bound: med **0.522 vs 0.473** | **NO** — refused arcs are, if anything, the more confident |
| they are short junk fragments | arc width, refused-binding-0 vs bound: med **6.23 vs 6.40 staff spaces** | **NO** — they are full-length curves |
| they were placed in the wrong bar | x-overlap of every arc segment with the bar it was placed in | **NO** — 779 of 779 land `inside` |
| they are duplicate detections | 48 duplicate pairs in one cell at IoU ≥ 0.7, 19 of them cross-staff | **a real defect, and not the cause** — see §7 |

⚠️ Confidence is a PROXY for ink quality and cannot say an arc is false; it is
used here only to ask whether the two populations look like the same ink. They
do.

## 4. THE REFUSED ARCS, PARTITIONED BY WHAT IS MISSING

`probe/why_refused.py`. Four buckets, split because the repairs differ — the
`detected_and_unrepresented` / `decided_and_unwritten` distinction one family
further down:

| | before | after §6 |
|---|--:|--:|
| binds 2+ (written, or refused for ending in one chord) | 171 | **204** |
| refused: heads in the bar, **NOT UNDER** the arc | 376 | 345 |
| refused: **NOTHING WAS READ** in its bars | 108 | 108 |
| refused: heads under it, **HELD BACK by the exporter** | 66 | 64 |

⚠️⚠️ **THE BRIEF'S LEADING HYPOTHESIS IS THE SMALLEST BUCKET AND IT IS BOUNDED
AT 66.** The manager's most concrete lead was that `_place_notes` holds back
554 notes on these pages (`duration_narrowed` 339, `no_pitch` 215) and that
`_noteheads_under` cannot see them. That is TRUE — `cell.detections` is what
`_place_notes` survived — but it is worth **at most 66 of 550 refusals (12%)**,
because the held-back heads mostly are not under an arc anyway. Closing the
narrowed-duration and no-pitch gaps would be worth a great deal to the file;
it is not what is wrong with the arcs.

## 5. THE LARGEST SINGLE CAUSE IS A DETECTION GAP, AND HERE IS ITS INK

⚠️ **The crops are BUILD PRODUCTS and `benchmarks/**/crops/` is gitignored by
this repo's own convention** — `probe/crop_arc.py` regenerates every one of
them from the committed record and the edition PDF, deterministically, and the
per-arc coordinates are printed beside each file so a reader can re-cut one by
hand.

`crops/ZEROHEAD-p3s1st0c3.png` — Litolff p.3, system 1, staff 0, bar 3. The
print shows a slur over **six** perfectly legible noteheads. The record's
entire content for that bar is:

```
glyph/3/1/0/3/0  tie             0.83   <- the arc
glyph/3/1/0/3/1  restWhole       0.56   <- there is no whole rest in the bar
glyph/3/1/0/3/2  accidentalFlat  0.40
glyph/3/1/0/3/3  staff           0.37
glyph/3/1/0/3/4  ledgerLine      0.30
```

**Not one notehead.** `crops/ZEROHEAD-p4s0st0c1.png` is the same shape with two
notes. The arc is the most confident detection on the bar in both.

**108 of 550 refused groups (19.6%) are in bars where the detector produced no
notehead at all.** Nothing in the exporter can touch those, and no arc rule
should try: an arc with nothing to bind must stay refused, because one end
leaves an unpaired `<slur type="start">` and an INVALID file.

⚠️ **This is stated as a COUNT, not a recall rate.** The record holds 2,347
gathered noteheads against an encoding truth of 1,965 notes over 18 parts
condensed to 12 staves, so we over-produce noteheads globally while missing
them locally. A global recall number would average two populations that behave
differently — the shape this repo already records for the arc grammar.

## 6. WHAT WAS REPAIRED: AN ARC IS DRAWN TO A STEM, NOT TO A NOTEHEAD

`crops/REFUSED-slur-p2s1st0c10.png` and `-c12.png`, with
`crops/CONTEXT-p2-s1-st0-c10-wide.png` for the passage. These are **real
printed slurs**, over chords, binding nothing — and the geometry says why. On
`p2/s1/st0/c10` the bar's chord has its head centres at page x 1966-1972 and
the arc's ink begins at **1980**. `_noteheads_under` pads by
`_SLUR_ARC_PAD_NOTEHEADS` = 0.25 notehead widths ≈ 6 px. It misses by two.

⚠️⚠️ **THIS IS THE `_beam_levels` FAULT, ONE FAMILY OVER, AND THE REPAIR IS
THE SAME ONE.** A beam stroke *"runs from the FIRST stem it joins to the LAST,
and a stem stands at the SIDE of its notehead"*, so `_beam_levels` — which
tested the head's CENTRE — read bar sums wrong on perfect ink, with the
overshoot clustering at **0.35-0.47 notehead widths**. An arc over stemmed
notes is drawn from stem top to stem top for exactly the same reason.
Measured here (`probe/pad_gap.py`): the distance from an arc's edge to the
nearest head centre outside it has median **0.52 notehead widths** — the stem
offset and nothing else.

⚠️⚠️ **AND THE OBVIOUS FIX — WIDENING THE PAD — WAS MEASURED AND REFUSED.**
`_SLUR_ARC_PAD_NOTEHEADS` sits in an interval the engraved Brahms fixture left
EMPTY (*"54 of 75 within 0.19 notehead widths, and the next is at 0.32"*). On
this document the same distribution is a **smooth slope with no gap anywhere**:

```
 0.00  58 | 0.25 116 | 0.50 110 | 0.75  92 | 1.00  48 | 1.25 25 | 1.50 7 ...
```

A pad read off that is a number fitted to a wish. The stem is not a wider
tolerance — it is the position the arc is actually drawn to.

**SHIPPED, no flag**: `_noteheads_under` takes an optional `x_probes`
(`id(detection) -> extra page x`), and `staged.export._stem_probes` fills it
from `Q.STEM`.

* ⚠️ **`Q.STEM` was gathered and read by nothing on this path** — 1,920 rows on
  this record. The repo's most-recorded pattern, and the third time this exact
  quantity has been found unread.
* ⚠️ **ADDITIVE, never subtractive**, in the shape `_stem_joined` and the
  ledger ladder already have: a probe can only make a head REACHABLE, the
  span's own endpoints stay the notehead centres, and a page whose stems the CV
  never read behaves exactly as before.
* ⚠️ **The attachment rule is `_stem_joined`'s, IMPORTED** (`_boxes_overlap`) —
  measured, not chosen: 819 heads take exactly one stem and the nearest miss is
  94 px.
* ⚠️ **`Q.STEM` is CANONICAL and carries no page box** — the *gathered in a
  frame that cannot answer* fault this repo already records. The conversion
  uses **the head as its own ruler** (it carries both boxes), which needs no
  fit; a per-cell affine over the glyph rows gives the identical answer at
  residual **0.00 px** (`probe/stem_reach.py`).
* **No new constant.**

### MEASURED — one gather, exported twice (`arc_arm.py`)

| | OFF | ON |
|---|--:|--:|
| `<slur type="start">` | 32 | **40** |
| `<tied type="start">` | 80 | **91** |
| slur spans marked | 76 | 91 |
| tie spans / links marked | 94 | 111 |
| tie chains | 74 | 85 |
| notes / rests / dynamics / articulations / fermatas / accidentals | — | **all identical** |
| `arc_binds_fewer_than_two_notes` | 551 | **519** |

**Controls, each able to fail.**

* **the note sequence is unchanged** — every note of every part by (pitch,
  type, dots, duration, voice, staff, chord, rest): 2460 == 2460, identical.
* **identical with the arc FAMILY stripped.** ⚠️ The obvious textual control
  was WRONG and its failure is the evidence: stripping only `<slur>`/`<tied>`
  FAILED, on `<tie>` (MusicXML writes the sounding `<tie>` in the note AND the
  notational `<tied>` in `<notations>`, so one tie is TWO elements) and on the
  `<notations>` wrapper emptying. Rather than widen the strip until it passed —
  *widening a control while teaching it about a legitimate-sounding exception
  is how a control stops being one* — the control was made STRUCTURAL and the
  strip kept beside it with the whole family named.
* **the accounting balance stays an EQUALITY**, both arms.
* **the arc partition stays EXACT across the change**: written + not-written ==
  the merged-group count in BOTH arms (112 + 609 == 721, and 131 + 590 == 721).
  ⚠️ This is the control that catches the arc-export session's own defect —
  *a counter placed where the mark is SET measures the decision and reports it
  as the file* — arriving from the other side, on a change that moves 19 marks.
* **the status census stays a PARTITION with `unaccounted` empty** — 14
  families filed of 14, `balanced: true`, identical either side.
* **the tie same-pitch invariant** (`record.Checkable`'s own rule, needs no
  print): tie starts resolving onto a next note of the same pitch **27.5% →
  30.8%**. ⚠️ ONE-SIDED — an unresolved tie is certainly wrong, a resolved one
  may still be invented — and it is quoted here only to show the repair does
  not make the known tie-pairing defect worse. **It does not fix it**: 63 of 91
  tie starts still resolve onto nothing.
* **REACH is printed before any figure and the arm exits non-zero at zero**:
  1,159 notes on this record are reachable at a stem.

**Mutation battery: 8 arms, ALL RED**, including a positive control in the same
class (make every head reachable → the tests asserting a stem changes nothing
go red). Arms run against SNAPSHOT trees, never the working copy — *a battery
that rewrites the files it mutates in place is not isolated from anything else
running beside it*. A missing anchor is reported as `BAD ANCHOR`, never as a
pass. ⚠️ The frame arm is the one that needed a fixture built for it: at scale
1.0 the canonical and page spellings agree in every coordinate, so the test
fixture makes the page notehead TWICE the canonical width, and reading the
stem's canonical offset as a page offset then lands 12.5 px short and goes red.

## 7. REFUSED, WITH ITS MEASURED REACH

### The cross-barline reach — +19 groups, and it is a GUESS

The crops name a second failure on the very same arcs: the printed slur runs
from the chord at the end of bar N to the chord at the start of bar N+1, its
ink stops AT the barline, and its continuation fragment in bar N+1 is ~0 px
wide because that chord sits at the bar's very beginning. So
`_merge_arcs_across_barlines` has nothing to join to, the chain breaks, and the
arc can only ever bind heads in its own bars.

Modelled (`probe/two_repairs.py`), letting an edge-reaching arc with no
continuation look into the neighbouring bar:

```
merged groups 721      binding 2+ now 171
  + the STEM rule alone          199
  + the CROSS-BARLINE rule alone 184
  + BOTH                         218        <- SUPER-ADDITIVE
```

⚠️ **They are super-additive because each repair alone leaves the arc binding
ONE head, which is still refused** — the same shape the duration reader records
(*+15 and +13 separately, +66 together*). So the separate numbers understate
both, which is why they are reported together.

**It is refused, and the measurement is the reason.** The rule needs a window
into the next bar, and the distribution that window would sit on is *where a
bar puts its first note* — mode 2.0-2.5 staff spaces past the barline, over all
282 edge-reaching arcs. That is a fact about ENGRAVING, not about this arc: any
window wide enough to admit the note admits **every** next-bar first note, so
the rule reduces to *"an arc touching a barline lands on the first note of the
next bar"*. That is a tie-break among candidates the ink does not distinguish,
and it is the one thing this architecture forbids outside the proposed INFER
stage. **It is INFER-shaped work and is recorded here with its reach so a
session holding the print can adjudicate it.**

### Duplicate arc detections — a real defect, deliberately not repaired here

48 pairs of arcs are placed in ONE cell with IoU >= 0.7, **19 of them detected
on two different staves** — and several pairs disagree about their own kind
(`glyph/2/0/8/9/2` slur == `glyph/2/0/8/9/5` tie, IoU 0.995). `_place_arcs`
sends every arc to the cell its OWNER names, and where one printed curve is
detected on two staves BOTH detections name the same owner, so both are placed.
**That is precisely the shape `_place_notes` was repaired for on 2026-09-11
(`A.is_relocated_copy`), one family over**, and the dedupe report said in
writing that it did not reach the arcs.

It is not repaired here because it is **not the cause of Sean's observation**
and the rule that fixes it is not the rule this session measured: an arc has no
`A.is_relocated_copy` equivalent (its `arc_owner` domain is not the contested
population the way `glyph_owner`'s is), so the repair is a dedupe pass over
placed arcs, with its own reach to measure. Ranked in §9.

### Everything else that was NOT touched

* `OMR_ARC_RECLASS` is not re-opened. Its refusal is inherited.
* No OMR-NED figure is claimed. The metric is symmetric and **rewards emitting
  more symbols** — the legacy slur work's first cut LOWERED pooled OMR-NED
  while RAISING the edit count — and this change emits 19 more.
* No arc binding fewer than two noteheads is emitted. The refusal is correct.

## 8. WHAT IS NOT ESTABLISHED

* **Accuracy.** Not one of the 19 added arcs has been checked against the
  print. The tie same-pitch invariant improves, which is consistent with them
  being right and does not show it.
* **n = 1 document, 1 publisher, 4 pages.** Litolff `984073` is the *low-res
  bitonal* scan this repo already records as the pessimistic end of the corpus
  (49 flags / 35 dots against Breitkopf's 371 / 656). **Breitkopf Brahms 1 is
  the document to re-run every figure here on**, and the stem-offset median in
  particular: a print whose slurs are drawn over noteheads rather than over
  stems would show a different distribution and a different reach.
* **The engraved family is untouched by construction and NOT measured.**
  `x_probes` defaults to `None`, the legacy pass passes nothing, and a test
  asserts that at the seam by source — but no engraved arm was run.
* **The 345 arcs with heads in the bar and none under them** are explained for
  the cases the crops open and NOT accounted for as a population. The
  cross-barline configuration is the one named; how much of the 345 it is
  remains unmeasured, because separating it needs the print.

## 9. RANKED NEXT

1. **The noteheads under the arcs.** §5's bar detects a `restWhole` at 0.56 and
   a `ledgerLine` at 0.30 on a bar printing six noteheads. This is the ceiling
   on arcs, and it is a DETECTION question — the same wall the hairpins hit.
2. **The tie PAIRING**, already ranked by the chord-tie session and unmoved
   here: 63 of 91 written tie starts resolve onto no note of their own pitch.
3. **A dedupe pass over placed arcs** (§7), with its reach measured first.
4. **The cross-barline reach** (§7), once someone holds the print — or once
   INFER exists, which is where it belongs.

---

## Reproducing

`REC` = `library/_shared-records/beethoven5-p1-p4.record.json` (132 MB, not
committed; md5 `d3620ba9cb70fc93f6b7ee91b6cbe40a`). All with `PYTHONPATH=.`
from the repo root.

| script | what it answers |
|---|---|
| `arc_partition.py REC` | the partition, and each refused arc's would-have-been heads |
| `arc_residue.py REC` | duplicates, and whether a refused arc's bars hold ink |
| `probe/why_refused.py REC [--off]` | the four-bucket table of §4 |
| `probe/arc_widths.py REC` | width by binding count |
| `probe/arc_in_its_bar.py REC` | is the arc inside the bar it was placed in |
| `probe/arc_confidence.py REC` | confidence, bound vs refused |
| `probe/pad_gap.py REC` | the pad distribution, and why it may not move |
| `probe/stem_reach.py REC` | the stem rule's reach, with the affine residual control |
| `probe/two_repairs.py REC 1.0` | stems and cross-barline, apart and together |
| `probe/name_the_notes.py REC N` | names the notes under refused arcs |
| `probe/crop_arc.py REC PDF` | renders the ink, so a human can look |
| `probe/truth_arcs.py works.json MXL beethoven-sym5-mvt1-984073-p` | the §1 denominator |
| `arc_arm.py REC` | the A/B, with its four controls |
| `mutants.py` | the 8-arm battery |
