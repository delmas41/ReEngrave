import sys
from collections import Counter

sys.path.insert(0, ".")
from tools.omr.staged.record_io import load_record  # noqa: E402

R = load_record(sys.argv[1])["record"]
last = {}
for v in R["verdicts"]:
    if v["quantity"] == "instrument":
        last[v["subject"]] = v
c = Counter()
for s, v in last.items():
    if str(v["reason"]) == "not_in_lexicon":
        d = v.get("detail") or {}
        c[(s.split("/")[1], repr(d.get("reader_text")), repr(d.get("lexicon_said")))] += 1
for k, n in sorted(c.items()):
    print(n, k)
