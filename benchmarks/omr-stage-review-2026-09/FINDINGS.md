# The STAGE REVIEW — roadmap 3.4

**Date:** 2026-09-23. **Path:** STAGED. Two lanes on one contract, the
review-actions sidecar (`tools/omr/staged/review/`).

Sean's design, his words (ROADMAP 3.4, DECISIONS 2026-09-23):

> *"a UI where it pulls up a staff on a system and shows me everything it is
> gathering — I give feedback by redrawing, deleting or adding boxes — then
> the next stage, you tell me what the stage is doing with that information
> and I give feedback on what is working and what isn't — each stage at a
> time, following the trail of information and decisions with human
> feedback."*

And the purpose, which is not *correct the score*:

> *"I mainly want this information so that we can then use it to determine
> how to refine the build, rules and decisions — structurally. All of the
> info would be given to you to turn into fixes."*

§A is lane (A)'s: `human_evidence.py`, `rerun.py`, `feedback.py` — the
sidecar ingested as human WITNESSES, ADJUDICATE→EXPORT re-run off the saved
record, the feedback file a session reads. §B is lane (B)'s: the viewer.

---

# §B — the viewer

`tools/omr/staged/review/server.py` + `static/`. FastAPI + uvicorn on
127.0.0.1:5060, plain HTML/JS/CSS, no build step, light theme, laid out for a
1440-px window.

## The one command

```
python3 -m tools.omr.staged.review.server \
  --record library/_shared-records/beethoven5-litolff-mvt1-whole-20260923.record.json \
  --pdf    library/editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf \
  --staff  staff/3/0/9
```

Then open `http://127.0.0.1:5060/?staff=staff/3/0/9`.

Start-up is **8 s** on the 314 MB record (3.6 s to load, 2.6 s to export, the
rest to index); it holds about 2.5 GB resident and answers every view from
memory afterwards (ADJUDICATE 1.1 MB in 44 ms; the other views in 3 ms).
`--no-serve` loads, runs the control, prints the head of the pick list and
exits — the cheapest way to check a record before opening a browser.

## What it shows, on `staff/3/0/9` (the Litolff p3 Viola)

Every view answers the same two questions in the same layout: **what did this
stage READ** on the left, **what did it DECIDE** on the right.

### Pick

One row per staff-system in the record — page, system, ordinal, part name,
the clef verdict with its outcome and reason, heads boxed / written / **lost**
and the refusal buckets — ordered by heads LOST descending, filterable by
page. 331 staves.

⚠️ **`staff/3/0/9` is FIRST ON PAGE 3 and THIRTEENTH over the whole document,
and the brief expected it first.** The notehead-funnel benchmark measured one
page; the pick list measures all sixteen. Reported as measured:

| rank | staff | part | clef | boxed | written | lost | top bucket |
|---|---|---|---|---|---|---|---|
| 1 | `staff/12/1/2` | Clarinet | narrowed | 66 | 0 | **66** | `no_pitch` x53 |
| 2 | `staff/2/1/9` | Viola | abstained | 63 | 0 | **63** | `no_pitch` x53 |
| 3 | `staff/6/0/7` | Viola | narrowed | 63 | 0 | **63** | `no_pitch` x49 |
| 4 | `staff/14/1/7` | ? | decided treble | 63 | 0 | **63** | `staff_not_identified` x52 |
| 5 | `staff/10/0/9` | Viola | narrowed | 59 | 0 | **59** | `no_pitch` x46 |
| ... | | | | | | | |
| 13 | `staff/3/0/9` | Viola | **abstained** | 48 | 0 | **48** | `no_pitch` x40 |

⚠️⚠️ **THE LIST ANSWERS THE QUESTION THE FUNNEL BENCHMARK ASKED FOR.** That
benchmark's closing paragraph reads: *"A roadmap item that hunts for a staff
with boxes and zero written would have surfaced this without anybody looking
at the page."* Sorting 331 staves by heads lost does exactly that, and the
answer is **37 staves box noteheads and write none of them**, and **24 staves
carry a `no_pitch` refusal** — not one, as page 3 alone suggested. Document
totals: **11,632 notehead boxes, 7,558 placed, 4,074 lost (35 %)**. This is a
POINTER, not a diagnosis; nothing here says those 37 have one cause, and the
top five split between `no_pitch` (an unread clef) and `staff_not_identified`
(an unnamed slot), which are different repairs.

### GATHER

The staff-system crop cut from the PDF at the record's own dpi (600), served
as a plain raster with the overlays drawn in the browser so they can be
toggled and clicked. On the Viola: crop `[295, 1689, 2663, 1973]` page px at
zoom 2 (4736 x 568), **frame control PASSED, contrast 152.51** — the same
number `crop_funnel.py` prints, because `_frame_ok` is IMPORTED from
`omr-infer-duration-print-2026-09/probe/crop_inferred.py`, not copied.

Overlays, each its own checkbox: `Q.STAFF_LINES` (green, so the crop says
WHICH staff it is about — Sean's own correction of 2026-09-23),
`Q.CELL_BOX` with printed bar numbers, every detector box coloured by family
(notehead / rest / clef / key / accidental / other) with class and confidence
on click, and the `Q.INK` summary. On this staff: **121 boxes — 48 notehead,
56 other, 8 accidental, 7 rest, 2 key**; 16 cells, bars 48–63 (the FILE's
numbering, one behind the print's 49–64 — exactly the off-by-one the funnel
FINDINGS records); 82 ink components over 16 cells.

**The two notehead boxes on the alto clef are visible, and they are what the
whole item is about**: `glyph/3/0/9/0/1` conf 0.642 at page px
`[388.5, 1828.2, 415.1, 1850.1]` and `glyph/3/0/9/0/6` conf 0.364 at
`[388.2, 1828.7, 415.8, 1861.6]`, both refused `no_pitch`. See
`out/gather-staff-3-0-9-cells0-1.png`: two red rectangles sitting on the
C-clef.

Actions: click a box then delete (with a note); drag a rectangle to add one
(category from `class_aliases`' canonical list, grouped by family); "Redraw
this box" then drag to redraw. Every action is appended to the sidecar
immediately and drawn in magenta; **the machine's box stays visible, struck
through if deleted** — a correction is a witness beside the machine's row,
never an erasure of it. A box with no `bbox_page_px` is reported as DECLINED
and is neither drawn nor redrawable.

⚠️ **A GATHER ACTION IS REFUSED WHERE THE FRAME CONTROL FAILED OR COULD NOT
RUN** (HTTP 409). A box drawn on a raster that is not the record's is not
evidence, and a caveat under a picture is not a control. Agree/disagree is
unaffected — that is about a verdict, not about a pixel.

### ADJUDICATE

The staff's own subject first, then its system, then its cells, then a
clickable table of all 121 glyphs. Every verdict is a card: quantity,
outcome, value, reason, `decided_by`, the rows it READ rendered as
**reader x quantity x value x score**, the basis, `used`/`considered`,
missing / declined / excluded, candidates with support, and any supersession
with its direction. Abstentions get the same card with their reason word.

All seven staff-level verdicts on the Viola:

| quantity | outcome | value | reason | used/considered |
|---|---|---|---|---|
| `staff_group` | decided | 2 | `bracket_block` | 1/1 |
| `measure_partition` | decided | 16 | `read` | 1/1 |
| `staff_ordinal` | decided | 9 | `read` | 1/1 |
| `instrument` | **abstained** | — | `no_evidence` | 0/0 |
| `slot_index` | **narrowed** | — | `family_block_not_forced` | 2/389 |
| **`clef`** | **abstained** | — | **`no_candidates`** | **0/5** |
| `key_signature` | **abstained** | — | `needs_clef` | 0/1 |

and all seven abstentions with their detail intact — `clef_glyph`
`no_detections`; **two `clef_located` `occupied` rows carrying their cluster
geometry** (`spacing_px 22.0`; clusters `2.09 x 4.5` and `3.36 x 4.5` spaces
at `x 2.68 / 2.05, y 4.36`), the exact numbers roadmap 2.11 is built on, now
readable without a script; `meter_glyph` `no_detections`; `meter_template`
`below_threshold` with all 21 template scores and the 0.5 floor;
`margin_label` `no_ink` with its rung ledger; `wedge_box` `no_ink`.

Glyph outcomes on this staff: **62 decided, 33 abstained, 3 narrowed**.

### EVALUATE

Nine glyphs on this staff carry a consequence — **six `move_glyph` pitches
and three `size_measure_rest` durations** — each with its cause-to-effect
chain and the superseded row's prior value and direction.

⚠️ **AN OBSERVATION THE VIEWER SURFACED ON ITS FIRST USE. NOT INVESTIGATED,
AND NOT A CLAIM OF HARM.** All six pitches are `move_glyph`, reason
`reowned`: `glyph_owner` gave the ink to `staff/3/0/8` (Violino II, reason
`distance`) and the pitch was re-derived from THAT staff's clef — which is
why a staff whose own clef abstained has any pitch at all. Three of the six
are not noteheads: `glyph/3/0/9/1/6` is a `ledgerLine`, `glyph/3/0/9/6/2` an
`accidentalNatural` and `glyph/3/0/9/14/2` a `dynamicP`, and each now carries
a `Q.PITCH` of `G3` or `F3`. They are `never_asked` at EXPORT
(`_place_notes` skips a row with no `notehead_class`), so nothing reaches the
file — but *`move_glyph` re-derives a pitch for every re-owned glyph, not
only for noteheads* is a fact about the rule a session may want to price. It
was found by clicking one staff, which is what the page is for.

The three consequences that do reach the file are the whole rests,
`whole_rest_means_the_bar` — on this staff, EVALUATE's only contribution to
the output is the measure-rest convention.

### INFER

Every inferred value on the staff, labelled INFERRED, with its rule, that
rule's own flag and whether the flag is on, its `forbids_argmax`, its bound,
and **the candidates of the verdict it collapsed**. On the Viola: **one
inference** — `slot_index = 9` by `collapse_slot_index_to_family_block`
(`OMR_SLOT_FAMILY_BLOCK` = ON), collapsing a NARROWED verdict that carried 2
candidates. The two duration rules (`OMR_INFER` = ON since `6f269360`) reach
nothing here, and the page says **REACH ZERO, not agreement**.

### EXPORT

Per head: written — with the `<note>` it became (step / alter / octave / type
/ dots) — or refused under its named bucket, beside our Verovio render of the
same bars. The render is `build_sidebyside.slice_measures` + `render_svg`,
imported from the count-pages build so the slice carries attributes forward
the same way theirs does; it ABSTAINS with a reason rather than drawing an
empty stave.

On the Viola: part **P10 "Viola"**, measures **48–63**, 22 KB of SVG, and

* **48 notehead rows, 48 refused, 0 written**, buckets `no_pitch` x40,
  `not_a_notehead:clipped_fragment` x3, `owned_by_another_staff` x3,
  `not_a_notehead:too_narrow` x1, `ink_is_a_whole_rest` x1;
* 73 other glyph rows — 7 written (the whole rests), 66 never asked.

Those are `benchmarks/omr-notehead-funnel-2026-09/FINDINGS.md`'s Table 1
numbers, bucket for bucket, and a slow test asserts them
(`test_stage_review_real_record.py`).

### Sidecar, re-run, feedback

The right rail shows every action as it is saved, with a cross to take one
back, and the file's path
(`benchmarks/omr-stage-review-2026-09/out/review-actions--staff-3-0-9.json`
by default; `--sidecar` overrides). The re-run button shells out to lane
(A)'s `python3 -m tools.omr.staged.review.rerun <record> <sidecar> --out
<dir>` and shows its exit code, its output, and any feedback file it wrote.
**Lane (A) is not in this tree**, so the button reports *"re-run not
available in this tree ... The sidecar IS saved: <path>"* and nothing is
faked. A smoke pass over the running server wrote one of each action kind;
the file matched the contract exactly and was then deleted rather than
committed — a smoke test is not Sean's reading.

## The controls, and they can fail

1. **The refusal decomposition is the EXPORTER's.** `run_export` wraps
   `_parse_subject` / `_place_notes` at run time — `funnel.py`'s move, for
   `funnel.py`'s reason — and files each `_drop` under its glyph. At start-up
   the per-subject log is summed and compared to
   `report["notes_not_written"]`; a mismatch **raises `ControlFailed`** and
   the server does not start. `--break-control` drops one logged refusal on
   purpose and was run that way first: it raises, naming the disagreement.
   The patches are restored in a `finally`, so no later export in the process
   reports through the viewer.
2. **The frame control is imported, not copied**, and it GATES the GATHER
   actions rather than annotating them.
3. **Two mutation arms, run before the tests were believed** (both reverted):
   * `to_page` with the zoom dropped, so it is a bare translation:
     `test_crop_to_page_is_computed_by_hand` and `test_round_trip_both_ways`
     FAIL. A round trip alone would not have caught it, which is why the
     expected crop coordinates are computed BY HAND from a frame whose origin
     is not 0 and whose zoom is not 1 — this repo has paid once already for
     two frames that were indistinguishable on a fixture starting at 0.
   * `validate_action` relaxed to `return action`:
     `test_it_refuses_what_the_contract_forbids` FAILS on all nine cases. Its
     positive control is `test_round_trip_every_kind`, which writes one of
     every kind and has every one accepted, so it cannot pass by refusing
     everything.
4. **`reach --check` caught the package before it was registered** — exit 1,
   `⚠️ UNREGISTERED MODULE review/server.py`. The line was then added to
   `NOT_A_STAGE`; a test asserts `unaccounted_modules() == []`.
5. **`wiring --check` caught the viewer CLOSING A GAP.** One COMMENT in
   `server.py` named `Q.DIRECTION_WORD.gate`; the bare-name detail scan read
   it as a consumer, that live `KNOWN_GAPS` entry reported STALE, and
   `staged.check` went 70 problems to 69. `server.py` now declares
   `DERIVED_CHECK = True`, for the reason `wiring.py` already excludes a gap
   list, a test, a benchmark probe and an auditor: **naming a key is not
   consuming it, and a page that only SHOWS a quantity to a human must not be
   able to close a gap.** Measured both ways — with the package moved aside,
   70 problems / 0 stale; with it plus the marker, 70 / 0.

## Gate

* `pytest tools/omr/tests -m "not slow" -q` → **2,851 passed, 3 skipped, 0
  failed** (main's 2,823 plus this lane's 28 fast tests). ⚠️ The first
  write-up of this line said 2,844 — the figure measured BEFORE the seven
  app-level tests were added in response to the two start-up faults below.
  Corrected by re-running, not by arithmetic.
* `pytest tools/omr/tests/test_stage_review.py -m "not slow" -q` → **28
  passed** in 1.4 s.
* `pytest tools/omr/tests/test_stage_review_real_record.py -q` → **4 passed**
  in 8.2 s. It SKIPS where the shared record is not on the machine, and a
  skip is reported as a skip.
* `python3 -m tools.omr.staged.check` → **255 open, every check
  `status=ok`** — identical to main.

⚠️ **TWO FAULTS THAT EVERY GREEN TEST MISSED, AND WHAT WAS ADDED BECAUSE OF
THEM.** Both were found by actually starting the thing, and both are now
covered.

* `from __future__ import annotations` + FastAPI: a route's `-> HTMLResponse`
  return annotation and a `Request` parameter annotation are resolved by
  pydantic in the MODULE namespace, and both names were imported INSIDE
  `create_app`. The app raised `PydanticUndefinedAnnotation` when it was
  BUILT — after every view function had been called and had passed. Fixed by
  importing FastAPI at module level; `TestTheAppItself` now builds the app
  and hits every route. **A test that calls the view functions is not a test
  that the app serves them.**
* `app.js` shipped with an unbalanced parenthesis in the pick list: 27 green
  Python tests, a server that served the file, and a page that would have
  rendered nothing. `TestTheStaticPageParses` now runs `node --check`,
  skipping where node is absent.

## What it cannot do yet

1. **No browser screenshot was taken.** This session's environment refused to
   navigate to `127.0.0.1:5060` (and the Chrome extension did not answer), so
   the page was verified through its API — every endpoint by `curl`, with the
   payloads quoted above — and the GATHER overlay was rendered from the
   server's OWN `/api/gather` payload by `probe/render_gather_overlay.py`
   into `out/`. That proves the payload lands on the ink; it does not prove
   the page's CSS looks right at 1440 px. **Sean is the first person who will
   see the page rendered.**
2. **`heads_written` is not the file's `<note>` count, and the two were not
   reconciled.** It counts notehead boxes `_place_notes` placed into a `Cell`
   (7,558 document-wide); the exporter's own `written["notes"]` is 7,878 and
   is counted after the join, including 479 condensed doubles. The difference
   was not chased. Every per-staff REFUSAL figure IS the exporter's own and
   is controlled against it.
3. **One staff per sidecar**, because the contract carries one `staff` key. A
   second staff opens a second file rather than giving that key a second
   meaning.
4. **A verdict's rows are truncated at 60 in the payload**, MARKED with the
   number withheld, with the verdict's own `used` / `considered` / `basis`
   counts beside it untouched. Without it, one ADJUDICATE payload for this
   staff was 5.8 MB (`arc_owner` considers ~1,800 rows and a staff carries
   hundreds of verdicts).
5. **The EXPORT view's agree/disagree files the GLYPH subject in `verdict`**,
   not a verdict id — a written note is not a verdict row, and inventing an
   id for it would be worse. Lane (A) reads `stage: "export"` to tell the two
   apart.
6. **Nothing here re-decides.** There is no "apply" button and no path from
   the sidecar into the record inside this lane. That is lane (A)'s job and
   the whole point of the split.
7. **GATHER is blind in exactly the way the record is** (CLAUDE.md §4d): it
   shows what the DETECTOR drew. A head the detector never fired on has no
   subject and no box, and the only way to say so is Sean drawing one.
8. **The pick list is computed from one export pass at start-up.** A record
   is a snapshot of the reader that made it, and this one is from a DIRTY
   tree (`provenance.dirty: true`, commit `dbc9962b`) — per §4b it is not a
   baseline, and the page says so in its header.

## The contract with lane (A)

The sidecar is exactly the shape the brief fixed, with optional fields only,
each documented in `server.OPTIONAL_FIELDS` and served at `/api/session`:
`note`, `quantity`, `outcome`, `value`, `prior_bbox_page_px`, `cell`,
`crop_px`. `bbox_page_px` is PAGE pixels at the record's own dpi; `crop_px`
carries the same rectangle in the crop's own pixels beside it, so the
conversion can be re-checked from the file alone. `cell` is filed only where
the rectangle falls inside exactly one `Q.CELL_BOX` and is left out
otherwise, never guessed.

## What is committed here

```
FINDINGS.md                          this file (§B)
probe/render_gather_overlay.py       the overlay rendered from the server's own payload
out/gather-staff-3-0-9-cells0-7.png  bars 48-55, all four overlay layers (+ .json)
out/gather-staff-3-0-9-cells0-1.png  the header: the two notehead boxes ON the alto clef
```

The record (314 MB), the edition PDF and the crop cache stay out of the tree;
crops are cached to the session scratchpad, never into the repo.
