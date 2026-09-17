# Do we know what the measurements are and what they are for?

Sean's question, 2026-09-17. A THIRD audit axis beside `wiring.py` (*does a
value REACH its consumer*) and `capture.py` (*is shape/position/raster/
resolution recorded per family*): **what KIND of measurement is a value, and
may two rows of it be combined?**

Tool: `tools/omr/staged/meaning.py`. Probes and outputs here. Branch not
merged. ⚠️ **This file was written by the manager from the agent's returned
report** — the agent was blocked from creating it — so treat the prose as a
transcription and the numbers as the tool's.

## 0. The answer in one paragraph

**For the FRAME sub-axis: we record it, we do not use it, and it would not be
sufficient if we did.** `Observation.frame` is written on every row and read in
exactly **four** places in the staged tree — twice as an opaque equality key in
the correlation filter (`adjudicate.py:465`, `groups.py:359`), once to build a
term label (`clef.py:217`). **Nothing reads it to decide whether two values may
be combined.** And it could not: it names the frame of *the crop the reader
worked in*, not the frame of anything the row carries.

**For SUBJECT, CLAIM STRENGTH and COMPARABILITY the record has nowhere to put
the fact.** That is why `positional_store.py` had to *invent* `Membership.kind`.
Of 13 calibration instances this axis catches **2 fully, 1 partially**.

## 1. Reach first

142 non-test modules. `Q` vocabulary 80 / written 46 / read 66; 28 decisions;
28 quantities read by >1 module; **42 pooled**; 54 detail keys whose NAME
declares a unit.

| § | question | population |
|---|---|--:|
| 1 | one quantity in **>1 frame** | **4** of 46 |
| 2 | `detail` declares a frame the `frame` field does not | **29** keys / **9** quantities |
| 2b | the row's **VALUE** is in a frame `frame` does not name | **1** |
| 3 | decision **SCOPE coarser** than its rows' frame | **13** pairs, 12 with no page-frame key |

Frames: `cell:* 23 · page 15 · header_window 5 · system 4 · bar_head:* 2 ·
system_margin 1`. Zero unresolved.

⚠️⚠️ **`wiring`'s first question is called "FRAME" and is not about one.** It
asks whether a declared input is read at a `Scope` that can reach where it is
FILED — subject reach. **VERIFIED against the tree by the manager**
(`wiring.py:42`: *"FRAME — a declared input read where it is never filed"*).
The collision means a green `wiring --check` reads as *frames are checked*.
They are not.

## 2. The findings

**§1 — four multi-frame quantities**: `direction_word`, `dynamic_letter`,
`wedge_box` (`cell:*`/`page`), `meter_template_at_bar`
(`bar_head:*`/`header_window`). `wedge_box` is the one HONEST case —
`adjudicate_wedge_anchor` abstains `no_page_frame` on exactly the box-less row,
a consumer declining rather than guessing, and the **only** such instance.
`meter_template_at_bar` is the one where incommensurability is already
MEASURED: the template score is monotone in window width (968 rise, 0 fall).

**§2 — nine quantities file at `cell:*` and carry page pixels in `detail`**
(`glyph_box`, `arc_box`, `rest`, `ink`, …). ⚠️⚠️ **Not nine bugs**: this is the
`Q.ONSET_COLUMN` repair applied deliberately. What it cost is that `frame`
stopped describing the row.

**§2b — `Q.CELL_BOX`**: filed `frame="cell:*"`, value is `bbox_page_px`. One
frame and no unit-declaring key, so **§1 and §2 both reported it clean**. The
consumer is correct; the FIELD is misleading. This is what makes the headline
stronger than *"frame describes the value"*.

**§3 — 13 decision/quantity pairs pool rows finer-framed than their scope.**
⚠️⚠️ The repaired `onset_column` is the ONE exempt row in its own table (it
reads `x_page`) — not designed for, it fell out, and a test pins that it is the
only one. Of the other twelve: **the four `meter` rows are the open finding**
(SYSTEM-scope vote over `cell:*` rows from every staff, no page-frame key — a
third route to the family CLAUDE.md already records as the scan-side blocker;
**not** a claim the vote is wrong, only that nothing checks); six are benign by
structure or unit (a staff prints one clef in one header cell; STEPS, ORDINALS
and COUNTS make no frame claim); `meter/rest` is probably benign
(quarter-length composes) and is listed because scope alone cannot tell.

## 3. Calibration — 2 of 13 fully, 1 partial

✅ **#1** `Q.ONSET_COLUMN` · ✅ **#6** dynamics letters vs noteheads ·
⚠️ **#7** `Q.CELL_BOX` partial.

❌ **#2** `STAFF_SPACING`/`CELL_STAFF_SPACE` — two single-frame quantities,
**and no single function reads both today**, so there is nothing live to catch ·
❌ **#3** `FLAG`/`AUG_DOT` — same Kind, same frame, different SUBJECT ·
❌ **#4** `gap_bridging_counts` — one value, wrong composition · ❌ **#5** `raw`
evidence vs synthesised — same name, opposite STANDING · ❌ **#10** crop drift —
accuracy, not record shape · ❌ **#11** `ink_explained_by` vs
`ink_detector_coverage` — a CLAIM-KIND fault · ❌ **#8/#9/#12/#13** out of scope.

> ⚠️⚠️ **The six in-scope misses share ONE cause: `Observation` has a field for
> the FRAME and none for the subject role, the claim kind, or
> commensurability.** Corroboration from the other end: `positional_store.py`,
> written days earlier for a different purpose, **had to invent
> `Membership.kind`** because the record had nowhere to put it. Two independent
> pieces of work reached the same gap.

## 4. The tool

Two-tier. **HARD tier at zero today**, so it CAN be a gate — unlike
`no_producer --check`, which CLAUDE.md records as unable ever to pass: positive
controls above floors, **every frame token placeable** (unplaceable is a hard
fail, never a skip), unaccounted findings, and stale entries (a closed gap must
leave). **ACCOUNTED tier: 24 findings, each with a reason.** `A-INK-4`
respected — no rule, veto or threshold, and a test asserts no pipeline module
imports it.

**`DERIVED_CHECK = True` is load-bearing, and it is MEASURED**: with the marker
renamed away, this tool's mention of `staff_bottom_line_page` closes a live
`wiring` DETAIL gap and `wiring --check` fails STALE (exit 1); with it in place,
`wiring --check` is byte-identical to baseline. `capture.py`'s hazard,
reproduced and caught.

**Controls**: baseline 8 checks exit 0 BEFORE any change; afterwards all 10
exit 0, with `capture`/`wiring`/`inventory`/`gather_coverage`/`export_coverage`
**byte-identical**. `health` and `no_producer` differ only in file/test counts
(the two new files); no finding line changed. ⚠️ A grep filter first reported
*no_producer FINDINGS CHANGED* — the filter was wrong, not the findings; read
the whole diff. 24 new tests, 121 pass across four instruments. Battery: 14
arms, 13 red, 1 expected-green positive control, **0 survivors**, restore
md5-verified; refuses a dirty tree and a stale in-flight sentinel.

## 5. Three faults in the instrument, each found by a zero that was too clean

1. ⚠️⚠️ **`adjudicate.REGISTRY` is EMPTY on a bare import** (the `@decision`
   decorator needs the `adjudicators` package). §3's first run iterated NOTHING
   and printed `0` — which reads exactly like *no decision pools across
   frames*. Now asserted before the section computes.
2. ⚠️⚠️ **`capture.py`'s documented `**common` trap, one spelling further on.**
   Resolving `dict(...)` but not `box_detail.update(k=v)` gave **12 unit keys
   and ZERO disagreements**; the true figures are **54 and 29**.
3. ⚠️⚠️ **§2b's first run also reported ZERO** — `Q.CELL_BOX`'s value
   expression contains no page token; it is one line earlier in the assignment.

**Generalisable form, four instances counting `gather_coverage`:** *in this
codebase a value, a frame and a detail dict are nearly always bound to a NAME
before they are written, so an AST walker that stops at the `Name` measures its
own resolver and reports the answer as clean.* Each pinned by a test and a
battery arm. A fourth, in the battery: the anchor `DERIVED_CHECK = True`
occurred TWICE (docstring + assignment) — the recorded *anchor occurring twice*
fault, visible only because an anchor miss is reported as an ERROR.

## 6. A sibling defect, found and NOT repaired

⚠️ **`reach.py`'s docstring says `--check` fails on an unaccounted staged
module. It does not.** `unaccounted_modules()` returned `['meaning.py']` while
`reach --check` exited 0; the only enforcement is `test_staged_reach.py:61`.
CLAUDE.md's *a rule described in a docstring and never built*, inside a derived
check. **VERIFIED independently by the manager**: `grep unaccounted_modules`
finds the definition, the docstring, and one TEST — `reach.py` never calls it,
and `--check`'s own `unaccounted` (line 352) is about QUANTITIES. Left for a
human; `meaning.py` was registered in `NOT_A_STAGE` so the suite is green.

## 7. What is NOT established

**Nothing was gathered, exported or measured on a page** — every figure is a
property of the tree, and necessarily: **no committed staged record carries
`Observation.frame` in JSON at all.** It is not established that any of the 24
findings COSTS anything — §2's nine are a deliberate repair, six of §3's twelve
are argued benign by hand, and the meter family is flagged on STRUCTURE, not
shown to pool frames that actually disagree (that needs a record and a crop).
§3 is a **screen**, not a verdict. The unit axis rests on a NAMING CONVENTION,
which is exactly how `Q.CELL_BOX` escaped §2. `FRAME_EXTENT` and `UNIT_SUFFIX`
are guarded against *unplaceable*, not against *wrongly placed*. Four
calibration instances are out of scope, so the axis was calibrated against
nine. No OMR-NED figure and no accuracy claim.

## 8. Ranked, if one thing is taken

1. **Rename one of the two "FRAME"s** — cheapest, and the collision actively
   misleads.
2. **Adjudicate §3's four `meter` rows against a record** — the one open
   finding, on the known scan-side blocker.
3. **Decide whether a CLAIM KIND belongs on `Observation`** — two independent
   pieces of work now want it. ⚠️ It perturbs every record in the tree, so it
   is Sean's call, not a check's.
