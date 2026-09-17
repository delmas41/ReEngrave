"""What KIND of measurement is this, and may two rows of it be COMBINED?
— the sixth derived question.

    python3 -m tools.omr.staged.meaning            # the table
    python3 -m tools.omr.staged.meaning --json
    python3 -m tools.omr.staged.meaning --check    # non-zero on a HARD fault
                                                   # or a stale gap entry

⚠️⚠️ **WHY THIS IS NOT A SEVENTH COPY OF AN EXISTING TOOL.** Five derived
instruments stand, and each asks whether a value *arrives*:

  `gather_coverage`   is it OBSERVED at all?
  `inventory --check` is a `wants` entry actually READ?
  `wiring --check`    can a declared read REACH it (frame / detail / roundtrip)?
  `no_producer`       is a threaded PARAMETER ever supplied?
  `reach --check`     does ANYTHING read it?
  `capture --check`   per FAMILY: is shape recorded with a score, is a
                      staff-grid position recorded as its own scoreless row,
                      which raster answered, is the resolution right?

**None of them asks whether the consumer knows what the value MEANS.** A value
can arrive, be declared, be read, and still be combined with a value it is not
commensurable with. That failure passes every check above.

⚠️⚠️ **AND `wiring`'s FIRST QUESTION IS CALLED "FRAME" AND IS NOT ABOUT ONE.**
`wiring.py`'s FRAME question asks whether a declared input is read at a
`Scope` that can reach where it is FILED -- a SUBJECT-reach question. This
module is about the COORDINATE frame, `Observation.frame`. The two words
collide, and a reader who sees `wiring --check` green may reasonably conclude
that frames are checked. They are not, and were not: see section 2.

## THE MOTIVATING FAULT, and it is this repo's own

`Q.ONSET_COLUMN` (CLAUDE.md, *Cross-staff simultaneity*): a measure cell is
rescaled so the staff span is constant, so **two cells' canonical frames
coincide BY CONSTRUCTION** -- two staves agreeing at canonical x is not
evidence of anything. It reported **1,062 columns at 76.6% corroborated**, a
plausible aggregate over nothing, and what caught it was not a check but a
number that was too good (699 of 814 residuals EXACTLY zero). The repair was
to carry page pixels beside the canonical ones.

Section 3 is that fault stated derivably: a decision at `Kind.SYSTEM` reading
rows written in a `cell:*` frame is pooling across frames. **The repaired
`onset_column` is the ONE row of that table marked exempt, because it is the
one decision that reads a page-frame key** -- which is the closest thing to a
calibration a static check gets.

## THE THREE QUESTIONS, and what each can and cannot see

**1. MULTI-FRAME QUANTITY** — is one quantity written in more than one
coordinate frame? Then two of its rows are not comparable without asking, and
nothing asks. 4 of the written quantities are.

**2. A ROW'S OWN DETAIL DISAGREES WITH ITS `frame` FIELD** — ten quantities are
filed at `cell:*` and carry page-pixel geometry in `detail`. ⚠️ These are **not
ten bugs**: they are the `Q.ONSET_COLUMN` repair, applied deliberately. What it
costs is that `Observation.frame` describes the row's `value` and **not the
row**, so the field cannot be used for comparability even though it looks like
it could. That is the finding, and it is about the RECORD's shape rather than
any one site.

**3. SCOPE COARSER THAN FRAME** — the arm above. The only arm here that would
have caught `Q.ONSET_COLUMN` before its repair.

## ⚠️ WHAT THIS CANNOT SEE, stated rather than implied

* **A SUBJECT-IDENTITY fault.** `Q.FLAG` and `Q.AUG_DOT` are gathered on the
  MARK's glyph and were read on the NOTEHEAD's -- both `Kind.GLYPH`, both
  `cell:*`, 134 and 157 rows reaching ZERO durations. Same Kind, same frame,
  different subject. Neither this module nor `wiring` sees it; what would is a
  check on *which* subject a quantity is filed on against the one the consumer
  asks about, WITHIN a Kind.
* **A UNIT error inside one value.** `gap_bridging_counts` was
  `(crossing objects) x (each object's width)`, and CLAUDE.md records that **no
  threshold could have worked**. One number, one frame, wrong composition. No
  static check reaches it.
* **TWO QUANTITIES THAT MEASURE THE SAME THING IN DIFFERENT FRAMES.**
  `Q.STAFF_SPACING` (page) and `Q.CELL_STAFF_SPACE` (cell) are one measurement
  in two frames. ⚠️ Measured: **no single function reads both today**, so there
  is nothing live to catch -- but a check would need a HUMAN to say the two are
  the same measurement, which is not derivable from either name.
* **PROVENANCE-as-evidence.** `Q.METER_TEMPLATE.raw` is a matched glyph and IS
  evidence; `rhythm._propagated_meter.raw` is SYNTHESISED and is not. Same key
  name, same unit, opposite standing. The distinction is a claim about where a
  value came from; `Observation.reader` carries it and no arm here weighs it.
* Anything about a metric's own semantics (musicdiff `wrong note` is not wrong
  pitch), which is outside the record entirely.

## ⚠️ IT REPORTS AND DOES NOT GATE BEHAVIOUR

`A-INK-4`: *a factor CONTRIBUTES, it does not decide.* Nothing here adds a
rule, a veto or a threshold to the pipeline. The accounted tier is an
INVENTORY with a reason per entry, never a suppression list, and a closed gap
must LEAVE it -- `--check` fails on an entry nothing reports any more.

⚠️ **`DERIVED_CHECK = True` IS LOAD-BEARING.** This module NAMES detail keys
(`bbox_page_px`, `band_offset_spaces`, ...) in order to audit them and consumes
none of them. `wiring`'s DETAIL question reports a key written and read by
nobody, and would count this module's mention as a read -- the exact hazard
`capture.py` hit and closed the same way. The marker is read from the AST so a
comment cannot opt a real consumer out.
"""
from __future__ import annotations

import argparse
import ast
import collections
import importlib
import json
import pathlib
import sys
from typing import Dict, List, Set, Tuple

#: ⚠️ THIS MODULE IS A DERIVED CHECK, NOT A STAGE. It names detail keys to
#: audit them and reads none of them at run time. See the docstring.
DERIVED_CHECK = True

_HERE = pathlib.Path(__file__).resolve().parent
_OMR = _HERE.parent
_ROOT = _OMR.parent.parent


# ─────────────────────────────────────────────────────────────────────────────
# Declared tables — both GUARDED, so a new entry is a loud failure
# ─────────────────────────────────────────────────────────────────────────────

#: Frame token -> the `Kind` whose extent that frame is measured within.
#:
#: ⚠️ DECLARED, because there is no mechanical link from the string `"cell:0"`
#: to `Kind.CELL`. It is guarded: a frame token this module cannot place is a
#: HARD failure, never a skip. That is the `class_aliases.unaccounted()`
#: contract -- a wider vocabulary must be loud.
FRAME_EXTENT: Dict[str, str] = {
    "cell:*": "CELL",
    "bar_head:*": "CELL",
    "header_window": "STAFF",
    "system": "SYSTEM",
    "system_margin": "SYSTEM",
    "page": "PAGE",
    "dossier": "DOCUMENT",
}

#: Suffix -> the unit/frame the KEY NAME itself declares. Longest first, so
#: `_page_px` is not read as `_px`.
#:
#: ⚠️ A NAMING convention, not a type. It is trusted here only to report a
#: DISAGREEMENT between a row's `frame` field and its own detail keys, never
#: to assert what a key holds.
UNIT_SUFFIX: List[Tuple[str, str]] = [
    ("_page_px", "page/px"),
    ("_canonical", "canonical/px"),
    ("_page", "page/px"),
    ("_spaces", "staff-space"),
    ("_steps", "staff-step"),
    ("_px", "?/px"),
    ("_ql", "quarter-length"),
    ("_beats", "beat"),
    ("_fraction", "dimensionless"),
    ("_ratio", "dimensionless"),
    ("_frac", "dimensionless"),
]

#: Which row frames a declared unit is compatible with. A unit that makes no
#: frame claim (staff-space, staff-step, time, dimensionless) is absent on
#: purpose: those COMPOSE across frames, which is why the positional store
#: keys on staff steps.
FRAME_OF_UNIT: Dict[str, Set[str]] = {
    "page/px": {"page", "system", "header_window", "system_margin"},
    "canonical/px": {"cell:*", "bar_head:*"},
}

#: Detail keys that lift a row into the PAGE frame. A decision pooling
#: per-cell rows across cells is safe iff it reads one of these instead of the
#: row's own value.
PAGE_FRAME_KEYS = frozenset({
    "bbox_page_px", "x_center_page", "y_center_page",
    "staff_bottom_line_page", "x_page",
})


#: Accounted findings, each with its reason. An INVENTORY, never a
#: suppression list: `--check` passes with these recorded and FAILS on an
#: entry nothing reports any more.
#:
#: Keyed `"<decision>/<quantity>"` for section 3 and `"<quantity>"` for
#: sections 1 and 2.
KNOWN_GAPS: Dict[str, str] = {
    # ── section 1: one quantity, several frames ──────────────────────────
    "direction_word": (
        "MULTI-FRAME BY REPAIR, and section 2 as well. The words are read by "
        "a CV rung that works in page pixels and filed per cell; CLAUDE.md "
        "records the marks carrying a PAGE x while the noteheads carry a "
        "CANONICAL one, and `_place_directions` therefore places a dynamic at "
        "the HEAD of its bar as a DECLARED simplification rather than against "
        "its nearest note. The frames are recorded; what is missing is any "
        "consumer that asks."),
    "dynamic_letter": (
        "MULTI-FRAME BY REPAIR. Same shape as `direction_word` and the same "
        "declared simplification in the exporter. ⚠️ CLAUDE.md measures the "
        "cost of the frame it is NOT read in: 24% of dynamic letters stand in "
        "the band of the staff ABOVE, because the letters go through "
        "per-measure cells while the hairpin reader works in page pixels per "
        "staff and is right BY CONSTRUCTION."),
    "wedge_box": (
        "MULTI-FRAME BY CONSTRUCTION, and the honest case: 46 of 47 rows are "
        "`cv_hairpins` carrying page pixels and 1 is a detector box in a cell "
        "frame. `adjudicate_wedge_anchor` abstains `no_page_frame` on exactly "
        "the box-less row, which is a consumer declining rather than "
        "guessing. REMOVE THIS ENTRY if the two readers are ever unified."),
    "meter_template_at_bar": (
        "MULTI-FRAME BY DESIGN: `OMR_METER_TEMPLATE_AT_BAR` reads the opening "
        "in a 16-space `header_window` and a mid-staff change in a 4-space "
        "`bar_head`, and CLAUDE.md measures WHY they cannot share one frame — "
        "the score is MONOTONE IN WINDOW WIDTH (968 rise, 0 fall), so a "
        "maximum over a subset is not comparable with a maximum over a "
        "superset. ⚠️ This is the one entry where the incommensurability is "
        "already MEASURED and written down."),

    # ── section 2: a row's detail disagrees with its own `frame` field ────
    # ⚠️ ALL TEN ARE ONE FINDING ABOUT THE RECORD, NOT TEN SITE BUGS. They
    #    are the `Q.ONSET_COLUMN` repair applied deliberately. Listed per
    #    quantity so that a quantity LOSING its page keys leaves the list.
    "glyph_box": (
        "ROW MIXES FRAMES BY REPAIR — the canonical case. CLAUDE.md: "
        "`gather_detections` had read `cell.bbox_page_px` all along and threw "
        "it away after converting one glyph; page pixels are carried beside "
        "the canonical box now, DECLINED rather than defaulted. The row's "
        "`frame` says `cell:*` and three of its detail keys are page pixels."),
    "arc_box": "ROW MIXES FRAMES BY REPAIR — `gather_glyph_families` was gathering in a frame that could not answer, so `arc_owner`'s declared input was present and could not answer its own cross-staff question. Page pixels added beside.",
    "articulation_mark": "ROW MIXES FRAMES BY REPAIR — same `gather_glyph_families` change as `arc_box`.",
    "fermata_mark": "ROW MIXES FRAMES BY REPAIR — same `gather_glyph_families` change as `arc_box`.",
    "ornament_mark": "ROW MIXES FRAMES BY REPAIR — same `gather_glyph_families` change as `arc_box`.",
    "rest": "ROW MIXES FRAMES BY REPAIR — same `gather_glyph_families` change as `arc_box`.",
    "ink": (
        "ROW MIXES FRAMES BY DESIGN — `Q.INK` carries the box in BOTH frames "
        "on purpose (`ink_bbox_canonical` AND `bbox_page_px`), because the "
        "p.62 alignment result had to be counted in page pixels: the printed "
        "meter's page x drifts 13.9 px (0.88 staff spaces) down the plate. "
        "PRODUCER ONLY; nothing reads either yet."),

    # ── section 3: a decision pooling rows finer-framed than its scope ────
    "onset_column/glyph_box": (
        "⚠️⚠️ THE REPAIRED CASE, AND THIS CHECK'S ONLY CALIBRATION POINT. "
        "`adjudicate_onset_column` is the decision whose canonical-frame "
        "version reported 1,062 columns of nothing, and it is the ONE row of "
        "section 3 that reads a page-frame key (`x_page`) instead of the "
        "row's own canonical value. It is listed as ACCOUNTED rather than "
        "dropped so that the day someone removes that page-frame read, this "
        "entry goes STALE and `--check` says so. ⚠️ DO NOT DELETE: an exempt "
        "row that leaves the table is indistinguishable from a fault that "
        "was never flagged."),
    "meter/meter_glyph": (
        "⚠️ OPEN FINDING, and the one this check would rank first. "
        "`adjudicate_meter` runs at `Kind.SYSTEM` and votes over `cell:*` "
        "rows from every staff, with NO page-frame key — so the cross-staff "
        "agreement it counts is agreement in frames that coincide by "
        "construction. CLAUDE.md records the scan-side meter READING as the "
        "standing blocker (`9/8` read as `9/4` on 10 staves, five spurious "
        "`4/4`), and records separately that a cross-staff majority is not an "
        "independent umpire. This is a third route to the same place. NOT a "
        "claim that the vote is wrong: a meter IS printed at one x on every "
        "staff, so the frames may well agree — what is missing is that "
        "nothing checks."),
    "meter/meter_template": "OPEN — same shape as `meter/meter_glyph`: a SYSTEM-scope vote over per-STAFF `header_window` readings, no page-frame key.",
    "meter/meter_template_at_bar": "OPEN — same shape, and compounded by the measured window-width monotonicity recorded under `meter_template_at_bar` above.",
    "meter/rest": "OPEN — `_bar_lengths_for` pools `cell:*` rest rows at SYSTEM scope. ⚠️ Bar LENGTH is a `quarter-length`, a unit that makes no frame claim, so this row is likely benign; it is listed because the check cannot tell from the scope alone.",
    "clef/clef_glyph": "BENIGN BY STRUCTURE, recorded rather than excused: `adjudicate_clef` is `Kind.STAFF` and a staff prints ONE clef in ONE header cell, so there is no second frame to pool against. The check flags it because a STAFF scope is coarser than a CELL frame; only a human can say the population is one.",
    "clef/clef_located": "BENIGN BY STRUCTURE — same as `clef/clef_glyph`.",
    "clef/clef_position": "BENIGN BY STRUCTURE — same as `clef/clef_glyph`. ⚠️ And this is the repo's exemplar of a position fact done RIGHT (scoreless, own reader, own quantity), so its unit is a staff STEP, which composes across frames.",
    "clef/notehead_staff_position": "BENIGN BY UNIT — a staff STEP makes no frame claim and is exactly the quantity the positional store keys on BECAUSE it composes. Flagged on scope alone.",
    "key_signature/keysig_marker": "BENIGN BY STRUCTURE — a key signature stands in the header cell of its staff; same one-population argument as `clef/clef_glyph`. ⚠️ Also an inert `wants` (owned by `inventory --check`), so nothing reads it at all.",
    "part_partition/staff_ordinal": "BENIGN BY UNIT — an ORDINAL is not a coordinate; `system` frame vs DOCUMENT scope is a counting fact, not a geometric one. Flagged because the check reads the scope, not the unit.",
    "part_partition/system_staff_count": "BENIGN BY UNIT — a COUNT, as above.",
}


# ─────────────────────────────────────────────────────────────────────────────
# Derivation
# ─────────────────────────────────────────────────────────────────────────────

def _q_by_attr() -> Dict[str, str]:
    from .record import Q
    return {k: v for k, v in vars(Q).items()
            if isinstance(v, str) and not k.startswith("_")}


def _files() -> List[pathlib.Path]:
    """Every non-test module under `tools/omr/`.

    ⚠️ The BENCHMARK tree is excluded on the rule `wiring` had to learn: a
    probe that NAMES a key in order to measure it is not a consumer of it,
    and committing one turned four live `Q.INK` gaps STALE.
    """
    out = []
    for p in sorted((_OMR).rglob("*.py")):
        if p.name.startswith("test_") or "tests" in p.parts:
            continue
        out.append(p)
    return out


def _accessors():
    from . import reach
    return reach._accessors()


def _frame_of(node: ast.AST, locals_: Dict[str, str] | None = None) -> str:
    """Canonicalise a `frame=` argument to a comparable token.

    A per-cell frame becomes `cell:*`: `cell:0` and `cell:7` are the same KIND
    of frame, and what matters for comparability is that a cell frame and a
    page frame are different kinds. ⚠️ That two DIFFERENT cells' canonical
    frames coincide by construction is a stronger statement, and is what
    section 3 is for.
    """
    consts = {"FRAME_PAGE": "page", "FRAME_SYSTEM": "system",
              "FRAME_HEADER_WINDOW": "header_window",
              "FRAME_MARGIN": "system_margin"}
    v = node
    if isinstance(v, ast.Constant) and isinstance(v.value, str):
        return "cell:*" if v.value.startswith("cell:") else v.value
    if isinstance(v, ast.Name):
        if v.id in consts:
            return consts[v.id]
        if locals_ and v.id in locals_:
            return locals_[v.id]
        return "<unresolved:%s>" % v.id
    if isinstance(v, ast.Attribute):
        return consts.get(v.attr, "<unresolved:%s>" % v.attr)
    if isinstance(v, ast.Call):
        f = v.func
        nm = f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", "?")
        if nm == "frame_cell":
            return "cell:*"
        if nm == "frame_bar_head":
            return "bar_head:*"
        return "<unresolved:call:%s>" % nm
    if isinstance(v, ast.BinOp):                      # "cell:%d" % c
        if (isinstance(v.left, ast.Constant)
                and str(v.left.value).startswith("cell:")):
            return "cell:*"
        return "<unresolved:binop>"
    if isinstance(v, ast.JoinedStr):                  # f"cell:{c}"
        head = next((x.value for x in v.values if isinstance(x, ast.Constant)),
                    "")
        return "cell:*" if str(head).startswith("cell:") else "<unresolved:f>"
    return "<unresolved:%s>" % type(v).__name__


def _local_frames(scope: ast.AST) -> Dict[str, str]:
    """`{name: frame token}` for `name = <frame expr>` inside one scope.

    ⚠️ NOT cosmetic. Every per-cell gather helper writes
    `frame = frame_cell(...)` once and then passes `frame=frame`, so a
    resolver that stops at the `Name` reports THIRTEEN quantities as
    unresolved and the multi-frame population reads far smaller than it is.
    """
    out: Dict[str, str] = {}
    for n in ast.walk(scope):
        if isinstance(n, ast.Assign) and len(n.targets) == 1:
            t = n.targets[0]
            if isinstance(t, ast.Name):
                tok = _frame_of(n.value)
                if not tok.startswith("<unresolved"):
                    out[t.id] = tok
    return out


def _dict_kwargs(scope: ast.AST) -> Dict[str, Set[str]]:
    """`{var: keyword names}` ever put into a dict here — `dict(...)` AND
    `.update(...)`.

    ⚠️⚠️ THE `.update()` HALF IS NOT OPTIONAL AND THIS MODULE'S OWN FIRST RUN
    PROVES IT. `capture.py` documents `**common` bound to `dict(...)` as the
    trap that made the shipped `gather_coverage` report five families as
    having NO READER. The dominant spelling in `gather.py` is the other one --
    `box_detail.update(bbox_page_px=..., ...)` then `**box_detail` -- and
    resolving only `dict(...)` found 12 unit-declaring keys and **ZERO** frame
    disagreements: it reported the question clean by failing to ask it. The
    true figures are 54 and 29. Same anti-pattern, one spelling further on.
    """
    out: Dict[str, Set[str]] = collections.defaultdict(set)
    for n in ast.walk(scope):
        if isinstance(n, ast.Assign) and len(n.targets) == 1:
            t = n.targets[0]
            if (isinstance(t, ast.Name) and isinstance(n.value, ast.Call)
                    and getattr(n.value.func, "id", None) == "dict"):
                out[t.id] |= {k.arg for k in n.value.keywords if k.arg}
        if (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                and n.func.attr == "update"
                and isinstance(n.func.value, ast.Name)):
            out[n.func.value.id] |= {k.arg for k in n.keywords if k.arg}
    return out


def _unpacked_frames(scope: ast.AST, locals_: Dict[str, str]) -> Dict[str, str]:
    """`{dict var: frame token}` for `var = dict(..., frame=...)`."""
    out: Dict[str, str] = {}
    for n in ast.walk(scope):
        if isinstance(n, ast.Assign) and len(n.targets) == 1:
            t = n.targets[0]
            if (isinstance(t, ast.Name) and isinstance(n.value, ast.Call)
                    and getattr(n.value.func, "id", None) == "dict"):
                for kw in n.value.keywords:
                    if kw.arg == "frame":
                        out[t.id] = _frame_of(kw.value, locals_)
    return out


def _unit_of_key(key: str) -> str | None:
    for suf, unit in UNIT_SUFFIX:
        if key.endswith(suf):
            return unit
    return None


def survey() -> dict:
    """Everything, derived. No hand list but the two declared tables."""
    by_attr = _q_by_attr()
    values = set(by_attr.values())
    read_at, write_at = _accessors()

    def q_of(node):
        if isinstance(node, ast.Attribute) and node.attr in by_attr:
            return by_attr[node.attr]
        if isinstance(node, ast.Constant) and node.value in values:
            return node.value
        return None

    writes: Dict[str, Set[str]] = collections.defaultdict(set)
    write_sites: Dict[str, List[tuple]] = collections.defaultdict(list)
    reads: Dict[str, Set[str]] = collections.defaultdict(set)
    detail: Dict[str, Dict[tuple, Set[tuple]]] = collections.defaultdict(
        lambda: collections.defaultdict(set))
    files = 0

    for p in _files():
        try:
            tree = ast.parse(p.read_text())
        except (SyntaxError, UnicodeDecodeError):
            continue
        files += 1
        rel = str(p.relative_to(_ROOT))
        parent = {}
        for n in ast.walk(tree):
            for ch in ast.iter_child_nodes(n):
                parent[id(ch)] = n
        cache: Dict[int, tuple] = {}

        def maps(node):
            """Locals visible at `node`, nearest scope winning."""
            chain, cur = [], node
            while id(cur) in parent:
                cur = parent[id(cur)]
                if isinstance(cur, (ast.FunctionDef, ast.AsyncFunctionDef,
                                    ast.Module)):
                    chain.append(cur)
            loc, unp = {}, {}
            dkw: Dict[str, Set[str]] = collections.defaultdict(set)
            for scope in reversed(chain):             # outermost first
                if id(scope) not in cache:
                    l = _local_frames(scope)
                    cache[id(scope)] = (l, _unpacked_frames(scope, l),
                                        _dict_kwargs(scope))
                l, u, d = cache[id(scope)]
                loc.update(l)
                unp.update(u)
                for k, v in d.items():
                    dkw[k] |= v
            return loc, unp, dkw

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            f = node.func
            name = (f.attr if isinstance(f, ast.Attribute)
                    else getattr(f, "id", None))
            if name in write_at:
                idx = write_at[name]
                q = q_of(node.args[idx]) if len(node.args) > idx else None
                if q is None:
                    continue
                loc, unp, dkw = maps(node)
                fr = "<unspecified>"
                for kw in node.keywords:
                    if kw.arg == "frame":
                        fr = _frame_of(kw.value, loc)
                        break
                else:
                    for kw in node.keywords:
                        if kw.arg is None and isinstance(kw.value, ast.Name):
                            fr = unp.get(kw.value.id,
                                         "<unresolved:**%s>" % kw.value.id)
                            break
                writes[q].add(fr)
                write_sites[q].append((rel, node.lineno, fr))
                keys = [kw.arg for kw in node.keywords if kw.arg]
                for kw in node.keywords:
                    if kw.arg is None and isinstance(kw.value, ast.Name):
                        keys += sorted(dkw.get(kw.value.id, ()))
                for k in keys:
                    u = _unit_of_key(k)
                    if u:
                        detail[q][(k, u)].add((fr, rel, node.lineno))
            elif name in read_at:
                idx = read_at[name]
                q = q_of(node.args[idx]) if len(node.args) > idx else None
                if q is None:
                    q = next((q_of(kw.value) for kw in node.keywords
                              if kw.arg == "quantity"), None)
                if q is not None:
                    reads[q].add(rel)

    # ── section 1 ───────────────────────────────────────────────────────
    multi_frame = {q: sorted(v) for q, v in writes.items() if len(v) > 1}

    # ── section 2 ───────────────────────────────────────────────────────
    mixed, unit_keys = [], 0
    for q, keys in sorted(detail.items()):
        for (k, u), sites in sorted(keys.items()):
            unit_keys += 1
            ok = FRAME_OF_UNIT.get(u)
            if not ok:
                continue                 # unit makes no frame claim
            bad = sorted({fr for fr, _, _ in sites} - ok)
            if bad:
                site = sorted(sites)[0]
                mixed.append((q, k, u, bad, site[1], site[2]))

    # ── section 3 ───────────────────────────────────────────────────────
    from . import adjudicate as A
    from . import adjudicators as _ad      # noqa: F401  populates REGISTRY
    from .record import _KIND_DEPTH

    depth = {k.name: v for k, v in _KIND_DEPTH.items()}
    scope_vs_frame, unknown_frames = [], set()
    for fr_set in writes.values():
        for fr in fr_set:
            if fr.startswith("<") or fr not in FRAME_EXTENT:
                unknown_frames.add(fr)
    for name, spec in sorted(A.REGISTRY.items()):
        sdepth = depth[spec.scope.name]
        try:
            import inspect
            src = inspect.getsource(spec.fn)
        except (OSError, TypeError, AttributeError):
            src = ""
        for q in sorted(spec.wants):
            for fr in sorted(writes.get(q, ())):
                ext = FRAME_EXTENT.get(fr)
                if ext is None:
                    continue             # already in unknown_frames
                if depth[ext] > sdepth:  # frame FINER than the scope
                    keys = sorted(k for k in PAGE_FRAME_KEYS if k in src)
                    scope_vs_frame.append(
                        (name, spec.scope.name, q, fr, ext, keys))

    return {
        "files_walked": files,
        "n_quantities": len(by_attr),
        "n_written": len(writes),
        "n_read": len(reads),
        "n_decisions": len(A.REGISTRY),
        "n_unit_keys": unit_keys,
        "multi_frame": multi_frame,
        "mixed_detail": mixed,
        "scope_vs_frame": scope_vs_frame,
        "unknown_frames": sorted(unknown_frames),
        "frame_histogram": dict(
            collections.Counter(f for v in writes.values() for f in v)),
        "write_sites": {q: v for q, v in write_sites.items()},
    }


# ─────────────────────────────────────────────────────────────────────────────
# Reporting
# ─────────────────────────────────────────────────────────────────────────────

def _keys_reported(s: dict) -> Set[str]:
    """Every KNOWN_GAPS key this run actually reports."""
    out = set(s["multi_frame"])
    out |= {q for q, *_ in s["mixed_detail"]}
    out |= {"%s/%s" % (n, q) for n, _, q, _, _, _ in s["scope_vs_frame"]}
    return out


def report(s: dict) -> int:
    print("═══ WHAT KIND OF MEASUREMENT IS THIS? ═" + "═" * 34)
    print()
    print(f"  files walked {s['files_walked']}   quantities {s['n_quantities']}"
          f"   written {s['n_written']}   read {s['n_read']}"
          f"   decisions {s['n_decisions']}")
    print()

    print(f"[1] ONE QUANTITY, SEVERAL FRAMES  ({len(s['multi_frame'])})")
    print("    two rows are not comparable without asking, and nothing asks")
    for q, fr in sorted(s["multi_frame"].items()):
        print(f"      {q:26s} {fr}")
    print()

    print(f"[2] A ROW'S DETAIL DISAGREES WITH ITS OWN `frame` FIELD "
          f"({len(s['mixed_detail'])} keys, "
          f"{len({q for q, *_ in s['mixed_detail']})} quantities)")
    print("    ⚠️ NOT that many bugs — this is the Q.ONSET_COLUMN repair, and")
    print("    what it costs is that `frame` describes the VALUE, not the row")
    for q, k, u, bad, rel, ln in s["mixed_detail"]:
        print(f"      {q:24s} {k:24s} says {u:12s} frame={bad}"
              f"   {rel.rsplit('/', 1)[-1]}:{ln}")
    print()

    svf = s["scope_vs_frame"]
    blind = [r for r in svf if not r[5]]
    print(f"[3] DECISION SCOPE COARSER THAN ROW FRAME  ({len(svf)})")
    print("    rows whose coordinate systems coincide BY CONSTRUCTION;")
    print("    the one arm that would have caught Q.ONSET_COLUMN unrepaired")
    for name, scope, q, fr, ext, keys in svf:
        mark = ("reads " + ",".join(keys) if keys
                else "** no page-frame key **")
        print(f"      {name:26s} scope={scope:8s} {q:24s} "
              f"frame={fr:14s} {mark}")
    print(f"    reading NO page-frame detail key: {len(blind)} of {len(svf)}")
    print()

    print("frame tokens (quantities carrying each):")
    for f, n in sorted(s["frame_histogram"].items(), key=lambda kv: -kv[1]):
        print(f"      {f:26s} {n}")
    print()
    print("── POSITIVE CONTROLS (a zero means the question did not run) ──")
    for k in ("files_walked", "n_written", "n_read", "n_decisions",
              "n_unit_keys"):
        print(f"   {k:16s} {s[k]}")
    return 0


def check(s: dict) -> int:
    """HARD tier, which is at zero today; plus the stale-entry contract."""
    bad = []

    # (a) positive controls. A question that cannot run must not pass.
    controls = {"files_walked": 10, "n_written": 30, "n_read": 30,
                "n_decisions": 20, "n_unit_keys": 20}
    for k, floor in controls.items():
        if s[k] <= floor:
            bad.append(f"CONTROL {k}={s[k]} <= {floor}: the derivation did "
                       f"not run, so every zero below it is vacuous")

    # (b) a frame token this module cannot place. Never a silent skip.
    for fr in s["unknown_frames"]:
        bad.append(f"UNPLACED FRAME {fr!r}: add it to FRAME_EXTENT, or fix "
                   f"the site that writes it. A frame this check cannot "
                   f"place is one it cannot reason about.")

    # (c) accounted / stale
    reported = _keys_reported(s)
    for k in sorted(reported - set(KNOWN_GAPS)):
        bad.append(f"UNACCOUNTED {k}: reported by this check and not in "
                   f"KNOWN_GAPS. Add it WITH ITS REASON.")
    for k in sorted(set(KNOWN_GAPS) - reported):
        bad.append(f"STALE {k}: KNOWN_GAPS names it and nothing reports it "
                   f"any more. A closed gap must LEAVE the list, or the list "
                   f"stops describing the pipeline and starts describing its "
                   f"history.")

    if bad:
        print("── FAILURES ──")
        for b in bad:
            print("  ✗ " + b)
        return 1
    print(f"ok — {len(reported)} findings, all accounted; "
          f"{len(s['unknown_frames'])} unplaced frames; controls live")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args(argv)
    s = survey()
    if a.json:
        print(json.dumps(s, indent=2, default=str))
        return 0
    if a.check:
        return check(s)
    return report(s)


if __name__ == "__main__":
    sys.exit(main())
