"""Price a change to `_pair_ties_in_staff` WITHOUT re-transcribing, by REPLAY.

⚠️⚠️ AN EXPORT-ONLY ARM IS STRUCTURALLY BLIND TO THIS CHANGE. The pairing runs
inside `transcribe`, so `reexport_arm.py` would report a clean zero that is the
instrument and not the result — the failure this repo has recorded more than any
other. Re-transcribing costs weights, `library/` and hours, and would fold the
detector's own jitter into the delta.

The escape is that BOTH tie rules are pure functions of the staff dict: the
cell rule reads canonical boxes, the staff rule page boxes, and the ONLY thing
either writes is `tied_to_next` / `tied_from_prev` on notehead dicts. A stored
`.omr.json` carries every input they read. So the whole tie-flag state can be
rebuilt from scratch over a stored transcription, and that rebuild is exactly
what a re-transcribe would have produced for this change.

⚠️ THAT CLAIM IS CHECKED, NOT ASSUMED, AND THE CHECK IS THE POINT.
`--control` strips every tie flag, replays BOTH shipped rules, and requires the
result to be IDENTICAL to the stored file's flags on every notehead. If the
replay cannot reproduce what shipped, no arm built on it may be read. It prints
the number of flags it reproduced, so "identical" cannot mean "both empty".

    python3 .../repair_arm.py --fixtures <dir> [--tag T] --control
    python3 .../repair_arm.py --fixtures <dir> [--tag T] --score
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
from tools.omr.transcribe import _pair_ties_in_staff  # noqa: E402

_FLAGS = ("tied_to_next", "tied_from_prev")

_EXPORT = (
    "import json,pathlib,sys;"
    "sys.path.insert(0, sys.argv[3]);"
    "from tools.omr.export import to_musicxml;"
    "pathlib.Path(sys.argv[2]).write_text("
    "to_musicxml(json.loads(pathlib.Path(sys.argv[1]).read_text())))"
)


def _staves(result):
    for page in result.get("pages", []):
        for sys_ in page.get("systems", []):
            for staff in sys_.get("staves", []):
                yield staff


def strip(result) -> int:
    n = 0
    for staff in _staves(result):
        for m in staff.get("measures", []):
            for det in m.get("detections", []):
                for f in _FLAGS:
                    if det.pop(f, None):
                        n += 1
    return n


def _box(det, key):
    b = det.get(key)
    return b if b and len(b) == 4 else None


def pair_cell(measure, *, window: float) -> None:
    """The shipped within-cell rule, replayed off `bbox` (canonical)."""
    dets = measure.get("detections", [])
    heads = [d for d in dets
             if d.get("category") == "notehead" and _box(d, "bbox")]
    ties = [d for d in dets
            if (d.get("class") or "").lower() == "tie" and _box(d, "bbox")]
    if not ties or len(heads) < 2:
        return
    avg_h = sum(d["bbox"][3] for d in heads) / len(heads)
    y_tol = max(avg_h * 3, 30)
    for tie in ties:
        tx0, ty0, tw, th = tie["bbox"]
        left = right = None
        bl = br = float("inf")
        for d in heads:
            bx, by, bw, bh = d["bbox"]
            xc, yc = bx + bw / 2.0, by + bh / 2.0
            if abs(yc - (ty0 + th / 2.0)) > y_tol:
                continue
            dxl = tx0 - xc
            if 0 <= dxl < bw * window and dxl < bl:
                left, bl = d, dxl
            dxr = xc - (tx0 + tw)
            if 0 <= dxr < bw * window and dxr < br:
                right, br = d, dxr
        if left is not None and right is not None and left is not right:
            left["tied_to_next"] = True
            right["tied_from_prev"] = True


def pair_staff_legacy(staff) -> None:
    """The staff rule AS IT SHIPPED before 2026-09-11: each side by argmin dx.

    ⚠️ The `on` arm calls the REAL `transcribe._pair_ties_in_staff`, so only
    the baseline is restated here — and it is restated because the baseline no
    longer exists in the tree. `--control` is what makes that restatement
    checkable: it must reproduce the stored transcriptions' flags exactly.
    """
    heads, ties = [], []
    for m in staff.get("measures", []):
        for det in m.get("detections", []):
            bp = _box(det, "bbox_page")
            if not bp:
                continue
            if det.get("category") == "notehead":
                heads.append(det)
            elif (det.get("class") or "").lower() == "tie":
                ties.append(bp)
    if not ties or len(heads) < 2:
        return
    avg_h = sum(d["bbox_page"][3] for d in heads) / len(heads)
    y_tol = max(avg_h * 3, 30)
    for tx0, ty0, tw, th in ties:
        tie_yc = ty0 + th / 2.0
        lefts, rights = [], []
        for d in heads:
            bx, by, bw, bh = d["bbox_page"]
            xc, yc = bx + bw / 2.0, by + bh / 2.0
            if abs(yc - tie_yc) > y_tol:
                continue
            dxl = tx0 - xc
            if 0 <= dxl < bw * 3:
                lefts.append((dxl, yc, d))
            dxr = xc - (tx0 + tw)
            if 0 <= dxr < bw * 3:
                rights.append((dxr, yc, d))
        if not lefts or not rights:
            continue
        left = min(lefts, key=lambda t: t[0])[2]
        right = min(rights, key=lambda t: t[0])[2]
        if left is right:
            continue
        left["tied_to_next"] = True
        right["tied_from_prev"] = True


def rebuild(result, *, prefer_same_position: bool) -> None:
    strip(result)
    for staff in _staves(result):
        for m in staff.get("measures", []):
            pair_cell(m, window=2.0)
        if prefer_same_position:
            _pair_ties_in_staff(staff)
        else:
            pair_staff_legacy(staff)


def _flagset(result) -> set:
    out = set()
    for si, staff in enumerate(_staves(result)):
        for mi, m in enumerate(staff.get("measures", [])):
            for di, det in enumerate(m.get("detections", [])):
                for f in _FLAGS:
                    if det.get(f):
                        out.add((si, mi, di, f))
    return out


def _rows(fixtures: pathlib.Path, tag: str | None):
    pattern = f"*.{tag}.omr.json" if tag else "*.omr.json"
    for omr in sorted(fixtures.glob(pattern)):
        stem = omr.name[: -len(f".{tag}.omr.json" if tag else ".omr.json")]
        for truth in (fixtures / f"{stem}.truth.musicxml",
                      fixtures / f"{stem}.musicxml"):
            if truth.is_file():
                yield stem, omr, truth
                break


def _tied(path: pathlib.Path) -> int:
    return len(re.findall(r'<tied[^>]*type="start"',
                          path.read_text(errors="replace")))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fixtures", type=pathlib.Path, required=True)
    ap.add_argument("--tag")
    ap.add_argument("--control", action="store_true")
    ap.add_argument("--score", action="store_true")
    ap.add_argument("--work-dir", type=pathlib.Path,
                    default=ROOT / "benchmarks" / "omr-tie-pairing-2026-09"
                    / "out" / "repair")
    ap.add_argument("--out", type=pathlib.Path)
    args = ap.parse_args()
    rows = list(_rows(args.fixtures, args.tag))
    if not rows:
        sys.stderr.write("FATAL: no fixture pairs — a dead instrument.\n")
        return 2

    if args.control:
        bad = 0
        total = 0
        for stem, omr, _ in rows:
            stored = json.loads(omr.read_text())
            want = _flagset(stored)
            got_doc = copy.deepcopy(stored)
            rebuild(got_doc, prefer_same_position=False)
            got = _flagset(got_doc)
            total += len(want)
            same = want == got
            bad += not same
            print(f"{stem[:44]:46s} stored={len(want):4d} replay={len(got):4d} "
                  f"{'OK' if same else 'MISMATCH'}"
                  f"{'' if same else f'  +{len(got - want)} -{len(want - got)}'}")
        print(f"\nreproduced {total} stored tie flags over {len(rows)} rows; "
              f"{bad} rows MISMATCH")
        if total == 0:
            sys.stderr.write("⚠️ ZERO flags reproduced — 'identical' here "
                             "would mean 'both empty'. A dead control.\n")
            return 2
        return 1 if bad else 0

    if not args.score:
        sys.stderr.write("FATAL: give --control or --score\n")
        return 2

    args.work_dir.mkdir(parents=True, exist_ok=True)
    totals = {"off": 0, "on": 0}
    ties = {"off": 0, "on": 0}
    n_differ = 0
    report = {"fixtures": str(args.fixtures), "tag": args.tag, "rows": []}
    for stem, omr, truth in rows:
        row = {"row_id": stem,
               "transcription_md5": hashlib.md5(omr.read_bytes()).hexdigest()}
        digests = {}
        for arm, prefer in (("off", False), ("on", True)):
            doc = json.loads(omr.read_text())
            rebuild(doc, prefer_same_position=prefer)
            src = args.work_dir / f"{stem}.{arm}.omr.json"
            src.write_text(json.dumps(doc))
            dst = args.work_dir / f"{stem}.{arm}.musicxml"
            subprocess.run([sys.executable, "-c", _EXPORT, str(src), str(dst),
                            str(ROOT)], check=True, env=dict(os.environ))
            res = score_pair(pred=dst, truth=truth)
            totals[arm] += res["omr_ed"]
            t = _tied(dst)
            ties[arm] += t
            digests[arm] = hashlib.md5(dst.read_bytes()).hexdigest()
            row[arm] = {"omr_ed": res["omr_ed"], "omr_ned": res["omr_ned"],
                        "tied_start": t}
        if len(set(digests.values())) > 1:
            n_differ += 1
        report["rows"].append(row)
        print(f"{stem[:36]:38s} off={row['off']['omr_ed']:6d}/{row['off']['tied_start']:3d}"
              f"   on={row['on']['omr_ed']:6d}/{row['on']['tied_start']:3d}"
              f"   ({row['on']['omr_ed'] - row['off']['omr_ed']:+d})")
    report["summed_edits"] = totals
    report["tied_starts"] = ties
    report["files_that_differ"] = n_differ
    print(f"\nsummed edits  off={totals['off']}  on={totals['on']}  "
          f"delta {totals['on'] - totals['off']:+d}")
    print(f"<tied> starts off={ties['off']}  on={ties['on']}")
    print(f"files that DIFFER between arms: {n_differ} of {len(rows)}")
    if n_differ == 0:
        sys.stderr.write("⚠️ ZERO files differ — inert, or the arm could not "
                         "see the change. Do not read the delta.\n")
    if args.out:
        args.out.write_text(json.dumps(report, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
