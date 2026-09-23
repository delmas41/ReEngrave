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
