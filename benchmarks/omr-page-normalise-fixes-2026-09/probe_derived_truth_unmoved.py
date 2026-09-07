"""Does the fix change the derived truth of any row that already had one?

The strongest available control, and the cheapest: a score can only move if the
FILE it is scored against moved, so compare the artefacts rather than the
numbers. The pre-fix module is loaded straight out of git — no stash, no
branch switch, both revisions live in one process — and both write a
page-normalised truth for every row that carries a hand map today.

⚠️ IDENTICAL BYTES IS A STRONGER STATEMENT THAN IDENTICAL EDITS. musicdiff has
a measured noise floor of roughly ±6 edits on this gate, so "the numbers did
not move" is a weak claim on a single arm; "the file did not move" has no noise
floor at all. Where the two revisions disagree, the fault is named.

⚠️ AND RAW BYTES ARE NOT AVAILABLE, WHICH THE SELF-CONTROL IS HERE TO PROVE.
music21's MusicXML writer mints a FRESH RANDOM `<score-instrument id="I…">` on
every write, so two writes of one score by one module differ on 92 lines of
Dvořák p5 — all of them ids. Comparing raw bytes therefore reports every row as
MOVED and would have been read as a catastrophic regression. Those ids are
canonicalised away (`_canonical`), and the SELF arm — the fixed module writing
the same row twice — must come back identical before the cross arm means
anything. The `<encoding-date>` stamp is date-only and every write happens in
one run, so it cannot manufacture a difference either.

    python3 benchmarks/omr-page-normalise-fixes-2026-09/probe_derived_truth_unmoved.py
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SCAN = ROOT / "benchmarks" / "omr-scan-e2e-2026-09"
sys.path.insert(0, str(SCAN))
sys.path.insert(0, str(ROOT / "benchmarks" / "omr-staves-map-completion-2026-09"))

import page_normalise as fixed                          # noqa: E402
import candidate_maps                                   # noqa: E402

MAIN = Path("/Users/seanjohnson/Desktop/ReEngrave")
REC = (MAIN / ".claude/worktrees/reconciliation/benchmarks"
       "/omr-scan-e2e-2026-09/fixtures")
#: ⚠️ THE BRANCH POINT, NAMED EXPLICITLY, NOT "HEAD". Once the fix is
#: committed HEAD carries it, and comparing HEAD against the working tree would
#: compare the fix with itself and report a clean PASS having tested nothing.
BASE_REV = "687d1c4e"      # the last commit before the fix


def load_old(tmp: Path):
    """The pre-fix module, out of git, as its own importable module."""
    src = subprocess.run(
        ["git", "-C", str(ROOT), "show",
         f"{BASE_REV}:benchmarks/omr-scan-e2e-2026-09/page_normalise.py"],
        capture_output=True, text=True, check=True).stdout
    path = tmp / "page_normalise_old.py"
    path.write_text(src)
    spec = importlib.util.spec_from_file_location("page_normalise_old", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["page_normalise_old"] = mod
    spec.loader.exec_module(mod)
    return mod


def hand_maps() -> list[tuple[str, list, str]]:
    doc = json.loads((SCAN / "works.json").read_text())
    by_id = {r["row_id"]: r for r in doc["rows"]}
    out = []
    for rid, row in by_id.items():
        v = row.get("staves")
        if isinstance(v, str) and v.startswith("same-as:"):
            v = by_id[v.split(":", 1)[1]]["staves"]
        if isinstance(v, list) and v:
            out.append((rid, v, "works.json hand map"))
    for rid in candidate_maps.CANDIDATES:
        out.append((rid, candidate_maps.flat(rid), "candidate map"))
    return out


#: the writer's own randomness — a fresh 32-hex instrument id per write.
_RANDOM_ID = re.compile(r'"I[0-9a-f]{32}"')


def _canonical(p: Path) -> str:
    return _RANDOM_ID.sub('"I#"', p.read_text())


def sha(p: Path) -> str:
    return hashlib.sha256(_canonical(p).encode()).hexdigest()


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="page-normalise-bytes-"))
    old = load_old(tmp)
    rows, moved, newly_possible, self_broken = [], [], [], []
    for rid, smap, kind in hand_maps():
        truth = REC / f"{rid}.truth.musicxml"
        if not truth.is_file():
            continue
        rec = {"row_id": rid, "map_kind": kind}
        for label, mod in (("pre_fix", old), ("fixed", fixed),
                           ("fixed_again", fixed)):   # SELF-control
            out = tmp / f"{rid}.{label}.musicxml"
            try:
                mod.write(truth, smap, out)
                rec[label] = sha(out)
            except Exception as exc:                      # noqa: BLE001
                rec[label] = f"RAISED {type(exc).__name__}: {exc}"
        rec["writer_is_deterministic"] = (rec["fixed"] == rec["fixed_again"])
        if not rec["writer_is_deterministic"]:
            self_broken.append(rid)
        rec["identical"] = (rec["pre_fix"] == rec["fixed"])
        if str(rec["pre_fix"]).startswith("RAISED"):
            newly_possible.append(rid)
        elif not rec["identical"]:
            moved.append(rid)
        rows.append(rec)
        mark = ("NEWLY POSSIBLE" if rid in newly_possible
                else ("identical" if rec["identical"] else "MOVED"))
        print(f"  {mark:15s} {rid:34s} {kind}")

    doc = {
        "generated_by": "benchmarks/omr-page-normalise-fixes-2026-09/"
                        "probe_derived_truth_unmoved.py",
        "base_rev": subprocess.run(["git", "-C", str(ROOT), "rev-parse",
                                    "--short", BASE_REV], capture_output=True,
                                   text=True).stdout.strip(),
        "fixed_transform_version": fixed.TRANSFORM_VERSION,
        "rows_whose_derived_truth_moved": moved,
        "rows_the_fix_makes_possible_at_all": newly_possible,
        "self_control_rows_the_writer_was_not_deterministic_on": self_broken,
        "verdict": "PASS" if not (moved or self_broken) else "FAIL",
        "rows": rows,
    }
    (HERE / "derived-truth-bytes.json").write_text(
        json.dumps(doc, indent=1, ensure_ascii=False) + "\n")
    print()
    print(f"moved: {moved or 'nothing'}")
    print(f"newly possible: {newly_possible or 'nothing'}")
    print(f"self-control failures: {self_broken or 'none'}")
    print(doc["verdict"])
    return 0 if not (moved or self_broken) else 1


if __name__ == "__main__":
    raise SystemExit(main())
