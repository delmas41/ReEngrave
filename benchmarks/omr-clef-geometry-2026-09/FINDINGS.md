# Clef-sized ink at the header is the clef — ROADMAP 2.11

**Path:** STAGED. **Date:** 2026-09-23. **Branch:** `claude/clef-geometry-2.11`.
**Convention:** registry entry `C88` (`docs/engraving-conventions.md`),
`docs/DECISIONS.md` 2026-09-23.

Sean, looking at the Litolff Viola crop:

> *"it also looks like the clef box is too small. the size of clefs are
> consistent to the staff and the edge of the first measure on the system —
> that should be helpful geometrically."*

The staff this fixes is the one
`benchmarks/omr-notehead-funnel-2026-09/FINDINGS.md` measured: Litolff
Beethoven 5 p.3 Viola, **48 noteheads boxed and 0 written**, 40 of them
refused `no_pitch` because the clef abstained.

## The result, in one line

On the Litolff count page `staff/3/0/9`'s clef goes **ABSTAINED
`no_candidates` → DECIDED `alto` `scored`**, its `no_pitch` refusals go
**40 → 0**, it writes **0 → 35** of its 48 boxed noteheads, the two detector
boxes standing on the clef are refused **`is_a_clef`**, and **0 of the 19 clef
verdicts the page already READ changed**. On Brahms 1 p.6 a second staff is
newly read (`staff/6/0/9`, alto) and **one already-READ clef changed** —
`staff/6/1/3`, treble → tenor — which §4c shows is very probably a correction
and which is **not adjudicated**.

---

## 1. Priced off the records FIRST — no gather

`probe/price_occupied.py`, read-only, over the three acceptance documents'
records named in `benchmarks/acceptance/manifest.json`:

```
python3 benchmarks/omr-clef-geometry-2026-09/probe/price_occupied.py \
    --only beethoven5-litolff \
    --out-json benchmarks/omr-clef-geometry-2026-09/out/occupied-reach-litolff.json
#   ... --only brahms1-breitkopf   --out-json .../occupied-reach-breitkopf.json
#   ... --only beethoven5-engraved --out-json .../occupied-reach-engraved.json
```

### 1a. The MEASURED height band, per family, per document

⚠️ **The roadmap's prose band was a guess; this is the measurement.** The
heights below are of every clef the CV locator **successfully read**, in staff
spaces.

⚠️ **The `cell:0` arm only, and the reason is arithmetic, not taste.**
`Q.CLEF_LOCATED.bbox` is in its own crop's canonical pixels and the record
carries `Q.CELL_STAFF_SPACE` for cell 0 and **nothing for the header-window
crop**. Dividing a header-frame bbox by cell 0's spacing produces heights
**above the locator's own `max_height_spaces` of 5.0** — 6.74 on Litolff, 9.05
on Breitkopf — arithmetically impossible for a cluster the locator accepted,
which is the tell that the divisor is wrong. Those rows appear in the JSON
under `… (header*)` and gate nothing. 2.11 closes the gap for the future by
recording `w_spaces`/`h_spaces` on the read itself.

| document | family | n | min | max | median |
|---|---|--:|--:|--:|--:|
| Litolff | alto | 13 | 3.73 | 4.63 | 4.45 |
| Litolff | tenor | 9 | 3.36 | 4.55 | 4.41 |
| Breitkopf | alto | 46 | 3.91 | 4.50 | 4.32 |
| Breitkopf | tenor | 14 | 4.04 | 4.36 | 4.27 |
| engraved | alto | 3 | 4.09 | 4.09 | 4.09 |
| **pooled** | **C-clef family** | **85** | **3.36** | **4.63** | **4.32** |

**Shipped band: 3.3 – 4.7 staff spaces**
(`ClefLocatorConfig.clef_family_min/max_height_spaces`), the pooled min/max
rounded outward to one decimal.

⚠️ **THE LOCATOR IS A C-CLEF LOCATOR, so it cannot measure the other two
families at all** — a treble-sized cluster is `too_big` and stops the search
before anything else runs. The roadmap's `treble ≈ 7–8` and `bass ≈ 3.5–4`
are therefore unmeasurable from this reader. They are measurable from a
**different** one, and the probe reports it: the height of every **detector**
clef box, same unit, same records.

| document | `clefG` | `clefF` | `clefCAlto` | `clefCTenor` |
|---|---|---|---|---|
| Litolff | n=296, med **7.19** | n=77, med **3.54** | n=8, med 4.39 | n=3, med 4.51 |
| Breitkopf | n=728, med **6.84** | n=230, med **3.46** | n=48, med 4.13 | n=35, med 4.19 |
| engraved | n=39, med **6.96** | n=15, med **3.33** | n=3, med 3.98 | — |

Two independent readers agreeing on the same geometry, plus a third source:
`C23`'s own **Numbers** row gives Bravura's `cClef` as **4.048** staff spaces,
inside the band.

⚠️⚠️ **THE SAME TABLE CARRIES THE RULE'S SHARPEST HAZARD.** `clefF`'s median
is **3.46–3.54**, i.e. **inside** the shipped 3.3–4.7 band. A bass clef's ink
is C-clef-sized on all three documents. What keeps this from turning bass
clefs into alto clefs is **the F-clef dot veto**, which 2.11 does not touch
and which still runs after the override — the settled finding CLAUDE.md
records at length (48 → 21 → 13 → 5 false positives), and the reason the
override was placed *in front of* the shape gates rather than instead of them.

### 1b. The reach — how many staves 2.11 could newly read

An `occupied` abstention is filed **per crop**, so a staff can carry two; the
reach is counted in **staves**, because a staff has one clef.

| | Litolff | Breitkopf | engraved |
|---|--:|--:|--:|
| `clef_located` abstentions on the `occupied` branch | **47** | **27** | **0** |
| …on how many staves | 27 | 17 | 0 |
| staves whose cluster is in the **config** band (2.2–5.0) | 27 | 17 | 0 |
| staves whose cluster is in the **measured** band (3.3–4.7) | **25** | **9** | 0 |
| …with a notehead box found overlapping it | 25 | 9 | 0 |
| **…whose `clef` verdict ABSTAINED** ← 2.11's reach | **8** | **0** | **0** |
| …whose `clef` verdict was NARROWED | 9 | 1 | 0 |
| …whose `clef` verdict was already DECIDED ← the risk | 8 | 8 | 0 |

**2 of 47 / 8 of 27 `occupied` clusters fall outside the measured band and
keep their veto**, which is why the band is narrower than the locator's own
accept bounds: if the two were equal the veto would be dead code for the only
class that can ever raise it (rule 7 — a control must be able to fail).

The 8 Litolff staves 2.11 would newly read, with their cluster heights:

```
staff/2/1/9  [4.32]        staff/3/0/9  [4.50, 4.50]   ← the funnel's staff
staff/5/0/7  [4.14, 4.14]  staff/5/1/5  [4.45, 4.82]
staff/7/0/9  [4.55]        staff/7/1/9  [4.00, 4.00]
staff/15/0/9 [4.45, 4.45]  staff/16/1/9 [4.45, 4.45]
```

⚠️ **Six of the eight are staff index 9 on a full system — the Viola.** This
is not eight unrelated faults; it is one plate's alto clef merging into its
own staff lines, eight times.

⚠️ **The Breitkopf reach of 0 is the PREDICTION and §4c refutes it.** The
prediction is taken off the whole-movement record, in which `staff/6/0/9`'s
clef is DECIDED alto; on a one-page re-gather the same staff ABSTAINS on base
and is newly read by the arm. A record is a snapshot of the reader that made
it, and a page-scoped run has less cross-system evidence than a 27-page one.
So the true reach is "at least 8 + 1", and the whole-document figure is the
floor rather than the answer.

### 1c. Sean's x-consistency check — measured, and NOT built

Sean named a third condition: the cluster should sit at *"the x the system's
other staves' clefs share"*. It is measured here and was **not built**,
because the measurement says it would discriminate nothing on this corpus:

* over **all 74** `occupied` abstentions on the two scans, the cluster's
  page-frame x sits **−60 to +3 page px** of the median x of the same
  system's other staves' detector clef boxes;
* those siblings' own x spread is **3–17 px** (Litolff) and **8–38 px**
  (Breitkopf) on all but three systems (180–255 px, systems carrying a
  mid-staff clef change).

Every cluster that reaches the occupancy test is *already* at the clef x,
because `header_frac` (0.30 of the cell) and `max_start_spaces` (6.0) bound it
there first. A SYSTEM-scoped x-band quantity would have added a producer, a
consumer and a scope to separate **zero** cases. The numbers are in
`out/occupied-reach-*.json` under
`cluster_x_vs_sibling_detector_median_page_px`.

⚠️ And on Litolff p.3 system 0 **not one staff has a `clef_located` row at
all** — the other ten read their clefs from the detector. A sibling x taken
only from the locator is empty exactly where 2.11 needs it, which is why the
probe reads `Q.GLYPH_BOX`'s `x_center_page` on clef-class boxes instead.

---

## 2. The change

Three files, no new quantity, no new flag.

**`tools/omr/clef_locator.py`** — `_overridable_occupancy`. A cluster that has
already passed the size, ink, margin and start-x gates is no longer vetoed by
a box on it when **all four** hold, and each can fail:

1. the caller supplied `occupied_classes` (opt-in — see below);
2. every overlapping box is **notehead-class**;
3. every overlapping box is **notehead-SIZED**, i.e. its own height is below
   the clef band's floor — *"the clef box is too small"* made a test. A box
   that is itself clef-sized is not obviously the error and keeps its veto;
4. **the detector drew NO clef box on this ink** — see §4c; this condition was
   added by the measurement, not by the design.

and the cluster's own height is inside the measured band. The symmetry gate,
the **F-clef dot veto** and the line snap all still have to agree: the
occupancy test was a cheap short-circuit *in front of* them, and this removes
the short-circuit for one named population only.

⚠️ **THE FROZEN PATHS DO NOT MOVE, BY CONSTRUCTION.** `occupied_classes` and
`clef_boxes` are new keywords; omit them and the call is bit-identical.
`transcribe.py` (FROZEN, CLAUDE.md §3) and `key_signature_locator.py` both
omit them. `_occupied_boxes` in `gather.py` is left byte-for-byte alone for
the same reason, and a clef box **refuses the override without ever becoming
a veto of its own** — so nothing that reads today stops reading.

**`tools/omr/staged/gather.py`** — `_occupied_notehead_rows` carries the class
and the **glyph subject** of each box beside its geometry (the detector
ordinal *is* the glyph subject's last coordinate, so the identity is exact,
not reconstructed). `_clef_boxes` supplies condition 4 using
`_is_clef_class`, the same predicate `gather_clef` uses, so the two cannot
disagree about the same box. A read that overrode boxes NAMES them on its
`Q.CLEF_LOCATED` row (`overrides_notehead_box`, `overrode_glyph_subjects`),
and the row now also records `w_spaces` / `h_spaces`.

**`tools/omr/staged/adjudicators/notehead_precision.py`** — a fourth rule,
`is_a_clef`, first in the order. It **measures nothing**: it reads the
subjects the clef read itself named, at `Scope.SELF_AND_ANCESTORS` (the row is
filed on the STAFF, and at the default `EXACT` a GLYPH query would return
nothing and fail silently). A CONNECT, not a guess — the refusal and the read
cannot disagree. It does **not** consult the staff's `clef` verdict: that is
an ADJUDICATE product of the same stage, and a located clef that loses the
clef contest still tells us what this ink is.

---

## 3. Tests, run RED first

`tools/omr/tests/test_clef_over_notehead_box.py`, against the **unmodified**
tree: **13 failed, 3 passed.** The 3 that pass on both trees are the
refusal's own positive controls. Green on the arm: **19 passed** (16 at the
first build + 3 for condition 4).

```
python3 -m pytest tools/omr/tests/test_clef_over_notehead_box.py -q
```

Positive controls, each a way for 2.11 to fail: a cluster **outside** the
band still vetoes · a **non-notehead** occupying box still vetoes · **one**
non-notehead among noteheads still vetoes · a box that is **itself clef-sized**
still vetoes · **a detected CLEF on the same ink** still vetoes · a detected
clef **elsewhere** does not refuse the override · a clef box is **never a veto
of its own** · a caller supplying **no classes** is unchanged · a notehead
**elsewhere** was never a veto · a clef read that overrode **nothing** refuses
nothing · a notehead **elsewhere on the staff** is untouched by the refusal.

⚠️ No source-text assertions: every test drives the real `locate_clef` over a
drawn cell or the real adjudicator over a real `Log`. The fixture clef is
drawn at **4.2 spaces** because the module's existing one is 2.6 — inside the
locator's accept bounds and *outside* the measured clef band, which makes it a
perfect negative control and useless as the positive one.

### The suite and the checks

| | |
|---|---|
| `pytest tools/omr/tests -m "not slow" -q` | **2,842 passed, 3 skipped** — 2,823 on the base tree plus the 19 new tests, arithmetic checked rather than assumed |
| `python3 -m tools.omr.staged.check` | **255 open, status ok** — and **255 on the base tree too**, measured by restoring the three files from `HEAD` and re-running. **No finding added.** |
| `inventory --check` / `wiring --check` | exit **0** / exit **0** |
| `python3 -m tools.omr.conventions --check` | **0 findings**, 115 entries |

⚠️ **TWO `test_conventions.py` MUTATION TESTS WERE VACUOUS-BY-LITERAL AND ARE
REPAIRED.** They mutate the string `| **MEASURED HERE** | 67 |`; `C88` takes
that count to 68, so `str.replace` silently matched nothing, the "broken"
document was the real one, and the tests failed with an **empty problem set**.
The count is now derived from the parsed entries and the target asserted to
exist — the guard the DUPLICATE SLUG test beside them already carried. The
tree's own recurring bug class arriving inside a mutation test.

---

## 4. The measurement — base vs arm, one real re-gather per page

A **GATHER** change is invisible to `readjudicate` and `reexport_arm`
(CLAUDE.md §4d); only a full re-gather prices it. `probe/run_ab.sh` runs the
reader twice on one page, restoring the three changed files from the commit's
parent for the base arm and asserting the tree is clean again before the arm
arm starts. `probe/run_arm.sh` re-runs the arm alone against an unchanged
base.

```
bash benchmarks/omr-clef-geometry-2026-09/probe/run_ab.sh febd383a~1 <pdf> <page> <tag>
python3 benchmarks/omr-clef-geometry-2026-09/probe/compare_ab.py \
    --base <out>/base-<tag>.record.json --arm <out>/arm-<tag>.record.json \
    --subject staff/3/0/9 --out-json <out>/ab-<tag>.json
python3 benchmarks/omr-notehead-funnel-2026-09/probe/funnel.py \
    --record <out>/{base,arm}-litolff-p3.record.json --page 3 --system 0 --staff 9 \
    --musicxml <out>/{base,arm}-litolff-p3.musicxml \
    --out-json <out>/funnel-{base,arm}-p3-s0-st9.json
```

`--no-surya --no-ocr`: nothing here touched the shared Surya/llama server, and
nothing was started or stopped. The per-staff head count is **funnel.py's**
question and is quoted from it rather than recomputed — a second copy of "the
refusal buckets" is the mistake `omr-cleanup-count-2026-09/build_sheet.py`
already paid for. Its control ran and PASSED on both arms.

### 4a. Litolff, pdf page 3 (the count page) — every gate

| gate | base | arm | |
|---|---|---|---|
| `staff/3/0/9` `clef` | ABSTAINED `no_candidates` | **DECIDED `alto` `scored`** | ✅ |
| clef verdicts on the page | 19 | 19 | |
| clef verdicts CHANGED | — | **1** (the one above) | |
| **READ clefs CHANGED** (gate: 0) | — | **0** | ✅ |
| `no_pitch` refusals on the page | **40** | **0** | ✅ |
| noteheads written on `staff/3/0/9` | **0 of 48** | **35 of 48** | ✅ |
| `pitch_decided` on `staff/3/0/9` | 3 | **48** | |
| boxes refused `is_a_clef` | 0 | **2** | ✅ |
| `status_census.unaccounted` | `[]` | `[]` | ✅ |
| export balance (`to_musicxml` RAISES if not) | balanced | balanced | ✅ |
| notes written, whole page | 326 | **361** (+35) | |
| empty bars padded, whole page | 58 | **49** (−9) | |

The two refused boxes are exactly the pair the roadmap named:
`glyph/3/0/9/0/1` `noteheadBlackOnLine` **conf 0.6419** and `glyph/3/0/9/0/6`
**conf 0.3641**, at page px x 388–416, y 1828–1862. Both `clef_located` arms
fired — `header_window` at symmetry 0.823, `cell:0` at 0.847 — and each named
the same two glyph subjects.

**The whole-page refusal ledger moves in exactly three places**, and the third
is the interesting one:

```
base  {duration_narrowed: 70, too_narrow: 6, ink_is_a_whole_rest: 5,
       clipped_fragment: 17, owned_by_another_staff: 10, no_pitch: 40}
arm   {duration_narrowed: 73, too_narrow: 6, ink_is_a_whole_rest: 5,
       clipped_fragment: 17, owned_by_another_staff: 10, is_a_clef: 2}
```

`duration_narrowed` **70 → 73**: the Viola's three NARROWED duration verdicts
at printed bar 51 were previously hidden behind `no_pitch` (the buckets are
ORDERED and a head is counted under the FIRST test it fails). They did not
appear; they **surfaced**. The funnel's own upper bound — *"37 of the 48 would
be written if the clef were decided"* — lands at **35**, which is 37 minus the
two boxes that turned out to be the clef itself.

### 4b. Breitkopf, pdf page 1 — the count page, and it is INERT

Brahms 1 pdf page **1** carries **0** `occupied` clef abstentions of any kind,
so the arm has nothing to move there. It was run anyway, and the result is a
**byte-identical refusal ledger**: 27 clef verdicts, **0** changed, **0**
overrides, **0** `is_a_clef`, 608 notes written on both arms,
`status_census.unaccounted` `[]` on both.

⚠️ **That zero is a no-change control, not a result.** CLAUDE.md §6b: *an arm
that moves nothing because it is inert and one that moves nothing because the
page holds nothing to move are the same number.* The reach on this page is
zero by construction, which is why page 6 was gathered as well.

### 4c. Breitkopf, pdf page 6 — the risk test, and the gate FAILS on one staff

Page 6 carries §1b's dangerous population. Result:

| | base | arm |
|---|---|---|
| clef verdicts on the page | 23 | 23 |
| clef verdicts CHANGED | — | **2** |
| **READ clefs CHANGED** (gate: 0) | — | **1** ❌ |
| overriding `clef_located` rows | 0 | 3 (2 staves) |
| boxes refused `is_a_clef` | 0 | 11 |
| `no_pitch` refusals | 122 | **77** |
| `not_a_notehead:too_narrow` | 385 | 378 |
| notes written, whole page | 385 | **421** (+36) |
| `status_census.unaccounted` | `[]` | `[]` |

* `staff/6/0/9` — **ABSTAINED `no_candidates` → DECIDED `alto`**, symmetry
  0.976, cluster 4.27 spaces, 3 boxes refused. `Q.CLEF_GLYPH` ABSTAINED
  `no_detections`: the detector saw no clef there at all. This is the Litolff
  fault on a second publisher.
* `staff/6/1/3` — **DECIDED `treble` → DECIDED `tenor`.** ❌ **The gate says 0
  READ clefs may change, and this is one.**

**What the evidence says about that staff, and it is not "the rule is wrong".**
The base's `treble` rests on a single `clefG` box at confidence 0.688 whose
`Q.CLEF_POSITION` is **19.36 half-steps below the top line** — i.e. about 5.7
staff spaces BELOW the bottom line, off the staff entirely. On the same page a
real treble clef reads `clef_position` **4.05** (`staff/6/1/4`, conf 0.900)
and **4.14** (`staff/6/1/5`, conf 0.945). It is a neighbouring staff's clef
bleeding into this staff's padded cell — the exact hazard `gather_clef`'s own
comment describes and files as *"RECORDED, NOT ACTED ON"*.

⚠️ **AND THE CROP SETTLES WHAT IS PRINTED, THOUGH NOT THE LINE.**
`out/print/breitkopf-p6-s1-st3-tenor-cell0.png`: the plate prints an
unmistakable **C clef** at that header, not a G clef. So the arm's read looks
like a **correction of a wrong `treble`**, not a regression — but *which* C
clef (alto vs tenor) is a line question this lane has NOT adjudicated, and the
sidecar carries `"VERDICT_none_yet": null`. **The gate is reported FAILED, not
argued away.** Sean settles it.

⚠️ **Condition 4 does not fire here, correctly.** The `clefG` box is 5.7
spaces off the staff and therefore does not overlap the cluster. Gating on
"any clef box anywhere in the cell" would silence 2.11 on most staves of a
conductor's page, where a neighbour's clef is in the padding by design; that
would be a blunt, unmeasured widening and it was not made.

⚠️ **A second finding this page hands to another lane, unfixed here:** a
`clefG` at `clef_position` 19.36 supported `treble` at 3.0 unopposed.
`Q.CLEF_POSITION` is gathered, is on the record, and `adjudicate_clef` does
not use it to discount an off-staff clef box. That is the tree's recurring
*the value existed and nothing read it*, in the clef contest.

---

## 5. The crops — for Sean, nothing adjudicated

`out/print/` (deliberately not `crops/`, which `.gitignore` excludes), cut
from the plate at the **gather's own DPI** read off the record's provenance
(600), zoom 4, behind `crop_inferred._frame_ok` **imported rather than
copied**. Five crops, two manifests.

| crop | frame | read | symmetry | overrode | frame contrast |
|---|---|---|--:|--:|--:|
| `litolff-p3-s0-st9-alto-cell0.png` | `cell:0` | alto | 0.847 | 2 | 152.5 |
| `litolff-p3-s0-st9-alto-header_window.png` | `header_window` | alto | 0.823 | 2 | 152.5 |
| `breitkopf-p6-s0-st9-alto-cell0.png` | `cell:0` | alto | 0.976 | 3 | — |
| `breitkopf-p6-s1-st3-tenor-cell0.png` | `cell:0` | tenor | 0.926 | 7 | — |
| `breitkopf-p6-s1-st3-tenor-header_window.png` | `header_window` | tenor | 0.927 | 4 | — |

GREEN = the staff's five `Q.STAFF_LINES`, so the crop says **which** staff it
is about (Sean's own correction of 2026-09-23) · BLUE = the ink cluster read
as the clef · RED = the detector notehead boxes the read overrode and the
exporter now refuses `is_a_clef`.

⚠️ **The BLUE box is drawn only on a `cell:0` crop.** A `header_window` bbox
is in a crop whose canonical spacing the record does not carry, so there is no
exact route to page pixels — DECLINED rather than approximated, because an
approximate box drawn on a plate for a human to adjudicate is worse than no
box (CLAUDE.md §6b). The sidecar says so per crop.

`MANIFEST-*.json` and every sidecar carry **`"VERDICT_none_yet": null`**.
Nothing in 2.11 has been adjudicated against the print.

---

## 6. Caveats, and what this does NOT establish

1. **THE ROADMAP GATE IS NOT FULLY MET.** *"0 READ clefs changed on the three
   documents"* holds on Litolff p.3 and Brahms p.1 and **fails on Brahms p.6**
   (`staff/6/1/3`, treble → tenor). §4c gives the evidence that it is probably
   a correction; it does not make it one.
2. **NOTHING IS PRINT-ADJUDICATED.** The crops exist so Sean can settle three
   questions: is `staff/6/1/3` a C clef and on which line; are the 11
   `is_a_clef` refusals all really clef ink; is the Litolff Viola alto.
3. **n = 3 documents, 2 publishers, 1 era.** The band is 85 clefs on two
   19th-century orchestral plates and one Verovio render. `C88`'s **Would be
   falsified by** row is the test.
4. **The whole-document reach is PREDICTED, and §1b shows the prediction is a
   FLOOR, not the answer.** §1's numbers come from the committed whole-movement
   records, which are snapshots of the reader that made them
   (`provenance.dirty: true` on the Litolff one — per CLAUDE.md §4b it is not
   a baseline). Only pages 3, 1 and 6 were re-gathered. Breitkopf was predicted
   to gain 0 staves and gained 1 on the one page that was run.
5. **A bass clef is C-clef-sized** (§1a). Nothing in 2.11 protects against
   that; the F-clef dot veto does, and it is untouched but not re-measured
   under the override beyond the two out-of-band bass staves on page 6.
6. **`_occupied_boxes`'s frame is not this lane's, and it is wrong.** For the
   `header_window` arm the locator compares a header-crop cluster against
   **cell 0's** canonical boxes, scaled by the header crop's spacing rather
   than their own. That predates 2.11 and is unchanged by it; `_clef_boxes`
   inherits it. Both arms agreed on every staff measured here.
7. **The refusal fires on the READ, not on the VERDICT.** If a future clef
   contest rejects an overriding `clef_located` row, the boxes it named are
   still refused `is_a_clef`. Deliberate (the ink is still a clef), and a
   claim a print pass could refute.
8. **The three derived-check blind spots apply** (CLAUDE.md §4d): none of them
   sees a GATHER change, none sees the DETECTOR, and `wiring` matches a detail
   key by bare name. `check` reporting 255 on both sides says nothing about
   whether this change is right.

---

# `adjudicate_clef` discounts an off-staff detector box — ROADMAP 2.11b

**Path:** STAGED. **Date:** 2026-09-28. **Branch:** `claude/clef-offstaff-2.11b`.

2.11's own second finding, unfixed there: on Brahms 1 p.6 `staff/6/1/3` a
single `clefG` detector box at `Q.CLEF_POSITION` 19.36 (~5.7 staff spaces
below the bottom line — a neighbour's clef bleeding into this staff's padded
measure cell) decided `treble` UNOPPOSED. `Q.CLEF_POSITION` was gathered, was
on the record, and `adjudicate_clef` never read it to discount the box — "the
value existed and nothing read it," in the clef contest this time.

## 7a. Measured first, per family, off the three acceptance records

`probe/price_position_bands.py`, read-only, `positional_store.
stream_observations` (never `record_io.load_record` on the 314/478 MB
shared records — this machine was running a concurrent heavy re-gather the
whole time this lane measured and landed, peaking near 63/68 GB used, and
streaming keeps peak RSS under 30 MB per document against reconstructing the
whole file). Every DETECTOR `Q.CLEF_GLYPH` row matched to its `Q.CLEF_POSITION`
row by `(subject, y_center)` — the same join `adjudicate_clef._on_staff_rows`
already performs per staff, done here once across a whole document:

| document | family | n | min | max | median | widest gap (low side) | widest gap (high side) |
|---|---|--:|--:|--:|--:|---|---|
| Litolff | G | 296 | −12.44 | 19.10 | 4.24 | (−5.548, 2.603) w=8.151 | (7.56, 13.303) w=5.743 |
| Litolff | F | 77 | 1.42 | 5.42 | 3.44 | none below −2 | none above 10 |
| Litolff | C | 11 | 1.82 | 6.10 | 4.12 | none below −2 | none above 10 |
| Breitkopf | G | 728 | −11.44 | 19.58 | 4.14 | (−4.190, 3.487) w=7.678 | (7.583, 12.92) w=5.337 |
| Breitkopf | F | 230 | −11.60 | 15.32 | 3.25 | (−7.023, 2.014) w=8.443¹ | (3.578, 12.982) w=9.404 |
| Breitkopf | C | 83 | 1.71 | 15.38 | 3.99 | none below −2 (min 1.71) | (6.229, 13.967) w=7.738 |
| engraved | G | 39 | −11.29 | 4.34 | 4.31 | (−11.139, 4.276) w=15.415 | none above 10 |
| engraved | F | 15 | 3.35 | 3.40 | 3.38 | none | none |
| engraved | C | 3 | 3.99 | 4.07 | 4.04 | none | none |
| **pooled** | **G** | **1,063** | −12.44 | 19.58 | 4.17 | contains −2.0 | contains 10.0 |
| **pooled** | **F** | **322** | −11.60 | 15.32 | 3.30 | contains −2.0 | contains 10.0 |
| **pooled** | **C** | **97** | 1.71 | 15.38 | 4.00 | (no negative outliers) | contains 10.0 |

¹ the pooled negative-side F gap (`(−7.023, 1.42)` w=8.443) is WIDER than
Litolff's own — Litolff's F never produces an off-staff outlier at all
(its lone low/high stragglers, 1.42 and 5.42, sit comfortably inside
[−2, 10]), so it contributes no boundary on that side; Breitkopf's does.

**n = 1,482 matched glyph/position pairs, all three acceptance documents.**
1,063 + 322 + 97 = 1,482, confirmed against the pooled totals above.

⚠️ **C is not one peak "on its line" — it is TWO**, tenor's (~1.7–2.6) and
alto's (~3.6–6.2), which is 3.4f's own `CLEF_BY_FAMILY_LINE["C"]` table
measured a second, independent way rather than a single band "on its line"
as this item's own brief assumed going in. Neither cluster is off-staff; the
brief's assumption was corrected by the measurement, not confirmed by it.

**The cut is not a new number.** In every document/family cell that produced
an off-staff outlier at all, the boundary the shipped
`ON_STAFF_MIN_STEPS`/`ON_STAFF_MAX_STEPS` (−2.0 / 10.0, roadmap A-CLEF-8,
`clef.py` line ~127) already draws falls INSIDE the measured gap — −2.0 sits
inside every negative-side gap above that exists, 10.0 inside every
positive-side gap that exists — and no genuine on-staff reading, of any
family, on any of the three documents, sits outside it. A second, narrower
band here would drift from that one the moment either was retuned, so the
discount reuses `_stands_on_this_staff`, the same predicate the
`stands_on_this_staff` BONUS term already trusted, rather than restating the
band a third time (CLAUDE.md, "derive it, don't re-list it").

## 7b. The repair

`_off_staff_discount_applies(row, on_staff)` (`clef.py`), a single named
function factored out of `_detector_terms` so a measurement can disable
exactly this rule: `on_staff is False` (a grid measured this box's position
and it falls outside the band above) **and** the row's reader is not one of
`_HUMAN_CLEF_READERS` (roadmap 3.4f's population — a human's own G/F clef box
reaches `_detector_terms` too, since `_clef_of` names G/F/percussion by class
regardless of who drew the box, and geometry does not get to overrule a
person's own reading any more than it overrules his C-clef class choice).

A discounted row is added to `discounted`, NOT to `candidates` — it stays in
`basis` (the row was still read, via `ev.rows(Q.CLEF_GLYPH)`), it is never in
`used`, and it is named `clef_box_off_the_staff` in the verdict's `detail`
(both on a `scored` decision, so `trace` shows every box that did not get to
vote, and on the `no_candidates` abstain path, so an abstention that was
caused by a discount says so rather than looking like silence). If a staff's
ONLY detector evidence is discounted, `candidates` ends up empty exactly as
if nothing had been detected there, and the staff ABSTAINS `no_candidates` —
the existing gap machinery (2.10's `clef_from_other_systems`, then INFER's
`fill_clef_gap`) is what may fill it afterward; `adjudicate_clef` itself
never defaults to treble (rule 8).

This REVERSES `_detector_terms`'s own prior design comment ("ADDITIVE, NOT A
FILTER... it would be the wrong call where a staff's only candidate stands
off it"), which was correct the day it was written and stopped being correct
once roadmap 2.10 gave an abstained clef somewhere else to land. The old
comment and the test that pinned it
(`test_staged_clef.py::TestAGlyphStandingOnANeighbouringStaff::
test_a_lone_glyph_standing_OFF_the_staff_is_still_the_best_evidence`) are
both updated in place, not deleted, with a docstring explaining which half
of the original finding is still true (an off-staff box IS still read, still
in `basis`) and which half this item closes (it may no longer decide alone).

## 7c. RED, then GREEN

`tools/omr/tests/test_staged_clef_offstaff.py`, written first and run
against the unrepaired tree (`clef.py` restored to `origin/main`'s copy,
`_off_staff_discount_applies`/`OFF_STAFF_REASON` do not exist there):

    5 failed, 0 passed

All five fail via `AttributeError` on `clef_mod.OFF_STAFF_REASON` (three) or
on the outcome/reason assertion itself (two — the lone-off-staff-box case
still DECIDES `treble` pre-fix, and the beside-a-normal-box case still shows
no discount), counted RED all the same (3.4f's own precedent, `test_
staged_clef_human_box.py` D1). After the fix, the same file:

    5 passed

The positive control (`TestThePositiveControlCanFail`: the SAME `clefG` at
its measured normal position, 4.3, still decides `treble`) is the control
that can fail — it is exactly the fixture the RED run above exercises with
one field changed (19.4 → 4.3), and it passes both before and after this
change, proving the discount is keyed on the POSITION, not on the glyph or
the family. The human-reader test (`TestAHumanRowIsNeverDiscounted`) uses a
deliberately high score to isolate one thing in the "coherence, not
accuracy" idiom this suite already uses: had the reader exemption not been
checked, the SAME off-staff position would have been discounted exactly as
it was for the detector case, and the staff would abstain instead of
deciding — it does not.

`tools/omr/tests/test_staged_clef.py`'s own pre-existing test
(`test_a_lone_glyph_standing_OFF_the_staff_is_still_the_best_evidence`,
§7b) was itself testing the behaviour this item reverses and is updated,
not left to fail silently — renamed `..._now_ABSTAINS`, asserting the new
outcome and the discount's presence in `detail`, `basis`, and absence from
`used`.

Full fast tier, before and after: **3399 passed, 3 skipped** both times
(244 s). `staged.check`: **253 → 253**, byte-identical TOTAL — this change
reads a quantity (`Q.CLEF_POSITION`) already in `adjudicate_clef`'s `wants=`
and already read (by `_on_staff_rows`, called from the pre-existing bonus
term), and returns only the `reason="scored"`/`"no_candidates"` the
decision already declares, so no `wants=`/`reasons=` update was needed —
`inventory --check` and `wiring --check` are unaffected by construction, not
merely observed clean.

## 7d. Measured on the saved records — ADJUDICATE-only, no GATHER

`probe/readjudicate_offstaff.py` (the same GATHER-ONCE-ADJUDICATE-TWICE
idiom `omr-key-majority-2026-09/readjudicate.py` used for roadmap 2.9:
rebuild a `Log` from a saved record's raw `observations`/`abstentions`,
`adjudicate.run` + `evaluate.run` + `infer.run` + the bounded second
`evaluate.run_over` — `pipeline.py`'s own shape). BASE = `clef.
_off_staff_discount_applies` monkeypatched to `lambda row, on_staff: False`
(2.11b's rule disabled by an explicit parameter, no new env flag — CLAUDE.md
rule 9); ARM = the unpatched function. `probe/compare_offstaff.py` diffs the
two runs' `Q.CLEF` verdicts by subject.

⚠️ **Sequential, on a contended machine.** A concurrent whole-movement
re-gather (roadmap item 0) ran the entire time; each Litolff run took
~20 min, and each Breitkopf run took ~120 min (vs. the ~15 min this
document's own §"5b" note estimated under lighter load) — both finished
and both are reported, wall time included so the number is not mistaken for
a quiet, uncontended baseline.

| document | clef verdicts | READ clefs CHANGED value (gate: 0 besides the named subject) | newly DECIDED (was not DECIDED in base) | rows discounted in the arm |
|---|--:|---|---|--:|
| Litolff | 331 (both arms) | **0** | 0 | 88 |
| Breitkopf | 691 (both arms) | **1** — `staff/6/1/3` (see below) | 1 — `staff/14/0/11` | 283 |
| engraved | 54 (both arms) | 0 | 0 | 3 |

**Litolff: three staves stopped deciding `treble` on an off-staff box alone,
none decided a DIFFERENT value.** `staff/11/0/7` and `staff/14/1/9`:
`decided/treble` (base) → `abstained/no_candidates` (arm). `staff/6/1/9`:
`decided/treble` (base) → `narrowed/margin_below_floor` (arm, a genuine
3-way tie treble/bass/alto at 1.5 each once the off-staff term is removed).
2.10's `infer.fill_clef_gap` did NOT refill any of the three in this run —
`clef_from_other_systems` stayed at 9 verdicts in both arms — so these three
staves are left honestly undecided rather than silently re-guessed; healing
them (if their own part has a decided clef on another system) is a
different, unmeasured question. **0 staff anywhere on Litolff decided a
DIFFERENT clef value.**

**Breitkopf: the named case, `staff/6/1/3`, base=`treble` → arm=`bass`.**
This IS the roadmap's own gate ("that staff's treble no longer rests on the
off-staff box") — satisfied, treble no longer decides there — but it is
also the ONE subject whose READ value changed on either document, and
CLAUDE.md's rule to report honestly applies to what the NEW value is, not
only to whether the gate's letter is met:

  * **The crop settles it is not `bass`, and confirms the discount is
    correct.** `out/print/c211b-breitkopf-p6-s1-st3-bass.png`: this staff's
    own header (GREEN lines) prints an unmistakable C clef; the discounted
    `clefG` (RED box) is the swirl of the TREBLE clef belonging to the
    staff below, exactly as 2.11's own finding on this same staff already
    established. The discount itself is right.
  * **Why `bass` and not `tenor`** (2.11's own one-page re-gather of this
    exact staff found `tenor`, Sean-adjudicated ✓ on 2026-09-23): the
    `library/_shared-records/brahms1-breitkopf-mvt1-whole-20260923.record.
    json` this lane measured against — per this item's own brief and
    CLAUDE.md §6b ("give every arm its own tag... a shared record is a
    snapshot of the reader that made it") — **predates 2.11's own
    GATHER-time C-clef-locator connect on this staff.** Checked directly on
    the raw record: `Q.CLEF_LOCATED` carries TWO `occupied` ABSTENTIONS for
    `staff/6/1/3` (both frames), not the DECIDED `tenor` 2.11's targeted
    p.6 re-gather produced — the committed whole-movement record was
    gathered before that fix reached this file, despite sharing its
    `20260923` filename. With the locator silent, once the off-staff `clefG`
    is discounted the ONLY remaining evidence is `Q.INSTRUMENT`'s
    conventional expected clef (`Term("instrument", W_INSTRUMENT=1.0, ...)`,
    `used=['vrd:435951']`, margin exactly at `MARGIN_FLOOR`), which says
    `bass` — also apparently wrong, by a mechanism 2.11b did not touch and
    is not the discount's fault. **A fresh whole-movement re-gather on
    today's tree (roadmap item 0, running concurrently with this
    measurement) would carry 2.11's connect too and is the right instrument
    to re-check this ONE subject's final value — not asserted here.**
  * **0 OTHER staves on Breitkopf changed value.** `staff/14/0/11`:
    `narrowed/None` (base) → `decided/alto` (arm) — a genuine tie broken by
    removing an off-staff distractor term, not a value CHANGE (base never
    decided). Crop: `out/print/c211b-breitkopf-p14-s0-st11-alto.png`, same
    GREEN/RED convention, same confirmation (the discounted box is a
    neighbour's).

**engraved: inert.** 3 detector `clefG` rows carry an off-staff position
(all a single Verovio rendering artefact — page-top/bottom systems' own
clef reads bleeding by exactly one system's height, −11.1 to −11.3, a tight
cluster) and all three are discounted, but each staff ALSO had independent
locator/other evidence already deciding the same value, so **0 clef
verdicts changed at all**, base or arm, byte-for-byte outcome and value.
Reported per CLAUDE.md §6b — an arm that moves nothing because the page
holds nothing TO move (Litolff p.1 in 2.11's own §4b) and one that moves
nothing because every discount was redundant are different numbers, and
this is the second kind: the discount FIRED (3 times) and changed nothing,
which is itself evidence the mechanism does not overreach where other
readers already agree.

## 7e. Crops — for Sean, nothing further adjudicated

`probe/crop_offstaff.py`, adapted from this lane's own `crop_clef.py`: same
DPI-off-the-record discipline, same frame control
(`crop_inferred._frame_ok`, imported not copied), same GREEN-staff-lines
convention. Differs in WHAT it boxes: `crop_clef.py` boxes a CV-locator
cluster (`Q.CLEF_LOCATED.bbox`); this boxes the DETECTOR's own `Q.GLYPH_BOX`
for the clef glyph, matched to the `Q.CLEF_GLYPH` row that names it by an
(x_center, y_center) hit against the box's OWN centre (`Q.GLYPH_BOX`'s (x,
y) is the box's TOP-LEFT corner, not its centre — caught by a real
filename/zero-boxes-drawn run, not reasoned out in advance; see the
script's own comment). RED = discounted; BLUE = the box the winning verdict
`used`; ORANGE = present but neither.

| crop | staff | base → arm | frame contrast |
|---|---|---|--:|
| `c211b-breitkopf-p6-s1-st3-bass.png` | (C clef printed) | treble → bass | 179.09 |
| `c211b-breitkopf-p14-s0-st11-alto.png` | staff/14/0/11 | narrowed → alto | 197.19 |
| `c211b-litolff-p11-s0-st7-abstained.png` | staff/11/0/7 | treble → abstained | 226.37 |
| `c211b-litolff-p14-s1-st9-abstained.png` | staff/14/1/9 | treble → abstained | 193.01 |
| `c211b-litolff-p6-s1-st9-abstained.png` | Vcl. (staff/6/1/9) | treble → narrowed | 28.66 |

All five frame controls PASSED (none refused). `staff/6/1/9`'s contrast
(28.66) is far below the others' — a real page-condition difference, not a
threshold failure (the control's own pass/fail line is separate and did not
trip); the crop is still legible (§7e's own inline view confirmed it).

Every sidecar and `MANIFEST-c211b-{litolff,breitkopf}.json` carry
**`"VERDICT_none_yet": null`**. Nothing beyond §7d's own crop reads above
(which staff the discounted box actually belongs to — visible directly, not
a line-level reading) has been adjudicated against the print.

## 7f. Caveats

1. **The Breitkopf whole-movement record is stale** (§7d) — it predates
   2.11's own GATHER-time fix on the one staff this item's own gate names.
   The discount is measured correct against it (the crop confirms); the
   record's OWN clef-locator gap is 2.11's, not 2.11b's, and is exactly
   what roadmap item 0's concurrent re-gather exists to close.
2. **This is an ADJUDICATE-only measurement** (CLAUDE.md §4d's blind spots):
   it cannot see a GATHER change, and the 283/88/3 "discounted" counts are
   priced against records already on disk, not against what a fresh gather
   would produce.
3. **n = 3 documents, 2 publishers, 1 era**, same population 2.11 measured
   from.
4. **The two Litolff staves that now abstain are not automatically
   refilled** by `infer.fill_clef_gap` in this run (§7d) — left honestly
   open, not claimed as an improvement beyond "no longer wrong."

---

## What is committed here

```
FINDINGS.md
probe/price_occupied.py         step 1 (2.11): the bands and the reach, off the records
probe/run_ab.sh                 the two-arm re-gather (a GATHER change needs one)
probe/run_arm.sh                the arm alone, against an unchanged base
probe/compare_ab.py             the gates, base vs arm (2.11)
probe/crop_clef.py              the print crops, frame control imported not copied (2.11)
probe/price_position_bands.py   2.11b step 1: per-family Q.CLEF_POSITION bands, streamed
probe/readjudicate_offstaff.py  2.11b: gather-once-adjudicate-twice, base vs arm
probe/compare_offstaff.py       2.11b: the gate, base vs arm, by subject
probe/crop_offstaff.py          2.11b: print crops for the changed verdicts
out/occupied-reach-{litolff,breitkopf,engraved}.json
out/ab-{litolff-p3,breitkopf-p1,breitkopf-p6}.json
out/funnel-{base,arm}-p3-s0-st9.json
out/position-bands.json                       2.11b: the measured bands, all three documents
out/ab-{litolff,breitkopf,engraved}-offstaff.json   2.11b: base-vs-arm clef diff, by subject
out/print/…                     10 crops (5 from 2.11, 5 from 2.11b) + sidecars
                                 + 3 manifests, VERDICT_none_yet: null
```

The `*.record.json` and `*.musicxml` under `out/` are **gitignored** —
7.6–12.8 MB (2.11) to hundreds of MB (2.11b's whole-movement arms) each and
regenerated by the commands above.
