# 2.290 — Page heads on the ledger: round 1, measure + plan (2026-11-10)

STAGED, no code. Branch `lane-2.290-page-heads` 2c4868ca8. Plan: docs/plan-2026-11-10-page-heads-on-the-ledger.md.
Written by the manager from the lane report (the lane's own Write was refused by a hook). Scripts are on the lane branch named below.

## Cause and process lesson
M6 (page heads) sat OFF for five days because it was planned from a document, not the tree: it built its own twin
fold (IoU 0.5) while two other head identities were already ON — `Q.MARK_GROUP` (box IoU 0.3, 10-07; read by export
write-once, `export_unison`, `glyph_owner`, `rhythm`) and `Q.PAGE_MARK` (shared ink 0.5, 2.240, 10-31; read by the
page owner). They disagree: 3,402 Litolff boxes are 2,706 heads by one and 2,826 by the other (591 pairs joined by
both, 234 only by IoU, 57 only by ink). Lesson: re-brief a plan with grep on the tree before building it; and a
refusal count is not a loss count.

## The three OFF flags today
`OMR_PAGE_HEADS` (M6a): file-only, nothing reads `Q.PAGE_HEAD`; all three ON vs OFF on Litolff p2 changes no note and
no head-box fate. `OMR_PAGE_HEAD_VIEWS` (M6b): the only part with a wanted effect (far-head trigger by box OR ink
centre). `OMR_PAGE_HEAD_CLAIM` (M6c): now a translation of ids the 2.284 ledger links exactly; cost one judged
right→narrowed on 11-05.

## Sizing (saved GATHER rows replayed; pre-2.285 gather)
Litolff 3,402 boxes: 66.5% written, 18.8% copies of a head, 9.6% refused as non-heads. Brahms 1,737: 63% / 11.7% /
19.9%. Head ink with one owner 77% (Litolff p2+p10; 18% twin-claimed) and 91.5% (Brahms p0; 2% twin). Only 6 of 844
twin drops are true orphans: the twin zoo costs code, not notes.

## Sean's tiles (answers/answers-2.290-r1.json)
Every sampled head-box refusal is right (7/7: a beam, two tremolo slashes, a part of a note, a ledger line, barline
ink, a tall chord box); three written controls are notes; two real heads dropped as `owned_by_another_staff` (the
2.289 loss). **The lane's crop look said 10/10 boxes held by the tremolo claim were printed heads; Sean calls both
sampled ones tremolo slashes — the "16 heads lost to the tremolo claim" is NOT supported.**

## The three open cases and where the plan fixes them
Phantom `doubleWhole` over a beam (`stroke_owner.shape_fit` accepts a 2.12 x 0.56 sp beam piece as `head_lens`) →
step 6. The ff touching a head box (`hairpin_reach.word_area_sparing_heads` drops whole components touching a note
box) → step 5. `DYNAMIC_SPARES` by box not pixel → step 5.

## Plan (steps; each names what it retires — see the plan doc)
1 one identity (measure) · 2 one identity ON · 3 one position / far-head read per head · 4 one claim per head on the
ledger · 5 pixels where a head meets another claim · 6 refusals from ink · 7 ink-only heads (on Sean's yes).
Build of steps 1, 2, 4 started 2026-11-11 on `lane-2.290-build`.

## 2.290 build, round 2 (2026-11-11) — built OFF, waiting on Sean's tiles

Written by the manager from the lane's report. Branch `lane-2.290-build-r2`
df506a4b9 (flags OFF; the retire commit is NOT included). Sean's r1 tiles: 8
of 12 right (`answers/answers-2.290-build-r1.json`).

**Cause of the four wrong r1 claims**
- Tile 12 (a claim between two half notes a third apart): `page_heads.same_head`
  compared ink centres CLIPPED by each detector box; each box clips toward
  the other, the centres came out 0.53 sp apart and the two heads were called
  one. The file then wrote ONE note where two are printed.
- Tiles 8 and 10 (slivers): nothing checked that a claim is a whole head; a
  rim-of-a-hollow-head allowance (thin piece up to 1.6 sp) and a 0.3 sp
  minimum side let slivers through.
- Tile 9 (half a quarter rest): the detector boxed the rest as a notehead and
  never as a rest, so the rest reader (which claims first) had nothing to fire
  on; the head tier claimed rest pieces by shape. It also wrote a false
  quarter C3 (Litolff p11 m104).

**Process lesson:** an ink centre clipped by a detector box is a biased
witness; a claim must be checked against what ONE head can be; a lone box
whose claim is refused falls back to the old twin rule, never becomes a new
note. Also: `benchmarks/**/crops/` is gitignored, so r1's real-case controls
SKIPPED on a clean checkout — real-case pixels now live in a tracked
`real_cases/npz/`.

**What changed**
- Two head-sized boxes whose centres are >= 0.9 sp apart are never one head
  (`BOX_CENTRES_A_THIRD_SP`; the farthest true twin pair on five pages is 0.85).
- A head claim is refused whole and counted (`claim_size`) when a side is
  under 0.6 sp or it is taller than 1.5 sp. No width cut (a head fused to its
  ledger line is ~2.8 sp wide).
- A lone box refused for size is re-read by the old twin rule (removes the false C3).
- `ink_attachment` could NOT separate the rest from stacked chord heads (same
  contact, 2.4-2.5 sp): the remaining half of that quarter rest is still
  claimed by a head. Only reading rests from ink fixes it.

**Measured** (flags OFF vs ON, fresh arms; Litolff p2, 8, 11; Brahms p14, 19)
- Litolff file: notes +2 -5 (r1: +3 -6). All five lost are one pitch at one x
  written once instead of twice; all three gained are eighths Sean judged.
  Brahms: notes +1.
- Ink on the page ledger: Litolff 71.8 -> 76.5%, Brahms 65.8 -> 74.0%;
  one owner 89.5 -> 90.1 / 87.7 -> 88.4.
- 258 of ~2,400 r1 claims are now refused (192 too small, 52 too tall): that
  ink stays with the cell boxes. Only ~10 of them are on Sean's tiles.
- judged right->wrong 0 (203 / 173 scored); judged_claims no new
  contradiction; check 228; fast tier 10,412 passed, 0 failed.
- All 12 r1 tiles replayed on real pixels; 5 cases fail on the r1 code.

**Not confirmed:** the 0.9 / 0.6 / 1.5 cut-offs are measured on two plates
only. Known misses left for plan step 5: r1 tile 3 (an eighth fused with its
stem stub, unclaimed) and 2.289 tile 9 (unison half note, two thin rims, now
refused by design). Hazard: `claim_readout` slices are cached by file name
and one lane silently reused another's stale slice.

## 2.290 build, round 3 (2026-11-11) — built OFF, waiting on Sean's tiles

Written by the manager from the lane's report. Branch `lane-2.290-build-r3`
790595078 (flags OFF; no retire commit). Sean's r2 tiles:
`answers/answers-2.290-build-r2.json` (a unison lost; too-tall refusals were
real heads; too-small refusals right).

**Causes**
- Lost unison (Litolff p8 m69 half F5): the detector drew two boxes on one
  head; flags OFF they were two heads so two notes were written BY LUCK. With
  one head identity, the existing unison reader `stem_value._one_stem_per_head`
  abstained: it asks whether "another head" sits under the stems and counted
  the sibling box of the SAME head as that other head. Fix: that reader skips
  boxes of the same page head (`Q.MARK_GROUP`) when `OMR_PAGE_HEAD_ONE` is on.
  **Lesson: every reader that asks "another head" must know the one identity.**
- Too-tall refusals: the 1.5 sp cut judged head + whatever ink runs on (a fat
  stem's stubs, a stem root, the long side strokes of a hollow half). Raised
  to 2.0 sp; a stem-column exclusion was tried and dropped (it removed the
  sides of hollow heads). 1 of 52 too-tall refusals remains.
- The quarter rest (r1 tile 9) was caught by the 1.5 cut only by accident. New
  rule: two heads' claimed strokes touching with contact 0.9-1.7 sp are ONE
  ink the stroke map cut; both claims refused (tangent chord heads touch at
  2.2-2.5 sp, the rest pieces at 1.27).
- Tiles 4 and 12 "on the system below": the pipeline's owner staff was right
  (`glyph_owner`), the tile was centred on the cell's staff. Tile maker fixed.
- Boxes "a little small" (tiles 1, 2, 6): the CLAIM is short of the head
  (about 60%, 56%, 38% of the oval's dark pixels, staff-line pixels included):
  the hollow head's top rim fused with stem or ledger — plan step 5, not built.

**Lost notes re-checked from the rows:** p8 m69 unison (real loss, fixed);
p2 m4, p11 m86, p2 m7, p11 m107 fold-right (one stem); p2 m32 two heads a
third apart (fixed r2). New GAIN p11 m75 half C4: a unison the OFF arm writes
once — unjudged, tile 1 of the r3 sheet.

**Measured** (OFF vs ON, both arms re-made on the merged tree with 2.299 and
2.300 ON; Litolff p2, 8, 11; Brahms p14, 19)
- Litolff notes +3 -4 (r2 +2 -5), slurs +2, ties -2; Brahms notes +1.
- Ledger: Litolff 71.8 -> 76.8%, Brahms 65.8 -> 73.9%; one owner 89.5 -> 90.2 / 87.7 -> 88.4.
- Refusals: 215 (186 too small, 18 cut-through/moved, 1 too tall).
- judged right->wrong 0 (203 / 173); judged_claims no new contradiction; check 228.
- Fast tier 10,534 passed, 0 failed with flags OFF AND with both flags exported ON.
- Real-pixel controls: all 24 judged tiles (r1 + r2); 85 cases pass, 3 known xfails.

**Not confirmed:** cut-offs 2.0 sp / 0.9-1.7 sp contact measured on two plates;
the 18 cut-through refusals mostly unlooked; conservation tool not re-run
flags ON; ties -2 on Litolff not explained in the report.

## 2.290 landing gate (2026-11-11) — NOT landed; waiting on Sean's gate tiles

Written by the manager from the gate reports. Branch `land-2.290`: merge
ff2694d90, pitch fix b0d0d2298 + e601cb459, retire 2ada124ba, flip 6ea65de6e
(main untouched). Sean's r3 tiles: `answers/answers-2.290-build-r3.json`.

**Defect found at the gate (Litolff p2 m7):** a folded head was written with
its most CONFIDENT box's pitch (G3) where the head's hole sits at F3; the tie
bound to the dropped box was lost. Export inherited a detector score as a
position; tie ends on a dropped box were resolved only behind
`OMR_UNISON_TIE_VOICE` (off). Fix `export._settle_folded_pitches`: one
position per folded head from its hole / ink centre; where that does not name
one box's step the note is written GUESSED (blue) with all candidates; tie
ends resolve to the written box of their own staff. 8 folds on the five pages
have members that disagree in pitch (1 settled by ink, 6 written blue).

**Why "judged right->wrong 0" could not see it:** `judged` scores only tiles
that name a written note's value; Sean's r1 tile 6 ("most of a half note")
is a claim answer with no pitch. The build r1-r3 answers are NOT yet in the
`data/judged-claims` registry. A control sees only what its answers record.

**After the fix (five pages, fresh arms):** Litolff notes +3 -4, ties +10,
slurs +2, ONE pitch change (p8 m59 Ab3 -> A3, carried by a tie that now
exists), blue +6; Brahms notes +1, blue +2. The +10 ties are chains of tied
halves at p8 m58-59, p11 m78-83, m90-91 — UNJUDGED. judged right->wrong 0;
check 228; conservation holds flags ON (0 unaccounted); fast tier on the
final tree 10,557 passed, 0 failed.

**Sean's question (are the wrongly refused heads duplicates, or small boxes?):**
neither, for the seven on his tiles. None has an accepted sibling claim (1 of
222 refusals does); detector boxes are normal size (1.2-1.45 x 1.0-1.5 sp);
earlier owners took 0 px. Four were whole heads refused by the cut-through
contact rule (contacts 1.5-1.69 sp, just under its 1.7 edge), one by too-tall,
two were slivers because the rest of the head is fused with its stem and
unclaimed. Over all 222: sibling 1, detector box small 30, earlier owner 1,
cut or fused 25, head-shaped ink refused by a rule 165. 166 of the 222 are
written as notes in both arms; 56 in neither (one of them a real eighth,
Litolff p2 glyph 2/0/0/1/15).

**Still keyed on a dropped box (not fixed):** accidental owners (23 Litolff,
17 Brahms), slur/arc anchors, dot roles, stem values, fermatas, wedge and
dynamic anchors.

**Retire:** removed M6c (`stroke_owner._head_claims`, never fires). Kept: the
no-ink twin rule (the fallback; 53 / 72 boxes), `gather.cluster_marks` and
`page_marks.link` as the `=0` opt-out.

## 2.290 gate r3 (2026-11-11) -- after Sean's gate r2 tiles; NOT landed, two tiles out

Branch `land-2.290` 3e761c585 (main merged at ab1d82daf). Agent's report, checked
against the branch log only; its looks are not evidence.

- **Cause of the gate r2 doubts:** the tiles did not say how many notes each arm
  writes, so a fold of two boxes on ONE head looked like a lost chord note.
  Process lesson: a fold tile must draw every box and the key must say which
  arm writes which.
- Tile 12 (Brahms p19 m30): both arms write two notes (G-flat 6 and A-flat 5);
  the fold joins a sliver box to the lower head. No chord note lost.
- All 8 disagreeing folds: one printed head each (members trim to the same ink,
  centres within 0.1 sp). New rule `page_heads.split_by_ink_extent`: members whose
  trimmed extents are centred >= 0.8 sp apart vertically or >= 0.9 sp across are
  two heads (r1 tile 12 is the positive real case). A first version on extent
  overlap split a twin box into a false third note (p2 m32) and was dropped.
- Tile 7 (Litolff p11 m107): ON writes two notes, OFF three (the third a thin
  box at the same x). Tile 11 (Brahms p14 m11): both arms write two dotted halves.
- Tile 3 (Litolff p8 m58-59 staff 3): the lower-left head has NO detector box
  and is unwritten in BOTH arms (a detector miss, not this lane). ON writes
  A-natural tied to A-natural; OFF wrote A-flat at m59 with no tie.
- Tile 1 (Litolff p8 m69-70): `export._drop_unison_same_pitch_slurs` -- no slur is
  written from a unison head to a note of the same pitch; the drop is counted.
  The tie itself is the arc binding job (2.298 job 2).
- Five pages, flags off vs on: Litolff notes +3 -4, ties +10, pitches ~1, blue +6;
  Brahms notes +1, flags +1, blue +2. Judged right->wrong 0. Fast tier 10,567
  passed flags ON (run one tooling commit before the tip); check 228.
- Tiles: `out/print-from-worktrees/2.290-gate-r3/` (two tiles).
