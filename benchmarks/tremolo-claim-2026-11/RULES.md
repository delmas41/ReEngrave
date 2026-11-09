# 2.276 micro test: tremolo slash reader, BEFORE or AFTER the noteheads are claimed (pre-registered, written before the first run)

STAGED GATHER, page-wide pass. Sean 2026-11-08: "a CV treatment on the page read ... a micro test ... before or after noteheads are claimed".

## The two orders (same finder, same pages, same tree)

The reader is the one slash finder GATHER already owns (`gather.stem_slashes`, 2.71: track the ink out of both sides of a stem, one line, thick,
angled, at least 0.35 sp each side), moved from "once per stem per padded cell" to ONCE per page stem on the page raster (`page_strokes` canvas), with
twin stems (the same stem seen by two cells) read once. What differs between the orders is only what the reader may know about heads:

* **A, BEFORE noteheads are claimed.** The reader sees raw ink and no head box. Nothing vetoes a stroke at a stem end. Its claim is filed before
  `file_page_heads` (the head claim) so a head claim finding that ink held records it CONTESTED.
* **B, AFTER noteheads are claimed.** The reader is handed the detector's notehead boxes (page px): `stem_slashes`' own `at_a_head` veto applies (a stroke at the
  stem end that a head box explains, with no head at the other end, is the head's). Its claim is filed after the head claim.

## Frozen sample (named before the run)

Litolff (beethoven5-litolff, pdf 984073) pages 6, 13, 16. Brahms (brahms1-breitkopf, imslp317803) pages 12, 15, 16. Page numbers are the record's 0-based
page index (`glyph/<page>/...`). Gathered once with both orders computed in one pass (experiment switch, removed after the test).

## What is counted (per order, per plate)

1. slashes found (stems with at least one passing slash);
2. fakes: a found slash that on a crop is not a tremolo slash (a head, a beam piece, a slur crossing a stem, a ledger line, a dynamic);
3. real heads wrongly taken: a found slash whose ink is a real notehead's (the claim would have taken a head);
4. slash ink still boxed as a head: a found slash that overlaps a detector notehead box (page px, any share >= 0.5 of the slash's box) -- the leak the claim
   exists to close.
Truth for 2, 3: my crop look at EVERY slash in A union B on the six pages (a control, not evidence: rule 7), Sean's judged slash answers where a subject matches
(`benchmarks/acceptance/judged-tiles.json`, answer contains trem/slash), and the 12 blind tiles at the end.

## What decides the order (pre-registered)

* A real head lost to the slash reader costs MORE than a slash left unclaimed (CLAUDE section 4, rule 8): a lost head is a note missing from the file; an unclaimed
  slash is a refusal that the existing per-head tests (2.49 / 2.137) already make.
* So: if A claims ANY real head (count 3 > 0) that B does not, B wins unless B misses more than 3 times as many true slashes as A's real-head count... in short,
  the order is chosen by the first of these that separates them:
  1. fewer real heads taken;
  2. then fewer fakes;
  3. then more true slashes found;
  4. then fewer slashes still boxed as heads.
  A tie on all four = B (the later, safer order: nothing lost that a head could own), and the result is reported as "no difference measured".
* A slash found by only one order is judged on its own crop; the counts are on distinct slashes (a stem's slash seen by two cells is one).

## What is NOT claimed

Square-cut ends (page-facts: slash octagonal, head oval) are Sean's convention but cannot be measured on the page stroke (2.214: the stroke is not the mark).
This reader does not test ends. It is a stem-crossing reader; slashes BETWEEN two notes with no stem (whole-note tremolo) are out of scope and counted as "not
read", never invented. A slash is never a note, value or rest in the file; binding it to the stem's note (what the tremolo means) is a later step.
