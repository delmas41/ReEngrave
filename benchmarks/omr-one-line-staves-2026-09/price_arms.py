"""Score a pair of exported MusicXML arms against a scan-gate row's truth.

The two arms come from the SAME tree and the same transcription flags apart
from `OMR_ONE_LINE_STAVES`, so the delta is attributable to the flag and to
nothing else. The truth is the committed trimmed truth the 20-row gate itself
scores against.

    python3 price_arms.py --row mahler-sym5-mvt1-local-p5 \
        --off /path/off.musicxml --on /path/on.musicxml
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
MAIN = Path("/Users/seanjohnson/Desktop/ReEngrave")
sys.path.insert(0, str(ROOT))

from tools.omr import omr_ned as omr_ned_mod                       # noqa: E402

REC = (MAIN / ".claude/worktrees/reconciliation/benchmarks"
       "/omr-scan-e2e-2026-09/fixtures")


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", action="append", default=[], metavar="ROW=NAME=XML",
                    help="repeatable; e.g. mahler-...-p5=off=/tmp/off.musicxml")
    ap.add_argument("--truth-dir", default=str(REC))
    ap.add_argument("--truth-suffix", default=".truth.musicxml")
    ap.add_argument("--out", default="price-arms.json")
    args = ap.parse_args(argv)

    pairs, entries = [], []
    for spec in args.arm:
        row, name, xml = spec.split("=", 2)
        truth = Path(args.truth_dir) / f"{row}{args.truth_suffix}"
        pred = Path(xml)
        if not truth.is_file():
            print(f"SKIP {row}: no truth fixture", file=sys.stderr)
            continue
        key = f"{row}|{name}"
        pairs.append((key, pred, truth))
        entries.append({"row_id": row, "arm": name, "pred": str(pred),
                        "sha": {"truth": sha(truth), "pred": sha(pred)}})

    scored = omr_ned_mod.score_batch(pairs, detail="AllObjects")
    by_name = {p["name"]: p for p in scored.get("pairs", [])}
    for e in entries:
        e["score"] = by_name.get(f"{e['row_id']}|{e['arm']}")

    def pool(arm):
        rows_ = [e for e in entries if e["arm"] == arm]
        ed = ts = ps = 0
        cats: dict[str, int] = {}
        for e in rows_:
            n = e["score"]
            ed += n["omr_ed"]
            ts += n["truth_symbols"]
            ps += n["pred_symbols"]
            for k, v in (n.get("categories") or {}).items():
                cats[k] = cats.get(k, 0) + v
        return {"omr_ned": ed / (ts + ps) if (ts + ps) else None,
                "omr_ed": ed, "truth_symbols": ts, "pred_symbols": ps,
                "categories": cats, "n_rows": len(rows_)}

    arms = sorted({e["arm"] for e in entries})
    doc = {
        "generated_by": "benchmarks/omr-one-line-staves-2026-09/price_arms.py",
        "git_head": subprocess.run(
            ["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True).stdout.strip(),
        "pooled": {a: pool(a) for a in arms},
        "rows": entries,
    }
    (HERE / args.out).write_text(json.dumps(doc, indent=1) + "\n")

    print(f"{'row':38} {'arm':6} {'NED':>8} {'edits':>7} {'ES':>6} {'parts':>6}")
    for e in entries:
        n = e["score"]
        es = (n.get("categories") or {}).get("entire staff insert/delete", 0)
        print(f"{e['row_id'][:38]:38} {e['arm']:6} {n['omr_ned']:8.4f} "
              f"{n['omr_ed']:7d} {es:6d} {n['pred_symbols']:6d}")
    for a in arms:
        p = doc["pooled"][a]
        print(f"POOLED {a:10} {p['omr_ned']:.4f}  ed {p['omr_ed']}  "
              f"ES {p['categories'].get('entire staff insert/delete', 0)}")
    print("wrote", HERE / args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
