"""Does the information REACH its consumer? — a DERIVED check for the repo's
highest-yield bug class.

    python3 -m tools.omr.staged.wiring            # the three tables
    python3 -m tools.omr.staged.wiring --json
    python3 -m tools.omr.staged.wiring --check    # non-zero on anything
                                                  # not on KNOWN_GAPS
    python3 -m tools.omr.staged.wiring --run rec.json   # confirm SCOPE from a
                                                        # real record

⚠️⚠️ **THE BUG CLASS, AND WHY IT NEEDED AN INSTRUMENT.** *The value existed
and nothing read it* has been found in this repo **ten or more times, every
one of them by accident**, and each find was expensive: `Q.STEM` gathered and
unread (916 rows, found THREE separate times); `pdf_path` rasterised and
dropped, so `gather_margin_labels` filed `not_implemented` on 75 of 75 staves
**on every staged run this repo has ever made**; `Q.METER`'s `segments`
reaching no file; `adjudicate_dynamic` deciding while `grep '<dynamics'
export.py` returned 0; `Q.METER_GLYPH`'s `letter` flag written and unread.
The 2026-09-11 handoff, after the second missing producer in two days, wrote
the conclusion this module implements: *"worth a derived check rather than a
third discovery."*

## The three questions this asks

Each has a live instance in the tree today, and neither of the two existing
staged instruments asks any of them. ⚠️ **The COUNT is the `controls()`
table's, not this heading's** — a hand-counted figure in prose is exactly
what rots in this repo, and this heading has already been wrong twice: it
said THREE after a fourth question landed, and FOUR after one left.

⚠️⚠️ **THE PRODUCER QUESTION IS NOT HERE, AND WAS NOT REMOVED FOR BEING
WRONG.** *A parameter threaded with no supplier* is asked by
**`tools/omr/no_producer.py`**, which a sibling session landed on main the
same day this was written — derived from the AST over the whole of `tools/`,
finding `pdf_path` and `roster` with no hint. This module had its own, and it
was a DUPLICATE. CLAUDE.md's record of the hairpin export built twice says
*run `git log --all --oneline -S "<the thing>"` before building anything*,
and this session did not — so ~200 lines were written and then deleted.
**Ask that question there.** What survives of it here is the roster REPAIR,
which closes one of that tool's own open findings.

**1. SCOPE — a declared input read where it is never filed.**

⚠️⚠️ **THIS QUESTION WAS CALLED "FRAME" UNTIL 2026-09-17 AND IS NOT ABOUT ONE.**
It asks whether a decision reads an input at a `Scope` that can REACH where the
input is FILED — subject reach. A COORDINATE frame (`page`, `cell:N`,
`header_window`) is a different axis entirely, recorded on every row as
`Observation.frame` and, as of 2026-09-17, checked by nothing that decides
whether two values may be combined. The collision was actively misleading: a
green `wiring --check` read as *"the frames are checked"*, and they are not.
Renamed on the measurement-meaning audit's first recommendation. A decision that
reads `ev.rows(Q.X)` at the default `Scope.EXACT` reads its OWN subject, whose
Kind is the decision's declared `scope`. If `Q.X` is only ever filed at a
DIFFERENT Kind, the declared input is present, declared, gathered — and
**structurally unable to answer**. CLAUDE.md records four instances of this
and states flatly that *neither `inventory --check` nor `gather_coverage` can
catch it*: the `wants` entry IS read and the quantity IS gathered, so both
tools see a healthy row. Only a test asserting the ANSWER comes out has ever
caught one.

**2. DETAIL — a key written into a row and read by nobody.** The finest grain
of the same fault, and the one `Q.METER_GLYPH`'s `letter` flag lived in for
months: `log.observe(..., letter=True)` writes a field on the row, and a
`grep` for it finds the write and nothing else. A quantity-level check cannot
see it, because the QUANTITY is read — it is one field of it that is not.

**3. ROUNDTRIP — a field dropped by its own `to_json`.** A field a class
declares, a consumer READS, and the class's own projection does not write —
so it cannot survive a saved record and the consumer silently gets the
default on every replay. `Verdict.single_pass_revision` is exactly that, and
it is the fixpoint guard's one sanctioned exemption. This is the `works.json`
`lines` fault with producer and projection in one place, where the comparison
is exact.

## ⚠️ DERIVED, NEVER A HAND LIST — and it must be able to FAIL

This repo has the scars for both halves of that sentence. `ARITY_FIELDS` **was
already incomplete the day it landed**, because it answered a hand list with a
hand list. The anti-drift guard in `gather_coverage` **had the very bug it
exists to prevent** — it compared names for exact equality, so `events` never
matched `Q.EVENT`. `health.py` reported *"EMPTY CELLS: none"* by ACCIDENT,
because one clause credited a registry-iterating test with covering every
decision. And the flag-direction guard's first version descended THROUGH
`environ.get` onto `os.environ`, matched nothing, and both its real assertions
passed vacuously.

So: every column here is read out of the code that runs (`ast`, `inspect`,
`adjudicate.REGISTRY`, `evaluate.RULES`), and **each question carries a
POSITIVE CONTROL** — a count of the cases it found to be HEALTHY. `--check`
exits non-zero when a control is zero, because a question that can only ever
answer "nothing wrong" is not a question. `controls()` is what makes a clean
run mean something.

⚠️ **AND ANYTHING UNRESOLVED IS REPORTED, NEVER DROPPED.** A gather site whose
subject expression this cannot resolve to a Kind lands in `unresolved`, and
`--check` fails on it. The default for a case nobody thought of is NOISY: a
silent skip is how a derivation quietly stops covering the thing it names.

⚠️ **A fallback here never converts "cannot tell" into a definite answer.** An
unresolvable Kind is `None` and `None` matches nothing — it is never spelled
"same" or "fine", because two guards in this repo reintroduced the exact
failure they guarded against by returning a value that compares equal to
itself.
"""

from __future__ import annotations

import argparse
import ast
import json
import pathlib
import sys
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

_HERE = pathlib.Path(__file__).resolve().parent
_TOOLS = _HERE.parent.parent                      # tools/
_ROOT = _TOOLS.parent                             # repo root


# ─────────────────────────────────────────────────────────────────────────────
# The standing gaps — an INVENTORY, not a suppression list
#
# ⚠️ Same contract as `export_coverage.KNOWN_GAPS` and `inventory.KNOWN_GAPS`,
# and for the same reason: a `--check` that is permanently red is a check
# nobody can put in CI, and one that hides its failures is worse. Every
# problem the derivation finds TODAY is listed here WITH ITS REASON, and
# `--check` fails on anything NOT on the list. ⚠️ AN ENTRY THAT IS CLOSED MUST
# LEAVE IT, or the list stops describing the pipeline and starts describing
# its history — `test_staged_wiring.py` enforces exactly that.
# ─────────────────────────────────────────────────────────────────────────────

KNOWN_GAPS: Dict[str, str] = {
    # ── SCOPE, latent: declared, filed elsewhere, unreadable the obvious way
    #
    # ⚠️ EACH IS A TRAP ARMED FOR THE NEXT PERSON, not a bug today. The
    # declaration is inert (`inventory --check` owns that half); what this
    # adds is that the naive `ev.rows(Q.X)` which closes it would return
    # NOTHING, silently. `instrument declares roster_entry` was the seventh
    # and LEFT this list on 2026-09-15 when it was wired.
    "SCOPE-LATENT adjudicate_clef declares Q.NOTEHEAD_STAFF_POSITION": (
        "the clef's OWN first `checked_by` entry — implied pitches against "
        "the instrument's written range — and the body never reads it. "
        "⚠️ MEASURED UNREACHABLE ON A SCAN (`inventory.KNOWN_GAPS`): the "
        "range test needs `Q.INSTRUMENT`, which abstains on 22 of 22 and 27 "
        "of 27 staves of the two scanned pages. What this row adds is that "
        "wiring it also needs `subject=` — the positions are on the GLYPHS."),
    "SCOPE-LATENT adjudicate_key_signature declares Q.DOSSIER_FACT": (
        "no dossier is supplied on the scan path BY PROTOCOL, and the "
        "`dossier` parameter has no producer at all — which is "
        "`tools/omr/no_producer.py`'s finding, not this module's. Closing "
        "this needs `Scope.SELF_AND_ANCESTORS`, not just a read."),
    "SCOPE-LATENT adjudicate_meter declares Q.DOSSIER_FACT": (
        "the meter's dossier tier, inert for the same reason as the key "
        "signature's and with the same frame trap waiting under it."),
    "SCOPE-LATENT adjudicate_part_partition declares Q.STAFF_ORDINAL": (
        "inert declaration; the partition reads slots, staff counts and — "
        "since 2026-09-20 — the instruments, for its second declared check. "
        "⚠️ The `Q.INSTRUMENT` entry that used to stand here LEFT this list "
        "when that check was performed, which is what closing a gap looks "
        "like. This one has not: nothing reads the ordinal, and the frame "
        "trap that entry named is still waiting under it — the ordinal is on "
        "the STAVES and this decision runs at DOCUMENT, so the repair needs "
        "`Scope.SELF_AND_DESCENDANTS` and not a bare read."),
    "SCOPE-LATENT adjudicate_system_membership declares Q.GAP_BRIDGING": (
        "inert declaration — the connectivity veto already ran in GATHER and "
        "the decision records its RESULT rather than the bridging. The "
        "bridging row is filed on the PAGE and the decision runs at SYSTEM."),

    # ── ROUNDTRIP
    "ROUNDTRIP Verdict.single_pass_revision": (
        "⚠️⚠️ A LIVE FAULT, REPORTED WITH ITS PRICE AND DELIBERATELY NOT "
        "REPAIRED. The field is declared on `Verdict`, READ by the fixpoint "
        "guard (`record.py:1026`) and ABSENT from `Verdict.to_json` — so it "
        "cannot survive a saved record: a replayed verdict comes back "
        "`False`, and the guard's ONE sanctioned exemption, the "
        "durations -> meter -> durations loop `reconcile_duration` is "
        "explicitly allowed, is silently not there. **No saved record can be "
        "replayed through that guard as written.** ⚠️ THE PRICE OF THE FIX "
        "IS WHY IT IS NOT TAKEN HERE: adding a key to `Verdict.to_json` "
        "changes EVERY record this repo writes, so every byte-identity "
        "control over a record — and this project runs several, including "
        "`regather_control.py`, which exits non-zero on an unstamped or "
        "mismatched pair — would report a difference that is not the change "
        "under test. That is the *perturbs upstream by existing* hazard, and "
        "pricing it is Sean's call. Found independently by a sibling agent; "
        "this check reproduces it from the tree with no hand-listing, which "
        "is the proof the question is live."),

    # ── UNRESOLVED gather sites, by SHAPE
    #
    # ⚠️ NAMED, NOT SHRUGGED AT. Eleven sites over three shapes, all of them
    # a subject that only exists at runtime. `--run rec.json` resolves every
    # one from a record's own subject keys, which is why the corroboration
    # arm exists; a TWELFTH site of a NEW shape fails `--check`.
    "UNRESOLVED Subject.from_key()": (
        "the Kind is IN THE KEY, at runtime. Deriving it statically would "
        "mean tracing which collection the key came from, across the module "
        "— and a wrong answer there is worse than none, because it would "
        "file a quantity at a Kind nothing files it at and manufacture a "
        "SCOPE finding against working code. `--run` answers it exactly."),
    "UNRESOLVED local 'sub' (bound from a collection or a caller)": (
        "`sub` is unpacked from a dict or a list (`for cell_key, dets in "
        "detections.items()`), so its Kind is a property of the collection "
        "rather than of any expression here. Same reason as above."),
    "UNRESOLVED local 'g' (bound from a collection or a caller)": (
        "`g, box, det = placed[i]` — a tuple unpacked from a list built "
        "elsewhere in the function. The interprocedural round cannot help: "
        "the caller passes an already-unresolved value."),

    # ── DETAIL keys written and named nowhere else
    #
    # ⚠️ AN INVENTORY, AND EACH ONE IS ITS OWN JOB WITH ITS OWN REACH. This
    # is the finest grain of *the value existed and nothing read it* —
    # `Q.METER_GLYPH`'s `letter` flag lived here for months — so the list is
    # kept as a work queue, never netted away. None was repaired in the pass
    # that built this tool, deliberately: a detail key is only worth wiring
    # against a decision that wants it, and choosing which is a separate
    # judgement from finding them.
    # ── DETAIL, added 2026-09-16 when this branch was landed onto main.
    #
    # ⚠️⚠️ THE CHECK WAS GREEN ON THIS BRANCH AND RED ON THE MERGED TREE, AND
    # THAT IS THE TOOL WORKING RATHER THAN A MERGE DEFECT. PR #34 (both OCR
    # rungs default ON) and PR #35 (the meter template at a bar head) each
    # landed detail keys while this branch was in flight. Every one below was
    # checked at landing time: written in `staged/gather.py`, named by NOTHING
    # outside it and outside tests. They are inventoried with a reason, never
    # suppressed -- `KNOWN_GAPS` is an inventory and anything not on it fails.
    "DETAIL Q.MARGIN_LABEL.rungs_requested": (
        "⚠️ RECORDED-ONLY BY DESIGN, and it is the fix PR #34 said had to "
        "land BEFORE the default moved. The record stamped every label "
        "`READERS.TEXT_LAYER` whichever rung ran, so it could not tell a "
        "venv-less machine from an unlabelled page -- an ABSENT/DECLINED "
        "collapse in the metadata. These six fields exist so a READER can "
        "separate them. No code consumes one yet, which is the honest state: "
        "the value is recorded for a human, not threaded to a decision."),
    "DETAIL Q.MARGIN_LABEL.rungs_available": (
        "which rungs this machine could actually run. See "
        "`rungs_requested` -- same purpose, same recorded-only state."),
    "DETAIL Q.MARGIN_LABEL.rungs_unavailable": (
        "the rungs that were asked for and could not run (no `.venv-surya`, "
        "no Tesseract). This is the half that makes a zero legible: without "
        "it, 'this page prints no labels' and 'this machine has no OCR' are "
        "the same empty result."),
    "DETAIL Q.MARGIN_LABEL.rungs_ran": (
        "which rungs actually executed. Recorded-only; no consumer."),
    "DETAIL Q.MARGIN_LABEL.rungs_failed": (
        "rungs that ran and errored, as distinct from rungs that ran and "
        "read nothing. Recorded-only; no consumer."),
    "DETAIL Q.MARGIN_LABEL.rung_failed": (
        "the per-label singular of `rungs_failed`. Recorded-only; no "
        "consumer. ⚠️ Kept as its own entry rather than folded into the "
        "plural: they are written at different sites (2361 vs 2392) and a "
        "single entry would let one of them go missing unnoticed."),
    "DETAIL Q.METER_TEMPLATE_AT_BAR.candidate_staves": (
        "how many staves of the system proposed a meter column at this bar, "
        "beside the quorum that admitted or refused it. ⚠️ RECORDED AND NOT "
        "GATED ON, which is that feature's own documented discipline -- "
        "CLAUDE.md records the same choice for its false population (13 of "
        "16 are a `C`, 'recorded and not gated on'). The quorum is a COUNT "
        "test; this field is what a later session would need to re-derive "
        "the quorum without a re-gather."),
    "DETAIL Q.MARGIN_LABEL.reader_confidence": (
        "⚠️ THE READER'S OWN CONFIDENCE IN THE LABEL, AND THE DECISION THAT "
        "NAMES THE STAFF DOES NOT LOOK AT IT. `adjudicate_instrument` takes "
        "`labels[-1].value` — the LAST row, not the best-read one — and "
        "spells it. CLAUDE.md's slot-index work records `Obol.` reading at "
        "`low` confidence on a real page, and `Tr. Alt.` resolving to a "
        "SINGER at HIGH confidence, so the field is neither useless nor "
        "sufficient. ⚠️ NOT REPAIRED HERE, and the reason is this file's own "
        "rule: detection confidence reaching a decision is CLASS D of the "
        "probability taxonomy, and an uncalibrated number consumed as "
        "evidence measured ECE 0.1277 — worse than none. Opening it means "
        "deciding what a tier is FOR, which is a judgement and not a wire."),
    "DETAIL Q.MARGIN_LABEL.reader_alias": (
        "the alias the READER's own lexicon fired on, beside the raw text. "
        "⚠️ WORTH OPENING: `adjudicate_instrument` deliberately re-runs the "
        "lexicon on the STRING so the resolution is re-interpretable, and "
        "this field is the reader's competing answer — a second reading of "
        "the same ink, which is what the record exists to keep apart."),
    "DETAIL Q.DIRECTION_WORD.page_n_read": (
        "⚠️ RANKED WORK, and CLAUDE.md already names it: *the ranked next "
        "step is to move the two OCR rungs into the record as INDEPENDENT "
        "readings — today `read_directions` returns only winners, so a "
        "refused candidate cannot be split into `the decoder was silent` and "
        "`the lexicon refused`*. These page-level counters ARE that split, "
        "written and consumed by nothing."),
    "DETAIL Q.DIRECTION_WORD.page_n_candidates":
        "as `Q.DIRECTION_WORD.page_n_read`.",
    "DETAIL Q.DIRECTION_WORD.page_n_rejected_by_lexicon":
        "as `Q.DIRECTION_WORD.page_n_read`.",
    "DETAIL Q.DIRECTION_WORD.page_conflicts": (
        "where the two OCR rungs read one crop differently. Recorded rather "
        "than re-asked, by a documented precedence — and read by nothing."),
    "DETAIL Q.DIRECTION_WORD.page_state":
        "as `Q.DIRECTION_WORD.page_n_read`.",
    "DETAIL Q.DIRECTION_WORD.split_is_page_level": (
        "marks a reason filed on every cell because it is really the PAGE's. "
        "A consumer separating page-level from cell-level abstentions would "
        "read it; none does."),
    "DETAIL Q.BRACKET_BLOCK.mirror": (
        "`mirror=True` marks a row that reproduces a LEGACY code path, for a "
        "human auditing the two against each other. Provenance for a reader, "
        "not evidence for a decision — the one class here that is arguably "
        "right to be unread."),
    "DETAIL Q.SYSTEMIC_COLUMN.mirror": "as `Q.BRACKET_BLOCK.mirror`.",
    "DETAIL Q.GAP_BRIDGING.mirror": "as `Q.BRACKET_BLOCK.mirror`.",
    "DETAIL Q.<loop-bound>.staff_lines_erased": (
        "which of the two cell images the CV rung read. ⚠️ NOT COSMETIC: "
        "*erase for the CV consumer, bound the search for everyone else, "
        "never erase for the detector* is a MEASURED rule (erasing before "
        "YOLO costs 7-13 pooled reading points), and this field is the only "
        "record of which side of it a row came from."),
    "DETAIL Q.BEAM_STROKE.staff_lines_erased":
        "as `Q.<loop-bound>.staff_lines_erased`.",
    # ── DETAIL, landed 2026-09-22 with the three honest empty-claim words.
    # Both keys exist so a LATER READER CAN CHECK THE REFUSAL'S OWN CLAIM,
    # which is the whole reason the words were split: `no_glyph_of_this_kind`
    # asserts the detector fired here, and `no_stems_to_join` asserts this
    # cell's stem set is too small to carry a beam. A reason word nothing can
    # check is a story.
    #
    # ⚠️⚠️ THEY WERE INVISIBLE TO THIS QUESTION UNTIL THEY WERE RENAMED. Named
    # `n_detections` and `n_stems` they each collided with an UNRELATED key
    # elsewhere in `tools/` (`transcribe`/`yolo_detector`/`annotate` and
    # `adjudicators/rhythm`'s own `stems_disagree` detail), and the DETAIL
    # test matches on the bare NAME -- so both read as consumed and `--check`
    # passed. That is a live blind spot in this tool, recorded in
    # `benchmarks/omr-no-ink-lie-2026-09/FINDINGS.md` §9 and NOT fixed here:
    # making the match quantity-aware moves every entry in this list at once.
    "DETAIL Q.<loop-bound>.cell_n_stems": (
        "how many CV stems this cell held when the beam family refused -- the "
        "number `no_stems_to_join` is asserting. A consumer that sees only "
        "the reason word cannot tell 0 from 1, and those are different "
        "readings of the same page."),
    "DETAIL Q.DYNAMIC_LETTER.cell_n_detections": (
        "how many detections the family filter looked past -- the number "
        "`no_glyph_of_this_kind` is asserting. It is also the one field that "
        "would catch the word going wrong: this reason on a cell reporting "
        "ZERO detections would be the old `no_ink` fault returning under a "
        "new name."),
    # ── DETAIL, surfaced 2026-09-17 when a BENCHMARK PROBE stopped counting
    # as a consumer (see the exclusion in `details()`).
    #
    # ⚠️⚠️ NOT NEW FAULTS — NEWLY VISIBLE ONES. Each key below is written by
    # `gather.py` and named, in the whole tree, only by a probe under
    # `benchmarks/`. A measuring instrument reading a value is not a pipeline
    # consuming it, so before the exclusion every one of these read as closed.
    # This is the same family as the two exclusions above (a test, and this
    # module's own gap list) and it is the third instance.
    "DETAIL Q.BRACKET_BLOCK.n_blocks": (
        "how many DISTINCT bracket blocks the system was cut into, carried on "
        "every staff's row. `adjudicate_staff_group` reads the block index "
        "and not the count — so a consumer cannot currently ask *did this "
        "system resolve into one family or six*, which is the question "
        "`BRACKET_COLUMN_MIN_EVIDENCE` exists to make answerable (without "
        "that floor a 25-staff Bruckner system manufactured ELEVEN groups)."),
    "DETAIL Q.DIRECTION_WORD.gate": (
        "why `OMR_DIRECTION_TEXT_SCAN_GATE` skipped this page. ⚠️ It is the "
        "reason string for an OUT_OF_SCOPE abstention, so the ABSTENTION is "
        "consumed and the explanation is not — a reader can tell the word "
        "reader did not run and cannot tell whether it was skipped, absent or "
        "refused without reading the note."),
    "DETAIL Q.DIRECTION_WORD.readers_run": (
        "which OCR rungs actually ran for this word, beside "
        "`winning_reader`. The ranked next step of the direction work is to "
        "put the two rungs on the record as INDEPENDENT readings; this is "
        "half of what that needs and nothing reads it yet."),
    "DETAIL Q.GLYPH_BAND_DISTANCE.own": (
        "whether THIS candidate is the staff the glyph was detected in — the "
        "contested/uncontested split. `adjudicate_glyph_owner` re-derives the "
        "same fact from the subject rather than reading it, so the two could "
        "disagree and nothing would say so."),
    "DETAIL Q.GLYPH_LADDER.found": (
        "how many ledger rungs were actually seen, against `expected`. The "
        "VALUE is the boolean `found == expected`, so a consumer can weigh "
        "'complete ladder' and cannot weigh 'three of four' — and the legacy "
        "rule this is derived from is COMPLETENESS ONLY *because* counting "
        "was measured worse (a ghost's one rung WAS the real note's own). "
        "⚠️ Recorded so that refusal stays checkable, not so it is reversed."),
    "DETAIL Q.MARGIN_LABEL.y_center_px": (
        "where in the margin this label sits. The label→staff assignment "
        "happens inside the reader (`_assign`, on block centroids) and the "
        "record keeps the result; this is the evidence that decision was made "
        "on, unread — which is the shape that let a whole-crop OCR block be "
        "assigned to one staff for months before block HEIGHT was recorded."),
    "DETAIL Q.STAFF_SKEW.thickness_px": (
        "the staff's measured printed line thickness, beside its wander. "
        "`staff_line_removal` measures thickness AGAIN, per cell, from the "
        "cell's own ink — deliberately, since it varies 0.06-0.31 spaces "
        "across the corpus — so this page-level figure is a second reading "
        "that nothing compares against the first."),

    # ── DETAIL, Q.INK — a PRODUCER shipped deliberately without a consumer
    #
    # ⚠️⚠️ THESE SEVEN ARE OPEN BY DESIGN AND MUST NOT BE READ AS AN OVERSIGHT.
    # `gather_ink` (flag `OMR_INK`, **default ON since 2026-09-17** —
    # this comment read `default OFF` until 2026-09-17 evening) is the
    # base ink layer Sean
    # asked for in `ASSUMPTIONS.md` A-DUR-5; it was built as the PRODUCER
    # ONLY, and no decision was wired to it in the same change, deliberately.
    # The reason is that the deliverable of that job is a REACH MEASUREMENT —
    # does unnamed ink line up across staves, against a null — and a consumer
    # landing in the same change would make that measurement unfalsifiable,
    # since a rule reading the rows would move the very numbers being used to
    # decide whether the rows are worth having.
    #
    # ⚠️ THE KEYS ARE SPELLED OUT AS LITERAL KWARGS AT THE EMIT SITE SO THIS
    # TOOL CAN SEE THEM, and that is itself a finding: this question reads the
    # AST for LITERAL keyword names, so a key passed as `**detail` never
    # enters the WRITTEN inventory at all -- and a key this tool does not know
    # is written can never be reported unread, whoever reads it.
    #
    # ⚠️ CHECKED EXACTLY, because the first wording of this comment said
    # "`gather_detections`' `bbox_page_px` has never been reported", which is
    # true and is the wrong grain: the bare NAME does appear, from gatherers
    # that spell it out. The blind spot is per `(quantity, key)` PAIR, which
    # is what this question reports in -- `Q.GLYPH_BOX.bbox_page_px`,
    # `Q.GLYPH_BOX.x_center_page` and `Q.GLYPH_BOX.category` are absent from
    # all 138 written pairs, because that gatherer passes them as
    # `**box_detail`. Widening the scan to follow a dict built in the same
    # function is ranked next work and was NOT taken here: it belongs to
    # whoever owns this tool, and it would surface findings across several
    # gatherers at once.
    #
    # Each entry LEAVES this list the day a decision reads it.
    "DETAIL Q.INK.ink_bbox_canonical": (
        "the component's box in the CELL's own canonical frame, beside the "
        "page-frame one. Kept because a cell-local consumer (a residue rule, "
        "which compares a component against this cell's own staff-line rows) "
        "wants the frame the rows are measured in, and converting back from "
        "page pixels would reintroduce the rounding the cell already paid."),
    "DETAIL Q.INK.ink_area_px": (
        "ink pixels in the component, as against the AREA OF ITS BOX. The "
        "pair is the discriminator a residue rule needs and neither half is "
        "enough: a staff-line remnant and a beam are both wide and flat, and "
        "what separates them is how densely they fill the rectangle."),
    # ⚠️⚠️ FOUR `Q.INK` KEYS LEFT THIS LIST ON 2026-09-17, AND THAT IS THE
    # TOOL WORKING. `ink_fill`, `ink_n_components`, `ink_detector_coverage`
    # and `ink_explained_by` were all recorded here as *gathered and read by
    # nothing*; `tools/omr/positional_store.py` now reads all four --
    # `ink_explained_by` most pointedly, since it is a LIST of the classes
    # overlapping a component and is the record's one existing piece of
    # many-to-many evidence. A CLOSED gap must LEAVE, so they are gone rather
    # than annotated. `ink_share_of_cell` stays: nothing reads it yet.
    "DETAIL Q.INK.ink_share_of_cell": (
        "this component's share of its cell's ink — the per-row half of "
        "`ink_n_components`. A component holding 0.9 of a cell is a merge, "
        "whatever its shape says."),

    # ── `Q.VERTICAL_RUN`: PRODUCER ONLY, and its first consumer is NAMED ────
    #
    # ⚠️⚠️ THE FIRST INTENDED CONSUMER OF ALL SEVEN IS ONE RULE: an ADJUDICATE
    # decision that asks WHAT KIND OF VERTICAL MARK this run is -- Sean's own
    # test, *a barline's two ends sit ON the outer staff lines; a stem's do
    # not* -- read against `Q.STAFF_LINES` in the page frame the rows now
    # carry. It does not exist. Nothing reads these DELIBERATELY: `Q.INK`'s
    # discipline, where a producer and its first consumer landing in one change
    # makes the reach measurement circular, so the reach figure would be a
    # measurement of the consumer.
    #
    # ⚠️ EACH ENTRY LEAVES THIS LIST THE DAY A DECISION READS IT, and the whole
    # block leaves when that rule lands. An entry kept past its closing is how
    # a gap list stops describing the tree; an entry removed early is how a
    # known gap becomes a false "someone reads it".
    #
    # ⚠️ THE FIVE PAGE-FRAME AND STAFF-SPACE KEYS ARE NOT LISTED HERE AND ARE
    # NOT READ EITHER -- `run_bbox_page_px`, `run_y_top_page`,
    # `run_y_bottom_page`, `run_x_center_page`, `run_width_spaces`,
    # `run_height_spaces`, `run_staff_space_px`. They go through a `**splat`
    # because they are DECLINED BY OMISSION on a cell that cannot supply the
    # frame, and this question reads the AST for LITERAL keyword names, so a
    # splatted key never enters the WRITTEN inventory at all. That blind spot
    # is already recorded above for `gather_detections`' own page box; naming
    # it here too because the page box is the POINT of this quantity and a
    # reader of this list would otherwise conclude it is read.
    "DETAIL Q.VERTICAL_RUN.run_outcome": (
        "WHICH of `detect_stems`' filters first refused this run, or that it "
        "was accepted -- the one field that did not exist anywhere before, "
        "because only survivors reached the record. It is a fact about the "
        "FILTER, never a name for the ink: the crop pass adjudicated the width "
        "cap's discards 33 of 33 REAL."),
    "DETAIL Q.VERTICAL_RUN.run_accepted": (
        "the boolean of `run_outcome`, beside it rather than derived at each "
        "read site. Kept because the two questions a consumer asks are "
        "different -- *did this survive* is a filter on the population, *why "
        "not* is the reason string -- and re-deriving the first by comparing "
        "against a vocabulary word is how the word gets restated."),
    "DETAIL Q.VERTICAL_RUN.run_refused_by_dimension": (
        "was it refused by one of the SIX dimension bounds, as against the "
        "relational pair rule. §9 of `docs/proposal-2026-09-18-boxing-is-a-"
        "decision.md` is the argument that all six are size windows on an "
        "object the engraver varies on purpose, so *how much of this "
        "population is refused BY DIMENSION* is the question that proposal "
        "asks and no instrument could answer. Derived from the vocabulary, so "
        "it cannot drift from the chain that produced it."),
    "DETAIL Q.VERTICAL_RUN.run_ink_area_px": (
        "ink pixels in the run, as against the area of its box -- the pair "
        "`run_ink_fill` completes. A barline and a stem are both thin and "
        "vertical; a merged blob that survived the opening is not, and what "
        "separates them is how densely the rectangle fills."),
    "DETAIL Q.VERTICAL_RUN.run_ink_fill": (
        "the density half of that pair. Kept apart from the area because a "
        "ratio alone cannot tell a two-pixel speck from a barline and an area "
        "alone cannot tell a hairline from a blob."),
    "DETAIL Q.VERTICAL_RUN.run_n_candidates": (
        "how many candidates this cell produced, on every row -- the "
        "`ink_n_components` precedent. A cell yielding fifty candidates and "
        "one yielding two are different evidence about the same accepted "
        "stroke, and a consumer that sees only its own row cannot tell."),
    "DETAIL Q.VERTICAL_RUN.staff_lines_erased": (
        "which RASTER this run was read off. `line_detection` prefers the "
        "erased variant and SILENTLY falls back to `cell.image`, and "
        "`capture.py` records that `Observation.frame` names a coordinate "
        "frame and never the raster -- so without this a whole-rung fallback "
        "would be indistinguishable from a thin page. `Q.STEM` carries the "
        "same key for the same reason and it is unread there too."),

    "DETAIL Q.STAFF_LINES.page_staff_index": (
        "the RASTER's own staff index — the join key back to `pws.staves`. "
        "Nothing downstream joins that way today; every consumer goes "
        "through the `Subject`. A debugging affordance."),
    "DETAIL Q.WEDGE_BOX.page_staff_index":
        "as `Q.STAFF_LINES.page_staff_index`.",
    # ⚠️⚠️ `Q.WEDGE_BOX.y_center_page` LEFT THIS LIST ON 2026-09-17 AND IT WAS
    # **NOT** GENUINELY CLOSED — recorded here because removing it silently
    # would turn a known gap into a false "someone reads it".
    # This question credits a key by its LEAF NAME, matched textually anywhere
    # under `tools/` (see the scan below), and `positional_store.py` reads
    # `y_center_page` off `Q.GLYPH_BOX` and `Q.INK` rows. It never touches a
    # `Q.WEDGE_BOX` row. So the hit is a COINCIDENCE OF A SHARED KEY NAME, the
    # textual-classifier limit `health.py` warns about in its own output
    # (*"the shape classifier is TEXTUAL"*), and the entry could not be kept
    # without failing `--check`. **The wedge's page-pixel centre is still
    # gathered and still unread in production.** Making this question
    # quantity-aware rather than leaf-aware is the repair; it is a change to
    # the tool, not to the gap list, and it is not taken here.
    "DETAIL Q.WEDGE_BOX.staff_bottom_line_page": (
        "the staff's own bottom line in page pixels — the origin a hairpin's "
        "band offset is measured from. Gathered and, in production, unread; "
        "the page-pixel frame `Q.ONSET_COLUMN` paid to learn about."),
    # ── positions.py, 2026-09-17. ⚠️ THESE TWO WERE INVISIBLE UNTIL THIS
    #    QUESTION LEARNED TO WALK A SECOND WRITE SITE — see `_row_writer_files`.
    #    Both belong to a module that is a PRODUCER with no consumer by design,
    #    so "named nowhere else" is the intended state, not a fault.
    "DETAIL Q.<loop-bound>.promoted_from": (
        "the row id a PROMOTED band position was measured off — the "
        "`CV_HAIRPINS` wedge box or the direction word. ⚠️ It is deliberately "
        "NOT `derived_from`: that would put the two rows in one `Log.closure` "
        "and make them ONE signal, which is the absorbed-witness state the "
        "promotion exists to leave. Recorded so a human can follow the join. "
        "⚠️ The quantity reads `<loop-bound>` because `_promote_from_log` "
        "takes it as a parameter — one helper, two quantities — which is this "
        "walker being honest rather than a defect."),
    "DETAIL Q.CELL_POSITION_BASIS.marks_unmeasured": (
        "how many marks a cell with NO five-line grid could not measure — a "
        "one-line percussion staff. The row is the REFUSAL and the count is "
        "its size, so a reader can tell *this page prints no rests* from "
        "*this staff has one line and twenty marks nobody could put on a "
        "grid*. Read by nothing, like the ten positions it accounts for."),
    "DETAIL Q.CELL_STAFF_SPACE.half_step": (
        "the half-step the spacing was doubled from. The duration reader "
        "consumes the SPACING; the half-step is the intermediate it came "
        "from, kept so a reader can check the doubling."),
    "DETAIL Q.CLEF_LOCATED.line_source": (
        "whether the clef's LINE was measured or defaulted — which is the "
        "distinction `clef_geometry` exists to make. ⚠️ WORTH OPENING: a "
        "clef whose line was defaulted is weaker evidence than one whose "
        "line was measured, and nothing downstream can currently tell."),
    "DETAIL Q.CLEF_LOCATED.locator_branch": (
        "the CV locator's own rejecting branch — `clef_locator`'s "
        "eight-branch taxonomy, which `probe_clef_rejection.py` "
        "cross-tabulates OUTSIDE the pipeline against hand-read clefs. A "
        "human's field."),
    "DETAIL Q.KEYSIG_RUN_POSITION.clefs_tried": (
        "which slot tables were fitted before the run was refused. ⚠️ It "
        "separates two states the abstention collapses — a run that fits NO "
        "table, and a header with no run at all — and the comment at the "
        "write site SAYS SO. Nothing reads the field that makes the "
        "separation."),
    "DETAIL Q.ROSTER_ENTRY.n_instruments": (
        "written by this session's own roster repair, so a reader scanning "
        "the record sees the roster's SIZE without parsing the value. "
        "Reported honestly rather than exempted: it is the same class as "
        "every row above, and a tool that excused its author's fields would "
        "not be worth running."),
}


def _gap_key(problem: str) -> Optional[str]:
    for key in KNOWN_GAPS:
        if problem.startswith(key):
            return key
    return None


def unaccounted(problems: Sequence[str]) -> List[str]:
    """Problems on no KNOWN_GAPS entry. These are what `--check` fails on."""
    return [p for p in problems if _gap_key(p) is None]


def stale_gaps(problems: Sequence[str]) -> List[str]:
    """KNOWN_GAPS entries nothing reports any more. A CLOSED gap must LEAVE."""
    hit = {_gap_key(p) for p in problems}
    return sorted(k for k in KNOWN_GAPS if k not in hit)


# ─────────────────────────────────────────────────────────────────────────────
# Shared AST helpers
# ─────────────────────────────────────────────────────────────────────────────

def _py_files(root: pathlib.Path) -> List[pathlib.Path]:
    return sorted(p for p in root.rglob("*.py") if "__pycache__" not in p.parts)


def _parse(path: pathlib.Path) -> Optional[ast.Module]:
    try:
        return ast.parse(path.read_text())
    except (SyntaxError, UnicodeDecodeError):       # noqa: BLE001
        return None


def _rel(path: pathlib.Path) -> str:
    try:
        return str(path.relative_to(_ROOT))
    except ValueError:
        return str(path)


def _declares_derived_check(path: pathlib.Path) -> bool:
    """Does this module declare itself a DERIVED CHECK rather than a consumer?

    ⚠️ READ FROM THE AST, not by a substring, so a mention of the name in a
    comment or a docstring cannot opt a real consumer out. The marker has to
    be a module-level `DERIVED_CHECK = True` assignment.
    """
    tree = _parse(path)
    if tree is None:
        return False
    for node in tree.body:
        if (isinstance(node, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id == "DERIVED_CHECK"
                        for t in node.targets)
                and isinstance(node.value, ast.Constant)
                and node.value.value is True):
            return True
    return False


def _tree_of(path: pathlib.Path) -> str:
    """Which TREE a call site lives in — and the distinction is the finding.

    A parameter only a BENCHMARK can supply has no production producer, which
    is a different fact from one nothing supplies at all and a different fact
    again from one the CLI supplies. Collapsing the three would have reported
    `roster` as fed the moment any probe passed one.
    """
    rel = _rel(path)
    if "/tests/" in rel or rel.split("/")[-1].startswith("test_"):
        return "test"
    if rel.startswith("benchmarks/"):
        return "benchmark"
    return "production"


# Helpers the remaining questions share (the PRODUCER question itself moved
# out — see the module docstring).
# ────────────────────────────────────────────────────────────────────────────────

#: Where a quantity is FILED and where a detail key is WRITTEN.
_PRODUCER_ROOTS = ("tools/omr/staged",)

#: Where a key might be READ.
_CALLSITE_ROOTS = ("tools", "benchmarks", "backend")


def _positional_order(fn: ast.FunctionDef) -> List[str]:
    """The parameters a POSITIONAL argument lands on, in order."""
    a = fn.args
    return [p.arg for p in (*a.posonlyargs, *a.args)]


# ─────────────────────────────────────────────────────────────────────────────
# 2. SCOPE — a declared input read where it is never filed
# ─────────────────────────────────────────────────────────────────────────────

#: `record`'s subject constructors, by the Kind they build.
_CTOR_KIND = {"DOCUMENT": "document", "page": "page", "system": "system",
              "staff": "staff", "cell": "cell", "glyph": "glyph"}


def _kind_of_expr(node: ast.AST, bound: Dict[str, str]) -> Optional[str]:
    """The Kind of a subject EXPRESSION, or None where it cannot be told.

    ⚠️ `None` IS NOT "fine". It flows into `unresolved`, which `--check` fails
    on. A resolver that silently returned a default would be this repo's own
    *a fallback must never convert "cannot tell" into a definite answer*,
    committed inside the tool written to catch that family.
    """
    if isinstance(node, ast.Name):
        return bound.get(node.id)
    if isinstance(node, ast.Attribute):
        # `R.DOCUMENT`
        if node.attr in _CTOR_KIND and isinstance(node.value, ast.Name):
            return _CTOR_KIND[node.attr]
        return None
    if isinstance(node, ast.Call):
        f = node.func
        if isinstance(f, ast.Attribute):
            # `R.staff(...)`, or `sub.at(Kind.CELL)`
            if f.attr in _CTOR_KIND:
                return _CTOR_KIND[f.attr]
            if f.attr == "at" and node.args:
                a = node.args[0]
                if isinstance(a, ast.Attribute):
                    return a.attr.lower()
            if f.attr == "parent":
                return None
        if isinstance(f, ast.Name) and f.id in _CTOR_KIND:
            return _CTOR_KIND[f.id]
    return None


class _SubjectKinds(ast.NodeVisitor):
    """Walk a module binding local names to subject Kinds, and record every
    `log.observe` / `log.abstain` site's subject Kind."""

    def __init__(self, seed: Optional[Dict[str, Dict[str, str]]] = None,
                 sigs: Optional[Dict[str, List[str]]] = None) -> None:
        self.bound: List[Dict[str, str]] = [{}]
        self.q_bound: List[Dict[str, List[str]]] = [{}]
        self.func: List[str] = []
        self.filed: Dict[str, Set[str]] = {}
        self.unresolved: List[Dict[str, Any]] = []
        #: func -> param -> Kind, learned from THIS module's own call sites.
        self.seed = seed or {}
        self.sigs = sigs or {}
        #: What this pass learned, for the next round of the fixpoint.
        self.arg_kinds: Dict[Tuple[str, str], Set[Optional[str]]] = {}

    # ── scopes ──────────────────────────────────────────────────────────────
    def visit_FunctionDef(self, node):                       # noqa: N802
        self.func.append(node.name)
        frame = dict(self.bound[-1])
        frame.update(self.seed.get(node.name, {}))
        self.bound.append(frame)
        self.q_bound.append(dict(self.q_bound[-1]))
        self.generic_visit(node)
        self.q_bound.pop()
        self.bound.pop()
        self.func.pop()

    def visit_Assign(self, node):                            # noqa: N802
        kind = _kind_of_expr(node.value, self.bound[-1])
        if kind:
            for t in node.targets:
                if isinstance(t, ast.Name):
                    self.bound[-1][t.id] = kind
        self.generic_visit(node)

    def visit_For(self, node):                               # noqa: N802
        # ⚠️ LOOP-BOUND QUANTITIES ARE REAL AND THE FIRST DRAFT OF
        # `gather_coverage` MISSED THEM: `gather_cv_lines` writes
        # `for quantity, kind in ((Q.STEM, "stems"), (Q.BEAM_STROKE, "beams"))`
        # and a visitor reading only `Q.X` literals at the call site reports
        # `Q.STEM` as never observed. Inherited rather than re-derived.
        frame = dict(self.q_bound[-1])
        targets = (node.target.elts if isinstance(node.target, ast.Tuple)
                   else [node.target])
        rows = (node.iter.elts
                if isinstance(node.iter, (ast.Tuple, ast.List)) else [])
        for pos, tgt in enumerate(targets):
            if not isinstance(tgt, ast.Name):
                continue
            found: List[str] = []
            for row in rows:
                cells = (row.elts if isinstance(row, (ast.Tuple, ast.List))
                         else [row])
                if pos < len(cells):
                    q = _q_literal(cells[pos])
                    if q and q not in found:
                        found.append(q)
            if found:
                frame[tgt.id] = found
        self.q_bound.append(frame)
        self.generic_visit(node)
        self.q_bound.pop()

    # ── the sites ───────────────────────────────────────────────────────────
    def visit_Call(self, node):                              # noqa: N802
        f = node.func
        # ⚠️ INTERPROCEDURAL, AND WITHOUT IT SIX SITES READ AS UNRESOLVED.
        # `_observe_ladder(log, g, ...)` and `_gather_keysig_markers(log, sub,
        # ...)` take their subject as a PARAMETER, so a walker that only
        # follows local assignments cannot say what Kind they file at. The
        # callers know. Learned here and fed back in the next round.
        callee = f.id if isinstance(f, ast.Name) else None
        if callee and callee in self.sigs:
            order = self.sigs[callee]
            for i, arg in enumerate(node.args):
                if isinstance(arg, ast.Starred) or i >= len(order):
                    break
                self.arg_kinds.setdefault((callee, order[i]), set()).add(
                    _kind_of_expr(arg, self.bound[-1]))
            for kw in node.keywords:
                if kw.arg:
                    self.arg_kinds.setdefault((callee, kw.arg), set()).add(
                        _kind_of_expr(kw.value, self.bound[-1]))
        verb = f.attr if isinstance(f, ast.Attribute) else None
        if verb in ("observe", "abstain") and node.args:
            kind = _kind_of_expr(node.args[0], self.bound[-1])
            quantities = self._quantities(node)
            where = f"{self.func[-1] if self.func else '<module>'}:{node.lineno}"
            shape = (_shape_of(node.args[0], self.bound[-1])
                     if kind is None else "")
            for q in quantities or ["<loop-bound>"]:
                if kind is None:
                    self.unresolved.append({"quantity": q, "where": where,
                                            "shape": shape})
                else:
                    self.filed.setdefault(q, set()).add(kind)
        self.generic_visit(node)

    def _quantities(self, node: ast.Call) -> List[str]:
        out: List[str] = []
        for arg in list(node.args[:3]):
            q = _q_literal(arg)
            if q:
                out.append(q)
            elif isinstance(arg, ast.Name):
                out.extend(self.q_bound[-1].get(arg.id, []))
        return out


def _shape_of(node: ast.AST, bound: Dict[str, str]) -> str:
    """WHY a subject expression could not be resolved — its syntactic shape.

    ⚠️ NAMING THE SHAPE IS WHAT MAKES `unresolved` AN INVENTORY RATHER THAN A
    SHRUG. "11 sites could not be derived" cannot be put on a gap list with a
    reason and cannot tell a NEW unresolvable shape from an old one; *"these
    eleven are `Subject.from_key`, whose Kind is in the key at runtime"* can,
    and a twelfth site of a different shape then fails `--check`.
    """
    if isinstance(node, ast.Call):
        f = node.func
        if isinstance(f, ast.Attribute):
            root = (f.value.id if isinstance(f.value, ast.Name) else "?")
            return f"{root}.{f.attr}()"
        if isinstance(f, ast.Name):
            return f"{f.id}()"
    if isinstance(node, ast.Name):
        return f"local '{node.id}' (bound from a collection or a caller)"
    if isinstance(node, ast.Subscript):
        return "subscript"
    return type(node).__name__


def _q_literal(node: ast.AST) -> Optional[str]:
    if (isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name)
            and node.value.id == "Q"):
        return node.attr
    return None


def _walk_gather() -> "_SubjectKinds":
    """Walk `gather.py` to a FIXPOINT over its own parameter bindings.

    Round 1 learns what Kind each call site passes; round 2 files those on the
    callee's parameters and re-walks; repeat until nothing new is learned. A
    parameter whose call sites DISAGREE, or any one of which is unresolved,
    stays unbound — ⚠️ never resolved to the majority, because a subject Kind
    that "cannot be told" must not be spelled as one that can.
    """
    tree = _parse(_HERE / "gather.py")
    if tree is None:
        return _SubjectKinds()
    sigs = {n.name: _positional_order(n) for n in ast.walk(tree)
            if isinstance(n, ast.FunctionDef)}
    seed: Dict[str, Dict[str, str]] = {}
    walker = _SubjectKinds(seed, sigs)
    for _ in range(4):
        walker = _SubjectKinds(seed, sigs)
        walker.visit(tree)
        grown = False
        for (fn, param), kinds in walker.arg_kinds.items():
            if None in kinds or len(kinds) != 1:
                continue              # ambiguous or untellable — leave unbound
            kind = next(iter(kinds))
            if seed.get(fn, {}).get(param) != kind:
                seed.setdefault(fn, {})[param] = kind
                grown = True
        if not grown:
            break
    return walker


def filed_kinds() -> Tuple[Dict[str, Set[str]], List[Dict[str, Any]]]:
    """Which Kind each quantity is FILED at — gather, verdicts and effects.

    Three producers, because a quantity can be written by any of the three
    stages and a check that read only GATHER would report every verdict-fed
    decision as broken.
    """
    from . import adjudicate as A
    from . import adjudicators  # noqa: F401  -- fills REGISTRY
    from . import consequences  # noqa: F401  -- fills RULES
    from . import evaluate as E
    from .record import Q

    by_value = {getattr(Q, n): n for n in vars(Q)
                if n.isupper() and not n.startswith("_")}

    walker = _walk_gather()
    filed: Dict[str, Set[str]] = {k: set(v) for k, v in walker.filed.items()}

    A._ensure_decisions()
    for spec in A.REGISTRY.values():
        name = by_value.get(spec.quantity)
        if name:
            filed.setdefault(name, set()).add(spec.scope.value)
    E._ensure_rules()
    for r in E.RULES:
        name = by_value.get(r.effect)
        if name:
            filed.setdefault(name, set()).add(r.scope.value)
    return filed, walker.unresolved


def _reads(spec) -> Tuple[Set[str], Set[str]]:
    """`(read at EXACT on its own subject, read with a reach of its own)`.

    ⚠️⚠️ THE SPLIT IS THE WHOLE CHECK, AND COLLAPSING IT MADE THE FIRST DRAFT
    REPORT 28 FALSE TRAPS. A decision at SYSTEM scope reading `Q.EVENT`,
    filed at CELL, looks broken — and is not: it reads DOWNWARD, through an
    explicit `subject=` or `scope=`, which is correct and common. A read
    carrying either kwarg has its reach decided by an expression this tool
    cannot evaluate, so it is EXCLUDED from the verdict rather than guessed
    at. What survives in the first set is the read whose reach is fixed by
    the decision's own declaration — the population where a Kind mismatch is
    unconditionally a bug.
    """
    import inspect
    if spec.stub:
        return set(), set()
    try:
        inspect.getsource(spec.fn)
    except OSError:                                          # noqa: BLE001
        return set(), set()
    mod_path = pathlib.Path(inspect.getfile(spec.fn))
    mod = _parse(mod_path)
    if mod is None:
        return set(), set()
    # ⚠️ The decision's own MODULE HELPERS count as the decision reading, the
    # same allowance `inventory._never_read` makes — `adjudicate_clef` asks
    # for `clef_glyph` through `_detector_terms(ev)`. A check that looked only
    # at the decision body would measure code STYLE.
    helpers = {n.name: n for n in ast.walk(mod)
               if isinstance(n, ast.FunctionDef)}
    start = helpers.get(spec.name)
    if start is None:
        return set(), set()

    exact: Set[str] = set()
    scoped: Set[str] = set()
    seen: Set[str] = set()
    frontier: List[ast.AST] = [start]
    for _ in range(3):
        nxt: List[ast.AST] = []
        for node in frontier:
            for a in ast.walk(node):
                if not isinstance(a, ast.Call):
                    continue
                f = a.func
                called = (f.attr if isinstance(f, ast.Attribute)
                          else f.id if isinstance(f, ast.Name) else None)
                if called in ("rows", "state", "verdict", "verdicts",
                              "refusals", "admitted") and a.args:
                    q = _q_literal(a.args[0])
                    if not q:
                        continue
                    kws = {k.arg for k in a.keywords}
                    (scoped if ("subject" in kws or "scope" in kws)
                     else exact).add(q)
                elif called in helpers and called not in seen:
                    seen.add(called)
                    nxt.append(helpers[called])
        frontier = nxt
        if not frontier:
            break
    return exact, scoped


def frames() -> Dict[str, Any]:
    """Declared inputs read at a Kind where nothing files them."""
    from . import adjudicate as A
    from . import adjudicators  # noqa: F401
    from .record import Q

    by_value = {getattr(Q, n): n for n in vars(Q)
                if n.isupper() and not n.startswith("_")}
    filed, unresolved = filed_kinds()

    A._ensure_decisions()
    broken: List[Dict[str, Any]] = []
    latent: List[Dict[str, Any]] = []
    healthy = 0
    reach_elsewhere = 0
    unknown: List[Dict[str, Any]] = []
    for spec in sorted(A.REGISTRY.values(), key=lambda s: s.name):
        read_at = spec.scope.value
        reads, scoped = _reads(spec)
        for q in sorted(vars(Q)):
            value = getattr(Q, q, None)
            if not isinstance(value, str) or value not in spec.wants:
                continue
            where = filed.get(q)
            if not where:
                # Not filed anywhere this tool can see. `gather_coverage`
                # owns that question; reported, never guessed at.
                unknown.append({"decision": spec.name, "quantity": q})
                continue
            row = {"decision": spec.name, "quantity": q, "reads_at": read_at,
                   "filed_at": sorted(where),
                   "fix": ("scope=Scope.SELF_AND_ANCESTORS"
                           if _is_ancestor(read_at, where) else "subject=")}
            if q in reads:
                if read_at in where:
                    healthy += 1
                else:
                    broken.append(row)
            elif q in scoped:
                # Read with a reach of its own. Correct and common — a
                # SYSTEM-scoped decision reading its own bars' events. Not
                # judged here; counted, so the exclusion is visible.
                reach_elsewhere += 1
            elif read_at not in where:
                # ⚠️⚠️ LATENT — DECLARED, FILED, AND UNREADABLE THE MOMENT
                # ANYBODY READS IT THE OBVIOUS WAY. This tier is the point of
                # the whole check: the four frame faults CLAUDE.md records
                # were each written, shipped and then found by a test
                # asserting the answer came out. A `wants` entry whose
                # quantity is filed only at a Kind `Scope.EXACT` cannot reach
                # is a TRAP ARMED FOR THE NEXT PERSON, and it is visible
                # BEFORE the consumer exists. `instrument declares
                # roster_entry` is exactly that trap: the roster is filed on
                # the DOCUMENT and the decision runs at STAFF.
                latent.append(row)
    return {"broken": broken, "latent": latent, "healthy": healthy,
            "reach_elsewhere": reach_elsewhere,
            "unknown": unknown, "unresolved": unresolved,
            "filed": {k: sorted(v) for k, v in sorted(filed.items())},
            "_q_names": sorted(by_value.values())}


_DEPTH = {"document": 0, "page": 1, "system": 2, "staff": 3, "cell": 4,
          "glyph": 5}


def _is_ancestor(read_at: str, filed_at: Set[str]) -> bool:
    """Would `SELF_AND_ANCESTORS` reach it? — i.e. is it filed ABOVE."""
    mine = _DEPTH.get(read_at)
    return mine is not None and any(
        _DEPTH.get(k, 99) < mine for k in filed_at)


# ─────────────────────────────────────────────────────────────────────────────
# 3. DETAIL — a key written into a row and read by nobody
# ─────────────────────────────────────────────────────────────────────────────

#: Keyword arguments of `observe`/`abstain` that are the ROW's own structure
#: rather than a detail key. Read off `record.Log.observe`'s signature, never
#: typed — see `_row_kwargs`.
_ROW_KWARG_SOURCES = ("observe", "abstain")


def _row_kwargs() -> Set[str]:
    """`Log.observe`/`Log.abstain`'s own named parameters, DERIVED.

    ⚠️ A HAND LIST HERE WOULD ROT THE DAY A PARAMETER IS ADDED, and it would
    rot SILENTLY — a new structural parameter would start being reported as
    an unread detail key. `ARITY_FIELDS` is this repo's worked example of
    answering a hand list with a hand list.
    """
    import inspect
    from .record import Log
    out: Set[str] = set()
    for name in _ROW_KWARG_SOURCES:
        fn = getattr(Log, name, None)
        if fn is None:
            continue
        for p in inspect.signature(fn).parameters.values():
            if p.kind is not inspect.Parameter.VAR_KEYWORD:
                out.add(p.name)
    return out - {"self"}


def _row_writer_files() -> Set[str]:
    """Staged modules that WRITE detail keys onto rows. ⚠️ DERIVED.

    ⚠️⚠️ **THE FIFTH INSTANCE OF *THE WRITE SITE IS NOT A READ*, AND THE FIRST
    WHERE THE WRITE SITE IS A SECOND MODULE.** The three exclusions below this
    function — a test, a benchmark probe, this module's own gap list — were
    each found by watching a live finding go silent. This one was found the
    same way: `positions.py` landed ten producers, its `_band_core` writes
    `staff_bottom_line_page` like `gather_wedge_boxes` does, and because the
    write-site exclusion was the hard-coded string `"gather.py"` that second
    WRITE registered as a READ and closed `DETAIL Q.WEDGE_BOX.
    staff_bottom_line_page` — a gap that is still completely open.

    A hand-list would have grown the same hole again on the next module, so
    the set is derived from `reach.STAGE_OF_FILE`: every staged file whose
    stage is GATHER is a row writer, is walked for WRITES, and is excluded
    from the READ scan. ⚠️ The import is local because `reach` imports this
    package too and both are instruments rather than stages.
    """
    from .reach import STAGE_OF_FILE
    return {name for name, stage in STAGE_OF_FILE.items() if stage == "GATHER"}


def details() -> Dict[str, Any]:
    """Detail keys written on rows, and whether anything mentions them."""
    structural = _row_kwargs()
    written: Dict[str, List[str]] = {}
    writers = _row_writer_files()
    trees = [t for t in (_parse(_HERE / n) for n in sorted(writers))
             if t is not None]

    # Walk for the detail keys, alongside the quantity each belongs to.
    class Keys(ast.NodeVisitor):
        def __init__(self) -> None:
            self.func: List[str] = []
            self.q_bound: List[Dict[str, List[str]]] = [{}]

        def visit_FunctionDef(self, node):                   # noqa: N802
            self.func.append(node.name)
            self.generic_visit(node)
            self.func.pop()

        def visit_Call(self, node):                          # noqa: N802
            f = node.func
            verb = f.attr if isinstance(f, ast.Attribute) else None
            if verb in ("observe", "abstain") and node.args:
                qs = [q for q in (_q_literal(a) for a in node.args[:3]) if q]
                q = qs[0] if qs else "<loop-bound>"
                for kw in node.keywords:
                    if kw.arg is None or kw.arg in structural:
                        continue
                    written.setdefault(f"Q.{q}.{kw.arg}", []).append(
                        f"{self.func[-1] if self.func else '<module>'}"
                        f":{node.lineno}")
            self.generic_visit(node)

    for tree in trees:
        Keys().visit(tree)

    # Who READS a key. Deliberately generous: ANY mention of the bare name as
    # a string literal or attribute anywhere outside gather.py counts, so what
    # survives is a key the rest of the tree does not name at all.
    mentioned: Set[str] = set()
    for rootname in _CALLSITE_ROOTS:
        base = _ROOT / rootname
        if not base.is_dir():
            continue
        for path in _py_files(base):
            if path.name in writers and "staged" in path.parts:
                continue              # the write site is not a read
            # ⚠️⚠️ A TEST NAMING A KEY IS NOT A CONSUMER OF IT, and leaving
            # tests in made this question report its own findings as closed:
            # the moment this module's test file asserted
            # `Q.MARGIN_LABEL.reader_confidence` is unread, the scan found
            # that string in `tools/` and declared it READ. A check whose own
            # test silences it is the vacuous-assertion family, arriving
            # through the back door.
            if _tree_of(path) == "test":
                continue
            # ⚠️⚠️ AND NOR IS A BENCHMARK PROBE — THE THIRD INSTANCE OF THE
            # SAME FAMILY, FOUND 2026-09-17 WHEN `Q.INK` LANDED. That
            # quantity ships as a PRODUCER with no consumer, deliberately, and
            # all seven of its keys were written into `KNOWN_GAPS` to say so.
            # The moment its measuring probes were committed, `--check` went
            # RED reporting FOUR of the seven as STALE — closed — because a
            # probe under `benchmarks/` had read them to take the measurement
            # the gap entries exist to describe. **The instrument that
            # measures a gap is not a consumer that closes it.**
            #
            # ⚠️ THE ARGUMENT WAS ALREADY WRITTEN DOWN IN THIS MODULE AND IS
            # APPLIED NOWHERE. `_tree_of`'s own docstring says collapsing the
            # three trees "would have reported `roster` as fed the moment any
            # probe passed one" -- and it was written for the PRODUCER
            # question, which has since MOVED OUT to `tools/omr/no_producer.py`
            # (this module's docstring says so). Checked rather than assumed:
            # `grep -n benchmark tools/omr/no_producer.py` returns one line and
            # it is a path in a comment, so that tool does not make the
            # distinction either. So before this line `_tree_of` was reachable
            # from exactly one caller -- the `test` exclusion below -- and the
            # `benchmark` branch it defines was dead. ⚠️ Whether the producer
            # question WANTS it is a separate job and is not decided here.
            #
            # ⚠️⚠️ AND THE FIRST DRAFT OF THIS COMMENT CLAIMED THE CHANGE WAS
            # CONFINED TO THE FOUR `Q.INK` KEYS THAT EXPOSED IT. IT IS NOT,
            # AND THE CLAIM WAS WRITTEN BEFORE THE MEASUREMENT — the exact
            # shape CLAUDE.md records as *asserting a mechanism without
            # measuring it*. Run: it surfaces **SEVEN more keys**, listed in
            # `KNOWN_GAPS` below, every one of them a detail key whose ONLY
            # reader anywhere in the tree is a benchmark probe. They were
            # not new faults; they were invisible.
            if _tree_of(path) == "benchmark":
                continue
            # ⚠️⚠️ AND NOR IS THIS MODULE'S OWN GAP LIST — FOUND THE HARD
            # WAY, BY WATCHING THIS QUESTION GO TO ZERO. Writing each unread
            # key into `KNOWN_GAPS` with its reason put every one of those
            # names into a file under `tools/`, the scan found them, and the
            # question that had just reported eighteen findings reported
            # NONE. **The inventory written to account for the findings
            # closed the check that produced them** — the vacuous-assertion
            # family arriving inside the tool built to catch it, one turn
            # after its docstring quotes `health.py` reporting "EMPTY CELLS:
            # none" by accident. A gap list naming a key is not a consumer of
            # it, for the same reason a test naming one is not.
            if path.resolve() == pathlib.Path(__file__).resolve():
                continue
            # ⚠️⚠️ NOR IS A SIBLING INSTRUMENT — THE FOURTH INSTANCE OF THE
            # SAME FAMILY, FOUND 2026-09-17 WHEN `staged.capture` LANDED.
            # That module AUDITS detail keys: it asks, per notation family,
            # whether a row records which raster it was measured on, so it
            # necessarily names `staff_lines_erased` in its own source. It
            # lives in `tools/omr/staged/`, so `_tree_of` calls it
            # PRODUCTION — and the moment it was committed, the two
            # `staff_lines_erased` entries below read as STALE and `--check`
            # went red on a key still consumed by nothing.
            #
            # The three exclusions above are one rule and this is its fourth
            # application: **a gap list, a test, a benchmark probe and an
            # auditor all NAME a key without CONSUMING it.** What separates
            # them from a real reader is not the tree they live in — this one
            # lives in the same tree as the consumers — so the module DECLARES
            # itself with a module-level `DERIVED_CHECK = True`.
            #
            # ⚠️ IT FAILS LOUD, WHICH IS WHY A MARKER IS ACCEPTABLE HERE. A
            # new instrument that forgets it does not silence this question;
            # it makes the affected entries report STALE, which `--check`
            # fails on. The dangerous direction — an instrument silently
            # closing a gap — is the one the marker's absence cannot cause.
            if _declares_derived_check(path):
                continue
            try:
                text = path.read_text()
            except (OSError, UnicodeDecodeError):            # noqa: BLE001
                continue
            for key in written:
                leaf = key.rsplit(".", 1)[1]
                if f'"{leaf}"' in text or f"'{leaf}'" in text \
                        or f".{leaf}" in text:
                    mentioned.add(key)

    unread = sorted(k for k in written if k not in mentioned)
    return {"written": len(written), "read": len(mentioned),
            "unread": [{"key": k, "sites": written[k][:3]} for k in unread]}


# ─────────────────────────────────────────────────────────────────────────────
# 4. ROUNDTRIP — a field declared on a serialisable class and dropped by its
#    own projection
# ─────────────────────────────────────────────────────────────────────────────

def roundtrip() -> Dict[str, Any]:
    """Fields a class declares and its own `to_json` does not emit.

    ⚠️⚠️ **THIS IS THE `works.json` `lines` FAULT, ONE LAYER IN.** That field
    was computed on the way in and dropped by **four separate projections**,
    and the repair that worked was to DERIVE the shape from the function that
    consumes it. Here the producer and the projection sit in one class, so
    the comparison is exact: the dataclass's declared fields against the keys
    its `to_json` writes.

    ⚠️ **A DROPPED FIELD THAT IS READ IS A DIFFERENT FACT FROM ONE THAT IS
    NOT**, and they are reported apart. A field nobody reads is dead weight; a
    field a real consumer reads **cannot survive a saved record**, so the
    consumer silently gets the default on every replay. `Verdict.
    single_pass_revision` is the second kind: it is the fixpoint guard's one
    sanctioned exemption, and a replayed record comes back `False`.

    ⚠️ Deliberately NOT extended to `from_json`: a class may legitimately
    re-derive a field on the way in. What it may not do is fail to WRITE one
    its own consumer reads.
    """
    out_dropped: List[Dict[str, Any]] = []
    emitted_total = 0
    classes = 0
    for rootname in _PRODUCER_ROOTS:
        for path in _py_files(_ROOT / rootname):
            tree = _parse(path)
            if tree is None:
                continue
            src = path.read_text()
            for node in ast.walk(tree):
                if not isinstance(node, ast.ClassDef):
                    continue
                to_json = next((n for n in node.body
                                if isinstance(n, ast.FunctionDef)
                                and n.name == "to_json"), None)
                if to_json is None:
                    continue
                classes += 1
                declared = [n.target.id for n in node.body
                            if isinstance(n, ast.AnnAssign)
                            and isinstance(n.target, ast.Name)
                            and not n.target.id.startswith("_")]
                # ⚠️⚠️ THE FIELD'S VALUE, NOT ITS NAME — AND THE FIRST CUT
                # COMPARED NAMES AND REPORTED A RENAME AS A DROP. `Witness`
                # emits `self.row_id` under the key `"row"`; the field
                # survives the round trip perfectly and a name comparison
                # calls it dropped. A check that cannot tell a RENAME from a
                # DROP has one false positive per renamed key and trains the
                # next reader to skim the list.
                emitted: Set[str] = set()
                for n in ast.walk(to_json):
                    if (isinstance(n, ast.Attribute)
                            and isinstance(n.value, ast.Name)
                            and n.value.id == "self"):
                        emitted.add(n.attr)
                emitted_total += len(emitted & set(declared))
                for f in declared:
                    if f in emitted:
                        continue
                    # ⚠️ "READ" IS COUNTED GENEROUSLY — any `.field` anywhere
                    # in the package outside this class's own `to_json`. What
                    # survives as `dropped_and_read` is a field with a real
                    # consumer that a saved record cannot carry to it.
                    n_uses = sum(
                        p.read_text().count(f".{f}")
                        for p in _py_files(_ROOT / rootname))
                    out_dropped.append({
                        "class": node.name, "field": f,
                        "file": _rel(path), "line": node.lineno,
                        "read": n_uses > 1,
                        "uses": n_uses})
    return {"classes_with_to_json": classes,
            "fields_emitted": emitted_total,
            "dropped": sorted(out_dropped,
                              key=lambda r: (not r["read"], r["class"],
                                             r["field"]))}


# ─────────────────────────────────────────────────────────────────────────────
# The report
# ─────────────────────────────────────────────────────────────────────────────

def controls(rep: Dict[str, Any]) -> Dict[str, Any]:
    """⚠️⚠️ THE POSITIVE CONTROLS, AND THEY ARE WHY A CLEAN RUN MEANS
    ANYTHING.

    Each question reports how many cases it found HEALTHY. A zero there does
    not mean the pipeline is clean — it means the question never reached its
    subject, which is exactly how the flag-direction guard's first version
    passed vacuously after descending THROUGH `environ.get` onto `os.environ`.
    `--check` exits non-zero on any zero here, BEFORE it looks at a single
    finding.
    """
    return {
        "frame_reads_that_line_up": rep["frames"]["healthy"],
        "frame_reads_with_their_own_reach": rep["frames"]["reach_elsewhere"],
        "frame_quantities_filed": len(rep["frames"]["filed"]),
        "detail_keys_written": rep["details"]["written"],
        "detail_keys_read": rep["details"]["read"],
        "roundtrip_classes_with_to_json":
            rep["roundtrip"]["classes_with_to_json"],
        "roundtrip_fields_emitted": rep["roundtrip"]["fields_emitted"],
    }


def problems(rep: Dict[str, Any]) -> List[str]:
    out: List[str] = []
    # ⚠️ ONE PROBLEM PER PARAMETER, NOT PER LINK. `roster` is declared on
    # three functions of one chain and is ONE fault; reporting it three times
    # inflates the count and makes the list read as three separate repairs.
    for b in rep["frames"]["broken"]:
        out.append(f"SCOPE {b['decision']} reads Q.{b['quantity']} at "
                   f"{b['reads_at']}, filed at {'/'.join(b['filed_at'])} "
                   f"— the declared input CANNOT ANSWER (fix: {b['fix']})")
    for b in rep["frames"]["latent"]:
        out.append(f"SCOPE-LATENT {b['decision']} declares Q.{b['quantity']} "
                   f"(scope {b['reads_at']}) filed only at "
                   f"{'/'.join(b['filed_at'])} — an EXACT read would return "
                   f"nothing (needs: {b['fix']})")
    for u in rep["frames"]["unresolved"]:
        out.append(f"UNRESOLVED {u['shape']} — gather site {u['where']} "
                   f"({u['quantity']}): subject Kind could not be derived")
    for d in rep["details"]["unread"]:
        out.append(f"DETAIL {d['key']} — written at {d['sites'][0]}, "
                   f"named nowhere else in the tree")
    for r in rep["roundtrip"]["dropped"]:
        out.append(
            f"ROUNDTRIP {r['class']}.{r['field']} — declared at "
            f"{r['file']}:{r['line']} and ABSENT from {r['class']}.to_json"
            + (f", and READ ({r['uses']} mentions): a saved record cannot "
               f"carry it to its consumer" if r["read"]
               else " (read by nothing)"))
    return out


def report() -> Dict[str, Any]:
    rep = {"frames": frames(), "details": details(),
           "roundtrip": roundtrip()}
    rep["controls"] = controls(rep)
    rep["problems"] = problems(rep)
    rep["unaccounted"] = unaccounted(rep["problems"])
    rep["stale_gaps"] = stale_gaps(rep["problems"])
    return rep


def with_run(rep: Dict[str, Any], run_path: str) -> Dict[str, Any]:
    """Confirm the FRAME table against a real record's own subject keys.

    ⚠️ THE STATIC SIDE IS THE CHECK AND THIS IS THE CORROBORATION, not the
    other way round: a record can only show where a quantity WAS filed on the
    pages that ran, so an empty page reads exactly like a quantity nothing
    files. The static derivation answers for the tree; this answers for one
    run, and where they disagree the disagreement is the finding.
    """
    data = json.loads(pathlib.Path(run_path).read_text())
    from .record import Q
    by_value = {getattr(Q, n): n for n in vars(Q)
                if n.isupper() and not n.startswith("_")}
    # ⚠️⚠️ `record`, NOT `log` — AND THE FIRST DRAFT READ `log`, WHICH IS THE
    # EXACT BUG CLASS THIS MODULE EXISTS TO CATCH, COMMITTED INSIDE IT.
    # `pipeline.run_staged` writes `result["record"] = log.to_json()`; a
    # reader of `data["log"]` finds nothing on EVERY real record and reports
    # `agree: 0` — which reads as *"the static table disagrees with every
    # run"* rather than as *"this consumer is looking in the wrong place"*. It
    # was found by grepping the producer instead of trusting the name, which
    # is the whole method. The key is DERIVED from `Log.to_json`'s own call
    # site rather than hard-coded a second time.
    record = data.get("record")
    if record is None:
        raise KeyError(
            "this record has no 'record' key. `pipeline.run_staged` writes "
            "`result['record'] = log.to_json()`; if that name has changed, "
            "change it HERE too rather than adding a fallback — a fallback "
            "would convert 'I cannot find the rows' into 'there are no rows'.")
    seen: Dict[str, Set[str]] = {}
    for bucket in ("observations", "abstentions", "verdicts"):
        for row in (record or {}).get(bucket, []) or []:
            name = by_value.get(row.get("quantity"), row.get("quantity"))
            key = str(row.get("subject") or "")
            if name and key:
                seen.setdefault(name, set()).add(key.split("/")[0])
    static = rep["frames"]["filed"]
    agree, only_static, only_run = [], [], []
    for q, kinds in sorted(seen.items()):
        s = set(static.get(q, ()))
        (agree if s == kinds else only_run).append(
            {"quantity": q, "static": sorted(s), "in_run": sorted(kinds)})
    for q in sorted(set(static) - set(seen)):
        only_static.append(q)
    rep["run"] = {"path": run_path, "agree": len(agree),
                  "disagree": only_run,
                  "static_only_not_on_these_pages": only_static}
    return rep


def render(rep: Dict[str, Any]) -> str:
    L: List[str] = []
    A = L.append
    A("═══ DOES THE INFORMATION REACH ITS CONSUMER? ═══════════════════════")
    A("")
    A("1. FRAME — a declared input read where it is never filed")
    if not rep["frames"]["broken"]:
        A("   none")
    for b in rep["frames"]["broken"]:
        A("  ⚠️ %s reads Q.%s at %s; filed at %s"
          % (b["decision"], b["quantity"], b["reads_at"],
             "/".join(b["filed_at"])))
        A("        fix: %s" % b["fix"])
    if rep["frames"]["latent"]:
        A("   LATENT — declared, filed elsewhere, unreadable the obvious way:")
    for b in rep["frames"]["latent"]:
        A("  ⚠️ %s declares Q.%s (scope %s), filed at %s — needs %s"
          % (b["decision"], b["quantity"], b["reads_at"],
             "/".join(b["filed_at"]), b["fix"]))
    if rep["frames"]["unknown"]:
        A("   (filed nowhere this tool sees — `gather_coverage` owns these: %s)"
          % ", ".join(sorted({u["quantity"] for u in rep["frames"]["unknown"]})))
    if rep["frames"]["unresolved"]:
        A("   ⚠️ UNRESOLVED gather sites: %d"
          % len(rep["frames"]["unresolved"]))
    A("")
    A("2. DETAIL — a key written on a row and named nowhere else")
    if not rep["details"]["unread"]:
        A("   none")
    for d in rep["details"]["unread"]:
        A("  ⚠️ %-44s %s" % (d["key"], d["sites"][0]))
    A("")
    A("3. ROUNDTRIP — a field declared and dropped by its own `to_json`")
    if not rep["roundtrip"]["dropped"]:
        A("   none")
    for r in rep["roundtrip"]["dropped"]:
        A("  %s %s.%s  %s"
          % ("⚠️⚠️" if r["read"] else "  ⚠️", r["class"], r["field"],
             f"READ ({r['uses']} mentions) — a saved record cannot carry it"
             if r["read"] else "(read by nothing)"))
    A("")
    A("── POSITIVE CONTROLS (a zero means the question did not run) ────────")
    for k, v in rep["controls"].items():
        A("   %-36s %s" % (k, v))
    if "run" in rep:
        A("")
        A("── against %s" % rep["run"]["path"])
        A("   quantities whose filed Kinds AGREE: %d" % rep["run"]["agree"])
        for d in rep["run"]["disagree"][:12]:
            A("   ⚠️ %-28s static %s / in run %s"
              % (d["quantity"], d["static"], d["in_run"]))
    A("")
    A("── %d problems, %d unaccounted, %d stale gap entries"
      % (len(rep["problems"]), len(rep["unaccounted"]),
         len(rep["stale_gaps"])))
    for p in rep["unaccounted"]:
        A("   NOT ON KNOWN_GAPS: %s" % p)
    for s in rep["stale_gaps"]:
        A("   STALE (closed — must LEAVE KNOWN_GAPS): %s" % s)
    return "\n".join(L)


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--run", default=None,
                    help="a staged record, to corroborate the FRAME table")
    args = ap.parse_args(argv)

    rep = report()
    if args.run:
        rep = with_run(rep, args.run)
    print(json.dumps(rep, indent=2, default=str) if args.json else render(rep))

    if not args.check:
        return 0
    # ⚠️ THE CONTROLS ARE CHECKED FIRST AND SEPARATELY. A dead question
    # reports no problems, which is indistinguishable from a clean tree
    # unless the tool says out loud that it ran.
    dead = [k for k, v in rep["controls"].items() if not v]
    if dead:
        print(f"\n⚠️⚠️ DEAD QUESTION — control(s) at zero: {dead}. "
              f"The tool did not reach its subject; a clean run means "
              f"NOTHING.", file=sys.stderr)
        return 2
    if rep["unaccounted"] or rep["stale_gaps"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
