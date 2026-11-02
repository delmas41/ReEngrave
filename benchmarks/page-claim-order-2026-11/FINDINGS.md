# 2.253 step 0: the page-wide kinds on the frozen sample -- count, and what their ink becomes (STAGED GATHER, read-only)

Written by the manager from the lane report (lane-2.253-page-order 111a4d5ae; the lane hook refuses subagent FINDINGS writes). Nothing built; no flag.

## Cause and process lesson

The "letters become hairpins" fault is already fixed at its source by 2.245's width test (narrow 'hairpins' are letters). What the CV hairpin reader (`gather_wedge_boxes`) still files are real hairpins. The live problem runs the other way: the reader MISSES most Brahms hairpins, and word-claim boxes reach over real hairpins -- so moving words ahead of hairpins now would delete real hairpins. Lesson: an earlier claim inherits that claim's box-size errors; measure where the earlier claim's box is wider than its ink before reordering.

## Count (frozen 16 pages, 20261029-night slices, 2.245's 1.6 sp rule applied; crops `out/print/2.253-count/`)

- Letters as hairpins: 0 of 48 kept rows (Litolff 1, Brahms 47); 9 narrow rows already refused by 2.245. Two kept rows are other marks: the '//' system separator (Brahms p4) and an accent '>' (Brahms p19). `hairpins_kept_sheet.png`.
- Hairpins inside a word claim: 5 rows, Brahms p8, all real hairpins beside 'dim.'/'espr.' (sheet tiles 10, 13, 27, 30, 38).
- Hairpins missed: reference encodings have 5 wedge starts on the Litolff pages, 119 on Brahms (per part, so condensed staves over-count); the reader files 1 and 47. Brahms p12 9 -> 0, p19 20 -> 1, p25 46 -> 5; p19 misses include short wedges above notes touching slurs (`pages/brahms_p19.png`).
- Rehearsal frames: Litolff 0; Brahms 8 (B, G, H, P, above and below the system, p4/12/14/25), none in the reference. p4 top 'B' = unclaimed strokes in two cells + a refused restWhole box + part of the bar-number word claim.
- 8va / pedal / segno / coda: none printed, none in either reference. The detector drew 31 boxes of those classes, all on other ink ("pedal" on 'cresc.'/'dim.'/'Basso', "ottava" on bottom staff lines, "segno" on 'ff'). `rare_classes_sheet.png`.
- Trill lines: Litolff >= 2 (timpani rolls p9, p16), none boxed; Brahms 3 'tr' (p4 1, p12 2 with wavy lines), boxed by the detector, read by nothing; wavy lines unread; the Brahms reference omits them.

## Ranked by whole-movement loss

1. Hairpin reach (~683 wedge starts per Brahms movement in the reference) -- not an order problem; its own row.
2. Word-claim box size over hairpins -- before any words-first order touches hairpins.
3. Rehearsal frames (~1 per Brahms page).
4. Trill wavy lines.
5. 8va / pedal / segno / coda -- absent on both plates.

## Not verified

Every classification is the lane's own look, not shown to Sean. The reference counts hairpins per part, not per printed staff. What the missed hairpins' ink becomes was not traced on the canvas (`claim_readout`). Brahms p5's bar range is unknown, so it has no reference count. Manager's look at p19: many of the "missed" marks are short wedges above single notes -- hairpin or long accent is Sean's call before a reach lane opens.
