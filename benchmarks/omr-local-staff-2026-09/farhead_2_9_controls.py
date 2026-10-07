"""lane-farhead-2-9 (2026-10-07): every Sean-confirmed tile keeps its answer. The subjects of the confirmed tiles of
  note_first 1-11 (seed 20261005 regenerated from the committed oos jsons), night_1006 1-5,7,8,11,12, edge_vs_through_flips 1-24,
  night_1007 2-4,6-12, brahms_1007_worse_cases 1,2, farhead_5_6 all but 2 and 9
are replayed on the 10-07 extracts with `look_where_it_must_be` OFF then ON; any that moves is printed.
CONTROL: the arm that matters (OFF) is the tree's reader as it stood; a tile whose subject is not a far head in the extract
(an owner or arc tile) is counted as `not_a_far_head`, never as unchanged.

  python3 farhead_2_9_controls.py <x7 litolff> <x7 brahms> <repo root>
"""
import json, random, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]))
import farhead_5_6_diag as D
import overnight_1004_report as R


def note_first():
    pool = []
    for path, which in (("farhead_note_first_oos_litolff.json", "beethoven5-litolff"), ("farhead_note_first_oos_brahms.json", "brahms1-breitkopf")):
        for r in json.loads((HERE / path).read_text()):
            if r["new"]["pos"] is not None and r["new"]["line_y"] is not None:
                r["doc"] = which
                pool.append(r)
    pick = random.Random(20261005).sample(pool, 12)
    return [("note_first %d" % i, r["doc"], r["subject"]) for i, r in enumerate(pick, 1) if i != 12]


def lists(root):
    P = Path(root) / "out/print"
    BR, LI = "brahms1-breitkopf", "beethoven5-litolff"
    out = note_first()
    n6 = json.loads((P / "ledgers/night_1006_sample.json").read_text())
    out += [("night_1006 %d" % i, r["doc"], r["subject"]) for i, r in enumerate(n6, 1) if i in (1, 2, 3, 4, 5, 7, 8, 11, 12)]
    ev = json.loads((P / "ledgers/edge_vs_through_flips.json").read_text())
    out += [("edge_vs_through_flips %d" % r["n"], BR if r["which"] == "brahms" else LI, r["subject"]) for r in ev]
    n7 = json.loads((P / "night_1007_sample.json").read_text())
    out += [("night_1007 %d" % r["n"], r["doc"], r["subject"]) for r in n7 if r["n"] in (2, 3, 4, 6, 7, 8, 9, 10, 11, 12)]
    b7 = json.loads((P / "brahms_1007_worse_cases.json").read_text())
    out += [("brahms_1007 %d" % r["n"], BR, r["subject"]) for r in b7 if r["n"] in (1, 2)]
    f56 = json.loads((P / "farhead_5_6.json").read_text())
    out += [("farhead_5_6 %d" % t["n"], BR, t["subject"]) for t in f56 if t["n"] not in (2, 9)]
    return out


if __name__ == "__main__":
    lito, brah, root = sys.argv[1:4]
    L = {"beethoven5-litolff": D.load(lito, "beethoven5-litolff"), "brahms1-breitkopf": D.load(brah, "brahms1-breitkopf")}
    tiles = lists(root)
    moved, same, skipped = [], 0, []
    for tag, doc, s in tiles:
        data, rep = L[doc]
        g = data["glyphs"].get(s)
        if g is None or not R.is_far(g) or "box" not in g or not ("fh" in g or "fh_abs" in g):
            skipped.append((tag, s, "not_a_far_head_in_the_extract"))
            continue
        ans = {}
        for on in (False, True):
            D.FH.READER_KEYWORDS["look_where_it_must_be"] = on
            gg, r, cap, gl, ctx = D.read_one(rep, data, s)
            ans[on] = (r["pos"], r["reason"][:80])
        if ans[False][0] != ans[True][0]:
            moved.append((tag, s, ans[False], ans[True]))
        else:
            same += 1
    print("confirmed tiles listed", len(tiles), "| far heads replayed", same + len(moved), "| unchanged", same, "| MOVED", len(moved),
          "| skipped (not a far head here)", len(skipped))
    for m in moved:
        print("  MOVED", m)
    for k in skipped:
        print("  skipped", k)
