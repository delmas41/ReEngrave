# 2.209 -- a box on a beam's end sets another note's value (STAGED ADJUDICATE `stem_value`)

Cause: `Q.HEAD_STEM` joins any notehead-classed box touching a stem; `stem_value` reads the levels from the member nearest the tip, and `share_stem_value` (EVALUATE, Sean 2.78 "no exceptions") rewrites the other heads, DECIDED ones included. Nothing asks whether the member is a head. On Brahms p0 `/12/1/15` (score 0.25) and p5 `/7/20` (0.30) the member is a beam's thick end (crops confirm), 0 whole strokes covered.
Count (2.202strokes records, frozen pages, ADJUDICATE replay, no gather): decided values moved by stem_value: Brahms 33, Litolff 27. By what: dots 27+1, base 22+4, levels 2+4. Only the 2 Brahms level moves take the level from a beam-end box.
Ink alone (no blob + beam stroke) is NOT enough: 113 heads excluded, strong ones too (merged plates). With the stem-tip witness: 2 Brahms heads + 5 weak Litolff boxes, no Litolff file change.
Residual: Litolff p16 `/2/3/7` (0.26) owns a stroke and still sets two eighths to a quarter; not caught.
Flag OMR_STEM_BEAM_END (OFF). Lane report (frozen sample, `out/lane-report/2.209`): Litolff nothing changed; Brahms values ~3 (two sixteenths restored, one eighth->quarter), flag -1, red bars 171->172, judged right->wrong 0, wrong->right 1. Tiles: `out/print/2.209/tiles/sheet.png` (key `out/print/2.209/key.json`), not yet sent.
Lesson: a membership test that reads no ink lets any box vote; and a second witness must come from another source before a rule that is right on one plate is applied on a merging one.
