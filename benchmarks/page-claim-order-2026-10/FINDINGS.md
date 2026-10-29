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
