# 2.278 micro test: pre-registered rules (copied verbatim from the plan, written BEFORE the prototype)

Source: docs/plan-2026-11-08-beam-flag-reading.md section 4 "Micro test, before any build (pre-registered)", sha f24726179. The plan wins over any paraphrase.

> Offline probe, no pipeline code, on frozen material only; kill at the first failed bar.
>
> 1. **Hand truth** (the only labelled beams, Brahms imslp317803 p0: 50 beams, 277 stems, 42 flags; Sean's boxes): from the page raster
>    alone (M4a `page_beams` strokes + 2.269 names, already on main, OFF), apply steps 2-4 (two-stem join, bind by width, levels) and compare each
>    truth stem's beamed/bare/flag class. **Pass: every stem bound to a beam is beamed in the truth (precision >= 0.98), and the
>    bound stems cover at least 90% of the truth-beamed stems that have a stem row** (the cell readers' number on the same page is
>    the control; the probe must beat it).
> 2. **The narrowed heads** (Litolff 8 frozen pages, Brahms p0+p5; the 20261104-night record): of the beam-family narrowed heads the rule
>    would decide, the share decided must be at least 50%, and every head Sean has judged (`judged build`; value answers on both plates)
>    must keep its answer: **judged right->wrong = 0** (a right->narrowed counts as a failure to explain, not a pass).
> 3. **Sean's blind tiles** (out/print/2.278, 12 tiles): the probe's value, where it decides, must match Sean on at least 11 of the
>    tiles it decides; any tile where it decides and Sean disagrees kills the rule until the cause is found.
> 4. **A control that can fail**: the same probe with the beam stroke shifted 12 px (about 0.75 staff space) must fail bar 1 (precision
>    falls); the same probe run with the two-stem rule removed must admit the slur/hairpin strokes M4a filed as beams (the count of
>    non-truth bound strokes must rise); if either does not move, the probe is a computation, not a measurement.
>
> Kill / pivot: precision below 0.95, or fewer than 30% of the beam-family narrowed heads decided, or any judged right->wrong. Then
> the loss is the page raster (fused ink on Litolff, 17 of my 40) and the next lane is the stem and head split (M6), not a beam reader.
> A pass opens one build lane, default OFF, measured on the frozen sample with the three measures (file diff, 12 tiles, judged
> right->wrong 0); the whole movement is the overnight's job.

Plan steps 2-5 the test applies (verbatim):

> 2. A stroke is a beam only if it joins at least two stems at their ends ... Two stems or more under it: certain. Fewer: not a beam. There is no "possible".
> 3. Bind by width: every stem whose tip lies under the beam's x-extent on the beam side is owned by that beam ... Beams stay inside one bar.
> 4. Levels = number of parallel strokes under the stem's x (a fused double beam is one stroke whose thickness is about two beams; it is split by the thickness ratio and the gap profile, never by a cell cut). A second level that cannot be shown is reported as unread, not as possible.
> 5. Flags are read at the tip of stems no beam owns.

Task brief (2026-11-09): Brahms p0 hand truth 50 beams, 277 stems, 42 flags. Pass: precision >= 0.98; coverage >= 90% of truth-beamed stems that have a row; >= 50% of beam-family narrowed heads decided; judged right->wrong 0; >= 11 matching on the tiles it decides. Kill: precision < 0.95, < 30% decided, any judged right->wrong. Controls: shifting a stroke 12 px must fail the precision bar; removing the two-stem rule must admit slurs and hairpins.

Lane rule: no tuning toward the bars after results are seen. Any change after seeing results is stated in FINDINGS and the controls re-run.
