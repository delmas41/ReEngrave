# 2.296 — A printed dynamic is claimed as a dynamic, not as a word (2026-11-11)

STAGED GATHER, flag `OMR_DYNAMIC_OWN_CLAIM` (`gather.gather_page_claims._file_compound`,
`claims.compound_dynamic_slots`, `claims.grow_to_ink`). Branch `lane-2.296-dynamics-not-words` 992938559.
Written by the manager from the lane report (the lane's Write was refused).

## Cause and process lesson
Mostly a NAME, not a claim. The register files a printed dynamic under owner `word` with source `dynamic_letters`;
`claim_readout` and `judged_claims` name a claim by its OWNER, so every dynamic's ink read as a word's. All five
Litolff p2 "contradictions" (2.295) stand on a READ `dynamic_letters` claim: the ink was already claimed once, for the
dynamic, and the exported file already wrote `<dynamics>`. Lesson: name a claim by the reader that filed it (its
`source`), never by an owner field shared by two readers — and never by the lexicon `category` (`cresc.` and `dim.`
are category `dynamic` too; a first rename keyed on category made Sean's "cr of cresc." a dynamic).
(The 2.295b lane had called the five "real, cell-settle word claims": true of the owner string, wrong about the mark.)

## Accounting or reading?
Accounting. Brahms p0: the file holds 14 `<dynamics><f/>` plus the words `legato`, `espr. e legato`, identical OFF
and ON. Litolff p2: the five tiles are written `<dynamics>` (f, f, sf, p), none as `<words>`. One reading difference,
not this lane's: 2.284b r1 #2 is written `f` where Sean reads `sf` (the detector boxed one wide `dynamicF`).

## Causes (flag OFF; Litolff p2, p8 + Brahms p0, p14)
- own dynamic claim, kind NAMED `word` — ink claimed once, correctly: 150
- marking words ("f legato", "p dolce"): the word's OCR box swallows the dynamic's letters, which then have no claim
  of their own: 16 of 23 marking words
- a false READ `fp` / `mp` over a word's letters (the detector boxed the `l` of `legato` as `dynamicP`): 9
- a GUESSED dynamic losing the settle: 0; in-staff vs between staves: not a cause.

## The fix (pipeline part)
A marking is word + dynamic. The dynamic is placed by the text's own order; the word's claim stops at the dynamic's
ink (reusing `hairpin_reach.word_area_sparing_heads`); the dynamic claims its own ink READ, grown to the ink touching
its tight detector box. It splits nothing it cannot place and nothing that would leave ink unclaimed
(`compound_not_split:<why>`, counted). Split: Brahms p0 8/8 markings, p14 7/12, Litolff p8 2/2, p2 0/1.
`claim_order` unchanged (words and dynamics are one layer).
The tool part: name a stroke-owner candidate `dynamic` when its claim row is owner `word` + `source ==
"dynamic_letters"` (`kind_patch.py` on the lane branch) — applied to `claim_readout` at landing.

## Measures (flag OFF vs ON)
- Exported file: NOTHING CHANGED on Litolff p2, p8 (1457 paired) or Brahms p0, p14 (1289 paired).
- Against Sean's Brahms p0 page-pass labels: his dynamic ink owned as `dynamic` 37.0% (as the tool stood) → 67.0%
  from naming alone → 100.0% with the flag ON; his 14 `f` owned as dynamic 14 of 14 ON (10 of 14 OFF). His word ink
  unchanged at 53.3%; the 28 word labels that were right stay right.
- All 20 registry dynamic tiles (Litolff p2, p4, p6, p9, p10) agree once named by `source`.
- Judged right→wrong 0 (186 Litolff, 210 Brahms). Fast tier 10212 passed; check 229; conservation holds.
- Flag OFF = main: 113,197 rows each on Litolff p2, p8, 0 different (a planted one-row edit reports exactly 1).
- 12 blind tiles for Sean: out/print-from-worktrees/2.296-r1/tiles (7 newly-dynamic, 3 words of split markings, 2
  controls). In tile 8 the dynamic also takes the `g` of `legato` — a stroke poking out of the word's OCR box falls to
  the cell-level dynamic box; on main too.

## The 38% of Sean's word ink held only by a GUESSED claim — a different cause, not fixed
Three labels: the title block, the composer and the plate number (142,087 px), filed `page_heading` GUESSED on
purpose by `claims.heading_blocks` since no reader reads them. The cure is a heading reader, not an order. The 6.6%
held by nobody is the tempo line "Un poco sostenuto" (Surya returned no reading; an unread candidate files no claim)
plus the numerals "3." "4.".

## Follow-ups (counts on the four pages)
1. 40 `twin_letters_disagree` runs: one ink boxed as both f and p, no claim at all (both candidates are dynamics, so
   the KIND follows) — needs Sean's tiles. 2. 21 `not_a_dynamic` runs unclaimed, plus Litolff's 19
   `all_ink_on_a_mark`. 3. Brahms p14: 5 of 12 markings not split (2 keep a false `mp`). 4. Heading text GUESSED;
   unread text candidates unclaimed.

## What went wrong along the way (process)
The lane's first readout cuts OVERWROTE two older slices of the same names
(`library/_shared-records/claim-readout-slices-litolff.off.gathered` / `.on.gathered`, dated 2026-11-02):
`cut_record` names a slice by the record's file name. Gathers that overlapped other lanes' starved the OCR
("worker silent for 20.0s", fallback to Tesseract) and produced 177 false differences; the final arms were gathered
one at a time with a longer per-crop deadline. It once started a third gather and once ran `pkill -f` on its own
script names.

## Not verified
Sean has judged none of the tiles; the compound reading (the text's order places the dynamic) is his to confirm.
Brahms OFF was not compared row-for-row with a main-code gather (the first was OCR-starved).

## LANDED ON 2026-11-11 (land-2.296 088719bdb)
Sean, going to bed: "Land what you can overnight and start working on the next steps when you can."
`OMR_DYNAMIC_OWN_CLAIM` default ON (`=0` opts out; still needs the page-wide words pass). The tool naming fix is
`claim_readout.named_owner` (owner `word` + source `dynamic_letters` -> `dynamic`), used by `owner_verdicts`,
`area_claims_fine` and `page_stroke_claims`, so `judged_claims` shares it. Real-tile test:
`tools/omr/tests/test_dynamic_naming_real_2_296.py` (slow; Sean's five dynamic tiles read dynamic, "cr of cresc."
stays a word). Fast tier on the landing tree 10,319 passed; check 228; conservation holds; export byte-identical for
the tool fix. No gather was run at landing: the "file unchanged, 14 of 14" evidence is the lane's.

`judged_claims` on the saved Litolff main slice: 28 agree / 6 contradict -> 32 / 2. FOUR of the five dynamic tiles now
agree; the fifth (2.284b r2 #2, `sf`) still CONTRADICTS as claimed twice — the dynamic owns 76% and a beam (27%) and a
stem (11%) also stand on its ink, at the tool's 0.3 cut. The other remaining Litolff contradiction is the tremolo
slash 2.276 r2 #4. (The lane's "5 -> 0" was on its own slices.)

Retired at landing: NOTHING. Every candidate is still reachable with the flag ON (a marking the split cannot place
stays one word claim): `gather.gather_page_claims`' `lone_letter_inside_a_claim` guard and `claims.spell_letter_runs`
go only when the flag itself is removed.

## 2.301 — dynamics hold their own ink only (2026-11-11), built, waiting on Sean's tiles

Written by the manager from the lane's report. Branch
`lane-2.301-dynamics-own-ink-only` 99e780117. From Sean's 2.296 r1 tiles
(`answers/answers-2.296-r1.json`).

**Causes**
- (a) `fp` where the page has p (tiles 2, 4): the detector boxed one p twice
  (`dynamicP` and `dynamicF`); `gather._file_compound` filed the joined twin
  letters as `detector_letter`. The split had already chosen p
  (`dynamic_token`); nothing reads `detector_letter`, so `fp` never reached
  the MusicXML. Fixed with no flag: the label is the slot's own token.
- (b) the g of "legato" in an f claim (tile 8): the stroke owner gives a
  page-wide claim only strokes wholly inside its box (+1 px,
  `stroke_owner._areas`); the g's stroke box ends 0.5 px outside, so it fell
  to a detector `dynamicF` box drawn on the g. Fix behind
  `OMR_WORD_OWNS_ITS_INK` (default OFF): `claims.edge_ink_boxes` files the
  word's own edge letters as slack-padded rectangles (0.1 sp), skipping
  anything overlapping a note-family box, an earlier claim, the marking's own
  dynamic, or a staff-line-like piece.
- (c) "sempre" blue on the più tile (tile 3): NOT a claim fault — it is the
  sibling word piece of the same marking; the tile boxed one piece only.

**Lessons:** a split part's label comes from its own slot, never the
detector's raw spelling; a tile boxes every piece of a claim. A first padded
box took a flat's stem and was caught by a control built from real tile-7
pixels (rule 7 held).

**Measured** (OFF vs ON, real gathers, Litolff p8, Brahms p0, p14)
- Exported file: nothing changed (699 / 1289 paired); red bars 0->0, 24->24.
- Ink that changes kind ON: Brahms p0 two g's dynamic -> word, an unclaimed
  o (legato) and e (pesante) -> word; Litolff p8 the accent of più (40 px)
  mark -> word; nothing leaves word.
- judged right->wrong 0 (141 / 210); check 228; fast tier 10,330 passed, 0 failed.
- 12 real-pixel controls: 6 fail on main, 12 pass.

**Not done:** `claim_readout ink` lines not captured; `judged_claims` on
Litolff p8 only (10 agree, 0 contradict). A barline stroke tinted as word
inside a "sempre più" (its tile 9) is a separate, older over-claim, unexamined.
