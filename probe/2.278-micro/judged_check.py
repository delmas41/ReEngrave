"""Bar 2 (judged right->wrong = 0) and bar 3 helper: every head Sean has judged (value answers, `judged score` joins by place/key) on the sample pages:
what would the group reading say, and does it keep his answer?

usage: python3 probe/2.278-micro/judged_check.py REC.pkl JUDGED.json [window]
"""
import sys, json, pickle, collections
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
import groups as G, heads as H
from tools.omr.staged import judged as J

D = pickle.load(open(sys.argv[1], "rb"))
jd = json.load(open(sys.argv[2]))
window = sys.argv[3] if len(sys.argv) > 3 else "B2"
pages = sorted(D["pages"])
reads = {p: G.read_page(D["pages"][p]) for p in pages}


def base_beats(h):
    v = h.get("value")
    if h.get("outcome") == "decided" and isinstance(v, dict) and v.get("beats") is not None:
        return v["beats"] * 2 ** (v.get("beam_levels") or 0)
    cs = h.get("cands") or []
    bs = set()
    for c in cs:
        bs.add(round((c[4] or 0) * 2 ** (c[1] or 0), 4))
    return bs.pop() if len(bs) == 1 else None


rows = []
seen = set()
for t in jd["tiles"]:
    sub = t.get("subject")
    if isinstance(sub, list):
        continue
    if t.get("status") not in ("right", "wrong", "narrowed") or not sub or sub not in D["heads"]:
        continue
    h = D["heads"][sub]
    if h["page"] not in pages or not h.get("bbox") or (t["item"], t["tile"], sub) in seen:
        continue
    seen.add((t["item"], t["tile"], sub))
    kind, val = J.parse_answer(t["answer"])
    if kind != "duration" or val is None:
        continue
    st, L, why, det = H.decide(D["pages"][h["page"]], reads[h["page"]], h, window=window)
    bb = base_beats(h)
    rb = None if (L is None or bb is None) else bb * 0.5 ** L
    rows.append(dict(item=t["item"], tile=t["tile"], sub=sub, page=h["page"], status=t["status"], sean=val, outcome=h.get("outcome"), reason=h.get("reason"),
                     reading=st, L=L, why=why, reading_beats=rb, bbox=h["bbox"]))
c = collections.Counter()
for r in rows:
    if r["reading"] == "undecided":
        c[(r["status"], "reading_undecided")] += 1
    elif r["reading_beats"] is None:
        c[(r["status"], "no_base")] += 1
    else:
        same = abs(r["reading_beats"] - r["sean"]) < 1e-6
        c[(r["status"], "reading_matches_sean" if same else "reading_DISAGREES_with_sean")] += 1
for k, v in sorted(c.items()): print(v, k)
print("judged value heads on the sample pages:", len(rows))
print("RIGHT->WRONG (record right, reading disagrees):", [r for r in rows if r["status"] == "right" and r["reading"] != "undecided" and r["reading_beats"] is not None and abs(r["reading_beats"] - r["sean"]) > 1e-6])
print("RIGHT->undecided (explain, not a pass):", sum(1 for r in rows if r["status"] == "right" and r["reading"] == "undecided"))
print("narrowed judged: ", [(r["sub"], r["sean"], r["reading"], r["L"], r["reading_beats"]) for r in rows if r["status"] == "narrowed"])
json.dump(rows, open(sys.argv[2].replace(".json", "_checked.json"), "w"), default=str)
