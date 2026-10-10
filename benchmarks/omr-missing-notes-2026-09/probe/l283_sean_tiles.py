#!/usr/bin/env python3
"""l283_sean_tiles: the arm's reading of the 30 heads SEAN JUDGED on the 2.81 blind tiles (`out/print/2.81-review/answers.json`), the
best out-of-sample test this lane has: every one of those heads stood in the 2.81 population P (base: narrowed
`beam_discounted_uncertain`, level 0 or 1, the beam level ranked first) and he said what is printed. Against his word:

  he says an EIGHTH:      arm DECIDED level 1 / NARROWED with no level-0 candidate -> acknowledged (the quarter is gone);
                          narrowed over 0 and 1 -> still undecided; decided level 0 -> WRONG
  he says anything else   (quarter, dotted quarter, half, a rest): arm decided level >= 1, or narrowed with no level-0
                          candidate -> NEWLY WRONG (a flag read where he sees none); narrowed over 0 -> unchanged; decided 0 -> ok

The tip row at the head's own stem tip (the end its decided direction points away from) is printed beside each.

    python3 l283_sean_tiles.py --arm-records brahms=path.json litolff=path.json ...   # every arm record that holds a tile page

⚠️ A glyph key is `glyph/<pdf page>/...` and the two scores' keys COLLIDE (Brahms pdf 2 and Litolff pdf 2 are both `glyph/2/...`): a
record is chosen by the tile's movement AND the key, never by the key alone (the first run of this script read three Brahms tiles
off the Litolff count-page record).
"""
import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from l283_truth_score import tip_state  # noqa: E402
from tools.omr.staged import readout as RD  # noqa: E402
from tools.omr.staged.record import Q  # noqa: E402


def levels(v):
    if v["outcome"] == "decided":
        val = v.get("value") or {}
        return "decided", [val.get("beam_levels")]
    out = []
    for c in v.get("candidates") or []:
        val = c.get("value") if isinstance(c, dict) else None
        if isinstance(val, dict):
            out.append(val.get("beam_levels"))
    return v["outcome"], sorted({x for x in out if x is not None})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm-records", nargs="+", required=True, help="movement=path.json ...")
    ap.add_argument("--tiles", default=str(REPO / "out/print/2.81-review"))
    a = ap.parse_args()
    man = json.loads((Path(a.tiles) / "manifest.json").read_text())
    ans = json.loads((Path(a.tiles) / "answers.json").read_text())
    runs = []
    for spec in a.arm_records:
        mv, p = spec.split("=", 1)
        runs.append((mv, RD.load_run(p)))
        print("loaded", mv, p, "pages", runs[-1][1].pages()[:30])
    rows = []
    for t in man["tiles"]:
        if t["kind"] != "sample":
            continue
        h = t["hidden"]
        key = h["key"]
        word = ans.get(t["id"])
        run = next((r for mv, r in runs if mv == h["movement"] and key in r.glyphs), None)
        if run is None:
            rows.append((t["id"], key, word, "NOT IN ANY ARM RECORD", None, None))
            continue
        v = run.standing(key, Q.DURATION, "ADJUDICATE")
        oc, lv = levels(v) if v else (None, [])
        rows.append((t["id"], key, word, f"{oc}:{v.get('reason') if v else None} levels {lv}", tip_state(run, key), (oc, lv)))
    tally = {"eighth": {"acknowledged": 0, "still_undecided": 0, "wrong": 0}, "other": {"unchanged": 0, "newly_wrong": 0}}
    for tid, key, word, reading, tip, ol in sorted(rows, key=lambda r: r[0]):
        verdict = ""
        if ol is not None:
            oc, lv = ol
            flagged = lv and 0 not in lv
            if word == "eighth":
                verdict = "ACKNOWLEDGED" if flagged else ("wrong" if oc == "decided" else "still undecided")
                tally["eighth"]["acknowledged" if flagged else ("wrong" if oc == "decided" else "still_undecided")] += 1
            else:
                verdict = "NEWLY WRONG" if flagged else "unchanged"
                tally["other"]["newly_wrong" if flagged else "unchanged"] += 1
        print(f"{tid} {key:24s} Sean: {str(word):14s} arm: {reading:45s} tip: {str(tip):32s} {verdict}")
    print("\nSean says an EIGHTH:", tally["eighth"])
    print("Sean says anything else (quarter, dotted quarter, half, rest):", tally["other"])


if __name__ == "__main__":
    main()
