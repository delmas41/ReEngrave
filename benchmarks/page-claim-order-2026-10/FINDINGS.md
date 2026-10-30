# 2.221 milestones 0 and 0b: census of the ink a page-wide claim order could change

STAGED, read-only. No flag, no gather, no change in `tools/`. Scripts: `census.py` (extract, count), `tiles.py` (crosstab, tiles).
Commands: `python3 benchmarks/page-claim-order-2026-10/census.py extract|count`, then `tiles.py crosstab|tiles`. Raw output: `census.json`, `crosstab.json`.

**Cause and process lesson.** Heads take ink first because no step ever wrote down who owns a column or a letter before the head box was drawn.
Old pair rules (`too_narrow`, `on_a_dynamic_letter`, `claimed_by:*`) then refuse most of the damage downstream, so on the exported file the
leak is small and the old rules are what hide it. Lesson: a head-box overlap count is not a measurement of theft. The shifted-region control
below shows chance overlap is as large as the real count for letters, so only Sean's tiles can say how many are real notes.

## Inputs
Frozen sample pages (`benchmarks/lane-report/sample.json`), saved gathered records of the 2.202f lane, ON arm (beams ON = main defaults):
`.../2-202-beams-cause-1f79a5/out/lane-report/2.202f/work/{litolff,brahms}.on.gathered.record.json` and the `.on.symbols.json` / `.on.musicxml`
EXPORT wrote from them. Pages: Litolff 2,4,6,8,9,10,11,16; Brahms 0,4,5,8,12,14,19,25. Written notes are matched to head boxes by place
(page + glyph key + box agreement; 0 unmatched). Share = dark pixels of the head box inside the region / its dark pixels, staff-line rows removed
(pipeline binarisation, 600 dpi). Not re-adjudicated: the record as saved, not a fresh run.

Populations: P_boxes (every detector head box) / P_live (still a notehead after ADJUDICATE) / P_written (head boxes written as a note).
Litolff 5796 / 4957 / 3739 distinct boxes (3898 notes in the file); Brahms 7015 / 5622 / 4430 (4441 notes).

## Counts, share >= 0.5 of the head's ink (">=0.25" in brackets). Format boxes / live / written
| region (reader that gave the geometry) | Litolff | Brahms |
|---|---|---|
| (a) interior barline column (`measure_extractor` cell edges, kept where the unerased raster shows a full-height rule) | 27 / 2 / **2** (51/21/15) | 565 / 0 / **0** (575/1/1) |
| (b) spelled-dynamic letters (detector `dynamic*` boxes used by the decided `dynamic` verdict) | 64 / 15 / **8** (80/24/14) | 28 / 1 / **0** (33/4/0) |
| (b) accepted direction word (surya/tesseract `direction_word` boxes) | 6 / 0 / **0** | 14 / 4 / **1** |
| (c) detector `brace` box (22 / 11 boxes) | 0 / 0 / **0** | 0 / 0 / **0** |
| (c) `bracket_reader.strokes_at_left_edge` (no consumer today; run as a measurement) | 2 / 0 / **0** | 6 / 1 / **0** |
| (c) PROXY: system left-edge region (staff start -9 sp .. +0.5 sp), NOT a bracket reader | 7 / 0 / **0** | 35 / 0 / **0** |
| (d) READ clef/key/meter/leading-column claim areas (`claimed_area`, owner's own box excluded) | 48 / 1 / **0** (49/1/1) | 111 / 8 / **0** (111/8/0) |

Read: on the exported file the order could move 2 (a) and 8-9 (b) written notes in Litolff, 1 (b) in Brahms, none for brackets, braces or
clef/key/meter: about 0.3% of written notes. In the boxes column the numbers are large (Brahms 565 barline boxes) but ADJUDICATE already
refuses nearly all (`crosstab.json`: Brahms (a) 553 `too_narrow` + 12 `clipped_fragment`; Litolff (b) `on_a_dynamic_letter` 29; (c)/(d)
`claimed_by:*`). So layers 1-2 would mostly retire old rules, not add notes. Plan §7 gate: (a)+(b) are near zero on the file.
Brackets (1b) show nothing: detector brace boxes touch no head; the bracket reader's rule strokes (4 to 23 per page, incl. the systemic barline) touch one live Brahms box.

## Controls (can fail)
- Nonzero where it must be: the old rules' own refusals are found (Brahms (a) 565 boxes; Litolff (b) 29 `on_a_dynamic_letter`; 24+13 `claimed_by:clef/key`).
- Shifted-region controls. Barline columns moved 3 sp right: written >=0.5 = 0 / 0 but >=0.25 = 343 / 371, so 0.25 is noise and 0.5 is used; control boxes >=0.5 are 6 / 1 vs real 27 / 565. PASSES.
  Spelled-letter boxes moved 4 sp right: written >=0.5 = **23 (Litolff) / 4 (Brahms)** vs real 8 / 0; >=0.9 = 10 vs 7. **FAILS: the letter overlap count is at or below chance.** A letter box lands on some real head wherever it sits, so the count does not show ink theft; the tiles must.

## 0b: ink shared by accidental / rest / dot boxes and WRITTEN head boxes (only this can change with the order)
Net dark pixels in the box intersection. Written heads touched: Litolff 20 accidental, 4 live-rest, 1 live-dot of 3739 (0.7%); Brahms 28, 4, 2 of 4430 (0.8%).
- accidental (all unrefused): Litolff 31 box pairs, 24 share ink, 14 share >=10% of the head's ink, 1489 px; Brahms 38 / 33 / 22 / 11587 px. Share of head ink: median 6% / 13%, upper quartile 23% / 67%, max 100%.
- rest (unrefused boxes): 4 pairs per plate, shares 21-87% (Litolff), 0-93% (Brahms). Refused rest boxes (68, 72 pairs) take nothing.
- dot (decided role): 1 and 2 pairs, 8-23% of the head's ink.
Small (about 0.5-0.8% of written heads) but not zero, with large tails (some heads are mostly accidental or rest ink). Convention (after the heads) stands unless Sean's 4 tiles say otherwise.

## Tiles
`out/print/2.221-census/` (12 tiles, `tiles/sheet.png`, `key.json` outside `tiles/`, `tiles/README.md`): 5 (b) letters written >=0.5, 1 (b) word, 2 (a) barline written >=0.5, 2 accidental, 1 unrefused rest, 1 dot (orange box = head, or head + the other box for 0b). Seed 2221. No control tiles. Not yet shown to Sean; nothing recorded.

## Not measured
- Brackets proper: no reader feeds the record; (c) is the test-only bracket reader plus a labelled proxy.
- Shared ink is a candidate pool, not ownership (a sharp touching a head cannot be split by this raster).
- Word ink under head boxes the detector never drew (milestone 6) is invisible here.
- Not re-adjudicated: a 2.202f gather, not a baseline re-run after today's 2.220 work.

## Sean's 12 census tiles (2026-10-28)
7 real notes (1, 3, 5, 7, 8, 9, 11), 3 not notes (2 and 12 naturals; 10 part of an ff), 2 oversized boxes (4: two heads a third apart + a natural; 6: several half heads, the "rest" partner was not a rest).
- Dynamic-letter group (1, 3, 5, 8, 10): 1 of 5 is ink taken from a dynamic (the ff). The other 4 are real notes beside letters: the letter overlap count is mostly chance, as its shifted control said.
- Barline group (2, 12): 0 of 2 are barline ink; both are NATURALS written as notes. The culprit is accidentals, not barlines.
- 0b (4, 6, 7, 11): 2 real notes, 2 boxes spanning more than one head.
- Lesson: the junk written as notes on this sample is ff letters and naturals; layer-order alone would not catch the naturals (they claim after heads, Sean q1), the one-head check (2.220 fix A) must.

## Barlines the census missed? (read-only, 2026-10-28; `barlines.py measure|tiles`, output `barlines.json`)

**Cause and process lesson.** The 5 "barlines written as quarters" are not in the file. All five are boxes ADJUDICATE already refused `too_narrow` in the saved record (decided, `notehead_is_not_a_notehead`), and no exported note sits within 1 sp of any of them (tile 11 has an eighth 1.5 sp away). The m1 sample was drawn from boxes with a decided `duration` (written = quarter), and a refused box still carries a duration verdict, so "written" meant "has a duration verdict", not "was exported". Of Sean's 12 m1 tiles only 2 (tiles 1, 8: both real quarters) are live boxes; 10 are refused (5 `too_narrow`, 2 `clipped_fragment`, 2 `stacked_head_duplicate`, 1 more `too_narrow` that was a rest). So the census (exported file) and Sean (refused boxes) did not measure the same population. Lesson: a sample is named by the population it was drawn from, and "written" must be matched against the exported file, not a verdict.

1. Per tile (all Brahms; all 0.25-0.74 sp wide; `barlines.json` "tiles"). Tiles 2, 4, 12 (p14) and 5 (p5): refused `too_narrow`, nearest census cell edge 0.13-0.18 sp away (3.4-4.8 px), band present, direct rule share 0.98-1.0. Census share 1.0 for 2, 4, 12 (they ARE in the census "boxes" column, 530 of Brahms 7015 at >=0.5), but not "written" because refused. Tile 5: census share 0.0, the box ends exactly on the cell edge (4342.0) so the band intersection is empty (1 px misalignment); direct 0.975. Tile 11 (p5): box lies right of the barline (edge 0.47 sp away), census 0.17, direct 0.41; also refused. Reason census did not count them as written notes: refused, so not exported.
2. Direct measure (rules found from the unerased raster: columns >=90% dark over the whole staff, width <=0.8 sp; head on a rule = >=50% of its net ink in them), WRITTEN notes on the 16 census pages: Brahms 0 / 4430 (controls +3 sp, -3 sp: 0, 0). Litolff 12 / 3739 (controls 7, 9): FAILS its control, these are heads with long stems, not barlines. m1 pages only: Litolff 6/1156 (controls 5, 3); Brahms 0/1243. Where the measure works: all Brahms boxes 816 on a rule (controls 19, 49), 730 of them `too_narrow`; decided-duration refused boxes on m1 pages 165 of 254 (controls 5, 15). So barline-as-note exists in the detector's boxes (hundreds) and is already refused; none survives into the file on Brahms. Litolff: no separation from stems, so no claim.
3. Floor: `tools/omr/staged/adjudicators/notehead_precision.py:151-152` (`TOO_NARROW_MIN_SPACES = 1.0`, class prefix `noteheadblack`), applied `:654-662` (`_too_narrow`) and `:3774-3783`. The 5 boxes are 0.25, 0.31, 0.25, 0.69, 0.35 sp wide and 0.63-0.74 tall; they did not pass: they were refused, and the m1 reader ran on refused boxes. The floor reaches `noteheadBlack*` only: written Half/Whole boxes under 1.0 sp: Brahms 1 (a half), Litolff 0. No upper limit on a written box; `PLAUSIBLE_HEAD_WIDTH_SPACES = (0.8, 2.1)` (`:2360`) feeds only the duplicate/stack rules. `on_a_barline` (`:3793`, `ownership.py:5491`) fires only for dot-sized marks.
4. Written notes, width x height in own staff spaces. Litolff n 3739: width median 1.47 (p5 1.31, p95 1.74, max 4.69), height median 1.32 (p5 1.04, p95 1.58, max 6.96); outside 1.0-1.9 wide: 54 (all over); outside 0.9-1.8 tall: 42 under, 69 over; either: 146 (3.9%). Brahms n 4430: width median 1.40 (p95 1.57, max 5.84), height median 1.20 (p95 1.30, max 3.16); wide: 1 under, 5 over; tall: 37 under, 9 over; either: 49 (1.1%). m1 pages: 52 / 1156 and 17 / 1243. The outliers are the stem-boxes and merged boxes (e.g. 1.43 x 6.96) Sean saw in tiles 6, 7.

Tiles: `out/print/2.221-barlines/` (10 tiles: every Litolff written note with direct share >=0.5 that the census did not count; Brahms has none). Expect most to be stems; they test whether the direct measure means anything. Not yet shown to Sean.

## m1/m1b page-wide (2026-10-29)

STAGED GATHER (claim) + ADJUDICATE (consult). Branch `lane-2.221-m1-pagewide`. Flags `OMR_CLAIM_WORDS_FIRST`, `OMR_CLAIM_BRACKETS_FIRST`, OFF.

**Cause and process lesson.** Words and brackets claim nothing today, so a head box on their ink is refused only later by pair rules (`on_a_dynamic_letter`, `too_narrow`, `claimed_by:leading_column`), or not at all. The parked m1 build (lane-2.221-m1) filed one claim per CELL, so one "cresc." across a barline became pieces. Sean then ruled that words and dynamics are read system- or page-wide, and that no reading pass may be added per symbol. Lesson: a claim is bookkeeping on rows GATHER already files. Its scope is the mark, not the cell. So it is ONE row per mark on its SYSTEM, built from existing reader rows. The bracket claim takes the page-wide pass's rule strokes as input (`edge_strokes`), so nothing scans twice.

**Prior work.** `docs/ink-rules.md` rows: "ink is a dynamic letter" (`on_a_dynamic_letter`, 2.107, C), "rest on a dynamic letter", "box is a dot / a barline" (`on_a_barline`), and "dot on a barline". Benchmarks: `omr-direction-text-2026-09`, `omr-staged-direction-2026-09`, `omr-lexicon-2026-09`, `omr-dynamics-{band,coupling,staged}-2026-09`, `omr-margin-labels-*`, `omr-bracket-{reading,stability}-2026-09`. Page facts: a word between braced staves names every staff in the brace; a brace alone names nothing; reading the brace is a named gap. Memory: the lexicon gate is load-bearing and is never loosened (the claim reads only ACCEPTED words); margin-label lexicon. m0 census above: about 0.3% of written notes are on word ink, and none on brackets.

**What was kept and what was rewritten from the parked build** (07ac8ca73, its diff reviewed line by line). Kept: owners `word` / `bracket`, flags, the consult branch (READ refuses; a stemmed head NARROWS blue), the literal refusal and narrowing reasons, export not-a-gap reasons, and margins. Rewritten: the per-cell `gather_word_bracket_claims` is now `gather_page_claims`. It files one row per mark on `R.system`, with `scope: system` and `cell: None`, and merges `boxes_inside` across the cells the mark meets. It drops the per-cell stroke `ink` rows. Added:
- dynamics from the detector's `Q.DYNAMIC_LETTER` rows, joined by `claims.spell_letter_runs` (READ only for 2+ letters spelling a dynamic);
- printed bar numbers;
- detector `brace`/`bracket` boxes at the system's left edge (a curved brace is no rule, so the edge scan misses it);
- `stroke_owner._areas`: a page-wide claim owns only strokes WHOLLY inside it, so a stem through a word's box keeps its ink.

Tests: 29 in `test_staged_page_claims_2_221.py`. Fast tier: 9302 passed, with 1 index test made current by `judged build`. Check: 198.

**Capture** (`m1_pagewide.py count`; `m1-pagewide.json`). Subset `m1-pagewide-sample.json`: Litolff p1, p4 and Brahms p0, p5. Run with `--from gather --workers 1`. Claims per page:

| page | words | dynamics (2+ letters) | bar numbers | bracket rules | detector braces | lone letters (not claimed) |
|---|---|---|---|---|---|---|
| Litolff p1 | 3 | 0 | 0 | 1 | 0 | 11 |
| Litolff p4 | 10 | 1 | 1 | 2 | 4 | 24 |
| Brahms p0 | 10 | 1 | 0 | 2 | 0 | 41 |
| Brahms p5 | 7 | 2 | 0 | 10 | 0 | 18 |

Head boxes holding >= 0.5 of their ink inside a claim: Litolff 11, Brahms 60 (most on Brahms p0 words). The consult fired `claimed_by:bracket` 8 times per plate (these replace 8 `claimed_by:leading_column` refusals) and `claim_narrowed:word` once (Brahms). It fired `claimed_by:word` 0 times, because earlier rules already refuse those boxes.

Brahms p0 against hand truth (classes `text` / `dynamic*` / `brace`; a claim matches when it covers >= half of either box):
- 60 truth marks; 17 claimed (dynamicF 8, text 7, dynamicP 1, brace 1); 43 unclaimed; 1 claim matches no truth mark (an edge rule overlapping two truth braces at 0.34/0.43).
- Unclaimed text (25): the title block and composer line, which no system reader reads; instrument names (`Q.MARGIN_LABEL` rows carry no box); and "espr. e legato" and "un poco sostenuto" where the word reader filed no accepted row.
- Unclaimed dynamicF (8): lone `f` letters. One detector letter is the detector's word alone, so it is not READ.
- Unclaimed braces (10): the brackets at x 1220-1260 are thick, so the edge scan returns no rule for them, and the detector drew no brace box on this page.

**File** (lane_report, subset, OFF vs ON): NOTHING CHANGED on either plate. Judged right->wrong 0, unwritten->wrong 0, invented->removed 0 (166 + 218 judged tiles on these pages). That is expected for a claim: the ink is now accounted once, by the claim instead of by the old pair rules.

**The tempo mark (Litolff p1 "Allegro con brio" + metronome).** The tempo note is detector box `glyph/1/0/0/3/1` (`noteheadHalfInSpace`, page px 1228,1078-1253,1101). It is written plain as a half G6 in bar 4. NOT CLAIMABLE from existing rows:
- the accepted word's box ends at x 1200;
- no direction candidate (accepted or refused) is filed to its right;
- the lexicon refuses digits (`direction_lexicon._prepare`);
- refused OCR texts reach the record only as a page count (`page_n_rejected_by_lexicon`);
- `_blank_detections` erases the head box before OCR.

A claim needs the word reader to keep the metronome candidate and file its text. That is in `direction_text` / `gather_direction_words`, fenced to lane-dedupe-passes, so it was not built.

**Not measured / open.**
- Lone dynamic letters (the most common dynamic: 41 detector letters on Brahms p0) do not claim. Whether a single `f`/`p` box outside the staves is READ is Sean's question (m0: letters were at chance next to real notes).
- Thick brackets need the page-wide pass's structure reader (barline lane).
- CV-only hairpins have no box, so their ink is unowned (out of scope).

**Tiles.** `out/print/2.221-m1-pagewide/` holds 12 blind tiles (`tiles/`, README with the question; `key.json` outside `tiles/`; seed 2221). They are 9 random claims, 1 claim matching no truth mark (only one exists, so the second slot went to a ninth random claim) and 2 unclaimed truth marks (a brace and a lone `f`). The orange box marks the claimed ink, or the truth mark for the unclaimed ones. Question: "Is this a word, dynamic, bracket or brace, or something else?" Not yet shown to Sean.
=======
## barlines system-wide (2026-10-29) -- 2.221 m2, LANDED ON (main 846efa623, OMR_BARLINE_SYSTEM_COLUMNS)
Written by the manager from the lane reports (subagent FINDINGS writes are refused). Branch lane-barlines-1029 (c1b47cef2 build, 3b9dbe7ca finish).

**Cause.** Barlines are read before GATHER: `pipeline.prepare_pages` -> `measure_extractor.detect_barlines` (:687), a per-staff scan plus a system vote. The vote used through-ink (a rule continuing through the gap between staves) only as a loose veto. So a per-staff majority kept stem alignments, and the blind `_drop_close_outliers` dropped the LEFT member of a close pair, which lost a real rule. Barlines claimed no ink, so their strokes were free for stem readers. Process lesson: the strongest witness, a rule running through the whole system ("especially since sometimes the barlines extend the length of the whole system", Sean), was being used as the weakest.

**m0** (fresh raster, frozen sample):
- Litolff 17 systems: 33 through-system / 251 through-group / 2 per-staff columns. Brahms 15 systems: 15 / 153 / 0.
- Litolff: false cuts at p6/1 x2559, p16/1 x921 and p9/1 x1526; missed real rule at p9/1 x1470 (all crop-confirmed); p8/0 x1679 ambiguous (abstains).
- Brahms: 0 faults.
- 4 of 17 Litolff systems are affected, about 10 red bars per wrong column.

**Fix** (the page-wide pass's structure reader, tools/omr/page_wide.py + measure_extractor `_system_barline_columns`, gated by `pws.staged_page_wide`; LEGACY callers unchanged: transcribe.py:4844, run_pipeline.py:73, visualize.py:140, staff_line_removal.py:317):
- through-ink first; the staff majority only where rules stop at each staff;
- tilt followed per staff: a Theil-Sen line through the voting staves, read at each gap's y. Litolff p6 x~2489 drifts 21 px top to bottom; fit vs rule centre <= 2.9 px; window +-8 px;
- barline ink claimed (stroke_owner TIERS `barline`, `gather_barline_claim`);
- one left-edge reader (`bracket_reader.read_brackets`; `left_edge_rules` deleted) telling brace from bracket by hook shape (braces 0.00-0.09 sp, brackets 0.70-1.27 sp), the whole mark top hook to bottom hook. The systemic barline is not yet emitted as a mark.

**Measures** (2 pages per plate, Litolff p6/p9, Brahms p5/p14, final code):
- cuts: exactly 3 removed, 1 added.
- Litolff: notes +10 -4, rests +3 -2, blue +5 -1, red marks 174 -> 153.
- Brahms: dynamics +1 -2, words +3 -1 (cause not run down).
- Judged right->wrong 0, unwritten->wrong 0, invented->removed 0.

**The lost notes:**
- 3 junk: the added barline read as a note, and 2 at the removed false cut.
- 1 re-read.
- 1 REAL quarter (Litolff p9 1734,2385; Sean: "There is a quarter note there but it is right next to a fermata over another quarter"). It was only ever a 0.074 stem-end detector rescue (`yolo_rescue_stem_head`), which the corrected crop (1470-1800 instead of 1526-1800) no longer re-finds. Not the barline claim (57 px away). Accepted by Sean; lane-stem-end-head reads the head from ink.

**Sean's tiles** (out/print/barlines-1029): 12/12. Tile 12 was a marker error on a tilted scan, not a reader error. Brace/bracket tiles (out/print/2.221-m1-pagewide): 3 and 6 are braces, 7 and 11 part of a bracket; the finisher re-reads these as brace and whole bracket.
>>>>>>> origin/main
