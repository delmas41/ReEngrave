# ROADMAP 2.276: tremolo slashes read once on the page, claimed once (STAGED)

Branch `lane-2.276-trem-claim` 2b5af727d, flag `OMR_PAGE_TREMOLO` (default OFF). Pre-registered rules are in RULES.md. The lane agent's Write of this file was refused by the harness. The manager committed it from the agent's report of 2026-11-09, which is the source; the numbers are the lane's own.

## Cause and process lesson
- **Cause:** a tremolo slash had no owner. The detector's tremolo classes never fire (0 boxes on both 20261104-night records), so slash ink reached ADJUDICATE only as a head, flag, beam or rest box in a padded cell, and was refused box by box.
- **What still gets through:** on the sample pages, Litolff 7 of 62 and Brahms 3 of 74 slashes still have a head box written as a note.
- **Lesson:** the claim plan left slashes per cell because they sit on a stem. That settled where they are read, not who owns their ink. A mark the detector cannot box is the one the page pass must read.

## Prior work
STAGED unless marked.
- **2.49:** a head-box test (a thick diagonal crossing a stem). ON.
- **2.71:** the one finder, `gather.stem_slashes` → `Q.STEM_SLASH`, once per stem per padded cell. ON.
- **2.137 `OMR_SLASH_AT_STEM_END`:** ON.
- **2.205:** the `stroke_owner.shape_fit` slash branch. Counted only.
- **2.214:** square vs round ends. Stopped, because the ends do not separate on fused ink.
- **2.270:** the `straddles_a_stem` export guard. ON.
- **LEGACY:** reads detector tremolo boxes that never fire, so it is dead on these plates.

## What works
The per-box rules refuse slash boxes the detector draws as heads: Litolff 99 and Brahms 181 by `tremolo_slash_crosses_stem`. None of them touches a slash nobody boxed, and none says the ink is claimed.

| plate | slashes found | no box at all | refused boxes only | box written |
|---|--:|--:|--:|--:|
| Litolff | 62 | 19 | 36 | 7 |
| Brahms | 74 | 33 | 38 | 3 |

## Micro test: read the slashes before or after the heads are known
Pages: Litolff 6, 13, 16; Brahms 12, 15, 16. Counts are the lane's own look.

| | Litolff before | Litolff after | Brahms before | Brahms after |
|---|--:|--:|--:|--:|
| slashes found | 74 | 62 | 77 | 74 |
| real heads taken | 12 | 0 | 2-3 | 1 |

- **Winner:** AFTER, by the pre-registered rule (fewest real heads taken).
- **Residual:** one dotted head is taken, and about 3 doubtful Brahms marks (a `p`, two small marks). Reported, not tuned.
- **Claim order:** the read runs after the heads are known, but the claim is filed in the layer before `head`. So a head box on slash ink is a later box than the claim.

## Built
- `tools/omr/staged/page_tremolo.py`: the 2.71 finder, run once per page stem on the page canvas.
- Claim rows: `Q.CLAIMED_AREA`, owner `tremolo`, unit `page_ink`. The layer `tremolo` goes before `head` in `claim_order.LAYERS`.
- Hook: in `gather.gather()`, after `gather_page_claim_boxes` and before `file_page_heads`.
- Registered in `record.py`, `capture.py` and `reach.py`.
- Tests: 10, in `test_page_tremolo_2_276.py`.
- The flag row is in the flags doc, and ink-rules was rebuilt.
- Retired: nothing. 2.277 consumes the claim as an ordinary layer. Once it lands, the 2.49 stroke witness, the 2.205 slash branch and the per-cell twin reads become redundant.
- A slash never becomes a note, value or rest. Binding a slash to its note is a later step.

## Measures
- **File, flag ON vs OFF:** unchanged on the Litolff frozen 8 pages, and on Brahms p5 and p12. Brahms was a 2-page control, not the frozen sample. Nothing consumes the claim yet.
- **Judged:** right→wrong 0 and unwritten→wrong 0. "OFF==record" is NOT CHECKED in gather mode.
- **Byte-identity:** flag OFF vs base 4020041e7, MusicXML identical on Litolff p4 and Brahms p5. This is not against today's main; merge main before landing.
- **Check:** `staged.check` 227. It was 232 until five unread detail keys were removed.
- **Fast tier:** 10,021 passed, 4 failed (the flag docs, ink-rules and wiring). All 4 were fixed and their files re-run (39 passed). The whole tier was not re-run.
- **Tiles:** `out/print/2.276/`, 12 tiles with key.json, asking "Is the boxed mark a tremolo slash?". Not yet answered. By the lane's look, 2, 3, 4, 5, 8, 9, 11 and 12 are slashes, and 1, 6, 7 and 10 are real heads. Tile 1 is the dotted head the reader takes, the control that can fail.

## Round 2 (branch `lane-2.276-r2`, 2026-11-09): the merged-tree tiles, re-read

- **Cause:** the "4/7" was a misread of the key, not a reader that takes heads. The key marks tiles 3, 4 and 6 `role: control, side: unchanged`: they are notes the merged tree STILL WRITES. On the Litolff frozen 8 pages (STAGED, `OMR_PAGE_TREMOLO` on, claim-final on) no tremolo claim overlaps any of the three boxes (checked on the claim rows), and all three keep `notehead_is_not_a_notehead: decided false, reason notehead`. The 4 `lost` boxes (tiles 1, 2, 5, 7) overlap a tremolo claim 79-100% and are the 4 slashes Sean named. So the claim covered real head ink 0 times in 7, not 3.
- **Process lesson:** the tile question ("each box is now refused... is it a note?") was posed over controls too, so a right answer on an unchanged note read as a defect. A control tile needs its own question, or a key column the reader checks before counting.
- **Sean's convention (tile 4, 2026-11-09):** a slash crosses the stem shaft between the head end and the free end, never at or past the head end. Built as a pure-ink test in `page_tremolo.head_end_verdict` (a heavy blob beside the stem within 1.4 sp of one end and not the other = head end; refuse a candidate within 1.4 sp of it or past it; abstain, keep the candidate, when both or neither end carries a blob).
- **What the end test alone settles** (page raster, Litolff): of the 4 true slashes, 3 pass (`ok`: head at the far end) and 1 (tile 5, short stem, ink at both ends) abstains; 0 refused. Of the 3 controls, none is a candidate (no claim to refuse); tested as hypothetical slashes at the head's own height: tile 4 would be refused (at the head end), tile 6's box lies past its stem top (would be refused), tile 3 (second head of a stacked chord, mid-shaft) is not settled by an end test. A shape test would be needed for that, and no claim exists there to fix.
- **On the 40 candidates the finder passes on the 8 pages:** `ok` 34, abstain 5 (12.5%), refused 1. The refused one (p9, `[2339,3622,2365,3650]`) is a dynamic `p`, so the refusal is right but by luck of placement. Fused ends are common over ALL page stems (head end told 2,621, both ends heavy 290, neither 3,933 of 6,844), and they are why the test cannot be the only test; among slash candidates the abstain rate is 12.5%.
- **Other claims that are not slashes (by my look at 12 tiles, not Sean's answer):** a beam fragment is still claimed; to Sean as tiles in `out/print/2.276-r2/tiles`.
- **Measures (main dcada1465 + this branch, flag ON vs OFF, Litolff frozen 8 pages, 20261104-night, master cells):** file notes -4, words +1; red bars 0 -> 0; judged right->wrong 0, unwritten->wrong 0, wrong->right 1. Identical to the pre-end-test scratch merge: the end test changed no written note.

## Round 3 (branch `lane-2.276-r3`, 2026-11-09): the beam piece and the dynamic p (Sean's r2 tiles 5, 6, 10)

- **Cause (STAGED GATHER):** both marks WERE read before the slash was, and the finder was never told. Tile 10 and tile 6 stand under the detector's `dynamicP` letter box (the candidate lies 0.96 / 0.95 inside it); tile 5 under a detector `beam` box (0.89 inside). Nobody CLAIMED either: the word claim files a lone dynamic letter GUESSED and not at all when the letter stands inside a staff's line band (`word:dynamic_letters:lone_letter_inside_a_staff`, "milestone 4"), and no page-wide beam claim stands before the tremolo claim (`page_beams` is OFF and runs after it; `claim_order.LAYERS` has beams AFTER heads). `read_page` was handed the detector's NOTEHEAD boxes only (the order micro test's one question) and its `at_a_head` veto is the only earlier read it consults. So it took ink that an earlier-ordered mark had been read on.
- **Which rule owns the order:** Sean 2026-10-16 (DECISIONS; plan-2026-10-28 section 3): notehead, stem, beam or flag, shared stem, THEN "trem slash or anything else"; a later step reads the earlier answers and never overturns them. Dynamics claim first (CLAUDE section 3; `claim_order.LAYERS` word_dynamic is layer 3, tremolo 6). The one value this lane adds is `HELD_SHARE_MIN`, which is not new: it is `claims.INSIDE_SHARE_MIN` (0.5, the register's own cut, a test asserts equality). No angle or thickness cut is touched.
- **Process lesson:** the order micro test varied one thing (heads known or not) and listed its residue ("a p, two small marks") as reported, not tuned. That residue was the other earlier families. When a micro test hands a reader the earlier reads, it hands every family the reading order puts first, not the one under test.
- **Fix:** `page_tremolo.held_boxes` (detector dynamic letters, `beam`, `flag*`, page px) handed to `read_page`; a candidate with at least 0.5 of its own box inside one is refused (`held_by_earlier_read`), before the stem-end test. It is a refusal, never a claim of the other mark: the beam and the p still have no page claim (that is the word / beam lanes' work). Tile 6 is now refused for the stated reason instead of by the placement luck the end test had.
- **Do the real slashes survive?** On the 12 r2 key boxes, the 9 real slashes' overlap with any dynamic / beam / flag box is 0.00 (probe on the OFF gathered record: their detector boxes are noteheads, a tie, an arpeggio and staff structure, none of the three families); the claim rows confirm: the 9 are each covered 1.00 by a tremolo claim in the r3 arm.
- **Measures (Litolff pages 2, 6, 9, 10, 16 = every page the 12 tiles stand on, 20261104-night, master cells, detector cache, flag ON vs OFF; `lane_report`, not the frozen sample):**
  - claims on those pages: r2 39, r3 37. The two dropped are tiles 5 and 10; nothing else changed, so no new tiles are owed (rule: tiles only where the claim set moves beyond the three).
  - claim cover of Sean's 12 boxes in r3: tiles 1-4, 7-9, 11, 12 covered 1.00; tiles 5, 6, 10 covered 0.00.
  - file: notes -4, words +1, red bars 0 -> 0 (identical to r2: the beam and p claims never wrote a note); judged right->wrong 0, unwritten->wrong 0, wrong->right 1.
  - `staged.check` TOTAL 229, like for like with the r2 head (229) on the same merged tree.
  - fast tier: 10,077 passed, 12 skipped, 2 xfailed, 0 failed.
  - Not measured: Brahms (a breitkopf beam box may cover a real slash; the cost is a lost claim that falls back to the old per-box refusals, never a wrong note), and the whole movement.
- Flag stays OFF.
