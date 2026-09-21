# Articulations & ornaments — one section per symbol

**2026-09-20.** Sean's five questions, per SYMBOL, for the family the detector
files under one category and the pipeline splits into three.

Companion reading, cited rather than repeated: Sean's own confusable table
[`docs/position-grammar-confusables-2026-09-04.md`](../position-grammar-confusables-2026-09-04.md)
§2 (DOT, WEDGE, HORIZONTAL STROKE are all this family); the convention registry
[`docs/engraving-conventions.md`](../engraving-conventions.md) entries
`C50 / C51 / C52 / C55 / C87 / L59 / L60`; and the per-family position work,
[`benchmarks/omr-family-positions-2026-09/FINDINGS.md`](../../benchmarks/omr-family-positions-2026-09/FINDINGS.md)
with `tools/omr/staged/positions.py` and `tools/omr/staged/capture.py`.

---

## The three facts that govern the whole family

**1. The detector's CATEGORY is useless here and the router knows it.** All ten
`artic*` classes, both `fermata*`, all four `ornament*`, all five `tremolo*`,
`arpeggiato`, `caesura`, `stringsUpBow`/`stringsDownBow` and
`keyboardPedalPed`/`keyboardPedalUp` carry category `ornament`
(`tools/omr/yolo_detector.py:75-90`, `:144-145`). Everything in this dossier is
routed by CLASS NAME instead (`tools/omr/staged/gather.py:735-752`,
`:845-913`). MEASURED HERE: 26 of 51 fermata carriers are RESTS on Litolff p1-3
(`benchmarks/omr-staged-fermata-2026-09/out/litolff-p1p3.txt`), which the
articulation rule structurally cannot reach — so a category-keyed router would
have lost half of them.

**2. There are exactly three quantities and three decisions, and nothing else
in the pipeline reads any of them.** `grep -rn 'Q.ARTICULATION_OWNER\|Q.FERMATA_OWNER\|Q.ORNAMENT_OWNER' tools/omr/staged/`
returns hits in `adjudicate.py`, `adjudicators/ownership.py`, `export.py`,
`gather.py`, `capture.py`, `positions.py`, `reach.py`, `record.py` and nowhere
else. `consequences.py` and `infer.py` between them read fourteen quantities
and **not one of them is from this family**. MEASURED HERE (grep of the tree).

**3. Six classes in this family have NO quantity, NO decision and NO export.**
`arpeggiato`, `caesura`, `stringsUpBow`, `stringsDownBow`, `keyboardPedalPed`,
`keyboardPedalUp`. They are not excused either — `export.FAMILIES`
(`tools/omr/staged/export.py:2933-2956`) does not claim them and
`NOT_NOTATION` (`:2965-2985`) does not excuse them, so `_unclaimed` (`:3052`)
reports them by name. On Litolff Beethoven 5 pp.1-4 that reads
`{"arpeggiato": 377, "stringsDownBow": 1}`
(`benchmarks/omr-cleanup-count-2026-09/out/coverage-p1-p4-2026-09-17.json`).
MEASURED HERE.

### Where the numbers in this file come from

| source | what it is | n |
|---|---|--:|
| `benchmarks/omr-cleanup-count-2026-09/out/coverage-p1-p4-2026-09-17.json` | the staged pipeline's own coverage report, Litolff Beethoven 5 mvt 1, pdf pp.1-4 | 12 parts, 1,183 measures |
| `benchmarks/omr-cleanup-count-2026-09/out/beethoven5-mvt1-p1-p4-2026-09-17.musicxml` | the file that run produced | same |
| `benchmarks/omr-staged-fermata-2026-09/out/litolff-p1p3.txt` | the fermata arm, Litolff pp.1-3 | 63 marks |
| `benchmarks/omr-corpus-widening-2026-09/FINDINGS.md` §3, FIX 3 | the articulation sweep, 8 engraved works | 218 marks |
| `benchmarks/omr-export-gaps-2026-09/FINDINGS-2026-09-08-ornaments-and-the-derived-check.md` | the ornament census over every committed artifact | 7,090 files |
| `benchmarks/omr-family-positions-2026-09/FINDINGS.md` §5 | reach on two publishers | — |
| **PROBE (this dossier)** | `benchmarks/omr-labeling-hollow2-2026-09-breitkopf-brahms1/transcription.json` — a COMMITTED transcription, read only | 10,523 detections, 83 staves, Brahms 1 / Breitkopf pp.1-3 |

**A probe WAS used and here is exactly what it did.** It read that one
committed transcription JSON and, for each class, took the median box width,
height and confidence, divided by each staff's own measured `line_spacing_px`
(median 27.5 px over 83 staves), and compared the results against Bravura's
`glyphBBoxes` (`tools/omr/annotate/static/bravura/bravura_metadata.json`). No
detector ran, no page was rendered, nothing was written. ⚠️ **That file was
transcribed with `deepscoresv2-yolov8l-imgsz2048-ft-30ep.pt`** — the
engraved-side routing weights, not the scan production graft — and its
detections are POST `_dedupe_cross_staff_detections` (1,343 removed). So it
describes an older checkpoint on a scan.

⚠️ **And the probe measures the detector's own boxes for the detector's own
classes.** It says how big a box the model draws once it has already chosen a
name; it is not a test of whether the ink is separable. That is the
breakthrough document's point arriving in a measurement of my own
([`docs/breakthrough-2026-09-18-the-unit-of-enquiry.md`](../breakthrough-2026-09-18-the-unit-of-enquiry.md)
§3: *measuring the subject cannot test the subject*).

### The measured shape table — everything below refers back to this

Left half: this dossier's probe, in staff spaces. Right half: Bravura.

| class | probe w × h (sp) | probe conf med | n | Bravura w × h (sp) |
|---|---|--:|--:|---|
| `articStaccatoAbove` | 0.36 × 0.36 | **0.684** | 69 | 0.336 × 0.336 |
| `articStaccatoBelow` | 0.36 × 0.36 | **0.725** | 40 | 0.336 × 0.336 |
| `articStaccatissimoAbove` | 0.44 × 0.65 | 0.475 | 7 | 0.396 × **1.180** |
| `articAccentAbove` | 1.67 × 0.36 | 0.547 | 7 | 1.356 × 0.976 |
| `articTenutoAbove` | 1.81 × 0.30 | **0.316** | 2 | 1.356 × 0.192 |
| `articTenutoBelow` | 1.96 × 0.33 | **0.394** | 5 | 1.356 × 0.192 |
| `articMarcatoAbove` | — (0 fired) | — | 0 | 0.944 × 1.016 |
| `fermataAbove` | 1.92 × 0.90 | 0.508 | 2 | 2.408 × 1.328 |
| `ornamentTrill` | 1.04 × 1.54 | 0.448 | 8 | 2.084 × 1.600 |
| `caesura` | 0.45 × 0.56 | 0.575 | 2 | 1.536 × 2.132 |
| `arpeggiato` | 0.55 × **3.24** | **0.369** | 99 | 0.485 × **5.434** |
| *reference:* `augmentationDot` | 0.48 × 0.47 | 0.718 | 465 | 0.400 × 0.400 |
| *reference:* `ledgerLine` | 2.02 × 0.29 | 0.344 | 768 | — |
| *reference:* `noteheadBlackOnLine` | 1.33 × 1.08 | 0.718 | 1,444 | 1.180 × 1.000 |

Three things fall out of it immediately and each has its own section below:
**a tenuto and a ledger line are the same box** (1.8-2.0 × 0.30 against
2.02 × 0.29); **a staccato dot and an augmentation dot are the same box**
(0.36 vs 0.48, ranges overlapping completely); and **`arpeggiato` at 0.55 × 3.24
is a plausible arpeggio shape**, which is why the "it's obviously a stem"
reading needs qualifying.

---

## `articStaccatoAbove` / `articStaccatoBelow`

A dot printed directly above or below a notehead, on the side away from the
stem. Produced only by the YOLO detector, as those two classes; the coarse
`articulationStaccato` (id 176) exists and states no side, so
`class_aliases.COARSER_THAN_CANONICAL` refuses to rename it. It is by far the
commonest mark in this family — **69 + 40 of 130 artic detections** on the
probe page, and **47 of the 48 articulations** that reached the Litolff file
are `<staccato>`.

### 1. What sets it apart — and what it is confused with

Sean's own table already has this one: *staccato — stacked vertically with one
head, on the opposite side from the stem, within ~a space; **never to the
head's right***
(`docs/position-grammar-confusables-2026-09-04.md` §2 DOT). **This dossier
agrees and adds a number: the confusion cannot be resolved by size.**

| confused with | the fact that separates it | evidence |
|---|---|---|
| **augmentation dot** | POSITION, not size. An aug dot is to the RIGHT of the head at the head's own y (or half a space above for a head on a line); a staccato is stacked vertically, x-offset zero | MEASURED HERE. `rhythm._pair_dots_to_targets` (`tools/omr/rhythm.py:1136-1190`) requires `tgt_x_right <= dot_x_left` — the note must be LEFT of the dot. Offsets bimodal over 116 dots: 52 at 0.00 spaces, 52 at +0.50, nothing between +0.57 and +3.75 |
| **augmentation dot, by SIZE** | it does **not** separate | **PROBE**: staccato max 0.91 sp against aug-dot min 0.25 sp — total overlap. 9.7% of 465 aug dots are at or below the staccato median; 1.8% of 109 staccati are at or above the aug-dot median |
| **repeat dots** | a vertical PAIR in spaces 2+3 beside a barline | LITERATURE / `docs/position-grammar-confusables-2026-09-04.md` §2. `repeatDot` is excused in `export.NOT_NOTATION` as a legacy known gap, so it never competes for a quantity |
| **F-clef dots** | header window only, past the clef body's right edge, 0.94-1.79 notehead widths | MEASURED HERE (the clef dot-veto work, `benchmarks/omr-clef-geometry/RESULTS.md`) |
| **bleed / speckle** | fails every position test at once | ASSERTED — the "matches nothing → drop" dividend in the confusables doc is proposed and not built |
| **portato (`<detached-legato>`)** | a staccato dot printed UNDER A SLUR. **Not separable at all today** | MEASURED HERE: Mozart 40's truth is 96 `<staccato>` + **14 `<detached-legato>`**; DSv2 has no class, because on the page it is a staccato dot (`benchmarks/omr-corpus-widening-2026-09/FINDINGS.md` FIX 3) |

⚠️ One thing the registry says that the shipped rule does not honour: `[L60]`,
a small articulation near the middle line is centred in the next free SPACE, so
the mark-to-head y distance is **quantised, not smooth**. The shipped rule does
not test y distance at all — only the SIGN of it — which is the right design
under that convention and is why it works. LITERATURE (Dorico), untested here.

### 2. Best method: YOLO / CV / other

**YOLO, and it is the one mark in this family the detector is genuinely good
at.** Median confidence 0.684 / 0.725 — the highest of any class in the family
and level with noteheads (0.718). PROBE, n = 109.

CV is a poor fit: a staccato dot is a blob of 0.36 staff spaces with no
internal structure, so a connected-component reader would find it and have
nothing to say about it. What CV *could* add is the one thing YOLO cannot —
`Q.INK` would place the dot's component beside the notehead's and the stem's,
so "this blob is stacked with that head and there is a stem on the other side"
becomes computable. That is proposed nowhere and is ASSERTED.

⚠️ **The resolution arithmetic is worth checking before assuming YOLO will stay
good at it.** A staff space is 100 canonical px
(`measure_extractor.CANONICAL_STAFF_SPAN_PX = 400`, `:1407`), so a staccato dot
is ~36 canonical px; the cell is then letterboxed to `OMR_IMGSZ` (default 512
in the container, 2048 for the weights this probe used). The dot is the
smallest notation glyph on the page and is the one most exposed to that
downscale. ASSERTED — the arithmetic follows from two measured constants, but
nobody has measured staccato recall against `imgsz`.

### 3. Where on the page the deciding information lives

**In x, at the notehead's own centre — and that is the tight key.** The
convention `[C51 + L58 + L61]` says the x offset is zero, and the repo's own
sweep found exactly that: a flat plateau from 0.50 to 2.50 notehead widths,
197 placed, precision 0.980, with a cliff at 0.30 (106 placed, 0.486). So x
joins tightly and y is the loose one. MEASURED HERE,
`benchmarks/omr-corpus-widening-2026-09/FINDINGS.md` §3, n = 218 over 8 works;
constant at `tools/omr/transcribe.py:2573`.

**In y, only the SIGN matters** — which side of the notehead centre the mark
falls. The distance is quantised by `[L60]` and is not used.

**And the side itself comes from the class name, not from the page.** The
position fact that would be an independent ruler exists —
`Q.ARTICULATION_POSITION` carries `measured_side` and `steps_clear_of_staff`
(`tools/omr/staged/positions.py:473-489`) — is default OFF
(`OMR_FAMILY_POSITIONS`) and is read by nothing
(`tools/omr/staged/reach.py:166-170`: *"the side is read off that class, so
today the two cannot disagree"*). Reach on Litolff p1-4 is **98 rows**, on
Brahms p0-3 **196** (`benchmarks/omr-family-positions-2026-09/FINDINGS.md` §5).

### 4. Stage by stage

| stage | what happens | where |
|---|---|---|
| **GATHER** | `gather_glyph_families` files `Q.ARTICULATION_MARK` — the class name, the canonical box, the page box, the confidence, and `side` from the class suffix | `tools/omr/staged/gather.py:884-886`; `_artic_side` at `:777-800` |
| | `gather_ownership_evidence` files `Q.GLYPH_BAND_DISTANCE` if the same class is detected on ANOTHER staff of the system at IoU ≥ `CONTEST_IOU` | `:537-633` |
| | `positions.py` files `Q.ARTICULATION_POSITION` **only when `OMR_FAMILY_POSITIONS=1`**, and nothing reads it | `positions.py:527` |
| **ADJUDICATE** | `adjudicate_articulation_owner` → `Q.ARTICULATION_OWNER`. Nearest notehead in x on the declared side, within 0.75 notehead widths of the cell's MEDIAN notehead width. Reasons: `nearest_on_declared_side`, `no_notehead`, `no_side_declared`, `no_evidence`. `Mode.ADDITIVE` | `adjudicators/ownership.py:711-838` |
| | Runs after `Q.GLYPH_OWNER` and before the rhythm block | `adjudicate.py:759` |
| **EVALUATE** | **nothing.** No consequence reads or writes any articulation quantity | `consequences.py` — grep returns none |
| **INFER** | **nothing.** `infer.py` reads fourteen quantities, none of them this family | `infer.py` |
| **EXPORT** | `_place_articulations` puts the kind on the owning notehead's detection dict by SUBJECT KEY, then `_mxl_note(articulations=…)` writes it per head (a chord member wears its own) | `export.py:1426-1468`, `:2475`, `:2489` |

**Litolff Beethoven 5 pp.1-4, measured** (coverage JSON, cited above):

```
marks in log        98
decided             82      abstained  no_notehead 16
written             48      lost       artic_owning_notehead_not_written 34
balance             balanced: true
```

⚠️ **The biggest single loss is not this decision's.** 34 of 98 marks are
correctly attached to a notehead that `_place_notes` then refused — that run
dropped 738 notes (`duration_narrowed` 335, `no_pitch` 205,
`owned_by_another_staff` 173, `ink_is_a_whole_rest` 25). So roughly a third of
the articulations are lost upstream of the family entirely. MEASURED HERE for
the total; the SPLIT of those 34 across the four note-drop reasons is
**not measured** and is one join away (join the 34 mark subjects to their
owner's drop reason).

### 5. Abstain or best-guess — and what leans on this mark's certainty

**(a) Yes, and it does, and the abstention is what buys the precision.** A mark
with no notehead on the correct side abstains `no_notehead` rather than taking
the nearest thing available. 21 of 218 abstain on the engraved corpus and
**precision is 0.980 because of it**
(`benchmarks/omr-corpus-widening-2026-09/FINDINGS.md` §3). On Litolff it is 16
of 98. There is no best-guess tier and none is proposed.

**(b) Nothing leans on it.** No adjudicator, no consequence, no inference and
no other exporter path reads `Q.ARTICULATION_OWNER`. A staccato is a leaf.

⚠️ The dependency runs the OTHER way and is strong: the mark's reading is
entirely downstream of **notehead detection and stem direction**. Two
consequences —

* **No head, no mark.** The rule has nothing to attach to and abstains.
* **No stem direction, wrong side.** The class name states the side; the SIDE
  is a consequence of the stem, which the engraver chose. Stem direction is
  read on **62.5% of noteheads on Litolff and 53.7% on Brahms**
  (`benchmarks/omr-staged-voices-2026-09/FINDINGS.md`, via CLAUDE.md's *Three
  families wired in one pass*), so on ~40-45% of heads the pipeline could not
  check the class's claim even if it wanted to.

⚠️ **The independence test fails, and it is worth saying plainly.**
`capture.py` computes `side_is_not_a_ruler` for exactly this family
(`tools/omr/staged/capture.py:1647-1652`): the side is read off the class name,
so a misclassified glyph carries a confidently wrong side, and side and class
fail together. That is the repo's correlated-witness hazard with the
correlation running through the class name — the same shape as *the bars are
not an independent umpire over a bad reading*. The independent ruler exists,
is default OFF, and is read by nothing.

**Evidence grade:** confidences and shapes PROBE (n = 109, one publisher, one
checkpoint); the 0.980 / plateau MEASURED HERE (n = 218, 8 engraved works); the
Litolff counts MEASURED HERE (n = 98); `[L60]` and the Dorico placement rules
LITERATURE; the `imgsz` exposure ASSERTED. Registry: `[C51 + L58 + L61]`,
`[L59]`, `[L60]`.

---

## `articStaccatissimoAbove` / `articStaccatissimoBelow`

A narrow vertical wedge in the staccato's position — the "hammered dot". Two
classes, YOLO only. Fired **7 times** on the probe page and **zero** times in
the labelled training corpus
(`benchmarks/omr-labeling-survey-2026-09/INVENTORY.md`).

### 1. What sets it apart — and what it is confused with

**From a staccato dot: HEIGHT, and it is the only articulation where shape
does the work.** Bravura `articStaccatissimoAbove` is 0.396 × **1.180** staff
spaces against staccato's 0.336 × 0.336 — a factor of 3.5 in height at the same
width. LITERATURE (Bravura `glyphBBoxes`).

⚠️ **And the probe disagrees with the font.** The detector's seven boxes
measure 0.44 × **0.65** sp (h/w 1.5), not 0.40 × 1.18 (h/w 3.0). Two readings
are possible and the probe cannot separate them: Breitkopf may print a shorter
wedge than Bravura draws, or the detector may be clipping the wedge's tail.
**PROBE, n = 7** — far too few to call, and worth a crop.

Otherwise confusable with: a staccato dot (above), a flag fragment, an
accidental's stroke. None measured here.

### 2. Best method: YOLO / CV / other

YOLO, weakly — median confidence 0.475, n = 7 (PROBE). The shape is the one
thing a CV reader could measure cheaply (a tall narrow component in the
articulation band), and it is the one thing that separates this from the
commonest mark on the page. Nothing does it. ASSERTED.

### 3. Where on the page the deciding information lives

Identical to the staccato: x at the notehead's centre, side from the class,
distance quantised. The mark's own HEIGHT is the discriminator and is recorded
on `Q.ARTICULATION_MARK` (`y0`/`y1`, `gather.py:852-856`) and read by nothing.

### 4. Stage by stage

Exactly the staccato's path — `articulation_kind`
(`tools/omr/transcribe.py:2576-2592`) returns `("staccatissimo", above)` and
the rest is identical. It exports as `<staccatissimo/>`.
**On Litolff pp.1-4 it produced zero elements** (the exported XML holds 47
`<staccato>`, 1 `<tenuto>` and nothing else). MEASURED HERE.

### 5. Abstain or best-guess — and what leans on this mark's certainty

**(a)** Same abstention as the staccato, same reasons, same lack of a
best-guess tier. **(b)** Nothing leans on it.

⚠️ There is no mechanism anywhere that would notice a staccatissimo read as a
staccato. It is one MusicXML element for another on the same note — the file
stays valid, the balance stays balanced, and only the print says otherwise.

**Evidence grade:** shape PROBE (n = 7 — do not quote it as a distribution);
Bravura LITERATURE; everything else ASSERTED. Registry: `[C51]`.

---

## `articAccentAbove` / `articAccentBelow`

The horizontal `>` wedge, notehead-scale. YOLO only; the coarse
`articulationAccent` (id 175) states no side and is refused a rename. Fired
7 times on the probe page; 16 + 12 boxes in the labelled corpus.

### 1. What sets it apart — and what it is confused with

**Sean's own entry is the load-bearing one and this dossier adds a number to
it.** `docs/position-grammar-confusables-2026-09-04.md` §2 WEDGE: an accent is
**note-anchored** (notehead-scale, stacked with ONE head); a hairpin is
**span-anchored** (dynamics band, two or more onsets). *"Width alone fails —
one-beat hairpins exist; note-anchor vs span-anchor does not."*

The number: **PROBE** gives the accent at 1.67 × 0.36 staff spaces, n = 7.
Bravura gives 1.356 × 0.976 and `hairpinThickness` 0.16. So an accent and a
short hairpin differ enormously in EXTENT and share a stroke weight — which is
the registry's own reading (`C49`) and is why the discriminator has to be the
anchor count, not the size. ⚠️ **Not one accent or hairpin has been
hand-adjudicated in this repo**, so `C49` is still ASSERTED at the level of
"how often does this actually happen".

Second confusable, and it is real on a scan: **the `>` of a printed word**.
`direction_text`'s lexicon rejected `P -iest`, `@ ,` and `CTESC.` on this very
document (`transcription.json` `direction_text.rejected`), so the page does
carry text fragments the readers argue about. ASSERTED — nobody has measured an
accent firing on a letter.

### 2. Best method: YOLO / CV / other

YOLO. Median confidence 0.547, n = 7 (PROBE). ⚠️ The mark is a thin diagonal
stroke pair, which is the shape class this repo moved to classical CV for stems
and beams on the stated ground that **YOLO bounding boxes are structurally bad
at thin lines** (CLAUDE.md, *Local OMR engine notes*). A hairpin is the same
shape and IS read by CV (`hairpin_detection`, worth wedges 2 → 118 on scans).
**Nobody has asked whether the hairpin reader's band search would find accents
if pointed at the notehead band.** That is the single most obvious untried
method in this dossier. ASSERTED.

### 3. Where on the page the deciding information lives

Same as the staccato in x and side. **What is different and unused: the accent
is wide.** Its extent relative to the notehead is what separates it from a
hairpin, and neither `Q.ARTICULATION_MARK` nor `Q.ARTICULATION_POSITION` is
read for width by any decision (the box is recorded; `_mark_discriminator`
adds only `steps_clear_of_staff`, `positions.py:473`).

### 4. Stage by stage

The staccato's path exactly. Exports as `<accent/>`. On the eleven-work
engraved set the class is real and reaches the file — Mahler 5 exports **6 of
6** (`benchmarks/omr-export-gaps-2026-09/FINDINGS.md` §1, which also records
that CLAUDE.md carried a stale "consumed 0" claim for two days after it was
closed). MEASURED HERE.

### 5. Abstain or best-guess — and what leans on this mark's certainty

**(a)** Abstains the same way. **(b)** Nothing reads it.

⚠️ **The one real coupling is with the WEDGE family and it is not modelled.**
An accent and a hairpin are the same ink at different scales; they are routed
to different quantities by CLASS (`gather.py` `_ARTIC_PREFIX` vs
`_WEDGE_CLASSES`), so a misclassification at the detector silently moves the
mark between two families that never compare notes. There is no arbitration
between them anywhere. MEASURED HERE (the routing); the cost is unmeasured.

**Evidence grade:** shape PROBE (n = 7); Mahler 6-of-6 MEASURED HERE;
the CV route ASSERTED. Registry: `[C49]`, `[C51]`.

---

## `articMarcatoAbove` / `articMarcatoBelow`

The vertical wedge `^`. **Zero detections on the probe page and zero in the
labelled corpus** (`INVENTORY.md`); the coarse spellings
`articulationMarcatoAbove`/`Below` ARE renamed to these by
`class_aliases.ALIASES`, because they are the only two articulation classes
whose coarse names state a side.

### 1. What sets it apart — and what it is confused with

**A marcato is the accent rotated, so the two are the same family and the same
confusable set** (`docs/position-grammar-confusables-2026-09-04.md` §2 WEDGE:
*"Marcato is the vertical wedge; same family"*). Bravura: 0.944 × 1.016 against
the accent's 1.356 × 0.976 — nearly square where the accent is wide.
LITERATURE.

⚠️ **The convention registry records an exception this pipeline cannot
honour**: marcato *"is always placed above the staff, regardless of the stem
direction"* (Dorico, via `[C51]`'s known exceptions). The shipped rule takes
the side off the class name and then REQUIRES the geometry to agree — so a
`articMarcatoBelow` on a stem-up note, which the engraver would not print, is
refused; but a correctly-printed marcato ABOVE a stem-up note whose class the
detector spelled `Below` is also refused. The rule cannot tell them apart.
MEASURED HERE (the code, `ownership.py:797-806`); never exercised, because the
class never fires.

### 2. Best method: YOLO / CV / other

Unknown — **reach is zero on everything measured**, so no method has been
tested. Measure reach before accuracy.

### 3. Where on the page the deciding information lives

As the accent. Plus the convention that marcato is always above, which is
available in the literature and encoded nowhere.

### 4. Stage by stage

The staccato's path. `articulation_kind` returns `("marcato", above)` and the
exporter writes `<strong-accent/>`. Zero on every document in the repo.

### 5. Abstain or best-guess — and what leans on this mark's certainty

**(a)** Abstains. **(b)** Nothing. **Reach is the whole finding here.**

**Evidence grade:** ASSERTED throughout — zero detections anywhere. Bravura
geometry LITERATURE. Registry: `[C51]`.

---

## `articTenutoAbove` / `articTenutoBelow`

A short horizontal stroke above or below the notehead. YOLO only.
7 detections on the probe page; 30 + 0 boxes in the labelled corpus.
**One `<tenuto>` reached the Litolff file** against 47 `<staccato>`.

### 1. What sets it apart — and what it is confused with

**This is Sean's own example and the probe now prices it: a tenuto and a ledger
line are the same box.**

| | w (sp) | h (sp) | conf med | n |
|---|--:|--:|--:|--:|
| `articTenutoAbove` | 1.81 | 0.30 | 0.316 | 2 |
| `articTenutoBelow` | 1.96 | 0.33 | 0.394 | 5 |
| `ledgerLine` | **2.02** | **0.29** | 0.344 | 768 |

**PROBE, Brahms 1 / Breitkopf pp.1-3.** Width, height and confidence all
overlap. `docs/position-grammar-confusables-2026-09-04.md` §2 HORIZONTAL STROKE
already says the discriminators exist and are positional — *a ledger line lies
ON the extended half-space lattice, continues a ladder run toward a head or has
a head centred through it, and matches the staff's own measured line thickness;
a tenuto sits OFF the lattice about a space beyond its head, with nothing
centred through it.* **This dossier agrees and adds that no shape test could
ever substitute**, because there is no shape difference to find.

⚠️ **And the confusion is live in the evidence chain, not just the export.**
The confusables doc says so and the tree confirms it: `_observe_ladder`
(`tools/omr/staged/gather.py:648-660`) builds the ledger ladder from
`ledgerLine` detections, and `adjudicate_glyph_owner` uses that ladder to
decide which staff owns a contested notehead. **A tenuto misread as a ledger
line feeds a false rung into note attribution; a ledger misread as a tenuto
starves it.** The registry adds the scale of the noise: the detector fires
`ledgerLine` on **1,107 ordinary staff lines inside the staff** on one
four-page record (`docs/engraving-conventions.md`, Stems & beams, known
exceptions). MEASURED HERE.

Second confusable: **a beam fragment**. Same stroke, same weight. Not measured.

### 2. Best method: YOLO / CV / other

**YOLO is measurably the weakest here and the reason is structural.** Median
confidence **0.316 / 0.394** — the lowest of any class in this family, against
staccato's 0.684-0.725 (PROBE, n = 7). A tenuto is 1.8 × 0.30 staff spaces:
a thin horizontal line, which is the exact shape class this repo moved to
classical CV for stems and beams. **`line_detection` already finds horizontal
runs** (`detect_beams`, `detect_lines`) and its output never reaches this
family.

The discriminator the confusables doc names — *on the lattice or off it* — is a
geometry test over the staff grid, not a classification. It needs
`Q.STAFF_LINES` and the mark's own page-pixel box, both of which are on the
record. Nothing computes it. ASSERTED, and it is the cheapest unbuilt thing in
this dossier.

### 3. Where on the page the deciding information lives

**Not in the mark. In the lattice around it.** Three facts, all already
gathered: (1) does the stroke's y sit on the extended half-space lattice;
(2) is a notehead centred through it; (3) does its thickness match the staff's
own measured `line_thickness_px` (recorded per staff since the frame-retention
work — the probe page reads `[6.0, 6.0, 6.0, 6.0, 6.0]` on staff 0 against a
tenuto height of 8-9 px).

⚠️ **The frame is the trap.** `Q.ARTICULATION_MARK` carries both a canonical
box and a page box (`gather.py:845-870`); `Q.STAFF_LINES` is page pixels. So
this test IS computable for this family — unlike the barline/stem test, which
`docs/plan-2026-09-18-what-distinguishes-each-mark.md` §5 records as
**uncomputable** because `Q.STEM` has no page coordinates at all. Worth saying
because the two look like the same problem and are not.

### 4. Stage by stage

The staccato's path exactly. Exports as `<tenuto/>`. Litolff pp.1-4: one
element. On the engraved corpus Boulanger's truth carries 13 tenuto and we
emit 9 (`benchmarks/omr-corpus-widening-2026-09/FINDINGS.md`).

### 5. Abstain or best-guess — and what leans on this mark's certainty

**(a)** Abstains like the rest; no best-guess tier.

**(b) ⚠️ This is the one mark in the family whose certainty other things depend
on, and the dependency is indirect.** Because tenuto and `ledgerLine` are the
same ink, an error in EITHER direction lands in `glyph_owner`'s ladder — which
decides which staff owns a cross-staff notehead, which decides whether that
note is written at all (`owned_by_another_staff` dropped 173 notes on Litolff
pp.1-4). So the failure does not show up as a missing tenuto; it shows up as a
note on the wrong staff.

**Independence:** the ladder and the tenuto reading come off the SAME detector
on the SAME raster, so they fail together by construction. The ladder rule is
already **COMPLETENESS ONLY, never count** for a related reason
(`gather.py:648`), which is the repo protecting itself against exactly this.

**Evidence grade:** shapes PROBE (n = 7 tenuto, 768 ledger — the tenuto n is
tiny and the claim rests on the ledger side plus the confusables doc);
1,107 false `ledgerLine` MEASURED HERE (registry, one four-page record);
the lattice test ASSERTED. Registry: `[C51]`, and the Stems & beams ledger
entry.

---

## `fermataAbove` / `fermataBelow`

The pause sign — a dot under an arc, hanging over whatever is sounding beneath
it. Its own quantity, its own adjudicator, its own carrier rule, and the only
member of this family whose carrier may be a REST.

### 1. What sets it apart — and what it is confused with

**It is not an articulation and the separation is the engraving's**
(`record.py:461-479`). An articulation names ONE notehead on the side its class
states; a fermata hangs over an EVENT, which on a conductor's page is most often
a whole-bar rest. MEASURED HERE and it is the majority case: **26 of 51 carriers
are rests** on Litolff p1-3, n = 51
(`benchmarks/omr-staged-fermata-2026-09/out/litolff-p1p3.txt`).

| confused with | separator | evidence |
|---|---|---|
| **a slur or tie end** | ASPECT. `tie` boxes measure h/w **0.19** and `slur` **0.21** on the probe page; `fermataAbove` measures **0.54** and Bravura's is 1.328/2.408 = **0.55** | PROBE (n = 828 tie, 76 slur, 2 fermata — the fermata side is n = 2 and is the font's number doing the work) |
| **the staff above's DYNAMICS** | ⚠️ **nothing separates them today.** The registry names this and the repo has not modelled it: a fermata is expected in the band ABOVE its staff, which on a conductor's page is the band the staff above's dynamics occupy, *"so fermata and dynamic detections in one gap are competing for the same ink and need arbitration, not independent attribution"* | LITERATURE / `[C52 + L62]`. The measured half: **24% of dynamic letters stand in the band of the staff immediately above, distance exactly 1, no exceptions** (`benchmarks/omr-dynamics-band-2026-09/FINDINGS.md`, n = 1,246 letters) |
| **a second detection of itself** | nothing; it is dedupe done by accident | MEASURED HERE: **13 of 51** Litolff carriers are named by exactly 2 marks each, heavily overlapping boxes, one confident and one not. The exporter's chord-hoist absorbs them. *"a happy accident, named as one"* |

### 2. Best method: YOLO / CV / other

**YOLO, and on the right document it is good.** Litolff p1-3: 63 detections,
confidence min 0.254 / median **0.807** / max 0.911, n = 63. On the probe's
Brahms page it fires 4 times at median 0.45-0.51, n = 4.

⚠️ **The shape is favourable to CV and nobody has tried.** Bravura
`fermataAbove` is 2.408 × 1.328 staff spaces — *"wide and low, an easily
separated shape"* (`[C52]`) — standing clear above the staff where there is
usually nothing else. A band search of the kind `hairpin_detection` already
runs would be a natural second reader. ASSERTED.

### 3. Where on the page the deciding information lives

**In x alone, inside the bar.** `adjudicate_fermata_owner` pairs by x — the
mark's centre inside a carrier's x-span, or failing that the nearest carrier
centre in the bar — and **never by pitch**. `ownership.py:1036-1130`.

**The side is NOT a constraint here**, and that is the sharpest difference from
an articulation: a `fermataAbove` over a whole-bar rest stands well above ink it
belongs to. `Q.FERMATA_MARK` records the side and **nothing reads it**, because
`_mxl_note` writes `type="upright"` unconditionally (`record.py:472-479`).

**There is no distance constant, deliberately** — the bar bounds the search —
and every verdict carries `dx_canonical_px` so one can be read off a measured
population later (`ownership.py:1076-1080`).

### 4. Stage by stage

| stage | what happens | where |
|---|---|---|
| **GATHER** | `Q.FERMATA_MARK` — class, boxes, confidence, `side` | `gather.py:905-913` |
| | `Q.FERMATA_POSITION` under `OMR_FAMILY_POSITIONS`, read by nothing | `positions.py:528` |
| **ADJUDICATE** | `adjudicate_fermata_owner` → `Q.FERMATA_OWNER`. Carriers are `("notehead", "rest")`. Reasons: `contains_the_mark`, `nearest_in_bar`, `no_carrier`, `no_evidence`. Runs beside the articulation, **not after the rhythm** — its carriers are GATHER rows, so it depends on no verdict at all | `ownership.py:1026-1130`; `adjudicate.py:760-764` |
| **EVALUATE / INFER** | nothing | — |
| **EXPORT** | `_place_fermatas` sets a flag on the carrier; `_mxl_note` HOISTS it to the chord's first `<note>` (one pause per event, unlike an articulation) | `export.py:1471-1514`, `:2402-2410` |

**Two runs, both measured:**

| | Litolff p1-3 | Litolff p1-4 |
|---|--:|--:|
| marks | 63 | 67 |
| decided | 51 | 55 |
| abstained `no_carrier` | 12 | 12 |
| absorbed (duplicate detections) | 13 | 13 |
| `<fermata>` written | **37** | **41** |
| `nearest_in_bar` fired | **0** | — |

⚠️ **The `nearest_in_bar` fallback has never fired on real ink.** All 51
Litolff decisions are `contains_the_mark`. Its correctness rests on its unit
test alone, and the legacy docstring's reason for keeping it (a fermata over a
bar's only rest is engraved at the BAR's middle while the rest glyph sits at
its own centre) is unexercised. MEASURED HERE, n = 51.

⚠️ **Reach is ZERO on Brahms 1 / Breitkopf p0-3** — `fermata` reads 0 ink rows
there (`benchmarks/omr-family-positions-2026-09/FINDINGS.md` §5), and the
fermata arm was RUN on that document specifically to make it print its own
negative control (`out/brahms-p0p3.txt`). One publisher only.

### 5. Abstain or best-guess — and what leans on this mark's certainty

**(a) Yes, and the abstention is a READING shortfall it honestly labels as
one.** 12 of 63 bars hold a pause and no notehead and no rest that we read —
*"the mark is right and the bar is empty"*. That is a gap in the note reading
reported by the fermata family, which is exactly what the abstention vocabulary
is for.

**(b) Nothing leans on it**, and one thing that plausibly should does not: a
fermata is a *strong* signal that its bar is a phrase end or a movement end,
which nothing in the pipeline uses. `capture.py:1232-1234` says the aggregate
version of this out loud — *"recording where fermatas fall is what later lets an
unnamed blob be scored as fermata-shaped"* — and no store exists.

⚠️ **The one dependency that is real and unarbitrated: the cell padding.** The
adjudicator's own docstring records it (`ownership.py:1065-1070`): a fermata is
printed above the staff and a measure cell is padded above, so a mark can land
in the cell of the staff ABOVE the one that prints it, exactly as a hairpin
does. `gather_ownership_evidence` WILL file a contest if the same class is
detected on both staves — but if only the upper cell reaches the ink, there is
no contest and no verdict, and the mark is filed against the wrong staff with
nothing recording that. That is the shape
`benchmarks/omr-phantom-notes-2026-09/FINDINGS_2026-09-15_STALENESS.md` measured
for noteheads (11 of 13 offending bars hold NO contest at all). ASSERTED for
fermatas — nobody has counted it.

**Evidence grade:** carriers 26/25, the 12 abstentions, the 13 duplicates and
the zero fallback all MEASURED HERE (n = 51-63, one document, one publisher);
the dynamics-band contest LITERATURE for the fermata half and MEASURED HERE for
the dynamics half; the padding hazard ASSERTED. Registry: `[C52 + L62]`.

---

## `ornamentTrill`

The `tr` (usually without its wavy line). YOLO only. **21 detections across
every committed transcription in the repo**, +26 more in class-inventory files;
8 on the probe page; **zero** in the labelled training corpus.

### 1. What sets it apart — and what it is confused with

**Its side is a convention, not a fact its class carries** — a trill is printed
clear ABOVE the note, centred on it, whatever the stem does. `[C87]`, status
ASSERTED: the convention carries no sweep and no plateau, and the code says so.

| confused with | separator | evidence |
|---|---|---|
| **the `Tr.` of a margin label** | the margin is outside every measure cell, so the detector never sees it — EXCEPT in a header crop that over-runs | MEASURED HERE, and the over-run is real: on Litolff p2 system 1, **all eleven header windows were 6.1-6.2 staff spaces and held the margin label and the systemic rule and no music**, because `system_left_edge` takes the MINIMUM of one estimate per staff and one staff under-ran its ten siblings by ~70 px (`benchmarks/omr-keysig-truth-2026-09/FINDINGS.md`, n = 11). Fixed by anchoring on the MEDIAN. ⚠️ No trill was observed firing on a label — the point is that the crop CAN contain one |
| **the lexicon's `Tr.`** | a different pipeline entirely | MEASURED HERE, and it is a live trap in the identity layer rather than here: `Tr.` is Trombe AND Tromboni and cost three staves on Beethoven 5 p.48 (CLAUDE.md, *Instrument identity*). The two readers never meet |
| **a mordent / a turn** | stroke count and shape | ASSERTED |
| **bleed on a dense page** | nothing | ASSERTED |

⚠️ **The `<wavy-line>` half is not attempted at all** — it needs a SPAN (start
and stop notes) and the detector gives a point
(`benchmarks/omr-export-gaps-2026-09/FINDINGS-2026-09-08-ornaments-and-the-derived-check.md`
§3). A scan-derived truth holds 17 `<ornaments>` = 15 tremolo-only + **2
`<wavy-line>` blocks**, so the shape is real in the corpus.

### 2. Best method: YOLO / CV / other

**YOLO, and it is mediocre: median confidence 0.448, n = 8** (PROBE). Placed
and unplaced trills do not separate by confidence — placed 0.70, 0.34, 0.74,
0.36; unplaced 0.31, 0.49, 0.56, 0.41
(`benchmarks/omr-export-gaps-2026-09/…ornaments…md` §4, n = 8) — which is
consistent with this repo's standing refusal to use confidence as a
discriminator.

**OCR is the obvious untried reader and it is already installed.** A trill is
the letters `tr`. `direction_text` runs Surya and Tesseract over the ink left
after every detection is subtracted, gated on a 181-word musical lexicon
(`tools/omr/direction_text.py`). It would read `tr` and the lexicon would
refuse it, because a two-letter token has no lexicon to be gated by — the same
argument CLAUDE.md already makes for dynamic letters. ASSERTED, and it is the
symmetrical opposite of the dynamics case: there the missing tool is a template
match against Bravura, and `symbol_library/` holds 38 templates and no ornament.

### 3. Where on the page the deciding information lives

**Above the note, centred on it in x** — an articulation's geometry with the
side hard-coded rather than parsed (`[C87]`). The constant is
`_ORNAMENT_MAX_DX_NOTEHEAD_WIDTHS = 1.0` (`tools/omr/transcribe.py:2699`) and
it is **declared UNMEASURED by its own author**: unlike the articulation's 0.75
it sits on no swept plateau, because across 7,090 committed artifacts there is
no per-mark truth to score a placement against.

**Reach, which is the number that matters:** 4 of the 8 detections find a
notehead within 1.0 notehead widths on the printed-above side; dx 4-13.5 px
against a median notehead width of ~30-40 px. So the four that place, place
easily — the constant is nowhere near binding — and the four that do not have
no notehead above them at all. MEASURED HERE, n = 8.

### 4. Stage by stage

| stage | what happens | where |
|---|---|---|
| **GATHER** | `Q.ORNAMENT_MARK` — routed by asking `transcribe._ORNAMENT_KINDS`, **not** by prefix, because `tremolo1`-`5` are ornaments whose names do not begin `ornament`. Carries `kind`, `strokes` and `side` | `gather.py:889-904`, `_ornament_kind` at `:755-774` |
| | `Q.ORNAMENT_POSITION` under the flag, read by nothing | `positions.py:529` |
| **ADJUDICATE** | `adjudicate_ornament_owner` → `Q.ORNAMENT_OWNER`. A NOTEHEAD, never a rest. Reasons: `nearest_on_declared_side`, `nearest_either_side`, `no_notehead`, `no_evidence` | `ownership.py:1135-1240` |
| **EVALUATE / INFER** | nothing | — |
| **EXPORT** | `_place_ornaments` → `_mxl_ornament_elements` → `<trill-mark/>` per head; LilyPond `\trill` | `export.py:1517-1560`; `tools/omr/export.py` |

**Litolff pp.1-4: 1 ornament mark in the whole record, 0 decided, 1 abstained
`no_notehead`, 0 elements written.** The family's status in the census is
`abstained`. MEASURED HERE.

**Brahms 1 / Breitkopf p0-3: 7 ornament ink rows**
(`benchmarks/omr-family-positions-2026-09/FINDINGS.md` §5). The A/B on the
Breitkopf transcription moved `<ornaments>` **0 → 4**, ledger rows 6,086 →
6,090, with **non-ornament rows identical (6,086 / 6,086)**. MEASURED HERE.

### 5. Abstain or best-guess — and what leans on this mark's certainty

**(a) Yes, and half the population does.** 4 of 8 abstain `no_notehead` rather
than taking the nearest thing available — the rule that keeps the articulation
pass at 0.980, inherited rather than re-decided.

**(b) Nothing leans on it downstream. One thing leans on it UPSTREAM, on the
legacy path only, and it is the finding of this section.**

`transcribe._filter_stems_overlapping_tremolo` (`tools/omr/transcribe.py:617-651`)
drops any classical-CV stem candidate whose box is ≥30% covered by a
tremolo / arpeggiato / **ornament** detection, because `detect_stems` finds tall
narrow near-vertical ink and these glyphs have that shape. It was verified on
real orchestral pages: on 6 of 8 sampled cells where it fired, removing the
phantom stem changed which real stem `_stem_for_notehead` picked — *"and
therefore the notehead's beam-anchored duration and/or inferred stem
direction"*. MEASURED HERE (the audit follow-up, 2026-07).

⚠️⚠️ **The STAGED path does not apply that filter.** `gather_cv_lines`
(`tools/omr/staged/gather.py:1383-1482`) calls `detect_lines` and files every
stem it returns straight into `Q.STEM`; `grep -rn '_filter_stems_overlapping_tremolo' tools/omr/`
returns hits in `transcribe.py` only. So an ornament detection protects the
legacy duration reader and does not protect the staged one. MEASURED HERE
(grep of the tree, no run).

**Evidence grade:** reach 4-of-8 and the confidences MEASURED HERE (n = 8, one
page); the 21/6/3/3 census MEASURED HERE (7,090 artifacts); the constant's
UNMEASURED status is the code's own declaration; the OCR route ASSERTED; the
staged/legacy filter asymmetry MEASURED HERE (tree, not run). Registry: `[C87]`.

---

## `ornamentTurn` / `ornamentTurnInverted`

The `S` on its side, and its mirror. **6 and 3 detections across every committed
artifact in the repo**; zero on the probe page; zero in the labelled corpus.

### 1. What sets it apart — and what it is confused with

From each other: **the mirror, and nothing else.** Bravura gives both as
1.840 × 0.872 staff spaces — **identical bounding boxes** (LITERATURE,
`glyphBBoxes`). So the box carries no information at all about which of the two
it is; only the ink does, and the ink is not read. This is the family's cleanest
example of *a box cannot carry the distinction* — the breakthrough document's
§8 narrow claim, in a case where the two classes are the same rectangle.

From a trill: shape. From a slur: `ornamentTurn` is 1.84 × 0.87 (h/w 0.47)
against slur 4.56 × 1.16 (h/w 0.21) on the probe page. ASSERTED — no turn has
ever been adjudicated here.

### 2. Best method: YOLO / CV / other

Unknown; reach is 9 detections in the whole repository and none on a benchmark
work. ⚠️ Whatever reads it must distinguish a glyph from its own mirror image,
which a bounding box cannot and a template match can. `symbol_library/` holds no
ornament template. ASSERTED.

### 3. Where on the page the deciding information lives

Above the note, centred in x — the trill's rule, same unmeasured constant.
And, uniquely in this family, **inside the box**: the mirror is the whole
question.

### 4. Stage by stage

The trill's path exactly. Exports `<turn/>` / `<inverted-turn/>`, LilyPond
`\turn` / `\reverseturn`. **Zero elements on every document measured.**

### 5. Abstain or best-guess — and what leans on this mark's certainty

**(a)** Abstains as the trill does. **(b)** Nothing.

⚠️ There is no mechanism that would notice a turn read as an inverted turn.
Same balance, same counts, valid file, wrong ornament.

**Evidence grade:** the identical Bravura boxes LITERATURE; the 6 and 3
MEASURED HERE (7,090 artifacts); everything else ASSERTED. Registry: `[C87]`.

---

## `ornamentMordent`

The zigzag with a vertical stroke through it. **3 detections in the whole
repository**; zero on the probe page; zero in the labelled corpus.

### 1. What sets it apart — and what it is confused with

**From a tremolo: the tremolo rides the STEM and the mordent stands above the
note.** That is the only separator the pipeline could use, and it is positional
(`[C55]` vs `[C87]`). Bravura: mordent 2.912 × 1.568 staff spaces — the widest
ornament — against `tremolo3` 1.200 × 2.232, which is narrow and tall.
LITERATURE.

From a trill's wavy line: a mordent is a short zigzag with a vertical bar
through it; a trill's wavy line is long and horizontal. ASSERTED.

### 2. Best method: YOLO / CV / other

Unknown; n = 3 across the repository. ASSERTED.

### 3. Where on the page the deciding information lives

Above the note, centred in x. Same unmeasured constant. The vertical bar
through the zigzag is the mark's own discriminator and is inside the box.

### 4. Stage by stage

The trill's path. Exports `<mordent/>`, LilyPond `\mordent`. Zero elements
everywhere measured.

### 5. Abstain or best-guess — and what leans on this mark's certainty

**(a)** Abstains. **(b)** Nothing.

**Evidence grade:** ASSERTED throughout; the Bravura geometry LITERATURE; the
3 detections MEASURED HERE. Registry: `[C87]`.

---

## `arpeggiato`

The vertical squiggle printed immediately left of a chord, spanning it.
**769 detections across every committed artifact in the repository** — the
largest single class in this family by an order of magnitude, and **the largest
single UNCLAIMED class in the pipeline**: 377 on Litolff pp.1-4, 98 + 86 on two
earlier pages, 99 on the probe page.

### 1. What sets it apart — and what it is confused with

**The repo's reading is that these are not arpeggios at all.**
`benchmarks/omr-staged-gather-2026-09/FINDINGS.md` §6: a 1:7 tall thin box at
half a notehead's confidence is *"a stem or a barline"* — 56 × 388 px at
confidence 0.39 on Beethoven 5 p3 (n = 98) and 40 × 243 at 0.35 on Brahms p2
(n = 86), against noteheads at 146 × 131 / 0.67 and 110 × 85 / 0.72. And it is
**deliberately NOT excused into `NOT_NOTATION`**, because `arpeggiato` really is
a notation family and burying it there would hide the misread. MEASURED HERE.

⚠️⚠️ **THIS DOSSIER PARTLY DISAGREES, AND THE DISAGREEMENT IS THE FINDING: the
SHAPE argument does not carry, because a real arpeggio is also a tall thin
mark.** Bravura `arpeggiato` is **0.485 × 5.434 staff spaces** — h/w 11.2,
*taller and thinner* than anything the detector is drawing here. So "tall and
thin at low confidence" cannot by itself say the class is wrong. LITERATURE
(Bravura `glyphBBoxes`) against MEASURED HERE (the census).

**What the geometry DOES say, measured.** PROBE over the 99 boxes on the probe
page, each expressed against its own staff's measured line positions:

| | value |
|---|---|
| height | min 0.73, p25 2.80, **median 3.24**, p75 3.86, max 5.91 staff spaces |
| top edge, relative to the TOP staff line | median **0.00** spaces |
| bottom edge, relative to the BOTTOM staff line | median **−0.45** (i.e. inside the staff) |
| both ends within 0.4 sp of the outer staff lines — **the barline test** | **9 of 99** |
| height in 3.8-4.2 sp (a staff's exact height) | 11 of 99 |

**So on this document the "barline" half is 9%, not the dominant story.** A
box that starts on the top line and ends inside the staff, 3.24 spaces tall, is
a STEM's footprint far more than a barline's — a barline runs the staff's full
4.0 spaces and anchors on both outer lines (`[C56 + L74]`, and the literature's
extent test: barline 4.0 spaces anchored at the staff's edges, stem ~3.5
anchored at a notehead). ⚠️ **This is a refinement of the repo's claim, not a
refutation**: "a stem or a barline" is still the right family; "a stem" is the
better half of it on this plate, and the SHAPE argument that was used to reach
it does not hold on its own.

Confusables, then, in the direction that matters: **a stem**, **a barline**,
and — because the squiggle is drawn hard against the chord — **the chord's own
ink through the cell's left edge**.

### 2. Best method: YOLO / CV / other

**Neither, as currently arranged.** YOLO fires 769 times at median confidence
0.369 (PROBE median on 99; the census medians are 0.39 and 0.35) and the repo's
own reading is that most are wrong. Classical CV is not better placed either:
`detect_stems` finds this exact shape, which is why
`_filter_stems_overlapping_tremolo` exists to stop the two readers feeding each
other.

**The discriminator is neither shape nor confidence — it is what stands BESIDE
the mark.** An arpeggio is drawn immediately left of a CHORD and spans that
chord's vertical extent; a stem is attached to ONE notehead at one end; a
barline anchors on both outer staff lines and nothing is beside it. That is
`docs/plan-2026-09-18-what-distinguishes-each-mark.md` §7's rule for stems —
*attachment, not length* — applied to a third member of the same shape family.
Nothing computes it. ASSERTED.

### 3. Where on the page the deciding information lives

**In the column immediately to its RIGHT.** Two or more noteheads stacked at
one x, spanning the mark's own y range, is an arpeggio; one notehead at one
end is a stem; nothing is a barline. Everything needed is on the record
(`Q.GLYPH_BOX` page boxes, `Q.EVENT`'s chord grouping, `Q.STAFF_LINES`).

⚠️ And the mark is in the right frame for it: `Q.GLYPH_BOX` carries page pixels
since the page-frame repair, so — unlike the barline/stem test that
`plan-2026-09-18` §5 records as uncomputable because `Q.STEM` has no page
coordinates — this one is computable today.

### 4. Stage by stage

| stage | what happens |
|---|---|
| **GATHER** | `Q.GLYPH_BOX` only. `gather_glyph_families` has no branch for it (`gather.py:875-913`: arcs, `artic*`, `rest*`, `_ornament_kind`, `fermata*` — and `_ORNAMENT_KINDS` does not list `arpeggiato`), so **no typed row is ever written** |
| | `Q.INK` records the component and its `ink_explained_by` names the class — with `gather.py:1726-1729` saying in terms that the coverage *"does NOT claim the component IS one of them, and on this corpus it frequently is not"* |
| **ADJUDICATE** | **nothing. There is no quantity and no decision.** `gather_ownership_evidence` will file a cross-staff contest for it like any class, and `glyph_owner` will decide that contest — but there is nothing to own |
| **EVALUATE / INFER** | nothing |
| **EXPORT** | nothing. `<arpeggiate/>` is a `<notations>` child, not an `<ornaments>` child, so it is a different element and a different gap — **PARKED** (`…ornaments…md` §3). `_unclaimed` reports the count by name |

**Litolff pp.1-4: `unclaimed_classes: {"arpeggiato": 377}`; 0 `<arpeggiate>` in
the exported file.** MEASURED HERE.

### 5. Abstain or best-guess — and what leans on this mark's certainty

**(a) It cannot abstain, because it is never asked.** There is no subject, no
verdict and no abstention — the ink has a `Q.GLYPH_BOX` row and a class name
filed as a FACT (`gather.py:373`, `log.observe`), and nothing downstream is
permitted to doubt it. This is the stage charter's §3a in its purest form
(`docs/stage-charter-2026-09-18-what-each-stage-does.md`).

**(b) ⚠️ On the LEGACY path a lot leans on it, and the leaning is BACKWARDS.**
`_filter_stems_overlapping_tremolo` deletes a CV stem whose box is ≥30% inside
an `arpeggiato` box. So 377 probably-wrong detections are, on that path,
**deleting stems** — and a stem is how `adjudicate_duration` attaches a note to
its beam (`Q.STEM`, worth per-staff readings 401 → 430 on Litolff and 42 → 108
on Breitkopf). A false `arpeggiato` over a real stem is a lost duration.

**On the STAGED path nothing leans on it at all**, because that filter is not
applied there (`gather_cv_lines` files raw `detect_lines` output). MEASURED
HERE (tree). Which of the two is better is unmeasured and is a real question:
the legacy path is protected against phantom stems and exposed to false
deletions; the staged path is the reverse.

**Independence:** none. The `arpeggiato` class and the CV stem reader see the
same ink on the same raster, and the legacy filter has one of them censoring
the other.

**Evidence grade:** the 377 / 769 / 99 counts MEASURED HERE; the height and
anchor distribution PROBE (n = 99, one publisher, one checkpoint, no print
adjudication); the Bravura 0.485 × 5.434 LITERATURE; the "stem rather than
barline" reading is a PROBE inference and **no box was checked against the
print**. Registry: none — `arpeggiato` has no convention entry, which is itself
worth noticing.

---

## `stringsUpBow` / `stringsDownBow`

The bowing marks. **1 detection on Litolff pp.1-4 (`stringsDownBow`)**; zero on
the probe page; zero in the labelled corpus.

### 1. What sets it apart — and what it is confused with

Bravura: `stringsDownBow` 1.248 × 1.272 staff spaces (a square bracket opening
downward), `stringsUpBow` 0.992 × 1.976 (a tall `V`). LITERATURE.

Confusable with: **a marcato** (`^`, 0.944 × 1.016 — the up-bow is a taller,
narrower version of the same idea), a **staccatissimo wedge**, and a **flag
fragment**. All ASSERTED; nothing has been adjudicated.

⚠️ There is a musical constraint nothing uses: a bowing mark only occurs on a
STRING staff. The instrument identity that would supply it is available
(`Q.INSTRUMENT`) and, on Litolff pp.1-4, abstains `no_evidence` on **75 of 75
staves** (`benchmarks/omr-part-join-phase2-2026-09/`), so the constraint is
unavailable exactly where the document needs it. MEASURED HERE.

### 2. Best method: YOLO / CV / other

Unknown — reach is 1. ASSERTED.

### 3. Where on the page the deciding information lives

Above the note, centred in x (the ornament's convention). And, for this mark
specifically, in the STAFF's identity, which is not read.

### 4. Stage by stage

**Nowhere.** No quantity, no adjudicator, no consequence, no export. It appears
in `_unclaimed_classes` and nowhere else. `yolo_detector._CATEGORY_MAP:144`
gives it category `ornament`; `gather_glyph_families` has no branch for it;
`_ORNAMENT_KINDS` does not list it; `FAMILIES` does not claim it;
`NOT_NOTATION` does not excuse it. **MEASURED HERE — this is a finding, stated
plainly.**

### 5. Abstain or best-guess — and what leans on this mark's certainty

**(a) It cannot abstain, because it is never asked.** **(b) Nothing.**

**Evidence grade:** the 1 detection MEASURED HERE; the 75-of-75 identity
abstention MEASURED HERE; everything else ASSERTED. Registry: none.

---

## `caesura`

The railroad tracks — two short parallel diagonal strokes on the top staff
line, meaning a break. **2 detections on the probe page** (confidence 0.357 and
0.793); one on an earlier Beethoven page
(`benchmarks/omr-staged-gather-2026-09/FINDINGS.md` §6); zero in the labelled
corpus.

### 1. What sets it apart — and what it is confused with

Bravura: 1.536 × 2.132 staff spaces. The PROBE's two boxes measure
**0.45 × 0.56** — a quarter the width and a quarter the height. Either the
detector is boxing ONE of the two strokes, or these are not caesuras. **PROBE,
n = 2** — too few to call, and the gap is large enough to be worth a crop.

Confusable with: a **staccatissimo wedge** (0.44 × 0.65 on the same page — the
probe boxes are almost identical), a **beam fragment**, a **flag**. ASSERTED.

### 2. Best method: YOLO / CV / other

Unknown — n = 3 in the repository. ASSERTED.

### 3. Where on the page the deciding information lives

**Its position on the TOP STAFF LINE, and its relation to a barline.** A
caesura sits at the top line, usually just before a barline, and applies to the
whole system rather than to a note — so it is the one mark in this family with
no owner at all. Nothing records that.

### 4. Stage by stage

**Nowhere.** Same as the bowings: category `ornament`
(`yolo_detector._CATEGORY_MAP:84`), no quantity, no decision, no export, no
excuse — reported in `_unclaimed`. MEASURED HERE.

### 5. Abstain or best-guess — and what leans on this mark's certainty

**(a)** Never asked. **(b)** Nothing. ⚠️ A caesura is a *structural* mark — it
breaks the flow of the system — and this pipeline has no representation for the
page's traversal order at all (`docs/exploration-what-is-on-the-page-2026-09-09.md`:
`volta` is not even in the class space, and *"the printed order is not the
playing order, and no part of either pipeline represents that"*).

**Evidence grade:** 2 detections and their boxes PROBE (n = 2); the Bravura
size LITERATURE; the absence from every stage MEASURED HERE. Registry: none.

---

## `keyboardPedalPed` / `keyboardPedalUp`

The piano pedal marks. **Zero detections on every document measured here**;
zero in the labelled corpus. Both are in the 208-class space (ids 110, 111).

### 1. What sets it apart — and what it is confused with

Bravura: `keyboardPedalPed` **4.076 × 2.252** staff spaces — by far the largest
glyph in this dossier, roughly a third the width of a short bar — and
`keyboardPedalUp` 1.800 × 1.800 (the `*`). LITERATURE.

**Confusable with printed TEXT**, which is what `Ped.` largely is: the
direction-text reader works on exactly that band under the staff, and its
lexicon would have to decide between reading the word and leaving it for the
detector. Nobody has looked. ASSERTED.

⚠️ **One measured trap involving `keyboardPedalUp` is on record and it is in
another family entirely.** A probe matching `startswith("key")` for key-signature
markers also caught `keyboardPedalUp` and reported 19 later-cell key markers
where there are 15 — *"the guard never reads a detection class, so no behaviour
depended on it"*, but a documented figure was wrong for it
(`tools/omr/key_signature_corroboration.py:44-52`). MEASURED HERE. It is the
family's contribution to the *prefix-matching a class space is dangerous*
lesson.

### 2. Best method: YOLO / CV / other

Unknown — zero reach. ⚠️ **And the reach is a property of the repertoire, not
of the detector**: every document in this repo's benchmark set is an orchestral
conductor's score. A piano score would have these on every page. ASSERTED.

### 3. Where on the page the deciding information lives

Below the staff, in the dynamics band, spanning a range of bars. It is a SPAN
mark like a hairpin, not a point mark — which is the same modelling problem
`<wavy-line>` has.

### 4. Stage by stage

**Nowhere.** Category `ornament` (`_CATEGORY_MAP:145`), no quantity, no
decision, no export, no excuse. MEASURED HERE.

### 5. Abstain or best-guess — and what leans on this mark's certainty

**(a)** Never asked. **(b)** Nothing.

**Evidence grade:** zero reach MEASURED HERE; the Bravura sizes LITERATURE; the
`startswith("key")` collision MEASURED HERE; everything else ASSERTED.
Registry: none.

---

## `tremolo1`–`tremolo5` — CROSS-REFERENCE ONLY

**The stems dossier owns this mark.** One paragraph, because it changes how the
rest of this family reads.

`tremolo1`-`5` ARE ornaments whose class names do not begin `ornament`, which
is why `gather_glyph_families` asks `_ORNAMENT_KINDS` instead of prefix-matching
(`gather.py:889-904`). They are wired end to end — gathered, adjudicated,
exported as `<tremolo type="single">N</tremolo>` — and **the detector produces
ZERO of them across 7,090 committed artifacts**, against a positive control of
34,115 detections. The label corpus carries **46 hand-drawn tremolo boxes the
checkpoint does not reproduce** (`tremolo2` ×15, `tremolo3` ×5 and others,
`benchmarks/omr-labeling-survey-2026-09/INVENTORY.md`). MEASURED HERE.

Three consequences for this dossier:

1. **The tenth export gap does not close**, and this is why: the eleven-work
   engraved truth's only ornaments are twelve `<tremolo>`.
   `ornamentTrill`/`Turn`/`Mordent` reaching the file moves it by exactly zero.
2. **A tremolo rides the STEM, so its class states no side** (`above=None`), and
   `adjudicate_ornament_owner` SKIPS the geometry test rather than guessing
   (`ownership.py:1207-1213`). It is the only mark here for which position is the
   only thing that could ever say which side it is on (`[C55]`).
3. **It is the reason `_ORNAMENT_MAX_DX_NOTEHEAD_WIDTHS` is 1.0 and not 0.75** —
   a tremolo stands on the stem, at the notehead's edge, so a constant tuned for
   a mark centred on the head is the wrong prior. That reasoning is sound and
   the constant is still unmeasured, and it now governs trills, turns and
   mordents, which ARE centred on the head. **A constant chosen for the one
   class that never fires is applied to the three that do.** MEASURED HERE
   (the code and its comment); the cost is unmeasured.

---

## What we do not know

1. **Whether any mark in this family is CORRECT.** Not one articulation,
   fermata or ornament has been adjudicated against the print in this repo. The
   articulation sweep scored placements against a truth MusicXML by INDEX
   (n = 218, precision 0.980) — that is placement accuracy given the class, not
   whether the class is right. The fermata arm says so explicitly: *"Nothing
   here compares a fermata against the print."*
2. **The split of the 34 lost Litolff articulations** across the four
   note-drop reasons. One join away, never done.
3. **Whether `arpeggiato`'s 377 are stems, barlines or arpeggios.** The probe
   says the height/anchor distribution is stem-like (9 of 99 pass the barline
   test), and no box has been looked at.
4. **Whether a staccatissimo, a caesura or a bowing mark would be read
   correctly**, because none has ever fired enough times to say. Reach is 7, 2
   and 1 respectively.
5. **Whether the class-name side is ever wrong.** `Q.ARTICULATION_POSITION`
   records the measured side beside it; the comparison has never been run,
   because it is a decision with a right to abstain and nobody has written one.
6. **What the `imgsz` downscale costs a 0.36-space staccato dot.** Nobody has
   swept it.
7. **Whether the staged path's missing phantom-stem filter costs anything.**
   Both directions of that trade are unmeasured.
8. **A second publisher for the fermata.** Litolff prints 63 on three pages,
   Breitkopf prints none on four. n = 1 document.
9. **How often a fermata lands in the cell of the staff above** with no contest
   to arbitrate it. Measured for noteheads, never for fermatas.

## Questions for Sean

1. **`arpeggiato`, 377 boxes on four pages.** The probe says most are 3.24
   staff spaces tall, starting on the top line and ending inside the staff —
   more stem-shaped than barline-shaped. Before anything is built: on a Litolff
   Beethoven 5 page, does the plate print arpeggios at all? If it prints none,
   the whole 377 is a detection fault and the repair is upstream; if it prints
   some, we need a rule and the rule is *what stands to its right*.

2. **The tenuto and the ledger line are the same box** (1.8-2.0 × 0.30 against
   2.02 × 0.29, and confidences that overlap). The confusables doc says the
   separator is *on the lattice or off it*, and that test is computable today
   from things already on the record. Is it worth building — given that the
   error lands in notehead ownership, not in a missing tenuto — or is a tenuto
   rare enough on this repertoire that we should just say so?

3. **Six classes have no quantity at all**: `arpeggiato`, `caesura`,
   `stringsUpBow`, `stringsDownBow`, `keyboardPedalPed`, `keyboardPedalUp`.
   Reach today is 377, 3, 1, 0, 0, 0 on everything measured. Do you want any of
   them wired now, or should they stay in `_unclaimed` — where they are
   reported by name and cost the human nothing, because nothing reaches the
   file?

4. **`_ORNAMENT_MAX_DX_NOTEHEAD_WIDTHS = 1.0` was chosen for the tremolo**,
   which rides the stem and never fires, and it now governs trills, turns and
   mordents, which are centred on the head like an articulation. Should the
   trill family inherit the articulation's measured 0.75 instead, and leave 1.0
   for the tremolo if it ever fires? That is a one-line split with a stated
   reason on each side.

5. **The fermata and the staff above's dynamics compete for the same gap.**
   The registry names it; nothing arbitrates it. We know 24% of dynamic letters
   land in the band of the staff immediately above. Is a fermata printed high
   enough above its own staff to be inside that band on a conductor's page, or
   does the engraver keep them apart?

6. **Is a staccatissimo's wedge really as short as the detector draws it?**
   Bravura draws 0.40 × 1.18 staff spaces; the seven boxes on Breitkopf
   Brahms 1 measure 0.44 × 0.65. Either Breitkopf prints a shorter wedge or we
   are clipping the tail — and which it is decides whether height can separate
   a staccatissimo from a staccato at all.

7. **The legacy path deletes a CV stem that sits inside an ornament box; the
   staged path does not.** On a plate producing 377 false `arpeggiato`, the
   legacy rule is deleting real stems and the staged one is keeping phantom
   ones. Which error would you rather have while we work this out?
