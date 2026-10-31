# ROADMAP 2.245 -- one cause for wrong-kind boxes (STAGED)

2026-10-31, branch `lane-2.245-wrong-kind` 610b326ae (Opus). Written by the manager from the lane's report (the lane's own write was refused by the hook). Scripts in this directory are on the branch.

## Cause and process lesson
ONE cause with several faces: the detector often boxes one ink under several classes, and every reader that turns a box into a mark takes the box's CLASS as the mark's kind. None of them checks the box's own size against that kind (fixed-size glyphs), the ink's shape (arcs, hairpins), or what an earlier claim or ADJUDICATE already said about that ink. Where the right class has no box at all (hairpins: about one detector box per page; an eighth rest never boxed), a low-confidence twin of the wrong class is the only claimant and stands as that kind. Three of the four had confidence 0.26-0.29.

Lesson: the claim order was built as if a box's class were a fact about the ink; it is a weak witness. Each layer (page owner, stroke owner, system arcs, notehead precision) was proved on its own boxes, never on whether the box is the kind it names.

## The four traced (20261029-night slices)
1. Litolff p10 `glyph/10/1/9/7/12` (2.240 s2 tile 2): a notehead box at 0.29, 1.85 x 0.59 sp, over a head's bottom plus a ledger line. ADJUDICATE already refuses it (duplicate box); the 2.240 page owner builds marks from GATHER boxes and gave the refused box an owner.
2. Brahms p19 `glyph/19/0/9/1/17` (2.240 s2 tile 9): a `tie` box at 0.26 on a hairpin leg; the same ink boxed `beam` from staff 10's cells; no hairpin box, no wedge read. The system-arc reader traced it and `arc_kind` decided "tie". The trace is straight (bow 0.06 sp); nothing tests for a bow.
3. Brahms p5 `glyph/5/0/4/4/15` (2.240 s2 tile 12): a notehead box at 0.29, 5.19 x 1.53 sp, on a slur four slur/tie boxes already name; ADJUDICATE kept it as a head and it was written as a half note. Nothing bounds a head box's size from above (the widest printed head is 1.69 sp).
4. Litolff p4 `glyph/4/0/8/5/8` (2.242 r1 tile 1): an eighth rest with no rest box. Its blob carries a head box (0.58, refused `too_narrow`) and a double-sharp box (0.34, 1.87 sp tall vs 1.01 printed); the double sharp blocks the narrow-box eighth-rest reader (`claimed_by_another_class`); with 2.242 ON the stroke owner gives the blob to the refused head.
- Add-on (2.223 letters read as hairpins, Sean's 2.223 tile 11): same cause -- the CV hairpin reader names ink a hairpin with no size test and without reading the word claim. Hairpin rows narrower than 1.6 sp: Litolff 3 of 4, Brahms 6 of 53 (`hairpin_letters.py`); 2.223's crops found 8 of 8 such rows are letters. Rows at least half inside a word claim: L 1, B 11 (not clean: word boxes over-reach onto real hairpins).

## How often (frozen sample, 8 + 8 pages)
- Head boxes >= 3 sp wide kept as heads: Litolff 10, Brahms 2; on the lane's crop look none of the 12 is one head (slurs/arc pieces, beams, 2-3 heads in one box, slashes or a dynamic, a quarter rest). 2.5-3.0 sp boxes are mostly two heads -- left alone.
- Box height is not a usable signal (tall and short boxes are mostly real heads); no height rule.
- "Arcs" that do not bow (>= 3 sp long, bow < 0.15 sp): Brahms 19, Litolff 1; 18 of the 19 Brahms ones are hairpin legs, all class `tie` (~2 hairpins a page read as arcs on Brahms).
- Refused head boxes still claiming strokes in the stroke owner: ~760 L, ~540 B; mostly duplicates that merge harmlessly.
Counts are the lane's own look on crops; not yet checked by Sean (his 12 tiles below).

## What was built (flag `OMR_BOX_KIND_SIZE`, default OFF, deny-list)
- `tools/omr/staged/box_kind.py`: `head_box_misfit` -- a head-class box >= 3.0 sp wide cannot be one head (3.0 = the stroke owner's existing `HEAD_MAX_W_SP` convention, not a tuned number).
- `adjudicate_notehead_is_not_a_notehead` refuses such a box `wider_than_a_head`, LAST among its refusals (first-in-chain re-labelled boxes already refused as duplicates).
- A stroke-owner veto on the same test was built and DROPPED: it lost a real Litolff eighth (p4 4/1/1/14) where the wide box is the only claimant big enough for the fused blob; `adjudicators/stroke_owner.py` is identical to main.
- reach.py, both flag tables, rule page + ink-rules regenerated, ROADMAP row, version_memory.

## Three measures (out/lane-report/2.245/, frozen sample)
- Litolff: notes +3 -10, flags +1 -4, beams +4 -1 ~2, blue +6 -4, words +5 -3; red bars 199 -> 197.
- Brahms: notes -2 (a beam boxed as a head; case 3's slur), values ~2, words -2; red bars 164 -> 162.
- Judged right->wrong 0, unwritten->wrong 0 both plates; wrong->right 1.
- Not clean: Litolff p9 9/0/3/1 (one box over three eighths: loses two eighths, gains one); p4 4/0/0/11 (removing a false head on "ff" leaves a gap and EXPORT marks the whole bar red, so its real half notes are no longer written -- a later-stage rule to rework, not a reason to keep the false note). 12 unjudged tiles in out/lane-report/2.245/unjudged/.
- Tests: test_box_kind_2_245.py (9). Full fast tier once: 9,504 passed, 10 failed (module not registered, rule page stale) -> fixed, 8 affected files 197 passed; the whole tier NOT re-run on the final tree.

## Handed off (fenced, not built)
- 2.240: build page marks only from boxes ADJUDICATE has not refused (case 1); call `box_kind.head_box_misfit` before a head box becomes a page mark.
- 2.223: a tie/slur trace that does not bow is a hairpin leg or a beam, not an arc (`straight_arcs.py`); hairpins need their own page-wide claim before arcs.
- 2.242 / 2.247: an accidental box much taller than its printed glyph is not that accidental; then the narrow-box eighth-rest reader can read case 4.
- Not built, this lane's own: the hairpin-letter source fix in `gather.py`'s hairpin reader (skip ink the word claim holds; test the mark's size) -- a GATHER change needing a `--from gather` measure.

## Prior work
ink-rules `too_narrow`, `notehead_is_a_duplicate_box`; page-facts §5 rejected `OMR_ARC_RECLASS` and the 2.25b hairpin exclusion (the bow test is the ink's own shape, neither of those); benchmarks omr-notehead-width-2026-09, omr-hairpin-cv-2026-09; LEGACY only ever set a width FLOOR for heads, never a ceiling.

## Incident
The lane's 2-page subset run (`LANE_REPORT_SAMPLE`) overwrote the shared Brahms lane-report slices (the lock/truncation incident 2.223 reported); a later full run re-cut them (stamp back to [0, 4, 5, 8, 12, 14, 19, 25], checked by the manager). Slices should be keyed by their page list (tooling follow-up).

## Tiles
out/print/2.245-tiles (key outside tiles/): the four places, four wide head boxes the rule refuses, two straight "ties" (hairpin legs), two controls. Sean's answers 2026-10-31 (answers.json): the four places as traced; wide head boxes 4/4 not one head (2 beam, 8 arc, 12 arc) but 4 holds an eighth + a natural and 10 three eighths -- refusing loses real notes; straight 'ties' 3/3 hairpin legs; control 3 an eighth; control 9 (2.54 sp, left alone) part of a C clef.
