"""One number: how many open findings do this repo's derived checks report?

    python3 -m tools.omr.staged.check              # the table
    python3 -m tools.omr.staged.check --json
    python3 -m tools.omr.staged.check --write       # benchmarks/acceptance/open-findings.json
    python3 -m tools.omr.staged.check --write --force   # write on a dirty tree anyway

Eleven derived self-checks already exist (`inventory`, `health`, `wiring`,
`gather_coverage`, `capture`, `reach`, `brakes`, `trace`, `conventions`,
`no_producer`, `export_coverage`, `accuracy_record`), and every one exits 0
today while printing findings that sit on its own `KNOWN_GAPS`-shaped list.
**They exit 0 because every finding is EXPLAINED, not because there is
nothing left to wire.** `docs/plan-2026-09-22-from-here-to-a-finished-
score.md` §3 item 2 / §5 Phase 0.4b asks for one command folding them into a
single number the roadmap can watch fall, plus two informational counts
(source-text tests, live mutation batteries) the same phase asks to retire.

**"Open" here is every finding the underlying tool reports, INCLUDING the
ones it already explains.** A finding leaves this count when it is wired,
not when it is written down -- the plan's own words: "The number must go
down."

Three exit states, not two, because a check that CANNOT RUN must never read
as a check that ran clean -- most of the checks below already refuse to
trust their own zero for exactly that reason (a "positive control" at zero):

    exit 2  BROKEN  a check raised an exception, or reports an internal
                    contradiction (an "unaccounted"/"stale" list non-empty,
                    or one of its own positive controls at zero)
    exit 1  OPEN    every check ran; the open-findings total is > 0
    exit 0  CLEAN   every check ran; the total is 0

Each check is read in-process from the module's own `build()` / `report()` /
`survey()` / `check()` function, not shelled out to and text-parsed --
`gather_coverage` has no `--check` flag at all, so it is called the same way
as the rest. Nothing here needs to fall back to parsing printed text today.

⚠️ **A NEW `.py` UNDER `tools/omr/staged/` MUST BE REGISTERED WITH
`reach.py` (`reach.NOT_A_STAGE`), AND THIS ONE IS** -- that module's own
comments call the registration "not optional": an unregistered file makes
`reach --check` report an "unregistered module" finding about this file's
existence, not its content. `DERIVED_CHECK = True` below is the other half
of the same convention (`capture.py`, `brakes.py`, `trace.py`, `meaning.py`
all carry it): this module names other modules' findings in order to COUNT
them and reads none of them at run time, so `wiring --check`'s DETAIL
question must not read a mention here as a consumer.
"""
from __future__ import annotations

import argparse
import ast
import datetime as _dt
import fnmatch
import json
import pathlib
import subprocess
import sys
from dataclasses import dataclass
from typing import Callable, List, Optional

DERIVED_CHECK = True

_HERE = pathlib.Path(__file__).resolve().parent      # tools/omr/staged
_ROOT = _HERE.parents[2]                             # staged -> omr -> tools -> root
_TESTS_DIR = _HERE.parent / "tests"                  # tools/omr/tests


@dataclass
class CheckResult:
    name: str
    open: int = 0
    broken: bool = False
    error: Optional[str] = None
    note: Optional[str] = None


def _safe(name: str, fn: Callable[[], "CheckResult"]) -> CheckResult:
    """Run one check, and never let it crash the whole roll-up.

    A crash IS a finding here -- the exit-state table above treats it the
    same as an internal contradiction (BROKEN), because a check that cannot
    even run has told us less than nothing about whether it is clean.
    """
    try:
        result = fn()
    except Exception as exc:                             # noqa: BLE001
        return CheckResult(name=name, open=0, broken=True,
                            error=f"{type(exc).__name__}: {exc}")
    result.name = name
    return result


# ─────────────────────────────────────────────────────────────────────────────
# The eleven derived checks
# ─────────────────────────────────────────────────────────────────────────────

def _check_inventory() -> CheckResult:
    from . import inventory as I
    inv = I.build()
    probs = inv["problems"]
    broken = bool(I.unaccounted(probs)) or bool(I.stale_gaps(probs))
    return CheckResult("staged.inventory", open=len(probs), broken=broken)


def _check_health() -> CheckResult:
    from . import health as H
    h = H.build()                                        # no --run: no fixture needed
    return CheckResult("staged.health", open=len(h["problems"]))


def _check_wiring() -> CheckResult:
    from . import wiring as W
    rep = W.report()
    dead = [k for k, v in rep["controls"].items() if not v]
    broken = bool(dead) or bool(rep["unaccounted"]) or bool(rep["stale_gaps"])
    return CheckResult("staged.wiring", open=len(rep["problems"]), broken=broken,
                        note=f"dead controls: {dead}" if dead else None)


def _check_gather_coverage() -> CheckResult:
    from . import gather_coverage as GC
    rep = GC.report()
    c = rep["counts"]
    # `gather_coverage` has no `--check`; its own `main()` treats
    # `unaccounted` and `class_space.unmapped` as the failing conditions and
    # `declared_ungathered` + `no_vocabulary` as the open, explained gaps.
    open_n = c["declared_ungathered"] + c["no_vocabulary"]
    broken = bool(c["unaccounted"]) or bool(rep["class_space"]["unmapped"])
    return CheckResult("staged.gather_coverage", open=open_n, broken=broken)


def _check_capture() -> CheckResult:
    from . import capture as C
    rep = C.report()
    dead = [k for k, v in rep["controls"].items() if not v]
    broken = bool(dead) or bool(rep["unaccounted"]) or bool(rep["stale_gaps"])
    return CheckResult("staged.capture", open=len(rep["problems"]), broken=broken,
                        note=f"dead controls: {dead}" if dead else None)


def _check_reach() -> CheckResult:
    from . import reach as R
    s = R.survey()
    bad = [r for r in s["rows"] if r["state"] != "LIVE"]
    unaccounted = [r["quantity"] for r in bad if r["quantity"] not in R.KNOWN_GAPS]
    reported = {r["quantity"] for r in bad}
    stale = [q for q in R.KNOWN_GAPS if q not in reported]
    orphan = R.unaccounted_modules()
    c = s["controls"]
    dead = c["with_a_reader"] == 0 or c["quantity_stage_read_pairs"] == 0
    broken = dead or bool(unaccounted) or bool(stale) or bool(orphan)
    note = f"unregistered modules: {orphan}" if orphan else None
    return CheckResult("staged.reach", open=len(bad), broken=broken, note=note)


def _check_brakes() -> CheckResult:
    from . import brakes as B
    bad, lines = B.check()
    return CheckResult("staged.brakes", open=len(lines), broken=bool(bad))


def _check_trace() -> CheckResult:
    from . import trace as T
    rep = T.report()
    dead = [k for k, v in rep["controls"].items() if not v]
    broken = bool(dead) or bool(rep["unaccounted"]) or bool(rep["stale_gaps"])
    return CheckResult("staged.trace", open=len(rep["problems"]), broken=broken)


def _check_conventions() -> CheckResult:
    from .. import conventions as CV
    reg = CV.load()
    dead = [k for k, v in reg.reach().items() if v == 0]
    return CheckResult("conventions", open=len(reg.problems()), broken=bool(dead))


def _check_no_producer() -> CheckResult:
    from .. import no_producer as NP
    report = NP.scan([_ROOT / "tools"])
    # `RECORDED` is this tool's own `KNOWN_GAPS`; every finding is OPEN
    # whether recorded or not (recorded means explained, not fixed). BROKEN
    # is the mirror -- a stale `RECORDED` entry whose finding no longer
    # fires. `RECORDED` is empty as of 2026-09-21, so `stale` is vacuously
    # empty today; kept real for the day an entry is recorded instead of fixed.
    idents = {f.ident for f in report.findings}
    stale = [ident for ident in NP.RECORDED if ident not in idents]
    return CheckResult("no_producer", open=len(report.findings), broken=bool(stale),
                        note=f"stale RECORDED entries: {stale}" if stale else None)


def _check_export_coverage() -> CheckResult:
    from .. import export_coverage as EC
    s = EC.survey()
    if not s.runs:
        return CheckResult("export_coverage", open=0,
                            note="no fixtures on disk -- run "
                                 "`orchestral_eval` first; this check has "
                                 "nothing to compare and reports a clean 0, "
                                 "not a broken run")
    broken = bool(s.incomplete) or bool(s.disagreement) or bool(s.unexplained)
    return CheckResult("export_coverage", open=len(s.gaps), broken=broken)


def _check_accuracy_record() -> CheckResult:
    from .. import accuracy_record as AR
    probs = AR.check()
    return CheckResult("accuracy_record", open=len(probs))


# ─────────────────────────────────────────────────────────────────────────────
# The two informational sub-checks (plan §3 item 2 / §5 Phase 0.4d, 0.4e)
# ─────────────────────────────────────────────────────────────────────────────

#: Exact filenames a source-text test is never counted against, because the
#: repo has already decided those two ARE the mechanism (the derived
#: flag-direction guard and the flag/docs cross-check), not a hazard of one.
_SOURCE_TEXT_ALLOWLIST = {
    "test_flag_default_direction.py",
    "test_flag_docs_match_predicates.py",
}


def _reads_source_text(path: pathlib.Path) -> bool:
    """Does this test call `inspect.getsource`, `ast.parse`/`ast.walk`, or
    read a `.py` path's text?

    Read from the AST, the way this repo's own derived checks read
    everything else, rather than by a `.py` substring anywhere in the file --
    a bare substring match over-counts wildly here, because plenty of tests
    build dicts keyed on filenames like `"test_x.py"` as fixture DATA and
    never open a file at all. The `.read_text()` / `open()` branch below asks
    for the `.py` literal specifically in the argument being read, not
    anywhere in the file.
    """
    try:
        tree = ast.parse(path.read_text())
    except (OSError, SyntaxError, UnicodeDecodeError):        # noqa: BLE001
        return False
    for node in ast.walk(tree):
        if (isinstance(node, ast.Attribute)
                and node.attr in ("getsource", "getsourcelines")
                and isinstance(node.value, ast.Name)
                and node.value.id == "inspect"):
            return True
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if (node.func.attr in ("parse", "walk")
                    and isinstance(node.func.value, ast.Name)
                    and node.func.value.id == "ast"):
                return True
            if node.func.attr == "read_text":
                try:
                    receiver = ast.unparse(node.func.value)
                except Exception:                             # noqa: BLE001
                    receiver = ""
                if ".py" in receiver:
                    return True
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id == "open" and node.args):
            try:
                arg0 = ast.unparse(node.args[0])
            except Exception:                                 # noqa: BLE001
                arg0 = ""
            if ".py" in arg0:
                return True
    return False


def _check_source_text_tests() -> CheckResult:
    if not _TESTS_DIR.is_dir():
        return CheckResult("source_text_tests", open=0,
                            broken=True, error=f"no such dir: {_TESTS_DIR}")
    hits = []
    for path in sorted(_TESTS_DIR.glob("*.py")):
        if path.name in _SOURCE_TEXT_ALLOWLIST or "gather_shape" in path.name:
            continue
        if _reads_source_text(path):
            hits.append(path.name)
    return CheckResult("source_text_tests", open=len(hits),
                        note=f"{len(hits)} of "
                             f"{len(list(_TESTS_DIR.glob('test_*.py')))} test "
                             f"files under tools/omr/tests/ (allowlist: "
                             f"{sorted(_SOURCE_TEXT_ALLOWLIST)})")


def _check_mutation_batteries() -> CheckResult:
    root = _ROOT / "benchmarks"
    if not root.is_dir():
        return CheckResult("mutation_batteries_live", open=0)
    files = []
    for path in root.rglob("*.py"):
        if "_archive" in path.parts:
            continue
        name = path.name.lower()
        if fnmatch.fnmatch(name, "mutate*.py") or fnmatch.fnmatch(name, "*battery*.py"):
            files.append(str(path.relative_to(_ROOT)))
    return CheckResult("mutation_batteries_live", open=len(files))


# ─────────────────────────────────────────────────────────────────────────────
# The roll-up
# ─────────────────────────────────────────────────────────────────────────────

CHECKS: List[tuple] = [
    ("staged.inventory", _check_inventory),
    ("staged.health", _check_health),
    ("staged.wiring", _check_wiring),
    ("staged.gather_coverage", _check_gather_coverage),
    ("staged.capture", _check_capture),
    ("staged.reach", _check_reach),
    ("staged.brakes", _check_brakes),
    ("staged.trace", _check_trace),
    ("conventions", _check_conventions),
    ("no_producer", _check_no_producer),
    ("export_coverage", _check_export_coverage),
    ("accuracy_record", _check_accuracy_record),
    ("source_text_tests", _check_source_text_tests),
    ("mutation_batteries_live", _check_mutation_batteries),
]


def run_all(checks: Optional[List[tuple]] = None) -> List[CheckResult]:
    return [_safe(name, fn) for name, fn in (checks or CHECKS)]


def total_open(results: List[CheckResult]) -> int:
    return sum(r.open for r in results)


def any_broken(results: List[CheckResult]) -> bool:
    return any(r.broken or r.error for r in results)


def exit_code(results: List[CheckResult]) -> int:
    if any_broken(results):
        return 2
    return 1 if total_open(results) > 0 else 0


def render(results: List[CheckResult]) -> str:
    lines = []
    width = max((len(r.name) for r in results), default=8)
    for r in results:
        status = "broken" if (r.broken or r.error) else "ok"
        extra = ""
        if r.error:
            extra = f"  ERROR: {r.error}"
        elif r.note:
            extra = f"  ({r.note})"
        lines.append(f"{r.name:<{width}}  open={r.open:<4}  status={status}{extra}")
    lines.append(f"{'TOTAL':<{width}}  open={total_open(results):<4}  "
                 f"status={'broken' if any_broken(results) else 'ok'}")
    return "\n".join(lines)


def as_json(results: List[CheckResult]) -> dict:
    return {
        "checks": {
            r.name: {"open": r.open, "broken": bool(r.broken or r.error),
                      "error": r.error, "note": r.note}
            for r in results
        },
        "total": total_open(results),
        "broken": any_broken(results),
    }


def _git(args: List[str]) -> str:
    proc = subprocess.run(["git", *args], cwd=str(_ROOT),
                           capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {proc.stderr.strip()}")
    return proc.stdout.strip()


def write_report(results: List[CheckResult], force: bool = False,
                  out_dir: Optional[pathlib.Path] = None) -> pathlib.Path:
    """Write `benchmarks/acceptance/open-findings.json`, tree-stamped.

    Refuses on a dirty tree unless `force=True` -- a number this is meant to
    watch fall over time must name the commit it was true of, or a later
    reader cannot tell whether it moved because of a landed change or because
    the tree was mid-edit when it was taken.

    `out_dir` defaults to `benchmarks/acceptance/` and exists as a parameter
    only so a test can point it at a temporary directory instead.
    """
    head = _git(["rev-parse", "HEAD"])
    status = _git(["status", "--porcelain"])
    dirty = bool(status)
    if dirty and not force:
        raise RuntimeError(
            "refusing to write open-findings.json on a DIRTY tree "
            "(uncommitted changes present); commit first, or pass "
            "force=True / --force to write anyway and record dirty=true.\n"
            f"`git status --porcelain`:\n{status}")
    out_dir = out_dir if out_dir is not None else (_ROOT / "benchmarks" / "acceptance")
    out_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "tree": head,
        "dirty": dirty,
        "date": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        **as_json(results),
    }
    path = out_dir / "open-findings.json"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return path


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else None)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--write", action="store_true",
                    help="write benchmarks/acceptance/open-findings.json")
    ap.add_argument("--force", action="store_true",
                    help="write --write's file even on a dirty tree")
    args = ap.parse_args(argv)

    results = run_all()

    if args.write:
        try:
            path = write_report(results, force=args.force)
        except RuntimeError as exc:
            print(f"REFUSED: {exc}", file=sys.stderr)
            return 2
        print(f"wrote {path.relative_to(_ROOT)}", file=sys.stderr)

    if args.json:
        print(json.dumps(as_json(results), indent=2, sort_keys=True))
    else:
        print(render(results))

    return exit_code(results)


if __name__ == "__main__":
    raise SystemExit(main())
