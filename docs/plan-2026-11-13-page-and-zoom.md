# Plan 2026-11-13 — the page holds the facts; a zoom is only a way of looking

ROADMAP 2.307. STAGED. Sean's idea (2026-11-13), the manager's plan. Status: **a test, not a build** —
nothing here changes a default until the two measurements in §5 are in and Sean has ruled.

> "Cell padding has introduced all kinds of issues. The narrow view helps with notehead recognition but
> it complicates things on so many other ways. The whole page approach seems to simplify that. [...]
> Instead of cropping cells could it be a zooming in on the page itself with 2-4 zoom settings but where
> every time something is read it has all the context around it? Instead of cells we could have zoom
> setting on the whole page associated to a location on the page." — Sean, 2026-11-13
>
> "I don't want to use old methods because new ones don't work - that is patchwork that doesn't help us
> actually work better." / "I don't want the old arc reader." — Sean, 2026-11-13

## 1. The cause this answers

The measure cell does three jobs at once (`measure_extractor._build_measure_cell`,
`gather.gather_detections`):

1. **A view** — the picture the detector is shown, 16 px per staff space, barline to barline, padded
   above and below the staff.
2. **A container** — every record row is filed under page / system / staff / cell / box, and readers ask
   "which boxes are in this cell?".
3. **Evidence** — being inside a staff's cell is taken as belonging to that staff and that bar.

Job 3 is the fault. A crop's edge means nothing on the page, and we let it mean something. What it has
cost, each already measured in a benchmark:

- Padding shows one head in two cells; every later reader must remember to ask whose it is. 2.306 r3
  lists 13 readers of stem direction / join that do not ask; fixing two of them took Brahms red bars
  143 -> 129 (page-ledger-2026-11 FINDINGS).
- A barline cuts an arc in two for the detector: it boxes the far half of 8% / 25% of such arcs; the same
  detector on the whole staff row boxes 70-75% (2.273, `arc_strip.py`).
- A box clipped at a cell's left edge was bound to the first head under it (2.305 r1 tile 5).
- Arcs handed open from cell to cell; ties across a system break; letters sharing pixels with the
  barline at a cell edge (2.304).

Every page-wide reader landed since 2.284 (ledger, rests, dynamics, words, heads, arcs, stems) has been
a move away from job 2 and job 3, one symbol at a time, with the cell still the container underneath.
That is why each new reader breaks old ones.

## 2. The principle

**A view is how we look. The page is where facts live. A view's edge is never evidence.**

- A fact has one home: its place on the page (and the ink it claims on the page ledger).
- "Bar 12 of staff 3" is a QUESTION asked of the page — the marks whose owner is staff 3 between these
  two barlines — not a crop. It has no padding, so it has no copies.
- Ownership comes from the page (staff lines, ledger lines: page-facts, 2.216 B), never from which
  picture a mark was seen in.
- A reader that needs to look closer asks for a view centred on its subject, with the surroundings on
  every side. Nothing is filed under the view.

## 3. The zooms

| zoom | centred on | reads |
|---|---|---|
| page | the page | staves, systems, braces, barlines, layout |
| system | one system | arcs, hairpins, words, dynamics, beams, stems (the page-wide pass, already built) |
| staff band | a strip a little taller than one staff, sliding along the system | heads, accidentals, rests, flags, dots, clefs, keys — the detector's zoom |
| mark | one mark | "which line is this head on", "is there a beam at this stem tip", hollow or filled |

The first two exist. The mark zoom is page-facts' "measure against the staff locally, at the subject's
own x" made into the way of looking. The staff band is the open question (§5 T2).

## 4. Two changes, in this order

**A. Flip the container (no detector change).** Every ADJUDICATE / EVALUATE / EXPORT reader gets its
marks from ONE question — owner staff + bar region on the page — never by listing a cell's boxes. A copy
seen in a neighbour's cell cannot reach a reader at all. Cell ids stay as names for old answers and
tests, matched by place.

**B. The detector looks through staff-band views instead of cells.** Results are mapped to page
coordinates and duplicates are merged ONCE, on the page, by place. Only if T2 shows it finds at least
what cells find.

## 5. The test (what goes out now)

Frozen sample, saved gathers, replays only; no default changes; no whole-movement runs.

**T1 — how much of today's loss is the cell's doing?** (measurement only)
- per plate: heads / accidentals / rests that are copies of a mark owned by another staff, and how many
  of each reach a reader that does not check the owner;
- detector boxes clipped at a cell edge (by kind), and marks the page ink shows crossing a barline;
- of the heads the detector never boxed that we already know about (2.290, 2.305 r3 tile 8, hand
  labels), how many sit at a cell edge, on a barline, or in the padding;
- a prototype of change A as ONE filter after ownership is decided (flag OFF by default): replay from
  ADJUDICATE with the flag off and on — red bars, the shared file-change lines, Sean's judged answers
  right -> wrong (must be 0).

**T2 — does the detector read a staff band as well as a cell?** (measurement only)
- the production detector, same weights, same 16 px per staff space, on (a) cells as today, (b) the
  whole staff row (the 2.273 strip cut), (c) sliding staff-band windows with overlap; boxes mapped to
  the page and merged by place;
- scored against Sean's hand-labelled Brahms page 0 by class — found / missed / not his — and against
  his judged head, rest and accidental answers on the other frozen pages; false boxes per page counted
  (the unguarded 2.273 strip added 20+ false ARC boxes a page: expect the same risk here and count it);
- reported as three numbers per class per way of looking. No tuning, no guards, no merging rules beyond
  "same class at the same place is one mark".

## 6. What would falsify it

- T1: the one-filter prototype moves little, or moves Sean's answers right -> wrong: then copies are not
  the main cost and change A is not worth a migration.
- T2: bands or rows find fewer heads than cells, or pay for them in false boxes: then the detector keeps
  cell-shaped views — and change A still stands, because a narrow view is harmless once its edge means
  nothing.

## 7. What it will not fix

Pitch misreads (2.305 r1 tiles 9, 11); stems fused into heads on Litolff; heads the detector misses for
reasons other than an edge; ties across a system break (that is binding, not looking).

## 8. The cost, said plainly

Every judged answer, tile key and test names marks by cell id (page / system / staff / cell / box). They
must keep working, matched by place, while the page becomes primary. That is a migration with a plan of
its own, written only if §5 says go.

## 9. What changes today regardless

No new page reader is landed BESIDE the old reader it replaces (Sean 2026-11-13; DECISIONS). 2.305 arc
binding and 2.306 stems stay built with flags off until each can stand alone.
