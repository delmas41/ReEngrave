# Plan 2026-11-04 — page-wide claims name page strokes, before beams (ROADMAP 2.269)

STAGED. Design only, no code (Sonnet design agent, tree b9763a2d4; filed by the manager, citations spot-checked). Paths are under `tools/omr/staged/`; `g` = gather.py, `so` = adjudicators/stroke_owner.py. Sean, 2026-11-04: "read and claim once ... passed on to every subsequent view or cell cut"; "Don't add more work".

## 1. Today, per kind (all STAGED; LEGACY has none)
Layer numbers are `claim_order.py:84-96` (CLAUDE §3). "Frame" is what the claim names.

| kind (layer) | who claims, file:line | frame | read by |
|---|---|---|---|
| staff lines, residue (0) | The eraser takes the line; nothing claims the leftover. `claim_readout.py:325-331` counts it as `residue:horizontal/curve`. | none | nobody |
| barlines (1) | `gather_barline_claim` g:295 (called g:17462): area ±0.45 sp, page px, per cell. M1 carves each rule into a page stroke of kind `barline` (`page_strokes.carve_columns` :206); no claim names it. | cell area; page stroke unclaimed | `so._areas` :87 (centre in area, on CELL strokes) |
| brackets, braces (1) | `gather_page_claims` g:15957 (called g:17749): one row per mark per system, page px. Detector brace/bracket boxes: `family_of` gives None (`stroke_owner.py:120`). | system area | `so._areas` page-wide branch (wholly inside, +1 px) |
| clef, key, meter (2) | clef g:15273/:15648/:15742; key :15418/:15508; meter :14958 (called g:17730-17741), area claims in page px per cell. Clef also files cell-ordinal `unit: ink` rows (`_file_ink_claim` g:15117), which `so` never reads (it reads ink rows only for arcs :123, hairpins :142). | cell area | `so._areas`, centre rule |
| words, dynamics (3) | `gather_page_claims`: accepted direction words, bar numbers, dynamic runs, margin labels. Detector `dynamic*` boxes: tier 4 (`stroke_owner.py:75`) via `Q.GLYPH_STROKES` (g:8046). | system area; cell box | `so` |
| arcs (4) | `gather_arc_claim` g:15131; page ids in `page_strokes` (g:15196-15201, from arcs_system.py:955). Done in M3. | cell ordinals + page ids | `so._arc_claims` :113 reads cell ordinals; page ids read by the binder only |
| hairpins (4) | `gather_hairpin_claim` g:15207 (called g:17621), one row per (hairpin, staff); default ON (`hairpin_reach.py:36`; the g:15214 docstring saying OFF is stale). | cell ordinals | `so._hairpin_claims` :131 |
| repeats (10) | `gather_repeat_dots` g:14761, `gather_volta_brackets` g:14592 claim nothing; a `repeatDot` box is family `dot` (tier 4). | cell box | `so` |
| whole rests (5) | `restWhole` box tier 1 via `Q.GLYPH_STROKES`; unboxed ones found in ADJUDICATE by `so._found_whole_rests` :150. | cell box / page-px box | `so` |
| ledgers (6) | `ledgerLine` box, family `ledger`, tier 1. An unboxed ledger is claimed by nobody; `gather_ledger_ink` g:9076 is a witness, not a claim. | cell box | `so` |

**Order:** GATHER calls page map g:17557, arcs g:17576, hairpins g:17621, `gather_cv_lines` g:17626, clef/key/meter g:17730-17741, words/brackets g:17749. Binding order is `stroke_owner.TIERS` (:65), not call order. A page reader placed at g:17626 (M4a) runs before the clef/key/meter/word/bracket rows exist.

## 2. Cause and lesson
The claims were built before the page map; their ids are cell ordinals or area boxes, so a reader on the page map cannot ask "whose is this stroke?". M3 translated arcs only. The M4a crops show the result: slur, staff line, C clef, ledger, "cresc.", trill read as beams. **Lesson:** when a new frame arrives, every claim that sits before the new reader must be re-expressed in that frame first, or the reader refiles other marks' ink (the 2.260b lesson again: ask the claimed object).

## 3. The change
One new GATHER step, `gather_page_claim_names` (new `page_claim_names.py`), once per page, after `gather_page_claims` (g:17749). It reads rows already on the log and the in-memory `PageMap`; it reads no raster and adds no reading pass. For each existing claim it files a `Q.CLAIMED_AREA` row, `unit: ink`, `frame: page`, same owner, `page_strokes=[ids]`, `owner_row` = the source row, `source` = "page_names"; the area row stays. Claims apply in layer order, first claim wins; a later claim on a named stroke is recorded contested, never taken. Before building, grep for readers of `unit: ink` rows (only arcs/hairpins in `so` today); if anything else reads them, use a companion quantity.

Is translation enough?
- Barlines: yes (the carved `barline` stroke inside the area).
- Brackets, braces, clef, key, meter, words: yes -- apply `so._areas`'s own predicate to page-stroke boxes (wholly inside +1 px for page-wide claims, centre rule for cell claims). No re-read.
- Hairpins: yes -- the arms already read, a page-frame `on_arms_share`, as `arc_claim.page_strokes_along` :116 does for arcs; named once, not per staff.
- Whole rests found by 2.52: yes (page-px box, centre rule).
- Boxed ledgers, boxed whole rests, repeat dots: by ink share (`COVER_SHARE_MIN` 0.5) after a cheap bounding-box test.
- **Staff-line residue: NOT translation.** No claim exists; a position rule from fields already on the page-stroke row (level, line-thin, ends on the same line row at its own x, `PageStaff.lines_at`). Cut-offs not established. Never retrace lines (the 2.48 comb is rejected, page-facts §5).
- Unboxed ledger ink, trill extension lines, volta brackets, octave and pedal lines need a new read: not in this plan; they stay unclaimed and are counted (the trill crop is not fixed here).
- Heads, stems, accidentals: M6, not here.

**Cost (2.262):** strokes bucketed by staff and sorted by x; each claim bisects to its candidates; mask tests only after the cheap bounding-box test. Time on Brahms p5; check peak RSS (`PageMap` lives until g:17749).

## 4. Steps (smallest first)
- **Step 0, consumer only, no flag:** M4a reads the arcs' existing `Q.CLAIMED_AREA.page_strokes` (the slur crops). Count the slur-as-beam cases first.
- **Step 1, `OMR_PAGE_CLAIM_NAMES` (OFF):** barlines, brackets/braces, clef/key/meter, words/dynamics, hairpins -- one flag, one pass, one owner table, one order (C-clef and "cresc." crops).
- **Step 2, `OMR_PAGE_CLAIM_LINE_RESIDUE` (OFF):** the residue position rule, taking only strokes no layer 1-5 claim named. Separate because it is a new decision, not a translation.
- **Step 3, `OMR_PAGE_CLAIM_BOXES` (OFF):** boxed ledgers, whole rests, repeat dots by ink share -- only if M4a still files ledgers after 1-2.
- M4a's `gather_page_beams` moves to just after the naming step (file-only, export identical). M4b settles the g:17677 order (`gather_notehead_stem_cross_ink` needs the beam rows).

## 5. Gate (lean)
- Export byte-identical with each flag on.
- `claim_readout` / `claim_order` on Brahms p0+p5, Litolff p6+p16 before/after: identical (they re-adjudicate the CELL stroke owner and cannot see page ids -- a must-not-move control, not the gain).
- The gain is the M4a re-run: page beams with no old slab (Brahms 31, Litolff 74) fall. Report strokes named per step by owner and double-named.
- Manager looks at crops before any go to Sean. Timing and peak RSS on Brahms p5/p0. Fast tier.

## 6. Risks
- The page map re-cuts strokes (barline carve, joins): apply predicates to page boxes, never map cell ids to page ids.
- Wholly-inside leaves a stem crossing a word unnamed (intended; matches `so._areas`). A word box over a real head takes the ink (DECISIONS 2026-10-28), as today.
- Hairpin arms: name only reads that pass the 2.261 beam guard (`OMR_HAIRPIN_NOT_A_BEAM`).
- Residue rule could name a thin flat tie/slur remnant on a line: arcs name theirs first; the thickness cut stays below a beam's 0.5 sp. Sean's tiles already call such strokes "staff line" (DECISIONS 2026-10-30).
- Two ids for one claim during migration (plan-2026-11-03 §D): `so` keeps reading cell ordinals until a later step.
- Stale docstring g:15214 (hairpin claim "OFF"): fix in the Step 1 commit.
- No question for Sean: the residue question is answered by his "staff line" tile labels.
