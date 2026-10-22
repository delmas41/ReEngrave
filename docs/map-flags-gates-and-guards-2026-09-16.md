# Map: flags, gates, and guards

Generated 2026-09-17 at commit `29fa5ca4` by `benchmarks/omr-flags-map-2026-09/build_doc.py`. Re-run that script to re-derive every mechanical fact in this file (file:line, default literal, presence-in-CLAUDE.md, and the allow/deny-list direction for flags whose comparison is a simple inline one). The one-line "what it gates" descriptions, the STAGE column, the byte-identical claim, and the numeric-guard MEASURED/ASSERTED judgement are **hand-authored syntheses of CLAUDE.md and the source**, each cited to a file:line or a CLAUDE.md line — they are not re-derived by the script, because CLAUDE.md expresses that judgement in prose, not as a grep-able keyword. Where this document could not verify a claim it says `UNANNOTATED` / `not characterized` rather than asserting one.

## 0. Sean's question, and the honest answer

> "Do we have a single place where all gates, guards, default settings or anything that could be flipped is stored? If we have a map then it should have all of the basic info of what is going where, what their rules are and what options/defaults are."

**No, and this file is that place now.** Three things existed before this document and none of them was complete on its own:

1. [`tools/omr/tests/test_flag_default_direction.py`](../tools/omr/tests/test_flag_default_direction.py) — derives every `os.environ.get(FLAG, default)` site compared *inline* to a literal word set, and enforces the allow-list/deny-list direction against the default. **It is the source of truth for the flags it can see.** Section 3 below documents the two syntactic patterns in this codebase it cannot see at all.
2. CLAUDE.md's "OMR knobs" table (search `## Environment variables` and the knobs table above it) — prose with the measured evidence and the reasons, for the flags someone remembered to add a row for.
3. [`docs/architecture-decision-map.md`](architecture-decision-map.md) — a CONSTANT/FLAG column inside each of ~12 per-decision tables in §5, organized by decision point rather than by flag; it overlaps this document's numeric-guard table but does not attempt to be a flat index.

**Positive controls, so the zeros below mean something:** this document's mechanical scan found **61 distinct env flags** (OMR_*/MAESTRO_*) at **66 call sites**, and **218 distinct numeric guard constants** at module level under `tools/omr/`.

---

## 1. Env flags

Every `os.environ.get(...)` / `os.getenv(...)` call under `tools/` or `backend/` (excluding tests) naming a literal or module-constant `OMR_*`/`MAESTRO_*` flag name. **Direction** is `deny-list (default ON)` / `allow-list (default OFF)` only where `test_flag_default_direction.py`'s own inline-comparison scan can see the site (CLAUDE.md's own rule: an OFF test must be a deny-list if the default is ON, and vice versa, or a typo silently flips the flag the wrong way). Where the site does not fit that scan's pattern, direction was read by hand and is marked so — see §3.1.

| Flag | Site (file:line) | Default | Direction | Stage | What it gates | Flag-off byte-identical? (CLAUDE.md) | In CLAUDE.md at all? |
|---|---|---|---|---|---|---|---|
| `MAESTRO_ANALYZE_TS` | `backend/modules/maestro_bridge.py:35` | _(non-literal — see annotation)_ | not simple inline compare — verified by hand, see annotation | operational | override the analyze.ts entry-point path for the theory-layer bridge | not stated | yes |
| `MAESTRO_BRIDGE_ENABLED` | `backend/modules/theory_layer.py:39` | `""` | not simple inline compare — verified by hand, see annotation | web app (theory layer, host-side only) | turns on Maestro theory-layer enrichment (key detection, rhythm validation, scholarly cross-check) | not stated | yes |
| `MAESTRO_NODE_BIN` | `backend/modules/maestro_bridge.py:36` | `node` | not simple inline compare — verified by hand, see annotation | operational | override the node binary path for the theory-layer bridge | not stated | yes |
| `MAESTRO_PITCH_RERANK_ENABLED` | `backend/modules/theory_layer.py:45` | `""` | not simple inline compare — verified by hand, see annotation | web app (theory layer, host-side only) | turns on M4 pitch re-ranking against the detected key (local OMR engine only) | not stated | yes |
| `MAESTRO_PITCH_RERANK_THRESHOLD` | `backend/modules/theory_layer.py:52` | `0.9` | not simple inline compare — verified by hand, see annotation | web app (theory layer, host-side only) | minimum re-rank confidence to auto-correct a pitch | not stated | yes |
| `MAESTRO_TIMEOUT_S` | `backend/modules/maestro_bridge.py:43` | `60` | not simple inline compare — verified by hand, see annotation | web app (theory layer, host-side only) | subprocess timeout for the node/tsx theory-layer bridge | not stated | yes |
| `MAESTRO_TSX_BIN` | `backend/modules/maestro_bridge.py:39` | _(non-literal — see annotation)_ | not simple inline compare — verified by hand, see annotation | operational | override the tsx binary path for the theory-layer bridge | not stated | yes |
| `OMR_ABSENT_INSTRUMENT_VETO` | `tools/omr/absent_instrument.py:120` | _(non-literal — see annotation)_ | not simple inline compare — verified by hand, see annotation | legacy transcribe/export | refuse a staff name the movement's printed lineup cannot contain (default mode 'on', with a window/rule sub-syntax) | not stated | **no** |
| `OMR_ADJUDICATE` | `tools/omr/staged/pipeline.py:55` | _(non-literal — see annotation)_ | not simple inline compare — verified by hand, see annotation | pipeline master switch | master switch for the whole staged pipeline: off/shadow/on (anything unrecognised reads as off) | not stated | **no** |
| `OMR_ARC_ATTRIBUTION` | `tools/omr/export.py:1946` | `move` | not simple inline compare — verified by hand, see annotation | legacy transcribe/export | gives a cross-staff slur/tie to the staff whose noteheads it hugs (move) instead of leaving it on the detecting staff | not stated | yes |
| `OMR_ARC_RECLASS` | `tools/omr/export.py:2149` | `0` | allow-list (default OFF) | legacy transcribe/export | export-time tie/slur grammar veto (measured and refused on the scan family; dormant) | yes (CLAUDE.md states it) | yes |
| `OMR_BRACKET_COLUMNS` | `tools/omr/system_grouping.py:523` | `""` | deny-list (default ON) | legacy transcribe/export | decide bracket instrument-family groups by counting systemic columns rather than crossing-pixel ink | yes (CLAUDE.md states it) | yes |
| `OMR_CELL_LINE_TRACE` | `tools/omr/measure_extractor.py:1176` | `""` | not simple inline compare — verified by hand, see annotation | legacy transcribe/export | slides a measure cell's stored 5-line staff grid onto the ink beneath it, for a tilted/bowed scanned staff | yes (CLAUDE.md states it) | yes |
| `OMR_CHOIR_GROUPING` | `tools/omr/system_grouping.py:215` | `""` | deny-list (default ON) | legacy transcribe/export | two cues for choir-barred / differently-indented pages (pair-local left-edge merge + open-score guard) | yes (CLAUDE.md states it) | yes |
| `OMR_CLEF_WEIGHTS` | `tools/omr/transcribe.py:4514 (+1 more site)` | _(non-literal — see annotation)_ | not simple inline compare — verified by hand, see annotation | legacy transcribe/export | optional clef-specialist weights for a second clef-only detector pass | not stated | yes |
| `OMR_CONDENSED_PARTS` | `tools/omr/export.py:3690 (+1 more site)` | `0` | not simple inline compare — verified by hand, see annotation | legacy transcribe/export | off: one part per player on a condensed staff; 'all' also splits ordinal-join fragments | yes (CLAUDE.md states it) | yes |
| `OMR_CONF_THRESHOLD` | `backend/modules/local_omr.py:113` | `0.25` | not simple inline compare — verified by hand, see annotation | web app | minimum YOLO detection confidence | not stated | yes |
| `OMR_CONTEST_DUMP` | `tools/omr/transcribe.py:3286` | `0` | allow-list (default OFF) | operational / debug | dump cross-staff ownership-contest detail to help diagnose the dedupe/ownership arbitration | not stated | **no** |
| `OMR_CV_HAIRPINS` | `tools/omr/transcribe.py:3274` | `0` | allow-list (default OFF) | legacy transcribe/export | classical-CV hairpin (crescendo/diminuendo wedge) detector, as a second reader alongside the YOLO detections | not stated | yes |
| `OMR_DIRECTION_READERS` | `tools/omr/direction_text.py:797` | `""` | not simple inline compare — verified by hand, see annotation | operational | override which OCR rung(s) read direction-text crops (surya, tesseract, or both) instead of the domain classifier | not stated | **no** |
| `OMR_DIRECTION_TEXT` | `tools/omr/staged/gather.py:2638 (+2 more sites)` | `1` | deny-list (default ON) | legacy transcribe/export (and GATHER via staged/gather.py, staged/pipeline.py) | reads the printed words inside a system (OCR) and exports them as &lt;words&gt; | not stated | yes |
| `OMR_DIRECTION_TEXT_SCAN_GATE` | `tools/omr/staged/gather.py:2550` | `0` | allow-list (default OFF) | GATHER | staged pipeline only: skip the direction-word OCR reader on a page PROVED to be a scan (it is expensive there for little yield) | not stated | yes |
| `OMR_DPI` | `backend/modules/local_omr.py:140` | `300` | not simple inline compare — verified by hand, see annotation | web app | PDF rasterization DPI (coupled to OMR_IMGSZ, deliberately different default from the CLI) | not stated | yes |
| `OMR_ENGRAVED_WEIGHTS` | `tools/omr/transcribe.py:4580` | `""` | not simple inline compare — verified by hand, see annotation | legacy transcribe/export | override the engraved-side weights file OMR_WEIGHT_ROUTING targets | not stated | yes |
| `OMR_EVAL_INDENT_MM` | `tools/omr/training/orchestral_eval.py:336` | `""` | not simple inline compare — verified by hand, see annotation | benchmark harness only | inject a LilyPond \paper indent override when rendering an orchestral_eval fixture; raises rather than rendering silently wrong if the source has no \paper block | not stated | **no** |
| `OMR_IMGSZ` | `backend/modules/local_omr.py:129` | _(non-literal — see annotation)_ | not simple inline compare — verified by hand, see annotation | web app | YOLO inference image size (larger is not better — see CLAUDE.md's imgsz-sweep note) | not stated | yes |
| `OMR_INFER` | `tools/omr/staged/infer.py:125` | `0` | allow-list (default OFF) | INFER | runs the 4th stage (INFER) after EVALUATE, before EXPORT; collapses a NARROWED verdict using cross-staff evidence | yes (CLAUDE.md states it) | yes |
| `OMR_INSTRUMENT_CLEF_DEFAULT` | `tools/omr/contextual.py:1103 (+1 more site)` | `0` | allow-list (default OFF) | legacy transcribe/export | whether an instrument's canonical clef may stand in for one never read (named only as a historically-corrected flag) | not stated | yes |
| `OMR_KEYSIG_CORROBORATION` | `tools/omr/key_signature_corroboration.py:219` | `""` | not simple inline compare — verified by hand, see annotation | legacy transcribe/export | reverts a mid-staff key-signature change no other staff of the same system also changes at the same bar | yes (CLAUDE.md states it) | yes |
| `OMR_LABEL_MERGE_QUALITY` | `tools/omr/contextual.py:541` | `1` | deny-list (default ON) | legacy transcribe/export | quality gate on merging OCR margin-label evidence (named only as a historically-corrected flag, not documented as a knob) | not stated | yes |
| `OMR_LEFT_EDGE_SPLIT` | `tools/omr/system_grouping.py:160` | `1` | deny-list (default ON) | legacy transcribe/export | a second barline scan at each system's shared left edge adds a system break the wide connectivity window merged away | not stated | yes |
| `OMR_LINEUP_SWAP_SPLIT` | `tools/omr/movement_reference.py:224` | `0` | allow-list (default OFF) | legacy transcribe/export | movement-reference lineup-swap detection: split the reference where two adjacent systems swap staff order | not stated | **no** |
| `OMR_MAX_PAGES` | `backend/modules/local_omr.py:106` | `5` | not simple inline compare — verified by hand, see annotation | web app | hard cap on pages transcribed per OMR job | not stated | yes |
| `OMR_METER_CARRY` | `tools/omr/staged/adjudicators/rhythm.py:1016` | `1` | deny-list (default ON) | ADJUDICATE | a system with no meter reading takes the last READ meter as a candidate, weighed by that system's own bars | not stated | yes |
| `OMR_METER_FROM_BARS` | `tools/omr/staged/adjudicators/rhythm.py:1144` | `1` | deny-list (default ON) | ADJUDICATE | a system with no meter and no carry derives the bar LENGTH from its own bars; cannot cross a movement boundary | not stated | yes |
| `OMR_METER_SEGMENTS` | `tools/omr/staged/export.py:132` | `1` | deny-list (default ON) | EXPORT | exporter reads the meter in force at each BAR from Q.METER's segments, instead of one meter per staff-run | yes (CLAUDE.md states it) | yes |
| `OMR_METER_TEMPLATE_AT_BAR` | `tools/omr/staged/gather.py:2045` | `0` | allow-list (default OFF) | GATHER | asks the template meter reader at candidate mid-staff bar heads across every staff of the system (a GATHER change) | yes (CLAUDE.md states it) | yes |
| `OMR_MOVEMENT_REFERENCE` | `tools/omr/movement_reference.py:137` | `1` | deny-list (default ON) | legacy transcribe/export | whether the whole-movement reference layout is built and used for the slot/instrument join (named only as a historically-corrected flag, not documented as a knob) | not stated | yes |
| `OMR_ONE_LINE_STAVES` | `tools/omr/measure_extractor.py:1199` | `""` | not simple inline compare — verified by hand, see annotation | legacy transcribe/export | admit a one-line percussion staff into cell canonicalisation instead of dropping it before it reaches a cell | not stated | **no** |
| `OMR_PARTIAL_DYNAMICS` | `tools/omr/export.py:1502` | `off` | not simple inline compare — verified by hand, see annotation | legacy transcribe/export | off/complete/other: whether an unspellable run of dynamic letters is exported partially instead of dropped whole | yes (CLAUDE.md states it) | yes |
| `OMR_PHASE26_FIXES` | `tools/omr/template_matcher.py:39` | _(non-literal — see annotation)_ | not simple inline compare — verified by hand, see annotation | legacy classical-CV template_matcher (Phase 2.5-2.7) | staged rollout level (0-4/'all') for the template-matcher detector's own bugfixes; defaults to the full stack | not stated | **no** |
| `OMR_PHASE28_FIX_TEXT_GATE` | `tools/omr/template_matcher.py:60` | _(non-literal — see annotation)_ | not simple inline compare — verified by hand, see annotation | legacy classical-CV template_matcher (Phase 2.8) | geometric staff-vicinity gate that drops template-matcher detections far from any staff line (tempo/dynamics text) | not stated | **no** |
| `OMR_REFERENCE_MOST_LABELLED` | `tools/omr/slots.py:85` | `""` | not simple inline compare — verified by hand, see annotation | legacy transcribe/export | on/pure/off: pick the movement reference system by how many staves it NAMES rather than by which staff count recurs | not stated | **no** |
| `OMR_ROSTER` | `tools/omr/roster.py:140` | `1` | deny-list (default ON) | legacy transcribe/export | whether the roster-driven part identity layer runs at all (named only as a historically-corrected flag, not documented as a knob) | not stated | yes |
| `OMR_ROSTER_CLEF` | `tools/omr/contextual.py:1575` | `0` | allow-list (default OFF) | legacy transcribe/export | let the work's catalog roster seed a staff's clef where none was read | not stated | **no** |
| `OMR_ROSTER_LABELS` | `tools/omr/work_roster.py:136` | `0` | allow-list (default OFF) | legacy transcribe/export | resolves a truncated/ambiguous margin label against the work's catalog roster (recover, disambiguate, or veto) | not stated | yes |
| `OMR_ROSTER_RANGE_VETO` | `tools/omr/transcribe.py:3164` | `0` | not simple inline compare — verified by hand, see annotation | legacy transcribe/export | off/label/all: delete a note outside its instrument's written range, gated by how trustworthy the staff identity is | not stated | **no** |
| `OMR_ROSTER_SCORE_ORDER_VETO` | `tools/omr/offroster_name.py:107` | _(non-literal — see annotation)_ | not simple inline compare — verified by hand, see annotation | legacy transcribe/export | refuse a staff identity deduced purely from canonical score order (vs. one read off an ink label) | not stated | **no** |
| `OMR_SCORE_LANGUAGE` | `tools/omr/score_language.py:438` | `0` | allow-list (default OFF) | legacy transcribe/export | reads the document's printing tradition (Italian vs German instrument names) to settle otherwise-ambiguous abbreviations | not stated | yes |
| `OMR_SLOT_GROUP_MAP` | `tools/omr/slots.py:320` | `""` | not simple inline compare — verified by hand, see annotation | legacy transcribe/export | map/ordinal/off: how a staff's bracket-group is compared to the reference layout's group when placing a span | not stated | **no** |
| `OMR_SLOT_STITCH` | `tools/omr/export.py:3670` | `1` | deny-list (default ON) | legacy transcribe/export | joins staves into continuous parts by contextual SLOT where the ordinal join refuses (suppressed tacet staves) | not stated | yes |
| `OMR_SPAN_REFERENCE_FIT` | `tools/omr/slots.py:605` | `""` | not simple inline compare — verified by hand, see annotation | legacy transcribe/export | search/refuse/off: how a span's own reference system is placed into the document's slot space | not stated | yes |
| `OMR_SURYA_KEEP_ALIVE` | `tools/omr/staff_labels_surya.py:93` | `""` | allow-list (default OFF) | operational | keep the Surya OCR llama.cpp server resident across runs instead of spawning/killing it per run | not stated | yes |
| `OMR_SURYA_PYTHON` | `tools/omr/staff_labels_surya.py:175` | _(non-literal — see annotation)_ | not simple inline compare — verified by hand, see annotation | operational | override the python executable used to launch the Surya OCR subprocess | not stated | **no** |
| `OMR_SURYA_SENTINEL` | `tools/omr/staff_labels_surya.py:98` | _(non-literal — see annotation)_ | not simple inline compare — verified by hand, see annotation | operational | override the path of the Surya server's own sentinel file (read directly because the host's Python cannot import surya) | not stated | **no** |
| `OMR_SURYA_TIMEOUT_S` | `tools/omr/staff_labels_surya.py:79` | `900` | not simple inline compare — verified by hand, see annotation | operational | per-crop timeout (seconds) for the Surya OCR subprocess | not stated | **no** |
| `OMR_TAIL_RULE` | `tools/omr/dossier.py:521` | `exact` | not simple inline compare — verified by hand, see annotation | legacy transcribe/export | none/exact/all: whether the staves below the dossier's last read label may be trusted too | not stated | **no** |
| `OMR_WEIGHTS_PATH` | `backend/modules/local_omr.py:95` | `""` | not simple inline compare — verified by hand, see annotation | legacy transcribe/export + web app | pin one YOLO weights file for every input, disabling OMR_WEIGHT_ROUTING | not stated | yes |
| `OMR_WEIGHT_ROUTING` | `tools/omr/transcribe.py:4526` | `""` | not simple inline compare — verified by hand, see annotation | legacy transcribe/export | classify each input scan-vs-engraved and route to the weights file measured best for that domain | not stated | yes |
| `OMR_WHOLE_REST_INK` | `tools/omr/staged/export.py:182` | `1` | deny-list (default ON) | EXPORT | refuses to write a pitched &lt;note&gt; where the record says the ink is a whole rest (the one staged repair that deletes notes) | yes (CLAUDE.md states it) | yes |
| `OMR_WORK_ID` | `tools/omr/work_roster.py:301` | `""` | not simple inline compare — verified by hand, see annotation | legacy transcribe/export | name the catalogued work for a PDF the score library does not hold, so OMR_ROSTER_LABELS has a roster to resolve against | not stated | yes |

---

## 2. Numeric guards / constants

Every module-level ALL-CAPS constant assigned a plain int/float literal anywhere under `tools/omr/` (excluding tests) — the thresholds, floors, and minimums an adjudicator or detector checks against, that are not env-flag-controlled at all (flipping one means editing the source). The **MEASURED vs ASSERTED** column is hand-read from CLAUDE.md for every constant CLAUDE.md discusses by name; the rest are reported as `not mentioned in CLAUDE.md` — that is **195 of 218** names, i.e. most of the guards in this codebase carry no recorded judgement about whether their value was ever swept against real data.

⚠️ **7 constant names are reused across unrelated modules** (mechanically detected: same ALL-CAPS name, different file:line, almost certainly a different threshold with a different reason) — `DOT_ABOVE_NOTE_MAX_SPACES`, `DOT_BELOW_NOTE_MAX_SPACES`, `MIN_WITNESSES`, `ORCH_PAD_STAFF_LINES`, `PROXIMITY_PX`, `SCORE_LABEL_MATCH`, `SCORE_POSITION_WEIGHT`. A judgement quoted for one site of a reused name is never applied to the other by this table; where CLAUDE.md's own prose cross-references one by bare name (`MIN_WITNESSES` is the case in point below), this document scopes the judgement to the specific file it was read from rather than guessing which site was meant.

| Constant | Site (file:line) | Value | CLAUDE.md judgement | CLAUDE.md's own words |
|---|---|---|---|---|
| `BAND_BOTTOM_SPACES` | `tools/omr/hairpin_detection.py:81` | `6.0` | not mentioned in CLAUDE.md |  |
| `BAND_LEFT_SPACINGS` | `tools/omr/bracket_reader.py:60` | `9.0` | not mentioned in CLAUDE.md |  |
| `BAND_RIGHT_SPACINGS` | `tools/omr/bracket_reader.py:61` | `3.0` | not mentioned in CLAUDE.md |  |
| `BAND_SPACES` | `tools/omr/training/staff_removal_eval.py:123` | `0.25` | not mentioned in CLAUDE.md |  |
| `BAND_TOP_SPACES` | `tools/omr/hairpin_detection.py:80` | `0.3` | not mentioned in CLAUDE.md |  |
| `BARLINE_MAX_WIDTH_LINESPACINGS` | `tools/omr/measure_extractor.py:91` | `0.7` | not mentioned in CLAUDE.md |  |
| `BARLINE_MIN_DISTANCE_PX` | `tools/omr/measure_extractor.py:92` | `60` | not mentioned in CLAUDE.md |  |
| `BARLINE_MIN_HEIGHT_FRAC` | `tools/omr/measure_extractor.py:78` | `0.8` | not mentioned in CLAUDE.md |  |
| `BEAM_EDGE_TOLERANCE_WIDTHS` | `tools/omr/staged/adjudicators/rhythm.py:102` | `1.0` | informed by measurement, not itself swept | the overshoot it must absorb 'clusters at 0.35-0.47 notehead widths'; the tolerance is set to 1.0, comfortably above that cluster, but no plateau is shown for 1.0 itself |
| `BEAM_Y_CLUSTER_FACTOR` | `tools/omr/rhythm.py:131` | `0.35` | not mentioned in CLAUDE.md |  |
| `BLANKS_TAR_SIZE` | `tools/omr/training/augment_scoreaug.py:103` | `195164160` | not mentioned in CLAUDE.md |  |
| `BRACKET_COLUMN_MIN_EVIDENCE` | `tools/omr/system_grouping.py:480` | `3` | justified by one counter-example, not a sweep | 'load-bearing -- a LilyPond render bars per staff, a 25-staff Bruckner system carries two crossing columns total, and without the floor the rule manufactured 11 groups from it' |
| `BRACKET_COLUMN_SUPPORT` | `tools/omr/system_grouping.py:454` | `0.5` | not mentioned in CLAUDE.md |  |
| `BRACKET_COLUMN_TOL_SPACINGS` | `tools/omr/system_grouping.py:450` | `0.75` | not mentioned in CLAUDE.md |  |
| `BRIDGE_GAP_TOLERANCE_SPACINGS` | `tools/omr/system_grouping.py:93` | `0.6` | not mentioned in CLAUDE.md |  |
| `BRIDGE_INK_FRACTION` | `tools/omr/system_grouping.py:84` | `0.8` | not mentioned in CLAUDE.md |  |
| `CANONICAL_STAFF_SPAN_PX` | `tools/omr/measure_extractor.py:37` | `400` | mentioned, but not with a measured/asserted judgement — unchecked |  |
| `CELL_LINE_MAX_SHIFT_SPACES` | `tools/omr/measure_extractor.py:1121` | `0.75` | not mentioned in CLAUDE.md |  |
| `CELL_LINE_MIN_ROWS_COVERED` | `tools/omr/measure_extractor.py:1142` | `4` | not mentioned in CLAUDE.md |  |
| `CELL_LINE_MIN_ROW_COVERAGE` | `tools/omr/measure_extractor.py:1129` | `0.45` | not mentioned in CLAUDE.md |  |
| `CELL_LINE_MIN_SHIFT_SPACES` | `tools/omr/measure_extractor.py:1152` | `0.05` | not mentioned in CLAUDE.md |  |
| `CELL_LINE_MIN_WIDTH_SPACES` | `tools/omr/measure_extractor.py:1166` | `4.0` | not mentioned in CLAUDE.md |  |
| `CELL_NEIGHBOUR_CLEARANCE_SPACES` | `tools/omr/measure_extractor.py:70` | `0.5` | not mentioned in CLAUDE.md |  |
| `CHOIR_MERGE_MIN_CROSS` | `tools/omr/system_grouping.py:205` | `1` | not mentioned in CLAUDE.md |  |
| `CLOSE_SPACINGS` | `tools/omr/bracket_reader.py:65` | `0.6` | not mentioned in CLAUDE.md |  |
| `COLUMN_LINK_OVERLAP` | `tools/omr/bracket_reader.py:72` | `0.7` | not mentioned in CLAUDE.md |  |
| `COLUMN_MIN_INDEPENDENT_WITNESSES` | `tools/omr/staged/inferences.py:35` | `2` | ASSERTED | 'COLUMN_MIN_INDEPENDENT_WITNESSES = 2 is unmeasured and its price is 28' |
| `CONF_HIGH` | `tools/omr/staged/adjudicators/clef.py:41` | `0.6` | not mentioned in CLAUDE.md |  |
| `CONF_LOW` | `tools/omr/staged/adjudicators/clef.py:42` | `0.3` | not mentioned in CLAUDE.md |  |
| `CONTEST_IOU` | `tools/omr/staged/gather.py:487` | `0.5` | ASSERTED (and the cited justification does not exist) | 'restates the measured _CROSS_STAFF_DUPLICATE_IOU = 0.3 and cites an assumption record that does not exist' -- grep -rn A-OWN-3 returns that one line and nothing else |
| `CROP_PAD_X_SPACES` | `tools/omr/direction_text.py:569` | `1.3` | not mentioned in CLAUDE.md |  |
| `CROP_PAD_Y_SPACES` | `tools/omr/direction_text.py:570` | `0.45` | not mentioned in CLAUDE.md |  |
| `CROSS_HALF_WIDTH_SPACES` | `tools/omr/annotate/ledger_grid.py:70` | `0.1` | not mentioned in CLAUDE.md |  |
| `CV_CONFIDENCE` | `tools/omr/hairpin_detection.py:285` | `0.99` | not mentioned in CLAUDE.md |  |
| `DEFAULTED_CLEF_MAX_WEIGHT` | `tools/omr/transcribe.py:1434` | `1.5` | not mentioned in CLAUDE.md |  |
| `DEFAULTED_CLEF_WEIGHT` | `tools/omr/transcribe.py:1425` | `0.5` | mentioned, but not with a measured/asserted judgement — unchecked |  |
| `DEFAULT_CLASSIFY_PAGES` | `tools/omr/input_domain.py:44` | `12` | not mentioned in CLAUDE.md |  |
| `DEFAULT_MIN_IOU` | `tools/omr/training/mxl_verdicts.py:91` | `0.3` | not mentioned in CLAUDE.md |  |
| `DEFAULT_MIN_STRENGTH` | `tools/omr/training/mxl_verdicts.py:90` | `0.5` | not mentioned in CLAUDE.md |  |
| `DEFAULT_WINDOW` | `tools/omr/absent_instrument.py:82` | `0` | not mentioned in CLAUDE.md |  |
| `DOT_ABOVE_NOTE_MAX_SPACES` | `tools/omr/rhythm.py:1118` | `0.75` | MEASURED | signed offsets are bimodal: 52 at 0.00 spaces, 52 at +0.50, nothing between +0.57 and +3.75 |
| `DOT_ABOVE_NOTE_MAX_SPACES` | `tools/omr/staged/adjudicators/rhythm.py:63` | `0.75` | MEASURED | signed offsets are bimodal: 52 at 0.00 spaces, 52 at +0.50, nothing between +0.57 and +3.75 |
| `DOT_BELOW_NOTE_MAX_SPACES` | `tools/omr/rhythm.py:1133` | `0.25` | MEASURED | same bimodal distribution as DOT_ABOVE_NOTE_MAX_SPACES; the window is asymmetric because a dot never sits below its note |
| `DOT_BELOW_NOTE_MAX_SPACES` | `tools/omr/staged/adjudicators/rhythm.py:64` | `0.25` | MEASURED | same bimodal distribution as DOT_ABOVE_NOTE_MAX_SPACES; the window is asymmetric because a dot never sits below its note |
| `ENGRAVED_MIN_DRAWINGS` | `tools/omr/input_domain.py:40` | `50` | not mentioned in CLAUDE.md |  |
| `EVENT_X_TOLERANCE_FALLBACK_PX` | `tools/omr/staged/adjudicators/rhythm.py:739` | `30.0` | not mentioned in CLAUDE.md |  |
| `EVENT_X_TOLERANCE_WIDTHS` | `tools/omr/staged/adjudicators/rhythm.py:735` | `0.6` | not mentioned in CLAUDE.md |  |
| `FINE_BLOCK_SIZE` | `tools/omr/class_aliases.py:164` | `136` | not mentioned in CLAUDE.md |  |
| `FLAT_SHAPE_THRESHOLD` | `tools/omr/key_signature_locator.py:243` | `0.62` | not mentioned in CLAUDE.md |  |
| `FONT_SIZE` | `tools/omr/annotate/build_archetypes.py:55` | `56` | not mentioned in CLAUDE.md |  |
| `GROUP_BOUNDARY_RATIO` | `tools/omr/system_grouping.py:97` | `0.5` | not mentioned in CLAUDE.md |  |
| `GROUP_LINE_SPACING_TOLERANCE` | `tools/omr/staff_detector.py:44` | `0.3` | not mentioned in CLAUDE.md |  |
| `GUTTER_PX` | `tools/omr/staff_labels_vision.py:130` | `70` | not mentioned in CLAUDE.md |  |
| `HEADER_SPECIALIST_REFERENCE_DPI` | `tools/omr/transcribe.py:1248` | `300` | not mentioned in CLAUDE.md |  |
| `HIGH_CONFIDENCE_FIT` | `tools/omr/clef_correction.py:70` | `0.9` | not mentioned in CLAUDE.md |  |
| `LABEL_COVERAGE_OK` | `tools/omr/contextual.py:420` | `0.75` | not mentioned in CLAUDE.md |  |
| `LABEL_RIGHT_MARGIN_PX` | `tools/omr/staff_labels.py:50` | `40` | not mentioned in CLAUDE.md |  |
| `LEDGER_ROUND_UP` | `tools/omr/staged/gather.py:494` | `0.25` | not mentioned in CLAUDE.md |  |
| `LEFT_BAND_GATE_FRAC` | `tools/omr/system_grouping.py:150` | `0.7` | not mentioned in CLAUDE.md |  |
| `LEFT_BAND_LEFT_SPACINGS` | `tools/omr/system_grouping.py:142` | `2.0` | not mentioned in CLAUDE.md |  |
| `LEFT_BAND_MIN_CROSS` | `tools/omr/system_grouping.py:144` | `1` | not mentioned in CLAUDE.md |  |
| `LEFT_BAND_RIGHT_SPACINGS` | `tools/omr/system_grouping.py:143` | `4.5` | not mentioned in CLAUDE.md |  |
| `LEVEL_TOL_SPACINGS` | `tools/omr/bracket_reader.py:288` | `0.75` | not mentioned in CLAUDE.md |  |
| `LINE_CROSSING_FACTOR` | `tools/omr/staff_line_removal.py:73` | `2.0` | not mentioned in CLAUDE.md |  |
| `LINE_ONLY_HEIGHT_MULT` | `tools/omr/header_ink.py:438` | `2.0` | not mentioned in CLAUDE.md |  |
| `LINE_SEARCH_RADIUS_SPACES` | `tools/omr/staff_line_removal.py:90` | `0.25` | not mentioned in CLAUDE.md |  |
| `MAJORITY_SHARE` | `tools/omr/key_consensus.py:117` | `0.6` | not mentioned in CLAUDE.md |  |
| `MARGIN_FLOOR` | `tools/omr/staged/adjudicators/clef.py:65` | `1.0` | not mentioned in CLAUDE.md |  |
| `MARGIN_SPACINGS` | `tools/omr/staff_labels_vision.py:125` | `30.0` | not mentioned in CLAUDE.md |  |
| `MAX_BLANK_WIDTH_SPACES` | `tools/omr/hairpin_detection.py:104` | `3.0` | not mentioned in CLAUDE.md |  |
| `MAX_CELL_WIDTH_PX` | `tools/omr/measure_extractor.py:38` | `2048` | not mentioned in CLAUDE.md |  |
| `MAX_COMPONENT_GROWTH` | `tools/omr/hairpin_detection.py:90` | `2.0` | not mentioned in CLAUDE.md |  |
| `MAX_CROP_UPSCALE` | `tools/omr/direction_text.py:588` | `4.0` | not mentioned in CLAUDE.md |  |
| `MAX_EDGE_PX` | `tools/omr/staff_labels_vision.py:131` | `1568` | not mentioned in CLAUDE.md |  |
| `MAX_ERASABLE_RUN_SPACES` | `tools/omr/staff_line_removal.py:82` | `0.45` | not mentioned in CLAUDE.md |  |
| `MAX_GROUP_BLOCKS` | `tools/omr/slots.py:360` | `12` | not mentioned in CLAUDE.md |  |
| `MAX_HEADER_LINE_SHIFT_SPACES` | `tools/omr/header_ink.py:157` | `0.6` | not mentioned in CLAUDE.md |  |
| `MAX_LINE_INK_RUNS_PER_SPACE` | `tools/omr/staff_detector.py:57` | `1.7` | not mentioned in CLAUDE.md |  |
| `MAX_LINE_THICKNESS_SPACES` | `tools/omr/staff_line_removal.py:67` | `0.35` | not mentioned in CLAUDE.md |  |
| `MAX_OUTLINE_RMS_SPACES` | `tools/omr/hairpin_detection.py:86` | `0.1` | not mentioned in CLAUDE.md |  |
| `MAX_PHRASE_TOKENS` | `tools/omr/direction_lexicon.py:123` | `6` | not mentioned in CLAUDE.md |  |
| `MAX_RULE_THICKNESS_SPACINGS` | `tools/omr/bracket_reader.py:275` | `1.75` | not mentioned in CLAUDE.md |  |
| `MAX_SPACES` | `tools/omr/annotate/ledger_grid.py:66` | `6.5` | not mentioned in CLAUDE.md |  |
| `MAX_STAFF_DISTANCE_FRAC` | `tools/omr/staff_labels.py:54` | `0.5` | not mentioned in CLAUDE.md |  |
| `MAX_SYSTEM_GAP_FACTOR` | `tools/omr/staff_detector.py:45` | `6.0` | not mentioned in CLAUDE.md |  |
| `MAX_WIDTH_SPACES` | `tools/omr/hairpin_detection.py:98` | `30.0` | not mentioned in CLAUDE.md |  |
| `MERGE_CAP_RATIO` | `tools/omr/movement_reference.py:80` | `2.0` | not mentioned in CLAUDE.md |  |
| `METER_AGREEMENT_FLOOR` | `tools/omr/staged/adjudicators/rhythm.py:923` | `0.7` | not mentioned in CLAUDE.md |  |
| `METER_CARRY_FLOOR` | `tools/omr/staged/adjudicators/rhythm.py:1077` | `2.0` | MEASURED (indirectly, via the boundary swing) | the +8.0 (true) vs -8.0 (false) swing that motivates the carry is measured against this floor of 2.0; the floor value itself is not independently swept |
| `METER_CARRY_MIN_BARS` | `tools/omr/staged/adjudicators/rhythm.py:1095` | `2` | not characterized (one observed cost, not a sweep) | 'METER_CARRY_MIN_BARS = 2 was seen refusing a CORRECT carry (a one-bar system whose single bar agrees), the first time that constant's price has been observed' |
| `METER_CARRY_MIN_STAVES_PER_BAR` | `tools/omr/staged/adjudicators/rhythm.py:1100` | `3` | ASSERTED | 'weights that are asserted, not measured -- METER_CARRY_MIN_STAVES_PER_BAR = 3 is set by analogy to METER_COVERAGE_FLOOR and never measured at all' |
| `METER_CHANGE_FLOOR` | `tools/omr/staged/adjudicators/rhythm.py:1355` | `3.0` | not characterized | named only as the threshold five spurious changes fall 'just over'; no sweep or plateau is quoted for its own value |
| `METER_CHANGE_MIN_STAVES` | `tools/omr/staged/adjudicators/rhythm.py:1423` | `2` | ASSERTED (by cross-reference to another asserted constant) | 'METER_CHANGE_MIN_STAVES = 2, asserted equal to key_signature_corroboration.MIN_WITNESSES -- not a tuned constant, because the populations overlap at 1 and every value above 1 confines the same four segments' |
| `METER_COVERAGE_FLOOR` | `tools/omr/staged/adjudicators/rhythm.py:946` | `0.5` | not characterized (only used as the analogy basis for another admittedly-asserted constant) | cited only as what METER_CARRY_MIN_STAVES_PER_BAR was set 'by analogy to' |
| `METER_FROM_BARS_FLOOR` | `tools/omr/staged/adjudicators/rhythm.py:1183` | `4.0` | mentioned, but not with a measured/asserted judgement — unchecked |  |
| `METER_TEMPLATE_AT_BAR_MIN_CANDIDATE_STAVES` | `tools/omr/staged/gather.py:2041` | `1` | not mentioned in CLAUDE.md |  |
| `METER_TEMPLATE_AT_BAR_MIN_STAVES` | `tools/omr/staged/adjudicators/rhythm.py:1629` | `3` | MEASURED | over 1,612 mid-staff bar-head windows on ten real scanned pages ... admitted on 1 staff the reader yields 16 spurious columns, on 2 two, on 3 ZERO — so METER_TEMPLATE_AT_BAR_MIN_STAVES = 3 |
| `METER_TEMPLATE_AT_BAR_WINDOW_SPACES` | `tools/omr/staged/gather.py:2025` | `4.0` | not mentioned in CLAUDE.md |  |
| `MIN_AGREEMENT` | `tools/omr/score_layouts.py:193` | `0.75` | not mentioned in CLAUDE.md |  |
| `MIN_CROP_SPACING_PX` | `tools/omr/direction_text.py:587` | `80.0` | not mentioned in CLAUDE.md |  |
| `MIN_DEFICIT_FRACTION` | `tools/omr/annotate/select_short_bar_cells.py:72` | `0.25` | not mentioned in CLAUDE.md |  |
| `MIN_DIAGNOSTIC_VOTES` | `tools/omr/score_language.py:295` | `3` | not mentioned in CLAUDE.md |  |
| `MIN_FIT` | `tools/omr/clef_correction.py:68` | `0.75` | not mentioned in CLAUDE.md |  |
| `MIN_FIT_MARGIN` | `tools/omr/clef_correction.py:69` | `0.25` | not mentioned in CLAUDE.md |  |
| `MIN_HEADER_SHIFT_GAIN` | `tools/omr/header_ink.py:160` | `1.05` | not mentioned in CLAUDE.md |  |
| `MIN_KEPT_FRACTION` | `tools/omr/work_roster.py:127` | `0.5` | not mentioned in CLAUDE.md |  |
| `MIN_KEPT_LETTERS` | `tools/omr/work_roster.py:120` | `3` | not mentioned in CLAUDE.md |  |
| `MIN_LABEL_CHARS` | `tools/omr/staff_labels.py:57` | `1` | not mentioned in CLAUDE.md |  |
| `MIN_LINE_LENGTH_FRAC` | `tools/omr/staff_detector.py:42` | `0.35` | not mentioned in CLAUDE.md |  |
| `MIN_MAJORITY` | `tools/omr/movement_reference.py:235` | `0.6` | not mentioned in CLAUDE.md |  |
| `MIN_NOTEHEADS` | `tools/omr/clef_correction.py:67` | `12` | not mentioned in CLAUDE.md |  |
| `MIN_OPEN_SPACES` | `tools/omr/hairpin_detection.py:84` | `0.5` | not mentioned in CLAUDE.md |  |
| `MIN_PEAK_DISTANCE_PX` | `tools/omr/staff_detector.py:41` | `4` | not mentioned in CLAUDE.md |  |
| `MIN_RESOLVED_BEATS` | `tools/omr/annotate/select_short_bar_cells.py:77` | `0.01` | not mentioned in CLAUDE.md |  |
| `MIN_ROSTER_NAMES` | `tools/omr/roster.py:91` | `2` | not mentioned in CLAUDE.md |  |
| `MIN_RULE_STRAIGHTNESS` | `tools/omr/bracket_reader.py:280` | `0.85` | not mentioned in CLAUDE.md |  |
| `MIN_RUN_SPACINGS` | `tools/omr/bracket_reader.py:68` | `2.0` | not mentioned in CLAUDE.md |  |
| `MIN_SCORE_PER_STAFF` | `tools/omr/score_layouts.py:196` | `0.5` | not mentioned in CLAUDE.md |  |
| `MIN_SHARE` | `tools/omr/score_language.py:299` | `0.7` | not mentioned in CLAUDE.md |  |
| `MIN_SIDE_OBS` | `tools/omr/movement_reference.py:231` | `3` | not mentioned in CLAUDE.md |  |
| `MIN_SIDE_SYSTEMS` | `tools/omr/movement_reference.py:229` | `3` | not mentioned in CLAUDE.md |  |
| `MIN_SPAN_PAGES` | `tools/omr/movement_reference.py:88` | `4` | not mentioned in CLAUDE.md |  |
| `MIN_SPAN_SYSTEMS` | `tools/omr/movement_reference.py:89` | `6` | not mentioned in CLAUDE.md |  |
| `MIN_STAVES` | `tools/omr/score_layouts.py:198` | `3` | not mentioned in CLAUDE.md |  |
| `MIN_SWAP_SUPPORT` | `tools/omr/movement_reference.py:243` | `4` | not mentioned in CLAUDE.md |  |
| `MIN_WIDTH_SPACES` | `tools/omr/hairpin_detection.py:97` | `0.8` | not mentioned in CLAUDE.md |  |
| `MIN_WITNESSES` | `tools/omr/key_consensus.py:105` | `3` | AMBIGUOUS NAME: another site shares this constant's name; a judgement exists for one of them but this row was not verified against it — see §2 note |  |
| `MIN_WITNESSES` | `tools/omr/key_signature_corroboration.py:202` | `2` | ASSERTED, but with a stated boundary argument (deliberately the weakest bar that can reject the observed failures) | 'Deliberately the WEAKEST defensible bar, and not a tuned constant. All seven observed flips sit at exactly 1 (no witness at all) in systems of 11 to 17 staves, so 2 is the first value that can reject any of them' |
| `MIN_WORD_CONF` | `tools/omr/staff_labels_tesseract.py:71` | `30.0` | not mentioned in CLAUDE.md |  |
| `MIN_X_OVERLAP_FRAC` | `tools/omr/system_grouping.py:109` | `0.5` | not mentioned in CLAUDE.md |  |
| `MISFIT_COVERAGE_FRAC` | `tools/omr/staff_detector.py:190` | `0.35` | not mentioned in CLAUDE.md |  |
| `MISFIT_MAX_SHIFT` | `tools/omr/staff_detector.py:193` | `2` | not mentioned in CLAUDE.md |  |
| `MISFIT_MIN_RUN_FRAC` | `tools/omr/staff_detector.py:149` | `0.5` | not mentioned in CLAUDE.md |  |
| `MISFIT_THICKNESS_RATIO` | `tools/omr/staff_detector.py:146` | `2.5` | not mentioned in CLAUDE.md |  |
| `NO_SIGNATURE_MIN_STAVES` | `tools/omr/key_consensus.py:125` | `3` | not mentioned in CLAUDE.md |  |
| `NO_SIGNATURE_SHARE` | `tools/omr/key_consensus.py:123` | `0.8` | not mentioned in CLAUDE.md |  |
| `ONSET_COLUMN_MIN_WITNESSES` | `tools/omr/staged/adjudicators/rhythm.py:2459` | `2` | not mentioned in CLAUDE.md |  |
| `ONSET_COLUMN_TOLERANCE_SPACES` | `tools/omr/staged/adjudicators/rhythm.py:2456` | `0.1` | not mentioned in CLAUDE.md |  |
| `ON_STAFF_MAX_STEPS` | `tools/omr/staged/adjudicators/clef.py:109` | `10.0` | not mentioned in CLAUDE.md |  |
| `ORCH_PAD_STAFF_LINES` | `tools/omr/annotate/recut_cells.py:64` | `5.0` | mentioned, but not with a measured/asserted judgement — unchecked |  |
| `ORCH_PAD_STAFF_LINES` | `tools/omr/annotate/select_cells_orchestral.py:46` | `5.0` | mentioned, but not with a measured/asserted judgement — unchecked |  |
| `OVERLAP_SPACINGS` | `tools/omr/staff_labels_vision.py:128` | `1.0` | not mentioned in CLAUDE.md |  |
| `PAD_ABOVE_STAFF_LINES` | `tools/omr/measure_extractor.py:44` | `4` | mentioned, but not with a measured/asserted judgement — unchecked |  |
| `PAD_BELOW_STAFF_LINES` | `tools/omr/measure_extractor.py:45` | `4` | not mentioned in CLAUDE.md |  |
| `PAD_MAX_STAFF_LINES` | `tools/omr/measure_extractor.py:66` | `6` | not mentioned in CLAUDE.md |  |
| `PEAK_PROMINENCE_FRAC` | `tools/omr/staff_detector.py:43` | `0.3` | not mentioned in CLAUDE.md |  |
| `PROXIMITY_PX` | `tools/omr/annotate/port_user_verdicts.py:33` | `30` | not mentioned in CLAUDE.md |  |
| `PROXIMITY_PX` | `tools/omr/annotate/port_verdicts.py:50` | `25` | not mentioned in CLAUDE.md |  |
| `PROXIMITY_PX` | `tools/omr/annotate/port_verdicts_to_yolo.py:48` | `30` | not mentioned in CLAUDE.md |  |
| `PSM` | `tools/omr/staff_labels_tesseract.py:67` | `6` | not mentioned in CLAUDE.md |  |
| `PSM_LINE` | `tools/omr/staff_labels_tesseract.py:112` | `7` | not mentioned in CLAUDE.md |  |
| `P_AUGRAPHY` | `tools/omr/training/augment_scoreaug.py:114` | `0.5` | not mentioned in CLAUDE.md |  |
| `P_BLANK_COMPOSITE` | `tools/omr/training/augment_scoreaug.py:112` | `0.85` | not mentioned in CLAUDE.md |  |
| `P_SHOW_THROUGH` | `tools/omr/training/augment_scoreaug.py:113` | `0.5` | not mentioned in CLAUDE.md |  |
| `REFERENCE_MAX_SIZE_RATIO` | `tools/omr/slots.py:74` | `2.0` | not mentioned in CLAUDE.md |  |
| `RESEGMENT_MAX_PIECE_FRAC` | `tools/omr/measure_extractor.py:1556` | `1.75` | not mentioned in CLAUDE.md |  |
| `RESEGMENT_MIN_CONNECTIVITY` | `tools/omr/measure_extractor.py:1547` | `0.5` | not mentioned in CLAUDE.md |  |
| `RESEGMENT_MIN_HEIGHT_FRAC` | `tools/omr/measure_extractor.py:1538` | `0.6` | not mentioned in CLAUDE.md |  |
| `RESEGMENT_MIN_PIECE_FRAC` | `tools/omr/measure_extractor.py:1555` | `0.5` | not mentioned in CLAUDE.md |  |
| `RESEGMENT_MIN_VOTE_FRAC` | `tools/omr/measure_extractor.py:1543` | `0.3` | not mentioned in CLAUDE.md |  |
| `RESEGMENT_STEER_WIDTH_FACTOR` | `tools/omr/measure_extractor.py:1564` | `1.5` | not mentioned in CLAUDE.md |  |
| `RESEGMENT_WIDTH_WARN_FACTOR` | `tools/omr/measure_extractor.py:1550` | `2.0` | not mentioned in CLAUDE.md |  |
| `ROSTER_PAGE_WINDOW` | `tools/omr/roster.py:83` | `3` | not mentioned in CLAUDE.md |  |
| `RUNAWAY_TEXT_MAX_CHARS` | `tools/omr/staff_labels_surya.py:155` | `120` | not mentioned in CLAUDE.md |  |
| `RUNG_BRIDGE_GAP_SPACES` | `tools/omr/annotate/ledger_grid.py:56` | `0.9` | not mentioned in CLAUDE.md |  |
| `RUNG_MAX_THICKNESS_SPACES` | `tools/omr/annotate/ledger_grid.py:59` | `0.4` | not mentioned in CLAUDE.md |  |
| `RUNG_MIN_LEN_SPACES` | `tools/omr/annotate/ledger_grid.py:52` | `1.3` | not mentioned in CLAUDE.md |  |
| `SCAN_MAX_DRAWINGS` | `tools/omr/direction_text.py:671` | `8` | not mentioned in CLAUDE.md |  |
| `SCAN_MIN_TOTAL_COVER` | `tools/omr/direction_text.py:678` | `0.95` | not mentioned in CLAUDE.md |  |
| `SCAN_TOTAL_RASTER_COVERAGE` | `tools/omr/input_domain.py:37` | `0.5` | not mentioned in CLAUDE.md |  |
| `SCORE_BAND_PER_STAFF` | `tools/omr/score_layouts.py:179` | `0.15` | not mentioned in CLAUDE.md |  |
| `SCORE_CLEF_MATCH` | `tools/omr/score_layouts.py:62` | `1.5` | not mentioned in CLAUDE.md |  |
| `SCORE_GROUP_MATCH` | `tools/omr/slots.py:53` | `1.5` | not mentioned in CLAUDE.md |  |
| `SCORE_LABEL_MATCH` | `tools/omr/score_layouts.py:56` | `6.0` | ASSERTED (cited as a Class-B probability-gate fault) | 'formed then quantised ... a flat SCORE_LABEL_MATCH = 6.0 -- slots.py and score_layouts.py are ALREADY additive-evidence models and the evidence is binarised twice on the way in' |
| `SCORE_LABEL_MATCH` | `tools/omr/slots.py:51` | `6.0` | ASSERTED (cited as a Class-B probability-gate fault) | 'formed then quantised ... a flat SCORE_LABEL_MATCH = 6.0 -- slots.py and score_layouts.py are ALREADY additive-evidence models and the evidence is binarised twice on the way in' |
| `SCORE_POSITION_WEIGHT` | `tools/omr/score_layouts.py:74` | `1.0` | not mentioned in CLAUDE.md |  |
| `SCORE_POSITION_WEIGHT` | `tools/omr/slots.py:55` | `1.0` | not mentioned in CLAUDE.md |  |
| `SINGLE_LINE_CLEARANCE_SPACES` | `tools/omr/staff_detector.py:89` | `4.0` | not mentioned in CLAUDE.md |  |
| `SINGLE_LINE_CLUSTER_WIDTH_FRAC` | `tools/omr/staff_detector.py:123` | `0.9` | not mentioned in CLAUDE.md |  |
| `SINGLE_LINE_MIN_OVERLAP_FRAC` | `tools/omr/staff_detector.py:94` | `0.6` | not mentioned in CLAUDE.md |  |
| `SINGLE_LINE_MIN_WIDTH_FRAC` | `tools/omr/staff_detector.py:93` | `0.5` | not mentioned in CLAUDE.md |  |
| `SINGLE_LINE_NEIGHBOUR_RUN_FRAC` | `tools/omr/staff_detector.py:102` | `0.5` | not mentioned in CLAUDE.md |  |
| `SMALL_HEAD_RATIO` | `tools/omr/training/mxl_verdicts.py:99` | `0.85` | not mentioned in CLAUDE.md |  |
| `SPAN_MIN_INK` | `tools/omr/measure_extractor.py:98` | `0.9` | not mentioned in CLAUDE.md |  |
| `STAFF_COMB_POOL_FRAC` | `tools/omr/staff_detector.py:71` | `0.3` | not mentioned in CLAUDE.md |  |
| `STAFF_COMB_TOLERANCE` | `tools/omr/staff_detector.py:74` | `0.25` | not mentioned in CLAUDE.md |  |
| `STAFF_EXTENT_MIN_LINES` | `tools/omr/staff_detector.py:55` | `3` | not mentioned in CLAUDE.md |  |
| `STAFF_LINE_BAND_SPACES` | `tools/omr/staff_detector.py:51` | `0.35` | not mentioned in CLAUDE.md |  |
| `STAFF_LINE_MAX_GAP_SPACES` | `tools/omr/staff_detector.py:46` | `1.0` | not mentioned in CLAUDE.md |  |
| `STAFF_SPACING_OUTLIER_FACTOR` | `tools/omr/staff_detector.py:79` | `1.6` | not mentioned in CLAUDE.md |  |
| `STEM_KERNEL_MARGIN` | `tools/omr/line_detection.py:122` | `0.8` | not mentioned in CLAUDE.md |  |
| `STEM_MAX_HEIGHT_LINES` | `tools/omr/line_detection.py:170` | `8.0` | MEASURED | 6.0 gives 0.1861, 7.0 gives 0.1601, 8.0 gives 0.1601, 9.0 gives 0.1610 (swept, sits on the plateau at 7.0-8.0) |
| `SYSTEM_BREAK_GAP_FACTOR` | `tools/omr/staff_detector.py:56` | `2.5` | not mentioned in CLAUDE.md |  |
| `TARGET_STAFF_SPACE_PX` | `tools/omr/yolo_detector.py:218` | `16` | not mentioned in CLAUDE.md |  |
| `TIE_SAME_POSITION_MAX_SPACES` | `tools/omr/transcribe.py:2418` | `0.25` | MEASURED | sits in a MEASURED empty interval (engraved same-pitch links max 0.168, one-step-apart links min 0.435) |
| `TILE` | `tools/omr/annotate/build_archetypes.py:54` | `72` | not mentioned in CLAUDE.md |  |
| `UPSCALE` | `tools/omr/staff_labels_tesseract.py:68` | `2` | not mentioned in CLAUDE.md |  |
| `WANDER_QUANTILE` | `tools/omr/header_ink.py:449` | `99.0` | not mentioned in CLAUDE.md |  |
| `WHOLE_REST_INK_MAX_ASPECT` | `tools/omr/staged/adjudicators/rhythm.py:2814` | `3.09` | not mentioned in CLAUDE.md |  |
| `WHOLE_REST_INK_MAX_HEIGHT_SPACES` | `tools/omr/staged/adjudicators/rhythm.py:2804` | `0.84` | not mentioned in CLAUDE.md |  |
| `WHOLE_REST_INK_MIN_ASPECT` | `tools/omr/staged/adjudicators/rhythm.py:2807` | `1.63` | not mentioned in CLAUDE.md |  |
| `WHOLE_REST_NEIGHBOUR_BARS` | `tools/omr/staged/adjudicators/rhythm.py:2832` | `2` | not mentioned in CLAUDE.md |  |
| `WHOLE_REST_NEIGHBOUR_STEPS` | `tools/omr/staged/adjudicators/rhythm.py:2836` | `1.5` | not mentioned in CLAUDE.md |  |
| `WHOLE_REST_STEP` | `tools/omr/staged/adjudicators/rhythm.py:2820` | `5.5` | not mentioned in CLAUDE.md |  |
| `WHOLE_REST_STEP_TOLERANCE` | `tools/omr/staged/adjudicators/rhythm.py:2826` | `1.0` | not mentioned in CLAUDE.md |  |
| `WINDOW_HALF_WIDTH_SPACES` | `tools/omr/annotate/ledger_grid.py:69` | `1.1` | not mentioned in CLAUDE.md |  |
| `WINDOW_MARGIN_SPACINGS` | `tools/omr/system_grouping.py:105` | `4.0` | not mentioned in CLAUDE.md |  |
| `W_CARRY` | `tools/omr/staged/adjudicators/clef.py:49` | `1.5` | not mentioned in CLAUDE.md |  |
| `W_CHANGE_BAR_FITS` | `tools/omr/staged/adjudicators/rhythm.py:1348` | `1.0` | not mentioned in CLAUDE.md |  |
| `W_CHANGE_GLYPH_LOOSE` | `tools/omr/staged/adjudicators/rhythm.py:1343` | `0.5` | not mentioned in CLAUDE.md |  |
| `W_CHANGE_GLYPH_PAIR` | `tools/omr/staged/adjudicators/rhythm.py:1339` | `3.0` | not mentioned in CLAUDE.md |  |
| `W_C_FAMILY` | `tools/omr/staged/adjudicators/clef.py:82` | `1.5` | not mentioned in CLAUDE.md |  |
| `W_DETECTOR_HIGH` | `tools/omr/staged/adjudicators/clef.py:44` | `3.0` | not mentioned in CLAUDE.md |  |
| `W_DETECTOR_LOW` | `tools/omr/staged/adjudicators/clef.py:46` | `0.4` | not mentioned in CLAUDE.md |  |
| `W_DETECTOR_MID` | `tools/omr/staged/adjudicators/clef.py:45` | `1.5` | not mentioned in CLAUDE.md |  |
| `W_DISTANCE` | `tools/omr/staged/adjudicators/ownership.py:27` | `0.5` | not mentioned in CLAUDE.md |  |
| `W_DOSSIER` | `tools/omr/staged/adjudicators/clef.py:51` | `4.0` | not mentioned in CLAUDE.md |  |
| `W_INSTRUMENT` | `tools/omr/staged/adjudicators/clef.py:50` | `1.0` | not mentioned in CLAUDE.md |  |
| `W_KEYSIG_FIT` | `tools/omr/staged/adjudicators/clef.py:115` | `1.5` | not mentioned in CLAUDE.md |  |
| `W_LADDER_COMPLETE` | `tools/omr/staged/adjudicators/ownership.py:25` | `4.0` | not mentioned in CLAUDE.md |  |
| `W_LOCATOR` | `tools/omr/staged/adjudicators/clef.py:47` | `2.0` | not mentioned in CLAUDE.md |  |
| `W_METER_BAR_FITS` | `tools/omr/staged/adjudicators/rhythm.py:1062` | `1.0` | not mentioned in CLAUDE.md |  |
| `W_METER_CARRIED` | `tools/omr/staged/adjudicators/rhythm.py:1051` | `1.0` | mentioned, but not with a measured/asserted judgement — unchecked |  |
| `W_ON_THIS_STAFF` | `tools/omr/staged/adjudicators/clef.py:98` | `1.5` | not mentioned in CLAUDE.md |  |
| `W_SPECIALIST` | `tools/omr/staged/adjudicators/clef.py:48` | `1.0` | not mentioned in CLAUDE.md |  |
| `YOLO_BEAM_MAX_CELL_FRACTION` | `tools/omr/rhythm.py:849` | `0.6` | not mentioned in CLAUDE.md |  |

---

## 3. Disagreements

### 3.1 A blind spot in the existing derived check itself

`test_flag_default_direction.py`'s `default_on_flags()` only matches a comparison written **inline** — `os.environ.get(FLAG, default) in {...}` (after unwrapping `.strip()`/`.lower()`) on the SAME expression. Reading the source for the flags this document's broader scan found (§1) turned up **two syntactic patterns that check is blind to**, both real and both currently used correctly (verified by hand, not by the automated check):

1. **Two-statement form** — `raw = os.environ.get(FLAG, default)` on one line, `return raw in {...}` (or `not in`) on another. Examples: `OMR_CELL_LINE_TRACE` (`tools/omr/measure_extractor.py:1176-1177`), `OMR_ONE_LINE_STAVES` (`tools/omr/measure_extractor.py:1199-1200`).
2. **`(env if env is not None else os.environ).get(...)`** — an injectable-environ pattern used for testability. Examples: `OMR_KEYSIG_CORROBORATION` (`tools/omr/key_signature_corroboration.py:219`), `OMR_ABSENT_INSTRUMENT_VETO` (`tools/omr/absent_instrument.py:120`), `OMR_ROSTER_SCORE_ORDER_VETO` (`tools/omr/offroster_name.py:107`).

All five read correctly by hand (deny-list for the three default-ON ones, allow-list for the two default-OFF ones), so this is not a live bug — but it means the guard CLAUDE.md itself calls the fix for *"a typo or an empty value would turn it OFF"* silently does not run on these five sites. A sixth flag, `OMR_ADJUDICATE`, uses neither pattern the check recognises NOR either of these two — it compares against a 3-way mode tuple (`raw in (MODE_OFF, MODE_SHADOW, MODE_ON)`) with an unrecognised value falling back to OFF, which is the correct fail-safe shape for a default-off master switch but is also invisible to the existing test.

### 3.2 Flags that exist in the code and CLAUDE.md never documents

This is split into two mechanically-distinct buckets, because "absent from a knobs table" and "absent from the file entirely" are different failure sizes, and the two must not be collapsed into one hand-typed list — the earlier draft of this section did exactly that (typed the flag names by hand instead of reading them off the computed sets below) and as a result misfiled `OMR_CV_HAIRPINS` and `OMR_SPAN_REFERENCE_FIT` into the wrong bucket. Both buckets below are rendered directly from the same `not_in_md` / `mentioned_no_row` sets used for the counts, so this cannot drift from them again silently.

**3.2a — 18 of 61: the flag's name never appears in CLAUDE.md at all** (checked with a plain `\bFLAG\b` regex over the whole file, so this is not a knobs-table formatting artefact — a flag mentioned only in prose would still be caught here as present).

- **`OMR_ABSENT_INSTRUMENT_VETO`** — refuse a staff name the movement's printed lineup cannot contain (default mode 'on', with a window/rule sub-syntax)
- **`OMR_ADJUDICATE`** — master switch for the whole staged pipeline: off/shadow/on (anything unrecognised reads as off)
- **`OMR_CONTEST_DUMP`** — dump cross-staff ownership-contest detail to help diagnose the dedupe/ownership arbitration
- **`OMR_DIRECTION_READERS`** — override which OCR rung(s) read direction-text crops (surya, tesseract, or both) instead of the domain classifier
- **`OMR_EVAL_INDENT_MM`** — inject a LilyPond \paper indent override when rendering an orchestral_eval fixture; raises rather than rendering silently wrong if the source has no \paper block
- **`OMR_LINEUP_SWAP_SPLIT`** — movement-reference lineup-swap detection: split the reference where two adjacent systems swap staff order
- **`OMR_ONE_LINE_STAVES`** — admit a one-line percussion staff into cell canonicalisation instead of dropping it before it reaches a cell
- **`OMR_PHASE26_FIXES`** — staged rollout level (0-4/'all') for the template-matcher detector's own bugfixes; defaults to the full stack
- **`OMR_PHASE28_FIX_TEXT_GATE`** — geometric staff-vicinity gate that drops template-matcher detections far from any staff line (tempo/dynamics text)
- **`OMR_REFERENCE_MOST_LABELLED`** — on/pure/off: pick the movement reference system by how many staves it NAMES rather than by which staff count recurs
- **`OMR_ROSTER_CLEF`** — let the work's catalog roster seed a staff's clef where none was read
- **`OMR_ROSTER_RANGE_VETO`** — off/label/all: delete a note outside its instrument's written range, gated by how trustworthy the staff identity is
- **`OMR_ROSTER_SCORE_ORDER_VETO`** — refuse a staff identity deduced purely from canonical score order (vs. one read off an ink label)
- **`OMR_SLOT_GROUP_MAP`** — map/ordinal/off: how a staff's bracket-group is compared to the reference layout's group when placing a span
- **`OMR_SURYA_PYTHON`** — override the python executable used to launch the Surya OCR subprocess
- **`OMR_SURYA_SENTINEL`** — override the path of the Surya server's own sentinel file (read directly because the host's Python cannot import surya)
- **`OMR_SURYA_TIMEOUT_S`** — per-crop timeout (seconds) for the Surya OCR subprocess
- **`OMR_TAIL_RULE`** — none/exact/all: whether the staves below the dossier's last read label may be trusted too

Of these, **`OMR_ADJUDICATE`** is the one worth reading twice: it is the master on/off/shadow switch for the **entire staged pipeline** (`tools/omr/staged/pipeline.py:47-56`) — every ADJUDICATE/EVALUATE/INFER/EXPORT flag CLAUDE.md documents at great length (the meter-carry, whole-rest-ink, meter-segments, infer-stage flags in §1 above) is inert unless this reads `shadow` or `1`. Nothing in CLAUDE.md says so.

**3.2b — 9 of 61: the flag's name appears in CLAUDE.md's prose, but never in a dedicated table row** (checked for a line starting `| \`FLAG\` |` in either the OMR knobs table or the Environment variables table). A reader searching the knobs tables for these would not find them, even though the mechanism is discussed:

- **`MAESTRO_ANALYZE_TS`** — override the analyze.ts entry-point path for the theory-layer bridge (see backend/modules/maestro_bridge.py:35; CLAUDE.md env-var table)
- **`MAESTRO_TSX_BIN`** — override the tsx binary path for the theory-layer bridge (see backend/modules/maestro_bridge.py:39; CLAUDE.md env-var table)
- **`OMR_CV_HAIRPINS`** — classical-CV hairpin (crescendo/diminuendo wedge) detector, as a second reader alongside the YOLO detections (see tools/omr/transcribe.py:3274)
- **`OMR_INSTRUMENT_CLEF_DEFAULT`** — whether an instrument's canonical clef may stand in for one never read (named only as a historically-corrected flag) (see tools/omr/contextual.py:1103, tools/omr/transcribe.py:4683; CLAUDE.md only names it in the 'flag default direction' fix list, no knob-table row)
- **`OMR_LABEL_MERGE_QUALITY`** — quality gate on merging OCR margin-label evidence (named only as a historically-corrected flag, not documented as a knob) (see tools/omr/contextual.py:541; CLAUDE.md only names it in the 'flag default direction' fix list, no knob-table row)
- **`OMR_MOVEMENT_REFERENCE`** — whether the whole-movement reference layout is built and used for the slot/instrument join (named only as a historically-corrected flag, not documented as a knob) (see tools/omr/movement_reference.py:137; CLAUDE.md only names it in the 'flag default direction' fix list, no knob-table row)
- **`OMR_ROSTER`** — whether the roster-driven part identity layer runs at all (named only as a historically-corrected flag, not documented as a knob) (see tools/omr/roster.py:140; CLAUDE.md only names it in the 'flag default direction' fix list, no knob-table row)
- **`OMR_SPAN_REFERENCE_FIT`** — search/refuse/off: how a span's own reference system is placed into the document's slot space (see tools/omr/slots.py:605; this is the flag behind the 'spans regression: found and fixed same day' MEMORY.md entry)
- **`OMR_SURYA_KEEP_ALIVE`** — keep the Surya OCR llama.cpp server resident across runs instead of spawning/killing it per run (see tools/omr/staff_labels_surya.py:93; CLAUDE.md's 'Cost, and how to remove most of it' section)

Four of these nine — `OMR_MOVEMENT_REFERENCE`, `OMR_LABEL_MERGE_QUALITY`, `OMR_INSTRUMENT_CLEF_DEFAULT`, and `OMR_ROSTER` — are individually *named* in CLAUDE.md's "A flag's OFF test must follow its DEFAULT" section, as flags that once shipped with the direction backwards and were corrected — but that section only says their direction was fixed, never what the flag currently does or defaults to as a knob.

### 3.3 CLAUDE.md rows naming a flag the code does not have

Every `OMR_*`/`MAESTRO_*`-shaped identifier anywhere in CLAUDE.md (44 distinct spellings) was checked against the 61 flags this document's code scan found a real `os.environ.get`/`os.getenv` call site for. **Positive control: 1 of 44** CLAUDE.md-only names found: `OMR_X` — CLAUDE.md's own generic placeholder name in an illustrative example table ("set `OMR_X`"), not a documented-but-unimplemented flag. **This is the one place this exercise did not find drift**: CLAUDE.md has never invented or left behind a phantom flag name, which is notable given how often its own text records the opposite failure (a flag's *behaviour* being described wrong).

### 3.4 Flag defaults: code vs CLAUDE.md's stated default

**Checked every flag with both (a) a knob-table or explicit-default row in CLAUDE.md and (b) a resolvable default in code — 43 flags. Zero direction or default-value contradictions were found as of this tree (commit `29fa5ca4`, stamped at the top of this file).** This is a genuine, checked negative, not an assumption: CLAUDE.md explicitly records at least two occasions where its knobs table *was* wrong for a period (`OMR_METER_CARRY`/`OMR_METER_FROM_BARS` read `still off` for a day after they flipped ON on 2026-09-15; `OMR_SLOT_STITCH`'s docstring carried a refuted claim for three days) — both were corrected before this scan ran, and this document is what re-checks whether a third instance has crept in since. The disagreement that remains is **coverage**, not **direction**: see §3.2.

---

## 4. Numeric guards CLAUDE.md never discusses at all

**195 of 218** module-level numeric constants under `tools/omr/` never appear in CLAUDE.md under their own name. Most are geometric constants local to one detector (pixel margins, aspect-ratio cutoffs) that this document's mechanical scan cannot distinguish from a load-bearing decision floor without reading every one by hand — which is exactly the kind of hand-list this task was asked not to produce. The table in §2 lists every one found, with `not mentioned in CLAUDE.md` in the judgement column wherever that is the honest answer; do not read that column as "unimportant", only as "unrecorded".

---

## 5. How to regenerate this document

```bash
python3 benchmarks/omr-flags-map-2026-09/build_doc.py
```

This re-derives every mechanical fact fresh from the current tree (the flag/guard inventories, the presence-in-CLAUDE.md checks, and the allow/deny-list direction for the sites the existing test can see) and re-applies the same hand-authored annotations above. If a new flag or guard has been added since this file's timestamp and `ANNOTATIONS`/`GUARD_JUDGEMENTS` was not updated for it, it will show up as `UNANNOTATED` / `not mentioned in CLAUDE.md` rather than silently vanishing — the same fail-safe shape CLAUDE.md prescribes for the flags themselves. To see the raw JSON this is built from without the hand-authored layer:

```bash
python3 benchmarks/omr-flags-map-2026-09/derive_map.py
```

