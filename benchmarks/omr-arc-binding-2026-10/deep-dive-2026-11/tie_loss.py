"""Why a decided+paired tie is not in the file (measure only): python3 tie_loss.py LEDGER.json MUSICXML"""
import collections
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import written as W

res = json.load(open(sys.argv[1]))
wr = W.parse(pathlib.Path(sys.argv[2]).read_text())
notes = wr["notes"]
starts = collections.defaultdict(list)
for a, b in wr["ties"]:
    starts[a].append(b)
c = collections.Counter()
ex = collections.defaultdict(list)
for r in res["rows"]:
    if r.get("lost_rule") != "export:tie_not_in_file":
        continue
    a, b = r["pair"]
    na, nb = notes.get(a), notes.get(b)
    if na is None or nb is None:
        why = "head_not_in_file(%s%s)" % ("start " if na is None else "", "stop" if nb is None else "")
    elif na["voice"] != nb["voice"]:
        why = "two_voices"
    elif na["pitch"] != nb["pitch"]:
        why = "pitch_differs(%s vs %s)" % ("same_step_other_spelling" if na["pitch"][0] == nb["pitch"][0] and na["pitch"][-1] == nb["pitch"][-1] else "different", "")
    elif a in starts:
        why = "start_tied_to_other_note"
    else:
        why = "unknown"
    c[why] += 1
    ex[why].append((r["curve"], a, b, na, nb))
print(c)
for w, l in ex.items():
    print(w, l[:2])
