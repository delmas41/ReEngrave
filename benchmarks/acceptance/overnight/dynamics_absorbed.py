"""Every bar whose spelled dynamics shrank between two re-gathers: was each lost
token ABSORBED into a word + dynamic marking of that bar, or LOST?
python3 dynamics_absorbed.py <shared-records dir> <base tag> <arm tag> [doc ...]"""
import collections
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[3]))
from tools.omr.staged.record_io import load_record   # noqa: E402


def live(rec, quantity):
    out = {}
    sup = {v.get("supersedes") for v in rec["verdicts"] if v.get("supersedes")}
    for v in rec["verdicts"]:
        if v["quantity"] == quantity and v["id"] not in sup:
            out[v["subject"]] = v
    return out


root, base, arm = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
docs = sys.argv[4:] or ["beethoven5-litolff", "brahms1-breitkopf"]
for doc in docs:
    a = load_record(root / f"{doc}-mvt1-whole-{base}.record.json")["record"]
    b = load_record(root / f"{doc}-mvt1-whole-{arm}.record.json")["record"]
    da, db = live(a, "dynamic"), live(b, "dynamic")
    words = live(b, "direction")
    marks = live(b, "marking")
    tally = collections.Counter()
    lost_examples = []
    for cell, va in da.items():
        before = collections.Counter(va.get("value") or [])
        after = collections.Counter((db.get(cell) or {}).get("value") or [])
        gone = before - after
        if not gone:
            continue
        held = collections.Counter()
        for m in ((marks.get(cell) or {}).get("detail") or {}).get("markings", []):
            for t in m.get("dynamics") or []:
                held[t.lower()] += 1
        for tok, n in gone.items():
            for _ in range(n):
                if held[tok.lower()] > 0:
                    held[tok.lower()] -= 1
                    tally["absorbed into a marking"] += 1
                else:
                    tally["not in a marking (a word letter OR a real loss -- the print decides)"] += 1
                    lost_examples.append((cell, tok, (words.get(cell) or {}).get("value"),
                                          [m.get("text") for m in ((marks.get(cell) or {}).get("detail") or {}).get("markings", [])]))
    print(f"== {doc}: {dict(tally)}")
    for ex in lost_examples[:25]:
        print("   not in a marking:", ex)
