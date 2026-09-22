"""What the DETECTOR called each box the print adjudicated.

⚠️ THE QUESTION IS WHETHER ANYTHING ON THE RECORD SEPARATES THE TWO REAL
CHORDS FROM THE THIRTEEN NON-NOTEHEADS. If a class name, a confidence or a
width did, the rule could be gated on it; if nothing does, the contamination
is upstream of anything this decision can read and the refusal is structural
rather than a matter of tuning.

⚠️ A CLASS NAME IS THE DETECTOR'S OWN WORD AND IS NOT A SECOND WITNESS to its
own box -- `Evidence.correlated_groups` calls every row from one reader on one
crop ONE SIGNAL. So a separation here would be the detector CONTRADICTING
ITSELF, which is usable, and an absence of separation is the stronger result.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import cell_of, stream_array  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--adjudication", required=True)
    ap.add_argument("--label", default="")
    ap.add_argument("--out", default="")
    a = ap.parse_args()

    man = json.loads(Path(a.manifest).read_text())
    adj = json.loads(Path(a.adjudication).read_text())["verdicts"]
    tiles = [t for t in man["tiles"]
             if t["stratum"] == "CANDIDATE" and t["id"] in adj]
    want = {t["subject"] for t in tiles} | {t["mate"] for t in tiles}

    info = {}
    for o in stream_array(a.record, "observations"):
        if o.get("quantity") != "glyph_box":
            continue
        s = o.get("subject", "")
        if s not in want:
            continue
        v = o.get("value")
        d = o.get("detail") or {}
        info[s] = {"smufl": v[0] if isinstance(v, (list, tuple)) and v else None,
                   "score": d.get("score"), "cell": cell_of(s)}

    by_verdict = defaultdict(Counter)
    conf = defaultdict(list)
    rows = []
    for t in tiles:
        v = adj[t["id"]]["verdict"]
        red, blue = info.get(t["subject"], {}), info.get(t["mate"], {})
        by_verdict[v][red.get("smufl")] += 1
        if red.get("score") is not None:
            conf[v].append(round(float(red["score"]), 3))
        rows.append({"tile": t["id"], "verdict": v,
                     "red_class": red.get("smufl"),
                     "red_score": red.get("score"),
                     "blue_class": blue.get("smufl"),
                     "blue_score": blue.get("score")})

    out = {
        "label": a.label or Path(a.record).name,
        "candidates_adjudicated": len(tiles),
        "RED_class_by_verdict": {k: dict(c) for k, c in by_verdict.items()},
        "RED_detector_score_by_verdict": {
            k: {"n": len(s), "min": min(s), "median": sorted(s)[len(s) // 2],
                "max": max(s)}
            for k, s in conf.items() if s},
        "rows": rows,
    }
    print(json.dumps({k: v for k, v in out.items() if k != "rows"}, indent=2))
    if a.out:
        Path(a.out).write_text(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
