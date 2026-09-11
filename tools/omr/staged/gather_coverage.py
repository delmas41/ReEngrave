"""What the GATHER stage collects, what it could collect, and what has no
vocabulary at all.

⚠️ THIS FILE EXISTS BECAUSE THE TWO LISTS IT PRINTS CANNOT BE WRITTEN BY HAND.
Every hand-written inventory in this repo has gone stale -- the handoff that
asked for this one opens by correcting two false claims in its own
predecessor, and CLAUDE.md records a fixed defect that stayed open in prose
for two days. So the lists are DERIVED: from the AST of `gather.py`, from
`record.Q`, from the adjudicator registry's own `wants=`, and from the legacy
event dicts `voicing.py` builds and `export.py` reads.

⚠️ THE QUESTION THAT WORKS IS NOT "IS THERE A Q FOR THIS."

`export_coverage.py` records why: auditing the DETECTOR'S CLASS SPACE for
classes nothing mentions calls accidentals *consumed*, because they are --
into `pitch`. The same trap is here. `Q.GLYPH_BOX` carries every detection
including its x, so "is x gathered" is YES and the answer is useless. What
the chord finding actually showed is that a SIGNAL CAN BE PRESENT IN A ROW
AND ABSENT FROM THE VOCABULARY -- no consumer can ask for it, no decision can
declare it in `wants=`, and no abstention can be recorded when it is missing.

So the comparison is against the LEGACY EVENT VOCABULARY: the keys the
existing pipeline puts on an event and carries to the exporter. Those are the
quantities the project has already proved a reader needs, measured at the one
place that has to have them all. A key with no Q is a quantity the staged
record cannot express.

Four populations, and they are different faults with different fixes:

  1. GATHERED          -- a gatherer emits it. The stage works.
  2. VERDICT_ELSEWHERE -- declared, not gathered, and OWNED by `adjudicate`.
                          Correct: a verdict is not a measurement.
  3. DECLARED_UNGATHERED -- declared as a MEASUREMENT and no gatherer emits
                          it. The vocabulary exists and nothing fills it.
  4. NO_VOCABULARY     -- the legacy pipeline carries it and `record.Q` has
                          no name for it. This is the chord class.

`LEGACY_TO_Q` is a MAPPING, not a suppression list, and `unaccounted()` fails
on any legacy key in neither it nor `NO_VOCABULARY` -- so a new event key is a
loud failure rather than a silent omission, the same contract
`class_aliases.unaccounted()` holds.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

_HERE = Path(__file__).resolve().parent
_OMR = _HERE.parent

# ─────────────────────────────────────────────────────────────────────────────
# 1. What gather.py emits -- from its AST, never from a list
# ─────────────────────────────────────────────────────────────────────────────


def _q_name(node: ast.AST) -> Optional[str]:
    """`Q.GLYPH_BOX` -> "GLYPH_BOX". Anything else -> None."""
    if (isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name)
            and node.value.id == "Q"):
        return node.attr
    return None


def _attr_tail(node: ast.AST) -> Optional[str]:
    """`READERS.DETECTOR` -> "DETECTOR"; `ABSTAIN.NO_INK` -> "NO_INK"."""
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _kwarg(call: ast.Call, name: str) -> Optional[ast.AST]:
    for kw in call.keywords:
        if kw.arg == name:
            return kw.value
    return None


def gathered(source: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
    """Every quantity `gather.py` observes or abstains on.

    ⚠️ OBSERVE AND ABSTAIN ARE RECORDED APART. A quantity a gatherer can only
    ever abstain on is DECLARED, not collected -- `_stub_cv_lines` emits
    `NOT_IMPLEMENTED` for `Q.STEM` and `Q.BEAM_STROKE` on a machine with no
    `line_detection`, and counting that as coverage would report a stub as a
    reader. The distinction is exactly `record`'s READ vs DECLINED.
    """
    src = source if source is not None else (_HERE / "gather.py").read_text()
    tree = ast.parse(src)

    out: Dict[str, Dict[str, Any]] = {}

    class Walker(ast.NodeVisitor):
        """⚠️ RESOLVES LOOP-BOUND QUANTITIES, because two of them are real.

        `gather_cv_lines` writes `for quantity, kind in ((Q.STEM, "stems"),
        (Q.BEAM_STROKE, "beams")): log.observe(sub, quantity, ...)`. A visitor
        that only reads `Q.X` literals at the call site reports `Q.STEM` as
        never observed -- and `adjudicate_duration` declares it in `wants=`,
        so the tool would invent a missing-evidence finding against a reader
        that works. The first run of this module did exactly that.
        """

        def __init__(self) -> None:
            self.func: List[str] = []
            self.bound: List[Dict[str, List[str]]] = [{}]

        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
            self.func.append(node.name)
            self.bound.append(dict(self.bound[-1]))
            self.generic_visit(node)
            self.bound.pop()
            self.func.pop()

        def visit_For(self, node: ast.For) -> None:
            # Bind each loop target that receives a Q literal from the
            # iterable, positionally where the iterable is a tuple of tuples.
            frame = dict(self.bound[-1])
            targets = (node.target.elts
                       if isinstance(node.target, ast.Tuple) else [node.target])
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
                        q = _q_name(cells[pos])
                        if q and q not in found:
                            found.append(q)
                if found:
                    frame[tgt.id] = found
            self.bound.append(frame)
            self.generic_visit(node)
            self.bound.pop()

        def _quantities(self, node: ast.Call) -> List[str]:
            """Every quantity this call could be emitting."""
            candidates = list(node.args[:3])
            kw = _kwarg(node, "quantity")
            if kw is not None:
                candidates.append(kw)
            out: List[str] = []
            for arg in candidates:
                q = _q_name(arg)
                if q:
                    out.append(q)
                elif isinstance(arg, ast.Name):
                    out.extend(self.bound[-1].get(arg.id, []))
            return out

        def visit_Call(self, node: ast.Call) -> None:
            fn = node.func
            verb = fn.attr if isinstance(fn, ast.Attribute) else None
            if verb in ("observe", "abstain"):
                where = self.func[-1] if self.func else "<module>"
                bucket = ("observed_by" if verb == "observe"
                          else "abstained_by")
                reader = _attr_tail(_kwarg(node, "reader") or ast.Pass())
                reason = _attr_tail(_kwarg(node, "reason") or ast.Pass())
                for quantity in self._quantities(node):
                    rec = out.setdefault(quantity, {
                        "observed_by": [], "abstained_by": [],
                        "readers": [], "reasons": [],
                    })
                    if where not in rec[bucket]:
                        rec[bucket].append(where)
                    if reader and reader not in rec["readers"]:
                        rec["readers"].append(reader)
                    if reason and reason not in rec["reasons"]:
                        rec["reasons"].append(reason)
            self.generic_visit(node)

    Walker().visit(tree)

    return out


# ─────────────────────────────────────────────────────────────────────────────
# 2. What is declared, and who owns it
# ─────────────────────────────────────────────────────────────────────────────


def declared() -> Tuple[str, ...]:
    from .record import Q
    return tuple(sorted(n for n in vars(Q)
                        if n.isupper() and not n.startswith("_")))


def verdict_quantities() -> Set[str]:
    """Quantities `adjudicate` owns. Read from the REGISTRY, not a list."""
    from . import adjudicate as A
    from . import adjudicators  # noqa: F401 -- THIS is what fills REGISTRY
    from .record import Q
    by_value = {getattr(Q, n): n for n in declared()}
    return {by_value[q] for q in A.REGISTRY if q in by_value}


def consequence_quantities() -> Set[str]:
    """Quantities the EVALUATE stage produces. Also read, not typed."""
    from . import consequences as C
    from .record import Q
    by_value = {getattr(Q, n): n for n in declared()}
    found: Set[str] = set()
    for name in ("REGISTRY", "CONSEQUENCES", "ORDER"):
        reg = getattr(C, name, None)
        if isinstance(reg, dict):
            found |= {by_value[q] for q in reg if q in by_value}
    src = (_HERE / "consequences.py").read_text()
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.keyword) and node.arg in ("quantity",
                                                          "produces"):
            q = _q_name(node.value)
            if q:
                found.add(q)
    return found


def wanted() -> Dict[str, List[str]]:
    """quantity -> the decisions that declare it in `wants=`.

    ⚠️ A `wants` entry naming a quantity nothing gathers is the sharpest
    signal this module produces: a decision has DECLARED the evidence it
    needs and no reader supplies it, so the decision can only ever abstain
    for lack of input while looking wired.
    """
    from . import adjudicate as A
    from . import adjudicators  # noqa: F401 -- REGISTRY is empty without it
    from .record import Q
    by_value = {getattr(Q, n): n for n in declared()}
    out: Dict[str, List[str]] = {}
    for quantity, spec in A.REGISTRY.items():
        owner = by_value.get(quantity, quantity)
        for w in spec.wants:
            out.setdefault(by_value.get(w, w), []).append(owner)
    return {k: sorted(v) for k, v in sorted(out.items())}


# ─────────────────────────────────────────────────────────────────────────────
# 3. The legacy event vocabulary -- what a reader has already been proved
#    to need, taken from the code that needs it
# ─────────────────────────────────────────────────────────────────────────────


def legacy_event_keys() -> Dict[str, List[str]]:
    """Keys the legacy pipeline puts on an event or reads back off one.

    Two sources, both AST:

      * `voicing.py` -- the dict literals that BUILD an event, plus every
        `.get("...")` it makes against a notehead. This is the producer.
      * `export.py` -- every `.get("...")`/`["..."]` against an event or a
        notehead. This is the consumer at the far end, and the one place
        every quantity has to be present at once.
    """
    out: Dict[str, List[str]] = {}

    def note(key: str, where: str) -> None:
        if key.startswith("_"):
            return
        rec = out.setdefault(key, [])
        if where not in rec:
            rec.append(where)

    voicing = ast.parse((_OMR / "voicing.py").read_text())
    for node in ast.walk(voicing):
        if isinstance(node, ast.Dict):
            for k in node.keys:
                if isinstance(k, ast.Constant) and isinstance(k.value, str):
                    note(k.value, "voicing:event")
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == "get" and node.args
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)):
            note(node.args[0].value, "voicing:read")
        if (isinstance(node, ast.Subscript)
                and isinstance(node.slice, ast.Constant)
                and isinstance(node.slice.value, str)):
            note(node.slice.value, "voicing:read")

    # The exporter reads far more than events (page dicts, staff dicts), so
    # only keys the producer also knows are taken from it -- otherwise this
    # becomes an inventory of export.py rather than of the event.
    known = set(out)
    export = ast.parse((_OMR / "export.py").read_text())
    for node in ast.walk(export):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == "get" and node.args
                and isinstance(node.args[0], ast.Constant)
                and node.args[0].value in known):
            note(node.args[0].value, "export:read")
    return {k: sorted(v) for k, v in sorted(out.items())}


#: A legacy event key -> the `record.Q` name that already expresses it.
#:
#: ⚠️ A MAPPING, NOT A SUPPRESSION LIST. Being mapped means the staged record
#: CAN carry the quantity, never that a gatherer does -- `gathered()` is what
#: answers that. Several entries map to a VERDICT on purpose: `duration_type`
#: is `Q.DURATION`'s output and belongs to `adjudicate`, not to a reader.
LEGACY_TO_Q: Dict[str, str] = {
    "duration_beats": "DURATION",
    "duration_type": "DURATION",
    "dots": "AUG_DOT",
    "rest": "GLYPH_BOX",
    "noteheads": "NOTEHEAD_CLASS",
    "pitch": "PITCH",
    "clef": "CLEF",
    "key_signature": "KEY_SIGNATURE",
    "time_signature": "METER",
    "time": "METER",
    "beam_states": "BEAM_STROKE",
    "slur_states": "ARC_OWNER",
    "wedge_states": "WEDGE_ANCHOR",
    "articulations": "ARTICULATION_OWNER",
    # ⚠️ THE VERDICT, NOT THE MARK, exactly as `articulations` maps to the
    # OWNER above: the legacy event key means "this event carries a pause",
    # which is a decision about what the ink hangs over and not the ink
    # itself. `Q.FERMATA_MARK` is the reading. CLOSED 2026-09-10; it was in
    # `NO_VOCABULARY`.
    "fermata": "FERMATA_OWNER",
    "direction_texts": "DIRECTION",
    "detections": "GLYPH_BOX",
    "bbox_page_px": "GLYPH_BOX",
    "systems": "SYSTEM_MEMBERSHIP",
    "confidence": "GLYPH_CONF",
    "class": "GLYPH_BOX",
    "category": "GLYPH_BOX",
    "smufl_name": "GLYPH_BOX",
    "staff_index": "STAFF_ORDINAL",
    "measure_index": "MEASURE_PARTITION",
    "measures": "MEASURE_PARTITION",
    "staves": "SYSTEM_STAFF_COUNT",
    "x_canonical": "GLYPH_BOX",
    "y_canonical": "GLYPH_BOX",
    "width_canonical": "GLYPH_BOX",
    "height_canonical": "GLYPH_BOX",
    "bbox": "GLYPH_BOX",
    "pages": "STAFF_LINES",
    # ⚠️ CLOSED 2026-09-09 BY PARALLEL WORK, and this tool's first version
    # reported them open for a day. `Q.EVENT` ("which glyphs of a bar sound
    # TOGETHER -- one event, N noteheads") is the chord quantity; its own
    # docstring settles `x_position` too, declaring the x POSITION a
    # measurement that `GLYPH_BOX` already carries and the SIMULTANEITY the
    # interpretation. Kept here rather than deleted so the closure is legible.
    "events": "EVENT",
    "n_events": "EVENT",
    "kind": "EVENT",
    "x_position": "GLYPH_BOX",
}

#: Legacy event keys with NO `record.Q` name, each with what it is and why its
#: absence is a hole rather than a naming preference.
#:
#: ⚠️ EVERY ENTRY HERE IS A FINDING, NOT A SUPPRESSION. An entry leaves this
#: table the day a `Q` is declared for it -- `unaccounted()` fails on a key in
#: neither table, and `test_gather_coverage.py` fails on an entry that has
#: since grown a `Q`, the same contract `export_coverage.KNOWN_GAPS` holds.
NO_VOCABULARY: Dict[str, str] = {
    "stem_direction": (
        "up | down, measured by `transcribe._stem_direction` from the stem "
        "against its noteheads. `Q.STEM` carries the stem's BOX and not its "
        "direction, so the quantity is derivable and undeclared -- and it is "
        "the discriminator the divisi guard runs on."),
    "tied_to_next": (
        "tie state carried on the notehead, chained across barlines by "
        "`transcribe._pair_ties_in_staff`. `Q.ARC_KIND` decides tie-vs-slur "
        "for one arc; nothing names the CHAIN a tie makes between two events."),
    "tied_from_prev": "the other end of the same chain; see `tied_to_next`.",
    "ornaments": (
        "trill / turn / mordent / tremolo, attached by "
        "`transcribe._attach_ornaments_in_cell`. The tenth export gap. "
        "`Q.ARTICULATION_MARK` is a different family and does not cover it."),
    "voices": (
        "a staff-measure's 1-2 VOICE STREAMS, split by "
        "`voicing.split_events_into_voices` on stem direction. MusicXML pairs "
        "`<slur>` WITHIN a `<voice>` and separates the streams with "
        "`<backup>`, so `Q.ARC_OWNER` already depends on a quantity the "
        "record cannot express -- and `export._lone_voice_is_the_second` "
        "re-decides the lane per measure downstream of it."),
    "voice_index": "which stream an event landed in; see `voices`.",
}


def q_covering(key: str) -> Optional[str]:
    """The declared `Q` that would name this legacy key, or None.

    ⚠️ THIS EXISTS BECAUSE THE OBVIOUS VERSION HAS A BUG AND THE BUG BIT.
    The first cut compared lowercased names for exact equality, so the legacy
    key `events` never matched `Q.EVENT` -- a singular/plural mismatch -- and
    `test_no_vocabulary_entries_still_have_no_vocabulary` waved through a
    finding that had been CLOSED on main. The stale claim reached a PR body,
    CLAUDE.md and a findings file before a different test caught it.

    ⚠️ It is deliberately NOT a substring test. `stem_direction` would match
    `Q.STEM` under one, and they are different quantities: `Q.STEM` carries a
    stem's BOX and says nothing about which way it points.
    """
    from .record import Q
    names = {n for n in vars(Q) if n.isupper() and not n.startswith("_")}
    probe = key.lower().strip("_")
    for variant in (probe, probe.rstrip("s"), probe + "s"):
        for n in names:
            if n.lower() == variant:
                return n
    return None


def unaccounted() -> Dict[str, List[str]]:
    """Legacy event keys in NEITHER table.

    ⚠️ THIS IS THE ANTI-DRIFT CONTRACT. A key added to an event and to
    neither table fails the suite, so widening the legacy vocabulary cannot
    silently widen the staged record's blind spot.
    """
    keys = legacy_event_keys()
    return {k: v for k, v in keys.items()
            if k not in LEGACY_TO_Q and k not in NO_VOCABULARY}


# ─────────────────────────────────────────────────────────────────────────────
# 3b. Is the ink there under a DIFFERENT name?
# ─────────────────────────────────────────────────────────────────────────────

#: An ungathered measurement -> the detector class names whose ink it is.
#:
#: ⚠️ THIS IS THE "WRONG PLACE" AXIS AND IT IS THE SUBTLER OF THE TWO.
#: `gather_detections` emits EVERY detection as `Q.GLYPH_BOX`, so this ink is
#: already in the log -- it is not missing, it is unnameable. A decision
#: declaring `wants=(Q.ARC_BOX,)` resolves to nothing while the arcs sit in
#: the same log under a generic name, and `Evidence` refuses a quantity the
#: decision did not declare, so the stub CANNOT reach them. That is a
#: different repair from `fermata`, which no row carries at all.
#: ⚠️ `WEDGE_BOX` and `DYNAMIC_LETTER` share the `dynamic` prefix and are NOT
#: the same family -- a hairpin is drawn BETWEEN its notes and a letter stands
#: under one, which is why `_wedge_anchors` exists apart from
#: `measure_dynamics`. The exclusion keeps them separable in this report.
INK_CLASS_PREFIXES: Dict[str, Tuple[str, ...]] = {
    "ARC_BOX": ("tie", "slur"),
    "ARTICULATION_MARK": ("artic",),
    "WEDGE_BOX": ("dynamiccrescendohairpin", "dynamicdiminuendohairpin"),
    "DYNAMIC_LETTER": ("dynamic",),
}

#: Classes a prefix would sweep up that belong to another quantity.
INK_CLASS_EXCLUDE: Dict[str, Tuple[str, ...]] = {
    "DYNAMIC_LETTER": ("dynamiccrescendohairpin", "dynamicdiminuendohairpin"),
}


def _detector_classes() -> Tuple[str, ...]:
    """The 208-class space, read from `deepscores_classes.py` by AST.

    ⚠️ THE CLASS SPACE, NOT `_CATEGORY_MAP`. The first cut read the category
    map's KEYS and reported `WEDGE_BOX` as having no detector class -- while
    `dynamicCrescendoHairpin` is class 173 and fires freely. The map is a
    coarse name -> family table resolved by SUBSTRING fallback, so a class it
    never names by hand is still detected; its keys are not the vocabulary.
    A coverage tool whose own inventory is an allow-list is the fault
    `export_coverage.compare()` was just repaired for.

    ⚠️ AST rather than import: `yolo_detector` imports `cv2`, and this module
    must run wherever `record.py` runs -- which its own docstring pins as
    stdlib only. A coverage tool that needs the vision stack installed is a
    coverage tool nobody runs in CI.
    """
    src = (_OMR / "training" / "deepscores_classes.py").read_text()
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) \
                and node.target.id == "DEEPSCORES_V2_CLASSES":
            try:
                return tuple(ast.literal_eval(node.value))
            except Exception:                                 # noqa: BLE001
                return ()
        if isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == "DEEPSCORES_V2_CLASSES"
                for t in node.targets):
            try:
                return tuple(ast.literal_eval(node.value))
            except Exception:                                 # noqa: BLE001
                return ()
    return ()


def ink_present_elsewhere() -> Dict[str, Dict[str, Any]]:
    """For each ungathered measurement, whether its ink reaches the log anyway.

    A hit means the detector has classes for it, so `gather_detections` files
    the ink under `Q.GLYPH_BOX` and the quantity is a NAMING gap. A miss means
    nothing reads it and the quantity is a READING gap. The two need different
    work and the report keeps them apart.
    """
    known = {c.lower() for c in _detector_classes()}
    out: Dict[str, Dict[str, Any]] = {}
    for quantity, prefixes in sorted(INK_CLASS_PREFIXES.items()):
        skip = tuple(x.lower() for x in INK_CLASS_EXCLUDE.get(quantity, ()))
        hits = sorted({c for c in known
                       if any(c.startswith(p.lower()) for p in prefixes)
                       and not c.startswith(skip or ("\0",))})
        out[quantity] = {
            "detector_classes": hits,
            "verdict": ("filed under Q.GLYPH_BOX -- a NAMING gap"
                        if hits else "no detector class -- a READING gap"),
        }
    return out


def stub_starvation() -> Dict[str, Dict[str, Any]]:
    """Declared stubs, and which of their declared inputs nobody gathers.

    ⚠️ THE POINT: a stub whose input is also ungathered is not one repair, it
    is two, and the record says so only if you ask. Writing the adjudicator
    would leave it abstaining for lack of evidence -- which is honest, and
    still not a working stage.
    """
    from . import adjudicate as A
    from . import adjudicators  # noqa: F401
    from .record import Q
    by_value = {getattr(Q, n): n for n in declared()}
    got = gathered()
    observed = {q for q, r in got.items() if r["observed_by"]}
    owned = {by_value.get(q, q) for q in A.REGISTRY}

    out: Dict[str, Dict[str, Any]] = {}
    for quantity, spec in A.REGISTRY.items():
        if not spec.stub:
            continue
        wants = [by_value.get(w, w) for w in spec.wants]
        out[by_value.get(quantity, quantity)] = {
            "wants": wants,
            "ungathered_inputs": [w for w in wants
                                  if w not in observed and w not in owned],
        }
    return dict(sorted(out.items()))


# ─────────────────────────────────────────────────────────────────────────────
# 3c. What the PAGE offers -- the class space, against the vocabulary
# ─────────────────────────────────────────────────────────────────────────────

#: Detector class family -> the `record.Q` that names its ink, or None.
#:
#: ⚠️ THE THIRD SOURCE FOR "COULD BE GATHERED", AND THE ONLY ONE THAT DOES NOT
#: DEPEND ON THE LEGACY PIPELINE. `legacy_event_keys()` finds what the current
#: reader carries; this finds what the DETECTOR ALREADY FIRES ON that no
#: quantity names -- including families the legacy pipeline drops too, so they
#: appear in neither the event dict nor the export.
#:
#: ⚠️ `export_coverage.py` warns that auditing the class space for "classes
#: nothing consumes" calls accidentals CONSUMED, because they are -- into
#: pitch. That warning is about a different question and is respected here:
#: this asks whether a family has its OWN NAME in the record, not whether
#: anything eventually uses it. `Q.GLYPH_BOX` carries every one of them, so a
#: `None` is never "the ink is lost" -- it is "no consumer can ask for it and
#: no abstention can be recorded about it", which is the chord fault exactly.
FAMILY_TO_Q: Dict[str, Optional[str]] = {
    "accidental": None,          # in-bar accidentals: only GLYPH_BOX carries them
    "arpeggiato": None,
    "artic": "ARTICULATION_MARK",
    "augmentation": "AUG_DOT",
    "beam": "BEAM_STROKE",
    "brace": None,               # the GLYPH; `Q.GROUP_SYMBOL` is the verdict
    "c": "CLEF_GLYPH",
    "caesura": None,
    "clef": "CLEF_GLYPH",
    "coda": None,
    "dynamic": "DYNAMIC_LETTER",
    "f": "CLEF_GLYPH",
    "fermata": "FERMATA_MARK",   # ⚠️ CLOSED 2026-09-10; was None
    "fingering": "TUPLET_MARKER",  # ⚠️ `fingering3` IS a triplet digit here
    "flag": "FLAG",
    "g": "CLEF_GLYPH",
    "grace": None,
    "key": "KEYSIG_MARKER",
    "keyboard": None,            # keyboardPedal*
    "ledger": "GLYPH_LADDER",
    "notehead": "NOTEHEAD_CLASS",
    "ornament": None,
    "ottava": None,
    "repeat": None,
    "rest": "REST",              # ⚠️ CLOSED on main 2026-09-09; was None
    "segno": None,
    "slur": "ARC_BOX",
    "staff": "STAFF_LINES",
    "stem": "STEM",
    "strings": None,             # stringsDownBow / stringsUpBow
    "tie": "ARC_BOX",
    "time": "METER_GLYPH",
    "tremolo": None,
    "tuplet": "TUPLET_MARKER",
    "unpitched": None,
}


#: A family whose `None` is DELIBERATE even though a `Q` of that name exists,
#: with the reason. ⚠️ An inventory, not a suppression: the guard in
#: `test_staged_gather_coverage.py` fails on any other None-with-a-Q, so a
#: family that quietly grows a gather quantity is a loud failure.
FAMILY_Q_IS_ELSEWHERE: Dict[str, str] = {
    "accidental":
        "`Q.ACCIDENTAL` exists but is an EVALUATE consequence -- the pitch "
        "respelled once the key settles -- not a gather-stage reading of the "
        "printed glyph. The in-bar accidental is still filed only as an "
        "anonymous `Q.GLYPH_BOX`, and it is SCOPE rather than a mark: it "
        "holds to the barline (`transcribe.py:2210` implements exactly that), "
        "which is a span the record has nowhere to put.",
}


def _family(class_name: str) -> str:
    import re
    m = re.match(r"[a-z]+", class_name)
    return m.group(0) if m else class_name


def class_space_coverage() -> Dict[str, Any]:
    """Every detector family, and whether a quantity names it.

    ⚠️ Fails loudly on a family in neither the map nor the class space, so a
    wider class space is a broken build rather than a silent blind spot --
    the contract `class_aliases.unaccounted()` holds for the same reason.
    """
    classes = _detector_classes()
    fams: Dict[str, List[str]] = {}
    for c in classes:
        fams.setdefault(_family(c), []).append(c)

    got = gathered()
    observed = {q for q, r in got.items() if r["observed_by"]}

    named, unnamed, declared_only = {}, {}, {}
    for fam in sorted(fams):
        quantity = FAMILY_TO_Q.get(fam, "__UNMAPPED__")
        row = {"classes": len(fams[fam]), "quantity": quantity}
        if quantity == "__UNMAPPED__":
            unnamed[fam] = {**row, "state": "UNMAPPED -- add it to FAMILY_TO_Q"}
        elif quantity is None:
            unnamed[fam] = {**row, "state": "no quantity names this family"}
        elif quantity in observed:
            named[fam] = {**row, "state": "gathered"}
        else:
            declared_only[fam] = {**row, "state": "quantity declared, ungathered"}

    return {
        "families": len(fams),
        "classes": len(classes),
        "gathered": named,
        "declared_ungathered": declared_only,
        "no_quantity": unnamed,
        "unmapped": sorted(f for f in fams if f not in FAMILY_TO_Q),
    }


# ─────────────────────────────────────────────────────────────────────────────
# 4. The report
# ─────────────────────────────────────────────────────────────────────────────


def report() -> Dict[str, Any]:
    got = gathered()
    decl = set(declared())
    verdicts = verdict_quantities()
    consequences = consequence_quantities()
    wants = wanted()

    observed = {q for q, r in got.items() if r["observed_by"]}
    abstain_only = {q for q, r in got.items()
                    if not r["observed_by"] and r["abstained_by"]}
    declared_only = {q for q in got if not got[q]["observed_by"]
                     and not got[q]["abstained_by"]}

    ungathered = decl - set(got)
    measurement_gap = sorted(ungathered - verdicts - consequences)
    verdict_elsewhere = sorted(ungathered & verdicts)
    consequence_elsewhere = sorted((ungathered & consequences) - verdicts)

    wanted_ungathered = {q: d for q, d in wants.items()
                         if q in decl and q not in observed
                         and q not in verdicts and q not in consequences}

    return {
        "gathered": {
            "observed": sorted(observed),
            "abstain_only": sorted(abstain_only),
            "mentioned_only": sorted(declared_only),
            "detail": {q: got[q] for q in sorted(got)},
        },
        "not_gathered": {
            "verdict_elsewhere": verdict_elsewhere,
            "consequence_elsewhere": consequence_elsewhere,
            "declared_ungathered": measurement_gap,
        },
        "wanted_but_ungathered": wanted_ungathered,
        "no_vocabulary": {k: {"why": v,
                              "seen_in": legacy_event_keys().get(k, [])}
                          for k, v in sorted(NO_VOCABULARY.items())},
        "class_space": class_space_coverage(),
        "stub_starvation": stub_starvation(),
        "ink_present_elsewhere": ink_present_elsewhere(),
        "unaccounted": unaccounted(),
        "counts": {
            "declared": len(decl),
            "observed": len(observed),
            "abstain_only": len(abstain_only),
            "declared_ungathered": len(measurement_gap),
            "no_vocabulary": len(NO_VOCABULARY),
            "unaccounted": len(unaccounted()),
        },
    }


def _print(rep: Dict[str, Any]) -> None:
    c = rep["counts"]
    print("═══ GATHER COVERAGE ═══")
    print(f"  declared quantities        {c['declared']:>4}")
    print(f"  OBSERVED by a gatherer     {c['observed']:>4}")
    print(f"  abstain-only (declared)    {c['abstain_only']:>4}")
    print(f"  declared, never gathered   {c['declared_ungathered']:>4}")
    print(f"  NO VOCABULARY AT ALL       {c['no_vocabulary']:>4}")
    print(f"  unaccounted (must be 0)    {c['unaccounted']:>4}")

    print("\n─── 1. GATHERED (observed) ───")
    for q in rep["gathered"]["observed"]:
        d = rep["gathered"]["detail"][q]
        readers = ",".join(d["readers"]) or "-"
        print(f"  {q:<28} {readers:<32} {','.join(d['observed_by'])}")

    if rep["gathered"]["abstain_only"]:
        print("\n─── 1b. ABSTAIN-ONLY (a reader declared it and never read) ───")
        for q in rep["gathered"]["abstain_only"]:
            d = rep["gathered"]["detail"][q]
            print(f"  {q:<28} {','.join(d['reasons']) or '-'}")

    print("\n─── 2. NOT GATHERED ───")
    ng = rep["not_gathered"]
    print(f"  owned by adjudicate  : {', '.join(ng['verdict_elsewhere']) or '-'}")
    print(f"  owned by evaluate    : {', '.join(ng['consequence_elsewhere']) or '-'}")
    print(f"  DECLARED, UNGATHERED : {', '.join(ng['declared_ungathered']) or '-'}")

    if rep["wanted_but_ungathered"]:
        print("\n─── 3. WANTED BY A DECISION AND NEVER GATHERED ───")
        for q, who in sorted(rep["wanted_but_ungathered"].items()):
            print(f"  {q:<28} wanted by {', '.join(who)}")

    print("\n─── 4. NO VOCABULARY (legacy carries it, record cannot name it) ───")
    for k, v in rep["no_vocabulary"].items():
        print(f"  {k:<18} {v['why'][:100]}")

    starved = {k: v for k, v in rep["stub_starvation"].items()
               if v["ungathered_inputs"]}
    if starved:
        print("\n─── 3b. DECLARED STUBS WHOSE INPUT IS ALSO UNGATHERED ───")
        for name, v in starved.items():
            ink = rep["ink_present_elsewhere"]
            notes = [f"{q}: {ink[q]['verdict']}" for q in v["ungathered_inputs"]
                     if q in ink]
            print(f"  {name:<22} ungathered: {', '.join(v['ungathered_inputs'])}")
            for n in notes:
                print(f"  {'':<22}   {n}")

    cs = rep["class_space"]
    print(f"\n─── 5. DETECTOR CLASS SPACE ({cs['classes']} classes, "
          f"{cs['families']} families) ───")
    print(f"  named and gathered   : {', '.join(sorted(cs['gathered'])) or '-'}")
    print(f"  named, not gathered  : {', '.join(sorted(cs['declared_ungathered'])) or '-'}")
    print("  NO QUANTITY NAMES IT :")
    for fam, v in sorted(cs["no_quantity"].items()):
        print(f"      {fam:<14} {v['classes']:>3} classes   {v['state']}")

    if rep["unaccounted"]:
        print("\n⚠️  UNACCOUNTED legacy keys (add to LEGACY_TO_Q or NO_VOCABULARY):")
        for k, where in sorted(rep["unaccounted"].items()):
            print(f"  {k:<28} {','.join(where)}")


def main(argv: Optional[List[str]] = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", action="store_true", help="machine-readable")
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args(argv)

    rep = report()
    if args.json or args.out:
        text = json.dumps(rep, indent=2, sort_keys=True)
        if args.out:
            args.out.write_text(text + "\n")
        else:
            print(text)
    else:
        _print(rep)
    return 1 if (rep["unaccounted"] or rep["class_space"]["unmapped"]) else 0


if __name__ == "__main__":
    raise SystemExit(main())
