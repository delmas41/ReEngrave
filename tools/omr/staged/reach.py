"""Does every QUANTITY reach a consumer? — the fifth derived question.

    python3 -m tools.omr.staged.reach            # the table
    python3 -m tools.omr.staged.reach --json
    python3 -m tools.omr.staged.reach --check    # non-zero on anything not
                                                 # on KNOWN_GAPS
    python3 -m tools.omr.staged.reach --run rec.json   # which edges CARRIED

⚠️⚠️ **WHY THIS IS NOT A SIXTH COPY OF AN EXISTING TOOL.** Four derived
instruments already stand and each asks a different question:

  `gather_coverage`  is it OBSERVED at all?
  `inventory --check` is a `wants` entry actually READ?
  `wiring --check`   can a declared read REACH it (frame / detail / roundtrip)?
  `no_producer`      is a threaded PARAMETER ever supplied?

**None of them asks whether anything reads a quantity AT ALL.** `wiring.py`'s
own docstring defers that one to run time -- *"`export.status_census` already
answers it at RUN time as a PARTITION"* -- and that is measurement-first. A
quantity that is gathered, declared by nobody and read by nobody is reported
by `gather_coverage` as **GATHERED (observed)**, i.e. as healthy.
`Q.STAFF_EXTENT` and `Q.STAFF_SKEW` sit in exactly that cell today.

## ⚠️ THE ACCESSOR SET IS DERIVED, AND THIS TOOL'S OWN FIRST RUN PROVES WHY

The first version hand-wrote the accessor names off a `grep`, missed
`rec.obs_of(...)` and `ev.state(...)`, and reported `Q.CELL_BOX` and
`Q.KEYSIG_RUN_POSITION` as read by nothing -- two false positives, from this
repo's own named anti-pattern, in a tool written to catch that anti-pattern.
`_accessors()` now reads every public method of `Log` / `Evidence` /
`export.Record` that takes a `quantity` parameter, and takes the ARGUMENT
INDEX from the signature rather than assuming it is first: `observe` and
`abstain` take the subject first, so an index assumption silently reads the
subject as the quantity and reports every gather site as unresolved.

## The four outcomes, which are four different repairs

  LIVE        produced and read by a later stage -- nothing to do
  GHOST       in `Q`, produced by nothing and declared by nobody
  UNREAD      produced, and NOTHING anywhere reads it
  GATHER_ONLY read, but only inside GATHER -- no later stage sees it

⚠️ UNREAD is not automatically a bug: a quantity may be gathered so a HUMAN
can read the record. What it must never be is UNREAD *and unremarked*, which
is how `Q.STEM` stayed unread through three separate discoveries.
"""
from __future__ import annotations

import argparse
import ast
import collections
import importlib
import inspect
import json
import pathlib
import sys
from typing import Dict, Set, Tuple

from .record import Q

#: Quantities whose lack of a reader is ACCOUNTED FOR, each with its reason.
#:
#: ⚠️ An INVENTORY, never a suppression list -- the same contract as
#: `export_coverage.KNOWN_GAPS` and `inventory.KNOWN_GAPS`. `--check` fails on
#: anything NOT here, **and on an entry nothing reports any more**: a closed
#: gap must LEAVE the list or the list stops describing the pipeline and starts
#: describing its history.
KNOWN_GAPS: Dict[str, str] = {
    # ── already reported by a sibling instrument; listed so this tool's own
    #    --check does not duplicate a failure another tool already owns.
    Q.DOSSIER_FACT: (
        "reported by `no_producer` as an OPEN FINDING: the staged CLI has no "
        "`--dossier`, so nothing ever supplies one and the row is an abstain. "
        "Also an inert `wants` on key_signature and meter (inventory owns that "
        "half)."),
    Q.GAP_BRIDGING: (
        "inert declaration, owned by `inventory --check`: the connectivity veto "
        "already ran in GATHER and `adjudicate_system_membership` reads the "
        "COUNT, not the bridging."),
    Q.GLYPH_CONF: (
        "inert declaration, owned by `inventory --check`. ⚠️ THE STANDING "
        "OBSERVATION: `_dedupe_cross_staff_detections` has both detections' "
        "confidences in hand at the moment it decides and uses neither, and the "
        "staged `glyph_owner` reproduced that."),
    Q.KEYSIG_MARKER: (
        "inert declaration, owned by `inventory --check`: the decision reads "
        "`keysig_clef_fit`, which the markers already feed in GATHER."),
    Q.SYSTEMIC_COLUMN: (
        "ABSTAIN-ONLY, and `gather_coverage` section 1b already reports it as "
        "such -- a reader declared it and never observed one."),
    Q.CLEF_REFUSAL_BRANCH: "DECLARED, UNGATHERED — reported by `gather_coverage` section 2.",
    Q.INPUT_DOMAIN: "DECLARED, UNGATHERED — reported by `gather_coverage` section 2.",
    Q.LEFT_EDGE_INK: "DECLARED, UNGATHERED — reported by `gather_coverage` section 2.",
    Q.TEXT_LAYER: (
        "DECLARED, UNGATHERED — reported by `gather_coverage` section 2. ⚠️ Not "
        "to be confused with `READERS.TEXT_LAYER`, which is alive and is what "
        "`gather_margin_labels` files a label under."),

    Q.DOCUMENT_IDENTITY: (
        "⚠️ BY DESIGN, NOT A FAULT — recorded 2026-09-17 with "
        "`gather_document_identity`, and the same producer-only discipline as "
        "`Q.INK` below. It files WHICH PRINTING this is (edition, publisher, "
        "work, scan type) on the DOCUMENT at `source_kind: \"catalog\"`, "
        "because where a mark falls is a property of the PLATE and the "
        "conditioning variable had no producer at all: `grep publisher "
        "tools/omr/staged/gather.py` returned ONE COMMENT while the catalog "
        "that knows has been committed all along. ⚠️ IT IS ALSO DEFAULT-OFF "
        "(`OMR_DOCUMENT_IDENTITY`, allow-list), so on a default run nothing "
        "observes it either. The consumer it is aimed at is "
        "`tools/omr/positional_store.py`, which reads it through "
        "`identity_of_record` on a SAVED record rather than through a staged "
        "accessor — which is why this tool cannot see the read. REMOVE THIS "
        "ENTRY the day a DECISION reads it."),

    Q.INK: (
        "⚠️ BY DESIGN, NOT A FAULT — recorded 2026-09-17 when `gather_ink` "
        "landed. `A-DUR-5` was deliberately built as the PRODUCER ONLY: it "
        "makes GATHER's population the INK rather than the detector's output, "
        "and wires into no consumer, so that its reach could be measured "
        "without the measurement being circular. The consumers it is aimed at "
        "already exist and are waiting — `Q.ONSET_COLUMN`, the groups layer's "
        "unanimous/majority/split, `Verdict.correlated` and the INFER stage. "
        "⚠️ THE FIRST CONSUMER IS THE RESIDUE ADJUDICATOR: *what is this ink?* "
        "-- a decision that may answer `staff_residue` and must live in "
        "ADJUDICATE, because nothing may be filtered at the gather site. "
        "REMOVE THIS ENTRY the day a consumer lands."),

    # ── THE TEN FAMILY POSITIONS + their refusal. OPEN BY DESIGN. ──────────
    #
    # ⚠️⚠️ THE SAME DISCIPLINE AS `Q.INK` ONE DAY EARLIER, AND FOR THE SAME
    # REASON: a producer and its first consumer landing together makes the
    # reach measurement circular. `positions.py` answers Sean's 2026-09-17
    # instruction — *"give the families real position information - or if it
    # should be symbol specific then make it so"* — for the eleven families
    # `capture.py` graded `position: NONE`, and wires NOTHING to read them.
    #
    # ⚠️ EACH ONE'S FIRST CONSUMER IS NAMED, because *UNREAD and unremarked*
    # is how `Q.STEM` stayed unread through three separate discoveries.
    # **REMOVE AN ENTRY THE DAY ITS CONSUMER LANDS.**
    Q.REST_POSITION: (
        "⚠️ OPEN BY DESIGN — producer only, `OMR_FAMILY_POSITIONS`. FIRST "
        "CONSUMER: `adjudicate_duration`, which reads a rest's CLASS NAME and "
        "nothing else, while a whole rest and a half rest are the same shape "
        "differing only in which line they touch and on which side. Second: "
        "`OMR_WHOLE_REST_INK`, whose position witness is reconstructed "
        "per-document from the detector's boxes and INVERTS between two "
        "publishers."),
    Q.ARC_POSITION: (
        "⚠️ OPEN BY DESIGN — producer only. FIRST CONSUMER: "
        "`adjudicate_arc_kind`, which declares `notehead_staff_position` (the "
        "NOTES' positions) and has nothing about the curve's own ink. "
        "`depth_steps` is the geometric half of the tie/slur grammar that "
        "`OMR_ARC_RECLASS` decides without."),
    Q.ARTICULATION_POSITION: (
        "⚠️ OPEN BY DESIGN — producer only. FIRST CONSUMER: "
        "`adjudicate_articulation_owner`, whose attach rule requires the "
        "geometry to AGREE with the side the class names — and the side is "
        "read off that class, so today the two cannot disagree."),
    Q.FERMATA_POSITION: (
        "⚠️ OPEN BY DESIGN — producer only. FIRST CONSUMER: "
        "`adjudicate_fermata_owner`. ⚠️ Its `nearest_in_bar` fallback fired "
        "ZERO times on the page it was measured on, so this family's own "
        "reach is the thing to measure before its accuracy."),
    Q.ORNAMENT_POSITION: (
        "⚠️ OPEN BY DESIGN — producer only. FIRST CONSUMER: "
        "`adjudicate_ornament_owner`. The sharpest case is the TREMOLO, whose "
        "class states no side at all because it rides the stem."),
    Q.TUPLET_MARKER_POSITION: (
        "⚠️ OPEN BY DESIGN — producer only. FIRST CONSUMER: "
        "`adjudicate_tuplet_ratio`, which fired ZERO times across 286 runs of "
        "the plumbing matrix on fixtures printing explicit tuplets. One "
        "`numeral` class covers meters, tuplet digits, fingerings and measure "
        "numbers — *a POSITIONAL distinction, made by where the digit "
        "stands* — so shape structurally cannot answer this and position is "
        "the only thing that can."),
    Q.METER_GLYPH_POSITION: (
        "⚠️ OPEN BY DESIGN — producer only. FIRST CONSUMER: "
        "`_meter_from_digits`, which accepts ANY two `timeSig*` glyphs at two "
        "different `y_center` values — no width, height, x or half test — and "
        "is how one barline broken into two fragments became the Litolff p.62 "
        "`3/4` this project cited for weeks."),
    Q.DYNAMIC_BAND_POSITION: (
        "⚠️ OPEN BY DESIGN — producer only, and PROMOTED rather than "
        "invented: the number was already on `Q.DYNAMIC_LETTER` as a detail "
        "of a SCORED row. FIRST CONSUMER: `adjudicate_glyph_owner`, which "
        "resolves a contested letter by DISTANCE — a quantity this repo has "
        "already measured being a coin flip (5-62 px) — where the band says "
        "24% of letters stand in the band of the staff immediately above, "
        "distance exactly 1, no exceptions."),
    Q.WEDGE_BAND_POSITION: (
        "⚠️ OPEN BY DESIGN — producer only, PROMOTED for the CV rung and "
        "MEASURED for the detector rung, which never carried one. FIRST "
        "CONSUMER: `adjudicate_wedge_anchor`."),
    Q.DIRECTION_BAND_POSITION: (
        "⚠️ OPEN BY DESIGN — producer only, and the only one of the ten that "
        "is genuinely NEW: this family has no detector row to promote a "
        "detail off. FIRST CONSUMER: `adjudicate_direction`, whose only "
        "staff-relative input today is `placement`, an above/below far too "
        "coarse to separate a `cresc.` in the dynamics row from an `Allegro` "
        "above the system."),
    Q.CELL_POSITION_BASIS: (
        "⚠️ ABSTAIN-ONLY BY CONSTRUCTION, never observed — it is the REFUSAL "
        "a cell with no five-line grid files, once, instead of the position "
        "rows it cannot measure. Same shape as `Q.SYSTEMIC_COLUMN` above. Its "
        "consumer is a HUMAN reading the record: it is what separates *this "
        "page prints no rests* from *this staff has one line and no ruler*."),

    # ── OPEN FINDINGS. Reported by NO other instrument. Recorded rather than
    #    excused, so `--check` can pass while the finding stays visible.
    Q.STAFF_EXTENT: (
        "⚠️ OPEN FINDING, NOT EXCUSED — recorded 2026-09-16, found by this "
        "check. `gather_geometry` observes it (`gather.py:121`) and it appears "
        "NOWHERE else in the whole non-test tree: no `wants`, no read, no "
        "export. `gather_coverage` files it under GATHERED (observed), i.e. as "
        "healthy. REMOVE THIS ENTRY the day a consumer lands."),
    Q.STAFF_SKEW: (
        "⚠️ OPEN FINDING, NOT EXCUSED — recorded 2026-09-16, found by this "
        "check. Same shape as STAFF_EXTENT: observed at `gather.py:133` (and "
        "abstained at :130) and read by nothing anywhere. The measured tilt/bow "
        "that `OMR_CELL_LINE_TRACE` exists to correct is recorded and never "
        "consulted."),
    Q.GROUP_SYMBOL: (
        "⚠️ OPEN FINDING — a DECIDED verdict no stage reads. CLAUDE.md records "
        "`<part-group>` as scoped and NOT built, with zero reach measured "
        "(`no_identity` on 22 of 22 staves), so the state is known; what was "
        "not reported by any instrument is that the verdict reaches no "
        "consumer at all."),
    Q.SYSTEM_MEMBERSHIP: (
        "⚠️ OPEN FINDING — decision #0's verdict is read by nothing. It appears "
        "in `implicates`, in `DOWNHILL`, in `legacy.EXTRACTED_QUANTITIES` and "
        "in `wants` — all DECLARATIONS, none of them a read."),
}

STAGE_OF_FILE = {
    "gather.py": "GATHER", "legacy.py": "GATHER",
    # ⚠️ A GATHER MODULE, and this tool's `unaccounted_modules()` is what
    # caught it being in neither list on the day it landed — a new staged
    # module is otherwise silently skipped and every quantity only it reads
    # reads as UNREAD, which for a module of ten producers would have been a
    # very plausible-looking table.
    "positions.py": "GATHER",
    "adjudicate.py": "ADJUDICATE", "groups.py": "ADJUDICATE",
    "evaluate.py": "EVALUATE", "consequences.py": "EVALUATE",
    "infer.py": "INFER", "inferences.py": "INFER",
    "export.py": "EXPORT",
    "pipeline.py": "HARNESS", "record.py": "HARNESS",
}
ORDER = ["GATHER", "ADJUDICATE", "EVALUATE", "INFER", "EXPORT", "HARNESS"]

#: Staged modules that are deliberately NOT a stage — instruments that REPORT
#: on quantities without consuming them, and the package marker.
#:
#: ⚠️⚠️ `STAGE_OF_FILE` is a HAND LIST keyed on filename, so a new staged
#: module is silently skipped and every quantity only it reads reads as
#: UNREAD. `unaccounted_modules()` closes that: every `.py` under `staged/`
#: must be in one list or the other, and `--check` fails otherwise. An earlier
#: draft guarded this with a separate `INSTRUMENTS` frozenset, which was an
#: EQUIVALENT MUTANT — the stage map already skipped those files, so the
#: exclusion could never change an answer. Deleted rather than left as
#: decoration.
NOT_A_STAGE = frozenset({
    "inventory.py", "health.py", "wiring.py", "gather_coverage.py",
    "record_coverage.py", "reach.py", "__init__.py", "__main__.py",
    # ⚠️ `capture.py` is a DERIVED CHECK, like the six above it: it asks, per
    # notation family, whether the ink's SHAPE, its staff-grid POSITION and
    # the RASTER it was measured on are recorded. It names quantities in
    # order to audit them and reads none of them at runtime — the same reason
    # it declares `DERIVED_CHECK = True` for `wiring`'s DETAIL question,
    # which counted its mention of `staff_lines_erased` as a consumer.
    "capture.py",
    # ⚠️ `meaning.py` is the seventh derived check: what KIND of measurement
    # is a quantity, and may two of its rows be COMBINED. It names detail
    # keys and frame tokens in order to audit them and reads none of them at
    # run time, so it declares `DERIVED_CHECK = True` for the same reason
    # `capture.py` does.
    "meaning.py",
    # ⚠️ `brakes.py` is a DERIVED CHECK for the same reason: it asks whether a
    # REFUSAL's premise was written against a capability the staged
    # architecture has since grown, and it NAMES quantities and reasons in
    # order to audit them while reading none of them at run time. It declares
    # `DERIVED_CHECK = True` for `wiring`'s DETAIL question too. Registering it
    # here is not optional — `unaccounted_modules()` must return empty, and a
    # staged `.py` in neither list breaks it.
    #
    # ⚠️⚠️ THAT GUARD WAS A TEST AND NOT `--check`, AND IS NOW BOTH. The
    # brake audit found it by a mutation arm that removed this very line and
    # watched `reach --check` exit 0, and reported it rather than repairing
    # it; the measurement-meaning audit found the same gap independently.
    # `check()` now calls `unaccounted_modules()` and FAILS on an
    # unregistered module (proved with a stray `_orphan_probe.py`: exit 1
    # naming it, exit 0 once removed). ⚠️ THE TWO HALVES LANDED ON DIFFERENT
    # BRANCHES AND ONLY THIS MERGE HAS BOTH — the comment was true when
    # written and false the moment the trees met, which is exactly the
    # 'merged tree is the one thing nobody runs' hazard.
    "brakes.py",
    # ⚠️ `trace.py` is the ninth derived check, and the only one that is
    # PER-SUBJECT rather than aggregate: given a saved record and a subject
    # key it replays what each stage DID to that symbol, and given a family
    # it walks the stage funnel. Like the eight above it, it NAMES quantities
    # and reason words in order to audit them and reads none of them at run
    # time, so it declares `DERIVED_CHECK = True` for `wiring`'s DETAIL
    # question as well.
    #
    # ⚠️ REGISTERING IT HERE IS NOT OPTIONAL, and the control was run in both
    # directions rather than assumed: with `trace.py` on disk and this line
    # absent, `reach --check` exits 1 naming it; move the file aside and it
    # exits 0. That is the guard the brake audit's mutation arm asked for,
    # doing its job on the next module to arrive.
    "trace.py",
})


def unaccounted_modules() -> list:
    """Staged modules in neither `STAGE_OF_FILE` nor `NOT_A_STAGE`."""
    root = pathlib.Path(__file__).resolve().parent
    out = []
    for p in sorted(root.rglob("*.py")):
        if p.name.startswith("test_"):
            continue
        if p.parent.name == "adjudicators":
            continue          # the whole package is ADJUDICATE, by directory
        if p.name in STAGE_OF_FILE or p.name in NOT_A_STAGE:
            continue
        out.append(str(p.relative_to(root)))
    return out


def _accessors() -> Tuple[Dict[str, int], Dict[str, int]]:
    """(read, write) -> {method name: index of its `quantity` argument}.

    ⚠️ DERIVED from the classes, and the INDEX is derived too. `observe` and
    `abstain` take `subject` first; assuming index 0 makes every gather site
    read as unresolved and every quantity as a GHOST.
    """
    read: Dict[str, int] = {}
    write: Dict[str, int] = {}
    for mname in ("tools.omr.staged.record", "tools.omr.staged.adjudicate",
                  "tools.omr.staged.export"):
        mod = importlib.import_module(mname)
        for _, cls in inspect.getmembers(mod, inspect.isclass):
            if cls.__module__ != mname:
                continue
            for name, fn in inspect.getmembers(cls, inspect.isfunction):
                if name.startswith("_"):
                    continue
                try:
                    params = [p for p in inspect.signature(fn).parameters
                              if p != "self"]
                except (TypeError, ValueError):
                    continue
                if "quantity" not in params:
                    continue
                (write if name in ("observe", "abstain") else read)[name] = \
                    params.index("quantity")
    return read, write


def _q_values() -> Dict[str, str]:
    return {k: v for k, v in vars(Q).items()
            if isinstance(v, str) and not k.startswith("_")}


def survey() -> dict:
    by_attr = _q_values()
    values = set(by_attr.values())
    read_at, write_at = _accessors()

    def qname(node):
        if (isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name)
                and node.value.id == "Q" and node.attr in by_attr):
            return by_attr[node.attr]
        if isinstance(node, ast.Constant) and node.value in values:
            return node.value
        return None

    produced: Dict[str, Set[str]] = collections.defaultdict(set)
    declared: Dict[str, Set[str]] = collections.defaultdict(set)
    read: Dict[str, Set[str]] = collections.defaultdict(set)
    sites: Dict[str, Set[str]] = collections.defaultdict(set)
    unresolved = []

    root = pathlib.Path(__file__).resolve().parent
    files = [p for p in sorted(root.rglob("*.py"))
             if not p.name.startswith("test_")]
    for path in files:
        stage = ("ADJUDICATE" if path.parent.name == "adjudicators"
                 else STAGE_OF_FILE.get(path.name))
        if stage is None:
            continue
        for node in ast.walk(ast.parse(path.read_text())):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
                continue
            attr = node.func.attr
            table = write_at if attr in write_at else (read_at if attr in read_at else None)
            if table is None:
                continue
            idx = table[attr]
            if len(node.args) <= idx:
                unresolved.append(f"{path.name}:{node.lineno} .{attr}(<kwarg>)")
                continue
            q = qname(node.args[idx])
            if q is None:
                unresolved.append(f"{path.name}:{node.lineno} .{attr}(<expr>)")
                continue
            site = f"{path.name}:{node.lineno}"
            if attr == "observe":
                produced[q].add(stage); sites[q].add(site)
            elif attr == "abstain":
                declared[q].add(stage)
            else:
                read[q].add(stage); sites[q].add(site)

    # VERDICTS are produced too: a decision produces its own quantity, a
    # consequence produces its effect, and both DECLARE what they consume.
    from . import adjudicate, evaluate
    importlib.import_module("tools.omr.staged.adjudicators")
    importlib.import_module("tools.omr.staged.consequences")
    importlib.import_module("tools.omr.staged.inferences")
    for quantity, spec in adjudicate.REGISTRY.items():
        produced[quantity].add("ADJUDICATE")
        for want in spec.wants:
            declared[want].add("ADJUDICATE")
    for rule in evaluate.RULES:
        produced[rule.effect].add("EVALUATE")
        declared[rule.cause].add("EVALUATE")
    from . import infer
    for rule in getattr(infer, "RULES", []):
        for q in getattr(rule, "reads", ()):
            read[q].add("INFER")

    rows = []
    for _, q in sorted(by_attr.items(), key=lambda kv: kv[1]):
        p, d, r = produced.get(q, set()), declared.get(q, set()), read.get(q, set())
        if not p and not d:
            state = "GHOST"
        elif not r:
            state = "UNREAD"
        elif not (r - {"GATHER"}):
            state = "GATHER_ONLY"
        else:
            state = "LIVE"
        rows.append({"quantity": q, "state": state, "produced": sorted(p),
                     "declared": sorted(d), "read": sorted(r),
                     "sites": sorted(sites.get(q, ()))[:4]})

    return {
        "rows": rows,
        "unresolved": unresolved,
        "controls": {
            "read_accessors": sorted(read_at),
            "write_accessors": sorted(write_at),
            "quantities": len(by_attr),
            "with_a_producer": sum(1 for r in rows if r["produced"]),
            "with_a_reader": sum(1 for r in rows if r["read"]),
            "quantity_stage_read_pairs": sum(len(v) for v in read.values()),
            "files_walked": len(files),
        },
    }


def _report(s: dict, check: bool) -> int:
    rows = s["rows"]
    print("═══ DOES EVERY QUANTITY REACH A CONSUMER? ═══════════════════════")
    bad = [r for r in rows if r["state"] != "LIVE"]
    for state, blurb in (("GHOST", "in Q, produced by nothing and declared by nobody"),
                         ("UNREAD", "produced, and NOTHING anywhere reads it"),
                         ("GATHER_ONLY", "read only inside GATHER")):
        group = [r for r in rows if r["state"] == state]
        print(f"\n{state} — {blurb} ({len(group)})")
        if not group:
            print("   none")
        for r in group:
            mark = "  " if r["quantity"] in KNOWN_GAPS else "⚠️"
            print(f" {mark} {r['quantity']:30} produced {','.join(r['produced']) or '—':22}"
                  f" read {','.join(r['read']) or '—'}")

    unaccounted = [r["quantity"] for r in bad if r["quantity"] not in KNOWN_GAPS]
    reported = {r["quantity"] for r in bad}
    stale = [q for q in KNOWN_GAPS if q not in reported]

    c = s["controls"]
    print("\n── POSITIVE CONTROLS (a zero means the question did not run) ──")
    for k in ("quantities", "with_a_producer", "with_a_reader",
              "quantity_stage_read_pairs", "files_walked"):
        print(f"   {k:24} {c[k]}")
    print(f"   read accessors derived   {len(c['read_accessors'])} {c['read_accessors']}")
    print(f"   write accessors derived  {len(c['write_accessors'])} {c['write_accessors']}")
    print(f"   call sites unresolved    {len(s['unresolved'])}")

    # ⚠️⚠️ THE MODULE ROSTER, WHICH THIS CHECK PROMISED TO ENFORCE AND DID
    # NOT. `NOT_A_STAGE`'s own comment says *"every `.py` under `staged/` must
    # be in one list or the other, and `--check` fails otherwise"* — and until
    # 2026-09-17 `unaccounted_modules()` was called by NOTHING but
    # `test_staged_reach.py:61`, so the CHECK exited 0 on an unregistered
    # module while the docstring said it would not. `STAGE_OF_FILE` is a HAND
    # LIST keyed on filename, so an unregistered staged module makes every
    # quantity only it reads read as UNREAD — the exact silent failure this
    # roster exists to prevent. CLAUDE.md's *a rule described in a docstring
    # and never built*, inside a derived check; found by the
    # measurement-meaning audit, which tripped it with its own new module.
    orphan_modules = unaccounted_modules()

    print(f"\n── {len(bad)} not LIVE, {len(unaccounted)} unaccounted, "
          f"{len(stale)} stale gap entries, "
          f"{len(orphan_modules)} unregistered modules")
    for q in unaccounted:
        print(f"   ⚠️ UNACCOUNTED {q}")
    for q in stale:
        print(f"   ⚠️ STALE GAP   {q} — nothing reports it any more; delete the entry")
    for m in orphan_modules:
        print(f"   ⚠️ UNREGISTERED MODULE {m} — put it in `STAGE_OF_FILE` or "
              f"`NOT_A_STAGE`; until then every quantity only it reads counts "
              f"as UNREAD")

    if c["with_a_reader"] == 0 or c["quantity_stage_read_pairs"] == 0:
        print("\n⚠️ POSITIVE CONTROL AT ZERO — the question did not run.")
        return 2
    return 1 if check and (unaccounted or stale or orphan_modules) else 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args(argv)
    s = survey()
    if args.json:
        print(json.dumps(s, indent=2))
        return 0
    return _report(s, args.check)


if __name__ == "__main__":
    sys.exit(main())
