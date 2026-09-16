"""Does the information REACH its consumer? — a DERIVED check for the repo's
highest-yield bug class.

    python3 -m tools.omr.staged.wiring            # the three tables
    python3 -m tools.omr.staged.wiring --json
    python3 -m tools.omr.staged.wiring --check    # non-zero on anything
                                                  # not on KNOWN_GAPS
    python3 -m tools.omr.staged.wiring --run rec.json   # confirm FRAME from a
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

## The four questions this asks

Each has a live instance in the tree today, and the first two are asked by
nothing else here. ⚠️ **The COUNT is the `controls()` table's, not this
heading's** — a hand-counted figure in prose is exactly what rots in this
repo, and this heading said THREE for one commit after the fourth landed.

**1. PRODUCER — a parameter threaded with no supplier.** A keyword argument
passed down a call chain that every caller merely FORWARDS and nobody ever
supplies a real value for. `pdf_path` was this until 2026-09-11. `roster` and
`dossier` still are: `staged/__main__.py` has no `--roster`, no `--work-id`
and no `--dossier`, so `Q.ROSTER_ENTRY` and `Q.DOSSIER_FACT` are dead on
every staged run ever made.

**2. FRAME — a declared input read where it is never filed.** A decision that
reads `ev.rows(Q.X)` at the default `Scope.EXACT` reads its OWN subject, whose
Kind is the decision's declared `scope`. If `Q.X` is only ever filed at a
DIFFERENT Kind, the declared input is present, declared, gathered — and
**structurally unable to answer**. CLAUDE.md records four instances of this
and states flatly that *neither `inventory --check` nor `gather_coverage` can
catch it*: the `wants` entry IS read and the quantity IS gathered, so both
tools see a healthy row. Only a test asserting the ANSWER comes out has ever
caught one.

**3. DETAIL — a key written into a row and read by nobody.** The finest grain
of the same fault, and the one `Q.METER_GLYPH`'s `letter` flag lived in for
months: `log.observe(..., letter=True)` writes a field on the row, and a
`grep` for it finds the write and nothing else. A quantity-level check cannot
see it, because the QUANTITY is read — it is one field of it that is not.

**4. ROUNDTRIP — a field dropped by its own `to_json`.** A field a class
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
    "PRODUCER dossier": (
        "⚠️ NO PRODUCER. `dossier` is threaded `run_staged` -> `run_staged_on` "
        "-> `gather` -> `gather_external` and `gather_clef_seed`, and nothing "
        "in `tools/` supplies one. DELIBERATELY LEFT OPEN: a dossier is "
        "generated from the same MusicXML the benchmarks score against, so "
        "the scan gate is dossier-free BY PROTOCOL and wiring a `--dossier` "
        "flag would put a truth file inside a measurement path. The roster is "
        "the tier that is admissible (`source_kind: catalog`) and it is the "
        "one this session wired."),
    # ── FRAME, latent: declared, filed elsewhere, unreadable the obvious way
    #
    # ⚠️ EACH IS A TRAP ARMED FOR THE NEXT PERSON, not a bug today. The
    # declaration is inert (`inventory --check` owns that half); what this
    # adds is that the naive `ev.rows(Q.X)` which closes it would return
    # NOTHING, silently. `instrument declares roster_entry` was the seventh
    # and LEFT this list on 2026-09-15 when it was wired.
    "FRAME-LATENT adjudicate_clef declares Q.NOTEHEAD_STAFF_POSITION": (
        "the clef's OWN first `checked_by` entry — implied pitches against "
        "the instrument's written range — and the body never reads it. "
        "⚠️ MEASURED UNREACHABLE ON A SCAN (`inventory.KNOWN_GAPS`): the "
        "range test needs `Q.INSTRUMENT`, which abstains on 22 of 22 and 27 "
        "of 27 staves of the two scanned pages. What this row adds is that "
        "wiring it also needs `subject=` — the positions are on the GLYPHS."),
    "FRAME-LATENT adjudicate_key_signature declares Q.DOSSIER_FACT": (
        "no dossier is supplied on the scan path BY PROTOCOL, and the "
        "`dossier` parameter has no producer at all (see below). Closing "
        "this needs `Scope.SELF_AND_ANCESTORS`, not just a read."),
    "FRAME-LATENT adjudicate_meter declares Q.DOSSIER_FACT": (
        "as above — the meter's dossier tier, inert for the same reason and "
        "with the same frame trap waiting under it."),
    "FRAME-LATENT adjudicate_part_partition declares Q.INSTRUMENT": (
        "the join is decided from staff COUNTS and slots. ⚠️ THIS ONE IS "
        "RANKED WORK, not a permanent gap: the Phase 2 part-join finding is "
        "that a short system must pair by INSTRUMENT NAME, and the identity "
        "is on the STAFVES while this decision runs at DOCUMENT — so the "
        "repair needs `subject=` per staff, not a bare read."),
    "FRAME-LATENT adjudicate_part_partition declares Q.STAFF_ORDINAL": (
        "inert declaration; the partition reads slots. Same frame shape as "
        "the row above and the same `subject=` requirement."),
    "FRAME-LATENT adjudicate_system_membership declares Q.GAP_BRIDGING": (
        "inert declaration — the connectivity veto already ran in GATHER and "
        "the decision records its RESULT rather than the bridging. The "
        "bridging row is filed on the PAGE and the decision runs at SYSTEM."),

    # ── PRODUCER
    "PRODUCER dossier": (
        "⚠️ NO PRODUCER. `dossier` is threaded `run_staged` -> `run_staged_on` "
        "-> `gather` -> `gather_external` and `gather_clef_seed`, and nothing "
        "in `tools/` supplies one. DELIBERATELY LEFT OPEN: a dossier is "
        "generated from the same MusicXML the benchmarks score against, so "
        "the scan gate is dossier-free BY PROTOCOL and wiring a `--dossier` "
        "flag would put a truth file inside a measurement path. The roster is "
        "the tier that is admissible (`source_kind: catalog`) and it is the "
        "one this session wired."),

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
        "FRAME finding against working code. `--run` answers it exactly."),
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
    "DETAIL Q.STAFF_LINES.page_staff_index": (
        "the RASTER's own staff index — the join key back to `pws.staves`. "
        "Nothing downstream joins that way today; every consumer goes "
        "through the `Subject`. A debugging affordance."),
    "DETAIL Q.WEDGE_BOX.page_staff_index":
        "as `Q.STAFF_LINES.page_staff_index`.",
    "DETAIL Q.WEDGE_BOX.y_center_page": (
        "⚠️ NAMED ONLY BY A TEST, which is why it appears here at all: this "
        "question excludes test trees, because a test asserting a key exists "
        "is not a consumer of it. The page-pixel centre a cross-staff "
        "question would need — the frame `Q.ONSET_COLUMN` paid to learn "
        "about — gathered and, in production, unread."),
    "DETAIL Q.WEDGE_BOX.staff_bottom_line_page":
        "as `Q.WEDGE_BOX.y_center_page`.",
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


# ─────────────────────────────────────────────────────────────────────────────
# 1. PRODUCER — a parameter threaded with no supplier
# ─────────────────────────────────────────────────────────────────────────────

#: Where a threaded parameter is DECLARED. The staged package plus the two
#: legacy entry points a staged run reaches through.
_PRODUCER_ROOTS = ("tools/omr/staged",)

#: Where a call site may live. Everything, so a benchmark-only supplier is
#: VISIBLE rather than invisible.
_CALLSITE_ROOTS = ("tools", "benchmarks", "backend")


def _param_names(fn: ast.FunctionDef) -> Set[str]:
    a = fn.args
    out = {p.arg for p in (*a.posonlyargs, *a.args, *a.kwonlyargs)}
    if a.vararg:
        out.add(a.vararg.arg)
    if a.kwarg:
        out.add(a.kwarg.arg)
    return out


def _positional_order(fn: ast.FunctionDef) -> List[str]:
    """The parameters a POSITIONAL argument lands on, in order.

    ⚠️ WITHOUT THIS THE CHECK REPORTS ITS OWN FLAGSHIP CASE AS DEAD.
    `staged/__main__.py` calls `pipeline.run_staged(args.pdf, ...)` — the PDF
    path is supplied POSITIONALLY and every link after it is `pdf_path=
    pdf_path`, a pure forward. A keyword-only walker sees a chain of forwards
    with no supplier and reports the parameter repaired on 2026-09-11 as
    still broken. A check that cannot tell its own fixed bug from its own
    open one is not measuring what it says.
    """
    a = fn.args
    return [p.arg for p in (*a.posonlyargs, *a.args)]


def _defaulted_kwargs(fn: ast.FunctionDef) -> Set[str]:
    """Parameters with a CONSTANT default — the ones that can go unsupplied.

    ⚠️ A constant default is what makes the failure SILENT: a parameter with
    no default raises on the first call that omits it, so it cannot be dead.
    `roster: Any = None` cannot.
    """
    a = fn.args
    out: Set[str] = set()
    positional = (*a.posonlyargs, *a.args)
    for p, d in zip(positional[len(positional) - len(a.defaults):], a.defaults):
        if isinstance(d, ast.Constant):
            out.add(p.arg)
    for p, d in zip(a.kwonlyargs, a.kw_defaults):
        if isinstance(d, ast.Constant):
            out.add(p.arg)
    return out


def _signatures() -> Dict[str, Dict[str, Any]]:
    """Every function in the staged package, by name, with its parameters."""
    out: Dict[str, Dict[str, Any]] = {}
    for rootname in _PRODUCER_ROOTS:
        for path in _py_files(_ROOT / rootname):
            tree = _parse(path)
            if tree is None:
                continue
            for node in ast.walk(tree):
                if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                out.setdefault(node.name, {
                    "function": node.name, "declared_in": _rel(path),
                    "line": node.lineno,
                    "positional": _positional_order(node),
                    "defaulted": sorted(_defaulted_kwargs(node)),
                    "all": sorted(_param_names(node)),
                })
    return out


def _call_sites(sigs: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Every argument passed to a staged function, with its SHAPE.

    `forward` means the value is a bare Name that is also a PARAMETER of the
    ENCLOSING function — the call is passing its own argument along and
    supplies nothing itself. That is the whole discrimination this rests on,
    and it is why the answer needs a FIXPOINT rather than a single pass: a
    forward is dead or alive according to whether the enclosing parameter is
    fed, which is the same question one level up.
    """
    out: List[Dict[str, Any]] = []
    for rootname in _CALLSITE_ROOTS:
        base = _ROOT / rootname
        if not base.is_dir():
            continue
        for path in _py_files(base):
            tree = _parse(path)
            if tree is None:
                continue
            stack: List[Tuple[str, Set[str]]] = [("<module>", set())]

            def record(called, param, value, node):
                if called not in sigs:
                    return
                shape, via = "value", None
                if isinstance(value, ast.Name) and value.id in stack[-1][1]:
                    shape, via = "forward", (stack[-1][0], value.id)
                elif isinstance(value, ast.Constant) and value.value is None:
                    shape = "none"
                out.append({"called": called, "param": param, "shape": shape,
                            "via": via, "file": _rel(path),
                            "line": node.lineno, "tree": _tree_of(path)})

            class Walk(ast.NodeVisitor):
                def visit_FunctionDef(self, node):      # noqa: N802
                    stack.append((node.name, _param_names(node)))
                    self.generic_visit(node)
                    stack.pop()

                visit_AsyncFunctionDef = visit_FunctionDef   # noqa: N815

                def visit_Call(self, node):             # noqa: N802
                    f = node.func
                    called = (f.id if isinstance(f, ast.Name)
                              else f.attr if isinstance(f, ast.Attribute)
                              else None)
                    if called in sigs:
                        order = sigs[called]["positional"]
                        for i, arg in enumerate(node.args):
                            if isinstance(arg, ast.Starred):
                                break     # a splat: position is unknowable
                            if i < len(order):
                                record(called, order[i], arg, node)
                        for kw in node.keywords:
                            if kw.arg is None:
                                # `**kwargs` — a forward by construction and
                                # NEVER a supplier. Recorded, not dropped, so
                                # a splat cannot silently read as a producer.
                                out.append({
                                    "called": called, "param": "**",
                                    "shape": "splat", "via": None,
                                    "file": _rel(path), "line": node.lineno,
                                    "tree": _tree_of(path)})
                                continue
                            record(called, kw.arg, kw.value, node)
                    self.generic_visit(node)

            Walk().visit(tree)
    return out


def producers() -> Dict[str, Any]:
    """Which threaded parameters have a real supplier, and which have none.

    ⚠️⚠️ A FIXPOINT, NOT A SINGLE PASS, AND THE FIRST DRAFT WAS THE SINGLE
    PASS. `roster` is forwarded at three links and supplied at none — dead,
    correctly. `detector` is forwarded at exactly the same three links and
    SUPPLIED at the top by `staged/__main__.py`, so it is alive. A pass that
    looks only at the link in front of it cannot tell them apart and reports
    both dead, which is the shape of a check that fails so often nobody reads
    it. FED propagates DOWN the chain from a real supply; what never receives
    it is what has no producer.
    """
    sigs = _signatures()
    sites = _call_sites(sigs)

    #: (function, param) -> {tree: [site, ...]}. The TREE is carried as its
    #: own field and never parsed back out of a rendered string.
    fed: Dict[Tuple[str, str], Dict[str, List[str]]] = {}

    def add(dst, tree, where):
        fed.setdefault(dst, {}).setdefault(tree, []).append(where)

    for s in sites:
        if s["shape"] == "value":
            add((s["called"], s["param"]), s["tree"],
                f"{s['file']}:{s['line']}")

    forwards = [s for s in sites if s["shape"] == "forward"]
    changed = True
    while changed:                      # small graph; converges in a few turns
        changed = False
        for s in forwards:
            src, dst = tuple(s["via"]), (s["called"], s["param"])
            for tree, wheres in list(fed.get(src, {}).items()):
                have = fed.get(dst, {}).get(tree)
                if have is None:
                    add(dst, tree, f"{wheres[0]} (via {src[0]}.{src[1]})")
                    changed = True

    by_param: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
    for s in sites:
        by_param.setdefault((s["called"], s["param"]), []).append(s)

    rows: List[Dict[str, Any]] = []
    for name, spec in sorted(sigs.items()):
        if name.startswith("_"):
            continue                  # a private helper has no outside caller
        for param in spec["defaulted"]:
            mine = by_param.get((name, param), [])
            if not mine:
                continue              # never threaded — not this question
            supply = fed.get((name, param), {})
            trees = sorted(supply)
            rows.append({
                "function": name, "param": param,
                "declared_in": spec["declared_in"], "line": spec["line"],
                "call_sites": len(mine),
                "fed_by": {t: v[:3] for t, v in supply.items()},
                "verdict": ("NO PRODUCER" if not supply
                            else "production" if "production" in trees
                            else "+".join(trees) + " only"),
            })
    return {"rows": rows, "n_call_sites": len(sites)}


# ─────────────────────────────────────────────────────────────────────────────
# 2. FRAME — a declared input read where it is never filed
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


def details() -> Dict[str, Any]:
    """Detail keys written on rows, and whether anything mentions them."""
    structural = _row_kwargs()
    written: Dict[str, List[str]] = {}
    tree = _parse(_HERE / "gather.py")

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

    if tree is not None:
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
            if path.name == "gather.py" and "staged" in path.parts:
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
        "producer_params_examined": len(rep["producers"]["rows"]),
        "producer_call_sites_seen": rep["producers"]["n_call_sites"],
        "producer_with_a_real_supplier": sum(
            1 for r in rep["producers"]["rows"] if r["fed_by"]),
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
    #
    # ⚠️ ONLY `NO PRODUCER` IS A PROBLEM, AND THE OTHER CLASS IS DELIBERATELY
    # NOT ONE. "supplied only by a test" describes a SEAM, and this project
    # builds them on purpose — `run_staged_on` exists so a test can drive the
    # whole pipeline with no PDF, no weights and no venv, which is what makes
    # the coherence tests cheap enough to run every time. Failing on those
    # would make `--check` permanently red, which is this repo's own stated
    # reason a check stops being read. They are RENDERED, so a reader can see
    # which parameters only a harness can reach, and they are not counted.
    seen: Set[str] = set()
    for r in rep["producers"]["rows"]:
        if r["verdict"] != "NO PRODUCER" or r["param"] in seen:
            continue
        chain = sorted({x["function"] for x in rep["producers"]["rows"]
                        if x["param"] == r["param"]
                        and x["verdict"] == "NO PRODUCER"})
        seen.add(r["param"])
        out.append(f"PRODUCER {r['param']} — threaded through "
                   f"{', '.join(chain)} and supplied by NOBODY")
    for b in rep["frames"]["broken"]:
        out.append(f"FRAME {b['decision']} reads Q.{b['quantity']} at "
                   f"{b['reads_at']}, filed at {'/'.join(b['filed_at'])} "
                   f"— the declared input CANNOT ANSWER (fix: {b['fix']})")
    for b in rep["frames"]["latent"]:
        out.append(f"FRAME-LATENT {b['decision']} declares Q.{b['quantity']} "
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
    rep = {"producers": producers(), "frames": frames(),
           "details": details(), "roundtrip": roundtrip()}
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
    A("1. PRODUCER — a parameter threaded with no supplier")
    A("   %-22s %-34s %s" % ("param", "function", "verdict"))
    for r in rep["producers"]["rows"]:
        if r["verdict"] == "production":
            continue                  # healthy; counted in the controls
        A("  ⚠️ %-22s %-34s %s" % (r["param"], r["function"], r["verdict"]))
    A("")
    A("2. FRAME — a declared input read where it is never filed")
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
    A("3. DETAIL — a key written on a row and named nowhere else")
    if not rep["details"]["unread"]:
        A("   none")
    for d in rep["details"]["unread"]:
        A("  ⚠️ %-44s %s" % (d["key"], d["sites"][0]))
    A("")
    A("4. ROUNDTRIP — a field declared and dropped by its own `to_json`")
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
