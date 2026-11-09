# 2.274 step 2: pages and verdict rule, written and committed BEFORE any hold-out output is read (2026-11-08)

STAGED. Sean 2026-11-08, "Try 1": take ONLY the page-ink runs a detector arc box agrees with (WITNESSED: 0 fakes in the 20 seeded on the round-4 hold-out), bind each
run's two ends to notes and write each as ONE arc in the exported file, behind a new flag `OMR_PAGE_ARC_WRITE` (default OFF). A run no detector box witnesses is NOT
written in this step (about 4.8 fakes a page).

## What is built (so the rule can name it)
- GATHER: step 1's `page_arcs.gather_page_arcs` (frozen at 6a64c47b8, unchanged but for one added detail key `space_page_px`); `OMR_PAGE_ARC_WRITE=1` turns it on.
- ADJUDICATE, after the heads and `Q.ARC_KIND` / `Q.TIE_PAIR`: `adjudicators/page_arc.adjudicate_page_arc_binding` (`Q.PAGE_ARC_BINDING`, one verdict per page). Each witnessed
  run's ends are bound by the code that binds a detector curve (`ownership._bind_detail`, 2.223's body MOVED), the closest-note rule for an end that stops short
  (2.271's `bind_end(closest_ok=True)`, reused), the kind by Sean's tie rule on the two bound heads, the detector's class not an input.
- EXPORT: one arc per `written` run; the detector arcs of every box that witnesses it are dropped (one mark, one arc); a run off a system's edge is offered to 2.271 step 3's
  `_across_system_spans` (reused).

## Pages
- DEVELOP (looked at, may be fixed on): Brahms p0 (Sean's 153 hand arcs, `data/hand-truth`, scored by `benchmarks/omr-arc-binding-2026-10/p0_spans.py`), Litolff p4.
- HOLD-OUT ("seen" by r4's reader, never by the binder): Brahms p11, p20; Litolff p5, p13.
- NEVER USED by any 2.274 round (spares in RULES-r2/r3/r4; neither page was read by any reader of this lane): Brahms p8, Litolff p11. The code is FROZEN (sha written below)
  before either is read.
- Gate pages (export byte-identical flag OFF vs main): Litolff p4, Brahms p5.
- The records: the saved `20261104-night` gathers, cut to these pages. They hold no `Q.PAGE_ARC` rows (gathered with `OMR_PAGE_ARCS` off), so `step2/build_inject.py` files the
  rows with the SAME function on the page's rebuilt raster (control: Litolff p4 gives 115 runs, the number the real-gather gate of r4 filed). Both arms re-adjudicate the same
  injected slices (`lane_report --from adjudicate`), same tree, flag OFF vs ON. No re-gather.

## Measure first (develop pages, before the hold-out is read)
For every witnessed run of Brahms p0 and Litolff p4: written / abstained (by reason); of the written, what the OFF file already has: the same two notes and kind
(`whole`), arcs over the run that are not those (`cut_or_short`), or none. That is what step 2 can gain at most. Predicted before it is read: most written runs are
already `whole` in OFF (the detector sees the arc); the gain is the cut/short and the none; abstentions are dominated by an end that cannot bind or a same-pitch pair with
heads between.

## Verdict (hold-out + never-used pages, pooled; per page next to pooled)
GOOD (worth Sean switching on) only if ALL hold:
1. BINDING: in a seeded sample of 30 WRITTEN runs (all if fewer), by crop (the arc as the file writes it, a thin box on each bound head), the start and the stop are the right
   notes on at least 27 of 30 (90%). "Right" for an end that stops short = the closest note, as ruled; an end where two notes were about equally near must have abstained.
2. NOTHING LOST: of the OFF arcs a written run replaces, in a seeded 20: at most 2 were right and whole in OFF and are wrong or gone in ON. And the file loses NO arc that no
   written run overlaps (a lost arc outside a run is a bug, counted by the same command).
3. JUDGED: Sean's judged answers going right -> wrong: 0 (`judged score`; a control that cannot fail for this lane is named: the judged arc answers read `Q.ARC_KIND`, which
   this flag does not change, so the file-level check below is the one that can fail).
4. GATES: export byte-identical flag OFF vs main on Litolff p4 and Brahms p5; fast tier green; `python3 -m tools.omr.staged.check` TOTAL no higher than 230.
5. SEAN'S 12 TILES (the question: "Does the arc start and end on the right notes?"): 11 of 12 right. Reported, not self-judged.
Otherwise NOT GOOD, naming which criterion failed. Abstentions are counted by reason and, for each reason, what the old path writes for the mark. No constant is changed after
the hold-out is read. A tile is never recut to hide a miss.

FROZEN: reader, binder, decision and export as of commit 0f76b70ca (the develop-page measure-first and fixes are in it; fast tier 10066 passed; `check` TOTAL 229), committed and
pushed BEFORE the hold-out pages (Brahms p11, p20; Litolff p5, p13) and the never-used pages (Brahms p8, Litolff p11) were looked at for step 2. Honest note: the develop run
(`lane_report` replays every page of a slice, not only the counted one) also computed the hold-out pages' arms, and a debug line printed hold-out arc keys (not their content or
verdicts) before this line was written; no hold-out number was read or acted on. The develop-page fixes before the freeze, each from a look at ONE develop page: (1) the closest note is
measured from the ink's own end (`core_ends`), not the extension's (Brahms p0: a short tie carried on through an augmentation dot to a ledger stub bound to the wrong note, 11 printed arcs
lost vs Sean's hand arcs); (2) closest with no window (a head a little behind the end is a candidate); an end with no head ahead of it on the staff is the system's edge, not the last note.
