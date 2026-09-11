# Arcs reach the file — the third `decided_and_unwritten` family, closed

2026-09-10. `adjudicate_arc_kind` and `adjudicate_arc_owner` landed the day
before and decide **199 arcs on one page**; `grep '<slur' tools/omr/staged/export.py`
returned **zero**. *The value existed and nothing read it* — inside the
architecture built to stop exactly that, one day after the same shape was found
and fixed for the dynamics.

## 1. WHAT LANDED

| | |
|---|---|
| `Q.CELL_BOX` | each measure cell's own page rectangle, **gathered** |
| `staged/export.py` | `_place_arcs`, `_pair_arcs`, `_arcs_by_kind`, `_flatten_part` |
| the merge | `_merge_arcs_across_barlines` / `_noteheads_under` / `_number_spans` **imported and called**, never ported |
| the report | `arcs_not_written`, a four-way partition, kept OUT of the note balance |

⚠️ **`Q.CELL_BOX` is a GATHER change, and it is the reason this could not be a
pure export fix.** `gather_detections` has read `cell.bbox_page_px` since page
boxes arrived (`_page_box` opens with it) and threw it away after converting
one glyph. The merge asks whether an arc ends ON its cell's right edge and the
next begins on its left; that is a question about the CELL's boundary, and
deriving it from the glyphs inside would put the edge wherever the outermost
detection happens to fall — so an arc genuinely reaching the barline would test
as ending in open space, the more certainly the wider the margin.

## 2. MEASURED — Litolff Beethoven 5, pdf pages 1-3, 12 parts

One gather, exported twice (`export_arc_arm.py`); the OFF arm removes the
pairing pass, reproducing the state this session found.

| | OFF | ON |
|---|--:|--:|
| `<slur>` elements | 0 | **46** |
| `<tied>` elements | 0 | **98** |
| slurs written | 0 | **23** |
| ties written | 0 | **49** |
| notes / rests | 1075 / 432 | 1075 / 432 |

**Controls.** Outside the arc elements the two files are **byte-identical**;
notes, rests and the accounting balance are unmoved; music21 reads the ON file
back as 12 parts and **exactly 23 Slur objects**, matching the counter.

**The partition is exact**: 514 arc rows → 476 merged groups (so **38 arcs, 7.4%,
are one half of a cross-barline pair**) → 23 slurs + 49 ties + 361 + 43 = 476.

## 3. ⚠️ THE DOMINANT BUCKET IS A READING SHORTFALL, NOT AN EXPORT ONE

**361 of 476 merged arcs (76%) bind fewer than two noteheads** and are refused —
one end would leave an unpaired `<slur type="start">` and an INVALID file. On a
scan the usual cause is that the notes under the arc were never detected. So
the export half of this family is now done and **the remaining three quarters
are the detector's**, which is the same shape this repo already records for
hairpins on scans. Do not read 23 slurs as "the exporter recovers a quarter of
the arcs" — it recovers all of the ones that had two notes to bind.

## 4. ⚠️ FOUR ACCOUNTING HOLES, THREE OF THEM IN THIS SESSION'S OWN CODE

Each was a place an arc vanished with no number attached. All four are now
counted, and `test_every_placed_arc_is_written_or_counted` asserts the
partition rather than any one of them.

1. **A bar with no geometry.** `_merge_arcs_across_barlines` opens with "no box
   or no spacing, break the chain and move on" — right, there is no unit to
   measure a boundary in — but its `continue` skips that bar's arcs whole.
2. **An arc binding fewer than two notes** (above).
3. **A span past the slur-number ceiling**, dropped rather than renumbered.
4. ⚠️⚠️ **A span whose ends land in the SAME CHORD — and this one was found on
   a real page rather than by review.** The report said **55 slurs where the
   file held 23**. `voicing._chord_span_states` discards a span whose start and
   stop share a chord ("a slur from a note to itself is a curve to nowhere"),
   and `_paired_spans` cannot catch those: it refuses two ends on one
   DETECTION, while a chord is several detections at one x. **32 of 55 marked
   spans**, discarded correctly and silently, two modules from anything that
   knows an arc was involved.

⚠️ **The fix for (4) is where the counter lives, not what it counts.** It was
incremented where the mark was SET; it now increments where the ELEMENT is
written. That is the `FAMILIES` table's own rule arriving from a new direction —
*a verdict says what was DECIDED, and only the exporter's counter says what
reached the FILE* — and a counter placed at the mark measures the first while
reporting it as the second.

## 5. ⚠️ WHAT THE MUTATION BATTERY FOUND THAT THE TESTS DID NOT

Nine arms. **Seven were red on the first run and two survived**, and both
survivors were the shape the handoff names: *a test named for a hazard it does
not reach*.

* **Reading a CORNER box as a WIDTH box** — `[x0,y0,x1,y1]` vs `[x,y,w,h]` —
  turned a 140px arc into a 1190px one and **every assertion still passed**,
  because a wider arc still yields one span with one start and one stop.
  ⚠️ **Counting spans cannot see a frame error; only naming the NOTES can.**
  The fixtures are offset to page x 1000 for the same reason: at the origin the
  two spellings agree in every coordinate.
* **Marking every chord member** rather than the first. Every fixture used
  single notes, so the mutant passed all of them. A `<slur>` on each member
  opens N spans of one number and closes one — malformed, not merely wrong.

⚠️ **One arm is an EQUIVALENT MUTANT, not a coverage gap.** Marking bar 0 of
every run a system break changes nothing: at index 0 `pending` is empty, and
`at_break` is read only inside `if pending and resumes`. Recorded so the next
person does not chase it.

## 6. ⚠️ NOT DONE, AND NOT ATTEMPTED

* **No OMR-NED figure is claimed, deliberately.** The metric is symmetric, so
  emitting more symbols is rewarded: the legacy slur work's first cut LOWERED
  pooled OMR-NED while RAISING the edit count. That is why the merge lands
  WITH the emission rather than after it, and why the control here is a
  byte-comparison plus a partition rather than a score.
* `OMR_ARC_RECLASS`'s position grammar is **not** re-litigated. `arc_kind`
  records the grammar's opinion and lets the detector's class decide; that
  refusal was measured on both families (scan +130 edits) and is inherited.
* The three remaining stubs are untouched: `articulation_owner`,
  `wedge_anchor`, `direction`.
