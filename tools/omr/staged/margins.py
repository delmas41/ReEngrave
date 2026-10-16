"""ROADMAP 2.106 step 1 -- every threshold refusal says how close it came.

`docs/plan-2026-10-12-inference-principles.md` §2: a rule that can refuse must
record, beside its answer, (1) what it would have chosen, (2) a SIGNED margin
in the rule's own units, (3) the abstention band it declared. A near miss and a
mile miss otherwise arrive at the consumer as the same word, and a gallery of
"the ten closest calls on each side of a cut" cannot be cut from the record.

## What is stored, and where (and why not `Verdict.candidates`)

* `Verdict.margin` -- signed, in `detail["margin_unit"]`:
  **>= 0: the cut the reached verdict stands on was CLEARED by this much;
  < 0: the rule declined to decide, short of the nearest candidate's cut by
  this much.** Nothing reads `Verdict.margin` on these deciders (they are
  `Mode.ADDITIVE`; the harness only looks at it for `COMPETITIVE`), so filing
  it changes no decision.
* `detail["margin_axis"]` -- WHICH measurement was the tightest one.
* `detail["band"]` -- the declared abstention band as `{axis: [lo, hi]}`, or
  `None` where the cut is a single line with no band declared (that `None` is
  itself the finding: P8 asks for a band and this rule has none).
* `detail["would_choose"]` -- the values the rule would have chosen, best
  first. ⚠️ NOT `Verdict.candidates`. `Verdict.__post_init__` forbids an
  ABSTAINED verdict from carrying candidates (a single survivor is not a
  narrowing), `adjudicate_one` clears them, and a dozen consumers test
  `if v.candidates` to mean "narrowed". Putting a refusal's would-be value
  there would turn a refusal into a narrowing -- a decision change. A rule
  that really NARROWS already files real candidates; this adds the margin to
  it and leaves them alone.

## The check part and what it can see

`check_margins()` is the TREE-level control (`staged.margins` in
`staged.check`): every reason a covered decider declares is classified
`threshold` (must file a margin) or `structural` (an impossibility: it says
why). A reason in neither, a stale entry, and a dead control are findings.
`audit(verdicts)` is the RECORD-level control: it counts the verdicts of a
covered decider whose reason is a threshold one and that carry no margin.
Run it on a record decided before this module existed and it counts them all;
run it on the same record re-decided and it counts zero -- and it is tested in
a state where it FAILS (a margin-less verdict is counted).
"""
from __future__ import annotations

import ast
import dataclasses
import pathlib
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

DERIVED_CHECK = True

THRESHOLD = "threshold"
STRUCTURAL = "structural"


# ─────────────────────────────────────────────────────────────────────────────
# Arithmetic the deciders share
# ─────────────────────────────────────────────────────────────────────────────

def slack(x: Optional[float], lo: Optional[float] = None,
          hi: Optional[float] = None) -> Optional[float]:
    """Signed distance from `x` to the nearer edge of `[lo, hi]`: positive
    inside, negative outside. `None` where `x` is unknown (a missing number
    has no margin; it is not zero)."""
    if x is None:
        return None
    parts = []
    if lo is not None:
        parts.append(x - lo)
    if hi is not None:
        parts.append(hi - x)
    return min(parts) if parts else None


def tightest(items: Iterable[Tuple[str, Optional[float]]]
             ) -> Tuple[Optional[str], Optional[float]]:
    """`(axis, slack)` of the smallest slack; `(None, None)` if none known."""
    known = [(a, s) for a, s in items if s is not None]
    if not known:
        return None, None
    return min(known, key=lambda t: t[1])


def attach(ruling, *, margin: Optional[float], axis: Optional[str],
           unit: str, band: Optional[Mapping[str, Sequence[float]]] = None,
           would_choose: Sequence[Any] = (), **extra: Any):
    """`ruling` with its margin, axis, unit, band and would-be values filed.

    A copy (`Ruling` is frozen); value, reason, candidates and `used` are
    untouched, so the verdict's outcome and value are exactly what they were.
    An existing `ruling.margin` (a COMPETITIVE contest's) is never replaced.
    """
    detail = dict(ruling.detail)
    detail["margin_axis"] = axis
    detail["margin_unit"] = unit
    detail["band"] = ({k: [float(v[0]), float(v[1])] for k, v in band.items()}
                      if band else None)
    detail["would_choose"] = list(would_choose)
    detail.update(extra)
    keep = ruling.margin if ruling.margin is not None else (
        None if margin is None else round(float(margin), 4))
    return dataclasses.replace(ruling, margin=keep, detail=detail)


# ─────────────────────────────────────────────────────────────────────────────
# The registry: which reasons are thresholds, which are structural
# ─────────────────────────────────────────────────────────────────────────────

#: decider name -> {reason: THRESHOLD | STRUCTURAL-with-why}. A STRUCTURAL
#: value is the one-line reason the refusal needs no margin (an impossibility,
#: not a near call). Every reason in the decider's own `reasons` tuple must
#: appear exactly once.
COVERED: Dict[str, Dict[str, str]] = {
    "adjudicate_unboxed_ink_is_a_rest": {
        "rest8th_shape": THRESHOLD, "restQuarter_shape": THRESHOLD,
        "already_read_as_a_glyph": THRESHOLD,
        "stem_stroke_not_a_rest": THRESHOLD,
        "thin_stroke_not_a_rest": THRESHOLD,
        "claimed_by_another_class": THRESHOLD,
        "head_beside_it": THRESHOLD, "shape_cannot_tell": THRESHOLD,
        "in_the_header": "the cluster is left of the header's end or the first "
                         "cell has no header box to measure from: a place, not a cut",
        "no_ink_reading": "GATHER filed no ink measurement: nothing to measure",
        "no_shape_reading": "GATHER filed no shape row: nothing to measure",
    },
    "adjudicate_narrow_box_is_an_eighth_rest": {
        "rest8th_shape": THRESHOLD, "not_rest_shaped": THRESHOLD,
        "shape_cannot_tell": THRESHOLD,
        "claimed_by_another_class": "another class's box stands on the ink, "
                                    "or its own verdict is not decided: a "
                                    "contest with no measured distance",
        "ink_already_read_as_a_glyph": "a standing decided rest/notehead box "
                                       "covers the ink: a fact, not a cut",
        "not_refused_as_too_narrow": "the box was not refused too_narrow: the "
                                     "rule does not apply",
        "no_ink_under_box": "no ink under the box: nothing to measure",
        "no_shape_reading": "GATHER filed no shape row: nothing to measure",
    },
}

#: Verdict-level reasons of a decider that has MANY other reasons covered
#: elsewhere or deliberately not: only the listed ones are classified, the
#: rest of that decider's vocabulary is in `NOT_COVERED` with the reason.
PARTIAL: Dict[str, Dict[str, str]] = {
    "adjudicate_notehead_is_not_a_notehead": {
        "too_narrow": THRESHOLD, "is_a_dot": THRESHOLD,
        "is_a_beam_piece": THRESHOLD,
        # ROADMAP 2.142: share of the smaller box a rest box covers
        "is_a_rest_twin": THRESHOLD,
        # ROADMAP 2.108: past the declared reach of every staff, in staff spaces
        "off_staff_glyph": THRESHOLD,
    },
    "adjudicate_rest_is_not_a_rest": {
        "rest_is_a_barline": THRESHOLD,
    },
    "adjudicate_duration": {
        "hollow_head_bare_stem": THRESHOLD, "head_fill_from_ink": THRESHOLD,
    },
}

#: Deliberately not covered, and why. Read by `check_margins` so an entry here
#: that stops being true (the decider disappears) is a finding, and by the
#: lane report.
NOT_COVERED: Dict[str, str] = {
    "stem-tip flag reader (ROADMAP 2.83, Q.STEM_TIP_INK)": (
        "a GATHER observation reader, not a decider: its cut files an "
        "Observation/Abstention with a `why`, and ROADMAP 2.104 is editing "
        "those readers. Margin there is a reader change, not bookkeeping on "
        "a verdict; revisit when 2.104 lands."),
    "notehead_is_not_a_notehead: every reason but too_narrow, is_a_dot": (
        "most are same-ink / contest / ownership rules whose evidence is "
        "an IoU, a keep-choice or another verdict, not a distance from one "
        "cut; ROADMAP 2.105 is editing this family's logic in parallel."),
    "duration: every reason but the two 2.88 hollow-head ones": (
        "the duration decider has ~40 reasons, most of them arithmetic or "
        "contests; 2.104 edits its flag/tip branches in parallel."),
    "the six INFER rules (inferences.py)": (
        "plan step 1 names them, but their refusals are dissent counts "
        "among witnesses (no distance from a cut) and 2.106 is told to add "
        "FIELDS at threshold sites only; they need a witness-support margin "
        "designed with Sean (plan §3 item), not a number lifted from a cut."),
    "2.99-adjacent: adjudicate_empty_bar_rest_search (rest_search.py)": (
        "its refusals are readings of a bar's ink, not a measured cut; left "
        "for the step-3 near-miss galleries to say which rules need one."),
}


def all_classified() -> Dict[str, Dict[str, str]]:
    return {**COVERED, **PARTIAL}


def threshold_reasons(decider: str) -> frozenset:
    return frozenset(r for r, k in all_classified().get(decider, {}).items()
                     if k == THRESHOLD)


# ─────────────────────────────────────────────────────────────────────────────
# The tree-level control
# ─────────────────────────────────────────────────────────────────────────────

def check_margins() -> Tuple[List[str], List[str]]:
    """`(problems, notes)`. A problem is a finding; a note is information.

    * a covered decider that is not registered, or a classified reason it does
      not declare (STALE);
    * a reason a FULLY covered decider declares that is in neither class
      (UNCLASSIFIED);
    * the audit's own positive control at zero (DEAD).
    """
    from . import adjudicate
    adjudicate._ensure_decisions()
    by_name = {s.name: s for s in adjudicate.REGISTRY.values()}
    problems: List[str] = []
    for decider, table in COVERED.items():
        spec = by_name.get(decider)
        if spec is None:
            problems.append(f"covered decider {decider!r} is not registered")
            continue
        declared = set(spec.reasons) - {adjudicate.ABSTAIN.NOT_IMPLEMENTED}
        for r in sorted(set(table) - declared):
            problems.append(f"{decider}: classified reason {r!r} is not "
                            f"declared (stale)")
        for r in sorted(declared - set(table)):
            problems.append(f"{decider}: declared reason {r!r} is classified "
                            f"neither threshold nor structural")
    for decider, table in PARTIAL.items():
        spec = by_name.get(decider)
        if spec is None:
            problems.append(f"partially covered decider {decider!r} is not "
                            f"registered")
            continue
        for r in sorted(set(table) - set(spec.reasons)):
            problems.append(f"{decider}: classified reason {r!r} is not "
                            f"declared (stale)")
    for decider, reason, line in unmarked_sites():
        problems.append(f"{decider}: a {reason!r} return (line {line}) files "
                        f"no margin")
    # the control: the audit must be able to FAIL
    probe = [{"decider": d, "reason": r, "margin": None, "outcome": "decided"}
             for d, t in all_classified().items()
             for r, k in t.items() if k == THRESHOLD]
    if audit(probe)["without_margin"] != len(probe) or not probe:
        problems.append("the margin audit's positive control found nothing: "
                        "it cannot fail")
    n_thr = sum(len(threshold_reasons(d)) for d in all_classified())
    notes = [f"{n_thr} threshold reasons over {len(all_classified())} "
             f"deciders carry a margin; {len(NOT_COVERED)} families "
             f"deliberately not covered (margins.NOT_COVERED)"]
    return problems, notes


# ─────────────────────────────────────────────────────────────────────────────
# The tree-level count of threshold returns with no margin (an AST read)
# ─────────────────────────────────────────────────────────────────────────────

#: Calls that file a margin around the `Ruling` they wrap.
WRAPPERS = frozenset({"attach", "_margin", "_shape_refusal",
                      "_with_hollow_margin"})

_ADJ_DIR = pathlib.Path(__file__).resolve().parent / "adjudicators"


def _reasons_in(node: ast.AST) -> List[str]:
    """Reason literals of every `Ruling(...)`, `Ruling.abstain(...)` and
    `Ruling.narrow(...)` constructed inside `node`."""
    out: List[str] = []
    for n in ast.walk(node):
        if not isinstance(n, ast.Call):
            continue
        f = n.func
        if isinstance(f, ast.Name) and f.id == "Ruling":
            for kw in n.keywords:
                if kw.arg == "reason" and isinstance(kw.value, ast.Constant):
                    out.append(kw.value.value)
        elif isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name) \
                and f.value.id == "Ruling":
            idx = 0 if f.attr == "abstain" else 1 if f.attr == "narrow" else None
            if idx is not None and len(n.args) > idx \
                    and isinstance(n.args[idx], ast.Constant):
                out.append(n.args[idx].value)
    return out


def _call_name(node: ast.AST) -> Optional[str]:
    if isinstance(node, ast.Call):
        f = node.func
        return f.id if isinstance(f, ast.Name) else (
            f.attr if isinstance(f, ast.Attribute) else None)
    return None


def decider_source(module: str) -> str:
    """Text of `adjudicators/<module>.py` (for a test to mutate)."""
    return (_ADJ_DIR / f"{module}.py").read_text()


def unmarked_sites(sources: Optional[Mapping[str, str]] = None
                   ) -> List[Tuple[str, str, int]]:
    """`(decider, reason, line)` for every `return` in a covered decider's body
    that returns a THRESHOLD reason's `Ruling` without wrapping it in a margin
    call (`WRAPPERS`). `sources` maps a decider-module file name to its text
    (default: the tree), so a test can hand it the pre-change source."""
    from . import adjudicate
    adjudicate._ensure_decisions()
    fn_of = {s.name: s.fn for s in adjudicate.REGISTRY.values()}
    out: List[Tuple[str, str, int]] = []
    for decider in all_classified():
        fn = fn_of.get(decider)
        if fn is None:
            continue
        fname = pathlib.Path(fn.__code__.co_filename).name
        text = (sources or {}).get(fname)
        if text is None:
            text = (_ADJ_DIR / fname).read_text()
        thr = threshold_reasons(decider)
        for node in ast.walk(ast.parse(text)):
            if not (isinstance(node, ast.FunctionDef)
                    and node.name == decider):
                continue
            for r in ast.walk(node):
                if not isinstance(r, ast.Return) or r.value is None:
                    continue
                got = [x for x in _reasons_in(r.value) if x in thr]
                if got and _call_name(r.value) not in WRAPPERS:
                    out.extend((decider, x, r.lineno) for x in got)
    return out


# ─────────────────────────────────────────────────────────────────────────────
# The record-level control
# ─────────────────────────────────────────────────────────────────────────────

def _field(v: Any, name: str) -> Any:
    return v.get(name) if isinstance(v, dict) else getattr(v, name, None)


def audit(verdicts: Iterable[Any]) -> Dict[str, Any]:
    """Count threshold-reason verdicts of covered deciders with and without a
    margin. Takes `Verdict`s or their JSON dicts (a saved record)."""
    thr = {d: threshold_reasons(d) for d in all_classified()}
    with_m = without_m = 0
    missing: Dict[Tuple[str, str], int] = {}
    seen: Dict[Tuple[str, str], int] = {}
    for v in verdicts:
        d, r = _field(v, "decider"), _field(v, "reason")
        if d not in thr or r not in thr[d]:
            continue
        seen[(d, r)] = seen.get((d, r), 0) + 1
        if _field(v, "margin") is None:
            without_m += 1
            missing[(d, r)] = missing.get((d, r), 0) + 1
        else:
            with_m += 1
    return {"threshold_verdicts": with_m + without_m, "with_margin": with_m,
            "without_margin": without_m,
            "by_reason": {f"{d}:{r}": {"n": n, "without_margin":
                                       missing.get((d, r), 0)}
                          for (d, r), n in sorted(seen.items())}}


# ─────────────────────────────────────────────────────────────────────────────
# The no-decision-change proof: re-decide a saved record, compare signatures
# ─────────────────────────────────────────────────────────────────────────────
#
#   python3 -m tools.omr.staged.margins redecide REC.json --out sig.json
#   python3 -m tools.omr.staged.margins compare base.json arm.json
#
# Run `redecide` once in the tree under test and once in a checkout of its
# base (`git archive origin/main tools | tar -x -C DIR`, plus this file copied
# in), one record at a time. A signature is, per verdict in file order,
# `(subject, quantity, decider, outcome, value, reason, candidate values)` --
# everything a consumer can act on and nothing a margin touches.

def signature(verdict: Mapping[str, Any]) -> List[Any]:
    import json
    return [verdict.get("subject"), verdict.get("quantity"),
            verdict.get("decider"), verdict.get("outcome"),
            json.dumps(verdict.get("value"), sort_keys=True, default=str),
            verdict.get("reason"),
            json.dumps([c.get("value") for c in verdict.get("candidates") or ()],
                       sort_keys=True, default=str)]


def redecide(record_path: str, out_path: str) -> Dict[str, Any]:
    import json
    from .review import rerun as RR
    from .record_io import load_record
    doc = load_record(record_path)
    rec = doc["record"] if "record" in doc else doc
    log, _ = RR.rebuild_gather(rec)
    RR.run_stages(log)
    result = RR._to_result(log, doc, None)
    verdicts = result["record"]["verdicts"]
    sigs = [signature(v) for v in verdicts]
    out = {"record": record_path, "n_verdicts": len(verdicts),
           "signatures": sigs,
           "with_margin": sum(1 for v in verdicts if v.get("margin") is not None),
           "audit": audit(verdicts)}
    pathlib.Path(out_path).write_text(json.dumps(out))
    return {k: v for k, v in out.items() if k != "signatures"}


def compare(base_path: str, arm_path: str) -> Dict[str, Any]:
    import json
    a = json.loads(pathlib.Path(base_path).read_text())
    b = json.loads(pathlib.Path(arm_path).read_text())
    sa, sb = a["signatures"], b["signatures"]
    differing = [i for i in range(min(len(sa), len(sb))) if sa[i] != sb[i]]
    return {"n_base": len(sa), "n_arm": len(sb),
            "identical": sa == sb, "n_differing": len(differing),
            "first_differing": [{"base": sa[i], "arm": sb[i]}
                                for i in differing[:5]],
            "margin_base": a.get("with_margin"), "margin_arm": b.get("with_margin"),
            "audit_base": a.get("audit"), "audit_arm": b.get("audit")}


def main(argv: Optional[Sequence[str]] = None) -> int:
    import argparse
    import json
    ap = argparse.ArgumentParser(description="ROADMAP 2.106 margins")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("redecide")
    r.add_argument("record")
    r.add_argument("--out", required=True)
    c = sub.add_parser("compare")
    c.add_argument("base")
    c.add_argument("arm")
    sub.add_parser("audit-tree")
    a = ap.parse_args(argv)
    if a.cmd == "redecide":
        print(json.dumps(redecide(a.record, a.out), indent=1))
        return 0
    if a.cmd == "compare":
        rep = compare(a.base, a.arm)
        print(json.dumps(rep, indent=1))
        return 0 if rep["identical"] else 1
    problems, notes = check_margins()
    print("\n".join(problems + notes))
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
