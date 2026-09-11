"""Price a TRANSCRIBE-side tie change by re-transcribing, two trees, one page.

⚠️⚠️ WHY NOT AN EXPORT-ONLY ARM, AND WHY NOT A REPLAY.
`_pair_ties_in_staff` runs inside `transcribe`, so `reexport_arm.py` and
`tree_arm.py` are STRUCTURALLY BLIND to this change and the clean zero they
would report is the instrument. The cheaper escape — replaying both tie rules
over a stored `.omr.json` — was built (`repair_arm.py`) and its own control
REFUSED it: `_pair_ties_in_cell` runs at `transcribe.py:2289` and
`_dedupe_cross_staff_detections` at `:5557`, so a stored transcription carries
tie flags set against a detection set the FILE NO LONGER HOLDS, and the replay
comes back short on three of eleven engraved rows. See `orphan_flags.py` — that
refusal is a finding in its own right.

So the page is read again, by each tree, in its own subprocess.

⚠️ THE DETECTOR'S OWN JITTER IS THE HAZARD AND IT IS MEASURED, NOT ASSUMED.
This change cannot move a detection, so the two arms' detection sets must be
identical; the arm compares them with the tie flags stripped and REFUSES to
report an edit delta on any row where they are not. A row whose detections
moved is named and excluded rather than folded in.

    python3 .../retranscribe_arm.py --fixtures <dir> \\
        --base <tree> --fix <tree> --out out/retranscribe.json
"""
from __future__ import annotations

import argparse
import copy
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

_FLAGS = ("tied_to_next", "tied_from_prev")

_EXPORT = (
    "import json,pathlib,sys;"
    "sys.path.insert(0, sys.argv[3]);"
    "from tools.omr.export import to_musicxml;"
    "pathlib.Path(sys.argv[2]).write_text("
    "to_musicxml(json.loads(pathlib.Path(sys.argv[1]).read_text())))"
)


def _strip(obj):
    """Just the DETECTIONS, tie flags removed — the control's whole subject.

    ⚠️ Comparing the whole record was tried and is the WRONG question: it also
    catches the weights PATH (the two trees differ by construction), a
    millisecond timing field, and — the one that mattered — which OCR engine
    the direction reader used. The first run of this arm excluded all eleven
    rows because the base tree had no `.venv-surya` beside it, so Surya
    self-disabled there and Tesseract read the words instead. That is
    CLAUDE.md's own documented worktree trap ("makes a --direction-text run
    score without the direction reader while looking like a normal run"),
    arriving inside a control built to catch something else. Both trees now
    carry the symlink, and the comparison asks only what the change could
    possibly move.
    """
    out = []
    for page in obj.get("pages", []):
        for sys_ in page.get("systems", []):
            for staff in sys_.get("staves", []):
                for m in staff.get("measures", []):
                    for det in m.get("detections", []):
                        d = copy.deepcopy(det)
                        for f in _FLAGS:
                            d.pop(f, None)
                        out.append(d)
    return out


def _flagcount(obj) -> tuple[int, int]:
    a = b = 0
    for page in obj.get("pages", []):
        for sys_ in page.get("systems", []):
            for staff in sys_.get("staves", []):
                for m in staff.get("measures", []):
                    for det in m.get("detections", []):
                        a += bool(det.get("tied_to_next"))
                        b += bool(det.get("tied_from_prev"))
    return a, b


def _digest(obj) -> str:
    return hashlib.md5(json.dumps(obj, sort_keys=True).encode()).hexdigest()


def _tied(path: pathlib.Path) -> int:
    return len(re.findall(r'<tied[^>]*type="start"',
                          path.read_text(errors="replace")))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fixtures", type=pathlib.Path, required=True)
    ap.add_argument("--base", type=pathlib.Path, required=True)
    ap.add_argument("--fix", type=pathlib.Path, required=True)
    ap.add_argument("--work-dir", type=pathlib.Path,
                    default=ROOT / "benchmarks" / "omr-tie-pairing-2026-09"
                    / "out" / "retx")
    ap.add_argument("--out", type=pathlib.Path)
    ap.add_argument("--only", nargs="*")
    args = ap.parse_args()
    if args.base.resolve() == args.fix.resolve():
        sys.stderr.write("FATAL: both arms name the SAME tree — an A/B that "
                         "cannot differ reports 'identical' whatever the "
                         "change did.\n")
        return 2
    base_src = (args.base / "tools" / "omr" / "transcribe.py").read_bytes()
    fix_src = (args.fix / "tools" / "omr" / "transcribe.py").read_bytes()
    if base_src == fix_src:
        sys.stderr.write("FATAL: the two trees' `transcribe.py` are "
                         "IDENTICAL. Refusing rather than reporting a zero.\n")
        return 2

    rows = []
    for pdf in sorted(args.fixtures.glob("*.pdf")):
        stem = pdf.name[:-4]
        truth = args.fixtures / f"{stem}.musicxml"
        if truth.is_file() and (not args.only or stem in args.only):
            rows.append((stem, pdf, truth))
    if not rows:
        sys.stderr.write("FATAL: no fixture pairs — a dead instrument.\n")
        return 2
    args.work_dir.mkdir(parents=True, exist_ok=True)

    report = {"base": str(args.base), "fix": str(args.fix), "rows": []}
    totals = {"base": 0, "fix": 0}
    ties = {"base": 0, "fix": 0}
    flags = {"base": [0, 0], "fix": [0, 0]}
    n_differ = n_excluded = 0
    for stem, pdf, truth in rows:
        recs = {}
        for arm, tree in (("base", args.base), ("fix", args.fix)):
            out = args.work_dir / f"{stem}.{arm}.omr.json"
            if not out.is_file():
                env = dict(os.environ)
                env["PYTHONPATH"] = str(tree)
                subprocess.run(
                    [sys.executable, "-m", "tools.omr.transcribe", str(pdf),
                     "--out", str(out)],
                    cwd=str(tree), check=True, env=env,
                    stdout=subprocess.DEVNULL)
            recs[arm] = json.loads(out.read_text())
        same_dets = _digest(_strip(recs["base"])) == _digest(_strip(recs["fix"]))
        row = {"row_id": stem, "detections_identical": same_dets}
        for arm in ("base", "fix"):
            a, b = _flagcount(recs[arm])
            flags[arm][0] += a
            flags[arm][1] += b
            src = args.work_dir / f"{stem}.{arm}.omr.json"
            dst = args.work_dir / f"{stem}.{arm}.musicxml"
            subprocess.run([sys.executable, "-c", _EXPORT, str(src), str(dst),
                            str(ROOT)], check=True)
            res = score_pair(pred=dst, truth=truth)
            t = _tied(dst)
            row[arm] = {"omr_ed": res["omr_ed"], "omr_ned": res["omr_ned"],
                        "tied_start": t, "tie_flags": [a, b]}
            if same_dets:
                totals[arm] += res["omr_ed"]
                ties[arm] += t
        if not same_dets:
            n_excluded += 1
        elif row["base"]["omr_ed"] != row["fix"]["omr_ed"]:
            n_differ += 1
        report["rows"].append(row)
        mark = "" if same_dets else "   EXCLUDED: detections moved"
        print(f"{stem[:28]:30s} base={row['base']['omr_ed']:5d}/"
              f"{row['base']['tied_start']:3d}  fix={row['fix']['omr_ed']:5d}/"
              f"{row['fix']['tied_start']:3d}  "
              f"({row['fix']['omr_ed'] - row['base']['omr_ed']:+d}){mark}")
    report["summed_edits_comparable_rows"] = totals
    report["tied_starts_comparable_rows"] = ties
    report["tie_flags"] = flags
    report["rows_excluded_detections_moved"] = n_excluded
    print(f"\ncomparable rows: {len(rows) - n_excluded} of {len(rows)}"
          f"   (excluded because detections moved: {n_excluded})")
    print(f"summed edits  base={totals['base']}  fix={totals['fix']}  "
          f"delta {totals['fix'] - totals['base']:+d}")
    print(f"<tied> starts base={ties['base']}  fix={ties['fix']}")
    print(f"tie FLAGS     base={flags['base']}  fix={flags['fix']}")
    print(f"rows whose edit count MOVED: {n_differ}")
    if args.out:
        args.out.write_text(json.dumps(report, indent=1))
    if n_differ == 0:
        sys.stderr.write("⚠️ NO row moved. Inert, or unreached — check the "
                         "reach probes before reading this as a result.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
