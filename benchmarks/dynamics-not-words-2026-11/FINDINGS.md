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

## 2.303 — letters inside a printed word are the word's (2026-11-11), built OFF, waiting on Sean's tiles

Written by the manager from the lane's report. Branch
`lane-2.303-letters-inside-a-word` 25bab2ce9, flag `OMR_LETTERS_ARE_THE_WORD`
default OFF. From Sean's 2.301 r1 tile 4 ("it boxes MP, but it's actually a
part of the word sempre").

**Cause (Part 1, the unread word — NOT fixed)**
- A false `<dynamics><mp/>` DOES reach the exported MusicXML: Litolff p8, P2
  m12 and P3 m12, the m+p of "sempre" in "sempre più p".
- The OCR candidate [1510,787,1718,822] read `sempre piu: °` — the right
  letters plus a colon and a degree sign. `direction_lexicon._prepare` accepts
  only letters, spaces and periods and refuses the whole string. Other
  readings of the same marking on the page are garbled italic (`npre pin p`,
  `Rempression`, `S2mpre Pir.`); 3 of ~9 staves with it were read.
- ADJUDICATE's "letter of a known word" rule (2.68, 2026-10-09) acts only on
  READ words; Sean's convention of that day ("surrounded by letters, the word
  decides") was never built for a word the lexicon refused. A neighbour-gap
  cut cannot stand in: the real final p sits 0.19-0.57 sp from "più" here.
- About 14 dynamic claims on Litolff p8 sit inside REFUSED candidates, nearly
  all letters of sempre/più; Brahms 2, both real p.
- Only 2 of 149 refusals on Litolff p8 would be rescued by trimming end
  debris. The lexicon gate is load-bearing and was not touched.

**Lesson:** the record keeps only a page-level `rejected` list, so what the
OCR said per candidate is invisible; a refusal needs its own text and box on
its row.

**Proposals for Part 1 (none built; need Sean):** (1) record each refused
candidate's text on its abstention row; (2) build "surrounded by letters" for
refused words; (3) a sibling staff's READ marking at the same x in the same
system as a second witness (a different source: another staff's ink);
(4) if the mp must go, mark it UNREAD, never silently drop or read it.

**Part 2, built (flag OFF):** `claims.letters_of_the_word`, in
`gather.gather_page_claims`. A run's letters are the word's only if every
letter box lies inside the READ word's box, the run's centre along the text
is outside every dynamic token (+1 character), and the CV reader measured
letter ink beside the run; restricted to runs the OFF arm filed as a READ
dynamic. Of the 11 candidates 2.301 counted: 8 removed, 1 real leading f kept
("f espr. e legato"), 2 mixed runs kept (a word letter + the real final p:
a 2.296 follow-up). Brahms p4 adds 3 removals. 11 removed in all.

**Measured** (OFF vs ON, real gathers: Litolff p8; Brahms p0, p14, p4)
- Exported file BYTE-IDENTICAL: the removals do not reach the file (2.68
  already kept those out at ADJUDICATE). Part 2 moves ink ownership only.
- judged right->wrong 0; judged_claims no new contradiction; the 24 judged
  2.296/2.301 tiles agree both ways except 2.301 tile 4 (Part 1, unsolved).
- check 228; fast tier 10,452 passed, 0 failed, flag OFF and ON.

**Not confirmed:** cut-offs rest on three pages of two plates; the 2.296 r1
and 2.301 r1 answers are not registered in `judged_claims` SOURCES (replayed
by the lane's own script); slices `claim-readout-slices-*-base/-on/-on2`
were left in `library/_shared-records`.

## 2.303 Part 1 r1 (2026-11-11) -- unread word, sibling witness; built OFF, NOT ready

Branch `lane-2.303-p1-unread-word-sibling` 0f73e5c99, flag `OMR_UNREAD_WORD_SIBLING`
default OFF. Agent's report; none of its 36 changed places is judged by Sean.

- **Cause:** on Litolff p8 staves 0-3 the word "sempre più p" is crossed by a
  BARLINE. The text reader's crop kept that stroke, read `sempre piu: °`, and
  `direction_lexicon._prepare` refused it. Staff 8 prints the same word clear of
  the barline and it was READ. The detector's m+p inside the unread line then
  became a dynamic.
- **Process lesson:** the barline's ink is claimed on the page-wide pass before
  words, but the text reader is still handed the raw crop with that ink in it.
  A reader should not be shown ink another reader already owns. The source fix
  is the crop, not a witness downstream (not built; proposed to Sean).
- **Built:** refused windows on one staff merge into a line (>= 2 detector
  letters, >= 4 median letter widths); a READ word at the same x-extent on a
  sibling staff makes it that word, GUESSED; otherwise red `unread text`;
  letters inside the line with ink on both sides are not written as a dynamic.
- **Measures (frozen sample, re-adjudicated, flag OFF vs ON):** Litolff dynamics
  +5 -7, words +7 -3; Brahms dynamics +5 -3, words +8 -2; notes and red bars
  unchanged. Judged right->wrong 0. Fast tier flag ON 10,462 passed, 0 failed;
  check 228. The saved night record does not reproduce under either arm (older
  code), equally OFF and ON.
- **Known faults (agent's own):** Brahms p0 staff 10 loses `ff`, gains `f` + a red
  mark; Litolff p8 P2 bar 12 still gets a stray `dyn.` and `pp`; a final `p`
  outside the unread window is written twice (blue in the word, plain as the
  dynamic).
- Tiles (not sent): `out/print-from-worktrees/2.303-p1-r1/` (12 of 15 changed
  lines; they box the whole line).

## 2.304 r1 (2026-11-12) -- the text reader not shown owned ink: built OFF, NEGATIVE, not to land

Branch `lane-2.304-text-reader-owned-ink` 3f557db7c, flag `OMR_TEXT_CROP_OWNED_INK`
default OFF (`tools/omr/staged/owned_ink.py`, `direction_text._without_owned_ink`).
Agent's report; its tiles are not judged.

- **Cause, corrected:** the 2.303 hypothesis (a barline left in the crop) is only
  part of it. On Litolff p8 the `p` of sempre and the `i` of più STAND ON the
  barline: letter and rule share pixels, so no ownership mask can split them.
  Whiting the rule inside the word took the `i`, and the lexicon then accepted
  `sempre p` for the printed `sempre più p` -- a wrong READ.
- **Process lesson:** "is the owned ink there" does not discriminate. A mask is
  safe only OUTSIDE the candidate's own box; where two marks share pixels the
  reader has to read through the crossing, not have it removed. And the earlier
  2.254 r3 retry had already whited lines on most refused windows (164 of 190
  Litolff, 119 of 124 Brahms) -- the prior work should have been in the brief.
- **Step 0** (Litolff 8 pages, Brahms 4): windows whose crop carries an earlier
  owner's ink -- Litolff 48 of 71 READ, 154 of 190 REFUSED; Brahms 54 of 80 READ,
  91 of 124 REFUSED. READ words carry it as often as refused ones.
- **Measures, flag ON vs OFF, same tree:** Litolff dynamics +2 -1, words +11 -9;
  Brahms dynamics -2 (two `p` lost), words +8 -8. READ words 69 -> 69 and
  77 -> 77 (as many lost as gained; one gain a wrong `min.`). Judged
  right->wrong 0. The false `mp` at Litolff p8 P2/P3 m12 is STILL written in
  every arm. Fast tier flag ON was not re-run whole after the lane's fixes.
- **Verdict:** no gain, new wrong reads. Stays OFF; candidate for removal.
  The cause case goes back to 2.303 part 1 (unread line: sibling witness, and
  no dynamic from letters inside an unread line).
- Also seen, not judged: the OFF arm READS `sempre p` for a printed `sempre più`
  at Litolff p8 staff 3 bar 11.

## 2.303 Part 1 r2 (2026-11-12) -- Sean's tiles 14 of 15; not landed

Branch `lane-2.303-p1-unread-word-sibling` b035325ba (+ tile script), flag OFF.
- **Causes found in r2:** the "lost ff" (Brahms p0 staff 10) was never READ -- a
  guess from the run `f`+`m`+`p` (f, then the m,p of "espr."); siblings that
  differ only by an end dynamic token were called disagreeing; the two boxes of
  one printed `m` were judged separately; a tempo heading (printed once per
  system) was used as a sibling. All four fixed with real-row controls (13).
- **File change OFF vs ON (38 places):** Litolff dynamics +4 -13, words +7 -4;
  Brahms dynamics +3 -5, words +8 -2. Judged right->wrong 0. Check 228. Fast
  tier flag ON 10,593 passed, 1 failed (stale flag-doc rows, fixed; whole suite
  NOT re-run).
- **Sean's 15 tiles:** every removed dynamic he saw is letters of a word; both
  kept dynamics are dynamics; both guessed words are right. Tile 9 (Brahms p4
  staff 10 bar 0): the p of "pesante" goes mp -> an unnamed dynamic; should be
  nothing.
- **Process lesson:** the agent called six removals "lost READ dynamics"; the
  three it named were each letters of a word on Sean's tiles. A dynamic made of
  letters inside a word was never a read.
- The word is written without its dynamic token ("sempre più"), the p stays the
  dynamic reader's; they are two directions (pairing for a guessed word not wired).
- Open: tile 9; 23 changed places unjudged; Brahms red `unread text` marks with
  no sibling (as designed, not judged).
