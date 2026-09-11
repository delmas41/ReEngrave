"""Score an UNFLAGGED export-side change by exporting the SAME `.omr.json`
from TWO TREES, and score both against the same truths.

⚠️ WHY NOT `reexport_arm.py`. That probe switches arms with an ENV VAR, which
is right for a flagged change and impossible for this one: the chord-tie
repair ships without a flag, so the two arms are two working trees. Everything
else is the same contract — the transcribe half is held byte-identical, so the
delta carries no detector jitter, and each row records its transcription md5 so
a later reader can CHECK that rather than trust it.

⚠️ WHAT IT THEREFORE CANNOT SEE: anything upstream of the exporter. Use it for
export-side arms ONLY.

⚠️ IT REFUSES TWO TREES AT THE SAME COMMIT with a clean status, because an arm
silently reused from an identical tree reports "identical" whatever the change
did — the failure `regather_control.py` exists to prevent, one family over. A
DIRTY tree is allowed and is named in the report; an unnameable tree is
refused rather than compared (a fallback must never turn "cannot tell" into
"same" or into "clean").

    python3 benchmarks/omr-chord-tie-2026-09/probe/tree_arm.py \\
        --fixtures <dir> --tag restamp-composed \\
        --arms base=/path/to/main fix=/path/to/worktree \\
        --out out/scan.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from tools.omr.omr_ned import score_pair  # noqa: E402

_TIED = re.compile(r'<tied type="(start|stop)"/>')


def _tree_id(tree: pathlib.Path) -> str:
    """`<sha>[+dirty]`, or refuse. Never a magic string that compares equal.

    ⚠️ Both facts are read together and BOTH must succeed. `git rev-parse`
    succeeding while `git status` fails would leave a commit with dirtiness
    unknown, which a consumer reads as clean — the exact half-named-tree
    conversion CLAUDE.md records.
    """
    stamp = tree / "TREE_ID"
    if not (tree / ".git").exists():
        # An exported tree (`git archive <commit>`) is not a repository and
        # cannot be asked. It must CARRY its identity, written by whatever
        # exported it, or it is refused — never defaulted.
        if not stamp.is_file():
            raise SystemExit(
                f"FATAL: {tree} is neither a git checkout nor carries a "
                "TREE_ID stamp. An unnameable tree is refused, never "
                "compared.")
        text = stamp.read_text().strip()
        if not text:
            raise SystemExit(f"FATAL: empty TREE_ID stamp in {tree}")
        return text

    def _git(*args: str) -> str:
        p = subprocess.run(["git", "-C", str(tree), *args],
                           capture_output=True, text=True)
        if p.returncode != 0:
            raise SystemExit(f"FATAL: cannot name the tree at {tree}: "
                             f"git {' '.join(args)} -> {p.stderr.strip()}")
        return p.stdout
    sha = _git("rev-parse", "HEAD").strip()
    dirty = bool(_git("status", "--porcelain").strip())
    if not sha:
        raise SystemExit(f"FATAL: empty HEAD for {tree}")
    return sha + ("+dirty" if dirty else "")


def _rows(fixtures: pathlib.Path, tag: str) -> list[str]:
    out = []
    suffix = f".{tag}.omr.json" if tag else ".omr.json"
    for p in sorted(fixtures.glob(f"*{suffix}")):
        rid = p.name[: -len(suffix)]
        for truth in (f"{rid}.truth.musicxml", f"{rid}.musicxml"):
            if (fixtures / truth).is_file():
                out.append(rid)
                break
    return out


def _truth(fixtures: pathlib.Path, rid: str) -> pathlib.Path:
    for name in (f"{rid}.truth.musicxml", f"{rid}.musicxml"):
        p = fixtures / name
        if p.is_file():
            return p
    raise SystemExit(f"FATAL: no truth for {rid}")


def _export(tree: pathlib.Path, src: pathlib.Path,
            dst: pathlib.Path) -> None:
    """Export in a SUBPROCESS rooted at that tree, so the arm really is that
    tree's exporter and not this process's already-imported modules."""
    proc = subprocess.run(
        [sys.executable, "-m", "tools.omr.export", str(src),
         "--format", "musicxml", "--out", str(dst)],
        cwd=str(tree), env=dict(os.environ), capture_output=True, text=True)
    if proc.returncode != 0:
        raise SystemExit(f"export failed for {src} in {tree}:\n"
                         f"{proc.stderr[-2000:]}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fixtures", type=pathlib.Path, required=True)
    ap.add_argument("--tag", default="")
    ap.add_argument("--arms", nargs="+", required=True,
                    help="name=/path/to/tree — first arm is the control")
    ap.add_argument("--work-dir", type=pathlib.Path,
                    default=ROOT / "benchmarks/omr-chord-tie-2026-09/out/arms")
    ap.add_argument("--out", type=pathlib.Path, default=None)
    args = ap.parse_args()

    arms = []
    for spec in args.arms:
        name, _, path = spec.partition("=")
        tree = pathlib.Path(path).resolve()
        arms.append((name, tree, _tree_id(tree)))
    ids = [i for _n, _t, i in arms]
    if len(set(ids)) != len(ids):
        raise SystemExit(
            "FATAL: two arms name the SAME tree state "
            f"({ids}). An arm silently reused from an identical tree reports "
            "'identical' whatever the change did.")

    rows = _rows(args.fixtures, args.tag)
    if not rows:
        raise SystemExit(f"FATAL: no rows in {args.fixtures} for tag "
                         f"{args.tag!r}. A missing fixture reads as a zero.")
    args.work_dir.mkdir(parents=True, exist_ok=True)

    report = {"fixtures": str(args.fixtures), "tag": args.tag,
              "n_rows": len(rows),
              "arms": [{"name": n, "tree": str(t), "tree_id": i}
                       for n, t, i in arms],
              "rows": []}
    base = arms[0][0]
    for rid in rows:
        src = args.fixtures / (f"{rid}.{args.tag}.omr.json" if args.tag
                               else f"{rid}.omr.json")
        truth = _truth(args.fixtures, rid)
        entry = {"row_id": rid,
                 "transcription_md5": hashlib.md5(src.read_bytes()).hexdigest()}
        for name, tree, _tid in arms:
            dst = args.work_dir / f"{rid}.{name}.musicxml"
            _export(tree, src, dst)
            res = score_pair(pred=dst, truth=truth, name=f"{rid}.{name}")
            text = dst.read_text()
            kinds = _TIED.findall(text)
            entry[name] = {
                "omr_ned": res["omr_ned"], "omr_ed": res["omr_ed"],
                "categories": res.get("categories", {}),
                "md5": hashlib.md5(text.encode()).hexdigest(),
                "tied_start": kinds.count("start"),
                "tied_stop": kinds.count("stop"),
                "tie_start": text.count('<tie type="start"/>'),
                "notes": text.count("<note>") + text.count("<note "),
            }
        line = f"{rid[:36]:38s}"
        for name, _t, _i in arms:
            d = entry[name]["omr_ed"] - entry[base]["omr_ed"]
            line += (f" {name}={entry[name]['omr_ed']:6d}"
                     + (f"({d:+d})" if name != base else "       "))
        line += ("   tied " + " ".join(
            f"{n}={entry[n]['tied_start']}/{entry[n]['tied_stop']}"
            for n, _t, _i in arms))
        line += "  SAME-FILE" if len({entry[n]["md5"]
                                      for n, _t, _i in arms}) == 1 else ""
        print(line)
        report["rows"].append(entry)

    print("\n⚠️ PER ROW FIRST. A pooled figure over rows this heterogeneous "
          "is context, not a verdict.")
    for name, _t, tid in arms:
        ed = sum(r[name]["omr_ed"] for r in report["rows"])
        ned_num = sum(r[name]["omr_ed"] for r in report["rows"])
        ts = sum(r[name]["tied_start"] for r in report["rows"])
        tp = sum(r[name]["tied_stop"] for r in report["rows"])
        d = ed - sum(r[base]["omr_ed"] for r in report["rows"])
        print(f"  {name:6s} {tid:48s} summed edits {ed:7d}"
              + ("   (control)" if name == base else f"   delta {d:+d}")
              + f"    <tied> {ts} start / {tp} stop")
        del ned_num
    moved = sum(1 for r in report["rows"]
                if len({r[n]["md5"] for n, _t, _i in arms}) > 1)
    print(f"\n  files that DIFFER between arms: {moved} of {len(rows)}   "
          "(a zero here is a dead instrument, not a clean result)")
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
