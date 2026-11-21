"""Exploration of a re-adjudicated record: which reason words / rows items 3-5 need. Read-only."""
import sys, json, collections, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[4]))
from tools.omr.staged.record_io import load_record
r = load_record(sys.argv[1])["record"]
c = collections.Counter()
ex = {}
for v in r["verdicts"]:
    s = json.dumps([v.get("reason"), v.get("value"), (v.get("detail") or {}).get("reason"), (v.get("detail") or {}).get("why")], default=str)
    if "claimed_by:arc" in s:
        k = (v["quantity"], v.get("status"), str(v.get("reason"))[:60], str(v.get("value"))[:60])
        c[k] += 1
        ex.setdefault(k, v)
for k, n in c.most_common():
    print(n, k)
for k, v in list(ex.items())[:2]:
    print(json.dumps({kk: vv for kk, vv in v.items() if kk != "detail"}, default=str)[:600])
    print(json.dumps(v.get("detail"), default=str)[:1500])
print(collections.Counter((o.get("detail") or {}).get("owner") for o in r["observations"] if o["quantity"] == "claimed_area"))
ca = [o for o in r["observations"] if o["quantity"] == "claimed_area" and (o.get("detail") or {}).get("owner") in ("arc", "arc_trace")]
print(len(ca))
if ca:
    print(json.dumps(ca[0], default=str)[:1500])
lw = [o for o in r["observations"] if o["quantity"] == "claimed_area" and (o.get("detail") or {}).get("letters_of_word")]
print("letters_of_word claims", len(lw))
if lw:
    print(json.dumps(lw[0], default=str)[:1200])
dy = [v for v in r["verdicts"] if v["quantity"] == "dynamic"]
print("dynamic verdicts", len(dy))
if dy:
    print(json.dumps(dy[0], default=str)[:1500])
du = [v for v in r["verdicts"] if v["quantity"] == "duration" and "one_beam_count" in (v.get("detail") or {})]
print("durations with one_beam_count", len(du))
if du:
    d = du[0]["detail"]
    print(json.dumps({k: d.get(k) for k in ("one_beam_count", "beams_by_stem", "flags_attached", "levels_certain", "levels_possible")}, default=str)[:1500])
