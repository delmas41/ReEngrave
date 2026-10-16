"""ROADMAP 2.153 -- for named glyphs: the STORED live adjudicate_duration verdict's detail beside the CURRENT replay's, key by key
(only keys that differ). usage: diffdetail_2_153.py SLICE.json GLYPH [GLYPH ...]"""
import json
import sys

sys.path.insert(0, ".")
rec = json.load(open(sys.argv[1]))
G = set(sys.argv[2:])
from tools.omr.staged.record import Q  # noqa: E402
from tools.omr.staged.review import rerun as RR  # noqa: E402
sys.path.insert(0, "benchmarks/omr-bar-sum-holdout-2026-09/probe")
import replay_util_2_153 as RU  # noqa: E402

st = {}
for v in rec["verdicts"]:
    if v["quantity"] == Q.DURATION and v["subject"] in G and v.get("decider") == "adjudicate_duration":
        st[v["subject"]] = v
log, _ = RU.rebuild(rec)
RR.run_stages(log)
for v in log.to_json()["verdicts"]:
    if v["quantity"] == Q.DURATION and v["subject"] in G and v.get("decider") == "adjudicate_duration":
        s = st.get(v["subject"])
        print("=====", v["subject"], "stored:", s and (s["outcome"], s["reason"]), "replay:", v["outcome"], v["reason"])
        a, b = (s or {}).get("detail") or {}, v.get("detail") or {}
        for k in sorted(set(a) | set(b)):
            if a.get(k) != b.get(k):
                print("   %-28s stored=%s | replay=%s" % (k, json.dumps(a.get(k), default=str)[:200], json.dumps(b.get(k), default=str)[:200]))
        print("   used stored/replay:", len((s or {}).get("used") or []), len(v.get("used") or []))
