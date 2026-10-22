# The GATHER sequence — what runs, in what order, and which orderings are real

**Date:** 2026-10-06. **Path:** STAGED (`tools/omr/staged/gather.py`,
`pipeline.py`). **Authority:** the body of `gather.gather()` and its
docstring. This document is a reading of the tree on that date; where it
and the tree disagree, the tree is right (CLAUDE.md rule 10). Re-derive the
dependency table with the snippet in §4 before trusting it.

Written for Sean's question of 2026-10-06: *"make a simple list of
everything that happens in the gather process and in what order"*, then
*"should the clef and page headers happen sooner? does order matter?"*
The answers are §1, §2 and §3; the change they led to is §5 (ROADMAP 2.58).

---

## 1. The sequence

### Before GATHER — page preparation (`pipeline.prepare_pages`)

1. Render each PDF page (`preprocessing.render_page`, 600 dpi on the CLI).
2. Detect staves and group them into systems (`staff_detector.detect_staves`).
3. Cut the page into measure cells (`measure_extractor.extract_measures`).
4. Make a second copy of every cell with the staff lines erased
   (`staff_line_removal.remove_staff_lines`). The detector reads the
   original; the classical-CV readers read the erased one. Never the other
   way round — erasing before the detector costs 7–13 reading points (§9).

### GATHER — once per page, in this order (`gather.gather`)

The **reads** column is what the step reads *off the record* that an earlier
step filed. A blank means it reads only the raster and the `detections`
map. Those blanks are the steps whose position is free.

| # | step | function | reads (from the record) |
|---|---|---|---|
| | *facts that do not come off this page* | | |
| 1 | External facts — dossier and roster, with a quality tier | `gather_external` | |
| 2 | Document identity — which printing this is (once per document) | `gather_document_identity` | |
| 3 | Movements — the `--movements` spec (once per document) | `gather_movements` | |
| 4 | Input domain — scan or engraved, off the PDF container (once per document) | `gather_input_domain` | |
| | *page structure* | | |
| 5 | Geometry — staff lines, spacing, extent, bracket blocks; builds the page→system map | `gather_geometry` | |
| 6 | Systems — what system grouping saw | `gather_systems` | geometry |
| 7 | Measures — barline columns, measure count per staff | `gather_measures` | geometry |
| 8 | Printed bar numbers — Tesseract on the numeral above each system | `gather_printed_bar_numbers` | geometry |
| | *the detector* | | |
| 9 | Detection — YOLO cell by cell, one row per box | `gather_detections` | geometry |
| 10 | Empty-bar whole-rest search — ink search in a bar with no notehead/rest box (**moved here 2026-10-06**, was step 23) | `gather_empty_bar_rest_search` | detections |
| 11 | Low-confidence rescue — second detector pass at 0.10, notehead/rest only, guided by stems/ties/accidentals; **appends to `detections` in place** | `gather_lowconf_rescue` | `Q.EMPTY_BAR_REST_SEARCH` |
| | *measurements hung off the detections* | | |
| 12 | Notehead re-centre — matched-window search per regular head | `gather_notehead_recentre` | |
| 13 | Notehead staff positions — clef-free | `gather_notehead_positions` | |
| 14 | Accidental positions | `gather_accidental_positions` | |
| 15 | Ownership evidence — both candidates of every cross-staff contest | `gather_ownership_evidence` | `Q.NOTEHEAD_RECENTRE` |
| 16 | Rhythm marks — flags, dots, tuplet markers | `gather_rhythm_marks` | |
| 17 | Glyph families — rests, arcs, articulations, fermatas, ornaments | `gather_glyph_families` | |
| 18 | Dynamic letters | `gather_dynamic_letters` | |
| 19 | Wedge boxes — detector and CV hairpins | `gather_wedge_boxes` | |
| | *classical CV on the erased image* | | |
| 20 | Stems and beams | `gather_cv_lines` | `Q.NOTEHEAD_RECENTRE` |
| 21 | Ink — one summary row per cell of every connected component | `gather_ink` | |
| 22 | Ledger ink — second witness under every ledger glyph | `gather_ledger_ink` | |
| 23 | Notehead ink — is the head itself filled | `gather_notehead_ink` | `Q.NOTEHEAD_RECENTRE` |
| 24 | Stacked-head fit | `gather_stacked_head_fit` | `Q.STEM` |
| 25 | Notehead/stem cross-ink — the tremolo-slash witness | `gather_notehead_stem_cross_ink` | `Q.STEM`, `Q.BEAM_STROKE` |
| 26 | Far-head ledger positions — position counted off the head's own ledgers | `gather_far_head_ledger_positions` | `Q.NOTEHEAD_STAFF_POSITION`, `Q.NOTEHEAD_STEM_CROSS_INK` |
| 27 | Detector beams — kept beside the CV strokes | `gather_detector_beams` | |
| | *page-header readers* | | |
| 28 | Clef — the detector's opinion per staff | `gather_clef` | |
| 29 | Clef locator — the CV C-clef locator | `gather_clef_locator` | |
| 30 | Clef seed — the dossier's clef, if supplied | `gather_clef_seed` | external facts |
| 31 | Key signature — accidental positions and which clefs they fit | `gather_key_signature` | `Q.CELL_STAFF_SPACE` |
| 32 | Meter — in the header, per staff | `gather_meter` | |
| 33 | Meter at mid-staff bar heads (off by default) | `gather_meter_at_bars` | |
| 34 | Meter OCR at mid-staff bar heads (off by default) | `gather_meter_ocr_at_bars` | |
| | *words* | | |
| 35 | Margin labels — PDF text layer → Surya → Tesseract | `gather_margin_labels` | |
| 36 | Direction words — Surya again; erases every detection from the mask first | `gather_direction_words` | detections |
| | *last* | | |
| 37 | Family positions — a position row for every mark (off by default) | `positions.gather_family_positions` | hairpin and direction-word rows |

### After the last page

38. Finish far-head positions — a page still held has no head size to read
    with; it abstains (`no_page_shape`) and is counted.
39. Freeze the log. Nothing is written after this; ADJUDICATE starts here.

One Surya worker is opened for the whole gather (`run_staged_on`), so the
model loads once, not once per page.

---

## 2. Does order matter?

GATHER decides nothing. A step's position matters in exactly two cases:

1. it **reads a row** an earlier step filed (`log.rows(Q.X, …)`), or
2. it **walks state** an earlier step mutated — today only `detections`,
   which the rescue appends to in place.

Everything else is kinship: the comment "beside `gather_ink` because it
reads the same erased raster" is a note to the reader, not a constraint.
Steps 12–19 read the detections; steps 20–27 read the erased raster; the
header readers read the header crop. Any of those could sit elsewhere after
step 9 and the record would not change by a byte.

⚠️ The failure mode when order is wrong is **silent**. `Log.rows()` on a
quantity nobody has filed returns an empty tuple, not an error. A reader
placed above its producer reads "nothing there" and proceeds as if that
were the answer. This is why the dependency column exists and why the one
misorder found (§5) now raises.

---

## 3. Should the clef and header readers run sooner?

No. **Nothing in GATHER reads `Q.CLEF`.**

- Notehead positions (step 13) are deliberately clef-free: a fractional
  staff position kept as measured, with the clef applied in EVALUATE
  (`restate_pitch`). That is the architecture's central claim, stated in
  `gather_notehead_positions`' own docstring.
- The key-signature reader (step 31) does not ask for a clef; it fits every
  clef's slot table and records which ones fit.
- The clef's consumers — `adjudicate_clef`, `restate_pitch`, the key-fit
  consumer — are all after the freeze.

Moving steps 28–34 to just after detection would reorder the record and
change nothing downstream. The only argument for it is that a human reads
the header first, and this stage is filing, not reading in that sense.

---

## 4. How to re-derive the dependency table

The table in §1 was produced by this and should be reproduced, not copied,
the next time anyone asks. It walks every `log.rows(...)` call in each
reader and the module-level helpers it calls, and prints the `Q.*` names
inside them.

```python
import ast, re
src = open("tools/omr/staged/gather.py").read()
t = ast.parse(src)
funcs = {n.name: n for n in t.body if isinstance(n, ast.FunctionDef)}

def helpers(fn, seen=None):
    seen = seen or set()
    for node in ast.walk(funcs[fn]):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) \
                and node.func.id in funcs and node.func.id not in seen:
            seen.add(node.func.id); helpers(node.func.id, seen)
    return seen

# the call order, read off gather()'s own body
order = [n.func.id for n in ast.walk(funcs["gather"])
         if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
         and n.func.id.startswith("gather_")]
for fn in order:
    reads = set()
    for b in {fn} | helpers(fn):
        for node in ast.walk(funcs[b]):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
                    and node.func.attr in ("rows", "refusals"):
                reads |= set(re.findall(r"Q\.([A-Z_]+)",
                                        ast.get_source_segment(src, node) or ""))
    print(f"{fn:36s} {sorted(reads)}")
```

Run on 2026-10-06 after the change it reproduces §1's column exactly, with
the rescue's read now pointing forward. Three steps read their OWN quantity
(`gather_document_identity`, `gather_movements`, `gather_input_domain`):
that is the once-per-document guard, not a dependency on anyone else.

What it cannot see: a reader that reads another's row through a different
accessor, a reader that reads mutated cell state (`cell.image_no_staff`,
`detections`), and anything in `positions.py`. Those three edges are known
by their call-site comments; a new one would need a new comment.

This is not a committed check (CLAUDE.md §6c limits source-text
assertions; a "gather-shape check" is the one allowance and nobody has
claimed it yet). If it becomes one, it needs a ROADMAP line and
registration in `reach.NOT_A_STAGE`.

---

## 5. What was found, and what changed (ROADMAP 2.58, commit `286289dd`)

**Found.** `gather()`'s docstring and `ASSUMPTIONS.md` A-GATHER-1 both said
"only three steps of the order are forced". The table in §1 shows about
eleven. Each later roadmap item (2.39b re-centre, 2.42 stacked heads, 2.49
tremolo, 2.52/2.55 rest search and rescue, 2.56 far heads) added a reader
that reads an earlier reader's row and said so in its own call-site
comment, while the summary kept saying three. A stale sentence like that
reads as a licence to reorder.

**One edge ran backwards.** The low-confidence rescue (then step 10) needed
to know whether the whole-rest search had already found a rest in the bar,
and the search ran at step 23. The rescue covered the gap by re-running the
search on a throwaway `Log()` and reading that. So the search ran twice on
every candidate bar, and the rescue read a scratch copy the record never
held.

**Changed.**

- The rest search runs directly after detection, before the rescue (steps
  10 and 11 above). This is also the order Sean gave on 2026-10-01: look
  for the whole rest in the middle of the bar first; rescue only a bar that
  has none.
- The rescue reads `Q.EMPTY_BAR_REST_SEARCH` off the real log. The scratch
  re-run is deleted.
- `GatherOrderError` (`gather.py`): the rescue raises if a candidate bar
  holds neither a search row nor a search refusal with ink on — the only
  way that happens is the rescue running before the search. With ink off
  (`OMR_INK=0`) the search files nothing by design and the rescue proceeds
  on every candidate, as it always did against the empty scratch log. A
  control that can fail (rule 7); its test was run RED against the previous
  `gather.py`.
- The one record change: a rescued bar now carries its `found=False`
  search row *beside* its rescued boxes. Before, the search ran after the
  rescue and skipped the bar as no longer boxless, so the record never said
  the search had looked. `adjudicate_empty_bar_whole_rest` abstains on a
  `found=False` (additive, never a gate), so the two do not contest.
- The clef and header readers did not move (§3).
- `gather()`'s docstring now states the rule (§2) and lists the edges,
  dated, with the instruction to re-derive them. A-GATHER-1 is marked
  falsified with the history (the design brief said two edges, verification
  found three, the tree held eleven). CLAUDE.md §4b carries one clause.

**Evidence.** Fast tier 4,545 passed / 0 failed. `staged.check` 247,
`open-findings.json` unchanged. One existing test narrowed
(`test_no_detector_is_a_supported_no_op` asserted an empty log; the search
now legitimately files there, so it asserts the *rescue* filed nothing).

**Not yet priced.** This is a GATHER change, and nothing in `check` sees a
GATHER change (CLAUDE.md §4d). The next full re-gather is what prices it.
Expected delta: exactly the added `found=False` rows on rescued bars (24
kept rescues on Litolff pp.1–3 by 2.55's own count, 0 on Brahms pp.0–1),
and no verdict change anywhere. A verdict that moves is a finding.
