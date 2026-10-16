"""ROADMAP 2.153 -- the first `adjudicate_duration` verdict of named glyphs under the flag OFF and ON, side by side (keys that differ).
usage: arms_detail_2_153.py SLICE.json GLYPH [GLYPH ...]"""
import json
import os
import sys

sys.path.insert(0, ".")
rec = json.load(open(sys.argv[1]))
G = set(sys.argv[2:])
from tools.omr.staged.review import rerun as RR  # noqa: E402

sys.path.insert(0, "benchmarks/omr-bar-sum-holdout-2026-09/probe")
import replay_util_2_153 as RU  # noqa: E402

out = {}
for arm, env in (("off", ""), ("on", "1")):
    os.environ["OMR_BEAM_LEVEL_NEEDS_A_JOINED_STEM"] = env
    log, _ = RU.rebuild(rec)
    RR.run_stages(log)
    for v in log.to_json()["verdicts"]:
        if v["subject"] in G and v["quantity"] == "duration":
            out.setdefault(v["subject"], {}).setdefault(arm, []).append(v)
for g, d in out.items():
    print("=====", g)
    for arm in ("off", "on"):
        for v in d.get(arm, []):
            val = v["value"] if isinstance(v["value"], dict) else v["value"]
            print("  ", arm, v["decider"], v["reason"], v["outcome"], json.dumps(val, default=str)[:90],
                  [c.get("value", {}).get("written") for c in (v.get("candidates") or [])] or "")
    a = next((v for v in d.get("off", []) if v["decider"] == "adjudicate_duration"), {}).get("detail", {})
    b = next((v for v in d.get("on", []) if v["decider"] == "adjudicate_duration"), {}).get("detail", {})
    for k in sorted(set(a) | set(b)):
        if a.get(k) != b.get(k):
            print("     %-26s off=%s | on=%s" % (k, json.dumps(a.get(k), default=str)[:120], json.dumps(b.get(k), default=str)[:120]))
