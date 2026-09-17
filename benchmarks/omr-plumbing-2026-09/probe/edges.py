"""Every CONNECTION in the staged pipeline, declared and measured.

    python3 benchmarks/omr-plumbing-2026-09/probe/edges.py RECORD.json [...]

⚠️ This is a PLUMBING test, not a quality test. It asks whether each declared
producer -> consumer edge ever CARRIED A VALUE, never whether the value was
right. Sean, 2026-09-16: *"I am not yet worried about the quality of what goes
through the plumbing ... I want to make sure everything is connected."*

## The five outcomes, because they are five different repairs

  LIVE            a value crossed this edge in at least one arm
  ASKED_ABSENT    the consumer ASKED and the log had nothing (recorded in
                  `Verdict.missing` -- so the wire is connected and the page
                  was silent, or the producer is dead)
  NEVER_ASKED     the consumer RAN and never once recorded asking. This is the
                  inert declaration, MEASURED rather than inferred from source
  NOT_EXERCISED   the consumer never ran because its SUBJECT population was
                  empty -- this page prints no such ink. The wire is untested,
                  not broken
  CONSUMER_DEAD   the consumer produced no verdict at all, and its subjects
                  WERE there
  PRODUCER_DEAD   the producing quantity has no row in any arm

⚠️⚠️ NEVER_ASKED and ASKED_ABSENT must not be pooled. The first is a wiring
fault -- the code does not read what it declares. The second is the pipeline
working: it asked, and this page had no such ink. Pooling them reports a
correct abstention as a broken wire, which is the ABSENT/DECLINED collapse
`record.py` exists to prevent, arriving in the instrument.

⚠️ DERIVED, never hand-listed. A new INFER rule, a new consequence or a new
decision is picked up with no edit here, because the declared edge set is read
out of `adjudicate.REGISTRY`, `evaluate.RULES` and `infer.RULES` at run time.
"""
from __future__ import annotations

import argparse
import ast
import collections
import importlib
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))

from tools.omr.staged import adjudicate, evaluate, infer  # noqa: E402
from tools.omr.staged.record import Q  # noqa: E402
import tools.omr.staged.adjudicators  # noqa: E402,F401  populates REGISTRY
import tools.omr.staged.consequences  # noqa: E402,F401  populates RULES
import tools.omr.staged.inferences  # noqa: E402,F401


def declared_edges() -> list:
    """(producer_quantity, consumer, stage, kind) -- from the tree."""
    edges = []
    for quantity, spec in adjudicate.REGISTRY.items():
        for want in spec.wants:
            edges.append((want, spec.name, "ADJUDICATE", "wants"))
    for rule in evaluate.RULES:
        name = getattr(rule.consequence, "value", str(rule.consequence))
        edges.append((rule.cause, f"consequence:{name}", "EVALUATE", "cause"))
    for rule in getattr(infer, "RULES", []):
        name = _infer_name(rule)
        for q in getattr(rule, "reads", ()):
            edges.append((q, f"inference:{name}", "INFER", "reads"))
    for q in _export_reads():
        edges.append((q, "export", "EXPORT", "reads"))
    return sorted(set(edges))


def _infer_name(rule) -> str:
    """⚠️ An INFER rule has no `name`; it carries `inference` (the enum) and
    `fn`. Falling back to "?" made every INFER edge unattributable."""
    who = getattr(rule, "inference", None)
    if who is not None:
        return getattr(who, "value", str(who))
    return getattr(getattr(rule, "fn", None), "__name__", "?")


def _export_reads() -> set:
    """Quantities `staged/export.py` reads by name. Derived from its AST."""
    by_attr = {k: v for k, v in vars(Q).items()
               if isinstance(v, str) and not k.startswith("_")}
    path = pathlib.Path(__file__).resolve().parents[3] / "tools/omr/staged/export.py"
    out = set()
    for node in ast.walk(ast.parse(path.read_text())):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr not in ("obs_of", "value", "verdict", "verdicts_of", "obs"):
            continue
        for a in node.args:
            if (isinstance(a, ast.Attribute) and isinstance(a.value, ast.Name)
                    and a.value.id == "Q" and a.attr in by_attr):
                out.add(by_attr[a.attr])
    return out


def measure(paths: list) -> dict:
    """What actually carried, pooled over every arm."""
    carried = collections.defaultdict(set)   # (q, consumer) -> {arm}
    asked_absent = collections.defaultdict(set)
    consumer_ran = collections.defaultdict(set)
    produced = collections.defaultdict(set)
    transitive = collections.defaultdict(set)
    arms = []
    for p in paths:
        arm = pathlib.Path(p).stem
        arms.append(arm)
        d = json.loads(pathlib.Path(p).read_text())
        rec = d.get("record", d)
        q_of = {}
        for o in rec.get("observations", ()):
            q_of[o["id"]] = o["quantity"]
            produced[o["quantity"]].add(arm)
        for v in rec.get("verdicts", ()):
            q_of[v["id"]] = v["quantity"]
        for a in rec.get("abstentions", ()):
            q_of[a.get("id", "")] = a.get("quantity")
        for v in rec.get("verdicts", ()):
            who = v.get("decider") or "?"
            consumer_ran[who].add(arm)
            if v.get("outcome") == "decided":
                produced[v["quantity"]].add(arm)
            # ⚠️⚠️ `considered` ∪ `used` ONLY — NEVER `basis`. A declared
            # `wants` edge is a DIRECT read, and `basis` is the TRANSITIVE
            # closure: on one arm `adjudicate_part_partition` showed
            # `instrument` and `staff_ordinal` in its basis purely because
            # `slot_index`'s own verdict rests on them. Crediting basis
            # reported an indirect ancestry as a direct read and contradicted
            # `inventory --check`, which was right.
            for rid in set(v.get("used") or ()) | set(v.get("considered") or ()):
                q = q_of.get(rid)
                if q:
                    carried[(q, who)].add(arm)
            for rid in set(v.get("basis") or ()):
                q = q_of.get(rid)
                if q:
                    transitive[(q, who)].add(arm)
            for q in (v.get("missing") or ()):
                asked_absent[(q, who)].add(arm)
            for q in (v.get("declined") or ()):
                asked_absent[(q, who)].add(arm)
        # EVALUATE: a consequence that fired read its cause
        ev = d.get("evaluation") or {}
        for entry in (ev.get("fired") or ()):
            name = entry[0] if isinstance(entry, (list, tuple)) else entry
            consumer_ran[f"consequence:{name}"].add(arm)
            for r in evaluate.RULES:
                if getattr(r.consequence, "value", str(r.consequence)) == name:
                    carried[(r.cause, f"consequence:{name}")].add(arm)
        for entry in (ev.get("skipped") or ()):
            name = entry[0] if isinstance(entry, (list, tuple)) else entry
            consumer_ran[f"consequence:{name}"].add(arm)
        # INFER
        inf = d.get("inference") or {}
        for entry in (inf.get("inferred") or ()):
            rule = (entry or {}).get("rule") if isinstance(entry, dict) else None
            if rule:
                consumer_ran[f"inference:{rule}"].add(arm)
        # ⚠️ AN INFER EDGE COULD NEVER BE LIVE UNTIL THIS EXISTED. A firing is
        # the only proof an inference read anything -- the record does not name
        # what a rule consulted -- so a fired rule marks its DECLARED reads as
        # carried, at `strength: inferred`. Without this the four edges of rule
        # 1 reported NEVER_ASKED across 143 arms in which it fired 46 times.
        if (inf.get("inferred") or ()):
            for r in getattr(infer, "RULES", ()):
                for q in getattr(r, "reads", ()):
                    carried[(q, f"inference:{_infer_name(r)}")].add(arm)
        for r in getattr(infer, "RULES", ()):
            if inf:                       # the stage ran at all
                consumer_ran[f"inference:{_infer_name(r)}"].add(arm)
        # EXPORT counters live beside the record
        stem = arm[:-len(".record")] if arm.endswith(".record") else arm
        for cand in sorted(pathlib.Path(p).parent.glob(stem + "*.coverage.json")):
            consumer_ran["export"].add(arm)
            break
    return {"carried": carried, "asked_absent": asked_absent,
            "consumer_ran": consumer_ran, "produced": produced,
            "transitive": transitive, "arms": arms}


#: decider name -> the quantity its subjects come from, for decisions that
#: declare one. A decision with no subject has nothing to decide, and that is
#: the PAGE being silent, not a broken wire.
def _state_only_reads() -> set:
    """(decider, quantity) pairs the record CANNOT witness.

    ⚠️⚠️ `Evidence.state()` calls `_check()` (which enforces the declaration)
    and NOT `_note()` (which records the row) -- so a quantity read only
    through `state()` never enters `Verdict.considered`/`used`/`basis`, and a
    NEVER_ASKED verdict about it is unprovable rather than false.
    """
    by = {k: v for k, v in vars(Q).items()
          if isinstance(v, str) and not k.startswith("_")}
    out = set()
    root = pathlib.Path(__file__).resolve().parents[3] / "tools/omr/staged"
    for path in sorted(root.rglob("*.py")):
        for fn in [n for n in ast.walk(ast.parse(path.read_text()))
                   if isinstance(n, ast.FunctionDef)]:
            via = {}
            for n in ast.walk(fn):
                if (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                        and n.args):
                    a = n.args[0]
                    if (isinstance(a, ast.Attribute)
                            and getattr(a.value, "id", None) == "Q"
                            and a.attr in by):
                        via.setdefault(by[a.attr], set()).add(n.func.attr)
            for q, methods in via.items():
                if methods == {"state"}:
                    out.add((fn.name, q))
    return out


def _subject_sources() -> dict:
    out = {}
    for _, spec in adjudicate.REGISTRY.items():
        src = getattr(spec, "subjects_from", None)
        if src:
            out[spec.name] = src
    return out


def classify(edges: list, m: dict) -> list:
    subj = _subject_sources()
    STATE_ONLY = _state_only_reads()
    out = []
    for q, consumer, stage, kind in edges:
        arms = m["carried"].get((q, consumer), set())
        strength = "proved"
        if arms:
            state = "LIVE"
        elif stage == "EXPORT":
            # ⚠️ WEAKER EVIDENCE, AND SAID SO. A verdict names the row ids it
            # used, so an ADJUDICATE edge is PROVED. The exporter records
            # counters, not reads -- so the most this can say is that the
            # exporter ran and the value was there to read.
            strength = "inferred"
            if not m["consumer_ran"].get("export"):
                state = "CONSUMER_DEAD"
            elif m["produced"].get(q):
                state = "LIVE"
            else:
                state = "PRODUCER_DEAD"
        elif not m["consumer_ran"].get(consumer):
            src = subj.get(consumer)
            state = ("NOT_EXERCISED" if src and not m["produced"].get(src)
                     else "CONSUMER_DEAD")
        elif m["asked_absent"].get((q, consumer)):
            state = "ASKED_ABSENT"
        elif not m["produced"].get(q):
            state = "PRODUCER_DEAD"
        elif m["transitive"].get((q, consumer)):
            # read by nothing directly, but present in the decision's ancestry
            state, strength = "INDIRECT_ONLY", "ancestry"
        elif (consumer, q) in STATE_ONLY:
            state, strength = "READ_UNTRACEABLE", "unprovable"
        else:
            state = "NEVER_ASKED"
        out.append({"producer": q, "consumer": consumer, "stage": stage,
                    "kind": kind, "state": state, "strength": strength,
                    "arms": sorted(arms)})
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("records", nargs="+")
    ap.add_argument("--json")
    args = ap.parse_args(argv)

    edges = declared_edges()
    m = measure(args.records)
    rows = classify(edges, m)

    order = ["LIVE", "ASKED_ABSENT", "NOT_EXERCISED", "READ_UNTRACEABLE",
             "INDIRECT_ONLY", "NEVER_ASKED", "PRODUCER_DEAD", "CONSUMER_DEAD"]
    by_state = collections.Counter(r["state"] for r in rows)
    print("═══ EVERY DECLARED CONNECTION, MEASURED ═══════════════════════════")
    print(f"arms pooled: {len(m['arms'])}  {m['arms']}")
    print(f"declared edges: {len(rows)}\n")
    for st in order:
        group = [r for r in rows if r["state"] == st]
        print(f"── {st}  ({len(group)})")
        if st == "LIVE":
            continue
        for r in group:
            print(f"     {r['producer']:28} → {r['consumer']:42} [{r['stage']}/{r['kind']}]")
    print("\n── SUMMARY")
    for st in order:
        print(f"   {st:16} {by_state.get(st, 0)}")
    print("\n── POSITIVE CONTROLS (a zero means the question did not run)")
    print(f"   consumers that ran        {len(m['consumer_ran'])}")
    print(f"   quantities with a row     {len(m['produced'])}")
    print(f"   edges that carried        {len(m['carried'])}")
    if args.json:
        pathlib.Path(args.json).write_text(json.dumps(
            {"rows": rows, "summary": dict(by_state), "arms": m["arms"]}, indent=2))
    if not m["carried"] or not m["consumer_ran"]:
        print("\n⚠️ POSITIVE CONTROL AT ZERO — the instrument did not run.")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
