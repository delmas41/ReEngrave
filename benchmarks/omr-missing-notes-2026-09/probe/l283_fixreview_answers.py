#!/usr/bin/env python3
"""l283_fixreview_answers: write `out/print/2.83-fix-review/answers.json` -- Sean's blind answers on the 10 fix-round tiles, scored against the standing ADJUDICATE duration verdict of
each head in the main (`8be6cf5f`), v5 (`28f1bda4`) and fix (`e9c8c202`) re-gather sets (`run_set.sh` directories), with each head's ADJUDICATE STATUS and its
refusal reason where it is refused. ROADMAP 2.83 fix round. Sean's words were relayed by the coordinator, verbatim; the tiles were shown in MANIFEST order.

    python3 l283_fixreview_answers.py --tiles out/print/2.83-fix-review --set main=DIR --set v5=DIR --set fix=DIR
"""
import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from l283_rescore import candidate_writtens, undotted  # noqa: E402
from tools.omr.staged import readout as RD  # noqa: E402
from tools.omr.staged.record import Q  # noqa: E402

WORDS = "1. 4  2. 8  3. 8  4. 8  5. 8  6. 4  7. 2  8. part of an accidental  9. 4  10. dot 4"
# his numbering is the manifest order: tile_01, tile_02, tile_03, control_1, tile_04, tile_05, tile_06, tile_07, tile_08, control_2
SEAN = {
    "tile_01": ("4", "quarter", 1.0, 0),
    "tile_02": ("8", "eighth", 0.5, 0),
    "tile_03": ("8", "eighth", 0.5, 0),
    "control_1": ("8", "eighth", 0.5, 0),
    "tile_04": ("8", "eighth", 0.5, 0),
    "tile_05": ("4", "quarter", 1.0, 0),
    "tile_06": ("2", "half", 2.0, 0),
    "tile_07": ("part of an accidental", "not a note", None, None),
    "tile_08": ("4", "quarter", 1.0, 0),
    "control_2": ("dot 4", "dotted quarter", 1.0, 1),
}


def record_paths(d, movement):
    d = Path(d)
    if movement == "brahms":
        return [d / "quick-b/out/brahms1-breitkopf/brahms1-breitkopf-p1.record.json", d / "brahms-tiles.record.json"]
    return [d / "quick-l/out/beethoven5-litolff/beethoven5-litolff-p3.record.json", d / "litolff-t.record.json"]


def describe(run, key):
    g = run.glyphs.get(key)
    if g is None:
        return None
    du = run.standing(key, Q.DURATION, "ADJUDICATE")
    status, why = RD.adjudicate_status(run, g)
    out = {"status": status, "status_reason": why}
    if du is None:
        out["duration"] = None
    elif du["outcome"] == "decided":
        v = du.get("value") or {}
        out["duration"] = {"outcome": "decided", "reason": du.get("reason"), "undotted": undotted(v) if v.get("written") is not None else None,
                           "dots": v.get("dots"), "beam_levels": v.get("beam_levels"), "head_fill": v.get("head_fill")}
    else:
        out["duration"] = {"outcome": du["outcome"], "reason": du.get("reason"), "candidates_undotted": sorted(candidate_writtens(du))}
    return out


def score(desc, want, want_dots):
    if desc is None or desc.get("duration") is None:
        return "ABSENT"
    d = desc["duration"]
    if d["outcome"] == "decided":
        ok = d["undotted"] is not None and abs(d["undotted"] - want) < 1e-6
        return "RIGHT" if ok else "WRONG"
    if d["outcome"] == "narrowed":
        return "NARROWED-IN" if any(abs(w - want) < 1e-6 for w in d["candidates_undotted"]) else "NARROWED-OUT"
    return d["outcome"].upper()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tiles", required=True)
    ap.add_argument("--set", action="append", required=True)
    a = ap.parse_args()
    tiles = Path(a.tiles)
    man = json.loads((tiles / "manifest.json").read_text())
    order = [t["id"] for t in man["tiles"]]
    assert order == ["tile_01", "tile_02", "tile_03", "control_1", "tile_04", "tile_05", "tile_06", "tile_07", "tile_08", "control_2"], order
    rows = {t["id"]: {"id": t["id"], "key": t["hidden"]["key"], "movement": t["hidden"]["movement"], "pdf_page": t["hidden"].get("pdf_page"),
                      "class": t["hidden"].get("change_class") or "control:" + t["hidden"].get("control", ""),
                      "manifest_base_reading(v5)": t["hidden"].get("base_reading"), "manifest_arm_reading(fix)": t["hidden"].get("arm_reading")}
            for t in man["tiles"]}
    for spec in a.set:
        tag, d = spec.split("=", 1)
        for movement in ("brahms", "litolff"):
            want = {k: r for k, r in rows.items() if r["movement"] == movement}
            for p in record_paths(d, movement):
                if not p.exists():
                    print("missing", p, file=sys.stderr)
                    continue
                run = RD.load_run(str(p))
                for tid, r in want.items():
                    if tag in r:
                        continue
                    desc = describe(run, r["key"])
                    if desc is not None:
                        r[tag] = desc
                del run
    answers = {}
    for i, tid in enumerate(order, 1):
        verb, name, val, dots = SEAN[tid]
        r = rows[tid]
        entry = {"shown_as": i, "sean": verb, "sean_reads": name, "verbatim": f"{i}. {verb}", "key": r["key"], "movement": r["movement"], "pdf_page": r["pdf_page"],
                 "class": r["class"], "v5_reading": r["manifest_base_reading(v5)"], "fix_reading": r["manifest_arm_reading(fix)"]}
        for tag in ("main", "v5", "fix"):
            desc = r.get(tag)
            entry[tag] = desc
            if val is not None:
                entry[tag + "_score"] = score(desc, val, dots)
        answers[tid] = entry
    out = {"judge": "sean", "date": "2026-10-11",
           "via": "cloud coordination session (tiles shown in MANIFEST order, numbered 1-10: " + ", ".join(order) + ")",
           "words": WORDS, "order": order, "answers": answers}
    (tiles / "answers.json").write_text(json.dumps(out, indent=1, default=str))
    for tid in order:
        e = answers[tid]
        print(f"{tid:10s} {e['verbatim'][:26]:26s} v5 {e.get('v5_score', '-'):13s} fix {e.get('fix_score', '-'):13s} main {e.get('main_score', '-'):13s}  {e['class']}")
    t7 = answers["tile_07"]
    for tag in ("main", "v5", "fix"):
        print("tile_07", tag, (t7.get(tag) or {}).get("status"), (t7.get(tag) or {}).get("status_reason"), (t7.get(tag) or {}).get("duration"))


if __name__ == "__main__":
    main()
