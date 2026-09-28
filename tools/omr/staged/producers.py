"""The DECLARED out-of-pipeline producers — a human reader, a review sidecar.

ROADMAP 0.5 / 3.4b-check. `Q.HUMAN_BOX_VERDICT` (and the handful of quantities
beside it that a human's box can carry — `Q.HUMAN_VERDICT_STANCE`,
`Q.GLYPH_BOX`, `Q.NOTEHEAD_CLASS`, `Q.NOTEHEAD_STAFF_POSITION`,
`Q.CLEF_GLYPH`, `Q.CLEF_POSITION`) has NO gather site and never will: a human
is not a gather rung, and a `gather_human_boxes()` reading a review sidecar
would put a review artefact inside the measurement path — the same structural
refusal that keeps a dossier out of it (CLAUDE.md §5b: there is no `--dossier`
and there will not be one). `review/human_evidence.py` files these rows from
outside the pipeline and sits in `reach.NOT_A_STAGE` for exactly that reason.

Before this module, every derived check that asked "who produces this
quantity" only ever looked at `gather.py` (or, for `gather_coverage.py`, at
nothing at all beyond the full `record.Q` vocabulary), so a decision reading a
human witness reported as UNSATISFIABLE — a producer that plainly exists,
reclassified as a hole. `inventory.py` carried nine hand-written `KNOWN_GAPS`
entries explaining exactly that misreading, one per decision, and
`gather_coverage.py` silently counted the same two quantities as
"declared, never gathered" with no explanation at all.

This module is the missing DECLARATION, and it is deliberately thin: the one
fact only a human can state is WHICH MODULE is a producer and WHICH OF ITS
OWN FUNCTIONS file a row — exactly the shape `reach.STAGE_OF_FILE` /
`NOT_A_STAGE` already accept as an unavoidable hand list, guarded by
`reach.unaccounted_modules()`. What is never hand-typed is WHICH QUANTITIES a
declared producer files: `filed()` reads that off the module's own AST, the
same discipline `inventory._gather_sites` applies to `gather.py`, so a hand
list can never drift from the code it claims to describe. `check()` and
`validate()` are the teeth: a declared writer function that does not exist,
or a declared producer that files nothing at all, is a broken declaration and
is reported (or raised) rather than trusted.

⚠️ NEVER A GATHER SITE. Nothing here may be folded into `reach.STAGE_OF_FILE`
or treated as a GATHER producer by `inventory`/`gather_coverage`/`wiring`: a
consumer of `all_filed()` must label what it reports OUT-OF-PIPELINE /
HUMAN, never as if a stage produced it. Sean's `--dossier` ruling is a
structural refusal, not a formatting preference, and this module exists to
make a human witness VISIBLE to the derived checks without ever making it
look like a rung of the pipeline.
"""
from __future__ import annotations

import ast
import importlib
import inspect
import pathlib
from typing import Dict, List, Tuple

_HERE = pathlib.Path(__file__).resolve().parent

#: Modules OUTSIDE the pipeline that file rows onto a staged record, keyed by
#: path relative to this package, each naming the module's OWN row-filing
#: functions. ⚠️ A HAND LIST, unavoidably: deciding WHICH module is an
#: out-of-pipeline producer, and which of ITS functions write a row, is a
#: fact only a human states — the same kind of fact `reach.STAGE_OF_FILE` and
#: `NOT_A_STAGE` already hand-list by filename. What is NOT hand-typed is
#: which QUANTITIES those functions file; see `filed()`. A new out-of-pipeline
#: producer (a second reviewer tool, say) adds one entry here and nothing
#: else — `check()`/`validate()` catch a stale or empty one immediately.
OUT_OF_PIPELINE: Dict[str, Tuple[str, ...]] = {
    "review/human_evidence.py": ("_obs_json", "_abs_json"),
}


def _module_for(rel_path: str):
    """Import the module a producer path names, by dotted path from this
    package — so the signature `_quantity_index` reads is the one the
    pipeline actually runs, not a re-parsed guess."""
    dotted = "tools.omr.staged." + rel_path[:-3].replace("/", ".")
    return importlib.import_module(dotted)


def _quantity_index(fn) -> int:
    """Where the `quantity` parameter sits in `fn`'s OWN signature.

    ⚠️ Read off the function, never hand-counted: `_obs_json` and `_abs_json`
    both happen to take it third today, and a reordered parameter list would
    silently pull the wrong AST argument if that "third" were typed here
    instead of asked of `inspect.signature`.
    """
    params = list(inspect.signature(fn).parameters)
    return params.index("quantity")


def filed(rel_path: str) -> Dict[str, List[str]]:
    """`{quantity: [filing function names]}` a producer's OWN source files,
    read off its AST rather than declared by hand.

    ⚠️ SAME SHAPE AS `inventory._gather_sites`, deliberately: a literal
    `Q.X` argument, in the slot the writer's OWN signature calls `quantity`,
    to one of the writer functions `OUT_OF_PIPELINE` names for this producer.
    Nothing here is a guess — a quantity this function does not find is a
    quantity that module does not file, full stop.
    """
    from .record import Q
    writer_names = OUT_OF_PIPELINE[rel_path]
    mod = _module_for(rel_path)
    idx = {name: _quantity_index(getattr(mod, name))
           for name in writer_names if hasattr(mod, name)}
    path = _HERE / rel_path
    tree = ast.parse(path.read_text())
    out: Dict[str, set] = {}

    class V(ast.NodeVisitor):
        def __init__(self) -> None:
            self.fn: List[str] = []

        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
            self.fn.append(node.name)
            self.generic_visit(node)
            self.fn.pop()

        def visit_Call(self, node: ast.Call) -> None:
            f = node.func
            name = f.id if isinstance(f, ast.Name) else None
            i = idx.get(name)
            if i is not None:
                arg = node.args[i] if i < len(node.args) else next(
                    (kw.value for kw in node.keywords
                     if kw.arg == "quantity"), None)
                if (isinstance(arg, ast.Attribute)
                        and isinstance(arg.value, ast.Name)
                        and arg.value.id == "Q"):
                    # ⚠️ THE VALUE, NOT THE ATTRIBUTE NAME. `Q.HUMAN_BOX_
                    # VERDICT` is the constant `"human_box_verdict"`, and
                    # every consumer of `filed()`/`all_filed()` -- `spec.
                    # wants`, `record.Q` vocabularies -- deals in that VALUE.
                    # Keying this table on the bare attribute spelling would
                    # make every lookup against it silently return nothing.
                    value = getattr(Q, arg.attr, None)
                    if isinstance(value, str):
                        out.setdefault(value, set()).add(
                            self.fn[-1] if self.fn else "<module>")
            self.generic_visit(node)

    V().visit(tree)
    return {k: sorted(v) for k, v in sorted(out.items())}


def all_filed() -> Dict[str, str]:
    """`{quantity: producer path}` over every declared out-of-pipeline
    producer.

    ⚠️ A quantity two DIFFERENT out-of-pipeline producers both claim to file
    is reported rather than silently resolved to whichever ran last — the
    same collision discipline `human_evidence.py`'s own offset-ordinal glyph
    bases exist to prevent one level down (module docstring, `HUMAN_GLYPH_
    BASE`). One producer filing the same quantity as a real GATHER site is a
    different, legitimate case (a human box re-files `Q.GLYPH_BOX`, which
    `gather.py` also files for a detection) and is not this function's
    concern — that is resolved by the CONSUMER treating `all_filed()` as one
    more possible source, not the only one.
    """
    out: Dict[str, str] = {}
    for rel in OUT_OF_PIPELINE:
        for q, sites in filed(rel).items():
            if not sites:
                continue
            if q in out and out[q] != rel:
                raise ValueError(
                    f"{q!r} is filed by BOTH {out[q]!r} and {rel!r} -- two "
                    f"out-of-pipeline producers cannot own one quantity")
            out[q] = rel
    return out


def check() -> List[str]:
    """Non-empty means a declared entry disagrees with the module it names:
    a writer function `OUT_OF_PIPELINE` says exists but does not, or a
    producer entry that, by AST, files NOTHING at all — a dead declaration
    that would otherwise silently stop describing anything."""
    problems: List[str] = []
    for rel, names in OUT_OF_PIPELINE.items():
        try:
            mod = _module_for(rel)
        except Exception as exc:                              # noqa: BLE001
            problems.append(f"{rel}: cannot import ({type(exc).__name__}: "
                           f"{exc})")
            continue
        for name in names:
            if not hasattr(mod, name):
                problems.append(
                    f"{rel}: declared writer {name!r} does not exist in "
                    f"the module")
        if not filed(rel):
            problems.append(
                f"{rel}: declared an out-of-pipeline producer and files "
                f"NOTHING by AST -- a dead entry")
    return problems


def validate() -> None:
    """RAISE if `OUT_OF_PIPELINE` disagrees with the module(s) it names.

    ⚠️ THE CONTROL THAT CAN FAIL (CLAUDE.md rule 7). `check()` is the report
    a human or another derived check reads; this is the same fact enforced
    hard, so a drifted registry cannot pass quietly the way three hand-typed
    decision tables in this repo already have (`inventory.py`'s own
    docstring).
    """
    problems = check()
    if problems:
        raise ValueError(
            "the out-of-pipeline producer registry disagrees with the "
            "module(s) it names:\n  " + "\n  ".join(problems))


def main(argv=None) -> int:                                   # pragma: no cover
    import argparse
    import json as _json
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args(argv)
    if args.check:
        problems = check()
        for p in problems:
            print(f"⚠️ {p}")
        print(f"{len(problems)} problem(s)")
        return 1 if problems else 0
    data = {rel: filed(rel) for rel in OUT_OF_PIPELINE}
    if args.json:
        print(_json.dumps(data, indent=2))
    else:
        for rel, qs in data.items():
            print(f"{rel} (OUT-OF-PIPELINE / human):")
            for q, sites in qs.items():
                print(f"  {q:<28} {', '.join(sites)}")
    return 0


if __name__ == "__main__":                                     # pragma: no cover
    import sys
    sys.exit(main())
