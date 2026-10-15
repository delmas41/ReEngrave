# ROADMAP 2.131 -- a staccato dot is not a staccatissimo triangle (STAGED GATHER / ADJUDICATE / EXPORT)

Flag `OMR_STACCATISSIMO_SHAPE`, **default OFF** until Sean's tiles (`out/print/2.131-review/staccatissimo-review.png`,
hidden `_hidden/manifest.json`). Records: Brahms 317803 `20261013-night`; page measurements off the 600 dpi raster.

## 1. How staccatissimo is handled today (STAGED, measured)
* Two paths, by detector CLASS. `articStaccatissimoAbove/Below` (Brahms 379 + 356 boxes) go to `Q.ARTICULATION_MARK`, `articulation_owner`, and write `<staccatissimo/>` / `-!` (354 `-!` in the 20261013-night .ly). `articStaccatoAbove/Below` and `augmentationDot` go to `Q.AUG_DOT`, are decided by `adjudicate_dot_role` by POSITION only, and a staccato-role dot writes `<staccato/>`. Shape is read by nothing.
* **The brief's premise is wrong for Sean's tiles 1, 6, 11.** On the raster the staccatissimo triangles stand 0.4-0.5 sp under the head and have NO detector box at all (nothing within +-40 px, any class). The "dot" that was decided augmentation is a separate tiny box (14x9, 5x5, 5x2 px at 600 dpi = 0.15-0.4 sp) sitting on the head's edge or a stem foot. So tiles 1/6/11 are two faults: a triangle never boxed (reach, not this item) and a junk box decided augmentation (a size/ink fault, not shape). Sean's tiles 3, 4, 15 ("stac") are the same: the box is a stem-foot nub, the real staccato dots under the heads are separate.
* **Hand truth cannot count this**: no hand-truth page (`data/hand-truth`) holds any `artic*` label; page 0 has 135 `augmentationDot` and nothing else dot-like. The only truth is Sean's 15 tiles (above).
* A wedge hiding in the staccato class is real: on 14 Brahms pages (3,153 dot-class + 1,619 staccato-class boxes + 712 staccatissimo-class) the staccato-class boxes holding a wedge = 65 of 1,619 (4%), the dot-class 34 of 3,153 (junk included). Crops of 15 + 15 viewed: the staccato-class ones are triangles pointing at the note.

## 2. Shape reading and its margin (page raster, ink inside the detector box)
| class (detector) | n | height/width median (10-90%) | taper = point end / base end |
|---|---|---|---|
| staccatissimo Above/Below | 712 | 1.45 / 1.50 (1.25-1.7) | 0.58 / 0.62 |
| staccato Above/Below | 1,619 | 1.00 (0.82-1.25) | 0.91 / 1.11 |
| augmentationDot | 3,153 | 0.94 (0.82-1.17) | 0.90 |
Cut used: h/w >= 1.3, taper <= 0.8 (point toward the head), 0.40-0.85 sp tall. By detector class the cut keeps 78-87% of staccatissimo and 4-6% of staccato (the wedges in the wrong class). **The margin is soft**: 5th pct of staccatissimo h/w is 1.2-1.25, 90th pct of staccato 1.25. A cut on one Breitkopf score, labelled by the detector itself (not truth), so the adjudicator stays behind the flag. The plates' staccatissimo is a SHORT wedge (0.54 x 0.36 sp, h/w 1.5), not Bravura's 1.18 x 0.40: the dossier's `[C51]` doubt resolved -- the detector is not clipping it. 9 of 358 staccatissimo-class boxes measure round (<1.15) only because the box merged with a staff line; all 9 are triangles on the crop.

## 3. Fix (default OFF)
* GATHER `gather.mark_shape` / `_observe_mark_shape`: new `Q.MARK_SHAPE` (reader `CV_MARK_SHAPE`, a measurement) for every dot/staccato-class box, off `image_no_staff`, only when the flag is on.
* ADJUDICATE `adjudicate_dot_role`, before the augmentation window: a wedge needs a head in the staccato window on the side its point faces, takes the nearest such head, and decides `staccatissimo` (detail names owner, `candidates: [staccatissimo, staccato]`, h/w, taper). A wedge never becomes augmentation or staccato: no head -> `wedge_without_a_head`, only heads on the wrong side -> `wedge_points_away` (abstentions).
* EXPORT `_place_dot_role_marks` writes the value into the same list as staccato -> `<staccatissimo/>`; `dot_role_balance.attached_staccatissimo_before_hold_out` (informational; the equality is unchanged). Never GUESSED-blue: kept a DECIDED role behind the flag; the cut may only NARROW until Sean confirms (decision for the tiles).
* **Open gap found, not fixed**: the staged LilyPond exporter reads only `head["articulations"]`, so NO dot-role mark reaches the .ly -- the 20261013-night Brahms .ly has 354 `-!` (class staccatissimo) and zero `-.` although ~2,800 staccatos are decided. A wedge relabelled by this item reaches MusicXML, not LilyPond, until that is fixed (follow-up).

## 4. Measured (one page re-gathered with the flag, then re-decided flag off vs on over the SAME gather rows)
Brahms pdf page 24: `dot_role` flag off {augmentation 152, staccato 128, ambiguous 25} -> on {augmentation 150, staccato 104, ambiguous 24, **staccatissimo 24**, wedge_without_a_head 3}. 24 staccato -> staccatissimo (14 Above, 9 Below, 1 other), 2 augmentation + 1 ambiguous -> abstained wedge without a head. 0 `wedge_points_away` after choosing the owner on the point's side (first version chose the nearest head and abstained 7). Written as staccatissimo off 0 / on 24 on this page; the detector's own staccatissimo class (not touched) is unchanged. Not measured: the whole movement (needs a re-gather; Sean runs it), truth before/after (no articulation truth exists).

## 5. Tests / checks
`tools/omr/tests/test_staged_staccatissimo_shape_2_131.py` (16; real h/w + thirds from `glyph/24/1/1/3/15`, `24/0/5/6/14`, round `25/0/3/3/8`, `24/0/5/1/1`; flag-off, round-staccato, no-shape, points-away, speck, round-dot-beside-head augmentation controls; export). Targeted staged suites 129 pass; `test_staged_capture.py` has 2-3 failures that also fail on a clean origin/main copy. `staged.check` TOTAL 193 (= main; a computed-reason Ruling first made it 194). `judged score`: flag OFF = no gather rows and no new branch, so the records are untouched by construction (not re-run: 6.7 GB record).

## 6. For Sean
13 tiles, 2 controls (a round staccato; a detector-labelled staccatissimo), question "dot or triangle? (staccato / staccatissimo / augmentation dot / other)". Decides: is the cut (h/w 1.3, taper 0.8) right; should a wedge be DECIDED or GUESSED blue. Follow-ups: boxes 5x2 px decided augmentation (size gate), unboxed triangles (reach), staccato missing from LilyPond.
