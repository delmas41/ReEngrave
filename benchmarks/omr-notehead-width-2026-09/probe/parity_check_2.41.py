"""ROADMAP 2.41 -- a large-sample PROXY control, additional to the crop
print check: the detector's own OnLine/InSpace class name is a SEPARATE
output channel from the box position (shape classification vs box
y-coordinate) and gives a cheap, page-wide expectation for each
reading's chosen position's PARITY (a line position is even, a space
position is odd, by this script's own position convention: pos 0 = the
staff's top line). Not a full ground truth (it is still the SAME
detector) but informative where it disagrees at scale -- reported next
to the crop-based judgement, never instead of it.
"""
import json
import sys


def parity_ok(pos, name):
    if pos is None:
        return None
    even = (pos % 2 == 0)
    if "OnLine" in name:
        return even
    if "InSpace" in name:
        return not even
    return None


def main():
    for page, path in [
        ("litolff", "benchmarks/omr-notehead-width-2026-09/out/2.41/measure-litolff-p3.json"),
        ("brahms", "benchmarks/omr-notehead-width-2026-09/out/2.41/measure-brahms-p1.json"),
    ]:
        d = json.load(open(path))
        rows = d["rows"]
        n = {"A": 0, "B": 0, "C": 0}
        ok = {"A": 0, "B": 0, "C": 0}
        for r in rows:
            name = r["name"]
            if "OnLine" not in name and "InSpace" not in name:
                continue
            for key, posfield in [("A", "a_pos"), ("B", "b_pos"), ("C", "c_pos")]:
                pos = r.get(posfield)
                if pos is None:
                    continue
                res = parity_ok(pos, name)
                if res is None:
                    continue
                n[key] += 1
                if res:
                    ok[key] += 1
        print(page, {k: f"{ok[k]}/{n[k]} = {ok[k]/n[k]:.3f}" for k in n})


if __name__ == "__main__":
    sys.exit(main())
