# A beam's y is not one number — Mozart 41's ×2 durations

**2026-09-02.** [FINDINGS.md](FINDINGS.md) closed with `mozart-sym41-mvt1` as the
worst surviving row at **0.3632 / 1051 edits**, `wrong note` 886 of them, and
named the residue: *"the dominant surviving ratio is ×2 on 18 notes — a beam
level one too few, which is `line_detection` territory, the same place the
stem-cap fix lived."*

The ratio was right and the address was wrong. The beams are detected, both
strokes of them, correctly placed and correctly counted. What throws one away is
in `rhythm.py`, in the arithmetic that decides which of them a stem is holding —
and it is the ninth time this repository has paid for the same shape: **the
signal is already there and something downstream discards it.**

    mozart-sym41-mvt1   0.3632 / 1051   ->   0.1541 / 449     -602 edits
    duration rate            0.868      ->     0.947
    wrong durations             40      ->        22
    the ×2 bucket                18      ->         0

### The probes, in the order they were needed

| script | answers |
|---|---|
| `probe_duration_ratios.py` (existing) | which ratio, which part, which bar |
| `probe_beam_levels.py` | what the shipped JSON says a cell's noteheads read |
| `probe_cv_beams.py` | what `detect_beams` found, component by component, with `_stacked_bar_count`'s per-column runs |
| `probe_beam_trace.py` | the counting path replayed per notehead — every beam that reached the decision and why it was kept |
| `probe_sloped_beam_reach.py` | the pair-level distribution: both distances, the bias, the flips |
| `probe_beam_level_delta.py` | the stem-level distribution: which stems change count, and whether the change extends a stack or invents a beam |

Logs and the raw CSV are in `out/`.

---

## 1. The mechanism

`rhythm._beams_attached_to_stem` counts the beam levels a stem holds. It takes
every beam whose x-range overlaps the stem, decides which END of the stem each
one belongs to, and clusters what it finds. The end test is a distance against
`end_window`, which is `4 × beam_y_cluster_tol` — 1.4 staff spaces.

That distance was measured **to the beam box's CENTRE.**

A beam detection is not a line. `line_detection.detect_beams` emits one
`LineDetection` per stacked bar, sliced out of a connected component's bounding
box — and a component that bounds a **sloped** stroke spans the stroke's entire
vertical excursion. The ink is at the band's top where the group ends high and
at its bottom where it ends low. The centre is a y the stroke passes through
only in the MIDDLE of the group.

So the centre is the right y for exactly one stem in a beamed group and wrong,
by up to half the band height, for the ones at either end — **in the direction
that pushes the outermost stem out of the window.** A group of three loses its
outer note; a group of two loses one of two.

⚠️ **This is a bias, not a tolerance.** It scales with the slope, which scales
with the interval the figure spans, so it is largest exactly where the music is
most active — and it is invisible in the middle of every group, which is why
the fault reads as a scatter of single wrong notes rather than as a broken part.

### The same correction already exists one module earlier

`line_detection._attached_stem_count` decides whether a stem ends at a component
at all, and it makes the opposite choice, with the reason in its docstring:

> The comparison is made against the component's ink IN THE STEM'S OWN COLUMN
> rather than against its bounding box. A sloped beam's box reaches far above
> and below the bar itself, so **box edges put the far stem out of range and a
> sloped double beam lost its lower bar.**

That is this fault exactly, written down, fixed for the *detection* of a beam
and not for the *count* that becomes a duration. `_stacked_bar_count` right
beside it carries the third instance of the same lesson (it sampled the bounding
box instead of the component's own label mask, and a sloped bar's box reaches
over its neighbours).

---

## 2. The worked example

**Mozart 41, Oboe I (staff 1), measure 0** — a rising triplet of sixteenths,
`G4 A4 B♭4`, printed twice in the bar. Canonical coordinates, staff spacing
65.2 px, so `beam_y_cluster_tol` = 22.8 px and `end_window` = **91.3 px**.

The CV detector reads the stack correctly — two strokes, not one:

    band 1   x 1062..1329   y 163..207    (h 44 = 0.67 sp)
    band 2   x 1060..1329   y 217..264    (h 47 = 0.72 sp)
    centres  185 and 240 — 55 px apart, against a 22.8 px tolerance: two levels

Three stems hang from it, and because the figure rises their tops climb:

| stem x | top y | d to band 1 | d to band 2 | d to CENTRE 1 | d to CENTRE 2 |
|--:|--:|--:|--:|--:|--:|
| 1061 | 192 | 0 | 25 | 7 | 48 |
| 1189 | 170 | 0 | 47 | 15 | 70 |
| **1318** | **146** | **17** | **71** | **39** | **94** |

Against the bands, all six pairs are inside the 91.3 px window and all three
notes read two levels. Against the centres, the last one is **94 px** — three
pixels past the fence — so the third note alone reads ONE level.

    NH x=1238  lvl=1  dur=0.333333  eighth   tuplet 3:2      <- exported
    NH x=1238  lvl=2  dur=0.166667  sixteenth tuplet 3:2     <- printed

A triplet sixteenth exported as a triplet eighth: ratio **×2**, the bucket
FINDINGS named. The tuplet ratio is applied correctly on both sides — this is
purely the beam level.

**It is the same figure across the wind section**, which is why one bar's worth
of geometry is worth 602 edits: staves 0, 1, 2 and 4 all flip the same stem at
x=1318 in m0, and staves 0-4, 12 and 13 all flip x=525 and x=1572 in m4.

### How the trace was obtained

`probe_beam_trace.py` rebuilds one cell from the PDF and replays the counting
path against the shipped `.omr.json`'s detections. ⚠️ **It has to call
`remove_staff_lines` to reproduce the real run, and the first draft did not** —
without it `image_no_staff` is `None`, `detect_beams` runs on raw ink, and all
five staff lines come back as full-width beams with 4-8 stem ends crossing them.
That produced a confident, complete and entirely wrong attribution (every stem
reading 3 levels off staff-line residue) before the replay was checked against
the JSON it was supposed to explain. The check that caught it was cheap: the
replay must reproduce the shipped `beam_levels` exactly, and it did not.

*(A real observation survives that mistake and is recorded in §6: CV beams skip
the `_spans_the_whole_cell` filter that YOLO beams get.)*

---

## 3. The distribution

Measured over **12 works** — the nine of this corpus plus the canonical three —
one page each, every cell, every (stem end, beam band) pair the x-overlap filter
admits, on the **merged** beam list the counter actually receives: **2586 pairs
over 1239 stems** (`probe_sloped_beam_reach.py`, `probe_beam_level_delta.py`;
raw rows in `out/sloped_beam_reach.csv`).

### The band height, which the bias is half of

    0.00 sp    18
    0.25 sp   130  ######
    0.50 sp  1080  ######################################################
    0.75 sp   896  ############################################
    1.00 sp   292  ##############
    1.25 sp   124  ######
    ----------------  the CV detector's own ceiling is 2.5 sp
    2.25 sp    14
    2.75 sp    16
    3.00 sp    16

A level beam bar is ~0.5 staff spaces; everything above that is slope, up to
about 1.25 — against a window of 1.4 spaces. **The 46 pairs above 2.25 are a
different animal and §6 takes them up:** `detect_beams` caps a CV component at
2.5 spaces, so anything taller is a YOLO box, which bounds a whole STACK rather
than one stroke.

### Where the two rules disagree, in units of the window itself

Normalised by `end_window`, because staff spacing varies threefold across these
works and a pixel figure would mix scales:

| | n | min | p25 | med | p75 | max |
|---|--:|--:|--:|--:|--:|--:|
| `d_centre`, admitted by both | 1128 | 0.00 | 0.16 | 0.19 | 0.41 | 1.00 |
| **`d_centre`, pairs that FLIP** | **49** | **1.01** | **1.03** | **1.06** | **1.17** | 1.96 |
| — of those, on a CV band | 40 | 1.01 | 1.03 | **1.05** | 1.16 | **1.29** |
| `d_box`, admitted by both | 1128 | 0.00 | 0.00 | 0.00 | 0.13 | 0.86 |
| **`d_box`, pairs that FLIP** | **49** | 0.01 | 0.72 | **0.78** | 0.86 | 1.00 |

**On a CV band — the case this fix is about — every flipped pair sits between
1.01 and 1.29 windows on the old measure**: piled against the fence, not
scattered beyond it. A population that genuinely did not belong would spread
across the whole range; one whose median is 1.05 windows out is a population the
fence is cutting through because the quantity being measured is biased. The bias
itself is 0.23-0.52 staff spaces there, half a band height, as it must be by
construction.

The 1.96 outlier in the full row is a YOLO band, and every pair past 1.29 is —
which is the whole of §6's second item.

### The unit that decides the duration is the STEM, not the pair

A pair that flips inside a cluster the stem already had changes nothing. Per
stem, both rules replayed over all 1239:

| transition | stems | what it is |
|---|--:|---|
| 1 → 2 | 21 | **extends a stack** |
| 2 → 3 | 5 | **extends a stack** |
| 0 → 1 | 5 | invents a first beam |
| | **31 of 1239** | 2.5% of stems change |

**26 of 31 extend a stack the stem already had** — the outermost note of a
beamed group regaining the stroke the rest of the group is already holding,
which is the fault under investigation and nothing else. The change is also a
**strict widening**: no pair admitted today is ever lost (asserted in the probe),
and no stem's count ever falls.

⚠️ **The first version of this probe was wrong, and the eval is what caught
it.** It fed `_beams_attached_to_stem` the CV beam list alone, and
`resolve_rhythms_for_cell` does not — it keeps a YOLO beam wherever no CV beam
overlaps its x-range, then dedupes. The CV-only probe reported **zero** changed
stems on `brahms-sym4-mvt1` while the end-to-end run moved that work by 2 edits,
and that contradiction is the only reason the omission was found. Corrected, the
probe finds brahms-sym4's single changed stem and predicts every work's eval
outcome exactly (below). *A replay is only evidence to the extent it replays the
whole path.*

### The stem count predicts the eval, work by work

| work | stems changed | edits moved |
|---|--:|--:|
| `mozart-sym41-mvt1` | 19 | **−602** |
| `boulanger-printemps-mvt1` | 7 | +7 |
| `mozart-sym40-mvt1` | 4 (all inventions) | 0 |
| `brahms-sym4-mvt1` | 1 (an invention) | +2 |
| `beethoven-sym3-mvt1`, `bruckner-sym5-mvt1`, `dvorak-sym9-mvt4`, `tchaikovsky-sym4-mvt2`, `tchaikovsky-sym6-mvt2` | **0** | **0** |
| **`beethoven-sym5-mvt1`, `brahms-sym1-mvt1`, `mahler-sym5-mvt1`** (canonical) | **0** | **0** |

**Every work with zero changed stems moves zero edits, and every work that moves
has stems that changed.** That correspondence is the strongest form this
evidence takes: the mechanism predicts, per work, both whether the score moves
and — for the two regressions — that it moves by a couple of edits rather than a
couple of hundred.

The canonical three are unchanged **by construction, not by comparison** — a
level beam's band is a bar thick, so its centre and its edges are within a few
pixels of each other and both rules agree. The measured runs in §5 confirm it,
but the reason they cannot move is that no stem in them has a band tall enough
for the bias to reach the fence.

---

## 4. What was refused

### Widening `end_window` instead — measured, and strictly worse

The obvious alternative is to leave the centre measurement alone and open the
window. It was priced over the same 2586 pairs:

| rule | pairs admitted | added vs today |
|---|--:|--:|
| today (`d_centre` ≤ 1.00 × window) | 1128 | — |
| **the band rule** | **1177** | **+49** |
| `d_centre` ≤ 1.10 × | 1157 | +29 |
| `d_centre` ≤ 1.20 × | 1180 | +52 |
| `d_centre` ≤ **1.30 ×** | 1205 | **+77** |
| `d_centre` ≤ 1.50 × | 1221 | +93 |
| `d_centre` ≤ 2.00 × | 1410 | +282 |

The CV-band flips run out to 1.29 windows, so a widened window would have to
reach 1.30× to recover the same stems — and there it admits **77 pairs, 28 more
than the band rule**, granted indiscriminately to every beam including the level
ones where there was never a bias to correct. It is also a number with nothing
under it: 1.2 and 1.4 are equally defensible and differ by 25 pairs.

The band rule needs **no new constant at all**. `end_window` and
`beam_y_cluster_tol` are untouched. It widens the reach by exactly the vertical
distance the slope introduced, band by band, and a level beam is unaffected.

### Interpolating the stroke's y at the stem's own x — refused as unbuildable here

The exact answer is where the ink is in the stem's column, which is what
`_attached_stem_count` reads. `rhythm.py` does not have the image: it receives
`LineDetection` boxes, and a box does not record which way its stroke slopes.
Recovering that would mean plumbing the label mask through `detect_beams`'
output — a much larger change for a correction the band already bounds, since
the stroke cannot be outside its own band at any x.

### Changing `line_detection.py` at all — not needed, and it would have been wrong

The handoff pointed at `line_detection`, on the reasonable ground that the
stem-cap fix lived there. **The detector is not at fault here.** On the worked
example it reads two strokes, at the right heights, with the right widths, and
`_stacked_bar_count` returns 2 for the component. Nothing in this fix touches
`line_detection.py`, and `tools/omr/training/line_detection_eval.py` does not
import `rhythm` — so the LilyPond stem/beam ground truth is unchanged **by
construction**, which is also the reason it is not evidence for this change
(see §7).

---

## 5. Measured

### `mozart-sym41-mvt1`, the target

| | before | after |
|---|--:|--:|
| OMR-NED | 0.3632 | **0.1541** |
| edits | 1051 | **449** |
| duration rate | 0.868 | **0.947** |
| note recall | 1.000 | 0.991 |
| `wrong note` | 886 | **250** |
| `wrong flag/beam` | — | 127 |

⚠️ **Note recall FALLS, 1.000 → 0.991, while the score improves by 602 edits.**
Two of 228 notes stop pairing. `orchestral_eval` aligns notes by index within a
bar, so changing a duration changes what pairs with what; this is the same class
of caveat FINDINGS recorded for `pitch_recall` on a divisi part. The duration
rate, which is computed on the matched notes, is the number that moved: 0.868 →
0.947.

Wrong durations fall 40 → 22 and the ×2 bucket is emptied:

| ratio | before | after | what it is |
|---|--:|--:|---|
| **×2** | **18** | **0** | beam level one too few — this fix |
| 3/2 | 6 | 7 | triplet read straight (handoff item 2 — a real detection gap) |
| ×6 | 6 | 6 | untouched |
| 1/6 | 4 | 4 | untouched |
| 1/2 | 3 | 3 | untouched |
| 1/4 | 2 | 2 | untouched |
| ×3 | 1 | 0 | |
| **total wrong** | **40** | **22** | of 226 paired notes |

⚠️ **`wrong flag/beam` is 127 of the surviving 449 and is NOT this fault
returning.** The ×2 bucket is empty; what remains under that musicdiff heading
is beam *grouping* — where a beam starts and stops — which is a different
question from how many strokes a note holds.

### The whole new corpus, both arms on ONE base

⚠️ **HEAD moved twice while this was measured** — five commits from other
workstreams landed, two of them touching `transcribe.py` and `export.py`, which
are in the path every one of these runs takes. A before/after table across a
moving base conflates other people's work with your own, so the baseline was
**re-measured on the same tree** rather than quoted from FINDINGS: `rhythm.py`
reverted to HEAD, the nine works run again, the fix restored.

It was worth doing and it came back clean — **the re-measured baseline
reproduces FINDINGS' after-table for all nine works to the edit**, so those five
commits did not touch this corpus and the deltas below are entirely this fix.

The after-arm was then run a second time, on a tree that had moved again
(`a90e99e` → `b127a5c`), and reproduced **every work to the edit** along with the
canonical 0.1328 / 942. Baseline arm on `ad5c474`; after arm confirmed on
`ad5c474` and again at `b127a5c`.

| work | before | after | delta | dur before → after |
|---|--:|--:|--:|--:|
| **`mozart-sym41-mvt1`** | 0.3632 / 1051 | **0.1541 / 449** | **−602** | 0.868 → **0.947** |
| `mozart-sym40-mvt1` | 0.1772 / 273 | 0.1772 / 273 | 0 | 0.952 → 0.952 |
| `beethoven-sym3-mvt1` | 0.1405 / 231 | 0.1405 / 231 | 0 | 1.000 → 1.000 |
| `bruckner-sym5-mvt1` | 0.1042 / 205 | 0.1042 / 205 | 0 | 1.000 → 1.000 |
| `dvorak-sym9-mvt4` | 0.3380 / 239 | 0.3380 / 239 | 0 | 1.000 → 1.000 |
| `tchaikovsky-sym4-mvt2` | 0.0571 / 88 | 0.0571 / 88 | 0 | 1.000 → 1.000 |
| `tchaikovsky-sym6-mvt2` | 0.1958 / 279 | 0.1958 / 279 | 0 | 0.985 → 0.985 |
| `brahms-sym4-mvt1` | 0.2296 / 427 | 0.2304 / 429 | **+2** | 0.933 → 0.933 |
| `boulanger-printemps-mvt1` | 0.7017 / 5374 | 0.7020 / 5381 | **+7** | 0.880 → 0.881 |
| **pooled (8, without Boulanger)** | **0.2057 / 2793** | **0.1613 / 2193** | **−600** | |
| pooled (all 9) | 0.3846 / 8167 | 0.3562 / 7574 | −593 | |

**Six of the nine works are identical to the edit**, and the one that moves is
the one the fault was diagnosed in. Mozart 41 stops being the corpus's worst row
by a wide margin — it was 0.3632 against a next-worst of 0.3380, and it is now
0.1541, fourth-best of the nine.

⚠️ **`mozart-sym40-mvt1` is 0 edits and 0.952 duration rate on BOTH arms** —
so the four `0 → 1` stems of §5's cost paragraph, the only way this change can
do harm, cost **nothing measurable**. That is not the same as being right, and
they are still reported as wrong; it is the price being zero on this corpus.

The two small regressions are +2 and +7. `boulanger-printemps-mvt1` is the work
whose STRUCTURE fails (43 parts against 46, 76% of its budget in whole-measure
and whole-staff operations before anything here), where FINDINGS already
established that every symbol added to an unpaired bar raises its charge; +7 on
5374 there is not a reading. `brahms-sym4-mvt1`'s +2 is two edits on 427 with
its duration rate unmoved at 0.933, and it is named rather than explained away.

### The canonical three — unchanged, edit for edit

Measured on the same tree, through this benchmark's own `--work-dir` so a
parallel canonical run could not collide:

| work | before | after | |
|---|--:|--:|---|
| `beethoven-sym5-mvt1` | 0.1649 / 205 | 0.1649 / 205 | identical |
| `brahms-sym1-mvt1` | 0.1707 / 674 | 0.1707 / 674 | identical |
| `mahler-sym5-mvt1` | 0.0331 / 63 | 0.0331 / 63 | identical |
| **pooled** | **0.1328 / 942** | **0.1328 / 942** | identical |

`accuracy_record --check` still agrees with CLAUDE.md; the recorded figure is
untouched and was not re-recorded.

### The cost, named — 5 stems, worth 9 edits

The `0 -> 1` transitions in §3 are the whole cost of this change, and they are
two places.

Four of them are one cell: **`mozart-sym40-mvt1` staff 8, measure 2**, stems at
x 125, 293, 820 and 988, every one of them y 799 h 212 at spacing 100. The cell
holds four heavily sloped single beams (fill 0.31-0.38 — two thirds of each box
is empty), two above and two below, and the two below run y 1113-1220. Those
four stems END at 1011, which is **104 px — 1.04 staff spaces — above the nearer
band's top edge**, inside a window of 140. Under the old rule the band's centre
at 1167 was 156 px away and they were refused. **They cost 0 edits**: Mozart 40
scores 0.1772 / 273 at a duration rate of 0.952 on both arms.

The fifth is **`brahms-sym4-mvt1` staff 18, measure 3**, stem x 937 y 123
h 291 at spacing 100 — one stem, and it is that work's whole +2.

A stem that stops a full staff space short of a beam is not holding that beam,
so all five are wrong. They are reported rather than tuned away: bounding them
would need a second constant stacked on `end_window`, and the corpus offers no
gap to put one in — five cases is not a distribution. The honest statement is
**26 of 31 changed stems are right and 5 are wrong, and the trade is −602 edits
against +9.**

---

## 6. Recorded, not fixed

### A YOLO band is a STACK, so half of it is not a slope correction — and that is exactly where both regressions live

The justification for measuring to the band is that **a stroke sweeps its own
band**. That is true of a CV band, which `detect_beams` emits one per stacked
bar. It is **not** true of a YOLO beam box, and the repository already says so,
in the merge comment a few lines above the function this fix changes:

> A YOLO beam box does not bound one stroke, it bounds the whole stack, so its
> centre lands in the GAP between two levels.

For such a box the height is not slope, it is levels — so widening the reach by
half of it grants a stem far more room than any slope justifies. The measurement
separates the two populations cleanly:

| | flips | max `d_centre` / window |
|---|--:|--:|
| flips on a **CV** band (`≤ 2.5 sp`) | 40 | **1.29** |
| flips on a **YOLO** band (`> 2.5 sp`) | 9 | **1.96** |

`detect_beams` caps a CV component at `max_height_lines = 2.5`, so the split is
exact rather than inferred. And the 9 YOLO-band flips are **all in
`brahms-sym4-mvt1`** — the work that carries one of the two regressions, its
single invented stem and its whole +2.

**Not fixed here, deliberately.** The evidence is 9 pairs in one work out of
twelve, and this repository's own standing rule is that a threshold seen on one
edition is not a threshold. It is also not free to implement: `rhythm.py`
receives CV and YOLO beams as one list of quack-compatible objects and would
have to start caring which detector produced each, and `confidence` (1.0 for CV
by convention) is too weak a signal to hang that on. **The right shape is
probably for `detect_beams` and the YOLO path to say what a band MEANS — one
stroke or a stack — rather than for the consumer to guess from its height.**

The prize is small and known: it would take `brahms-sym4-mvt1` from +2 to 0 and
leave Mozart 41's −602 untouched, since all 26 of its flips are CV bands.

### A CV beam is not checked for spanning the whole cell; a YOLO beam is

`resolve_rhythms_for_cell` filters YOLO beams through `_spans_the_whole_cell`
(`YOLO_BEAM_MAX_CELL_FRACTION` = 0.6) and then adds the CV list **unfiltered**:

```python
elif cat == "structural" and cls == "beam":
    if not _spans_the_whole_cell(d, cell):      # YOLO only
        beams.append(d)
...
beams = list(cv_beams) + [y for y in beams if not _overlaps_any_in_x(y, cv_beams)]
```

There is no stated reason for the asymmetry, and it is what turns a failure of
staff-line removal into wrong DURATIONS rather than merely fewer beams. Seen
directly while building `probe_beam_trace.py`: with `image_no_staff` absent,
`detect_beams` returns all five staff lines as full-width components — each one
crossed by 4-8 stem ends, so `_attached_stem_count`'s quorum passes — and every
stem in the cell then counts three "levels" off staff-line residue spaced one
staff space apart, well outside the 0.35-space clustering tolerance.

**Not a live fault on this corpus** (removal works on all twelve engraved
pages), which is exactly why it should not be fixed on this corpus: the works
that would exercise it are scans, and a filter added here without one measuring
it would be a guess. It belongs with the scan row.

### `_beam_levels_for_notehead` has the same shape and was deliberately left alone

The no-stem fallback measures `abs(b_y_center - nh_y_center)` too. It is far
less exposed — its gate is `max_stem_distance` at **5.5** staff spaces, against
a bias of at most 0.6, and its `end_window` step compares band centres to
another band centre, where a shared slope largely cancels. Changing it would
alter cells the fault does not reach, on no evidence. Left as is on purpose.

### Two works produce no (stem end, beam band) pairs at all

`beethoven-sym3-mvt1` and `dvorak-sym9-mvt4` contribute **zero** pairs over 152
and 54 cells. Both post a duration rate of 1.000, so this is very likely correct
— their excerpts are chordal and unbeamed — but it means neither work can say
anything about beams, and neither should be quoted as evidence that a beam
change is safe.

---

## 7. ⚠️ The green ground truth that is not evidence here

`benchmarks/omr-phase4-lines` — the LilyPond stem and beam ground truth — is
unchanged by this fix, and that fact carries **no information about it**.
`tools/omr/training/line_detection_eval.py` imports `preprocessing`,
`staff_detector`, `measure_extractor`, `staff_line_removal` and
`line_detection`, and **not `rhythm`**. It measures what `detect_beams` emits;
this fix changes what a later module does with that output. It is unchanged by
construction, and the run confirms the expected numbers (summed |error| 8 on the
beam table, 15 on the stem table, both as inherited).

This is the repository's standing warning arriving for the third time — *"a
green ground truth is evidence about its own coverage, not about your change"* —
and the discipline it asks for is the question asked before the run: **does this
harness contain a case where what I changed would matter?** Here the answer is
no, and it is no for a structural reason rather than a corpus one.

The harness that CAN speak to it is the per-stem replay in §3, which is a
distribution over 1239 real stems on 12 real pages, and the pinned unit tests
built from the measured geometry of the worked example
(`TestBeamsAttachedToStem` in `tools/omr/tests/test_rhythm.py`).

---

## 8. What the next session should pick up

Ranked, with the evidence already gathered. Items 1 and 2 are new here; the rest
of FINDINGS' list is unchanged and still stands.

1. **A YOLO band should not be read as a swept stroke** (§6). All 9 flips on a
   YOLO band are in `brahms-sym4-mvt1` and they are its whole +2. The clean fix
   is for the beam list to carry what a band MEANS — one stroke or a stack —
   rather than for `rhythm.py` to infer it from height. Worth doing when a
   second work exercises it; do not tune it on brahms-sym4 alone.
2. **`mozart-sym41-mvt1`'s residue is now `wrong note` 250 and `wrong flag/beam`
   127 of 449.** The ×2 bucket is gone; 22 wrong durations remain, of which 7 are
   FINDINGS' item 2 (triplet groups carrying no digit under EITHER class name — a
   genuine detection gap) and 6 are a ratio of ×6 that nothing has attributed
   yet. `probe_duration_ratios.py --detail` names the bars.
3. **`boulanger-printemps-mvt1` is still a STRUCTURE failure** — 43 parts against
   46 — and until that is fixed its row cannot be read as recognition, in either
   direction. Unchanged from FINDINGS item 6.
4. **CV beams skip `_spans_the_whole_cell`** (§6). Latent on engraved pages,
   live on any page where staff-line removal fails. Belongs with the scan row.
5. FINDINGS items 3, 4, 5 and 7 (detached-legato, the `Oboes`/`Cellos` lexicon
   gap, tchaikovsky-6's `shift:-4`, mahler-sym5-mvt4's `musicxml2ly` failure)
   are untouched by this work.

### The standing warning this round produced

**A replay is only evidence to the extent that it replays the whole path.** The
per-stem probe was built against the CV beam list because that is where the
worked example lived, and `resolve_rhythms_for_cell` merges YOLO beams into it.
The probe then reported zero changed stems on a work that moved by two edits —
and the only reason that was caught is that the end-to-end number was measured
beside it. A probe agreeing with your hypothesis is not the check; a probe
disagreeing with the end-to-end run is.
