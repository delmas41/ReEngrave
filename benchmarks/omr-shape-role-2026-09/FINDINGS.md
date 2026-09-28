# Shape from the class, role from the geometry — the audit

**ROADMAP 2.12** · audit and design lane, 2026-09-23 · branch
`claude/shape-role-audit-2.12`, base `404ccc5a` · **no product code changed;
nothing under `tools/` was touched.**

⚠️ **EVERY `file:line` BELOW IS AS OF `404ccc5a`.** `origin/main` moved to
`48496e30` (3.4C) while this lane ran, and that landing shifts
`adjudicators/ownership.py` — the `arc_kind` class test cited at `:626` is
at `:688` there. `gather.py`'s line numbers are unchanged on both
(`_KEYSIG_CLASSES` `:2364`, `_DOT_CLASS` test `:801`, the 2.6 category test
`:678`). CLAUDE.md rule 10: the tree outranks this ledger — check a line
before quoting it.

Sean, 2026-09-23 (`docs/DECISIONS.md`): *"a detector class is TWO claims: the
SHAPE … which the detector is good at, and the ROLE … which is a guess about
context made from a crop. GATHER files the shape and the position and records
the detector's role-guess as ONE witness; ADJUDICATE decides the role from
geometry on the record. No gather filter may key on the role-half of a
class."* And: *"it seems that our staged model would require it to look at all
the blobs and come up with a list of potential ways it could be labeled with
boxes, yolo/CV choices all connected to the ink, and then allow the other
stages to decide … or maybe another way that is better that we haven't figured
out yet."*

Part 1 is the audit, measured. Part 2 sizes five architectures and recommends
one.

---

## 0. How every number here was produced

Two probes, both read-only, both under `probe/`:

```bash
python3 benchmarks/omr-shape-role-2026-09/probe/role_disagreement.py --all
python3 benchmarks/omr-shape-role-2026-09/probe/ink_vs_boxes.py --all
```

`role_disagreement.py` reads the three acceptance documents named in
`benchmarks/acceptance/manifest.json`, one SUBPROCESS per record, and counts —
family by family — the boxes whose ROLE-half the record's own geometry
contradicts. `ink_vs_boxes.py` answers Part 2(c)'s join question on the two
`--ink-rows` records. Every record is read through
`tools.omr.staged.record_io.load_record` and nowhere else (CLAUDE.md §4b).
Raw output is under `out/`. Wall time: 17 s and 4 s.

### ⚠️ Three caveats on the inputs, before any number is quoted

1. **Two of the three acceptance records were gathered on a DIRTY tree.**
   Litolff `dbc9962b` `dirty: true`; Breitkopf `47fbff1e` `dirty: true`; the
   engraved fixture `f48a59ce` `dirty: false`. CLAUDE.md §4b: *a record from a
   dirty tree is not a baseline.* These figures are a CENSUS of a population,
   not an A/B delta, so the dirt does not invalidate them — but no line below
   may be quoted as a baseline a later arm is measured against.
2. **The engraved record is the control that can fail, and it does not fire.**
   It is a Verovio render of Beethoven 5 bars 1–24 — an exact page, cut by the
   same gather. On six of the ten families it returns **0**
   (`keysig_vs_accidental`, `rest_whole_vs_half`, `flag_up_down_vs_stem`,
   `timesig_role`, `clef_sized_notehead`, `role_twin_boxes`) while the two
   scans return hundreds. A probe that counted noise would not separate that
   way. The four families where it is non-zero (11, 6, 1, 1) are this probe's
   own floor and are stated as such in each row.
3. **The rest convention was checked, not assumed.** The probe measures a
   whole rest against half-step 2.5 and a half rest against 3.5. On the
   engraved fixture all **216 of 216** `restWhole` land at median **2.55**
   (p10 2.539, p90 2.560) — a 0.02-half-step spread, which is the frame
   control. The parity convention for `OnLine`/`InSpace` (even half-steps are
   lines) has a second, independent witness already in the tree:
   `tools/omr/training/measure_align.py:617`,
   `return "OnLine" if position % 2 == 0 else "InSpace"`.

---

## PART 1 — THE AUDIT

### 1. The table, sorted by reach

Reach = boxes whose role-half the tree's own geometry contradicts, summed over
the three acceptance records. **Reach is not work order** — §3 says why.

| # | family · site | class set it keys on | SHAPE claim | ROLE claim | role decided from geometry today? | Litolff | Breitkopf | engraved | **reach** |
|--:|---|---|---|---|---|--:|--:|--:|--:|
| 1 | `tie` / `slur` · `gather.py:962` (`_ARC_CLASSES`) → `adjudicators/ownership.py:626` | `("tie","slur")` | one arc | its two ends are the same written pitch | **YES — computed, recorded, and refused as a gate.** `adjudicate_arc_kind` reads `Q.NOTEHEAD_STAFF_POSITION` at both ends and writes `detail.grammar.says` beside the class; `OMR_ARC_RECLASS` is default-OFF on a measured refusal (+130 scan edits, all tie→slur) | 585 / 2 656 | 6 963 / 14 788 | 1 / 75 | **7 549** |
| 2 | `notehead*OnLine` / `*InSpace` · `gather.py:423, 495, 712, 2238` | `startswith("notehead")` + the suffix on `Q.NOTEHEAD_CLASS` | black / half / whole head | it stands on a line, not in a space | **NO — and nothing reads it either.** `Q.NOTEHEAD_STAFF_POSITION` (`gather.py:495-501`) measures the same fact clef-free; `rhythm._HEAD_BEATS` matches the shape PREFIX only; 2.6 removed the last consumer from the ownership contest. The role-half is dead weight that still costs row 4 | 2 994 / 11 632 | 3 384 / 24 533 | 11 / 371 | **6 389** |
| 3 | `artic*Above/Below`, `fermata*Above/Below` · `gather.py:857-875` (`_artic_side`), `:964`, `:985` | `endswith("Above")` / `("Below")` | the mark | which side of the notes it sits on | **NO on the staged path.** `_artic_side` reads the NAME and files it as `detail.side`; `adjudicate_articulation_owner` / `fermata_owner` never check it against the head's y. The legacy reader DID (`_attach_articulations_in_cell` requires the geometry to agree) | 139 / 644 | 989 / 4 143 | 6 / 84 | **1 134** |
| 4 | **two spellings of one head, both surviving NMS** · `gather.py:374` | pairs at IoU > 0.3 sharing a shape core | one piece of ink | `OnLine` and `InSpace` at once | **NO, and no adjudicator can repair it.** `detect()` is called without `agnostic_nms`, so NMS is class-wise and the ink's evidence splits across two output channels. `gather.py:356-373` records this; `benchmarks/omr-staged-dedupe-2026-09/FINDINGS.md` §6.1 ranks it first | 505 / 37 390 | 354 / 98 908 | 0 / 1 741 | **859** |
| 5 | `key*` vs `accidental*` · `gather.py:2364` (`_KEYSIG_CLASSES`), `:2510` | `("keySharp","keyFlat","keyNatural")` | a flat / sharp / natural | it belongs to the key signature | **NO — a hard GATHER filter.** An `accidental*` box standing left of cell 0's first notehead is in the header window and is dropped with no row and no abstention; a `key*` box past the first barline is gathered by nothing | 194 / 2 058 | 617 / 7 860 | 0 / 155 | **811** |
| 6 | `augmentationDot` vs `articStaccato*` · `gather.py:764` (`_DOT_CLASS`), `:801`, `:964` | `== "augmentationDot"` / `startswith("artic")` | one small filled dot | after the head (dot) vs above/below it (staccato) | **NO — routed by class at gather.** The asymmetric dot window (0.75 above, 0.25 below, in staff spaces) lives in `_attached_dots` and only ever sees boxes the detector already called `augmentationDot` | 116 / 608 | 555 / 9 683 | 1 / 4 | **672** |
| 7 | `restWhole` vs `restHalf` · `gather.py:967`, `adjudicators/rhythm.py:579` (`_rest_ruling`) | `startswith("rest")`, then `rhythm._REST_DURATIONS[name]` | one small filled rectangle | which line it hangs from | **NO for the duration** — `_rest_ruling` takes the value straight off the class. **YES for the mirror case** — `adjudicate_notehead_is_a_whole_rest` already computes `_staff_step` against `Q.STAFF_LINES` to catch a whole rest labelled a notehead. The geometry exists and the rest reader does not call it | 300 / 1 642 | 267 / 2 104 | 0 / 216 | **567** |
| 8 | `timeSig*` · `gather.py:2611`, `:2770`, `adjudicators/rhythm.py:1461` | `startswith("timeSig")` | a numeral, or a C | it states the meter | **PARTLY.** `_meter_candidate_columns` requires a second staff of the system to fire in the same cell before the template reader is asked mid-staff — but cell 0 is unchecked, and a lone mid-staff box is still filed as `Q.METER_GLYPH` | 23 / 85 | 83 / 517 | 0 / 36 | **106** |
| 9 | `flag8thUp` / `flag8thDown` · `gather.py:763` (`_FLAG_PREFIX`), `:797` | `startswith("flag")`, value keeps the suffix | a flag of N hooks | the stem it hangs on points up | **THE VALUE EXISTS AND NOTHING READS IT.** `adjudicate_stem_direction` decides the same fact from `Q.STEM`, on the NOTEHEAD's subject; the flag is filed on its OWN glyph subject and the two are never compared. `_flag_levels_for` reads the HOOK COUNT off the same name and ignores the suffix | 27 / 253 (90 cells joinable) | 21 / 3 040 (527 joinable) | 0 / 6 | **48** |
| 10 | a `notehead*` box on clef-sized ink · `gather.py:2227` (`_occupied_boxes`), `:2244` (`_occupied_notehead_rows`), `clef_locator.py:789` | `startswith("notehead")` | a head | it is a head and not a clef | **YES SINCE 2.11** (`benchmarks/omr-clef-geometry-2026-09/`). `_overridable_occupancy` lets a measured 3.3–4.7-space cluster override a notehead label. The residual is 22 boxes ≥ 3.0 spaces tall in cell 0 | 18 / 898 | 4 / 3 296 | 0 / 44 | **22** |

### 1b. Every site, by file — the raw sweep

`gather.py` and the readers it calls, every place a detector class string or a
`category` string is tested. Marked **ROLE** where the test keys on the
role-half, **SHAPE** where it keys on the shape family only (correct by the
methodology, listed so the sweep can be seen to be exhaustive).

| file:line | predicate | SHAPE / ROLE |
|---|---|---|
| `staged/gather.py:303` | `category != "clef"` | SHAPE (family guard; dropping it admits 27 classes as clefs — a `flag8thUp` enters as a BASS clef) |
| `staged/gather.py:423, 495, 712, 1462, 2238, 2262` | `smufl_name.startswith("notehead")` | SHAPE |
| `staged/gather.py:678` | `di.category != dj.category` | SHAPE — **this is 2.6**, the repair; it used to be `smufl_name` |
| `staged/gather.py:721` | `!= "ledgerLine"` | SHAPE |
| `staged/gather.py:797` | `startswith("flag")`; `Q.FLAG` keeps the `Up`/`Down` suffix | **ROLE** (row 9) |
| `staged/gather.py:801` | `== "augmentationDot"` | **ROLE** (row 6) |
| `staged/gather.py:805` | `in ("tuplet3","fingering3","tupletBracket","tupleBracket")` | SHAPE — both spellings admitted, positional gate downstream. **Already the 2.12 shape** |
| `staged/gather.py:857, 873-876` | `endswith("Above")` / `endswith("Below")` in `_artic_side` | **ROLE** (row 3) |
| `staged/gather.py:962` | `in ("tie","slur")` | **ROLE** (row 1) |
| `staged/gather.py:964, 967, 985` | `startswith("artic")` / `("rest")` / `("fermata")` | SHAPE routers; the ROLE rides in the value |
| `staged/gather.py:1112` | `in _DYNAMIC_LETTER_CLASSES` | SHAPE (letters only) |
| `staged/gather.py:1213` | `_WEDGE_CLASSES` lookup | SHAPE |
| `staged/gather.py:1946` | `!= "beam"` | SHAPE |
| `staged/gather.py:2011, 2287` | `_is_clef_class(name, category)` | SHAPE — asks `clef_geometry.clef_family`, the one measured answer, rather than a second hand-written set |
| `staged/gather.py:2238, 2252` | `startswith("notehead")` in `_occupied_boxes` / `_occupied_notehead_rows` | **ROLE** — **this is 2.11**, now overridable (row 10) |
| `staged/gather.py:2510` | `in ("keySharp","keyFlat","keyNatural")` | **ROLE** (row 5) |
| `staged/gather.py:2611, 2770` | `startswith("timeSig")` | **ROLE** (row 8) |
| `staged/adjudicators/rhythm.py:231` | `_FLAG_LEVELS` lookup on the lower-cased name | SHAPE (hook count) — reads the same name whose suffix row 9 is about, and ignores the suffix |
| `staged/adjudicators/rhythm.py:457` | `str(head).startswith(name)` over `_HEAD_BEATS` | SHAPE |
| `staged/adjudicators/rhythm.py:579` | `rhythm._rest_duration(str(row.value))` | **ROLE** (row 7) |
| `staged/adjudicators/rhythm.py:1461, 3105` | `startswith("timeSig")`, `startswith("restwhole")` | **ROLE** (rows 8, 7) |
| `staged/adjudicators/rhythm.py:2725` | `detail.category == "notehead"` | SHAPE |
| `staged/adjudicators/ownership.py:626` | `str(arc.value).lower().startswith("tie")` | **ROLE** (row 1) — the grammar is computed on the next 60 lines and not acted on |
| `clef_locator.py:773, 789` | `occupied_classes is None`; `startswith("notehead")` | SHAPE — **2.11's opt-in**; the `OnLine`/`InSpace` suffix is deliberately never consulted |
| `clef_locator.py:1044, 1048, 1053` | literal `"cClefAlto"` fed to `resolve_clef`; `read.source != "geometry"`; `read.name == "mezzosoprano"` | the class's role half is a PLACEHOLDER that geometry overwrites, and the abstain path names when it could not |
| `clef_geometry.py:176` | `"percussion" in s`, or `s in ("clef8","clef15")` | **ROLE** — names no pitch; refused rather than read |
| `clef_geometry.py:178` | strips `clef` and `change` from the name | **the codebase's explicit shape/role separator** — it deletes the `Change` role marker and keeps the shape core |
| `clef_geometry.py:193, 205, 262` | family initial `c`/`g`/`f`; `family == "C"` | SHAPE |
| `clef_geometry.py:207, 266` | `"tenor" in core else "alto"`; the class-name role as `fallback` | **ROLE** — and `resolve_clef` exists to prefer the measured line over it |
| `clef_geometry.py:282` | `CLEF_BY_FAMILY_LINE` family x line table | **ROLE, MEASURED** — a family landing on a line it never uses is refused |
| `key_signature_locator.py:310` | `if not clef: return None` | **ROLE of the CLEF** — deliberate and paid for: fitting three flats against a guessed clef once returned TWO SHARPS |
| `key_signature_locator.py:398, 405, 409, 467` | both sharp and flat patterns tried; zigzag residual decides; a lone accidental decided by ink bottom-heaviness | **SHAPE, from pixels** — and at `:405` the SHAPE is inferred FROM the role, the inverse of a class test |
| `time_signature_locator.py:284, 294, 337, 504` | `startswith("timeSig")`; the two letter-meter names | SHAPE — selecting Bravura rasters by digit |
| `time_signature_locator.py:256, 585` | `raw not in LETTER_METERS`; the winner carries `symbol` | BOTH — reconstructs the `symbol=` fact a detection would have carried, from the matched template |
| `line_detection.py:53, 363, 745, 1163` | MINTS `smufl_name="stem"/"beam"`, `category="stem"/"structural"` | **ROLE, PRODUCED** — and produced geometrically: `detect_beams` decides beam-vs-slur-vs-ledger by ATTACHED STEM COUNT (`min_attached_stems` at `:1054`, enforced at `:1143`; `_attached_stem_count` at `:989`), never by a class name |
| `line_detection.py:485, 563, 762` | `_meets_a_notehead`, `_drop_paired_strokes`, the notehead gate | no class test at all — raw `(x,y,w,h)` boxes; whichever class filter selected them happened in the CALLER |
| `direction_text.py:327` | `det.get("category") == "dynamic"` AND `_is_inside_a_word` | **ROLE, AND ALREADY OVERRULED** — the one place in the sweep that tests a role half and then measures against it |
| `direction_text.py:326` | span excluded when wider than `max_blank_width_spaces` | spans are excluded by WIDTH, deliberately, rather than by a class list |
| `staff_header.py`, `staff_labels*.py` | **zero sites** | ink profiles, staff geometry and OCR only; nearest-staff-centre attachment is the only spatial test |

### 2. Rows where the tree CANNOT compute the geometry today — a row is a finding

| family | population (Breitkopf) | why it is uncomputable, and what it would take |
|---|--:|---|
| **dynamic letters** (`dynamicF/P/M/S/Z/R`) | 3 949 boxes | ⚠️ **NO ROLE IS CONFLATED HERE** — the class names a LETTER and claims nothing about context. The real role question (*is this run of letters a dynamic marking or a word?*) is already answered geometrically, one module over, by `direction_text.py:326-327`: it tests `category == "dynamic"` and then **overrules it** with an ink-gap measurement (`_is_inside_a_word`) and a width threshold rather than a class list. That is the 2.12 shape, built before 2.12 |
| **`numeral0`–`numeral9`, `tuple`** | 0 fired on all three records | `class_aliases.COARSER_THAN_CANONICAL` REFUSES to map these: the coarse vocabulary has one numeral class for time signatures, tuplet digits, fingerings and measure numbers alike. The role is not recoverable from the name at all. The whole coarse block (ids 136–207) fires zero times on every record measured, so this is latent, not live |
| **`tuplet3` vs `fingering3`** | 101 boxes, 8 classes | ⚠️ **ALREADY THE 2.12 SHAPE.** `_TUPLET_CLASSES` admits BOTH spellings and `adjudicate_tuplet_ratio` gates positionally. `gather.py:765-769` records why: 33 `fingering3` against 16 `tuplet3` over twelve works, and all 33 sat in a cell holding a real triplet |
| **`clefCAlto` / `clefCTenor`** | 96 boxes | ⚠️ **ALREADY THE 2.12 SHAPE.** `clef_geometry.resolve_clef` MEASURES the line off the staff and uses the class name only as the abstain fallback |
| **`beam`** | 11 918 boxes | The role question is *beam vs slur vs tie vs ledger line*, and `line_detection.detect_beams` already decides it by ATTACHED STEM COUNT. `gather_detector_beams` UNIONS the two readers rather than gating (union worth pooled 0.1917 → 0.1861; replacement measured and refused) |
| **`ledgerLine`** | 7 818 boxes | Claims no role; `_ledger_index` reads it as geometry already |
| **`keyboardPedal*`** | 25 boxes | No quantity is gathered and nothing reads it. Not a role conflation — an unread family |
| **the invisible half of row 4** | not countable | A head whose evidence split across `OnLine`/`InSpace` and left BOTH channels under `conf 0.25` was emitted as neither. CLAUDE.md §9: *a box the detector never drew has no subject.* Only a detector arm can count it |

### 3. ⚠️ REACH IS NOT WORK ORDER, and three rows say so

* **Row 1 (7 549, the largest) has a MEASURED REFUSAL attached.** `arc_kind`'s
  docstring prices the grammar veto: engraved 0.1306 → 0.1306, scan 0.8387 →
  0.8391, **+130 edits, all in the tie→slur half**. The geometry is already
  computed and already recorded (`detail.grammar.says`: Litolff `slur` 1 013,
  `tie` 222, silent 1 421; Breitkopf 8 439, 1 461, 4 888). Acting on it is a
  flag that was measured and refused, not a gap. What 2.12 adds here is
  nothing.
* **Row 2 (6 389, the second largest) costs NOTHING today.** Nothing on the
  staged path reads `OnLine`/`InSpace` for a decision — verified by sweeping
  the tree for both suffixes outside `tools/omr/tests/`: every live consumer
  is a training-side module, the annotate UI, or a comment. Its only real cost
  is row 4, which is a DETECTOR change, not an adjudicator change.
* **Row 10 (22, the smallest) was worth a whole roadmap item** — because those
  22 boxes each kill a clef, and a dead clef killed 48 Viola heads on one
  Litolff page (DECISIONS 2026-09-23, ROADMAP 2.10).

The families where the role-half is BOTH wrong and CONSUMED are rows 5, 6, 7
and 8 — **2 156 boxes** between them. That is the actionable reach.

### 4. The three fixed by hand today, as the pattern

| item | the collision | the fix, in one line | where |
|---|---|---|---|
| **2.9b** (in flight; **NOT on `main` at `404ccc5a`** — `_KEYSIG_CLASSES` at `gather.py:2364` is still the three-name tuple) | `_KEYSIG_CLASSES` drops a header flat the detector spelled `accidentalFlat` | widen the GATHER set to the shape; let the header window decide the role | `benchmarks/omr-key-majority-2026-09/` |
| **2.6** (merged `99f9e185`) | the ownership contest's identity test read `smufl_name`, so one piece of ink was ruled "not the same thing as itself" because two cells disagreed about the very fact in dispute | key the identity test on `category` (the SHAPE family); leave the winner to ladder → range → distance | `benchmarks/omr-owner-domain-2026-09/`, `gather.py:678` |
| **2.11** (merged `24d26b8d`) | a 1-space `notehead` label vetoed a 4.5-space geometric clef read | let a measured 3.3–4.7-space cluster override the notehead label | `benchmarks/omr-clef-geometry-2026-09/`, `clef_locator.py:789` |

All three are the same move: **stop letting the role-half of a class decide,
and let a measurement decide instead.** All three were found by following one
staff through the stages by hand. The table in §1 is what that search returns
when it is run exhaustively.

### 5. Proposed roadmap lines — one per family, in ACTIONABLE reach order

Each names the GATHER change, the ADJUDICATE change, the test that runs RED
first, and the gate. ⚠️ Every line whose GATHER half changes the detection set
or a gather filter needs **two full re-gathers** to price (CLAUDE.md §6b);
`readjudicate.py` and `reexport_arm.py` are structurally blind to it and a zero
from either is not evidence. Litolff is 12.8 h, Breitkopf 1.2 h, engraved
minutes.

---

**2.12a — the printed accidental's ROLE comes from the header window, not from
its class.** *(reach 811; Litolff 194, Breitkopf 617, engraved 0)*

* **GATHER**: `_gather_keysig_markers` admits every `key*` AND `accidental*`
  box in cell 0, files `Q.KEYSIG_MARKER` with `detail.detector_role` =
  `"key"` / `"accidental"` (the detector's guess, ONE witness), and files the
  box's x against the cell's first notehead as
  `detail.left_of_first_notehead`. No class is dropped. `key*` boxes in cells
  other than 0 get a row too.
* **ADJUDICATE**: `adjudicate_key_signature` reads the ladder of SLOTS it
  already reads (2.9) over the widened marker set, and requires the header
  window; a marker right of the first notehead is DECLINED with a named
  reason, not filtered away.
* **RED first**: a test asserting that a Breitkopf header cell holding only
  `accidentalFlat` boxes produces a `Q.KEYSIG_MARKER` row. It fails on the
  unrepaired tree — 503 such boxes on Breitkopf, 115 on Litolff, on 246 and 64
  staves. The positive control in the same class: a cell-0 `accidentalFlat`
  standing RIGHT of the first notehead must still be declined, or the test
  passes by admitting everything.
* **GATE**: every staff that loses a header accidental today gains a marker
  row; 0 staves whose key is DECIDED today change value; Sean's 46-staff
  adjudication does not get worse. **Two re-gathers.**
* ⚠️ **This is 2.9b's other half and must land with it, not against it.**

---

**2.12b — a rest's value comes from the line it hangs on, corroborated by its
class.** *(reach 567; Litolff 300 — 102 landing on the other convention, 198
on neither; Breitkopf 267 — 32 and 235)*

* **GATHER**: unchanged. `Q.REST` already carries `bbox_page_px`, and
  `Q.STAFF_LINES` + `Q.CELL_STAFF_SPACE` are already on the record. **No
  re-gather.**
* **ADJUDICATE**: `_rest_ruling` computes `_staff_step` — the function
  `adjudicate_notehead_is_a_whole_rest` already uses, CALLED not copied — and
  compares the class's claim with the measured slot. Agreement → DECIDED as
  today. Disagreement where the measurement lands on the other convention →
  NARROWED over both, which EXPORT already refuses to argmax
  (`duration_narrowed`). Disagreement landing on neither → ABSTAIN
  `rest_stands_where_no_rest_hangs`.
* **RED first**: a fixture rest labelled `restHalf` sitting at half-step 2.5.
  It reads 2.0 beats today. Positive control: a `restWhole` at 2.5 must stay
  DECIDED at 4.0, or the rule passes by narrowing everything.
* **GATE**: 0 change on the engraved record (216 of 216 already agree — the
  control that can fail); at most the 102 + 32 measured disagreements move to
  NARROWED; `status_census.unaccounted` stays empty. Sean adjudicates ten
  crops of the `lands_on_neither` population before any of it is acted on.
* ⚠️ The two conventions are ONE half-step apart on a plate that bows; the
  `lands_on_neither` bucket (198 + 235) is bigger than the repairable one and
  is a different finding. **Do not let this line grow to cover it.**

---

**2.12c — a small filled dot's role comes from where it sits, not from which
of two classes the detector picked.** *(reach 672; Litolff 116, Breitkopf 555)*

* **GATHER**: `gather_rhythm_marks` files `Q.AUG_DOT` for `augmentationDot`
  AND `articStaccato*`, with `detail.detector_role`; `gather_glyph_families`
  does the same for `Q.ARTICULATION_MARK`. ⚠️ Two rows from ONE reader on one
  glyph is the correlation fault — so this must be ONE quantity carrying a
  `detector_role` detail, not two quantities on one subject. **Two
  re-gathers.**
* **ADJUDICATE**: `adjudicate_duration`'s `_attached_dots` already owns the
  asymmetric window (0.75 above, 0.25 below, in staff spaces) and becomes the
  decider: a dot inside the window and RIGHT of the head's ink is an
  augmentation dot whatever its class; one above or below is an articulation.
  Both outcomes are DECIDED; neither → ABSTAIN.
* **RED first**: a Breitkopf cell where an `articStaccato*` box sits right of
  a head and level with it (43 measured, 9 on Litolff) must dot the note.
  Positive control: a real staccato one space above must NOT.
* **GATE**: the 512 + 107 `aug_dot` rows not right of any head stop dotting;
  the 43 + 9 staccatos sitting where a dot sits start dotting; bar sums do not
  get worse on any of the three records; engraved unchanged (population 4).

**BUILT AND MEASURED 2026-09-28** (`claude/dot-role-2.12c` `67e320ae`, not
merged). GATHER and ADJUDICATE landed as planned above, ONE quantity
(`Q.AUG_DOT`, `detail.detector_role`), never two. EXPORT did not: the plan's
"one above or below is an articulation" would have routed a staccato-role
mark back through `Q.ARTICULATION_MARK`/`articulation_owner`, and gather no
longer files a staccato-classed box there at all (the correlation fix
forbids it) — so a new decision, `adjudicate_dot_role` (`Q.DOT_ROLE`), and a
new export function, `_place_dot_role_marks`, carry the role and the
placement instead. `_attached_dots`'s own window test was pulled out to
`_in_augmentation_window` unchanged, so nothing that used to dot a note
stops dotting IT SPECIFICALLY for a reason other than a real geometry
failure.

### The measurement (before any cut)

`probe/dot_role_offsets.py` — every `augmentationDot` and `articStaccato*`
box on the three acceptance records, offset from its NEAREST notehead
centre, in staff spaces (dx: centre-to-centre, positive = right; dy:
centre-to-centre, positive = above). Read-only, no gather, no code path this
item touches. Breitkopf is the population the cut is taken from (6,816
`augmentationDot`, 2,818 `articStaccato*` — the larger, cleaner plate);
Litolff (MERGING, per CLAUDE.md §10) agrees on the SHAPE of the two clusters
and is markedly noisier, which the pricing run below explains further.

| population | dx cluster | dy cluster | n in cluster / total |
|---|---|---|---|
| `augmentationDot` | **+1.00 to +1.75**, peak 1.25–1.50 | **[-0.25, +0.75]** | 6,333 / 6,816 (93%) |
| `articStaccato*` | **[-0.25, +0.25]** | \|dy\| ≥ ~1.0, both signs | 2,378 / 2,818 (84%) |

The dy cluster for `augmentationDot` is an INDEPENDENT confirmation of the
already-shipped `DOT_ABOVE_NOTE_MAX_SPACES` (0.75) / `DOT_BELOW_NOTE_MAX_SPACES`
(0.25) — measured from the opposite side (dot-to-head instead of the
2026-09 116-dot calibration), landing on the same window. The gap the
`articStaccato*` cut is taken in is a real valley, not a smooth taper: the
dy histogram holds **19 of 2,818** rows in [0.50, 0.75) against **169** in
[0.75, 1.00) and **970** in [1.00, 1.25) — a 9x jump either side of 0.75.
The dx histogram for `articStaccato*` falls from 2,378 inside [-0.25,+0.25]
to 27 in [0.25,0.50) and 9 in [-0.50,-0.25) — nothing supports widening past
±0.5. **Cut: `STACCATO_CENTRED_MAX_SPACES = 0.5`, `STACCATO_OFFSET_MIN_SPACES
= 0.75`** (`tools/omr/staged/adjudicators/rhythm.py`). Full histograms:
`out/dot-role-offsets--<id>.json`.

⚠️ **CONVENTION ASSUMED / WHAT WOULD FALSIFY IT / NOT CONFIRMED.** Sean has
not adjudicated a single print crop of this family. Nine crops are cut below
(`out/print/*-d212c-*`); `VERDICT_none_yet: null` on every sidecar.

### RED → GREEN

`tools/omr/tests/test_staged_dot_role.py`, 12 tests: GATHER routes both
classes into `Q.AUG_DOT` and neither into `Q.ARTICULATION_MARK` (4 tests);
ADJUDICATE — RED (a staccato-classed box right of the head must dot the
note), the mirror (a dot-classed box above the head must not), a positive
control (a correctly classed and placed dot still dots), an ambiguous
offset abstains and feeds neither consumer (4 tests); EXPORT — a
staccato-role mark reaches the file without inflating `articulation_balance`,
an augmentation-role mark is not written as an articulation, an abstention
is counted by its reason, the whole population is a partition (4 tests). All
12 were RED against the pre-2.12c tree (`Q.DOT_ROLE` does not exist there)
and GREEN after. `pytest tools/omr/tests -m "not slow"`: 3,417 passed, 0
failed. `staged.check`: **253**, unchanged from main.

### Pricing — two one-page GATHERS, base (merge-base `ad7d473b`, a detached
worktree) vs arm (`67e320ae`), both clean, `--no-surya --no-ocr`

| | Litolff p3 | Breitkopf p1 |
|---|--:|--:|
| `Q.AUG_DOT` population | 6 → 15 | 49 → 68 |
| dots (`augmentationDot`-class) that stop dotting | 6 | 21 |
| — of those, DECIDED `staccato` instead (not just abstained) | 0 | 4 |
| staccatos (`articStaccato*`-class) that start dotting | 0 | 0 |
| `Q.DOT_ROLE` abstained (`dot_role_ambiguous` / no candidate) | 12 | 21 |
| `Q.DURATION` verdicts changed | 0 / 628 | 0 / 1,365 |
| real staccati reaching a file-shaped owner, TOTAL (was `articulation_owner`
  decided `staccato`, now `Q.DOT_ROLE` decided `staccato`, either origin
  class) | 4 → 3 | 16 → 19 |
| — of the arm total, RECOVERED from a `dot`-classed box the old path could
  never reach (staccato-class only) | 0 | 4 |
| — of the arm total, from the SAME staccato-classed population base owned | 3 | 15 |

**Zero durations move on either page.** That is not a null result: on
BOTH pages, every `augmentationDot`-classed row that now abstains was
*already* failing `_attached_dots`'s own (unchanged) window test before
2.12c — the window is the SAME code, just unnamed until now. What 2.12c
changes is that a box the pipeline silently dropped now says WHY
(`dot_role_ambiguous`, `no_notehead_or_rest_in_cell`) instead of vanishing
with no row at all — rule 8, the fallback CLAUDE.md forbids is exactly
"drop it and say nothing," and that is what the pre-2.12c tree did to every
one of these 27 rows.

**Net, Breitkopf GAINS three real staccati it never had a path to before**
(16 → 19): four `augmentationDot`-classed boxes turn out to sit centred and
clear of a head, and only a role decided from GEOMETRY — never from a
class the detector cannot be argued out of — can hand them to the
articulation path at all. That is the mechanism working in the direction
the audit predicted (row 6: "43 + 9 staccatos sitting where a dot sits").

**One real regression per page, measured, not hidden, on the
staccato-CLASSED population specifically:** both pages lose exactly ONE
staccato that `articulation_owner`'s wider tolerance (`_ARTIC_MAX_DX_
NOTEHEAD_WIDTHS`, measured in NOTEHEAD WIDTHS) placed and the 0.5-STAFF-SPACE
cut does not — Litolff's is `glyph/3/0/10/0/10` (centred at 0.70 spaces,
confidence 0.38); Breitkopf's is `glyph/1/0/1/5/16` (`dx_notehead_widths`
0.585 in the old measure, 0.725 staff spaces in the new one, confidence
0.49) — the SAME near-miss shape on both plates, both just past the cut,
both at confidence under 0.5. **The Litolff crop says this loss may not be
a loss at all** — see below.

**A finding this pricing run was not built to make, and made anyway:** two
of the nine crops below — one on Litolff (the LOST staccato) and one
"confirmed staccato" on the same page — land on the CUSP where two slur
segments cross below a notehead, not on a dot at all. Geometry disambiguates
ROLE (augmentation vs staccato) between two candidates that both exist; it
cannot say whether the ink is a real mark in the first place, and a slur
cusp sits in roughly the same place a staccato does. This is the audit's own
row 4 in a new costume ("two spellings of one head, both surviving NMS...
no adjudicator can repair it") and is NOT this item's to fix — flagged for
whoever picks up 2.12g or the ink-first line.

### Crops for Sean

`out/print/beethoven5-litolff-p3-d212c-*.png` (5) and
`out/print/brahms1-breitkopf-p1-d212c-*.png` (4), 9 total: the lost
staccato (slur-cusp candidate, above), three `stopped-dotting` abstentions,
one `confirmed-staccato`, one dot-classed row the geometry moved TO
staccato, and one unchanged positive control. GREEN = the five
`Q.STAFF_LINES`; RED corner bracket = the dot-or-staccato box itself; ORANGE
= the notehead the augmentation window matched, where one did.
`VERDICT_none_yet: null` on every sidecar and on both manifests
(`MANIFEST-*-d212c.json`) — nothing here has been print-confirmed.

---

**2.12d — a mid-staff `timeSig*` box states a meter only where the system
agrees.** *(reach 106; Litolff 23, Breitkopf 83)*

* **GATHER**: `_gather_meter_glyphs` keeps filing every `timeSig*` box and
  adds `detail.corroborating_staves` — the number `_meter_candidate_columns`
  already computes and throws away. **No new detection; one re-gather to file
  the detail.**
* **ADJUDICATE**: `adjudicate_meter` treats a mid-staff glyph with zero
  corroboration as evidence with a score, not as a reading; it may not carry a
  meter change alone.
* **RED first**: the five `timeSig4` on barline fragments CLAUDE.md §7
  records — a fixture cell holding one mid-staff `timeSig4` and nothing else
  must not change the meter. Positive control: Litolff p.62's real change (a
  whole system's worth of glyphs in cell 8) must still be read.
* **GATE**: 0 of the corroborated 31 + 360 columns change; the 23 + 83 lone
  ones stop carrying; bar-sum agreement does not fall on any record.
* ⚠️ **A wrong meter is dearer than no meter** — 390 LilyPond bar-check
  failures against 164. This line only ever makes the reader quieter, which is
  the safe direction.

---

**2.12e — a flag's stem direction is the stem's, not the flag's name.**
*(reach 48; Litolff 27 of 90 joinable cells, Breitkopf 21 of 527)*

* **GATHER**: unchanged — `Q.FLAG` and `Q.STEM` are both already on the
  record. **No re-gather.** A CONNECT, not a new mechanism.
* **ADJUDICATE**: `_attached_flags` already finds the flag through the stem
  that touches the head. Where the attached stem's decided direction
  contradicts the flag's class suffix, record it in
  `detail.detector_role_disagrees` and keep the STEM's answer — the flag's
  class contributes its HOOK COUNT only, which is the half `_flag_levels_for`
  actually reads.
* **RED first**: a fixture head with a decided down stem carrying a
  `flag8thUp` box must read stem-down. Positive control: agreement must stay
  DECIDED with no extra row.
* **GATE**: 0 durations change (the hook count is untouched); the 48
  disagreements appear on the record where none does today; `check` finds no
  new open finding.
* ⚠️ **The smallest reach in the table and the cheapest line in it.** It is
  here because 2 513 + 163 flags are UNJOINABLE today — the join, not the
  disagreement, is the finding.

---

**2.12f — the side an articulation or fermata sits on is measured, not read
off the suffix.** *(reach 1 134; Litolff 139, Breitkopf 989, engraved 6)*

* **GATHER**: `_artic_side` keeps returning the name's claim, filed as
  `detail.detector_role` rather than as `detail.side`. **One re-gather** (a
  detail rename is a gather change).
* **ADJUDICATE**: `adjudicate_articulation_owner` and `fermata_owner` measure
  the mark's y against the head they attach it to and file the measured side;
  a disagreement is recorded, and the MEASURED side wins for an articulation.
  ⚠️ For a FERMATA it wins nothing: `gather.py:868-872` records that a
  fermata's side is not an attach constraint — it hangs over whatever sounds
  beneath it, including a whole-bar rest it stands well above. So the fermata
  half is RECORD-ONLY until `export._mxl_note` stops writing an upright
  `fermata` element unconditionally.
* **RED first**: a Breitkopf `articAccentBelow` sitting above its head must
  attach above. Positive control: an `articAccentBelow` below its head must
  not move.
* **GATE**: `articulation_owner` decides where it abstains today; 0 fermatas
  change placement; the engraved record's 6 are adjudicated against the print
  first — they are this probe's own floor and may be the probe's error rather
  than the detector's.

---

**2.12g — one piece of ink is one reading: collapse the role-twin channels
before NMS.** *(reach 859 visible, plus an invisible half no record can count)*

* **DETECTOR**: `yolo_detector.detect` passes neither `iou_threshold` nor
  `agnostic_nms`, taking `0.7` / `False`, where the frozen legacy path — under
  which every measured figure in this repo was taken — uses `0.5` / `True`
  (`gather.py:356-373`; `benchmarks/omr-staged-dedupe-2026-09/FINDINGS.md`
  §6.1, ranked first, already probed: 755 detections / 55 overlapping
  same-category pairs against 709 / 16). Two arms: (i) the legacy settings;
  (ii) a NARROWER change that collapses only the role-twin channels
  (`*OnLine`/`*InSpace`, `*Above`/`*Below`, `*Up`/`*Down`) by taking the max
  of the twin rows before NMS, leaving genuinely different marks to compete.
* **ADJUDICATE**: nothing. The role then comes from
  `Q.NOTEHEAD_STAFF_POSITION`, which is already filed.
* **RED first**: a fixture cell where one head yields two boxes at IoU 0.94
  must yield one. ⚠️ **Run it against the unrepaired tree first** — 505 + 354
  such pairs exist, so it will be red.
* **GATE**: the 859 twin pairs collapse; the total notehead count does not
  FALL (the collapse must merge, never delete); `status_census.unaccounted`
  empty; the 20-row scan gate moves by less than its ±6 noise floor, or
  improves. **Two full re-gathers per arm — four in total.** The most
  expensive line here and the only one that can reach the invisible half.

---

## PART 2 — THE ARCHITECTURE QUESTION, SIZED NOT BUILT

### (a) Minimal — remove every role-filter in GATHER, decide roles in ADJUDICATE

What §5 is: the seven lines above, generalised. GATHER files the shape, the
position, and `detail.detector_role`; the adjudicators decide.

* **Fixes that the others do not**: it is the only option that produces a
  DECISION. Every other option here makes a role-half harder to misuse; this
  one replaces it with a measurement, on a record, with a reason and a right
  to abstain. It is also the only one whose unit of work is a single family,
  so it can be landed and priced one line at a time.
* **Costs**: about 8 call sites in `gather.py`, 5 adjudicators, 10 tests. Four
  of the seven lines need a re-gather (2.12a, c, d, f); three do not (2.12b,
  2.12e, and the adjudicate half of the others). Re-gather budget if each line
  lands alone: **8 full gathers** — roughly 51 h Litolff plus 5 h Breitkopf.
  Batched into one gather per landing pair, 2 gathers, which is what §5's
  ordering is designed to allow.
* **Risks**: widening a gather filter admits ink that was previously dropped
  silently, and a widened set is widened for EVERY score (the lexicon lesson,
  CLAUDE.md §10). Each line therefore needs its positive control in the same
  class or it passes by admitting everything. Second risk: an adjudicator that
  now decides where it abstained is a new DECIDED population with no print
  behind it — 2.12b's gate names Sean's crops for exactly that.
* **What it does NOT fix**: row 4 / 2.12g. A twin pair is created before
  `gather.py` sees anything, and the head lost to a sub-threshold split has no
  subject for any stage to reason about.

### (b) Canonicalise at the reader — split shape and role in `canonicalize_names`

Extend `class_aliases.canonicalize_names` (the ONE place the model's `names`
are read, CLAUDE.md §9) so a detection arrives as `shape` + `detector_role`
and no later code can see a role-half by accident.

* **Measured blast radius** (`grep -rn smufl_name tools/omr/staged`): **49
  sites in 26 functions** — `gather.py` 33, `positions.py` 10,
  `review/human_evidence.py` 3, `gather_coverage.py` 1,
  `adjudicators/rhythm.py` 1, `adjudicate.py` 1. Tree-wide excluding tests:
  **270**. In `tools/omr/tests`: **131**. The heaviest single functions are
  `positions.gather_band_positions` (5), `gather_dynamic_letters` (4), and
  `gather_detections` / `gather_wedge_boxes` / `gather_clef` /
  `_gather_meter_glyphs` / `positions.gather_step_positions` (3 each).
* **Fixes that the others do not**: it is the only option that makes the fault
  UNREPEATABLE. The same collision was found three times in one day; a
  vocabulary where the role-half is not spelled into the shape name cannot be
  filtered on by a fourth lane that has not read this document.
* **Costs**: the 49 staged sites plus the 131 test sites, and every FINDINGS
  file, benchmark JSON and committed record that spells a class the old way
  becomes unreadable against the new spelling. `unaccounted()` and the
  208-name vocabulary of record both change. The committed records are the
  real cost: this probe, `trace.py`, `export_coverage` and `score_reading` all
  key on the printed class name.
* **Risks**: it delivers **zero** decided-from-geometry roles by itself. It is
  a rename. And a rename touching 270 sites on a path where CLAUDE.md already
  records eight bugs of the form *a signal recognised correctly and thrown
  away on the way out* is a large chance to add a ninth.
* **Verdict**: **do not do this as a refactor.** Do the cheap half instead: a
  new `check` part, derived by AST the way `test_flag_default_direction.py`
  already derives the flag convention, that FAILS when a module under
  `tools/omr/staged/` tests a string ending in a role suffix or beginning
  `key` / `accidental`. One file, no re-gather, and it buys the guarantee
  without the rename.

### (c) Ink-first, candidates per box — Sean's description, sized

**Measured** (`probe/ink_vs_boxes.py`, on the two committed `--ink-rows`
records: Litolff pp.1–4 `e38dbc25` `dirty: false`, Breitkopf pp.0–3 `27311d68`
`dirty: false`; a box COVERS a component when it holds at least 50 % of the
component's area):

| | Litolff (MERGING) | Breitkopf (SHATTERING) |
|---|--:|--:|
| ink components | 7 093 | 15 212 |
| detector boxes | 8 486 | 12 932 |
| components covered by **no** box | 3 651 (**51.5 %**) | 7 335 (**48.2 %**) |
| components covered by exactly one box | 2 340 (33.0 %) | 4 789 (31.5 %) |
| components covered by 2 or more boxes | 1 102 | 3 088 |
| components carrying **more than one notation class** (excluding `staff` and `stem`) | 281 (**4.0 %**) | 1 146 (**7.5 %**) |
| boxes covering **no whole** component | 5 441 (**64.1 %**) | 7 190 (**55.6 %**) |
| boxes covering exactly one | 2 256 (26.6 %) | 3 941 (30.5 %) |

The genuinely contested components, `staff` and `stem` excluded, are exactly
the role conflations this audit found: Litolff `dynamicF|dynamicS` 90,
`slur|tie` 15, `beam|slur` 12, `noteheadBlackInSpace|noteheadBlackOnLine` 11;
Breitkopf `beam|slur` 99, `slur|tie` 69, `beam|tie` 66, `augmentationDot|tie`
65, `articAccent` twins 35.

**What this says.** The ink-to-box join is not one-to-one and is not close.
**About half of every plate's ink is covered by no detector box at all**, and
on the MERGING plate **64 % of boxes cover no whole component** — a Litolff
notehead's box bounds part of a merged blob, which is precisely what `Q.INK`'s
own FINDINGS record (*Litolff MERGES, Breitkopf SHATTERS; it does NOT transfer
at full strength*). And the "several candidate labels per box" population that
ink-first exists to serve is **4.0 % – 7.5 %** of components from today's
post-NMS output.

* **The detector call would have to change, and exactly how**: `predict()`
  runs NMS inside ultralytics and returns `boxes.cls` (the argmax) and
  `boxes.conf` (that class's score only). Per-class scores are **not
  available** from `results.boxes`. Two routes. (1) Call
  `self._model.model(im)` directly and slice the raw prediction tensor —
  `preds[:, 4:, :]` is the per-class sigmoid score for every anchor — then do
  your own top-k and your own class-agnostic NMS. (2) Reach ultralytics' own
  NMS with `multi_label=True`, which emits one row per class above the
  threshold for one box. ⚠️ `ultralytics 8.4.50` (the version installed) does
  **not** expose `ultralytics.utils.ops.non_max_suppression` — the import path
  has moved, so route 2 needs a version probe before it can be costed. Either
  way this is a change at the detector call, and every measured figure in this
  repo was taken under the current one.
* **What `record` would have to hold**: a glyph subject's last coordinate is
  an INDEX INTO THE DETECTOR'S OUTPUT for that cell (CLAUDE.md §4b). An ink
  subject inverts that — the component becomes the subject and a box becomes a
  row on it. The ordinal space exists already (`_CV_GLYPH_BASE` = 100 000,
  ink at 200 000); the SUBJECT TREE does not. `record.py`, `record_io.py`,
  `record_slim.py`, `trace.py`, `reach.py`, `wiring.py`, `gather_coverage.py`
  and `positional_store.py` all key on the current tree.
* **Which adjudicators would become "choose among candidates"**:
  `Outcome.NARROWED` with candidates and per-candidate support already exists,
  and INFER already knows how to collapse one to a reader's own candidate. So
  `clef`, `duration`, `key_signature`, `arc_kind`,
  `notehead_is_a_whole_rest` and `meter` change SHAPE but not KIND. EXPORT
  already refuses to argmax a narrowing, and `status_census` would gain a
  `no_candidate_chosen` family.
* **What the derived checks would report**: `gather_coverage` would compare
  declared quantities against INK components rather than detector families, so
  its "detector families with no quantity" column is replaced by "ink with no
  reading" — the 48–52 % above, which is a far louder number than anything
  `check` prints today. `reach` and `wiring` are unaffected in kind.
* **Size**: about 10 files in `staged/`, the detector call, the vocabulary,
  and **four full re-gathers minimum** (two arms x two scan documents) before
  anything can be priced. The ink layer alone is 115 MB/page on Breitkopf in
  its component form. Realistically a multi-week lane.
* **Risks**: the largest surface and the least measured ground beneath it. And
  the number it is built on — candidates per box — is 4–7.5 % today. ⚠️ **The
  candidates it needs do not exist until the detector call changes, so (c) is
  DOWNSTREAM of (e), not an alternative to it.**

### (d) A shape-only detector

Retrain or graft the head onto shape families only (flat / sharp / natural;
black / half / whole head; C / F / G clef; rest shapes), leaving every role to
geometry.

* **The corpus**: 5 764 hand-drawn boxes over 1 060 label files, 84 distinct
  classes (`data/user-labeled/`, membership per `catalog-versions.txt`).
  **4 713 of them — 81.8 % — carry a role-half**, in 47 of the 84 classes:
  noteheads `OnLine`/`InSpace` 2 777, `tie`/`slur` 536, `accidental*` 405,
  `augmentationDot` + `articStaccato*` 342, `key*` 229, artic and fermata
  sides 185, `restWhole`/`restHalf` 188, flags 64, `clefC*` 49, digits 44.
  Collapsing them is a relabel of four fifths of the corpus — mechanical for
  the suffix families, **not** mechanical for `key*` vs `accidental*` (there
  the role IS the answer, not a suffix) or for `augmentationDot` vs
  `articStaccato*`.
* **Why training is the wrong instrument here, already measured**: round 5
  (`benchmarks/omr-labeling-survey-2026-09/ROUND5_METHOD_2026-09-04.md`) shows
  it is **class deletion, not suppression** — `tie` 249 → 0, `slur` 184 → 0,
  `beam` 188 → 0, `augmentationDot` 150 → 0, `accidentalFlat` 80 → 0,
  `restWhole` 396 → 0 across every method arm, with median confidence going
  UP (0.669–0.698 against production's 0.604). Eleven method arms failed. The
  recipe that works is head surgery (`merge_class_head.py`): a YOLOv8 detect
  head is per-class in its last layer, `model.22.cv3.{0,1,2}.2` — one weight
  row and one bias per class — and surgery puts the BASE's row back for a
  class the corpus never labels.
* **Fixes that the others do not**: nothing (a) and (e) do not, at far greater
  cost. Surgery RESTORES rows; it does not COLLAPSE them, and collapsing is
  what a shape-only vocabulary needs.
* **Costs**: a relabel of 4 713 boxes, a new vocabulary of record, a new
  weights file, three-axis gating per candidate
  (`benchmarks/omr-labeling-survey-2026-09/`), plus every consumer in (b)'s
  270 sites, plus four re-gathers.
* **Risks**: CLAUDE.md §9's measured facts apply directly — fine-tuning on
  this corpus deletes classes; 41 % of hollow-cell ink is never boxed, so
  anything the passes did not sweep trains as background; the labeled cell
  PNGs are not regenerable, so a bad relabel is not undoable.
* **Verdict**: **refused on cost.** But note the useful half of it: the
  collapse it wants can be done at INFERENCE on the existing weights, with no
  training and no labels — which is (e).

### (e) Collapse the role-twin channels at inference — the cheaper half of (d)

The idea (e) takes from (d): a YOLOv8 head is per-class in its last layer, so
`noteheadBlackOnLine` and `noteheadBlackInSpace` are two output channels
scoring the same ink. Take the **max** of the twin channels before NMS
(YOLOv8 scores each class with a sigmoid, not a softmax, so max is the
calibrated collapse and a sum is not) and one head yields one box. Nothing is
retrained; nothing is relabelled; the twin rows keep their weights and are
simply not allowed to compete with each other.

* **Fixes that the others do not**: it is the ONLY option that reaches the
  invisible half — a head whose evidence split across two channels and left
  both under `conf 0.25`, emitted as neither spelling and therefore with no
  subject any stage could repair. It also removes the 859 visible twin pairs
  with no adjudicator change at all, because once the pair is one box the role
  comes from `Q.NOTEHEAD_STAFF_POSITION`, which is already filed.
* **Costs**: one function in `yolo_detector.py` (about 30 lines) and the twin
  table, DERIVED from the vocabulary by suffix rather than hand-listed. **Two
  full re-gathers per arm.** No labels, no training, no new weights file, no
  vocabulary change.
* **Risks**: the collapse must MERGE and never DELETE — the gate has to assert
  the total notehead count does not fall, or this is exactly the note-deleting
  rule CLAUDE.md warns OMR-NED will reward. And the suffix table must be
  derived from the class space, because a hand-written second list is how the
  `_CLEF_CLASSES_INCUMBENT` drop happened (`gather.py:259-268`: it admits the
  spelling that never occurs and drops the two that do).
* **Its sibling arm**: simply passing the legacy `iou_threshold=0.5,
  agnostic_nms=True` under which every measured figure in this repo was taken.
  Cheaper still, and already probed (755 detections / 55 same-category
  overlapping pairs → 709 / 16), but blunter: it suppresses across ALL
  classes, so a real `ff`'s two adjacent letters are at risk. Run both arms;
  they answer different questions.

**(e2), considered and refused — segmentation masks instead of boxes.**
DeepScoresV2 ships instance masks, and a segmentation head would make the
ink-to-box join exact, which is (c)'s hardest problem. But it is a full
retrain of a head this project has measured eleven times as collapsing on this
corpus, on top of a class space that is already spelled twice, and there is no
fallback equivalent to head surgery for a seg head. Priced worse than (d).

### 6. Recommendation

**Do (a), family by family, in §5's order, and make (e) its second step.**

(a) is not recommended because it is cheap — it is recommended because it is
the only option that converts a role-guess into a DECISION with a reason and a
right to abstain, and because its unit of work is one family, so each line is
independently priced, independently landed and independently reversible. Per
unit of work it yields the most decided-from-geometry roles by a wide margin:
**2 156 boxes across four lines** (2.12a, b, c, d) where the role-half is both
wrong AND consumed, of which **2.12b and 2.12e need no re-gather at all**
because every quantity they read is already on the record. **Its second step
is (e)** — a second step rather than a first, because (e) changes the
detection set and so invalidates the baseline every (a) line is measured
against, but (e) is the only thing in this document that can reach the 859
twin boxes and the invisible head behind them, which no adjudicator will ever
repair. **(b) is right as a `check` part and wrong as a refactor**: derive the
rule by AST so no fourth lane can add an eleventh role filter, and do not
rename 270 sites to buy it. **(c) is where this points and is not affordable
yet** — half of every plate's ink is covered by no box at all, only 4–7.5 % of
components carry more than one notation class, and the candidate labels it is
built to consume do not exist until the detector call changes, which is (e);
revisit it once (e) has landed and that number has been re-measured. **(d) is
refused**: its useful half is (e), done without training, without labels and
without a new vocabulary.

---

## 7. What this lane did NOT establish

* **No accuracy claim anywhere.** Every number is a count of a DISAGREEMENT
  between a class name and a measurement. Which of the two is right is Sean's
  question against the print, and not one crop was cut in this lane. The
  `lands_on_neither` rest bucket (433 boxes) and the engraved record's own
  6 + 11 + 1 + 1 are the first things to send him.
* **Two of the three acceptance records are DIRTY** (§0). Fine for a census;
  not a baseline.
* **The probe cannot see a GATHER change** — it reads a saved record, so it
  shares the blind spot `check`'s parts have (CLAUDE.md §4d). Every line in §5
  that widens a gather filter is priced by two full re-gathers and by nothing
  in this directory.
* **`f_flag_stem` joins only the unambiguous cells** — 90 of 253 flags on
  Litolff, 527 of 3 040 on Breitkopf. The disagreement rate over the joinable
  population (27/90 and 21/527) is what is measured; whether it holds over the
  2 676 unjoinable ones is unknown, and re-deriving `_attached_flags`'s stem
  attachment inside a probe would have been a second, drifting copy of the
  rule.
* **`f_timesig_role` uses corroboration as a PROXY for "the geometry supports
  this role".** A lone mid-staff `timeSig4` on a page that really does change
  meter on one staff alone would be counted as a disagreement. The engraved
  control returns 0 and Litolff p.62's real change is corroborated 31 times,
  so the proxy separates — but it is a proxy.
* **`f_rest_whole_half` cannot distinguish a role error from bad ink.** Of the
  567 disagreements, only 134 land ON the other convention; 433 land on
  neither and are a different finding.
* **Nothing here was run RED against an unrepaired tree**, because nothing
  here is a repair. Each §5 line names its own RED test and its own positive
  control; none of them has been written.
* **The ink figures are FOUR PAGES of each plate**, not a movement — the
  acceptance records are all in roadmap 1.1's summary ink form, which
  aggregates away the per-component geometry (c) is about.

---
---

# PART 3 — THE TWO RE-GATHER-FREE LINES, BUILT

**2026-09-23** · branch `claude/shape-role-b-e-2.12`, base `de6213e7` ·
`tools/omr/staged/adjudicators/rhythm.py`,
`tools/omr/tests/test_staged_rest_slot_and_flag_direction.py`,
`tools/omr/staged/reach.py`, `docs/engraving-conventions.md` C17.

Both lines are ADJUDICATE-only, as §5 priced them, so `readjudicate_b_e.py` is
the right instrument and its blindness to GATHER costs nothing here.

### How every number in Part 3 was produced

```bash
python3 benchmarks/omr-shape-role-2026-09/probe/rest_slot_and_flag_join.py --all
python3 benchmarks/omr-shape-role-2026-09/readjudicate_b_e.py <record> --label <id> --off --out out/be--<id>--base.json
python3 benchmarks/omr-shape-role-2026-09/readjudicate_b_e.py <record> --label <id>       --out out/be--<id>--arm.json
python3 benchmarks/omr-shape-role-2026-09/compare_b_e.py        # the tables below
python3 benchmarks/omr-shape-role-2026-09/probe/crop_rest_slot.py --all
```

⚠️⚠️ **BASE AND ARM ARE BOTH REBUILT ON THIS TREE AND THE RECORD IS NOT THE
BASELINE** (CLAUDE.md §6b). `--off` returns the two new rules to the nothing
they produced before — `_rest_slot_verdict` returns `None`, `_flag_direction`
returns `{}` — so the difference between the runs is this lane and nothing
else. Wall time: Litolff 11 min per arm, Breitkopf 47 and 42 min, engraved 12 s.

**The control, printed before any delta:**

| record | `--off` reproduces the record's own `duration` verdicts | what differs |
|---|---|---|
| Litolff (`dbc9962b`, **dirty**) | 14,461 of 14,530 | 69 `narrowed → decided` |
| Breitkopf (`47fbff1e`, **dirty**) | 32,369 of 32,656 | 287 `narrowed → decided` |
| engraved (`f48a59ce`, clean) | **688 of 688** | — |

The 69 and 287 are **the tree having moved since those records were gathered**,
not this lane: every one is a beam-ambiguity narrowing that today decides. The
engraved record, the only clean-tree one, reproduces exactly — which is what
says the rebuild itself is sound and the two shortfalls are the inputs.

---

## §2.12b — A REST'S VALUE COMES FROM THE LINE IT HANGS ON

> ⚠️⚠️ **SUPERSEDED IN ITS NUMBERS BY PART 4 (§2.12b-cal), 2026-09-23.** Sean
> adjudicated all ten `lands_on_the_other_convention` crops this section cut:
> **ten of ten are whole rests**, so `REST_SLOT_SLACK = 0.5` — the constant
> named below — was measuring the convention's nominal line and not these
> plates. It no longer exists; the bands are measured. Everything in this
> section about the RULE'S SHAPE (three outcomes, never flips, the mirror
> `_staff_step`, the `neither` bucket's ownership half) stands unchanged.

### The change

`_rest_ruling` took a rest's value off its class. C17 says in terms that *the
vertical slot is the rest's IDENTITY, not decoration — NO shape, size or
aspect-ratio classifier can ever separate a whole rest from a half rest*, so
the detector choosing between those two classes reports something it cannot
know. The slot is now MEASURED with `_staff_step` — **the function
`adjudicate_notehead_is_a_whole_rest` already uses, CALLED not copied**,
because the two ask one question from opposite sides.

| the slot says | verdict | EXPORT |
|---|---|---|
| `class_not_contradicted` | DECIDED, exactly as before | written |
| `lands_on_the_other_convention` | **NARROWED** over both values, measured one first | refuses to argmax → `rest_duration_narrowed`, counted |
| `lands_on_neither_convention` | **ABSTAINED** `rest_stands_where_no_rest_hangs` | `rest_duration_abstained`, counted |
| nothing measurable | DECIDED as before, `slot: no_page_frame` / `no_staff_geometry` | written |

**It does not FLIP a value.** C17's own *Known exceptions* name two killers for
the absolute slot on this repertoire — a scanned staff tilts and bows up to a
whole step, and *in multi-voice writing rests are displaced from their default
position*, which destroys the absolute-position discriminator outright.
Deciding from the slot would be a default flipped on agreement with our own
reading (rule 5) before one crop has been adjudicated. Where the ink lands on
NEITHER slot there is no fallback to the class either: the class is the guess
the ink has just contradicted, and 4.0 quarters of silence is a very loud
answer to *we cannot tell* (rule 8).

⚠️ `class_not_contradicted` is **not** *the slot confirms the class*, and the
weaker word is the true one: the predicate is asymmetric (a rest must be
nearer the OTHER slot BY MORE THAN THE SLACK before the class is contradicted
at all), so ink displaced away from BOTH slots lands there too.

Constants: `HALF_REST_STEP` is **derived** from `WHOLE_REST_STEP` — the whole
content of the convention is *one line apart*, and two typed constants would
be free to drift into a gap that is not one line. `REST_SLOT_SLACK = 0.5` is
the audit probe's own constant, so the population this rule acts on and the
population §1 reported are the same population. `_REST_SLOT_BY_CLASS` holds
exactly two classes: every other rest names its value by its SHAPE.

### Per record — what the slot said

| | Litolff | Breitkopf | engraved |
|---|--:|--:|--:|
| `restWhole` + `restHalf` on the record | 1,642 | 2,104 | 216 |
| measurable against the staff | 1,642 | 2,104 | 216 |
| `class_not_contradicted` | 1,342 | 1,837 | **216** |
| `lands_on_the_other_convention` | 102 | 32 | **0** |
| `lands_on_neither_convention` | 198 | 235 | **0** |
| median step, `class_not_contradicted` (nominal **5.5**) | 5.52 | 5.33 | 5.45 |
| median step, `lands_on_the_other_convention` (nominal **4.5**) | 4.53 | 4.65 | — |

**The engraved record is the control that can fail, and it does not fire**:
216 of 216 land in `class_not_contradicted`, and the export is identical in
every count in both arms. The two medians are the frame control this rule
needed and did not have — **the convention holds on both plates and on the
render**, to within 0.2 of a half step.

⚠️ The adjudicator's frame (`_staff_step`: bottom line 0, up positive, whole
5.5 / half 4.5) and the audit probe's (top line 0, down positive, whole 2.5 /
half 3.5) are a reflection of each other, and they were checked rather than
assumed: **they give the same verdict on all 3,962 rows**
(`frames_disagree: 0` on every record).

### On the record, after EVALUATE and INFER

| | Litolff base → arm | Breitkopf base → arm |
|---|---|---|
| `duration` DECIDED | 13,054 → 12,760 | 28,651 → 28,385 |
| `duration` NARROWED | 1,476 → 1,572 | 3,979 → 4,010 |
| `duration` ABSTAINED | 0 → 198 | 26 → 261 |
| reason `rest_slot_contradicts_class` | 0 → **99** | 0 → **31** |
| reason `rest_stands_where_no_rest_hangs` | 0 → **198** | 0 → **235** |

⚠️ **99 SURVIVING NARROWINGS AGAINST 102 MEASURED, AND THE THREE MISSING ARE
THE SYSTEM WORKING.** The adjudicator narrowed 102; INFER then collapsed three
of them to one of *that reader's own candidates* (`+3` on
`the_neighbours_run_to_the_same_barline`), which is exactly the licence
`infer.py` has and could not exercise while the verdict was a bare DECIDED
value. Breitkopf's 31 against 32 is one such collapse. The narrowing is
therefore not only a refusal — it is what gives a later stage something to
work on.

⚠️ The 26 Breitkopf ABSTENTIONS in the BASE are **not** this rule: they are the
pre-existing `unreadable_rest`, `restHBar` / `restHNr` multi-measure
indicators that name no single value.

### The file

| | Litolff base → arm | Breitkopf base → arm | engraved |
|---|---|---|---|
| `<note>` (rests included) | 8,605 → **8,696** | 7,822 → **7,872** | 666 → 666 |
| `<rest>` | 4,950 → 4,898 | 6,679 → 6,696 | 335 → 335 |
| `measure="yes"` | 4,385 → 4,309 | 5,514 → 5,497 | 251 → 251 |
| pitched notes (`<note>` − `<rest>`) | 3,655 → **3,798** | 1,143 → **1,176** | 331 → 331 |
| `rest_duration_narrowed` | 0 → 99 | 0 → 31 | 0 |
| `rest_duration_abstained` | 0 → 198 | 26 → 261 | 0 |
| `bar_does_not_add_up` (events) | 5,416 → **5,046** | 19,022 → **18,791** | 42 → 42 |
| **bars held out (2.8)** | 1,874 → **1,771** | 4,565 → **4,525** | 36 → 36 |
| bars moved **INTO** the held set | **0** | **0** | **0** |
| bars moved **OUT** of the held set | **101** | **40** | 0 |
| `status_census.unaccounted` | `[]` → `[]` | `[]` → `[]` | `[]` |
| accounting `balanced` | True → True | True → True | True |

⚠️⚠️ **THE RESULT IS THAT REFUSING 563 REST DURATIONS LET 141 BARS START
ADDING UP, AND NOT ONE BAR STOPPED.** The direction is asymmetric by
construction — a rest that no longer claims 4.0 quarters cannot make a bar
*longer* — but the asymmetry was predicted, not assumed, and the count is
measured: 0 in, 141 out, on two plates that fail in opposite ways. 176 more
pitched notes reach the file because their bars now balance.

⚠️ This is **not** an accuracy claim. Nothing says the 141 bars now hold the
RIGHT notes; it says they hold a sum the meter admits, which is what 2.8's
hold-out is a proxy for. The count that decides is Sean's.

### ⚠️⚠️ THE FINDING UNDER THE `lands_on_neither` BUCKET: IT IS MOSTLY NOT ABOUT RESTS

§5 said *the `lands_on_neither` bucket is bigger than the repairable one and is
a different finding — do not let this line grow to cover it.* Cutting the crops
and looking at them says what that different finding IS.

| | Litolff | Breitkopf | pooled |
|---|--:|--:|--:|
| `lands_on_neither_convention` | 198 | 235 | 433 |
| …standing **BELOW** the staff it is filed on | 82 | **186** | 268 |
| …standing **ABOVE** it | 4 | 4 | 8 |
| …**inside** its own staff | 112 | 45 | 157 |
| median step of the bucket | 1.35 | **−7.31** (p10 −7.60) | — |

**276 of the 433 stand outside the staff they are filed on**, and Breitkopf's
186 are a tight cluster at step −7.3 — 3.65 spaces *below* the bottom line,
which is the next staff down. The measure cell is padded 4 staff spaces (6
where the neighbour is far) and on a conductor's page that reaches the next
staff's ink (CLAUDE.md §10).
`out/print/brahms1-breitkopf-p12-s0-st4-c13-g0-lands_on_neither_convention.png`
shows it plainly: the green `Q.STAFF_LINES` are one staff, the bracketed rest
is on the staff below, and it is hanging correctly under the fourth line **of
that staff**.

So that bucket is substantially `glyph_owner`'s contest showing through a
rest-reading probe, and only the 157 inside-the-staff rows are a rest question
at all.

⚠️ **IT IS RECORDED AND DECIDES NOTHING.** `detail.outside_its_own_staff` is
`below` / `above` / `null` on every measured rest, and the abstain reason
stays ONE word. *Which staff owns this ink* is `glyph_owner`'s contest —
ladder, then range, then distance, and a resolved contest DROPS the loser —
and a duration decision inventing an ownership verdict would be a second,
weaker copy of it wearing a rhythm decision's name. **This is a candidate
roadmap line, not a thing 2.12b may grow to cover.**

⚠️ And it cuts the other way too: 97 Breitkopf and 13 Litolff rests read
`class_not_contradicted` while standing wholly ABOVE their own staff. The
predicate's asymmetry protects them, correctly — but they are the same
ownership population wearing a bucket name that sounds like agreement, which
is why that bucket is not called `agrees`.

### The crops for Sean

`benchmarks/omr-shape-role-2026-09/out/print/` — **31 PNGs, 31 JSON sidecars,
2 manifests**, cut from the plate at the gather's own DPI (600, read off
`provenance.settings.args.dpi`, never assumed):

* 21 of `lands_on_neither_convention` (9 Litolff, 12 Breitkopf);
* 10 of `lands_on_the_other_convention` (4 Litolff, 6 Breitkopf).

Each carries GREEN `Q.STAFF_LINES`, a BLUE dashed line at the whole-rest slot
and an ORANGE dashed line at the half-rest slot **drawn from the adjudicator's
own `WHOLE_REST_STEP` / `HALF_REST_STEP`** (a crop with a ruler, CLAUDE.md
§6b), and a RED **corner bracket** on the exact rest — never a margin tick at
its x. The sample is a stride over the subject-sorted population, not the
first N, so it spreads across pages and systems.

⚠️ **THE FRAME CONTROL CAN FAIL AND DID**: 5 of Litolff's 18 candidates were
REFUSED with their contrast recorded (−103.89, −25.61, −23.50, 5.05, 7.77) and
are listed in the manifest rather than dropped. `_frame_ok` is imported from
`omr-infer-duration-print-2026-09/probe/crop_inferred.py`, not copied.

⚠️ `VERDICT_none_yet` is `null` on every sidecar and on both manifests.
**NOTHING IN 2.12b HAS BEEN ADJUDICATED AGAINST THE PRINT**, which is why the
rule narrows and abstains and flips no value.

### ⚠️ `Q.REST_POSITION` IS STILL UNREAD, AND THE REASON IS A TOOL BLIND SPOT

`reach.py` names `adjudicate_duration` as that quantity's FIRST CONSUMER, and
this was the day it should have come off the list. Two things stop it:

1. **It files ZERO rows on all three acceptance records** — `positions.py` is
   behind `OMR_FAMILY_POSITIONS`, which is DEFAULT OFF. A rule resting on it
   would be inert exactly where it is needed.
2. **Declaring it in `wants` opens a NEW `inventory --check` finding** —
   *"duration wants 'rest_position', which no gather site observes and no
   decision produces"* — because `inventory._producers` walks the AST of
   `gather.py` **and nothing else**, so every quantity `positions.py` observes
   is invisible to that tool.

Suppressing (2) with a `KNOWN_GAPS` entry would be gaming: a known entry is a
reason a gap EXISTS, never a reason one is acceptable. So the slot is measured
from the box and the staff, which every record carries, and **the blind spot in
`inventory` is now what that reach entry is about**. What `Q.REST_POSITION`
would still add is real and unmeasured: it reads which EDGE of the rectangle is
nearer a line and how decisively (`attach_margin`), which is strictly more of
the convention than a centre is.

---

## §2.12e — A FLAG'S STEM DIRECTION IS THE STEM'S

### The change

A CONNECT, not a mechanism (CLAUDE.md §2 rule 6). `_flag_direction` reads the
DECIDED `stem_direction` verdict on the notehead the flag is attached to,
files it as the flag's direction, records the class suffix beside it as the
detector's opinion, and marks `detector_role_disagrees` where they differ.
Where there is no decided direction it names WHICH silence —
`stem_direction_abstained` (with the abstention's own reason) or
`no_stem_direction_verdict` — because *no reader ran* and *the reader could
not say* are the distinction the record exists for.

**A disagreement never drops the flag.** Its SHAPE claim — how many hooks —
is what `_flag_levels_for` reads and what sets the duration, and it is
untouched. A note with no flag carries **no** `flag_*` key at all, so *no
flag* cannot be mistaken for *a flag with no direction*.

### Per record

| | Litolff base → arm | Breitkopf base → arm | engraved base → arm |
|---|---|---|---|
| flags attached to a head | 220 → 220 | 2,773 → 2,772 | 4 → 4 |
| direction from `stem_direction` | 0 → **153** | 0 → **2,528** | 0 → **4** |
| `stem_direction_abstained` | 0 → 34 | 0 → 50 | 0 → 0 |
| **class contradicts the stem** | 0 → **22** | 0 → **11** | 0 → **0** |
| `<note>` | 8,605 → 8,696 | 7,822 → 7,872 | 666 → 666 |
| `status_census.unaccounted` | `[]` | `[]` | `[]` |

⚠️ **THE `<note>` MOVEMENT IN THIS TABLE IS 2.12b's, NOT 2.12e's.** Both lines
ran in one arm. 2.12e's own gate is that **zero durations move**, and it is
met where it can be seen alone: on the engraved record the flag direction
lands on 4 of 4 flags and the file is identical in every count. The scan
columns cannot separate the two lines and are not quoted as if they could.

⚠️ `flags attached` 2,773 → 2,772 on Breitkopf. **One flag left the population,
and it is 2.12b's doing, not a lost flag**: a rest whose duration now abstains
takes its whole verdict — and its `flags_attached` tally — off the record.

### ⚠️ THE FINDING UNDERNEATH: THE AUDIT'S 2,676 UNJOINABLE FLAGS ARE 205

§5 said *the join, not the disagreement, is the finding*, on the audit's count
of **2,676** flags unjoinable to a stem (Litolff 163, Breitkopf 2,513). That
number is an artefact of the probe's own restriction, not of the adjudicator's
reach.

`f_flag_stem` joins only cells holding **exactly one** flag row and **exactly
one** DECIDED `stem_direction`, because a probe cannot re-run
`_attached_flags`. The adjudicator joins a flag to a head through the STEM that
touches both, so its population is *flags in a cell that holds at least one
decided direction*:

| | Litolff | Breitkopf | engraved | pooled |
|---|--:|--:|--:|--:|
| flags carrying a role half | 253 | 3,040 | 6 | 3,299 |
| in a cell with a decided `stem_direction` | 213 | 2,877 | 4 | **3,094** |
| **UNJOINABLE** | 40 | 163 | 2 | **205** |
| …because every direction in the cell abstained | 34 | 139 | 0 | 173 |
| …because no `stem_direction` verdict reached the cell | 6 | 24 | 2 | 32 |

**205, not 2,676** — and the adjudicator confirms it from the other side: it
sourced a direction for **2,685 of the 2,996** flags it found attached to a
head. The residue is dominated by `stem_direction` ABSTAINING (173 of 205),
which is `no_stem` and `stems_disagree`, not a join that does not exist.

⚠️ **THE AUDIT'S FIGURE IS NOT WRONG, IT IS A DIFFERENT QUANTITY**, and Part 1
said so at the time (*"whether it holds over the 2,676 unjoinable ones is
unknown"*). What is corrected here is the inference §5 drew from it — *2,676
flags are unjoinable today* — which reads as a reach problem and is not one.
**Do not open a roadmap line for the flag join on the strength of that
number.**

### The disagreement rate, and what it is not

33 disagreements over the 2,685 flags whose direction the stem answered —
**1.2 %** — against the audit's 27 of 90 and 21 of 527 over its narrower join.
Both are real; they are rates over different populations, and the wider one is
the one the pipeline actually has. Nothing acts on either: the disagreement is
on the record where none was, so the next lane can price it.

---

## Part 3's controls, tests and checks

* **RED first, with the split recorded.** Restore `rhythm.py` from `de6213e7`
  and `pytest tools/omr/tests/test_staged_rest_slot_and_flag_direction.py` is
  **19 failed, 4 passed**. The 4 that pass are the positive controls — a rest
  in its own slot still reads 4.0; the slack still protects a bowed plate; a
  contradicted flag still counts and still reads 0.5 beats (2.12e's whole
  gate); a note with no flag carries no `flag_*` key.
* `pytest tools/omr/tests -m "not slow" -q` — **3,039 → 3,062 passed**, 3
  skipped, 0 failed.
* `python3 -m tools.omr.staged.check` — **258 → 258**. `inventory --check` 12,
  `wiring --check` 69, `reach` 25 not LIVE / 0 unaccounted / 0 stale gap
  entries, `conventions --check` 0 findings.
* C17 in `docs/engraving-conventions.md` now names this consumer in its **Code**
  row, and its **Status** says the discriminator is *READ but still DECIDES
  NOTHING* — ⚠️ being read is not being measured, and the line must not be
  promoted to MEASURED HERE until Sean has adjudicated the crops.

## What Part 3 did NOT do, and the honest gaps

* **Nothing is print-confirmed.** 31 crops are cut and `VERDICT_none_yet` is
  null on all of them.
* **Neither scan record is a baseline** — both are dirty-tree gathers, and the
  `--off` control reproduces 99.5 % / 99.1 % of their duration verdicts, not
  100 %. The deltas above are base-vs-arm ON THIS TREE and are sound; the
  absolute counts are a census of those records, not of the pipeline.
* **The two lines were measured in ONE arm**, so the scan `<note>` movement
  cannot be attributed between them. Only the engraved record separates them,
  and there 2.12b moves nothing and 2.12e moves nothing.
* **The 157 inside-the-staff `lands_on_neither` rows are unexplained.** The 276
  outside-the-staff ones have a mechanism; these do not, beyond *ink standing
  where no rest of either kind hangs*.
* **`Q.REST_POSITION`'s edge witness is unmeasured.** It is strictly more of the
  convention than a centre and nothing here tests whether it separates better.
* **No LilyPond, no OMR-NED, no scan gate.** The staged path exports MusicXML
  only, and OMR-NED is the engraved control where this lane moves nothing.

---

# PART 4 — §2.12b-cal: THE BANDS CAME FROM THE PLATE

**2026-09-23** · branch `claude/rest-slot-cal-2.12b`, base `dd64da6a` ·
`tools/omr/staged/adjudicators/rhythm.py`,
`tools/omr/tests/test_staged_rest_slot_and_flag_direction.py`,
`docs/engraving-conventions.md` C17,
`benchmarks/omr-shape-role-2026-09/probe/rest_slot_calibration.py`.

**The fact this item starts from.** Sean adjudicated all ten
`lands_on_the_other_convention` crops §2.12b cut
(`out/print/ADJUDICATION-sean-2026-09-23-rests.json`): *"they are all whole
notes."* **Ten of ten are whole rests — the detector's `restWhole` was right
10 of 10 and the slot geometry wrong 10 of 10.** Their measured steps run
4.16–4.713 against a nominal whole-rest slot of 5.5. The rule NARROWED and
never flipped, so no value was lost; what was wrong was the band.

### How every number in Part 4 was produced

```bash
python3 benchmarks/omr-shape-role-2026-09/probe/rest_slot_calibration.py --all
python3 benchmarks/omr-shape-role-2026-09/probe/rest_slot_calibration.py --derive
python3 benchmarks/omr-shape-role-2026-09/readjudicate_b_e.py <rec> --label <id> --control
python3 benchmarks/omr-shape-role-2026-09/readjudicate_b_e.py <rec> --label <id> --old-bands --out out/cal--<id>--base.json
python3 benchmarks/omr-shape-role-2026-09/readjudicate_b_e.py <rec> --label <id>              --out out/cal--<id>--arm.json
python3 benchmarks/omr-shape-role-2026-09/compare_b_e.py --prefix cal
python3 benchmarks/omr-shape-role-2026-09/probe/crop_rest_slot.py --record <rec> --pdf <plate> --label <id> --moved
```

⚠️⚠️ **THE BASE IS §2.12b's NOMINAL BANDS, NOT THE PRE-2.12b NOTHING.** This
item changes exactly one thing — where the bands come from — so the base it
must be read against is 2.12b as merged. `readjudicate_b_e.py --old-bands`
restores that predicate verbatim and both arms are rebuilt on ONE tree
(CLAUDE.md §6b). `--off` is untouched and answers the other question; §2.12b's
own `be--*` artefacts are untouched, which is why this pass writes `cal--*`.

⚠️ **THE DERIVATION POPULATION IS PINNED TO THE NOMINAL BANDS AND CANNOT
WIDEN ITSELF.** `rest_slot_calibration.py` records `verdict_nominal` beside
`verdict` and the confirmed population is read off the first. Without that
pin, the moment the calibrated bands land the population grows by the 124 rows
they newly decide, and a re-run would "confirm" the wider band with the rows
that band itself admitted.

---

## 1. The measurement — where rests actually hang

Every `restWhole` / `restHalf` box on the three acceptance records, measured
with `rhythm._staff_step` (CALLED, not copied) against its own staff's
`Q.STAFF_LINES` and `Q.STAFF_SPACING` in page pixels. Frame: bottom line 0,
one step per half space, up positive — a whole rest hangs at 5.5, a half rest
sits at 4.5. **3,918 `restWhole`, 44 `restHalf`, 0 unmeasurable.**

### 1a. Per family, per record — the print-confirmed population

*Confirmed = the class §2.12b's bands do not contradict, standing inside its
own staff, plus Sean's ten.*

| record | family | n | p1 | p5 | p50 | p95 | p99 |
|---|---|--:|--:|--:|--:|--:|--:|
| engraved | `restWhole` | 215 | 5.43 | 5.43 | **5.45** | 5.473 | 5.497 |
| engraved | `restHalf` | **0** | — | — | — | — | — |
| Litolff | `restWhole` | 1,329 | 4.76 | 4.94 | **5.52** | 5.964 | 7.09 |
| Litolff | `restHalf` | **2** | 3.16 | 3.16 | 3.16 | 3.21 | 3.21 |
| Breitkopf | `restWhole` | 1,715 | 4.855 | 5.036 | **5.32** | 5.93 | 6.94 |
| Breitkopf | `restHalf` | **0** | — | — | — | — | — |
| **pooled** | `restWhole` | **3,259** | 4.79 | **5.01** | **5.412** | **5.91** | 7.06 |
| **pooled** | `restHalf` | **2** | 3.16 | 3.16 | 3.16 | 3.21 | 3.21 |

0.1-step histograms per record and per reference point are in
`out/rest-slot-cal--<id>.json` (`families.<class>.<population>.histogram_*`).

### 1b. ⚠️⚠️ WHERE THE TWO FAMILIES SEPARATE: NOWHERE, BECAUSE ONE IS EMPTY

The question this item asks — *the gap between the whole-rest distribution's
upper tail and the half-rest distribution's lower tail* — **has no answer on
these three documents, and that is the finding.**

* **The half-rest family does not exist here.** The detector says `restHalf`
  **44 times against 3,918 `restWhole`** (1.1%). Of the 44, **3 stand inside
  the staff they are filed on**: two on Litolff at steps 3.16 and 3.21, one at
  7.18. The other 41 are outside their staff — 31 of Breitkopf's 35 at step
  −7.4, the next staff down through the cell's 4-space pad, which is the
  ownership finding §2.12b already recorded.
* **The whole-rest family covers the half-rest slot completely.** Its low tail
  is a smooth ramp with no second mode and no trough anywhere near 4.5. All
  `restWhole` rows standing inside a staff, in 0.1-step bins, reading down:

  | step | 4.8 | 4.7 | 4.6 | 4.5 | 4.4 | 4.3 | 4.2 | 4.1 | 4.0 | 3.9 | 3.8 | 3.7 | 3.6 | 3.5 | 3.4 |
  |---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
  | n | 51 | 45 | 27 | 23 | 12 | 6 | 11 | 9 | 6 | 4 | 3 | 1 | 6 | 1 | 4 |

  §2.12b's threshold fell at **4.75**, in the middle of that ramp. Sean's ten
  are a direct sample of the rows below it, and they are the bottom **0.3%**
  of the whole population's own tail (4.16 at its 0.00-th percentile, 4.713 at
  its 0.28-th).
* **The only measured trough is at 3.4–3.9** — bins of 1–6 rows against 23–51
  just above, a full staff space below the half rest's slot. Nothing has ever
  been cropped there.

**So the plates show one rest distribution, not two, and any band claiming a
separation near 4.5 is claiming something the plates do not show.**

### 1c. ⚠️ THE MEASUREMENT POINT WAS CHECKED FIRST, AND IT IS NOT THE FAULT

A whole rest HANGS (top edge on the 4th line) and a half rest SITS (bottom
edge on the 3rd), so a box CENTRE is the right reading only where the box is
exactly one step tall. `_staff_step` reads the centre. Measured at all three
reference points on the confirmed population:

| record | height p50 | centre p50 | top p50 | bottom p50 | p5–p95 span: centre / top / bottom |
|---|--:|--:|--:|--:|---|
| engraved | 0.98 | 5.45 | **5.94** | 4.96 | 0.04 / 0.05 / 0.10 |
| Litolff | 1.32 | 5.52 | 6.16 | 4.897 | 1.02 / 1.14 / **0.98** |
| Breitkopf | 0.98 | 5.32 | 5.80 | 4.82 | 0.89 / 1.08 / **0.84** |

* **The convention is confirmed exactly on the engraved control**: box height
  0.98 steps, top edge 5.94 — the 4th line — bottom edge 4.96, centre 5.45.
  The nominal 5.5 is right to within 0.05 of a step.
* **The bottom edge is the tightest reading on both scans**, by 0.04 and 0.05
  of a step, and the height column says why: Litolff's boxes run 1.32 steps
  where the glyph is 1.0, and the extra height goes on at the TOP (top edge
  0.22 above the engraved one, bottom edge 0.06 below) — the rest touches its
  line and the merging plate takes the box up with it.
* **But that is a 0.05-step effect against a 1.0-step error.** Sean's ten sit
  a full step low at EVERY reference point: their top edges (4.50–5.32) are
  where an ordinary whole rest's BOTTOM edge is (4.82–4.90). No choice of
  reference point decides them.

**⇒ The fix is the BAND, not the reference point.** `_staff_step` is
unchanged, and the mirror rule `adjudicate_notehead_is_a_whole_rest`, which
shares it, is untouched.

---

## 2. The change

`REST_SLOT_SLACK = 0.5` — half the gap between the two slots, a statement
about the convention — is replaced by two named tolerances, and each class's
band is bounded **only on the side the other convention lies on**:

| constant | value | measured? |
|---|--:|---|
| `WHOLE_REST_STEP` | 5.5 | the convention, confirmed by the engraved control at 5.45 — **unchanged** |
| `HALF_REST_STEP` | 4.5 | DERIVED from it, never typed — **unchanged** |
| `REST_SLOT_TOLERANCE_WHOLE` | **1.35** | **MEASURED HERE** — 5.5 − 4.16, the lowest rest a musician confirmed off the print, rounded out to the next 0.05 |
| `REST_SLOT_TOLERANCE_HALF` | 0.5 | **NOT MEASURED** — the convention's own midpoint, kept because 3 half rests inside a staff is nothing to measure on, and a SEPARATE constant so the record can say which is which |

For a `restWhole`: **DECIDED** at step ≥ 4.15, **NARROWED** over both values at
3.15 ≤ step < 4.15, **ABSTAINED** `rest_stands_where_no_rest_hangs` below 3.15.
For a `restHalf`, the mirror about its own slot: DECIDED at ≤ 5.0, NARROWED at
5.0 < step ≤ 6.85, ABSTAINED above. Three outcomes, as before, and **no value
is ever flipped** — a row that gains a value gains the CLASS's own reading.

### ⚠️ Why the band is NOT the pooled p5/p95, which the item asked for

A ±(p95 − p5)/2 band is **±0.45** — the nominal 0.5 back again — and it
contradicts ten of ten rests a musician read off the plate. **The dispersion
of the BULK is not the extent of the POPULATION**: on a scan, warp and
multi-voice displacement move individual rests and not the median, so the TAIL
is the thing being measured. The p5/p95 numbers are reported in §1a and
refused as the band's source, with the reason.

### ⚠️ Why the tolerance sits BELOW its own plateau

Sweeping the lower edge over the whole `restWhole` population:

| tolerance | lower edge | decided | narrowed | abstained |
|--:|--:|--:|--:|--:|
| 1.25 | 4.25 | 3,475 | 47 | 396 |
| **1.35** | **4.15** | **3,484** | **49** | **385** |
| 1.50 | 4.00 | 3,494 | 59 | 365 |
| 1.60 | 3.90 | 3,500 | **68** | 350 |
| 1.70 | 3.80 | 3,505 | **68** | 345 |
| 1.80 | 3.70 | 3,506 | **68** | 344 |
| 1.90 | 3.60 | 3,509 | **68** | 341 |
| 2.00 | 3.50 | 3,513 | 65 | 340 |

The narrowed count is flat at **68 for a tolerance of 1.60–1.90** — the
measured 3.4–3.9 trough. **1.35 is deliberately under that plateau.** A band at
1.90 would DECIDE **25 more rows** that nobody has looked at, which is a
default flipped on agreement with our own reading (CLAUDE.md §2 rule 5); a
narrower band narrows instead, and a narrowing loses nothing because EXPORT
refuses to argmax one.

### ⚠️ Why neither band has an edge on its far side

There is no third rest convention above the whole rest's slot or below the
half rest's, so ink there is DISPLACED, not AMBIGUOUS — and displacement is
`glyph_owner`'s contest, not this decision's. **111 of the print-confirmed
rests stand outside their own staff altogether.** An upper edge on the whole
band would convert **2–3% of a print-confirmed population into abstentions**
(68 rows above 6.66, 41 above 7.0) to answer a question nothing asked. This is
a convention argument, not a tolerance choice, and a test pins it.

---

# PART 5 — §2.12d: A MID-STAFF `timeSig*` STATES A METER ONLY WHERE THE
SYSTEM AGREES

*(Branch `claude/meter-agree-2.12d`, 2026-09-28. Diagnosis:
`benchmarks/omr-bar-sum-holdout-2026-09/FINDINGS.md` §13, "the funnel", on
the fresh whole-movement Breitkopf Brahms 1/i record `c19cbca7`. This item's
own reach row in Part 3 above: reach 106 total, Litolff 23, Breitkopf 83.)*

## The mechanism, before this item

`adjudicate_meter` (`tools/omr/staged/adjudicators/rhythm.py`) already
computed a `corroborated` flag on every mid-system change candidate
(`METER_CHANGE_MIN_STAVES = 2`, A-METER-6) and used it for exactly ONE of the
two things a change does: it gated whether the change could be CARRIED to a
later, abstaining system (`_meter_in_force_at_end`). It did NOT gate whether
the change governed its OWN system's bars — A-METER-6 deliberately left that
half open, because on the boundary corpus available then (4 pages, two
scans) the one confirmed true single-staff change (Litolff p.62, a real
`3/4` read on 1 of 17 staves) was indistinguishable by support, staff count
or bar math from three false ones on the same corpus.

## The change

`METER_CHANGE_GATES_OWN_SYSTEM = True` — a plain module constant, not a
flag, per the roadmap item's own instruction ("NOT a new env flag"; the
constant is toggled directly by `price_2_12d.py` below, the same way this
suite's own tests already reference `rhythm_mod.METER_CHANGE_MIN_STAVES`
directly). `_meter_changes` now declines a candidate that clears
`METER_CHANGE_FLOOR` but not `METER_CHANGE_MIN_STAVES` BEFORE it can become a
segment: it is filed into a new `declined_changes` list on the system's
`Q.METER` value, under `declined_reason: "meter_change_not_system_wide"`
(`rhythm.METER_CHANGE_NOT_SYSTEM_WIDE`), and the meter in force is left
exactly as it was. A cautionary past the system's last barline (A-METER-5) is
tested FIRST and is unaffected either way. Where a system's ONLY candidate
meter fact is a declined lone-staff change, `_change_only` now abstains
outright rather than deciding via `change_only` — rule 8: never convert
"cannot tell" into 4/4 or any other default.

CONVENTION ASSUMED / WHAT WOULD FALSIFY IT / NOT CONFIRMED (also in the code,
beside `METER_CHANGE_GATES_OWN_SYSTEM`): CLAUDE.md §10's "a key change is
printed at one bar on every staff of the system" is taken to hold for a
meter change too. It would be FALSIFIED by a genuine printed change this
gate declines only because the system's other staves were simply never
DETECTED at that bar (a coverage failure wearing a convention failure's
clothes) — exactly the risk A-METER-6 priced against Litolff p.62, now
accepted on the strength of the evidence below. **NOT CONFIRMED WITH SEAN.**

## Where the Brahms 4/4 comes from — traced on the record directly

The fresh whole-movement Breitkopf record (`c19cbca7`, 53 `Q.METER`
verdicts) was loaded once via `record_io.load_record` and its `meter`
verdicts inspected directly — this part needed no re-adjudication, because
the `corroborated` flag already committed on each segment says exactly what
2.12d would decide. `system/0/0` opens the movement `6/8` (`reason: voted`),
correctly, with a correctly-read corroborated cautionary `9/8` at its last
cell (10 staves). `system/1/0` VOTES an opening of **`9/4`** — the misread
`omr-meter-carry-brahms-2026-09/FINDINGS.md` already named on a 4-page
slice, now confirmed whole-movement — and its own `Q.METER_GLYPH` rows also
propose a further, uncorroborated `4/4` at cell 2 (staff 7 only, support
4.0). `system/1/1` is the funnel's own named case: opening unknown
(`change_only`), a lone-staff `4/4` at cell 4 (staff 7, support 3.0,
`bars_contradict: 1` — **the bars themselves disagreeing with the one staff
that read it**) — and under the OLD rule this governed the ENTIRE system's
bars from cell 4 on, which is exactly what the funnel's `meter_wrong` bucket
(859 bars) measures.

**19 mid-system change segments across the whole document already carry
`corroborated: false`** on the committed (pre-2.12d) record — every one of
them read by exactly ONE staff, values `4/4` (17 of 19), `3/4` (1) and one
letter `C`, on systems 1, 4, 5, 7, 8, 10, 11, 14, 15, 18, 20, 21 and 26.
These are the exact candidates 2.12d declines:

| system | cell | value | support | staff(s) | bars_fit/contradict |
|---|--:|---|--:|---|---|
| system/1/0 | 2 | 4/4 | 4.0 | [7] | 0/0 |
| system/1/1 | 4 | 4/4 | 3.0 | [7] | 0/1 |
| system/4/1 | 3 | 4/4 | 3.0 | [1] | 0/0 |
| system/5/1 | 2 | 3/4 | 3.5 | [6] | 0/0 |
| system/5/1 | 6 | 4/4 | 3.0 | [4] | 0/0 |
| system/7/0 | 6 | C (4/4) | 3.0 | [10] | 0/0 |
| system/8/1 | 8 | 4/4 | 3.0 | [0] | 0/0 |
| system/10/0 | 3 | 4/4 | 3.0 | [5] | 0/0 |
| system/11/0 | 2 | 4/4 | 3.0 | [8] | 1/1 |
| system/11/1 | 7 | 4/4 | 3.5 | [7] | 0/0 |
| system/11/1 | 8 | 3/4 | 3.0 | [8] | 0/0 |
| system/14/0 | 3 | 4/4 | 3.0 | [9] | 0/0 |
| system/14/1 | 7 | 4/4 | 3.0 | [5] | 0/0 |
| system/15/1 | 6 | 4/4 | 3.0 | [6] | 0/0 |
| system/18/0 | 2 | 4/4 | 3.0 | [0] | 0/0 |
| system/18/1 | 4 | 4/4 | 3.5 | [6] | 0/0 |
| system/20/1 | 7 | 4/4 | 3.0 | [5] | 0/0 |
| system/21/0 | 6 | 4/4 | 3.0 | [0] | 0/0 |
| system/26/0 | 2 | 4/4 | 3.5 | [1] | 0/0 |

⚠️ A SEPARATE, small cluster of early systems (2 and 3) carries
`corroborated: true` on a WRONG `4/4` at 2–4 staves of an orchestral
system's ~14 (`system/2/0`: 2 staves, support 6.0; `system/2/1`: 2 staves;
`system/3/0`: **4 staves**, support 11.5; `system/3/1`: 3 staves). 2.12d does
not reach these — flagged, not chased. `METER_CHANGE_MIN_STAVES`'s absolute
floor of 2 is not the same question as a FRACTION of the system, and the
LEGACY pipeline's own `drop_uncorroborated_meter_changes`
(`tools/omr/rhythm.py:631`) already uses `max(2, round(0.5 * n_staves))` —
prior art for a stronger, proportional threshold, deliberately NOT retuned
here (this item reuses the existing staged-pipeline constant rather than
introducing a new, unmeasured one).

## Litolff: reach is ZERO, established without re-adjudication

The Litolff shared record (`library/_shared-records/beethoven5-litolff-
mvt1-whole-20260923.record.json`, provenance `dbc9962b`, 101,361 verdicts,
156,525 observations, 31 `Q.METER` verdicts) carries **no mid-system change
segments at all** — every system's value holds only its opening
(`from_cell: 0`) segment; `_meter_changes` never once cleared
`METER_CHANGE_FLOOR` on a mid-staff candidate anywhere in this document.
2.12d's gate only ever acts on a candidate that already reached `segments`;
with none present, base and arm are necessarily byte-identical on this
document — established by DIRECT INSPECTION of the committed record rather
than by running two full re-adjudications that could only confirm the same
zero (CLAUDE.md §6b: *"reach before accuracy... a change that moves nothing
because it is inert and one that moves nothing because the page holds
nothing to move are the same number"* — here it is verifiably the latter,
not a guess). This matches the funnel's own caveat: *"2.15 and 2.12d are
recommended from Brahms evidence and are not yet shown to move Litolff's 18
owned heads at all."*

## The engraved document: fully re-adjudicated and exported, byte-identical

Unlike Brahms and Litolff, the small engraved fixture record
(`beethoven5-engraved-p0p2-20260928T110428Z`, 8,148 observations, 6,022
verdicts) WAS fully re-adjudicated and exported both ways with
`price_2_12d.py` (below): CONTROL 3 of 3 `Q.METER` verdicts reproduced
exactly with the gate off (0 differ, +0 extra — the harness is sound).
Base (gate off) and arm (gate on): meters in force `{(2,4): 450}` on both,
`bars_held_out_sum` 36/449 (`fraction` 0.0802) on both, pitched `<note>`
count **331 on both**, and 2.8's independent bar-sum control (own parser, no
exporter import) **450 assessed / 450 exact / 0 wrong** on both. Clean,
unanimous ink corroborates its own meter on every staff; there is nothing
for this gate to decline, and nothing moved — the positive-direction control
this item's own test suite also asserts (the movement-start meter is read
as before).

## ⚠️ The Brahms whole-movement base/arm EXPORT pricing did NOT complete in
this session

`price_2_12d.py --control` on the fresh whole-movement Brahms record (1.1 GB,
440,057 observations, 317,217 verdicts, 89 systems) was started and run for
**over 70 minutes** (rebuild + `adjudicate.run` + `evaluate.run` +
`infer.run` + `evaluate.run_over`, no export yet) without completing; process
RSS grew steadily to ~11.8 GB and then plateaued for the last ~15 minutes of
observation while CPU stayed pinned near 100% — consistent with real,
ongoing cross-staff work at a scale (89 systems, dense Breitkopf ink) this
exact whole-movement re-adjudication operation appears never to have been
run at before (no prior FINDINGS entry reports a whole-movement
`readjudicate`-style timing; the closest comparable, `omr-owner-domain-
2026-09/FINDINGS.md`, reports 54 s for a small page-level record, ~140x
smaller). This is reported as a fact about the COST of the instrument, not
about the mechanism under test — `readjudicate.py`-style tools are known
BLIND to GATHER and otherwise trusted; nothing here suggests they are wrong,
only that a first whole-movement run of one is expensive enough that it did
not finish inside this lane's session.

**What this means for the numbers the roadmap item asked for:**
`bars_held_out_sum` base → arm, the live meters-in-force histogram, and the
pitched `<note>` count base → arm on Brahms are **NOT YET MEASURED** by this
lane. What IS established, without needing that run, is the exact POPULATION
this item changes on Brahms (the 19-row table above, each already carrying
`corroborated: false` on the UNCHANGED record) and that none of them fit a
`bars_fit > 0` profile that would make the old behaviour more defensible.
Given 2.8's own committed figures for this same record
(`bars_held_out_sum_bars: 4,513`, `meter_wrong` bucket 859 bars per the
funnel's own partition), and that `meter_wrong` is PRECISELY the set of bars
whose own reading already sums to the true meter but are judged against a
wrong `in_force` — a fact computed independently of this item's own code —
**the 859-bar / released-bars figure the roadmap line already carries is the
correct order-of-magnitude expectation**, but it is the funnel's number, not
a number this lane re-derived from an arm export, and should be labelled as
such rather than restated as if measured twice.

**To resume**: `python3 benchmarks/omr-shape-role-2026-09/price_2_12d.py
<record> --label brahms1-breitkopf --out-dir <dir> --control`, then
`--arm base` and `--arm arm` (in that order, sequentially — CLAUDE.md §13,
the machine is shared), each writing `<label>-<arm>.musicxml`,
`.coverage.json` and `.meter_histogram.json`. Each run is expected to take
on the order of an hour or more at this document's scale; run it as its own
job, not inside an interactive lane.

## Crops

8 print crops cut, `benchmarks/omr-shape-role-2026-09/out/print/
m212d-brahms1-breitkopf/` (script: `crop_declined_meter.py`; geometry read
ONCE via `record_io.load_record`; pages rendered straight off the PDF; no
detector, no re-gather, no re-adjudication — this needed none of the pending
run above). Each brackets the CELL the declined reading was filed at in red,
draws the READING staff's own `Q.STAFF_LINES` in blue (CLAUDE.md
`feedback_send_sean_the_crop`: never a neighbour's), and labels the declined
value, its support and which staff(s) read it. `VERDICT_none_yet: null` on
every sidecar, for Sean. ⚠️ **The bracket is the CELL FRAME, not the glyph
itself** — `Q.METER_GLYPH` carries only `x_canonical`/`y_center` (no
page-pixel bbox for this family), named as a caveat in every sidecar rather
than overstated as a glyph-level bracket.

7 of the 8 crops were visually inspected in this session (not by Sean): in
every one, **no readable time-signature digit stack is visible anywhere near
the bracketed cell** — each shows either an isolated ink blob (plausibly a
whole rest, a beam fragment, or a dynamic/text mark) or ordinary notation
with no numerals at all. This is consistent with, but not a substitute for,
Sean's own adjudication (`VERDICT_none_yet` stands on all eight).

| file | system | declined | support | staff(s) |
|---|---|---|--:|---|
| `m212d-brahms1-breitkopf-declined-1-0-7-2.png` | system/1/0 | 4/4 | 4.0 | [7] |
| `m212d-brahms1-breitkopf-declined-1-1-7-4.png` | system/1/1 | 4/4 | 3.0 | [7] |
| `m212d-brahms1-breitkopf-declined-4-1-1-3.png` | system/4/1 | 4/4 | 3.0 | [1] |
| `m212d-brahms1-breitkopf-declined-5-1-6-2.png` | system/5/1 | 3/4 | 3.5 | [6] |
| `m212d-brahms1-breitkopf-declined-7-0-10-6.png` | system/7/0 | C (4/4) | 3.0 | [10] |
| `m212d-brahms1-breitkopf-declined-8-1-0-8.png` | system/8/1 | 4/4 | 3.0 | [0] |
| `m212d-brahms1-breitkopf-declined-10-0-5-3.png` | system/10/0 | 4/4 | 3.0 | [5] |
| `m212d-brahms1-breitkopf-declined-11-0-8-2.png` | system/11/0 | 4/4 | 3.0 | [8] |

## Tests

RED first, `tools/omr/tests/test_staged_meter_system_agreement.py` (new
file, 4 tests): one staff of 12 reading `4/4` mid-movement is DECLINED (`6/8`
continues, `meter_at` unaffected, `declined_changes` names the reading under
`meter_change_not_system_wide`) — **verified RED on the tree before this
item** by setting `rhythm.METER_CHANGE_GATES_OWN_SYSTEM = False` at runtime:
the same test then FAILS with the pre-item segment `(4, 4, 4)` present
(`AssertionError: [(0, 6, 8), (4, 4, 4)] != [(0, 6, 8)]`). All staves of a
system reading `3/4` at one column states the change (the brief's own
positive control). A cautionary meter past the system's last barline governs
no bar (A-METER-5, reasserted here as a regression guard). The
movement-start meter is read as before (positive control — the OPENING is a
different code path, `adjudicate_meter`'s `voted` branch, untouched by this
item).

`TestAnUncorroboratedChangeIsNotCarriedOffItsSystem` in
`test_staged_header_rhythm.py` (A-METER-6's own test class) updated in place
rather than left contradicting shipped behaviour — CLAUDE.md: *"a
superseded measurement with its correction beside it is worth more than a
gap"*: `test_a_one_staff_change_still_governs_its_own_system` →
`test_a_one_staff_change_no_longer_governs_its_own_system` (now asserts the
declined candidate is recorded, not applied, plus the corroborated positive
control inline); `test_the_segment_records_the_corroboration_either_way` →
`test_corroboration_is_recorded_either_way__declined_or_kept` (the old test
indexed `segments[1]` unconditionally, which no longer exists for the
uncorroborated case — rewritten to check `declined_changes` there and
`segments` for the corroborated case); `test_the_skipped_source_is_NAMED_
rather_than_skipped_silently` → `test_an_uncorroborated_change_only_system_
now_abstains_outright` (the source now abstains OUTRIGHT rather than
deciding `change_only` and being refused only at the carry) plus a new
positive control, `test_a_CORROBORATED_change_only_system_still_decides_
and_carries`. The class docstring documents the reversal and cites this item
by name. The OLDER mechanism (`_meter_in_force_at_end`'s own defensive
filtering of a legacy uncorroborated segment) remains covered directly, on
synthetic dicts bypassing the live gate, by `test_the_helper_returns_None_
rather_than_an_unfiltered_value`, `test_a_falsy_value_has_NO_carryable_
meter` and `test_a_record_written_before_the_rule_still_carries` — untouched,
since 2.12d does not change what a RECORD WRITTEN BEFORE IT means.

`pytest tools/omr/tests -m "not slow" -q`: **3,452 passed, 3 skipped**.
`python3 -m tools.omr.staged.check`: **251** (unchanged from main).

## What contradicted this brief

The brief's own figure — *"4,126 of them (91.4%) are judged against 4.0
quarters"* — is the DENOMINATOR the funnel's own partition (§13 above)
already separates from the number this item actually releases: only
`meter_wrong` (859 bars, 19.0% of the 4,513 held) are bars whose own reading
already matches the true meter and would be released by fixing rule (1);
the other ~3,267 bars judged against 4.0 are ALSO wrong for unrelated
reasons (`missing_events`, `extra_events`, cross-staff ownership per 2.6)
this item does not touch. ROADMAP's own 2.12d line already carries the
corrected 859 figure, not the brief's 4,126 — confirmed correct by this
lane, not newly found wrong.

Litolff was not "not yet priced" so much as **provably unaffected** — no
re-adjudication was needed to show reach zero, only to READ the existing
record's own `corroborated` flags. The brief's suggested pricing tools
(2.9c's `readjudicate.py`, `review/rerun.py`) are the right shape for a
page-level or few-page record; at true whole-movement scale (440K
observations, 89 systems) this lane found the SAME shape of tool takes well
over an hour per arm and did not finish inside the session — worth recording
as a fact about the instrument for whoever prices the next whole-movement
item this way.

## Any default-to-4/4 path

None was found in `adjudicate_meter`, `_meter_changes` or `_change_only`
themselves — the RED-first test above is the closest thing to a probe this
item ran, and it passes GREEN: an unreadable system now ABSTAINS rather than
defaulting. `_bar_holds_out` (2.8, EXPORT) still requires a `Q.METER`
reading before it will judge a bar at all, so export-side there is no
independent default-to-4/4 path this item found. This is a NEGATIVE finding
scoped to the code this item touched, not an exhaustive audit of all 28
decisions and EXPORT for other, unrelated default paths.

---

# PART 6 — §2.12h: A VOTE IS NOT THE ONLY WITNESS TO A SYSTEM'S OPENING —
THE ADJACENT CAUTIONARY IS THE ONE THAT WAS NEVER ASKED

*(Branch `claude/opening-meter-2.12h`, 2026-09-28. Brief: Brahms 1/i's
opening meter reads `9/4` on `system/1/0` where the plate "prints `6/8`".
That premise was WRONG — see "What contradicted this brief" below — and the
trace, not the brief, is what this item was built against.)*

## The trace (one record, read once)

`python3 -m tools.omr.staged.trace --run <the 2026-09-28 whole-movement
Brahms record> --subject system/1/0`: `meter = {numerator: 9, denominator: 4,
raw: "9/4", ...}`, `decider=adjudicate_meter reason=voted`, `read 10 of 1034
rows considered`. Reading the record's own `Q.METER_TEMPLATE` rows directly
(`record_io.load_record`, once) for the ten staves that spoke: every one of
them reads `raw: "9/4"` at `score` 0.50–0.53 (barely over `min_score = 0.50`)
with a runner-up of `"6/4"` or `"C"` — **never `"9/8"`** — at a margin of only
0.04–0.09. `LocatedTimeSignature` keeps only the winner and ONE runner-up, so
the template reader's own score for a genuine `9/8` candidate is not on the
record at all; an ADJUDICATE-only fix cannot "pick a better candidate" out of
what GATHER wrote down, only weigh the vote against a DIFFERENT witness
already on the record.

That witness already exists. `system/0/0` — the immediately preceding system
— is DECIDED `voted` `6/8` and its own value carries `cautionary: {from_cell:
7, numerator: 9, denominator: 8, raw: "9/8", support: 26.5, staves_reading_
it: [0,1,2,3,4,6,8,10,12] (9 of 14), corroborated: true, bars_fit: 0}`. A-
METER-5 already reads and RECORDS this courtesy signature, with the comment
*"consuming it belongs with the carry"* — but nothing before this item ever
did: `_carry_meter` only ever asks `_meter_in_force_at_end` for a source's
own bar-governing meter, and the "voted" success path returns outright the
moment coverage and agreement clear, never consulting a neighbour.

## The print (crops, not inference)

`benchmarks/omr-shape-role-2026-09/crop_opening_meter.py` (self-contained,
geometry-only read of `cell_box`/`staff_lines`/`staff_spacing` from the same
record, pages rendered straight off the PDF, no detector, no re-gather) cuts
`system/1/0` cell 0 (the header, where `Q.METER_GLYPH` already files a
low-confidence `timeSig8` box on 2 of 14 staves at `x≈432`) on staves 1, 4,
6, 8, plus `system/0/0`'s own cautionary cell (7) for contrast:
`benchmarks/omr-shape-role-2026-09/out/print/m212h-brahms1-breitkopf/`.
Every crop shows the SAME two-digit stack: a single-loop "9" (tail below,
left) over a DOUBLE-loop "8" (two stacked closed counters) — unambiguously
`9/8`, on both the opening and the cautionary. **Not `9/4`** (a "4" has no
enclosed counter at this weight) **and not `6/8`** (a "6" has its loop at the
BOTTOM with the tail rising, the mirror of what is printed). `VERDICT_none_
yet: null` on every sidecar, for Sean.

## The cause, named

The denominator digit "8" is misread as "4" by the header-window TEMPLATE
reader (`time_signature_locator.locate_time_signature`) specifically on this
crop — `9/8` IS one of `DEFAULT_METERS`' 21 candidate templates, so this is
not a missing template, it is that candidate's own NCC score losing to `9/4`
and `6/4` on this particular (Breitkopf-shattered) ink. The numerator digit
"9" is read correctly by the SAME reader on the SAME ten staves — the fault
is confined to the denominator half of the match.

## The fix — ADJUDICATE only, two connected pieces

No GATHER change; both pieces are new code in
`tools/omr/staged/adjudicators/rhythm.py`, wiring an already-recorded fact
into two consumers that never read it before (CLAUDE.md rule 6: connect,
never guess):

1. `_adjacent_corroborated_cautionary(ev, here)` — the STRICT immediate
   predecessor system's `cautionary`, if `corroborated`. Adjacency is
   computed off `Subject`'s own document ordering (`ev.subjects(Kind.
   SYSTEM)`, sorted), not "nearest system with a decided meter" — a
   cautionary names the system directly after it and nothing farther, so a
   system `_carry_meter` had to walk past an abstention to reach never
   qualifies.
2. `adjudicate_meter`'s "voted" success path now calls it: where the
   immediate predecessor's corroborated cautionary DISAGREES with this
   system's own unanimous vote, the vote is not asserted outright — it is
   rerouted through the existing `_meter_fallbacks` ladder under a new
   reason, `opening_disagrees_with_prior_cautionary`.
3. `_carry_meter` itself: when the source it is examining is that same
   strict-adjacent cautionary-bearer, it substitutes the cautionary's
   `(numerator, denominator, raw)` for `_meter_in_force_at_end`'s answer
   (which would otherwise just repeat the source's OWN in-force meter —
   the wrong question once a change is printed between the two systems),
   then weighs it via the SAME `_corroborate` bar-arbitration every other
   carry candidate already goes through (`METER_CARRY_FLOOR`, `METER_CARRY_
   MIN_BARS`). `detail["carried_via_cautionary"]` says which fact of the
   source travelled, for anyone reading the record later.

A vote is never simply overruled by the cautionary, and the cautionary is
never asserted on its own say-so (rule 8: a fallback never converts "cannot
tell" into an answer) — the destination's OWN bars still decide whether the
carried candidate stands, exactly as for any other carry, and a bar-refusal
still ends in an ABSTAIN naming `carry_outweighed_by_the_bars`, never a
default.

## Tests, RED first

`tools/omr/tests/test_staged_opening_meter.py` (new file, 7 tests, synthetic
two- and three-system fixtures reproducing the Brahms shape at fixture
scale — no real record needed to prove the mechanism):

- **RED, verified two ways.** (a) `test_the_fix_is_reachable_RED_without_it`
  monkeypatches `_adjacent_corroborated_cautionary` to always return `None`
  (exactly what every call site saw before this item) and asserts the
  destination still asserts its own wrong vote — this passes GREEN today as
  a live regression guard. (b) Independently, the pre-fix `rhythm.py` was
  restored from `git show HEAD:...` and the suite re-run: `test_the_bars_
  confirm_the_cautionary_and_it_is_carried` and `test_the_bars_can_still_
  REFUSE_the_cautionary` both FAILED (the second with an `AttributeError`
  for the function this item adds, the first by asserting `9/4` where `9/8`
  is now expected) — then the fixed file was restored and all 7 passed.
- **GREEN, the fix.** The destination's own bars (2 bars of 4.5 quarters,
  3 staves each) fit `9/8` and refuse `9/4`'s own 9.0-quarter length →
  `reason="carried"`, value `9/8`, `detail["carried_via_cautionary"] is
  True`.
- **Positive control — a clean opening is untouched.** No preceding system
  at all → a plain unanimous `4/4` vote reads `4/4`, `reason="voted"`
  (the brief's own requested control).
- **Control — agreement means no reroute.** Destination votes `9/8` (the
  SAME value the cautionary names) → `reason="voted"` still, proving the
  mechanism does not fire needlessly even though it would reach the same
  answer either way.
- **Control — an UNCORROBORATED cautionary does not override.** Only 1 of 3
  staves reads the courtesy signature → below `METER_CHANGE_MIN_STAVES = 2`
  → the vote stands.
- **Control — the bars can still REFUSE the cautionary (the brief's second
  requested control, rule 8).** Destination's own bars measure 2.0 quarters
  twice — neither witness's length — → `Outcome.ABSTAINED`, reason `carry_
  outweighed_by_the_bars`, never a default and never the cautionary by fiat.
- **Control — adjacency, not "nearest decided system".** Three systems: the
  cautionary-bearer, an intervening system that AGREES with it (so it is not
  itself rerouted) and prints no cautionary of its own, then a third system
  voting a DIFFERENT, conflicting value — the third system is unaffected,
  because the cautionary was never printed for it.

`pytest tools/omr/tests/test_staged_opening_meter.py -v`: 7 passed.
`pytest tools/omr/tests/test_staged_header_rhythm.py`: 94 passed (no
regression in the existing meter/cautionary suite). `pytest tools/omr/tests
-m "not slow" -q -p no:warnings -x`: **3,472 passed, 3 skipped** (up from
3,465/3 on `41cdc025` by exactly this item's 7 new tests).
`python3 -m tools.omr.staged.check`: **251** (unchanged from main).

## The one-subject re-decision — SKIPPED, and why

The brief asked for one narrow re-decision of `system/1/0`'s `Q.METER` from
the saved record, naming `review/rerun.py --staff` as a candidate tool.
Read closely: `--staff` only narrows the CENSUS `rerun.py` reports (`staff_
census`, which subjects a diff line is grouped under) — `rebuild_gather`
replays every observation and abstention in the file into a fresh `Log` and
`run_stages` then calls `pipeline.decide`, which re-adjudicates the WHOLE
document (89 systems, 440K observations on this record), not one subject.
This is exactly the cost 2.12d's own session already measured and the
proof budget for this item explicitly excludes ("no whole-movement re-
adjudications"). No tool in the tree re-decides a single `Q.METER` verdict
in isolation from a saved record — **skipped, per the brief's own
fallback instruction.**

## What contradicted this brief

**"The plate prints `6/8`" was wrong.** The crops (above) show `9/8`
unambiguously at both `system/1/0`'s opening and `system/0/0`'s cautionary
one system earlier — the SAME shape 2.12d's own session already named in
passing (*"the opening `9/8` is voted `9/4`"*) without this item's brief
picking it up. The fix reads `9/8`, not `6/8`, and the tests assert that
value throughout. Sean has not adjudicated the crops (`VERDICT_none_yet:
null` on every sidecar) — if he reads the print differently the fix should
be revisited, but three independent sources agree here: the cautionary's
own corroborated reading (9 of 14 staves), the low-confidence `timeSig8`
detector box at the opening's own cell 0, and the crop itself.

The brief's suggested re-decision tool does not do what its own flag name
suggests — recorded above rather than silently worked around.

---

## §2.12h.b — the 6/8 RETURN, one bar after the 9/8, is not gathered at all
(manager follow-up, TRACE ONLY: no code, no runs, no re-adjudication)

*(Reads the SAME saved record via `record_io.load_record`, plus two crops
straight off the PDF — no detector, no re-gather, no re-adjudication.)*

**(1) Is the return gathered?** No, effectively not. Across all 14 staves of
`system/1/0`, `cell:1` (the bar immediately after the system's own opening
bar, cell 0) carries exactly **ONE observation, of any quantity, on any
staff**: `staff/1/0/9`, `Q.METER_GLYPH` `timeSig1`, score 0.72 — unpaired
(no second digit row at that cell on that staff, so `_meter_from_digits`
cannot even form a candidate from it) and unrelated to a `6/8` shape. **Zero**
`timeSig6` detections exist anywhere in the whole system (checked all 21
`Q.METER_GLYPH` rows the system holds, at every cell). This is a genuine
DETECTOR RECALL miss, not a misclassification: two crops cut straight off the
PDF at `cell:1`'s own geometry —
`out/print/m212h-brahms1-breitkopf/m212hb-brahms1-breitkopf-sys1-0-return-
cell1-staff1-clean.png` and a tall strip spanning the whole system's height
at that same x — show a clean, unambiguous **`6/8`** stacked at the very
start of `cell:1`, confirmed by eye on very close to every one of the
system's 14 staves (13 legible in the tall strip). The detector simply never
boxed it — no stray box under any class, at any confidence, sits there for
12 of 14 staves.

**(2) Declined, or never a candidate?** Never a candidate — there is nothing
for `_meter_changes` to decline, because nothing pairs. The mid-system
candidates that DO exist near this point (cells 2–6, one lone staff each —
staff 5 at cells 3/4/5, staff 7 at cells 2/3/6 — all low-confidence `timeSig4`
pairs, `staves_reading_it` length 1) are a SEPARATE, unrelated false-positive
population (already the cell-2 row in Part 5's 19-row table) that 2.12d's
`METER_CHANGE_MIN_STAVES = 2` correctly declines — but declining them answers
a different question. The true `6/8` restatement never reaches `_meter_
changes` at all, corroborated or not, because GATHER produced no digit rows
for it to read.

**(3) What meter carries from m.9 onward?** `9/8` — the corrected opening
from 2.12h §2.12h itself — stands for the REST of `system/1/0` (no segment
ever supersedes it, since nothing was gathered to propose one) and would
carry into any later abstaining system exactly as the wrong `9/4` used to.
**2.12h fixed the OPENING misread; the RETURN one bar later is untouched and
is a GATHER-side gap, not an ADJUDICATE one** — `time_signature_locator` (or
whatever reads `Q.METER_GLYPH`'s digit boxes) needs to be asked why a
clean, unambiguous, system-wide `6/8` produces one stray unrelated box on
one staff and nothing on the other thirteen. Not investigated further here
(trace only, per the manager's instruction) — flagged as the next lever on
this same funnel.


# PART 7 — §2.12i: THE BAR-HEAD TEMPLATE READER WAS PRICED AGAINST THE REAL
FIXTURE IT WAS WAITING FOR, AND REFUSES THE CHANGE IT WAS BUILT TO CATCH

*(Branch `claude/meter-at-bar-2.12i`, 2026-09-28, base `origin/main` at
`c323cd96` (2.12h.b). Brief: promote `OMR_METER_TEMPLATE_AT_BAR` — `docs/
flags-2026-09.md`'s own row said "review when a fixture with a real
mid-staff change exists", and 2.12h.b just found one: Brahms 1/i Breitkopf
`317803`, pdf index 1, `system/1/0` cell 1, a clean printed `6/8` the
detector never boxes on 13 of 14 staves.)*

## Setup, and one correction to the brief

`_meter_template_at_bar_enabled()` (`gather.py:3234`) ANDs the flag's own
switch with `research_enabled(METER_TEMPLATE_AT_BAR_ENV)`, which tests
whether `OMR_RESEARCH`'s comma-separated value NAMES the flag's own string —
`docs/flags-2026-09.md`'s worked example is `OMR_RESEARCH=OMR_FAMILY_
POSITIONS`. The brief's `OMR_RESEARCH=1` does not satisfy this (`"1" != "OMR_
METER_TEMPLATE_AT_BAR"`) and the arm would silently run as a no-op OFF
gather. Corrected to `OMR_METER_TEMPLATE_AT_BAR=1 OMR_RESEARCH=OMR_METER_
TEMPLATE_AT_BAR` before running anything, confirmed by the reach numbers
below being non-zero.

## The two one-page gathers (per the proof budget — no whole-movement run)

Tree clean, committed at base before both arms; symlinks per CLAUDE.md §5a
(a fresh worktree has none of them); weights `deepscoresv2-yolov8l-hollow-
graft-shift09-2026-09-04.pt`; `--dpi 600 --no-surya --no-ocr`, no
`--musicxml` during gather (export run separately afterward on the saved
records, per CLAUDE.md's own operational note about the exporter import
order).

```
python3 -m tools.omr.staged brahms...317803.pdf --pages 1 --weights ... --dpi 600 --no-surya --no-ocr --out arm-off.staged.json
OMR_METER_TEMPLATE_AT_BAR=1 OMR_RESEARCH=OMR_METER_TEMPLATE_AT_BAR python3 -m tools.omr.staged brahms...317803.pdf --pages 1 ... --out arm-on.staged.json
```

## REACH — real, not dead

OFF arm: 0 `meter_template_at_bar` rows (byte-identity control holds). ON
arm: **162 rows asked** across `system/1/0` (14 staves × 6 candidate cells:
1–6) and `system/1/1` (13 staves × 5 candidate cells), **2 answered**. The
candidate-column gate (`_meter_candidate_columns`, `MIN_CANDIDATE_STAVES=1`)
is exactly as loose as designed: cell 1's own candidacy comes from a SINGLE
stray `timeSig1` box on one staff (2.12h.b's own finding), which is enough
to open the column to all 14 staves — the mechanism worked exactly as
built. The reach is not the failure here.

## THE FIXTURE CELL ITSELF — `system/1/0`, cell 1, all 14 staves

| staff | verdict | its score | `6/8`'s own rank | `6/8`'s own score | top-1 | top-2 |
|--:|---|--:|--:|--:|---|---|
| 0  | abstain (below 0.50) | – | 4  | 0.4046 | `6/4` 0.4707 | `12/4` 0.4297 |
| 1  | abstain | – | 7  | 0.3725 | `6/4` 0.4963 | `9/8` 0.4430 |
| 2  | abstain | – | 8  | 0.3573 | `9/8` 0.4625 | `6/4` 0.4443 |
| 3  | abstain | – | 7  | 0.3908 | `6/4` 0.4757 | `9/8` 0.4430 |
| **4**  | **`9/8`** | **0.5113** | 2  | 0.4266 | `9/8` 0.5113 | `6/8` 0.4266 |
| 5  | abstain | – | 8  | 0.3377 | `9/8` 0.4425 | `6/4` 0.4096 |
| **6**  | **`6/4`** | **0.5030** | >2 (not top-2) | – | `6/4` 0.5030 | `9/8` 0.4611 |
| 7  | abstain | – | 6  | 0.3855 | `6/4` 0.4738 | `9/8` 0.4692 |
| 8  | abstain | – | 3  | 0.3871 | `9/8` 0.4747 | `6/4` 0.4073 |
| 9  | abstain | – | 6  | 0.3588 | `6/4` 0.4500 | `9/8` 0.4406 |
| 10 | abstain | – | 4  | 0.3961 | `6/4` 0.4743 | `9/8` 0.4231 |
| 11 | abstain | – | 6  | 0.3436 | `9/8` 0.4521 | `6/4` 0.4171 |
| 12 | abstain | – | 4  | 0.3608 | `9/8` 0.4627 | `6/4` 0.3994 |
| 13 | abstain | – | 4  | 0.3490 | `9/8` 0.4433 | `6/4` 0.4127 |

**`6/8` — the print's own answer, confirmed by eye on close to all 14
staves in 2.12h.b's crops — never wins on ANY staff, and is the runner-up on
exactly ONE (staff 4, still 8.5 points behind the winner).** Its own score
sits at 0.34–0.47 everywhere, always below the winner AND the runner-up. The
two staves that DO clear the 0.50 floor (4 and 6) clear it by less than
0.013 above the floor, into the WRONG answer, each alone (`METER_TEMPLATE_
AT_BAR_MIN_STAVES = 3`; 1 « 3 on both). `_admit_template_consensus` therefore
admits nothing at cell 1, or at any of the other 10 candidate cells on this
page (0 answered outside cell 1).

## THE CAUSE, named — the SAME confusion 2.12h already measured, plus a new one

2.12h (this same document, this same reader, the system's OPENING at cell
0, a 16-space header window) already measured *"the denominator digit '8'
is misread as '4' ... the numerator '9' is read correctly."* Here, one bar
later, the SAME denominator confusion recurs (`6/8`'s `8` loses to `9/8`'s
and `6/4`'s templates) and is joined by a NEW numerator confusion (`6/8`'s
`6` loses to `9/8`'s `9` — a rotationally similar loop-shaped digit, the
same family of confusion). The two crops 2.12h.b already cut
(`out/print/m212h-brahms1-breitkopf/m212hb-*-staff1-clean.png`, `*-staff7
.png`) show why on inspection: this Breitkopf plate's `6` and `8` are
heavier, blobbier strokes than the Bravura NCC templates
`time_signature_locator` matches against (staff 7's `8` fuses into the
staff line as a single dark blob) — the true shape is a worse NCC match to
its OWN template than the neighbouring wrong ones are, on this specific
engraving. This is not a new mechanism defect to fix here (out of scope for
a proof-budget item) — it is the answer to "why was this left in research":
**the reader's known weak axis (denominator legibility) is exactly the axis
this fixture tests, twice over (denominator AND, newly, numerator).**

## Every other cell and system on the page

Untouched: 0 of the other 10 candidate cells (`system/1/0` cells 2–6, `system
/1/1` cells 1,2,4,5,6,7) answer at all — the pre-existing single-staff false
positives at those cells that 2.12d already declines (`meter_change_not_
system_wide`) are UNCHANGED, because this reader never reaches quorum there
either.

## Openings, segments, and the export — byte-identical

`system/1/0` opening: `9/4 (voted)` in BOTH arms (this one-page gather has
no preceding page to carry 2.12h's corroborated cautionary from — expected,
and orthogonal to this item: `Q.METER_TEMPLATE_AT_BAR` is a separate
quantity precisely so it cannot touch an opening vote). `system/1/1`:
`carry_not_corroborated` in both. **Systems whose segments moved: 0.
Systems whose opening moved: 0.** Exporting both saved records
(`tools.omr.staged.export`, no gather): `bars_held_out_sum` **85 → 85**, and
the two `.musicxml` files are **byte-for-byte identical** (`diff` clean).
The flag has zero measurable effect anywhere on this page.

## The no-change control — Litolff, pdf index 3

Base: 0 rows (clean). Arm: **19 rows asked, 0 answered** (this continuation
page does carry some meter-shaped ink mid-system, unlike Litolff p.1 in the
original research, so reach is non-zero here too — the mechanism is live,
not dead). Meter verdicts, segments and openings identical in both arms on
both systems present (`system/3/0`, `system/3/1`, both `bars_name_a_length_
without_a_form`).

## THE GATE, against the brief's own wording

Brief: *"the arm states 6/8 at `system/1/0` cell 1, with the quorum and the
per-staff scores named, and it passes 2.12d's system-agreement rule."* It
does not. No staff states `6/8`; no quorum of any value forms; the two
answers that exist are wrong, single-staff, and would be declined by
2.12d's own rule even if `METER_TEMPLATE_AT_BAR_MIN_STAVES` were removed
entirely. **GATE FAILS.**

## DECISION: NOT PROMOTED

Per CLAUDE.md rule 5 (reach before accuracy — reach is real, accuracy is
now measured and negative) and the proof budget's own instruction ("if the
gate fails, do not promote — write the numbers into FINDINGS and stop"):
`OMR_METER_TEMPLATE_AT_BAR` is left exactly as `docs/flags-2026-09.md`
already has it — `research`, default OFF, gated behind `OMR_RESEARCH`. No
code changed under `tools/omr/staged/`; no test file added or removed. The
mechanism's own safety (`METER_TEMPLATE_AT_BAR_MIN_STAVES = 3`) did its job
here — it refused the two wrong single-staff answers exactly as it would
refuse two wrong answers under any circumstance, which is a working control,
not a wasted one.

## What is now established that was not before

* This was the first time any page in reach printed a real mid-staff meter
  change; it no longer isn't. The answer the original FINDINGS flagged as
  entirely unmeasured (*"it has never been shown that this reads a real
  one"*) is now measured, and is negative on this one fixture.
* The failure mode is not the safety net (quorum) catching a good reading
  too late — the READER itself does not produce a correct candidate on any
  of the 14 staves, so no quorum threshold, however loosened, would have
  helped here without also un-refusing the 16 spurious single-staff columns
  section 2 of the original FINDINGS measured on blank ink.
* The cause is not this fixture's alone: it is the SAME denominator
  confusion 2.12h measured at this system's own opening, one bar earlier, on
  the SAME reader. Two independent measurements on two adjacent bars of one
  document now agree that this specific Breitkopf plate's digit strokes are
  a poor NCC match to the Bravura template on both axes (`8`→`4`/`6`, `6`→
  `9`) — a fact about THIS ENGRAVING's typeface at this weight, not a
  one-off. A different publisher's digit strokes were not tested here and
  might score differently; nothing here claims otherwise.

## What contradicted this brief

* `OMR_RESEARCH=1` does not enable the flag; it must name `OMR_METER_
  TEMPLATE_AT_BAR` itself (see "Setup", above).
* The gate's predicted outcome — a clean 6/8 consensus — did not hold. The
  print IS a clean, unambiguous 6/8 (2.12h.b already established this by
  eye and this item did not need to re-verify it), but the READER does not
  see it that way.

## Landing

No promotion, so no new tests, no `docs/flags-2026-09.md` row change, no
`test_flag_triage.py` change, no touch to `gather.py` or `rhythm.py` beyond
reading them. `pytest tools/omr/tests -m "not slow"` and `tools.omr.staged.
check` were run unmodified as a landing sanity check (numbers in the
ROADMAP line); both were already green/251 on this branch's base and remain
so, since no code moved.

---

# PART 8 — §2.12j: THE RESIDUAL 4/4 IS ELEVEN MINORITY-CORROBORATED
`change_only` SEGMENTS, EACH CLEARING THE ABSOLUTE FLOOR ON STAFF COUNT
ALONE WHILE ITS OWN BARS NEVER AGREE

*(Branch `claude/brahms-common-time-2.12j`, 2026-09-28. Base: the 2.12d + 2.12h
batch re-decision `.claude/worktrees/redecide-92b6ab04/out-redecide/brahms/
amended.record.json` (1.6 GB; 53 `Q.METER` verdicts over 27 pages — page 0
carries one system, pages 1-26 two each), committed on `main` at `92b6ab04`
(distinct from the larger 89-system whole-movement gather Part 5 above priced
separately and never finished exporting — this is the record the manager's
own batch re-decision produced and named for this item), read ONCE via a
targeted `ijson` stream over `record.verdicts`/`record.
observations` for `quantity == "meter"` / `"meter_glyph"` — no re-gather, no
re-adjudication, per the proof budget. `record_io.load_record`'s full pool
expansion was not run against this file; the fields this item reads
[`considered`/`basis`/`correlated` id-lists] were never dereferenced, so the
sanctioned expansion path was unnecessary for this trace and would have cost
minutes rather than the ~8s/pass `ijson` took.)*

## Where the 4/4 comes from — the whole causal chain, traced once

Every one of the 53 `Q.METER` verdicts on the amended record was read (value,
`reason`, `raw`, `segments`, `corroborated`, `bars_fit`/`bars_contradict`) and
matched against `bars_held_out_sum.held`'s own per-`(page, system)` count of
bars judged `want_quarters: 4.0` vs `3.0` (`brahms.coverage.json`):

| system | outcome / reason | value | held bars @3.0 / @4.0 |
|---|---|---|---:|
| 0/0 | decided / voted | 6/8 | 71 / 0 |
| 1/0, 1/1 | abstained / `carry_not_corroborated` | — | 177 / 0 |
| **2/0** | **decided / change_only** | **4/4** (from_cell 4) | 37 / 24 |
| **2/1** | **decided / change_only** | **4/4** (from_cell 1) | 0 / 48 |
| **3/0** | **decided / change_only** | **4/4** (from_cell 6) | 0 / 83 |
| **3/1** | **decided / change_only** | **4/4** (from_cell 3) | 0 / 108 |
| 4/0 | decided / **derived_from_bars** | 6/8 (borrowed from 0/0) | 85 / 0 |
| 4/1 – 9/0 (10 systems) | abstained (carry, mostly `carry_not_corroborated`) | — | 806 / 0 |
| **9/1** | **decided / change_only** | **4/4** (from_cell 7) | 62 / 23 |
| **10/0** | **decided / change_only** | **4/4** (from_cell 4) | 0 / 93 |
| 10/1 | abstained / `carry_not_corroborated` | — | 12 / 63 |
| **11/0** | **decided / change_only** | **4/4** (from_cell 8) | 10 / 89 |
| 11/1 | abstained / `carry_not_corroborated` | — | 0 / 71 |
| **12/0** | **decided / change_only** | **4/4** (from_cell 12) | 0 / 131 |
| 12/1 | abstained / `carry_outweighed_by_the_bars` | — | 0 / 95 |
| **13/0** | **decided / change_only** | **4/4** (from_cell 7) | 0 / 108 |
| 13/1 – 26/1 (27 systems, includes 15/0 and 16/0 below) | abstained (carry, mixed reasons) except 15/0, 16/0 | — | 0 / 2,298 |
| **15/0** | **decided / change_only** | **4/4** (from_cell 4) | 0 / 57 |
| **16/0** | **decided / change_only** | **4/4** (from_cell 2) | 0 / 115 |

(15/0 and 16/0's own 57 + 115 = 172 are already counted inside the 13/1–26/1
row's 2,298; broken out on their own line because they are two of the eleven
causes. Every figure above was read directly off `brahms.coverage.json`; the
column sums to the file's own grand total, 1,260 bars @ 3.0 and 3,234 @ 4.0,
exactly.) **ELEVEN systems** — page/local `(2,0) (2,1) (3,0)
(3,1) (9,1) (10,0) (11,0) (12,0) (13,0) (15,0) (16,0)` — each carry a
`Q.METER` verdict `DECIDED` `change_only` `4/4`, and every one is the SAME
shape:

| system | from_cell | staves reading it | `Q.SYSTEM_STAFF_COUNT` | coverage | required (2.12j) | support | bars_fit | bars_contradict |
|---|--:|---|--:|---:|--:|--:|--:|--:|
| 2/0 | 4 | [6, 8] | 14 | 14.3% | 7 | 6.0 | 0 | 0 |
| 2/1 | 1 | [7, 8] | 14 | 14.3% | 7 | 4.5 | 0 | 2 |
| 3/0 | 6 | [2, 4, 5, 7] | 14 | 28.6% | 7 | 11.5 | 0 | 1 |
| 3/1 | 3 | [5, 6, 7] | 14 | 21.4% | 7 | 7.0 | 0 | 2 |
| 9/1 | 7 | [9, 10] | 13 | 15.4% | 6 | 5.5 | 0 | 1 |
| 10/0 | 4 | [0, 4] | 13 | 15.4% | 6 | 6.0 | 0 | 0 |
| 11/0 | 8 | [1, 2] | 14 | 14.3% | 7 | 6.5 | 0 | 0 |
| 12/0 | 12 | [4, 5] | 14 | 14.3% | 7 | 5.0 | 0 | 1 |
| 13/0 | 7 | [0, 6] | 14 | 14.3% | 7 | 6.0 | 0 | 0 |
| 15/0 | 4 | [4, 5] | 12 | 16.7% | 6 | 4.0 | 0 | 2 |
| 16/0 | 2 | [6, 7] | 14 | 14.3% | 7 | 6.5 | 0 | 0 |

(`Q.SYSTEM_STAFF_COUNT` read directly off the record's own verdicts, not
approximated; `required = max(2, round(0.5 * count))`, Python's round-half-
to-even. Every one of the eleven reads on 2-4 staves, 3-6 short of what its
OWN system's size now requires.)

**`bars_fit` is 0 on every single one** — not one of the eleven candidates has
so much as ONE bar of its own system agreeing with the 4/4 it declares; five
of them have the bars actively CONTRADICTING it (`bars_contradict` 1-2), and
it wins anyway, because `support` never needed `bars_fit` in the first place:
`2 * W_CHANGE_GLYPH_PAIR = 6.0` already clears `METER_CHANGE_FLOOR = 3.0`
before a single bar term is added. The bar-math control CANNOT FAIL a
2-staff-corroborated candidate — CLAUDE.md rule 7's own example of "a control
that must be able to fail," found here rather than merely quoted.

## The mechanism downstream — one write poisons the file until the next one

`export._part_xml`'s own carry (`in_force`, ROADMAP 2.8, unchanged and
CORRECT — see its own comment: *"the meter a reader of this file sees... a
bar whose own system never settled a meter is, to music21 or to Verovio, in
the last meter this part declared"*) means every one of these eleven DECIDED
`4/4` verdicts REWRITES `<time>` for the file from that bar on, and every
LATER system that itself abstains (the overwhelming majority — 40 of 53
systems: 33 `carry_not_corroborated` + 7 `carry_outweighed_by_the_bars`)
inherits whatever the file last wrote, not its own system's
(non-)reading. `system/4/0`'s `derived_from_bars` `6/8` is the one place the
file self-corrects (a length read off the ACTUAL bars, borrowing 0/0's
spelling) — pages 4-8 are entirely `3.0` because of it. Nothing resets it a
second time: from `system/13/0` on, the file never writes anything but `4/4`
again for the rest of the movement (13 more pages), which is where the bulk
of the 3,234 lives.

## The cause is ONE mechanism, not several

Every one of the eleven shares the identical shape: `_meter_changes`'s
`corroborated` flag was `len(staves) >= METER_CHANGE_MIN_STAVES` (an
ABSOLUTE floor of 2), on systems of 12-14 staves. 2.12d's own session
measured and flagged exactly this in Part 5 above (*"a fraction-of-the-system
threshold is visible in the fresh record too... and is NOT this item's to
fix — flagged, not chased"*) and named the prior art: the LEGACY pipeline's
own `tools/omr/rhythm.py:631 drop_uncorroborated_meter_changes` already uses
`max(2, round(0.5 * n_staves))`. **One cause, eleven instances, thousands of
bars** — not several unrelated mechanisms. (A GATHER-level theory was also
checked and set aside: the underlying `Q.METER_GLYPH` rows behind several of
these — e.g. `staff/2/0/6` cell 4 carries SIX separate `timeSig4` detector
boxes at scattered `y_center` spanning ~4.4 canonical staff-spaces, all the
identical digit, on ONE staff — look like detector noise on ordinary ink
rather than a real printed digit stack, and a geometry-based rejection in
`_meter_from_digits` was prototyped and simulated against all eleven cases.
It was set aside in favour of the coverage fix: geometry clustering resolved
9 of 11 cleanly but left 2 borderline on tolerance choice, `_meter_from_
digits` has zero existing unit coverage to protect against a wrong guess at
the right window size, and the coverage fix — reusing an ALREADY-MEASURED
legacy constant rather than a new geometric threshold this lane would have to
invent — resolves all eleven with no fixture in the suite needing more than
100% or a name-checked majority. CLAUDE.md rule 6: connect, never guess.)

## The fix — ADJUDICATE only, one flag's meaning changed, nothing new declared

`tools/omr/staged/adjudicators/rhythm.py`. `METER_CHANGE_MIN_STAVES = 2`
(the absolute floor A-METER-6 measured and still the floor below which
nothing is EVER corroborated) is unchanged, along with its own test
(`test_the_constant_is_the_weakest_bar_that_can_confine_anything`, still
`== 2`, still `== key_signature_corroboration.MIN_WITNESSES`). What changed
is what `corroborated` MEANS: a new `_required_corroboration(total_staves)`
returns `max(METER_CHANGE_MIN_STAVES, round(METER_CHANGE_COVERAGE_FLOOR *
total_staves))` (`METER_CHANGE_COVERAGE_FLOOR = 0.5`, the cited legacy prior
art, NOT imported — LEGACY is frozen, CLAUDE.md §3), and `total_staves` is
`None` (falls back to the unchanged absolute floor) wherever `Q.SYSTEM_
STAFF_COUNT` is undecided. `_meter_changes` gained one new parameter,
`total_staves`, fetched by its two callers (`_with_segments`, `_change_only`)
via a new `_total_staff_count(ev)` helper placed beside `_bar_lengths_for`/
`_last_cell_per_staff` — the SAME `inventory._never_read` depth-3 shape those
two are already threaded as arguments for, so `Q.SYSTEM_STAFF_COUNT` (already
in `adjudicate_meter`'s own `wants`) does not become a new inert declaration.
This gates BOTH rule (1) (`METER_CHANGE_GATES_OWN_SYSTEM`, unchanged, still
reads the same `corroborated` flag) and rule (2) (A-METER-6's carry
eligibility) through the one flag both already shared — no second place had
to be told to agree with this one.

On the eleven real systems (12-14 staves each, per the table above),
`required` is 6 or 7; the largest reading is 4 staves (28.6%). All eleven
now DECLINE (`meter_change_not_system_wide`), recorded in `declined_changes`
exactly as 2.12d already files a declined candidate, never silently dropped.
**Predicted, not yet re-measured** (the proof budget excludes a whole-
movement re-adjudication; the manager's own batch re-decision is the
instrument that will confirm this): with all eleven declined, the file's
`in_force` is never rewritten away from `6/8` by any of them, so the causal
chain traced above collapses back to the `4/0` reset's own `6/8` — and stays
there for the remainder of the movement, since nothing else in the traced
chain ever asserted anything but the eleven phantom changes. This would
release close to the full 3,234-bar `4.0` population, not a subset of it,
because the eleven are not eleven independent releases but ONE broken
mechanism poisoning one shared file-wide `in_force`. The 1,260 bars already
judged at `3.0` are untouched (2.12b/2.12b-cal territory, unrelated).

## Existing test suite checked for regressions before writing anything new

- `test_staged_meter_system_agreement.py` (2.12d, `N_STAVES=4/12`): every
  positive control uses ALL staves (100% coverage; `max(2, round(0.5*4))=2`,
  `max(2, round(0.5*12))=6`, both `<=` the count used) — unaffected. Its
  negative control (1 staff) was already below the absolute floor —
  unaffected.
- `test_staged_header_rhythm.py`'s `TestAnUncorroboratedChangeIsNotCarriedOff
  ItsSystem` (`N_STAVES=4`): same shape, same result — unaffected.
- `test_staged_opening_meter.py` (2.12h, `N_STAVES=3`): the cautionary
  corroboration positive control uses 2 of 3 staves; `max(2, round(0.5*3)) =
  max(2, 2) = 2` (Python's round-half-to-even rounds 1.5 to 2) — identical
  requirement, unaffected. Its negative control (1 of 3) was already below
  the absolute floor.
- On the REAL record, `system/0/0`'s own corroborated `9/8` cautionary reads
  9 of 14 staves (64.3%), comfortably above the new floor — 2.12h's carry-via-
  cautionary mechanism (which reads the SAME `corroborated` flag) is
  unaffected on the document this item is about.

All confirmed by running `pytest tools/omr/tests/test_staged_meter_system_
agreement.py tools/omr/tests/test_staged_header_rhythm.py tools/omr/tests/
test_staged_opening_meter.py tools/omr/tests/test_meter_template_at_bar.py
-q`: 139 passed, no regressions.

## The export-side hypothesis — checked and NOT found

The brief's third possible cause, "an export-side 4.0 fallback judging a
bar," does not hold up: `export._bar_quarters` already refuses the `4.0`
fallback for a `None`/incomplete meter (its own docstring: *"AND ITS 4.0
FALLBACK IS REFUSED HERE... No meter, no verdict"* — ROADMAP 2.8, shipped
well before this item), and `_bar_holds_out` calls it before doing anything
else. This matches 2.12d's own PART 5 finding above (*"`_bar_holds_out`...
still requires a `Q.METER` reading before it will judge a bar at all, so
export-side there is no independent default-to-4/4 path"*) and this item's
own re-check of the same code confirms it a second time, on the actual
functions rather than by re-reading the comment. `TestExportNeverJudgesAn
UnknownBarAgainstFour4` in the new test file is a NEGATIVE-finding regression
guard, not a fix — both its assertions already pass unmodified before this
item.

## Crops

4 print crops cut, `benchmarks/omr-shape-role-2026-09/out/print/
m212j-phantom-change/` (script: `crop_2_12j_phantom_change.py`; geometry —
`staff_lines`/`staff_spacing`/`cell_box` only, for the ten specific staff/cell
subjects needed — streamed ONCE via a targeted `ijson` pass over `record.
observations` rather than the full `record_io.load_record` on a 1.6 GB file,
since these three quantities are never pooled by `record_io` — pooling there
applies only to a VERDICT's own `considered`/`basis`/`correlated` id-lists;
pages rendered straight off the PDF; no detector, no re-gather, no
re-adjudication). Each crop brackets EVERY reading staff's own cell frame in
one image (never a neighbour's lines borrowed for another staff) and labels
the decided value, its support, and what fraction of the system's own staves
read it:

| file | system | decided | support | staves | coverage |
|---|---|---|--:|---|---|
| `m212j-phantom-2-0-4.png` | 2/0 | 4/4 | 6.0 | [6, 8] | 2/14 |
| `m212j-phantom-3-0-6.png` | 3/0 | 4/4 | 11.5 | [2, 4, 5, 7] | 4/14 |
| `m212j-phantom-9-1-7.png` | 9/1 | 4/4 | 5.5 | [9, 10] | 2/13 |
| `m212j-phantom-12-0-12.png` | 12/0 | 4/4 | 5.0 | [4, 5] | 2/14 |

`VERDICT_none_yet: null` on every sidecar, for Sean — these let him confirm
no time-signature digit stack is printed at any of these mid-system cells,
matching the eleven's own `bars_fit: 0` (nothing on the page corroborates the
reading either way but the staves themselves, and those staves are a small
minority).

## Tests, RED first

`tools/omr/tests/test_staged_meter_no_phantom_common_time.py` (new file, 8
tests):

- **(a) RED, verified two ways.** (i) `test_the_fix_is_reachable_RED_without_
  it` monkeypatches `_required_corroboration` back to the bare absolute floor
  it replaces — the phantom `4/4` stands as a segment. (ii) Independently,
  `rhythm.py` was restored from `git show HEAD:...` (the fix's own commit not
  yet made — the pre-2.12j tree) and the whole new file re-run: the two
  behavioural tests that assert the decline FAILED (`[(0, 6, 8), (4, 4, 4)]
  != [(0, 6, 8)]`) while the positive-control and export-negative-finding
  tests passed unchanged, then the fixed file was restored and all 8 passed.
  A THIRD test in this class writes real, actively-CONTRADICTING bar evidence
  (3 bars of `6/8`-length `3.0` quarters at and after the change's own cell)
  and shows the fix still declines on staff coverage, not because the bars
  happened to race to the rescue this time (CLAUDE.md rule 7).
- **(b) Positive controls, so (a)'s refusal cannot pass for a rule that
  refuses everything (CLAUDE.md §6b).** All 14 of 14 staves reading a change
  still states it; 8 of 14 (57.1%, a clear majority but NOT unanimity) also
  clears the new proportional floor; the movement-start OPENING vote (a
  different code path, `adjudicate_meter`'s `voted` branch above `_meter_
  changes` entirely) is untouched.
- **(c) The export-fallback hypothesis, confirmed negative.** `_bar_quarters`
  refuses the `4.0` fallback for `None`/incomplete meters; `_bar_holds_out`
  never manufactures a `want_quarters: 4.0` refusal when no meter has ever
  been declared (a positive control in the same test proves the fixture is
  realistic: the SAME bar, WITH a meter supplied, correctly holds out).

`pytest tools/omr/tests/test_staged_meter_no_phantom_common_time.py -v`: 8
passed. `pytest tools/omr/tests -m "not slow" -q -p no:warnings -x`: **3,519
passed, 3 skipped** (3,511 on this branch's `origin/main` base — 649831a7 —
plus exactly this item's 8 new tests; no other test file touched). `python3
-m tools.omr.staged.check`: **251** (unchanged from main — this item re-wires
an EXISTING quantity's EXISTING consumer more correctly; it declares nothing
new and reaches nothing new).

## What contradicted this brief

- **"In 2.12h, `C` was a runner-up template on Brahms's headers"** pointed at
  the wrong mechanism for THIS item. The `would_have_been: "C"` detail that
  appears on several of the eleven `change_only` verdicts comes from the
  SAME system's own OPENING vote failing coverage at cell 0 (a low-confidence
  template match on ordinary continuation-header ink, unrelated to the
  meter this movement actually carries) — it is `_meter_fallbacks`' own
  detail riding along into `_change_only`'s result, NOT the cause of the
  mid-system `4/4` itself. The real mid-system candidates read via `Q.METER_
  GLYPH`'s raw DETECTOR classes (`timeSig4`, never a `C`-shaped letter class)
  at cells that are NOT the header window (cells 1-12, never cell 0).
- **"A continuation-system template match... because every staff has the
  same key-signature shape"** does not apply either — these are mid-system
  candidates, not header/cell-0 opening reads, so there is no key-signature
  window for them to share.
- **The export-side `4.0` fallback hypothesis is negative** — see above;
  2.12d's own Part 5 already established this and this item re-confirms it
  rather than finding it wrong.
- **A GATHER-side fix (rejecting `_meter_from_digits`'s scattered-digit
  reads geometrically) was viable but strictly worse for this item's proof
  budget**: it resolved 9 of 11 cases cleanly in simulation but left 2
  borderline on the exact clustering tolerance chosen, is untested territory
  (`_meter_from_digits` has no existing unit coverage), and would have
  required inventing a new geometric constant this lane could not measure
  against a calibration corpus in the time available — set aside in favour
  of reusing an already-measured legacy constant that resolves all eleven.
  Not chased further; flagged here as the SAME shape 2.12b/2.12c already
  named as a residual gap in `Q.METER_GLYPH`'s own reading quality, should a
  future item want the GATHER-side half too.

## Landing

`pytest tools/omr/tests -m "not slow" -q -p no:warnings -x`: 3,519 passed, 3
skipped. `python3 -m tools.omr.staged.check`: 251 (unchanged from main). No
GATHER change; `tools/omr/staged/adjudicators/rhythm.py` is the only file
touched besides the new test file and this benchmark's own crop script.
