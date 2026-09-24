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
