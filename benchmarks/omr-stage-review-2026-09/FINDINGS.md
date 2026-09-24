# The STAGE REVIEW — roadmap 3.4

**Date:** 2026-09-23. **Path:** STAGED. Two lanes on one contract, the
review-actions sidecar (`tools/omr/staged/review/`).

Sean's design, his words (ROADMAP 3.4, DECISIONS 2026-09-23):

review-actions sidecar (`tools/omr/staged/review/SIDECAR.md`).

Sean's design and its purpose, his words (ROADMAP 3.4, DECISIONS 2026-09-23):

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
127.0.0.1:5075, plain HTML/JS/CSS, no build step, light theme, laid out for a
1440-px window.

## The one command

```
python3 -m tools.omr.staged.review.server \
  --record library/_shared-records/beethoven5-litolff-mvt1-whole-20260923.record.json \
  --pdf    library/editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf \
  --staff  staff/3/0/9
```

Then open `http://127.0.0.1:5075/?staff=staff/3/0/9`.

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
   navigate to `127.0.0.1:5075` (and the Chrome extension did not answer), so
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

> and I give feedback on what is working and what isn't."*

> *"I mainly want this information so that we can then use it to determine how
> to refine the build, rules and decisions — structurally. All of the info
> would be given to you to turn into fixes."*

§A below is lane (A): the sidecar ingested as human WITNESSES,
ADJUDICATE→EXPORT re-run off the saved record, and the feedback file a session
reads. §B is lane (B), the viewer, and is written by that lane.

---

# §A — the evidence half

**Branch:** `claude/stage-review-evidence-3.4a`.
**Status:** built, tested, and run once end to end on the Litolff p3 Viola
staff **by a SESSION, not by Sean**. Nothing here is his adjudication.

## A1. What was built, and the one thing it connects

`tools/omr/staged/review/`, registered in `reach.NOT_A_STAGE`:

| module | question it answers |
|---|---|
| `human_evidence.py` | what does a review action BECOME on the record? |
| `rerun.py` | what do the stages DO with it, re-decided from GATHER? |
| `feedback.py` | what does a session read, without the record in hand? |
| `SIDECAR.md` | the contract with lane (B) |

**The one CONNECT.** `adjudicate_notehead_is_not_a_notehead` grows a fourth
reason, `human_not_a_symbol`, reading `Q.HUMAN_BOX_VERDICT`. It is its own
small function (`_human_not_a_symbol`) so roadmap 2.11's `is_a_clef` refusal
lands beside it rather than through it, and it is tested FIRST and OUTSIDE the
geometry gate: every other rule there abstains `no_staff_geometry` when the
cell cannot supply a unit, and a human did not measure — he looked at the
print, which is worth most exactly where the machine can say least.
`export.py` is UNTOUCHED; the refusal already buckets as
`not_a_notehead:<reason>`.

**Everything else a review pass produces is applied by nobody, on purpose.** A
stance on a verdict (`Q.HUMAN_VERDICT_STANCE`) is filed AGAINST it and read by
no stage; `reach.KNOWN_GAPS` carries the reason, and that entry does not leave
the list when something reads it — something reading it is the finding.

## A2. The subject problem, and what a human box cannot have

A glyph subject's last coordinate is an index into the detector's output for
that cell (CLAUDE.md §4b), so a box the detector never drew has no index.
Answered the way `Q.INK` already answered it: an **offset ordinal**, 400 000 —
the FIFTH base, past `gather.py`'s four (90 000 direction, 100 000 CV,
200 000 ink, 300 000 vertical runs). A test derives those four off the module
and asserts no overlap; a collision would not raise, it would silently merge a
human's box and another reader's row into one subject.

| quantity | human box | why |
|---|---|---|
| `Q.GLYPH_BOX` | yes | the cell's canonical frame is RECOVERED from that cell's own rows (`upscale_factor` and origin, inverted out of `gather._page_box`'s arithmetic), with an anchor-agreement control that can fail |
| `Q.NOTEHEAD_CLASS` | yes | when the category is a notehead class — `gather`'s own test, imported |
| `Q.NOTEHEAD_STAFF_POSITION` | yes | grid recovered from `Q.CELL_STAFF_SPACE` plus any notehead in the cell carrying both frames; two such noteheads CHECK each other |
| `Q.GLYPH_CONF` | **no** | a person produced no softmax. Writing 1.0 converts *there is no such measurement* into a definite one (CLAUDE.md rule 8) |
| `Q.GLYPH_BAND_DISTANCE`, `Q.GLYPH_LADDER` | **no** | produced by `gather_ownership_evidence` from the cell RASTER. Not derivable from rows — **so a human box never enters `glyph_owner`'s contest** |
| `Q.BEAM_STROKE`, `Q.FLAG`, `Q.AUG_DOT` | **no** | read off the cell raster by `line_detection` |

Every absence is named in `human_evidence.HUMAN_BOX_ABSENT` and reported per
action. An inventory, never a suppression list.

⚠️⚠️ **AND THE CONSEQUENCE OF THE LAST ROW IS NOT "no duration" — IT IS A
DURATION READ FROM THE HEAD ALONE, WHICH IS WORSE, BECAUSE IT IS AN ANSWER.**
Measured: a human `noteheadBlackOnLine` comes back DECIDED `written 1.0`,
reason `head_and_marks`, with the marks half of that reason contributing
nothing. Correct for a quarter note, wrong for every beamed or flagged one,
and NOTHING ON THE ROW SAYS WHICH — he drew a box, not a stem. A session
reading a review pass must treat a human box's duration as UNMEASURED rather
than as read. Pinned by a test; closing it needs a GATHER function that
re-reads the cell raster around a human box, which is 2.6-shaped and not this
lane's.

### The honest table — which stages SEE a human box

⚠️ MEASURED by running the real stages over a fixture, not predicted. A human
`add_box` receives verdicts on **exactly five** quantities, and
`test_stage_review.py` asserts that SET, so a change that starts or stops
reading a human box fails visibly with the quantity named.

| stage | decides about a human box? | which |
|---|---|---|
| GATHER | **no, and never will** | a human is not a gather rung; `capture.READER_RASTER` files him `None` because no function under `tools/omr` touches the pixels he looked at |
| ADJUDICATE (glyph scope) | **yes, 4** | `notehead_is_not_a_notehead` (the only one that WEIGHS a human `Q.HUMAN_BOX_VERDICT`), `stem_direction`, `notehead_is_a_whole_rest`, `duration` |
| ADJUDICATE (cell / system scope) | **yes, indirectly** | `event` and `voices` take the new glyph into the bar's event structure and WEIGH it; `onset_column` and `meter` are merely HANDED it |
| EVALUATE | **yes** | `restate_pitch` gives the human box a pitch from the staff's clef |
| INFER | **no** | its two duration rules declare `Q.GLYPH_OWNER`, which a human box cannot have — so a human box is structurally outside them |
| EXPORT | **yes** | written, and counted |

⚠️ `used` is not `basis` is not `considered`, and the diff reports them apart.
`Verdict.used` is what the DECISION says it weighed; `considered` is what the
HARNESS handed it. A human row in the second and not the first means the
decision was OFFERED his reading and did not use it — the structural finding
this machinery exists to collect, and the opposite of a row that did work. The
`redraw_box` test turns on exactly this: a `redrawn` row IS handed to
`notehead_is_not_a_notehead` (it declares the quantity) and is declined, so a
test asserting *nothing read it* would have been WRONG and would have looked
right.

## A3. Controls, and the ones that were watched to fail

* **An empty sidecar must reproduce the record's standing verdicts N/N AND
  write a byte-identical MusicXML.** Both halves, because reproducing the
  verdicts is not reproducing the file.
* **`--break-control` perturbs one replayed GATHER row** and was run in that
  state FIRST on the fixture. On the real record the control did not need
  perturbing to fail — see A5.
* **The per-subject export census sums back to the exporter's own
  `notes_not_written`, or the run RAISES.** The refusal buckets are
  instrumented at run time (`export._place_notes` wrapped, no edit to
  `tools/`) — the same method `omr-notehead-funnel-2026-09/probe/funnel.py`
  uses, and for the same reason: the repo has paid once for a second copy of
  the refusal rules (`omr-cleanup-count-2026-09/build_sheet.py` reported 542
  where the exporter refused 738).
* **The frame recovery REFUSES rather than averages.** Two anchors disagreeing
  about the cell origin by more than 0.5 page px, or a cell with no anchor at
  all, is refused and named — a box in the wrong frame is a measurement that
  looks exactly like a right one.
* **A human-amended record is a NEW file** whose provenance names the parent
  record's md5 and the sidecar's sha256; `rerun` refuses to write over the
  parent.
* **Tests run RED first, in two stages.** Against `origin/main` the file dies
  on `ModuleNotFoundError`. With the human test REMOVED from the adjudicator
  it is **4 failed / 36 passed**, and the four are exactly the delete's
  consequences — so those tests measure the CONNECT, not the ingest.

### Blind spots, by construction

Inherited from `readjudicate.py` and `reinfer.py` and stated rather than
discovered later: this replays ADJUDICATE→EXPORT over a FIXED GATHER, so **a
change to `gather.py` never enters the rebuild** and a green control across one
proves nothing. A human's box is not such a change — it is a row appended to
the saved record, which the rebuild does carry.

## A4. Two faults the tests found, both silent and plausible

1. **A VERDICT ID IS NOT STABLE ACROSS A RE-DECISION.** `rerun` re-runs
   ADJUDICATE from the GATHER rows, so `vrd:000029` in the arm is a different
   verdict from `vrd:000029` in the parent. Resolving a stance by id against
   the arm returned `group_symbol`/`bracket` where the clef was expected —
   wrong, and plausible. Fixed by copying the verdict AS IT STOOD onto the
   human's own row (`_what_he_was_shown`) and re-resolving against the arm by
   (quantity, subject). That is `factsheet.merge`'s `reader_said` one layer
   down, and its argument carries: a disagreement is uninterpretable without
   what was disagreed WITH, and which side is right is a further act of
   adjudication that nothing here performs.
2. **A derivation off a field that does not exist.** `_stage_of_verdict` read
   `evaluate.Rule.name`, which the class does not have, so all seven
   consequences reported as ADJUDICATE and `restate_pitch` filed a pitch under
   the wrong stage. Now derived off `RULES[*].fn.__name__`, and it RAISES on
   an empty set rather than returning one.

A third was avoided rather than found: `wiring --check`'s mention test is a
**raw-text substring scan**, so naming `Q.CELL_STAFF_SPACE`'s half-step detail
key anywhere in this package — code, docstring OR COMMENT, and even as the
SUFFIX of another identifier — reports a standing pipeline finding as CLOSED
and turns the check red. The module reads the quantity's VALUE instead, which
is what a consumer should have been reading anyway (and is the only correct
read on a one-line percussion cell). That is the fifth instance of the family
`wiring.py`'s own docstring records paying for: a gap list, a test, a
benchmark probe and an auditor, each closing a gap by naming it.

## A5. The run on the Litolff p3 Viola staff

⚠️⚠️ **A SESSION'S ACTIONS, NOT SEAN'S.** The sidecar declares reader
`session-test`, which `record.READERS` documents as NOT a human witness: it
read the RECORD, so it is correlated with every machine row it cites, in
exactly the way CLAUDE.md §10 warns about. Sean's rows would come off the
PRINT and carry reader `sean`.

Record: `library/_shared-records/beethoven5-litolff-mvt1-whole-20260923.record.json`,
md5 `7dbee148868c39634a20d5881143d3ee` — matches the committed `.md5` sidecar.
Sidecar: `out/viola-p3.sidecar.json`, sha256
`fc1a32684f5792cc6b100bdfa29fb790405aee0d9efbff3f8b3951ad632edb3d`.

Three actions, every one justified from
`benchmarks/omr-notehead-funnel-2026-09/FINDINGS.md` §"Why the clef abstained":

| id | action | justification |
|---|---|---|
| `act-0001` | `delete_box` `glyph/3/0/9/0/1` | a `noteheadBlackOnLine` at conf 0.642 on the alto C-clef's ink, page px [388.52, 1828.19, 415.14, 1850.09] |
| `act-0002` | `delete_box` `glyph/3/0/9/0/6` | the same ink boxed again at conf 0.364, [388.20, 1828.67, 415.77, 1861.58] |
| `act-0003` | `disagree` with `vrd:176187` | the staff's `clef` verdict, ABSTAINED `no_candidates` |

Both boxes' page coordinates were re-read off the record for the sidecar and
match the funnel's measurement to the pixel.

### The control, on the real record — it FAILED on today's tree, and the
### failure is fully explained

⚠️⚠️ **RUN FIRST, AND READ FIRST.** An empty sidecar on today's tree gives

    98,999 of 99,068 standing verdicts identical, 69 differ, 0 absent, 0 new
    <note> 12,375 -> 12,424     MusicXML identical: FALSE

and the tool printed its own alarm: *the sidecar was empty and the record did
not reproduce.* **All 69 are INFER `duration`** — 49 `the_neighbours_run_to_
the_same_barline`, 20 `the_neighbours_name_this_gap`.

Those are not drift. They are **exactly** the figures ROADMAP 2.3 records for
the `OMR_INFER` OFF→ON flip of 2026-09-23 (`6f269360`): *"Litolff 0→69
inferences (20 by column, 49 to barline), `<note>` 12,375→12,424."* The
record's own provenance names commit `dbc9962b…` with **`dirty: true`** — it
predates the flip, and CLAUDE.md §4b already says a record from a dirty tree
is not a baseline. So the control did the one job a control has: it caught a
TREE difference between the record and the tree replaying it, down to the
individual verdict, before any arm was read.

With the record's own tree restored (`OMR_INFER=0`):

    99,068 of 99,068 standing verdicts identical, 0 differ, 0 absent, 0 new
    <note> 12,375 -> 12,375     MusicXML identical: TRUE     CONTROL PASSED

**The replay is faithful on the real 314 MB record.** Every figure below is
taken with `OMR_INFER=0` for that reason, and the ON run is kept beside it
(`out/viola-p3.control-INFER-ON.diff.json`) because it is the more useful
artefact of the two.

### The census reproduces the funnel benchmark, from a different instrument

Before any action, on `staff/3/0/9`:

| bucket | this tool | `omr-notehead-funnel-2026-09` Table 1 |
|---|---|---|
| `no_pitch` | 40 | 40 |
| `not_a_notehead:clipped_fragment` | 3 | 3 |
| `not_a_notehead:too_narrow` | 1 | 1 |
| `ink_is_a_whole_rest` | 1 | 1 |
| `owned_by_another_staff` | 3 | 3 |
| **refused total** | **48** | **48** |
| noteheads written | **0** (7 rests) | **0** |

Two instruments, written independently, agreeing head for head on a staff
that loses all 48 of them. That is the positive control this arm needed and it
was not designed as one.

### The arm

    99,066 of 99,068 standing verdicts identical, 2 differ, 0 absent, 0 new
    3 actions, 3 rows filed, 0 refused, 0 frames refused, 0 grids refused

**Both differences are the two deleted boxes, and each names its human row:**

| subject | before | after |
|---|---|---|
| `glyph/3/0/9/0/1` | `decided False` (`notehead`) | **`decided True` (`human_not_a_symbol`)** |
| `glyph/3/0/9/0/6` | `decided False` (`notehead`) | **`decided True` (`human_not_a_symbol`)** |

Both are `how: "used"` — `adjudicate_notehead_is_not_a_notehead` WEIGHED the
human row, it did not merely receive it. Per stage: ADJUDICATE 2 verdicts
naming a human row, 2 of them weighing it; EVALUATE 0; INFER 0.

**The staff census, after:**

    no_pitch 40 -> 38
    not_a_notehead:human_not_a_symbol 0 -> 2
    refused total 48 -> 48     noteheads written 0 -> 0

⚠️⚠️ **AND THE MUSICXML IS BYTE-IDENTICAL: `<note>` 12,375 → 12,375.** The
human's two corrections changed the ACCOUNTING and not one note of the output.
That is the most useful thing this pass produced, and it is a finding about
the pipeline rather than about the human:

* the two boxes were being refused `no_pitch`, which says *we could not pitch
  this notehead*. They are not noteheads; they are the two halves of an alto
  C-clef. The bucket was TRUE and beside the point, and a cleanup count
  reading it would have gone looking for a pitch problem.
* what would actually put those 40 bars of Viola music in the file is the
  CLEF — and the clef is what `act-0003` disagrees with, and **no stage reads
  a stance.** Deliberately (`reach.KNOWN_GAPS`).

So the review pass says, in its own numbers: *the human can tell the pipeline
what a box is NOT and it will believe him; he cannot yet tell it what the
CLEF is, and until he can this staff stays empty.* Roadmap 2.10 and 2.11 are
the two items that would close it, and 2.11's rule — *clef-sized ink at the
header is the clef, and a notehead box on it is refused `is_a_clef`* — is
precisely what these two human deletions did by hand.

**The one row that reached nothing, reported not hidden:** `act-0003`, the
stance (`obs:174397`). The feedback file carries it with the verdict it
disagrees with, that verdict's own `reason` (`no_candidates`), its decider
(`adjudicate_clef`), how many rows the decision was handed (5), the decision's
declared `checked_by` (all four constraints, including the one the tree
records as *declared and not implemented*), and
`verdict_was_changed_by_this: false` — re-resolved against the arm by
(quantity, subject), not asserted.

### Cost, on this machine

| | |
|---|---|
| gather rows replayed | **174,394** |
| verdicts after ADJUDICATE | 84,626 |
| standing verdicts compared | **99,068** |
| wall, whole movement, one run | **~11.5 min** (two in parallel; ~12.5 min alone) |
| peak RSS | **~3.7 GB** (64 GB machine, no pressure) |
| amended record written | 239 MB (pooled) |

A control writes no amended record, so the control arm is cheaper than the
number above. This is a fact about this machine, not a budget — roadmap 1.2b
owns that question.

### The artefacts

`out/viola-p3.sidecar.json` (the three actions, committed),
`out/viola-p3.arm.diff.json`, `out/viola-p3.arm.feedback.json`,
`out/viola-p3.control-INFER-OFF.diff.json` (the N/N pass),
`out/viola-p3.control-INFER-ON.diff.json` (the 69-verdict tree difference).
The amended record (239 MB) and the arm's MusicXML are NOT committed.

## A6. What is NOT established

* **Nothing here has been adjudicated by a human against the print.** The
  roadmap row's gate — *one full pass by Sean yields a feedback file a session
  can read, and at least one of his rows appears in a re-decided verdict's
  basis* — is NOT met by this lane alone: it needs lane (B)'s viewer and Sean.
  What IS established is that the machinery the gate needs exists and works on
  the real record, and that a human row CAN appear in a re-decided verdict's
  basis (two did).
* **n = 1 document, 1 staff, 3 actions, and no `add_box` on a real plate.**
  The Viola sidecar adds no box on purpose: the funnel measured this staff's
  failure as boxes the detector drew WRONGLY, not heads it missed (*at most 2
  of the reference's 31 heads have no detector box at all*). The `add_box`
  path is exercised on the fixture only, and Breitkopf is not run.
* **The `redrawn` verdict value reaches no consumer.** A redraw says the box
  is in the wrong PLACE, a different claim from *not a symbol*, and what to do
  with the machine's own box is a decision nobody has taken.
* **`staged.check` went 255 → 259, status=ok, and N GOING UP IS AGAINST
  CLAUDE.md §4d.** Reported rather than argued away. The +4 are one fact
  spoken by four instruments — two quantities whose PRODUCER is a human,
  outside the pipeline: `inventory` +1 (a `wants` entry whose quantity no
  gather site observes), `gather_coverage` +2 (its DECLARED-UNGATHERED list,
  which has no gaps mechanism), `reach` +1 (the stance, producer-only by
  design). Closing them would mean inventing a `gather_human_boxes()` that
  reads a JSON file, which would put a review artefact inside the measurement
  path — the same structural refusal that keeps a dossier out of it (there is
  no `--dossier` and there will not be one).
* **A per-STAFF export census is INSTRUMENTED, not derived from the record.**
  It wraps the exporter at run time and is only as good as that wrapper; the
  equality control against `notes_not_written` is what makes it usable, and it
  can fail.
* **The stance is unread by design, so a review pass cannot yet tell the
  pipeline about a CLEF.** That is the gap A5 measures, not a defect of this
  lane, and the items that close it are 2.10 and 2.11.

## How to reproduce

    # the control on the record's own tree — must reproduce it N/N and write
    # an identical file
    OMR_INFER=0 python3 -m tools.omr.staged.review.rerun \
      library/_shared-records/beethoven5-litolff-mvt1-whole-20260923.record.json \
      --control --out <scratch>/control0 --staff staff/3/0/9

    # the same on today's tree — 69 INFER duration verdicts differ, and that
    # is the finding
    python3 -m tools.omr.staged.review.rerun <record> --control \
      --out <scratch>/control --staff staff/3/0/9

    # the control, seen FAILING on demand
    python3 -m tools.omr.staged.review.rerun <record> --control \
      --break-control --out <scratch>/red

    # the arm
    OMR_INFER=0 python3 -m tools.omr.staged.review.rerun <record> \
      benchmarks/omr-stage-review-2026-09/out/viola-p3.sidecar.json \
      --out <scratch>/arm --staff staff/3/0/9 --progress


# §C — the LABELS (roadmap 3.4c, 2026-09-23)

Sean, after his first minutes on the §B viewer:

> *"it works now but the UI is awkward — I need to be able to select a box and
> re-label it"*

and, in the same breath:

> *"and to label boxes as nothing or belongs to another staff etc."*

His first real case is on this very staff. The alto clef at the head of the
Litolff p3 Viola is boxed by the detector as **two `noteheadBlackOnLine`
glyphs** — `glyph/3/0/9/0/1` at conf 0.642 and `glyph/3/0/9/0/6` at conf
0.364 — so `adjudicate_clef` abstains `no_candidates` and **all 48 notehead
boxes on the staff are lost, 40 of them under `no_pitch`**. He did not want
to delete those two boxes. He wanted to say what they ARE.

## C1. The panel asks ONE question

**WHAT IS THIS?** — five answers, each a witness, each a row the stages read
or visibly fail to read. The set is ONE TABLE,
`human_evidence.HUMAN_BOX_LABELS`; `check_sidecar`'s required fields,
`server.KIND_REQUIRES`, `/api/labels`, the panel's buttons, its keyboard
hints and `SIDECAR.md`'s table all derive from it, and
`test_the_server_offers_exactly_lane_As_verbs` asserts the two ends cannot
drift. The *etc.* in his ask is satisfied by adding a row there.

| answer | kind | the row it becomes | key |
|---|---|---|---|
| a symbol of class … | `relabel_box` | `Q.HUMAN_BOX_VERDICT = is_a:<class>` on the machine's glyph, **plus** a human box of the new class | `l` |
| nothing — not a symbol | `delete_box` | `= not_a_symbol` (the verb is unchanged) | `0` / `d` |
| belongs to another staff | `own_box` | `= owner:<staff subject>` | `↑` / `↓` |
| a duplicate of another box | `dup_box` | `= duplicate_of:<glyph>` | `=` |
| I can't tell | `unsure_box` | an **Abstention**, reason `ABSTAIN.HUMAN_UNSURE` | `u` |

⚠️ **`nothing` keeps the verb `delete_box`.** The panel shows him the word he
means; the contract keeps the spelling it had. Two spellings for one claim
would make every sidecar written before today ambiguous about which it meant.

⚠️ **A human may DECLINE, and the record can now say so.** `unsure_box` is an
Abstention, not a value, because `State.DECLINED` and `State.READ` are what
the record exists to keep apart — and a review tool that could file only his
ANSWERS would quietly select for the boxes he was sure about, so the places
where the PLATE itself is ambiguous would never reach the record at all. It
is read by nothing, deliberately.

## C2. Which stages see what — DERIVED, and it is two questions

`human_evidence.visibility()` reads this off `adjudicate.REGISTRY`,
`evaluate.RULES` and `infer.RULES`; `rerun.py` then MEASURES it per run.
Folding the two halves into one table is how a lane reports a quantity as
live that nothing ever receives.

**(i) A human BOX — a subject of its own** (`add_box`, and the box half of
`relabel_box` / `redraw_box`). Quantities it can carry: `glyph_box`,
`notehead_class`, `notehead_staff_position`, and — new in 3.4c, on the STAFF
subject, for a clef-class box in CELL 0 only — `clef_glyph`, `clef_position`.

| | decisions |
|---|---|
| **domain** (the human's subject IS a subject) | `duration`, `event`, `stem_direction`, `notehead_is_a_whole_rest`, `notehead_is_not_a_notehead` — all via `notehead_class` |
| **wants** (declared as evidence) | `arc_kind`, `arc_owner`, `articulation_owner`, **`clef`** (`clef_glyph`, `clef_position`, `notehead_staff_position`), `duration`, `event`, `fermata_owner`, `glyph_owner`, `notehead_is_a_whole_rest`, `notehead_is_not_a_notehead`, `onset_column`, `ornament_owner`, **`slot_index`** (`clef_glyph`), `stem_direction`, `tuplet`, `wedge_anchor` |
| **EVALUATE cause** | none directly; `restate_pitch` reaches a human box through its `notehead_staff_position` |
| **INFER reads** | `collapse_duration_by_column`, `collapse_duration_to_barline` (`glyph_box`), **`collapse_slot_index_to_family_block`** (`clef_glyph`) |

The two rows in bold are 3.4c's: before it, a human box could not reach the
clef decision at all. `test_EXACTLY_these_stages_see_the_relabelled_box`
pins the verdicts a human box actually RECEIVES —
`{notehead_is_not_a_notehead, stem_direction, notehead_is_a_whole_rest,
duration, pitch}` — exactly, so a change that starts or stops reading one
fails there with the quantity named.

**(ii) A human LABEL — a row on the MACHINE's own subject**
(`Q.HUMAN_BOX_VERDICT`).

| | decisions |
|---|---|
| **domain** | *none* — a label never creates a subject |
| **wants** | `adjudicate_notehead_is_not_a_notehead`, `adjudicate_glyph_owner` |
| **EVALUATE / INFER** | nothing |

⚠️ **Two decisions DECLARE it, so the harness hands BOTH of them every label
on that glyph** — including the ones that are not their question. A
`owner:` row lands in the notehead refusal's `basis` and is declined there; a
`redrawn` row did the same before 3.4c. **`used` is the only field that
separates OFFERED from WEIGHED**, which is why the diff reports the three
apart, and a test asserting "this row reached nothing" would have been WRONG
and would have looked right
(`test_an_owner_row_on_an_UNCONTESTED_glyph_DECIDES_NOTHING`).

⚠️ **`own_box` only DECIDES on a CONTESTED glyph.**
`adjudicate_glyph_owner`'s domain is `subjects_from=Q.GLYPH_BAND_DISTANCE` —
the contested population. On an uncontested glyph there is no
`Q.GLYPH_OWNER` verdict at all, so the human's row is filed, offered to the
notehead refusal, declined, and decides nothing. Named rather than hidden.

## C3. The clef connect, and the thing it exposes

A clef-class box in **cell 0** files the same two rows `gather_clefs` files
for a detected clef: `Q.CLEF_GLYPH` on the STAFF and `Q.CLEF_POSITION` beside
it, the position from the cell's own recovered grid with the control that can
fail. That is a CONNECT, not a guess — the arithmetic is the record's own and
the class test is `gather._is_clef_class`, imported with its category half
(without which 27 classes read as clefs, `flag8thUp` as a BASS clef).

⚠️ **Cell 0 only.** *A clef is read at the head of the staff* is gather's own
rule; a mid-staff clef change is a reading GATHER does not make and this
module may not invent one. A clef-class box elsewhere gets no clef row and
the action's `absent[Q.CLEF_GLYPH]` says why
(`test_a_clef_class_box_OUTSIDE_cell_0_files_no_clef_row`).

⚠️⚠️ **AND THE ROW CARRIES `score=None`, WHICH THE CLEF CONTEST READS AS THE
WEAKEST EVIDENCE THERE IS.** `clef._detector_terms` weights by `row.score`
and reads `None` as 0.0, i.e. `W_DETECTOR_LOW`. Measured on the fixture: a
staff carrying a detector `gClef` at 0.9 and a human `clefCAlto` comes back
**`treble`, scores `{treble: 1.0}`**, with the human's row in `basis` and
never in `used` — offered and declined. A person who read the plate is
outranked by one detection. That is wrong, it is NOT repaired here (writing a
confidence would be exactly the fallback CLAUDE.md rule 8 forbids), and
repairing it is a change to `clef.py`'s weighting with its own measurement.
`test_THE_HUMANS_CLEF_ENTERS_AS_THE_WEAKEST_WITNESS_AND_IT_IS_SAID` pins it.

## C4. `rhythm._head_class` traced — and the row it reads was NOT filed

The brief asked whether a relabel INSIDE the notehead family should file a
human `Q.NOTEHEAD_CLASS` on the machine's glyph, because that is what
`adjudicate_duration` reads. It was traced, and the answer is **no**:

    def _head_class(ev):
        rows = ev.rows(Q.NOTEHEAD_CLASS)
        return max(rows, key=lambda r: (r.score or 0.0)).value

A human row carries `score=None` → 0.0 and would **lose** to the detector's
0.9 — while still landing in that verdict's `used`, because
`adjudicate_duration` puts every `Q.NOTEHEAD_CLASS` row it can see there. The
feedback file would report the row as WEIGHED and the value would not move:
this repo's own standing bug class (*the value existed and nothing read it*)
wearing the opposite mask, and harder to catch.

So the relabel files no such row. The new class arrives as a **human box of
its own**, and `adjudicate_duration` decides on THAT subject — asserted
exactly (`black → half` gives `written 2.0` on the human subject and leaves
the machine's `1.0` untouched).

⚠️ **The price is a duplicate note, and it is asserted rather than buried.**
An in-family relabel adds a head and refuses none, so the bar carries the
machine's quarter AND the human's half
(`test_AND_THE_PRICE_IS_TWO_NOTES_WHERE_THE_PLATE_HAS_ONE`). Closing it needs
either a rule that `is_a:<other notehead>` supersedes the head class — which
means changing how `_head_class` ranks, not adding a row — or a rule that
refuses the machine's box, which is `redrawn`'s open question and a decision
nobody has taken. Neither is 3.4c's.

## C5. The controls, and the RED

⚠️ **RUN RED FIRST, and the RED that matters is not "the verb did not
exist".** With the whole ingest in place and ONLY the two connects neutered —
`_human_not_a_symbol`'s `is_a`/`duplicate_of` arms returning None and
`_human_owner` returning None — the two test files ran **7 failed, 98
passed**, and the seven are exactly the consequence tests. Every ingest test
stayed green, so they test the CONNECT and not the filing: the rows are filed
either way.

⚠️ **The ownership test has a positive control in the same class.** Without a
human row the same fixture contest decides `staff/0/0/1`, reason `distance`,
and `control_differ == 0`. A `_human_owner` that fired on every glyph would
look exactly like one that works, and this is what separates them.

⚠️ **`own_box` reports whether the named staff HOLDS the ink, and repairs
nothing.** CLAUDE.md §10: a resolved contest DROPS the loser and never
relocates it, so awarding a glyph to a staff whose own detector never boxed
that ink removes a note and adds none. `detail.twin_on_the_named_staff`
carries the `Q.GLYPH_BAND_DISTANCE` row that proves otherwise, and says
whether that staff is the glyph's OWN — because the commonest `own_box` pulls
a head back to the staff it was cut from, where the "twin" is the glyph
itself.

⚠️ **The `wiring` substring trap caught this lane too — the sixth time.**
`_twin_on` first read the band row's own detail flag for *is this the glyph's
own staff*, which is the obvious read. `wiring --check`'s DETAIL question is
a raw-text substring scan over everything under `tools/`, so that one mention
reported a standing pipeline finding as CLOSED: **69 problems, 1 STALE gap
entry, `staged.check` status=broken**. A review instrument reading a detail
key does not make a STAGE consume it. The answer is the same one
`recover_cell_grid` records one function along — derive it from the SUBJECT
(the glyph's staff is in its key) and never name the key.

⚠️ **A human naming a staff the contest never offered is NOT swallowed.**
`_human_owner` checks nothing: if he names `staff/0/0/7` the verdict says
`staff/0/0/7`, the twin field says `null`, and the note count does not move.
That he disagrees with the candidate SET is the finding.

## C6. `staged.check`: 258 → 259, and N GOING UP IS AGAINST CLAUDE.md §4d

Reported rather than argued away. Baseline measured on this branch's own base
(`git archive 2666f383` into a scratch tree, `staged.check` there = **258**).
The +1 is `inventory`, one new `KNOWN_GAPS` entry: **`glyph_owner wants
'human_box_verdict'`** — the same fact the `notehead_is_not_a_notehead` entry
already carries, one decision along. The declaration IS read
(`ownership._human_owner`); what the tool reports is that the quantity's
PRODUCER is a human, outside the pipeline. Closing it would mean inventing a
`gather_human_boxes()` that reads a JSON file, which puts a review artefact
inside the measurement path — the same structural refusal that keeps a
dossier out of it. `wiring` 70, `reach` 25, `brakes` 8: all unchanged.

⚠️ Every CONNECT of a human witness to a further decision costs exactly one
of these, by construction. That is the shape of the cost, and it should be
priced before the next one rather than discovered.

## C7. The run on the real record — Sean's own case

Record: `library/_shared-records/beethoven5-litolff-mvt1-whole-20260923.record.json`
(313 MB, 156,525 observations, 17,869 abstentions, 101,361 verdicts, 331
staves, dpi 600, provenance `dbc9962b` **dirty** — not a baseline). The
relabel was made **through the HTTP API** on a server run on port 5076
(Sean's own is on 5075 and was not touched), so the frame control gated it
exactly as it gates his clicks.

⚠️⚠️ **THE CONTROL RUNS FIRST AND IT IS THE ONLY REASON ANY OF THIS IS
READABLE.** An empty sidecar on today's tree gives **78 differing standing
verdicts** and `<note>` **8,588 → 8,605 (+17)`** — 69 INFER `duration` and 9
INFER `clef`, all of it drift between the tree that gathered the record and
the tree that re-decides it. **Every one of those numbers would otherwise
have been read as the relabel's.** The first draft of this section nearly
was: nine staves across the movement gaining a decided `alto` clef is an
extremely convincing thing to attribute to a human saying *that is an alto
clef*, and it is not his.

| | control | relabel arm | own_box arm |
|---|---|---|---|
| standing verdicts differ | **78** | **79** | **79** |
| absent from the rebuild | 0 | 0 | **1** |
| `<note>` | 8,588 → 8,605 | 8,588 → 8,605 | 8,588 → 8,605 |
| the ONE extra verdict | — | `notehead_is_not_a_notehead` on `glyph/3/0/9/0/1` | `glyph_owner` on `glyph/3/0/9/6/3` |

### C7a. `relabel_box glyph/3/0/9/0/1 → clefCAlto`

Four rows, and the file names all four:

    obs:174395  glyph/3/0/9/0/400000  glyph_box      ["clefCAlto", 289.0, 579.0, 169.0, 139.0]
    obs:174396  staff/3/0/9           clef_glyph     "clefCAlto"          score=None
    obs:174397  staff/3/0/9           clef_position  4.082857142857148
    obs:174398  glyph/3/0/9/0/1       human_box_verdict  "is_a:clefCAlto"

207 verdicts named one of them; **1 WEIGHED one** —
`adjudicate_notehead_is_not_a_notehead` on `glyph/3/0/9/0/1`, `decided True`,
reason `human_not_a_symbol`, `detail.human_says = is_a:clefCAlto`. Census on
`staff/3/0/9`: `no_pitch` 40 → **39**, `not_a_notehead:human_not_a_symbol`
0 → **1**, `refused_total` 48 both ways, `written {rest: 7}` both ways.

⚠️ **`clef_position` 4.0829.** An alto clef's centre sits on the middle line,
which is staff position **4.0** — so the human's box, converted through the
cell's own recovered grid, places it **0.083 of a staff step** off the line
it is printed on. That is the measurement `clef.py` says should name a C
clef's line, derived honestly, on the record.

**Did the clef decision change? NO.**

    vrd:176191  staff/3/0/9  clef  ABSTAINED  no_candidates  adjudicate_clef
      considered: [obs:174397, obs:174396, vrd:175497, obs:024447-50]
      used:       []
      basis:      [... obs:174395, obs:174396, obs:174397 ...]
      declined:   [clef_located, keysig_clef_fit]
      candidates: []

The decision **read both of his rows and used neither**, and the cause is
exact, in `adjudicators/clef.py`:

* `_GLYPH_TO_CLEF` is `{clefG: treble, clefF: bass, clefUnpitchedPercussion:
  percussion}`, so `_clef_of("clefCAlto")` is **None**. That is deliberate and
  measured — *the class names the FAMILY, geometry names the LINE*, and
  DeepScoresV2 has no soprano/mezzo/baritone class at all.
* `_c_family_support` therefore admits his row only as support for **a C clef
  somebody else NAMED**. Nothing named one (`Q.CLEF_LOCATED` declined), so
  `named_c` is empty, the row supports nothing, and `candidates` stays empty.
* `if not candidates: return Ruling.abstain("no_candidates")`.

**Did any head get a pitch? NO. `<note>` on `staff/3/0/9`: 0 before, 0 after**
(seven measure rests each way). The whole-document `<note>` count is
**identical to the control**, so the relabel wrote no note and removed none.

⚠️⚠️ **THIS IS THE FINDING, AND IT IS A GOOD ONE.** The refusal to let a class
name a C clef's line is RIGHT for the detector — `benchmarks/` records
`clefCTenor` firing where the locator measured alto, twice, at 0.91. It is
WRONG for a person: he did not classify a glyph, he read which line the clef
is printed on, and he handed over the position to prove it. Closing it is one
branch in `_c_family_support`'s caller gated on the ROW'S READER — a human
`clefC*` row NAMES its C clef instead of merely supporting one — with its own
measurement. **That is the structural refinement this pass was run to find**
(Sean: *"I mainly want this information so that we can then use it to
determine how to refine the build, rules and decisions — structurally"*).

⚠️ **A SECOND GAP, VISIBLE IN THE CONTROL AND THEREFORE NOT THE RELABEL'S.**
`infer:fill_clef_gap` DOES give `staff/3/0/9` a decided **`alto`** (`tally
{alto: 14, treble: 1, bass: 1}` over 16 systems of slot 9, superseding the
abstention) — **and not one head gets a pitch anyway.** `restate_pitch` is an
EVALUATE consequence and EVALUATE runs BEFORE INFER (§4a), so a clef decided
at INFER pitches nothing. Forty `no_pitch` heads survive a correct, decided,
document-wide clef. Measured in all three arms.

⚠️ **The other half of his case is still there.** `glyph/3/0/9/0/6`, the
alto clef's other arm (`noteheadBlackOnLine`, conf 0.364), was not in this
sidecar and is still a notehead. One click, same panel.

### C7b. `own_box glyph/3/0/9/6/3 → staff/3/0/9` (owned BACK to the Viola)

`adjudicate_glyph_owner` had awarded this head to `staff/3/0/8` (**Violin**)
on `distance`. One row (`owner:staff/3/0/9`), 145 verdicts named it, **1
WEIGHED it**:

    glyph_owner  glyph/3/0/9/6/3
      before  decided  staff/3/0/8  distance
      after   decided  staff/3/0/9  human_owner

Census on `staff/3/0/9`: `owned_by_another_staff` 3 → **2**, `no_pitch`
40 → **41**, `written {rest: 7}` unchanged, `<note>` identical to the control.

⚠️ **The head came home and fell straight into the same clef gap.** The
human's reading was applied exactly, the refusal moved from one named bucket
to another, and the file did not change — because the Viola has no clef in
EVALUATE. Two corrections are needed to write one note, and 3.4c can only
file one of them.

⚠️ **`absent_from_the_rebuild` went 0 → 1, and `Diff` COUNTS IT WITHOUT
NAMING IT.** One standing verdict the parent held has no counterpart in this
arm — almost certainly the `Q.PITCH` the head carried as the Violin's — and
the diff cannot say which, because `diff_records` records only the count.
**A review pass therefore cannot report which verdict a human's row
REMOVED**, which is the same class of gap as the ones this lane exists to
find. Naming the first N absent keys is a cheap fix and is not taken here.

⚠️ **AND A HUMAN LABELLING ONE COPY DOES NOT LABEL THE TWIN.** A cross-staff
contest is per-GLYPH-SUBJECT: the Violin's own copy of this ink is a
different subject with its own `glyph_owner` verdict, which this row does not
touch. Owning the Viola copy home does not take the Violin's away. On this
staff it cost nothing (the Viola cannot write the note anyway), but on a
staff whose clef is decided it would write the head TWICE. The panel should
prompt for the twin; it does not yet.

### C7c. What the feedback file says, and one thing it cannot

`reached_nothing: []` and `refused: []` in both arms — every row reached a
decision. The per-stage summary reports `verdicts_naming_a_human_row` 207 /
145 against `verdicts_that_WEIGHED_one` **1** and **1**, which is the number
that means anything.

⚠️ **A human row weighed by a SUPERSEDED verdict disappears from the report.**
`adjudicate_clef`'s abstention carries both of his clef rows in `considered`
and `basis` — and `infer:fill_clef_gap` supersedes it, so `_verdict_index`
resolves the standing verdict to the INFER one and `basis_names_human` never
sees the ADJUDICATE pass. The rows are in the record; the feedback file omits
them. That is how §C7a's diagnosis had to be read out of the amended record
by hand rather than off the file, and it is worth closing.

## C8. How to reproduce

    # the CONTROL first — without it every number below is unattributable
    python3 -m tools.omr.staged.review.rerun \
      library/_shared-records/beethoven5-litolff-mvt1-whole-20260923.record.json \
      --out <scratch>/control --staff staff/3/0/9 --progress

    # the relabel arm
    python3 -m tools.omr.staged.review.rerun <record> \
      benchmarks/omr-stage-review-2026-09/out/relabel-clefCAlto.sidecar.json \
      --out <scratch>/relabel --staff staff/3/0/9 --progress

    # the own_box arm
    python3 -m tools.omr.staged.review.rerun <record> \
      benchmarks/omr-stage-review-2026-09/out/relabel-own-viola.sidecar.json \
      --out <scratch>/own --staff staff/3/0/9 --progress

    # the viewer the relabel was made in (⚠️ 5075 is Sean's; use another port)
    python3 -m tools.omr.staged.review.server --record <record> \
      --pdf library/editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf \
      --staff staff/3/0/9 --port 5076

Each run is ~12 minutes and ~4 GB, most of it loading the record.
Committed here: `relabel-clefCAlto.sidecar.json`,
`relabel-clefCAlto.arm.diff.json`, `relabel-clefCAlto.arm.feedback.json`,
`relabel-own-viola.sidecar.json`, `relabel-own-viola.arm.diff.json`,
`relabel-own-viola.arm.feedback.json` and
`relabel-CONTROL-empty-sidecar.diff.json` — the control beside the arms,
because an arm without its control is a number, not a measurement.
