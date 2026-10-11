#!/usr/bin/env python3
"""l283_rescore: Sean's 14 blind answers on `out/print/2.83-review/` (his recorded `answers.json`) scored against the standing ADJUDICATE duration verdict
of the same heads in each given re-gather SET (a directory `set-TAG/` written by `run_set.sh`: `quick-b/` pdf 0-1, `brahms-tiles.record.json`,
`quick-l/`, `litolff-t.record.json`). Per head, per set: the verdict (decided / narrowed, reason) and whether Sean's printed value is the decided value
(RIGHT), inside the narrowing (NARROWED, answer inside), or not (WRONG: decided another value, or narrowed without it). ROADMAP 2.83 fix round.

    python3 l283_rescore.py --tiles out/print/2.83-review --set base=DIR --set v5=DIR --set fix=DIR [--json out.json]

Sean's answers: 8 = an eighth (0.5), 4 = a quarter (1.0), Dot 4 = a dotted quarter (1.5), Dot 2 = a dotted half (3.0). Written beats (`written`, dots
included) are compared, so a tuplet ratio never enters.
"""
import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from tools.omr.staged import readout as RD  # noqa: E402
from tools.omr.staged.record import Q  # noqa: E402

VALUE = {"8": 0.5, "4": 1.0, "Dot 4": 1.5, "Dot 2": 3.0, "2": 2.0, "Dot 8": 0.75}


def record_paths(d, movement):
    d = Path(d)
    if movement == "brahms":
        return [d / "quick-b/out/brahms1-breitkopf/brahms1-breitkopf-p1.record.json", d / "brahms-tiles.record.json"]
    return [d / "quick-l/out/beethoven5-litolff/beethoven5-litolff-p3.record.json", d / "litolff-t.record.json"]


def verdict_of(run, key):
    if key not in run.glyphs:
        return None
    du = run.standing(key, Q.DURATION, "ADJUDICATE")
    if du is None:
        return None
    return du


def candidate_writtens(du):
    out = []
    for c in du.get("candidates") or []:
        v = c.get("value") if isinstance(c, dict) else None
        if isinstance(v, dict) and v.get("written") is not None:
            out.append(float(v["written"]))
    return out


def score(du, want):
    if du is None:
        return "ABSENT", "no verdict"
    if du["outcome"] == "decided":
        w = (du.get("value") or {}).get("written")
        ok = w is not None and abs(float(w) - want) < 1e-6
        return ("RIGHT" if ok else "WRONG"), f"decided {du.get('reason')} written {w}"
    if du["outcome"] == "narrowed":
        ws = candidate_writtens(du)
        inside = any(abs(w - want) < 1e-6 for w in ws)
        return ("NARROWED-IN" if inside else "NARROWED-OUT"), f"narrowed {du.get('reason')} {sorted(ws)}"
    return du["outcome"].upper(), str(du.get("reason"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tiles", required=True)
    ap.add_argument("--set", action="append", required=True, help="TAG=DIR")
    ap.add_argument("--json", default=None)
    a = ap.parse_args()
    tiles = Path(a.tiles)
    man = json.loads((tiles / "manifest.json").read_text())
    ans = json.loads((tiles / "answers.json").read_text())["answers"]
    rows = []
    for t in man["tiles"]:
        h = t["hidden"]
        rows.append({"id": t["id"], "key": h["key"], "movement": h["movement"], "sean": ans[t["id"]]["sean"], "kind": t["kind"],
                     "klass": h.get("change_class") or "control:" + h.get("control", "")})
    sets = [s.split("=", 1) for s in a.set]
    for tag, d in sets:
        for movement in ("brahms", "litolff"):
            wanted = {r["key"]: r for r in rows if r["movement"] == movement}
            for p in record_paths(d, movement):
                if not p.exists():
                    print(f"[{tag}] missing {p}", file=sys.stderr)
                    continue
                run = RD.load_run(str(p))
                for key, r in wanted.items():
                    if r.get(tag) is not None:
                        continue
                    du = verdict_of(run, key)
                    if du is None:
                        continue
                    want = VALUE[r["sean"]]
                    r[tag] = score(du, want)
                del run
    print(f"{'tile':10s} {'sean':6s} {'class':22s} " + " | ".join(f"{tag:>34s}" for tag, _ in sets))
    for r in sorted(rows, key=lambda r: r["id"]):
        cells = []
        for tag, _ in sets:
            v = r.get(tag)
            cells.append(f"{(v[0] + ' ' + v[1])[:34]:>34s}" if v else f"{'(not in set)':>34s}")
        print(f"{r['id']:10s} {r['sean']:6s} {r['klass'][:22]:22s} " + " | ".join(cells))
    if a.json:
        Path(a.json).write_text(json.dumps(rows, indent=1, default=str))


if __name__ == "__main__":
    main()
