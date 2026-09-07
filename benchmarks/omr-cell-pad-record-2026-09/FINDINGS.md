# A measure cell records the pad it was cut with

2026-09-07 · branch `claude/fix-measurecell-pad`, cut from `main` at `77e46b5f`.

## The gap

`MeasureCell` recorded the bbox, the canonical staff-line ys and the upscale
factor — everything about the frame except **the pad the crop was taken at**.
The pipeline cuts at `PAD_ABOVE_STAFF_LINES = 4`;
`annotate/select_cells_orchestral` **monkey-patches those module globals to
5.0** for a labeling batch, and does not patch `PAD_MAX_STAFF_LINES`.

Every saved label box lives in the cell's CANONICAL frame, so a cell re-cut at
a different pad is not a slightly different picture — it is the same music at a
different scale, with every box in the batch landing somewhere else and nothing
downstream saying so. `annotate/recut_cells.choose_mode_and_cut` therefore
**derives** the pad: it cuts the page under each candidate mode and keeps the
one that reproduces the manifest's `cell_canonical_w` / `_h` /
`staff_line_ys_canonical`. That derivation exists only because the fact was
never written down.

## The field

`MeasureCell.pad_above_staff_lines` / `.pad_below_staff_lines`, floats in staff
spaces, populated in `measure_extractor._build_measure_cell`. The value is
always one of two constants — the point is **which**, per cell and per side.

**PER-CELL, NOT PER-MODULE, and that is the whole design point.** The pad
starts at the module constant and GROWS to `PAD_MAX_STAFF_LINES` on whichever
side the neighbouring staff is further than the ceiling away
(`grown(default, room)`), so on an ordinary page the top staff is cut at 6
above and 4 below while the staff beneath it is cut at 4 on both. Reading the
module constant would be wrong exactly where the growth happens, which is the
case the growth exists for.

`grown()` now returns `(spaces, pixels)` rather than pixels alone. The pixel
pad is truncated to an `int`, so `px / spacing` answers **3.998** for a
four-space pad and could not be compared against the constant it came from.
The pixel arithmetic is unchanged — `int(ceiling)` and `int(spaces * spacing)`
are the two branches the one-line conditional already took.

It is the pad the cut **asked for**. `y0`/`y1` are additionally clamped to the
paper, so a staff at the page edge got less; what it actually got is
`bbox_page_px` against the staff's own `line_ys`.

## ⚠️ `recut_cells` is untouched, deliberately

The derivation stays. Two reasons, and neither is caution for its own sake:

- its abort-on-frame-mismatch is a **safety property** over irreplaceable human
  verdicts, not a workaround to optimise away;
- **no batch carries this field at all, and none will until a cutter changes.**
  It is not merely that legacy manifests lack it: no manifest writer anywhere
  in `annotate/`, `run_pipeline.py` or `transcribe.py` emits it, so every batch
  cut from here on lacks it too. The derivation is the only thing that can read
  *any* batch, today and after this lands.

Record first, decide later — including deciding not to.

## Agreement with the derivation — `probe/probe_pad_vs_derivation.py`

**Read the anti-vacuity clause first, because it is the difference between this
probe and a green tick.** A cell grown to the ceiling on both sides records
`(6.0, 6.0)` under *either* padding mode, so a page whose every cell grew that
way would "agree" with both modes and prove nothing. The probe therefore
requires that **at least one cell's recorded pad be inconsistent with the mode
that was NOT chosen**, and fails loudly (`VACUOUS`) otherwise.

Around that: cut the page under mode M, write a **legacy-shaped manifest with
no pad field**, hand it to `choose_mode_and_cut`, and check the derivation
recovers M and that every re-cut cell's recorded pad is consistent with it.

600 dpi, 678 cells, `RESULT: PASS`:

| page | cut as | derivation says | consistent with it | inconsistent with the other | derivation's own "wrong frame" |
|---|---|---|--:|--:|--:|
| Beethoven 5 / Litolff scan p1 | pipeline | pipeline | 192/192 | 112/192 | — |
| " | orchestral | orchestral | 192/192 | 112/192 | 112 (pipeline arm) |
| Brahms 1 engraved fixture | pipeline | pipeline | 147/147 | 133/147 | — |
| " | orchestral | orchestral | 147/147 | 133/147 | 133 (pipeline arm) |

⚠️ **The last two columns are equal on both pages and in both directions — but
this is NOT an independent second witness, and an earlier draft of this file
overclaimed it as one.** The pad *causes* the crop height, which causes the
canonical scale, which causes `cell_canonical_w/h` and the staff-line ys. The
field is that cause recorded; the derivation is the same cause observed through
its effect. There is one underlying fact and one causal path, so the two
**cannot** disagree about *which* cells differ between modes unless one of them
is broken — the agreement is a consistency check, not corroboration by a second
source.

What it is still worth having: they are genuinely **different computations over
different data** — two floats against three geometric arrays, through separate
code — so either could break without the other, and the agreement rules out a
class of bug in each (a pad recorded from the wrong side, a `grown()` branch
that does not match the crop actually taken, a derivation that matches frames
by accident).

The remaining 80 / 14 are cells grown to the ceiling on **both** sides, where
the modes are genuinely indistinguishable. ⚠️ Note what the field does there:
it records `6.0`, which is true under either mode and **does not flag itself as
undecidable** — a consumer must already know. That warning now lives in
`types.py`, where a consumer will look. Measured per-page pad pairs, both cut
by the pipeline at 600 dpi:

| page | (6,4) | (4,4) | (4,6) | **(6,6) — undecidable** | total |
|---|--:|--:|--:|--:|--:|
| Beethoven 5 / Litolff p1 | 32 | 48 | 32 | **80** | 192 |
| brahms-sym1-mvt1 | 42 | 49 | 42 | **14** | 147 |

**Four distinct pad pairs on one page** is a sharper demonstration of
"per-cell, not per-module" than the top-staff example above, and 192 − 80 = 112
and 147 − 14 = 133 reconcile the table exactly.

## Byte-identity — `probe/run_arms.py` + the audit's `compare_arms.py`

One scanned page (Beethoven 5 / Litolff 1870 p.1, bitonal 600 ppi) and one
engraved fixture (`brahms-sym1-mvt1`), `--no-direction-text --no-contextual`.
Comparator reused from `benchmarks/omr-pipeline-audit-2026-09/probe/`.

**Control first** (two `before` arms of the same tree): PASS, both pages
byte-identical, 0 keys moved. So the harness is deterministic on these pages
and a difference in the real A/B would have been attributable.

**before vs after:** PASS.

| page | MusicXML | staves / measures | pre-existing JSON keys changed | new JSON keys |
|---|---|---|--:|--:|
| engraved-brahms1 | byte-identical, 165 617 B | 21 / 147 unchanged | 0 | **0** |
| scan-beethoven5-litolff-p1 | byte-identical, 64 552 B | 12 / 192 unchanged | 0 | **0** |

## ⚠️ The field does NOT reach the result JSON

Checked rather than assumed, as the barline-evidence work required: `grep -c
pad_above_staff_lines` over both arms' result JSON returns **0**.

`transcribe.py:4527` builds each measure dict from an explicit key list —
`bbox_page_px`, `staff_line_ys_canonical`, `upscale_factor`, and nothing
generic — and every other serialiser of a cell (`run_pipeline.py`, the four
`annotate/select_*.py` manifest writers) is the same shape. None of those files
is owned by this change, so the field was not wired into any of them.

**So its consumers today are hypothetical.** It has in-process value — anything
holding a `MeasureCell` can now ask what pad it was cut at instead of inferring
it — and zero reach past the process boundary. Giving it reach means adding a
key to `transcribe`'s measure dict and to the manifest writers, which is a
separate decision with a separate blast radius (a manifest gains a key that
`recut_cells` could then read directly).

## Red-first mutations

`tools/omr/tests/test_measure_cell_pad.py`, 5 tests. The fixture crowds its
staves ~5 spaces apart on purpose: an interior staff then grows on **neither**
side while the top staff grows above and **only** above, so one page yields
cells whose pad differs between the two sides of the same cell. A page of
well-spaced staves (every side at the ceiling) could not detect the bug at all
— which is why `test_the_fixture_crowds_its_staves` asserts the crowding before
anything else does.

| mutation | result |
|---|---|
| populate from `PAD_ABOVE/BELOW_STAFF_LINES` (the module constant) | **3 failed** |
| swap above/below at the constructor | **3 failed** |
| omit both fields, leave the `None` default | **4 failed** |
| spread the staves so both sides grow (fixture drift) | **4 failed**, the crowding guard first |

Also run: `test_recut_cells_e2e.py`, `test_left_edge_split_e2e.py`,
`test_measure_extractor.py`, `test_recut_cells.py` — 104 passed.
