# One-line percussion staves — what the `>= 5` filter protects, and what it costs

2026-09-06/07. Branch `worktree-agent-a64f7fb5bce33d36a`, on `aaafc0ee` (main)
merged. **`OMR_ONE_LINE_STAVES` is OFF by default and no other default moves.**

```bash
python3 benchmarks/omr-one-line-staves-2026-09/probe_census.py --per-edition 3
python3 benchmarks/omr-one-line-staves-2026-09/probe_engraved_exposure.py
python3 benchmarks/omr-one-line-staves-2026-09/cut_crops.py
bash     benchmarks/omr-one-line-staves-2026-09/run_ab.sh <tag> <pdf> <page>
python3 benchmarks/omr-one-line-staves-2026-09/make_normalised_truth.py
python3 benchmarks/omr-one-line-staves-2026-09/price_arms.py --arm ROW=NAME=XML
```

---

## The answer in one paragraph

The filter guards **five** things, not the one its comments name, and one of the
five is the reason the obvious fix is dangerous. Admitting the staves safely
took a reconstructed canonical span, two stated units, and three sites left
filtered exactly as they were. It then **works** — the staff reaches a cell, a
detection and the export, at the right scale, with every geometric reader
abstaining and **no pitch resolved on it**. But what it is WORTH depends
entirely on which benchmark era you score it in, and the two eras disagree in
sign: **+65 edits in the shipped era, −212 edits and `entire staff` 504 → 0 in
the page-normalised era.** That is not a contradiction and it is not noise —
§4 works `docs/backlog-2026-09-07-open-items.md` §A00's list and lands on (b),
the metric charging for something other than correctness.

**Recommendation: keep the flag, keep it OFF, and couple it to the staves-map
work.** It is not independently shippable, and the reason is measured rather
than cautious.

## ⚠️ Which instrument can see this work

Read this before running anything, because one named instrument is blind and
saying so is more useful than a green run on it.

| instrument | can it see a one-line percussion staff? |
|---|---|
| `benchmarks/omr-identity-harness-2026-09/` | **NO.** Its 1571 records are `beet5` and `brahms1` only, and `grep -ic "percussion\|drum\|cymbal\|triangle\|trommel\|becken"` over `probe/corpus.py` and `out/records.json` returns **0 and 0**. Neither work prints one — corroborated by `probe_engraved_exposure.py` detecting 0 on both. It would report no movement whatever the flag did |
| the engraved eleven (`orchestral_eval`) | **only via `dvorak-sym9-mvt4`** — 1 printed, 1 detected. The other ten are byte-identical by construction (§3) |
| the 20-row scan gate | **yes**, on the four Mahler rows — and it is the instrument that produced §4's two tables |
| the structural accounting (`entire staff`, printed-vs-emitted staff count) | **yes**, and this is the honest one: §4.1 shows the edit count answering with the wrong sign in the shipped era |

⚠️ **A green identity-harness run is not evidence here.** Stated plainly because
the next reader would otherwise assume the named instrument was applied and
passed.

## ⚠️ HAZARD TO IRREPLACEABLE HUMAN WORK — what a labeling session must do

`annotate/select_cells_orchestral.py` calls `extract_measures`. **So a labeling
batch cut with `OMR_ONE_LINE_STAVES=1` contains percussion cells that a batch
cut without it does not — and `cells.json` records no flag**, exactly as it
records no padding mode. Hand-labeled cell PNGs are not regenerable.

This cannot fire while the flag is off, which is why it is not fixed here. What
a labeling session should do until it is:

1. **Do not set the flag for a labeling batch** unless the batch is deliberately
   a percussion sweep. The flag changes which cells exist, not just how they
   look.
2. **If you do set it, record it in the batch** — a line in `batch_config.json`
   or the batch README naming `OMR_ONE_LINE_STAVES=1`. `recut_cells` derives the
   padding mode by matching the manifest; it has nothing to derive this from,
   because a missing cell looks like a missing cell.
3. **Re-cut with the same setting you cut with.** A flag-on batch re-cut with
   the flag off leaves its percussion verdicts with **no image** — loud rather
   than silent (`recut_cells` reports missing cells, it does not mis-frame the
   surviving ones), but still a session lost to confusion.

⚠️ What is NOT at risk: the *framing* of any five-line cell. `_cell_span_px` is
the identity on a five-line staff and one-line staves never reach
`_measure_x_boundaries`, so the three fields `recut_cells.frame_mismatch`
compares cannot move — asserted with the flag **ON** (§2.2).

The real fix is a flag column in `cells.json`, alongside the padding mode.
Out of scope: `cells.json` is written by tools this session was not sent to
change.

---

## 1. What `>= 5` protects against

### 1.0 The population is exactly one function's output

`_group_into_staves` accepts **only five-peak windows** (`staff_detector.py:230`,
`if len(peaks) < 5: return []`), so a staff with fewer than five lines is
always exactly **one** line and always came from
`staff_detector._single_line_staff_rows`. There is no 2/3/4-line population to
worry about. The filter's blast radius is that one function's accept list, and
the question "how much of what it drops is real" is the question "how precise is
`_single_line_staff_rows`".

### 1.1 Five guards, and only three of them are written down

| # | what it guards | where | still filtered? |
|---|---|---|---|
| 1 | the **barline vote** — a staff with no span answers "there is a barline here" for any stem crossing it, and it moves the denominator of a fraction | `:464`, comment present | **YES**, unconditionally |
| 2 | `resegment`'s **morphological kernel**, sized from the staff span: span 0 makes it 1×0 and OpenCV raises. The comment names the page it crashed on (La Mer p.25) | `:1471`, comment present | **YES**, unconditionally |
| 3 | the **cell**, canonicalised by the five-line span | `:1148`, comment present | this is the one the flag opens |
| 4 | ⚠️ **the system's own measure boundaries** — `sys_staves` at `:1148` is also what `_measure_x_boundaries` receives, and it takes a MEDIAN over `x_start` and a **MAX** over `x_end` | `:1148`, **no comment** | **YES**, unconditionally |
| 5 | ⚠️ **the canonical scale itself** — `_upscale_to_canonical` reads `staff_span_px <= 0` as *"do not scale"* and returns the cell at **1.0** | `:818`, **no comment** | fixed, not filtered |

**Guard 4 is the one that would have made this change non-additive**, and
nothing in the tree says so. `probe_margin_reach.py` measures it on the four
Mahler pages — a percussion rule's printed extent is simply not its neighbours':

| page | five-line `x_start` median | the rules' `x_start` | boundaries move? |
|---|--:|---|---|
| p2 | 843 | 881, 879 | **YES** — first measure `(843, 1436)` → `(845, 1436)` |
| p3 | 449 | 506, 505 | no |
| p4 | 458.5 | 515, 515, 514 | **YES** — `(458, 517)` → `(462, 517)` |
| p5 | 454 | 515, 516, 515, 513 | **YES** — `(454, 515)` → **`(464, 1164)`** |

**3 of 4 pages.** (⚠️ My first draft had the DIRECTION backwards: the rules
start ~55 px *later* than the median five-line staff, not earlier. The
displacement is what matters, not its sign, because the function medians.)
Pinned by `test_the_percussion_rule_does_not_vote_on_the_system_edges`.

#### ⚠️ Guard 4 priced — and it turns out to protect a bug as well as prevent one

A 649 px move on p5 is too large to describe and leave. Opened
(`/tmp` probe, reproduced by `probe_margin_reach.py`'s numbers):

```
barline xs        515, 1164, 1529, 2105, 2503, 2869, 3296, 3664, 4219
five-line only    x_lo=454  spacing=25.8  edge_margin=52  cut=506  -> 515 KEPT
rules voting      x_lo=464  spacing=25.8  edge_margin=52  cut=516  -> 515 DROPPED
```

`_measure_x_boundaries` drops any barline within two staff spaces of the
system's left edge, because — its own comment — *"the one opening it as part of
the bracket … neither divides two measures, and treating the opening one as a
boundary manufactures a sliver 'measure' … which then swallows the clef."*
**The barline at 515 is that opening rule.** Adjudicated by looking
(`crops/mahler-p5-system-head.png`): at page x 515 stands the bracket's vertical
rule immediately left of the clefs; the first real barline is the full-height
one at **1164**, with the measure number *24*, the clefs, the key signatures and
the notes between them.

So on this page the five-line-only answer **manufactures exactly the sliver the
function exists to prevent**, and admitting the percussion rules is what fixes
it — by moving `x_lo` 454 → 464, which lifts the cut from 506 to 516 and clears
the rule at 515 by **one pixel**. The five-line-only arm misses it by **nine**.

⚠️ **But the end-to-end cost is ZERO, and that is why guard 4 stays.**
`transcribe._drop_furniture_measures` removes leading empty columns downstream,
and the arithmetic closes exactly: 8 barlines survive the edge filter → 9
boundaries, while both arms report **8.0 measures per staff** (136/17 and
168/21). The sliver is created and then dropped. So:

* the effect is **real** (boundaries move on 3 of 4 pages);
* on the one page opened it moves toward the **truth**, not away;
* and it is **absorbed** before it reaches a measure, so relaxing guard 4 buys
  nothing measurable and risks a page where the median moves the other way.

**Priced, therefore kept.** What this actually indicts is neither the flag nor
the guard but `_measure_x_boundaries`' opening-rule rejection being a hard
2-space margin off a silently-medianed `x_lo` — a nine-pixel boolean, the
Class-A shape the decision map already files at `D16`. Recorded for that
workstream, not fixed here.

**Guard 5 is the one that makes the naive fix quietly wrong.** Deleting the
`>= 5` and nothing else does not crash — it hands the detector a percussion cell
at *page resolution* while every other cell on the page arrives upscaled to a
400 px staff span. That is precisely the inference-scale fault
`benchmarks/omr-detector-scale` measured, arriving through a different door.
`_cell_span_px` reconstructs the scale instead — four spaces of the page's own
staff spacing is what a five-line staff on this page spans — and
`test_the_cell_arrives_at_the_SAME_SCALE_as_its_neighbours` fails (scale 20.0
against 100.0) if it is reverted.

### 1.2 Census — how much of what it drops is real

<!--CENSUS-->

---

## 2. Which consumers break — traced, then guarded

⚠️ **The dangerous consumers are not the ones that need five lines.** Six
independent readers already abstain on a one-line staff, because this project
consistently wrote `!= 5` / `< 5` guards instead of assuming five. The two that
bite are the two that need a staff-space **unit** and answer with a constant
written for a different frame — silently, with no exception and no abstention.

| consumer | on a 1-line staff, before | verdict |
|---|---|---|
| **`pitch_resolver.pitch_for_notehead`** | `len(...) < 2` → **`None`** | ✅ already safe — **the single most important one, and it was already right** |
| `pitch_resolver.pitch_candidates_for_notehead` | `< 2` → `[]` | ✅ already safe |
| `voicing._is_pitched_notehead` | an unpitched notehead never becomes an event | ✅ — so the staff exports as **rests**, never as fake notes |
| `clef_geometry.line_named_by` | `!= 5` → `None` | ✅ already safe |
| `transcribe._staff_geometry` | `!= 5` → `None` | ✅ already safe |
| `hairpin_detection` | needs `staff_geometry.line_ys_page` ≥ 5; that block is `None` | ✅ already safe |
| `measure_align.detection_position` (the label pre-fill) | `< 5` → `None` | ✅ already safe |
| `measure_extractor._neighbour_room` | already skips `< 5` when measuring pad room | ✅ already safe |
| `clef_correction.apply_clef_corrections` | skips `instrument.unpitched`; contextual names these staves `Percussion`, which **is** `unpitched=True` | ✅ already safe |
| `contextual._fill_defaulted_clefs` | skips any staff with `clef_source`; the flag sets `"one_line_staff"` | ✅ safe by the new marking |
| `staff_header` | `max(1.0, staff.line_spacing_px)` → the page spacing | ✅ correct number already |
| ⚠️ **`line_detection._staff_line_spacing`** | `< 2` → **`24.0`**, a constant written for another frame — an uncapped canonical cell's spacing is `CANONICAL_STAFF_SPAN_PX / 4 = 100`, and a width-capped one is something else again. Silently wrong in both: every stem-length gate and beam cluster measured in the wrong unit | **FIXED** — `_build_measure_cell` states the cell's own spacing (`staff.line_spacing_px * scale`), which is exact whether or not the cell was width-capped |
| ⚠️ **`staff_line_removal.remove_staff_lines_from_cell`** | `< 2` → spacing **`0.0`** → `cap = h`, i.e. the run-height cap lifted to the whole cell, so a stem crossing the rule becomes an erasure candidate | **FIXED** — same stated spacing |
| ⚠️ **`export._mxl_attributes_block`** | `_MXL_CLEF_SIGN` is built from `CLEF_BY_FAMILY_LINE`, which holds only the **pitched** families, so `percussion` falls through to `("G", 2)` — a bass drum exported as a **treble** staff | **FIXED** — `<sign>percussion</sign>` + `<staff-lines>1</staff-lines>` |
| `export._clef_to_lily` | returns `percussion` unchanged — already the literal LilyPond clef name | ✅ no change needed; pinned anyway |
| ⚠️ `contextual._apply_dossier_clefs` | would override a percussion clef from a dossier fact | **KNOWN LIMIT**, §6 |

### 2.1 The pitch question, answered on a real page

The commission's sharpest worry — *"a one-line staff admitted without those
guards produces nonsense pitches on a bass-drum staff"* — is measured, not
argued. Mahler 5 p5, controlled A/B, same tree, same flags but the one:

| | staves | measures | noteheads | **pitched** |
|---|--:|--:|--:|--:|
| flag off | 17 | 136 | 251 | 251 |
| flag on | **21** | **168** | 705 | **251** |

**Pitched is 251 in both.** The four admitted staves detect 97–137 noteheads
each and resolve **zero** pitches, exactly as `pitch_resolver`'s existing guard
requires. And all **17** five-line staves are byte-identical in their
detections — 0 of 17 changed — so the transform is additive on the page as well
as in the unit tests.

⚠️ **Those 454 unpitched noteheads are not percussion notes.** A measure cell is
padded 4–6 staff spaces above and below, so on a conductor's page a one-line
rule's cell reaches into the staves either side; the detections are mostly the
neighbours' ink. They cost nothing downstream (no pitch ⇒ no event) but they are
noise in the JSON, and they are the reason §6 refuses to claim this reads
percussion.

### 2.2 ⚠️ Committed human labels cannot be invalidated by this — stated with the reason

`measure_extractor` has **14 non-test importers** — counted on the AST, not on
`grep`, because five further files mention it only in prose (`export.py`,
`line_detection.py`, `score_reading.py`, `system_grouping.py`,
`yolo_detector.py`) and none in `backend/` imports it at all. Six of the
fourteen are the labeling pipeline: `annotate/recut_cells.py`,
`annotate/select_cells.py`, `annotate/select_cells_orchestral.py`,
`annotate/select_timesig_cells.py`, `annotate/server.py`, plus
`training/phase1_layout_eval.py`. (Relayed to me as 15; my AST count is 14 and
the method is above, so the difference is probably one test file or a
prose-only hit.)
Hand-labeled cell PNGs are **not regenerable**, and
`recut_cells.frame_mismatch` aborts a batch by comparing exactly three fields:
`cell_canonical_w`, `cell_canonical_h`, `staff_line_ys_canonical`.

The change cannot move any of them, for one reason: **`_cell_span_px` is the
identity on every five-line staff.** `page_span` is the only line of
`_build_measure_cell` touched, the crop box is computed before it, and
`_measure_x_boundaries` never sees a one-line staff. This is asserted directly
against those three fields **with the flag ON**
(`TestCommittedHUMANLABELSCannotBeInvalidated`) — stronger than a flag-off
argument, because it says the mechanism cannot move a frame even while running.
`test_recut_cells_e2e.py` is green.

⚠️ **One real labeling footgun, and it is operational, not silent.**
`select_cells_orchestral` calls `extract_measures`, so a batch cut with the flag
ON contains percussion cells a batch cut with it OFF does not — and `cells.json`
records no flag, exactly as it records no padding mode. Re-cutting such a batch
with the flag off leaves those cells' verdicts with no image. `recut_cells`
already derives the padding mode by matching the manifest; a flag column would
be the same move. **Not fixed here** — it cannot fire while the flag is off, and
`cells.json` is written by tools this session was not sent to change.

---

## 3. Exposure — where a one-line staff can even occur

`probe_engraved_exposure.py`, both questions asked separately (what the fixture
**prints**, per its own LilyPond source, and what `staff_detector` **finds**):

| the engraved eleven | printed 1-line staves | detected |
|---|--:|--:|
| 10 of the 11 works | 0 | 0 |
| **`dvorak-sym9-mvt4`** | **1** | **1** (staff 13, spacing 41) |

So the engraved benchmark is **byte-identical by construction on ten of eleven
works**, and can genuinely price the eleventh. ⚠️ Worth recording separately:
`mahler-sym5-mvt1`'s engraved fixture writes `\clef "percussion"` four times but
renders them through LilyPond's `\new DrumStaff`, which is **five lines** — so
the engraved Mahler does not reproduce the scanned Mahler's printing, and a
percussion result on one says nothing about the other.

---

## 4. What it is worth — and ⚠️ the two eras disagree in SIGN

Both columns are one controlled A/B: same tree, same page, same flags apart from
`OMR_ONE_LINE_STAVES`, scored through the same `musicdiff` bridge against the
20-row gate's own committed trimmed truth. Nothing is re-transcribed between
arms.

### Mahler 5 p5 — the shipped era (truth as the gate scores it today)

| arm | OMR-NED | edits | `entire staff` | `entire measure` | `wrong note` |
|---|--:|--:|--:|--:|--:|
| off | 0.9294 | 2948 | 1220 | 1121 | 414 |
| **on** | 0.9279 | **3013** | **1012** | 1296 | 480 |

⚠️ **The ratio falls and the edit count RISES.** That is the metric's documented
dilution reward, not a gain: the prediction went from 1108 to 1183 symbols. The
structural charge does move the right way (`entire staff` −208) but more comes
back as whole-measure and unpaired-note charges. **Read this row as +65 edits.**

### Mahler 5 p5 — the page-normalised era (truth condensed onto printed staves)

| arm | OMR-NED | edits | `entire staff` | `entire measure` |
|---|--:|--:|--:|--:|
| off | 0.8389 | 2286 | **504** | 888 |
| **on** | **0.7407** | **2074** | **0** | 826 |

**−212 edits, and `entire staff` goes to zero.** This is the exact residual
`benchmarks/omr-staves-map-completion-2026-09/FINDINGS.md` §6 attributed to
one-line percussion and could not remove — removed, on the same prediction
files, by admitting the staves. Here the ratio and the edit count move together,
so it is not dilution.

<!--DVORAK-->

### 4.1 ⚠️ Working §A00's list, because the shipped-era arm is worse

Sean's rule: *a worse score does not condemn the mechanism — ask what ELSE is
wrong first.*

**(a) Is the COMPARISON valid?** Yes. One tree, one page, both arms
`--no-direction-text`, run **sequentially** so neither was measured under a
different machine load, predictions scored in one `musicdiff` batch. The five
five-line staves' detections are byte-identical between arms, so the only
difference between the two files is the four added parts.

**(b) Is the METRIC charging for something other than correctness? — YES, and
this is the answer.** In the shipped era Mahler's truth carries **38 encoded
parts** against **17–21 printed staves**. musicdiff's part alignment is
monotonic, so where the truth is longer than the prediction it sheds parts from
the END — which on a conductor's page is the string section, the most expensive
staves there are. Adding four parts in the MIDDLE therefore re-shuffles *which*
parts get shed; it does not pair the percussion. Normalise the truth onto the
printed staves — 21 against 21 — and the identical prediction scores **−212**
with `entire staff` at zero. **The mechanism did not change between those two
rows. Only the denominator did.**

**(c) Can a DOWNSTREAM consumer use the signal?** Partly, and honestly:
* it reaches the export as a part named `Percussion`, with a **percussion clef**
  and `<staff-lines>1</staff-lines>`, and the right number of measures;
* it does **not** reach note content. There is no unpitched reading path, so
  every bar is a rest. That is a true statement about what we read — *there is a
  percussion part here and we found no notes on it* — and it is strictly more
  than the staff being absent, but it is not percussion transcription.

**(d) Is the mechanism wrong?** No. It does what it claims, additively, with the
pitch guard holding. What it is not is *independently* valuable.

---

## 5. Decision-map checkpoint (`docs/architecture-decision-map.md`)

### ⚠️ 5.0 The map is WRONG about my area — independent corroboration

Stage 3's note says `Staff.nominal_line_spacing_px` *"exists specifically so
such a staff could size its windows, **and no production site reads it**."*
**That is false**, and I hit it independently before the verification branch was
relayed to me:

* `Staff.line_spacing_px` (`types.py:101-102`) returns that field whenever
  `len(line_ys) < 2`;
* `system_grouping` reads that property in **nine** places and has **no `>= 5`
  filter** anywhere;
* `staff_detector.detect_staves` hands `assign_systems_by_bridging` the **full**
  staff list, one-line staves included.

So a one-line percussion rule has fed **system-grouping geometry** since the day
it was first detected — on main, with this flag off. `claude/verify-decision-map`
is right and the map needs correcting.

⚠️ **Two refinements the correction itself needs**, both pinned by
`TestSystemGroupingIsUpstreamAndCannotSeeTheFlag`:

1. **The value is not nonsense.** `line_spacing_px` returns the **page's own
   spacing** (41.0 in the test, and the real Mahler/Dvořák values) — exactly the
   job the field's docstring claims. The relayed worry that *"a nonsense spacing
   there propagates into grouping"* does not materialise; what propagates is the
   correct scale.
2. **It is not downstream of this flag.** Grouping is decided in
   `detect_staves`, which runs **before** `extract_measures`; neither
   `staff_detector` nor `system_grouping` imports it (asserted on the AST,
   because `system_grouping.py:30` mentions the module in prose), and the flag is
   read at **exactly one place** (also asserted). The flag cannot move a system
   boundary.

Where the map is **right**: the `>= 5` filter's three locations (`:464`,
`:1148`, `:1471`) are exact, backlog item **C3** describes it correctly, and
`_dedupe_cross_staff_detections`'s "both confidences in hand and neither read"
is confirmed by the 454 unpitched detections above landing in the percussion
cells with no confidence arbitration.

### 5.1 The five questions

**1. What does my decision already have available that it does not use?**
`Staff.line_thickness_px` — `measure_line_geometry` traces it for a one-line
staff too, and it would say whether a full-width rule is printed at staff weight
(a percussion staff) or heavier (a page rule). Unused. And the **detection
confidences** in the admitted cell, which would separate the neighbours' bled
ink from anything real; unused, which is the same Class-D gap the map records
for `_dedupe_cross_staff_detections`.

**2. What consumes my output?** §2's table, in full. The important half:
`_cell_span_px` is the **first production reader** of
`nominal_line_spacing_px`'s *intended* purpose — so this **closes** an entry on
the "gathered and never used" list rather than adding one. Nothing new is
emitted that nobody reads: `staff_lines` and `clef: percussion` are both
consumed by `export._mxl_attributes_block`, and `unpitched` was **already** set
by `contextual` from the lexicon (see question 5).

**3. What do I depend on, and is it SATISFIABLE?** One dependency:
`nominal_line_spacing_px > 0`. It is set by `detect_staves` under exactly the
condition (`spacing > 0`) that lets `_single_line_staff_rows` run at all, so it
is satisfiable **by construction** — and where it is not, `_cell_span_px`
returns 0 and the staff is refused rather than admitted unscaled
(`test_a_spacingless_rule_is_not_admitted`).

**4. Am I inside a cycle, or would my change create one?** No. The flag reads
only stage-1 geometry (`line_ys`, page spacing) and produces cells. It reads no
identity, no clef and no pitch — and the clef it *writes* is derived from the
line count, not from any downstream reading, so it cannot close a loop with
`clef_correction` (which skips `unpitched` anyway).

**5. Is this information already gathered elsewhere?** `staff["unpitched"]` is
already written by `contextual.py:1354` from the instrument lexicon. ⚠️ **These
two are NOT one signal**: the lexicon's comes from the printed **label**
("Becken"), mine from the printed **rule count**. They share no ancestor, and
the geometric one reaches staves no lexicon can name — which matters given the
measured finding that 29 of 29 unresolved non-treble scan staves print no label
at all. Both write the same value, so there is no conflict to resolve.

---

## 6. What I refused, and what is still missing

* **Refused: lowering the number.** The three `>= 5` sites are still `>= 5`.
  Guards 1, 2 and 4 are relaxed by nothing; only the cell loop takes an extra,
  separately-collected list.
* **Refused: reading the percussion.** The admitted staff exports **measures of
  rest**. Doing better needs an unpitched reading path — `<unpitched>` with a
  `display-step`/`display-octave`, a percussion-aware `voicing`, and a way to
  tell a real notehead on the rule from the 454 neighbour detections that
  currently land in its padded cell. None of that is here, and claiming it would
  be the "detected then dropped" failure in a new place.
* **Refused: turning it on.** The shipped-era arm is +65 edits (§4). The flag is
  worth what §4's second table says **only** in the page-normalised era, which
  is another workstream's and is not on main.
* **Refused: fixing `cells.json`'s missing flag column** (§2.2) — out of scope
  and unreachable while the flag is off.
* **Known limit, not fixed:** `contextual._apply_dossier_clefs` would overwrite
  the percussion clef from a dossier fact. Reachable only on a `--dossier` run
  with the flag on; the scan gate is dossier-free by protocol.
* **Known limit:** the census (§1.2) measures `_single_line_staff_rows`'
  precision on the library as it stands. It cannot measure **recall** — Mahler
  p2 detects 2 of its 5 printed rules and the other three are missed by that
  function, not by this filter.

## 7. Files

| file | what |
|---|---|
| `probe_census.py` | library-wide census of what `>= 5` drops |
| `probe_engraved_exposure.py` | printed vs detected one-line staves on the engraved eleven |
| `cut_crops.py` | crops for hand-adjudicating census hits |
| `run_ab.sh` / `run_all.sh` | one controlled A/B, arms run in sequence |
| `make_normalised_truth.py` | the page-normalised truth, from the completion session's own maps |
| `price_arms.py` | score two arms against a row's truth in one musicdiff batch |
| `price-p5.json` / `price-p5-normalised.json` | the two eras' numbers |
| `engraved-exposure.json`, `census.json` | the measurements |
